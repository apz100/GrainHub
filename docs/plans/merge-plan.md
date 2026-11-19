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
  to head `0019`, and Cycle 13 corrected the §8 deploy sign-off
  line to `0019` as well (verified 2026-11-19, Cycle 16 — the
  checklist now reads `0019` in both places). Nothing stale
  remains to fix there when merging.
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

---

## Cycles 13–15 (added Cycle 16)

**Status: PLAN ONLY — nothing has been merged.** §§0–7 above cover
Cycles 1–7 and the Cycles 8–12 section covers Cycles 8–12; both
are unchanged. This section extends the plan to Cycles 13–15,
verified from git history and the cycle reports on 2026-11-19
(Cycle 16). `master` is still at `f2c3206` — no cycle work is on
`master` yet.

### 0c. Branch chain — Cycles 13–15, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-15` gives **49 commits** (43
through Cycle 12 + 6 in Cycles 13–15), **0 merge commits**, no
branch points. Cycle 13's first commit `f1dc87f` has parent
`4b2472b` (the Cycle 12 tip), and each later cycle branches from
the previous tip. Per-branch commit counts: Cycle 13: 2, Cycle 14:
2, Cycle 15: 2.

That means the §2 procedure continues unchanged: merge in order
13 → 15 after 12, one branch at a time with `--no-ff`, running the
§3 gates at each step. A single fast-forward of `master` to the
`cycle-15` tip (`7f8c263`) would give the same tree as fifteen
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

### 1c. What each branch contains (Cycles 13–15)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 13 | `6acc8e2` | 590 passed, 0 failed | **PASS** (re-run this cycle; no web files changed) |
| Cycle 14 | `d196b2a` | 617 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 13) |
| Cycle 15 | `7f8c263` | 629 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 13) |

No web files changed in any of Cycles 13–15, so the only fresh
web-build evidence in this range is Cycle 13's pass.

- **Cycle 13** (`overnight/grainhub-cycle-13`; commits `f1dc87f`,
  `6acc8e2`): PRO Coop second `cashbids.php` embed proven (12
  rows, MANSON.IA — 13th embed site, registered as
  `pro_coop_21302b`); 10 per-location Bushel probes verified
  (Skyland 6, Smithfield 4, 30 tests); The Andersons GRAINweb
  verdict from saved HTML — browser-only, no static route; merge
  plan extended to Cycle 12; super-plan §9 extended to Cycle 12.
  32 new tests, suite 590.
  Full detail: `docs/plans/overnight-cycle-13-report.md`.
- **Cycle 14** (`overnight/grainhub-cycle-14`; commits `94defb7`,
  `d196b2a`): Skyland picker sweep complete — all 14 IDs verified
  (39 rows this cycle, 7 registry entries, 21 tests); Smithfield
  batch 1669–1674 (17 rows, 6 tests); Andersons bundle read
  (1,079 bytes) confirms browser-only, no network call of any
  kind; Chadbourn re-check still stale (Nov 18 header). 27 new
  tests, suite 617.
  Full detail: `docs/plans/overnight-cycle-14-report.md`.
- **Cycle 15** (`overnight/grainhub-cycle-15`; commits `7b9d69d`,
  `7f8c263`): Smithfield batches A + B — 11 locations verified
  (1675–1688; 18 rows; 1675 Raeford served an empty widget, not
  registered, guarded by a negative test; 1681's live h2 is "Rose
  Hill, NC"); Andersons locations-list probe (27,082 bytes, a
  pure per-location directory) closes the Andersons for static
  collection — only a rendered browser session remains; super-plan
  §9 extended to Cycle 14. Smithfield now 22 of 31 verified. 12
  new tests, suite 629.
  Full detail: `docs/plans/overnight-cycle-15-report.md`.

### 3c. Gates — updated expectations for Cycles 13–15

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 13: 590, Cycle 14: 617,
   Cycle 15: 629 — **0 failed** at every step.
2. **Web build** — re-run once at the Cycle 13 step (it passed
   there) and once at the Cycle 15 step so the final tree is
   verified as a whole. Cycles 13–15 changed no web files, so a
   build failure at one of those steps would point at an earlier
   cycle, not the branch being merged.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycles 13–15 (`git log` on
   the Alembic versions dir in `cycle-12..cycle-15` is empty, and
   the file list at the Cycle 15 tip is `0001`–`0019`). Expect
   exactly one head, `0019`, at every step 13–15.
4. **Boundary spot-check** — each Cycle 13–15 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 15 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; all three reports state
   none. Note Cycle 15's Andersons page carried a
   `data-google-api-key` attribute; its value was deliberately not
   reproduced anywhere in the repo.

### 4c. Known conflicts and overlaps — Cycles 13–15

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **every** cycle 13–15 as well (all three work
  commits touch it). Same rule as §4: later wins.
- **Source registry** (`app/services/source_registry.py`) —
  touched in Cycles 13, 14, and 15: PRO Coop 21302b + 10
  per-location adapters (13), 7 Skyland + 6 Smithfield adapters
  (14), 11 Smithfield adapters (15). Later wins, never drop a
  registration.
- **`bushel_source.py`** — touched in all three cycles (13, 14,
  15) for the per-location entries. Additive only; the Wheaton
  tabbed-widget fallback from Cycle 11 is untouched in this
  range.
- **`us_elevators_urls.toml`** — reclassifications accumulate in
  Cycles 13–15: PRO Coop 21302b + 10 per-location entries (13),
  7 Skyland + 6 Smithfield entries (14), 11 Smithfield entries
  (15). The Cycle 15 values are the current truth.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in Cycle 13 (progress to Cycle 12) and Cycle 15
  (progress to Cycle 14); Cycle 14 did not touch it. Linear, no
  conflict expected.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycles 13–15.

### 5c. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 16): `?? .github/` in `git status` on the
  Cycle 16 checkout. Merging Cycles 13–15 as well as 1–12 will
  **not** bring it into `master`. Same remedy as §5: Adam
  re-authenticates `gh` with `workflow` scope, or adds the file
  via the GitHub web UI. Do not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycles 13–15.** No new
  unpushed files, secrets, or held-back work is reported in any
  of the three reports. The §5 review-not-blocker list is
  unchanged: email-bid endpoint public by default, futures
  endpoints return prices `null` until a licensed feed is wired,
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Correction to §5b (made Cycle 16):** the §5b note that the
  deployment checklist's §8 sign-off line still said head `0018`
  is now stale — Cycle 13 corrected it to `0019`, and the
  checklist now reads `0019` in both §3 and §8.

### 7c. After the merges — updated

§7 applies with the Cycle 15 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 629 passed / 0
failed, web build last fully passed in Cycle 13 (re-run at the
Cycle 15 merge step). The still-open decisions list in §7.4 is
unchanged by Cycles 13–15. Open work carried forward: 8
Smithfield locations still unverified + the Raeford re-probe;
Chadbourn + Skyland 3370/3621 staleness watch; Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, and now
The Andersons — closed for static collection, browser-only).

---

## Cycles 16–18 (added Cycle 19)

### 0d. Branch chain — Cycles 16–18, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-18` gives **55 commits** (49
through Cycle 15 + 6 in Cycles 16–18), **0 merge commits**, no
branch points. Cycle 16's first commit `58679eb` has parent
`7f8c263` (the Cycle 15 tip), and each later cycle branches from
the previous tip: merge-base(16, 17) is the Cycle 16 tip
`ee1a794`, merge-base(17, 18) is the Cycle 17 tip `6154176`.
Per-branch commit counts: Cycle 16: 2, Cycle 17: 2, Cycle 18: 2.

That means the §2 procedure continues unchanged: merge in order
16 → 18 after 15, one branch at a time with `--no-ff`, running the
§3 gates at each step. A single fast-forward of `master` to the
`cycle-18` tip (`722dd8f`) would give the same tree as eighteen
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

### 1d. What each branch contains (Cycles 16–18)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 16 | `ee1a794` | 638 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 13) |
| Cycle 17 | `6154176` | 643 passed, 0 failed | **PASS** (re-run this cycle; `/history` page change compiled) |
| Cycle 18 | `722dd8f` | 646 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Web files changed only in Cycle 17 (`app/history/page.tsx`), so
the only fresh web-build evidence in this range is Cycle 17's
pass.

- **Cycle 16** (`overnight/grainhub-cycle-16`; commits `58679eb`,
  `ee1a794`): Smithfield East Region sweep complete — 30 of 31
  locations verified and registered (batch 5: 1689–1691,
  2064–2066, 20 rows; loose ends: Lapaz 2067 and Hamer 2179
  verified, Raeford 1675 re-probed still empty and left
  unregistered); Waverly (1691) is the fattest Smithfield page yet
  (7 rows) and the first to carry Grain Sorghum. The Andersons
  fully closed on licensing grounds: the Maumee facility page
  carries 3 static bid tables (23 rows) but they are
  Barchart-licensed data, deliberately not collected; the Ohio
  locations list is a pure directory. Merge plan extended to
  Cycle 15. 9 new tests, suite 638.
  Full detail: `docs/plans/overnight-cycle-16-report.md`.
- **Cycle 17** (`overnight/grainhub-cycle-17`; commits `7187c16`,
  `6154176`): source-catalogue audit, 0 GETs — 15 verified toml
  entries enabled in `us_elevators_urls.toml` (10 Cycle 4/5 Bushel
  sites, Ace Ethanol, Alliance Grain, AGP, 2 USDA mirrors); CRC
  reclassified `unknown → stonex`; Collwest comment corrected
  (country confirmed Canadian, entry stays disabled as a record).
  Basis tracker + source health verified already real (no rewire);
  price-history endpoints now return `source` and `as_of` on
  every response and the web `/history` page threads them through
  (2 new tests); report calendar verified already correctly
  wired. Super-plan §9 extended to Cycle 16. Drift found, not
  fixed: `config.toml` `[us]` list stale (30 vs 122 entries).
  5 new tests, suite 643.
  Full detail: `docs/plans/overnight-cycle-17-report.md`.
- **Cycle 18** (`overnight/grainhub-cycle-18`; commits `1ef1da6`,
  `722dd8f`): the Cycle 17 drift resolved — `config.toml` `[us]`
  synced from the urls toml by a new script
  (`scripts/sync_us_elevators_config.py`, idempotent, `--check`
  mode) with a 3-test guard (`test_source_config_sync.py`).
  Mae-Mart proxy identified from page JS (`grain-proxy.php`,
  Yahoo Finance `=F` symbols, futures quotes only — not called,
  next probe named for a later cycle). CGB cash-bid page found
  via site navigation (`cgbgrain.com/cash-bids`, AgriCharts
  embed, 113 locations in the dropdown) — the AgriCharts URL was
  deliberately not fetched; CGB now sits in the licensed-feed
  decision bucket. Unreachable trio re-checked (CVA 202/0 bytes,
  Landus 429 Vercel checkpoint, Mercer Landmark 522/0 bytes) —
  still blocked, toml comments updated only. 3 new tests,
  suite 646.
  Full detail: `docs/plans/overnight-cycle-18-report.md`.

**Count correction carried forward (Cycle 18):** the Cycle 17
report's "122 entries" in `us_elevators_urls.toml` was a grep
artifact — one `[[us.elevators]]` string appears in a comment in
the urls file header, so `grep -c` overcounts by one. The true
count is **121 entries in both files, 102 enabled**, verified
with `tomllib` by the coordinator. Use 121, not 122, from here
on.

### 3d. Gates — updated expectations for Cycles 16–18

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 16: 638, Cycle 17: 643,
   Cycle 18: 646 — **0 failed** at every step.
2. **Web build** — re-run once at the Cycle 17 step (it passed
   there) and once at the Cycle 18 step so the final tree is
   verified as a whole. Only Cycle 17 changed web files, so a
   build failure at the Cycle 16 or 18 step would point at an
   earlier cycle, not the branch being merged.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycles 16–18 (`git log` on
   the Alembic versions dir in `cycle-15..cycle-18` is empty, and
   the file list at the Cycle 18 tip is `0001`–`0019`). The only
   two commits ever touching that directory in
   `master..cycle-18` are from Cycle 1 and Cycle 7 (which added
   `0019`). Expect exactly one head, `0019`, at every step 16–18.
4. **Boundary spot-check** — each Cycle 16–18 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 18 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; all three reports state
   none. Note Cycle 18's Mae-Mart and CGB work deliberately did
   not call the identified proxy or the AgriCharts embed URL.

### 4d. Known conflicts and overlaps — Cycles 16–18

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **every** cycle 16–18 as well (all three work
  commits touch it). Same rule as §4: later wins.
- **Source registry** (`app/services/source_registry.py`) —
  touched in **Cycle 16 only** in this range (8 Smithfield
  adapters: batch 5 + Lapaz + Hamer). Cycles 17–18 did not touch
  it. Later wins, never drop a registration.
- **`bushel_source.py`** — touched in **Cycle 16 only** in this
  range (Smithfield `fetch_smithfield_*()` wrappers + the Raeford
  empty-widget comment). Cycles 17–18 did not touch it. Additive
  only; the Wheaton tabbed-widget fallback from Cycle 11 is
  untouched in this range.
- **`us_elevators_urls.toml`** — edited in Cycles 17 and 18, not
  16 (Cycle 16's toml changes went through `config.toml` toggles
  + enabled entries recorded in the catalogue): 15 entries
  enabled + CRC reclassified + Collwest comment (17); the
  unreachable-trio re-check comments (18). The Cycle 18 values
  are the current truth — **121 entries, 102 enabled**.
- **`config.toml`** (`app/platform/market_data/sources/config.toml`)
  — touched in Cycles 16 and 18, not 17: Smithfield toggles (16),
  then the full `[us]` sync from the urls toml by script (18).
  The Cycle 18 synced list is the current truth; the urls toml
  is canonical and the sync script + guard test keep them in
  step. Do not hand-edit the `[us]` list — re-run the script.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in **Cycle 17 only** in this range (progress to Cycle
  16, test chain 179 → 638). Cycles 16 and 18 did not touch it.
  Linear, no conflict expected.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycles 16–18.

### 5d. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 19): `?? .github/` in `git status` on the
  Cycle 19 checkout. Merging Cycles 16–18 as well as 1–15 will
  **not** bring it into `master`. Same remedy as §5: Adam
  re-authenticates `gh` with `workflow` scope, or adds the file
  via the GitHub web UI. Do not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycles 16–18.** No new
  unpushed files, secrets, or held-back work is reported in any
  of the three reports. The §5 review-not-blocker list is
  unchanged: email-bid endpoint public by default, futures
  endpoints return prices `null` until a licensed feed is wired,
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycles 16–18 (not
  blockers):** the Mae-Mart proxy probe (1 GET, gated on whether
  relying on the site's relay of third-party futures + static
  basis is acceptable) and the CGB `cashbids-js.php` question are
  both gated on the licensed-feed decision; the unreachable trio
  (CVA, Landus, Mercer Landmark) stays re-check-only.

### 7d. After the merges — updated

§7 applies with the Cycle 18 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 646 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 18 merge step). The still-open decisions list in §7.4 is
unchanged by Cycles 16–18. Open work carried forward: the
Smithfield + Skyland per-location sweeps are now complete (30 of
31 Smithfield, Raeford posts no public bids); Playwright render
checks (DTN family, FMN filtered view, Mapleview, StoneX, The
Andersons — closed for static collection, browser-only — and now
Landus, Vercel checkpoint); Chadbourn + Hamer + Skyland 3370/3621
staleness watch; Mae-Mart proxy probe; CGB licensed-feed
decision.

## Cycle 19 (added Cycle 20)

### 0e. Branch chain — Cycle 19, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-19` gives **57 commits** (55
through Cycle 18 + 2 in Cycle 19), **0 merge commits**, no
branch points. Cycle 19's first commit `9c96e5c` has parent
`722dd8f` (the Cycle 18 tip), and merge-base(18, 19) is the
Cycle 18 tip `722dd8f`. Per-branch commit count for Cycle 19: 2
(`9c96e5c`, `b47d638`).

That means the §2 procedure continues unchanged: merge Cycle 19
after 18, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-19` tip (`b47d638`) would give the same tree as nineteen
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

(The Cycles 16–18 section's "55 commits master..cycle-18"
figure was re-verified in Cycle 20 and is correct — no
correction needed.)

### 1e. What the branch contains (Cycle 19)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 19 | `b47d638` | 656 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `b47d6381fdc2441b1a5bb40c553d5b6fa39039ee`.
No web files changed in Cycle 19, so there is no fresh
web-build evidence in this range.

- **Cycle 19** (`overnight/grainhub-cycle-19`; commits `9c96e5c`,
  `b47d638`): Mae-Mart futures proxy probed **live** — `GET
  http://www.mae-martfarms.com/grain-proxy.php?symbols=ZCZ26=F`
  answered 301 (http → https), then HTTP 200 JSON matching the
  page JS's documented contract exactly (object keyed by symbol;
  numeric `price`, string `currency` `"USX"`, numeric
  `timestamp` and `fetched`). `fetch_mae_mart()` now fills
  `futures_price` on corn/soy/wheat rows as an optional second
  step (`include_futures=True`, one GET per symbol: `ZCZ26=F`,
  `ZSF27=F`, `ZWN27=F`; `USX` cents ÷ 100, other currencies taken
  as dollars as-is). New helpers `parse_mae_mart_proxy_json()`
  (pure parser; ignores malformed/unknown-symbol entries) and
  `fetch_mae_mart_futures()` (per-symbol failure skipped, never
  fatal); any proxy failure degrades gracefully to the static-only
  rows. Deliberately NOT done: `cash_price` is never computed
  from futures + basis — that remains an open decision. Rye
  untouched. 7 new tests (synthetic fixtures only).
- **Ingestion-orchestrator coverage audit — real gap found and
  fixed:** the scheduled poller (`list_due_sources()` in
  `app/services/source_orchestration.py`) reached only the 5 pilot
  keys (`agricharts`, `glg`, `hensall`, `snobelen`, `andersons`);
  the other 88 of 93 registry adapters were unreachable on
  schedule. The pilot-allowlist clause was removed (9 lines
  changed, comment explains); all 93 adapters are now reachable.
  Remaining gates unchanged; the pilot set still governs
  promotion status and remains the default seed scope. 3
  regression tests in `tests/test_source_orchestration_due_sources.py`
  (verified to fail on pre-fix code via temporary stash, pass
  after). Gaps documented, not fixed: the deployed 08:00/15:00
  cron runs the file-ingestion job, not the poller (scheduling
  decision); US agricharts/DTN urls-toml entries have no registry
  adapter (adapter-shape change needed — registry calls
  `fetch_fn()` with no args, these require a URL); toggled-off
  `bunge` and `mapleview` are still seedable and fetchable (should
  seeding honor `[sources]` toggles? — coordinator to decide).
  10 new tests in total this cycle, suite 646 → 656.
- **Merge plan extended to Cycles 16–18** (184 lines added, 0
  removed). The Cycles 13–15 section's "49 commits" figure
  re-verified correct. One correction recorded: the Cycle 17
  report's "122 entries" was a grep artifact — true count is
  **121 entries, 102 enabled**.
- **Super-plan §9 extended to Cycle 18** (heading/intro now cover
  Cycles 1–18, test chain 179 → 646; Cycle 17 + 18 bullets added;
  blockers updated).
  Full detail: `docs/plans/overnight-cycle-19-report.md`.

### 3e. Gates — updated expectations for Cycle 19

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 19: 656 — **0 failed**.
   (646 at Cycle 18 + 10 new: Mae-Mart 7, orchestration 3.)
2. **Web build** — re-run once at the Cycle 19 step so the final
   tree is verified as a whole. No web files changed in Cycle 19,
   so a build failure at this step would point at an earlier
   cycle, not the branch being merged. Last full pass was
   Cycle 17.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycle 19 (`git log` on
   the Alembic versions dir in `cycle-18..cycle-19` is empty, and
   the file list at the Cycle 19 tip is `0001`–`0019`). The only
   two commits ever touching that directory in
   `master..cycle-19` are from Cycle 1 and Cycle 7 (which added
   `0019`). Expect exactly one head, `0019`, at the Cycle 19 step.
4. **Boundary spot-check** — the Cycle 19 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 19 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; the report states none.
   Note the Mae-Mart proxy probe used one live GET and the
   response's price value was deliberately not copied into any
   doc or the report.

### 4e. Known conflicts and overlaps — Cycle 19

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **Cycle 19** as well (145 lines changed; the
  catalogue note documents the orchestrator gaps found this
  cycle). Same rule as §4: later wins.
- **Source orchestration** (`app/services/source_orchestration.py`)
  — touched in **Cycle 19 only** in this range (pilot-allowlist
  clause removed from `list_due_sources()`, 9 lines). Small,
  coordinator-verified; no other cycle touches this file, so no
  overlap. The behaviour change is real but gated: pilot-only
  deployments are unaffected until an admin seeds `scope=all`.
- **Mae-Mart source** (`app/platform/market_data/sources/mae_mart_source.py`)
  — touched in **Cycle 19 only** in this range (futures-proxy
  fill, 122 lines). Additive optional step; the static-only path
  is unchanged and remains the fallback. No other cycle touches
  this file.
- **Source registry** (`app/services/source_registry.py`) —
  **not** touched in Cycle 19. No new adapters were registered;
  the 93-adapter set is unchanged — the fix only changes which
  seeded sources the scheduled poller reaches.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in **Cycle 19** (progress to Cycle 18, test chain
  179 → 646). Linear, no conflict expected.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 19.

### 5e. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 20): `?? .github/` in `git status` on the
  Cycle 20 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 19 as well as 1–18 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 19.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 19
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 19 (not
  blockers):** computing Mae-Mart `cash_price` from futures +
  static basis (open decision for Adam/the coordinator, gated on
  the licensed-feed decision); scheduling `poll_sources` instead
  of the file-ingestion job in the deployed 08:00/15:00 cron
  (deployment decision); the US agricharts/DTN adapter-shape
  change; whether seeding should honor the `[sources]` toggles
  for `bunge`/`mapleview`.

### 7e. After the merges — updated

§7 applies with the Cycle 19 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 656 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 19 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 19 except for the additions in §5e above.
Open work carried forward: Playwright render checks (DTN family,
FMN filtered view, Mapleview, StoneX, The Andersons — closed for
static collection, browser-only — and Landus, Vercel checkpoint);
Chadbourn + Hamer + Skyland 3370/3621 staleness watch; Mae-Mart
cash-price decision; poller scheduling decision; US agricharts/DTN
adapter gap; `bunge`/`mapleview` toggle question.
