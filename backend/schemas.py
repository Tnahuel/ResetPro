from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rol_esperado: Optional[Literal["usuario", "profesor", "admin"]] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str
    id: int


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=6, max_length=72)


class AltaCuentaRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    rol: Literal["usuario", "profesor", "admin"]
    detalle: Optional[str] = Field(default=None, max_length=120)


class CuentaResponse(BaseModel):
    id: int
    nombre: str
    email: str
    rol: str


class UsuarioPerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None
    altura: Optional[float] = None
    peso: Optional[float] = None


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    edad: Optional[int] = None
    altura: Optional[float] = None
    peso: Optional[float] = None
    grupo_muscular_actual: Optional[str] = None

    class Config:
        from_attributes = True


class DietaUpdate(BaseModel):
    enlace_externo: Optional[str] = None
    proteina: Optional[float] = Field(default=None, ge=0)
    carbohidratos: Optional[float] = Field(default=None, ge=0)
    grasas: Optional[float] = Field(default=None, ge=0)
    micros: Optional[str] = Field(default=None, max_length=255)
    tipo_dieta: Optional[str] = Field(default=None, max_length=60)


class DietaOut(BaseModel):
    id: int
    usuario_id: int
    proteina: float
    carbohidratos: float
    grasas: float
    micros: Optional[str] = None
    tipo_dieta: Optional[str] = None
    enlace_externo: Optional[str] = None

    class Config:
        from_attributes = True


class TurnoCreate(BaseModel):
    usuario_id: int
    profesor_id: int
    fecha: date
    rango_horario: str = Field(pattern=r"^\d{2}:\d{2}$")
    grupo_muscular: Optional[str] = Field(default=None, max_length=60)


class TurnoOut(BaseModel):
    id: int
    usuario_id: int
    profesor_id: int
    usuario_nombre: str
    profesor_nombre: str
    fecha: date
    rango_horario: str
    estado: str
    grupo_muscular: Optional[str] = None
    nota: Optional[int] = None


class ProfesorOut(BaseModel):
    id: int
    nombre: str
    especialidad: Optional[str] = None
    horarios: Optional[str] = None
    horas_trabajadas: float = 0

    class Config:
        from_attributes = True


class CalificarAlumnoRequest(BaseModel):
    turno_id: int
    nota: int = Field(ge=1, le=10)


class RegistrarHorasRequest(BaseModel):
    horas: float = Field(gt=0, le=24)
