import re
from datetime import datetime
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationDeviceTokenUpsertRequest(BaseModel):
    provider: Literal["fcm", "apns"] = "fcm"
    token: str = Field(min_length=1, max_length=4096)

    model_config = ConfigDict(extra="forbid")

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("Notification token must not be blank")
        return token


class NotificationDeviceResponse(BaseModel):
    id: UUID
    device_id: str
    platform: Literal["android", "ios"]
    app_version: str
    device_name: str | None
    has_active_token: bool
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime


class PersonalNotificationPreferences(BaseModel):
    messages: bool = True
    training_reminders: bool = False
    nutrition_reminders: bool = False
    return_reminders: bool = False
    training_time: str | None = None
    nutrition_time: str | None = None
    reminder_timezone: str | None = None

    @field_validator("training_time", "nutrition_time")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
            raise ValueError("Time must be HH:mm")
        return value

    @field_validator("reminder_timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Timezone must be a valid IANA name") from None
        return value


class NotificationPreferencesUpdateRequest(PersonalNotificationPreferences):
    enabled: bool
    approved_plans: bool
    required_reviews: bool
    body_analysis: bool
    cycle_reminders: bool
    physician_decisions: bool
    nutrition_updates: bool = True

    model_config = ConfigDict(extra="forbid")


class NotificationPreferencesResponse(PersonalNotificationPreferences):
    enabled: bool
    approved_plans: bool
    required_reviews: bool
    body_analysis: bool
    cycle_reminders: bool
    physician_decisions: bool
    nutrition_updates: bool
    updated_at: datetime | None


class NotificationInboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_type: str
    payload: dict[str, object]
    created_at: datetime
    read_at: datetime | None


class NotificationInboxPage(BaseModel):
    items: list[NotificationInboxResponse]
    unread_count: int
    older_cursor: UUID | None = None
