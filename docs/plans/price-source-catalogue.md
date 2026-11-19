# GrainHub Price-Source Catalogue

Public elevator cash-bid sources verified during overnight Cycle 1
(2026-11-19). One polite probe per URL, contact User-Agent
`GrainHub-Research/1.0 +https://github.com/apz100/GrainHub`.

**Rules:** public elevator pages and public government data only.
No Farmbucks / GrainFox / Barchart paywalled data, no bulk scraping
of licensed feeds. A source is **verified** only when bid content
was seen in a direct fetch. **Partially verified** = live homepage
+ search-index evidence, bid table not yet seen directly.

## Ontario — existing panel (from the repo, verified 2026-11-19)

| Company | Location(s) | URL | Type | Crops | Frequency | Status |
|---|---|---|---|---|---|---|
| AgriCharts / Farm Market News | Brinston, Cardinal, Chesterville, Dalkeith, Johnstown, Kars, Lansdowne, North Gower, Prescott, Vankleek Hill, Winchester | https://fmn1.agricharts.com/markets/cash.php | AgriCharts writeBidRow | corn, soy, wheat | intraday | Verified live 200 (2026-11-19). Keep. Full read 2026-11-18 — see "Farm Market News cash page" section below. |

## Farm Market News cash page — full read (2026-11-18 23:49–23:51 EST)

The page `https://fmn1.agricharts.com/markets/cash.php` was read in full.
It is **one long scrolling list, not paginated**: **204 separate bid
tables covering 86 distinct named delivery points** — 85 Ontario-titled
plus 1 Quebec ("Quebec FOB Corn"). No prices are copied here;
locations, crops, and structure only.

- **Columns per table:** Name, Delivery, Delivery End, Futures Month,
  Futures Price, Change, Basis, Cash Price, Settlement.
- **Crops:** corn, soybeans, wheat (HRS / HRW / SRW / SWW, new + old
  crop). **Barley and oats only at Hensall HDC and Sunderland.**
  **No canola table appeared.**
- **Delivery:** mostly old crop Nov 2026 and new crop Oct 2027
  (corn/soy) / Jul–Aug 2027 (wheat), with a few exceptions
  (e.g. London Dec 2026–Feb 2027).
- **Delivery points in page order (86):** Alliston, Amberly, Arner,
  Aylmer, Ayr, Beeton, Belmore, Blenheim, Brantford, Brigden, Brinston,
  Burford, Burgessville, Cargill ON, Chatham Ethanol, Chatham-Kent Avg,
  Chatham/Oungah, Chesterville, Collingwood, Dalkeith, Delhi, Dresden,
  Essex Cty, Exeter, Forest, Glencoe, Grafton, Grand Valley, Guelph,
  Hagersville, Haggerty, Hamilton Transfer, Hensall HDC,
  Hensall Thompson, Highgate, Huron FOB, Ingredion Cardinal,
  Ingredion London, Johnstown Ethanol, Kars, Kent Bridge, Kent FOB,
  Lamb FOB, Lansdowne, Lindsay, Listowel, London, London Avg, Lucknow,
  McGregor, Mdsx FOB, Milverton, Mitchell GLG, Mitchell Thompsons,
  Monkton, North Gower, Norwich, Oakwood-Sunderland Co-op, Palmerston,
  Park Hill, Pontypool, Port Albert, Port Colborne,
  Port Colborne Transfer, Port Perry, Prescott Transfer, Putnam,
  Quebec FOB, Rochester, Seaforth, Straffordville, Sunderland,
  Tavistock, Thamesville, Thornton, Toledo Elevator, Trenton,
  Tupperville, Vankleek Hill, Varna, W O Feed, Wheatley, Windsor,
  Windsor Crusher, Woodstock, Wyoming.
- **Dropdown discrepancy — the default view is NOT the complete FMN
  Ontario set:** the Location dropdown lists **336 options (335
  named)** — far more than the 204 tables on the default view.
  Dropdown-only entries include Winchester, Sarnia, Goderich, Durham,
  Wellington, Chatham, Kintore, Maxville, and others, plus duplicates
  (Delhi ×4, Glencoe ×4, Hensall Thompson ×4, Sarnia ×4).
- **Location-filter mechanism (verified 2026-11-19, Cycle 3 — see
  `docs/plans/fmn-location-filter.md`):** dropdown option values
  ARE numeric `location_filter` IDs (336 options; e.g. Winchester
  `2523`, Winchester Corn `1965`, Winchester Soybeans `1992`).
  `cash.php?location_filter=2523` returns HTTP 200 with Winchester
  selected and the bid-table scaffolding — BUT the static HTML
  contains zero inline `writeBidRow(...)` invocations (vs 454 on the
  default view) and an empty `jsquote.php symbols=` parameter, so
  the filtered rows are JS-rendered, not embedded. **Still to prove:**
  a Playwright render check that Winchester rows actually load.
  If confirmed, the FMN collector covers up to 335 Ontario points
  from one URL pattern.
- **Collector built (Cycle 10, `fmn_source.py`, 31 tests):** the 204
  tables are real `<table class="homepage_quoteboard">` elements,
  but the data rows are JavaScript — one `writeBidRow(...)` call per
  row inside each `<tbody>` (454 occurrences on the page, of which 1
  is the function definition, so **453 row calls**). The parser reads
  those calls from static HTML (balanced-paren scan, no JS
  execution, no browser). Verified live 2026-11-19 (one polite GET,
  200, 353,938 bytes): **453 rows, 87 distinct delivery points**
  (Corn 151, Soybeans 145, wheat 153, Barley 2, Oats 2). The 87th
  point vs the 86 in the 2026-11-18 read is **"US Rep"** (`US Rep
  Corn`, symbol ZCZ26) — a table the earlier read did not list.
  **Gap:** futures price / change / cash price on the 449
  futures-linked rows are NOT in the static HTML — they come from a
  separate `jsquote.php` feed the calls reference, which was not
  fetched (one-GET scope); those fields are `None` with a note until
  a later cycle fetches the feed or renders with Playwright.
  Barley/oats manual rows (4, Hensall HDC + Sunderland only) get
  cash from the page's own deterministic `basis / 100` render rule.
  Currency is recorded as CAD by FMN Ontario convention — inferred,
  not labelled on the page; confirm against a rendered page. Basis
  is kept at published cents scale, not divided by 100. Registered
  as `fmn` in `source_registry.py` + `config.toml`.
| Great Lakes Grain | 36 locations incl. Embrun, MacEwen Farms | https://cashbids.greatlakesgrain.com/index.cfm | DTN index.cfm (Playwright) | corn, soy, wheat, IP soy | not stated | Verified live 200. Keep. |
| London Agricultural Commodities | 18 elevators incl. Charwen (Thornton) | https://www.londonag-dtn.com/index.cfm?show=11 | DTN index.cfm (Playwright) | corn, soy, wheat | not stated | **Fixed 2026-11-19 (Cycle 3):** `lac_source.py` base URL updated from dead `dtn.londonag.com` to `www.londonag-dtn.com`; re-verified live 200 with "Cash Bid" content and Location dropdown (options/tables are JS-rendered, as the Playwright collector expects). New pytest: `tests/test_lac_source.py`. |
| The Andersons Canada | 14 locations (Blacks Lane, Blenheim, Granton, Hensall, Kent Bridge, Mitchell, Norwich, Pain Court, Pontypool, Port Albert, Claybanks, IGPC Ethanol, Kintore, Rannoch) | https://dtn-api.andersonscanada.com/cash-bids/blacks-lane | DTN HTML tables, plain requests | corn, soy, white/SRW wheat | basis daily ~5:10 pm EST | Verified live 200 (1 of 14 slugs probed). Keep. |
| Snobelen Farms | Brantford + northern group (Ripley, Lucknow, Amberley, Dungannon, Palmerston, Benmiller, Tiverton) | https://snobelenfarms.com/wp-content/plugins/mv_blocks/blocks/dtn/feed.php?commodity=all&location=Brantford | DTN feed.php, plain HTTP | corn, soy, HRW/SRW/soft white/HRS wheat | not stated | Verified live 200. Keep. |
| Hensall District Co-operative | Hensall, Ailsa Craig + others | https://hensallco-op.ca/Cash-Bids.htm | DTN widget (Playwright) | corn, soy, SRW/HRW/HRS/soft white wheat | not stated | Verified live 200. Keep. |
| DG Global | destinations per row | https://dgglobal.ca/cash-bids | Plain HTML table | corn, soy, wheat | not stated | Verified live 200. Keep. |
| Wanstead Farmers Co-op | Wanstead / Alvinston | https://fscooperatives.com/wansteadfarmerscoop/agriculture/cash-bids | DTN widget (Playwright) | corn, soy, IP soy, SRW/HRW/soft white wheat | not stated | Verified live 200. Keep. |
| Ganaraska Grain | Port Hope | https://www.ganaraskagrain.com/cashbidsindex | AgriCharts jsquote.php | corn, soy, wheat | not stated | Verified live 200. Keep. |
| Ingredion | Cardinal | https://ag.ingredion.com/cash-bids | Plain HTML / Playwright | corn (processor) | not stated | Verified live 200. Keep (CashGrainBids collector). |
| Greenfield Global | Johnstown | https://ggi.marketplace.barchart.com/cash-bids | Barchart marketplace (Playwright) | corn (ethanol) | not stated | **Status-only, HEAD check 200.** Do not scrape Barchart data; Adam to confirm whether the existing collector is acceptable or should be dropped. |
| Bunge | Hamilton (was), Altona/Harrowby/Morden MB | https://www.bungeag.com/locations/hamilton-on/ | — | — | — | **Dead 404, keep disabled** (`bunge = false` already). No replacement URL found. |

## Ontario — new candidates (verified 2026-11-19)

| Company | Location | URL | Type | Crops | Frequency | Status |
|---|---|---|---|---|---|---|
| North Gower Grains | North Gower | https://northgowergrains.com/ (daily blog post, e.g. /wednesday-november-18-2026-820-am/) | Plain HTML daily post table | corn, soy, SRW/HRW/HRS wheat (incl. protein) | daily ~7:00 am | **Collector added 2026-11-19 (Cycle 3):** `north_gower_source.py` parses the daily-post table (Name/Notes/Basis Month/Futures/Basis/Cash Price/Cash Price tonne); homepage `#cash-bids` is a CTA with no prices — collector follows the latest daily-post link. Ordinary source; no special treatment. |
| Collwest Grain | Collingwood | https://www.collwestgrain.com/ | Homepage cash-bid widget (.cbmod) | corn, soy, SRW/HRW/HRS wheat, canola, barley, oats | daily | **Collector added 2026-11-19 (Cycle 3):** `collwest_source.py` parses the homepage widget (Delivery/Bid/Basis/Futures per crop-year). Verified live 200. **Cycle 4:** the generic Bushel collector (`bushel_source.py`, `fetch_collwest_bushel`) parses the same widget — verified live 2026-11-19, 16 rows, zero value differences vs `collwest_source.py`. **Country confirmed Canadian, CAD (2026-11-18):** footer address 2924 Sixth Line, Collingwood, ON L9Y 3Z1, phone 705-445-7276; canola/barley/oats per tonne, corn/soy/wheat per bushel; `collwestgrain.o.bushelsites.com` serves identical content — www domain is canonical. Do not enable in the US config. |
| Mae-Mart Farms | Norfolk County | http://www.mae-martfarms.com/grain-pricing | Plain HTML tables (gp-table-*) | corn, soy, wheat, rye | continuous in market hours | **Collector added 2026-11-19 (Cycle 3):** `mae_mart_source.py` parses the tables. Basis is static; corn/soy/wheat cash prices are JS-filled from the site's futures proxy, so those rows carry basis with cash price empty + reason (never guessed). Rye has a static manualPrice, so its cash price is parsed. Homepage cards are "—" placeholders only. **Cycle 18 (2026-11-19):** proxy identified verbatim from the page's inline JS — `var PROXY = '/grain-proxy.php'`, called as `fetch(PROXY + '?symbols=' + encodeURIComponent(sym))`, one symbol per request, i.e. `http://www.mae-martfarms.com/grain-proxy.php?symbols=<SYMBOL>`. Symbols are Yahoo Finance format (`ZCZ26=F`, `ZSF27=F`, `ZWN27=F`). The proxy returns **futures quotes only**, not cash bids: JSON keyed by symbol, each entry with `price` and `currency`; `currency === 'USX'` means the price is in cents (client divides by 100) — `USX` is the Yahoo Finance currency code for CBOT grain futures. Cash is computed client-side as futures + static basis. No Barchart/DTN/AgriCharts markers anywhere in the page. Upstream is **not confirmed** (the proxy itself was not called — that is a later cycle's probe); the symbol format and `USX` handling are consistent with a Yahoo Finance public-quote relay, but that is inference from the client JS only. **Next probe (later cycle, 1 GET):** `GET /grain-proxy.php?symbols=ZCZ26=F` — confirm the response shape and whether the relay is live. Open decision for Adam/coordinator: even if live, using it means relying on the site's relay of third-party futures data plus the site's static basis to compute cash — the collector currently does not call it. **Cycle 19 (2026-11-19): probe done — proxy is LIVE and matches the contract exactly.** `GET /grain-proxy.php?symbols=ZCZ26=F` (1 GET, http → 301 → https) returned HTTP 200, `application/json`, 89 bytes: JSON keyed by the symbol, entry with numeric `price`, `currency: "USX"`, plus `timestamp` and `fetched` fields. Contract confirmed: `USX` = cents. Collector now fills `futures_price` on corn/soy/wheat rows from the proxy (one GET per symbol, USX cents ÷ 100 per the page's own rule) as an optional second step that degrades gracefully to basis-only rows if the proxy fails. `cash_price` is still NOT computed from futures + basis — that remains an open decision for Adam/coordinator (relying on a third-party relay + static basis to compute cash is a bigger step). Rye untouched (no symbol, static manualPrice). 7 new tests in `tests/test_ontario_collectors.py`, all synthetic fixtures. |
| Mapleview Grain | London | https://www.mapleviewgrain.ca/ → https://mapleview.graindiscovery.com/ | Grain Discovery JS app | corn, soy, wheat (old + new crop) | not stated | **No plain-HTML collector possible (Cycle 3):** homepage `#bids` is marketing copy; the bids page is a Next.js app shell with no bid content in static HTML. `mapleview_source.py` is a stub returning an explicit unsupported reason. Needs a Playwright render or a public Grain Discovery feed (later cycle). |
| Charwen Farms | Thornton (Simcoe County) | https://charwenfarms.ca/ | Plain HTML | corn, soy, wheat | not stated | Partially verified — homepage live, cash-bids page exists per homepage but not yet fetched. Investigate: may duplicate LAC feed (Charwen is an LAC location). |
| Addis Grain | Simcoe County area | https://www.addisgrain.com/ | Unknown | corn, soy, wheat (old + new crop) | not stated | Partially verified — homepage live only; bids page not yet located. Investigate. |

## Ontario — ruled out (no public web bid page)

Parrish & Heimbecker (app-only, P&H Direct), Richardson Pioneer
(gated app), ADM (ADM Access app / text alerts), Thompsons Ltd.
(now The Andersons, already covered), Sylvite (no elevator bids),
Cargill / Viterra / G3 Canada (no public Ontario web bids found).

## Ontario — leads not yet probed

St. Lawrence Grains & Farm Supply (Stouffville / Havelock /
Peterborough-Norwood), Homeland Grain (Norwich), GFO SellSmart
(app, possible aggregated Ontario feed), Bunge Canada replacement URL.

## Ontario counts

- Existing base URLs probed: 13 — 11 live, 2 dead (LAC old domain, Bunge Hamilton).
- New candidates: 7 — 4 fully verified (North Gower Grains, Collwest,
  Mae-Mart, Mapleview), 2 partially verified (Charwen, Addis),
  1 replacement URL verified (LAC new domain). **Cycle 3 update:**
  collectors added for North Gower Grains, Collwest, Mae-Mart
  (Mapleview: stub only — JS app, no plain-HTML structure); LAC base
  URL fixed in code.
- **Action items (done in Cycle 3):** `lac_source.py` base URL
  updated to `londonag-dtn.com` and re-verified; collectors added for North Gower Grains, Collwest,
  Mae-Mart (`app/platform/market_data/sources/{north_gower,collwest,
  mae_mart,mapleview}_source.py`, pytest in
  `tests/test_ontario_collectors.py` + `tests/test_lac_source.py`,
  fixtures in `tests/fixtures/`). Mapleview has no plain-HTML
  structure — stub only. **Still to wire (not done here — new files
  only, no shared-file edits in this cycle):** register the four new
  collectors in `app/services/source_registry.py` (SourceAdapter
  entries) and add `north_gower / collwest / mae_mart / mapleview`
  toggles to the `[sources]` section of `config.toml`; confirm
  Greenfield/Barchart handling with Adam. **Still to prove:** FMN
  `location_filter` rows rendering in a browser (Playwright check
  of `cash.php?location_filter=2523` — see
  `docs/plans/fmn-location-filter.md`); if it loads, the FMN
  collector covers up to 335 Ontario points from one URL pattern.

## United States — existing list (verified 2026-11-19)

58 unique URLs probed from `config.toml` + `us_elevators_urls.toml`.
47 of 58 returned HTTP 200. Full detail:
`~/workspace/us-probe/us-price-sources.md`.

| Status | Count | Meaning |
|---|---|---|
| Verified live — bid-table marker in static HTML | **8** | `writeBidRow` ×7, `CashBidTable` ×1 |
| Live — page served, bids JS-rendered (widget ref present) | 26 | Needs Playwright to confirm bid rows |
| Live site — no bid table at this URL | 13 | Homepage / generic page / redirect target |
| Blocked (confirmed challenge / rate-limit) | 2 | StateLine Coop (Cloudflare challenge), Landus (HTTP 429) |
| Uncertain — possible bot-check strings | 2 | Al-Corn, Elite Octane |
| Dead | 7 | Cardinal Ethanol, Gold Eagle, POET, Luckey Farmers, Hull Coop (all 404); Mercer Landmark (522); CVA (202 empty body) |

### Verified live (AgriCharts `writeBidRow`)

| Company | Location | URL | Type | Crops | Frequency | Status |
|---|---|---|---|---|---|---|
| Ag Plus | — | https://www.agplusinc.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified 2026-11-19. Keep. **Cycle 21 (2026-11-19):** wrapper `fetch_ag_plus` verified live — 36 rows (Corn 12, Beans 12, Wheat 12), 6 locations (Churubusco, Edgerton, Garrett, Monroeville, Raber, South Whitley). |
| Farmers Win Coop | — | https://www.farmerswin.com/markets/cash.php | AgriCharts | corn, soybean | intraday | Verified. Keep. **Cycle 21 (2026-11-19):** wrapper `fetch_farmers_win_coop` verified live — 171 rows (Corn 90, Soybeans 81), 18 locations. |
| Heartland Coop | — | https://www.heartlandcoop.com/markets/cash.php | AgriCharts | corn | intraday | Verified. **Config fixed**: `config.toml` used `myaccount.heartlandcoop.com/bids.htm` (no bid marker); switched to cash.php. **Cycle 21 (2026-11-19):** wrapper `fetch_heartland_coop` returned 0 rows — page fetched (2xx) but no `jsquote.php` script tag in the HTML, so `fetch_us_agricharts` bailed before parsing. Site-side change (page restructured or tag removed); wrapper URL/name verified correct against config + Cycle 1 discovery, no wrapper change. Re-probe in a later cycle. **Cycle 22 (2026-11-19): re-probed through the wrapper — still 0 rows, `jsquote.php` tag still missing; wrapper unchanged.** **Cycle 23 (2026-11-19): toggled OFF in `config.toml` `[sources]` (`heartland_coop = false`) — two consecutive 0-row probes (Cycles 21, 22), `jsquote.php` tag missing; the poller would fetch it daily for nothing. Reversible. `us_elevators_urls.toml` entry stays enabled; the toggle is the gate. Not re-probed this cycle, per the Cycle 23 decision.** |
| Heritage Grain Cooperative | — | https://www.heritagegrain.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified. Keep. (Page title says "Legacy Grain" — possible rebrand.) **Cycle 21 (2026-11-19):** wrapper `fetch_heritage_grain_cooperative` returned 3 rows only (CORN / BEANS / WHEAT - CASH, 1 each) and the `Location` labels are the commodity names — the page's `<h4>` tags hold commodity headings, not location names, so the generic parser's h4-as-location assumption mislabels them. Wrapper URL/name correct; site-structure quirk, not a wrapper bug. Follow-up: check whether the page genuinely lists only 3 cash bids or more rows in a format the regex skips. **Cycle 22 (2026-11-19): answered — the page lists 14 bids, not 3; 11 forward-month rows were skipped because their notes argument holds an escaped quote (`'DEC \'26'`), and all 14 `<h4>` tags are commodity headings. Generic parser fixed (escaped-quote support + commodity-heading fallback); see "Cycle 22 — Heartland/Mulvane re-probes + Heritage parser fix".** **Cycle 23 (2026-11-19): confirmed LIVE — `fetch_heritage_grain_cooperative()` returned 14 rows (CORN 6, BEANS 6, WHEAT 2), all with the company fallback location `Heritage Grain Cooperative - Heritage Grain Cooperative`, deliveries Oct 2026–Nov 2027. The Cycle 22 parser fix is confirmed live; follow-up closed.** |
| Keller | — | https://www.kellergrain.com/markets/cash.php | AgriCharts | corn, soybean, wheat | intraday | Verified. Keep. **Cycle 21 (2026-11-19):** wrapper `fetch_keller` verified live — 14 rows (Corn 7, Soybeans 7), 1 location (Keller). |
| Kokomo Grain | Kokomo, IN | https://www.kokomograin.com/markets/cash.php?location_filter= | AgriCharts | corn, soybean, wheat | intraday | Verified. Keep. **Cycle 21 (2026-11-19):** wrapper `fetch_kokomo_grain` verified live — 63 rows (Corn 29, Soybeans 24, Wheat 5, NGMO Waxy 5), 8 locations. |
| Legacy Farmers | — | https://www.legacyfarmers.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified. Keep. **Cycle 21 (2026-11-19):** wrapper `fetch_legacy_farmers` verified live — 66 rows (Beans 25, Corn 24, Wheat 17), 10 locations. |
| Sunrise | — | https://www.sunriseco-op.com | DTN `CashBidTable` on homepage | — | intraday | Verified widget on homepage; find its cash-bids sub-page for a stable URL. **Cycle 10 (2026-11-19):** confirmed classic DTN — `<div id="target">` + `CashBidTable(tableOptions)`, companyID 23043, CIHedging `CashBidWidget.js`, ATLAS DTN shell; no static bid rows. Reclassified `unknown → dtn` and enabled in `us_elevators_urls.toml` (covered by existing `us_dtn_source.py`); Playwright render check still open. |

### Dead — disabled in config (2026-11-19)

Cardinal Ethanol (404), Gold Eagle Coop (404), POET (404 — site redesigned, no cash.php), Luckey Farmers (404), Hull Coop (404). Mercer Landmark (522, may be transient — re-check later), CVA (202 empty body — re-check later). **Cycle 10 re-check (2026-11-19):** Hull Coop still 404 at `/cash-bids` — but its 404 page links `/cashbids` (different slug), so that slug is the next probe; Mercer Landmark still 522 with an empty body; CVA still 202 with an empty body. All three reclassified `unknown → unreachable` in `us_elevators_urls.toml` except Hull Coop, which stays `unknown` pending the `/cashbids` probe.

### Blocked / uncertain — do not retry aggressively

StateLine Coop (Cloudflare "One moment, please..."), Landus (HTTP 429 Vercel checkpoint), Al-Corn + Elite Octane (captcha-related strings; page otherwise looks real — re-check with a browser/Playwright). **Cycle 10 (2026-11-19):** Landus still 429 — a Vercel Security Checkpoint page ("We're verifying your browser", JS required), reclassified `unknown → unreachable`; StateLine now serves its homepage 200 with no challenge page (the reCAPTCHA strings are form-related), but no widget sits on the homepage — its `/cash-bids` sub-page is still unfetched.

### Reclassified

AGP → DTN, Five Star Coop → DTN, Gateway FS → DTN (DTN refs found in HTML despite the .php URL).

### Do not add

Bunge `bungeag.com/cash-bids` (redirects to a locations archive — no bid table). ADM FarmView / CargillAg / GrainBridge: login-gated, no public page.

## United States — new candidates (20 probed, 19 live, 1 dead, 2026-11-19)

| Company | Location | URL | Type | Crops | Frequency | Status |
|---|---|---|---|---|---|---|
| Central Farmers Coop | Salem, SD | https://www.cenfarmcoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, oats | intraday | **Verified** `writeBidRow`. Added to active config. **Cycle 21 batch B (2026-11-19):** verified through the wrapper `fetch_central_farmers_coop()` — 75 rows (Corn 44, Soybeans 30, Winter Wheat 1; 11 locations). |
| Anthony Farmers Co-op | Harper, KS | https://www.anthonycoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, milo, canola | intraday | **Verified** `writeBidRow`. Added to active config. **Cycle 21 batch B (2026-11-19):** verified through the wrapper `fetch_anthony_farmers_coop()` — 9 rows (Corn 3, Milo 3, Soybeans 3; ANTHONY, HARPER, SHARON). |
| Mulvane Cooperative Union | Mulvane, KS | https://www.mulvanecoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, milo | intraday | **Verified** `writeBidRow`. Added to active config. **Cycle 21 batch B (2026-11-19):** wrapper `fetch_mulvane_coop()` returns **0 rows** — HTTP 200 but no `jsquote.php` script tag on the page (site-side; not a wrapper bug). Re-probe in a later cycle. **Cycle 22 (2026-11-19): re-probed through the wrapper — still 0 rows, `jsquote.php` tag still missing; wrapper unchanged.** **Cycle 23 (2026-11-19): toggled OFF in `config.toml` `[sources]` (`mulvane_coop = false`) — two consecutive 0-row probes (Cycles 21, 22), `jsquote.php` tag missing; the poller would fetch it daily for nothing. Reversible. `us_elevators_urls.toml` entry stays enabled; the toggle is the gate. Not re-probed this cycle, per the Cycle 23 decision.** |
| Brubaker Grain | West Alexandria, OH | https://dtn.brubakergrain.com/ | DTN | corn, soybean, wheat | intraday | Widget ref + live bid rows in search index. Added to active config; confirm rows in Playwright. |
| Hoffman Ag Service | Marshall, MI | https://dtn.hoffmanag.com/ | DTN | corn, soybean, wheat | intraday | Same as above. Added to active config. |
| Wilton Farmers Union Elevator | Wilton, ND | https://www.wiltonfarmerselevator.com/index.cfm?show=11&mid=5&theLocation=1&cmid=all&layout=19 | DTN | spring/durum wheat, soybean, corn, flax, canola, sunflower, barley, oats, peas, pinto beans | intraday | Broadest crop list in the survey. Added to active config; confirm rows in Playwright. |
| Chandler Feed | Chandler, MN | https://chandlerfeed.o.bushelsites.com | Bushel (new type) | corn, soybean, oats | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, homepage `.cbmod` widget, **17 rows**, 6-column layout (Delivery/Bid/Basis/Futures/Change/Futures Month, no Last Trade), corn/oats/soy, USD/bu. Futures/change in fractional cents notation (`433-2` → 433.25). Classless location h2 (`Chandler`). Footer lists Chandler, Edgerton and Woodstock, MN; widget shows Chandler only. `fetch_bushel_site("chandler_feed")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| FAC | Arcadia, IA | https://www.faccooperative.com/cash-bids | Bushel (new type) | corn, soybean | daily, dated | **Collector added 2026-11-19 (Cycle 4):** `bushel_source.py` generic Bushel collector (`fetch_fac` / `fetch_bushel_site("fac")`, direct_dict). Verified live 2026-11-19: 200, 7-column `.cbmod` widget, month delivery labels, **45 rows across 3 locations on one page** (Arcadia + Schleswig corn/soy, AGP Manning soy only), USD/bu. Not yet wired into `source_registry.py` (needs a coordinator decision). |
| Cameron Coop | Cameron, MO | https://www.cameroncoop.com/ | Bushel (new type) | corn, soybean | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, homepage `.cbmod` widget, **4 rows**, 7-column layout, corn/soy (no oats section on the live page, despite the earlier listing), USD/bu. Change published in dollars (-0.0225), unlike FAC's cents. Footer address: Cameron, MO 64429. `fetch_bushel_site("cameron_coop")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| CGS | Bazine, KS | https://www.cgscoop.net/ | Bushel (new type) | wheat, milo, corn | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, homepage `.cbmod` widget, **4 rows**, 6-column layout (no Last Trade), wheat/milo/corn, USD/bu. Footer address: Bazine, KS 67516. `fetch_bushel_site("cgs")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| Almota Elevator | Colfax, WA | https://www.almotagrain.com/cash-bids | Bushel (new type) | soft white wheat, HRW wheat, barley | daily, dated | PNW wheat coverage. **Verified live 2026-11-19 (Cycle 5):** 200, 7-column `.cbmod` widget, **12 rows**, soft white wheat / hard red winter wheat / barley, USD. **DTN ambiguity resolved:** the page's only `dtn` string sits inside a base64 blob; the bids render in the Bushel widget (footer: "Data provided by Bushel"). Barley rows are Bid-only at per-tonne scale, so barley is $/t (scale-inferred). Footer address: Colfax, WA 99111. `fetch_bushel_site("almota")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| Williams Gin & Grain | North Dakota | https://williamsginandgrain.com/cashbidssingle- | Bushel (new type) | corn, grain sorghum | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200 at the URL as given — the trailing `-` is the real path, not truncation: the page loads, no redirect, and the site's own nav links to `/cashbidssingle-`. 7-column `.cbmod` widget, **2 rows**, corn ("As Harvested") + grain sorghum ("Harvest"), USD/bu. Location label is the company name; town unconfirmed from the page. `fetch_bushel_site("williams_gin")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| Rugby Farmers Elevator | Rugby, ND | https://rugbyfarmers.com/ | Bushel (new type) | HRS wheat, soybean, corn | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, homepage `.cbmod` widget, **12 rows**, 5-column layout (no Futures Month / Last Trade), HRS wheat/soy/corn, USD/bu. Classless location h2 ("Rugby & York Bids") — page covers Rugby & York; rows labelled Rugby (footer: 201 Dewey St SE, Rugby, ND 58368). `fetch_bushel_site("rugby")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| Lake Norden Farmers Elevator | Lake Norden, SD | https://www.lakenordenfarmerselevator.net/cash-bids | Bushel (new type) | corn, soybean | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, 7-column `.cbmod` widget, **2 rows**, corn ("Nc 2026") + soy ("Cash"), USD/bu. Change published in dollars (-0.0225), unlike FAC's cents. Footer address: Lake Norden, SD 57248. `fetch_bushel_site("lake_norden")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| United Cooperative | Webster City, IA | https://www.unitedcoop.com/cash-bids | Bushel (new type) | corn, soybean | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, 7-column `.cbmod` widget, **12 rows**, corn/soy, USD/bu. **Catalogue correction:** the footer contact is 1932 W 2nd St, Webster City, IA 50595 — the earlier "Beaver Dam, WI" town was wrong for this domain (no Beaver Dam mention anywhere on the live page). **Same-org question vs Batch 4 `unitedcooperative.com` RESOLVED
(Cycle 5, coordinator check): `unitedcooperative.com` is "United
Cooperative–Beaver Dam", corporate office N7160 Raceway Road,
Beaver Dam, WI 53916 — a different org from this Webster City, IA
Bushel site. Two orgs sharing a name; keep them as separate
sources.** `fetch_bushel_site("united_coop")` enabled. Wired into
`source_registry.py` as `united_coop` (Cycle 5). |
| Collwest Grain | — | https://collwestgrain.o.bushelsites.com | Bushel (new type) | — | — | **Removed from US list 2026-11-18 — confirmed Canadian (Collingwood, ON; CAD). See the Ontario section.** Generic Bushel collector (`bushel_source.py`, Cycle 4) also covers it — verified live 2026-11-19 via the www domain: 16 rows, 5-col widget, CAD, per-tonne canola/barley/oats. |
| Forest River Coop | Forest River, ND | https://www.forestrivercoop.com/ | Bushel (new type) | corn, soybean, wheat | daily, dated | **Verified live 2026-11-19 (Cycle 5):** 200, homepage `.cbmod` widget, **3 rows**, 7-column layout, USD/bu. Grade-prefixed commodity labels ("#1 Spring Wheat", "#2 Yellow Corn", "#2 Yellow Soybeans"). First section heads Bid as "Cash Price" with a blank Delivery header; futures/change in fractional cents notation (`630-0` → 630.0, `433-2` → 433.25). Footer address: Forest River, ND 58233. `fetch_bushel_site("forest_river")` enabled. Not yet wired into `source_registry.py` (coordinator decision). |
| James Valley Grain | — | https://jamesvalleygrain.com/pages/usdacash.php | USDA mirror (new type) | corn, soybean, wheat, oats | daily (USDA AMS cycle) | **Verified 2026-11-18** — direct fetch 200; report "USDA Cash Bid Report for Nov 18, 2026" (same-day fresh). 227-row static HTML table (`table table-condensed`), 25 region sections incl. "Gulf Coast Ports - LA" and "Pacific Ports"; prices in cents/bushel. History via `?id=N` (sequential numeric id; 7730 = Nov 18, 2026; archive on the page back to Nov 05, 2026). URL/format looks stable for a collector. Disabled — needs a USDA-mirror collector. |
| FS Grain | — | https://www.fsgrain.com/pages/usdacash.php | USDA mirror (new type) | corn, soybean, wheat, oats | daily (USDA AMS cycle) | **Verified 2026-11-18** — direct fetch 200; same report as James Valley (same id 7730, "USDA Cash Bid Report for Nov 18, 2026", same rows incl. Gulf Coast Ports – LA). Same table shape and `?id=N` history. URL/format looks stable for a collector. Disabled — needs a USDA-mirror collector. |
| Farmers Coop Equity | Zenda, KS | https://www.fceisabel.com/markets/cash.php | AgriCharts | — | — | **Dead 404.** Do not add. |

## United States — Gulf / PNW export terminals

No individual public cash-bid page was found for any Gulf or PNW export
terminal operator (CGB, ADM, Bunge, Cargill, United Grain, etc. — terminal
bids are login-gated or unpublished). The public coverage route is USDA AMS
reports: **Louisiana & Texas Export Bids** (Gulf) and **Portland Daily Grain
Bids** (PNW, via Portland Merchant's Exchange), mirrored on the two
USDA-mirror pages above (James Valley Grain, FS Grain) — both verified
same-day fresh on 2026-11-18, with "Gulf Coast Ports - LA" and "Pacific
Ports" sections in the table and history via `?id=N`.

## United States — counts

- Existing list: 58 probed — 8 verified, 26 live widget-present, 13 live
  no-bid-table, 2 blocked, 2 uncertain, 7 dead. 47/58 HTTP 200.
- New candidates: 20 probed — 19 live, 1 dead. 6 added to the active
  config (3 AgriCharts + 3 DTN), 11 Bushel + 2 USDA-mirror added
  disabled pending new collectors, 1 dead not added. **Cycle 3 update:**
  Collwest was one of the 11 Bushel entries and is confirmed Canadian
  (Collingwood, ON; CAD) — moved to the Ontario section, so the US
  Bushel set is now 10. Bushel-collector research is done (see
  docs/plans/bushel-collector-research.md): bids are in static HTML
  on the two sites checked, so a plain-HTTP table parser looks
  feasible — Playwright not needed for FAC or Collwest.
- Config changes applied in Cycle 1: 4 dead entries disabled in
  `config.toml` (Cardinal Ethanol, Gold Eagle, POET, Luckey Farmers);
  Heartland URL switched to the verified cash.php; AGP / Five Star Coop /
  Gateway FS reclassified to DTN in `us_elevators_urls.toml`; 6 new
  entries added to both `config.toml` and `us_elevators_urls.toml`;
  13 Bushel/USDA entries added disabled.
- **Cycle 4 update:** the generic Bushel collector is built
  (`GrainBids/grainbids/apps/api/app/platform/market_data/sources/bushel_source.py`,
  `fetch_bushel` / `parse_bushel_html`, direct_dict shape). FAC verified
  live 2026-11-19 (45 rows, 3 locations, USD/bu); Collwest verified live
  the same day as the second shape check (16 rows, CAD, per-tonne
  canola/barley/oats, thin Bid-only rows). The other 8 US Bushel sites
  have registry entries but are unverified — each needs one polite GET
  to confirm shape/locations/currency before enabling. **Correction to
  the Cycle 3 research note:** the cash bids are in the `.cbmod` div
  widget on both verified sites, not in `table.standardTable` /
  `table.market_table` (FAC's standardTable is a "Data provided by
  Bushel" footer; Collwest's market_table is the futures table). The
  collector parses the widget first and only falls back to a real
  `<table>` whose header row contains Delivery + Bid. Not yet wired
  into `source_registry.py` — coordinator decision.
- **Cycle 5 update:** the remaining 9 Bushel sites are all verified
  live 2026-11-19 (one polite GET each, all 200, all `.cbmod`
  widgets) and enabled in the registry — the Bushel set is now
  11/11 verified (FAC + Collwest + 9 new). Row counts: Chandler Feed
  17, Cameron Coop 4, CGS 4, Almota 12, Williams Gin 2, Rugby 12,
  Lake Norden 2, United Coop 12, Forest River 3. Three parser gaps
  found by this sweep and fixed in `bushel_source.py` (with synthetic
  fixtures + tests, no live HTML in the repo): fractional CBOT
  futures/change notation (`433-2` → 433.25, in published cents),
  classless location h2 (Chandler, Rugby), and Forest River's
  "Cash Price" Bid header with a blank Delivery header. **Units
  warning:** futures/change keep each site's published units and
  they vary — decimal sites publish futures in dollars (4.3325)
  and change in cents (FAC -2.25) or dollars (Cameron, Lake Norden:
  -0.0225); fractional sites publish both in cents. Two ambiguities
  resolved: Almota's bids render in the Bushel widget (its only
  `dtn` string is inside a base64 blob), and Williams Gin's
  `/cashbidssingle-` URL is canonical (loads 200, self-linked in
  the site's nav). United Coop's same-org question was resolved by
  the coordinator: `unitedcooperative.com` is a different org
  (Beaver Dam, WI) from the Webster City, IA Bushel site. All 11
  Bushel sites are now verified live and wired into
  `source_registry.py` (Cycle 5).
- Follow-ups for a later cycle: find cash-bid sub-pages for the 19 Batch 4
  homepages (Sunrise's sub-page is the priority); chase the CGB cash-bid
  module URL from the USDA SCL report (do not guess it); wiring the
  Bushel collector into `source_registry.py` would unlock 10 US
  elevators (FAC + the 9 Cycle 5 sites; 11th, Collwest, is Canadian —
  see Ontario) and a USDA-mirror collector
  would unlock Gulf + Portland export bids in one fetch.

## United States — Cycle 6 DTN sweep (2026-11-19)

Re-probed the 28 sites Cycle 1 left as "live, widget present — confirm
via Playwright" (26) plus "uncertain" (2). The 26 were reconstructed
from the Cycle 1 tables as: the 16 DTN-ref sites (Ag Partners, Agtegra,
Allied, CFS, Frontier, Green Plains, Heritage Coop, Linn, Midway, AGP,
Five Star, Gateway FS, Superior Ag, TGM, United Coop
`unitedcooperative.com`, Ursa) + Aurora + Kanza (config type `dtn`)
+ Ace Ethanol + Alliance Grain ("live, page served") + Heartland
`bids.htm` + Ag State + ALCIVIA + CRC + CGB + Bunge (live, no bid
marker) = 26; plus Al-Corn + Elite Octane (uncertain) = 28. One polite
GET per URL, contact User-Agent, ~2 s spacing. One extra GET of a
distinct embedded endpoint (Agtegra's AgriCharts `cashbids.php` URL,
taken verbatim from the page) to test whether that embed serves a
static table. Raw HTML saved to `/tmp` scratch only, never the repo.
No prices are recorded here — row counts and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 22 | Page served |
| Non-200 / unreachable (no retry) | 6 | Ag Partners 503 "Site is offline"; Heartland `bids.htm` proxy error; ALCIVIA, Bunge, CRC, Five Star read timeouts (30 s) |
| Bid rows visible in static HTML | **2** | Ace Ethanol (11 rows), Alliance Grain (10 rows) — both Bushel `.cbmod` |
| JS-only (widget present, no bid rows in static HTML) | 20 | Everything else live: DTN / AgriCharts-embed / StoneX / Bushel-iframe |
| No bid table at the probed URL | 1 | CGB (corporate grain page); Gateway FS also landed on a homepage (its cash-bids sub-page is linked but was not fetched) |
| Blocked (429 / Cloudflare challenge) | 0 | Every captcha/Cloudflare substring hit was a false positive (see below) |

### Per-site results

| Company | URL | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Heartland Coop (config URL) | https://myaccount.heartlandcoop.com/bids.htm | proxy error | — | — (unreachable this sweep) | Moot — config already uses the verified `cash.php` AgriCharts URL |
| Ag Partners | https://agpartners.net/cash-bids | 503 "Site is offline" | No | Offline page, no widget | Was DTN; now down — re-check later, do not assume dead. **Cycle 8:** back up — 200 (→ `/cash-bids/`), modern DTN widget (`content-services.dtn.com/ui-widgets/cash-bids-table-widget-1.0-latest.js`), no static bid rows. DTN Playwright. |
| Agtegra | https://www.agtegra.com/cash-bids | 200 | No | AgriCharts `cashbids.php` embed (`sdwg.agricharts.com`, location 3135) + ATLAS DTN shell (`/dtncashbidwidget/bindlocation`) | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` returns a `var bids` JSON payload, 8 Corn rows (Hecla). Generic collector `cashbids_embed_source.py` (`fetch_agtegra`). No Playwright needed. |
| Allied Cooperative | https://www.allied.coop/grain/cash-bids | 200 | No | Modern DTN widget `content-services.dtn.com/ui-widgets/cash-bids-table-widget-1.0-latest.js` | DTN Playwright (`us_dtn_source.py`) — needs a render check: modern widget, not classic `CashBidTable` |
| Aurora Coop | https://auroracoop.com/markets | 200 | No | Modern DTN widget JS (same as Allied) | DTN Playwright — render check needed |
| CFS | https://www.cfscoop.com/products-services/grain | 200 | No | aghost DTN widget (`DtnCashbidDetailsScript.js` + location-cookie flow); the one `<table>` is a futures quotes table, not bids | DTN Playwright — render check needed |
| Frontier Coop | https://www.frontiercooperative.com/grain/cash-bids | 200 | No | **StoneX** widget (`StonexCashbidScript.js`); inline JSON model is empty in static HTML (`LocationRecords: null`, default date) | NEW pattern — no existing collector; Playwright or StoneX investigation in a later cycle. **Cycle 8:** StoneX iframe unchanged (same key), inline model still empty; the verbatim iframe target (`stonehedge.stonex.com/component/bids?...`) is a JS app shell with no static bid data — see "Cycle 8 re-checks". |
| Green Plains | https://gpreinc.com/corn-bids/ | 200 | No | Modern DTN widget JS (same as Allied) | DTN Playwright — render check needed |
| Heritage Cooperative | https://www.heritagecooperative.com/grain/cash-bids | 200 | No | AgriCharts `cashbids.php` embed (`heritagecoop.agricharts.com`, location 21608) + ATLAS DTN shell | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` `var bids` JSON, 15 rows (Ada; Corn 7, Soybeans 7, Wheat SRW 1). Generic collector `cashbids_embed_source.py` (`fetch_heritage_coop`). No Playwright needed. |
| Kanza Coop | https://www.kanzacoop.com/services/grain | 200 | No | ATLAS DTN shell (`/dtncashbidwidget/bindlocation`, `ATLAS_DTN_CASHBID` panel); no `cashbids.php` embed | DTN Playwright — render check needed |
| Linn Coop | https://www.linncoop.com/grain/cash-bids | 200 | No | AgriCharts `cashbids.php` embed (`linncoop.agricharts.com`, filter=all) + ATLAS DTN shell | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` `var bids` JSON, 51 rows across 5 locations (ADM, Alburnett & Springville Elevator, Cargill (Beans), Cargill (Starch), Ingredion; #2 Yellow Corn 39, Soybeans 12). Generic collector `cashbids_embed_source.py` (`fetch_linn_coop`). No Playwright needed. |
| Midway Coop | https://www.midwaycoop.com/grain/cash-bids | 200 | No | AgriCharts `cashbids.php` embed (`midwaycoop.agricharts.com`, location 82270) + ATLAS DTN shell | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` `var bids` JSON, 8 rows (location label published as "All Locations"; Corn / Milo / Soybeans / Wheat, 2 each). Generic collector `cashbids_embed_source.py` (`fetch_midway_coop`). No Playwright needed. |
| Ace Ethanol | https://www.aceethanol.com/cash-bids | 200 | **Yes — 11 rows, Corn, 7-col widget** | Bushel `.cbmod` widget in static HTML, dated header | Existing generic Bushel collector (`bushel_source.py`) — verified against saved HTML, status ok |
| AGP | https://www.agp.com/grain/bids | 200 (→ `/bids/`) | No | **Bushel via iframe**: `<iframe src="https://agp.o.bushelsites.com/cash-bids">` inside a `dtn-page` shell | Reclassified dtn → bushel (iframe). **Verified 2026-11-19 (Cycle 7):** one polite GET of the iframe target — 200, standard 7-col Bushel `.cbmod` widget in static HTML, parsed by the generic `bushel_source.py` collector with no changes (status ok). Only 1 row on the page: Chester, NE, Soybeans, Nov 2026, USD/bu; widget header dated Nov 18, 2026 11:40 PM. Registry entry `agp` added (`fetch_agp()`); not yet wired into `source_registry.py` (coordinator decision). |
| Ag State | https://www.agstate.org/grain | 200 (→ `agstate.org/grain/`) | No | AgriCharts `cashbids.php` embed (`agstate.agricharts.com`, location 84205); **zero `dtn` strings** — Cycle 1's DTN label was wrong | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` `var bids` JSON, 11 rows (Corn 6, Soybeans 5; `groupby=ccommodity`, location label published as "A.C."). Generic collector `cashbids_embed_source.py` (`fetch_ag_state`). No Playwright needed. |
| ALCIVIA | https://www.alcivia.com/cash-bids | read timeout (30 s) | — | — (unreachable this sweep) | Re-check later, no retry. **Cycle 8:** back up — 200 (→ `/wisconsin-grain-services/cash-bids-grain-wisconsin-grain/`), AgriCharts `cashbids.php` embed (`alciviacoop.agricharts.com`, `groupby=location`, `filter=all`) — same family as Cycle 7's six; `cashbids-js.php` static route to verify in a later cycle. **Cycle 9:** resolved — `cashbids-js.php` static route proven, 181 rows, 15 locations; `fetch_alcivia` added, reclassified `unknown → agricharts-embed`. |
| Alliance Grain | https://www.alliance-grain.com/cash-bids | 200 | **Yes — 10 rows, Corn 5 + Soybeans 5, 7-col widget** | Bushel `.cbmod` widget in static HTML; location h2 "Gibson City - West"; compact delivery labels (`Nov26`) | Existing generic Bushel collector — verified against saved HTML, status ok |
| Bunge | https://www.bungeag.com/cash-bids | read timeout (30 s) | — | — (unreachable this sweep) | Still do-not-add (Cycle 1: redirects to a locations archive); re-check later. **Cycle 8:** 200 (→ `/locations/`), still the locations archive; "Cash Bids" is nav text only, no bid table. Still do-not-add. |
| CRC | https://www.centralregioncoop.com/grain | read timeout (30 s) | — | — (unreachable this sweep) | Re-check later, no retry. **Cycle 8:** back up — 200 (→ `/grain/`), but a generic grain-services page with no widget and no bid table; its Cash Bids links point to the homepage anchor `/home/#cash-bids`. Follow-up: one GET of the homepage. Site now brands as "Central United Cooperative" (assets on `centralunitedcoop.com`). **Cycle 9:** homepage GET (200) — anchor is actually `#cash-bids-futures`; the section holds a lazy-loaded StoneX component iframe, no static bid rows; no collector added. |
| CGB | https://cgb.com/cgb-grain/ | 200 | No | Corporate grain page; no widget, no bid table | **Resolved 2026-11-19 (Cycle 18):** the cash-bid page was found by site navigation, not the USDA SCL report — `cgb.com/cgb-grain/` links to `https://www.cgbgrain.com`, whose homepage links `/cash-bids` → `https://cgbgrain.com/cash-bids/`. That page is a WordPress page with an **AgriCharts cash-bids widget**: `<script src="https://cgb.agricharts.com/inc/cashbids/cashbids.php?filter=all&location&commodity&groupby=location&width=100%&showtimestamp=1&hidenav=1&showchart=1&format=table&fields=name,delivery_start,delivery_end,basismonth,futures,futureschange,basis,price&groupheading=table&bidsort=commodity&dateformat=%m/%d/%Y&months=11">` plus `//www.agricharts.com/marketdata/quotelib.js`. No static bid rows (0 `<table>` in the HTML); the location dropdown lists 113 CGB locations statically, rows are JS-filled. The AgriCharts URL was **not fetched** (licensed feed — record and stop). Open decision: AgriCharts is licensed data, same bucket as the DTN/Barchart licensed-feed decision (Cycle 17 item 10); whether the `cashbids-js.php` static route used by the generic `cashbids_embed_source.py` collector exists for `cgb.agricharts.com` is a later-cycle question gated on that decision. The USDA SCL lead is no longer needed. |
| Five Star Coop | https://www.fivestarcoop.com/cash-bids | read timeout (30 s) | — | — (unreachable this sweep) | Was DTN-ref in Cycle 1; re-check later, no retry. **Cycle 8:** back up — 200 (→ `/grain-elevators-and-services/five-star-cash-bids/`), **static bid rows: 299 rows, 21 locations, Corn 197 + Soybeans 102** in a server-rendered wpDataTables table (Location / Commodity / Delivery Periods / Bids / Basis / Change). New static pattern — plain-HTML parser feasible; see "Cycle 8 re-checks". |
| Gateway FS | https://www.gatewayfs.com/markets/cash.php | 200 (→ `fscooperatives.com/gatewayfs`) | No | Homepage; `dtn` hits are nav links only (DTN News → `dtnpf.com`); nav links a cash-bids sub-page (`/gatewayfs/agriculture/cash-bids`, not fetched) | Unconfirmed — was DTN-ref in Cycle 1 on nav links alone; one GET of the sub-page in a later cycle. **Cycle 8:** sub-page fetched — 200, Next.js app shell with `<div id="cash-bids-root" data-slug="gateway">` and DTN widget classes, no static bid rows. JS-only; DTN Playwright / render check. |
| Superior Ag | https://www.superiorag.com | 200 | No | AgriCharts `cashbids.php` embed (`superiorag-cb-jsi.agricharts.com`, location 82244) + ATLAS DTN tab (`dtn-cashbid-tab`) | **Resolved 2026-11-19 (Cycle 7):** static route proven — `cashbids-js.php` `var bids` JSON, 12 rows (CORN 8, SOYBEANS 4; `groupby=ccommodity`, location "Princeton Central"). Generic collector `cashbids_embed_source.py` (`fetch_superior_ag`). No Playwright needed. |
| TGM | https://www.totalgrainmarketing.com | 200 | No | Growmark DTN module JS (`/DesktopModules/Growmark/DTN/...`); nav links `/Cash-Bids` (not fetched) and a Barchart marketplace portal (out of scope — do not scrape Barchart) | DTN Playwright — render check needed; one GET of `/Cash-Bids` in a later cycle. **Cycle 8:** `/Cash-Bids` fetched — 200, AgriCharts `cashbids.php` embed (`totalgrain.agricharts.com`, `groupby=ccommodity`) — same family as Cycle 7's six; `cashbids-js.php` static route to verify in a later cycle. The Barchart marketplace link was not fetched (out of scope). **Cycle 9:** resolved — `cashbids-js.php` static route proven, 362 rows, 24 locations; `fetch_tgm` added, reclassified `unknown → agricharts-embed`. |
| United Coop (`unitedcooperative.com`) | https://www.unitedcooperative.com | 200 | No | ATLAS DTN shell (`dtn-cashbid-tab` on homepage + bindlocation JS); no `cashbids.php` embed | DTN Playwright — render check needed. Still a different org from the Webster City, IA Bushel site (Cycle 5) |
| Ursa Farmers Coop | https://www.ursacoop.com | 200 | No — skeleton only | aghost/DTN page: "Local Cash Bids loading..." with commodity + delivery labels but **empty Basis/Cash cells** in static HTML; footer "Copyright DTN"; futures tables are static (futures, not cash bids) | DTN Playwright (`us_dtn_source.py`, parses rendered tables) — render check needed |
| Al-Corn | https://www.al-corn.com/cash-bids | 200 (→ `al-corn.com/cash-bids/`) | No | **Classic DTN**: `<div id="target">` + `tableOptions = { targetID: "target", companyID: 239483, … }; CashBidTable(tableOptions);` (+ CIHedging `CashBidWidget.js`/`ChartJS.js`) | DTN Playwright — **exact fit** for `us_dtn_source.py`. RESOLVED: was "uncertain"; no challenge page |
| Elite Octane | https://www.eliteoctane.net/cash-bids/ | 200 | No | `<div id="target">` + CIHedging `CashBidWidget.js`/`ChartJS.js`; no inline `tableOptions` — the loader initializes the widget | DTN Playwright (via CIHedging loader) — render check needed. RESOLVED: was "uncertain"; no challenge page |

### False positives — captcha / Cloudflare substring hits

- **Captcha strings** on Aurora (Divi contact-form CSS), Green Plains
  (Gravity Forms reCAPTCHA for a form), Ag State (form error strings),
  Al-Corn (Avada contact-form reCAPTCHA CSS), Elite Octane (cookie-policy
  text describing `cf_clearance` + a consent tool listing `recaptcha`).
  None is a challenge page: all five pages are full-size with on-topic
  titles and real content. Both "uncertain" sites are resolved on this
  evidence (see table).
- **Cloudflare strings** everywhere are `cdnjs.cloudflare.com` CDN asset
  hosts (jQuery, OwlCarousel, jQuery UI), same as the Cycle 1 caveat —
  not a challenge. No site returned a Cloudflare challenge page or a
  429 in this sweep.

### Static-HTML sites — no new parser needed

Ace Ethanol and Alliance Grain serve the Bushel `.cbmod` widget in
static HTML, and the existing generic parser already handles both
shapes: `parse_bushel_html` run against the saved `/tmp` HTML (no new
fetch) returns status ok — Ace 11 rows (Corn; month-year labels like
"Nov 2026"), Alliance 10 rows (Corn 5 + Soybeans 5; compact labels
like "Nov26"; location "Gibson City - West"). Synthetic fixtures +
tests added (no live HTML in the repo):
`tests/fixtures/bushel_ace_sample.html`,
`tests/fixtures/bushel_alliance_sample.html`,
`tests/test_bushel_cycle6_shapes.py` (2 tests; full bushel run
19 passed: 2 new + 17 existing). No `bushel_source.py` change was
needed. **Wiring still needed (coordinator):** `BUSHEL_SITES` entries
`ace_ethanol` + `alliance_grain` (verified shapes, USD, 7-col) and
`us_elevators_urls.toml` type changes `unknown → bushel` for both.

### New collector lead — AgriCharts `cashbids.php` embed (6 sites)

Agtegra, Heritage Cooperative, Linn Coop, Midway Coop, Ag State and
Superior Ag all embed a `<script src="…agricharts.com/inc/cashbids/
cashbids.php?filter=…&location=…&format=table&fields=…">` inside an
ATLAS "DTN CASHBID" tab/shell (Ag State has the embed with no DTN
string at all). The one endpoint probe (Agtegra's URL verbatim, 200,
`text/javascript`, 11.5 KB) returns a JS loader that
`document.write`s a second script (`cashbids-js.php`) — **no static
table, no `writeBidRow`**. So these six are JS-only and no existing
collector covers them: `us_agricharts_source.py` handles the
`writeBidRow` + `jsquote.php` pattern, not this embed. Per-site
embed hosts + location IDs (from page HTML, not prices): Agtegra
`sdwg.agricharts.com` / 3135; Heritage `heritagecoop.agricharts.com`
/ 21608; Linn `linncoop.agricharts.com` / filter=all (no location);
Midway `midwaycoop.agricharts.com` / 82270; Ag State
`agstate.agricharts.com` / 84205; Superior
`superiorag-cb-jsi.agricharts.com` / 82244.

**Resolved 2026-11-19 (Cycle 7) — static route proven, no Playwright
needed.** The loader is not a dead end: it XHRs a second URL
(`cashbids-js.php`, same host and query params as the embed URL plus
`noscript=1` / `acCnt=1` — the loader's own `widgetURL`, fetched
verbatim, one polite GET per site). That endpoint returns 200
`text/html` carrying a `<script id="cb-functions">` block with
`var bids = [...]` — a JSON array of location groups, each with a
`cashbids` array of bid objects (commodity, symbol, delivery
start/end, basis month, basis in integer cents, futures/change in
CBOT fractional cents, cash price $/bu + per-tonne, change in
dollars, per-row `location_name`, `require_login`, `active`). All
six sites verified live, one GET per `cashbids.php` loader + one per
`cashbids-js.php` URL, contact User-Agent. Row counts (structure
only, no prices): Agtegra 8 (Hecla, Corn); Heritage 15 (Ada; Corn 7,
Soybeans 7, Wheat SRW 1); Linn 51 (5 locations — ADM, Alburnett &
Springville Elevator, Cargill (Beans), Cargill (Starch), Ingredion;
#2 Yellow Corn 39, Soybeans 12); Midway 8 (location label "All
Locations"; Corn / Milo / Soybeans / Wheat, 2 each); Ag State 11
(Corn 6, Soybeans 5; `groupby=ccommodity`, location label "A.C.");
Superior 12 (CORN 8, SOYBEANS 4; `groupby=ccommodity`, location
"Princeton Central"). Generic collector built:
`GrainBids/grainbids/apps/api/app/platform/market_data/sources/cashbids_embed_source.py`
(`parse_cashbids_embed_html` / `fetch_cashbids_embed_site` /
`CASHBIDS_EMBED_SITES`, direct_dict shape), synthetic fixtures +
10 tests in `tests/test_cashbids_embed_collector.py` (no live fetch
in pytest), verified against the saved live responses (row counts
match). Two parser rules that matter: (1) the rendered
`table.cashbid_table` is NOT the parse target — Agtegra's table body
is empty client-filled rows, so the JSON payload is the only
reliable static route; (2) on the two `groupby=ccommodity` sites the
group name is a commodity, so the row location comes from
`location_name`, never the group name. Login-gated / inactive rows
are skipped and counted, never silently dropped. **Wiring still
needed (coordinator):** `CASHBIDS_EMBED_SITES` entries are in the
collector but not yet in `source_registry.py`; `us_elevators_urls.toml`
type changes `dtn → agricharts-embed` for the six (Ag State was
already mislabelled DTN in Cycle 1 — it has zero DTN strings).

### Other notes

- **Modern DTN widget:** Allied, Aurora and Green Plains load
  `content-services.dtn.com/ui-widgets/cash-bids-table-widget-1.0-
  latest.js`, not the classic `CashBidTable(tableOptions)` call.
  `us_dtn_source.py` waits for `#target table` after render, so a
  Playwright check must confirm the modern widget renders a table
  that collector can parse. Only Al-Corn has the classic inline
  `tableOptions` (companyID 239483).
- **StoneX is a new widget family:** Frontier Coop is the first
  StoneX site in the catalogue. No existing collector; later cycle.
- **Re-checks for a later cycle:** Ag Partners (503 "Site is offline"
  — may be transient maintenance, not necessarily dead); ALCIVIA,
  CRC, Five Star Coop, Bunge (all read timeouts — one GET each,
  no aggressive retry); Gateway FS sub-page
  (`/gatewayfs/agriculture/cash-bids`); TGM `/Cash-Bids`. (AGP's
  Bushel iframe target was fetched and verified in Cycle 7 — see the
  AGP row above.)
- **Wiring needed (not done here — new files only, no shared-file
  edits in this cycle):** `BUSHEL_SITES` entries for Ace Ethanol +
  Alliance Grain (AGP's entry was added in Cycle 7);
  `us_elevators_urls.toml` reclassifications
  (Ace/Alliance `unknown → bushel`, AGP `dtn → bushel`, Agtegra /
  Heritage / Linn / Midway / Superior / Ag State `dtn → agricharts-
  embed` — collector built in Cycle 7, `cashbids_embed_source.py`,
  still needs `source_registry.py` wiring, Gateway FS
  `dtn → unconfirmed`); Playwright render checks for the 12
  DTN-family JS-only sites (Allied, Aurora, Green Plains, CFS,
  Kanza, United `unitedcooperative.com`, Ursa, Al-Corn, Elite
  Octane, TGM + the two modern-widget unknowns); collector decision
  for the 1-site StoneX group (the 6-site cashbids.php group is
  resolved — collector built in Cycle 7).

## United States — Cycle 8 re-checks (2026-11-19)

Re-checked the 5 sites Cycle 6 left as timed-out/blocked (Ag Partners
503, ALCIVIA / CRC / Five Star / Bunge read timeouts), fetched the
two unfetched sub-pages (Gateway FS `/gatewayfs/agriculture/cash-bids`,
TGM `/Cash-Bids`), and re-fetched Frontier Coop plus the verbatim
StoneX iframe target from its saved Cycle 6 HTML. One polite GET per
URL, contact User-Agent, ~2 s spacing, 30 s timeout, no retries.
Raw HTML saved to `/tmp/cycle8/` scratch only, never the repo. No
prices are recorded here — row counts and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 9 | Every URL probed, including all 5 Cycle 6 failures |
| Static bid rows visible | **1** | Five Star Coop — 299 rows in a wpDataTables table (new pattern) |
| JS-only (widget present, no bid rows in static HTML) | 5 | Ag Partners (modern DTN), ALCIVIA + TGM (AgriCharts embed), Gateway FS sub-page (Next.js + DTN classes), Frontier (StoneX iframe) |
| No bid table at the probed URL | 2 | CRC (`/grain` is a generic services page; bids live on the homepage anchor), Bunge (still the locations archive) |
| StoneX component app shell, no static data | 1 | `stonehedge.stonex.com/component/bids` — JS app, data fetched at runtime |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Ag Partners | https://agpartners.net/cash-bids | 200 (→ `/cash-bids/`) | No | Modern DTN widget `content-services.dtn.com/ui-widgets/cash-bids-table-widget/cash-bids-table-widget-1.0-latest.js` | DTN Playwright — render check needed (same family as Allied / Aurora / Green Plains) |
| ALCIVIA | https://www.alcivia.com/cash-bids | 200 (→ `/wisconsin-grain-services/cash-bids-grain-wisconsin-grain/`) | No | AgriCharts `cashbids.php` embed (`alciviacoop.agricharts.com`, `filter=all`, `groupby=location`) | **Resolved 2026-11-19 (Cycle 9):** static route proven — one GET of the loader-derived `cashbids-js.php` URL (verbatim, `filter=all`, `groupby=location`, `months=11`) — 200, `var bids` JSON, **181 rows across 15 Wisconsin locations (Corn 90, Soybeans 75, Wheat 16)**. Generic collector `cashbids_embed_source.py` (`fetch_alcivia`). Reclassified `unknown → agricharts-embed` in `us_elevators_urls.toml`. No Playwright needed. |
| CRC | https://www.centralregioncoop.com/grain | 200 (→ `/grain/`) | No | Generic grain-services page; no widget, no iframe, no bid table. Cash Bids links point to the homepage anchor `/home/#cash-bids`. Site now brands as "Central United Cooperative" (assets on `centralunitedcoop.com`) | None at this URL. **Cycle 9:** homepage GET (200) — the anchor is actually `/home/#cash-bids-futures`, not `#cash-bids`. The Cash Bids section holds a lazy-loaded StoneX component iframe (no static `src`, no static bid rows) plus a DTN preconnect; no collector added. A later StoneX render check is the only open route (same family as Frontier Coop). **Cycle 10:** `ufcmn.com` (UFC, Batch 4) now redirects to this same `centralunitedcoop.com` homepage, and the Cash Bids section there carries a StoneX component iframe with a static `src` — UFC classified `unknown → stonex`, same StoneX family as Frontier/CRC. |
| Five Star Coop | https://www.fivestarcoop.com/cash-bids | 200 (→ `/grain-elevators-and-services/five-star-cash-bids/`) | **Yes — 299 rows, 21 locations, Corn 197 + Soybeans 102** | **wpDataTables** (new pattern): server-rendered `<table id="table_1">` in an Elementor wpdatatables widget; headers Location / Commodity / Delivery Periods / Bids / Basis / Change (+ hidden ID columns). Tables 2–4 on the same page are DTN futures (CBOT/CME/NYMEX), not cash bids. DTN futures widget also present; the "View Cash Bids Grid" button targets this table | **Resolved 2026-11-19 (Cycle 9):** plain-HTTP collector built (`wpdatatables_source.py`, `fetch_five_star_coop`, 43 tests); delivery labels normalised to `%b %Y`. Parser notes: delivery labels are inconsistent (`Dec26` vs `Dec 27`, `Apr 27` vs `April 27`); locations include third-party delivery points (e.g. AGP Mason City, Valero Charles City, Shell Rock Soy Processing) as well as Five Star elevators |
| Bunge | https://www.bungeag.com/cash-bids | 200 (→ `/locations/`) | No | Locations archive; "Cash Bids" is nav text only | Still do-not-add |
| Gateway FS (sub-page) | https://fscooperatives.com/gatewayfs/agriculture/cash-bids | 200 | No | Next.js app shell: `<div id="cash-bids-root" data-slug="gateway">` + DTN widget classes (`dtn_showCommoditiesSelect`, `dtn_showLocationsSelect`, …). The relative href was resolved against the Cycle 6 redirect target (`fscooperatives.com/gatewayfs`) | DTN Playwright — render check needed |
| TGM (`/Cash-Bids`) | https://www.totalgrainmarketing.com/Cash-Bids | 200 | No | AgriCharts `cashbids.php` embed (`totalgrain.agricharts.com`, `filter=all`, `groupby=ccommodity`) | **Resolved 2026-11-19 (Cycle 9):** static route proven — one GET of the loader-derived `cashbids-js.php` URL (verbatim, `filter=all`, `groupby=ccommodity`, `months=10`) — 200, `var bids` JSON, **362 rows across 24 Illinois/Indiana locations (Corn 120, Beans→Soybeans 120, Wheat 120, White Corn 2)**. Generic collector `cashbids_embed_source.py` (`fetch_tgm`). Reclassified `unknown → agricharts-embed` in `us_elevators_urls.toml`. The Barchart marketplace link in TGM's nav was not fetched (out of scope). No Playwright needed. |
| Frontier Coop | https://www.frontiercooperative.com/grain/cash-bids | 200 | No | StoneX iframe unchanged (same key as Cycle 6); inline JSON model still empty (`LocationRecords: null`, default date). ATLAS DTN shell (`/dtncashbidwidget/bindlocation`) also present on the page | See StoneX research below |

### StoneX research (Frontier Coop)

The StoneX widget is an `<iframe>` whose `src` is taken verbatim
from Frontier's page HTML:

`https://stonehedge.stonex.com/component/bids?key=RTD5A1BZ4L1339KAKG0STJT34WOKQEJ8&cols=name%2Cbasis%2Ccash%2Cchange&hideRows=false`

One polite GET of that URL (Cycle 6 precedent: one extra GET of a
distinct embedded endpoint taken verbatim from the page) returns
HTTP 200, `text/html`, 5.9 KB — a **JS app shell ("StoneX Hedge")**,
not data:

- Single bundled script (`/assets/index-B3HX-M8I.js`) + jQuery CDN;
  **zero `<table>` elements, zero bid rows, zero bid values** in
  static HTML.
- Content-Security-Policy `connect-src` lists
  `https://api.stonehedge.stonex.com` (plus SignalR
  `wss://stonehedge.service.signalr.net` and
  `https://auth.stonex.com`) — the bids are fetched at runtime from
  the StoneX API by the JS app, over a websocket-capable connection,
  behind StoneX auth.
- The widget key in the iframe URL is a public site key embedded in
  Frontier's public page HTML, not a credential; it identifies the
  widget instance, not a user.

**Conclusion: no static-data route exists for StoneX.** A collector
would need a browser render of the iframe, and the runtime API may
be auth-gated — that needs a Playwright render check in a later
cycle before any collector decision. Research only; no collector
built. StoneX remains a 1-site group (Frontier Coop).

### Follow-ups for a later cycle

- **Five Star Coop wpDataTables collector (done, Cycle 9):** new
  plain-HTTP pattern (299 rows, 21 locations) — parser built in
  `wpdatatables_source.py` (`fetch_five_star_coop`) with synthetic
  fixtures + 43 tests, delivery labels normalised to `%b %Y`;
  reclassified `dtn → wpdatatables` and wired into
  `source_registry.py` + `config.toml`.
- **ALCIVIA + TGM `cashbids-js.php` static-route checks (done, Cycle 9):**
  one GET each of the loader-derived URL (verbatim, as in Cycle 7)
  confirmed the `var bids` JSON payload serves rows — ALCIVIA 181
  rows / 15 locations, TGM 362 rows / 24 locations. Both added to
  `cashbids_embed_source.py` (`fetch_alcivia`, `fetch_tgm`),
  reclassified `unknown → agricharts-embed` in
  `us_elevators_urls.toml`, and wired into `source_registry.py` +
  `config.toml`.
- **CRC homepage (done, Cycle 9):** one GET of
  `https://www.centralregioncoop.com/` (200) — the anchor is
  actually `#cash-bids-futures`, and the section holds a lazy-loaded
  StoneX component iframe with no static bid rows. No collector
  added; a later StoneX render check is the only open route.
- **StoneX render check:** Playwright render of Frontier's page /
  the StoneX iframe to see whether rows load and whether the
  runtime API is reachable without auth.
- **Wiring:** all Cycle 8/9 follow-ups now wired — Five Star
  (`wpdatatables`), ALCIVIA + TGM (`agricharts-embed`). Gateway FS
  `dtn → unconfirmed` stands (sub-page is DTN-widget JS-only); Ag
  Partners stays DTN (modern widget).

## United States — Cycle 10 sweep (2026-11-19)

Probed the 19 genuinely unprobed `unknown` entries left in
`us_elevators_urls.toml` (Batch 4 homepages + CVA / Hull Coop /
Landus / Mercer Landmark). The 7 other `unknown` entries were
already resolved in the catalogue narrative and were NOT re-fetched:
Ace Ethanol + Alliance Grain (Bushel verified, Cycle 6), Bunge
(locations archive, do-not-add), CRC (StoneX-only, Cycles 8–9), CGB
(corporate page), United Coop `unitedcooperative.com` (ATLAS DTN
shell), Ursa Farmers Coop (DTN skeleton). One polite GET per URL,
contact User-Agent, ~2 s spacing, 30 s timeout, no retries. Raw HTML
saved to `/tmp/cycle10/` scratch only, never the repo. No prices are
recorded here — row counts and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 15 | Page served |
| Non-200 / empty / blocked | 4 | CVA 202 empty body; Hull Coop 404; Landus 429 Vercel checkpoint; Mercer Landmark 522 empty body |
| Static bid rows visible in static HTML | **2** | Synergy (4 rows) + Wheaton Grain (5 rows) — both Bushel `.cbmod` |
| JS-only / widget family identified, no static rows | 9 | PRO Coop (AgriCharts embed), Sunrise (classic DTN), Ray Carroll (DTN index.cfm iframes), UFC (StoneX iframe), Winchester (Bushel FCCP iframes), Skyland + Smithfield (Bushel FCCP, bids on sub-page), West-Con + Wheaton Dumont (AgriCharts-hosted, JS-filled widget) |
| No widget at the probed URL | 4 | Pro Ag (AgriCharts-hosted, nav link only), StateLine + The Andersons (sub-page linked), Star of the West (no bid page at all) |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| CVA | https://www.cvacoop.com/cash-bids | 202, empty body | — | — (no content; same as Cycle 1) | None — reclassified `unknown → unreachable` |
| Hull Coop | https://www.hullcoop.com/cash-bids | 404 | — | 404 page; its Cash Bids button links `/cashbids` (different slug) | None at this URL — stays `unknown`; one GET of `/cashbids` next. **Cycle 11 (2026-11-19):** 200 at `/cashbids` — AgriCharts `cashbids.php` embed (`hullcoopresp.agricharts.com`, `groupby=ccommodity`), no static rows; reclassified `unknown → agricharts-embed`, still disabled; `cashbids-js.php` check open. **Cycle 12 (2026-11-19):** `cashbids-js.php` 200, `var bids` JSON, 12 rows (Hull, IA — Corn 6, Soybeans 6); enabled, registry entry `hull_coop`. |
| Landus | https://www.landus.ag/businesses/grain/grain-bids | 429 | — | Vercel Security Checkpoint ("We're verifying your browser", JS required) | Blocked — reclassified `unknown → unreachable`, no retry |
| Mercer Landmark | https://www.mercerlandmark.com/cash-bids | 522, empty body | — | — (no content; same as Cycle 1) | None — reclassified `unknown → unreachable` |
| Pro Ag | https://www.proagfarmers.com | 200 | No | AgriCharts-hosted homepage (s3 `media.agricharts.com` assets, `quotelib.js`); no bid widget on homepage, nav links `/markets/cash.php`. Barchart marketplace link present — not followed (out of scope) | None at this URL — stays `unknown`; one GET of `/markets/cash.php` next. **Cycle 11 (2026-11-19):** 200 at `/markets/cash.php` — **78 static `writeBidRow` rows** (Corn / Soybeans / Wheat, 6 `h4` locations), all 78 match the existing `us_agricharts_source.py` `_WRITEBIDROW_RX` (verified against saved HTML); reclassified `unknown → agricharts` and **enabled**. |
| PRO Coop | https://procooperative.com | 200 (→ `/`) | No | **AgriCharts `cashbids.php` embed ×3** (`procooperative.agricharts.com`, locations 21297 `groupby=location` + 21302 `groupby=ccommodity`); also links `/cash-bids` and a `my.procooperative.com` login portal (not followed) | **Collector candidate (later cycle):** same family as Cycle 7/9's six + ALCIVIA/TGM — one GET of the loader-derived `cashbids-js.php` URL to prove the static `var bids` route. Reclassified `unknown → agricharts-embed`, still disabled. **Cycle 11 (2026-11-19):** 21297 Ayrshire view verified (6 Corn rows), enabled. **Cycle 12 (2026-11-19):** first 21302 embed verified (MANSON.IA, 12 rows — CORN 6, SOYBEANS 6), separate registry entry `pro_coop_21302`; second 21302 embed still unchecked. **Cycle 13 (2026-11-19):** second 21302 embed verified (MANSON.IA, 12 rows — CORN 6, SOYBEANS 6; the payload still carries `delivery_end` on every row despite the embed's fields list omitting it), separate registry entry `pro_coop_21302b` — the two embeds serve the same Manson view. |
| Ray Carroll | https://www.ray-carroll.com | 200 | No | **DTN index.cfm iframes ×4** (`index.cfm?show=87…layout=combined_table_by_location`, corn / soybeans / SRW wheat / milo); page tables are nav / futures / announcements; footer "Copyright DTN" | DTN Playwright — same `index.cfm` family as Great Lakes Grain / London Ag. Reclassified `unknown → dtn`, still disabled (render check + iframe/sub-page route open) |
| Skyland Grain | https://www.skylandgrain.com | 200 | No | **Bushel FCCP family**: `portal.bushelpowered.com/skyland` app links, `/cashbidssingle-` nav link; no `.cbmod` widget on the homepage, no bid table | Bushel — bids live on the `/cashbidssingle-` sub-page. Reclassified `unknown → bushel`, still disabled; one GET of `/cashbidssingle-` next. **Cycle 11 (2026-11-19):** 200 at `/cashbidssingle-` — the nav link target is literally `/cashbidssingle-` (empty ID) and serves a **14-location picker** (`CashBidsLocationID`s 2730–3621 in static HTML). The sweep worker reported no widget — **corrected by the coordinator's re-check: the page also serves a static 7-col `.cbmod` widget (Cunningham Area, 6 rows) and is now enabled with a registry entry** (see the Cycle 11 section). |
| Smithfield | https://smithfieldgrain.com | 200 | No | **Bushel FCCP family**: "Data provided by Bushel" footer, `portal.bushelpowered.com/smithfield` links; no `.cbmod` widget on the homepage — the only table is a futures table (Contract / Last / Chg) | Bushel — bids live on the FCCP cash-bids pages (nav: `/fccp-cash-bids-east-region-20249`). Reclassified `unknown → bushel`, still disabled; one GET of the East Region page next. **Cycle 11 (2026-11-19):** 200 at `/fccp-cash-bids-east-region-20249` — a **per-location link list** (NC / IN / OH / SC / VA, ~30 locations), no static rows; each location links `/cashbidssingle-<id>` and page JS iframes that target per location; probe one per-location target next (e.g. `/cashbidssingle-1666`, Bentonville); stays `bushel`, still disabled. |
| Star of the West | https://www.starofthewest.com | 200 | No | Milling-company homepage; zero cash-bid mentions, no grain/bid links at all | None — reclassified `unknown → none`, do not add |
| StateLine Coop | https://www.statelinecoop.com | 200 (→ `statelinecoop.com/`) | No | WordPress homepage, no challenge page this time (Cycle 1 reported a Cloudflare challenge; the reCAPTCHA strings now are form-related). No widget on homepage; nav links `/cash-bids`; page CSS references `table.cashbid_table`, hinting at an embed on the sub-page | None at this URL — stays `unknown`; one GET of `/cash-bids` next. **Cycle 11 (2026-11-19):** 200 at `/cash-bids` — AgriCharts `cashbids.php` embed (`statelinecoop.agricharts.com`, `groupby=location`) plus custom CSS for `table.cashbid_table`, no static rows; reclassified `unknown → agricharts-embed`, still disabled; `cashbids-js.php` check open. **Cycle 12 (2026-11-19):** `cashbids-js.php` 200, `var bids` JSON, 126 rows (11 locations — Corn 60, Soybeans 66); enabled, registry entry `stateline_coop`. |
| Sunrise | https://www.sunriseco-op.com | 200 | No | **Classic DTN**: `<div id="target">` + `CashBidTable(tableOptions)`, companyID 23043, CIHedging `CashBidWidget.js` / `ChartJS.js`, ATLAS DTN shell (`/dtncashbidwidget/bindlocation`) | **Exact fit for existing `us_dtn_source.py`** — reclassified `unknown → dtn` and **enabled** in `us_elevators_urls.toml` (the only enable in this cycle). Playwright render check still open |
| Synergy | https://www.synergycoop.com | 200 | **Yes — 4 rows, Corn 2 + Soybeans 2, Cameron, 6-col widget, dated header Nov 19, 2026** | Bushel `.cbmod` widget in static HTML (div/`ul` rows, `sixColumnsBigFirst`, not `<table>` rows) | **Collector candidate — ready:** the existing generic `bushel_source.py` parses the saved HTML with status ok (4 rows, Cameron, Corn 2 + Soybeans 2). Reclassified `unknown → bushel` and enabled; `BUSHEL_SITES` registry entry + `fetch_synergy()` added in Cycle 10 (3 tests) |
| The Andersons | https://www.andersonsgrain.com | 200 | No | Corporate Trade Group homepage, no widget; bid links `/locations/cash-bids/` + `/local-bids/locations-list/` | None at this URL — stays `unknown`; one GET of a bid sub-page next. Distinct from The Andersons Canada (DTN, Ontario section). **Cycle 11 (2026-11-19):** 200 at `/locations/cash-bids/` — proprietary GRAINweb "MyCashBids" **interactive location-picker** (choose a location + commodities, click Add; selections saved for next visit), no static rows, no recognizable embed; bids load via JS after a location is picked; needs a browser/API investigation; stays `unknown`, still disabled. **Cycle 14 (2026-11-19):** the `my-cash-bids` bundle fetched verbatim (1,079 bytes) — picker logic only, **no network call of any kind, no API route, no POST target**; confirmed browser-only (form POST + server render, possibly account-bound). See "The Andersons — GRAINweb investigation (Cycle 13)" + Cycle 14 addendum. Stays `unknown`, still disabled. **Cycle 15 (2026-11-19):** the locations-list page fetched verbatim — HTTP 200, 27,082 bytes; a plain 41-facility directory, 0 tables, 0 forms, no static bids. The Andersons is **closed for static collection**; only a rendered browser session (possibly account-bound) remains. **Cycle 16 (2026-11-19):** both confirmatory checks named in Cycle 15 are done — the Maumee facility page (HTTP 200) DOES carry static bid tables (3 tables: Corn 10 rows, Soybeans 10, Red Wheat 3), but the page states all market data is provided by Barchart Solutions, so the tables are licensed data and are NOT collected; the Ohio per-state list page (HTTP 200) is the same directory markup with no bids. The Andersons is now **fully closed** — the closure rests on licensing, not absence of static rows. See the Cycle 16 loose-ends section. |
| UFC | https://www.ufcmn.com | 200 (→ `centralunitedcoop.com/`) | No | **StoneX**: redirects to the Central United Cooperative homepage (same site/org as CRC); Cash Bids section is a StoneX component iframe (`stonehedge.stonex.com/component/bids`, `hideRows=true`). The DTN widget hits are map/weather widgets, not cash bids | StoneX — same family as Frontier Coop / CRC (JS app shell, no static route per Cycle 8 research). Reclassified `unknown → stonex`, still disabled; render check is the only open route |
| West-Con | https://www.west-con.com | 200 | No | AgriCharts-hosted homepage (s3 `media.agricharts.com` assets, `quotelib.js`); homepage cash widget is **JS-filled — values blank (`&nbsp;`) in static HTML**, location scaffolding Holloway / Appleton / Milbank / DLVD AGP Dawson / Aberdeen | None at this URL — stays `unknown`; one GET of `/markets/cash.php` next to confirm the `writeBidRow` route. **Cycle 11 (2026-11-19):** 200 at `/markets/cash.php` — **84 static `writeBidRow` rows** (Corn / Soybeans / DNS Wheat) — **but a parser gap:** delivery start/end are month-name labels (`'Dec 2026'`, `'Jan 2027'`), not `MM/DD/YYYY`, so the existing `us_agricharts_source.py` `_WRITEBIDROW_RX` matches **0/84**; reclassified `unknown → agricharts`, still disabled pending a small regex extension. |
| Wheaton Dumont | https://www.wdcoop.com | 200 | No | AgriCharts-hosted homepage (s3 `media.agricharts.com` assets, `quotelib.js`); homepage cash widget is **JS-filled — values blank in static HTML**, location scaffolding Wheaton / Dumont / Browns Valley / LaMars / Hankinson / Mantador / Sisseton (+ Britton, SD / Rutland, ND) | None at this URL — stays `unknown`; one GET of `/markets/cash.php` next to confirm the `writeBidRow` route. **Cycle 11 (2026-11-19):** dropped from the sub-page sweep to stay in the 9-GET budget (same AgriCharts pattern as West-Con); the `/markets/cash.php` probe is still open. |
| Wheaton Grain | https://www.wheatongrain.com | 200 | **Yes — 5 rows, Corn 2 + Soybeans 3, Chippewa Falls, 6-col widget** (Corn heads Bid as "Cash", Soybeans as "Bid") | Bushel `.cbmod` widget in static HTML — **but a new shape variant**: tabbed widget (`easyResponsiveTabs`, location tab "Chippewa Falls"), commodity headings are bare `h3.fcControls` with **no `div.cbCommodity` wrapper**, rows are `sixColumnsBigFirst` `ul`s | **Collector candidate — parser gap found:** the existing generic `bushel_source.py` returns "empty" against the saved HTML (`_parse_widget` only walks `div.cbCommodity` sections). A later cycle needs a small parser extension (fall back to `h3.fcControls` + following `ul`s when no `cbCommodity` divs exist). Reclassified `unknown → bushel`, still disabled; registry entry needed after the fix |
| Winchester Ag | https://www.winchesteragservice.com | 200 (→ `wheatongrain.com/fccp-winchester-locations-23823`) | No | **Bushel FCCP embeds ×2**: the redirect target is a Wheaton Grain FCCP location page with iframes `/cashbidssingle-3439?embed=y` + `/cashbidssingle-3440?embed=y`; no static rows at the probed URL | Bushel — Winchester Ag is a Wheaton Grain location, not an independent site. Reclassified `unknown → bushel`, still disabled; one GET per embed target next (Cycle 7 AGP precedent). **Cycle 11 (2026-11-19):** 200 at `/cashbidssingle-3439?embed=y` — **static Bushel `.cbmod` widget, 10 rows (Corn 5 + Soybeans 5, Winchester)**, standard wrapped `.cbCommodity` + 7-col `ul.sevenColumnsBigFirst` (FAC shape); existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 10 rows, against saved HTML; **enabled** (entry URL updated to the embed target); the 3440 target stays open. **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-3440?embed=y` — **static 7-col `.cbmod` widget, 5 rows (Soybeans only)** — but the location h2 is **"Georgetown"**: 3440 serves Wheaton's Georgetown location, not Winchester; **enabled** as a separate entry (`winchester_3440` + `fetch_winchester_3440()`). |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Synergy — parses cleanly.** `parse_bushel_html` run against the
  saved `/tmp/cycle10` HTML returns status ok: 4 rows, location
  Cameron, Corn 2 + Soybeans 2, widget header dated Nov 19, 2026.
  No `bushel_source.py` change needed for this shape.
- **Wheaton Grain — parser gap.** Same function against the saved
  HTML returns status "empty" ("cash-bid widget found but no bid
  rows parsed") even though 5 rows are visible in the widget: the
  tabbed widget has no `div.cbCommodity` sections, so
  `_parse_widget` finds nothing to walk. The rows use the same
  `sixColumnsBigFirst` `ul` pattern (header `ul.fcControlsSubHdr` +
  data `ul.fcControls1/2`, 6 cells each) under bare `h3.fcControls`
  headings. Fix in a later cycle: fall back to `h3.fcControls` +
  following `ul`s when the widget has no `cbCommodity` divs.
  (Synthetic fixture + test, no live HTML in the repo.)
- **Skyland Grain + Smithfield — confirmed unsupported at the
  probed URL.** `parse_bushel_html` returns status "unsupported"
  (no `.cbmod` widget or Delivery/Bid table) for both homepages,
  as expected — their bids live on FCCP sub-pages.

### Reclassifications applied (`us_elevators_urls.toml`)

`unknown → bushel`: Skyland Grain, Smithfield, Synergy, Wheaton
Grain, Winchester Ag. `unknown → agricharts-embed`: PRO Coop.
`unknown → dtn`: Ray Carroll, Sunrise (Sunrise also
`enabled = false → true` — classic DTN, covered by existing
`us_dtn_source.py`). `unknown → stonex`: UFC. `unknown → none`:
Star of the West. `unknown → unreachable`: CVA, Landus, Mercer
Landmark. Left `unknown` with a Cycle 10 comment: Hull Coop
(`/cashbids` slug to probe), Pro Ag / West-Con / Wheaton Dumont
(AgriCharts-hosted homepages — probe `/markets/cash.php`),
StateLine Coop (`/cash-bids` sub-page), The Andersons
(`/locations/cash-bids/` sub-page). The 7 skipped entries
(Ace Ethanol, Alliance Grain, Bunge, CRC, CGB, United Coop
`unitedcooperative.com`, Ursa Farmers Coop) were not touched.
All other entries stay `enabled = false` except Sunrise.

### Follow-ups for a later cycle

- **PRO Coop `cashbids-js.php` check:** one GET of the
  loader-derived URL (Cycle 7/9 pattern) to prove the static
  `var bids` route; if it serves rows, add `fetch_pro_coop` to
  `cashbids_embed_source.py` and enable.
- **Sub-page probes (one GET each):** Hull Coop `/cashbids`;
  Pro Ag / West-Con / Wheaton Dumont `/markets/cash.php`;
  StateLine `/cash-bids`; The Andersons `/locations/cash-bids/`;
  Skyland `/cashbidssingle-`; Smithfield
  `/fccp-cash-bids-east-region-20249`; Winchester embed targets
  `/cashbidssingle-3439` + `/cashbidssingle-3440` (on
  `wheatongrain.com`).
- **Wheaton Grain parser gap:** extend `bushel_source.py`
  `_parse_widget` for tabbed widgets without `div.cbCommodity`
  (see above), then add a `BUSHEL_SITES` entry for Wheaton Grain.
  Synergy's entry was added in Cycle 10 (`fetch_synergy`, 3 tests).
- **Playwright render checks:** Sunrise (classic DTN, enabled);
  Ray Carroll (DTN index.cfm iframes); UFC / StoneX family
  (Frontier, CRC, UFC — now 3 sites, still no static route).

## United States — Cycle 11 sub-page sweep (2026-11-19)

Probed the 9 sub-page follow-ups left by Cycle 10, one polite GET
each (User-Agent `GrainHub-Research/1.0`, 30 s timeout, no retries,
~2 s spacing) — 9 GETs total, budget respected. Skyland needed 2
GETs (homepage to recover the `/cashbidssingle-` target, then the
target itself), so Wheaton Dumont's `/markets/cash.php` probe was
dropped to stay in budget: same AgriCharts pattern as West-Con, and
it is still open. Raw HTML saved to `/tmp/cycle11/` scratch only,
never the repo. No prices are recorded here — row counts and widget
patterns only. Classify only; no collectors were built by the sweep
worker — the coordinator added registry entries for the three
collector-ready sites afterwards (Winchester, Skyland, Wheaton Grain;
see below).

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 9 | Every probed sub-page served (no 404s, blocks, or empty bodies this cycle) |
| Static bid rows visible in static HTML | **4** | Pro Ag (78 `writeBidRow` rows), West-Con (84 `writeBidRow` rows), Winchester 3439 (10 Bushel `.cbmod` rows), Skyland (6 Bushel `.cbmod` rows — corrected by coordinator re-check, see below) |
| Embed / loader pattern, no static rows | 2 | Hull Coop + StateLine Coop (AgriCharts `cashbids.php` embed) |
| Location picker / link list, no static rows | 1 | Smithfield (per-location link list) — Skyland moved to static rows (correction below) |
| Interactive JS app, no static rows | 1 | The Andersons (GRAINweb "MyCashBids" location-picker) |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Hull Coop | https://www.hullcoop.com/cashbids | 200 (→ `/cashbids/`) | No | **AgriCharts `cashbids.php` embed** (`hullcoopresp.agricharts.com`, `groupby=ccommodity`, `format=table`, 8-month window); WordPress/Elementor page, no bid table in static HTML | AgriCharts embed — same family as Cycle 7/9's six + ALCIVIA/TGM/PRO Coop. Reclassified `unknown → agricharts-embed`, still disabled; one GET of the loader-derived `cashbids-js.php` URL to prove the static `var bids` route. **Cycle 12 (2026-11-19):** proven — 200, `var bids` JSON, 12 rows (Hull, IA — Corn 6, Soybeans 6); enabled. |
| Pro Ag | https://www.proagfarmers.com/markets/cash.php | 200 | **Yes — 78 rows** (Corn / Soybeans / Wheat, 6 `h4` locations: Brandon, CLARISSA, EAGLE BEND / EAGLE BEND WEST, GARFIELD, Hoffman, PARKERS PRAIRIE) | Classic AgriCharts `writeBidRow()` calls inline in static HTML, `MM/DD/YYYY` delivery dates | **Collector-ready:** all 78 calls match the existing `us_agricharts_source.py` `_WRITEBIDROW_RX` (verified against saved HTML). Reclassified `unknown → agricharts` and **enabled** (entry URL updated to `/markets/cash.php`); no registry adapter needed — the orchestrator drives `fetch_us_agricharts(url, name)` from the toml |
| West-Con | https://www.west-con.com/markets/cash.php | 200 | **Yes — 84 rows** (Corn / Soybeans / DNS Wheat, location param `All`) | Classic AgriCharts `writeBidRow()` calls inline in static HTML — **but delivery start/end are month-name labels** (`'Dec 2026'`, `'Jan 2027'`, 10 distinct), not `MM/DD/YYYY` | **Parser gap found:** the existing `_WRITEBIDROW_RX` requires `MM/DD/YYYY` dates and matches **0/84**. Reclassified `unknown → agricharts`, still disabled; a small regex extension (accept month-name delivery labels) unblocks it. **Cycle 12 (2026-11-19):** regex extended to accept month-name labels; verified **84/84** against the saved Cycle 11 HTML (10 distinct labels, start == end on all rows). **Enabled** (toml entry flipped `enabled = true`); no registry adapter needed — the orchestrator drives `fetch_us_agricharts` from the toml. 7 tests in `test_us_agricharts_source.py`. |
| StateLine Coop | https://www.statelinecoop.com/cash-bids | 200 (→ `statelinecoop.com/cash-bids/`) | No | **AgriCharts `cashbids.php` embed** (`statelinecoop.agricharts.com`, `groupby=location`) on a WordPress page, plus custom CSS for `table.cashbid_table` (the Cycle 10 hint was right); no bid table in static HTML. Footer: "All market data is provided by Barchart Solutions" (attribution only — no Barchart link followed) | AgriCharts embed — same family as Hull Coop / PRO Coop. Reclassified `unknown → agricharts-embed`, still disabled; `cashbids-js.php` check open. **Cycle 12 (2026-11-19):** proven — 200, `var bids` JSON, 126 rows (11 locations — Corn 60, Soybeans 66); enabled. |
| The Andersons | https://www.andersonsgrain.com/locations/cash-bids/ | 200 | No | Proprietary GRAINweb **"MyCashBids" interactive location-picker**: "Customize Your Cash Bids! Select the location first, and then the commodities…" with an Add-commodity form (`data-ui="add-commodity"`), a "Bid and Basis Charts" modal, and an empty-src `chartFrame` iframe; links to `/local-bids/locations-list/` and `/local-bids/locations/` | No recognizable embed and no static rows; bids load via JS after a location is picked. Stays `unknown`, still disabled; needs a browser/API investigation (distinct from The Andersons Canada, DTN, in the Ontario section). **Cycle 15 (2026-11-19):** the locations-list page (`/local-bids/locations-list/`) fetched verbatim — HTTP 200, 27,082 bytes; a plain 41-facility directory, 0 tables, 0 forms, no static bids. The Andersons is **closed for static collection**; only a rendered browser session remains. **Cycle 16 (2026-11-19):** both confirmatory checks named in Cycle 15 are done — the Maumee facility page (HTTP 200) DOES carry static bid tables (3 tables: Corn 10 rows, Soybeans 10, Red Wheat 3), but the page states all market data is provided by Barchart Solutions, so the tables are licensed data and are NOT collected; the Ohio per-state list page (HTTP 200) is the same directory markup with no bids. The Andersons is now **fully closed** — the closure rests on licensing, not absence of static rows. See the Cycle 16 loose-ends section. |
| Skyland Grain | https://www.skylandgrain.com/cashbidssingle- | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area), widget header dated Nov 19, 2026 | The nav link target is literally **`/cashbidssingle-` (empty ID)** and serves a **14-location picker** (`CashBidsLocationID`s 2730–3621 in static HTML) **AND** a static 7-col Bushel `.cbmod` widget for the default location (Cunningham Area). The sweep worker reported "no `.cbmod` widget, no bid rows" — **wrong; corrected by the coordinator's re-check** (a fresh GET parses ok, 6 rows; the saved `/tmp/cycle11` HTML parses ok too). Same canonical trailing-dash pattern as Williams Gin (Cycle 5) | **Collector-ready:** the existing generic `bushel_source.py` parses it with no changes. **Enabled** (entry URL updated to `/cashbidssingle-`); `BUSHEL_SITES` registry entry + `fetch_skyland()` added in Cycle 11 (6 tests). Per-location `/cashbidssingle-<id>` targets still open. **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-2730` — **static 7-col `.cbmod` widget, 6 rows (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area)** — 2730 is Cunningham Area's own per-location ID, so the rows duplicate the default page; **enabled** as a separate entry (`skyland_2730` + `fetch_skyland_2730()`); 13 picker IDs still open. **Cycle 13 (2026-11-19):** 6 more per-location targets probed (2731 Conlen - Hartley, 2734 Etter, 2740 Moscow/Dermot/Kismet/Pleasant Valley, 2742 Johnson - Ulysses - N Sublette, 2754 Olton Area, 2761 Elkhart - Hough - Rolla Area) — all 200, all static 7-col `.cbmod` widgets; **enabled** as separate entries; 7 picker IDs still open (2763, 2766, 2770, 2771, 2778, 3370, 3621). **Cycle 14 (2026-11-19):** the last 7 per-location targets probed (2763 Satanta - Ryus, 2766 Spearman - Gruver - Texline, 2770 Sunray Area, 2771 Kendall - Midway - Lydia, 2778 Buckeye - Syracuse, 3370 Hugoton, 3621 Vilas - Walsh) — all 200, all static 7-col `.cbmod` widgets; **enabled** as separate entries; **all 14 picker IDs now verified — the Skyland sweep is complete**. |
| Smithfield | https://smithfieldgrain.com/fccp-cash-bids-east-region-20249 | 200 | No | **Bushel FCCP per-location link list** (NC / IN / OH / SC / VA, ~30 locations, e.g. Bentonville 1666, Bladenboro 1725); no static rows, no `.cbmod` widget; page JS iframes `/cashbidssingle-<locId>` per location | Bushel — bids live on the per-location `/cashbidssingle-<id>` targets. Stays `bushel`, still disabled; probe one per-location target next (e.g. `/cashbidssingle-1666`, Bentonville). **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-1666` — **static 7-col `.cbmod` widget, 3 rows (Soybeans 1, Wheat 1, Corn 1, Bentonville, NC)**; **enabled** as a separate per-location entry (`smithfield_bentonville` + `fetch_smithfield_bentonville()`); ~29 East Region locations still open. **Cycle 13 (2026-11-19):** 4 more per-location targets probed (1725 Bladenboro, 1667 Bladenboro Feed Mill, 2294 Chadbourn, 1668 Clarkton) — all 200, all static 7-col `.cbmod` widgets; **enabled** as separate entries; 26 East Region locations still open. **Cycle 14 (2026-11-19):** 6 more per-location targets probed (1669 Clinton, 1670 Hobbsville, 1671 Kinston, 1672 LaGrange, 1673 Morgan's Corner, 1674 Mount Olive) — all 200, all static 7-col `.cbmod` widgets; **enabled** as separate entries; 20 East Region locations still open. **Cycle 15 batch B (2026-11-19):** 6 more per-location targets probed (1683 Creswell, 1684 Warsaw, 1685 Harpster, 1686 Morral, 1687 Darlington, 1688 Lake City) — all 200, all static 7-col `.cbmod` widgets, all widget headers dated Nov 19, 2026; **enabled** as separate entries; 14 East Region locations still open after this batch (1675, 1676, 1678, 1679, 1681, 1682, 1689, 1690, 1691, 2064, 2065, 2066, 2067, 2179) — the sibling batch A is probing 1675–1682 in parallel. **Cycle 15 batch A (2026-11-19):** 5 of the 6 batch-A targets verified (1676 Red Springs, 1678 Walstonburg, 1679 Weeksville, 1681 The Chief Feed Mill, 1682 Laurinburg Feed Mill) — all 200, all static 7-col `.cbmod` widgets, all headers Nov 19, 2026; **enabled** as separate entries. 1675 Raeford returned 200 with an **empty widget, 0 rows — NOT registered**, re-probe later. Combined, Cycle 15 leaves 8 East Region locations still open (1689, 1690, 1691, 2064, 2065, 2066, 2067, 2179) plus the Raeford re-probe. **Cycle 16 (2026-11-19):** 6 more per-location targets probed (1689 Nichols, 1690 Petersburg, 1691 Waverly, 2064 Kinston JCH, 2065 Jones County, 2066 Deep Run JCH) — all 200, all static 7-col `.cbmod` widgets, all widget headers dated Nov 19, 2026; **enabled** as separate entries; Waverly is the fattest Smithfield page yet (7 rows, incl. the first Grain Sorghum on a Smithfield page). Only 2 East Region locations still open (2067, 2179) plus the Raeford re-probe. **Cycle 16 loose ends (2026-11-19):** both done — 2067 Lapaz (2 Corn rows, fresh Nov 19 header) and 2179 Hamer (1 Soybeans row, header a day stale, Nov 18) verified and **enabled** as separate entries (`smithfield_lapaz`, `smithfield_hamer`); Raeford (1675) re-probed and **still empty** (0 rows, status "empty", second probe in a row) — **NOT registered**, and no further re-probe is planned. The 31-location East Region list is now fully covered except Raeford. See the Cycle 16 loose-ends section. |
| Winchester Ag | https://www.wheatongrain.com/cashbidssingle-3439?embed=y | 200 | **Yes — 10 rows** (Corn 5 + Soybeans 5, Winchester), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows (Delivery / Bid / Basis / Futures / Change / Futures Month / Last Trade) — the FAC shape, not Wheaton Grain's tabbed variant | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 10 rows, against saved HTML — no parser change needed. **Enabled** (entry URL updated to the embed target); `BUSHEL_SITES` registry entry + `fetch_winchester()` added in Cycle 11 (6 tests). The 3440 target stays open. **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-3440?embed=y` — **static 7-col `.cbmod` widget, 5 rows (Soybeans only)** — but the location h2 is **"Georgetown"**: 3440 serves Wheaton's Georgetown location, not Winchester; **enabled** as a separate entry (`winchester_3440` + `fetch_winchester_3440()`). |
| Wheaton Dumont | — (not probed) | — | — | Dropped to stay in the 9-GET budget (Skyland took 2 GETs); same AgriCharts-hosted pattern as West-Con | Still open: one GET of `https://www.wdcoop.com/markets/cash.php` next. **Cycle 12 (2026-11-19):** one GET of `https://www.wdcoop.com/markets/cash.php` returned 200 with **43 static `writeBidRow` rows** (Corn 18 / Soybeans 16 / Spring Wheat 9, 8 `<h4>` locations) — but delivery labels are the SHORT month form (`'Nov 26'`, `'Jan 27'`, 6 distinct), so the Cycle 12 regex needed a second extension (2-digit years) before it matched; verified **43/43** against saved HTML, 6 rows span two adjacent months. Reclassified `unknown → agricharts` and **enabled** (entry URL updated to `/markets/cash.php`); no registry adapter needed. |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Winchester 3439 — parses cleanly.** `parse_bushel_html` run
  against the saved `/tmp/cycle11` HTML returns status ok: 10 rows,
  location Winchester, Corn 5 + Soybeans 5, widget header dated Nov
  19, 2026. No `bushel_source.py` change needed for this shape
  (the Cycle 11 tabbed-widget fix for Wheaton Grain is not needed
  here — this is the standard wrapped variant).
- **Pro Ag — matches the existing collector regex.** The
  `us_agricharts_source.py` `_WRITEBIDROW_RX` applied to the saved
  HTML matches 78/78 data calls. No code change needed.
- **Skyland — parses cleanly (coordinator correction).** The sweep
  worker reported no widget on `/cashbidssingle-`, but the saved
  `/tmp/cycle11` HTML and a fresh coordinator GET both return status
  ok from `parse_bushel_html`: 6 rows, location Cunningham Area
  (Corn 2, Milo 1, Red Wheat 2, Soybeans 1). The page serves a
  14-location picker AND a default-location widget; the worker
  evidently only inspected the picker. No `bushel_source.py` change
  needed. Registry entry + `fetch_skyland()` added by the
  coordinator (6 tests).
- **West-Con — parser gap.** The same regex matches 0/84 data
  calls: every call's delivery start/end are month-name labels
  (`'Dec 2026'`, …) where the regex requires `MM/DD/YYYY`. The
  rest of the call shape matches (commodity, basis, weight,
  rowclass, chartsym, `quotes['SYMBOL']` futures symbol). Fix in a
  later cycle: accept month-name delivery labels in
  `_WRITEBIDROW_RX` (and decide how the collector dates a
  month-only delivery window). No live HTML in the repo.

### Reclassifications applied (`us_elevators_urls.toml`)

`unknown → agricharts`: Pro Ag (also `enabled = false → true`),
West-Con. `unknown → agricharts-embed`: Hull Coop, StateLine Coop.
Winchester Ag: entry URL updated to the verified embed target
(`wheatongrain.com/cashbidssingle-3439?embed=y`) and `enabled =
false → true`. Skyland Grain: entry URL updated to
`/cashbidssingle-` and `enabled = false → true` (coordinator
correction — static widget found on re-check). The Andersons,
Smithfield: type unchanged (`unknown` / `bushel`), comments updated
with the Cycle 11 findings, still disabled. Wheaton Dumont: untouched
(still open). All other entries unchanged.

### The Andersons — GRAINweb investigation (Cycle 13)

Saved-HTML-only analysis — **no new HTTP requests**. Source: the
Cycle 11 save `/tmp/cycle11/andersons_cashbids.html` (23,263 bytes,
655 lines, saved 2026-11-19 06:10) of
`https://www.andersonsgrain.com/locations/cash-bids/` (HTTP 200 in
Cycle 11). Every string below is verbatim from that file; the
bundled JS was **not** fetched, so what the picker calls after a
location is picked is still unknown.

- **No static bid rows.** The file contains no bid table and no
  price rows: a case-insensitive search for `<table`, `price`,
  `basis`, or `$` followed by a digit matches exactly one line —
  the modal heading `<h2>Bid and Basis Charts</h2>`. No
  `writeBidRow`, `.cbmod`, `cashbids.php`, or embed markup anywhere.
- **What the page is:** a "MyCashBids" picker. Heading `My Bids`
  plus the instruction "Customize Your Cash Bids! Select the
  location first, and then the commodities you want from the
  drop-down menu below, and then click the \"add\" button. You may
  add as many bids from as many locations as you want. Your bid
  selections will be saved the next time you come to this page."
- **The only form:** `<form action="/locations/cash-bids/Add"
  method="POST" data-ui="location-selector-form">` with a hidden
  `__RequestVerificationToken` field (value not reproduced here),
  a location `<select data-ui="location" id="SelectedLocation"
  name="SelectedLocation">` with 18 options, an empty commodities
  `<select name="SelectedCommodity" data-ui="commodity"></select>`
  (populated client-side, see below), and a submit `<button
  type="submit" class="Button" data-ui="add-commodity">Add</button>`.
  The form posts a saved selection; it does not itself return bids.
- **Locations and commodities are inline data, not an API call.**
  A single inline script defines `ANDERSONS_GRAIN_LOCATIONS`, a
  JSON map from numeric location ID to commodity list, and the
  location `<select>` carries the same 18 options: 40 Toledo -
  Edwin Dr, 948 Toledo - Kuhlman Dr, 1009 Metamora, 1027
  Greenville, 1052 Auburn, 1062 Hemlock, 1069 Oakley, 1076
  Standish, 1091 Reading, 1098 White Pigeon, 1108 Dunkirk, 1118
  Oakville, 1138 Delphi, 1145 Clymers, 1162 Denison, 1396 Maumee,
  12194 Albion, 55689 Port William. Commodities per location are
  Corn everywhere; Soybean and Red Wheat at most locations; White
  Wheat only at Auburn, Hemlock, Oakley, Standish; Corn-only at
  Greenville, Clymers, Denison, Albion. The commodity dropdown is
  empty in the HTML and is filled from this map by JS — so the
  picker needs JS even before any bid loads.
- **Script `src`s (6, all of them):**
  `/static/scripts/modernizr.js`,
  `/static/scripts/polyfill/arrayFind.js`,
  `https://use.typekit.net/sfk3nih.js`, `polyfill/matchmedia.js`
  (IE9 conditional only), `/Static/js/site.js`, and
  `/bundles/js/my-cash-bids?v=C0G6bVc73LyEBcO1OYpPFy7jWEA7shnNPkHnIdQ0d7o1`
  — the last is the picker logic. The matching CSS bundle is
  `/bundles/css/my-cash-bids?v=Z0gEAIxl_Ix7Ps_PNW2JNgQy7YDRTeUKB1NYmWVY_Hs1`.
  No `grainweb.com` script is loaded.
- **No XHR/fetch/API strings in the HTML.** No occurrence of
  `fetch(`, `XMLHttpRequest`, `.ajax(`, `axios`, or `getJSON`; the
  only `load(` is `Typekit.load()`. No `/api/`, `.json`, or
  `endpoint` string; the only `api` substrings are the
  `data-google-api-key` attribute name and
  `fonts.googleapis.com`. The bid-loading endpoint, if one exists,
  is named only inside the `my-cash-bids` bundle, which is not in
  the saved HTML.
- **Iframes (2):** `<iframe id="chartFrame" src="" frameborder="0"
  width="965" height="650">` inside the `#ModalCashBids1` "Bid and
  Basis Charts" modal — `src` empty, set by JS when a chart is
  opened — and the Google Tag Manager noscript iframe
  (`https://www.googletagmanager.com/ns.html?id=GTM-M6N6DVS`).
  No bid iframe.
- **GRAINweb is links only.** `https://grainweb.com/` appears as a
  plain nav/footer link (twice) and `/tools/grainweb/` as a "GRAINweb
  FAQ" link. No GRAINweb embed, script, or iframe.
- **Other hooks:** `data-ui` attributes are `accordion-menu`,
  `background-image`, `header`, `primary-menu`,
  `location-selector-form`, `location`, `commodity`,
  `add-commodity`; `data-state="off"`, `data-status="disabled"`.
  Login links point to
  `/login?returnUrl=%2flocations%2fcash-bids%2f` — the page served
  200 anonymously in Cycle 11, but saved selections may be
  account-bound. Related links on the page:
  `/local-bids/locations-list/` and `/local-bids/locations/`.
  Inline scripts besides the location map: the GTM loader
  (`GTM-M6N6DVS`), a `gaCustom` dimensions block, and
  `var SEARCH_PAGE_URL = '/search/';` — none bid-related.

**Verdict: browser-only.** No static route exists on this page and
no API endpoint is named anywhere in the saved HTML — the picker
cannot be collected from static HTML, and the endpoint it calls
(if any) lives inside the un-fetched `my-cash-bids` bundle. Next
probe for a later cycle (one GET): read the bundle verbatim at
`https://www.andersonsgrain.com/bundles/js/my-cash-bids?v=C0G6bVc73LyEBcO1OYpPFy7jWEA7shnNPkHnIdQ0d7o1`
and grep it for the URL the picker posts to — if it names a JSON
route, that route is the API candidate to try next; if it posts
only to `/locations/cash-bids/Add`, the only remaining path is a
rendered browser session. Secondary candidate (one GET):
`https://www.andersonsgrain.com/local-bids/locations-list/` — it
may list per-location pages. Stays `unknown`, still disabled.
Distinct from The Andersons Canada (DTN, Ontario section).
**Cycle 15 (2026-11-19):** the locations-list page fetched
verbatim — HTTP 200, 27,082 bytes, saved to
`/tmp/cycle15/andersons_locations_list.html`. It is a plain
per-location directory (41 facility links in 10 state/province
groups, no login wall), with **0 tables, 0 forms, and no
`writeBidRow`, `.cbmod`, or `cashbids.php` anywhere** — no static
bids. The Andersons is **closed for static collection**; only a
rendered browser session (possibly account-bound) remains. Full
findings in the Cycle 15 section below.

**Cycle 16 (2026-11-19) — confirmatory checks done, closure
now rests on licensing.** Both low-odds checks named in Cycle 15
were fetched (one GET each, HTTP 200, saved to `/tmp/cycle16/`):
the Maumee facility page
(`https://www.andersonsgrain.com/locations/oh/maumee/`) and the
Ohio per-state list page
(`https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/`).
The Ohio list page is the same directory markup as the master
list — body lists the same 7 Ohio facilities, no bids. The
Maumee page is the surprise: alongside the expected facility
info (Hours, Discount Schedules, DP/Storage Rates, Contacts,
About This Facility, Maps embed) it carries **3 static
`styled-table` bid tables** (Corn 10 delivery rows, Soybeans
10, Red Wheat 3; columns Delivery / Bid / Basis / Futures /
Chg / Symbol / Last Trade) — static bid rows DO exist on
Andersons facility pages. But the page carries a Barchart
disclaimer ("All market data is provided by Barchart
Solutions"), so the tables are **Barchart-licensed data** and
are deliberately NOT collected, NOT registered, and no toml
entry was added. The Andersons is therefore **fully closed**:
no static-collection path remains that is in scope — the
facility tables are licensed, the picker is a JS form POST
(possibly account-bound), and the list pages are directories.
No new probe exists: the other 40 facility pages would serve
the same Barchart-licensed tables (do not probe them — the
answer is already known and the data is out of scope). Full
findings in the Cycle 16 loose-ends section below.

**Cycle 14 addendum (2026-11-19) — bundle fetched verbatim, thread
closed.** One GET of the bundle URL above (HTTP 200, 1,079 bytes,
saved to `/tmp/cycle14/andersons_my_cash_bids.js`). It is a
Browserify wrapper defining exactly one module (83); the modules it
requires (`./mod/master-page`, `./mod/get-ui`,
`./mod/accordion-menu`, `jquery`) are not defined in this file —
they come from a shared bundle loaded separately on the page
(`site.js` is the other page script). The picker's entire logic,
verbatim:

```js
n("./mod/master-page");
var u=n("jquery"),r=n("./mod/get-ui"),f=r("location"),t=r("commodity"),i=r("add-commodity"),e=n("./mod/accordion-menu");
e("accordion-menu");
i.prop("disabled",!0);i.hide();t.hide();
f.change(function(){
  var f=u(this).val(),r=(ANDERSONS_GRAIN_LOCATIONS||{})[f]||[],n;
  if(!r.length){t.html("");t.hide();i.prop("disabled",!0);i.hide();return}
  for(t.html('<option value="">All Commodities<\/option>'),n=0;n<r.length;n++)t.append("<option>"+r[n]+"<\/option>");
  t.show();i.prop("disabled",!1);i.show()
})
```

Findings, all verbatim strings from the bundle:

- **No network call of any kind.** No `fetch(`, `XMLHttpRequest`,
  `$.ajax`, `axios`, `getJSON`, `.post(`, or `.get(` — a grep for
  those plus `/api/`, `.json`, and `http` returns nothing except
  the single identifier `ANDERSONS_GRAIN_LOCATIONS`.
- **No POST target in the bundle.** The form's
  `/locations/cash-bids/Add` action is known only from the saved
  Cycle 11 HTML; the bundle never names it, and it names no other
  URL at all.
- **No token/CSRF handling.** No `__RequestVerificationToken`,
  `antiForgery`, `csrf`, or `token` string anywhere (the hidden
  token field is in the HTML form only). No credential-like string
  of any kind in the bundle (secret scan: 0 matches).
- **What the picker actually does:** on location change it reads
  the inline global `ANDERSONS_GRAIN_LOCATIONS` (location ID →
  commodity list, embedded in the page HTML per Cycle 13) and
  populates the commodity `<select>` with an `All Commodities`
  option plus one `<option>` per commodity, then enables/shows the
  Add button. That is the whole bundle — it wires the dropdowns and
  nothing else. Bid loading, if any, happens only after the form
  POSTs and the server renders the saved-selection page; there is
  no client-side bid fetch to intercept.

**Verdict (final): confirmed browser-only.** No static-data route
and no public API exist for The Andersons GRAINweb picker — the
only remaining paths are (a) a rendered browser session that picks
a location, submits the form, and reads the server-rendered saved
bids (possibly account-bound — the page links
`/login?returnUrl=%2flocations%2fcash-bids%2f`), or (b) the
secondary candidate `/local-bids/locations-list/`, which may list
per-location pages with static bids. No collector can be built from
static fetches. Stays `unknown`, still disabled.

### Follow-ups for a later cycle

- **Embed `cashbids-js.php` checks (one GET each):** Hull Coop
  (`hullcoopresp.agricharts.com`) and StateLine Coop
  (`statelinecoop.agricharts.com`), same loader-derived route as
  PRO Coop — if the static `var bids` JSON serves, add
  `fetch_` entries to `cashbids_embed_source.py` and enable.
  (Two embed sites now wait on this check: Hull Coop and StateLine
  Coop. PRO Coop's `cashbids-js.php` route was verified in Cycle 11
  by a parallel worker — see its `us_elevators_urls.toml` entry,
  now enabled.) **Done in Cycle 12 (2026-11-19):** both proven —
  Hull 12 rows (Corn 6, Soybeans 6), StateLine 126 rows (Corn 60,
  Soybeans 66) — both enabled with registry entries; the PRO Coop
  first 21302 embed was proven in the same cycle (MANSON.IA,
  12 rows), second 21302 embed still open.
- **Per-location Bushel probes (one GET each):** Skyland
  `/cashbidssingle-<id>` (14 IDs on file, e.g. 2730 — the default
  location is now covered by `fetch_skyland()`); Smithfield
  `/cashbidssingle-<id>` (e.g. 1666 Bentonville); Winchester
  `/cashbidssingle-3440?embed=y`.
- **West-Con regex fix:** extend `_WRITEBIDROW_RX` in
  `us_agricharts_source.py` for month-name delivery labels, then
  enable West-Con (and re-check Wheaton Dumont's
  `/markets/cash.php` first — it may share the same date format).
- **Wheaton Dumont `/markets/cash.php` probe:** one GET, still
  open (dropped from this sweep on budget).
- **The Andersons browser/API investigation:** the GRAINweb
  "MyCashBids" picker needs a rendered session or an API route
  found in its JS bundles; no static route exists. **Cycle 13
  (2026-11-19):** investigated from the saved Cycle 11 HTML — see
  "The Andersons — GRAINweb investigation (Cycle 13)" above;
  verdict browser-only, next probe is one GET of the
  `my-cash-bids` bundle. **Cycle 14 (2026-11-19): bundle fetched
  verbatim — done, thread closed:** no network call, no API route,
  no POST target in the bundle; confirmed browser-only (form POST
  + server render, possibly account-bound). Only remaining probe
  is `/local-bids/locations-list/` (one GET) or a rendered browser
  session.
- **Registry wiring (coordinator):** Pro Ag (`agricharts`) and
  Winchester Ag (`bushel`, `BUSHEL_SITES` + `fetch_` function)
  were enabled in the toml this cycle; their registry entries are
  still to be added.

## United States — Cycle 12 per-location Bushel probes (2026-11-19)

Probed the three per-location `/cashbidssingle-<id>` targets left
open by Cycle 11, one polite GET each (User-Agent
`GrainHub-Research/1.0`, 30 s timeout, no retries, ~2 s spacing) —
3 GETs total, budget respected. All three served 200 with a static
Bushel `.cbmod` widget and parsed cleanly with the existing generic
`bushel_source.py` parser — no parser change needed. Raw HTML saved
to `/tmp/cycle12/` scratch only, never the repo. No prices are
recorded here — row counts and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 3 | Every probed per-location target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **3** | Winchester 3440 (5 Soybeans rows, Georgetown), Skyland 2730 (6 rows, Cunningham Area), Smithfield 1666 (3 rows, Bentonville, NC) |
| New parser gap | 0 | All three are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) — Wheaton Grain's tabbed variant was not needed anywhere |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Winchester Ag — Georgetown (3440) | https://www.wheatongrain.com/cashbidssingle-3440?embed=y | 200 | **Yes — 5 rows** (Soybeans 5), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows (Delivery / Bid / Basis / Futures / Change / Futures Month / Last Trade) — the FAC shape, not Wheaton Grain's tabbed variant. **The location h2 is "Georgetown": the 3440 embed serves Wheaton's Georgetown location, not Winchester** (3439 is Winchester) | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry for the 3440 target; the 3439 entry is untouched); `BUSHEL_SITES` registry entry `winchester_3440` + `fetch_winchester_3440()` added in Cycle 12 (9 tests in `test_bushel_cycle12_locations.py`) |
| Skyland Grain — Cunningham Area (2730) | https://www.skylandgrain.com/cashbidssingle-2730 | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows — the FAC shape. **2730 is Cunningham Area's own per-location ID: the rows are the same 6 as the default `/cashbidssingle-` page**, so this entry duplicates the `skyland` widget. The static page carries no picker links (the picker is JS-driven); the ID→location mapping is confirmed only by the widget's location h2 | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry for the 2730 target; the default-page entry is untouched); `BUSHEL_SITES` registry entry `skyland_2730` + `fetch_skyland_2730()` added in Cycle 12 (9 tests in `test_bushel_cycle12_locations.py`) |
| Smithfield Grain — Bentonville (1666) | https://smithfieldgrain.com/cashbidssingle-1666 | 200 | **Yes — 3 rows** (Soybeans 1, Wheat 1, Corn 1, Bentonville, NC), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows — the FAC shape. Location h2 is "Bentonville, NC" (mapped to "Bentonville" in the registry entry). Delivery labels are descriptive ("Nov/Dec Delivery", "June Delivery", "November") rather than month abbreviations | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry for the 1666 target; the East Region link-list entry stays disabled); `BUSHEL_SITES` registry entry `smithfield_bentonville` + `fetch_smithfield_bentonville()` added in Cycle 12 (9 tests in `test_bushel_cycle12_locations.py`). **First Smithfield location verified** |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Winchester 3440 — parses cleanly.** `parse_bushel_html` run
  against the saved `/tmp/cycle12` HTML returns status ok: 5 rows,
  location Georgetown, Soybeans only, widget header dated Nov 19,
  2026. No `bushel_source.py` change needed for this shape.
- **Skyland 2730 — parses cleanly.** Same call returns status ok:
  6 rows, location Cunningham Area (Corn 2, Milo 1, Red Wheat 2,
  Soybeans 1). No `bushel_source.py` change needed.
- **Smithfield 1666 — parses cleanly.** Same call returns status ok:
  3 rows, location "Bentonville, NC" (Soybeans, Wheat, Corn).
  No `bushel_source.py` change needed.

### Reclassifications applied (`us_elevators_urls.toml`)

Three new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Winchester Ag — Georgetown (3440), Skyland Grain
— Cunningham Area (2730), Smithfield Grain — Bentonville (1666).
The existing entries for the 3439 embed target, the Skyland default
page, and the Smithfield East Region link list are untouched (the
link-list entry stays disabled). `config.toml` gains three toggles
(`winchester_3440`, `skyland_2730`, `smithfield_bentonville`), all
true. All other entries unchanged.

### Follow-ups for a later cycle

- **More per-location Bushel probes (one GET each):** Skyland has
  7 more picker IDs on file (2730, 2731, 2734, 2740, 2742, 2754,
  2761 verified; the remaining IDs are 2763, 2766, 2770, 2771,
  2778, 3370, 3621) — each new ID is a new location's widget.
  Smithfield has 26 more East Region locations (1666, 1725, 1667,
  2294, 1668 verified). Both families are now proven to serve
  static `.cbmod` widgets at the per-location targets, so each
  probe is low-risk; probe a few per cycle, not in bulk.
- **Skyland ID→location mapping:** the 2730 page carries no picker
  links in static HTML, so the only way to learn which town each
  remaining ID serves is to fetch it (or find the picker's
  ID→name mapping in the page JS). No shortcut exists short of a
  probe per ID.
- **West-Con regex fix:** done in Cycle 12 — see the
  AgriCharts regex-fix section below; West-Con is enabled.
- **Wheaton Dumont `/markets/cash.php` probe:** done in Cycle 12 —
  200, 43 static rows, reclassified `unknown → agricharts` and
  enabled; see the AgriCharts regex-fix section below.
- **The Andersons browser/API investigation:** the GRAINweb
  "MyCashBids" picker needs a rendered session or an API route
  found in its JS bundles; no static route exists.
- **Registry wiring (coordinator):** the three new Cycle 12
  `BUSHEL_SITES` entries (`winchester_3440`, `skyland_2730`,
  `smithfield_bentonville`) and their `fetch_` functions are in
  `bushel_source.py`; `source_registry.py` wiring is the
  coordinator's step.

## United States — Cycle 12 AgriCharts regex fix (West-Con + Wheaton Dumont) (2026-11-19)

One polite GET (User-Agent `GrainHub-Research/1.0`, 30 s timeout,
no retry) plus a regex fix in `us_agricharts_source.py` — no new
fetch for West-Con (verified against the saved Cycle 11 HTML).
Raw HTML saved to `/tmp/cycle12/` scratch only, never the repo.
No prices are recorded here — row counts and patterns only.

### The fix

`_WRITEBIDROW_RX` now accepts three delivery-window forms:
`MM/DD/YYYY` (unchanged), month-name labels (`'Dec 2026'`,
`'January 2027'`), and short month labels (`'Nov 26'`, `'Jan 27'`
— 2-digit year). Month-only windows are kept VERBATIM in the
Delivery / Delivery End columns: no day is invented (no
first-of-month synthesis) and no century is expanded for 2-digit
years, because the source never states either. (One fix attempt
dropped the opening quote before the delivery group and matched
0 rows; caught by the saved-HTML check before any test was
written.)

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| West-Con | https://www.west-con.com/markets/cash.php | (saved Cycle 11 HTML, no new fetch) | **Yes — 84 rows** (Corn 30 / Soybeans 44 / DNS Wheat 10, location param `All`, no `<h4>` tags) | Classic AgriCharts `writeBidRow()` calls inline in static HTML; delivery start/end are month-name labels (`'Dec 2026'` … `'Oct 2027'`, 10 distinct), start == end on all rows | **Collector-ready:** fixed regex matches **84/84** against saved HTML. **Enabled**; no registry adapter needed — the orchestrator drives `fetch_us_agricharts` from the toml |
| Wheaton Dumont | https://www.wdcoop.com/markets/cash.php | 200 | **Yes — 43 rows** (Corn 18 / Soybeans 16 / Spring Wheat 9, 8 `<h4>` locations: Wheaton/Dumont/Browns Valley/LaMars/Hankinson/Mantador/Sisseton groupings plus AGP DLVD Aberdeen/Dawson, Britton, Rutland, Graceville/Tenney) | Classic AgriCharts `writeBidRow()` calls inline in static HTML; delivery labels are the SHORT month form (`'Nov 26'` … `'Oct 27'`, 6 distinct), 6 rows span two adjacent months (e.g. `'Oct 27'` → `'Nov 27'`) | **Collector-ready:** fixed regex matches **43/43** against saved HTML. Reclassified `unknown → agricharts` and **enabled** (entry URL updated to `/markets/cash.php`); no registry adapter needed |

### Tests

7 new tests in `tests/test_us_agricharts_source.py` (plus
`tests/fixtures/us_agricharts_mixed_sample.html`, all values
invented): month-name labels parse, short month labels parse,
MM/DD/YYYY still parses, mixed page, end-to-end mocked fetch
keeps labels verbatim, and row-count checks against the saved
West-Con (84) and Wheaton Dumont (43) HTML. Full API suite:
558 passed, 0 failed.

### Reclassifications applied (`us_elevators_urls.toml`)

West-Con: `enabled = true` (already `agricharts`). Wheaton
Dumont: `unknown → agricharts`, `enabled = true`, URL updated to
`/markets/cash.php`. Registry wiring is the coordinator's step
(no adapter needed for this family).

## United States — Cycle 12 AgriCharts `cashbids-js.php` checks (2026-11-19)

Checked the three AgriCharts `cashbids.php` embeds left open by
Cycle 11, one polite GET per loader-derived `cashbids-js.php` URL
(User-Agent `GrainHub-Research/1.0`, 30 s timeout, no retries,
~2 s spacing) — 5 GETs total, budget respected: Hull Coop page +
js.php (2), StateLine Coop page + js.php (2), PRO Coop location
21302 js.php (1, URL derived from the saved Cycle 11 homepage
fetch in `/tmp/procoop_home.html` — no homepage re-fetch). All
three served 200 with a `var bids` JSON payload and parsed cleanly
with the existing generic `cashbids_embed_source.py` parser — no
parser change needed. Raw responses saved to `/tmp/cycle12/`
scratch only, never the repo. No prices are recorded here — row
counts and location/commodity breakdowns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200, `var bids` JSON | **3** | Hull Coop (12 rows), StateLine Coop (126 rows), PRO Coop 21302 first embed (12 rows) |
| New parser gap | 0 | All three are the standard `var bids` shape — `groupby=ccommodity` (Hull, PRO 21302) and `groupby=location` (StateLine) both already handled; `location_name` is authoritative on the commodity-grouped sites |
| Skipped rows (login-gated / inactive) | 0 | Every payload row parsed — no login-gated or inactive rows in any of the three live payloads |

### Per-site results

| Company | URL probed | HTTP | `var bids` payload? | Rows / breakdown | Collector pattern |
|---|---|---|---|---|---|
| Hull Coop | https://www.hullcoop.com/cashbids (page) → https://hullcoopresp.agricharts.com/inc/cashbids/cashbids-js.php?filter=all&location=&commodity=&groupby=ccommodity&width=&showtimestamp=1&hidenav=1&&showchart=1&format=table&fields=delivery_start%2Cbasismonth%2Cfutureschange%2Cbasis%2Cprice&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d%2F%25Y&months=8&locations=&commodities=&noscript=1&&acCnt=1 | 200 / 200 | **Yes** | **12 rows** — 1 location (Hull, IA), Corn 6, Soybeans 6; groups named Corn / Soybeans (`groupby=ccommodity`), row location from `location_name`. Loader src carries `hidenav=1&&showchart=1` (double ampersand mid-query), kept verbatim | **Collector-ready:** `parse_cashbids_embed_html` verified status ok, 12 rows, against saved HTML — no parser change needed. **Enabled**; registry entry `hull_coop` + `fetch_hull_coop()` added in Cycle 12 (6 new tests in `test_cashbids_embed_collector.py`) |
| StateLine Coop | https://www.statelinecoop.com/cash-bids (page) → https://statelinecoop.agricharts.com/inc/cashbids/cashbids-js.php?filter=all&location=&commodity=&groupby=location&width=90%&enableScrollIntoView=1&format=table&fields=name%2Cdelivery_start%2Cfutureschange%2Cbasis%2Cbasismonth%2Cfutures%2Cprice%2Cnotes&groupheading=row&bidsort=commodity&dateformat=%25b+%25d%2C+%25Y&months=8&locations=&commodities=&noscript=1&&acCnt=1 | 200 / 200 | **Yes** | **126 rows** — 11 locations (Armstrong, Blue Earth, Cylinder, Emmetsburg-AGP, Fenton, Lakota, Ledyard, Marna, North Burt, Ringsted, Swea City — Iowa / Minnesota), Corn 60, Soybeans 66; Emmetsburg-AGP is Soybeans-only (6 rows), every other location 12 rows (Corn 6, Soybeans 6). `groupby=location`, `filter=all`, no single default location | **Collector-ready:** `parse_cashbids_embed_html` verified status ok, 126 rows, against saved HTML — no parser change needed. **Enabled**; registry entry `stateline_coop` + `fetch_stateline_coop()` added in Cycle 12 |
| PRO Coop — location 21302, first embed | https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php?filter=location&location=21302&commodity=&groupby=ccommodity&width=100%&showtimestamp=1&showchart=1&enableScrollIntoView=1&format=table&fields=%0Adelivery_start%2C%0Adelivery_end%2C%0Aprice%2C%0Abasis%2C%0Afutureschange%0A&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d%2F%25Y&months=11&noscript=1&&acCnt=1 (derived from the saved Cycle 11 homepage loader src; the loader's `fields` value carries literal newline characters, which requests percent-encodes to `%0A` on the wire — the registry URL is that wire form, matching the Cycle 11 21297 entry) | 200 | **Yes** | **12 rows** — 1 location (MANSON.IA), CORN 6, SOYBEANS 6; groups named CORN / SOYBEANS (`groupby=ccommodity`), row location from `location_name`. This is the FIRST of the homepage's two 21302 embeds (fields with `delivery_end`); the second 21302 embed (fields without `delivery_end`) was NOT checked — 1 GET was budgeted for 21302 | **Collector-ready:** `parse_cashbids_embed_html` verified status ok, 12 rows, against saved HTML — no parser change needed. Registry entry `pro_coop_21302` + `fetch_pro_coop_21302()` added in Cycle 12; the existing `pro_coop` (21297 Ayrshire) entry is untouched |

### Reclassifications applied (`us_elevators_urls.toml`)

Hull Coop and StateLine Coop: `enabled = false → true`
(`agricharts-embed`, verified Cycle 12). PRO Coop: entry already
enabled (Cycle 11, 21297 view); comment updated — the first
21302 embed is now verified (separate `pro_coop_21302` registry
entry), the second 21302 embed still open. **Cycle 13
(2026-11-19):** the second 21302 embed is now verified too
(separate `pro_coop_21302b` registry entry) — see the Cycle 13
section below. `config.toml` gains
three toggles (`hull_coop`, `stateline_coop`,
`pro_coop_21302`), all true. All other entries unchanged.

### Follow-ups for a later cycle

- **PRO Coop second 21302 embed (one GET):** done in Cycle 13 —
  the homepage's other location-21302 embed (`groupby=ccommodity`,
  fields `delivery_start` / `price` / `basis` / `futureschange` —
  no `delivery_end`) was verified live 2026-11-19 (MANSON.IA, 12
  rows — same Manson view as the first embed; the payload still
  carries `delivery_end` on every row), separate registry entry
  `pro_coop_21302b`; see the Cycle 13 section below. The URL was
  derived from the saved Cycle 11 homepage fetch
  (`/tmp/procoop_home.html`) — no homepage re-fetch.
- **Done this cycle:** Hull Coop + StateLine Coop
  `cashbids-js.php` checks (both proven, enabled) and the PRO
  Coop first 21302 embed (proven, separate registry entry).
- **West-Con regex fix:** done in Cycle 12 — see the
  AgriCharts regex-fix section above; West-Con is enabled.
- **Wheaton Dumont `/markets/cash.php` probe:** done in Cycle 12 —
  200, 43 static rows, reclassified `unknown → agricharts` and
  enabled; see the AgriCharts regex-fix section above.
- **The Andersons browser/API investigation:** the GRAINweb
  "MyCashBids" picker needs a rendered session or an API route
  found in its JS bundles; no static route exists.
- **Registry wiring (coordinator):** the three new Cycle 12
  `CASHBIDS_EMBED_SITES` entries (`hull_coop`,
  `stateline_coop`, `pro_coop_21302`) and their `fetch_`
  functions are in `cashbids_embed_source.py`;
  `source_registry.py` wiring is the coordinator's step.

## United States — Cycle 13 PRO Coop second 21302 embed + per-location Bushel sweep (2026-11-19)

Probed the two open threads from Cycle 12, one polite GET each
(User-Agent `GrainHub-Research/1.0`, 30 s timeout, no retries,
~2 s spacing) — 11 GETs total, budget respected: the PRO Coop
second location-21302 `cashbids-js.php` URL (derived from the saved
Cycle 11 homepage fetch in `/tmp/procoop_home.html` — no homepage
re-fetch), 6 Skyland per-location targets (2731, 2734, 2740, 2742,
2754, 2761), and 4 Smithfield East Region targets (1725 Bladenboro,
1667 Bladenboro Feed Mill, 2294 Chadbourn, 1668 Clarkton — the last
three taken from the saved Cycle 11 East Region link list in
`/tmp/cycle11/smithfield_fccp.html`). All 11 served 200 and parsed
cleanly with the existing generic parsers — no parser change
needed. Raw HTML saved to `/tmp/cycle13/` scratch only, never the
repo. No prices are recorded here — row counts, location/commodity
breakdowns and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 11 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **11** | PRO Coop 21302b (12 rows, Manson), Skyland 2731 (5), 2734 (5), 2740 (7), 2742 (7), 2754 (5), 2761 (6), Smithfield 1725 (1), 1667 (2), 2294 (1), 1668 (1) |
| New parser gap | 0 | All ten Bushel pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) — Wheaton Grain's tabbed variant was not needed anywhere; the cashbids payload parses with the existing `var bids` path |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| PRO Coop — location 21302, second embed | https://procooperative.agricharts.com/inc/cashbids/cashbids-js.php?filter=location&location=21302&commodity=&groupby=ccommodity&width=100%&showtimestamp=1&showchart=1&enableScrollIntoView=1&format=table&fields=%0Adelivery_start%2C%0Aprice%2C%0Abasis%2C%0Afutureschange%0A&groupheading=table&bidsort=commodity&dateformat=%25m%2F%25d%2F%25Y&months=11&noscript=1&&acCnt=1 (derived from the saved Cycle 11 homepage loader src — the second 21302 `<script>` sits in the homepage's `elementor-hidden-desktop` section, the mobile variant of the same widget; the loader's `fields` value carries literal newline characters, which requests percent-encodes to `%0A` on the wire — the registry URL is that wire form, matching the Cycle 12 first-embed entry) | 200 | **Yes** | **12 rows** — 1 location (MANSON.IA), CORN 6, SOYBEANS 6; groups named CORN / SOYBEANS (`groupby=ccommodity`), row location from `location_name`. **The fields list does NOT filter the payload: the returned bid objects still carry `delivery_end` on all 12 rows**, and the (commodity, delivery window, symbol, futures month) structure matches the first embed's payload exactly — the two embeds serve the same Manson view | **Collector-ready:** `parse_cashbids_embed_html` verified status ok, 12 rows, against saved HTML — no parser change needed. Registry entry `pro_coop_21302b` + `fetch_pro_coop_21302b()` added in Cycle 13 (2 new tests in `test_cashbids_embed_collector.py`, plus registry-URL assertions in the existing registry test); the existing `pro_coop` (21297 Ayrshire) and `pro_coop_21302` (first embed) entries are untouched |
| Skyland Grain — Conlen - Hartley (2731) | https://www.skylandgrain.com/cashbidssingle-2731 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows — the FAC shape. Location h2 "Conlen - Hartley" | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry for the 2731 target; the default-page and 2730 entries are untouched); `BUSHEL_SITES` registry entry `skyland_2731` + `fetch_skyland_2731()` added in Cycle 13 (30 tests in `test_bushel_cycle13_locations.py` cover all ten Cycle 13 Bushel targets) |
| Skyland Grain — Etter (2734) | https://www.skylandgrain.com/cashbidssingle-2734 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Etter" | **Collector-ready:** `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2734` + `fetch_skyland_2734()` added in Cycle 13 |
| Skyland Grain — Moscow, Dermot, Kismet, Pleasant Valley (2740) | https://www.skylandgrain.com/cashbidssingle-2740 | 200 | **Yes — 7 rows** (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, White Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is the four-town grouping "Moscow, Dermot, Kismet, Pleasant Valley", kept as published. "White Wheat" is not in `COMMODITY_MAP` and passes through as-is, like "Red Wheat" | **Collector-ready:** `parse_bushel_html` verified status ok, 7 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2740` + `fetch_skyland_2740()` added in Cycle 13 |
| Skyland Grain — Johnson - Ulysses - N Sublette (2742) | https://www.skylandgrain.com/cashbidssingle-2742 | 200 | **Yes — 7 rows** (Corn 2, Milo 1, Red Wheat 2, White Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Johnson - Ulysses - N Sublette" | **Collector-ready:** `parse_bushel_html` verified status ok, 7 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2742` + `fetch_skyland_2742()` added in Cycle 13 |
| Skyland Grain — Olton Area (2754) | https://www.skylandgrain.com/cashbidssingle-2754 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Olton Area" | **Collector-ready:** `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2754` + `fetch_skyland_2754()` added in Cycle 13 |
| Skyland Grain — Elkhart - Hough - Rolla Area (2761) | https://www.skylandgrain.com/cashbidssingle-2761 | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, White Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Elkhart - Hough - Rolla Area" | **Collector-ready:** `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2761` + `fetch_skyland_2761()` added in Cycle 13 |
| Smithfield Grain — Bladenboro (1725) | https://smithfieldgrain.com/cashbidssingle-1725 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Bladenboro, NC" (mapped to "Bladenboro" in the registry entry). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry; the East Region link-list entry stays disabled); registry entry `smithfield_bladenboro` + `fetch_smithfield_bladenboro()` added in Cycle 13 |
| Smithfield Grain — Bladenboro Feed Mill (1667) | https://smithfieldgrain.com/cashbidssingle-1667 | 200 | **Yes — 2 rows** (Corn 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Bladenboro Feed Mill, NC" (mapped to "Bladenboro Feed Mill"). Distinct from the Bladenboro Elevator target (1725). Delivery labels are descriptive ("November", "June Delivery") as on the Bentonville page | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_bladenboro_feed_mill` + `fetch_smithfield_bladenboro_feed_mill()` added in Cycle 13 |
| Smithfield Grain — Chadbourn (2294) | https://smithfieldgrain.com/cashbidssingle-2294 | 200 | **Yes — 1 row** (Soybeans), widget header dated **Nov 18, 2026** | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Chadbourn, NC" (mapped to "Chadbourn"). Thin page: a single Soybeans row. **The widget header is a day older than the other Cycle 13 pages (Nov 19)** — the Chadbourn widget had not refreshed at probe time; worth watching on the next fetch, not a parser issue. **Cycle 14 (2026-11-19): re-check — header STILL "Cash bids for Wednesday, November 18, 2026", still 1 Soybeans row (Last Trade 12:23 AM). Chadbourn lags a full day behind the other Smithfield pages; the widget is stale, not just slow to refresh — flag for the collector (a same-day freshness check would fail this location daily). **Cycle 22 (2026-11-19): re-check — header STILL "Cash bids for Wednesday, November 18, 2026", still 1 Soybeans row, `parse_bushel_html` status ok. Third consecutive stale probe (Cycles 13, 14, 22); persistent one-day lag, not a transient delay.** | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_chadbourn` + `fetch_smithfield_chadbourn()` added in Cycle 13 |
| Smithfield Grain — Clarkton (1668) | https://smithfieldgrain.com/cashbidssingle-1668 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Clarkton, NC" (mapped to "Clarkton"). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_clarkton` + `fetch_smithfield_clarkton()` added in Cycle 13 |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **PRO Coop 21302b — parses cleanly.** `parse_cashbids_embed_html`
  run against the saved `/tmp/cycle13` response returns status ok:
  12 rows, location MANSON.IA (CORN 6, SOYBEANS 6), `delivery_end`
  present on all 12 rows. No `cashbids_embed_source.py` change
  needed for this shape — the `fields` list is a display hint, not
  a payload filter.
- **Skyland 2731 / 2734 / 2740 / 2742 / 2754 / 2761 — parse cleanly.**
  `parse_bushel_html` run against each saved `/tmp/cycle13` HTML
  returns status ok with the row counts above and the location
  from each page's h2. No `bushel_source.py` change needed.
- **Smithfield 1725 / 1667 / 2294 / 1668 — parse cleanly.**
  Same call returns status ok with 1 / 2 / 1 / 1 rows and the
  mapped town locations. No `bushel_source.py` change needed.

### Tests

32 new tests: 30 in `tests/test_bushel_cycle13_locations.py`
(registry entry + synthetic-fixture parse + mocked fetch per
target, all fixture values invented) and 2 in
`tests/test_cashbids_embed_collector.py` for `pro_coop_21302b`
(parse + mocked fetch, plus registry-URL assertions — including
that the js_url omits `delivery_end` while the fixture payload
still carries it — added to the existing registry test). Full API
suite: **590 passed, 0 failed** (Cycle 12 baseline 558).

### Reclassifications applied (`us_elevators_urls.toml`)

Ten new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Skyland Grain — Conlen - Hartley (2731), Etter
(2734), Moscow/Dermot/Kismet/Pleasant Valley (2740), Johnson -
Ulysses - N Sublette (2742), Olton Area (2754), Elkhart - Hough -
Rolla Area (2761); Smithfield Grain — Bladenboro (1725),
Bladenboro Feed Mill (1667), Chadbourn (2294), Clarkton (1668).
PRO Coop: no new toml entry (the entry is already enabled from
Cycle 11) — its comment now records that both 21302 embeds are
verified (`pro_coop_21302` + `pro_coop_21302b`). `config.toml`
gains eleven toggles (`skyland_2731`, `skyland_2734`,
`skyland_2740`, `skyland_2742`, `skyland_2754`, `skyland_2761`,
`smithfield_bladenboro`, `smithfield_bladenboro_feed_mill`,
`smithfield_chadbourn`, `smithfield_clarkton`, `pro_coop_21302b`),
all true. All other entries unchanged.

### Follow-ups for a later cycle

- **More per-location Bushel probes (one GET each):** Skyland has
  7 picker IDs still open (2763, 2766, 2770, 2771, 2778, 3370,
  3621); Smithfield has 20 East Region locations still open
  (1675, 1676, 1678, 1679, 1681, 1682, 1683, 1684, 1685, 1686,
  1687, 1688, 1689, 1690, 1691, 2064, 2065, 2066, 2067, 2179 —
  from the saved Cycle 11 East Region link list; 1669–1674
  verified in Cycle 14). Probe a few per cycle, not in bulk.
- **Skyland ID→location mapping:** the per-location pages carry no
  picker links in static HTML, so the only way to learn which town
  each remaining ID serves is to fetch it (or find the picker's
  ID→name mapping in the page JS). No shortcut exists short of a
  probe per ID.
- **Smithfield thin pages:** Bladenboro, Chadbourn and Clarkton
  each carry a single Soybeans row and Bladenboro Feed Mill only
  Corn + Wheat — the East Region locations are thin widgets, not
  multi-commodity boards. Expect 1–3 rows per remaining target.
  **Cycle 14 (2026-11-19):** revised — five of the six Cycle 14
  pages (Clinton, Hobbsville, Kinston, LaGrange, Mount Olive)
  carry a full 3 rows (Corn + Soybeans + Wheat); only Morgan's
  Corner is thin (Soybeans + Wheat). The 1-row pages are the
  exception, not the rule.
- **Chadbourn staleness watch:** the 2294 widget header was dated
  Nov 18, 2026 while every other Cycle 13 page was Nov 19 — check
  on the next fetch whether Chadbourn refreshes daily or lags.
  **Cycle 14 (2026-11-19) re-check: STILL Nov 18, still 1 Soybeans
  row — Chadbourn lags a full day; the widget is stale, not just
  slow. Flag for the collector: a same-day freshness check would
  fail this location daily. **Cycle 22 (2026-11-19) re-check:
  STILL Nov 18, still 1 Soybeans row — third consecutive stale
  probe; the one-day lag is persistent.**
- **Registry wiring (coordinator):** the eleven new Cycle 13
  registry entries (`pro_coop_21302b` in
  `CASHBIDS_EMBED_SITES`; `skyland_2731`, `skyland_2734`,
  `skyland_2740`, `skyland_2742`, `skyland_2754`, `skyland_2761`,
  `smithfield_bladenboro`, `smithfield_bladenboro_feed_mill`,
  `smithfield_chadbourn`, `smithfield_clarkton` in `BUSHEL_SITES`)
  and their `fetch_` functions are in their source modules;
  `source_registry.py` wiring is the coordinator's step.

## United States — Cycle 14 Andersons bundle probe + Chadbourn re-check (2026-11-19)

Two polite GETs, budget respected (User-Agent
`GrainHub-Research/1.0`, no retries, ~2 s spacing): the Andersons
`my-cash-bids` JS bundle (the Cycle 13 verdict's named next probe)
and a re-check of Smithfield Chadbourn (2294, the Cycle 13
staleness watch). Raw files saved to `/tmp/cycle14/` scratch only,
never the repo. No prices are recorded here — row counts and
structure only. Research only: no code changes, no tests.

### Andersons — `my-cash-bids` bundle, fetched verbatim

`https://www.andersonsgrain.com/bundles/js/my-cash-bids?v=C0G6bVc73LyEBcO1OYpPFy7jWEA7shnNPkHnIdQ0d7o1`
— HTTP 200, 1,079 bytes, saved to
`/tmp/cycle14/andersons_my_cash_bids.js`.

- **Structure:** a Browserify wrapper defining exactly one module
  (83). It requires `./mod/master-page`, `./mod/get-ui`,
  `./mod/accordion-menu`, and `jquery` — none of which are defined
  in this file; they come from a shared bundle loaded separately
  on the page (`site.js` is the other page script). The picker
  logic itself is fully contained in module 83.
- **Verbatim picker logic:** on location change, read the inline
  global `ANDERSONS_GRAIN_LOCATIONS` (location ID → commodity
  list, embedded in the page HTML per Cycle 13) and populate the
  commodity `<select>` with an `All Commodities` option plus one
  `<option>` per commodity, then enable/show the Add button; with
  no commodities for the location, clear and hide the dropdown and
  disable/hide Add. That is the whole bundle — it wires the
  dropdowns and nothing else.
- **No network call of any kind:** no `fetch(`, `XMLHttpRequest`,
  `$.ajax`, `axios`, `getJSON`, `.post(`, or `.get(`. A grep for
  those plus `/api/`, `.json`, and `http` returns nothing except
  the single identifier `ANDERSONS_GRAIN_LOCATIONS`.
- **No POST target in the bundle:** the form's
  `/locations/cash-bids/Add` action is known only from the saved
  Cycle 11 HTML; the bundle never names it, and it names no other
  URL at all.
- **No token/CSRF handling:** no `__RequestVerificationToken`,
  `antiForgery`, `csrf`, or `token` string anywhere (the hidden
  token field lives in the HTML form only). No credential-like
  string of any kind in the bundle (secret scan: 0 matches).

**Verdict: confirmed browser-only — the API thread is closed.**
No static-data route and no public API exist for The Andersons
GRAINweb picker. Bid loading, if any, happens only after the form
POSTs and the server renders the saved-selection page; there is no
client-side bid fetch to intercept. No collector can be built from
static fetches, and no trivially parseable static route was
revealed — **no collector work follows from this probe**. The
Andersons stays `unknown`, still disabled. Full bundle analysis
also recorded as a Cycle 14 addendum under "The Andersons —
GRAINweb investigation (Cycle 13)" above.

### Smithfield — Chadbourn (2294) re-check

`https://www.smithfieldgrain.com/cashbidssingle-2294` — HTTP 200,
80,256 bytes, saved to
`/tmp/cycle14/smithfield_chadbourn_2294.html`.

- **Widget header STILL "Cash bids for Wednesday, November 18,
  2026"** — a full day behind on Nov 19, while every other Cycle
  13 Smithfield page was dated Nov 19. Chadbourn lags; the widget
  is stale, not just slow to refresh.
- **Still 1 row: Soybeans** (standard wrapped `.cbmod` shape,
  Last Trade 12:23 AM). Row count and structure unchanged from
  Cycle 13; no parser issue.
- **Collector flag:** a same-day freshness check would fail this
  location daily — if a freshness gate is ever added to the Bushel
  collector, Chadbourn needs an exemption or a lag tolerance, not
  a parser fix. The `smithfield_chadbourn` entry itself is
  unchanged.

### Follow-ups for a later cycle

- **The Andersons — last static probe:** **Cycle 15
  (2026-11-19): done — one GET of
  `https://www.andersonsgrain.com/local-bids/locations-list/`
  returned HTTP 200, 27,082 bytes: a plain 41-facility directory
  (10 state/province groups), 0 tables, 0 forms, no `writeBidRow`,
  `.cbmod`, or `cashbids.php` — no static bids. The Andersons is
  closed for static collection; only a rendered browser session
  (possibly account-bound) remains. Two low-odds confirmatory
  targets remain open for a later cycle (1 GET each, not fetched):
  `https://www.andersonsgrain.com/locations/oh/maumee/` and
  `https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/`.
  See the Cycle 15 section.**
- **More per-location Bushel probes (one GET each):** **Cycle 14
  (2026-11-19): done — all 7 remaining Skyland picker IDs probed
  (2763, 2766, 2770, 2771, 2778, 3370, 3621), all 200, all static
  7-col `.cbmod` widgets; the 14-location Skyland sweep is
  complete.** Smithfield has 26 East Region locations still open
  (see Cycle 13 follow-ups). Probe a few per cycle, not in bulk.
- **Chadbourn freshness:** re-check the 2294 header again on a
  later cycle to see whether the lag is a permanent one-day offset
  or whether the widget eventually catches up.

## United States — Cycle 15 Andersons locations-list probe (2026-11-19)

One polite GET, budget respected (User-Agent
`GrainHub-Research/1.0`, no retries): the Andersons
locations-list page — the last static chance named in Cycle 14.
Raw file saved to `/tmp/cycle15/andersons_locations_list.html`
scratch only, never the repo. No prices are recorded here — link
targets and structure only. Research only: no code changes, no
tests.

### Andersons — locations-list page, fetched verbatim

`https://www.andersonsgrain.com/local-bids/locations-list/` —
HTTP 200, 27,082 bytes, saved to
`/tmp/cycle15/andersons_locations_list.html`.

- **What the page actually is:** a plain per-location directory,
  not a picker and not a login wall. Title: `Locations List -
  The Andersons Trade Group`. The full page body serves
  anonymously; a `Login` link exists in the nav
  (`/login?returnUrl=%2flocal-bids%2flocations-list%2f`) but
  nothing on the page requires signing in. Body heading: "Please
  choose a Grain Facilities state", then one collapsible group
  per state/province, each listing its facility names as links.
- **No static bid rows of any kind:** 0 `<table>` elements,
  0 `<form>` elements, 0 occurrences of `writeBidRow`, `.cbmod`,
  or `cashbids.php`, and no price-like strings (`$n.nn`, `basis`)
  anywhere in the file. The only bid-related links are the nav
  links back to the already-probed GRAINweb picker
  (`/locations/cash-bids/`, Cycle 11) and to `/local-bids/locations/`
  (Locations Map). No `my-cash-bids` reference, no
  `ANDERSONS_GRAIN_LOCATIONS` global on this page.
- **Scripts:** 8 external script sources only
  (`modernizr.js`, `arrayFind.js` polyfill, Typekit, Wistia,
  `matchmedia.js` polyfill, `/Static/js/site.js`,
  `/bundles/js/products-services`); no bid-loading script.
- **Credential-like string (value NOT recorded):** the `<html>`
  tag carries a `data-google-api-key` attribute — a Google API
  key embedded in the page markup. Its value is not reproduced
  here or anywhere in the repo, per the no-secrets rule.

### Per-location link targets (verbatim, URLs + names only)

41 facility links, grouped by the page's own state sections:

- **Idaho** (8) — `/locations/id/bliss/` Bliss,
  `/locations/id/buhl/` Buhl, `/locations/id/driscoll/` Driscoll,
  `/locations/id/glenns-ferry/` Glenns Ferry,
  `/locations/id/hansen/` Hansen, `/locations/id/harris/` Harris
  Burley, `/locations/id/lincoln/` Lincoln,
  `/locations/id/pleasant-valley/` Pleasant Valley
- **Illinois** (1) — `/locations/il/mansfield/` Mansfield
- **Indiana** (4) — `/locations/in/clymers/` Clymers,
  `/locations/in/delphi/` Delphi, `/locations/in/dunkirk/` Dunkirk,
  `/locations/in/oakville/` Oakville
- **Iowa** (1) — `/locations/ia/denison/` Denison
- **Louisiana** (5) — `/locations/la/delhi/` Delhi,
  `/locations/la/lake-providence/` Lake Providence,
  `/locations/la/newellton/` Newellton,
  `/locations/la/tallulah/` Tallulah, `/locations/la/wisner/` Wisner
- **Michigan** (8) — `/locations/mi/albion/` Albion,
  `/locations/mi/auburn/` Auburn, `/locations/mi/hemlock/` Hemlock,
  `/locations/mi/hudson/` Hudson, `/locations/mi/oakley/` Oakley,
  `/locations/mi/reading/` Reading, `/locations/mi/standish/`
  Standish, `/locations/mi/white-pigeon/` White Pigeon
- **Nebraska** (3) — `/locations/ne/fairmont/` Fairmont,
  `/locations/ne/kearney/` Kearney, `/locations/ne/riverdale/`
  Riverdale
- **Ohio** (7) — `/locations/oh/greenville/` Greenville,
  `/locations/oh/maumee/` Maumee, `/locations/oh/metamora/`
  Metamora, `/locations/oh/portwilliam/` Port William,
  `/locations/oh/toledo-edwin/` Toledo - Edwin Dr,
  `/locations/oh/toledo-kuhlman/` Toledo - Kuhlman Dr,
  `/locations/oh/toledo-reynolds/` Toledo - Reynolds Rd
- **Texas** (1) — `/locations/tx/houston/` Houston
- **Canada** (3) — `/locations/ca/carlea/` Carlea, SK,
  `/locations/ca/darlingford/` Darlingford, MB,
  `/locations/ca/zenon-park/` Zenon Park, SK

10 per-state list links (same destinations, filtered view):
`/local-bids/locations-list/location-list/idaho/`,
`/local-bids/locations-list/location-list/illinois/`,
`/local-bids/locations-list/location-list/indiana/`,
`/local-bids/locations-list/location-list/iowa/`,
`/local-bids/locations-list/location-list/louisiana/`,
`/local-bids/locations-list/location-list/michigan/`,
`/local-bids/locations-list/location-list/nebraska/`,
`/local-bids/locations-list/location-list/ohio/`,
`/local-bids/locations-list/location-list/texas/`,
`/local-bids/locations-list/location-list/canada/`.
Also linked: `/local-bids/locations-list-office/` (Trading
Offices) and `/local-bids/locations/` (Locations Map).

### Verdict: the Andersons is closed for static collection

The last static chance is spent. The locations-list page is a
pure directory: it links to 41 facility info pages and back to
the already-probed GRAINweb picker, and carries no bid data
itself. No static-bid page exists anywhere in its link tree
except the picker (`/locations/cash-bids/`, Cycle 11 — JS form
POST, no static rows). **Only a rendered browser session
remains** — one that picks a location, submits the form, and
reads the server-rendered saved bids (possibly account-bound;
the picker page links
`/login?returnUrl=%2flocations%2fcash-bids%2f`). No collector
can be built from static fetches. Stays `unknown`, still
disabled. Full findings also recorded as a Cycle 15 addendum
under "The Andersons — GRAINweb investigation (Cycle 13)" above.

**Cycle 16 (2026-11-19) — confirmatory checks done, closure
refined.** Both checks named below were fetched: the Maumee
facility page DOES carry static bid tables (3 tables: Corn 10
rows, Soybeans 10, Red Wheat 3), but the page states all market
data is provided by Barchart Solutions — the tables are
licensed data and are NOT collected. The Ohio per-state list
page is the same directory markup, no bids. The Andersons is
now **fully closed**: the closure rests on licensing, not on
absence of static rows. No new probe exists (the other 40
facility pages would serve the same Barchart-licensed tables;
do not probe them). Full findings in the Cycle 16 loose-ends
section below.

### Next probes, if a later cycle wants confirmatory checks (NOT fetched — 1 GET each, low odds)

**Cycle 16 (2026-11-19): both checks below are DONE — this list
is spent, do not re-fetch.**

1. `https://www.andersonsgrain.com/locations/oh/maumee/` — one
   representative facility page (Maumee, OH, flagship Ohio
   location): tests whether facility pages carry static bids or
   only contact/directions info. Expected: info only.
   **Cycle 16 result: expectation WRONG — the page DOES carry
   static bid tables (3 tables: Corn 10 rows, Soybeans 10, Red
   Wheat 3), but the page states all market data is provided by
   Barchart Solutions, so the tables are licensed data and are
   NOT collected. See the Cycle 16 loose-ends section.**
2. `https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/`
   — one per-state list page: tests whether state lists differ
   from the master list. Expected: same directory markup, no bids.
   **Cycle 16 result: expectation CONFIRMED — same directory
   markup (same 7 Ohio facilities), no bids. See the Cycle 16
   loose-ends section.**
3. (No third candidate — `/locations/cash-bids/` was already
   probed in Cycle 11 and is the picker itself, not a new target.)

## United States — Cycle 14 Smithfield East Region batch (2026-11-19)

Probed the next six Smithfield East Region per-location targets,
one polite GET each (User-Agent `GrainHub-Research/1.0`, 30 s
timeout, no retries, ~2 s spacing) — 6 GETs total, budget
respected. The list page itself was recovered from the saved
Cycle 11 page (`/tmp/cycle11/smithfield_fccp.html`), so no GET
was spent re-fetching it; the six targets (1669 Clinton, 1670
Hobbsville, 1671 Kinston, 1672 LaGrange, 1673 Morgan's Corner,
1674 Mount Olive) are the next six IDs in numeric order after the
five already verified (1666, 1667, 1668, 1725, 2294). All six
served 200 and parsed cleanly with the existing generic parser —
no parser change needed. Raw HTML saved to `/tmp/cycle14/`
scratch only, never the repo. No prices are recorded here — row
counts, location/commodity breakdowns and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 6 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **6** | Clinton (3), Hobbsville (3), Kinston (3), LaGrange (3), Morgan's Corner (2), Mount Olive (3) — 17 rows total |
| New parser gap | 0 | All six pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Smithfield Grain — Clinton (1669) | https://smithfieldgrain.com/cashbidssingle-1669 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Clinton, NC" (mapped to "Clinton" in the registry entry). Delivery labels are descriptive ("November", "Nov/Dec", "June Delivery") as on the Bentonville page | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry; the East Region link-list entry stays disabled); registry entry `smithfield_clinton` + `fetch_smithfield_clinton()` added in Cycle 14 |
| Smithfield Grain — Hobbsville (1670) | https://smithfieldgrain.com/cashbidssingle-1670 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Hobbsville, NC" (mapped to "Hobbsville") | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_hobbsville` + `fetch_smithfield_hobbsville()` added in Cycle 14 |
| Smithfield Grain — Kinston (1671) | https://smithfieldgrain.com/cashbidssingle-1671 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Kinston, NC" (mapped to "Kinston"). Distinct from the JCH - Kinston Elevator target (2064), still open | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_kinston` + `fetch_smithfield_kinston()` added in Cycle 14 |
| Smithfield Grain — LaGrange (1672) | https://smithfieldgrain.com/cashbidssingle-1672 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "LaGrange, NC" (mapped to "LaGrange") | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_lagrange` + `fetch_smithfield_lagrange()` added in Cycle 14 |
| Smithfield Grain — Morgan's Corner (1673) | https://smithfieldgrain.com/cashbidssingle-1673 | 200 | **Yes — 2 rows** (Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Morgans Corner, NC" (**no apostrophe** — the registry entry maps it to "Morgans Corner"). Delivery labels are descriptive ("Nov/Dec", "June/July"). No Corn row on this page | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_morgans_corner` + `fetch_smithfield_morgans_corner()` added in Cycle 14 |
| Smithfield Grain — Mount Olive (1674) | https://smithfieldgrain.com/cashbidssingle-1674 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Mount Olive, NC" (mapped to "Mount Olive") | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_mount_olive` + `fetch_smithfield_mount_olive()` added in Cycle 14 |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Smithfield 1669 / 1670 / 1671 / 1672 / 1673 / 1674 — parse
  cleanly.** `parse_bushel_html` run against each saved
  `/tmp/cycle14` HTML returns status ok with 3 / 3 / 3 / 3 / 2 /
  3 rows and the mapped town locations. No `bushel_source.py`
  change needed for the widget shape — the registry additions
  are the only code change.

### Tests

6 new tests in `tests/test_bushel_cycle14_smithfield.py` (one per
location: registry entry exists + synthetic-fixture parse, all
fixture values invented). Full API suite: **596 passed, 0
failed** (Cycle 13 baseline 590).

### Reclassifications applied (`us_elevators_urls.toml`)

Six new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Smithfield Grain — Clinton (1669),
Hobbsville (1670), Kinston (1671), LaGrange (1672), Morgan's
Corner (1673), Mount Olive (1674). `config.toml` gains six
toggles (`smithfield_clinton`, `smithfield_hobbsville`,
`smithfield_kinston`, `smithfield_lagrange`,
`smithfield_morgans_corner`, `smithfield_mount_olive`), all true.
The East Region link-list entry stays disabled. All other
entries unchanged.

### Follow-ups for a later cycle

- **More Smithfield per-location probes (one GET each):** 20 East
  Region locations still open (1675, 1676, 1678, 1679, 1681,
  1682, 1683, 1684, 1685, 1686, 1687, 1688, 1689, 1690, 1691,
  2064, 2065, 2066, 2067, 2179 — from the saved Cycle 11 East
  Region link list). Probe a few per cycle, not in bulk. The
  next batch in numeric order is 1675 Raeford, 1676 Red Springs,
  1678 Walstonburg, 1679 Weeksville, 1681 The Chief Feed Mill,
  1682 Laurinburg Feed Mill. Note 2064 is a second Kinston
  target (JCH - Kinston Elevator), distinct from 1671.
  **Cycle 15 batch A (2026-11-19):** that batch probed 1675–
  1682 — five verified and enabled; 1675 Raeford served 200
  with an empty widget (0 rows) and was NOT registered, re-probe
  later. A parallel Cycle 15 batch B covered 1683–1688.
  Combined, 8 locations still open (1689, 1690, 1691, 2064,
  2065, 2066, 2067, 2179) plus the Raeford re-probe.
  **Cycle 15 batch B (2026-11-19):** 1683 Creswell, 1684 Warsaw,
  1685 Harpster, 1686 Morral, 1687 Darlington, 1688 Lake City
  probed and enabled — 14 East Region locations still open after
  this batch (1675, 1676, 1678, 1679, 1681, 1682, 1689, 1690,
  1691, 2064, 2065, 2066, 2067, 2179); the sibling batch A is
  probing 1675–1682 in parallel, so the combined Cycle 15
  remainder will be smaller. Note 1683–1688 are the first
  Smithfield targets outside NC (Harpster/Morral OH, Darlington/
  Lake City SC) — the h2 state suffix varies (", OH", ", SC"),
  and Harpster's live h2 is bare "Harpster" with no state.
  **Cycle 16 (2026-11-19):** 1689 Nichols, 1690 Petersburg,
  1691 Waverly, 2064 Kinston JCH, 2065 Jones County, 2066 Deep
  Run JCH probed and enabled — only 2067 and 2179 still open,
  plus the Raeford re-probe.
- **Smithfield row counts:** Cycle 14 revises the Cycle 13
  thin-page expectation — five of six pages carry a full 3 rows
  (Corn + Soybeans + Wheat); only Morgan's Corner is thin
  (Soybeans + Wheat, no Corn). The 1-row pages (Bladenboro,
  Chadbourn, Clarkton) are the exception, not the rule.
- **Registry wiring (coordinator):** the six new Cycle 14
  registry entries (`smithfield_clinton`,
  `smithfield_hobbsville`, `smithfield_kinston`,
  `smithfield_lagrange`, `smithfield_morgans_corner`,
  `smithfield_mount_olive` in `BUSHEL_SITES`) and their `fetch_`
  functions are in `bushel_source.py`; `source_registry.py`
  wiring is the coordinator's step.

## United States — Cycle 14 Skyland picker sweep, final 7 IDs (2026-11-19)

Probed the last 7 open Skyland picker IDs, one polite GET each
(User-Agent `GrainHub-Research/1.0`, 30 s timeout, no retries,
~2 s spacing) — 7 GETs total, budget respected. All 7 served 200
and parsed cleanly with the existing generic `bushel_source.py`
parser — no parser change needed. This completes the 14-location
Skyland picker sweep: 2730 in Cycle 12, 2731 / 2734 / 2740 / 2742 /
2754 / 2761 in Cycle 13, and these 7 in Cycle 14. Raw HTML saved
to `/tmp/cycle14/` scratch only, never the repo. No prices are
recorded here — row counts, location/commodity breakdowns and
widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 7 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **7** | Skyland 2763 (6), 2766 (5), 2770 (5), 2771 (6), 2778 (6), 3370 (6), 3621 (5) — 39 rows total |
| New parser gap | 0 | All seven pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) — Wheaton Grain's tabbed variant was not needed anywhere |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Skyland Grain — Satanta - Ryus (2763) | https://www.skylandgrain.com/cashbidssingle-2763 | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, White Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape: `div.cbCommodity` + `ul.sevenColumnsBigFirst` 7-col rows — the FAC shape. Location h2 "Satanta - Ryus" | **Collector-ready:** the existing generic `bushel_source.py` `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); `BUSHEL_SITES` registry entry `skyland_2763` + `fetch_skyland_2763()` added in Cycle 14 |
| Skyland Grain — Spearman - Gruver - Texline (2766) | https://www.skylandgrain.com/cashbidssingle-2766 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Spearman - Gruver - Texline" | **Collector-ready:** `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2766` + `fetch_skyland_2766()` added in Cycle 14 |
| Skyland Grain — Sunray Area (2770) | https://www.skylandgrain.com/cashbidssingle-2770 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Sunray Area" | **Collector-ready:** `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2770` + `fetch_skyland_2770()` added in Cycle 14 |
| Skyland Grain — Kendall - Midway - Lydia (2771) | https://www.skylandgrain.com/cashbidssingle-2771 | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, White Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Kendall - Midway - Lydia" | **Collector-ready:** `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2771` + `fetch_skyland_2771()` added in Cycle 14 |
| Skyland Grain — Buckeye - Syracuse (2778) | https://www.skylandgrain.com/cashbidssingle-2778 | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, White Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Buckeye - Syracuse" | **Collector-ready:** `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_2778` + `fetch_skyland_2778()` added in Cycle 14 |
| Skyland Grain — Hugoton (3370) | https://www.skylandgrain.com/cashbidssingle-3370 | 200 | **Yes — 6 rows** (Corn 2, Milo 2, Red Wheat 2), widget header dated **Nov 18, 2026** | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Hugoton, KS" (mapped to "Hugoton" in the registry entry). **The first Skyland page with two Milo rows.** **The widget header is a day older than the other Cycle 14 pages (Nov 19)** — like Chadbourn in Cycle 13; the Hugoton widget had not refreshed at probe time. **Cycle 22 (2026-11-19): re-check — header STILL "Cash bids for Wednesday, November 18, 2026", still 6 rows (Corn 2, Milo 2, Red Wheat 2), `parse_bushel_html` status ok. Second consecutive stale probe; persistent one-day lag.** | **Collector-ready:** `parse_bushel_html` verified status ok, 6 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_3370` + `fetch_skyland_3370()` added in Cycle 14 |
| Skyland Grain — Vilas - Walsh (3621) | https://www.skylandgrain.com/cashbidssingle-3621 | 200 | **Yes — 5 rows** (Corn 2, Milo 1, Red Wheat 2), widget header dated **Nov 18, 2026** | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 "Vilas - Walsh". **The widget header is a day older than the other Cycle 14 pages (Nov 19)** — like 3370 and Chadbourn in Cycle 13. **Cycle 22 (2026-11-19): re-check — header STILL "Cash bids for Wednesday, November 18, 2026", still 5 rows (Corn 2, Milo 1, Red Wheat 2), `parse_bushel_html` status ok. Second consecutive stale probe; persistent one-day lag.** | **Collector-ready:** `parse_bushel_html` verified status ok, 5 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `skyland_3621` + `fetch_skyland_3621()` added in Cycle 14 |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Skyland 2763 / 2766 / 2770 / 2771 / 2778 / 3370 / 3621 — parse
  cleanly.** `parse_bushel_html` run against each saved
  `/tmp/cycle14` HTML returns status ok with the row counts above
  and the location from each page's h2 (3370 mapped from
  "Hugoton, KS" to "Hugoton" via the registry `location_labels`).
  No `bushel_source.py` change needed.

### Tests

21 new tests in `tests/test_bushel_cycle14_skyland.py` (registry
entry + synthetic-fixture parse + mocked fetch per target, all
fixture values invented). Full API suite at run time: **617
passed, 0 failed** (Cycle 13 baseline 590 + 21 here + 6 from a
concurrent sibling worker's Smithfield Cycle 14 file, which
landed in the working tree during this run).

### Reclassifications applied (`us_elevators_urls.toml`)

Seven new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Skyland Grain — Satanta - Ryus (2763),
Spearman - Gruver - Texline (2766), Sunray Area (2770), Kendall -
Midway - Lydia (2771), Buckeye - Syracuse (2778), Hugoton (3370),
Vilas - Walsh (3621). The Skyland default-page entry's comment now
records that all 14 picker IDs are verified. `config.toml` gains
seven toggles (`skyland_2763`, `skyland_2766`, `skyland_2770`,
`skyland_2771`, `skyland_2778`, `skyland_3370`, `skyland_3621`),
all true. All other entries unchanged.

### Follow-ups for a later cycle

- **More per-location Bushel probes (one GET each):** the Skyland
  picker is fully swept — no IDs remain. Smithfield has 26 East
  Region locations still open (1669, 1670, 1671, 1672, 1673, 1674,
  1675, 1676, 1678, 1679, 1681, 1682, 1683, 1684, 1685, 1686, 1687,
  1688, 1689, 1690, 1691, 2064, 2065, 2066, 2067, 2179 — from the
  saved Cycle 11 East Region link list). Probe a few per cycle,
  not in bulk.
- **Hugoton / Vilas - Walsh staleness watch:** the 3370 and 3621
  widget headers were dated Nov 18, 2026 while the other five
  Cycle 14 pages were Nov 19 — check on the next fetch whether
  they refresh daily or lag, as with Chadbourn (2294).
  **Cycle 22 (2026-11-19) re-check: STILL Nov 18 at both, row
  counts unchanged (6 and 5) — second consecutive stale probe;
  the one-day lag is persistent, like Chadbourn.**
- **Registry wiring (coordinator):** the seven new Cycle 14
  `BUSHEL_SITES` entries (`skyland_2763`, `skyland_2766`,
  `skyland_2770`, `skyland_2771`, `skyland_2778`, `skyland_3370`,
  `skyland_3621`) and their `fetch_` functions are in
  `bushel_source.py`; `source_registry.py` wiring is the
  coordinator's step.

## United States — Cycle 15 Smithfield East Region batch B (2026-11-19)

Probed the next six Smithfield East Region per-location targets
after the Cycle 14 batch, one polite GET each (User-Agent
`GrainHub-Research/1.0`, 30 s timeout, no retries, ~2 s spacing)
— 6 GETs total, budget respected. The list page itself was
recovered from the saved Cycle 11 page
(`/tmp/cycle11/smithfield_fccp.html`), so no GET was spent
re-fetching it; the six targets (1683 Creswell, 1684 Warsaw,
1685 Harpster, 1686 Morral, 1687 Darlington, 1688 Lake City)
are the next six IDs in numeric order after the six already
verified in Cycle 14 (1669–1674), skipping the 1675–1682 block
being probed in parallel by the sibling batch A. All six served
200 and parsed cleanly with the existing generic parser — no
parser change needed. Raw HTML saved to `/tmp/cycle15/` scratch
only, never the repo. No prices are recorded here — row counts,
location/commodity breakdowns and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 6 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **6** | Creswell (2), Warsaw (2), Harpster (1), Morral (1), Darlington (1), Lake City (1) — 8 rows total |
| New parser gap | 0 | All six pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) |
| Stale widget headers | 0 | All six headers dated Thursday, November 19, 2026 — fresh, no Chadbourn-style lag |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Smithfield Grain — Creswell (1683) | https://smithfieldgrain.com/cashbidssingle-1683 | 200 | **Yes — 2 rows** (Corn 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Creswell, NC" (mapped to "Creswell" in the registry entry); the list page calls this location Creswell Feed Mill | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry; the East Region link-list entry stays disabled); registry entry `smithfield_creswell` + `fetch_smithfield_creswell()` added in Cycle 15 |
| Smithfield Grain — Warsaw (1684) | https://smithfieldgrain.com/cashbidssingle-1684 | 200 | **Yes — 2 rows** (Corn 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Warsaw, NC" (mapped to "Warsaw") | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_warsaw` + `fetch_smithfield_warsaw()` added in Cycle 15 |
| Smithfield Grain — Harpster (1685) | https://smithfieldgrain.com/cashbidssingle-1685 | 200 | **Yes — 1 row** (Corn), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is bare "Harpster" (**no state suffix** — the first Smithfield h2 without one; the list page calls it Harpster Elevator, OH). Thin page: a single Corn row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_harpster` + `fetch_smithfield_harpster()` added in Cycle 15 |
| Smithfield Grain — Morral (1686) | https://smithfieldgrain.com/cashbidssingle-1686 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Morral, OH" (mapped to "Morral"). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_morral` + `fetch_smithfield_morral()` added in Cycle 15 |
| Smithfield Grain — Darlington (1687) | https://smithfieldgrain.com/cashbidssingle-1687 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Darlington, SC" (mapped to "Darlington"). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_darlington` + `fetch_smithfield_darlington()` added in Cycle 15 |
| Smithfield Grain — Lake City (1688) | https://smithfieldgrain.com/cashbidssingle-1688 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Lake City, SC" (mapped to "Lake City"). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_lake_city` + `fetch_smithfield_lake_city()` added in Cycle 15 |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Smithfield 1683 / 1684 / 1685 / 1686 / 1687 / 1688 — parse
  cleanly.** `parse_bushel_html` run against each saved
  `/tmp/cycle15` HTML returns status ok with 2 / 2 / 1 / 1 / 1 /
  1 rows and the mapped town locations. No `bushel_source.py`
  change needed for the widget shape — the registry additions
  are the only code change.

### Tests

6 new tests in `tests/test_bushel_cycle15_smithfield_b.py` (one per
location: registry entry exists + synthetic-fixture parse, all
fixture values invented). Full API suite: **623 passed, 0
failed** (Cycle 14 baseline 617).

### Reclassifications applied (`us_elevators_urls.toml`)

Six new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Smithfield Grain — Creswell (1683), Warsaw
(1684), Harpster (1685), Morral (1686), Darlington (1687),
Lake City (1688). `config.toml` gains six toggles
(`smithfield_creswell`, `smithfield_warsaw`,
`smithfield_harpster`, `smithfield_morral`,
`smithfield_darlington`, `smithfield_lake_city`), all true.
The East Region link-list entry stays disabled. All other
entries unchanged.

### Follow-ups for a later cycle

- **More Smithfield per-location probes (one GET each):** 14 East
  Region locations still open after this batch (1675, 1676,
  1678, 1679, 1681, 1682, 1689, 1690, 1691, 2064, 2065, 2066,
  2067, 2179 — from the saved Cycle 11 East Region link list);
  the sibling batch A is probing 1675–1682 in parallel, so the
  combined Cycle 15 remainder will be smaller. The next batch
  after both is 1689, 1690, 1691, 2064, 2065, 2066. Note 2064
  is a second Kinston target (JCH - Kinston Elevator),
  distinct from 1671; 2065/2066 are the remaining JCH targets
  (Deep Run Feed Mill / Jones County Elevator, per the list
  page). Probe a few per cycle, not in bulk. **Cycle 16
  (2026-11-19):** that next batch is done — 1689 Nichols, 1690
  Petersburg, 1691 Waverly, 2064 Kinston JCH, 2065 Jones
  County, 2066 Deep Run JCH all probed and enabled; only 2067
  and 2179 still open, plus the Raeford re-probe.
  **Cycle 16 loose ends (2026-11-19):** those are done too —
  2067 Lapaz (2 Corn rows) and 2179 Hamer (1 Soybeans row)
  probed and enabled; Raeford re-probed and still empty (not
  registered). The East Region list is now fully covered except
  Raeford; see the Cycle 16 loose-ends section.
- **Smithfield row counts:** Cycle 15 batch B revises the Cycle
  14 full-page expectation again — only Creswell and Warsaw
  carry 2 rows; the other four are thin 1-row pages (Corn for
  Harpster, Soybeans for Morral/Darlington/Lake City). The
  3-row pages (Clinton, Hobbsville, Kinston, LaGrange, Mount
  Olive) and the 1–2-row pages are both common; row count is
  per-location, not a family trait.
- **Smithfield outside NC:** 1685–1688 are the first verified
  Smithfield targets outside North Carolina (OH, SC). The h2
  state suffix follows the location (", OH", ", SC") — except
  Harpster, whose h2 is bare "Harpster". The parser's
  `location_labels` mapping handles both shapes; no parser
  change was needed.
- **Registry wiring (coordinator):** the six new Cycle 15
  registry entries (`smithfield_creswell`, `smithfield_warsaw`,
  `smithfield_harpster`, `smithfield_morral`,
  `smithfield_darlington`, `smithfield_lake_city` in
  `BUSHEL_SITES`) and their `fetch_` functions are in
  `bushel_source.py`; `source_registry.py` wiring is the
  coordinator's step.

## United States — Cycle 15 Smithfield East Region batch A (2026-11-19)

Probed the next six Smithfield East Region per-location targets,
one polite GET each (User-Agent `GrainHub-Research/1.0`, ~2 s
spacing, no retries) — 6 GETs total, budget respected. The list
page itself was recovered from the saved Cycle 11 page
(`/tmp/cycle11/smithfield_fccp.html`), so no GET was spent
re-fetching it; the six targets (1675 Raeford, 1676 Red Springs,
1678 Walstonburg, 1679 Weeksville, 1681 The Chief Feed Mill,
1682 Laurinburg Feed Mill) are the next six IDs in numeric order
after the Cycle 14 batch (1669–1674). Five served 200 with
static rows and parsed cleanly with the existing generic parser
— no parser change needed. Raw HTML saved to `/tmp/cycle15/`
scratch only, never the repo. No prices are recorded here — row
counts, location/commodity breakdowns and widget patterns only.
A parallel Cycle 15 batch B probed 1683–1688 in the same cycle.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 6 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **5** | Red Springs (1), Walstonburg (3), Weeksville (2), The Chief Feed Mill (2), Laurinburg Feed Mill (2) — 10 rows total |
| Empty widget, 0 rows (not registered) | **1** | Raeford (1675): 200, but the page is the generic site shell with an empty `.cbmod` widget — no location h2, no header date, parser status "empty" |
| New parser gap | 0 | All five row-carrying pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape) |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Smithfield Grain — Raeford (1675) | https://smithfieldgrain.com/cashbidssingle-1675 | 200 | **No — 0 rows** (parser status "empty": "cash-bid widget found but no bid rows parsed") | An **empty `.cbmod` widget shell** on the generic site shell: no location h2, no "Raeford" text anywhere, no widget header date, no Delivery/Bid table. The page is the standard nav/footer shell ("Data provided by Bushel", "All prices delayed 10 minutes") with no location-specific content — the widget rendered no rows server-side at probe time | **Not registered.** No `BUSHEL_SITES` entry, no toml entry, no test fixture from live HTML. **Re-probe in a later cycle** before ever registering it — it may be a temporarily empty feed rather than a dead location |
| Smithfield Grain — Red Springs (1676) | https://smithfieldgrain.com/cashbidssingle-1676 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Red Springs, NC" (mapped to "Red Springs" in the registry entry). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry; the East Region link-list entry stays disabled); registry entry `smithfield_red_springs` + `fetch_smithfield_red_springs()` added in Cycle 15 batch A |
| Smithfield Grain — Walstonburg (1678) | https://smithfieldgrain.com/cashbidssingle-1678 | 200 | **Yes — 3 rows** (Corn 1, Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Walstonburg, NC" (mapped to "Walstonburg") | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_walstonburg` + `fetch_smithfield_walstonburg()` added in Cycle 15 batch A |
| Smithfield Grain — Weeksville (1679) | https://smithfieldgrain.com/cashbidssingle-1679 | 200 | **Yes — 2 rows** (Soybeans 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Weeksville, NC" (mapped to "Weeksville"). No Corn row on this page | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_weeksville` + `fetch_smithfield_weeksville()` added in Cycle 15 batch A |
| Smithfield Grain — The Chief Feed Mill (1681) | https://smithfieldgrain.com/cashbidssingle-1681 | 200 | **Yes — 2 rows** (Corn 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is **"Rose Hill, NC"** — the list page calls this target The Chief Feed Mill, but the live page labels it by the mill's town; the registry entry maps it to "Rose Hill" | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_chief_feed_mill` + `fetch_smithfield_chief_feed_mill()` added in Cycle 15 batch A |
| Smithfield Grain — Laurinburg Feed Mill (1682) | https://smithfieldgrain.com/cashbidssingle-1682 | 200 | **Yes — 2 rows** (Corn 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Laurinburg Feed Mill, NC" (mapped to "Laurinburg Feed Mill", as with Bladenboro Feed Mill in Cycle 13). Distinct from any Laurinburg elevator target — there is none on the list | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_laurinburg_feed_mill` + `fetch_smithfield_laurinburg_feed_mill()` added in Cycle 15 batch A |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Smithfield 1676 / 1678 / 1679 / 1681 / 1682 — parse
  cleanly.** `parse_bushel_html` run against each saved
  `/tmp/cycle15` HTML with its registry `site=` returns status ok
  with 1 / 3 / 2 / 2 / 2 rows and the mapped locations (Rose Hill
  for 1681). No `bushel_source.py` change needed for the widget
  shape — the registry additions are the only code change.
- **Smithfield 1675 — parses empty.** The same call against the
  saved `/tmp/cycle15` HTML returns status "empty", 0 rows, no
  location. The `.cbmod` div exists but carries no
  `.cbCommodity` rows; a test guards that the target stays
  unregistered.

### Tests

6 new tests in `tests/test_bushel_cycle15_smithfield.py` (one per
verified location: registry entry exists + synthetic-fixture
parse, all fixture values invented; plus a negative test that
Raeford has no registry entry and that an empty `.cbmod` widget
parses to status "empty"). Full API suite: **629 passed, 0
failed** (Cycle 14 baseline 617 + 6 batch-A tests + 6 sibling
batch-B tests in `tests/test_bushel_cycle15_smithfield_b.py`,
which landed in the tree while this batch was running).

### Reclassifications applied (`us_elevators_urls.toml`)

Five new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Smithfield Grain — Red Springs (1676),
Walstonburg (1678), Weeksville (1679), The Chief Feed Mill
(1681), Laurinburg Feed Mill (1682). `config.toml` gains five
toggles (`smithfield_red_springs`, `smithfield_walstonburg`,
`smithfield_weeksville`, `smithfield_chief_feed_mill`,
`smithfield_laurinburg_feed_mill`), all true. Raeford (1675)
gets no entry anywhere. The East Region link-list entry stays
disabled. All other entries unchanged.

### Follow-ups for a later cycle

- **Raeford (1675) re-probe (one GET):** the only Smithfield
  target so far to serve an empty widget. Re-fetch
  `/cashbidssingle-1675` in a later cycle; if it then carries
  rows, register it like the others. If it stays empty across
  two probes, treat it as a location that posts no public bids
  and stop spending GETs on it. **Cycle 16 (2026-11-19):**
  re-probed — still empty (HTTP 200, generic shell, empty
  `.cbmod` widget, 0 rows, status "empty"); NOT registered, and
  no further re-probe is planned. See the Cycle 16 loose-ends
  section.
- **More Smithfield per-location probes (one GET each):** 8 East
  Region locations still open (1689 Nichols, 1690 Petersburg,
  1691 Waverly Feed Mill, 2064 JCH - Kinston, 2065 JCH - Jones
  County, 2066 JCH - Deep Run Feed Mill, 2067 Lapaz, 2179
  Hamer — from the saved Cycle 11 East Region link list).
  Probe a few per cycle, not in bulk. Note 2064 is a second
  Kinston target (JCH - Kinston Elevator), distinct from 1671.
- **Registry wiring (coordinator):** the five new Cycle 15 batch
  A registry entries (`smithfield_red_springs`,
  `smithfield_walstonburg`, `smithfield_weeksville`,
  `smithfield_chief_feed_mill`,
  `smithfield_laurinburg_feed_mill` in `BUSHEL_SITES`) and their
  `fetch_` functions are in `bushel_source.py`;
  `source_registry.py` wiring is the coordinator's step (that
  file is coordinator-only this cycle).
- **Freshness:** all five batch-A widget headers are dated
  Thursday, November 19, 2026 — fresh, no Chadbourn-style lag
  on this batch.
- **Cycle 16 (2026-11-19):** this batch is now done — 1689
  Nichols, 1690 Petersburg, 1691 Waverly, 2064 Kinston JCH,
  2065 Jones County, 2066 Deep Run JCH all probed and enabled
  (see the Cycle 16 section). Only 2 East Region locations
  still open (2067 Lapaz, 2179 Hamer) plus the Raeford re-probe.
  **Cycle 16 loose ends (2026-11-19):** those are done too —
  2067 Lapaz and 2179 Hamer probed and enabled, Raeford
  re-probed and still empty (not registered). The East Region
  list is now fully covered except Raeford; see the Cycle 16
  loose-ends section.

## United States — Cycle 16 Smithfield East Region (2026-11-19)

Probed the next six Smithfield East Region per-location targets,
one polite GET each (User-Agent `GrainHub-Research/1.0`, ~2 s
spacing, no retries) — 6 GETs total, budget respected. The list
page itself was recovered from the saved Cycle 11 page
(`/tmp/cycle11/smithfield_fccp.html`), so no GET was spent
re-fetching it; the six targets (1689 Nichols, 1690 Petersburg,
1691 Waverly, 2064 JCH - Kinston, 2065 JCH - Jones County,
2066 JCH - Deep Run Feed Mill) are the next six IDs in numeric
order after the Cycle 15 batches (1683–1688 and 1675–1682).
All six served 200 and parsed cleanly with the existing
generic parser — no parser change needed. Raw HTML saved to
`/tmp/cycle16/` scratch only, never the repo. No prices are
recorded here — row counts, location/commodity breakdowns and
widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 6 | Every probed target served (no 404s, blocks, or empty bodies) |
| Static bid rows visible in static HTML | **6** | Nichols (1), Petersburg (4), Waverly (7), Kinston JCH (3), Jones County (3), Deep Run JCH (2) — 20 rows total |
| New parser gap | 0 | All six pages are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape); the parser already normalizes the widget's "Sorghum" header to "Grain Sorghum" |
| Stale widget headers | 0 | All six headers dated Thursday, November 19, 2026 — fresh, no Chadbourn-style lag |
| Empty widgets | 0 | No Raeford-style empty widget in this batch |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Smithfield Grain — Nichols (1689) | https://smithfieldgrain.com/cashbidssingle-1689 | 200 | **Yes — 1 row** (Soybeans), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Nichols, SC" (mapped to "Nichols"). Thin page: a single Soybeans row | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry; the East Region link-list entry stays disabled); registry entry `smithfield_nichols` + `fetch_smithfield_nichols()` added in Cycle 16 |
| Smithfield Grain — Petersburg (1690) | https://smithfieldgrain.com/cashbidssingle-1690 | 200 | **Yes — 4 rows** (Corn 1, Wheat 1, Soybeans 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Petersburg, VA" (mapped to "Petersburg"); the Soybeans rows share one `.cbCommodity` block, two data rows | **Collector-ready:** `parse_bushel_html` verified status ok, 4 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_petersburg` + `fetch_smithfield_petersburg()` added in Cycle 16 |
| Smithfield Grain — Waverly (1691) | https://smithfieldgrain.com/cashbidssingle-1691 | 200 | **Yes — 7 rows** (Corn 3, Wheat 2, Grain Sorghum 2), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Waverly, VA" (mapped to "Waverly"). The widget publishes the sorghum block as "Sorghum"; the parser normalizes it to "Grain Sorghum". **The fattest Smithfield page yet (7 rows) and the first to carry Grain Sorghum** | **Collector-ready:** `parse_bushel_html` verified status ok, 7 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_waverly` + `fetch_smithfield_waverly()` added in Cycle 16 |
| Smithfield Grain — Kinston JCH (2064) | https://smithfieldgrain.com/cashbidssingle-2064 | 200 | **Yes — 3 rows** (Corn 1, Wheat 1, Soybeans 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Kinston JCH, NC" (mapped to "Kinston JCH" — the list page calls it JCH - Kinston Elevator). **A second Kinston target, distinct from smithfield_kinston (1671, Kinston Elevator)** | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_kinston_jch` + `fetch_smithfield_kinston_jch()` added in Cycle 16 |
| Smithfield Grain — Jones County (2065) | https://smithfieldgrain.com/cashbidssingle-2065 | 200 | **Yes — 3 rows** (Corn 1, Wheat 1, Soybeans 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Jones County, NC" (mapped to "Jones County"; the list page calls it JCH - Jones County Elevator) | **Collector-ready:** `parse_bushel_html` verified status ok, 3 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_jones_county` + `fetch_smithfield_jones_county()` added in Cycle 16 |
| Smithfield Grain — Deep Run JCH (2066) | https://smithfieldgrain.com/cashbidssingle-2066 | 200 | **Yes — 2 rows** (Corn 1, Wheat 1), widget header dated Nov 19, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Deep Run JCH, NC" (mapped to "Deep Run JCH"; the list page calls it JCH - Deep Run Feed Mill) | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_deep_run_jch` + `fetch_smithfield_deep_run_jch()` added in Cycle 16 |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Smithfield 1689 / 1690 / 1691 / 2064 / 2065 / 2066 — parse
  cleanly.** `parse_bushel_html` run against each saved
  `/tmp/cycle16` HTML returns status ok with 1 / 4 / 7 / 3 / 3 /
  2 rows and the mapped locations ("Kinston JCH" and "Deep Run
  JCH" for the two JCH h2s). No `bushel_source.py` change needed
  for the widget shape — the registry additions are the only
  code change.

### Tests

6 new tests in `tests/test_bushel_cycle16_smithfield.py` (one per
verified location: registry entry exists + synthetic-fixture
parse, all fixture values invented). No negative test in this
batch — no empty widget was served (the Raeford empty-widget
case is covered in `test_bushel_cycle15_smithfield.py`). Full
API suite: **635 passed, 0 failed** (Cycle 15 baseline 629 + 6
new Cycle 16 tests).

### Reclassifications applied (`us_elevators_urls.toml`)

Six new `[[us.elevators]]` entries, all `type = "bushel"`,
`enabled = true`: Smithfield Grain — Nichols (1689),
Petersburg (1690), Waverly (1691), Kinston JCH (2064), Jones
County (2065), Deep Run JCH (2066). `config.toml` gains six
toggles (`smithfield_nichols`, `smithfield_petersburg`,
`smithfield_waverly`, `smithfield_kinston_jch`,
`smithfield_jones_county`, `smithfield_deep_run_jch`), all
true. The East Region link-list entry stays disabled. All other
entries unchanged.

### Follow-ups for a later cycle

- **Raeford (1675) re-probe (one GET):** the only Smithfield
  target so far to serve an empty widget. Re-fetch
  `/cashbidssingle-1675` in a later cycle; if it then carries
  rows, register it like the others. If it stays empty across
  two probes, treat it as a location that posts no public bids
  and stop spending GETs on it. **Cycle 16 loose ends
  (2026-11-19):** re-probed — still empty (0 rows, status
  "empty"), NOT registered, and no further re-probe is planned.
  See the Cycle 16 loose-ends section.
- **More Smithfield per-location probes (one GET each):** only 2
  East Region locations still open (2067 Lapaz, 2179 Hamer —
  from the saved Cycle 11 East Region link list). Probe them
  in a later cycle, one GET each. After those, the 31-location
  East Region list is fully covered except Raeford (1675),
  pending its re-probe. **Cycle 16 loose ends (2026-11-19):**
  both probed and enabled (Lapaz 2 Corn rows, Hamer 1 Soybeans
  row); the East Region list is now fully covered except
  Raeford. See the Cycle 16 loose-ends section.
- **Registry wiring (coordinator):** the six new Cycle 16
  registry entries (`smithfield_nichols`,
  `smithfield_petersburg`, `smithfield_waverly`,
  `smithfield_kinston_jch`, `smithfield_jones_county`,
  `smithfield_deep_run_jch` in `BUSHEL_SITES`) and their
  `fetch_` functions are in `bushel_source.py`;
  `source_registry.py` wiring is the coordinator's step (that
  file is coordinator-only this cycle).
- **Freshness:** all six Cycle 16 widget headers are dated
  Thursday, November 19, 2026 — fresh, no Chadbourn-style lag
  on this batch.
- **Smithfield row counts:** Waverly (7 rows) breaks the Cycle
  15 batch-B expectation that Smithfield pages top out at 3
  rows; the new ceiling is 7, and Grain Sorghum is now a
  fourth commodity on Smithfield pages (Corn, Soybeans, Wheat,
  Grain Sorghum). Row count and commodity mix are per-location,
  not a family trait.

## United States — Cycle 16 Smithfield loose ends + Andersons confirmatory checks (2026-11-19)

Closed the two loose ends left by Cycle 15, in one 5-GET task
(User-Agent `GrainHub-Research/1.0`, ~2 s spacing, no retries):
the Raeford (1675) re-probe, the last two open Smithfield East
Region IDs (2067 Lapaz, 2179 Hamer), and the two low-odds
Andersons confirmatory checks named in the Cycle 15 Andersons
section (Maumee facility page, Ohio per-state list page). The
Smithfield location names come from the saved Cycle 11 list page
(`/tmp/cycle11/smithfield_fccp.html`), so no GET was spent
re-fetching it. Raw HTML saved to `/tmp/cycle16/` scratch only,
never the repo. No prices are recorded here — row counts,
location/commodity breakdowns and widget patterns only.

### Counts

| Status | Count | Meaning |
|---|---|---|
| HTTP 200 | 5 | Every probed target served (no 404s, blocks, or empty bodies) |
| Smithfield static bid rows visible in static HTML | **2 of 3** | Lapaz (2 Corn rows), Hamer (1 Soybeans row); Raeford still empty, 0 rows |
| Andersons static bid rows visible in static HTML | **1 of 2 pages** | Maumee facility page carries 3 static bid tables (see below) — but the page states the data is provided by Barchart Solutions, so it is licensed data and NOT collected; the Ohio list page carries no bids |
| New parser gap | 0 | Lapaz and Hamer are the standard wrapped `.cbCommodity` + 7-col shape (the FAC shape); the parser already handles both |
| Stale widget headers | 1 | Hamer's header is dated Wednesday, November 18, 2026 — a day stale, like Chadbourn (Cycle 13); Lapaz is fresh (Nov 19) |
| Empty widgets | 1 | Raeford, second probe in a row |

### Per-site results

| Company | URL probed | HTTP | Static bid rows? | Widget / pattern in static HTML | Collector pattern |
|---|---|---|---|---|---|
| Smithfield Grain — Raeford (1675), re-probe | https://smithfieldgrain.com/cashbidssingle-1675 | 200 | **No — still empty** (0 rows, status "empty") | Generic site shell with an empty `.cbmod` widget: 1 `cbmod` marker, 0 `cbCommodity`, 0 `sevenColumnsBigFirst`; no location h2, no header date — identical shape to the Cycle 15 batch-A probe | **NOT registered** (second empty probe in a row). Per the Cycle 15 batch-A follow-up, treat Raeford as a location that posts no public bids and stop spending GETs on it. Pinned by a negative test in `tests/test_bushel_cycle16_raeford.py` (unknown site key + empty-widget shape parses to status "empty") |
| Smithfield Grain — Lapaz (2067) | https://smithfieldgrain.com/cashbidssingle-2067 | 200 | **Yes — 2 rows** (Corn 2), widget header dated Thursday, November 19, 2026 (fresh) | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Lapaz, IN" (mapped to "Lapaz"; the list page calls it IN - Lapaz Elevator (LAP)) | **Collector-ready:** `parse_bushel_html` verified status ok, 2 rows, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_lapaz` + `fetch_smithfield_lapaz()` added in Cycle 16 |
| Smithfield Grain — Hamer (2179) | https://smithfieldgrain.com/cashbidssingle-2179 | 200 | **Yes — 1 row** (Soybeans), widget header dated Wednesday, November 18, 2026 | Bushel **`.cbmod` widget in static HTML**, standard wrapped shape — the FAC shape. Location h2 is "Hamer, SC" (mapped to "Hamer"; the list page calls it SC - Hamer Elevator). Thin page: a single Soybeans row. **Header a day stale** — the Hamer widget had not refreshed at probe time, like Chadbourn (Cycle 13); worth watching on the next fetch, not a parser issue. **Cycle 22 (2026-11-19): re-check — header STILL "Cash bids for Wednesday, November 18, 2026", still 1 Soybeans row, `parse_bushel_html` status ok. Second consecutive stale probe; persistent one-day lag.** | **Collector-ready:** `parse_bushel_html` verified status ok, 1 row, against saved HTML — no parser change needed. **Enabled** (new toml entry); registry entry `smithfield_hamer` + `fetch_smithfield_hamer()` added in Cycle 16 |
| The Andersons — Maumee facility page | https://www.andersonsgrain.com/locations/oh/maumee/ | 200 | **Yes — static tables, but NOT collectable (see right)** | Facility info page (title "Maumee Grain Elevator - The Andersons Trade Group", h1 "Maumee"): Hours, Discount Schedules, Important Info, DP/Storage Rates, Contacts, About This Facility, Google Maps embed — **plus 3 static `styled-table` bid tables** under a "Cash Bids" tab ("Corn, Beans, Red Wheat"): columns Delivery / Bid / Basis / Futures / Chg / Symbol / Last Trade; Corn 10 delivery rows, Soybeans 10, Red Wheat 3 (23 rows total); last-trade stamps in the early-morning hours. The "Bid and Basis Charts" section itself is JS-driven (empty-src `chartFrame` iframe), but the tables are plain static HTML. Disclaimer on the page: cash prices update at 10-minute intervals through the CBOT day session, basis values update daily at 5:10 pm EST, all bids subject to change | **NOT collected, NOT registered.** The page carries a Barchart disclaimer ("All market data is provided by Barchart Solutions", `barcharts-disclaimer` div, link to `barchart.com/solutions`) — the tables are **Barchart-licensed data**, out of scope for GrainHub collection under the no-licensed-data guardrail. This finding does NOT reopen the Andersons: the closure now rests on licensing, not on absence of static rows (see the Cycle 16 addendum under "The Andersons — GRAINweb investigation (Cycle 13)"). No collector, no toml entry |
| The Andersons — Ohio per-state list page | https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/ | 200 | **No** | Title "Ohio - The Andersons Trade Group". Same directory substance as the master list page (Cycle 15): body lists the same 7 Ohio facilities (Greenville, Maumee, Metamora, Port William, Toledo - Edwin Dr, Toledo - Kuhlman Dr, Toledo - Reynolds Rd) in 3 small layout tables (2 facility names each); the page also carries the full 41-facility directory in its nav links (all states). 0 bid tables, 0 price-like strings, 0 `styled-table` elements | None — directory only, confirms the master-list finding. No collector |

### Static-HTML sites — parser verification (saved HTML only, no new fetch)

- **Smithfield 2067 / 2179 — parse cleanly.**
  `parse_bushel_html` run against each saved `/tmp/cycle16`
  HTML with its new registry site returns status ok with 2
  rows (Lapaz, Corn 2) / 1 row (Hamer, Soybeans 1) and the
  mapped locations ("Lapaz", "Hamer"). No `bushel_source.py`
  change needed for the widget shape — the registry additions
  are the only code change.
- **Smithfield 1675 (Raeford) — still empty.**
  `parse_bushel_html` run against the saved `/tmp/cycle16`
  HTML returns status "empty", 0 rows, location None — same as
  Cycle 15 batch A. No registry entry, by design.

### Tests

3 new tests in `tests/test_bushel_cycle16_raeford.py` (Lapaz and
Hamer: registry entry exists + synthetic-fixture parse, all
fixture values invented; Raeford: negative test — unknown site
key raises `KeyError` and the empty-widget shape parses to
status "empty"). Full API suite: **638 passed, 0 failed**
(Cycle 15 baseline 629 + 6 sibling Cycle 16 tests + 3 new
tests in this task).

### Reclassifications applied (`us_elevators_urls.toml`)

Two new `[[us.elevators]]` entries, both `type = "bushel"`,
`enabled = true`: Smithfield Grain — Lapaz (2067), Hamer
(2179). `config.toml` gains two toggles (`smithfield_lapaz`,
`smithfield_hamer`), both true. No Andersons entry: the Maumee
tables are Barchart-licensed data and are deliberately not
collected. The East Region link-list entry stays disabled. All
other entries unchanged.

### Follow-ups for a later cycle

- **Smithfield East Region is now fully covered (except
  Raeford).** With Lapaz (2067) and Hamer (2179) enabled, every
  ID on the saved Cycle 11 East Region list page is verified
  except Raeford (1675), which has now served an empty widget
  on two probes (Cycle 15 batch A, Cycle 16). No further
  Smithfield East Region probes are open; do not spend more
  GETs on Raeford unless the widget shape changes.
- **Stale headers to watch:** Hamer's widget header is dated
  November 18, 2026 — a day stale, like Chadbourn (Cycle 13).
  If the collector adds a same-day freshness check, Hamer (and
  Chadbourn) will trip it; that is a data-freshness flag, not a
  parser issue. **Cycle 22 (2026-11-19) re-check: STILL Nov 18,
  still 1 Soybeans row — second consecutive stale probe; the
  one-day lag is persistent. The watch now covers four locations
  (Chadbourn, Hamer, Hugoton, Vilas - Walsh), all still one day
  stale.**
- **The Andersons is now fully closed.** Both confirmatory
  checks named in Cycle 15 are done: the Maumee facility page
  and the Ohio per-state list page. The Maumee check surfaced
  static bid tables, but they are Barchart-licensed data and
  are not collected — so the closure stands, now on licensing
  grounds rather than absence of static rows. No new Andersons
  probe exists: the remaining 40 facility pages would serve
  the same Barchart-licensed tables (do not probe them — the
  answer is already known and the data is out of scope), and
  the only other path (a rendered browser session against the
  GRAINweb picker) is unchanged from Cycle 15.
- **Registry wiring (coordinator):** the two new Cycle 16
  registry entries (`smithfield_lapaz`, `smithfield_hamer` in
  `BUSHEL_SITES`) and their `fetch_` functions are in
  `bushel_source.py`; `source_registry.py` wiring is the
  coordinator's step (that file is coordinator-only this cycle).

## Cycle 17 — basis tracker + source health wiring verified (2026-11-19)

**No rewire was needed.** The Cycle 3 polish backlog item
("source health data feeding the basis tracker") was already
complete: `app/api/routes/basis.py::_load_source_status_map`
reuses the source-health dashboard's own
`build_source_health_rows` (`app/api/routes/source_health.py`)
over the real `ingestion_runs` + `source_health_snapshots`
rows, so the tracker and the dashboard can never disagree
about a source. The dashboard vocabulary `live` / `stale` /
`broken` / `unknown` is reported on basis rows as `healthy` /
`stale` / `broken` / `unknown` (`live` → `healthy`, stated on
every tracker/history response via `source_status_note`).
A source with no ingestion run and no snapshot is `unknown`,
never assumed healthy — including a price row whose source
is not registered in the `sources` table at all.

Two things were confirmed as *not* feeding the status, by
design: the live probe (`app/services/price_source_probe.py`)
is a manual CLI smoke test whose results are not persisted
to any table, so it cannot contribute rows; and the basis
arithmetic itself is untouched — the status is attached at
the route layer (`_attach_source_status`) after
`rank_basis` / `build_basis_history` run, so no basis value
can change because of a health record.

**Cycle 17 additions (tests only, no app code changed):**
three route-level tests in `tests/test_basis_tracker.py`
covering a row from a healthy source, a row from a
stale/broken source, and a row with no health record
(`unknown`, not live) — the same three cases were already
covered in `tests/test_cycle3_polish.py`; the new tests put
them in the basis tracker's own test file, plus a fourth
test pinning the case-insensitive match between a price
row's `source_name` and its health record. API suite after
Cycle 17: **643 passed, 0 failed** (638 Cycle 16 baseline
+ 3 new tests here + 2 tests added concurrently by a
sibling worker in `test_price_history.py`).

### Cycle 17 — price history + report calendar wiring check (2026-11-19)

**Price history / seasonal averages: already wired to real data; one small gap closed.** `GET /api/prices/history` and `GET /api/prices/seasonal` (`app/api/routes/price_history.py`) read real `NormalizedPrice` rows joined to `PriceSnapshot` only — no static or placeholder prices, no interpolation, years with no data reported as missing. Seasonal averages are computed from those same normalized cash prices, *not* from USDA research rows: `ResearchReport` rows hold report metrics (ending stocks, crop progress), not cash prices, so no price is derived from them (the route's note already says this). The one gap: the responses carried no source or date, so an empty state was a bare empty list. Both endpoints now return `source` (normalized prices already in the database; nothing invented/backfilled/estimated) and `as_of` (today's UTC date) on every response, empty or not. The web `/history` page (`apps/web/app/history/page.tsx`) already called the real API and showed honest empty states; it now surfaces the `source`/`as_of` provenance in both empty states. Two new tests in `tests/test_price_history.py` pin `source`/`as_of` on empty and seeded history and seasonal responses (seasonal multi-year mean verified: 2025 $6.00 + 2026 $7.00, ISO week 10 → $6.50).

**Report calendar: already correctly wired; no change needed.** `GET /api/research/calendar` (`app/api/routes/report_calendar.py`) builds the verified 2026 schedule and attaches `ingestion_status` per event from real `ResearchReport` rows (`ingested` with report date/vintage/source/ingested_at, or `not_ingested_yet`, never a fake "available"); report types with no collector (Prospective Plantings / Acreage / Small Grains Summary) are always `not_ingested_yet`, and with no database available the status is `unknown`. Both states were already covered by `tests/test_cycle3_polish.py` (ingested WASDE row, empty database, no-database), so no new calendar tests were added.

## United States — Cycle 17 source audit (2026-11-19)

Audit only: 0 GETs. Every fact below comes from the repo —
`us_elevators_urls.toml`, `config.toml`, `source_registry.py`
(read-only), `bushel_source.py` / `cashbids_embed_source.py` /
`wpdatatables_source.py`, and this catalogue. No collector code
or registry changed; no prices invented.

### Counts (`us_elevators_urls.toml`, after the Cycle 17 fixes below)

| Family | Total | Enabled | Disabled |
|---|---|---|---|
| bushel | 64 | 62 | 2 |
| agricharts | 16 | 13 | 3 (dead 404: Cardinal Ethanol, Gold Eagle, POET) |
| dtn | 16 | 13 | 3 (Luckey Farmers dead 404; Gateway FS, Ray Carroll — Playwright only) |
| agricharts-embed | 11 | 11 | 0 |
| wpdatatables | 1 | 1 | 0 |
| usda | 2 | 2 | 0 |
| unknown | 5 | 0 | 5 |
| stonex | 2 | 0 | 2 |
| unreachable | 3 | 0 | 3 |
| none | 1 | 0 | 1 |
| **Total** | **121** | **102** | **19** |

Before the fixes: 87 enabled / 34 disabled. The 15-entry jump is
entirely the stale-disabled bushel + USDA-mirror entries below.

### Remaining `unknown` / `none` / `unreachable` — full list with verdicts

| Name | URL | Toml | Catalogue verdict |
|---|---|---|---|
| Bunge | https://www.bungeag.com/cash-bids | unknown, off | Do-not-add. `/cash-bids` redirects to a locations archive; "Cash Bids" is nav text only, no bid table (Cycles 1, 6, 8). No replacement URL found. Ontario Bunge is a separate dead entry (`bunge = false`). |
| CGB | https://cgb.com/cgb-grain/ | unknown, off | **Resolved 2026-11-19 (Cycle 18):** cash-bid page found via site navigation — `https://cgbgrain.com/cash-bids/` (linked from `cgb.com/cgb-grain/` → `www.cgbgrain.com` → `/cash-bids`). AgriCharts cash-bids widget (`cgb.agricharts.com/inc/cashbids/cashbids.php?...`); no static bid rows; AgriCharts URL not fetched (licensed feed). USDA SCL lead closed as unnecessary. Open decision is the licensed-feed question, not a missing URL. |
| The Andersons | https://www.andersonsgrain.com | unknown, off | **Closed for static collection.** GRAINweb "MyCashBids" picker (Cycle 11/13); facility pages carry static tables but they are Barchart-licensed data and are NOT collected (Cycle 16 Maumee check). No further probes. Only a rendered browser session against the picker remains, unchanged since Cycle 15. |
| United Coop | https://www.unitedcooperative.com | unknown, off | ATLAS DTN shell on homepage (`dtn-cashbid-tab`); no static bid rows (Cycle 6). DTN Playwright render check needed. Distinct org from the Webster City, IA Bushel site (`unitedcoop.com`, enabled). |
| Ursa Farmers Coop | https://www.ursacoop.com | unknown, off | DTN page: "Local Cash Bids loading..." with empty Basis/Cash cells in static HTML (Cycle 6). DTN Playwright render check needed (`us_dtn_source.py` parses rendered tables). |
| CRC | https://www.centralregioncoop.com/grain | **stonex, off** (reclassified this audit) | StoneX family: homepage `#cash-bids-futures` section holds a lazy-loaded StoneX component iframe, no static bid rows (Cycles 9–10). Same family as Frontier Coop / UFC. No static route; render check only. |
| CVA | https://www.cvacoop.com/cash-bids | unreachable, off | HTTP 202, empty body — same in Cycle 1, Cycle 10, and Cycle 18 (re-checked 2026-11-19: still 202, 0 bytes). Do not retry aggressively; a later re-check is the only open item. |
| Landus | https://www.landus.ag/businesses/grain/grain-bids | unreachable, off | HTTP 429, Vercel Security Checkpoint page (JS required) — blocked, no retry (Cycle 10); re-checked 2026-11-19 (Cycle 18): still 429, checkpoint page, 25,097 bytes, no bid widget. |
| Mercer Landmark | https://www.mercerlandmark.com/cash-bids | unreachable, off | HTTP 522, empty body — same in Cycle 1, Cycle 10, and Cycle 18 (re-checked 2026-11-19: still 522, 0 bytes). Re-check later only. |
| Star of the West | https://www.starofthewest.com | none, off | Milling-company homepage; zero cash-bid mentions, no grain/bid links — no public bid page, do not add (Cycle 10). |
| UFC | https://www.ufcmn.com | stonex, off | Redirects to Central United Cooperative; Cash Bids section is a StoneX component iframe (`stonehedge.stonex.com/component/bids`, `hideRows=true`) (Cycle 10). No static route; render check only. |

### Mismatches found and fixed in the toml (Cycle 17)

All 17 were clear contradictions between the catalogue's stated
verdict (plus the matching `config.toml` `[sources]` toggle and
`source_registry.py` adapter, both already on) and the toml. No
enabled/disabled state was changed on a guess.

**Enabled (15) — verified sources the toml had left disabled:**

| Entry | Catalogue verdict the toml contradicted |
|---|---|
| FAC, Chandler Feed, Cameron Coop, CGS, Almota Elevator, Williams Gin & Grain, Rugby Farmers Elevator, Lake Norden Farmers Elevator, United Cooperative, Forest River Coop (10) | All verified live in Cycles 4–5 (Bushel `.cbmod` widgets, 2–45 rows each); catalogue Cycle 5 update: "All 11 Bushel sites are now verified live and wired into `source_registry.py`". The toml still carried the Cycle 1 note "Keep disabled until a bushel collector exists" — the collector has existed since Cycle 4 and every one of these already had a registry adapter + a `true` toggle. |
| Ace Ethanol, Alliance Grain (2) | Verified live Cycle 6 (Bushel `.cbmod`, 11 / 10 rows). The catalogue's Cycle 6 section records the reclassification `unknown → bushel` — but it was never applied to the toml, which still said `unknown` / disabled. Fixed: type → `bushel`, enabled. |
| AGP (1) | Verified live Cycle 7 (Bushel via iframe, Chester, NE, 1 row). The catalogue records "Reclassified dtn → bushel (iframe)" — never applied to the toml, which still said `dtn` / disabled. Fixed: type → `bushel`, enabled. |
| James Valley Grain (USDA mirror), FS Grain (USDA mirror) (2) | USDA AMS report mirrors, verified live Cycle 4 (`usda_mirror_source.py`, registry + toggles `usda_mirror_jvg` / `usda_mirror_fsg` already on). The toml still carried the Cycle 1 "Keep disabled until a usda collector exists" note. Fixed: enabled. The two section-header comments (Bushel, USDA) were updated to match. |

**Reclassified, still disabled (1):** CRC `unknown → stonex`
(catalogue Cycles 9–10 place it in the StoneX family with
Frontier Coop / UFC; no static route).

**Comment only (1):** Collwest Grain — the toml said "VERIFY
COUNTRY FIRST"; the country was confirmed Canadian
2026-11-18 (Collingwood, ON; CAD) and the catalogue says it
was "Removed from US list". The comment now records the
confirmed verdict; the entry stays disabled as a record so the
URL is not re-added. Whether to delete the row outright is a
coordinator decision (see remaining work).

**No other catalogue ↔ toml contradiction found.** In
particular: no toml-enabled entry is one the catalogue calls
failed/unprobed (the 13 enabled DTN sites are all widget-present
JS-only, Playwright render check open — not failed); the 3
disabled AgriCharts entries are the confirmed 404s; the
Smithfield link-list entry correctly stays disabled (a link
list, not a bid page); Raeford (1675) correctly has no entry
(empty widget on two probes, not registered).

### Registry / toggle cross-check (read-only)

- **Every `BUSHEL_SITES` key (63), every
  `CASHBIDS_EMBED_SITES` key (13) and `five_star_coop` has a
  matching `config.toml` `[sources]` toggle (`true`) and a
  `source_registry.py` adapter.** No registry entry lacks a
  toggle; no toggle-`true` entry lacks an adapter. Only
  `bunge` and `mapleview` toggles are `false` (both with
  adapters, both disabled by design).
- **Every toml entry has a collection route:** `agricharts`
  (16) and `dtn` (16) via the generic `us_agricharts_source.py`
  / `us_dtn_source.py` orchestrator drivers (no per-site
  adapter needed — the toml itself is the driver);
  `bushel` (64) via `bushel_source.py` except the Smithfield
  link-list entry, which has no `BUSHEL_SITES` key by design;
  `agricharts-embed` (11) via `cashbids_embed_source.py`;
  `wpdatatables` (1) via `wpdatatables_source.py`; `usda` (2)
  via `usda_mirror_source.py`. `stonex` (2), `unknown` (5),
  `unreachable` (3), `none` (1) correctly have no adapter.
- **Two registry keys share one toml row, by design:**
  `pro_coop_21302` and `pro_coop_21302b` are the second and
  third embeds on the PRO Coop homepage — there is a single
  PRO Coop toml entry. No dedicated toml rows needed.
- **`fmn` has a registry adapter + toggle but no US toml
  entry — correct:** it is the Ontario AgriCharts cash page,
  not a US elevator.
- **Drift found (not fixed — coordinator decision):**
  `config.toml`'s own `[[us.elevators]]` list is stale: 30
  entries vs 121 in `us_elevators_urls.toml`. 91 urls-toml
  entries are missing from it (every Cycle 10–16 addition,
  all embed sites, Five Star, all Skyland/Smithfield
  per-location rows, the re-enabled bushel sites), and 4
  entries disagree on type (Agtegra, Heritage Cooperative,
  Linn Coop, Midway Coop: `dtn` in `config.toml` `[us]`,
  `agricharts-embed` in the urls toml and the registry).
  Enabled flags agree (0 mismatches) where both lists have
  the entry. The legacy GrainBidder orchestrator reads
  `config.toml` `[us]`; the FastAPI platform reads the
  registry + `[sources]` toggles. Decide: sync the legacy
  `[us]` list to the urls toml, or deprecate it and point
  the orchestrator at `us_elevators_urls.toml`.

### Remaining work (prioritised)

**Playwright-only (no GET will settle these):**

1. DTN render checks (enabled in toml, widget present, rows
   need a rendered page): Sunrise (classic DTN, companyID
   23043), Ag Partners (modern DTN widget), Al-Corn + Elite
   Octane (captcha strings seen — re-check in a browser),
   Ray Carroll (DTN `index.cfm` iframes), Gateway FS sub-page
   (`/gatewayfs/agriculture/cash-bids`, Next.js + DTN
   classes), United Coop (`unitedcooperative.com`), Ursa
   Farmers Coop. The other enabled DTN sites (Allied, Aurora,
   CFS, Frontier, Green Plains, Kanza, Brubaker, Hoffman,
   Wilton) are the same family — one render-check pass
   covers the set.
2. StoneX render check: Frontier Coop, CRC, UFC — the StoneX
   iframe is a JS app shell behind StoneX auth (Cycle 8
   research: no static-data route). A Playwright render is
   the only open route; if rows do not load, the family is
   closed. Note the Frontier ambiguity: the toml types it
   `dtn` (an ATLAS DTN shell is also on the page) while the
   catalogue treats it as StoneX-primary — the render check
   should settle which widget carries the bids.
3. The Andersons GRAINweb picker — a rendered browser session
   is the only remaining path, and the data it would serve is
   Barchart-licensed on the facility pages, so this is low
   value unless Adam wants a licensed-data decision first.

**GET-probe items (1 GET each, polite, no retries):**

4. CGB — chase the cash-bid module URL from the USDA SCL
   report; do not guess it. **Resolved 2026-11-19 (Cycle 18):**
   found via site navigation instead — `https://cgbgrain.com/cash-bids/`
   (AgriCharts widget; AgriCharts URL not fetched, licensed feed).
   The USDA SCL lead is closed as unnecessary; the remaining
   question is the licensed-feed decision, not a missing URL.
5. CVA (202 empty body) and Mercer Landmark (522) — **done in
   Cycle 18 (2026-11-19):** both re-checked, both unchanged
   (CVA still 202 / 0 bytes; Mercer still 522 / 0 bytes), and
   Landus re-checked too (still 429 Vercel checkpoint). All
   three stay `unreachable` in the toml. No further re-checks
   until a later cycle; odds of change remain low.
6. Bunge — no replacement URL found in Cycles 1/6/8; only
   re-probe if a new URL surfaces.

**Decisions for Adam / coordinator:**

7. Collwest Grain toml row: delete it (catalogue says
   "removed from US list") or keep the disabled record
   (current state after this audit)?
8. `config.toml` `[us.elevators]`: sync the 91 missing
   entries + 4 type fixes, or deprecate the legacy list in
   favour of `us_elevators_urls.toml`?
9. StoneX family (Frontier / CRC / UFC): Playwright-only,
   auth-gated — worth any more effort, or close it?
10. DTN / Barchart licensed-feed decision (open since Cycle
    1): a licensed feed would replace the DTN Playwright
    work and the Andersons question outright.
11. Smithfield + Skyland sweeps are **complete** (Skyland
    14/14 IDs, Smithfield 30/31 — Raeford posts no public
    bids). No further probes on either; do not spend GETs
    on Raeford unless its widget shape changes.

## Cycle 18 — unreachable re-checks (2026-11-19)

Re-check only: exactly 3 GETs, one per site, User-Agent
`GrainHub-Research/1.0`, ~2s spacing, no retries. URLs taken
verbatim from `us_elevators_urls.toml` (not guessed). Raw HTML
saved to `/tmp/cycle18/` only; no prices copied anywhere
(counts and structure only). All three are unchanged from
Cycle 10 — still blocked/empty, so none was registered, no
collector code or tests were added, and the toml
classifications stay `unreachable` (comments updated with the
new check date only).

| Site | URL | Status | Body | Bid widget present? | Rows | Verdict |
|---|---|---|---|---|---|---|
| CVA | https://www.cvacoop.com/cash-bids | HTTP 202 | 0 bytes | No — empty body, no widget family markers (Bushel `.cbmod`, AgriCharts `writeBidRow`/cashbids embed, DTN `CashBidTable`, wpDataTables) | 0 | Still unreachable; unchanged since Cycle 1 |
| Landus | https://www.landus.ag/businesses/grain/grain-bids | HTTP 429 | 25,097 bytes | No — body is the Vercel Security Checkpoint page (`<title>Vercel Security Checkpoint</title>`, JS/browser verification required); no bid widget markers | 0 | Still blocked; no retry |
| Mercer Landmark | https://www.mercerlandmark.com/cash-bids | HTTP 522 | 0 bytes | No — empty body, no widget family markers | 0 | Still unreachable; unchanged since Cycle 1 |

**Cycle 17 follow-ups closed by this check:** item 5 of the
Cycle 17 remaining-work list (CVA / Mercer Landmark single
re-checks) is done — both unchanged, plus Landus re-checked
unchanged. No new follow-ups: the next re-check, if any,
belongs to a later cycle; all three sites have now returned
the same result in three consecutive checks (Cycles 1, 10,
18) for CVA and Mercer Landmark, and two (Cycles 10, 18) for
Landus.

## Cycle 18 — Mae-Mart proxy + CGB cash-bid chase (2026-11-19)

Research only: exactly 4 GETs, User-Agent `GrainHub-Research/1.0`,
~2s spacing, no retries, no prices copied anywhere (endpoints and
structure only). No code changes, no tests. Both Cycle 17 open
items below are now closed as research questions; each leaves one
decision for Adam / the coordinator.

### Mae-Mart futures proxy — identified, not called

GET 1: `http://www.mae-martfarms.com/grain-pricing` (200, 35,952
bytes). The inline pricing JS names the proxy verbatim:

- `var PROXY = '/grain-proxy.php';`
- `fetch(PROXY + '?symbols=' + encodeURIComponent(sym))` — one
  symbol per request, i.e.
  `http://www.mae-martfarms.com/grain-proxy.php?symbols=<SYMBOL>`.
- Symbols are Yahoo Finance format: `ZCZ26=F` (corn), `ZSF27=F`
  (soybeans), `ZWN27=F` (wheat); rye has no symbol and a static
  `manualPrice`.
- Response shape (from the client JS, not from a call): JSON
  keyed by symbol, each entry with `price` and `currency`; when
  `currency === 'USX'` the price is in cents and the client
  divides by 100. `USX` is the Yahoo Finance currency code for
  CBOT grain futures quoted in cents/bu.
- The proxy returns **futures quotes only, not cash bids**. Cash
  is computed client-side as futures + the statically published
  basis. That is why the collector's corn/soy/wheat rows carry
  basis with cash price empty.
- No Barchart / DTN / AgriCharts markers anywhere in the page
  (zero hits for `barchart`, `dtn`, `agricharts`, `yahoo`,
  `stooq`, `cme`, `marketdata`, `alphavantage`).
- Upstream **not confirmed**: the proxy itself was deliberately
  not called. The Yahoo-style `=F` symbols and `USX` handling
  are consistent with a relay of Yahoo Finance public quote
  data, but that is inference from the client JS only — the
  relay could equally call another upstream server-side.

**Next probe (later cycle, 1 GET):**
`GET http://www.mae-martfarms.com/grain-proxy.php?symbols=ZCZ26=F`
— confirm the response shape and whether the relay is live.
**Open decision:** even if live, using it means the collector
would rely on the site's relay of third-party futures data plus
the site's static basis to compute cash. The collector
currently does not call it, and that stays the case until Adam
/ the coordinator decides. No change to `mae_mart_source.py`
in this cycle.

### CGB cash-bid page — found via site navigation

- GET 2: `https://cgb.com/cgb-grain/` (200, 151,242 bytes).
  Corporate grain page: zero hits for `bid`, `cash`, `futures`,
  `market price`, `sitemap` in visible text; no sitemap linked;
  no cash-bid link. It does link `https://www.cgbgrain.com`
  (the CGB Grain division site).
- GET 3: `https://www.cgbgrain.com` (200, 132,258 bytes, final
  `https://cgbgrain.com/`). Homepage links `/cash-bids` with the
  text "View Cash Bids — Select a location and view the current
  bids for different crops." Also links `/futures-quotes/` and
  the `https://my.cgbgrain.com` account portal.
- GET 4: `https://cgbgrain.com/cash-bids/` (200, 102,876 bytes).
  WordPress page, "Cash Bids — Select a location from the
  drop-down menu below." **AgriCharts family**: it embeds
  `<script src="https://cgb.agricharts.com/inc/cashbids/cashbids.php?filter=all&location&commodity&groupby=location&width=100%&showtimestamp=1&hidenav=1&showchart=1&format=table&fields=name,delivery_start,delivery_end,basismonth,futures,futureschange,basis,price&groupheading=table&bidsort=commodity&dateformat=%m/%d/%Y&months=11">`
  plus `//www.agricharts.com/marketdata/quotelib.js`. No static
  bid rows (0 `<table>` elements in the HTML); the location
  dropdown lists 113 CGB locations statically and rows are
  JS-filled by the AgriCharts script.
- The AgriCharts URL was **not fetched** — licensed feed:
  record and stop, per the cycle guardrails. The USDA SCL
  report lead was not needed and was not chased; no GETs were
  spent hunting for the SCL report.

**Cycle 17 follow-ups closed:** item 4 of the Cycle 17
remaining-work list (CGB cash-bid module URL) is resolved — the
URL is `https://cgbgrain.com/cash-bids/`, found by following
links present on the corporate page, not by guessing. The
Mae-Mart proxy question (Cycle 17 audit item (a)) is resolved
as far as identification goes — endpoint pattern, response
shape, and futures-only nature are all on record from the page
source.
**Open decisions:** (1) AgriCharts is licensed data — CGB
belongs in the same licensed-feed decision bucket as the
DTN/Barchart decision (Cycle 17 item 10), not in a missing-URL
bucket. Whether the `cashbids-js.php` static route used by the
generic `cashbids_embed_source.py` collector exists for
`cgb.agricharts.com` is a later-cycle question gated on that
decision. (2) Mae-Mart proxy live-check (1 GET, above) plus the
rely-on-relay decision.

## Cycle 18 — config.toml [[us.elevators]] synced from us_elevators_urls.toml (2026-11-19)

Code only, 0 GETs. The Cycle 17 audit found the drift: `config.toml`
`[[us.elevators]]` held only 30 entries against 121 in
`us_elevators_urls.toml` (91 missing — all Cycle 10–16 additions), plus
4 type mismatches (Agtegra, Heritage Cooperative, Linn Coop, Midway
Coop: `dtn` in config.toml vs `agricharts-embed` in the urls toml /
registry). Enabled flags agreed wherever both lists overlapped.

Fix, per the coordinator's SYNC decision — `config.toml`
`[[us.elevators]]` is now a faithful copy of `us_elevators_urls.toml`
(same entries, same name / url / type / enabled, same order, audit
comments included), generated by script, not by hand:

- New script `GrainBids/grainbids/apps/api/scripts/sync_us_elevators_config.py`
  (run it to re-sync; `--check` exits 1 when out of sync). It replaces
  only the `[[us.elevators]]` section of `config.toml` with the
  corresponding span of `us_elevators_urls.toml`, transplanted verbatim,
  and preserves everything else in `config.toml` byte-for-byte —
  including the `[sources]` toggles, which it never touches. It validates
  its output (both files must parse; the generated list must equal the
  canonical list) before writing, and refuses to write on failure.
  `us_elevators_urls.toml` is canonical: edit entries there, re-run the
  script. Note: the script matches the `[[us.elevators]]` marker only at
  line start — the marker text also appears inside a comment in the urls
  file header.
- Verified after the sync: **121 vs 121 entries, zero per-entry diffs**
  on name / url / type / enabled, in order. The `[sources]` toggles block
  is byte-identical to before the sync; the text before the generated
  section and after it (`[notifications]` onward) is unchanged vs git
  HEAD. (The brief said 122; the actual count in both files is 121 —
  the Cycle 17 audit table above also totals 121.)
- No legacy-only fields existed: every entry in both files carried
  exactly `enabled` / `type` / `name` / `url`, so nothing per-entry had
  to be preserved beyond those four fields. One pre-existing comment was
  not carried over because it lived only in the old config.toml section:
  the Heartland Coop `# verified writeBidRow 2026-11-19` note on its url
  line; the urls toml does not carry it and the classification already
  records the same fact.
- Guard test `GrainBids/grainbids/apps/api/tests/test_source_config_sync.py`
  (stdlib `tomllib` only, 3 tests): asserts the two lists match on
  name / url / type / enabled, that entries carry exactly those four
  fields with unique names, and that the generated header is present in
  `config.toml`. Verified it fails on a tampered copy (one entry removed).
- Behaviour note: the synced list now includes enabled entries whose
  types the legacy GrainBidder does not handle (`bushel`,
  `agricharts-embed`, `usda`, `wpdatatables`, `stonex`, `unknown`,
  `unreachable`, `none`). GrainBidder already skips unknown types with a
  `[SKIP]` line, so the legacy run is unaffected; the FastAPI platform
  reads the registry, not this list.
- Follow-up (not done here): the `[us]` intro comment in `config.toml`
  still says "To add a new elevator: copy a block below…" — that advice
  is now stale, since the section is generated. It sits outside the
  replaced section, so it was left byte-for-byte; the wording should be
  updated to point at `us_elevators_urls.toml` + the sync script.

## Cycle 19 — Mae-Mart futures proxy probe (2026-11-19)

### Probe result: proxy is LIVE and matches the documented contract

- One GET, exactly as Cycle 18 specified: `GET http://www.mae-martfarms.com/grain-proxy.php?symbols=ZCZ26=F`, User-Agent `GrainHub-Research/1.0`.
- The `http://` URL answered 301 (http → https redirect); following the redirect — the same logical probe, as the page's relative `fetch()` call uses the page scheme — returned **HTTP 200, `application/json; charset=utf-8`, 89 bytes**. Response saved to `/tmp/cycle19/mae_mart_proxy_zcz26.json` (not committed; it contains a live price, which is never copied into docs or reports).
- Exact shape: a JSON object keyed by the requested symbol; the entry has a numeric `price`, a string `currency` (`"USX"`), plus numeric `timestamp` and `fetched` fields. This is exactly the contract the page's inline JS documents (JSON keyed by symbol, `price` + `currency`, `USX` = cents → client divides by 100). No extra keys beyond `timestamp`/`fetched`.
- Upstream is still **not confirmed** — the proxy was called, not its upstream. The symbol format and `USX` handling remain consistent with a Yahoo Finance public-quote relay, but that is inference only.

### What changed in the collector

- `mae_mart_source.py`: `fetch_mae_mart()` now fills `futures_price` on corn/soybean/wheat rows from the proxy as an optional second step (`include_futures=True`, one GET per symbol: `ZCZ26=F`, `ZSF27=F`, `ZWN27=F`), following the page's own rule (`USX` cents ÷ 100; any other currency taken as dollars as-is). New helpers: `parse_mae_mart_proxy_json()` (pure parser, ignores malformed/unknown-symbol entries) and `fetch_mae_mart_futures()` (per-symbol failure is skipped, never fatal).
- Graceful degradation: any proxy failure leaves the rows exactly as the static parse produced them (basis only, `futures_price=None`) and appends a "proxy unavailable" note.
- Deliberately NOT changed: `cash_price` is still never computed from futures + basis. Using the site's relay of third-party futures data plus its static basis to compute cash remains an open decision for Adam/the coordinator. Rye is untouched (no futures symbol; static `manualPrice` cash price as before).
- Tests: 7 new tests in `GrainBids/grainbids/apps/api/tests/test_ontario_collectors.py`, all against synthetic fixtures with invented values — proxy JSON cents→dollars, malformed-entry handling, fetch fills all three futures crops, proxy failure leaves rows unchanged, `include_futures=False` skips the proxy, and the proxy is called once per symbol with the contact User-Agent.

## Cycle 19 — Ingestion-orchestrator coverage audit (code only, 0 GETs)

### How the orchestrator enumerates sources

There are three ingestion paths, and they enumerate sources three
different ways — none of them reads `us_elevators_urls.toml` (no
Python code reads that file; it is canonical input only for
`scripts/sync_us_elevators_config.py`, which copies it into
`config.toml` `[[us.elevators]]`).

1. **FastAPI scheduled poll** — `app/jobs/poll_sources.py`
   (`run_once` / `run_loop`) → `poll_due_sources()` →
   `list_due_sources()` → `run_source_refresh()` → `_fetch_with_timeout()`
   (spawned subprocess, per-source timeout) →
   `fetch_with_adapter()` in `app/services/source_registry.py`.
   Enumeration: `Source` rows in the database. `list_due_sources()`
   filters `is_active=True`, `source_type == "automated"`,
   `next_poll_at IS NULL OR next_poll_at <= now` (`next_poll_at` is
   advanced by `update_source_health_state()` after each attempt, so
   due-gating works). It did **not** read the registry, the
   `config.toml` `[sources]` toggles, or either toml list.
2. **Deployed 08:00 / 15:00 America/Toronto job** (deployment
   checklist §4) — `python -m app.jobs.daily_source_ingestion` →
   `run_scheduled_file_ingestion_cycle()`, which iterates only
   `Source` rows with `source_type == "file"` and a `url`. It never
   calls any registry adapter: **0 of 93 adapters** are reached by
   the deployed schedule.
3. **Legacy GrainBidder** —
   `app/platform/market_data/sources/orchestrator/GrainBidder.py`
   `_gather_source_data()` — a hardcoded list of 10 Ontario fetchers
   gated by `config.source_enabled()` (`[sources]` toggles), plus
   `config.toml` `[[us.elevators]]` (121 entries, synced from the
   urls toml in Cycle 18) dispatched by `type` to the generic
   `fetch_us_agricharts(url, name)` / `fetch_us_dtn(url, name,
   playwright)`. It writes CSV/Excel only (plus an optional legacy
   SQLite hook); it does not write to the platform database. Types
   it skips with `[SKIP]`: `bushel`, `agricharts-embed`, `usda`,
   `wpdatatables`, `stonex`, `unknown`, `unreachable`, `none`.
4. **Manual path** — `POST /api/sources/{id}/refresh` →
   `run_source_refresh()` — reaches any single adapter that has a
   `Source` row. Seeding defaults to pilot scope
   (`POST /api/sources/seed`, `scope=pilot`); `scope=all` seeds all
   93 registry adapters.

### Per-family trace (registry → orchestrator)

Registry: **93 adapters**, all fetch functions present and callable
with zero arguments (the `url`-taking ones — `fmn`, `usda_mirror`,
`collwest`, `mae_mart`, `mapleview` — all have module-level URL
defaults). By module: `bushel_source` 62, `cashbids_embed_source`
13, `usda_mirror_source` 2, `wpdatatables_source` 1, `fmn_source` 1,
Ontario playwright/direct modules 14.

| Family | Registry adapters | Scheduled poll before fix | After fix |
| --- | --- | --- | --- |
| bushel (`bushel_source`, direct_dict) | 62 | 0 — none are pilot | all, when seeded + due |
| agricharts-embed (`cashbids_embed_source`) | 13 | 0 | all, when seeded + due |
| wpdatatables (`five_star_coop`) | 1 | 0 | yes, when seeded + due |
| fmn (`fmn_source`) | 1 | 0 | yes, when seeded + due |
| usda mirror (`usda_mirror_source`) | 2 | 0 | yes, when seeded + due |
| Ontario direct_dict | 4 | 0 | yes, when seeded + due |
| Ontario playwright | 9 | 4 of 5 pilot keys are playwright (`agricharts`, `glg`, `hensall`, `snobelen`); `lac`, `bunge`, `dg_global`, `ganaraska`, `wanstead` were unreachable | all, when seeded + due |
| `andersons` (direct/api) | 1 | yes (pilot) | yes |
| US agricharts / DTN generic (`us_agricharts_source`, `us_dtn_source`) | **0 — no adapter keys exist** | unreachable from the FastAPI platform entirely | still unreachable (see below) |

### Gap found and fixed (small, safe)

**`list_due_sources()` filtered on the 5-key pilot allowlist**
(`Source.adapter_key.in_(pilot_keys)`), so the scheduled poll could
only ever reach `agricharts`, `glg`, `hensall`, `snobelen`,
`andersons` — 88 of 93 registry adapters were unreachable on
schedule even after `seed scope=all`. Fix (Cycle 19):
`app/services/source_orchestration.py` — removed the pilot-key
clause; the remaining gates (`is_active`, `source_type ==
"automated"`, due by `next_poll_at`) are unchanged. The pilot set
still governs promotion status (`_promotion_status`) and remains
the default seed scope, so existing pilot-only deployments are
unaffected until an admin explicitly seeds `scope=all`. Regression
tests: 3 new tests in
`GrainBids/grainbids/apps/api/tests/test_source_orchestration_due_sources.py`
(in-memory SQLite, seeded from the registry itself) asserting the
due set equals the enabled registry set, that non-pilot adapters
are included, and that inactive / file-type / not-yet-due rows are
excluded. Verified the 3 tests fail on the pre-fix code and pass
after it. Full API suite: **656 passed, 0 failed** (646 baseline +
3 new + 7 sibling Cycle 19 Mae-Mart tests).

### Gaps documented, NOT fixed (need a coordinator / Adam decision)

1. **The deployed 08:00/15:00 cron runs the file-ingestion job,
   not the poller.** Even after this fix, the scheduled job in the
   deployment checklist (`python -m app.jobs.daily_source_ingestion`)
   reaches 0 registry adapters. `app/jobs/poll_sources.py` exists
   (plus a local Windows task script
   `GrainBids/grainbids/infra/scripts/run-source-poller.ps1`) but
   nothing in the deployment checklist schedules it. Deciding to
   schedule the poller (and at what cadence — a full 93-source sweep
   runs sequentially with per-source timeouts) is a deployment
   decision, not a code change.
2. **US agricharts / DTN have no registry adapters.** 13 enabled
   `agricharts` + 13 enabled `dtn` entries in
   `us_elevators_urls.toml` are reachable only through GrainBidder's
   generic `fetch_us_agricharts(url, name)` /
   `fetch_us_dtn(url, name, playwright)` (CSV output, not the
   platform DB). The registry's `fetch_with_adapter()` calls
   `fetch_fn()` with no arguments, and these functions require a
   URL — so wiring them in needs an adapter-shape change (e.g.
   per-URL adapter keys or a URL parameter on `SourceAdapter`), not
   a one-line fix.
3. **Toggled-off adapters are still seedable/fetchable.**
   `config.toml` `[sources]` has exactly the 93 registry keys, with
   2 off: `bunge = false` (URLs no longer valid) and `mapleview =
   false` (stub only, JS-rendered). The FastAPI orchestrator never
   reads `[sources]` — only GrainBidder does, and only for its 10
   Ontario fetchers — so `seed scope=all` creates active `Source`
   rows for both, manual refresh fetches them, and after this fix
   scheduled polling would too. Decide whether seeding should honor
   the `[sources]` toggles or the toggles are legacy-only and the
   platform's `is_active` is the single gate. (Same class of
   mismatch, name-level only and not asserted as the same source:
   `us_elevators_urls.toml` lists `Bunge`, `Collwest Grain`,
   `United Coop`, `The Andersons`, `Smithfield` as
   `enabled = false` while registry keys `bunge`, `collwest`,
   `united_coop`, `andersons`, `smithfield_*` are enabled — worth
   confirming whether those rows are the same entities or stale
   duplicates before any toggle is trusted.)

## Cycle 20 — seeding + polling honour the `[sources]` toggles (2026-11-19)

Fixes Cycle 19 gap 3 (coordinator decision: seeding SHOULD honour the
toggles). No deployment config or cron was changed; the poller
scheduling gap (Cycle 19 gap 1) is documented, not fixed — see the
deployment checklist §4 step 6.

### What changed (code, 0 GETs)

- New `app/services/source_toggles.py`: single place the FastAPI side
  consults the toggles. It reuses the existing loader
  (`app.platform.market_data.sources.grain_bids.config.config.source_enabled()`),
  which already implements "missing toggle = enabled". Only an
  explicit `false` disables an adapter; a missing/unreadable config
  fails open (everything enabled) rather than breaking seed/poll.
- `seed_sources_from_registry()` now returns a `SeedSourcesResult`
  (`created`, `skipped_disabled`) instead of a plain int, and skips
  any adapter whose toggle is off. `POST /api/sources/seed` returns
  the skipped keys in the response (`skipped_disabled`) so the admin
  can see them.
- `list_due_sources()` filters out rows whose adapter toggle is off,
  even if the `Source` row already exists (defence in depth — a row
  seeded before the toggle was turned off must not keep polling).
  The check is where the due list is built, not inside the
  per-source fetch subprocess.

### Effect today

`config.toml` `[sources]` has exactly the 93 registry keys, 2 off:
`bunge = false` (URLs no longer valid) and `mapleview = false` (stub
only, JS-rendered). `seed scope=all` now creates 91 rows and reports
`skipped_disabled: ["bunge", "mapleview"]`; a pre-existing `bunge` /
`mapleview` row is excluded from the scheduled poll. Re-enabling
either adapter is a one-line config change (`= true`) — no code
change, no re-seed of the other 91 needed (re-run seed; already-seeded
rows are skipped as duplicates).

### Tests

`tests/test_source_toggle_gating.py` (6 tests): seeding skips
bunge/mapleview and records them; seeding includes a toggled-on
adapter; explicit-key seeding still skips a disabled key;
`list_due_sources` excludes a pre-existing toggled-off row; missing
toggle defaults to enabled (helper + due list, synthetic key);
toggle flipped off after seeding drops the row from the due list
(monkeypatched). The Cycle 19 due-source tests were updated to the
new expected counts (91 seeded / due, not 93).

### Still open (not fixed here)

- Poller scheduling: the deployed 08:00/15:00 cron still runs only
  the file-ingestion job; see deployment checklist §4 step 6 for the
  exact change (`python -m app.jobs.poll_sources` alongside it).
- US `us_elevators_urls.toml` toggle mismatch (Cycle 19 gap 2/3
  note): `Bunge`, `Collwest Grain`, `United Coop`, `The Andersons`,
  `Smithfield` are `enabled = false` there while the registry keys
  are enabled — still unconfirmed whether those are the same
  entities or stale duplicates.

## Cycle 20 — US AgriCharts + DTN registry adapters (code only, 0 GETs)

Closes Cycle 19 gap 2 at the adapter level: the 13 enabled
`agricharts` + 13 enabled `dtn` entries in
`us_elevators_urls.toml` (verified from the file this cycle — 13 + 13,
not trusted from the audit note) now each have a zero-argument
`fetch_<slug>()` wrapper bound to the entry's URL and name, so the
registry — which calls `fetch_fn()` with no arguments — can drive
them. No page was fetched in this cycle (0 GETs); no price, basis,
or bid was invented.

### What was added

- `us_agricharts_source.py`: `US_AGRICHARTS_SITES` map (key →
  company, URL) + 13 `fetch_<slug>()` wrappers calling
  `fetch_us_agricharts(url, name)`. Mode for the coordinator's
  `SourceAdapter` rows: `"direct"` (returns a DataFrame).
- `us_dtn_source.py`: `US_DTN_SITES` map + 13 `fetch_<slug>()`
  wrappers calling `fetch_us_dtn(url, name, None)`, plus an explicit
  guard at the top of `fetch_us_dtn`: with `playwright=None` it
  returns an empty DataFrame before touching Playwright or the
  network, because the DTN widget renders via JavaScript and there
  is nothing to parse without a render. No Playwright is launched
  from the adapter path, ever; no fake row is ever returned.
- `config.toml` `[sources]`: 26 new toggles, none pre-existing, no
  existing value touched. AgriCharts 13 are `true` (static pages);
  DTN 13 are `false` (JS-only, not collectable without a render —
  same precedent as `bunge = false` / `mapleview = false`).
- Tests: `tests/test_us_agricharts_dtn_adapters.py` — 30 tests,
  synthetic fixtures only (invented values, Testville / Test
  Elevator Co.), generic fetch mocked, no network. One test per
  adapter asserting the wrapper is zero-argument and passes the
  correct URL/name; one asserting the adapter maps match the
  enabled toml entries exactly; one asserting the real
  `fetch_us_dtn(url, name, None)` returns empty with no I/O; one
  asserting the 26 `[sources]` toggles exist with the expected
  values.
- Registry wiring is the coordinator's step (this worker may not
  edit `source_registry.py`). Exact lines to add to `ADAPTERS`:

```python
"ag_plus": SourceAdapter("ag_plus", "us_agricharts_source", "fetch_ag_plus", "direct", "scraper", 15, 90),
"farmers_win_coop": SourceAdapter("farmers_win_coop", "us_agricharts_source", "fetch_farmers_win_coop", "direct", "scraper", 15, 90),
"heartland_coop": SourceAdapter("heartland_coop", "us_agricharts_source", "fetch_heartland_coop", "direct", "scraper", 15, 90),
"heritage_grain_cooperative": SourceAdapter("heritage_grain_cooperative", "us_agricharts_source", "fetch_heritage_grain_cooperative", "direct", "scraper", 15, 90),
"keller": SourceAdapter("keller", "us_agricharts_source", "fetch_keller", "direct", "scraper", 15, 90),
"kokomo_grain": SourceAdapter("kokomo_grain", "us_agricharts_source", "fetch_kokomo_grain", "direct", "scraper", 15, 90),
"legacy_farmers": SourceAdapter("legacy_farmers", "us_agricharts_source", "fetch_legacy_farmers", "direct", "scraper", 15, 90),
"pro_ag": SourceAdapter("pro_ag", "us_agricharts_source", "fetch_pro_ag", "direct", "scraper", 15, 90),
"west_con": SourceAdapter("west_con", "us_agricharts_source", "fetch_west_con", "direct", "scraper", 15, 90),
"wheaton_dumont": SourceAdapter("wheaton_dumont", "us_agricharts_source", "fetch_wheaton_dumont", "direct", "scraper", 15, 90),
"central_farmers_coop": SourceAdapter("central_farmers_coop", "us_agricharts_source", "fetch_central_farmers_coop", "direct", "scraper", 15, 90),
"anthony_farmers_coop": SourceAdapter("anthony_farmers_coop", "us_agricharts_source", "fetch_anthony_farmers_coop", "direct", "scraper", 15, 90),
"mulvane_coop": SourceAdapter("mulvane_coop", "us_agricharts_source", "fetch_mulvane_coop", "direct", "scraper", 15, 90),
"ag_partners": SourceAdapter("ag_partners", "us_dtn_source", "fetch_ag_partners", "direct", "scraper", 15, 90),
"al_corn": SourceAdapter("al_corn", "us_dtn_source", "fetch_al_corn", "direct", "scraper", 15, 90),
"allied_cooperative": SourceAdapter("allied_cooperative", "us_dtn_source", "fetch_allied_cooperative", "direct", "scraper", 15, 90),
"aurora_coop": SourceAdapter("aurora_coop", "us_dtn_source", "fetch_aurora_coop", "direct", "scraper", 15, 90),
"cfs": SourceAdapter("cfs", "us_dtn_source", "fetch_cfs", "direct", "scraper", 15, 90),
"elite_octane": SourceAdapter("elite_octane", "us_dtn_source", "fetch_elite_octane", "direct", "scraper", 15, 90),
"frontier_coop": SourceAdapter("frontier_coop", "us_dtn_source", "fetch_frontier_coop", "direct", "scraper", 15, 90),
"green_plains": SourceAdapter("green_plains", "us_dtn_source", "fetch_green_plains", "direct", "scraper", 15, 90),
"kanza_coop": SourceAdapter("kanza_coop", "us_dtn_source", "fetch_kanza_coop", "direct", "scraper", 15, 90),
"sunrise": SourceAdapter("sunrise", "us_dtn_source", "fetch_sunrise", "direct", "scraper", 15, 90),
"brubaker_grain": SourceAdapter("brubaker_grain", "us_dtn_source", "fetch_brubaker_grain", "direct", "scraper", 15, 90),
"hoffman_ag": SourceAdapter("hoffman_ag", "us_dtn_source", "fetch_hoffman_ag", "direct", "scraper", 15, 90),
"wilton_farmers_union_elevator": SourceAdapter("wilton_farmers_union_elevator", "us_dtn_source", "fetch_wilton_farmers_union_elevator", "direct", "scraper", 15, 90),
```

### Per-entry table — AgriCharts (13 entries; 11 toggled on, 2 toggled off in Cycle 23 — all static-capable)

| Entry | URL | Status | Adapter key | Toggle |
| --- | --- | --- | --- | --- |
| Ag Plus | https://www.agplusinc.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: verified live through wrapper `fetch_ag_plus` — 36 rows (Corn 12, Beans 12, Wheat 12), 6 locations** | `ag_plus` | true |
| Farmers Win Coop | https://www.farmerswin.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: verified live through wrapper `fetch_farmers_win_coop` — 171 rows (Corn 90, Soybeans 81), 18 locations** | `farmers_win_coop` | true |
| Heartland Coop | https://www.heartlandcoop.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: wrapper `fetch_heartland_coop` returned 0 rows — page fetched (2xx) but no `jsquote.php` script tag in HTML; site-side change, wrapper URL/name correct, no fix made. Re-probe in a later cycle. **Cycle 22 (2026-11-19): re-probed through the wrapper — still 0 rows, `jsquote.php` tag still missing; wrapper unchanged** **Cycle 23 (2026-11-19): toggle flipped to `false` in `config.toml` `[sources]` — two consecutive 0-row probes (Cycles 21, 22), `jsquote.php` tag missing. Reversible; `us_elevators_urls.toml` entry stays enabled, the toggle is the gate.** | `heartland_coop` | false |
| Heritage Grain Cooperative | https://www.heritagegrain.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery; distinct from `heritage_coop` (Heritage Cooperative, agricharts-embed). **Cycle 21: wrapper `fetch_heritage_grain_cooperative` returned 3 rows only (CORN/BEANS/WHEAT - CASH, 1 each); page `<h4>` tags are commodity headings, so `Location` labels are commodity names — site-structure quirk, not a wrapper bug. **Cycle 22 (2026-11-19): the page lists 14 bids, not 3 — 11 forward-month rows were skipped because their notes argument holds an escaped quote (`'DEC \'26'`), and all 14 `<h4>` tags are commodity headings. Generic parser fixed in `us_agricharts_source.py` (escaped-quote support in group/notes + commodity-heading location fallback); verified against the saved Cycle 22 capture to 14 correctly-labelled rows; see "Cycle 22 — Heartland/Mulvane re-probes + Heritage parser fix"** | `heritage_grain_cooperative` | true **Cycle 23 (2026-11-19): confirmed LIVE through the wrapper — 14 rows (CORN 6, BEANS 6, WHEAT 2), all with the company fallback location `Heritage Grain Cooperative - Heritage Grain Cooperative`; the Cycle 22 parser fix is confirmed live.** |
| Keller | https://www.kellergrain.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: verified live through wrapper `fetch_keller` — 14 rows (Corn 7, Soybeans 7), 1 location** | `keller` | true |
| Kokomo Grain | https://www.kokomograin.com/markets/cash.php?location_filter= | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: verified live through wrapper `fetch_kokomo_grain` — 63 rows (Corn 29, Soybeans 24, Wheat 5, NGMO Waxy 5), 8 locations** | `kokomo_grain` | true |
| Legacy Farmers | https://www.legacyfarmers.com/markets/cash.php | static-capable — writeBidRow confirmed, Cycle 1 discovery. **Cycle 21: verified live through wrapper `fetch_legacy_farmers` — 66 rows (Beans 25, Corn 24, Wheat 17), 10 locations** | `legacy_farmers` | true |
| Pro Ag | https://www.proagfarmers.com/markets/cash.php | static-capable — verified live Cycle 11: 78 static writeBidRow rows (Corn / Soybeans / Wheat, 6 h4 locations). **Cycle 21 batch B (2026-11-19): verified THROUGH the wrapper** `fetch_pro_ag()` — 78 rows, identical count and locations to Cycle 11 (Soybeans 35, Corn 31, Wheat 12; Brandon, CLARISSA, EAGLE BEND / EAGLE BEND WEST, GARFIELD, Hoffman, PARKERS PRAIRIE). No wrapper bug. | `pro_ag` | true |
| West-Con | https://www.west-con.com/markets/cash.php | static-capable — verified live Cycles 11–12: 84 static writeBidRow rows; month-name delivery labels ('Dec 2026'), kept verbatim. **Cycle 21 batch B (2026-11-19): verified THROUGH the wrapper** `fetch_west_con()` — 84 rows (Soybeans 44, Corn 30, DNS Wheat (Milling Quality) 10; deliveries 'Dec 2026'–'Jul 2027' month labels). Note: all rows carry the single fallback location `West-Con - West-Con` — the page has no `<h4>` location headings before its rows, so the parser's company-name fallback applies (generic-parser behaviour, not a wrapper bug). | `west_con` | true |
| Wheaton Dumont | https://www.wdcoop.com/markets/cash.php | static-capable — verified live Cycle 12: 43 static writeBidRow rows; short month labels ('Nov 26', 'Jan 27'), kept verbatim. **Cycle 21 batch B (2026-11-19): verified THROUGH the wrapper** `fetch_wheaton_dumont()` — 43 rows, identical count to Cycle 12 (Corn 18, Soybeans 16, Spring Wheat 9; 8 locations; deliveries 'Nov 26'–'Oct 27'). No wrapper bug. | `wheaton_dumont` | true |
| Central Farmers Coop | https://www.cenfarmcoop.com/markets/cash.php | static-capable — writeBidRow confirmed in fetched HTML, Cycle 1 ("enable immediately"). **Cycle 21 batch B (2026-11-19): verified THROUGH the wrapper** `fetch_central_farmers_coop()` — 75 rows (Corn 44, Soybeans 30, Winter Wheat 1; 11 locations: Canova, Dimock, Freeman, Lyons, Marion, Montrose, Mt Vernon, Salem, Springfield, Tyndall, Viborg). No wrapper bug. | `central_farmers_coop` | true |
| Anthony Farmers Co-op | https://www.anthonycoop.com/markets/cash.php | static-capable — writeBidRow confirmed in fetched HTML, Cycle 1 ("enable immediately"). **Cycle 21 batch B (2026-11-19): verified THROUGH the wrapper** `fetch_anthony_farmers_coop()` — 9 rows (Corn 3, Milo 3, Soybeans 3; 3 locations: ANTHONY, HARPER, SHARON; single delivery 09/01/2026). Thin page but structurally sound — 3 locations × 3 commodities, one delivery month each. No wrapper bug. | `anthony_farmers_coop` | true |
| Mulvane Coop | https://www.mulvanecoop.com/markets/cash.php | static-capable — writeBidRow confirmed in fetched HTML, Cycle 1 ("enable immediately"). **Cycle 21 batch B (2026-11-19): FAILED through the wrapper** `fetch_mulvane_coop()` — HTTP 200 but **0 rows**: `[US-AG WARN] Mulvane Coop: jsquote script tag not found in page`. The page no longer carries the `jsquote.php` script tag the generic parser requires, so `fetch_us_agricharts` returns empty before parsing any rows. **Not a wrapper bug** — the wrapper passes the exact toml URL/name (`https://www.mulvanecoop.com/markets/cash.php`, "Mulvane Coop"); the failure is site-side (page template changed since Cycle 1, or the cash page is now JS-rendered / served differently). Wrapper left unchanged; toggle flipped to `false` in Cycle 23 (see below). **Follow-up (later cycle, 1 GET):** re-probe the cash page and inspect what it serves now — if the jsquote tag is gone for good, the entry needs either a new static route or a toggle flip to `false`. **Cycle 23: resolved — toggle flipped to `false`; re-probe only if the site is believed to have restored the tag.** **Cycle 22 (2026-11-19): re-probed through the wrapper — still 0 rows, `jsquote.php` tag still missing; wrapper unchanged.** **Cycle 23 (2026-11-19): toggle flipped to `false` in `config.toml` `[sources]` — two consecutive 0-row probes (Cycles 21, 22), `jsquote.php` tag missing. Reversible; `us_elevators_urls.toml` entry stays enabled, the toggle is the gate.** | `mulvane_coop` | false |

### Per-entry table — enabled DTN (13, all JS-only)

| Entry | URL | Status | Adapter key | Toggle |
| --- | --- | --- | --- | --- |
| Ag Partners | https://agpartners.net/cash-bids | JS-only — modern DTN widget (content-services), no static bid rows (Cycles 6/8; was 503 "Site is offline" in Cycle 6, back up 200 in Cycle 8) | `ag_partners` | false |
| Al-Corn | https://www.al-corn.com/cash-bids | JS-only — classic DTN, exact fit for `us_dtn_source.py`: `<div id="target">` + `CashBidTable`, companyID 239483 (Cycle 6) | `al_corn` | false |
| Allied Cooperative | https://www.allied.coop/grain/cash-bids | JS-only — modern DTN widget (content-services), no static bid rows (Cycle 6) | `allied_cooperative` | false |
| Aurora Coop | https://auroracoop.com/markets | JS-only — modern DTN widget (content-services), no static bid rows (Cycle 6) | `aurora_coop` | false |
| CFS | https://www.cfscoop.com/products-services/grain | JS-only — aghost DTN widget (`DtnCashbidDetailsScript.js`) + location-cookie flow; only static table is a futures quotes table (Cycle 6) | `cfs` | false |
| Elite Octane | https://www.eliteoctane.net/cash-bids | JS-only — `<div id="target">` + CIHedging `CashBidWidget.js` loader, no inline `tableOptions` (Cycle 6) | `elite_octane` | false |
| Frontier Coop | https://www.frontiercooperative.com/grain/cash-bids | JS-only — **not DTN at all**: StoneX widget (`StonexCashbidScript.js`), inline JSON model empty in static HTML (Cycles 6/8/9). The DTN adapter returns empty for it; a StoneX collector is a separate later-cycle item | `frontier_coop` | false |
| Green Plains | https://gpreinc.com/corn-bids/ | JS-only — modern DTN widget (content-services), no static bid rows (Cycle 6) | `green_plains` | false |
| Kanza Coop | https://www.kanzacoop.com/services/grain | JS-only — ATLAS DTN shell (`/dtncashbidwidget/bindlocation`), no static bid rows (Cycle 6) | `kanza_coop` | false |
| Sunrise | https://www.sunriseco-op.com | JS-only — classic DTN, exact fit for `us_dtn_source.py`: `<div id="target">` + `CashBidTable`, companyID 23043, CIHedging `CashBidWidget.js`, ATLAS DTN shell (Cycle 10) | `sunrise` | false |
| Brubaker Grain | https://dtn.brubakergrain.com/ | JS-only — DTN-subdomain host; widget ref confirmed in HTML, live bid rows visible only in search index (Cycle 1); rows still to confirm in Playwright | `brubaker_grain` | false |
| Hoffman Ag | https://dtn.hoffmanag.com/ | JS-only — DTN-subdomain host; same as Brubaker (Cycle 1); rows still to confirm in Playwright | `hoffman_ag` | false |
| Wilton Farmers Union Elevator | https://www.wiltonfarmerselevator.com/index.cfm?show=11&mid=5&theLocation=1&cmid=all&layout=19 | JS-only — DTN index.cfm page; widget ref confirmed, rows visible only in search index (Cycle 1); rows still to confirm in Playwright | `wilton_farmers_union_elevator` | false |

No entry in either table is "unknown": every agricharts entry has
writeBidRow confirmed in fetched HTML or verified live, and every
DTN entry has its widget family identified in the Cycle 6 sweep
(or Cycles 1/10 for the subdomain/classic entries) with no static
bid rows. What is unknown is only whether each DTN page renders
collectable rows in Playwright — that is probe work, not a
classification gap.

### Follow-up — live verification is a later cycle's GET-probe work

1. **AgriCharts adapters (13):** one polite GET each of the
   `/markets/cash.php` pages through the new zero-arg wrappers;
   confirm each returns rows via `fetch_us_agricharts` (the three
   Cycle 11–12 entries — Pro Ag, West-Con, Wheaton Dumont — were
   verified live against the generic, but not through these
   wrappers; the other ten were confirmed from fetched HTML in
   Cycle 1, not through a wrapper call). **Cycle 21 (2026-11-19):
   batch B verified 6 of the 13 through their wrappers** — Pro Ag
   (78 rows), West-Con (84), Wheaton Dumont (43), Central Farmers
   Coop (75), Anthony Farmers Co-op (9) all return rows; **Mulvane
   Coop returns 0 rows** (HTTP 200, no `jsquote.php` script tag on
   the page — site-side, not a wrapper bug; re-probe in a later
   cycle). A sibling batch A is verifying the remaining 7 wrappers
   (ag_plus, farmers_win_coop, heartland_coop,
   heritage_grain_cooperative, keller, kokomo_grain, legacy_farmers)
   in parallel; see "Cycle 21 agricharts wrapper verification —
   batch B" below. **Cycle 21 (2026-11-19):
   7 of 13 done** — Ag Plus (36 rows), Farmers Win Coop (171),
   Keller (14), Kokomo Grain (63), Legacy Farmers (66) all verified
   live through their wrappers; Heartland Coop returned 0 rows
   (page fetched but no `jsquote.php` script tag — site-side change,
   re-probe later); Heritage Grain Cooperative returned 3 rows with
   `Location` labels mis-set to commodity names (page `<h4>` tags
   are commodity headings — site-structure quirk). **All 13 now
   verified through wrappers:** batch B covered the other 6 (Pro Ag
   78, West-Con 84, Wheaton Dumont 43, Central Farmers Coop 75,
   Anthony Farmers Co-op 9 — all returning rows; Mulvane Coop 0
   rows, same missing-`jsquote.php`-tag failure as Heartland).
   Net: 11 of 13 return rows; 2 (Heartland, Mulvane) fail site-side
   on the missing jsquote tag.
2. **DTN adapters (13):** Playwright render check, one per page —
   confirm the widget renders rows and that `_parse_cash_table`
   parses them. Until then every DTN adapter honestly returns
   empty, its toggle stays `false`, and it must not be seeded as
   collectable. Al-Corn and Sunrise (classic `CashBidTable`) are
   the best first candidates — the generic was written for exactly
   that shape.
3. **Frontier Coop / StoneX:** not a DTN render check — needs the
   StoneX investigation already open from Cycles 6/8/9 (same family
   as CRC / UFC). Do not flip its toggle on the DTN adapter.
4. **Coordinator step:** add the 26 `SourceAdapter` lines above to
   `app/services/source_registry.py`; seeding `scope=all` will then
   include the 13 agricharts adapters (toggles on) while the 13 DTN
   adapters remain toggle-off until item 2 proves them. Note Cycle
   19 gap 3 still applies: the FastAPI orchestrator does not read
   `[sources]` toggles, so the toggle-off state alone does not gate
   seeding — the coordinator should confirm the intended gate
   before seeding the DTN keys.

## Cycle 21 — live verification of AgriCharts wrappers 1–7 (2026-11-19)

Closes the first half of Cycle 20 follow-up item 1: 7 of the 13
zero-arg AgriCharts wrappers were called live, one wrapper call
each (7 page GETs, ~2 s spacing, no retries), run from the API venv
as `fetch_<slug>()` with no arguments. No live price, basis, or bid
was saved to the repo — counts and structure only. No wrapper bug
was found, so no wrapper code was changed and no new tests were
added; the full test suite was not re-run (no code changed).

### Per-wrapper results

| Wrapper | URL | Rows | Commodities (rows) | Locations | Status |
| --- | --- | --- | --- | --- | --- |
| `fetch_ag_plus` | https://www.agplusinc.com/markets/cash.php | 36 | Corn 12, Beans 12, Wheat 12 | 6 (Churubusco, Edgerton, Garrett, Monroeville, Raber, South Whitley) | OK — verified live through wrapper |
| `fetch_farmers_win_coop` | https://www.farmerswin.com/markets/cash.php | 171 | Corn 90, Soybeans 81 | 18 | OK — verified live through wrapper |
| `fetch_heartland_coop` | https://www.heartlandcoop.com/markets/cash.php | 0 | — | — | FAIL (site-side) — page fetched (2xx, no HTTP error) but no `jsquote.php` script tag in the HTML, so `fetch_us_agricharts` returned empty before parsing. Wrapper URL/name verified correct against `us_elevators_urls.toml` + Cycle 1 discovery; no wrapper change |
| `fetch_heritage_grain_cooperative` | https://www.heritagegrain.com/markets/cash.php | 3 | CORN - CASH 1, BEANS - CASH 1, WHEAT - CASH 1 | 3, but mislabelled — `Location` values are the commodity names | PARTIAL (site-structure quirk) — page `<h4>` tags hold commodity headings, not location names, so the generic parser's h4-as-location assumption mislabels them. Wrapper URL/name correct; no wrapper change |
| `fetch_keller` | https://www.kellergrain.com/markets/cash.php | 14 | Corn 7, Soybeans 7 | 1 (Keller) | OK — verified live through wrapper |
| `fetch_kokomo_grain` | https://www.kokomograin.com/markets/cash.php?location_filter= | 63 | Corn 29, Soybeans 24, Wheat 5, NGMO Waxy 5 | 8 (Adm Fkt, Amboy, Anderson, Edinburgh, Emporia, Kokomo, T-L Laf, Winamac) | OK — verified live through wrapper |
| `fetch_legacy_farmers` | https://www.legacyfarmers.com/markets/cash.php | 66 | Beans 25, Corn 24, Wheat 17 | 10 (Apex Grain Marketing, Custar, Deshler, East Findlay, Fostoria, McComb, Mt Blanchard, Mt Cory, North Findlay, West Findlay) | OK — verified live through wrapper |

All 7 returned DataFrames have the standard 10 columns
(`Location`, `Name`, `Delivery`, `Delivery End`, `Futures Month`,
`Futures Price`, `Change`, `Basis`, `Bushel Cash Price`,
`MT Cash Price`).

### Observations / follow-ups

1. **Heartland Coop — re-probe in a later cycle (1 GET).** The
   page served a 2xx response but without the `jsquote.php` script
   tag the generic collector depends on. Possibilities: the site
   restructured its cash page, dropped the AgriCharts embed, or
   served a different template to this request. Do not flip its
   `[sources]` toggle off on one observation; a single re-probe
   decides whether it is a transient template change or a real
   break. If the tag is gone for good, the fix belongs in the
   generic collector (alternate futures source), not the wrapper.
   **Cycle 22 (2026-11-19): re-probed — still 0 rows, tag still
   missing. Second consecutive failure; not transient. No toggle
   change made here; see Cycle 22 section.**
2. **Heritage Grain Cooperative — parser follow-up, not a wrapper
   bug.** Only 3 rows parsed and their `Location` values are
   commodity names. Open questions for a later cycle: does the page
   genuinely list only 3 cash bids (one per commodity, single
   delivery point), or are more rows present in a shape the
   `writeBidRow` regex skips (e.g. a different delivery format)?
   Separately, the generic parser assumes `<h4>` = location name;
   on this page `<h4>` = commodity heading. A later cycle could
   teach the parser to detect h4-as-commodity pages (or to fall
   back to the company name as the location when the h4 text
   matches a commodity name). No change made here — out of scope
   for a wrapper-verification task. **Cycle 22 (2026-11-19):
   resolved — see "Cycle 22 — Heartland/Mulvane re-probes +
   Heritage parser fix": the page lists 14 bids, 11 skipped by an
   escaped quote in the notes argument; parser fixed and verified
   to 14 correctly-labelled rows.**
3. **User-Agent note for the coordinator:** the task brief said the
   fetch functions send `GrainHub-Research/1.0`, but
   `us_agricharts_source.py` `_HEADERS` actually sends a Chrome
   `Mozilla/5.0` UA. The wrappers were run as-is (no override, per
   the brief); if the intended UA is `GrainHub-Research/1.0`, that
   is a deliberate change for a later cycle, not something this
   worker silently altered.
4. **Remaining wrapper verifications (6) — done by sibling batch B
   in parallel:** Pro Ag (78 rows), West-Con (84), Wheaton Dumont
   (43), Central Farmers Coop (75), Anthony Farmers Co-op (9) all
   verified through their wrappers; Mulvane Coop returned 0 rows
   with the same missing-`jsquote.php`-tag failure as Heartland
   Coop. All 13 wrappers are now verified through live calls.

## Cycle 21 agricharts wrapper verification — batch B

Closes the second half of Cycle 20 follow-up item 1: the remaining
6 of the 13 zero-arg AgriCharts wrappers were called live, one
wrapper call each (6 page GETs, ~2 s spacing, no retries), run from
the API venv as `fetch_<slug>()` with no arguments. This completes
the 6 left open by the sibling batch A (its item 4); combined,
Cycle 21 has now verified all 13 AgriCharts wrappers live. No live
price, basis, or bid was saved to the repo — counts and structure
only. No wrapper bug was found, so no wrapper code was changed and
no new tests were added; the full test suite was not re-run (no code
changed).

### Per-wrapper results

| Wrapper | URL | Rows | Commodities (rows) | Locations | Status |
| --- | --- | --- | --- | --- | --- |
| `fetch_mulvane_coop` | https://www.mulvanecoop.com/markets/cash.php | 0 | — | — | FAIL (site-side) — HTTP 200, but no `jsquote.php` script tag in the page, so `fetch_us_agricharts` returned empty before parsing (`[US-AG WARN] Mulvane Coop: jsquote script tag not found in page`). Wrapper URL/name verified correct against `us_elevators_urls.toml` (line 679) + Cycle 1 discovery; no wrapper change |
| `fetch_pro_ag` | https://www.proagfarmers.com/markets/cash.php | 78 | Soybeans 35, Corn 31, Wheat 12 | 6 (Brandon, CLARISSA, EAGLE BEND / EAGLE BEND WEST, GARFIELD, Hoffman, PARKERS PRAIRIE) | OK — verified live through wrapper; count and locations identical to Cycle 11 |
| `fetch_west_con` | https://www.west-con.com/markets/cash.php | 84 | Soybeans 44, Corn 30, DNS Wheat (Milling Quality) 10 | 1 (fallback `West-Con - West-Con` — see note) | OK — verified live through wrapper; count identical to Cycles 11–12, month-name deliveries ('Dec 2026'–'Jul 2027') kept verbatim |
| `fetch_wheaton_dumont` | https://www.wdcoop.com/markets/cash.php | 43 | Corn 18, Soybeans 16, Spring Wheat 9 | 8 (AGP DLVD ABERDEEN, SD; AGP DLVD DAWSON, MN; Britton, SD; Browns Valley/Sisseton, SD; Graceville/Tenney; Rutland, ND; Wheaton/Dumont/Browns Valley/LaMars/Hankinson/Mantador/Sisseton; Wheaton/Dumont/Tenney/LaMars/Hankinson/Mantador) | OK — verified live through wrapper; count identical to Cycle 12, short month labels ('Nov 26'–'Oct 27') kept verbatim |
| `fetch_central_farmers_coop` | https://www.cenfarmcoop.com/markets/cash.php | 75 | Corn 44, Soybeans 30, Winter Wheat 1 | 11 (Canova, Dimock, Freeman, Lyons, Marion, Montrose, Mt Vernon, Salem, Springfield, Tyndall, Viborg) | OK — verified live through wrapper (first live verification; previously Cycle 1 HTML only) |
| `fetch_anthony_farmers_coop` | https://www.anthonycoop.com/markets/cash.php | 9 | Corn 3, Milo 3, Soybeans 3 | 3 (ANTHONY, HARPER, SHARON) | OK — verified live through wrapper (first live verification; previously Cycle 1 HTML only). Thin page but structurally sound: 3 locations × 3 commodities, single delivery 09/01/2026 |

All 5 non-empty DataFrames have the standard 10 columns
(`Location`, `Name`, `Delivery`, `Delivery End`, `Futures Month`,
`Futures Price`, `Change`, `Basis`, `Bushel Cash Price`,
`MT Cash Price`).

### Observations / follow-ups

1. **Mulvane Coop — re-probe in a later cycle (1 GET).** Same
   failure mode as Heartland Coop in batch A (2xx, no `jsquote.php`
   script tag): the page no longer carries the tag the generic
   collector requires, so the adapter yields nothing even though
   its toggle is `true` and the wrapper is correct. Possibilities:
   the site restructured its cash page, dropped the AgriCharts
   embed, or served a different template to this request. Do not
   flip its `[sources]` toggle off on one observation; a single
   re-probe decides whether it is transient or a real break. If
   the tag is gone for good, the fix belongs in the generic
   collector (alternate futures source), not the wrapper — and the
   same fix would cover Heartland Coop. **Cycle 22 (2026-11-19):
   re-probed — still 0 rows, tag still missing. Second consecutive
   failure; not transient. No toggle change made here; see Cycle 22
   section.**
2. **West-Con location fallback.** All 84 rows carry the single
   location `West-Con - West-Con`: the page has no `<h4>` location
   headings before its rows, so the parser's company-name fallback
   applies. This matches Cycle 11–12 (location param `All`) and is
   generic-parser behaviour, not a wrapper bug — no change made.
3. **Cycle 21 totals (both batches):** 11 of 13 AgriCharts
   wrappers verified live returning rows (289 rows this batch +
   batch A's 353 = 642 rows across the cycle); 2 return 0 rows for
   the same site-side reason (Heartland Coop, Mulvane Coop —
   missing `jsquote.php` tag). No wrapper bug was found in either
   batch. Cycle 20 follow-up item 1 is now closed for the
   AgriCharts half; the DTN half (item 2) is untouched.
4. **User-Agent note (agrees with batch A):** the task brief said
   the fetch functions send `GrainHub-Research/1.0`, but
   `us_agricharts_source.py` `_HEADERS` actually sends a Chrome
   `Mozilla/5.0` UA. The wrappers were run as-is (no override, per
   the brief); if the intended UA is `GrainHub-Research/1.0`, that
   is a deliberate change for a later cycle.

## Cycle 22 — staleness re-checks: Chadbourn, Hamer, Hugoton, Vilas - Walsh (2026-11-19)

Re-checked the four locations on the staleness watch, one polite
GET each (4 GETs total, User-Agent `GrainHub-Research/1.0`, ~2 s
spacing, no retries), in the early hours of Nov 19, 2026 (EST).
Raw HTML saved to `/tmp/cycle22/` scratch only, never the repo.
No prices are recorded here — counts and structure only.
Research only: no code changes, no tests, full suite not run.

**URL note:** the task brief listed the Smithfield URLs with a
`www.` prefix, but the registry (`BUSHEL_SITES` in
`bushel_source.py`) records them without it
(`https://smithfieldgrain.com/cashbidssingle-2294` and
`...-2179`). The registry URLs were used, per the brief's own
"exact URLs from the registry" instruction. Both Skyland URLs
match the registry exactly.

### Per-location results

| Location | URL probed | HTTP | Widget header date | Rows (vs earlier) | Verdict |
| --- | --- | --- | --- | --- | --- |
| Smithfield Grain — Chadbourn (2294) | https://smithfieldgrain.com/cashbidssingle-2294 | 200 | Wednesday, November 18, 2026 | 1 (Soybeans 1) — unchanged | **Still stale by one day** |
| Smithfield Grain — Hamer (2179) | https://smithfieldgrain.com/cashbidssingle-2179 | 200 | Wednesday, November 18, 2026 | 1 (Soybeans 1) — unchanged | **Still stale by one day** |
| Skyland Grain — Hugoton (3370) | https://www.skylandgrain.com/cashbidssingle-3370 | 200 | Wednesday, November 18, 2026 | 6 (Corn 2, Milo 2, Red Wheat 2) — unchanged | **Still stale by one day** |
| Skyland Grain — Vilas - Walsh (3621) | https://www.skylandgrain.com/cashbidssingle-3621 | 200 | Wednesday, November 18, 2026 | 5 (Corn 2, Milo 1, Red Wheat 2) — unchanged | **Still stale by one day** |

All four parsed cleanly with the existing generic parser
(`parse_bushel_html` run against each saved `/tmp/cycle22/`
HTML with its registry site — status ok, mapped locations
"Chadbourn", "Hamer", "Hugoton", "Vilas - Walsh"). No parser
change needed; the staleness is in the widgets' data, not the
parse.

### Verdict — staleness watch UNCHANGED (not resolved, not reduced)

None of the four caught up: every widget header is still dated
Wednesday, November 18, 2026, against a Nov 19 probe date, and
every row count is identical to its earlier probe. Chadbourn is
now stale on its third consecutive probe (Cycles 13, 14, 22);
Hugoton and Vilas - Walsh on their second (Cycles 14, 22);
Hamer on its second (Cycles 16, 22). The lag is a persistent
one-day lag at all four locations, not a transient refresh
delay — but it is still exactly one day, no worse. The watch
stays in place for all four, and the standing collector note
stands: a same-day freshness gate would fail these four
locations daily, so they need an exemption / lag tolerance if
such a gate is ever added. No new follow-up probe is opened
beyond the existing watch (re-check again in a later cycle;
a daytime re-check would also test whether the widgets refresh
later in the day rather than overnight).

## Cycle 22 — Heartland/Mulvane re-probes + Heritage parser fix (2026-11-19)

Closes all three Cycle 21 follow-ups for the AgriCharts wrappers:
the Heartland Coop re-probe (batch A item 1), the Mulvane Coop
re-probe (batch B item 1), and the Heritage Grain Cooperative
parser investigation (batch A item 2). 3 page GETs total, ~2 s
spacing, no retries: `fetch_heartland_coop()` and
`fetch_mulvane_coop()` live through the API venv (wrappers as-is,
Chrome UA), plus one direct fetch of the Heritage cash page with
`GrainHub-Research/1.0` (URL from `us_elevators_urls.toml`,
`https://www.heritagegrain.com/markets/cash.php`), raw HTML saved
to `/tmp/cycle22/heritage_cash.html` (64,855 bytes, HTTP 200).
No live price, basis, or bid was saved to the repo — counts and
structure only.

### Per-target results

| Target | Call | Rows | Finding | Status |
| --- | --- | --- | --- | --- |
| Heartland Coop | `fetch_heartland_coop()` | 0 | `[US-AG WARN] Heartland Coop: jsquote script tag not found in page` — same failure as Cycle 21 | STILL FAILING (site-side) — second consecutive failure, not transient |
| Mulvane Coop | `fetch_mulvane_coop()` | 0 | `[US-AG WARN] Mulvane Coop: jsquote script tag not found in page` — same failure as Cycle 21 batch B | STILL FAILING (site-side) — second consecutive failure, not transient |
| Heritage Grain Cooperative | direct page fetch | 14 data calls in HTML (was 3 parsed in Cycle 21) | 11 forward-month rows skipped by the regex (escaped quote in notes); all 14 `<h4>` tags are commodity headings | FIXED in the generic parser — see below |

### Heartland / Mulvane — still failing, wrappers unchanged

Both pages still serve HTTP 200 without the `jsquote.php` script
tag, so `fetch_us_agricharts` still returns empty before parsing.
Two consecutive failures (Cycles 21 and 22) rule out a transient
template change: the tag is gone for good on both sites, or both
cash pages are now served in a form the collector cannot use.
No wrapper change was made (both wrappers pass the exact toml
URL/name); no toggle change was made here. Next step for a later
cycle: either a generic-collector alternate futures source (the
fix Cycle 21 anticipated — it would cover both sites at once) or
flipping both toggles to `false` so the adapters stop yielding
nothing. The toggles stay `true` for now.

### Heritage — the page lists 14 bids, not 3 (two parser bugs found)

Reading the saved HTML verbatim:

1. **14 `writeBidRow` data calls, not 3.** One per commodity
   heading: CORN/BEANS/WHEAT - CASH (1 each, the 3 Cycle 21
   parsed) plus CORN/BEANS - DEC 2026, JAN 2027, FEB 2027,
   MAR 2027, FALL 2027 and WHEAT - JUL 2027 (11 more). All
   deliveries are full MM/DD/YYYY windows. No other bid shape is
   present — no second table, no `data-bid` attributes, no other
   bid-row pattern; the 11 missing rows are ordinary
   `writeBidRow` calls the regex failed to match.
2. **Why the regex skipped them:** the forward-month rows carry
   the delivery label in the notes argument (arg 10) with an
   escaped quote — `'DEC \'26'`, `'JAN \'27'`, `'FALL \'27'`,
   `'JUL \'27'` — and the regex's group/notes fields were
   `'[^']*'`, which stops at the escaped quote, so the whole row
   failed to match. The 3 cash rows have plain notes (`'CASH'`)
   and matched. The `jsquote.php` tag is present and lists all 8
   symbols the 14 rows reference
   (`ZCZ26,ZSF27,ZWZ26,ZCH27,ZSH27,ZCZ27,ZSX27,ZWN27`), so
   futures lookup covers every row.
3. **The `<h4>` tags are commodity headings.** All 14 `<h4>`
   texts are commodity headings (`CORN - CASH`,
   `CORN - DEC 2026`, …), each exactly equal to the row name
   beneath it, in document order (each `<h4>` precedes its row).
   The generic parser's h4-as-location assumption therefore
   mislabels every row's `Location` with a commodity name.

### Parser fix (generic collector, not the wrapper)

In `app/platform/market_data/sources/us_agricharts_source.py`:

- **Escaped quotes:** the group (arg 9) and notes (arg 10)
  fields in `_WRITEBIDROW_RX` changed from `'[^']*'` to
  `'(?:[^'\\]|\\.)*'`, so an escaped quote inside either field
  no longer breaks the match. Verified offline against the saved
  capture: 14/14 rows match (was 3/14).
- **Commodity headings:** new `_is_commodity_heading(h4_text,
  row_name)` — true when the `<h4>` text exactly equals the
  row's commodity name (case-insensitive), or starts with a
  commodity word (`corn|soybeans?|beans|wheat|milo|sorghum|
  barley|oats|canola|rye|sunflowers?|flax|peas|lentils?|
  chickpeas|durum`). Rows under such a heading fall back to the
  company name as the location — the same `Company - Company`
  fallback shape West-Con already produces (no `<h4>` headings
  there). The word-boundary check keeps real place names out
  (`Wheatland`, `Cornwall` do not match); genuine location
  `<h4>`s are unaffected. Verified end-to-end with mocked
  futures against the saved capture: 14 rows, names as listed
  above, single location
  `Heritage Grain Cooperative - Heritage Grain Cooperative`.

No live re-call of the Heritage wrapper was made after the fix
(the 3-GET budget for this task was spent); the fix is verified
against the saved capture plus synthetic fixtures, and the next
live wrapper call should return 14 rows.

### Tests

4 new tests in
`GrainBids/grainbids/apps/api/tests/test_us_agricharts_source.py`
(+ synthetic fixture
`tests/fixtures/us_agricharts_heritage_sample.html`, all values
invented, neutral `Test Elevator` naming):

- `test_escaped_quote_notes_parse` — fixture rows with escaped
  quotes in notes and group all match the regex (4/4).
- `test_is_commodity_heading` — exact-match and commodity-word
  cases true; `Riverside`, `Wheatland`, `Cornwall`, `Garfield`
  false.
- `test_commodity_h4_falls_back_to_company` — mocked-HTTP
  end-to-end: commodity-heading rows get the company fallback
  location, the genuine `Riverside` heading is still used.
- `test_heritage_saved_html_row_count` — structure only, skips
  when `/tmp/cycle22/heritage_cash.html` is absent: 14 data
  calls, 14 regex matches, 14 `<h4>`s equal to the row names,
  jsquote symbols cover all row symbols, 7 distinct delivery
  starts.

Full API suite: **696 passed, 0 failed** (692 baseline + 4 new).

### Follow-ups

1. **Heartland Coop / Mulvane Coop — decide in a later cycle:**
   alternate futures source in the generic collector, or flip
   both toggles to `false`. Two consecutive 0-row probes each;
   do not keep re-probing them every cycle without a fix plan. **Cycle 23 (2026-11-19): decided — both toggles flipped to `false` in `config.toml` `[sources]` (see "Cycle 23 — Heritage live confirmation + Heartland/Mulvane toggle-off").**
2. **Heritage Grain Cooperative — confirm live (1 GET):** call
   `fetch_heritage_grain_cooperative()` once in a later cycle;
   expect 14 rows with the company fallback location. **Cycle 23 (2026-11-19): confirmed live — 14 rows, company fallback location (see Cycle 23 section).**

## Cycle 23 — Heritage live confirmation + Heartland/Mulvane toggle-off (2026-11-19)

### Heritage Grain Cooperative — parser fix confirmed live (1 GET)

One live wrapper call, `fetch_heritage_grain_cooperative()`, run from
the API venv (the wrapper's existing Chrome User-Agent, unchanged).
Result: **14 rows**, exactly as the Cycle 22 parser fix predicted —
so the fix is confirmed live, and the Cycle 22 follow-up is closed.

- Commodities: CORN 6, BEANS 6, WHEAT 2 (from the `Name` field:
  `CORN - CASH`, `BEANS - CASH`, `WHEAT - CASH` plus the DEC 2026 /
  JAN / FEB / MAR / FALL 2027 forward rows and `WHEAT - JUL 2027`).
- Location: all 14 rows carry the company fallback location
  `Heritage Grain Cooperative - Heritage Grain Cooperative` — the
  page's `<h4>` tags are commodity headings, so the Cycle 22
  commodity-heading fallback applies, as designed.
- Deliveries: Oct 2026–Nov 2027 (cash plus forward months).
- Standard 10 columns (`Location`, `Name`, `Delivery`,
  `Delivery End`, `Futures Month`, `Futures Price`, `Change`,
  `Basis`, `Bushel Cash Price`, `MT Cash Price`).
- No live price, basis, or bid is recorded here — counts and
  structure only.

### Heartland Coop / Mulvane Coop — toggles flipped to `false`

Per the coordinator's decision, both `[sources]` toggles in
`config.toml` were set to `false` (`heartland_coop`,
`mulvane_coop`). They were **not re-probed this cycle** — two
consecutive 0-row wrapper probes each (Cycles 21 and 22) already
established the failure, and the pages no longer carry the
`jsquote.php` script tag the generic parser requires. The poller
would fetch them daily for nothing; toggling off is reversible
(flip back to `true` and re-probe if a site restores the tag).

Split to note for future readers: the `us_elevators_urls.toml`
entries for both sites stay `enabled = true` (Heartland Coop,
`https://www.heartlandcoop.com/markets/cash.php`; Mulvane Coop,
`https://www.mulvanecoop.com/markets/cash.php`). The `[sources]`
toggle is the gate that seeding and polling honour — the toml
`enabled` flag alone does not re-enable a source. The wrappers
(`fetch_heartland_coop`, `fetch_mulvane_coop`) and registry rows
are unchanged, so re-enabling is a one-line toggle flip.

Effect on seeding: the seeded set drops from 104 to 102 adapters
(the toggle-gating tests derive the disabled set from the real
toggles, so they stay correct without hardcoded counts).

### Tests

1 new test in
`GrainBids/grainbids/apps/api/tests/test_source_toggle_gating.py`
(`test_cycle23_zero_row_agricharts_adapters_toggled_off`): both
toggles are `false`, both keys are in the derived disabled set,
sibling adapters (`heritage_grain_cooperative`, `keller`) stay on,
an explicit-key seed of both plus `keller` creates only `keller`
and records both in `skipped_disabled`, and pre-existing rows for
both stay out of the due list. `test_config_toggles_exist_for_all_new_adapters`
in `tests/test_us_agricharts_dtn_adapters.py` was updated to expect
`false` for exactly these two AgriCharts keys (all other AgriCharts
toggles still `true`).

Full API suite: **697 passed, 0 failed** (696 baseline + 1 new).

### AgriCharts futures-fallback design note (design only, 0 GETs)

With both toggles off, the open question is what the generic collector should do when a page no longer carries the `jsquote.php` tag. A design note ([agricharts-futures-fallback-design.md](agricharts-futures-fallback-design.md)) read `fetch_us_agricharts` and `fmn_source.py` and found the key fact: **basis is in the `writeBidRow` row itself** (arg 1), not in the feed — only Futures Price and the two cash prices derived from it (futures + basis) depend on jsquote, while Name, Basis, Delivery, Location and futures symbol are page-native, Futures Month is decodable from the symbol, and Change is never filled anyway. It weighs four options — (a) parse rows with futures/cash `None` (the FMN Cycles 10–11 precedent), (b) derive the feed URL from the row symbols and probe it (exact 2-GET-per-site probe given), (c) leave as-is with periodic re-probes, (d) futures from another feed — and recommends (a), with the (b) probe run first on Heartland only. No code was changed; the decision needed from Adam/coordinator is whether basis-only rows may flow into the pipeline (i.e. downstream handles `None` futures/cash) and whether Futures Month may be decoded from the symbol, with toggles staying off until the chosen option is implemented and probe-confirmed.

### Follow-ups

1. **Heartland / Mulvane — re-enable path:** if either site is
   believed to have restored the `jsquote.php` tag (or the generic
   collector gains an alternate futures source), flip its toggle
   back to `true` and re-probe once through the wrapper. Do not
   re-probe them routinely while the toggles are off.
2. **Heritage — no follow-up.** Live-confirmed at 14 rows; nothing
   open.

## Cycle 24 — AgriCharts fallback (a) implemented; (b) probe fails; staleness watch 4th consecutive (2026-11-19)

### AgriCharts futures fallback, option (a) — implemented + tested (2 GETs live verification)

Coordinator decision (Cycle 24): option (a) from the Cycle 23 design note is APPROVED — (i) basis-only rows may flow into the pipeline (futures/cash explicitly `None` with a note, never invented; no quarantine, same as FMN), (ii) Futures Month may be decoded from the symbol. `fetch_us_agricharts` no longer returns empty when the jsquote tag is absent/unmatched: it parses rows as basis-only (Basis / Delivery / Location / Name / Symbol filled, Futures Month decoded from the contract symbol via a new `futures_month_from_symbol()`, Futures Price / Change / both cash prices `None` with a `Note` column). Tag-present behaviour unchanged; Chrome UA unchanged. 5 new tests (synthetic fixtures, neutral names); full suite 702 passed.

**Live verification: Heartland 0 rows, Mulvane 0 rows.** Both pages' `writeBidRow` rows are no longer matched in the static HTML at all — the design doc's §3 assumption (rows still in the HTML) does not hold live. So (a) is proven by mocked tests but recovers neither site today. **Toggles stay `false`.** Scope note: degrading the same way when the tag IS present but the feed fetch fails was NOT implemented (tag-present behaviour kept exactly unchanged); it is a one-line follow-up.

### Option (b) probe — Heartland: fails (2 GETs)

**Correction to Cycles 21–23:** Heartland's jsquote tag is **not missing** — it is present but with an empty symbols list (`symbols=&fields=name,month,last...`). The collector regex requires `[A-Z0-9,]+` after `symbols=`, so it does not match and the collector reports "tag not found". The derived feed URL (exact design-doc pattern) returned HTTP 200, 20 bytes, body exactly `var quotes = null;` — the endpoint is alive and the URL shape is confirmed, but with an empty symbol list there is nothing to query: 0 symbols, nothing usable. (b) fails because there is nothing to query, not because of a 404 or wrong shape.

**Deeper finding:** Heartland's default "All Locations" view carries **zero `writeBidRow` data rows** in the static HTML (the single occurrence is the function definition; no `<h4>` headings, no quoteboard tables). The bid area is empty. Open hypothesis (untested, needs a further GET): rows may appear only when a `location_filter` value is selected — the page lists a Location filter with 106 named points. Follow-up probe (1 GET, later cycle): `cash.php?location_filter=<one id>`. Mulvane was not probed for (b) (gated on Heartland's feed answering — it did not) and its page structure was not inspected this cycle.

### Staleness daytime re-check — still Nov 18, all four (4 GETs)

Daytime re-check (Thu, Nov 19) of the four one-day-stale Bushel widgets: **none refreshed to Nov 19**. All four still carry the header "Cash bids for Wednesday, November 18, 2026", zero Nov 19 date strings anywhere in any page. The widgets do not refresh later in the day, at least not by the morning check.

| Site | Header | Rows | Streak |
|---|---|---|---|
| Smithfield Chadbourn 2294 | Nov 18 | 1 Soybeans | Cycles 13, 14, 22, 24 |
| Smithfield Hamer, SC 2179 | Nov 18 | 1 Soybeans | Cycles 16, 22, 24 |
| Skyland Hugoton, KS 3370 | Nov 18 | 6 (Corn/Milo/Red Wheat) | Cycles 14, 22, 24 |
| Skyland Vilas-Walsh 3621 | Nov 18 | 5 (Corn/Milo/Red Wheat) | Cycles 14, 22, 24 |

All still exactly one day stale — no worse. Standing note stands: a same-day freshness gate would fail these four daily, so they need an exemption/lag tolerance if such a gate is ever added.

### Follow-ups

1. **Heartland filtered-view probe (1 GET):** `cash.php?location_filter=<one id>` — tests whether rows appear only under a selected location. Same probe could be run for Mulvane.
2. **Feed-down degradation (one-line follow-up):** treat empty quotes from a present tag like the no-tag path.
3. **Staleness watch:** no further daytime re-checks needed — the refresh-later-in-the-day hypothesis is now answered (no). Keep the four on the exemption list for any future freshness gate.

## Cycle 25 — Heartland filtered view empty; Mulvane re-checked empty; feed-down degradation (2026-11-19)

### Heartland filtered-view probe (1 GET)

`https://www.heartlandcoop.com/markets/cash.php?location_filter=22143` (ADM – DSM, first named option in the page's 106-location filter): HTTP 200, 36,246 bytes. The server honoured the filter (option marked selected), but the page still carries **0 `writeBidRow` data rows** and the jsquote tag still has empty symbols. The Cycle 24 open hypothesis — rows appear only under a selected location — does **not** hold for the tested location. No usable filtered-URL pattern for the collector; the feed question is moot. Only one location id was tested; default + one filtered view both empty makes a per-location difference unlikely.

### Mulvane default view re-checked (1 GET)

`https://www.mulvanecoop.com/markets/cash.php`: HTTP 200, 33,214 bytes, **0 `writeBidRow` rows**. **Correction:** Mulvane's jsquote tag is **present with empty symbols**, not missing — the Cycle 21–23 "tag missing" phrasing is corrected for Mulvane too. The page has a Location filter (4 named: Clearwater 3866, Clearwater-253 80891, Mulvane 3864, Mulvane-251 80889) and a Commodity filter (Wheat HRW 2461, Corn 2462, Milo 2463, Soybeans 2464). **Both sites stay dark; toggles stay off.** Option (a) still recovers neither site live because the rows are not in the static HTML at all.

### Feed-down degradation implemented (mocked tests only, 0 GETs)

Tag present + jsquote feed returns empty (`var quotes = null;` or `{}`) now degrades like the no-tag path: rows return basis-only (futures/cash `None` with note, month decoded from symbol). 2 new parametrized tests; full suite 704 passed. Tag-absent and tag-present-with-data paths unchanged. Scope note: only the *empty-quotes* case degrades — a feed fetch that raises (HTTP error/timeout) still returns empty via the outer `except`; further one-line follow-up if wanted.

### Follow-ups

1. **Heartland / Mulvane — closed for now.** Default view, one filtered view (Heartland), and the feed derivation all return nothing. No further probes without a new hypothesis (e.g. a JS-rendered route, or a different AgriCharts host). Toggles stay `false`.
2. **Feed-error degradation** (outer `except` path) — one-line follow-up, if wanted.

## Cycle 26 — Live re-verification sweep: all five exact matches; feed-error degradation (2026-11-19)

### Live re-verification sweep (5 site probes, Thu, Nov 19)

All five key collectors re-verified live via their wrappers; **all returned `status='ok'` with row counts identical to the last verification — no drift, no failures.** Counts only, no values recorded.

| Collector | Rows now | Last verified | Verdict |
|---|---|---|---|
| FMN (`fetch_fmn_cash`) | 453 rows (87 points, 204 tables; 449/449 futures-linked filled) | Cycle 10–11: 453 | Exact match |
| Five Star Coop (`fetch_five_star_coop`) | 299 rows, 21 locations | Cycle 8–9: 299 | Exact match |
| TGM embed (`fetch_tgm`) | 362 rows, 24 locations | Cycle 9: 362 | Exact match |
| USDA mirror, James Valley (`fetch_usda_mirror`) | 197 rows, 29 regions, report id 7730, dated Nov 18 | Cycle 4: 197 | Exact match |
| FAC, Bushel (`fetch_fac`) | 45 rows, 3 locations; header dated Nov 19 | Cycle 4–5: 45 | Exact match |

Notes: FMN's dropdown still lists more points than the 204 tables (known limitation, unchanged); Five Star's page trade date is Nov 18; FAC's widget header is fresh (Nov 19). The five collectors' live behaviour is stable across cycles — the catalogue's verified counts stand.

### Feed-error degradation implemented (mocked tests only, 0 GETs)

Only the `_fetch_jsquote` call is now wrapped in its own `try/except`: a feed fetch that RAISES (HTTP error/timeout) degrades to basis-only rows, like the no-tag (Cycle 24) and empty-feed (Cycle 25) paths. A page fetch that raises still returns empty via the outer `except` (no HTML to parse, no invented rows). 5 new mocked tests (3 feed-raises, 2 page-raises); full suite 709 passed. This closes the last open follow-up from the Cycle 23 design note — all three degradation paths (no tag, empty feed, feed error) now behave the same way.

## Cycle 27 — AgriCharts wrappers re-verification: all 10 exact matches (2026-11-19)

Live re-verification sweep of the 10 working US AgriCharts wrappers (one call each, no retries). **All 10 returned `[US-AG OK]` with no warnings — no degraded/basis-only path, no jsquote failures — and row counts exactly matching Cycle 21.** 639 rows total, 0 zero-row results. Counts only, no values recorded.

| Wrapper | Rows now | Cycle 21 | Locations |
|---|---|---|---|
| Ag Plus | 36 | 36 | 6 |
| Farmers Win Coop | 171 | 171 | 18 |
| Keller | 14 | 14 | 1 |
| Kokomo Grain | 63 | 63 | 8 |
| Legacy Farmers | 66 | 66 | 10 |
| Pro Ag | 78 | 78 | 6 |
| West-Con | 84 | 84 | 1 |
| Wheaton Dumont | 43 | 43 | 8 |
| Central Farmers Coop | 75 | 75 | 11 |
| Anthony Farmers Co-op | 9 | 9 | 3 |

Heritage was confirmed live in Cycle 23 (14 rows) and Heartland/Mulvane are closed for now — neither was re-probed. Together with Cycle 26's sweep (FMN 453, Five Star 299, TGM 362, USDA mirror 197, FAC 45), every live-verified collector has now been re-checked this morning with zero drift — the catalogue's verified counts stand.

## Cycle 28 — Embed family re-verification: all 13 exact matches; FS Grain mirror confirmed (2026-11-19)

Live re-verification sweep of the full 13-site AgriCharts-embed family plus the FS Grain USDA mirror (13 calls, one per site, no retries). **All returned `status='ok'` with row counts exactly matching their earlier verifications — no drift, no failures.** Counts only, no values recorded.

| Site | Rows now | Prior | Locations |
|---|---|---|---|
| Agtegra | 8 | 8 (Cycle 7) | 1 (Hecla) |
| Heritage Cooperative (embed) | 15 | 15 (Cycle 7) | 1 (Ada) |
| Linn Coop | 51 | 51 (Cycle 7) | 5 |
| Midway Coop | 8 | 8 (Cycle 7) | 1 ("All Locations") |
| Ag State | 11 | 11 (Cycle 7) | 1 |
| Superior Ag | 12 | 12 (Cycle 7) | 1 |
| ALCIVIA | 181 | 181 (Cycle 9) | 15 |
| TGM | 362 | 362 (Cycle 9) | 24 |
| PRO Coop 21297 (Ayrshire) | 6 | 6 (Cycle 11) | 1 |
| PRO Coop 21302 (Manson) | 12 | 12 (Cycle 12) | 1 |
| PRO Coop 21302b (Manson dup) | 12 | 12 (Cycle 13) | 1 |
| Hull Coop | 12 | 12 (Cycle 12) | 1 |
| StateLine Coop | 126 | 126 (Cycle 12) | 11 |

**816 rows across the 13 embed sites** (TGM re-verified in Cycle 26; the other 12 this cycle). Structure unchanged everywhere: same location sets, commodity splits, and groupby behaviour (Ag State / Superior Ag still group by commodity with `location_name` authoritative; Midway still publishes the single "All Locations" label; StateLine still 12 rows per location except Emmetsburg-AGP, Soybeans-only with 6).

USDA mirror, FS Grain (`fetch_usda_mirror_fs_grain`): **197 rows, report id 7730, dated Nov 18, 2026** — exact match to the James Valley re-verification in Cycle 26. Caveat: the region count was not re-tallied this run (rows grouped on `location`, which is "United States" for all rows); the 29-region figure stands from Cycle 26.

## Cycle 29 — Bushel sample re-verification (6/6 exact); Mae-Mart still viable (2026-11-19)

### Bushel per-location sample re-verification (6 calls)

One call per site, no retries. **All 6 returned `status: ok` with exact row-count matches** to the Cycles 13–16 baselines. Counts only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2731 Conlen–Hartley | 5 | Nov 19 | Exact match |
| Skyland 3370 Hugoton, KS | 6 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 1691 Waverly, VA | 7 | Nov 19 | Exact match — still the fattest page |
| Smithfield 1671 Kinston, NC | 3 | Nov 19 | Exact match |
| Smithfield 1689 Nichols, SC | 1 | Nov 19 | Exact match |
| Smithfield 2067 Lapaz, IN | 2 | Nov 19 | Exact match |

5 of 6 headers fresh (Nov 19); only Hugoton remains dated Nov 18 — same one-day lag as Cycles 14 and 24, row count/composition unchanged, so site-side staleness, not a collector issue. One Waverly delivery label carries the site's own call-ahead note ("Nov 2026 -starting 11/16/26. *Please Call Ahead*") — published text, not a price.

### Mae-Mart live re-check (2 logical probes)

- **Grain-pricing page:** HTTP 200, 35,952 bytes — **byte-identical size to Cycle 18**. Inline pricing JS still present (`var PROXY = '/grain-proxy.php';`, cosmetic whitespace only); symbols `ZCZ26=F`, `ZSF27=F`, `ZWN27=F` unchanged; all 4 tables present, 1 row each (basis numeric, cash/futures "—" in static HTML, as documented); rye `manualPrice` still in the inline `ALL_BIDS` JSON; `USX` cents rule still in the JS. No Barchart/DTN/AgriCharts/Yahoo markers.
- **Proxy:** HTTP 200, `application/json`, **89 bytes — byte-identical size to Cycle 19**; JSON shape unchanged (keyed by symbol; `price` numeric, `currency` "USX", `timestamp`/`fetched` ints). **One change:** the `.php` URL now 301s to the extensionless `https://www.mae-martfarms.com/grain-proxy?symbols=ZCZ26=F` (Cycle 19's redirect kept the `.php`). Transparent to the collector (`requests` follows redirects by default) — no code change needed; the stored proxy URL could optionally be updated to the extensionless form.
- **Verdict: collector still viable as-is.** Nothing restructured, no dead endpoints, no symbol changes.

## Cycle 30 — Bushel sample #2 (6/6 exact); Mae-Mart proxy URL stored extensionless (2026-11-19)

### Bushel per-location sample #2 (6 calls)

One call per site, no retries. **All 6 returned `status: ok` with exact row-count matches** to the Cycles 13–16 baselines. Counts only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2734 Etter | 5 | Nov 19 | Exact match |
| Skyland 2761 Elkhart–Hough–Rolla Area | 6 | Nov 19 | Exact match |
| Skyland 2778 Buckeye–Syracuse | 6 | Nov 19 | Exact match |
| Smithfield 1670 Hobbsville | 3 | Nov 19 | Exact match |
| Smithfield 1690 Petersburg, VA | 4 | Nov 19 | Exact match |
| Smithfield 2179 Hamer, SC | 1 | **Nov 18** | Exact match (count); still one day stale |

5 of 6 headers fresh (Nov 19); Hamer remains dated Nov 18 — same one-day lag as Cycles 16 and 24, count unchanged, site-side lag not a collector issue. Delivery-label structure unchanged (Skyland "N/C 26/27" labels; Petersburg's second Soybeans row still carries the "Nov 2026 - SBOC 10% or Above" label).

### Mae-Mart proxy URL stored extensionless (mocked tests only, 0 GETs)

Following the Cycle 29 finding (the `.php` URL now 301s to the extensionless canonical form), the stored proxy URL in `mae_mart_source.py` was updated: `http://www.mae-martfarms.com/grain-proxy.php` → `http://www.mae-martfarms.com/grain-proxy` (5 occurrences, URL string only, no behaviour change; scheme kept as `http`). Query construction unchanged (one GET per symbol). New mocked test `test_mae_mart_proxy_url_is_extensionless` asserts the constant and that the mocked fetch calls exactly that URL with `params == {"symbols": "ZCZ26=F"}`. Full suite 710 passed.

## Cycle 31 — Bushel samples #3 + Cycle 4/5 sites: 12/12 exact; Almota joins staleness watch (2026-11-19)

### Bushel per-location sample #3 (6 calls)

One call per site, no retries. **All 6 returned `status: ok` with exact row-count matches** to the Cycles 13–16 baselines. Counts only, no values recorded.

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Skyland 2740 Moscow/Dermot/Kismet/Pleasant Valley | 7 | Nov 19 | Exact match |
| Skyland 3621 Vilas–Walsh | 5 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 2294 Chadbourn | 1 | **Nov 18** | Exact match (count); still one day stale |
| Smithfield 1725 Bladenboro | 1 | Nov 19 | Exact match |
| Smithfield 2064 Kinston JCH, NC | 3 | Nov 19 | Exact match |
| Smithfield 1683 Creswell | 2 | Nov 19 | Exact match |

### Cycle 4/5 Bushel sites re-verification (6 calls)

One call per site, no retries. **All 6 returned `status: ok` with exact row-count matches** to Cycle 5. Counts only, no values recorded.

| Site | Rows now | Cycle 5 | Locations |
|---|---|---|---|
| Chandler Feed | 17 | 17 | 1 (Chandler) |
| Cameron Coop | 4 | 4 | 1 (Cameron) |
| CGS | 4 | 4 | 1 (Bazine) |
| Almota | 12 | 12 | 1 (Colfax) |
| Williams Gin | 2 | 2 | 1 ("Williams Gin & Grain" as location label; town still unconfirmed from the page, as in Cycle 5) |
| Rugby | 12 | 12 | 1 (Rugby) |

**New staleness note: Almota's widget header is dated Nov 18** — one day stale, the same lag pattern as Chadbourn / Hugoton / Vilas-Walsh / Hamer. Its row count is still exactly 12, so the collector parses it fine; the page is serving yesterday's board. Almota joins the staleness watch list (first stale probe for it). The watch list is now five widgets: Chadbourn, Hamer, Hugoton (3370), Vilas-Walsh (3621), Almota — all exactly one day behind, all still on the exemption list for any future freshness gate.
