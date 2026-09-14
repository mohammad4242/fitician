from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.errors import (
    CORRELATION_ID_HEADER,
    build_error_detail,
    build_error_response,
    create_request_id,
    normalize_validation_errors,
)


def test_known_error_has_safe_complete_envelope() -> None:
    detail = build_error_detail(
        503,
        {
            "code": "BODY_ANALYSIS_PROVIDER_UNAVAILABLE",
            "message": "provider secret must never reach the client",
            "meta": {
                "retry_after_seconds": 30,
                "provider_secret": "do-not-leak",
            },
        },
        request_id="req-contract-1",
    )

    assert detail["code"] == "BODY_ANALYSIS_PROVIDER_UNAVAILABLE"
    assert detail["retryable"] is True
    assert detail["request_id"] == "req-contract-1"
    assert detail["meta"] == {"retry_after_seconds": 30}
    assert "provider secret" not in str(detail)
    assert "stack" not in str(detail).lower()


def test_unknown_server_error_is_not_explained_by_internal_detail() -> None:
    detail = build_error_detail(
        500,
        {
            "message": "sql password=private-value at /srv/fitician/app.py",
            "query": "SELECT * FROM private_notes",
        },
        request_id="req-contract-2",
    )

    assert detail["code"] == "INTERNAL_SERVER_ERROR"
    assert detail["message"] == "خطای غیرمنتظره‌ای رخ داد. دوباره تلاش کنید."
    assert detail["retryable"] is True
    assert detail["request_id"] == "req-contract-2"
    assert "private-value" not in str(detail)
    assert "private_notes" not in str(detail)
    assert "/srv/fitician" not in str(detail)


def test_validation_errors_become_safe_field_contract() -> None:
    detail = normalize_validation_errors(
        [
            {
                "type": "missing",
                "loc": ["body", "weight_kg"],
                "msg": "Field required",
                "input": "secret should not be echoed",
            },
            {
                "type": "greater_than",
                "loc": ["body", "training_days"],
                "msg": "Input should be greater than 0",
            },
        ],
        request_id="req-contract-3",
    )

    assert detail == {
        "code": "VALIDATION_ERROR",
        "message": "اطلاعات واردشده را بررسی و موارد مشخص‌شده را اصلاح کنید.",
        "retryable": False,
        "fields": [
            {"field": "weight_kg", "code": "required", "message": "وزن وارد نشده است."},
            {
                "field": "training_days",
                "code": "greater_than",
                "message": "تعداد روزهای تمرین باید در بازه مجاز باشد.",
            },
        ],
        "meta": {},
        "request_id": "req-contract-3",
    }
    assert "secret should not be echoed" not in str(detail)


def test_response_normalizes_http_exception_and_preserves_retry_header() -> None:
    response = build_error_response(
        HTTPException(
            status_code=429,
            detail={
                "code": "AUTH_RATE_LIMITED",
                "message": "safe rate limit message",
                "retry_after_seconds": 17,
            },
            headers={"Retry-After": "17"},
        ),
        request_id="req-contract-4",
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert response.headers[CORRELATION_ID_HEADER] == "req-contract-4"
    assert response.body


def test_known_legacy_string_detail_gets_a_stable_domain_code() -> None:
    detail = build_error_detail(
        409,
        "Workout plan generation is already in progress",
        request_id="req-contract-domain-1",
    )

    assert detail == {
        "code": "WORKOUT_GENERATION_IN_PROGRESS",
        "message": "ساخت برنامه تمرینی در حال انجام است. بعداً دوباره بررسی کنید.",
        "retryable": False,
        "meta": {},
        "request_id": "req-contract-domain-1",
    }


def test_request_id_accepts_safe_value_and_replaces_invalid_value() -> None:
    assert create_request_id("mobile-123") == "mobile-123"
    generated = create_request_id("not safe/with spaces")
    assert generated != "not safe/with spaces"
    assert len(generated) >= 16


def test_api_adds_correlation_id_to_success_and_http_error(client: TestClient) -> None:
    def conflict() -> None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "WORKOUT_GENERATION_IN_PROGRESS",
                "meta": {"current_state": "generating", "private_note": "hidden"},
            },
        )

    client.app.add_api_route("/test-error-contract-conflict", conflict, methods=["GET"])
    response = client.get(
        "/test-error-contract-conflict",
        headers={CORRELATION_ID_HEADER: "backend-contract-1"},
    )

    assert response.status_code == 409
    assert response.headers[CORRELATION_ID_HEADER] == "backend-contract-1"
    assert response.json()["detail"] == {
        "code": "WORKOUT_GENERATION_IN_PROGRESS",
        "message": "ساخت برنامه تمرینی در حال انجام است. بعداً دوباره بررسی کنید.",
        "retryable": False,
        "meta": {"current_state": "generating"},
        "request_id": "backend-contract-1",
    }


def test_api_normalizes_validation_and_auth_errors(client: TestClient) -> None:
    validation = client.post(
        "/api/v1/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            CORRELATION_ID_HEADER: "backend-contract-2",
        },
        json={"email": "invalid", "password": "secret7"},
    )
    assert validation.status_code == 422
    assert validation.headers[CORRELATION_ID_HEADER] == "backend-contract-2"
    validation_detail = validation.json()["detail"]
    assert validation_detail["code"] == "VALIDATION_ERROR"
    assert validation_detail["retryable"] is False
    assert validation_detail["request_id"] == "backend-contract-2"
    assert validation_detail["fields"]
    assert all("input" not in field for field in validation_detail["fields"])
    assert "secret7" not in validation.text

    auth = client.get(
        "/api/v1/auth/me",
        headers={CORRELATION_ID_HEADER: "backend-contract-3"},
    )
    assert auth.status_code == 401
    assert auth.headers[CORRELATION_ID_HEADER] == "backend-contract-3"
    assert auth.json()["detail"]["code"] == "AUTHENTICATION_REQUIRED"
    assert auth.json()["detail"]["request_id"] == "backend-contract-3"


def test_cors_allows_and_exposes_correlation_id(client: TestClient) -> None:
    response = client.options(
        "/api/v1/products",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Correlation-ID",
        },
    )

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers["access-control-allow-headers"]

    actual = client.get(
        "/api/v1/products",
        headers={"Origin": "http://localhost:5173"},
    )
    assert actual.status_code == 200
    assert CORRELATION_ID_HEADER in actual.headers["access-control-expose-headers"]


def test_unhandled_exception_returns_redacted_internal_error(client: TestClient) -> None:
    def crash() -> None:
        raise RuntimeError("private token and SQL query must stay server-side")

    client.app.add_api_route("/test-error-contract-crash", crash, methods=["GET"])
    safe_client = TestClient(client.app, raise_server_exceptions=False)
    response = safe_client.get(
        "/test-error-contract-crash",
        headers={CORRELATION_ID_HEADER: "backend-contract-5"},
    )

    assert response.status_code == 500
    assert response.headers[CORRELATION_ID_HEADER] == "backend-contract-5"
    assert response.json()["detail"] == {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "خطای غیرمنتظره‌ای رخ داد. دوباره تلاش کنید.",
        "retryable": True,
        "meta": {},
        "request_id": "backend-contract-5",
    }
    assert "private token" not in response.text
