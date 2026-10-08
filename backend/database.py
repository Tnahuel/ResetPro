import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

log = logging.getLogger("resetpro")

Base = declarative_base()

_engine = None
_SessionLocal = None


def database_url() -> str:
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
        or ""
    ).strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        if os.getenv("VERCEL"):
            raise RuntimeError(
                "Falta DATABASE_URL. Conecta la base Neon desde Vercel > Storage."
            )
        log.warning("Sin DATABASE_URL: usando SQLite local (solo para pruebas).")
        url = "sqlite:////tmp/resetpro_local.db" if os.name != "nt" else "sqlite:///resetpro_local.db"
    return url


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        if url.startswith("sqlite"):
            _engine = create_engine(url, connect_args={"check_same_thread": False})
        else:
            kwargs = {"pool_pre_ping": True}
            if os.getenv("VERCEL"):
                # Serverless: no mantener conexiones abiertas entre invocaciones.
                kwargs["poolclass"] = NullPool
            _engine = create_engine(url, **kwargs)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal
