from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.api.permissions import IsAdminRole, IsAdminOrVendedor
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from apps.reports.services.financial_reports import FinancialReportService
from apps.reports.services.dashboard_service import DashboardService
from apps.reports.services.credit_reports import CreditReportService

from apps.api.views.mixins import ReporteBaseMixin
from apps.api.utils.date_parser import parse_fecha_inicio, parse_fecha_fin, get_local_now

class DashboardAPIView(APIView, ReporteBaseMixin):
    """
    GET /api/reportes/dashboard/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def get(self, request, *args, **kwargs):
        # 1. Parsing pasivo/seguro garantizando datetime awares
        fecha_inicio = parse_fecha_inicio(request)
        fecha_fin = parse_fecha_fin(request)
        
        # 2. Mixin inyector de MetaData contract-friendly
        meta = self._build_meta(fecha_inicio, fecha_fin)
        
        # 3. Consolidación de Servicios subyacentes intactos (Zero side effects/Lógica local)
        estadisticas = DashboardService.estadisticas_rapidas()
        
        # RBAC Check para Utilidad Estimada (Solo ADMIN puede ver)
        rol_nombre = getattr(request.user.rol, 'nombre', '') if hasattr(request.user, 'rol') else ''
        if rol_nombre != 'ADMIN':
            estadisticas["utilidad_estimada"] = None
            estadisticas["utilidad_margen"] = None

        data = {
            "estadisticas_rapidas": estadisticas,
            "resumen_general": DashboardService.resumen_general(fecha_inicio, fecha_fin),
            "ventas_por_dia": DashboardService.ventas_por_dia(fecha_inicio, fecha_fin),
            "ingresos_por_metodo": DashboardService.ingresos_por_metodo(fecha_inicio, fecha_fin),
            "top_productos": DashboardService.top_productos(fecha_inicio, fecha_fin),
            "cartera_resumen": DashboardService.cartera_resumen() 
            # cartera_resumen no recibe fechas por diseño del servicio original. Acepta kwargs si aplica a futuro. 
        }
        
        # 4. JSON unificado
        return Response({
            "success": True, 
            "data": data,
            "meta": meta
        }, status=status.HTTP_200_OK)


class EstadoCuentaClienteAPIView(APIView, ReporteBaseMixin):
    """
    GET /api/reportes/estado-cuenta/{cliente_id}/
    """
    permission_classes = [IsAuthenticated, IsAdminOrVendedor]

    def get(self, request, cliente_id, *args, **kwargs):
        try:
            reporte = CreditReportService.estado_cuenta_cliente(cliente_id=cliente_id)
            import dataclasses
            data = dataclasses.asdict(reporte) if dataclasses.is_dataclass(reporte) else getattr(reporte, "__dict__", str(reporte))
            
            # Mixin Meta (No acepta fechas este endpoint, solo inyecta el "generado_en")
            meta = self._build_meta(None, None)
            
            return Response({
                "success": True, 
                "data": data,
                "meta": meta
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReportesFinancierosAPIView(APIView, ReporteBaseMixin):
    """
    GET /api/reportes/financieros/
    Exclusivo ADMIN
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, *args, **kwargs):
        fecha_inicio = parse_fecha_inicio(request)
        fecha_fin = parse_fecha_fin(request)
        
        # fallback si la vista de utilidades de plano exige dates al servicio
        if not fecha_inicio or not fecha_fin:
            ahora = get_local_now()
            inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_inicio = fecha_inicio or inicio_mes
            fecha_fin = fecha_fin or ahora
            
        reporte = FinancialReportService.utilidad_bruta_por_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        import dataclasses
        data = dataclasses.asdict(reporte) if dataclasses.is_dataclass(reporte) else getattr(reporte, "__dict__", str(reporte))
        meta = self._build_meta(fecha_inicio, fecha_fin)
        
        return Response({
            "success": True, 
            "data": data,
            "meta": meta
        }, status=status.HTTP_200_OK)
