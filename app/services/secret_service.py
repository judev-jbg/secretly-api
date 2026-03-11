"""Lógica de negocio para el CRUD de secretos."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.secret import Secret
from app.schemas.secret import SecretCreate, SecretUpdate


def get_secrets(db: Session, user_id: str) -> list[Secret]:
    """
    Retorna la lista de secretos del usuario (sin blobs cifrados en memoria).

    :param db: Sesión de base de datos.
    :param user_id: UUID del usuario autenticado.
    :return: Lista de secretos.
    """
    return db.query(Secret).filter(Secret.user_id == user_id).order_by(Secret.created_at.desc()).all()


def get_secret(db: Session, user_id: str, secret_id: str) -> Secret | None:
    """
    Retorna un secreto específico del usuario, incluyendo el blob cifrado.

    :param db: Sesión de base de datos.
    :param user_id: UUID del usuario autenticado.
    :param secret_id: UUID del secreto.
    :return: Secreto o None si no existe o no pertenece al usuario.
    """
    return (
        db.query(Secret)
        .filter(Secret.id == secret_id, Secret.user_id == user_id)
        .first()
    )


def create_secret(db: Session, user_id: str, payload: SecretCreate) -> Secret:
    """
    Crea un nuevo secreto cifrado.

    :param db: Sesión de base de datos.
    :param user_id: UUID del usuario autenticado.
    :param payload: Datos del secreto.
    :return: Secreto creado.
    """
    secret = Secret(
        id=str(uuid.uuid4()),
        user_id=user_id,
        alias=payload.alias,
        secret_type=payload.secret_type,
        encrypted=payload.encrypted,
        iv=payload.iv,
    )
    db.add(secret)
    db.commit()
    db.refresh(secret)
    return secret


def update_secret(db: Session, user_id: str, secret_id: str, payload: SecretUpdate) -> Secret | None:
    """
    Actualiza un secreto existente. Solo modifica los campos enviados.

    :param db: Sesión de base de datos.
    :param user_id: UUID del usuario autenticado.
    :param secret_id: UUID del secreto.
    :param payload: Campos a actualizar.
    :return: Secreto actualizado o None si no existe.
    """
    secret = get_secret(db, user_id, secret_id)
    if not secret:
        return None

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(secret, field, value)

    secret.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(secret)
    return secret


def delete_secret(db: Session, user_id: str, secret_id: str) -> bool:
    """
    Elimina un secreto del vault.

    :param db: Sesión de base de datos.
    :param user_id: UUID del usuario autenticado.
    :param secret_id: UUID del secreto.
    :return: True si se eliminó, False si no existía.
    """
    secret = get_secret(db, user_id, secret_id)
    if not secret:
        return False

    db.delete(secret)
    db.commit()
    return True
