from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.session import get_engine
from app.exercises.seed_data import EXERCISE_SEEDS
from app.exercises.seed_media_sync import sync_seed_media, validate_seed_media
from app.exercises.service import SeedResult, seed_exercises
from app.media.factory import build_s3_storage


def format_seed_result(result: SeedResult) -> str:
    alternative_label = "alternative" if result.alternatives == 1 else "alternatives"
    return f"Seeded {result.exercises} exercises and {result.alternatives} {alternative_label}."


def main() -> None:
    settings = get_settings()
    paths = tuple(seed.media_path for seed in EXERCISE_SEEDS if seed.media_path.endswith(".gif"))
    if settings.media_storage_backend == "s3":
        validate_seed_media(paths, build_s3_storage(settings))
    else:
        source_root = Path(__file__).resolve().parents[3] / "frontend/public/exercises"
        sync_seed_media(paths, source_root=source_root, media_root=settings.media_root)
    with Session(get_engine(settings)) as db:
        result = seed_exercises(db)
    print(format_seed_result(result))


if __name__ == "__main__":
    main()
