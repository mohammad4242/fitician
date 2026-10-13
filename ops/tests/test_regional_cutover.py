from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "regional-cutover.py"
spec = importlib.util.spec_from_file_location("regional_cutover", SCRIPT)
assert spec and spec.loader
regional_cutover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(regional_cutover)


def ready_manifest() -> dict[str, object]:
    candidate_sha = "d" * 40
    return {
        "mode": "final",
        "candidate_type": "application",
        "candidate_sha": candidate_sha,
        "ci": {
            "passed": True,
            "commit_sha": candidate_sha,
            "run_id": "12345",
            "completed_at_utc": datetime.now(UTC).isoformat(),
        },
        "source": {
            "host": "mohammad@141.11.0.99",
            "live_preserved": True,
            "preserved_services": {"postgres": True, "redis": True, "agent": True},
            "frozen_container_ids": {
                "backend": "api-1",
                "backend-2": "api-2",
                "food-photo-worker": "food-1",
                "body-analysis-worker": "body-1",
                "notification-worker": "notification-1",
                "scheduler": "scheduler-1",
            },
        },
        "evidence": {
            "external_network_authenticated": True,
            "destination_https_dns_ready": True,
            "source_writes_frozen": True,
            "all_writers_drained": True,
            "agent_writes_quiesced": True,
            "database": {
                "encrypted": True,
                "sha256": "a" * 64,
                "expected_sha256": "a" * 64,
                "restore_verified": True,
                "data_validation_passed": True,
            },
            "agent": {
                "encrypted": True,
                "sha256": "b" * 64,
                "expected_sha256": "b" * 64,
                "restore_verified": True,
                "auth_validation_passed": True,
            },
        },
        "dns": {"owned_records_only": ["@", "api", "www"]},
    }


class RegionalCutoverGateTests(unittest.TestCase):
    def test_cutover_rejects_missing_external_network_auth_and_snapshot_restore(self) -> None:
        manifest = ready_manifest()
        evidence = manifest["evidence"]
        assert isinstance(evidence, dict)
        evidence["external_network_authenticated"] = False
        evidence["database"]["restore_verified"] = False
        evidence["agent"]["auth_validation_passed"] = False

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("external_network_authenticated" in error for error in errors))
        self.assertTrue(any("database.restore_verified" in error for error in errors))
        self.assertTrue(any("agent.auth_validation_passed" in error for error in errors))

    def test_rehearsal_manifest_cannot_be_promoted_to_cutover(self) -> None:
        manifest = ready_manifest()
        manifest["mode"] = "rehearsal"

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("mode must be final" in error for error in errors))

    def test_cutover_requires_exact_verified_api_and_four_consumer_ids(self) -> None:
        manifest = ready_manifest()
        source = manifest["source"]
        assert isinstance(source, dict)
        source["frozen_container_ids"].pop("scheduler")

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("frozen_container_ids" in error for error in errors))

    def test_database_checksum_mismatch_blocks_cutover(self) -> None:
        manifest = ready_manifest()
        evidence = manifest["evidence"]
        assert isinstance(evidence, dict)
        evidence["database"]["sha256"] = "c" * 64

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("database SHA-256 mismatch" in error for error in errors))

    def test_post_write_rollback_requires_freeze_and_reconciliation(self) -> None:
        manifest = ready_manifest()
        manifest["writes_started"] = True
        manifest["rollback"] = {"target_writes_frozen": False, "reconciliation_complete": False}

        errors = regional_cutover.validate_manifest(manifest, action="rollback")

        self.assertTrue(any("target_writes_frozen" in error for error in errors))
        self.assertTrue(any("reconciliation_complete" in error for error in errors))

    def test_rollback_rejects_missing_writes_started_state(self) -> None:
        manifest = ready_manifest()
        manifest["writes_started"] = False
        manifest.pop("writes_started")

        errors = regional_cutover.validate_manifest(manifest, action="rollback")

        self.assertTrue(
            any("writes_started must be explicitly true or false" in error for error in errors)
        )

    def test_cutover_requires_matching_recent_ci_evidence(self) -> None:
        manifest = ready_manifest()
        manifest["ci"]["commit_sha"] = "e" * 40

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("CI commit SHA" in error for error in errors))

    def test_cutover_rejects_stale_ci_run(self) -> None:
        manifest = ready_manifest()
        manifest["ci"]["completed_at_utc"] = (datetime.now(UTC) - timedelta(days=8)).isoformat()

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("no older than 7 days" in error for error in errors))

    def test_stable_config_can_reuse_older_ci_for_exact_stable_application_sha(self) -> None:
        manifest = ready_manifest()
        manifest["candidate_type"] = "stable-config"
        manifest["candidate_sha"] = "e" * 40
        manifest["stable_application_sha"] = manifest["ci"]["commit_sha"]
        manifest["ci"]["completed_at_utc"] = (datetime.now(UTC) - timedelta(days=90)).isoformat()

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertFalse(any("no older than 7 days" in error for error in errors))

    def test_stable_config_requires_ci_for_declared_application_sha(self) -> None:
        manifest = ready_manifest()
        manifest["candidate_type"] = "stable-config"
        manifest["candidate_sha"] = "e" * 40
        manifest["stable_application_sha"] = "f" * 40

        errors = regional_cutover.validate_manifest(manifest, action="cutover")

        self.assertTrue(any("stable_application_sha" in error for error in errors))

    def test_streaming_integrity_check_accepts_match_and_rejects_mismatch(self) -> None:
        payload = b"encrypted snapshot bytes" * 100
        expected = hashlib.sha256(payload).hexdigest()
        scratch = Path(__file__).resolve().parents[2] / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        temp = scratch / "regional-cutover-integrity-fixture.bin"
        try:
            temp.write_bytes(payload)
            self.assertEqual(regional_cutover.check_sha256(temp, expected), expected)
            with self.assertRaises(ValueError):
                regional_cutover.check_sha256(temp, "0" * 64)
        finally:
            temp.unlink(missing_ok=True)

    def test_dns_plan_changes_only_apex_and_api_a_records(self) -> None:
        snapshot = {
            "zone": "fitician.fit",
            "records": [
                {
                    "id": "r1",
                    "type": "A",
                    "name": "fitician.fit",
                    "content": "141.11.0.99",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "r2",
                    "type": "A",
                    "name": "api.fitician.fit",
                    "content": "141.11.0.99",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "r3",
                    "type": "CNAME",
                    "name": "www.fitician.fit",
                    "content": "fitician.fit",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "r4",
                    "type": "MX",
                    "name": "fitician.fit",
                    "content": "mail.example.test",
                    "priority": 10,
                },
                {
                    "id": "r5",
                    "type": "TXT",
                    "name": "fitician.fit",
                    "content": "mail-verification",
                    "ttl": 300,
                },
            ],
        }

        plan = regional_cutover.plan_dns_updates(snapshot, "203.0.113.20")

        self.assertEqual({item["record_id"] for item in plan["updates"]}, {"r1", "r2"})
        self.assertEqual(plan["preserved_unrelated_record_count"], 2)
        self.assertEqual({item["patch"]["content"] for item in plan["updates"]}, {"203.0.113.20"})

    def test_dns_plan_rejects_records_without_provider_ids(self) -> None:
        snapshot = {
            "zone": "fitician.fit",
            "records": [{"type": "A", "name": "fitician.fit", "content": "141.11.0.99"}],
        }

        with self.assertRaises(ValueError):
            regional_cutover.plan_dns_updates(snapshot, "203.0.113.20")

    def test_dns_rollback_plan_restores_only_owned_records(self) -> None:
        before = {
            "zone": "fitician.fit",
            "records": [
                {
                    "id": "a",
                    "type": "A",
                    "name": "fitician.fit",
                    "content": "141.11.0.99",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "b",
                    "type": "A",
                    "name": "api.fitician.fit",
                    "content": "141.11.0.99",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "c",
                    "type": "CNAME",
                    "name": "www.fitician.fit",
                    "content": "fitician.fit",
                    "ttl": 300,
                    "proxied": True,
                },
                {
                    "id": "mail",
                    "type": "MX",
                    "name": "fitician.fit",
                    "content": "mail.example.test",
                    "priority": 10,
                },
            ],
        }
        current = json.loads(json.dumps(before))
        current["records"][0]["content"] = "203.0.113.20"
        current["records"][1]["content"] = "203.0.113.20"
        current["records"][3]["content"] = "changed-mail.example.test"

        plan = regional_cutover.plan_dns_rollback(before, current)

        self.assertEqual({item["record_id"] for item in plan["updates"]}, {"a", "b"})
        self.assertEqual({item["patch"]["content"] for item in plan["updates"]}, {"141.11.0.99"})
        self.assertEqual(plan["preserved_unrelated_record_count"], 1)

    def test_https_plan_is_exact_pinned_read_only_probe(self) -> None:
        command = regional_cutover.https_probe_command("fitician.fit", "203.0.113.20")

        self.assertEqual(command[0], "curl")
        self.assertIn("--resolve", command)
        self.assertEqual(command[command.index("--noproxy") + 1], "*")
        self.assertIn("fitician.fit:443:203.0.113.20", command)
        self.assertEqual(command[-1], "https://fitician.fit/healthz")
        with self.assertRaises(ValueError):
            regional_cutover.https_probe_command("fitician.fit", "not-an-ip")

    def test_https_cli_is_dry_run_and_does_not_perform_a_request(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = regional_cutover.main(["https-plan", "--address", "203.0.113.20"])

        self.assertEqual(status, 0)
        self.assertIn("curl", output.getvalue())
        self.assertIn("Dry run only", output.getvalue())

    def test_restore_plan_is_shell_valid_and_limited_to_isolated_name(self) -> None:
        command = regional_cutover._restore_pipeline(
            Path("/secure/key file"), Path("/backup/snapshot.age"), "fitician-regional-restore-run1"
        )
        syntax = subprocess.run(
            ["bash", "-n", "-c", command], check=False, capture_output=True, text=True
        )

        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        self.assertIn("pg_restore --single-transaction --exit-on-error", command)
        with self.assertRaises(ValueError):
            regional_cutover._restore_pipeline(
                Path("/secure/key"), Path("/backup/snapshot.age"), "fitician-db-1"
            )


class RegionalRestoreWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = Path(__file__).resolve().parents[2] / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.encrypted = self.root / "snapshot.dump.age"
        self.payload = b"synthetic QA postgres custom archive"
        self.encrypted.write_bytes(self.payload)
        self.identity = self.root / "age.identity"
        self.identity.write_text("test-only-identity-placeholder\n")
        self.identity.chmod(0o600)
        self.snapshot = self.root / "source-snapshot.json"
        self.expected = {
            "counts": {"sessions": 0, "users": 1},
            "fingerprints": {"users": "a" * 32},
            "alembic": ["synthetic_head"],
        }
        self.snapshot.write_text(json.dumps(self.expected))
        self.actual_snapshot = self.root / "restored-state.json"
        self.actual_snapshot.write_text(
            json.dumps(
                {
                    **self.expected,
                    "tables": sorted(self.expected["counts"]),
                    "unvalidated_foreign_keys": 0,
                }
            )
        )
        self.restored = self.root / "restored.dump"
        self.ssh_calls = self.root / "ssh-calls"
        self.ssh_calls.write_text("")
        self._command("age", '#!/bin/sh\n[ "$1" = "--decrypt" ] || exit 2\ncat "$4"\n')
        fake_ssh = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
command = sys.argv[-1]
with Path(os.environ["FAKE_SSH_CALLS"]).open("a") as calls:
    calls.write(command + "\\n")
if "docker inspect" in command:
    mounts = [{
        "Type": "volume",
        "Name": "fitician_regional_restore_run1_data",
        "Destination": os.environ.get("FAKE_MOUNT", "/var/lib/postgresql"),
        "RW": True,
    }]
    print("%s|%s|%s|%s|%s" % (
        "true", os.environ.get("FAKE_NETWORK", "none"),
        os.environ.get("FAKE_PORTS", "null"), json.dumps(mounts), os.environ.get(
            "FAKE_IMAGE", "postgres:18-alpine@sha256:"
            "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15")))
elif "docker ps" in command:
    print(os.environ.get("FAKE_VOLUME_ATTACHMENTS", "fitician-regional-restore-run1"))
elif "regional-empty-check" in command:
    print(os.environ.get("FAKE_PUBLIC_TABLES", "0"))
elif "pg_restore" in command:
    Path(os.environ["FAKE_RESTORED"]).write_bytes(sys.stdin.buffer.read())
elif "regional-verify" in command:
    print(Path(os.environ["FAKE_EXPECTED"]).read_text())
else:
    raise SystemExit(2)
"""
        self._command("ssh", fake_ssh)
        self.environment = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "FAKE_RESTORED": str(self.restored),
            "FAKE_EXPECTED": str(self.actual_snapshot),
            "FAKE_SSH_CALLS": str(self.ssh_calls),
        }

    def _command(self, name: str, contents: str) -> None:
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def _restore(self) -> dict[str, object]:
        with patch.dict(os.environ, self.environment, clear=True):
            return regional_cutover.execute_restore(
                identity_file=self.identity,
                encrypted_file=self.encrypted,
                expected_snapshot=self.snapshot,
                expected_sha256=hashlib.sha256(self.payload).hexdigest(),
                container="fitician-regional-restore-run1",
                confirmation="fitician-regional-restore-run1",
            )

    def _restore_args(self) -> list[str]:
        return [
            "restore-plan",
            "--identity-file",
            str(self.identity),
            "--encrypted-file",
            str(self.encrypted),
            "--expected-snapshot",
            str(self.snapshot),
            "--sha256",
            hashlib.sha256(self.payload).hexdigest(),
            "--restore-container",
            "fitician-regional-restore-run1",
        ]

    def test_restore_cli_dry_run_does_not_contact_destination(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            status = regional_cutover.main(self._restore_args())

        self.assertEqual(status, 0)
        self.assertIn("DRY RUN ONLY", output.getvalue())
        self.assertEqual(self.ssh_calls.read_text(), "")
        self.assertFalse(self.restored.exists())

    def test_execute_requires_matching_target_confirmation_before_ssh(self) -> None:
        error = io.StringIO()
        with redirect_stderr(error):
            status = regional_cutover.main(
                self._restore_args() + ["--execute", "--confirm-target", "wrong-container"]
            )

        self.assertEqual(status, 2)
        self.assertIn("exactly match", error.getvalue())
        self.assertEqual(self.ssh_calls.read_text(), "")

    def test_synthetic_isolated_restore_streams_and_compares_snapshot_evidence(self) -> None:
        result = self._restore()

        self.assertEqual(self.restored.read_bytes(), self.payload)
        self.assertEqual(result["tables_verified"], 2)
        self.assertEqual(result["fingerprints_verified"], 1)
        self.assertFalse(result["age_identity_sent_to_destination"])
        self.assertFalse(result["volumes_deleted"])
        remote_commands = self.ssh_calls.read_text()
        self.assertNotIn(str(self.identity), remote_commands)
        self.assertIn("--single-transaction --exit-on-error", remote_commands)
        self.assertNotIn("volume rm", remote_commands)

    def test_restore_refuses_nonempty_target_before_streaming_archive(self) -> None:
        self.environment["FAKE_PUBLIC_TABLES"] = "1"

        with self.assertRaisesRegex(RuntimeError, "contains public tables"):
            self._restore()

        self.assertFalse(self.restored.exists())
        self.assertNotIn("pg_restore", self.ssh_calls.read_text())

    def test_restore_refuses_networked_target_before_streaming_archive(self) -> None:
        self.environment["FAKE_NETWORK"] = "bridge"

        with self.assertRaisesRegex(RuntimeError, "network=none"):
            self._restore()

        self.assertFalse(self.restored.exists())

    def test_restore_rejects_legacy_postgres_data_mount_for_postgres18(self) -> None:
        with (
            patch.dict(self.environment, {"FAKE_MOUNT": "/var/lib/postgresql/data"}),
            self.assertRaisesRegex(RuntimeError, "PostgreSQL 18"),
        ):
            self._restore()
        self.assertEqual(self.ssh_calls.read_text().count("pg_restore"), 0)

    def test_restore_rejects_nonpinned_or_wrong_postgres18_image(self) -> None:
        for image in (
            "postgres:18-evil@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
            "postgres:18-alpine@sha256:" + "0" * 64,
        ):
            with self.subTest(image=image), patch.dict(self.environment, {"FAKE_IMAGE": image}):
                with self.assertRaisesRegex(RuntimeError, "pinned PostgreSQL 18"):
                    self._restore()
        self.assertEqual(self.ssh_calls.read_text().count("pg_restore"), 0)

    def test_restore_rejects_unexpected_or_missing_public_tables(self) -> None:
        for tables in (["sessions", "unexpected", "users"], ["users"]):
            with self.subTest(tables=tables):
                self.actual_snapshot.write_text(
                    json.dumps(
                        {
                            **self.expected,
                            "tables": tables,
                            "unvalidated_foreign_keys": 0,
                        }
                    )
                )
                with self.assertRaisesRegex(RuntimeError, "table inventory"):
                    self._restore()

    def test_restore_refuses_published_database_port_before_streaming_archive(self) -> None:
        self.environment["FAKE_PORTS"] = json.dumps(
            {"5432/tcp": [{"HostIp": "0.0.0.0", "HostPort": "5432"}]}
        )

        with self.assertRaisesRegex(RuntimeError, "no published ports"):
            self._restore()

        self.assertFalse(self.restored.exists())

    def test_restore_refuses_volume_attached_to_another_container(self) -> None:
        self.environment["FAKE_VOLUME_ATTACHMENTS"] = (
            "fitician-regional-restore-run1\nother-container"
        )

        with self.assertRaisesRegex(RuntimeError, "attached only"):
            self._restore()

        self.assertFalse(self.restored.exists())

    def test_restore_fails_if_post_restore_fingerprint_does_not_match(self) -> None:
        actual = json.loads(self.actual_snapshot.read_text())
        actual["fingerprints"]["users"] = "f" * 32
        self.actual_snapshot.write_text(json.dumps(actual))

        with self.assertRaisesRegex(RuntimeError, "fingerprints"):
            self._restore()

        self.assertEqual(self.restored.read_bytes(), self.payload)


if __name__ == "__main__":
    unittest.main()
