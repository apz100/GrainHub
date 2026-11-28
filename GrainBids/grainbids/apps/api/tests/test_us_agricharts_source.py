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
import requests

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


# ─── Cycle 24 — basis-only fallback when the jsquote tag is missing ───
# Option (a), FMN precedent: a page with no jsquote.php script tag no
# longer returns empty before parsing. Rows parse as basis-only:
# Basis / Delivery / Location / Name / Symbol filled, Futures Month
# decoded from the contract symbol, Futures Price / Change / cash
# None with a Note, never invented. A page WITH the tag is unchanged.

_NO_TAG_NOTE_FRAGMENT = "jsquote.php"


def _strip_jsquote_tag(html: str) -> str:
    """Remove the jsquote <script src> line, keeping the writeBidRow rows."""
    lines = [ln for ln in html.splitlines() if "jsquote.php" not in ln]
    return "\n".join(lines)


class _Resp24:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_no_jsquote_tag_returns_basis_only_rows() -> None:
    """Cycle 24 (a): no jsquote tag → rows still parse, basis filled.

    Futures Price / Change / both cash prices are None with a Note
    (never invented), and no jsquote feed fetch is attempted at all
    — exactly one GET, for the page itself.
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    page_no_tag = _strip_jsquote_tag(page)
    assert "jsquote.php" not in page_no_tag
    assert page_no_tag.count("writeBidRow('") == 4

    called_urls: list[str] = []

    def _fake_get(url, params=None, headers=None, timeout=None):
        called_urls.append(url)
        return _Resp24(page_no_tag)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert called_urls == ["https://example.invalid/markets/cash.php"]
    # Basis (the per-elevator signal) survives, as published.
    assert df["Basis"].tolist() == ["-25", "-20", "+10", "+12"]
    assert df["Name"].tolist() == ["CORN", "CORN", "SOYBEANS", "SOYBEANS"]
    assert df["Delivery"].tolist() == [
        "12/01/2026", "Dec 2026", "January 2027", "Nov 26",
    ]
    assert set(df["Location"].tolist()) == {"Test Elevator - Riverside"}
    # Feed-dependent values are missing, not zero and not invented.
    for col in ("Futures Price", "Change", "Bushel Cash Price", "MT Cash Price"):
        assert df[col].map(lambda v: v is None).all(), col
        assert not (df[col] == "").any()
        assert not (df[col] == 0).any()
    # FMN-pattern note on every row.
    assert all(_NO_TAG_NOTE_FRAGMENT in (n or "") for n in df["Note"].tolist())
    assert all("never invented" in (n or "") for n in df["Note"].tolist())


def test_no_jsquote_tag_decodes_futures_month_from_symbol() -> None:
    """Cycle 24 (ii): Futures Month is decoded from the symbol, not None.

    ZCZ26 -> Dec 2026, ZSF27 -> Jan 2027, ZSN27 -> Jul 2027 — the
    same decoder as fmn_source.futures_month_from_symbol. (The
    feed's month for ZSN27 in the tagged fixture is 'Nov 26', a
    delivery label; the decoder returns the contract month.)
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    page_no_tag = _strip_jsquote_tag(page)

    with patch.object(ag.requests, "get", return_value=_Resp24(page_no_tag)):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert df["Futures Month"].tolist() == [
        "Dec 2026", "Dec 2026", "Jan 2027", "Jul 2027",
    ]


def test_futures_month_from_symbol_decoder() -> None:
    """Cycle 24: the symbol->month decoder itself (FMN decoder, reused)."""
    assert ag.futures_month_from_symbol("ZCZ26") == "Dec 2026"
    assert ag.futures_month_from_symbol("ZSF27") == "Jan 2027"
    assert ag.futures_month_from_symbol("ZSN27") == "Jul 2027"
    assert ag.futures_month_from_symbol("ZCH27") == "Mar 2027"
    assert ag.futures_month_from_symbol("MWU27") == "Sep 2027"
    assert ag.futures_month_from_symbol(None) is None
    assert ag.futures_month_from_symbol("") is None
    assert ag.futures_month_from_symbol("NOTASYMBOL") is None


def test_tagged_page_behaves_exactly_as_before() -> None:
    """Cycle 24 (c): regression guard — a page WITH the tag is unchanged.

    Futures + cash come from the mocked feed, Futures Month is the
    feed's month verbatim, and the Note column is empty (no
    degradation note). Same values as the Cycle 12 tagged test.
    Cycle 25: also asserts both GETs happen (page + jsquote feed),
    distinguishing the with-data path from the degraded paths, which
    fetch the feed and get nothing (Cycle 25) or never fetch it
    (Cycle 24 no-tag).
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    jsquote = (
        "var quotes={'ZCZ26':{name:'Corn',month:'Dec 26',last:'450'},"
        "'ZSF27':{name:'Soybeans',month:'Jan 27',last:'1100'},"
        "'ZSN27':{name:'Soybeans',month:'Nov 26',last:'1050'}};"
    )

    called_urls: list[str] = []

    def _fake_get(url, params=None, headers=None, timeout=None):
        called_urls.append(url)
        if "jsquote" in url:
            return _Resp24(jsquote)
        return _Resp24(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert called_urls == [
        "https://example.invalid/markets/cash.php",
        "https://www.agricharts.com/marketdata/jsquote.php",
    ]
    assert df["Futures Price"].tolist() == ["450", "450", "1100", "1050"]
    assert df["Futures Month"].tolist() == ["Dec 26", "Dec 26", "Jan 27", "Nov 26"]
    assert df["Bushel Cash Price"].tolist()[0] == "$4.25"
    assert df["Bushel Cash Price"].tolist()[2] == "$11.10"
    assert df["Note"].tolist() == ["", "", "", ""]
    assert df["Basis"].tolist() == ["-25", "-20", "+10", "+12"]


def test_no_tag_page_with_no_rows_still_empty() -> None:
    """Cycle 24: no tag AND no writeBidRow rows → empty, not a crash."""
    page = "<html><body><h4>Testville</h4><p>No bids today.</p></body></html>"

    with patch.object(ag.requests, "get", return_value=_Resp24(page)):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert df.empty


# ─── Cycle 25 — feed-down degradation (design §9 scope note) ───
# Tag IS present but the jsquote feed returns no data (empty quotes)
# degrades the same way as the Cycle 24 no-tag path: rows parse as
# basis-only, Futures Month decoded from the symbol, Futures Price /
# Change / cash None with a Note, never invented. Tag-present-with-
# data behaviour is unchanged (see the extended regression guard
# in test_tagged_page_behaves_exactly_as_before below).


@pytest.mark.parametrize(
    "empty_feed",
    [
        "var quotes = null;",  # the empty-feed body observed live (Cycle 24 §9)
        "var quotes={};",
    ],
)
def test_tag_present_feed_empty_returns_basis_only_rows(empty_feed: str) -> None:
    """Cycle 25 (a): tag present + feed returns no data → basis-only rows.

    Same values as the no-tag test, except the feed IS fetched (two
    GETs: page + jsquote) — the tag is present, it just yields
    nothing. Basis / Delivery / Location / Name filled, Futures
    Month decoded from the symbol, feed-dependent values None
    with a Note, never invented.
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    assert "jsquote.php" in page
    assert page.count("writeBidRow('") == 4

    called_urls: list[str] = []

    def _fake_get(url, params=None, headers=None, timeout=None):
        called_urls.append(url)
        if "jsquote" in url:
            return _Resp24(empty_feed)
        return _Resp24(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert called_urls == [
        "https://example.invalid/markets/cash.php",
        "https://www.agricharts.com/marketdata/jsquote.php",
    ]
    assert df["Basis"].tolist() == ["-25", "-20", "+10", "+12"]
    assert df["Name"].tolist() == ["CORN", "CORN", "SOYBEANS", "SOYBEANS"]
    assert df["Delivery"].tolist() == [
        "12/01/2026", "Dec 2026", "January 2027", "Nov 26",
    ]
    assert set(df["Location"].tolist()) == {"Test Elevator - Riverside"}
    # Futures Month decoded from the symbol, as on the no-tag path.
    assert df["Futures Month"].tolist() == [
        "Dec 2026", "Dec 2026", "Jan 2027", "Jul 2027",
    ]
    # Feed-dependent values are missing, not zero and not invented.
    for col in ("Futures Price", "Change", "Bushel Cash Price", "MT Cash Price"):
        assert df[col].map(lambda v: v is None).all(), col
        assert not (df[col] == "").any()
        assert not (df[col] == 0).any()
    assert all(_NO_TAG_NOTE_FRAGMENT in (n or "") for n in df["Note"].tolist())
    assert all("never invented" in (n or "") for n in df["Note"].tolist())


# ─── Cycle 26 — feed-fetch-raise degradation ───
# Tag IS present and the jsquote feed fetch itself RAISES (HTTP
# error, timeout, any exception from _fetch_jsquote): the
# collector degrades exactly like the Cycle 24 no-tag and Cycle 25
# empty-feed paths — rows parse as basis-only, Futures Month
# decoded from the symbol, Futures Price / Change / cash None
# with a Note, never invented. The page fetch itself failing is
# different: with no HTML there is nothing to parse, so the
# collector still returns an empty DataFrame (outer except).


@pytest.mark.parametrize(
    "feed_error",
    [
        requests.exceptions.HTTPError("503 Service Unavailable"),
        requests.exceptions.ConnectTimeout("connect timed out"),
        requests.exceptions.ReadTimeout("read timed out"),
    ],
)
def test_tag_present_feed_fetch_raises_returns_basis_only_rows(
    feed_error: Exception,
) -> None:
    """Cycle 26 (a): tag present + feed fetch raises → basis-only rows.

    Same values as the no-tag / empty-feed tests, except the feed
    fetch raises instead of returning empty: two GETs are attempted
    (page + jsquote), the second raises, and the rows still parse.
    Basis / Delivery / Location / Name filled, Futures Month
    decoded from the symbol, feed-dependent values None with a
    Note, never invented.
    """
    page = (FIXTURES / "us_agricharts_mixed_sample.html").read_text(encoding="utf-8")
    assert "jsquote.php" in page
    assert page.count("writeBidRow('") == 4

    called_urls: list[str] = []

    def _fake_get(url, params=None, headers=None, timeout=None):
        called_urls.append(url)
        if "jsquote" in url:
            raise feed_error
        return _Resp24(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert len(df) == 4
    assert called_urls == [
        "https://example.invalid/markets/cash.php",
        "https://www.agricharts.com/marketdata/jsquote.php",
    ]
    assert df["Basis"].tolist() == ["-25", "-20", "+10", "+12"]
    assert df["Name"].tolist() == ["CORN", "CORN", "SOYBEANS", "SOYBEANS"]
    assert df["Delivery"].tolist() == [
        "12/01/2026", "Dec 2026", "January 2027", "Nov 26",
    ]
    assert set(df["Location"].tolist()) == {"Test Elevator - Riverside"}
    # Futures Month decoded from the symbol, as on the no-tag path.
    assert df["Futures Month"].tolist() == [
        "Dec 2026", "Dec 2026", "Jan 2027", "Jul 2027",
    ]
    # Feed-dependent values are missing, not zero and not invented.
    for col in ("Futures Price", "Change", "Bushel Cash Price", "MT Cash Price"):
        assert df[col].map(lambda v: v is None).all(), col
        assert not (df[col] == "").any()
        assert not (df[col] == 0).any()
    assert all(_NO_TAG_NOTE_FRAGMENT in (n or "") for n in df["Note"].tolist())
    assert all("never invented" in (n or "") for n in df["Note"].tolist())


@pytest.mark.parametrize(
    "page_error",
    [
        requests.exceptions.HTTPError("500 Internal Server Error"),
        requests.exceptions.ConnectTimeout("connect timed out"),
    ],
)
def test_page_fetch_raises_still_returns_empty(page_error: Exception) -> None:
    """Cycle 26 (b): the page fetch itself raises → empty, no crash.

    A failed page fetch leaves no HTML to parse, so there are no
    rows to degrade to — the outer except returns an empty
    DataFrame, exactly as before Cycle 26. No invented rows, no
    exception escaping to the caller.
    """
    def _fake_get(url, params=None, headers=None, timeout=None):
        raise page_error

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://example.invalid/markets/cash.php", "Test Elevator"
        )

    assert df.empty


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


# ─── Farmbucks batch (2026-11-28) — Pilgrim's Gold'n Plump ───────────────
# Recorded live fixture (tests/fixtures/us_agricharts_pilgrims_sample.html):
# the <h4> location headings, writeBidRow() data calls and jsquote.php
# script tag trimmed from https://gnpcograin.com/markets/cash.php, kept
# in document order. Values are the live bids at capture time (2026-11-28),
# not invented test data. The jsquote feed is mocked with the live quotes
# the page's symbols resolved to at capture time.

PILGRIMS_SAVED = FIXTURES / "us_agricharts_pilgrims_sample.html"

# Live jsquote values at capture (2026-11-28): ZCH27 Mar 2027 463,
# ZCK27 May 2027 472.75, ZCN27 Jul 2027 480.5, ZCZ27 Dec 2027 491.
_PILGRIMS_JSQUOTE = (
    "var quotes={'ZCH27':{name:'Corn',month:'March 2027',last:'463'},"
    "'ZCK27':{name:'Corn',month:'May 2027',last:'472.75'},"
    "'ZCN27':{name:'Corn',month:'July 2027',last:'480.5'},"
    "'ZCZ27':{name:'Corn',month:'December 2027',last:'491'}};"
)


def test_pilgrims_saved_html_row_count() -> None:
    """Structure only: the regex matches all 12 saved Pilgrims rows."""
    html = PILGRIMS_SAVED.read_text(encoding="utf-8")
    assert html.count("writeBidRow('") == 12
    ms = list(ag._WRITEBIDROW_RX.finditer(html))
    assert len(ms) == 12
    assert {m.group(1) for m in ms} == {"Corn"}
    # Two <h4> location headings, one per 6-row block, in order.
    assert ag._H4_RX.findall(html) == ["Arcadia", "Sauk Rapids"]
    # The jsquote tag lists a symbol for every row.
    jm = ag._JSQUOTE_SCRIPT_RX.search(html)
    assert jm is not None
    assert {m.group(7) for m in ms} == {"ZCH27", "ZCK27", "ZCN27", "ZCZ27"}
    assert {m.group(7) for m in ms} <= set(jm.group(2).split(","))
    # All deliveries are full MM/DD/YYYY windows (6 distinct starts).
    assert {m.group(3) for m in ms} == {
        "11/01/2026", "12/01/2026", "01/01/2027",
        "04/01/2027", "06/01/2027", "10/01/2027",
    }


def test_pilgrims_saved_html_fetch() -> None:
    """Full fetch against the recorded fixture: 12 rows, 2 locations,
    cash prices derived from the mocked live jsquote feed, USD/bu."""
    page = PILGRIMS_SAVED.read_text(encoding="utf-8")

    def _fake_get(url, params=None, headers=None, timeout=None):
        if "jsquote" in url:
            return _Resp24(_PILGRIMS_JSQUOTE)
        return _Resp24(page)

    with patch.object(ag.requests, "get", side_effect=_fake_get):
        df = ag.fetch_us_agricharts(
            "https://gnpcograin.com/markets/cash.php", "Pilgrim's Gold'n Plump"
        )

    assert len(df) == 12
    assert df["Location"].tolist().count("Pilgrim's Gold'n Plump - Arcadia") == 6
    assert df["Location"].tolist().count("Pilgrim's Gold'n Plump - Sauk Rapids") == 6
    assert set(df["Name"]) == {"Corn"}
    assert df["Futures Month"].tolist() == [
        "March 2027", "March 2027", "March 2027",
        "May 2027", "July 2027", "December 2027",
    ] * 2
    assert df["Futures Price"].tolist() == [
        "463", "463", "463", "472.75", "480.5", "491",
    ] * 2
    # Basis -69 on 463 -> $3.94 (Arcadia Nov); -87 on 463 -> $3.76 (Sauk Rapids Nov).
    arcadia_nov = df[df["Location"] == "Pilgrim's Gold'n Plump - Arcadia"].iloc[0]
    assert arcadia_nov["Delivery"] == "11/01/2026"
    assert arcadia_nov["Delivery End"] == "11/30/2026"
    assert arcadia_nov["Basis"] == "-69"
    assert arcadia_nov["Bushel Cash Price"] == "$3.94"
    sauk_nov = df[df["Location"] == "Pilgrim's Gold'n Plump - Sauk Rapids"].iloc[0]
    assert sauk_nov["Basis"] == "-87"
    assert sauk_nov["Bushel Cash Price"] == "$3.76"
    assert df["Note"].tolist() == [""] * 12
