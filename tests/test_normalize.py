from f1_strategy_data.normalize import (
    count_shared_stint_boundaries,
    driver_number_map,
    normalize_pit_events,
    normalize_race_context,
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


def test_shared_stint_boundary_is_assigned_to_previous_stint_only():
    source_rows = [
        {"session_key": 1, "driver_number": 4, "stint_number": 1, "compound": "MEDIUM", "lap_start": 1, "lap_end": 20, "tyre_age_at_start": 0},
        {"session_key": 1, "driver_number": 4, "stint_number": 2, "compound": "HARD", "lap_start": 20, "lap_end": 40, "tyre_age_at_start": 0},
    ]
    rows = normalize_stints(source_rows, {4: "norris"}, 2026, 11, **PROVENANCE)

    assert [(row["lap_start"], row["lap_end"]) for row in rows] == [(1, 20), (21, 40)]
    assert count_shared_stint_boundaries(source_rows, {4: "norris"}) == 1


def test_jolpica_pit_event_is_kept_when_openf1_event_is_missing():
    payload = {"MRData": {"RaceTable": {"Races": [{"PitStops": [
        {"driverId": "norris", "lap": "56", "stop": "3", "duration": "21.878"}
    ]}]}}}
    rows = normalize_jolpica_pit_events(payload, [], {1: "norris"}, {"norris": 70}, 2026, 11, 1, **PROVENANCE)
    assert len(rows) == 1
    assert rows[0]["pit_duration_s"] == 21.878
    assert rows[0]["validation_status"] == "warning"


def test_race_context_uses_nearest_start_weather_and_counts_safety_cars():
    sessions = [{
        "session_key": 1, "meeting_key": 2, "circuit_key": 3,
        "circuit_short_name": "Test Circuit", "country_code": "TST",
        "country_name": "Testland", "location": "Test City",
        "date_start": "2026-07-26T13:00:00+00:00",
    }]
    weather = [
        {"date": "2026-07-26T12:50:00+00:00", "air_temperature": 20},
        {"date": "2026-07-26T13:01:00+00:00", "air_temperature": 24, "rainfall": True},
    ]
    controls = [
        {"message": "SAFETY CAR DEPLOYED"},
        {"message": "VIRTUAL SAFETY CAR DEPLOYED"},
        {"message": "SAFETY CAR IN THIS LAP"},
    ]
    row = normalize_race_context(
        sessions, controls, weather, RACE, 1, **PROVENANCE
    )[0]

    assert row["circuit_key"] == 3
    assert row["start_air_temperature_c"] == 24.0
    assert row["start_rainfall"] is True
    assert row["safety_car_deployments"] == 1
    assert row["virtual_safety_car_deployments"] == 1
    assert row["winner_laps_completed"] == 70
