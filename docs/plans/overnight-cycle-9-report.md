# Overnight Cycle 9 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-9` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 9 complete — Cycle 8 follow-ups closed: Five Star
wpDataTables collector, ALCIVIA + TGM cashbids embeds proven, CRC
resolved.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `0b35f18` | Five Star wpDataTables collector (299 rows); ALCIVIA + TGM cashbids embeds proven (543 rows); CRC resolved as StoneX-only |
| *(this commit)* | Cycle 9 report |

## 2. Test results

- **Full API suite: 454 passed, 0 failed** (Cycle 8 ended at 407).
  New tests in Cycle 9: wpDataTables collector 43, cashbids embed
  +4 = **47 new tests**.
- Web build was not re-run in Cycle 9 (no web files changed).

## 3. What was built (done)

### Five Star Coop wpDataTables collector — new pattern
- **Verified live with one polite GET:** the page serves a
  server-rendered wpDataTables table (`table_1`); parsed against
  the saved Cycle 8 HTML it yields **299 rows — Corn 197 +
  Soybeans 102, 21 locations, date 2026-11-18** — matching Cycle 8
  exactly.
- New generic collector `wpdatatables_source.py`
  (`fetch_five_star_coop()`, `WPDATATABLES_SITES` registry) with
  43 tests and synthetic fixtures. It selects only the table whose
  header contains both "Location" and "Bids" (preferring
  `id="table_1"`); Tables 2–4 are DTN futures and are never parsed
  as bids. Header-driven column map (Location / Commodity /
  Delivery Periods / Bids / Basis / Change / TradeDateTime); six
  hidden bookkeeping columns ignored. Locations kept verbatim,
  including third-party delivery points (AGP Mason City, Valero
  Charles City, Shell Rock Soy Processing). Repeated header row at
  the end of `<tbody>` and all-money-blank rows skipped; a row with
  bid/basis blank but change present is kept with a note. Units as
  published (Bids/Basis $/bu; Change in cents). Fractional CBOT
  notation (`433-2` → 433.25) handled for robustness. Every row
  carries `source: "five_star_coop"` and `date`; no price invented.
- **Delivery-label normalisation** (to `%b %Y`, documented in the
  module docstring): `Nov26`/`Nov 26` → Nov 2026, `Dec26` → Dec
  2026, `Dec27`/`Dec 27` → Dec 2027, `Jan27` → Jan 2027, `Feb 27`
  → Feb 2027, `Mar 27` → Mar 2027, `Apr 27`/`April 27` → Apr 2027,
  `May 27` → May 2027, `June 27` → Jun 2027, `July 27` → Jul 2027,
  `Oct 27.` → Oct 2027. Unknown labels are kept verbatim and
  flagged in `notes`, never dropped or guessed.
- Wired in: `source_registry.py` adapter, `config.toml` toggle
  (`five_star_coop = true`), `us_elevators_urls.toml`
  reclassified `dtn → wpdatatables`, enabled. Catalogue updated
  (Cycle 9 resolution note; follow-up bullet marked done).

### ALCIVIA + TGM cashbids embeds — static route proven
- One polite GET each of the loader-derived `cashbids-js.php`
  URLs (verbatim, as in Cycle 7). Derivation note: the saved Cycle
  8 page loader `src` contains literal newlines inside `fields=`,
  encoded as `%0A` per the Cycle 7 Agtegra precedent, appending
  only `&&acCnt=1` — verified against the four saved Cycle 7
  loader JS files, which show the loader appends exactly
  `&acCnt=<n>` to a widgetURL ending in `&` (no `noscript=1`
  added; that param in Agtegra's URL came from its own page's src
  query, which ALCIVIA/TGM don't have).
- **ALCIVIA: 200, `var bids` JSON, 181 rows across 15 Wisconsin
  locations** (Corn 90, Soybeans 75, Wheat 16), all rows complete,
  0 login-gated, 0 inactive. `groupby=location`, `months=11`.
- **TGM: 200, `var bids` JSON, 362 rows across 24 Illinois/Indiana
  locations** (Corn 120, Beans→Soybeans 120, Wheat 120, White Corn
  2), all complete, 0 skipped. `groupby=ccommodity` (groups are
  commodity-named, row location from `location_name`, as with Ag
  State/Superior); TGM labels soybeans "Beans" — all 120 carry ZS
  symbols, so `"beans" → "Soybeans"` was added to `COMMODITY_MAP`;
  "White Corn" (ZC symbols) kept as published. TGM's Barchart
  marketplace link was not fetched (out of scope).
- `fetch_alcivia()` / `fetch_tgm()` added to
  `cashbids_embed_source.py` (registry now 8 verified sites, js
  URLs byte-identical to the URLs fetched and verified); 4 new
  tests with synthetic fixtures (invented values only). Wired in:
  `source_registry.py` adapters, `config.toml` toggles
  (`alcivia = true`, `tgm = true`), `us_elevators_urls.toml`
  reclassified `unknown → agricharts-embed`, enabled; TGM's URL
  updated to the verified `/Cash-Bids` page. Catalogue updated
  (Cycle 9 resolution notes in both per-site tables; follow-up
  bullets marked done). Raw fetched responses in `/tmp/cycle9/`
  scratch only, never the repo.

### CRC — resolved, no collector
- One GET of the homepage (200). Correction to Cycle 8: the anchor
  is actually `/home/#cash-bids-futures`, not `#cash-bids`. The
  Cash Bids section holds a **lazy-loaded StoneX component iframe**
  (no static `src`, nothing loads statically) plus a DTN
  preconnect — **no static bid rows anywhere on the homepage**. No
  collector added. The StoneX iframe is the only open route (same
  family as Frontier Coop; a render check in a later cycle). The
  iframe's keyed URL was deliberately not copied into any doc.
  Catalogue updated with the Cycle 9 note.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 9 code, tests, fixtures, or docs
(verified by grep on the new/changed lines). The company appears
only as one ordinary price source in pre-existing catalogue/config
text, per the boundary. No contact made.

## 5. What is still scaffold / stub

- Playwright render checks for the DTN-family JS-only sites (now
  including Ag Partners and Gateway FS), plus FMN filtered view
  and Mapleview. StoneX is now a 2-site family (Frontier Coop +
  CRC) with no static-data route — render check is the only path,
  and the runtime API may be auth-gated.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope — this cycle it was accidentally staged by
  `git add -A` and the push was rejected for exactly that reason;
  the commit was redone without it and the file remains untracked
  locally). Currency still not stored on normalized price rows.

## 6. Blocked / needs Adam

Carried from Cycles 1–8: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX).

**New in Cycle 9:** nothing new needs Adam. All Cycle 8
follow-ups are now closed except the Playwright render checks.
