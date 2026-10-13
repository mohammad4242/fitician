import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "rehearse-regional.py"
SPEC = importlib.util.spec_from_file_location("rehearse_regional", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class OfflineRehearsalGuards(unittest.TestCase):
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
