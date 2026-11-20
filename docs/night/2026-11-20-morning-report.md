# Night Queue — Morning Report, 2026-11-20

Branch: `night/2026-11-20` (from master `dd43fac`). Four work
items, four commits, all gates green. Nothing merged, production
untouched, $0 spent. Baseline on master was 768 passed / 5 skipped
/ 0 failed; the branch finishes at **785 passed / 5 skipped /
0 failed** with the web build green (34 routes) at every item
boundary.

## Item 1 — Bounded-loading volume tests · DONE (commit 4aae4db)

New `tests/test_volume_bounded_loading.py` (8 tests): a real
SQLite database seeded with thousands of rows per test, SQLAlchemy
`load` events on `NormalizedPrice` / `PriceSnapshot` counting
materialized instances, plus an emitted-SQL check that
`price_snapshots.raw_payload_json` is never transferred. Every
Phase A endpoint's bound binds **exactly**:

| Loader / endpoint | Seeded | Materialized |
|---|---:|---:|
| Shared preview loader (price list / previews / market search) | 3,000 | exactly limit×3 (30 at limit=10) |
| Top-movers loader | 3,000 | 30 at limit=10 |
| Price-history loader | 6,000 | exactly `_HISTORY_FETCH_LIMIT` (5,000) |
| Best-bids loader | 1,000 | exactly `_BEST_BIDS_FETCH_LIMIT` (300) |
| Saved-search preview | 1,000 | exactly 25 (the limit) |
| Watchlist preview | 1,000 | exactly 20 (the limit) |
| Quotes-export loader | 20,500 | exactly 20,000 |

No endpoint proved unbounded, so no fixes were needed — the
marathon's Phase A bounds all hold under volume. Gate after the
item: 776 passed / 5 skipped / 0 failed; web build green.

## Item 2 — Company-identity SQL GROUP BY · DONE (commit 48c6864)

`list_ambiguous_location_company_candidates`
(`app/services/source_company_identity_diagnostics.py`) no longer
aggregates in Python. The identity predicate
(`_source_creates_company_identity` / `canonical_source_name`) is
a pure function of the source-name string, so the service now
selects the distinct source names under the base filters,
evaluates the predicate once per name, runs **one GROUP BY**
(location, company, source_name) count query over just the
passing names, and merges into the unchanged row builder.

Equivalence is proven, not asserted: new
`tests/test_company_identity_grouped_aggregation.py` (4 tests)
holds a verbatim copy of the pre-fix implementation as a reference
and compares byte-identical outputs across ambiguous,
single-company and ghost locations; non-identity and `None` source
names; canonical label merges (GLG + Great Lakes Grain → one row
of 5); untrusted companies; cross-org rows; a trusted current
company with zero price rows; the `source_id` filter; the limit
slice; and a 3,000-row volume seed whose emitted SQL contains the
GROUP BY. Gate: 780 passed / 5 skipped / 0 failed; web build
green. (One intermediate full-suite run showed a single failure
whose name was not captured; two subsequent full runs were both
fully green — recorded here honestly as a probable flake; it has
not recurred.)

## Item 3 — Collector coverage extension · DONE (commit 71c3260)

Ontario-first, one polite GET each (`GrainHub-Research/1.0`),
static sources only:

- **Homeland Grain (Norwich, ON) — new working adapter.** Its
  `/cash-bids` page serves a standard 7-column Bushel `.cbmod`
  widget; the generic parser handled all **13 live rows** unchanged
  (corn, soybeans, delivered-Hamilton soybeans, soft red winter
  wheat, on-farm pick-up wheat). Wired end to end:
  `BUSHEL_SITES["homeland"]`, `fetch_homeland()`, registry adapter
  `homeland`, `[sources]` toggle on, CAD. Fixture-tested
  (`tests/test_bushel_homeland.py`, 5 tests, synthetic fixture
  mirroring the live shape). Registry totals now: **120 adapters,
  102 toggle-enabled, 89 live.**
- **Charwen Farms — ruled out.** Its own `/cash-bids/` 404s; the
  homepage "Cash Bids" link points at LAC's bids page, and LAC
  already lists Charwen as a delivery point — a duplicate of
  existing coverage.
- **Addis Grain — ruled out for plain HTTP.** Bids render through
  a JS DTN + Grain Discovery block; no static table (Mapleview
  class — needs a browser render).
- **St. Lawrence Grains & Farm Supply — ruled out for plain
  HTTP.** Same DTN + Grain Discovery JS block on `slgrainsfs.ca`.

Docs updated with dated results: `docs/plans/collector-coverage.md`
(per-adapter row, family counts, night addendum) and
`docs/plans/price-source-catalogue.md` (Charwen/Addis rows, leads
list). Gate: 785 passed / 5 skipped / 0 failed; web build green.

## Item 4 — Ops runbook · DONE (commit 5927ac5)

`docs/runbook.md`: what runs where (Render API / Vercel web /
Supabase DB), the deploy flow (push master → auto-deploy,
`alembic upgrade head` on boot), environment variables **by name
only**, free-tier facts (512 MB, sleep + cold start, 750
instance-hours, Supabase 500 MB), health endpoints, incident
response from the 2026-11-19 OOM night (signatures: proxy 502 +
a *missing* request log line + Render Events "Ran out of memory";
where Logs / Events / Deploys live; auto-recovery behaviour;
rollback caveat), and the deployment verification checklist —
probe a **new** route to prove new code is live before testing a
suspect endpoint, then re-check health and Events afterwards.

## Commits on this branch

| Commit | Item |
|---|---|
| `4aae4db` | 1 — bounded-loading volume tests |
| `48c6864` | 2 — company-identity SQL GROUP BY |
| `71c3260` | 3 — Homeland Grain adapter + Ontario lead resolutions |
| `5927ac5` | 4 — production ops runbook |

11 files changed vs master, 1,296 insertions, 27 deletions.

## Guardrail compliance

- **$0 spend** — nothing bought, enabled, or provisioned.
- **No merges** — all work is on `night/2026-11-20`; master and
  every other branch untouched.
- **Production untouched** — no production API calls were needed
  or made this session (not even health probes); no production DB
  writes; all tests ran against local SQLite.
- **Protected files untouched** — `app/api/routes/basis.py` and
  `app/services/basis_tracker.py` do not appear in the branch diff
  (the hotfix branch owns them).
- **Parked decisions respected** — no LLM work; no Barchart/DTN
  contact or probing (the DTN + Grain Discovery blocks on the
  Addis / St. Lawrence pages were identified from their static
  HTML only; no DTN host or endpoint was called). North Gower
  appears nowhere in this branch's changes.
- **No secrets** in git, logs, or this report — the runbook lists
  variable names only; live captures stayed in `/tmp`; committed
  fixtures use invented values.
- Third-party fetches were one polite GET per page with the
  project's contact user-agent.

## Parked for Adam

1. **Basis hotfix awaiting merge OK** — branch
   `hotfix/basis-tracker-sql` is built and verified (777 passed;
   3,000 seeded pairs → 6 materialized). On your go, the 3-step
   post-merge verification is: (1) merge to master and confirm the
   Render deploy + boot migrations, (2) probe a new route to
   confirm the new code is live, (3) then call
   `GET /api/basis/tracker` once and confirm a 200 with no OOM in
   Render Events. **Until then, do not call the tracker on
   production** — the currently deployed code is the one that
   OOM'd on 2026-11-19.
2. **Seed production sources** — run
   `python -m app.jobs.seed_sources` against prod (dry-run first)
   and retire the legacy Windows-path "Ontario Daily File" source
   (~10 min; `docs/decisions/source-registration-rollout.md`).
   The new `homeland` adapter will seed with the rest whenever
   this runs.
3. **Scheduling decision** — GitHub Actions ($0, workflow prepared
   but inert; needs repo secrets + uncommenting the schedule) vs
   Render cron (**$2.00/mo**, UTC-only). Recommendation stands:
   GitHub Actions.
4. **grainbids.com DNS** — checklist ready
   (`docs/decisions/grainbids-dns-checklist.md`); nothing entered.
5. **Commodity pins (optional)** — three ambiguous labels (Wheat,
   Hard Red Wheat, GLG Cash) remain deliberately unpinned in
   `commodity_aliases`; pinning them is a product call.
6. **This branch** — `night/2026-11-20` (4 commits) is ready for
   your review/merge whenever you are; nothing in it needs to
   land before the hotfix.
