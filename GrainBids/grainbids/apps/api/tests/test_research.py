from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.market_report import append_research_section, compile_market_report  # noqa: E402
from app.services.research import (  # noqa: E402
    ResearchKeyRequired,
    fetch_fas_psd,
    fetch_nass_quick_stats,
    parse_commitments_of_traders_text,
    parse_crop_production_text,
    parse_crop_progress_text,
    parse_export_sales_text,
    parse_grain_stocks_text,
    parse_nass_records,
    parse_wasde_text,
    research_status,
)


def test_nass_without_key_raises_key_required() -> None:
    with pytest.raises(ResearchKeyRequired):
        fetch_nass_quick_stats(commodity="Corn", year=2026, api_key="")


def test_fas_without_key_raises_key_required() -> None:
    with pytest.raises(ResearchKeyRequired):
        fetch_fas_psd(commodity_code="0440000", api_key="")


def test_fas_psd_calls_commodities_with_trailing_slash(monkeypatch) -> None:
    # The FAS server returns HTTP 500 for /api/psd/commodities without a
    # trailing slash and 200 with it (verified live 2026-11-19). Pin the
    # slashed URL so the slash is never "cleaned up" away.
    import app.services.research as research

    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return [{"commodityCode": "0440000", "commodityName": "Corn"}]

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        return FakeResponse()

    monkeypatch.setattr(research.requests, "get", fake_get)
    rows = fetch_fas_psd(commodity_code="0440000", api_key="test-key")
    assert captured["url"] == "https://api.fas.usda.gov/api/psd/commodities/"
    assert captured["params"] == {"commodityCode": "0440000"}
    assert rows == [{"commodityCode": "0440000", "commodityName": "Corn"}]


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


def test_parse_grain_stocks_text_extracts_latest_year_totals() -> None:
    # Lines copied verbatim from the Sep 30 2026 Grain Stocks txt release
    # (ESMIS grst0926_0.txt), Domestic Units table; December 1 has no
    # 2026 values yet, so no December rows are emitted for the latest year.
    text = """Contents
Grain Stocks by Position and Month in Domestic Units - United States: 2025 and 2026..........................  4
Grain Stocks by Position and Month in Metric Units - United States: 2025 and 2026............................  5
Grain Stocks by Position and Month in Domestic Units - United States: 2025 and 2026
[Blank data cells indicate estimation period has not yet begun]
----------------------------------------------------------------------------------------------
                :                 2025                 :                 2026
                :-----------------------------------------------------------------------------
      Date      :     On     :    Off     : Total all  :     On     :    Off     : Total all
                :   farms    :  farms 1/  : positions  :   farms    :  farms 1/  : positions
----------------------------------------------------------------------------------------------
                :                                1,000 bushels
Corn            :
March 1 ........: 4,500,000    3,647,437     8,147,437   5,432,000    3,598,190    9,030,190
September 1 ....:   643,200      908,086     1,551,286     787,300    1,307,757    2,095,057
December 1 .....: 8,699,000    4,606,825    13,305,825
Soybeans        :
September 1 ....:    91,500      233,306       324,806      90,400      224,733      315,133
----------------------------------------------------------------------------------------------
Grain Stocks by Position and Month in Metric Units - United States: 2025 and 2026
Corn            :
September 1 ....: 16,338,030   23,066,450   39,404,480   19,998,340   33,218,560   53,216,900
"""
    values = parse_grain_stocks_text(text)
    by_key = {(v["commodity"], v["metric"], v["position_date"]): v["value"] for v in values}
    assert by_key[("Corn", "total_stocks", "September 1, 2026")] == "2095057"
    assert by_key[("Corn", "on_farm_stocks", "September 1, 2026")] == "787300"
    assert by_key[("Corn", "off_farm_stocks", "September 1, 2026")] == "1307757"
    assert by_key[("Corn", "total_stocks", "March 1, 2026")] == "9030190"
    assert by_key[("Soybeans", "total_stocks", "September 1, 2026")] == "315133"
    assert all("December 1, 2026" not in key[2] for key in by_key)
    # Metric-units table must not leak in (its September corn total differs).
    assert by_key[("Corn", "total_stocks", "September 1, 2026")] != "53216900"
    assert all(v["unit"] == "thousand bushels" for v in values)
    assert all(v["source"] == "USDA NASS Grain Stocks" for v in values)


def test_parse_grain_stocks_text_returns_nothing_without_the_table() -> None:
    assert parse_grain_stocks_text("Grain Stocks\nOld crop corn stocks totaled 2.10 billion bushels.\n") == []
    assert parse_grain_stocks_text("") == []


def test_parse_commitments_of_traders_text_keeps_latest_grain_week_only() -> None:
    # First record is verbatim from the CFTC Public Reporting Environment
    # Legacy futures-only dataset (2022-09-13 corn); the 2022-09-20 rows
    # are synthetic fixtures with distinct values to test date filtering.
    import json

    payload = json.dumps(
        [
            {
                "market_and_exchange_names": "CORN - CHICAGO BOARD OF TRADE",
                "report_date_as_yyyy_mm_dd": "2022-09-13T00:00:00.000",
                "contract_market_name": "CORN",
                "open_interest_all": "1310411",
                "noncomm_positions_long_all": "424311",
                "noncomm_positions_short_all": "129742",
                "noncomm_postions_spread_all": "181162",
                "comm_positions_long_all": "588143",
                "comm_positions_short_all": "822322",
            },
            {
                "market_and_exchange_names": "CORN - CHICAGO BOARD OF TRADE",
                "report_date_as_yyyy_mm_dd": "2022-09-20T00:00:00.000",
                "contract_market_name": "CORN",
                "open_interest_all": "1300000",
                "noncomm_positions_long_all": "400000",
                "noncomm_positions_short_all": "120000",
                "noncomm_postions_spread_all": "180000",
                "comm_positions_long_all": "580000",
                "comm_positions_short_all": "820000",
            },
            {
                "market_and_exchange_names": "SOYBEANS - CHICAGO BOARD OF TRADE",
                "report_date_as_yyyy_mm_dd": "2022-09-20T00:00:00.000",
                "contract_market_name": "SOYBEANS",
                "open_interest_all": "900000",
                "noncomm_positions_long_all": "100000",
                "noncomm_positions_short_all": "50000",
                "comm_positions_long_all": "400000",
                "comm_positions_short_all": "450000",
            },
            {
                "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
                "report_date_as_yyyy_mm_dd": "2022-09-20T00:00:00.000",
                "contract_market_name": "GOLD",
                "open_interest_all": "500000",
                "noncomm_positions_long_all": "200000",
                "noncomm_positions_short_all": "100000",
                "comm_positions_long_all": "150000",
                "comm_positions_short_all": "160000",
            },
        ]
    )
    values = parse_commitments_of_traders_text(payload)
    by_key = {(v["commodity"], v["metric"]): v["value"] for v in values}
    assert by_key[("Corn", "open_interest")] == "1300000"
    assert by_key[("Corn", "noncommercial_long")] == "400000"
    assert by_key[("Corn", "noncommercial_spread")] == "180000"
    assert by_key[("Soybeans", "open_interest")] == "900000"
    # Soybeans fixture omits the spread field: it must be absent, not zero.
    assert ("Soybeans", "noncommercial_spread") not in by_key
    # Older week and non-grain markets are excluded entirely.
    assert "1310411" not in by_key.values()
    assert not any(v["commodity"] == "Gold" for v in values)
    assert all(v["report_date"] == "2022-09-20" for v in values)
    assert all(v["unit"] == "contracts" for v in values)
    assert all(v["source"] == "CFTC Commitments of Traders" for v in values)


def test_parse_commitments_of_traders_text_returns_nothing_for_bad_input() -> None:
    assert parse_commitments_of_traders_text("not json") == []
    assert parse_commitments_of_traders_text("{}") == []
    assert parse_commitments_of_traders_text("") == []


def test_parse_export_sales_text_sums_country_rows_for_latest_week() -> None:
    # First row is verbatim from the AgTransport Export Sales mirror
    # (Albania, corn, week ending 2007-10-18); other rows are synthetic
    # fixtures with distinct values to test summing and date filtering.
    import json

    payload = json.dumps(
        [
            {
                "date": "2007-10-18T00:00:00.000",
                "week": "42",
                "myear": "2007/2008",
                "country": "ALBANIA",
                "commodity": "Corn",
                "unit": "Metric Tons",
                "wkexportscmy": "5929",
                "accexportscmy": "5929",
                "outsalescmy": "0",
                "grosalescmy": "5929",
                "netsalescmy": "5929",
                "totcommcmy": "5929",
            },
            {
                "date": "2007-10-18T00:00:00.000",
                "week": "42",
                "myear": "2007/2008",
                "country": "BRAZIL",
                "commodity": "Corn",
                "unit": "Metric Tons",
                "wkexportscmy": "1000",
                "netsalescmy": "1000",
                "outsalescmy": "500",
                "totcommcmy": "1500",
            },
            {
                "date": "2007-10-18T00:00:00.000",
                "week": "42",
                "myear": "2007/2008",
                "country": "JAPAN",
                "commodity": "Wheat",
                "unit": "Metric Tons",
                "wkexportscmy": "200",
                "netsalescmy": "300",
                "outsalescmy": "400",
                "totcommcmy": "700",
            },
            {
                "date": "2007-10-11T00:00:00.000",
                "week": "41",
                "myear": "2007/2008",
                "country": "ALBANIA",
                "commodity": "Corn",
                "unit": "Metric Tons",
                "wkexportscmy": "99999",
                "netsalescmy": "99999",
                "outsalescmy": "99999",
                "totcommcmy": "99999",
            },
        ]
    )
    values = parse_export_sales_text(payload)
    by_key = {(v["commodity"], v["metric"]): v["value"] for v in values}
    assert by_key[("Corn", "net_sales")] == "6929"
    assert by_key[("Corn", "weekly_exports")] == "6929"
    assert by_key[("Corn", "outstanding_sales")] == "500"
    assert by_key[("Corn", "total_commitments")] == "7429"
    assert by_key[("Wheat", "net_sales")] == "300"
    assert "99999" not in by_key.values()
    assert all(v["week_ending"] == "2007-10-18" for v in values)
    assert all(v["marketing_year"] == "2007/2008" for v in values)
    assert all(v["unit"] == "Metric Tons" for v in values)
    assert all(v["source"] == "USDA FAS Export Sales" for v in values)


def test_parse_export_sales_text_returns_nothing_for_bad_input() -> None:
    assert parse_export_sales_text("not json") == []
    assert parse_export_sales_text("[]") == []
    assert parse_export_sales_text("") == []
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


# --- Crop Production (Nov 10 2026 release, ESMIS crop1126.txt) ---
# Table excerpts below are verbatim from the release file; the Rice
# table heading wrap and the Sorghum units line (no trailing dashes)
# are the two format quirks the parser must handle.
_CROP_PRODUCTION_CORN = """Corn for Grain Area Harvested, Yield, and Production - States and United States: 2025 and
Forecasted November 1, 2026
----------------------------------------------------------------------------------------------
                 :  Area harvested   :          Yield per acre          :     Production
                 :----------------------------------------------------------------------------
      State      :         :         :          :         2026          :          :
                 :  2025   :  2026   :   2025   :-----------------------:   2025   :   2026
                 :         :         :          : October 1 :November 1 :          :
----------------------------------------------------------------------------------------------
                 :    1,000 acres       ---------- bushels ----------    --- 1,000 bushels ---
                 :
Iowa ............: 13,150    12,800     210.0       219.0       219.0     2,761,500  2,803,200
United States ...: 90,948    88,506     186.5       181.2       179.6    16,963,628 15,893,419
----------------------------------------------------------------------------------------------
"""

_CROP_PRODUCTION_RICE = """Rice Area Harvested, Yield, and Production - States and United States: 2025 and Forecasted
November 1, 2026
-------------------------------------------------------------------------------------------------
              :   Area harvested    :            Yield per acre            :    Production 1/
              :----------------------------------------------------------------------------------
     State    :          :          :            :          2026           :          :
              :   2025   :   2026   :    2025    :-------------------------:   2025   :   2026
              :          :          :            : October 1  : November 1 :          :
-------------------------------------------------------------------------------------------------
              :     1,000 acres         ------------ pounds -----------      ---- 1,000 cwt ---
              :
Arkansas ........:  1,200       900       7,600        7,700        7,700       91,200     69,300
United States :  2,740      2,057       7,544        7,668        7,664      206,707    157,648
-------------------------------------------------------------------------------------------------
"""


def test_parse_crop_production_text_extracts_us_rows() -> None:
    values = parse_crop_production_text(_CROP_PRODUCTION_CORN + _CROP_PRODUCTION_RICE)
    by_key = {
        (v["commodity"], v["metric"], v["year"], v.get("forecast")): v["value"]
        for v in values
    }
    assert by_key[("Corn", "production", 2026, None)] == "15893419"
    assert by_key[("Corn", "production", 2025, None)] == "16963628"
    assert by_key[("Corn", "area_harvested", 2026, None)] == "88506"
    assert by_key[("Corn", "yield", 2026, "November 1, 2026")] == "179.6"
    assert by_key[("Corn", "yield", 2026, "October 1, 2026")] == "181.2"
    assert by_key[("Corn", "yield", 2025, None)] == "186.5"
    # Rice uses different units, read from its own units line.
    assert by_key[("Rice", "production", 2026, None)] == "157648"
    assert by_key[("Rice", "yield", 2026, "November 1, 2026")] == "7664"
    rice_yield = [v for v in values if v["commodity"] == "Rice" and v["metric"] == "yield"][0]
    assert rice_yield["unit"] == "pounds per acre"
    rice_prod = [v for v in values if v["commodity"] == "Rice" and v["metric"] == "production"][0]
    assert rice_prod["unit"] == "thousand cwt"
    corn_prod = [v for v in values if v["commodity"] == "Corn" and v["metric"] == "production"][0]
    assert corn_prod["unit"] == "thousand bushels"
    assert all(v["forecast_date"] == "November 1, 2026" for v in values)
    assert all(v["source"] == "USDA NASS Crop Production" for v in values)
    # State rows are ignored: no Iowa / Arkansas values in the output.
    assert "2803200" not in {v["value"] for v in values}
    assert "69300" not in {v["value"] for v in values}


def test_parse_crop_production_text_returns_nothing_for_bad_input() -> None:
    assert parse_crop_production_text("") == []
    assert parse_crop_production_text("Crop Production\nCorn production is forecast at 15.9 billion bushels.\n") == []
    # Heading present but the United States row is missing -> nothing.
    assert parse_crop_production_text(
        "Corn for Grain Area Harvested, Yield, and Production - States and United States: 2025 and\n"
        "Forecasted November 1, 2026\n"
        "Iowa ............: 13,150    12,800     210.0       219.0       219.0     2,761,500  2,803,200\n"
    ) == []


def test_parse_crop_production_text_skips_incomplete_us_row() -> None:
    # A United States row with a blank cell (fewer than 7 numbers)
    # must be skipped, never positionally guessed.
    text = _CROP_PRODUCTION_CORN.replace(
        "United States ...: 90,948    88,506     186.5       181.2       179.6    16,963,628 15,893,419",
        "United States ...: 90,948    88,506     186.5       181.2               16,963,628 15,893,419",
    )
    assert parse_crop_production_text(text) == []
