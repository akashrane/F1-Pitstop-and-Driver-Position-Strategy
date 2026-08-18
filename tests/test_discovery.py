from datetime import UTC, datetime

import f1_strategy_data.discovery as discovery


def test_cancelled_and_future_sessions_are_not_matched(monkeypatch):
    monkeypatch.setattr(discovery, "jolpica_season_results", lambda season: ({"MRData": {"RaceTable": {"Races": [
        {"round": "1", "raceName": "Completed", "date": "2026-03-08"},
        {"round": "2", "raceName": "Cancelled", "date": "2026-04-12"},
    ]}}}, {}))
    monkeypatch.setattr(discovery, "openf1", lambda endpoint, **filters: ([
        {"date_start": "2026-03-08T04:00:00+00:00", "date_end": "2026-03-08T06:00:00+00:00", "session_key": 1, "is_cancelled": False},
        {"date_start": "2026-04-12T15:00:00+00:00", "date_end": "2026-04-12T17:00:00+00:00", "session_key": 2, "is_cancelled": True},
    ], {}))
    refs = discovery.discover_completed_races(2026, datetime(2026, 8, 1, tzinfo=UTC))
    assert refs[0].session_key == 1
    assert refs[1].session_key is None


def test_local_race_date_can_match_next_utc_day(monkeypatch):
    monkeypatch.setattr(discovery, "jolpica_season_results", lambda season: ({
        "MRData": {"RaceTable": {"Races": [{
            "round": "22", "raceName": "Las Vegas Grand Prix", "date": "2024-11-23",
        }]}}
    }, {}))
    monkeypatch.setattr(discovery, "openf1", lambda endpoint, **filters: ([{
        "date_start": "2024-11-24T06:00:00+00:00",
        "date_end": "2024-11-24T08:00:00+00:00",
        "session_key": 9644,
        "is_cancelled": False,
    }], {}))

    refs = discovery.discover_completed_races(2024, datetime(2026, 1, 1, tzinfo=UTC))

    assert refs[0].session_key == 9644

