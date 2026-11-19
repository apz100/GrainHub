# Overnight Cycle 19 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-19` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 19 complete — Mae-Mart proxy live and
`futures_price` filled, scheduled poller pilot-allowlist removed
(all 93 adapters reachable), merge plan extended to Cycles 16–18,
super-plan §9 extended to Cycle 18.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `9c96e5c` | Mae-Mart proxy live, futures_price filled; poller pilot-allowlist removed (93 adapters reachable); merge plan extended to Cycle 18 |
| *(this commit)* | Cycle 19 report |

## 2. Test results

- **Full API suite: 656 passed, 0 failed** (Cycle 18 ended at 646).
  New tests in Cycle 19: Mae-Mart 7, orchestration 3 = **10 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Mae-Mart futures proxy — LIVE, collector extended (1 GET)
- `GET http://www.mae-martfarms.com/grain-proxy.php?symbols=ZCZ26=F`
  → the `http://` URL answered **301** (http → https); following
  that redirect returned **HTTP 200, `application/json;
  charset=utf-8`, 89 bytes**. Response shape matches the page JS's
  documented contract exactly: JSON object keyed by the requested
  symbol, entry with numeric `price`, string `currency` (`"USX"`),
  plus numeric `timestamp` and `fetched` fields. No other keys.
  (The live price value is deliberately not copied into any doc or
  this report.) Upstream still not confirmed — Yahoo Finance relay
  remains inference only. The coordinator independently verified
  the saved response (keys/field types match).
- `fetch_mae_mart()` now fills `futures_price` on corn/soy/wheat
  rows from the proxy as an optional second step
  (`include_futures=True`, one GET per symbol: `ZCZ26=F`,
  `ZSF27=F`, `ZWN27=F`), following the page's own rule (`USX`
  cents ÷ 100; other currencies taken as dollars as-is). New
  helpers: `parse_mae_mart_proxy_json()` (pure parser; ignores
  malformed/unknown-symbol entries) and
  `fetch_mae_mart_futures()` (per-symbol failure skipped, never
  fatal). Any proxy failure degrades gracefully to the static-only
  rows (basis only, `futures_price=None`, "proxy unavailable"
  note). 7 new tests, all synthetic fixtures with invented values
  — proxy JSON cents→dollars, malformed-entry handling, fetch fills
  all three futures crops, proxy failure leaves rows unchanged,
  `include_futures=False` skips the proxy, one GET per symbol with
  the contact User-Agent.
- **Deliberately NOT done:** `cash_price` is never computed from
  futures + basis — that remains an open decision for Adam/the
  coordinator (using a third-party relay + static basis to compute
  cash is a bigger step). Rye untouched (no symbol; static
  `manualPrice` cash as before).

### Ingestion-orchestrator coverage audit — real gap found and fixed
- **How the orchestrator enumerates sources (three paths, none
  reads `us_elevators_urls.toml`):**
  1. **FastAPI scheduled poll** — `app/jobs/poll_sources.py` →
     `poll_due_sources()` → `list_due_sources()` →
     `run_source_refresh()` → `_fetch_with_timeout()` (spawned
     subprocess, per-source timeout) → `fetch_with_adapter()` in
     `source_registry.py`. Enumeration is by `Source` DB rows,
     filtered on `is_active`, `source_type == "automated"`, and
     `next_poll_at` due (advanced after each attempt by
     `update_source_health_state()`, so due-gating works).
  2. **Deployed 08:00/15:00 job** (checklist §4) —
     `python -m app.jobs.daily_source_ingestion` → file-source
     cycle only (`source_type == "file"`). It reaches **0 of 93
     registry adapters**.
  3. **Legacy GrainBidder** — hardcoded 10 Ontario fetchers gated
     by `[sources]` toggles, plus `config.toml`
     `[[us.elevators]]` (121 entries, Cycle-18 synced) dispatched
     by type to generic `fetch_us_agricharts(url, name)` /
     `fetch_us_dtn(url, name, playwright)`. Writes CSV/Excel only,
     not the platform DB; skips `bushel`, `agricharts-embed`,
     `usda`, `wpdatatables`, etc.
  4. Manual `POST /api/sources/{id}/refresh` reaches any single
     adapter with a `Source` row (seed defaults to pilot;
     `scope=all` seeds all 93).
- **Per-family trace** (registry = 93 adapters; all fetch functions
  exist and are zero-arg callable — the `url`-taking ones all have
  module defaults): bushel 62, cashbids-embed 13, usda-mirror 2,
  wpdatatables 1, fmn 1, Ontario direct_dict 4, Ontario playwright
  9, andersons 1. **Before the fix, scheduled polling reached only
  the 5 pilot keys** (`agricharts`, `glg`, `hensall`, `snobelen`,
  `andersons`); the other 88 were unreachable on schedule. US
  agricharts (13 enabled) + DTN (13 enabled) urls-toml entries
  have **no registry adapter at all** — reachable only via
  GrainBidder's generic functions.
- **Gap fixed (small, safe):** removed the pilot-allowlist clause
  (`Source.adapter_key.in_(pilot_keys)`) from
  `list_due_sources()` in `app/services/source_orchestration.py`
  (9 lines changed, comment explains). Remaining gates unchanged;
  the pilot set still governs promotion status and remains the
  default seed scope, so pilot-only deployments are unaffected
  until an admin seeds `scope=all`. 3 regression tests in
  `tests/test_source_orchestration_due_sources.py` (in-memory
  SQLite, seeded from the registry): due set equals the enabled
  registry set, non-pilot adapters included, inactive/file/
  not-yet-due excluded. Verified all 3 fail on pre-fix code (via
  temporary stash) and pass after. The coordinator independently
  verified the diff (pilot clause removed, gates otherwise
  unchanged).
- **Gaps documented, not fixed** (in the catalogue note): (1) the
  deployed 08:00/15:00 cron runs the file-ingestion job, not the
  poller — scheduling `poll_sources` is a deployment decision;
  (2) US agricharts/DTN need an adapter-shape change (registry
  calls `fetch_fn()` with no args; these require a URL); (3)
  toggled-off adapters `bunge` and `mapleview` (`[sources]` off,
  registry present) are still seedable and fetchable — the FastAPI
  side never reads `[sources]`; coordinator to decide if seeding
  should honor toggles. Also flagged name-level collisions
  (urls-toml disabled `Bunge`/`Collwest Grain`/`United Coop`/`The
  Andersons`/`Smithfield` vs enabled registry keys) as unverified,
  not asserted as the same entities.
- Could not verify from code alone whether `poll_sources` is
  scheduled anywhere in production (only a local Windows task
  script found) or whether the urls-toml disabled names are the
  same entities as the registry keys.

### Merge plan extended to Cycles 16–18
- New "Cycles 16–18 (added Cycle 19)" section, verified from git
  history and the cycle reports (coordinator spot-checks: chain
  `master..cycle-18` = **55 commits**, 0 merges; tips 16
  `ee1a794`, 17 `6154176`, 18 `722dd8f`; per-branch 2 commits each;
  test chain 638 → 643 → 646; Alembic head still `0019`; CI
  workflow file still untracked). 184 lines added, 0 removed.
  The Cycles 13–15 section's "49 commits" figure re-verified
  correct. One correction recorded in the new section: the Cycle
  17 report's "122 entries" was a grep artifact — true count is
  **121 entries, 102 enabled**.

### Super-plan §9 extended to Cycle 18
- Heading/intro now cover Cycles 1–18 (test chain 179 → 646);
  Cycle 17 + 18 bullets added; blockers updated (CGB AgriCharts
  embed, Mae-Mart proxy identified, sweeps complete).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 19 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll, United Coop, Ursa), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Staleness watch: Chadbourn (Nov 18), Hamer (Nov 18), Skyland
  3370/3621 (Nov 18).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- **New gaps documented this cycle:** deployed 08:00/15:00 cron
  runs the file-ingestion job, not the poller (scheduling decision);
  US agricharts/DTN entries have no registry adapter (adapter-shape
  change needed); toggled-off `bunge`/`mapleview` are still seedable
  (should seeding honor `[sources]` toggles?).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–18: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 19:** nothing new needs Adam — but the Mae-Mart
cash-price computation and the poller scheduling decisions are
flagged for the coordinator.
