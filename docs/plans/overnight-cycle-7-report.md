# Overnight Cycle 7 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-7` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 7 complete — cashbids.php embed collector, AGP
iframe check, basis-alert wiring.

**Never merged to master or to cycle-1/2/3/4/5/6. No spending, no
vendor contact, no emails sent, no secrets, no deployment changes,
no paywalled/licensed data scraped. No price, WASDE number, basis,
or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `1031f8a` | AGP iframe verified Bushel (Chester, NE) and registered; basis thresholds wired into alert evaluator (migration 0019) |
| `019806e` | AgriCharts cashbids.php embed collector (6 sites verified, 105 rows); registered + reclassified |
| *(this commit)* | Cycle 7 report |

## 2. Test results

- **Full API suite: 407 passed, 0 failed** (Cycle 6 ended at 380).
  New tests in Cycle 7: basis-alert wiring 14, Bushel AGP 3,
  cashbids embed 10 = **27 new tests**.
- Web build was not re-run in Cycle 7 (no web files changed).

## 3. What was built (done)

### AgriCharts cashbids.php embed collector
- **Static route proven — no Playwright needed.** The
  `cashbids.php` embed is a JS loader that XHRs a second endpoint,
  `cashbids-js.php` (same host + query params, plus `noscript=1` /
  `acCnt=1` — the loader's own `widgetURL`). That endpoint returns
  a `<script id="cb-functions">` block with `var bids = [...]` — a
  JSON array of location groups. A plain GET + JSON parse suffices.
- **Verified row counts (structure only, no prices recorded):**
  Agtegra 8 (Hecla, Corn); Heritage 15 (Ada; Corn 7, Soybeans 7,
  Wheat SRW 1); Linn 51 (5 locations incl. ADM, Cargill, Ingredion;
  #2 Yellow Corn 39, Soybeans 12); Midway 8 (label "All Locations");
  Ag State 11 (Corn 6, Soybeans 5); Superior 12 (CORN 8, SOYBEANS
  4). **Total 105 rows.** All rows carry cash $/bu + per-tonne,
  basis (integer cents), futures/change (CBOT fractional cents),
  symbol, delivery start/end, basis month. Login-gated/inactive
  rows are skipped and counted. On `groupby=ccommodity` sites the
  group name is a commodity, so row location comes from
  `location_name`.
- All 6 sites registered in `source_registry.py` with config
  toggles on, and reclassified `dtn → agricharts-embed` in
  `us_elevators_urls.toml` (Ag State was mislabelled DTN since
  Cycle 1 — zero DTN strings on its page).

### AGP iframe check
- One polite GET of `agp.o.bushelsites.com/cash-bids`: 200, a
  standard 7-column Bushel `.cbmod` widget — **1 row** (Chester,
  NE, Soybeans, Nov 2026, bid 11.38, basis −0.75, USD/bu). No
  parser changes needed. Registered as `agp`. Caveat: that page
  shows only Chester — if AGP has more locations, they live on
  other pages not yet identified.

### Basis-alert wiring
- Migration `0019` (← `0018`, chain verified linear) adds
  nullable `basis_threshold` + `basis_threshold_operator` to
  `alert_rules`. The evaluator runs the optional basis check after
  each rule's price loop with the same location/saved-search/
  delivery-month scoping, creating deduped alerts via a shared
  helper (price path refactored onto it with identical behaviour).
  Invalid thresholds are caught and skipped — a bad rule can never
  fail an ingestion run. `/api/alerts` create/update accept the
  new fields. 14 wiring tests.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 7 code, tests, or docs (verified
by grep). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks for the 12 DTN-family JS-only sites,
  plus FMN filtered view and Mapleview. StoneX (Frontier) is a
  1-site widget family with no collector.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called). Gateway FS + TGM cash-bids sub-pages unfetched.
- Ag Partners / ALCIVIA / CRC / Five Star / Bunge re-checks due
  (503/timeouts may be transient).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized
  price rows.

## 6. Blocked / needs Adam

Carried from Cycles 1–6: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview).
