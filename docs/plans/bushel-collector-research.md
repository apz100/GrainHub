# Bushel-pattern collector research (Cycle 3, 2026-11-18)

Research only — no collector was written. One polite GET per URL,
contact User-Agent `GrainHub-Research/1.0 +https://github.com/apz100/GrainHub`.

> **Correction (Cycle 4):** the bids are **not** in `<table
> class="standardTable">` / `<table class="market_table">`. On both
> verified sites the bids live in the `.cbmod` div widget — the same
> structure `collwest_source.py` already parses. FAC's only
> `standardTable` is a 4-row "Data provided by Bushel" footer and
> Collwest's `market_table` is the futures market table. The generic
> collector (`bushel_source.py`) parses the widget first and only
> falls back to a real `<table>` when its header contains both
> "Delivery" and "Bid". FAC verified live: 45 rows, 3 locations.
> Collwest cross-check: 16/16 rows match the existing collector.

## Question

Can one collector pattern cover the 11 disabled Bushel-pattern sites
in the price-source catalogue (10 US + Collwest, now confirmed
Canadian — see below), or does each site need its own scraper?

## Sites inspected live

| Site | URL fetched | Result |
|---|---|---|
| FAC (Farmers Cooperative Elevator Co.), Arcadia, IA | https://www.faccooperative.com/cash-bids | 200, 188,057 bytes |
| Collwest Grain, Ltd., Collingwood, ON | https://www.collwestgrain.com/ | 200, 158,518 bytes |
| Collwest Grain (Bushel host) | https://collwestgrain.o.bushelsites.com | 200, 158,600 bytes — content identical to the www domain |

Both pages show bids dated **Wednesday, November 18, 2026** (the
fetch day), headed "Cash bids for [date]".

## Finding: bids are in static HTML — no JS rendering needed

On both sites the full bid table is server-rendered in the HTML
returned by a plain GET. No API endpoint, GraphQL, or JSON payload
carries the bids; no JavaScript execution is required to see them.
The earlier Cycle 1 note that Bushel bids are "JS-rendered" is
**wrong for these two sites** (it was inferred from widget references,
not from a rendered check). A plain-requests + HTML-table parser
should work — Playwright is not needed for FAC or Collwest.

## Shared platform structure

Both sites are the same "Bushel Sites" platform
(`o.bushelsites.com` hosting; branded domains front the same host):

- ASP.NET pages (`ScriptResource.axd`, `.axd` handlers).
- Identical script stack: jQuery 3.6.3, jquery-migrate 3.4.0,
  jQuery UI 1.13.2, modernizr, `/scripts/jquery.main.js`,
  bxSlider 4.2.15.
- Footer attribution on both: "Data provided by Bushel — All prices
  delayed 10 minutes." (with a link to bushelpowered.com).
- Grower portal links to `portal.bushelpowered.com/<site>/welcome`.
- Images served from `<site>.o.bushelsites.com`.
- The branded domain and the `o.bushelsites.com` subdomain serve
  the same content (Collwest bytes differ by <0.1%); the branded
  domain is the canonical URL.

## Table shapes (the variation a single collector must handle)

| | FAC | Collwest |
|---|---|---|
| Table class | `standardTable` (1 table on the page) | `market_table` (2 tables: cash bids + a futures market table) |
| Columns | Delivery, Bid, Basis, Futures, Change, Futures Month, Last Trade (7) | Delivery, Bid, Basis, Futures, Change (5) |
| Commodity grouping | Section heading per commodity (Corn, Soybeans, …) | Section heading per commodity (Corn, Soybeans, Soft Red Wheat, HRW, HRS, Canola, Barley, Oats) |
| Delivery labels | Month labels ("November '26", "December '26", … "Oct. / Nov. '27") | Crop-year labels ("2026 Crop", "2027 Crop", "2028 Crop") |
| Thin rows | — | Barley / Oats rows carry Bid only (no Basis / Futures / Change) |
| Units | USD per bushel (US site) | **CAD**: corn/soy/wheat per bushel; canola, barley, oats per tonne |

Currency evidence for Collwest: the canola row's futures value
matches the ICE canola contract (CAD/tonne) and barley/oats bids sit
at per-tonne scale; the page also lists a "Canadian Dollar" futures
contract in its market-data table. See the Collwest note below.

## What a collector would need (sketch, not built)

1. Plain HTTP GET with the contact UA; parse the HTML.
2. Find the cash-bids table by class (`standardTable` or
   `market_table`), ignoring any second market/futures table.
3. Walk section headings for the commodity, then rows for delivery /
   bid / basis / futures / change (basis, futures, change, futures
   month, last trade optional — absent on thin rows).
4. Per-site config (not per-site code): URL, table class,
   currency + unit map (USD/bu vs CAD/bu vs CAD/t by commodity),
   locations covered.
5. Date handling: the page shows the current day's bids only; no
   archive or history was observed on either page.

## Open questions before building

- **Pattern confirmation on a third site.** Only FAC and Collwest
  were fetched. Confirm the same static-table shape on one more
  Bushel site — ideally a homepage-only one (Cameron Coop, CGS,
  Forest River, Rugby) — before building, since those may put the
  table on the homepage rather than a `/cash-bids` page.
- **FAC location coverage.** FAC's nav lists Arcadia, Manning and
  Schleswig, but the cash-bids table has no location column. It is
  unverified whether the page covers one location or all three.
- **Williams Gin URL.** `williamsginandgrain.com/cashbidssingle-`
  loads but the path looks truncated; confirm the canonical cash-bids
  URL before adding it.
- **Almota is ambiguous.** Its HTML carries a DTN reference while
  its snippet says "Data provided by Bushel" — confirm which widget
  actually renders the bids.
- **Canadian units.** Collwest is CAD (see below). If any other
  Bushel site turns out Canadian, the collector must carry
  currency/units per site, not per pattern.

## Verdict

**Yes — a single Bushel collector pattern looks feasible.** The two
sites checked share a platform, a script stack, a dated "Cash bids
for [date]" heading, and a server-rendered HTML bid table. The
variation is limited to table class, column set, delivery-label
style, and currency/units — all handleable with per-site config
around one parser. No Playwright, no API key, no login.

## Collwest country/currency note (answered in this cycle)

Collwest Grain is **Canadian, CAD**. Evidence from the live fetch
of https://www.collwestgrain.com/ (2026-11-18):

- Address in the page footer: 2924 Sixth Line, Collingwood, ON
  L9Y 3Z1; phone 705-445-7276 (Ontario area code).
- Canola/barley/oats bids are per-tonne scale (canola futures shown
  against the ICE canola contract, CAD/tonne); corn/soy/wheat are
  per bushel.
- The page lists a Canadian Dollar futures contract in its
  market-data table.

**Do not enable Collwest in the US config.** It belongs in the
Ontario panel once the Bushel collector exists. The
`collwestgrain.o.bushelsites.com` host serves identical content;
use the www domain as canonical.
