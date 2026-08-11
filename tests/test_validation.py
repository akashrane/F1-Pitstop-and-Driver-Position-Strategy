from f1_strategy_data.validation import duplicate_key_issues, pit_stop_issues, weather_issues


def test_duplicate_primary_key_is_reported():
    rows = [{"season": 2026, "round": 1}, {"season": 2026, "round": 1}]
    issues = duplicate_key_issues(rows, ("season", "round"))
    assert [issue.code for issue in issues] == ["duplicate_primary_key"]


def test_estimated_track_temperature_is_rejected():
    rows = [{"weather_source": "open_meteo", "track_temperature_c": 30}]
    assert "estimated_track_temperature" in [issue.code for issue in weather_issues(rows)]


def test_timestamp_and_ranges_are_validated():
    rows = [{"weather_source": "openf1", "observed_at_utc": "2026-03-08T05:02:00Z", "humidity_pct": 101, "wind_speed_ms": -1}]
    codes = {issue.code for issue in weather_issues(rows)}
    assert codes == {"invalid_humidity", "invalid_wind_speed"}


def test_pit_lap_cannot_exceed_completed_laps():
    rows = [{"lap_number": 20, "driver_laps_completed": 12}]
    assert [issue.code for issue in pit_stop_issues(rows)] == ["pit_after_retirement"]
