# Phase E — Web resilience for a sleeping free-tier API

Date: 2026-11-20 (marathon branch `marathon/2026-11-20`)
Scope: `GrainBids/grainbids/apps/web` only. No API URLs, env var names, or
org-id behaviour changed. No new dependencies, services, or CDNs.

## New shared code

### `apps/web/lib/fetch-resilient.ts` (new)
- `fetchResilient(input, init)` — drop-in `fetch` replacement:
  - Timeout via `AbortController`, default **75s** (`DEFAULT_API_TIMEOUT_MS`),
    long enough to outlast a free-tier Render cold start (~50s) plus a real
    response, so a dead request eventually fails instead of hanging forever.
    A caller-supplied `signal` is honoured and never retried.
  - **Exactly one retry** (after 1.5s) on network failure or timeout only.
    HTTP error responses are returned untouched, so existing `.ok` / detail
    handling in every page keeps working unchanged. Mutations pass
    `retries: 0` so a POST/PATCH/PUT is never replayed blindly.
  - Throws the typed `ApiFetchError` (`kind: "timeout" | "network" | "http"
    | "aborted"`, optional `status`) only when no response could be obtained,
    with plain-language messages ("Could not reach the API. It may be waking
    up — please retry.").
- `fetchJsonResilient()` — same, plus JSON parsing and an `http`-kind
  `ApiFetchError` carrying the API's `detail` message for non-2xx.
- `readApiFailure(res)` — the response-detail reader the dashboard used to
  define locally, now shared.
- `SLOW_FETCH_THRESHOLD_MS = 3000` — the shared "this is a slow load" cutoff.

### `apps/web/app/_components/fetch-states.tsx` (new)
- `useSlowLoad(loading, thresholdMs?)` hook — true once a load has been
  continuously running past the threshold.
- `WakingApiNotice` — amber `role="status"` banner: **"Waking the API —
  free tier, first load can take up to a minute."**
- `FetchErrorNotice` — red `role="alert"` banner with the error message and
  a **Retry** button.
- `SkeletonTableRows` / `SkeletonCards` — `animate-pulse` placeholders in
  the existing Tailwind style.

## Pages changed

### `app/dashboard/page.tsx` (Bid Intelligence Dashboard; also served at `/` and `/bids`)
- All GETs (SLA, facets, preview ×12-location fan-out, preview-grouped,
  top-movers, summary, watchlists, watchlist preview) routed through
  `fetchResilient`; the two POSTs (create watchlist, create alert rule)
  use it with `retries: 0`. Local `readFailure` now delegates to the
  shared `readApiFailure`.
- The indefinite **"Refreshing..."** is gone: the panel header now shows a
  bounded "Loading…" that becomes "Waking the API…" after 3s, plus the
  page-level `WakingApiNotice` while any dashboard load is slow.
- Errors render as `FetchErrorNotice` with a Retry button that re-runs
  both meta and market loads (previously a bare red line of text).
- Skeleton rows (13 cols) in Live Price Preview, skeleton cards in Top
  Bids by Delivery Month and Top Basis Movers, and skeleton rows + waking
  notice + retryable error for the Watchlist Run-Now Preview — panels no
  longer sit silently empty during a cold start.
- A11y: `aria-label` on the location/company/region/sort/date filter
  controls, watchlist select/name input, and alert metric/operator/
  threshold controls; `aria-pressed` on the commodity tab buttons.

### `app/dashboard/open-alerts-panel.tsx`
- Loads and status PATCHes routed through `fetchResilient` (PATCH with
  `retries: 0`).
- Refresh button now reads "Loading…" while running; slow loads show the
  waking notice; failures show `FetchErrorNotice` with Retry; skeleton
  rows while the first load is in flight.

### `app/sources/page.tsx`
- `loadData` (runs, sources, SLA, alerts, facets, canonical coverage),
  priority loads, and all mutations routed through `fetchResilient`
  (mutations `retries: 0`). `loadData` now tracks a `dataLoading` state.
- Previously the page had **no** initial-load state at all and its only
  error text was buried inside the manual-ingestion form. Now: a
  "Loading source data…" status, the waking notice on slow loads, and a
  top-level `FetchErrorNotice` with Retry directly under the header.
- Metric cards show "…" instead of misleading `0`s while the SLA loads;
  skeleton rows in the coverage, source-adapter, ingestion-runs, and
  alerts tables.
- A11y: company `<select>` and priority-keys `<textarea>` labels are now
  associated via `htmlFor`/`id` (they were unassociated text before).

### `app/prototypes/price-finder/page.tsx` (market search)
- Best-bids and market-search GETs (including the radius fallback retry)
  routed through `fetchResilient`. Search logic split into
  `performSearch()` so it can be re-run without a form event.
- Submit button shows "Waking the API…" on slow searches and the waking
  notice appears under the form.
- The API-unreachable state (which shows clearly-labelled example rows)
  now has a **Retry search** button instead of being a dead end.

### `app/best-bids/page.tsx` (server-rendered market page)
- Fetch routed through `fetchResilient` (timeout + one retry now apply
  server-side too).
- Failure is no longer indistinguishable from empty: a failed load renders
  a "Could not load best bids" panel explaining the API may be waking,
  with a Retry link, instead of the "No best bids yet" empty state.

### Research pages (server-rendered; they do not fetch client-side)
All routed through `fetchResilient`, and each fetch helper now returns a
`failed` flag so an unreachable API is not reported as "no data ingested
yet". On failure each page shows a "Could not load … — the API did not
respond (it may be waking up…)" message with a Retry link:
- `app/research/page.tsx` — banner when any of the five report fetches
  failed ("counts below may be incomplete").
- `app/research/wasde/page.tsx`
- `app/research/crop-progress/page.tsx`
- `app/research/grain-stocks/page.tsx`
- `app/research/export-sales/page.tsx`
- `app/research/commitments-of-traders/page.tsx`

### `app/globals.css`
- Added a global `:focus-visible` outline (brass, 2px, offset) — the
  codebase had no focus style pattern, so keyboard focus was previously
  invisible on most controls. Mouse interaction is unaffected.

## Not changed
- API shapes, props, endpoints, env vars (`NEXT_PUBLIC_API_URL`,
  `NEXT_PUBLIC_ORG_ID`, …), and the org/role header behaviour in
  `lib/api.ts` are untouched.
- Other client pages (alerts, watchlists, quotes, basis, futures, today,
  etc.) still use plain `fetch`; they can adopt `fetchResilient` +
  `fetch-states` incrementally — the helpers were designed as drop-in
  replacements for exactly that.

## Verification
- `npm run build` in `apps/web`: **passes** (33 routes; only pre-existing
  `react-hooks/exhaustive-deps` lint warnings, unchanged in kind).
- Grep confirms no raw `fetch(` and no "Refreshing" string remain in any
  page touched above.
