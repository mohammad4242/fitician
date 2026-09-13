from types import TracebackType
from typing import Any

import httpx
import pytest

from app.auth import providers
from app.auth.providers import FarazSmsProvider, SmtpEmailProvider
from app.config import Settings


class FakeHttpClient:
    request_url: str | None = None
    request_headers: dict[str, str] | None = None
    request_json: dict[str, object] | None = None

    def __init__(self, **_kwargs: object) -> None:
        pass

    def __enter__(self) -> "FakeHttpClient":
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        pass

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        type(self).request_url = url
        type(self).request_headers = headers
        type(self).request_json = json
        return httpx.Response(
            201,
            json={
                "status": "success",
                "data": 0,
                "messages": "sent",
            },
            request=httpx.Request("POST", url),
        )


class ApplicationFailureHttpClient(FakeHttpClient):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        type(self).request_url = url
        type(self).request_headers = headers
        type(self).request_json = json
        return httpx.Response(
            201,
            json={
                "status": "failed",
                "data": 1,
                "messages": "failed test-api-key 123456",
            },
            request=httpx.Request("POST", url),
        )


class HttpFailureHttpClient(FakeHttpClient):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        type(self).request_url = url
        type(self).request_headers = headers
        type(self).request_json = json
        return httpx.Response(
            503,
            content=b"upstream failure",
            request=httpx.Request("POST", url),
        )


class NetworkFailureHttpClient(FakeHttpClient):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connection failed",
            request=httpx.Request("POST", url),
        )


def test_faraz_sms_provider_sends_pattern_request_and_converts_e164_recipient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)
    provider = FarazSmsProvider(
        Settings(
            sms_provider="farazsms",
            farazsms_api_key="test-api-key",
            farazsms_base_url="https://api.iranpayamak.com/ws/v1",
            farazsms_from_number="50002178584000",
            farazsms_pattern_code="SJ3FgPrE0C",
        )
    )

    provider.send_login_otp("+989123456789", "123456")

    assert FakeHttpClient.request_url == "https://api.iranpayamak.com/ws/v1/sms/pattern"
    assert FakeHttpClient.request_headers == {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Api-Key": "test-api-key",
    }
    assert FakeHttpClient.request_json == {
        "code": "SJ3FgPrE0C",
        "attributes": {"code": "123456"},
        "recipient": "09123456789",
        "line_number": "50002178584000",
        "number_format": "english",
    }


def test_faraz_sms_provider_rejects_application_level_delivery_failure_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "Client", ApplicationFailureHttpClient)
    provider = FarazSmsProvider(
        Settings(
            sms_provider="farazsms",
            farazsms_api_key="test-api-key",
            farazsms_from_number="50002178584000",
            farazsms_pattern_code="SJ3FgPrE0C",
        )
    )

    with pytest.raises(RuntimeError) as exc_info:
        provider.send_login_otp("+989123456789", "123456")
    assert str(exc_info.value) == "Faraz SMS delivery failed"
    assert "test-api-key" not in str(exc_info.value)
    assert "123456" not in str(exc_info.value)


@pytest.mark.parametrize("client_class", [HttpFailureHttpClient, NetworkFailureHttpClient])
def test_faraz_sms_provider_maps_http_and_network_failures(
    monkeypatch: pytest.MonkeyPatch,
    client_class: type[FakeHttpClient],
) -> None:
    monkeypatch.setattr(httpx, "Client", client_class)
    provider = FarazSmsProvider(
        Settings(
            sms_provider="farazsms",
            farazsms_api_key="test-api-key",
            farazsms_from_number="50002178584000",
            farazsms_pattern_code="SJ3FgPrE0C",
        )
    )

    with pytest.raises(RuntimeError, match=r"\AFaraz SMS delivery failed\Z"):
        provider.send_login_otp("+989123456789", "123456")


@pytest.mark.parametrize(
    "missing_field",
    ["farazsms_api_key", "farazsms_from_number", "farazsms_pattern_code"],
)
def test_faraz_sms_provider_requires_complete_configuration(missing_field: str) -> None:
    values: dict[str, object] = {
        "sms_provider": "farazsms",
        "farazsms_api_key": "test-api-key",
        "farazsms_from_number": "50002178584000",
        "farazsms_pattern_code": "SJ3FgPrE0C",
    }
    values[missing_field] = " "

    with pytest.raises(ValueError, match=r"\AFaraz SMS provider is not configured\Z"):
        FarazSmsProvider(Settings(**values))  # type: ignore[arg-type]


class FakeSmtp:
    last_message: Any = None

    def __init__(self, host: str, port: int, timeout: int) -> None:
        assert (host, port, timeout) == ("smtp.example.com", 587, 10)

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        pass

    def starttls(self) -> None:
        pass

    def login(self, username: str, password: str) -> None:
        assert (username, password) == ("fitician", "smtp-secret")

    def send_message(self, message: Any) -> None:
        type(self).last_message = message


def test_smtp_provider_sends_reset_link_without_exposing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("smtplib.SMTP", FakeSmtp)
    provider = SmtpEmailProvider(
        Settings(
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_username="fitician",
            smtp_password="smtp-secret",
            smtp_from_address="no-reply@fitician.example",
        )
    )

    provider.send_password_reset(
        "user@example.com",
        "https://fitician.example/reset-password?token=raw-token",
    )

    message = FakeSmtp.last_message
    assert message["To"] == "user@example.com"
    assert "raw-token" in message.get_content()
    assert "smtp-secret" not in message.as_string()


def test_smtp_provider_reuses_delivery_for_verification_and_welcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("smtplib.SMTP", FakeSmtp)
    provider = SmtpEmailProvider(
        Settings(
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_from_address="no-reply@fitician.example",
        )
    )

    provider.send_email_verification(
        "user@example.com",
        "https://fitician.example/verify-email?token=verification-token",
    )
    assert "verification-token" in FakeSmtp.last_message.get_content()
    provider.send_welcome_email("user@example.com")
    assert "فیتیشن" in FakeSmtp.last_message.get_content()


def test_google_provider_passes_backend_audience_to_official_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_verify(token: str, _request: object, audience: str) -> dict[str, object]:
        captured.update(token=token, audience=audience)
        return {
            "iss": "https://accounts.google.com",
            "sub": "google-sub",
            "email": "member@example.com",
            "email_verified": True,
            "name": "Member",
            "picture": "https://example.com/picture.jpg",
        }

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", fake_verify)
    assert hasattr(providers, "GoogleIdTokenProvider")
    provider = providers.GoogleIdTokenProvider(Settings(google_client_id="fitician-client-id"))

    identity = provider.verify("signed-token")

    assert captured == {"token": "signed-token", "audience": "fitician-client-id"}
    assert identity.sub == "google-sub"
    assert identity.email_verified is True
