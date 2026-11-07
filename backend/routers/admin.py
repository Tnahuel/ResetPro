import secrets
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

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


def _turno_referencia(turnos, hoy):
    """Turno que representa al alumno: el proximo activo; si no hay, el ultimo activo; si no, el cancelado."""
    activos = [t for t in turnos if t.estado != models.EstadoTurnoEnum.cancelado]
    proximos = [t for t in activos if t.fecha >= hoy]
    if proximos:
        return proximos[0], "proximo"       # `turnos` viene ordenado por fecha y hora
    if activos:
        return activos[-1], "ultimo"
    if turnos:
        return turnos[-1], "cancelado"
    return None, None


def _archivo_dict(a):
    if not a:
        return None
    return {"id": a.id, "nombre": a.nombre, "creado_en": a.creado_en.isoformat() + "Z" if a.creado_en else None}


@router.get("/estudiantes-detalle")
def estudiantes_detalle(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Dashboard de estudiantes con su turno vigente, PDFs actuales, macros y ultimo acceso."""
    ahora = datetime.utcnow()
    hoy = hoy_local()

    usuarios = (
        db.query(models.Usuario)
        .options(joinedload(models.Usuario.credenciales))
        .order_by(models.Usuario.nombre).all()
    )

    turnos_por_usuario = {}
    turnos = (
        db.query(models.Turno)
        .options(joinedload(models.Turno.profesor))
        .order_by(models.Turno.fecha, models.Turno.rango_horario).all()
    )
    for t in turnos:
        turnos_por_usuario.setdefault(t.usuario_id, []).append(t)

    archivos = {}
    filas = (
        db.query(models.Archivo.id, models.Archivo.usuario_id, models.Archivo.tipo,
                 models.Archivo.nombre, models.Archivo.creado_en)
        .order_by(models.Archivo.id.desc()).all()
    )
    for a in filas:
        archivos.setdefault((a.usuario_id, a.tipo), a)   # queda el mas nuevo de cada tipo

    dietas = {}
    for d in db.query(models.Dieta).order_by(models.Dieta.id.desc()).all():
        dietas.setdefault(d.usuario_id, d)

    resultado = []
    for u in usuarios:
        turno, tipo = _turno_referencia(turnos_por_usuario.get(u.id, []), hoy)
        if turno is None:
            estado = "sin_turnos"
        elif tipo == "cancelado":
            estado = "cancelado"
        elif tipo == "ultimo":
            estado = "completado"
        else:
            estado = turno.estado.value
        acceso = u.credenciales.ultimo_acceso if u.credenciales else None
        dieta = dietas.get(u.id)
        resultado.append({
            "id": u.id,
            "nombre": u.nombre,
            "email": u.credenciales.email if u.credenciales else None,
            "grupo_muscular": (turno.grupo_muscular if turno and turno.grupo_muscular else u.grupo_muscular_actual),
            "turno": {
                "tipo": tipo,
                "fecha": turno.fecha.isoformat(),
                "hora": turno.rango_horario,
                "profesor": turno.profesor.nombre if turno.profesor else None,
            } if turno else None,
            "rutina": _archivo_dict(archivos.get((u.id, "rutina"))),
            "dieta_pdf": _archivo_dict(archivos.get((u.id, "dieta"))),
            "macros": {
                "proteina": dieta.proteina, "carbohidratos": dieta.carbohidratos, "grasas": dieta.grasas,
                "micros": dieta.micros,
            } if dieta else None,
            "ultimo_acceso": acceso.isoformat() + "Z" if acceso else None,
            "activo_semana": bool(acceso and (ahora - acceso) <= timedelta(days=7)),
            "estado": estado,
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


# ---------------------------- Profesores ----------------------------
@router.get("/profesores-detalle")
def profesores_detalle(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    hoy = hoy_local()
    ahora = datetime.utcnow()
    vigentes = [models.EstadoTurnoEnum.pendiente, models.EstadoTurnoEnum.confirmado]

    totales = dict(
        db.query(models.Turno.profesor_id, func.count(models.Turno.id))
        .group_by(models.Turno.profesor_id).all()
    )
    proximos = {
        fila[0]: (fila[1], fila[2])
        for fila in db.query(
            models.Turno.profesor_id,
            func.count(models.Turno.id),
            func.count(func.distinct(models.Turno.usuario_id)),
        ).filter(models.Turno.fecha >= hoy, models.Turno.estado.in_(vigentes))
        .group_by(models.Turno.profesor_id).all()
    }

    resultado = []
    profesores = (
        db.query(models.Profesor)
        .options(joinedload(models.Profesor.credenciales))
        .order_by(models.Profesor.nombre).all()
    )
    for p in profesores:
        acceso = p.credenciales.ultimo_acceso if p.credenciales else None
        n_prox, n_alumnos = proximos.get(p.id, (0, 0))
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "email": p.credenciales.email if p.credenciales else None,
            "especialidad": p.especialidad,
            "turnos_total": totales.get(p.id, 0),
            "turnos_proximos": n_prox,
            "alumnos_proximos": n_alumnos,
            "ultimo_acceso": acceso.isoformat() + "Z" if acceso else None,
            "activo_semana": bool(acceso and (ahora - acceso) <= timedelta(days=7)),
        })
    return resultado


# ---------------------------- Eliminar ----------------------------
@router.delete("/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Borra al alumno con su cuenta, turnos, dieta, PDFs e historial."""
    u = db.get(models.Usuario, usuario_id)
    if not u:
        raise HTTPException(status_code=404, detail="El alumno no existe")
    nombre, cred_id = u.nombre, u.credenciales_id

    eliminados = {}
    for etiqueta, modelo in (("valoraciones", models.Valoracion), ("turnos", models.Turno), ("archivos", models.Archivo),
                             ("dietas", models.Dieta), ("entrenamientos", models.Entrenamiento)):
        eliminados[etiqueta] = (
            db.query(modelo).filter(modelo.usuario_id == usuario_id).delete(synchronize_session=False)
        )
    db.query(models.Recuperacion).filter(models.Recuperacion.credenciales_id == cred_id).delete(synchronize_session=False)
    db.expire_all()
    cred = db.get(models.Credenciales, cred_id)
    if cred:
        db.delete(cred)   # la cuenta arrastra al perfil de usuario
    db.commit()
    return {"ok": True, "nombre": nombre, "eliminados": eliminados}


@router.delete("/profesores/{profesor_id}")
def eliminar_profesor(profesor_id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Borra al profesor con su cuenta y los turnos que tenia asignados."""
    p = db.get(models.Profesor, profesor_id)
    if not p:
        raise HTTPException(status_code=404, detail="El profesor no existe")
    nombre, cred_id = p.nombre, p.credenciales_id

    eliminados = {}
    for etiqueta, modelo in (("valoraciones", models.Valoracion), ("turnos", models.Turno), ("entrenamientos", models.Entrenamiento)):
        eliminados[etiqueta] = (
            db.query(modelo).filter(modelo.profesor_id == profesor_id).delete(synchronize_session=False)
        )
    db.query(models.Recuperacion).filter(models.Recuperacion.credenciales_id == cred_id).delete(synchronize_session=False)
    db.expire_all()
    cred = db.get(models.Credenciales, cred_id)
    if cred:
        db.delete(cred)
    db.commit()
    return {"ok": True, "nombre": nombre, "eliminados": eliminados}


# ---------------------------- Recuperacion de contrasenas ----------------------------
def _perfil_de(cred):
    return {
        models.RolEnum.usuario: cred.usuario,
        models.RolEnum.profesor: cred.profesor,
        models.RolEnum.admin: cred.administrador,
    }.get(cred.rol)


@router.get("/recuperaciones")
def solicitudes_recuperacion(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """Pedidos de "olvide mi clave" que NO salieron por email (para atenderlos a mano)."""
    ahora = datetime.utcnow()
    filas = (
        db.query(models.Recuperacion)
        .options(joinedload(models.Recuperacion.credenciales))
        .filter(
            models.Recuperacion.usado_en.is_(None),
            models.Recuperacion.expira_en > ahora,
            models.Recuperacion.enviado.is_(False),
            models.Recuperacion.origen == "usuario",
        )
        .order_by(models.Recuperacion.creado_en.desc()).limit(100).all()
    )
    vistos, resultado = set(), []
    for r in filas:
        c = r.credenciales
        if c is None or c.id in vistos:
            continue
        vistos.add(c.id)
        perfil = _perfil_de(c)
        resultado.append({
            "email": c.email,
            "rol": c.rol.value,
            "nombre": perfil.nombre if perfil else c.email,
            "perfil_id": perfil.id if perfil else None,
            "creado_en": r.creado_en.isoformat() + "Z",
        })
    return resultado


@router.post("/enlace-recuperacion")
def enlace_recuperacion(
    payload: schemas.EnlaceRecuperacionRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Genera un enlace de un solo uso (24 hs) para que la persona cree su clave nueva.
    Invalida los enlaces anteriores de esa cuenta."""
    modelo = {"usuario": models.Usuario, "profesor": models.Profesor, "admin": models.Administrador}[payload.rol]
    perfil = db.get(modelo, payload.id)
    if not perfil:
        raise HTTPException(status_code=404, detail="La cuenta no existe")

    ahora = datetime.utcnow()
    db.query(models.Recuperacion).filter(
        models.Recuperacion.credenciales_id == perfil.credenciales_id,
        models.Recuperacion.usado_en.is_(None),
    ).update({"usado_en": ahora}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    rec = models.Recuperacion(
        credenciales_id=perfil.credenciales_id,
        token_hash=security.hash_token(token),
        expira_en=ahora + timedelta(hours=24),
        origen="admin",
        enviado=True,
    )
    db.add(rec)
    db.commit()
    return {
        "token": token,
        "expira_en": rec.expira_en.isoformat() + "Z",
        "nombre": perfil.nombre,
        "email": perfil.credenciales.email,
    }


# ---------------------------- Valoraciones (solo administrador) ----------------------------
@router.get("/valoraciones")
def valoraciones(
    profesor_id: Optional[int] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """Votos de 1 a 5 estrellas de los alumnos hacia los profesores.
    Los filtros de fecha se aplican sobre el dia del turno.
    - `profesores`: ranking de TODOS los profesores (solo filtra por fecha).
    - `general` y `valoraciones`: ademas filtran por profesor_id si se indica."""
    if desde and hasta and desde > hasta:
        raise HTTPException(status_code=400, detail="La fecha \"desde\" no puede ser posterior a \"hasta\"")

    V, T = models.Valoracion, models.Turno

    def filtrar(q, con_profesor):
        if desde:
            q = q.filter(T.fecha >= desde)
        if hasta:
            q = q.filter(T.fecha <= hasta)
        if con_profesor and profesor_id:
            q = q.filter(V.profesor_id == profesor_id)
        return q

    # Ranking por profesor
    filas = (
        filtrar(db.query(V.profesor_id, V.estrellas, func.count(V.id)).select_from(V).join(T, V.turno_id == T.id), False)
        .group_by(V.profesor_id, V.estrellas).all()
    )
    por_profe = {}
    for pid, est, n in filas:
        por_profe.setdefault(pid, {str(i): 0 for i in range(1, 6)})[str(est)] = n

    ranking = []
    for p in db.query(models.Profesor).order_by(models.Profesor.nombre).all():
        dist = por_profe.get(p.id, {str(i): 0 for i in range(1, 6)})
        cantidad = sum(dist.values())
        promedio = round(sum(int(k) * v for k, v in dist.items()) / cantidad, 2) if cantidad else None
        ranking.append({"id": p.id, "nombre": p.nombre, "promedio": promedio,
                        "cantidad": cantidad, "distribucion": dist})
    ranking.sort(key=lambda r: (r["promedio"] is None, -(r["promedio"] or 0), -r["cantidad"], r["nombre"]))

    # Totales con todos los filtros
    cantidad, promedio = filtrar(
        db.query(func.count(V.id), func.avg(V.estrellas)).select_from(V).join(T, V.turno_id == T.id), True
    ).one()

    # Detalle de votos (mas recientes primero)
    detalle = (
        filtrar(
            db.query(V, T, models.Usuario.nombre, models.Profesor.nombre)
            .select_from(V)
            .join(T, V.turno_id == T.id)
            .join(models.Usuario, V.usuario_id == models.Usuario.id)
            .join(models.Profesor, V.profesor_id == models.Profesor.id),
            True,
        )
        .order_by(V.creado_en.desc(), V.id.desc()).limit(501).all()
    )
    truncado = len(detalle) > 500
    lista = [{
        "id": v.id,
        "estrellas": v.estrellas,
        "alumno": alumno,
        "profesor": profesor,
        "profesor_id": v.profesor_id,
        "fecha_turno": t.fecha.isoformat(),
        "hora": t.rango_horario,
        "grupo_muscular": t.grupo_muscular,
        "votado_en": v.creado_en.isoformat() + "Z" if v.creado_en else None,
    } for v, t, alumno, profesor in detalle[:500]]

    return {
        "general": {"cantidad": cantidad, "promedio": round(float(promedio), 2) if promedio is not None else None},
        "profesores": ranking,
        "valoraciones": lista,
        "truncado": truncado,
    }
