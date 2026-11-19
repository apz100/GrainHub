# Overnight Cycle 4 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-4` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 4 complete — the three Cycle 3 leftovers that could
be built without a live browser or Adam are done.

**Never merged to master or to cycle-1/2/3. No spending, no vendor
contact, no emails sent, no secrets, no deployment changes, no
paywalled/licensed data scraped. No price, WASDE number, basis, or
bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `a351bbb` | Email-bid ingest endpoint (parse-only preview, no storage; 12 tests) |
| `11dc318` | Generic Bushel collector (FAC verified live, 45 rows; Collwest cross-check 16/16); FAC registered |
| `a190703` | Correct Bushel research doc — bids live in `.cbmod` widget, not tables |
| `5b0d314` | USDA-mirror collector (both hosts registered; Gulf + Pacific Ports), Crop Production parser wired into ingest-file |
| *(this commit)* | Cycle 4 report |

## 2. Test results

- **Full API suite: 359 passed, 0 failed** (Cycle 3 ended at 320).
  New tests in Cycle 4: email-bid route 12, Bushel collector 12,
  USDA-mirror collector 12, Crop Production parser 3 = **39 new tests**.
- Web build was not re-run in Cycle 4 (no web files changed).

## 3. What was built (done)

### Email-bid ingest endpoint
- `POST /api/email-bids/parse` (JSON pasted text or `.eml`/`.txt`/
  `.csv` upload; `.eml` headers extracted with stdlib `email`) and
  `GET /api/email-bids/senders` (six supported companies, quirks
  pulled from the parser module itself). Parse-only by construction:
  takes a DB session for parity but never touches it (asserted with
  a strict fake session), no mailbox access, no sends, no storage.
- **Flag:** the endpoint is public (no auth), matching the public
  best-bids pattern. Making it admin-only is a one-line change if
  Adam wants that.

### Bushel collector
- Generic collector (`bushel_source.py`) parsing the `.cbmod`
  widget first, falling back to a real `<table>` only when its
  header contains both "Delivery" and "Bid".
- **Correction to Cycle 3 research:** bids are **not** in
  `standardTable`/`market_table` — FAC's only `standardTable` is
  a "Data provided by Bushel" footer and Collwest's `market_table`
  is the futures table. The research doc was corrected in place.
- **Live verification:** FAC parsed **45 rows** across 3 locations
  (Arcadia + Schleswig corn/soy, AGP Manning soy only), USD/bu.
  Collwest cross-check: **16/16 rows match** the existing
  collector on the same live HTML.
- FAC registered in `source_registry.py` (`fac = true`). The other
  8 US Bushel sites stay unverified — the collector deliberately
  refuses to fetch them until each gets its own confirming probe
  (Almota's DTN-vs-Bushel ambiguity and Williams Gin's canonical
  URL still open).

### USDA-mirror collector
- Parses both mirror pages (James Valley Grain, FS Grain): same
  report id **7730, Nov 18, 2026**, **197 data rows, 29 region
  sections** (catalogue said 25 — the live page has 29), incl.
  **Gulf Coast Ports – LA (15 rows)** and **Pacific Ports (24
  rows)**; history via `?id=N` back to Nov 05, 2026.
- **Unit finding (inference, raw numbers always kept):** the page
  footnote claims "all prices are cents/bushel", but printed values
  are dollar-scale for most rows while one White Oats export row
  prints cents-scale — so unit is inferred **per row by magnitude**
  (≥100 → `cents/bu`, else `$/bu`); basis is always cents.
  `cash_price` is the low end of the printed low–high range, with
  `low_price`/`high_price` also returned. Rows before the first
  section row carry `region=None` rather than an invented region.
- Both mirrors registered (`usda_mirror_jvg`, `usda_mirror_fsg`),
  config toggles on. One fetch now unlocks Gulf + Portland export
  bids.

### Crop Production parser
- Format verified from the real Nov 10 2026 txt (161,866 bytes):
  per-crop "Area Harvested, Yield, and Production" tables with a
  7-number "United States" row. Parser covers Corn for Grain,
  Sorghum for Grain, Soybeans for Beans, Rice. Verified against the
  full file: **28 rows**, e.g. Corn production 2026 = 15,893,419
  thousand bu, yield Nov 1 = 179.6 bu/ac (Oct 1 = 181.2). Wired
  into `POST /api/research/ingest-file` (`report_type=
  "crop_production"`). The txt URL is release-specific — the caller
  must pass the current URL from the ESMIS Crop Production page.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 4 code, tests, or docs (verified
by grep). The collector registry, catalogue, and reports treat the
company only as one ordinary price source where it already was;
nothing new features it. No contact made.

## 5. What is still scaffold / stub

- FMN filtered view and Mapleview: need a live-browser Playwright
  render check (subagents cannot do this).
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called); rows carry `cash_price=None` with an explicit reason.
- Remaining 8 US Bushel sites unverified (one polite GET each).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope).
- Currency is still not stored on normalized price rows.

## 6. Blocked / needs Adam

Carried from Cycles 1–3: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only).
