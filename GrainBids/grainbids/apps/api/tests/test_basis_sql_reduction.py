"""Real-DB tests for the basis routes' SQL-reduced pair loaders.

Production evidence: the 100k-pair cap on the legacy loader was not
enough — after it shipped, ``GET /api/basis/tracker`` still drove the
512 MB free-tier instance out of memory (Render recorded "Ran out of
memory (used over 512MB)" on 2026-11-19 23:46 EST and restarted it).
The routes now reduce in SQL instead:

* ``_load_latest_pairs_per_group`` — one newest pair per (location,
  commodity, delivery) group via a row_number() window, for /tracker;
* ``_load_history_pairs`` — each (location, commodity) group's oldest
  ``limit`` pairs, for /history;
* ``_count_missing_basis_by_commodity`` — /history's missing count
  over the whole org in SQL, since the service can only count the
  bounded candidate set it is handed.

These tests pin, against a real (SQLite) session:
- equivalence: reduced loaders + the unchanged services produce the
  same ranking / history as the legacy full loader + services;
- the filter-then-latest cases a naive latest-per-location reduction
  would get wrong (a newer snapshot that does not claim the requested
  delivery month or commodity must not shadow the older one that does);
- bounded loading: thousands of stored pairs materialize as
  group-count pairs.

SQLite in-memory; JSONB columns are swapped to plain JSON for DDL
only (same trick as test_basis_pair_loading.py — production runs
Postgres, and the window functions used here run on both).
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import JSON, create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.api.routes.basis as basis_route  # noqa: E402
from app.api.routes.basis import router as basis_router  # noqa: E402
from app.api.routes.market_search import parse_delivery_month  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.commodity import Commodity  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.basis_tracker import build_basis_history, rank_basis  # noqa: E402

ORG_ID = uuid.uuid4()
LOC_A = uuid.uuid4()
LOC_B = uuid.uuid4()
BASE = datetime(2026, 11, 1, tzinfo=timezone.utc)
PAYLOAD = {"rows": [{"note": "x" * 200} for _ in range(20)]}

_TABLES = (
    "organizations",
    "sources",
    "commodities",
    "price_snapshots",
    "normalized_prices",
    "locations",
    "ingestion_runs",
    "source_health_snapshots",
)


def _make_session() -> Session:
    # StaticPool + check_same_thread=False: the route tests hand this
    # session to a TestClient, which serves requests in another thread.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table_name in _TABLES:
        table = Base.metadata.tables[table_name]
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        table.create(bind=engine)
    session = Session(bind=engine)
    session.add(Organization(id=ORG_ID, name="Reduction Test Org"))
    session.flush()
    return session


class _Seed:
    """Small builder: one snapshot per capture time, rows across locations."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.source = Source(
            id=uuid.uuid4(), org_id=ORG_ID, name="test-source", source_type="automated"
        )
        self.commodity = Commodity(id=uuid.uuid4(), name="Corn")
        session.add_all([self.source, self.commodity])
        session.flush()
        self._snapshots: dict[int, PriceSnapshot] = {}

    def snapshot(self, hour: int) -> PriceSnapshot:
        if hour not in self._snapshots:
            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                source_id=self.source.id,
                commodity_id=self.commodity.id,
                captured_at=BASE + timedelta(hours=hour),
                raw_payload_json=PAYLOAD,
            )
            self.session.add(snapshot)
            self.session.flush()
            self._snapshots[hour] = snapshot
        return self._snapshots[hour]

    def price(self, hour: int, **overrides) -> NormalizedPrice:
        values = {
            "id": uuid.uuid4(),
            "snapshot_id": self.snapshot(hour).id,
            "location_id": LOC_A,
            "location": "Alpha",
            "commodity_name": "Corn",
            "source_name": "test-source",
            "futures_month": "Dec 2026",
            "delivery_label": "December 2026",
            "delivery_end": "December 2026",
            "futures_price": Decimal("4.79"),
            "cash_price_bu": Decimal("6.19"),
            "basis": Decimal("1.40"),
            "composite_key": f"key-{uuid.uuid4()}",
        }
        values.update(overrides)
        row = NormalizedPrice(**values)
        self.session.add(row)
        self.session.flush()
        return row


def _ranked_signature(result: dict) -> list[tuple]:
    return [
        (row["location"], row["basis"], row["rank"], row["quote_date"])
        for row in result["ranked"]
    ]


def _unranked_signature(result: dict) -> list[tuple]:
    return [
        (row["location"], row["missing_reason"]) for row in result["unranked"]
    ]


# ---------------------------------------------------------------------------
# Tracker: equivalence with the legacy full load, incl. filter-then-latest
# ---------------------------------------------------------------------------


def _seed_tracker_dataset(session: Session) -> None:
    seed = _Seed(session)
    # Alpha corn Dec: three captures; the newest has the WEAKEST basis
    # (latest wins in the tracker, not strongest).
    seed.price(0, cash_price_bu=Decimal("6.50"), basis=Decimal("1.71"))
    seed.price(10, cash_price_bu=Decimal("6.30"), basis=Decimal("1.51"))
    seed.price(20, cash_price_bu=Decimal("6.19"), basis=Decimal("1.40"))
    # Alpha corn Mar 2027: newest capture overall for Alpha corn, but it
    # does not claim Dec 2026 — a Dec request must fall back to hour 20.
    seed.price(
        30,
        futures_month="Mar 2027",
        delivery_label="March 2027",
        delivery_end="March 2027",
        cash_price_bu=Decimal("9.99"),
        basis=Decimal("5.20"),
    )
    # Alpha wheat Dec: newest Alpha capture overall; a corn request
    # must ignore it and use hour 20.
    seed.price(40, commodity_name="Wheat", cash_price_bu=Decimal("8.00"), basis=Decimal("3.21"))
    # Beta corn Dec: strongest basis, single capture.
    seed.price(
        15,
        location_id=LOC_B,
        location="Beta",
        cash_price_bu=Decimal("6.60"),
        basis=Decimal("1.81"),
    )
    # Beta corn Dec older capture with no futures price: unranked only
    # if it were the latest, which it is not — hour 15 wins for Beta.
    seed.price(
        5,
        location_id=LOC_B,
        location="Beta",
        futures_price=None,
        cash_price_bu=Decimal("6.00"),
        basis=None,
    )
    # Gamma corn Dec: only capture has no futures price -> unranked.
    seed.price(
        12,
        location_id=uuid.uuid4(),
        location="Gamma",
        futures_price=None,
        cash_price_bu=Decimal("6.00"),
        basis=None,
    )
    session.commit()
    session.expunge_all()


def test_tracker_reduced_load_matches_legacy_ranking() -> None:
    session = _make_session()
    try:
        _seed_tracker_dataset(session)
        legacy_pairs = basis_route._load_price_pairs(session, org_id=ORG_ID)
        reduced_pairs, truncated = basis_route._load_latest_pairs_per_group(
            session, org_id=ORG_ID
        )
        assert truncated is False
        # 8 stored rows collapse to one per (location, commodity,
        # delivery) group: Alpha corn Dec, Alpha corn Mar, Alpha wheat
        # Dec, Beta corn Dec, Gamma corn Dec.
        assert len(reduced_pairs) == 5
        assert len(legacy_pairs) == 8

        dec_key = parse_delivery_month("2026-12")
        for kwargs in (
            {"commodity": "corn"},
            {"commodity": "corn", "delivery_month_key": dec_key},
            {"commodity": "wheat"},
            {},
        ):
            legacy = rank_basis(legacy_pairs, **kwargs)
            reduced = rank_basis(reduced_pairs, **kwargs)
            assert _ranked_signature(reduced) == _ranked_signature(legacy)
            assert _unranked_signature(reduced) == _unranked_signature(legacy)
            assert reduced["row_count"] == legacy["row_count"]
            assert reduced["unranked_count"] == legacy["unranked_count"]

        # The headline case in plain terms: Dec corn ranks Beta (1.81)
        # over Alpha's LATEST Dec quote (1.40 at hour 20) — not Alpha's
        # newer Mar quote (5.20) and not its older stronger Dec quotes.
        result = rank_basis(reduced_pairs, commodity="corn", delivery_month_key=dec_key)
        assert [(row["location"], row["basis"]) for row in result["ranked"]] == [
            ("Beta", 1.81),
            ("Alpha", 1.40),
        ]
        assert [row["location"] for row in result["unranked"]] == ["Gamma"]
    finally:
        session.close()


def test_tracker_loader_defers_raw_payload() -> None:
    session = _make_session()
    try:
        seed = _Seed(session)
        seed.price(0)
        seed.price(10)
        session.commit()
        session.expunge_all()
        pairs, _truncated = basis_route._load_latest_pairs_per_group(
            session, org_id=ORG_ID
        )
        assert len(pairs) == 1
        _price, snapshot = pairs[0]
        assert snapshot is not None
        assert "raw_payload_json" not in snapshot.__dict__
        assert snapshot.raw_payload_json == PAYLOAD
    finally:
        session.close()


def test_tracker_loader_materializes_group_count_not_pair_count() -> None:
    """Bounded loading: thousands of pairs -> one pair per group."""
    session = _make_session()
    try:
        seed = _Seed(session)
        # 3 locations x 2 commodities x 500 hourly captures = 3,000 pairs.
        locations = [(LOC_A, "Alpha"), (LOC_B, "Beta"), (uuid.uuid4(), "Gamma")]
        for hour in range(500):
            for location_id, name in locations:
                for commodity_name in ("Corn", "Wheat"):
                    seed.price(
                        hour,
                        location_id=location_id,
                        location=name,
                        commodity_name=commodity_name,
                    )
        session.commit()
        session.expunge_all()

        pairs, truncated = basis_route._load_latest_pairs_per_group(
            session, org_id=ORG_ID
        )
        assert truncated is False
        assert len(pairs) == 6  # 3 locations x 2 commodities x 1 delivery group
        legacy_count = len(basis_route._load_price_pairs(session, org_id=ORG_ID))
        assert legacy_count == 3000
    finally:
        session.close()


def test_tracker_loader_respects_defensive_group_cap(monkeypatch) -> None:
    session = _make_session()
    try:
        seed = _Seed(session)
        for index, name in enumerate(("Alpha", "Beta", "Gamma")):
            seed.price(
                index,
                location_id=uuid.uuid4(),
                location=name,
                commodity_name="Corn",
            )
        session.commit()
        session.expunge_all()
        monkeypatch.setattr(basis_route, "MAX_TRACKER_GROUPS", 2)
        pairs, truncated = basis_route._load_latest_pairs_per_group(
            session, org_id=ORG_ID
        )
        assert truncated is True
        assert len(pairs) == 2
    finally:
        session.close()


# ---------------------------------------------------------------------------
# History: bounded candidates + whole-org missing count
# ---------------------------------------------------------------------------


def _seed_history_dataset(session: Session) -> None:
    seed = _Seed(session)
    # Alpha corn: 12 hourly captures. Hours 0-2 are the oldest; the
    # route's limit in these tests is 3, so only they can be served.
    # Missing-basis rows sit at hours 1 (inside the served window) and
    # 8 and 9 (outside it) — the reported missing_count must cover all
    # three even though hours 8/9 are never loaded as candidates.
    for hour in range(12):
        overrides = {}
        if hour in (1, 8, 9):
            overrides = {"futures_price": None, "basis": None}
        seed.price(hour, cash_price_bu=Decimal("6.00") + Decimal(hour) / Decimal(100), **overrides)
    # Beta corn: two captures, one missing — counted for unfiltered
    # requests, excluded when location_id=Alpha is requested.
    seed.price(0, location_id=LOC_B, location="Beta", futures_price=None, basis=None)
    seed.price(1, location_id=LOC_B, location="Beta")
    # Alpha wheat: one missing row — a different canonical commodity.
    seed.price(0, commodity_name="Wheat", futures_price=None, basis=None)
    session.commit()
    session.expunge_all()


def test_history_reduced_load_matches_legacy_result() -> None:
    session = _make_session()
    try:
        _seed_history_dataset(session)
        legacy_pairs = basis_route._load_price_pairs(session, org_id=ORG_ID)
        reduced_pairs, truncated = basis_route._load_history_pairs(
            session, org_id=ORG_ID, location_id=LOC_A, limit=3
        )
        assert truncated is False
        # 12 Alpha corn rows -> the oldest 3 candidates, plus Alpha's
        # single wheat row (its own group; the service filters it out
        # for a corn request — canonical commodity is a Python-side
        # filter, so the loader's candidate set is a superset).
        assert len(reduced_pairs) == 4

        missing = basis_route._count_missing_basis_by_commodity(
            session, org_id=ORG_ID, location_id=LOC_A
        )
        # Grouped by commodity: Alpha's wheat missing row is separate.
        assert missing == {"corn": 3, "wheat": 1}

        legacy = build_basis_history(
            legacy_pairs, commodity="corn", location_id=LOC_A, limit=3
        )
        reduced = build_basis_history(
            reduced_pairs,
            commodity="corn",
            location_id=LOC_A,
            limit=3,
            missing_count_override=missing["corn"],
        )
        assert [row["quote_date"] for row in reduced["rows"]] == [
            row["quote_date"] for row in legacy["rows"]
        ]
        assert [row["basis"] for row in reduced["rows"]] == [
            row["basis"] for row in legacy["rows"]
        ]
        assert reduced["row_count"] == legacy["row_count"] == 3
        # The legacy service count and the SQL count agree here: the
        # missing rows outside the served window are inside the legacy
        # loader's (uncapped, small-data) load too.
        assert reduced["missing_count"] == legacy["missing_count"] == 3
        assert "3 without a computable basis" in reduced["data_quality"]
    finally:
        session.close()


def test_history_missing_count_covers_rows_beyond_candidate_window() -> None:
    session = _make_session()
    try:
        _seed_history_dataset(session)
        # Unfiltered: corn missing = Alpha 3 + Beta 1; wheat = 1.
        missing = basis_route._count_missing_basis_by_commodity(
            session, org_id=ORG_ID, location_id=None
        )
        assert missing == {"corn": 4, "wheat": 1}
        # With the candidate window at limit=3, the service alone would
        # only see Alpha's hour-1 missing row; the SQL count is what
        # keeps the reported number honest.
        reduced_pairs, _ = basis_route._load_history_pairs(
            session, org_id=ORG_ID, location_id=None, limit=3
        )
        service_only = build_basis_history(reduced_pairs, limit=3)
        assert service_only["missing_count"] < 5
        with_override = build_basis_history(
            reduced_pairs, limit=3, missing_count_override=5
        )
        assert with_override["missing_count"] == 5
    finally:
        session.close()


def test_history_loader_materializes_limit_per_group_not_pair_count() -> None:
    session = _make_session()
    try:
        seed = _Seed(session)
        # One location/commodity group with 2,000 captures, plus a
        # second group with 5.
        for hour in range(2000):
            seed.price(hour)
        for hour in range(5):
            seed.price(hour, location_id=LOC_B, location="Beta")
        session.commit()
        session.expunge_all()

        pairs, truncated = basis_route._load_history_pairs(
            session, org_id=ORG_ID, location_id=None, limit=10
        )
        assert truncated is False
        assert len(pairs) == 15  # Alpha's oldest 10 + all 5 of Beta's
        keys = [price.composite_key for price, _ in pairs]
        assert len(set(keys)) == 15
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Routes end to end on a real session
# ---------------------------------------------------------------------------


def _route_client(session: Session) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(basis_router)

    def override_db():
        yield session

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=ORG_ID, user_email=None, user_role="admin"
    )
    return TestClient(test_app)


def _seed_locations(session: Session) -> None:
    session.add_all(
        [
            Location(
                id=LOC_A, org_id=ORG_ID, name="Alpha", canonical_key="alpha",
                latitude=45.05, longitude=-75.55,
            ),
            Location(
                id=LOC_B, org_id=ORG_ID, name="Beta", canonical_key="beta",
                latitude=45.26, longitude=-75.36,
            ),
        ]
    )
    session.flush()


def test_tracker_route_on_real_session_ranks_latest_per_location() -> None:
    session = _make_session()
    try:
        _seed_locations(session)
        _seed_tracker_dataset(session)
        client = _route_client(session)
        try:
            response = client.get(
                "/api/basis/tracker",
                params={"commodity": "corn", "delivery_month": "2026-12"},
            )
        finally:
            client.app.dependency_overrides.clear()
        assert response.status_code == 200
        body = response.json()
        assert [(row["location"], row["basis"]) for row in body["ranked"]] == [
            ("Beta", 1.81),
            ("Alpha", 1.40),
        ]
        assert [row["location"] for row in body["unranked"]] == ["Gamma"]
        assert body["row_count"] == 2
    finally:
        session.close()


def test_history_route_on_real_session_reports_full_missing_count() -> None:
    session = _make_session()
    try:
        _seed_locations(session)
        _seed_history_dataset(session)
        client = _route_client(session)
        try:
            response = client.get(
                "/api/basis/history",
                params={"commodity": "corn", "location_id": str(LOC_A), "limit": 3},
            )
        finally:
            client.app.dependency_overrides.clear()
        assert response.status_code == 200
        body = response.json()
        assert body["row_count"] == 3
        assert [row["quote_date"] for row in body["rows"]] == [
            "2026-11-01",
            "2026-11-01",
            "2026-11-01",
        ]
        # All three Alpha corn missing rows are counted, including the
        # two outside the served oldest-3 window.
        assert body["missing_count"] == 3
        assert "3 without a computable basis" in body["data_quality"]
    finally:
        session.close()
