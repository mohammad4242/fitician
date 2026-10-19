"""Rolling API deployment must keep a healthy peer and restore proxy routing."""

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "rolling_backend", Path(__file__).resolve().parents[1] / "rolling-backend.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
BASE = {
    "apps": {
        "http": {
            "servers": {
                "public": {
                    "routes": [
                        {
                            "handle": [
                                {
                                    "handler": "reverse_proxy",
                                    "upstreams": [
                                        {"dial": "backend:8000"},
                                        {"dial": "backend-2:8000"},
                                    ],
                                    "health_checks": {"active": {"uri": "/readyz"}},
                                }
                            ]
                        },
                        {
                            "handle": [
                                {
                                    "handler": "reverse_proxy",
                                    "upstreams": [{"dial": "frontend:80"}],
                                }
                            ]
                        },
                    ]
                }
            }
        }
    }
}


class FakeRuntime:
    def __init__(self, fail=()):
        self.config = deepcopy(BASE)
        self.events = []
        self.fail = set(fail)
        self.healthy = {"backend": True, "backend-2": True}

    def read_config(self):
        return deepcopy(self.config)

    def load_config(self, config):
        self.config = deepcopy(config)
        self.events.append(("route", module.backend_upstreams(config)))

    def ready(self, service):
        if not self.healthy[service]:
            raise RuntimeError("unhealthy peer")
        self.events.append(("ready", service))

    def recreate(self, service, rollback=False):
        peers = module.backend_upstreams(self.config)
        expected = {"backend", "backend-2"} - {service}
        assert peers == [expected], "replacement began without draining its traffic"
        assert self.healthy[next(iter(expected))], "no healthy peer"
        self.events.append(("rollback" if rollback else "up", service))
        if (service, rollback) in self.fail:
            self.healthy[service] = False
            raise RuntimeError("controlled replacement failure")
        self.healthy[service] = True


class RollingBackendTests(unittest.TestCase):
    def test_success_drains_each_replica_and_restores_exact_original_proxy(self):
        runtime = FakeRuntime()
        module.roll(runtime)
        self.assertEqual(runtime.config, BASE)
        self.assertEqual(
            [e for e in runtime.events if e[0] == "up"],
            [("up", "backend"), ("up", "backend-2")],
        )
        self.assertFalse(any(e[0] == "rollback" for e in runtime.events))

    def test_failure_rolls_back_failed_replica_first_while_healthy_peer_serves(self):
        runtime = FakeRuntime(fail={("backend-2", False)})
        with self.assertRaises(module.RolledBack):
            module.roll(runtime)
        self.assertEqual(runtime.config, BASE)
        self.assertEqual(
            [e for e in runtime.events if e[0] == "rollback"],
            [("rollback", "backend-2"), ("rollback", "backend")],
        )

    def test_failed_rollback_keeps_unhealthy_replica_drained(self):
        runtime = FakeRuntime(fail={("backend-2", False), ("backend-2", True)})
        with self.assertRaises(module.RollbackFailed):
            module.roll(runtime)
        self.assertEqual(module.backend_upstreams(runtime.config), [{"backend"}])
        self.assertTrue(runtime.healthy["backend"])

    def test_unknown_or_partial_proxy_topology_fails_before_any_mutation(self):
        for config in (
            {},
            {"upstreams": [{"dial": "backend:8000"}]},
            {"upstreams": [{"dial": "backend:8000"}, {"dial": "external:8000"}]},
        ):
            runtime = FakeRuntime()
            runtime.config = config
            with self.subTest(config=config), self.assertRaises(RuntimeError):
                module.roll(runtime)
            self.assertEqual(runtime.events, [])

    def test_unhealthy_peer_fails_without_proxy_or_container_changes(self):
        runtime = FakeRuntime()
        runtime.healthy["backend-2"] = False
        with self.assertRaises(RuntimeError):
            module.roll(runtime)
        self.assertFalse(
            any(e[0] in {"route", "up", "rollback"} for e in runtime.events)
        )
        self.assertEqual(runtime.config, BASE)

    def test_drain_preserves_all_unrelated_proxy_config(self):
        config = module.drained_config(BASE, "backend")
        self.assertEqual(
            BASE["apps"]["http"]["servers"]["public"]["routes"][1],
            config["apps"]["http"]["servers"]["public"]["routes"][1],
        )
        self.assertEqual(module.backend_upstreams(BASE), [{"backend", "backend-2"}])
        self.assertEqual(module.backend_upstreams(config), [{"backend-2"}])


class DockerRuntimeSafetyTests(unittest.TestCase):
    def test_proxy_edit_from_another_operator_is_not_overwritten(self):
        runtime = object.__new__(module.DockerRuntime)
        runtime.caddy = "caddy-container"
        runtime.expected_config = deepcopy(BASE)
        external = deepcopy(BASE)
        external["operator_edit"] = True
        runtime.command = Mock(return_value=json.dumps(external))
        with self.assertRaises(module.ProxyDrift):
            runtime.load_config(module.drained_config(BASE, "backend"))
        self.assertEqual(runtime.command.call_count, 1)
        self.assertNotIn("reload", runtime.command.call_args.args[0])

    def test_concurrent_proxy_edit_does_not_trigger_destructive_restoration(self):
        runtime = FakeRuntime()

        def edited(config):
            runtime.config["operator_edit"] = True
            raise module.ProxyDrift("operator updated proxy")

        runtime.load_config = edited
        with self.assertRaises(module.RollbackFailed):
            module.roll(runtime)
        self.assertTrue(runtime.config["operator_edit"])
        self.assertFalse(any(e[0] in {"up", "rollback"} for e in runtime.events))


class CLISafetyTests(unittest.TestCase):
    def test_authorization_and_sha_checks_precede_any_runtime_commands(self):
        import contextlib
        import io

        argv = [
            "rolling-backend.py",
            "--candidate-contract",
            "/candidate.yaml",
            "--rollback-contract",
            "/previous.yaml",
            "--candidate-tag",
            "a" * 40,
            "--rollback-tag",
            "b" * 40,
            "--backup-dir",
            "/private-backup",
        ]
        for arguments in (argv, [*argv, "--owner-approved", "--candidate-tag", "main"]):
            with (
                self.subTest(arguments=arguments),
                patch.object(module.sys, "argv", arguments),
                patch.object(module, "DockerRuntime") as runtime,
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(module.main(), 75)
                runtime.assert_not_called()
