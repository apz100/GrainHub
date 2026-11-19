# Overnight Cycle 35 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-35` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 35 complete — AgriCharts cashbids-embed family
re-verified 12/12 exact matches (454 rows); merge plan extended
to Cycle 34, super-plan §9 extended to Cycle 34. Executed
directly by the coordinator — subagent spawning became
unavailable this session (see §3).

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `c9aa28f` | Embed family re-verified 12/12 exact (454 rows); merge plan extended to Cycle 34 |
| *(this commit)* | Cycle 35 report |

## 2. Test results

- **Full API suite: 711 passed, 0 failed** (unchanged — docs /
  research only cycle, no code changed). Coordinator ran the
  suite once to confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Embed family re-verification — 12/12 exact matches

One call per site, no retries, via the module's own
`cashbids_embed_source.py` wrappers. **All 12 returned
`status: ok` with exact row-count matches** to the Cycle 28
baselines. 454 rows total. Counts only, no values recorded.
Structure unchanged everywhere: same location sets, commodity
splits, and groupby behaviour (Ag State / Superior Ag still
group by commodity with `location_name` authoritative; Midway
still publishes the single "All Locations" label; StateLine
still 12 rows per location except Emmetsburg-AGP, Soybeans-only
with 6; the two PRO 21302 embeds still serve the same Manson
view).

| Site | Rows now | Prior | Locations | Verdict |
|---|---|---|---|---|
| Agtegra | 8 | 8 (Cycle 28) | 1 (Hecla) | Exact match |
| Heritage (embed) | 15 | 15 | 1 (Ada) | Exact match |
| Linn | 51 | 51 | 5 (ADM, Alburnett & Springville, Cargill Beans, Cargill Starch, Ingredion) | Exact match |
| Midway | 8 | 8 | 1 ("All Locations") | Exact match |
| Ag State | 11 | 11 | 1 (A.C.) | Exact match |
| Superior Ag | 12 | 12 | 1 (Princeton Central) | Exact match |
| ALCIVIA | 181 | 181 | 15 Wisconsin locations | Exact match |
| Hull Coop | 12 | 12 | 1 (Hull) | Exact match |
| StateLine Coop | 126 | 126 | 11 (Armstrong, Blue Earth, Cylinder, Emmetsburg-AGP, Fenton, Lakota, Ledyard, Marna, North Burt, Ringsted, Swea City) | Exact match |
| PRO Coop 21297 (Ayrshire) | 6 | 6 | 1 (AYRSHIRE.IA) | Exact match |
| PRO Coop 21302 (Manson) | 12 | 12 | 1 (MANSON.IA) | Exact match |
| PRO Coop 21302b (Manson) | 12 | 12 | 1 (MANSON.IA) | Exact match |

TGM (362 rows, re-verified in Cycle 26) was not re-probed this
cycle, so the family stands at 12/12 here rather than 13/13.
With TGM the Cycle 28 family total was 816 rows.

### Process change — subagent spawning unavailable

Three spawn attempts for Cycle 35 workers (two re-verification
batches + the merge-plan extension) all failed identically with
"subagent bootstrap is no longer authorized", including one
retry. The coordinator executed the whole cycle directly
instead — same method (one polite GET per site via the module's
own wrappers, counts only), same merge-plan verification
routine, no change to the results. If spawning stays
unavailable, later cycles will continue coordinator-direct;
the work is the same, just slower (no parallelism).

### Merge plan extended to Cycle 34

New "Cycle 34 (added Cycle 35)" section (256 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-34` = **87 commits**,
0 merges; tip `50fdf88` (full
`50fdf8835f7fe00ea20769df4d4f643f35ef7dd5`); Cycle 34 added 2
commits; test count 711; Alembic head still `0019`; CI workflow
file still untracked; Cycle 33→34 diff 8 files, 475 insertions,
6 deletions). The Cycle 33 section's "85 commits" figure
re-verified correct. No discrepancies found between git and the
Cycle 34 report.

### Super-plan §9 extended to Cycle 34

Cycle 34 bullet added (Bushel samples #6 + Smithfield/Alliance
11/12, Alliance Gibson City → Anchor/Cropsey/Colfax, Smithfield
sweep fully re-verified; merge plan extended to Cycle 33,
85 commits).

### Price-source catalogue — Cycle 35 section added

New "Cycle 35" section (embed family 12/12, 454 rows) plus the
process note about subagent spawning.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 35 code, tests, fixtures, or docs
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
- Subagent spawning is unavailable in this session — later cycles
  run coordinator-direct unless it comes back.

## 6. Blocked / needs Adam

Carried from Cycles 1–34: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 35:** nothing new needs Adam.
