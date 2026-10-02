import importlib.util
import unittest
from pathlib import Path


class BackendQualityTests(unittest.TestCase):
    def test_line_shifts_preserve_existing_diagnostics_but_new_errors_fail(self):
        script = Path(__file__).resolve().parents[1] / "check-backend-quality.py"
        spec = importlib.util.spec_from_file_location("quality", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = module.diagnostics("mypy", "app/workouts/service.py:3: error: bad [arg-type]\n")
        shifted = module.diagnostics("mypy", "app/workouts/service.py:10: error: bad [arg-type]\n")
        self.assertEqual(before, shifted)
        after = module.diagnostics(
            "mypy",
            "app/workouts/service.py:10: error: bad [arg-type]\n"
            "app/workouts/service.py:11: error: new [arg-type]\n",
        )
        self.assertEqual(sum((after - before).values()), 1)
