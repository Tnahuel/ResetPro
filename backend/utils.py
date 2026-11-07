import os
from datetime import date, datetime, timedelta
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


# --- Valoraciones de turnos ---
DURACION_TURNO_MIN = int(os.getenv("DURACION_TURNO_MIN", "60"))   # cuanto dura un entrenamiento
DIAS_PARA_VALORAR = int(os.getenv("DIAS_PARA_VALORAR", "30"))     # plazo para calificar un turno


def turno_finalizado(fecha: date, hora: str) -> bool:
    """True cuando ya paso el horario del turno mas su duracion (hora local)."""
    try:
        hh, mm = (int(x) for x in hora.split(":")[:2])
    except (ValueError, AttributeError):
        return fecha < hoy_local()   # horario ilegible: se considera hecho al dia siguiente
    inicio = datetime(fecha.year, fecha.month, fecha.day, hh, mm, tzinfo=zona())
    return ahora_local() >= inicio + timedelta(minutes=DURACION_TURNO_MIN)
