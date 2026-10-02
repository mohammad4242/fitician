#!/usr/bin/env python3
"""Refuse cumulative unvalidated or high-risk changes since the running component."""

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_plan(plan: dict, component: str, validated_tests: list[str], shared_validated: bool):
    if plan["full_ci_required"]:
        raise SystemExit(
            "Cumulative changes require Full CI/release: " + ", ".join(plan["full_reasons"])
        )
    if plan["shared_changed"] and not shared_validated:
        raise SystemExit("Cumulative shared changes need shared validation in this exact run")
    if component == "backend":
        missing = set(plan["backend_tests"]) - set(validated_tests)
        if missing:
            raise SystemExit(
                "Cumulative backend suites were not validated: " + ", ".join(sorted(missing))
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=["frontend", "backend"], required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--validated-tests", default="[]")
    parser.add_argument("--shared-validated", choices=["true", "false"], default="false")
    args = parser.parse_args()
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.base, args.head],
        cwd=ROOT,
        check=True,
    )
    if args.base == args.head:
        return
    spec = importlib.util.spec_from_file_location("classify", ROOT / "ops/ci-classify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    plan = module.classify(module.git_paths(args.base, args.head))
    check_plan(
        plan, args.component, json.loads(args.validated_tests), args.shared_validated == "true"
    )
    print("Cumulative component release scope is covered by this exact validation run")


if __name__ == "__main__":
    main()
