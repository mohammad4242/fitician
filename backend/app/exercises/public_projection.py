"""Rights-checked stable public media and an explicit instructional field allowlist."""

import re

from app.exercises.enums import MediaType
from app.exercises.media_metadata import OWNER_LICENSE
from app.exercises.media_resolver import ordered_media_assets
from app.exercises.models import Exercise
from app.exercises.public_schemas import (
    PublicExerciseDetail,
    PublicExerciseMedia,
    PublicExerciseSummary,
)

PLACEHOLDER = "/exercises/exercise-placeholder.svg"
GENERAL_SAFETY_FA = [
    "نکات ایمنی اختصاصی ثبت نشده است؛ برای بررسی فرم این حرکت از مربی واجد صلاحیت کمک بگیر.",
    "در صورت درد یا ناراحتی غیرعادی، حرکت را متوقف کن؛ "
    "این راهنمای عمومی جای ارزیابی فردی را نمی‌گیرد.",
]
GENERAL_SAFETY_EN = [
    "Exercise-specific safety notes have not been recorded; "
    "ask a qualified trainer to check your form.",
    "Stop if you experience pain or unusual discomfort; "
    "this general guidance does not replace an individual assessment.",
]
PUBLIC_MEDIA = re.compile(
    r"^/media/exercises/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_.-]+\.(?:gif|mp4|webm|webp|png|jpg|jpeg)$"
)


def approved_media(path: str, license: str | None) -> bool:
    return (
        bool(PUBLIC_MEDIA.fullmatch(path))
        and ".." not in path
        and license
        in {
            OWNER_LICENSE,
            "Fitician original",
        }
    )


def public_detail(exercise: Exercise) -> PublicExerciseDetail:
    assets = [
        PublicExerciseMedia(
            presentation=asset.presentation,
            role=asset.role,
            sort_order=asset.sort_order,
            media_path=asset.media_path,
            media_type=asset.media_type,
            media_attribution=asset.media_attribution,
        )
        for asset in ordered_media_assets(exercise.media_assets, primary_path=exercise.media_path)
        if approved_media(asset.media_path, asset.media_license)
        and asset.media_type != MediaType.PLACEHOLDER
    ]
    path, kind = PLACEHOLDER, MediaType.PLACEHOLDER
    attribution = None
    if assets:
        path, kind, attribution = (
            assets[0].media_path,
            assets[0].media_type,
            assets[0].media_attribution,
        )
    elif approved_media(exercise.media_path, exercise.media_license):
        path, kind, attribution = (
            exercise.media_path,
            exercise.media_type,
            exercise.media_attribution,
        )
    return PublicExerciseDetail(
        slug=exercise.slug,
        name_en=exercise.name_en,
        name_fa=exercise.name_fa,
        content_type=exercise.content_type,
        body_region=exercise.body_region,
        primary_muscle=exercise.primary_muscle,
        muscle_focus=exercise.muscle_focus,
        secondary_muscles=sorted([item.muscle for item in exercise.secondary_muscles]),
        equipment=sorted([item.equipment for item in exercise.equipment_items]),
        difficulty=exercise.difficulty,
        labels=sorted([item.label for item in exercise.labels]),
        instructions_en=exercise.instructions_en,
        instructions_fa=exercise.instructions_fa,
        safety_notes_en=exercise.safety_notes_en or GENERAL_SAFETY_EN,
        safety_notes_fa=exercise.safety_notes_fa or GENERAL_SAFETY_FA,
        media_path=path,
        media_type=kind,
        media_attribution=attribution,
        media_assets=assets,
    )


def public_summary(exercise: Exercise) -> PublicExerciseSummary:
    return PublicExerciseSummary.model_validate(public_detail(exercise).model_dump())
