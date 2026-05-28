from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.permissions import IsAdminOrVendedor
from rest_framework.permissions import IsAuthenticated

from apps.api.serializers.venta_serializer import (
    AgregarProductoSerializer,
    CrearVentaSerializer,
    FinalizarVentaSerializer,
)
from apps.customers.models import Cliente
from apps.sales.models import Venta
from apps.sales.services.venta_service import VentaService

# Utility para conversión segura de Decimal a float
def _to_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


class CrearVentaAPIView(APIView):
    """
    POST /api/ventas/
    Crea una nueva venta en estado EN_PROCESO llamando a VentaService.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        serializer = CrearVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo_venta = serializer.validated_data['tipo_venta']
        cliente_id = serializer.validated_data.get('cliente_id')
        
        cliente = None
        if cliente_id:
            cliente = get_object_or_404(Cliente, pk=cliente_id)

        # Llamada al Service (Core Logic)
        venta = VentaService.crear_venta(
            usuario=request.user,
            tipo_venta=tipo_venta,
            cliente=cliente,
        )

        # Respuesta serializable (DTO / dict)
        response_data = {
            "id": venta.id,
            "folio": venta.folio,
            "tipo_venta": venta.tipo_venta,
            "estado": venta.estado,
            "cliente": {
                "id": venta.cliente.id,
                "nombre": venta.cliente.nombre
            } if venta.cliente else None,
            "subtotal": _to_float(venta.subtotal),
            "total": _to_float(venta.total),
            "created_at": venta.created_at.isoformat(),
        }

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_201_CREATED)


class AgregarProductoAPIView(APIView):
    """
    POST /api/ventas/{id}/agregar-producto/
    Agrega un producto a una venta y recalcula los totales mediante VentaService.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, pk, *args, **kwargs):
        # Validar existencia de la venta primero para dar 404 claro
        get_object_or_404(Venta, pk=pk)

        serializer = AgregarProductoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variante_id = serializer.validated_data['variante_id']
        cantidad = serializer.validated_data['cantidad']

        # Llamada al Service
        detalle = VentaService.agregar_producto(
            venta_id=pk,
            variante_id=variante_id,
            cantidad=cantidad,
        )

        response_data = {
            "detalle_id": detalle.id,
            "venta_id": detalle.venta_id,
            "variante": {
                "id": detalle.variante.id,
                "nombre": str(detalle.variante.nombre),
                "sku": detalle.variante.sku,
            },
            "cantidad": detalle.cantidad,
            "precio_unitario": _to_float(detalle.precio_unitario),
            "subtotal": _to_float(detalle.subtotal),
        }

        return Response({
            "success": True,
            "data": response_data,
            "message": "Producto agregado con éxito."
        }, status=status.HTTP_200_OK)


class FinalizarVentaAPIView(APIView):
    """
    POST /api/ventas/{id}/finalizar/
    Finaliza la venta, efectúa descuentos de stock, valida límite de crédito, etc.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, pk, *args, **kwargs):
        get_object_or_404(Venta, pk=pk)

        serializer = FinalizarVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        force_credit_override = serializer.validated_data.get('force_credit_override', False)
        authorized_by = serializer.validated_data.get('authorized_by')

        try:
            venta = VentaService.finalizar_venta(
                venta_id=pk,
                force_credit_override=force_credit_override,
                authorized_by=authorized_by,
            )
        except ValueError as e:
            return Response({
                "success": False,
                "error": str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            return Response({
                "success": False,
                "error": str(e),
            }, status=status.HTTP_403_FORBIDDEN)

        response_data = {
            "id": venta.id,
            "folio": venta.folio,
            "estado": venta.estado,
            "total_final": _to_float(venta.total),
        }

        return Response({
            "success": True,
            "data": response_data,
            "message": f"Venta {venta.folio} finalizada exitosamente."
        }, status=status.HTTP_200_OK)


class DetalleVentaAPIView(APIView):
    """
    GET /api/ventas/{id}/
    Obtiene el detalle completo de la venta, optimizado con prefetch.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def get(self, request, pk, *args, **kwargs):
        # Usamos prefetch para evitar N+1
        venta = get_object_or_404(
            Venta.objects.select_related('cliente', 'usuario')
            .prefetch_related('detalles__variante__producto', 'pagos__detalles'),
            pk=pk
        )

        detalles_data = []
        for det in venta.detalles.all():
            detalles_data.append({
                "id": det.id,
                "producto": str(det.variante.producto.nombre),
                "variante": str(det.variante.nombre),
                "cantidad": det.cantidad,
                "precio_unitario": _to_float(det.precio_unitario),
                "subtotal": _to_float(det.subtotal),
            })

        pagos_data = []
        total_pagado = Decimal('0.00')
        total_comision = Decimal('0.00')

        for pago in venta.pagos.all():
            total_pagado += pago.monto_cliente
            total_comision += pago.cargo_tarjeta
            for pd in pago.detalles.all():
                pagos_data.append({
                    "id": pd.id,
                    "metodo": pd.metodo_pago,
                    "monto": _to_float(pd.monto),
                    "cargo_generado": _to_float(pd.cargo_generado),
                })

        response_data = {
            "id": venta.id,
            "folio": venta.folio,
            "usuario": venta.usuario.username,
            "cliente": {
                "id": venta.cliente.id,
                "nombre": venta.cliente.nombre,
                "saldo_actual": _to_float(venta.cliente.saldo_actual),
            } if venta.cliente else None,
            "tipo_venta": venta.tipo_venta,
            "estado": venta.estado,
            "subtotal": _to_float(venta.subtotal),
            "total": _to_float(venta.total),
            "total_pagado": _to_float(total_pagado),
            "total_comision": _to_float(total_comision),
            "pagos": pagos_data,
            "created_at": venta.created_at.isoformat(),
            "updated_at": venta.updated_at.isoformat(),
            "detalles": detalles_data,
        }

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_200_OK)
