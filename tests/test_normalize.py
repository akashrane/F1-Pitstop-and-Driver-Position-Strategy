from f1_strategy_data.normalize import (
    driver_number_map,
    normalize_pit_events,
    normalize_jolpica_pit_events,
    normalize_stints,
    normalize_weather,
)


RACE = {
    "season": "2026",
    "round": "11",
    "Results": [{
        "number": "1",
        "position": "1",
        "grid": "2",
        "laps": "70",
        "status": "Finished",
        "Driver": {"driverId": "norris", "permanentNumber": "4", "givenName": "Lando", "familyName": "Norris"},
        "Constructor": {"constructorId": "mclaren"},
    }],
}
PROVENANCE = {"source_url": "https://example.test/source", "retrieved_at_utc": "2026-07-27T00:00:00+00:00"}


def test_driver_number_map_uses_event_number_not_permanent_number():
    assert driver_number_map(RACE) == {1: "norris"}


def test_openf1_tables_use_canonical_units_and_ids():
    identifiers = {4: "norris"}
    stints = normalize_stints([{"session_key": 1, "driver_number": 4, "stint_number": 1, "compound": "MEDIUM", "lap_start": 1, "lap_end": 20, "tyre_age_at_start": 0}], identifiers, 2026, 11, **PROVENANCE)
    pits = normalize_pit_events([{"session_key": 1, "driver_number": 4, "date": "2026-07-26T13:30:00+00:00", "lap_number": 20, "pit_duration": 21.2, "stop_duration": 2.3}], identifiers, {"norris": 70}, 2026, 11, **PROVENANCE)
    weather = normalize_weather([{"session_key": 1, "date": "2026-07-26T13:01:00+00:00", "air_temperature": 24.0, "track_temperature": 40.0, "humidity": 55, "pressure": 1008.0, "rainfall": False, "wind_direction": 180, "wind_speed": 3.2}], 2026, 11, **PROVENANCE)
    assert stints[0]["driver_id"] == "norris"
    assert pits[0]["pit_duration_s"] == 21.2
    assert weather[0]["wind_speed_ms"] == 3.2


def test_jolpica_pit_event_is_kept_when_openf1_event_is_missing():
    payload = {"MRData": {"RaceTable": {"Races": [{"PitStops": [
        {"driverId": "norris", "lap": "56", "stop": "3", "duration": "21.878"}
    ]}]}}}
    rows = normalize_jolpica_pit_events(payload, [], {1: "norris"}, {"norris": 70}, 2026, 11, 1, **PROVENANCE)
    assert len(rows) == 1
    assert rows[0]["pit_duration_s"] == 21.878
    assert rows[0]["validation_status"] == "warning"