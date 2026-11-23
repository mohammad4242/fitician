import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import text


@pytest.mark.parametrize("fingerprints", [{"users"}, set()])
def test_backup_inventory_handles_the_complete_schema_without_json_argument_overflow(
    db, fingerprints
):
    root = Path(__file__).parents[2]
    spec = importlib.util.spec_from_file_location(
        "backup_snapshot", root / "ops/final-database-snapshot.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generator = module._metadata_query(fingerprints).replace("\\gexec", "")
    query = db.execute(text(generator)).scalar_one()
    metadata = json.loads(db.execute(text(query)).scalar_one())
    assert len(metadata["tables"]) > 50
    assert set(metadata["counts"]) == set(metadata["tables"])
    assert metadata["counts"]["users"] == 0
    assert metadata["fingerprints"] == (
        {"users": "d41d8cd98f00b204e9800998ecf8427e"} if fingerprints else {}
    )
    assert metadata["unvalidated_foreign_keys"] == 0
