#!/usr/bin/env python3
"""Discover and verify recent complete CI evidence for unchanged application inputs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FULL_JOBS = (
    "Select validation and release path",
    "Secret scan",
    "Backend tests",
    "Frontend verification",
    "Frontend browser regression (Chromium and WebKit)",
    "Shared core and contract checks",
    "Mobile tests and validation",
    "Android debug build",
    "Dependency audit",
    "Production Compose and deployment checks",
    "Scalability foundation contract checks",
    "Short two-replica runtime smoke",
    "Isolated Iran and Germany HTTP smoke",
    "Agent complete suite",
)
OPS_PATHS = {
    "compose.prod.iran.yaml",
    "compose.prod.germany.yaml",
    "compose.split-test.yaml",
    "Caddyfile",
    "ops/ci-baseline.py",
    "ops/ci-classify.py",
    "ops/ci-release-gate.py",
    "ops/check-db-connection-budget.py",
    "ops/check-runtime-capacity.py",
    "ops/deploy-regional.sh",
    "ops/verify-regional.sh",
    "ops/split-test.sh",
    "ops/split_test_probe.py",
    "ops/redis/redis.conf",
    "ops/env/iran.env.example",
    "ops/env/germany.env.example",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy-production.yml",
    ".github/workflows/deploy-component.yml",
    ".github/workflows/deploy-regional.yml",
    ".github/workflows/deploy-caddy-production.yml",
    ".github/workflows/frontend-appearance-release.yml",
    ".github/workflows/frontend-only.yml",
    ".github/workflows/backend-only.yml",
}


def ops_only(paths: list[str]) -> bool:
    return any(not path.startswith("docs/") for path in paths) and all(
        path in OPS_PATHS
        or path.startswith("ops/tests/")
        and path.endswith(".py")
        or path.startswith("docs/")
        and path.endswith(".md")
        for path in paths
    )


def git_delta(base: str, head: str, root: Path = ROOT) -> list[str]:
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, head],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if ancestry.returncode:
        raise ValueError("Full CI baseline is not a candidate ancestor")
    raw = subprocess.check_output(
        ["git", "diff", "--no-renames", "--name-only", "-z", base, head], cwd=root
    )
    return sorted(os.fsdecode(path) for path in raw.split(b"\0") if path)


def verify(
    evidence: dict, repository: str, head: str, root: Path = ROOT, *, now: datetime | None = None
) -> dict:
    try:
        run, jobs, plan = evidence["run"], evidence["jobs"], evidence["plan"]
        sha = run["head_sha"]
        valid = (
            re.fullmatch(r"[0-9a-f]{40}", sha)
            and run["head_repository"]["full_name"] == repository
            and run["name"] == "Fitician CI"
            and run["path"] == ".github/workflows/ci.yml"
            and run["status"] == "completed"
            and run["conclusion"] == "success"
            and run["event"] in {"push", "workflow_dispatch"}
            and plan["sha"] == sha
            and plan["full_ci_required"] is True
            and isinstance(run["id"], int)
            and run["id"] > 0
        )
        if not valid:
            raise ValueError("Untrusted Full CI baseline")
        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        now = now or datetime.now(UTC)
        if created.tzinfo is None or not -timedelta(minutes=5) <= now - created <= timedelta(
            days=7
        ):
            raise ValueError("Full CI baseline must be at most seven days old")
        for name in FULL_JOBS:
            matches = [job for job in jobs if job["name"].split(" / ")[-1] == name]
            if len(matches) != 1 or matches[0]["conclusion"] != "success":
                raise ValueError("Incomplete Full CI baseline")
        paths = git_delta(sha, head, root)
        if not ops_only(paths):
            raise ValueError("Candidate changes require full validation")
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("Malformed Full CI baseline") from error
    return {"run_id": run["id"], "sha": sha, "changed_paths": paths}


def api(endpoint: str) -> dict:
    return json.loads(subprocess.check_output(["gh", "api", endpoint]))


def api_jobs(endpoint: str) -> list[dict]:
    pages = subprocess.check_output(
        [
            "gh",
            "api",
            "--paginate",
            endpoint + "/jobs?per_page=100&filter=latest",
            "--jq",
            ".jobs | @json",
        ],
        text=True,
    )
    return [job for page in pages.splitlines() for job in json.loads(page)]


def load_run(repository: str, run_id: int, directory: Path) -> dict:
    endpoint = f"repos/{repository}/actions/runs/{run_id}"
    run = api(endpoint)
    jobs = api_jobs(endpoint)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=directory) as scratch:
        subprocess.run(
            [
                "gh",
                "run",
                "download",
                str(run_id),
                "--repo",
                repository,
                "--name",
                "fitician-release-plan",
                "--dir",
                scratch,
            ],
            check=True,
            capture_output=True,
        )
        plan = json.loads((Path(scratch) / "release-plan.json").read_text())
    return {"run": run, "jobs": jobs, "plan": plan}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    evidence = {}
    runs = api(f"repos/{repository}/actions/workflows/ci.yml/runs?status=success&per_page=100")
    for run in runs["workflow_runs"]:
        # Avoid downloading unrelated or expired artifacts.
        try:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if datetime.now(UTC) - created > timedelta(days=7):
                continue
            if not ops_only(git_delta(run["head_sha"], args.head)):
                continue
            candidate = load_run(repository, run["id"], args.output.parent)
            proof = verify(candidate, repository, args.head)
        except (ValueError, subprocess.CalledProcessError, OSError):
            continue
        evidence = candidate
        print(f"Verified complete baseline run={proof['run_id']} SHA={proof['sha']}")
        break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    if not evidence:
        print("No reusable complete baseline; normal fail-closed selection applies")


if __name__ == "__main__":
    main()
