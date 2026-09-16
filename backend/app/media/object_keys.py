"""Provider-neutral object keys derived from existing Fitician media paths."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

PUBLIC_PATH_PREFIX = "/media/"
PRIVATE_SCOPES = frozenset(
    {"body-photos", "food-photos", "profile-photos", "nutrition-labs"}
)


class MediaObjectKeyError(ValueError):
    pass


def _safe_relative_path(value: str) -> PurePosixPath:
    if not value or value.strip() != value or "\\" in value or "%" in value:
        raise MediaObjectKeyError("Media key must be a normalized relative path")
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise MediaObjectKeyError("Provider URLs are not stable media keys")
    if unquote(value) != value or "//" in value:
        raise MediaObjectKeyError("Encoded or empty media-key segments are not allowed")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise MediaObjectKeyError("Media key must not escape its namespace")
    return path


def public_object_key(public_path: str) -> str:
    if not public_path.startswith(PUBLIC_PATH_PREFIX):
        raise MediaObjectKeyError("Public media path must start with /media/")
    relative = _safe_relative_path(public_path.removeprefix(PUBLIC_PATH_PREFIX))
    return f"public/{relative.as_posix()}"


def private_object_key(scope: str, storage_key: str) -> str:
    if scope not in PRIVATE_SCOPES:
        raise MediaObjectKeyError("Unknown private media scope")
    relative = _safe_relative_path(storage_key)
    return f"private/{scope}/{relative.as_posix()}"
