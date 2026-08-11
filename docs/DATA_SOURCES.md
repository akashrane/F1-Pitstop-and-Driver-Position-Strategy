# Data source and accuracy policy

## Source hierarchy

1. FIA final classifications and decision documents are authoritative for classified position, penalties, and official race outcome.
2. F1 live-timing data exposed through FastF1 or OpenF1 is the primary source for laps, stints, pit events, race control, and trackside weather.
3. Jolpica is the maintained Ergast successor and is used for schedules, historical results, and available historical pit stops.
4. Open-Meteo may provide off-track contextual weather only. Its soil temperature is not F1 track temperature.

## Accuracy rules

- Every measurement keeps its source URL and retrieval timestamp.
- Weather is joined by UTC observation time within the race session, never by spreading a full day across race laps.
- Missing pit-stop coverage remains null with `validation_status=unavailable`; it is never converted to zero.
- Track temperature is accepted only from trackside timing data.
- Final position is checked against the FIA final classification when an official document is available.
- Raw responses are immutable. Cleaning and feature generation operate on versioned derived tables.

## Canonical tables

- `race_drivers`: one driver per race, including targets and pre-race features.
- `stints`: one continuous tyre stint per driver and session.
- `pit_events`: one observed pit-lane visit.
- `weather_observations`: timestamped trackside observations.

Each table must include stable season, round, session, and driver identifiers plus `source`, `source_url`, `retrieved_at_utc`, and `validation_status`.

## Modeling boundary

Features are tagged `pre_race`, `live`, or `post_race`. Post-race values cannot be used to train pre-race or live prediction models. Evaluation must use chronological race or season holdouts rather than random row splits.
