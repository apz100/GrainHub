# Overnight Cycle 12 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-12` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 12 complete — West-Con regex fix, three embed
checks proven, three per-location Bushel probes.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `cfa6161` | West-Con regex fix unblocks 2 sites; Hull/StateLine/PRO-21302 embeds proven; per-location Bushel probes (Georgetown, Skyland 2730, Bentonville) |
| *(this commit)* | Cycle 12 report |

## 2. Test results

- **Full API suite: 558 passed, 0 failed** (Cycle 11 ended at 536).
  New tests in Cycle 12: per-location Bushel 9, embed checks 6,
  regex fix 7 = **22 new tests**.
- Web build was not re-run in Cycle 12 (no web files changed; last
  full pass Cycle 10).

## 3. What was built (done)

### West-Con regex fix — one fix unblocks two sites
- `_WRITEBIDROW_RX` in `us_agricharts_source.py` now accepts three
  delivery-window forms via a new `_MONTH_LABEL` / `_DELIVERY`
  pattern: `MM/DD/YYYY` (unchanged), month-name labels (`'Dec
  2026'`, `'January 2027'` — full or abbreviated month), and short
  month labels (`'Nov 26'`, `'Jan 27'` — 2-digit year). Group
  numbering is unchanged, so `fetch_us_agricharts` needed no logic
  change.
- **Decision (documented in the module docstring):** month-only
  windows are kept **verbatim** in the Delivery / Delivery End
  columns. No day is invented (no first-of-month synthesis) and no
  century is expanded for 2-digit years, because the source never
  states either; the label itself is the delivery window.
- **West-Con** — verified against the saved Cycle 11 HTML (no new
  fetch): fixed regex matches **84/84** rows (Corn 30 / Soybeans 44
  / DNS Wheat 10), 10 distinct month labels, start == end on all
  rows. Enabled in the toml.
- **Wheaton Dumont** — one polite GET of `/markets/cash.php`
  (200, 62,357 bytes): **43 static `writeBidRow` rows** (Corn 18 /
  Soybeans 16 / Spring Wheat 9, 8 `<h4>` locations). Surprise: its
  labels are the **short form** (`'Nov 26'`, `'Jan 27'`, 6
  distinct) — the first fix matched 0/43, so the year was extended
  to `(?:\d{4}|\d{2})`; fixed regex then matches **43/43**; 6 rows
  span two adjacent months (e.g. `'Oct 27'` → `'Nov 27'`).
  Reclassified `unknown → agricharts`, enabled, URL updated.
  No registry adapter needed for either site (the orchestrator
  drives `fetch_us_agricharts` from the toml).
- 7 new tests (month-name, short-month, MM/DD/YYYY regression,
  mixed page, mocked end-to-end fetch, row-count checks vs saved
  West-Con 84 and Wheaton Dumont 43 HTML). The coordinator
  independently re-verified the regex against both saved pages:
  84 and 43 matches.
- One real bug caught during verification: the first edit dropped
  the opening quote before the delivery group and matched 0 rows;
  the saved-HTML check caught it before any test was written.

### AgriCharts `cashbids-js.php` checks — all three proven
- **GET budget: 5/5 used, no retries.** Hull + StateLine each took
  a page GET (to derive the loader URL) + a js.php GET; PRO Coop
  21302's URL came from the saved Cycle 11 homepage (no re-fetch).
- **Hull Coop** (`hullcoopresp.agricharts.com`,
  `groupby=ccommodity`, filter=all): js.php 200, `var bids` JSON,
  **12 rows, 1 location (Hull, IA): Corn 6, Soybeans 6.** Loader
  src carries `hidenav=1&&showchart=1` (double ampersand
  mid-query), kept verbatim in the registry URL.
- **StateLine Coop** (`statelinecoop.agricharts.com`,
  `groupby=location`, filter=all): js.php 200, `var bids` JSON,
  **126 rows, 11 locations** (Armstrong, Blue Earth, Cylinder,
  Emmetsburg-AGP, Fenton, Lakota, Ledyard, Marna, North Burt,
  Ringsted, Swea City): Corn 60, Soybeans 66. Emmetsburg-AGP is
  Soybeans-only (6 rows); every other location 12 rows.
- **PRO Coop 21302, first embed** (`procooperative.agricharts.com`,
  `groupby=ccommodity`): js.php 200, `var bids` JSON, **12 rows, 1
  location (MANSON.IA): CORN 6, SOYBEANS 6.** The loader src
  carries literal newlines in `fields`, percent-encoded to `%0A`
  on the wire — registry URL uses the `%0A` form, matching the
  Cycle 11 21297 entry's method.
- All three parsed status ok with the existing parser — no parser
  change, no skipped rows, no missing-field notes. Registry entries
  (`hull_coop`, `stateline_coop`, `pro_coop_21302`, all
  verified=True) + `fetch_*()` functions, toml enabled, `config.toml`
  toggles, registry adapters wired by the coordinator, 6 new tests
  with synthetic fixtures. Embed family now **12 sites**. The
  coordinator independently re-verified all three against the saved
  js responses: 12 / 126 / 12 rows, 1 / 11 / 1 locations.
- **Still open:** PRO Coop's **second** 21302 embed (fields
  `delivery_start` / `price` / `basis` / `futureschange`, no
  `delivery_end`) — 1 GET in a later cycle, derivable from the
  saved homepage.

### Per-location Bushel probes — all three verified
- **Winchester 3440** (`/cashbidssingle-3440?embed=y`): 200,
  **5 rows, Soybeans only** — and the location h2 reads
  **"Georgetown"**, not Winchester: the 3440 embed serves Wheaton's
  Georgetown location (3439 is Winchester). Registered as
  `winchester_3440` with `default_location="Georgetown"`, fact
  noted in the registry, toml, and catalogue. Standard wrapped
  7-col shape; parser ok, no change. The coordinator independently
  verified against the saved HTML: ok, 5 rows, Georgetown.
- **Skyland 2730** (`/cashbidssingle-2730`): 200, **6 rows** (Corn
  2, Milo 1, Red Wheat 2, Soybeans 1) — **2730 duplicates the
  default Skyland page**: it is Cunningham Area's own per-location
  ID, same 6-row breakdown as the existing `skyland` entry.
  Registered anyway, duplication noted. The static page carries no
  picker links, so the ID→town mapping for the other 13 picker IDs
  can only be learned by probing each.
- **Smithfield 1666** (`/cashbidssingle-1666`, Bentonville): 200,
  **3 rows** (Soybeans 1, Wheat 1, Corn 1). Standard wrapped 7-col
  shape; parser ok, no change. First verified Smithfield location.
  Location label "Bentonville, NC" maps to "Bentonville".
- 9 new tests (registry + fixture parse + mocked fetch per site),
  registry adapters wired by the coordinator, `config.toml`
  toggles, 3 new enabled toml entries.

### Super-plan progress — §9 extended to Cycle 11
- Heading/intro now cover Cycles 1–11 (test chain 179 → 536);
  Cycle 11 bullet added; blockers updated (embed family now 9
  sites at the time of writing — 12 after this cycle's checks;
  FMN collector complete for the default view).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 12 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit; the only
matches in the super-plan/catalogue are pre-existing text). No
contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (3 sites: Frontier, CRC, UFC).
- PRO Coop second 21302 embed (1 GET); remaining 13 Skyland picker
  IDs and ~29 other Smithfield East Region locations (one GET
  each); Andersons GRAINweb investigation.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–11: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX).

**New in Cycle 12:** nothing new needs Adam.
