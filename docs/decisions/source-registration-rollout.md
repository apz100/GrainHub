# Decision paper — Production source-registration rollout plan

**Status:** prepared 2026-11-20 (overnight run). Nothing in this plan
has been executed against production. Every step is Adam's to approve.
**Cost of the whole plan: $0** (one local command against the existing
free Supabase database; no new services).

## Where production stands tonight

- The production org ("GrainBids Demo Org",
  `9e39595c-5706-4496-a59f-b1b38b7c15da`) has **6 registered sources**,
  all legacy rows from the local setup — all stale/failing. One is
  "Ontario Daily File", whose identifier is a Windows path
  (`P:\Adam\...`) that can never resolve on Render.
- The adapter registry in code holds **119 adapters, 101
  toggle-enabled** (`docs/plans/collector-coverage.md`, Cycle 40
  correction). **None of them are registered as `Source` rows in
  production**, so the scheduled poller (`app.jobs.poll_sources`) has
  almost nothing to poll and the site's prices only change when the
  local pipeline pushes them.
- The seed machinery already exists and is idempotent:
  `seed_sources_from_registry()` (used by `POST /api/sources/seed`)
  skips adapters that already have a row for the org and skips
  toggle-off adapters. New tonight: a one-command CLI wrapper,
  `python -m app.jobs.seed_sources` (branch
  `overnight/2026-11-20`), with `--dry-run`, `--org-id/--org-name`,
  and `--scope pilot|all`.

## Rollout steps (in order)

1. **Merge the overnight branch** (or just the seed-job commit) to
   master — Adam's review. Not strictly required to run the job (it
   can run from the branch checkout), but master is the deployable
   source of truth.
2. **Dry-run against production** (read-only; writes nothing):
   ```
   cd GrainBids/grainbids/apps/api
   DATABASE_URL=<Supabase session-pooler URL> \
     .venv/bin/python -m app.jobs.seed_sources \
       --org-id 9e39595c-5706-4496-a59f-b1b38b7c15da --dry-run
   ```
   Expect `would create` ≈ 101 minus any adapter keys the legacy
   rows already carry, and `skipped_disabled` = the 18 toggle-off
   keys. If the numbers look wrong, stop here — nothing was written.
3. **Real run** — same command without `--dry-run`. Adds `Source`
   rows only; **no prices are fetched and nothing polls yet**, so
   this step alone changes nothing user-visible.
4. **Verify**: `GET /api/source-health` (org headers) should list the
   new sources with status `unknown` (never "healthy" before a first
   poll — that honesty is by design).
5. **Retire the dead legacy row**: set "Ontario Daily File"
   `is_active=false` (admin UI or one SQL update). It can never
   succeed from a server and its permanent failure noise hides real
   failures. Leave the other legacy rows until step 6 proves the
   registry rows work; then deactivate any that duplicate a registry
   adapter.
6. **First poll, small**: trigger a manual refresh on 2–3 pilot
   adapters (`POST /api/sources/{id}/refresh`, admin) and confirm
   rows land in the price preview before any schedule is enabled.
   Note the 8 Ontario Playwright-mode adapters additionally need a
   Chromium-equipped environment to fetch — the Render web service
   is not one, so expect those to fail in a Render-hosted poll until
   the scheduling decision (cron proposal paper) picks where polling
   runs. The ~93 direct/direct_dict adapters need only HTTPS.
7. **Scheduling**: separate decision — see the Render cron proposal
   (paid) vs GitHub Actions (free) paper. Seeding without scheduling
   is safe and reversible; nothing auto-polls until a scheduler
   exists.

## Risks and mitigations

- **Free-instance load**: a full 101-adapter poll is heavy for a
  512 MB free instance if it ever ran inside the web service. It
  doesn't: the poller is its own process (`app.jobs.poll_sources`),
  and fetches run in subprocesses with per-source timeouts. Where
  that process runs is the scheduling decision, not this one.
- **Bad rows**: seeding writes only `sources` rows. Undo = set
  `is_active=false` on the seeded rows (they're the ones with
  `source_type='automated'` and a non-null `adapter_key`); no price
  data exists to roll back until a poll runs.
- **Duplicates**: the service dedupes on adapter key per org and the
  CLI was tested for idempotency (second run creates 0).

## Recommendation

Approve steps 2–5 as one morning action (~10 minutes): dry-run,
seed, verify, retire the Windows-path row. Defer step 6–7 to the
scheduling decision so the first poll happens wherever polling will
live long-term.
