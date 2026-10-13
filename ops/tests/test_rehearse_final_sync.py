from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "rehearse-final-sync.py"
spec = importlib.util.spec_from_file_location("rehearse_final_sync", SCRIPT)
assert spec and spec.loader
rehearsal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearsal)


class RehearsalSafetyTests(unittest.TestCase):
    def test_resource_names_are_run_scoped(self) -> None:
        self.assertEqual(
            rehearsal.resource_names("qa-123"),
            (
                "fitician-final-sync-qa-123-source",
                "fitician-final-sync-qa-123-restore",
                "fitician_final_sync_qa_123_source",
                "fitician_final_sync_qa_123_restore",
            ),
        )

    def test_invalid_run_id_fails_before_docker_or_volumes(self) -> None:
        with (
            patch.object(
                rehearsal.subprocess,
                "run",
                side_effect=AssertionError("invalid run ID must not inspect Docker"),
            ),
            self.assertRaisesRegex(ValueError, "run ID"),
        ):
            rehearsal.rehearse("../production", rehearsal.WORK / "unused.json")


if __name__ == "__main__":
    unittest.main()
