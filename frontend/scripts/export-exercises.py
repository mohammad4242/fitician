"""Build-only public projection of canonical seeds. Never reads a DB or environment secrets."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.exercises.seed_data import EXERCISE_SEEDS  # noqa: E402

FIELDS = (
    "slug", "name_fa", "name_en", "primary_muscle", "secondary_muscles",
    "muscle_focus", "equipment", "difficulty", "instructions_fa", "safety_notes_fa",
)
records = [{field: getattr(seed, field) for field in FIELDS} for seed in EXERCISE_SEEDS]
target = ROOT / "frontend/src/seo/exercise-data.json"
content = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
if "--check" in sys.argv:
    if not target.exists() or target.read_text() != content:
        raise SystemExit("Public exercise projection is stale; run npm run export:exercises")
else:
    target.write_text(content)
print(f"Public exercise projection: {len(records)} canonical seeds; allowlisted text fields only")
