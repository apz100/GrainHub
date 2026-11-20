# Overnight Cycle 27 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-27` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 27 complete — all 10 working US AgriCharts wrappers
re-verified live, all exact matches (639 rows); merge plan extended
to Cycle 26, super-plan §9 extended to Cycle 26.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `90b2bb7` | AgriCharts wrappers re-verified, all 10 exact matches; merge plan extended to Cycle 26 |
| *(this commit)* | Cycle 27 report |

## 2. Test results

- **Full API suite: 709 passed, 0 failed** (unchanged — docs/research
  only cycle, no code changed). Coordinator re-ran the suite to
  confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### AgriCharts wrappers re-verification — all 10 exact matches (10 calls)

One call per wrapper, no retries, via the venv python. **All 10
returned `[US-AG OK]` with no warnings** — no degraded/basis-only
path, no jsquote failures — and row counts exactly matching Cycle
21. **639 rows total, 0 zero-row results.** Counts only, no values
recorded. Structure identical across all 10: 11 columns (Location,
Name, Delivery, Delivery End, Futures Month, Futures Price, Change,
Basis, Bushel Cash Price, MT Cash Price, Note).

| Wrapper | Rows now | Cycle 21 | Locations |
|---|---|---|---|
| Ag Plus | 36 | 36 | 6 |
| Farmers Win Coop | 171 | 171 | 18 |
| Keller | 14 | 14 | 1 |
| Kokomo Grain | 63 | 63 | 8 |
| Legacy Farmers | 66 | 66 | 10 |
| Pro Ag | 78 | 78 | 6 |
| West-Con | 84 | 84 | 1 |
| Wheaton Dumont | 43 | 43 | 8 |
| Central Farmers Coop | 75 | 75 | 11 |
| Anthony Farmers Co-op | 9 | 9 | 3 |

Heritage was confirmed live in Cycle 23 (14 rows) and Heartland/
Mulvane are closed for now — neither was re-probed. Together with
Cycle 26's sweep (FMN 453, Five Star 299, TGM 362, USDA mirror 197,
FAC 45), **every live-verified collector has now been re-checked
this morning with zero drift** — the catalogue's verified counts
stand.

### Merge plan extended to Cycle 26

New "Cycle 26 (added Cycle 27)" section (223 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-26` = **71 commits**,
0 merges; tip `ca481a9`; Cycle 26 added 2 commits; test count 709;
Alembic head still `0019`; CI workflow file still untracked; Cycle
26 diff 7 files, 526 insertions, 8 deletions). The Cycle 25
section's "69 commits" figure re-verified correct. No discrepancies
found between git and the Cycle 26 report on any figure checked.

### Super-plan §9 extended to Cycle 26

Heading/intro now cover Cycles 1–26 (test chain 179 → 709); Cycle
26 bullet added; blockers updated (feed-error degradation done,
design-note work complete, five-collector sweep exact matches).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 27 code, tests, fixtures, or docs
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

Carried from Cycles 1–26: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 27:** nothing new needs Adam.
