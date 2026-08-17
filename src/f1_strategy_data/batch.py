"""Batch orchestration and consolidated canonical outputs."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .discovery import discover_completed_races
from .pipeline import build_historical_season, build_reference_race


TABLES = ("race_context", "race_drivers", "stints", "pit_events", "weather_observations")


def build_seasons(
    start_year: int,
    end_year: int,
    root: Path,
    continue_on_error: bool = True,
    refresh: bool = False,
) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for season in range(start_year, end_year + 1):
        print(f"Building season {season} ({season - start_year + 1}/{end_year - start_year + 1})", flush=True)
        if season < 2023:
            try:
                reports = build_historical_season(season, root, refresh=refresh)
                runs.extend({
                    "season": season,
                    "round_number": report["round_number"],
                    "race_name": report.get("race_name", ""),
                    "race_date": report.get("race_date", ""),
                    "detailed_source_status": "historical_results_only",
                    "status": report["status"],
                    "table_rows": report["table_rows"],
                    "issues": report["issues"],
                } for report in reports)
            except Exception as error:
                runs.append({
                    "season": season, "round_number": 0,
                    "status": "failed", "reason": f"{type(error).__name__}: {error}",
                })
                if not continue_on_error:
                    raise
            continue
        try:
            completed_races = discover_completed_races(season)
        except Exception as error:
            runs.append({
                "season": season,
                "round_number": 0,
                "race_name": "season discovery",
                "status": "failed",
                "reason": f"{type(error).__name__}: {error}",
            })
            if not continue_on_error:
                raise
            continue
        for race in completed_races:
            record = race.as_dict()
            if race.session_key is None:
                record.update(status="unavailable", reason="OpenF1 detailed session coverage is unavailable; FastF1 backfill required")
                runs.append(record)
                continue
            try:
                report = build_reference_race(season, race.round_number, race.session_key, root, refresh=refresh)
                record.update(status=report["status"], table_rows=report["table_rows"], issues=report["issues"])
            except Exception as error:
                record.update(status="failed", reason=f"{type(error).__name__}: {error}")
                if not continue_on_error:
                    raise
            runs.append(record)

    consolidated = consolidate(root, start_year, end_year)
    manifest = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "start_year": start_year,
        "end_year": end_year,
        "runs": runs,
        "consolidated_rows": consolidated,
        "summary": _summary(runs),
    }
    output = root / "processed" / f"manifest_{start_year}_{end_year}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def consolidate(
    root: Path,
    start_year: int,
    end_year: int,
    allowed_statuses: tuple[str, ...] = ("verified",),
) -> dict[str, int]:
    """Combine publication-safe tables independently.

    A defect in telemetry must not delete an independently valid official race
    result. A table is excluded only when that table has an error-level issue.
    """
    destination = root / "processed" / f"consolidated_{start_year}_{end_year}"
    destination.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for table in TABLES:
        paths = sorted((root / "processed").glob("????/round-??/" + table + ".csv"))
        paths = [path for path in paths if start_year <= int(path.parts[-3]) <= end_year]
        rows: list[dict[str, str]] = []
        for path in paths:
            report_path = path.parent / "validation_report.json"
            if not report_path.exists():
                continue
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("status") == "failed":
                continue
            table_errors = [
                issue for issue in report.get("issues", [])
                if issue.get("severity") == "error" and issue.get("table") == table
            ]
            if table_errors:
                continue
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows.extend(csv.DictReader(handle))
        counts[table] = len(rows)
        output = destination / f"{table}.csv"
        if rows:
            with output.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        elif output.exists():
            output.unlink()
    return counts


def _summary(runs: Iterable[dict[str, Any]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for run in runs:
        status = str(run["status"])
        summary[status] = summary.get(status, 0) + 1
    return summary
