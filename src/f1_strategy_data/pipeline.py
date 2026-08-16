"""Reference-race build pipeline with immutable raw snapshots."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .normalize import (
    count_shared_stint_boundaries,
    driver_number_map,
    jolpica_race,
    normalize_pit_events,
    normalize_jolpica_pit_events,
    normalize_race_drivers,
    normalize_stints,
    normalize_weather,
)
from .sources import jolpica_pit_stops, jolpica_results, openf1
from .validation import duplicate_key_issues, pit_stop_issues, stint_issues, weather_issues


TABLE_KEYS = {
    "race_drivers": ("season", "round_number", "driver_id"),
    "stints": ("session_key", "driver_id", "stint_number"),
    "pit_events": ("session_key", "driver_id", "stop_number"),
    "weather_observations": ("session_key", "observed_at_utc", "weather_source"),
}


def build_reference_race(
    season: int,
    round_number: int,
    session_key: int,
    root: Path,
    refresh: bool = False,
) -> dict[str, Any]:
    raw_dir = root / "raw" / str(season) / f"round-{round_number:02d}"
    processed_dir = root / "processed" / str(season) / f"round-{round_number:02d}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    payloads: dict[str, Any] = {}
    provenance: dict[str, dict[str, str]] = {}
    for name, loader in {
        "jolpica_results": lambda: jolpica_results(season, round_number),
        "jolpica_pits": lambda: jolpica_pit_stops(season, round_number),
        "openf1_results": lambda: openf1("session_result", session_key=session_key),
        "openf1_stints": lambda: openf1("stints", session_key=session_key),
        "openf1_pits": lambda: openf1("pit", session_key=session_key),
        "openf1_weather": lambda: openf1("weather", session_key=session_key),
    }.items():
        payloads[name], provenance[name] = _load_or_fetch(raw_dir, name, loader, refresh)

    race = jolpica_race(payloads["jolpica_results"])
    identifiers = driver_number_map(race)
    race_drivers, result_mismatches = normalize_race_drivers(
        race, payloads["openf1_results"], session_key, **provenance["jolpica_results"]
    )
    completed_laps = {row["driver_id"]: row["laps_completed"] for row in race_drivers}
    tables = {
        "race_drivers": race_drivers,
        "stints": normalize_stints(payloads["openf1_stints"], identifiers, season, round_number, **provenance["openf1_stints"]),
        "pit_events": normalize_jolpica_pit_events(
            payloads["jolpica_pits"], payloads["openf1_pits"], identifiers, completed_laps,
            season, round_number, session_key, **provenance["jolpica_pits"]
        ),
        "weather_observations": normalize_weather(payloads["openf1_weather"], season, round_number, **provenance["openf1_weather"]),
    }

    issue_records: list[dict[str, Any]] = []
    adjusted_boundaries = count_shared_stint_boundaries(payloads["openf1_stints"], identifiers)
    if adjusted_boundaries:
        issue_records.append({
            "severity": "info",
            "code": "normalized_shared_stint_boundary",
            "table": "stints",
            "count": adjusted_boundaries,
            "message": "Moved later stint starts one lap forward where OpenF1 assigned a boundary lap to both stints",
        })
    for table, rows in tables.items():
        issue_records.extend(issue.__dict__ | {"table": table} for issue in duplicate_key_issues(rows, TABLE_KEYS[table]))
    issue_records.extend(issue.__dict__ | {"table": "pit_events"} for issue in pit_stop_issues(tables["pit_events"]))
    issue_records.extend(issue.__dict__ | {"table": "stints"} for issue in stint_issues(tables["stints"]))
    issue_records.extend(issue.__dict__ | {"table": "weather_observations"} for issue in weather_issues(tables["weather_observations"]))
    issue_records.extend({"severity": "error", "code": "result_position_mismatch", "table": "race_drivers", **item} for item in result_mismatches)
    openf1_pits = normalize_pit_events(
        payloads["openf1_pits"], identifiers, completed_laps, season, round_number,
        **provenance["openf1_pits"]
    )
    issue_records.extend(_pit_count_mismatches(payloads["jolpica_pits"], openf1_pits))

    for name, rows in tables.items():
        _write_csv(processed_dir / f"{name}.csv", rows)

    report = {
        "season": season,
        "round_number": round_number,
        "session_key": session_key,
        "table_rows": {name: len(rows) for name, rows in tables.items()},
        "source_checksums_sha256": {name: _sha256(raw_dir / f"{name}.json") for name in payloads},
        "issues": issue_records,
        "status": (
            "quarantined" if any(issue["severity"] == "error" for issue in issue_records)
            else "warning" if any(issue["severity"] == "warning" for issue in issue_records)
            else "verified"
        ),
    }
    _write_json(processed_dir / "validation_report.json", report)
    return report


def _load_or_fetch(raw_dir: Path, name: str, loader: Any, refresh: bool) -> tuple[Any, dict[str, str]]:
    payload_path = raw_dir / f"{name}.json"
    provenance_path = raw_dir / f"{name}.provenance.json"
    if not refresh and payload_path.exists() and provenance_path.exists():
        return (
            json.loads(payload_path.read_text(encoding="utf-8")),
            json.loads(provenance_path.read_text(encoding="utf-8")),
        )
    payload, provenance = loader()
    _write_json(payload_path, payload)
    _write_json(provenance_path, provenance)
    return payload, provenance


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty canonical table: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pit_count_mismatches(jolpica_payload: dict[str, Any], openf1_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    races = jolpica_payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    jolpica_rows = races[0].get("PitStops", []) if races else []
    jolpica_counts: dict[str, int] = {}
    openf1_counts: dict[str, int] = {}
    for row in jolpica_rows:
        jolpica_counts[row["driverId"]] = jolpica_counts.get(row["driverId"], 0) + 1
    for row in openf1_rows:
        openf1_counts[row["driver_id"]] = openf1_counts.get(row["driver_id"], 0) + 1
    return [{
        "severity": "warning",
        "code": "pit_count_mismatch",
        "table": "pit_events",
        "driver_id": driver_id,
        "jolpica_count": jolpica_counts.get(driver_id, 0),
        "openf1_count": openf1_counts.get(driver_id, 0),
    } for driver_id in sorted(jolpica_counts.keys() | openf1_counts.keys())
      if jolpica_counts.get(driver_id, 0) != openf1_counts.get(driver_id, 0)]
