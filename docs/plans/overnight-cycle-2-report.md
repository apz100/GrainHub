# Overnight Cycle 2 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-2` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 2 complete — all nine approved items built.

**Never merged to master or to cycle-1. No spending, no vendor contact,
no emails sent, no secrets, no deployment changes, no paywalled/licensed
data scraped. No price, WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `90bfb29` | Price history + seasonal averages and public best-bid API (14 tests) |
| `9284665` | Basis tracker with neutral Testville pilot; North Gower Grains removed as pilot/example per Adam's boundary |
| `c4ee27a` | Source health dashboard, futures strip + canola desk, report calendar, daily newsletter generator (42 tests) |
| `9475bbd` | Web pages for basis, source health, futures, calendar, history, best bids, newsletter; `next build` passes (28 pages) |
| `ecc961b` | Email-bid OCR parsing module (32 tests) |
| *(this commit)* | Cycle 2 report + Farm Market News full-read findings in the price-source catalogue |

## 2. Test results

- **Full API suite: 291 passed, 0 failed, 2 warnings** (pre-existing
  Starlette deprecation warnings). Cycle 1 ended at 179 passed.
  New tests in Cycle 2: price history 8, best bids 6, basis tracker 24,
  source health 10, futures strip 6, report calendar 9, daily
  newsletter 17, email-bid parser 32 = **112 new tests**.
- One transient failure was seen once mid-cycle
  (`test_tracker_route_ranks_and_reports_provenance`) while a sibling
  file was being edited concurrently; it passes in isolation and in
  every full run since.
- **Web build: PASS.** `npm install` succeeded, `npm run build`
  exit 0, "Compiled successfully", type-checking passed, 28 pages
  generated. The 7 new routes are dynamic server-rendered pages.
  Only pre-existing ESLint `react-hooks/exhaustive-deps` warnings in
  older pages remain; they were left untouched.

## 3. What was built (done)

### a. Basis tracker
- `GET /api/basis/tracker` and `GET /api/basis/history`:
  basis = cash − futures (per bushel, Decimal), computed only from
  real `NormalizedPrice` rows. Missing cash/futures → named
  `missing_*` reasons, listed as unranked, never estimated.
  History oldest-first; ranking latest-quote-per-location, rank 1 =
  strongest basis, haversine radius with unknown-distance and
  outside-radius exclusion counts. Responses carry source, currency
  (null — see below), unit, quote date, futures month, and a
  `data_quality` note. Page `/basis`.
- **Honest gap:** `NormalizedPrice` (and `PriceSnapshot`/`Source`)
  carry **no currency column**, so basis responses report
  `currency: null` with a note that values should only be compared
  within the same currency. A currency column or per-source currency
  mapping is a data-model decision for Adam.

### b. Source health dashboard
- `GET /api/source-health` and `/api/source-health/summary`: one row
  per price source — status live / stale / broken / unknown, last
  fetch time, parse success rate, last error, consecutive failures —
  computed only from real `ingestion_runs` and
  `source_health_snapshots`. No run and no snapshot → `unknown` with
  "No ingestion data recorded yet". Page `/source-health`.
- Note: probe results (`price_source_probe.py`) are a manual CLI
  smoke test and are not persisted to any table, so they cannot
  contribute health rows yet.

### c. Daily newsletter generator
- `GET /api/newsletter/daily-draft` and
  `POST /api/newsletter/daily-draft/preview`: auto-drafts the daily
  market report from real prices, real USDA research rows, and the
  report calendar's upcoming events. Sections: top bids, basis
  movers, USDA today, upcoming reports. Every empty section renders
  an explicit empty state. **Delivery stays OFF:**
  `DELIVERY_ENABLED = False`, no SMTP import, no send endpoint,
  dedup key `daily-YYYY-MM-DD`. Page `/newsletter`.
- Basis "movers" are ranked from today's snapshot only, with an
  explicit note that no day-over-day move is claimed (no prior-day
  basis is stored).

### d. Futures strip + ICE Canola desk
- `GET /api/futures/strip` (CBOT corn/soybeans/SRW, KC HRW, MGEX HRS,
  oats) and `GET /api/futures/canola` (ICE Canola, CAD/tonne).
  There is no futures table/service in the repo, so both endpoints
  return the contract structure (next 5 contract months) with every
  price explicitly `null`, `available: false`,
  `feed_status: "not_wired"`, delay labelled "10–15 min delayed
  (once a licensed feed is wired)". No futures price invented.
  Page `/futures`.

### e. Price history + 5-year seasonal averages
- `GET /api/prices/history` (real normalized prices only, deduped,
  sorted by date) and `GET /api/prices/seasonal` (5-year seasonal
  average by ISO week, per-year weekly means then mean across years,
  capped at the 5 most recent years present). If fewer than 5 years
  exist, the response states `years_covered` and that missing years
  are not invented or interpolated. USDA research rows are **not**
  averaged into prices (they hold report metrics, not cash prices).
  Page `/history`.

### f. Report calendar
- `GET /api/research/calendar` (2026 only; other years → 400):
  WASDE 12 dates, Grain Stocks quarterly, Prospective Plantings,
  Acreage, Small Grains, Crop Progress Mondays Apr–Nov, Export Sales
  Thursdays, COT Fridays — each with `days_until` computed from the
  current date, plus `next_event` and the next 10 upcoming events.
  As of 2026-11-18 the next event was Export Sales, Thu 2026-11-19.
  Page `/calendar`.

### g. Email-bid OCR pipeline (parsing module)
- `app/services/email_bid_parser.py` — pure stdlib parsing, no
  Outlook, no mailbox access, no network, no DB, no sending:
  `parse_email_bid_text` (sender dispatch: MacEwen, Andersons,
  BroadGrain, Richardson, P&H, Bunge), `parse_ocr_bid_rows`
  (OCR-noise tolerance, suspect digits flagged at confidence 0.5,
  never silently corrected), normalization helpers ($/bu ↔ $/MT,
  CAD/USD with caller-supplied FX only, delivery-month and futures-
  month parsing), and `ocr_image_to_text` (optional Pillow/
  pytesseract, clear error when unavailable). Only complete rows are
  valid; incomplete rows are returned separately as rejected with
  reasons. 32 tests. No router yet — wiring it to an upload/ingest
  endpoint is a Cycle 3 item.

### h. Public best-bid page
- `GET /api/best-bids` — public, no auth, no org header: top bid
  per company per commodity + delivery month from real normalized
  prices, grouped by commodity and delivery month, with company,
  location, cash price (bu + mt), basis, unit, quote date, futures
  month, source. No user data in the response. Page `/best-bids`.

### i. GitHub Actions CI — written, NOT pushed (blocker)
- `.github/workflows/api-tests.yml` is written (Python 3.12,
  install API requirements, run pytest on every push/PR, no secrets,
  no deploy steps) but **could not be pushed**: GitHub rejected the
  push because the `gh` OAuth token lacks the `workflow` scope
  ("refusing to allow an OAuth App to create or update workflow
  `.github/workflows/api-tests.yml` without `workflow` scope").
  The file sits untracked in the local working tree on this branch.
  Adam needs to re-authenticate `gh` with workflow scope, or add
  the file via the GitHub web UI. Nothing else in Cycle 2 was
  blocked by this.

## 4. North Gower Grains boundary — applied

Adam's boundary (23:46 EST, refined 23:47 EST): GrainHub must not
be related to North Gower Grains at all, **except** that scraping
their public bid prices is allowed as one ordinary source among
many, with no special treatment.

Applied in Cycle 2:
- The basis tracker pilot was changed from North Gower to a neutral
  synthetic location ("Testville", synthetic coordinates,
  `find_default_origin`). All Cycle 2 tests that used North Gower
  as the example location/company were swapped to the same neutral
  example (Testville / Test Elevator Co.), keeping test geometry
  consistent (~28 km Testville–Russell separation).
- Zero "North Gower" matches remain in the new Cycle 2 code, tests,
  pages, or docs I wrote, verified by grep — except:
  - the price-source catalogue, where North Gower Grains is listed
    as one ordinary verified source (prices only, "Ordinary source;
    no special treatment", "top priority" language removed);
  - the probe list, which keeps its price-page entry as an ordinary
    data source;
  - the town name "North Gower" in pre-existing geographic location
    lists (dashboard page, AgriCharts location list) — the town, not
    the company, and pre-existing code, not Cycle 2 work.
- Legacy/archive files and the pre-existing
  `location_company_seed_docx.py` mapping were left untouched, and
  the Cycle 1 report (a historical record) was not rewritten.
- No contact was made, no affiliation is implied anywhere.

## 5. Farm Market News — full read (2026-11-18, Adam)

The FMN cash page (`fmn1.agricharts.com/markets/cash.php`) was read
in full: one long scrolling list, **204 bid tables, 86 delivery
points** (85 Ontario + Quebec FOB Corn), columns Name / Delivery /
Delivery End / Futures Month / Futures Price / Change / Basis / Cash
Price / Settlement; corn, soybeans, wheat (HRS/HRW/SRW/SWW), barley
and oats only at Hensall HDC and Sunderland, no canola table.
Delivery mostly old crop Nov 2026 / new crop Oct 2027 (corn/soy) /
Jul–Aug 2027 (wheat).

**Key finding:** the Location dropdown lists **336 options (335
named)** — far more than the 204 tables. Dropdown-only entries
include Winchester, Sarnia, Goderich, Durham, Wellington, Chatham,
Kintore, Maxville. The default view is NOT the complete FMN Ontario
set. Existing repo code already builds
`cash.php?location_filter={loc_id}` URLs, so the Cycle 3 task is to
verify the dropdown values map to `location_filter` IDs and fetch a
dropdown-only location (e.g. Winchester). If it loads, one collector
pattern covers up to 335 Ontario points. Full detail (location list
only, no prices) in `docs/plans/price-source-catalogue.md`.

## 6. What is still scaffold / stub

- Futures endpoints: contract structure only, prices null until a
  licensed/delayed feed is wired (Barchart/DTN decision — Adam).
- Research value parsers for Grain Stocks / Export Sales / COT are
  not built (Cycle 1 carry-over; Cycle 3 if formats verify).
- Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments (Cycle 1 carry-overs).
- Email-bid parser is a module only — no upload/ingest endpoint
  wired to it yet.
- Source health cannot yet use probe results (not persisted).
- CI workflow file written but not pushed (token scope — see §3i).

## 7. Blocked / needs Adam

Carried from Cycle 1, unchanged: NASS API key (free), FAS/data.gov
key (free), LLM provider + key for Advisor `/ask`, Barchart/DTN
licensed feed decision, ERP choice, eSign provider, pricing/hosting
decisions. **New:** re-authenticate `gh` with `workflow` scope (or
add the CI workflow via the GitHub web UI) so `.github/workflows/
api-tests.yml` can be pushed. **New:** currency is not stored on
normalized price rows — a currency column or per-source currency
mapping is needed before basis/best-bid responses can report real
currency instead of `null`.
