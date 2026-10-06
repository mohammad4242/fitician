"""Anonymous educational projections. No internal response inheritance."""

from pydantic import BaseModel, ConfigDict, Field

from app.exercises.enums import (
    BodyRegion,
    Difficulty,
    Equipment,
    ExerciseContentType,
    ExerciseLabel,
    MediaPresentation,
    MediaRole,
    MediaType,
    MuscleFocus,
    MuscleGroup,
)
from app.exercises.schemas import ExerciseFilters


class PublicExerciseFilters(ExerciseFilters):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1, le=10000)


class PublicExerciseMedia(BaseModel):
    presentation: MediaPresentation
    role: MediaRole
    sort_order: int
    media_path: str
    media_type: MediaType
    media_attribution: str | None


class PublicExerciseSummary(BaseModel):
    slug: str
    name_en: str
    name_fa: str
    content_type: ExerciseContentType
    body_region: BodyRegion | None
    primary_muscle: MuscleGroup | None
    secondary_muscles: list[MuscleGroup]
    muscle_focus: MuscleFocus | None
    equipment: list[Equipment]
    difficulty: Difficulty
    labels: list[ExerciseLabel]
    media_path: str
    media_type: MediaType


class PublicExerciseDetail(PublicExerciseSummary):
    instructions_fa: list[str]
    instructions_en: list[str]
    safety_notes_fa: list[str]
    safety_notes_en: list[str]
    media_attribution: str | None
    media_assets: list[PublicExerciseMedia]


class PublicExercisePage(BaseModel):
    items: list[PublicExerciseSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
