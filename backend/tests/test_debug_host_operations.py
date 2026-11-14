from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.debugging.models import DebugOperation
from tests.test_debug_automation import broker_for, setup_case


def test_read_only_server_requests_bind_occurrence_target_and_idempotency(db):
    from app.debugging.host_operations import queue_observation

    _, occurrence, run, _ = setup_case(db)
    first = queue_observation(db, run.id, "server-1", "production-iran")
    assert first.kind == "observe" and first.occurrence_id == occurrence.id
    assert first.request["trace_id"] == occurrence.trace_id
    assert queue_observation(db, run.id, "server-1", "production-iran").id == first.id
    with pytest.raises(ValueError, match="automation_idempotency_conflict"):
        queue_observation(db, run.id, "server-1", "production-germany")
    assert db.scalar(select(func.count()).select_from(DebugOperation)) == 1
    with pytest.raises(ValueError, match="observation_target_not_authorized"):
        queue_observation(db, run.id, "server-2", "ssh production")


def test_observation_does_not_grant_deployment_or_redispatch_on_repeated_intent(db):
    from app.debugging.automation import claim_operation
    from app.debugging.host_operations import queue_observation, record_observation

    _, _, run, _ = setup_case(db)
    row = queue_observation(db, run.id, "server-1", "production-germany")
    worker = broker_for(db, run)
    claimed = claim_operation(db, worker)
    record_observation(
        db, worker, row.id, claimed.lease_token, "observation_prepared", {"policy_commit": "a" * 40}
    )
    first = record_observation(db, worker, row.id, claimed.lease_token, "dispatch_intent", {})
    repeat = record_observation(db, worker, row.id, claimed.lease_token, "dispatch_intent", {})
    assert first["disposition"] == "dispatch_once"
    assert repeat["disposition"] == "reconcile_only"
    assert row.state == "dispatching" and not row.result.get("deployment_authorization")


def packet():
    import hashlib
    import json
    from datetime import UTC, datetime

    rows = [
        {
            "service": "agent-service",
            "container_id": "a" * 64,
            "image_id": "sha256:" + "b" * 64,
            "status": "running",
            "health": "healthy",
            "restart_count": 0,
            "commit": "c" * 40,
            "release_provenance": "image_label",
            "logs": [],
            "logs_state": "correlation_required",
        }
    ]
    identity = [{k: rows[0].get(k) for k in ("service", "container_id", "image_id")}]
    return {
        "schema_version": 1,
        "target_environment": "production-germany",
        "captured_at": datetime.now(UTC).isoformat(),
        "services": rows,
        "database_revision": [],
        "baseline_sha256": hashlib.sha256(
            json.dumps([identity, []], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "complete": True,
        "missing_services": [],
        "capacity": {},
        "provenance": "fixed_read_only_host_collector",
        "business_outcome_verified": False,
        "medical_form": "private-fixture-not-for-persistence",
    }


def test_host_receipts_are_sanitized_target_bound_and_do_not_confirm_resolution(db):
    from app.debugging.automation import claim_operation
    from app.debugging.host_operations import queue_observation, record_observation

    _, _, run, _ = setup_case(db)
    worker = broker_for(db, run)
    row = queue_observation(db, run.id, "host-read", "production-germany")
    claimed = claim_operation(db, worker)
    lease = claimed.lease_token
    record_observation(
        db, worker, row.id, lease, "observation_prepared", {"policy_commit": "a" * 40}
    )
    record_observation(db, worker, row.id, lease, "dispatch_intent", {})
    record_observation(db, worker, row.id, lease, "dispatched", {"workflow_run_id": 123})
    value = {
        "workflow_run_id": 123,
        "workflow_conclusion": "success",
        "artifact_id": 10,
        "artifact_digest": "sha256:" + "d" * 64,
        "observation": packet(),
    }
    wrong = {**value, "observation": {**packet(), "target_environment": "production-iran"}}
    with pytest.raises(ValueError, match="invalid_host_observation"):
        record_observation(db, worker, row.id, lease, "observation_completed", wrong)
    result = record_observation(db, worker, row.id, lease, "observation_completed", value)
    assert result["operation"]["state"] == "succeeded"
    import json

    assert "private-fixture" not in json.dumps(result)
    assert result["operation"]["result"]["observation"]["business_outcome_verified"] is False
    from app.debugging.findings import proposal_payload

    evidence_id = result["operation"]["result"]["evidence_id"]
    proposal = {
        "classification": "observed_fact",
        "text": "Agent service was healthy at collection.",
        "evidence_ids": [evidence_id],
    }
    assert proposal_payload(db, run, proposal)["evidence_ids"] == [evidence_id]
    from app.debugging.models import DebugMessage, DebugThread
    from app.debugging.service import submit_message

    run.state = "completed"
    thread = db.get(DebugThread, run.thread_id)
    actor_id = db.get(DebugMessage, run.message_id).actor_id
    foreign_run = submit_message(
        db, thread.issue_id, actor_id, "inspect", str(uuid4()), row.occurrence_id
    )
    with pytest.raises(ValueError, match="finding_evidence_not_found"):
        proposal_payload(db, foreign_run, proposal)


def test_host_broker_persists_intent_before_dispatch_and_cancels_only_recorded_workflow():
    import asyncio

    from app.debugging.github_automation import REPOSITORY
    from app.debugging.host_broker import advance_observation

    job = {
        "id": str(uuid4()),
        "kind": "observe",
        "state": "preparing",
        "lease_token": str(uuid4()),
        "request": {"target_environment": "production-germany", "trace_id": None},
        "result": {"policy_commit": "a" * 40},
    }
    actions = []

    class Github:
        async def dispatch_observation(self, identifier, policy, target, trace):
            actions.append("dispatch")
            assert actions == ["dispatch_intent", "dispatch"]
            return 123

        async def validation_run(self, identifier):
            return {
                "id": identifier,
                "head_sha": "a" * 40,
                "path": ".github/workflows/debug-server-observation.yml",
                "head_repository": {"full_name": REPOSITORY},
                "event": "workflow_dispatch",
                "display_title": "Debug observation " + job["id"],
                "status": "in_progress",
            }

        async def cancel_validation(self, identifier):
            assert actions[-1] == "cancel_intent" and identifier == 123
            actions.append("cancel")

    async def rpc(path, value):
        if path.endswith("/authorize"):
            return {"authorized": True, "cancel_requested": True}
        stage = value["stage"]
        actions.append(stage)
        if stage == "dispatched":
            job.update(state="running", result={**job["result"], "workflow_run_id": 123})
        return {
            "operation": job,
            "disposition": {"dispatch_intent": "dispatch_once", "cancel_intent": "cancel_once"}.get(
                stage, "recorded"
            ),
        }

    async def run():
        await advance_observation(job, Github(), rpc)
        await advance_observation(job, Github(), rpc)

    asyncio.run(run())
    assert actions == ["dispatch_intent", "dispatch", "dispatched", "cancel_intent", "cancel"]


def test_restart_reconciles_observation_instead_of_redispatching():
    import asyncio

    from app.debugging.host_broker import advance_observation

    job = {
        "id": str(uuid4()),
        "kind": "observe",
        "state": "uncertain",
        "lease_token": str(uuid4()),
        "request": {"target_environment": "production-germany", "trace_id": None},
        "result": {"policy_commit": "a" * 40},
    }
    calls = []

    class Github:
        async def find_observation(self, *args):
            return {"id": 123}

        async def dispatch_observation(self, *args):
            raise AssertionError("Duplicate dispatch")

    async def rpc(path, value):
        calls.append(value["stage"])
        return {
            "operation": {
                **job,
                "state": "running",
                "result": {**job["result"], "workflow_run_id": 123},
            },
            "disposition": "recorded",
        }

    result = asyncio.run(advance_observation(job, Github(), rpc))
    assert result["state"] == "running" and calls == ["dispatched"]


def test_observation_migration_refuses_to_delete_existing_audit_on_downgrade(db):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy.exc import DBAPIError

    from app.debugging.host_operations import queue_observation

    _, _, run, _ = setup_case(db)
    queue_observation(db, run.id, "retain-audit", "production-germany")
    path = Path(__file__).parents[1] / "alembic/versions/20261114_185_debug_host_observations.py"
    spec = importlib.util.spec_from_file_location("host_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with pytest.raises(DBAPIError, match="Retain host observation audit"):
        with db.begin_nested(), Operations.context(MigrationContext.configure(db.connection())):
            migration.downgrade()
    assert db.scalar(select(func.count()).select_from(DebugOperation)) == 1


def test_complete_host_evidence_requires_container_identity_and_retains_only_numeric_capacity():
    from app.debugging.host_operations import validate_observation

    request = {"target_environment": "production-germany", "trace_id": None}
    value = packet()
    value["capacity"] = {
        "cpu_count": 1,
        "memory": {"MemAvailable": 512 * 1024**2},
        "root_disk_free_bytes": 2000 * 1024**2,
        "credential": "private-capacity-fixture",
    }
    safe = validate_observation(value, request)
    assert safe["capacity"] == {
        "cpu_count": 1,
        "memory": {"MemAvailable": 512 * 1024**2},
        "root_disk_free_bytes": 2000 * 1024**2,
    }
    # Even a correctly hashed packet cannot claim completeness without actual identities.
    value = packet()
    value["services"][0]["container_id"] = None
    import hashlib
    import json

    identity = [{k: value["services"][0][k] for k in ("service", "container_id", "image_id")}]
    value["baseline_sha256"] = hashlib.sha256(
        json.dumps([identity, []], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="invalid_host_observation"):
        validate_observation(value, request)


def test_optional_iran_workers_are_sanitized_and_bound_to_the_same_host_baseline():
    import hashlib
    import json

    from app.debugging.host_operations import validate_observation

    value = packet()
    value["target_environment"] = "production-iran"
    value["database_revision"] = ["20261114_185"]
    template = value["services"][0]
    names = [
        "backend",
        "backend-2",
        "frontend",
        "db",
        "redis",
        "body-analysis-worker",
        "food-photo-worker",
        "notification-worker",
        "scheduler",
        "caddy",
        "debug-worker",
    ]
    value["services"] = [{**template, "service": name, "private": "discard"} for name in names]
    identities = sorted(
        [
            {key: row[key] for key in ("service", "container_id", "image_id")}
            for row in value["services"]
        ],
        key=lambda row: row["service"],
    )
    value["baseline_sha256"] = hashlib.sha256(
        json.dumps(
            [identities, value["database_revision"]], sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    request = {"target_environment": "production-iran", "trace_id": None}
    safe = validate_observation(value, request)
    assert "debug-worker" in {row["service"] for row in safe["services"]}
    assert "private" not in json.dumps(safe)
    value["services"].append({**template, "service": "unrelated-container"})
    with pytest.raises(ValueError, match="invalid_host_observation"):
        validate_observation(value, request)


def test_observation_submission_rejects_other_connectors_expired_leases_and_lost_admin(client, db):
    from datetime import UTC, datetime, timedelta

    from app.debugging.connectors import claim_call, enqueue_call, enroll_connector
    from tests.admin.test_ai_task_settings_api import _admin

    actor = _admin(client, db)
    _, occurrence, run, _ = setup_case(db, actor)
    runtime, token = enroll_connector(db, actor.id, "Runtime")
    foreign, foreign_token = enroll_connector(db, actor.id, "Other runtime")
    call = enqueue_call(db, run, runtime, "turn", "fitician_codex_turn", {"messages": []})
    claim_call(db, runtime)
    payload = {
        "lease_token": str(call.lease_token),
        "key": "observe-1",
        "target_environment": "production-germany",
    }
    path = f"/api/v1/debug-connectors/{runtime.id}/calls/{call.id}/host-observations"
    assert client.post(path, json=payload).status_code == 401
    other = f"/api/v1/debug-connectors/{foreign.id}/calls/{call.id}/host-observations"
    assert (
        client.post(
            other, json=payload, headers={"Authorization": "Bearer " + foreign_token}
        ).status_code
        == 409
    )
    headers = {"Authorization": "Bearer " + token}
    call.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    assert client.post(path, json=payload, headers=headers).status_code == 409
    call.lease_until = datetime.now(UTC) + timedelta(minutes=1)
    db.flush()
    reply = client.post(path, json=payload, headers=headers)
    assert reply.status_code == 200
    assert reply.json()["occurrence_id"] == str(occurrence.id)
    assert client.post(path, json=payload, headers=headers).json() == reply.json()
    actor.is_admin = False
    db.flush()
    assert client.post(path, json=payload, headers=headers).status_code == 401
