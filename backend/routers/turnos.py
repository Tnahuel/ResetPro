from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_payload, get_db, require_role
from ..serializers import turno_out

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

    ocupado = db.query(models.Turno).filter(
        models.Turno.profesor_id == payload.profesor_id,
        models.Turno.fecha == payload.fecha,
        models.Turno.rango_horario == payload.rango_horario,
        models.Turno.estado != models.EstadoTurnoEnum.cancelado,
    ).first()
    if ocupado:
        raise HTTPException(status_code=409, detail="El profesor ya tiene un turno en ese horario")

    turno = models.Turno(**payload.model_dump(), estado=models.EstadoTurnoEnum.confirmado)
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return turno_out(turno)


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
