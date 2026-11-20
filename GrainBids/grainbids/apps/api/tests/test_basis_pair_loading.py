"""Regression tests for the basis routes' pair loader bounds.

On 2026-11-19 the production ``GET /api/basis/tracker`` took the
free-tier API instance down three times in a row (HTTP 502, instance
dead afterwards) while every other endpoint stayed healthy. The
loader behind it (``_load_price_pairs``, shared with /history)
fetched **every** stored (price, snapshot) pair for the org with no
limit, including each snapshot's ``raw_payload_json`` — the one
unbounded-size field, a whole day file per snapshot — even though
nothing in the basis paths reads it.

These tests pin the two bounds added in response:
- ``raw_payload_json`` is deferred (not transferred by the query,
  still lazily loadable if anything ever needs it);
- the load is capped at the newest ``MAX_PRICE_PAIRS`` pairs.

SQLite in-memory; the JSONB column is swapped to plain JSON for DDL
only (same trick the repro used — production runs Postgres).
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import JSON, create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.api.routes.basis as basis_route  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.commodity import Commodity  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402

ORG_ID = uuid.uuid4()
PAYLOAD = {"rows": [{"note": "x" * 500} for _ in range(50)]}


def _session_with_pairs(pair_count: int) -> Session:
    Base.metadata.tables["price_snapshots"].c.raw_payload_json.type = JSON()
    engine = create_engine("sqlite://")
    for table in ("organizations", "sources", "commodities", "price_snapshots", "normalized_prices"):
        Base.metadata.tables[table].create(bind=engine)
    session = Session(bind=engine)
    session.add(Organization(id=ORG_ID, name="Basis Test Org"))
    source = Source(id=uuid.uuid4(), org_id=ORG_ID, name="test-source", source_type="automated")
    commodity = Commodity(id=uuid.uuid4(), name="Corn")
    session.add_all([source, commodity])
    session.flush()
    base = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for index in range(pair_count):
        snapshot = PriceSnapshot(
            id=uuid.uuid4(),
            source_id=source.id,
            commodity_id=commodity.id,
            captured_at=base + timedelta(hours=index),
            raw_payload_json=PAYLOAD,
        )
        session.add(snapshot)
        session.flush()
        session.add(
            NormalizedPrice(
                id=uuid.uuid4(),
                snapshot_id=snapshot.id,
                location="Testville",
                commodity_name="Corn",
                source_name="test-source",
                composite_key=f"pair-{index}",
            )
        )
    session.commit()
    session.expunge_all()
    return session


def test_loader_defers_raw_payload_but_keeps_it_reachable() -> None:
    session = _session_with_pairs(3)
    try:
        pairs = basis_route._load_price_pairs(session, org_id=ORG_ID)
        assert len(pairs) == 3
        for _price, snapshot in pairs:
            assert snapshot is not None
            # Deferred: the payload was NOT transferred by the query…
            assert "raw_payload_json" not in snapshot.__dict__
            # …but it still lazy-loads on access (semantics preserved).
            assert snapshot.raw_payload_json == PAYLOAD
    finally:
        session.close()


def test_loader_caps_at_max_pairs_newest_first(monkeypatch) -> None:
    session = _session_with_pairs(5)
    try:
        monkeypatch.setattr(basis_route, "MAX_PRICE_PAIRS", 2)
        pairs = basis_route._load_price_pairs(session, org_id=ORG_ID)
        assert len(pairs) == 2
        keys = [price.composite_key for price, _snapshot in pairs]
        assert keys == ["pair-4", "pair-3"]  # newest captures first
    finally:
        session.close()
