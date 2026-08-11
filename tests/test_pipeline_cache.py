from pathlib import Path

from f1_strategy_data.pipeline import _load_or_fetch


def test_raw_snapshot_cache_avoids_repeat_download(tmp_path: Path):
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return [{"value": calls}], {"source_url": "https://example.test", "retrieved_at_utc": "now"}

    first = _load_or_fetch(tmp_path, "sample", loader, refresh=False)
    second = _load_or_fetch(tmp_path, "sample", loader, refresh=False)

    assert calls == 1
    assert second == first


def test_refresh_replaces_cached_snapshot(tmp_path: Path):
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return [{"value": calls}], {"source_url": "https://example.test", "retrieved_at_utc": str(calls)}

    _load_or_fetch(tmp_path, "sample", loader, refresh=False)
    payload, _ = _load_or_fetch(tmp_path, "sample", loader, refresh=True)

    assert calls == 2
    assert payload == [{"value": 2}]
