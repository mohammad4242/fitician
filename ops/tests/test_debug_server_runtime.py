import json
import os
import subprocess
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]


class DebugServerRuntimeTests(unittest.TestCase):
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
