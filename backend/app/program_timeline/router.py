from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.database.session import get_db
from app.program_timeline.schemas import ProgramTimelineTodayResponse
from app.program_timeline.service import build_program_timeline
from app.time_context import validate_timezone_name

router = APIRouter(prefix="/api/v1/program-timeline", tags=["program-timeline"])
DatabaseSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/today", response_model=ProgramTimelineTodayResponse)
def read_program_timeline_today(
    db: DatabaseSession,
    user: CurrentUser,
    timezone: str | None = Query(default=None),
) -> ProgramTimelineTodayResponse:
    if timezone is not None:
        try:
            timezone = validate_timezone_name(timezone)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "TIMEZONE_INVALID"},
            ) from None
    return build_program_timeline(db, user_id=user.id, timezone_name=timezone)
