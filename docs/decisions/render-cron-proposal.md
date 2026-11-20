# Proposal: Scheduled ingestion for GrainBids — Render Cron Jobs vs GitHub Actions

**Status:** DRAFT for Adam's decision — nothing has been created, enabled, or bought.
**Date:** 2026-11-19 (America/Toronto). All prices in USD, read from official pages on 2026-11-19 (citations inline).
**Zero-spend guardrail:** the $0 option is presented first and recommended. The paid option is priced exactly so it can be approved or rejected on numbers, not vibes.

---

## 1. What needs scheduling

Per `docs/plans/deployment-checklist.md` §4, two separate jobs must run **twice a day, 08:00 and 15:00 America/Toronto**, from `apps/api`, with the same env as the API (`DATABASE_URL`, USDA keys, etc.):

| Job | Command | What it does |
|---|---|---|
| A — file ingestion | `python -m app.jobs.daily_source_ingestion` | Ingests file sources only. Reaches **0 of the registry adapters** on its own. |
| B — registry poller | `python -m app.jobs.poll_sources` | One pass over every due, active, automated `Source` row (the seeded adapters). Exits with an error if no `Commodity` row exists. |

Both commands are one-shot (they run and exit) — `poll_sources` only loops if passed `--loop`, which must **not** be used with a scheduler. Without both jobs, no new prices ever appear after deploy.

**Planning assumption for runtimes:** 2–10 minutes per run is used throughout. Job B polls every due adapter over the public internet, so it is the more likely of the two to sit at the top of that range. Actual runtimes are unknown until the first real runs — the cost table below shows why, on Render, that uncertainty barely matters.

---

## 2. Option 1 — RECOMMENDED ($0): GitHub Actions scheduled workflows

The repo (`github.com/apz100/GrainHub`) is **public**. GitHub's billing doc states that standard GitHub-hosted runners are **free in public repositories** — the usage "remains free independently and does not reduce the included compute usage":

- Source: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions — "The following usage remains free independently… Standard GitHub-hosted runners in public repositories" and "The use of standard GitHub-hosted runners is free: In public repositories / For GitHub Pages / For Dependabot." (Larger runners are billed even on public repos — this design uses only the standard `ubuntu-latest` runner.)

### Design A (preferred): run the job code in the workflow

One workflow file on the **default branch** (`.github/workflows/ingestion.yml`), with two scheduled triggers (GitHub Actions natively supports an IANA `timezone:` per schedule entry, so no DST hand-conversion is needed — see caveats for the alternative):

```yaml
on:
  schedule:
    - cron: "0 8 * * *"
      timezone: "America/Toronto"
    - cron: "0 15 * * *"
      timezone: "America/Toronto"
  workflow_dispatch: {}   # manual run button for debugging / catch-up runs
jobs:
  ingest:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    concurrency: ingestion        # never overlap two runs
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r GrainBids/grainbids/apps/api/requirements.txt
      - working-directory: GrainBids/grainbids/apps/api
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          NASS_API_KEY: ${{ secrets.NASS_API_KEY }}
          FAS_DATA_GOV_API_KEY: ${{ secrets.FAS_DATA_GOV_API_KEY }}
          # + the same non-secret env the API uses (APP_ENV=production, ALLOW_IMPLICIT_ORG=false, …)
        run: |
          python -m app.jobs.daily_source_ingestion
          python -m app.jobs.poll_sources
```

Why this shape:

- It runs the **exact commands from the checklist**, unmodified — no API endpoint needs to exist, and the Render service does not even need to be awake.
- Both jobs run sequentially in one workflow run, twice a day: 4 job executions/day total, ≈120 workflow runs/month. On a public repo the runner minutes cost **$0** regardless.
- `workflow_dispatch` gives a free manual "run it now" button — the equivalent of Render's Trigger Run button.

**Secret-handling note (read before approving):** `DATABASE_URL` would live in a second place — GitHub Actions repo secrets — in addition to Render env. Actions secrets are write-only in the UI and are masked in logs, but it is still a full production database credential held by another platform. Rules if this design is adopted: (1) never echo env in workflow steps; (2) use the Supabase **session-pooler** URI (the same one Render uses), not a direct admin connection string with extra privileges; (3) if repo access ever widens or the workflow is forked, rotate the Supabase password; (4) scheduled workflows are **disabled by default in forks**, so a fork does not run this with your secrets (and secrets are not passed to fork workflows anyway). The USDA keys are free keys, lower stakes, same treatment.

### Design B (alternative): curl the existing API endpoints

The codebase was checked (read-only) for an existing trigger endpoint. What actually exists today:

| Endpoint (all under the API, admin-gated) | Covers |
|---|---|
| `POST /api/ingestion/source-files/run` | Job A equivalent — runs `run_scheduled_file_ingestion_cycle` (the same service function the file-ingestion job calls). |
| `POST /api/ingestion/source-file/run` | Single file source only — not the cycle. |
| `POST /api/sources/{source_id}/refresh` | **One** source per call (`run_source_refresh`, trigger_type "manual"). |
| — | **There is no endpoint that runs the poller.** Nothing calls `poll_due_sources` over HTTP. |

So a pure-curl design **cannot replicate Job B**: it would have to `GET /api/sources`, extract every due/active source ID, and POST a refresh for each one — re-implementing the poller's due/active logic in shell, with different semantics (manual trigger type, per-source error handling, no single summary). It also has two operational strikes: the free Render service may be asleep, and a cold start takes about a minute (Render docs, Deploy for Free: spin-up "takes about one minute"), so the first curl needs a warm-up hit on `/health/live` plus generous timeouts/retries; and the run's real work happens inside the web service's request handling rather than in a batch process.

One more honesty note on auth: the API's admin gate is **header-based** — `require_admin` checks the `X-User-Role: admin` header (with `X-Org-Id` for the org), per `app/core/request_context.py`. There is no shared-secret/token credential on these endpoints in the current code. Design B therefore needs no secret for auth (the org UUID stored as an Actions secret is an identifier, not a credential) — but by the same token, anyone who knows the org UUID can already call these endpoints today. That is a pre-existing property of the deployed API, not something Design B creates; it is flagged here because it affects how much weight "authenticated endpoint" should carry in this decision.

**Verdict:** Design A is the faithful $0 implementation. Design B is documented so the option is visible, but it is a partial re-implementation and is **not** recommended.

### Caveats for GitHub Actions scheduling (all from GitHub's docs)

Source: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows (schedule / workflow_dispatch sections):

1. **Runs can be delayed or dropped under load.** "The `schedule` event can be delayed during periods of high loads of GitHub Actions workflow runs. High load times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped." Our target times (08:00, 15:00) are exactly top-of-hour. Mitigation: schedule at **08:05 / 15:05** Toronto time — a few minutes late is irrelevant for grain bids, and GitHub itself advises scheduling "at a different time of the hour" to decrease delay. A dropped run is the real risk; the next run is 7 hours later. Acceptable for now; the source-health page shows whether a run happened.
2. **60-day inactivity disable (public repos).** "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days." GrainHub is under active development, so this should not bite — but if the repo ever goes quiet for 60 days, ingestion silently stops until someone re-enables the workflow (Actions tab → Enable workflow, or a commit that changes the cron). Worth a calendar note if the project pauses.
3. **Forks:** scheduled workflows are disabled by default when a public repository is forked (same docs / Disabling and enabling a workflow). Only affects forks, not this repo.
4. **Default branch only:** scheduled workflows run only if the workflow file exists on the default branch, and run the latest commit on it. The workflow must be merged to `master` to work at all — it cannot be trialled from a side branch (manual `workflow_dispatch` runs from a branch are possible only after the file exists on the default branch).
5. **Minimum interval** is once every 5 minutes — irrelevant here (we need twice a day), but it rules out using Actions as a sub-5-minute scheduler.
6. **Timezone support is real:** "By default, scheduled workflows run in UTC. You can optionally specify a timezone using an IANA timezone string" — e.g. `timezone: "America/Toronto"` as in Design A, so DST is handled by GitHub. (DST edge rule from the same page: during spring-forward, schedules in skipped hours advance to the next valid time — 08:00/15:00 are never in the skipped 2–3 a.m. window.)

---

## 3. Option 2 — PAID: Render Cron Jobs (exact price)

Render Cron Jobs are a separate paid service type — they are **not** in Render's free list (Deploy for Free, https://render.com/docs/free, lists only web services, Postgres, Key Value, and static sites as free; "Other service types don't support Free instances").

### The rate

- Smallest cron compute plan (`0.5c-512mb`, 0.5 CPU / 512 MB): **$0.00016 per minute**, billed prorated **by the second** on active running time.
  - Source: https://render.com/pricing (cron job rate table; the pricing page's FAQ confirms "billing is prorated to the second… You are only billed for compute when these services are actively running"). The same $0.00016/minute figure is stated on Render's own comparison page: https://render.com/articles/render-vs-netlify ("Render cron job, 512 MB — $0.00016/minute").
- **Minimum charge: $1 per cron job service per month.**
  - Source: https://render.com/docs/cronjobs — "Billing is prorated by the second, based on active running time during a given month. There is a minimum monthly charge of $1 per cron job service."
- Workspace plan: the current Hobby workspace is **$0/month + compute** (https://render.com/pricing), so no workspace fee is added by this option. (For scale: the next cron size up, `1c-2g`, is $0.00058/minute — even that does not change the outcome below, because the $1 minimum dominates.)
- Operational facts from https://render.com/docs/cronjobs: at most one run of a job is active at a time (a scheduled run that collides is delayed, not duplicated); a run is stopped after 12 hours; cron jobs cannot use a persistent disk (neither job needs one); env vars are set per service or shared via an environment group (use a group so the cron services carry the same `DATABASE_URL` / keys as the API).

### The arithmetic (per job, per month)

Runs per job per month = 2 runs/day × 30 days = **60 runs**.

| Runtime per run | Minutes/month | × $0.00016 | Billed (after $1 minimum) |
|---|---|---|---|
| 2 min | 120 | $0.0192 | **$1.00** |
| 5 min | 300 | $0.0480 | **$1.00** |
| 10 min | 600 | $0.0960 | **$1.00** |

Break-even against the minimum: $1.00 ÷ $0.00016/min = **6,250 minutes/month** per job — i.e. a job would need to average **~104 minutes per run** (60 runs) before the per-minute rate costs more than the minimum. At any realistic runtime (2–10 min), the per-minute charge is noise.

**Total for both jobs: 2 services × $1.00 = $2.00/month** (plus $0 workspace fee on Hobby). That is the exact, whole cost of the Render option at the smallest instance size — small, but it is **not $0**, it requires a payment method on the Render workspace, and under the current zero-spend instruction it needs Adam's explicit approval before anyone creates these services.

### The timezone trap (Render-specific)

Render cron schedules are **UTC only** — https://render.com/docs/cronjobs: "All day and time ranges use UTC." There is no timezone field. America/Toronto is UTC−4 in daylight time (EDT) and UTC−5 in standard time (EST), so a fixed UTC expression **cannot** hold 08:00/15:00 Toronto year-round:

| Toronto target | EDT (Mar–Nov) | EST (Nov–Mar) |
|---|---|---|
| 08:00 | `0 12 * * *` | `0 13 * * *` |
| 15:00 | `0 19 * * *` | `0 20 * * *` |

(Conversions verified with `date` for 2026-01-15 and 2026-07-15.) With Render you must either (a) pick one pair and accept the runs shifting by an hour for half the year, or (b) edit both cron expressions twice a year at the DST transitions. The deployment checklist explicitly warns "Use the `America/Toronto` timezone on the schedule itself — do not convert to UTC by hand (daylight saving changes the UTC offset)" — Render Cron Jobs cannot honour that instruction; GitHub Actions can (its `timezone:` field, §2 caveats #6). Blueprint shape if this option is ever approved (for illustration — **not** added to the repo's `render.yaml`, which currently defines only the web service):

```yaml
  - type: cron
    name: grainhub-ingestion-files
    runtime: python
    plan: starter            # legacy name for 0.5c-512mb
    rootDir: GrainBids/grainbids/apps/api
    buildCommand: pip install -r requirements.txt
    schedule: "0 12,19 * * *"   # EDT only — see DST warning above
    startCommand: python -m app.jobs.daily_source_ingestion
  - type: cron
    name: grainhub-poll-sources
    # … identical shape, startCommand: python -m app.jobs.poll_sources
```

---

## 4. Side-by-side

| | GitHub Actions (Design A) | Render Cron Jobs |
|---|---|---|
| **Cost** | **$0** (public repo, standard runners free) | **$2.00/month** (2 × $1 minimum) + payment method required |
| Timezone | Native `America/Toronto`, DST handled | UTC only — 1-hour drift half the year, or manual edits twice a year |
| Runs the real job commands | Yes, exactly as in checklist §4 | Yes |
| Timing reliability | Best-effort: may be delayed at top of hour; queued jobs may be dropped under high load | Render-scheduled; single-run guarantee |
| Failure visibility | Actions tab logs; run failure shows in GitHub | Render Runs page + logs |
| Extra credential exposure | `DATABASE_URL` + USDA keys also stored as GitHub secrets | Secrets stay inside Render (env group) |
| Silent-stop risk | Auto-disabled after 60 days of repo inactivity | None (billed service) |
| Setup effort | One workflow file on `master` + 3 repo secrets | Two cron services (dashboard or Blueprint) + env group + payment method |

## 5. Recommendation

**Adopt Option 1, Design A (GitHub Actions, $0), scheduled 08:05 and 15:05 America/Toronto.** It runs the exact checklist commands, handles DST correctly, and costs nothing — which is the constraint Adam set. Its weaknesses (possible delay, theoretical dropped run, 60-day inactivity rule) are all tolerable for twice-daily grain-bid ingestion and are all visible after the fact on the source-health page.

**Keep Render Cron Jobs as the documented fallback at exactly $2.00/month** if Actions scheduling ever proves unreliable in practice (e.g. repeated dropped runs). That switch is a small, known spend — but it is a spend, so it comes back to Adam for approval rather than being enabled under this proposal.

**Decision needed from Adam:** approve the GitHub Actions workflow (one new file on `master` + adding `DATABASE_URL`, `NASS_API_KEY`, `FAS_DATA_GOV_API_KEY` as repo secrets). Nothing in this draft creates the workflow, the secrets, or any Render service.

---

### Sources (all read 2026-11-19)

- Render pricing — https://render.com/pricing (cron $0.00016/min on 0.5c-512mb; billing prorated to the second; Hobby workspace $0 + compute)
- Render Cron Jobs docs — https://render.com/docs/cronjobs ($1/month minimum per cron service; UTC-only schedules; single-run guarantee; 12-hour cap; no persistent disk)
- Render Deploy for Free — https://render.com/docs/free (cron jobs not among free service types; free web spin-up ≈ 1 minute)
- Render vs Netlify (Render, official) — https://render.com/articles/render-vs-netlify (corroborates $0.00016/minute cron rate and $1 minimum)
- GitHub Actions billing — https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions (standard runners free in public repos; larger runners billed)
- GitHub workflow events — https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows (schedule delays/drops, default-branch rule, 60-day public-repo disable, 5-minute minimum interval, IANA `timezone:` support)
- Repo (read-only): `docs/plans/deployment-checklist.md` §4; `GrainBids/grainbids/apps/api/app/jobs/daily_source_ingestion.py`; `…/app/jobs/poll_sources.py`; `…/app/api/routes/ingestion.py`; `…/app/api/routes/sources.py`; `…/app/core/request_context.py`
