# Overnight Cycle 1 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-1` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** core Cycle 1 done; US price-source discovery still running when this draft was written — see §6.

**Never merged to master. No spending, no vendor contact, no secrets, no deployment changes.**

## 1. Commits

| Commit | What |
|---|---|
| `02fe1f2` | Phase 0: restore missing `is_benchmark_location_label`; fix company-identity lookup to try raw source alias as well as canonical name |
| `c540852` | Sprint 01: `/api/market-search` (commodity, location, radius_km haversine, delivery_month, grouped by month, top-N) with tests |
| `f10d74b` | Advisor v1, Elevator Ops v1, Research v1, market-search wiring |
| `8cb6a40` | Price-source catalogue (Ontario), probe smoke test, research expansion pages, fix unmounted uploads router |

## 2. Test results

- **Full suite: 179 passed, 0 failed, 2 warnings** (pre-existing Starlette deprecation warnings).
  - Baseline before Cycle 1: 109 passed (after Phase 0 fixes; 1 import error fixed in Phase 0).
  - New tests: market search 8, advisor 29, elevator ops 21, research 8, price-source probe 4.
- One transient failure seen once mid-cycle (`test_ask_returns_501_even_with_llm_key_set`): a child subagent was still writing test files during that run. It passed in isolation and in every full run since (three consecutive full green runs).
- Smoke test (uvicorn, no DB in this environment): `/health/live` 200, `/docs` 200, `/health/ready` correctly 503 (`DATABASE_URL is not set`). All DB-backed endpoints return 500 in this environment because `get_request_context` depends on `get_db` — expected without a database, not a code bug. Route-level behaviour is covered by TestClient tests with fake sessions.
- Web: `apps/web/node_modules` is not installed, so `tsc --noEmit` / `next build` could not be run. New pages follow the existing page patterns exactly but are **unverified by the TypeScript compiler** — run `npm install && npm run build` before trusting them.

## 3. What was built (done)

### Core Cycle 1
- **Phase 0 hardening:** restored `is_benchmark_location_label`; fixed `_desired_company_id_for_row` alias lookup. Baseline 109 passed.
- **Market search** (`GET /api/market-search`): commodity, location, lat/lng + `radius_km` (haversine, 6371.0088 km), `delivery_month` (parses `YYYY-MM`, `Month YYYY`, `Month`), grouped by delivery month, top-N (default 30, max 30). 400 when a radius has no resolvable origin; rows without coordinates are excluded and counted as `excluded_unknown_distance`.
- **Research silo v1:** `ResearchReport` model + migration `0018`; NASS Quick Stats + FAS PSD collectors (key-gated — raise a clear "key required" error with no key, never call the API); WASDE / Crop Progress public-file ingestion with parsers that only return values actually in the file; routes `/api/research/status|reports|wasde|crop-progress|nass|ingest-file`; web pages `/research`, `/research/wasde`, `/research/crop-progress` (+ `/research/grain-stocks`, `/research/export-sales`, `/research/commitments-of-traders` — see scaffold below); "Research" added to top nav.
- **Newsletter:** market-report preview appends a USDA research section when research rows exist (`append_research_section`); delivery stays OFF by default (dry-run default, `MARKET_REPORT_EMAIL_ENABLED=false`, dedup by subscriber + issue_key). `compile_market_report` signature unchanged — bids-only path still works.
- **Audit fix:** the uploads router was implemented but never mounted in `app/main.py` — every `/api/uploads` call 404'd. Now mounted. (Found by the read-only API audit.)

### Advisor silo v1 (GrainFox-like)
- Farm profile model + migration `0016` (risk tolerance is a column on the profile, not a separate table), breakeven calculator, sell-now-vs-hold scenario math, sell/hold signal from the latest **real** canonical cash price (`insufficient_data` with named reasons when data is missing — never an invented price), routes `/api/advisor/farm-profiles|breakeven|scenarios|signal|ask`, wired into `app/main.py`.
- `/ask` is a scaffold: always 501, never calls a paid API. Without a key it says the key is not configured; with a key it says the provider is not wired up in Cycle 1.

### Elevator Ops silo v1 (Bushel-like)
- Contract / scale-ticket / CRM-note models + migration `0017`, routes `/api/elevator-ops/contracts|scale-tickets|crm-notes|esign|module`, wired into `app/main.py`; white-label grower portal page `/portal` (placeholder branding, empty states, no invented data).
- eSign is a stub: records `pending_signature` + timestamp, calls no provider, sends nothing. No payments, settlements, invoicing, or ERP sync.

### Price-source discovery (Ontario — done)
- `docs/plans/price-source-catalogue.md`: 20 Ontario URLs probed (one polite probe each).
  - Existing panel: **11 live, 2 dead** (LAC old domain `dtn.londonag.com` → 404; Bunge Hamilton → 404, config already disables it).
  - New candidates: **7 found** — North Gower Grains fully verified (daily blog-post bid table, Adam's own elevator, top priority); LAC replacement domain `londonag-dtn.com` verified live with "Cash Bid" content; Collwest, Mae-Mart Farms, Mapleview Grain verified by direct fetch; Charwen Farms and Addis Grain partially verified (homepage live, bids page not yet fetched).
  - Ruled out (app-only, no public web bids): P&H, Richardson Pioneer, ADM. Thompsons = Andersons (already covered).
- `app/services/price_source_probe.py`: polite single-probe smoke test (one GET per source, contact UA, 2 s pause, records reachability + bid-content presence only — **no prices recorded**), with tests for the classifier (live probes are CLI-only, not in pytest).
- **Not done:** collector code for the 4 newly verified sources (North Gower Grains, Collwest, Mae-Mart, Mapleview) is not written yet — next step. `lac_source.py` base URL still points at the dead domain and needs updating to `londonag-dtn.com` + re-verification.

## 4. What is scaffold / stub (honest list)

- Advisor `/ask`: 501 scaffold, no LLM provider wired, no key anywhere.
- Elevator Ops eSign: `pending_signature` stub, no provider. Portal: placeholder branding, no grower login, no signing UI. No ERP sync, no payments.
- Research: Grain Stocks / Export Sales / Commitments of Traders pages exist but their **value parsers are not built** — ingest accepts the file and records source/vintage, values stay empty until a parser exists. WASDE and Crop Progress parsers only handle the text formats they were written for; a format change returns nothing rather than guessing.
- Market-report research section only appears when research rows exist; with no ingestion yet, the preview is bids-only as before.
- Signals endpoints read `SignalForecast` but nothing in the API writes forecasts (pre-existing gap, found by audit).

## 5. Blocked / needs Adam (decisions for the morning)

1. **NASS API key** — free, by email at quickstats.nass.usda.gov/api. Set `NASS_API_KEY` in env. Without it, NASS collectors report "key required".
2. **FAS PSD / data.gov key** — free at api.data.gov/signup. Set `FAS_DATA_GOV_API_KEY` in env.
3. **LLM provider + key for Advisor `/ask`** — pick a provider (OpenAI, Anthropic, other), supply `GRAINHUB_LLM_API_KEY`, decide cost/usage limits. Nothing will spend without this.
4. **Barchart / DTN licensed feed** — Adam knows people at both. The free layer cannot give daily county-by-county elevator cash bids; that dataset only comes from a licensed feed or direct buyer integration. No contact was made overnight (guardrail).
5. **Greenfield Global / Barchart marketplace** — the existing Playwright collector reads a Barchart-hosted page. Confirm whether that is acceptable or should be dropped (guardrail: no Barchart scraping).
6. **ERP choice for Elevator Ops** — no ERP (Agris / Agvance / AgTrax) is referenced anywhere in the repo. Adam to decide which is first.
7. **eSign provider** — DocuSign / Adobe Sign / other, before any real signing flow.
8. **LAC base URL fix + new-source collectors** — approve updating `lac_source.py` to `londonag-dtn.com` and writing collectors for North Gower Grains, Collwest, Mae-Mart, Mapleview (Charwen only if its feed is independent of LAC).
9. **Pricing / hosting decisions** — not started; nothing deployed.

## 6. US price-source discovery

**Still running when this draft was written** (worker `63dba572`). US section of `docs/plans/price-source-catalogue.md` is a placeholder to be merged when it returns: verification of `config.toml` / `us_elevators_urls.toml` (AgriCharts writeBidRow + DTN CashBidTable pages), Corn Belt + Gulf/PNW expansion, live/dead/redirect/blocked counts.

## 7. Guardrails — compliance

No money spent. No vendor contacted. No emails/messages sent. No paywalled or licensed data scraped (Farmbucks / GrainFox / Barchart pages were never used as data sources; Greenfield was HEAD-only). No secrets in git (keys are env-only config). No merge to master, no force-push, nothing deleted. No price, WASDE number, or bid invented anywhere — empty states say so explicitly.
