#!/usr/bin/env python3
"""Fail-closed changed-path selection shared by CI and production release gates."""

from __future__ import annotations

import argparse
import ast
import functools
import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (
    "run_backend",
    "run_frontend",
    "run_frontend_browser",
    "run_shared",
    "run_mobile",
    "run_android",
    "run_dependencies",
    "run_production_contract",
    "run_scalability",
    "run_multi_replica",
)
DOMAIN_TESTS = {
    "workouts": (
        "workouts",
        "workout_cycles",
        "workout_reviews",
        "training_templates",
        "exercises",
        "athlete_state",
        "program_timeline",
        "program_conversations",
    ),
    "workout_cycles": (
        "workouts",
        "workout_cycles",
        "workout_reviews",
        "program_timeline",
    ),
    "workout_reviews": (
        "workouts",
        "workout_cycles",
        "workout_reviews",
        "program_conversations",
    ),
    "nutrition": (
        "nutrition",
        "athlete_state",
        "program_timeline",
        "program_conversations",
    ),
    "exercises": ("exercises", "workouts", "training_templates"),
    "training_templates": ("training_templates", "workouts", "exercises"),
    "profile": ("profile", "athlete_state", "workouts", "nutrition"),
    "athlete_state": ("athlete_state", "profile", "workouts", "nutrition"),
    "program_timeline": ("program_timeline", "workouts", "workout_cycles", "nutrition"),
    "program_conversations": (
        "program_conversations",
        "workout_reviews",
        "workouts",
        "nutrition",
    ),
}
CRITICAL_TESTS = (
    "tests/entitlements",
    "tests/auth",
    "tests/errors",
    "tests/test_health.py",
    "tests/test_openapi_mobile_contract.py",
    "tests/test_behavior_safety_regressions.py",
    "tests/test_time_context.py",
)
SAFE_CORE = {
    "formatters.ts",
    "iran-calendar.ts",
    "local-date.ts",
    "billingPresentation.ts",
    "body-ghost.ts",
    "body-ghost-editor.ts",
    "body-ghost-pose.ts",
    "body-ghost-scale.ts",
}


@functools.lru_cache(maxsize=8)
def worker_dependencies(root: Path) -> set[str]:
    """Static transitive imports, including relative and literal dynamic imports.

    Deleted files remain in the closure as module paths. Runtime/schema/config files
    and dynamic worker entry points are separately classified as high risk.
    """
    files = list((root / "backend/app").rglob("*.py"))
    modules = {}
    for path in files:
        relative = path.relative_to(root / "backend").with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        modules[".".join(parts)] = path
    pending = [
        "app.body_analysis.worker",
        "app.nutrition.food_photo_worker",
        "app.notifications.worker",
        "app.scheduler.worker",
    ]
    seen = set()
    result = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        result.add("backend/" + name.replace(".", "/") + ".py")
        path = modules.get(name)
        if path is None:
            continue
        result.add(path.relative_to(root).as_posix())
        tree = ast.parse(path.read_text(), filename=str(path))
        package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        for node in ast.walk(tree):
            imports = []
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    base = importlib.util.resolve_name("." * node.level + base, package)
                imports.append(base)
                imports.extend(base + "." + alias.name for alias in node.names)
            elif (
                isinstance(node, ast.Call)
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                if isinstance(node.args[0].value, str) and node.args[
                    0
                ].value.startswith("app."):
                    imports.append(node.args[0].value)
            for target in imports:
                if target.startswith("app.") and target != "app.main":
                    # Workers import main only to register ORM relationships at startup.
                    # API route registration is not a worker business-code dependency.
                    if target in modules:
                        pending.append(target)
                    else:
                        # Preserve deleted direct modules; symbols are harmless here.
                        result.add("backend/" + target.replace(".", "/") + ".py")
                    parts = target.split(".")
                    for index in range(1, len(parts)):
                        parent = ".".join(parts[:index])
                        if parent in modules and modules[parent].name == "__init__.py":
                            pending.append(parent)
    return result


def test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return ".test." in name or ".spec." in name or path.startswith("backend/tests/")


def classify(paths: list[str], root: Path = ROOT, *, force_full: bool = False) -> dict:
    paths = sorted(set(paths))
    workers = worker_dependencies(root)
    areas = set()
    domains = set()
    reasons = []
    shared = False
    migrations = False
    contracts = False
    infra = False
    deploy = set()
    for path in paths:
        parts = path.split("/")
        name = parts[-1]
        if (
            path.startswith(("docs/", "reports/"))
            and path.endswith((".md", ".txt"))
            or path in {"README.md", "CHANGELOG.md", "AGENTS.md"}
        ):
            continue
        if path.startswith("backend/alembic/"):
            migrations = True
        if (
            path.startswith("contracts/")
            or "/generated/" in path
            or name in {"models.py", "schemas.py", "openapi_export.py"}
        ):
            contracts = True
        if path.startswith((".github/", "ops/", "docker/")) or name.startswith(
            ("compose", "Caddyfile", "Dockerfile")
        ):
            infra = True
        safe = False
        if path.startswith(("frontend/src/", "frontend/public/", "frontend/e2e/")):
            areas.add("frontend")
            safe = (
                "/generated/" not in path
                and not name.endswith((".sh", ".conf"))
                and not (
                    not test_file(path)
                    and (
                        path in {"frontend/src/App.tsx", "frontend/src/main.tsx"}
                        or path.startswith(
                            ("frontend/src/api/", "frontend/src/lib/auth/")
                        )
                        or path.startswith("frontend/src/features/auth/")
                        and name
                        in {
                            "AuthContext.tsx",
                            "api.ts",
                            "ProtectedRoute.tsx",
                            "GoogleSignInButton.tsx",
                        }
                        or path.startswith(
                            (
                                "frontend/src/features/billing/",
                                "frontend/src/features/entitlements/",
                            )
                        )
                        and name.endswith(("api.ts", "Context.tsx", "Gate.tsx"))
                    )
                )
            )
            if not test_file(path) and not path.startswith("frontend/e2e/"):
                deploy.add("frontend")
        elif path.startswith("mobile/"):
            areas.add("mobile")
            safe = True  # Native-only inputs do not change VPS artifacts.
        elif path.startswith("packages/fitician-core/src/"):
            shared = True
            areas.update(("frontend", "mobile"))
            safe = (
                name in SAFE_CORE
                or test_file(path)
                or path.startswith("packages/fitician-core/src/i18n/")
            )
            if not test_file(path):
                deploy.add("frontend")
        elif (
            len(parts) >= 4
            and parts[:2] == ["backend", "app"]
            and parts[2] in DOMAIN_TESTS
        ):
            domain = parts[2]
            domains.add(domain)
            areas.add("backend")
            deploy.add("backend")
            safe = (
                path.endswith(".py")
                and path not in workers
                and name
                not in {
                    "models.py",
                    "schemas.py",
                    "router.py",
                    "dependencies.py",
                    "security.py",
                    "__init__.py",
                    "enums.py",
                }
                and not any(
                    word in name
                    for word in (
                        "worker",
                        "scheduler",
                        "migration",
                        "payment",
                        "provider",
                        "retention",
                    )
                )
            )
        elif path.startswith("backend/tests/"):
            areas.add("backend")
            domain = parts[2] if len(parts) > 3 else ""
            safe = domain in DOMAIN_TESTS
            if safe:
                domains.add(domain)
        if not safe:
            reasons.append(path)
    full = force_full or bool(reasons) or not paths
    plan = {key: full for key in SCOPES}
    if not full:
        plan.update(
            run_backend="backend" in areas,
            run_frontend="frontend" in areas,
            run_frontend_browser=False,
            run_shared=shared or "backend" in areas,
            run_mobile="mobile" in areas,
        )
    if not full:
        plan["run_dependencies"] = any(
            path.startswith("mobile/")
            and path.rsplit("/", 1)[-1]
            in {"package.json", "package-lock.json", "npm-shrinkwrap.json", ".npmrc"}
            for path in paths
        )
        plan["run_android"] = any(
            path.startswith(("mobile/android/", "mobile/plugins/", "mobile/modules/"))
            or path
            in {
                "mobile/package.json",
                "mobile/package-lock.json",
                "mobile/eas.json",
                "mobile/app.json",
            }
            or path.startswith(
                ("mobile/app.config.", "mobile/metro.config.", "mobile/babel.config.")
            )
            for path in paths
        )
    path_kind = (
        "full"
        if full
        else (
            "docs" if not areas else next(iter(areas)) if len(areas) == 1 else "medium"
        )
    )
    suites = set(CRITICAL_TESTS)
    for domain in domains:
        suites.update("tests/" + suite for suite in DOMAIN_TESTS[domain])
    plan.update(
        path=path_kind,
        frontend_only=path_kind == "frontend",
        backend_only=path_kind == "backend",
        mobile_only=path_kind == "mobile",
        full_ci_required=full,
        shared_changed=shared,
        contracts_changed=contracts,
        migration_changed=migrations,
        infra_changed=infra,
        deploy_frontend=full or "frontend" in deploy,
        deploy_backend=full or "backend" in deploy,
        deploy_agent=full,
        deployable=full or bool(deploy),
        backend_domains=sorted(domains),
        backend_tests=sorted(suites),
        changed_paths=paths,
        full_reasons=sorted(reasons),
    )
    return plan


def frontend_release_paths(paths: list[str]) -> bool:
    """Deployment scope only: these paths still require the complete Full CI gates."""
    allowed = {
        ".dockerignore",
        ".gitignore",
        "package-lock.json",
        "package.json",
        ".github/workflows/public-seo.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/frontend-only.yml",
        ".github/workflows/backend-only.yml",
        ".github/workflows/deploy-component.yml",
        ".github/workflows/deploy-production.yml",
        "ops/ci-classify.py",
        "ops/ci-release-gate.py",
        "ops/check-component-release.py",
    }
    has_frontend = False
    for path in paths:
        if path.startswith("frontend/") and not Path(path).name.startswith(".env"):
            has_frontend = True
        elif path in allowed or path.startswith("ops/tests/") and path.endswith(".py"):
            continue
        elif path.startswith(("docs/", "reports/")) and path.endswith((".md", ".txt")):
            continue
        else:
            return False
    return has_frontend


def git_paths(base: str, head: str) -> list[str]:
    if not base or set(base) == {"0"}:
        command = ["git", "ls-tree", "-r", "--name-only", "-z", head]
    else:
        command = ["git", "diff", "--no-renames", "--name-only", "-z", base, head]
    raw = subprocess.check_output(command, cwd=ROOT)
    return [os.fsdecode(path) for path in raw.split(b"\0") if path]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default=os.environ.get("GITHUB_SHA", "HEAD"))
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = classify(
        git_paths(args.base, args.head) if not args.full else [], force_full=args.full
    )
    plan["base_sha"] = args.base
    plan["release_requested"] = os.environ.get(
        "EVENT_NAME", os.environ.get("GITHUB_EVENT_NAME")
    ) == "push" or (
        os.environ.get("EVENT_NAME", os.environ.get("GITHUB_EVENT_NAME"))
        == "workflow_dispatch"
        and os.environ.get("DISPATCH_MODE") == "release"
    )
    plan["sha"] = subprocess.check_output(
        ["git", "rev-parse", args.head], cwd=ROOT, text=True
    ).strip()
    print("Release classification:")
    for key, value in plan.items():
        print(f"{key}={json.dumps(value, separators=(',', ':'))}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, indent=2) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            for key, value in plan.items():
                rendered = (
                    value
                    if isinstance(value, str)
                    else json.dumps(value, separators=(",", ":"))
                )
                print(f"{key}={rendered}", file=stream)


if __name__ == "__main__":
    main()
