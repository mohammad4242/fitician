from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import create_app

PRODUCTION_AUTH_DELIVERY = {
    "email_provider": "smtp",
    "smtp_host": "smtp.example.com",
    "smtp_from_address": "no-reply@fitician.example",
    "sms_provider": "farazsms",
    "farazsms_api_key": "test-faraz-api-key",
    "farazsms_from_number": "50002178584000",
    "farazsms_pattern_code": "SJ3FgPrE0C",
    "phone_otp_hmac_secret": "production-phone-otp-hmac-secret-for-tests",
    "google_client_id": "fitician-client-id.apps.googleusercontent.com",
}


def test_settings_accept_explicit_environment_values() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://fitician:fitician@localhost:5432/fitician",
        frontend_origin="http://localhost:5173",
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
    )

    assert settings.session_ttl_seconds == 604800
    assert settings.frontend_origin == "http://localhost:5173"
    assert settings.email_provider == "fake"
    assert settings.sms_provider == "fake"
    assert settings.password_reset_ttl_seconds == 900
    assert settings.phone_otp_ttl_seconds == 300
    assert settings.phone_otp_resend_cooldown_seconds == 60
    assert settings.phone_otp_max_attempts == 5
    assert settings.email_verification_ttl_seconds == 86400
    assert settings.farazsms_base_url == "https://api.iranpayamak.com/ws/v1"


def test_android_google_client_id_is_loaded_from_server_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_ANDROID_CLIENT_ID", "android-client-for-tests")

    settings = Settings(_env_file=None)

    assert settings.google_android_client_id == "android-client-for-tests"


def test_delivery_credentials_are_redacted() -> None:
    settings = Settings(
        smtp_password="smtp-secret",
        farazsms_api_key="sms-secret",
        phone_otp_hmac_secret="otp-secret-with-at-least-thirty-two-characters",
    )

    rendered = repr(settings)
    assert "smtp-secret" not in rendered
    assert "sms-secret" not in rendered
    assert "otp-secret" not in rendered


def test_s3_configuration_requires_complete_values_and_redacts_secrets() -> None:
    settings = Settings(app_env="test", s3_access_key_id="access", s3_secret_access_key="secret")
    assert settings.media_storage_backend == "local"
    assert "secret" not in repr(settings)
    assert "s3_access_key_id" not in repr(settings)
    with pytest.raises(ValidationError, match="S3 media storage requires"):
        Settings(app_env="test", media_storage_backend="s3")
    configured = Settings(
        app_env="test",
        media_storage_backend="s3",
        s3_endpoint="https://s3.example.test",
        s3_bucket="fitician-media",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        s3_region="ir-thr-at1",
        media_public_base_url="https://media.example.test",
    )
    assert configured.media_storage_backend == "s3"


def test_production_requires_google_identity_configuration() -> None:
    with pytest.raises(ValidationError, match="Google client ID"):
        Settings(
            _env_file=None,
            google_client_id=None,
            app_env="production",
            frontend_origin="https://fitician.example",
            cookie_secure=True,
            session_cookie_name="__Host-fitician_session",
            private_file_signing_key="production-private-file-signing-key-for-tests",
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_from_address="no-reply@fitician.example",
            sms_provider="farazsms",
            farazsms_api_key="test-faraz-api-key",
            farazsms_from_number="50002178584000",
            farazsms_pattern_code="SJ3FgPrE0C",
            phone_otp_hmac_secret="production-phone-otp-hmac-secret-for-tests",
        )


@pytest.mark.parametrize("apple_client_id", [None, "", "   "])
def test_production_allows_missing_apple_identity_configuration(
    apple_client_id: str | None,
) -> None:
    settings = Settings(
        app_env="production",
        frontend_origin="https://fitician.example",
        cookie_secure=True,
        session_cookie_name="__Host-fitician_session",
        private_file_signing_key="production-private-file-signing-key-for-tests",
        apple_client_id=apple_client_id,
        **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
    )

    assert settings.app_env == "production"
    assert settings.apple_client_id is None


def test_production_rejects_fake_auth_delivery_providers() -> None:
    with pytest.raises(ValidationError, match="SMTP email provider"):
        Settings(
            app_env="production",
            frontend_origin="https://fitician.example",
            cookie_secure=True,
            session_cookie_name="__Host-fitician_session",
            private_file_signing_key="production-private-file-signing-key-for-tests",
        )


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"sms_provider": "fake"}, "configured Faraz SMS provider"),
        ({"farazsms_api_key": None}, "configured Faraz SMS provider"),
        ({"farazsms_api_key": " "}, "configured Faraz SMS provider"),
        ({"farazsms_from_number": None}, "Faraz SMS sender number"),
        ({"farazsms_from_number": " "}, "Faraz SMS sender number"),
        ({"farazsms_pattern_code": None}, "Faraz SMS pattern code"),
        ({"farazsms_pattern_code": " "}, "Faraz SMS pattern code"),
    ],
)
def test_production_requires_complete_faraz_sms_configuration(
    override: dict[str, object],
    expected_message: str,
) -> None:
    values: dict[str, object] = {
        "app_env": "production",
        "frontend_origin": "https://fitician.example",
        "cookie_secure": True,
        "session_cookie_name": "__Host-fitician_session",
        "private_file_signing_key": "production-private-file-signing-key-for-tests",
        **PRODUCTION_AUTH_DELIVERY,
    }
    values.update(override)

    with pytest.raises(ValidationError, match=expected_message):
        Settings(**values)  # type: ignore[arg-type]


def test_local_settings_accept_multiple_explicit_frontend_origins() -> None:
    settings = Settings(
        app_env="local",
        frontend_origin="http://localhost:5173",
        frontend_origins="http://localhost:5173,http://100.97.78.5:5173",
        cookie_secure=False,
        session_cookie_name="fitician_session",
    )

    assert settings.allowed_frontend_origins == (
        "http://localhost:5173",
        "http://100.97.78.5:5173",
    )


def test_production_settings_accept_secure_cookie_contract() -> None:
    settings = Settings(
        app_env="production",
        frontend_origin="https://fitician.example",
        cookie_secure=True,
        session_cookie_name="__Host-fitician_session",
        private_file_signing_key="production-private-file-signing-key-for-tests",
        **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
    )

    assert settings.app_env == "production"


def test_account_deletion_is_disabled_by_default() -> None:
    assert Settings(app_env="test").account_deletion_enabled is False


def test_production_account_deletion_requires_legal_approval() -> None:
    with pytest.raises(ValidationError, match="legal approval"):
        Settings(
            app_env="production",
            frontend_origin="https://fitician.example",
            cookie_secure=True,
            session_cookie_name="__Host-fitician_session",
            private_file_signing_key="production-private-file-signing-key-for-tests",
            account_deletion_enabled=True,
            **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
        )


def test_production_account_deletion_accepts_recorded_legal_approval() -> None:
    settings = Settings(
        app_env="production",
        frontend_origin="https://fitician.example",
        cookie_secure=True,
        session_cookie_name="__Host-fitician_session",
        private_file_signing_key="production-private-file-signing-key-for-tests",
        account_deletion_enabled=True,
        account_deletion_legal_approval="legal-approval-2026-09-08",
        **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
    )

    assert settings.account_deletion_enabled is True


def test_production_settings_normalize_a_trailing_origin_slash() -> None:
    settings = Settings(
        app_env="production",
        frontend_origin="https://fitician.example/",
        cookie_secure=True,
        session_cookie_name="__Host-fitician_session",
        private_file_signing_key="production-private-file-signing-key-for-tests",
        **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
    )

    assert settings.frontend_origin == "https://fitician.example"


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"frontend_origin": "http://fitician.example"}, "HTTPS frontend origin"),
        ({"frontend_origin": "https://"}, "complete frontend origin"),
        (
            {"frontend_origin": "https://fitician.example/app"},
            "origin without credentials, path, query, or fragment",
        ),
        (
            {"frontend_origin": "https://user@fitician.example"},
            "origin without credentials, path, query, or fragment",
        ),
        (
            {"frontend_origin": "https://fitician.example?source=config"},
            "origin without credentials, path, query, or fragment",
        ),
        ({"cookie_secure": False}, "secure cookies"),
        ({"session_cookie_name": "fitician_session"}, "__Host-fitician_session"),
    ],
)
def test_production_settings_reject_insecure_cookie_contract(
    override: dict[str, object],
    expected_message: str,
) -> None:
    values: dict[str, object] = {
        "app_env": "production",
        "frontend_origin": "https://fitician.example",
        "cookie_secure": True,
        "session_cookie_name": "__Host-fitician_session",
        "private_file_signing_key": "production-private-file-signing-key-for-tests",
        **PRODUCTION_AUTH_DELIVERY,
    }
    values.update(override)

    with pytest.raises(ValidationError, match=expected_message):
        Settings(**values)  # type: ignore[arg-type]


def test_production_settings_reject_default_private_file_signing_key() -> None:
    with pytest.raises(ValidationError, match="strong private file signing key"):
        Settings(
            app_env="production",
            frontend_origin="https://fitician.example",
            cookie_secure=True,
            session_cookie_name="__Host-fitician_session",
            **PRODUCTION_AUTH_DELIVERY,  # type: ignore[arg-type]
        )


def test_settings_redact_zen_api_key_in_repr() -> None:
    settings = Settings(opencode_zen_api_key="test-secret-key")

    assert "test-secret-key" not in repr(settings)
    assert settings.workout_max_repair_attempts == 1
    assert settings.workout_generation_cooldown_seconds == 0
    assert settings.workout_deterministic_fallback_enabled is True
    assert settings.workout_max_candidates == 80
    assert settings.workout_max_request_bytes == 262144
    assert settings.workout_warmup_minutes == 5


def test_agent_service_settings_normalize_and_redact_token() -> None:
    settings = Settings(agent_service_token="  agent-service-token-for-tests  ")

    assert settings.agent_service_token is not None
    assert settings.agent_service_token.get_secret_value() == "agent-service-token-for-tests"
    assert settings.agent_service_connect_timeout_seconds == 5.0
    assert settings.agent_service_max_image_bytes == 8 * 1024 * 1024
    assert "agent-service-token-for-tests" not in repr(settings)


def test_blank_agent_service_token_keeps_api_mode_available() -> None:
    settings = Settings(agent_service_token="   ")

    assert settings.agent_service_token is None


def test_app_lifespan_owns_a_dedicated_agent_service_client(tmp_path: Path) -> None:
    settings = Settings(
        app_env="test",
        cookie_secure=False,
        session_cookie_name="fitician_session",
        media_root=tmp_path / "media",
    )
    app = create_app(settings)

    with TestClient(app):
        assert app.state.agent_http_client.is_closed is False

    assert app.state.agent_http_client.is_closed is True


def test_settings_accept_an_explicit_zen_proxy_url() -> None:
    settings = Settings(opencode_zen_proxy_url="socks5://127.0.0.1:10808")

    assert settings.opencode_zen_proxy_url == "socks5://127.0.0.1:10808"


def test_trusted_proxy_ips_have_a_private_network_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.trusted_proxy_ips == "127.0.0.1,::1,172.16.0.0/12"


def test_food_price_api_credentials_are_disabled_and_redacted_by_default() -> None:
    settings = Settings(
        food_price_persianapi_api_key="persian-secret",
        food_price_basalam_api_key="basalam-secret",
        food_price_provider_api_key="future-secret",
    )

    assert settings.food_price_persianapi_enabled is False
    assert settings.food_price_basalam_api_enabled is False
    assert settings.food_price_provider_api_enabled is False
    assert "persian-secret" not in repr(settings)
    assert "basalam-secret" not in repr(settings)
    assert "future-secret" not in repr(settings)
