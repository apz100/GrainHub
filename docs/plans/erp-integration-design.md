# Elevator Ops — ERP Integration Design (Agris / Agvance / AgTrax)

**Status: design only.** No vendor has been contacted, no partner
agreement exists, no credentials exist, and no pricing is quoted
anywhere in this document. Every price or cost statement below is
either "not published — ask the vendor" or explicitly labelled as a
stale third-party report. Nothing here authorises spending, contact,
or a trial sign-up.

**Scope:** Phase 4 of the super plan
(`docs/plans/grainhub-super-plan.md` §6) — how Elevator Ops
(contracts, scale tickets, settlements, grower portal, CRM) would
integrate with Agris, Agvance, and AgTrax. This is a design and
vendor-selection document only. No code is written here, and no
integration is built until Adam picks a vendor and that vendor
agrees to work with GrainHub.

**What exists today (Cycle 1):** Elevator Ops v1 is a scaffold —
`Contract`, `ScaleTicket`, and `CRMNote` models, routes under
`/api/elevator-ops/`, a white-label grower portal page (`/portal`),
and an eSign stub that records `pending_signature` and calls no
provider. There is **no ERP sync, no payments, no settlements, and
no invoicing**. The ERP is always the system of record for grain
accounting; GrainHub must never become a second, divergent ledger.

**Boundary (standing):** GrainHub — and any company built from it —
must not be related to Adam's employer's elevator company in any
way except that scraping its public prices is OK. That means: no
ERP pilot, no showcase, no featured integration, no branding, and
no implied affiliation with any specific elevator, including in
this document. All examples below use synthetic names only
("Testville", "Test Elevator Co.").

## 1. What each ERP is (public sources only)

### 1.1 Agris — Greenstone Systems / Cultura Technologies

- **Vendor:** Greenstone Systems, a brand of Cultura Technologies
  (Alpharetta, Georgia), part of Volaris Group / Constellation
  Software. The AGRIS suite was acquired in 2011; the system itself
  dates to 1978.
- **Deployment:** on-premise at the elevator/co-op, or hosted through
  Greenstone. It is **not cloud-native SaaS** — due diligence must
  cover how hosting is delivered and how web companions connect back
  to a core installation.
- **Scale:** a GEAPS listing credits Greenstone with 400+ customers
  and 5,000+ ERP users — the largest installed base of the three.
- **Modules:** grain accounting and financial reporting; commodity
  contract and basis management; settlements; position tracking;
  multi-location inventory; cooperative patronage/equity. Companions:
  **oneWeigh** (scale automation), **MyGrower** (grower self-service
  portal), **AgTMS** (transportation), **CINCH**, **Insights**
  (dashboards).
- **Integration surface (public):** no public API documentation was
  found. Integrations exist as **vendor partnerships**: Barchart
  integrates with Agris for grower accounting data (scale tickets,
  contracts, balances, settlements), contract generation from filled
  offers, and eSign; Bushel integrates bi-directionally with Agris
  (reads and writes) for statements, invoices, and retail data.
  The integration path is therefore a partner agreement with
  Greenstone, not a self-serve API key. The technical mechanism
  (API, direct database access, file exchange, or a Greenstone-hosted
  connector) is a question for the vendor — see §5, Q1.
- **Pricing:** not published; quoted per organisation against modules,
  locations, and user counts, typically with annual maintenance.

### 1.2 Agvance — Software Solutions Integrated (SSI)

- **Vendor:** Software Solutions Integrated, LLC (Shelbyville, IL /
  Avon, IN); 40+ years in ag retail software. Agvance is an
  all-in-one ERP for ag retailers and cooperatives: accounting,
  agronomy, grain, energy, and patronage.
- **Deployment:** cloud-based; the API is described as "100% cloud
  based restful API" with no install.
- **Grain module:** Agvance Grain "fully automates your entire grain
  elevator operation" — receiving, scale tickets, inventory,
  contracts, settlements, storage/drying charges. Grower portal is
  **Grower360** (offers, balances, grain positions); Barchart offers
  are shown inside Grower360. **Agvance Analytics** covers reporting
  across products.
- **Integration surface (public):** the **only one of the three with a
  public developer programme**. SSI introduced the Agvance API in
  2015; `agvance.net/api` publishes developer resources (API
  introduction, user setup, status codes, production vs testing
  keys, connection authorisation, release notes, support requests).
  Third-party software companies already build mobile/web tools on
  it. AgGateway EDI messaging and AGIIS directory support are also
  documented for B2B/retail integration. Barchart has a published
  Agvance integration (accounting data, contracts, eSign into
  Marketplace apps).
- **Pricing:** not published in the material found — ask the vendor.
  The API itself is presented as a developer resource, not a
  separately priced product, but confirm whether API access needs a
  customer sponsorship, a partner agreement, or a fee.

### 1.3 AgTrax — AgTrax (Hutchinson, Kansas)

- **Vendor:** AgTrax, headquartered in Hutchinson, KS; ~28 years
  building agribusiness software for full-service cooperatives,
  grain elevators, feed stores, and agronomy providers, across the
  top US agriculture states and central Canada.
- **Products:** **TraxView** (core accounting: commodity accounting,
  AR/AP, purchasing, invoicing, inventory, payroll, patronage and
  equity, hedging); **AgRemote** (scale interface — inbound/outbound
  tickets); **OnlineAccess** (web portal: balances, statements,
  invoices, proof of yield, grain/equity balances); **Elevate**
  (bin management and grain traceability, incl. FSMA-oriented
  traceability); plus SQL replication and Power BI reporting.
- **Integration surface (public):** no public API documentation was
  found. What is documented is a **partner programme with 20+
  integrated partners**, and two concrete mechanisms:
  - **APIs with named partners** — Barchart (phone app: bids, grain
    tickets, grain balances) and Square 9 (invoice imaging: an
    approved invoice's data is sent into AgTrax via API).
  - **ODBC extraction** — customers use ODBC to pull AgTrax data
    into custom reports and Excel. SQL replication is also listed.
  - Bushel has a **bi-directional** AgTrax integration: digital
    make-offer flows create contracts automatically in AgTrax, and
    e-sign is automated between the two systems.
  The integration path is therefore a partner agreement, with the
  technical mechanism (partner API, ODBC/SQL replication, or both)
  to be confirmed — see §5, Q1.
- **Pricing:** not published in the material found — ask the vendor.

## 2. What Elevator Ops needs from an ERP

GrainHub's Elevator Ops v1 models are the starting point; the ERP
owns the authoritative versions of the same records.

| GrainHub object (today) | ERP counterpart | Direction | Notes |
|---|---|---|---|
| `Contract` (type, commodity, quantity, price, delivery, status) | Grain contract: cash, forward, basis, hedge-to-arrive, deferred payment | ERP -> GrainHub (read); GrainHub -> ERP (create from a filled offer, only where the ERP supports it) | Contract creation from GrainHub is the highest-risk write: it must be idempotent and confirmed by the ERP's own contract number before it is shown as real |
| `ScaleTicket` (gross/tare/net, moisture, grade factors, ticket number) | Scale ticket from the scale interface (oneWeigh / AgRemote / Agvance Grain) | ERP -> GrainHub (read, near-real-time) | Tickets are created at the scale, never in GrainHub. GrainHub displays them and links them to contracts/settlements |
| Settlement / invoice / payment | Settlement, invoice, AR/AP, patronage | ERP -> GrainHub (read) | No payments in GrainHub until a payments design exists. Display-only in phase 1 of the integration |
| Grower balances (bushels by commodity, storage, drying) | Commodity balances, grain bank, storage/drying charges | ERP -> GrainHub (read) | The grower portal's core read model |
| CRM notes / producer records | Customer master, producer notes | Both (read mostly) | GrainHub CRM notes are GrainHub-native; only the customer identity is shared, by ERP customer id |
| eSign | Contract signature (Barchart/Agris pattern; Bushel/AgTrax pattern) | GrainHub -> ERP (status) | eSign provider is undecided (Cycle 1 blocker). Do not design the signature flow until the provider is picked; the ERP only needs the signed status + document reference back |

**Out of scope for the first integration:** payments and
settlements execution, payroll, inventory valuation, hedging/position
management, agronomy, and energy. Those stay in the ERP.

## 3. Sync model (design)

### 3.1 System of record

- The ERP is the system of record for contracts, scale tickets,
  settlements, balances, and customer identity. GrainHub keeps a
  **read cache** (its existing `Contract` / `ScaleTicket` tables,
  plus an `erp_sync_state` record per tenant) and never treats its
  own copy as authoritative.
- Every synced record carries: ERP record id, ERP record version or
  last-modified timestamp, sync timestamp, and sync source. A record
  with no ERP id is GrainHub-native (e.g. a CRM note) and is never
  pushed to the ERP.

### 3.2 Sync direction and cadence

- **Read (ERP -> GrainHub):** poll on a schedule (hourly at first;
  near-real-time only if the vendor offers webhooks or a streaming
  feed — none of the three advertises webhooks publicly). Poll per
  tenant, per object type, using the ERP's last-modified watermark
  so each run fetches only changes. Scale tickets during harvest
  need the shortest interval; contracts and balances can be slower.
- **Write (GrainHub -> ERP):** only two writes in the first phase,
  both behind explicit confirmation:
  1. Create a contract from a filled offer (the Bushel/AgTrax
     pattern), and
  2. Record an eSign completion against a contract.
  Both must be **idempotent**: GrainHub sends a client-generated
  idempotency key; a retry after a network failure must not create
  a duplicate contract. The write is only shown as complete after
  the ERP returns its own contract number / status.
- **Conflict rule:** if the ERP record changed after GrainHub's last
  sync, the ERP wins and GrainHub re-reads. GrainHub never
  overwrites an ERP record from a stale cache. A failed write is
  recorded in ingestion/sync diagnostics with the ERP's error, and
  the portal shows the record as "sync pending" — never as if the
  write had succeeded.

### 3.3 Tenancy, credentials, and audit

- One ERP connection per elevator tenant (per org), never a shared
  GrainHub-wide credential. Credentials are per-tenant secrets in
  env / the approved secret store, never in git, never in the
  database in plaintext, and never logged.
- Every sync run writes a run record (started/finished, objects
  read/written, errors) in the same style as `ingestion_runs`, so
  the source-health dashboard pattern extends to ERP health:
  a tenant whose ERP sync is failing shows `broken` with the real
  reason instead of silently showing stale balances.
- Audit log for every write: who (grower or merchandiser),
  what (contract id, idempotency key), when, and the ERP's
  confirmation. This is the paper trail that replaces slippage
  disputes — the same requirement Bushel's firm-offer flow exists
  to satisfy.

### 3.4 What "integrated" must mean before launch

- A contract created in GrainHub appears in the ERP with the ERP's
  own number, and a contract created in the ERP appears in the
  grower portal, within one sync interval.
- A scale ticket created at the scale appears in the portal within
  one sync interval, with the same ticket number, weights, moisture,
  and grade factors as the ERP.
- A failed sync is visible (dashboard + portal banner) with the real
  error, and no stale balance is presented as current.
- No GrainHub write can create a duplicate contract on retry.
- The ERP vendor has confirmed in writing what GrainHub may read,
  what it may write, and what happens to synced data if the
  integration is terminated.

## 4. Per-vendor integration sketch

### 4.1 Agvance (recommended first — see §6)

- **Path:** public REST API (`agvance.net/api`). Request developer
  access: production vs testing keys are a published concept, so
  ask for a testing key first and build against it.
- **Expected shape:** REST resources for grain contracts, scale
  tickets, balances, and customers, behind per-tenant API
  authorisation. Confirm the exact resources, pagination, and
  rate limits from the API docs once access is granted — the
  public page lists the doc set but not the endpoint inventory.
- **Fit:** cloud API matches GrainHub's architecture (no on-prem
  connector to deploy); grain module covers the objects in §2;
  Grower360 is the closest existing analogue to GrainHub's portal,
  which makes the read model easy to validate; Barchart precedent
  proves third-party portal integrations are supported.
- **Risks:** Agvance is ag-retail-first; grain is one module among
  agronomy/energy. Confirm the grain API surface is as complete as
  the retail surface, and confirm whether API access requires the
  elevator to sponsor GrainHub or a direct SSI partner agreement.

### 4.2 Agris (second)

- **Path:** partner agreement with Greenstone. No public API docs,
  so the first step is a commercial conversation, not code: ask
  for the integration guide, the data-access mechanism, and whether
  a sandbox/hosted demo environment exists.
- **Fit:** largest installed base (400+ customers) and the deepest
  grain-accounting feature set (contracts, basis, settlements,
  positions, patronage); oneWeigh + MyGrower cover the scale and
  portal edges GrainHub would otherwise have to build around.
- **Risks:** on-prem/hosted deployment means every tenant may need
  a per-site connector or a Greenstone-hosted bridge — the
  integration effort is per-tenant, not write-once. No public docs
  means the technical design cannot be validated until Greenstone
  shares them. MyGrower already is a grower portal, so GrainHub
  must define clearly what its portal adds rather than duplicating it.

### 4.3 AgTrax (third)

- **Path:** partner agreement (20+ integrated partners). Ask for
  the partner API documentation and a sandbox; in parallel, evaluate
  the ODBC/SQL-replication read path, which customers already use
  for reporting — it may be the fastest read-only route for tickets
  and balances, with the partner API reserved for contract writes.
- **Fit:** TraxView + AgRemote + OnlineAccess cover the same objects
  as §2; Elevate adds bin-level traceability GrainHub does not have;
  the Bushel precedent proves bi-directional contract creation and
  e-sign automation are supported patterns.
- **Risks:** no public API docs; ODBC is a read path, not a write
  path, so contract creation still needs the partner API; a
  per-tenant ODBC/SQL connection is operationally heavy (VPN or
  hosted bridge per elevator) compared with a cloud API.

## 5. Questions to ask each vendor

Ask these through Adam, after he picks an order. Do not cold-contact
vendors from the repo.

**For all three:**

1. What is the integration mechanism — public REST API, partner API,
   direct database/ODBC access, file exchange, or a vendor-hosted
   connector — and is there written developer documentation and a
   sandbox/testing environment?
2. Is there a partner programme, and what does it require (agreement,
   fee, certification, customer sponsorship, security review)?
3. Which objects are readable (contracts, scale tickets, settlements,
   balances, customers) and which are writable (contract creation,
   eSign status)? What are the exact resources/fields, pagination,
   rate limits, and idempotency support for writes?
4. How are changes delivered — polling with last-modified watermarks,
   webhooks, or batch export — and what is the realistic latency for
   a scale ticket during harvest?
5. How does authentication/tenancy work — per-elevator credentials,
   OAuth, API keys, or IP allow-listing — and how are credentials
   rotated?
6. What are the commercial terms — integration fee, per-tenant fee,
   per-transaction fee, revenue share, or none — and what happens to
   synced data if the integration is terminated?
7. Who is the integration contact and what is the support channel
   when a sync breaks?

**Vendor-specific:**

- **Agris/Greenstone:** How does a cloud application connect to an
  on-prem or Greenstone-hosted Agris core — is there a hosted API
  gateway, or a per-site connector? How does MyGrower connect, and
  can GrainHub use the same channel? Is there a demo tenant?
- **Agvance/SSI:** What is the process for a testing key vs a
  production key, and does API access need the elevator customer to
  sponsor GrainHub? Is the grain API surface (contracts, tickets,
  balances) as complete as the retail surface? Are there rate limits
  or quotas?
- **AgTrax:** Is the partner API the same surface Barchart and Bushel
  use, and can GrainHub join the same programme? Is ODBC/SQL
  replication a supported read path for a third-party portal, or
  only for the customer's own reporting? How is a per-tenant
  connection secured (VPN, hosted bridge)?

## 6. Recommendation: approach Agvance first

**Approach Agvance first, Agris second, AgTrax third.**

Reasons, all from the public material above:

1. **It is the only one with a public, documented, cloud REST API.**
   Agvance has published developer resources since 2015, with
   testing vs production keys and a stated welcome to third-party
   software companies. GrainHub can evaluate the API surface and
   build a prototype against a testing key without a per-tenant
   on-prem deployment — the other two require a commercial
   conversation before any technical validation is possible.
2. **It covers the objects in §2.** The grain module, Grower360
   portal, and Agvance Analytics map directly onto contracts, scale
   tickets, balances, and reporting. The Barchart precedent shows
   the exact pattern GrainHub needs (ERP accounting data into a
   grower-facing app, plus eSign) already works.
3. **Lowest integration risk.** A cloud API means one integration
   serves every Agvance tenant, instead of a per-site connector
   (Agris) or a per-tenant ODBC/SQL connection (AgTrax).

Counter-considerations, stated honestly:

- **Agris has the larger installed base** (400+ customers) and the
  deepest grain-accounting depth. If Adam's target elevators are
  mostly Agris shops, Agris may be the commercially right first
  choice despite the higher technical friction. Ask Adam which ERP
  his target elevators actually run before finalising the order.
- **AgTrax's ODBC path** may be the fastest read-only route for a
  single pilot elevator, but it does not scale to many tenants and
  does not cover writes — it is a tactical option, not a platform
  strategy.
- **The recommendation is about integration order, not exclusivity.**
  Elevator Ops should be designed (§3) so the ERP is a pluggable
  adapter: the same GrainHub `Contract` / `ScaleTicket` models and
  the same sync-state machinery, with one adapter per vendor.
  Building Agvance first must not hard-code Agvance semantics into
  the core models.

## 7. Sequencing (after Adam picks the vendor)

1. Adam confirms the order and the target elevator profile (which ERP
   the elevators GrainHub wants to serve actually run).
2. Vendor conversation (questions in §5) and written confirmation of
   read/write scope, data handling, and termination terms.
3. Testing/sandbox access; validate the API surface against §2 and
   §3.4. If the surface does not cover contracts + tickets +
   balances, stop and re-evaluate — do not build a partial sync and
   present it as complete.
4. Build one adapter (read-only first: tickets, balances, contracts),
   behind a per-tenant feature flag, with sync-run diagnostics.
5. Add the two writes (contract from filled offer; eSign status)
   only after read sync is proven in a pilot tenant, with
   idempotency tests.
6. eSign provider decision (Cycle 1 blocker) in parallel — the ERP
   write for eSign status depends on it.

## Sources (public, checked 2026-11-19)

- Agris profile — usa.erp-software.org/software/agris/ (vendor,
  deployment, modules, pricing model); Greenstone/GEAPS listing —
  geaps.com/company/greenstone-systems/ (400+ customers, 5,000+
  users); Barchart–Agris integration — barchart.com/solutions/
  integrations/agris; Bushel–Agris integration —
  bushelpowered.com/partnerships-integrations/agris.
- Agvance API developer resources — agvance.net/api (API since 2015,
  cloud REST, testing vs production keys); Agvance Grain —
  agvance.net/products/grain; Barchart–Agvance integration —
  barchart.com/solutions/integrations/agvance.
- AgTrax — agtrax.com (About Us; 20+ integrated partners); Scott
  Cooperative case study — agtrax.com/case-studies/
  scott-cooperative-association/ and grainjournal.com (TraxView,
  AgRemote, OnlineAccess, Elevate, ODBC, partner APIs); Bushel–
  AgTrax integration — bushelpowered.com/partnerships-integrations/
  agtrax.

**Design only — no vendor contacted, no keys, no pricing quoted.**
