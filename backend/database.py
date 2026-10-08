import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

log = logging.getLogger("resetpro")

Base = declarative_base()

_engine = None
_SessionLocal = None


def raw_database_url():
    """Busca la URL de PostgreSQL. Devuelve (nombre_variable, url) o (None, "")."""
    for nombre in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL"):
        valor = (os.getenv(nombre) or "").strip()
        if valor:
            return nombre, valor
    # La integracion de Vercel puede agregar un prefijo propio (STORAGE_URL, NEON_DATABASE_URL, ...).
    # Se toma cualquier variable cuyo valor sea una URL de Postgres, prefiriendo la "pooled".
    candidatas = []
    for nombre, valor in os.environ.items():
        v = (valor or "").strip()
        if v.startswith(("postgres://", "postgresql://")):
            sin_pool = any(x in nombre.upper() for x in ("UNPOOLED", "NON_POOLING", "NO_SSL"))
            candidatas.append((sin_pool, nombre, v))
    if candidatas:
        candidatas.sort(key=lambda c: (c[0], c[1]))
        return candidatas[0][1], candidatas[0][2]
    return None, ""


def database_url() -> str:
    _, url = raw_database_url()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        if os.getenv("VERCEL"):
            raise RuntimeError(
                "No se encontro ninguna variable con la URL de PostgreSQL. En Vercel: "
                "Storage > conecta la base Neon a ESTE proyecto (entorno Production) y hace Redeploy."
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
