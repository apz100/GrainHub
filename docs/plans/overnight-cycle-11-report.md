# Overnight Cycle 11 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-11` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 11 complete — FMN jsquote feed fills all rows, PRO
Coop embed proven, Wheaton tabbed-widget fix, sub-page sweep with a
coordinator correction (Skyland).

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `fd8d58e` | FMN jsquote feed fills 449/449 rows; PRO Coop embed proven; Wheaton tabbed-widget fix; sub-page sweep (Pro Ag, Winchester, Skyland corrected + registered) |
| *(this commit)* | Cycle 11 report |

## 2. Test results

- **Full API suite: 536 passed, 0 failed** (Cycle 10 ended at 488).
  New tests in Cycle 11: FMN jsquote 13+ (file grew substantially
  with quotes/cash-rule/fetch-plumbing tests), PRO Coop embed 4,
  Wheaton tabbed widget 6, Skyland + Winchester 6 = **48 new tests
  net** (536 − 488).
- Web build was not re-run in Cycle 11 (no web files changed; last
  full pass Cycle 10).

## 3. What was built (done)

### FMN jsquote feed — the Cycle 10 gap is closed
- One polite GET of the feed URL verbatim from the saved FMN page
  (`agricharts.com/marketdata/jsquote.php?varname=quotes&symbols=
  ZWN27,ZWZ26,ZCZ26,ZCZ27,ZSF27,ZSX27,MWU27,MWZ26,ZCH27,ZSH27&
  fields=name,month,last&…`) → **200, 9,445 bytes, `var quotes` with
  all 10 symbols**, each with rawLast/change/month/exchange. (The
  empty `user=`/`pass=` params in the URL are the page's own
  public-feed params, not credentials.)
- `fmn_source.py` now parses the feed (`parse_quotes_feed()` —
  brace-matching JS-literal parser, anchored field regex so `change`
  never matches inside `exchange`) and fills `futures_price` /
  `change` / `cash_price` on futures-linked rows via
  `quote_to_dollars()` / `quote_cash_price()`, replicating the page's
  own `writeBidRow` render rule (verified from the saved HTML:
  `price = rawLast × (WCE ? 100 : 1)`; MW/ZR/ZM → `price + basis/100`
  in dollars; otherwise `(price + basis)` cents with the 0.5
  whole-cent floor/ceil step, `/100`). Unit facts verified from the
  feed: CBOT quotes in cents (`/100` for dollars); MW quotes
  (exchange MIAX, basecode `C`) in dollars as-is; no `unitcode`
  field; exchangeRate `1`; `currConv` false.
- **Live verification (scratch, counts only; independently
  re-verified by the coordinator against the saved page + feed):
  453 rows, 449 futures-linked, all 449 filled, 0 unfilled; 4
  manual barley/oats rows unchanged.** Missing-quote rows stay
  `None` with a "no quote for SYMBOL" note; `fetch_fmn_cash()`
  degrades gracefully to page-only with a note if the feed fetch
  fails or returns no symbols. The FMN collector is now complete
  for the default view — only the dropdown filter (335 points) still
  needs a Playwright render check.

### PRO Coop cashbids embed — proven (9th embed site)
- GET 1: homepage (200, 335 KB) carries 3 AgriCharts `cashbids.php`
  loader embeds (`procooperative.agricharts.com`): location 21297
  (`groupby=location`) + location 21302 twice
  (`groupby=ccommodity`).
- GET 2: loader-derived `cashbids-js.php` URL for the 21297 embed
  (verbatim, `noscript=1` & `acCnt=1` per the module's documented
  method) → **200, 36 KB, `var bids` JSON: 1 group, 6 rows, 1
  location (AYRSHIRE.IA), all Corn, all active, none login-gated.**
  Existing parser handles it (status ok). `fetch_pro_coop()` added,
  toml enabled, `config.toml` toggle, 4 tests with synthetic
  fixtures (incl. login-gated + inactive skipping), registry test
  updated 8 → 9 sites, registry adapter wired by the coordinator.
- **Caveat:** this entry covers the 21297 Ayrshire view only — the
  two 21302 embeds were not checked (GET budget). One GET in a later
  cycle if a second PRO Coop view is wanted.

### Wheaton Grain tabbed-widget parser fix
- The Cycle 10 gap is closed: `_parse_widget` now falls back to
  `_parse_tabbed_widget` when a `.cbmod` widget contains no
  `div.cbCommodity` sections. The fallback reads the location from
  the `ul.resp-tabs-list` tab label, pairs each
  `div.resp-tabs-container` panel with its tab by index, and parses
  `h3.fcControls` headings + following row `ul`s with the shared
  row-group parser (the ul-row loop was refactored out of
  `_parse_commodity_section` into `_parse_row_ul_group`, so the
  row-dict shape is identical). The wrapped path is untouched.
- Also added `"cash": "cash_price"` to `HEADER_FIELDS` (Wheaton's
  Corn section heads the Bid column "Cash"). No existing fixture
  uses a bare "Cash" header, so no existing behaviour changes.
- **Verified against a fresh live GET** (200, 142 KB): the parser
  now returns status ok, **5 rows (Corn 2 + Soybeans 3, Chippewa
  Falls)**; before the fix it returned "empty". 6 tests, registry
  entry + `fetch_wheaton_grain()`, registry adapter + `config.toml`
  toggle, toml enabled. (Multi-tab pairing is reasoned, not
  live-verified — Wheaton has a single tab.)
- **Fixture lesson (coordinator):** the row parser only accepts
  `fcControls1`/`fcControls2` row `ul`s — live pages alternate
  those two classes. A Winchester fixture written with
  `fcControls1`–`5` parsed 4 rows instead of 10; fixed by matching
  the live alternation. No parser change needed.

### Sub-page sweep — 9 GETs, all 200
- **Pro Ag** (`/markets/cash.php`): **78 `writeBidRow` rows** (Corn
  / Soybeans / Wheat, 6 `h4` locations), all 78 match the existing
  `us_agricharts_source.py` `_WRITEBIDROW_RX`. Reclassified
  `unknown → agricharts`, enabled. No registry adapter needed —
  the orchestrator drives `fetch_us_agricharts(url, name)` from
  the toml.
- **Winchester 3439** (`/cashbidssingle-3439?embed=y`): **10 rows**
  (Corn 5 + Soybeans 5, Winchester), standard wrapped 7-col
  `.cbmod`, parser ok with no changes. Enabled; `BUSHEL_SITES`
  entry + `fetch_winchester()` added (6 tests). The 3440 target
  stays open.
- **West-Con** (`/markets/cash.php`): **84 `writeBidRow` rows** —
  but delivery dates are month-name labels (`'Dec 2026'`), so the
  existing regex matches **0/84**. Parser gap recorded; a small
  regex extension unblocks it (and probably Wheaton Dumont too).
  Reclassified `unknown → agricharts`, still disabled.
- **Hull Coop** (`/cashbids`) + **StateLine Coop** (`/cash-bids`):
  AgriCharts `cashbids.php` embeds, no static rows.
  Reclassified `unknown → agricharts-embed`, still disabled;
  `cashbids-js.php` checks open.
- **The Andersons** (`/locations/cash-bids/`): proprietary GRAINweb
  "MyCashBids" interactive location-picker; no static rows, no
  embed. Stays `unknown`; needs a browser/API investigation.
- **Smithfield** (East Region page): per-location link list (~30
  locations); no static rows. Stays `bushel`; probe one
  `/cashbidssingle-<id>` target next (e.g. 1666 Bentonville).
- **Skyland — coordinator correction (see §4).**
- Wheaton Dumont's `/markets/cash.php` probe was dropped to stay in
  the 9-GET budget (Skyland took 2 GETs); still open.

### Super-plan progress — §9 extended to Cycles 8–10
- Heading/intro now cover Cycles 1–10 (test chain 179 → 488);
  bullets added for Cycles 8, 9, 10; blockers updated (embed family
  now 8 sites, FMN collector built, Five Star collector built, cashbids
  counts, Sunrise as a second classic-DTN fit, currency design note).

## 4. Correction — Skyland Grain (sweep worker was wrong)

- The Cycle 11 sweep worker reported that Skyland's
  `/cashbidssingle-` target serves only a 14-location picker with
  "no `.cbmod` widget, no bid rows". **That was wrong.** The
  coordinator re-checked with a fresh GET: the page serves the
  picker **and** a static 7-col Bushel `.cbmod` widget for the
  default location — **6 rows (Corn 2, Milo 1, Red Wheat 2,
  Soybeans 1, Cunningham Area)**, parser status ok. The worker's
  own saved HTML parses ok too; it evidently only inspected the
  picker. Same canonical trailing-dash pattern as Williams Gin
  (Cycle 5).
- **Corrected in the repo:** catalogue Skyland rows (Cycle 10
  annotation + Cycle 11 section + counts: static-rows sites 3 → 4,
  picker-only 2 → 1), toml entry (URL updated to
  `/cashbidssingle-`, enabled), `BUSHEL_SITES` entry +
  `fetch_skyland()` (6 tests, synthetic fixture), registry adapter
  + `config.toml` toggle. Per-location `/cashbidssingle-<id>`
  targets are still open.

## 5. North Gower Grains boundary — applied

Zero references in any new Cycle 11 code, tests, fixtures, or docs
(verified by grep on the new/changed lines). The FMN data lists it
as one ordinary location among 87; fixtures/examples use Alliston,
Hensall HDC, Chatham-Kent Avg, Quebec FOB. No contact made.

## 6. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (now 3 sites: Frontier, CRC, UFC).
- West-Con regex gap (month-name delivery labels, 0/84 matched);
  Wheaton Dumont `/markets/cash.php` probe; PRO Coop 21302 embeds;
  Winchester 3440 target; Skyland/Smithfield per-location targets;
  Andersons GRAINweb investigation.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 7. Blocked / needs Adam

Carried from Cycles 1–10: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX).

**New in Cycle 11:** nothing new needs Adam.
