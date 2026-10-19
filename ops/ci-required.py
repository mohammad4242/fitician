"""Evaluate the stable Required CI check against selected-job results."""

from __future__ import annotations

import argparse
import json
import os
import sys

PLAN_JOBS = {
    "run_frontend": "frontend",
    "run_frontend_browser": "frontend-browser",
    "run_shared": "shared",
    "run_mobile": "mobile",
    "run_android": "android",
    "run_dependencies": "dependencies",
    "run_production_contract": "production-contract",
    "run_scalability": "scalability-contract",
    "run_multi_replica": "multi-replica-smoke",
    "run_split_region": "split-region-smoke",
}
ALL_JOBS = (
    "changes",
    "backend",
    "frontend",
    "backend-component",
    "frontend-browser",
    "shared",
    "mobile",
    "android",
    "dependencies",
    "secrets",
    "production-contract",
    "scalability-contract",
    "multi-replica-smoke",
    "split-region-smoke",
    "agent",
    "container-images",
)


def failures(plan: dict, results: dict, *, image_required: bool) -> list[str]:
    failed = []
    for always_required in ("changes", "secrets"):
        if results.get(always_required) != "success":
            failed.append(always_required)
    agent_result = results.get("agent")
    if agent_result in {"failure", "cancelled"} or (
        plan.get("full_ci_required") is True and agent_result != "success"
    ):
        failed.append("agent")
    if results.get("backend-component") in {"failure", "cancelled"}:
        failed.append("backend-component")
    backend_job = "backend" if plan.get("full_ci_required") is True else "backend-component"
    backend_result = results.get(backend_job)
    if backend_result in {"failure", "cancelled"} or (
        plan.get("run_backend") is True and backend_result != "success"
    ):
        failed.append(backend_job)
    for selector, job in PLAN_JOBS.items():
        result = results.get(job)
        if result in {"failure", "cancelled"} or (
            plan.get(selector) is True and result != "success"
        ):
            failed.append(job)
    image_result = results.get("container-images")
    if image_result in {"failure", "cancelled"} or (
        image_required and image_result != "success"
    ):
        failed.append("container-images")
    return sorted(set(failed))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--image-required", action="store_true")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan)
        results = json.loads(os.environ["CI_JOB_RESULTS"])
        if not isinstance(plan, dict) or not isinstance(results, dict):
            raise TypeError
    except (KeyError, json.JSONDecodeError, TypeError, ValueError) as error:
        print("Required CI inputs are malformed", file=sys.stderr)
        raise SystemExit(1) from error
    failed = failures(plan, results, image_required=args.image_required)
    if failed:
        print("Required CI checks failed: " + ", ".join(failed), file=sys.stderr)
        raise SystemExit(1)
    print("All selected validation jobs passed")


if __name__ == "__main__":
    main()
