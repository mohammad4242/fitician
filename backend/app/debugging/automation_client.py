"""Outbound Germany CI broker. No production shell, database or model credentials."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from .connector import read_private_configuration, save_private, validate_configuration
from .github_automation import REPOSITORY, WORKFLOW, GitHubAutomation, private_credential

CONFIG = Path("/run/fitician-automation/worker.json")
CREDENTIAL = Path("/run/fitician-automation/github.json")
STATE = Path("/state")
Rpc = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class PreflightCache:
    """Bound GitHub polling without retaining a previous private credential."""

    def __init__(self) -> None:
        self.fingerprint = ""
        self.expires = 0.0
        self.result: dict[str, Any] = {}

    async def get(
        self, github: GitHubAutomation, token: str, *, now: float | None = None
    ) -> dict[str, Any]:
        now = time.monotonic() if now is None else now
        fingerprint = hashlib.sha256(token.encode()).hexdigest()
        if fingerprint != self.fingerprint or now >= self.expires:
            self.fingerprint, self.expires = fingerprint, now + 60
            try:
                self.result = await github.preflight()
            except ValueError as error:
                self.result = {
                    "github_authenticated": False,
                    "workflow_installed": False,
                    "policy_commit": None,
                    "error_code": str(error)
                    if str(error).startswith("github_")
                    else "github_unreachable",
                }
        return dict(self.result)


def verify_run(job: dict[str, Any], run: dict[str, Any]) -> None:
    if (
        run.get("head_sha") != job["result"]["policy_commit"]
        or run.get("path") != ".github/workflows/" + WORKFLOW
        or run.get("event") != "workflow_dispatch"
        or run.get("head_repository", {}).get("full_name") != REPOSITORY
        or run.get("display_title") != "Debug validation " + job["id"]
    ):
        raise ValueError("github_invalid_identity")


async def advance(job: dict[str, Any], github: GitHubAutomation, rpc: Rpc) -> dict[str, Any]:
    identifier = UUID(job["id"])
    prefix = "/operations/" + str(identifier)

    async def receipt(stage: str, value: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = await rpc(
            prefix + "/progress",
            {
                "lease_token": job["lease_token"],
                "stage": stage,
                "result": value,
            },
        )
        return {**job, **response["operation"]}, response["disposition"]

    if job["kind"] != "validate":
        raise ValueError("automation_execution_failed")
    state = job["state"]
    if state == "preparing":
        if job.get("cancel_requested"):
            job, _ = await receipt("failed", {"code": "automation_cancelled_before_dispatch"})
            return job
        if not job["result"].get("candidate_commit"):
            preparation = await github.prepare_candidate(
                identifier, job["request"]["snapshot"], datetime.fromisoformat(job["created_at"])
            )
            job, _ = await receipt("prepared", preparation)
        job, disposition = await receipt("dispatch_intent", {})
        if disposition != "dispatch_once":
            return job
        try:
            run_id = await github.dispatch_validation(
                identifier,
                job["result"]["policy_commit"],
                job["result"]["candidate_commit"],
                job["request"]["profile"],
                job["request"]["tests"],
            )
        except ValueError as error:
            if str(error) != "github_mutation_uncertain":
                raise
            run_id = None
        if run_id is None:
            job, _ = await receipt("uncertain", {})
        else:
            job, _ = await receipt("dispatched", {"workflow_run_id": run_id})
        return job
    if state in {"dispatching", "uncertain"}:
        existing = await github.find_validation(identifier, job["result"]["policy_commit"])
        if existing:
            job, _ = await receipt("dispatched", {"workflow_run_id": existing["id"]})
        return job
    if state == "running":
        authority = await rpc(
            prefix + "/authorize", {"lease_token": job["lease_token"], "intent": "observe"}
        )
        if not authority.get("authorized"):
            raise ValueError("automation_authority_lost")
        run_id = job["result"]["workflow_run_id"]
        run = await github.validation_run(run_id)
        verify_run(job, run)
        if run.get("status") != "completed":
            if authority.get("cancel_requested"):
                job, disposition = await receipt("cancel_intent", {})
                if disposition == "cancel_once":
                    try:
                        await github.cancel_validation(run_id)
                    except ValueError as error:
                        if str(error) not in {
                            "github_mutation_uncertain",
                            "github_request_rejected",
                        }:
                            raise
            return job
        conclusion = run.get("conclusion")
        if conclusion not in {
            "success",
            "failure",
            "cancelled",
            "timed_out",
            "neutral",
            "skipped",
            "action_required",
            "startup_failure",
            "stale",
        }:
            raise ValueError("github_invalid_response")
        artifact: dict[str, Any] = {
            "artifact_id": None,
            "artifact_digest": None,
            "validation": None,
        }
        if conclusion != "cancelled":
            try:
                artifact = await github.validation_artifact(
                    run_id, identifier, job["request"]["profile"]
                )
            except ValueError as error:
                if conclusion == "success" or str(error) != "github_artifact_not_found":
                    raise
        job, _ = await receipt(
            "completed", {**artifact, "workflow_run_id": run_id, "workflow_conclusion": conclusion}
        )
        return job
    return job


def make_rpc(client: httpx.AsyncClient, base: str, token: str) -> Rpc:
    async def rpc(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await client.post(
            base + path, json=payload, headers={"Authorization": "Bearer " + token}
        )
        if response.status_code in {401, 403}:
            raise ValueError("automation_channel_authorization_rejected")
        if response.status_code != 200 or len(response.content) > 2097152:
            raise ValueError("automation_channel_unavailable")
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("automation_channel_unavailable")
        return result

    return rpc


def make_guard(rpc: Rpc, job: dict[str, Any]) -> Callable[[str], Awaitable[None]]:
    identifier, lease = job["id"], job["lease_token"]

    async def guard(intent: str) -> None:
        value = await rpc(
            "/operations/" + identifier + "/authorize", {"lease_token": lease, "intent": intent}
        )
        if not value.get("authorized"):
            raise ValueError("automation_authority_lost")

    return guard


class Broker:
    def __init__(
        self, config: Path = CONFIG, credential: Path = CREDENTIAL, state: Path = STATE
    ) -> None:
        self.config_file, self.credential_file, self.root = config, credential, state
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.phase = "starting"
        self.connected = False
        self.revision = os.environ.get("FITICIAN_RUNTIME_COMMIT", "")
        self.preflight = PreflightCache()

    async def pulse(self) -> None:
        while True:
            save_private(
                self.root / "status.json",
                {
                    "heartbeat": time.time(),
                    "state": self.phase,
                    "connected": self.connected,
                    "runtime_revision": self.revision,
                },
            )
            await asyncio.sleep(5)

    async def serve(self) -> None:
        pulse = asyncio.create_task(self.pulse())
        try:
            while True:
                self.connected = False
                self.phase = "awaiting_enrollment"
                if not self.config_file.is_file():
                    await asyncio.sleep(5)
                    continue
                try:
                    config = validate_configuration(read_private_configuration(self.config_file))
                    environment = config["environment"]
                    base = config["server"].rstrip("/") + "/api/v1/debug-automation/" + config["id"]
                    async with (
                        httpx.AsyncClient(
                            timeout=20, trust_env=False, follow_redirects=False
                        ) as channel,
                        httpx.AsyncClient(
                            timeout=20, trust_env=False, follow_redirects=False
                        ) as remote,
                    ):
                        rpc = make_rpc(channel, base, config["token"])
                        while True:
                            heartbeat = {
                                "runtime_revision": self.revision,
                                "github_authenticated": False,
                                "workflow_installed": False,
                                "policy_commit": None,
                                "error_code": None,
                            }
                            try:
                                token = private_credential(self.credential_file)
                                github = GitHubAutomation(remote, token)
                                preflight = await self.preflight.get(github, token)
                                heartbeat.update(preflight)
                            except ValueError as error:
                                heartbeat["error_code"] = (
                                    str(error)
                                    if str(error).startswith("github_")
                                    else "github_unreachable"
                                )
                            response = await rpc("/heartbeat", heartbeat)
                            self.connected = True
                            if response.get("environment") != environment:
                                raise ValueError("automation_environment_mismatch")
                            if (
                                not heartbeat["github_authenticated"]
                                or not heartbeat["workflow_installed"]
                            ):
                                self.phase = str(
                                    heartbeat.get("error_code") or "github_workflow_not_installed"
                                )
                                await asyncio.sleep(10)
                                continue
                            self.phase = "ready"
                            job = (await rpc("/poll", {})).get("job")
                            if not job:
                                await asyncio.sleep(2)
                                continue
                            if job["environment"] != environment or job["repository"] != REPOSITORY:
                                raise ValueError("automation_environment_mismatch")
                            self.phase = job["state"]

                            guard = make_guard(rpc, job)
                            github = GitHubAutomation(remote, token, guard=guard)
                            try:
                                updated = await advance(job, github, rpc)
                                if updated["state"] in {
                                    "preparing",
                                    "dispatching",
                                    "uncertain",
                                    "running",
                                }:
                                    await rpc(
                                        "/operations/" + job["id"] + "/progress",
                                        {
                                            "lease_token": job["lease_token"],
                                            "stage": "waiting",
                                            "result": {
                                                "workflow_status": "unknown"
                                                if updated["state"] == "uncertain"
                                                else "requested"
                                            },
                                        },
                                    )
                            except ValueError as error:
                                code = str(error)
                                if (
                                    code.startswith("github_")
                                    and code != "github_mutation_uncertain"
                                ):
                                    await rpc(
                                        "/operations/" + job["id"] + "/progress",
                                        {
                                            "lease_token": job["lease_token"],
                                            "stage": "failed",
                                            "result": {"code": code},
                                        },
                                    )
                                else:
                                    self.phase = "operation_confirmation_pending"
                            await asyncio.sleep(2)
                except (OSError, ValueError, KeyError, TypeError, httpx.HTTPError):
                    self.phase, self.connected = "configuration_or_connection_blocked", False
                    await asyncio.sleep(10)
        finally:
            pulse.cancel()
            await asyncio.gather(pulse, return_exceptions=True)


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("serve", "health", "status"), default="serve", nargs="?")
    args = parser.parse_args()
    if args.action == "health":
        from .server_runtime import healthy

        raise SystemExit(0 if healthy(STATE / "status.json") else 1)
    if args.action == "status":
        print((STATE / "status.json").read_text())
        return
    asyncio.run(Broker().serve())


if __name__ == "__main__":
    main()
