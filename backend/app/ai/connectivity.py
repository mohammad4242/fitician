"""Authenticated, bounded Agent connectivity checks without running a model."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import AppSettings, get_current_user
from app.auth.models import User
from app.body_analysis.providers.agent_service import AgentServiceProvider
from app.body_analysis.providers.models import AIProviderError, ProviderErrorCode

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/connectivity")
async def agent_connectivity(
    request: Request,
    _user: Annotated[User, Depends(get_current_user)],
    settings: AppSettings,
) -> dict[str, bool | str | None]:
    client = getattr(request.app.state, "agent_http_client", None)
    if not isinstance(client, httpx.AsyncClient):
        return {"network_unavailable": False, "error_code": "not_configured"}
    provider = AgentServiceProvider(
        client,
        base_url=settings.agent_service_base_url,
        token=settings.agent_service_token,
        agent_name="codex",
        connect_timeout_seconds=settings.agent_service_connect_timeout_seconds,
    )
    try:
        await provider.ensure_connection()
    except AIProviderError as error:
        return {
            "network_unavailable": error.code is ProviderErrorCode.AGENT_NETWORK_UNAVAILABLE,
            "error_code": error.code.value,
        }
    return {"network_unavailable": False, "error_code": None}
