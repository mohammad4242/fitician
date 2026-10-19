import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "auto_release", ROOT / "ops/ci-auto-release.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SHA = "a" * 40


def valid_run():
    return {
        "id": 123,
        "name": "Fitician CI",
        "path": ".github/workflows/ci.yml",
        "head_sha": SHA,
        "head_branch": "main",
        "head_repository": {"full_name": "owner/repo"},
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }


class CanonicalRunTests(unittest.TestCase):
    def test_exact_successful_main_push_is_accepted(self):
        module.validate_run(valid_run(), "owner/repo", SHA, 123)

    def test_forged_stale_and_noncanonical_runs_are_rejected(self):
        run = valid_run()
        variants = [
            {**run, "id": 124},
            {**run, "path": ".github/workflows/other.yml"},
            {**run, "head_branch": "feature"},
            {**run, "event": "pull_request"},
            {**run, "head_repository": {"full_name": "fork/repo"}},
            {**run, "status": "in_progress"},
            {**run, "conclusion": "failure"},
        ]
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                module.validate_run(bad, "owner/repo", SHA, 123)
        with self.assertRaises(ValueError):
            module.validate_run(run, "owner/repo", "b" * 40, 123)

    def test_deploy_time_recheck_rejects_main_advance_or_changed_run(self):
        with patch.object(
            module,
            "gh_json",
            side_effect=[valid_run(), {"commit": {"sha": SHA}}],
        ):
            module.validate_current_main("owner/repo", 123, SHA)
        with patch.object(
            module,
            "gh_json",
            side_effect=[valid_run(), {"commit": {"sha": "b" * 40}}],
        ), self.assertRaisesRegex(ValueError, "current main CI"):
            module.validate_current_main("owner/repo", 123, SHA)

    def test_canonical_but_stale_runs_are_skipped_before_artifact_lookup(self):
        stale = {**valid_run(), "head_sha": "b" * 40}
        with patch.object(module, "gh_json", side_effect=[stale, {"commit": {"sha": SHA}}]) as api:
            result = module.validate_automatic_run("owner/repo", 123, Path("unused"))
        self.assertEqual(result, {"skip_release": "true", "auto_release": "false"})
        self.assertEqual(api.call_count, 2)


class AutomaticRouteTests(unittest.TestCase):
    def test_exactly_one_component_routes_to_iran(self):
        for component in ("frontend", "backend"):
            plan = {
                "full_ci_required": False,
                "selective_ci_required": False,
                "deployable": True,
                "deploy_frontend": component == "frontend",
                "deploy_backend": component == "backend",
                "deploy_agent": False,
                "changed_paths": [
                    "frontend/src/app.tsx"
                    if component == "frontend"
                    else "backend/app/workouts/service.py"
                ],
            }
            self.assertEqual(
                module.select_auto_route(plan, "component"), ("iran", component)
            )

    def test_strict_agent_source_only_routes_to_germany_with_full_ci(self):
        plan = {
            "full_ci_required": True,
            "selective_ci_required": False,
            "deployable": True,
            "deploy_agent": True,
            "deploy_frontend": True,
            "deploy_backend": True,
            "changed_paths": [
                "agent-service/app/main.py",
                "agent-service/tests/test_main.py",
                "docs/agent.md",
            ],
        }
        self.assertEqual(module.select_auto_route(plan, "full"), ("germany", "agent"))

    def test_multiple_components_full_and_unsafe_agent_changes_never_auto_route(self):
        frontend = {
            "full_ci_required": False,
            "selective_ci_required": False,
            "deployable": True,
            "deploy_frontend": True,
            "deploy_backend": False,
            "deploy_agent": False,
            "changed_paths": ["frontend/src/app.tsx"],
        }
        mixed = {
            **frontend,
            "deploy_backend": True,
            "changed_paths": ["frontend/src/app.tsx", "backend/app/workouts/service.py"],
        }
        full = {
            **frontend,
            "full_ci_required": True,
            "deploy_backend": True,
            "deploy_agent": True,
            "changed_paths": ["compose.prod.iran.yaml"],
        }
        agent = {
            **full,
            "deploy_agent": True,
            "deploy_frontend": True,
            "deploy_backend": True,
            "changed_paths": ["agent-service/app/main.py", "agent-service/Dockerfile"],
        }
        self.assertEqual(module.select_auto_route(frontend, "component"), ("iran", "frontend"))
        for plan, path in ((mixed, "component"), (full, "full"), (agent, "full")):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                module.select_auto_route(plan, path)

    def test_canonical_noneligible_plans_skip_without_failing_the_workflow(self):
        plan = module.classify_paths([])
        plan["deployable"] = False
        self.assertIsNone(module.automatic_route_or_skip(plan, "full"))


if __name__ == "__main__":
    unittest.main()
