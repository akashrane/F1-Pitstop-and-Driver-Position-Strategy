from __future__ import annotations

import f1_strategy_data.sources as sources


def test_full_season_results_follow_jolpica_pagination(monkeypatch):
    calls = []

    def fake_get(url):
        calls.append(url)
        offset = 0 if "offset=0" in url else 2
        races = (
            [{"round": "1", "Results": [{"position": "1"}, {"position": "2"}]}]
            if offset == 0 else
            [{"round": "2", "Results": [{"position": "1"}]}]
        )
        return ({
            "MRData": {"total": "3", "RaceTable": {"Races": races}}
        }, {"source_url": url, "retrieved_at_utc": "2026-01-01T00:00:00+00:00"})

    monkeypatch.setattr(sources, "_get_json", fake_get)
    payload, _ = sources.jolpica_season_full_results(1950)

    assert len(calls) == 2
    assert [race["round"] for race in payload["MRData"]["RaceTable"]["Races"]] == ["1", "2"]
    assert payload["MRData"]["total"] == "3"
