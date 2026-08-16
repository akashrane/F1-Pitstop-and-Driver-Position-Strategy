"""Source clients with explicit provenance metadata.

The clients intentionally use only the Python standard library. Raw responses
should be retained by callers so future source corrections can be replayed.
"""

from __future__ import annotations

import json
import socket
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


USER_AGENT = "f1-strategy-weather-data/0.1 (+https://github.com/akashrane/F1-Pitstop-and-Driver-Position-Strategy)"
_LAST_REQUEST_AT: dict[str, float] = {}
_MIN_INTERVAL_SECONDS = {"api.openf1.org": 2.1, "api.jolpi.ca": 0.25}


def _get_json(url: str, timeout: int = 60, attempts: int = 6) -> tuple[Any, dict[str, str]]:
    for attempt in range(attempts):
        _throttle(url)
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            break
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == attempts - 1:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else min(2 ** attempt, 30)
            time.sleep(delay)
        except (URLError, TimeoutError, socket.timeout):
            if attempt == attempts - 1:
                raise
            time.sleep(min(2 ** attempt, 30))
    provenance = {
        "source_url": url,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
    }
    return payload, provenance


def _throttle(url: str) -> None:
    """Stay below known free-tier request rates before a server returns 429."""
    host = urlparse(url).hostname or ""
    interval = _MIN_INTERVAL_SECONDS.get(host, 0.25)
    now = time.monotonic()
    wait = interval - (now - _LAST_REQUEST_AT.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT[host] = time.monotonic()


def jolpica_results(season: int, round_number: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch race classification data from the maintained Ergast successor."""
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_number}/results.json?limit=100"
    return _get_json(url)


def jolpica_pit_stops(season: int, round_number: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch available pit-stop records.

    An empty response means unavailable/unknown unless independently verified;
    it must never be converted automatically to zero stops.
    """
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_number}/pitstops.json?limit=2000"
    return _get_json(url)


def openf1(endpoint: str, **filters: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Fetch session-timestamped OpenF1 data such as weather, stints, or pits."""
    allowed = {"weather", "stints", "pit", "laps", "sessions", "meetings", "drivers", "starting_grid", "session_result", "race_control"}
    if endpoint not in allowed:
        raise ValueError(f"Unsupported OpenF1 endpoint: {endpoint}")
    query = urlencode({key: value for key, value in filters.items() if value is not None})
    url = f"https://api.openf1.org/v1/{endpoint}"
    if query:
        url = f"{url}?{query}"
    return _get_json(url)


def jolpica_season_results(season: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch one result per completed race for reliable round discovery.

    The unfiltered results endpoint paginates individual driver results, so a
    nominally large limit can still stop part-way through a race. Position 1
    gives us exactly one row per completed Grand Prix; the per-round builder
    subsequently fetches the complete classification.
    """
    url = f"https://api.jolpi.ca/ergast/f1/{season}/results/1.json?limit=100"
    return _get_json(url)


def jolpica_season_full_results(season: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Fetch every classified driver result in a season for historical backfill."""
    base = f"https://api.jolpi.ca/ergast/f1/{season}/results.json"
    return _get_paginated_races(base, "Results")


def _get_paginated_races(base_url: str, row_key: str) -> tuple[dict[str, Any], dict[str, str]]:
    """Collect Jolpica pages while preserving its race-grouped response shape."""
    offset = 0
    races_by_round: dict[int, dict[str, Any]] = {}
    provenance: dict[str, str] | None = None
    total = 0
    while offset == 0 or offset < total:
        payload, page_provenance = _get_json(f"{base_url}?limit=100&offset={offset}")
        provenance = provenance or page_provenance
        mrdata = payload.get("MRData", {})
        total = int(mrdata.get("total", 0))
        page_races = mrdata.get("RaceTable", {}).get("Races", [])
        page_count = 0
        for race in page_races:
            round_number = int(race["round"])
            incoming = list(race.get(row_key, []))
            page_count += len(incoming)
            if round_number not in races_by_round:
                races_by_round[round_number] = {**race, row_key: incoming}
            else:
                races_by_round[round_number][row_key].extend(incoming)
        if page_count == 0:
            break
        offset += page_count
    combined = {
        "MRData": {
            "limit": str(offset), "offset": "0", "total": str(total),
            "RaceTable": {"Races": [races_by_round[key] for key in sorted(races_by_round)]},
        }
    }
    return combined, provenance or {"source_url": base_url, "retrieved_at_utc": datetime.now(UTC).isoformat()}
