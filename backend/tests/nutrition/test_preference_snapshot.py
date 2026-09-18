from uuid import UUID

from app.nutrition.preference_snapshot import (
    PreferenceFeedback,
    build_preference_snapshot,
)


def test_feedback_snapshot_keeps_hard_and_soft_preferences_separate() -> None:
    snapshot = build_preference_snapshot(
        liked_food_ids=(UUID(int=1),),
        disliked_food_ids=(UUID(int=2),),
        feedback=(
            PreferenceFeedback(UUID(int=10), "liked"),
            PreferenceFeedback(UUID(int=11), "disliked"),
            PreferenceFeedback(UUID(int=12), "do_not_suggest_again"),
            PreferenceFeedback(UUID(int=13), "prefer_more_often"),
        ),
    )

    assert snapshot.liked_food_ids == ("00000000-0000-0000-0000-000000000001",)
    assert snapshot.disliked_food_ids == ("00000000-0000-0000-0000-000000000002",)
    assert snapshot.liked_meal_ids == (str(UUID(int=10)),)
    assert snapshot.disliked_meal_ids == (str(UUID(int=11)),)
    assert snapshot.excluded_meal_ids == (str(UUID(int=12)),)
    assert snapshot.prefer_more_often_meal_ids == (str(UUID(int=13)),)


def test_preference_snapshot_is_deterministic_and_adherence_neutral_without_data() -> None:
    first = build_preference_snapshot(feedback=())
    second = build_preference_snapshot(feedback=())

    assert first == second
    assert first.data_sufficient is False
    assert first.historical_meal_adherence == ()


def test_snapshot_combines_profile_meal_preferences_and_feedback_without_losing_categories(
) -> None:
    snapshot = build_preference_snapshot(
        liked_meal_ids=(UUID(int=20),),
        disliked_meal_ids=(UUID(int=21),),
        feedback=(
            PreferenceFeedback(UUID(int=20), "prefer_more_often"),
            PreferenceFeedback(UUID(int=22), "do_not_suggest_again"),
        ),
        hard_excluded_food_ids=(UUID(int=30),),
        hard_excluded_meal_ids=(UUID(int=31),),
    )

    assert snapshot.liked_meal_ids == (str(UUID(int=20)),)
    assert snapshot.disliked_meal_ids == (str(UUID(int=21)),)
    assert snapshot.prefer_more_often_meal_ids == (str(UUID(int=20)),)
    assert snapshot.feedback_excluded_meal_ids == (str(UUID(int=22)),)
    assert snapshot.excluded_meal_ids == (str(UUID(int=22)),)
    assert snapshot.hard_excluded_food_ids == (str(UUID(int=30)),)
    assert snapshot.hard_excluded_meal_ids == (str(UUID(int=31)),)
