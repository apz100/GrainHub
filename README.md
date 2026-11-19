# GrainHub — Unified Repo

One repo containing all the code from Adam's two existing repos, merged
verbatim (no code changes, only this top-level README and .gitignore added).

- `GrainBids/` — from https://github.com/apz100/GrainBids
  The active platform. `GrainBids/grainbids/` is the runtime:
  - `apps/web`: Next.js + TypeScript + Tailwind
  - `apps/api`: FastAPI + SQLAlchemy + Alembic (Postgres)
  - Product modules: Bids, Alerts, Quotes, Sources, Watchlists, Admin,
    Market Report / newsletter. BasisBoard is the bids/market module
    inside GrainBids, not a separate product.
  - Production baseline: Vercel + Render + Supabase.
    Ingestion at 08:00 and 15:00 America/Toronto.
  - See `GrainBids/grainbids/README.md` for local dev.

- `CashGrainBids/` — from https://github.com/apz100/CashGrainBids
  The older Windows / Playwright pipeline that GrainBids grew out of:
  AgriCharts and elevator web collectors, Outlook email bid parsing
  (with OCR for image tables), Bank of Canada FX, basis normalization,
  CSV / Excel / PDF daily reports, and the North Gower pricing-decision
  layer. See `CashGrainBids/SETUP.md`.

## How the two fit together

GrainBids is the umbrella / active runtime. CashGrainBids is the
legacy pipeline — kept here as reference and as the source of the
collectors, email parsers, FX and pricing logic that were migrated
into GrainBids (`apps/api/app/platform/market_data/sources/` and
`apps/api/legacy_*`).

## Next work (planned silos, all on the GrainBids backend)

1. GrainStats-like research site — USDA reports (WASDE, Crop Progress,
   Grain Stocks, Export Sales), by report and by commodity.
2. Farmbucks-like price finder — market search by commodity, location,
   radius, delivery month; watchlists and alerts (Sprint 01).
3. GrainFox-like advisor — farm profile, risk, sell/hold signals, AI assistant.
4. Bushel / Grain Discovery-like elevator ops — white-label grower portal,
   contracts, scale tickets, payments, ERP integration.

## Sources

Original repos remain the upstream copies until this unified repo is
pushed somewhere. Do not edit the originals and this copy in parallel
without merging — pick one as the source of truth.
