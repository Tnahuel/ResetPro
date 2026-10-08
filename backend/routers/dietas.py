from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import check_usuario_access, get_current_payload, get_db, require_role

router = APIRouter(prefix="/dietas", tags=["dietas"])


@router.get("/usuario/{usuario_id}", response_model=List[schemas.DietaOut])
def dietas_de_usuario(usuario_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    check_usuario_access(sesion, usuario_id)
    return db.query(models.Dieta).filter(models.Dieta.usuario_id == usuario_id).all()


@router.post("/usuario/{usuario_id}", response_model=schemas.DietaOut)
def cargar_o_actualizar_dieta(
    usuario_id: int,
    payload: schemas.DietaUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "profesor")),
):
    if not db.get(models.Usuario, usuario_id):
        raise HTTPException(status_code=404, detail="El alumno no existe")
    dieta = (
        db.query(models.Dieta).filter(models.Dieta.usuario_id == usuario_id)
        .order_by(models.Dieta.id.desc()).first()
    )
    if not dieta:
        dieta = models.Dieta(usuario_id=usuario_id)
        db.add(dieta)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(dieta, campo, valor)
    db.commit()
    db.refresh(dieta)
    return dieta
