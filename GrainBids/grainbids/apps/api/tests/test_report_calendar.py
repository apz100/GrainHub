"""USDA report calendar tests.

Dates are the verified 2026 schedule from the research notes
(report.md §5). Countdown math is tested against a fixed "today" so
it does not depend on the day the suite runs.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.report_calendar import build_calendar, router as calendar_router  # noqa: E402


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(calendar_router)
    return TestClient(app)


def _by_report(events: list[dict], report: str) -> list[dict]:
    return [event for event in events if event["report"] == report]


def test_wasde_2026_dates_and_noon_release() -> None:
    events = _by_report(build_calendar(2026, date(2026, 1, 1)), "WASDE")
    assert len(events) == 12
    assert [event["release_at"][:10] for event in events] == [
        "2026-01-12",
        "2026-02-10",
        "2026-03-10",
        "2026-04-09",
        "2026-05-12",
        "2026-06-11",
        "2026-07-10",
        "2026-08-12",
        "2026-09-11",
        "2026-10-09",
        "2026-11-10",
        "2026-12-10",
    ]
    assert all(event["release_time_et"] == "12:00 PM ET" for event in events)
    assert all(event["publisher"].startswith("USDA") for event in events)


def test_countdown_days_until_from_fixed_today() -> None:
    events = build_calendar(2026, date(2026, 1, 1))
    wasde = _by_report(events, "WASDE")[0]
    assert wasde["days_until"] == 11
    assert wasde["is_past"] is False
    assert wasde["is_today"] is False
    # A release on the day itself is "today", not past.
    events = build_calendar(2026, date(2026, 1, 12))
    wasde = _by_report(events, "WASDE")[0]
    assert wasde["days_until"] == 0
    assert wasde["is_today"] is True
    assert wasde["is_past"] is False
    # And the day after it is past.
    events = build_calendar(2026, date(2026, 1, 13))
    assert _by_report(events, "WASDE")[0]["is_past"] is True
    assert _by_report(events, "WASDE")[0]["days_until"] == -1


def test_quarterly_and_annual_fixed_reports() -> None:
    events = build_calendar(2026, date(2026, 1, 1))
    assert [e["release_at"][:10] for e in _by_report(events, "Grain Stocks")] == [
        "2026-01-12",
        "2026-03-31",
        "2026-06-30",
        "2026-09-30",
    ]
    assert [e["release_at"][:10] for e in _by_report(events, "Prospective Plantings")] == [
        "2026-03-31"
    ]
    assert [e["release_at"][:10] for e in _by_report(events, "Acreage")] == ["2026-06-30"]
    assert [e["release_at"][:10] for e in _by_report(events, "Small Grains Summary")] == [
        "2026-09-30"
    ]


def test_crop_progress_mondays_april_to_november() -> None:
    events = _by_report(build_calendar(2026, date(2026, 1, 1)), "Crop Progress")
    assert len(events) == 35
    assert events[0]["release_at"][:10] == "2026-04-06"
    assert events[-1]["release_at"][:10] == "2026-11-30"
    assert all(e["release_time_et"] == "4:00 PM ET" for e in events)
    assert all(date.fromisoformat(e["release_at"][:10]).weekday() == 0 for e in events)


def test_export_sales_thursdays_and_cot_fridays() -> None:
    events = build_calendar(2026, date(2026, 1, 1))
    sales = _by_report(events, "Export Sales")
    assert len(sales) == 53  # 2026 starts and ends on a Thursday
    assert sales[0]["release_at"][:10] == "2026-01-01"
    assert sales[-1]["release_at"][:10] == "2026-12-31"
    assert all(e["release_time_et"] == "8:30 AM ET" for e in sales)
    assert all(e["publisher"] == "USDA FAS" for e in sales)
    cot = _by_report(events, "Commitments of Traders")
    assert len(cot) == 52
    assert cot[0]["release_at"][:10] == "2026-01-02"
    assert all(e["release_time_et"] == "3:30 PM ET" for e in cot)
    assert all(e["publisher"] == "CFTC" for e in cot)


def test_events_sorted_by_release_time() -> None:
    events = build_calendar(2026, date(2026, 6, 1))
    release_times = [event["release_at"] for event in events]
    assert release_times == sorted(release_times)


def test_other_years_are_refused_not_invented() -> None:
    with pytest.raises(ValueError, match="Only the verified 2026 schedule"):
        build_calendar(2027, date(2026, 1, 1))
    with pytest.raises(ValueError, match="Only the verified 2026 schedule"):
        build_calendar(2025, date(2026, 1, 1))


def test_endpoint_returns_next_event_and_upcoming() -> None:
    payload = _client().get("/api/research/calendar").json()
    assert payload["year"] == 2026
    assert payload["schedule"] == "2026 USDA report schedule"
    assert "USDA" in payload["source"]
    assert payload["timezone"] == "America/New_York"
    assert payload["count"] == len(payload["events"])
    assert payload["next_event"] is not None
    assert payload["next_event"]["days_until"] >= 0
    assert payload["next_event"] == payload["upcoming"][0]
    assert len(payload["upcoming"]) == 10
    upcoming_times = [event["release_at"] for event in payload["upcoming"]]
    assert upcoming_times == sorted(upcoming_times)
    assert all(event["days_until"] >= 0 for event in payload["upcoming"])


def test_endpoint_refuses_other_years() -> None:
    response = _client().get("/api/research/calendar?year=2027")
    assert response.status_code == 400
    assert "2026" in response.json()["detail"]
