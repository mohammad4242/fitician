import asyncio
import time
from uuid import uuid4

import pytest

from app.debugging.deployment_broker import advance_deployment


def job(state):
    return {
        "id": str(uuid4()),
        "kind": "deploy",
        "state": state,
        "request": {},
        "lease_token": str(uuid4()),
        "result": {
            "preview": {"policy_commit": "a" * 40},
            "grant": {"expires_at": int(time.time()) + 1000},
        },
    }


def test_lost_deploy_acknowledgement_only_reconciles_and_never_redispatches(monkeypatch):
    import app.debugging.deployment_broker as broker

    original = job("uncertain")
    calls = []

    class Adapter:
        def __init__(self, github):
            pass

        async def find(self, identifier, policy):
            calls.append("find")
            return {"id": 123}

        async def dispatch(self, *args):
            raise AssertionError("Duplicate deployment")

    monkeypatch.setattr(broker, "GitHubDeployment", Adapter)

    async def rpc(path, payload):
        calls.append(payload["stage"])
        return {"operation": {**original, "state": "running"}, "disposition": "recorded"}

    result = asyncio.run(advance_deployment(original, None, rpc))
    assert result["state"] == "running" and calls == ["find", "dispatched"]


def test_changed_artifact_and_missing_authorization_cannot_reach_dispatch(monkeypatch):
    import app.debugging.deployment_broker as broker

    original = job("preparing")
    calls = []

    class Adapter:
        def __init__(self, github):
            pass

        async def preview(self, request):
            return {"policy_commit": "b" * 40}

        async def dispatch(self, *args):
            raise AssertionError("Unauthorized deployment")

    monkeypatch.setattr(broker, "GitHubDeployment", Adapter)

    async def rpc(path, payload):
        calls.append(payload)
        raise AssertionError("No dispatch intent without matching artifact")

    with pytest.raises(ValueError, match="github_release_not_ready"):
        asyncio.run(advance_deployment(original, None, rpc))
    original["result"].pop("grant")
    with pytest.raises(ValueError, match="deployment_not_authorized"):
        asyncio.run(advance_deployment(original, None, rpc))
    assert calls == []


def test_cancellation_before_preparation_never_touches_github():
    original = job("preparing")
    original["cancel_requested"] = True
    receipts = []

    async def rpc(path, value):
        receipts.append(value)
        return {"operation": {**original, "state": "cancelled"}, "disposition": "recorded"}

    result = asyncio.run(advance_deployment(original, None, rpc))
    assert result["state"] == "cancelled"
    assert receipts[0]["result"] == {"code": "automation_cancelled_before_dispatch"}
