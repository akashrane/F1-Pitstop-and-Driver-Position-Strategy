from __future__ import annotations

import pandas as pd
import pytest

from f1_strategy_data.modeling import TASKS, evaluate_task


def _frame(task: str) -> pd.DataFrame:
    spec = TASKS[task]
    rows = []
    for index in range(60):
        is_test = index >= 40
        row = {
            "season": 2026 if is_test else 2025,
            "dataset_split": "test" if is_test else "train",
            "driver_id": f"driver-{index % 5}",
            "constructor_id": f"team-{index % 3}",
            "current_compound": ["SOFT", "MEDIUM", "HARD"][index % 3],
        }
        for offset, column in enumerate(spec["numeric"]):
            row[column] = (index + offset) % 17
        if task == "finishing_position":
            row[spec["target"]] = index % 20 + 1
        elif task == "pit_stop_count":
            row[spec["target"]] = index % 3
        else:
            row[spec["target"]] = index % 11 == 0
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.mark.parametrize("task", list(TASKS))
def test_evaluate_task_reports_chronological_metrics(task: str) -> None:
    report = evaluate_task(task, _frame(task))

    assert report["train_rows"] == 40
    assert report["test_rows"] == 20
    assert report["train_seasons"] == [2025, 2025]
    assert report["test_seasons"] == [2026, 2026]
    assert TASKS[task]["target"] not in report["features"]
    assert "dataset_split" not in report["features"]
    assert set(report) >= {"baseline", "model"}


def test_evaluate_task_rejects_non_chronological_split() -> None:
    frame = _frame("finishing_position")
    frame.loc[frame["dataset_split"] == "train", "season"] = 2026

    with pytest.raises(ValueError, match="not chronological"):
        evaluate_task("finishing_position", frame)


def test_evaluate_task_rejects_missing_feature() -> None:
    frame = _frame("pit_stop_count").drop(columns=["grid_position"])

    with pytest.raises(ValueError, match="missing columns: grid_position"):
        evaluate_task("pit_stop_count", frame)
