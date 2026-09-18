from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github/workflows/ci.yml"


class ScalabilityContractTests(unittest.TestCase):
    def test_ci_has_fast_scalability_contract_job_before_image_publish(self) -> None:
        workflow = CI.read_text()
        self.assertIn("scalability-contract:", workflow)
        self.assertIn("compose.multi.yaml", workflow)
        self.assertIn("Caddyfile.multi", workflow)
        self.assertIn("python -m compileall", workflow)
        self.assertIn("python -m alembic heads", workflow)
        self.assertIn("uv run ruff check", workflow)
        self.assertIn("uv run mypy", workflow)
        contract_index = workflow.index("scalability-contract:")
        publish_index = workflow.index("container-images:")
        self.assertLess(contract_index, publish_index)
        publish_needs = workflow[publish_index :].split("runs-on:", 1)[0]
        self.assertIn("scalability-contract", publish_needs)

    def test_multi_replica_contract_keeps_backend_and_caddy_private(self) -> None:
        compose = (ROOT / "compose.multi.yaml").read_text()
        caddy = (ROOT / "Caddyfile.multi.yaml").read_text()

        self.assertIn("backend-2:", compose)
        self.assertIn('127.0.0.1:8080:80', compose)
        self.assertIn('127.0.0.1:8002:8000', compose)
        self.assertIn("ports: !override", compose)
        self.assertIn("backend:8000 backend-2:8000", caddy)
        self.assertIn("health_uri /readyz", caddy)

    def test_caddy_and_backend_healthchecks_use_readiness(self) -> None:
        for caddy_name in ("Caddyfile", "Caddyfile.multi.yaml"):
            caddy = (ROOT / caddy_name).read_text()
            self.assertNotIn("health_uri /healthz", caddy)
            self.assertIn("health_uri /readyz", caddy)

        for compose_name in ("compose.yaml", "compose.prod.yaml"):
            compose = (ROOT / compose_name).read_text()
            self.assertIn("http://127.0.0.1:8000/readyz", compose)


if __name__ == "__main__":
    unittest.main()
