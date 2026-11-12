import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sentry_egress", Path(__file__).parents[1] / "sentry-egress.py"
)
module = importlib.util.module_from_spec(spec)


class SentryEgressTests(unittest.TestCase):
    def test_rejects_arbitrary_destinations_and_requires_explicit_private_binding(self):
        spec.loader.exec_module(module)
        for host in [
            "example.com",
            "us.sentry.io.evil.invalid",
            "127.0.0.1",
            "us.sentry.io\nhttp_access allow all",
        ]:
            with self.assertRaises(ValueError):
                module.configuration([host])
        config = module.configuration(["us.sentry.io", "o123.ingest.us.sentry.io"])
        self.assertIn("http_access deny !CONNECT", config)
        self.assertIn("http_access deny !SSL_ports", config)
        self.assertIn("http_access deny !sentry_hosts", config)
        self.assertIn("proxy_auth REQUIRED", config)
        self.assertIn("http_access deny all", config)
        self.assertNotIn("ssl_bump", config)
        self.assertIn("access_log none", config)
