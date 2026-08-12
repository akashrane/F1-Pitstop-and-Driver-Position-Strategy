"""Validate a batch manifest before publishing model-ready files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_TABLES = ("race_drivers", "stints", "pit_events", "weather_observations")


def validate_manifest(path: Path) -> list[str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if manifest.get("summary", {}).get("failed", 0):
        errors.append(f"{manifest['summary']['failed']} race build(s) failed")
    verified = manifest.get("summary", {}).get("verified", 0)
    if verified < 1:
        errors.append("no verified races are available for publication")
    counts = manifest.get("consolidated_rows", {})
    for table in REQUIRED_TABLES:
        if counts.get(table, 0) < 1:
            errors.append(f"consolidated table {table} is empty")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate_manifest(args.manifest)
    if errors:
        print("Release validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Release validation passed: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
