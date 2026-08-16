"""Leakage-safe feature builders for Formula 1 prediction tasks."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Iterable


PRE_RACE_COLUMNS = (
    "season", "round_number", "session_key", "driver_id", "constructor_id",
    "grid_position", "driver_prior_starts", "driver_prior_avg_finish",
    "driver_prior_avg_grid", "driver_prior_dnf_rate",
    "driver_prior_avg_positions_gained", "driver_recent5_avg_finish",
    "driver_recent5_avg_grid", "constructor_prior_starts",
    "constructor_prior_avg_finish", "constructor_prior_dnf_rate",
    "constructor_recent5_avg_finish", "circuit_key", "start_air_temperature_c",
    "start_track_temperature_c", "start_humidity_pct", "start_pressure_mbar",
    "start_rainfall", "start_wind_speed_ms", "circuit_prior_races",
    "circuit_prior_avg_winner_laps", "circuit_prior_avg_safety_cars",
    "circuit_prior_avg_virtual_safety_cars", "circuit_prior_rain_rate",
    "classified_position", "dataset_split",
)

PIT_COUNT_COLUMNS = (
    "season", "round_number", "session_key", "driver_id", "constructor_id",
    "grid_position", "driver_prior_races", "driver_prior_avg_pit_stops",
    "driver_recent5_avg_pit_stops", "driver_prior_zero_stop_rate",
    "driver_prior_two_plus_stop_rate", "driver_prior_avg_stints",
    "constructor_prior_driver_races", "constructor_prior_avg_pit_stops",
    "constructor_recent5_avg_pit_stops", "circuit_key", "start_air_temperature_c",
    "start_track_temperature_c", "start_humidity_pct", "start_pressure_mbar",
    "start_rainfall", "start_wind_speed_ms", "circuit_prior_races",
    "circuit_prior_avg_winner_laps", "circuit_prior_avg_safety_cars",
    "circuit_prior_avg_virtual_safety_cars", "circuit_prior_rain_rate",
    "pit_stop_count", "dataset_split",
)

NEXT_PIT_COLUMNS = (
    "season", "round_number", "session_key", "driver_id", "lap_number",
    "current_stint_number", "current_compound", "tyre_age_laps",
    "pit_stops_completed", "laps_since_last_pit", "pit_this_lap",
    "next_pit_lap", "laps_until_next_pit", "event_observed", "dataset_split",
)


def build_pre_race_finishing_features(
    rows: Iterable[dict[str, str]], holdout_season: int | None = None,
    context_rows: Iterable[dict[str, str]] = (),
) -> list[dict[str, object]]:
    """Build rolling features using completed races strictly before each row's race."""
    ordered = sorted(rows, key=lambda row: (
        int(row["season"]), int(row["round_number"]), row["driver_id"]
    ))
    driver_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    constructor_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    contexts = _context_by_race(context_rows)
    circuit_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    output: list[dict[str, object]] = []

    for race_rows in _group_races(ordered):
        race_key = (int(race_rows[0]["season"]), int(race_rows[0]["round_number"]))
        context = contexts.get(race_key)
        context_features = _context_features(context, circuit_history)
        pending: list[tuple[dict[str, str], dict[str, object]]] = []
        for row in race_rows:
            finish = _required_positive_int(row.get("classified_position"), "classified_position")
            driver = driver_history[row["driver_id"]]
            constructor_id = row.get("constructor_id", "")
            constructor = constructor_history[constructor_id] if constructor_id else []
            season = int(row["season"])
            feature_row: dict[str, object] = {
                "season": season,
                "round_number": int(row["round_number"]),
                "session_key": _optional_int(row.get("session_key")),
                "driver_id": row["driver_id"],
                "constructor_id": constructor_id or None,
                "grid_position": _optional_int(row.get("grid_position")),
                **_history_features("driver", driver),
                **_history_features("constructor", constructor, recent_grid=False, positions_gained=False),
                **context_features,
                "classified_position": finish,
                "dataset_split": "test" if holdout_season is not None and season >= holdout_season else "train",
            }
            output.append(feature_row)
            pending.append((row, _history_record(row, finish)))

        # Update only after every driver in this race has received their features.
        for row, record in pending:
            driver_history[row["driver_id"]].append(record)
            constructor_id = row.get("constructor_id", "")
            if constructor_id:
                constructor_history[constructor_id].append(record)
        _update_circuit_history(context, circuit_history)
    return output


def build_pre_race_feature_file(input_path: Path, output_path: Path, holdout_season: int | None = None,
                                context_path: Path | None = None) -> int:
    with input_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    contexts = _read_optional_csv(context_path)
    features = build_pre_race_finishing_features(rows, holdout_season, contexts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PRE_RACE_COLUMNS))
        writer.writeheader()
        writer.writerows(features)
    return len(features)


def build_pit_count_features(
    race_rows: Iterable[dict[str, str]],
    pit_rows: Iterable[dict[str, str]],
    stint_rows: Iterable[dict[str, str]],
    holdout_season: int | None = None,
    context_rows: Iterable[dict[str, str]] = (),
) -> list[dict[str, object]]:
    """Build pre-race pit-count features and observed stop-count targets."""
    pit_counts = _counts_by_driver_race(pit_rows)
    stint_counts = _counts_by_driver_race(stint_rows)
    ordered = sorted(race_rows, key=lambda row: (
        int(row["season"]), int(row["round_number"]), row["driver_id"]
    ))
    driver_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    constructor_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    contexts = _context_by_race(context_rows)
    circuit_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    output: list[dict[str, object]] = []
    for current_race in _group_races(ordered):
        race_key = (int(current_race[0]["season"]), int(current_race[0]["round_number"]))
        context = contexts.get(race_key)
        context_features = _context_features(context, circuit_history)
        pending: list[tuple[dict[str, str], dict[str, object]]] = []
        for row in current_race:
            key = _driver_race_key(row)
            stops = pit_counts.get(key, 0)
            stints = stint_counts.get(key)
            driver = driver_history[row["driver_id"]]
            constructor_id = row.get("constructor_id", "")
            constructor = constructor_history[constructor_id] if constructor_id else []
            season = int(row["season"])
            output.append({
                "season": season,
                "round_number": int(row["round_number"]),
                "session_key": _optional_int(row.get("session_key")),
                "driver_id": row["driver_id"],
                "constructor_id": constructor_id or None,
                "grid_position": _optional_int(row.get("grid_position")),
                **_pit_history_features("driver", driver),
                **_pit_history_features("constructor", constructor),
                **context_features,
                "pit_stop_count": stops,
                "dataset_split": "test" if holdout_season is not None and season >= holdout_season else "train",
            })
            pending.append((row, {"pit_stops": stops, "stints": stints}))
        for row, record in pending:
            driver_history[row["driver_id"]].append(record)
            constructor_id = row.get("constructor_id", "")
            if constructor_id:
                constructor_history[constructor_id].append(record)
        _update_circuit_history(context, circuit_history)
    return output


def build_pit_count_feature_file(
    race_path: Path, pit_path: Path, stint_path: Path, output_path: Path,
    holdout_season: int | None = None,
    context_path: Path | None = None,
) -> int:
    inputs = []
    for path in (race_path, pit_path, stint_path):
        with path.open(encoding="utf-8", newline="") as handle:
            inputs.append(list(csv.DictReader(handle)))
    features = build_pit_count_features(
        *inputs, holdout_season=holdout_season, context_rows=_read_optional_csv(context_path)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PIT_COUNT_COLUMNS))
        writer.writeheader()
        writer.writerows(features)
    return len(features)


def build_next_pit_features(
    race_rows: Iterable[dict[str, str]],
    pit_rows: Iterable[dict[str, str]],
    stint_rows: Iterable[dict[str, str]],
    holdout_season: int | None = None,
) -> list[dict[str, object]]:
    """Build recurrent lap-level rows for next-pit classification or survival models."""
    pits_by_race: dict[tuple[int, int, str], list[int]] = defaultdict(list)
    for row in pit_rows:
        pits_by_race[_driver_race_key(row)].append(
            _required_positive_int(row.get("lap_number"), "lap_number")
        )
    stints_by_race: dict[tuple[int, int, str], list[dict[str, object]]] = defaultdict(list)
    for row in stint_rows:
        stints_by_race[_driver_race_key(row)].append({
            "stint_number": _required_positive_int(row.get("stint_number"), "stint_number"),
            "compound": row.get("compound") or None,
            "lap_start": _required_positive_int(row.get("lap_start"), "lap_start"),
            "lap_end": _required_positive_int(row.get("lap_end"), "lap_end"),
            "tyre_age_at_start": _optional_int(row.get("tyre_age_at_start_laps")),
        })
    output: list[dict[str, object]] = []
    for race in sorted(race_rows, key=lambda row: (
        int(row["season"]), int(row["round_number"]), row["driver_id"]
    )):
        key = _driver_race_key(race)
        completed_laps = _optional_int(race.get("laps_completed"))
        if completed_laps is None or completed_laps <= 0:
            continue
        pit_laps = sorted(set(lap for lap in pits_by_race.get(key, []) if lap <= completed_laps))
        stints = sorted(stints_by_race.get(key, []), key=lambda row: int(row["stint_number"]))
        season = int(race["season"])
        for lap in range(1, completed_laps + 1):
            stint = _stint_for_lap(stints, lap)
            if stint is None:
                continue
            previous_pits = [pit for pit in pit_laps if pit < lap]
            future_pits = [pit for pit in pit_laps if pit >= lap]
            next_pit = future_pits[0] if future_pits else None
            base_age = stint["tyre_age_at_start"]
            output.append({
                "season": season,
                "round_number": int(race["round_number"]),
                "session_key": _optional_int(race.get("session_key")),
                "driver_id": race["driver_id"],
                "lap_number": lap,
                "current_stint_number": stint["stint_number"],
                "current_compound": stint["compound"],
                "tyre_age_laps": (
                    int(base_age) + lap - int(stint["lap_start"])
                    if base_age is not None else None
                ),
                "pit_stops_completed": len(previous_pits),
                "laps_since_last_pit": lap - previous_pits[-1] if previous_pits else lap - 1,
                "pit_this_lap": next_pit == lap,
                "next_pit_lap": next_pit,
                "laps_until_next_pit": next_pit - lap if next_pit is not None else None,
                "event_observed": next_pit is not None,
                "dataset_split": "test" if holdout_season is not None and season >= holdout_season else "train",
            })
    return output


def build_next_pit_feature_file(
    race_path: Path, pit_path: Path, stint_path: Path, output_path: Path,
    holdout_season: int | None = None,
) -> int:
    inputs = []
    for path in (race_path, pit_path, stint_path):
        with path.open(encoding="utf-8", newline="") as handle:
            inputs.append(list(csv.DictReader(handle)))
    features = build_next_pit_features(*inputs, holdout_season=holdout_season)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(NEXT_PIT_COLUMNS))
        writer.writeheader()
        writer.writerows(features)
    return len(features)


def _group_races(rows: list[dict[str, str]]) -> Iterable[list[dict[str, str]]]:
    current_key: tuple[int, int] | None = None
    group: list[dict[str, str]] = []
    for row in rows:
        key = (int(row["season"]), int(row["round_number"]))
        if current_key is not None and key != current_key:
            yield group
            group = []
        current_key = key
        group.append(row)
    if group:
        yield group


def _history_features(
    prefix: str,
    history: list[dict[str, object]],
    recent_grid: bool = True,
    positions_gained: bool = True,
) -> dict[str, object]:
    recent = history[-5:]
    values: dict[str, object] = {
        f"{prefix}_prior_starts": len(history),
        f"{prefix}_prior_avg_finish": _average(history, "finish"),
    }
    if recent_grid:
        values[f"{prefix}_prior_avg_grid"] = _average(history, "grid")
    values[f"{prefix}_prior_dnf_rate"] = _average(history, "dnf")
    if positions_gained:
        values[f"{prefix}_prior_avg_positions_gained"] = _average(history, "positions_gained")
    values[f"{prefix}_recent5_avg_finish"] = _average(recent, "finish")
    if recent_grid:
        values[f"{prefix}_recent5_avg_grid"] = _average(recent, "grid")
    return values


def _pit_history_features(prefix: str, history: list[dict[str, object]]) -> dict[str, object]:
    recent = history[-5:]
    if prefix == "driver":
        return {
            "driver_prior_races": len(history),
            "driver_prior_avg_pit_stops": _average(history, "pit_stops"),
            "driver_recent5_avg_pit_stops": _average(recent, "pit_stops"),
            "driver_prior_zero_stop_rate": _rate(history, lambda value: value == 0),
            "driver_prior_two_plus_stop_rate": _rate(history, lambda value: value >= 2),
            "driver_prior_avg_stints": _average(history, "stints"),
        }
    return {
        "constructor_prior_driver_races": len(history),
        "constructor_prior_avg_pit_stops": _average(history, "pit_stops"),
        "constructor_recent5_avg_pit_stops": _average(recent, "pit_stops"),
    }


def _stint_for_lap(stints: list[dict[str, object]], lap: int) -> dict[str, object] | None:
    return next((stint for stint in stints
                 if int(stint["lap_start"]) <= lap <= int(stint["lap_end"])), None)


def _counts_by_driver_race(rows: Iterable[dict[str, str]]) -> dict[tuple[int, int, str], int]:
    counts: dict[tuple[int, int, str], int] = defaultdict(int)
    for row in rows:
        counts[_driver_race_key(row)] += 1
    return dict(counts)


def _driver_race_key(row: dict[str, str]) -> tuple[int, int, str]:
    return int(row["season"]), int(row["round_number"]), row["driver_id"]


def _rate(history: list[dict[str, object]], predicate: object) -> float | None:
    if not history:
        return None
    matches = sum(bool(predicate(int(row["pit_stops"]))) for row in history)  # type: ignore[operator]
    return round(matches / len(history), 6)


def _history_record(row: dict[str, str], finish: int) -> dict[str, object]:
    grid = _optional_int(row.get("grid_position"))
    valid_grid = grid if grid is not None and grid > 0 else None
    return {
        "finish": finish,
        "grid": valid_grid,
        "positions_gained": valid_grid - finish if valid_grid is not None else None,
        "dnf": 0.0 if _is_classified_finish(row.get("status", "")) else 1.0,
    }


def _is_classified_finish(status: str) -> bool:
    normalized = status.strip().lower()
    return normalized == "finished" or normalized.startswith("+")


def _average(rows: Iterable[dict[str, object]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return round(fmean(values), 6) if values else None


def _optional_int(value: object) -> int | None:
    return int(str(value)) if value not in (None, "") else None


def _required_positive_int(value: object, field: str) -> int:
    result = _optional_int(value)
    if result is None or result < 1:
        raise ValueError(f"{field} must be a positive integer")
    return result


def _read_optional_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _context_by_race(rows: Iterable[dict[str, str]]) -> dict[tuple[int, int], dict[str, str]]:
    return {(int(row["season"]), int(row["round_number"])): row for row in rows}


def _context_features(
    context: dict[str, str] | None,
    histories: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    circuit_key = context.get("circuit_key") if context else None
    history = histories.get(str(circuit_key), []) if circuit_key not in (None, "") else []
    return {
        "circuit_key": _optional_int(circuit_key),
        "start_air_temperature_c": _optional_float(context.get("start_air_temperature_c") if context else None),
        "start_track_temperature_c": _optional_float(context.get("start_track_temperature_c") if context else None),
        "start_humidity_pct": _optional_float(context.get("start_humidity_pct") if context else None),
        "start_pressure_mbar": _optional_float(context.get("start_pressure_mbar") if context else None),
        "start_rainfall": _optional_bool(context.get("start_rainfall") if context else None),
        "start_wind_speed_ms": _optional_float(context.get("start_wind_speed_ms") if context else None),
        "circuit_prior_races": len(history),
        "circuit_prior_avg_winner_laps": _average(history, "winner_laps"),
        "circuit_prior_avg_safety_cars": _average(history, "safety_cars"),
        "circuit_prior_avg_virtual_safety_cars": _average(history, "virtual_safety_cars"),
        "circuit_prior_rain_rate": _average(history, "rain"),
    }


def _update_circuit_history(
    context: dict[str, str] | None,
    histories: dict[str, list[dict[str, object]]],
) -> None:
    if not context or context.get("circuit_key") in (None, ""):
        return
    histories[str(context["circuit_key"])].append({
        "winner_laps": _optional_float(context.get("winner_laps_completed")),
        "safety_cars": _optional_float(context.get("safety_car_deployments")),
        "virtual_safety_cars": _optional_float(context.get("virtual_safety_car_deployments")),
        "rain": float(_optional_bool(context.get("start_rainfall")) or False),
    })


def _optional_float(value: object) -> float | None:
    return float(str(value)) if value not in (None, "") else None


def _optional_bool(value: object) -> bool | None:
    if value in (None, ""):
        return None
    return str(value).strip().lower() in {"true", "1", "yes"}
