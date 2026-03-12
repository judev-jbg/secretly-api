"""Tests de integración para los endpoints de autenticación."""

import pytest


class TestRegister:
    """Tests para POST /auth/register."""

    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "password123",
            "salt": "c2FsdA==",
        })
        assert res.status_code == 201
        assert res.json()["message"] == "User registered successfully"

    def test_register_duplicate_email(self, client, registered_user):
        res = client.post("/api/auth/register", json=registered_user)
        assert res.status_code == 409

    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "salt": "c2FsdA==",
        })
        assert res.status_code == 422


class TestLogin:
    """Tests para POST /auth/login."""

    def test_login_success(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["salt"] == registered_user["salt"]
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert res.status_code == 401


class TestRefresh:
    """Tests para POST /auth/refresh."""

    def test_refresh_success(self, client, registered_user):
        login_res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh_token = login_res.json()["refresh_token"]

        res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_refresh_invalid_token(self, client):
        res = client.post("/api/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert res.status_code == 401

    def test_refresh_with_access_token_fails(self, client, registered_user):
        """Un access token no debe poder usarse como refresh token."""
        login_res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        access_token = login_res.json()["access_token"]

        res = client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert res.status_code == 401


class TestForgotPassword:
    """Tests para POST /auth/forgot-password."""

    def test_forgot_password_existing_email(self, client, registered_user):
        """Siempre retorna 200 aunque el email no exista (anti-enumeration)."""
        res = client.post("/api/auth/forgot-password", json={"email": registered_user["email"]})
        assert res.status_code == 200

    def test_forgot_password_unknown_email(self, client):
        res = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
        assert res.status_code == 200


class TestResetPassword:
    """Tests para POST /auth/reset-password."""

    def _get_reset_token(self, client, registered_user, db):
        """Helper: genera un token de reset directamente en la DB."""
        from app.services.auth_service import create_reset_token
        return create_reset_token(db, registered_user["email"])

    def test_reset_password_success(self, client, registered_user, db):
        token = self._get_reset_token(client, registered_user, db)
        res = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "newpassword456",
        })
        assert res.status_code == 200

        # Verificar que el login funciona con la nueva contraseña
        login_res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "newpassword456",
        })
        assert login_res.status_code == 200

    def test_reset_password_invalid_token(self, client):
        res = client.post("/api/auth/reset-password", json={
            "token": "invalid-token",
            "new_password": "newpassword456",
        })
        assert res.status_code == 400

    def test_reset_does_not_change_salt(self, client, registered_user, db):
        """El salt no debe cambiar tras un reset (la encryption_key se preserva)."""
        from app.models.user import User
        user_before = db.query(User).filter(User.email == registered_user["email"]).first()
        salt_before = user_before.salt

        token = self._get_reset_token(client, registered_user, db)
        client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "newpassword456",
        })

        db.refresh(user_before)
        assert user_before.salt == salt_before
