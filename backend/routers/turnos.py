from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_payload, get_db, require_role
from ..serializers import turno_out
from ..utils import DIAS_PARA_VALORAR, hoy_local, turno_finalizado

router = APIRouter(prefix="/turnos", tags=["turnos"])


@router.post("", response_model=schemas.TurnoOut)
def asignar_turno(
    payload: schemas.TurnoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "profesor")),
):
    if not db.get(models.Usuario, payload.usuario_id):
        raise HTTPException(status_code=404, detail="El alumno no existe")
    if not db.get(models.Profesor, payload.profesor_id):
        raise HTTPException(status_code=404, detail="El profesor no existe")

    reemplazados = 0
    if payload.reemplazar:
        # El turno nuevo "pisa" a los proximos del alumno (queda el historial como cancelado).
        proximos = db.query(models.Turno).filter(
            models.Turno.usuario_id == payload.usuario_id,
            models.Turno.fecha >= hoy_local(),
            models.Turno.estado.in_([models.EstadoTurnoEnum.pendiente, models.EstadoTurnoEnum.confirmado]),
        ).all()
        for t in proximos:
            t.estado = models.EstadoTurnoEnum.cancelado
        reemplazados = len(proximos)
        db.flush()

    ocupado = db.query(models.Turno).filter(
        models.Turno.profesor_id == payload.profesor_id,
        models.Turno.fecha == payload.fecha,
        models.Turno.rango_horario == payload.rango_horario,
        models.Turno.estado != models.EstadoTurnoEnum.cancelado,
    ).first()
    if ocupado:
        raise HTTPException(status_code=409, detail="El profesor ya tiene un turno en ese horario")

    turno = models.Turno(**payload.model_dump(exclude={"reemplazar"}), estado=models.EstadoTurnoEnum.confirmado)
    db.add(turno)
    db.commit()
    db.refresh(turno)
    salida = turno_out(turno)
    salida.reemplazados = reemplazados
    return salida


@router.get("", response_model=List[schemas.TurnoOut])
def listar_turnos(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    turnos = db.query(models.Turno).order_by(models.Turno.fecha.desc(), models.Turno.rango_horario).limit(500).all()
    return [turno_out(t) for t in turnos]


def _es_dueno(sesion: dict, turno: models.Turno) -> bool:
    rol = sesion.get("rol")
    if rol == "admin":
        return True
    if rol == "usuario":
        return sesion.get("perfil_id") == turno.usuario_id
    if rol == "profesor":
        return sesion.get("perfil_id") == turno.profesor_id
    return False


@router.patch("/{turno_id}/cancelar", response_model=schemas.TurnoOut)
def cancelar_turno(turno_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    turno = db.get(models.Turno, turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if not _es_dueno(sesion, turno):
        raise HTTPException(status_code=403, detail="No podes cancelar este turno")
    turno.estado = models.EstadoTurnoEnum.cancelado
    db.commit()
    db.refresh(turno)
    return turno_out(turno)


@router.patch("/{turno_id}/aceptar", response_model=schemas.TurnoOut)
def aceptar_turno(turno_id: int, db: Session = Depends(get_db), sesion: dict = Depends(require_role("profesor"))):
    turno = db.get(models.Turno, turno_id)
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if not _es_dueno(sesion, turno):
        raise HTTPException(status_code=403, detail="Ese turno es de otro profesor")
    turno.estado = models.EstadoTurnoEnum.confirmado
    db.commit()
    db.refresh(turno)
    return turno_out(turno)


@router.post("/{turno_id}/valorar")
def valorar_turno(
    turno_id: int,
    payload: schemas.ValorarTurnoRequest,
    db: Session = Depends(get_db),
    sesion: dict = Depends(get_current_payload),
):
    """El alumno califica (1 a 5 estrellas) un turno que ya realizo. Un voto por turno.
    Solo el alumno dueño del turno puede votar; el profesor nunca ve el resultado."""
    if sesion.get("rol") != "usuario":
        raise HTTPException(status_code=403, detail="Solo los alumnos pueden calificar sus turnos")

    turno = db.get(models.Turno, turno_id)
    if not turno or turno.usuario_id != sesion.get("perfil_id"):
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if turno.estado == models.EstadoTurnoEnum.cancelado:
        raise HTTPException(status_code=400, detail="Ese turno fue cancelado")
    if not turno_finalizado(turno.fecha, turno.rango_horario):
        raise HTTPException(status_code=400, detail="Vas a poder calificar el turno cuando termine el entrenamiento")
    if turno.fecha < hoy_local() - timedelta(days=DIAS_PARA_VALORAR):
        raise HTTPException(status_code=400, detail="Ya pasó el plazo para calificar este turno")
    if db.query(models.Valoracion.id).filter(models.Valoracion.turno_id == turno_id).first():
        raise HTTPException(status_code=409, detail="Ya calificaste este turno")

    db.add(models.Valoracion(
        turno_id=turno.id, usuario_id=turno.usuario_id,
        profesor_id=turno.profesor_id, estrellas=payload.estrellas,
    ))
    try:
        db.commit()
    except IntegrityError:   # dos toques simultaneos: el segundo no pisa al primero
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya calificaste este turno")
    return {"ok": True, "estrellas": payload.estrellas}
