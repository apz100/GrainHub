# Decision paper — Auth for the email-bid endpoint

**Question:** Should `POST /api/email-bids/parse` stay public?
**Cost context:** Zero spend. Every option below is $0.

## What the code actually does (verified)

- **It is public.** In `app/api/routes/email_bids.py`, `parse_email_bids`
  (:249) takes only `request` and `db: Session = Depends(get_db)` — no
  `RequestContext`, no role check. `GET /api/email-bids/senders` (:218)
  takes no dependencies at all. `app/main.py:78` includes the router with
  no router-level guard.
- **It is parse-only, not ingestion into prices.** The module docstring
  (:1–11) and handler (:255, `_ = db  # Deliberately unused`) state it
  stores nothing and sends nothing; it runs the pure parser in
  `app/services/email_bid_parser.py` and returns a preview of the caller's
  own text/file. Uploads are capped at 2 MiB (:36). The route tests
  (`tests/test_email_bids_route.py`) use a fake session that *raises* on
  any DB read/write, proving no DB access. Parsed rows never reach
  `NormalizedPrice`, best-bids, or basis — it cannot poison market data.
- **No in-repo caller needs it public.** No web code calls it (no match
  under `apps/web`). The legacy pipeline does not call this HTTP endpoint
  either: `CashGrainBids/email_bid_sources.py` + `pipeline.py` parse
  Outlook mail locally on Windows. Today the endpoint is an operator
  preview tool: a human pastes email text or uploads a `.eml`/`.txt`/`.csv`.
- **How "admin" works elsewhere:** `app/core/request_context.py` defines
  `get_request_context` (headers `X-Org-Id`, `X-User-Email`, `X-User-Role`)
  and `require_admin` (:39–42: role must be `admin`/`owner`, else 403).
  Write endpoints use `Depends(require_admin)` — e.g.
  `app/api/routes/ingestion.py:100,118`, `sources.py:60+`, `quotes.py:64`.
  Caveat: this is a *trusted header*, not authentication — there is no
  login/session anywhere in the API, so anyone can send
  `X-User-Role: admin`. In production it still filters casual traffic,
  because `app/core/config.py` forces `ALLOW_IMPLICIT_ORG=false`, so a
  missing role defaults to `member` (`request_context.py:31`), not admin.

## Is the checklist's "one-line change" claim true?

Mostly, with footnotes. `docs/plans/deployment-checklist.md:242` says:
"Email-bid endpoint is public by default (admin-only is a one-line change
if Adam wants it)." For `POST /parse` alone it is *nearly* one line —
add `context: RequestContext = Depends(require_admin)` to the signature,
plus editing the import line in the same file. It is **not** literally
one line end-to-end: (1) `GET /senders` needs the same treatment or stays
public; (2) the standalone route tests build the router with only a fake
DB, so `require_admin` → `get_request_context` → an Organization DB lookup
would break them until they add a context override and headers; (3) any
future scripted caller must start sending `X-Org-Id` + `X-User-Role`.

## Options

### 1. Leave public
- **Work:** None. **Cost:** $0.
- **Risk:** Low, and bounded by parse-only design: no stored data leaks
  (response echoes only the caller's input; `/senders` exposes only
  sender names/markers already in the parser docstring), no writes to
  abuse. Residual risk is unauthenticated compute — repeated 2 MiB
  uploads as a cheap DoS / free parser oracle — with no rate limiting
  anywhere in `app/main.py`.

### 2. Require admin role header (`require_admin`)
- **Work:** Signature + import in `email_bids.py` for both routes, test
  overrides/headers, document the headers for the operator. ~½ hour.
  **Cost:** $0.
- **Risk:** Breaks anonymous preview use (the only current use) unless
  the caller sends headers. Protection is shallow — the header is
  spoofable by anyone who knows it — so this stops bots and casual
  probing, not a determined attacker. Consistent with every other
  write endpoint in the codebase.

### 3. Require a shared secret token (env var)
- **Work:** New setting in `app/core/config.py` (e.g. `EMAIL_BIDS_TOKEN`),
  a header check with constant-time compare in `email_bids.py`, set the
  var in Render, distribute it to whoever previews bids, tests. ~15–25
  lines plus deploy config — the most work of the four. **Cost:** $0.
- **Risk:** Real authentication, unlike Option 2, but a new secret to
  store, rotate, and leak; overkill for an endpoint that reads/writes no
  data. No other endpoint in the API uses this pattern, so it becomes a
  one-off mechanism to maintain.

### 4. Disable the endpoint in production
- **Work:** Gate `app.include_router(email_bids_router)` in
  `app/main.py:78` on `settings.app_env` (or a new flag); keep it in dev.
  A few lines + a test. **Cost:** $0.
- **Risk:** Removes the attack surface entirely, but also removes the
  preview tool from the live site — Adam would run it locally instead.
  The parser library itself is unaffected, and no pipeline depends on
  the HTTP route, so nothing else breaks.

## Recommendation: Option 2 (admin header), keep `/senders` gated too

The exposure today is low, so this is hygiene, not an emergency — but
Option 2 matches the codebase's existing convention for every other
non-public POST, costs $0, and needs no new secret or env var. Be clear
about what it buys: it ends anonymous/bot access; it is **not** real
authentication, because `X-User-Role` is caller-asserted. If a stronger
guarantee is ever needed because the endpoint grows DB writes, revisit
Option 3 then — and if Adam never uses the live preview, Option 4 is
equally defensible and simpler.

**Decision needed from Adam:** pick 1–4; default if no decision: leave
public (Option 1) is safe to deploy, per the parse-only evidence above.
