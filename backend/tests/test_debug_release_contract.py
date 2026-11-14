import pytest


def manifest():
    return {
        "version": 1,
        "repository": "mohammad4242/fitician",
        "commit": "a" * 40,
        "ci_run_id": 123,
        "run_attempt": 1,
        "images": {
            kind: {
                "reference": f"mohammad4242/fitician-{kind}@sha256:" + "b" * 64,
                "image_id": "sha256:" + "c" * 64,
            }
            for kind in ("backend", "frontend", "agent")
        },
        "debug_runtime": {
            "artifact_name": "fitician-debug-runtime-" + "a" * 40,
            "archive_sha256": "d" * 64,
            "image_id": "sha256:" + "e" * 64,
            "cli_version": "0.167.2",
        },
        "web_source_maps": {
            "release": "fitician-web@" + "a" * 40,
            "private_layers_checked": True,
            "upload_state": "uploaded",
        },
    }


def test_release_contract_requires_exact_content_addressed_images_and_runtime_proof():
    from app.debugging.release_contract import validate_release

    value = manifest()
    assert validate_release(value, commit="a" * 40, ci_run_id=123) == value
    for change in [
        {"commit": "f" * 40},
        {"ci_run_id": 456},
        {"images": {"backend": value["images"]["backend"]}},
        {"arbitrary_command": "ssh production"},
    ]:
        with pytest.raises(ValueError):
            validate_release({**value, **change}, commit="a" * 40, ci_run_id=123)
    for reference in [
        "mohammad4242/fitician-backend:main",
        "untrusted/fitician-backend@sha256:" + "b" * 64,
    ]:
        changed = manifest()
        changed["images"]["backend"]["reference"] = reference
        with pytest.raises(ValueError):
            validate_release(changed, commit="a" * 40, ci_run_id=123)


def test_incomplete_private_source_map_gate_and_mismatched_runtime_artifact_are_rejected():
    from app.debugging.release_contract import validate_release

    for area, field, value in [
        ("debug_runtime", "artifact_name", "other-artifact"),
        ("debug_runtime", "cli_version", "unverified"),
        ("web_source_maps", "private_layers_checked", False),
        ("web_source_maps", "upload_state", "failed"),
    ]:
        changed = manifest()
        changed[area][field] = value
        with pytest.raises(ValueError):
            validate_release(changed, commit="a" * 40, ci_run_id=123)
