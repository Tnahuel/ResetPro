import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import email_utils, models, schemas, security
from ..deps import get_current_payload, get_db
from ..utils import base_url

MINUTOS_EMAIL = 60

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


def _perfil(cred):
    return {
        models.RolEnum.usuario: cred.usuario,
        models.RolEnum.profesor: cred.profesor,
        models.RolEnum.admin: cred.administrador,
    }.get(cred.rol)


@router.post("/olvide-password")
def olvide_password(payload: schemas.OlvidePasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Pide un enlace para crear una contrasena nueva.
    Responde siempre lo mismo exista o no el email (no revela que cuentas existen)."""
    canal = "email" if email_utils.proveedor() else "administrador"

    cred = db.query(models.Credenciales).filter(
        models.Credenciales.email == payload.email.lower()
    ).first()
    if cred:
        ahora = datetime.utcnow()
        # Freno basico: un pedido cada 2 minutos por cuenta.
        reciente = db.query(models.Recuperacion).filter(
            models.Recuperacion.credenciales_id == cred.id,
            models.Recuperacion.usado_en.is_(None),
            models.Recuperacion.creado_en >= ahora - timedelta(minutes=2),
        ).first()
        if not reciente:
            token = secrets.token_urlsafe(32)
            rec = models.Recuperacion(
                credenciales_id=cred.id,
                token_hash=security.hash_token(token),
                expira_en=ahora + timedelta(minutes=MINUTOS_EMAIL),
                origen="usuario",
                enviado=False,
            )
            db.add(rec)
            db.commit()

            sitio = base_url(request)
            if canal == "email" and sitio:
                perfil = _perfil(cred)
                nombre = perfil.nombre if perfil else cred.email
                enlace = f"{sitio}/restablecer.html?token={token}"
                asunto, texto, cuerpo = email_utils.plantilla_recuperacion(nombre, enlace, MINUTOS_EMAIL)
                if email_utils.enviar(cred.email, asunto, texto, cuerpo):
                    rec.enviado = True
                    db.commit()
    return {"ok": True, "canal": canal}


def _recuperacion_vigente(db: Session, token: str):
    rec = db.query(models.Recuperacion).filter(
        models.Recuperacion.token_hash == security.hash_token(token)
    ).first()
    if not rec or rec.usado_en is not None or rec.expira_en < datetime.utcnow():
        return None
    return rec


@router.post("/validar-recuperacion")
def validar_recuperacion(payload: schemas.ValidarRecuperacionRequest, db: Session = Depends(get_db)):
    rec = _recuperacion_vigente(db, payload.token)
    return {"valido": rec is not None}


@router.post("/restablecer-password")
def restablecer_password(payload: schemas.RestablecerPasswordRequest, db: Session = Depends(get_db)):
    rec = _recuperacion_vigente(db, payload.token)
    if rec is None:
        raise HTTPException(status_code=400, detail="El enlace no es valido o ya vencio. Pedi uno nuevo.")
    cred = db.get(models.Credenciales, rec.credenciales_id)
    if cred is None:
        raise HTTPException(status_code=400, detail="La cuenta ya no existe.")

    cred.contrasena_hash = security.hash_password(payload.password_nueva)
    # Este enlace y cualquier otro pendiente de la cuenta quedan inutilizados.
    db.query(models.Recuperacion).filter(
        models.Recuperacion.credenciales_id == cred.id,
        models.Recuperacion.usado_en.is_(None),
    ).update({"usado_en": datetime.utcnow()}, synchronize_session=False)
    db.commit()
    return {"ok": True, "rol": cred.rol.value}
