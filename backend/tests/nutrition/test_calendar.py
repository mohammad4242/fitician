from datetime import date, timedelta

from app.nutrition.calendar import (
    nutrition_absolute_day_number,
    nutrition_pattern_day_index,
)


def test_recurring_nutrition_template_repeats_every_seven_days() -> None:
    start = date(2026, 9, 13)

    assert nutrition_absolute_day_number(start, start) == 1
    assert nutrition_pattern_day_index(start, start) == 0
    assert nutrition_absolute_day_number(start, start + timedelta(days=6)) == 7
    assert nutrition_pattern_day_index(start, start + timedelta(days=6)) == 6
    assert nutrition_absolute_day_number(start, start + timedelta(days=7)) == 8
    assert nutrition_pattern_day_index(start, start + timedelta(days=7)) == 0
    assert nutrition_absolute_day_number(start, start + timedelta(days=14)) == 15
    assert nutrition_pattern_day_index(start, start + timedelta(days=14)) == 0
