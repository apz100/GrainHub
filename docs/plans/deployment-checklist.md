# GrainHub — Deployment Checklist

**Status:** checklist only — no deployment was performed, no config was
changed, no secrets are in this file. Written 2026-11-19 (Cycle 6).
Production baseline: **Vercel (web) + Render (API) + Supabase
(Postgres)**, per `GrainBids/grainbids/README.md` ("Production baseline
(Vercel + Render + Supabase)").

**Read this first — the branch rule.** No cycle branch
(`overnight/grainhub-cycle-1` … `overnight/grainhub-cycle-6`) has ever
been merged to `master`. **Deployment is from `master` only.** Do not
deploy a cycle branch. Before any deploy, the cycle branches must be
reviewed by Adam and merged to `master` (or the wanted commits
cherry-picked) — a deploy from an unmerged branch would ship
unreviewed code, including scaffolds and stubs listed in the cycle
reports. If in doubt, stop and ask Adam; never deploy to work around
the review step.

**Scope of this checklist:** the first production deploy of the
`master` branch as it stands after the cycle merges, plus every later
re-deploy. It covers env vars, migrations, the ingestion schedule,
post-deploy health checks, and rollback. It does not cover DNS /
domain changes, pricing, or vendor contracts — those are Adam
decisions (see §7).

## 0. Before you start — decisions and keys only Adam can supply

Do not start the deploy until each item below is resolved. Keys are
**env-only: obtain from Adam, never commit, never paste into a doc,
chat log, or ticket**. `.env.example` files are the only place a key
name may appear in the repo.

| # | Item | Status / note |
|---|---|---|
| 1 | Cycle branches reviewed and merged to `master` | **Not done** — see the branch rule above. Nothing deploys until this happens. |
| 2 | `NASS_API_KEY` (USDA NASS Quick Stats, free key by email) | Needed for Research collectors; without it NASS endpoints return a clear "key required" error, they do not fail the deploy. Obtain from Adam. |
| 3 | `FAS_DATA_GOV_API_KEY` (free data.gov key) | Needed for USDA FAS PSD collectors; same key-gated behaviour as NASS. Obtain from Adam. |
| 4 | `GRAINHUB_LLM_API_KEY` (or `OPENAI_API_KEY`) | Needed for Advisor `/ask`; without it the assistant stays 501 by design. Obtain from Adam — and only after he has chosen the LLM provider. |
| 5 | Barchart / DTN licensed feed decision | **Parked 2026-11-19 at Adam's request.** Do not chase it, do not contact the vendors, do not probe the Andersons legacy DTN host, do not spend cycles on pricing/licensing. The plug-in spec stays current (`docs/plans/barchart-dtn-integration-design.md` §8 checklist) and a feed can be added later by config + one adapter with no route changes (proven by `tests/test_licensed_feed_plugin.py`). No feed is wired today; do not deploy assuming one exists. |
| 6 | ERP choice (Agvance recommended first, Agris second, AgTrax third) | Elevator Ops only; not a deploy blocker. |
| 7 | eSign provider | Elevator Ops only; eSign is a stub today. Not a deploy blocker. |
| 8 | Hosting / domain decision | Keep Vercel + Render + Supabase (the baseline), or change? Confirm the production domains before setting `API_CORS_ORIGINS` and `NEXT_PUBLIC_API_URL`. |

## 1. Supabase (Postgres) — set up first

1. In the Supabase dashboard, create (or confirm) the project and copy
   the Postgres connection string. That string becomes `DATABASE_URL`
   for the API — paste it into Render as an env var, never into git.
2. Confirm the database is reachable from Render (same project/region
   as the API service where possible; if the connection string uses a
   pooler host, use exactly the host Supabase shows — do not guess one).
3. Do **not** create tables by hand. Schema comes only from the Alembic
   chain in §3.

## 2. Environment variables

### 2a. Render — API (`apps/api`)

Required (deploy fails or refuses to start without these):

| Variable | Value / note |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | Supabase Postgres URL (from §1). The app raises at startup if this is missing when `APP_ENV=production`. |
| `ALLOW_IMPLICIT_ORG` | `false`. The app raises at startup if this is not `false` in production. Local dev uses `true`; production must never. |
| `API_CORS_ORIGINS` | Comma-separated production origins, e.g. `https://grainbids.com,https://www.grainbids.com,https://<your-vercel-domain>`. The app raises at startup if no origin is set in production. Replace `<your-vercel-domain>` with the real Vercel domain from §2b — do not leave the placeholder in. |
| `API_ENABLE_DOCS` | `false` in production (disables Swagger/OpenAPI). |

Optional, but set them now if the feature is wanted (all default off /
empty — leaving them unset is safe, the feature just stays off):

| Variable | Value / note |
|---|---|
| `NASS_API_KEY` | Free USDA NASS key — **obtain from Adam, env-only, never commit**. |
| `FAS_DATA_GOV_API_KEY` | Free data.gov key for FAS PSD — **obtain from Adam, env-only, never commit**. |
| `GRAINHUB_LLM_API_KEY` | LLM key for Advisor `/ask` — **obtain from Adam, env-only, never commit**. (`OPENAI_API_KEY` is also accepted by the advisor service; prefer the `GRAINHUB_` name so the key's purpose is obvious.) |
| `ALERT_EMAIL_ENABLED` | `false` unless alert email is wanted. If `true`, also set `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO`, `ALERT_SMTP_HOST`, `ALERT_SMTP_PORT` (587), `ALERT_SMTP_USERNAME`, `ALERT_SMTP_PASSWORD` (env-only), `ALERT_SMTP_USE_TLS=true`. |
| `MARKET_REPORT_EMAIL_ENABLED` | `false` unless weekly market-report delivery is wanted. If `true`, also set `MARKET_REPORT_EMAIL_FROM`, `MARKET_REPORT_UNSUBSCRIBE_URL`, and reuse the `ALERT_SMTP_*` values. Delivery is deduped per subscriber + ISO week. |
| `MARKET_REPORT_REGION` | e.g. `Eastern Ontario` (default in `.env.example`). |
| `MARKET_REPORT_PUBLIC_URL` | Public site URL, e.g. `https://grainbids.com`. |

### 2b. Vercel — web (`apps/web`)

| Variable | Value / note |
|---|---|
| `NEXT_PUBLIC_API_URL` | The Render API's public URL, e.g. `https://<your-api-domain>`. This is the only required web env var. It is public by design (it is baked into the browser bundle), so it must be the API's public URL and nothing secret. |
| `NEXT_PUBLIC_ORG_ID` | Default org id for the web app (see `apps/web/.env.example`). |
| `NEXT_PUBLIC_USER_ROLE` | Default role for the web app (see `apps/web/.env.example`). |

No API keys, database URLs, or SMTP credentials go in Vercel env vars
— the web app never talks to the database or to USDA/LLM providers
directly; everything goes through the API.

### 2c. After setting env vars

- In Render, confirm the API service redeploys (env var changes trigger
  a redeploy) and the deploy log shows a clean start with no
  `DATABASE_URL` / `ALLOW_IMPLICIT_ORG` / `API_CORS_ORIGINS` startup
  error.
- In Vercel, confirm the web build succeeds. A web build failure does
  not affect the API, and vice versa — check both dashboards.

## 3. Database migrations (Alembic)

Migrations live in `GrainBids/grainbids/apps/api/alembic/versions/`.
The chain was verified linear on 2026-11-19 (Cycle 7, head `0019`):

| Revision | Down-revision | Contents |
|---|---|---|
| `0015` | `0014` | Market-report delivery |
| `0016` | `0015` | Farm profiles (Advisor silo) |
| `0017` | `0016` | Elevator Ops |
| `0018` | `0017` | Research reports |
| `0019` | `0018` | Basis-threshold alert fields |

So the tail of the chain is `0014 → 0015 → 0016 → 0017 → 0018 → 0019`, single
head `0019`, no branches. **Verify this yourself before migrating**
(the chain can change when a new cycle lands):

1. From `apps/api`, with `DATABASE_URL` pointing at the Supabase
   database, run `alembic current` — note the revision the database is
   on (a fresh database reports nothing applied).
2. Run `alembic heads` — expect exactly one head, `0019`. If there are
   two heads, stop: the chain has branched and needs a merge revision
   before any deploy.
3. Run `alembic upgrade head` — applies every unapplied migration in
   order, ending at `0019`.
4. Re-run `alembic current` — it must now report `0019`. If it does
   not, stop and read the migration error; do not deploy the API
   against a half-migrated database.
5. Never run `alembic downgrade` on production unless Adam has
   explicitly approved a rollback plan for that migration (see §6 —
   migrations are forward-only by default).

## 4. Ingestion schedule — 08:00 and 15:00 America/Toronto

Daily ingestion is **not** part of the web/API deploy; it is a
scheduled job that must exist separately, or no new prices will ever
appear after deploy.

1. Use the host scheduler / cron (Render Cron Jobs or the equivalent
   for wherever the job runs) with two runs a day: **08:00 and 15:00
   America/Toronto**. Use the `America/Toronto` timezone on the
   schedule itself — do not convert to UTC by hand (daylight saving
   changes the UTC offset).
2. Job command: `python -m app.jobs.daily_source_ingestion` (run from
   `apps/api`, with the same `DATABASE_URL` and env as the API).
3. For Render-hosted ingestion, sources must use stable public HTTPS
   file URLs — local `P:\...` paths will not resolve on Render.
   (See the README section "Scheduling" and
   `infra/scripts/register-daily-ingestion-task.ps1` for the local
   Windows Scheduled Task equivalent.)
4. After the first scheduled run, check the ingestion run in the app
   (`/api/source-health` / the source-health page): a run should exist
   with a parse-success count. No run at all means the schedule is not
   firing — fix the schedule, not the API.
5. Weekly market report (separate, optional): preview any time with
   `python -m app.jobs.weekly_market_report` (prints the report and
   subscriber count; sends nothing). Delivery only when
   `MARKET_REPORT_EMAIL_ENABLED=true` and the `--send` flag is passed;
   schedule it once weekly after a successful ingestion cycle.
6. **Schedule the registry poller too — the file job above does not
   poll any registry adapter (Cycle 19 audit, Cycle 20 note).** The
   08:00/15:00 cron in step 2 runs `python -m
   app.jobs.daily_source_ingestion`, which ingests file sources only:
   it reaches **0 of the 93 registry adapters**. To poll the seeded
   adapters on schedule, add a second cron job (same times, same
   `America/Toronto` timezone, same working directory `apps/api` and
   env) with the command `python -m app.jobs.poll_sources`. That runs
   one pass over every due, active, automated `Source` row
   (`app/jobs/poll_sources.py` → `poll_due_sources`, one-shot by
   default; `--loop --sleep-seconds 60` runs it continuously instead).
   Without this second job, seeded adapters are never polled and
   their prices never refresh, no matter how often the file job runs.
   Before the first poller run, confirm at least one `Commodity` row
   exists — the poller exits with an error if the commodity table is
   empty. This is a deployment decision, not a code change: no cron
   or deployment config was changed in Cycle 20, only this note.

## 5. Post-deploy health checks

Run these in order, from a browser or `curl`. Replace
`<api-domain>` / `<web-domain>` with the real domains.

| # | Check | Expected |
|---|---|---|
| 1 | `GET https://<api-domain>/health/live` | `{"ok": true, "env": "production"}` — liveness, no DB needed. |
| 2 | `GET https://<api-domain>/health/ready` | `{"ok": true, ...}` — readiness, checks the DB. **503 means the database is unavailable**: check `DATABASE_URL` and Supabase before anything else. |
| 3 | `GET https://<api-domain>/api/health/db` | `{"ok": true, "database": "connected", ...}` (503 on DB error). |
| 4 | `GET https://<api-domain>/health` | `{"ok": true, "env": "production"}`. |
| 5 | Scripted smoke test: `infra/scripts/smoke-test.ps1 -ApiBaseUrl https://<api-domain> -WebBaseUrl https://<web-domain> -CheckWeb -OrgId <org-uuid> -UserRole admin` | Exit 0. (Windows/PowerShell; see README "Health checks".) |
| 6 | Open the web app at `https://<web-domain>` | Pages load; `/bids` shows data only if ingestion has run (§4) — an empty table before the first ingestion run is expected, not an error. |
| 7 | `GET /api/basis/tracker` (with org headers) | Returns ranked/unranked rows or an honest empty state; `currency: null` is expected until the currency-column decision is made (§7). |
| 8 | `GET /api/source-health` | One row per source; sources with no ingestion data report `unknown`, never "healthy". |
| 9 | `GET /api/alerts/rules` and `GET /api/alerts/recent` | Return the org's rules / recent alerts (empty lists are fine on a fresh deploy). |
| 10 | `GET /api/market-search?commodity=Corn` (with org headers) | Returns search results or an honest empty state. |
| 11 | Newsletter preview only: `GET /api/market-report/preview` (admin) | Renders a preview; **do not** run a `--send` delivery as a deploy check. |

If check 1 fails, the API did not start — read the Render deploy
log. If checks 2–3 fail but 1 passes, the problem is the database
connection, not the code. If 1–4 pass but 5–11 fail, check
`API_CORS_ORIGINS` (web origin missing) and the org headers.

## 6. Rollback

- **Code rollback:** redeploy the previous `master` commit in Render
  (Render keeps prior deploys; redeploy the last known-good one) and
  the previous Vercel deployment. Both are one-click in their
  dashboards — no git force-push, no branch surgery. Note the commit
  hash you rolled back from, so the bad deploy can be investigated on
  its branch.
- **Database rollback:** Alembic migrations are **forward-only by
  default**. There is no automatic `downgrade` step in this checklist,
  and running one unreviewed can destroy data. If a deploy must be
  rolled back *and* a migration in that deploy is the problem, stop
  and get Adam's explicit approval for the specific downgrade
  (`alembic downgrade <revision>`) after confirming what data that
  migration added or changed. Rolling the code back without rolling
  the database back is safe for additive migrations (new tables /
  columns); the old code simply ignores them.
- **Ingestion rollback:** if a bad ingestion run wrote bad rows, do
  not delete rows by hand. Record the run id and the source, and fix
  forward with a corrected ingestion run — deletion is out of scope
  for this checklist.
- **Never roll back by deploying a cycle branch.** Rollback target is
  always a previous `master` deploy.

## 7. Known gaps that are NOT deploy blockers (but Adam still owns them)

Carried from Cycles 1–5; none of these stops a deploy, because every
one fails honestly (key-gated error, 501, `null` price, `unknown`
status) instead of failing silently:

- NASS / FAS keys, LLM provider + key (see §0). Barchart/DTN is
  parked at Adam's request (2026-11-19) — not a gap and not a
  blocker; see §0 row 5.
- Futures strip + ICE canola desk return contract structure with
  prices `null` until a licensed feed is wired.
- Advisor `/ask` is 501; eSign is a stub; no ERP sync, no payments.
- Currency is not stored on normalized price rows — basis / best-bid
  responses report `currency: null` with a data-quality note.
- Email-bid endpoint is public by default (admin-only is a one-line
  change if Adam wants it).
- CI workflow (`.github/workflows/api-tests.yml`) is written but
  unpushed — the `gh` token lacks `workflow` scope; Adam needs to
  re-authenticate `gh` or add the file via the GitHub web UI.
- FMN filtered view and Mapleview still need a live-browser
  Playwright render check.

## 8. Deploy sign-off (copy into the deploy note)

- [ ] §0: cycle branches reviewed + merged to `master`; keys/decisions recorded.
- [ ] §1: Supabase project confirmed; `DATABASE_URL` set in Render only.
- [ ] §2: Render + Vercel env vars set; no secrets in git.
- [ ] §3: `alembic heads` = single head `0019`; `alembic current` = `0019` after upgrade.
- [ ] §4: Ingestion scheduled 08:00 + 15:00 America/Toronto; first run verified in source health. Poller job (`python -m app.jobs.poll_sources`) scheduled alongside the file job (§4 step 6), or the decision not to schedule it recorded.
- [ ] §5: Health checks 1–11 pass (or each failure recorded with its cause).
- [ ] §6: Previous known-good Render + Vercel deploys identified for rollback.
- Deployed by: ______  Date/time (America/Toronto): ______  Master commit: ______
