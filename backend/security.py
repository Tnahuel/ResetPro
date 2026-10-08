import hashlib
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ALGORITHM = "HS256"
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))


def secret_info():
    """Devuelve (clave, origen). Si no hay JWT_SECRET_KEY se deriva de DATABASE_URL."""
    explicit = os.getenv("JWT_SECRET_KEY")
    if explicit:
        return explicit, "JWT_SECRET_KEY"
    from .database import raw_database_url
    base = raw_database_url()[1]
    if base:
        return hashlib.sha256(("resetpro-jwt:" + base).encode()).hexdigest(), "derivada de DATABASE_URL"
    return "solo-para-desarrollo-local", "clave de desarrollo (solo local)"


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode(payload, secret_info()[0], algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, secret_info()[0], algorithms=[ALGORITHM])
