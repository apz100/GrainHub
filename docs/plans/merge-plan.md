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

---

## Cycles 8–12 (added Cycle 13)

**Status: PLAN ONLY — nothing has been merged.** §§0–7 above cover
Cycles 1–7 and are unchanged. This section extends the plan to
Cycles 8–12, verified from git history and the cycle reports on
2026-11-19 (Cycle 13). `master` is still at `f2c3206` — no cycle
work is on `master` yet.

### 0b. Branch chain — Cycles 8–12, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-12` gives **43 commits** (32
through Cycle 7 + 11 in Cycles 8–12), **0 merge commits**, no
branch points. Cycle 8's first commit `b0ba527` has parent
`7d3240f` (the Cycle 7 tip), and each later cycle branches from
the previous tip. Per-branch commit counts: Cycle 8: 3, Cycle 9: 2,
Cycle 10: 2, Cycle 11: 2, Cycle 12: 2.

That means the §2 procedure continues unchanged: merge in order
8 → 12 after 7, one branch at a time with `--no-ff`, running the
§3 gates at each step. A single fast-forward of `master` to the
`cycle-12` tip (`4b2472b`) would give the same tree as twelve
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

### 1b. What each branch contains (Cycles 8–12)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 8 | `62f9480` | 407 passed, 0 failed | Not re-run (no web files changed) |
| Cycle 9 | `17d26cb` | 454 passed, 0 failed | Not re-run (no web files changed) |
| Cycle 10 | `7e1a94e` | 488 passed, 0 failed | **PASS** (re-run this cycle) |
| Cycle 11 | `7696cc0` | 536 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 10) |
| Cycle 12 | `4b2472b` | 558 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 10) |

No web files changed in any of Cycles 8–12 (Cycle 10's report
confirms none changed since Cycle 5), so the only fresh web-build
evidence in this range is Cycle 10's pass.

- **Cycle 8** (`overnight/grainhub-cycle-8`; commits `b0ba527`,
  `aa570be`, `62f9480`): docs-only cycle — this merge plan (§§0–7),
  super-plan §9 progress to Cycle 7, deployment-checklist
  migration head corrected `0018 → 0019`; plus a re-check sweep in
  the catalogue (all 5 Cycle 6 failures back up; Five Star 299
  static wpDataTables rows; StoneX has no static-data route). No
  code, so no new tests — suite unchanged at 407.
  Full detail: `docs/plans/overnight-cycle-8-report.md`.
- **Cycle 9** (`overnight/grainhub-cycle-9`; commits `0b35f18`,
  `17d26cb`): Five Star Coop wpDataTables collector (299 rows, 21
  locations; new generic `wpdatatables_source.py`, 43 tests);
  ALCIVIA + TGM `cashbids.php` embeds proven (543 rows); CRC
  resolved as StoneX-only. 47 new tests, suite 454.
  Full detail: `docs/plans/overnight-cycle-9-report.md`.
- **Cycle 10** (`overnight/grainhub-cycle-10`; commits `52c6d42`,
  `7e1a94e`): FMN `writeBidRow` collector (453 rows, 87 delivery
  points, 204 tables; new `fmn_source.py`, 31 tests); 19-site US
  sweep (13 reclassified, Sunrise enabled, Synergy Cooperative
  registered in `bushel_source.py`, 3 tests); currency design note
  (`docs/plans/currency-design.md`). Web build re-run: PASS. 34
  new tests, suite 488.
  Full detail: `docs/plans/overnight-cycle-10-report.md`.
- **Cycle 11** (`overnight/grainhub-cycle-11`; commits `fd8d58e`,
  `7696cc0`): FMN `jsquote` feed fills 449/449 futures-linked
  rows; PRO Coop embed proven; Wheaton Grain tabbed-widget
  fallback in `bushel_source.py` (`_parse_tabbed_widget`,
  easyResponsiveTabs); 9-site sub-page sweep (Pro Ag 78 rows and
  Winchester 10 rows registered; Skyland corrected to 6 static
  rows and registered; West-Con parser gap found — month-name
  delivery labels; The Andersons GRAINweb picker documented, no
  static route). 48 new tests net, suite 536.
  Full detail: `docs/plans/overnight-cycle-11-report.md`.
- **Cycle 12** (`overnight/grainhub-cycle-12`; commits `cfa6161`,
  `4b2472b`): West-Con regex fix (month-name + short-month
  delivery labels; 84/84 West-Con, 43/43 Wheaton Dumont) unblocks
  2 sites; Hull / StateLine / PRO-21302 `cashbids.php` embeds
  proven (12 + 126 + 12 rows) and enabled; three per-location
  Bushel probes enabled (Georgetown 3440, Skyland 2730,
  Bentonville 1666). 22 new tests, suite 558.
  Full detail: `docs/plans/overnight-cycle-12-report.md`.

### 3b. Gates — updated expectations for Cycles 8–12

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 8: 407, Cycle 9: 454,
   Cycle 10: 488, Cycle 11: 536, Cycle 12: 558 — **0 failed** at
   every step.
2. **Web build** — re-run once at the Cycle 10 step (it passed
   there) and once at the Cycle 12 step so the final tree is
   verified as a whole. Cycles 8, 9, 11, 12 changed no web files,
   so a build failure at one of those steps would point at an
   earlier cycle, not the branch being merged.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycles 8–12 (`git log` on
   the Alembic versions dir in `master..cycle-12` shows only the
   Cycle 1 and Cycle 7 commits, and the file list at the Cycle 12
   tip is `0001`–`0019`). Expect exactly one head, `0019`, at
   every step 8–12.
4. **Boundary spot-check** — each Cycle 8–12 report has its own
   boundary section; Cycle 10 notes the company named in the
   Cycle 2 boundary appears as one ordinary FMN delivery point
   among 87 — ordinary source only, consistent with the boundary.
   Re-check once at the Cycle 12 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; all five reports state
   none.

### 4b. Known conflicts and overlaps — Cycles 8–12

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **every** cycle 8–12 as well (all five work commits
  touch it). Same rule as §4: later wins.
- **Source registry** (`app/services/source_registry.py`) —
  touched in Cycles 9–12 (Cycle 8 added no code): Five Star
  adapter (9), Synergy (10), Winchester + Skyland (11), Hull /
  StateLine / PRO + three per-location entries (12). Later wins,
  never drop a registration.
- **`us_elevators_urls.toml`** — reclassifications accumulate in
  Cycles 9–12: Five Star `dtn → wpdatatables` (9); 13 in the
  Cycle 10 sweep; Pro Ag / West-Con / Hull / StateLine /
  Winchester / Skyland (11); West-Con / Wheaton Dumont / Hull /
  StateLine / PRO + per-location entries (12). The Cycle 12 values
  are the current truth.
- **`bushel_source.py`** — touched in Cycles 10 (Synergy site +
  `fetch_synergy`), 11 (tabbed-widget fallback
  `_parse_tabbed_widget` for Wheaton Grain — additive, only runs
  when no `div.cbCommodity` sections are found), and 12
  (per-location entries). A bad resolve here would lose the
  Wheaton tabbed shape; same care as the Cycle 6 string-literal
  note in §4, but there is no broken intermediate commit in this
  range.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in Cycle 8 (progress to Cycle 7) and Cycle 12; linear,
  no conflict expected.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycles 8–12.

### 5b. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 13): `?? .github/` in `git status` on the
  Cycle 13 checkout. Merging Cycles 8–12 as well as 1–7 will
  **not** bring it into `master`. Cycle 9 adds a cautionary
  detail: that cycle it was accidentally staged by `git add -A`
  and the push was rejected for exactly the `workflow`-scope
  reason; the commit was redone without it and the file remains
  untracked locally. Same remedy as §5: Adam re-authenticates
  `gh` with `workflow` scope, or adds the file via the GitHub web
  UI. Do not hand-copy it into a merge commit.
- **§7 step 1 is partly done on the branch already:** Cycle 8
  (`b0ba527`) corrected `docs/plans/deployment-checklist.md` §3
  to head `0019` — but the §8 deploy sign-off checklist still
  says `alembic heads` = single head `0018` (stale line). Fix that
  line when merging; do not deploy against the stale number.
- **Nothing else new is held back in Cycles 9–12.** No new
  unpushed files, secrets, or held-back work is reported in any
  of the five reports. The §5 review-not-blocker list is
  unchanged, with one addition: Cycle 10 wrote a currency design
  doc (`docs/plans/currency-design.md`), but normalized price rows
  still carry no currency — the currency decision is still open.

### 7b. After the merges — updated

§7 applies with the Cycle 12 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 558 passed / 0
failed, web build last fully passed in Cycle 10 (re-run at the
Cycle 12 merge step). The still-open decisions list in §7.4 is
unchanged by Cycles 8–12, plus the currency design doc now exists
as the basis for the currency-column decision.
