"""Esquemas Pydantic para los endpoints de secretos."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


SecretType = Literal["token", "database", "login", "ssh", "api_key"]


class SecretCreate(BaseModel):
    """Payload para crear un nuevo secreto."""
    alias: str
    secret_type: SecretType
    encrypted: str
    iv: str


class SecretUpdate(BaseModel):
    """Payload para actualizar un secreto existente. Todos los campos son opcionales."""
    alias: str | None = None
    secret_type: SecretType | None = None
    encrypted: str | None = None
    iv: str | None = None


class SecretMeta(BaseModel):
    """Representación pública de un secreto (sin blob cifrado)."""
    id: str
    alias: str
    secret_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SecretDetail(SecretMeta):
    """Representación completa de un secreto (incluye blob cifrado)."""
    encrypted: str
    iv: str
