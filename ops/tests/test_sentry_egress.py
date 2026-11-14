import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "sentry_egress", Path(__file__).parents[1] / "sentry-egress.py"
)
module = importlib.util.module_from_spec(spec)


class SentryEgressTests(unittest.TestCase):
    def test_boot_recovery_retries_only_the_owned_proxy_after_private_network_start(
        self,
    ):
        from configparser import ConfigParser

        path = Path(__file__).parents[1] / "systemd/fitician-sentry-egress.service"
        self.assertTrue(path.is_file())
        unit = ConfigParser(interpolation=None)
        unit.read(path)
        self.assertIn("tailscaled.service", unit["Unit"]["After"])
        self.assertIn("docker.service", unit["Unit"]["After"])
        self.assertEqual(unit["Service"]["Restart"], "on-failure")
        self.assertEqual(
            unit["Service"]["ExecStart"],
            "/usr/bin/python3 /opt/fitician-agent/sentry-egress/supervision/recover.py",
        )
        self.assertNotIn("ExecStop", unit["Service"])
        self.assertEqual(unit["Service"]["RemainAfterExit"], "yes")

    def test_recovery_repairs_an_orphaned_owned_network_and_checks_the_listener(self):
        recovery_spec = importlib.util.spec_from_file_location(
            "recover", Path(__file__).parents[1] / "recover-sentry-egress.py"
        )
        self.assertTrue(Path(recovery_spec.origin).is_file())
        recovery = importlib.util.module_from_spec(recovery_spec)
        recovery_spec.loader.exec_module(recovery)
        container = {
            "Id": "owned-proxy-id",
            "Config": {
                "Labels": {"com.docker.compose.project": "fitician-sentry-egress"}
            },
            "HostConfig": {
                "NetworkMode": "fitician-sentry-egress_default",
                "ReadonlyRootfs": True,
                "PortBindings": {
                    "3128/tcp": [{"HostIp": "100.108.24.126", "HostPort": "3188"}]
                },
            },
            "State": {"Status": "running"},
            "NetworkSettings": {"Networks": {}, "Ports": {}},
        }
        calls = []

        def command(*args):
            calls.append(args)
            if args[:2] == ("docker", "inspect"):
                return json.dumps([container])
            if args[:3] == ("docker", "network", "inspect"):
                return json.dumps(
                    [
                        {
                            "Driver": "bridge",
                            "Labels": {
                                "com.docker.compose.project": "fitician-sentry-egress"
                            },
                        }
                    ]
                )
            if args[:3] == ("docker", "network", "connect"):
                container["NetworkSettings"] = {
                    "Networks": {"fitician-sentry-egress_default": {}},
                    "Ports": container["HostConfig"]["PortBindings"],
                }
                return ""
            self.fail("Unexpected mutation")

        class Listener:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def sendall(self, value):
                self.value = value

            def recv(self, limit):
                return b"HTTP/1.1 407 Proxy Authentication Required\r\n"

        result = recovery.recover(
            command=command, connect=lambda *args, **kw: Listener()
        )
        self.assertTrue(result["network_recovered"])
        self.assertTrue(result["listener_verified"])
        self.assertEqual(
            [c for c in calls if c[:3] == ("docker", "network", "connect")],
            [
                (
                    "docker",
                    "network",
                    "connect",
                    "fitician-sentry-egress_default",
                    "owned-proxy-id",
                )
            ],
        )
        calls.clear()
        self.assertFalse(
            recovery.recover(command=command, connect=lambda *a, **kw: Listener())[
                "network_recovered"
            ]
        )
        self.assertFalse(any(c[:3] == ("docker", "network", "connect") for c in calls))
        container["HostConfig"]["PortBindings"]["3128/tcp"][0]["HostIp"] = "0.0.0.0"
        with self.assertRaises(ValueError):
            recovery.recover(command=command, connect=lambda *a, **kw: Listener())

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
