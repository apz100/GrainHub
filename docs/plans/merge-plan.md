# GrainHub — Merge Plan for Cycle Branches 1–7

**Status: PLAN ONLY — nothing has been merged.** Written 2026-11-19
(Cycle 8). No branch was merged, no commit was made, nothing was
pushed, and no deployment was changed while writing this plan. Adam
reviews and merges; this document only says how.

**Branches:** `overnight/grainhub-cycle-1` through
`overnight/grainhub-cycle-7`, remote `https://github.com/apz100/GrainHub`.
`master` is still at `f2c3206` ("Add GrainHub super plan") — no cycle
work is on `master` yet.

## 0. Branch chain — verified from git, 2026-11-19

The chain is **linear**: each cycle branch was branched from the
previous one (`cycle-1` from `master`, `cycle-2` from `cycle-1`, …,
`cycle-7` from `cycle-6`). Verified with
`git log --oneline master..overnight/grainhub-cycle-7`: **32 commits**,
no merges, no branch points. That means:

- Merging in order 1 → 7 is a clean fast-forward at each step — the
  tip of `cycle-7` (`7d3240f`) is exactly `master` + all 32 commits.
- There are **no true merge conflicts** waiting in a sequential
  merge, because no two branches diverged. Conflicts only appear if
  Adam cherry-picks individual commits instead of merging whole
  branches (see §4).
- A single fast-forward of `master` to the `cycle-7` tip would give
  the same tree as seven sequential merges. Prefer the sequential
  merges anyway (§2): they give a review checkpoint and a stop point
  per cycle, so one bad branch does not take the other six with it.

Per-branch commit counts: Cycle 1: 6, Cycle 2: 6, Cycle 3: 5,
Cycle 4: 5, Cycle 5: 3, Cycle 6: 4, Cycle 7: 3.

## 1. What each branch contains

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 1 | `a7e08e5` | 179 passed, 0 failed | **Not run** (node_modules not installed in Cycle 1) |
| Cycle 2 | `a880c71` | 291 passed, 0 failed | PASS, 28 pages |
| Cycle 3 | `7345d30` | 320 passed, 0 failed | PASS (prototypes static) |
| Cycle 4 | `fe670e5` | 359 passed, 0 failed | Not re-run (no web files changed) |
| Cycle 5 | `7b44e11` | 364 passed, 0 failed | PASS, 33 pages |
| Cycle 6 | `59e7d41` | 380 passed, 0 failed | Not re-run (no web files changed) |
| Cycle 7 | `7d3240f` | 407 passed, 0 failed | Not re-run (no web files changed) |

- **Cycle 1** (`overnight/grainhub-cycle-1`): Phase 0 hardening,
  `GET /api/market-search`, Research v1 (NASS/FAS key-gated
  collectors, WASDE/Crop Progress ingestion + pages), Advisor v1,
  Elevator Ops v1, and the price-source catalogue (Ontario 20 URLs
  probed, US 58 probed + 20 new candidates, 6 added to config).
  Full detail: `docs/plans/overnight-cycle-1-report.md`.
- **Cycle 2** (`overnight/grainhub-cycle-2`): basis tracker, source
  health dashboard, daily newsletter generator (delivery off),
  futures strip + ICE canola desk (contract structure only, prices
  null), price history + 5-year seasonal averages, report calendar,
  email-bid OCR parsing module, public best-bid API + page. FMN cash
  page read in full (204 tables, 86 points, 336-option dropdown).
  Full detail: `docs/plans/overnight-cycle-2-report.md`.
- **Cycle 3** (`overnight/grainhub-cycle-3`): prototypes (mobile
  price finder, onboarding wizard, pricing page), Ontario collectors
  (Collwest, Mae-Mart, Mapleview stub), LAC base-URL fix, FMN
  location-filter verification, Bushel collector research, USDA
  mirror verification, Grain Stocks / Export Sales / COT parsers,
  Barchart/DTN + ERP design docs.
  Full detail: `docs/plans/overnight-cycle-3-report.md`.
- **Cycle 4** (`overnight/grainhub-cycle-4`): email-bid ingest
  endpoint (`POST /api/email-bids/parse`, parse-only, no storage),
  generic Bushel collector (FAC verified live, 45 rows; Collwest
  cross-check 16/16), USDA-mirror collector (both hosts, Gulf +
  Pacific Ports), Crop Production parser wired into ingest-file.
  Full detail: `docs/plans/overnight-cycle-4-report.md`.
- **Cycle 5** (`overnight/grainhub-cycle-5`): all 11 Bushel sites
  verified live and registered (plus FAC/Collwest from Cycle 4);
  United Coop same-org question resolved (two separate orgs);
  parser fixes (fractional futures, classless `<h2>`, Cash-Price
  header); `/today` morning-view page.
  Full detail: `docs/plans/overnight-cycle-5-report.md`.
- **Cycle 6** (`overnight/grainhub-cycle-6`): DTN sweep (28 sites:
  2 static-HTML, 20 JS-only, 6 unreachable; Ace Ethanol + Alliance
  Grain verified Bushel and registered), deployment checklist
  (Vercel/Render/Supabase), basis-alert helpers (standalone, not
  yet wired). Includes the corrupted-string-literal fix — see §4.
  Full detail: `docs/plans/overnight-cycle-6-report.md`.
- **Cycle 7** (`overnight/grainhub-cycle-7`): AgriCharts
  `cashbids.php` embed collector (6 sites, 105 rows, static route
  via `cashbids-js.php` — no Playwright needed), AGP iframe
  verified Bushel (Chester, NE) and registered, basis thresholds
  wired into the alert evaluator (migration `0019`).
  Full detail: `docs/plans/overnight-cycle-7-report.md`.

## 2. Merge order and procedure

Merge **in order, 1 → 7, one branch at a time**, on `master`:

```sh
git checkout master
git merge --no-ff overnight/grainhub-cycle-1   # then run the §3 gates
git merge --no-ff overnight/grainhub-cycle-2   # then run the §3 gates
# … repeat through cycle-7
git push origin master
```

Use `--no-ff` so each cycle stays visible as one merge commit even
though the chain is linear — that keeps the per-cycle review
checkpoints in history and makes a per-cycle revert possible. Push
after each merge, or once at the end; either is fine, but do not
push a branch whose gates have not passed. If a gate fails at any
step, stop at that branch, fix forward on a new branch off `master`,
and do not merge the later cycles until the failure is understood —
later cycles build on the earlier ones (e.g. Cycle 7's collector
assumes Cycle 6's catalogue reclassifications).

## 3. Gates to run before each merge

Run these **on the branch being merged** (checked out, or in a
worktree), before the `git merge` for that cycle. Expected results
are the counts in §1 — a lower count or any failure is a stop, not
a warning to merge past.

1. **Full API test suite** — from `GrainBids/grainbids/apps/api`,
   run the full pytest suite. Expect: Cycle 1: 179 passed,
   Cycle 2: 291, Cycle 3: 320, Cycle 4: 359, Cycle 5: 364,
   Cycle 6: 380, Cycle 7: 407 — **0 failed** at every step.
   (Pre-existing Starlette deprecation warnings are expected.)
2. **Web build** — from `GrainBids/grainbids/apps/web`, run
   `npm install && npm run build`. Expect exit 0. This matters most
   at Cycle 1 (its build was never run — node_modules was missing),
   Cycle 2 (28 pages), Cycle 3 (prototype routes), and Cycle 5
   (33 pages, `/today`). Cycles 4, 6, 7 changed no web files, so a
   build re-run there is a sanity check, not a gate that can newly
   fail — still run it once at the Cycle 7 step so the final tree
   is verified as a whole.
3. **Alembic chain** — from `apps/api`, run `alembic heads` and
   expect exactly one head. The head moves as cycles land:
   `0018` after Cycle 1, still `0018` through Cycle 6, **`0019`
   after Cycle 7** (basis-threshold columns). Two heads means stop
   — the chain has branched and needs a merge revision before any
   deploy. (Note: `docs/plans/deployment-checklist.md` §3 still
   says the head is `0018` — it was written in Cycle 6, before
   `0019` existed. Update it to `0019` after merging Cycle 7; do
   not deploy against the stale number.)
4. **Boundary spot-check** — grep the merged diff for the company
   named in the Cycle 2 boundary (North Gower Grains): it must
   appear only as one ordinary price source (collector registry,
   catalogue, probe list), never as a pilot, showcase, featured
   bid, branding, or implied affiliation. Cycles 2–7 each verified
   this in their reports; re-check once at the Cycle 3 step (which
   adds its collector) and once at the end.
5. **No-secrets spot-check** — `git log -p` for the branch must
   show no API keys, tokens, or credentials. All cycles report
   none; this is a cheap re-confirmation, not a suspicion.

## 4. Known conflicts and overlaps to watch for

Because the chain is linear, a sequential merge produces no
conflicts. Watch these instead — they are the places where a
cherry-pick, a rebase, or a careless resolve would silently lose
work:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **every** cycle (Cycle 1: Ontario + US survey;
  Cycle 2: FMN full read; Cycle 3: Collwest/Bushel/USDA findings;
  Cycle 4: USDA-mirror counts; Cycle 5: Bushel sweep table;
  Cycle 6: DTN sweep, 28 sites; Cycle 7: embed reclassifications).
  Each cycle's edits build on the last. Cherry-picking across
  cycles will conflict here; resolve by keeping the later cycle's
  classifications (they correct earlier ones — e.g. Ag State was
  mislabelled DTN since Cycle 1 and is corrected to
  `agricharts-embed` in Cycle 7).
- **Source registry** (`app/services/source_registry.py`) —
  touched in Cycles 3, 4, 5, 6, 7, each adding registrations
  (Ontario collectors → FAC → 11 Bushel sites → Ace/Alliance →
  AGP + 6 embed sites). Same rule: later wins, never drop a
  registration to resolve a conflict.
- **`us_elevators_urls.toml`** — reclassifications accumulate:
  Cycle 1 (AGP/Five Star/Gateway → DTN), Cycle 6 (AGP `dtn →
  bushel`, Ace/Alliance `unknown → bushel`, five sites →
  AgriCharts embed, Frontier `DTN → StoneX`), Cycle 7 (six sites
  `dtn → agricharts-embed`). The Cycle 7 values are the current
  truth; do not let a conflict resolution resurrect a Cycle 1 or
  Cycle 6 label.
- **Cycle 6 string-literal fix** — commit `387c985` (DTN sweep)
  was pushed with a corrupted string literal in
  `bushel_source.py` that broke pytest collection for the two
  Bushel test files. It was fixed on top by `eb01c71` (line-level
  rewrite, full suite 380 passed); the broken commit was **not**
  rewritten, so history shows the mistake and the fix. Do not
  cherry-pick `387c985` without `eb01c71`, and do not "clean up"
  the history by dropping either commit. When merging Cycle 6,
  verify the suite passes at the branch tip (380), not at the
  intermediate commit.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) — edited
  in Cycle 2 (one line) and Cycle 5 (progress section added);
  Cycle 8 updates it to Cycles 1–7. Linear merge, no conflict
  expected.
- **Migration chain** — `0015 → 0016 → 0017 → 0018` (Cycle 1)
  then `0019` (Cycle 7). Linear, single head at each tip. No
  branch in the chain; if `alembic heads` ever shows two heads
  after a merge, stop (see §3.3).
- **Prototypes** (`apps/web/app/prototypes/`) — Cycle 3 added
  them bannered "Prototype — not production". Merging ships them
  under `/prototypes/*`. That is intentional in the branch, but
  Adam should confirm he wants prototype pages visible on the
  merged site before deploying, not before merging.

## 5. What must NOT be merged as-is

- **The CI workflow file is not in any branch.** `.github/workflows/
  api-tests.yml` (Python 3.12, pytest on push/PR, no secrets, no
  deploy steps) was written in Cycle 2 but **could not be pushed**:
  GitHub rejected it because the `gh` OAuth token lacks the
  `workflow` scope. It still sits **untracked in the local working
  tree** (`?? .github/`, verified 2026-11-19). Merging all seven
  branches will **not** bring it into `master` — the `.github`
  directory must not be assumed present after the merges. To get
  CI: Adam re-authenticates `gh` with `workflow` scope and the
  file is committed/pushed from the local tree, or he adds it via
  the GitHub web UI. Do not hand-copy it into a merge commit as a
  shortcut — the scope problem would just recur on the next
  workflow change.
- **Nothing else is held back.** Every other file from Cycles 1–7
  is committed on its branch and merges normally. In particular:
  no secrets, keys, or credentials are in any branch (verified in
  each cycle report); no deployment config was changed by any
  cycle; no vendor was contacted.
- **Review, don't rubber-stamp, these known behaviours** (they
  merge as-is by design, but Adam should know they ship):
  the email-bid endpoint (`POST /api/email-bids/parse`) is public
  by default — admin-only is a one-line change if wanted; futures
  endpoints return contract structure with prices `null` until a
  licensed feed is wired; Advisor `/ask` is a 501 scaffold; eSign
  is a stub; normalized price rows carry no currency, so basis /
  best-bid responses report `currency: null`.

## 6. Rollback — per `docs/plans/deployment-checklist.md` §6

These rules apply to the **deploy** that follows the merges, and
to a bad merge itself:

- **Code rollback:** redeploy the previous `master` commit in
  Render (API) and the previous Vercel deployment (web). Both are
  one-click in their dashboards. **No git force-push, no branch
  surgery.** Note the commit hash rolled back from, so the bad
  deploy can be investigated on its branch.
- **Never roll back by deploying a cycle branch.** The rollback
  target is always a previous `master` deploy — a cycle branch is
  unreviewed code by definition until merged.
- **Database rollback:** Alembic migrations are **forward-only by
  default**. There is no automatic downgrade step. If a deploy
  must be rolled back *and* a migration in that deploy is the
  problem, stop and get Adam's explicit approval for the specific
  downgrade (`alembic downgrade <revision>`) after confirming what
  data that migration added or changed. Rolling code back without
  rolling the database back is safe for additive migrations (new
  tables/columns — including Cycle 7's `0019` basis-threshold
  columns); the old code simply ignores them.
- **Ingestion rollback:** if a bad ingestion run wrote bad rows,
  do not delete rows by hand. Record the run id and the source,
  and fix forward with a corrected ingestion run.
- **Bad merge rollback:** if a merge itself is wrong (before any
  deploy), revert with `git revert -m 1 <merge-commit>` on
  `master` — do not rewrite `master` history once pushed.

## 7. After the merges — before any deploy

1. Update `docs/plans/deployment-checklist.md` §3 and §8: Alembic
   head is now `0019`, not `0018`.
2. Work through the deployment checklist §0–§5 in order
   (decisions/keys, Supabase, env vars, migrations, ingestion
   schedule 08:00 + 15:00 America/Toronto, health checks 1–11).
3. **Deploy from `master` only** — never from a cycle branch.
   The checklist's branch rule (§0) still applies after the
   merges: it exists to stop unreviewed code shipping, and these
   merges are the review step that satisfies it.
4. Still open after merging (Adam's decisions, unchanged by the
   merges): NASS key, FAS/data.gov key, LLM provider + key,
   Barchart/DTN licensed feed decision (redistribution licence),
   ERP choice (Agvance recommended first), eSign provider,
   pricing/hosting decisions, `gh` `workflow` scope for CI,
   currency column / per-source currency mapping, email-bid
   endpoint auth (public vs admin-only), and Playwright render
   checks (12 DTN-family JS-only sites, FMN filtered view,
   Mapleview). Full list in the super-plan §9.
