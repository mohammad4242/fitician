from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import DatabaseSession, get_current_user
from app.auth.models import User
from app.progress.schemas import Preset, ProgressOverview
from app.progress.service import overview

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])
Member = Annotated[User, Depends(get_current_user)]


@router.get("/overview", response_model=ProgressOverview)
def get_overview(
    db: DatabaseSession,
    user: Member,
    preset: Preset = "week",
    timezone: Annotated[str | None, Query(max_length=64)] = None,
) -> ProgressOverview:
    return overview(db, user.id, preset=preset, timezone=timezone)
