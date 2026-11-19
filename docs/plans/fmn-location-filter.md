# FMN location_filter verification (Cycle 3, 2026-11-19)

One polite GET per URL, contact User-Agent
`GrainHub-Research/1.0 +https://github.com/apz100/GrainHub`.
Locations, crops, and structure only — **no prices copied here**.

## Question

The FMN cash page (`https://fmn1.agricharts.com/markets/cash.php`)
shows 204 bid tables on its default view, but its Location dropdown
lists 336 options (335 named). Do the dropdown option values map to
numeric `location_filter` IDs, and does fetching a dropdown-only
location (e.g. Winchester) load its bid table?

## Finding 1 — dropdown values ARE numeric location_filter IDs

`GET https://fmn1.agricharts.com/markets/cash.php` → HTTP 200.

- `<select id="locationFilter">` present with **336 `<option>`s**.
- Every non-empty option `value` is numeric. First option is empty
  (`All Locations`).
- Examples of the value/label shape: `88363` → `Alliston`,
  `4189` → `Alliston Corn`, `4202` → `Alliston Soybeans`,
  `3407` → `Amberly Corn`.
- Winchester entries: `2523` → `Winchester` (location-level),
  `1965` → `Winchester Corn`, `1992` → `Winchester Soybeans`.
- Same pattern for other dropdown-only entries, e.g. Sarnia has
  location-level IDs (`35807`, `35809`, `35810`, `35811` → `Sarnia`)
  plus commodity-specific IDs (`2700` → `Sarnia Ethanol Corn`,
  `35806` → `Sarnia Transfer Corn`, `35808` → `Sarnia Transfer
  Soybeans`).
- This matches the existing collector pattern in
  `app/platform/market_data/sources/cash_bids_dynamic.py`, which
  builds `cash.php?location_filter={loc_id}` URLs from the same
  dropdown.

## Finding 2 — filtered page loads, but bid rows are JS-rendered

`GET https://fmn1.agricharts.com/markets/cash.php?location_filter=2523`
(Winchester, location-level ID) → HTTP 200.

- The dropdown on the returned page shows **Winchester selected**,
  and the page contains the bid-table scaffolding (Cash Price /
  Basis headings, the `writeBidRow` JavaScript function).
- **However, the static HTML contains zero inline `writeBidRow(...)`
  invocations** (the function definition only), and the
  `jsquote.php` script tag carries an **empty `symbols=` parameter**.
- Contrast with the default (unfiltered) view fetched the same day:
  **454 inline `writeBidRow(...)` invocations** and a populated
  `symbols=` list (CBOT futures symbols), i.e. the default view
  embeds bid rows directly in the HTML.
- The filtered page's remaining tables are navigation/chrome shells
  only; no bid rows are present in the static HTML.

## Interpretation

- The `location_filter` parameter is **accepted** (HTTP 200,
  Winchester selected in the dropdown), so the mechanism exists.
- The filtered view does **not** embed bid rows in static HTML the
  way the default view does. The rows are presumably loaded
  client-side after render (the filter is applied by JavaScript),
  or not at all for this location.
- **Not yet proven:** whether a browser-rendered
  `?location_filter=2523` page actually displays Winchester bid
  rows. That needs a Playwright render check (browser work — not
  done in this cycle; see open item below).

## Implication for the FMN collector

- If the Playwright render check confirms rows load, the existing
  Playwright collector pattern (`cash_bids_dynamic.py`) can iterate
  the dropdown's numeric IDs and cover up to **335 Ontario points**
  from one URL pattern — including dropdown-only locations
  (Winchester, Sarnia, Goderich, Durham, Wellington, Chatham,
  Kintore, Maxville, …).
- Per-location fetching should stay polite (the existing collector
  already sleeps 0.5 s between locations) and should reuse one
  browser session across locations.

## Open item

- **Playwright render check:** load
  `cash.php?location_filter=2523` in headless Chromium and confirm
  Winchester bid rows render (and count tables/rows). If rows do not
  render, investigate how the filter is applied client-side before
  building the 335-location sweep. Do not guess additional endpoints.
