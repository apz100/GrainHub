# Overnight Cycle 37 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-37` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 37 complete — early Bushel sites re-verified
9/9 exact matches; Mae-Mart still viable (page 171 bytes
smaller, proxy shape unchanged); merge plan extended to
Cycle 36, super-plan §9 extended to Cycle 36. Executed
directly by the coordinator (subagent spawning still unavailable).

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `368a03a` | Early Bushel sites 9/9 exact; Mae-Mart still viable (page 171 bytes smaller, proxy shape unchanged); merge plan extended to Cycle 36 |
| *(this commit)* | Cycle 37 report |

## 2. Test results

- **Full API suite: 711 passed, 0 failed** (unchanged — docs /
  research only cycle, no code changed). Coordinator ran the
  suite once to confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Early Bushel sites — 9/9 exact matches (102 rows)

One call per site, no retries, via the module's own
`bushel_source.py` wrappers. Last re-verified Cycles 26 (FAC) /
31 (Chandler, Cameron, CGS, Almota, Williams Gin, Rugby) /
32 (Lake Norden, United Coop). All 9 exact again; 8 of 9 headers
fresh Nov 19. Counts only, no values recorded.

| Site | Rows now | Prior | Header date | Verdict |
|---|---|---|---|---|
| FAC | 45 | 45 (Cycle 26) | Nov 19 | Exact match |
| Chandler Feed | 17 | 17 (Cycle 31) | Nov 19 | Exact match |
| Cameron Coop | 4 | 4 | Nov 19 | Exact match |
| CGS | 4 | 4 | Nov 19 | Exact match |
| Almota | 12 | 12 | **Nov 18** | Exact match (count); still one day stale |
| Williams Gin | 2 | 2 | Nov 19 | Exact match |
| Rugby | 12 | 12 | Nov 19 | Exact match |
| Lake Norden | 2 | 2 | Nov 19 | Exact match |
| United Cooperative (Webster City) | 12 | 12 (Cycle 32) | Nov 19 | Exact match |

**Almota:** header still dated Nov 18 — the same one-day lag
found in Cycle 31. Count unchanged at 12, so the collector
parses it fine; the page is serving yesterday's board. It stays
on the staleness watch list (five widgets); no further re-checks
needed beyond the regular sweeps.

### Mae-Mart — still viable as-is (2 logical probes)

- **Pricing page** (1 GET): **35,781 bytes** — 171 bytes smaller
  than Cycles 18/29 (35,952). Structure unchanged: all three
  futures symbols present (`ZCZ26=F`, `ZSF27=F`, `ZWN27=F`),
  `grain-proxy` referenced, 4 tables, parse status ok, **4
  rows** (Corn, Soybeans, Wheat, Rye — basis present on all;
  futures/cash empty without the proxy step, Rye carrying its
  static manual cash price as in Cycle 18). The byte difference
  is not diagnosed further — no saved Cycle 29 copy exists to
  diff against, and the pricing content is intact.
- **Proxy** (1 GET, `grain-proxy?symbols=ZCZ26=F`, redirects
  followed): HTTP 200, `application/json; charset=utf-8`, **88
  bytes** (was 89 in Cycles 19/29 — the 1-byte difference is the
  price value itself changing length, which is expected). JSON
  shape unchanged: keyed by symbol, numeric `price`, `currency`
  `"USX"`, integer `timestamp` and `fetched`. The extensionless
  canonical URL is served directly. Collector still viable
  as-is; no code change needed. No price value was recorded
  anywhere.

### Merge plan extended to Cycle 36

New "Cycle 36 (added Cycle 37)" section (221 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-36` = **91 commits**,
0 merges; tip `f273da4` (full
`f273da44b7da90b715a19df902dd2e171924d2b6`); Cycle 36 added 2
commits; test count 711; Alembic head still `0019`; CI workflow
file still untracked; Cycle 35→36 diff 4 files, 399 insertions,
0 deletions). The Cycle 35 section's "89 commits" figure
re-verified correct. No discrepancies found between git and the
Cycle 36 report.

### Super-plan §9 extended to Cycle 36

Cycle 36 bullet added (AgriCharts wrappers 11/11 + key
collectors 5/5, 16/16 overall; every live-verified collector
family re-checked with zero drift; merge plan extended to
Cycle 35, 89 commits).

### Price-source catalogue — Cycle 37 section added

New "Cycle 37" section (early Bushel sites 9/9 + Mae-Mart).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 37 code, tests, fixtures, or docs
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
  Almota). No re-checks needed beyond the regular sweeps.
- AGP + Alliance Grain: both pages changed the location they serve
  once (Chester → Aberdeen; Gibson City → Anchor/Cropsey/Colfax).
  If either rotates again, a later re-verification will catch it.
  No action needed now.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed). Mae-Mart page is 171 bytes smaller than
  Cycles 18/29; structure unchanged, not diagnosed further.
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).
- Subagent spawning is unavailable in this session — cycles run
  coordinator-direct unless it comes back.

## 6. Blocked / needs Adam

Carried from Cycles 1–36: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 37:** nothing new needs Adam.
