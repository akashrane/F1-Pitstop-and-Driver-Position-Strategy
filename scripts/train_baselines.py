"""Train and evaluate all Phase 5 chronological baseline models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1_strategy_data.modeling import evaluate_files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finishing-position", type=Path, required=True)
    parser.add_argument("--pit-stop-count", type=Path, required=True)
    parser.add_argument("--next-pit", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("reports/generated/baseline_metrics.json"))
    args = parser.parse_args()
    result = evaluate_files({
        "finishing_position": args.finishing_position,
        "pit_stop_count": args.pit_stop_count,
        "next_pit": args.next_pit,
    }, args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
