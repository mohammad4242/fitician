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
            {"published": port, "host_ip": "127.0.0.1"}
            for port in ("18080", "18443")
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
            "type": "bind", "source": "/production", "target": "/var/lib/postgresql"
        }
        with self.assertRaisesRegex(ValueError, "dedicated rehearsal volume"):
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
        self.assertEqual(module.validate_config(self.isolated_config())["project"], module.PROJECT)

    def test_cli_project_precedes_and_overrides_production_env_project(self):
        command = module.compose_command(Path("production.env"))
        self.assertEqual(command[command.index("--project-name") + 1], module.PROJECT)
        self.assertEqual(command.count("--project-name"), 1)

    def test_rejects_production_project_even_with_rehearsal_volume_names(self):
        with self.assertRaisesRegex(ValueError, "separate rehearsal project"):
            module.validate_config({"name": "fitician-iran"})

    def test_rejects_noninternal_network_before_any_startup(self):
        with self.assertRaisesRegex(ValueError, "internal network"):
            module.validate_config({"name": module.PROJECT, "networks": {"default": {}}})
