"""Local-only durable Body Analysis acceptance fixture.

This module intentionally has no HTTP entry point. It seeds ordinary durable queue rows and
provides inspection/reclaim/cleanup commands for local failure drills.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

import app.main  # noqa: F401  # register all models before CLI queries
from app.auth.models import AuthSession, User
from app.auth.security import make_session_token
from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.models import BodyAnalysis
from app.body_analysis.providers import (
    LOCAL_FAKE_PROVIDER_NAME,
    local_fake_provider_allowed,
)
from app.body_analysis.service import AnalysisExecutionConfig, BodyAnalysisService
from app.body_photos.enums import BodyPhotoPurpose, BodyPhotoSessionState, BodyPhotoView
from app.body_photos.models import BodyPhoto, BodyPhotoSession
from app.config import Settings, get_settings
from app.database.session import get_engine
from app.profile.enums import FitnessGoal, Sex
from app.profile.models import BodyMeasurement, UserProfile


def local_fake_model_id(delay_seconds: float) -> str:
    milliseconds = round(delay_seconds * 1000)
    if milliseconds < 0 or milliseconds > 600_000:
        raise ValueError("delay must be between 0 and 600 seconds")
    return f"local-fake-v1-delay-{milliseconds}"


def _require_fixture_mode(settings: Settings) -> None:
    if not local_fake_provider_allowed(settings):
        raise RuntimeError(
            "local acceptance requires APP_ENV=local/test and "
            "BODY_ANALYSIS_LOCAL_FAKE_PROVIDER_ENABLED=true"
        )


def seed_body_jobs(
    db: Session,
    settings: Settings,
    *,
    count: int,
    delay_seconds: float,
) -> dict[str, Any]:
    _require_fixture_mode(settings)
    if count < 1 or count > 200:
        raise ValueError("count must be between 1 and 200")
    batch_id = uuid4()
    model_id = local_fake_model_id(delay_seconds)
    analysis_ids: list[str] = []
    for index in range(count):
        user_id = uuid4()
        user = User(
            id=user_id,
            email=f"local-acceptance-{batch_id}-{index}@example.invalid",
            password_hash="local-acceptance-fixture",
        )
        profile = UserProfile(
            user_id=user_id,
            sex=Sex.MALE,
            height_cm=178,
            fitness_goal=FitnessGoal.BUILD_MUSCLE,
        )
        measurement = BodyMeasurement(
            user_id=user_id,
            weight_kg=82.5,
            shoulder_circumference_cm=122,
            waist_circumference_cm=84,
            hip_circumference_cm=98,
        )
        photo_session = BodyPhotoSession(
            user_id=user_id,
            purpose=BodyPhotoPurpose.PROGRESS_CHECK,
            state=BodyPhotoSessionState.QUEUED,
            submitted_at=datetime.now(UTC),
        )
        db.add_all([user, profile, measurement, photo_session])
        db.flush()
        db.add_all(
            [
                BodyPhoto(
                    session_id=photo_session.id,
                    view=view,
                    storage_key=f"local-acceptance/{batch_id}/{index}/{view.value}.png",
                    mime_type="image/png",
                    byte_size=1,
                    width=1,
                    height=1,
                )
                for view in BodyPhotoView
            ]
        )
        db.flush()
        analysis = BodyAnalysisService(db).queue(
            photo_session.id,
            user_id,
            AnalysisExecutionConfig(
                provider_name=LOCAL_FAKE_PROVIDER_NAME,
                primary_model=model_id,
                prompt_version="local-acceptance-v1",
                schema_version="4.0",
                retry_limit=0,
                timeout_seconds=600,
            ),
            confirm_measurements_current=True,
            correlation_id=f"local-acceptance:{batch_id}",
        )
        analysis_ids.append(str(analysis.id))
    return {"batch_id": str(batch_id), "analysis_ids": analysis_ids, "count": count}


def seed_catalogue_member(db: Session, settings: Settings) -> dict[str, Any]:
    """Create an isolated local member session for authenticated cache drills."""
    _require_fixture_mode(settings)
    user = User(
        id=uuid4(),
        email=f"local-acceptance-catalogue-{uuid4()}@example.invalid",
        password_hash="local-acceptance-fixture",
    )
    raw_token, token_hash = make_session_token()
    db.add(user)
    db.flush()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
    )
    db.commit()
    return {
        "user_id": str(user.id),
        "session_cookie_name": settings.session_cookie_name,
        "session_token": raw_token,
    }


def cleanup_member(db: Session, user_id: UUID) -> dict[str, Any]:
    user_exists = db.get(User, user_id) is not None
    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    return {"user_id": str(user_id), "deleted_users": int(user_exists)}


def inspect_body(db: Session, analysis_id: UUID) -> dict[str, Any]:
    analysis = db.scalar(
        select(BodyAnalysis)
        .where(BodyAnalysis.id == analysis_id)
        .options(selectinload(BodyAnalysis.result_versions))
    )
    if analysis is None:
        raise ValueError(f"body analysis not found: {analysis_id}")
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status.value,
        "locked_by": analysis.locked_by,
        "locked_at": analysis.locked_at.isoformat() if analysis.locked_at else None,
        "attempt_count": analysis.attempt_count,
        "result_version_count": len(analysis.result_versions),
    }


def inspect_batch(db: Session, batch_id: UUID) -> dict[str, Any]:
    analyses = db.scalars(
        select(BodyAnalysis)
        .where(BodyAnalysis.correlation_id == f"local-acceptance:{batch_id}")
        .options(selectinload(BodyAnalysis.result_versions))
        .order_by(BodyAnalysis.created_at, BodyAnalysis.id)
    ).all()
    terminal_states = {
        BodyAnalysisStatus.REVIEW_PENDING,
        BodyAnalysisStatus.COMPLETED,
        BodyAnalysisStatus.FAILED,
    }
    return {
        "batch_id": str(batch_id),
        "analysis_ids": [str(analysis.id) for analysis in analyses],
        "queued": sum(analysis.status is BodyAnalysisStatus.QUEUED for analysis in analyses),
        "processing": sum(analysis.status is BodyAnalysisStatus.ANALYZING for analysis in analyses),
        "terminal": sum(analysis.status in terminal_states for analysis in analyses),
        "max_result_versions": max(
            (len(analysis.result_versions) for analysis in analyses), default=0
        ),
    }


def expire_body_lease(db: Session, settings: Settings, analysis_id: UUID) -> dict[str, Any]:
    analysis = db.get(BodyAnalysis, analysis_id)
    if analysis is None:
        raise ValueError(f"body analysis not found: {analysis_id}")
    if analysis.locked_at is None or analysis.status is not BodyAnalysisStatus.ANALYZING:
        raise ValueError("body analysis must be claimed and analyzing before lease expiry")
    analysis.locked_at = datetime.now(UTC) - timedelta(
        seconds=settings.body_analysis_worker_lease_seconds + 1
    )
    db.commit()
    return inspect_body(db, analysis_id)


def cleanup_batch(db: Session, batch_id: UUID) -> dict[str, Any]:
    prefix = f"local-acceptance:{batch_id}"
    analysis_ids = db.scalars(
        select(BodyAnalysis.id).where(BodyAnalysis.correlation_id == prefix)
    ).all()
    user_ids = db.scalars(
        select(User.id).where(User.email.like(f"local-acceptance-{batch_id}-%@example.invalid"))
    ).all()
    if analysis_ids:
        db.execute(delete(BodyAnalysis).where(BodyAnalysis.id.in_(analysis_ids)))
    if user_ids:
        db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()
    return {
        "batch_id": str(batch_id),
        "deleted_analyses": len(analysis_ids),
        "deleted_users": len(user_ids),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local deterministic Body Analysis acceptance fixture"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed-body")
    seed.add_argument("--count", type=int, default=1)
    seed.add_argument("--delay-seconds", type=float, default=0.0)
    inspect = commands.add_parser("inspect-body")
    inspect.add_argument("--analysis-id", type=UUID, required=True)
    expire = commands.add_parser("expire-body-lease")
    expire.add_argument("--analysis-id", type=UUID, required=True)
    batch = commands.add_parser("inspect-batch")
    batch.add_argument("--batch-id", type=UUID, required=True)
    cleanup = commands.add_parser("cleanup-batch")
    cleanup.add_argument("--batch-id", type=UUID, required=True)
    commands.add_parser("seed-catalogue-member")
    cleanup_user = commands.add_parser("cleanup-member")
    cleanup_user.add_argument("--user-id", type=UUID, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    settings = get_settings()
    engine = get_engine(settings)
    with Session(engine) as db:
        if arguments.command == "seed-body":
            result = seed_body_jobs(
                db, settings, count=arguments.count, delay_seconds=arguments.delay_seconds
            )
        elif arguments.command == "inspect-body":
            result = inspect_body(db, arguments.analysis_id)
        elif arguments.command == "expire-body-lease":
            result = expire_body_lease(db, settings, arguments.analysis_id)
        elif arguments.command == "inspect-batch":
            result = inspect_batch(db, arguments.batch_id)
        elif arguments.command == "seed-catalogue-member":
            result = seed_catalogue_member(db, settings)
        elif arguments.command == "cleanup-member":
            result = cleanup_member(db, arguments.user_id)
        else:
            result = cleanup_batch(db, arguments.batch_id)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
