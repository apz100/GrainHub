# Overnight Cycle 24 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-24` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 24 complete — AgriCharts fallback (a) implemented and
tested; (b) probe fails on Heartland (and corrects the Cycle 21–23
finding); staleness daytime re-check: none of the four refreshed;
merge plan extended to Cycle 23, super-plan §9 extended to Cycle 23.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `2120e29` | AgriCharts fallback (a) implemented; (b) probe fails on Heartland; staleness watch 4th consecutive; merge plan extended to Cycle 23 |
| *(this commit)* | Cycle 24 report |

## 2. Test results

- **Full API suite: 702 passed, 0 failed** (Cycle 23 ended at 697).
  New tests in Cycle 24: **5** (all in
  `tests/test_us_agricharts_source.py`).
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### AgriCharts fallback, option (a) — implemented + tested

Coordinator decision (Cycle 24, recorded in the design doc §9):
option (a) from the Cycle 23 design note is **APPROVED** — (i)
basis-only rows MAY flow into the pipeline (futures/cash explicitly
`None` with a note, never invented; no quarantine, same as FMN
today); (ii) YES, decode Futures Month from the symbol.

- `fetch_us_agricharts` (`us_agricharts_source.py`) no longer
  returns an empty DataFrame when the jsquote tag is absent or
  unmatched. It parses the `writeBidRow` rows as basis-only:
  Basis / Delivery / Delivery End / Location / Name / futures
  symbol as published; **Futures Month decoded from the contract
  symbol** via a new `futures_month_from_symbol()` (same month-code
  map and regex as `fmn_source.futures_month_from_symbol`, copied
  locally to avoid an import coupling, since this module is also
  imported standalone by GrainBidder); **Futures Price / Change /
  Bushel Cash Price / MT Cash Price = `None`**, never invented.
- New `Note` column (FMN pattern): basis-only rows carry
  *"Basis as published; futures price, change and cash price come
  from the page's external quotes feed (jsquote.php) and are not in
  the static HTML — left as None, never invented; futures month
  decoded from the contract symbol"*; feed-backed rows carry `""`,
  so the schema is stable across both paths. Downstream GrainBidder
  selects a fixed column list, so the extra column is dropped at
  output and is harmless.
- Tag-present behaviour is **exactly unchanged**, including the
  existing early return when the tag is present but the feed returns
  no data. Chrome UA unchanged. No config, registry, or `app/main.py`
  changes. **Toggles stay `false`.**
- 5 new tests (synthetic fixtures, neutral `Test Elevator` /
  `Testville` names): (a) no-tag page → 4 rows, basis filled,
  futures/cash all `None` (asserted not `""` and not `0`), note
  present, exactly one GET (no feed fetch attempted); (b) Futures
  Month decoded (`ZCZ26 → Dec 2026`, `ZSF27 → Jan 2027`, `ZSN27 →
  Jul 2027`) plus a decoder unit test (`None`/`""`/unrecognised →
  `None`) — the worker's first expectation for `ZSN27` was wrong
  (`N` is July, not November); the test docstring records this;
  (c) tagged page with mocked feed → behaviour exactly as before
  (futures filled, feed months verbatim, cash filled, Note `""`);
  (d) no-tag page with no rows → empty DataFrame, no crash.
  Coordinator independently verified the diff and the suite (702
  passed; `test_us_agricharts_source.py` 16 passed).
- **Live verification (2 GETs): Heartland 0 rows, Mulvane 0
  rows.** Both pages' `writeBidRow` rows are no longer matched in
  the static HTML at all — the design doc's §3 assumption (rows
  still in the HTML) does **not** hold live as of this probe. So
  (a) is implemented and proven by mocked tests but recovers
  neither site today. No live price/basis/bid values recorded.
- Scope note: degrading the same way when the tag IS present but
  the feed fetch fails was NOT implemented (the task kept
  tag-present behaviour exactly unchanged). It is a one-line
  follow-up: treat empty quotes like the no-tag path.

### Option (b) probe — Heartland: fails (2 GETs)

- **Correction to Cycles 21–23:** Heartland's jsquote tag is **not
  missing** — it is present but with an **empty symbols list**
  (`symbols=&fields=name,month,last...`). The collector's regex
  requires `[A-Z0-9,]+` after `symbols=`, so it does not match and
  the collector reports "tag not found". The design doc §1 wording
  ("stopped carrying the jsquote.php script tag") is inaccurate for
  the current page and is corrected in design-doc §9. (Mulvane's
  tag state was not re-checked this cycle.)
- The derived feed URL (exact design-doc pattern) returned HTTP
  200, 20 bytes, body exactly `var quotes = null;` — the endpoint
  is alive and the URL shape is confirmed correct, but with an
  empty symbol list there is nothing to query: 0 symbols, nothing
  usable. **(b) fails because there is nothing to query**, not
  because of a 404 or wrong shape.
- **Deeper finding:** Heartland's default "All Locations" view
  carries **zero `writeBidRow` data rows** in the static HTML (the
  single occurrence is the function definition; no `<h4>` headings,
  no quoteboard tables). The bid area is empty. The page does have
  a Location filter (107 options: "All Locations" + 106 named
  delivery points) and a commodity filter, plus "Export to
  Spreadsheet" / print links. No bid-data AJAX/fetch was found in
  the static HTML.
- **Open hypothesis (untested, needs 1 GET):** rows may appear only
  when a `location_filter` value is selected. Follow-up probe (1
  GET, later cycle): `cash.php?location_filter=<one id>`. Mulvane
  was not probed for (b) (gated on Heartland's feed answering —
  it did not).

### Staleness daytime re-check — none refreshed (4 GETs)

Daytime re-check (Thu, Nov 19) of the four one-day-stale Bushel
widgets: **none refreshed to Nov 19**. All four still carry the
header "Cash bids for Wednesday, November 18, 2026"; zero Nov 19
date strings anywhere in any page. The widgets do not refresh later
in the day, at least not by the morning check.

| Site | Header | Rows | Streak |
|---|---|---|---|
| Smithfield Chadbourn 2294 | Nov 18 | 1 Soybeans | Cycles 13, 14, 22, 24 (4th) |
| Smithfield Hamer, SC 2179 | Nov 18 | 1 Soybeans | Cycles 16, 22, 24 (3rd) |
| Skyland Hugoton, KS 3370 | Nov 18 | 6 (Corn/Milo/Red Wheat) | Cycles 14, 22, 24 (3rd) |
| Skyland Vilas-Walsh 3621 | Nov 18 | 5 (Corn/Milo/Red Wheat) | Cycles 14, 22, 24 (3rd) |

All still exactly one day stale — no worse. The refresh-later-in-
the-day hypothesis is now answered (no), so no further daytime
re-checks are needed. Standing note stands: a same-day freshness
gate would fail these four daily, so they need an exemption/lag
tolerance if such a gate is ever added.

### Merge plan extended to Cycle 23

New "Cycle 23 (added Cycle 24)" section, verified from git history
and the cycle report (coordinator spot-checks: chain
`master..cycle-23` = **65 commits**, 0 merges; tip `9f534e6`;
Cycle 23 added 2 commits; test count 697; Alembic head still
`0019`; CI workflow file still untracked). 230 lines added, 0
removed. The Cycle 22 section's "63 commits" figure re-verified
correct.

### Super-plan §9 extended to Cycle 23

Heading/intro now cover Cycles 1–23 (test chain 179 → 697); Cycle
23 bullet added; blockers updated (Heritage confirmed, Heartland/
Mulvane toggles off, fallback design note, UA decision).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 24 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland filtered-view probe (`cash.php?location_filter=<id>`,
  1 GET) — the next step for the two dark AgriCharts sites;
  Mulvane's page structure not yet inspected. Feed-down degradation
  (tag present, feed fails) is a one-line follow-up.
- Staleness watch: the four widgets stay on the exemption list for
  any future freshness gate.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–23: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 24:** nothing new needs Adam. The AgriCharts
fallback (a) approval — flagged for the coordinator in Cycle 23 —
was decided by the coordinator this cycle and is now implemented.
