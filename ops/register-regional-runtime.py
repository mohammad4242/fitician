"""Adopt an already-running regional deployment after read-only proof."""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
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
ROLE_SOURCE_PROOF_VERSION = "iran-worker-role-source-v1"
WORKER_ENTRYPOINTS = {
    "backend/app/body_analysis/worker.py": "run_worker",
    "backend/app/nutrition/food_photo_worker.py": "run_worker",
    "backend/app/notifications/worker.py": "run_worker",
    "backend/app/scheduler/worker.py": "run_scheduler",
}
BACKEND_IMAGE_INPUTS = (
    "backend/Dockerfile",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/alembic.ini",
    "backend/.dockerignore",
    "backend/alembic",
    "backend/app",
)


def _role_ast(
    source: str, relative_path: str, expected_function: str, *, candidate: bool
) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise ValueError("Worker entrypoint source is invalid") from error
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == expected_function
    ]
    if len(functions) != 1:
        raise ValueError("Worker entrypoint function is missing or duplicated")
    function = functions[0]

    class Calls(ast.NodeVisitor):
        def __init__(self) -> None:
            self.main = 0
            self.bridge = 0

        def visit_Call(self, node: ast.Call) -> None:
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "import_module"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "app.main"
                and not node.keywords
            ):
                self.main += 1
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "install_diagnostic_log_bridge"
                and len(node.args) == 1
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "settings"
                and not node.keywords
            ):
                self.bridge += 1
            self.generic_visit(node)

    calls = Calls()
    for statement in function.body:
        calls.visit(statement)
    if calls.bridge != 1 or (
        calls.main != 1 if candidate else calls.main not in {0, 1}
    ):
        raise ValueError("Worker startup initialization is invalid")

    heartbeat_contexts = [
        node
        for node in ast.walk(function)
        if isinstance(node, (ast.With, ast.AsyncWith))
        and any(
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.context_expr.func, ast.Name)
            and item.context_expr.func.id in {"async_heartbeat", "threaded_heartbeat"}
            for item in node.items
        )
    ]
    if len(heartbeat_contexts) != 1:
        raise ValueError("Worker heartbeat context is missing or ambiguous")
    heartbeat_body = heartbeat_contexts[0].body

    def startup_call(statement: ast.stmt, name: str) -> bool:
        return (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Name)
            and statement.value.func.id == name
            and (
                name != "import_module"
                or (
                    len(statement.value.args) == 1
                    and isinstance(statement.value.args[0], ast.Constant)
                    and statement.value.args[0].value == "app.main"
                    and not statement.value.keywords
                )
            )
            and (
                name != "install_diagnostic_log_bridge"
                or (
                    len(statement.value.args) == 1
                    and isinstance(statement.value.args[0], ast.Name)
                    and statement.value.args[0].id == "settings"
                    and not statement.value.keywords
                )
            )
        )

    bridge_indexes = [
        index
        for index, statement in enumerate(heartbeat_body)
        if startup_call(statement, "install_diagnostic_log_bridge")
    ]
    main_indexes = [
        index
        for index, statement in enumerate(heartbeat_body)
        if startup_call(statement, "import_module")
    ]
    if len(bridge_indexes) != 1 or len(main_indexes) != calls.main:
        raise ValueError("Worker startup calls must be direct heartbeat statements")
    if candidate:
        if main_indexes[0] + 1 != bridge_indexes[0]:
            raise ValueError("Worker app import must immediately precede log setup")
    elif main_indexes and abs(main_indexes[0] - bridge_indexes[0]) != 1:
        raise ValueError("Legacy worker startup calls must remain in heartbeat context")

    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "importlib"
        and len(node.names) == 1
        and node.names[0].name == "import_module"
        and node.names[0].asname is None
    ]
    if len(imports) != (1 if candidate or calls.main else 0):
        raise ValueError("Worker import_module dependency is invalid")
    tree.body = [node for node in tree.body if node not in imports]

    class RemoveStartupCalls(ast.NodeTransformer):
        def visit_Expr(self, node: ast.Expr):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if (
                    value.func.id == "import_module"
                    and len(value.args) == 1
                    and isinstance(value.args[0], ast.Constant)
                    and value.args[0].value == "app.main"
                    and not value.keywords
                ):
                    return None
                if (
                    value.func.id == "install_diagnostic_log_bridge"
                    and len(value.args) == 1
                    and isinstance(value.args[0], ast.Name)
                    and value.args[0].id == "settings"
                    and not value.keywords
                ):
                    return None
            if (
                isinstance(value, ast.Constant)
                and value.value
                == "Run all periodic loops in one independently deployable process."
            ):
                return None
            return self.generic_visit(node)

    remover = RemoveStartupCalls()
    function.body = [
        transformed
        for statement in function.body
        if (transformed := remover.visit(statement)) is not None
    ]
    return ast.dump(tree, include_attributes=False)


def validate_role_source_compatibility(
    api_sha: str, worker_sha: str, *, root: Path = ROOT
) -> dict:
    """Prove that a newer worker image changes only safe worker startup imports."""
    if not SHA_RE.fullmatch(api_sha) or not SHA_RE.fullmatch(worker_sha):
        raise ValueError("Runtime role SHA is invalid")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", api_sha, worker_sha],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode:
        raise ValueError("API source SHA is not an ancestor of worker source SHA")
    raw = subprocess.check_output(
        [
            "git",
            "diff",
            "--no-renames",
            "--name-only",
            "-z",
            api_sha,
            worker_sha,
            "--",
            *BACKEND_IMAGE_INPUTS,
        ],
        cwd=root,
    )
    changed = sorted(os.fsdecode(path) for path in raw.split(b"\0") if path)
    if set(changed) - set(WORKER_ENTRYPOINTS):
        raise ValueError("Backend image inputs differ outside worker entrypoints")
    for relative, function in WORKER_ENTRYPOINTS.items():
        try:
            old = subprocess.check_output(
                ["git", "show", f"{api_sha}:{relative}"], cwd=root, text=True
            )
            new = subprocess.check_output(
                ["git", "show", f"{worker_sha}:{relative}"], cwd=root, text=True
            )
        except subprocess.SubprocessError as error:
            raise ValueError(
                "Worker source is unavailable for compatibility proof"
            ) from error
        if _role_ast(old, relative, function, candidate=False) != _role_ast(
            new, relative, function, candidate=True
        ):
            raise ValueError("Worker behavior differs outside startup initialization")
    return {
        "version": ROLE_SOURCE_PROOF_VERSION,
        "api_sha": api_sha,
        "worker_sha": worker_sha,
        "ancestor_verified": True,
        "backend_image_inputs": changed,
        "entrypoint_ast_equivalent": True,
    }


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
    role_proof: dict | None,
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
        if role_proof is not None:
            encoded = base64.urlsafe_b64encode(
                json.dumps(role_proof, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            args.extend(["--role-proof-b64", encoded])
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
            role_proof=None,
            accepted_at="",
        )
        role_proof = None
        if region == "iran" and probe["api_sha"] != probe["worker_sha"]:
            role_proof = validate_role_source_compatibility(
                probe["api_sha"], probe["worker_sha"], root=ROOT
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
            "role_source_compatibility": role_proof,
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
                role_proof=role_proof,
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
