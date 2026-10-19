"""Fail-closed checks for safe registration of an already-running regional stack."""

from __future__ import annotations

import copy
import importlib.util
import json
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
    app_ref = f"registry.example/fitician-backend:{SHA}"
    frontend_ref = f"registry.example/fitician-frontend:{OTHER_SHA}"
    base_refs = {
        "db": "postgres:18-alpine@sha256:db",
        "redis": "redis:8-alpine@sha256:redis",
        "backend": app_ref,
        "backend-2": app_ref,
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
        environment = (
            dict(critical)
            if service
            in {
                "backend",
                "backend-2",
                "scheduler",
                "food-photo-worker",
                "body-analysis-worker",
            }
            else {}
        )
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
        self.assertEqual(result["app_sha"], SHA)
        self.assertEqual(result["service_image_tags"]["backend-2"], SHA)
        self.assertIn("fitician_caddy-data", result["external_volumes"])
        self.assertNotIn("not-printed-token", json.dumps(result))

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


class ControllerDryRunTests(unittest.TestCase):
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

        def fake_ssh(alias, app_dir, *, apply, probe, evidence, accepted_at):
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
