from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db.models import (
    Case,
    DecimalField,
    F,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from apps.products.models import PrecioProducto
from apps.reports.dto import SalesSummaryDTO, TopProductDTO
from apps.sales.models import DetalleVenta, Venta

# Estados que se consideran "ventas válidas" para reportes
_ESTADOS_VALIDOS = [
    Venta.Estado.COMPLETADA,
    Venta.Estado.PARCIAL,
    Venta.Estado.LIQUIDADA,
]

_ZERO = Decimal('0.00')
_Q2 = Decimal('0.01')


class SalesReportService:
    """
    Servicio de reportes de ventas — lectura pura.

    Reglas:
    - Sin escrituras a la base de datos.
    - Sin transaction.atomic.
    - Sin side effects.
    - Todos los montos son Decimal con 2 decimales.
    - Retorna DTOs, no dicts.
    """

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    @staticmethod
    def sales_summary(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        estados: list[str] | None = None,
    ) -> SalesSummaryDTO:
        """
        Resumen de ventas en un rango de fechas.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).
            estados: Lista de estados a incluir. Por defecto:
                     COMPLETADA, PARCIAL, LIQUIDADA.

        Returns:
            SalesSummaryDTO con totales y ticket promedio.
        """
        estados_filtro = estados or [e.value for e in _ESTADOS_VALIDOS]

        ventas = Venta.objects.filter(
            created_at__gte=fecha_inicio,
            created_at__lte=fecha_fin,
            estado__in=estados_filtro,
        )

        # ── Agregados en una sola query ──
        agg = ventas.aggregate(
            total_sales=Coalesce(
                Sum('total'), _ZERO, output_field=DecimalField(),
            ),
            total_contado=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo_venta=Venta.TipoVenta.CONTADO,
                            then=F('total'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            total_credito=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo_venta=Venta.TipoVenta.CREDITO,
                            then=F('total'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )

        total_sales = Decimal(str(agg['total_sales'])).quantize(_Q2)
        total_contado = Decimal(str(agg['total_contado'])).quantize(_Q2)
        total_credito = Decimal(str(agg['total_credito'])).quantize(_Q2)
        total_ventas = ventas.count()

        ticket_promedio = (
            (total_sales / total_ventas).quantize(_Q2)
            if total_ventas > 0
            else _ZERO
        )

        return SalesSummaryDTO(
            total_sales=total_sales,
            total_contado=total_contado,
            total_credito=total_credito,
            total_ventas=total_ventas,
            ticket_promedio=ticket_promedio,
        )

    @staticmethod
    def top_productos_vendidos(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
        limit: int = 10,
    ) -> list[TopProductDTO]:
        """
        Productos más vendidos en un rango de fechas.

        Agrupa por variante y calcula cantidad_vendida, total_generado
        y utilidad_generada (usando precio_compra vigente).

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).
            limit: Cantidad máxima de resultados (default 10).

        Returns:
            Lista de TopProductDTO ordenada por cantidad_vendida DESC.
        """
        estados_filtro = [e.value for e in _ESTADOS_VALIDOS]

        # ── Agrupar DetalleVenta por variante ──
        detalles = (
            DetalleVenta.objects
            .filter(
                venta__created_at__gte=fecha_inicio,
                venta__created_at__lte=fecha_fin,
                venta__estado__in=estados_filtro,
            )
            .values(
                'variante_id',
                'variante__producto__id',
                'variante__producto__nombre',
                'variante__nombre',
            )
            .annotate(
                cantidad_vendida=Sum('cantidad'),
                total_generado=Coalesce(
                    Sum('subtotal'), _ZERO,
                    output_field=DecimalField(),
                ),
            )
            .order_by('-cantidad_vendida')[:limit]
        )

        # ── Obtener precios de compra vigentes para utilidad ──
        variante_ids = [d['variante_id'] for d in detalles]

        precios_compra = {
            p['variante_id']: p['precio_compra']
            for p in PrecioProducto.objects.filter(
                variante_id__in=variante_ids,
                vigente=True,
            ).values('variante_id', 'precio_compra')
        }

        # ── Construir DTOs ──
        resultado: list[TopProductDTO] = []

        for detalle in detalles:
            variante_id = detalle['variante_id']
            producto_nombre = detalle['variante__producto__nombre']
            variante_nombre = detalle['variante__nombre']

            nombre = (
                f'{producto_nombre} — {variante_nombre}'
                if variante_nombre and variante_nombre != 'Default'
                else producto_nombre
            )

            cantidad = detalle['cantidad_vendida']
            total_gen = Decimal(str(detalle['total_generado'])).quantize(_Q2)

            # Utilidad: (precio_unitario_promedio - costo) * cantidad
            precio_compra = precios_compra.get(variante_id)

            if precio_compra is not None and cantidad > 0:
                costo = Decimal(str(precio_compra)).quantize(_Q2)
                utilidad = (
                    total_gen - (costo * cantidad)
                ).quantize(_Q2)
            else:
                utilidad = _ZERO

            resultado.append(TopProductDTO(
                producto_id=detalle['variante__producto__id'],
                nombre=nombre,
                cantidad_vendida=cantidad,
                total_generado=total_gen,
                utilidad_generada=utilidad,
            ))

        return resultado
