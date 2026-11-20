# Currency design note — GrainHub (Cycle 10, design only)

**Status:** proposal for Adam's decision. No migration landed, no code
changed. The `currency: null` gap found in Cycle 2 is still open.

## The problem

`NormalizedPrice` (`GrainBids/grainbids/apps/api/app/models/normalized_price.py`)
stores `cash_price_bu`, `cash_price_mt`, `basis`, `futures_price` —
all with **no currency column**. Downstream, the basis tracker and
the public best-bid page therefore report `currency: null`, even
though the collectors already know the currency for most rows. A
Canadian farmer comparing a CAD Ontario bid with a USD US bid
currently sees two bare numbers with no way to tell them apart.

## Where currency is already known (verified, per collector)

| Source family | Currency | Evidence |
|---|---|---|
| Bushel `.cbmod` sites (US) | USD | Per-site config in `bushel_source.py` (`currency="USD"`); Collwest is the one CAD exception (`currency="CAD"`, Collingwood ON) |
| Collwest standalone | CAD | `collwest_source.py` docstring + row `"currency": "CAD"` — basis + CBOT futures ≈ bid in CAD/bu |
| AgriCharts `cashbids.php` embed (8 US sites) | USD | US elevators; bids in $/bu + per-tonne; no CAD signal |
| Five Star wpDataTables | USD | Iowa coop; $/bu bids |
| FMN cash page (Ontario) | CAD | Ontario delivery points; GFO cash bids in CAD |
| USDA AMS mirrors (James Valley / FS Grain) | USD | USDA report values in USD |
| Ontario direct collectors (Mae-Mart, Mapleview, etc.) | CAD | Ontario elevators (to be confirmed per site when wired) |

Caveats, recorded not solved: the Bushel module docstring warns
futures/change **units** vary per site (dollars vs cents) — currency
and unit are separate axes and must not be conflated. Barley/oats
rows at Hensall HDC / Sunderland carry no futures/basis at all.

## Proposed change (for Adam to approve)

1. **Migration `0020`** (← `0019`, chain stays linear): add nullable
   `currency` (`String(3)`, ISO 4217, e.g. `USD` / `CAD`) to
   `normalized_prices`. Nullable on purpose — historical rows stay
   `NULL` (unknown) rather than being guessed.
2. **Ingestion:** each collector's row `currency` (already emitted by
   Bushel/Collwest; to be added to the cashbids-embed, wpDataTables,
   FMN, and USDA-mirror row dicts) is copied into the column at
   insert time. Collectors that cannot determine currency leave it
   `NULL` and note the reason — never default to USD.
3. **API responses:** basis tracker, best-bids, market search, and
   price history return the stored `currency` per row (or `null`
   with `currency_unknown: true` where missing), instead of today's
   blanket `currency: null`.
4. **No silent conversion at ingest.** Store the price in its source
   currency. Any cross-currency comparison (basis rank across the
   border, best-bid lists mixing CAD/USD) must either (a) display
   both currencies side by side, or (b) convert explicitly with a
   labelled FX rate — see below.

## Decisions Adam needs to make

1. **Store source currency (recommended) vs convert to USD at
   ingest?** Storing source currency preserves the bid as published
   and keeps the audit trail clean; conversion can be layered on top
   for display. Converting at ingest destroys the published figure.
2. **FX source for display conversion:** Bank of Canada daily noon
   rate (free, public, already used by the legacy CashGrainBids
   pipeline) is the obvious pick for CAD↔USD. Confirm, and confirm
   the rate's as-of date must be shown next to any converted figure.
3. **Mixed-currency lists:** in best-bids / basis rank, should
   CAD and USD rows be shown in one list with converted values, or
   grouped by currency with no conversion? Recommendation: group by
   currency by default; conversion only as an explicit, labelled
   toggle.
4. **Backfill:** historical `normalized_prices` rows — backfill
   currency from the source registry where the source is unambiguous
   (e.g. all Bushel US sites → USD), or leave all history `NULL`
   and only populate from the migration date forward? Recommendation:
   backfill only where the mapping is unambiguous, and record the
   backfill rule in the migration.

## What this unblocks once decided

- Honest `currency` on basis-tracker and best-bid responses.
- Cross-border basis ranking and best-bid comparison with labelled
  FX conversion.
- Advisor breakeven in the farm's own currency (farm profiles
  already note "figures are in USD unless the farm says otherwise").

## What this does NOT do

- No FX conversion is implemented by this note; no rate is fetched.
- No migration, model change, or API change is included — this file
  is the proposal only.
