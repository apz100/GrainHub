# Overnight Cycle 38 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-38` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 38 complete — web build re-run passes (33 pages);
config / registry drift audit clean; merge plan extended to
Cycle 37, super-plan §9 extended to Cycle 37. Executed directly
by the coordinator (subagent spawning still unavailable). No
live fetches this cycle.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `21515be` | Web build re-run passes (33 pages); config/registry drift audit clean; merge plan extended to Cycle 37 |
| *(this commit)* | Cycle 38 report |

## 2. Test results

- **Full API suite: 711 passed, 0 failed** (unchanged — docs /
  research only cycle, no code changed). Coordinator ran the
  suite once to confirm.
- **Web build: ✓ Compiled successfully, 33/33 static pages
  generated** — first full re-run since Cycle 17. See §3 for
  the workspaces caveat.

## 3. What was built (done)

### Web build re-run — passes

`npm run build --workspace=grainbids-web` from
`GrainBids/grainbids`: **✓ Compiled successfully, 33/33 static
pages generated.**

**Workspaces caveat (worth recording):** `apps/web` has no local
`node_modules` — this is an npm-workspaces monorepo and
dependencies are hoisted to the root
`GrainBids/grainbids/node_modules/`. Running plain `npm install`
inside `apps/web` is a no-op that reports "up to date" without
installing anything (and `npm ls` there errors with
`ENOWORKSPACES`). The workspace-aware build command is the
correct one. The root `GrainBids/grainbids/package-lock.json`
stray file reappeared during the build, as in earlier cycles —
deleted, not committed (the real lockfile is
`apps/web/package-lock.json`, already tracked). `git status`
after the build shows only the pre-existing untracked `.github/`.

### Config / registry drift audit — clean

Verified directly with `tomllib` + the real toggle loader (not
from memory):

| Check | Result |
|---|---|
| `us_elevators_urls.toml` | 121 entries, 102 enabled (same as Cycle 18) |
| `config.toml` `[us]` | 121 entries, 102 enabled; per-entry name/url/type/enabled match with the urls toml |
| Registry adapters (`ADAPTERS`) | 119 |
| Disabled by `[sources]` toggle | 17 — bunge, mapleview, 13 DTN, Heartland, Mulvane (same set as Cycle 23) |
| Seedable (adapters − disabled) | 102 |

The AGP (Cycle 33) and Alliance Grain (Cycle 34) comment edits
introduced no drift: both toml files still agree
entry-for-entry, and the toggle-disabled set is unchanged.

### Merge plan extended to Cycle 37

New "Cycle 37 (added Cycle 38)" section (225 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-37` = **93 commits**,
0 merges; tip `55804ca` (full
`55804caad27529f36d12c11b1dd4416a89f49b4c`); Cycle 37 added 2
commits; test count 711; Alembic head still `0019`; CI workflow
file still untracked; Cycle 36→37 diff 4 files, 400 insertions,
0 deletions). The Cycle 36 section's "91 commits" figure
re-verified correct. No discrepancies found between git and the
Cycle 37 report.

### Super-plan §9 extended to Cycle 37

Cycle 37 bullet added (early Bushel sites 9/9, Mae-Mart still
viable; merge plan extended to Cycle 36, 91 commits).

### Price-source catalogue — Cycle 38 section added

New "Cycle 38" section (web build + drift audit).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 38 code, tests, fixtures, or docs
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

Carried from Cycles 1–37: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 38:** nothing new needs Adam.
