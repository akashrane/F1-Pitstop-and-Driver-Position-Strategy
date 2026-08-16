"""Leakage-safe chronological baseline models for the three prediction tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
    root_mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


TASKS: dict[str, dict[str, Any]] = {
    "finishing_position": {
        "target": "classified_position",
        "kind": "regression",
        "numeric": [
            "grid_position", "driver_prior_starts", "driver_prior_avg_finish",
            "driver_prior_avg_grid", "driver_prior_dnf_rate",
            "driver_prior_avg_positions_gained", "driver_recent5_avg_finish",
            "driver_recent5_avg_grid", "constructor_prior_starts",
            "constructor_prior_avg_finish", "constructor_prior_dnf_rate",
            "constructor_recent5_avg_finish",
        ],
        "categorical": ["driver_id", "constructor_id"],
    },
    "pit_stop_count": {
        "target": "pit_stop_count",
        "kind": "regression",
        "numeric": [
            "grid_position", "driver_prior_races", "driver_prior_avg_pit_stops",
            "driver_recent5_avg_pit_stops", "driver_prior_zero_stop_rate",
            "driver_prior_two_plus_stop_rate", "driver_prior_avg_stints",
            "constructor_prior_driver_races", "constructor_prior_avg_pit_stops",
            "constructor_recent5_avg_pit_stops",
        ],
        "categorical": ["driver_id", "constructor_id"],
    },
    "next_pit": {
        "target": "pit_this_lap",
        "kind": "classification",
        "numeric": [
            "lap_number", "current_stint_number", "tyre_age_laps",
            "pit_stops_completed", "laps_since_last_pit",
        ],
        "categorical": ["driver_id", "current_compound"],
    },
}


def evaluate_task(task: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Fit baselines on train rows and evaluate only on later test rows."""
    if task not in TASKS:
        raise ValueError(f"Unknown task: {task}")
    spec = TASKS[task]
    feature_columns = spec["numeric"] + spec["categorical"]
    required = set(feature_columns + [spec["target"], "dataset_split", "season"])
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{task} is missing columns: {', '.join(missing)}")
    train = frame.loc[frame["dataset_split"] == "train"].copy()
    test = frame.loc[frame["dataset_split"] == "test"].copy()
    if train.empty or test.empty:
        raise ValueError(f"{task} requires non-empty train and test splits")
    if int(train["season"].max()) >= int(test["season"].min()):
        raise ValueError(f"{task} split is not chronological")

    x_train, x_test = train[feature_columns], test[feature_columns]
    y_train, y_test = train[spec["target"]], test[spec["target"]]
    def preprocessor() -> ColumnTransformer:
        return ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median"), spec["numeric"]),
        ("categorical", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
        ]), spec["categorical"]),
        ])

    if spec["kind"] == "classification":
        if y_train.nunique() < 2:
            raise ValueError(f"{task} training split needs both target classes")
        baseline = DummyClassifier(strategy="prior").fit(x_train, y_train)
        development, validation = _development_split(train, task)
        tuning_model = Pipeline([
            ("features", preprocessor()),
            ("model", GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ]).fit(development[feature_columns], development[spec["target"]])
        validation_probability = tuning_model.predict_proba(validation[feature_columns])[:, 1]
        threshold, validation_f1 = _best_f1_threshold(validation[spec["target"]], validation_probability)
        model = Pipeline([
            ("features", preprocessor()),
            ("model", GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ]).fit(x_train, y_train)
        return _classification_report(
            task, train, test, y_test, baseline, model, x_test, feature_columns,
            threshold, int(validation["season"].iloc[0]), validation_f1,
        )

    baseline = DummyRegressor(strategy="median").fit(x_train, y_train)
    selection: dict[str, Any] | None = None
    if task == "pit_stop_count":
        development, validation = _development_split(train, task)
        candidates = {
            "gradient_boosting": lambda: GradientBoostingRegressor(n_estimators=100, random_state=42),
            "random_forest": lambda: RandomForestRegressor(
                n_estimators=200, min_samples_leaf=5, random_state=42, n_jobs=1
            ),
        }
        scores: dict[str, float] = {}
        for name, factory in candidates.items():
            candidate = Pipeline([("features", preprocessor()), ("model", factory())]).fit(
                development[feature_columns], development[spec["target"]]
            )
            scores[name] = float(mean_absolute_error(
                validation[spec["target"]], candidate.predict(validation[feature_columns])
            ))
        selected_name = min(scores, key=scores.get)  # type: ignore[arg-type]
        estimator = candidates[selected_name]()
        selection = {
            "validation_season": int(validation["season"].iloc[0]),
            "validation_mae": scores,
            "selected_model": selected_name,
        }
    else:
        estimator = GradientBoostingRegressor(n_estimators=100, random_state=42)
    model = Pipeline([("features", preprocessor()), ("model", estimator)]).fit(x_train, y_train)
    return _regression_report(
        task, train, test, y_test, baseline, model, x_test, feature_columns, selection
    )


def evaluate_files(paths: dict[str, Path], output: Path | None = None) -> dict[str, Any]:
    """Evaluate feature CSVs and optionally persist one JSON report."""
    missing_tasks = sorted(set(TASKS) - set(paths))
    if missing_tasks:
        raise ValueError(f"Missing task paths: {', '.join(missing_tasks)}")
    reports = {task: evaluate_task(task, pd.read_csv(paths[task])) for task in TASKS}
    result = {
        "methodology": "chronological holdout; every train season precedes every test season",
        "tasks": reports,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _split_metadata(train: pd.DataFrame, test: pd.DataFrame, features: list[str]) -> dict[str, Any]:
    return {
        "features": features,
        "train_rows": len(train),
        "test_rows": len(test),
        "train_seasons": [int(train["season"].min()), int(train["season"].max())],
        "test_seasons": [int(test["season"].min()), int(test["season"].max())],
    }


def _development_split(train: pd.DataFrame, task: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    seasons = sorted(int(value) for value in train["season"].unique())
    if len(seasons) < 2:
        raise ValueError(f"{task} needs at least two training seasons for leakage-safe tuning")
    validation_season = seasons[-1]
    return train.loc[train["season"] < validation_season], train.loc[train["season"] == validation_season]


def _best_f1_threshold(y: pd.Series, probability: Any) -> tuple[float, float]:
    """Choose a classification cutoff using validation data only."""
    candidates = [value / 100 for value in range(1, 100)]
    scored = [(float(f1_score(y, probability >= value, zero_division=0)), value) for value in candidates]
    score, threshold = max(scored, key=lambda item: (item[0], -item[1]))
    return threshold, score


def _regression_report(
    task: str, train: pd.DataFrame, test: pd.DataFrame, y: pd.Series,
    baseline: Any, model: Any, x: pd.DataFrame, features: list[str],
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def metrics(prediction: Any) -> dict[str, float]:
        return {
            "mae": float(mean_absolute_error(y, prediction)),
            "rmse": float(root_mean_squared_error(y, prediction)),
        }
    report = {
        "task": task,
        **_split_metadata(train, test, features),
        "baseline": metrics(baseline.predict(x)),
        "model": metrics(model.predict(x)),
    }
    if selection is not None:
        report["model_selection"] = selection
    return report


def _classification_report(
    task: str, train: pd.DataFrame, test: pd.DataFrame, y: pd.Series,
    baseline: Any, model: Any, x: pd.DataFrame, features: list[str],
    threshold: float, validation_season: int, validation_f1: float,
) -> dict[str, Any]:
    def metrics(estimator: Any, cutoff: float | None = None) -> dict[str, float]:
        probability = estimator.predict_proba(x)[:, 1]
        prediction = estimator.predict(x) if cutoff is None else probability >= cutoff
        return {
            "average_precision": float(average_precision_score(y, probability)),
            "brier_score": float(brier_score_loss(y, probability)),
            "accuracy": float(accuracy_score(y, prediction)),
            "precision": float(precision_score(y, prediction, zero_division=0)),
            "recall": float(recall_score(y, prediction, zero_division=0)),
            "f1": float(f1_score(y, prediction, zero_division=0)),
        }
    return {
        "task": task,
        **_split_metadata(train, test, features),
        "positive_rate": float(y.astype(int).mean()),
        "baseline": metrics(baseline),
        "model": metrics(model, threshold),
        "threshold_selection": {
            "validation_season": validation_season,
            "metric": "f1",
            "selected_threshold": threshold,
            "validation_f1": validation_f1,
        },
    }
