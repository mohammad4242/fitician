import ast
import json
import os
import shlex
import subprocess
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]


class DebugServerRuntimeTests(unittest.TestCase):
    def test_runtime_packages_the_matching_code_mode_host(self):
        dockerfile = (ROOT / "docker/debug-runtime/Dockerfile").read_text()
        self.assertIn(
            "rust-v0.167.2/codex-code-mode-host-x86_64-unknown-linux-musl.tar.gz",
            dockerfile,
        )
        self.assertIn(
            "189475a654d82ca776e08dfef22734106d3e5b2cf21da6e84ec3d974d02c39a6",
            dockerfile,
        )
        self.assertIn(
            "COPY --from=codex /usr/local/bin/codex-code-mode-host /usr/local/bin/codex-code-mode-host",
            dockerfile,
        )

    def test_runtime_distribution_contains_transitive_enrolled_job_imports(self):
        dockerfile = (ROOT / "docker/debug-runtime/Dockerfile").read_text()
        modules = set()
        for line in dockerfile.replace("\\\n", " ").splitlines():
            if not line.startswith("COPY backend/app/"):
                continue
            for source in shlex.split(line)[1:-1]:
                if source.startswith("backend/app/debugging/") and source.endswith(".py"):
                    modules.add(Path(source).stem)
        pending = ["server_runtime", "automation_client"]
        visited = set()
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            self.assertIn(name, modules, f"Enrolled runtime job requires missing module: {name}")
            tree = ast.parse((ROOT / "backend/app/debugging" / (name + ".py")).read_text())
            pending.extend(
                node.module.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module
            )

    def test_automation_service_has_separate_private_configuration_and_bounded_resources(
        self,
    ):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "compose.debug-runtime.yaml",
                "--profile",
                "automation",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=dict(
                os.environ,
                FITICIAN_DEBUG_RUNTIME_IMAGE="sha256:" + "a" * 64,
                FITICIAN_DEBUG_RUNTIME_ROOT="/opt/fitician-debug-runtime",
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        service = json.loads(result.stdout)["services"]["automation"]
        self.assertEqual(
            service["entrypoint"], ["python", "-m", "app.debugging.automation_client"]
        )
        self.assertEqual(service["user"], "10001:10001")
        self.assertEqual(int(service["mem_limit"]), 192 * 1024**2)
        self.assertEqual(float(service["cpus"]), 0.1)
        self.assertTrue(service["read_only"])
        mounts = {m["target"]: m["source"] for m in service["volumes"]}
        self.assertEqual(
            mounts,
            {
                "/state": "/opt/fitician-debug-runtime/automation-state",
                "/run/fitician-automation": "/opt/fitician-debug-runtime/automation-private",
            },
        )
        self.assertFalse(service.get("ports"))

    def test_existing_required_ci_builds_and_exercises_the_exact_runtime_artifact(self):
        import re

        text = (ROOT / ".github/workflows/ci.yml").read_text()
        section = re.search(
            r"^  split-region-smoke:\n(.*?)(?=^  agent:)",
            text,
            re.MULTILINE | re.DOTALL,
        )[1]
        self.assertIn("docker/debug-runtime/Dockerfile", section)
        self.assertIn("APP_BUILD_SHA=${{ github.sha }}", section)
        self.assertIn("ops/smoke-debug-runtime.py", section)
        self.assertIn("fitician-debug-runtime-${{ github.sha }}", section)
        self.assertIn("sha256sum", section)
        self.assertIn("scope=fitician-debug-runtime", section)
        self.assertNotIn("production-germany", section)

    def test_runtime_compose_has_only_dedicated_state_and_no_generation_authority(self):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "compose.debug-runtime.yaml",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=dict(
                os.environ,
                FITICIAN_DEBUG_RUNTIME_IMAGE="sha256:" + "a" * 64,
                FITICIAN_DEBUG_RUNTIME_ROOT="/opt/fitician-debug-runtime",
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        service = json.loads(result.stdout)["services"]["connector"]
        self.assertEqual(service["user"], "10001:10001")
        self.assertTrue(service["read_only"])
        self.assertEqual(service["cap_drop"], ["ALL"])
        self.assertEqual(int(service["mem_limit"]), 512 * 1024**2)
        self.assertEqual(float(service["cpus"]), 0.25)
        self.assertEqual(service["pids_limit"], 96)
        self.assertFalse(service.get("ports"))
        self.assertNotIn("environment", service)
        self.assertEqual(set(service["networks"]), {"debug-runtime"})
        mounts = {m["target"]: m for m in service["volumes"]}
        self.assertEqual(set(mounts), {"/state", "/run/fitician-connector"})
        self.assertTrue(mounts["/run/fitician-connector"]["read_only"])
        self.assertTrue(
            all(
                m["source"].startswith("/opt/fitician-debug-runtime/")
                for m in mounts.values()
            )
        )

    def test_independent_dependency_lock_matches_the_application_lock(self):
        packages = {
            p["name"]: p
            for p in tomllib.loads((ROOT / "backend/uv.lock").read_text())["package"]
        }
        current = None
        for line in (
            (ROOT / "docker/debug-runtime/requirements.lock").read_text().splitlines()
        ):
            if not line.strip() or line.startswith("#"):
                continue
            if not line.startswith(" "):
                name, version = line.rstrip(" \\").split("==")
                current = packages[name]
                self.assertEqual(version, current["version"])
            else:
                self.assertIn(
                    line.strip().rstrip(" \\").removeprefix("--hash="),
                    {w["hash"] for w in current["wheels"]},
                )

    def test_runtime_build_has_an_allowlisted_context_and_no_authentication_source(
        self,
    ):
        dockerfile = (ROOT / "docker/debug-runtime/Dockerfile").read_text()
        self.assertIn("0.167.2", dockerfile)
        self.assertIn(
            "8246e846c550ea21197fcc4067bc270dca895e94ea42ed6a282e6f4e0125b15f",
            dockerfile,
        )
        self.assertIn("--require-hashes", dockerfile)
        self.assertNotIn("COPY . ", dockerfile)
        self.assertNotIn("agent-service/", dockerfile)
        self.assertNotIn("auth.json", dockerfile)
        self.assertEqual(
            (ROOT / "docker/debug-runtime/Dockerfile.dockerignore")
            .read_text()
            .splitlines()[0],
            "**",
        )

    def test_dockerfile_defines_lightweight_broker_target_and_default_connector_target(self):
        dockerfile = (ROOT / "docker/debug-runtime/Dockerfile").read_text()
        self.assertIn("AS runtime-deps", dockerfile)
        self.assertIn("AS broker", dockerfile)
        self.assertIn("AS connector", dockerfile)
        broker_section = dockerfile.split("AS broker\n", 1)[1].split("FROM runtime-deps AS connector", 1)[0]
        connector_section = dockerfile.split("FROM runtime-deps AS connector\n", 1)[1]
        self.assertNotIn("/usr/local/bin/codex", broker_section)
        self.assertNotIn("codex-code-mode-host", broker_section)
        self.assertNotIn("install --no-install-recommends -y git", broker_section)
        self.assertIn('ENTRYPOINT ["python", "-m", "app.debugging.automation_client"]', broker_section)
        self.assertIn("COPY --from=codex /usr/local/bin/codex", connector_section)
        self.assertIn('ENTRYPOINT ["python", "-m", "app.debugging.server_runtime"]', connector_section)

    def test_compose_supports_dedicated_broker_image_independently_of_connector(self):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                "compose.debug-runtime.yaml",
                "--profile",
                "automation",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=dict(
                os.environ,
                FITICIAN_DEBUG_RUNTIME_IMAGE="sha256:" + "a" * 64,
                FITICIAN_DEBUG_BROKER_IMAGE="sha256:" + "b" * 64,
                FITICIAN_DEBUG_RUNTIME_ROOT="/opt/fitician-debug-runtime",
            ),
            capture_output=True,
            text=True,
            check=True,
        )
        services = json.loads(result.stdout)["services"]
        self.assertEqual(services["connector"]["image"], "sha256:" + "a" * 64)
        self.assertEqual(services["automation"]["image"], "sha256:" + "b" * 64)
