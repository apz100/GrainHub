# Overnight Cycle 10 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-10` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 10 complete — FMN writeBidRow collector, 19-site US
sweep, Synergy registered, currency design note, web build re-verified.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `52c6d42` | FMN writeBidRow collector (453 rows, 87 points); 19-site US sweep (13 reclassified, Sunrise enabled, Synergy registered); currency design note |
| *(this commit)* | Cycle 10 report |

## 2. Test results

- **Full API suite: 488 passed, 0 failed** (Cycle 9 ended at 454).
  New tests in Cycle 10: FMN collector 31, Synergy 3 = **34 new
  tests**.
- **Web build: `npm run build` passes** (re-run this cycle; no web
  files changed since Cycle 5, 30 `page.tsx` files).

## 3. What was built (done)

### FMN cash-page collector — `fmn_source.py` (31 tests)
- **Key discovery: the page is NOT plain HTML tables.** The 204 bid
  tables are real `<table class="homepage_quoteboard">` elements,
  but the data rows are JavaScript — one `writeBidRow(...)` call per
  row inside each `<tbody>` (454 occurrences on the page, of which 1
  is the function definition, so **453 row calls**). The parser reads
  those calls from static HTML (balanced-paren scan + quote-aware
  arg splitter, no JS execution, no browser). The `writeBidRow`
  function definition sits in a standalone script block and is
  explicitly excluded (tested).
- **Verified live with one polite GET** (200, 353,938 bytes, saved
  to `/tmp/fmn/` scratch only; the coordinator re-fetched once to
  independently verify counts after the worker's scratch file was
  lost — same byte size, same counts): **204 tables, 453 rows, 87
  distinct delivery points** — Corn 151, Soybeans 145, wheat 153
  (SRW 86, HRW 30, SWW 22, HRS 15), Barley 2, Oats 2; 4 manual rows,
  449 futures-linked rows. Dropdown confirmed at 336 options, so the
  default view is still not the complete FMN set.
- **The 87th point vs Adam's 86 (2026-11-18 read) is "US Rep"**
  (`US Rep Corn`, symbol ZCZ26) — a real table the earlier read did
  not list. The parser reports what the page titles.
- Parser decisions: title → location/commodity by stripping the
  trailing crop word (plain title = wheat table); locations kept
  verbatim (incl. `Chatham-Kent Avg`, `London Avg`, `Huron FOB`,
  `Quebec FOB`, `Port Colborne Transfer`, the page's own doubled
  `Hamilton Transfer Transfer`); wheat-class row names kept verbatim
  (`HRW New Crop Wheat`, …) with commodity canonicalised to
  `Wheat — HRS/HRW/SRW/SWW`; delivery labels kept verbatim as month
  labels; basis kept exactly as published (cents scale, NOT divided
  by 100, per the repo's "published numbers, NOT normalized"
  convention, with a unit note on each row); futures month decoded
  from the contract symbol (`ZCZ26` → Dec 2026, `ZSF27` → Jan 2027,
  `MWU27` → Sep 2027 — symbol decoding, not a feed reading);
  settlement is the literal fallback `"0-0"` on every row.
- **Barley/oats manual rows** (19-arg calls, no quote arg, only at
  Hensall HDC and Sunderland): cash = `basis / 100` per the page's
  own deterministic render rule, `unit="$/t"`,
  `cash_price_mt` = same number; basis/futures/change `None` with a
  "manual row" note.
- **Known gap — futures price / change / cash price are NOT in the
  static HTML.** They come from a separate `<script src>` feed
  (`jsquote.php?varname=quotes&symbols=…10 symbols…&fields=name,month,last…`)
  that populates the `quotes` dict the calls reference. It was
  deliberately NOT fetched (one-GET scope); those three fields are
  `None` with an explanatory note on futures-linked rows, never
  invented. A later cycle can fetch the jsquote feed (one GET) or
  render with Playwright to fill them.
- **Currency (CAD) and units ($/bu)** are recorded by FMN Ontario
  convention — inferred, not labelled on the page (the static HTML
  contains no CAD/CDN/tonne/bushel text at all); flagged in the
  module docstring, to confirm against a rendered page. The page
  publishes no as-of date, so `date` = fetch date
  (America/Toronto), overridable via `as_of`.
- Wired in: `source_registry.py` adapter (`fmn` →
  `fetch_fmn_cash`), `config.toml` toggle (`fmn = true`), catalogue
  FMN section updated with the Cycle 10 collector note.

### 19-site US sweep — 13 reclassified
- One polite GET per site (19 total, ~2 s spacing, 30 s timeout,
  no retries). The 7 already-resolved `unknown` entries were not
  re-fetched. **Counts: 15× HTTP 200; 4 non-200/blocked; 2 sites
  with static rows (9 rows total); 9 JS-only/widget-identified; 4
  with no widget at the probed URL.**
- **Reclassified:** CVA → unreachable (202, empty body, same as
  Cycle 1); Landus → unreachable (429, Vercel Security Checkpoint,
  JS required, no retry); Mercer Landmark → unreachable (522, empty
  body, same as Cycle 1); PRO Coop → agricharts-embed (3
  `cashbids.php` embeds, locations 21297 + 21302; `cashbids-js.php`
  check is the next step, still disabled); Ray Carroll → dtn (DTN
  `index.cfm` iframes ×4); Skyland Grain → bushel (Bushel FCCP
  family, no widget on homepage); Smithfield → bushel (Bushel FCCP
  family, futures table only; bids on
  `/fccp-cash-bids-east-region-20249`); Star of the West → none
  (milling homepage, zero bid mentions, do not add); **Sunrise →
  dtn, enabled** (classic DTN: `<div id="target">` +
  `CashBidTable(tableOptions)`, companyID 23043 — exactly what
  existing `us_dtn_source.py` handles; same precedent as Al-Corn,
  which is enabled; Playwright render check still open); Synergy →
  bushel (static rows, see below); UFC → stonex (redirects to
  `centralunitedcoop.com` — same site/org as CRC; StoneX family now
  3 sites: Frontier, CRC, UFC, still no static route); Wheaton
  Grain → bushel (static rows, parser gap — see below); Winchester
  Ag → bushel (redirects to a Wheaton Grain FCCP page; two
  `/cashbidssingle-` embeds, 3439/3440).
- **Kept unknown (annotated):** Hull Coop (404 at `/cash-bids`,
  but the 404 page links `/cashbids` — probe that slug next);
  Pro Ag (AgriCharts-hosted homepage, nav links
  `/markets/cash.php`); StateLine Coop (homepage serves normally
  now — **no Cloudflare challenge this time**, Cycle 1 reported
  one; `/cash-bids` linked); The Andersons (corporate homepage,
  `/locations/cash-bids/` linked; distinct from Andersons Canada);
  West-Con + Wheaton Dumont (AgriCharts-hosted, JS-filled homepage
  widget, probe `/markets/cash.php`). `unknown` count in the toml
  is now 13.
- **Synergy — collector-ready, registered this cycle:** static
  Bushel `.cbmod`, 4 rows (Corn 2 + Soybeans 2, Cameron), 6-col,
  dated Nov 19, 2026. The coordinator independently verified
  `parse_bushel_html` against the saved HTML returns status ok, 4
  rows. `BUSHEL_SITES` entry + `fetch_synergy()` added (3 tests,
  synthetic fixture), registry adapter + `config.toml` toggle, toml
  enabled. Catalogue updated.
- **Wheaton Grain — parser gap found (new shape variant):** static
  Bushel `.cbmod`, 5 rows (Corn 2 + Soybeans 3, Chippewa Falls),
  6-col — but the widget is tabbed (`easyResponsiveTabs`) with bare
  `h3.fcControls` headings and **no `div.cbCommodity` wrapper**, so
  the generic parser returns "empty" despite 5 visible rows (the
  coordinator independently confirmed: status "unsupported", 0
  rows). A later cycle needs a small `_parse_widget` fallback; no
  collector built here.
- TOML re-validated by parse (76 elevators). Raw HTML in
  `/tmp/cycle10/` scratch only. No prices copied into docs.

### Currency design note — `docs/plans/currency-design.md`
- Design-only proposal for Adam's decision; no migration landed, no
  code changed. Documents the `currency: null` gap (Cycle 2):
  `NormalizedPrice` stores prices with no currency column, while
  collectors already know it per row (Bushel USD except Collwest
  CAD; Collwest CAD; cashbids-embed USD; Five Star USD; FMN CAD
  by convention; USDA mirrors USD). Proposes migration `0020`
  (nullable ISO-4217 `currency` on `normalized_prices`, backfill
  only where unambiguous), ingestion from the collectors' row
  currency, per-row currency in API responses, and **no silent
  conversion at ingest** — store source currency, convert only for
  display with a labelled FX rate. Decisions for Adam: store vs
  convert at ingest (recommends store), FX source (Bank of Canada
  daily rate, already used by legacy CashGrainBids), mixed-currency
  list behaviour (recommends group-by-currency by default), backfill
  scope.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 10 code, tests, fixtures, or docs
(verified by grep on the new/changed lines). The FMN page lists a
"North Gower" delivery point among its 87 — it is one ordinary
location in the source data, used nowhere as an example, pilot,
fixture name, or featured location (fixtures/examples use Alliston,
Hensall HDC, Chatham-Kent Avg, Quebec FOB). No contact made.

## 5. What is still scaffold / stub

- FMN futures price / change / cash price need the `jsquote.php`
  feed (one GET) or a Playwright render; FMN currency/units need a
  rendered-page confirmation; FMN dropdown filter needs a Playwright
  render check (Winchester `location_filter=2523`).
- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view, Mapleview, StoneX family (now 3
  sites: Frontier, CRC, UFC).
- Wheaton Grain Bushel parser gap (tabbed widget, no
  `div.cbCommodity`); PRO Coop `cashbids-js.php` check; sub-page
  probes (Hull `/cashbids`, Pro Ag / West-Con / Wheaton Dumont
  `/markets/cash.php`, StateLine `/cash-bids`, Andersons
  `/locations/cash-bids/`, Skyland `/cashbidssingle-`, Smithfield
  East Region page, Winchester embeds 3439/3440).
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written this cycle — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–9: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX).

**New in Cycle 10:** the currency design note adds four concrete
decisions (store vs convert at ingest; FX source; mixed-currency
list behaviour; backfill scope) — see
`docs/plans/currency-design.md`.
