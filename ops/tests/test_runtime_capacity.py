from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/check-runtime-capacity.py"


class RuntimeCapacityTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_default_two_replica_topology_keeps_750_mib_headroom(self) -> None:
        result = self._run("--replicas", "2")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertGreaterEqual(payload["memory_headroom_mib"], 750)
        self.assertEqual(payload["replicas"], 2)
        self.assertTrue(payload["within_budget"])

    def test_third_backend_replica_exceeds_the_4_gib_budget(self) -> None:
        result = self._run("--replicas", "3")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime capacity exceeded", result.stderr)

    def test_monitoring_overlay_is_not_counted_in_normal_topology(self) -> None:
        normal = self._run()
        monitored = self._run("--include-monitoring")

        self.assertEqual(normal.returncode, 0, normal.stderr)
        self.assertNotEqual(monitored.returncode, 0)
        self.assertGreater(
            json.loads(monitored.stdout)["memory_limit_total_mib"],
            json.loads(normal.stdout)["memory_limit_total_mib"],
        )

    def test_production_compose_exposes_configurable_service_limits(self) -> None:
        compose = (ROOT / "compose.prod.yaml").read_text()
        for variable in (
            "POSTGRES_MEMORY_LIMIT",
            "REDIS_MEMORY_LIMIT",
            "AGENT_MEMORY_LIMIT",
            "BACKEND_MEMORY_LIMIT",
            "BODY_ANALYSIS_WORKER_MEMORY_LIMIT",
            "FOOD_PHOTO_WORKER_MEMORY_LIMIT",
            "NOTIFICATION_WORKER_MEMORY_LIMIT",
            "SCHEDULER_MEMORY_LIMIT",
            "FRONTEND_MEMORY_LIMIT",
            "CADDY_MEMORY_LIMIT",
        ):
            self.assertIn(variable, compose)

    def test_preflight_defaults_match_rendered_production_compose(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "DOCKERHUB_USERNAME": "example",
                "IMAGE_TAG": "0" * 40,
                "POSTGRES_PASSWORD": "placeholder",
                "DATABASE_URL": "postgresql+psycopg://fitician:placeholder@db:5432/fitician",
                "AGENT_SERVICE_TOKEN": "placeholder",
                "REDIS_PASSWORD": "placeholder",
                "FITICIAN_DOMAIN": "example.com",
            }
        )
        rendered = subprocess.run(
            ["docker", "compose", "-f", "compose.prod.yaml", "config", "--format", "json"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        services = json.loads(rendered.stdout)["services"]
        memory_mib = sum(
            int(config["mem_limit"]) // (1024 * 1024)
            for name, config in services.items()
            if name != "migrations"
        )
        cpus = sum(
            float(config["cpus"]) for name, config in services.items() if name != "migrations"
        )
        preflight = self._run()
        payload = json.loads(preflight.stdout)

        self.assertEqual(memory_mib, payload["memory_limit_total_mib"])
        self.assertAlmostEqual(cpus, payload["cpu_limit_total"])

    def test_preflight_reads_non_default_limits_from_rendered_compose(self) -> None:
        environment = os.environ.copy()
        environment.update(
            {
                "DOCKERHUB_USERNAME": "example",
                "IMAGE_TAG": "0" * 40,
                "POSTGRES_PASSWORD": "placeholder",
                "DATABASE_URL": "postgresql+psycopg://fitician:placeholder@db:5432/fitician",
                "AGENT_SERVICE_TOKEN": "placeholder",
                "REDIS_PASSWORD": "placeholder",
                "FITICIAN_DOMAIN": "example.com",
                "BACKEND_MEMORY_LIMIT": "100m",
                "BACKEND_CPU_LIMIT": "0.05",
            }
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--replicas", "2", "--compose-file", "compose.prod.yaml"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["services"]["backend"]["memory_mib_each"], 100)
        self.assertEqual(payload["services"]["backend"]["cpus_each"], 0.05)


if __name__ == "__main__":
    unittest.main()
