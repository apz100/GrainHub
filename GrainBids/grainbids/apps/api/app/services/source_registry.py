from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import sys
from typing import Callable

import pandas as pd

from app.platform.market_data.service import get_sources_path


@dataclass(frozen=True)
class SourceAdapter:
    key: str
    module: str
    function: str
    mode: str
    source_class: str
    default_poll_minutes: int
    default_timeout_seconds: int


ADAPTERS: dict[str, SourceAdapter] = {
    "agricharts": SourceAdapter("agricharts", "agricharts_source", "fetch_agricharts_bids", "playwright", "scraper", 15, 90),
    "andersons": SourceAdapter("andersons", "andersons_source", "fetch_andersons_all", "direct", "api", 10, 60),
    "bunge": SourceAdapter("bunge", "bunge_source", "fetch_bunge_all", "playwright", "scraper", 15, 90),
    "dg_global": SourceAdapter("dg_global", "dg_global_source", "fetch_dg_global", "playwright", "scraper", 15, 90),
    "ganaraska": SourceAdapter("ganaraska", "ganaraska_source", "fetch_ganaraska", "playwright", "scraper", 15, 90),
    "glg": SourceAdapter("glg", "glg_source", "fetch_glg_all", "playwright", "scraper", 15, 90),
    "hensall": SourceAdapter("hensall", "hensall_source", "fetch_hensall", "playwright", "scraper", 15, 90),
    "lac": SourceAdapter("lac", "lac_source", "fetch_lac_all", "playwright", "scraper", 15, 90),
    "snobelen": SourceAdapter("snobelen", "snobelen_source", "fetch_snobelen_all", "playwright", "scraper", 15, 90),
    "wanstead": SourceAdapter("wanstead", "wanstead_source", "fetch_wanstead_all", "playwright", "scraper", 15, 90),
    "collwest": SourceAdapter("collwest", "collwest_source", "fetch_collwest", "direct_dict", "scraper", 15, 90),
    "mae_mart": SourceAdapter("mae_mart", "mae_mart_source", "fetch_mae_mart", "direct_dict", "scraper", 15, 90),
    "north_gower": SourceAdapter("north_gower", "north_gower_source", "fetch_north_gower_latest", "direct_dict", "scraper", 15, 90),
    "mapleview": SourceAdapter("mapleview", "mapleview_source", "fetch_mapleview", "direct_dict", "scraper", 15, 90),
    "fac": SourceAdapter("fac", "bushel_source", "fetch_fac", "direct_dict", "scraper", 15, 90),
    "chandler_feed": SourceAdapter("chandler_feed", "bushel_source", "fetch_chandler_feed", "direct_dict", "scraper", 15, 90),
    "cameron_coop": SourceAdapter("cameron_coop", "bushel_source", "fetch_cameron_coop", "direct_dict", "scraper", 15, 90),
    "cgs": SourceAdapter("cgs", "bushel_source", "fetch_cgs", "direct_dict", "scraper", 15, 90),
    "almota": SourceAdapter("almota", "bushel_source", "fetch_almota", "direct_dict", "scraper", 15, 90),
    "williams_gin": SourceAdapter("williams_gin", "bushel_source", "fetch_williams_gin", "direct_dict", "scraper", 15, 90),
    "rugby": SourceAdapter("rugby", "bushel_source", "fetch_rugby", "direct_dict", "scraper", 15, 90),
    "lake_norden": SourceAdapter("lake_norden", "bushel_source", "fetch_lake_norden", "direct_dict", "scraper", 15, 90),
    "united_coop": SourceAdapter("united_coop", "bushel_source", "fetch_united_coop", "direct_dict", "scraper", 15, 90),
    "forest_river": SourceAdapter("forest_river", "bushel_source", "fetch_forest_river", "direct_dict", "scraper", 15, 90),
    "ace_ethanol": SourceAdapter("ace_ethanol", "bushel_source", "fetch_ace_ethanol", "direct_dict", "scraper", 15, 90),
    "alliance_grain": SourceAdapter("alliance_grain", "bushel_source", "fetch_alliance_grain", "direct_dict", "scraper", 15, 90),
    "agp": SourceAdapter("agp", "bushel_source", "fetch_agp", "direct_dict", "scraper", 15, 90),
    "synergy": SourceAdapter("synergy", "bushel_source", "fetch_synergy", "direct_dict", "scraper", 15, 90),
    "wheaton_grain": SourceAdapter("wheaton_grain", "bushel_source", "fetch_wheaton_grain", "direct_dict", "scraper", 15, 90),
    "skyland": SourceAdapter("skyland", "bushel_source", "fetch_skyland", "direct_dict", "scraper", 15, 90),
    "winchester": SourceAdapter("winchester", "bushel_source", "fetch_winchester", "direct_dict", "scraper", 15, 90),
    "winchester_3440": SourceAdapter("winchester_3440", "bushel_source", "fetch_winchester_3440", "direct_dict", "scraper", 15, 90),
    "skyland_2730": SourceAdapter("skyland_2730", "bushel_source", "fetch_skyland_2730", "direct_dict", "scraper", 15, 90),
    "smithfield_bentonville": SourceAdapter("smithfield_bentonville", "bushel_source", "fetch_smithfield_bentonville", "direct_dict", "scraper", 15, 90),
    "agtegra": SourceAdapter("agtegra", "cashbids_embed_source", "fetch_agtegra", "direct_dict", "scraper", 15, 90),
    "heritage_coop": SourceAdapter("heritage_coop", "cashbids_embed_source", "fetch_heritage_coop", "direct_dict", "scraper", 15, 90),
    "linn_coop": SourceAdapter("linn_coop", "cashbids_embed_source", "fetch_linn_coop", "direct_dict", "scraper", 15, 90),
    "midway_coop": SourceAdapter("midway_coop", "cashbids_embed_source", "fetch_midway_coop", "direct_dict", "scraper", 15, 90),
    "ag_state": SourceAdapter("ag_state", "cashbids_embed_source", "fetch_ag_state", "direct_dict", "scraper", 15, 90),
    "superior_ag": SourceAdapter("superior_ag", "cashbids_embed_source", "fetch_superior_ag", "direct_dict", "scraper", 15, 90),
    "alcivia": SourceAdapter("alcivia", "cashbids_embed_source", "fetch_alcivia", "direct_dict", "scraper", 15, 90),
    "tgm": SourceAdapter("tgm", "cashbids_embed_source", "fetch_tgm", "direct_dict", "scraper", 15, 90),
    "pro_coop": SourceAdapter("pro_coop", "cashbids_embed_source", "fetch_pro_coop", "direct_dict", "scraper", 15, 90),
    "hull_coop": SourceAdapter("hull_coop", "cashbids_embed_source", "fetch_hull_coop", "direct_dict", "scraper", 15, 90),
    "stateline_coop": SourceAdapter("stateline_coop", "cashbids_embed_source", "fetch_stateline_coop", "direct_dict", "scraper", 15, 90),
    "pro_coop_21302": SourceAdapter("pro_coop_21302", "cashbids_embed_source", "fetch_pro_coop_21302", "direct_dict", "scraper", 15, 90),
    "pro_coop_21302b": SourceAdapter("pro_coop_21302b", "cashbids_embed_source", "fetch_pro_coop_21302b", "direct_dict", "scraper", 15, 90),
    "skyland_2731": SourceAdapter("skyland_2731", "bushel_source", "fetch_skyland_2731", "direct_dict", "scraper", 15, 90),
    "skyland_2734": SourceAdapter("skyland_2734", "bushel_source", "fetch_skyland_2734", "direct_dict", "scraper", 15, 90),
    "skyland_2740": SourceAdapter("skyland_2740", "bushel_source", "fetch_skyland_2740", "direct_dict", "scraper", 15, 90),
    "skyland_2742": SourceAdapter("skyland_2742", "bushel_source", "fetch_skyland_2742", "direct_dict", "scraper", 15, 90),
    "skyland_2754": SourceAdapter("skyland_2754", "bushel_source", "fetch_skyland_2754", "direct_dict", "scraper", 15, 90),
    "skyland_2761": SourceAdapter("skyland_2761", "bushel_source", "fetch_skyland_2761", "direct_dict", "scraper", 15, 90),
    "smithfield_bladenboro": SourceAdapter("smithfield_bladenboro", "bushel_source", "fetch_smithfield_bladenboro", "direct_dict", "scraper", 15, 90),
    "smithfield_bladenboro_feed_mill": SourceAdapter("smithfield_bladenboro_feed_mill", "bushel_source", "fetch_smithfield_bladenboro_feed_mill", "direct_dict", "scraper", 15, 90),
    "smithfield_chadbourn": SourceAdapter("smithfield_chadbourn", "bushel_source", "fetch_smithfield_chadbourn", "direct_dict", "scraper", 15, 90),
    "smithfield_clarkton": SourceAdapter("smithfield_clarkton", "bushel_source", "fetch_smithfield_clarkton", "direct_dict", "scraper", 15, 90),
    "skyland_2763": SourceAdapter("skyland_2763", "bushel_source", "fetch_skyland_2763", "direct_dict", "scraper", 15, 90),
    "skyland_2766": SourceAdapter("skyland_2766", "bushel_source", "fetch_skyland_2766", "direct_dict", "scraper", 15, 90),
    "skyland_2770": SourceAdapter("skyland_2770", "bushel_source", "fetch_skyland_2770", "direct_dict", "scraper", 15, 90),
    "skyland_2771": SourceAdapter("skyland_2771", "bushel_source", "fetch_skyland_2771", "direct_dict", "scraper", 15, 90),
    "skyland_2778": SourceAdapter("skyland_2778", "bushel_source", "fetch_skyland_2778", "direct_dict", "scraper", 15, 90),
    "skyland_3370": SourceAdapter("skyland_3370", "bushel_source", "fetch_skyland_3370", "direct_dict", "scraper", 15, 90),
    "skyland_3621": SourceAdapter("skyland_3621", "bushel_source", "fetch_skyland_3621", "direct_dict", "scraper", 15, 90),
    "smithfield_clinton": SourceAdapter("smithfield_clinton", "bushel_source", "fetch_smithfield_clinton", "direct_dict", "scraper", 15, 90),
    "smithfield_hobbsville": SourceAdapter("smithfield_hobbsville", "bushel_source", "fetch_smithfield_hobbsville", "direct_dict", "scraper", 15, 90),
    "smithfield_kinston": SourceAdapter("smithfield_kinston", "bushel_source", "fetch_smithfield_kinston", "direct_dict", "scraper", 15, 90),
    "smithfield_lagrange": SourceAdapter("smithfield_lagrange", "bushel_source", "fetch_smithfield_lagrange", "direct_dict", "scraper", 15, 90),
    "smithfield_morgans_corner": SourceAdapter("smithfield_morgans_corner", "bushel_source", "fetch_smithfield_morgans_corner", "direct_dict", "scraper", 15, 90),
    "smithfield_mount_olive": SourceAdapter("smithfield_mount_olive", "bushel_source", "fetch_smithfield_mount_olive", "direct_dict", "scraper", 15, 90),
    "smithfield_red_springs": SourceAdapter("smithfield_red_springs", "bushel_source", "fetch_smithfield_red_springs", "direct_dict", "scraper", 15, 90),
    "smithfield_walstonburg": SourceAdapter("smithfield_walstonburg", "bushel_source", "fetch_smithfield_walstonburg", "direct_dict", "scraper", 15, 90),
    "smithfield_weeksville": SourceAdapter("smithfield_weeksville", "bushel_source", "fetch_smithfield_weeksville", "direct_dict", "scraper", 15, 90),
    "smithfield_chief_feed_mill": SourceAdapter("smithfield_chief_feed_mill", "bushel_source", "fetch_smithfield_chief_feed_mill", "direct_dict", "scraper", 15, 90),
    "smithfield_laurinburg_feed_mill": SourceAdapter("smithfield_laurinburg_feed_mill", "bushel_source", "fetch_smithfield_laurinburg_feed_mill", "direct_dict", "scraper", 15, 90),
    "smithfield_creswell": SourceAdapter("smithfield_creswell", "bushel_source", "fetch_smithfield_creswell", "direct_dict", "scraper", 15, 90),
    "smithfield_warsaw": SourceAdapter("smithfield_warsaw", "bushel_source", "fetch_smithfield_warsaw", "direct_dict", "scraper", 15, 90),
    "smithfield_harpster": SourceAdapter("smithfield_harpster", "bushel_source", "fetch_smithfield_harpster", "direct_dict", "scraper", 15, 90),
    "smithfield_morral": SourceAdapter("smithfield_morral", "bushel_source", "fetch_smithfield_morral", "direct_dict", "scraper", 15, 90),
    "smithfield_darlington": SourceAdapter("smithfield_darlington", "bushel_source", "fetch_smithfield_darlington", "direct_dict", "scraper", 15, 90),
    "smithfield_lake_city": SourceAdapter("smithfield_lake_city", "bushel_source", "fetch_smithfield_lake_city", "direct_dict", "scraper", 15, 90),
    "five_star_coop": SourceAdapter("five_star_coop", "wpdatatables_source", "fetch_five_star_coop", "direct_dict", "scraper", 15, 90),
    "fmn": SourceAdapter("fmn", "fmn_source", "fetch_fmn_cash", "direct_dict", "scraper", 15, 90),
    "usda_mirror_jvg": SourceAdapter("usda_mirror_jvg", "usda_mirror_source", "fetch_usda_mirror", "direct_dict", "scraper", 15, 90),
    "usda_mirror_fsg": SourceAdapter("usda_mirror_fsg", "usda_mirror_source", "fetch_usda_mirror_fs_grain", "direct_dict", "scraper", 15, 90),
}
PILOT_ADAPTER_KEYS = ("agricharts", "glg", "hensall", "snobelen", "andersons")


def list_adapters() -> list[SourceAdapter]:
    return [ADAPTERS[key] for key in sorted(ADAPTERS.keys())]


def list_pilot_adapter_keys() -> list[str]:
    return [key for key in PILOT_ADAPTER_KEYS if key in ADAPTERS]


def get_adapter(key: str) -> SourceAdapter:
    normalized = key.strip().lower()
    if normalized not in ADAPTERS:
        raise KeyError(f"Unsupported source adapter '{key}'")
    return ADAPTERS[normalized]


def fetch_with_adapter(adapter: SourceAdapter) -> pd.DataFrame:
    _ensure_sources_path_on_sys_path()
    fetch_fn = _load_fetch_fn(adapter)
    result = fetch_fn()
    if result is None:
        return pd.DataFrame()
    if isinstance(result, pd.DataFrame):
        return result
    raise TypeError(f"Unexpected adapter output type for {adapter.key}: {type(result)!r}")


def _ensure_sources_path_on_sys_path() -> None:
    path = get_sources_path()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_fetch_fn(adapter: SourceAdapter) -> Callable[[], pd.DataFrame]:
    module = import_module(f"app.platform.market_data.sources.{adapter.module}")
    target = getattr(module, adapter.function)

    if adapter.mode == "direct":
        return target

    if adapter.mode == "direct_dict":
        # Cycle 3 plain-HTML collectors return {"rows": [...], "status": ...}
        # instead of a DataFrame; convert rows to a DataFrame here.
        def _dict_runner() -> pd.DataFrame:
            result = target()
            if result is None:
                return pd.DataFrame()
            if isinstance(result, pd.DataFrame):
                return result
            if isinstance(result, dict):
                rows = result.get("rows") or []
                return pd.DataFrame(rows)
            raise TypeError(f"Unexpected adapter output type for {adapter.key}: {type(result)!r}")

        return _dict_runner

    if adapter.mode == "playwright":
        def _runner() -> pd.DataFrame:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                return target(playwright)

        return _runner

    raise ValueError(f"Unsupported adapter mode: {adapter.mode}")
