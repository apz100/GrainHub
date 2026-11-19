# Overnight Cycle 30 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-30` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 30 complete — Bushel per-location sample #2 re-verified
6/6 exact matches; Mae-Mart proxy URL stored extensionless (1 new
test); merge plan extended to Cycle 29, super-plan §9 extended to
Cycle 29.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `7c18db0` | Bushel sample #2 re-verified 6/6; Mae-Mart proxy URL stored extensionless; merge plan extended to Cycle 29 |
| *(this commit)* | Cycle 30 report |

## 2. Test results

- **Full API suite: 710 passed, 0 failed** (Cycle 29 ended at 709).
  New tests in Cycle 30: **1** (Mae-Mart proxy URL).
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample #2 — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycles 13–16 baselines. Counts
only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2734 Etter | 5 | Nov 19 | Exact match |
| Skyland 2761 Elkhart–Hough–Rolla Area | 6 | Nov 19 | Exact match |
| Skyland 2778 Buckeye–Syracuse | 6 | Nov 19 | Exact match |
| Smithfield 1670 Hobbsville | 3 | Nov 19 | Exact match |
| Smithfield 1690 Petersburg, VA | 4 | Nov 19 | Exact match |
| Smithfield 2179 Hamer, SC | 1 | **Nov 18** | Exact match (count); still one day stale |

5 of 6 headers fresh (Nov 19); Hamer remains dated Nov 18 — same
one-day lag as Cycles 16 and 24, count unchanged, site-side lag
not a collector issue. Delivery-label structure unchanged (Skyland
"N/C 26/27" labels; Petersburg's second Soybeans row still carries
the "Nov 2026 - SBOC 10% or Above" label).

### Mae-Mart proxy URL stored extensionless (mocked tests only, 0 GETs)

Following the Cycle 29 finding (the `.php` URL now 301s to the
extensionless canonical form), the stored proxy URL in
`mae_mart_source.py` was updated:
`http://www.mae-martfarms.com/grain-proxy.php` →
`http://www.mae-martfarms.com/grain-proxy` (5 occurrences, URL
string only, no behaviour change; scheme kept as `http`). Query
construction unchanged (one GET per symbol). The only remaining
`.php` mention in the file is inside the historical Cycle 29
parenthetical explaining the 301 (the old URL, not a called URL).
New mocked test `test_mae_mart_proxy_url_is_extensionless` asserts
the constant and that the mocked fetch calls exactly that URL with
`params == {"symbols": "ZCZ26=F"}`. No existing test asserted the
`.php` URL literally — the existing proxy test asserts against the
constant, so it covers the new URL automatically. Targeted file 18
passed; **full suite 710 passed**. Two self-caught issues fixed by
the worker (a wrong test expectation — the fake returns the full
3-symbol synthetic payload — and a duplicated docstring line).

### Merge plan extended to Cycle 29

New "Cycle 29 (added Cycle 30)" section (214 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-29` = **77 commits**,
0 merges; tip `fc7cf03`; Cycle 29 added 2 commits; test count 709;
Alembic head still `0019`; CI workflow file still untracked; Cycle
28→29 diff 4 files, 374 insertions, 6 deletions — all under
`docs/plans/`, no code changed). The Cycle 28 section's "75 commits"
figure re-verified correct. No discrepancies found between git and
the Cycle 29 report.

### Super-plan §9 extended to Cycle 29

Heading/intro now cover Cycles 1–29 (test chain 179 → 709); Cycle
29 bullet added; blockers updated (Bushel sample 6/6, Mae-Mart
viable, proxy canonical URL now extensionless).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 30 code, tests, fixtures, or docs
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

Carried from Cycles 1–29: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 30:** nothing new needs Adam.
