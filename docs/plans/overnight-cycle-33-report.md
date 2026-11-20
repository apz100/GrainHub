# Overnight Cycle 33 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-33` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 33 complete — Bushel samples #5 and Skyland/AGP
re-verified, 11/12 exact matches (AGP changed site-side); AGP
registry entry updated Chester → Aberdeen; merge plan extended to
Cycle 32, super-plan §9 extended to Cycle 32.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `550220a` | Bushel samples #5 + Skyland/AGP re-verified 11/12; AGP switches Chester to Aberdeen; merge plan extended to Cycle 32 |
| *(this commit)* | Cycle 33 report |

## 2. Test results

- **Full API suite: 710 passed, 0 failed.** Coordinator ran the
  suite twice — once before the AGP metadata update and once after
  — both 710 passed. No new tests added; one existing assertion
  updated (AGP registry `default_location` Chester → Aberdeen,
  plus a notes assertion). The targeted run of
  `test_bushel_agp.py` + `test_source_config_sync.py` passes (6
  passed), confirming the two toml files stay in sync after the
  AGP comment edits.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Bushel per-location sample #5 — 6/6 exact matches

One call per site, no retries. **All 6 returned `status: ok` with
exact row-count matches** to the Cycles 12–15 baselines; all six
headers fresh (Nov 19). Counts only, no values recorded. 14 rows
total. IDs verified against the registry before fetching (1666 =
Bentonville confirmed; Clarkton is 1668).

| Site | Rows now | Header date | Verdict |
|---|---|---|---|
| Smithfield Bentonville (1666) | 3 | Nov 19 | Exact match |
| Smithfield Bladenboro Feed Mill (1667) | 2 | Nov 19 | Exact match |
| Smithfield Clinton (1669) | 3 | Nov 19 | Exact match |
| Smithfield Morgans Corner (1673) | 2 | Nov 19 | Exact match |
| Smithfield Red Springs (1676) | 1 | Nov 19 | Exact match |
| Smithfield Walstonburg (1678) | 3 | Nov 19 | Exact match |

**Bentonville gap from Cycle 32 closed:** the Cycle 32 brief
mislabelled 1666 as Clarkton and the worker fetched Clarkton
(1668) instead; Bentonville (1666) was not re-fetched. This cycle
it was — 3 rows (Soybeans 1 / Wheat 1 / Corn 1), exact match to
Cycle 12.

### Skyland / Forest River / AGP / Ace Ethanol — 5/6 exact matches

One call per site, no retries. Counts only, no values recorded.

| Site | Rows now | Prior | Header date | Verdict |
|---|---|---|---|---|
| Skyland 2766 Spearman–Gruver–Texline | 5 | 5 (Cycle 14) | Nov 19 | Exact match |
| Skyland 2770 Sunray Area | 5 | 5 (Cycle 14) | Nov 19 | Exact match |
| Skyland 2771 Kendall–Midway–Lydia | 6 | 6 (Cycle 14) | Nov 19 | Exact match |
| Forest River | 3 | 3 (Cycle 5) | Nov 19 | Exact match |
| AGP (iframe target) | 8 | 1 (Cycle 7) | Nov 19, 01:50 AM | **Changed — see below** |
| Ace Ethanol | 11 | 11 (Cycle 6) | Nov 19 | Exact match |

**AGP — site-side change, not a collector issue:** the iframe
target (`agp.o.bushelsites.com/cash-bids`) no longer serves
Chester, NE. It now returns location **AGP Aberdeen, SD**, 8 rows:
Soybeans 3 (Nov/Dec/Jan) + Soybean Meal 5 (Nov–Mar, a commodity
not present in Cycle 7). Status `ok`, parsed cleanly with no
warnings. The worker did not re-call it (no-re-probe rule).

**Coordinator decision:** update the existing `agp` registry entry
rather than register a second one — same URL, same collector, only
the served default location changed. Changes (commit `550220a`):
`bushel_source.py` — `default_location` Chester → Aberdeen,
registry notes + module docstring + `fetch_agp` docstring updated
to record both observations; `test_bushel_agp.py` — registry
assertion now expects Aberdeen (plus a notes assertion), module
docstring notes the change; `config.toml` and
`us_elevators_urls.toml` — AGP comments updated identically in
both files (sync guard still passes). The synthetic Chester
fixture is kept as a parse test (its location comes from the
fixture's own h2). If the page rotates its default location again,
a later re-verification will catch it.

### Merge plan extended to Cycle 32

New "Cycle 32 (added Cycle 33)" section (217 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-32` = **83 commits**,
0 merges; tip `cf37686`; Cycle 32 added 2 commits; test count 710;
Alembic head still `0019`; CI workflow file still untracked). The
Cycle 31 section's "81 commits" figure re-verified correct. Note:
the new section's §7r still lists Bentonville as needing a
re-verification call — that was accurate for Cycle 32; it was
closed this cycle (see above).

### Super-plan §9 extended to Cycle 32

Cycle 32 bullet added (Bushel samples #4 + Cycle 11/5 sites 12/12
exact matches; merge plan extended to Cycle 31, 81 commits).

### Price-source catalogue — Cycle 33 section added

New "Cycle 33" section (both sweeps + AGP change) and the AGP
catalogue row updated with the Cycle 33 finding (also correcting
its stale "not yet wired into `source_registry.py`" note — AGP
was wired in Cycle 20).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 33 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit). No contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (no new hypothesis).
- Staleness watch: five widgets on the exemption list for any future
  freshness gate (Chadbourn, Hamer, Hugoton 3370, Vilas-Walsh 3621,
  Almota). No re-checks needed.
- AGP: the iframe target changed its served default location once
  (Chester → Aberdeen); if it rotates again, a later
  re-verification will catch it. No action needed now.
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–32: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 33:** nothing new needs Adam.
