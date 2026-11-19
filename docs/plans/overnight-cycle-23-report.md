# Overnight Cycle 23 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-23` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 23 complete — Heritage confirmed live (14 rows),
Heartland + Mulvane toggled off, jsquote-fallback design note,
merge plan extended to Cycle 22, super-plan §9 extended to Cycle 22.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `c9c9c2e` | Heritage confirmed live (14 rows); Heartland + Mulvane toggled off; jsquote fallback design note; merge plan extended to Cycle 22 |
| *(this commit)* | Cycle 23 report |

## 2. Test results

- **Full API suite: 697 passed, 0 failed** (Cycle 22 ended at 696).
  New tests in Cycle 23: toggle-off 1 = **1 new test**.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Heritage live confirmation — CONFIRMED (1 GET)
- `fetch_heritage_grain_cooperative()` called live returned **14
  rows**, exactly as the Cycle 22 parser fix predicted. `[US-AG
  OK] Heritage Grain Cooperative: 14 rows from 1 locations`.
- **Commodities:** CORN 6, BEANS 6, WHEAT 2 (CASH rows plus DEC
  2026 / JAN / FEB / MAR / FALL 2027 forwards and WHEAT – JUL
  2027), deliveries Oct 2026–Nov 2027.
- **Location:** all 14 rows carry the company fallback `Heritage
  Grain Cooperative - Heritage Grain Cooperative` — the page's
  `<h4>` tags are commodity headings, so the Cycle 22
  commodity-heading fallback applies as designed. Standard 10
  columns. The Cycle 22 follow-up is closed.

### Heartland / Mulvane toggle-off (coordinator decision)
- In `config.toml`, `heartland_coop = false` and `mulvane_coop =
  false`, each with a Cycle 23 comment (two consecutive 0-row
  probes, Cycles 21–22; `jsquote.php` tag missing; poller would
  fetch daily for nothing; reversible; `us_elevators_urls.toml`
  entry stays enabled — the toggle is the gate). **Not re-probed**,
  per the decision. Wrappers/registry rows unchanged, so
  re-enabling is a one-line flip.
- **Seed count is now 104 → 102** (119 adapters − 17 toggled off:
  bunge, mapleview, 13 DTN, Heartland, Mulvane).
- New test `test_cycle23_zero_row_agricharts_adapters_toggled_off`
  in `tests/test_source_toggle_gating.py`: both toggles false, both
  in the derived disabled set, siblings (`heritage_grain_cooperative`,
  `keller`) still on, explicit-key seed of both + `keller` creates
  only `keller` and records both in `skipped_disabled`, and
  pre-existing rows for both stay out of the due list. Also updated
  `test_config_toggles_exist_for_all_new_adapters` (it asserted
  *all* AgriCharts toggles true; it now expects `false` for exactly
  `heartland_coop`/`mulvane_coop`, all others still `true`). No
  hardcoded seeded count anywhere — the gating/orchestration tests
  derive the disabled set from the real toggles.
- The coordinator independently verified the toggles (heartland
  false, mulvane false, heritage true) and the suite (697 passed).
- Self-inflicted break, fixed by the worker: an edit intended as a
  no-op dropped the newline after a test function definition,
  producing an `IndentationError` caught on the first suite run
  (collection error, 0 tests ran). Fixed the line, re-ran, suite
  green at 697.

### AgriCharts futures-fallback design note (design only, 0 GETs)
- New `docs/plans/agricharts-futures-fallback-design.md` (170
  lines): the problem, current behaviour, field analysis, FMN
  precedent, 4 options with pros/cons and per-site returns, a
  recommendation, tests, and the decision needed. No option was
  implemented.
- **Field analysis (verified against the code):** `writeBidRow`
  args carry, with **no jsquote feed needed**: Name (arg 0),
  **Basis in ¢/bu (arg 1, signed — in the row itself)**,
  Delivery/Delivery End (args 6–7), Location (surrounding `<h4>`,
  company fallback), futures symbol (arg 14).
  **Feed-dependent:** Futures Price (`last`) and Bushel/MT Cash
  Price (computed as futures + basis). **Either:** Futures Month —
  taken from the feed's `month` field today, but decodable from the
  symbol (FMN does exactly this). **Neither:** Change is hardcoded
  `""` — the collector never fills it, feed or no feed, so nothing
  is lost there. Current behaviour: missing tag → warning + empty
  DataFrame before any row parsing. FMN (`fmn_source.py`, Cycles
  10–11) degrades instead: parses the page, leaves futures/change/
  cash `None` with a note, decodes month from the symbol.
- **Recommendation: (a) Parse rows with futures/cash `None` (FMN
  precedent), with the (b) probe run first on Heartland only.**
  Key reason: basis is in the row, not the feed, so the surviving
  data is complete for the thing that actually differs by elevator
  — basis-only rows are useful and honest, the pattern is already
  proven by FMN, and it needs no new network call or guessed URL.
  Futures Month should be decoded from the symbol so that column
  survives too. Option (b) (derive the feed URL from row symbols,
  `varname=quotes`) is worth a 2-GET Heartland probe first since
  full rows would be strictly better if the feed still answers,
  but (b) alone leaves the collector brittle the next time a tag
  disappears. Options (c) (leave as-is, toggles off) and (d)
  (futures from another feed — parked, month-matching risk) are
  documented with pros/cons.
- **Decision needed from Adam/coordinator:** approve (a) for
  implementation in a later cycle, including two sub-decisions: (i)
  whether basis-only rows may flow into the pipeline — i.e.
  downstream handles `None` futures/cash — or should be
  flagged/quarantined until proven; (ii) whether Futures Month may
  be decoded from the symbol rather than left `None`. Toggles stay
  off until (a) is implemented and at least one site is
  probe-confirmed returning rows; re-enabling is a separate step.

### Merge plan extended to Cycle 22
- New "Cycle 22 (added Cycle 23)" section, verified from git
  history and the cycle report (coordinator spot-checks: chain
  `master..cycle-22` = **63 commits**, 0 merges; tip `7704d02`;
  Cycle 22 added 2 commits; test count 696; Alembic head still
  `0019`; CI workflow file still untracked). 226 lines added, 0
  removed. The Cycle 21 section's "61 commits" figure re-verified
  correct.

### Super-plan §9 extended to Cycle 22
- Heading/intro now cover Cycles 1–22 (test chain 179 → 696);
  Cycle 22 bullet added; blockers updated (Heritage parser fixed).

### Coordinator decision recorded: agricharts UA stays Chrome
- The Cycle 21 finding (the agricharts collector sends a Chrome
  `Mozilla/5.0` UA, not `GrainHub-Research/1.0`) is **kept as-is**:
  the Chrome UA is pre-existing Cycle 1 behaviour, it works, and
  changing it risks fetches being blocked as non-browser traffic.
  Research probes continue to use `GrainHub-Research/1.0`.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 23 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- AgriCharts fallback (a) implementation — pending the decision
  above; Heartland probe (b) — 2 GETs, pending the same decision.
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

Carried from Cycles 1–22: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 23:** nothing new needs Adam — but the AgriCharts
fallback (a) implementation approval is flagged for the
coordinator (two sub-decisions in §3 above).
