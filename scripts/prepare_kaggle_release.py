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
    for path in sorted(source.glob("*.csv")):
        table = path.stem
        schema = _read_schema(schema_root / f"{table}.schema.json")
        fields = _document_fields(path, table, schema)
        shutil.copy2(path, destination / path.name)
        resources.append({
            "path": path.name,
            "description": TABLE_DESCRIPTIONS[table],
            "schema": {"fields": fields},
        })
        dictionary_rows.extend(_dictionary_rows(table, path.name, fields, schema))
    shutil.copy2(manifest, destination / "validation_manifest.json")
    _write_dictionary(destination / "data_dictionary.csv", dictionary_rows)
    _write_readme(destination / "README.md", start_year, end_year, resources)
    current = _read_existing_metadata(existing_metadata)
    licenses = current.get("licenses")
    if not isinstance(licenses, list) or len(licenses) != 1:
        raise ValueError("Existing Kaggle metadata must contain exactly one license")
    metadata = {
        "id": slug,
        "title": current.get("title", DATASET_TITLE),
        "subtitle": DATASET_SUBTITLE,
        "description": DATASET_DESCRIPTION,
        "licenses": licenses,
        "expectedUpdateFrequency": "weekly",
        "resources": resources,
    }
    (destination / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def _read_existing_metadata(path: Path | None) -> dict:
    if path is None or not path.is_file():
        raise FileNotFoundError("Download the existing Kaggle metadata before preparing a release")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_schema(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical schema: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _document_fields(csv_path: Path, table: str, schema: dict) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        headers = next(csv.reader(handle))
    properties = schema["properties"]
    if headers != list(properties):
        raise ValueError(f"{csv_path.name} columns do not match schema order")
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

Only verified races enter the published CSV tables. Warning, quarantined, failed, and unavailable races are retained in the validation manifest rather than silently filled or presented as verified. Source URLs and UTC retrieval timestamps are retained in every canonical table.

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
