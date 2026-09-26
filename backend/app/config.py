from functools import lru_cache
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fitician:fitician@localhost:5432/fitician"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    db_statement_timeout_ms: int = Field(default=30000, ge=0, le=600000)
    trusted_proxy_ips: str = "127.0.0.1,::1,172.16.0.0/12"
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_password: SecretStr | None = Field(default=None, repr=False)
    redis_max_connections: int = Field(default=10, ge=1, le=100)
    redis_connect_timeout_seconds: float = Field(default=1.0, gt=0, le=30)
    redis_socket_timeout_seconds: float = Field(default=2.0, gt=0, le=60)
    redis_health_check_interval_seconds: int = Field(default=15, ge=0, le=3600)
    cache_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    cache_detail_ttl_seconds: int = Field(default=600, ge=1, le=86400)
    cache_lock_ttl_seconds: int = Field(default=5, ge=1, le=60)
    cache_lock_wait_ms: int = Field(default=50, ge=0, le=50)
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str | None = None
    app_env: Literal["local", "test", "production"] = "local"
    instance_header_enabled: bool = False
    instance_id: str | None = Field(default=None, max_length=120)
    cookie_secure: bool = True
    session_cookie_name: str = "__Host-fitician_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    mobile_access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    mobile_refresh_token_ttl_seconds: int = Field(
        default=30 * 24 * 60 * 60, ge=3600, le=365 * 24 * 60 * 60
    )
    account_deletion_enabled: bool = False
    account_deletion_legal_approval: str | None = Field(default=None, max_length=160)
    account_deletion_grace_period_days: int = Field(default=7, ge=1, le=30)
    account_deletion_reauth_window_seconds: int = Field(default=600, ge=60, le=3600)
    account_deletion_worker_interval_seconds: int = Field(default=60, ge=10, le=3600)
    billing_default_provider: str | None = None
    billing_fake_provider_enabled: bool = False
    billing_order_ttl_minutes: int = Field(default=30, ge=1, le=1440)
    billing_callback_base_url: str | None = Field(default=None, max_length=500)
    notification_worker_batch_size: int = Field(default=100, ge=1, le=500)
    notification_worker_poll_seconds: float = Field(default=5.0, gt=0, le=60)
    notification_worker_lease_seconds: int = Field(default=60, ge=10, le=3600)
    notification_fcm_enabled: bool = False
    notification_fcm_project_id: str | None = None
    notification_fcm_service_account_json: SecretStr | None = Field(default=None, repr=False)
    notification_fcm_base_url: str = "https://fcm.googleapis.com"
    notification_fcm_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    notification_apns_enabled: bool = False
    notification_apns_team_id: str | None = None
    notification_apns_key_id: str | None = None
    notification_apns_private_key: SecretStr | None = Field(default=None, repr=False)
    notification_apns_bundle_id: str = "com.fitician.app"
    notification_apns_base_url: str = "https://api.push.apple.com"
    notification_apns_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    notification_max_delivery_attempts: int = Field(default=5, ge=1, le=10)
    notification_retry_base_seconds: int = Field(default=30, ge=1, le=3600)
    notification_retry_max_seconds: int = Field(default=1800, ge=1, le=86400)
    email_provider: Literal["fake", "smtp"] = "fake"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = Field(default=None, repr=False)
    smtp_from_address: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    password_reset_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    email_verification_ttl_seconds: int = Field(default=86400, ge=300, le=604800)
    sms_provider: Literal["fake", "farazsms"] = "fake"
    farazsms_api_key: SecretStr | None = Field(default=None, repr=False)
    farazsms_base_url: str = "https://api.iranpayamak.com/ws/v1"
    farazsms_from_number: str | None = None
    farazsms_pattern_code: str | None = None
    sms_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    phone_otp_hmac_secret: SecretStr = Field(
        default=SecretStr("fitician-local-phone-otp-secret-change-me"), repr=False
    )
    phone_otp_ttl_seconds: int = Field(default=300, ge=60, le=900)
    phone_otp_resend_cooldown_seconds: int = Field(default=60, ge=10, le=600)
    phone_otp_max_attempts: int = Field(default=5, ge=1, le=10)
    google_client_id: str | None = None
    google_android_client_id: str | None = None
    apple_client_id: str | None = None
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"
    apple_jwks_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    apple_jwks_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    apple_clock_skew_seconds: int = Field(default=60, ge=0, le=300)
    auth_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86400)
    auth_register_ip_limit: int = Field(default=20, ge=1, le=1000)
    auth_register_identifier_limit: int = Field(default=5, ge=1, le=1000)
    auth_password_ip_limit: int = Field(default=20, ge=1, le=1000)
    auth_password_identifier_limit: int = Field(default=5, ge=1, le=1000)
    auth_phone_otp_ip_limit: int = Field(default=10, ge=1, le=1000)
    auth_phone_otp_identifier_limit: int = Field(default=10, ge=1, le=1000)
    auth_forgot_password_ip_limit: int = Field(default=20, ge=1, le=1000)
    auth_forgot_password_identifier_limit: int = Field(default=5, ge=1, le=1000)
    auth_email_verification_ip_limit: int = Field(default=10, ge=1, le=1000)
    auth_email_verification_user_limit: int = Field(default=5, ge=1, le=1000)
    auth_google_ip_limit: int = Field(default=30, ge=1, le=1000)
    auth_apple_ip_limit: int = Field(default=30, ge=1, le=1000)
    auth_mobile_password_ip_limit: int = Field(default=20, ge=1, le=1000)
    auth_mobile_password_identifier_limit: int = Field(default=5, ge=1, le=1000)
    auth_mobile_google_ip_limit: int = Field(default=30, ge=1, le=1000)
    auth_mobile_apple_ip_limit: int = Field(default=30, ge=1, le=1000)
    auth_mobile_refresh_ip_limit: int = Field(default=60, ge=1, le=1000)
    application_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86400)
    body_analysis_rate_limit: int = Field(default=5, ge=1, le=1000)
    body_photo_upload_rate_limit: int = Field(default=30, ge=1, le=1000)
    workout_generation_rate_limit: int = Field(default=5, ge=1, le=1000)
    media_root: Path = Path("var/media")
    media_public_path: str = "/media"
    media_storage_backend: Literal["local", "s3"] = "local"
    media_local_fallback_enabled: bool = True
    media_public_base_url: str | None = None
    s3_endpoint: str | None = None
    s3_bucket: str | None = None
    s3_public_bucket: str | None = None
    s3_private_bucket: str | None = None
    s3_access_key_id: SecretStr | None = Field(default=None, repr=False)
    s3_secret_access_key: SecretStr | None = Field(default=None, repr=False)
    s3_region: str | None = None
    s3_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    s3_read_timeout_seconds: float = Field(default=60.0, gt=0, le=600)
    s3_max_attempts: int = Field(default=3, ge=1, le=10)
    s3_public_object_acl: Literal["private", "public-read"] = "public-read"
    media_max_bytes: int = 20 * 1024 * 1024
    media_max_video_bytes: int = 64 * 1024 * 1024
    import_media_max_bytes: int = 24 * 1024 * 1024
    media_max_video_duration_seconds: float = 20.0
    media_read_chunk_bytes: int = 1024 * 1024
    body_photo_storage_root: Path = Path("var/private/body-photos")
    body_photo_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    body_photo_max_pixels: int = Field(default=40_000_000, ge=1, le=40_000_000)
    body_photo_min_width: int = Field(default=256, ge=64, le=4096)
    body_photo_min_height: int = Field(default=512, ge=64, le=8192)
    body_photo_read_chunk_bytes: int = Field(default=1024 * 1024, ge=1024, le=4 * 1024 * 1024)
    profile_photo_storage_root: Path = Path("var/private/profile-photos")
    profile_photo_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    profile_photo_max_pixels: int = Field(default=16_000_000, ge=1, le=40_000_000)
    profile_photo_min_dimension: int = Field(default=128, ge=1, le=4096)
    profile_photo_read_chunk_bytes: int = Field(default=1024 * 1024, ge=1024, le=4 * 1024 * 1024)
    food_photo_storage_root: Path = Path("var/private/food-photos")
    food_photo_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=20 * 1024 * 1024)
    food_photo_max_pixels: int = Field(default=20_000_000, ge=1, le=40_000_000)
    food_photo_retention_days: int = Field(default=30, ge=1, le=365)
    food_photo_rate_limit: int = Field(default=10, ge=1, le=1000)
    food_photo_worker_batch_size: int = Field(default=5, ge=1, le=50)
    food_photo_worker_poll_seconds: float = Field(default=3.0, gt=0, le=60)
    food_photo_worker_lease_seconds: int = Field(default=600, ge=30, le=3600)
    food_photo_max_attempts: int = Field(default=3, ge=1, le=10)
    food_photo_retry_base_seconds: int = Field(default=30, ge=1, le=3600)
    food_photo_retry_max_seconds: int = Field(default=1800, ge=1, le=86400)
    body_analysis_worker_batch_size: int = Field(default=1, ge=1, le=20)
    body_analysis_worker_poll_seconds: float = Field(default=3.0, gt=0, le=60)
    body_analysis_worker_lease_seconds: int = Field(default=900, ge=60, le=3600)
    body_analysis_local_fake_provider_enabled: bool = False
    body_analysis_retry_base_seconds: int = Field(default=30, ge=1, le=3600)
    body_analysis_retry_max_seconds: int = Field(default=900, ge=1, le=86400)
    job_heartbeat_path: Path = Path("/tmp/fitician-health/heartbeat.json")
    job_heartbeat_interval_seconds: float = Field(default=5.0, gt=0, le=60)
    job_heartbeat_max_age_seconds: float = Field(default=20.0, gt=1, le=300)
    nutrition_lab_storage_root: Path = Path("var/private/nutrition-labs")
    nutrition_lab_max_bytes: int = Field(default=12 * 1024 * 1024, ge=1024, le=30 * 1024 * 1024)
    nutrition_lab_max_pixels: int = Field(default=20_000_000, ge=1, le=40_000_000)
    nutrition_lab_retention_days: int = Field(default=365 * 7, ge=30, le=365 * 20)
    nutrition_lab_upload_rate_limit: int = Field(default=20, ge=1, le=1000)
    nutrition_upload_rate_window_seconds: int = Field(default=3600, ge=60, le=86400)
    private_file_access_ttl_seconds: int = Field(default=300, ge=30, le=900)
    private_file_signing_key: SecretStr = Field(
        default=SecretStr("fitician-local-private-file-signing-key-change-me"), repr=False
    )
    ffprobe_path: str = "ffprobe"
    ffprobe_timeout_seconds: float = 5.0
    ffmpeg_path: str = "ffmpeg"
    ffmpeg_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    owner_video_import_max_bytes: int = Field(
        default=64 * 1024 * 1024,
        ge=1024,
        le=256 * 1024 * 1024,
    )
    owner_video_import_work_root: Path = Path("var/imports/owner-video")
    owner_video_codex_path: str = "codex"
    owner_video_codex_model: str | None = None
    owner_video_codex_timeout_seconds: float = Field(default=420.0, gt=0, le=600)
    owner_video_identification_confidence: float = Field(default=0.90, ge=0, le=1)
    owner_video_match_confidence: float = Field(default=0.92, ge=0, le=1)
    owner_video_presentation_confidence: float = Field(default=0.80, ge=0, le=1)
    opencode_zen_api_key: SecretStr | None = Field(default=None, repr=False)
    opencode_zen_base_url: str = "https://opencode.ai/zen/v1"
    opencode_zen_model: str = "gpt-5.6-terra"
    opencode_zen_timeout_seconds: float = Field(default=420.0, gt=0, le=600)
    opencode_zen_proxy_url: str | None = Field(default=None, max_length=500, repr=False)
    ai_credential_encryption_key: SecretStr | None = Field(default=None, repr=False)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = Field(default=420.0, gt=0, le=600)
    agent_service_base_url: str = "http://agent-service:9001"
    agent_service_token: SecretStr | None = Field(default=None, repr=False)
    agent_service_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    agent_service_max_image_bytes: int = Field(
        default=8 * 1024 * 1024, ge=1024, le=64 * 1024 * 1024
    )
    openrouter_proxy_url: str | None = Field(default=None, max_length=500, repr=False)
    ai_model_catalog_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    @field_validator("opencode_zen_proxy_url", "openrouter_proxy_url", mode="before")
    @classmethod
    def normalize_empty_proxy_urls(cls, value: object) -> str | None:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return None if value is None else str(value)

    @field_validator("apple_client_id", mode="before")
    @classmethod
    def normalize_empty_apple_client_id(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    workout_prompt_version: str = "v1"
    workout_policy_version: str = "v1"
    workout_catalog_programming_version: str = "v1"
    workout_max_repair_attempts: int = Field(default=1, ge=0, le=1)
    workout_generation_cooldown_seconds: int = Field(default=0, ge=0, le=3600)
    workout_deterministic_fallback_enabled: bool = True
    workout_max_candidates: int = Field(default=80, ge=3, le=200)
    workout_max_request_bytes: int = Field(default=262144, ge=1024, le=1048576)
    workout_warmup_minutes: int = Field(default=5, ge=0, le=30)
    food_price_update_enabled: bool = True
    food_price_update_timezone: str = "Asia/Tehran"
    food_price_update_hour: int = Field(default=12, ge=0, le=23)
    food_price_update_minute: int = Field(default=0, ge=0, le=59)
    food_price_provider_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    food_price_provider_retries: int = Field(default=3, ge=1, le=5)
    food_price_public_source_url: str | None = Field(default=None, max_length=500, repr=False)
    food_price_api_key: SecretStr | None = Field(default=None, repr=False)
    food_price_api_base_url: str | None = Field(default=None, max_length=500, repr=False)
    food_price_persianapi_enabled: bool = False
    food_price_persianapi_api_key: SecretStr | None = Field(default=None, repr=False)
    food_price_basalam_api_enabled: bool = False
    food_price_basalam_api_key: SecretStr | None = Field(default=None, repr=False)
    food_price_provider_api_enabled: bool = False
    food_price_provider_api_key: SecretStr | None = Field(default=None, repr=False)
    food_price_provider_base_url: str | None = Field(default=None, max_length=500, repr=False)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("agent_service_token", mode="before")
    @classmethod
    def normalize_agent_service_token(cls, value: object) -> SecretStr | None:
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Agent Service token must be text")
        token = value.strip()
        return SecretStr(token) if token else None

    @property
    def allowed_frontend_origins(self) -> tuple[str, ...]:
        configured_origins = (
            tuple(origin.strip().rstrip("/") for origin in self.frontend_origins.split(","))
            if self.frontend_origins is not None
            else ()
        )
        return tuple(
            dict.fromkeys(
                origin for origin in (self.frontend_origin, *configured_origins) if origin
            )
        )

    @model_validator(mode="after")
    def enforce_private_body_photo_storage(self) -> Self:
        if self.media_storage_backend == "s3":
            public_bucket = self.s3_public_bucket or self.s3_bucket
            required = {
                "S3 endpoint": self.s3_endpoint,
                "S3 public bucket": public_bucket,
                "S3 access key": (
                    self.s3_access_key_id.get_secret_value() if self.s3_access_key_id else None
                ),
                "S3 secret key": (
                    self.s3_secret_access_key.get_secret_value()
                    if self.s3_secret_access_key
                    else None
                ),
                "S3 region": self.s3_region,
                "public media base URL": self.media_public_base_url,
            }
            missing = [name for name, value in required.items() if not value or not value.strip()]
            if missing:
                raise ValueError(f"S3 media storage requires {', '.join(missing)}")
            if self.app_env == "production":
                if not self.s3_private_bucket or not self.s3_private_bucket.strip():
                    raise ValueError("Production S3 media storage requires S3 private bucket")
                if self.media_local_fallback_enabled:
                    raise ValueError("Production S3 media storage must disable local fallback")
            for name, value in (
                ("S3 endpoint", self.s3_endpoint),
                ("public media base URL", self.media_public_base_url),
            ):
                parsed = urlsplit(value or "")
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(f"{name} must be an HTTP(S) URL")
                if parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError(f"{name} must not contain credentials, query, or fragment")
        public_root = self.media_root.resolve()
        private_root = self.body_photo_storage_root.resolve()
        if private_root == public_root or private_root.is_relative_to(public_root):
            raise ValueError("Body photo storage must be outside public media storage")
        profile_private_root = self.profile_photo_storage_root.resolve()
        if profile_private_root == public_root or profile_private_root.is_relative_to(public_root):
            raise ValueError("Profile photo storage must be outside public media storage")
        food_private_root = self.food_photo_storage_root.resolve()
        if food_private_root == public_root or food_private_root.is_relative_to(public_root):
            raise ValueError("Food photo storage must be outside public media storage")
        lab_root = self.nutrition_lab_storage_root.resolve()
        if lab_root == public_root or lab_root.is_relative_to(public_root):
            raise ValueError("Nutrition lab storage must be outside public media storage")
        return self

    @model_validator(mode="after")
    def enforce_production_cookie_contract(self) -> Self:
        if self.app_env != "production":
            if self.billing_default_provider is None:
                self.billing_default_provider = "fake"
            return self
        if self.billing_default_provider == "fake" or self.billing_fake_provider_enabled:
            raise ValueError("Production cannot enable the fake billing provider")
        origin = urlsplit(self.frontend_origin)
        if origin.scheme != "https":
            raise ValueError("Production requires an HTTPS frontend origin")
        if origin.hostname is None:
            raise ValueError("Production requires a complete frontend origin")
        if (
            origin.username is not None
            or origin.password is not None
            or origin.path not in {"", "/"}
            or origin.query
            or origin.fragment
        ):
            raise ValueError(
                "Production requires an origin without credentials, path, query, or fragment"
            )
        if not self.cookie_secure:
            raise ValueError("Production requires secure cookies")
        if self.session_cookie_name != "__Host-fitician_session":
            raise ValueError("Production requires the __Host-fitician_session cookie name")
        if self.email_provider != "smtp" or not self.smtp_host or not self.smtp_from_address:
            raise ValueError("Production requires a configured SMTP email provider")
        if (
            self.sms_provider != "farazsms"
            or self.farazsms_api_key is None
            or not self.farazsms_api_key.get_secret_value().strip()
        ):
            raise ValueError("Production requires a configured Faraz SMS provider")
        if not self.farazsms_from_number or not self.farazsms_from_number.strip():
            raise ValueError("Production requires a Faraz SMS sender number")
        if not self.farazsms_pattern_code or not self.farazsms_pattern_code.strip():
            raise ValueError("Production requires a Faraz SMS pattern code")
        if not self.google_client_id:
            raise ValueError("Production requires a Google client ID")
        otp_secret = self.phone_otp_hmac_secret.get_secret_value()
        if otp_secret == "fitician-local-phone-otp-secret-change-me" or len(otp_secret) < 32:
            raise ValueError("Production requires a strong phone OTP HMAC secret")
        signing_key = self.private_file_signing_key.get_secret_value()
        if (
            signing_key == "fitician-local-private-file-signing-key-change-me"
            or len(signing_key) < 32
        ):
            raise ValueError("Production requires a strong private file signing key")
        self.frontend_origin = f"https://{origin.netloc}"
        return self

    @model_validator(mode="after")
    def enforce_account_deletion_approval(self) -> Self:
        if (
            self.app_env == "production"
            and self.account_deletion_enabled
            and not self.account_deletion_legal_approval
        ):
            raise ValueError("Production account deletion requires recorded legal approval")
        return self

    @model_validator(mode="after")
    def reject_local_fake_provider_in_production(self) -> Self:
        if self.app_env == "production" and self.body_analysis_local_fake_provider_enabled:
            raise ValueError("Production cannot enable the local fake body analysis provider")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
