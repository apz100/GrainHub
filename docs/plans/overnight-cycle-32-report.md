# Overnight Cycle 32 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-32` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 32 complete — Bushel samples #4 and Cycle 11/5 sites
re-verified, 12/12 exact matches; merge plan extended to Cycle 31,
super-plan §9 extended to Cycle 31.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `aab24c1` | Bushel samples #4 + Cycle 11/5 sites re-verified 12/12; merge plan extended to Cycle 31 |
| *(this commit)* | Cycle 32 report |

## 2. Test results

- **Full API suite: 710 passed, 0 failed** (unchanged — docs/research
  only cycle, no code changed). Coordinator re-ran the suite to
  confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample #4 — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycles 13–14 baselines; all six
headers fresh (Nov 19). Counts only, no values recorded. 25 rows
total, identical to the earlier total.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2742 Johnson–Ulysses–N Sublette | 7 | Nov 19 | Exact match |
| Skyland 2754 Olton Area | 5 | Nov 19 | Exact match |
| Skyland 2763 Satanta–Ryus | 6 | Nov 19 | Exact match |
| Smithfield Clarkton (1668) | 1 | Nov 19 | Exact match |
| Smithfield 1672 LaGrange | 3 | Nov 19 | Exact match |
| Smithfield 1674 Mount Olive | 3 | Nov 19 | Exact match |

**Correction (coordinator brief error, caught by the worker):** the
task listed "Smithfield 1666 Clarkton", but 1666 is Bentonville
(verified Cycle 12, 3 rows) and Clarkton is 1668 (verified Cycle
13, 1 Soybeans row). The worker fetched Clarkton (1668), matching
the town name and count. **Bentonville (1666) was not re-fetched —
it still needs its own call in a later sample.**

### Cycle 11 + Cycle 5 Bushel sites — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches.** Counts only, no values recorded.

| Site | Rows now | Prior | Header date | Verdict |
|---|---|---|---|---|
| Winchester 3439 | 10 | 10 (Cycle 11) | Nov 19 | Exact match |
| Wheaton Grain | 5 | 5 (Cycle 11) | — (no capturable header date) | Exact match |
| Synergy | 4 | 4 (Cycle 10) | Nov 19 | Exact match |
| Skyland default (Cunningham Area) | 6 | 6 (Cycle 11) | Nov 19 | Exact match |
| Lake Norden | 2 | 2 (Cycle 5) | Nov 19 | Exact match |
| United Cooperative (Webster City) | 12 | 12 (Cycle 5) | Nov 19 | Exact match |

**Note:** Wheaton Grain's tabbed widget carries no capturable header
date (no `fcControlsSectionHeader` element) — structure observation
only, not a failure; the 5 rows parsed cleanly via the Cycle 11
tabbed-widget fallback. If header-date freshness tracking matters
for that site, it would need a different date source on the page.

### Merge plan extended to Cycle 31

New "Cycle 31 (added Cycle 32)" section (207 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-31` = **81 commits**,
0 merges; tip `31b31be`; Cycle 31 added 2 commits; test count 710;
Alembic head still `0019`; CI workflow file still untracked; Cycle
30→31 diff 4 files, 377 insertions, 5 deletions). The Cycle 30
section's "79 commits" figure re-verified correct. No discrepancies
found between git and the Cycle 31 report. (The worker noted the
Cycle 31 report's "77 commits" re-verification claim is carried
from that report, not re-verified by the worker — the task only
asked for the Cycle 30 figure, which was verified directly from git.)

### Super-plan §9 extended to Cycle 31

Heading/intro now cover Cycles 1–31 (test chain 179 → 710); Cycle
31 bullet added; blockers updated (Bushel samples #3 + Cycle 4/5
sites 12/12, Almota joins the staleness watch).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 32 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (no new hypothesis).
- Staleness watch: five widgets on the exemption list for any future
  freshness gate (Chadbourn, Hamer, Hugoton 3370, Vilas-Walsh 3621,
  Almota).
- Bentonville (Smithfield 1666) still needs a re-verification call
  (missed in Cycle 32 by a brief error — see §3).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–31: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 32:** nothing new needs Adam.
