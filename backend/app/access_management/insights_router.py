from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.access_management import insights_service as service
from app.access_management import plan_insights
from app.access_management.insights_schemas import (
    AccessOverview,
    ActivityItem,
    AnalysisItem,
    LoginItem,
    MemberSummary,
    NutritionDetail,
    NutritionHistoryItem,
    Page,
    ProgressItem,
    UserInsights,
    WorkoutDetail,
    WorkoutHistoryItem,
)
from app.admin.dependencies import require_admin
from app.auth.dependencies import DatabaseSession

router = APIRouter(tags=["admin-access"], dependencies=[Depends(require_admin)])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=1000000)]


@router.get("/overview", response_model=AccessOverview)
def overview(db: DatabaseSession) -> AccessOverview:
    return service.overview(db)


@router.get("/users", response_model=Page[MemberSummary])
def users(
    db: DatabaseSession,
    q: Annotated[str | None, Query(max_length=320)] = None,
    limit: Limit = 25,
    offset: Offset = 0,
    signup_period: service.SignupPeriod = "all",
    from_date: date | None = None,
    to_date: date | None = None,
    sort: service.UserSort = "newest",
) -> Page[MemberSummary]:
    return service.users_page(
        db,
        q=q,
        limit=limit,
        offset=offset,
        signup_period=signup_period,
        from_date=from_date,
        to_date=to_date,
        sort=sort,
    )


@router.get("/users/{user_id}/insights", response_model=UserInsights)
def insights(user_id: UUID, db: DatabaseSession) -> UserInsights:
    return service.insights(db, user_id)


@router.get("/users/{user_id}/activity", response_model=Page[ActivityItem])
def activity(
    user_id: UUID,
    db: DatabaseSession,
    limit: Limit = 25,
    offset: Offset = 0,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
) -> Page[ActivityItem]:
    return service.activity_page(db, user_id, limit=limit, offset=offset, event_type=event_type)


@router.get("/users/{user_id}/logins", response_model=Page[LoginItem])
def logins(
    user_id: UUID, db: DatabaseSession, limit: Limit = 25, offset: Offset = 0
) -> Page[LoginItem]:
    return service.logins_page(db, user_id, limit=limit, offset=offset)


@router.get("/users/{user_id}/workout-plans", response_model=Page[WorkoutHistoryItem])
def workout_plans(
    user_id: UUID, db: DatabaseSession, limit: Limit = 25, offset: Offset = 0
) -> Page[WorkoutHistoryItem]:
    return plan_insights.workout_plans(db, user_id, limit=limit, offset=offset)


@router.get("/users/{user_id}/workout-plans/{plan_id}", response_model=WorkoutDetail)
def workout_detail(user_id: UUID, plan_id: UUID, db: DatabaseSession) -> WorkoutDetail:
    return plan_insights.workout_detail(db, user_id, plan_id)


@router.get("/users/{user_id}/nutrition-plans", response_model=Page[NutritionHistoryItem])
def nutrition_plans(
    user_id: UUID, db: DatabaseSession, limit: Limit = 25, offset: Offset = 0
) -> Page[NutritionHistoryItem]:
    return plan_insights.nutrition_plans(db, user_id, limit=limit, offset=offset)


@router.get("/users/{user_id}/nutrition-plans/{plan_id}", response_model=NutritionDetail)
def nutrition_detail(user_id: UUID, plan_id: UUID, db: DatabaseSession) -> NutritionDetail:
    return plan_insights.nutrition_detail(db, user_id, plan_id)


@router.get("/users/{user_id}/progress", response_model=Page[ProgressItem])
def progress(
    user_id: UUID, db: DatabaseSession, limit: Limit = 25, offset: Offset = 0
) -> Page[ProgressItem]:
    return service.progress_page(db, user_id, limit=limit, offset=offset)


@router.get("/users/{user_id}/body-analyses", response_model=Page[AnalysisItem])
def analyses(
    user_id: UUID, db: DatabaseSession, limit: Limit = 25, offset: Offset = 0
) -> Page[AnalysisItem]:
    return service.analyses_page(db, user_id, limit=limit, offset=offset)
