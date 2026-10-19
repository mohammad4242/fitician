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


def frontend_image_paths(paths: list[str]) -> list[str]:
    return [
        path
        for path in paths
        if path.startswith(
            ("frontend/", "packages/", "vendor/", "backend/app/exercises/")
        )
        or path in {"package.json", "package-lock.json", ".dockerignore"}
    ]


def agent_image_paths(paths: list[str]) -> list[str]:
    build_files = {
        "agent-service/Dockerfile",
        "agent-service/.dockerignore",
        "agent-service/pyproject.toml",
        "agent-service/uv.lock",
    }
    return [
        path
        for path in paths
        if path.startswith(("agent-service/app/", "agent-service/docker/"))
        or path in build_files
    ]


def strict_agent_image_paths(paths: list[str]) -> list[str]:
    image_paths = agent_image_paths(paths)
    if not image_paths or any(
        not path.startswith("agent-service/app/") or not path.endswith(".py")
        for path in image_paths
    ):
        raise SystemExit("Automatic Agent release includes unvalidated image inputs")
    return image_paths


def role_controller():
    spec = importlib.util.spec_from_file_location(
        "register_regional_runtime", ROOT / "ops/register-regional-runtime.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load runtime role source verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backend_image_paths(
    api_base: str, worker_base: str, head: str
) -> tuple[list[str], dict]:
    controller = role_controller()
    if api_base == worker_base:
        proof = {
            "version": 1,
            "api_sha": api_base,
            "worker_sha": worker_base,
            "ancestor_verified": True,
            "entrypoint_ast_equivalent": True,
            "backend_image_inputs": [],
        }
    else:
        proof = controller.validate_role_source_compatibility(api_base, worker_base)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", worker_base, head],
        cwd=ROOT,
        check=True,
    )
    paths = [
        path
        for path in classifier.git_paths(worker_base, head)
        if path.startswith("backend/")
    ]
    return paths, proof


def check_plan(
    plan: dict,
    component: str,
    validated_tests: list[str],
    shared_validated: bool,
    *,
    full_frontend_validated: bool = False,
    full_agent_validated: bool = False,
):
    if plan["full_ci_required"]:
        if (
            full_frontend_validated
            and component == "frontend"
            and classifier.frontend_release_paths(plan["changed_paths"])
        ):
            return
        if full_agent_validated and component == "agent":
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
    parser.add_argument(
        "--component", choices=["frontend", "backend", "agent"], required=True
    )
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--validated-tests", default="[]")
    parser.add_argument(
        "--shared-validated", choices=["true", "false"], default="false"
    )
    parser.add_argument("--full-ci-run-id", default="")
    parser.add_argument("--full-agent-validated", action="store_true")
    parser.add_argument("--auto-agent", action="store_true")
    parser.add_argument("--worker-base", default="")
    args = parser.parse_args()
    if args.full_ci_run_id:
        if args.component not in {"frontend", "agent"}:
            raise SystemExit(
                "Full CI scoped deployment supports frontend or Agent only"
            )
        if args.component == "agent":
            raise SystemExit("Agent Full CI validation is supplied by the caller")
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
    role_proof = None
    if args.component == "frontend":
        paths = frontend_image_paths(classifier.git_paths(args.base, args.head))
    elif args.component == "backend":
        worker_base = args.worker_base or args.base
        paths, role_proof = backend_image_paths(args.base, worker_base, args.head)
        print(
            "Verified runtime API/worker source roles: "
            + json.dumps(role_proof, sort_keys=True)
        )
    else:
        paths = agent_image_paths(classifier.git_paths(args.base, args.head))
        if args.auto_agent:
            paths = strict_agent_image_paths(paths)
    if args.full_ci_run_id:
        # Compare every frontend image input. Unrelated native/API source was never
        # part of the independently deployed frontend image and will not be touched.
        paths = frontend_image_paths(paths)
    if not paths and args.component in {"frontend", "backend"}:
        print("No cumulative changes to this deployed image's inputs")
        return
    plan = classifier.classify(paths)
    check_plan(
        plan,
        args.component,
        json.loads(args.validated_tests),
        args.shared_validated == "true",
        full_frontend_validated=bool(args.full_ci_run_id),
        full_agent_validated=args.full_agent_validated,
    )
    print("Cumulative component release scope is covered by this exact validation run")


if __name__ == "__main__":
    main()
