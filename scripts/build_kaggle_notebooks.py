"""Generate the public Kaggle notebook series for the canonical F1 dataset."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "kaggle"
DATASET = "akashrane2609/formula-1-pit-stop-dataset"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": dedent(text).strip() + "\n"}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(text).strip() + "\n",
    }


SETUP = code(
    """
    import os
    from pathlib import Path
    import warnings

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import seaborn as sns

    warnings.filterwarnings("ignore", category=FutureWarning)
    sns.set_theme(style="whitegrid", context="notebook")
    pd.set_option("display.max_columns", 100)

    REQUIRED_FILES = {"race_context.csv", "race_drivers.csv", "pit_events.csv"}
    configured_dir = os.getenv("F1_DATA_DIR")
    candidates = [
        Path(configured_dir) if configured_dir else None,
        Path("/kaggle/input/formula-1-pit-stop-dataset"),
        Path.cwd() / "release" / "kaggle",
        Path.cwd() / "data",
    ]
    kaggle_input = Path("/kaggle/input")
    if kaggle_input.exists():
        candidates.extend(path for path in kaggle_input.iterdir() if path.is_dir())

    DATA_DIR = next(
        (path for path in candidates if path and REQUIRED_FILES.issubset(p.name for p in path.glob("*.csv"))),
        None,
    )
    if DATA_DIR is None:
        checked = "\\n - ".join(str(path) for path in candidates if path)
        raise FileNotFoundError(
            "Could not find the F1 dataset CSV files. Attach the Kaggle dataset "
            "'akashrane2609/formula-1-pit-stop-dataset' or set F1_DATA_DIR to the "
            f"directory containing the CSV files.\\nChecked:\\n - {checked}"
        )
    print(f"Reading data from {DATA_DIR}")
    """
)


GUIDE_SETUP = code(
    """
    import os
    from pathlib import Path
    import matplotlib.pyplot as plt
    import pandas as pd

    pd.set_option('display.max_columns', 100)
    REQUIRED_FILES = {'race_context.csv', 'race_drivers.csv', 'pit_events.csv',
                      'stints.csv', 'weather_observations.csv', 'coverage.csv',
                      'data_quality_issues.csv', 'data_dictionary.csv'}
    configured = os.getenv('F1_DATA_DIR')
    candidates = [Path(configured)] if configured else []
    candidates += [Path('/kaggle/input/formula-1-pit-stop-dataset'),
                   Path.cwd() / 'release' / 'kaggle', Path.cwd() / 'data']
    kaggle_input = Path('/kaggle/input')
    if kaggle_input.exists():
        candidates += [p for p in kaggle_input.iterdir() if p.is_dir()]
    DATA_DIR = next((p for p in candidates if p.is_dir() and
                     REQUIRED_FILES.issubset({f.name for f in p.glob('*.csv')})), None)
    if DATA_DIR is None:
        try:
            import kagglehub
        except ImportError as exc:
            raise ImportError('Attach the dataset in Kaggle, or in Colab run %pip install kagglehub and rerun this cell.') from exc
        DATA_DIR = Path(kagglehub.dataset_download('akashrane2609/formula-1-pit-stop-dataset'))
    missing_files = REQUIRED_FILES - {p.name for p in DATA_DIR.glob('*.csv')}
    if missing_files:
        raise FileNotFoundError(f'Missing required files in {DATA_DIR}: {sorted(missing_files)}')
    print(f'Dataset directory: {DATA_DIR}')
    """
)


NOTEBOOKS = {
    "01_dataset_guide": {
        "slug": "f1-dataset-guide-coverage-quality-and-joins",
        "title": "F1 Dataset Guide: Coverage, Quality and Joins",
        "cells": [
            md('''<a href="https://www.kaggle.com/code/akashrane2609/dataset-guide-coverage-quality-and-joins" target="_blank"><img alt="Open in Kaggle" src="https://kaggle.com/static/images/open-in-kaggle.svg"></a>'''),
            md("""
            # Formula 1 dataset: a field guide

            **Start here before analyzing strategy.** This notebook shows what each row represents, where the historical record starts, which missing values mean “unavailable,” and how to join tables without multiplying rows. Run all cells to refresh the numbers for the release attached to this notebook.

            | If you want to… | Go to |
            |:--|:--|
            | Understand files and time coverage | Inventory and historical coverage |
            | Build a race or driver view | Keys and two safe join recipes |
            | Assess whether an observation can be used | Missingness, quality ledger, and provenance |
            | Train a model | Feature timing and modeling checklist |

            **Scope:** race results extend further back than pit stops and modern telemetry. A missing pit row in an uncovered race is not evidence of zero stops. The newest season can be partial.
            """),
            GUIDE_SETUP,
            md("""
            ## 1. Inventory: what is in this release?

            `race_context` is one row per race; `race_drivers` is one row per entrant; `pit_events` records visits to the pits; `stints` records tyre runs; `weather_observations` is a time series. The companion files describe coverage, fields, quality decisions, and source provenance. Counts below come from the attached files, so they change when the dataset is updated.
            """),
            code("""
            core = ['race_context', 'race_drivers', 'pit_events', 'stints', 'weather_observations']
            tables = {name: pd.read_csv(DATA_DIR / f'{name}.csv', low_memory=False) for name in core}
            coverage = pd.read_csv(DATA_DIR / 'coverage.csv')
            issues = pd.read_csv(DATA_DIR / 'data_quality_issues.csv', low_memory=False)
            dictionary = pd.read_csv(DATA_DIR / 'data_dictionary.csv', low_memory=False)
            provenance_path = DATA_DIR / 'provenance.csv'
            provenance = pd.read_csv(provenance_path, low_memory=False) if provenance_path.exists() else None
            inventory = pd.DataFrame([
                {'table': name, 'rows': len(frame), 'columns': frame.shape[1],
                 'first_season': frame.season.min() if len(frame) else pd.NA,
                 'last_season': frame.season.max() if len(frame) else pd.NA}
                for name, frame in tables.items()
            ])
            display(inventory)
            print('Companion files:', ', '.join(p.name for p in sorted(DATA_DIR.glob('*.csv')) if p.stem not in core))
            """),
            md("""
            ## 2. Grain and keys

            A **grain** is what one row stands for. Join a many-row table to a one-row table only after checking that the one-row side has unique keys.

            | File | One row represents | Join key / expected unique key |
            |:--|:--|:--|
            | `race_context` | A race | `season, round_number` |
            | `race_drivers` | A driver entry in a race | `season, round_number, driver_id, car_number` |
            | `pit_events` | A recorded pit visit | `season, round_number, driver_id, stop_number` |
            | `stints` | A tyre stint | `season, round_number, driver_id, stint_number` |
            | `weather_observations` | A weather sample | Use its session and timestamp fields; aggregate before joining to a race |

            `driver_id` alone is not a race key. Keep `car_number` in the historical entry key. Never directly join raw pit visits and raw stints to driver entries together: the two one-to-many relationships multiply rows. Aggregate each table to driver-race first.
            """),
            code("""
            keys = {
                'race_context': ['season', 'round_number'],
                'race_drivers': ['season', 'round_number', 'driver_id', 'car_number'],
                'pit_events': ['season', 'round_number', 'driver_id', 'stop_number'],
                'stints': ['season', 'round_number', 'driver_id', 'stint_number'],
            }
            key_report = pd.DataFrame([
                {'table': name, 'rows': len(tables[name]),
                 'null_key_rows': int(tables[name][cols].isna().any(axis=1).sum()),
                 'duplicate_key_rows': int(tables[name].duplicated(cols, keep=False).sum())}
                for name, cols in keys.items()
            ])
            display(key_report)
            if key_report[['null_key_rows', 'duplicate_key_rows']].to_numpy().any():
                print('Review key exceptions before joining; do not silently drop duplicates.')
            """),
            md("""
            ## 3. Historical coverage

            The dataset combines sources with different start years. `coverage.csv` is the release-specific reference; the chart uses its declared boundaries. The season at the right edge may still be underway, so compare race counts before interpreting a trend. Pit events begin in the modern pit-source era (2011); tyre stints and sampled weather are much newer (2023 onward).
            """),
            code("""
            display(coverage)
            spans = coverage.dropna(subset=['earliest_season', 'latest_season']).copy()
            spans['earliest_season'] = pd.to_numeric(spans.earliest_season)
            spans['latest_season'] = pd.to_numeric(spans.latest_season)
            fig, ax = plt.subplots(figsize=(10, max(3, len(spans) * .48)))
            for y, row in enumerate(spans.itertuples()):
                ax.plot([row.earliest_season, row.latest_season], [y, y], lw=9, solid_capstyle='round', color='#e10600')
            ax.set(yticks=range(len(spans)), yticklabels=spans['table'], xlabel='Season', title='Declared availability by table')
            ax.grid(axis='x', alpha=.25)
            plt.tight_layout()
            races_per_season = tables['race_context'].groupby('season').size().rename('races').tail(12)
            display(races_per_season.to_frame().T)
            """),
            md("""
            ## 4. Join recipe: race context → driver entries

            This is the base table for driver-level questions. `validate='many_to_one'` raises an error if a race key is repeated on the context side. Check unmatched rows and row count rather than assuming a successful merge is correct.
            """),
            code("""
            race_key = ['season', 'round_number']
            context_columns = [c for c in ['season', 'round_number', 'circuit_short_name', 'country_name', 'start_rainfall']
                               if c in tables['race_context'].columns]
            driver_view = tables['race_drivers'].merge(
                tables['race_context'][context_columns], on=race_key, how='left',
                validate='many_to_one', indicator=True
            )
            print('Driver entries:', len(tables['race_drivers']), '| joined rows:', len(driver_view))
            display(driver_view['_merge'].value_counts().rename('rows').to_frame())
            display(driver_view.drop(columns='_merge').head(5))
            """),
            md("""
            ## 5. Join recipe: recorded stops per driver

            Count pit events at the **driver-race** grain before joining. A race with no pit-event rows is excluded: its absence could mean the source did not supply data. Within a race that has recorded pit events, an entrant with no matching event gets a zero *recorded* stop count. This is a descriptive view, not a claim that the source captures every real-world stop.
            """),
            code("""
            driver_key = ['season', 'round_number', 'driver_id']
            pit_counts = tables['pit_events'].groupby(driver_key).size().rename('recorded_stops').reset_index()
            covered_races = pit_counts[race_key].drop_duplicates()
            entrants = tables['race_drivers'].merge(covered_races, on=race_key, how='inner')
            stops_view = entrants.merge(pit_counts, on=driver_key, how='left', validate='many_to_one')
            stops_view['recorded_stops'] = stops_view['recorded_stops'].fillna(0).astype(int)
            print('Races with pit records:', len(covered_races), '| driver entries in those races:', len(stops_view))
            display(stops_view.groupby('season').agg(races=('round_number', 'nunique'),
                                                     entrants=('driver_id', 'size'),
                                                     mean_recorded_stops=('recorded_stops', 'mean')).tail(10))
            """),
            md("""
            ## 6. Missing values need a reason

            Missingness may reflect an entire source era, an unavailable race, or a field missing within an otherwise covered record. These cases need different treatment. The table below compares missing rates within seasons; choose a field in `column_to_check` to inspect its pattern. Read its dictionary description and `coverage.csv` before filling values.
            """),
            code("""
            column_to_check = 'start_rainfall'
            frame = tables['race_context']
            if column_to_check not in frame:
                print(f'{column_to_check} is absent in this release; choose another race_context column.')
            else:
                rates = frame.groupby('season')[column_to_check].agg(
                    rows='size', missing=lambda values: values.isna().sum(),
                    missing_rate=lambda values: values.isna().mean()
                ).reset_index()
                display(rates.tail(20))
                ax = rates.plot(x='season', y='missing_rate', figsize=(10, 3.5), legend=False, color='#3671c6')
                ax.set(ylabel='Fraction missing', ylim=(0, 1), title=f'Missing {column_to_check} by season')
                plt.tight_layout()
                display(dictionary[(dictionary['table'] == 'race_context') &
                                   (dictionary['column'] == column_to_check)])
            """),
            md("""
            ## 7. Inspect quality decisions and origins

            `data_quality_issues.csv` is a ledger of warnings, errors, and their resolutions. Filter by table or race before using a suspicious value. `provenance.csv`, when included in the release, records where each table/race came from. An issue count measures documented decisions; it is not a score for a driver or team.
            """),
            code("""
            display(issues.groupby(['severity', 'affected_table', 'resolution'], dropna=False)
                    .size().rename('issues').reset_index().sort_values('issues', ascending=False).head(20))
            display(issues[['season', 'round_number', 'affected_table', 'issue_code', 'issue_message']].tail(8))
            if provenance is not None:
                display(provenance.head(8))
                print('Provenance rows:', len(provenance))
            else:
                print('No provenance.csv in this release; consult the dataset card for source details.')
            """),
            md("""
            ## 8. Choose features at the right time

            The dictionary includes `feature_time`, `role`, and `target` where supplied. A pre-race model can use information available before lights out; it cannot use pit visits, final classification, or weather observed later. For an in-race model, specify the decision lap and discard future observations. Split by race or season in chronological order to avoid learning from future races.
            """),
            code("""
            timing_columns = [c for c in ['table', 'column', 'description', 'feature_time', 'role', 'target']
                              if c in dictionary.columns]
            focus = ['grid_position', 'classified_position', 'start_rainfall', 'lap_number', 'pit_duration_s']
            display(dictionary.loc[dictionary['column'].isin(focus), timing_columns].head(25))
            if 'target' in dictionary:
                display(dictionary.loc[dictionary['target'].astype(str).str.lower().isin(['true', '1', 'yes']),
                                       timing_columns].head(20))
            """),
            md("""
            ## 9. Before you publish a chart or model

            - State the unit of analysis: race, driver-race, pit visit, stint, or timestamp.
            - Restrict to seasons and races where the relevant source is available; show the number of observations.
            - Validate join cardinality and inspect unmatched keys.
            - Explain whether a zero was observed or inferred within a covered race.
            - Check the quality ledger and provenance for the slice you use.
            - Fix the prediction moment, exclude targets and later events, and split chronologically.
            - Treat race-start rainfall as a snapshot; it does not describe conditions throughout a race. Associations here do not establish causality.

            **Continue exploring:** [Pit stop and weather](https://www.kaggle.com/code/akashrane2609/f1-pit-stop-trends-and-weather-strategy) · [Tyre stints](https://www.kaggle.com/code/akashrane2609/f1-tyre-stint-strategy-explorer) · [Position strategy](https://www.kaggle.com/code/akashrane2609/f1-leakage-safe-prediction-baselines). Adapt the recipes above to your question, and cite the dataset release used for your result.
            """),
        ],
    },
    "02_pit_stop_weather": {
        "slug": "f1-pit-stop-trends-and-weather-strategy",
        "title": "F1 Pit Stop Trends and Weather Strategy",
        "cells": [
            md("""
            # F1 Pit Stop Trends and Weather Strategy

            Explore recorded pit-stop patterns from 2011 onward and race-start trackside weather from 2023 onward. These are descriptive associations—not causal claims—and the 2026 season may be incomplete.
            """),
            SETUP,
            code("""
            pits = pd.read_csv(DATA_DIR / "pit_events.csv")
            drivers = pd.read_csv(DATA_DIR / "race_drivers.csv")
            context = pd.read_csv(DATA_DIR / "race_context.csv")
            race_keys = ["season", "round_number"]

            entrants = drivers.groupby(race_keys).size().rename("entrants")
            race_pits = pits.groupby(race_keys).size().rename("pit_stops")
            by_race = context.merge(entrants, on=race_keys, how="left").merge(race_pits, on=race_keys, how="left")
            # Only count zero-stop drivers within races that have pit-event coverage.
            # A race with no pit records may reflect missing source data, not zero stops.
            by_race = by_race[by_race["season"] >= 2011].copy()
            missing_pit_races = by_race["pit_stops"].isna()
            print(f"Excluding {missing_pit_races.sum()} races with no recorded pit events")
            by_race = by_race[~missing_pit_races & by_race["entrants"].gt(0)].copy()
            by_race["stops_per_driver"] = by_race["pit_stops"] / by_race["entrants"]
            by_race.head()
            """),
            md("## How pit-stop frequency changed\n\nRaces without pit-event records are excluded because an empty source response cannot establish a genuine zero-stop race. Counts describe recorded pit events only."),
            code("""
            annual = by_race.groupby("season").agg(
                races=("round_number", "size"), mean_stops_per_driver=("stops_per_driver", "mean")
            ).reset_index()
            plt.figure(figsize=(11, 4))
            sns.lineplot(data=annual, x="season", y="mean_stops_per_driver", marker="o", color="#e10600")
            plt.title("Average recorded stops per driver and race")
            plt.ylabel("Stops per driver")
            plt.tight_layout()
            display(annual.tail(10))
            print("The last season may be incomplete; compare its race count before reading the trend.")
            """),
            md("## Typical pit laps and durations\n\n`pit_duration_s` is source-defined pit-lane duration and is not interchangeable with stationary `stop_duration_s`."),
            code("""
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            sns.histplot(pits["lap_number"].dropna(), bins=35, ax=axes[0], color="#3671c6")
            axes[0].set_title("Recorded pit-stop lap distribution")
            duration = pits["pit_duration_s"].dropna()
            duration = duration[duration.between(duration.quantile(.01), duration.quantile(.99))]
            sns.histplot(duration, bins=35, ax=axes[1], color="#ff8700")
            axes[1].set_title("Pit-lane duration (1st–99th percentile)")
            plt.tight_layout()
            """),
            md("## Race-start rain and stopping frequency\n\nWeather is measured near the scheduled start and does not describe every lap. It is suitable for a lights-out snapshot, not a full-race weather history."),
            code("""
            modern = by_race[by_race["start_rainfall"].notna()].copy()
            modern["start_condition"] = np.where(modern["start_rainfall"].astype(float).gt(0), "Rain at start", "Dry at start")
            weather_summary = modern.groupby("start_condition")["stops_per_driver"].agg(
                races="count", mean="mean", median="median"
            )
            display(weather_summary)
            print("Race-start rain is descriptive; it does not account for rain later in a race.")
            plt.figure(figsize=(7, 4))
            sns.boxplot(data=modern, x="start_condition", y="stops_per_driver", palette=["#3671c6", "#e10600"])
            plt.title("Stops per driver by race-start rainfall")
            plt.xlabel("")
            plt.tight_layout()
            """),
            md("## Most stop-intensive races"),
            code("""
            cols = ["season", "round_number", "circuit_short_name", "country_name", "pit_stops", "entrants", "stops_per_driver", "start_rainfall"]
            by_race.sort_values("stops_per_driver", ascending=False)[cols].head(15)
            """),
        ],
    },
    "03_tyre_strategy": {
        "slug": "f1-tyre-stint-strategy-explorer",
        "title": "F1 Tyre Stint Strategy Explorer",
        "cells": [
            md("""
            # F1 Tyre Stint Strategy Explorer

            Explore modern tyre compounds, completed-lap stint lengths, tyre age, and strategy sequences. Stint data begins in 2023; it does not contain lap times, so stint length is not a tyre-degradation measurement.
            """),
            SETUP,
            code("""
            stints = pd.read_csv(DATA_DIR / "stints.csv")
            pits = pd.read_csv(DATA_DIR / "pit_events.csv")
            context = pd.read_csv(DATA_DIR / "race_context.csv")
            stints["stint_length_laps"] = stints["lap_end"] - stints["lap_start"] + 1
            valid = stints[stints["stint_length_laps"].gt(0)].copy()
            valid["compound"] = valid["compound"].fillna("UNKNOWN").str.upper()
            valid.head()
            """),
            md("## Compound usage by season"),
            code("""
            usage = valid.groupby(["season", "compound"]).size().rename("stints").reset_index()
            usage["share"] = usage["stints"] / usage.groupby("season")["stints"].transform("sum")
            pivot = usage.pivot(index="season", columns="compound", values="share").fillna(0)
            pivot.plot.bar(stacked=True, figsize=(11, 5), colormap="tab20")
            plt.title("Share of recorded stints by compound")
            plt.ylabel("Share")
            plt.legend(title="Compound", bbox_to_anchor=(1.02, 1), loc="upper left")
            plt.tight_layout()
            """),
            md("## Stint length distributions"),
            code("""
            common = valid[valid["compound"].isin(["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"])]
            plt.figure(figsize=(11, 5))
            sns.boxplot(data=common, x="compound", y="stint_length_laps", showfliers=False,
                        order=["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"])
            plt.title("Completed-lap stint lengths by compound")
            plt.xlabel("")
            plt.ylabel("Laps")
            plt.tight_layout()
            common.groupby("compound")["stint_length_laps"].agg(["count", "median", "mean"]).round(1)
            """),
            md("## Strategy sequences\n\nA sequence summarizes recorded compounds for one driver-race. Stint transitions are checked against pit events where those records exist; discrepancies need review and are not treated as measured stops. The sequence does not encode safety-car timing, traffic, or tyre condition."),
            code("""
            strategy = (valid.sort_values(["season", "round_number", "driver_id", "stint_number"])
                .groupby(["season", "round_number", "driver_id"])["compound"]
                .agg(" → ".join).rename("strategy").reset_index())
            strategy["stint_transitions"] = strategy["strategy"].str.count("→")
            pit_counts = pits.groupby(["season", "round_number", "driver_id"]).size().rename("recorded_stops")
            strategy = strategy.merge(pit_counts, on=["season", "round_number", "driver_id"], how="left")
            covered_races = pits[["season", "round_number"]].drop_duplicates().assign(pit_coverage=True)
            strategy = strategy.merge(covered_races, on=["season", "round_number"], how="left")
            strategy.loc[strategy["pit_coverage"].eq(True), "recorded_stops"] = (
                strategy.loc[strategy["pit_coverage"].eq(True), "recorded_stops"].fillna(0)
            )
            display(pd.DataFrame({
                "driver_races_with_pit_coverage": [strategy["pit_coverage"].eq(True).sum()],
                "stint_stop_disagreements": [(
                    strategy["pit_coverage"].eq(True)
                    & strategy["stint_transitions"].ne(strategy["recorded_stops"])
                ).sum()],
            }))
            display(strategy["strategy"].value_counts().head(15).to_frame("driver_races"))
            plt.figure(figsize=(9, 5))
            top = strategy["strategy"].value_counts().head(10).sort_values()
            top.plot.barh(color="#e10600")
            plt.title("Most common recorded compound sequences")
            plt.xlabel("Driver-races")
            plt.tight_layout()
            """),
            md("## Build a race strategy table"),
            code("""
            race_names = context[["season", "round_number", "circuit_short_name", "country_name"]]
            strategy.merge(race_names, on=["season", "round_number"], how="left").sort_values(
                ["season", "round_number", "stint_transitions"], ascending=[False, False, False]
            ).head(25)
            """),
        ],
    },
    "04_prediction_baselines": {
        "slug": "f1-leakage-safe-prediction-baselines",
        "title": "F1 Leakage-Safe Prediction Baselines",
        "cells": [
            md("""
            # F1 Leakage-Safe Prediction Baselines

            Two reproducible baselines: finishing position and pit-stop count. Features are computed from prior races only, and the latest season is held out chronologically. Scores are reference points—not claims of production readiness.
            """),
            SETUP,
            code("""
            from sklearn.compose import ColumnTransformer
            from sklearn.dummy import DummyRegressor
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.impute import SimpleImputer
            from sklearn.metrics import mean_absolute_error, mean_squared_error
            from sklearn.pipeline import Pipeline
            from sklearn.preprocessing import OneHotEncoder

            drivers = pd.read_csv(DATA_DIR / "race_drivers.csv")
            pits = pd.read_csv(DATA_DIR / "pit_events.csv")
            context = pd.read_csv(DATA_DIR / "race_context.csv")
            keys = ["season", "round_number", "driver_id"]

            frame = drivers.merge(context[["season", "round_number", "circuit_id"]], on=["season", "round_number"], how="left")
            stop_counts = pits.groupby(keys).size().rename("pit_stop_count").reset_index()
            covered_races = pits[["season", "round_number"]].drop_duplicates().assign(pit_coverage=True)
            frame = frame.merge(stop_counts, on=keys, how="left")
            frame = frame.merge(covered_races, on=["season", "round_number"], how="left")
            # Zero is supported for a driver only when other pit events establish race coverage.
            covered = frame["season"].ge(2011) & frame["pit_coverage"].eq(True)
            frame.loc[covered, "pit_stop_count"] = frame.loc[covered, "pit_stop_count"].fillna(0)
            frame = frame.sort_values(["season", "round_number", "driver_id"]).reset_index(drop=True)

            # Collapse to one entity/race value before shifting. This prevents another
            # entry in the same race from entering the current row's history.
            def add_prior_mean(data, entity, value, output):
                race_value = (data.groupby([entity, "season", "round_number"], as_index=False)[value]
                              .mean().sort_values([entity, "season", "round_number"]))
                race_value[output] = race_value.groupby(entity)[value].transform(
                    lambda s: s.shift().expanding().mean()
                )
                return data.merge(race_value[[entity, "season", "round_number", output]],
                                  on=[entity, "season", "round_number"], how="left")

            frame = add_prior_mean(frame, "driver_id", "classified_position", "driver_prior_mean_finish")
            frame = add_prior_mean(frame, "constructor_id", "classified_position", "constructor_prior_mean_finish")
            frame = add_prior_mean(frame, "driver_id", "pit_stop_count", "driver_prior_mean_stops")
            frame.tail()
            """),
            md("## Chronological evaluation helper\n\nUse three rolling season holdouts, with all training data before each holdout. The newest season is excluded because it may be incomplete. Mean Spearman correlation compares ordering within each race; higher is better."),
            code("""
            categorical = ["driver_id", "constructor_id", "circuit_id"]
            numeric = ["grid_position", "driver_prior_mean_finish", "constructor_prior_mean_finish", "driver_prior_mean_stops"]
            prep = ColumnTransformer([
                ("num", SimpleImputer(strategy="median"), numeric),
                ("cat", Pipeline([
                    ("impute", SimpleImputer(strategy="most_frequent")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]), categorical),
            ])

            def evaluate(data, target):
                data = data.dropna(subset=[target]).copy()
                seasons = sorted(data["season"].unique())
                # Conservatively exclude the latest season because it may still be underway.
                test_seasons = seasons[-4:-1]
                assert len(test_seasons) == 3, "At least four seasons are needed"
                rows = []
                for test_season in test_seasons:
                    train = data[data["season"] < test_season]
                    test = data[data["season"] == test_season]
                    assert train["season"].max() < test["season"].min()
                    X_train, X_test = train[numeric + categorical], test[numeric + categorical]
                    y_train, y_test = train[target], test[target]
                    models = {
                        "median_dummy": Pipeline([("prep", prep), ("model", DummyRegressor(strategy="median"))]),
                        "random_forest": Pipeline([("prep", prep), ("model", RandomForestRegressor(
                            n_estimators=40, max_depth=12, min_samples_leaf=4, random_state=42, n_jobs=1
                        ))]),
                    }
                    predictions = {}
                    if target == "classified_position":
                        # A driver starting position is a meaningful pre-race finish benchmark.
                        predictions["grid_position"] = test["grid_position"].to_numpy()
                    for name, model in models.items():
                        model.fit(X_train, y_train)
                        predictions[name] = model.predict(X_test)
                    for name, pred in predictions.items():
                        rank_frame = test[["season", "round_number"]].copy()
                        rank_frame["actual"] = y_test.to_numpy()
                        rank_frame["predicted"] = pred
                        correlations = [
                            group["actual"].corr(group["predicted"], method="spearman")
                            for _, group in rank_frame.groupby(["season", "round_number"])
                            if group["actual"].nunique() > 1 and group["predicted"].nunique() > 1
                        ]
                        rows.append({
                            "target": target, "model": name, "test_season": test_season,
                            "train_rows": len(train), "test_rows": len(test),
                            "MAE": mean_absolute_error(y_test, pred),
                            "RMSE": mean_squared_error(y_test, pred) ** .5,
                            "mean_race_spearman": np.mean(correlations) if correlations else np.nan,
                        })
                return pd.DataFrame(rows), test_seasons
            """),
            md("## Finishing-position baseline\n\n`classified_position` is the target and never a feature. Grid position and prior-history aggregates are available before the race."),
            code("""
            finish_data = frame[frame["classified_position"].notna() & frame["grid_position"].notna()]
            finish_scores, finish_test_seasons = evaluate(finish_data, "classified_position")
            finish_scores.round(3)
            """),
            md("## Pit-stop-count baseline\n\nThis task starts in 2011. An absent driver pit row counts as zero only if the race has recorded pit events; races with no pit-event records are excluded."),
            code("""
            pit_data = frame[frame["season"].ge(2011) & frame["pit_stop_count"].notna()]
            pit_scores, pit_test_seasons = evaluate(pit_data, "pit_stop_count")
            scores = pd.concat([finish_scores, pit_scores], ignore_index=True)
            display(scores.round(3))
            summary = scores.groupby(["target", "model"], as_index=False).agg(
                mean_MAE=("MAE", "mean"), mean_RMSE=("RMSE", "mean"),
                mean_race_spearman=("mean_race_spearman", "mean"),
            )
            display(summary.round(3))
            sns.barplot(data=summary, x="target", y="mean_MAE", hue="model", errorbar=None)
            plt.title("Mean absolute error across three rolling season holdouts")
            plt.ylabel("Mean MAE (lower is better)")
            plt.xlabel("")
            plt.tight_layout()
            """),
            md("## Responsible interpretation\n\n- The latest season is excluded from scoring because it may be incomplete.\n- Historical averages are shifted, but a stronger production pipeline should compute features race-by-race to handle duplicate historical entries explicitly.\n- Race-start weather is excluded here to keep this a strict pre-event baseline.\n- Compare finish predictions with the grid baseline and within-race ranking, not MAE alone.\n- Inspect uncertainty and race coverage before deployment; never replace the chronological holdout with a random row split."),
        ],
    },
}


def build() -> None:
    for folder, spec in NOTEBOOKS.items():
        destination = OUT / folder
        destination.mkdir(parents=True, exist_ok=True)
        notebook_name = f"{spec['slug']}.ipynb"
        cells = []
        for index, cell in enumerate(spec["cells"]):
            copied = dict(cell)
            copied["id"] = f"{folder.replace('_', '-')}-{index:02d}"
            cells.append(copied)
        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.11"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        (destination / notebook_name).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
        metadata = {
            "id": f"akashrane2609/{spec['slug']}",
            "title": spec["title"],
            "code_file": notebook_name,
            "language": "python",
            "kernel_type": "notebook",
            "is_private": False,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": [DATASET],
            "competition_sources": [],
            "kernel_sources": [],
            "model_sources": [],
        }
        (destination / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
