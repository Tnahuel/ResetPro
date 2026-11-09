import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import get_session_factory
from .security import decode_access_token

log = logging.getLogger("resetpro")
bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    """Sesion por request. La primera vez crea las tablas y carga los datos de ejemplo."""
    try:
        from .init_db import init_once
        init_once()
        factory = get_session_factory()
    except Exception as exc:  # noqa: BLE001
        log.exception("No se pudo preparar la base de datos")
        raise HTTPException(
            status_code=503,
            detail=(
                str(exc) if isinstance(exc, RuntimeError)
                else f"Base de datos no disponible ({type(exc).__name__}). Revisa la conexion a Neon en Vercel."
            ),
        )
    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_current_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inicia sesion para continuar")
    try:
        return decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion vencida o invalida")


def require_role(*roles: str):
    """El admin siempre pasa: no tiene restricciones dentro de la plataforma."""
    def checker(payload: dict = Depends(get_current_payload)) -> dict:
        rol = payload.get("rol")
        if rol != "admin" and rol not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenes permisos para esta accion")
        return payload
    return checker


def check_usuario_access(payload: dict, usuario_id: int) -> None:
    """Un usuario solo ve lo suyo. Profesores y admin pueden ver a cualquier alumno."""
    if payload.get("rol") == "usuario" and payload.get("perfil_id") != usuario_id:
        raise HTTPException(status_code=403, detail="No podes ver datos de otro usuario")


def check_profesor_access(payload: dict, profesor_id: int) -> None:
    if payload.get("rol") == "profesor" and payload.get("perfil_id") != profesor_id:
        raise HTTPException(status_code=403, detail="No podes ver la agenda de otro profesor")
