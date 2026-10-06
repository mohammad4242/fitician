from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = "a" * 40
NEW = "b" * 40


class ComponentDeployTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "bin").mkdir()
        (self.root / "compose.prod.yaml").touch()
        (self.root / ".env").write_text("IMAGE_TAG=" + OLD + "\nKEEP=yes\n")
        (self.root / ".scalability-foundation-accepted").write_text(
            f"foundation_version=1\nimage_tag={OLD}\nevidence_run_id=123\n"
            "accepted_at=2026-09-18T00:00:00Z\n"
        )
        (self.root / "calls").touch()
        self.env = {
            **os.environ,
            "PATH": str(self.root / "bin") + ":" + os.environ["PATH"],
            "VPS_APP_DIR": str(self.root),
            "IMAGE_TAG": NEW,
            "COMPONENT": "frontend",
            "PREVIOUS_IMAGE_TAG": OLD,
            "EXPECTED_CURRENT_TAG": OLD,
            "FAKE_STATE_DIR": str(self.root),
        }
        self.command(
            "docker",
            """#!/bin/bash
printf 'tag=%s %s\n' \
  "${FRONTEND_IMAGE_TAG:-${BACKEND_API_IMAGE_TAG:-}}" "$*" >> "$FAKE_STATE_DIR/calls"
case "$*" in
  *' ps -aq'*) printf '%s\n' frontend backend backend-2 scheduler redis db agent-service ;;
  *' ps -q '*)
    for arg do service=$arg; done
    printf '%s\n' "$service" ;;
  *'inspect'*'com.docker.compose.service'*'RestartCount'*)
    for arg do service=$arg; done
    restarts=0
    if [ "$service" = redis ] && [ -f "$FAKE_STATE_DIR/new" ] &&
       [ "${FAKE_UNRELATED_RESTART:-}" = yes ]; then restarts=1; fi
    printf '%s:%s:%s:started\n' "$service" "$service" "$restarts" ;;
  *'inspect'*'com.docker.compose.service'*)
    for arg do service=$arg; done
    printf '%s\n' "$service" ;;
  *Config.Image*)
    for arg do service=$arg; done
    tag=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    if [ -f "$FAKE_STATE_DIR/new" ]; then tag=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; fi
    if [ "$service" = frontend ]; then kind=frontend; else kind=backend; fi
    printf 'example/fitician-%s:%s\n' "$kind" "$tag" ;;
  *State.Health.Status*) printf '%s\n' "${FAKE_HEALTH:-healthy}" ;;
  *' exec -T db '*) printf '%s\n' old_revision ;;
  run*alembic*) printf '%s (head)\n' "${FAKE_TARGET_REVISION:-old_revision}" ;;
  *' up '* )
    case "${FRONTEND_IMAGE_TAG:-${BACKEND_API_IMAGE_TAG:-}}" in
      bbbbbbbb*) touch "$FAKE_STATE_DIR/new"; [ "${FAKE_UP_FAIL:-}" != yes ] ;;
      *) rm -f "$FAKE_STATE_DIR/new" ;;
    esac ;;
esac
""",
        )
        self.command(
            "curl",
            """#!/bin/sh
[ "${FAKE_SMOKE_FAIL:-}" != yes ] || exit 22
printf '<meta name="enamad" content="74257848" />'
""",
        )

    def command(self, name, text):
        path = self.root / "bin" / name
        path.write_text(text)
        path.chmod(0o755)

    def run_deploy(self):
        return subprocess.run(
            ["bash", str(ROOT / "ops/deploy-component.sh")],
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_frontend_success_persists_only_frontend_tag(self):
        preserved = {
            "BACKEND_API_IMAGE_TAG": "c" * 40,
            "WORKER_IMAGE_TAG": "d" * 40,
            "AGENT_IMAGE_TAG": "e" * 40,
            "DATABASE_IMAGE_TAG": "f" * 40,
        }
        with (self.root / ".env").open("a") as stream:
            for key, value in preserved.items():
                stream.write(f"{key}={value}\n")
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        for key, value in preserved.items():
            self.assertIn(f"{key}={value}", (self.root / ".env").read_text())
        self.assertIn("FRONTEND_IMAGE_TAG=" + NEW, (self.root / ".env").read_text())
        self.assertIn("IMAGE_TAG=" + OLD, (self.root / ".env").read_text())
        calls = (self.root / "calls").read_text()
        self.assertIn("--no-deps", calls)
        self.assertNotIn("migrations", calls)
        self.assertNotIn("--remove-orphans", calls)

    def test_backend_updates_both_replicas_without_migration(self):
        self.env["COMPONENT"] = "backend"
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.root / "calls").read_text()
        self.assertIn("backend backend-2", calls)
        self.assertNotIn("upgrade head", calls)
        self.assertIn("BACKEND_API_IMAGE_TAG=" + NEW, (self.root / ".env").read_text())

    def test_public_failure_rolls_back_only_component(self):
        self.env["FAKE_SMOKE_FAIL"] = "yes"
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        calls = (self.root / "calls").read_text().splitlines()
        ups = [line for line in calls if " up " in line]
        self.assertEqual(len(ups), 2)
        self.assertTrue(all(line.endswith("frontend") for line in ups))
        self.assertNotIn("FRONTEND_IMAGE_TAG=" + NEW, (self.root / ".env").read_text())

    def test_up_failure_and_unhealthy_component_roll_back(self):
        for value in ("up", "health"):
            with self.subTest(value=value):
                self.env["FAKE_UP_FAIL"] = "yes" if value == "up" else "no"
                self.env["FAKE_HEALTH"] = (
                    "unhealthy" if value == "health" else "healthy"
                )
                (self.root / "calls").write_text("")
                result = self.run_deploy()
                self.assertNotEqual(result.returncode, 0)
                ups = [
                    line
                    for line in (self.root / "calls").read_text().splitlines()
                    if " up " in line
                ]
                self.assertEqual(len(ups), 2)
                self.assertFalse((self.root / "new").exists())

    def test_unrelated_restart_is_detected_even_when_id_is_unchanged(self):
        self.env["FAKE_UNRELATED_RESTART"] = "yes"
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unrelated container", result.stderr)
        self.assertFalse((self.root / "new").exists())

    def test_backend_pending_schema_blocks_before_rollout(self):
        self.env.update(COMPONENT="backend", FAKE_TARGET_REVISION="new_revision")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(" up ", (self.root / "calls").read_text())

    def test_invalid_scalability_acceptance_blocks_component_release(self):
        (self.root / ".scalability-foundation-accepted").write_text("unapproved\n")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(" up ", (self.root / "calls").read_text())

    def test_stale_baseline_refused_before_rollout(self):
        self.env["EXPECTED_CURRENT_TAG"] = "c" * 40
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(" up ", (self.root / "calls").read_text())


if __name__ == "__main__":
    unittest.main()
