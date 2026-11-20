# Morning report — overnight run, Thu 2026-11-19 → Fri 2026-11-20

**Branch:** `overnight/2026-11-20` (from master `ee3c3d0`, 7 commits,
pushed to GitHub). **Nothing merged to master. Nothing bought,
enabled, or created outside the repo. Total spend: $0.**
Production (master) is untouched and still live.

**Test gate:** full API suite **731 passed / 5 skipped / 0 failed**
(baseline 717 + 14 new tests). Web build green. Detail log:
`docs/overnight/2026-11-20-run-log.md`.

---

## The headline: the production basis tracker is broken (found, fixed, not yet deployed)

Phase 1's smoke test caught a real production bug. `GET
/api/basis/tracker` **kills the API instance** — reproduced 3/3
(502 after ~16 s, instance dead for minutes afterwards), while every
other endpoint stays healthy. Root cause, two bugs in one loader:

1. It loaded **every stored price pair for the org, unbounded**,
   including each snapshot's full raw payload — enough to OOM the
   512 MB free instance.
2. Its row check (`isinstance(item, tuple)`) is false for real
   database rows, so it **silently threw away every row it loaded**.
   The endpoint only ever worked against fake test data; against a
   real database it could never have returned a ranked row.

Fixed on the branch with regression tests that use a real database
session (the old tests couldn't see bug 2 by construction). **It
needs your merge to reach production** — after merging, one call to
`/api/basis/tracker` should return 200 with ranked rows; that's the
verification step.

## Phase by phase

### Phase 1 — Deployment smoke: DONE (10/11 pass)
All §5 checks run against the live URLs: health ×4, SLA, summary,
facets, price preview (real rows), source-health, alert rules +
recent, market search (250 corn rows), market-report preview (renders
with the GrainBids name), web 200. Only item 7 (basis tracker) fails
— see headline. Full table in the run log.

### Phase 2 — Ingestion preparation: DONE (prepared, nothing enabled)
- **2a. One-command seed job** — `python -m app.jobs.seed_sources`
  registers the registry adapters as `Source` rows for an org
  (idempotent, toggle-aware, `--dry-run`, `--scope pilot|all`).
  6 new tests. The morning step is literally one command.
- **2b. Scheduling proposal** (`docs/decisions/render-cron-proposal.md`):
  Render Cron Jobs would cost **exactly $2.00/month** (2 jobs × $1
  minimum; the $0.00016/min rate is noise at realistic runtimes) —
  and Render cron is **UTC-only**, so it can't hold 08:00/15:00
  Toronto through DST. **Recommended instead: GitHub Actions, $0**
  (public repo), native `America/Toronto` timezone, runs the exact
  job commands. The workflow file is prepared on the branch with its
  schedule **commented out** — inert until you approve and add repo
  secrets (`DATABASE_URL` + the two USDA keys would live in GitHub
  secrets too; the paper flags that honestly).
- **2c. DNS checklist** (`docs/decisions/grainbids-dns-checklist.md`):
  exact records for grainbids.com → Vercel (A record, value from the
  Vercel dashboard), www → Vercel (CNAME, project-specific target),
  api.grainbids.com → Render (CNAME `grainhub-api.onrender.com`).
  Dashboards first, DNS second, env vars last. **No free-tier
  blocker**: Render Free includes custom domains + TLS (2 included
  on Hobby), Vercel Hobby allows 50/project. Cost $0. Nothing entered.

### Phase 3 — Research silo real data: DONE
- **FAS PSD world data is wired.** Live probing proved the legacy
  `/api/psd/worldData` endpoint is **dead** (404 in every form) and
  found the real shape: `GET /api/psd/commodity/{code}/world/year/
  {marketYear}` (corn 2026 → 15 rows; decoded world corn production
  1,291,550 thousand MT, ending stocks 281,938 — internally
  consistent with 2025). New code: `fetch_fas_psd_world()`, runtime
  attribute/unit lookups (third-party attribute tables do **not**
  match the live API — never hardcode them), and a decoder,
  `parse_fas_psd_rows()`. Also fixed: `fetch_fas_psd()` claimed to
  return PSD data but only ever returned the commodity catalogue,
  unfiltered (the server ignores the filter param) — it now filters
  client-side and says what it is. 6 new tests, HTTP mocked, no keys
  anywhere near code or fixtures. The connector doc was corrected too.
- **NASS verified, no change needed:** counts CORN 2026 = 20,778;
  the collector's exact query returns 20,778 records; every field
  the parser reads matches the live payload (incl. the 179.6 BU/ACRE
  national corn yield).
- Not done (scaffold, by design): no API route exposes the new PSD
  data yet — that's wiring for a future cycle, noted in the findings.

### Phase 4 — Collector coverage: BLOCKED (environment), static checks done
The leftover checks all need a real browser render, and **this
sandbox cannot render**: Chromium was installed, but the VM's
authenticated egress proxy refuses Chromium tunnels (5
configurations, all `ERR_TUNNEL_CONNECTION_FAILED`) while
curl/python reach the same hosts fine. Static re-verification
instead, all tonight: the FMN filtered Winchester view
(`location_filter=2523`) still embeds **no** bid rows (1
`writeBidRow` definition vs 454 calls on the default view) — Cycle 3
finding unchanged, render question still open; all 8 Ontario
collector pages return HTTP 200; Al-Corn and Sunrise DTN fetches
still honestly return 0 rows without a browser (Al-Corn's URL now
redirects to the non-www host — followed automatically, not a
breakage). No adapter code changed: nothing was proven to have
changed shape. The render checks remain open for any machine with
direct internet (e.g. yours).

### Phase 5 — Decision papers: DONE (all in `docs/decisions/`)
- **Currency column** — recommend Option A: store currency per price
  row (migration 0020), backfill only unambiguous sources. $0.
- **Email-bid endpoint auth** — verified the endpoint is parse-only
  (writes nothing, cannot poison prices); recommend adding the
  standard admin header for consistency. $0 either way; leaving it
  public is also safe.
- **Keep-warm** — recommend **do nothing ($0)** for now. 24/7 warm
  costs 720–744 of the 750 free instance-hours/month (6 h headroom
  in a 31-day month; exhaustion = suspension, worse than sleep).
  If warm is ever wanted: UptimeRobot free. Paid instance: $7/month.
- **Source-registration rollout** — dry-run → seed → verify → retire
  the dead Windows-path source → first small poll. ~10 minutes, $0.

## Morning decision list (each with its cost)

| # | Decision | Cost | My recommendation |
|---|---|---|---|
| 1 | Merge `overnight/2026-11-20` to master (deploys the basis fix + seed job + FAS code) | $0 | **Yes** — then verify `/api/basis/tracker` returns 200 |
| 2 | Run the seed job against prod (dry-run first) + retire the Windows-path source | $0 | **Yes** (rollout paper, steps 2–5) |
| 3 | Scheduling: approve the GitHub Actions workflow (add 3 repo secrets, uncomment schedule) — or Render cron | **$0** (Actions) / **$2.00/mo** (Render) | Actions at $0. **Render cron costs money and needs your explicit OK — it was NOT created** |
| 4 | Paste `NASS_API_KEY` + `FAS_DATA_GOV_API_KEY` into Render env (your step — I can't read them back) | $0 | Yes, whenever convenient; collectors stay idle until then |
| 5 | grainbids.com DNS (checklist prepared, nothing entered) | $0 | Whenever you're ready; ~15 min following the checklist |
| 6 | Currency Option A (migration 0020) | $0 | Approve for a future cycle |
| 7 | Email-bid admin header | $0 | Approve for a future cycle (low urgency) |
| 8 | Keep-warm pinger | $0 | Skip for now (paper explains the instance-hours risk) |

## Commits on `overnight/2026-11-20`

- `b25e57f` One-command seed job for registry adapters (Phase 2a)
- `23f0351` FAS PSD world data with the verified live endpoint shape (Phase 3)
- `59bc9fe` + `0bba68d` Run log (Phases 1 + 4)
- `aee3f3e` Source-registration rollout paper (Phase 5)
- `d6a2fd0` Decision papers + prepared ingestion workflow (Phases 2b, 2c, 5)
- `3f93785` Basis endpoints fix: real-DB row bug + unbounded load (Phase 1)

## Guardrail compliance

Zero spending (no purchases, no paid tiers, no Render cron jobs
created, no domains touched) · no merges to master · no vendor
contact (Barchart/DTN untouched; the Andersons DTN host was not
probed) · LLM still parked · North Gower treated as one ordinary
source, nothing featured · no secrets in git or in any report (USDA
probing went through the credential layer; keys never printed) ·
everything above is labelled done / scaffold / blocked with the
evidence in the run log and papers.
