"""Tests de integración para los endpoints de secretos (CRUD)."""

import pytest


# ─── Helpers ───────────────────────────────────────────────────────────────

def get_auth_headers(client, registered_user):
    """Retorna los headers de autorización para un usuario registrado."""
    res = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_secret(alias="mi-token", secret_type="token"):
    """Payload base para crear un secreto."""
    return {
        "alias": alias,
        "secret_type": secret_type,
        "encrypted": "Y2lwaGVydGV4dGJhc2U2NA==",
        "iv": "aXZiYXNlNjQ=",
    }


# ─── Sin autenticación ──────────────────────────────────────────────────────

class TestSecretsAuth:
    """Verifica que todos los endpoints requieran token Bearer."""

    def test_list_without_token(self, client):
        assert client.get("/api/secrets").status_code == 401

    def test_get_without_token(self, client):
        assert client.get("/api/secrets/some-id").status_code == 401

    def test_create_without_token(self, client):
        assert client.post("/api/secrets", json=make_secret()).status_code == 401

    def test_update_without_token(self, client):
        assert client.put("/api/secrets/some-id", json={"alias": "x"}).status_code == 401

    def test_delete_without_token(self, client):
        assert client.delete("/api/secrets/some-id").status_code == 401


# ─── Listar secretos ────────────────────────────────────────────────────────

class TestListSecrets:
    """Tests para GET /secrets."""

    def test_list_empty(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        res = client.get("/api/secrets", headers=headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_list_returns_created_secrets(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        client.post("/api/secrets", json=make_secret("token-gh", "token"), headers=headers)
        client.post("/api/secrets", json=make_secret("db-prod", "database"), headers=headers)

        res = client.get("/api/secrets", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_list_does_not_expose_encrypted_blob(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        client.post("/api/secrets", json=make_secret(), headers=headers)

        res = client.get("/api/secrets", headers=headers)
        item = res.json()[0]
        assert "encrypted" not in item
        assert "iv" not in item

    def test_list_only_own_secrets(self, client, registered_user, db):
        """Un usuario no debe ver los secretos de otro."""
        other = {"email": "other@example.com", "password": "pass123", "salt": "c2FsdA=="}
        client.post("/api/auth/register", json=other)
        other_headers = get_auth_headers(client, other)
        client.post("/api/secrets", json=make_secret("otro-token"), headers=other_headers)

        headers = get_auth_headers(client, registered_user)
        res = client.get("/api/secrets", headers=headers)
        assert res.json() == []


# ─── Obtener un secreto ─────────────────────────────────────────────────────

class TestGetSecret:
    """Tests para GET /secrets/{id}."""

    def test_get_existing_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        created = client.post("/api/secrets", json=make_secret(), headers=headers).json()

        res = client.get(f"/api/secrets/{created['id']}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == created["id"]
        assert "encrypted" in data
        assert "iv" in data

    def test_get_nonexistent_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        res = client.get("/api/secrets/00000000-0000-0000-0000-000000000000", headers=headers)
        assert res.status_code == 404

    def test_get_other_user_secret_returns_404(self, client, registered_user, db):
        """Obtener el secreto de otro usuario retorna 404 (no revelar existencia)."""
        other = {"email": "other@example.com", "password": "pass123", "salt": "c2FsdA=="}
        client.post("/api/auth/register", json=other)
        other_headers = get_auth_headers(client, other)
        other_secret = client.post("/api/secrets", json=make_secret(), headers=other_headers).json()

        headers = get_auth_headers(client, registered_user)
        res = client.get(f"/api/secrets/{other_secret['id']}", headers=headers)
        assert res.status_code == 404


# ─── Crear secreto ──────────────────────────────────────────────────────────

class TestCreateSecret:
    """Tests para POST /secrets."""

    def test_create_token_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        res = client.post("/api/secrets", json=make_secret("gh-token", "token"), headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["alias"] == "gh-token"
        assert data["secret_type"] == "token"
        assert "id" in data
        assert "created_at" in data

    def test_create_all_secret_types(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        for t in ["token", "database", "login", "ssh", "api_key"]:
            res = client.post("/api/secrets", json=make_secret(f"secret-{t}", t), headers=headers)
            assert res.status_code == 201, f"Failed for type: {t}"

    def test_create_invalid_secret_type(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        payload = make_secret()
        payload["secret_type"] = "invalid_type"
        res = client.post("/api/secrets", json=payload, headers=headers)
        assert res.status_code == 422


# ─── Actualizar secreto ─────────────────────────────────────────────────────

class TestUpdateSecret:
    """Tests para PUT /secrets/{id}."""

    def test_update_alias(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        created = client.post("/api/secrets", json=make_secret("old-alias"), headers=headers).json()

        res = client.put(f"/api/secrets/{created['id']}", json={"alias": "new-alias"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["alias"] == "new-alias"

    def test_update_encrypted_blob(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        created = client.post("/api/secrets", json=make_secret(), headers=headers).json()

        new_enc = "bmV3Y2lwaGVydGV4dA=="
        res = client.put(
            f"/api/secrets/{created['id']}",
            json={"encrypted": new_enc, "iv": "bmV3aXY="},
            headers=headers,
        )
        assert res.status_code == 200

        detail = client.get(f"/api/secrets/{created['id']}", headers=headers).json()
        assert detail["encrypted"] == new_enc

    def test_update_nonexistent_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        res = client.put(
            "/api/secrets/00000000-0000-0000-0000-000000000000",
            json={"alias": "x"},
            headers=headers,
        )
        assert res.status_code == 404

    def test_update_other_user_secret_returns_404(self, client, registered_user, db):
        other = {"email": "other@example.com", "password": "pass123", "salt": "c2FsdA=="}
        client.post("/api/auth/register", json=other)
        other_headers = get_auth_headers(client, other)
        other_secret = client.post("/api/secrets", json=make_secret(), headers=other_headers).json()

        headers = get_auth_headers(client, registered_user)
        res = client.put(f"/api/secrets/{other_secret['id']}", json={"alias": "hack"}, headers=headers)
        assert res.status_code == 404


# ─── Eliminar secreto ────────────────────────────────────────────────────────

class TestDeleteSecret:
    """Tests para DELETE /secrets/{id}."""

    def test_delete_existing_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        created = client.post("/api/secrets", json=make_secret(), headers=headers).json()

        res = client.delete(f"/api/secrets/{created['id']}", headers=headers)
        assert res.status_code == 204

        res = client.get(f"/api/secrets/{created['id']}", headers=headers)
        assert res.status_code == 404

    def test_delete_nonexistent_secret(self, client, registered_user):
        headers = get_auth_headers(client, registered_user)
        res = client.delete("/api/secrets/00000000-0000-0000-0000-000000000000", headers=headers)
        assert res.status_code == 404

    def test_delete_other_user_secret_returns_404(self, client, registered_user, db):
        other = {"email": "other@example.com", "password": "pass123", "salt": "c2FsdA=="}
        client.post("/api/auth/register", json=other)
        other_headers = get_auth_headers(client, other)
        other_secret = client.post("/api/secrets", json=make_secret(), headers=other_headers).json()

        headers = get_auth_headers(client, registered_user)
        res = client.delete(f"/api/secrets/{other_secret['id']}", headers=headers)
        assert res.status_code == 404
        # El secreto del otro usuario debe seguir intacto
        assert client.get(f"/api/secrets/{other_secret['id']}", headers=other_headers).status_code == 200
