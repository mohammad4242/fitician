from pathlib import Path

from app.config import Settings
from app.media.private_migration import build_private_manifest


def test_private_manifest_includes_only_current_local_references(tmp_path: Path) -> None:
    root = tmp_path / "body"
    current = root / "aa" / "photo.jpg"
    current.parent.mkdir(parents=True)
    current.write_bytes(b"body")
    (root / "bb").mkdir()
    (root / "bb" / "unknown.jpg").write_bytes(b"unknown")
    settings = Settings(body_photo_storage_root=root)

    manifest, missing = build_private_manifest(
        settings,
        {
            "body-photos": {"aa/photo.jpg"},
            "food-photos": set(),
            "profile-photos": set(),
            "nutrition-labs": set(),
        },
        categories=("body-photos",),
    )

    assert [record.object_key for record in manifest] == ["private/body-photos/aa/photo.jpg"]
    assert missing == ()
