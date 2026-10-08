from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..deps import get_current_payload, get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    cred = db.query(models.Credenciales).filter(
        models.Credenciales.email == payload.email.lower()
    ).first()
    if not cred or not security.verify_password(payload.password, cred.contrasena_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contrasena incorrectos")

    if payload.rol_esperado and cred.rol.value != payload.rol_esperado:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta cuenta no tiene ese rol")

    perfil = {
        models.RolEnum.usuario: cred.usuario,
        models.RolEnum.profesor: cred.profesor,
        models.RolEnum.admin: cred.administrador,
    }[cred.rol]
    if perfil is None:
        raise HTTPException(status_code=500, detail="La cuenta no tiene perfil asociado")

    cred.ultimo_acceso = datetime.utcnow()
    db.commit()

    token = security.create_access_token({
        "sub": str(cred.id), "rol": cred.rol.value, "perfil_id": perfil.id, "nombre": perfil.nombre,
    })
    return schemas.TokenResponse(access_token=token, rol=cred.rol.value, nombre=perfil.nombre, id=perfil.id)


@router.post("/cambiar-password")
def cambiar_password(
    payload: schemas.CambiarPasswordRequest,
    db: Session = Depends(get_db),
    sesion: dict = Depends(get_current_payload),
):
    cred = db.get(models.Credenciales, int(sesion["sub"]))
    if not cred or not security.verify_password(payload.password_actual, cred.contrasena_hash):
        raise HTTPException(status_code=400, detail="La contrasena actual no es correcta")
    cred.contrasena_hash = security.hash_password(payload.password_nueva)
    db.commit()
    return {"ok": True}
