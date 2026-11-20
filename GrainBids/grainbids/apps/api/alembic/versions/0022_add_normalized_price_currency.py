"""add currency column to normalized_prices, with unambiguous backfill

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-20

Implements docs/plans/currency-design.md as approved by Adam on
2026-11-20 ("go with the recommendations"):

1. Store the SOURCE currency per price row — no conversion at ingest.
2. FX for display is the Bank of Canada daily noon rate, shown with
   its as-of date (display layer; not part of this migration).
3. Mixed-currency lists group by currency by default; conversion is
   an explicit, labelled toggle only (API layer; not this migration).
4. Backfill historical rows ONLY where the source -> currency mapping
   is unambiguous, with the rule recorded here; everything else stays
   NULL (unknown), never guessed.

Schema: nullable ``currency`` String(3) (ISO 4217) on
``normalized_prices``. Nullable on purpose — a row whose source does
not record a currency keeps NULL rather than a default.

BACKFILL RULE (this migration): a stored row is backfilled when the
source that produced its snapshot — ``price_snapshots.source_id`` ->
``sources``, matched on ``COALESCE(sources.adapter_key, sources.name)``
(seeded sources carry the adapter key in both) — is one of the
adapter keys below. The lists were derived on 2026-11-20 from the
collector code itself, not assumed:

* USD — every registry adapter served by ``bushel_source``: each
  site's entry in ``bushel_source.BUSHEL_SITES`` records
  ``currency="USD"`` (62 sites; the one CAD Bushel site, Collwest, is
  served by ``collwest_source`` instead and is in the CAD list).
* USD — every ``cashbids_embed_source`` site
  (``CASHBIDS_EMBED_SITES`` all record ``currency="USD"``), the
  ``wpdatatables_source`` site (Five Star Coop, ``currency="USD"``),
  and both USDA AMS mirror adapters (``usda_mirror_source`` emits its
  module constant ``CURRENCY = "USD"`` on every row).
* CAD — the collectors that hard-code ``"currency": "CAD"`` in every
  emitted row: ``collwest_source`` (Collingwood, ON),
  ``mae_mart_source`` (its page labels the cash column CAD/bu),
  ``north_gower_source`` (Ontario elevator; CAD recorded by the
  collector), and ``fmn_source`` (Farm Market News Ontario cash page,
  GFO bids in CAD).

DELIBERATELY NOT BACKFILLED (rows stay NULL): adapter families whose
collector code records no currency at all — the Playwright Ontario
sources (agricharts, glg, hensall, lac, snobelen, wanstead,
ganaraska, dg_global), andersons, bunge, the ``us_agricharts_source``
and ``us_dtn_source`` families, and mapleview — plus every file /
manual source. Their collectors also emit no currency today, so
their rows stay NULL going forward; backfilling them would guess a
currency the pipeline itself does not record.

Downgrade drops the column (the backfill lives only in the new
column, so dropping it fully reverses this migration).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


# Adapter keys whose collector code records USD for every row
# (see the backfill rule in the module docstring).
_USD_ADAPTER_KEYS = (
    # bushel_source — BUSHEL_SITES per-site currency, all USD.
    "ace_ethanol",
    "agp",
    "alliance_grain",
    "almota",
    "cameron_coop",
    "cgs",
    "chandler_feed",
    "fac",
    "forest_river",
    "lake_norden",
    "rugby",
    "skyland",
    "skyland_2730",
    "skyland_2731",
    "skyland_2734",
    "skyland_2740",
    "skyland_2742",
    "skyland_2754",
    "skyland_2761",
    "skyland_2763",
    "skyland_2766",
    "skyland_2770",
    "skyland_2771",
    "skyland_2778",
    "skyland_3370",
    "skyland_3621",
    "smithfield_bentonville",
    "smithfield_bladenboro",
    "smithfield_bladenboro_feed_mill",
    "smithfield_chadbourn",
    "smithfield_chief_feed_mill",
    "smithfield_clarkton",
    "smithfield_clinton",
    "smithfield_creswell",
    "smithfield_darlington",
    "smithfield_deep_run_jch",
    "smithfield_hamer",
    "smithfield_harpster",
    "smithfield_hobbsville",
    "smithfield_jones_county",
    "smithfield_kinston",
    "smithfield_kinston_jch",
    "smithfield_lagrange",
    "smithfield_lake_city",
    "smithfield_lapaz",
    "smithfield_laurinburg_feed_mill",
    "smithfield_morgans_corner",
    "smithfield_morral",
    "smithfield_mount_olive",
    "smithfield_nichols",
    "smithfield_petersburg",
    "smithfield_red_springs",
    "smithfield_walstonburg",
    "smithfield_warsaw",
    "smithfield_waverly",
    "smithfield_weeksville",
    "synergy",
    "united_coop",
    "wheaton_grain",
    "williams_gin",
    "winchester",
    "winchester_3440",
    # cashbids_embed_source — CASHBIDS_EMBED_SITES, all USD.
    "ag_state",
    "agtegra",
    "alcivia",
    "heritage_coop",
    "hull_coop",
    "linn_coop",
    "midway_coop",
    "pro_coop",
    "pro_coop_21302",
    "pro_coop_21302b",
    "stateline_coop",
    "superior_ag",
    "tgm",
    # wpdatatables_source — Five Star Coop (Iowa), USD.
    "five_star_coop",
    # usda_mirror_source — USDA AMS mirrors, CURRENCY = "USD".
    "usda_mirror_fsg",
    "usda_mirror_jvg",
)

# Adapter keys whose collectors hard-code "CAD" in every emitted row.
_CAD_ADAPTER_KEYS = (
    "collwest",
    "fmn",
    "mae_mart",
    "north_gower",
)


def _backfill(bind: sa.engine.Connection, currency: str, adapter_keys: tuple[str, ...]) -> None:
    statement = sa.text(
        """
        UPDATE normalized_prices
        SET currency = :currency
        WHERE currency IS NULL
          AND snapshot_id IN (
              SELECT ps.id
              FROM price_snapshots AS ps
              JOIN sources AS s ON s.id = ps.source_id
              WHERE COALESCE(s.adapter_key, s.name) IN :adapter_keys
          )
        """
    ).bindparams(sa.bindparam("adapter_keys", expanding=True))
    bind.execute(statement, {"currency": currency, "adapter_keys": list(adapter_keys)})


def upgrade() -> None:
    op.add_column(
        "normalized_prices",
        sa.Column("currency", sa.String(length=3), nullable=True),
    )
    bind = op.get_bind()
    _backfill(bind, "USD", _USD_ADAPTER_KEYS)
    _backfill(bind, "CAD", _CAD_ADAPTER_KEYS)


def downgrade() -> None:
    op.drop_column("normalized_prices", "currency")
