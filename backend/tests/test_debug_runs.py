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
