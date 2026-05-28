from django.utils import timezone
import datetime

from apps.api.utils.date_parser import get_local_now, get_local_isoformat

class ReporteBaseMixin:
    """
    Provee el generador estructural de metadatos del Reporte estandarizando
    el contrato JSON exigido para los reportes API hacia Frontend.
    """
    
    def _build_meta(self, fecha_inicio: datetime.datetime | None, fecha_fin: datetime.datetime | None) -> dict:
        """
        Construye información inofensiva de auditoria API.
        Formato de fechas dictado en str isoformat() convertido a
        hora local (settings.TIME_ZONE) para su correcta presentación.
        """
        # Convertimos todas las fechas a la hora local para evitar el desfase de +00:00 (UTC)
        # Esto ocurre 100% en la capa de respuesta de API sin alterar a la Base de Datos.
        now = get_local_now()
        
        fi_str = get_local_isoformat(fecha_inicio)
        ff_str = get_local_isoformat(fecha_fin)
        
        return {
            "fecha_inicio": fi_str,
            "fecha_fin": ff_str,
            "generado_en": now.isoformat()
        }
