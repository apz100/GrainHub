# Overnight Cycle 22 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-22` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 22 complete — Heritage parser fix (escaped
quotes, 14/14 rows), Heartland + Mulvane still failing on re-probe,
staleness watch unchanged (all four still one day behind), merge
plan extended to Cycle 21, super-plan §9 extended to Cycle 21.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `f250e8c` | Heritage parser fix (escaped quotes, 14/14 rows); Heartland + Mulvane still failing; staleness watch unchanged; merge plan extended to Cycle 21 |
| *(this commit)* | Cycle 22 report |

## 2. Test results

- **Full API suite: 696 passed, 0 failed** (Cycle 21 ended at 692).
  New tests in Cycle 22: Heritage parser 4 = **4 new tests**.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Heritage Grain Cooperative — page lists 14 bids, not 3; parser bug fixed
- Direct fetch of `https://www.heritagegrain.com/markets/cash.php`
  (URL from the toml), HTTP 200, 64,855 bytes. Verbatim reading
  shows **14 `writeBidRow` data calls**, not 3: the 3 cash rows
  Cycle 21 parsed plus 11 forward-month rows (CORN/BEANS DEC 2026,
  JAN/FEB/MAR 2027, FALL 2027; WHEAT JUL 2027). All deliveries are
  full MM/DD/YYYY. No other bid shape exists on the page.
- **Why 11 were skipped:** forward-month rows carry the delivery
  label in the notes argument with an escaped quote — `'DEC \'26'`,
  `'JAN \'27'`, `'FALL \'27'`, `'JUL \'27'` — and the regex's
  group/notes fields were `'[^']*'`, which stops at the escaped
  quote and fails the whole row. The `jsquote.php` tag is present
  and lists all 8 symbols the 14 rows reference.
- **Yes, the `<h4>` tags are commodity headings:** all 14, each
  exactly equal to the row name beneath it, in document order.
- **Parser fix (generic collector, not the wrapper):** group (arg
  9) and notes (arg 10) fields in `_WRITEBIDROW_RX` changed from
  `'[^']*'` to `'(?:[^'\\]|\\.)*'` — escaped quotes no longer break
  the match. Verified offline against the saved capture: 14/14
  rows match (was 3/14). New `_is_commodity_heading(h4_text,
  row_name)`: true when the `<h4>` exactly equals the row's
  commodity name (case-insensitive) or starts with a commodity
  word; such rows fall back to the company name as location (same
  `Company - Company` shape West-Con already produces).
  Word-boundary check keeps real place names out (`Wheatland`,
  `Cornwall` tested). Verified end-to-end with mocked futures
  against the saved capture: 14 rows, single location `Heritage
  Grain Cooperative - Heritage Grain Cooperative`.
- 4 new tests (escaped-quote regex parsing,
  `_is_commodity_heading` unit cases, mocked-HTTP end-to-end
  fallback with a genuine `Riverside` heading still used, and a
  structure-only saved-HTML test that skips if the capture is
  absent) plus a synthetic fixture (all values invented, neutral
  `Test Elevator` naming).
- The coordinator independently verified the fix against the saved
  capture: 14 matches (was 3), `jsquote.php` tag present.
- No live re-call of the Heritage wrapper after the fix — the
  3-GET budget was spent; verification is via the saved capture +
  synthetic fixtures. **Next live wrapper call should return 14
  rows (1 GET, later cycle).**

### Heartland + Mulvane re-probes — still failing (2 GETs)
- `fetch_heartland_coop()` live: 0 rows, `[US-AG WARN] Heartland
  Coop: jsquote script tag not found in page`. Same failure as
  Cycle 21 — second consecutive failure, so not transient. Wrapper
  unchanged.
- `fetch_mulvane_coop()` live: 0 rows, same missing-`jsquote.php`-
  tag warning. Second consecutive failure. Wrapper unchanged.
- Recommendation from the worker (recorded, not acted on): two
  consecutive 0-row probes each — either a generic-collector
  alternate futures source (covers both at once, as Cycle 21
  anticipated) or flip both toggles to `false`. Do not re-probe
  them every cycle without a fix plan.

### Staleness re-checks — watch UNCHANGED (4 GETs)
- Smithfield Chadbourn 2294: HTTP 200, header **Wed, Nov 18,
  2026**, 1 row (Soybeans) — unchanged. **Still stale by one day**
  (3rd consecutive stale probe: Cycles 13, 14, 22).
- Smithfield Hamer 2179: HTTP 200, header **Wed, Nov 18, 2026**,
  1 row (Soybeans) — unchanged. **Still stale by one day** (2nd
  consecutive stale probe).
- Skyland Hugoton 3370: HTTP 200, header **Wed, Nov 18, 2026**,
  6 rows (Corn 2, Milo 2, Red Wheat 2) — unchanged. **Still stale
  by one day** (2nd consecutive stale probe).
- Skyland Vilas-Walsh 3621: HTTP 200, header **Wed, Nov 18,
  2026**, 5 rows (Corn 2, Milo 1, Red Wheat 2) — unchanged.
  **Still stale by one day** (2nd consecutive stale probe).
- The lag is a persistent one-day lag at all four, still exactly
  one day (no worse). The standing collector note stands: a
  same-day freshness gate would fail these four daily, so they need
  an exemption/lag tolerance if such a gate is ever added. No new
  follow-up probe opened beyond the existing watch; a daytime
  re-check in a later cycle could test whether the widgets refresh
  later in the day rather than overnight.
- The coordinator independently confirmed the Nov 18 headers in
  the saved Chadbourn + Hugoton files.
- URL note: the task brief listed the Smithfield URLs with a
  `www.` prefix, but the registry records them without it — the
  worker used the registry URLs, correctly.

### Merge plan extended to Cycle 21
- New "Cycle 21 (added Cycle 22)" section, verified from git
  history and the cycle report (coordinator spot-checks: chain
  `master..cycle-21` = **61 commits**, 0 merges; tip `726f865`;
  Cycle 21 added 2 commits; test count 692; Alembic head still
  `0019`; CI workflow file still untracked). 200 lines added, 0
  removed. The Cycle 20 section's "59 commits" figure re-verified
  correct.

### Super-plan §9 extended to Cycle 21
- Heading/intro now cover Cycles 1–21 (test chain 179 → 692);
  Cycle 21 bullet added; blockers updated (agricharts wrappers
  verified, Heartland/Mulvane site-side failures, Heritage
  mislabelling).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 22 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heritage live confirmation (1 GET, expect 14 rows); Heartland /
  Mulvane decision (alternate futures source vs toggles off).
- Staleness watch: Chadbourn (3rd consecutive stale probe), Hamer,
  Skyland 3370/3621 (2nd each) — all still exactly one day behind.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–21: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 22:** nothing new needs Adam.
