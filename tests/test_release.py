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
        values = {column: "" for column in headers}
        sample_values = {
            "season": "2026", "round_number": "1", "source": "openf1",
            "weather_source": "openf1", "source_url": "https://example.test/source",
            "retrieved_at_utc": "2026-01-01T00:00:00+00:00", "validation_status": "verified",
        }
        values.update({column: value for column, value in sample_values.items() if column in values})
        with (source / f"{table}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            writer.writerow(values)
    (processed / "manifest_2023_2026.json").write_text("{}\n", encoding="utf-8")
    existing_metadata = tmp_path / "current-metadata.json"
    existing_metadata.write_text(json.dumps({
        "title": "Existing Dataset Title",
        "license": {
            "name": "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)",
            "url": "https://creativecommons.org/licenses/by-nc/4.0/",
        },
    }), encoding="utf-8")

    destination = tmp_path / "release"
    prepare_release(
        tmp_path / "data", 2023, 2026, destination,
        "owner/slug", schema_root, existing_metadata,
    )

    assert (destination / "validation_manifest.json").exists()
    metadata = json.loads((destination / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert metadata["id"] == "owner/slug"
    assert metadata["title"] == "Existing Dataset Title"
    assert "licenses" not in metadata
    assert metadata["expectedUpdateFrequency"] == "weekly"
    assert "keywords" not in metadata
    assert [resource["path"] for resource in metadata["resources"]] == [
        "pit_events.csv", "race_drivers.csv", "stints.csv", "weather_observations.csv", "provenance.csv"
    ]
    race_fields = next(item for item in metadata["resources"] if item["path"] == "race_drivers.csv")["schema"]["fields"]
    assert race_fields[0] == {
        "name": "season",
        "type": "integer",
        "description": "Formula 1 World Championship season year.",
    }
    assert not {"source", "source_url", "retrieved_at_utc", "validation_status"} & {
        field["name"] for field in race_fields
    }
    with (destination / "race_drivers.csv").open(encoding="utf-8", newline="") as handle:
        assert not {"source", "source_url", "retrieved_at_utc", "validation_status"} & set(next(csv.reader(handle)))
    with (destination / "weather_observations.csv").open(encoding="utf-8", newline="") as handle:
        weather_headers = set(next(csv.reader(handle)))
    assert "weather_source" in weather_headers
    assert not {"source_url", "retrieved_at_utc", "validation_status"} & weather_headers
    with (destination / "provenance.csv").open(encoding="utf-8", newline="") as handle:
        provenance = list(csv.DictReader(handle))
    assert len(provenance) == 4
    assert {row["table"] for row in provenance} == set(TABLES)
    assert (destination / "README.md").exists()
    with (destination / "data_dictionary.csv").open(encoding="utf-8", newline="") as handle:
        dictionary = list(csv.DictReader(handle))
    classified = next(row for row in dictionary if row["table"] == "race_drivers" and row["column"] == "classified_position")
    assert classified["feature_time"] == "post_race"
    assert classified["target"] == "True"
