# Overnight Cycle 34 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-34` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 34 complete — Bushel samples #6 and Smithfield /
Alliance re-verified, 11/12 exact matches (Alliance changed
site-side); Alliance registry entry updated Gibson City →
Anchor/Cropsey/Colfax; Smithfield East Region sweep now fully
re-verified; merge plan extended to Cycle 33, super-plan §9
extended to Cycle 33.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `8a16b44` | Bushel samples #6 + Smithfield/Alliance re-verified 11/12; Alliance switches Gibson City to Anchor/Cropsey/Colfax; merge plan extended to Cycle 33 |
| *(this commit)* | Cycle 34 report |

## 2. Test results

- **Full API suite: 711 passed, 0 failed** (+1 vs Cycle 33: new
  registry test `test_alliance_grain_registry_entry_updated_cycle34`).
  Coordinator ran the suite once, after the Alliance metadata
  update.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample #6 — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycle 15 baselines; all six
headers fresh (Nov 19). Counts only, no values recorded. 10 rows
total.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Smithfield Weeksville (1679) | 2 | Nov 19 | Exact match |
| Smithfield Chief Feed Mill / Rose Hill (1681) | 2 | Nov 19 | Exact match |
| Smithfield Laurinburg Feed Mill (1682) | 2 | Nov 19 | Exact match |
| Smithfield Warsaw (1684) | 2 | Nov 19 | Exact match |
| Smithfield Harpster (1685) | 1 | Nov 19 | Exact match |
| Smithfield Morral, OH (1686) | 1 | Nov 19 | Exact match |

### Smithfield / Alliance / Winchester 3440 — 5/6 exact matches

One call per site, no retries. Counts only, no values recorded.

| Site | Rows now | Prior | Header date | Verdict |
|---|---|---|---|---|
| Smithfield Darlington, SC (1687) | 1 | 1 (Cycle 15) | Nov 19 | Exact match |
| Smithfield Lake City, SC (1688) | 1 | 1 (Cycle 15) | Nov 19 | Exact match |
| Smithfield Jones County (2065) | 3 | 3 (Cycle 16) | Nov 19 | Exact match |
| Smithfield Deep Run JCH (2066) | 2 | 2 (Cycle 16) | Nov 19 | Exact match |
| Alliance Grain | 10 | 10 (Cycle 6) | Nov 19 | **Changed — see below** |
| Winchester 3440 (Georgetown) | 5 | 5 (Cycle 12) | Nov 19 | Exact match |

**Alliance Grain — site-side change, same pattern as AGP (Cycle
33):** the page still returns 10 rows (Corn 5 + Soybeans 5), fresh
header, status ok, but the live h2 is now **`Anchor/Cropsey/Colfax`**
instead of `Gibson City - West` (Cycle 6). The registry entry has
no `location_labels` mapping, so the parsed location is the raw
live h2 — a genuine site-side change, not a parser issue. The
worker did not re-call it (no-re-probe rule).

**Coordinator decision (same as AGP):** update the existing
`alliance_grain` registry entry rather than register a second one.
Changes (commit `8a16b44`): `bushel_source.py` —
`default_location` Gibson City → Anchor/Cropsey/Colfax, registry
notes + `fetch_alliance_grain` docstring updated to record both
observations; `config.toml` and `us_elevators_urls.toml` — Alliance
comments updated identically in both files (sync guard still
passes as part of the full suite); new registry test
`test_alliance_grain_registry_entry_updated_cycle34` in
`test_bushel_cycle6_shapes.py`. The saved Cycle 6 Gibson City
fixture in the same test file is kept as a parse test (its location
comes from the fixture's own h2).

**Milestone — Smithfield East Region sweep fully re-verified:**
with samples #5 (Cycle 33) and #6 plus this batch, all **30
verified Smithfield locations** have now been re-fetched at least
once across Cycles 29–34, every one an exact row-count match
(Raeford 1675 posts no public bids and is not registered).
Likewise every Skyland per-location ID except 2730 has been
re-fetched at least once (2730 duplicates the default Cunningham
Area page, re-verified in Cycle 32).

### Merge plan extended to Cycle 33

New "Cycle 33 (added Cycle 34)" section (255 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-33` = **85 commits**,
0 merges; tip `52e8089`; Cycle 33 added 2 commits; test count 710;
Alembic head still `0019`; CI workflow file still untracked; Cycle
32→33 diff 8 files, 440 insertions, 11 deletions). The Cycle 32
section's "83 commits" figure re-verified correct. No discrepancies
found between git and the Cycle 33 report.

### Super-plan §9 extended to Cycle 33

Cycle 33 bullet added (Bushel samples #5 + Skyland/AGP 11/12,
AGP Chester → Aberdeen, Bentonville gap closed; merge plan
extended to Cycle 32, 83 commits).

### Price-source catalogue — Cycle 34 section added

New "Cycle 34" section (both sweeps + Alliance change + the
Smithfield milestone) and the Alliance Grain catalogue row updated
with the Cycle 34 finding.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 34 code, tests, fixtures, or docs
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
- AGP + Alliance Grain: both iframe/widget pages changed the
  location they serve once (Chester → Aberdeen; Gibson City →
  Anchor/Cropsey/Colfax). If either rotates again, a later
  re-verification will catch it. No action needed now.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–33: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 34:** nothing new needs Adam.
