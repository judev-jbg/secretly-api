"""Lógica de negocio para autenticación: registro, login, reset de contraseña."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest


def register_user(db: Session, payload: RegisterRequest) -> User:
    """
    Registra un nuevo usuario.
    Lanza ValueError si el email ya existe.

    :param db: Sesión de base de datos.
    :param payload: Datos de registro.
    :return: Usuario creado.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ValueError("Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        auth_hash=hash_password(payload.password),
        salt=payload.salt,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, payload: LoginRequest) -> dict:
    """
    Autentica a un usuario y retorna tokens JWT + salt.
    Lanza ValueError si las credenciales son inválidas.

    :param db: Sesión de base de datos.
    :param payload: Email y contraseña.
    :return: Dict con access_token, refresh_token y salt.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.auth_hash):
        raise ValueError("Invalid credentials")

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "salt": user.salt,
    }


def create_reset_token(db: Session, email: str) -> str | None:
    """
    Genera un token de reset para el usuario con ese email.
    Retorna el token si el usuario existe, None si no.
    No revelar si el email existe para evitar user enumeration.

    :param db: Sesión de base de datos.
    :param email: Email del usuario.
    :return: Token de reset o None.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    token = str(uuid.uuid4())
    user.reset_token = token
    user.reset_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    return token


def reset_password(db: Session, token: str, new_password: str) -> bool:
    """
    Aplica el reset de contraseña si el token es válido y no expiró.
    No modifica el salt ni los secretos cifrados.

    :param db: Sesión de base de datos.
    :param token: Token de reset.
    :param new_password: Nueva contraseña en texto plano.
    :return: True si se aplicó correctamente, False si el token es inválido.
    """
    user = db.query(User).filter(User.reset_token == token).first()
    if not user or not user.reset_expires:
        return False

    expires = user.reset_expires.replace(tzinfo=timezone.utc) if user.reset_expires.tzinfo is None else user.reset_expires
    if datetime.now(timezone.utc) > expires:
        return False

    user.auth_hash = hash_password(new_password)
    user.reset_token = None
    user.reset_expires = None
    db.commit()
    return True
