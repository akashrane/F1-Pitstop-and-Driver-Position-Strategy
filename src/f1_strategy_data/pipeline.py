"""Reference-race build pipeline with immutable raw snapshots."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError

from .normalize import (
    completed_laps_for_pit_validation,
    count_shared_stint_boundaries,
    driver_number_map,
    jolpica_race,
    normalize_pit_events,
    normalize_jolpica_pit_events,
    normalize_race_drivers,
    normalize_race_context,
    normalize_historical_race_context,
    normalize_stints,
    normalize_weather,
)
from .sources import (
    jolpica_pit_stops, jolpica_results, jolpica_season_full_results, openf1,
)
from .validation import duplicate_key_issues, pit_stop_issues, stint_issues, weather_issues


TABLE_KEYS = {
    "race_context": ("season", "round_number"),
    "race_drivers": ("season", "round_number", "driver_id", "car_number"),
    "stints": ("session_key", "driver_id", "stint_number"),
    "pit_events": ("season", "round_number", "driver_id", "stop_number"),
    "weather_observations": ("session_key", "observed_at_utc", "weather_source"),
}


def build_historical_season(
    season: int, root: Path, refresh: bool = False
) -> list[dict[str, Any]]:
    """Build pre-OpenF1 races from two immutable season-level Jolpica snapshots."""
    raw_dir = root / "raw" / str(season)
    raw_dir.mkdir(parents=True, exist_ok=True)
    results_payload, results_provenance = _load_or_fetch(
        raw_dir, "jolpica_season_results", lambda: jolpica_season_full_results(season), refresh
    )
    races = results_payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    reports: list[dict[str, Any]] = []
    for race in races:
        round_number = int(race["round"])
        processed_dir = root / "processed" / str(season) / f"round-{round_number:02d}"
        processed_dir.mkdir(parents=True, exist_ok=True)
        race_drivers, _ = normalize_race_drivers(
            race, [], None, **results_provenance
        )
        completed_laps = completed_laps_for_pit_validation(race_drivers)
        if season >= 2011:
            race_raw_dir = raw_dir / f"round-{round_number:02d}"
            race_raw_dir.mkdir(parents=True, exist_ok=True)
            pit_wrapper, pits_provenance = _load_or_fetch(
                race_raw_dir, "jolpica_pits",
                lambda round_number=round_number: jolpica_pit_stops(season, round_number),
                refresh,
            )
        else:
            pit_wrapper = {"MRData": {"RaceTable": {"Races": []}}}
            pits_provenance = results_provenance
        pit_events = normalize_jolpica_pit_events(
            pit_wrapper, [], {}, completed_laps, season, round_number, None, **pits_provenance
        )
        for row in pit_events:
            row["validation_status"] = "verified"
        tables = {
            "race_context": normalize_historical_race_context(race, **results_provenance),
            "race_drivers": race_drivers,
            "pit_events": pit_events,
        }
        issues: list[dict[str, Any]] = [{
            "severity": "info", "code": "detailed_telemetry_unavailable",
            "message": "OpenF1 stints, trackside weather, and race control are unavailable before 2023",
        }]
        if season < 2011:
            issues.append({
                "severity": "info", "code": "pit_events_unavailable",
                "message": "The upstream archive does not provide pit-stop events before 2011",
            })
        for table, rows in tables.items():
            issues.extend(
                issue.__dict__ | {"table": table}
                for issue in duplicate_key_issues(rows, TABLE_KEYS[table])
            )
        issues.extend(issue.__dict__ | {"table": "pit_events"} for issue in pit_stop_issues(pit_events))
        for name, rows in tables.items():
            if rows:
                _write_csv(processed_dir / f"{name}.csv", rows)
            else:
                stale = processed_dir / f"{name}.csv"
                if stale.exists():
                    stale.unlink()
        report = {
            "season": season,
            "round_number": round_number,
            "race_name": race.get("raceName", ""),
            "race_date": race.get("date", ""),
            "session_key": None,
            "table_rows": {name: len(rows) for name, rows in tables.items()},
            "source_checksums_sha256": {
                "jolpica_season_results": _sha256(raw_dir / "jolpica_season_results.json"),
                **({"jolpica_pits": _sha256(
                    raw_dir / f"round-{round_number:02d}" / "jolpica_pits.json"
                )}
                   if season >= 2011 else {}),
            },
            "issues": issues,
            "status": "quarantined" if any(item["severity"] == "error" for item in issues) else "verified",
        }
        _write_json(processed_dir / "validation_report.json", report)
        reports.append(report)
    return reports


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
    required_loaders = {
        "jolpica_results": lambda: jolpica_results(season, round_number),
        "jolpica_pits": lambda: jolpica_pit_stops(season, round_number),
    }
    optional_loaders = {
        "openf1_results": lambda: openf1("session_result", session_key=session_key),
        "openf1_session": lambda: openf1("sessions", session_key=session_key),
        "openf1_race_control": lambda: openf1("race_control", session_key=session_key),
        "openf1_stints": lambda: openf1("stints", session_key=session_key),
        "openf1_pits": lambda: openf1("pit", session_key=session_key),
        "openf1_weather": lambda: openf1("weather", session_key=session_key),
    }
    for name, loader in required_loaders.items():
        payloads[name], provenance[name] = _load_or_fetch(raw_dir, name, loader, refresh)
    unavailable_sources: list[str] = []
    for name, loader in optional_loaders.items():
        try:
            payloads[name], provenance[name] = _load_or_fetch(raw_dir, name, loader, refresh)
        except HTTPError as error:
            if error.code != 404:
                raise
            payloads[name] = []
            provenance[name] = provenance["jolpica_results"]
            unavailable_sources.append(name)

    race = jolpica_race(payloads["jolpica_results"])
    identifiers = driver_number_map(race)
    race_drivers, result_mismatches = normalize_race_drivers(
        race, payloads["openf1_results"], session_key, **provenance["jolpica_results"]
    )
    completed_laps = completed_laps_for_pit_validation(race_drivers)
    valid_stint_payloads = [
        row for row in payloads["openf1_stints"]
        if row.get("lap_start") is not None and row.get("lap_end") is not None
    ]
    race_context = (
        normalize_race_context(
            payloads["openf1_session"], payloads["openf1_race_control"],
            payloads["openf1_weather"], race, session_key, **provenance["openf1_session"]
        ) if payloads["openf1_session"] else
        normalize_historical_race_context(race, **provenance["jolpica_results"])
    )
    normalized_stints = normalize_stints(
        valid_stint_payloads, identifiers, season, round_number,
        **provenance["openf1_stints"],
    )
    tables = {
        "race_context": race_context,
        "race_drivers": race_drivers,
        "stints": normalized_stints,
        "pit_events": normalize_jolpica_pit_events(
            payloads["jolpica_pits"], payloads["openf1_pits"], identifiers, completed_laps,
            season, round_number, session_key, **provenance["jolpica_pits"]
        ),
        "weather_observations": normalize_weather(payloads["openf1_weather"], season, round_number, **provenance["openf1_weather"]),
    }

    issue_records: list[dict[str, Any]] = []
    issue_records.extend({
        "severity": "info", "code": "optional_source_unavailable", "source": name,
        "message": f"{name} returned 404; available canonical tables were preserved",
    } for name in unavailable_sources)
    omitted_stints = len(payloads["openf1_stints"]) - len(valid_stint_payloads)
    if omitted_stints:
        issue_records.append({
            "severity": "info", "code": "incomplete_stint_boundary", "table": "stints",
            "count": omitted_stints, "message": "Omitted source stint rows without both lap boundaries",
        })
    identified_stints = [
        row for row in valid_stint_payloads
        if row.get("driver_number") is not None
        and int(row["driver_number"]) in identifiers
    ]
    omitted_zero_lap_stints = len(identified_stints) - len(normalized_stints)
    if omitted_zero_lap_stints:
        issue_records.append({
            "severity": "info", "code": "zero_lap_stint_omitted", "table": "stints",
            "count": omitted_zero_lap_stints,
            "message": "Omitted source tyre records that covered no exclusive completed racing lap",
        })
    adjusted_boundaries = count_shared_stint_boundaries(valid_stint_payloads, identifiers)
    if adjusted_boundaries:
        issue_records.append({
            "severity": "info",
            "code": "normalized_shared_stint_boundary",
            "table": "stints",
            "count": adjusted_boundaries,
            "message": "Resolved shared boundary laps by moving later stint starts or omitting zero-lap tyre records",
        })
    for table, rows in tables.items():
        issue_records.extend(issue.__dict__ | {"table": table} for issue in duplicate_key_issues(rows, TABLE_KEYS[table]))
    issue_records.extend(issue.__dict__ | {"table": "pit_events"} for issue in pit_stop_issues(tables["pit_events"]))
    issue_records.extend(issue.__dict__ | {"table": "stints"} for issue in stint_issues(tables["stints"]))
    issue_records.extend(issue.__dict__ | {"table": "weather_observations"} for issue in weather_issues(tables["weather_observations"]))
    issue_records.extend({"severity": "warning", "code": "result_position_mismatch", "table": "race_drivers", **item} for item in result_mismatches)
    openf1_pits = normalize_pit_events(
        payloads["openf1_pits"], identifiers, completed_laps, season, round_number,
        **provenance["openf1_pits"]
    )
    if "openf1_pits" not in unavailable_sources:
        issue_records.extend(_pit_count_mismatches(payloads["jolpica_pits"], openf1_pits))

    for name, rows in tables.items():
        output = processed_dir / f"{name}.csv"
        if rows:
            _write_csv(output, rows)
        elif output.exists():
            output.unlink()

    report = {
        "season": season,
        "round_number": round_number,
        "session_key": session_key,
        "table_rows": {name: len(rows) for name, rows in tables.items()},
        "source_checksums_sha256": {
            name: _sha256(raw_dir / f"{name}.json")
            for name in payloads if (raw_dir / f"{name}.json").exists()
        },
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
