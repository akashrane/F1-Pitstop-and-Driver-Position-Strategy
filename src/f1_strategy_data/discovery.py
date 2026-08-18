"""Discover completed races and map Jolpica rounds to OpenF1 sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .sources import jolpica_season_results, openf1


@dataclass(frozen=True)
class RaceRef:
    season: int
    round_number: int
    race_name: str
    race_date: str
    session_key: int | None
    detailed_source_status: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def discover_completed_races(season: int, as_of: datetime | None = None) -> list[RaceRef]:
    as_of = as_of or datetime.now(UTC)
    results_payload, _ = jolpica_season_results(season)
    races = results_payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    sessions: list[dict[str, Any]] = []
    if season >= 2023:
        try:
            sessions, _ = openf1("sessions", year=season, session_name="Race")
        except Exception:
            sessions = []
    completed_sessions = [
        row for row in sessions
        if not row.get("is_cancelled", False) and _parse_time(row["date_end"]) <= as_of
    ]
    refs: list[RaceRef] = []
    for race in races:
        race_date = race["date"]
        session = _match_session_date(race_date, completed_sessions)
        refs.append(RaceRef(
            season=season,
            round_number=int(race["round"]),
            race_name=race["raceName"],
            race_date=race_date,
            session_key=int(session["session_key"]) if session else None,
            detailed_source_status="available" if session else "unavailable",
        ))
    return refs


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _match_session_date(
    local_race_date: str, sessions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match local calendar dates while allowing a race to cross midnight UTC."""
    race_day = datetime.fromisoformat(local_race_date).date()
    exact = [row for row in sessions if _parse_time(row["date_start"]).date() == race_day]
    if len(exact) == 1:
        return exact[0]
    adjacent = [
        row for row in sessions
        if abs((_parse_time(row["date_start"]).date() - race_day).days) == 1
    ]
    return adjacent[0] if not exact and len(adjacent) == 1 else None

