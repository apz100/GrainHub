# Overnight Cycle 5 Report — GrainHub

**Branch:** `overnight/grainhub-cycle-5` (remote `https://github.com/apz100/GrainHub`)
**Date:** 2026-11-19 (overnight, America/Toronto)
**Status:** Cycle 5 complete — all remaining Bushel sites verified,
plus the Today page and a super-plan progress section.

**Never merged to master or to cycle-1/2/3/4. No spending, no vendor
contact, no emails sent, no secrets, no deployment changes, no
paywalled/licensed data scraped. No price, WASDE number, basis, or
bid invented anywhere.**

## 1. Commits

| Commit | What |
|---|---|
| `168cea4` | Today morning-view page + super-plan progress section (build passes, 33 pages) |
| `aeef76f` | All 11 Bushel sites verified live and registered; United Coop same-org question resolved; parser fixes |
| *(this commit)* | Cycle 5 report |

## 2. Test results

- **Full API suite: 364 passed, 0 failed** (Cycle 4 ended at 359;
  5 new Bushel tests).
- **Web build: PASS.** `npm run build` exit 0, 33 pages generated.

## 3. What was built (done)

### Bushel verification sweep — all 11 sites now verified
One polite GET per site (9 total, zero extras). All returned 200
with a `.cbmod` widget dated Wednesday, November 18, 2026. Live
HTML was saved only to `/tmp` scratch — nothing live entered the
repo, and no prices were copied into docs.

| Site | Rows | Shape | Crops |
|---|---|---|---|
| Chandler Feed (Chandler, MN) | 17 | 6-col widget | corn, oats, soy |
| Cameron Coop (Cameron, MO) | 4 | 7-col widget | corn, soy |
| CGS (Bazine, KS) | 4 | 6-col widget | wheat, milo, corn |
| Almota Elevator (Colfax, WA) | 12 | 7-col widget | SWW, HRW wheat, barley ($/t) |
| Williams Gin & Grain | 2 | 7-col widget | corn, grain sorghum |
| Rugby Farmers Elevator (Rugby, ND) | 12 | 5-col widget | HRS wheat, soy, corn |
| Lake Norden Farmers Elevator (Lake Norden, SD) | 2 | 7-col widget | corn, soy |
| United Cooperative (Webster City, IA) | 12 | 7-col widget | corn, soy |
| Forest River Coop (Forest River, ND) | 3 | 7-col widget | HRS wheat, corn, soy |

All 9 (plus FAC and Collwest from Cycle 4) are now registered in
`source_registry.py` with config toggles on.

**Parser fixes found by the sweep:** fractional CBOT
futures/change notation (`433-2` → 433.25, `−2-2` → −2.25, in
published cents) on Chandler/Forest River — previously mis-parsed
as 433.0/−2.0; classless location `<h2>` (Chandler, Rugby)
previously yielded location `None`; Forest River's "Cash Price"
Bid header with a blank Delivery header cell previously lost the
first section's delivery + bid. **Units warning (in the module
docstring):** futures/change keep each site's published units and
they vary — decimal sites publish futures in dollars (4.3325) and
change in cents (FAC −2.25) or dollars (Cameron, Lake Norden:
−0.0225); fractional sites publish both in cents. Consumers must
not assume one unit for these fields.

**Ambiguities resolved:** Almota's only `dtn` string sits inside
a base64 blob — the bids render in the Bushel widget. Williams
Gin's `/cashbidssingle-` URL is canonical (loads 200, self-linked
in the site's nav). **United Coop same-org question resolved by
the coordinator:** `unitedcooperative.com` is "United
Cooperative–Beaver Dam", corporate office N7160 Raceway Road,
Beaver Dam, WI 53916 — a different org from the Webster City, IA
Bushel site. Two orgs sharing a name; kept as separate sources.

### Today page
- New `/today` page: top 10 best bids, corn basis snapshot (top
  5), next report-calendar release with countdown, futures strip
  status with delay label, source-health count tiles — all real API
  data only, every section with an honest empty state, each linked
  to its full page. Added as the first nav entry.

### Super-plan progress section
- New section 9 in `docs/plans/grainhub-super-plan.md`:
  branch names, test counts 179 → 291 → 320 → 359 → 364, 2–3
  lines per cycle, and the remaining blockers needing Adam.

## 4. North Gower Grains boundary — applied

Zero references in any new Cycle 5 code, tests, pages, or docs
(verified by grep; the only super-plan match is the pre-existing
town reference in the bio line). No contact made.

## 5. What is still scaffold / stub

- FMN filtered view and Mapleview: need a live-browser Playwright
  render check.
- Mae-Mart cash prices: JS-filled from the site's futures proxy
  (not called).
- Futures endpoints still null until a licensed feed is wired;
  Advisor `/ask` still 501; eSign still a stub; no ERP sync, no
  payments. CI workflow file still unpushed (gh token lacks
  `workflow` scope).
- Currency is still not stored on normalized price rows.

## 6. Blocked / needs Adam

Carried from Cycles 1–4: NASS key, FAS/data.gov key, LLM provider +
key, Barchart/DTN licensed feed decision (redistribution licence),
ERP choice (Agvance recommended), eSign provider, pricing/hosting
decisions, gh `workflow` scope, currency column decision, email-bid
endpoint auth decision (public vs admin-only), Playwright render
checks (FMN filtered view, Mapleview).
