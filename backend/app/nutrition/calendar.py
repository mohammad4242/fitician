from datetime import date


def nutrition_pattern_day_index(start_date: date, target_date: date) -> int:
    """Return the recurring weekly-template index for a calendar date."""
    return (target_date - start_date).days % 7


def nutrition_absolute_day_number(start_date: date, target_date: date) -> int:
    """Return the one-based absolute day number for a calendar date."""
    return (target_date - start_date).days + 1
