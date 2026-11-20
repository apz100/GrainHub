# Keep-Warm Options for the Free Render API (grainhub-api)

**Status:** DRAFT for Adam's decision — no pinger, workflow, or plan change has been set up.
**Date:** 2026-11-19 (America/Toronto). All prices/limits cited to the page read on 2026-11-19.
**Zero-spend guardrail:** $0 options first. The only paid option is priced exactly at the end.

---

## 1. The problem, precisely

- The API runs on a Render **Free** web service. Render docs (Deploy for Free, https://render.com/docs/free): "Render **spins down** a Free web service that goes **15 minutes** without receiving any inbound traffic… A Free web service spins back *up* whenever it next receives an HTTP request… **This process takes about one minute.** Render displays a loading page to connecting browsers while a service is spinning up."
- So the user-visible cost of sleep is: **the first request after ≥15 idle minutes waits ~1 minute** (and API calls from the web app can time out or show an empty state on that first hit — the cold start already observed on the live dashboard check). Every later request is fast until the next idle gap.
- "Keeping it warm" = making sure *some* request lands at least every <15 minutes, forever. The target endpoint for pings is `GET https://grainhub-api.onrender.com/health/live` (exists in the app; liveness check, no DB needed — the cheapest possible wake-up). After the DNS change, the same path on `https://api.grainbids.com/health/live` works identically.

## 2. The instance-hours math (read this before choosing any pinger)

Render docs (same page): "Render grants **750 Free instance hours** to each workspace per calendar month: a Free web service consumes these hours as long as it's running (**spun-down services don't consume Free instance hours**). If you consume all of your Free instance hours during a given month, Render **suspends** all of your Free web services until the start of the next month."

Keeping one service awake 24/7 consumes:

| Month length | Hours awake (24 × days) | vs 750-hour allowance | Headroom |
|---|---|---|---|
| 30 days | 720 h | ✅ fits | 30 h |
| 31 days | 744 h | ✅ fits — barely | **6 h** |
| February (28 d) | 672 h | ✅ fits | 78 h |

Three qualifiers that make "barely" the operative word:

1. **The 750 hours are per workspace, not per service.** Any other free web service in the same Render workspace draws from the same pool. GrainHub currently has one free web service; adding a second always-warm one would blow the budget outright (2 × 744 = 1,488 h ≫ 750).
2. **Headroom in a 31-day month is 6 hours total** — restarts, deploys, and spin-up time all count as "running". Ordinary use fits, but there is no slack for a second service or an anomaly.
3. **Exhaustion is punished, not billed:** with no payment method, hitting 750 = the API is **suspended until the 1st of next month**. A keep-warm setup that misfires (e.g. two pingers, or a second service added later and forgotten) can convert "occasionally slow first hit" into "hard down for days". That asymmetry is the main risk of options (b) and (c).

Net: 24/7 warm is *arithmetically* inside the free allowance for a single service — 720–744 h ≤ 750 h — but with effectively zero margin in 31-day months.

## 3. Ping-volume math (for the 10-minute options)

- Every 10 minutes = 6/hour × 24 h × 30 days = **4,320 pings/month** (4,464 in a 31-day month).
- Every 5 minutes = **8,640 pings/month** (30-day). Every 14 minutes ≈ 3,086/month — the sparsest interval that still beats the 15-minute spin-down, with only 1 minute of slack for a delayed ping (not recommended; one late ping = asleep).
- 10 minutes is the sweet spot: 5 minutes of slack per cycle absorbs pinger jitter, at half the request volume of a 5-minute interval.

## 4. Options

| # | Option | Cost | Interval / pings per month | Keeps warm? | Main risks / notes |
|---|---|---|---|---|---|
| (a) | **Do nothing** | **$0** | — | No | First hit after 15 idle min waits ~1 min; occasional empty-looking dashboard on cold start. Zero risk, zero moving parts. Ingestion (see render-cron-proposal.md) is unaffected — the Actions jobs run the code themselves and don't need the API awake. |
| (b1) | **UptimeRobot free tier** pinging `/health/live` | **$0** | Fixed **5 min** on free = 8,640 pings/mo | Yes, with 10 min of slack per cycle | External account to own; free tier is a monitor product (you also get down-alerts, a genuine bonus). Interval can't be set to 10 min on free — it's 5 min or nothing. |
| (b2) | **cron-job.org** pinging `/health/live` | **$0** | Set **every 10 min** = 4,320 pings/mo | Yes, with 5 min of slack | Donation-funded community service, no SLA/punctuality guarantee; 30-second execution timeout vs ~1-minute cold start (see note below); auto-disables a job after >25 consecutive failures. |
| (c) | **GitHub Actions scheduled ping** (`*/10` cron + `workflow_dispatch`) | **$0** on the public repo | Every ~10 min = 4,320 runs/mo, each <1 min | Mostly — see delay caveat | GitHub schedule delays (worst at top of hour) can occasionally stretch a gap past 15 min → an occasional cold start slips through. Shares the 60-day inactivity-disable rule with the ingestion workflow. |
| (d) | **Render paid instance** (smallest paid web plan, `0.5c-512mb` / legacy "Starter") | **$7/month** | n/a — paid services don't spin down | Yes, unconditionally | Real money + payment method; also removes other free-tier limits, but costs 42× the Render-cron fallback and is unnecessary at current traffic. |

### Evidence for the table

- **(b1) UptimeRobot** — https://uptimerobot.com/pricing/ : Free plan is "$0/month… No credit card required!", includes **50 monitors** at a **5 min. monitoring interval** (HTTP monitor type included). 50 monitors ≫ the 1 needed; the binding constraint is the fixed 5-minute interval, not a ping quota (none is stated). Paid Solo ($12/month annual rate shown on the page) would allow 60-second intervals — not needed and not $0, listed only for completeness.
- **(b2) cron-job.org** — https://cron-job.org/en/ : "Our service is absolutely free and financed entirely by voluntary donations"; jobs can run "with frequencies up to once per minute". FAQ (https://cron-job.org/en/faq/): no limit on number of jobs (fair use expected); each execution **times out after 30 seconds** and reads at most 64 KB of response; a job that "subsequently fails more than 25 times" is auto-deactivated; punctuality is explicitly **not** guaranteed. ⚠️ The 30 s timeout vs the ~1 min cold start: the first ping after a sleep will *time out from cron-job.org's point of view* — but the request still reaches Render and wakes the service, so the *next* ping (10 min later) succeeds. Failures therefore don't accumulate consecutively while the service is healthy; the 25-failure disable only triggers if the API is genuinely down for ~4+ hours of pings. Acceptable, but it means cron-job.org's own success stats will under-report how well this works.
- **(c) GitHub Actions** — billing: standard runners are free in public repositories (https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions). Scheduling behaviour: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows — shortest interval 5 minutes (10 is fine); "The `schedule` event can be delayed during periods of high loads… High load times include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped." Mitigation built into the design: use offset minutes (`3,13,23,33,43,53 * * * *`) instead of `*/10` so pings avoid the top-of-hour crush; worst realistic case is an occasional 15+ minute gap and one cold start, not an outage. Also: the workflow must live on the default branch, and public-repo scheduled workflows are auto-disabled after 60 days without repo activity (same page) — the same caveat as the ingestion workflow; one re-enable fixes both.
- **(d) Render paid** — $7/month for the 512 MB web-service plan: Render's own comparison page, https://render.com/articles/render-vs-netlify ("Render web service or background worker, 512 MB — $7/month"; the page states its figures are from render.com/pricing). Paid instances don't spin down — spin-down is a Free-plan limitation (Deploy for Free doc). **This is a spend and is not recommended under the zero-spend instruction**; it is priced here so the option is decidable if cold starts ever become a real user problem.

## 5. Recommendation

**Start with (a) do nothing — $0 — and add (b1) UptimeRobot free only if cold starts actually bother real use.**

Reasoning: the site's current traffic is Adam + early testers; a ~1-minute wait on the first hit after an idle quarter-hour is an annoyance, not a failure, and ingestion doesn't depend on the API being awake at all (the GitHub Actions jobs run the ingestion code directly). Every keep-warm option spends the workspace's scarcest free resource — the 750 instance hours, with only 6 hours of headroom in a 31-day month — to remove that annoyance, and introduces a small but real risk of the API being *suspended* (worse than asleep) if anything else ever draws on the same pool.

If/when warm matters (sharing grainbids.com publicly, a demo for a potential user), **(b1) UptimeRobot free** is the best $0 tool: purpose-built, 5-minute checks, no repo coupling, no schedule-drop risk, and its down-alerts are independently useful. Prefer it over (c) — Actions delays make gaps past 15 minutes a matter of when, not if — and over (b2), whose 30-second timeout fights the 1-minute cold start on every genuine wake-up. Whichever pinger is chosen: **one pinger only**, pointed at `/health/live`, and re-check the workspace's instance-hour usage in the Render billing page after the first full month.

**Decision needed from Adam:** none right now under this recommendation. If he wants warm-from-day-one, the ask is: approve creating a free UptimeRobot account monitor for `https://grainhub-api.onrender.com/health/live` (later `api.grainbids.com`) — $0, no card.

---

### Sources (all read 2026-11-19)

- Render — Deploy for Free: https://render.com/docs/free (15-minute spin-down; ~1-minute spin-up; 750 free instance hours per workspace per month; suspension on exhaustion; spun-down services consume no hours)
- UptimeRobot — Plans & Pricing: https://uptimerobot.com/pricing/ (Free $0, no card; 50 monitors; 5-minute interval)
- cron-job.org — homepage: https://cron-job.org/en/ (entirely free, donation-funded; up to once per minute) and FAQ: https://cron-job.org/en/faq/ (30 s timeout; 64 KB read cap; >25 consecutive failures → auto-deactivate; no punctuality guarantee; no job-count limit, fair use)
- GitHub — Actions billing: https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions (standard runners free in public repos)
- GitHub — Events that trigger workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows (5-minute minimum interval; delay/drop behaviour; 60-day public-repo disable)
- Render — Render vs Netlify (official, prices from render.com/pricing): https://render.com/articles/render-vs-netlify (smallest paid web service $7/month)
- Repo (read-only): `GrainBids/grainbids/apps/api/app/main.py` (`/health/live` endpoint); `render.yaml` (free plan)
