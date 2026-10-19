"""Fail-closed checks for safe registration of an already-running regional stack."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
import regional_runtime as runtime

CONTROLLER_SPEC = importlib.util.spec_from_file_location(
    "register_regional_runtime", ROOT / "ops" / "register-regional-runtime.py"
)
controller = importlib.util.module_from_spec(CONTROLLER_SPEC)
assert CONTROLLER_SPEC.loader is not None
CONTROLLER_SPEC.loader.exec_module(controller)

SHA = "f3646e547ebecdbdabc920ca999fba5927ebfc87"
OTHER_SHA = "d338a20a7d4a49c47ae0b5ab5bf4e462edd8fad5"
WORKER_SHA = "2c9bf5f733b0e874c6eb2fd74761602077c8b045"
API_SHA = SHA
NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)


def foundation_inputs(*, created_at: str | None = None):
    run_id = 39234244399
    run = {
        "id": run_id,
        "name": "Fitician local scalability checks",
        "path": ".github/workflows/load-test.yml",
        "status": "completed",
        "conclusion": "success",
        "head_sha": SHA,
        "head_branch": "main",
        "head_repository": {"full_name": "mohammad4242/fitician"},
        "created_at": created_at or (NOW - timedelta(hours=1)).isoformat(),
    }
    jobs = [
        {
            "name": "Local multi-replica load and failure drills",
            "conclusion": "success",
        }
    ]
    artifacts = [
        {
            "id": 9331,
            "name": f"fitician-scalability-{run_id}",
            "expired": False,
            "size_in_bytes": 123456,
        }
    ]
    return run, jobs, artifacts


def make_iran_snapshot(root: Path):
    releases = root / "releases"
    contract_path = releases / SHA / "compose.prod.iran.yaml"
    older_path = releases / OTHER_SHA / "compose.prod.iran.yaml"
    contract_path.parent.mkdir(parents=True)
    older_path.parent.mkdir(parents=True)
    contract_path.write_text("services: {}\n")
    older_path.write_text("services: {}\n")
    app_ref = f"registry.example/fitician-backend:{WORKER_SHA}"
    api_ref = f"registry.example/fitician-backend:{API_SHA}"
    frontend_ref = f"registry.example/fitician-frontend:{OTHER_SHA}"
    base_refs = {
        "db": "postgres:18-alpine@sha256:db",
        "redis": "redis:8-alpine@sha256:redis",
        "backend": api_ref,
        "backend-2": api_ref,
        "scheduler": app_ref,
        "food-photo-worker": app_ref,
        "body-analysis-worker": app_ref,
        "notification-worker": app_ref,
        "frontend": frontend_ref,
        "caddy": "caddy:2-alpine@sha256:caddy",
    }
    critical = {
        "DATABASE_URL": "postgresql://user:secret@db/fitician",
        "AGENT_SERVICE_BASE_URL": "https://agent.tailnet.example",
        "AGENT_SERVICE_TOKEN": "not-printed-token",
        "APP_ENV": "production",
        "REDIS_HOST": "redis",
        "REDIS_PASSWORD": "not-printed-password",
    }
    volume_specs = {
        "db": [("postgres", "/var/lib/postgresql")],
        "redis": [("redis", "/data")],
        "caddy": [("caddy-data", "/data"), ("caddy-config", "/config")],
    }
    volumes = {
        name: {"name": f"fitician_{name}", "external": True}
        for specs in volume_specs.values()
        for name, _ in specs
    }
    services = {}
    containers = []
    images = {}
    volume_details = {}
    ids = {}
    image_ids_by_ref = {}
    old_path = str(older_path)
    for index, service in enumerate(runtime.IRAN_SERVICES):
        ref = base_refs[service]
        image_id = image_ids_by_ref.setdefault(ref, f"sha256:image-{service}")
        ids[service] = image_id
        images[ref] = {"Id": image_id}
        if service in {"backend", "backend-2"}:
            environment = dict(critical)
        elif service in {"scheduler", "food-photo-worker", "body-analysis-worker"}:
            environment = {
                key: value for key, value in critical.items() if key != "REDIS_HOST"
            }
        else:
            environment = {}
        if service in {"backend", "backend-2"}:
            environment["FITICIAN_DOMAIN"] = "fitician.fit"
        mounts = []
        declared_volumes = []
        for source, target in volume_specs.get(service, []):
            name = f"fitician_{source}"
            mounts.append({"Type": "volume", "Name": name, "Destination": target})
            declared_volumes.append(
                {"type": "volume", "source": source, "target": target}
            )
            volume_details[name] = {"Name": name}
        contract_for_service = (
            old_path if service == "backend-2" else str(contract_path)
        )
        container = {
            "Id": f"container-{service}",
            "Image": image_id,
            "Config": {
                "Image": ref,
                "Env": [f"{key}={value}" for key, value in environment.items()],
                "Labels": {
                    runtime.LABEL_PROJECT: "fitician-iran",
                    runtime.LABEL_SERVICE: service,
                    runtime.LABEL_CONFIGS: contract_for_service,
                },
            },
            "State": {"Status": "running", "Health": {"Status": "healthy"}},
            "Mounts": mounts,
            "HostConfig": {},
        }
        if service == "caddy":
            container["HostConfig"]["PortBindings"] = {
                "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "80"}],
                "443/tcp": [{"HostIp": "0.0.0.0", "HostPort": "443"}],
            }
        containers.append(container)
        services[service] = {
            "image": ref,
            "environment": environment,
            "healthcheck": {"test": ["CMD", "health"]},
            "volumes": declared_volumes,
        }
    rendered = {"services": services, "volumes": volumes}
    checks = {
        "api_statuses": {
            "backend": {"livez": 200, "readyz": 200},
            "backend-2": {"livez": 200, "readyz": 200},
        },
        "schema_revision": "20261018_175",
        "alembic_head": "20261018_175",
        "origin_status": 200,
        "agent_capabilities": True,
        "domain": "https://fitician.fit",
        "worker_mappers": {name: True for name in runtime.WORKER_MODULES},
    }
    return contract_path, containers, rendered, images, volume_details, checks


def make_germany_snapshot(root: Path):
    contract = root / "releases" / OTHER_SHA / "compose.prod.germany.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text("services: {}\n")
    ref = f"registry.example/fitician-agent:{OTHER_SHA}"
    image_id = "sha256:agent-image"
    volume_name = "existing-agent-auth"
    container = {
        "Id": "container-agent",
        "Image": image_id,
        "Config": {
            "Image": ref,
            "Env": ["AGENT_SERVICE_TOKEN=not-printed-token"],
            "Healthcheck": {
                "Test": ["CMD-SHELL", "curl -fsS http://127.0.0.1:9001/healthz"],
                "Interval": 10_000_000_000,
                "Timeout": 5_000_000_000,
                "Retries": 10,
            },
            "Labels": {
                runtime.LABEL_PROJECT: "fitician-germany",
                runtime.LABEL_SERVICE: "agent-service",
                runtime.LABEL_CONFIGS: str(contract),
            },
        },
        "State": {"Status": "running", "Health": {"Status": "healthy"}},
        "Mounts": [
            {"Type": "volume", "Name": volume_name, "Destination": "/home/agent"}
        ],
        "HostConfig": {
            "Privileged": False,
            "CapAdd": None,
            "CapDrop": ["ALL"],
            "ReadonlyRootfs": True,
            "SecurityOpt": ["no-new-privileges:true"],
            "PidsLimit": 256,
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=256m"},
            "Memory": 469_762_048,
            "NanoCpus": 400_000_000,
            "RestartPolicy": {"Name": "unless-stopped"},
            "Init": True,
            "Devices": None,
            "DeviceRequests": None,
            "PortBindings": {"9001/tcp": [{"HostIp": "127.0.0.1", "HostPort": "9001"}]},
        },
    }
    rendered = {
        "services": {
            "agent-service": {
                "image": ref,
                "environment": {"AGENT_SERVICE_TOKEN": "not-printed-token"},
                "privileged": False,
                "cap_drop": ["ALL"],
                "read_only": True,
                "security_opt": ["no-new-privileges:true"],
                "pids_limit": 256,
                "tmpfs": ["/tmp:rw,noexec,nosuid,size=256m"],
                "mem_limit": "469762048",
                "cpus": 0.4,
                "restart": "unless-stopped",
                "init": True,
                "healthcheck": {
                    "test": ["CMD-SHELL", "curl -fsS http://127.0.0.1:9001/healthz"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 10,
                },
                "volumes": [
                    {"type": "volume", "source": "agent-home", "target": "/home/agent"}
                ],
            }
        },
        "volumes": {"agent-home": {"name": volume_name, "external": True}},
    }
    return (
        contract,
        [container],
        rendered,
        {ref: {"Id": image_id}},
        {volume_name: {"Name": volume_name}},
        {"agent_capabilities": True},
    )


class FoundationEvidenceTests(unittest.TestCase):
    def test_scalability_evidence_must_match_worker_role_sha(self):
        run, jobs, artifacts = foundation_inputs()
        run["head_sha"] = WORKER_SHA
        proof = controller.validate_foundation_evidence(
            run,
            jobs,
            artifacts,
            repository="mohammad4242/fitician",
            runtime_sha=WORKER_SHA,
            now=NOW,
        )
        self.assertEqual(proof["sha"], WORKER_SHA)
        with self.assertRaises(ValueError):
            controller.validate_foundation_evidence(
                run,
                jobs,
                artifacts,
                repository="mohammad4242/fitician",
                runtime_sha=API_SHA,
                now=NOW,
            )

    def test_requires_successful_same_repo_main_sha_job_and_real_artifact(self):
        run, jobs, artifacts = foundation_inputs()
        accepted = controller.validate_foundation_evidence(
            run,
            jobs,
            artifacts,
            repository="mohammad4242/fitician",
            runtime_sha=SHA,
            now=NOW,
        )
        self.assertEqual(accepted["run_id"], 39234244399)
        self.assertEqual(accepted["artifact"], "fitician-scalability-39234244399")
        self.assertNotIn("archive_download_url", accepted)
        self.assertNotIn("secret", json.dumps(accepted).lower())

    def test_rejects_failed_forged_mismatched_stale_or_artifactless_evidence(self):
        cases = []
        run, jobs, artifacts = foundation_inputs()
        for key, value in (
            ("conclusion", "failure"),
            ("head_branch", "feature/x"),
            ("head_sha", OTHER_SHA),
            ("name", "Fitician CI"),
            ("path", "other.yml"),
        ):
            changed = dict(run)
            changed[key] = value
            cases.append((changed, jobs, artifacts))
        cases.append(
            (
                run,
                [{"name": controller.SCALABILITY_JOB, "conclusion": "failure"}],
                artifacts,
            )
        )
        cases.append((run, jobs, []))
        expired = [dict(artifacts[0], expired=True)]
        cases.append((run, jobs, expired))
        old_run, _, _ = foundation_inputs(
            created_at=(NOW - timedelta(days=15)).isoformat()
        )
        cases.append((old_run, jobs, artifacts))
        for bad_run, bad_jobs, bad_artifacts in cases:
            with (
                self.subTest(run=bad_run, jobs=bad_jobs, artifacts=bad_artifacts),
                self.assertRaises(ValueError),
            ):
                controller.validate_foundation_evidence(
                    bad_run,
                    bad_jobs,
                    bad_artifacts,
                    repository="mohammad4242/fitician",
                    runtime_sha=SHA,
                    now=NOW,
                )


class RoleSourceCompatibilityTests(unittest.TestCase):
    def _compatibility_repo(self, mutation: str | None = None) -> tuple[Path, str, str]:
        root = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, root)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "test@example.invalid"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", "Test"], check=True
        )
        files = tuple(controller.WORKER_ENTRYPOINTS)
        for relative in files:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            tree = ast.parse((ROOT / relative).read_text())
            function = next(
                node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == controller.WORKER_ENTRYPOINTS[relative]
            )
            heartbeat = next(
                node
                for node in ast.walk(function)
                if isinstance(node, (ast.With, ast.AsyncWith))
                and any(
                    isinstance(item.context_expr, ast.Call)
                    and isinstance(item.context_expr.func, ast.Name)
                    and item.context_expr.func.id
                    in {"async_heartbeat", "threaded_heartbeat"}
                    for item in node.items
                )
            )
            bridge_statement = next(
                statement
                for statement in heartbeat.body
                if isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "install_diagnostic_log_bridge"
            )
            heartbeat.body.remove(bridge_statement)
            if relative == "backend/app/scheduler/worker.py":
                main_statement = next(
                    statement
                    for statement in heartbeat.body
                    if isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Call)
                    and isinstance(statement.value.func, ast.Name)
                    and statement.value.func.id == "import_module"
                )
                heartbeat.body.remove(main_statement)
                tree.body = [
                    node
                    for node in tree.body
                    if not (
                        isinstance(node, ast.ImportFrom)
                        and node.module == "importlib"
                        and any(alias.name == "import_module" for alias in node.names)
                    )
                ]
            configure_index = next(
                index
                for index, statement in enumerate(function.body)
                if isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "configure_structured_logging"
            )
            function.body.insert(configure_index + 1, bridge_statement)
            source = ast.unparse(tree) + "\n"
            destination.write_text(source)
        (root / "backend/pyproject.toml").write_text("[project]\nname='fitician'\n")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "api"], check=True)
        api = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        for relative in files:
            (root / relative).write_text((ROOT / relative).read_text())
        if mutation == "worker_once":
            path = root / "backend/app/body_analysis/worker.py"
            tree = ast.parse(path.read_text())
            target = next(
                node
                for node in tree.body
                if isinstance(node, ast.AsyncFunctionDef)
                and node.name == "run_body_analysis_once"
            )
            target.body.insert(1, ast.Assert(test=ast.Constant(value=True)))
            path.write_text(ast.unparse(tree) + "\n")
        elif mutation in {"import_outside_heartbeat", "reverse_startup_calls"}:
            path = root / "backend/app/body_analysis/worker.py"
            tree = ast.parse(path.read_text())
            target = next(
                node
                for node in tree.body
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_worker"
            )
            heartbeat = next(
                node
                for node in ast.walk(target)
                if isinstance(node, (ast.With, ast.AsyncWith))
                and any(
                    isinstance(item.context_expr, ast.Call)
                    and isinstance(item.context_expr.func, ast.Name)
                    and item.context_expr.func.id == "async_heartbeat"
                    for item in node.items
                )
            )
            main_statement = next(
                statement
                for statement in heartbeat.body
                if isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "import_module"
            )
            bridge_statement = next(
                statement
                for statement in heartbeat.body
                if isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "install_diagnostic_log_bridge"
            )
            heartbeat.body.remove(main_statement)
            heartbeat.body.remove(bridge_statement)
            if mutation == "import_outside_heartbeat":
                target.body.insert(target.body.index(heartbeat), main_statement)
                heartbeat.body.insert(0, bridge_statement)
            else:
                heartbeat.body[:0] = [bridge_statement, main_statement]
            path.write_text(ast.unparse(tree) + "\n")
        elif mutation == "dependency":
            (root / "backend/pyproject.toml").write_text(
                "[project]\nname='fitician'\nversion='2'\n"
            )
        elif mutation == "schema":
            path = root / "backend/alembic/versions/changed.py"
            path.parent.mkdir(parents=True)
            path.write_text("revision = 'changed'\n")
        elif mutation == "api":
            path = root / "backend/app/main.py"
            path.write_text("APP_SOURCE_CHANGED = True\n")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "worker"], check=True)
        worker = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        return root, api, worker

    def test_accepts_current_startup_only_worker_source(self):
        root, api, worker = self._compatibility_repo()
        proof = controller.validate_role_source_compatibility(api, worker, root=root)
        self.assertEqual(proof["api_sha"], api)
        self.assertEqual(proof["worker_sha"], worker)
        self.assertTrue(proof["ancestor_verified"])
        self.assertTrue(proof["entrypoint_ast_equivalent"])
        with self.assertRaises(ValueError):
            controller.validate_role_source_compatibility(worker, api, root=root)

    def test_rejects_run_once_dependency_schema_and_api_changes(self):
        for mutation in (
            "worker_once",
            "import_outside_heartbeat",
            "reverse_startup_calls",
            "dependency",
            "schema",
            "api",
        ):
            with self.subTest(mutation=mutation):
                root, api, worker = self._compatibility_repo(mutation)
                with self.assertRaises(ValueError):
                    controller.validate_role_source_compatibility(
                        api, worker, root=root
                    )


class RuntimeSnapshotTests(unittest.TestCase):
    def test_iran_accepts_compatible_selective_contract_labels(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
        ) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                app_dir
            )
            result = runtime.validate_runtime_snapshot(
                alias="iran",
                app_dir=app_dir,
                containers=containers,
                rendered=rendered,
                image_details=images,
                volume_details=volumes,
                live_checks=checks,
            )
        self.assertEqual(result["app_sha"], WORKER_SHA)
        self.assertEqual(result["api_sha"], API_SHA)
        self.assertEqual(result["worker_sha"], WORKER_SHA)
        self.assertEqual(
            result["role_versions"], {"api": API_SHA, "worker": WORKER_SHA}
        )
        self.assertEqual(result["service_image_tags"]["backend-2"], API_SHA)
        self.assertIn("fitician_caddy-data", result["external_volumes"])
        self.assertNotIn("scheduler.REDIS_HOST", result["critical_env_sha256"])
        self.assertNotIn("not-printed-token", json.dumps(result))

    def test_worker_redis_host_may_be_absent_from_contract_and_runtime(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                app_dir
            )
            result = runtime.validate_runtime_snapshot(
                alias="iran",
                app_dir=app_dir,
                containers=containers,
                rendered=rendered,
                image_details=images,
                volume_details=volumes,
                live_checks=checks,
            )
        self.assertNotIn("food-photo-worker.REDIS_HOST", result["critical_env_sha256"])

    def test_worker_redis_host_is_checked_when_contract_and_runtime_provide_it(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                app_dir
            )
            service = "scheduler"
            container = next(
                item
                for item in containers
                if item["Config"]["Labels"][runtime.LABEL_SERVICE] == service
            )
            rendered["services"][service]["environment"]["REDIS_HOST"] = "redis"
            container["Config"]["Env"].append("REDIS_HOST=redis")
            result = runtime.validate_runtime_snapshot(
                alias="iran",
                app_dir=app_dir,
                containers=containers,
                rendered=rendered,
                image_details=images,
                volume_details=volumes,
                live_checks=checks,
            )
        self.assertIn("scheduler.REDIS_HOST", result["critical_env_sha256"])

    def test_worker_redis_host_if_present_must_match_nonempty_contract(self):
        cases = (
            ("scheduler", "declared_missing"),
            ("scheduler", "unexpected_runtime"),
            ("scheduler", "empty"),
            ("backend", "declared_missing"),
        )
        for service, case in cases:
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory(dir=ROOT) as folder,
            ):
                app_dir = Path(folder)
                _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                    app_dir
                )
                container = next(
                    item
                    for item in containers
                    if item["Config"]["Labels"][runtime.LABEL_SERVICE] == service
                )
                if case == "declared_missing":
                    rendered["services"][service]["environment"]["REDIS_HOST"] = "redis"
                    if service == "backend":
                        container["Config"]["Env"].remove("REDIS_HOST=redis")
                elif case == "unexpected_runtime":
                    container["Config"]["Env"].append("REDIS_HOST=redis")
                else:
                    rendered["services"][service]["environment"]["REDIS_HOST"] = ""
                    container["Config"]["Env"].append("REDIS_HOST=")
                with self.assertRaisesRegex(
                    runtime.RegistrationError,
                    "critical runtime setting differs from its contract",
                ):
                    runtime.validate_runtime_snapshot(
                        alias="iran",
                        app_dir=app_dir,
                        containers=containers,
                        rendered=rendered,
                        image_details=images,
                        volume_details=volumes,
                        live_checks=checks,
                    )

    def test_iran_rejects_different_api_replicas_or_worker_shas(self):
        mutations = ("api", "worker")
        for role in mutations:
            with (
                self.subTest(role=role),
                tempfile.TemporaryDirectory(dir=ROOT) as folder,
            ):
                app_dir = Path(folder)
                _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                    app_dir
                )
                if role == "api":
                    containers[3]["Config"]["Image"] = rendered["services"][
                        "scheduler"
                    ]["image"]
                    containers[3]["Image"] = images[containers[3]["Config"]["Image"]][
                        "Id"
                    ]
                    rendered["services"]["backend-2"]["image"] = containers[3][
                        "Config"
                    ]["Image"]
                else:
                    containers[4]["Config"]["Image"] = rendered["services"]["backend"][
                        "image"
                    ]
                    containers[4]["Image"] = images[containers[4]["Config"]["Image"]][
                        "Id"
                    ]
                    rendered["services"]["scheduler"]["image"] = containers[4][
                        "Config"
                    ]["Image"]
                with self.assertRaises(runtime.RegistrationError):
                    runtime.validate_runtime_snapshot(
                        alias="iran",
                        app_dir=app_dir,
                        containers=containers,
                        rendered=rendered,
                        image_details=images,
                        volume_details=volumes,
                        live_checks=checks,
                    )

    def test_iran_accepts_only_known_worker_health_override(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                app_dir
            )
            override = (
                app_dir
                / "artifacts/request-tracing-20261018/worker-startup.override.yaml"
            )
            override.parent.mkdir(parents=True)
            override.write_text(
                "services:\n"
                "  body-analysis-worker:\n    healthcheck:\n      start_period: 120s\n"
                "  food-photo-worker:\n    healthcheck:\n      start_period: 120s\n"
                "  notification-worker:\n    healthcheck:\n      start_period: 120s\n"
                "  scheduler:\n    healthcheck:\n      start_period: 120s\n"
            )
            for service in runtime.WORKER_MODULES:
                rendered["services"][service]["healthcheck"]["start_period"] = "120s"
            notification = next(
                item
                for item in containers
                if item["Config"]["Labels"][runtime.LABEL_SERVICE]
                == "notification-worker"
            )
            notification["Config"]["Labels"][runtime.LABEL_CONFIGS] += f",{override}"
            result = runtime.validate_runtime_snapshot(
                alias="iran",
                app_dir=app_dir,
                containers=containers,
                rendered=rendered,
                image_details=images,
                volume_details=volumes,
                live_checks=checks,
            )
            self.assertEqual(
                result["historical_worker_override_sha256"],
                runtime.WORKER_OVERRIDE_SHA256,
            )
            override.write_text(override.read_text() + "# unexpected\n")
            with self.assertRaises(runtime.RegistrationError):
                runtime.validate_runtime_snapshot(
                    alias="iran",
                    app_dir=app_dir,
                    containers=containers,
                    rendered=rendered,
                    image_details=images,
                    volume_details=volumes,
                    live_checks=checks,
                )

    def test_iran_rejects_failed_mapper_probe(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                app_dir
            )
            checks["worker_mappers"]["scheduler"] = False
            with self.assertRaises(runtime.RegistrationError):
                runtime.validate_runtime_snapshot(
                    alias="iran",
                    app_dir=app_dir,
                    containers=containers,
                    rendered=rendered,
                    image_details=images,
                    volume_details=volumes,
                    live_checks=checks,
                )

    def test_iran_rejects_mixed_unhealthy_or_inconsistent_runtime(self):
        mutations = [
            lambda containers: containers[-1]["Config"]["Labels"].__setitem__(
                runtime.LABEL_PROJECT, "other"
            ),
            lambda containers: containers[2]["State"]["Health"].__setitem__(
                "Status", "unhealthy"
            ),
            lambda containers: containers[3]["Config"].__setitem__(
                "Image", f"registry.example/fitician-backend:{OTHER_SHA}"
            ),
            lambda containers: containers[2].__setitem__("Image", "sha256:wrong"),
            lambda containers: containers[0]["Mounts"][0].__setitem__(
                "Name", "wrong-data"
            ),
            lambda containers: containers[-1]["HostConfig"]["PortBindings"].pop(
                "443/tcp"
            ),
        ]
        for mutate in mutations:
            with tempfile.TemporaryDirectory(
                dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
            ) as folder:
                app_dir = Path(folder)
                _, containers, rendered, images, volumes, checks = make_iran_snapshot(
                    app_dir
                )
                mutate(containers)
                with (
                    self.subTest(mutate=mutate),
                    self.assertRaises(runtime.RegistrationError),
                ):
                    runtime.validate_runtime_snapshot(
                        alias="iran",
                        app_dir=app_dir,
                        containers=containers,
                        rendered=rendered,
                        image_details=images,
                        volume_details=volumes,
                        live_checks=checks,
                    )

    def test_germany_requires_existing_auth_volume_and_loopback_binding(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
        ) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_germany_snapshot(
                app_dir
            )
            result = runtime.validate_runtime_snapshot(
                alias="alman",
                app_dir=app_dir,
                containers=containers,
                rendered=rendered,
                image_details=images,
                volume_details=volumes,
                live_checks=checks,
            )
            self.assertEqual(result["app_sha"], OTHER_SHA)
            containers[0]["HostConfig"]["PortBindings"]["9001/tcp"][0]["HostIp"] = (
                "0.0.0.0"
            )
            with self.assertRaises(runtime.RegistrationError):
                runtime.validate_runtime_snapshot(
                    alias="alman",
                    app_dir=app_dir,
                    containers=containers,
                    rendered=rendered,
                    image_details=images,
                    volume_details=volumes,
                    live_checks=checks,
                )
            containers[0]["HostConfig"]["PortBindings"] = {
                "9001/tcp": [{"HostIp": "127.0.0.1", "HostPort": "9001"}],
                "9002/tcp": [{"HostIp": "0.0.0.0", "HostPort": "9002"}],
            }
            with self.assertRaises(runtime.RegistrationError):
                runtime.validate_runtime_snapshot(
                    alias="alman",
                    app_dir=app_dir,
                    containers=containers,
                    rendered=rendered,
                    image_details=images,
                    volume_details=volumes,
                    live_checks=checks,
                )

    def test_germany_rejects_unexpected_mounts_and_host_security_drift(self):
        mutations = [
            lambda c: c[0]["Mounts"].append(
                {"Type": "bind", "Name": "", "Destination": "/etc", "RW": True}
            ),
            lambda c: c[0]["HostConfig"].__setitem__("Privileged", True),
            lambda c: c[0]["HostConfig"].__setitem__("CapAdd", ["NET_ADMIN"]),
            lambda c: c[0]["HostConfig"].__setitem__("CapDrop", []),
            lambda c: c[0]["HostConfig"].__setitem__("ReadonlyRootfs", False),
            lambda c: c[0]["HostConfig"].__setitem__("SecurityOpt", []),
            lambda c: c[0]["HostConfig"].__setitem__("PidsLimit", 512),
            lambda c: c[0]["HostConfig"]["Tmpfs"].__setitem__("/var/tmp", "rw"),
            lambda c: c[0]["HostConfig"].__setitem__(
                "Devices", [{"PathOnHost": "/dev/kvm"}]
            ),
            lambda c: c[0]["HostConfig"].__setitem__("Memory", 0),
            lambda c: c[0]["HostConfig"].__setitem__("NanoCpus", 0),
            lambda c: c[0]["HostConfig"]["RestartPolicy"].__setitem__("Name", "always"),
            lambda c: c[0]["Config"]["Healthcheck"].__setitem__("Retries", 1),
            lambda c: c[0]["Mounts"][0].__setitem__("RW", False),
        ]
        for mutate in mutations:
            with (
                self.subTest(mutate=mutate),
                tempfile.TemporaryDirectory(dir=ROOT) as folder,
            ):
                app_dir = Path(folder)
                _, containers, rendered, images, volumes, checks = (
                    make_germany_snapshot(app_dir)
                )
                mutate(containers)
                with self.assertRaises(runtime.RegistrationError):
                    runtime.validate_runtime_snapshot(
                        alias="alman",
                        app_dir=app_dir,
                        containers=containers,
                        rendered=rendered,
                        image_details=images,
                        volume_details=volumes,
                        live_checks=checks,
                    )

    def test_rejects_unexpected_running_service_in_project(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, rendered, images, volumes, checks = make_germany_snapshot(
                app_dir
            )
            sidecar = copy.deepcopy(containers[0])
            sidecar["Id"] = "container-sidecar"
            sidecar["Config"]["Labels"][runtime.LABEL_SERVICE] = "unexpected-sidecar"
            containers.append(sidecar)
            with self.assertRaises(runtime.RegistrationError):
                runtime.validate_runtime_snapshot(
                    alias="alman",
                    app_dir=app_dir,
                    containers=containers,
                    rendered=rendered,
                    image_details=images,
                    volume_details=volumes,
                    live_checks=checks,
                )

    def test_germany_inspect_runs_capability_probe_before_validation(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _contract, containers, rendered, images, volumes, _ = make_germany_snapshot(
                app_dir
            )
            env_file = app_dir / ".env"
            env_file.write_text("DOCKERHUB_USERNAME=test\n")
            container = containers[0]

            def docker_json(args):
                if args[:1] == ["inspect"]:
                    return [container]
                if args[:2] == ["image", "inspect"]:
                    return [images[args[2]]]
                if args[:2] == ["volume", "inspect"]:
                    return [volumes[args[2]]]
                raise AssertionError(args)

            def run(args, **kwargs):
                if args[:2] == ["docker", "ps"]:
                    return json.dumps({"ID": "container-agent"})
                if args[:3] == ["docker", "compose", "-p"]:
                    return json.dumps(rendered)
                if args[:3] == ["docker", "exec", "container-agent"]:
                    return json.dumps({"ok": True})
                raise AssertionError(args)

            with (
                patch.object(runtime, "_docker_json", side_effect=docker_json),
                patch.object(runtime, "_run", side_effect=run) as run_mock,
            ):
                result = runtime.inspect_runtime(app_dir, "alman")
            self.assertTrue(result["live_checks"]["agent_capabilities"])
            self.assertTrue(
                any(
                    call.args[0][:3] == ["docker", "exec", "container-agent"]
                    for call in run_mock.call_args_list
                )
            )

    def test_inspect_does_not_filter_same_project_sidecars(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            _, containers, _, _, _, _ = make_germany_snapshot(app_dir)
            sidecar = copy.deepcopy(containers[0])
            sidecar["Id"] = "container-sidecar"
            sidecar["Config"]["Labels"][runtime.LABEL_SERVICE] = "unexpected-sidecar"
            (app_dir / ".env").write_text("DOCKERHUB_USERNAME=test\n")
            by_id = {"container-agent": containers[0], "container-sidecar": sidecar}

            def docker_json(args):
                if args[:1] == ["inspect"]:
                    return [by_id[args[1]]]
                raise AssertionError(args)

            def run(args, **kwargs):
                if args[:2] == ["docker", "ps"]:
                    return "\n".join(
                        json.dumps({"ID": container_id}) for container_id in by_id
                    )
                raise AssertionError(args)

            with (
                patch.object(runtime, "_docker_json", side_effect=docker_json),
                patch.object(runtime, "_run", side_effect=run),
                self.assertRaises(runtime.RegistrationError),
            ):
                runtime.inspect_runtime(app_dir, "alman")

    def test_rejects_unknown_alias_and_symlink_or_conflicting_markers(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
        ) as folder:
            app_dir = Path(folder)
            contract, *_ = make_iran_snapshot(app_dir)
            marker, _ = runtime.marker_paths(app_dir, "iran")
            marker.symlink_to(contract)
            with self.assertRaises(runtime.RegistrationError):
                runtime.read_active_contract_marker(app_dir, "iran", {str(contract)})
            marker.unlink()
            marker.write_text(
                str(app_dir / "releases" / OTHER_SHA / "compose.prod.iran.yaml")
            )
            with self.assertRaises(runtime.RegistrationError):
                runtime.read_active_contract_marker(app_dir, "iran", {str(contract)})
        with self.assertRaises(runtime.RegistrationError):
            runtime.validate_region("other")


class RuntimeProbeTimeoutTests(unittest.TestCase):
    def test_mapper_probe_uses_one_isolated_exact_image_per_shared_image_id(self):
        selected = [
            {
                "Id": service,
                "Image": "sha256:" + "a" * 64,
                "Config": {"Labels": {runtime.LABEL_SERVICE: service}},
            }
            for service in runtime.WORKER_MODULES
        ]
        success = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(
            runtime.subprocess, "run", side_effect=[success, success]
        ) as run:
            checks = runtime._probe_worker_mappers(selected)
        self.assertEqual(checks, {service: True for service in runtime.WORKER_MODULES})
        self.assertEqual(run.call_count, 2)
        probe, cleanup = (call.args[0] for call in run.call_args_list)
        self.assertEqual(probe[:2], ["docker", "run"])
        self.assertIn("sha256:" + "a" * 64, probe)
        self.assertIn("--network", probe)
        self.assertEqual(probe[probe.index("--network") + 1], "none")
        self.assertIn("--read-only", probe)
        self.assertIn("--cap-drop", probe)
        self.assertEqual(probe[probe.index("--cap-drop") + 1], "ALL")
        self.assertEqual(probe[probe.index("--memory") + 1], "256m")
        self.assertEqual(probe[probe.index("--cpus") + 1], "0.25")
        self.assertEqual(probe[probe.index("--pids-limit") + 1], "128")
        self.assertEqual(probe[probe.index("--env") + 1], "APP_ENV=test")
        env_values = [
            probe[index + 1] for index, arg in enumerate(probe[:-1]) if arg == "--env"
        ]
        self.assertEqual(
            env_values,
            ["APP_ENV=test", "DATABASE_URL=sqlite://", "TMPDIR=/app/var"],
        )
        self.assertFalse(any("SECRET" in arg or "PASSWORD" in arg for arg in probe))
        self.assertFalse(any(arg in {"--volume", "--mount", "-v"} for arg in probe))
        self.assertIn("--pull", probe)
        self.assertEqual(probe[probe.index("--pull") + 1], "never")
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 180)
        self.assertEqual(cleanup[:3], ["docker", "rm", "--force"])
        self.assertEqual(cleanup[3], probe[probe.index("--name") + 1])
        self.assertEqual(run.call_args_list[1].kwargs["timeout"], 30)

    def test_mapper_probes_coalesce_by_actual_image_id_and_remain_sequential(self):
        selected = [
            {
                "Id": service,
                "Image": f"sha256:{index // 2 + 1:064x}",
                "Config": {"Labels": {runtime.LABEL_SERVICE: service}},
            }
            for index, service in enumerate(runtime.WORKER_MODULES)
        ]
        success = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(runtime.subprocess, "run", side_effect=[success] * 4) as run:
            checks = runtime._probe_worker_mappers(selected)
        self.assertEqual(checks, {service: True for service in runtime.WORKER_MODULES})
        probes = [
            call.args[0] for call in run.call_args_list if call.args[0][1] == "run"
        ]
        self.assertEqual(len(probes), 2)
        self.assertEqual(
            [probe[probe.index("--entrypoint") + 2] for probe in probes],
            [f"sha256:{1:064x}", f"sha256:{2:064x}"],
        )
        for probe in probes:
            code = probe[-1]
            self.assertEqual(code.count("import_module('app.main')"), 1)
            for module in runtime.WORKER_MODULES.values():
                self.assertEqual(code.count(f"import_module({module!r})"), 1)
            self.assertEqual(code.count("configure_mappers()"), 1)

    def test_timed_out_mapper_probe_cleans_up_only_its_named_container(self):
        selected = [
            {
                "Id": service,
                "Image": "sha256:" + "b" * 64,
                "Config": {"Labels": {runtime.LABEL_SERVICE: service}},
            }
            for service in runtime.WORKER_MODULES
        ]
        timeout = subprocess.TimeoutExpired(["docker", "run"], 180)
        removed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with patch.object(
            runtime.subprocess, "run", side_effect=[timeout, removed]
        ) as run:
            checks = runtime._probe_worker_mappers(selected)
        self.assertEqual(checks, {service: False for service in runtime.WORKER_MODULES})
        probe = run.call_args_list[0].args[0]
        cleanup = run.call_args_list[1].args[0]
        self.assertEqual(
            cleanup, ["docker", "rm", "--force", probe[probe.index("--name") + 1]]
        )

    def test_worker_identity_health_or_restart_change_during_probe_fails_closed(self):
        before = {
            "Id": "worker-1",
            "Image": "sha256:" + "c" * 64,
            "RestartCount": 0,
            "State": {
                "Status": "running",
                "StartedAt": "2026-10-19T10:00:00Z",
                "Health": {"Status": "healthy"},
            },
            "Config": {"Labels": {runtime.LABEL_SERVICE: "scheduler"}},
        }
        mutations = (
            {**before, "Id": "replacement-worker"},
            {**before, "Image": "sha256:" + "d" * 64},
            {**before, "RestartCount": 1},
            {
                **before,
                "State": {**before["State"], "StartedAt": "2026-10-19T10:01:00Z"},
            },
            {
                **before,
                "State": {
                    **before["State"],
                    "Health": {"Status": "unhealthy"},
                },
            },
        )
        for changed in mutations:
            with (
                self.subTest(changed=changed),
                patch.object(runtime, "_docker_json", return_value=[changed]),
                self.assertRaisesRegex(
                    runtime.RegistrationError,
                    "Worker changed during isolated mapper qualification",
                ),
            ):
                runtime._verify_worker_containers_unchanged([before])

    def test_readonly_command_timeout_defaults_to_45_seconds_and_is_overridable(self):
        completed = subprocess.CompletedProcess([], 0, stdout="ok", stderr="")
        with patch.object(runtime.subprocess, "run", return_value=completed) as run:
            self.assertEqual(runtime._run(["docker", "ps"]), "ok")
            self.assertEqual(runtime._run(["docker", "exec"], timeout=180), "ok")
        self.assertEqual(
            [call.kwargs["timeout"] for call in run.call_args_list], [45, 180]
        )


class MarkerWriteTests(unittest.TestCase):
    def test_marker_creation_is_atomic_private_idempotent_and_conflict_safe(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
        ) as folder:
            target = Path(folder) / "marker"
            self.assertTrue(runtime._atomic_create(target, "safe\n"))
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertFalse(runtime._atomic_create(target, "safe\n"))
            with self.assertRaises(runtime.RegistrationError):
                runtime._atomic_create(target, "conflict\n")

    def test_marker_link_is_removed_if_directory_sync_fails(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            target = Path(folder) / "marker"
            with (
                patch.object(runtime.os, "fsync", side_effect=[None, OSError("sync")]),
                self.assertRaises(OSError),
            ):
                runtime._atomic_create(target, "safe\n")
            self.assertFalse(target.exists())

    def test_apply_rolls_back_partial_marker_registration(self):
        with tempfile.TemporaryDirectory(
            dir=ROOT / "artifacts" if (ROOT / "artifacts").is_dir() else ROOT
        ) as folder:
            app_dir = Path(folder)
            (app_dir / "releases" / SHA).mkdir(parents=True)
            contract = app_dir / "releases" / SHA / "compose.prod.iran.yaml"
            contract.write_text("services: {}\n")
            summary = {
                "region": "iran",
                "app_sha": SHA,
                "invariant_sha256": "a" * 64,
                "active_contract": None,
                "registration_contract": str(contract),
                "markers": {
                    "active_contract": "missing",
                    "scalability_acceptance": "missing",
                },
            }
            active, foundation = runtime.marker_paths(app_dir, "iran")
            evidence = {"sha": SHA, "run_id": 39234244399}
            original = runtime._atomic_create

            def fail_foundation(path: Path, content: str) -> bool:
                if path == foundation:
                    raise OSError("injected safe failure")
                return original(path, content)

            with (
                patch.object(runtime, "inspect_runtime", return_value=summary),
                patch.object(runtime, "_atomic_create", side_effect=fail_foundation),
                self.assertRaises(OSError),
            ):
                runtime.apply_registration(
                    app_dir=app_dir,
                    alias="iran",
                    expected_invariant_sha256="a" * 64,
                    evidence=evidence,
                    accepted_at="2026-10-19T12:00:00Z",
                )
            self.assertFalse(active.exists())
            self.assertFalse(foundation.exists())
            self.assertFalse(
                (app_dir / "backups" / "regional-runtime-registration").exists()
            )

    def test_mixed_role_apply_requires_and_records_matching_source_proof(self):
        source_root, api_sha, worker_sha = (
            RoleSourceCompatibilityTests._compatibility_repo(self)
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            app_dir = Path(folder)
            contract = app_dir / "releases" / worker_sha / "compose.prod.iran.yaml"
            contract.parent.mkdir(parents=True)
            contract.write_text("services: {}\n")
            _, foundation = runtime.marker_paths(app_dir, "iran")
            accepted_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            foundation.write_text(
                "foundation_version=1\n"
                f"image_tag={worker_sha}\n"
                "evidence_run_id=12345\n"
                f"accepted_at={accepted_at}\n"
            )
            current = {
                "region": "iran",
                "api_sha": api_sha,
                "worker_sha": worker_sha,
                "app_sha": worker_sha,
                "invariant_sha256": "b" * 64,
                "active_contract": None,
                "registration_contract": str(contract),
            }
            with (
                patch.object(runtime, "inspect_runtime", return_value=current),
                self.assertRaises(runtime.RegistrationError),
            ):
                runtime.apply_registration(
                    app_dir=app_dir,
                    alias="iran",
                    expected_invariant_sha256="b" * 64,
                    evidence=None,
                    accepted_at=accepted_at,
                )
            proof = controller.validate_role_source_compatibility(
                api_sha, worker_sha, root=source_root
            )
            with patch.object(runtime, "inspect_runtime", return_value=current):
                result = runtime.apply_registration(
                    app_dir=app_dir,
                    alias="iran",
                    expected_invariant_sha256="b" * 64,
                    evidence=None,
                    accepted_at=accepted_at,
                    role_proof=proof,
                )
            active, _ = runtime.marker_paths(app_dir, "iran")
            self.assertTrue(result["active_contract_created"])
            record = json.loads(
                Path(result["evidence_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(record["role_source_compatibility"], proof)
            self.assertTrue(active.is_file())


class ControllerDryRunTests(unittest.TestCase):
    def test_ssh_apply_transmits_exact_role_proof(self):
        proof = {
            "version": controller.ROLE_SOURCE_PROOF_VERSION,
            "api_sha": API_SHA,
            "worker_sha": WORKER_SHA,
            "ancestor_verified": True,
            "backend_image_inputs": sorted(controller.WORKER_ENTRYPOINTS),
            "entrypoint_ast_equivalent": True,
        }
        completed = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
        with patch.object(
            controller.subprocess, "run", return_value=completed
        ) as remote:
            controller._ssh(
                "iran",
                Path("/opt/fitician-iran"),
                apply=True,
                probe={"invariant_sha256": "a" * 64},
                evidence=None,
                role_proof=proof,
                accepted_at="2026-10-19T12:00:00Z",
            )
        args = remote.call_args.args[0]
        self.assertEqual(
            remote.call_args.kwargs["timeout"],
            controller.REMOTE_PROBE_TIMEOUT_SECONDS,
        )
        encoded = args[args.index("--role-proof-b64") + 1]
        self.assertEqual(
            json.loads(controller.base64.urlsafe_b64decode(encoded).decode()), proof
        )

    def test_default_mode_never_calls_remote_apply(self):
        calls = []
        result = {
            "region": "germany",
            "app_sha": OTHER_SHA,
            "markers": {
                "active_contract": "missing",
                "scalability_acceptance": "missing",
            },
        }

        def fake_ssh(
            alias, app_dir, *, apply, probe, evidence, role_proof, accepted_at
        ):
            calls.append(apply)
            return result

        with (
            patch.object(controller, "_ssh", side_effect=fake_ssh),
            patch.object(
                sys,
                "argv",
                [
                    str(ROOT / "ops/register-regional-runtime.py"),
                    "--region",
                    "alman",
                    "--app-dir",
                    "/opt/fitician",
                ],
            ),
            patch("builtins.print") as output,
        ):
            controller.main()
        self.assertEqual(calls, [False])
        rendered = json.loads(output.call_args.args[0])
        self.assertEqual(rendered["mode"], "dry-run")
        self.assertEqual(rendered["writes"], [])

    def test_controller_proves_and_forwards_mixed_roles_on_apply(self):
        calls = []
        runtime_probe = {
            "region": "iran",
            "app_sha": WORKER_SHA,
            "api_sha": API_SHA,
            "worker_sha": WORKER_SHA,
            "invariant_sha256": "c" * 64,
            "markers": {
                "active_contract": "present",
                "scalability_acceptance": "present",
            },
        }
        proof = {
            "api_sha": API_SHA,
            "worker_sha": WORKER_SHA,
            "entrypoint_ast_equivalent": True,
        }

        def fake_ssh(
            alias, app_dir, *, apply, probe=None, evidence, role_proof, accepted_at
        ):
            calls.append((apply, role_proof))
            return runtime_probe if not apply else {"registered": True}

        with (
            patch.object(controller, "_ssh", side_effect=fake_ssh),
            patch.object(
                controller, "validate_role_source_compatibility", return_value=proof
            ) as source_check,
            patch.object(
                sys,
                "argv",
                [
                    str(ROOT / "ops/register-regional-runtime.py"),
                    "--region",
                    "iran",
                    "--app-dir",
                    "/opt/fitician-iran",
                    "--apply",
                    "--owner-approved",
                ],
            ),
            patch("builtins.print") as output,
        ):
            controller.main()
        source_check.assert_called_once_with(API_SHA, WORKER_SHA, root=ROOT)
        self.assertEqual(calls, [(False, None), (True, proof)])
        rendered = json.loads(output.call_args.args[0])
        self.assertEqual(rendered["role_source_compatibility"], proof)

    def test_apply_requires_both_explicit_flags(self):
        with (
            patch.object(
                sys,
                "argv",
                [
                    str(ROOT / "ops/register-regional-runtime.py"),
                    "--region",
                    "alman",
                    "--app-dir",
                    "/opt/fitician",
                    "--apply",
                ],
            ),
            self.assertRaises(SystemExit) as error,
        ):
            controller.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
