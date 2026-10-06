from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def job(workflow, name):
    text = (ROOT / ".github/workflows" / workflow).read_text()
    match = re.search(
        r"^  " + re.escape(name) + r":\n(.*?)(?=^  [\w-]+:\n|\Z)", text, re.M | re.S
    )
    if not match:
        raise AssertionError(name)
    return match.group(1)


class ComponentWorkflowTests(unittest.TestCase):
    def test_full_and_component_image_paths_are_exclusive(self):
        full = job("ci.yml", "container-images")
        fast = job("ci.yml", "backend-component")
        frontend = job("ci.yml", "frontend")
        self.assertIn("needs.changes.outputs.full_ci_required == 'true'", full)
        self.assertIn("needs.changes.outputs.full_ci_required != 'true'", fast)
        self.assertIn("needs.changes.outputs.full_ci_required != 'true'", frontend)
        self.assertIn("called_by_router: true", frontend)
        self.assertNotIn(
            "push:", (ROOT / ".github/workflows/frontend-only.yml").read_text()
        )
        self.assertNotIn(
            "push:", (ROOT / ".github/workflows/backend-only.yml").read_text()
        )

    def test_production_full_and_component_routes_are_exclusive(self):
        full = job("deploy-production.yml", "deploy")
        front = job("deploy-production.yml", "deploy-frontend-component")
        back = job("deploy-production.yml", "deploy-backend-component")
        self.assertIn("release_path == 'full'", full)
        self.assertIn("release_path == 'component'", front)
        self.assertIn("release_path == 'component'", back)
        for component in (front, back):
            self.assertIn("github.event.workflow_run.head_sha", component)

    def test_nightly_validation_never_publishes_or_deploys(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn('cron: "23 0 * * *"', ci)
        full = job("ci.yml", "container-images")
        self.assertIn("github.event_name == 'schedule'", full)
        self.assertIn(
            "push: ${{ github.event_name == 'push' || "
            "(github.event_name == 'workflow_dispatch' && inputs.mode == 'release') }}",
            full,
        )
        cd = job("deploy-production.yml", "automatic_images_gate")
        self.assertIn("github.event.workflow_run.event == 'push'", cd)

    def test_deployment_is_not_cancelled_by_validation_concurrency(self):
        deploy = job("deploy-component.yml", "deploy")
        self.assertIn("group: fitician-production", deploy)
        self.assertIn("cancel-in-progress: false", deploy)
        self.assertIn("queue: max", deploy)
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertNotIn("mobile-resume", ci)
        full = job("deploy-production.yml", "deploy")
        self.assertIn("cancel-in-progress: false", full)
        self.assertIn("--require-full", full)

    def test_exact_run_release_evidence_is_uploaded(self):
        change = job("ci.yml", "changes")
        self.assertIn("name: fitician-release-plan", change)
        self.assertIn("overwrite: true", change)
        self.assertIn("include-hidden-files: true", change)
        gate = job("deploy-production.yml", "automatic_images_gate")
        self.assertIn("ci-release-gate.py", gate)
        self.assertIn("github.event.workflow_run.id", gate)

    def test_core_artifact_is_shared_only_within_exact_sha_run(self):
        shared = job("ci.yml", "shared")
        self.assertIn("npm run build:core", shared)
        self.assertIn("name: fitician-core-${{ github.sha }}", shared)
        self.assertIn("overwrite: true", shared)
        self.assertIn("core_artifact:", job("ci.yml", "frontend"))
        self.assertIn("actions/download-artifact@v4", job("ci.yml", "mobile"))
        frontend = (ROOT / ".github/workflows/frontend-only.yml").read_text()
        self.assertIn("if: inputs.core_artifact == ''", frontend)


class FullFrontendWorkflowTests(unittest.TestCase):
    def test_full_frontend_proof_flows_to_existing_isolated_deployer(self):
        gate = job("deploy-production.yml", "automatic_images_gate")
        frontend = job("deploy-production.yml", "deploy-frontend-component")
        self.assertIn("full_ci_run_id", gate)
        self.assertIn("release_path == 'frontend-full'", frontend)
        self.assertIn("full_ci_run_id:", frontend)
        deploy = job("deploy-component.yml", "deploy")
        self.assertIn("--require-frontend-full", deploy)
        self.assertIn("--full-ci-run-id", deploy)
        self.assertIn("GH_TOKEN: ${{ github.token }}", deploy)
        self.assertIn(
            "actions: read",
            (ROOT / ".github/workflows/deploy-component.yml").read_text(),
        )
        self.assertIn("ops/deploy-component.sh", deploy)

    def test_nested_callers_allow_read_only_release_evidence(self):
        for name in (
            "ci",
            "frontend-only",
            "backend-only",
            "deploy-production",
            "deploy-component",
        ):
            text = (ROOT / ".github/workflows" / f"{name}.yml").read_text()
            self.assertIn("permissions:\n  contents: read\n  actions: read", text)
