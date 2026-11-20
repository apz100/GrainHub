# Overnight Cycle 21 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-21` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 21 complete — 11 of 13 agricharts wrappers
verified live (642 rows); Heartland + Mulvane fail site-side
(same cause); merge plan extended to Cycle 20, super-plan §9
extended to Cycle 20.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `38bf6d5` | 11 of 13 agricharts wrappers verified live (642 rows); Heartland + Mulvane fail site-side; merge plan extended to Cycle 20 |
| *(this commit)* | Cycle 21 report |

## 2. Test results

- **Full API suite: 692 passed, 0 failed** (unchanged from Cycle 20
  — no code changed in this cycle, so no new tests).
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Live verification of the 13 agricharts wrappers (13 GETs, 1 per wrapper)
- **Batch A (7):** Ag Plus 36 rows (Corn 12, Beans 12, Wheat 12;
  6 locations: Churubusco, Edgerton, Garrett, Monroeville, Raber,
  South Whitley); Farmers Win Coop 171 (Corn 90, Soybeans 81; 18
  locations); Keller 14 (Corn 7, Soybeans 7; 1 location); Kokomo
  Grain 63 (Corn 29, Soybeans 24, Wheat 5, NGMO Waxy 5; 8
  locations); Legacy Farmers 66 (Beans 25, Corn 24, Wheat 17; 10
  locations). **353 rows.**
- **Batch B (6):** Pro Ag 78 (Soybeans 35, Corn 31, Wheat 12; 6
  locations — identical count/locations to Cycle 11); West-Con 84
  (Soybeans 44, Corn 30, DNS Wheat 10; 1 fallback location —
  page has no `<h4>` headings — identical count to Cycles 11–12,
  month-name deliveries kept verbatim); Wheaton Dumont 43 (Corn
  18, Soybeans 16, Spring Wheat 9; 8 locations — identical count
  to Cycle 12, short month labels kept verbatim); Central Farmers
  Coop 75 (Corn 44, Soybeans 30, Winter Wheat 1; 11 locations —
  first live verification, was Cycle 1 HTML only); Anthony Farmers
  Co-op 9 (Corn 3, Milo 3, Soybeans 3; 3 locations — first live
  verification; thin but structurally sound, 3 locs × 3
  commodities, single delivery 09/01/2026). **289 rows.**
- **Combined: 11 of 13 wrappers return rows, 642 rows total.** All
  returning wrappers produced the standard 10-column DataFrame. No
  wrapper bugs were found, so no code was changed.
- **Two site-side failures (same cause):** Heartland Coop and
  Mulvane Coop both return 0 rows — HTTP 200, but the page no
  longer carries the `jsquote.php` script tag the generic parser
  requires, so `fetch_us_agricharts` returns empty before parsing.
  Wrapper URLs/names verified correct against the toml and Cycle 1
  discovery. Needs a re-probe in a later cycle (1 GET each); a
  future generic-collector fix (alternate futures source) would
  cover both. Two of 13 sites failing the same way suggests
  AgriCharts may be rolling out a template change.
- **Heritage Grain Cooperative — partial (3 rows):** rows parse,
  but `Location` values are the commodity names ("CORN - CASH"
  etc.) because the page's `<h4>` tags are commodity headings, not
  location names — the generic parser's h4-as-location assumption
  mislabels them. Open follow-up: does the page genuinely list
  only 3 cash bids, or are more rows in a shape the `writeBidRow`
  regex skips? A parser-level fix (detect h4-as-commodity pages)
  is a later-cycle item.
- **User-Agent discrepancy (noted, not changed):** the task brief
  said the fetch functions send `GrainHub-Research/1.0`, but
  `_HEADERS` in `us_agricharts_source.py` actually sends a Chrome
  `Mozilla/5.0` UA. Wrappers were run as-is with no override. The
  coordinator independently confirmed the Chrome UA in the source
  (pre-existing from Cycle 1). Changing the UA is a deliberate
  decision for a later cycle, not something altered here.

### Merge plan extended to Cycle 20
- New "Cycle 20 (added Cycle 21)" section, verified from git
  history and the cycle report (coordinator spot-checks: chain
  `master..cycle-20` = **59 commits**, 0 merges; tip `9329169`;
  Cycle 20 added 2 commits; test count 692; Alembic head still
  `0019`; CI workflow file still untracked). 227 lines added, 0
  removed. The Cycle 19 section's "57 commits" figure re-verified
  correct. Overlaps recorded: `source_orchestration.py` touched in
  both Cycle 19 and 20 — sequential merge must carry both the
  allowlist removal and the toggle gating.

### Super-plan §9 extended to Cycle 20
- Heading/intro now cover Cycles 1–20 (test chain 179 → 692);
  Cycle 20 bullet added; blockers updated (registry 119 adapters,
  DTN toggles off awaiting Playwright).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 21 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland + Mulvane re-probes (1 GET each); Heritage h4-as-commodity
  parser question; agricharts UA decision (Chrome UA vs
  GrainHub-Research/1.0).
- Staleness watch: Chadbourn (Nov 18), Hamer (Nov 18), Skyland
  3370/3621 (Nov 18).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–20: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 21:** nothing new needs Adam.
