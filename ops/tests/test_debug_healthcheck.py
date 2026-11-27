import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "backend/app/debugging/healthcheck.py"


class DebugHealthcheckTests(unittest.TestCase):
    def test_liveness_does_not_import_provider_packages_or_export_status_content(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            status = Path(folder) / "status.json"
            status.write_text(
                json.dumps({"heartbeat": time.time(), "token": "private-health-fixture"})
            )
            status.chmod(0o600)
            result = subprocess.run(
                [sys.executable, "-S", str(SCRIPT), "--status-file", str(status)],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            self.assertEqual(
                result.returncode, 0, "A fresh heartbeat must work without site packages"
            )
            self.assertEqual(result.stdout + result.stderr, "")

    def test_failed_runtime_reports_only_closed_container_health_facts(self):
        spec = importlib.util.spec_from_file_location(
            "runtime_smoke_health", ROOT / "ops/smoke-debug-runtime.py"
        )
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        raw = {
            "State": {
                "Running": False,
                "ExitCode": 137,
                "OOMKilled": True,
                "Error": "private-health-fixture",
                "Health": {
                    "Status": "unhealthy",
                    "FailingStreak": 3,
                    "Log": [{"ExitCode": -1, "Output": "private-health-fixture"}],
                },
            },
            "Config": {"Env": ["GITHUB_TOKEN=private-health-fixture"]},
        }
        output = io.StringIO()
        with (
            patch.object(helper, "inspect", return_value=raw),
            contextlib.redirect_stdout(output),
            self.assertRaisesRegex(RuntimeError, "isolated_runtime_liveness_failed"),
        ):
            helper.wait_healthy("owned-runtime")
        self.assertTrue(output.getvalue(), "Liveness failures need bounded diagnostic facts")
        packet = json.loads(output.getvalue())
        self.assertTrue(packet["runtime_health_failure"]["oom_killed"])
        self.assertEqual(packet["runtime_health_failure"]["exit_code"], 137)
        self.assertEqual(packet["runtime_health_failure"]["probe_exit_codes"], [-1])
        self.assertNotIn("private-health-fixture", output.getvalue())

    def test_liveness_rejects_stale_future_malformed_or_unsafe_status_files(self):
        self.assertTrue(SCRIPT.is_file(), "A standalone liveness probe is required")
        spec = importlib.util.spec_from_file_location("standalone_runtime_health", SCRIPT)
        health = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(health)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            status = Path(folder) / "status.json"
            self.assertFalse(health.healthy(status, now=100))
            for value in (
                {"heartbeat": 54},
                {"heartbeat": 101},
                {"heartbeat": True},
                {"heartbeat": float("nan")},
                {"heartbeat": "99"},
                [],
                {},
            ):
                status.write_text(json.dumps(value))
                status.chmod(0o600)
                self.assertFalse(health.healthy(status, now=100))
            status.write_text(json.dumps({"heartbeat": 99}))
            status.chmod(0o600)
            self.assertTrue(health.healthy(status, now=100))
            status.chmod(0o644)
            self.assertFalse(health.healthy(status, now=100))
            status.chmod(0o600)
            link = Path(folder) / "link.json"
            link.symlink_to(status)
            self.assertFalse(health.healthy(link, now=100))
            status.write_text("not-json")
            self.assertFalse(health.healthy(status, now=100))
            status.write_text(" " * 65537)
            self.assertFalse(health.healthy(status, now=100))

    def test_compose_uses_the_same_standalone_probe_for_both_isolated_services(self):
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
            env={
                **os.environ,
                "FITICIAN_DEBUG_RUNTIME_IMAGE": "sha256:" + "a" * 64,
                "FITICIAN_DEBUG_RUNTIME_ROOT": "/opt/fitician-debug-runtime",
            },
            capture_output=True,
            text=True,
            check=True,
        )
        services = json.loads(result.stdout)["services"]
        for name in ("connector", "automation"):
            self.assertEqual(
                services[name]["healthcheck"]["test"],
                ["CMD", "python", "-m", "app.debugging.healthcheck"],
            )


if __name__ == "__main__":
    unittest.main()
