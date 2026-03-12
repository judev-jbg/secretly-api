"""Esquemas Pydantic para los endpoints de secretos."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SecretType = Literal["token", "database", "login", "ssh", "api_key"]


class SecretCreate(BaseModel):
    """Payload para crear un nuevo secreto."""
    alias: str = Field(
        description="Nombre descriptivo del secreto",
        examples=["AWS Production Key"],
    )
    secret_type: SecretType = Field(
        description="Categoría del secreto",
        examples=["api_key"],
    )
    encrypted: str = Field(
        description="Contenido del secreto cifrado en el cliente (base64)",
        examples=["U2FsdGVkX1+vupppZksvRf5pq5g5XjFRIipRkwB0K1Y="],
    )
    iv: str = Field(
        description="Vector de inicialización usado para el cifrado (base64)",
        examples=["3f8a2b1c4d5e6f7a8b9c0d1e"],
    )


class SecretUpdate(BaseModel):
    """Payload para actualizar un secreto existente. Todos los campos son opcionales."""
    alias: str | None = Field(
        default=None,
        description="Nuevo nombre descriptivo",
        examples=["AWS Staging Key"],
    )
    secret_type: SecretType | None = Field(
        default=None,
        description="Nueva categoría del secreto",
        examples=["api_key"],
    )
    encrypted: str | None = Field(
        default=None,
        description="Nuevo contenido cifrado (base64)",
        examples=["U2FsdGVkX1+vupppZksvRf5pq5g5XjFRIipRkwB0K1Y="],
    )
    iv: str | None = Field(
        default=None,
        description="Nuevo vector de inicialización (base64)",
        examples=["3f8a2b1c4d5e6f7a8b9c0d1e"],
    )


class SecretMeta(BaseModel):
    """Representación pública de un secreto (sin blob cifrado)."""
    id: str = Field(
        description="Identificador único del secreto (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    alias: str = Field(
        description="Nombre descriptivo del secreto",
        examples=["AWS Production Key"],
    )
    secret_type: str = Field(
        description="Categoría del secreto",
        examples=["api_key"],
    )
    created_at: datetime = Field(
        description="Fecha y hora de creación",
    )
    updated_at: datetime = Field(
        description="Fecha y hora de última actualización",
    )

    model_config = {"from_attributes": True}


class SecretDetail(SecretMeta):
    """Representación completa de un secreto (incluye blob cifrado)."""
    encrypted: str = Field(
        description="Contenido cifrado del secreto (base64)",
        examples=["U2FsdGVkX1+vupppZksvRf5pq5g5XjFRIipRkwB0K1Y="],
    )
    iv: str = Field(
        description="Vector de inicialización del cifrado (base64)",
        examples=["3f8a2b1c4d5e6f7a8b9c0d1e"],
    )
