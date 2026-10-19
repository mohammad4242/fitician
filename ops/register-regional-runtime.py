"""Adopt an already-running regional deployment after read-only proof."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import regional_runtime

ROOT = Path(__file__).resolve().parents[1]
REMOTE_PROBE = ROOT / "ops" / "regional_runtime.py"
WORKFLOW_NAME = "Fitician local scalability checks"
SCALABILITY_JOB = "Local multi-replica load and failure drills"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate_foundation_evidence(
    run: dict,
    jobs: list[dict],
    artifacts: list[dict],
    *,
    repository: str,
    runtime_sha: str,
    now: datetime | None = None,
) -> dict:
    """Verify successful same-main-SHA local-scale run and its retained artifact."""

    now = now or datetime.now(UTC)
    run_id = run.get("id")
    created_text = run.get("created_at", "")
    try:
        created = datetime.fromisoformat(created_text.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError("Scalability evidence timestamp is invalid") from error
    if (
        not isinstance(run_id, int)
        or run_id <= 0
        or run.get("name") != WORKFLOW_NAME
        or run.get("path") != ".github/workflows/load-test.yml"
        or run.get("head_branch") != "main"
        or (run.get("head_repository") or {}).get("full_name") != repository
        or run.get("head_sha") != runtime_sha
        or not SHA_RE.fullmatch(runtime_sha)
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or created.tzinfo is None
        or not timedelta(0) <= now - created <= timedelta(days=14)
    ):
        raise ValueError("Scalability evidence is failed, stale, or mismatched")
    matches = [job for job in jobs if job.get("name") == SCALABILITY_JOB]
    if len(matches) != 1 or matches[0].get("conclusion") != "success":
        raise ValueError("Scalability workflow job is not successful")
    artifact_name = f"fitician-scalability-{run_id}"
    matches = [
        artifact for artifact in artifacts if artifact.get("name") == artifact_name
    ]
    if (
        len(matches) != 1
        or matches[0].get("expired") is not False
        or not isinstance(matches[0].get("size_in_bytes"), int)
        or matches[0]["size_in_bytes"] <= 0
    ):
        raise ValueError("Successful scalability artifact is missing or expired")
    artifact = matches[0]
    return {
        "run_id": run_id,
        "sha": runtime_sha,
        "repository": repository,
        "workflow": WORKFLOW_NAME,
        "branch": "main",
        "created_at": created.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "job": SCALABILITY_JOB,
        "job_conclusion": "success",
        "artifact": artifact_name,
        "artifact_id": artifact.get("id"),
        "artifact_size_in_bytes": artifact["size_in_bytes"],
        "artifact_expired": False,
    }


def _gh_json(endpoint: str) -> dict:
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise ValueError("Unable to verify GitHub evidence") from error


def load_foundation_evidence(repository: str, run_id: int, runtime_sha: str) -> dict:
    base = f"repos/{repository}/actions/runs/{run_id}"
    run = _gh_json(base)
    jobs_response = _gh_json(base + "/jobs?per_page=100")
    artifacts_response = _gh_json(base + "/artifacts?per_page=100")
    jobs = jobs_response.get("jobs", [])
    artifacts = artifacts_response.get("artifacts", [])
    return validate_foundation_evidence(
        run,
        jobs,
        artifacts,
        repository=repository,
        runtime_sha=runtime_sha,
    )


def _repository() -> str:
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Unable to identify the current GitHub repository") from error
    value = result.stdout.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Current GitHub repository identity is invalid")
    return value


def _ssh(
    alias: str,
    app_dir: Path,
    *,
    apply: bool,
    probe: dict,
    evidence: dict | None,
    accepted_at: str,
) -> dict:
    args = [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        alias,
        "python3",
        "-",
        "--alias",
        alias,
        "--app-dir",
        str(app_dir),
        "--apply" if apply else "--probe",
    ]
    if apply:
        args.append("--owner-approved")
        args.extend(
            [
                "--expected-invariant-sha256",
                probe["invariant_sha256"],
                "--accepted-at",
                accepted_at,
            ]
        )
        if evidence is not None:
            encoded = base64.urlsafe_b64encode(
                json.dumps(evidence, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            args.extend(["--evidence-b64", encoded])
    try:
        result = subprocess.run(
            args,
            input=REMOTE_PROBE.read_text(encoding="utf-8"),
            check=True,
            capture_output=True,
            text=True,
            timeout=150,
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise ValueError("Remote read-only proof or registration failed") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, choices=("iran", "alman"))
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--evidence-run-id", type=int)
    parser.add_argument(
        "--apply", action="store_true", help="write only missing safe markers"
    )
    parser.add_argument("--owner-approved", action="store_true")
    args = parser.parse_args()
    if args.apply != args.owner_approved:
        parser.error("--apply requires --owner-approved; default mode is read-only")
    if not args.app_dir.is_absolute() or not re.fullmatch(
        r"/[A-Za-z0-9._/-]+", str(args.app_dir)
    ):
        parser.error("--app-dir must be an absolute safe path")
    try:
        region = regional_runtime.validate_region(args.region)
        if args.region not in {"iran", "alman"}:
            raise ValueError("Unsupported SSH alias")
        probe = _ssh(
            args.region,
            args.app_dir,
            apply=False,
            probe={},
            evidence=None,
            accepted_at="",
        )
        evidence = None
        if region == "iran" and probe["markers"]["scalability_acceptance"] == "missing":
            if args.evidence_run_id is None:
                raise ValueError(
                    "Iran adoption requires --evidence-run-id for fresh full artifact proof"
                )
            evidence = load_foundation_evidence(
                _repository(), args.evidence_run_id, probe["app_sha"]
            )
        result: dict = {
            "mode": "apply" if args.apply else "dry-run",
            "runtime": probe,
            "foundation_evidence": evidence,
            "writes": [],
        }
        if args.apply:
            accepted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            registration = _ssh(
                args.region,
                args.app_dir,
                apply=True,
                probe=probe,
                evidence=evidence,
                accepted_at=accepted_at,
            )
            result["registration"] = registration
            result["writes"] = [
                key
                for key, value in (
                    (
                        "active_contract_marker",
                        registration.get("active_contract_created"),
                    ),
                    (
                        "scalability_foundation_marker",
                        registration.get("scalability_marker_created"),
                    ),
                    ("sanitized_remote_evidence", registration.get("evidence_path")),
                )
                if value
            ]
        print(json.dumps(result, sort_keys=True))
    except (ValueError, KeyError, TypeError) as error:
        # Exceptions from SSH/GitHub are sanitized by the wrappers above.
        print(str(error), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
