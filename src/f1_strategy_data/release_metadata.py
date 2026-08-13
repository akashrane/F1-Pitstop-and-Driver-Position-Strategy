"""Human-readable documentation for canonical release tables and columns."""

TABLE_DESCRIPTIONS = {
    "race_drivers": "One row per driver and race, including grid position, official classification, and result status.",
    "stints": "One row per continuous tyre stint, including compound, lap boundaries, and tyre age.",
    "pit_events": "One row per observed pit-lane visit, including stop order, lap, and available durations.",
    "weather_observations": "Timestamped trackside weather observations recorded during race sessions.",
}

COLUMN_DESCRIPTIONS = {
    "season": "Formula 1 World Championship season year.",
    "round_number": "Official championship round number within the season.",
    "session_key": "OpenF1 identifier for the race session; null where that source has no session identifier.",
    "driver_id": "Stable lowercase driver identifier used across canonical tables.",
    "driver_name": "Driver's displayed full name.",
    "constructor_id": "Stable lowercase constructor or team identifier.",
    "grid_position": "Official starting-grid position; 0 denotes a pit-lane start where supplied by the source.",
    "classified_position": "Official classified finishing position and the finishing-position prediction target.",
    "laps_completed": "Number of race laps officially completed by the driver.",
    "status": "Official result status, such as Finished, Lapped, Accident, or Disqualified.",
    "stint_number": "Sequential tyre-stint number for a driver in the race.",
    "compound": "Tyre compound reported by the timing source.",
    "lap_start": "First race lap of the continuous tyre stint.",
    "lap_end": "Last race lap of the continuous tyre stint.",
    "tyre_age_at_start_laps": "Tyre age in completed laps when the stint began.",
    "stop_number": "Sequential pit-stop number for a driver in the race.",
    "lap_number": "Race lap on which the pit-lane visit occurred.",
    "pit_duration_s": "Elapsed pit-lane duration in seconds where available.",
    "stop_duration_s": "Stationary service duration in seconds where available.",
    "driver_laps_completed": "Driver's official total completed laps, retained for post-race validation.",
    "observed_at_utc": "UTC timestamp of the trackside weather observation.",
    "air_temperature_c": "Trackside air temperature in degrees Celsius.",
    "track_temperature_c": "Measured track-surface temperature in degrees Celsius.",
    "humidity_pct": "Relative humidity as a percentage.",
    "pressure_mbar": "Atmospheric pressure in millibars.",
    "rainfall": "Whether rainfall was detected at the observation time.",
    "wind_direction_deg": "Wind direction in degrees from 0 through 359.",
    "wind_speed_ms": "Wind speed in metres per second.",
    "weather_source": "Timing-data provider that supplied the trackside weather measurement.",
    "source": "Primary source used to create the canonical record.",
    "source_url": "URL of the upstream source request used for the record.",
    "retrieved_at_utc": "UTC timestamp at which the source response was retrieved.",
    "validation_status": "Data-quality state: verified, warning, quarantined, or unavailable.",
}

DATASET_TITLE = "Formula 1 Pit Stop Dataset"
DATASET_SUBTITLE = "Validated F1 pit stops, tyre stints, race results and trackside weather"
DATASET_DESCRIPTION = (
    "Accuracy-first Formula 1 tables for pit-stop and finishing-position modelling. "
    "The latest release contains only races that passed automated validation; warning "
    "and quarantined races remain documented in validation_manifest.json. Source URLs, "
    "retrieval timestamps, feature timing, nullability, and units are included for auditability."
)
DATASET_KEYWORDS = [
    "Tabular",
    "Sports",
    "Auto Racing",
    "Time Series Analysis",
]
