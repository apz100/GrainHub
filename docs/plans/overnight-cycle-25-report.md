# Overnight Cycle 25 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-25` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 25 complete — Heartland filtered view empty (hypothesis
closed), Mulvane re-checked empty (tag correction extended), feed-down
degradation implemented, merge plan extended to Cycle 24, super-plan §9
extended to Cycle 24.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `c4b221b` | Heartland filtered view empty, Mulvane re-checked empty; feed-down degradation; merge plan extended to Cycle 24 |
| *(this commit)* | Cycle 25 report |

## 2. Test results

- **Full API suite: 704 passed, 0 failed** (Cycle 24 ended at 702).
  New tests in Cycle 25: **2** (parametrized feed-down cases).
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Heartland filtered-view probe — hypothesis closed (1 GET)

`cash.php?location_filter=22143` (ADM – DSM, first named option in
the page's 106-location filter): HTTP 200, 36,246 bytes. The server
honoured the filter (option marked selected), but the page still
carries **0 `writeBidRow` data rows** and the jsquote tag still has
empty symbols. The Cycle 24 open hypothesis — rows appear only under
a selected location — does **not** hold for the tested location.
There is no usable filtered-URL pattern for the collector; the feed
question is moot. Caveat: only one location id was tested, but
default + one filtered view both returning zero rows with empty
symbols makes a per-location difference unlikely. No live price,
basis, or bid recorded.

### Mulvane default view re-checked (1 GET)

`https://www.mulvanecoop.com/markets/cash.php`: HTTP 200, 33,214
bytes, **0 `writeBidRow` rows**. **Correction:** Mulvane's jsquote
tag is **present with empty symbols**, not missing — the Cycle
21–23 "tag missing" phrasing is corrected for Mulvane too. The page
has a Location filter (4 named: Clearwater 3866, Clearwater-253
80891, Mulvane 3864, Mulvane-251 80889) and a Commodity filter
(Wheat HRW 2461, Corn 2462, Milo 2463, Soybeans 2464).
**Both sites stay dark; toggles stay off.** Option (a) still
recovers neither site live because the rows are not in the static
HTML at all. **Heartland / Mulvane are closed for now** — default
view, one filtered view, and the feed derivation all return nothing.
No further probes without a new hypothesis (e.g. a JS-rendered
route, or a different AgriCharts host).

### Feed-down degradation — implemented (mocked tests only, 0 GETs)

Tag present + jsquote feed returns empty (`var quotes = null;` or
`{}`) now degrades like the no-tag path instead of returning an
empty DataFrame: rows return basis-only (futures/cash `None` with
note, month decoded from symbol). No new code path was needed for
the rows themselves — the Cycle 24 degraded branch already handles
`degraded=True` regardless of cause. 2 new parametrized tests (both
empty-feed shapes) plus a called-URL assertion on the existing
with-data regression guard (proving both page and feed are fetched
on the with-data path). Tag-absent and tag-present-with-data paths
unchanged; Chrome UA, toggles, registry untouched. Coordinator
independently verified the suite (704 passed; targeted file 18
passed).
Scope note: only the *empty-quotes* case degrades. If the feed
fetch itself raises (HTTP error/timeout), the outer `except` still
returns an empty DataFrame — a further one-line follow-up if wanted.

### Merge plan extended to Cycle 24

New "Cycle 24 (added Cycle 25)" section (285 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-24` = **67 commits**,
0 merges; tip `f90cb8b`; Cycle 24 added 2 commits; test count 702;
Alembic head still `0019`; CI workflow file still untracked; Cycle
24 diff 7 files, 788 insertions, 33 deletions). The Cycle 23
section's "65 commits" figure re-verified correct. The worker
correctly noted the uncommitted Cycle 25 feed-down work in the
working tree while writing (it has now landed in this cycle's
commit).

### Super-plan §9 extended to Cycle 24

Heading/intro now cover Cycles 1–24 (test chain 179 → 702); Cycle
24 bullet added; blockers updated (fallback (a) done, (b) fails,
staleness daytime re-check answered).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 25 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (see §3). Feed-error
  degradation (outer `except` path) is a one-line follow-up.
- Staleness watch: the four widgets stay on the exemption list for
  any future freshness gate (no further re-checks needed).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–24: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 25:** nothing new needs Adam.
