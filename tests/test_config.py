"""Tests para la configuración portable entre local, Render y Supabase."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_uses_supabase_url_when_provided(monkeypatch):
    """Una URL completa debe permitir configurar Render sin variables DB_* separadas."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres.project:password@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require",
    )
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(
        secret_key="test-secret-key",
        cors_origins=["https://app.example.com"],
        _env_file=None,
    )

    assert settings.database_url == (
        "postgresql://postgres.project:password@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )


def test_database_url_builds_from_component_variables_when_not_provided(monkeypatch):
    """La configuración local existente debe seguir funcionando."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_name="secretly",
        db_user="postgres",
        db_password="p@ss word",
        secret_key="test-secret-key",
        cors_origins=["http://localhost:5173"],
        _env_file=None,
    )

    assert settings.database_url == "postgresql://postgres:p%40ss+word@localhost:5432/secretly"


def test_cors_origins_accepts_comma_separated_production_origins(monkeypatch):
    """Render puede recibir varios dominios sin exigir una lista JSON."""
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, https://admin.example.com")

    settings = Settings(
        db_host="localhost",
        db_port=5432,
        db_name="secretly",
        db_user="postgres",
        db_password="password",
        secret_key="test-secret-key",
        _env_file=None,
    )

    assert settings.cors_origins == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


def test_configuration_requires_database_settings_when_database_url_is_missing(monkeypatch):
    """Un despliegue incompleto debe fallar antes de servir peticiones."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        Settings(secret_key="test-secret-key", _env_file=None)
