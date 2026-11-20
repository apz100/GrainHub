"""Night queue 2026-11-20, item 1 — bounded-loading VOLUME tests.

Marathon Phase A (docs/marathon/phase-a-notes.md) proved the
payload-deferral fixes with SQL inspection and small real-DB tests:
the shared preview query, top-movers, price history, best-bids,
saved-search / watchlist previews and the quotes export loader no
longer transfer ``PriceSnapshot.raw_payload_json``. What Phase A did
not prove is the *volume* side of the same production lesson (the
2026-11-19 basis-tracker OOM on the 512 MB instance): when the table
holds far more rows than an endpoint returns, does the endpoint's
materialized load stay bounded by its documented fetch bound instead
of growing with the table?

These tests seed thousands of (snapshot, price) pairs into a real
SQLite database and count how many ORM instances the endpoint
actually materializes, via SQLAlchemy ``load`` events on
``NormalizedPrice`` / ``PriceSnapshot`` (GC-proof, unlike identity-map
inspection after a handler returns), plus a check of the emitted SQL
that the deferred ``raw_payload_json`` column is never transferred.
Bounds pinned:

* shared preview loader / price list / top-movers: fetch ``limit*3``
* price history loader: ``_HISTORY_FETCH_LIMIT`` (5,000) rows
* best-bids: ``_BEST_BIDS_FETCH_LIMIT`` (300) rows
* saved-search preview: the ``limit`` parameter (<= 300)
* watchlist preview: the ``limit`` parameter (<= 200)
* quotes export loader: the ``limit`` parameter (endpoint max 20,000)

SQLite in-memory; JSONB columns are swapped to plain JSON for DDL
only (same trick as tests/test_phase_a_endpoint_robustness.py —
production runs Postgres). The normalized-prices handlers apply
Postgres-only recency filters (``~`` / ``to_date`` / ``initcap``);
those are monkeypatched to a no-op exactly as in Phase A — the fetch
bounds being pinned live in the loaders/queries, untouched by the
stub.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import JSON, create_engine, event, insert  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.api.routes.best_bids as best_bids_route  # noqa: E402
import app.api.routes.normalized_prices as np_route  # noqa: E402
import app.api.routes.price_history as price_history_route  # noqa: E402
import app.api.routes.quotes as quotes_route  # noqa: E402
import app.api.routes.saved_searches as saved_searches_route  # noqa: E402
import app.api.routes.watchlists as watchlists_route  # noqa: E402
from app.core.request_context import RequestContext  # noqa: E402
from app.models.commodity import Commodity  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.saved_search import SavedSearch  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.models.watchlist import Watchlist  # noqa: E402

ORG_ID = uuid.uuid4()
CTX = RequestContext(org_id=ORG_ID, user_email=None, user_role="admin")
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
# Small payload for volume seeds: deferral is what is being proven,
# not payload size (Phase A already pins the large-payload shape).
SMALL_PAYLOAD = {"rows": [{"note": "x" * 50}]}

_PRICE_TABLES = [Organization, Source, Commodity, PriceSnapshot, NormalizedPrice]
_CHUNK = 1000


def _make_engine(models):
    engine = create_engine("sqlite://")
    for model in models:
        table = model.__table__
        for column in table.c:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        table.create(bind=engine)
    return engine


def _seed_pairs_bulk(session: Session, count: int, *, day=TODAY, spread_days: int = 1) -> None:
    """Bulk-insert org/source/commodity + ``count`` (snapshot, price)
    pairs with core inserts (fast enough for tens of thousands).

    Snapshots are spread over ``spread_days`` days ending on ``day``;
    locations cycle over 50 names so dedupe keys stay diverse.
    """
    source_id = uuid.uuid4()
    commodity_id = uuid.uuid4()
    session.add(Organization(id=ORG_ID, name="Volume Org"))
    session.add(Source(id=source_id, org_id=ORG_ID, name="test-source", source_type="automated"))
    session.add(Commodity(id=commodity_id, name="Corn"))
    session.commit()

    base = datetime.combine(day, time(0, 0), tzinfo=timezone.utc)
    snapshot_rows: list[dict] = []
    price_rows: list[dict] = []
    for index in range(count):
        snapshot_id = uuid.uuid4()
        captured_at = base - timedelta(days=index % spread_days) + timedelta(seconds=index % 86_000)
        snapshot_rows.append(
            {
                "id": snapshot_id,
                "source_id": source_id,
                "commodity_id": commodity_id,
                "captured_at": captured_at,
                "raw_payload_json": SMALL_PAYLOAD,
            }
        )
        price_rows.append(
            {
                "id": uuid.uuid4(),
                "snapshot_id": snapshot_id,
                "location": f"Testville {index % 50}",
                "commodity_name": "Corn",
                "source_name": "test-source",
                "composite_key": f"vol-{index}",
                "delivery_label": "December 2027",
                "delivery_end": "December 2027",
                "futures_month": "December 2027",
                "futures_price": Decimal("4.50"),
                "basis": Decimal("0.40"),
                "basis_change": Decimal("0.05"),
                "cash_price_bu": Decimal("4.90"),
                "cash_price_mt": Decimal("192.90"),
                "is_canonical": True,
            }
        )
        if len(snapshot_rows) >= _CHUNK:
            session.execute(insert(PriceSnapshot), snapshot_rows)
            session.execute(insert(NormalizedPrice), price_rows)
            snapshot_rows, price_rows = [], []
    if snapshot_rows:
        session.execute(insert(PriceSnapshot), snapshot_rows)
        session.execute(insert(NormalizedPrice), price_rows)
    session.commit()
    session.expunge_all()


class _LoadCounter:
    """Counts ORM instances materialized from the database.

    ``load`` instance events fire once per instance populated from a
    result row, whether or not the caller keeps a reference — so the
    counts measure what the endpoint actually pulled, even for
    handlers that return serialized dicts. Payload transfer is
    counted from the emitted SQL (the Phase A method): any SELECT
    that transfers ``raw_payload_json`` — as a full-entity column or
    as a deferred lazy-load — names ``price_snapshots.raw_payload_json``
    in its column list; the deferred queries never do.
    """

    def __init__(self, engine) -> None:
        self._engine = engine
        self.prices = 0
        self.snapshots = 0
        self.payload_transfers = 0

    def _on_price(self, target, context) -> None:
        self.prices += 1

    def _on_snapshot(self, target, context) -> None:
        self.snapshots += 1

    def _on_sql(self, conn, cursor, statement, parameters, context, executemany) -> None:
        if "SELECT" in statement.upper() and "price_snapshots.raw_payload_json" in statement:
            self.payload_transfers += 1

    def __enter__(self) -> "_LoadCounter":
        event.listen(NormalizedPrice, "load", self._on_price)
        event.listen(PriceSnapshot, "load", self._on_snapshot)
        event.listen(self._engine, "before_cursor_execute", self._on_sql)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(NormalizedPrice, "load", self._on_price)
        event.remove(PriceSnapshot, "load", self._on_snapshot)
        event.remove(self._engine, "before_cursor_execute", self._on_sql)


def _stub_recency_filters(monkeypatch) -> None:
    monkeypatch.setattr(np_route, "_build_market_period_recency_filters", lambda: [])


# ---------------------------------------------------------------------------
# Shared preview query: price list / previews / market search all fetch
# at most limit*3 pairs (normalized_prices._load_preview_payload and
# list_normalized_prices / top_movers share _base_query).
# ---------------------------------------------------------------------------


def test_preview_loader_volume_bounded(monkeypatch) -> None:
    _stub_recency_filters(monkeypatch)
    engine = _make_engine([*_PRICE_TABLES, Company, Location])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 3_000)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = np_route._load_preview_payload(
                    context=CTX,
                    db=session,
                    commodity=None,
                    location=None,
                    source_name=None,
                    region=None,
                    company_id=None,
                    location_id=None,
                    captured_date=TODAY,
                    include_non_canonical=False,
                    sort="captured_desc",
                    limit=10,
                )
            # 3,000 rows in the table, limit=10: the fetch is limit*3.
            assert loads.prices == 30, f"preview loader materialized {loads.prices} prices"
            assert loads.snapshots == 30, f"preview loader materialized {loads.snapshots} snapshots"
            assert loads.payload_transfers == 0, "preview loader pulled raw_payload_json"
            assert len(result) <= 10
            assert len(result) >= 1
        finally:
            session.close()
    finally:
        seed_session.close()


def test_price_list_volume_bounded(monkeypatch) -> None:
    _stub_recency_filters(monkeypatch)
    engine = _make_engine([*_PRICE_TABLES, Company, Location])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 3_000)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = np_route.list_normalized_prices(
                    commodity=None,
                    location=None,
                    source_name=None,
                    region=None,
                    company_id=None,
                    location_id=None,
                    captured_date=TODAY,
                    include_non_canonical=False,
                    limit=10,
                    context=CTX,
                    db=session,
                )
            assert loads.prices == 30, f"price list materialized {loads.prices} prices"
            assert loads.snapshots == 30
            assert loads.payload_transfers == 0
            assert len(result["rows"]) == 10
        finally:
            session.close()
    finally:
        seed_session.close()


def test_top_movers_volume_bounded(monkeypatch) -> None:
    _stub_recency_filters(monkeypatch)
    engine = _make_engine([*_PRICE_TABLES, Company, Location])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 1_000)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = np_route.top_movers(
                    commodity=None,
                    location=None,
                    source_name=None,
                    region=None,
                    company_id=None,
                    location_id=None,
                    captured_date=TODAY,
                    include_non_canonical=False,
                    limit=10,
                    context=CTX,
                    db=session,
                )
            assert loads.prices == 30, f"top-movers materialized {loads.prices} prices"
            assert loads.snapshots == 30
            assert loads.payload_transfers == 0
            assert len(result["rows"]) == 10
        finally:
            session.close()
    finally:
        seed_session.close()


# ---------------------------------------------------------------------------
# Price history: the loader fetch is capped at _HISTORY_FETCH_LIMIT
# no matter how large the price table grows.
# ---------------------------------------------------------------------------


def test_price_history_loader_volume_capped() -> None:
    engine = _make_engine(_PRICE_TABLES)
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 6_000, spread_days=30)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                pairs = price_history_route._load_price_rows(
                    session, commodity="Corn", location_id=None
                )
            cap = price_history_route._HISTORY_FETCH_LIMIT
            assert loads.prices == cap, (
                f"history loader materialized {loads.prices} prices from 6,000 seeded; "
                f"expected the {cap} fetch cap to bind"
            )
            assert loads.snapshots == cap
            assert loads.payload_transfers == 0
            assert len(pairs) <= cap
        finally:
            session.close()
    finally:
        seed_session.close()


# ---------------------------------------------------------------------------
# Best bids: fixed fetch cap of _BEST_BIDS_FETCH_LIMIT (300).
# ---------------------------------------------------------------------------


def test_best_bids_volume_capped() -> None:
    engine = _make_engine([*_PRICE_TABLES, Company, Location])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 1_000)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = best_bids_route.best_bids(commodity=None, limit=30, db=session)
            cap = best_bids_route._BEST_BIDS_FETCH_LIMIT
            assert loads.prices == cap, (
                f"best-bids materialized {loads.prices} prices from 1,000 seeded; "
                f"expected the {cap} fetch cap to bind"
            )
            assert loads.snapshots == cap
            assert loads.payload_transfers == 0
            assert result["bid_count"] >= 1
        finally:
            session.close()
    finally:
        seed_session.close()


# ---------------------------------------------------------------------------
# Saved-search / watchlist previews: the fetch is the limit parameter
# itself (route caps: 300 / 200).
# ---------------------------------------------------------------------------


def test_saved_search_preview_volume_bounded() -> None:
    engine = _make_engine([*_PRICE_TABLES, SavedSearch])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 1_000)
        saved_id = uuid.uuid4()
        seed_session.add(SavedSearch(id=saved_id, org_id=ORG_ID, name="Corn watch", filters_json={}))
        seed_session.commit()
        seed_session.expunge_all()
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = saved_searches_route.preview_saved_search(
                    saved_search_id=saved_id, limit=25, context=CTX, db=session
                )
            assert loads.prices == 25, f"saved-search preview materialized {loads.prices} prices"
            assert loads.snapshots == 25
            assert loads.payload_transfers == 0
            assert len(result["rows"]) == 25
        finally:
            session.close()
    finally:
        seed_session.close()


def test_watchlist_preview_volume_bounded() -> None:
    engine = _make_engine([*_PRICE_TABLES, Watchlist])
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 1_000)
        watchlist_id = uuid.uuid4()
        seed_session.add(Watchlist(id=watchlist_id, org_id=ORG_ID, name="My list", filters_json={}))
        seed_session.commit()
        seed_session.expunge_all()
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                result = watchlists_route.preview_watchlist(
                    watchlist_id=watchlist_id, limit=20, context=CTX, db=session
                )
            assert loads.prices == 20, f"watchlist preview materialized {loads.prices} prices"
            assert loads.snapshots == 20
            assert loads.payload_transfers == 0
            assert len(result["rows"]) <= 20
            assert len(result["rows"]) >= 1
        finally:
            session.close()
    finally:
        seed_session.close()


# ---------------------------------------------------------------------------
# Quotes export loader: the fetch is the limit parameter; the export
# endpoint allows at most 20,000 rows. Seed past the cap and prove
# the cap binds exactly.
# ---------------------------------------------------------------------------


def test_quotes_export_loader_volume_capped() -> None:
    engine = _make_engine(_PRICE_TABLES)
    seed_session = Session(bind=engine)
    try:
        _seed_pairs_bulk(seed_session, 20_500, spread_days=30)
        session = Session(bind=engine)
        try:
            with _LoadCounter(engine) as loads:
                rows = quotes_route._load_quote_rows(
                    session,
                    org_id=ORG_ID,
                    commodity=None,
                    location=None,
                    source_name=None,
                    captured_date=None,
                    limit=20_000,
                )
            assert len(rows) == 20_000, f"quotes loader returned {len(rows)} rows from 20,500 seeded"
            assert loads.prices == 20_000, f"quotes loader materialized {loads.prices} prices"
            assert loads.snapshots == 20_000
            assert loads.payload_transfers == 0
        finally:
            session.close()
    finally:
        seed_session.close()
