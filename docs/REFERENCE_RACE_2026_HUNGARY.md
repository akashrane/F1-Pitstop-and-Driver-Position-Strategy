# Phase 2 reference race: 2026 Hungarian Grand Prix

The first canonical end-to-end build targets round 11 of the 2026 season at the Hungaroring.

## Identity

- Season: 2026
- Round: 11
- OpenF1 session key: `11342`
- Race date: 2026-07-26
- FIA final classification: published as Hungarian Grand Prix Doc 62 on 2026-07-26 at 19:25 CET

The build intentionally maps OpenF1 records using the car number used at the event rather than the driver's permanent number. This matters in 2026 because Lando Norris used number 1 while his permanent number remains 4.

## Generated rows

| Table | Rows |
|---|---:|
| `race_drivers` | 22 |
| `stints` | 67 |
| `pit_events` | 44 |
| `weather_observations` | 156 |

All 22 classified positions agree between Jolpica and OpenF1. Canonical primary keys are unique, stint boundaries do not overlap, pit laps do not exceed the driver's completed laps, and weather observations pass range and timestamp validation.

## Open warning

The race remains `warning`, not fully verified, because the pit sources disagree for Lando Norris:

- Jolpica: 3 pit events
- OpenF1: 2 pit events

The pipeline preserves the OpenF1 table and records the discrepancy in `validation_report.json`; it does not silently choose a value. This event must be reconciled against another timing source before the race is approved for publication or modeling.

## Reproduce

```powershell
$env:PYTHONPATH = "src"
python scripts/build_reference_race.py --season 2026 --round 11 --session-key 11342
```

Raw snapshots are written under `data/raw/2026/round-11/`. Canonical CSVs and the validation report are written under `data/processed/2026/round-11/`. Generated data is ignored by Git and is published only after validation.
