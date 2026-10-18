"""Fixtures compartidos para los tests del backend.
Usa SQLite en un archivo de test que se recrea antes de cada test.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
import app.models  # noqa: F401 - registra modelos en Base.metadata


TEST_DB_PATH = "./test_secretly.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"


def make_engine():
    """Crea un engine fresco con una nueva DB de test."""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db():
    """Sesión de test sobre una DB limpia por cada test."""
    engine = make_engine()
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    """Cliente HTTP con la sesión de test inyectada."""
    from app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.services.email_service.fm.send_message", new_callable=AsyncMock):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client):
    """Registra un usuario de prueba y retorna sus credenciales."""
    payload = {"email": "test@example.com", "password": "password123", "salt": "c2FsdGJhc2U2NA=="}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201, res.json()
    return payload


@pytest.fixture
def secret_payload_factory():
    """Construye payloads cifrados válidos sin compartir estado entre tests."""
    def factory(alias="mi-token", secret_type="token"):
        return {
            "alias": alias,
            "secret_type": secret_type,
            "encrypted": "Y2lwaGVydGV4dGJhc2U2NA==",
            "iv": "aXZiYXNlNjQ=",
        }

    return factory


@pytest.fixture
def other_registered_user(client):
    """Registra un segundo usuario para comprobar aislamiento entre cuentas."""
    payload = {
        "email": "other@example.com",
        "password": "password456",
        "salt": "b3RoZXJzYWx0YmFzZTY0",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.json()
    return payload


@pytest.fixture
def database_execute_spy(db, monkeypatch):
    """Permite comprobar las consultas ejecutadas por el health check."""
    execute_spy = MagicMock(wraps=db.execute)
    monkeypatch.setattr(db, "execute", execute_spy)
    return execute_spy


@pytest.fixture
def unavailable_database(db, monkeypatch):
    """Simula una base de datos no disponible sin incluir datos sensibles."""
    execute_mock = MagicMock(side_effect=SQLAlchemyError("database unavailable"))
    monkeypatch.setattr(db, "execute", execute_mock)
    return execute_mock
