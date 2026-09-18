from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class MonitoringContractTests(unittest.TestCase):
    def test_overlay_is_private_pinned_and_resource_bounded(self) -> None:
        overlay = (ROOT / "compose.observability.yaml").read_text()
        for service in ("prometheus:", "grafana:", "redis-exporter:"):
            self.assertIn(service, overlay)
        images = re.findall(r"^\s+image:\s+(.+)$", overlay, flags=re.MULTILINE)
        self.assertEqual(len(images), 3)
        self.assertTrue(all("@sha256:" in image for image in images))
        self.assertIn('127.0.0.1:${PROMETHEUS_PORT:-9090}:9090', overlay)
        self.assertIn('127.0.0.1:${GRAFANA_PORT:-3000}:3000', overlay)
        self.assertIn("mem_limit:", overlay)
        self.assertIn("cpus:", overlay)
        self.assertNotIn('"9090:9090"', overlay)
        self.assertNotIn('"3000:3000"', overlay)

    def test_prometheus_and_grafana_are_provisioned_without_secrets(self) -> None:
        prometheus = (ROOT / "ops/monitoring/prometheus.yml").read_text()
        alerts = (ROOT / "ops/monitoring/alerts.yml").read_text()
        datasource = (
            ROOT / "ops/monitoring/grafana/provisioning/datasources/prometheus.yml"
        ).read_text()
        dashboard = (
            ROOT / "ops/monitoring/grafana/provisioning/dashboards/provider.yml"
        ).read_text()
        self.assertIn("/metrics", prometheus)
        self.assertIn("fitician-backend", prometheus)
        self.assertIn("alert:", alerts)
        self.assertIn("http://prometheus:9090", datasource)
        self.assertIn("options:", dashboard)
        self.assertNotIn("PASSWORD", prometheus.upper())

    def test_environment_contract_mentions_private_monitoring_settings(self) -> None:
        env = (ROOT / ".env.example").read_text()
        for name in (
            "PROMETHEUS_PORT=",
            "PROMETHEUS_RETENTION=",
            "PROMETHEUS_RETENTION_SIZE=",
            "GRAFANA_PORT=",
            "GRAFANA_ADMIN_USER=",
            "GRAFANA_ADMIN_PASSWORD=",
        ):
            self.assertIn(name, env)


if __name__ == "__main__":
    unittest.main()

