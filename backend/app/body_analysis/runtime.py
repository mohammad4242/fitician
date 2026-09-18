from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.task_provider import build_task_provider
from app.auth.dependencies import AppSettings, DatabaseSession
from app.body_analysis.admin_config.enums import AIExecutionBackend, AITaskType
from app.body_analysis.admin_config.models import AIModelCatalogEntry, AITaskConfig
from app.body_analysis.admin_config.service import (
    AIConfigError,
    decrypted_key,
)
from app.body_analysis.providers import AIProvider
from app.body_analysis.service import AnalysisExecutionConfig
from app.config import Settings


@dataclass(frozen=True)
class BodyAnalysisRuntime:
    provider: AIProvider
    config: AnalysisExecutionConfig


def get_body_analysis_runtime(
    request: Request,
    db: DatabaseSession,
    settings: AppSettings,
) -> BodyAnalysisRuntime:
    ai_client = getattr(request.app.state, "ai_http_client", None)
    agent_client = getattr(request.app.state, "agent_http_client", None)
    if not isinstance(ai_client, httpx.AsyncClient) or not isinstance(
        agent_client, httpx.AsyncClient
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "BODY_ANALYSIS_PROVIDER_UNAVAILABLE"},
        )
    try:
        return build_body_analysis_runtime(
            db,
            settings,
            ai_http_client=ai_client,
            agent_http_client=agent_client,
        )
    except (AIConfigError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "BODY_ANALYSIS_PROVIDER_UNAVAILABLE"},
        ) from error


def build_body_analysis_runtime(
    db: Session,
    settings: Settings,
    *,
    ai_http_client: httpx.AsyncClient,
    agent_http_client: httpx.AsyncClient,
) -> BodyAnalysisRuntime:
    task = db.scalar(
        select(AITaskConfig).where(AITaskConfig.task_type == AITaskType.BODY_PHOTO_ANALYSIS)
    )
    if task is None or not task.enabled:
        raise ValueError("body analysis task is not enabled")
    try:
        backend = AIExecutionBackend(task.execution_backend)
    except ValueError as error:
        raise ValueError("body analysis execution backend is invalid") from error
    client = ai_http_client if backend is AIExecutionBackend.API else agent_http_client
    key = (
        decrypted_key(db, provider=task.provider, settings=settings)
        if backend is AIExecutionBackend.API
        else None
    )
    configured = build_task_provider(
        task,
        settings=settings,
        http_client=client,
        agent_http_client=(
            agent_http_client if backend is AIExecutionBackend.AGENT_SERVICE else None
        ),
        api_key=key,
    )
    if configured.supports_cost_accounting:
        _validate_budget_preflight(db, task)
    return BodyAnalysisRuntime(
        provider=configured.provider,
        config=AnalysisExecutionConfig(
            provider_name=configured.provider_name,
            primary_model=configured.primary_model_id,
            fallback_models=configured.fallback_model_ids,
            prompt_version="body-analysis-v4-evidence",
            schema_version="4.0",
            temperature=task.temperature,
            max_output_tokens=task.max_output_tokens,
            timeout_seconds=task.timeout_seconds,
            minimum_confidence=task.minimum_confidence,
            max_cost_per_request=(
                task.max_cost_per_request
                if configured.supports_cost_accounting
                and task.max_cost_per_request
                and task.max_cost_per_request > 0
                else None
            ),
            routing_preferences=configured.routing_preferences,
        ),
    )


BodyAnalysisRuntimeDependency = Annotated[BodyAnalysisRuntime, Depends(get_body_analysis_runtime)]


def _validate_budget_preflight(db: Session, task: AITaskConfig) -> None:
    if task.max_cost_per_request is None or task.max_cost_per_request == 0:
        return
    model_ids = (task.primary_model_id, *task.fallback_model_ids)
    for model_id in model_ids:
        entry = db.scalar(
            select(AIModelCatalogEntry).where(
                AIModelCatalogEntry.provider == task.provider,
                AIModelCatalogEntry.model_id == model_id,
                AIModelCatalogEntry.available.is_(True),
                AIModelCatalogEntry.supports_image_input.is_(True),
                AIModelCatalogEntry.supports_structured_output.is_(True),
            )
        )
        if (
            entry is None
            or entry.context_length is None
            or entry.input_price_per_token is None
            or entry.output_price_per_token is None
            or entry.context_length < task.max_output_tokens
        ):
            raise ValueError("cannot evaluate image-analysis request cost")
        maximum_input_tokens = entry.context_length - task.max_output_tokens
        worst_case_cost = (
            entry.input_price_per_token * maximum_input_tokens
            + entry.output_price_per_token * task.max_output_tokens
        )
        if worst_case_cost > task.max_cost_per_request:
            raise ValueError("configured cost ceiling cannot cover the request bound")
