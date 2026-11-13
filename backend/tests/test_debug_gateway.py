from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.auth.models import User
from app.debugging.connectors import claim_call, enqueue_call, enroll_connector, finish_call
from app.debugging.service import claim_run, submit_message
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def setup_run(db, action="analyze"):
    user = User(id=uuid4(), email=f"{uuid4()}@example.com", password_hash="unused", is_admin=True)
    db.add(user)
    db.flush()
    event = record_event(
        db,
        EventInput(
            component="api",
            operation="debug_test",
            stage="failed",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    run = submit_message(db, event.issue_id, user.id, "inspect", str(uuid4()), event.id, action)
    run = claim_run(db)
    connector, token = enroll_connector(db, user.id, "Laptop")
    return user, run, connector, token


def test_durable_tool_delivery_rejects_mutations_and_payload_reuse(db):
    user, run, connector, _ = setup_run(db)
    with pytest.raises(ValueError, match="mutation_not_authorized"):
        enqueue_call(
            db, run, connector, "write", "fitician_write_file", {"path": "bug.py", "content": "x"}
        )
    first = enqueue_call(db, run, connector, "read-1", "fitician_read_file", {"path": "bug.py"})
    assert (
        enqueue_call(db, run, connector, "read-1", "fitician_read_file", {"path": "bug.py"}).id
        == first.id
    )
    with pytest.raises(ValueError, match="tool_idempotency_conflict"):
        enqueue_call(db, run, connector, "read-1", "fitician_read_file", {"path": "other.py"})
    db.flush()
    job = claim_call(db, connector)
    assert job["run_id"] == str(run.id)
    assert claim_call(db, connector) is None
    first.lease_until = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    replacement = claim_call(db, connector)
    assert replacement["id"] == job["id"]
    assert replacement["lease_token"] != job["lease_token"]
    with pytest.raises(ValueError, match="connector_lease_lost"):
        finish_call(
            db,
            connector,
            first.id,
            __import__("uuid").UUID(job["lease_token"]),
            {"output": "stale"},
        )
    finish_call(
        db,
        connector,
        first.id,
        first.lease_token,
        {"output": "email=user@example.com", "token": "private-fixture"},
    )
    assert first.result["token"] == "[redacted]"
    assert "user@example.com" not in str(first.result)
    finish_call(db, connector, first.id, first.lease_token, {"output": "duplicate"})
    assert first.result["output"] != "duplicate"


def test_authority_is_rechecked_after_enqueue_and_cancel(db):
    user, run, connector, _ = setup_run(db)
    enqueue_call(db, run, connector, "read", "fitician_read_file", {"path": "bug.py"})
    db.flush()
    user.is_admin = False
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        claim_call(db, connector)
    user.is_admin = True
    run.cancel_requested = True
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        enqueue_call(db, run, connector, "read-next", "fitician_read_file", {"path": "bug.py"})


def test_tool_output_is_durable_sanitized_citable_and_retry_safe(db):
    from uuid import UUID

    from sqlalchemy import select

    from app.debugging.connectors import update_call
    from app.debugging.models import DebugRunEvent

    _, run, connector, _ = setup_run(db)
    call = enqueue_call(db, run, connector, "read", "fitician_read_file", {"path": "bug.py"})
    claim_call(db, connector)
    payload = {
        "tool": "fitician_read_file",
        "output": "bug.py:2 user@example.com token=private-fixture",
    }
    result = update_call(db, connector, call.id, call.lease_token, 1, "tool_completed", payload)
    evidence_id = UUID(result["evidence_id"])
    evidence = db.get(DebugRunEvent, evidence_id)
    assert evidence.run_id == run.id
    assert evidence.payload["output"] == "bug.py:2 [email redacted] token=[redacted]"
    assert evidence.payload["provenance"] == "connector_tool"
    assert (
        update_call(db, connector, call.id, call.lease_token, 1, "tool_completed", payload)
        == result
    )
    assert len(list(db.scalars(select(DebugRunEvent).where(DebugRunEvent.id == evidence_id)))) == 1
    with pytest.raises(ValueError, match="tool_progress_conflict"):
        update_call(
            db,
            connector,
            call.id,
            call.lease_token,
            1,
            "tool_completed",
            {"tool": "fitician_read_file", "output": "different"},
        )
    run.cancel_requested = True
    with pytest.raises(ValueError, match="run_no_longer_authorized"):
        update_call(db, connector, call.id, call.lease_token, 2, "tool_completed", payload)


def test_finding_proposal_progress_is_durable_scoped_and_retry_safe(db):
    from app.debugging.connectors import update_call
    from app.debugging.models import DebugRunEvent

    _, run, connector, _ = setup_run(db)
    call = enqueue_call(db, run, connector, "finding", "fitician_record_finding", {})
    claim_call(db, connector)
    payload = {
        "classification": "hypothesis",
        "text": "Check the selected failure",
        "evidence_ids": [run.evidence["occurrence_id"]],
    }
    first = update_call(db, connector, call.id, call.lease_token, 1, "finding_proposed", payload)
    assert first["evidence_id"]
    assert (
        update_call(db, connector, call.id, call.lease_token, 1, "finding_proposed", payload)
        == first
    )
    event = db.get(DebugRunEvent, __import__("uuid").UUID(first["evidence_id"]))
    assert event.payload["classification"] == "hypothesis"
    with pytest.raises(ValueError, match="finding_not_supported"):
        update_call(
            db,
            connector,
            call.id,
            call.lease_token,
            2,
            "finding_proposed",
            {**payload, "classification": "confirmed"},
        )
