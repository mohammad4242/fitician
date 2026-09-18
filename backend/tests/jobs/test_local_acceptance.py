from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select

from app.auth.models import User
from app.auth.service import session_for_token
from app.body_analysis.models import BodyAnalysis
from app.body_analysis.providers.local_fake import (
    LocalFakeBodyAnalysisProvider,
    local_fake_provider_allowed,
)
from app.body_analysis.worker import run_body_analysis_once
from app.config import Settings
from app.jobs.local_acceptance import (
    cleanup_batch,
    cleanup_member,
    inspect_body,
    seed_body_jobs,
    seed_catalogue_member,
)


def test_local_fake_provider_is_rejected_outside_explicit_local_mode() -> None:
    assert local_fake_provider_allowed(
        Settings(app_env="local", body_analysis_local_fake_provider_enabled=True)
    )
    assert not local_fake_provider_allowed(
        Settings(app_env="test", body_analysis_local_fake_provider_enabled=False)
    )
    production = Settings.model_construct(
        app_env="production", body_analysis_local_fake_provider_enabled=True
    )
    assert not local_fake_provider_allowed(production)


def test_production_settings_reject_local_fake_provider() -> None:
    with pytest.raises(ValueError, match="local fake body analysis provider"):
        Settings(
            app_env="production",
            body_analysis_local_fake_provider_enabled=True,
            frontend_origin="https://example.com",
            cookie_secure=True,
            session_cookie_name="__Host-fitician_session",
            billing_default_provider="real",
            email_provider="smtp",
            smtp_host="smtp.example.com",
            smtp_from_address="noreply@example.com",
            sms_provider="farazsms",
            farazsms_api_key=SecretStr("test-key"),
            farazsms_from_number="1000",
            farazsms_pattern_code="pattern",
            google_client_id="google-client",
            phone_otp_hmac_secret=SecretStr("x" * 32),
            private_file_signing_key=SecretStr("y" * 32),
            _env_file=None,
        )


def test_local_fake_provider_returns_deterministic_v4_payload() -> None:
    provider = LocalFakeBodyAnalysisProvider.from_model_id(
        "local-fake-v1-delay-1"
    )
    request = object()
    response = asyncio.run(provider.analyze_images(request, images=()))
    assert response.model_id == "local-fake-v1-delay-1"
    assert response.payload["schema_version"] == "4.0"
    assert response.payload["assessment_status"] == "complete"
    assert len(response.payload["area_observations"]) == 11


def test_local_fake_provider_rejects_unbounded_or_malformed_delay() -> None:
    with pytest.raises(ValueError, match="model id"):
        LocalFakeBodyAnalysisProvider.from_model_id("local-fake-v1-delay-999999")
    with pytest.raises(ValueError, match="model id"):
        LocalFakeBodyAnalysisProvider.from_model_id("local-fake-v1-delay-nope")


def test_fixture_job_is_durable_and_finalized_once(db, test_settings: Settings) -> None:
    test_settings.body_analysis_local_fake_provider_enabled = True
    seeded = seed_body_jobs(db, test_settings, count=1, delay_seconds=0)
    analysis_id = UUID(seeded["analysis_ids"][0])
    async def run() -> int:
        async with httpx.AsyncClient() as client:
            return await run_body_analysis_once(
                db,
                settings=test_settings,
                ai_http_client=client,
                agent_http_client=client,
                worker_id="local-acceptance-test-worker",
            )

    assert asyncio.run(run()) == 1
    first = inspect_body(db, analysis_id)
    assert first["status"] == "review_pending"
    assert first["result_version_count"] == 1
    assert asyncio.run(run()) == 0
    second = inspect_body(db, analysis_id)
    assert second["result_version_count"] == 1

    batch_id = seeded["batch_id"]
    assert db.scalar(select(BodyAnalysis.id).where(BodyAnalysis.id == analysis_id)) is not None
    cleanup = cleanup_batch(db, UUID(batch_id))
    assert cleanup["deleted_analyses"] == 1


def test_catalogue_member_fixture_creates_and_cleans_isolated_session(
    db, test_settings: Settings
) -> None:
    test_settings.body_analysis_local_fake_provider_enabled = True

    seeded = seed_catalogue_member(db, test_settings)

    user_id = UUID(seeded["user_id"])
    assert seeded["session_cookie_name"] == test_settings.session_cookie_name
    assert session_for_token(db, seeded["session_token"]).user_id == user_id

    result = cleanup_member(db, user_id)
    assert result["deleted_users"] == 1
    assert db.get(User, user_id) is None
    assert session_for_token(db, seeded["session_token"]) is None
