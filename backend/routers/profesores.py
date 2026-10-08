from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import check_profesor_access, get_current_payload, get_db, require_role
from ..serializers import turno_out
from ..utils import hoy_local

router = APIRouter(prefix="/profesores", tags=["profesores"])


@router.get("", response_model=List[schemas.ProfesorOut])
def listar_profesores(db: Session = Depends(get_db), _=Depends(get_current_payload)):
    return db.query(models.Profesor).order_by(models.Profesor.nombre).all()


@router.get("/{profesor_id}/agenda")
def agenda(
    profesor_id: int,
    dias: int = Query(7, ge=1, le=60),
    db: Session = Depends(get_db),
    sesion: dict = Depends(get_current_payload),
):
    """Turnos de hoy en adelante, con el alumno, el grupo muscular y la rutina en PDF."""
    check_profesor_access(sesion, profesor_id)
    hoy = hoy_local()
    turnos = (
        db.query(models.Turno)
        .filter(models.Turno.profesor_id == profesor_id, models.Turno.fecha >= hoy,
                models.Turno.fecha <= hoy + timedelta(days=dias),
                models.Turno.estado != models.EstadoTurnoEnum.cancelado)
        .order_by(models.Turno.fecha, models.Turno.rango_horario).all()
    )
    resultado = []
    for t in turnos:
        archivo = (
            db.query(models.Archivo.id, models.Archivo.nombre)
            .filter(models.Archivo.usuario_id == t.usuario_id, models.Archivo.tipo == "rutina")
            .order_by(models.Archivo.id.desc()).first()
        )
        item = turno_out(t).model_dump(mode="json")
        item["rutina"] = {"id": archivo.id, "nombre": archivo.nombre} if archivo else None
        resultado.append(item)
    return {"hoy": hoy.isoformat(), "turnos": resultado}


@router.post("/{profesor_id}/calificar", response_model=schemas.TurnoOut)
def calificar_alumno(
    profesor_id: int,
    payload: schemas.CalificarAlumnoRequest,
    db: Session = Depends(get_db),
    sesion: dict = Depends(require_role("profesor")),
):
    check_profesor_access(sesion, profesor_id)
    turno = db.get(models.Turno, payload.turno_id)
    if not turno or turno.profesor_id != profesor_id:
        raise HTTPException(status_code=404, detail="Turno no encontrado para este profesor")
    turno.nota = payload.nota
    db.commit()
    db.refresh(turno)
    return turno_out(turno)


@router.post("/{profesor_id}/horas")
def registrar_horas(
    profesor_id: int,
    payload: schemas.RegistrarHorasRequest,
    db: Session = Depends(get_db),
    sesion: dict = Depends(require_role("profesor")),
):
    check_profesor_access(sesion, profesor_id)
    profesor = db.get(models.Profesor, profesor_id)
    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    profesor.horas_trabajadas = (profesor.horas_trabajadas or 0) + payload.horas
    db.commit()
    return {"profesor_id": profesor_id, "horas_trabajadas": profesor.horas_trabajadas}
