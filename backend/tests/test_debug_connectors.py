import pytest

from app.debugging.connectors import authenticate_connector, enroll_connector


def test_connector_uses_its_own_revocable_credential_and_environment(db):
    from uuid import uuid4

    from app.auth.models import User

    actor = User(
        id=uuid4(), email="connector-admin@example.com", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    connector, token = enroll_connector(db, actor.id, "Laptop")
    assert connector.token_hash != token
    assert authenticate_connector(db, connector.id, token).id == connector.id
    with pytest.raises(ValueError, match="connector_not_authorized"):
        authenticate_connector(db, connector.id, "wrong-token")
    connector.revoked = True
    with pytest.raises(ValueError, match="connector_not_authorized"):
        authenticate_connector(db, connector.id, token)


def test_connector_enrollment_requires_admin_csrf_and_scoped_bearer(client, db):
    from uuid import uuid4

    from tests.admin.test_ai_task_settings_api import _admin

    base = "/api/v1/admin/diagnostics/connectors"
    assert client.get(base).status_code == 401
    _admin(client, db)
    assert client.post(base, json={"name": "Laptop"}).status_code == 403
    response = client.post(
        base, json={"name": "Laptop"}, headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    row = response.json()
    assert "token" not in str(client.get(base).json())
    target = f"/api/v1/debug-connectors/{row['id']}/poll"
    assert client.post(target, json={}).status_code == 401
    bearer = {"Authorization": "Bearer " + row["token"]}
    assert client.post(target, json={}, headers=bearer).status_code == 200
    assert (
        client.post(f"/api/v1/debug-connectors/{uuid4()}/poll", json={}, headers=bearer).status_code
        == 401
    )
    assert (
        client.post(
            base + f"/{row['id']}/revoke", headers={"Origin": "http://localhost:5173"}
        ).status_code
        == 200
    )
    assert client.post(target, json={}, headers=bearer).status_code == 401


def test_runtime_heartbeat_exposes_only_closed_setup_codes_to_admins(client, db):
    from tests.admin.test_ai_task_settings_api import _admin

    _admin(client, db)
    base = "/api/v1/admin/diagnostics/connectors"
    row = client.post(
        base, json={"name": "Germany"}, headers={"Origin": "http://localhost:5173"}
    ).json()
    heartbeat = f"/api/v1/debug-connectors/{row['id']}/heartbeat"
    bearer = {"Authorization": "Bearer " + row["token"]}
    payload = {
        "repository_head": "a" * 40,
        "runtime_error_code": "dedicated_codex_authentication_required",
    }
    assert client.post(heartbeat, json=payload).status_code == 401
    assert client.post(heartbeat, json=payload, headers=bearer).status_code == 200
    assert (
        client.get(base).json()[0]["capabilities"]["runtime_error_code"]
        == payload["runtime_error_code"]
    )
    assert (
        client.post(
            heartbeat,
            json={**payload, "runtime_error_code": "arbitrary-secret-error"},
            headers=bearer,
        ).status_code
        == 422
    )
    # An older connector does not have to supply the additive health field.
    assert (
        client.post(heartbeat, json={"repository_head": "a" * 40}, headers=bearer).status_code
        == 200
    )
