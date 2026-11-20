from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources.usda_mirror_source import (  # noqa: E402
    FS_GRAIN_URL,
    JAMES_VALLEY_URL,
    fetch_usda_mirror,
    parse_usda_mirror_html,
    usda_mirror_history_url,
)

# Synthetic fixture modelled on the verified live page structure
# (table.table-condensed, 7 columns, colspan=7 section rows, the
# <select name="id"> archive form). Values are synthetic except where
# noted as verbatim from the live page fetched 2026-11-19.
FIXTURE_HTML = """<html><head><title>James Valley Grain, LLC - USDA Daily Cash Bids</title></head>
<body>
<form class="form-inline" action="/pages/usdacash.php" method="GET">
<label class="control-label" for="id">USDA Cash Bid Report for</label>
<select class="form-control" id="id" name="id" onchange="this.form.submit();">
<option selected="" value="7730">Nov 18, 2026</option>
<option value="7729">Nov 17, 2026</option>
<option value="7728">Nov 16, 2026</option>
</select></form>
<table class="table table-condensed">
<tr><th>Commodity</th><th>Type</th><th>Low Price</th><th>High Price</th>
<th>Price Chg. (cents)</th><th>Basis (cents)</th><th>Bid Chg. (cents)</th></tr>
<tr><td colspan="7">Central</td></tr>
<tr><td>Corn</td><td>Processor</td><td>+5.10</td><td>+5.25</td><td>+0.08</td><td>+75.00 Z</td><td>UNCH</td></tr>
<tr><td>Soybeans</td><td>Mills and Processors</td><td>+12.40</td><td>+12.40</td><td>UNCH</td><td></td><td>UNCH</td></tr>
<tr><td colspan="7">Gulf Coast Ports - LA</td></tr>
<tr><td>Soybeans</td><td>Export</td><td>+13.28</td><td>+13.28</td><td>+0.07</td><td>+110.00 F</td><td>UNCH</td></tr>
<tr><td>Corn</td><td>Export</td><td>+5.36</td><td>+5.38</td><td>+0.10</td><td>+99.00 Z to +101.00 Z</td><td>UNCH</td></tr>
<tr><td colspan="7">Pacific Ports</td></tr>
<tr><td>Wheat</td><td>Export</td><td>+6.47</td><td>+6.52</td><td>+0.21</td><td>+35.00 Z to +40.00 Z</td><td>UNCH</td></tr>
<tr><td>White Oats</td><td>Export</td><td>+260.00</td><td>+260.00</td><td>UNCH</td><td>+0.00</td><td>UNCH</td></tr>
</table></body></html>
"""


def test_parse_assigns_region_sections() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    assert out["status"] == "ok"
    by_region = {}
    for row in out["rows"]:
        by_region.setdefault(row["region"], []).append(row["commodity"])
    assert by_region["Central"] == ["Corn", "Soybeans"]
    assert by_region["Gulf Coast Ports - LA"] == ["Soybeans", "Corn"]
    assert by_region["Pacific Ports"] == ["Wheat", "Oats"]
    assert out["company"] == "James Valley Grain"
    assert out["location"] == "United States"
    assert all(row["currency"] == "USD" for row in out["rows"])


def test_parse_gulf_coast_rows_verbatim_values() -> None:
    # The Gulf soybeans row below is verbatim from the live page
    # fetched 2026-11-19 (report 7730, Nov 18, 2026).
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    gulf = [r for r in out["rows"] if r["region"] == "Gulf Coast Ports - LA"]
    soy = gulf[0]
    assert soy["commodity"] == "Soybeans"
    assert soy["bid_type"] == "Export"
    assert soy["cash_price"] == 13.28
    assert soy["low_price"] == 13.28 and soy["high_price"] == 13.28
    assert soy["basis"] == "+110.00 F"
    assert soy["basis_cents"] == 110.0
    assert soy["basis_high_cents"] == 110.0
    assert soy["basis_month"] == "F"
    assert soy["unit"] == "$/bu"


def test_parse_pacific_ports_rows_and_basis_range() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    pnw = [r for r in out["rows"] if r["region"] == "Pacific Ports"]
    wheat = pnw[0]
    assert wheat["commodity"] == "Wheat"
    assert wheat["cash_price"] == 6.47  # low end of the printed range
    assert wheat["high_price"] == 6.52
    assert wheat["basis_cents"] == 35.0
    assert wheat["basis_high_cents"] == 40.0
    assert wheat["basis_month"] == "Z"
    corn = [r for r in out["rows"] if r["region"] == "Gulf Coast Ports - LA"][1]
    assert corn["basis_cents"] == 99.0
    assert corn["basis_high_cents"] == 101.0


def test_parse_missing_basis_is_none_not_zero() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    central_soy = [r for r in out["rows"] if r["region"] == "Central"][1]
    assert central_soy["basis"] is None
    assert central_soy["basis_cents"] is None
    assert central_soy["basis_high_cents"] is None
    assert central_soy["basis_month"] is None
    assert central_soy["cash_price"] == 12.4  # row kept: price present
    # A basis of +0.00 is a real zero, not missing.
    oats = [r for r in out["rows"] if r["commodity"] == "Oats"][0]
    assert oats["basis_cents"] == 0.0


def test_parse_oats_unit_inference_by_magnitude() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    oats = [r for r in out["rows"] if r["commodity"] == "Oats"][0]
    assert oats["cash_price"] == 260.0
    assert oats["unit"] == "cents/bu"  # cents-scale print, not $260/bu
    corn = [r for r in out["rows"] if r["commodity"] == "Corn"][0]
    assert corn["unit"] == "$/bu"


def test_parse_history_select_and_report_id() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url=JAMES_VALLEY_URL)
    assert out["report_id"] == "7730"
    assert out["report_date"] == "Nov 18, 2026"
    assert out["history"] == [
        {"id": "7730", "date": "Nov 18, 2026"},
        {"id": "7729", "date": "Nov 17, 2026"},
        {"id": "7728", "date": "Nov 16, 2026"},
    ]
    assert all(r["report_id"] == "7730" for r in out["rows"])
    assert usda_mirror_history_url(JAMES_VALLEY_URL, 7729) == (
        "https://jamesvalleygrain.com/pages/usdacash.php?id=7729"
    )
    assert usda_mirror_history_url(FS_GRAIN_URL, "7728") == (
        "https://www.fsgrain.com/pages/usdacash.php?id=7728"
    )


def test_parse_rows_before_first_section_have_no_region() -> None:
    # The live page puts 12 data rows before the first section row;
    # the parser must not invent a region for them.
    html = FIXTURE_HTML.replace(
        '<tr><td colspan="7">Central</td></tr>\n', "", 1
    )
    out = parse_usda_mirror_html(html, url=JAMES_VALLEY_URL)
    assert out["status"] == "ok"
    assert out["rows"][0]["region"] is None
    assert out["rows"][0]["commodity"] == "Corn"


def test_parse_empty_table_reports_empty() -> None:
    html = """<html><head><title>FS Grain - USDA Daily Cash Bids</title></head><body>
    <table class="table table-condensed">
    <tr><th>Commodity</th><th>Type</th><th>Low Price</th><th>High Price</th>
    <th>Price Chg. (cents)</th><th>Basis (cents)</th><th>Bid Chg. (cents)</th></tr>
    </table></body></html>"""
    out = parse_usda_mirror_html(html, url=FS_GRAIN_URL)
    assert out["status"] == "empty"
    assert out["rows"] == []
    assert out["company"] == "FS Grain"


def test_parse_no_table_reports_unsupported() -> None:
    out = parse_usda_mirror_html("<html><body><p>Daily Cash Bids</p></body></html>", url=JAMES_VALLEY_URL)
    assert out["status"] == "unsupported"
    assert out["rows"] == []
    assert out["company"] == "James Valley Grain"
    assert parse_usda_mirror_html("")["status"] == "unsupported"


def test_parse_company_falls_back_to_page_title() -> None:
    out = parse_usda_mirror_html(FIXTURE_HTML, url="https://example.com/pages/usdacash.php")
    assert out["company"] == "James Valley Grain, LLC"


def test_parse_skips_rows_with_no_price_and_no_basis() -> None:
    html = FIXTURE_HTML.replace(
        "<td>+5.10</td><td>+5.25</td><td>+0.08</td><td>+75.00 Z</td>",
        "<td>UNCH</td><td>UNCH</td><td>UNCH</td><td>UNCH</td>",
    )
    out = parse_usda_mirror_html(html, url=JAMES_VALLEY_URL)
    assert out["status"] == "ok"
    assert not any(
        r["region"] == "Central" and r["commodity"] == "Corn" for r in out["rows"]
    )


def test_fetch_usda_mirror_uses_one_get(monkeypatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        status_code = 200
        text = FIXTURE_HTML

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **kwargs) -> FakeResponse:
        calls.append(url)
        assert kwargs["headers"]["User-Agent"].startswith("GrainHub-Research/")
        return FakeResponse()

    monkeypatch.setattr(
        "app.platform.market_data.sources.usda_mirror_source.requests.get", fake_get
    )
    out = fetch_usda_mirror(JAMES_VALLEY_URL)
    assert calls == [JAMES_VALLEY_URL]
    assert out["status"] == "ok"
    assert len(out["rows"]) == 6
    assert out["report_id"] == "7730"
