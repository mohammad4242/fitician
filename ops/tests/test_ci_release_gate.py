import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "gate", Path(__file__).resolve().parents[1] / "ci-release-gate.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SHA = "b" * 40


def success(*names):
    return [{"name": name, "conclusion": "success"} for name in names]


class ReleaseGateTests(unittest.TestCase):
    def test_frontend_fast_does_not_require_full_images(self):
        plan = dict(
            sha=SHA,
            release_requested=True,
            deployable=True,
            full_ci_required=False,
            deploy_frontend=True,
            deploy_backend=False,
            deploy_agent=False,
        )
        jobs = success(
            "Secret scan",
            "Frontend component / Frontend verification",
            "Frontend component / Build, verify, and push frontend image",
        )
        self.assertEqual(module.release_path(plan, jobs, SHA), "component")
        with self.assertRaises(ValueError):
            module.release_path(plan, jobs[:-1], SHA)

    def test_sha_mismatch_and_missing_full_images_fail_closed(self):
        plan = dict(sha=SHA, release_requested=True, deployable=True, full_ci_required=True)
        with self.assertRaises(ValueError):
            module.release_path(plan, success("Secret scan"), SHA)
        with self.assertRaises(ValueError):
            module.release_path(plan, [], "a" * 40)
        self.assertEqual(
            module.release_path(
                plan,
                success("Secret scan", "Build and publish immutable production images"),
                SHA,
            ),
            "full",
        )

    def test_nightly_manual_validation_and_mobile_never_release(self):
        for requested, deployable in [(False, True), (True, False)]:
            self.assertEqual(
                module.release_path(
                    dict(sha=SHA, release_requested=requested, deployable=deployable),
                    [],
                    SHA,
                ),
                "none",
            )


if __name__ == "__main__":
    unittest.main()
