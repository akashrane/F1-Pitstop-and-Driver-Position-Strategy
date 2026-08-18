"""Human-readable documentation for canonical release tables and columns."""

TABLE_DESCRIPTIONS = {
    "race_context": "One row per race with circuit identity, race-start weather, race distance, and safety-car outcomes.",
    "race_drivers": "One row per driver and race, including grid position, official classification, and result status.",
    "stints": "One row per continuous tyre stint, including compound, lap boundaries, and tyre age.",
    "pit_events": "One row per observed pit-lane visit, including stop order, lap, and available durations.",
    "weather_observations": "Timestamped trackside weather observations recorded during race sessions.",
    "provenance": "Compact source and retrieval metadata removed from the analysis-ready CSV files.",
    "coverage": "Per-table season coverage and row counts; unavailable historical telemetry is not represented as zero.",
    "data_quality_issues": "Per-race validation findings, source limitations, normalization decisions, and publication treatment.",
}

PUBLIC_EXCLUDED_COLUMNS = {"source", "source_url", "retrieved_at_utc", "validation_status"}

PROVENANCE_COLUMNS = (
    "season", "round_number", "table", "source", "source_url",
    "retrieved_at_utc", "validation_status",
)

COLUMN_DESCRIPTIONS = {
    "season": "Formula 1 World Championship season year.",
    "round_number": "Official championship round number within the season.",
    "session_key": "OpenF1 identifier for the race session; null where that source has no session identifier.",
    "meeting_key": "OpenF1 identifier for the Grand Prix meeting.",
    "circuit_key": "OpenF1 identifier for the circuit configuration.",
    "circuit_id": "Stable Jolpica circuit identifier available across historical seasons.",
    "circuit_short_name": "Short name of the circuit used by OpenF1.",
    "country_code": "Three-letter country code supplied for the meeting.",
    "country_name": "Country hosting the race meeting.",
    "location": "City or locality associated with the circuit.",
    "session_start_utc": "Scheduled UTC start timestamp of the race session.",
    "start_weather_observed_at_utc": "Timestamp of the trackside observation nearest the scheduled start, within 15 minutes.",
    "start_air_temperature_c": "Trackside air temperature nearest the scheduled race start.",
    "start_track_temperature_c": "Measured track temperature nearest the scheduled race start.",
    "start_humidity_pct": "Relative humidity nearest the scheduled race start.",
    "start_pressure_mbar": "Atmospheric pressure nearest the scheduled race start.",
    "start_rainfall": "Whether rainfall was detected nearest the scheduled race start.",
    "start_wind_speed_ms": "Wind speed nearest the scheduled race start.",
    "winner_laps_completed": "Official laps completed by the race winner; a post-race outcome.",
    "safety_car_deployments": "Number of full safety-car deployment messages during the race.",
    "virtual_safety_car_deployments": "Number of virtual safety-car deployment messages during the race.",
    "driver_id": "Stable lowercase driver identifier used across canonical tables.",
    "car_number": "Car or entry number used by the driver in that race; part of the historical entry key.",
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
    "table": "Canonical table from which the provenance record was extracted.",
    "earliest_season": "Earliest season containing an observed row in the table.",
    "latest_season": "Latest season containing an observed row in the table.",
    "row_count": "Number of published rows in the table.",
    "availability_note": "Known source-coverage boundary and interpretation guidance.",
    "race_name": "Official or source-provided race name.",
    "run_status": "Overall validation status assigned to the race build.",
    "severity": "Severity assigned to the individual data-quality finding.",
    "affected_table": "Canonical table affected by the finding, when table-specific.",
    "issue_code": "Stable machine-readable identifier for the data-quality finding.",
    "issue_message": "Human-readable explanation of the finding or source limitation.",
    "resolution": "Publication action taken for the finding, such as documentation, warning, exclusion, or blocking.",
}

DATASET_TITLE = "Formula 1 Pit Stop Dataset"
DATASET_SUBTITLE = "F1 results since 1950, pit stops since 2011 and detailed telemetry since 2023"
DATASET_DESCRIPTION = (
    "Accuracy-first Formula 1 tables for pit-stop and finishing-position modelling from 1950 "
    "through the current season. Official race entries and circuit metadata begin in 1950, "
    "recorded pit events begin in 2011, and detailed tyre, trackside weather, and race-control "
    "coverage begins in 2023. Unavailable historical telemetry is left absent rather than "
    "converted to false zeros. coverage.csv and validation_manifest.json document every boundary."
)
