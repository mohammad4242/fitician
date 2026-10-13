from __future__ import annotations

import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "final-database-snapshot.py"
spec = importlib.util.spec_from_file_location("final_database_snapshot", SCRIPT)
assert spec and spec.loader
final_snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(final_snapshot)


def freeze_manifest() -> dict[str, object]:
    writers = sorted(final_snapshot.WRITERS)
    return {
        "source_host": final_snapshot.SOURCE,
        "ingress_drained": True,
        "freeze_complete": True,
        "frozen_container_ids": {
            name: f"{index:064x}" for index, name in enumerate(writers, 1)
        },
        "preserved_services": {name: True for name in sorted(final_snapshot.PRESERVED)},
    }


class FreezeManifestTests(unittest.TestCase):
    def test_accepts_complete_unique_freeze_attestation(self) -> None:
        self.assertEqual(
            set(final_snapshot.validate_freeze_manifest(freeze_manifest())),
            final_snapshot.WRITERS,
        )

    def test_rejects_incomplete_or_duplicate_writer_ids(self) -> None:
        manifest = freeze_manifest()
        manifest["frozen_container_ids"]["scheduler"] = manifest[
            "frozen_container_ids"
        ]["backend"]

        with self.assertRaisesRegex(ValueError, "unique"):
            final_snapshot.validate_freeze_manifest(manifest)

        manifest = freeze_manifest()
        manifest["freeze_complete"] = False
        with self.assertRaisesRegex(ValueError, "freeze_complete"):
            final_snapshot.validate_freeze_manifest(manifest)

    def test_rejects_missing_preserved_database_or_agent(self) -> None:
        manifest = freeze_manifest()
        manifest["preserved_services"].pop("db")

        with self.assertRaisesRegex(ValueError, "db, redis, and agent-service"):
            final_snapshot.validate_freeze_manifest(manifest)


class SourceFreezeRuntimeTests(unittest.TestCase):
    def _runtime(self, extra: str = "") -> tuple[list[dict[str, object]], str]:
        writers = final_snapshot.validate_freeze_manifest(freeze_manifest())
        containers = []
        lines = []
        for index, (service, container_id) in enumerate(writers.items(), 1):
            containers.append(
                {
                    "Id": container_id,
                    "Config": {
                        "Labels": {
                            "com.docker.compose.project": "fitician",
                            "com.docker.compose.service": service,
                        }
                    },
                    "State": {"Running": False},
                }
            )
            lines.append(f"{container_id} exited {service}")
        for index, service in enumerate(sorted(final_snapshot.PRESERVED), 20):
            container_id = f"{index:064x}"
            lines.append(f"{container_id} running {service}")
        if extra:
            lines.append(f"{99:064x} running {extra}")
        return containers, "\n".join(lines)

    def test_verifies_all_exact_stopped_writers_and_live_dependencies(self) -> None:
        containers, inventory = self._runtime()
        with (
            patch.object(final_snapshot, "_docker_json", return_value=containers),
            patch.object(
                final_snapshot.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, inventory, ""),
            ),
        ):
            live = final_snapshot.verify_source_state(
                "fitician", freeze_manifest()["frozen_container_ids"]
            )
        self.assertEqual(set(live), final_snapshot.PRESERVED)

    def test_rejects_any_additional_running_writer(self) -> None:
        containers, inventory = self._runtime("backend")
        with (
            patch.object(final_snapshot, "_docker_json", return_value=containers),
            patch.object(
                final_snapshot.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, inventory, ""),
            ),
            self.assertRaisesRegex(RuntimeError, "unlisted or still-running"),
        ):
            final_snapshot.verify_source_state(
                "fitician", freeze_manifest()["frozen_container_ids"]
            )


class SnapshotCliTests(unittest.TestCase):
    def test_dry_run_does_not_inspect_or_contact_docker(self) -> None:
        output = io.StringIO()
        with (
            patch("sys.stdout", output),
            patch.object(
                final_snapshot.subprocess,
                "run",
                side_effect=AssertionError("unexpected Docker call"),
            ),
        ):
            result = final_snapshot.main(
                [
                    "--freeze-manifest",
                    "freeze.json",
                    "--encrypted-output",
                    "snapshot.dump.age",
                    "--metadata-output",
                    "snapshot.json",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("DRY RUN ONLY", output.getvalue())

    def test_execute_requires_exact_source_confirmation_before_any_command(
        self,
    ) -> None:
        output = io.StringIO()
        with (
            patch("sys.stderr", output),
            patch.object(
                final_snapshot.subprocess,
                "run",
                side_effect=AssertionError("unexpected Docker call"),
            ),
        ):
            result = final_snapshot.main(
                [
                    "--execute",
                    "--confirm-source",
                    "wrong-source",
                    "--freeze-manifest",
                    "freeze.json",
                    "--encrypted-output",
                    "snapshot.dump.age",
                    "--metadata-output",
                    "snapshot.json",
                ]
            )
        self.assertEqual(result, 2)
        self.assertIn("must exactly equal", output.getvalue())

    def test_snapshot_query_contains_all_counts_and_selected_fingerprints(self) -> None:
        query = final_snapshot._metadata_query({"users", "sessions"})
        self.assertIn("pg_tables", query)
        self.assertIn("users", query)
        self.assertIn("sessions", query)
        self.assertIn("row_to_json", query)
        self.assertIn("\\gexec", query)


if __name__ == "__main__":
    unittest.main()
