from pathlib import Path
from types import SimpleNamespace

import pytest

from f1_strategy_data.intelligence_agent import (
    EnterpriseDataIntelligenceAgent,
    build_catalog,
    discover_csv_files,
)


def test_catalog_is_bounded_and_profiles_nulls(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "races.csv").write_text("season,winner\n2025,A\n2026,\n", encoding="utf-8")

    profile = build_catalog(tmp_path, max_rows=1)[0]

    assert profile.path == "data/races.csv"
    assert profile.sampled_rows == 1
    assert profile.null_counts == {"season": 0, "winner": 0}
    assert profile.sample == [{"season": "2025", "winner": "A"}]


def test_data_root_cannot_escape_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="escapes repository"):
        discover_csv_files(tmp_path, ("../outside",))


def test_agent_uses_responses_api_without_storage(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "races.csv").write_text("season,winner\n2026,A\n", encoding="utf-8")
    calls = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text="Grounded answer")

    client = SimpleNamespace(responses=Responses())
    agent = EnterpriseDataIntelligenceAgent(
        tmp_path, client=client, model="test-model", data_roots=("data",),
    )

    assert agent.ask("Who won?") == "Grounded answer"
    assert calls[0]["model"] == "test-model"
    assert calls[0]["store"] is False
    assert "data/races.csv" in calls[0]["input"]
