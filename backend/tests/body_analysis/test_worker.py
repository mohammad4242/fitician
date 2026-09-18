from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.service import BodyAnalysisService
from app.body_analysis.worker import claim_body_analysis_jobs

from .test_execution_and_reviews import _config, _submitted_session


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
