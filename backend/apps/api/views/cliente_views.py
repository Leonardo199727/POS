from decimal import Decimal

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from apps.payments.services.pago_service import PagoService
from apps.customers.services.cliente_service import ClienteService
from apps.customers.models import Cliente
from apps.api.permissions import IsAdminOrVendedor
from apps.api.pagination import CustomPagination
from apps.api.serializers.cliente_serializer import (
    ClienteListSerializer,
    ClienteCreateSerializer,
    ClienteUpdateSerializer,
)


def _to_float(val) -> float:
    """Convierte Decimal/str a float para serialización JSON."""
    if val is None:
        return 0.0
    return float(Decimal(str(val)))


class ClienteListAPIView(generics.ListAPIView):
    """
    GET /api/clientes/
    GET /api/clientes/?search=mata

    Lista paginada de clientes activos con búsqueda opcional.
    Soporta búsqueda por ID (exacto) y por nombre (parcial, case-insensitive).
    Usa CustomPagination (6 resultados por página, formato {success, data, meta}).
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]
    serializer_class = ClienteListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Retorna clientes activos, opcionalmente filtrados por el parámetro 'search'.
        - Si search es numérico, filtra por ID exacto O nombre parcial.
        - Si search es texto, filtra por nombre parcial (icontains).
        """
        qs = Cliente.objects.filter(activo=True)

        search = self.request.query_params.get('search', '').strip()
        if search:
            filters = Q(nombre__icontains=search)
            if search.isdigit():
                filters |= Q(id=int(search))
            qs = qs.filter(filters)

        return qs.order_by('id')


class ClienteCreateAPIView(generics.CreateAPIView):
    """
    POST /api/clientes/crear/

    Crea un nuevo cliente en el sistema.
    Campos requeridos: nombre.
    Campos opcionales: telefono, email, direccion, tipo_cliente, limite_credito.

    Retorna el cliente creado con su ID asignado (HTTP 201).
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]
    serializer_class = ClienteCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cliente = serializer.save()

        response_serializer = ClienteListSerializer(cliente)
        return Response(
            {
                'success': True,
                'message': f'Cliente "{cliente.nombre}" creado exitosamente.',
                'data': response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ClienteUpdateAPIView(generics.RetrieveUpdateAPIView):
    """
    PATCH /api/clientes/<id>/

    Actualiza parcialmente un cliente existente.
    Solo se envían los campos que se desean modificar.

    Retorna el cliente actualizado con HTTP 200.
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]
    serializer_class = ClienteUpdateSerializer
    queryset = Cliente.objects.filter(activo=True)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        # Seguridad: Vendedores NO pueden modificar el límite de crédito
        data = request.data.copy()
        rol_nombre = getattr(request.user.rol, 'nombre', '')
        if rol_nombre == 'VENDEDOR' and 'limite_credito' in data:
            data.pop('limite_credito')

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        cliente = serializer.save()

        response_serializer = ClienteListSerializer(cliente)
        return Response(
            {
                'success': True,
                'message': f'Cliente "{cliente.nombre}" actualizado exitosamente.',
                'data': response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ClienteAbonoAPIView(APIView):
    """
    POST /api/clientes/<id>/abono/
    Registra un abono libre a la cuenta del cliente (reduce la deuda actual).
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, pk, *args, **kwargs):
        metodos_pago = request.data.get('metodos_pago')
        if not metodos_pago or not isinstance(metodos_pago, list):
            return Response(
                {"detail": "Debe proporcionar una lista 'metodos_pago' válida con método y monto."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Llama a la capa de dominio, que encapsula la lógica de reducir saldo y generar MovimientoCredito
        pago = PagoService.registrar_pago_credito(
            cliente_id=pk,
            metodos_pago=metodos_pago,
            usuario=request.user,
            venta_id=None
        )

        # Refrescar el cliente para obtener el saldo actualizado
        cliente = Cliente.objects.get(pk=pk)

        return Response(
            {
                "success": True,
                "message": f"Abono de ${pago.monto_cliente} registrado exitosamente.",
                "data": {
                    "pago_id": pago.id,
                    "folio": f"P-{pago.id:05d}",
                    "monto_cliente": _to_float(pago.monto_cliente),
                    "cargo_tarjeta": _to_float(pago.cargo_tarjeta),
                    "total_cobrado": _to_float(pago.total_cobrado),
                    "saldo_nuevo": _to_float(cliente.saldo_actual),
                    "saldo_anterior": _to_float(cliente.saldo_actual + pago.monto_cliente),
                }
            },
            status=status.HTTP_201_CREATED,
        )


class ClienteCargoAPIView(APIView):
    """
    POST /api/clientes/<id>/cargo/
    Aplica un cargo o ajuste manual a la cuenta del cliente (aumenta la deuda actual).
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def post(self, request, pk, *args, **kwargs):
        monto = request.data.get('monto')
        concepto = request.data.get('concepto')
        
        # El validador se propaga y DRF captura ValidationError nativo
        movimiento = ClienteService.registrar_cargo_manual(
            cliente_id=pk,
            monto=monto,
            concepto=concepto,
            usuario=request.user
        )

        return Response(
            {
                "success": True,
                "message": f"Cargo manual por ${movimiento.monto} aplicado.",
                "data": {
                    "movimiento_id": movimiento.id,
                    "monto": _to_float(movimiento.monto),
                    "concepto": movimiento.descripcion,
                    "saldo_anterior": _to_float(movimiento.saldo_anterior),
                    "saldo_nuevo": _to_float(movimiento.saldo_nuevo),
                }
            },
            status=status.HTTP_201_CREATED,
        )


class ClienteMovimientosAPIView(APIView):
    """
    GET /api/clientes/<id>/movimientos/
    Obtiene el historial de movimientos recientes (Cargos, Abonos, Ventas a Crédito).
    CQRS Read Model: Utiliza la forma simplificada generada por la capa de dominio.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        limit_param = request.query_params.get('limite', '50')
        limite = int(limit_param) if limit_param.isdigit() else 50
        
        # El servicio encapsula la lógica de obtener, ordenar y unificarlos en DTOs amigables a la UI
        movimientos = ClienteService.obtener_movimientos_recientes(cliente_id=pk, limite=limite)
        
        return Response(
            {
                "success": True,
                "data": movimientos
            },
            status=status.HTTP_200_OK
        )
