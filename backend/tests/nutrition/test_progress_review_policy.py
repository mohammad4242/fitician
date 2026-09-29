from datetime import date, timedelta
from decimal import Decimal

from app.nutrition.progress_review import weight_rate


def test_duplicate_same_day_weighings_do_not_create_a_trend():
    start = date(2026, 9, 1)
    assert weight_rate([(start, Decimal(80))] * 10, start, start + timedelta(days=27)) is None


def test_rate_compares_two_halves_and_ignores_invalid_or_out_of_window_weights():
    start = date(2026, 9, 1)
    points = [
        (start + timedelta(days=day), Decimal(80) - Decimal(day) / 14) for day in [0, 7, 20, 27]
    ]
    points += [(start, Decimal("NaN")), (start - timedelta(days=1), Decimal(100))]
    assert weight_rate(points, start, start + timedelta(days=27)) == Decimal("-.500")


def test_stale_or_short_weight_history_cannot_produce_a_rate():
    start = date(2026, 9, 1)
    assert (
        weight_rate(
            [(start + timedelta(days=i), Decimal(80)) for i in range(4)],
            start,
            start + timedelta(days=27),
        )
        is None
    )
    assert (
        weight_rate(
            [(start + timedelta(days=i), Decimal(80)) for i in [0, 5, 10, 15]],
            start,
            start + timedelta(days=27),
        )
        is None
    )
