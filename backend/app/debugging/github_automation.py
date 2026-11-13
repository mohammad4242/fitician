"""Fixed GitHub API adapter; credentials stay in the separate automation worker."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from .ci_contract import validate_snapshot, validation_spec

REPOSITORY = "mohammad4242/fitician"
PREFIX = "https://api.github.com/repos/" + REPOSITORY
WORKFLOW = "debug-validation.yml"
API_VERSION = "2026-03-10"


def private_credential(path: Path) -> str:
    if (
        not path.is_absolute()
        or not path.is_file()
        or path.is_symlink()
        or path.stat().st_mode & 0o077
        or path.stat().st_size > 16384
    ):
        raise ValueError("github_credential_not_configured")
    try:
        value = json.loads(path.read_text())
        token = value["token"]
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_]{20,255}", token):
            raise ValueError
        return token
    except (ValueError, KeyError, TypeError):
        raise ValueError("github_credential_not_configured") from None


def sha(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise ValueError("github_invalid_identity")
    return value


class GitHubAutomation:
    def __init__(
        self,
        client: httpx.AsyncClient,
        token: str,
        *,
        guard: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        if "authorization" in client.headers or client.auth is not None:
            raise ValueError("github_client_default_auth_not_allowed")
        self.client = client
        self._token = token
        self.guard = guard

    async def _api(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        missing: bool = False,
    ) -> Any:
        # Paths originate only in the fixed methods below, never model-supplied URLs.
        if method != "GET" and self.guard:
            intent = (
                "publish"
                if path == "/pulls"
                else "dispatch"
                if path.endswith("/dispatches")
                else "cancel"
                if path.endswith("/cancel")
                else "prepare"
            )
            await self.guard(intent)
        try:
            async with self.client.stream(
                method,
                PREFIX + path,
                json=payload,
                headers={
                    "Authorization": "Bearer " + self._token,
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": API_VERSION,
                },
                timeout=20,
                follow_redirects=False,
            ) as response:
                if response.status_code == 404 and missing:
                    return None
                if response.status_code == 429 or (
                    response.status_code == 403
                    and (
                        response.headers.get("x-ratelimit-remaining") == "0"
                        or response.headers.get("retry-after")
                    )
                ):
                    raise ValueError("github_rate_limited")
                if response.status_code in {401, 403}:
                    raise ValueError("github_authorization_rejected")
                if response.status_code not in {200, 201, 202, 204}:
                    raise ValueError("github_request_rejected")
                if response.status_code in {202, 204}:
                    return None
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 8388608:
                        raise ValueError("github_response_too_large")
                try:
                    return json.loads(data)
                except ValueError:
                    raise ValueError("github_invalid_response") from None
        except httpx.HTTPError:
            raise ValueError(
                "github_mutation_uncertain" if method != "GET" else "github_unreachable"
            ) from None

    async def main_commit(self) -> str:
        result = await self._api("GET", "/git/ref/heads/main")
        return sha(result["object"]["sha"])

    async def publish_validated_pr(
        self, request: dict[str, Any], *, create: bool
    ) -> dict[str, Any] | None:
        """One immutable draft; a timed-out POST is reconciled, never retried here."""
        proof = request["proof"]
        identifier = str(UUID(request["validation_id"]))
        candidate, policy = sha(proof["candidate_commit"]), sha(proof["policy_commit"])
        branch = "debug/ci-" + identifier
        if proof["branch"] != branch or not re.fullmatch(
            r"(fix|feat|test|refactor)\([A-Za-z0-9_-]+\): [^\r\n]{5,120}", request["title"]
        ):
            raise ValueError("github_publication_proof_mismatch")
        workflow = await self.validation_run(proof["workflow_run_id"])
        if (
            workflow.get("head_sha") != policy
            or workflow.get("event") != "workflow_dispatch"
            or workflow.get("path") != ".github/workflows/" + WORKFLOW
            or workflow.get("display_title") != "Debug validation " + identifier
            or workflow.get("head_repository", {}).get("full_name") != REPOSITORY
            or workflow.get("status") != "completed"
            or workflow.get("conclusion") != "success"
        ):
            raise ValueError("github_publication_proof_mismatch")
        artifact = await self.validation_artifact(
            proof["workflow_run_id"], UUID(identifier), request["profile"]
        )
        if any(
            artifact.get(k) != proof.get(k)
            for k in ("artifact_id", "artifact_digest", "validation")
        ):
            raise ValueError("github_publication_proof_mismatch")
        current = await self._api("GET", "/git/ref/heads/" + branch)
        if current.get("object", {}).get("sha") != candidate:
            raise ValueError("github_publication_branch_changed")
        existing = await self._api(
            "GET", f"/pulls?state=all&head=mohammad4242:{branch}&base=main&per_page=100"
        )
        if not isinstance(existing, list) or len(existing) > 1:
            raise ValueError("github_duplicate_publication")
        if existing:
            pr = existing[0]
            if pr.get("state") != "open":
                raise ValueError("github_publication_already_closed")
        elif not create:
            return None
        else:
            main = await self.main_commit()
            # A changed main requires a new worktree/test; never revert newer unrelated work.
            if main != proof["base_commit"]:
                raise ValueError("github_repair_requires_current_base")
            comparison = await self._api("GET", "/compare/" + main + "..." + candidate)
            paths = {f["path"] for f in request["snapshot"]["files"]}
            if (
                not paths
                or comparison.get("status") != "ahead"
                or comparison.get("merge_base_commit", {}).get("sha") != main
                or {f["filename"] for f in comparison.get("files", [])} != paths
            ):
                raise ValueError("github_publication_proof_mismatch")
            validation = proof["validation"]
            body = (
                "A focused repair prepared through Fitician's issue-scoped debug agent.\n\n"
                f"Exact tested commit: `{candidate}`.\n"
                f"Validation operation: `{identifier}`.\n"
                f"Profile: `{request['profile']}`; exercised: {validation['exercised']}.\n"
                f"Tests: `{json.dumps(request['tests'])}`.\n"
                f"Sandbox image: `{validation['image']}`.\n"
                f"Artifact digest: `{proof['artifact_digest']}`.\n\n"
                f"[CI evidence](https://github.com/{REPOSITORY}/actions/runs/{proof['workflow_run_id']}).\n\n"
                "Tests cover the selected scope only. "
                "Review the diff and required CI before merge. "
                "Deployment and verified resolution require separate artifact-bound authorization "
                "and scenario verification. This operation cannot merge or deploy."
            )
            if await self.main_commit() != main:
                raise ValueError("github_repair_requires_current_base")
            pr = await self._api(
                "POST",
                "/pulls",
                {
                    "head": branch,
                    "base": "main",
                    "draft": True,
                    "title": request["title"],
                    "body": body,
                },
            )
        number = pr.get("number")
        if (
            type(number) is not int
            or number < 1
            or pr.get("html_url") != f"https://github.com/{REPOSITORY}/pull/{number}"
            or pr.get("head", {}).get("sha") != candidate
            or pr.get("head", {}).get("ref") != branch
            or pr.get("base", {}).get("ref") != "main"
        ):
            raise ValueError("github_publication_proof_mismatch")
        return {
            "pr_number": number,
            "pr_url": pr["html_url"],
            "candidate_commit": candidate,
            "branch": branch,
            "base": "main",
        }

    async def preflight(self) -> dict[str, Any]:
        policy = await self.main_commit()
        workflow = await self._api("GET", f"/actions/workflows/{WORKFLOW}", missing=True)
        installed = bool(
            workflow
            and workflow.get("state") == "active"
            and workflow.get("path") == ".github/workflows/" + WORKFLOW
        )
        return {
            "github_authenticated": True,
            "workflow_installed": installed,
            "policy_commit": policy,
            "error_code": None if installed else "github_workflow_not_installed",
        }

    async def _fixed_ref(self, reference: str, commit: str) -> None:
        # Only private candidate branches and exact trusted-policy tags can be created.
        if not re.fullmatch(
            r"heads/debug/ci-[a-f0-9-]{36}|tags/debug-policy/[a-f0-9]{40}", reference
        ):
            raise ValueError("github_ref_not_authorized")
        existing = await self._api("GET", "/git/ref/" + reference, missing=True)
        if existing:
            if existing.get("object", {}).get("sha") != commit:
                raise ValueError("github_immutable_ref_conflict")
            return
        await self._api("POST", "/git/refs", {"ref": "refs/" + reference, "sha": sha(commit)})
        observed = await self._api("GET", "/git/ref/" + reference)
        if observed.get("object", {}).get("sha") != commit:
            raise ValueError("github_immutable_ref_conflict")

    async def prepare_candidate(
        self, operation_id: UUID, snapshot: dict[str, Any], created_at: datetime
    ) -> dict[str, str]:
        snapshot = validate_snapshot(snapshot)
        identifier = str(UUID(str(operation_id)))
        base = sha(snapshot["base_commit"])
        policy = await self.main_commit()
        commit = await self._api("GET", "/git/commits/" + base)
        if commit.get("sha") != base:
            raise ValueError("github_invalid_identity")
        tree = sha(commit["tree"]["sha"])
        candidate = base
        if snapshot["files"]:
            original = await self._api("GET", "/git/trees/" + tree + "?recursive=1")
            if original.get("truncated") or not isinstance(original.get("tree"), list):
                raise ValueError("github_incomplete_tree")
            entries = {entry["path"]: entry for entry in original["tree"]}
            changes = []
            for file in snapshot["files"]:
                before = entries.get(file["path"])
                if before and (
                    before["mode"] not in {"100644", "100755"} or before["type"] != "blob"
                ):
                    raise ValueError("github_snapshot_path_not_regular")
                if file["content"] is None:
                    if before is None:
                        raise ValueError("github_snapshot_delete_not_found")
                    blob = None
                else:
                    value = await self._api(
                        "POST", "/git/blobs", {"content": file["content"], "encoding": "utf-8"}
                    )
                    blob = sha(value["sha"])
                changes.append(
                    {
                        "path": file["path"],
                        "mode": before["mode"] if before else "100644",
                        "type": "blob",
                        "sha": blob,
                    }
                )
            value = await self._api("POST", "/git/trees", {"base_tree": tree, "tree": changes})
            tree = sha(value["sha"])
            # Explicit dates make content-addressed preparation retry-safe across restarts.
            date = created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            author = {
                "name": "Fitician debug_agent",
                "email": "debug-agent@users.noreply.github.com",
                "date": date,
            }
            value = await self._api(
                "POST",
                "/git/commits",
                {
                    "message": f"test(debug-agent): validate isolated repair {identifier}",
                    "tree": tree,
                    "parents": [base],
                    "author": author,
                    "committer": author,
                },
            )
            candidate = sha(value["sha"])
        branch = "debug/ci-" + identifier
        await self._fixed_ref("heads/" + branch, candidate)
        await self._fixed_ref("tags/debug-policy/" + policy, policy)
        return {
            "base_commit": base,
            "candidate_commit": candidate,
            "branch": branch,
            "policy_commit": policy,
            "policy_ref": "debug-policy/" + policy,
            "snapshot_digest": snapshot["snapshot_digest"],
            "tree_digest": snapshot["tree_digest"],
        }

    async def dispatch_validation(
        self, operation_id: UUID, policy: str, candidate: str, profile: str, tests: list[str]
    ) -> int | None:
        spec = validation_spec(profile, tests)
        response = await self._api(
            "POST",
            f"/actions/workflows/{WORKFLOW}/dispatches",
            {
                "ref": "debug-policy/" + sha(policy),
                "return_run_details": True,
                "inputs": {
                    "candidate_sha": sha(candidate),
                    "request_id": str(UUID(str(operation_id))),
                    "profile": spec["profile"],
                    "tests_json": json.dumps(spec["tests"]),
                },
            },
        )
        if response is None:
            return None  # An accepted request without run identity is still unconfirmed.
        run_id = response.get("workflow_run_id")
        if type(run_id) is not int or run_id < 1:
            raise ValueError("github_mutation_uncertain")
        return run_id

    async def find_validation(self, operation_id: UUID, policy: str) -> dict[str, Any] | None:
        title = "Debug validation " + str(UUID(str(operation_id)))
        matches: list[dict[str, Any]] = []
        for page in range(1, 6):
            result = await self._api(
                "GET",
                f"/actions/workflows/{WORKFLOW}/runs?event=workflow_dispatch&per_page=100&page={page}",
            )
            runs = result.get("workflow_runs", [])
            for run in runs:
                if (
                    run.get("display_title") == title
                    and run.get("head_sha") == sha(policy)
                    and run.get("event") == "workflow_dispatch"
                    and run.get("path") == ".github/workflows/" + WORKFLOW
                    and run.get("head_repository", {}).get("full_name") == REPOSITORY
                ):
                    matches.append(run)
            if len(runs) < 100:
                break
        if len(matches) > 1:
            raise ValueError("github_duplicate_dispatch")
        return matches[0] if matches else None

    async def validation_run(self, run_id: int) -> dict[str, Any]:
        if type(run_id) is not int or run_id < 1:
            raise ValueError("github_invalid_identity")
        result = await self._api("GET", f"/actions/runs/{run_id}")
        if not isinstance(result, dict):
            raise ValueError("github_invalid_response")
        return result

    async def cancel_validation(self, run_id: int) -> None:
        if type(run_id) is not int or run_id < 1:
            raise ValueError("github_invalid_identity")
        await self._api("POST", f"/actions/runs/{run_id}/cancel")

    async def validation_artifact(
        self, run_id: int, operation_id: UUID, profile: str
    ) -> dict[str, Any]:
        if (
            type(run_id) is not int
            or run_id < 1
            or profile not in {"backend", "migrations", "frontend", "frontend_build", "agent"}
        ):
            raise ValueError("github_invalid_identity")
        name = f"debug-validation-{UUID(str(operation_id))}-{profile}"
        matches: list[dict[str, Any]] = []
        for page in range(1, 6):
            result = await self._api(
                "GET", f"/actions/runs/{run_id}/artifacts?per_page=100&page={page}"
            )
            items = result.get("artifacts", [])
            matches.extend(
                item for item in items if item.get("name") == name and not item.get("expired")
            )
            if len(items) < 100:
                break
        if len(matches) != 1:
            raise ValueError("github_artifact_not_found")
        artifact = matches[0]
        if (
            type(artifact.get("id")) is not int
            or artifact["id"] < 1
            or not re.fullmatch(r"sha256:[a-f0-9]{64}", artifact.get("digest", ""))
            or type(artifact.get("size_in_bytes")) is not int
            or not 0 < artifact["size_in_bytes"] <= 1048576
        ):
            raise ValueError("github_artifact_invalid")
        try:
            response = await self.client.get(
                PREFIX + f"/actions/artifacts/{artifact['id']}/zip",
                headers={
                    "Authorization": "Bearer " + self._token,
                    "X-GitHub-Api-Version": API_VERSION,
                },
                timeout=20,
                follow_redirects=False,
            )
            if response.status_code != 302:
                raise ValueError("github_artifact_invalid")
            location = response.headers.get("location", "")
            target = urlsplit(location)
            if (
                target.scheme != "https"
                or not target.hostname
                or target.username
                or target.password
                or target.port not in {None, 443}
                or not target.hostname.endswith(
                    (".blob.core.windows.net", ".githubusercontent.com")
                )
            ):
                raise ValueError("github_artifact_invalid")
            data = bytearray()
            # The client has no default authentication. Never forward API authorization.
            async with self.client.stream(
                "GET", location, timeout=20, follow_redirects=False
            ) as download:
                if download.status_code != 200:
                    raise ValueError("github_artifact_invalid")
                async for chunk in download.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > 1048576:
                        raise ValueError("github_artifact_invalid")
            if (
                len(data) != artifact["size_in_bytes"]
                or "sha256:" + hashlib.sha256(data).hexdigest() != artifact["digest"]
            ):
                raise ValueError("github_artifact_invalid")
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if (
                    archive.namelist() != ["validation.json"]
                    or archive.getinfo("validation.json").file_size > 32000
                ):
                    raise ValueError("github_artifact_invalid")
                validation = json.loads(archive.read("validation.json"))
                if not isinstance(validation, dict):
                    raise ValueError("github_artifact_invalid")
            return {
                "artifact_id": artifact["id"],
                "artifact_digest": artifact["digest"],
                "validation": validation,
            }
        except (httpx.HTTPError, zipfile.BadZipFile, KeyError, json.JSONDecodeError):
            raise ValueError("github_artifact_invalid") from None
