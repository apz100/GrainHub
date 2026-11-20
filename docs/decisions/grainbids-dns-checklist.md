# DNS Checklist: grainbids.com → Vercel (web) + Render (API)

**Status:** DRAFT checklist for Adam to execute — no domain, DNS, or env changes have been made.
**Date:** 2026-11-19 (America/Toronto). All record values and limits are cited to the official doc page they were read from on 2026-11-19.
**Cost:** **$0.** Custom domains are included on both free tiers for this setup — see §4, including the one numeric limit to watch.
**Registrar:** unknown — every step below is written generically for "your registrar's DNS panel" (wherever grainbids.com's DNS records are edited). Do **not** change the domain's nameservers; only add/edit the records in §2. Leaving nameservers alone keeps any existing records (e.g. email MX) untouched.

**Target setup**

| Hostname | Points to | Serves |
|---|---|---|
| `grainbids.com` | Vercel | Web app (currently `grainhub-web.vercel.app`) |
| `www.grainbids.com` | Vercel | Web app (same project; one of apex/www is canonical, the other redirects — pick in step 1) |
| `api.grainbids.com` | Render | API (currently `grainhub-api.onrender.com`) |

---

## 1. Step order (do not reorder)

The dashboards must know about each domain **before** DNS points at them — both Vercel and Render only display the exact record values to use, and only issue TLS certificates, for domains already added to the service/project.

- [ ] **Step 1 — Add the domains in the dashboards first.**
  - **Vercel:** open the web project → **Settings → Domains** → **Add Existing** → add `grainbids.com`. Vercel will prompt to also add the `www` subdomain — accept, and set which of apex / `www` is the primary (the other redirects to it). (Vercel docs, Adding & Configuring a Custom Domain: https://vercel.com/docs/domains/working-with-domains/add-a-domain — domains are managed from Settings → Domains; adding an apex prompts for `www`.)
  - **Render:** open the `grainhub-api` service → **Settings → Custom Domains** → **+ Add Custom Domain** → add `api.grainbids.com`. (Render docs, Custom Domains: https://render.com/docs/custom-domains — "Only web services and static sites support custom domains"; the 3-step flow is add in dashboard → configure DNS → verify.)
  - In both dashboards, **copy the exact record values shown for this project/service** — see the ⚠️ notes in §2. The values in the table are the expected ones, but the dashboard value wins if they differ.
- [ ] **Step 2 — Add the DNS records in §2** at your registrar's DNS panel, and remove the conflicting records listed there.
- [ ] **Step 3 — Verify in both dashboards.** Vercel: the domain's status in Settings → Domains flips to properly configured once DNS propagates and the certificate issues (usually minutes; DNS changes can take longer to propagate). Render: service → Settings → Custom Domains → **Verify**; on success Render issues the TLS certificate. (Render docs: if verification fails, DNS may not have propagated yet — wait a few minutes and retry.)
- [ ] **Step 4 — Test the API on its new name before touching any env var:** `https://api.grainbids.com/health/live` should return `{"ok": true, "env": "production"}`. First hit may take ~1 minute — the free service cold-starts if it was asleep (see keep-warm.md). Also test `https://grainbids.com` and `https://www.grainbids.com` load the web app over HTTPS.
- [ ] **Step 5 — Only after Step 4 passes, update env vars** (§3) and redeploy. Until this step, the site keeps using the working `*.vercel.app` / `*.onrender.com` addresses, so a DNS problem cannot take the app down.

---

## 2. Records to add (at your registrar's DNS panel)

| # | Hostname | Type | Name/host field | Value | Notes |
|---|---|---|---|---|---|
| 1 | `grainbids.com` | **A** | `@` (apex/root — some panels want the field left blank) | **The IPv4 address shown in Vercel Settings → Domains for this project** — expected `76.76.21.21` | Apex domains cannot use CNAME; Vercel configures them with an A record. ⚠️ Use the dashboard's value, not a copied one: Vercel's DNS docs warn "Use the IP address shown in your project's Settings > Domains. Projects can be assigned different addresses, so don't copy one from another project." (https://vercel.com/docs/domains/managing-dns-records). `76.76.21.21` is the long-standing documented Vercel anycast IP and the expected value; if the dashboard shows a different address, the dashboard is right. |
| 2 | `www.grainbids.com` | **CNAME** | `www` | **The CNAME target shown in Vercel Settings → Domains for this project** — a project-specific target of the form `<hash>.vercel-dns-<nnn>.com` | Vercel configures subdomains with a CNAME, and "Each project has a unique CNAME record e.g. `d1d4fc829fe7bc7c.vercel-dns-017.com`" (https://vercel.com/docs/domains/working-with-domains/add-a-domain). ⚠️ Older guides (and Vercel's own CLI examples) show the generic `cname.vercel-dns.com`; if the dashboard shows a project-specific target, use that — a stale/generic value can leave the domain at "Invalid Configuration". |
| 3 | `api.grainbids.com` | **CNAME** | `api` | `grainhub-api.onrender.com` | Render docs, Configuring DNS Providers: "For non-root domains, you should always add a `CNAME` record pointing to your app's Render subdomain" (https://render.com/docs/configure-other-dns). The service keeps its `onrender.com` address alongside the custom domain — nothing breaks if DNS is later removed. |

### Records to remove / check while you're in the panel

- [ ] **Any other A or AAAA record for `@` (apex)** that conflicts with record 1 — Vercel flags conflicting A/AAAA/CNAME records for the same hostname as an invalid configuration (troubleshooting table, add-a-domain doc above).
- [ ] **Any AAAA record covering `api.grainbids.com`** (and, per Render's instruction, AAAA records on the domain while configuring): "Remove any `AAAA` records from your domain while configuring DNS. `AAAA` records map to an IPv6 address, and Render uses IPv4." (https://render.com/docs/custom-domains). In practice the one that matters is any AAAA that would answer for `api`; removing stray AAAA records for the three hostnames in scope is the safe reading of both vendors' guidance.
- [ ] **Any existing CNAME for `www` or `api`** pointing somewhere else (e.g. registrar parking/defaults) — replace it with records 2 and 3; a hostname can only have one CNAME.
- [ ] **CAA records:** only if the domain already has CAA records — they must allow the issuers: Render requires Let's Encrypt (`letsencrypt.org`) and Google Trust Services (`pki.goog`) (custom-domains doc, CAA section); Vercel issues via Let's Encrypt. If there are no CAA records, do nothing.
- [ ] **Conditional — TXT `_vercel`:** only if Vercel says the domain is in use by another Vercel account/team when you add it in Step 1. Then Vercel shows a TXT record to add at `_vercel.grainbids.com` to verify access (add-a-domain doc, "Verify domain access"). Not expected here; listed so a prompt in the dashboard isn't a surprise.

**TTL:** leave the registrar default (or 3600 if asked). Lowering TTL a day ahead would speed a rollback, but for a first-time setup with no existing traffic on these names it is unnecessary.

---

## 3. Env updates — after `api.grainbids.com` works (Step 5)

Do these only after Step 4's health check passes on the new hostname. Order matters: CORS first (API side), then the web's API URL, so the browser is never pointed at an API that rejects its origin.

- [ ] **Render (API service) → Environment:** set `API_CORS_ORIGINS` to include the new web origins **in addition to** the existing Vercel origin during transition:
  `https://grainbids.com,https://www.grainbids.com,https://grainhub-web.vercel.app`
  (The app refuses to start in production with no CORS origin set — keep the list non-empty at all times. Saving triggers a redeploy; confirm `/health/live` still returns 200 after it.)
- [ ] **Vercel (web project) → Settings → Environment Variables:** set `NEXT_PUBLIC_API_URL` = `https://api.grainbids.com`, then **redeploy** the web project (this value is baked into the browser bundle at build time — changing the env var without a redeploy changes nothing).
- [ ] **Verify end to end:** load `https://grainbids.com`, confirm market search / bids pages return data (the browser is now calling `api.grainbids.com`; a CORS mistake shows up here as empty data with API health still green).
- [ ] **Optional, later:** the `onrender.com` subdomain can be disabled in Render (Settings → Custom Domains → Render Subdomain → Disabled) once everything has run on the custom domain for a while. **Recommendation: leave it enabled** — it is a free fallback/debug address, and disabling it makes all requests to it 404.

---

## 4. Free-tier blockers — checked, none found (with evidence)

- ✅ **Render free web services support custom domains.** Deploy for Free (https://render.com/docs/free), "Free web services — Supported features include: Custom domains; Managed TLS certificates". So `api.grainbids.com` on the free `grainhub-api` service is allowed, with free auto-issued/renewed TLS (custom-domains doc: "Render automatically creates and renews TLS certificates for all custom domains").
- ✅ **Render domain allowance covers this at $0.** Custom Domains doc (https://render.com/docs/custom-domains): Hobby workspaces include **2** custom domains; each beyond that is $0.25/month. This setup adds exactly **1** Render custom domain (`api.grainbids.com`) → within the included 2 → **$0**.
- ✅ **Vercel Hobby domain limit covers this.** Add-a-domain doc: "Hobby teams have a limit of 50 custom domains per project." This setup adds **2** (`grainbids.com`, `www.grainbids.com`) → **$0**.
- ⚠️ **Not a blocker, but the one number to remember:** if more Render custom domains are added later (e.g. a second API service), the 3rd and beyond cost $0.25/month each on Hobby. Nothing in the current plan comes close.
- ⚠️ **Process gotcha, not a tier limit:** both vendors verify the dashboard-added domain against live DNS and issue certificates only after records propagate. Adding DNS first (before the dashboard steps) just wastes time — hence the step order in §1.

## 5. Rollback

DNS changes are fully reversible: delete records 1–3 (or repoint `api` back) and revert the two env vars in §3 to the `*.vercel.app` / `*.onrender.com` values, then redeploy web. The original platform URLs never stop working during or after this change (Render keeps the `onrender.com` subdomain alongside custom domains; Vercel keeps the `vercel.app` URL).

---

### Sources (all read 2026-11-19)

- Vercel — Adding & Configuring a Custom Domain: https://vercel.com/docs/domains/working-with-domains/add-a-domain (apex → A record; subdomain → CNAME; per-project unique CNAME target; 50 custom domains/project on Hobby; TXT verification case; conflicting-record troubleshooting)
- Vercel — Setting up a custom domain (CLI): https://vercel.com/docs/domains/set-up-custom-domain (dashboard-first flow; use the recommended values from Settings → Domains / `vercel domains verify`)
- Vercel — Managing DNS Records: https://vercel.com/docs/domains/managing-dns-records (apex A record must use the IP shown for the project; projects can be assigned different addresses)
- Render — Custom Domains: https://render.com/docs/custom-domains (3-step flow; Hobby includes 2 domains, $0.25/month each beyond; free managed TLS; remove AAAA records; CAA issuers)
- Render — Configuring DNS Providers: https://render.com/docs/configure-other-dns (subdomains always CNAME to the service's `onrender.com` subdomain; root-domain A record `216.24.57.1` / ANAME-ALIAS — not needed here since the apex goes to Vercel, listed only so the value isn't mistakenly used for `api`)
- Render — Deploy for Free: https://render.com/docs/free (free web services support custom domains + managed TLS; spin-up ≈ 1 minute)
- Repo (read-only): `docs/plans/deployment-checklist.md` §2 (env var names and semantics: `API_CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`); `render.yaml` (service name `grainhub-api`, free plan)
