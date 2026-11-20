# GrainBids — Production Runbook

How GrainBids runs in production, how deploys work, and what to do
when something breaks. Written 2026-11-20 (night queue) from the
2026-11-19 launch and the OOM incident that followed it.
Environment variables are listed **by name only** — values live in
the Render / Vercel dashboards and the Secure Vault, never in git
or in this document.

## What runs where

| Piece | Platform | URL | Source |
|---|---|---|---|
| API (FastAPI) | Render free web service `grainhub-api` | https://grainhub-api.onrender.com | repo `apz100/GrainHub`, branch `master`, root `GrainBids/grainbids/apps/api` |
| Web (Next.js) | Vercel project `grainhub-web` | https://grainhub-web.vercel.app | same repo/branch, root `GrainBids/grainbids/apps/web` |
| Database | Supabase Postgres (Adam's existing GrainBids project, us-east-1, free tier) | — | reached from Render via the Supabase **session pooler** host |

Production domain (owned, DNS not yet changed): grainbids.com —
plan is web at `grainbids.com`, API at `api.grainbids.com`. See
`docs/decisions/grainbids-dns-checklist.md`.

## Deploy flow

1. Merge to `master` and push to GitHub. **That is the deploy.**
   Both Render and Vercel auto-deploy on push to `master`.
2. Render build: `pip install -r requirements.txt`.
3. Render start command runs migrations on every boot:
   `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   `alembic upgrade head` is idempotent; Render's free plan has no
   separate release step, so migrations ride the boot. The
   blueprint is `render.yaml` at the repo root.
4. Vercel builds the Next.js app from its root directory; the API
   URL is baked in at build time via `NEXT_PUBLIC_API_URL`.
5. Verify with the checklist below — a green deploy is not proof
   the new code is serving.

There is no staging environment. Anything merged to `master` is
production within a few minutes.

## Environment variables (names only)

**Render (API service → Environment tab):**

| Name | Notes |
|---|---|
| `DATABASE_URL` | Secret. Must use the Supabase **session pooler** URI — Render is IPv4-only and cannot reach the direct (IPv6) Supabase host; that mismatch failed deploy attempt 2 on launch night. A bare `postgresql://` scheme is rewritten to the psycopg v3 driver in code. |
| `API_CORS_ORIGINS` | Must include every web origin that calls the API (currently the Vercel URL; add the custom domain when DNS lands). |
| `NASS_API_KEY` | Secret. USDA NASS Quick Stats key (Adam's, entered via dashboard). |
| `FAS_DATA_GOV_API_KEY` | Secret. data.gov key for USDA FAS PSD. |
| `APP_ENV` | `production`. |
| `ALLOW_IMPLICIT_ORG` | `false` in production. |
| `API_ENABLE_DOCS` | `false` in production. |
| `PYTHON_VERSION` | Pinned in `render.yaml`. |
| `PORT` | Provided by Render. |

Not set (parked with the LLM decision): `GRAINHUB_LLM_API_KEY` /
`OPENAI_API_KEY`. The Advisor `/ask` endpoint returns 501 until a
provider is chosen and a key is set.

Dashboard quirk learned on launch night: after editing variables,
the **"Save, rebuild, and deploy"** button sits at the bottom
right of the Environment Variables table (left of Cancel) — saving
is what triggers the rebuild; there is no separate apply step.

**Vercel (web project → Settings → Environment Variables):**

| Name | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | The Render API base URL. |
| `NEXT_PUBLIC_ORG_ID` | The single org in the production DB. |
| `NEXT_PUBLIC_USER_ROLE` | Role the public web shell presents as. |
| `NEXT_PUBLIC_USER_EMAIL` | Referenced in code; set alongside the role if used. |

`NEXT_PUBLIC_*` values are public by design (they ship to the
browser) — never put a secret behind one.

## Free-tier facts (the constraints that bite)

- **API memory: 512 MB.** The binding constraint. An endpoint that
  loads unbounded rows — especially full ORM objects with raw JSON
  payloads — will OOM the instance (see the incident below). New
  list/preview endpoints must bound their loads in SQL (limits,
  column-only queries, `DISTINCT ON` / window functions) and carry
  a volume test.
- **The API sleeps when idle.** First request after a quiet period
  cold-starts (observed ~50 s or more). The web app's shared fetch
  has a cold-start timeout + one retry and shows an honest
  "Waking the API" state. Keep-warm pingers are decided **off**
  (`docs/decisions/keep-warm.md`).
- **750 free instance-hours/month** on Render — one always-on free
  service fits inside it; extra services or cron jobs change the
  math (Render cron is a paid add-on; see
  `docs/decisions/render-cron-proposal.md`).
- **Supabase free: 500 MB database** (~318 MB used at launch).
  Watch growth once server-side ingestion is scheduled.
- Vercel free tier serves the web app; builds run on push.

## Health endpoints

- `GET /health/live` → `{"ok": true, "env": "production"}` —
  process is up. Render's own health check uses this path.
- `GET /health/ready` → database `"connected"` — process up **and**
  DB reachable. This is the meaningful "is production healthy"
  probe.

## Incident response — the 2026-11-19 OOM night

**What happened.** The basis tracker endpoint loaded every price
pair in the database into Python, including full raw payloads. On
the 512 MB free instance that is fatal: the instance ran out of
memory and died mid-request. It happened three times that evening
(22:37, 22:51, 22:53 EST) and again at 23:46, right after the
marathon merge deployed — the first post-deploy tracker call got a
**proxy 502**, the app logs showed **no request line for it at
all** (only health checks), and Render Events recorded the cause.
The instance auto-recovered each time within about a minute.

**Signatures of an OOM:**

- Clients see `502` from Render's proxy (the app never responds).
- Render dashboard → service → **Events**: "Ran out of memory
  (>512 MB)" followed by a restart.
- **Logs** show surrounding requests but *no log line for the
  request that died* — it was killed before it could log. A missing
  request line plus an Events OOM at the same minute is the
  fingerprint.
- `/health/live` and `/health/ready` come back on their own after
  the restart; no manual intervention is needed for the instance
  itself.

**Where things live in the Render dashboard:** **Logs** (app
stdout/stderr), **Events** (deploys, restarts, OOMs — the incident
timeline), **Deploys** (history, manual deploy, redeploy an older
commit), **Environment** (variables), **Settings** (build/start
commands, health-check path).

**Response steps:**

1. Check **Events** first — confirm OOM vs a deploy failure vs a
   crash loop, and note the timestamp.
2. Check **Logs** around that timestamp. If the suspect request
   has no line, it died mid-load (memory), not with an app error.
3. Stop calling the suspect endpoint. The instance recovers by
   itself; repeated calls just re-kill it.
4. Fix on a branch: bound the load in SQL, add a real-DB volume
   test that counts materialized rows (the pattern in
   `tests/test_volume_bounded_loading.py`), run the full suite,
   merge, then verify with the checklist below — probing a new
   route first.
5. Rollback, if needed: **Deploys** tab → redeploy the previous
   commit. Note migrations only move forward on boot
   (`alembic upgrade head`); old code against a newer schema is a
   risk to weigh, not an automatic safe state.

## Deployment verification checklist

Learned the night a "successful" deploy still served a fatal
endpoint. In order:

1. **Deploy finished?** Render **Deploys/Events**: the new deploy
   is live, no failed build, migrations ran in the boot log.
2. **Health:** `GET /health/live` → ok; `GET /health/ready` →
   database connected. (Allow for a cold start if the service was
   asleep — retry once after ~60 s before concluding anything.)
3. **Prove the NEW code is live:** call a route that only exists
   in the new code (a newly added endpoint, or one whose response
   shape changed). A 200 from an old route proves nothing — the
   old instance may still be serving. On 2026-11-19 the FAS PSD
   route served this purpose after the marathon merge.
4. **Only then test the suspect/fixed endpoint** — once, and watch
   the result.
5. **Re-check health and Events after the test:** health still
   green, no "Ran out of memory" event. An endpoint that answers
   200 but OOMs the instance a minute later is not fixed.
6. **Web:** load the Vercel URL, confirm the title/branding and
   that one data-backed page renders real rows (an empty first
   paint during an API cold start is the known free-tier
   behaviour, not a data gap — reload after the API wakes).

## Standing operational notes

- **Ingestion is not scheduled server-side yet.** Collectors can
  run from the server (USDA keys are set), but the schedule is
  Adam's open decision: GitHub Actions ($0, workflow prepared but
  inert) vs Render cron ($2/mo). Until then, production prices are
  only as fresh as the last manual run. See
  `docs/decisions/render-cron-proposal.md`.
- **Production sources are not seeded yet.** The registry's
  adapters are code; the DB needs
  `python -m app.jobs.seed_sources` (dry-run first) to create the
  source rows, and the legacy Windows-path source retired. See
  `docs/decisions/source-registration-rollout.md` (~10 min).
- **Newsletter delivery is OFF** by design; the generator runs in
  dry-run only.
- **Parked, do not touch:** the Barchart/DTN licensed-feed decision
  (the `andersons` adapter stays toggled off; do not probe its
  legacy host) and the LLM provider decision.
