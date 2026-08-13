from f1_strategy_data.features import NEXT_PIT_COLUMNS, build_next_pit_features


def test_next_pit_features_separate_live_state_from_targets():
    races = [{"season": "2025", "round_number": "1", "session_key": "11", "driver_id": "a", "laps_completed": "6"}]
    pits = [
        {"season": "2025", "round_number": "1", "driver_id": "a", "lap_number": "3"},
        {"season": "2025", "round_number": "1", "driver_id": "a", "lap_number": "5"},
    ]
    stints = [
        {"season": "2025", "round_number": "1", "driver_id": "a", "stint_number": "1", "compound": "MEDIUM", "lap_start": "1", "lap_end": "3", "tyre_age_at_start_laps": "0"},
        {"season": "2025", "round_number": "1", "driver_id": "a", "stint_number": "2", "compound": "HARD", "lap_start": "4", "lap_end": "5", "tyre_age_at_start_laps": "1"},
        {"season": "2025", "round_number": "1", "driver_id": "a", "stint_number": "3", "compound": "SOFT", "lap_start": "6", "lap_end": "6", "tyre_age_at_start_laps": "0"},
    ]
    result = build_next_pit_features(races, pits, stints)
    assert len(result) == 6
    lap3 = result[2]
    assert lap3["pit_stops_completed"] == 0
    assert lap3["pit_this_lap"] is True
    assert lap3["next_pit_lap"] == 3
    assert lap3["laps_until_next_pit"] == 0
    lap4 = result[3]
    assert lap4["pit_stops_completed"] == 1
    assert lap4["laps_since_last_pit"] == 1
    assert lap4["current_compound"] == "HARD"
    assert lap4["tyre_age_laps"] == 1
    lap6 = result[5]
    assert lap6["event_observed"] is False
    assert lap6["next_pit_lap"] is None
    assert tuple(lap6) == NEXT_PIT_COLUMNS


def test_next_pit_rows_skip_uncovered_laps_and_apply_holdout():
    races = [
        {"season": "2026", "round_number": "1", "session_key": "11", "driver_id": "a", "laps_completed": "3"},
        {"season": "2026", "round_number": "1", "session_key": "11", "driver_id": "dns", "laps_completed": "0"},
    ]
    stints = [{"season": "2026", "round_number": "1", "driver_id": "a", "stint_number": "1", "compound": "HARD", "lap_start": "2", "lap_end": "3", "tyre_age_at_start_laps": "0"}]
    result = build_next_pit_features(races, [], stints, holdout_season=2026)
    assert [row["lap_number"] for row in result] == [2, 3]
    assert {row["dataset_split"] for row in result} == {"test"}
