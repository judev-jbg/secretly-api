"""Authenticated endpoints for the encrypted vault."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.schemas.secret import (
    SecretCreate,
    SecretDetail,
    SecretMeta,
    SecretUpdate,
    UnlockAttemptResponse,
    UnlockTokenRequest,
)
from app.services import secret_service
from app.services.email_service import send_secret_unlock_email


router = APIRouter(prefix="/api/secrets", tags=["secrets"])
bearer = HTTPBearer(description="JWT access token obtained from /auth/login")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    user_id = decode_token(credentials.credentials, expected_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


@router.get("", response_model=list[SecretMeta], summary="List secrets")
def list_secrets(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return secret_service.get_secrets(db, user_id)


@router.get("/{secret_id}", response_model=SecretDetail, summary="Get secret")
def get_secret(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    secret = secret_service.get_secret(db, user_id, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    if secret.is_locked:
        raise HTTPException(status_code=423, detail="Secret locked for security")
    return secret


@router.post(
    "", response_model=SecretMeta, status_code=status.HTTP_201_CREATED,
    summary="Create secret",
)
def create_secret(
    payload: SecretCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return secret_service.create_secret(db, user_id, payload)
    except secret_service.AliasConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/{secret_id}", response_model=SecretMeta, summary="Update secret")
def update_secret(
    secret_id: str,
    payload: SecretUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        secret = secret_service.update_secret(db, user_id, secret_id, payload)
    except secret_service.AliasConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not secret_service.delete_secret(db, user_id, secret_id):
        raise HTTPException(status_code=404, detail="Secret not found")


@router.post("/{secret_id}/restore", response_model=SecretMeta)
def restore_secret(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        secret = secret_service.restore_secret(db, user_id, secret_id)
    except (ValueError, secret_service.AliasConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


@router.post(
    "/{secret_id}/unlock-failure",
    response_model=UnlockAttemptResponse,
)
async def register_unlock_failure(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    secret, attempts_remaining, token = secret_service.register_unlock_failure(
        db, user_id, secret_id
    )
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    if secret.is_locked:
        if token:
            await send_secret_unlock_email(secret.user.email, secret.alias, token)
        raise HTTPException(status_code=423, detail="Secret locked for security")
    return {"attempts_remaining": attempts_remaining}


@router.post("/{secret_id}/unlock-success", status_code=status.HTTP_204_NO_CONTENT)
def register_unlock_success(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not secret_service.register_unlock_success(db, user_id, secret_id):
        secret = secret_service.get_secret(db, user_id, secret_id)
        if secret and secret.is_locked:
            raise HTTPException(status_code=423, detail="Secret locked for security")
        raise HTTPException(status_code=404, detail="Secret not found")


@router.post("/{secret_id}/unlock", status_code=status.HTTP_204_NO_CONTENT)
def unlock_secret(
    secret_id: str,
    payload: UnlockTokenRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = secret_service.unlock_with_token(db, user_id, secret_id, payload.token)
    if result is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    if not result:
        raise HTTPException(status_code=400, detail="Invalid or expired unlock token")
