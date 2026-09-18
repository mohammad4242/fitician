from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import Settings
from tests.error_assertions import assert_standard_error

ORIGIN = {"Origin": "http://localhost:5173"}


def test_forgot_password_rate_limit_is_generic(
    client: TestClient,
    test_settings: Settings,
) -> None:
    test_settings.auth_forgot_password_ip_limit = 1
    payload = {"email": "unknown@example.com"}

    first = client.post("/api/v1/auth/forgot-password", headers=ORIGIN, json=payload)
    limited = client.post("/api/v1/auth/forgot-password", headers=ORIGIN, json=payload)

    assert first.status_code == 202
    assert limited.status_code == 429
    assert_standard_error(
        limited.json()["detail"],
        code="AUTH_RATE_LIMITED",
        message="درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.",
        retryable=True,
    )


def test_phone_send_rate_limit_does_not_reveal_account_state(
    client: TestClient,
    test_settings: Settings,
) -> None:
    test_settings.auth_phone_otp_ip_limit = 1

    first = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": "09123456789"},
    )
    limited = client.post(
        "/api/v1/auth/phone/send-otp",
        headers=ORIGIN,
        json={"phone_number": "09351234567"},
    )

    assert first.status_code == 202
    assert limited.status_code == 429
    assert_standard_error(
        limited.json()["detail"],
        code="AUTH_RATE_LIMITED",
        message="درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.",
        retryable=True,
    )


def test_web_password_login_rate_limit_is_shared_with_the_api(
    client: TestClient,
    test_settings: Settings,
) -> None:
    test_settings.auth_password_ip_limit = 1

    first = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "unknown-login@example.com", "password": "wrong password"},
    )
    limited = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "unknown-login@example.com", "password": "wrong password"},
    )

    assert first.status_code == 401
    assert limited.status_code == 429
    assert_standard_error(
        limited.json()["detail"],
        code="AUTH_RATE_LIMITED",
        message="درخواست‌های ورود زیاد است. کمی بعد دوباره تلاش کنید.",
        retryable=True,
    )


def test_auth_uses_shared_redis_limiter_before_database_fallback(
    client: TestClient,
) -> None:
    calls: list[dict[str, object]] = []

    class StubLimiter:
        async def consume(self, **kwargs: object) -> SimpleNamespace:
            calls.append(kwargs)
            return SimpleNamespace(
                allowed=len(calls) == 1,
                retry_after_seconds=17,
            )

    client.app.state.rate_limiter = StubLimiter()
    response = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "distributed@example.com", "password": "wrong password"},
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert [call["namespace"] for call in calls] == ["auth", "auth"]
