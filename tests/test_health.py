"""Tests de integracion para el endpoint de salud de la API y la base de datos."""


def test_health_when_database_is_available_returns_ok(client, database_execute_spy):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    executed_statement = database_execute_spy.call_args.args[0]
    assert str(executed_statement) == "SELECT 1"


def test_health_without_authentication_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_when_called_repeatedly_does_not_modify_database(
    client,
    db,
    database_execute_spy,
):
    client.get("/api/health")
    client.get("/api/health")

    assert database_execute_spy.call_count == 2
    assert not db.new
    assert not db.dirty
    assert not db.deleted


def test_health_when_database_is_unavailable_returns_503(client, unavailable_database):
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "database": "unavailable",
    }


def test_health_when_database_is_unavailable_does_not_expose_error_details(
    client,
    unavailable_database,
):
    response = client.get("/api/health")

    assert response.status_code == 503
    response_content = response.text.lower()
    assert "database unavailable" not in response_content
    assert "database_url" not in response_content
    assert "password" not in response_content
