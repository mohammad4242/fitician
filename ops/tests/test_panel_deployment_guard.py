import importlib.util
import unittest
from pathlib import Path


class PanelDeploymentGuardTests(unittest.TestCase):
    def test_expired_or_changed_baseline_and_untrusted_identity_are_rejected(self):
        path = Path(__file__).parents[1] / "panel-deployment-guard.py"
        spec = importlib.util.spec_from_file_location("panel_guard", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        request = {
            "operation_id": "9f91ff9f-6a91-40ac-b57e-66099b5c354e",
            "target": "iran",
            "baseline": "a" * 64,
            "expires": 2000,
        }
        packet = {
            "target_environment": "production-iran",
            "baseline_sha256": "a" * 64,
            "complete": True,
        }
        module.verify(request, packet, now=1000)
        for changed in (
            {"expires": 999},
            {"baseline": "b" * 64},
            {"operation_id": "$(touch owned)"},
        ):
            with self.assertRaises(ValueError):
                module.verify({**request, **changed}, packet, now=1000)
        with self.assertRaises(ValueError):
            module.verify(request, {**packet, "complete": False}, now=1000)

    def test_panel_guard_runs_under_host_lock_before_mutations_and_owner_gate_is_preserved(self):
        root = Path(__file__).parents[2]
        source = (root / "ops/deploy-regional.sh").read_text()
        self.assertIn("flock -n 9", source)
        self.assertIn("panel-deployment-guard.py", source)
        self.assertLess(source.index("panel-deployment-guard.py"), source.index("docker update"))
        workflow = (root / ".github/workflows/deploy-regional.yml").read_text()
        for text in (
            "production-owner-approval",
            "expected_baseline_sha256",
            "authorization_expires_at",
            "operation_id",
            "fitician-deployment-",
        ):
            self.assertTrue(text in workflow, text)


if __name__ == "__main__":
    unittest.main()
