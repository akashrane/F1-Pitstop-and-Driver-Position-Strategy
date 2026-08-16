# F1 Pit-Stop and Driver Position Strategy

An accuracy-first data and modeling project for two Formula 1 prediction tasks:

1. When and how often a driver will pit.
2. Where a driver will finish the race.

The repository is being upgraded from its original 1950â€“2024 experimental pipeline to a reproducible pipeline covering completed races through 2026.

## Current status

The files under `F1_Position_Predictor/Formula1_Data` and `F1_Data_Scrapping/Data_Retived` are retained as **legacy artifacts**. They are useful for tracing the original project, but they are not yet certified as model-ready.

The audit identified important limitations:

- Historical source gaps were sometimes represented as zero pit stops instead of unavailable values.
- Open-Meteo soil temperature was labeled as F1 track temperature.
- Full-day hourly weather was interpolated across race laps without using actual lap timestamps.
- Some generated features were random or synthetic.
- Several files contain character-encoding corruption.
- The original validation used synthetic data and may contain target leakage.

Do not use legacy model scores as production-quality benchmarks until the rebuilt datasets and chronological evaluation are complete.

## Accuracy policy

- FIA final classifications are authoritative for official race outcomes.
- FastF1/OpenF1 trackside timing data is preferred for laps, stints, pits, race control, and weather.
- Jolpica replaces the retired Ergast API for schedules, results, and available historical pit stops.
- Open-Meteo is contextual off-track weather only; it is not a source of measured track temperature.
- Missing source coverage remains null and is accompanied by a validation status.
- Raw source responses are immutable and carry retrieval metadata.

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for the full policy.

## Canonical datasets

The rebuilt pipeline produces separate tables instead of one ambiguous merged file:

| Table | Grain | Purpose |
|---|---|---|
| `race_drivers` | Driver Ã— race | Starting conditions, official result, and finishing-position target |
| `stints` | Driver Ã— continuous tyre stint | Compound, tyre age, stint boundaries, and degradation |
| `pit_events` | Driver Ã— pit-lane visit | Pit lap, duration, and surrounding race state |
| `weather_observations` | Session Ã— observation timestamp | Trackside air/track temperature, humidity, rainfall, pressure, and wind |

Every field used for modeling will be tagged as `pre_race`, `live`, or `post_race` to prevent target leakage.

## Repository layout

```text
src/f1_strategy_data/   Source clients and validation logic
scripts/                Auditing and pipeline entry points
tests/                  Automated data-quality tests
docs/                   Source and methodology documentation
F1_Position_Predictor/  Legacy notebook, model, reports, and datasets
F1_Data_Scrapping/      Legacy collection scripts and retrieved data
```

## Development

The validation foundation uses the Python standard library. Run:

```powershell
python -m pytest -q
python scripts/audit_legacy_data.py `
  F1_Position_Predictor/Formula1_Data/f1_pitstops_2018_2024.csv
```

The source clients currently expose Jolpica results/pit stops and OpenF1 session endpoints while retaining source URL and retrieval time.

Build every completed race in a season range and create verified-only consolidated tables:

```powershell
$env:PYTHONPATH = "src"
python scripts/build_seasons.py --start-year 2023 --end-year 2026
```

Raw responses and their provenance are cached per race. Use `--refresh` only
when intentionally taking new source snapshots. Each run writes a manifest;
warning and quarantined races remain available for investigation but are
excluded from the model-ready consolidated tables.

## Automated updates

`.github/workflows/update-dataset.yml` runs every Tuesday at 06:17 UTC, after
the usual race weekend, and can also be started manually. It tests the code,
builds completed races, rejects failed or empty releases, uploads the verified
files as a GitHub Actions artifact, and publishes a Kaggle version on scheduled
runs. Warning and quarantined races are visible in the manifest but are not
included in the published CSV files.

Configure these GitHub repository settings before enabling publication:

- Actions secrets: `KAGGLE_USERNAME` and `KAGGLE_KEY`
- Actions variable: `KAGGLE_DATASET_SLUG`, for example
  `akashrane2609/formula-1-pit-stop-dataset`

The Kaggle dataset must already exist. For a first publication, run
`kaggle datasets create -p release/kaggle` locally once; later workflow runs
create versions with `kaggle datasets version`.

## Planned modeling approach

- Pit-stop count: count or classification model using only information known at prediction time.
- Next pit lap: survival/hazard or lap-level classification model.
- Finishing position: ranking or ordinal model evaluated on future races/seasons.
- 2026 is treated as a separate regulation era to account for concept drift.

Random row splits and synthetic validation will be replaced by chronological race and season holdouts.

## Phase 4 feature engineering

Build the leakage-safe pre-race finishing-position table from a consolidated
`race_drivers.csv` file:

```powershell
$env:PYTHONPATH = "src"
python scripts/build_pre_race_features.py `
  --input data/processed/consolidated_2023_2026/race_drivers.csv `
  --race-context data/processed/consolidated_2023_2026/race_context.csv `
  --output data/features/pre_race_finishing_position.csv `
  --holdout-season 2026
```

Rolling driver and constructor features are calculated from races completed
strictly before the current race. All drivers in one race are scored before
that race updates any history, preventing teammate-result leakage.

Build the pre-race pit-stop-count table from the three verified canonical
inputs:

```powershell
python scripts/build_pit_count_features.py `
  --race-drivers data/processed/consolidated_2023_2026/race_drivers.csv `
  --race-context data/processed/consolidated_2023_2026/race_context.csv `
  --pit-events data/processed/consolidated_2023_2026/pit_events.csv `
  --stints data/processed/consolidated_2023_2026/stints.csv `
  --output data/features/pre_race_pit_stop_count.csv `
  --holdout-season 2026
```

A missing pit-event row becomes a zero-stop target only because these inputs
contain verified races; unavailable or quarantined races are excluded earlier.

Build the live lap-level next-pit table:

```powershell
python scripts/build_next_pit_features.py `
  --race-drivers data/processed/consolidated_2023_2026/race_drivers.csv `
  --pit-events data/processed/consolidated_2023_2026/pit_events.csv `
  --stints data/processed/consolidated_2023_2026/stints.csv `
  --output data/features/live_next_pit.csv `
  --holdout-season 2026
```

Each row represents the state at one driver lap. Future pit timing appears only
in target columns. Weather is intentionally omitted until lap timestamps are
available for a time-safe observation join.

## Phase 5 baseline models

Install the modeling dependencies and evaluate all three tasks with a strict
future-season holdout:

```powershell
python -m pip install -e ".[modeling,dev]"
$env:PYTHONPATH = "src"
python scripts/train_baselines.py `
  --finishing-position data/features/pre_race_finishing_position.csv `
  --pit-stop-count data/features/pre_race_pit_stop_count.csv `
  --next-pit data/features/live_next_pit.csv
```

The command compares a simple dummy baseline with a gradient-boosted
model and writes `reports/generated/baseline_metrics.json`. Regression tasks
report MAE and RMSE. The imbalanced next-pit classifier reports average
precision, Brier score, accuracy, precision, recall, and F1. Its probability
threshold is selected on the latest training season, never the test season.
The pit-count task similarly chooses between gradient boosting and a random
forest using that internal chronological validation season. Fixed feature allowlists exclude all
targets, identifiers used only for joining, and post-race fields. Training is
rejected unless every training season precedes every test season.

Historical OpenF1 stints sometimes assign the same boundary lap to two
adjacent stints. The normalizer preserves that lap as the last completed lap of
the earlier stint and moves the later stint start forward by one. Each repair
is retained as an informational validation record; multi-lap overlaps remain
errors and quarantine the race.

## Phase 6 race context

The canonical `race_context.csv` contains one row per verified race with its
circuit identity, scheduled UTC start, the nearest trackside weather reading
within 15 minutes of that start, and post-race safety-car and race-distance
outcomes. The raw session, weather, and race-control responses remain cached
with checksums for auditability.

Feature builders use current race-start weather because it is observable at
lights out. Current-race winner laps and safety-car counts are never used as
predictors. Instead, the builders calculate rolling circuit history strictly
from earlier completed races: prior average winner laps, safety-car and virtual
safety-car deployments, and rain rate. This preserves the chronological
leakage boundary even when the same circuit appears multiple times.

## Author

Akash Rane â€” [LinkedIn](https://www.linkedin.com/in/akashrane/) Â· [Portfolio](https://akashrane.github.io/website/)
