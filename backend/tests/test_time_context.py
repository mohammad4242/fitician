from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.time_context import (
    DEFAULT_MEMBER_TIMEZONE,
    fitician_weekday,
    local_date_for_timezone,
    local_midnight_utc,
    member_timezone_or_default,
    validate_timezone_name,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 9, 12), 0),  # Saturday
        (date(2026, 9, 13), 1),  # Sunday
        (date(2026, 9, 14), 2),  # Monday
        (date(2026, 9, 15), 3),  # Tuesday
        (date(2026, 9, 16), 4),  # Wednesday
        (date(2026, 9, 17), 5),  # Thursday
        (date(2026, 9, 18), 6),  # Friday
    ],
)
def test_fitician_weekday_uses_saturday_as_zero(value: date, expected: int) -> None:
    assert fitician_weekday(value) == expected


def test_local_date_uses_the_requested_timezone_at_utc_boundary() -> None:
    tehran_midnight = datetime.combine(
        date(2026, 9, 14), time.min, tzinfo=ZoneInfo("Asia/Tehran")
    ).astimezone(UTC)
    before_midnight = tehran_midnight.replace(microsecond=0) - datetime.resolution
    after_midnight = tehran_midnight

    assert local_date_for_timezone("UTC", now=before_midnight) == date(2026, 9, 13)
    assert local_date_for_timezone("Asia/Tehran", now=before_midnight) == date(2026, 9, 13)
    assert local_date_for_timezone("Asia/Tehran", now=after_midnight) == date(2026, 9, 14)


def test_tehran_local_midnight_converts_to_utc() -> None:
    expected = datetime.combine(
        date(2026, 9, 14), time.min, tzinfo=ZoneInfo("Asia/Tehran")
    ).astimezone(UTC)
    assert local_midnight_utc(date(2026, 9, 14), "Asia/Tehran") == expected


def test_member_timezone_falls_back_only_when_values_are_missing_or_invalid() -> None:
    assert DEFAULT_MEMBER_TIMEZONE == "Asia/Tehran"
    assert member_timezone_or_default() == DEFAULT_MEMBER_TIMEZONE
    assert member_timezone_or_default("Not/AZone") == DEFAULT_MEMBER_TIMEZONE
    assert member_timezone_or_default("Not/AZone", "America/Los_Angeles") == "America/Los_Angeles"
    assert member_timezone_or_default("America/Los_Angeles", "Asia/Tehran") == "America/Los_Angeles"


@pytest.mark.parametrize("timezone_name", ["", "Not/AZone", "Asia/DefinitelyMissing"])
def test_invalid_timezone_fails_validation(timezone_name: str) -> None:
    with pytest.raises(ValueError):
        validate_timezone_name(timezone_name)


@pytest.mark.parametrize("timezone_name", ["Asia/Tehran", "Europe/Amsterdam", "UTC"])
def test_valid_timezone_is_preserved(timezone_name: str) -> None:
    assert validate_timezone_name(timezone_name) == timezone_name
