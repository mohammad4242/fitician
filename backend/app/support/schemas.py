from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.support.enums import SupportCategory, SupportStatus


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def clean_text(cls, value: object) -> object:
        if type(value) is str:
            if "\x00" in value or not value.strip():
                raise ValueError("Text must not be blank or contain null bytes")
            return value.strip()
        return value


class SupportMetadata(StrictInput):
    platform: Literal["web", "android", "ios"]
    app_version: str | None = Field(default=None, max_length=40)
    build_version: str | None = Field(default=None, max_length=40)
    locale: str | None = Field(default=None, max_length=16)


class TicketInput(StrictInput):
    category: SupportCategory
    subject: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    request_id: UUID
    metadata: SupportMetadata | None = None


class ReplyInput(StrictInput):
    body: str = Field(min_length=1, max_length=4000)
    request_id: UUID


class StatusInput(StrictInput):
    status: SupportStatus
    request_id: UUID


class ReadInput(StrictInput):
    message_id: UUID


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    category: SupportCategory
    subject: str
    status: SupportStatus
    troubleshooting_metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    resolved_at: datetime | None


class SupportMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sender_id: UUID | None
    sender_role: Literal["member", "admin"]
    body: str
    created_at: datetime


class TicketDetail(BaseModel):
    ticket: TicketResponse
    viewer_id: UUID
    messages: list[SupportMessageResponse]
    unread_count: int
    older_cursor: UUID | None


class TicketPage(BaseModel):
    items: list[TicketResponse]
    total: int
    open_count: int
    older_cursor: UUID | None
