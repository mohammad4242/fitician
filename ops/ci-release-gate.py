#!/usr/bin/env python3
"""Check exact-run, exact-SHA release evidence; never infer release from CI success alone."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "classifier", Path(__file__).with_name("ci-classify.py")
)
classifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classifier)


def trusted_run(run: dict, sha: str, repository: str, name: str) -> bool:
    return (
        run["head_sha"] == sha
        and run["conclusion"] == "success"
        and run["name"] == name
        and run["head_branch"] == "main"
        and run["event"] in {"push", "workflow_dispatch"}
        and run["head_repository"]["full_name"] == repository
    )


def require_seo_evidence(repository: str, sha: str) -> None:
    endpoint = (
        f"repos/{repository}/actions/workflows/public-seo.yml/runs"
        f"?head_sha={sha}&branch=main&status=success&per_page=100"
    )
    runs = json.loads(subprocess.check_output(["gh", "api", endpoint]))["workflow_runs"]
    if not any(
        trusted_run(run, sha, repository, "Public SEO delivery") for run in runs
    ):
        raise SystemExit("Missing successful exact-main-SHA production SEO tests")


def release_path(plan: dict, jobs: list[dict], sha: str) -> str:
    if plan.get("sha") != sha:
        raise ValueError("Release evidence SHA mismatch")
    if not plan.get("release_requested") or not plan.get("deployable"):
        return "none"

    def passed(name):
        return any(
            job["name"].endswith(name) and job["conclusion"] == "success"
            for job in jobs
        )

    if not passed("Secret scan"):
        raise ValueError("Missing successful secret scan")
    if plan.get("full_ci_required"):
        if not passed("Build and publish immutable production images"):
            raise ValueError("Exact SHA did not publish full release images")
        return (
            "frontend-full"
            if classifier.frontend_release_paths(plan.get("changed_paths", []))
            else "full"
        )
    if plan.get("deploy_frontend"):
        if not passed("Frontend verification") or not passed(
            "Build, verify, and push frontend image"
        ):
            raise ValueError("Exact SHA did not pass frontend validation/image checks")
    if plan.get("deploy_backend"):
        if not passed("Backend domain verification") or not passed(
            "Build, verify, and push backend image"
        ):
            raise ValueError("Exact SHA did not pass backend validation/image checks")
    if plan.get("run_shared") and not passed("Shared core and contract checks"):
        raise ValueError("Missing successful shared contract checks")
    if plan.get("deploy_agent"):
        raise ValueError("Agent deployment requires Full CI")
    if not plan.get("deploy_frontend") and not plan.get("deploy_backend"):
        return "none"
    return "component"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--require-full", action="store_true")
    parser.add_argument("--require-frontend-full", action="store_true")
    parser.add_argument("--directory", type=Path, default=Path(".ci-evidence"))
    args = parser.parse_args()
    repository = os.environ["GITHUB_REPOSITORY"]
    endpoint = f"repos/{repository}/actions/runs/{args.run_id}"
    run = json.loads(subprocess.check_output(["gh", "api", endpoint]))
    if not trusted_run(run, args.sha, repository, "Fitician CI"):
        raise SystemExit("Untrusted or unsuccessful exact-SHA CI run")
    args.directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "gh",
            "run",
            "download",
            args.run_id,
            "--repo",
            repository,
            "--name",
            "fitician-release-plan",
            "--dir",
            str(args.directory),
        ],
        check=True,
    )
    plan = json.loads((args.directory / "release-plan.json").read_text())
    pages = json.loads(
        subprocess.check_output(
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                endpoint + "/jobs?per_page=100&filter=latest",
            ]
        )
    )
    jobs = [job for page in pages for job in page["jobs"]]
    path = release_path(plan, jobs, args.sha)
    if args.require_frontend_full and path != "frontend-full":
        raise SystemExit("Frontend-only Full CI deployment scope was not verified")
    if path == "frontend-full":
        require_seo_evidence(repository, args.sha)
    if args.require_full and path != "full":
        raise SystemExit(
            "Manual full deployment requires successful Full CI and published images for this SHA"
        )
    print(f"Verified release path={path}; sha={args.sha}; CI run={args.run_id}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            values = {
                "ready": path != "none",
                "release_path": path,
                "deploy_frontend": path == "frontend-full"
                or path == "component"
                and plan["deploy_frontend"],
                "full_ci_run_id": args.run_id if path == "frontend-full" else "",
                "deploy_backend": path == "component" and plan["deploy_backend"],
                "shared_validated": plan.get("run_shared", False),
                "backend_tests": plan.get("backend_tests", []),
            }
            for key, value in values.items():
                rendered = (
                    value
                    if isinstance(value, str)
                    else json.dumps(value, separators=(",", ":"))
                )
                print(f"{key}={rendered}", file=stream)


if __name__ == "__main__":
    main()
