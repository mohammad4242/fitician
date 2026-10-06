"""Build-only public projection of canonical seeds. Never reads a DB or environment secrets."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.exercises.catalog_categories import (  # noqa: E402
    BODY_REGION_CATEGORIES,
    CORE_CATEGORIES,
    LOWER_BODY_CATEGORIES,
    UPPER_BODY_CATEGORIES,
)
from app.exercises.seed_data import EXERCISE_SEEDS  # noqa: E402
from app.exercises.taxonomy import MUSCLE_FOCUS_CATEGORIES  # noqa: E402

FIELDS = (
    "slug",
    "name_fa",
    "name_en",
    "primary_muscle",
    "secondary_muscles",
    "muscle_focus",
    "equipment",
    "difficulty",
    "instructions_fa",
    "safety_notes_fa",
    "body_region",
    "instructions_en",
    "safety_notes_en",
    "media_path",
    "media_type",
    "media_attribution",
)
records = [
    {
        **{field: getattr(seed, field) for field in FIELDS},
        "content_type": "exercise",
        "labels": [],
        "media_assets": [],
    }
    for seed in EXERCISE_SEEDS
]
# Optional DB projections are refreshed explicitly through the safe exporter and code review.
snapshot = ROOT / "frontend/src/seo/exercise-publications.json"
if snapshot.exists():
    additions = json.loads(snapshot.read_text())
    if additions is not None:
        expected = set(records[0])
        for record in additions:
            if set(record) != expected:
                raise SystemExit("Invalid public publication projection")
        records = additions
manifest = json.loads(
    (ROOT / "backend/app/exercises/publication_slugs.json").read_text()
)
if set(manifest) != {record["slug"] for record in records}:
    raise SystemExit("Public API discovery and prerender publication manifest disagree")
target = ROOT / "frontend/src/seo/exercise-data.json"
content = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
if "--check" in sys.argv:
    if not target.exists() or target.read_text() != content:
        raise SystemExit(
            "Public exercise projection is stale; run npm run export:exercises"
        )
else:
    target.write_text(content)


def categories(values):
    return [{"value": value, "name_en": en, "name_fa": fa} for value, en, fa in values]


category_data = {
    "body_regions": categories(BODY_REGION_CATEGORIES),
    "upper_body": categories(UPPER_BODY_CATEGORIES),
    "lower_body": categories(LOWER_BODY_CATEGORIES),
    "core": categories(CORE_CATEGORIES),
    "muscle_focuses": {
        muscle: [
            {"value": c.value, "name_en": c.name_en, "name_fa": c.name_fa}
            for c in values
        ]
        for muscle, values in MUSCLE_FOCUS_CATEGORIES.items()
    },
}
category_target = ROOT / "frontend/src/seo/exercise-categories.json"
category_content = json.dumps(category_data, ensure_ascii=False, indent=2) + "\n"
if "--check" in sys.argv:
    if not category_target.exists() or category_target.read_text() != category_content:
        raise SystemExit("Public category projection is stale")
else:
    category_target.write_text(category_content)
print(f"Public exercise projection: {len(records)} approved instructional records")
