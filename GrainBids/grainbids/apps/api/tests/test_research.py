from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.market_report import append_research_section, compile_market_report  # noqa: E402
from app.services.research import (  # noqa: E402
    ResearchKeyRequired,
    fetch_nass_quick_stats,
    parse_crop_progress_text,
    parse_nass_records,
    parse_wasde_text,
    research_status,
)


def test_nass_without_key_raises_key_required() -> None:
    with pytest.raises(ResearchKeyRequired):
        fetch_nass_quick_stats(commodity="Corn", year=2026, api_key="")


def test_research_status_reports_keys_as_absent_by_default() -> None:
    status = research_status()
    assert status.nass_configured is False
    assert status.fas_configured is False
    assert status.wasde_file_url.startswith("https://")


def test_parse_nass_records_normalises_fields() -> None:
    parsed = parse_nass_records(
        [
            {
                "commodity_desc": "CORN",
                "statisticcat_desc": "PRODUCTION",
                "year": "2026",
                "state_name": "IOWA",
                "county_name": "",
                "Value": "2,500,000,000",
                "unit_desc": "BU",
            }
        ]
    )
    assert parsed[0]["commodity"] == "CORN"
    assert parsed[0]["statistic"] == "PRODUCTION"
    assert parsed[0]["source"] == "USDA NASS Quick Stats"


def test_parse_wasde_text_extracts_ending_stocks_only_when_present() -> None:
    text = """U.S. Corn Supply and Use
Beginning stocks 2,095
Production 15,893
Ending stocks 1,758
U.S. Soybeans Supply and Use
Ending stocks 300
"""
    values = parse_wasde_text(text)
    assert {v["commodity"]: v["value"] for v in values} == {"Corn": "1758", "Soybeans": "300"}
    assert all(v["source"] == "USDA WASDE" for v in values)


def test_parse_wasde_text_returns_nothing_for_unrelated_text() -> None:
    assert parse_wasde_text("No tables here.\nEnding stocks 999\n") == []


def test_parse_crop_progress_text_extracts_harvest_percent() -> None:
    text = "Corn harvested 88\nSoybeans harvested 96\nWinter wheat planted 92\n"
    values = parse_crop_progress_text(text)
    assert {v["commodity"]: (v["metric"], v["value"]) for v in values} == {
        "Corn": ("harvested", "88"),
        "Soybeans": ("harvested", "96"),
        "Winter Wheat": ("planted", "92"),
    }


def test_append_research_section_is_noop_without_reports() -> None:
    report = compile_market_report(
        {"Corn": [], "Soybeans": [], "Wheat": []},
        generated_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        region="Eastern Ontario",
    )
    assert append_research_section(report, []) is report


def test_append_research_section_labels_source_and_vintage() -> None:
    report = compile_market_report(
        {"Corn": [], "Soybeans": [], "Wheat": []},
        generated_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        region="Eastern Ontario",
    )
    updated = append_research_section(
        report,
        [
            {
                "report_type": "wasde",
                "commodity": "Corn",
                "report_date": "2026-11-10",
                "vintage": "2026-11-10",
                "source": "USDA WASDE",
                "payload": {
                    "values": [
                        {
                            "commodity": "Corn",
                            "metric": "ending_stocks",
                            "value": "1758",
                            "unit": "million bushels",
                        }
                    ]
                },
            }
        ],
    )
    assert "USDA Research" in updated.text
    assert "USDA WASDE" in updated.text
    assert "2026-11-10" in updated.text
    assert "1758" in updated.text
    assert updated.sections[-1]["kind"] == "research"
