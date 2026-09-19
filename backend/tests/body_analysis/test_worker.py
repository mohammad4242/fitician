from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.models import BodyAnalysis, BodyAnalysisResultVersion
from app.body_analysis.providers import (
    AIProviderError,
    ProviderErrorCode,
    StructuredGenerationResponse,
)
from app.body_analysis.runtime import BodyAnalysisRuntime
from app.body_analysis.service import BodyAnalysisService
from app.body_analysis.worker import claim_body_analysis_jobs, process_body_analysis_job
from app.config import Settings
from app.notifications.models import NotificationOutboxEvent

from .test_execution_and_reviews import (
    _config,
    _FailingProvider,
    _normalized_payload,
    _Provider,
    _submitted_session,
    _TransientProvider,
)


class _BlockingProvider(_Provider):
    def __init__(self, *, error: Exception | None = None) -> None:
        super().__init__(_normalized_payload(classification="clear_lag"))
        self.error = error
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def analyze_images(self, request: object, *, images: tuple[object, ...]) -> object:
        self.started.set()
        await self.release.wait()
        if self.error is not None:
            self.calls += 1
            raise self.error
        return await super().analyze_images(request, images=images)


class _NamedProvider(_Provider):
    def __init__(self) -> None:
        super().__init__()

    async def analyze_images(self, request: object, *, images: tuple[object, ...]) -> object:
        response = await super().analyze_images(request, images=images)
        assert isinstance(response, StructuredGenerationResponse)
        return response.model_copy(
            update={
                "model_id": "winning-worker-model",
                "provider_request_id": "winning-worker-request",
            }
        )


async def _run_stale_worker_race(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    stale_provider: _BlockingProvider,
) -> tuple[UUID, bool, bool, datetime]:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    worker_a = "body-analysis-live-a"
    worker_b = "body-analysis-live-b"
    now = datetime.now(UTC)
    assert claim_body_analysis_jobs(
        db,
        worker_id=worker_a,
        now=now,
        lease_seconds=60,
        batch_size=1,
    ) == [analysis.id]

    winning_provider = _NamedProvider()
    providers = iter((stale_provider, winning_provider))
    monkeypatch.setattr(
        "app.body_analysis.worker.build_body_analysis_runtime",
        lambda *args, **kwargs: BodyAnalysisRuntime(provider=next(providers), config=_config()),
    )
    settings = Settings(app_env="test", _env_file=None)

    async with httpx.AsyncClient() as ai_client, httpx.AsyncClient() as agent_client:
        worker_a_task = asyncio.create_task(
            process_body_analysis_job(
                db,
                analysis.id,
                worker_id=worker_a,
                settings=settings,
                ai_http_client=ai_client,
                agent_http_client=agent_client,
                now=now,
            )
        )
        await stale_provider.started.wait()

        analysis.locked_at = datetime.now(UTC) - timedelta(seconds=61)
        db.commit()
        assert claim_body_analysis_jobs(
            db,
            worker_id=worker_b,
            now=datetime.now(UTC),
            lease_seconds=60,
            batch_size=1,
        ) == [analysis.id]
        worker_b_processed = await process_body_analysis_job(
            db,
            analysis.id,
            worker_id=worker_b,
            settings=settings,
            ai_http_client=ai_client,
            agent_http_client=agent_client,
            now=datetime.now(UTC),
        )

        db.refresh(analysis)
        winning_available_at = analysis.available_at
        stale_provider.release.set()
        worker_a_processed = await worker_a_task

    return analysis.id, worker_a_processed, worker_b_processed, winning_available_at


def _analysis_events(db: Session, analysis_id: UUID) -> list[NotificationOutboxEvent]:
    prefix = f"body-analysis:{analysis_id}:"
    return list(
        db.scalars(
            select(NotificationOutboxEvent).where(
                NotificationOutboxEvent.deduplication_key.like(f"{prefix}%")
            )
        ).all()
    )


def test_stale_worker_success_cannot_finalize_after_reclaim(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    stale_provider = _BlockingProvider()
    analysis_id, stale_processed, winning_processed, _ = asyncio.run(
        _run_stale_worker_race(db, monkeypatch, stale_provider)
    )

    assert stale_processed is False
    assert winning_processed is True
    assert stale_provider.calls == 1
    persisted = db.get(BodyAnalysis, analysis_id)
    assert persisted is not None
    db.refresh(persisted)
    assert persisted.status is BodyAnalysisStatus.REVIEW_PENDING
    assert persisted.model_id == "winning-worker-model"
    assert persisted.provider_request_id == "winning-worker-request"
    assert persisted.error_code is None
    assert persisted.error_message is None
    assert persisted.locked_by is None
    assert persisted.locked_at is None
    versions = list(
        db.scalars(
            select(BodyAnalysisResultVersion).where(
                BodyAnalysisResultVersion.analysis_id == analysis_id
            )
        ).all()
    )
    assert len(versions) == 1
    assert versions[0].normalized_result["findings"][0]["classification"] == "clear_lag"
    events = _analysis_events(db, analysis_id)
    assert [event.event_type for event in events] == ["body_analysis_completed"]
    assert any(record.getMessage() == "body analysis lease lost" for record in caplog.records)
    assert not any("execution failed" in record.getMessage() for record in caplog.records)


def test_stale_worker_failure_cannot_mutate_successful_reclaim(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_provider = _BlockingProvider(
        error=AIProviderError(ProviderErrorCode.TIMEOUT, "provider timed out")
    )
    analysis_id, stale_processed, winning_processed, winning_available_at = asyncio.run(
        _run_stale_worker_race(db, monkeypatch, stale_provider)
    )

    assert stale_processed is False
    assert winning_processed is True
    assert stale_provider.calls == 1
    persisted = db.get(BodyAnalysis, analysis_id)
    assert persisted is not None
    db.refresh(persisted)
    assert persisted.status is BodyAnalysisStatus.REVIEW_PENDING
    assert persisted.available_at == winning_available_at
    assert persisted.attempt_count == 2
    assert persisted.error_code is None
    assert persisted.error_message is None
    assert persisted.locked_by is None
    assert persisted.locked_at is None
    versions = list(
        db.scalars(
            select(BodyAnalysisResultVersion).where(
                BodyAnalysisResultVersion.analysis_id == analysis_id
            )
        ).all()
    )
    assert len(versions) == 1
    assert versions[0].normalized_result["findings"][0]["classification"] == "clear_lag"
    events = _analysis_events(db, analysis_id)
    assert [event.event_type for event in events] == ["body_analysis_completed"]


def test_owned_worker_records_terminal_failure_and_releases_lease(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    worker_id = "body-analysis-owned-failure"
    now = datetime.now(UTC)
    assert claim_body_analysis_jobs(
        db,
        worker_id=worker_id,
        now=now,
        lease_seconds=60,
        batch_size=1,
    ) == [analysis.id]
    provider = _FailingProvider()
    monkeypatch.setattr(
        "app.body_analysis.worker.build_body_analysis_runtime",
        lambda *args, **kwargs: BodyAnalysisRuntime(provider=provider, config=_config()),
    )

    async def run() -> bool:
        async with httpx.AsyncClient() as ai_client, httpx.AsyncClient() as agent_client:
            return await process_body_analysis_job(
                db,
                analysis.id,
                worker_id=worker_id,
                settings=Settings(app_env="test", _env_file=None),
                ai_http_client=ai_client,
                agent_http_client=agent_client,
                now=now,
            )

    assert asyncio.run(run()) is True
    db.refresh(analysis)
    assert analysis.status is BodyAnalysisStatus.FAILED
    assert analysis.error_code == ProviderErrorCode.UNAUTHORIZED.value
    assert analysis.completed_at is not None
    assert analysis.locked_by is None
    assert analysis.locked_at is None
    assert [event.event_type for event in _analysis_events(db, analysis.id)] == [
        "body_analysis_failed"
    ]


def test_owned_worker_requeues_retryable_failure_and_releases_lease(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, photo_session = _submitted_session(db)
    config = _config().model_copy(
        update={"retry_limit": 1, "retry_base_seconds": 1, "retry_max_seconds": 2}
    )
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, config)
    worker_id = "body-analysis-owned-retry"
    now = datetime.now(UTC)
    assert claim_body_analysis_jobs(
        db,
        worker_id=worker_id,
        now=now,
        lease_seconds=60,
        batch_size=1,
    ) == [analysis.id]
    provider = _TransientProvider()
    monkeypatch.setattr(
        "app.body_analysis.worker.build_body_analysis_runtime",
        lambda *args, **kwargs: BodyAnalysisRuntime(provider=provider, config=config),
    )

    async def run() -> bool:
        async with httpx.AsyncClient() as ai_client, httpx.AsyncClient() as agent_client:
            return await process_body_analysis_job(
                db,
                analysis.id,
                worker_id=worker_id,
                settings=Settings(app_env="test", _env_file=None),
                ai_http_client=ai_client,
                agent_http_client=agent_client,
                now=now,
            )

    assert asyncio.run(run()) is True
    db.refresh(analysis)
    assert analysis.status is BodyAnalysisStatus.QUEUED
    assert analysis.error_code == ProviderErrorCode.TIMEOUT.value
    assert analysis.completed_at is None
    assert analysis.available_at > now
    assert analysis.locked_by is None
    assert analysis.locked_at is None
    assert _analysis_events(db, analysis.id) == []


def test_claim_body_analysis_jobs_assigns_a_lease_and_is_bounded(db: Session) -> None:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    now = datetime.now(UTC)

    claimed = claim_body_analysis_jobs(
        db,
        worker_id="body-analysis-test-1",
        now=now,
        lease_seconds=60,
        batch_size=1,
    )

    assert claimed == [analysis.id]
    db.refresh(analysis)
    assert analysis.status is BodyAnalysisStatus.QUEUED
    assert analysis.locked_by == "body-analysis-test-1"
    assert analysis.locked_at == now


def test_claim_body_analysis_jobs_reclaims_stale_analysis(db: Session) -> None:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    stale_at = datetime.now(UTC) - timedelta(minutes=20)
    analysis.status = BodyAnalysisStatus.ANALYZING
    analysis.locked_by = "dead-worker"
    analysis.locked_at = stale_at
    db.commit()
    now = datetime.now(UTC)

    claimed = claim_body_analysis_jobs(
        db,
        worker_id="body-analysis-test-2",
        now=now,
        lease_seconds=60,
        batch_size=1,
    )

    assert claimed == [analysis.id]
    db.refresh(analysis)
    assert analysis.status is BodyAnalysisStatus.QUEUED
    assert analysis.locked_by == "body-analysis-test-2"
    assert analysis.locked_at == now


def test_claim_body_analysis_jobs_skips_a_live_lease(db: Session) -> None:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    analysis.locked_by = "live-worker"
    analysis.locked_at = datetime.now(UTC)
    db.commit()

    claimed = claim_body_analysis_jobs(
        db,
        worker_id="body-analysis-test-3",
        now=datetime.now(UTC),
        lease_seconds=60,
        batch_size=1,
    )

    assert claimed == []


def test_process_body_analysis_job_executes_once_and_releases_lease(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, photo_session = _submitted_session(db)
    analysis = BodyAnalysisService(db).queue(photo_session.id, user.id, _config())
    now = datetime.now(UTC)
    worker_id = "body-analysis-test-process"
    assert claim_body_analysis_jobs(
        db,
        worker_id=worker_id,
        now=now,
        lease_seconds=60,
        batch_size=1,
    ) == [analysis.id]
    provider = _Provider()
    monkeypatch.setattr(
        "app.body_analysis.worker.build_body_analysis_runtime",
        lambda *args, **kwargs: BodyAnalysisRuntime(provider=provider, config=_config()),
    )
    ai_client = httpx.AsyncClient()
    agent_client = httpx.AsyncClient()
    try:
        processed = asyncio.run(
            process_body_analysis_job(
                db,
                analysis.id,
                worker_id=worker_id,
                settings=Settings(app_env="test", _env_file=None),
                ai_http_client=ai_client,
                agent_http_client=agent_client,
                now=now,
            )
        )
    finally:
        asyncio.run(ai_client.aclose())
        asyncio.run(agent_client.aclose())

    assert processed is True
    assert provider.calls == 1
    db.refresh(analysis)
    assert analysis.status is BodyAnalysisStatus.REVIEW_PENDING
    assert analysis.locked_by is None
    assert analysis.locked_at is None
