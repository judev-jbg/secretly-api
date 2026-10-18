"""Integration tests for the secure secret lifecycle."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.secret import Secret


def auth_headers(client, user):
    response = client.post(
        "/api/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_secret(client, headers, payload):
    response = client.post("/api/secrets", json=payload, headers=headers)
    assert response.status_code == 201, response.json()
    return response.json()


class TestUniqueAlias:
    def test_create_duplicate_active_alias_returns_conflict(
        self, client, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        create_secret(client, headers, secret_payload_factory(" Production "))

        response = client.post(
            "/api/secrets",
            json=secret_payload_factory("production"),
            headers=headers,
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Secret alias already exists"

    def test_same_alias_is_allowed_for_different_users(
        self, client, registered_user, other_registered_user, secret_payload_factory
    ):
        first_headers = auth_headers(client, registered_user)
        second_headers = auth_headers(client, other_registered_user)
        first = create_secret(
            client, first_headers, secret_payload_factory(" shared-alias ")
        )

        response = client.post(
            "/api/secrets",
            json=secret_payload_factory("shared-alias"),
            headers=second_headers,
        )

        assert response.status_code == 201
        assert first["alias"] == "shared-alias"

    def test_update_to_duplicate_alias_returns_conflict(
        self, client, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        create_secret(client, headers, secret_payload_factory("first"))
        second = create_secret(client, headers, secret_payload_factory("second"))

        response = client.put(
            f"/api/secrets/{second['id']}",
            json={"alias": " FIRST "},
            headers=headers,
        )

        assert response.status_code == 409

    def test_update_keeps_own_alias(self, client, registered_user, secret_payload_factory):
        headers = auth_headers(client, registered_user)
        secret = create_secret(client, headers, secret_payload_factory("my-alias"))

        response = client.put(
            f"/api/secrets/{secret['id']}",
            json={"alias": " My-Alias "},
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["alias"] == "My-Alias"


class TestImmutableSecretType:
    def test_update_rejects_secret_type(
        self, client, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        secret = create_secret(client, headers, secret_payload_factory())

        response = client.put(
            f"/api/secrets/{secret['id']}",
            json={"secret_type": "login"},
            headers=headers,
        )

        assert response.status_code == 422


class TestSoftDeleteAndRestore:
    def test_delete_hides_secret_but_keeps_database_row(
        self, client, db, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())

        response = client.delete(f"/api/secrets/{created['id']}", headers=headers)

        assert response.status_code == 204
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        assert stored.deleted_at is not None
        assert client.get("/api/secrets", headers=headers).json() == []
        assert client.get(f"/api/secrets/{created['id']}", headers=headers).status_code == 404

    def test_restore_within_undo_window_returns_secret_to_vault(
        self, client, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        client.delete(f"/api/secrets/{created['id']}", headers=headers)

        response = client.post(f"/api/secrets/{created['id']}/restore", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert len(client.get("/api/secrets", headers=headers).json()) == 1

    def test_restore_after_undo_window_returns_conflict(
        self, client, db, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        client.delete(f"/api/secrets/{created['id']}", headers=headers)
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        stored.deleted_at = datetime.now(timezone.utc) - timedelta(seconds=6)
        db.commit()

        response = client.post(f"/api/secrets/{created['id']}/restore", headers=headers)

        assert response.status_code == 409

    def test_deleted_alias_can_be_reused(
        self, client, db, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory("reusable"))
        client.delete(f"/api/secrets/{created['id']}", headers=headers)
        deleted = db.query(Secret).filter(Secret.id == created["id"]).one()

        response = client.post(
            "/api/secrets",
            json=secret_payload_factory(" REUSABLE "),
            headers=headers,
        )

        assert response.status_code == 201
        assert deleted.deleted_at is not None

    def test_other_user_cannot_restore_deleted_secret(
        self, client, registered_user, other_registered_user, secret_payload_factory
    ):
        owner_headers = auth_headers(client, registered_user)
        other_headers = auth_headers(client, other_registered_user)
        created = create_secret(client, owner_headers, secret_payload_factory())
        client.delete(f"/api/secrets/{created['id']}", headers=owner_headers)

        owner_restore = client.post(
            f"/api/secrets/{created['id']}/restore", headers=owner_headers
        )
        assert owner_restore.status_code == 200
        client.delete(f"/api/secrets/{created['id']}", headers=owner_headers)

        response = client.post(
            f"/api/secrets/{created['id']}/restore", headers=other_headers
        )

        assert response.status_code == 404


@pytest.fixture
def unlock_email_spy(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(
        "app.routers.secrets.send_secret_unlock_email", spy, raising=False
    )
    return spy


class TestSecurityLock:
    def test_third_failure_locks_secret_and_sends_token_email(
        self,
        client,
        db,
        registered_user,
        secret_payload_factory,
        unlock_email_spy,
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory("production-token"))

        first = client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)
        second = client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)
        third = client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)

        assert first.status_code == 200
        assert first.json()["attempts_remaining"] == 2
        assert second.json()["attempts_remaining"] == 1
        assert third.status_code == 423
        assert third.json()["detail"] == "Secret locked for security"
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        assert stored.locked_at is not None
        assert stored.unlock_token_hash
        unlock_email_spy.assert_awaited_once()
        email, alias, token = unlock_email_spy.await_args.args
        assert email == registered_user["email"]
        assert alias == "production-token"
        assert token not in third.text
        assert stored.unlock_token_hash != token

    def test_locked_secret_does_not_expose_encrypted_content(
        self, client, registered_user, secret_payload_factory, unlock_email_spy
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        for _ in range(3):
            client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)

        response = client.get(f"/api/secrets/{created['id']}", headers=headers)

        assert response.status_code == 423
        assert "encrypted" not in response.text

    def test_valid_token_unlocks_secret_and_is_single_use(
        self,
        client,
        db,
        registered_user,
        secret_payload_factory,
        unlock_email_spy,
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        for _ in range(3):
            client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)
        token = unlock_email_spy.await_args.args[2]

        response = client.post(
            f"/api/secrets/{created['id']}/unlock",
            json={"token": token},
            headers=headers,
        )

        assert response.status_code == 204
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        assert stored.locked_at is None
        assert stored.failed_unlock_attempts == 0
        assert stored.unlock_token_hash is None
        assert client.get(f"/api/secrets/{created['id']}", headers=headers).status_code == 200
        repeated = client.post(
            f"/api/secrets/{created['id']}/unlock",
            json={"token": token},
            headers=headers,
        )
        assert repeated.status_code == 400

    def test_invalid_or_expired_token_keeps_secret_locked(
        self,
        client,
        db,
        registered_user,
        secret_payload_factory,
        unlock_email_spy,
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        for _ in range(3):
            client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        stored.unlock_token_expires = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

        invalid = client.post(
            f"/api/secrets/{created['id']}/unlock",
            json={"token": "invalid-token-that-is-long-enough"},
            headers=headers,
        )
        expired = client.post(
            f"/api/secrets/{created['id']}/unlock",
            json={"token": unlock_email_spy.await_args.args[2]},
            headers=headers,
        )

        assert invalid.status_code == 400
        assert expired.status_code == 400
        db.refresh(stored)
        assert stored.locked_at is not None

    def test_unlock_success_resets_failures(
        self, client, db, registered_user, secret_payload_factory
    ):
        headers = auth_headers(client, registered_user)
        created = create_secret(client, headers, secret_payload_factory())
        client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)
        client.post(f"/api/secrets/{created['id']}/unlock-failure", headers=headers)

        response = client.post(
            f"/api/secrets/{created['id']}/unlock-success", headers=headers
        )

        assert response.status_code == 204
        stored = db.query(Secret).filter(Secret.id == created["id"]).one()
        assert stored.failed_unlock_attempts == 0

    def test_other_user_cannot_report_failure_or_unlock(
        self, client, registered_user, other_registered_user, secret_payload_factory
    ):
        owner_headers = auth_headers(client, registered_user)
        other_headers = auth_headers(client, other_registered_user)
        created = create_secret(client, owner_headers, secret_payload_factory())

        for _ in range(3):
            client.post(
                f"/api/secrets/{created['id']}/unlock-failure", headers=owner_headers
            )
        owner_locked = client.get(
            f"/api/secrets/{created['id']}", headers=owner_headers
        )
        assert owner_locked.status_code == 423

        failure = client.post(
            f"/api/secrets/{created['id']}/unlock-failure", headers=other_headers
        )
        unlock = client.post(
            f"/api/secrets/{created['id']}/unlock",
            json={"token": "some-token-that-is-long-enough"},
            headers=other_headers,
        )

        assert failure.status_code == 404
        assert unlock.status_code == 404
