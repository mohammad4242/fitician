import re
import subprocess
import unittest
from contextlib import suppress
from json import dumps
from os import environ, getpid
from pathlib import Path
from time import time

ROOT = Path(__file__).resolve().parents[2]
WORKERS = (
    "body-analysis-worker",
    "food-photo-worker",
    "notification-worker",
    "scheduler",
)


class WorkerHealthContractTests(unittest.TestCase):
    def test_local_and_production_workers_have_stale_heartbeat_healthchecks(self) -> None:
        for compose_name in ("compose.yaml", "compose.prod.yaml"):
            compose = (ROOT / compose_name).read_text()
            for service in WORKERS:
                match = re.search(
                    rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)",
                    compose,
                )
                self.assertIsNotNone(match)
                service_block = match.group("body") if match is not None else ""
                self.assertIn("JOB_HEARTBEAT_SERVICE", service_block)
                self.assertIn("sh", service_block)
                self.assertIn("/app/app/jobs/worker-healthcheck.sh", service_block)
                self.assertNotIn('test: ["CMD", "python"', service_block)
                self.assertIn("healthcheck:", service_block)
                self.assertIn("tmpfs:", service_block)
                if compose_name == "compose.prod.yaml":
                    self.assertIn("timeout: 3s", service_block)
                    self.assertIn("start_period: 15s", service_block)

    def test_worker_healthcheck_validates_fresh_matching_live_heartbeat(self) -> None:
        script = ROOT / "backend/app/jobs/worker-healthcheck.sh"
        work_dir = ROOT / "artifacts/test-worker-health"
        heartbeat = work_dir / "heartbeat.json"
        work_dir.mkdir(parents=True, exist_ok=True)
        heartbeat.write_text(
            dumps({"pid": getpid(), "service": "test-worker", "timestamp": time()}),
            encoding="utf-8",
        )
        environment = environ | {
            "JOB_HEARTBEAT_PATH": str(heartbeat),
            "JOB_HEARTBEAT_SERVICE": "test-worker",
            "JOB_HEARTBEAT_MAX_AGE_SECONDS": "20",
        }
        try:
            result = subprocess.run(
                ["sh", str(script)],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            environment["JOB_HEARTBEAT_SERVICE"] = "other-worker"
            result = subprocess.run(
                ["sh", str(script)],
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
        finally:
            with suppress(FileNotFoundError):
                heartbeat.unlink()
                work_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
