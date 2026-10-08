from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import check_usuario_access, get_current_payload, get_db
from ..serializers import turno_out
from ..utils import hoy_local

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

DIAS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def _usuario_o_404(db: Session, usuario_id: int) -> models.Usuario:
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    check_usuario_access(sesion, usuario_id)
    return _usuario_o_404(db, usuario_id)


@router.patch("/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_perfil(
    usuario_id: int,
    payload: schemas.UsuarioPerfilUpdate,
    db: Session = Depends(get_db),
    sesion: dict = Depends(get_current_payload),
):
    check_usuario_access(sesion, usuario_id)
    usuario = _usuario_o_404(db, usuario_id)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.get("/{usuario_id}/imc")
def calcular_imc(usuario_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    check_usuario_access(sesion, usuario_id)
    usuario = _usuario_o_404(db, usuario_id)
    if not usuario.altura or not usuario.peso:
        raise HTTPException(status_code=400, detail="Faltan datos de altura o peso")
    return {"usuario_id": usuario_id, "imc": round(usuario.peso / (usuario.altura ** 2), 2)}


@router.get("/{usuario_id}/turnos", response_model=List[schemas.TurnoOut])
def turnos_del_usuario(usuario_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    check_usuario_access(sesion, usuario_id)
    turnos = (
        db.query(models.Turno).filter(models.Turno.usuario_id == usuario_id)
        .order_by(models.Turno.fecha, models.Turno.rango_horario).all()
    )
    return [turno_out(t) for t in turnos]


@router.get("/{usuario_id}/panel")
def panel_usuario(usuario_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    """Todo lo que muestra el panel del usuario en una sola llamada."""
    check_usuario_access(sesion, usuario_id)
    usuario = _usuario_o_404(db, usuario_id)

    hoy = hoy_local()
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)

    activos = models.Turno.estado != models.EstadoTurnoEnum.cancelado
    turnos_semana = (
        db.query(models.Turno)
        .filter(models.Turno.usuario_id == usuario_id, models.Turno.fecha >= lunes,
                models.Turno.fecha <= domingo, activos)
        .order_by(models.Turno.fecha, models.Turno.rango_horario).all()
    )
    por_dia = {}
    for t in turnos_semana:
        por_dia.setdefault(t.fecha, t)

    semana = []
    for i in range(7):
        dia = lunes + timedelta(days=i)
        t = por_dia.get(dia)
        semana.append({
            "fecha": dia.isoformat(), "dia": DIAS[i], "hoy": dia == hoy,
            "grupo": t.grupo_muscular if t else None,
        })

    proximo = (
        db.query(models.Turno)
        .filter(models.Turno.usuario_id == usuario_id, models.Turno.fecha >= hoy, activos)
        .order_by(models.Turno.fecha, models.Turno.rango_horario).first()
    )
    turno_hoy = por_dia.get(hoy)

    dieta = (
        db.query(models.Dieta).filter(models.Dieta.usuario_id == usuario_id)
        .order_by(models.Dieta.actualizado_en.desc()).first()
    )

    def ultimo_archivo(tipo):
        a = (
            db.query(models.Archivo.id, models.Archivo.nombre)
            .filter(models.Archivo.usuario_id == usuario_id, models.Archivo.tipo == tipo)
            .order_by(models.Archivo.id.desc()).first()
        )
        return {"id": a.id, "nombre": a.nombre} if a else None

    return {
        "usuario": {"id": usuario.id, "nombre": usuario.nombre,
                    "grupo_muscular_actual": usuario.grupo_muscular_actual},
        "hoy": hoy.isoformat(),
        "grupo_hoy": turno_hoy.grupo_muscular if turno_hoy else None,
        "semana": semana,
        "proximo_turno": turno_out(proximo).model_dump(mode="json") if proximo else None,
        "dieta": schemas.DietaOut.model_validate(dieta).model_dump() if dieta else None,
        "rutina": ultimo_archivo("rutina"),
        "dieta_pdf": ultimo_archivo("dieta"),
    }
