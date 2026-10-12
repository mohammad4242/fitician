"""Render the real regional contracts; never use application secrets."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RegionalTopologyTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.scratch.cleanup)
        self.env_file = Path(self.scratch.name) / ".env"
        self.env_file.write_text("")
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": os.environ["HOME"],
            "FITICIAN_ENV_FILE": str(self.env_file),
            "DOCKERHUB_USERNAME": "example",
            "IMAGE_TAG": "a" * 40,
            "POSTGRES_PASSWORD": "test-only",
            "REDIS_PASSWORD": "test-only",
            "DATABASE_URL": "postgresql+psycopg://fitician:test-only@db:5432/fitician",
            "FITICIAN_DOMAIN": "example.com",
            "AGENT_SERVICE_BASE_URL": "https://agent.example.ts.net",
            "AGENT_SERVICE_TOKEN": "test-only-token-that-is-more-than-32-characters",
            "POSTGRES_VOLUME_NAME": "test-pg",
            "REDIS_VOLUME_NAME": "test-redis",
            "CADDY_DATA_VOLUME_NAME": "test-caddy",
            "CADDY_CONFIG_VOLUME_NAME": "test-caddy-config",
            "AGENT_HOME_VOLUME_NAME": "existing-agent-home",
        }

    def render(self, region):
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(self.env_file),
                "-f",
                f"compose.prod.{region}.yaml",
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_iran_starts_without_local_agent_and_keeps_data_private(self):
        config = self.render("iran")
        services = config["services"]
        self.assertEqual(
            set(services),
            {
                "db",
                "redis",
                "backend",
                "backend-2",
                "migrations",
                "food-photo-worker",
                "body-analysis-worker",
                "notification-worker",
                "scheduler",
                "frontend",
                "caddy",
            },
        )
        for name, service in services.items():
            self.assertNotIn("agent-service", service.get("depends_on", {}), name)
            if name != "caddy":
                self.assertFalse(service.get("ports"), name)
            if name in {
                "backend",
                "backend-2",
                "food-photo-worker",
                "body-analysis-worker",
                "scheduler",
                "notification-worker",
            }:
                self.assertEqual(
                    service["environment"]["AGENT_SERVICE_BASE_URL"],
                    self.env["AGENT_SERVICE_BASE_URL"],
                )
        for volume in config["volumes"].values():
            self.assertTrue(volume["external"])
        self.assertEqual(int(services["db"]["mem_limit"]), 512 * 1024**2)
        for name in ("db", "redis", "caddy"):
            self.assertRegex(services[name]["image"], r"@sha256:[0-9a-f]{64}$")

    def test_germany_has_only_agent_and_existing_auth_volume(self):
        config = self.render("germany")
        self.assertEqual(set(config["services"]), {"agent-service"})
        agent = config["services"]["agent-service"]
        self.assertTrue(agent["init"])
        self.assertNotIn("env_file", agent)
        self.assertFalse(
            any(key.startswith(("S3_", "DATABASE_", "REDIS_")) for key in agent["environment"])
        )
        self.assertEqual(agent["ports"][0]["host_ip"], "127.0.0.1")
        self.assertEqual(agent["ports"][0]["published"], "9001")
        self.assertEqual(len(agent["volumes"]), 1)
        volume = config["volumes"]["fitician_agent_home"]
        self.assertTrue(volume["external"])
        self.assertEqual(volume["name"], "existing-agent-home")

    def test_regional_services_bound_disk_usage_from_container_logs(self):
        for region in ("iran", "germany"):
            for name, service in self.render(region)["services"].items():
                with self.subTest(region=region, service=name):
                    self.assertEqual(service.get("logging"), {
                        "driver": "json-file",
                        "options": {"max-size": "10m", "max-file": "3"},
                    })

    def test_capacity_uses_region_specific_rendered_limits(self):
        for region in ("iran", "germany"):
            result = subprocess.run(
                [
                    sys.executable,
                    "ops/check-runtime-capacity.py",
                    "--env-file",
                    str(self.env_file),
                    "--region",
                    region,
                    "--compose-file",
                    f"compose.prod.{region}.yaml",
                ],
                cwd=ROOT,
                env=self.env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["within_budget"])
            self.assertGreaterEqual(payload["memory_headroom_mib"], 750)
            if region == "iran":
                self.assertNotIn("agent-service", payload["services"])
                self.assertEqual(payload["replicas"], 2)
            else:
                self.assertEqual(set(payload["services"]), {"agent-service"})

    def test_capacity_rejects_wrong_host_topology(self):
        for region, filename in (
            ("iran", "compose.prod.yaml"),
            ("germany", "compose.prod.iran.yaml"),
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    "ops/check-runtime-capacity.py",
                    "--env-file",
                    str(self.env_file),
                    "--region",
                    region,
                    "--compose-file",
                    filename,
                ],
                cwd=ROOT,
                env=self.env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime capacity configuration invalid", result.stderr)

    def test_iran_over_budget_resources_fail_closed(self):
        result = subprocess.run(
            [
                sys.executable,
                "ops/check-runtime-capacity.py",
                "--env-file",
                str(self.env_file),
                "--region",
                "iran",
                "--compose-file",
                "compose.prod.iran.yaml",
            ],
            cwd=ROOT,
            env=self.env | {"BACKEND_MEMORY_LIMIT": "2g"},
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)["within_budget"])

    def test_database_budget_uses_rendered_pool_settings(self):
        for pool_size, expected_status, expected_connections in ((5, 0, 32), (20, 1, 62)):
            result = subprocess.run(
                [
                    sys.executable,
                    "ops/check-db-connection-budget.py",
                    "--compose-file",
                    "compose.prod.iran.yaml",
                    "--env-file",
                    str(self.env_file),
                ],
                cwd=ROOT,
                env=self.env | {"DB_POOL_SIZE": str(pool_size)},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, expected_status, result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["possible_connections"], expected_connections
            )

    def test_database_budget_rejects_missing_application_topology(self):
        result = subprocess.run(
            [
                sys.executable,
                "ops/check-db-connection-budget.py",
                "--compose-file",
                "compose.prod.germany.yaml",
                "--env-file",
                str(self.env_file),
            ],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid rendered database connection budget", result.stderr)

    def test_database_budget_reads_env_file_budget_and_rejects_unbounded_pool(self):
        for settings in ("DB_CONNECTION_BUDGET=30\n", "DB_MAX_OVERFLOW=-1\n"):
            self.env_file.write_text(settings)
            result = subprocess.run(
                [
                    sys.executable,
                    "ops/check-db-connection-budget.py",
                    "--compose-file",
                    "compose.prod.iran.yaml",
                    "--env-file",
                    str(self.env_file),
                ],
                cwd=ROOT,
                env=self.env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
