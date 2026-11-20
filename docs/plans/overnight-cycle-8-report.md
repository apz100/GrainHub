# Overnight Cycle 8 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-8` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 8 complete — merge plan for branches 1–7,
Cycle 6 re-check sweep, StoneX research, super-plan progress to
Cycle 7.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `b0ba527` | Merge plan for branches 1–7; super-plan progress §9 to Cycle 7; deployment-checklist migration head corrected 0018 → 0019 |
| `aa570be` | Cycle 8 re-check sweep in the price-source catalogue (all 5 Cycle 6 failures back up; Five Star 299 static rows; StoneX no static-data route) |
| *(this commit)* | Cycle 8 report |

## 2. Test results

- **Full API suite: 407 passed, 0 failed** (unchanged from Cycle 7
  — Cycle 8 added no code, so no new tests).
- Web build was not re-run in Cycle 8 (no web files changed).

## 3. What was built (done)

### Merge plan — `docs/plans/merge-plan.md` (new, 15 KB)
- Verified from git history before writing: the branch chain is
  linear (each cycle branched from the previous one), `master`
  still at `f2c3206`, 32 commits total `master..cycle-7`
  (6/6/5/5/3/4/3 per cycle), no merges or branch points — so
  sequential merging has no true conflicts.
- Merge order 1 → 7 with `--no-ff` per branch (keeps per-cycle
  checkpoints and revertability), per-branch summaries, test
  counts (179 → 291 → 320 → 359 → 364 → 380 → 407, all 0 failed),
  and web-build status per cycle.
- Gates before each merge: full API suite at the per-cycle count,
  `npm run build`, `alembic heads` = single head (`0018` through
  Cycle 6, `0019` after Cycle 7), boundary spot-check, no-secrets
  spot-check.
- Conflicts/overlaps documented: catalogue edited in all 7
  cycles, `source_registry.py` in Cycles 3–7, `us_elevators_urls.toml`
  reclassifications accumulating (Cycle 7 values are current truth
  — Ag State corrected from DTN to agricharts-embed), Cycle 6's
  corrupted string literal in `bushel_source.py` (`387c985` broken,
  fixed on top by `eb01c71` — never cherry-pick one without the
  other, do not rewrite history), super-plan §9, linear migration
  chain.
- **Must NOT be merged as-is:** the CI workflow file is in no
  branch and sits untracked locally (`.github/workflows/api-tests.yml`,
  890 bytes) — it needs `gh` re-auth with `workflow` scope or adding
  via the GitHub web UI. `.github` must not be assumed present after
  merging. Also flagged as review-not-blocker: public-by-default
  email-bid endpoint, null futures prices, `/ask` 501, eSign stub,
  `currency: null`.
- Rollback per deployment-checklist §6: redeploy previous `master`
  in Render/Vercel (no force-push, no branch surgery), never roll
  back by deploying a cycle branch, migrations forward-only
  (downgrade only with Adam's explicit approval per revision),
  ingestion fix-forward, bad merge reverted with
  `git revert -m 1`.

### Super-plan progress — §9 extended to Cycles 5–7
- Heading and intro now cover Cycles 1–7 with the full test-count
  chain 179 → 407.
- 2–3 line bullets added for Cycles 5 (364), 6 (380), and 7 (407).
- Blockers updated with newest findings: cashbids.php collector
  done (6 sites, 105 rows, static route), AGP verified Bushel and
  registered, basis alerts wired (migration `0019`, checklist head
  stale at `0018` — fixed in this cycle), DTN sweep results
  (28 sites: 2 static-HTML, 20 JS-only, 6 unreachable; Al-Corn
  only classic `CashBidTable` fit), Playwright checks still pending
  (12 DTN-family JS-only sites, FMN filtered view, Mapleview). The
  `gh` workflow-scope item now notes the CI file is in no branch
  and untracked locally.

### Deployment checklist — migration head corrected
- The checklist still said head `0018` (Cycle 6). Corrected to
  `0019` with the new revision row (basis-threshold alert fields),
  tail chain `0014 → … → 0019`, and all `alembic` steps updated.

### Cycle 8 re-check sweep — price-source catalogue
- One polite GET per URL (9 total, contact User-Agent, ~2 s
  spacing, 30 s timeout, no retries). **All 9 returned HTTP 200 —
  every Cycle 6 failure is back up.**
- **Ag Partners** (was 503): 200 (→ `/cash-bids/`), modern DTN
  widget, no static rows. DTN Playwright.
- **ALCIVIA** (was timeout): 200, AgriCharts `cashbids.php` embed
  (`alciviacoop.agricharts.com`, `groupby=location`) — same family
  as Cycle 7's six; `cashbids-js.php` static route to verify later.
- **CRC** (was timeout): 200, but a generic grain-services page
  with no widget and no bid table; Cash Bids links point to the
  homepage anchor `/home/#cash-bids`. Follow-up: one GET of the
  homepage. Site now brands as "Central United Cooperative".
- **Five Star Coop** (was timeout): 200, **static bid rows: 299
  rows, 21 locations, Corn 197 + Soybeans 102**, in a
  server-rendered **wpDataTables** table (new pattern: Location /
  Commodity / Delivery Periods / Bids / Basis / Change). Plain-HTTP
  parser feasible; delivery labels are inconsistent (`Dec26` vs
  `Dec 27`, `Apr 27` vs `April 27`). Tables 2–4 on the page are
  DTN futures, not cash bids.
- **Bunge** (was timeout): 200, still the locations archive;
  "Cash Bids" is nav text only. Still do-not-add.
- **Gateway FS** sub-page (previously unfetched): 200, Next.js app
  shell with `<div id="cash-bids-root" data-slug="gateway">` + DTN
  widget classes, no static rows. DTN Playwright.
- **TGM** `/Cash-Bids` (previously unfetched): 200, AgriCharts
  `cashbids.php` embed (`totalgrain.agricharts.com`,
  `groupby=ccommodity`) — same family as Cycle 7; static route to
  verify later. Barchart marketplace link not fetched (out of scope).

### StoneX research (Frontier Coop)
- Page re-fetched: StoneX iframe unchanged (same key), inline JSON
  model still empty (`LocationRecords: null`).
- One GET of the verbatim iframe target
  (`stonehedge.stonex.com/component/bids?...`) returns 200, 5.9 KB
  — a JS app shell ("StoneX Hedge"), zero tables, zero bid data.
  CSP `connect-src` shows runtime fetching from
  `api.stonehedge.stonex.com` via SignalR/`auth.stonex.com`.
- **Conclusion: no static-data route exists for StoneX** — needs a
  browser render check, and the runtime API may be auth-gated.
  Research only; no collector built. (The widget key in the iframe
  URL is a public site key embedded in Frontier's public page HTML,
  not a credential.)
- Raw HTML saved to `/tmp/cycle8/` scratch only, never the repo. No
  prices copied into docs — row counts and widget patterns only.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 8 code, tests, or docs (verified
by grep on the new/changed lines). The company appears only as one
ordinary price source in pre-existing catalogue text, per the
boundary. No contact made.

## 5. What is still scaffold / stub

- Playwright render checks for the DTN-family JS-only sites (now
  including Ag Partners and Gateway FS), plus FMN filtered view
  and Mapleview. StoneX (Frontier) has no static-data route —
  render check is the only path, and the runtime API may be
  auth-gated.
- Five Star wpDataTables collector not yet built (new plain-HTTP
  pattern, 299 rows); ALCIVIA + TGM `cashbids-js.php` static-route
  checks not yet run; CRC homepage `#cash-bids` check not yet run.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized
  price rows.

## 6. Blocked / needs Adam

Carried from Cycles 1–7: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX).

**New in Cycle 8:** nothing new needs Adam beyond the carried
list. The merge plan is ready for his review whenever he wants to
merge branches 1–7 in order — no merge was performed.
