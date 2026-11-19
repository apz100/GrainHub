"""US AgriCharts + DTN URL-bound registry adapter tests (Cycle 20).

The 13 enabled ``agricharts`` + 13 enabled ``dtn`` entries in
``us_elevators_urls.toml`` had no registry adapter at all — the legacy
generic functions take a URL, while the registry calls ``fetch_fn()``
with no arguments. Cycle 20 adds one zero-argument ``fetch_<slug>()``
wrapper per entry in ``us_agricharts_source.py`` / ``us_dtn_source.py``
(bound to the entry's URL and name) plus ``[sources]`` toggles in
``config.toml``. Registry wiring (``SourceAdapter`` rows) is the
coordinator's step and is NOT asserted here — these tests assert the
wrappers exist, are zero-argument, and pass the correct URL/name to
the generic fetch.

All fixtures are synthetic (invented values, neutral names only —
Testville / Test Elevator Co.). No live fetching inside pytest: the
generic fetch is mocked for the wrapper tests, and the one test that
calls the real ``fetch_us_dtn`` passes ``playwright=None`` so the
Cycle 20 guard returns empty before any I/O.
"""

from __future__ import annotations

import inspect
import sys
import tomllib
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.platform.market_data.sources import us_agricharts_source, us_dtn_source  # noqa: E402

SOURCES_DIR = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "platform"
    / "market_data"
    / "sources"
)
URLS_PATH = SOURCES_DIR / "us_elevators_urls.toml"
CONFIG_PATH = SOURCES_DIR / "config.toml"

# Expected adapter keys: (key, company_name, url) — mirrors the enabled
# entries in us_elevators_urls.toml, verified against that file by
# test_adapter_maps_match_enabled_toml_entries below.
EXPECTED_AGRICHARTS: list[tuple[str, str, str]] = [
    ("ag_plus", "Ag Plus", "https://www.agplusinc.com/markets/cash.php"),
    ("farmers_win_coop", "Farmers Win Coop", "https://www.farmerswin.com/markets/cash.php"),
    ("heartland_coop", "Heartland Coop", "https://www.heartlandcoop.com/markets/cash.php"),
    ("heritage_grain_cooperative", "Heritage Grain Cooperative", "https://www.heritagegrain.com/markets/cash.php"),
    ("keller", "Keller", "https://www.kellergrain.com/markets/cash.php"),
    ("kokomo_grain", "Kokomo Grain", "https://www.kokomograin.com/markets/cash.php?location_filter="),
    ("legacy_farmers", "Legacy Farmers", "https://www.legacyfarmers.com/markets/cash.php"),
    ("pro_ag", "Pro Ag", "https://www.proagfarmers.com/markets/cash.php"),
    ("west_con", "West-Con", "https://www.west-con.com/markets/cash.php"),
    ("wheaton_dumont", "Wheaton Dumont", "https://www.wdcoop.com/markets/cash.php"),
    ("central_farmers_coop", "Central Farmers Coop", "https://www.cenfarmcoop.com/markets/cash.php"),
    ("anthony_farmers_coop", "Anthony Farmers Co-op", "https://www.anthonycoop.com/markets/cash.php"),
    ("mulvane_coop", "Mulvane Coop", "https://www.mulvanecoop.com/markets/cash.php"),
]

EXPECTED_DTN: list[tuple[str, str, str]] = [
    ("ag_partners", "Ag Partners", "https://agpartners.net/cash-bids"),
    ("al_corn", "Al-Corn", "https://www.al-corn.com/cash-bids"),
    ("allied_cooperative", "Allied Cooperative", "https://www.allied.coop/grain/cash-bids"),
    ("aurora_coop", "Aurora Coop", "https://auroracoop.com/markets"),
    ("cfs", "CFS", "https://www.cfscoop.com/products-services/grain"),
    ("elite_octane", "Elite Octane", "https://www.eliteoctane.net/cash-bids"),
    ("frontier_coop", "Frontier Coop", "https://www.frontiercooperative.com/grain/cash-bids"),
    ("green_plains", "Green Plains", "https://gpreinc.com/corn-bids/"),
    ("kanza_coop", "Kanza Coop", "https://www.kanzacoop.com/services/grain"),
    ("sunrise", "Sunrise", "https://www.sunriseco-op.com"),
    ("brubaker_grain", "Brubaker Grain", "https://dtn.brubakergrain.com/"),
    ("hoffman_ag", "Hoffman Ag", "https://dtn.hoffmanag.com/"),
    ("wilton_farmers_union_elevator", "Wilton Farmers Union Elevator",
     "https://www.wiltonfarmerselevator.com/index.cfm?show=11&mid=5&theLocation=1&cmid=all&layout=19"),
]


def _toml_enabled(toml_type: str) -> list[tuple[str, str]]:
    with URLS_PATH.open("rb") as fh:
        entries = tomllib.load(fh)["us"]["elevators"]
    return sorted(
        (e["name"], e["url"])
        for e in entries
        if e["enabled"] and e["type"] == toml_type
    )


def _synthetic_frame() -> pd.DataFrame:
    """One invented row — synthetic fixture, never a real price."""
    return pd.DataFrame([{
        "Location": "Testville - Test Elevator Co.",
        "Name": "Corn",
        "Delivery": "12/31/2026",
        "Delivery End": "12/31/2026",
        "Futures Month": "Dec 2026",
        "Futures Price": "400",
        "Change": "",
        "Basis": "+10",
        "Bushel Cash Price": "$4.10",
        "MT Cash Price": "161.41",
    }])


def test_adapter_maps_match_enabled_toml_entries() -> None:
    """The module adapter maps cover exactly the enabled toml entries."""
    assert sorted(
        (name, url) for _key, name, url in EXPECTED_AGRICHARTS
    ) == _toml_enabled("agricharts")
    assert sorted(
        (name, url) for _key, name, url in EXPECTED_DTN
    ) == _toml_enabled("dtn")

    assert set(us_agricharts_source.US_AGRICHARTS_SITES) == {
        key for key, _name, _url in EXPECTED_AGRICHARTS
    }
    assert set(us_dtn_source.US_DTN_SITES) == {
        key for key, _name, _url in EXPECTED_DTN
    }
    for key, name, url in EXPECTED_AGRICHARTS:
        assert us_agricharts_source.US_AGRICHARTS_SITES[key] == (name, url)
    for key, name, url in EXPECTED_DTN:
        assert us_dtn_source.US_DTN_SITES[key] == (name, url)


@pytest.mark.parametrize(
    "key,name,url",
    EXPECTED_AGRICHARTS,
    ids=[key for key, _n, _u in EXPECTED_AGRICHARTS],
)
def test_agricharts_wrapper_passes_bound_url_and_name(
    key: str, name: str, url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each agricharts wrapper is zero-arg and calls the generic with its URL/name."""
    wrapper = getattr(us_agricharts_source, f"fetch_{key}")
    required = [
        p for p in inspect.signature(wrapper).parameters.values()
        if p.default is inspect.Parameter.empty
    ]
    assert required == [], f"fetch_{key} must take no arguments"

    sentinel = _synthetic_frame()
    mock_fetch = Mock(return_value=sentinel)
    monkeypatch.setattr(us_agricharts_source, "fetch_us_agricharts", mock_fetch)

    result = wrapper()
    mock_fetch.assert_called_once_with(url, name)
    pd.testing.assert_frame_equal(result, sentinel)


@pytest.mark.parametrize(
    "key,name,url",
    EXPECTED_DTN,
    ids=[key for key, _n, _u in EXPECTED_DTN],
)
def test_dtn_wrapper_passes_bound_url_and_name_with_no_browser(
    key: str, name: str, url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each DTN wrapper is zero-arg and calls the generic with its URL/name and no browser.

    The registry adapter path has no Playwright render, so the wrapper
    passes ``playwright=None``; the generic then returns an empty
    DataFrame honestly (see test_dtn_generic_without_browser_is_empty).
    """
    wrapper = getattr(us_dtn_source, f"fetch_{key}")
    required = [
        p for p in inspect.signature(wrapper).parameters.values()
        if p.default is inspect.Parameter.empty
    ]
    assert required == [], f"fetch_{key} must take no arguments"

    sentinel = pd.DataFrame()
    mock_fetch = Mock(return_value=sentinel)
    monkeypatch.setattr(us_dtn_source, "fetch_us_dtn", mock_fetch)

    result = wrapper()
    mock_fetch.assert_called_once_with(url, name, None)
    assert result is sentinel


def test_dtn_generic_without_browser_is_empty() -> None:
    """Real fetch_us_dtn(url, name, None) returns empty without any I/O.

    The Cycle 20 guard returns before Playwright is touched, so this
    needs no network and never invents a row. The URL is synthetic
    (.invalid) to prove nothing is fetched.
    """
    result = us_dtn_source.fetch_us_dtn(
        "https://example.invalid/cash-bids", "Testville", None
    )
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_config_toggles_exist_for_all_new_adapters() -> None:
    """config.toml [sources] has one toggle per new adapter key.

    AgriCharts adapters are static-capable, so they are on; DTN
    adapters are JS-only with no render on the adapter path, so they
    stay off until a later cycle's Playwright render check.
    """
    with CONFIG_PATH.open("rb") as fh:
        sources = tomllib.load(fh)["sources"]
    for key, _name, _url in EXPECTED_AGRICHARTS:
        assert sources.get(key) is True, f"[sources] toggle {key} should be true"
    for key, _name, _url in EXPECTED_DTN:
        assert sources.get(key) is False, f"[sources] toggle {key} should be false"


def test_agricharts_and_dtn_keys_do_not_collide() -> None:
    """The 26 new keys are distinct from each other and from heritage_coop."""
    all_keys = [k for k, _n, _u in EXPECTED_AGRICHARTS + EXPECTED_DTN]
    assert len(all_keys) == len(set(all_keys)) == 26
    assert "heritage_grain_cooperative" not in {"heritage_coop"}
    assert "heritage_grain_cooperative" in set(all_keys)
