from __future__ import annotations

import asyncio
import logging
import socket
from datetime import UTC, datetime, timedelta
from importlib import import_module
from typing import cast
from uuid import UUID, uuid4

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.body_analysis.enums import BodyAnalysisStatus
from app.body_analysis.models import BodyAnalysis
from app.body_analysis.providers import (
    LOCAL_FAKE_PROVIDER_NAME,
    AIProvider,
    AIProviderError,
    ImageInput,
    LocalFakeBodyAnalysisProvider,
    ProviderErrorCode,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    local_fake_provider_allowed,
)
from app.body_analysis.runtime import build_body_analysis_runtime
from app.body_analysis.service import BodyAnalysisLeaseLost, BodyAnalysisService
from app.config import Settings, get_settings
from app.database.session import get_engine
from app.jobs.heartbeat import async_heartbeat
from app.jobs.runtime import install_async_signal_handlers, wait_for_stop
from app.observability.logging import configure_structured_logging, log_event

import_module("app.main")  # Ensure all SQLAlchemy models and relationships are registered

logger = logging.getLogger(__name__)


class _UnavailableProvider:
    async def analyze_images(
        self,
        request: StructuredGenerationRequest,
        *,
        images: tuple[ImageInput, ...],
    ) -> StructuredGenerationResponse:
        del request, images
        raise AIProviderError(
            ProviderErrorCode.NOT_CONFIGURED,
            "The body analysis provider is not configured.",
        )

    def normalize_error(self, error: Exception) -> AIProviderError:
        if isinstance(error, AIProviderError):
            return error
        return AIProviderError(
            ProviderErrorCode.NOT_CONFIGURED,
            "The body analysis provider is not configured.",
        )


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


def _locked_body_analysis(
    db: Session,
    analysis_id: UUID,
    *,
    worker_id: str,
) -> BodyAnalysis | None:
    analysis = db.scalar(
        select(BodyAnalysis)
        .where(
            BodyAnalysis.id == analysis_id,
            BodyAnalysis.status == BodyAnalysisStatus.QUEUED,
            BodyAnalysis.locked_by == worker_id,
        )
        .options(selectinload(BodyAnalysis.session))
        .with_for_update()
    )
    if analysis is None:
        db.rollback()
    return analysis


def _release_body_analysis_lease(
    db: Session,
    analysis_id: UUID,
    *,
    worker_id: str,
) -> None:
    analysis = db.scalar(
        select(BodyAnalysis)
        .where(
            BodyAnalysis.id == analysis_id,
            BodyAnalysis.locked_by == worker_id,
        )
        .with_for_update()
    )
    if analysis is None:
        db.rollback()
        return
    analysis.locked_at = None
    analysis.locked_by = None
    db.commit()


async def process_body_analysis_job(
    db: Session,
    analysis_id: UUID,
    *,
    worker_id: str,
    settings: Settings,
    ai_http_client: httpx.AsyncClient,
    agent_http_client: httpx.AsyncClient,
    now: datetime | None = None,
) -> bool:
    """Execute one claimed analysis and release only the owning lease."""
    analysis = _locked_body_analysis(db, analysis_id, worker_id=worker_id)
    if analysis is None:
        return False
    execution_config = BodyAnalysisService.execution_config_for_analysis(analysis)
    db.commit()  # Release the claim row lock before the provider call.

    try:
        try:
            provider: AIProvider
            if analysis.provider == LOCAL_FAKE_PROVIDER_NAME:
                if not local_fake_provider_allowed(settings):
                    raise ValueError("local fake provider is disabled")
                provider = LocalFakeBodyAnalysisProvider.from_model_id(analysis.model_id)
            else:
                runtime = build_body_analysis_runtime(
                    db,
                    settings,
                    ai_http_client=ai_http_client,
                    agent_http_client=agent_http_client,
                )
                provider = runtime.provider
        except (ValueError, RuntimeError) as error:
            logger.warning(
                "Body analysis provider configuration unavailable for %s: %s",
                analysis_id,
                type(error).__name__,
            )
            provider = cast(AIProvider, _UnavailableProvider())
        await BodyAnalysisService(db).execute(
            analysis_id,
            provider,
            execution_config,
            worker_id=worker_id,
        )
    except BodyAnalysisLeaseLost:
        db.rollback()
        log_event(
            logger,
            "body analysis lease lost",
            job_id=str(analysis_id),
            worker_id=worker_id,
            status="lease_lost",
        )
        return False
    except Exception:
        db.rollback()
        logger.exception("Body analysis worker execution failed for %s", analysis_id)
        return False

    log_event(
        logger,
        "body analysis job processed",
        request_id=analysis.correlation_id,
        job_id=str(analysis.id),
        worker_id=worker_id,
        attempt=analysis.attempt_count,
        status=analysis.status.value,
    )
    _release_body_analysis_lease(db, analysis_id, worker_id=worker_id)
    return True


async def run_body_analysis_once(
    db: Session,
    *,
    settings: Settings,
    ai_http_client: httpx.AsyncClient,
    agent_http_client: httpx.AsyncClient,
    worker_id: str,
    now: datetime | None = None,
) -> int:
    current = now or datetime.now(UTC)
    analysis_ids = claim_body_analysis_jobs(
        db,
        worker_id=worker_id,
        now=current,
        lease_seconds=settings.body_analysis_worker_lease_seconds,
        batch_size=settings.body_analysis_worker_batch_size,
    )
    processed = 0
    for analysis_id in analysis_ids:
        processed += int(
            await process_body_analysis_job(
                db,
                analysis_id,
                worker_id=worker_id,
                settings=settings,
                ai_http_client=ai_http_client,
                agent_http_client=agent_http_client,
                now=current,
            )
        )
    return processed


def _worker_id() -> str:
    return f"{socket.gethostname()}:{uuid4()}"


async def run_worker(
    settings: Settings,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    configure_structured_logging()
    worker_id = _worker_id()
    requested_stop = stop_event or asyncio.Event()
    if stop_event is None:
        install_async_signal_handlers(requested_stop)
    engine = get_engine(settings)
    ai_timeout = httpx.Timeout(settings.openrouter_timeout_seconds)
    agent_timeout = httpx.Timeout(settings.agent_service_connect_timeout_seconds)
    async with (
        async_heartbeat(
            settings.job_heartbeat_path,
            service="body-analysis-worker",
            interval_seconds=settings.job_heartbeat_interval_seconds,
        ),
        httpx.AsyncClient(
            timeout=ai_timeout,
            proxy=settings.openrouter_proxy_url or None,
            trust_env=False,
        ) as ai_client,
        httpx.AsyncClient(timeout=agent_timeout, trust_env=False) as agent_http_client,
    ):
        while not requested_stop.is_set():
            try:
                with Session(engine) as db:
                    await run_body_analysis_once(
                        db,
                        settings=settings,
                        ai_http_client=ai_client,
                        agent_http_client=agent_http_client,
                        worker_id=worker_id,
                    )
            except Exception:
                logger.exception("Body analysis worker iteration failed")
            await wait_for_stop(requested_stop, settings.body_analysis_worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run_worker(get_settings()))
