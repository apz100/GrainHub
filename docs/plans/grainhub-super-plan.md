# GrainHub — Super Plan

Owner: Adam (apz100) · Repo: https://github.com/apz100/GrainHub
Written: 2026-11-18 · Status: active plan for the whole platform, not just one silo.

## 1. Vision

One shared grain-markets platform for all levels — farmers, grain elevators /
merchandisers, processors, and exporters — across the US and Canada.

It is four products on one backend:

1. **Price Finder** (Farmbucks-like) — find the best local cash bid.
2. **Research** (GrainStats-like) — USDA and official reports, made simple.
3. **Advisor** (GrainFox-like) — personalised sell / hold help, with AI.
4. **Elevator Ops** (Bushel / Grain Discovery-like) — grower portal, contracts,
   scale tickets, payments, ERP integration.

Plus a daily newsletter / report feed that runs off the same data.

Adam works in merchandising at a grain elevator in North Gower, Ontario,
lives in Russell, Ontario, has an IT / programming background, and already
knows people at Barchart and DTN for a licensed feed. His existing Python
scrapers are the starting point, not the foundation for North America.

## 2. Where we start (2026-11-18, verified from the code)

Unified repo `GrainHub` = `GrainBids` + `CashGrainBids`, 945 tracked files,
pushed to https://github.com/apz100/GrainHub (public, master branch).

### GrainBids — the active platform

- `apps/web`: Next.js 14 + TypeScript + Tailwind
- `apps/api`: FastAPI 0.111 + SQLAlchemy 2 + Alembic (15 migrations), Postgres
- Production baseline: Vercel + Render + Supabase
- Ingestion at 08:00 and 15:00 America/Toronto
- Routes: bids, normalized prices, sources, ingestion, market data,
  market report, newsletter, alerts, watchlists, saved searches, quotes,
  signals, settings, reference
- Working path: configured source file → ingestion run → normalization →
  `normalized_prices` → bids dashboard
- Ontario sources: AgriCharts, GLG, LAC, Andersons, Snobelen, Hensall,
  DG Global, Wanstead, Ganaraska (Bunge disabled — URLs no longer valid)
- US sources in config: AgriCharts `writeBidRow` pages (no browser) and
  DTN CashBidTable pages (Playwright)
- BasisBoard is the bids / market module inside GrainBids, not a separate product.

### CashGrainBids — the legacy pipeline

- Playwright web collectors, Outlook email bid parsing (OCR for image tables),
  Bank of Canada FX, basis normalisation, CSV / Excel / PDF daily reports
- North Gower pricing-decision layer: competitor benchmarks, USD-basis
  ceilings, recommended max CAD basis
- Reporting roadmap: Elevator Basis Market Position, Direct-Ship Buyer
  Comparison, Daily Market Movement, Opportunity Summary

### What is NOT built yet

- No USDA research collectors or dashboards (no WASDE / Crop Progress /
  Grain Stocks / Export Sales ingestion in the API)
- Market search by commodity + location + radius + delivery month is
  Sprint 01 work, not finished — canonical companies / locations are
  in progress
- Advisor: only a signals scaffold — no farm profile, risk profile,
  breakeven / scenario / cash-flow tools, no AI assistant
- Elevator Ops: no ERP integration, contracts, scale tickets, eSign,
  or payments
- No licensed Barchart / DTN feed wired in yet (contacts exist, no
  contract / key in the repo — never commit keys)

## 3. Architecture — one backend, four front doors

```
Collectors (per source, same interface)
  fetch -> normalise -> validate -> store raw + normalised
        |
Postgres (Supabase) — canonical companies, locations, commodities,
  normalised prices, futures, USDA reports, users, orgs,
  watchlists, saved searches, alerts, signals, newsletter subs
        |
FastAPI core API — one place for basis, CAD/USD, $/bu vs $/t,
  delivery-month grouping, top-N per month, alerts evaluation
        |
  +-- Next.js web: /bids, /sources, /alerts, /watchlists, /quotes,
  |   /signals, /dashboard, /settings, /upload
  +-- Research site: by report and by commodity (see §5)
  +-- Newsletter / market report job (weekly now, daily target)
  +-- AI advisor: reads the same API, never scrapes directly
```

Rules:

- Every price row carries: source, location, company (canonical),
  commodity, delivery month, futures month / price, basis, cash,
  currency, unit, quote date, fetched-at, delay label.
- Never invent a price, a WASDE number, or a bid. If a source is
  missing / stale, show that, with the source and date.
- Public-domain government data (USDA, StatCan, CGC) is free to reuse
  with attribution. Licensed data (Barchart / DTN) only via a licensed
  feed. Do not bulk-scrape Barchart / AgriCharts pages for republication,
  do not scrape Farmbucks / GrainFox paywalled data.
- Collectors run on the data's own cadence, cache aggressively,
  respect rate limits, honour 429 with backoff, send a contact
  User-Agent, respect robots.txt.
- Secrets only in env, never in git. `.env.example` only.
- One worktree / branch per task, narrow scope, reviewable diffs —
  see `GrainBids/grainbids/docs/operations/multi-agent-workflow.md`.

## 4. Data sources

### Free government APIs / downloads (the research backbone)

| Source | What it gives | Key / cost |
|---|---|---|
| USDA NASS Quick Stats | Acreage, yield, production, stocks, prices received — national / state / county, monthly / annual | Free key by email, 50,000 records/request |
| USDA AMS MARS / My Market News | Daily state grain bids + Gulf / Portland export bids, cash + basis, regional / terminal only | Free, eAuthentication key, 100,000 rows/request registered |
| USDA FAS PSD / Export Sales | World supply / demand by country, monthly; weekly export sales by destination | Free data.gov key, 1,000 req/hour |
| USDA WASDE / Crop Production / Grain Stocks / Crop Progress | Monthly / quarterly / weekly reports — **download, not an API** (ESMIS / usda.gov files) | Free, no key |
| Statistics Canada WDS | Canadian area / yield / production, table 32-10-0359-01 | Free, no key |
| Canadian Grain Commission Weekly | Weekly deliveries / exports / stocks, volumes only | Free, no key |
| Ontario (OMAFRA / GFO / Farm Market News) | Ontario weekly corn prices, daily commodity report, SellSmart | Free to read |

There is **no** free public API for daily county-by-county elevator
cash bids in the US or Canada. That dataset does not exist as a
government product.

### Futures (delayed, free to read)

CBOT corn / soybeans / wheat, KC HRW, MGEX HRS, oats — 10–15 min
delayed via CME / Barchart / TradingView. ICE Canola is the hard one:
only Barchart, TradingView, Yahoo (partial, high legal risk) and
e-ADM carry it free. Twelve Data free is CBOT-only, internal
non-display. Stooq scripted access is blocked — do not build on it.

### Local cash bids

- Adam's Ontario scrapers + Outlook email bids (OCR) — the seed panel.
- Public elevator pages (AgriCharts / DTN patterns) — permission-first,
  one collector per company, config-driven, no code change to add one.
- Licensed feed — Barchart OnDemand and/or DTN, via Adam's contacts.
  This is the Farmbucks-scale answer; budget it before public launch.
  Do not publish Yahoo / Twelve-free data to users.

## 5. The four silos

### Silo 1 — Price Finder (Farmbucks-like) — build first, after research

- Search: location + grain + radius + delivery month; grouped by
  delivery month, top 30 per month, sorted by price
- Free public best-bid page by company, as the traffic funnel
- Watchlists, saved searches (month-scoped), price alerts (email now,
  SMS next), best-bid history
- Buyer-branded listings, click-to-call, data-privacy pledge:
  searches / watchlists / alerts are never sold to buyers
- Elevators list bids via partnership / data integration, not by
  scraping a competitor
- Benchmark: Farmbucks $120 CAD/yr or $20 CAD/mo, 30-day trial,
  700+ buyers / 4,600+ locations

### Silo 2 — Research (GrainStats-like) — build first, simplest

This is the open gap: none of Farmbucks / GrainFox / Bushel /
Grain Discovery is primarily a research site.

- One page per official report, same pattern every time: plain-English
  description, one chart, one map where geography matters, one sortable
  table with week-on-week change and 5-year average, source + vintage
  on every number
- Two navigation axes: by report (WASDE, Crop Production, Grain Stocks,
  Prospective Plantings, Acreage, Crop Progress, Export Sales, Export
  Inspections, Grain Crushings, COT, Drought, Ethanol, River Levels,
  Panama Canal) and by commodity (corn, soybeans, wheat SRW/HRW/HRS,
  canola, barley, oats, rye, flax, sorghum)
- Geography: US vs world, state-by-state, export destinations,
  Gulf vs PNW
- Newsletter spine: WASDE day (~10th monthly, noon ET), Crop Progress
  Mondays 4pm ET, Export Sales Thursdays 8:30am ET
- Free delayed + ads, paid real-time + alerts + newsletter, ad-free
  (GrainStats benchmark: Alerts $50/mo, Pro $100/mo, no self-serve
  checkout — contact us)
- Canola Desk: ICE canola curve + crush / deliveries / exports —
  thinnest free data, needs a licensed feed first
- Methods & Sources trust page: every number labelled with source,
  delay, vintage, link; "confirm with your buyer" on all cash bids

### Silo 3 — Advisor (GrainFox-like)

- Farm Profile: crop mix, acres, storage, cash-flow goals
- Risk Profile: risk tolerance drives the plan, free as a lead magnet
- Smart Advisor: personalised sell / hold signals and a sales plan
  ("Sell 30% of CWRS on Mar 30" style), not generic advice
- Farm Wealth Toolkit: Scenario Planner, Cash Flow Planner,
  ROI Calculator, breakevens, sell-now-vs-hold graphs
- AI assistant (Sinoa-like): ask about markets, weather, crop
  conditions, trade news — backed by analyst expertise and real
  market signals, priced per question pack as well as by subscription
- Expert insights: FarmLink / DePutter-style analyst reports,
  StatsCan / USDA / WASDE summaries, daily podcasts / wires
- Benchmark: GrainFox Basic $0, Market Intelligence $1,500 CAD/yr,
  Smart $3,000 CAD/yr, Smart Plan+ per acre + human advisor,
  Sinoa $19.99 / 100 questions

### Silo 4 — Elevator Ops (Bushel / Grain Discovery-like) — last, heaviest

- White-label grower portal: each elevator's own brand, not GrainHub's
- Live bids, firm offers (delivered / FOB), timestamped acceptance
  (price locks on tap, paper trail — no slippage disputes)
- Grower portfolio: commodity balances, contracts, scale tickets,
  settlements, invoices, eSign, payments — ERP-connected
- Commercial Portal: truck sales, near-real-time scale tickets,
  grade-factor alerts, contract balances
- CRM: producer notes, buying opportunities, origination analytics
- Traceability / sustainability data collection, logistics
- Payments: settlements, AR/AP, invoicing, line of credit
- Benchmark: Bushel 3,500+ facilities, farmer plans $75–$599/yr,
  agribusiness pricing demo-only; Grain Discovery demo-only,
  15,000+ users

## 6. Phases

### Phase 0 — Harden the core (must finish first)

- Single active runtime: `apps/web` + `apps/api` only; legacy is reference
- Env guardrails, health checks (`/health/live`, `/health/ready`,
  `/api/health/db`), smoke test passes
- Ingestion quality: parse success, rejects, duplicates, missing fields
  per run; source health / freshness visible
- Canonical companies + locations, deterministic dedupe keys

### Phase 1 — Research site v1 + Price Finder core (Sprint 01)

- USDA collectors: NASS Quick Stats, AMS MARS, FAS PSD, WASDE /
  Crop Progress / Grain Stocks file ingestion
- Research dashboards by report and by commodity, with the
  GrainStats pattern (§5, Silo 2)
- Market search endpoint + `/bids` table-first UX, top-N per month
- Saved searches + alert trigger loop end-to-end for one pilot org
- Newsletter / market report: preview safe, delivery deduped by
  subscriber + week

### Phase 2 — Price Finder scale

- Barchart / DTN licensed feed (Adam's contacts) as the primary
  bid source; Ontario scrapers + email bids as the seed panel
- US Corn Belt + Gulf / PNW export coverage
- Alerts by SMS, watchlist sharing, best-bid history

### Phase 3 — Advisor

- Farm Profile, Risk Profile, Scenario / Cash Flow / ROI tools
- Sell / hold signals, AI assistant with question packs
- Tiered pricing: free basic → insights → advisor → human advisor

### Phase 4 — Elevator Ops

- White-label portal, digital contracting / eSign, scale tickets,
  payments, ERP integrations (Agris, Agvance, AgTrax, etc.)
- Commercial Portal, CRM, traceability

### Phase 5 — Monetise + launch

- Pricing per silo, free trials, per-acre advisor top tier
- Public launch, onboarding, support, terms / privacy,
  data-licence compliance review

## 7. Overnight autonomous cycle — Cycle 1 (2026-11-18 night)

Scope for tonight only. Do this, in this order, on branch
`overnight/grainhub-cycle-1`. Do NOT merge to master. Push the
branch to GitHub frequently.

1. Audit: run the existing API tests, record the baseline
   (pass / fail / skip), note broken / scaffold-only routes.
2. Phase 0 hardening: fix only what blocks the smoke test and
   ingestion diagnostics; no redesigns.
3. Sprint 01 P0: canonical companies / locations, deterministic
   dedupe, market-search endpoint (commodity, location, radius,
   delivery month, grouped by month, top-N), with tests.
4. Research silo v1: USDA collectors for NASS Quick Stats and
   FAS PSD (key-free paths first; key-gated paths as config +
   stub with clear "key required" behaviour), WASDE / Crop
   Progress / Grain Stocks file ingestion from public downloads,
   plus two research dashboard pages (WASDE + Crop Progress)
   in the web app, by report and by commodity, with source,
   delay and vintage on every number.
5. Newsletter: market-report preview works end-to-end with
   the new research data; delivery stays off by default.
6. Tests + docs: add / update tests for everything new,
   update this plan with what actually landed, and write
   `docs/plans/overnight-cycle-1-report.md` with: what was
   built, test results, branch + commits, what is still
   scaffold / stub, and what needs Adam (keys, Barchart/DTN
   pricing, decisions).

### Hard guardrails for the overnight cycle

- No spending money. No paid APIs, no paid subscriptions, no ads.
- No contacting Barchart, DTN, or any vendor. No emails or messages
  to anyone on Adam's behalf.
- No scraping paywalled / licensed data (Farmbucks, GrainFox,
  Barchart). Public government data and public elevator pages only,
  permission-first, polite rate limits.
- No secrets in git. No credentials in code, logs, or commits.
- No deleting data, repos, or branches. No force-push to master.
  No merging to master — branch only, for Adam to review.
- No public launch, no deployment changes, no DNS / domain changes.
- If a test, a source, or an API is broken, record it and move on —
  do not invent data to fill the gap, and do not fake a passing test.
- Stop and report if: a paid wall blocks the work, a source's
  terms forbid the use, or the build cannot be made green
  without a decision from Adam.

### Morning definition of done

- Branch `overnight/grainhub-cycle-1` pushed to apz100/GrainHub
- Tests run, results recorded, no silent failures
- Research v1 + market search actually work against real
  (public) data or clearly-labelled stubs
- Report file written, with the exact next decisions Adam
  needs to make

## 8. Open questions for Adam (not blockers for Cycle 1)

- Barchart / DTN: which feed, what pricing, what coverage?
- Hosting / domains: grainhub.com? Keep Vercel + Render + Supabase?
- Frontend: keep Next.js web first, or native mobile app next?
- Newsletter: daily from day one, or weekly market report first?
- Pricing: match Farmbucks / GrainFox benchmarks, or start free?
- Elevator Ops: which ERP first (Agris / Agvance / AgTrax)?
- US scope: Corn Belt first, or Corn Belt + Gulf / PNW from day one?
