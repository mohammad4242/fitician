"""Read-only host evidence must never return Docker secrets or arbitrary log text."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        "debug_host", ROOT / "ops/debug-server-observation.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class HostEvidenceTests(unittest.TestCase):
    def test_only_explicit_known_worker_names_are_read_from_private_activation_policy(
        self,
    ):
        host = module()
        self.assertTrue(
            hasattr(host, "optional_workers"), "Activated workers must be observable"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            path = Path(folder) / "diagnostics-workers.json"
            self.assertEqual(host.optional_workers(path), [])
            path.write_text(json.dumps({"version": 1, "services": ["debug-worker"]}))
            path.chmod(0o600)
            self.assertEqual(host.optional_workers(path), ["debug-worker"])
            path.write_text(json.dumps({"version": 1, "services": ["db"]}))
            with self.assertRaisesRegex(
                ValueError, "observation_worker_policy_invalid"
            ):
                host.optional_workers(path)

    def test_worker_evidence_uses_separate_project_and_affects_deployment_baseline(
        self,
    ):
        host = module()
        self.assertTrue(
            hasattr(host, "optional_workers"), "Activated workers must be observable"
        )
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args[1] == "ps":
                return "a" * 12
            if args[1] == "inspect":
                return json.dumps(
                    {
                        "container_id": "a" * 64,
                        "image_id": "sha256:" + "b" * 64,
                        "status": "running",
                        "health": "healthy",
                        "restart_count": 0,
                    }
                )
            if args[1] == "exec":
                return "20261114_185"
            return "c" * 40

        with (
            patch.object(host, "optional_workers", return_value=["debug-worker"]),
            patch.object(host, "command", side_effect=command),
        ):
            packet = host.observe("iran")
        worker = next(
            row for row in packet["services"] if row["service"] == "debug-worker"
        )
        self.assertEqual(worker["commit"], "c" * 40)
        self.assertTrue(packet["complete"])
        self.assertTrue(
            any(
                "label=com.docker.compose.project=fitician-iran-diagnostics" in call
                for call in calls
            )
        )
        without = [
            row for row in packet["services"] if row["service"] != "debug-worker"
        ]
        self.assertNotEqual(
            packet["baseline_sha256"],
            host.baseline(without, packet["database_revision"]),
        )

    def test_only_correlated_allowlisted_log_fields_leave_the_host(self):
        host = module()
        trace = "a" * 32
        raw = "\n".join(
            [
                json.dumps(
                    {
                        "trace_id": trace,
                        "error_code": "PROVIDER_TIMEOUT",
                        "medical_form": "private-health-fixture",
                        "message": "private-prompt-fixture",
                        "token": "private-credential-fixture",
                    }
                ),
                json.dumps({"trace_id": "b" * 32, "error_code": "OTHER_ISSUE"}),
                "Traceback: private unstructured medical fixture",
            ]
        )
        rows = host.correlated_logs(raw, trace)
        self.assertEqual(rows, [{"trace_id": trace, "error_code": "PROVIDER_TIMEOUT"}])
        self.assertNotIn("private", json.dumps(rows))
        self.assertEqual(host.correlated_logs(raw, None), [])

    def test_baseline_binds_container_image_and_database_revision_but_not_clock_or_logs(
        self,
    ):
        host = module()
        services = [
            {
                "service": "backend",
                "container_id": "a" * 64,
                "image_id": "sha256:" + "b" * 64,
                "status": "running",
                "health": "healthy",
            }
        ]
        digest = host.baseline(services, ["20261018_175"])
        self.assertEqual(
            digest,
            host.baseline([{**services[0], "health": "starting"}], ["20261018_175"]),
        )
        self.assertNotEqual(
            digest,
            host.baseline(
                [{**services[0], "image_id": "sha256:" + "c" * 64}], ["20261018_175"]
            ),
        )
        self.assertNotEqual(digest, host.baseline(services, ["20261113_184"]))

    def test_targets_and_trace_identifiers_cannot_select_arbitrary_commands(self):
        host = module()
        with patch.object(host, "command") as command:
            for target, trace in [("other", None), ("iran", "a" * 32 + ";id")]:
                with self.assertRaises(ValueError):
                    host.observe(target, trace)
            command.assert_not_called()

    def test_collection_uses_fixed_metadata_templates_and_never_reads_container_environment(
        self,
    ):
        host = module()
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args[1] == "ps":
                return "a" * 12
            if args[1] == "inspect":
                return json.dumps(
                    {
                        "container_id": "a" * 64,
                        "image_id": "sha256:" + "b" * 64,
                        "status": "running",
                        "health": "healthy",
                        "restart_count": 0,
                    }
                )
            return "c" * 40

        with patch.object(host, "command", side_effect=command):
            packet = host.observe("germany")
        self.assertTrue(packet["complete"])
        self.assertFalse(packet["business_outcome_verified"])
        self.assertNotIn("Config.Env", json.dumps(calls))
        self.assertFalse(any("logs" in call for call in calls))
        self.assertEqual(packet["services"][0]["commit"], "c" * 40)

    def test_unavailable_image_label_is_unknown_release_not_missing_service(self):
        host = module()

        def command(args, **kwargs):
            if args[1] == "ps":
                return "a" * 12
            if args[1] == "inspect":
                return json.dumps(
                    {
                        "container_id": "a" * 64,
                        "image_id": "sha256:" + "b" * 64,
                        "status": "running",
                        "health": None,
                        "restart_count": 0,
                    }
                )
            raise ValueError("observation_command_failed")

        with patch.object(host, "command", side_effect=command):
            packet = host.observe("germany")
        self.assertTrue(packet["complete"])
        self.assertEqual(packet["services"][0]["release_provenance"], "unknown")
        self.assertIsNone(packet["services"][0]["commit"])

    def test_remote_wrapper_rejects_injection_before_creating_credentials_or_connecting(
        self,
    ):
        import os
        import subprocess

        base = {
            **os.environ,
            "VPS_HOST": "host.example.invalid",
            "VPS_USER": "deploy",
            "VPS_SSH_PRIVATE_KEY": "synthetic-not-a-key",
            "VPS_KNOWN_HOSTS": "synthetic-not-a-host",
            "OBSERVATION_TARGET": "iran",
        }
        for change in (
            {"OBSERVATION_TARGET": "iran;id"},
            {"OBSERVATION_TRACE_ID": "a" * 32 + ";id"},
            {"VPS_HOST": "-oProxyCommand=id"},
            {"VPS_SSH_PORT": "0"},
        ):
            result = subprocess.run(
                ["bash", str(ROOT / "ops/debug-observe-remote.sh")],
                env={**base, **change},
                capture_output=True,
                check=False,
                timeout=5,
                cwd=ROOT,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"synthetic-not-a-key", result.stdout + result.stderr)

    def test_workflow_requires_reviewed_main_policy_and_existing_protected_environment(
        self,
    ):
        workflow = (ROOT / ".github/workflows/debug-server-observation.yml").read_text()
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("os.environ['POLICY']==os.environ['GITHUB_SHA']", workflow)
        self.assertIn("'production-iran' || 'production-germany'", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("contents: write", workflow)
        wrapper = (ROOT / "ops/debug-observe-remote.sh").read_text()
        self.assertIn("StrictHostKeyChecking=yes", wrapper)
        self.assertIn("ClearAllForwardings=yes", wrapper)
        self.assertNotIn("eval ", wrapper)
