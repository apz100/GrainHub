# Overnight Cycle 26 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-26` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 26 complete — feed-error degradation implemented (the
last AgriCharts fallback follow-up); live re-verification sweep of five
key collectors, all exact matches; merge plan extended to Cycle 25,
super-plan §9 extended to Cycle 25.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `797f8af` | Feed-error degradation; live re-verification sweep all exact matches; merge plan extended to Cycle 25 |
| *(this commit)* | Cycle 26 report |

## 2. Test results

- **Full API suite: 709 passed, 0 failed** (Cycle 25 ended at 704).
  New tests in Cycle 26: **5** (feed-error degradation).
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Feed-error degradation — implemented (mocked tests only, 0 GETs)

Only the `_fetch_jsquote` call is now wrapped in its own
`try/except`: a feed fetch that RAISES (HTTP error/timeout) degrades
to basis-only rows, like the no-tag (Cycle 24) and empty-feed
(Cycle 25) paths. A page fetch that raises still returns empty via
the outer `except` (no HTML to parse, no invented rows). The
empty-feed check gained a `not degraded` guard so a raised feed
doesn't double-log. 5 new mocked tests: 3 feed-raises (HTTPError
503, ConnectTimeout, ReadTimeout) → basis-only rows; 2 page-raises
(HTTPError 500, ConnectTimeout) → empty DataFrame, no exception
escapes. Targeted file 23 passed; **full suite 709 passed**.
This closes the last open follow-up from the Cycle 23 design note —
all three degradation paths (no tag, empty feed, feed error) now
behave the same way. The design note's work is complete; the only
remaining AgriCharts open item is Heartland/Mulvane, closed for now.

### Live re-verification sweep — all five exact matches (5 probes)

All five key collectors re-verified live via their wrappers; **all
returned `status='ok'` with row counts identical to the last
verification — no drift, no failures.** Counts only, no values
recorded.

| Collector | Rows now | Last verified | Verdict |
|---|---|---|---|
| FMN (`fetch_fmn_cash`) | 453 rows (87 points, 204 tables; 449/449 futures-linked filled) | Cycle 10–11: 453 | Exact match |
| Five Star Coop (`fetch_five_star_coop`) | 299 rows, 21 locations | Cycle 8–9: 299 | Exact match |
| TGM embed (`fetch_tgm`) | 362 rows, 24 locations | Cycle 9: 362 | Exact match |
| USDA mirror, James Valley (`fetch_usda_mirror`) | 197 rows, 29 regions, report id 7730, dated Nov 18 | Cycle 4: 197 | Exact match |
| FAC, Bushel (`fetch_fac`) | 45 rows, 3 locations; header dated Nov 19 | Cycle 4–5: 45 | Exact match |

Notes: FMN's dropdown still lists more points than the 204 tables
(known limitation, unchanged); Five Star's page trade date is Nov 18;
FAC's widget header is fresh (Nov 19). The five collectors' live
behaviour is stable across cycles — the catalogue's verified counts
stand. (One early hiccup, resolved by the worker: the first probe
script inserted `"app"` instead of the api directory into `sys.path`;
fixing the path resolved it. No site probe was retried.)

### Merge plan extended to Cycle 25

New "Cycle 25 (added Cycle 26)" section (229 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-25` = **69 commits**,
0 merges; tip `95b310d`; Cycle 25 added 2 commits; test count 704;
Alembic head still `0019`; CI workflow file still untracked; Cycle
25 diff 7 files, 574 insertions, 8 deletions). The Cycle 24
section's "67 commits" figure re-verified correct. The worker
correctly verified from committed code that the empty-feed
degradation landed in Cycle 25 and that the feed-error case was
still open — it has now landed in this cycle.

### Super-plan §9 extended to Cycle 25

Heading/intro now cover Cycles 1–25 (test chain 179 → 704); Cycle
25 bullet added; blockers updated (Heartland/Mulvane closed for
now, feed-down degradation done).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 26 code, tests, fixtures, or docs
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

Carried from Cycles 1–25: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 26:** nothing new needs Adam.
