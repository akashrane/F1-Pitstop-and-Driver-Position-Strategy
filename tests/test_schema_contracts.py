import json
from pathlib import Path


SCHEMA_DIR = Path(__file__).parents[1] / "schemas"
EXPECTED = {
    "race_drivers.schema.json": {"season", "round_number", "driver_id", "source", "source_url", "retrieved_at_utc", "validation_status"},
    "stints.schema.json": {"session_key", "driver_id", "stint_number", "source", "source_url", "retrieved_at_utc", "validation_status"},
    "pit_events.schema.json": {"session_key", "driver_id", "stop_number", "source", "source_url", "retrieved_at_utc", "validation_status"},
    "weather_observations.schema.json": {"session_key", "observed_at_utc", "weather_source", "source_url", "retrieved_at_utc", "validation_status"},
    "pre_race_finishing_position.schema.json": {"season", "round_number", "driver_id", "classified_position", "dataset_split"},
}


def test_all_schema_contracts_are_valid_json_and_closed():
    assert {path.name for path in SCHEMA_DIR.glob("*.schema.json")} == set(EXPECTED)
    for filename, required in EXPECTED.items():
        schema = json.loads((SCHEMA_DIR / filename).read_text(encoding="utf-8"))
        assert schema["$schema"].endswith("2020-12/schema")
        assert schema["additionalProperties"] is False
        assert required <= set(schema["required"])
        assert set(schema["required"]) <= set(schema["properties"])


def test_every_model_field_declares_timing_or_non_feature_role():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        for name, definition in schema["properties"].items():
            assert "x-feature-time" in definition or "x-role" in definition or name in {
                "source", "source_url", "retrieved_at_utc", "validation_status", "weather_source"
            }, f"{path.name}:{name} needs a modeling-time annotation"
