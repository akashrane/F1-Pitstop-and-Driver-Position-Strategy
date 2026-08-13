import json
import csv
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
    schema_root = Path(__file__).parents[1] / "schemas"
    for table in TABLES:
        schema = json.loads((schema_root / f"{table}.schema.json").read_text(encoding="utf-8"))
        headers = list(schema["properties"])
        (source / f"{table}.csv").write_text(",".join(headers) + "\n", encoding="utf-8")
    (processed / "manifest_2023_2026.json").write_text("{}\n", encoding="utf-8")

    destination = tmp_path / "release"
    prepare_release(tmp_path / "data", 2023, 2026, destination, "owner/slug", schema_root)

    assert (destination / "validation_manifest.json").exists()
    metadata = json.loads((destination / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "owner/slug"
    assert metadata["title"] == "Formula 1 Pit Stop Dataset"
    assert metadata["keywords"] == ["Tabular", "Sports", "Auto Racing", "Time Series Analysis"]
    assert [resource["path"] for resource in metadata["resources"]] == [
        "pit_events.csv", "race_drivers.csv", "stints.csv", "weather_observations.csv"
    ]
    race_fields = next(item for item in metadata["resources"] if item["path"] == "race_drivers.csv")["schema"]["fields"]
    assert race_fields[0] == {
        "name": "season",
        "type": "integer",
        "description": "Formula 1 World Championship season year.",
    }
    assert (destination / "README.md").exists()
    with (destination / "data_dictionary.csv").open(encoding="utf-8", newline="") as handle:
        dictionary = list(csv.DictReader(handle))
    classified = next(row for row in dictionary if row["table"] == "race_drivers" and row["column"] == "classified_position")
    assert classified["feature_time"] == "post_race"
    assert classified["target"] == "True"
