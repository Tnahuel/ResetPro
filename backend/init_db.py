"""Crea las tablas y carga datos de ejemplo la primera vez que arranca la API."""
import base64
import logging
import os
import threading
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models, security
from .database import Base, get_engine
from .seed_pdfs import PDFS
from .utils import hoy_local

log = logging.getLogger("resetpro")

_initialized = False
_lock = threading.Lock()
LOCK_ID = 727272


def _flag(nombre: str, default: str = "true") -> bool:
    return os.getenv(nombre, default).strip().lower() in ("1", "true", "yes", "si", "on")


def init_once() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        engine = get_engine()
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                # Evita que dos arranques en frio simultaneos creen/siembren a la vez.
                conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": LOCK_ID})
            Base.metadata.create_all(bind=conn)
            session = Session(bind=conn)
            try:
                if session.query(models.Credenciales).count() == 0:
                    if _flag("SEED_DEMO_DATA"):
                        seed_demo(session)
                    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
                    admin_pass = os.getenv("ADMIN_PASSWORD", "")
                    if admin_email and admin_pass:
                        _crear_cuenta(
                            session, os.getenv("ADMIN_NAME", "Administrador"),
                            admin_email, security.hash_password(admin_pass), "admin",
                        )
                    session.flush()
            finally:
                session.close()
        _initialized = True


def _crear_cuenta(session, nombre, email, pw_hash, rol, **extra):
    existente = session.query(models.Credenciales).filter_by(email=email).first()
    if existente:
        return None
    cred = models.Credenciales(email=email, contrasena_hash=pw_hash, rol=models.RolEnum(rol))
    session.add(cred)
    session.flush()
    cls = {"usuario": models.Usuario, "profesor": models.Profesor, "admin": models.Administrador}[rol]
    perfil = cls(credenciales_id=cred.id, nombre=nombre, **extra)
    session.add(perfil)
    session.flush()
    return perfil


def seed_demo(session) -> None:
    log.info("Cargando datos de ejemplo...")
    hoy = hoy_local()
    ahora = datetime.utcnow()
    h_admin = security.hash_password("admin123")
    h_prof = security.hash_password("profesor123")
    h_user = security.hash_password("usuario123")

    _crear_cuenta(session, "Agustina Diaz", "admin@resetpro.app", h_admin, "admin", permisos="total")

    mariano = _crear_cuenta(session, "Mariano Coria", "mariano@resetpro.app", h_prof, "profesor",
                            especialidad="Hipertrofia", horarios="Lun a Vie 09:00-21:00")
    daniela = _crear_cuenta(session, "Daniela Suarez", "daniela@resetpro.app", h_prof, "profesor",
                            especialidad="Funcional", horarios="Lun a Sab 08:00-16:00")
    ignacio = _crear_cuenta(session, "Ignacio Paz", "ignacio@resetpro.app", h_prof, "profesor",
                            especialidad="Fuerza", horarios="Mar a Sab 14:00-22:00")

    alumnos = {}
    datos = [
        ("sarah", "Sarah Martinez", 27, 1.68, 64, "Espalda", ahora - timedelta(hours=1)),
        ("julian", "Julian Perez", 31, 1.79, 81, "Piernas", ahora - timedelta(days=1)),
        ("camila", "Camila Rios", 24, 1.65, 58, "Hombro", ahora - timedelta(days=2)),
        ("lucas", "Lucas Fernandez", 29, 1.82, 85, "Core", ahora - timedelta(days=9)),
        ("valentina", "Valentina Lopez", 26, 1.70, 62, "Piernas", ahora - timedelta(days=3)),
        ("nico", "Nico Suarez", 35, 1.77, 90, "Pecho", ahora - timedelta(days=20)),
    ]
    for clave, nombre, edad, altura, peso, grupo, acceso in datos:
        p = _crear_cuenta(session, nombre, f"{clave}@resetpro.app", h_user, "usuario",
                          edad=edad, altura=altura, peso=peso, grupo_muscular_actual=grupo)
        p.credenciales.ultimo_acceso = acceso
        alumnos[clave] = p
    session.flush()

    def turno(alumno, prof, fecha, hora, grupo):
        estado = models.EstadoTurnoEnum.completado if fecha < hoy else models.EstadoTurnoEnum.confirmado
        session.add(models.Turno(usuario_id=alumno.id, profesor_id=prof.id, fecha=fecha,
                                 rango_horario=hora, grupo_muscular=grupo, estado=estado))

    # Semana completa de Sarah (lunes a sabado, 18:00 con Mariano)
    lunes = hoy - timedelta(days=hoy.weekday())
    semana = ["Pecho", "Espalda", "Piernas", "Hombro", "Brazos", "Core"]
    for i, grupo in enumerate(semana):
        turno(alumnos["sarah"], mariano, lunes + timedelta(days=i), "18:00", grupo)

    turno(alumnos["julian"], mariano, hoy, "19:00", "Piernas")
    turno(alumnos["camila"], mariano, hoy, "20:00", "Hombro")
    turno(alumnos["lucas"], mariano, hoy, "21:00", "Core")
    turno(alumnos["julian"], mariano, hoy + timedelta(days=2), "19:00", "Espalda")
    turno(alumnos["valentina"], daniela, hoy + timedelta(days=1), "17:00", "Piernas")
    turno(alumnos["nico"], ignacio, hoy - timedelta(days=3), "16:00", "Pecho")

    session.add(models.Entrenamiento(usuario_id=alumnos["sarah"].id, profesor_id=mariano.id,
                                     fecha=hoy - timedelta(days=7), grupo_muscular="Espalda",
                                     notas="Sesion completa"))

    def rutina(alumno, clave):
        nombre, b64 = PDFS[clave]
        raw = base64.b64decode(b64)
        session.add(models.Archivo(usuario_id=alumno.id, tipo="rutina", nombre=nombre,
                                   mime="application/pdf", tamano=len(raw), contenido=raw))

    rutina(alumnos["sarah"], "espalda")
    rutina(alumnos["julian"], "piernas")
    rutina(alumnos["camila"], "hombro")

    session.add(models.Dieta(usuario_id=alumnos["sarah"].id, proteina=145, carbohidratos=210, grasas=62,
                             micros="Vitamina D, Magnesio, Omega 3", tipo_dieta="Hipertrofia"))
    session.add(models.Dieta(usuario_id=alumnos["julian"].id, proteina=180, carbohidratos=300, grasas=80,
                             micros="Zinc, Magnesio", tipo_dieta="Volumen"))
    session.flush()
