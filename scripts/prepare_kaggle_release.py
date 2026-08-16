"""Create a self-contained directory accepted by the Kaggle CLI."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from f1_strategy_data.release_metadata import (
    COLUMN_DESCRIPTIONS,
    DATASET_DESCRIPTION,
    DATASET_SUBTITLE,
    DATASET_TITLE,
    PROVENANCE_COLUMNS,
    PUBLIC_EXCLUDED_COLUMNS,
    TABLE_DESCRIPTIONS,
)


def prepare_release(
    data_root: Path,
    start_year: int,
    end_year: int,
    destination: Path,
    slug: str,
    schema_root: Path = Path("schemas"),
    existing_metadata: Path | None = None,
) -> None:
    source = data_root / "processed" / f"consolidated_{start_year}_{end_year}"
    manifest = data_root / "processed" / f"manifest_{start_year}_{end_year}.json"
    if not source.is_dir() or not manifest.is_file():
        raise FileNotFoundError("Run scripts/build_seasons.py before preparing a release")
    destination.mkdir(parents=True, exist_ok=True)
    resources = []
    dictionary_rows = []
    provenance_rows: list[dict[str, str]] = []
    coverage_rows: list[dict[str, object]] = []
    for path in sorted(source.glob("*.csv")):
        table = path.stem
        schema = _read_schema(schema_root / f"{table}.schema.json")
        rows, headers = _read_canonical_csv(path, schema)
        public_headers = [column for column in headers if column not in PUBLIC_EXCLUDED_COLUMNS]
        fields = _document_fields(public_headers, table, schema)
        _write_projected_csv(destination / path.name, rows, public_headers)
        provenance_rows.extend(_extract_provenance(table, rows))
        resources.append({
            "path": path.name,
            "description": TABLE_DESCRIPTIONS[table],
            "schema": {"fields": fields},
        })
        dictionary_rows.extend(_dictionary_rows(table, path.name, fields, schema))
        seasons = [int(row["season"]) for row in rows]
        coverage_rows.append({
            "table": table,
            "earliest_season": min(seasons),
            "latest_season": max(seasons),
            "row_count": len(rows),
            "availability_note": _coverage_note(table),
        })
    coverage_fields = [
        {"name": "table", "type": "string", "description": COLUMN_DESCRIPTIONS["table"]},
        {"name": "earliest_season", "type": "integer", "description": COLUMN_DESCRIPTIONS["earliest_season"]},
        {"name": "latest_season", "type": "integer", "description": COLUMN_DESCRIPTIONS["latest_season"]},
        {"name": "row_count", "type": "integer", "description": COLUMN_DESCRIPTIONS["row_count"]},
        {"name": "availability_note", "type": "string", "description": COLUMN_DESCRIPTIONS["availability_note"]},
    ]
    _write_rows(destination / "coverage.csv", coverage_rows, [field["name"] for field in coverage_fields])
    resources.append({
        "path": "coverage.csv", "description": TABLE_DESCRIPTIONS["coverage"],
        "schema": {"fields": coverage_fields},
    })
    dictionary_rows.extend({
        "table": "coverage", "file": "coverage.csv", "column": field["name"],
        "type": field["type"], "nullable": False,
        "description": field["description"], "feature_time": "", "role": "",
        "target": False, "unit": "", "allowed_values": "",
    } for field in coverage_fields)
    provenance_rows = _deduplicate_rows(provenance_rows, PROVENANCE_COLUMNS)
    _write_rows(destination / "provenance.csv", provenance_rows, PROVENANCE_COLUMNS)
    provenance_fields = _provenance_fields()
    resources.append({
        "path": "provenance.csv",
        "description": TABLE_DESCRIPTIONS["provenance"],
        "schema": {"fields": provenance_fields},
    })
    dictionary_rows.extend(_provenance_dictionary_rows(provenance_fields))
    shutil.copy2(manifest, destination / "validation_manifest.json")
    _write_dictionary(destination / "data_dictionary.csv", dictionary_rows)
    _write_readme(destination / "README.md", start_year, end_year, resources)
    current = _read_existing_metadata(existing_metadata)
    metadata = {
        "id": slug,
        "title": current.get("title", DATASET_TITLE),
        "subtitle": DATASET_SUBTITLE,
        "description": DATASET_DESCRIPTION,
        "expectedUpdateFrequency": "weekly",
        "resources": resources,
    }
    (destination / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def _coverage_note(table: str) -> str:
    return {
        "race_context": "Race and circuit metadata from 1950; detailed start weather and safety-car fields from 2023.",
        "race_drivers": "Official classified race entries from 1950.",
        "pit_events": "Recorded pit-stop events from 2011; absence before 2011 means unavailable, not zero stops.",
        "stints": "Detailed tyre-stint timing from OpenF1 coverage beginning in 2023.",
        "weather_observations": "Minute-level trackside OpenF1 weather beginning in 2023.",
    }[table]


def _read_existing_metadata(path: Path | None) -> dict:
    if path is None or not path.is_file():
        raise FileNotFoundError("Download the existing Kaggle metadata before preparing a release")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_schema(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical schema: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_canonical_csv(csv_path: Path, schema: dict) -> tuple[list[dict[str, str]], list[str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        rows = list(reader)
    properties = schema["properties"]
    if headers != list(properties):
        raise ValueError(f"{csv_path.name} columns do not match schema order")
    return rows, headers


def _document_fields(headers: list[str], table: str, schema: dict) -> list[dict[str, str]]:
    properties = schema["properties"]
    fields = []
    for column in headers:
        if column not in COLUMN_DESCRIPTIONS:
            raise KeyError(f"Missing description for {table}.{column}")
        spec = properties[column]
        fields.append({
            "name": column,
            "type": _kaggle_type(spec),
            "description": COLUMN_DESCRIPTIONS[column],
        })
    return fields


def _write_projected_csv(path: Path, rows: list[dict[str, str]], headers: list[str]) -> None:
    projected = [{column: row[column] for column in headers} for row in rows]
    _write_rows(path, projected, headers)


def _write_rows(path: Path, rows: list[dict[str, object]], headers: list[str] | tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


def _extract_provenance(table: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    extracted = []
    for row in rows:
        extracted.append({
            "season": row["season"],
            "round_number": row["round_number"],
            "table": table,
            "source": row.get("source") or row.get("weather_source", ""),
            "source_url": row.get("source_url", ""),
            "retrieved_at_utc": row.get("retrieved_at_utc", ""),
            "validation_status": row.get("validation_status", ""),
        })
    return extracted


def _deduplicate_rows(rows: list[dict[str, str]], headers: tuple[str, ...]) -> list[dict[str, str]]:
    unique = {tuple(row[column] for column in headers): row for row in rows}
    return [unique[key] for key in sorted(unique)]


def _provenance_fields() -> list[dict[str, str]]:
    types = {"season": "integer", "round_number": "integer", "retrieved_at_utc": "datetime"}
    return [{
        "name": column,
        "type": types.get(column, "string"),
        "description": COLUMN_DESCRIPTIONS[column],
    } for column in PROVENANCE_COLUMNS]


def _provenance_dictionary_rows(fields: list[dict[str, str]]) -> list[dict[str, object]]:
    return [{
        "table": "provenance",
        "file": "provenance.csv",
        "column": field["name"],
        "type": field["type"],
        "nullable": False,
        "description": field["description"],
        "feature_time": "",
        "role": "identifier" if field["name"] in {"season", "round_number", "table"} else "",
        "target": False,
        "unit": "",
        "allowed_values": "",
    } for field in fields]


def _kaggle_type(spec: dict) -> str:
    if spec.get("format") == "date-time":
        return "datetime"
    value = spec.get("type", "string")
    types = value if isinstance(value, list) else [value]
    return next((item for item in types if item != "null"), "string")


def _dictionary_rows(table: str, filename: str, fields: list[dict], schema: dict) -> list[dict[str, object]]:
    required = set(schema.get("required", []))
    rows = []
    for field in fields:
        spec = schema["properties"][field["name"]]
        rows.append({
            "table": table,
            "file": filename,
            "column": field["name"],
            "type": field["type"],
            "nullable": field["name"] not in required or "null" in (spec.get("type") or []),
            "description": field["description"],
            "feature_time": spec.get("x-feature-time", ""),
            "role": spec.get("x-role", ""),
            "target": bool(spec.get("x-target", False)),
            "unit": spec.get("x-unit", ""),
            "allowed_values": " | ".join(str(value) for value in spec.get("enum", [])),
        })
    return rows


def _write_dictionary(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("Refusing to write an empty data dictionary")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(path: Path, start_year: int, end_year: int, resources: list[dict]) -> None:
    files = "\n".join(f"- `{item['path']}`: {item['description']}" for item in resources)
    text = f"""# F1 Pit Stop and Race Strategy Data

Validated canonical data for completed Formula 1 races from {start_year} through {end_year}.

## Files

{files}
- `data_dictionary.csv`: Types, descriptions, feature timing, units, targets, and nullability.
- `validation_manifest.json`: Per-race build status, row counts, and validation issues.

## Quality policy

Canonical tables are admitted independently: a telemetry defect cannot delete an independently valid official race result. A table with an error-level issue remains excluded for that race, and every issue stays visible in the validation manifest. Repeated source URLs, retrieval timestamps, and validation fields are removed from the analysis-ready tables and preserved compactly in `provenance.csv`.

## Modelling boundary

Use `feature_time` in the data dictionary to separate `pre_race`, `live`, and `post_race` fields. Post-race fields must not be used as predictors for pre-race or live models.
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--destination", type=Path, default=Path("release/kaggle"))
    parser.add_argument("--slug", required=True, help="Kaggle owner/dataset-slug")
    parser.add_argument("--schema-root", type=Path, default=Path("schemas"))
    parser.add_argument("--existing-metadata", type=Path, required=True)
    args = parser.parse_args()
    prepare_release(
        args.data_root, args.start_year, args.end_year, args.destination,
        args.slug, args.schema_root, args.existing_metadata,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
