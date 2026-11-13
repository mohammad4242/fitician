from uuid import uuid4

import pytest

from app.debugging import automation
from app.debugging.publication import queue_publication
from tests.test_debug_automation import broker_for, request, setup_case


def successful_validation(db, run):
    row = automation.queue_validation(db, run.id, "validation", request())
    row.state = "succeeded"
    row.result = {
        "candidate_commit": "c" * 40,
        "base_commit": "a" * 40,
        "branch": "debug/ci-" + str(row.id),
        "policy_commit": "d" * 40,
        "snapshot_digest": request()["snapshot"]["snapshot_digest"],
        "artifact_verified": True,
        "artifact_id": 123,
        "artifact_digest": "sha256:" + "e" * 64,
        "workflow_run_id": 456,
        "workflow_conclusion": "success",
        "validation": {
            "passed": True,
            "exercised": 2,
            "failures": 0,
            "profile": "backend",
            "tests": request()["tests"],
            "image": "sha256:" + "f" * 64,
        },
    }
    db.flush()
    return row


def test_publication_requires_matching_successful_occurrence_scoped_ci_evidence(db):
    _, occurrence, run, _ = setup_case(db)
    run.action = "prepare_fix"
    validation = successful_validation(db, run)
    first = queue_publication(
        db,
        run.id,
        "pr-1",
        validation.id,
        "fix(debug-agent): repair seeded behavior",
        request()["snapshot"]["snapshot_digest"],
    )
    assert first.kind == "publish_pr" and first.state == "queued"
    assert first.occurrence_id == occurrence.id
    assert first.worker_id == broker_for(db, run).id
    assert (
        queue_publication(
            db,
            run.id,
            "pr-1",
            validation.id,
            "fix(debug-agent): repair seeded behavior",
            request()["snapshot"]["snapshot_digest"],
        ).id
        == first.id
    )
    with pytest.raises(ValueError, match="automation_snapshot_mismatch"):
        queue_publication(
            db,
            run.id,
            "pr-wrong",
            validation.id,
            "fix(debug-agent): repair seeded behavior",
            "0" * 64,
        )
    validation.occurrence_id = uuid4()
    with pytest.raises(ValueError, match="matching_successful_ci_required"):
        queue_publication(
            db,
            run.id,
            "pr-other",
            validation.id,
            "fix(debug-agent): repair seeded behavior",
            request()["snapshot"]["snapshot_digest"],
        )


def test_connection_probe_and_failed_tests_cannot_authorize_publication(db):
    _, _, run, _ = setup_case(db)
    run.action = "prepare_fix"
    validation = successful_validation(db, run)
    for state, purpose in [("failed", "repair_validation"), ("succeeded", "connection_check")]:
        validation.state = state
        validation.request = {**validation.request, "purpose": purpose}
        with pytest.raises(ValueError, match="matching_successful_ci_required"):
            queue_publication(
                db,
                run.id,
                "denied",
                validation.id,
                "fix(debug-agent): repair seeded behavior",
                request()["snapshot"]["snapshot_digest"],
            )


def test_publication_ack_replay_never_authorizes_a_second_post_or_marks_issue_resolved(db):
    from app.debugging.publication import record_publication
    from app.observability.diagnostics_models import DiagnosticIssue

    _, occurrence, run, _ = setup_case(db)
    run.action = "prepare_fix"
    validation = successful_validation(db, run)
    row = queue_publication(
        db,
        run.id,
        "pr-once",
        validation.id,
        "fix(debug-agent): repair seeded behavior",
        request()["snapshot"]["snapshot_digest"],
    )
    broker = broker_for(db, run)
    leased = automation.claim_operation(db, broker)
    assert leased.id == row.id
    first = record_publication(db, broker, row.id, row.lease_token, "publication_intent", {})
    assert first["disposition"] == "publish_once"
    assert (
        record_publication(db, broker, row.id, row.lease_token, "publication_intent", {})[
            "disposition"
        ]
        == "reconcile_only"
    )
    record_publication(db, broker, row.id, row.lease_token, "uncertain", {})
    receipt = {
        "pr_number": 43,
        "pr_url": "https://github.com/mohammad4242/fitician/pull/43",
        "candidate_commit": "c" * 40,
        "branch": validation.result["branch"],
        "base": "main",
    }
    run.state = "completed"
    completed = record_publication(
        db, broker, row.id, row.lease_token, "publication_completed", receipt
    )
    assert completed["operation"]["state"] == "succeeded"
    assert (
        record_publication(db, broker, row.id, row.lease_token, "publication_completed", receipt)
        == completed
    )
    assert db.get(DiagnosticIssue, occurrence.issue_id).status == "new"
