import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "rehearse-regional.py"
SPEC = importlib.util.spec_from_file_location("rehearse_regional", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class OfflineRehearsalGuards(unittest.TestCase):
    def isolated_config(self):
        mounts = {
            "db": [("pg", "/var/lib/postgresql")],
            "redis": [("redis", "/data")],
            "caddy": [("tls", "/data"), ("config", "/config")],
        }
        services = {
            name: {
                "networks": {"default": {}},
                "mem_limit": 1024 * 1024,
                "cpus": 0.01,
                "environment": {
                    "DATABASE_URL": "postgresql://qa@db/fitician_offline_rehearsal"
                },
                "volumes": [
                    {"type": "volume", "source": source, "target": target}
                    for source, target in mounts.get(name, [])
                ],
            }
            for name in module.SERVICES
        }
        services["db"]["environment"]["POSTGRES_DB"] = "fitician_offline_rehearsal"
        services["caddy"]["ports"] = [
            {"published": port, "host_ip": "127.0.0.1"} for port in ("18080", "18443")
        ]
        return {
            "name": module.PROJECT,
            "networks": {"default": {"internal": True}},
            "services": services,
            "volumes": {
                key: {"external": True, "name": f"fitician_offline_rehearsal_{key}_qa"}
                for key in ("pg", "redis", "tls", "config")
            },
        }

    def test_rejects_database_bind_mount_despite_safe_volume_declarations(self):
        config = self.isolated_config()
        config["services"]["db"]["volumes"][0] = {
            "type": "bind",
            "source": "/production",
            "target": "/var/lib/postgresql",
        }
        with self.assertRaisesRegex(ValueError, "rehearsal"):
            module.validate_config(config)

    def test_rejects_undeclared_service_volume(self):
        config = self.isolated_config()
        config["services"]["db"]["volumes"][0]["source"] = "production_data"
        with self.assertRaisesRegex(ValueError, "dedicated rehearsal volume"):
            module.validate_config(config)

    def test_rejects_shared_names_between_rehearsal_volume_roles(self):
        config = self.isolated_config()
        config["volumes"]["redis"] = deepcopy(config["volumes"]["pg"])
        with self.assertRaisesRegex(ValueError, "distinct rehearsal volumes"):
            module.validate_config(config)

    def test_accepts_dedicated_rehearsal_mounts(self):
        self.assertEqual(
            module.validate_config(self.isolated_config())["project"], module.PROJECT
        )

    def test_rejects_host_privileges_and_namespace_escapes(self):
        for key, value in (
            ("privileged", True),
            ("network_mode", "host"),
            ("pid", "host"),
            ("ipc", "host"),
            ("devices", ["/dev/sda"]),
            ("cap_add", ["SYS_ADMIN"]),
        ):
            with self.subTest(key=key):
                config = self.isolated_config()
                config["services"]["backend"][key] = value
                with self.assertRaisesRegex(ValueError, "host access"):
                    module.validate_config(config)

    def test_rejects_arbitrary_host_bind_mount(self):
        config = self.isolated_config()
        config["services"]["backend"]["volumes"] = [
            {"type": "bind", "source": "/", "target": "/host", "read_only": True}
        ]
        with self.assertRaisesRegex(ValueError, "read-only rehearsal configuration"):
            module.validate_config(config)

    def test_rejects_configuration_bind_outside_workspace(self):
        config = self.isolated_config()
        config["services"]["caddy"]["volumes"].append(
            {
                "type": "bind",
                "source": "/production/rehearsal.Caddyfile",
                "target": "/etc/caddy/Caddyfile",
                "read_only": True,
            }
        )
        with self.assertRaisesRegex(ValueError, "read-only rehearsal configuration"):
            module.validate_config(config)

    def test_accepts_only_reviewed_readonly_configuration_binds(self):
        config = self.isolated_config()
        config["services"]["caddy"]["volumes"].append(
            {
                "type": "bind",
                "source": str(module.ROOT / "ops/Caddyfile.offline-rehearsal"),
                "target": "/etc/caddy/Caddyfile",
                "read_only": True,
            }
        )
        self.assertEqual(module.validate_config(config)["project"], module.PROJECT)
        config["services"]["caddy"]["volumes"][-1]["read_only"] = False
        with self.assertRaisesRegex(ValueError, "read-only rehearsal configuration"):
            module.validate_config(config)

    def test_cli_project_precedes_and_overrides_production_env_project(self):
        command = module.compose_command(Path("production.env"))
        self.assertEqual(command[command.index("--project-name") + 1], module.PROJECT)
        self.assertEqual(command.count("--project-name"), 1)

    def test_rejects_production_project_even_with_rehearsal_volume_names(self):
        with self.assertRaisesRegex(ValueError, "separate rehearsal project"):
            module.validate_config({"name": "fitician-iran"})

    def test_rejects_noninternal_network_before_any_startup(self):
        with self.assertRaisesRegex(ValueError, "internal network"):
            module.validate_config(
                {"name": module.PROJECT, "networks": {"default": {}}}
            )
