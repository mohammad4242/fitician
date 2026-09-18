import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def service_block(compose: str, service: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(service)}:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:|\Z)",
        compose,
    )
    if match is None:
        raise AssertionError(f"missing service: {service}")
    return match.group("body")


class ShutdownContractTests(unittest.TestCase):
    def test_grace_periods_cover_provider_timeout_without_exceeding_queue_leases(self) -> None:
        for compose_name in ("compose.yaml", "compose.prod.yaml"):
            compose = (ROOT / compose_name).read_text()
            self.assertIn("stop_grace_period: 450s", service_block(compose, "body-analysis-worker"))
            self.assertIn("stop_grace_period: 450s", service_block(compose, "food-photo-worker"))
            self.assertIn("stop_grace_period: 30s", service_block(compose, "notification-worker"))
            self.assertIn("stop_grace_period: 60s", service_block(compose, "scheduler"))
            self.assertIn("stop_grace_period: 45s", service_block(compose, "backend"))


if __name__ == "__main__":
    unittest.main()
