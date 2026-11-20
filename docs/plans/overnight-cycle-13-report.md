# Overnight Cycle 13 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-13` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 13 complete — PRO Coop second embed, 10
per-location Bushel probes, Andersons GRAINweb verdict, merge plan
extended to Cycle 12, web build re-verified.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `f1dc87f` | PRO Coop 21302b + 10 per-location Bushel probes; Andersons GRAINweb verdict (browser-only); merge plan extended to Cycle 12 |
| *(this commit)* | Cycle 13 report |

## 2. Test results

- **Full API suite: 590 passed, 0 failed** (Cycle 12 ended at 558).
  New tests in Cycle 13: per-location Bushel 30, PRO Coop 21302b 2
  = **32 new tests**.
- **Web build: `npm run build` passes** (re-run this cycle; no web
  files changed).

## 3. What was built (done)

### PRO Coop second 21302 embed — proven (13th embed site)
- `cashbids-js.php` URL derived from the saved Cycle 11 homepage
  (no homepage re-fetch; the second `<script>` sits in the
  homepage's `elementor-hidden-desktop` section, the mobile
  variant) → 200, `var bids` JSON, **12 rows, MANSON.IA (Corn 6,
  Soybeans 6)**.
- Key finding: the embed's fields list omits `delivery_end`, but
  the payload still carries `delivery_end` on all 12 rows, and the
  (commodity, delivery window, symbol, futures month) structure
  matches the first embed's saved Cycle 12 payload exactly — the
  two embeds serve the same Manson view. Parsed by the existing
  parser, no changes. Registered as `pro_coop_21302b` +
  `fetch_pro_coop_21302b()`, toml enabled, `config.toml` toggle,
  registry adapter wired by the coordinator, 2 new tests.
  The coordinator independently verified against the saved
  response: ok, 12 rows, MANSON.IA.

### Per-location Bushel sweep — 10 targets, all verified
- **11 GETs total, all HTTP 200** (1 PRO Coop + 10 locations).
  All standard wrapped 7-col `.cbmod` widgets (FAC shape); all
  parsed by the existing generic parser, no changes. The
  coordinator independently verified every target against the
  saved HTML — row counts and locations match exactly.
- **Skyland (6):** 2731 Conlen–Hartley 5 rows (Corn 2, Milo 1,
  Red Wheat 2); 2734 Etter 5 rows; 2740 Moscow, Dermot, Kismet,
  Pleasant Valley 7 rows (Corn 2, Milo 1, Red Wheat 2, Soybeans 1,
  White Wheat 1); 2742 Johnson–Ulysses–N Sublette 7 rows (Corn 2,
  Milo 1, Red Wheat 2, White Wheat 2); 2754 Olton Area 5 rows;
  2761 Elkhart–Hough–Rolla Area 6 rows (Corn 2, Milo 1, Red Wheat
  2, White Wheat 1). "White Wheat" passes through unmapped like
  "Red Wheat" (no parser change, noted in code/tests).
- **Smithfield (4):** 1725 Bladenboro 1 Soybeans row; 1667
  Bladenboro Feed Mill 2 rows (Corn 1, Wheat 1 — distinct from the
  1725 Elevator target); 2294 Chadbourn 1 Soybeans row; 1668
  Clarkton 1 Soybeans row. Location h2s carry ", NC" and are
  mapped to town names as with Bentonville. **Chadbourn's widget
  header is dated Nov 18, 2026 — a day older than all other Cycle
  13 pages** — flagged as a staleness watch, not a parser issue.
- 10 registry entries + `fetch_*()` wrappers, `config.toml`
  toggles, 10 new enabled toml entries, registry adapters wired
  by the coordinator, 30 new tests with synthetic fixtures.
  Skyland now 7 of 14 IDs verified; Smithfield 5 of ~31 locations
  verified (26 still open).

### The Andersons — GRAINweb investigation (research, no fetches)
- Analyzed the saved Cycle 11 HTML (23,263 bytes) with zero new
  HTTP requests. **Verdict: browser-only.** No static bid rows
  (the only `<table`/`price`/`basis`/`$+digit` hit is the modal
  heading "Bid and Basis Charts"); no `writeBidRow`, `.cbmod`, or
  `cashbids.php` markup; no `fetch(`, `XMLHttpRequest`, `.ajax(`,
  `axios`, or `getJSON` strings; no `/api/`, `.json`, or `endpoint`
  strings. GRAINweb appears only as plain links.
- The picker is one form (`POST /locations/cash-bids/Add`,
  CSRF-protected — token value deliberately not reproduced), an
  18-option location select, and an empty commodity select filled
  from inline `ANDERSONS_GRAIN_LOCATIONS` JSON (18 IDs; Corn
  everywhere, White Wheat only at Auburn/Hemlock/Oakley/Standish).
  The picker logic lives in the un-fetched bundle
  `/bundles/js/my-cash-bids?v=…` — the only place the endpoint
  could be named. Login links point to
  `/login?returnUrl=%2flocations%2fcash-bids%2f` (selections may be
  account-bound).
- **Next probe named (one GET, later cycle):** read that bundle
  verbatim and grep it for the picker's post target; secondary
  candidate is one GET of `/local-bids/locations-list/`. Stays
  `unknown`, still disabled. Findings written to the catalogue.

### Merge plan extended to Cycles 8–12
- New "Cycles 8–12 (added Cycle 13)" section, verified from git
  history and the cycle reports (coordinator re-verified the headline
  numbers: `master..cycle-12` = **43 commits**, 0 merges, tip
  `4b2472b`). Per-branch commit counts 8: 3, 9: 2, 10: 2, 11: 2,
  12: 2; test chain 407 → 407 → 454 → 488 → 536 → 558; Alembic
  head still `0019`; CI workflow file still untracked (with the
  Cycle 9 accidental-stage detail); new conflicts/overlaps
  (catalogue every cycle; `source_registry.py` in 9–12;
  `us_elevators_urls.toml` reclassifications; `bushel_source.py`
  tabbed fallback in Cycle 11). §§0–7 untouched.
- Also fixed by the coordinator: the deployment checklist's §8
  sign-off line still said head `0018` — corrected to `0019`.

### Super-plan progress — §9 extended to Cycle 12
- Heading/intro now cover Cycles 1–12 (test chain 179 → 558);
  Cycle 12 bullet added; blockers updated (embed family now 12
  sites at the time of writing — 13 after this cycle).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 13 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit; the only
matches in the super-plan/catalogue are pre-existing text). No
contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (3 sites: Frontier, CRC, UFC), and now
  The Andersons GRAINweb (browser-only verdict — needs a live
  browser session or the bundle read).
- Remaining Skyland picker IDs (7: 2763, 2766, 2770, 2771, 2778,
  3370, 3621) and Smithfield East Region locations (26 of ~31);
  Chadbourn staleness watch (Nov 18 header).
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–12: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons).

**New in Cycle 13:** nothing new needs Adam.
