# Overnight Cycle 15 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-15` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 15 complete — Smithfield batches A + B (11
locations verified, 1 empty widget), Andersons locations-list
probe closes the Andersons for static collection, super-plan §9
extended to Cycle 14.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `7b9d69d` | Smithfield batches A+B (11 locations); Raeford empty widget; Andersons locations-list is a pure directory — closed for static collection |
| *(this commit)* | Cycle 15 report |

## 2. Test results

- **Full API suite: 629 passed, 0 failed** (Cycle 14 ended at 617).
  New tests in Cycle 15: batch A 6, batch B 6 = **12 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 13).

## 3. What was built (done)

### Smithfield East Region batch A — 1675–1682 (6 GETs)
- 1676 Red Springs 1 row (Soybeans); 1678 Walstonburg 3 (Corn,
  Soybeans, Wheat); 1679 Weeksville 2 (Soybeans, Wheat); 1681 The
  Chief Feed Mill 2 (Corn, Wheat); 1682 Laurinburg Feed Mill 2
  (Corn, Wheat). All HTTP 200, standard wrapped 7-col `.cbmod`
  widgets, headers all dated Thursday, November 19, 2026 — no
  staleness. **10 rows total.**
- **1675 Raeford is the first Smithfield target to serve an empty
  widget** — HTTP 200 with the generic site shell and an empty
  `.cbmod` div, no location h2, no "Raeford" text, no header date,
  0 rows, status "empty". **Not registered** anywhere; a negative
  test guards that. Needs a re-probe in a later cycle (may be a
  temporarily empty feed).
- **1681's live h2 is "Rose Hill, NC"**, not the list name — the
  mill's town. Registry maps it to "Rose Hill" (key
  `smithfield_chief_feed_mill`, default_location "Rose Hill"),
  with the mismatch recorded. 1682's h2 is "Laurinburg Feed Mill,
  NC", mapped to "Laurinburg Feed Mill" (Bladenboro Feed Mill
  precedent).
- 5 registry entries + `fetch_smithfield_*()` wrappers,
  `config.toml` toggles, 5 new enabled toml entries, registry
  adapters wired by the coordinator, 6 new tests (5 per location +
  1 Raeford negative) with synthetic fixtures.

### Smithfield East Region batch B — 1683–1688 (6 GETs)
- 1683 Creswell 2 rows (Corn 2; list page calls it Creswell Feed
  Mill); 1684 Warsaw 2 (Corn 1, Wheat 1); 1685 Harpster 1 (Corn
  1 — h2 is bare "Harpster", no state suffix, the first Smithfield
  h2 without one); 1686 Morral, OH 1 (Soybeans 1); 1687
  Darlington, SC 1 (Soybeans 1); 1688 Lake City, SC 1 (Soybeans
  1). All HTTP 200, standard wrapped 7-col `.cbmod` widgets,
  headers all dated Thursday, November 19, 2026 — fresh, no
  Chadbourn-style staleness. **8 rows total.**
- 1685–1688 are the first verified Smithfield targets outside NC
  (OH, SC). Row-count expectation revised again: only
  Creswell/Warsaw carry 2 rows; four of six are thin 1-row pages —
  row count is per-location, not a family trait.
- 6 registry entries + `fetch_smithfield_*()` wrappers,
  `config.toml` toggles, 6 new enabled toml entries, registry
  adapters wired by the coordinator, 6 new tests with synthetic
  fixtures.
- The coordinator independently verified all 12 Smithfield targets
  against the saved HTML — row counts, locations, and the Raeford
  empty widget match exactly.

### Smithfield status after Cycle 15
- **22 of 31 locations verified** (11 from Cycles 11–14, 11 this
  cycle). **8 locations still open** (1689, 1690, 1691, 2064,
  2065, 2066, 2067, 2179) plus the Raeford re-probe. Next batch:
  1689, 1690, 1691, 2064, 2065, 2066. Note 2064 is a second
  Kinston target (JCH — Kinston Elevator), distinct from 1671.

### The Andersons — locations-list probe (1 GET) — CLOSED for static collection
- `GET https://www.andersonsgrain.com/local-bids/locations-list/`
  → HTTP 200, **27,082 bytes**. A plain per-location directory —
  **not** a picker and **not** a login wall. Title: "Locations
  List - The Andersons Trade Group". Heading: "Please choose a
  Grain Facilities state", then one collapsible group per
  state/province listing facility names as links. The full body
  serves anonymously (a Login link exists in the nav but nothing
  requires signing in).
- **No static bid rows of any kind:** 0 `<table>` elements, 0
  `<form>` elements, 0 occurrences of `writeBidRow`, `.cbmod`, or
  `cashbids.php`, and no price-like strings anywhere. No
  `my-cash-bids` reference and no `ANDERSONS_GRAIN_LOCATIONS`
  global on this page. The only bid-related links point back to
  the already-probed GRAINweb picker (`/locations/cash-bids/`,
  Cycle 11) and `/local-bids/locations/` (Locations Map).
- **41 per-location link targets** (verbatim URLs + names only):
  Idaho 8, Illinois 1, Indiana 4, Iowa 1, Louisiana 5, Michigan
  8, Nebraska 3, Ohio 7, Texas 1, Canada 3 — all under
  `/locations/<state>/<slug>/`. Plus 10 per-state list links,
  a Trading Offices link, and the Locations Map link. Full list is
  in the catalogue section.
- **Credential-like string:** the `<html>` tag carries a
  `data-google-api-key` attribute. Its value is **not reproduced**
  anywhere in the catalogue, this report, or the repo, per the
  no-secrets rule.
- **Verdict:** the last static chance named in Cycle 14 is spent.
  No static-bid page exists anywhere in its link tree. **Only a
  rendered browser session remains** — one that picks a location,
  submits the form, and reads the server-rendered saved bids
  (possibly account-bound).
- Low-odds confirmatory checks named for a later cycle (1 GET
  each, **not fetched**): `https://www.andersonsgrain.com/locations/oh/maumee/`
  (representative facility page — expected: info only) and
  `https://www.andersonsgrain.com/local-bids/locations-list/location-list/ohio/`
  (per-state list — expected: same directory markup, no bids).
- The coordinator independently verified the saved page: 27,082
  bytes, 0 tables, 0 bid strings, title matches, 46 `/locations/`
  links.

### Super-plan §9 extended to Cycle 14
- Heading/intro now cover Cycles 1–14 (test chain 179 → 617);
  Cycle 13 + 14 bullets added; blockers updated (embed family 13
  sites, Skyland sweep complete, Smithfield 11 of 31 at the time
  of writing — 22 after this cycle, Andersons confirmed
  browser-only).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 15 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (incl. Sunrise, Ray
  Carroll), FMN filtered view (Winchester `location_filter=2523`),
  Mapleview, StoneX family (3 sites: Frontier, CRC, UFC), and now
  The Andersons GRAINweb (closed for static collection — only a
  rendered browser session remains).
- Remaining Smithfield East Region locations (8 of 31) + Raeford
  re-probe; Chadbourn + Skyland 3370/3621 staleness watch.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–14: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision (four
concrete choices in `docs/plans/currency-design.md`), email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons).

**New in Cycle 15:** nothing new needs Adam.
