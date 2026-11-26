"""Currency derivation rules (migration 0022, Adam's country rule).

Two ways a stored price row gets its currency, in priority order:

1. STATED — the collector itself records a currency on the row
   (Bushel per-site config, Collwest / FMN / Mae-Mart / North Gower
   CAD, USDA mirrors USD, ...). Copied verbatim at insert; never
   overwritten by anything here.
2. COUNTRY — Adam's rule (2026-11-20): this platform covers North
   America only, and a cash price is denominated in the currency of
   the country its delivery location is in — Canada -> CAD, US ->
   USD. Applied when the collector states no currency.

The schema records no country on the ``locations`` table; a delivery
location's country is a property of the elevator that publishes its
bids, and every registry adapter serves delivery points in exactly
one country. ``ADAPTER_COUNTRIES`` therefore records the country per
adapter key for the families whose collectors state no currency,
derived from the collector code on 2026-11-20:

* CA — the Ontario Playwright collectors (agricharts' FMN Ontario
  cash page, dg_global.ca, Ganaraska, Great Lakes Grain, Hensall
  Co-op, London Agricultural Commodities, Snobelen Farms, Wanstead
  Farmers Co-op), Mapleview Grain (London, ON), Bunge's four scraped
  locations (Altona MB, Hamilton ON, Harrowby MB, Morden MB), and
  The Andersons Canada (andersonscanada.com; all-Ontario locations).
* US — the ``us_dtn_source`` and ``us_agricharts_source`` families,
  whose modules scrape US grain elevators exclusively.

Adapters whose collectors state a currency are NOT in this table
(the stated value wins and needs no derivation), and file / manual
sources have no adapter key, so their rows stay NULL (unknown).
Migration 0022 carries its own copy of these lists (migrations stay
self-contained); a test asserts the two copies agree.
"""

from __future__ import annotations


COUNTRY_CURRENCIES: dict[str, str] = {
    "CA": "CAD",
    "US": "USD",
}

# Country names / codes accepted as a location country, normalized
# to the ISO codes used in COUNTRY_CURRENCIES.
_COUNTRY_ALIASES: dict[str, str] = {
    "CA": "CA",
    "CAN": "CA",
    "CANADA": "CA",
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "UNITED STATES OF AMERICA": "US",
}

# Adapter key -> ISO country code, for collectors that record no
# currency (see module docstring for the derivation).
ADAPTER_COUNTRIES: dict[str, str] = {
    # Canada — Ontario Playwright collectors + Ontario/MB sites.
    "agricharts": "CA",
    "andersons": "CA",
    "bunge": "CA",
    "dg_global": "CA",
    "ganaraska": "CA",
    "glg": "CA",
    "hensall": "CA",
    "lac": "CA",
    "mapleview": "CA",
    "snobelen": "CA",
    "wanstead": "CA",
    # United States — us_dtn_source family.
    "ag_partners": "US",
    "al_corn": "US",
    "allied_cooperative": "US",
    "aurora_coop": "US",
    "brubaker_grain": "US",
    "cfs": "US",
    "elite_octane": "US",
    "frontier_coop": "US",
    "green_plains": "US",
    "hoffman_ag": "US",
    "kanza_coop": "US",
    "sunrise": "US",
    "wilton_farmers_union_elevator": "US",
    # United States — us_agricharts_source family.
    "ag_plus": "US",
    "anthony_farmers_coop": "US",
    "central_farmers_coop": "US",
    "farmers_win_coop": "US",
    "heartland_coop": "US",
    "heritage_grain_cooperative": "US",
    "keller": "US",
    "kokomo_grain": "US",
    "legacy_farmers": "US",
    "mulvane_coop": "US",
    "pro_ag": "US",
    "west_con": "US",
    "wheaton_dumont": "US",
}


def currency_for_country(country: str | None) -> str | None:
    """Currency for a location country (CA -> CAD, US -> USD).

    Accepts ISO codes and plain country names, case-insensitively.
    Anything else (including None) returns None — unknown stays
    unknown rather than being guessed.
    """
    if country is None:
        return None
    code = _COUNTRY_ALIASES.get(str(country).strip().upper())
    if code is None:
        return None
    return COUNTRY_CURRENCIES[code]


def currency_for_adapter(adapter_key_or_name: str | None) -> str | None:
    """Country-rule currency for a source's adapter key (or, for
    sources seeded before adapter_key existed, its name — the same
    COALESCE the migration backfill matches on). None when the
    adapter records its own currency, is unlisted, or the source is
    a file / manual source."""
    if adapter_key_or_name is None:
        return None
    country = ADAPTER_COUNTRIES.get(str(adapter_key_or_name).strip())
    if country is None:
        return None
    return COUNTRY_CURRENCIES[country]
