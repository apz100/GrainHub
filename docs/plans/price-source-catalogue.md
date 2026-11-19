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
| Mae-Mart Farms | Norfolk County | http://www.mae-martfarms.com/grain-pricing | Plain HTML tables (gp-table-*) | corn, soy, wheat, rye | continuous in market hours | **Collector added 2026-11-19 (Cycle 3):** `mae_mart_source.py` parses the tables. Basis is static; corn/soy/wheat cash prices are JS-filled from the site's futures proxy, so those rows carry basis with cash price empty + reason (never guessed). Rye has a static manualPrice, so its cash price is parsed. Homepage cards are "—" placeholders only. |
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
| Ag Plus | — | https://www.agplusinc.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified 2026-11-19. Keep. |
| Farmers Win Coop | — | https://www.farmerswin.com/markets/cash.php | AgriCharts | corn, soybean | intraday | Verified. Keep. |
| Heartland Coop | — | https://www.heartlandcoop.com/markets/cash.php | AgriCharts | corn | intraday | Verified. **Config fixed**: `config.toml` used `myaccount.heartlandcoop.com/bids.htm` (no bid marker); switched to cash.php. |
| Heritage Grain Cooperative | — | https://www.heritagegrain.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified. Keep. (Page title says "Legacy Grain" — possible rebrand.) |
| Keller | — | https://www.kellergrain.com/markets/cash.php | AgriCharts | corn, soybean, wheat | intraday | Verified. Keep. |
| Kokomo Grain | Kokomo, IN | https://www.kokomograin.com/markets/cash.php?location_filter= | AgriCharts | corn, soybean, wheat | intraday | Verified. Keep. |
| Legacy Farmers | — | https://www.legacyfarmers.com/markets/cash.php | AgriCharts | corn, wheat | intraday | Verified. Keep. |
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
| Central Farmers Coop | Salem, SD | https://www.cenfarmcoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, oats | intraday | **Verified** `writeBidRow`. Added to active config. |
| Anthony Farmers Co-op | Harper, KS | https://www.anthonycoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, milo, canola | intraday | **Verified** `writeBidRow`. Added to active config. |
| Mulvane Cooperative Union | Mulvane, KS | https://www.mulvanecoop.com/markets/cash.php | AgriCharts | corn, soybean, wheat, milo | intraday | **Verified** `writeBidRow`. Added to active config. |
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
| CGB | https://cgb.com/cgb-grain/ | 200 | No | Corporate grain page; no widget, no bid table | None at this URL; USDA SCL follow-up still open |
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
| PRO Coop | https://procooperative.com | 200 (→ `/`) | No | **AgriCharts `cashbids.php` embed ×3** (`procooperative.agricharts.com`, locations 21297 `groupby=location` + 21302 `groupby=ccommodity`); also links `/cash-bids` and a `my.procooperative.com` login portal (not followed) | **Collector candidate (later cycle):** same family as Cycle 7/9's six + ALCIVIA/TGM — one GET of the loader-derived `cashbids-js.php` URL to prove the static `var bids` route. Reclassified `unknown → agricharts-embed`, still disabled. **Cycle 11 (2026-11-19):** 21297 Ayrshire view verified (6 Corn rows), enabled. **Cycle 12 (2026-11-19):** first 21302 embed verified (MANSON.IA, 12 rows — CORN 6, SOYBEANS 6), separate registry entry `pro_coop_21302`; second 21302 embed still unchecked. |
| Ray Carroll | https://www.ray-carroll.com | 200 | No | **DTN index.cfm iframes ×4** (`index.cfm?show=87…layout=combined_table_by_location`, corn / soybeans / SRW wheat / milo); page tables are nav / futures / announcements; footer "Copyright DTN" | DTN Playwright — same `index.cfm` family as Great Lakes Grain / London Ag. Reclassified `unknown → dtn`, still disabled (render check + iframe/sub-page route open) |
| Skyland Grain | https://www.skylandgrain.com | 200 | No | **Bushel FCCP family**: `portal.bushelpowered.com/skyland` app links, `/cashbidssingle-` nav link; no `.cbmod` widget on the homepage, no bid table | Bushel — bids live on the `/cashbidssingle-` sub-page. Reclassified `unknown → bushel`, still disabled; one GET of `/cashbidssingle-` next. **Cycle 11 (2026-11-19):** 200 at `/cashbidssingle-` — the nav link target is literally `/cashbidssingle-` (empty ID) and serves a **14-location picker** (`CashBidsLocationID`s 2730–3621 in static HTML). The sweep worker reported no widget — **corrected by the coordinator's re-check: the page also serves a static 7-col `.cbmod` widget (Cunningham Area, 6 rows) and is now enabled with a registry entry** (see the Cycle 11 section). |
| Smithfield | https://smithfieldgrain.com | 200 | No | **Bushel FCCP family**: "Data provided by Bushel" footer, `portal.bushelpowered.com/smithfield` links; no `.cbmod` widget on the homepage — the only table is a futures table (Contract / Last / Chg) | Bushel — bids live on the FCCP cash-bids pages (nav: `/fccp-cash-bids-east-region-20249`). Reclassified `unknown → bushel`, still disabled; one GET of the East Region page next. **Cycle 11 (2026-11-19):** 200 at `/fccp-cash-bids-east-region-20249` — a **per-location link list** (NC / IN / OH / SC / VA, ~30 locations), no static rows; each location links `/cashbidssingle-<id>` and page JS iframes that target per location; probe one per-location target next (e.g. `/cashbidssingle-1666`, Bentonville); stays `bushel`, still disabled. |
| Star of the West | https://www.starofthewest.com | 200 | No | Milling-company homepage; zero cash-bid mentions, no grain/bid links at all | None — reclassified `unknown → none`, do not add |
| StateLine Coop | https://www.statelinecoop.com | 200 (→ `statelinecoop.com/`) | No | WordPress homepage, no challenge page this time (Cycle 1 reported a Cloudflare challenge; the reCAPTCHA strings now are form-related). No widget on homepage; nav links `/cash-bids`; page CSS references `table.cashbid_table`, hinting at an embed on the sub-page | None at this URL — stays `unknown`; one GET of `/cash-bids` next. **Cycle 11 (2026-11-19):** 200 at `/cash-bids` — AgriCharts `cashbids.php` embed (`statelinecoop.agricharts.com`, `groupby=location`) plus custom CSS for `table.cashbid_table`, no static rows; reclassified `unknown → agricharts-embed`, still disabled; `cashbids-js.php` check open. **Cycle 12 (2026-11-19):** `cashbids-js.php` 200, `var bids` JSON, 126 rows (11 locations — Corn 60, Soybeans 66); enabled, registry entry `stateline_coop`. |
| Sunrise | https://www.sunriseco-op.com | 200 | No | **Classic DTN**: `<div id="target">` + `CashBidTable(tableOptions)`, companyID 23043, CIHedging `CashBidWidget.js` / `ChartJS.js`, ATLAS DTN shell (`/dtncashbidwidget/bindlocation`) | **Exact fit for existing `us_dtn_source.py`** — reclassified `unknown → dtn` and **enabled** in `us_elevators_urls.toml` (the only enable in this cycle). Playwright render check still open |
| Synergy | https://www.synergycoop.com | 200 | **Yes — 4 rows, Corn 2 + Soybeans 2, Cameron, 6-col widget, dated header Nov 19, 2026** | Bushel `.cbmod` widget in static HTML (div/`ul` rows, `sixColumnsBigFirst`, not `<table>` rows) | **Collector candidate — ready:** the existing generic `bushel_source.py` parses the saved HTML with status ok (4 rows, Cameron, Corn 2 + Soybeans 2). Reclassified `unknown → bushel` and enabled; `BUSHEL_SITES` registry entry + `fetch_synergy()` added in Cycle 10 (3 tests) |
| The Andersons | https://www.andersonsgrain.com | 200 | No | Corporate Trade Group homepage, no widget; bid links `/locations/cash-bids/` + `/local-bids/locations-list/` | None at this URL — stays `unknown`; one GET of a bid sub-page next. Distinct from The Andersons Canada (DTN, Ontario section). **Cycle 11 (2026-11-19):** 200 at `/locations/cash-bids/` — proprietary GRAINweb "MyCashBids" **interactive location-picker** (choose a location + commodities, click Add; selections saved for next visit), no static rows, no recognizable embed; bids load via JS after a location is picked; needs a browser/API investigation; stays `unknown`, still disabled. |
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
| The Andersons | https://www.andersonsgrain.com/locations/cash-bids/ | 200 | No | Proprietary GRAINweb **"MyCashBids" interactive location-picker**: "Customize Your Cash Bids! Select the location first, and then the commodities…" with an Add-commodity form (`data-ui="add-commodity"`), a "Bid and Basis Charts" modal, and an empty-src `chartFrame` iframe; links to `/local-bids/locations-list/` and `/local-bids/locations/` | No recognizable embed and no static rows; bids load via JS after a location is picked. Stays `unknown`, still disabled; needs a browser/API investigation (distinct from The Andersons Canada, DTN, in the Ontario section) |
| Skyland Grain | https://www.skylandgrain.com/cashbidssingle- | 200 | **Yes — 6 rows** (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area), widget header dated Nov 19, 2026 | The nav link target is literally **`/cashbidssingle-` (empty ID)** and serves a **14-location picker** (`CashBidsLocationID`s 2730–3621 in static HTML) **AND** a static 7-col Bushel `.cbmod` widget for the default location (Cunningham Area). The sweep worker reported "no `.cbmod` widget, no bid rows" — **wrong; corrected by the coordinator's re-check** (a fresh GET parses ok, 6 rows; the saved `/tmp/cycle11` HTML parses ok too). Same canonical trailing-dash pattern as Williams Gin (Cycle 5) | **Collector-ready:** the existing generic `bushel_source.py` parses it with no changes. **Enabled** (entry URL updated to `/cashbidssingle-`); `BUSHEL_SITES` registry entry + `fetch_skyland()` added in Cycle 11 (6 tests). Per-location `/cashbidssingle-<id>` targets still open. **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-2730` — **static 7-col `.cbmod` widget, 6 rows (Corn 2, Milo 1, Red Wheat 2, Soybeans 1, Cunningham Area)** — 2730 is Cunningham Area's own per-location ID, so the rows duplicate the default page; **enabled** as a separate entry (`skyland_2730` + `fetch_skyland_2730()`); 13 picker IDs still open. |
| Smithfield | https://smithfieldgrain.com/fccp-cash-bids-east-region-20249 | 200 | No | **Bushel FCCP per-location link list** (NC / IN / OH / SC / VA, ~30 locations, e.g. Bentonville 1666, Bladenboro 1725); no static rows, no `.cbmod` widget; page JS iframes `/cashbidssingle-<locId>` per location | Bushel — bids live on the per-location `/cashbidssingle-<id>` targets. Stays `bushel`, still disabled; probe one per-location target next (e.g. `/cashbidssingle-1666`, Bentonville). **Cycle 12 (2026-11-19):** 200 at `/cashbidssingle-1666` — **static 7-col `.cbmod` widget, 3 rows (Soybeans 1, Wheat 1, Corn 1, Bentonville, NC)**; **enabled** as a separate per-location entry (`smithfield_bentonville` + `fetch_smithfield_bentonville()`); ~29 East Region locations still open. |
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
  found in its JS bundles; no static route exists.
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
  13 more picker IDs on file (2730 was the first; the remaining IDs
  run to 3621) — each new ID is a new location's widget. Smithfield
  has ~29 more East Region locations (e.g. Bladenboro 1725 from the
  Cycle 11 link list). Both families are now proven to serve static
  `.cbmod` widgets at the per-location targets, so each probe is
  low-risk; probe a few per cycle, not in bulk.
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
entry), the second 21302 embed still open. `config.toml` gains
three toggles (`hull_coop`, `stateline_coop`,
`pro_coop_21302`), all true. All other entries unchanged.

### Follow-ups for a later cycle

- **PRO Coop second 21302 embed (one GET):** the homepage's
  other location-21302 embed (`groupby=ccommodity`, fields
  `delivery_start` / `price` / `basis` / `futureschange` — no
  `delivery_end`) was not checked; derive its `cashbids-js.php`
  URL from the saved Cycle 11 homepage fetch
  (`/tmp/procoop_home.html`) the same way and fetch it once.
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
