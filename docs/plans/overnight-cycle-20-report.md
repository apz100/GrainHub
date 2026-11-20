# Overnight Cycle 20 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-20` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 20 complete — 26 US agricharts/DTN registry
adapters wired (registry now 119), seeding + poller honour the
`[sources]` toggles, merge plan extended to Cycle 19, super-plan
§9 extended to Cycle 19.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere. 0 web fetches in
this cycle — code work only.**

## 1. Commits

| Commit | What |
|---|---|
| `24a61d0` | 26 US agricharts/DTN adapters wired (119 total); seeding + poller honor [sources] toggles; merge plan extended to Cycle 19 |
| *(this commit)* | Cycle 20 report |

## 2. Test results

- **Full API suite: 692 passed, 0 failed** (Cycle 19 ended at 656).
  New tests in Cycle 20: agricharts/DTN adapters 30, toggle gating
  6 = **36 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### URL-bound registry adapters — 13 agricharts + 13 DTN (0 GETs)
- **AgriCharts — all 13 static-capable** (writeBidRow confirmed in
  fetched HTML, Cycle 1, or verified live): Ag Plus, Farmers Win
  Coop, Heartland Coop, Heritage Grain Cooperative, Keller, Kokomo
  Grain, Legacy Farmers, Pro Ag (78 rows verified live Cycle 11),
  West-Con (84 rows, Cycles 11–12), Wheaton Dumont (43 rows, Cycle
  12), Central Farmers Coop, Anthony Farmers Co-op, Mulvane Coop.
- **DTN — all 13 JS-only** (no static bid rows; widget family
  identified in the Cycle 6 sweep unless noted): Ag Partners
  (modern DTN widget), Al-Corn (classic CashBidTable, companyID
  239483 — exact fit for the generic), Allied Cooperative
  (modern), Aurora Coop (modern), CFS (aghost widget +
  location-cookie flow), Elite Octane (CIHedging loader), Frontier
  Coop (**StoneX, not DTN** — flagged in code, catalogue, and
  toggles), Green Plains (modern), Kanza Coop (ATLAS shell),
  Sunrise (classic, companyID 23043, Cycle 10), Brubaker Grain,
  Hoffman Ag, Wilton Farmers Union Elevator (DTN-subdomain/index.cfm,
  rows only in search index, Cycle 1). None are "unknown" — only
  whether each renders collectable rows in Playwright is still open.
- `US_AGRICHARTS_SITES` map + 13 zero-arg `fetch_<slug>()`
  wrappers calling `fetch_us_agricharts(url, name)`;
  `US_DTN_SITES` map + 13 wrappers calling
  `fetch_us_dtn(url, name, None)`; plus an explicit guard at the
  top of `fetch_us_dtn`: with `playwright=None` it returns an empty
  DataFrame before touching Playwright or the network (previously
  it fell through to a misleading `'NoneType' object has no
  attribute 'chromium'` error path). Legacy GrainBidder calls with
  a real playwright are unaffected.
- 26 new `[sources]` toggles (none pre-existed, no existing value
  touched): agricharts 13 = `true`; DTN 13 = `false` (JS-only, not
  collectable without a render — same precedent as
  `bunge`/`mapleview`).
- All 26 wired into `source_registry.py` by the coordinator
  (mode `"direct"`, `15, 90`, like the other adapters). Registry
  now holds **119 adapters** (93 + 26). The coordinator verified
  every wrapper exists and the toggles read correctly (Sunrise
  false, ag_plus true).
- 30 new tests, synthetic fixtures only, generic fetch mocked, no
  network — adapter maps match the enabled toml entries exactly;
  each wrapper is zero-arg and passes the correct URL/name (DTN
  with `playwright=None`); the real `fetch_us_dtn(url, name, None)`
  returns empty with no I/O; all 26 toggles exist with expected
  values.
- `heritage_grain_cooperative` is deliberately distinct from
  existing `heritage_coop` (different company/site).
- **Live verification is a later cycle's GET-probe work (0 GETs
  this cycle):** one polite GET each through the 13 agricharts
  wrappers (Pro Ag / West-Con / Wheaton Dumont were verified via
  the generic, not the wrappers), and a Playwright render check
  per DTN page (Al-Corn and Sunrise first — classic shape the
  generic was written for). DTN toggles must stay `false` until
  then. Frontier Coop is StoneX, not DTN — the DTN adapter returns
  empty for it by design; a StoneX collector is a separate
  later-cycle item.

### Seeding + poller honour `[sources]` toggles (Cycle 19 gap closed)
- **New `app/services/source_toggles.py`** — single place the
  FastAPI side consults the `[sources]` toggles. Reuses the
  existing loader
  (`app.platform.market_data.sources.grain_bids.config.config.source_enabled()`),
  which already implements "missing toggle = enabled" — no new
  config mechanism. Only an explicit `false` disables an adapter;
  an unreadable/missing config fails open (everything enabled)
  rather than breaking seed/poll. Exposes `is_adapter_enabled(key)`
  and `disabled_adapter_keys(keys)`.
- `seed_sources_from_registry()` now returns a
  `SeedSourcesResult(created, skipped_disabled)` instead of a plain
  `int`, and skips any adapter whose toggle is off. Today `seed
  scope=all` creates **104 rows** (119 adapters − 15 toggled off:
  bunge, mapleview, 13 DTN) and reports `skipped_disabled` with
  all 15 keys. `list_due_sources()` filters out rows whose adapter
  toggle is off, even if the `Source` row already exists (defence
  in depth — a row seeded before the toggle was turned off must not
  keep polling). The check is where the due list is built, not
  inside the per-source fetch subprocess.
- `POST /api/sources/seed` now returns `{"created",
  "skipped_disabled", "scope", "adapter_keys"}` so the admin can
  see the skipped keys.
- 6 new tests in `tests/test_source_toggle_gating.py`: seeding
  skips toggled-off adapters and records them; seeding includes a
  toggled-on adapter; explicit-key seeding still skips a disabled
  key; `list_due_sources` excludes a pre-existing toggled-off row;
  missing toggle defaults to enabled (synthetic key `testville`);
  toggle flipped off after seeding drops the row from the due list.
- **Coordinator fix during wiring:** adding the 26 adapters broke
  8 tests whose count assertions hardcoded "only bunge/mapleview
  are disabled" (e.g. `assert result.created == len(ADAPTERS) - 2`).
  Fixed by deriving the disabled set from the real toggles
  (`disabled_adapter_keys(sorted(ADAPTERS))`) in both test files —
  no production code changed for this, and the assertions now stay
  correct as adapters are added. Suite green again at 692.
- **Deployment note:** `docs/plans/deployment-checklist.md` §4
  step 6 (new) + §8 checkbox — schedule the poller as a second
  cron job alongside the file job, with the consequence stated.
  Exact invocation verified from code, not guessed:
  `python -m app.jobs.poll_sources` (run from `apps/api` with the
  API's env; default one-shot run; `--loop --sleep-seconds 60` for
  continuous), corroborated by the existing
  `GrainBids/grainbids/infra/scripts/run-source-poller.ps1`. No
  deployment config or cron was changed. Note also recorded: the
  poller errors out if the `Commodity` table is empty, so at least
  one Commodity row must exist before the first run.

### Merge plan extended to Cycle 19
- New "Cycle 19 (added Cycle 20)" section, verified from git
  history and the cycle report (coordinator spot-checks: chain
  `master..cycle-19` = **57 commits**, 0 merges; tip `b47d638`;
  Cycle 19 added 2 commits; test count 656; Alembic head still
  `0019`; CI workflow file still untracked). 176 lines added, 0
  removed. The Cycles 16–18 section's "55 commits" figure
  re-verified correct.
- Repo hygiene check (read-only): only the in-progress super-plan
  edit and the known untracked `.github/` in `git status`;
  `GrainBids/grainbids/package-lock.json` has not reappeared;
  `__pycache__` dirs are gitignored — no action needed.

### Super-plan §9 extended to Cycle 19
- Heading/intro now cover Cycles 1–19 (test chain 179 → 656);
  Cycle 19 bullet added; blockers updated (poller reaches all 93
  adapters — now 119 with the new ones — but the deployed cron
  still runs the file job, not the poller; Mae-Mart proxy live).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 20 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Live verification of the 13 new agricharts wrappers (1 GET each).
- Staleness watch: Chadbourn (Nov 18), Hamer (Nov 18), Skyland
  3370/3621 (Nov 18).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–19: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 20:** nothing new needs Adam.
