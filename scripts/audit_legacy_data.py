"""Profile legacy CSVs without modifying them."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def audit_csv(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames or []

    canonical = [json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows]
    duplicate_rows = sum(count - 1 for count in Counter(canonical).values() if count > 1)
    nulls = {column: sum(row.get(column, "").strip() == "" for row in rows) for column in columns}
    mojibake_markers = ("Ãƒ", "Ã‚", "Ã¢", "Ã°Å¸")
    mojibake_rows = sum(any(marker in value for marker in mojibake_markers for value in row.values()) for row in rows)

    return {
        "file": str(path),
        "rows": len(rows),
        "columns": columns,
        "duplicate_rows": duplicate_rows,
        "null_counts": nulls,
        "rows_with_possible_mojibake": mojibake_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = [audit_csv(path) for path in args.paths]
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
