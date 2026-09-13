from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_MEMBER_TIMEZONE = "Asia/Tehran"


def validate_timezone_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Timezone must be a valid IANA timezone name")
    timezone_name = value.strip()
    if not timezone_name:
        raise ValueError("Timezone must be a valid IANA timezone name")
    try:
        ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ValueError("Timezone must be a valid IANA timezone name") from error
    return timezone_name


def member_timezone_or_default(*values: str | None) -> str:
    for value in values:
        if value is None:
            continue
        try:
            return validate_timezone_name(value)
        except ValueError:
            continue
    return DEFAULT_MEMBER_TIMEZONE


def local_date_for_timezone(
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> date:
    timezone = ZoneInfo(validate_timezone_name(timezone_name))
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return current.astimezone(timezone).date()


def local_midnight_utc(local_date: date, timezone_name: str) -> datetime:
    timezone = ZoneInfo(validate_timezone_name(timezone_name))
    return datetime.combine(local_date, time.min, tzinfo=timezone).astimezone(UTC)


def fitician_weekday(value: date) -> int:
    return (value.weekday() + 2) % 7
