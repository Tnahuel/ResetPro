import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models, security
from .database import database_url, get_engine, get_session_factory, raw_database_url
from .routers import admin, archivos, auth, dietas, profesores, turnos, usuarios

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="ResetPro API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

# En Vercel front y API comparten dominio, asi que CORS no hace falta.
# Solo se activa si definis CORS_ORIGINS (por ejemplo para un front en otro dominio).
origenes = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origenes:
    app.add_middleware(
        CORSMiddleware, allow_origins=origenes, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

for r in (auth.router, usuarios.router, profesores.router, turnos.router,
          dietas.router, archivos.router, admin.router):
    app.include_router(r, prefix="/api")


@app.get("/api")
def api_root():
    return {"status": "ok", "service": "ResetPro API"}


@app.get("/api/health")
def health():
    """Diagnostico para verificar el despliegue (lo usa /estado.html)."""
    info = {
        "api": "ok",
        "db": "error",
        "motor": None,
        "usuarios": None,
        "variable_db": raw_database_url()[0] or "ninguna",
        "jwt": security.secret_info()[1],
        "detalle": None,
    }
    try:
        from .init_db import init_once
        init_once()
        engine = get_engine()
        info["motor"] = engine.dialect.name
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = get_session_factory()()
        try:
            info["usuarios"] = db.query(models.Usuario).count()
        finally:
            db.close()
        info["db"] = "ok"
    except Exception as exc:  # noqa: BLE001
        info["detalle"] = f"{type(exc).__name__}: {str(exc)[:200]}"
        try:
            url = database_url()
            if url:
                info["detalle"] = info["detalle"].replace(url, "[DATABASE_URL]")
        except Exception:  # noqa: BLE001
            pass
    return info


# Solo en local: sirve el frontend desde public/ para probar todo con un solo comando.
if not os.getenv("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    _public = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    if os.path.isdir(_public):
        app.mount("/", StaticFiles(directory=_public, html=True), name="public")
