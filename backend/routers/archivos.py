from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..deps import check_usuario_access, get_current_payload, get_db, require_role

router = APIRouter(prefix="/archivos", tags=["archivos"])

MAX_BYTES = 4 * 1024 * 1024  # el limite de body de una funcion de Vercel ronda los 4.5 MB


@router.post("")
async def subir_archivo(
    usuario_id: int = Form(...),
    tipo: Literal["rutina", "dieta"] = Form(...),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "profesor")),
):
    if not db.get(models.Usuario, usuario_id):
        raise HTTPException(status_code=404, detail="El alumno no existe")

    contenido = await archivo.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera los 4 MB")
    if not contenido.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="El archivo no es un PDF valido")

    nombre = (archivo.filename or "documento.pdf")[:255]
    registro = models.Archivo(
        usuario_id=usuario_id, tipo=tipo, nombre=nombre,
        mime="application/pdf", tamano=len(contenido), contenido=contenido,
    )
    db.add(registro)

    if tipo == "dieta":
        dieta = (
            db.query(models.Dieta).filter(models.Dieta.usuario_id == usuario_id)
            .order_by(models.Dieta.id.desc()).first()
        )
        if not dieta:
            dieta = models.Dieta(usuario_id=usuario_id)
            db.add(dieta)
        dieta.archivo_pdf = nombre

    db.commit()
    db.refresh(registro)
    return {"id": registro.id, "nombre": registro.nombre, "tipo": registro.tipo, "usuario_id": usuario_id}


@router.get("/{archivo_id}")
def descargar_archivo(archivo_id: int, db: Session = Depends(get_db), sesion: dict = Depends(get_current_payload)):
    archivo = db.get(models.Archivo, archivo_id)
    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    check_usuario_access(sesion, archivo.usuario_id)
    nombre_ascii = archivo.nombre.encode("ascii", "ignore").decode() or "documento.pdf"
    return Response(
        content=bytes(archivo.contenido),
        media_type=archivo.mime or "application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{nombre_ascii}\"; filename*=UTF-8\x27\x27{quote(archivo.nombre)}",
            "Cache-Control": "private, no-store",
        },
    )
