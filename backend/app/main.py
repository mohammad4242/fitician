import asyncio
import logging
import mimetypes
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.access_management.exceptions import AccessManagementError
from app.access_management.router import router as access_management_router
from app.account_deletion.router import router as account_deletion_router
from app.account_deletion.scheduler import account_deletion_scheduler_loop
from app.admin.router import router as admin_router
from app.admin_audit.router import router as admin_audit_router
from app.auth.providers import (
    build_apple_identity_provider,
    build_email_provider,
    build_google_identity_provider,
    build_sms_provider,
)
from app.auth.router import router as auth_router
from app.billing.admin_router import router as billing_admin_router
from app.billing.exceptions import BillingError
from app.billing.providers import build_payment_providers
from app.billing.router import router as billing_router
from app.body_analysis.admin_config.crypto import CredentialEncryptionError
from app.body_analysis.admin_config.router import router as admin_ai_settings_router
from app.body_analysis.admin_config.service import sync_agent_service_proxy
from app.body_analysis.comparison_router import router as body_progress_comparison_router
from app.body_analysis.history_router import router as body_progress_history_router
from app.body_analysis.router import admin_router as body_analysis_admin_router
from app.body_analysis.router import review_router as body_analysis_review_router
from app.body_analysis.router import router as body_analysis_router
from app.body_photos.router import router as body_photo_router
from app.config import Settings, get_settings
from app.database.session import get_engine
from app.entitlements.exceptions import (
    AccessTermTooShortError,
    EntitlementQuotaExceededError,
    EntitlementRequiredError,
)
from app.entitlements.router import router as entitlements_router
from app.errors import (
    CORRELATION_ID_HEADER,
    build_error_response,
    create_request_id,
    error_response,
)
from app.exercises.router import router as exercises_router
from app.infrastructure.redis import create_redis_service
from app.media.delivery import deliver_public_media
from app.media.factory import build_s3_storage
from app.media.storage import ObjectStorage
from app.notifications.router import router as notifications_router
from app.nutrition.price_scheduler import scheduler_loop
from app.nutrition.retention_scheduler import retention_scheduler_loop
from app.nutrition.router import router as nutrition_router
from app.profile.router import router as profile_router
from app.program_timeline.router import router as program_timeline_router
from app.workout_cycles.router import router as workout_cycles_router
from app.workout_reviews.router import (
    member_router as workout_member_reviews_router,
)
from app.workout_reviews.router import (
    router as workout_reviews_router,
)
from app.workouts.router import router as workout_plans_router

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    public_media_storage: ObjectStorage | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    active_settings.media_root.mkdir(parents=True, exist_ok=True)
    mimetypes.add_type("image/webp", ".webp")
    if active_settings.media_storage_backend == "s3" and public_media_storage is None:
        public_media_storage = build_s3_storage(active_settings)
    redis_service = create_redis_service(active_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        zen_timeout = httpx.Timeout(active_settings.opencode_zen_timeout_seconds)
        ai_timeout = httpx.Timeout(active_settings.openrouter_timeout_seconds)
        agent_timeout = httpx.Timeout(active_settings.agent_service_connect_timeout_seconds)
        food_price_timeout = httpx.Timeout(active_settings.food_price_provider_timeout_seconds)
        async with (
            httpx.AsyncClient(
                timeout=zen_timeout,
                proxy=active_settings.opencode_zen_proxy_url or None,
                trust_env=False,
            ) as zen_client,
            httpx.AsyncClient(
                timeout=ai_timeout,
                proxy=active_settings.openrouter_proxy_url or None,
                trust_env=False,
            ) as ai_client,
            httpx.AsyncClient(timeout=agent_timeout, trust_env=False) as agent_client,
            httpx.AsyncClient(timeout=food_price_timeout, trust_env=False) as food_price_client,
        ):
            app.state.zen_http_client = zen_client
            app.state.ai_http_client = ai_client
            app.state.agent_http_client = agent_client
            app.state.food_price_http_client = food_price_client
            app.state.redis = redis_service
            background_tasks: list[asyncio.Task[None]] = []
            if active_settings.app_env != "test":
                try:
                    with Session(get_engine(active_settings.database_url)) as db:
                        await sync_agent_service_proxy(
                            db,
                            client=agent_client,
                            settings=active_settings,
                        )
                except (CredentialEncryptionError, SQLAlchemyError) as error:
                    logger.warning("Agent Service proxy startup sync failed: %s", error)
                background_tasks.append(
                    asyncio.create_task(
                        scheduler_loop(
                            active_settings,
                            food_price_client,
                            agent_http_client=agent_client,
                        )
                    )
                )
                background_tasks.append(
                    asyncio.create_task(retention_scheduler_loop(active_settings))
                )
                if active_settings.account_deletion_enabled:
                    background_tasks.append(
                        asyncio.create_task(account_deletion_scheduler_loop(active_settings))
                    )
            try:
                yield
            finally:
                for task in background_tasks:
                    task.cancel()
                try:
                    await asyncio.gather(*background_tasks)
                except asyncio.CancelledError:
                    pass
                await redis_service.close()

    app = FastAPI(title="Fitician API", lifespan=lifespan)
    app.state.billing_providers = build_payment_providers(active_settings)
    app.state.email_provider = build_email_provider(active_settings)
    app.state.sms_provider = build_sms_provider(active_settings)
    app.state.google_identity_provider = build_google_identity_provider(active_settings)
    app.state.apple_identity_provider = build_apple_identity_provider(active_settings)
    app.dependency_overrides[get_settings] = lambda: active_settings

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        with Session(get_engine(active_settings.database_url)) as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_frontend_origins),
        allow_credentials=True,
        allow_methods=["DELETE", "GET", "PATCH", "POST", "PUT"],
        allow_headers=[
            "Content-Type",
            "Idempotency-Key",
            CORRELATION_ID_HEADER,
            "X-Fitician-Food-Photo-Consent",
            "X-Fitician-Client-Crop-Confirmed",
            "X-Fitician-Client-Crop-Confidence",
            "X-Fitician-Original-Height",
            "X-Fitician-Crop-Top",
            "X-Fitician-Crop-Bottom",
            "X-Fitician-Processed-SHA256",
            "X-Fitician-Crop-Evidence-SHA256",
        ],
        expose_headers=[CORRELATION_ID_HEADER],
    )

    @app.middleware("http")
    async def correlation_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = create_request_id(request.headers.get(CORRELATION_ID_HEADER))
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request exception", extra={"request_id": request_id})
            raise
        response.headers[CORRELATION_ID_HEADER] = request_id
        return response

    def request_id(request: Request) -> str:
        return create_request_id(getattr(request.state, "request_id", None))

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
        return build_error_response(error, request_id(request))

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(
        request: Request,
        _error: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception(
            "Database request failed",
            extra={"request_id": request_id(request)},
        )
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            {"code": "SERVICE_UNAVAILABLE"},
            request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        error_types = {item["type"] for item in error.errors()}
        error_code: str | None = None
        error_message: str | None = None
        if "AGE_NOT_SUPPORTED" in error_types:
            error_code = "AGE_NOT_SUPPORTED"
            error_message = "فیتیشن در حال حاضر فقط برای افراد ۱۸ سال و بالاتر ارائه می‌شود."
        elif "AGE_OUT_OF_RANGE" in error_types:
            error_code = "AGE_OUT_OF_RANGE"
            error_message = "تاریخ تولد واردشده پشتیبانی نمی‌شود."
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"code": error_code or "VALIDATION_ERROR", "message": error_message}
            if error_code is not None
            else {"code": "VALIDATION_ERROR"},
            request_id(request),
            fields=error.errors(),
            retryable=False,
        )

    @app.exception_handler(EntitlementRequiredError)
    async def entitlement_required_error_handler(
        request: Request,
        error: EntitlementRequiredError,
    ) -> JSONResponse:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            {"code": "ENTITLEMENT_REQUIRED"},
            request_id(request),
            meta={
                "entitlement": error.entitlement.value,
                "eligible_packages": [package.value for package in error.eligible_packages],
            },
            retryable=False,
        )

    @app.exception_handler(EntitlementQuotaExceededError)
    async def entitlement_quota_error_handler(
        request: Request,
        error: EntitlementQuotaExceededError,
    ) -> JSONResponse:
        return error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {"code": "ENTITLEMENT_QUOTA_EXCEEDED"},
            request_id(request),
            headers={"Retry-After": str(error.retry_after_seconds)},
            meta={
                "entitlement": error.entitlement.value,
                "reset_at": error.reset_at.isoformat(),
                "retry_after_seconds": error.retry_after_seconds,
            },
            retryable=True,
        )

    @app.exception_handler(AccessTermTooShortError)
    async def access_term_too_short_error_handler(
        request: Request,
        error: AccessTermTooShortError,
    ) -> JSONResponse:
        return error_response(
            status.HTTP_403_FORBIDDEN,
            {"code": "ACCESS_TERM_TOO_SHORT"},
            request_id(request),
            meta={
                "requested_weeks": error.requested_weeks,
                "maximum_weeks": error.maximum_weeks,
            },
            retryable=False,
        )

    @app.exception_handler(BillingError)
    async def billing_error_handler(
        request: Request,
        error: BillingError,
    ) -> JSONResponse:
        return error_response(
            error.status_code,
            {"code": error.code, "message": error.message},
            request_id(request),
        )

    @app.exception_handler(AccessManagementError)
    async def access_management_error_handler(
        request: Request,
        error: AccessManagementError,
    ) -> JSONResponse:
        return error_response(
            error.status_code,
            {"code": error.code, "message": error.message},
            request_id(request),
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, _error: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled application exception",
            extra={"request_id": request_id(request)},
        )
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"code": "INTERNAL_SERVER_ERROR"},
            request_id(request),
        )

    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(billing_admin_router)
    app.include_router(admin_audit_router)
    app.include_router(access_management_router)
    app.include_router(entitlements_router)
    app.include_router(account_deletion_router)
    app.include_router(body_photo_router)
    app.include_router(body_analysis_router)
    app.include_router(body_progress_comparison_router)
    app.include_router(body_progress_history_router)
    app.include_router(profile_router)
    app.include_router(program_timeline_router)
    app.include_router(nutrition_router)
    app.include_router(notifications_router)
    app.include_router(workout_plans_router)
    app.include_router(workout_reviews_router)
    app.include_router(workout_member_reviews_router)
    app.include_router(workout_cycles_router)
    app.include_router(exercises_router)
    app.include_router(admin_router)
    app.include_router(admin_ai_settings_router)
    app.include_router(body_analysis_review_router)
    app.include_router(body_analysis_admin_router)

    @app.api_route(
        f"{active_settings.media_public_path.rstrip('/')}/{{media_path:path}}",
        methods=["GET", "HEAD"],
        name="public-media",
        include_in_schema=False,
    )
    async def public_media(media_path: str) -> Response:
        return await deliver_public_media(
            media_path,
            settings=active_settings,
            storage=public_media_storage,
        )

    return app


app = create_app()
