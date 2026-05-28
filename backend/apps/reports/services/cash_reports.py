from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    Sum,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404

from apps.cash.models import Caja, MovimientoCaja
from apps.reports.dto import (
    CajaResumenDTO,
    CorteCajaDTO,
    DiferenciaAcumuladaDTO,
    UsuarioCajaDTO,
)

_ZERO = Decimal('0.00')
_Q2 = Decimal('0.01')


class CashReportService:
    """
    Servicio de reportes de caja — lectura pura.

    Reglas:
    - Sin escrituras.
    - Sin transaction.atomic.
    - Retorna DTOs.
    - Decimal quantizado a 0.01.
    - No recalcular cierres (usar valores almacenados en Caja).
    """

    # ------------------------------------------------------------------
    # 1. Resumen de una caja específica (Arqueo)
    # ------------------------------------------------------------------

    @staticmethod
    def resumen_caja(caja_id: int) -> CajaResumenDTO:
        """
        Obtiene el detalle completo de una caja, incluyendo
        totales calculados de movimientos y valores de cierre almacenados.
        """
        caja = get_object_or_404(
            Caja.objects.select_related('usuario_apertura', 'usuario_cierre'),
            pk=caja_id
        )

        # Agregar movimientos por método de pago (solo entradas suman al arqueo de efectivo/tarjeta)
        # Nota: El saldo teórico se debe calcular:
        # Saldo Teórico Efectivo = Monto Inicial + Entradas Efectivo - Salidas Efectivo
        # Pero aquí piden "total_entradas_por_metodo".
        # Vamos a desglosar entradas y salidas generales.

        movs_agg = caja.movimientos.aggregate(
            entradas_efectivo=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(
                        tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                        metodo_pago=MovimientoCaja.MetodoPago.EFECTIVO
                    )
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            entradas_tarjeta=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(
                        tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                        metodo_pago=MovimientoCaja.MetodoPago.TARJETA
                    )
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            entradas_transferencia=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(
                        tipo=MovimientoCaja.TipoMovimiento.ENTRADA,
                        metodo_pago=MovimientoCaja.MetodoPago.TRANSFERENCIA
                    )
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            total_salidas=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(tipo=MovimientoCaja.TipoMovimiento.SALIDA)
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )

        entradas_efe = Decimal(str(movs_agg['entradas_efectivo'])).quantize(_Q2)
        entradas_tar = Decimal(str(movs_agg['entradas_tarjeta'])).quantize(_Q2)
        entradas_tra = Decimal(str(movs_agg['entradas_transferencia'])).quantize(_Q2)
        salidas = Decimal(str(movs_agg['total_salidas'])).quantize(_Q2)
        total_entradas = entradas_efe + entradas_tar + entradas_tra
        flujo_neto = (total_entradas - salidas).quantize(_Q2)
        monto_inicial = Decimal(str(caja.monto_inicial)).quantize(_Q2)

        # Valores de cierre (pueden ser None si la caja está abierta)
        def _q(val):
            return Decimal(str(val)).quantize(_Q2) if val is not None else None

        return CajaResumenDTO(
            caja_id=caja.pk,
            usuario_apertura=caja.usuario_apertura.get_full_name() or caja.usuario_apertura.username,
            usuario_cierre=(
                caja.usuario_cierre.get_full_name() or caja.usuario_cierre.username
            ) if caja.usuario_cierre else None,
            estado=caja.get_estado_display(),
            monto_inicial=monto_inicial,
            total_entradas_efectivo=entradas_efe,
            total_entradas_tarjeta=entradas_tar,
            total_entradas_transferencia=entradas_tra,
            total_salidas=salidas,
            flujo_neto=flujo_neto,
            # Esperados
            total_efectivo_esperado=_q(caja.total_efectivo_esperado),
            total_tarjeta_esperado=_q(caja.total_tarjeta_esperado),
            total_transferencia_esperado=_q(caja.total_transferencia_esperado),
            # Declarados
            total_efectivo_declarado=_q(caja.total_efectivo_contado),
            total_tarjeta_declarado=_q(caja.total_tarjeta_declarado),
            total_transferencia_declarado=_q(caja.total_transferencia_declarado),
            # Diferencias
            diferencia_efectivo=_q(caja.diferencia_efectivo),
            diferencia_tarjeta=_q(caja.diferencia_tarjeta),
            diferencia_transferencia=_q(caja.diferencia_transferencia),
        )

    # ------------------------------------------------------------------
    # 2. Cortes acumulados por rango
    # ------------------------------------------------------------------

    @staticmethod
    def cortes_por_rango(
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> CorteCajaDTO:
        """
        Totales acumulados de cajas CERRADAS en el rango.
        """
        qs = Caja.objects.filter(
            estado=Caja.Estado.CERRADA,
            fecha_cierre__range=(fecha_inicio, fecha_fin)
        )

        agg = qs.aggregate(
            total_cajas=Count('id'),
            sum_esperado_efectivo=Coalesce(Sum('total_efectivo_esperado'), _ZERO, output_field=DecimalField()),
            sum_contado_efectivo=Coalesce(Sum('total_efectivo_contado'), _ZERO, output_field=DecimalField()),
            sum_dif_efectivo=Coalesce(Sum('diferencia_efectivo'), _ZERO, output_field=DecimalField()),
            sum_dif_tarjeta=Coalesce(Sum('diferencia_tarjeta'), _ZERO, output_field=DecimalField()),
            sum_dif_transferencia=Coalesce(Sum('diferencia_transferencia'), _ZERO, output_field=DecimalField()),
        )

        return CorteCajaDTO(
            total_cajas=agg['total_cajas'],
            total_efectivo_esperado=Decimal(str(agg['sum_esperado_efectivo'])).quantize(_Q2),
            total_efectivo_contado=Decimal(str(agg['sum_contado_efectivo'])).quantize(_Q2),
            diferencia_efectivo=Decimal(str(agg['sum_dif_efectivo'])).quantize(_Q2),
            diferencia_tarjeta=Decimal(str(agg['sum_dif_tarjeta'])).quantize(_Q2),
            diferencia_transferencia=Decimal(str(agg['sum_dif_transferencia'])).quantize(_Q2),
        )

    # ------------------------------------------------------------------
    # 3. Análisis de diferencias acumuladas
    # ------------------------------------------------------------------

    @staticmethod
    def diferencias_acumuladas() -> DiferenciaAcumuladaDTO:
        """
        Análisis histórico de todas las diferencias registradas (sobrantes/faltantes).
        """
        # Solo cajas cerradas tienen diferencias calculadas
        qs = Caja.objects.filter(estado=Caja.Estado.CERRADA)

        agg = qs.aggregate(
            dif_efe=Coalesce(Sum('diferencia_efectivo'), _ZERO, output_field=DecimalField()),
            dif_tar=Coalesce(Sum('diferencia_tarjeta'), _ZERO, output_field=DecimalField()),
            dif_tra=Coalesce(Sum('diferencia_transferencia'), _ZERO, output_field=DecimalField()),
            # Contar cajas donde diferencia_efectivo != 0
            cajas_con_dif=Count(
                'id',
                filter=~models.Q(diferencia_efectivo=0)
            ),
            prom_dif_efe=Coalesce(Avg('diferencia_efectivo'), _ZERO, output_field=DecimalField()),
        )

        return DiferenciaAcumuladaDTO(
            total_diferencia_efectivo=Decimal(str(agg['dif_efe'])).quantize(_Q2),
            total_diferencia_tarjeta=Decimal(str(agg['dif_tar'])).quantize(_Q2),
            total_diferencia_transferencia=Decimal(str(agg['dif_tra'])).quantize(_Q2),
            cantidad_cajas_con_diferencia=agg['cajas_con_dif'],
            promedio_diferencia_efectivo=Decimal(str(agg['prom_dif_efe'])).quantize(_Q2),
        )

    # ------------------------------------------------------------------
    # 4. Ingresos por usuario
    # ------------------------------------------------------------------

    @staticmethod
    def ingresos_por_usuario(
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
    ) -> list[UsuarioCajaDTO]:
        """
        Rendimiento por usuario basado en movimientos de caja.
        """
        qs = MovimientoCaja.objects.all()

        if fecha_inicio:
            qs = qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha__lte=fecha_fin)

        # Agrupar por usuario
        stats = (
            qs.values('usuario__id', 'usuario__first_name', 'usuario__last_name', 'usuario__username')
            .annotate(
                total_entradas=Coalesce(
                    Sum(
                        'monto',
                        filter=models.Q(tipo=MovimientoCaja.TipoMovimiento.ENTRADA)
                    ),
                    _ZERO,
                    output_field=DecimalField(),
                ),
                total_salidas=Coalesce(
                    Sum(
                        'monto',
                        filter=models.Q(tipo=MovimientoCaja.TipoMovimiento.SALIDA)
                    ),
                    _ZERO,
                    output_field=DecimalField(),
                ),
                count=Count('id'),
            )
            # Ordenamos en Python o via annotate extra para flujo neto,
            # pero Django ORM permite ordenar por operación en annotate si se define.
        )

        resultado = []
        for item in stats:
            entradas = Decimal(str(item['total_entradas']))
            salidas = Decimal(str(item['total_salidas']))
            flujo = entradas - salidas
            
            # Nombre: first + last, o username si vacíos
            nombre = f"{item['usuario__first_name']} {item['usuario__last_name']}".strip()
            if not nombre:
                nombre = item['usuario__username']

            resultado.append(UsuarioCajaDTO(
                usuario_id=item['usuario__id'],
                nombre=nombre,
                total_entradas=entradas.quantize(_Q2),
                total_salidas=salidas.quantize(_Q2),
                flujo_neto=flujo.quantize(_Q2),
                total_movimientos=item['count'],
            ))

        # Ordenar descendente por flujo neto
        resultado.sort(key=lambda x: x.flujo_neto, reverse=True)

        return resultado
