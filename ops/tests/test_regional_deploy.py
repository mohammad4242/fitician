from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/deploy-regional.sh"
OLD = "a" * 40
NEW = "b" * 40


class RegionalDeployTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name)
        self.bin = self.app / "bin"
        self.bin.mkdir()
        self.releases = self.app / "releases"
        self.old_release = self.releases / OLD
        self.new_release = self.releases / NEW
        self.old_release.mkdir(parents=True)
        self.new_release.mkdir()
        self.old_contract = self.old_release / "compose.prod.iran.yaml"
        self.old_contract.touch()
        self.contract = self.new_release / "compose.prod.iran.yaml"
        self.contract.touch()
        (self.app / ".regional-iran-active-contract").write_text(str(self.old_contract) + "\n")
        (self.app / ".regional-germany-active-contract").write_text(
            str(self.old_contract).replace("iran", "germany") + "\n"
        )
        (self.app / ".scalability-foundation-accepted").write_text(
            "foundation_version=1\n"
            f"image_tag={OLD}\n"
            "evidence_run_id=12345\n"
            f"accepted_at={datetime.now(UTC).isoformat()}\n"
        )
        (self.app / ".env").write_text(
            f"IMAGE_TAG={OLD}\nFRONTEND_IMAGE_TAG={OLD}\n"
            f"BACKEND_API_IMAGE_TAG={OLD}\nWORKER_IMAGE_TAG={OLD}\n"
            f"AGENT_IMAGE_TAG={OLD}\nPOSTGRES_VOLUME_NAME=pg-data\n"
            "REDIS_VOLUME_NAME=redis-data\nCADDY_DATA_VOLUME_NAME=caddy-data\n"
            "CADDY_CONFIG_VOLUME_NAME=caddy-config\nAGENT_HOME_VOLUME_NAME=agent-home\n"
        )
        self.original_env_mode = (self.app / ".env").stat().st_mode & 0o777
        (self.new_release / "backup-production.sh").write_text(
            "#!/bin/sh\nprintf 'backup-production.sh\\n' >> \"$FAKE_CALLS\"\n"
            "exit ${FAKE_BACKUP_STATUS:-0}\n"
        )
        (self.new_release / "backup-production.sh").chmod(0o755)
        (self.new_release / "ops").mkdir()
        (self.new_release / "ops" / "verify-regional.sh").write_text(
            (ROOT / "ops/verify-regional.sh").read_text()
        )
        for name in ("check-db-connection-budget.py", "check-runtime-capacity.py"):
            path = self.new_release / "ops" / name
            path.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n")
            path.chmod(0o755)
        self.calls = self.app / "calls"
        self.calls.touch()
        self.tags = self.app / "running-tags"
        self.tags.write_text(
            f"FRONTEND={OLD}\nAPI={OLD}\nWORKER={OLD}\nAGENT={OLD}\n"
        )
        self.command(
            "docker",
            r'''#!/usr/bin/env bash
printf '%s\n' "$*" >> "$FAKE_CALLS"
if [[ "$*" == *" ps -q "* ]]; then
  for arg in "$@"; do service=$arg; done
  printf 'container-%s\n' "$service"
elif [[ "$*" == *"config --format json"* ]]; then
  if [[ "${COMPOSE_PROJECT_NAME:-}" == fitician_de ]]; then
    printf '{"services":{"agent-service":{"image":"example/fitician-agent:%s","volumes":[{"type":"volume","source":"agent-state","target":"/home/agent"}]}},"volumes":{"agent-state":{"name":"agent-home","external":true}}}' "$IMAGE_TAG"
  else
    printf '{"services":{"db":{"image":"postgres:18-alpine","environment":{"POSTGRES_DB":"fitician"}},"redis":{"image":"redis:8-alpine"},"caddy":{"image":"caddy:2-alpine"},"migrations":{"image":"example/fitician-backend:%s","environment":{"DATABASE_URL":"%s"}},"backend":{"image":"example/fitician-backend:%s","environment":{"DATABASE_URL":"%s"}},"backend-2":{"image":"example/fitician-backend:%s"},"scheduler":{"image":"example/fitician-backend:%s"},"food-photo-worker":{"image":"example/fitician-backend:%s"},"body-analysis-worker":{"image":"example/fitician-backend:%s"},"notification-worker":{"image":"example/fitician-backend:%s"},"frontend":{"image":"example/fitician-frontend:%s"}},"volumes":{"pg":{"name":"pg-data","external":%s},"redis":{"name":"redis-data","external":true},"caddy-data":{"name":"caddy-data","external":true},"caddy-config":{"name":"caddy-config","external":true}}}' \
      "$IMAGE_TAG" \
      "${FAKE_DATABASE_URL:-postgresql+psycopg://user:pass@db:5432/fitician}" \
      "$IMAGE_TAG" \
      "${FAKE_DATABASE_URL:-postgresql+psycopg://user:pass@db:5432/fitician}" \
      "$IMAGE_TAG" "$IMAGE_TAG" "$IMAGE_TAG" "$IMAGE_TAG" "$IMAGE_TAG" "$IMAGE_TAG" \
      "${FAKE_POSTGRES_EXTERNAL:-true}"
  fi
elif [[ "$*" == *"volume inspect"* ]]; then
  [ "${FAKE_AUTH_VOLUME_MISSING:-false}" != true ]
elif [[ "$1" == ps ]]; then
  printf 'legacy-agent\n'
elif [[ "$*" == *"com.docker.compose.service"* ]]; then
  printf 'agent-service\n'
elif [[ "$*" == *"RestartPolicy.Name"* ]]; then
  printf 'unless-stopped\n'
elif [[ "$*" == *"stop agent-service"* ]]; then
  exit "${FAKE_STOP_CANDIDATE_STATUS:-0}"
elif [[ "$*" == *"image inspect"* ]]; then
  [ "${FAKE_IMAGE_PRESENT:-true}" = true ]
elif [[ "$*" == *"Config.Image"* ]]; then
  for arg in "$@"; do id=$arg; done
  service=${id#container-}
  case "$service" in
    frontend) tag=$(awk -F= '$1=="FRONTEND" {print $2}' "$FAKE_TAGS") ;;
    backend|backend-2) tag=$(awk -F= '$1=="API" {print $2}' "$FAKE_TAGS") ;;
    scheduler|food-photo-worker|body-analysis-worker|notification-worker) tag=$(awk -F= '$1=="WORKER" {print $2}' "$FAKE_TAGS") ;;
    agent-service) tag=$(awk -F= '$1=="AGENT" {print $2}' "$FAKE_TAGS") ;;
    *) tag=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa ;;
  esac
  case "$service" in
    frontend) image=example/fitician-frontend:$tag ;;
    backend|backend-2) image=example/fitician-backend:$tag ;;
    agent-service) image=example/fitician-agent:$tag ;;
    *) image=example/fitician-backend:$tag ;;
  esac
  printf '%s\n' "$image"
elif [[ "$*" == *"State.Status"* ]]; then
  printf 'running\n'
elif [[ "$*" == *"State.Health.Status"* ]]; then
  printf '%s\n' "${FAKE_HEALTH:-healthy}"
elif [[ "$*" == *"SELECT version_num"* ]]; then
  printf '%s\n' "${FAKE_CURRENT_REVISION:-head_old}"
elif [[ "$*" == *"SELECT count(*) FROM users"* ]]; then
  printf '%s\n' "${FAKE_USER_COUNT:-3}"
elif [[ "$*" == *"alembic heads"* ]]; then
  printf 'HEADS_TAGSTATE|%s|%s\n' "$BACKEND_API_IMAGE_TAG" "$WORKER_IMAGE_TAG" >> "$FAKE_CALLS"
  printf '%s (head)\n' "${FAKE_TARGET_REVISION:-head_old}"
elif [[ "$*" == *"AGENT_SERVICE_TOKEN"* ]]; then
  exit "${FAKE_AGENT_STATUS:-0}"
elif [[ "$*" == *"run --pull never --rm --no-deps migrations alembic upgrade"* ]]; then
  printf 'MIGRATION_TAGSTATE|%s|%s\n' "$BACKEND_API_IMAGE_TAG" "$WORKER_IMAGE_TAG" >> "$FAKE_CALLS"
  [ "${FAKE_FAIL_MIGRATION:-false}" != true ]
elif [[ "$*" == *" up "* ]]; then
  if [[ "${FAKE_FAIL_NEW_UP:-false}" == true && "${IMAGE_TAG:-}" == "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" ]]; then
    exit 1
  fi
  printf 'FRONTEND=%s\nAPI=%s\nWORKER=%s\nAGENT=%s\n' \
    "${FRONTEND_IMAGE_TAG:-}" "${BACKEND_API_IMAGE_TAG:-}" \
    "${WORKER_IMAGE_TAG:-}" "${AGENT_IMAGE_TAG:-}" > "$FAKE_TAGS"
  printf 'TAGSTATE|%s|%s|%s|%s\n' \
    "${FRONTEND_IMAGE_TAG:-}" "${BACKEND_API_IMAGE_TAG:-}" \
    "${WORKER_IMAGE_TAG:-}" "${AGENT_IMAGE_TAG:-}" >> "$FAKE_CALLS"
fi
''',
        )
        self.command("curl", "#!/bin/sh\nexit ${FAKE_CURL_STATUS:-0}\n")
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "REGION": "iran",
            "DEPLOY_KIND": "full",
            "IMAGE_TAG": NEW,
            "APP_DIR": str(self.app),
            "RELEASE_DIR": str(self.new_release),
            "COMPOSE_FILE": str(self.contract),
            "COMPOSE_PROJECT_NAME": "fitician_iran",
            "FITICIAN_ENV_FILE": str(self.app / ".env"),
            "OWNER_APPROVED": "true",
            "ALLOW_SCHEMA_MIGRATIONS": "false",
            "FAKE_CALLS": str(self.calls),
            "FAKE_TAGS": str(self.tags),
        }

    def command(self, name: str, contents: str) -> None:
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def run_deploy(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)], env=self.env, capture_output=True, text=True, check=False
        )

    def test_iran_full_backs_up_before_rollout_and_persists_tags_after_verify(self) -> None:
        result = self.run_deploy()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text().splitlines()
        backup = next(index for index, line in enumerate(calls) if "backup-production.sh" in line)
        rollout = next(index for index, line in enumerate(calls) if " up -d" in line)
        self.assertLess(backup, rollout)
        self.assertEqual(
            (self.app / ".regional-iran-active-contract").read_text(), str(self.contract) + "\n"
        )
        self.assertIn("IMAGE_TAG=" + NEW, (self.app / ".env").read_text())
        self.assertEqual((self.app / ".env").stat().st_mode & 0o777, 0o600)

    def test_backup_failure_stops_before_any_rollout(self) -> None:
        self.env["FAKE_BACKUP_STATUS"] = "9"

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))
        self.assertEqual(
            (self.app / ".env").stat().st_mode & 0o777, self.original_env_mode
        )

    def test_unapproved_schema_change_stops_after_backup(self) -> None:
        self.env.update(FAKE_CURRENT_REVISION="old_head", FAKE_TARGET_REVISION="new_head")

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        calls = self.calls.read_text().splitlines()
        self.assertTrue(any("backup-production.sh" in line for line in calls))
        self.assertFalse(any(" up -d" in line for line in calls))

    def test_initial_iran_writes_scalability_marker_only_after_verified_release(self) -> None:
        (self.app / ".regional-iran-active-contract").unlink()
        (self.app / ".scalability-foundation-accepted").unlink()
        self.env.update(
            INITIAL_DEPLOY="true",
            FIRST_SCALABILITY_RELEASE_APPROVED="true",
            SCALABILITY_EVIDENCE_RUN_ID="67890",
        )

        result = self.run_deploy()

        self.assertEqual(result.returncode, 0, result.stderr)
        marker = (self.app / ".scalability-foundation-accepted").read_text()
        self.assertIn(f"image_tag={NEW}\n", marker)
        self.assertIn("evidence_run_id=67890\n", marker)

    def test_failed_initial_iran_release_does_not_accept_scalability_foundation(self) -> None:
        (self.app / ".regional-iran-active-contract").unlink()
        (self.app / ".scalability-foundation-accepted").unlink()
        self.env.update(
            INITIAL_DEPLOY="true",
            FIRST_SCALABILITY_RELEASE_APPROVED="true",
            SCALABILITY_EVIDENCE_RUN_ID="67890",
            FAKE_FAIL_NEW_UP="true",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.app / ".scalability-foundation-accepted").exists())

    def test_empty_initial_database_stops_the_new_runtime(self) -> None:
        (self.app / ".regional-iran-active-contract").unlink()
        self.env.update(INITIAL_DEPLOY="true", FAKE_USER_COUNT="0")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(" stop backend backend-2 " in line
                            for line in self.calls.read_text().splitlines()))
        self.assertFalse((self.app / ".regional-iran-active-contract").exists())

    def test_initial_germany_stops_candidate_before_restarting_legacy(self) -> None:
        (self.app / ".regional-germany-active-contract").unlink()
        contract = self.new_release / "compose.prod.germany.yaml"
        contract.touch()
        self.env.update(REGION="germany", DEPLOY_KIND="agent", INITIAL_DEPLOY="true",
                        COMPOSE_FILE=str(contract), COMPOSE_PROJECT_NAME="fitician_de",
                        FAKE_AGENT_STATUS="1")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        calls = self.calls.read_text().splitlines()
        stop = next(i for i, line in enumerate(calls) if " stop agent-service" in line)
        start = next(i for i, line in enumerate(calls) if line == "start legacy-agent")
        self.assertLess(stop, start)
        self.assertIn("update --restart=unless-stopped legacy-agent", calls)
        self.assertFalse((self.app / ".regional-germany-active-contract").exists())

    def test_initial_germany_never_starts_two_auth_volume_writers(self) -> None:
        (self.app / ".regional-germany-active-contract").unlink()
        contract = self.new_release / "compose.prod.germany.yaml"
        contract.touch()
        self.env.update(REGION="germany", DEPLOY_KIND="agent", INITIAL_DEPLOY="true",
                        COMPOSE_FILE=str(contract), COMPOSE_PROJECT_NAME="fitician_de",
                        FAKE_AGENT_STATUS="1", FAKE_STOP_CANDIDATE_STATUS="1")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("start legacy-agent", self.calls.read_text().splitlines())

    def test_approved_schema_migration_uses_candidate_images_and_manual_recovery(self) -> None:
        self.env.update(
            ALLOW_SCHEMA_MIGRATIONS="true",
            FAKE_CURRENT_REVISION="old_head",
            FAKE_TARGET_REVISION="new_head",
            FAKE_FAIL_MIGRATION="true",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manual recovery", result.stderr.lower())

        calls = self.calls.read_text().splitlines()
        migration = next(line for line in calls if line.startswith("MIGRATION_TAGSTATE|"))
        self.assertEqual(migration, f"MIGRATION_TAGSTATE|{NEW}|{NEW}")
        self.assertFalse(any(" up -d" in line for line in calls))
        stopped = next(line for line in calls if " stop caddy frontend backend " in line)
        self.assertIn("body-analysis-worker notification-worker", stopped)
        self.assertNotIn(" db", stopped)
        self.assertNotIn(" redis", stopped)

    def test_approved_schema_failure_requires_manual_recovery_without_image_rollback(self) -> None:
        self.env.update(
            ALLOW_SCHEMA_MIGRATIONS="true",
            FAKE_CURRENT_REVISION="old_head",
            FAKE_TARGET_REVISION="new_head",
            FAKE_FAIL_NEW_UP="true",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        calls = self.calls.read_text().splitlines()
        self.assertFalse(any(" up -d" in line and "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in line for line in calls))
        self.assertIn("manual recovery", result.stderr.lower())
        stopped = next(line for line in calls if " stop caddy frontend backend " in line)
        self.assertNotIn(" db", stopped)
        self.assertNotIn(" redis", stopped)

    def test_failed_iran_full_release_restores_mixed_running_versions(self) -> None:
        frontend, api, worker, agent = ("c" * 40, "d" * 40, "e" * 40, "f" * 40)
        self.tags.write_text(
            f"FRONTEND={frontend}\nAPI={api}\nWORKER={worker}\nAGENT={agent}\n"
        )
        self.env["FAKE_CURL_STATUS"] = "1"

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        states = [line for line in self.calls.read_text().splitlines() if line.startswith("TAGSTATE|")]
        self.assertEqual(len(states), 2)
        self.assertEqual(states[0], "TAGSTATE|" + "|".join([NEW, NEW, NEW, OLD]))
        self.assertEqual(states[1], "TAGSTATE|" + "|".join([frontend, api, worker, OLD]))
        self.assertEqual(
            (self.app / ".regional-iran-active-contract").read_text(),
            str(self.old_contract) + "\n",
        )
        self.assertNotIn("IMAGE_TAG=" + NEW, (self.app / ".env").read_text())

    def test_backend_component_rejects_schema_change_before_rollout(self) -> None:
        self.env.update(
            DEPLOY_KIND="backend",
            FAKE_CURRENT_REVISION="old_head",
            FAKE_TARGET_REVISION="new_head",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))
        self.assertFalse(any("backup-production.sh" in line for line in self.calls.read_text().splitlines()))
        self.assertIn(f"HEADS_TAGSTATE|{NEW}|{NEW}", self.calls.read_text().splitlines())

    def test_iran_rejects_database_url_pointing_outside_local_database_service(self) -> None:
        self.env["FAKE_DATABASE_URL"] = "postgresql+psycopg://user:pass@germany:5432/fitician"

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL", result.stderr)
        self.assertFalse(any("backup-production.sh" in line for line in self.calls.read_text().splitlines()))
        self.assertNotIn("germany", result.stderr)

    def test_iran_rejects_non_external_persistent_volume_before_rollout(self) -> None:
        self.env["FAKE_POSTGRES_EXTERNAL"] = "false"

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Compose safety", result.stderr)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))

    def test_preloaded_release_requires_every_candidate_image_before_mutation(self) -> None:
        self.env.update(IMAGE_SOURCE="preloaded", FAKE_IMAGE_PRESENT="false")

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("preloaded immutable image is missing", result.stderr)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))

    def test_preloaded_full_release_checks_infrastructure_images_before_bootstrap(self) -> None:
        (self.app / ".regional-iran-active-contract").unlink()
        self.env.update(INITIAL_DEPLOY="true", IMAGE_SOURCE="preloaded")
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        for image in ("postgres:18-alpine", "redis:8-alpine", "caddy:2-alpine"):
            self.assertIn(f"image inspect {image}", calls)
            self.assertLess(calls.index(f"image inspect {image}"), calls.index("up -d"))

    def test_iran_requires_valid_scalability_marker_before_mutation(self) -> None:
        (self.app / ".scalability-foundation-accepted").unlink()

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scalability evidence", result.stderr)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))

    def test_germany_agent_deploy_skips_database_and_checks_auth_capabilities(self) -> None:
        contract = self.new_release / "compose.prod.germany.yaml"
        contract.touch()
        (self.app / ".regional-germany-active-contract").write_text(
            str(self.old_release / "compose.prod.germany.yaml") + "\n"
        )
        (self.old_release / "compose.prod.germany.yaml").touch()
        self.env.update(
            REGION="germany",
            DEPLOY_KIND="agent",
            COMPOSE_FILE=str(contract),
            COMPOSE_PROJECT_NAME="fitician_de",
        )

        result = self.run_deploy()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text().splitlines()
        self.assertFalse(any("backup-production.sh" in line for line in calls))
        self.assertFalse(any("migrations" in line or "db " in line for line in calls))
        self.assertTrue(any("AGENT_SERVICE_TOKEN" in line for line in calls))

    def test_germany_agent_failure_rolls_back_only_agent_image(self) -> None:
        contract = self.new_release / "compose.prod.germany.yaml"
        contract.touch()
        (self.app / ".regional-germany-active-contract").write_text(
            str(self.old_release / "compose.prod.germany.yaml") + "\n"
        )
        (self.old_release / "compose.prod.germany.yaml").touch()
        self.env.update(
            REGION="germany",
            DEPLOY_KIND="agent",
            COMPOSE_FILE=str(contract),
            COMPOSE_PROJECT_NAME="fitician_de",
            FAKE_AGENT_STATUS="1",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        ups = [line for line in self.calls.read_text().splitlines() if " up -d" in line]
        self.assertEqual(len(ups), 2)
        self.assertTrue(all(line.endswith("agent-service") for line in ups))
        self.assertNotIn("AGENT_IMAGE_TAG=" + NEW, (self.app / ".env").read_text())

    def test_germany_requires_existing_external_auth_volume_before_rollout(self) -> None:
        contract = self.new_release / "compose.prod.germany.yaml"
        contract.touch()
        (self.app / ".regional-germany-active-contract").write_text(
            str(self.old_release / "compose.prod.germany.yaml") + "\n"
        )
        (self.old_release / "compose.prod.germany.yaml").touch()
        self.env.update(
            REGION="germany",
            DEPLOY_KIND="agent",
            COMPOSE_FILE=str(contract),
            COMPOSE_PROJECT_NAME="fitician_de",
            FAKE_AUTH_VOLUME_MISSING="true",
        )

        result = self.run_deploy()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(" up -d" in line for line in self.calls.read_text().splitlines()))

    def test_workflow_is_manual_and_uses_separate_region_environments(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-regional.yml").read_text()

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("production-iran", workflow)
        self.assertIn("production-germany", workflow)
        self.assertIn("ops/ci-release-gate.py", workflow)
        self.assertIn("--require-full", workflow)
        self.assertIn("ops/check-component-release.py", workflow)
        self.assertIn("frontend-full", workflow)


if __name__ == "__main__":
    unittest.main()
