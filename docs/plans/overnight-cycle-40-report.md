# Overnight Cycle 40 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-40` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (morning, America/Toronto)
**Status:** Cycle 40 complete — Barchart/DTN parked at Adam's
request; `andersons` toggled off; feed plug-in proven in code
(5 new tests); Collwest correction; merge plan extended to
Cycle 39, super-plan §9 extended to Cycle 39. Executed directly
by the coordinator (subagent spawning still unavailable).

**Timing note:** the overnight window's ~07:30 stop passed
before this cycle was tasked — Adam's morning update arrived at
~07:58 EST with new direction (park Barchart/DTN, prove the
plug-in path in code). This cycle ran on that update and closes
the overnight work; no further cycle is started after it.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere. No probe of the
Andersons legacy DTN host was made — the probe-list entry for
that host was removed, not exercised.**

## 1. Commits

| Commit | What |
|---|---|
| `32e53b6` | Park Barchart/DTN at Adam's request; andersons toggled off; feed plug-in proven in code (5 tests); Collwest correction; merge plan extended to Cycle 39 |
| *(this commit)* | Cycle 40 report |

## 2. Test results

- **Full API suite: 716 collected, 711 passed, 5 skipped, 0 failed.**
  The 5 new tests are `tests/test_licensed_feed_plugin.py`
  (all pass). The 5 skipped are pre-existing conditional skips
  whose saved live HTML in `/tmp` was cleaned between turns
  (FMN ×2, West-Con, Wheaton Dumont, Heritage) — not a
  regression: in Cycle 39, with the `/tmp` files present, the
  same suite collected 711 and passed 711.
- Web build: not re-run (no web files changed; last full pass
  Cycle 38, 33/33 pages).

## 3. What was built (done)

### Barchart/DTN parked at Adam's request — the decision, in code

Adam's morning update (2026-11-19): he does NOT want to worry
about Barchart/DTN yet. Do not chase the decision, do not
contact them, do not probe the Andersons legacy DTN host, and
do not spend any more cycles on Barchart/DTN pricing or
licensing. The app must instead be designed so their feeds can
be incorporated easily down the road. Changes made:

- **`andersons = false`** in `config.toml` `[sources]`
  (one-line flip, reversible, with a comment citing the design
  doc §8). The `andersons` adapter targets the legacy DTN API
  host (`dtn-api.andersonscanada.com/cash-bids/<slug>`), built
  in Cycle 1, never re-verified. Seeding
  (`seed_sources_from_registry`) and scheduled polling
  (`list_due_sources`) both honour the toggle, so the adapter
  can no longer be seeded or polled. **Seedable count is now
  101** (119 adapters − 18 disabled: bunge, mapleview, 13 DTN,
  Heartland, Mulvane, andersons). The adapter stays in the
  registry as the record of the source; its
  `PILOT_ADAPTER_KEYS` membership is now vestigial (a pilot-scope
  seed skips it via the toggle) and can be cleaned up when the
  feed topic is re-opened.
- **Probe-list entry removed:** the Andersons Canada legacy DTN
  host URL was deleted from `SAMPLE_SOURCES` in
  `app/services/price_source_probe.py` (replaced by a comment
  recording the removal). The probe runner is manual/CLI only;
  nothing in the suite or the poller ever called it, and it was
  not exercised. LAC's page lives on a `londonag-dtn.com`
  domain, but that is a public elevator page, not a DTN API
  host — untouched.
- **Design doc updated**
  (`docs/plans/barchart-dtn-integration-design.md`): header now
  records PARKED 2026-11-19 at Adam's request; §7 decision log
  gains a parked entry; new **§8 feed plug-in checklist**
  (11 steps — see below). The §6 vendor questions stay for
  when/if Adam re-opens the topic.
- **Deployment checklist updated:** §0 row 5 now reads Parked
  (was Open); §7 no longer lists Barchart/DTN among the
  Adam-owned gaps.
- **Super-plan §9 "Remaining blockers" paragraph updated:**
  Barchart/DTN is explicitly NOT a blocker and NOT on the
  needs-Adam list. The CGB `cashbids-js.php` question and the
  Mae-Mart cash-price decision it gated are parked with it
  (the Mae-Mart cash-price question waits on Adam re-opening
  the feed topic or deciding it standalone).

### Feed plug-in proven in code (not just in a doc)

Audit (grep, Cycle 40): the only `barchart`/`dtn` mentions in
`app/` outside collector modules are the 13 DTN-family adapter
entries in `source_registry.py` (all toggle-off), two
docstring/note mentions in `app/api/routes/futures.py` (delay
labels, "until a feed is wired"), and the now-removed
probe-list entry. Zero mentions in the web app. Every price
consumer reads `NormalizedPrice` generically:

- Market search, the newsletter, and the market report all call
  `_load_preview_payload(..., source_name=None, ...)` — no
  source filter, no vendor allowlist.
- Best-bids and the basis tracker query `NormalizedPrice`
  directly with no source-name allowlist (best-bids filters
  only on `cash_price_bu` being present).
- Advisor signals take a duck-typed price row
  (`signal_for_profile_and_price`); research dashboards read
  `ResearchReport` rows.

New `tests/test_licensed_feed_plugin.py` (**5 tests**, all pass):

1. A synthetic adapter registered in `ADAPTERS` resolves
   through `fetch_with_adapter` — same shape as the
   `andersons` entry (mode `direct`, source_class `api`).
2. Seeding honours toggles: the synthetic key seeds (no toggle
   entry = enabled) while parked `andersons` is skipped and
   reported in `skipped_disabled`.
3. Defence in depth: a pre-existing `andersons` `Source` row
   never comes back as due from `list_due_sources`.
4. Rows with `source_name` `barchart/getGrainBids` /
   `dtn/content-services` surface in market search (HTTP,
   `GET /api/market-search?commodity=Corn`) with no route
   change.
5. The same rows surface on the public best-bid page (HTTP,
   no auth headers) under their own source names.

**Feed plug-in checklist (design doc §8, summarised):**
redistribution licence in writing + sandbox key in env only →
thin client (`barchart_client.py` / `dtn_client.py`, key-gated
error mirroring `ResearchKeyRequired`) → one collector per
vendor (`licensed_feed_collector.py`, §4 mapping to
`NormalizedPrice`) → one registry adapter (`direct` / `api`) →
explicit `[sources]` toggle (off until the key exists) →
`licensed_feeds` config section (env-gated, disabled by
default) → seed verification → end-to-end ingestion check →
no-route-change verification across market search / best-bids /
basis / newsletter / market report / source health → fallback
confirmation (free sources keep running; feed down shows
`broken`/`stale` with the real reason, never a silent
fallback). What stays disabled until a licence/key exists: the
toggle, the config section, and any futures/canola wiring that
depends on the feed. The futures strip keeps returning
contract structure with prices `null` and the ICE canola desk
stays `not_wired` — the honest state, not a gap to work around.

### Collwest toggle / toml — resolved, no change needed

The Cycle 39 coverage snapshot claimed `collwest` has no
explicit `[sources]` toggle and defaults to enabled.
**Wrong:** `collwest = true` is an explicit toggle in
`config.toml` `[sources]` (line 32). Its `[us]` entry (both
toml files, synced) is disabled with the comment that the
country was confirmed Canadian 2026-11-18 (Collingwood, ON;
CAD) — removed from the US list per the catalogue, kept only
as a disabled record so the URL is not re-added. A
name-matched comparison showed toggle-vs-`[us]` mismatches
are **normal and by design**: Sunrise, Mulvane, Brubaker
Grain, Hoffman Ag, Wilton Farmers Union Elevator are
`[us]`-enabled + toggle-off (the `[us]` list catalogues the
source; the toggle gates collection — the Heartland/Mulvane
pattern), and United Coop is the reverse (`[us]`-off +
toggle-on), the same shape as Collwest. The Cycle 18 sync
guard deliberately compares only name/url/type/enabled
between the two `[us]` lists, not toggles vs `[us]` enabled.
The FMN precedent also matters: Canadian CAD sources are
enabled platform-wide. **No toggle change made** — the
"mismatch" dissolves on inspection. (One follow-up exec call
during the comparison failed with "subprocess executor is
draining"; the executor recovered on retry and the comparison
was completed from the name-matched result, not claimed from
the failed call.)

### Collector-coverage snapshot — corrected in Cycle 40

`docs/plans/collector-coverage.md` (Cycle 39 doc) corrected:
headline **102 → 101 toggle-enabled, 17 → 18 off**;
`andersons_source` family row 1 → 0 enabled; `andersons` row
`on` → `OFF`, status `pending` → `off`, note rewritten as
parked; `collwest` row note corrected (explicit toggle, `[us]`
disabled as a record by design); open item 1 rewritten as
RESOLVED (no change needed), open item 2 rewritten as PARKED
(do not probe). A correction banner was added under the title
(the snapshot itself stays as-of Cycle 39).

### Merge plan extended to Cycle 39

New "Cycle 39 (added Cycle 40)" section, verified from git
history and the cycle report (coordinator spot-checks: chain
`master..cycle-39` = **97 commits**, 0 merges; tip `79efad8`
(full `79efad812e7d7785db0cf33158113aac46d1d525`); Cycle 39
added 2 commits (`5dfb6de`, `79efad8`); test count 711;
Alembic head still `0019`; CI workflow file still untracked;
Cycle 38→39 work-commit diff 4 files, 446 insertions, 0
deletions; report commit 1 file, 156 insertions). The Cycle 38
section's "95 commits" figure re-verified correct. No
discrepancies found between git and the Cycle 39 report.

### Super-plan §9 extended to Cycle 39

Cycle 39 bullet added (unreachable trio unchanged; coverage
snapshot written; merge plan extended to Cycle 38, 95
commits). The "Remaining blockers" paragraph was updated as
described above (Barchart/DTN parked, not a blocker).

### Price-source catalogue — Cycle 40 section added

New "Cycle 40" section (Barchart/DTN parked, Collwest +
Andersons corrections, feed plug-in proof, design-doc §8).
The Cycle 39 section's collwest/andersons wording is left as
written (historical record of what Cycle 39 found); the Cycle
40 section records the corrections explicitly.

## 4. North Gower Grains boundary — applied

Zero new references in any new Cycle 40 code, tests, or docs
(verified by grep on the changed/new files). The only hit is
the pre-existing probe-list entry `("North Gower Grains",
"https://northgowergrains.com/")` — an unmodified context line
in the diff, kept as one ordinary price source among many,
which is exactly what the refined boundary allows (public
prices may be collected as one ordinary source; no pilot /
showcase / branding / affiliation). No contact made.

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
- Mae-Mart `cash_price` from futures + static basis — parked with
  the Barchart/DTN decision (see §3); futures_price is still
  filled by the proxy, cash is still not computed.
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).
- Subagent spawning is unavailable in this session — cycles run
  coordinator-direct unless it comes back. One exec call in this
  cycle failed transiently ("subprocess executor is draining");
  the executor recovered on the immediate retry and no work was
  lost.
- The 5 skipped tests are pre-existing `/tmp`-dependent skips
  (saved live HTML cleaned between turns); they pass when the
  scratch files exist.

## 6. Blocked / needs Adam

Carried from Cycles 1–39, **minus Barchart/DTN (parked, see §3):**
NASS key, FAS/data.gov key, LLM provider + key, ERP choice
(Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, The
Andersons, Landus).

**New in Cycle 40:** nothing new needs Adam. Barchart/DTN is
parked at his request, with the plug-in points listed in §3 —
it is not a blocker for the current build, and the CGB
`cashbids-js.php` question and the Mae-Mart cash-price
decision are parked with it.
