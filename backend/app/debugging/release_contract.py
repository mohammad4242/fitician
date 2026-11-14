"""Immutable regional release identity shared by CI, broker and deployment checks."""

from __future__ import annotations

import json
import re
from typing import Any, cast

REPOSITORY = "mohammad4242/fitician"


def _digest(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"sha256:[a-f0-9]{64}", value))


def validate_release(value: Any, *, commit: str, ci_run_id: int) -> dict[str, Any]:
    def reject() -> None:
        raise ValueError("release_manifest_invalid")

    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "version",
            "repository",
            "commit",
            "ci_run_id",
            "run_attempt",
            "images",
            "debug_runtime",
            "web_source_maps",
        }
        or len(json.dumps(value).encode()) > 16384
    ):
        reject()
    if (
        type(value["version"]) is not int
        or value["version"] != 1
        or value["repository"] != REPOSITORY
        or not isinstance(commit, str)
        or not re.fullmatch(r"[a-f0-9]{40}", commit)
        or value["commit"] != commit
        or type(ci_run_id) is not int
        or ci_run_id < 1
        or type(value["ci_run_id"]) is not int
        or value["ci_run_id"] != ci_run_id
        or type(value["run_attempt"]) is not int
        or not 1 <= value["run_attempt"] <= 1000
    ):
        reject()
    images = value["images"]
    if not isinstance(images, dict) or set(images) != {"backend", "frontend", "agent"}:
        reject()
    for role, image in images.items():
        if (
            not isinstance(image, dict)
            or set(image) != {"reference", "image_id"}
            or not isinstance(image["reference"], str)
            or not re.fullmatch(
                "mohammad4242/fitician-" + role + r"@sha256:[a-f0-9]{64}", image["reference"]
            )
            or not _digest(image["image_id"])
        ):
            reject()
    runtime = value["debug_runtime"]
    if (
        not isinstance(runtime, dict)
        or set(runtime) != {"artifact_name", "archive_sha256", "image_id", "cli_version"}
        or runtime["artifact_name"] != "fitician-debug-runtime-" + commit
        or not isinstance(runtime["archive_sha256"], str)
        or not re.fullmatch(r"[a-f0-9]{64}", runtime["archive_sha256"])
        or not _digest(runtime["image_id"])
        or runtime["cli_version"] != "0.167.2"
    ):
        reject()
    maps = value["web_source_maps"]
    if (
        not isinstance(maps, dict)
        or set(maps) != {"release", "private_layers_checked", "upload_state"}
        or maps["release"] != "fitician-web@" + commit
        or maps["private_layers_checked"] is not True
        or not isinstance(maps["upload_state"], str)
        or maps["upload_state"] not in {"uploaded", "disabled"}
    ):
        reject()
    return cast(dict[str, Any], value)
