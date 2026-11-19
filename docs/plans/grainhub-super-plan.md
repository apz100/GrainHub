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
- pricing-decision layer: competitor benchmarks, USD-basis
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

## 9. Progress — Cycles 1–31 (2026-11-18/19)

Thirty-one overnight autonomous cycles on branches `overnight/grainhub-cycle-1`
through `overnight/grainhub-cycle-31`, none merged to master. Full API test
suite grew **179 → 291 → 320 → 359 → 364 → 380 → 407 → 407 → 454 → 488 → 536 → 558 → 590 → 617 → 629 → 638 → 643 → 646 → 656 → 692 → 692 → 696 → 697 → 702 → 704 → 709 → 709 → 709 → 709 → 710 → 710 passed, 0 failed**
across the thirty-one cycles. Full detail in `docs/plans/overnight-cycle-N-report.md`.
Merge order, gates, and conflicts are in `docs/plans/merge-plan.md`.

- **Cycle 1** (`overnight/grainhub-cycle-1`, 179 tests): Phase 0 hardening,
  `GET /api/market-search` (commodity + location + radius + delivery month,
  top-N by month), Research v1 (NASS/FAS key-gated collectors, WASDE/Crop
  Progress ingestion + pages), Advisor v1 (farm profile, breakeven,
  sell/hold signals; `/ask` 501), Elevator Ops v1 (contracts, scale
  tickets, CRM, eSign stub), and the price-source catalogue (Ontario 20
  URLs probed, US 58 probed + 20 new candidates, 6 added to config).
- **Cycle 2** (`overnight/grainhub-cycle-2`, 291 tests): basis tracker,
  source-health dashboard, daily newsletter generator (delivery off),
  futures strip + ICE canola desk (contract structure only, prices null),
  price history + 5-year seasonal averages, report calendar, email-bid
  OCR parsing module, and the public best-bid API + page. FMN cash page
  read in full: 204 bid tables, 86 delivery points, but the location
  dropdown lists 336 options — the default view is not the complete set.
- **Cycle 3** (`overnight/grainhub-cycle-3`, 320 tests): prototypes
  (mobile price finder, onboarding wizard, pricing page), new Ontario
  collectors (Collwest, Mae-Mart, Mapleview stub), LAC base-URL fix,
  FMN location-filter verification, Bushel collector research, USDA-mirror
  verification, Grain Stocks / Export Sales / COT value parsers, and
  design docs for Barchart/DTN and ERP integration.
- **Cycle 4** (`overnight/grainhub-cycle-4`, 359 tests): email-bid ingest
  endpoint (`POST /api/email-bids/parse`, parse-only), generic Bushel
  collector (FAC verified live, 45 rows; Collwest cross-check 16/16),
  USDA-mirror collector (both hosts, Gulf + Pacific Ports), and the
  Crop Production value parser wired into ingest-file.
- **Cycle 5** (`overnight/grainhub-cycle-5`, 364 tests): all 11 Bushel
  sites verified live and registered (plus FAC/Collwest from Cycle 4);
  United Coop same-org question resolved (two separate orgs — Beaver
  Dam, WI vs Webster City, IA); parser fixes for fractional futures,
  classless `<h2>` locations, and the Cash-Price header; `/today`
  morning-view page (build passes, 33 pages).
- **Cycle 6** (`overnight/grainhub-cycle-6`, 380 tests): DTN sweep of
  28 sites (2 static-HTML, 20 JS-only, 6 unreachable); Ace Ethanol +
  Alliance Grain verified Bushel and registered; deployment checklist
  (Vercel/Render/Supabase); basis-alert helpers (standalone, not yet
  wired). Also fixed a corrupted string literal in `bushel_source.py`
  that had briefly broken test collection (see the Cycle 6 report).
- **Cycle 7** (`overnight/grainhub-cycle-7`, 407 tests): AgriCharts
  `cashbids.php` embed collector (6 sites, 105 rows, via the static
  `cashbids-js.php` route — no Playwright needed); AGP iframe verified
  Bushel (Chester, NE) and registered; basis thresholds wired into the
  alert evaluator (migration `0019`, single Alembic head).
- **Cycle 8** (`overnight/grainhub-cycle-8`, 407 tests, docs only):
  merge plan for branches 1–7 (linear chain verified, `--no-ff` order,
  gates, conflicts, rollback); super-plan progress to Cycle 7;
  deployment-checklist migration head corrected 0018 → 0019; re-check
  sweep of all 5 Cycle 6 failures — all back up — including Five Star
  Coop's 299 static rows in a new wpDataTables pattern, and StoneX
  research (no static-data route exists; render check only).
- **Cycle 9** (`overnight/grainhub-cycle-9`, 454 tests): Five Star
  wpDataTables collector built (299 rows, 21 locations, delivery-label
  normalisation); ALCIVIA (181 rows) + TGM (362 rows) `cashbids-js.php`
  routes proven and registered (embed family now 8 sites); CRC
  resolved — homepage Cash Bids section is a lazy-loaded StoneX
  iframe, no collector.
- **Cycle 10** (`overnight/grainhub-cycle-10`, 488 tests): FMN
  writeBidRow collector (204 tables, 453 rows, 87 delivery points —
  the 87th is "US Rep Corn", missed by the earlier read; futures
  price/change/cash price still need the `jsquote.php` feed);
  19-site US sweep (13 reclassified, Sunrise enabled as classic DTN,
  Synergy registered as Bushel, Wheaton Grain parser gap found,
  StoneX family grows to 3 with UFC); currency design note (proposal
  only, no migration); web build re-verified passing.
- **Cycle 11** (`overnight/grainhub-cycle-11`, 536 tests): FMN
  jsquote feed fetched — all 449 futures-linked rows now filled
  (futures price/change/cash price via the page's own render rule);
  PRO Coop embed proven (9th embed site, Ayrshire only); Wheaton
  Grain tabbed-widget parser fix; 9 sub-page probes (Pro Ag 78 rows,
  Winchester 3439 10 rows, West-Con 84 rows but a regex gap, Hull +
  StateLine embeds, Andersons proprietary picker, Smithfield link
  list) — plus a coordinator correction: Skyland's
  `/cashbidssingle-` page DOES serve a static widget (6 rows), and
  was registered after the sweep worker wrongly reported none.
- **Cycle 12** (`overnight/grainhub-cycle-12`, 558 tests): West-Con
  regex fix (month-name delivery labels) unblocks West-Con (84/84)
  and Wheaton Dumont (43/43); Hull (12 rows), StateLine (126 rows)
  and PRO Coop's second 21302 embed (Manson, 12 rows) proven —
  embed family now 12 sites; per-location Bushel probes
  (Winchester 3440 is Georgetown, 5 Soybeans rows; Skyland 2730
  duplicates the default page; Smithfield Bentonville, 3 rows).
- **Cycle 13** (`overnight/grainhub-cycle-13`, 590 tests): PRO Coop
  second 21302 embed proven as a duplicate Manson view (12 rows,
  embed family now 13); 10 per-location Bushel probes (6 Skyland,
  4 Smithfield); Andersons GRAINweb research — browser-only
  verdict from the saved HTML (no static rows, no API strings);
  merge plan extended to Cycles 8–12 (43 commits, 0 merges);
  deployment-checklist sign-off line corrected 0018 → 0019.
- **Cycle 14** (`overnight/grainhub-cycle-14`, 617 tests): Skyland
  picker sweep finished — all 14 IDs verified (39 rows in the last
  7, first double-Milo page at Hugoton 3370); Smithfield batch
  1669–1674 (17 rows; the 1-row pages are the exception, most carry
  a full 3 rows); Andersons `my-cash-bids` bundle read (1,079
  bytes, zero network calls — browser-only confirmed); Chadbourn
  re-check still stale (Nov 18 header).
- **Cycle 15** (`overnight/grainhub-cycle-15`, 629 tests): Smithfield
  batches A + B (11 locations; Raeford serves an empty widget and
  is not registered; Chief Feed Mill's h2 is Rose Hill); Andersons
  locations-list probe — a pure directory of 41 facility links,
  0 tables, no bids — closed for static collection pending two
  confirmatory checks; super-plan §9 extended to Cycle 14.
- **Cycle 16** (`overnight/grainhub-cycle-16`, 638 tests): Smithfield
  East Region sweep finished — 30 of 31 locations verified
  (Waverly fattest at 7 rows, first Grain Sorghum page; Lapaz +
  Hamer close the list; Raeford re-probe still empty, treated as
  posting no public bids); Andersons fully closed — Maumee facility
  page DOES carry 3 static bid tables but they are
  Barchart-licensed, so not collected; merge plan extended to
  Cycles 13–15 (49 commits, 0 merges).
- **Cycle 17** (`overnight/grainhub-cycle-17`, 643 tests): source
  audit — 15 verified sources enabled in the toml that stale Cycle
  1 notes had left disabled (10 Cycle 4/5 Bushel sites, Ace,
  Alliance, AGP, both USDA mirrors); CRC reclassified to stonex;
  basis-tracker source-health wiring verified already real; price
  history now carries source/as_of labels; report calendar already
  wired to ingestion status; `config.toml` `[us]` drift found (30
  vs 121 entries).
- **Cycle 18** (`overnight/grainhub-cycle-18`, 646 tests): `config.toml`
  `[us]` synced from the urls toml (121 entries, guard test, sync
  script); Mae-Mart futures proxy identified (`grain-proxy.php`,
  Yahoo-style `=F` symbols, futures only); CGB cash-bid page found
  (AgriCharts embed — licensed, not fetched); unreachable trio
  (CVA, Landus, Mercer) still blocked on re-check.
- **Cycle 19** (`overnight/grainhub-cycle-19`, 656 tests): Mae-Mart
  proxy probed live (200, JSON, contract matches) and the collector
  now fills `futures_price` (cash NOT computed — open decision);
  ingestion audit found the scheduled poller only reached 5 pilot
  adapters — pilot-allowlist removed, all 93 adapters reachable;
  documented gaps: deployed cron runs the file job not the poller,
  US agricharts/DTN entries have no registry adapter, toggled-off
  bunge/mapleview still seedable; merge plan extended to Cycles
  16–18 (55 commits, 0 merges).
- **Cycle 20** (`overnight/grainhub-cycle-20`, 692 tests): 26 URL-bound
  registry adapters built and wired for the enabled US agricharts
  (13, all static-capable) + DTN (13, all JS-only, toggles off)
  entries — registry now 119 adapters; seeding + poller now honour
  `[sources]` toggles (seed scope=all creates 104 rows, 15 skipped);
  poller scheduling documented in the deployment checklist
  (`python -m app.jobs.poll_sources`); merge plan extended to Cycle
  19 (57 commits, 0 merges).
- **Cycle 21** (`overnight/grainhub-cycle-21`, 692 tests, docs only):
  11 of 13 agricharts wrappers verified live (642 rows); Heartland
  + Mulvane return 0 rows site-side (page no longer carries the
  `jsquote.php` tag — possible AgriCharts template change);
  Heritage Grain returns 3 rows with locations mislabelled as
  commodities (h4-as-commodity pages); agricharts collector sends
  a Chrome UA, not GrainHub-Research/1.0 (pre-existing, kept);
  merge plan extended to Cycle 20 (59 commits, 0 merges).
- **Cycle 22** (`overnight/grainhub-cycle-22`, 696 tests): Heritage
  parser fix — escaped quotes in writeBidRow notes now handled
  (14/14 rows vs 3/14) plus h4-as-commodity fallback; Heartland +
  Mulvane still 0 rows on re-probe (2nd consecutive failure each);
  staleness watch unchanged (all four still exactly one day
  behind); merge plan extended to Cycle 21 (61 commits, 0 merges).
- **Cycle 23** (`overnight/grainhub-cycle-23`, 697 tests): Heritage
  parser fix confirmed live — 14 rows (CORN 6, BEANS 6, WHEAT 2),
  company fallback location; Heartland + Mulvane toggles flipped to
  `false` (two consecutive 0-row probes each; seed count 104 → 102);
  AgriCharts futures-fallback design note written (key finding:
  basis is in the `writeBidRow` row itself, not the feed;
  recommends parsing rows with futures/cash `None`, FMN precedent);
  agricharts Chrome UA kept (coordinator decision); merge plan
  extended to Cycle 22 (63 commits, 0 merges).
- **Cycle 24** (`overnight/grainhub-cycle-24`, 702 tests): AgriCharts
  fallback (a) implemented — no-tag pages now parse basis-only
  rows (futures/cash `None` with note, month decoded from symbol),
  5 new tests; live check Heartland/Mulvane still 0 rows (rows no
  longer in static HTML, so (a) recovers neither site); option (b)
  probe fails on Heartland (feed returns `var quotes = null;`) and
  corrects Cycles 21–23 (tag present with empty symbols, not
  missing); staleness daytime re-check — none of the four refreshed
  (Chadbourn 4th consecutive stale probe); merge plan extended to
  Cycle 23 (65 commits, 0 merges).
- **Cycle 25** (`overnight/grainhub-cycle-25`, 704 tests): Heartland
  filtered view (`location_filter=22143`) still 0 rows — hypothesis
  closed; Mulvane re-checked 0 rows (tag present, empty symbols —
  correction extended); feed-down degradation implemented (empty
  feed → basis-only rows), 2 new tests; Heartland/Mulvane closed
  for now; merge plan extended to Cycle 24 (67 commits, 0 merges).
- **Cycle 26** (`overnight/grainhub-cycle-26`, 709 tests): feed-error
  degradation implemented (feed fetch raising → basis-only rows;
  page fetch raising still empty), 5 new tests — all three
  degradation paths now behave the same way, design-note work
  complete; live re-verification sweep of five key collectors, all
  exact matches (FMN 453, Five Star 299, TGM 362, USDA mirror 197,
  FAC 45); merge plan extended to Cycle 25 (69 commits, 0 merges).
- **Cycle 27** (`overnight/grainhub-cycle-27`, 709 tests, docs only):
  all 10 working US AgriCharts wrappers re-verified live, all exact
  matches to Cycle 21 (639 rows, 0 zero-row results); every
  live-verified collector has now been re-checked this morning with
  zero drift; merge plan extended to Cycle 26 (71 commits, 0 merges).
- **Cycle 28** (`overnight/grainhub-cycle-28`, 709 tests, docs only):
  full 13-site AgriCharts-embed family re-verified live, all exact
  matches (816 rows); FS Grain USDA mirror confirmed (197 rows,
  report id 7730); merge plan extended to Cycle 27 (73 commits, 0
  merges).
- **Cycle 29** (`overnight/grainhub-cycle-29`, 709 tests, docs only):
  Bushel per-location sample re-verified 6/6 exact matches (Hugoton
  still Nov 18, one day stale); Mae-Mart still viable as-is (page
  byte-identical to Cycle 18, proxy shape identical to Cycle 19;
  proxy now 301s to extensionless `/grain-proxy`); merge plan
  extended to Cycle 28 (75 commits, 0 merges).
- **Cycle 30** (`overnight/grainhub-cycle-30`, 710 tests): Bushel
  sample #2 re-verified 6/6 exact matches (Hamer still Nov 18, one
  day stale); Mae-Mart proxy URL stored extensionless (1 new test);
  merge plan extended to Cycle 29 (77 commits, 0 merges).
- **Cycle 31** (`overnight/grainhub-cycle-31`, 710 tests, docs only):
  Bushel samples #3 + Cycle 4/5 sites re-verified 12/12 exact
  matches; Almota joins the staleness watch (first stale probe —
  watch list now five widgets); merge plan extended to Cycle 30
  (79 commits, 0 merges).
- **Cycle 32** (`overnight/grainhub-cycle-32`, 710 tests, docs only):
  Bushel samples #4 + Cycle 11/5 sites re-verified 12/12 exact
  matches (all headers fresh; Wheaton Grain has no capturable
  header date); merge plan extended to Cycle 31 (81 commits, 0 merges).
- **Cycle 33** (`overnight/grainhub-cycle-33`, 710 tests): Bushel
  samples #5 + Skyland/AGP re-verified 11/12 exact matches (AGP
  changed site-side Chester → Aberdeen, registry updated);
  Bentonville gap from Cycle 32 closed; merge plan extended to
  Cycle 32 (83 commits, 0 merges).
- **Cycle 34** (`overnight/grainhub-cycle-34`, 711 tests): Bushel
  samples #6 + Smithfield/Alliance re-verified 11/12 exact
  matches (Alliance changed site-side Gibson City →
  Anchor/Cropsey/Colfax, registry updated); Smithfield East
  Region sweep fully re-verified (all 30 locations, Cycles
  29–34); merge plan extended to Cycle 33 (85 commits, 0 merges).
- **Cycle 35** (`overnight/grainhub-cycle-35`, 711 tests, docs
  only): embed family re-verified 12/12 exact matches (454
  rows); subagent spawning became unavailable — Cycle 35 run
  coordinator-direct; merge plan extended to Cycle 34
  (87 commits, 0 merges).
- **Cycle 36** (`overnight/grainhub-cycle-36`, 711 tests, docs
  only): AgriCharts wrappers 11/11 + key collectors 5/5 exact
  matches (16/16 overall); every live-verified collector
  family now re-checked this morning with zero drift; merge
  plan extended to Cycle 35 (89 commits, 0 merges).
- **Cycle 37** (`overnight/grainhub-cycle-37`, 711 tests, docs
  only): early Bushel sites 9/9 exact matches; Mae-Mart still
  viable (page 171 bytes smaller, proxy shape unchanged);
  merge plan extended to Cycle 36 (91 commits, 0 merges).
- **Cycle 38** (`overnight/grainhub-cycle-38`, 711 tests, docs
  only): web build re-run passes (33/33 pages, first since
  Cycle 17); config/registry drift audit clean (121 entries,
  102 enabled, 119 adapters, 17 toggled off); merge plan
  extended to Cycle 37 (93 commits, 0 merges).

**Remaining blockers that need Adam:** NASS API key (free) and FAS /
data.gov key (free); LLM provider + key for Advisor `/ask`; Barchart /
DTN licensed feed decision — Barchart docs prohibit redistribution, so
a separate redistribution licence decides whether the Price Finder can
use the feed at all; ERP choice (Agvance recommended first, Agris
second, AgTrax third); eSign provider; `gh` re-authentication with
`workflow` scope so the written CI workflow (`.github/workflows/
api-tests.yml`) can be pushed — the file is in no branch, it sits
untracked locally, and the `.github` directory must not be assumed
present after merging; currency column or per-source currency
mapping — normalized price rows carry no currency, so basis/best-bid
responses report `currency: null` (a design note with four concrete
decisions is now in `docs/plans/currency-design.md`); email-bid endpoint is public by
default (admin-only is a one-line change if wanted); pricing/hosting
decisions. **Newest findings:** the `cashbids.php` embed family is
now 13 sites (PRO Coop 21302b proven in Cycle 13); the Skyland
picker sweep is complete (all 14 IDs verified) and the Smithfield
East Region sweep is complete (30 of 31 locations; Raeford posts no
public bids); the Andersons is fully closed for static collection
(the Maumee facility tables are Barchart-licensed); CGB's cash-bid
page is an AgriCharts embed (licensed, not fetched); Mae-Mart's
futures proxy is live and the collector now fills `futures_price`
(cash NOT computed — open decision); the registry holds 119 adapters
(13 agricharts wrappers verified live in Cycle 21 — 11 return rows,
642 total; Heartland + Mulvane return 0 rows site-side on two
consecutive probes, possibly an AgriCharts template change; Heritage
parser fixed in Cycle 22 to 14/14 rows); seeding + poller now honour
`[sources]` toggles; the FMN collector is complete for the default
view (453 rows, all 449 futures-linked rows filled via the
`jsquote.php` feed); Five Star's wpDataTables collector is built
(299 rows); the DTN sweep found only 2 of 28 sites static-HTML, 20
JS-only, 6 unreachable, with Al-Corn the only classic inline
`CashBidTable` fit for the DTN collector (Sunrise is a second
classic-DTN fit, enabled in Cycle 10). A Playwright render check of
the DTN-family JS-only sites, the FMN filtered view, and Mapleview's
Grain Discovery shell still needs a live browser session. **Cycle
23 additions:** Heritage confirmed live at 14 rows (parser fix
closed); Heartland + Mulvane toggled off in `config.toml`
(`heartland_coop`/`mulvane_coop = false`, reversible; seed count
104 → 102); AgriCharts futures-fallback design note written
(`docs/plans/agricharts-futures-fallback-design.md`) — basis is in
the row, not the feed; coordinator decision recorded to keep the
collector's Chrome UA. **Cycle 24 additions:** fallback (a)
implemented and tested (basis-only parsing; live Heartland/Mulvane
still 0 rows — rows no longer in static HTML); (b) probe fails
(feed returns `var quotes = null;`) and corrects the "tag missing"
phrasing (tag present, empty symbols); staleness daytime re-check
— none of the four refreshed, refresh-later hypothesis answered
(no). **Cycle 25 additions:** Heartland filtered view still 0 rows
(hypothesis closed); Mulvane re-checked 0 rows, tag correction
extended; feed-down degradation implemented; Heartland/Mulvane
closed for now. **Cycle 26 additions:** feed-error degradation
implemented — design-note work complete; live re-verification
sweep of five key collectors, all exact matches (FMN 453, Five
Star 299, TGM 362, USDA mirror 197, FAC 45). **Cycle 27
additions:** all 10 working AgriCharts wrappers re-verified live,
all exact matches (639 rows) — every live-verified collector now
re-checked this morning with zero drift. **Cycle 28 additions:**
full 13-site embed family re-verified live, all exact matches
(816 rows); FS Grain mirror confirmed (197 rows, report id 7730).
**Cycle 29 additions:** Bushel sample 6/6 exact matches (Hugoton
still one day stale); Mae-Mart still viable — page byte-identical
to Cycle 18, proxy shape identical to Cycle 19, canonical URL now
extensionless. **Cycle 30 additions:** Bushel sample #2 6/6 exact
matches (Hamer still one day stale); Mae-Mart proxy URL stored
extensionless. **Cycle 31 additions:** Bushel samples #3 + Cycle
4/5 sites 12/12 exact matches; Almota joins the staleness watch
(watch list now five widgets).
