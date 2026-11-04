"""Calificacion (1 a 5 estrellas) del alumno hacia el profesor de un turno ya realizado.

Privacidad: el profesor NO ve estas calificaciones. Aca solo hay endpoints del alumno;
la pantalla con todos los votos es /api/admin/valoraciones (solo administrador).
"""
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..deps import get_current_payload, get_db
from ..utils import hoy_local, turno_finalizado

router = APIRouter(prefix="/valoraciones", tags=["valoraciones"])

DIAS_VENTANA = 30      # se ofrecen para calificar los turnos de los ultimos 30 dias
MAX_PENDIENTES = 5     # y como mucho los 5 mas recientes, para no abrumar al alumno


def _alumno_id(sesion: dict) -> int:
    """Solo el alumno califica. Ni el profesor ni el admin (el admin pasa require_role, por eso
    se valida el rol de forma estricta)."""
    if sesion.get("rol") != "usuario" or not sesion.get("perfil_id"):
        raise HTTPException(status_code=403, detail="Solo los alumnos pueden calificar sus turnos")
    return sesion["perfil_id"]


@router.get("/pendientes", response_model=List[schemas.TurnoPorCalificar])
def turnos_por_calificar(db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    """Turnos del alumno que ya terminaron, no se cancelaron y todavia no calificó."""
    usuario_id = _alumno_id(sesion)
    hoy = hoy_local()
    ya_calificados = select(models.Valoracion.turno_id).where(models.Valoracion.usuario_id == usuario_id)
    turnos = (
        db.query(models.Turno)
        .options(joinedload(models.Turno.profesor))
        .filter(
            models.Turno.usuario_id == usuario_id,
            models.Turno.estado != models.EstadoTurnoEnum.cancelado,
            models.Turno.fecha >= hoy - timedelta(days=DIAS_VENTANA),
            models.Turno.fecha <= hoy,
            ~models.Turno.id.in_(ya_calificados),
        )
        .order_by(models.Turno.fecha.desc(), models.Turno.rango_horario.desc())
        .all()
    )
    finalizados = [t for t in turnos if turno_finalizado(t.fecha, t.rango_horario)]
    return [
        schemas.TurnoPorCalificar(
            turno_id=t.id, fecha=t.fecha, rango_horario=t.rango_horario,
            grupo_muscular=t.grupo_muscular,
            profesor_nombre=t.profesor.nombre if t.profesor else "",
        )
        for t in finalizados[:MAX_PENDIENTES]
    ]


@router.post("", response_model=schemas.ValoracionOut, status_code=201)
def calificar_turno(
    payload: schemas.ValoracionCreate,
    db: Session = Depends(get_db),
    sesion: dict = Depends(get_current_payload),
):
    usuario_id = _alumno_id(sesion)
    turno = db.get(models.Turno, payload.turno_id)
    # 404 tambien si el turno es de otro alumno: no se revela que existe.
    if not turno or turno.usuario_id != usuario_id:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if turno.estado == models.EstadoTurnoEnum.cancelado:
        raise HTTPException(status_code=400, detail="Un turno cancelado no se puede calificar")
    if not turno_finalizado(turno.fecha, turno.rango_horario):
        raise HTTPException(status_code=400, detail="Vas a poder calificar el turno cuando termine el entrenamiento")
    if db.query(models.Valoracion.id).filter(models.Valoracion.turno_id == turno.id).first():
        raise HTTPException(status_code=409, detail="Ya calificaste este turno")

    db.add(models.Valoracion(
        turno_id=turno.id, usuario_id=usuario_id, profesor_id=turno.profesor_id, estrellas=payload.estrellas,
    ))
    try:
        db.commit()
    except IntegrityError:   # dos envios a la vez: gana el primero
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya calificaste este turno")
    return schemas.ValoracionOut(turno_id=turno.id, estrellas=payload.estrellas)
