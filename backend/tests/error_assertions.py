from collections.abc import Mapping


def assert_standard_error(
    detail: Mapping[str, object],
    *,
    code: str,
    message: str,
    retryable: bool,
    meta: Mapping[str, object] | None = None,
) -> None:
    request_id = detail.get("request_id")
    assert isinstance(request_id, str) and request_id
    assert dict(detail) == {
        "code": code,
        "message": message,
        "retryable": retryable,
        "meta": dict(meta or {}),
        "request_id": request_id,
    }
