# Overnight Cycle 28 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-28` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 28 complete — full 13-site AgriCharts-embed family
re-verified live, all exact matches (816 rows); FS Grain USDA mirror
confirmed; merge plan extended to Cycle 27, super-plan §9 extended
to Cycle 27.

**Never merged to master or to any earlier cycle branch. No
spending, no vendor contact, no emails sent, no secrets, no
deployment changes, no paywalled/licensed data scraped. No price,
WASDE number, basis, or bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `823bf2d` | Embed family re-verified, all 13 exact matches; FS Grain mirror confirmed; merge plan extended to Cycle 27 |
| *(this commit)* | Cycle 28 report |

## 2. Test results

- **Full API suite: 709 passed, 0 failed** (unchanged — docs/research
  only cycle, no code changed). Coordinator re-ran the suite to
  confirm.
- Web build: not re-run (no web files changed; last full pass Cycle 17).

## 3. What was built (done)

### Embed family re-verification — all 13 exact matches (13 calls)

One call per site, no retries. **All returned `status='ok'` with
row counts exactly matching their earlier verifications — no drift,
no failures.** **816 rows across the 13 embed sites** (TGM
re-verified in Cycle 26; the other 12 this cycle). Counts only, no
values recorded.

| Site | Rows now | Prior | Locations |
|---|---|---|---|
| Agtegra | 8 | 8 (Cycle 7) | 1 (Hecla) |
| Heritage Cooperative (embed) | 15 | 15 (Cycle 7) | 1 (Ada) |
| Linn Coop | 51 | 51 (Cycle 7) | 5 |
| Midway Coop | 8 | 8 (Cycle 7) | 1 ("All Locations") |
| Ag State | 11 | 11 (Cycle 7) | 1 |
| Superior Ag | 12 | 12 (Cycle 7) | 1 |
| ALCIVIA | 181 | 181 (Cycle 9) | 15 |
| TGM | 362 | 362 (Cycle 9) | 24 |
| PRO Coop 21297 (Ayrshire) | 6 | 6 (Cycle 11) | 1 |
| PRO Coop 21302 (Manson) | 12 | 12 (Cycle 12) | 1 |
| PRO Coop 21302b (Manson dup) | 12 | 12 (Cycle 13) | 1 |
| Hull Coop | 12 | 12 (Cycle 12) | 1 |
| StateLine Coop | 126 | 126 (Cycle 12) | 11 |

Structure unchanged everywhere: same location sets, commodity
splits, and groupby behaviour (Ag State / Superior Ag still group
by commodity with `location_name` authoritative; Midway still
publishes the single "All Locations" label; StateLine still 12 rows
per location except Emmetsburg-AGP, Soybeans-only with 6). The
separate AgriCharts wrapper for the other Heritage-named source was
not probed (already confirmed live in Cycle 23).

### FS Grain USDA mirror confirmed (1 call)

`fetch_usda_mirror_fs_grain()`: **197 rows, report id 7730, dated
Nov 18, 2026** — exact match to the James Valley re-verification
in Cycle 26. Caveat: the region count was not re-tallied this run
(rows grouped on `location`, which is "United States" for all
rows); the 29-region figure stands from Cycle 26.

### Merge plan extended to Cycle 27

New "Cycle 27 (added Cycle 28)" section (194 lines added, 0
removed), verified from git history and the cycle report
(coordinator spot-checks: chain `master..cycle-27` = **73 commits**,
0 merges; tip `ba4df98`; Cycle 27 added 2 commits; test count 709;
Alembic head still `0019`; CI workflow file still untracked; Cycle
27 diff 4 files, 371 insertions, 6 deletions — no code changed).
The Cycle 26 section's "71 commits" figure re-verified correct.
No discrepancies found between git and the Cycle 27 report.

### Super-plan §9 extended to Cycle 27

Heading/intro now cover Cycles 1–27 (test chain 179 → 709); Cycle
27 bullet added; blockers updated (all 10 wrappers re-verified,
every live-verified collector re-checked with zero drift).

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 28 code, tests, fixtures, or docs
(verified by grep on the added lines of the commit; the single
match in the range diff is the Cycle 27 report's own
boundary-attestation heading, not a reference in content). No
contact made.

## 5. What is still scaffold / stub

- Playwright render checks: DTN family (Al-Corn + Sunrise first —
  classic shape), FMN filtered view (Winchester
  `location_filter=2523`), Mapleview, StoneX family (3 sites:
  Frontier, CRC, UFC), The Andersons GRAINweb (closed for static
  collection — only a rendered browser session remains, and the
  facility tables are Barchart-licensed), Landus (Vercel checkpoint).
- Heartland / Mulvane: closed for now (no new hypothesis).
- Staleness watch: the four widgets stay on the exemption list for
  any future freshness gate (no further re-checks needed).
- Mae-Mart `cash_price` from futures + static basis — open
  decision (not computed).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized price
  rows (design note written in Cycle 10 — decision pending).

## 6. Blocked / needs Adam

Carried from Cycles 1–27: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence —
now also gates CGB's `cashbids-js.php` question and the Mae-Mart
cash-price decision), ERP choice (Agvance recommended), eSign
provider, pricing/hosting decisions, gh `workflow` scope, currency
column decision (four concrete choices in
`docs/plans/currency-design.md`), email-bid endpoint auth decision
(public vs admin-only), Playwright render checks (DTN family, FMN
filtered view, Mapleview, StoneX, The Andersons, Landus).

**New in Cycle 28:** nothing new needs Adam.
