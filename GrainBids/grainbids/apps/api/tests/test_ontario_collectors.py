"""Tests for the Cycle 3 Ontario plain-HTML collectors.

All parsing tests run against saved synthetic fixtures in
tests/fixtures/ — no live fetching inside pytest. Fixture values are
invented test data, not live prices.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import collwest_source  # noqa: E402
from app.platform.market_data.sources import mae_mart_source  # noqa: E402
from app.platform.market_data.sources import mapleview_source  # noqa: E402
from app.platform.market_data.sources import north_gower_source  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Collwest
# ---------------------------------------------------------------------------


def test_collwest_parses_widget_rows() -> None:
    result = collwest_source.parse_collwest_html(_read("collwest_sample.html"))
    assert result["status"] == "ok"
    assert result["company"] == "Collwest Grain"
    assert result["location"] == "Collingwood"
    rows = result["rows"]
    assert len(rows) == 3  # oats row is all dashes -> skipped
    corn_2026 = next(
        r for r in rows if r["commodity"] == "Corn" and r["delivery_month"] == "2026 Crop"
    )
    assert corn_2026["cash_price"] == 5.11
    assert corn_2026["basis"] == 1.10
    assert corn_2026["futures_price"] == 4.01
    assert corn_2026["currency"] == "CAD"
    assert corn_2026["unit"] == "$/bu"
    assert corn_2026["cash_price_mt"] is None
    soy = next(r for r in rows if r["commodity"] == "Soybeans")
    assert soy["cash_price"] == 15.01
    assert soy["delivery_month"] == "2026 Crop"


def test_collwest_missing_widget_is_unsupported() -> None:
    result = collwest_source.parse_collwest_html("<html><body>no bids here</body></html>")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_collwest_fetch_uses_contact_user_agent() -> None:
    class _FakeResponse:
        text = "<html></html>"

        def raise_for_status(self) -> None:
            pass

    with patch("app.platform.market_data.sources.collwest_source.requests.get") as fake_get:
        fake_get.return_value = _FakeResponse()
        collwest_source.fetch_collwest_html()
    _, kwargs = fake_get.call_args
    assert kwargs["headers"]["User-Agent"] == collwest_source.CONTACT_USER_AGENT
    assert fake_get.call_args.args[0] == collwest_source.COLLWEST_URL


# ---------------------------------------------------------------------------
# Mae-Mart
# ---------------------------------------------------------------------------


def test_mae_mart_parses_basis_and_rye_cash() -> None:
    result = mae_mart_source.parse_mae_mart_html(_read("mae_mart_sample.html"))
    assert result["status"] == "ok"
    rows = result["rows"]
    assert len(rows) == 2
    corn = next(r for r in rows if r["commodity"] == "Corn")
    assert corn["delivery_month"] == "Harvest 2026"
    assert corn["basis"] == 1.25
    # Cash price is JS-rendered from the site's futures proxy: never guessed.
    assert corn["cash_price"] is None
    assert "futures proxy" in corn["note"]
    assert corn["currency"] == "CAD"
    rye = next(r for r in rows if r["commodity"] == "Rye")
    assert rye["delivery_month"] == "Current Bid"
    assert rye["basis"] == 0.0
    assert rye["cash_price"] == 6.11  # static manualPrice in ALL_BIDS JSON
    assert "manualPrice" in rye["note"]


def test_mae_mart_missing_tables_is_unsupported() -> None:
    result = mae_mart_source.parse_mae_mart_html("<html><body>no tables</body></html>")
    assert result["status"] == "unsupported"
    assert result["rows"] == []


# ---------------------------------------------------------------------------
# Mae-Mart futures proxy (Cycle 19 — proxy verified live, 1 GET)
# ---------------------------------------------------------------------------

# Synthetic proxy payloads: invented values, not live prices.
_SYNTHETIC_PROXY_JSON = {
    "ZCZ26=F": {"price": 450.25, "currency": "USX", "timestamp": 1000, "fetched": 1001},
    "ZSF27=F": {"price": 1075.25, "currency": "USX", "timestamp": 1000, "fetched": 1001},
    "ZWN27=F": {"price": 551.25, "currency": "USX", "timestamp": 1000, "fetched": 1001},
}


def _mae_mart_multi_crop_html() -> str:
    """Synthetic 4-crop page mirroring the fixture's structure.

    Corn/soy/wheat carry basis only (cash is JS-filled); rye has a
    static manualPrice. All values are invented test data.
    """
    tables = ""
    for table_id, delivery, basis in [
        ("gp-table-corn", "HARVEST 2026", "+1.2500"),
        ("gp-table-soybeans", "HARVEST 2026", "+0.7500"),
        ("gp-table-wheat", "HARVEST 2026", "+0.5000"),
        ("gp-table-rye", "Current Bid", "+0.0000"),
    ]:
        tables += (
            f'<table class="gp-table" id="{table_id}"><tbody>'
            f"<tr><td>Best Bid {delivery}</td><td>—</td><td>{basis}</td>"
            "<td>—</td><td>—</td><td>Lock a Bid</td></tr>"
            "</tbody></table>"
        )
    return (
        "<html><body>" + tables + "<script>"
        'var ALL_BIDS = {"corn":[{"symbol":"ZCZ26=F","basis":1.25,"manualPrice":null}],'
        '"soybeans":[{"symbol":"ZSF27=F","basis":0.75,"manualPrice":null}],'
        '"wheat":[{"symbol":"ZWN27=F","basis":0.5,"manualPrice":null}],'
        '"rye":[{"symbol":"","basis":0,"manualPrice":7.77}]};'
        "</script></body></html>"
    )


def test_mae_mart_proxy_json_cents_to_dollars() -> None:
    result = mae_mart_source.parse_mae_mart_proxy_json(_SYNTHETIC_PROXY_JSON)
    # USX = cents per the page's own rule: divide by 100.
    assert result == {"Corn": 4.5025, "Soybeans": 10.7525, "Wheat": 5.5125}


def test_mae_mart_proxy_json_ignores_bad_entries() -> None:
    data = {
        "ZCZ26=F": {"price": 400.0, "currency": "USD"},  # non-USX: as-is
        "ZSF27=F": {"price": "not-a-number", "currency": "USX"},
        "ZWN27=F": {"currency": "USX"},  # no price
        "ZZZ99=F": {"price": 1.0, "currency": "USX"},  # unknown symbol
        "BAD": "not-a-dict",
    }
    assert mae_mart_source.parse_mae_mart_proxy_json(data) == {"Corn": 400.0}
    assert mae_mart_source.parse_mae_mart_proxy_json({}) == {}
    assert mae_mart_source.parse_mae_mart_proxy_json(None) == {}  # type: ignore[arg-type]


def test_mae_mart_fetch_fills_futures_and_leaves_cash_empty() -> None:
    with (
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_html",
            return_value=_read("mae_mart_sample.html"),
        ),
        patch.object(
            mae_mart_source, "fetch_mae_mart_futures", return_value={"Corn": 4.50}
        ),
    ):
        result = mae_mart_source.fetch_mae_mart()
    assert result["status"] == "ok"
    corn = next(r for r in result["rows"] if r["commodity"] == "Corn")
    assert corn["futures_price"] == 4.50
    # Cash is NEVER computed from futures + basis here.
    assert corn["cash_price"] is None
    assert corn["basis"] == 1.25
    rye = next(r for r in result["rows"] if r["commodity"] == "Rye")
    assert rye["futures_price"] is None  # no symbol, no proxy call
    assert rye["cash_price"] == 6.11  # static manualPrice, untouched


def test_mae_mart_fetch_fills_all_three_futures_crops() -> None:
    with (
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_html",
            return_value=_mae_mart_multi_crop_html(),
        ),
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_futures",
            return_value={"Corn": 4.50, "Soybeans": 10.75, "Wheat": 5.51},
        ),
    ):
        result = mae_mart_source.fetch_mae_mart()
    assert result["status"] == "ok"
    assert len(result["rows"]) == 4
    by_crop = {r["commodity"]: r for r in result["rows"]}
    assert by_crop["Corn"]["futures_price"] == 4.50
    assert by_crop["Soybeans"]["futures_price"] == 10.75
    assert by_crop["Wheat"]["futures_price"] == 5.51
    assert by_crop["Rye"]["futures_price"] is None
    assert by_crop["Rye"]["cash_price"] == 7.77
    for crop in ("Corn", "Soybeans", "Wheat"):
        assert by_crop[crop]["cash_price"] is None


def test_mae_mart_proxy_failure_leaves_rows_unchanged() -> None:
    with (
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_html",
            return_value=_read("mae_mart_sample.html"),
        ),
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_futures",
            side_effect=Exception("proxy down"),
        ),
    ):
        result = mae_mart_source.fetch_mae_mart()
    assert result["status"] == "ok"
    corn = next(r for r in result["rows"] if r["commodity"] == "Corn")
    assert corn["futures_price"] is None
    assert corn["cash_price"] is None
    assert corn["basis"] == 1.25
    rye = next(r for r in result["rows"] if r["commodity"] == "Rye")
    assert rye["cash_price"] == 6.11
    assert any("proxy unavailable" in note for note in result["notes"])


def test_mae_mart_proxy_disabled_skips_proxy() -> None:
    with (
        patch.object(
            mae_mart_source,
            "fetch_mae_mart_html",
            return_value=_read("mae_mart_sample.html"),
        ),
        patch.object(
            mae_mart_source, "fetch_mae_mart_futures"
        ) as fake_futures,
    ):
        result = mae_mart_source.fetch_mae_mart(include_futures=False)
    fake_futures.assert_not_called()
    corn = next(r for r in result["rows"] if r["commodity"] == "Corn")
    assert corn["futures_price"] is None


def test_mae_mart_futures_calls_proxy_one_symbol_per_request() -> None:
    class _FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return _SYNTHETIC_PROXY_JSON

    with patch(
        "app.platform.market_data.sources.mae_mart_source.requests.get"
    ) as fake_get:
        fake_get.return_value = _FakeResponse()
        result = mae_mart_source.fetch_mae_mart_futures()
    assert result == {"Corn": 4.5025, "Soybeans": 10.7525, "Wheat": 5.5125}
    assert fake_get.call_count == 3  # one GET per symbol, like the page
    for call in fake_get.call_args_list:
        args, kwargs = call
        assert args[0] == mae_mart_source.MAE_MART_PROXY_URL
        assert kwargs["params"]["symbols"] in ("ZCZ26=F", "ZSF27=F", "ZWN27=F")
        assert kwargs["headers"]["User-Agent"] == mae_mart_source.CONTACT_USER_AGENT


# ---------------------------------------------------------------------------
# North Gower
# ---------------------------------------------------------------------------


def test_north_gower_parses_daily_post_table() -> None:
    result = north_gower_source.parse_north_gower_html(_read("north_gower_sample.html"))
    assert result["status"] == "ok"
    rows = result["rows"]
    assert len(rows) == 5
    corn_spot = next(
        r
        for r in rows
        if r["commodity"] == "Corn" and r["delivery_month"] == "Spot"
    )
    assert corn_spot["cash_price"] == 6.01
    assert corn_spot["cash_price_mt"] == 236.67
    assert corn_spot["basis"] == 2.0
    assert corn_spot["futures_price"] == 4.01
    assert corn_spot["basis_month"] == "Sep 2026"
    assert corn_spot["currency"] == "CAD"
    hrs = next(r for r in rows if r["commodity"] == "Wheat — HRS")
    assert hrs["delivery_month"] == "Spot"
    assert hrs["cash_price"] == 7.75


def test_north_gower_homepage_without_table_is_unsupported() -> None:
    result = north_gower_source.parse_north_gower_html(
        "<html><body><div id='cash-bids'>Contact us</div></body></html>"
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []


def test_north_gower_find_latest_post_url() -> None:
    homepage = """
    <html><body>
      <a href="https://northgowergrains.com/tuesday-november-17-2026-700-am/">Nov 17</a>
      <a href="https://northgowergrains.com/wednesday-november-18-2026-820-am/">Nov 18</a>
      <a href="https://northgowergrains.com/category/blog/">Daily Blog</a>
    </body></html>
    """
    # First daily-post link in document order is returned.
    assert (
        north_gower_source.find_latest_post_url(homepage)
        == "https://northgowergrains.com/tuesday-november-17-2026-700-am/"
    )
    assert north_gower_source.find_latest_post_url("<html></html>") is None


# ---------------------------------------------------------------------------
# Mapleview (stub — JS-rendered, no plain-HTML structure)
# ---------------------------------------------------------------------------


def test_mapleview_js_shell_is_unsupported_with_reason() -> None:
    result = mapleview_source.parse_mapleview_html(_read("mapleview_sample.html"))
    assert result["status"] == "unsupported"
    assert result["rows"] == []
    assert any("Grain Discovery" in note for note in result["notes"])
    assert any("Playwright" in note for note in result["notes"])


def test_mapleview_homepage_copy_is_unsupported() -> None:
    result = mapleview_source.parse_mapleview_html(
        "<html><body><section id='bids'>Cash bids. View current bids.</section></body></html>"
    )
    assert result["status"] == "unsupported"
    assert result["rows"] == []
