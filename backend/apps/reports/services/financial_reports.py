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

from apps.cash.models import MovimientoCaja
from apps.payments.models import Pago, PagoDetalle
from apps.products.models import PrecioProducto
from apps.reports.dto import CashFlowDTO, GrossProfitDTO, PaymentMethodSummaryDTO
from apps.sales.models import DetalleVenta, Venta

# Estados que se consideran "ventas válidas" para reportes
_ESTADOS_VALIDOS = [
    Venta.Estado.COMPLETADA,
    Venta.Estado.PARCIAL,
    Venta.Estado.LIQUIDADA,
]

_ZERO = Decimal('0.00')
_Q2 = Decimal('0.01')


class FinancialReportService:
    """
    Servicio de reportes financieros — lectura pura.

    Reglas:
    - Sin escrituras a la base de datos.
    - Sin transaction.atomic.
    - Sin side effects.
    - No llama a otros servicios.
    - Todos los montos son Decimal con 2 decimales.
    - Retorna DTOs, no dicts.
    """

    # ------------------------------------------------------------------
    # 1) Utilidad bruta por periodo
    # ------------------------------------------------------------------

    @staticmethod
    def utilidad_bruta_por_periodo(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> GrossProfitDTO:
        """
        Calcula la utilidad bruta en un rango de fechas.

        utilidad_bruta = total_ventas - costo_productos_vendidos

        Donde:
        - total_ventas = Sum(DetalleVenta.subtotal)
        - costo = Sum(precio_compra_vigente * cantidad)

        Si precio_compra es NULL, el costo se trata como 0.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            GrossProfitDTO con totales, utilidad bruta y margen.
        """
        estados_filtro = [e.value for e in _ESTADOS_VALIDOS]

        # ── Detalles agrupados por variante ──
        detalles = (
            DetalleVenta.objects
            .filter(
                venta__created_at__gte=fecha_inicio,
                venta__created_at__lte=fecha_fin,
                venta__estado__in=estados_filtro,
            )
            .values('variante_id')
            .annotate(
                total_generado=Coalesce(
                    Sum('subtotal'), _ZERO,
                    output_field=DecimalField(),
                ),
                cantidad_total=Sum('cantidad'),
            )
        )

        # ── Precios de compra vigentes en batch ──
        variante_ids = [d['variante_id'] for d in detalles]

        precios_compra = {
            p['variante_id']: p['precio_compra']
            for p in PrecioProducto.objects.filter(
                variante_id__in=variante_ids,
                vigente=True,
            ).values('variante_id', 'precio_compra')
        }

        # ── Calcular totales ──
        total_ventas = _ZERO
        costo_total = _ZERO

        for detalle in detalles:
            total_gen = Decimal(str(detalle['total_generado']))
            cantidad = detalle['cantidad_total']
            total_ventas += total_gen

            precio_compra = precios_compra.get(detalle['variante_id'])
            if precio_compra is not None:
                costo = Decimal(str(precio_compra))
                costo_total += costo * cantidad

        total_ventas = total_ventas.quantize(_Q2)
        costo_total = costo_total.quantize(_Q2)
        utilidad_bruta = (total_ventas - costo_total).quantize(_Q2)

        margen_porcentual = (
            ((utilidad_bruta / total_ventas) * 100).quantize(_Q2)
            if total_ventas > _ZERO
            else _ZERO
        )

        return GrossProfitDTO(
            total_ventas=total_ventas,
            costo_total=costo_total,
            utilidad_bruta=utilidad_bruta,
            margen_porcentual=margen_porcentual,
        )

    # ------------------------------------------------------------------
    # 2) Total ventas contado
    # ------------------------------------------------------------------

    @staticmethod
    def total_ventas_contado(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> Decimal:
        """
        Suma de Venta.total donde tipo_venta = CONTADO.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            Decimal quantizado a 0.01.
        """
        estados_filtro = [e.value for e in _ESTADOS_VALIDOS]

        total = Venta.objects.filter(
            created_at__gte=fecha_inicio,
            created_at__lte=fecha_fin,
            estado__in=estados_filtro,
            tipo_venta=Venta.TipoVenta.CONTADO,
        ).aggregate(
            total=Coalesce(
                Sum('total'), _ZERO,
                output_field=DecimalField(),
            ),
        )['total']

        return Decimal(str(total)).quantize(_Q2)

    # ------------------------------------------------------------------
    # 3) Total ventas crédito
    # ------------------------------------------------------------------

    @staticmethod
    def total_ventas_credito(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> Decimal:
        """
        Suma de Venta.total donde tipo_venta = CREDITO.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            Decimal quantizado a 0.01.
        """
        estados_filtro = [e.value for e in _ESTADOS_VALIDOS]

        total = Venta.objects.filter(
            created_at__gte=fecha_inicio,
            created_at__lte=fecha_fin,
            estado__in=estados_filtro,
            tipo_venta=Venta.TipoVenta.CREDITO,
        ).aggregate(
            total=Coalesce(
                Sum('total'), _ZERO,
                output_field=DecimalField(),
            ),
        )['total']

        return Decimal(str(total)).quantize(_Q2)

    # ------------------------------------------------------------------
    # 4) Ingresos por método de pago
    # ------------------------------------------------------------------

    @staticmethod
    def ingresos_por_metodo_pago(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> PaymentMethodSummaryDTO:
        """
        Suma de PagoDetalle.monto agrupada por metodo_pago.

        Mide dinero efectivamente cobrado, no facturado.
        Filtra por Pago.fecha.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            PaymentMethodSummaryDTO con desglose por método.
        """
        agg = PagoDetalle.objects.filter(
            pago__fecha__gte=fecha_inicio,
            pago__fecha__lte=fecha_fin,
        ).aggregate(
            efectivo=Coalesce(
                Sum(
                    Case(
                        When(
                            metodo_pago=PagoDetalle.MetodoPago.EFECTIVO,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            tarjeta=Coalesce(
                Sum(
                    Case(
                        When(
                            metodo_pago=PagoDetalle.MetodoPago.TARJETA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            transferencia=Coalesce(
                Sum(
                    Case(
                        When(
                            metodo_pago=PagoDetalle.MetodoPago.TRANSFERENCIA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )

        efectivo = Decimal(str(agg['efectivo'])).quantize(_Q2)
        tarjeta = Decimal(str(agg['tarjeta'])).quantize(_Q2)
        transferencia = Decimal(str(agg['transferencia'])).quantize(_Q2)
        total_ingresos = (efectivo + tarjeta + transferencia).quantize(_Q2)

        return PaymentMethodSummaryDTO(
            efectivo=efectivo,
            tarjeta=tarjeta,
            transferencia=transferencia,
            total_ingresos=total_ingresos,
        )

    # ------------------------------------------------------------------
    # 5) Costo financiero tarjeta
    # ------------------------------------------------------------------

    @staticmethod
    def costo_financiero_tarjeta(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> Decimal:
        """
        Suma de PagoDetalle.cargo_generado donde metodo_pago = TARJETA
        y con_intereses = True.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            Decimal quantizado a 0.01.
        """
        total = PagoDetalle.objects.filter(
            pago__fecha__gte=fecha_inicio,
            pago__fecha__lte=fecha_fin,
            metodo_pago=PagoDetalle.MetodoPago.TARJETA,
            con_intereses=True,
        ).aggregate(
            total=Coalesce(
                Sum('cargo_generado'), _ZERO,
                output_field=DecimalField(),
            ),
        )['total']

        return Decimal(str(total)).quantize(_Q2)

    # ------------------------------------------------------------------
    # 6) Flujo de efectivo real
    # ------------------------------------------------------------------

    @staticmethod
    def flujo_efectivo_real(
        *,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> CashFlowDTO:
        """
        Flujo de caja real desde MovimientoCaja: entradas - salidas,
        agrupado por método de pago.

        Args:
            fecha_inicio: Inicio del rango (inclusivo).
            fecha_fin: Fin del rango (inclusivo).

        Returns:
            CashFlowDTO con netos por método y flujo total.
        """
        movimientos = MovimientoCaja.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        )

        agg = movimientos.aggregate(
            # ── Efectivo ──
            efectivo_entradas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            efectivo_salidas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.SALIDA,
                            metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            # ── Tarjeta ──
            tarjeta_entradas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                            metodo_pago=MovimientoCaja.MetodoPago.TARJETA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            tarjeta_salidas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.SALIDA,
                            metodo_pago=MovimientoCaja.MetodoPago.TARJETA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            # ── Transferencia ──
            transferencia_entradas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                            metodo_pago=MovimientoCaja.MetodoPago.TRANSFERENCIA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            transferencia_salidas=Coalesce(
                Sum(
                    Case(
                        When(
                            tipo=MovimientoCaja.TipoMovimiento.SALIDA,
                            metodo_pago=MovimientoCaja.MetodoPago.TRANSFERENCIA,
                            then=F('monto'),
                        ),
                        default=Value(_ZERO),
                        output_field=DecimalField(),
                    ),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )

        efectivo_neto = (
            Decimal(str(agg['efectivo_entradas']))
            - Decimal(str(agg['efectivo_salidas']))
        ).quantize(_Q2)

        tarjeta_neto = (
            Decimal(str(agg['tarjeta_entradas']))
            - Decimal(str(agg['tarjeta_salidas']))
        ).quantize(_Q2)

        transferencia_neto = (
            Decimal(str(agg['transferencia_entradas']))
            - Decimal(str(agg['transferencia_salidas']))
        ).quantize(_Q2)

        flujo_total = (
            efectivo_neto + tarjeta_neto + transferencia_neto
        ).quantize(_Q2)

        return CashFlowDTO(
            efectivo_neto=efectivo_neto,
            tarjeta_neto=tarjeta_neto,
            transferencia_neto=transferencia_neto,
            flujo_total=flujo_total,
        )
