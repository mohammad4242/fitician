"""Refresh reviewed prerender projections from explicitly approved records.

Run from backend with --output ../frontend/src/seo/exercise-publications.json.
The output and publication_slugs.json must be reviewed/released together.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database.session import get_engine
from app.exercises.models import Exercise
from app.exercises.public_projection import public_detail


def export_public_exercises(db: Session, output: Path, manifest: Path) -> None:
    records = list(
        db.scalars(
            select(Exercise)
            .where(
                Exercise.is_active.is_(True),
                Exercise.is_public.is_(True),
                Exercise.needs_review.is_(False),
            )
            .options(
                selectinload(Exercise.secondary_muscles),
                selectinload(Exercise.equipment_items),
                selectinload(Exercise.media_assets),
                selectinload(Exercise.labels),
            )
            .order_by(Exercise.slug)
        )
    )
    if any(
        "Replace this placeholder metadata after review." in record.instructions_en
        or not record.instructions_fa
        or not record.instructions_en
        for record in records
    ):
        raise ValueError("Public exercise export requires completed instructional review")
    data = [public_detail(record).model_dump(mode="json") for record in records]
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    manifest.write_text(json.dumps([record.slug for record in records], indent=2) + "\n")
    print(f"Exported {len(records)} explicitly approved public exercise projections")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with Session(get_engine(get_settings())) as db:
        export_public_exercises(db, args.output, Path(__file__).with_name("publication_slugs.json"))


if __name__ == "__main__":
    main()
