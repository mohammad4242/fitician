#!/usr/bin/env python3
"""Refuse cumulative unvalidated or high-risk changes since the running component."""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


SPEC = importlib.util.spec_from_file_location("classifier", ROOT / "ops/ci-classify.py")
classifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classifier)


def check_plan(
    plan: dict,
    component: str,
    validated_tests: list[str],
    shared_validated: bool,
    *,
    full_frontend_validated: bool = False,
):
    if plan["full_ci_required"]:
        if (
            full_frontend_validated
            and component == "frontend"
            and classifier.frontend_release_paths(plan["changed_paths"])
        ):
            return
        raise SystemExit(
            "Cumulative changes require Full CI/release: "
            + ", ".join(plan["full_reasons"])
        )
    if plan["shared_changed"] and not shared_validated:
        raise SystemExit(
            "Cumulative shared changes need shared validation in this exact run"
        )
    if component == "backend":
        missing = set(plan["backend_tests"]) - set(validated_tests)
        if missing:
            raise SystemExit(
                "Cumulative backend suites were not validated: "
                + ", ".join(sorted(missing))
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", choices=["frontend", "backend"], required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--validated-tests", default="[]")
    parser.add_argument(
        "--shared-validated", choices=["true", "false"], default="false"
    )
    parser.add_argument("--full-ci-run-id", default="")
    args = parser.parse_args()
    if args.full_ci_run_id:
        if args.component != "frontend":
            raise SystemExit("Full CI scoped deployment supports frontend only")
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "ops/ci-release-gate.py"),
                "--run-id",
                args.full_ci_run_id,
                "--sha",
                args.head,
                "--require-frontend-full",
                "--directory",
                ".ci-evidence/component-full",
            ],
            cwd=ROOT,
            check=True,
        )
    # A prior reviewed manual frontend image can be on a divergent branch.
    # Only exact Full CI proof permits it; ordinary component ancestry stays strict.
    ancestry = (
        ["git", "merge-base", args.base, args.head]
        if args.full_ci_run_id
        else ["git", "merge-base", "--is-ancestor", args.base, args.head]
    )
    subprocess.run(
        ancestry,
        cwd=ROOT,
        check=True,
    )
    if args.base == args.head:
        return
    paths = classifier.git_paths(args.base, args.head)
    if args.full_ci_run_id:
        # Compare every frontend image input. Unrelated native/API source was never
        # part of the independently deployed frontend image and will not be touched.
        paths = [
            path
            for path in paths
            if path.startswith(
                ("frontend/", "packages/", "vendor/", "backend/app/exercises/")
            )
            or path in {"package.json", "package-lock.json", ".dockerignore"}
        ]
    plan = classifier.classify(paths)
    check_plan(
        plan,
        args.component,
        json.loads(args.validated_tests),
        args.shared_validated == "true",
        full_frontend_validated=bool(args.full_ci_run_id),
    )
    print("Cumulative component release scope is covered by this exact validation run")


if __name__ == "__main__":
    main()
