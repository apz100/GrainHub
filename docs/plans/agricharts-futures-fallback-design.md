# AgriCharts collector: what to do when jsquote.php is missing

Status: design only (Cycle 23, 2026-11-19). No code changed, 0 GETs.
Applies to `us_agricharts_source.py` (`fetch_us_agricharts`).
Related precedent: `fmn_source.py` (Cycles 10–11).

## 1. The problem

2 of the 13 generic-AgriCharts sites — Heartland Coop and
Mulvane Coop (`heartlandcoop.com` / `mulvanecoop.com`, both
`/markets/cash.php`) — stopped carrying the `jsquote.php`
`<script>` tag. Two consecutive 0-row probes each (Cycles 21,
22); the pages still return HTTP 200. Same cause at both, so
plausibly an AgriCharts template change rather than two
independent breakages — unconfirmed, and the other 11 sites
still carry the tag. Cycle 23 flips both toggles off; the open
question is what the collector should do when the tag is
missing, so the sites can come back instead of staying dark.

## 2. Current behaviour

`fetch_us_agricharts` searches the page for the jsquote tag
(`_JSQUOTE_SCRIPT_RX`: `jsquote.php?varname=…&symbols=…`). If
the tag is absent it prints a warning and returns an empty
DataFrame **before parsing any rows** — even though the
`writeBidRow()` rows may still be in the HTML. Same early
return if the jsquote feed itself returns no data.

## 3. Field analysis: what actually depends on the feed

Verified against `_WRITEBIDROW_RX` and the row-building code
(`writeBidRow(name, basis, manual, eod, incwt, rounding, start,
end, location, group, notes, weight, rowclass, chartsym,
quotes['SYMBOL'])`):

| Row field | Source | Needs jsquote? |
|---|---|---|
| Name | arg 0 | No |
| Basis (¢/bu) | arg 1, signed | **No — in the row itself** |
| Delivery / Delivery End | args 6–7, verbatim | No |
| Location | surrounding `<h4>` (company fallback) | No |
| Futures symbol | arg 14 (`quotes['SYMBOL']`) | No |
| Futures Month | feed `month` today | No — decodable from symbol (FMN does this) |
| Futures Price | feed `last` | **Yes** |
| Bushel / MT Cash Price | futures + basis | **Yes (via futures)** |
| Change | — | No — hardcoded `""`; never filled, feed or no feed |

A missing tag costs exactly the futures price and the two cash
prices derived from it; basis, delivery, location, name and
symbol are all page-native. Basis is the elevator-specific
signal (futures are common across sites), so a basis-only row
is still real, published data.

## 4. FMN precedent

`fmn_source.py` already degrades this way (Cycles 10–11):
on a feed failure or an empty feed it still parses the page.
Futures-linked rows get `futures_price` / `change` /
`cash_price` = `None`, basis as published, `futures_month`
decoded from the contract symbol, and a note saying the values
come from the external feed and are not in the static HTML.
Nothing is invented. The same pattern applies directly here —
the only difference is that the US collector currently bails
before parsing instead of degrading.

## 5. Options

### (a) Parse rows with futures / cash None (FMN precedent)

Drop the early return; parse the `writeBidRow` rows, set
Futures Price / Bushel Cash / MT Cash to `None` (or empty, per
the column's convention), keep Basis / Delivery / Location /
Name / Symbol, decode Futures Month from the symbol (reuse the
FMN month-code decoder), and attach a note that futures and
cash come from the missing jsquote feed. A feed fetch failure
(tag present, feed down) degrades the same way.
- Pros: recovers both sites, no new network dependency; basis
  (the per-elevator signal) survives; FMN-consistent; honest
  (None + note, never invented); other 11 sites unaffected.
- Cons: partial rows flow downstream — every consumer must
  treat a missing cash price as missing, not zero.
- Returns for Heartland/Mulvane: one row per bid, Basis /
  Delivery / Location filled, Futures Price and cash `None`,
  Futures Month decoded from the symbol.

### (b) Derive the jsquote feed URL without the tag

The tag supplies `varname` and `symbols`. Symbols are
recoverable from the page itself — the row regex already
captures each row's futures symbol (group 7) — and `varname`
is conventionally `quotes` (FMN's verbatim feed URL uses it).
- Pros: if the feed still answers, full rows (futures + cash)
  with no behaviour change downstream.
- Cons: unproven — needs a probe; if AgriCharts removed the
  tag because the feed is gone for these sites, this fails
  exactly like today; adds a code path that guesses a URL
  parameter.
- Probe (exact, 2 GETs per site): (1) GET the cash page,
  confirm `writeBidRow` rows are still present; collect the
  distinct symbols from the rows' quote tokens. (2) GET
  `https://www.agricharts.com/marketdata/jsquote.php?varname=quotes&symbols=<comma-joined
  symbols>&fields=name,month,last&settle=0&displayType=bids`
  and check for HTTP 200 plus a populated `quotes` object
  covering those symbols. Heartland first (2 GETs); Mulvane
  (2 more) only if Heartland's feed answers.

### (c) Leave as-is (0 rows, toggles off), re-probe periodically

No code change. Both sites stay dark until a later cycle
re-probes and finds the tag back (or a new static route).
- Pros: zero code, zero risk of partial rows downstream.
- Cons: loses both sites' basis data indefinitely; the
  re-probe has no trigger and drifts unless scheduled; if the
  template change is permanent, this is a permanent loss of
  2 of 13 sites. Returns for Heartland/Mulvane: nothing.

### (d) Futures from another feed (noted, not recommended)

Fill futures from a different source (e.g. the platform's own
futures feed) and compute cash as futures + basis — the Cycle 22
follow-up's "alternate futures source". But it couples a cash-bid
collector to a futures feed it does not own, and the futures must
match the row's contract month exactly or the cash price is wrong.
Park it; (a) gets the basis back without it, and (b) is cheaper.

## 6. Recommendation: (a), with (b) as a one-off probe

Implement (a). The deciding fact is in §3: **basis is in the
row, not the feed**, so the surviving data is complete for the
thing that actually differs by elevator. Basis-only rows are
useful and honest, the FMN collector already proved the
pattern, and it needs no new network call or guessed URL.
Decode Futures Month from the symbol so that column survives
too. Run the (b) probe first anyway (2 GETs, Heartland only):
if the feed still answers, (b) is strictly better for that
site and (a) is the fallback. Either way, (a) is what ships —
(b) alone leaves the collector brittle the next time a tag
disappears.

## 7. Tests needed for (a)

In `tests/test_us_agricharts_source.py`, mocked HTTP,
synthetic fixtures (invented values, neutral naming):
1. Fixture with `writeBidRow` rows and **no** jsquote tag →
   rows returned; Basis / Delivery / Location / Name / Symbol
   filled; Futures Price and both cash prices `None` (or
   empty, per convention); note present.
2. Same fixture **with** the tag → unchanged behaviour
   (futures + cash filled) — regression guard for the
   other 11 sites.
3. Futures Month decoded from the symbol matches the feed
   month on the tagged fixture.
4. Row whose symbol is absent from the quotes map → `None`
   futures/cash, no crash (already true via `quotes.get`).
5. Downstream: normalized ingest treats `None` cash as
   missing, not `0` — test at the adapter/normalization
   layer before re-enabling either site.
6. Full API suite stays green (696 passed baseline).

## 8. Decision needed

Coordinator/Adam: approve (a) for implementation in a later
cycle. Two sub-decisions: (i) confirm partial (basis-only)
rows may flow into the pipeline — i.e. downstream handles
`None` futures/cash — or whether they should be flagged /
quarantined until that is proven (test 5 above); (ii)
confirm Futures Month may be decoded from the symbol rather
than left `None`. Toggles stay off until (a) is implemented
and at least one site is probe-confirmed returning rows;
re-enabling is a separate step, not part of this design.

## 9. Cycle 24 findings — (a) implemented, (b) fails, both sites still dark

**Decision (coordinator, Cycle 24): option (a) APPROVED.** (i) Basis-only
rows MAY flow into the pipeline — futures/cash are explicitly `None`
with a note, never invented; no quarantine (same as FMN today). (ii)
YES, decode Futures Month from the symbol.

### Correction to §1 — the tag is present, its symbols are empty

The Cycle 24 (b) probe (1 GET of Heartland's cash page) found the
jsquote tag is **not missing** — it is present but with an empty
symbols list (`symbols=&fields=name,month,last...`). The collector's
`_JSQUOTE_SCRIPT_RX` requires `[A-Z0-9,]+` after `symbols=`, so it
does not match and the collector bails with "tag not found". §1's
wording ("stopped carrying the jsquote.php script tag") is inaccurate
for the current page; the accurate statement is "the page's jsquote
tag carries no symbols". The same correction applies to the Cycle
21/22/23 reports' "tag missing" phrasing for Heartland. (Mulvane's
tag state was not re-checked this cycle.)

### (b) fails for Heartland (2 GETs)

With zero symbols on the page, the §5(b) derivation degenerates to
an empty `symbols=` list. The derived feed URL (exact §5 pattern)
returned HTTP 200, 20 bytes, body exactly `var quotes = null;` —
the endpoint is alive and the URL shape is confirmed correct, but
there is nothing to query: 0 symbols, nothing usable. **(b) fails
not with a 404 or a wrong shape, but because there is nothing to
query.**

### (a) implemented (Cycle 24) — but recovers neither site live

`fetch_us_agricharts` no longer returns empty when the tag is
absent/unmatched: it parses rows as basis-only (Basis / Delivery /
Location / Name / Symbol filled, Futures Month decoded from the
symbol via `futures_month_from_symbol()`, Futures Price / Change /
both cash prices `None` with a `Note` column saying the values come
from the missing feed, never invented). Tag-present behaviour is
unchanged. 5 new tests (synthetic fixtures), full suite 702 passed.
**Live verification (2 GETs): Heartland 0 rows, Mulvane 0 rows.**
Both pages' `writeBidRow` rows are no longer matched in the static
HTML at all — the §3 assumption (rows still in the HTML) does not
hold live as of this probe, so (a) is proven by mocked tests but
recovers neither site today. **Toggles stay `false`.**

### Open hypothesis (untested)

Heartland's page carries a Location filter with 106 named points;
rows may appear only when a `location_filter` value is selected, or
the default view may be genuinely empty/broken. Follow-up probe (1
GET, later cycle): `cash.php?location_filter=<one id>`. Do not
re-probe routinely without that plan. Mulvane's page structure was
not inspected this cycle — same probe applies if pursued.

### Scope note

§5(a) also suggested degrading the same way when the tag IS present
but the feed fetch fails; that was NOT implemented in Cycle 24 (the
task kept tag-present behaviour exactly unchanged). It is a one-line
follow-up: treat empty quotes like the no-tag path.

### Cycle 25 update

- **Filtered-view hypothesis tested — does not hold (1 GET).**
  `cash.php?location_filter=22143` (ADM – DSM, first named option)
  returned HTTP 200, 36,246 bytes; the server honoured the filter
  (option marked selected) but the page still carries **0
  `writeBidRow` data rows** and the jsquote tag still has empty
  symbols. There is no usable filtered-URL pattern for the
  collector. (Only one location id tested; default + one filtered
  view both empty makes a per-location difference unlikely.)
- **Mulvane correction:** Mulvane's tag is likewise **present with
  empty symbols**, not missing — the Cycle 21–23 "tag missing"
  phrasing is corrected for Mulvane too. Its default view carries
  0 rows; it has a 4-location filter (Clearwater, Clearwater-253,
  Mulvane, Mulvane-251) and a commodity filter (Wheat HRW, Corn,
  Milo, Soybeans). **Both sites stay dark; toggles stay off.**
- **Feed-down degradation implemented (Cycle 25).** Tag present +
  empty feed (`var quotes = null;` or `{}`) now degrades like the
  no-tag path (basis-only rows). Only the empty-quotes case
  degrades; a feed fetch that *raises* (HTTP error/timeout) still
  returns empty via the outer `except` — a further one-line
  follow-up if wanted.

### Cycle 26 update — feed-error degradation closes the design

The last open follow-up from §5(a) is now implemented: a feed fetch
that RAISES (HTTP error/timeout) degrades to basis-only rows — only
the `_fetch_jsquote` call is wrapped in its own `try/except`, so a
page fetch that raises still returns empty (no HTML to parse). All
three degradation paths (no tag, empty feed, feed error) now behave
the same way. 5 new mocked tests; suite 709 passed. **Live
re-verification sweep (5 probes, Cycle 26): FMN 453 rows, Five Star
299, TGM 362, USDA mirror 197, FAC 45 — all exact matches to their
last verifications.** The design note's work is complete; the only
remaining AgriCharts open item is Heartland/Mulvane, closed for now
(see catalogue Cycle 25).
