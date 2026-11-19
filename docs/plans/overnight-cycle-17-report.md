# Overnight Cycle 17 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-17` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 17 complete — source-catalogue audit (15 verified
toml entries enabled), basis-tracker source-health wiring verified
(already real), price-history/calendar wiring verified, super-plan
§9 extended to Cycle 16.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere. 0 web fetches in
this cycle — audit and code work only.**

## 1. Commits

| Commit | What |
|---|---|
| `7187c16` | Source audit enables 15 verified toml entries; basis health + price-history/calendar wiring verified; history source/as_of labels |
| *(this commit)* | Cycle 17 report |

## 2. Test results

- **Full API suite: 643 passed, 0 failed** (Cycle 16 ended at 638).
  New tests in Cycle 17: basis tracker 3, price history 2 = **5 new tests**.
- **Web build: `npm run build` passes** (re-run this cycle; the
  `/history` page change compiled).

## 3. What was built (done)

### Source-catalogue audit (docs + toml fixes, 0 GETs)
- `us_elevators_urls.toml` now holds **122 entries — 102 enabled /
  20 disabled** (coordinator-verified by grep; the audit worker's
  "121" was off by one). By family: bushel 64 (62 enabled),
  agricharts 16 (13), dtn 16 (13), agricharts-embed 11 (11),
  wpdatatables 1 (1), usda 2 (2), unknown 5 (0), stonex 2 (0),
  unreachable 3 (0), none 1 (0).
- **17 toml changes, all clear contradictions between the
  catalogue's stated verdict (plus a matching `config.toml` toggle
  = true and a registry adapter already present) and the toml —
  nothing changed on a guess:**
  - **Enabled 15:** the 10 Cycle 4/5 Bushel sites (FAC, Chandler
    Feed, Cameron Coop, CGS, Almota, Williams Gin, Rugby, Lake
    Norden, United Cooperative, Forest River) — the catalogue said
    "all 11 Bushel sites are now verified live and wired" in
    Cycle 5, but the toml still carried the stale Cycle 1 note
    "Keep disabled until a bushel collector exists" (the collector
    exists since Cycle 4). Plus Ace Ethanol and Alliance Grain
    (Cycle 6 verified, reclassification never applied to the
    toml), AGP (Cycle 7 verified via Bushel iframe, never
    applied), and the 2 USDA mirrors (verified Cycle 4, collector
    + toggles + registry all on, toml still said "no collector
    yet"). The coordinator independently verified the fixes in the
    file (FAC, Chandler, Ace, Alliance, AGP, both USDA mirrors now
    enabled with Cycle 17 audit comments).
  - **Reclassified, still disabled:** CRC `unknown → stonex`
    (homepage StoneX iframe, same family as Frontier/UFC).
  - **Comment only:** Collwest Grain — toml said "VERIFY COUNTRY
    FIRST"; country was confirmed Canadian 2026-11-18 and the
    catalogue says "removed from US list". Comment now records the
    confirmed verdict; entry stays disabled as a record (deletion
    is a coordinator decision).
- **Remaining unknown list (with catalogue verdicts):** Bunge
  (do-not-add, locations archive); CGB (corporate page, open
  follow-up is chasing the cash-bid module URL from the USDA SCL
  report — do not guess it); The Andersons (closed for static
  collection); United Coop (ATLAS DTN shell — Playwright render
  check needed; distinct org from the enabled Webster City Bushel
  site); Ursa Farmers Coop (DTN page, empty Basis/Cash cells —
  Playwright render check needed); CVA / Landus / Mercer Landmark
  (`unreachable` — re-check only, no retry); Star of the West
  (`none` — no public bid page, do not add); UFC (`stonex` —
  redirects to Central United Cooperative).
- **Registry / toggle cross-check:** all 63 `BUSHEL_SITES` keys,
  all 13 embed keys, and `five_star_coop` have a `true` toggle and
  a registry adapter. No toggle-true entry lacks an adapter; only
  `bunge`/`mapleview` toggles are false (by design). Every toml
  entry has a collection route. `pro_coop_21302`/`21302b` correctly
  share the single PRO Coop toml row. `fmn` correctly has no US
  toml entry (Ontario page).
- **Drift found, not fixed:** `config.toml`'s own
  `[[us.elevators]]` list is stale — 30 entries vs 122 in the urls
  toml; 91 entries missing (all Cycle 10–16 additions) and 4 type
  mismatches (Agtegra, Heritage, Linn, Midway: `dtn` there vs
  `agricharts-embed` in the urls toml/registry). Enabled flags
  agree where both lists overlap. The legacy GrainBidder reads
  `config.toml` `[us]`; the FastAPI platform reads registry +
  toggles. **Coordinator decision: sync it or deprecate it in
  favour of the urls toml.**
- **Prioritised remaining work (written into the catalogue):**
  Playwright-only (DTN render checks — one pass covers the
  family; StoneX render check, auth-gated JS shell — if rows don't
  load, close the family; Andersons GRAINweb picker, low value —
  data is Barchart-licensed); GET probes, 1 each (CGB — chase SCL
  URL, don't guess; CVA/Mercer Landmark single re-checks; Bunge
  only if a new URL surfaces); decisions (Collwest row delete vs
  keep; `config.toml` `[us]` sync vs deprecate; StoneX — more
  effort or close; DTN/Barchart licensed-feed decision, open since
  Cycle 1).

### Basis tracker + source health — verified, no rewire needed
- **The Cycle 3 polish item was already complete and real.** In
  `app/api/routes/basis.py`, `_load_source_status_map` loads the
  org's `Source` rows plus the newest `IngestionRun` and
  `SourceHealthSnapshot` rows and passes them through the
  dashboard's own `build_source_health_rows`, so the tracker and
  the dashboard can never disagree about a source.
  `_attach_source_status` stamps every ranked, unranked, and
  history row with `source_status`. Dashboard vocabulary
  `live`/`stale`/`broken`/`unknown` is reported as
  `healthy`/`stale`/`broken`/`unknown` (`live` → `healthy`,
  stated on every response via `source_status_note`). A source
  with no ingestion run and no snapshot is `unknown`, never
  assumed healthy — including a price row whose source isn't
  registered in the `sources` table at all. Status is attached at
  the route layer *after* `rank_basis`/`build_basis_history`, so
  basis arithmetic is untouched by health data.
- By design, the live probe (`price_source_probe.py`) is a manual
  CLI smoke test whose results are never persisted, so it cannot
  contribute rows; and `serialize_basis_row` carries no status —
  only the two basis routes attach it.
- **Tests + doc only, zero app code:** `tests/test_basis_tracker.py`
  extended (+174 lines) with 3 new route-level tests — healthy +
  stale + broken rows from real ingestion runs, unknown when no
  health record exists (asserts "No ingestion data" note, never
  live), and case-insensitive matching between a price row's
  `source_name` and its health record. Fixtures use Testville /
  Sampletown Grain Co. / DG Global.

### Price history + report calendar — verified, small fix
- **Price history was already wired to real data:**
  `GET /api/prices/history` and `GET /api/prices/seasonal` read
  real `NormalizedPrice` rows joined to `PriceSnapshot` only — no
  static/placeholder prices, no interpolation, missing years
  reported as missing. Seasonal averages are computed from those
  same normalized cash prices, *not* from USDA research rows —
  the route's own note already says this correctly
  (`ResearchReport` rows hold report metrics like ending stocks
  and crop progress, not cash prices, so no price can be derived
  from them). The web `/history` page already called the real API
  and showed honest empty states.
- **The one real gap: responses carried no source or date**, so an
  empty state was a bare empty list. Fixed: both `/history` and
  `/seasonal` now return `source` ("Normalized prices already in
  the database (ingested elevator cash bids); no price is invented,
  backfilled or estimated") and `as_of` (today's UTC date) on every
  response, empty or not. The web page now threads the metadata
  through and both empty states display the source and as-of date.
  2 new tests pin `source`/`as_of` on empty and seeded responses
  (seasonal multi-year mean verified: 2025 $6.00 + 2026 $7.00, ISO
  week 10 → $6.50).
- **Report calendar was already correctly wired — no change
  needed.** The verified 2026 schedule carries `ingestion_status`
  per event from real `ResearchReport` rows (`ingested` with report
  date/vintage/source/ingested_at, or `not_ingested_yet`, never a
  fake "available"). Types with no collector (Prospective
  Plantings / Acreage / Small Grains Summary) are always
  `not_ingested_yet`; with no database the status is `unknown`.
  Both states were already covered by `tests/test_cycle3_polish.py`.
- Web build passes with the `/history` change compiled.

### Super-plan §9 extended to Cycle 16
- Heading/intro now cover Cycles 1–16 (test chain 179 → 638);
  Cycle 15 + 16 bullets added; blockers updated (Skyland + Smithfield
  sweeps complete, Andersons closed on licensing).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 17 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll, United Coop, Ursa), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), and The Andersons GRAINweb (closed for
  static collection — only a rendered browser session remains, and
  the facility tables are Barchart-licensed).
- Staleness watch: Chadbourn (Nov 18), Hamer (Nov 18), Skyland
  3370/3621 (Nov 18) — all need an exemption/lag tolerance if a
  freshness gate is ever added.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).
- **New drift found this cycle:** `config.toml` `[us]` list is
  stale (30 vs 122 entries) — sync or deprecate, coordinator
  decision.

## 6. Blocked / needs Adam

Carried from Cycles 1–16: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons).

**New in Cycle 17:** nothing new needs Adam — but the
`config.toml` `[us]` sync-vs-deprecate decision is flagged for the
coordinator (no Adam input required unless he wants a say).
