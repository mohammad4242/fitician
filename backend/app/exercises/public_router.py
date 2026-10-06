"""Read-only public exercises. Publication is independent of member visibility."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.auth.dependencies import DatabaseSession
from app.exercises.public_projection import public_detail, public_summary
from app.exercises.public_schemas import (
    PublicExerciseDetail,
    PublicExerciseFilters,
    PublicExercisePage,
)
from app.exercises.router import categories
from app.exercises.schemas import ExerciseCategories
from app.exercises.service import PUBLISHED_SLUGS, get_active_exercise_by_slug, list_exercises
from app.infrastructure.rate_limiter import RedisRateLimitUnavailable


async def public_read_limit(request: Request, response: Response) -> None:
    # Revalidate publication on every request; never cache revoked approval.
    response.headers["Cache-Control"] = "no-store"
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return  # Existing test/development infrastructure disables distributed limits.
    try:
        result = await limiter.consume(
            namespace="public-exercises",
            operation="read",
            actor=request.client.host if request.client else "unknown",
            limit=120,
            window_seconds=60,
        )
    except RedisRateLimitUnavailable:
        raise HTTPException(503, detail={"code": "RATE_LIMIT_UNAVAILABLE"}) from None
    if not result.allowed:
        raise HTTPException(
            429,
            detail={"code": "RATE_LIMITED"},
            headers={"Retry-After": str(result.retry_after_seconds)},
        )


router = APIRouter(
    prefix="/api/v1/public", tags=["public-exercises"], dependencies=[Depends(public_read_limit)]
)


@router.get("/exercise-categories", response_model=ExerciseCategories)
def public_categories() -> ExerciseCategories:
    return categories()


@router.get("/exercises", response_model=PublicExercisePage)
def public_exercises(
    filters: Annotated[PublicExerciseFilters, Query()], db: DatabaseSession
) -> PublicExercisePage:
    records, total = list_exercises(db, filters, public_only=True)
    return PublicExercisePage(
        items=[public_summary(record) for record in records],
        page=filters.page,
        page_size=filters.page_size,
        total=total,
        total_pages=(total + filters.page_size - 1) // filters.page_size,
    )


@router.get("/exercises/{slug}", response_model=PublicExerciseDetail)
def public_exercise(slug: str, db: DatabaseSession) -> PublicExerciseDetail:
    record = get_active_exercise_by_slug(db, slug)
    if record is None or not record.is_public or record.needs_review or slug not in PUBLISHED_SLUGS:
        raise HTTPException(404, detail={"code": "EXERCISE_NOT_FOUND"})
    return public_detail(record)
