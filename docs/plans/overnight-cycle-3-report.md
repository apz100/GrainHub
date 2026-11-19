# Overnight Cycle 3 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-3` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 3 complete — prototypes, research blockers, scaffold
gaps, polish, and Phase 2 prep design docs all done.

**Never merged to master or to cycle-1/2. No spending, no vendor
contact, no emails sent, no secrets, no deployment changes, no
paywalled/licensed data scraped. No price, WASDE number, basis, or
bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `c49710a` | Prototypes — mobile price finder, onboarding wizard, pricing page (build passes) |
| `541b49c` | Ontario collectors (Collwest, Mae-Mart, North Gower ordinary source, Mapleview stub), LAC URL fix, FMN location-filter verification (14 tests) |
| `8cc4427` | Polish wiring (source status on basis, ingestion status on calendar), history charts fixed, Barchart/DTN + ERP design docs (full suite 320 passed) |
| `90736c1` | Collwest confirmed Canadian, Bushel collector research, USDA mirrors verified, Grain Stocks / Export Sales / COT parsers (full suite 320 passed) |
| *(this commit)* | Cycle 3 report |

## 2. Test results

- **Full API suite: 320 passed, 0 failed** (Cycle 2 ended at 291).
  New tests in Cycle 3: Ontario collectors 10, LAC 4, polish 10,
  research 6 = **30 new tests** (one research test count overlaps
  a renamed Cycle 1 test; net +29).
- **Web build: PASS.** `npm run build` exit 0, `tsc --noEmit`
  clean, prototype routes built as static pages.

## 3. What was built (done)

### Prototypes (all under `app/prototypes/`, bannered "Prototype — not production")
- **Mobile price finder** (`/prototypes/price-finder`): phone-width
  search UI wired to real `/api/best-bids` and `/api/market-search`,
  results grouped by delivery month; synthetic rows only as
  clearly-labelled examples when the API is unreachable.
- **Onboarding wizard** (`/prototypes/onboarding`): 6 steps (farm
  location → crop mix/acres/yield/cost → storage → cash-flow target
  → risk tolerance → review), client-side, saves nothing; review
  step has a labelled preview POST to `/api/advisor/farm-profiles`.
  (A stale Cycle 1 docstring claimed the advisor router was
  unwired — verified: it **is** wired in `app/main.py`.)
- **Pricing page** (`/prototypes/pricing`): five draft tiers +
  bundle card, figures from the super-plan benchmarks, labelled
  "benchmark-based draft pricing, not final — final pricing is
  Adam's decision".

### Research blockers — all answered without Adam
- **Collwest Grain: CANADIAN, CAD.** Footer address 2924 Sixth
  Line, Collingwood, ON; canola/barley/oats per-tonne CAD, corn/soy/
  wheat per-bushel CAD. Catalogue updated; **not enabled in any US
  config.** (Its `.o.bushelsites.com` mirror has identical content;
  the www site is canonical.)
- **Bushel collector: single pattern looks feasible** (research
  only, no collector written yet). FAC's cash-bids page is
  **server-rendered static HTML** — no JS execution, API, or login
  needed. Correction to Cycle 1: bids are static, not JS-rendered.
  One parser must handle table-class, column-count, delivery-label,
  and currency variation (USD/bu vs CAD/bu vs CAD/t). Full write-up
  in `docs/plans/bushel-collector-research.md`.
- **USDA mirrors: fresh and stable-looking.** James Valley Grain
  and FS Grain both show the identical same-day report "USDA Cash
  Bid Report for Nov 18, 2026" (id 7730): 227-row static HTML
  table, 25 region sections incl. Gulf Coast Ports – LA and Pacific
  Ports. History via `?id=N` (sequential, archive back to Nov 05,
  2026). Catalogue updated.

### Scaffold gaps filled (no keys needed)
- **LAC base URL fixed** to `londonag-dtn.com`, re-verified live.
- **FMN location filter verified:** dropdown has 336 options, all
  numeric IDs (e.g. Winchester `2523`). `?location_filter=2523`
  returns 200 with Winchester selected — but filtered rows are
  JS-rendered (zero inline `writeBidRow` calls vs 454 on the
  default view). A Playwright render check is still needed to prove
  the rows load; that needs a live browser, which subagents cannot
  do. Findings in `docs/plans/fmn-location-filter.md`.
- **New Ontario collectors** (plain HTML, fixture-tested, registered
  in `source_registry.py` via a new `direct_dict` mode, config
  toggles added): Collwest (full parser), Mae-Mart (partial — cash
  prices JS-filled, rows carry `cash_price=None` with an explicit
  reason; rye parsed), North Gower Grains (full parser, ordinary
  source only), Mapleview (stub by design — bids live in a Next.js /
  Grain Discovery shell with no static bid content; needs a
  Playwright render or a public Grain Discovery feed).
- **Report value parsers** (all return only values present in the
  file): Grain Stocks (NASS quarterly txt, verified against the
  real Sep 30 2026 release — corn Sep 1 2026 total 2,095,057;
  soy 315,133), Export Sales (USDA AgTransport Socrata mirror, no
  key; latest week ending 2026-11-05; dataset has no TOTAL row),
  Commitments of Traders (CFTC Socrata JSON, no key, grain markets
  only). Wired into `POST /api/research/ingest-file`. `crop_production`
  still has no value parser (no verified public file format this
  cycle).

### Polish
- Basis rows now carry `source_status` from the same source-health
  logic as the dashboard (healthy/stale/broken/unknown).
- Calendar events carry `ingestion_status` from real
  `ResearchReport` rows; the calendar stays public with no DB
  (`unknown` instead of `not_ingested_yet`).
- `/history` page fixed (it previously called the history/seasonal
  endpoints with no `commodity`, so it could never render data) and
  given two SVG line charts from real API data, with empty states
  and no interpolation.

### Phase 2 prep — design docs only
- `docs/plans/barchart-dtn-integration-design.md`: Barchart
  OnDemand (`getGrainBids`/`getQuote`/`getHistory`, env-key auth);
  DTN has no single self-serve cash-bid API. **Key finding:
  Barchart docs expressly prohibit redistribution (internal use
  only)** — a separate redistribution licence decides whether the
  Price Finder can use the feed at all. The stale "$500/month
  from 2021" figure is flagged as not-a-quote.
- `docs/plans/erp-integration-design.md`: Agris (partner-only,
  no public API), Agvance (public cloud REST API since 2015 — the
  only public API of the three), AgTrax (partner API + ODBC read
  path). **Recommendation: Agvance first**, Agris second, AgTrax
  third. ERP is system of record; sync model documented.

## 4. North Gower Grains boundary — applied

Same boundary as Cycle 2: prices may be collected as one ordinary
source among many; no pilot, showcase, branding, affiliation, or
special treatment. Applied: the new collector uses the company name
only as a data-source identifier (like `lac`, `hensall`); zero
North Gower references in the new prototypes, pages, or design
docs; the catalogue lists it as an ordinary verified source.
Legacy/archive files untouched. No contact made.

## 5. What is still scaffold / stub

- Bushel collector: research done, collector not yet written
  (next cycle — the pattern is verified feasible).
- USDA-mirror collector: not yet written (pages verified fresh and
  stable; one fetch unlocks Gulf + Portland export bids).
- FMN filtered view: JS-rendered — needs a Playwright render check.
- Mapleview: stub only — needs Playwright or a Grain Discovery feed.
- `crop_production` value parser: no verified public file format.
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope — Adam to re-auth or add via web UI).
- Email-bid parser is a module only — no upload/ingest endpoint
  wired to it yet.

## 6. Blocked / needs Adam

Carried from Cycles 1–2: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (now with the
redistribution-licence finding), ERP choice (Agvance recommended),
eSign provider, pricing/hosting decisions, gh `workflow` scope for
the CI file, currency column / per-source currency mapping.
**New:** a Playwright render check of the FMN filtered view and of
Mapleview's Grain Discovery shell needs a live browser session.
