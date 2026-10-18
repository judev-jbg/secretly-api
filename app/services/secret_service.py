"""Business logic for encrypted secrets."""

import hashlib
import hmac
import secrets as token_secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.secret import Secret
from app.schemas.secret import SecretCreate, SecretUpdate


MAX_UNLOCK_ATTEMPTS = 3
UNDO_WINDOW_SECONDS = 5


class AliasConflictError(ValueError):
    """An active secret already uses the normalized alias."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _active_query(db: Session, user_id: str):
    return db.query(Secret).filter(
        Secret.user_id == user_id,
        Secret.deleted_at.is_(None),
    )


def _alias_exists(
    db: Session, user_id: str, alias: str, exclude_secret_id: str | None = None
) -> bool:
    query = _active_query(db, user_id).filter(
        func.lower(func.trim(Secret.alias)) == alias.strip().lower()
    )
    if exclude_secret_id:
        query = query.filter(Secret.id != exclude_secret_id)
    return db.query(query.exists()).scalar()


def get_secrets(db: Session, user_id: str) -> list[Secret]:
    return _active_query(db, user_id).order_by(Secret.created_at.desc()).all()


def get_secret(db: Session, user_id: str, secret_id: str) -> Secret | None:
    return _active_query(db, user_id).filter(Secret.id == secret_id).first()


def get_deleted_secret(db: Session, user_id: str, secret_id: str) -> Secret | None:
    return db.query(Secret).filter(
        Secret.id == secret_id,
        Secret.user_id == user_id,
        Secret.deleted_at.is_not(None),
    ).first()


def create_secret(db: Session, user_id: str, payload: SecretCreate) -> Secret:
    if _alias_exists(db, user_id, payload.alias):
        raise AliasConflictError("Secret alias already exists")
    secret = Secret(
        id=str(uuid.uuid4()),
        user_id=user_id,
        alias=payload.alias,
        secret_type=payload.secret_type,
        encrypted=payload.encrypted,
        iv=payload.iv,
    )
    db.add(secret)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AliasConflictError("Secret alias already exists") from exc
    db.refresh(secret)
    return secret


def update_secret(
    db: Session, user_id: str, secret_id: str, payload: SecretUpdate
) -> Secret | None:
    secret = get_secret(db, user_id, secret_id)
    if not secret:
        return None
    if payload.alias is not None and _alias_exists(
        db, user_id, payload.alias, exclude_secret_id=secret_id
    ):
        raise AliasConflictError("Secret alias already exists")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(secret, field, value)
    secret.updated_at = _utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AliasConflictError("Secret alias already exists") from exc
    db.refresh(secret)
    return secret


def delete_secret(db: Session, user_id: str, secret_id: str) -> bool:
    secret = get_secret(db, user_id, secret_id)
    if not secret:
        return False
    secret.deleted_at = _utcnow()
    db.commit()
    return True


def restore_secret(db: Session, user_id: str, secret_id: str) -> Secret | None:
    secret = get_deleted_secret(db, user_id, secret_id)
    if not secret:
        return None
    if _utcnow() - _as_utc(secret.deleted_at) > timedelta(seconds=UNDO_WINDOW_SECONDS):
        raise ValueError("Undo window expired")
    if _alias_exists(db, user_id, secret.alias, exclude_secret_id=secret_id):
        raise AliasConflictError("Secret alias already exists")
    secret.deleted_at = None
    secret.updated_at = _utcnow()
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AliasConflictError("Secret alias already exists") from exc
    db.refresh(secret)
    return secret


def register_unlock_failure(
    db: Session, user_id: str, secret_id: str
) -> tuple[Secret | None, int, str | None]:
    secret = _active_query(db, user_id).filter(Secret.id == secret_id).with_for_update().first()
    if not secret:
        return None, 0, None
    if secret.locked_at is not None:
        return secret, 0, None
    secret.failed_unlock_attempts += 1
    token = None
    if secret.failed_unlock_attempts >= MAX_UNLOCK_ATTEMPTS:
        token = token_secrets.token_urlsafe(32)
        secret.locked_at = _utcnow()
        secret.unlock_token_hash = _token_hash(token)
        secret.unlock_token_expires = _utcnow() + timedelta(
            minutes=settings.secret_unlock_token_expire_minutes
        )
    db.commit()
    db.refresh(secret)
    return secret, max(0, MAX_UNLOCK_ATTEMPTS - secret.failed_unlock_attempts), token


def register_unlock_success(db: Session, user_id: str, secret_id: str) -> bool:
    secret = get_secret(db, user_id, secret_id)
    if not secret or secret.locked_at is not None:
        return False
    secret.failed_unlock_attempts = 0
    db.commit()
    return True


def unlock_with_token(db: Session, user_id: str, secret_id: str, token: str) -> bool | None:
    secret = _active_query(db, user_id).filter(Secret.id == secret_id).with_for_update().first()
    if not secret:
        return None
    now = _utcnow()
    token_valid = (
        secret.locked_at is not None
        and secret.unlock_token_hash is not None
        and secret.unlock_token_expires is not None
        and _as_utc(secret.unlock_token_expires) >= now
        and hmac.compare_digest(secret.unlock_token_hash, _token_hash(token))
    )
    if not token_valid:
        return False
    secret.failed_unlock_attempts = 0
    secret.locked_at = None
    secret.unlock_token_hash = None
    secret.unlock_token_expires = None
    db.commit()
    return True
