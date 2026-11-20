# Overnight Cycle 31 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-31` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 31 complete — Bushel samples #3 and Cycle 4/5 sites
re-verified, 12/12 exact matches; Almota joins the staleness watch
(first stale probe for it); merge plan extended to Cycle 30,
super-plan §9 extended to Cycle 30.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `c1d1f74` | Bushel samples #3 + Cycle 4/5 sites re-verified 12/12; Almota joins staleness watch; merge plan extended to Cycle 30 |
| *(this commit)* | Cycle 31 report |

## 2. Test results

- **Full API suite: 710 passed, 0 failed** (unchanged — docs/research
  only cycle, no code changed). Coordinator re-ran the suite to
  confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample #3 — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycles 13–16 baselines. Counts
only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2740 Moscow/Dermot/Kismet/Pleasant Valley | 7 | Nov 19 | Exact match |
| Skyland 3621 Vilas–Walsh | 5 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 2294 Chadbourn | 1 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 1725 Bladenboro | 1 | Nov 19 | Exact match |
| Smithfield 2064 Kinston JCH, NC | 3 | Nov 19 | Exact match |
| Smithfield 1683 Creswell | 2 | Nov 19 | Exact match |

### Cycle 4/5 Bushel sites re-verification — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to Cycle 5. Counts only, no values
recorded.

| Site | Rows now | Cycle 5 | Locations |
|---|---|---|---|
| Chandler Feed | 17 | 17 | 1 (Chandler) |
| Cameron Coop | 4 | 4 | 1 (Cameron) |
| CGS | 4 | 4 | 1 (Bazine) |
| Almota | 12 | 12 | 1 (Colfax) |
| Williams Gin | 2 | 2 | 1 ("Williams Gin & Grain" as location label; town still unconfirmed from the page, as in Cycle 5) |
| Rugby | 12 | 12 | 1 (Rugby) |

**New staleness note: Almota's widget header is dated Nov 18** —
one day stale, the same lag pattern as Chadbourn / Hugoton /
Vilas-Walsh / Hamer. Its row count is still exactly 12, so the
collector parses it fine; the page is serving yesterday's board.
Almota joins the staleness watch list (first stale probe for it).
The watch list is now **five widgets**: Chadbourn, Hamer, Hugoton
(3370), Vilas-Walsh (3621), Almota — all exactly one day behind,
all still on the exemption list for any future freshness gate.

### Merge plan extended to Cycle 30

New "Cycle 30 (added Cycle 31)" section (213 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-30` = **79 commits**,
0 merges; tip `d3e3b69`; Cycle 30 added 2 commits; test count 710;
Alembic head still `0019`; CI workflow file still untracked; Cycle
29→30 diff 6 files, 416 insertions, 11 deletions). The Cycle 29
section's "77 commits" figure re-verified correct. No discrepancies
found between git and the Cycle 30 report.

### Super-plan §9 extended to Cycle 30

Heading/intro now cover Cycles 1–30 (test chain 179 → 710); Cycle
30 bullet added; blockers updated (Bushel sample #2 6/6, Mae-Mart
proxy URL stored extensionless).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 31 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (no new hypothesis).
- Staleness watch: five widgets now on the exemption list for any
  future freshness gate (no further re-checks needed).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–30: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 31:** nothing new needs Adam.
