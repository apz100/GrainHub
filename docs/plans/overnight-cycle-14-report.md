# Overnight Cycle 14 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-14` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 14 complete — Skyland picker sweep finished (all
14 IDs), Smithfield batch 1669–1674, Andersons bundle read confirms
browser-only, Chadbourn still stale.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `94defb7` | Skyland sweep complete (7 IDs); Smithfield batch 1669–1674; Andersons bundle confirms browser-only; Chadbourn still stale |
| *(this commit)* | Cycle 14 report |

## 2. Test results

- **Full API suite: 617 passed, 0 failed** (Cycle 13 ended at 590).
  New tests in Cycle 14: Skyland 21, Smithfield 6 = **27 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 13).

## 3. What was built (done)

### Skyland picker sweep — COMPLETE (7 GETs, all 14 picker IDs now verified)
- 2763 Satanta–Ryus 6 rows (Corn 2, Milo 1, Red Wheat 2, White
  Wheat 1); 2766 Spearman–Gruver–Texline 5; 2770 Sunray Area 5;
  2771 Kendall–Midway–Lydia 6; 2778 Buckeye–Syracuse 6;
  3370 Hugoton, KS 6 (Corn 2, **Milo 2** — first Skyland page with
  two Milo rows — Red Wheat 2; h2 carries ", KS", mapped via
  `location_labels` as with Smithfield's ", NC"); 3621 Vilas–Walsh
  5. **39 rows total.** All static `.cbmod` widgets, parsed by the
  existing generic parser, no changes.
- **Staleness watch:** 3370 and 3621 widget headers dated Nov 18,
  2026 (a day older than the other five, Nov 19) — same pattern as
  Chadbourn in Cycle 13, flagged in the catalogue.
- 7 registry entries + `fetch_skyland_<ID>()` wrappers,
  `config.toml` toggles, 7 new enabled toml entries, registry
  adapters wired by the coordinator, 21 new tests with synthetic
  fixtures. Skyland is now fully swept — no picker IDs remain
  unverified. The coordinator independently verified all 7 against
  the saved HTML — row counts and locations match exactly.

### Smithfield East Region batch — 1669–1674 (6 GETs)
- The list page was **not** re-fetched: the saved Cycle 11 page
  (`/tmp/cycle11/smithfield_fccp.html`, 31 IDs) still exists, so
  all 6 GETs went to per-location targets. All HTTP 200, standard
  wrapped 7-col `.cbmod` widgets, widget headers all dated
  Thursday, November 19, 2026, parsed by the existing parser, no
  changes.
- 1669 Clinton 3 rows (Corn 1, Soybeans 1, Wheat 1); 1670
  Hobbsville 3; 1671 Kinston 3; 1672 LaGrange 3; 1673 Morgans
  Corner 2 (Soybeans 1, Wheat 1 — no Corn; live h2 has **no
  apostrophe**); 1674 Mount Olive 3. **17 rows total.**
- Revision of a Cycle 13 expectation: five of six pages carry a
  full 3 rows — the 1-row pages (Bladenboro/Chadbourn/Clarkton)
  are the exception, not the rule.
- 6 registry entries + `fetch_smithfield_*()` wrappers,
  `config.toml` toggles, 6 new enabled toml entries, registry
  adapters wired by the coordinator, 6 new tests with synthetic
  fixtures. Smithfield now 11 of 31 locations verified; **20 East
  Region locations still open** (1675, 1676, 1678, 1679, 1681–1691,
  2064–2067, 2179). Next numeric batch: 1675 Raeford, 1676 Red
  Springs, 1678 Walstonburg, 1679 Weeksville, 1681 The Chief Feed
  Mill, 1682 Laurinburg Feed Mill. Note 2064 is a second Kinston
  target (JCH — Kinston Elevator), distinct from 1671.
- The coordinator independently verified all 6 against the saved
  HTML — row counts and locations match exactly.

### The Andersons — bundle read (1 GET) — CONFIRMED BROWSER-ONLY
- `GET https://www.andersonsgrain.com/bundles/js/my-cash-bids?v=C0G6bVc73LyEBcO1OYpPFy7jWEA7shnNPkHnIdQ0d7o1`
  → HTTP 200, **1,079 bytes**. A Browserify wrapper defining
  exactly one module (83); the picker logic is fully contained
  there. On location change it reads the inline global
  `ANDERSONS_GRAIN_LOCATIONS` and populates the commodity
  `<select>` (verbatim strings:
  `(ANDERSONS_GRAIN_LOCATIONS||{})[f]||[]`,
  `'<option value="">All Commodities<\/option>'`,
  `t.append("<option>"+r[n]+"<\/option>")`).
- **No network call of any kind:** grep for `fetch(`,
  `XMLHttpRequest`, `$.ajax`, `axios`, `getJSON`, `.post(`, `.get(`,
  `/api/`, `.json`, `http` returns nothing except the single
  identifier `ANDERSONS_GRAIN_LOCATIONS`. No POST target in the
  bundle (`/locations/cash-bids/Add` is known only from the saved
  Cycle 11 HTML); no token/CSRF handling, no secrets (0 matches).
- **Conclusion:** confirmed browser-only — form POST + server
  render, possibly account-bound (page links
  `/login?returnUrl=%2flocations%2fcash-bids%2f`). No static-data
  route and no public API exist. No collector built, correctly.
  The coordinator independently verified the bundle (1,079 bytes,
  zero network-call strings).
- **Precise next probe (one GET, later cycle):**
  `https://www.andersonsgrain.com/local-bids/locations-list/` —
  it may list per-location pages with static bids. If that is also
  a picker/links page with no static bids, the Andersons is closed
  for static collection and only a rendered browser session
  remains.

### Chadbourn re-check (1 GET) — STILL STALE
- `GET https://www.smithfieldgrain.com/cashbidssingle-2294` →
  HTTP 200, 80,256 bytes. Widget header still **"Cash bids for
  Wednesday, November 18, 2026"** — a full day behind on Nov 19,
  while every other Cycle 13/14 Smithfield page was Nov 19. Still
  **1 row: Soybeans** (standard wrapped `.cbmod` shape, Last Trade
  12:23 AM). Structure and count unchanged; no parser issue. This
  is a stale widget, not a slow refresh. Collector flag recorded:
  a same-day freshness check would fail this location daily, so
  Chadbourn would need an exemption/lag tolerance if a freshness
  gate is ever added. The coordinator independently confirmed the
  Nov 18 header in the saved HTML.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 14 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (3 sites: Frontier, CRC, UFC), and now
  The Andersons GRAINweb (bundle verdict: browser-only; the
  locations-list probe is the last static chance).
- Remaining Smithfield East Region locations (20 of 31); Chadbourn
  + Skyland 3370/3621 staleness watch.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–13: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons).

**New in Cycle 14:** nothing new needs Adam.
