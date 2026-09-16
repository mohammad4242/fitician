from pathlib import Path

from scripts.reconcile_media import classify_private_files


def test_private_reconciliation_preserves_unknown_and_reports_missing(tmp_path: Path) -> None:
    root = tmp_path / "body-photos"
    (root / "aa").mkdir(parents=True)
    (root / "aa" / "current.jpg").write_bytes(b"current")
    (root / "aa" / "unknown.jpg").write_bytes(b"unknown")

    records, summary = classify_private_files(
        category="body-photos",
        root=root,
        current_keys={"aa/current.jpg": "body_photos", "aa/missing.jpg": "body_photos"},
        historical_keys={},
    )

    assert {record["category"] for record in records} == {
        "REFERENCED_CURRENT",
        "MISSING_ON_DISK",
        "UNKNOWN",
    }
    assert summary["db_total_keys"] == 2
    assert summary["disk_files"] == 2
    assert summary["matching_current"] == 1
    assert summary["missing_current"] == 1
    assert summary["unreferenced_disk"] == 1


def test_private_reconciliation_recognizes_exact_test_pdf(tmp_path: Path) -> None:
    root = tmp_path / "nutrition-labs"
    (root / "bb").mkdir(parents=True)
    (root / "bb" / "fixture.pdf").write_bytes(b"%PDF-1.4\n%%EOF")

    records, summary = classify_private_files(
        category="nutrition-labs", root=root, current_keys={}, historical_keys={}
    )

    assert records[0]["category"] == "TEST_FIXTURE"
    assert summary["classifications"]["TEST_FIXTURE"] == 1
