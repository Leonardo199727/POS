import datetime
from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.reports.services.credit_reports import CreditReportService
from apps.reports.services.financial_reports import FinancialReportService
from apps.reports.services.sales_reports import SalesReportService
from apps.sales.models import Venta
from apps.payments.models import PagoDetalle

class DashboardService:
    """
    Servicio optimizado para proveer datos a dashboards (React, Vue, etc.).
    
    Reglas arquitectónicas:
    - Retorna dicts y listas con tipos de datos serializables (float, str, int).
    - No expone modelos de Django ni QuerySets.
    - No contiene lógica HTML o de vistas.
    - Reutiliza servicios de reporte existentes cuando es posible.
    - Convierte Decimal a float o strings serializables.
    """

    @staticmethod
    def _to_float(value: Any) -> float:
        """Convierte Decimal a float de forma segura para JSON."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _get_dates(
        fecha_inicio: datetime.datetime | None,
        fecha_fin: datetime.datetime | None,
    ) -> tuple[datetime.datetime, datetime.datetime]:
        """
        Calcula fechas seguras por defecto si no son provistas.
        Si no hay inicio, desde 2000-01-01.
        Si no hay fin, hasta ahora.
        """
        now = timezone.now()
        start = fecha_inicio or timezone.make_aware(datetime.datetime(2000, 1, 1))
        end = fecha_fin or now
        return start, end

    @staticmethod
    def estadisticas_rapidas() -> Dict[str, Any]:
        """
        Retorna los 4 KPIs principales para las tarjetas superiores del dashboard correspondientes al día actual.
        """
        from apps.customers.models import Cliente, MovimientoCredito
        from apps.inventory.models import Inventario
        from apps.sales.models import Venta
        from django.db.models import F, Case, When, IntegerField
        
        now = timezone.now()
        hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
        ayer_inicio = hoy_inicio - datetime.timedelta(days=1)
        
        # 1. Ventas de hoy vs ayer
        estados_validos = [Venta.Estado.COMPLETADA, Venta.Estado.PARCIAL, Venta.Estado.LIQUIDADA]
        ventas_hoy = Venta.objects.filter(
            created_at__gte=hoy_inicio,
            estado__in=estados_validos
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()))['total']
        
        ventas_ayer = Venta.objects.filter(
            created_at__gte=ayer_inicio,
            created_at__lt=hoy_inicio,
            estado__in=estados_validos
        ).aggregate(total=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()))['total']
        
        if ventas_ayer > 0:
            porcentaje_vs_ayer = ((ventas_hoy - ventas_ayer) / ventas_ayer) * 100
        else:
            porcentaje_vs_ayer = 100.0 if ventas_hoy > 0 else 0.0

        # 2. Clientes activos (Con movimientos recientes ó Ventas hoy)
        clientes_venta_hoy = list(Venta.objects.filter(created_at__gte=hoy_inicio).exclude(cliente__isnull=True).values_list('cliente_id', flat=True))
        clientes_mov_hoy = list(MovimientoCredito.objects.filter(fecha__gte=hoy_inicio).values_list('cliente_id', flat=True))
        clientes_activos = len(set(clientes_venta_hoy + clientes_mov_hoy))

        # 3. Items en Stock
        stock_agg = Inventario.objects.aggregate(
            total_items=Coalesce(Sum('stock_actual'), 0),
            bajo_critico=Sum(
                Case(
                    When(stock_actual__lte=F('stock_minimo'), then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )
        )
        total_items = stock_agg['total_items']
        bajo_stock_critico = stock_agg['bajo_critico'] or 0

        # 4. Utilidad Estimada (Hoy)
        utilidad_dto = FinancialReportService.utilidad_bruta_por_periodo(
            fecha_inicio=hoy_inicio,
            fecha_fin=now,
        )
        margen = 0.0
        if utilidad_dto.total_ventas > 0:
            margen = (utilidad_dto.utilidad_bruta / utilidad_dto.total_ventas) * 100

        return {
            "ventas_hoy": DashboardService._to_float(ventas_hoy),
            "ventas_vs_ayer_porcentaje": DashboardService._to_float(porcentaje_vs_ayer),
            "clientes_activos_hoy": clientes_activos,
            "items_en_stock": total_items,
            "items_bajo_stock_critico": bajo_stock_critico,
            "utilidad_estimada": DashboardService._to_float(utilidad_dto.utilidad_bruta),
            "utilidad_margen": DashboardService._to_float(margen),
        }

    @staticmethod
    def resumen_general(
        fecha_inicio: datetime.datetime | None = None,
        fecha_fin: datetime.datetime | None = None,
    ) -> Dict[str, float | int]:
        """
        KPIs principales para el dashboard.
        """
        start, end = DashboardService._get_dates(fecha_inicio, fecha_fin)

        utilidad_dto = FinancialReportService.utilidad_bruta_por_periodo(
            fecha_inicio=start,
            fecha_fin=end,
        )

        ingresos_dto = FinancialReportService.ingresos_por_metodo_pago(
            fecha_inicio=start,
            fecha_fin=end,
        )

        cartera_dto = CreditReportService.estado_cartera_general(
            fecha_inicio=start,
            fecha_fin=end,
        )

        return {
            "ventas_totales": DashboardService._to_float(utilidad_dto.total_ventas),
            "ingresos_totales": DashboardService._to_float(ingresos_dto.total_ingresos),
            "costo_total": DashboardService._to_float(utilidad_dto.costo_total),
            "utilidad_bruta": DashboardService._to_float(utilidad_dto.utilidad_bruta),
            "clientes_con_deuda": int(cartera_dto.total_clientes_con_deuda),
            "saldo_cartera": DashboardService._to_float(cartera_dto.saldo_cartera),
        }

    @staticmethod
    def ventas_por_dia(
        fecha_inicio: datetime.datetime | None = None,
        fecha_fin: datetime.datetime | None = None,
    ) -> Dict[str, List[str | float]]:
        """
        Ventas agrupadas por día para gráficas.
        """
        start, end = DashboardService._get_dates(fecha_inicio, fecha_fin)

        estados_validos = [
            Venta.Estado.COMPLETADA,
            Venta.Estado.PARCIAL,
            Venta.Estado.LIQUIDADA,
        ]

        ventas_diarias = (
            Venta.objects.filter(
                created_at__gte=start,
                created_at__lte=end,
                estado__in=estados_validos,
            )
            .annotate(dia=TruncDate('created_at'))
            .values('dia')
            .annotate(total_str=Coalesce(Sum('total'), Decimal('0.00'), output_field=DecimalField()))
            .order_by('dia')
        )

        labels = []
        data = []

        for v in ventas_diarias:
            if v['dia']:
                labels.append(v['dia'].strftime('%Y-%m-%d'))
                data.append(DashboardService._to_float(v['total_str']))

        return {
            "labels": labels,
            "data": data,
        }

    @staticmethod
    def ingresos_por_metodo(
        fecha_inicio: datetime.datetime | None = None,
        fecha_fin: datetime.datetime | None = None,
    ) -> Dict[str, List[str | float]]:
        """
        Ingresos desglosados por método de pago.
        """
        start, end = DashboardService._get_dates(fecha_inicio, fecha_fin)

        ingresos_dto = FinancialReportService.ingresos_por_metodo_pago(
            fecha_inicio=start,
            fecha_fin=end,
        )

        return {
            "labels": ["Efectivo", "Tarjeta", "Transferencia"],
            "data": [
                DashboardService._to_float(ingresos_dto.efectivo),
                DashboardService._to_float(ingresos_dto.tarjeta),
                DashboardService._to_float(ingresos_dto.transferencia),
            ],
        }

    @staticmethod
    def top_productos(
        fecha_inicio: datetime.datetime | None = None,
        fecha_fin: datetime.datetime | None = None,
        limit: int = 5,
    ) -> Dict[str, List[str | int]]:
        """
        Top N productos más vendidos.
        """
        start, end = DashboardService._get_dates(fecha_inicio, fecha_fin)

        top_dtos = SalesReportService.top_productos_vendidos(
            fecha_inicio=start,
            fecha_fin=end,
            limit=limit,
        )

        labels = []
        data = []

        for dto in top_dtos:
            labels.append(dto.nombre)
            data.append(int(dto.cantidad_vendida))

        return {
            "labels": labels,
            "data": data,
        }

    @staticmethod
    def cartera_resumen() -> Dict[str, float | int]:
        """
        Resumen general de cartera actual (sin rango de fechas).
        """
        # Según los requerimientos se debe retornar total_credito_colocado, 
        # total_recuperado, saldo_actual_cartera y clientes_con_saldo.
        
        cartera_dto = CreditReportService.estado_cartera_general()

        return {
            "total_credito_colocado": DashboardService._to_float(cartera_dto.total_credito_colocado),
            "total_recuperado": DashboardService._to_float(cartera_dto.total_recuperado),
            "saldo_actual_cartera": DashboardService._to_float(cartera_dto.saldo_cartera),
            "clientes_con_saldo": int(cartera_dto.total_clientes_con_deuda),
        }
