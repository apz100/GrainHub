# Decision paper — Currency on normalized prices

**Question:** How should GrainBids stop reporting `currency: null`?
**Cost context:** Zero spend. Every option below is $0.

## The problem

`NormalizedPrice` has no currency column — `app/models/normalized_price.py`
stores `cash_price_bu`, `cash_price_mt`, `basis`, `futures_price` only.
So every consumer hardcodes or propagates null: `app/api/routes/best_bids.py:126`
(`"currency": None`, note at :47), `app/api/routes/price_history.py:137`
(same, note at :14–16), and `app/services/basis_tracker.py` (`compute_basis_for_row`
does `getattr(row, "currency", None)`; `rank_basis`/`build_basis_history`
return `"currency": None` at :313/:470, passed through by
`app/api/routes/basis.py:275,316`). A CAD Ontario bid and a USD US bid
therefore look identical — yet the currency is usually known at collection:
per `docs/plans/currency-design.md`, Bushel sites carry per-site
`currency="USD"` / Collwest `"CAD"` in
`app/platform/market_data/sources/bushel_source.py:224,244,255`, FMN Ontario
is CAD, US AgriCharts/USDA mirrors are USD, and
`app/services/email_bid_parser.py:165` already parses rows as CAD by default.

## Option A — Store currency per price row (migration 0020)

The proposal already drafted in `docs/plans/currency-design.md`.

- **Work:** Alembic `0020` (head is `0019`) adding nullable
  `currency String(3)` to `normalized_prices`; add the field to the model;
  copy the collector row's `currency` at insert — the main writer is
  `NormalizedPrice(...)` in `app/services/upload_csv.py:496`; change the two
  hardcoded `None`s in best-bids/price-history (basis tracker picks the
  column up automatically via its `getattr`). Tests per route.
- **Backfill:** Optional and separable. Design note recommends backfilling
  only unambiguous sources (e.g. Bushel US → USD) and leaving the rest
  `NULL` = honestly unknown; never default to USD.
- **Risk:** Low. Nullable, additive, no conversion. Main risk is a
  collector emitting a wrong currency — mitigated by leaving `NULL` when
  unsure. Historical ambiguity remains visible, not hidden.
- **Cost:** $0.

## Option B — Derive currency at read time, no migration

Map `source_name` (via snapshot → `Source` in `app/models/source.py`, or the
collector registries in code) to a currency in each serializer.

- **Work:** No migration, no backfill, no ingest change. Build and maintain
  a source→currency map; wire it into best-bids, price-history, basis
  tracker, and market search so they cannot disagree.
- **Risk:** Highest correctness risk. `Source` has no currency or country
  column (only `name`, `adapter_key`, `url`, `location_name`, `region`), and
  `NormalizedPrice` only carries a free-text `source_name`. Aggregators and
  exceptions break a coarse map — Collwest is CAD inside the otherwise-USD
  Bushel family, and AgriCharts covers both Ontario CAD and US USD
  material. It also retroactively labels all history by today's guess,
  with no audit trail, and every new source silently returns null (or
  worse, a stale mapping) until the map is updated.
- **Cost:** $0 — cheapest to ship, most expensive to trust.

## Option C — Per-source default + per-row override

Add `currency` to `Source` (admin-set, via the existing `require_admin`
CRUD in `app/api/routes/sources.py`) **and** the Option A per-row column;
ingest writes the source default unless the collector row supplies its own.

- **Work:** Everything in A, plus a `sources.currency` migration, source
  create/update API + validation, and precedence logic (row > source >
  null) with tests. Roughly 1.5–2× Option A.
- **Risk:** Low correctness risk, higher complexity risk: two places can
  disagree, and changing a source default raises the question of whether
  history should change (it must not). Solves a configurability problem
  GrainBids does not yet have — collector currency is already in code
  config, not operator-entered data.
- **Cost:** $0.

## Option D — Do nothing for now

Keep `currency: null` with the existing data-quality notes.

- **Work / cost:** None / $0. **Risk:** Cross-border comparisons stay
  misleading in the UI, and this blocks honest basis ranking and
  own-currency advisor figures (per the design note, "What this unblocks").

## Recommendation: Option A

Do A, with the design note's guardrails: store the **source** currency,
nullable, no silent conversion at ingest, no USD default, backfill only
unambiguous sources, and group mixed-currency lists by currency by
default (any FX display later uses the free Bank of Canada rate, labelled
with its date — $0). A is the only option that records what was actually
published, per row, at the moment of ingest; B guesses it forever after,
and C adds a second source of truth for no current benefit. If a source
later genuinely serves two currencies, its collector already emits
per-row values, so A handles it without revisiting this decision.

**Decision needed from Adam:** approve A + unambiguous-only backfill,
or pick B/C/D.
