"""Utilidades de seguridad: hashing de contraseñas y manejo de JWT."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Genera el bcrypt hash de una contraseña."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica si una contraseña coincide con su hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """
    Crea un JWT de acceso con expiración corta.

    :param subject: Identificador del usuario (UUID como string).
    :return: Token JWT firmado.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """
    Crea un JWT de refresco con expiración larga.

    :param subject: Identificador del usuario (UUID como string).
    :return: Token JWT firmado.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> Optional[str]:
    """
    Decodifica un JWT y retorna el subject si es válido.

    :param token: Token JWT.
    :param expected_type: Tipo esperado ("access" o "refresh").
    :return: UUID del usuario o None si el token es inválido.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
