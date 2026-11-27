import pytest

from app.debugging.connectors import authenticate_connector, enroll_connector


@pytest.mark.parametrize("execution_role", [None, "repository_worker"])
def test_enrolled_runtime_reconnects_to_real_routes_and_reuses_registration_after_restart(
    client, db, tmp_path, execution_role
):
    import asyncio
    import json
    import time

    import httpx

    from app.debugging.connector import LaptopConnector, load_configuration
    from tests.admin.test_ai_task_settings_api import _admin
    from tests.test_debug_tools import repository

    _admin(client, db)
    base = "/api/v1/admin/diagnostics/connectors"
    response = client.post(
        base,
        json={"name": "Germany integration runtime"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    enrollment = response.json()
    source = tmp_path / "repository"
    repository(source)
    if execution_role:
        from app.debugging.tools import _git

        _git(source, "remote", "add", "origin", "git@github.com:mohammad4242/fitician.git")
    config_path = tmp_path / "connector.json"
    config_path.write_text(
        json.dumps(
            {
                **({"execution_role": execution_role} if execution_role else {}),
                "id": enrollment["id"],
                "token": enrollment["token"],
                "server": "http://127.0.0.1",
                "repository_name": enrollment["repository"],
                "environment": enrollment["environment"],
                "repository": str(source),
                "workspace_root": str(tmp_path / "runtime"),
                "github_enabled": False,
                "ci_enabled": False,
            }
        )
    )
    config_path.chmod(0o600)

    async def run():
        recovered = asyncio.Event()

        class OneConnectionFailure(httpx.AsyncBaseTransport):
            def __init__(self):
                self.inner = httpx.ASGITransport(app=client.app)
                self.failures = 0

            async def handle_async_request(self, request):
                if self.failures == 0:
                    self.failures += 1
                    raise httpx.ConnectError("controlled offline fixture", request=request)
                result = await self.inner.handle_async_request(request)
                if request.url.path.endswith("/heartbeat") and result.status_code == 200:
                    recovered.set()
                return result

            async def aclose(self):
                await self.inner.aclose()

        transport = OneConnectionFailure()
        async with httpx.AsyncClient(transport=transport) as http:
            runtime = LaptopConnector(load_configuration(config_path), http)
            task = asyncio.create_task(runtime.run())
            try:
                await asyncio.wait_for(recovered.wait(), timeout=12)
                for _ in range(100):
                    if runtime.connection_error is None and runtime.last_contact > 0:
                        break
                    await asyncio.sleep(0.01)
                assert runtime.connection_error is None
                assert time.monotonic() - runtime.last_contact < 2
                assert transport.failures == 1
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

            restarted = LaptopConnector(load_configuration(config_path), http)
            await restarted.heartbeat()
            assert restarted.connection_error is None and restarted.last_contact > 0
            return restarted

    runtime = asyncio.run(run())
    rows = client.get(base).json()
    assert len(rows) == 1 and rows[0]["id"] == enrollment["id"]
    assert rows[0]["last_seen"] is not None
    assert enrollment["token"] not in json.dumps(rows)
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert runtime.config["id"] == enrollment["id"]


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
