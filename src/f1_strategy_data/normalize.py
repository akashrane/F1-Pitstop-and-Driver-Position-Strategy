"""Normalize source responses into the canonical Phase 1 schemas."""

from __future__ import annotations

from typing import Any, Iterable


def jolpica_race(payload: dict[str, Any]) -> dict[str, Any]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if len(races) != 1:
        raise ValueError(f"Expected exactly one Jolpica race, received {len(races)}")
    return races[0]


def driver_number_map(race: dict[str, Any]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for result in race.get("Results", []):
        driver = result["Driver"]
        # OpenF1 keys records by the number used at the event. This can differ
        # from a driver's permanent number (for example, the champion's 1).
        number = result.get("number") or driver.get("permanentNumber")
        if number is not None:
            mapping[int(number)] = driver["driverId"]
    return mapping


def normalize_race_drivers(
    race: dict[str, Any],
    openf1_results: Iterable[dict[str, Any]],
    session_key: int,
    source_url: str,
    retrieved_at_utc: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_number = {int(row["driver_number"]): row for row in openf1_results}
    rows: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for result in race.get("Results", []):
        driver = result["Driver"]
        number_value = result.get("number") or driver.get("permanentNumber")
        number = int(number_value) if number_value is not None else None
        openf1_row = by_number.get(number) if number is not None else None
        jolpica_position = _optional_int(result.get("position"))
        openf1_position = _optional_int(openf1_row.get("position")) if openf1_row else None
        if openf1_position is not None and jolpica_position != openf1_position:
            mismatches.append({
                "driver_id": driver["driverId"],
                "jolpica_position": jolpica_position,
                "openf1_position": openf1_position,
            })
        rows.append({
            "season": int(race["season"]),
            "round_number": int(race["round"]),
            "session_key": session_key,
            "driver_id": driver["driverId"],
            "driver_name": f"{driver['givenName']} {driver['familyName']}",
            "constructor_id": result.get("Constructor", {}).get("constructorId"),
            "grid_position": _optional_int(result.get("grid")),
            "classified_position": jolpica_position,
            "laps_completed": _optional_int(result.get("laps")),
            "status": result.get("status", "Unknown"),
            "source": "jolpica",
            "source_url": source_url,
            "retrieved_at_utc": retrieved_at_utc,
            "validation_status": "verified" if openf1_position == jolpica_position else "warning",
        })
    return rows, mismatches


def normalize_stints(
    source_rows: Iterable[dict[str, Any]],
    identifiers: dict[int, str],
    season: int,
    round_number: int,
    source_url: str,
    retrieved_at_utc: str,
) -> list[dict[str, Any]]:
    rows = [{
        "season": season,
        "round_number": round_number,
        "session_key": int(row["session_key"]),
        "driver_id": identifiers[int(row["driver_number"])],
        "stint_number": int(row["stint_number"]),
        "compound": row.get("compound"),
        "lap_start": int(row["lap_start"]),
        "lap_end": int(row["lap_end"]),
        "tyre_age_at_start_laps": _optional_int(row.get("tyre_age_at_start")),
        "source": "openf1",
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at_utc,
        "validation_status": "verified",
    } for row in source_rows if int(row["driver_number"]) in identifiers]
    by_driver: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_driver.setdefault((row["session_key"], row["driver_id"]), []).append(row)
    for driver_rows in by_driver.values():
        ordered = sorted(driver_rows, key=lambda row: (row["stint_number"], row["lap_start"]))
        for previous, current in zip(ordered, ordered[1:]):
            # Some OpenF1 historical records assign the pit lap to both stints.
            # Keep it as the completed lap of the old stint and begin the new
            # stint on the following lap. Larger overlaps remain validation errors.
            if current["lap_start"] == previous["lap_end"]:
                current["lap_start"] += 1
    return rows


def count_shared_stint_boundaries(
    source_rows: Iterable[dict[str, Any]], identifiers: dict[int, str]
) -> int:
    """Count adjacent source stints sharing exactly one boundary lap."""
    by_driver: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for row in source_rows:
        driver_number = int(row["driver_number"])
        if driver_number in identifiers:
            key = (int(row["session_key"]), driver_number)
            by_driver.setdefault(key, []).append(
                (int(row["stint_number"]), int(row["lap_start"]), int(row["lap_end"]))
            )
    return sum(
        current[1] == previous[2]
        for spans in by_driver.values()
        for previous, current in zip(sorted(spans), sorted(spans)[1:])
    )


def normalize_pit_events(
    source_rows: Iterable[dict[str, Any]],
    identifiers: dict[int, str],
    completed_laps: dict[str, int | None],
    season: int,
    round_number: int,
    source_url: str,
    retrieved_at_utc: str,
) -> list[dict[str, Any]]:
    counters: dict[str, int] = {}
    output: list[dict[str, Any]] = []
    for row in sorted(source_rows, key=lambda item: (int(item["driver_number"]), item["date"])):
        driver_id = identifiers.get(int(row["driver_number"]))
        if driver_id is None:
            continue
        counters[driver_id] = counters.get(driver_id, 0) + 1
        output.append({
            "season": season,
            "round_number": round_number,
            "session_key": int(row["session_key"]),
            "driver_id": driver_id,
            "stop_number": counters[driver_id],
            "lap_number": int(row["lap_number"]),
            "pit_duration_s": _optional_float(row.get("pit_duration") or row.get("lane_duration")),
            "stop_duration_s": _optional_float(row.get("stop_duration")),
            "driver_laps_completed": completed_laps.get(driver_id),
            "source": "openf1",
            "source_url": source_url,
            "retrieved_at_utc": retrieved_at_utc,
            "validation_status": "verified",
        })
    return output


def normalize_jolpica_pit_events(
    jolpica_payload: dict[str, Any],
    openf1_rows: Iterable[dict[str, Any]],
    identifiers: dict[int, str],
    completed_laps: dict[str, int | None],
    season: int,
    round_number: int,
    session_key: int,
    source_url: str,
    retrieved_at_utc: str,
) -> list[dict[str, Any]]:
    races = jolpica_payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    jolpica_rows = races[0].get("PitStops", []) if races else []
    openf1_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in openf1_rows:
        driver_id = identifiers.get(int(row["driver_number"]))
        if driver_id is not None:
            openf1_by_key[(driver_id, int(row["lap_number"]))] = row
    output: list[dict[str, Any]] = []
    for row in jolpica_rows:
        driver_id = row["driverId"]
        lap_number = int(row["lap"])
        enrichment = openf1_by_key.get((driver_id, lap_number), {})
        output.append({
            "season": season,
            "round_number": round_number,
            "session_key": session_key,
            "driver_id": driver_id,
            "stop_number": int(row["stop"]),
            "lap_number": lap_number,
            "pit_duration_s": _optional_float(enrichment.get("pit_duration") or enrichment.get("lane_duration") or row.get("duration")),
            "stop_duration_s": _optional_float(enrichment.get("stop_duration")),
            "driver_laps_completed": completed_laps.get(driver_id),
            "source": "jolpica",
            "source_url": source_url,
            "retrieved_at_utc": retrieved_at_utc,
            "validation_status": "verified" if enrichment else "warning",
        })
    return output


def normalize_weather(
    source_rows: Iterable[dict[str, Any]],
    season: int,
    round_number: int,
    source_url: str,
    retrieved_at_utc: str,
) -> list[dict[str, Any]]:
    return [{
        "season": season,
        "round_number": round_number,
        "session_key": int(row["session_key"]),
        "observed_at_utc": row["date"],
        "air_temperature_c": _optional_float(row.get("air_temperature")),
        "track_temperature_c": _optional_float(row.get("track_temperature")),
        "humidity_pct": _optional_float(row.get("humidity")),
        "pressure_mbar": _optional_float(row.get("pressure")),
        "rainfall": row.get("rainfall"),
        "wind_direction_deg": _optional_int(row.get("wind_direction")),
        "wind_speed_ms": _optional_float(row.get("wind_speed")),
        "weather_source": "openf1",
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at_utc,
        "validation_status": "verified",
    } for row in source_rows]


def _optional_int(value: object) -> int | None:
    return None if value in (None, "") else int(value)


def _optional_float(value: object) -> float | None:
    return None if value in (None, "") else float(value)
