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
| Sunrise | — | https://www.sunriseco-op.com | DTN `CashBidTable` on homepage | — | intraday | Verified widget on homepage; find its cash-bids sub-page for a stable URL. |

### Dead — disabled in config (2026-11-19)

Cardinal Ethanol (404), Gold Eagle Coop (404), POET (404 — site redesigned, no cash.php), Luckey Farmers (404), Hull Coop (404). Mercer Landmark (522, may be transient — re-check later), CVA (202 empty body — re-check later).

### Blocked / uncertain — do not retry aggressively

StateLine Coop (Cloudflare "One moment, please..."), Landus (HTTP 429 Vercel checkpoint), Al-Corn + Elite Octane (captcha-related strings; page otherwise looks real — re-check with a browser/Playwright).

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
