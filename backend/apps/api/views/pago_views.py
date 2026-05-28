from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.permissions import IsAdminOrVendedor
from rest_framework.permissions import IsAuthenticated

from apps.api.serializers.pago_serializer import (
    PagoContadoSerializer,
    PagoCreditoSerializer,
    PagoInicialSerializer,
    PagoMixtoSerializer,
)
from apps.payments.models import Pago
from apps.payments.services.pago_service import PagoService
from apps.sales.models import Venta


def _to_float(value) -> float:
    """Helper interno seguro para convertir Decimal a float para respuestas JSON."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _build_pago_response(pago: Pago, saldo_restante: float = 0.0, estado_venta: str = '') -> dict:
    """Helper interno para construir el dict uniforme esperado por el contrato de la API."""
    data = {
        "pago_id": pago.id,
        "folio": f"P-{pago.id:05d}",
        "venta_id": pago.venta_id if pago.venta_id else None,
        "cliente_id": pago.cliente_id if pago.cliente_id else None,
        "total_pagado": _to_float(pago.monto_cliente),
    }

    if pago.venta_id:
        data["saldo_restante"] = saldo_restante
        data["estado_venta"] = estado_venta

    return data


class PagoContadoAPIView(APIView):
    """
    POST /api/pagos/contado/
    Registra el pago completo de una venta de contado.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        serializer = PagoContadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        venta_id = serializer.validated_data['venta_id']
        metodos_pago = serializer.validated_data['metodos_pago']

        # Llamada al Service de Dominio
        pago = PagoService.registrar_pago_contado(
            venta_id=venta_id,
            metodos_pago=metodos_pago,
            usuario=request.user,
        )

        # Para contado, el saldo siempre es 0 y el estado es COMPLETADA o el original de la venta.
        # Recuperamos la venta desde el Pago para no golpear la DB otra vez innecesariamente.
        saldo = 0.0
        estado_venta = pago.venta.estado if pago.venta else ""

        response_data = _build_pago_response(pago, saldo, estado_venta)

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_201_CREATED)


class PagoCreditoAPIView(APIView):
    """
    POST /api/pagos/credito/
    Registra un abono a la cuenta de crédito de un cliente.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        serializer = PagoCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cliente_id = serializer.validated_data['cliente_id']
        venta_id = serializer.validated_data.get('venta_id')
        metodos_pago = serializer.validated_data['metodos_pago']

        # Llamada al Service de Dominio
        pago = PagoService.registrar_pago_credito(
            cliente_id=cliente_id,
            metodos_pago=metodos_pago,
            usuario=request.user,
            venta_id=venta_id,
        )

        saldo = 0.0
        estado_venta = ""
        
        if pago.venta:
            # Calcular usando regla de PagoService
            saldo = _to_float(PagoService._calcular_saldo_pendiente_venta(pago.venta))
            estado_venta = pago.venta.estado

        response_data = _build_pago_response(pago, saldo, estado_venta)

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_201_CREATED)


class PagoMixtoAPIView(APIView):
    """
    POST /api/pagos/mixto/
    Registra un pago con múltiples métodos o pagos fraccionados.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        serializer = PagoMixtoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        venta_id = serializer.validated_data['venta_id']
        metodos_pago = serializer.validated_data['metodos_pago']

        # Llamada al Service de Dominio
        pago = PagoService.registrar_pago_mixto(
            venta_id=venta_id,
            metodos_pago=metodos_pago,
            usuario=request.user,
        )

        saldo = 0.0
        estado_venta = ""
        
        if pago.venta:
            if pago.venta.tipo_venta == Venta.TipoVenta.CREDITO:
                saldo = _to_float(PagoService._calcular_saldo_pendiente_venta(pago.venta))
            estado_venta = pago.venta.estado

        response_data = _build_pago_response(pago, saldo, estado_venta)

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_201_CREATED)


class PagoInicialAPIView(APIView):
    """
    POST /api/pagos/inicial/
    Registra un anticipo (pago inicial) para una venta a crédito.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, *args, **kwargs):
        serializer = PagoInicialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        venta_id = serializer.validated_data['venta_id']
        metodos_pago = serializer.validated_data['metodos_pago']

        # Llamada al Service de Dominio
        pago = PagoService.registrar_pago_inicial(
            venta_id=venta_id,
            metodos_pago=metodos_pago,
            usuario=request.user,
        )

        saldo = 0.0
        estado_venta = ""
        
        if pago.venta:
            saldo = _to_float(PagoService._calcular_saldo_pendiente_venta(pago.venta))
            estado_venta = pago.venta.estado

        response_data = _build_pago_response(pago, saldo, estado_venta)

        return Response({
            "success": True,
            "data": response_data,
        }, status=status.HTTP_201_CREATED)
