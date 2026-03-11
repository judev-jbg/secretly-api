"""Endpoints CRUD para el vault de secretos."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.schemas.secret import SecretCreate, SecretUpdate, SecretMeta, SecretDetail
from app.services import secret_service

router = APIRouter(prefix="/secrets", tags=["secrets"])


def get_current_user_id(
    authorization: str = Depends(lambda: None),
) -> str:
    """Placeholder — reemplazado por la dependency real de abajo."""
    pass


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    """
    Dependency que valida el JWT Bearer y retorna el user_id.
    Lanza 401 si el token es inválido o expirado.
    """
    user_id = decode_token(credentials.credentials, expected_type="access")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user_id


@router.get("", response_model=list[SecretMeta])
def list_secrets(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna la lista de secretos del usuario (alias y tipo, sin blobs)."""
    return secret_service.get_secrets(db, user_id)


@router.get("/{secret_id}", response_model=SecretDetail)
def get_secret(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna un secreto completo incluyendo el blob cifrado."""
    secret = secret_service.get_secret(db, user_id, secret_id)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return secret


@router.post("", response_model=SecretMeta, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: SecretCreate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Crea un nuevo secreto cifrado en el vault."""
    return secret_service.create_secret(db, user_id, payload)


@router.put("/{secret_id}", response_model=SecretMeta)
def update_secret(
    secret_id: str,
    payload: SecretUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza un secreto existente. Solo modifica los campos enviados."""
    secret = secret_service.update_secret(db, user_id, secret_id, payload)
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return secret


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    secret_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina un secreto del vault."""
    deleted = secret_service.delete_secret(db, user_id, secret_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
