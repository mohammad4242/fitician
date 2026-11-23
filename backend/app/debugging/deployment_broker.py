"""Reconcile durable release actions; a completed workflow never resolves an issue."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from .automation_client import Rpc
from .github_automation import REPOSITORY, GitHubAutomation
from .github_deployment import WORKFLOW, GitHubDeployment


async def advance_deployment(
    job: dict[str, Any], github: GitHubAutomation, rpc: Rpc
) -> dict[str, Any]:
    identifier = UUID(job["id"])
    prefix = "/operations/" + str(identifier)
    adapter = GitHubDeployment(github)

    async def receipt(stage: str, value: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = await rpc(
            prefix + "/progress",
            {"lease_token": job["lease_token"], "stage": stage, "result": value},
        )
        return {**job, **response["operation"]}, response["disposition"]

    state = job["state"]
    if state == "verifying":
        proof = await github._json_artifact(
            job["result"]["workflow_run_id"],
            "fitician-deployment-" + str(identifier),
            "deployment.json",
            "readback",
        )
        job, _ = await receipt("deployment_verified", proof)
        return job
    if state == "preparing":
        if job.get("cancel_requested"):
            job, _ = await receipt("failed", {"code": "automation_cancelled_before_dispatch"})
            return job
        if not job["result"].get("preview"):
            proof = await adapter.preview(job["request"])
            job, _ = await receipt("deployment_prepared", proof)
            return job
        grant = job["result"].get("grant")
        if not grant:
            raise ValueError("deployment_not_authorized")
        if grant["expires_at"] <= int(time.time()):
            raise ValueError("deployment_authorization_expired")
        # Recheck merged repair, CI attempt and immutable artifact before external mutation.
        current = await adapter.preview(job["request"])
        if current != job["result"]["preview"]:
            raise ValueError("github_release_not_ready")
        job, disposition = await receipt("dispatch_intent", {})
        if disposition != "dispatch_once":
            return job
        try:
            run_id = await adapter.dispatch(identifier, grant)
        except ValueError as error:
            if str(error) != "github_mutation_uncertain":
                raise
            run_id = None
        job, _ = (
            await receipt("dispatched", {"workflow_run_id": run_id})
            if run_id
            else await receipt("uncertain", {})
        )
    elif state in {"dispatching", "uncertain"}:
        # Do not repeat deployment after a lost acknowledgement, even after grant expiry.
        existing = await adapter.find(identifier, job["result"]["preview"]["policy_commit"])
        if existing:
            job, _ = await receipt("dispatched", {"workflow_run_id": existing["id"]})
    elif state == "running":
        authority = await rpc(
            prefix + "/authorize", {"lease_token": job["lease_token"], "intent": "observe"}
        )
        if not authority.get("authorized"):
            raise ValueError("automation_authority_lost")
        run_id = job["result"]["workflow_run_id"]
        run = await github.validation_run(run_id)
        if (
            run.get("head_sha") != job["result"]["preview"]["policy_commit"]
            or run.get("path") != ".github/workflows/" + WORKFLOW
            or run.get("event") != "workflow_dispatch"
            or run.get("head_repository", {}).get("full_name") != REPOSITORY
            or run.get("display_title") != "Debug deployment " + str(identifier)
        ):
            raise ValueError("github_invalid_identity")
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
        job, _ = await receipt(
            "deployment_completed",
            {"workflow_run_id": run_id, "workflow_conclusion": run.get("conclusion")},
        )
    return job
