"""Cross-table and field-level validation for canonical datasets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    row_number: int | None = None


def duplicate_key_issues(rows: Iterable[Mapping[str, object]], keys: tuple[str, ...]) -> list[ValidationIssue]:
    values = [tuple(row.get(key) for key in keys) for row in rows]
    counts = Counter(values)
    return [
        ValidationIssue("error", "duplicate_primary_key", f"Key {key!r} occurs {count} times")
        for key, count in counts.items()
        if count > 1
    ]


def weather_issues(rows: Iterable[Mapping[str, object]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, row in enumerate(rows, start=2):
        source = str(row.get("weather_source", ""))
        track_temp = _number(row.get("track_temperature_c"))
        humidity = _number(row.get("humidity_pct"))
        wind_speed = _number(row.get("wind_speed_ms"))
        timestamp = row.get("observed_at_utc")

        if track_temp is not None and source in {"open_meteo", "open-meteo", "estimated"}:
            issues.append(ValidationIssue("error", "estimated_track_temperature", "Track temperature must come from trackside timing data", index))
        if humidity is not None and not 0 <= humidity <= 100:
            issues.append(ValidationIssue("error", "invalid_humidity", f"Humidity is {humidity}", index))
        if wind_speed is not None and wind_speed < 0:
            issues.append(ValidationIssue("error", "invalid_wind_speed", f"Wind speed is {wind_speed}", index))
        if timestamp and not _is_utc_timestamp(str(timestamp)):
            issues.append(ValidationIssue("error", "invalid_weather_timestamp", "Weather timestamp must be ISO-8601 UTC", index))
    return issues


def pit_stop_issues(rows: Iterable[Mapping[str, object]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, row in enumerate(rows, start=2):
        lap = _integer(row.get("lap_number"))
        completed = _integer(row.get("driver_laps_completed"))
        if lap is not None and lap < 1:
            issues.append(ValidationIssue("error", "invalid_pit_lap", f"Pit lap is {lap}", index))
        if lap is not None and completed is not None and lap > completed:
            issues.append(ValidationIssue("error", "pit_after_retirement", f"Pit lap {lap} exceeds {completed} completed laps", index))
    return issues


def stint_issues(rows: Iterable[Mapping[str, object]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_driver: dict[tuple[object, object], list[tuple[int, int, int]]] = {}
    for index, row in enumerate(rows, start=2):
        start = _integer(row.get("lap_start"))
        end = _integer(row.get("lap_end"))
        if start is None or end is None:
            issues.append(ValidationIssue("error", "missing_stint_boundary", "Stint boundaries are required", index))
            continue
        if end < start:
            issues.append(ValidationIssue("error", "invalid_stint_boundary", f"Stint ends on lap {end} before lap {start}", index))
        key = (row.get("session_key"), row.get("driver_id"))
        by_driver.setdefault(key, []).append((start, end, index))
    for key, spans in by_driver.items():
        previous_end: int | None = None
        for start, end, index in sorted(spans):
            if previous_end is not None and start <= previous_end:
                issues.append(ValidationIssue("error", "overlapping_stints", f"Overlapping stint for {key!r}", index))
            previous_end = max(previous_end or end, end)
    return issues


def _number(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: object) -> int | None:
    number = _number(value)
    return int(number) if number is not None and number.is_integer() else None


def _is_utc_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0