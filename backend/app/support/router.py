from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.admin.dependencies import AdminUser
from app.auth.dependencies import (
    AppSettings,
    DatabaseSession,
    get_current_user,
    require_authenticated_mutation,
)
from app.auth.models import User
from app.support import service
from app.support.enums import SupportCategory, SupportStatus
from app.support.limits import limit_write
from app.support.schemas import (
    ReadInput,
    ReplyInput,
    StatusInput,
    SupportMessageResponse,
    TicketDetail,
    TicketInput,
    TicketPage,
    TicketResponse,
)

Member = Annotated[User, Depends(get_current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=160)]
router = APIRouter(prefix="/api/v1/support/tickets", tags=["support"])
admin_router = APIRouter(prefix="/api/v1/support/admin/tickets", tags=["admin-support"])
mutation = [Depends(require_authenticated_mutation)]


@router.get("", response_model=TicketPage)
def member_list(
    db: DatabaseSession,
    user: Member,
    status: SupportStatus | None = None,
    category: SupportCategory | None = None,
    search: Search = None,
    before: UUID | None = None,
    limit: Limit = 30,
) -> TicketPage:
    return service.list_tickets(
        db,
        user,
        admin=False,
        status=status,
        category=category,
        search=search,
        before=before,
        limit=limit,
    )


@router.post("", response_model=TicketResponse, status_code=201, dependencies=mutation)
async def create(
    payload: TicketInput, request: Request, db: DatabaseSession, user: Member, settings: AppSettings
) -> TicketResponse:
    await limit_write(request, db, settings, user, payload.request_id, create=True)
    return service.create_ticket(db, user, payload)


@router.get("/{ticket_id}", response_model=TicketDetail)
@router.get("/{ticket_id}/messages", response_model=TicketDetail)
def member_detail(
    ticket_id: UUID,
    db: DatabaseSession,
    user: Member,
    before: UUID | None = None,
    limit: Limit = 30,
) -> TicketDetail:
    return service.read_ticket(db, user, ticket_id, admin=False, before=before, limit=limit)


@router.post(
    "/{ticket_id}/messages",
    response_model=SupportMessageResponse,
    status_code=201,
    dependencies=mutation,
)
async def member_reply(
    ticket_id: UUID,
    payload: ReplyInput,
    request: Request,
    db: DatabaseSession,
    user: Member,
    settings: AppSettings,
) -> SupportMessageResponse:
    service.owned_ticket(db, user, ticket_id)
    await limit_write(request, db, settings, user, payload.request_id, create=False)
    return service.send_reply(db, user, ticket_id, payload, admin=False)


@router.put("/{ticket_id}/read", status_code=204, dependencies=mutation)
def member_read(ticket_id: UUID, payload: ReadInput, db: DatabaseSession, user: Member) -> Response:
    service.mark_read(db, user, ticket_id, payload.message_id, admin=False)
    return Response(status_code=204)


@admin_router.get("", response_model=TicketPage)
def admin_list(
    db: DatabaseSession,
    user: AdminUser,
    status: SupportStatus | None = None,
    category: SupportCategory | None = None,
    search: Search = None,
    before: UUID | None = None,
    limit: Limit = 30,
) -> TicketPage:
    return service.list_tickets(
        db,
        user,
        admin=True,
        status=status,
        category=category,
        search=search,
        before=before,
        limit=limit,
    )


@admin_router.get("/{ticket_id}", response_model=TicketDetail)
@admin_router.get("/{ticket_id}/messages", response_model=TicketDetail)
def admin_detail(
    ticket_id: UUID,
    db: DatabaseSession,
    user: AdminUser,
    before: UUID | None = None,
    limit: Limit = 30,
) -> TicketDetail:
    return service.read_ticket(db, user, ticket_id, admin=True, before=before, limit=limit)


@admin_router.post(
    "/{ticket_id}/messages",
    response_model=SupportMessageResponse,
    status_code=201,
    dependencies=mutation,
)
async def admin_reply(
    ticket_id: UUID,
    payload: ReplyInput,
    request: Request,
    db: DatabaseSession,
    user: AdminUser,
    settings: AppSettings,
) -> SupportMessageResponse:
    service.owned_ticket(db, user, ticket_id, admin=True)
    await limit_write(request, db, settings, user, payload.request_id, create=False)
    return service.send_reply(db, user, ticket_id, payload, admin=True)


@admin_router.put("/{ticket_id}/read", status_code=204, dependencies=mutation)
def admin_read(
    ticket_id: UUID, payload: ReadInput, db: DatabaseSession, user: AdminUser
) -> Response:
    service.mark_read(db, user, ticket_id, payload.message_id, admin=True)
    return Response(status_code=204)


@admin_router.patch("/{ticket_id}/status", response_model=TicketResponse, dependencies=mutation)
def admin_status(
    ticket_id: UUID, payload: StatusInput, db: DatabaseSession, user: AdminUser
) -> TicketResponse:
    return service.change_status(db, user, ticket_id, payload)
