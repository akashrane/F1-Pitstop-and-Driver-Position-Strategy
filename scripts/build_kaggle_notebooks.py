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
        checked = "\n - ".join(str(path) for path in candidates if path)
        raise FileNotFoundError(
            "Could not find the F1 dataset CSV files. Attach the Kaggle dataset "
            "'akashrane2609/formula-1-pit-stop-dataset' or set F1_DATA_DIR to the "
            f"directory containing the CSV files.\nChecked:\n - {checked}"
        )
    print(f"Reading data from {DATA_DIR}")
    """
)


NOTEBOOKS = {
    "01_dataset_guide": {
        "slug": "f1-dataset-guide-coverage-quality-and-joins",
        "title": "F1 Dataset Guide: Coverage, Quality and Joins",
        "cells": [
            md("""
            # F1 Dataset Guide: Coverage, Quality and Joins

            A practical tour of the canonical Formula 1 tables: what each row means, which seasons are covered, how quality decisions are documented, and how to join the files safely.

            **You will learn:** table grain, historical availability boundaries, key integrity, and modeling-time leakage boundaries. Missing telemetry before its source era means *unavailable*, not zero.
            """),
            SETUP,
            code("""
            files = ["race_context", "race_drivers", "pit_events", "stints", "weather_observations"]
            tables = {name: pd.read_csv(DATA_DIR / f"{name}.csv", low_memory=False) for name in files}
            coverage = pd.read_csv(DATA_DIR / "coverage.csv")
            issues = pd.read_csv(DATA_DIR / "data_quality_issues.csv", low_memory=False)
            dictionary = pd.read_csv(DATA_DIR / "data_dictionary.csv")

            inventory = pd.DataFrame({
                "table": files,
                "rows": [len(tables[n]) for n in files],
                "columns": [tables[n].shape[1] for n in files],
                "earliest_season": [tables[n]["season"].min() for n in files],
                "latest_season": [tables[n]["season"].max() for n in files],
            })
            inventory
            """),
            md("## Historical coverage\n\nThe tables deliberately begin in different years because source availability differs. This prevents false zeroes in early seasons."),
            code("""
            display(coverage)
            ax = coverage.sort_values("earliest_season").plot.barh(
                x="table", y="row_count", figsize=(10, 4), legend=False, color="#e10600"
            )
            ax.set(title="Published rows by table", xlabel="Rows", ylabel="")
            plt.tight_layout()
            """),
            md("## Key integrity and join map\n\nUse `(season, round_number)` for a race, add `driver_id` for a driver-race, and use `session_key` where modern session-level data provides it."),
            code("""
            checks = {
                "race_context unique race": ~tables["race_context"].duplicated(["season", "round_number"]).any(),
                "race_drivers unique entry": ~tables["race_drivers"].duplicated(["season", "round_number", "driver_id", "car_number"]).any(),
                "pit_events unique stop": ~tables["pit_events"].duplicated(["season", "round_number", "driver_id", "stop_number"]).any(),
                "stints unique stint": ~tables["stints"].duplicated(["season", "round_number", "driver_id", "stint_number"]).any(),
                "all driver races have context": tables["race_drivers"].merge(
                    tables["race_context"][["season", "round_number"]].drop_duplicates(),
                    on=["season", "round_number"], how="left", indicator=True
                )["_merge"].eq("both").all(),
            }
            pd.Series(checks, name="passed").to_frame()
            """),
            md("## Missingness is meaningful\n\nThe chart below highlights columns whose availability is tied to a source era. Read `coverage.csv` and the dictionary before imputing values."),
            code("""
            missing = pd.concat({name: frame.isna().mean() for name, frame in tables.items()}).rename("missing_rate")
            missing = missing[missing.gt(0)].sort_values(ascending=False).head(25).reset_index()
            missing.columns = ["table", "column", "missing_rate"]
            display(missing)
            plt.figure(figsize=(9, 7))
            sns.barplot(data=missing, y=missing["table"] + "." + missing["column"], x="missing_rate", color="#3671c6")
            plt.title("Largest documented missingness rates")
            plt.xlabel("Fraction missing")
            plt.ylabel("")
            plt.tight_layout()
            """),
            md("## Quality ledger\n\nEvery normalization or coverage decision is published. `warning` is included but documented; an error would exclude the affected table for that race."),
            code("""
            display(issues.groupby(["severity", "resolution"], dropna=False).size().rename("issues").reset_index())
            issues["issue_code"].value_counts().head(12).to_frame("count")
            """),
            md("## Modeling checklist\n\n- Define the prediction moment first.\n- Use only fields available by that moment.\n- Split chronologically by race or season.\n- Do not interpret absent pre-2011 pit rows as zero stops.\n- Treat 2026 as a partial season until it is complete.\n- Keep targets such as `classified_position` out of predictors."),
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
            by_race["pit_stops"] = by_race["pit_stops"].fillna(0)
            by_race["stops_per_driver"] = by_race["pit_stops"] / by_race["entrants"]
            by_race = by_race[by_race["season"] >= 2011].copy()
            by_race.head()
            """),
            md("## How pit-stop frequency changed"),
            code("""
            annual = by_race.groupby("season").agg(
                races=("round_number", "size"), mean_stops_per_driver=("stops_per_driver", "mean")
            ).reset_index()
            plt.figure(figsize=(11, 4))
            sns.lineplot(data=annual, x="season", y="mean_stops_per_driver", marker="o", color="#e10600")
            plt.title("Average recorded stops per driver and race")
            plt.ylabel("Stops per driver")
            plt.tight_layout()
            annual.tail(10)
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
            display(modern.groupby("start_condition")["stops_per_driver"].agg(["count", "mean", "median"]))
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
            md("## Strategy sequences\n\nA sequence summarizes the ordered compounds for one driver-race. It is useful for exploration but does not encode safety-car timing, traffic, or tyre condition."),
            code("""
            strategy = (valid.sort_values(["season", "round_number", "driver_id", "stint_number"])
                .groupby(["season", "round_number", "driver_id"])["compound"]
                .agg(" → ".join).rename("strategy").reset_index())
            strategy["stops_implied"] = strategy["strategy"].str.count("→")
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
                ["season", "round_number", "stops_implied"], ascending=[False, False, False]
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
            frame = frame.merge(stop_counts, on=keys, how="left")
            # Zero is valid only inside the recorded-pit era (2011 onward).
            frame.loc[frame["season"].ge(2011), "pit_stop_count"] = frame.loc[frame["season"].ge(2011), "pit_stop_count"].fillna(0)
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
            md("## Chronological evaluation helper"),
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
                test_season = int(data["season"].max())
                train, test = data[data["season"] < test_season], data[data["season"] == test_season]
                assert train["season"].max() < test["season"].min()
                X_train, X_test = train[numeric + categorical], test[numeric + categorical]
                y_train, y_test = train[target], test[target]
                models = {
                    "median_dummy": Pipeline([("prep", prep), ("model", DummyRegressor(strategy="median"))]),
                    "random_forest": Pipeline([("prep", prep), ("model", RandomForestRegressor(
                        n_estimators=40, max_depth=12, min_samples_leaf=4, random_state=42, n_jobs=1
                    ))]),
                }
                rows = []
                for name, model in models.items():
                    model.fit(X_train, y_train)
                    pred = model.predict(X_test)
                    rows.append({"target": target, "model": name, "test_season": test_season,
                                 "train_rows": len(train), "test_rows": len(test),
                                 "MAE": mean_absolute_error(y_test, pred),
                                 "RMSE": mean_squared_error(y_test, pred) ** .5})
                return pd.DataFrame(rows), test_season
            """),
            md("## Finishing-position baseline\n\n`classified_position` is the target and never a feature. Grid position and prior-history aggregates are available before the race."),
            code("""
            finish_data = frame[frame["classified_position"].notna() & frame["grid_position"].notna()]
            finish_scores, finish_test_season = evaluate(finish_data, "classified_position")
            finish_scores.round(3)
            """),
            md("## Pit-stop-count baseline\n\nThis task starts in 2011, when recorded pit-event coverage begins. An absent pit row is treated as zero only within that supported era."),
            code("""
            pit_data = frame[frame["season"].ge(2011) & frame["pit_stop_count"].notna()]
            pit_scores, pit_test_season = evaluate(pit_data, "pit_stop_count")
            scores = pd.concat([finish_scores, pit_scores], ignore_index=True)
            display(scores.round(3))
            sns.barplot(data=scores, x="target", y="MAE", hue="model")
            plt.title("Chronological holdout MAE (lower is better)")
            plt.xlabel("")
            plt.tight_layout()
            """),
            md("## Responsible interpretation\n\n- The latest season may be incomplete, so metrics will change after each race.\n- Historical averages are shifted, but a stronger production pipeline should compute features race-by-race to handle duplicate historical entries explicitly.\n- Race-start weather is excluded here to keep this a strict pre-event baseline.\n- Use ranking metrics and uncertainty estimates before deploying finish predictions.\n- Never replace the chronological holdout with a random row split."),
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
