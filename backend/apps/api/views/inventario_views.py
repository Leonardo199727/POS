from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.inventory.models import Inventario, MovimientoInventario
from apps.api.serializers.inventario_serializer import (
    StockCriticoSerializer,
    UpdateStockSerializer,
)
from apps.api.pagination import CustomPagination


class StockCriticoPagination(CustomPagination):
    """Paginación de 10 elementos para la vista de Stock Crítico."""
    page_size = 10


class StockCriticoListAPIView(generics.ListAPIView):
    """
    GET /api/inventario/stock-critico/

    Devuelve los registros de inventario cuyo stock_actual
    es menor o igual a su stock_minimo, ordenados del más
    crítico al menos crítico.

    Query params:
        - search: filtra por nombre de producto o código interno.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = StockCriticoSerializer
    pagination_class = StockCriticoPagination

    def get_queryset(self):
        qs = (
            Inventario.objects
            .filter(stock_actual__lte=F('stock_minimo'))
            .select_related('variante__producto')
            .order_by('stock_actual')
        )
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(variante__producto__nombre__icontains=search) |
                Q(variante__producto__codigo_interno__icontains=search)
            )
        return qs


class UpdateStockAPIView(generics.UpdateAPIView):
    """
    PATCH /api/inventario/{pk}/stock/

    Actualiza únicamente el stock_actual de un registro de inventario.
    Registra un MovimientoInventario de tipo 'ajuste_manual' como
    auditoría del cambio.

    Body (JSON):
        { "stock_actual": <int ≥ 0> }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateStockSerializer
    http_method_names = ['patch']
    queryset = Inventario.objects.select_related('variante__producto')

    @transaction.atomic
    def perform_update(self, serializer):
        inventario = self.get_object()
        nuevo_stock = serializer.validated_data['stock_actual']
        stock_anterior = inventario.stock_actual
        diferencia = nuevo_stock - stock_anterior

        # Actualizar stock
        inventario.stock_actual = nuevo_stock
        inventario.save(update_fields=['stock_actual', 'updated_at'])

        # Registrar movimiento de auditoría
        MovimientoInventario.objects.create(
            inventario=inventario,
            variante=inventario.variante,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE_MANUAL,
            cantidad=diferencia,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            referencia_tipo=MovimientoInventario.ReferenciaTipo.AJUSTE,
            motivo='Ajuste manual desde Stock Crítico',
            usuario=self.request.user,
            fecha=timezone.now(),
        )

    def patch(self, request, *args, **kwargs):
        inventario = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                'id': inventario.pk,
                'stock_actual': inventario.stock_actual,
                'message': 'Stock actualizado correctamente.',
            },
            status=status.HTTP_200_OK,
        )


