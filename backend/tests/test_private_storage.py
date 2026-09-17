from pathlib import Path

from app.config import Settings
from app.media.private_storage import build_private_storage


def test_local_private_storage_keeps_scope_relative_keys(tmp_path: Path) -> None:
    settings = Settings(
        body_photo_storage_root=tmp_path / "body",
        food_photo_storage_root=tmp_path / "food",
        profile_photo_storage_root=tmp_path / "profile",
        nutrition_lab_storage_root=tmp_path / "labs",
    )
    storage = build_private_storage(settings)

    stored = storage.put("body-photos", b"body", ".jpg", "image/jpeg")

    assert stored.key.count("/") == 1
    assert storage.read("body-photos", stored.key) == b"body"
    storage.delete("body-photos", stored.key)
    assert storage.exists("body-photos", stored.key) is False
