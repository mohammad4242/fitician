"""Observe through the protected fixed workflow. Persist intent before dispatch; never retry it."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from .automation_client import Rpc
from .github_automation import REPOSITORY, GitHubAutomation


async def advance_observation(
    job: dict[str, Any], github: GitHubAutomation, rpc: Rpc
) -> dict[str, Any]:
    identifier = UUID(job["id"])
    prefix = "/operations/" + str(identifier)

    async def receipt(stage: str, value: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = await rpc(
            prefix + "/progress",
            {"lease_token": job["lease_token"], "stage": stage, "result": value},
        )
        return {**job, **response["operation"]}, response["disposition"]

    state = job["state"]
    if state == "preparing":
        if job.get("cancel_requested"):
            job, _ = await receipt("failed", {"code": "automation_cancelled_before_dispatch"})
            return job
        if not job["result"].get("policy_commit"):
            policy = await github.observation_policy()
            job, _ = await receipt("observation_prepared", {"policy_commit": policy})
        job, disposition = await receipt("dispatch_intent", {})
        if disposition != "dispatch_once":
            return job
        try:
            run_id = await github.dispatch_observation(
                identifier,
                job["result"]["policy_commit"],
                job["request"]["target_environment"],
                job["request"]["trace_id"],
            )
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
        existing = await github.find_observation(identifier, job["result"]["policy_commit"])
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
            run.get("head_sha") != job["result"]["policy_commit"]
            or run.get("path") != ".github/workflows/debug-server-observation.yml"
            or run.get("event") != "workflow_dispatch"
            or run.get("head_repository", {}).get("full_name") != REPOSITORY
            or run.get("display_title") != "Debug observation " + str(identifier)
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
        proof: dict[str, Any] = {"artifact_id": None, "artifact_digest": None, "observation": None}
        if run.get("conclusion") == "success":
            proof = await github.observation_artifact(run_id, identifier)
        job, _ = await receipt(
            "observation_completed",
            {**proof, "workflow_run_id": run_id, "workflow_conclusion": run.get("conclusion")},
        )
    return job
