"""All production actions must stay unreachable during regional qualification."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_JOBS = {
    "deploy-production.yml": (
        "automatic_images_gate", "automatic_deploy_gate", "deploy",
        "deploy-frontend-component", "deploy-backend-component",
    ),
    "deploy-component.yml": ("deploy",),
    "deploy-regional.yml": ("deploy",),
    "deploy-caddy-production.yml": ("deploy-caddy-production",),
    "frontend-appearance-release.yml": ("frontend-release",),
    "frontend-only.yml": ("deploy-frontend-production",),
    "backend-only.yml": ("deploy-backend-production",),
}


class CDSafetyTests(unittest.TestCase):
    def test_all_production_jobs_are_unconditionally_disabled(self):
        for filename, names in DEPLOY_JOBS.items():
            text = (ROOT / ".github/workflows" / filename).read_text()
            for name in names:
                with self.subTest(workflow=filename, job=name):
                    match = re.search(
                        r"(?ms)^  " + re.escape(name) + r":\n(.*?)(?=^  [\w-]+:|\Z)", text
                    )
                    self.assertIsNotNone(match)
                    body = match.group(1)
                    condition = re.search(r"(?m)^    if: (.*)$", body)
                    self.assertIsNotNone(condition)
                    if condition.group(1) == ">-":
                        expression = re.search(
                            r"(?m)^    if: >-\n((?:      [^\n]*\n)+)", body
                        ).group(1).strip()
                        self.assertTrue(expression.startswith("false && ("))
                        self.assertTrue(expression.endswith(")"))
                    else:
                        self.assertEqual(condition.group(1), "${{ false }}")

    def test_no_automatic_production_trigger_or_object_store_dependency(self):
        production = (ROOT / ".github/workflows/deploy-production.yml").read_text()
        self.assertNotIn("  workflow_run:", production)
        for filename in ("ci.yml", "frontend-only.yml"):
            workflow = (ROOT / ".github/workflows" / filename).read_text()
            self.assertNotIn('"${MEDIA_BASE%/}/public/landing/videos/landfilm.mp4"', workflow)
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            self.assertNotRegex(path.read_text().lower(), r"arvan|arvancloud")
