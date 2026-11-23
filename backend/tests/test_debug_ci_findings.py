from uuid import UUID

import pytest

from app.debugging import automation
from app.debugging.ci_contract import _digest
from app.debugging.connectors import enroll_connector
from app.debugging.findings import FindingReview, list_findings, proposal_payload, verify_finding
from tests.test_debug_automation import request
from tests.test_debug_findings import seed_finding, setup_case


def ci_evidence(db, run, worker, passed, marker):
    payload = request()
    snapshot = {**payload["snapshot"], "tree_digest": marker * 64}
    snapshot.pop("snapshot_digest")
    payload["snapshot"] = {**snapshot, "snapshot_digest": _digest(snapshot)}
    row = automation.queue_validation(db, run.id, "ci-" + marker, payload)
    automation.claim_operation(db, worker)
    prepare = {
        "base_commit": snapshot["base_commit"],
        "candidate_commit": marker * 40,
        "policy_commit": "d" * 40,
        "branch": "debug/ci-" + str(row.id),
        "policy_ref": "debug-policy/" + "d" * 40,
        "snapshot_digest": payload["snapshot"]["snapshot_digest"],
        "tree_digest": snapshot["tree_digest"],
    }
    automation.record_progress(db, worker, row.id, row.lease_token, "prepared", prepare)
    automation.record_progress(db, worker, row.id, row.lease_token, "dispatch_intent", {})
    workflow_id = int(marker, 16) + 100
    automation.record_progress(
        db, worker, row.id, row.lease_token, "dispatched", {"workflow_run_id": workflow_id}
    )
    validation = {
        "candidate_commit": marker * 40,
        "policy_commit": "d" * 40,
        "profile": payload["profile"],
        "tests": payload["tests"],
        "image": "sha256:" + "e" * 64,
        "passed": passed,
        "exit_code": 0 if passed else 1,
        "exercised": 1,
        "skipped": 0,
        "failures": 0 if passed else 1,
        "failed_tests": []
        if passed
        else [{"class_name": "TestRegression", "name": "test_boundary", "type": "failure"}],
        "failed_stage": None if passed else 0,
        "diagnostics": [],
    }
    receipt = {
        "workflow_run_id": workflow_id,
        "workflow_conclusion": "success" if passed else "failure",
        "artifact_id": workflow_id + 1,
        "artifact_digest": "sha256:" + "f" * 64,
        "validation": validation,
    }
    response = automation.record_progress(db, worker, row.id, row.lease_token, "completed", receipt)
    assert (
        automation.record_progress(db, worker, row.id, row.lease_token, "completed", receipt)
        == response
    )
    return row


def case(client, db):
    actor, occurrence, run = setup_case(client, db)
    worker, _ = enroll_connector(db, actor.id, "CI broker", kind="automation")
    run.config_snapshot = {**run.config_snapshot, "automation_worker_id": str(worker.id)}
    return actor, occurrence, run, worker


def test_artifact_verified_ci_comparison_can_be_explicitly_reviewed_and_cited(client, db):
    actor, occurrence, run, worker = case(client, db)
    finding = seed_finding(db, run)
    before = ci_evidence(db, run, worker, False, "b")
    after = ci_evidence(db, run, worker, True, "c")
    assert before.result.get("evidence_id"), "Validated CI receipts need an immutable citation ID"
    assert after.result.get("evidence_id")
    run.state = "completed"
    db.flush()
    proposal = proposal_payload(
        db,
        run,
        {
            "classification": "observed_fact",
            "text": "Focused regression passed",
            "evidence_ids": [after.result["evidence_id"]],
        },
    )
    assert proposal["evidence_ids"] == [after.result["evidence_id"]]
    review = FindingReview(
        before_test_id=UUID(before.result["evidence_id"]),
        after_test_id=UUID(after.result["evidence_id"]),
        evidence_version=run.evidence["evidence_version"],
        note="Reviewed the same isolated CI regression and exact patch.",
    )
    recorded = verify_finding(db, occurrence.issue_id, finding.id, actor.id, "ci-review-1", review)
    assert (
        verify_finding(db, occurrence.issue_id, finding.id, actor.id, "ci-review-1", review).id
        == recorded.id
    )
    assert recorded.payload["method"] == "reviewed_regression_comparison"
    assert recorded.payload["test_provenance"] == "github_actions"
    page = list_findings(db, occurrence.issue_id, occurrence.id, 20, 0)
    assert len(page["findings"][0]["test_evidence"]) == 2


@pytest.mark.parametrize(
    "tamper",
    [
        "artifact",
        "candidate",
        "policy",
        "tests",
        "no_test_failure",
        "occurrence",
        "image",
        "cancelled",
    ],
)
def test_ci_reviews_reject_unverified_or_incomparable_receipts(client, db, tamper):
    actor, occurrence, run, worker = case(client, db)
    finding = seed_finding(db, run)
    before = ci_evidence(db, run, worker, False, "b")
    after = ci_evidence(db, run, worker, True, "c")
    assert before.result.get("evidence_id"), "Validated CI receipts need immutable evidence"
    run.state = "completed"
    if tamper == "artifact":
        after.result = {**after.result, "artifact_verified": False}
    elif tamper == "candidate":
        after.result = {**after.result, "candidate_commit": "a" * 40}
    elif tamper == "policy":
        after.result = {
            **after.result,
            "policy_commit": "a" * 40,
            "validation": {**after.result["validation"], "policy_commit": "a" * 40},
        }
    elif tamper == "tests":
        after.request = {**after.request, "tests": ["backend/tests/test_diagnostics.py"]}
    elif tamper == "occurrence":
        from uuid import uuid4

        after.occurrence_id = uuid4()
    elif tamper == "image":
        after.result = {
            **after.result,
            "validation": {**after.result["validation"], "image": "sha256:" + "a" * 64},
        }
    elif tamper == "cancelled":
        after.state = "cancelled"
    else:
        before.result = {
            **before.result,
            "validation": {**before.result["validation"], "failed_tests": []},
        }
    db.flush()
    with pytest.raises(
        ValueError, match="regression_evidence_required|matching_regression_comparison_required"
    ):
        verify_finding(
            db,
            occurrence.issue_id,
            finding.id,
            actor.id,
            "ci-review-denied",
            FindingReview(
                before_test_id=UUID(before.result["evidence_id"]),
                after_test_id=UUID(after.result["evidence_id"]),
                evidence_version=run.evidence["evidence_version"],
                note="Synthetic review must reject mismatched provenance.",
            ),
        )
