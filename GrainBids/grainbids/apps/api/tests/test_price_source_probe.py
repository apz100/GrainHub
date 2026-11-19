from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.price_source_probe import SAMPLE_SOURCES, classify_status, probe_sources  # noqa: E402


def test_classify_live_with_bid_content() -> None:
    status, has_bid = classify_status(200, "<html>Cash Bids for today</html>")
    assert status == "live"
    assert has_bid is True


def test_classify_live_without_bid_content() -> None:
    status, has_bid = classify_status(200, "<html>Welcome</html>")
    assert status == "live"
    assert has_bid is False


def test_classify_blocked_and_dead() -> None:
    assert classify_status(403)[0] == "blocked"
    assert classify_status(429)[0] == "blocked"
    assert classify_status(404)[0] == "dead"
    assert classify_status(500)[0] == "dead"
    assert classify_status(None)[0] == "error"


def test_probe_sources_records_per_source_status_without_network() -> None:
    class _FakeResponse:
        def __init__(self, status_code: int, text: str) -> None:
            self.status_code = status_code
            self.text = text

    with patch("app.services.price_source_probe.requests.get") as fake_get:
        fake_get.return_value = _FakeResponse(200, "Cash Bids")
        results = probe_sources(SAMPLE_SOURCES[:2], pause_seconds=0)
    assert len(results) == 2
    assert all(r.status == "live" and r.has_bid_content for r in results)
    assert [r.company for r in results] == [s[0] for s in SAMPLE_SOURCES[:2]]
