"""Build and consolidate completed races across a season range."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1_strategy_data.batch import build_seasons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=1950)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached raw source snapshots")
    args = parser.parse_args()
    manifest = build_seasons(args.start_year, args.end_year, args.data_root, not args.fail_fast, args.refresh)
    print(json.dumps({"summary": manifest["summary"], "consolidated_rows": manifest["consolidated_rows"]}, indent=2))
    failed_runs = [run for run in manifest["runs"] if run.get("status") == "failed"]
    if failed_runs:
        print("\nFailed race builds:")
        for run in failed_runs:
            season = run.get("season", "unknown")
            round_number = run.get("round_number", "unknown")
            race_name = run.get("race_name") or "unknown race"
            reason = run.get("reason") or "No failure reason was recorded"
            print(f"- {season} round {round_number} ({race_name}): {reason}")
        print(f"\nDiagnostic manifest: {args.data_root / 'processed' / f'manifest_{args.start_year}_{args.end_year}.json'}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
