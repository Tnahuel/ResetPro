import enum
from datetime import datetime

from sqlalchemy import (
    Column, Date, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer,
    LargeBinary, String,
)
from sqlalchemy.orm import deferred, relationship

from .database import Base


class RolEnum(str, enum.Enum):
    usuario = "usuario"
    profesor = "profesor"
    admin = "admin"


class EstadoTurnoEnum(str, enum.Enum):
    pendiente = "pendiente"
    confirmado = "confirmado"
    cancelado = "cancelado"
    completado = "completado"


class Credenciales(Base):
    __tablename__ = "credenciales"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    contrasena_hash = Column(String(255), nullable=False)
    rol = Column(SqlEnum(RolEnum, name="rol_enum"), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)
    ultimo_acceso = Column(DateTime)

    usuario = relationship("Usuario", back_populates="credenciales", uselist=False, cascade="all, delete-orphan")
    profesor = relationship("Profesor", back_populates="credenciales", uselist=False, cascade="all, delete-orphan")
    administrador = relationship("Administrador", back_populates="credenciales", uselist=False, cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    credenciales_id = Column(Integer, ForeignKey("credenciales.id", ondelete="CASCADE"), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    edad = Column(Integer)
    altura = Column(Float)
    peso = Column(Float)
    imagen = Column(String(255))
    grupo_muscular_actual = Column(String(60))

    credenciales = relationship("Credenciales", back_populates="usuario")
    dietas = relationship("Dieta", back_populates="usuario", cascade="all, delete-orphan")
    turnos = relationship("Turno", back_populates="usuario", cascade="all, delete-orphan")
    entrenamientos = relationship("Entrenamiento", back_populates="usuario", cascade="all, delete-orphan")
    archivos = relationship("Archivo", back_populates="usuario", cascade="all, delete-orphan")


class Profesor(Base):
    __tablename__ = "profesores"

    id = Column(Integer, primary_key=True, index=True)
    credenciales_id = Column(Integer, ForeignKey("credenciales.id", ondelete="CASCADE"), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    especialidad = Column(String(120))
    horarios = Column(String(255))
    horas_trabajadas = Column(Float, default=0)

    credenciales = relationship("Credenciales", back_populates="profesor")
    turnos = relationship("Turno", back_populates="profesor")
    entrenamientos = relationship("Entrenamiento", back_populates="profesor")


class Administrador(Base):
    __tablename__ = "administradores"

    id = Column(Integer, primary_key=True, index=True)
    credenciales_id = Column(Integer, ForeignKey("credenciales.id", ondelete="CASCADE"), unique=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    permisos = Column(String(120), default="total")

    credenciales = relationship("Credenciales", back_populates="administrador")


class Dieta(Base):
    __tablename__ = "dietas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    archivo_pdf = Column(String(255))
    enlace_externo = Column(String(255))
    proteina = Column(Float, default=0)
    carbohidratos = Column(Float, default=0)
    grasas = Column(Float, default=0)
    micros = Column(String(255))
    tipo_dieta = Column(String(60))
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="dietas")


class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    rango_horario = Column(String(30), nullable=False)
    estado = Column(SqlEnum(EstadoTurnoEnum, name="estado_turno_enum"), default=EstadoTurnoEnum.confirmado)
    grupo_muscular = Column(String(60))
    nota = Column(Integer)

    usuario = relationship("Usuario", back_populates="turnos")
    profesor = relationship("Profesor", back_populates="turnos")


class Entrenamiento(Base):
    __tablename__ = "entrenamientos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    profesor_id = Column(Integer, ForeignKey("profesores.id", ondelete="CASCADE"), nullable=False)
    fecha = Column(Date, nullable=False)
    grupo_muscular = Column(String(60))
    notas = Column(String(255))

    usuario = relationship("Usuario", back_populates="entrenamientos")
    profesor = relationship("Profesor", back_populates="entrenamientos")


class Archivo(Base):
    """PDFs (rutinas y dietas) guardados dentro de PostgreSQL, sin depender de disco."""
    __tablename__ = "archivos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # "rutina" | "dieta"
    nombre = Column(String(255), nullable=False)
    mime = Column(String(100), default="application/pdf")
    tamano = Column(Integer, default=0)
    creado_en = Column(DateTime, default=datetime.utcnow)
    contenido = deferred(Column(LargeBinary, nullable=False))

    usuario = relationship("Usuario", back_populates="archivos")
