# Morning report — marathon run, Thu 2026-11-19 → Fri 2026-11-20

**Branch:** `marathon/2026-11-20`, stacked on `overnight/2026-11-20`
(which is itself unmerged — one stacked merge decision, below).
**Nothing merged. Production untouched. Total spend: $0.**

**Test gate:** full API suite **768 passed / 5 skipped / 0 failed**
(baseline 731 → +37 net new tests). **Web build green, 34 routes**
(33 + the new /research/psd). Alembic single head **0021**.

**Timing, honestly:** the plan budgeted 8 hours; the work finished
in about 2¼ hours (23:30–~01:45 EST). The phases turned out to be
finite and three of them ran in parallel — the scope in the plan was
completed in full, not shrunk; there was simply no honest way to
stretch verified work to fill the clock. Two items remain genuinely
blocked by this sandbox's network egress (not by effort), listed
under Blocked.

---

## Headline: the basis-tracker bug was a pattern, and it was everywhere

Last night's production crash came from loading full
`PriceSnapshot` rows — including `raw_payload_json`, a whole day
file per snapshot — when only `captured_at` was needed. Phase A
audited every GET endpoint for that class and found it live in
**8 more places**: the shared preview query behind the price list,
previews, market search, the market report and the newsletter
(up to 3,000 payloads per request), top-movers, price history
(5,000), best-bids, saved-search/watchlist previews, the quotes
export loader (20,000), and the research calendar (unbounded, full
payload JSON). On the 512 MB free instance these were the same
crash waiting for a bigger day. All are fixed with deferred
payload loading; the advisor's signal endpoint also loaded every
matching price row to take the first — now `limit(1)`. Evidence:
19 new real-database tests — **10 failed before the fixes, all 19
pass after** — plus a full audit table (phase-a-notes.md) covering
every GET endpoint, including the ones verified clean.

## Phase by phase

### Phase 0 — Baseline and queue: DONE
Baseline re-verified on the stacked branch (731/5/0, web green);
29 route modules (~90 endpoints) and 119 registry adapters
inventoried; live production snapshots saved read-only
(`docs/marathon/snapshots/`).

### Phase A — Endpoint robustness audit: DONE (commit 4b1a1fc)
See headline. Documented but not fixed (in the notes): the
ingestion company-identity endpoint aggregates an unbounded scan
in Python (proper fix is a SQL GROUP BY — a follow-up, no
correctness break today); price_history/seasonal have **no org
scoping** (flagged: that's a product decision, code unchanged);
alerts/rules N+1 and a few no-limit per-org config lists
(registry scale, observed only).

### Phase B — Commodity/location normalization: DONE (f4d6901)
A conservative resolver (crop-tag aware) + a `commodity_aliases`
override table (migration 0020) now sit under the existing
canonicalization seam, so facets, previews and search all inherit
it. The 25 live labels collapse into 6 canonical groups; "HRW
Wheat (New Crop)" keeps its crop tag. **Search is fixed for
canonical names**: "HRW Wheat" previously matched zero stored rows
(raw labels are "HRW New Crop Wheat", "HARD RED WINTER"); it now
expands to the raw variants — proven against a real database.
Ambiguous labels (`Wheat`, `Hard Red Wheat`, `GLG Cash`) are
flagged with reasons and never guessed; a human can pin them in
the override table. Locations: all 136 live facet locations
verified already-canonical — no speculative merges. A dry-run-only
report job (`python -m app.jobs.report_commodity_normalization`)
makes the mapping auditable; it never writes.

### Phase C — Research silo build-out: DONE (9c4c095)
The FAS PSD data wired last night is now reachable: cached routes
`GET /api/research/fas-psd/world` (decoded with runtime
attribute/unit lookups), `/fas-psd/commodities`, and
`/nass/series` (cached, bounded, honest `truncated` flag), backed
by `research_cache_entries` (migration 0021, 24 h TTL; a labelled
"stale" payload is served on upstream failure instead of an
error). New web page **/research/psd** (World Supply & Demand)
with key-required / failed / empty states and cache age shown,
linked from the research index. NASS live shape re-verified
through the connector (corn yield 179.6 bu/acre). Scaffold note:
production data flows only after the stacked merge + a schedule —
both Adam's decisions, unchanged from last night's list.

### Phase D — Collector coverage: DONE (6da1ce1)
96 adapters executed live: **93 returned rows, 0 errors**; counts
match prior verifications except ag_state (11→21), agp (8→1,
fluctuates), USDA mirrors (197→182, new daily report). Only
zero-row adapters are the three already known (one stub, two
closed co-ops — re-confirmed). **FMN is settled**: 10 filtered
views probed — all return empty shells over plain HTTP, so the
~248 dropdown-only delivery points are not reachable without a
browser render; FMN coverage stays 453 rows / 87 points. No
adapter code changed (nothing was proven to have changed shape).
Catalogue + coverage docs updated with dated statuses.

### Phase E — Web resilience: DONE (f58e6ae)
A shared resilient fetch (timeout sized for a ~50 s cold start,
one retry, mutations never replayed) plus honest states across
the dashboard, alerts panel, sources, price-finder, best-bids and
all research pages: "Waking the API" notices, skeletons, and
retryable errors replace the indefinite "Refreshing…". Server
pages now distinguish "API unreachable" from "no data yet" — the
two were indistinguishable before. Accessibility: focus-visible
outline (none existed), aria labels/pressed states, associated
form labels.

### Phase F — Newsletter/market-report dry run: DONE (a6c35cb)
Generated locally from realistic data and inspected line by line
(outputs in `docs/marathon/dry-run/`): GrainBids branding, no
placeholder leakage, medians/ranges verified by hand, honesty
caveats intact, real calendar loader renders proper upcoming
report names, delivery OFF. **No product defects found**; the one
suspicious output was traced to the dry-run fixture itself.

## Blocked (environment, not effort)

- **Browser render checks** (FMN filtered views rendered, the 8
  Ontario JS-widget pages): this sandbox's Chromium cannot egress
  (established last night; curl/python work, browser tunnels
  don't). Still open for any machine with direct internet.
- **WASDE / Crop Progress live-file parse verification**:
  www.usda.gov returns 403 to this sandbox and downloads.usda.gov
  is unreachable from it. The parsers are covered by fixture
  tests (passing); production egress from Render is different,
  so this can be verified from the server after a merge.

## What needs Adam (short list, each priced)

| # | Decision | Cost |
|---|---|---|
| 1 | Merge the stack: `overnight/2026-11-20` then `marathon/2026-11-20` into master (deploys: basis fix, Phase A payload fixes, normalization, research routes + PSD page, web resilience; migrations 0020 + 0021 run on boot) — then verify /api/basis/tracker returns 200 | $0 |
| 2 | Run the source seed job against prod + retire the Windows-path source (from last night's list; ~10 min) | $0 |
| 3 | Scheduling: GitHub Actions ($0, recommended, workflow prepared inert) vs Render cron ($2.00/mo, needs explicit OK — NOT created) | $0 / $2/mo |
| 4 | grainbids.com DNS (checklist prepared, nothing entered) | $0 |
| 5 | Optional pins: any `commodity_aliases` overrides for the 3 ambiguous labels (e.g. if "Hard Red Wheat" from a given source is always spring wheat) | $0 |
| 6 | Optional follow-ups from Phase A notes: SQL GROUP BY for the company-identity endpoint; decide whether price_history/seasonal should be org-scoped | $0 |

USDA keys into Render: **done last night** (verified configured
live) — off the list.

## Commits on `marathon/2026-11-20`

- `cd0e988` Marathon plan (Adam-approved spec)
- `14a685c` Phase 0: baseline, inventory, live snapshots
- `f4d6901` Phase B: canonical commodity resolution + search expansion
- `6da1ce1` Phase D: collector coverage re-verified; FMN settled
- `9c4c095` Phase C: cached research routes + /research/psd page
- `a6c35cb` Phase F: newsletter/market-report dry run
- `4b1a1fc` Phase A: endpoint robustness audit + payload fixes
- `f58e6ae` Phase E: web resilience
- `15a04ac` Run log: integration + final gates

## Guardrail compliance

Zero spending · no merges · production untouched (read-only GETs
only) · no production DB writes (local fixtures, injected rows,
live public fetches) · no vendor contact · LLM and Barchart/DTN
parked · North Gower treated as one ordinary source (15 rows,
counted like every other adapter) · no secrets in git, logs or
reports (diff scanned; USDA access only through the connector
helpers) · no Chromium-dependent work attempted.
