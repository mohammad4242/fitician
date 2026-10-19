"""Validate a completed main CI run and select a narrowly eligible regional release."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CI_NAME = "Fitician CI"
CI_PATH = ".github/workflows/ci.yml"


def validate_run(run: dict, repository: str, main_sha: str, run_id: int) -> None:
    if (
        run.get("id") != run_id
        or run.get("name") != CI_NAME
        or run.get("path") != CI_PATH
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("head_branch") != "main"
        or run.get("event") != "push"
        or (run.get("head_repository") or {}).get("full_name") != repository
        or not SHA_RE.fullmatch(str(run.get("head_sha", "")))
        or run.get("head_sha") != main_sha
    ):
        raise ValueError("Workflow run is not successful canonical current-main CI")


def agent_source_only(paths: object) -> bool:
    if not isinstance(paths, list) or not paths:
        return False
    has_app_source = False
    for path in paths:
        if not isinstance(path, str):
            return False
        if path.startswith("agent-service/app/") and path.endswith(".py"):
            has_app_source = True
        elif (
            path.startswith("agent-service/tests/") and path.endswith(".py")
        ) or (path.startswith(("docs/", "reports/")) and path.endswith((".md", ".txt"))):
            continue
        else:
            return False
    return has_app_source


def classify_paths(paths: list[str]) -> dict:
    spec = importlib.util.spec_from_file_location(
        "ci_classifier", ROOT / "ops/ci-classify.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("Unable to load changed-path classifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classify(paths, ROOT)


def select_auto_route(plan: dict, release_path: str) -> tuple[str, str]:
    if not plan.get("deployable"):
        raise ValueError("CI run has no deployable release")
    paths = plan.get("changed_paths")
    if not isinstance(paths, list):
        raise TypeError("CI changed-path evidence is malformed")
    classified = classify_paths(paths)
    for key in (
        "full_ci_required",
        "deploy_frontend",
        "deploy_backend",
        "deploy_agent",
    ):
        if classified.get(key) != plan.get(key):
            raise ValueError("CI release plan does not match its changed-path classification")
    if (
        release_path == "full"
        and plan.get("full_ci_required") is True
        and plan.get("selective_ci_required") is not True
        and plan.get("deploy_agent") is True
        and agent_source_only(paths)
    ):
        return "germany", "agent"
    if (
        release_path == "component"
        and plan.get("full_ci_required") is False
        and plan.get("selective_ci_required") is False
        and plan.get("deploy_agent") is False
        and plan.get("deploy_frontend") is True
        and plan.get("deploy_backend") is False
    ):
        return "iran", "frontend"
    if (
        release_path == "component"
        and plan.get("full_ci_required") is False
        and plan.get("selective_ci_required") is False
        and plan.get("deploy_agent") is False
        and plan.get("deploy_frontend") is False
        and plan.get("deploy_backend") is True
    ):
        return "iran", "backend"
    raise ValueError("CI path is ambiguous or outside automatic regional release policy")


def gh_json(endpoint: str) -> dict:
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
        raise ValueError("Unable to verify canonical GitHub Actions evidence") from error


def load_gate():
    spec = importlib.util.spec_from_file_location(
        "ci_release_gate", ROOT / "ops/ci-release-gate.py"
    )
    if spec is None or spec.loader is None:
        raise ValueError("Unable to load CI release gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_automatic_run(repository: str, run_id: int, output_dir: Path) -> dict:
    if run_id <= 0 or "/" not in repository:
        raise ValueError("Invalid workflow run identity")
    base = f"repos/{repository}/actions/runs/{run_id}"
    run = gh_json(base)
    branch = gh_json(f"repos/{repository}/branches/main")
    main_sha = (branch.get("commit") or {}).get("sha", "")
    validate_run(run, repository, main_sha, run_id)

    artifacts = gh_json(f"{base}/artifacts?per_page=100").get("artifacts", [])
    matches = [item for item in artifacts if item.get("name") == "fitician-release-plan"]
    if (
        len(matches) != 1
        or matches[0].get("expired") is not False
        or not isinstance(matches[0].get("size_in_bytes"), int)
        or matches[0]["size_in_bytes"] <= 0
    ):
        raise ValueError("Canonical CI release-plan artifact is missing or expired")
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "gh", "run", "download", str(run_id), "--repo", repository,
                "--name", "fitician-release-plan", "--dir", str(output_dir),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Unable to retrieve canonical CI release plan") from error
    plan_path = output_dir / "release-plan.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Canonical CI release plan is malformed") from error

    gate = load_gate()
    jobs = gh_json(f"{base}/jobs?per_page=100").get("jobs", [])
    path = gate.release_path(plan, jobs, run["head_sha"])
    if path == "selective":
        gate.require_selective_evidence(repository, plan, run["head_sha"], output_dir)
    target, kind = select_auto_route(plan, path)
    return {
        "target": target,
        "deploy_kind": kind,
        "image_tag": run["head_sha"],
        "ci_run_id": run_id,
        "owner_approved": "true",
        "allow_schema_migrations": "false",
        "initial_deploy": "false",
        "first_scalability_release_approved": "false",
        "scalability_evidence_run_id": "",
        "image_source": "registry",
        "auto_release": "true",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--directory", type=Path, default=Path(".ci-evidence/auto"))
    args = parser.parse_args()
    try:
        values = validate_automatic_run(args.repository, args.run_id, args.directory)
    except (ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        raise SystemExit("GITHUB_OUTPUT is required")
    with open(output, "a", encoding="utf-8") as stream:
        for name, value in values.items():
            print(f"{name}={value}", file=stream)


if __name__ == "__main__":
    main()
