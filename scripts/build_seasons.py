"""Build and consolidate completed races across a season range."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1_strategy_data.batch import build_seasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2023)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached raw source snapshots")
    args = parser.parse_args()
    manifest = build_seasons(args.start_year, args.end_year, args.data_root, not args.fail_fast, args.refresh)
    print(json.dumps({"summary": manifest["summary"], "consolidated_rows": manifest["consolidated_rows"]}, indent=2))
    return 1 if manifest["summary"].get("failed", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
