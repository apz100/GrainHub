# Overnight Cycle 36 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-36` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 36 complete — AgriCharts wrappers + key collectors
re-verified 16/16 exact matches; merge plan extended to Cycle 35,
super-plan §9 extended to Cycle 35. Executed directly by the
coordinator (subagent spawning still unavailable).

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `a03b382` | AgriCharts wrappers + key collectors re-verified 16/16 exact; merge plan extended to Cycle 35 |
| *(this commit)* | Cycle 36 report |

## 2. Test results

- **Full API suite: 711 passed, 0 failed** (unchanged — docs /
  research only cycle, no code changed). Coordinator ran the
  suite once to confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### AgriCharts wrappers — 11/11 exact matches (653 rows)

One call per wrapper, no retries, via the module's own
`us_agricharts_source.py` wrappers. Last re-verified Cycle 27
(10 wrappers, 639 rows — Heritage excluded there). All 11 now
exact, including Heritage at 14 rows (confirmed Cycle 23).
Counts only, no values recorded.

| Wrapper | Rows now | Prior | Locations | Verdict |
|---|---|---|---|---|
| Ag Plus | 36 | 36 (Cycle 27) | 6 | Exact match |
| Farmers Win Coop | 171 | 171 | 18 | Exact match |
| Heritage Grain Cooperative | 14 | 14 (Cycle 23) | 1 | Exact match |
| Keller | 14 | 14 | 1 | Exact match |
| Kokomo Grain | 63 | 63 | 8 | Exact match |
| Legacy Farmers | 66 | 66 | 10 | Exact match |
| Pro Ag | 78 | 78 | 6 | Exact match |
| West-Con | 84 | 84 | 1 (fallback location) | Exact match |
| Wheaton Dumont | 43 | 43 | 8 | Exact match |
| Central Farmers Coop | 75 | 75 | 11 | Exact match |
| Anthony Farmers Co-op | 9 | 9 | 3 | Exact match |

### Key collectors — 5/5 exact matches

One call each, no retries. Last re-verified Cycle 26, all exact
then — and still exact now.

| Collector | Rows now | Prior | Notes |
|---|---|---|---|
| FMN (`fetch_fmn_cash`, page + jsquote feed) | 453 | 453 (Cycle 26) | 204 tables, 87 delivery points; 449/449 futures-linked rows filled from the feed |
| Five Star Coop | 299 | 299 | 21 locations; page trade date Nov 18 |
| TGM | 362 | 362 | 24 locations (completes the embed family: 13/13 now re-verified across Cycles 35–36) |
| USDA mirror — James Valley | 197 | 197 | Report id 7730, dated Nov 18, 2026 |
| USDA mirror — FS Grain | 197 | 197 | Same report id 7730, dated Nov 18, 2026 |

**Coverage note:** with Cycles 35–36, every live-verified
collector family has now been re-checked this morning with zero
drift: Bushel per-location sweeps (Cycles 29–34), the full
13-site embed family (Cycle 35 + TGM here), all 11 working
AgriCharts wrappers, FMN, Five Star, and both USDA mirrors.

### Merge plan extended to Cycle 35

New "Cycle 35 (added Cycle 36)" section (220 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-35` = **89 commits**,
0 merges; tip `95f5515` (full
`95f551559e7184217e3940613c098a98515337c0`); Cycle 35 added 2
commits; test count 711; Alembic head still `0019`; CI workflow
file still untracked; Cycle 34→35 diff 4 files, 428 insertions,
0 deletions). The Cycle 34 section's "87 commits" figure
re-verified correct. No discrepancies found between git and the
Cycle 35 report.

### Super-plan §9 extended to Cycle 35

Cycle 35 bullet added (embed family 12/12, subagent spawning
unavailable, merge plan extended to Cycle 34, 87 commits).

### Price-source catalogue — Cycle 36 section added

New "Cycle 36" section (AgriCharts wrappers 11/11 + key
collectors 5/5 + the coverage note).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 36 code, tests, fixtures, or docs
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
  Almota). No re-checks needed.
- AGP + Alliance Grain: both pages changed the location they serve
  once (Chester → Aberdeen; Gibson City → Anchor/Cropsey/Colfax).
  If either rotates again, a later re-verification will catch it.
  No action needed now.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).
- Subagent spawning is unavailable in this session — cycles run
  coordinator-direct unless it comes back.

## 6. Blocked / needs Adam

Carried from Cycles 1–35: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 36:** nothing new needs Adam.
