"""Build the Phase 2 reference race from live source APIs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from f1_strategy_data.pipeline import build_reference_race


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--round", dest="round_number", type=int, default=11)
    parser.add_argument("--session-key", type=int, default=11342)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    args = parser.parse_args()
    report = build_reference_race(args.season, args.round_number, args.session_key, args.data_root)
    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "quarantined" else 0


if __name__ == "__main__":
    raise SystemExit(main())