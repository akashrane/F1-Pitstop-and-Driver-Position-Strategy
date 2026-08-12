import json
from pathlib import Path

from f1_strategy_data.batch import TABLES
from scripts.prepare_kaggle_release import prepare_release
from scripts.validate_release import validate_manifest


def test_release_gate_rejects_failed_build(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({
        "summary": {"verified": 1, "failed": 1},
        "consolidated_rows": {table: 1 for table in TABLES},
    }), encoding="utf-8")
    assert validate_manifest(path) == ["1 race build(s) failed"]


def test_prepare_release_copies_tables_manifest_and_metadata(tmp_path: Path):
    processed = tmp_path / "data" / "processed"
    source = processed / "consolidated_2023_2026"
    source.mkdir(parents=True)
    for table in TABLES:
        (source / f"{table}.csv").write_text("id\n1\n", encoding="utf-8")
    (processed / "manifest_2023_2026.json").write_text("{}\n", encoding="utf-8")

    destination = tmp_path / "release"
    prepare_release(tmp_path / "data", 2023, 2026, destination, "owner/slug", "Title")

    assert (destination / "validation_manifest.json").exists()
    metadata = json.loads((destination / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "owner/slug"
