# Phase F notes — newsletter / market-report dry run (2026-11-20)

Method: generated the daily newsletter and the weekly market report
locally from realistic injected Eastern Ontario data (never prod),
saved the rendered output in `docs/marathon/dry-run/`, and inspected
it line by line. Delivery stayed OFF throughout (the draft dict
itself reports `delivery.enabled=false`).

## Verified

- Subject/branding: "GrainBids Daily Newsletter — November 20, 2026"
  and "GrainBids Eastern Ontario Market Report — November 20, 2026".
  No "GrainHub" string anywhere in the outputs.
- No placeholder leakage: no `None`, `nan`, `TODO`, or lorem text in
  text, HTML, or JSON outputs.
- Numbers check out by hand: corn median $7.26/bu across 4 listed
  markets (rows shown are top 3), range $0.43; soybeans median
  $15.52, range $0.21; single-market wheat range honestly "n/a".
- Basis-movers section carries its honesty caveat verbatim ("Ranked
  from today's snapshot only — no prior-day basis is stored, so this
  is not a day-over-day move").
- USDA section honestly reports "No USDA report dated 2026-11-20 is
  on file" when nothing is dated today, with the on-file count.
- Upcoming reports via the REAL calendar loader (not injected):
  renders proper names + publishers ("Commitments of Traders —
  2026-11-20; source: CFTC", "Crop Progress — 2026-11-23; source:
  USDA NASS", …) inside the 14-day window.
- Market report + research section (the route's actual composition):
  appends a `research` section that renders "no values parsed from
  the file" for an empty payload rather than inventing values.
- HTML renders cleanly (single-column, inline styles, GrainBids h1).

## Investigated, not a defect

- Injected upcoming events rendered as raw codes (`grain_stocks`)
  in the first dry run — traced to the fixture using a `title` key;
  the renderer reads `name`, which is exactly what the production
  loader (`_load_upcoming_events` ← report calendar) supplies.
  Fixture error, not product error; no code changed.
- The single "-" line under text headings is a deliberate, consistent
  separator in both text renderers. Left as-is (style, not a bug).

## Changes made

None to product code — the dry run exposed nothing that met the
fix bar. Existing suites re-run: test_daily_newsletter +
test_research = 41 passed.
