from f1_strategy_data.features import PRE_RACE_COLUMNS, build_pre_race_finishing_features


def _row(season, round_number, driver, constructor, grid, finish, status="Finished"):
    return {
        "season": str(season), "round_number": str(round_number), "session_key": str(round_number),
        "driver_id": driver, "constructor_id": constructor, "grid_position": str(grid),
        "classified_position": str(finish), "status": status,
    }


def test_features_use_only_prior_races_and_not_current_teammate_result():
    rows = [
        _row(2025, 1, "a", "team", 1, 2),
        _row(2025, 1, "b", "team", 5, 8, "Accident"),
        _row(2025, 2, "a", "team", 2, 1),
        _row(2025, 2, "b", "team", 6, 5),
    ]
    result = build_pre_race_finishing_features(reversed(rows), holdout_season=2026)
    first_race = [row for row in result if row["round_number"] == 1]
    second_race = [row for row in result if row["round_number"] == 2]
    assert {row["constructor_prior_starts"] for row in first_race} == {0}
    assert {row["constructor_prior_starts"] for row in second_race} == {2}
    assert {row["constructor_prior_avg_finish"] for row in second_race} == {5.0}
    a_second = next(row for row in second_race if row["driver_id"] == "a")
    assert a_second["driver_prior_avg_finish"] == 2.0
    assert a_second["driver_prior_avg_positions_gained"] == -1.0


def test_holdout_is_chronological_and_cold_start_is_null():
    result = build_pre_race_finishing_features([
        _row(2025, 1, "a", "x", 1, 1),
        _row(2026, 1, "a", "x", 2, 3),
    ], holdout_season=2026)
    assert result[0]["dataset_split"] == "train"
    assert result[1]["dataset_split"] == "test"
    assert result[0]["driver_prior_starts"] == 0
    assert result[0]["driver_prior_avg_finish"] is None
    assert tuple(result[0]) == PRE_RACE_COLUMNS


def test_pit_lane_grid_is_not_used_for_positions_gained_history():
    result = build_pre_race_finishing_features([
        _row(2025, 1, "a", "x", 0, 10),
        _row(2025, 2, "a", "x", 3, 2),
    ])
    assert result[1]["driver_prior_avg_grid"] is None
    assert result[1]["driver_prior_avg_positions_gained"] is None


def test_race_context_uses_current_weather_but_only_prior_circuit_outcomes():
    contexts = [
        {"season": "2025", "round_number": "1", "circuit_key": "7", "start_air_temperature_c": "20", "start_rainfall": "true", "winner_laps_completed": "50", "safety_car_deployments": "1", "virtual_safety_car_deployments": "0"},
        {"season": "2025", "round_number": "2", "circuit_key": "7", "start_air_temperature_c": "24", "start_rainfall": "false", "winner_laps_completed": "52", "safety_car_deployments": "0", "virtual_safety_car_deployments": "1"},
    ]
    result = build_pre_race_finishing_features([
        _row(2025, 1, "a", "x", 1, 1),
        _row(2025, 2, "a", "x", 2, 2),
    ], context_rows=contexts)

    assert result[0]["start_air_temperature_c"] == 20.0
    assert result[0]["circuit_prior_races"] == 0
    assert result[1]["start_air_temperature_c"] == 24.0
    assert result[1]["circuit_prior_avg_winner_laps"] == 50.0
    assert result[1]["circuit_prior_avg_safety_cars"] == 1.0
    assert result[1]["circuit_prior_rain_rate"] == 1.0
