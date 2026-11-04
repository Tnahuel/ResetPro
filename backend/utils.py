import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def zona() -> ZoneInfo:
    try:
        return ZoneInfo(os.getenv("APP_TIMEZONE", "America/Argentina/Cordoba"))
    except Exception:
        return ZoneInfo("UTC")


def ahora_local() -> datetime:
    return datetime.now(zona())


def hoy_local() -> date:
    return ahora_local().date()


def duracion_turno_min() -> int:
    """Minutos que dura un turno (los horarios de la agenda son bloques de 1 hora)."""
    try:
        return max(1, int(os.getenv("DURACION_TURNO_MIN", "60")))
    except ValueError:
        return 60


def turno_finalizado(fecha: date, rango_horario: str, ahora: datetime = None) -> bool:
    """True si el turno ya termino (hora de inicio + duracion <= ahora, en hora local).
    Nada en el sistema marca los turnos como 'completado', asi que se calcula por fecha y hora."""
    try:
        h, m = (int(x) for x in rango_horario.split(":")[:2])
        inicio = datetime.combine(fecha, time(h, m), tzinfo=zona())
    except (ValueError, AttributeError):
        return False
    return inicio + timedelta(minutes=duracion_turno_min()) <= (ahora or ahora_local())


def base_url(request=None) -> str:
    """URL publica del sitio, para armar el enlace del email.
    Prioriza APP_BASE_URL y el dominio de produccion de Vercel (no se puede manipular
    con el header Host); solo usa el request como ultimo recurso (desarrollo local)."""
    explicito = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if explicito:
        return explicito
    produccion = os.getenv("VERCEL_PROJECT_PRODUCTION_URL", "").strip()
    if produccion:
        return "https://" + produccion
    if request is not None:
        proto = request.headers.get("x-forwarded-proto") or request.url.scheme
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        return f"{proto}://{host}"
    return ""
