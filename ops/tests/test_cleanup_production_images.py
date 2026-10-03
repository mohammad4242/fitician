from __future__ import annotations

import importlib.util
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "cleanup-production-images.py"


class CleanupImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location("cleanup_images", SCRIPT)
        self.assertIsNotNone(spec)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.now = datetime.now(UTC)
        self.repository = "example/fitician-backend"
        self.current = "a" * 40
        self.previous = "b" * 40

    def image(self, tag: str, identity: str = "sha256:old", age: int = 48) -> dict:
        return {
            "Id": identity,
            "RepoTags": [f"{self.repository}:{tag}"],
            "Created": (self.now - timedelta(hours=age)).isoformat(),
        }

    def select(self, images: list, active: set | None = None) -> list:
        return self.module.cleanup_candidates(
            images, active or set(), {self.current, self.previous}, {self.repository}, self.now, 24
        )

    def test_preserves_current_previous_and_container_referenced_images(self) -> None:
        images = [
            self.image(self.current),
            self.image(self.previous),
            self.image("c" * 40, identity="sha256:active"),
        ]
        self.assertEqual(self.select(images, {"sha256:active"}), [])

    def test_selects_only_old_unused_fitician_immutable_images(self) -> None:
        old = self.image("d" * 40)
        self.assertEqual(self.select([old]), [old])
        self.assertEqual(self.select([self.image("latest"), self.image("e" * 40, age=1)]), [])

    def test_preserves_foreign_and_mixed_repository_images(self) -> None:
        image = self.image("f" * 40)
        image["RepoTags"].append("postgres:18-alpine")
        self.assertEqual(self.select([image]), [])

    def test_dangling_and_duplicate_ids_are_safe(self) -> None:
        image = self.image("f" * 40)
        self.assertEqual(self.select([image, image]), [image])
        self.assertEqual(
            self.select([{"Id": "x", "RepoTags": None, "Created": self.now.isoformat()}]), []
        )

    def test_recent_two_images_preserve_component_rollback(self) -> None:
        images = [
            self.image("c" * 40, identity="c", age=1),
            self.image("d" * 40, identity="d", age=2),
            self.image("e" * 40, identity="e", age=3),
        ]
        self.assertEqual(
            self.module.recent_image_shas(images, {self.repository}), {"c" * 40, "d" * 40}
        )

    def test_requires_two_explicit_rollback_shas(self) -> None:
        with self.assertRaises(ValueError):
            self.module.cleanup_candidates(
                [], set(), {self.current}, {self.repository}, self.now, 24
            )


if __name__ == "__main__":
    unittest.main()
