"""Create a self-contained directory accepted by the Kaggle CLI."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def prepare_release(data_root: Path, start_year: int, end_year: int, destination: Path, slug: str) -> None:
    source = data_root / "processed" / f"consolidated_{start_year}_{end_year}"
    manifest = data_root / "processed" / f"manifest_{start_year}_{end_year}.json"
    if not source.is_dir() or not manifest.is_file():
        raise FileNotFoundError("Run scripts/build_seasons.py before preparing a release")
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.csv"):
        shutil.copy2(path, destination / path.name)
    shutil.copy2(manifest, destination / "validation_manifest.json")
    # Existing dataset versions only need the target dataset identifier.
    # Creation-only fields can make Kaggle reject CreateDatasetVersion after
    # the individual files have already uploaded successfully.
    metadata = {"id": slug}
    (destination / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--destination", type=Path, default=Path("release/kaggle"))
    parser.add_argument("--slug", required=True, help="Kaggle owner/dataset-slug")
    args = parser.parse_args()
    prepare_release(args.data_root, args.start_year, args.end_year, args.destination, args.slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
