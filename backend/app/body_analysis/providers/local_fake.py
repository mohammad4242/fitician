from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from app.body_analysis.providers.models import (
    AIProviderError,
    ImageInput,
    ModelCapabilities,
    ModelCapabilityFilter,
    ProviderConnectionResult,
    ProviderErrorCode,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from app.config import Settings

LOCAL_FAKE_PROVIDER_NAME = "local_fake"
_MODEL_PATTERN = re.compile(r"^local-fake-v1-delay-(?P<milliseconds>[0-9]+)$")
_MAX_DELAY_MILLISECONDS = 600_000


def local_fake_provider_allowed(settings: Settings) -> bool:
    """Allow deterministic provider execution only in explicitly local/test modes."""
    return (
        settings.app_env in {"local", "test"}
        and settings.body_analysis_local_fake_provider_enabled
    )


class LocalFakeBodyAnalysisProvider:
    """Deterministic, network-free v4 provider for local resilience drills."""

    provider_name = LOCAL_FAKE_PROVIDER_NAME
    display_name = "Fitician local acceptance fake"
    provider_family = "local"
    supports_text_input = True
    supports_image_input = True
    supports_structured_output = True
    context_length = 65_536
    input_price_per_token = None
    output_price_per_token = None
    available = True

    def __init__(self, *, model_id: str, delay_seconds: float) -> None:
        self.model_id = model_id
        self.delay_seconds = delay_seconds

    @classmethod
    def from_model_id(cls, model_id: str) -> LocalFakeBodyAnalysisProvider:
        match = _MODEL_PATTERN.fullmatch(model_id)
        if match is None:
            raise ValueError("local fake model id must encode a bounded delay")
        milliseconds = int(match.group("milliseconds"))
        if milliseconds > _MAX_DELAY_MILLISECONDS:
            raise ValueError("local fake model id delay is too large")
        return cls(model_id=model_id, delay_seconds=milliseconds / 1000)

    async def analyze_images(
        self,
        request: StructuredGenerationRequest,
        *,
        images: tuple[ImageInput, ...],
    ) -> StructuredGenerationResponse:
        del request, images
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return StructuredGenerationResponse(
            payload=_v4_payload(),
            model_id=self.model_id,
            attempted_models=(self.model_id,),
            provider_request_id=f"local-fake:{self.model_id}",
            input_tokens=0,
            output_tokens=0,
            cost=None,
        )

    async def generate_structured_text(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        del request
        return StructuredGenerationResponse(
            payload={},
            model_id=self.model_id,
            attempted_models=(self.model_id,),
        )

    async def test_connection(self) -> ProviderConnectionResult:
        return ProviderConnectionResult(checked_at=datetime.now(UTC), model_count=1)

    async def list_models(
        self, filters: ModelCapabilityFilter | None = None
    ) -> tuple[ModelCapabilities, ...]:
        del filters
        return (
            ModelCapabilities(
                provider=self.provider_name,
                model_id=self.model_id,
                display_name=self.display_name,
                provider_family=self.provider_family,
                supports_text_input=self.supports_text_input,
                supports_image_input=self.supports_image_input,
                supports_structured_output=self.supports_structured_output,
                context_length=self.context_length,
                input_price_per_token=self.input_price_per_token,
                output_price_per_token=self.output_price_per_token,
            ),
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        if model_id != self.model_id:
            raise AIProviderError(ProviderErrorCode.MODEL_NOT_FOUND, "Local fake model not found.")
        return (await self.list_models())[0]

    def normalize_error(self, error: Exception) -> AIProviderError:
        if isinstance(error, AIProviderError):
            return error
        return AIProviderError(
            ProviderErrorCode.PROVIDER_UNAVAILABLE,
            "Local fake provider failed.",
        )


def _v4_payload() -> dict[str, Any]:
    areas = (
        "shoulders",
        "chest",
        "back",
        "lats",
        "arms",
        "forearms",
        "waist_midsection",
        "glutes",
        "quads",
        "hamstrings",
        "calves",
    )
    return {
        "schema_version": "4.0",
        "assessment_status": "complete",
        "area_observations": [
            {
                "area": area,
                "classification": "balanced",
                "evidence_strength": "moderate",
                "supporting_views": ["front", "side"],
                "observation_tags": ["relative_width"],
                "limitation_codes": [],
                "suggested_training_emphasis": [],
            }
            for area in areas
        ],
        "upper_lower_balance": {
            "state": "balanced",
            "evidence_strength": "moderate",
            "supporting_views": ["front", "side"],
        },
        "visible_symmetry": {
            "state": "no_clear_difference",
            "evidence_strength": "moderate",
            "supporting_views": ["front", "back"],
        },
    }
