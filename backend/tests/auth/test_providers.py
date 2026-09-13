from types import TracebackType
from typing import Any

import httpx
import pytest

from app.auth import providers
from app.auth.providers import IPPanelSmsProvider, SmtpEmailProvider
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
            204,
            content=b"",
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
            200,
            json={"meta": {"status": False}},
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


def test_ippanel_provider_uses_pattern_contract_with_empty_success_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "Client", FakeHttpClient)
    provider = IPPanelSmsProvider(
        Settings(
            sms_provider="ippanel",
            ippanel_api_key="test-api-key",
            ippanel_base_url="https://edge.ippanel.com/v1/api",
            ippanel_from_number="+983000505",
            ippanel_pattern_code="test-pattern-code",
        )
    )

    provider.send_login_otp("+989123456789", "123456")

    assert FakeHttpClient.request_url == "https://edge.ippanel.com/v1/api/send"
    assert FakeHttpClient.request_headers == {
        "Authorization": "test-api-key",
        "Content-Type": "application/json",
    }
    assert FakeHttpClient.request_json == {
        "sending_type": "pattern",
        "from_number": "+983000505",
        "code": "test-pattern-code",
        "recipients": ["+989123456789"],
        "params": {"code": "123456"},
    }


def test_ippanel_provider_rejects_application_level_delivery_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "Client", ApplicationFailureHttpClient)
    provider = IPPanelSmsProvider(
        Settings(
            sms_provider="ippanel",
            ippanel_api_key="test-api-key",
            ippanel_from_number="+983000505",
            ippanel_pattern_code="test-pattern-code",
        )
    )

    with pytest.raises(RuntimeError, match=r"\AIPPanel delivery failed\Z"):
        provider.send_login_otp("+989123456789", "123456")


@pytest.mark.parametrize("client_class", [HttpFailureHttpClient, NetworkFailureHttpClient])
def test_ippanel_provider_maps_http_and_network_failures(
    monkeypatch: pytest.MonkeyPatch,
    client_class: type[FakeHttpClient],
) -> None:
    monkeypatch.setattr(httpx, "Client", client_class)
    provider = IPPanelSmsProvider(
        Settings(
            sms_provider="ippanel",
            ippanel_api_key="test-api-key",
            ippanel_from_number="+983000505",
            ippanel_pattern_code="test-pattern-code",
        )
    )

    with pytest.raises(RuntimeError, match=r"\AIPPanel delivery failed\Z"):
        provider.send_login_otp("+989123456789", "123456")


@pytest.mark.parametrize(
    "missing_field",
    ["ippanel_api_key", "ippanel_from_number", "ippanel_pattern_code"],
)
def test_ippanel_provider_requires_complete_configuration(missing_field: str) -> None:
    values: dict[str, object] = {
        "sms_provider": "ippanel",
        "ippanel_api_key": "test-api-key",
        "ippanel_from_number": "+983000505",
        "ippanel_pattern_code": "test-pattern-code",
    }
    values[missing_field] = " "

    with pytest.raises(ValueError, match=r"\AIPPanel provider is not configured\Z"):
        IPPanelSmsProvider(Settings(**values))  # type: ignore[arg-type]


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
        assert (username, password) == ("fitsho", "smtp-secret")

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
            smtp_username="fitsho",
            smtp_password="smtp-secret",
            smtp_from_address="no-reply@fitsho.example",
        )
    )

    provider.send_password_reset(
        "user@example.com",
        "https://fitsho.example/reset-password?token=raw-token",
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
            smtp_from_address="no-reply@fitsho.example",
        )
    )

    provider.send_email_verification(
        "user@example.com",
        "https://fitsho.example/verify-email?token=verification-token",
    )
    assert "verification-token" in FakeSmtp.last_message.get_content()
    provider.send_welcome_email("user@example.com")
    assert "فیتشو" in FakeSmtp.last_message.get_content()


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
    provider = providers.GoogleIdTokenProvider(Settings(google_client_id="fitsho-client-id"))

    identity = provider.verify("signed-token")

    assert captured == {"token": "signed-token", "audience": "fitsho-client-id"}
    assert identity.sub == "google-sub"
    assert identity.email_verified is True
