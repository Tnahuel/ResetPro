import os
from datetime import date, datetime
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
