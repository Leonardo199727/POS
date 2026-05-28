from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import (
    Count,
    DecimalField,
    Sum,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.customers.models import Cliente, MovimientoCredito
from apps.reports.dto import (
    CarteraGeneralDTO,
    ClienteSaldoDTO,
    EstadoCuentaClienteDTO,
    MovimientoEstadoCuentaDTO,
    TopClienteCreditoDTO,
)

_ZERO = Decimal('0.00')
_Q2 = Decimal('0.01')


class CreditReportService:
    """
    Servicio de reportes de crédito — lectura pura.

    Fuente de verdad: MovimientoCredito (ledger).
    Reglas:
    - Sin escrituras.
    - Sin transaction.atomic.
    - Retorna DTOs.
    - Decimal quantizado a 0.01.
    """

    # ------------------------------------------------------------------
    # 1. Estado general de la cartera
    # ------------------------------------------------------------------

    @staticmethod
    def estado_cartera_general(
        *,
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
    ) -> CarteraGeneralDTO:
        """
        Calcula el estado global de la cartera de crédito.

        - total_credito_colocado: Sum(cargos)
        - total_recuperado: Sum(abonos)
        - saldo_cartera: Colocado - Recuperado
        - total_clientes_con_deuda: Clientes con saldo_actual > 0
        - total_movimientos: Total de registros en ledger

        Permite filtrado opcional por fechas para análisis histórico
        (aunque el saldo_cartera es el "histórico acumulado" en ese rango).
        """
        qs = MovimientoCredito.objects.all()

        if fecha_inicio:
            qs = qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha__lte=fecha_fin)

        # ── Agregados ──
        agg = qs.aggregate(
            total_cargos=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(tipo=MovimientoCredito.TipoMovimiento.CARGO_VENTA)
                    | models.Q(tipo=MovimientoCredito.TipoMovimiento.AJUSTE),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            total_abonos=Coalesce(
                Sum(
                    'monto',
                    filter=models.Q(tipo=MovimientoCredito.TipoMovimiento.ABONO_PAGO),
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
            count=Count('id'),
        )

        # Nota: "total_clientes_con_deuda" se refiere al estado ACTUAL,
        # independientemente del rango de fechas de movimientos consultado.
        # Si se requiere histórico, sería más complejo (reconstruir saldos).
        # Asumimos estado actual de Clientes.
        clientes_con_deuda = Cliente.objects.filter(saldo_actual__gt=0).count()

        colocado = Decimal(str(agg['total_cargos'])).quantize(_Q2)
        recuperado = Decimal(str(agg['total_abonos'])).quantize(_Q2)
        saldo_cartera = (colocado - recuperado).quantize(_Q2)

        return CarteraGeneralDTO(
            total_credito_colocado=colocado,
            total_recuperado=recuperado,
            saldo_cartera=saldo_cartera,
            total_clientes_con_deuda=clientes_con_deuda,
            total_movimientos=agg['count'],
        )

    # ------------------------------------------------------------------
    # 2. Estado de cuenta de cliente
    # ------------------------------------------------------------------

    @staticmethod
    def estado_cuenta_cliente(cliente_id: int) -> EstadoCuentaClienteDTO:
        """
        Retorna el historial completo del cliente:
        - Movimientos de crédito (compras a crédito, pagos, ajustes).
        - Ventas de contado.
        """
        cliente = get_object_or_404(Cliente, pk=cliente_id)

        # ── 1. Obtener Movimientos de Crédito ──
        movimientos_qs = (
            MovimientoCredito.objects
            .filter(cliente_id=cliente_id)
            .select_related('venta', 'pago')
            .prefetch_related(
                'venta__detalles',
                'venta__detalles__variante',
                'venta__detalles__variante__producto',
                'pago__detalles',
            )
            .order_by('fecha', 'id')
            .distinct()
        )

        METODO_PAGO_MAP = {
            'efectivo': 'Efectivo',
            'tarjeta': 'Tarjeta',
            'transferencia': 'Transferencia',
        }

        # Estructura temporal para ordenar cronológicamente
        eventos = []
        seen_ids = set()

        for mov in movimientos_qs:
            if mov.id in seen_ids:
                continue
            seen_ids.add(mov.id)

            referencia = ''
            detalle = ''
            metodo = ''
            tipo_amigable = ''

            # CARGO (Venta a Crédito)
            if mov.tipo == MovimientoCredito.TipoMovimiento.CARGO_VENTA:
                tipo_amigable = 'Compra a Crédito'
                metodo = ''
                
                if mov.venta:
                    folio_str = str(mov.venta.folio)
                    referencia = folio_str if '-' in folio_str else f'V-{folio_str.zfill(5)}'
                    
                    nombres = []
                    for det in mov.venta.detalles.all():
                        nom = str(det.variante.producto.nombre)
                        if det.cantidad > 1:
                            nom = f"{det.cantidad} x {nom}"
                        nombres.append(nom)
                    detalle = ", ".join(nombres) if nombres else "Compra de productos"
                else:
                    referencia = 'Venta s/ref'
                    detalle = 'Compra'

            # ABONO (Pago)
            elif mov.tipo == MovimientoCredito.TipoMovimiento.ABONO_PAGO:
                tipo_amigable = 'Pago / Abono'
                detalle = 'Abono a cuenta'
                
                if mov.pago:
                    referencia = f'P-{str(mov.pago.pk).zfill(5)}'
                    
                    metodos_usados = set()
                    for det in mov.pago.detalles.all():
                        lbl = METODO_PAGO_MAP.get(det.metodo_pago, det.metodo_pago)
                        metodos_usados.add(lbl)
                    metodo = ", ".join(sorted(metodos_usados))
                else:
                    referencia = 'Pago s/ref'
                    metodo = 'Desconocido'

            # AJUSTE / OTROS
            elif mov.tipo == MovimientoCredito.TipoMovimiento.AJUSTE:
                tipo_amigable = 'Ajuste / Cargo'
                referencia = 'AJUSTE'
                detalle = mov.descripcion or 'Ajuste de saldo'
                metodo = ''
            
            else:
                tipo_amigable = mov.get_tipo_display()
                detalle = mov.descripcion or ''

            monto = Decimal(str(mov.monto)).quantize(_Q2)
            saldo = Decimal(str(mov.saldo_nuevo)).quantize(_Q2)

            eventos.append({
                'fecha_dt': mov.fecha,
                'es_credito': True,
                'movimiento': tipo_amigable,
                'detalle': detalle,
                'metodo': metodo,
                'monto': monto,
                'saldo': saldo,
                'referencia': referencia,
            })

        # ── 2. Obtener Ventas de Contado ──
        # Importamos Venta aquí para evitar dependencias circulares si es necesario,
        from apps.sales.models import Venta
        ventas_contado_qs = (
            Venta.objects
            .filter(cliente_id=cliente_id, tipo_venta=Venta.TipoVenta.CONTADO)
            .prefetch_related('detalles', 'detalles__variante__producto')
        )

        for vc in ventas_contado_qs:
            folio_str = str(vc.folio)
            referencia = folio_str if '-' in folio_str else f'V-{folio_str.zfill(5)}'
            
            nombres = []
            for det in vc.detalles.all():
                nom = str(det.variante.producto.nombre)
                if det.cantidad > 1:
                    nom = f"{det.cantidad} x {nom}"
                nombres.append(nom)
            detalle = ", ".join(nombres) if nombres else "Compra de productos"
            
            # Una venta de contado idealmente tiene sus pagos, pero por simplicidad
            # lo listamos como "Venta Contado" y método "Mismo folio".
            eventos.append({
                'fecha_dt': vc.created_at,
                'es_credito': False,
                'movimiento': 'Compra de Contado',
                'detalle': detalle,
                'metodo': 'Contado',  # O podríamos rastear el Pago exacto para el método, pero para UX es suficiente.
                'monto': Decimal(str(vc.total)).quantize(_Q2),
                'saldo': None,  # Se calcula después
                'referencia': referencia,
            })

        # ── 3. Ordenar y calcular saldos de arrastre ──
        eventos.sort(key=lambda x: x['fecha_dt'])
        
        movimientos_dtos: list[MovimientoEstadoCuentaDTO] = []
        saldo_arrastre = _ZERO
        
        for ev in eventos:
            if ev['es_credito']:
                saldo_arrastre = ev['saldo']
            
            movimientos_dtos.append(MovimientoEstadoCuentaDTO(
                fecha=ev['fecha_dt'].strftime('%d/%m/%Y'),
                movimiento=ev['movimiento'],
                detalle=ev['detalle'],
                metodo=ev['metodo'],
                monto=ev['monto'],
                saldo=saldo_arrastre,
                referencia=ev['referencia'],
            ))

        saldo_actual = Decimal(str(cliente.saldo_actual)).quantize(_Q2)
        fecha_gen = timezone.now().strftime('%d/%m/%Y %H:%M')

        return EstadoCuentaClienteDTO(
            cliente_id=cliente.pk,
            nombre_cliente=cliente.nombre,
            telefono=cliente.telefono if cliente.telefono else '',
            direccion=cliente.direccion if cliente.direccion else '',
            saldo_actual=saldo_actual,
            fecha_generacion=fecha_gen,
            movimientos=movimientos_dtos,
        )

    # ------------------------------------------------------------------
    # 3. Clientes con saldo pendiente
    # ------------------------------------------------------------------

    @staticmethod
    def clientes_con_saldo_pendiente() -> list[ClienteSaldoDTO]:
        """
        Lista de clientes que actualmente tienen deuda (saldo_actual > 0).
        Ordenados de mayor a menor deuda.
        """
        clientes = (
            Cliente.objects
            .filter(saldo_actual__gt=0)
            .order_by('-saldo_actual')
            .values('id', 'nombre', 'saldo_actual', 'limite_credito')
        )

        resultado = []
        for c in clientes:
            resultado.append(ClienteSaldoDTO(
                cliente_id=c['id'],
                nombre=c['nombre'],
                saldo_actual=Decimal(str(c['saldo_actual'])).quantize(_Q2),
                limite_credito=Decimal(str(c['limite_credito'])).quantize(_Q2),
            ))

        return resultado

    # ------------------------------------------------------------------
    # 4. Top clientes por crédito
    # ------------------------------------------------------------------

    @staticmethod
    def top_clientes_por_credito(limit: int = 10) -> list[TopClienteCreditoDTO]:
        """
        Top N clientes que más crédito han utilizado (suma de cargos).
        Independientemente de si ya pagaron o no.
        """
        # Agrupar por cliente, sumar 'monto' donde tipo='cargo'
        top_clientes = (
            MovimientoCredito.objects
            .filter(tipo=MovimientoCredito.TipoMovimiento.CARGO_VENTA)
            .values('cliente__id', 'cliente__nombre')
            .annotate(
                total_credito=Sum('monto'),
                cantidad_cargos=Count('id')
            )
            .order_by('-total_credito')[:limit]
        )

        resultado = []
        for item in top_clientes:
            resultado.append(TopClienteCreditoDTO(
                cliente_id=item['cliente__id'],
                nombre=item['cliente__nombre'],
                total_credito=Decimal(str(item['total_credito'])).quantize(_Q2),
                cantidad_cargos=item['cantidad_cargos'],
            ))

        return resultado
