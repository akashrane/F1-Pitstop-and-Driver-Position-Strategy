from f1_strategy_data.features import PIT_COUNT_COLUMNS, build_pit_count_features


def _race(round_number, driver, constructor="team"):
    return {"season": "2025", "round_number": str(round_number), "session_key": str(round_number),
            "driver_id": driver, "constructor_id": constructor, "grid_position": "1"}


def _events(round_number, driver, count):
    return [{"season": "2025", "round_number": str(round_number), "driver_id": driver} for _ in range(count)]


def _stints(round_number, driver, count):
    return [{"season": "2025", "round_number": str(round_number), "driver_id": driver} for _ in range(count)]


def test_pit_count_target_and_history_are_leakage_safe():
    races = [_race(1, "a"), _race(1, "b"), _race(2, "a"), _race(2, "b")]
    pits = _events(1, "a", 1) + _events(1, "b", 2) + _events(2, "a", 2)
    stints = _stints(1, "a", 2) + _stints(1, "b", 3) + _stints(2, "a", 3) + _stints(2, "b", 1)
    result = build_pit_count_features(races, pits, stints)
    first = [row for row in result if row["round_number"] == 1]
    second = [row for row in result if row["round_number"] == 2]
    assert {row["constructor_prior_driver_races"] for row in first} == {0}
    assert {row["constructor_prior_avg_pit_stops"] for row in second} == {1.5}
    a_second = next(row for row in second if row["driver_id"] == "a")
    b_second = next(row for row in second if row["driver_id"] == "b")
    assert a_second["driver_prior_avg_pit_stops"] == 1.0
    assert a_second["driver_prior_avg_stints"] == 2.0
    assert a_second["pit_stop_count"] == 2
    assert b_second["pit_stop_count"] == 0
    assert tuple(a_second) == PIT_COUNT_COLUMNS


def test_pit_count_rates_and_holdout():
    races = [_race(1, "a"), _race(2, "a"), {**_race(1, "a"), "season": "2026"}]
    pits = _events(2, "a", 2)
    result = build_pit_count_features(races, pits, [], holdout_season=2026)
    final = result[-1]
    assert final["driver_prior_zero_stop_rate"] == 0.5
    assert final["driver_prior_two_plus_stop_rate"] == 0.5
    assert final["dataset_split"] == "test"
