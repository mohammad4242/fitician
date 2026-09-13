from datetime import UTC, date, datetime

import pytest

from app.time_context import (
    fitician_weekday,
    local_date_for_timezone,
    local_midnight_utc,
    validate_timezone_name,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 9, 12), 0),  # Saturday
        (date(2026, 9, 13), 1),  # Sunday
        (date(2026, 9, 14), 2),  # Monday
    ],
)
def test_fitician_weekday_uses_saturday_as_zero(value: date, expected: int) -> None:
    assert fitician_weekday(value) == expected


def test_local_date_uses_the_requested_timezone_at_utc_boundary() -> None:
    now = datetime(2026, 9, 13, 20, 45, tzinfo=UTC)

    assert local_date_for_timezone("UTC", now=now) == date(2026, 9, 13)
    assert local_date_for_timezone("Asia/Tehran", now=now) == date(2026, 9, 14)


def test_tehran_local_midnight_converts_to_utc() -> None:
    assert local_midnight_utc(date(2026, 9, 14), "Asia/Tehran") == datetime(
        2026, 9, 13, 20, 30, tzinfo=UTC
    )


@pytest.mark.parametrize("timezone_name", ["", "Not/AZone", "Asia/DefinitelyMissing"])
def test_invalid_timezone_fails_validation(timezone_name: str) -> None:
    with pytest.raises(ValueError):
        validate_timezone_name(timezone_name)


@pytest.mark.parametrize("timezone_name", ["Asia/Tehran", "Europe/Amsterdam", "UTC"])
def test_valid_timezone_is_preserved(timezone_name: str) -> None:
    assert validate_timezone_name(timezone_name) == timezone_name
