from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

from app.config import Settings
from app.media.public import PublicMediaReader
from app.media.storage import ObjectStorage
from app.nutrition.pdf import (
    _resolve_image_data_uri,
    build_nutrition_plan_html,
    render_nutrition_plan_pdf,
)
from app.nutrition.schemas import (
    WeeklyPlanDayResponse,
    WeeklyPlanFoodResponse,
    WeeklyPlanMealResponse,
    WeeklyPlanResponse,
)


def _mock_plan() -> WeeklyPlanResponse:
    now = datetime(2026, 9, 7, 10, 0, 0, tzinfo=UTC)
    day1_meals = [
        WeeklyPlanMealResponse(
            id=UUID("018f0000-0000-7000-8000-000000000001"),
            catalogue_meal_id=None,
            catalogue_meal_category=None,
            name_fa="املت قارچ و اسفناج",
            name_en="Mushroom Spinach Omelet",
            meal_code="BRK-01",
            image_url=None,
            slot_role="breakfast",
            slot_index=0,
            target_distribution={"energy_kcal": 0.25},
            nutrient_totals={
                "energy_kcal": 420.0,
                "protein_g": 28.0,
                "carbohydrate_g": 18.0,
                "fat_g": 26.0,
            },
            cost_irr=450000,
            is_locked=False,
            foods=[
                WeeklyPlanFoodResponse(
                    food_id=UUID("018f0000-0000-7000-8000-000000000010"),
                    slug="egg",
                    name_fa="تخم‌مرغ",
                    name_en="Egg",
                    grams=120.0,
                    cost_irr=200000,
                    nutrients={"energy_kcal": 180.0, "protein_g": 15.0},
                ),
                WeeklyPlanFoodResponse(
                    food_id=UUID("018f0000-0000-7000-8000-000000000011"),
                    slug="spinach",
                    name_fa="اسفناج",
                    name_en="Spinach",
                    grams=80.0,
                    cost_irr=100000,
                    nutrients={"energy_kcal": 20.0, "protein_g": 2.0},
                ),
            ],
        ),
        WeeklyPlanMealResponse(
            id=UUID("018f0000-0000-7000-8000-000000000002"),
            catalogue_meal_id=None,
            catalogue_meal_category=None,
            name_fa="چلو جوجه کباب",
            name_en="Chicken Kebab with Rice",
            meal_code="LNC-01",
            image_url=None,
            slot_role="lunch",
            slot_index=1,
            target_distribution={"energy_kcal": 0.40},
            nutrient_totals={
                "energy_kcal": 650.0,
                "protein_g": 52.0,
                "carbohydrate_g": 75.0,
                "fat_g": 16.0,
            },
            cost_irr=1200000,
            is_locked=False,
            foods=[
                WeeklyPlanFoodResponse(
                    food_id=UUID("018f0000-0000-7000-8000-000000000012"),
                    slug="chicken-breast",
                    name_fa="سینه مرغ",
                    name_en="Chicken Breast",
                    grams=200.0,
                    cost_irr=800000,
                    nutrients={"energy_kcal": 330.0, "protein_g": 62.0},
                ),
                WeeklyPlanFoodResponse(
                    food_id=UUID("018f0000-0000-7000-8000-000000000013"),
                    slug="white-rice",
                    name_fa="برنج کته",
                    name_en="Cooked White Rice",
                    grams=250.0,
                    cost_irr=400000,
                    nutrients={"energy_kcal": 320.0, "carbohydrate_g": 70.0},
                ),
            ],
        ),
    ]

    days = [
        WeeklyPlanDayResponse(
            day_index=0,
            plan_date=date(2026, 9, 7),
            nutrient_totals={
                "energy_kcal": 2100.0,
                "protein_g": 140.0,
                "carbohydrate_g": 220.0,
                "fat_g": 65.0,
            },
            cost_irr=2500000,
            meals=day1_meals,
        )
    ]

    return WeeklyPlanResponse(
        id=UUID("018f0000-0000-7000-8000-000000000099"),
        revision=1,
        lifecycle_status="active",
        is_user_visible=True,
        physician_approved=True,
        review_status="approved",
        physician_approved_at=now,
        physician_display_name="دکتر احمدی",
        physician_user_visible_notes=None,
        physician_change_summary=[],
        supersedes_plan_id=None,
        start_date=date(2026, 9, 7),
        planner_policy_version="v1",
        planner_version="v1",
        scientific_policy_version="v1",
        formula_version="v1",
        weekly_cost_irr=17500000,
        weekly_budget_irr=20000000,
        budget_status="within_budget",
        warning_codes=[],
        explanation_codes=[],
        input_snapshot={},
        price_snapshot={},
        food_data_manifest={},
        repair_actions=[],
        nutrients={},
        days=days,
        created_at=now,
    )


def test_build_nutrition_plan_html_renders_rtl_and_fonts() -> None:
    plan = _mock_plan()
    html = build_nutrition_plan_html(plan)

    assert 'dir="rtl"' in html
    assert 'lang="fa"' in html
    assert 'font-family: "Vazirmatn", "DejaVu Sans", sans-serif' in html
    assert "فیتیشن | FITICIAN" in html
    assert "برنامه رژیم و تغذیه اختصاصی" in html


def test_build_nutrition_plan_html_includes_days_and_meals() -> None:
    plan = _mock_plan()
    html = build_nutrition_plan_html(plan)

    # Day header
    assert "روز ۱ (شنبه)" in html
    assert "۲۱۰۰ kcal" in html
    assert "۱۴۰" in html

    # Meals
    assert "املت قارچ و اسفناج" in html
    assert "صبحانه" in html
    assert "چلو جوجه کباب" in html
    assert "ناهار" in html

    # Foods & portions
    assert "تخم‌مرغ (۱۲۰ گرم)" in html
    assert "اسفناج (۸۰ گرم)" in html
    assert "سینه مرغ (۲۰۰ گرم)" in html
    assert "برنج کته (۲۵۰ گرم)" in html

    # Meal macros
    assert "۴۲۰ کیلوکالری" in html
    assert "پروتئین ۲۸" in html
    assert "کربوهیدرات ۱۸" in html
    assert "چربی ۲۶" in html


def test_resolve_image_data_uri_handles_none_and_public_media(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _resolve_image_data_uri(None) is None
    assert _resolve_image_data_uri("") is None

    settings = Settings(app_env="test", media_root=tmp_path / "media")
    monkeypatch.setattr("app.nutrition.pdf.get_settings", lambda: settings)
    fake_img = settings.media_root / "meal-catalogue" / "test.png"
    fake_img.parent.mkdir(parents=True)
    fake_img.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    data_uri = _resolve_image_data_uri("/media/meal-catalogue/test.png")
    assert data_uri is not None
    assert data_uri.startswith("data:image/png;base64,")
    assert _resolve_image_data_uri(str(fake_img)) is None
    assert _resolve_image_data_uri("/media/../private/photo.jpg") is None


def test_render_nutrition_plan_pdf_generates_pdf_bytes() -> None:
    plan = _mock_plan()
    pdf_bytes = render_nutrition_plan_pdf(plan)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")


def test_pdf_html_reuses_one_remote_catalogue_image(tmp_path: Path) -> None:
    plan = _mock_plan()
    path = "/media/meal-catalogue/shared.png"
    for meal in plan.days[0].meals:
        meal.image_url = path
    settings = Settings(
        app_env="test",
        media_root=tmp_path / "media",
        media_storage_backend="s3",
        s3_endpoint="https://s3.example.test",
        s3_bucket="fitician-media",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        s3_region="ir-thr-at1",
        media_public_base_url="https://media.example.test",
    )
    storage = Mock(spec=ObjectStorage)
    storage.read.return_value = b"\x89PNG\r\n\x1a\nimage"

    html = build_nutrition_plan_html(plan, PublicMediaReader(settings, storage))

    assert html.count('src="data:image/png;base64,') == 2
    storage.read.assert_called_once_with("public/meal-catalogue/shared.png")
