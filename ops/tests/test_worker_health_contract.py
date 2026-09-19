import re
import unittest
from pathlib import Path

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
                self.assertIn("python", service_block)
                self.assertIn("app.jobs.heartbeat", service_block)
                self.assertIn("healthcheck:", service_block)
                self.assertIn("tmpfs:", service_block)
                if compose_name == "compose.prod.yaml":
                    self.assertIn("timeout: 10s", service_block)


if __name__ == "__main__":
    unittest.main()
