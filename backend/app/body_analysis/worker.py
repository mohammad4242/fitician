from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.models import BodyAnalysis


def claim_body_analysis_jobs(
    db: Session,
    *,
    worker_id: str,
    now: datetime,
    lease_seconds: int,
    batch_size: int,
) -> list[UUID]:
    """Claim queued or stale body-analysis rows with a short DB lease.

    The claim transaction is deliberately separate from provider execution. A
    worker crash therefore leaves a timestamped lease that another worker can
    reclaim after ``lease_seconds``.
    """
    stale_before = now - timedelta(seconds=lease_seconds)
    claimable = or_(
        and_(
            BodyAnalysis.status == BodyAnalysisStatus.QUEUED,
            BodyAnalysis.available_at <= now,
            or_(
                BodyAnalysis.locked_at.is_(None),
                BodyAnalysis.locked_at <= stale_before,
            ),
        ),
        and_(
            BodyAnalysis.status == BodyAnalysisStatus.ANALYZING,
            BodyAnalysis.locked_at <= stale_before,
        ),
    )
    analyses = db.scalars(
        select(BodyAnalysis)
        .where(claimable)
        .order_by(BodyAnalysis.available_at, BodyAnalysis.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).all()
    if not analyses:
        db.rollback()
        return []

    for analysis in analyses:
        analysis.status = BodyAnalysisStatus.QUEUED
        analysis.available_at = now
        analysis.locked_at = now
        analysis.locked_by = worker_id
    db.commit()
    return [analysis.id for analysis in analyses]
