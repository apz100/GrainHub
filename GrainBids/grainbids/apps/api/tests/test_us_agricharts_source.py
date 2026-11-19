"""us_agricharts_source tests — Cycle 12 month-name delivery-label fix.

Cycle 11 found West-Con's /markets/cash.php serves 84 static
writeBidRow rows whose delivery start/end are month-name labels
('Dec 2026', 'Jan 2027'), not MM/DD/YYYY — and the old
_WRITEBIDROW_RX matched 0/84. Cycle 12 extended the regex to accept
month-name labels (full/abbreviated month, 4-digit or 2-digit year)
alongside MM/DD/YYYY. Month-only windows are kept VERBATIM in the
Delivery / Delivery End columns: no day is invented and no century is
expanded for 2-digit years.

All fixtures below are synthetic with invented values; no live
fetching inside pytest. The saved-HTML row-count tests read the
Cycle 11 / Cycle 12 captures in /tmp (structure only — counts and
labels, no prices) and skip when the captures are absent.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import us_agricharts_source as ag  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
WESTCON_SAVED = Path("/tmp/cycle11/westcon_cash.html")
WDCOOP_SAVED = Path("/tmp/cycle12/wdcoop_cash.html")


def _row(name="CORN", basis=-25, rounding=1, start="12/01/2026",
         end="12/31/2026", symbol="ZCZ26", weight=56) -> str:
    return (
        f"writeBidRow('{name}',{basis},false,false,false,{rounding},"
        f"'{start}','{end}','All','&nbsp;','&nbsp;',"
        f"{weight},'odd','c=1300&l=1631&d=Z26',quotes['{symbol}'], "
        f"0-0, false, false, false,'AG_ONLY');"
    )


def test_month_name_labels_parse() -> None:
    """Abbreviated and full month labels with a 4-digit year (West-Con shape)."""
    html = "\n".join([
        _row(start="Dec 2026", end="Dec 2026"),
        _row(name="SOYBEANS", basis=10, start="January 2027",
             end="January 2027", symbol="ZSF27", weight=60),
        _row(name="SOYBEANS", basis=12, start="September 2027",
             end="September 2027", symbol="ZSU27", weight=60),
    ])
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 3
    assert [(m.group(3), m.group(4)) for m in ms] == [
        ("Dec 2026", "Dec 2026"),
        ("January 2027", "January 2027"),
        ("September 2027", "September 2027"),
    ]


def test_short_month_labels_parse() -> None:
    """Month + 2-digit year ('Nov 26') as served by Wheaton Dumont."""
    html = "\n".join([
        _row(start="Nov 26", end="Nov 26"),
        _row(name="SOYBEANS", basis=10, start="Oct 27", end="Nov 27",
             symbol="ZSN27", weight=60),
    ])
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 2
    assert [(m.group(3), m.group(4)) for m in ms] == [
        ("Nov 26", "Nov 26"),
        ("Oct 27", "Nov 27"),
    ]


def test_mmddyyyy_still_parses() -> None:
    """Regression: the original MM/DD/YYYY form is untouched."""
    html = _row(start="12/01/2026", end="01/15/2027")
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 1
    assert (ms[0].group(3), ms[0].group(4)) == ("12/01/2026", "01/15/2027")
    assert ms[0].group(1) == "CORN"
    assert ms[0].group(2) == "-25"
    assert ms[0].group(7) == "ZCZ26"


def test_mixed_page_all_forms() -> None:
    """MM/DD/YYYY, month-name, and short-month rows on one page."""
    html = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 4
    assert [(m.group(3), m.group(4)) for m in ms] == [
        ("12/01/2026", "12/31/2026"),
        ("Dec 2026", "Dec 2026"),
        ("January 2027", "January 2027"),
        ("Nov 26", "Dec 26"),
    ]
    # The writeBidRow() JS definition line must not match.
    assert not any("name" in m.group(1) for m in ms)


def test_fetch_keeps_month_labels_verbatim() -> None:
    """End-to-end (mocked HTTP): month labels reach the DataFrame verbatim.

    No day is invented for a month-only window and no century is
    expanded for a 2-digit year — the label itself is the delivery.
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    jsquote = (
        "var quotes={'ZCZ26':{name:'Corn',month:'Dec 26',last:'450'},"
        "'ZSF27':{name:'Soybeans',month:'Jan 27',last:'1100'},"
        "'ZSN27':{name:'Soybeans',month:'Nov 26',last:'1050'}};"
    )

    class _Resp:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url, params=None, headers=None, timeout=None):
        if "jsquote" in url:
            return _Resp(jsquote)
        return _Resp(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert df["Delivery"].tolist() == [
        "12/01/2026", "Dec 2026", "January 2027", "Nov 26",
    ]
    assert df["Delivery End"].tolist() == [
        "12/31/2026", "Dec 2026", "January 2027", "Dec 26",
    ]
    assert set(df["Location"].tolist()) == {"Test Elevator - Riverside"}
    # Cash math still works off the mocked futures last: 450 + (-25) = 425c.
    assert df["Bushel Cash Price"].tolist()[0] == "$4.25"
    assert df["Bushel Cash Price"].tolist()[2] == "$11.10"


@pytest.mark.skipif(not WESTCON_SAVED.exists(),
                    reason="Cycle 11 saved West-Con HTML not present")
def test_westcon_saved_html_row_count() -> None:
    """Structure only: the fixed regex matches all 84 saved West-Con rows."""
    html = WESTCON_SAVED.read_text(encoding="utf-8")
    assert html.count("writeBidRow('") == 84
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 84
    assert len({m.group(3) for m in ms}) == 10  # distinct month labels
    assert {m.group(1) for m in ms} == {
        "CORN", "SOYBEANS", "DNS WHEAT (Milling Quality)",
    }
    assert all(m.group(3) == m.group(4) for m in ms)  # single-month rows


@pytest.mark.skipif(not WDCOOP_SAVED.exists(),
                    reason="Cycle 12 saved Wheaton Dumont HTML not present")
def test_wdcoop_saved_html_row_count() -> None:
    """Structure only: the fixed regex matches all 43 saved Wheaton Dumont rows."""
    html = WDCOOP_SAVED.read_text(encoding="utf-8")
    assert html.count("writeBidRow('") == 43
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 43
    assert len({m.group(3) for m in ms}) == 6  # distinct short month labels
    assert {m.group(1).strip() for m in ms} == {
        "Corn", "Soybeans", "Spring Wheat",
    }


# ─── Cycle 22 — Heritage: escaped-quote notes + commodity <h4> headings ───

HERITAGE_FIXTURE = FIXTURES / "us_agricharts_heritage_sample.html"
HERITAGE_SAVED = Path("/tmp/cycle22/heritage_cash.html")


def test_escaped_quote_notes_parse() -> None:
    """Cycle 22: forward-month rows whose notes hold 'DEC \\'26' parse.

    Before the fix the group/notes `'[^']*'` stopped at the escaped
    quote and the whole row failed to match — 11 of 14 Heritage rows
    were skipped. The fixture's escaped-quote rows must all match.
    """
    html = HERITAGE_FIXTURE.read_text(encoding="utf-8")
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 4
    assert [m.group(1) for m in ms] == [
        "CORN - CASH", "BEANS - DEC 2026", "CORN - JAN 2027", "SOYBEANS",
    ]
    assert [m.group(7) for m in ms] == ["ZCZ26", "ZSF27", "ZCH27", "ZSF27"]


def test_is_commodity_heading() -> None:
    """Cycle 22: h4-as-commodity detection, with location names kept out."""
    # Exact match with the row's commodity name (Heritage shape).
    assert ag._is_commodity_heading("CORN - DEC 2026", "CORN - DEC 2026")
    assert ag._is_commodity_heading("corn - cash", "CORN - CASH")
    # Starts with a commodity word, even if it differs from the row name.
    assert ag._is_commodity_heading("BEANS - CASH", "BEANS - DEC 2026")
    assert ag._is_commodity_heading("WHEAT", "WHEAT - JUL 2027")
    # Real locations are never commodity headings — the word boundary
    # keeps place names that merely start with a commodity word out.
    assert not ag._is_commodity_heading("Riverside", "CORN")
    assert not ag._is_commodity_heading("Wheatland", "WHEAT")
    assert not ag._is_commodity_heading("Cornwall", "CORN")
    assert not ag._is_commodity_heading("Garfield", "SOYBEANS")


def test_commodity_h4_falls_back_to_company() -> None:
    """Cycle 22 end-to-end (mocked HTTP): commodity <h4>s are not locations.

    Rows under a commodity heading fall back to the company name
    ('Test Elevator - Test Elevator', the West-Con fallback shape),
    while a genuine location heading ('Riverside') is still used.
    """
    page = HERITAGE_FIXTURE.read_text(encoding="utf-8")
    jsquote = (
        "var quotes={'ZCZ26':{name:'Corn',month:'Dec 26',last:'450'},"
        "'ZSF27':{name:'Soybeans',month:'Jan 27',last:'1100'},"
        "'ZCH27':{name:'Corn',month:'Mar 27',last:'460'}};"
    )

    class _Resp:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def _fake_get(url, params=None, headers=None, timeout=None):
        if "jsquote" in url:
            return _Resp(jsquote)
        return _Resp(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert df["Name"].tolist() == [
        "CORN - CASH", "BEANS - DEC 2026", "CORN - JAN 2027", "SOYBEANS",
    ]
    assert df["Location"].tolist() == [
        "Test Elevator - Test Elevator",
        "Test Elevator - Test Elevator",
        "Test Elevator - Test Elevator",
        "Test Elevator - Riverside",
    ]
    # No location value is a commodity name any more.
    assert not any("CORN" in loc or "BEANS" in loc for loc in df["Location"])


@pytest.mark.skipif(not HERITAGE_SAVED.exists(),
                    reason="Cycle 22 saved Heritage HTML not present")
def test_heritage_saved_html_row_count() -> None:
    """Structure only: the fixed regex matches all 14 saved Heritage rows.

    Cycle 21's live wrapper call returned 3 rows; the Cycle 22 capture
    (/tmp/cycle22/heritage_cash.html, 1 direct GET) holds 14 writeBidRow
    data calls under 14 commodity <h4> headings — the other 11 were
    skipped pre-fix because their notes argument holds an escaped quote
    ('DEC \\'26'). Counts and labels only, no prices.
    """
    html = HERITAGE_SAVED.read_text(encoding="utf-8")
    assert html.count("writeBidRow('") == 14
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 14
    assert {m.group(1) for m in ms} == {
        "CORN - CASH", "BEANS - CASH", "WHEAT - CASH",
        "CORN - DEC 2026", "BEANS - DEC 2026",
        "CORN - JAN 2027", "BEANS - JAN 2027",
        "CORN - FEB 2027", "BEANS - FEB 2027",
        "CORN - MAR 2027", "BEANS - MAR 2027",
        "CORN - FALL 2027", "BEANS - FALL 2027",
        "WHEAT - JUL 2027",
    }
    h4s = ag._H4_RX.findall(html)
    assert len(h4s) == 14
    # Every <h4> is a commodity heading, not a location: each equals
    # its row's commodity name.
    assert set(h4s) == {m.group(1) for m in ms}
    # The jsquote tag lists a symbol for every row.
    jm = ag._JSQUOTE_SCRIPT_RX.search(html)
    assert jm is not None
    assert {m.group(7) for m in ms} <= set(jm.group(2).split(","))
    # All deliveries are full MM/DD/YYYY windows (7 distinct starts).
    assert {m.group(3) for m in ms} == {
        "10/01/2026", "12/01/2026", "01/01/2027", "02/01/2027",
        "03/01/2027", "07/01/2027", "09/01/2027",
    }
