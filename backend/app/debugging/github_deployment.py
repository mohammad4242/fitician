"""Fixed regional release API adapter; no model-provided workflows, refs or commands."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from .github_automation import REPOSITORY, GitHubAutomation, sha
from .release_contract import validate_release

WORKFLOW = "deploy-regional.yml"


class GitHubDeployment:
    def __init__(self, github: GitHubAutomation) -> None:
        self.github = github

    async def preview(self, request: dict[str, Any]) -> dict[str, Any]:
        github = self.github
        main = await github.main_commit()
        pr = await github._api("GET", "/pulls/" + str(int(request["pr_number"])))
        ci = await github.validation_run(request["ci_run_id"])
        if (
            pr.get("merged") is not True
            or pr.get("merge_commit_sha") != main
            or pr.get("base", {}).get("ref") != "main"
            or pr.get("base", {}).get("repo", {}).get("full_name") != REPOSITORY
            or pr.get("head", {}).get("repo", {}).get("full_name") != REPOSITORY
            or pr.get("head", {}).get("sha") != request["candidate_commit"]
            or ci.get("head_sha") != main
            or ci.get("head_branch") != "main"
            or ci.get("path") != ".github/workflows/ci.yml"
            or ci.get("name") != "Fitician CI"
            or ci.get("event") not in {"push", "workflow_dispatch"}
            or ci.get("head_repository", {}).get("full_name") != REPOSITORY
            or ci.get("status") != "completed"
            or ci.get("conclusion") != "success"
        ):
            raise ValueError("github_release_not_ready")
        artifact = await github._json_artifact(
            request["ci_run_id"],
            "fitician-release-manifest-" + main,
            "manifest.json",
            "manifest",
            content_digest=True,
        )
        manifest = validate_release(
            artifact["manifest"], commit=main, ci_run_id=request["ci_run_id"]
        )
        if manifest["run_attempt"] != ci.get("run_attempt"):
            raise ValueError("github_release_not_ready")
        return {
            "manifest": manifest,
            "manifest_sha256": artifact["content_sha256"],
            "artifact_id": artifact["artifact_id"],
            "artifact_digest": artifact["artifact_digest"],
            "policy_commit": main,
            "pr_number": request["pr_number"],
        }

    async def dispatch(self, identifier: UUID, grant: dict[str, Any]) -> int | None:
        if grant["expires_at"] <= int(time.time()):
            raise ValueError("deployment_authorization_expired")
        if await self.github.main_commit() != sha(grant["commit"]):
            raise ValueError("github_release_not_ready")
        target = grant["target_environment"]
        if (target, grant["deploy_kind"]) not in {
            ("production-iran", "full"),
            ("production-germany", "agent"),
        } or grant["allow_schema_migrations"] is not False:
            raise ValueError("deployment_not_authorized")
        value = await self.github._api(
            "POST",
            "/actions/workflows/" + WORKFLOW + "/dispatches",
            {
                "ref": "main",
                "return_run_details": True,
                "inputs": {
                    "target": target.removeprefix("production-"),
                    "deploy_kind": grant["deploy_kind"],
                    "image_tag": grant["commit"],
                    "ci_run_id": str(grant["ci_run_id"]),
                    "owner_approved": "true",
                    "allow_schema_migrations": "false",
                    "initial_deploy": "false",
                    "image_source": "preloaded" if target == "production-iran" else "registry",
                    "expected_manifest_sha256": grant["manifest_sha256"],
                    "expected_baseline_sha256": grant["baseline_sha256"],
                    "authorization_expires_at": str(grant["expires_at"]),
                    "operation_id": str(identifier),
                },
            },
        )
        identifier_value = value.get("workflow_run_id") if value else None
        if type(identifier_value) is not int or identifier_value < 1:
            return None
        return identifier_value

    async def find(self, identifier: UUID, policy: str) -> dict[str, Any] | None:
        matches = []
        for page in range(1, 6):
            value = await self.github._api(
                "GET",
                f"/actions/workflows/{WORKFLOW}/runs?event=workflow_dispatch&per_page=100&page={page}",
            )
            rows = value.get("workflow_runs", [])
            for row in rows:
                if (
                    row.get("display_title") == "Debug deployment " + str(identifier)
                    and row.get("head_sha") == sha(policy)
                    and row.get("head_repository", {}).get("full_name") == REPOSITORY
                    and row.get("path") == ".github/workflows/" + WORKFLOW
                    and row.get("event") == "workflow_dispatch"
                ):
                    matches.append(row)
            if len(rows) < 100:
                break
        if len(matches) > 1:
            raise ValueError("github_duplicate_dispatch")
        return matches[0] if matches else None
