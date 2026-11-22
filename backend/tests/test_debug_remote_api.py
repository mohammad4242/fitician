import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from tests.test_debug_germany_provider import KEY, credential


def test_iran_worker_delegates_whole_api_turn_without_any_application_key(
    db, test_settings, monkeypatch
):
    from app.debugging import worker
    from tests.test_debug_gateway import setup_run

    _, run, target, _ = setup_run(db)
    target.last_seen = datetime.now(UTC)
    revision = str(uuid4())
    target.capabilities = {
        "supports_api": True,
        "api_provider": "openrouter",
        "api_credential_revision": revision,
    }
    run.config_snapshot = {
        "enabled": True,
        "execution_backend": "api",
        "provider": "openrouter",
        "primary_model_id": "chosen/model",
        "connector_id": str(target.id),
    }
    seen = []

    async def remote(engine, identifier, lease, key, tool, args):
        seen.append((identifier, tool, args))
        return {"output": "مدرک بررسی شد.", "mode": "api_tools", "model": "chosen/model"}

    def forbidden(*args, **kwargs):
        raise AssertionError("Production application key accessed")

    monkeypatch.setattr(worker, "CredentialCipher", forbidden, raising=False)
    monkeypatch.setattr(worker, "get_engine", lambda _: db.connection())
    monkeypatch.setattr(worker, "call_connector", remote)
    db.flush()
    asyncio.run(worker.execute_run(test_settings, run.id, run.lease_token))
    db.expire_all()
    assert run.state == "completed"
    assert len(seen) == 1 and seen[0][1] == "fitician_api_turn"
    assert seen[0][2]["messages"][-1]["content"] == "inspect"


def test_api_credential_rotation_does_not_invalidate_a_codex_profile_but_pins_api_runs(db):
    from app.debugging.runtime_profiles import execution_capabilities
    from tests.test_debug_runtime_profiles import target_fixture

    _, target = target_fixture(db)
    target.capabilities = {"api_provider": "openrouter", "api_credential_revision": str(uuid4())}
    codex = execution_capabilities(target)
    api = execution_capabilities(target, backend="api")
    target.capabilities = {**target.capabilities, "api_credential_revision": str(uuid4())}
    assert execution_capabilities(target) == codex
    assert execution_capabilities(target, backend="api") != api


def test_connector_runs_the_api_model_and_repository_tool_with_separate_auth(tmp_path):
    from app.debugging.connector import LaptopConnector
    from app.debugging.germany_provider import GermanyProvider
    from tests.test_debug_tools import repository

    source = tmp_path / "repo"
    release = repository(source)
    private = tmp_path / "model-api.json"
    value = credential(private)
    submitted = []
    model_posts = []

    def fitician(request):
        assert request.headers["authorization"] == "Bearer " + "x" * 48
        assert KEY not in request.content.decode()
        submitted.append(json.loads(request.content))
        return httpx.Response(
            200, json={"sequence": submitted[-1].get("sequence", 0), "evidence_id": str(uuid4())}
        )

    def provider(request):
        assert request.headers["authorization"] == "Bearer " + KEY
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 1,
                        "limit_remaining": 1,
                        "limit_reset": "daily",
                        "include_byok_in_limit": True,
                    }
                },
            )
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "chosen/model", "supported_parameters": ["tools", "tool_choice"]}
                    ]
                },
            )
        p = json.loads(request.content)
        model_posts.append(p)
        if len(model_posts) == 1:
            message = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "one",
                        "type": "function",
                        "function": {
                            "name": "fitician_read_file",
                            "arguments": '{"path":"bug.py"}',
                        },
                    }
                ],
            }
        else:
            assert "return a - b" in p["messages"][-1]["content"]
            message = {"role": "assistant", "content": "مدرک بررسی شد."}
        return httpx.Response(
            200, json={"choices": [{"message": message}], "usage": {"completion_tokens": 50}}
        )

    async def run():
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(fitician)) as app_client,
            httpx.AsyncClient(transport=httpx.MockTransport(provider)) as model_client,
        ):
            config = {
                "server": "https://fitician.example",
                "id": str(uuid4()),
                "token": "x" * 48,
                "repository_name": "mohammad4242/fitician",
                "environment": "test",
                "repository": str(source),
                "workspace_root": str(tmp_path / "runtime"),
                "github_enabled": False,
            }
            runtime = GermanyProvider(private, tmp_path / "rate", model_client)
            client = LaptopConnector(config, app_client, model_provider=runtime)
            job = {
                "id": str(uuid4()),
                "run_id": str(uuid4()),
                "thread_id": str(uuid4()),
                "lease_token": str(uuid4()),
                "repository": config["repository_name"],
                "environment": "test",
                "release_commit": release,
                "action": "analyze",
                "tool": "fitician_api_turn",
                "arguments": {"messages": [{"role": "user", "content": "inspect"}]},
                "config": {
                    "execution_backend": "api",
                    "primary_model_id": "chosen/model",
                    "max_output_tokens": 512,
                    "connector_capabilities": {"api_credential_revision": value["revision"]},
                },
            }
            result = await client.execute(job)
            assert result.get("mode") == "api_tools" and result["model"] == "chosen/model"
            assert await client.execute(job) == result

    asyncio.run(run())
    assert len(model_posts) == 2
    assert any(
        e["kind"] == "tool_completed" and "return a - b" in e["payload"].get("output", "")
        for e in submitted
    )
    assert KEY not in "".join(p.read_text() for p in (tmp_path / "runtime").glob("*.json"))


def test_debug_settings_never_use_or_replace_application_credentials(db, test_settings):
    import pytest

    from app.body_analysis.admin_config import service
    from app.body_analysis.admin_config.enums import AIProviderName, AITaskType
    from app.body_analysis.admin_config.models import AIProviderCredential
    from app.body_analysis.admin_config.schemas import AITaskConfigUpdate
    from tests.test_debug_gateway import setup_run

    setup_run(db)
    from sqlalchemy import select

    from app.auth.models import User

    actor = db.scalar(select(User).where(User.is_admin.is_(True)))
    original = AIProviderCredential(
        provider=AIProviderName.OPENROUTER,
        encrypted_api_key="unchanged-production-ciphertext",
        key_last_four="KEEP",
    )
    db.add(original)
    db.flush()
    detail = next(c for c in service.list_task_configs(db) if c.task_type == AITaskType.DEBUG_AGENT)
    assert detail.credential.configured is False
    assert detail.credential.masked is None
    with pytest.raises(service.AIConfigError, match="Germany credential store"):
        service.save_task_config(
            db,
            task_type=AITaskType.DEBUG_AGENT,
            actor=actor,
            settings=test_settings,
            payload=AITaskConfigUpdate(api_key="synthetic-key-never-use", replace_credential=True),
        )
    assert original.encrypted_api_key == "unchanged-production-ciphertext"
    assert original.key_last_four == "KEEP"


def test_api_probe_pins_selected_model_and_credential_without_codex(db):
    from app.debugging.probes import claim_probe, finish_probe, queue_api_probe
    from tests.test_debug_runtime_profiles import target_fixture

    actor, target = target_fixture(db)
    target.last_seen = datetime.now(UTC)
    revision = str(uuid4())
    target.capabilities = {
        "repository_head": "a" * 40,
        "supports_api": True,
        "api_provider": "openrouter",
        "api_credential_revision": revision,
    }
    probe = queue_api_probe(db, target, actor.id, "chosen/model")
    job = claim_probe(db, target)
    assert job["execution_backend"] == "api"
    assert job["config"]["primary_model_id"] == "chosen/model"
    assert job["config"]["connector_capabilities"]["api_credential_revision"] == revision
    finish_probe(
        db,
        target,
        probe.id,
        probe.lease_token,
        {
            "model": "chosen/model",
            "mode": "analysis_only",
            "read_tool_executed": False,
            "output": "observed",
        },
    )
    assert probe.state == "completed"


def test_api_probe_routes_require_admin_origin_and_same_environment(client, db):
    from app.debugging.connectors import enroll_connector
    from tests.admin.test_ai_task_settings_api import ORIGIN, _admin

    base = f"/api/v1/admin/diagnostics/connectors/{uuid4()}/api-probes"
    assert client.post(base, json={"model": "chosen/model"}, headers=ORIGIN).status_code == 401
    actor = _admin(client, db)
    target, _ = enroll_connector(db, actor.id, "Germany API fixture")
    target.last_seen = datetime.now(UTC)
    target.capabilities = {
        "repository_head": "a" * 40,
        "supports_api": True,
        "api_provider": "openrouter",
        "api_credential_revision": str(uuid4()),
    }
    db.commit()
    base = f"/api/v1/admin/diagnostics/connectors/{target.id}/api-probes"
    assert client.post(base, json={"model": "chosen/model"}).status_code == 403
    response = client.post(base, json={"model": "chosen/model"}, headers=ORIGIN)
    assert response.status_code == 200, response.json()
    probe = response.json()
    assert "request_config" not in response.text
    assert client.post(base, json={"model": "chosen/model"}, headers=ORIGIN).status_code == 409
    assert client.get(base + "/" + str(uuid4())).status_code == 404
    target.environment = "unauthorized-other-environment"
    db.commit()
    assert client.get(base + "/" + probe["id"]).status_code == 409
    assert client.post(base, json={"model": "chosen/model"}, headers=ORIGIN).status_code == 409


def test_api_probe_runs_a_real_scoped_read_without_codex_and_replays_no_paid_requests(tmp_path):
    import subprocess

    from app.debugging.connector import LaptopConnector
    from app.debugging.germany_provider import GermanyProvider
    from tests.test_debug_tools import repository

    source = tmp_path / "repo"
    repository(source)
    probe_source = source / "backend/app/observability/synthetic_probe.py"
    probe_source.parent.mkdir(parents=True)
    probe_source.write_text(
        "def synthetic_probe():\n    raise RuntimeError('controlled fixture')\n"
    )
    subprocess.run(["git", "-C", str(source), "add", "backend"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "test: seed probe",
        ],
        check=True,
    )
    release = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    private = tmp_path / "model-api.json"
    value = credential(private)
    posts = []

    def provider(request):
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 1,
                        "limit_remaining": 1,
                        "limit_reset": "daily",
                        "include_byok_in_limit": True,
                    }
                },
            )
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "chosen/model", "supported_parameters": ["tools", "tool_choice"]}
                    ]
                },
            )
        payload = json.loads(request.content)
        posts.append(payload)
        if len(posts) == 1:
            message = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "probe-read",
                        "type": "function",
                        "function": {
                            "name": "fitician_read_file",
                            "arguments": json.dumps(
                                {
                                    "path": "backend/app/observability/synthetic_probe.py",
                                    "count": 12,
                                }
                            ),
                        },
                    }
                ],
            }
        else:
            assert "controlled fixture" in payload["messages"][-1]["content"]
            message = {"role": "assistant", "content": "فایل آزمایش کنترل‌شده خوانده شد."}
        return httpx.Response(
            200, json={"choices": [{"message": message}], "usage": {"completion_tokens": 10}}
        )

    async def run():
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(provider)) as model_http,
            httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
            ) as app_http,
        ):
            client = LaptopConnector(
                {
                    "server": "https://fitician.example",
                    "id": str(uuid4()),
                    "token": "x" * 48,
                    "repository_name": "mohammad4242/fitician",
                    "environment": "test",
                    "repository": str(source),
                    "workspace_root": str(tmp_path / "runtime"),
                },
                app_http,
                model_provider=GermanyProvider(private, tmp_path / "rate", model_http),
            )
            job = {
                "id": str(uuid4()),
                "lease_token": str(uuid4()),
                "model": "chosen/model",
                "release_commit": release,
                "execution_backend": "api",
                "config": {
                    "primary_model_id": "chosen/model",
                    "max_output_tokens": 512,
                    "connector_capabilities": {"api_credential_revision": value["revision"]},
                },
            }
            result = await client.execute_probe(job)
            assert "error_code" not in result, result
            assert result["mode"] == "api_tools" and result["read_tool_executed"]
            assert result["model"] == "chosen/model"
            assert await client.execute_probe(job) == result

    asyncio.run(run())
    assert len(posts) == 2
