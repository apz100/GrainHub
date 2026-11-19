# Overnight Cycle 29 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-29` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 29 complete — Bushel per-location sample re-verified
6/6 exact matches; Mae-Mart still viable as-is (page byte-identical
to Cycle 18, proxy shape identical to Cycle 19); merge plan extended
to Cycle 28, super-plan §9 extended to Cycle 28.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `3a47b4c` | Bushel sample re-verified 6/6; Mae-Mart still viable; merge plan extended to Cycle 28 |
| *(this commit)* | Cycle 29 report |

## 2. Test results

- **Full API suite: 709 passed, 0 failed** (unchanged — docs/research
  only cycle, no code changed). Coordinator re-ran the suite to
  confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample re-verification — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycles 13–16 baselines. Counts
only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2731 Conlen–Hartley | 5 | Nov 19 | Exact match |
| Skyland 3370 Hugoton, KS | 6 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 1691 Waverly, VA | 7 | Nov 19 | Exact match — still the fattest page |
| Smithfield 1671 Kinston, NC | 3 | Nov 19 | Exact match |
| Smithfield 1689 Nichols, SC | 1 | Nov 19 | Exact match |
| Smithfield 2067 Lapaz, IN | 2 | Nov 19 | Exact match |

5 of 6 headers fresh (Nov 19); only Hugoton remains dated Nov 18 —
same one-day lag as Cycles 14 and 24, row count/composition
unchanged, so site-side staleness, not a collector issue. One
Waverly delivery label carries the site's own call-ahead note ("Nov
2026 -starting 11/16/26. *Please Call Ahead*") — published text,
not a price.

### Mae-Mart live re-check — still viable as-is (2 logical probes)

- **Grain-pricing page:** HTTP 200, 35,952 bytes — **byte-identical
  size to Cycle 18**. Inline pricing JS still present (`var PROXY =
  '/grain-proxy.php';`, cosmetic whitespace only); symbols
  `ZCZ26=F`, `ZSF27=F`, `ZWN27=F` unchanged; all 4 tables present,
  1 row each (basis numeric, cash/futures "—" in static HTML, as
  documented); rye `manualPrice` still in the inline `ALL_BIDS`
  JSON; `USX` cents rule still in the JS. No Barchart/DTN/AgriCharts/
  Yahoo markers.
- **Proxy:** HTTP 200, `application/json`, **89 bytes — byte-identical
  size to Cycle 19**; JSON shape unchanged (keyed by symbol; `price`
  numeric, `currency` "USX", `timestamp`/`fetched` ints). **One
  change:** the `.php` URL now 301s to the extensionless
  `https://www.mae-martfarms.com/grain-proxy?symbols=ZCZ26=F`
  (Cycle 19's redirect kept the `.php`). Transparent to the
  collector (`requests` follows redirects by default) — no code
  change needed; the stored proxy URL could optionally be updated
  to the extensionless form.
- **Verdict: collector still viable as-is.** Nothing restructured,
  no dead endpoints, no symbol changes. (Probe-count transparency:
  the worker's first proxy attempt omitted redirect-following and
  stopped at the 301, then re-issued the same logical probe with
  redirects followed — 2 logical probes as tasked, 4 raw HTTP
  requests. The proxy scratch file in `/tmp/cycle29/` contains a
  live price value and must not be committed; it is not in the repo.)

### Merge plan extended to Cycle 28

New "Cycle 28 (added Cycle 29)" section (204 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-28` = **75 commits**,
0 merges; tip `7e99076`; Cycle 28 added 2 commits; test count 709;
Alembic head still `0019`; CI workflow file still untracked; Cycle
27→28 diff 4 files, 359 insertions, 6 deletions — all under
`docs/plans/`, no code changed). The Cycle 27 section's "73 commits"
figure re-verified correct. No discrepancies found between git and
the Cycle 28 report.

### Super-plan §9 extended to Cycle 28

Heading/intro now cover Cycles 1–28 (test chain 179 → 709); Cycle
28 bullet added; blockers updated (full embed family re-verified,
FS Grain mirror confirmed).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 29 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (no new hypothesis).
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

Carried from Cycles 1–28: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 29:** nothing new needs Adam.
