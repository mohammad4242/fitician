from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.runtime import BodyAnalysisRuntime
from app.body_analysis.service import BodyAnalysisService
from app.body_analysis.worker import claim_body_analysis_jobs, process_body_analysis_job
from app.config import Settings

from .test_execution_and_reviews import _config, _Provider, _submitted_session


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
