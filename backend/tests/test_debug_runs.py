from uuid import uuid4

import pytest

from app.debugging.service import cancel_run, claim_run, submit_message
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def test_submissions_are_idempotent_and_issue_scoped(db):
    from app.auth.models import User

    actor = User(
        id=uuid4(), email="debug-admin@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    issue = record_event(
        db,
        EventInput(
            component="api",
            operation="test",
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    first = submit_message(db, issue.issue_id, actor.id, "inspect the failure", "request-1")
    repeat = submit_message(db, issue.issue_id, actor.id, "inspect the failure", "request-1")
    assert first.id == repeat.id
    with pytest.raises(ValueError, match="idempotency_conflict"):
        submit_message(db, issue.issue_id, actor.id, "different request", "request-1")
    run = claim_run(db)
    assert run.id == first.id
    assert claim_run(db) is None
    cancel_run(db, issue.issue_id, run.id)
    assert run.cancel_requested


def test_conversation_requires_admin_and_mutations_require_origin(client, db):
    from tests.admin.test_ai_task_settings_api import _admin

    issue = record_event(
        db,
        EventInput(
            component="api",
            operation="test",
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    issue_id = issue.issue_id
    assert (
        client.get(f"/api/v1/admin/diagnostics/issues/{issue_id}/conversation").status_code == 401
    )
    _admin(client, db)
    base = f"/api/v1/admin/diagnostics/issues/{issue_id}"
    assert (
        client.post(
            base + "/messages",
            json={"content": "inspect"},
            headers={"Idempotency-Key": "request-123"},
        ).status_code
        == 403
    )
    first = client.post(
        base + "/messages",
        json={"content": "inspect"},
        headers={"Origin": "http://localhost:5173", "Idempotency-Key": "request-123"},
    )
    assert first.status_code == 200
    repeat = client.post(
        base + "/messages",
        json={"content": "inspect"},
        headers={"Origin": "http://localhost:5173", "Idempotency-Key": "request-123"},
    )
    assert repeat.json()["id"] == first.json()["id"]
    history = client.get(base + "/conversation").json()
    assert len(history["messages"]) == 1
    assert history["messages"][0]["content"] == "inspect"
    assert (
        client.get(
            f"/api/v1/admin/diagnostics/issues/{uuid4()}/runs/{first.json()['id']}/events"
        ).status_code
        == 404
    )


def test_disabled_agent_finishes_as_blocked_without_fabricating_a_reply(
    db, test_settings, monkeypatch
):
    import asyncio

    from sqlalchemy import select

    from app.auth.models import User
    from app.debugging import worker
    from app.debugging.models import DebugMessage

    actor = User(
        id=uuid4(), email="disabled-debug@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    issue = record_event(
        db,
        EventInput(
            component="api",
            operation="test",
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    queued = submit_message(db, issue.issue_id, actor.id, "inspect", "disabled-request-1")
    run = claim_run(db)
    db.flush()
    monkeypatch.setattr(worker, "get_engine", lambda settings: db.connection())
    asyncio.run(worker.execute_run(test_settings, run.id, run.lease_token))
    db.expire_all()
    assert queued.state == "blocked"
    assert queued.error_code == "debug_agent_disabled"
    assert len(list(db.scalars(select(DebugMessage)))) == 1


def test_run_pins_selected_occurrence_even_without_stack(db):
    from app.auth.models import User

    actor = User(
        id=uuid4(), email="occurrence-admin@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    event = record_event(
        db,
        EventInput(
            component="api",
            operation="test",
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    run = submit_message(
        db, event.issue_id, actor.id, "inspect this occurrence", "occurrence-request", event.id
    )
    assert run.evidence["occurrence_id"] == str(event.id)
    with pytest.raises(ValueError, match="idempotency_conflict"):
        submit_message(
            db, event.issue_id, actor.id, "inspect this occurrence", "occurrence-request", None
        )


def test_default_occurrence_is_latest_and_retry_does_not_rebind(db):
    from app.auth.models import User

    actor = User(email="latest-admin@example.invalid", password_hash="unused", is_admin=True)
    db.add(actor)
    db.flush()
    payload = EventInput(
        component="api",
        operation="latest",
        stage="test",
        platform="backend",
        category="application_bug",
        severity="error",
        error_code="UNHANDLED_EXCEPTION",
        outcome="failure",
    )
    old = record_event(
        db,
        EventInput.model_validate(
            {
                **payload.model_dump(),
                "exception_evidence": {"values": [{"type": "ValueError", "frames": []}]},
            }
        ),
    )
    latest = record_event(db, payload)
    assert old.issue_id == latest.issue_id
    run = submit_message(db, latest.issue_id, actor.id, "inspect", "latest-request")
    assert run.evidence["occurrence_id"] == str(latest.id)
    assert run.evidence["snapshot"] is None
    record_event(db, payload)
    assert submit_message(db, latest.issue_id, actor.id, "inspect", "latest-request").id == run.id
    assert run.evidence["occurrence_id"] == str(latest.id)


def test_standalone_debug_worker_registers_its_orm_relationships():
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import app.debugging.worker; from sqlalchemy.orm import configure_mappers; "
            "configure_mappers()",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=__import__("pathlib").Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stderr


def test_offline_execution_target_blocks_before_any_provider_or_tool_action(
    db, test_settings, monkeypatch
):
    import asyncio

    from app.debugging import worker
    from tests.test_debug_gateway import setup_run

    _, run, connector, _ = setup_run(db)
    run.config_snapshot = {
        "enabled": True,
        "execution_backend": "agent_service",
        "agent_name": "codex",
        "agent_model_id": "selected-model",
        "connector_id": str(connector.id),
    }
    connector.last_seen = None
    db.flush()
    calls = []

    async def forbidden(*args, **kwargs):
        calls.append(args)
        raise ValueError("unexpected_runtime_call")

    monkeypatch.setattr(worker, "get_engine", lambda _: db.connection())
    monkeypatch.setattr(worker, "call_connector", forbidden)
    import uuid

    asyncio.run(worker.execute_run(test_settings, run.id, uuid.UUID(str(run.lease_token))))
    db.expire_all()
    assert run.state == "blocked"
    assert run.error_code == "execution_target_offline"
    assert not calls


@pytest.mark.parametrize(
    "content",
    [
        '{"medical_form": "sensitive-fixture-never-persist"}',
        '{"nested": {"request_body": {"photo": "sensitive-fixture-never-persist"}}}',
        "medical_form: sensitive-fixture-never-persist",
        "data:image/jpeg;base64,c2Vuc2l0aXZlLWZpeHR1cmU=",
    ],
)
def test_sensitive_operator_pastes_are_rejected_before_conversation_persistence(db, content):
    from sqlalchemy import func, select

    from app.debugging.models import DebugMessage, DebugRun, DebugThread

    before = [
        db.scalar(select(func.count()).select_from(model))
        for model in (DebugMessage, DebugRun, DebugThread)
    ]
    with pytest.raises(ValueError, match="sensitive_message_rejected"):
        # Rejection happens before issue lookup or creation, never retaining the raw input.
        submit_message(db, uuid4(), uuid4(), content, "private-paste-test")
    assert before == [
        db.scalar(select(func.count()).select_from(model))
        for model in (DebugMessage, DebugRun, DebugThread)
    ]


def test_operator_text_preserves_source_references_and_scrubs_contact_values():
    from app.debugging.privacy import validate_operator_message

    safe = validate_operator_message(
        "Inspect backend/app/main.py:42; contact debug@example.invalid"
    )
    assert "backend/app/main.py:42" in safe and "debug@example.invalid" not in safe
    # Discussing the code identifier is permitted; pasting its payload is not.
    assert validate_operator_message("Check why medical_form validation failed")
    with pytest.raises(ValueError, match="sensitive_message_rejected"):
        validate_operator_message(r'{"\u0074oken": "private-fixture"}')


def test_quoted_credentials_in_model_and_tool_text_are_removed():
    from app.debugging.privacy import sanitize_text

    safe = sanitize_text(
        'Evidence: {"api_key": "private credential fixture", "file": "backend/app/main.py"}'
    )
    assert "private credential fixture" not in safe
    assert "backend/app/main.py" in safe


def test_history_pages_retain_the_runs_for_their_messages_and_current_active_run(client, db):
    from datetime import UTC, datetime, timedelta

    from app.debugging.models import DebugMessage, DebugRun, DebugThread
    from tests.admin.test_ai_task_settings_api import _admin

    _admin(client, db)
    issue = record_event(
        db,
        EventInput(
            component="api",
            operation="history-proof",
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    thread = DebugThread(issue_id=issue.issue_id, environment="test")
    # Use the configured diagnostics environment rather than inventing a cross-environment thread.
    from app.observability.environment import diagnostics_environment

    thread.environment = diagnostics_environment()
    db.add(thread)
    db.flush()
    runs = []
    for index in range(25):
        message = DebugMessage(
            thread_id=thread.id,
            role="user",
            content="Synthetic history " + str(index),
            created_at=datetime(2026, 11, 1, tzinfo=UTC) + timedelta(minutes=index),
        )
        db.add(message)
        db.flush()
        run = DebugRun(
            thread_id=thread.id,
            message_id=message.id,
            state="completed",
            action="analyze",
            config_snapshot={},
            evidence={"occurrence_id": str(issue.id)},
        )
        db.add(run)
        db.flush()
        runs.append(run)
    runs[-1].state = "queued"
    db.flush()
    base = f"/api/v1/admin/diagnostics/issues/{issue.issue_id}/conversation"
    first = client.get(base + "?limit=5").json()
    second = client.get(base + "?limit=5&before=" + first["next_cursor"]).json()
    assert {item["id"] for item in second["runs"]} == {str(run.id) for run in runs[15:20]} | {
        str(runs[-1].id)
    }
    assert all(item["message_id"] for item in second["runs"])
