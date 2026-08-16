"""Build leakage-safe pre-race finishing-position features."""

from __future__ import annotations

import argparse
from pathlib import Path

from f1_strategy_data.features import build_pre_race_feature_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Consolidated race_drivers.csv")
    parser.add_argument("--output", type=Path, default=Path("data/features/pre_race_finishing_position.csv"))
    parser.add_argument("--holdout-season", type=int, help="This season and later are marked as test")
    parser.add_argument("--race-context", type=Path)
    args = parser.parse_args()
    count = build_pre_race_feature_file(args.input, args.output, args.holdout_season, args.race_context)
    print(f"Wrote {count} leakage-safe rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
