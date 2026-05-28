import datetime
from django.utils import timezone
from django.utils.dateparse import parse_date

def _safe_make_aware(dt: datetime.datetime) -> datetime.datetime:
    """Convierte un datetime naive a timezone aware, o lo deja así si ya lo es."""
    if timezone.is_aware(dt):
        return dt
    return timezone.make_aware(dt)

def parse_fecha_inicio(request) -> datetime.datetime | None:
    """
    Extrae 'fecha_inicio' de query params (YYYY-MM-DD).
    Retorna None si no existe o formato es inválido,
    garantizando que no reviente la pipeline financiera.
    Asume inicio orgánico a las 00:00:00.
    """
    fecha_str = request.query_params.get('fecha_inicio')
    if not fecha_str:
        return None
        
    parsed = parse_date(fecha_str)
    if not parsed:
        return None
        
    dt = datetime.datetime.combine(parsed, datetime.time.min)
    return _safe_make_aware(dt)

def parse_fecha_fin(request) -> datetime.datetime | None:
    """
    Extrae 'fecha_fin' de query params (YYYY-MM-DD).
    Retorna None si no existe o formato es inválido.
    Asume el fin del día (23:59:59.999999) para inclusión estricta.
    """
    fecha_str = request.query_params.get('fecha_fin')
    if not fecha_str:
        return None
        
    parsed = parse_date(fecha_str)
    if not parsed:
        return None
        
    dt = datetime.datetime.combine(parsed, datetime.time.max)
    return _safe_make_aware(dt)

def rango_por_defecto() -> tuple[datetime.datetime, datetime.datetime]:
    """
    Si no hay filtro, asume históricamente un inicio holgado,
    y fin en el instante actual.
    """
    ahora = get_local_now()
    inicio = _safe_make_aware(datetime.datetime(2000, 1, 1))
    return inicio, ahora

def get_local_now() -> datetime.datetime:
    """Devuelve la fecha y hora actual en la zona horaria local configurada en settings.TIME_ZONE."""
    return timezone.localtime(timezone.now())

def get_local_isoformat(dt: datetime.datetime | None) -> str | None:
    """Convierte de forma segura un datetime a la zona horaria local y devuelve su ISO 8601."""
    if not dt:
        return None
    return timezone.localtime(dt).isoformat()
