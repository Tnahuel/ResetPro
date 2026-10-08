from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..deps import get_db, require_role
from ..utils import hoy_local

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/cuentas", response_model=schemas.CuentaResponse)
def crear_cuenta(
    payload: schemas.AltaCuentaRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    email = payload.email.lower()
    if db.query(models.Credenciales).filter(models.Credenciales.email == email).first():
        raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese email")

    cred = models.Credenciales(
        email=email,
        contrasena_hash=security.hash_password(payload.password),
        rol=models.RolEnum(payload.rol),
    )
    db.add(cred)
    db.flush()

    if payload.rol == "usuario":
        perfil = models.Usuario(credenciales_id=cred.id, nombre=payload.nombre, grupo_muscular_actual=payload.detalle)
    elif payload.rol == "profesor":
        perfil = models.Profesor(credenciales_id=cred.id, nombre=payload.nombre, especialidad=payload.detalle)
    else:
        perfil = models.Administrador(credenciales_id=cred.id, nombre=payload.nombre, permisos=payload.detalle or "total")
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return schemas.CuentaResponse(id=perfil.id, nombre=perfil.nombre, email=cred.email, rol=payload.rol)


@router.get("/estudiantes-detalle")
def estudiantes_detalle(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Dashboard de estudiantes: ultimo turno, profesor y ultimo acceso a la web."""
    ahora = datetime.utcnow()
    resultado = []
    for u in db.query(models.Usuario).order_by(models.Usuario.nombre).all():
        ultimo = (
            db.query(models.Turno).filter(models.Turno.usuario_id == u.id)
            .order_by(models.Turno.fecha.desc(), models.Turno.rango_horario.desc()).first()
        )
        acceso = u.credenciales.ultimo_acceso if u.credenciales else None
        resultado.append({
            "id": u.id,
            "nombre": u.nombre,
            "grupo_muscular": u.grupo_muscular_actual,
            "profesor": ultimo.profesor.nombre if ultimo else None,
            "ultimo_turno": f"{ultimo.fecha.isoformat()} {ultimo.rango_horario}" if ultimo else None,
            "ultimo_acceso": acceso.isoformat() + "Z" if acceso else None,
            "activo_semana": bool(acceso and (ahora - acceso) <= timedelta(days=7)),
            "estado": ultimo.estado.value if ultimo else "sin_turnos",
        })
    return resultado


@router.get("/stats")
def stats(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    ahora = datetime.utcnow()
    con_rutina = db.query(models.Archivo.usuario_id).filter(models.Archivo.tipo == "rutina").distinct().count()
    total_usuarios = db.query(models.Usuario).count()
    activos = (
        db.query(models.Credenciales)
        .filter(models.Credenciales.rol == models.RolEnum.usuario,
                models.Credenciales.ultimo_acceso >= ahora - timedelta(days=7))
        .count()
    )
    return {
        "usuarios": total_usuarios,
        "activos_semana": activos,
        "profesores": db.query(models.Profesor).count(),
        "turnos_hoy": db.query(models.Turno).filter(
            models.Turno.fecha == hoy_local(),
            models.Turno.estado != models.EstadoTurnoEnum.cancelado).count(),
        "rutinas_pendientes": max(total_usuarios - con_rutina, 0),
    }
