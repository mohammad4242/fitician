import asyncio
from uuid import uuid4

from app.debugging.automation_client import advance
from app.debugging.github_automation import REPOSITORY


def test_restart_after_uncertain_dispatch_observes_existing_run_without_dispatching_again():
    identifier = str(uuid4())
    job = {
        "id": identifier,
        "kind": "validate",
        "state": "uncertain",
        "lease_token": str(uuid4()),
        "request": {"profile": "backend", "tests": ["backend/tests/test_debug_runs.py"]},
        "result": {"policy_commit": "a" * 40, "candidate_commit": "b" * 40},
    }
    actions = []

    class Github:
        async def find_validation(self, operation_id, policy):
            return {"id": 123}

        async def dispatch_validation(self, *args):
            raise AssertionError("Unknown dispatch must never be repeated")

    async def rpc(path, payload):
        assert path.endswith("/progress")
        actions.append(payload)
        return {
            "operation": {
                **job,
                "state": "running",
                "result": {**job["result"], "workflow_run_id": 123},
            },
            "disposition": "recorded",
        }

    result = asyncio.run(advance(job, Github(), rpc))
    assert result["state"] == "running"
    assert [a["stage"] for a in actions] == ["dispatched"]


def test_successful_dispatch_is_preceded_by_persisted_intent_and_not_inferred_from_acceptance():
    identifier = str(uuid4())
    job = {
        "id": identifier,
        "kind": "validate",
        "state": "preparing",
        "lease_token": str(uuid4()),
        "request": {"profile": "migrations", "tests": []},
        "result": {"policy_commit": "a" * 40, "candidate_commit": "b" * 40},
    }
    order = []

    class Github:
        async def dispatch_validation(self, *args):
            order.append("dispatch")
            assert order[0] == "dispatch_intent"
            return None

    async def rpc(path, payload):
        order.append(payload["stage"])
        return {
            "operation": {**job, "state": "dispatching"},
            "disposition": "dispatch_once" if payload["stage"] == "dispatch_intent" else "recorded",
        }

    asyncio.run(advance(job, Github(), rpc))
    assert order == ["dispatch_intent", "dispatch", "uncertain"]


def test_cancellation_targets_only_the_recorded_workflow_and_does_not_fabricate_delivery():
    job = {
        "id": str(uuid4()),
        "kind": "validate",
        "state": "running",
        "lease_token": str(uuid4()),
        "request": {"profile": "migrations", "tests": []},
        "result": {"workflow_run_id": 123, "policy_commit": "a" * 40, "candidate_commit": "b" * 40},
    }
    actions = []

    class Github:
        async def validation_run(self, run_id):
            return {
                "id": run_id,
                "head_sha": "a" * 40,
                "path": ".github/workflows/debug-validation.yml",
                "event": "workflow_dispatch",
                "head_repository": {"full_name": REPOSITORY},
                "display_title": "Debug validation " + job["id"],
                "status": "in_progress",
            }

        async def cancel_validation(self, run_id):
            actions.append(run_id)

    async def rpc(path, payload):
        if path.endswith("/progress"):
            return {"operation": job, "disposition": "cancel_once"}
        return {"authorized": True, "cancel_requested": True, "state": "running"}

    result = asyncio.run(advance(job, Github(), rpc))
    assert result["state"] == "running" and actions == [123]


def test_cancelled_preparation_does_not_dispatch_or_create_a_github_branch():
    job = {
        "id": str(uuid4()),
        "kind": "validate",
        "state": "preparing",
        "cancel_requested": True,
        "lease_token": str(uuid4()),
        "request": {},
        "result": {},
    }
    receipts = []

    async def rpc(path, payload):
        receipts.append(payload)
        return {"operation": {**job, "state": "cancelled"}, "disposition": "recorded"}

    result = asyncio.run(advance(job, object(), rpc))
    assert result["state"] == "cancelled"
    assert receipts[0]["result"]["code"] == "automation_cancelled_before_dispatch"


def test_preflight_is_cached_for_one_minute_and_invalidated_on_credential_rotation():
    from app.debugging.automation_client import PreflightCache

    checks = []

    class Github:
        async def preflight(self):
            checks.append("request")
            return {
                "github_authenticated": True,
                "workflow_installed": True,
                "policy_commit": "a" * 40,
            }

    async def exercise():
        cache = PreflightCache()
        first = await cache.get(Github(), "first-private-token", now=100)
        assert await cache.get(Github(), "first-private-token", now=159) == first
        assert len(checks) == 1
        await cache.get(Github(), "first-private-token", now=160)
        await cache.get(Github(), "rotated-private-token", now=161)
        assert len(checks) == 3
        assert "private-token" not in repr(vars(cache))

    asyncio.run(exercise())


def test_publication_restart_reconciles_without_repeating_an_unknown_post():
    job = {
        "id": str(uuid4()),
        "kind": "publish_pr",
        "state": "uncertain",
        "lease_token": str(uuid4()),
        "request": {"validation_id": str(uuid4())},
        "result": {},
    }
    checks = []

    class Github:
        async def publish_validated_pr(self, request, *, create):
            checks.append(create)
            assert create is False
            return None

    async def rpc(path, payload):
        raise AssertionError("No receipt may fabricate a PR")

    assert asyncio.run(advance(job, Github(), rpc))["state"] == "uncertain"
    assert checks == [False]
