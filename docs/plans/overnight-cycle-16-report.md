# Overnight Cycle 16 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-16` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 16 complete — Smithfield East Region sweep
finished (30 of 31 locations; Raeford posts no public bids),
Andersons fully closed on licensing grounds, merge plan extended
to Cycles 13–15.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `58679eb` | Smithfield sweep complete (30 of 31; Raeford posts no bids); Andersons closed on licensing (Maumee tables are Barchart data); merge plan extended to Cycle 15 |
| *(this commit)* | Cycle 16 report |

## 2. Test results

- **Full API suite: 638 passed, 0 failed** (Cycle 15 ended at 629).
  New tests in Cycle 16: batch 5 (6) + loose ends (3) = **9 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 13).

## 3. What was built (done)

### Smithfield East Region batch 5 — 1689–1691, 2064–2066 (6 GETs)
- 1689 Nichols, SC 1 row (Soybeans); 1690 Petersburg, VA 4 (Corn
  1, Wheat 1, Soybeans 2); 1691 Waverly, VA 7 (Corn 3, Wheat 2,
  Grain Sorghum 2); 2064 Kinston JCH, NC 3 (Corn 1, Wheat 1,
  Soybeans 1); 2065 Jones County, NC 3; 2066 Deep Run JCH, NC 2
  (Corn 1, Wheat 1). **20 rows total.** All HTTP 200, standard
  wrapped 7-col `.cbmod` widgets, headers all dated Thursday,
  November 19, 2026 — fresh. No empty widgets, no staleness.
- **Waverly (1691) is the fattest Smithfield page yet (7 rows)**
  and the first Smithfield page to carry **Grain Sorghum** (widget
  publishes the block as "Sorghum"; the parser already normalizes
  it to "Grain Sorghum").
- **2064 is a genuine second Kinston target**, distinct from
  `smithfield_kinston` (1671): live h2 "Kinston JCH, NC" mapped
  to "Kinston JCH". Same treatment for Deep Run ("Deep Run JCH").
- 6 registry entries + `fetch_smithfield_*()` wrappers,
  `config.toml` toggles, 6 new enabled toml entries, registry
  adapters wired by the coordinator, 6 new tests with synthetic
  fixtures.

### Smithfield loose ends — Raeford re-probe, 2067, 2179 (3 GETs)
- **Raeford 1675 — re-probe: STILL EMPTY, not registered.**
  HTTP 200, generic site shell with an empty `.cbmod` widget (1
  `cbmod` marker, 0 `cbCommodity`, 0 `sevenColumnsBigFirst`), no
  location h2, no header date, 0 rows, parser status `"empty"` —
  identical shape to Cycle 15. Second empty probe in a row.
  Treated as a location that posts no public bids; no further
  re-probe planned. The Raeford comment in `bushel_source.py`
  records this; no registry entry, toggle, or toml entry.
- **2067 Lapaz Elevator, IN: VERIFIED and registered.** HTTP 200,
  standard wrapped 7-col `.cbmod` widget, **2 rows, both Corn**,
  h2 "Lapaz, IN" → "Lapaz". Header Thursday, November 19, 2026
  (fresh).
- **2179 Hamer Elevator, SC: VERIFIED and registered.** HTTP 200,
  same widget shape, **1 row, Soybeans**, h2 "Hamer, SC" →
  "Hamer". Header **Wednesday, November 18, 2026 — a day stale,
  like Chadbourn** (Cycle 13); a data-freshness flag for the
  collector, not a parser issue.
- 2 registry entries + `fetch_smithfield_*()` wrappers,
  `config.toml` toggles, 2 new enabled toml entries, registry
  adapters wired by the coordinator, 3 new tests (Lapaz + Hamer
  parse/registry; Raeford negative — unknown key raises
  `KeyError`, empty-widget shape parses to status `"empty"`).
- The coordinator independently verified all 9 Smithfield targets
  against the saved HTML — row counts, locations, and the Raeford
  empty widget match exactly.

### Smithfield East Region — SWEEP COMPLETE
- **30 of 31 locations verified and registered** (the 31-location
  list from the saved Cycle 11 page is now fully covered except
  Raeford, which posts no public bids). Skyland is likewise
  complete (all 14 IDs). The per-location Bushel sweep programme
  that began in Cycle 10 is done.

### The Andersons — confirmatory checks (2 GETs) — FULLY CLOSED
- **Maumee facility page — the surprise.** `GET
  https://www.andersonsgrain.com/locations/oh/maumee/` → HTTP
  200, **34,992 bytes**. Expected "info only" — wrong. The page
  has facility info (Hours, Discount Schedules, Important Info,
  DP/Storage Rates, Contacts, About This Facility, Google Maps
  embed) **plus 3 static `styled-table` bid tables** under a "Cash
  Bids" tab ("Corn, Beans, Red Wheat"), columns Delivery / Bid /
  Basis / Futures / Chg / Symbol / Last Trade: Corn 10 delivery
  rows, Soybeans 10, Red Wheat 3 (**23 rows total**). The "Bid and
  Basis Charts" section itself is JS-driven (empty-src
  `chartFrame` iframe), but the tables are plain static HTML.
  **However, the page carries a Barchart disclaimer ("All market
  data is provided by Barchart Solutions") — the tables are
  Barchart-licensed data, so they are deliberately NOT collected,
  NOT registered, no toml entry.** Do not probe the other 40
  facility pages — the answer is already known and the data is out
  of scope.
- **Ohio per-state list — expectation confirmed.** `GET
  https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/`
  → HTTP 200, **28,666 bytes**. Same directory substance as the
  master list page (Cycle 15): the same 7 Ohio facilities in 3
  small layout tables, plus the full 41-facility directory in nav
  links. 0 bid tables, 0 price-like strings. No bids.
- **Verdict:** the Andersons is fully closed. The closure now
  rests on licensing rather than absence of static rows: the
  facility tables are Barchart-licensed (out of scope), the picker
  is a JS form POST (possibly account-bound), and the list pages
  are directories. **No new probe exists.**
- The coordinator independently verified the Maumee page (34,992
  bytes, 3 styled-table tables, Barchart Solutions disclaimer
  present) and the Ohio list (28,666 bytes, 3 layout tables).

### Merge plan extended to Cycles 13–15
- New "Cycles 13–15 (added Cycle 16)" section, verified from git
  history and the cycle reports (coordinator spot-checks: chain
  `master..cycle-15` = **49 commits**, 0 merges; tips 13
  `6acc8e2`, 14 `d196b2a`, 15 `7f8c263`; per-branch 2 commits
  each; test chain 590 → 617 → 629; Alembic head still `0019`; CI
  workflow file still untracked). Structure mirrors the Cycles
  8–12 section; §§0–7 and the 8–12 section untouched except one
  stale statement fixed in place (§5b: the deployment-checklist
  §8 sign-off line was already corrected to `0019` in Cycle 13).
- Note: the merge-plan worker found `bushel_source.py` was touched
  in Cycle 13 too, not just 14–15 as the brief said — recorded in
  the new section.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 16 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit; the merge-plan
file's single occurrence is the pre-existing §3.4 reference). No
contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (3 sites: Frontier, CRC, UFC), and The
  Andersons GRAINweb (closed for static collection — only a
  rendered browser session remains, and the facility tables are
  Barchart-licensed).
- Staleness watch: Chadbourn (Nov 18), Hamer (Nov 18), Skyland
  3370/3621 (Nov 18) — all need an exemption/lag tolerance if a
  freshness gate is ever added.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–15: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons).

**New in Cycle 16:** nothing new needs Adam.
