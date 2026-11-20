# Phase A — Endpoint Robustness Audit (marathon 2026-11-20)

Scope: every GET list/report endpoint in `GrainBids/grainbids/apps/api/app/api/routes/*.py`
except `research.py` (owned by another phase) and `basis.py` (fixed 2026-11-19).
Checks per endpoint: (1) unbounded queries, (2) heavy payload columns loaded
unnecessarily, (3) row/ORM-type assumptions fake-data tests can't catch,
(4) missing pagination on growable lists.

Method: every file read line by line. Suspects were proven with a failing
real-database test first (SQLite in-memory, real ORM rows, same pattern as
`tests/test_basis_pair_loading.py`), then fixed. Evidence lives in
`tests/test_phase_a_endpoint_robustness.py` (19 tests: pre-fix 10 failed /
9 passed, post-fix 19 passed; the two preview tests were re-verified to fail
on the unfixed routes after a test-side fix). Handler tests assert on the
emitted SQL (a full-entity select names the payload column; a deferred one
does not) and/or on the loaded instance `__dict__`, plus functional results
from real rows.

## Proven findings — FIXED

| Endpoint | Check | Finding | Fix |
|---|---|---|---|
| `GET /api/normalized-prices` (list), `/preview`, `/preview-grouped`, `GET /api/market-search`, market-report + daily-newsletter services (all via `_base_query` / `_load_preview_payload`) | (2) | Full `PriceSnapshot` entities selected — `raw_payload_json` (a whole day file per file-ingestion snapshot) transferred for up to `limit*3` = 3,000 rows/request; Python only ever reads `snapshot.captured_at` | `defer(PriceSnapshot.raw_payload_json)` on `_base_query` in `normalized_prices.py` |
| `GET /api/normalized-prices/top-movers` | (2) | Same full-snapshot load from its own inline query (fetch ≤ 300 rows) | Query rebuilt on `_base_query` (identical org/freshness semantics, defer included) |
| `GET /api/prices/history`, `GET /api/prices/seasonal` (via `_load_price_rows`) | (2) | Full snapshots incl. payload for up to `_HISTORY_FETCH_LIMIT` = 5,000 rows; only `captured_at` read | `defer(PriceSnapshot.raw_payload_json)` in `price_history.py` |
| `GET /api/best-bids` | (2) | Full snapshots incl. payload, 300 rows; only `captured_at` read | `defer(...)` in `best_bids.py` |
| `GET /api/saved-searches/{id}/preview` | (2) | Full snapshots incl. payload, ≤ 300 rows; only `captured_at` read | `defer(...)` in `saved_searches.py` |
| `GET /api/watchlists/{id}/preview` | (2) | Full snapshots incl. payload, ≤ 200 rows; only `captured_at` read | `defer(...)` in `watchlists.py` |
| `POST /api/quotes/export` loader `_load_quote_rows` (report endpoint, not GET — same proven pattern, flagged as such) | (2) | Full snapshots incl. payload for up to 20,000 export rows; serializer reads only `captured_at` | `defer(...)` in `quotes.py` |
| `GET /api/research/calendar` (`report_calendar.py`) | (1)+(2) | `select(ResearchReport).scalars().all()` — **every** stored report row, full `payload` JSON included, no limit — to compute latest-per-type status from 5 scalar fields; `payload` never read | `defer(ResearchReport.payload)` in `report_calendar.py` |
| `GET /api/advisor/signal` (via `_latest_price`) | (1) | Loaded **every** matching `NormalizedPrice` row for org+commodity (no LIMIT; table grows with every ingestion run) to take `rows[0]` | `.limit(1)` in `advisor.py` (ordering unchanged: canonical first, then newest capture) |

Deferred columns still lazy-load on access, so semantics are preserved if a
future caller ever needs them; the SQL-side freshness filter in
`normalized_prices` (`raw_payload_json["ingestion_run_id"].astext`) is
unaffected by `defer`.

## Findings documented, NOT fixed (need a product decision or a larger change)

| Endpoint | Finding |
|---|---|
| `GET /api/ingestion/company-identity/ambiguous-locations` (admin) | Service loads **all** `(location_id, company_id, source_name)` triples for the org with no SQL limit and aggregates in Python; the `limit` param applies to output rows only. Column-light (3 scalars, no payload) but row-unbounded on the largest table. Proper fix = push `GROUP BY location_id, company_id, source_name` + count into SQL. No correctness break, so no failing test was written; recommend a follow-up cycle. |
| `GET /api/prices/history`, `/seasonal` | No org scoping at all (no `Source` join) — returns every org's prices. `best_bids` is public by design; whether history/seasonal should be is a product decision. Flagged, unchanged. |
| `GET /api/research/calendar` | Row count is still unbounded (now light scalar rows only). Latest-per-type could be pushed into SQL; not needed for safety after the defer. |
| `GET /api/alerts/rules` | Unbounded per-org list + 2 aggregate queries per rule (N+1). Rules are user-created config (small); no heavy columns. Observation only. |
| `GET /api/advisor/farm-profiles`, `GET /api/saved-searches`, `GET /api/watchlists`, `GET /api/source-health`, `GET /api/sources` | Per-org lists with no `limit`. All are config/registry-scale tables (user's own profiles/searches/lists; ~125 registered sources), no payload columns, and the JSON columns they do load (`filters_json`, `crop_mix_json`) are part of the response. Observation only — add limits if these ever become user-generated at scale. |
| `GET /api/market-search` (`_resolve_origin`) | Resolving an origin by location *name* loads all of the org's `Location` rows to compare canonical keys. Small rows, no payload columns. Observation only. |

## Clean endpoints (read line by line + real-DB test where marked ✔)

| Endpoint | Bound / why clean | Test |
|---|---|---|
| `GET /api/normalized-prices/facets` | Distinct-column selects + `GROUP BY` aggregates only; no entity or payload loads | ✔ real rows (commodities/locations/summary values) |
| `GET /api/normalized-prices/summary` | Aggregate `avg`/`count` only | ✔ |
| `GET /api/advisor/farm-profiles` | Per-org config rows; `crop_mix_json` is response data | ✔ |
| `GET /api/alerts/rules` | See observation above; works against real rows incl. per-rule aggregates | ✔ |
| `GET /api/alerts/recent` | `limit` ≤ 200; `(Alert, AlertRule)` Row unpacking verified against real rows | ✔ |
| `GET /api/elevator-ops/contracts` / `/scale-tickets` / `/crm-notes` | All `limit` ≤ 200 | ✔ (incl. limit honoured with 3 seeded contracts, limit=2) |
| `GET /api/ingestion/runs` | `limit` ≤ 200 via `list_ingestion_runs` | ✔ |
| `GET /api/ingestion/sla` | Service caps run scans at 2,000 / recent 5 (code read of `source_orchestration.build_sla_summary`) | code read |
| `GET /api/ingestion/diagnostics`, `/basis-change-diagnostics` | Admin; service loads latest snapshot (`limit 1`) + that one snapshot's price rows. Diagnostics *deliberately* reads `raw_payload_json` fields (source_file_path, run id) — that is its output, and it is bounded to one snapshot | code read |
| `GET /api/market-report/preview` | `ResearchReport` capped at 10 and `payload` **is** the response content (intentional); price side via `_load_preview_payload` (fixed above) | code read |
| `GET /api/newsletter/daily-draft` | Composes `_load_preview_payload` (fixed above) + `ResearchReport` `limit 10` in the service | code read |
| `GET /api/quotes/runs` | `limit` ≤ 200 | ✔ |
| `GET /api/quotes/runs/{id}/download` | Single-row lookup | code read |
| `GET /api/sources/priority` | Per-company config rows | ✔ |
| `GET /api/sources/priority/candidates`, `/canonical-coverage` | `GROUP BY` aggregates over prices; tuple unpacking of real Rows verified | ✔ |
| `GET /api/source-health`, `/summary` | Sources registry-scale; runs/snapshots capped at 500 (same bound as basis fix) | ✔ (live + broken classification from real rows) |
| `GET /api/uploads` | `limit` ≤ 200; `raw_headers`/`column_mapping` are small and part of the response | ✔ |
| `GET /api/sources` (reference), `GET /api/commodities` | `limit` ≤ 1,000 | ✔ |
| `GET /api/signals/forecast` | `limit` ≤ 1,000 | ✔ |
| `GET /api/signals/health` | `max`/`count` aggregates only. Not executed against SQLite: the handler subtracts a tz-aware `now` from the stored datetime in Python and SQLite returns naive datetimes (Postgres returns aware, so prod is fine) — test-environment artifact, not a bug | code read |
| `GET /api/email-bids/senders` | No DB — derived from parser-module constants | code read |
| `GET /api/futures/strip`, `/canola` | No DB — static contract structure, prices explicitly null | code read |
| `GET /api/market-data/sources`, `/adapters` | Registry/filesystem metadata, no table scans | code read |
| `GET /api/newsletter/unsubscribe` | Single-row token lookup | code read |
| All `GET */module` endpoints (`bids`, `settings`, `alerts`, `quotes`, `sources`, `watchlists`, `elevator-ops`) | Static dicts, no DB | code read |

## Check (3) — row/ORM-type assumptions

Tuple/Row unpacking from `.all()` was exercised against real SQLAlchemy
rows in the tests above (alerts/recent, quotes export loader, sources
candidates + coverage, facets company/location rows, normalized-prices
list/preview) — all correct. The only `isinstance`-on-rows filter outside
`basis.py` is `report_calendar`'s `isinstance(row, ResearchReport)` over
`.scalars()` results — always true for real rows, harmless (unlike the
basis `isinstance(item, tuple)` bug). No other instances found.

## Test-environment notes

- The normalized-prices list/top-movers handler tests stub out
  `_build_market_period_recency_filters` (Postgres-only `~` / `to_date` /
  `initcap` SQL that SQLite cannot execute — pre-existing). The loader
  bound being pinned lives in `_base_query`, untouched by the stub, and
  the facets/summary tests run the same way.
- `GET /api/market-search` was not separately real-DB tested: its
  default path runs the Postgres JSONB freshness subquery. It shares
  `_load_preview_payload` / `_base_query` with the tested endpoints and
  inherits the defer fix.

## Suite counts

- Baseline (branch start): 731 passed / 5 skipped / 0 failed.
- This phase's file: `tests/test_phase_a_endpoint_robustness.py` — 19 tests.
- Full API suite after Phase A fixes: **768 passed / 5 skipped / 0 failed**
  (delta vs baseline includes tests added by parallel marathon phases on
  the shared branch).
