# Phase D — Collector coverage deepening (2026-11-20, overnight marathon)

HTTP-level only (curl/python `requests`, contact User-Agent
`GrainHub-Research/1.0 +https://github.com/apz100/GrainHub`). No
browser/Chromium was used — the sandbox browser cannot egress.
No prices are recorded here — HTTP statuses, shapes, and row
counts only. Method: every toggle-relevant registry adapter that
can run over plain HTTP was executed live through
`app/services/source_registry.py::fetch_with_adapter` (one polite
GET per adapter; FMN and Mae-Mart make their designed second
GETs). The 8 Ontario Playwright adapters were re-verified by a
raw GET of their catalogue URL (page served + widget markers);
their rendered-row verification still needs a browser. The 13
DTN adapters (all toggled off, JS-only) were not probed — render
checks remain pending. The `andersons` adapter was **not**
probed: it targets the parked legacy DTN host (Cycle 40 rule).

## Headline

- **96 adapters executed live: 93 returned rows, 0 errors.**
  The only zero-row adapters are the three already known:
  `mapleview` (stub by design), `heartland_coop` and
  `mulvane_coop` (closed Cycle 25 — re-confirmed tonight: page
  served, `jsquote.php` script tag still missing, 0 rows).
- **No collector page has changed shape.** Every live row count
  matches the Cycle 35–37 last-verified counts exactly, except
  three site-side content changes (below). No adapter code was
  changed in this phase; no fix was needed.
- Fixture suites for all touched families re-run after the
  sweep: **197 passed, 5 skipped** (`test_fmn_collector`,
  `test_bushel_collector`, `test_cashbids_embed_collector`,
  `test_us_agricharts_source`, `test_usda_mirror_collector`,
  `test_wpdatatables_collector`, `test_ontario_collectors`).

### Site-side changes since last verification

| Adapter | Last verified | Tonight (2026-11-20) | Note |
|---|---|---|---|
| `ag_state` | 11 rows (Cycle 35) | **21 rows** | More rows published on the same `cashbids-js.php` route; parser unchanged |
| `agp` | 8 rows (Cycle 33) | **1 row** | Bushel iframe page content fluctuates site-side (was 1 row in Cycle 7, 8 in Cycle 33, 1 tonight); parser unchanged |
| `usda_mirror_jvg` / `usda_mirror_fsg` | 197 rows (Cycle 36, report id 7730, Nov 18) | **182 rows each** | New daily USDA AMS report; both mirrors agree exactly, as before |
| `north_gower` | verified Cycle 3 (no count recorded) | **15 rows** | First row count recorded for this adapter |

## Per-source results (2026-11-20)

### FMN (Ontario) — see the FMN section below for the full investigation

| Adapter | Rows tonight | Last verified | Verdict |
|---|---:|---:|---|
| `fmn` | 453 | 453 (Cycle 36) | Unchanged — default view identical in size (353,938 bytes) and shape |

### Ontario direct-HTTP adapters

| Adapter | Rows tonight | Last verified | Verdict |
|---|---:|---:|---|
| `collwest` | 16 | 16 (Cycle 3/5) | Unchanged |
| `mae_mart` | 4 | 4 (Cycle 37) | Unchanged (page + futures proxy) |
| `north_gower` | 15 | — (Cycle 3) | Live; first count recorded |
| `mapleview` | 0 | stub | Unchanged — stub returns its explicit unsupported reason (Grain Discovery JS shell) |

### Ontario Playwright adapters — catalogue URL raw GET (render check still pending)

| Source | URL | HTTP | Evidence tonight |
|---|---|---|---|
| Great Lakes Grain | cashbids.greatlakesgrain.com/index.cfm | 200 | 60,111 B; `CashBid` markers present (42) |
| London Ag Commodities | londonag-dtn.com/index.cfm?show=11 | 200 | 48,181 B; "Cash Bid" + `CashBid` markers present |
| Snobelen Farms | snobelenfarms.com …/dtn/feed.php?commodity=all&location=Brantford | 200 | 10,731 B served (feed endpoint live) |
| Hensall Co-op | hensallco-op.ca/Cash-Bids.htm | 200 | 42,654 B; Cash/Bid markers present |
| DG Global | dgglobal.ca/cash-bids | 200 | 21,037 B served |
| Wanstead | fscooperatives.com/wansteadfarmerscoop/agriculture/cash-bids | 200 | 106,492 B; Cash Bid / DTN markers present |
| Ganaraska Grain | ganaraskagrain.com/cashbidsindex | 200 | 81,568 B; `jsquote` reference present |
| Ingredion (Cardinal) | ag.ingredion.com/cash-bids | 200 | 81,201 B served |
| Bunge (Hamilton) | bungeag.com/locations/hamilton-on/ | **404** | Unchanged — stays dead/disabled |

### AgriCharts `writeBidRow` (US) — all unchanged vs Cycle 36

| Adapter | Rows tonight | Last | | Adapter | Rows tonight | Last |
|---|---:|---:|---|---|---:|---:|
| `ag_plus` | 36 | 36 | | `keller` | 14 | 14 |
| `anthony_farmers_coop` | 9 | 9 | | `kokomo_grain` | 63 | 63 |
| `central_farmers_coop` | 75 | 75 | | `legacy_farmers` | 66 | 66 |
| `farmers_win_coop` | 171 | 171 | | `pro_ag` | 78 | 78 |
| `heritage_grain_cooperative` | 14 | 14 | | `west_con` | 84 | 84 |
| `wheaton_dumont` | 43 | 43 | | `heartland_coop` | 0 | 0 (closed) |
| `mulvane_coop` | 0 | 0 (closed) | | | | |

### AgriCharts cashbids embed — all unchanged vs Cycle 35 except `ag_state`

| Adapter | Rows tonight | Last | | Adapter | Rows tonight | Last |
|---|---:|---:|---|---|---:|---:|
| `agtegra` | 8 | 8 | | `pro_coop` | 6 | 6 |
| `alcivia` | 181 | 181 | | `pro_coop_21302` | 12 | 12 |
| `heritage_coop` | 15 | 15 | | `pro_coop_21302b` | 12 | 12 |
| `hull_coop` | 12 | 12 | | `stateline_coop` | 126 | 126 |
| `linn_coop` | 51 | 51 | | `superior_ag` | 12 | 12 |
| `midway_coop` | 8 | 8 | | `tgm` | 362 | 362 |
| `ag_state` | **21** | 11 | | | | |

### Bushel `.cbmod` — all unchanged vs Cycles 29–37 except `agp`

| Adapter | Rows | | Adapter | Rows | | Adapter | Rows |
|---|---:|---|---|---:|---|---|---:|
| `ace_ethanol` | 11 | | `skyland_2763` | 6 | | `smithfield_hobbsville` | 3 |
| `agp` | **1** (was 8) | | `skyland_2766` | 5 | | `smithfield_jones_county` | 3 |
| `alliance_grain` | 10 | | `skyland_2770` | 5 | | `smithfield_kinston` | 3 |
| `almota` | 12 | | `skyland_2771` | 6 | | `smithfield_kinston_jch` | 3 |
| `cameron_coop` | 4 | | `skyland_2778` | 6 | | `smithfield_lagrange` | 3 |
| `cgs` | 4 | | `skyland_3370` | 6 | | `smithfield_lake_city` | 1 |
| `chandler_feed` | 17 | | `skyland_3621` | 5 | | `smithfield_lapaz` | 2 |
| `fac` | 45 | | `smithfield_bentonville` | 3 | | `smithfield_laurinburg_feed_mill` | 2 |
| `forest_river` | 3 | | `smithfield_bladenboro` | 1 | | `smithfield_morgans_corner` | 2 |
| `lake_norden` | 2 | | `smithfield_bladenboro_feed_mill` | 2 | | `smithfield_morral` | 1 |
| `rugby` | 12 | | `smithfield_chadbourn` | 1 | | `smithfield_mount_olive` | 3 |
| `skyland` | 6 | | `smithfield_chief_feed_mill` | 2 | | `smithfield_nichols` | 1 |
| `skyland_2730` | 6 | | `smithfield_clarkton` | 1 | | `smithfield_petersburg` | 4 |
| `skyland_2731` | 5 | | `smithfield_clinton` | 3 | | `smithfield_red_springs` | 1 |
| `skyland_2734` | 5 | | `smithfield_creswell` | 2 | | `smithfield_walstonburg` | 3 |
| `skyland_2740` | 7 | | `smithfield_darlington` | 1 | | `smithfield_warsaw` | 2 |
| `skyland_2742` | 7 | | `smithfield_deep_run_jch` | 2 | | `smithfield_waverly` | 7 |
| `skyland_2754` | 5 | | `smithfield_hamer` | 1 | | `smithfield_weeksville` | 2 |
| `skyland_2761` | 6 | | `smithfield_harpster` | 1 | | `synergy` | 4 |
| `united_coop` | 12 | | `wheaton_grain` | 5 | | `williams_gin` | 2 |
| `winchester` | 10 | | `winchester_3440` | 5 | | | |

### Other families

| Adapter | Rows tonight | Last verified | Verdict |
|---|---:|---:|---|
| `five_star_coop` (wpDataTables) | 299 | 299 (Cycle 36) | Unchanged |
| `usda_mirror_jvg` | 182 | 197 (Cycle 36) | New daily report; shape unchanged |
| `usda_mirror_fsg` | 182 | 197 (Cycle 36) | Same report as JVG, as before |

### Not probed tonight (by rule or by design)

- `andersons` — parked; the legacy DTN host must not be probed (Cycle 40).
- 13 DTN adapters (`ag_partners`, `al_corn`, `allied_cooperative`,
  `aurora_coop`, `brubaker_grain`, `cfs`, `elite_octane`,
  `frontier_coop`, `green_plains`, `hoffman_ag`, `kanza_coop`,
  `sunrise`, `wilton_farmers_union_elevator`) — all toggled off,
  JS-only; Playwright render checks still pending.
- Greenfield Global (Barchart marketplace) — not fetched;
  Barchart data is parked/out of scope.

## FMN investigation — dropdown-only locations over plain HTTP

Question: the default `cash.php` view carries 204 bid tables /
453 rows, but the Location dropdown lists far more points. Can
the dropdown-only locations (Winchester, Sarnia, Goderich,
Durham, Wellington, Chatham, Kintore, Maxville, …) be reached
with bid data over plain HTTP via `?location_filter=<id>`?

**Answer: no — none of them. Every filtered view is an empty
shell over plain HTTP.** This extends the Cycle 3 finding (which
tested Winchester only) to all eight named towns, at both
location level and commodity level, plus the page's own
`print=true` variant.

### Evidence (2026-11-20, one GET per view)

Default view, re-verified tonight: HTTP 200, 353,938 bytes
(identical size to the Cycle 10 verification), 204
`homepage_quoteboard` tables, 454 `writeBidRow(` occurrences
(453 row calls + 1 function definition), `jsquote.php`
`symbols=` populated with the 10 CBOT/MIAX symbols. The
`locationFilter` select tonight contains **335 named options**
(+ the empty "All Locations" option).

| Filtered view | ID | HTTP | Bytes | Quoteboard tables | `writeBidRow(` occurrences | `jsquote symbols=` |
|---|---|---:|---:|---:|---:|---|
| Winchester (location) | 2523 | 200 | 50,354 | 0 | 1 (definition only) | empty |
| Sarnia (location) | 35807 | 200 | 50,340 | 0 | 1 | empty |
| Goderich (location) | 4426 | 200 | 50,329 | 0 | 1 | empty |
| Durham (location) | 652 | 200 | 50,323 | 0 | 1 | empty |
| Wellington (location) | 84074 | 200 | 50,335 | 0 | 1 | empty |
| Chatham (location) | 24090 | 200 | 50,339 | 0 | 1 | empty |
| Winchester Corn | 1965 | 200 | 50,364 | 0 | 1 | empty |
| Kintore Corn | 4196 | 200 | 50,337 | 0 | 1 | empty |
| Maxville Corn | 3439 | 200 | 50,360 | 0 | 1 | empty |
| Winchester `&print=true` | 2523 | 200 | 29,519 | 0 | 1 | empty |

Notes on the IDs: Kintore and Maxville have **no location-level
dropdown option at all** — only commodity options (Kintore Corn
4196 / Kintore Soybeans 4206; Maxville Corn 3439 / Maxville
Soybeans 3440). Sarnia has four duplicate location-level options
(35807/35809/35810/35811, all labelled "Sarnia"); 35807 was
probed. The parameter **is** accepted: on the Winchester view
the returned HTML marks `<option selected value="2523">Winchester`
(the Cycle 3 "selected" check missed this because the attribute
order is `selected` before `value`). The filtered HTML contains
no `var bids` JSON, no `.cbmod` widget, and no other static data
endpoint — the ~50 KB is page chrome plus the bid-table
scaffolding and the `writeBidRow` function definition.

### Conclusion

- Over plain HTTP, **zero** dropdown-only FMN locations are
  reachable with bid data. The filtered rows are rendered
  client-side (or not at all) — the static HTML gives no route
  to them, and no additional endpoint is discoverable from the
  filtered page's own markup.
- The FMN collector's coverage therefore stays exactly what it
  is: the default view's 453 rows / 87 delivery points.
- The only remaining route to the other ~248 dropdown points is
  the already-open **Playwright render check** of
  `cash.php?location_filter=2523` (browser work, not possible in
  this sandbox). Until that check shows rows rendering, do not
  build a 335-location sweep.

## Adapter fixes

None. No page changed shape, so per the phase rules nothing was
changed on suspicion: every parser that was live at last check
still parses its live page tonight, proven by the row counts
above plus the 197 passing fixture tests.
