import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        "diagnostics_release", ROOT / "ops/diagnostics-release.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class DiagnosticsReleaseTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name)

    def policy(self, services):
        path = self.app / "diagnostics-workers.json"
        path.write_text(json.dumps({"version": 1, "services": services}))
        path.chmod(0o600)
        return path

    def secret(self, service, extra=""):
        path = self.app / (service + ".env")
        path.write_text("DATABASE_URL=postgresql+psycopg://synthetic@db/test\n" + extra)
        path.chmod(0o600)
        return path

    def test_absent_policy_cannot_activate_workers(self):
        helper = module()
        self.assertEqual(helper.load_policy(self.app), [])

    def test_only_explicit_unique_known_services_are_accepted(self):
        helper = module()
        for services in (["backend"], ["debug-worker", "debug-worker"], "debug-worker"):
            self.policy(services)
            with self.assertRaisesRegex(ValueError, "diagnostics_policy_invalid"):
                helper.load_policy(self.app)
        self.policy(["debug-worker"])
        self.assertEqual(helper.load_policy(self.app), ["debug-worker"])

    def test_configuration_must_be_private_regular_files_and_never_leaks_values(self):
        helper = module()
        path = self.secret("debug-worker", "AI_CREDENTIAL_ENCRYPTION_KEY=synthetic-private\n")
        self.assertIn("debug-worker", helper.config_fingerprints(self.app, ["debug-worker"]))
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "diagnostics_private_file_required"):
            helper.config_fingerprints(self.app, ["debug-worker"])
        path.unlink()
        path.symlink_to(self.app / "outside.env")
        with self.assertRaisesRegex(ValueError, "diagnostics_private_file_required"):
            helper.config_fingerprints(self.app, ["debug-worker"])

    def test_sync_and_alert_credentials_cannot_be_shared_with_debug_worker(self):
        helper = module()
        self.secret(
            "debug-worker",
            "AI_CREDENTIAL_ENCRYPTION_KEY=synthetic\nSENTRY_API_TOKEN=private\n",
        )
        with self.assertRaisesRegex(ValueError, "diagnostics_secret_scope_invalid"):
            helper.config_fingerprints(self.app, ["debug-worker"])

    def test_sms_activation_is_required_before_start_not_inferred_from_provider_key(
        self,
    ):
        helper = module()
        self.secret(
            "diagnostics-alert-worker",
            "FARAZSMS_API_KEY=synthetic\nFARAZSMS_FROM_NUMBER=123456\nDIAGNOSTICS_ALERT_PHONE=synthetic\n",
        )
        with self.assertRaisesRegex(ValueError, "diagnostics_configuration_incomplete"):
            helper.config_fingerprints(self.app, ["diagnostics-alert-worker"])

    def test_sms_activation_requires_usable_https_panel_origin_and_timezone(self):
        helper = module()
        common = (
            "FARAZSMS_API_KEY=synthetic\nFARAZSMS_FROM_NUMBER=123456\n"
            "DIAGNOSTICS_ALERT_PHONE=synthetic\nDIAGNOSTICS_ALERT_ENABLED=true\n"
        )
        for origin, activation in (
            ("", "2026-11-14T00:00:00+00:00"),
            ("http://localhost:5173", "2026-11-14T00:00:00+00:00"),
            ("https://user:secret@fitician.ir", "2026-11-14T00:00:00+00:00"),
            (
                "https://fitician.ir/private?token=synthetic",
                "2026-11-14T00:00:00+00:00",
            ),
            ("https://fitician.ir/#fragment", "2026-11-14T00:00:00+00:00"),
            ("https://fitician.ir", "not-a-time"),
            ("https://fitician.ir", "2026-11-14T00:00:00"),
        ):
            self.secret(
                "diagnostics-alert-worker",
                common
                + "FRONTEND_ORIGIN="
                + origin
                + "\nDIAGNOSTICS_ALERT_ENABLED_AT="
                + activation
                + "\n",
            )
            with (
                self.subTest(origin=origin, activation=activation),
                self.assertRaisesRegex(ValueError, "diagnostics_configuration_incomplete"),
            ):
                helper.config_fingerprints(self.app, ["diagnostics-alert-worker"])
        self.secret(
            "diagnostics-alert-worker",
            common
            + "FRONTEND_ORIGIN=https://fitician.ir\nDIAGNOSTICS_ALERT_ENABLED_AT=2026-11-14T00:00:00Z\n",
        )
        self.assertIn(
            "diagnostics-alert-worker",
            helper.config_fingerprints(self.app, ["diagnostics-alert-worker"]),
        )

    def test_database_budget_check_fails_before_any_capacity_or_container_inspection(
        self,
    ):
        helper = module()
        with (
            patch.object(helper, "command", side_effect=ValueError("unavailable")) as run,
            self.assertRaisesRegex(ValueError, "diagnostics_database_budget_check_failed"),
        ):
            helper.capacity(self.app, self.app, "fitician-iran", ["debug-worker"])
        self.assertEqual(run.call_count, 1)
        self.assertIn("--additional-worker-connections", run.call_args.args[0])
        self.assertEqual(run.call_args.args[0][-1], "1")

    def test_capacity_accounts_for_full_worker_limits_and_existing_runtime(self):
        helper = module()
        with self.assertRaisesRegex(ValueError, "diagnostics_capacity_exceeded"):
            helper.check_capacity(
                ["debug-worker", "diagnostics-sync-worker", "diagnostics-alert-worker"],
                core_memory=2880,
                other_memory=0,
                host_memory=3916,
                core_cpu=2.2,
                other_cpu=0,
                host_cpus=2,
                disk_free=10 * 1024**3,
            )
        helper.check_capacity(
            ["debug-worker"],
            core_memory=2880,
            other_memory=0,
            host_memory=6144,
            core_cpu=2.2,
            other_cpu=0,
            host_cpus=4,
            disk_free=10 * 1024**3,
        )

    def test_commands_are_fixed_and_use_never_pull_with_explicit_services(self):
        helper = module()
        commands = []

        def command(args, **kwargs):
            commands.append((args, kwargs))
            return ""

        with patch.object(helper, "command", side_effect=command):
            helper.compose(
                self.app,
                self.app / "releases" / ("a" * 40),
                "fitician-iran",
                "a" * 40,
                ["debug-worker"],
                ["up", "-d", "--pull", "never", "--no-deps", "--wait"],
            )
        args, kwargs = commands[0]
        self.assertEqual(args[-1], "debug-worker")
        self.assertEqual(args[args.index("-p") + 1], "fitician-iran-diagnostics")
        self.assertEqual(kwargs["env"]["FITICIAN_DEBUG_NETWORK"], "fitician-iran_default")
        self.assertNotIn("DATABASE_URL", kwargs["env"])
        self.assertIn("never", args)

    def test_rollback_restores_previous_release_not_candidate_and_retains_state(self):
        helper = module()
        previous = {
            "version": 1,
            "commit": "a" * 40,
            "services": ["debug-worker"],
            "config_sha256": {"debug-worker": "b" * 64},
        }
        helper.write_private(self.app / ".diagnostics-active.json", previous)
        helper.save_previous(self.app, "c" * 40)
        helper.write_private(
            self.app / ".diagnostics-active.json", {**previous, "commit": "c" * 40}
        )
        calls = []
        with (
            patch.object(
                helper,
                "activate",
                side_effect=lambda app, project, state: calls.append(state),
            ),
            patch.object(helper, "pause", return_value=None),
        ):
            helper.rollback(self.app, "fitician-iran", "c" * 40)
        self.assertEqual(calls, [previous])
        self.assertEqual(json.loads((self.app / ".diagnostics-active.json").read_text()), previous)

    def test_existing_workers_without_policy_fail_closed(self):
        helper = module()
        helper.write_private(self.app / ".diagnostics-active.json", {"version": 1})
        with self.assertRaisesRegex(ValueError, "diagnostics_policy_missing_for_active_workers"):
            helper.load_policy(self.app)

    def test_emergency_quiescence_does_not_depend_on_current_secret_files_or_policy(
        self,
    ):
        helper = module()
        state = {
            "version": 1,
            "commit": "a" * 40,
            "services": ["debug-worker"],
            "config_sha256": {"debug-worker": "b" * 64},
        }
        helper.write_private(self.app / ".diagnostics-active.json", state)
        with (
            patch(
                "sys.argv",
                [
                    "diagnostics-release.py",
                    "quiesce",
                    "--app-dir",
                    str(self.app),
                    "--commit",
                    "c" * 40,
                    "--project",
                    "fitician-iran",
                ],
            ),
            patch.object(helper, "pause") as pause,
        ):
            self.assertEqual(helper.main(), 0)
        pause.assert_called_once_with(self.app, "fitician-iran", state)

    def test_real_compose_keeps_secrets_literal_and_scoped_without_volumes_or_ports(
        self,
    ):
        debug = self.secret(
            "debug-worker",
            "AI_CREDENTIAL_ENCRYPTION_KEY=literal$SYNTHETIC_UNSET#value\n",
        )
        sync = self.secret("diagnostics-sync-worker", "SENTRY_API_TOKEN=synthetic-sync-only\n")
        alert = self.secret("diagnostics-alert-worker", "FARAZSMS_API_KEY=synthetic-alert-only\n")
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                "/dev/null",
                "-f",
                str(ROOT / "compose.debugging.yaml"),
                "--profile",
                "diagnostics-debug",
                "--profile",
                "diagnostics-alerts",
                "config",
                "--format",
                "json",
            ],
            env={
                "PATH": os.environ["PATH"],
                "HOME": os.environ["HOME"],
                "FITICIAN_DEBUG_IMAGE": "example/fitician-backend:" + "a" * 40,
                "FITICIAN_DEBUG_ENV_FILE": str(debug),
                "FITICIAN_SYNC_ENV_FILE": str(sync),
                "FITICIAN_ALERT_ENV_FILE": str(alert),
                "FITICIAN_DEBUG_NETWORK": "synthetic_default",
                "DIAGNOSTICS_ENVIRONMENT": "production-iran",
            },
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, "Synthetic Compose rendering failed")
        config = json.loads(result.stdout)
        self.assertFalse(config.get("volumes"))
        services = config["services"]
        self.assertEqual(
            services["debug-worker"]["environment"]["AI_CREDENTIAL_ENCRYPTION_KEY"],
            # `config` escapes dollars so its serialized output can be parsed again.
            "literal$$SYNTHETIC_UNSET#value",
        )
        for name, service in services.items():
            self.assertFalse(service.get("ports"))
            self.assertFalse(service.get("volumes"))
            self.assertTrue(service["read_only"])
            self.assertEqual(service["environment"].get("DB_POOL_SIZE"), "1")
            self.assertEqual(service["environment"].get("DB_MAX_OVERFLOW"), "0")
            self.assertEqual(service["healthcheck"]["start_period"], "2m0s")
            self.assertEqual(service["environment"]["DIAGNOSTICS_ENVIRONMENT"], "production-iran")
            if name != "diagnostics-sync-worker":
                self.assertNotIn("SENTRY_API_TOKEN", service["environment"])
            if name != "diagnostics-alert-worker":
                self.assertNotIn("FARAZSMS_API_KEY", service["environment"])


if __name__ == "__main__":
    unittest.main()


class SharedDiagnosticsTests(DiagnosticsReleaseTests):
    def shared_policy(self, services):
        path = self.policy(services)
        path.write_text(json.dumps({"version": 2, "mode": "shared", "services": services}))
        return path

    def shared_secret(self, extra=""):
        path = self.app / "diagnostics-shared.env"
        path.write_text(
            "DIAGNOSTICS_ENVIRONMENT=production-iran\n"
            "DEBUG_REMOTE_DISPATCH_ENABLED=true\n"
            "DIAGNOSTICS_MAINTENANCE_ENABLED=true\n"
            "DIAGNOSTICS_ALERT_ENABLED=false\n"
            "SENTRY_ORG=synthetic\nSENTRY_PROJECT=synthetic-backend\n"
            "SENTRY_API_TOKEN=synthetic-read-only\n" + extra
        )
        path.chmod(0o600)
        return path

    def test_shared_policy_reuses_scheduler_without_dedicated_containers(self):
        helper = module()
        roles = ["debug-worker", "diagnostics-sync-worker"]
        self.shared_policy(roles)
        self.shared_secret()
        self.assertEqual(helper.load_policy(self.app), sorted(roles))
        state = helper.desired_state(self.app, "a" * 40)
        self.assertEqual(state["mode"], "shared")
        self.assertEqual(set(state["config_sha256"]), {"scheduler"})
        helper.write_private(self.app / helper.ACTIVE, state)
        self.assertEqual(helper.load_state(self.app), state)
        self.assertEqual(
            helper.scheduler_env_file(self.app),
            str(self.app / "diagnostics-shared.env"),
        )
        with patch.object(helper, "command", return_value="d" * 12) as command:
            helper.pause(self.app, "fitician-iran", state)
        self.assertEqual(
            command.call_args_list[-1].args[0],
            ["docker", "stop", "--time", "30", "d" * 12],
        )
        self.assertIn(
            "label=com.docker.compose.service=scheduler",
            command.call_args_list[0].args[0],
        )

    def test_shared_credentials_cannot_activate_unapproved_alerts_or_export_model_secrets(
        self,
    ):
        helper = module()
        self.shared_policy(["debug-worker", "diagnostics-sync-worker"])
        for extra in (
            "FITICIAN_DEBUG_OPENROUTER_API_KEY=synthetic-model-secret\n",
            "GITHUB_TOKEN=synthetic-github\n",
            "DIAGNOSTICS_ALERT_PHONE=private\n",
            "FARAZSMS_API_KEY=private\n",
            "DIAGNOSTICS_ALERT_ENABLED=true\n",
        ):
            self.shared_secret(extra)
            with self.assertRaises(ValueError):
                helper.desired_state(self.app, "a" * 40)
        self.shared_secret()
        helper.desired_state(self.app, "a" * 40)

    def test_shared_capacity_uses_available_memory_and_keeps_production_reserve(self):
        helper = module()
        helper.check_shared_capacity(
            available_mib=1220,
            load_average=0.6,
            cpus=2,
            scheduler_remaining_mib=80,
            disk_free=9 * 1024**3,
        )
        for changes in (
            {"available_mib": 900},
            {"load_average": 1.9},
            {"scheduler_remaining_mib": 20},
            {"disk_free": 1024**3},
        ):
            kwargs = dict(
                available_mib=1220,
                load_average=0.6,
                cpus=2,
                scheduler_remaining_mib=80,
                disk_free=9 * 1024**3,
            )
            kwargs.update(changes)
            with self.assertRaisesRegex(ValueError, "diagnostics_capacity_exceeded"):
                helper.check_shared_capacity(**kwargs)

    def test_shared_readback_checks_scheduler_image_and_role_heartbeats(self):
        helper = module()
        self.shared_policy(["debug-worker", "diagnostics-sync-worker"])
        self.shared_secret()
        state = helper.desired_state(self.app, "a" * 40)
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args[:3] == ["docker", "image", "inspect"]:
                return "sha256:" + "b" * 64
            if args[:2] == ["docker", "ps"]:
                return "c" * 12
            if args[:2] == ["docker", "inspect"]:
                return "sha256:" + "b" * 64 + " running healthy"
            return ""

        with patch.object(helper, "command", side_effect=command):
            helper.verify(self.app, "fitician-iran", state)
        self.assertTrue(any("/run/fitician/debug-dispatch.json" in cmd for cmd in calls))
        self.assertTrue(any("/run/fitician/diagnostics-sync-worker.json" in cmd for cmd in calls))
        self.assertFalse(any("up" in cmd or "stop" in cmd for cmd in calls))

    def test_shared_compose_and_release_path_load_extra_secrets_only_in_scheduler(self):
        self.shared_policy(["debug-worker", "diagnostics-sync-worker"])
        private = self.shared_secret()
        env = {
            **os.environ,
            "DOCKERHUB_USERNAME": "synthetic",
            "IMAGE_TAG": "a" * 40,
            "DATABASE_URL": "postgresql+psycopg://synthetic:synthetic@db:5432/synthetic",
            "POSTGRES_USER": "synthetic",
            "POSTGRES_PASSWORD": "synthetic",
            "POSTGRES_DB": "synthetic",
            "REDIS_PASSWORD": "synthetic",
            "FITICIAN_DOMAIN": "fitician.example",
            "POSTGRES_VOLUME_NAME": "synthetic-pg",
            "REDIS_VOLUME_NAME": "synthetic-redis",
            "CADDY_DATA_VOLUME_NAME": "synthetic-caddy",
            "CADDY_CONFIG_VOLUME_NAME": "synthetic-caddy-config",
            "AGENT_SERVICE_BASE_URL": "http://100.64.0.2:8090",
            "AGENT_SERVICE_TOKEN": "synthetic-agent",
            "FITICIAN_ENV_FILE": "/dev/null",
            "FITICIAN_DIAGNOSTICS_ENV_FILE": str(private),
        }
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                "/dev/null",
                "-f",
                str(ROOT / "compose.prod.iran.yaml"),
                "config",
                "--format",
                "json",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, "Synthetic Compose rendering failed")
        services = json.loads(result.stdout)["services"]
        self.assertEqual(
            services["scheduler"]["environment"].get("SENTRY_API_TOKEN"),
            "synthetic-read-only",
        )
        for name, service in services.items():
            if name != "scheduler":
                self.assertNotIn("SENTRY_API_TOKEN", service.get("environment", {}))
        self.assertNotIn("debug-worker", services)
        self.assertNotIn("diagnostics-sync-worker", services)
        deploy = (ROOT / "ops/deploy-regional.sh").read_text()
        self.assertIn("diagnostics env-file", deploy)
        self.assertIn('FITICIAN_DIAGNOSTICS_ENV_FILE="$diagnostics_env_file"', deploy)

    def test_shared_alert_role_requires_explicit_activation(
        self,
    ):
        helper = module()
        roles = ["debug-worker", "diagnostics-sync-worker", "diagnostics-alert-worker"]
        self.shared_policy(roles)
        secret = self.shared_secret(
            "FARAZSMS_API_KEY=test-sms-only\nFARAZSMS_FROM_NUMBER=test-line\n"
            "DIAGNOSTICS_ALERT_PHONE=test-recipient\nFRONTEND_ORIGIN=https://fitician.example\n"
            "DIAGNOSTICS_ALERT_ENABLED_AT=2026-11-22T00:00:00+00:00\n"
        )
        with self.assertRaisesRegex(ValueError, "diagnostics_configuration_incomplete"):
            helper.desired_state(self.app, "a" * 40)
        secret.write_text(
            secret.read_text().replace(
                "DIAGNOSTICS_ALERT_ENABLED=false", "DIAGNOSTICS_ALERT_ENABLED=true"
            )
        )
        self.assertEqual(helper.desired_state(self.app, "a" * 40)["services"], sorted(roles))

    def test_shared_rollback_restores_previous_role_configuration_and_exact_release(self):
        helper = module()
        self.shared_policy(["debug-worker", "diagnostics-sync-worker"])
        self.shared_secret()
        previous = helper.desired_state(self.app, "a" * 40)
        helper.write_private(self.app / helper.ACTIVE, previous)
        helper.save_previous(self.app, "c" * 40)
        helper.write_private(self.app / helper.ACTIVE, helper.desired_state(self.app, "c" * 40))
        with patch.object(helper, "pause") as pause, patch.object(helper, "activate") as activate:
            helper.rollback(self.app, "fitician-iran", "c" * 40)
        activate.assert_called_once_with(self.app, "fitician-iran", previous)
        pause.assert_called_once()
        self.assertEqual(helper.load_state(self.app), previous)

    def test_base_environment_cannot_enable_shared_dispatch_without_host_policy(self):
        helper = module()
        path = self.app / ".env"
        path.write_text('DEBUG_REMOTE_DISPATCH_ENABLED="true"\n')
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "diagnostics_unapproved_shared_activation"):
            helper.scheduler_env_file(self.app)

    def test_shared_alerts_declare_sync_role_instead_of_inheriting_an_unapproved_loop(self):
        helper = module()
        self.shared_policy(["diagnostics-alert-worker"])
        with self.assertRaisesRegex(ValueError, "diagnostics_policy_invalid"):
            helper.load_policy(self.app)
