# Overnight Cycle 6 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-6` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 6 complete — DTN sweep, deployment checklist,
basis alerts.

**Never merged to master or to cycle-1/2/3/4/5. No spending, no vendor
contact, no emails sent, no secrets, no deployment changes, no
paywalled/licensed data scraped. No price, WASDE number, basis, or
bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `a69703b` | Deployment checklist (Vercel/Render/Supabase) + basis-alert helpers (14 tests) |
| `387c985` | DTN sweep (28 sites); Ace Ethanol + Alliance Grain verified Bushel, registered |
| `eb01c71` | Fix corrupted string literal in `bushel_source.py` (see §4) |
| *(this commit)* | Cycle 6 report |

## 2. Test results

- **Full API suite: 380 passed, 0 failed** (Cycle 5 ended at 364).
  New tests in Cycle 6: basis alerts 14, Bushel Cycle 6 shapes 2 =
  **16 new tests**.
- Web build was not re-run in Cycle 6 (no web files changed).

## 3. What was built (done)

### DTN widget sweep (28 sites, one polite GET each)
The Cycle 1 survey never enumerated the 26 by name, so they were
reconstructed from its tables (16 DTN-ref sites + Aurora/Kanza +
Ace/Alliance + Heartland `bids.htm` + Ag State/ALCIVIA/CRC/CGB/
Bunge) — arithmetic verified and documented in the catalogue.

- **22× HTTP 200; 6 non-200/unreachable** (Ag Partners 503 "Site
  is offline"; Heartland `bids.htm` proxy error; ALCIVIA, Bunge,
  CRC, Five Star read timeouts at 30 s — recorded, not retried).
- **Static-HTML bid rows: 2** — Ace Ethanol (11 rows Corn) and
  Alliance Grain (10 rows Corn 5 + Soybeans 5), both Bushel
  `.cbmod` widgets, handled by the existing generic collector
  (verified against saved HTML, status ok). Both registered in
  `source_registry.py` with config toggles on.
- **JS-only: 20. No bid table at probed URL: 1** (CGB).
  **Blocked (429/Cloudflare): 0** — every captcha/Cloudflare
  substring hit was a false positive (contact-form reCAPTCHA CSS,
  cookie-policy text, `cdnjs.cloudflare.com` CDN hosts).
- **Reclassifications:** AGP `dtn → bushel` (page embeds an
  `<iframe src="https://agp.o.bushelsites.com/cash-bids">`; iframe
  URL not fetched — follow-up); Ace/Alliance `unknown → bushel`;
  Agtegra, Heritage, Linn, Midway, Superior `DTN-ref → AgriCharts
  cashbids.php embed + ATLAS DTN shell` (JS-only, no existing
  collector); Ag State `→ cashbids.php embed` with zero `dtn`
  strings (Cycle 1 label was wrong); Gateway FS `DTN-ref →
  unconfirmed` (only nav links; its cash-bids sub-page unfetched);
  Frontier `DTN → StoneX` (new widget family, inline model empty
  in static HTML); Al-Corn + Elite Octane **uncertain → resolved**
  (real DTN widgets, no challenge). Al-Corn is the only site with
  classic inline `CashBidTable(tableOptions)` (companyID 239483) —
  an exact fit for `us_dtn_source.py`.
- **New collector lead (research only, not built):** AgriCharts
  `cashbids.php` embed, 6 sites (Agtegra 3135, Heritage 21608,
  Linn filter=all, Midway 82270, Ag State 84205, Superior 82244).
  `us_agricharts_source.py` covers `writeBidRow`, not this embed.
- Full per-site table in `docs/plans/price-source-catalogue.md`
  ("Cycle 6 DTN sweep" section). Playwright render checks are
  still needed for the 12 DTN-family JS-only sites.

### Deployment checklist
- `docs/plans/deployment-checklist.md`: Vercel web + Render API +
  Supabase Postgres. Branch rule up front (deploy from `master`
  only; cycle branches 1–6 unmerged, must be reviewed/merged
  first); env vars per service; API keys env-only with "obtain
  from Adam, never commit" notes (key names verified against the
  actual code); Alembic chain verified linear (single head `0018`);
  ingestion 08:00 + 15:00 America/Toronto; health endpoints;
  rollback note (migrations forward-only). No deployment changes
  made.

### Basis alerts
- `app/services/basis_alerts.py`: pure helpers —
  `find_basis_crossings` over the basis-tracker response shape or
  a row list (`>`/`>=` = up, `<`/`<=` = down, missing/non-numeric
  basis skipped and counted, never triggering) and
  `detect_basis_crossing` for moves between readings. 14 tests.
  Deliberately standalone — not wired into the alert DB loop or
  `/api/alerts` routes yet, so that wiring can be reviewed
  separately.

## 4. Mistake found and fixed in this cycle

Commit `387c985` was pushed while `bushel_source.py` contained a
corrupted string literal (a bad edit left `\"` escape sequences
and a missing opening quote in the Forest River site notes), which
broke pytest collection for the two Bushel test files (2 errors).
The breakage was caught by my own full-suite run immediately
after the push, fixed with a line-level rewrite, and verified:
**380 passed, 0 failed**. The fix is commit `eb01c71` on top —
the broken commit was not rewritten, so the history shows the
mistake and the fix. Lesson recorded: never let a `| tail`
mask a failing pytest exit code when committing.

## 5. North Gower Grains boundary — applied

Zero references in any new Cycle 6 code, tests, or docs (verified
by grep). No contact made.

## 6. What is still scaffold / stub

- Playwright render checks for the 12 DTN-family JS-only sites,
  plus FMN filtered view and Mapleview.
- Collector decisions pending: AgriCharts `cashbids.php` embed
  (6 sites) and StoneX (1 site, Frontier).
- AGP iframe target, Gateway FS + TGM cash-bids sub-pages
  unfetched; Ag Partners / ALCIVIA / CRC / Five Star / Bunge
  re-checks due (503/timeouts may be transient).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope). Currency still not stored on normalized
  price rows. Basis alerts not yet wired into the alert loop.

## 7. Blocked / needs Adam

Carried from Cycles 1–5: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (DTN family, FMN filtered view, Mapleview).
