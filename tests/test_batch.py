import csv
import json
from pathlib import Path

import f1_strategy_data.batch as batch
from f1_strategy_data.batch import consolidate


def test_consolidate_combines_round_files(tmp_path: Path):
    for round_number in (1, 2):
        folder = tmp_path / "processed" / "2026" / f"round-{round_number:02d}"
        folder.mkdir(parents=True)
        with (folder / "race_drivers.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["season", "driver_id"])
            writer.writeheader()
            writer.writerow({"season": 2026, "driver_id": f"driver-{round_number}"})
        (folder / "validation_report.json").write_text(
            json.dumps({
                "status": "verified" if round_number == 1 else "quarantined",
                "issues": [] if round_number == 1 else [{
                    "severity": "error", "table": "race_drivers", "code": "bad_result"
                }],
            }),
            encoding="utf-8",
        )
    counts = consolidate(tmp_path, 2026, 2026)
    assert counts["race_drivers"] == 1
    output = tmp_path / "processed" / "consolidated_2026_2026" / "race_drivers.csv"
    assert output.exists()
    with output.open(encoding="utf-8", newline="") as handle:
        assert [row["driver_id"] for row in csv.DictReader(handle)] == ["driver-1"]


def test_discovery_failure_is_recorded_without_aborting_manifest(tmp_path: Path, monkeypatch):
    def fail_discovery(season):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(batch, "discover_completed_races", fail_discovery)
    manifest = batch.build_seasons(2023, 2023, tmp_path)

    assert manifest["summary"] == {"failed": 1}
    assert manifest["runs"][0]["race_name"] == "season discovery"
    assert manifest["runs"][0]["reason"] == "RuntimeError: rate limited"
    assert (tmp_path / "processed" / "manifest_2023_2023.json").exists()
