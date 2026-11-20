# Barchart / DTN Licensed Feed — Integration Design

**Status: design only — PARKED 2026-11-19 at Adam's request.** Do
not contact the vendors, do not probe the Andersons legacy DTN
host, and do not spend cycles on Barchart/DTN pricing or licensing
until Adam re-opens it. The `andersons` adapter is toggled off and
its probe-list entry removed (Cycle 40). This document stays as the
plug-in spec: §8 is the checklist for adding a licensed feed later.
No vendor has been contacted, no contract or key exists, and no
pricing is quoted anywhere in this document. Every price figure
below is either marked as a stale third-party report that must be
re-confirmed with the vendor, or explicitly labelled "ask the vendor".
Nothing here authorises spending, contact, or a trial sign-up.

**Scope:** Phase 2 of the super plan (`docs/plans/grainhub-super-plan.md`
§6) — a licensed Barchart OnDemand and/or DTN feed as the primary bid
source for the Price Finder silo, with the Ontario scrapers, email bids,
and USDA data as the seed panel and fallback. This design covers the
feed only. It does not cover Barchart/DTN grower-portal products, and it
does not change the existing rule: do not bulk-scrape Barchart or
AgriCharts pages for republication.

**Related blockers:** Cycle 1 report
(`docs/plans/overnight-cycle-1-report.md` §5, item 4) — Adam knows people
at both vendors; no contact was made. Item 5 — the existing Playwright
collector reads a Barchart-hosted page (Greenfield Global / Barchart
marketplace); Adam still needs to confirm whether that is acceptable or
should be dropped. A licensed feed does not retroactively bless that
collector; treat it as a separate decision.

## 1. What each vendor actually sells (public sources only)

### 1.1 Barchart OnDemand

- A commercially licensed REST market-data service: ~70 named endpoints
  returning JSON, XML, or CSV, hosted at `ondemand.websol.barchart.com`
  (older examples also use `marketdata.websol.barchart.com`).
- Auth is a single `apikey` query parameter (some client examples use
  `key=`). No OAuth, no token refresh.
- Endpoints relevant to GrainHub, from Barchart's published catalog:
  - `getGrainBids` — grain cash bids.
  - `getQuote` — real-time, delayed, or end-of-day quotes (futures,
    equities, forex, crypto).
  - `getHistory` — tick, minute-bar, or end-of-day history; date range
    drives the record count unless capped with `maxRecords`.
  - `getUSDAGrainPrices`, `getCmdtyStats` — USDA grain prices and
    commodity statistics.
  - `getFuturesSpecifications`, `getFuturesExpirations`,
    `getFuturesOptions`, `getFuturesSpreads` — futures metadata.
  - `getNews` — headlines by source / category / keyword.
- Barchart's own agriculture data table lists **Cash Grain Bids —
  Barchart, Realtime, US**, plus Grain Price & Basis Indexes (realtime,
  US). Canadian coverage is **not** stated in the public material
  found — see §6, question 1.
- **Redistribution is expressly prohibited** in the published docs:
  data is for internal use only. That is the single most important
  commercial fact in this design: showing Barchart cash bids to
  GrainHub end users is republication, and needs a redistribution
  licence negotiated separately from a plain OnDemand key. Do not
  assume an OnDemand key covers the Price Finder. See §6, question 2.
- No public price list. Barchart builds custom packages through sales.
  A 2021 Barchart support reply, quoted in a third-party review, said
  OnDemand APIs started at $500/month — that is five years old and is
  **not** a quote; treat it only as a floor to ask about.
- The old free market-data API was retired (its host now answers
  HTTP 410). There is no free tier to prototype against.
- Official clients exist for Java, JavaScript, PHP, Python, and MATLAB,
  but treat them as sample code: the Python client on PyPI is at
  v1.1.1 (April 2023) and the Java client has had no commit since
  February 2019. GrainHub should write its own thin client (see §3)
  rather than depend on them.
- No public rate-limit numbers were found. `getHistory` publishes no
  fixed per-call record cap; one endpoint (`getEquitiesByExchange`)
  refuses a `fileDate` more than 30 days back. Assume per-key quotas
  exist and are disclosed only in the contract — design for them
  (§3.4).

### 1.2 DTN — there is no single "DTN API" for cash bids

DTN sells agriculture data through several different products, and the
public material does not describe one self-serve REST API for
per-elevator cash bids. Do not assume the DTN route looks like the
Barchart route.

- **DTN Content Services** (`cp-docs.dtn.com`): REST Web Services plus
  Composable Widgets (a JavaScript framework for embedding DTN
  visualisations) for Markets and Weather content on a licensee's own
  website. Access requires an active account and license keys provided
  by a DTN account representative — keys are not self-serve. Whether
  the Markets API includes per-elevator cash bids, or only futures /
  market commentary, is **not** stated in the public getting-started
  page — see §6, question 5.
- **DTN Portal / DTN Ag Marketplace**: the elevator-branded grower
  portal (cash bids, offers, contracts, scale tickets) that many US
  elevators run. This is a product elevators buy, not a data feed
  GrainHub can call. It matters for two reasons: (a) it is the source
  of the DTN `CashBidTable` widget pages the legacy pipeline already
  reads with Playwright, and (b) it is a competing/complementary
  Elevator Ops surface, not a Price Finder feed.
- **DTN IQFeed** (`iqhelp.dtn.com`): a streaming market-data API over a
  versioned socket protocol (current protocol 6.2), with an SDK behind
  a developer registration and an API Developer Agreement. A 2019 DTN
  FAQ priced the API developer licence at $420/year (stale — not a
  quote) **on top of** a separate feed subscription. IQFeed is
  futures/equities market data; it is not an elevator cash-bid feed.
  Do not pursue IQFeed for the Price Finder unless DTN says otherwise.
- **What to ask DTN first:** which product actually carries licensed,
  redistributable per-elevator cash bids for a third-party web
  application — Content Services Markets API, a DTN Portal data
  feed, or something else — and what its auth, format, and
  redistribution terms are. See §6, question 5.

## 2. Where it plugs in (existing pipeline)

The existing collector contract (super plan §3) is unchanged:

```
fetch -> normalise -> validate -> store raw + normalised
```

A licensed feed is one more collector implementing the same interface
as the current per-source collectors — it is not a parallel pipeline.

| Layer | Today | With a licensed feed |
|---|---|---|
| Source config | `config.toml` / `us_elevators_urls.toml` entries per elevator page | One `barchart` and/or one `dtn` source entry, plus per-location mapping (see §4) |
| Fetch | Playwright / HTTP scrape per page, or Outlook email parse | One authenticated REST client per vendor, called on the ingestion cadence (08:00 / 15:00 America/Toronto today) |
| Normalise | Per-collector parsing into `NormalizedPrice` rows | One mapping per vendor (see §4), into the same `NormalizedPrice` rows |
| Store | Raw snapshot + normalised price, deduped by composite key | Same. The feed's own quote timestamp becomes `captured_at`; the feed's location/commodity identifiers map to canonical companies/locations |
| Health | `ingestion_runs` + `source_health_snapshots` drive `/api/source-health` and the basis tracker's `source_status` | Same tables, same dashboard. A failed/expired key shows up as `broken` with the vendor's error, exactly like a dead scraper today |
| Fallback | — | Free sources keep running (see §5) |

### New code (when a key exists — none of this is written yet)

- `app/services/barchart_client.py` — thin `requests` client:
  `get_grain_bids()`, `get_quote()`, `get_history()`. Key from env
  only (`BARCHART_API_KEY`), never in code, logs, or git. Raises a
  `FeedKeyRequired`-style error when unconfigured, mirroring
  `ResearchKeyRequired` in `app/services/research.py` — the collector
  must refuse to call the API without a key, and the ingestion run
  must record that honestly instead of failing silently.
- `app/services/dtn_client.py` — same shape, once DTN confirms which
  product/endpoint applies (`DTN_API_KEY`, plus whatever auth that
  product actually uses — do not assume `apikey=` works for DTN).
- `app/services/licensed_feed_collector.py` — one collector per vendor
  implementing the existing collector interface; vendor response ->
  normalised rows (§4); records raw payload, run status, parse
  success rate, and errors into `ingestion_runs` like every other
  collector.
- Config: a `licensed_feeds` section (env-gated, disabled by default)
  listing which vendors are enabled and which endpoints are in scope.
  No key in config files — `.env.example` only, following the existing
  rule for `NASS_API_KEY` / `FAS_DATA_GOV_API_KEY`.

## 3. Auth, endpoints, and rate limits (design)

### 3.1 Auth (env keys only)

- Keys live in env (`BARCHART_API_KEY`, `DTN_API_KEY` or the
  DTN-product-specific name), loaded through `app/core/config.py`
  like the NASS/FAS keys. No key is stored in git, in the database,
  or in logs. Key presence is reported only as a boolean
  (`/api/research/status` already does this for NASS/FAS; mirror it
  for the feeds).
- Barchart: `apikey` query parameter on every request (per published
  docs). DTN: auth method is **unknown until DTN answers** — Content
  Services speaks of "license keys" per package; IQFeed uses a
  login/password + product id over its socket protocol. Do not write
  DTN auth code until the product is identified.

### 3.2 Endpoints to use (Barchart; DTN pending §6 Q5)

| Need | Barchart endpoint | Notes |
|---|---|---|
| Cash bids by location | `getGrainBids` | Core Price Finder input. Confirm the request shape (by location? by radius/zip? by contributor?) from the docs once licensed — the public catalog names the endpoint but not its parameters. |
| Futures prices for basis | `getQuote` (futures symbols) / `getHistory` | Replaces/augments the delayed futures the basis tracker uses today. Confirm which symbols and which delay/real-time entitlement the licence covers. |
| Futures history / seasonal | `getHistory` (`type=daily`, `startDate`/`endDate`, `maxRecords`) | Backfill for price history and seasonal averages. Confirm the lookback limit — one Barchart endpoint caps `fileDate` at 30 days; confirm whether that applies to grain endpoints. |
| USDA cross-check | `getUSDAGrainPrices`, `getCmdtyStats` | Optional; the Research silo already ingests USDA directly for free, so only use these if they add coverage the free collectors lack. |
| ICE canola | Ask | The super plan notes ICE Canola is the hard future (only Barchart, TradingView, Yahoo partial, e-ADM carry it free). Confirm whether the licence includes ICE canola futures, and at what delay. |

### 3.3 Response mapping — see §4.

### 3.4 Rate limits, caching, and failure behaviour

- No public Barchart/DTN rate-limit numbers were found, so the design
  assumes the worst and asks (§6 Q3): per-key request quota, per-minute
  caps, and whether `getGrainBids` is billed per call, per location,
  or per row.
- Until the contract states limits, the collector must:
  - Call only on the ingestion cadence (twice daily today), never per
    web request. The web app reads stored `NormalizedPrice` rows only.
  - Cache aggressively: one feed call per (vendor, location set) per
    ingestion run; never re-fetch inside a single run.
  - Honour HTTP 429 with backoff and record the run as failed-with-
    retry, exactly as `app/services/research.py` does
    (`ResearchUpstreamError` on 429). Never retry in a tight loop.
  - Send a contact User-Agent, as the existing collectors do.
  - On auth failure (401/403) or an expired key, mark the source
    `broken` with the vendor's error message, and surface it on the
    source-health dashboard — do not silently fall back and pretend
    the feed is live. Fallback (§5) is about data coverage, not about
    hiding a broken feed.
  - Respect `robots.txt` where it applies (it does not apply to an
    authenticated API, but the principle stands: only call what the
    licence covers).

## 4. Mapping to `normalized_prices`

The target row is the existing `NormalizedPrice` model
(`app/models/normalized_price.py`): `source_name`, `location`,
`location_id`, `company_id`, `commodity_name`, `delivery_label`,
`delivery_end`, `futures_month`, `futures_price`, `basis`,
`cash_price_bu`, `cash_price_mt`, plus the snapshot's `captured_at`.
Currency is not stored on normalised rows today (see the basis
tracker note); if the feed returns an explicit currency, store it on
the raw snapshot and record the currency on the row only if/when the
model gains a currency column — never assume CAD or USD.

| Feed field (to confirm per vendor) | Normalised field | Rule |
|---|---|---|
| Bid / cash price | `cash_price_bu` (and `cash_price_mt` if the feed gives $/t) | Convert only with the documented unit; if the feed's unit is ambiguous, reject the row with a named reason rather than guessing |
| Basis | `basis` (cross-check) | Recompute basis as cash − futures from stored prices, as the basis tracker already does; keep the feed's basis only as the stored cross-check value |
| Futures price + month | `futures_price`, `futures_month` | From `getQuote`/`getHistory` for the matching contract month; never pair a cash bid with a futures price from a different month |
| Delivery / contract month | `delivery_label`, `delivery_end` | Map through the existing delivery-month canonicalisation (`_canonical_month_label`); unparseable labels are stored verbatim and flagged, not coerced |
| Location / facility | `location`, `location_id` | Map the feed's facility identifier to canonical `Location` rows via the existing canonical resolver; an unmapped facility is stored with `location_id = null` and counted, never silently merged into another location |
| Company / contributor | `company_id`, `source_name` | `source_name` is the vendor + feed (e.g. `barchart/getGrainBids`); the contributor maps to a canonical `Company` the same way scraped sources do |
| Quote timestamp | snapshot `captured_at` | The feed's quote time, not the fetch time. If the feed gives no per-quote time, use the run time and record `delay_label` honestly |
| Delay / entitlement | `delay_label` on the snapshot | Real-time vs delayed, exactly as licensed. A delayed feed must be labelled delayed everywhere it is shown, including the public best-bid page |

**Dedupe:** the existing composite key
(location | commodity | delivery month | futures month) applies
unchanged. A feed row that duplicates a scraped row for the same
location/commodity/month must not create a second price — see §5 for
precedence.

**Unknowns to confirm from vendor docs once licensed:** the exact
`getGrainBids` request parameters and response field names; whether
bids are per facility or per contributor roll-up; whether basis is
supplied or must be computed; which units each commodity is quoted in;
and whether Canadian facilities are included at all.

## 5. Fallback to free sources

The licensed feed must never become a single point of failure, and
must never be the only copy of a price.

- **Free sources keep running.** Ontario scrapers, Outlook email bids
  (OCR), and USDA collectors stay enabled. The feed is additive: it
  extends coverage (US Corn Belt, Gulf/PNW export context via USDA
  mirrors) rather than replacing the seed panel.
- **Precedence when both exist.** If the feed and a scraper both
  produce a row for the same location/commodity/month, keep both rows
  (they are different sources with different `source_name`s) and let
  the existing top-N / best-bid logic rank them — do not silently
  overwrite the scraped row, and do not silently prefer the feed.
  Record the overlap in ingestion diagnostics so Adam can see where
  the feed duplicates free coverage and where it adds new coverage.
- **Feed down / key expired / quota exhausted.** Ingestion continues
  with free sources; the feed's source-health row goes `broken` or
  `stale` with the real reason; the basis tracker and best-bid page
  show the free data with their normal staleness labels. No price is
  ever invented to fill a feed gap, and no stale feed price is ever
  presented as current.
- **Licence ends / not renewed.** Disable the feed in config; the
  platform continues on free sources. Stored historical feed rows stay
  in the database (they were lawfully obtained while licensed) but
  must not be republished beyond what the licence allows after
  termination — confirm the post-termination rule in the contract
  (§6 Q2) before relying on this.

## 6. Cost questions for Adam (to ask the vendors — not answered here)

Ask these through Adam's contacts, not by cold outreach from the
repo. No pricing is quoted in this document because none is published.

1. **Coverage:** Does Barchart `getGrainBids` include Canadian
   facilities (Ontario specifically), or is it US-only? Does DTN's
   feed include Canadian elevators? What is the facility count by
   state/province, and how are new facilities added?
2. **Redistribution licence:** What licence covers showing cash bids
   to GrainHub end users on the public best-bid page and in the Price
   Finder (republication), as opposed to internal use only? What are
   its terms, attribution requirements, and post-termination rules for
   already-stored rows? This decides whether the Price Finder can use
   the feed at all.
3. **Pricing model:** How is the feed priced — flat monthly, per API
   call, per location/facility, per row, or per end user? What is
   included at the entry tier, and what counts as overage? Is there a
   trial/sandbox key for integration testing?
4. **Rate limits and quotas:** Per-key request limits, per-minute caps,
   `getGrainBids` billing unit, `getHistory` lookback limits, and
   whether bulk/by-region calls are available instead of one call per
   facility.
5. **DTN product identification:** Which DTN product carries licensed,
   redistributable per-elevator cash bids for a third-party web app —
   Content Services Markets API, a DTN Portal feed, or another
   product? What are its auth, format (REST? widgets only?), and
   redistribution terms? Is there a developer/sandbox environment?
6. **Futures and canola:** Which futures are included, at what delay
   (real-time vs 10–15 min delayed), and is ICE canola included? What
   is the surcharge, if any, for real-time vs delayed?
7. **Data semantics:** Exact `getGrainBids` parameters and response
   fields; per-facility vs contributor roll-up; whether basis is
   supplied; units per commodity; per-quote timestamps; and how
   corrections/revisions are signalled (do bids change after first
   transmission?).
8. **Support and SLA:** Who is the integration contact, what is the
   support channel for a broken feed, and is there an uptime/SLA
   commitment? What happens to the key if the account lapses?

## 7. Decision log (for Adam)

- **Barchart vs DTN vs both:** Not decided here. Barchart has the
  clearer developer surface (documented REST catalog, named
  `getGrainBids` endpoint, cash bids listed as realtime US). DTN has
  the deeper elevator footprint (Portal/CashBidTable widgets are
  already the source of many scraped pages) but no public self-serve
  cash-bid API was found — its route needs a vendor conversation
  first. If only one can be pursued first, Barchart is the more
  concrete integration; DTN is the more important coverage question.
- **Do not build either client until:** (a) the redistribution
  question (Q2) is answered in writing, and (b) a trial/sandbox key
  exists. Writing a client against guessed endpoints wastes the
  integration effort if the licence does not cover the Price Finder.
- **The Greenfield/Barchart-page collector** (Cycle 1, item 5) is a
  separate decision from the feed and stays as-is until Adam rules
  on it.
- **Parked 2026-11-19 (Cycle 40, Adam's request).** Barchart/DTN is
  not a blocker for the current build and is not on the needs-Adam
  list. The `andersons` adapter (legacy DTN host) is toggled off
  and its probe-list entry removed; the 13 DTN-family widget
  adapters were already toggled off (Cycle 20). When/if Adam
  re-opens it, follow the §8 checklist — no design rework is
  needed first.

## 8. Feed plug-in checklist — adding a licensed feed later

Proven in code by `tests/test_licensed_feed_plugin.py` (Cycle 40):
a synthetic adapter registered through the registry, seeded
through the toggles, and surfaced by market search and the public
best-bid page with **no route changes**. A real licensed feed
follows the same steps — config + one adapter, nothing else.

**Preconditions (do not start until both are true):**

1. The redistribution question (§6 Q2) is answered **in writing**:
   the licence covers showing cash bids to GrainHub end users
   (republication), not just internal use. A plain OnDemand key
   does not cover the Price Finder.
2. A trial/sandbox key exists, stored in env only
   (`BARCHART_API_KEY`, `DTN_API_KEY` or the DTN-product-specific
   name) — never in code, config, logs, or git. Key presence is
   reported only as a boolean, mirroring `/api/research/status`
   for NASS/FAS.

**Plug-in steps (in order):**

3. Write the thin client (`app/services/barchart_client.py` and/or
   `app/services/dtn_client.py`, §2): `get_grain_bids()`,
   `get_quote()`, `get_history()`. Key from env only. Raise a
   `FeedKeyRequired`-style error when unconfigured, mirroring
   `ResearchKeyRequired` — the collector must refuse to call the
   API without a key, and the ingestion run must record that
   honestly instead of failing silently.
4. Write the collector (`app/services/licensed_feed_collector.py`,
   §2): one collector per vendor implementing the existing
   collector interface — a zero-arg `fetch_<vendor>()` returning
   a DataFrame (or the `{"rows": [...]}` dict the `direct_dict`
   mode converts), mapped to `NormalizedPrice` rows per §4.
   Record the raw payload, run status, parse success rate, and
   errors into `ingestion_runs` like every other collector.
   Honour HTTP 429 with backoff; on 401/403 mark the source
   `broken` with the vendor's error — never silently fall back
   and pretend the feed is live.
5. Register **one adapter** in `app/services/source_registry.py`:
   `SourceAdapter("<vendor>", "<module>", "fetch_<vendor>",
   "direct", "api", <poll_minutes>, <timeout_seconds>)` — the
   same shape as the `andersons` entry (mode `direct`,
   source_class `api`). No other registry change is needed.
6. Add the toggle in `config.toml` `[sources]` (`<vendor> =
   false` until the key exists, then `true`). Only an explicit
   `false` disables; a missing toggle defaults to enabled, so
   add the entry explicitly. Seeding (`seed_sources_from_registry`)
   and scheduled polling (`list_due_sources`) both honour it —
   no seeding or poller change is needed.
7. Add the `licensed_feeds` config section (§2, env-gated,
   disabled by default) listing which vendors are enabled and
   which endpoints are in scope. No key in config files —
   `.env.example` only.
8. Verify the seed: `POST /api/sources/seed?scope=all` (or the
   equivalent seed call) creates the `Source` row for the new
   key, and a toggled-off key is reported in `skipped_disabled`.
9. Verify the flow end to end on a test org: run one ingestion
   for the new source and confirm rows land in `normalized_prices`
   with `source_name` `<vendor>/<endpoint>` (e.g.
   `barchart/getGrainBids`), the feed's quote time as
   `captured_at`, and `delay_label` honest (real-time vs
   delayed). Confirm the overlap rule (§5): a feed row that
   duplicates a scraped row for the same location/commodity/month
   is kept as a second row under its own `source_name` — never
   silently overwriting the scraped row.
10. Verify **no route changes were needed**: market search, the
    public best-bid page, the basis tracker, the newsletter, and
    the market report all read `NormalizedPrice` rows generically
    (market search / newsletter / market report via
    `_load_preview_payload(..., source_name=None, ...)`; best-bids
    and basis via direct `NormalizedPrice` selects with no
    source-name allowlist; advisor signals take a duck-typed
    price row). Confirm the new rows surface in each with the
    feed's `source_name` shown, and that the source-health
    dashboard shows the feed (`live`, or `broken` with the real
    reason on auth/quota failure).
11. Confirm fallback (§5): free sources keep running; feed down /
    key expired / quota exhausted leaves the feed's health row
    `broken`/`stale` with the real reason while the basis tracker
    and best-bid page keep showing free data with their normal
    staleness labels. No price is ever invented to fill a feed gap.

**What stays disabled until a licence/key exists:** the adapter
toggle (`false`), the `licensed_feeds` config section, and any
futures/canola desk wiring that depends on the feed. The futures
strip keeps returning contract structure with prices `null` and
the ICE canola desk stays labelled `not_wired` — that is the
honest state, not a gap to work around.

## Sources (public, checked 2026-11-19)

- Barchart OnDemand API catalog / docs — `ondemand.websol.barchart.com`;
  Barchart agriculture data table (Cash Grain Bids, realtime, US) —
  barchart.com/cmdty/solutions/agribusiness.
- Third-party reviews of Barchart OnDemand (pricing model, retired
  free API, stale Python client, redistribution restriction) —
  aistocktradingbots.com/blog/barchart-api/;
  stockmarketstack.com/tools/barchart-ondemand.
- DTN Content Services getting started — cp-docs.dtn.com
  (REST Web Services + Composable Widgets; keys from account rep).
- DTN IQFeed API docs and 2019 FAQ — iqhelp.dtn.com/api/;
  dtn.com (IQFeed developer licence, socket protocol 6.2).
- DTN Ag Marketplace / DTN Portal — dtn.com/agriculture/producer/
  ag-marketplace/.

**Design only — no vendor contacted, no keys, no pricing quoted.**
