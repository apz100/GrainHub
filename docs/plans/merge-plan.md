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

---

## Cycle 20 (added Cycle 21)

### 0f. Branch chain — Cycle 20, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-20` gives **59 commits** (57
through Cycle 19 + 2 in Cycle 20), **0 merge commits**, no
branch points. Cycle 20's first commit `24a61d0` has parent
`b47d638` (the Cycle 19 tip), and merge-base(19, 20) is the
Cycle 19 tip `b47d638`. Per-branch commit count for Cycle 20: 2
(`24a61d0`, `9329169`).

That means the §2 procedure continues unchanged: merge Cycle 20
after 19, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-20` tip (`9329169`) would give the same tree as twenty
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

(The Cycle 19 section's "57 commits master..cycle-19" figure
was re-verified in Cycle 21 and is correct — no correction
needed.)

### 1f. What the branch contains (Cycle 20)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 20 | `9329169` | 692 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `9329169d6d564107ab93d062d49f4397f2e967bb`.
No web files changed in Cycle 20, so there is no fresh
web-build evidence in this range.

- **Cycle 20** (`overnight/grainhub-cycle-20`; commits `24a61d0`,
  `9329169`): 26 US agricharts/DTN registry adapters wired —
  13 AgriCharts (all static-capable: Ag Plus, Farmers Win Coop,
  Heartland Coop, Heritage Grain Cooperative, Keller, Kokomo
  Grain, Legacy Farmers, Pro Ag, West-Con, Wheaton Dumont,
  Central Farmers Coop, Anthony Farmers Co-op, Mulvane Coop)
  and 13 DTN (all JS-only: Ag Partners, Al-Corn, Allied
  Cooperative, Aurora Coop, CFS, Elite Octane, Frontier Coop,
  Green Plains, Kanza Coop, Sunrise, Brubaker Grain, Hoffman Ag,
  Wilton Farmers Union Elevator). `US_AGRICHARTS_SITES` map +
  13 zero-arg `fetch_<slug>()` wrappers calling
  `fetch_us_agricharts(url, name)`; `US_DTN_SITES` map + 13
  wrappers calling `fetch_us_dtn(url, name, None)`; plus an
  explicit guard at the top of `fetch_us_dtn`: with
  `playwright=None` it returns an empty DataFrame before
  touching Playwright or the network. 26 new `[sources]`
  toggles (none pre-existed, no existing value touched):
  agricharts 13 = `true`, DTN 13 = `false` (JS-only, same
  precedent as `bunge`/`mapleview`). All 26 wired into
  `source_registry.py` by the coordinator (mode `"direct"`,
  `15, 90`, like the other adapters); registry now holds **119
  adapters** (93 + 26). Frontier Coop is StoneX, not DTN —
  flagged in code, catalogue, and toggles; the DTN adapter
  returns empty for it by design. 30 new tests (synthetic
  fixtures only, generic fetch mocked, no network). **0 web
  fetches this cycle** — live verification of the 13
  agricharts wrappers (1 GET each) and a Playwright render
  check per DTN page (Al-Corn and Sunrise first) are later-cycle
  work; DTN toggles must stay `false` until then.
- **Seeding + poller honour `[sources]` toggles (Cycle 19 gap
  closed):** new `app/services/source_toggles.py` — single place
  the FastAPI side consults the toggles, reusing the existing
  loader (`source_enabled()`, "missing toggle = enabled"); only
  an explicit `false` disables an adapter, and an
  unreadable/missing config fails open rather than breaking
  seed/poll. `seed_sources_from_registry()` now returns a
  `SeedSourcesResult(created, skipped_disabled)` and skips any
  adapter whose toggle is off; today `seed scope=all` creates
  **104 rows** (119 adapters − 15 toggled off: bunge, mapleview,
  13 DTN) and reports `skipped_disabled` with all 15 keys.
  `list_due_sources()` filters out rows whose adapter toggle is
  off, even if the `Source` row already exists (defence in
  depth). `POST /api/sources/seed` now returns `{"created",
  "skipped_disabled", "scope", "adapter_keys"}`. 6 new tests in
  `tests/test_source_toggle_gating.py`. **Coordinator fix during
  wiring:** adding the 26 adapters broke 8 tests whose count
  assertions hardcoded "only bunge/mapleview are disabled";
  fixed by deriving the disabled set from the real toggles
  (`disabled_adapter_keys(sorted(ADAPTERS))`) in both test
  files — no production code changed for this. 36 new tests in
  total this cycle, suite 656 → 692.
- **Deployment note:** `docs/plans/deployment-checklist.md` §4
  step 6 (new) + §8 checkbox — schedule the poller as a second
  cron job alongside the file job, with the consequence stated.
  Exact invocation verified from code:
  `python -m app.jobs.poll_sources` (run from `apps/api` with
  the API's env; default one-shot run; `--loop --sleep-seconds
  60` for continuous). No deployment config or cron was changed.
  Note also recorded: the poller errors out if the `Commodity`
  table is empty, so at least one Commodity row must exist
  before the first run.
- **Merge plan extended to Cycle 19** (176 lines added, 0
  removed). The Cycles 16–18 section's "55 commits" figure
  re-verified correct.
- **Super-plan §9 extended to Cycle 19** (heading/intro now
  cover Cycles 1–19, test chain 179 → 656; Cycle 19 bullet
  added; blockers updated — poller reaches all 93 adapters,
  now 119 with the new ones, but the deployed cron still runs
  the file job, not the poller; Mae-Mart proxy live).
  Full detail: `docs/plans/overnight-cycle-19-report.md` for the
  merge-plan/super-plan work and
  `docs/plans/overnight-cycle-20-report.md` for this cycle.

### 3f. Gates — updated expectations for Cycle 20

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 20: 692 — **0 failed**.
   (656 at Cycle 19 + 36 new: agricharts/DTN adapters 30,
   toggle gating 6.)
2. **Web build** — re-run once at the Cycle 20 step so the final
   tree is verified as a whole. No web files changed in Cycle 20,
   so a build failure at this step would point at an earlier
   cycle, not the branch being merged. Last full pass was
   Cycle 17.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycle 20 (`git log` on
   the Alembic versions dir in `cycle-19..cycle-20` is empty, and
   the file list at the Cycle 20 tip is `0001`–`0019`). The only
   two commits ever touching that directory in
   `master..cycle-20` are from Cycle 1 and Cycle 7 (which added
   `0019`). Expect exactly one head, `0019`, at the Cycle 20 step.
4. **Boundary spot-check** — the Cycle 20 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 20 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; the report states none.

### 4f. Known conflicts and overlaps — Cycle 20

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **Cycle 20** as well (200 lines changed; the 26
  new sites documented, Frontier Coop flagged StoneX). Same rule
  as §4: later wins.
- **`us_agricharts_source.py` + `us_dtn_source.py`** — both **new
  files** in Cycle 20 (127 + 211 lines: the site maps, the 26
  zero-arg wrappers, and the `fetch_us_dtn` `playwright=None`
  guard). No earlier cycle touches either file, so no overlap;
  the guard is additive and legacy GrainBidder calls with a real
  playwright are unaffected.
- **`config.toml`**
  (`app/platform/market_data/sources/config.toml`) — touched in
  Cycle 20 (31 lines: the 26 new `[sources]` toggles, none
  pre-existed, no existing value touched). The Cycle 18 synced
  `[us]` list is the base; the toggles here are purely additive.
- **Source registry** (`app/services/source_registry.py`) —
  touched in **Cycle 20** (26 lines: the 26 adapter
  registrations, mode `"direct"`, `15, 90`). Later wins, never
  drop a registration. Registry now holds 119 adapters.
- **Source toggles** (`app/services/source_toggles.py`) — **new
  file** in Cycle 20 (52 lines: `is_adapter_enabled`,
  `disabled_adapter_keys`). No earlier cycle touches it; it is
  the single place the FastAPI side consults the toggles.
- **Source orchestration** (`app/services/source_orchestration.py`)
  — touched in **Cycle 20** (32 lines: seed + due-list toggle
  gating) and in **Cycle 19** (pilot-allowlist removal from
  `list_due_sources()`). Both changes live in the same
  functions' neighbourhood, so a careless resolve could drop
  either the allowlist removal or the toggle gating — sequential
  merge carries both; verify both behaviours survive (the
  toggle-gating tests and the Cycle 19 orchestration regression
  tests). `app/api/routes/sources.py` was also touched in
  Cycle 20 (9 lines: the seed response shape); no earlier cycle
  touches it.
- **Deployment checklist** (`docs/plans/deployment-checklist.md`)
  — touched in Cycle 20 (§4 step 6 new + §8 checkbox: poller as
  a second cron). Additive; no deployment config or cron was
  changed.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in **Cycle 20** (progress to Cycle 19, test chain
  179 → 656). Linear, no conflict expected.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 20.

### 5f. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 21): `?? .github/` in `git status` on the
  Cycle 21 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 20 as well as 1–19 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 20.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 20
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 20 (not
  blockers):** live verification of the 13 agricharts wrappers
  (1 GET each); Playwright render check per DTN page (Al-Corn +
  Sunrise first — classic shape the generic was written for);
  Frontier Coop needs a StoneX collector as a separate
  later-cycle item (the DTN adapter returns empty for it by
  design); DTN toggles stay `false` until verified; scheduling
  the poller as a second cron job (deployment decision,
  checklist §4 step 6); Mae-Mart `cash_price` from futures +
  static basis (still open, gated on the licensed-feed
  decision); at least one `Commodity` row must exist before the
  first poller run.

### 7f. After the merges — updated

§7 applies with the Cycle 20 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 692 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 20 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 20 except for the additions in §5f above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint); live
verification of the 13 agricharts wrappers; Chadbourn + Hamer +
Skyland 3370/3621 staleness watch; Mae-Mart cash-price decision;
poller scheduling decision; currency decision.

## Cycle 21 (added Cycle 22)

### 0g. Branch chain — Cycle 21, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-21` gives **61 commits** (59
through Cycle 20 + 2 in Cycle 21), **0 merge commits**, no
branch points. Cycle 21's first commit `38bf6d5` has parent
`9329169` (the Cycle 20 tip), and merge-base(20, 21) is the
Cycle 20 tip `9329169`. Per-branch commit count for Cycle 21: 2
(`38bf6d5`, `726f865`).

That means the §2 procedure continues unchanged: merge Cycle 21
after 20, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-21` tip (`726f865`) would give the same tree as twenty-one
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

(The Cycle 20 section's "59 commits master..cycle-20" figure
was re-verified in Cycle 22 and is correct — no correction
needed.)

### 1g. What the branch contains (Cycle 21)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 21 | `726f865` | 692 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `726f865d97f5fb4f2d0329010c37913f5d408848`.
No web files changed in Cycle 21, so there is no fresh
web-build evidence in this range. **No code changed at all in
Cycle 21** — docs only (4 files: merge plan, super-plan §9,
price-source catalogue, the Cycle 21 report itself) — so the
test count is unchanged from Cycle 20 and no new tests were
added.

- **Cycle 21** (`overnight/grainhub-cycle-21`; commits `38bf6d5`,
  `726f865`): live verification of the 13 agricharts wrappers
  wired in Cycle 20 — **11 of 13 return rows, 642 rows total**
  (13 GETs, 1 per wrapper). Batch A, 353 rows: Ag Plus 36 (Corn
  12, Beans 12, Wheat 12; 6 locations), Farmers Win Coop 171
  (Corn 90, Soybeans 81; 18 locations), Keller 14 (Corn 7,
  Soybeans 7; 1 location), Kokomo Grain 63 (Corn 29, Soybeans
  24, Wheat 5, NGMO Waxy 5; 8 locations), Legacy Farmers 66
  (Beans 25, Corn 24, Wheat 17; 10 locations). Batch B, 289
  rows: Pro Ag 78 (Soybeans 35, Corn 31, Wheat 12; 6
  locations — identical count/locations to Cycle 11), West-Con
  84 (Soybeans 44, Corn 30, DNS Wheat 10; 1 fallback location —
  page has no `<h4>` headings — identical count to Cycles
  11–12, month-name deliveries kept verbatim), Wheaton Dumont
  43 (Corn 18, Soybeans 16, Spring Wheat 9; 8 locations —
  identical count to Cycle 12, short month labels kept
  verbatim), Central Farmers Coop 75 (Corn 44, Soybeans 30,
  Winter Wheat 1; 11 locations — first live verification, was
  Cycle 1 HTML only), Anthony Farmers Co-op 9 (Corn 3, Milo 3,
  Soybeans 3; 3 locations — first live verification; thin but
  structurally sound, 3 locs × 3 commodities, single delivery
  09/01/2026). All returning wrappers produced the standard
  10-column DataFrame. No wrapper bugs were found, so no code
  was changed.
- **Two site-side failures, same cause:** Heartland Coop and
  Mulvane Coop both return 0 rows — HTTP 200, but the page no
  longer carries the `jsquote.php` script tag the generic
  parser requires, so `fetch_us_agricharts` returns empty
  before parsing. Wrapper URLs/names verified correct against
  the toml and Cycle 1 discovery. Needs a re-probe in a later
  cycle (1 GET each); a future generic-collector fix
  (alternate futures source) would cover both. Two of 13 sites
  failing the same way suggests AgriCharts may be rolling out
  a template change.
- **Heritage Grain Cooperative — partial (3 rows):** rows parse,
  but `Location` values are the commodity names ("CORN - CASH"
  etc.) because the page's `<h4>` tags are commodity headings,
  not location names — the generic parser's h4-as-location
  assumption mislabels them. Open follow-up: does the page
  genuinely list only 3 cash bids, or are more rows in a shape
  the `writeBidRow` regex skips? A parser-level fix (detect
  h4-as-commodity pages) is a later-cycle item.
- **User-Agent discrepancy (noted, not changed):** the task brief
  said the fetch functions send `GrainHub-Research/1.0`, but
  `_HEADERS` in `us_agricharts_source.py` actually sends a
  Chrome `Mozilla/5.0` UA. Wrappers were run as-is with no
  override. The coordinator independently confirmed the Chrome
  UA in the source (pre-existing from Cycle 1). Changing the UA
  is a deliberate decision for a later cycle, not something
  altered here.
- **Price-source catalogue edited** (173 insertions, 24
  deletions — 197 lines changed): the 13-wrapper verification
  results, the Heartland/Mulvane failures, and the Heritage
  h4 note recorded.
- **Merge plan extended to Cycle 20** (227 lines added, 0
  removed). The Cycle 19 section's "57 commits" figure
  re-verified correct.
- **Super-plan §9 extended to Cycle 20** (heading/intro now
  cover Cycles 1–20, test chain 179 → 692; Cycle 20 bullet
  added; blockers updated — registry 119 adapters, DTN toggles
  off awaiting Playwright).
  Full detail: `docs/plans/overnight-cycle-21-report.md`.

### 3g. Gates — updated expectations for Cycle 21

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 21: 692 — **0 failed**.
   (Unchanged from Cycle 20 — no code changed in this cycle, so
   no new tests.)
2. **Web build** — re-run once at the Cycle 21 step so the final
   tree is verified as a whole. No web files changed in Cycle 21,
   so a build failure at this step would point at an earlier
   cycle, not the branch being merged. Last full pass was
   Cycle 17.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycle 21 (`git log` on
   the Alembic versions dir in `cycle-20..cycle-21` is empty, and
   the file list at the Cycle 21 tip is `0001`–`0019`). The only
   two commits ever touching that directory in
   `master..cycle-21` are from Cycle 1 and Cycle 7 (which added
   `0019`). Expect exactly one head, `0019`, at the Cycle 21 step.
4. **Boundary spot-check** — the Cycle 21 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 21 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; the report states none.

### 4g. Known conflicts and overlaps — Cycle 21

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **Cycle 21** as well (197 lines changed; the 13
  agricharts-wrapper verification results, the Heartland/Mulvane
  failures, the Heritage h4 note). Same rule as §4: later wins.
- **Merge plan** (`docs/plans/merge-plan.md`) — extended in
  Cycle 21 (227 lines added, 0 removed: the Cycle 20 section).
  Additive; no earlier text touched.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in **Cycle 21** (progress to Cycle 20, test chain
  179 → 692). Linear, no conflict expected.
- **No collector code changed in Cycle 21** — no overlap with
  any code file. In particular `app/services/source_registry.py`
  was not touched this cycle (last touched in Cycle 20 with the
  26 adapter registrations — nothing to carry here), and neither
  `us_agricharts_source.py` nor `us_dtn_source.py` was touched:
  verification found no wrapper bugs to fix.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 21.

### 5g. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 22): `?? .github/` in `git status` on the
  Cycle 22 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 21 as well as 1–20 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 21.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 21
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 21 (not
  blockers):** Heartland + Mulvane re-probes (1 GET each);
  Heritage h4-as-commodity parser question (detect
  h4-as-commodity pages, or confirm the page genuinely lists
  only 3 bids); agricharts User-Agent decision (Chrome UA vs
  `GrainHub-Research/1.0`); the Cycle 20 open item "live
  verification of the 13 agricharts wrappers" is now closed
  except for the two failing sites; Playwright render checks
  still pending (DTN family — Al-Corn + Sunrise first — FMN
  filtered view, Mapleview, StoneX including Frontier, The
  Andersons — closed for static collection, browser-only — and
  Landus, Vercel checkpoint); DTN toggles stay `false` until
  verified; scheduling the poller as a second cron job
  (deployment decision, checklist §4 step 6); Mae-Mart
  `cash_price` from futures + static basis (still open, gated
  on the licensed-feed decision); at least one `Commodity` row
  must exist before the first poller run.

### 7g. After the merges — updated

§7 applies with the Cycle 21 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 692 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 21 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 21 except for the additions in §5g above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Heartland + Mulvane re-probes; Heritage parser question;
agricharts User-Agent decision; Chadbourn + Hamer + Skyland
3370/3621 staleness watch; Mae-Mart cash-price decision;
poller scheduling decision; currency decision.

## Cycle 22 (added Cycle 23)

### 0h. Branch chain — Cycle 22, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-22` gives **63 commits** (61
through Cycle 21 + 2 in Cycle 22), **0 merge commits**, no
branch points. Cycle 22's first commit `f250e8c` has parent
`726f865` (the Cycle 21 tip), and merge-base(21, 22) is the
Cycle 21 tip `726f865`. Per-branch commit count for Cycle 22: 2
(`f250e8c`, `7704d02`).

That means the §2 procedure continues unchanged: merge Cycle 22
after 21, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-22` tip (`7704d02`) would give the same tree as twenty-two
sequential merges; prefer the sequential merges for the same
reason as §0 (a review checkpoint and stop point per cycle).

(The Cycle 21 section's "61 commits master..cycle-21" figure
was re-verified in Cycle 23 and is correct — no correction
needed.)

### 1h. What the branch contains (Cycle 22)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 22 | `7704d02` | 696 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `7704d0294a623168f869589e40e0d9708c660f55`.
No web files changed in Cycle 22, so there is no fresh
web-build evidence in this range. 7 files changed in Cycle 22
(799 insertions, 33 deletions): the collector fix, its tests
and fixture, the price-source catalogue, the merge plan, the
super-plan §9, and the Cycle 22 report itself.

- **Cycle 22** (`overnight/grainhub-cycle-22`; commits `f250e8c`,
  `7704d02`): Heritage Grain Cooperative parser fix — the page
  lists **14 `writeBidRow` bids, not 3**. The 11 forward-month
  rows (CORN/BEANS DEC 2026, JAN/FEB/MAR 2027, FALL 2027; WHEAT
  JUL 2027) were skipped because their delivery label sits in
  the notes argument with an escaped quote (`'DEC \'26'` etc.)
  and the regex's group/notes fields were `'[^']*'`, which
  stops at the escaped quote and fails the whole row. Fix is in
  the generic collector (`us_agricharts_source.py`, 49
  insertions, 3 deletions): group (arg 9) and notes (arg 10)
  changed from `'[^']*'` to `'(?:[^'\\]|\\.)*'`. Verified
  offline against the saved capture: 14/14 rows match (was
  3/14), and end-to-end with mocked futures: 14 rows, single
  location `Heritage Grain Cooperative - Heritage Grain
  Cooperative`. New `_is_commodity_heading(h4_text, row_name)`:
  true when the `<h4>` exactly equals the row's commodity name
  (case-insensitive) or starts with a commodity word; such rows
  fall back to the company name as location (same `Company -
  Company` shape West-Con already produces), with a
  word-boundary check keeping real place names out
  (`Wheatland`, `Cornwall` tested). **4 new tests** (escaped-
  quote regex parsing, `_is_commodity_heading` unit cases,
  mocked-HTTP end-to-end fallback with a genuine `Riverside`
  heading still used, and a structure-only saved-HTML test
  that skips if the capture is absent) plus a synthetic
  fixture (all values invented, neutral `Test Elevator`
  naming). The coordinator independently verified the fix
  against the saved capture: 14 matches (was 3),
  `jsquote.php` tag present. No live re-call of the Heritage
  wrapper after the fix — the 3-GET budget was spent; the next
  live wrapper call should return 14 rows (1 GET, later cycle).
- **Heartland + Mulvane re-probes — still failing (2 GETs):**
  both return 0 rows, HTTP 200, `[US-AG WARN] ... jsquote
  script tag not found in page` — same failure as Cycle 21,
  second consecutive failure each, so not transient. Wrappers
  unchanged. Worker recommendation (recorded, not acted on):
  either a generic-collector alternate futures source (covers
  both at once, as Cycle 21 anticipated) or flip both toggles
  to `false`. Do not re-probe them every cycle without a fix
  plan.
- **Staleness re-checks — watch UNCHANGED (4 GETs):** Smithfield
  Chadbourn 2294 (1 row, Soybeans), Smithfield Hamer 2179 (1
  row, Soybeans), Skyland Hugoton 3370 (6 rows), Skyland
  Vilas-Walsh 3621 (5 rows) — all HTTP 200 with header **Wed,
  Nov 18, 2026**, all still exactly one day behind. Chadbourn
  is on its 3rd consecutive stale probe (Cycles 13, 14, 22);
  Hamer, Hugoton, and Vilas-Walsh on their 2nd each. The lag
  is persistent, not worsening. The standing collector note
  stands: a same-day freshness gate would fail these four
  daily, so they need an exemption/lag tolerance if such a
  gate is ever added. A daytime re-check in a later cycle
  could test whether the widgets refresh later in the day
  rather than overnight. The coordinator independently
  confirmed the Nov 18 headers in the saved Chadbourn +
  Hugoton files. (URL note: the task brief listed the
  Smithfield URLs with a `www.` prefix, but the registry
  records them without it — the worker used the registry
  URLs, correctly.)
- **Price-source catalogue edited** (213 insertions, 14
  deletions — 227 lines changed): the Heritage 14-row
  finding and parser fix, the Heartland/Mulvane second
  consecutive failures, and the unchanged staleness watch.
- **Merge plan extended to Cycle 21** (200 lines added, 0
  removed). The Cycle 20 section's "59 commits" figure
  re-verified correct in Cycle 22.
- **Super-plan §9 extended to Cycle 21** (26 insertions, 16
  deletions — heading/intro now cover Cycles 1–21, test chain
  179 → 692; Cycle 21 bullet added; blockers updated —
  agricharts wrappers verified, Heartland/Mulvane site-side
  failures, Heritage mislabelling).
- **Boundary applied:** zero references to the excluded
  elevator in any new Cycle 22 code, tests, fixtures, or docs
  (verified by grep on the added lines; the single match in
  the range diff is the report's own boundary-attestation
  heading).
  Full detail: `docs/plans/overnight-cycle-22-report.md`.

### 3h. Gates — updated expectations for Cycle 22

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 22: 696 — **0 failed**.
   (Cycle 21 ended at 692; Cycle 22 adds 4 Heritage parser
   tests.)
2. **Web build** — re-run once at the Cycle 22 step so the final
   tree is verified as a whole. No web files changed in Cycle 22,
   so a build failure at this step would point at an earlier
   cycle, not the branch being merged. Last full pass was
   Cycle 17.
3. **Alembic chain** — head is **still `0019`**. Verified from
   git: no migration file was added in Cycle 22 (`git log` on
   the Alembic versions dir in `cycle-21..cycle-22` is empty, and
   the file list at the Cycle 22 tip is `0001`–`0019`). The only
   two commits ever touching that directory in
   `master..cycle-22` are from Cycle 1 and Cycle 7 (which added
   `0019`). Expect exactly one head, `0019`, at the Cycle 22 step.
4. **Boundary spot-check** — the Cycle 22 report has its own
   boundary section (zero new references, verified by grep on the
   added lines). Re-check once at the Cycle 22 step as in §3.4.
5. **No-secrets spot-check** — as §3.5; the report states none.

### 4h. Known conflicts and overlaps — Cycle 22

The chain is still linear, so a sequential merge still produces
no conflicts. The §4 watch-list extends as follows:

- **Price-source catalogue** (`docs/plans/price-source-catalogue.md`)
  — edited in **Cycle 22** as well (227 lines changed; the
  Heritage 14-row finding and parser fix, the Heartland/Mulvane
  second failures, the unchanged staleness watch). Same rule as
  §4: later wins.
- **Merge plan** (`docs/plans/merge-plan.md`) — extended in
  Cycle 22 (200 lines added, 0 removed: the Cycle 21 section).
  Additive; no earlier text touched.
- **Super-plan §9** (`docs/plans/grainhub-super-plan.md`) —
  updated in **Cycle 22** (progress to Cycle 21, test chain
  179 → 692). Linear, no conflict expected.
- **`us_agricharts_source.py`** — touched in **Cycle 22** (49
  insertions, 3 deletions: the escaped-quote regex fix and the
  `_is_commodity_heading` fallback). Last touched before that in
  Cycle 20 (the 26 adapter wirings) and Cycle 12 (the West-Con
  regex fix), so no other cycle in the chain edits the same
  lines in this range; the Cycle 22 change applies cleanly on
  top of the Cycle 20 version. Its test file
  (`tests/test_us_agricharts_source.py`, +123 lines, 4 new
  tests) and the new synthetic fixture
  (`tests/fixtures/us_agricharts_heritage_sample.html`, +26
  lines) are likewise Cycle 22-only in this range.
- **No registry changes in Cycle 22** — `app/services/
  source_registry.py` was not touched this cycle (`git log` on
  it in `cycle-21..cycle-22` is empty); no adapter, toggle, or
  registration change to carry. Neither `us_dtn_source.py` nor
  any other collector file was touched.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 22.

### 5h. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 23): `?? .github/` in `git status` on the
  Cycle 23 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 22 as well as 1–21 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 22.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 22
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 22 (not
  blockers):** Heritage live confirmation (1 GET, expect 14
  rows); Heartland + Mulvane decision (generic-collector
  alternate futures source vs toggles off — do not re-probe
  without a fix plan); staleness watch (Chadbourn 3rd
  consecutive stale probe, Hamer + Skyland 3370/3621 2nd each,
  all exactly one day behind; daytime re-check could test
  whether widgets refresh later in the day); agricharts
  User-Agent decision (Chrome UA vs `GrainHub-Research/1.0`);
  Playwright render checks still pending (DTN family — Al-Corn
  + Sunrise first — FMN filtered view, Mapleview, StoneX
  including Frontier, The Andersons — closed for static
  collection, browser-only — and Landus, Vercel checkpoint);
  DTN toggles stay `false` until verified; scheduling the
  poller as a second cron job (deployment decision, checklist
  §4 step 6); Mae-Mart `cash_price` from futures + static basis
  (still open, gated on the licensed-feed decision); at least
  one `Commodity` row must exist before the first poller run.

### 7h. After the merges — updated

§7 applies with the Cycle 22 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 696 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 22 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 22 except for the additions in §5h above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Heritage live confirmation (expect 14 rows); Heartland +
Mulvane decision; Chadbourn + Hamer + Skyland 3370/3621
staleness watch; agricharts User-Agent decision; Mae-Mart
cash-price decision; poller scheduling decision; currency
decision.

## Cycle 23 (added Cycle 24)

### 0i. Branch chain — Cycle 23, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-23` gives **65 commits** (63
through Cycle 22 + 2 in Cycle 23), **0 merge commits**, no
branch points. Cycle 23's first commit `c9c9c2e` has parent
`7704d02` (the Cycle 22 tip), and merge-base(22, 23) is the
Cycle 22 tip `7704d02`. Per-branch commit count for Cycle 23: 2
(`c9c9c2e`, `9f534e6`).

That means the §2 procedure continues unchanged: merge Cycle 23
after 22, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-23` tip (`9f534e6`) would give the same tree as
twenty-three sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 22 section's "63 commits master..cycle-22" figure
was re-verified in Cycle 24 and is correct — no correction
needed.)

### 1i. What the branch contains (Cycle 23)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 23 | `9f534e6` | 697 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `9f534e6be9c3c03d172dfa7b14149dfcf065c079`.
No web files changed in Cycle 23, so there is no fresh
web-build evidence in this range. 8 files changed in Cycle 23
(756 insertions, 39 deletions): the toggle flip, its tests, the
price-source catalogue, the new futures-fallback design note,
the merge plan, the super-plan §9, and the Cycle 23 report
itself.

- **Cycle 23** (`overnight/grainhub-cycle-23`; commits `c9c9c2e`,
  `9f534e6`): Heritage Grain Cooperative live confirmation —
  one live wrapper call, `fetch_heritage_grain_cooperative()`,
  returned **14 rows** (CORN 6, BEANS 6, WHEAT 2; deliveries Oct
  2026–Nov 2027), all with the company fallback location
  `Heritage Grain Cooperative - Heritage Grain Cooperative`,
  exactly as the Cycle 22 parser fix predicted. The Cycle 22
  follow-up is closed. No live price/basis/bid recorded
  anywhere — counts and structure only.
- **Heartland + Mulvane toggles flipped to `false`** (coordinator
  decision): `heartland_coop` and `mulvane_coop` in `config.toml`
  `[sources]`, each with a Cycle 23 comment (two consecutive
  0-row probes, Cycles 21–22; `jsquote.php` tag missing; poller
  would fetch daily for nothing; reversible;
  `us_elevators_urls.toml` entries stay enabled — the toggle is
  the gate). Not re-probed this cycle, per the decision.
  Wrappers/registry rows unchanged, so re-enabling is a one-line
  flip. **Seed count 104 → 102** (119 adapters − 17 toggled off:
  bunge, mapleview, 13 DTN, Heartland, Mulvane). **1 new test**
  (`test_cycle23_zero_row_agricharts_adapters_toggled_off` in
  `tests/test_source_toggle_gating.py`: both toggles false, both
  in the derived disabled set, siblings
  `heritage_grain_cooperative`/`keller` still on, explicit-key
  seed of both + `keller` creates only `keller` and records both
  in `skipped_disabled`, pre-existing rows for both stay out of
  the due list) plus an update to
  `test_config_toggles_exist_for_all_new_adapters` (now expects
  `false` for exactly `heartland_coop`/`mulvane_coop`, all other
  AgriCharts toggles still `true`). No hardcoded seeded count
  anywhere — the gating/orchestration tests derive the disabled
  set from the real toggles. Self-inflicted break, fixed by the
  worker before commit: an edit dropped the newline after a test
  function definition, producing an `IndentationError` caught on
  the first suite run (collection error, 0 tests ran); fixed the
  line, re-ran, suite green at 697.
- **AgriCharts futures-fallback design note** (design only, 0
  GETs): new `docs/plans/agricharts-futures-fallback-design.md`
  (170 lines). Field analysis verified against the code:
  `writeBidRow` args carry, with no jsquote feed needed, Name
  (arg 0), **Basis in ¢/bu (arg 1, signed — in the row itself)**,
  Delivery/Delivery End (args 6–7), Location (surrounding
  `<h4>`, company fallback), futures symbol (arg 14).
  Feed-dependent: Futures Price (`last`) and Bushel/MT Cash
  Price (computed as futures + basis). Either: Futures Month —
  taken from the feed's `month` field today, but decodable from
  the symbol (FMN does exactly this). Neither: Change is
  hardcoded `""` — the collector never fills it, feed or no
  feed. Current behaviour: missing tag → warning + empty
  DataFrame before any row parsing. FMN degrades instead
  (parses the page, leaves futures/change/cash `None` with a
  note, decodes month from the symbol). **Recommendation: (a)
  parse rows with futures/cash `None` (FMN precedent), with the
  (b) probe run first on Heartland only.** (b) (derive the feed
  URL from row symbols, `varname=quotes`) is worth a 2-GET
  Heartland probe first since full rows would be strictly better
  if the feed still answers, but (b) alone leaves the collector
  brittle the next time a tag disappears. (c) (leave as-is,
  toggles off) and (d) (futures from another feed — parked,
  month-matching risk) are documented with pros/cons. **Decision
  needed from Adam/coordinator:** approve (a) for implementation
  in a later cycle, including two sub-decisions: (i) whether
  basis-only rows may flow into the pipeline or should be
  flagged/quarantined until proven; (ii) whether Futures Month
  may be decoded from the symbol. Toggles stay off until (a) is
  implemented and at least one site is probe-confirmed returning
  rows; re-enabling is a separate step. (Cycle 24 note: the
  coordinator approved (a) — basis-only rows may flow with
  explicit `None`, no quarantine; month decoding approved. See
  the Cycle 24 report.)
- **Coordinator decision recorded: agricharts UA stays Chrome.**
  The Cycle 21 finding (the collector sends a Chrome
  `Mozilla/5.0` UA, not `GrainHub-Research/1.0`) is kept as-is:
  pre-existing Cycle 1 behaviour, it works, changing it risks
  fetches being blocked as non-browser traffic. Research probes
  continue to use `GrainHub-Research/1.0`.
- **Price-source catalogue edited:** the Heritage live
  confirmation, the Heartland/Mulvane toggle-off (split to note:
  toml `enabled` stays `true`, the `[sources]` toggle is the
  gate), and the design-note summary.
- **Merge plan extended to Cycle 22** (226 lines added, 0
  removed). The Cycle 21 section's "61 commits" figure
  re-verified correct in Cycle 23.
- **Super-plan §9 extended to Cycle 22** (heading/intro now
  cover Cycles 1–22, test chain 179 → 696; Cycle 22 bullet
  added; blockers updated).
- **Boundary applied:** zero references to the excluded
  elevator in any new Cycle 23 code, tests, fixtures, or docs
  (verified by grep on the added lines).
  Full detail: `docs/plans/overnight-cycle-23-report.md`.

### 3i. Gates — updated expectations for Cycle 23

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 23: 697 — **0 failed**.
   (Cycle 22 ended at 696; Cycle 23 adds 1 toggle-gating test.)
2. **Web build** — re-run once at the Cycle 23 step so the final
   tree is verified as a whole. No web files changed in Cycle 23,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Cycle 23 adds no migration.
4. **Boundary spot-check** — grep the Cycle 23 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs.
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 23 diff (none are reported).

### 4i. Known conflicts and overlaps — Cycle 23

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 23's additions are
  the Heritage confirmation, the toggle-off, and the design-note
  summary; no earlier text was rewritten), the merge plan
  (pure append of the Cycle 22 section), the super-plan §9
  (Cycle 22 bullet + blockers update; no earlier bullet was
  rewritten). `config.toml` `[sources]` was last touched in
  Cycle 20 (26 new toggles) — Cycle 23 flips two values in place
  and adds a comment per key; no structural conflict.
  `test_source_toggle_gating.py` was created in Cycle 20 and
  extended in Cycle 23 (one new test appended; the
  `test_seed_skips_toggled_off_adapters_and_records_them`
  function was not edited — the worker's `IndentationError`
  came from a dropped newline after that function's def line
  and was fixed in place before commit, with no change to the
  function's body or semantics).
- **No new collector, registry, or adapter code in Cycle 23.**
  `us_agricharts_source.py`, `source_registry.py`, and
  `app/main.py` were not touched this cycle (`git log` on them
  in `cycle-22..cycle-23` is empty); no adapter, toggle-shape,
  or registration change to carry beyond the two value flips.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 23.

### 5i. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 24): `?? .github/` in `git status` on the
  Cycle 24 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 23 as well as 1–22 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 23.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 23
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 23 (not
  blockers):** AgriCharts fallback (a) implementation approval
  (approved by the coordinator in Cycle 24 — basis-only rows may
  flow, month decoded from symbol; implementation in Cycle 24);
  Heartland filtered-view probe (`cash.php?location_filter=<id>`,
  1 GET, later cycle — rows may appear only under a selected
  location); staleness watch (Chadbourn 4th consecutive stale
  probe, Hamer + Skyland 3370/3621 3rd each after the Cycle 24
  daytime re-check, all exactly one day behind; the
  refresh-later-in-the-day hypothesis is now answered — no — so
  no further daytime re-checks are needed; the four stay on the
  exemption list for any future freshness gate); agricharts
  User-Agent decision (resolved in Cycle 23 — Chrome UA kept);
  Playwright render checks still pending (DTN family — Al-Corn
  + Sunrise first — FMN filtered view, Mapleview, StoneX
  including Frontier, The Andersons — closed for static
  collection, browser-only — and Landus, Vercel checkpoint);
  DTN toggles stay `false` until verified; scheduling the
  poller as a second cron job (deployment decision, checklist
  §4 step 6); Mae-Mart `cash_price` from futures + static basis
  (still open, gated on the licensed-feed decision); at least
  one `Commodity` row must exist before the first poller run.

### 7i. After the merges — updated

§7 applies with the Cycle 23 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 697 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 23 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 23 except for the additions in §5i above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
AgriCharts fallback (a) implementation (approved, in Cycle 24);
Heartland filtered-view probe; Chadbourn + Hamer + Skyland
3370/3621 staleness watch (exemption list); Mae-Mart
cash-price decision; poller scheduling decision; currency
decision.

---

## Cycle 24 (added Cycle 25)

### 0j. Branch chain — Cycle 24, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-24` gives **67 commits** (65
through Cycle 23 + 2 in Cycle 24), **0 merge commits**, no
branch points. Cycle 24's first commit `2120e29` has parent
`9f534e6` (the Cycle 23 tip), and merge-base(23, 24) is the
Cycle 23 tip `9f534e6`. Per-branch commit count for Cycle 24: 2
(`2120e29`, `f90cb8b`).

That means the §2 procedure continues unchanged: merge Cycle 24
after 23, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-24` tip (`f90cb8b`) would give the same tree as
twenty-four sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 23 section's "65 commits master..cycle-23" figure
was re-verified in Cycle 25 and is correct — 65, 0 merge
commits. `master` is still at `f2c3206` — no cycle work is on
`master` yet.)

### 1j. What the branch contains (Cycle 24)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 24 | `f90cb8b` | 702 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `f90cb8ba4c9bb20f7d4ea88c616d8e4b408c21a4`.
No web files changed in Cycle 24, so there is no fresh
web-build evidence in this range. 7 files changed in Cycle 24
(788 insertions, 33 deletions): the fallback (a) implementation
and its tests, the design-doc §9 correction, the price-source
catalogue, the merge plan, the super-plan §9, and the Cycle 24
report itself.

- **Cycle 24** (`overnight/grainhub-cycle-24`; commits `2120e29`,
  `f90cb8b`): AgriCharts fallback, option (a) — **implemented +
  tested**. Coordinator decision (Cycle 24, recorded in the
  design doc §9): option (a) from the Cycle 23 design note is
  **APPROVED** — (i) basis-only rows MAY flow into the pipeline
  (futures/cash explicitly `None` with a note, never invented;
  no quarantine, same as FMN today); (ii) YES, decode Futures
  Month from the symbol. `fetch_us_agricharts`
  (`us_agricharts_source.py`, 107 insertions, 26 deletions) no
  longer returns an empty DataFrame when the jsquote tag is
  absent or unmatched: it parses the `writeBidRow` rows as
  basis-only (Basis / Delivery / Delivery End / Location / Name
  / futures symbol as published); **Futures Month decoded from
  the contract symbol** via a new `futures_month_from_symbol()`
  (same month-code map and regex as `fmn_source.
  futures_month_from_symbol`, copied locally to avoid an import
  coupling, since this module is also imported standalone by
  GrainBidder); **Futures Price / Change / Bushel Cash Price /
  MT Cash Price = `None`**, never invented. New `Note` column
  (FMN pattern): basis-only rows carry the note that the values
  come from the page's external quotes feed and are left as
  `None`, never invented, with the month decoded from the
  contract symbol; feed-backed rows carry `""`, so the schema is
  stable across both paths. Tag-present behaviour is **exactly
  unchanged**, including the existing early return when the tag
  is present but the feed returns no data. Chrome UA unchanged.
  No config, registry, or `app/main.py` changes. **Toggles stay
  `false`.** **5 new tests** (142 insertions, 1 deletion in
  `tests/test_us_agricharts_source.py`; 16 tests in that file at
  the tip): (a) no-tag page → 4 rows, basis filled, futures/cash
  all `None` (asserted not `""` and not `0`), note present,
  exactly one GET (no feed fetch attempted); (b) Futures Month
  decoded (`ZCZ26 → Dec 2026`, `ZSF27 → Jan 2027`, `ZSN27 →
  Jul 2027`) plus a decoder unit test (`None`/`""`/unrecognised
  → `None`) — the worker's first expectation for `ZSN27` was
  wrong (`N` is July, not November); the test docstring records
  this; (c) tagged page with mocked feed → behaviour exactly as
  before (futures filled, feed months verbatim, cash filled,
  Note `""`); (d) no-tag page with no rows → empty DataFrame, no
  crash. **Live verification (2 GETs): Heartland 0 rows,
  Mulvane 0 rows.** Both pages' `writeBidRow` rows are no longer
  matched in the static HTML at all — the design doc's §3
  assumption (rows still in the HTML) does **not** hold live as
  of this probe. So (a) is implemented and proven by mocked
  tests but recovers neither site today. No live price/basis/bid
  values recorded.
- **Option (b) probe — Heartland: fails (2 GETs). Correction
  to Cycles 21–23:** Heartland's jsquote tag is **not missing**
  — it is present but with an **empty symbols list**
  (`symbols=&fields=name,month,last...`). The collector's regex
  requires `[A-Z0-9,]+` after `symbols=`, so it does not match
  and the collector reports "tag not found". The design doc §1
  wording ("stopped carrying the jsquote.php script tag") is
  inaccurate for the current page and is corrected in design-doc
  §9. (Mulvane's tag state was not re-checked this cycle.) The
  derived feed URL (exact design-doc pattern) returned HTTP 200,
  20 bytes, body exactly `var quotes = null;` — the endpoint is
  alive and the URL shape is confirmed correct, but with an
  empty symbol list there is nothing to query: 0 symbols,
  nothing usable. **(b) fails because there is nothing to
  query**, not because of a 404 or wrong shape. **Deeper
  finding:** Heartland's default "All Locations" view carries
  **zero `writeBidRow` data rows** in the static HTML (the single
  occurrence is the function definition; no `<h4>` headings, no
  quoteboard tables). The bid area is empty. The page does have
  a Location filter (107 options: "All Locations" + 106 named
  delivery points) and a commodity filter, plus "Export to
  Spreadsheet" / print links. No bid-data AJAX/fetch was found
  in the static HTML. **Open hypothesis (untested, needs 1
  GET):** rows may appear only when a `location_filter` value is
  selected. Follow-up probe (1 GET, later cycle):
  `cash.php?location_filter=<one id>`. Mulvane was not probed
  for (b) (gated on Heartland's feed answering — it did not).
- **Staleness daytime re-check — none refreshed (4 GETs):**
  daytime re-check (Thu, Nov 19) of the four one-day-stale
  Bushel widgets: **none refreshed to Nov 19**. All four still
  carry the header "Cash bids for Wednesday, November 18,
  2026"; zero Nov 19 date strings anywhere in any page. The
  widgets do not refresh later in the day, at least not by the
  morning check. Smithfield Chadbourn 2294 (1 Soybeans row, 4th
  consecutive stale probe — Cycles 13, 14, 22, 24); Smithfield
  Hamer, SC 2179 (1 Soybeans row, 3rd — Cycles 16, 22, 24);
  Skyland Hugoton, KS 3370 (6 rows Corn/Milo/Red Wheat, 3rd —
  Cycles 14, 22, 24); Skyland Vilas-Walsh 3621 (5 rows
  Corn/Milo/Red Wheat, 3rd — Cycles 14, 22, 24). All still
  exactly one day stale — no worse. The refresh-later-in-the-day
  hypothesis is now answered (no), so no further daytime
  re-checks are needed. Standing note stands: a same-day
  freshness gate would fail these four daily, so they need an
  exemption/lag tolerance if such a gate is ever added.
- **Price-source catalogue edited** (33 insertions): the
  fallback (a) implementation, the (b) probe failure and tag
  correction, and the daytime staleness re-check.
- **Merge plan extended to Cycle 23** (230 lines added, 0
  removed — verified from the `cycle-23..cycle-24` diff). The
  Cycle 22 section's "63 commits" figure re-verified correct in
  Cycle 24.
- **Super-plan §9 extended to Cycle 23** (22 insertions, 6
  deletions — heading/intro now cover Cycles 1–23, test chain
  179 → 697; Cycle 23 bullet added; blockers updated —
  Heritage confirmed, Heartland/Mulvane toggles off, fallback
  design note, UA decision).
- **Boundary applied:** zero references to the excluded
  elevator in any new Cycle 24 code, tests, fixtures, or docs
  (verified by grep on the added lines of the commit). No
  contact made.
  Full detail: `docs/plans/overnight-cycle-24-report.md`.

### 3j. Gates — updated expectations for Cycle 24

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 24: 702 — **0 failed**.
   (Cycle 23 ended at 697; Cycle 24 adds 5 tests, all in
   `tests/test_us_agricharts_source.py`.)
2. **Web build** — re-run once at the Cycle 24 step so the final
   tree is verified as a whole. No web files changed in Cycle 24,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Verified from git: no migration
   file was added in Cycle 24 (`git log` on the Alembic versions
   dir in `cycle-23..cycle-24` is empty, and the file list at
   the Cycle 24 tip is `0001`–`0019`, 19 files).
4. **Boundary spot-check** — grep the Cycle 24 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs.
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 24 diff (none are reported).

### 4j. Known conflicts and overlaps — Cycle 24

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 24's additions are
  the fallback (a) implementation, the (b) probe failure and tag
  correction, and the daytime staleness re-check; no earlier
  text was rewritten), the merge plan (pure append of the
  Cycle 23 section, 230 lines added, 0 removed), the super-plan
  §9 (Cycle 23 bullet + blockers update; no earlier bullet was
  rewritten). The design doc
  (`docs/plans/agricharts-futures-fallback-design.md`, created
  in Cycle 23) was corrected in §9 this cycle (61 insertions, 0
  deletions: the §1 wording corrected — the tag is present with
  an empty symbols list, not missing — and the coordinator's
  approval of option (a) recorded, including both
  sub-decisions).
- **`config.toml`** (`app/platform/market_data/sources/
  config.toml`) — **not touched in Cycle 24** (`git log` on it
  in `cycle-23..cycle-24` is empty; last touched in Cycle 23
  with the two toggle flips). No toggle value changed this
  cycle; Heartland/Mulvane stay `false`, all other AgriCharts
  toggles stay `true`.
- **`us_agricharts_source.py`** — touched in **Cycle 24** (107
  insertions, 26 deletions: the fallback (a) basis-only path
  and `futures_month_from_symbol()`). Last touched before that
  in Cycle 22 (the escaped-quote regex fix and the
  `_is_commodity_heading` fallback), so no other cycle in the
  chain edits the same lines in this range; the Cycle 24 change
  applies cleanly on top of the Cycle 22 version. Its test file
  (`tests/test_us_agricharts_source.py`, 142 insertions, 1
  deletion, 5 new tests) is likewise Cycle 24-only in this
  range.
- **No registry changes in Cycle 24** — `app/services/
  source_registry.py` was not touched this cycle; no adapter,
  toggle, or registration change to carry. Neither
  `us_dtn_source.py` nor `app/main.py` was touched.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 24.

### 5j. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 25): `?? .github/` in `git status` on the
  Cycle 25 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 24 as well as 1–23 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 24.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 24
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 24 (not
  blockers):** AgriCharts fallback (a) is **DONE** in Cycle 24
  (basis-only rows may flow with explicit `None`, no quarantine;
  Futures Month decoded from the symbol — coordinator approval
  recorded in design-doc §9). Heartland/Mulvane toggles stay
  `false` until a site is probe-confirmed returning rows;
  **Heartland filtered-view probe open** (`cash.php?
  location_filter=<one id>`, 1 GET, later cycle — rows may
  appear only under a selected location; Mulvane's page
  structure not yet inspected). **Feed-down degradation — NOT
  implemented in Cycle 24** (the task kept tag-present behaviour
  exactly unchanged; commit `2120e29` retains the early `return
  pd.DataFrame()` when the tag is present but the feed returns
  no data — confirmed from the committed code, not just the
  report). It is a one-line follow-up: treat empty quotes like
  the no-tag path. **Working-tree note (Cycle 25, uncommitted):**
  at the time this section was written, the Cycle 25 checkout
  carries an uncommitted change to `us_agricharts_source.py`
  (plus its test file) implementing exactly that follow-up —
  an empty feed now degrades like the no-tag path instead of
  returning an empty DataFrame. That is another worker's
  in-progress Cycle 25 work, not committed and not part of
  Cycle 24; verify against the Cycle 25 report whether it
  landed — do not assume it from this note. **Staleness watch:**
  the four widgets stay on the exemption list for any future
  freshness gate; no further daytime re-checks are needed (the
  refresh-later-in-the-day hypothesis is answered — no).
  Playwright render checks still pending (DTN family — Al-Corn
  + Sunrise first — FMN filtered view, Mapleview, StoneX
  including Frontier, The Andersons — closed for static
  collection, browser-only — and Landus, Vercel checkpoint);
  DTN toggles stay `false` until verified; scheduling the
  poller as a second cron job (deployment decision, checklist
  §4 step 6); Mae-Mart `cash_price` from futures + static basis
  (still open, gated on the licensed-feed decision); at least
  one `Commodity` row must exist before the first poller run;
  agricharts User-Agent decision resolved in Cycle 23 (Chrome
  UA kept).

### 7j. After the merges — updated

§7 applies with the Cycle 24 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 702 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 24 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 24 except for the additions in §5j above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Heartland filtered-view probe (plus Mulvane structure
inspection); feed-down degradation follow-up (see the §5j
working-tree note — it may already be in Cycle 25, verify
there); Chadbourn + Hamer + Skyland 3370/3621 staleness watch
(exemption list); Mae-Mart cash-price decision; poller
scheduling decision; currency decision.

---

## Cycle 25 (added Cycle 26)

### 0k. Branch chain — Cycle 25, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-25` gives **69 commits** (67
through Cycle 24 + 2 in Cycle 25), **0 merge commits**, no
branch points. Cycle 25's first commit `c4b221b` has parent
`f90cb8b` (the Cycle 24 tip), and merge-base(24, 25) is the
Cycle 24 tip `f90cb8b`. Per-branch commit count for Cycle 25: 2
(`c4b221b`, `95b310d`).

That means the §2 procedure continues unchanged: merge Cycle 25
after 24, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-25` tip (`95b310d`) would give the same tree as
twenty-five sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 24 section's "67 commits master..cycle-24" figure
was re-verified in Cycle 26 and is correct — 67, 0 merge
commits. `master` is still at `f2c3206` — no cycle work is on
`master` yet.)

### 1k. What the branch contains (Cycle 25)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 25 | `95b310d` | 704 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `95b310d308e4b6e55772cdaddbe9aaf4da4a4a53`.
No web files changed in Cycle 25, so there is no fresh
web-build evidence in this range. 7 files changed in Cycle 25
(574 insertions, 8 deletions): the feed-down degradation and
its tests, the design-doc §9 scope note, the price-source
catalogue, the merge plan, the super-plan §9, and the Cycle 25
report itself.

- **Cycle 25** (`overnight/grainhub-cycle-25`; commits `c4b221b`,
  `95b310d`): Heartland filtered-view probe — **hypothesis
  closed**. `cash.php?location_filter=22143` (ADM – DSM, first
  named option in the page's 106-location filter): HTTP 200,
  36,246 bytes. The server honoured the filter (option marked
  selected), but the page still carries **0 `writeBidRow` data
  rows** and the jsquote tag still has empty symbols. The Cycle
  24 open hypothesis — rows appear only under a selected
  location — does **not** hold for the tested location. There
  is no usable filtered-URL pattern for the collector; the feed
  question is moot. Caveat: only one location id was tested,
  but default + one filtered view both returning zero rows with
  empty symbols makes a per-location difference unlikely. No
  live price, basis, or bid recorded.
- **Mulvane default view re-checked (1 GET):**
  `https://www.mulvanecoop.com/markets/cash.php`: HTTP 200,
  33,214 bytes, **0 `writeBidRow` rows**. **Correction:**
  Mulvane's jsquote tag is **present with empty symbols**, not
  missing — the Cycle 21–23 "tag missing" phrasing is corrected
  for Mulvane too. The page has a Location filter (4 named:
  Clearwater 3866, Clearwater-253 80891, Mulvane 3864,
  Mulvane-251 80889) and a Commodity filter (Wheat HRW 2461,
  Corn 2462, Milo 2463, Soybeans 2464). **Both sites stay dark;
  toggles stay off.** Option (a) still recovers neither site
  live because the rows are not in the static HTML at all.
  **Heartland / Mulvane are closed for now** — default view,
  one filtered view, and the feed derivation all return
  nothing. No further probes without a new hypothesis (e.g. a
  JS-rendered route, or a different AgriCharts host).
- **Feed-down degradation — implemented (mocked tests only, 0
  GETs).** Tag present + jsquote feed returns empty (`var
  quotes = null;` or `{}`) now degrades like the no-tag path
  instead of returning an empty DataFrame: rows return
  basis-only (futures/cash `None` with note, month decoded from
  symbol). No new code path was needed for the rows themselves
  — the Cycle 24 degraded branch already handles `degraded=True`
  regardless of cause. **2 new parametrized tests** (both
  empty-feed shapes) plus a called-URL assertion on the existing
  with-data regression guard (proving both page and feed are
  fetched on the with-data path). Tag-absent and
  tag-present-with-data paths unchanged; Chrome UA, toggles,
  registry untouched. The coordinator independently verified
  the suite (704 passed; targeted file 18 passed). **This
  resolves the §5j working-tree note:** the feed-down work the
  Cycle 24 section saw uncommitted in the Cycle 25 checkout
  has now landed in this cycle's commit `c4b221b` (verified
  from the committed diff, not just the report). **Scope note:**
  only the *empty-quotes* case degrades. If the feed fetch
  itself raises (HTTP error/timeout), the outer `except` still
  returns an empty DataFrame — a further one-line follow-up if
  wanted (see §5k).
- **Price-source catalogue edited** (19 insertions): the
  Heartland filtered-view result, the Mulvane re-check and tag
  correction, and the feed-down degradation.
- **Merge plan extended to Cycle 24** (285 lines added, 0
  removed — verified from the `cycle-24..cycle-25` diff). The
  Cycle 23 section's "65 commits" figure re-verified correct in
  Cycle 25.
- **Super-plan §9 extended to Cycle 24** (heading/intro now
  cover Cycles 1–24, test chain 179 → 702; Cycle 24 bullet
  added; blockers updated — fallback (a) done, (b) fails,
  staleness daytime re-check answered).
- **Boundary applied:** zero references in any new Cycle 25
  code, tests, fixtures, or docs (verified by grep on the added
  lines of the commit). No contact made.
  Full detail: `docs/plans/overnight-cycle-25-report.md`.

### 3k. Gates — updated expectations for Cycle 25

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 25: 704 — **0 failed**.
   (Cycle 24 ended at 702; Cycle 25 adds 2 parametrized
   feed-down tests.)
2. **Web build** — re-run once at the Cycle 25 step so the final
   tree is verified as a whole. No web files changed in Cycle 25,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Verified from git: no migration
   file was added in Cycle 25 (`git log` on the Alembic versions
   dir in `cycle-24..cycle-25` is empty, and the file list at
   the Cycle 25 tip is `0001`–`0019`, 19 files).
4. **Boundary spot-check** — grep the Cycle 25 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs.
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 25 diff (none are reported).

### 4k. Known conflicts and overlaps — Cycle 25

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 25's additions are
  the Heartland filtered-view result, the Mulvane re-check and
  tag correction, and the feed-down degradation; no earlier
  text was rewritten), the merge plan (pure append of the
  Cycle 24 section, 285 lines added, 0 removed), the super-plan
  §9 (Cycle 24 bullet + blockers update; no earlier bullet was
  rewritten). The design doc
  (`docs/plans/agricharts-futures-fallback-design.md`, created
  in Cycle 23, corrected in §9 in Cycle 24) was updated in §9
  this cycle (23 insertions: the scope note — tag present but
  feed returns no data degrades like the no-tag path).
- **`config.toml`** (`app/platform/market_data/sources/
  config.toml`) — **not touched in Cycle 25** (`git log` on it
  in `cycle-24..cycle-25` is empty; last touched in Cycle 23
  with the two toggle flips). No toggle value changed this
  cycle; Heartland/Mulvane stay `false`, all other AgriCharts
  toggles stay `true`.
- **`us_agricharts_source.py`** — touched in **Cycle 25** (16
  lines changed: the empty-feed degradation — the tag-present
  branch now sets `degraded = True` instead of returning an
  empty DataFrame, with the warning reworded). Last touched
  before that in Cycle 24 (the fallback (a) basis-only path),
  so no other cycle in the chain edits the same lines in this
  range; the Cycle 25 change applies cleanly on top of the
  Cycle 24 version. Its test file
  (`tests/test_us_agricharts_source.py`, 77 insertions, 2 new
  parametrized tests + the called-URL assertion) is likewise
  Cycle 25-only in this range.
- **No registry changes in Cycle 25** — `app/services/
  source_registry.py` was not touched this cycle; no adapter,
  toggle, or registration change to carry. Neither
  `us_dtn_source.py` nor `app/main.py` was touched.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 25.

### 5k. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 26): `?? .github/` in `git status` on the
  Cycle 26 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 25 as well as 1–24 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 25.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 25
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 25 (not
  blockers):** feed-down degradation (empty-quotes case) is
  **DONE** in Cycle 25 — implemented, tested, and landed in
  commit `c4b221b`; this closes the §5j working-tree note.
  **Feed-error degradation is still open** as a one-line
  follow-up: if the feed fetch itself raises (HTTP
  error/timeout), the outer `except` in
  `us_agricharts_source.py` still returns an empty DataFrame
  (verified from the committed Cycle 25 code, lines 394–396) —
  it does not yet degrade like the empty-quotes path.
  **Heartland / Mulvane are closed for now** (default view, one
  filtered view, and the feed derivation all return nothing;
  toggles stay `false`; no further probes without a new
  hypothesis). **Staleness watch:** the four widgets stay on
  the exemption list for any future freshness gate; no further
  re-checks are needed. Playwright render checks still pending
  (DTN family — Al-Corn + Sunrise first — FMN filtered view,
  Mapleview, StoneX including Frontier, The Andersons — closed
  for static collection, browser-only — and Landus, Vercel
  checkpoint); DTN toggles stay `false` until verified;
  scheduling the poller as a second cron job (deployment
  decision, checklist §4 step 6); Mae-Mart `cash_price` from
  futures + static basis (still open, gated on the
  licensed-feed decision); at least one `Commodity` row must
  exist before the first poller run; agricharts User-Agent
  decision resolved in Cycle 23 (Chrome UA kept).

### 7k. After the merges — updated

§7 applies with the Cycle 25 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 704 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 25 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 25 except for the additions in §5k above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
feed-error degradation one-line follow-up; Chadbourn + Hamer +
Skyland 3370/3621 staleness watch (exemption list); Mae-Mart
cash-price decision; poller scheduling decision; currency
decision.

---

## Cycle 26 (added Cycle 27)

### 0l. Branch chain — Cycle 26, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-26` gives **71 commits** (69
through Cycle 25 + 2 in Cycle 26), **0 merge commits**, no
branch points. Cycle 26's first commit `797f8af` has parent
`95b310d` (the Cycle 25 tip), and merge-base(25, 26) is the
Cycle 25 tip `95b310d`. Per-branch commit count for Cycle 26: 2
(`797f8af`, `ca481a9`).

That means the §2 procedure continues unchanged: merge Cycle 26
after 25, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-26` tip (`ca481a9`) would give the same tree as
twenty-six sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 25 section's "69 commits master..cycle-25" figure
was re-verified in Cycle 27 and is correct — 69, 0 merge
commits. `master` is still at `f2c3206` — no cycle work is on
`master` yet.)

### 1l. What the branch contains (Cycle 26)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 26 | `ca481a9` | 709 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `ca481a993cad416f1eeb29605b47a8d3f17c7fc0`.
No web files changed in Cycle 26, so there is no fresh
web-build evidence in this range. 7 files changed in Cycle 26
(526 insertions, 8 deletions): the feed-error degradation and
its tests, the design-doc closing note, the price-source
catalogue, the merge plan, the super-plan §9, and the Cycle 26
report itself.

- **Cycle 26** (`overnight/grainhub-cycle-26`; commits `797f8af`,
  `ca481a9`): feed-error degradation — **implemented (mocked
  tests only, 0 GETs)**. Only the `_fetch_jsquote` call is now
  wrapped in its own `try/except`: a feed fetch that RAISES
  (HTTP error/timeout) degrades to basis-only rows, like the
  no-tag (Cycle 24) and empty-feed (Cycle 25) paths. A page
  fetch that raises still returns empty via the outer `except`
  (no HTML to parse, no invented rows). The empty-feed check
  gained a `not degraded` guard so a raised feed doesn't
  double-log. **5 new mocked tests**: 3 feed-raises (HTTPError
  503, ConnectTimeout, ReadTimeout) → basis-only rows; 2
  page-raises (HTTPError 500, ConnectTimeout) → empty
  DataFrame, no exception escapes. Targeted file 23 passed;
  **full suite 709 passed**. This closes the last open
  follow-up from the Cycle 23 design note — all three
  degradation paths (no tag, empty feed, feed error) now
  behave the same way. **This resolves the §5k open item:**
  the feed-error degradation follow-up the Cycle 25 section
  recorded as still open has now landed in this cycle's
  commit `797f8af` (verified from the committed diff, not
  just the report).
- **Live re-verification sweep — all five exact matches (5
  probes).** All five key collectors re-verified live via
  their wrappers; **all returned `status='ok'` with row counts
  identical to the last verification — no drift, no failures.**
  Counts only, no values recorded.

  | Collector | Rows now | Last verified | Verdict |
  |---|---|---|---|
  | FMN (`fetch_fmn_cash`) | 453 rows (87 points, 204 tables; 449/449 futures-linked filled) | Cycle 10–11: 453 | Exact match |
  | Five Star Coop (`fetch_five_star_coop`) | 299 rows, 21 locations | Cycle 8–9: 299 | Exact match |
  | TGM embed (`fetch_tgm`) | 362 rows, 24 locations | Cycle 9: 362 | Exact match |
  | USDA mirror, James Valley (`fetch_usda_mirror`) | 197 rows, 29 regions, report id 7730, dated Nov 18 | Cycle 4: 197 | Exact match |
  | FAC, Bushel (`fetch_fac`) | 45 rows, 3 locations; header dated Nov 19 | Cycle 4–5: 45 | Exact match |

  Notes: FMN's dropdown still lists more points than the 204
  tables (known limitation, unchanged); Five Star's page trade
  date is Nov 18; FAC's widget header is fresh (Nov 19). The
  five collectors' live behaviour is stable across cycles —
  the catalogue's verified counts stand.
- **Price-source catalogue edited** (20 insertions): the
  feed-error degradation and the live re-verification sweep
  results.
- **Merge plan extended to Cycle 25** (229 lines added, 0
  removed — verified from the `cycle-25..cycle-26` diff). The
  Cycle 24 section's "67 commits" figure re-verified correct in
  Cycle 26.
- **Super-plan §9 extended to Cycle 25** (15 insertions, 6
  deletions — heading/intro now cover Cycles 1–25, test chain
  179 → 704; Cycle 25 bullet added; blockers updated —
  Heartland/Mulvane closed for now, feed-down degradation
  done).
- **Boundary applied:** zero references in any new Cycle 26
  code, tests, fixtures, or docs (verified by grep on the added
  lines of the commit). No contact made.
  Full detail: `docs/plans/overnight-cycle-26-report.md`.

### 3l. Gates — updated expectations for Cycle 26

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 26: 709 — **0 failed**.
   (Cycle 25 ended at 704; Cycle 26 adds 5 feed-error
   degradation tests.)
2. **Web build** — re-run once at the Cycle 26 step so the final
   tree is verified as a whole. No web files changed in Cycle 26,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Verified from git: no migration
   file was added in Cycle 26 (`git log` on the Alembic versions
   dir in `cycle-25..cycle-26` is empty, and the file list at
   the Cycle 26 tip is `0001`–`0019`, 19 files).
4. **Boundary spot-check** — grep the Cycle 26 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs.
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 26 diff (none are reported).

### 4l. Known conflicts and overlaps — Cycle 26

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 26's additions are
  the feed-error degradation and the live re-verification
  sweep; no earlier text was rewritten), the merge plan (pure
  append of the Cycle 25 section, 229 lines added, 0 removed),
  the super-plan §9 (Cycle 25 bullet + blockers update; no
  earlier bullet was rewritten). The design doc
  (`docs/plans/agricharts-futures-fallback-design.md`, created
  in Cycle 23, corrected in §9 in Cycle 24, scope note in
  Cycle 25) was updated this cycle (14 insertions: the Cycle 26
  closing note — the design note's work is complete; all three
  degradation paths behave the same way; the only remaining
  AgriCharts open item is Heartland/Mulvane, closed for now).
- **`config.toml`** (`app/platform/market_data/sources/
  config.toml`) — **not touched in Cycle 26** (`git log` on it
  in `cycle-25..cycle-26` is empty; last touched in Cycle 23
  with the two toggle flips). No toggle value changed this
  cycle; Heartland/Mulvane stay `false`, all other AgriCharts
  toggles stay `true`.
- **`us_agricharts_source.py`** — touched in **Cycle 26** (23
  insertions, 2 deletions: the `_fetch_jsquote`-only
  `try/except` and the `not degraded` guard). Last touched
  before that in Cycle 25 (the empty-feed degradation), so no
  other cycle in the chain edits the same lines in this range;
  the Cycle 26 change applies cleanly on top of the Cycle 25
  version. Its test file
  (`tests/test_us_agricharts_source.py`, 100 insertions, 0
  deletions, 5 new tests) is likewise Cycle 26-only in this
  range.
- **No registry changes in Cycle 26** — `app/services/
  source_registry.py` was not touched this cycle (it is not
  among the 7 files changed in `cycle-25..cycle-26`); no
  adapter, toggle, or registration change to carry. Neither
  `us_dtn_source.py` nor `app/main.py` was touched.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 26.

### 5l. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 27): `?? .github/` in `git status` on the
  Cycle 27 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 26 as well as 1–25 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 26.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 26
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 26 (not
  blockers):** the AgriCharts futures-fallback design note's
  work is **COMPLETE** in Cycle 26 — feed-error degradation is
  done, closing the last open follow-up; no further degradation
  work is open. **Heartland / Mulvane are closed for now**
  (default view, one filtered view, and the feed derivation all
  return nothing; toggles stay `false`; no further probes
  without a new hypothesis). **Staleness watch:** the four
  widgets (Smithfield Chadbourn + Hamer, Skyland 3370/3621)
  stay on the exemption list for any future freshness gate; no
  further re-checks are needed. Playwright render checks still
  pending (DTN family — Al-Corn + Sunrise first — FMN filtered
  view, Mapleview, StoneX including Frontier, The Andersons —
  closed for static collection, browser-only — and Landus,
  Vercel checkpoint); DTN toggles stay `false` until verified;
  scheduling the poller as a second cron job (deployment
  decision, checklist §4 step 6); Mae-Mart `cash_price` from
  futures + static basis (still open, gated on the
  licensed-feed decision); at least one `Commodity` row must
  exist before the first poller run; agricharts User-Agent
  decision resolved in Cycle 23 (Chrome UA kept). Still needs
  Adam (carried from Cycles 1–25, nothing new in Cycle 26):
  NASS key, FAS/data.gov key, LLM provider + key, Barchart/DTN
  licensed feed decision (redistribution licence — now also
  gates the CGB `cashbids-js.php` question and the Mae-Mart
  cash-price decision), ERP choice (Agvance recommended),
  eSign provider, pricing/hosting decisions, `gh` `workflow`
  scope, currency column decision (four concrete choices in
  `docs/plans/currency-design.md`), email-bid endpoint auth
  decision (public vs admin-only).

### 7l. After the merges — updated

§7 applies with the Cycle 26 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 709 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 26 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 26 except for the additions in §5l above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Chadbourn + Hamer + Skyland 3370/3621 staleness watch
(exemption list); Mae-Mart cash-price decision; poller
scheduling decision; currency decision.

---

## Cycle 27 (added Cycle 28)

### 0m. Branch chain — Cycle 27, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-27` gives **73 commits** (71
through Cycle 26 + 2 in Cycle 27), **0 merge commits**, no
branch points. Cycle 27's first commit `90b2bb7` has parent
`ca481a9` (the Cycle 26 tip), and merge-base(26, 27) is the
Cycle 26 tip `ca481a9`. Per-branch commit count for Cycle 27: 2
(`90b2bb7`, `ba4df98`).

That means the §2 procedure continues unchanged: merge Cycle 27
after 26, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-27` tip (`ba4df98`) would give the same tree as
twenty-seven sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 26 section's "71 commits master..cycle-26" figure
was re-verified in Cycle 28 and is correct — 71, 0 merge
commits. `master` is still at `f2c3206` — no cycle work is on
`master` yet.)

### 1m. What the branch contains (Cycle 27)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 27 | `ba4df98` | 709 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `ba4df98bf41d6a2e707f05b205bc753314d72df0`.
No web files changed in Cycle 27, so there is no fresh
web-build evidence in this range. 4 files changed in Cycle 27
(371 insertions, 6 deletions): the price-source catalogue, the
merge plan, the super-plan §9, and the Cycle 27 report itself.
**No code changed at all in Cycle 27** — docs/research only —
so the test count is unchanged from Cycle 26 and no new tests
were added.

- **Cycle 27** (`overnight/grainhub-cycle-27`; commits `90b2bb7`,
  `ba4df98`): AgriCharts wrappers re-verification — **all 10
  exact matches (10 calls, 1 per wrapper, no retries, via the
  venv python)**. All 10 returned `[US-AG OK]` with no
  warnings — no degraded/basis-only path, no jsquote failures —
  and row counts exactly matching Cycle 21. **639 rows total, 0
  zero-row results.** Counts only, no values recorded.
  Structure identical across all 10: 11 columns (Location,
  Name, Delivery, Delivery End, Futures Month, Futures Price,
  Change, Basis, Bushel Cash Price, MT Cash Price, Note).

  | Wrapper | Rows now | Cycle 21 | Locations |
  |---|---|---|---|
  | Ag Plus | 36 | 36 | 6 |
  | Farmers Win Coop | 171 | 171 | 18 |
  | Keller | 14 | 14 | 1 |
  | Kokomo Grain | 63 | 63 | 8 |
  | Legacy Farmers | 66 | 66 | 10 |
  | Pro Ag | 78 | 78 | 6 |
  | West-Con | 84 | 84 | 1 |
  | Wheaton Dumont | 43 | 43 | 8 |
  | Central Farmers Coop | 75 | 75 | 11 |
  | Anthony Farmers Co-op | 9 | 9 | 3 |

  Heritage was confirmed live in Cycle 23 (14 rows) and
  Heartland / Mulvane are closed for now — neither was
  re-probed. Together with Cycle 26's sweep (FMN 453, Five
  Star 299, TGM 362, USDA mirror 197, FAC 45), **every
  live-verified collector has now been re-checked this morning
  with zero drift** — the catalogue's verified counts stand.
- **Price-source catalogue edited** (19 insertions): the
  10-wrapper re-verification results.
- **Merge plan extended to Cycle 26** (223 lines added, 0
  removed — verified from the `cycle-26..cycle-27` diff). The
  Cycle 25 section's "69 commits" figure re-verified correct in
  Cycle 27.
- **Super-plan §9 extended to Cycle 26** (heading/intro now
  cover Cycles 1–26, test chain 179 → 709; Cycle 26 bullet
  added; blockers updated — feed-error degradation done,
  design-note work complete, five-collector sweep exact
  matches).
- **Boundary applied:** zero references in any new Cycle 27
  code, tests, fixtures, or docs — the single match in the
  range diff is the report's own boundary-attestation heading.
  No contact made.
  Full detail: `docs/plans/overnight-cycle-27-report.md`.

### 3m. Gates — updated expectations for Cycle 27

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 27: 709 — **0 failed**.
   (Unchanged from Cycle 26 — no code changed in this cycle, so
   no new tests. The coordinator re-ran the suite to confirm.)
2. **Web build** — re-run once at the Cycle 27 step so the final
   tree is verified as a whole. No web files changed in Cycle 27,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Verified from git: no migration
   file was added in Cycle 27 (`git log` on the Alembic versions
   dir in `cycle-26..cycle-27` is empty, and the file list at
   the Cycle 27 tip is `0001`–`0019`, 19 files).
4. **Boundary spot-check** — grep the Cycle 27 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs (the report's own
   boundary-attestation heading is the only match).
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 27 diff (none are reported).

### 4m. Known conflicts and overlaps — Cycle 27

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 27's additions are
  the 10-wrapper re-verification results; no earlier text was
  rewritten), the merge plan (pure append of the Cycle 26
  section, 223 lines added, 0 removed), the super-plan §9
  (Cycle 26 bullet + blockers update; no earlier bullet was
  rewritten).
- **`config.toml`** (`app/platform/market_data/sources/
  config.toml`) — **not touched in Cycle 27** (`git log` on it
  in `cycle-26..cycle-27` is empty; last touched in Cycle 23
  with the two toggle flips). No toggle value changed this
  cycle; Heartland/Mulvane stay `false`, all other AgriCharts
  toggles stay `true`.
- **No collector, registry, or code file touched in Cycle 27**
  — docs/research only (4 files changed, all under
  `docs/plans/`). `us_agricharts_source.py`,
  `app/services/source_registry.py`, `us_dtn_source.py`, and
  `app/main.py` were not touched this cycle.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 27.

### 5m. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 28): `?? .github/` in `git status` on the
  Cycle 28 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 27 as well as 1–26 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 27.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 27
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 27 (not
  blockers):** **nothing new needs Adam in Cycle 27.** Every
  live-verified collector has now been re-checked this morning
  with zero drift (Cycle 27's 10 AgriCharts wrappers, 639 rows,
  plus Cycle 26's five-collector sweep) — the catalogue's
  verified counts stand. Playwright render checks still pending
  (DTN family — Al-Corn + Sunrise first — FMN filtered view,
  Mapleview, StoneX including Frontier, The Andersons — closed
  for static collection, browser-only — and Landus, Vercel
  checkpoint); DTN toggles stay `false` until verified;
  scheduling the poller as a second cron job (deployment
  decision, checklist §4 step 6); Mae-Mart `cash_price` from
  futures + static basis (still open, gated on the
  licensed-feed decision); at least one `Commodity` row must
  exist before the first poller run; agricharts User-Agent
  decision resolved in Cycle 23 (Chrome UA kept). Still needs
  Adam (carried from Cycles 1–26, nothing new in Cycle 27):
  NASS key, FAS/data.gov key, LLM provider + key, Barchart/DTN
  licensed feed decision (redistribution licence — now also
  gates the CGB `cashbids-js.php` question and the Mae-Mart
  cash-price decision), ERP choice (Agvance recommended),
  eSign provider, pricing/hosting decisions, `gh` `workflow`
  scope, currency column decision (four concrete choices in
  `docs/plans/currency-design.md`), email-bid endpoint auth
  decision (public vs admin-only).

### 7m. After the merges — updated

§7 applies with the Cycle 27 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 709 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 27 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 27 except for the additions in §5m above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Chadbourn + Hamer + Skyland 3370/3621 staleness watch
(exemption list); Mae-Mart cash-price decision; poller
scheduling decision; currency decision.

---

## Cycle 28 (added Cycle 29)

### 0n. Branch chain — Cycle 28, verified from git

The chain is **still linear**: `git log --oneline
master..overnight/grainhub-cycle-28` gives **75 commits** (73
through Cycle 27 + 2 in Cycle 28), **0 merge commits**, no
branch points. Cycle 28's first commit `823bf2d` has parent
`ba4df98` (the Cycle 27 tip), and merge-base(27, 28) is the
Cycle 27 tip `ba4df98`. Per-branch commit count for Cycle 28: 2
(`823bf2d`, `7e99076`).

That means the §2 procedure continues unchanged: merge Cycle 28
after 27, one branch at a time with `--no-ff`, running the §3
gates at each step. A single fast-forward of `master` to the
`cycle-28` tip (`7e99076`) would give the same tree as
twenty-eight sequential merges; prefer the sequential merges for
the same reason as §0 (a review checkpoint and stop point per
cycle).

(The Cycle 27 section's "73 commits master..cycle-27" figure
was re-verified in Cycle 29 and is correct — 73, 0 merge
commits. `master` is still at `f2c3206` — no cycle work is on
`master` yet.)

### 1n. What the branch contains (Cycle 28)

| Branch | Tip | Tests at tip | Web build at tip |
|---|---|---|---|
| Cycle 28 | `7e99076` | 709 passed, 0 failed | Not re-run (no web files changed; last full pass Cycle 17) |

Tip commit hash (full): `7e99076d033e0d36453981ca6f57c65e7a3e65ee`.
No web files changed in Cycle 28, so there is no fresh
web-build evidence in this range. 4 files changed in Cycle 28
(359 insertions, 6 deletions): the price-source catalogue (24
insertions), the merge plan (194 insertions), the super-plan §9
(14 insertions, 6 deletions), and the Cycle 28 report itself
(127 insertions). **No code changed at all in Cycle 28** —
docs/research only — so the test count is unchanged from
Cycle 27 and no new tests were added.

- **Cycle 28** (`overnight/grainhub-cycle-28`; commits `823bf2d`,
  `7e99076`): embed family re-verification — **all 13 exact
  matches (13 calls, 1 per site, no retries)**. All 13 returned
  `status='ok'` with row counts exactly matching their earlier
  verifications — no drift, no failures. **816 rows across the
  13 embed sites** (TGM re-verified in Cycle 26; the other 12
  this cycle). Counts only, no values recorded.

  | Site | Rows now | Prior | Locations |
  |---|---|---|---|
  | Agtegra | 8 | 8 (Cycle 7) | 1 (Hecla) |
  | Heritage Cooperative (embed) | 15 | 15 (Cycle 7) | 1 (Ada) |
  | Linn Coop | 51 | 51 (Cycle 7) | 5 |
  | Midway Coop | 8 | 8 (Cycle 7) | 1 ("All Locations") |
  | Ag State | 11 | 11 (Cycle 7) | 1 |
  | Superior Ag | 12 | 12 (Cycle 7) | 1 |
  | ALCIVIA | 181 | 181 (Cycle 9) | 15 |
  | TGM | 362 | 362 (Cycle 9) | 24 |
  | PRO Coop 21297 (Ayrshire) | 6 | 6 (Cycle 11) | 1 |
  | PRO Coop 21302 (Manson) | 12 | 12 (Cycle 12) | 1 |
  | PRO Coop 21302b (Manson dup) | 12 | 12 (Cycle 13) | 1 |
  | Hull Coop | 12 | 12 (Cycle 12) | 1 |
  | StateLine Coop | 126 | 126 (Cycle 12) | 11 |

  Structure unchanged everywhere: same location sets,
  commodity splits, and groupby behaviour (Ag State /
  Superior Ag still group by commodity with `location_name`
  authoritative; Midway still publishes the single "All
  Locations" label; StateLine still 12 rows per location except
  Emmetsburg-AGP, Soybeans-only with 6). The separate
  AgriCharts wrapper for the other Heritage-named source was
  not probed (already confirmed live in Cycle 23).
- **FS Grain USDA mirror confirmed (1 call):**
  `fetch_usda_mirror_fs_grain()`: **197 rows, report id 7730,
  dated Nov 18, 2026** — exact match to the James Valley
  re-verification in Cycle 26. Caveat: the region count was not
  re-tallied this run (rows grouped on `location`, which is
  "United States" for all rows); the 29-region figure stands
  from Cycle 26.
- **Merge plan extended to Cycle 27** (194 lines added, 0
  removed — verified from the `cycle-27..cycle-28` diff). The
  Cycle 26 section's "71 commits" figure re-verified correct in
  Cycle 28. No discrepancies found between git and the Cycle 27
  report.
- **Super-plan §9 extended to Cycle 27** (14 insertions, 6
  deletions — heading/intro now cover Cycles 1–27, test chain
  179 → 709; Cycle 27 bullet added; blockers updated — all 10
  wrappers re-verified, every live-verified collector re-checked
  with zero drift).
- **Boundary applied:** zero references in any new Cycle 28
  code, tests, fixtures, or docs — the single match in the
  range diff is the Cycle 27 report's own boundary-attestation
  heading, not a reference in content. No contact made.
  Full detail: `docs/plans/overnight-cycle-28-report.md`.

### 3n. Gates — updated expectations for Cycle 28

§3 applies unchanged, with these per-cycle numbers:

1. **Full API test suite** — expect Cycle 28: 709 — **0 failed**.
   (Unchanged from Cycle 27 — no code changed in this cycle, so
   no new tests. The coordinator re-ran the suite to confirm.)
2. **Web build** — re-run once at the Cycle 28 step so the final
   tree is verified as a whole. No web files changed in Cycle 28,
   so a re-run is a no-op confirmation; last full pass remains
   Cycle 17.
3. **Alembic heads** — expect exactly one head, `0019`
   (unchanged since Cycle 7). Verified from git: no migration
   file was added in Cycle 28 (`git log` on the Alembic versions
   dir in `cycle-27..cycle-28` is empty, and the file list at
   the Cycle 28 tip is `0001`–`0019`, 19 files).
4. **Boundary spot-check** — grep the Cycle 28 range diff for
   the excluded elevator name; expect zero new references in
   code, tests, fixtures, or docs (the report's own
   boundary-attestation heading is the only match).
5. **No-secrets spot-check** — no new credentials, keys, or
   tokens in the Cycle 28 diff (none are reported).

### 4n. Known conflicts and overlaps — Cycle 28

- **Files also touched by earlier cycles:** the price-source
  catalogue (edited in every cycle — Cycle 28's additions are
  the 13-site embed re-verification results and the FS Grain
  mirror confirmation; no earlier text was rewritten), the merge
  plan (pure append of the Cycle 27 section, 194 lines added, 0
  removed), the super-plan §9 (Cycle 27 bullet + blockers
  update; no earlier bullet was rewritten).
- **`config.toml`** (`app/platform/market_data/sources/
  config.toml`) — **not touched in Cycle 28** (`git log` on it
  in `cycle-27..cycle-28` is empty; last touched in Cycle 23
  with the two toggle flips). No toggle value changed this
  cycle; Heartland/Mulvane stay `false`, all other AgriCharts
  toggles stay `true`.
- **No collector, registry, or code file touched in Cycle 28**
  — docs/research only (4 files changed, all under
  `docs/plans/`). `us_agricharts_source.py`,
  `app/services/source_registry.py`, `us_dtn_source.py`, and
  `app/main.py` were not touched this cycle.
- **Migration chain** — unchanged: `0015 → … → 0018` (Cycle 1)
  then `0019` (Cycle 7), single head throughout Cycle 28.

### 5n. What must NOT be merged as-is — update

- **The CI workflow file is STILL not in any branch.** Verified
  2026-11-19 (Cycle 29): `?? .github/` in `git status` on the
  Cycle 29 checkout (`.github/workflows/api-tests.yml`).
  Merging Cycle 28 as well as 1–27 will **not** bring it into
  `master`. Same remedy as §5: Adam re-authenticates `gh` with
  `workflow` scope, or adds the file via the GitHub web UI. Do
  not hand-copy it into a merge commit.
- **Nothing else new is held back in Cycle 28.** No new unpushed
  files, secrets, or held-back work is reported in the Cycle 28
  report. The §5 review-not-blocker list is unchanged and carried
  forward: email-bid endpoint public by default, futures
  endpoints still return prices `null` until a licensed feed is
  wired (the Mae-Mart proxy now fills `futures_price` on
  collector rows only — it does not feed the futures endpoints),
  Advisor `/ask` is a 501 scaffold, eSign is a stub, normalized
  price rows carry no currency (`currency: null`).
- **Open decisions carried forward from Cycle 28 (not
  blockers):** **nothing new needs Adam in Cycle 28.** The full
  embed family is now re-verified (all 13 exact matches, 816
  rows) and the FS Grain USDA mirror is confirmed — the
  catalogue's verified counts stand. Playwright render checks
  still pending (DTN family — Al-Corn + Sunrise first — FMN
  filtered view (Winchester `location_filter=2523`), Mapleview,
  StoneX family (Frontier, CRC, UFC), The Andersons — closed for
  static collection, browser-only — and Landus, Vercel
  checkpoint); DTN toggles stay `false` until verified;
  scheduling the poller as a second cron job (deployment
  decision, checklist §4 step 6); Mae-Mart `cash_price` from
  futures + static basis (still open, gated on the
  licensed-feed decision); at least one `Commodity` row must
  exist before the first poller run; agricharts User-Agent
  decision resolved in Cycle 23 (Chrome UA kept). Still needs
  Adam (carried from Cycles 1–27, nothing new in Cycle 28):
  NASS key, FAS/data.gov key, LLM provider + key, Barchart/DTN
  licensed feed decision (redistribution licence — now also
  gates the CGB `cashbids-js.php` question and the Mae-Mart
  cash-price decision), ERP choice (Agvance recommended),
  eSign provider, pricing/hosting decisions, `gh` `workflow`
  scope, currency column decision (four concrete choices in
  `docs/plans/currency-design.md`), email-bid endpoint auth
  decision (public vs admin-only).

### 7n. After the merges — updated

§7 applies with the Cycle 28 tip as the end state: Alembic head
`0019` (unchanged since Cycle 7), test suite 709 passed / 0
failed, web build last fully passed in Cycle 17 (re-run at the
Cycle 28 merge step). The still-open decisions list in §7.4 is
unchanged by Cycle 28 except for the additions in §5n above.
Open work carried forward: Playwright render checks (DTN family
— Al-Corn + Sunrise first — FMN filtered view, Mapleview,
StoneX including Frontier, The Andersons — closed for static
collection, browser-only — and Landus, Vercel checkpoint);
Heartland / Mulvane closed for now (no new hypothesis);
Chadbourn + Hamer + Skyland 3370/3621 staleness watch
(exemption list); Mae-Mart cash-price decision; poller
scheduling decision; currency decision.
