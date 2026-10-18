"""Pydantic schemas for secret endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SecretType = Literal["token", "database", "login", "ssh", "api_key"]


def _normalize_alias(value: str) -> str:
    alias = value.strip()
    if not alias:
        raise ValueError("Alias cannot be empty")
    if len(alias) > 255:
        raise ValueError("Alias cannot exceed 255 characters")
    return alias


class SecretCreate(BaseModel):
    """Encrypted secret creation payload."""

    alias: str
    secret_type: SecretType
    encrypted: str
    iv: str

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str) -> str:
        return _normalize_alias(value)


class SecretUpdate(BaseModel):
    """Editable fields; the original secret type is immutable."""

    alias: str | None = None
    encrypted: str | None = None
    iv: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        return _normalize_alias(value) if value is not None else None


class SecretMeta(BaseModel):
    """Public secret metadata without encrypted content."""

    id: str
    alias: str
    secret_type: str
    created_at: datetime
    updated_at: datetime
    is_locked: bool = False

    model_config = {"from_attributes": True}


class SecretDetail(SecretMeta):
    """Secret metadata plus client-encrypted content."""

    encrypted: str
    iv: str


class UnlockTokenRequest(BaseModel):
    """One-time token delivered by email."""

    token: str = Field(min_length=16, max_length=255)


class UnlockAttemptResponse(BaseModel):
    """Remaining attempts before a security lock."""

    attempts_remaining: int = Field(ge=0, le=2)
