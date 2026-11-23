from app.sentry import sanitize_event


def test_short_sdk_filename_uses_only_sanitized_repository_absolute_path():
    frames = [
        {
            "filename": "case.py",
            "abs_path": "/home/private-user/repo/backend/app/debugging/case.py",
            "function": "operation",
            "lineno": 4,
            "vars": {"token": "private-fixture"},
        },
        {
            "filename": "case.py",
            "abs_path": "/home/private-user/secrets.env",
            "function": "external",
            "lineno": 8,
        },
        {
            "filename": "case.py",
            "abs_path": "/home/private-user/repo/app/../secrets.env",
            "function": "unsafe",
            "lineno": 9,
        },
    ]
    result = sanitize_event(
        {"exception": {"values": [{"type": "ValueError", "stacktrace": {"frames": frames}}]}}, {}
    )
    clean = result["exception"]["values"][0]["stacktrace"]["frames"]
    assert clean[0]["filename"] == "app/debugging/case.py"
    assert clean[0]["function"] == "operation" and clean[0]["lineno"] == 4
    assert "filename" not in clean[1] and "filename" not in clean[2]
    assert "private-user" not in str(result) and "private-fixture" not in str(result)
    assert "abs_path" not in str(result) and "vars" not in str(result)
