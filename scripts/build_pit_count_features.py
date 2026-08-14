"""Build leakage-safe pre-race pit-stop-count features."""

from __future__ import annotations

import argparse
from pathlib import Path

from f1_strategy_data.features import build_pit_count_feature_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--race-drivers", type=Path, required=True)
    parser.add_argument("--pit-events", type=Path, required=True)
    parser.add_argument("--stints", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/features/pre_race_pit_stop_count.csv"))
    parser.add_argument("--holdout-season", type=int)
    args = parser.parse_args()
    count = build_pit_count_feature_file(
        args.race_drivers, args.pit_events, args.stints, args.output, args.holdout_season
    )
    print(f"Wrote {count} leakage-safe rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
