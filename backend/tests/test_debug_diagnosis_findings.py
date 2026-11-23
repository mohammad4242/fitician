import asyncio

from sqlalchemy import select

from app.debugging import agent_runtime
from app.debugging.findings import list_findings
from app.debugging.models import DebugRunEvent, DebugThread
from tests.test_debug_gateway import setup_run


def test_cited_diagnosis_populates_findings_once_without_confirming_cause(
    db, test_settings, monkeypatch
):
    _, run, _, _ = setup_run(db)
    occurrence = run.evidence["occurrence_id"]
    requests = []
    config = {
        "agent_name": "codex",
        "agent_model_id": "selected-model",
        "agent_profile_id": "selected-profile",
        "agent_profile_fingerprint": "a" * 16,
        "timeout_seconds": 30,
        "connector_capabilities": {},
    }

    async def infer(*args, **kwargs):
        requests.append(kwargs)
        return {
            "agent": "codex",
            "model_id": "selected-model",
            "profile_id": "selected-profile",
            "execution_mode": "real",
            "payload": {
                "kind": "diagnosis",
                "happened": "A synthetic operation failed",
                "facts": ["Failure was recorded", "Failure was recorded"],
                "hypotheses": ["A boundary check may be missing"],
                "next_checks": ["Reproduce with the bounded test fixture"],
                "evidence_ids": [occurrence],
            },
        }

    monkeypatch.setattr(agent_runtime, "_agent_service_json", infer)

    def execute():
        return asyncio.run(
            agent_runtime.run_agent(
                test_settings,
                db.connection(),
                run.id,
                run.lease_token,
                config,
                [{"role": "user", "content": "Investigate"}],
            )
        )

    first = execute()
    assert execute() == first
    assert len(requests) == 1
    db.expire_all()
    proposals = list(
        db.scalars(
            select(DebugRunEvent).where(
                DebugRunEvent.run_id == run.id, DebugRunEvent.kind == "finding_proposed"
            )
        )
    )
    assert len(proposals) == 3
    assert {p.payload["classification"] for p in proposals} == {
        "observed_fact",
        "hypothesis",
        "next_check",
    }
    assert all(p.payload["occurrence_id"] == occurrence for p in proposals)
    issue = db.get(DebugThread, run.thread_id).issue_id
    findings = list_findings(db, issue, None, 20, 0)["findings"]
    assert len(findings) == 3
    assert all(f["verification"] is None for f in findings)
