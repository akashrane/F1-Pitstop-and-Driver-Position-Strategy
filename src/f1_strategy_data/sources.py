"""Source clients with explicit provenance metadata.

The clients intentionally use only the Python standard library. Raw responses
should be retained by callers so future source corrections can be replayed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "f1-strategy-weather-data/0.1 (+https://github.com/akashrane/F1-Pitstop-and-Driver-Position-Strategy)"


def _get_json(url: str, timeout: int = 60) -> tuple[Any, dict[str, str]]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    provenance = {
        "source_url": url,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
    }
    return payload, provenance


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
    allowed = {"weather", "stints", "pit", "laps", "sessions", "meetings", "drivers", "starting_grid", "session_result"}
    if endpoint not in allowed:
        raise ValueError(f"Unsupported OpenF1 endpoint: {endpoint}")
    query = urlencode({key: value for key, value in filters.items() if value is not None})
    url = f"https://api.openf1.org/v1/{endpoint}"
    if query:
        url = f"{url}?{query}"
    return _get_json(url)