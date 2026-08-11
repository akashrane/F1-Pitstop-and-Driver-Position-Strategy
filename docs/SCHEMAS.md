# Canonical schema contracts

The JSON Schema files in `schemas/` are the version-controlled contracts for generated datasets. A breaking field, key, unit, or nullability change requires a schema version change and release note.

| Table | Primary key | Earliest detailed coverage target |
|---|---|---|
| `race_drivers` | `season`, `round_number`, `driver_id` | 1950 results; detailed features vary |
| `stints` | `session_key`, `driver_id`, `stint_number` | 2018 verified rebuild |
| `pit_events` | `session_key`, `driver_id`, `stop_number` | Source-dependent; unavailable is null |
| `weather_observations` | `session_key`, `observed_at_utc`, `weather_source` | 2018 verified rebuild |

Custom annotations make modeling constraints machine-readable:

- `x-feature-time`: `pre_race`, `live`, or `post_race`
- `x-target`: prediction target
- `x-unit`: canonical stored unit
- `x-role`: identifier rather than feature

CSV headers use the JSON property names exactly. Empty CSV fields represent schema `null`; a genuine numeric zero must be stored as `0`.
