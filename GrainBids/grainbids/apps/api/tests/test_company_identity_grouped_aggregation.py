"""Night queue 2026-11-20, item 2 — company-identity aggregation in SQL.

``list_ambiguous_location_company_candidates`` used to load every
``(location_id, company_id, source_name)`` triple for the org from
the largest table in the schema and count in Python (marathon
Phase A documented it as row-unbounded and deferred the fix). The
service now evaluates the identity predicate / canonical label once
per *distinct* source name and lets SQL ``GROUP BY`` do the
counting.

These tests pin equivalence: ``_reference_candidates`` below is a
faithful copy of the pre-fix implementation (the old main loop; the
shared helpers ``_trusted_companies`` and
``_build_ambiguous_location_rows`` are imported unchanged), and the
new implementation must return byte-identical results on every
seeded scenario — ambiguous and unambiguous locations, non-identity
source names, canonical source-label merges, untrusted companies,
cross-org rows, locations with no Location row, a trusted current
company with no price rows, the ``source_id`` filter and the
``limit`` slice. A volume test then seeds 3,000 price rows and
asserts the new implementation still matches the reference while
its counting query is a GROUP BY.

SQLite in-memory; JSONB columns swapped to plain JSON for DDL only
(production runs Postgres), same pattern as the other real-DB tests.
"""

from __future__ import annotations

import sys
import uuid
from collections import defaultdict
from datetime import datetime, time, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import JSON, create_engine, event, insert, select  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.commodity import Commodity  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.market_canonicalization import canonical_source_name  # noqa: E402
from app.services.source_company_identity_diagnostics import (  # noqa: E402
    _build_ambiguous_location_rows,
    _trusted_companies,
    list_ambiguous_location_company_candidates,
)
from app.services.upload_csv import _source_creates_company_identity  # noqa: E402

ORG_ID = uuid.uuid4()
OTHER_ORG_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()

GLG_ID = uuid.uuid4()  # "Great Lakes Grain" — trusted
LAC_ID = uuid.uuid4()  # "London Agricultural Commodities" — trusted
AGG_ID = uuid.uuid4()  # "AgriCharts" — NOT trusted (aggregator name)
LOC_A = uuid.uuid4()  # ambiguous: GLG + LAC rows
LOC_B = uuid.uuid4()  # single company: GLG only
LOC_C = uuid.uuid4()  # current company LAC, price rows only GLG
LOC_D = uuid.uuid4()  # other org's location
LOC_GHOST = uuid.uuid4()  # price rows but no Location row

_MODELS = [Organization, Company, Location, Source, Commodity, PriceSnapshot, NormalizedPrice]


def _reference_candidates(
    db: Session,
    *,
    org_id: uuid.UUID,
    source_id: uuid.UUID | None = None,
    limit: int = 25,
) -> dict[str, object]:
    """The pre-fix implementation, copied verbatim (modulo the name)
    from source_company_identity_diagnostics as of master dd43fac."""
    trusted_company_name_by_id, trusted_company_ids = _trusted_companies(db, org_id=org_id)
    if not trusted_company_ids:
        return {"rows": [], "total_count": 0}

    query = (
        select(NormalizedPrice.location_id, NormalizedPrice.company_id, NormalizedPrice.source_name)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(
            Source.org_id == org_id,
            NormalizedPrice.location_id.is_not(None),
            NormalizedPrice.company_id.is_not(None),
            NormalizedPrice.company_id.in_(trusted_company_ids),
        )
    )
    if source_id is not None:
        query = query.where(Source.id == source_id)

    candidate_rows = db.execute(query).all()
    by_location: dict[uuid.UUID, dict[str, object]] = {}

    for location_id, company_id, source_name in candidate_rows:
        if location_id is None or company_id is None:
            continue
        if not _source_creates_company_identity(source_name):
            continue
        entry = by_location.get(location_id)
        if entry is None:
            entry = {
                "company_counts": defaultdict(int),
                "source_counts": defaultdict(int),
            }
            by_location[location_id] = entry
        entry["company_counts"][company_id] += 1
        source_label = canonical_source_name(source_name) or (source_name or "").strip() or "Unknown"
        entry["source_counts"][source_label] += 1

    if not by_location:
        return {"rows": [], "total_count": 0}

    location_rows = (
        db.execute(
            select(Location).where(
                Location.org_id == org_id,
                Location.id.in_(set(by_location.keys())),
            )
        )
        .scalars()
        .all()
    )

    for location in location_rows:
        entry = by_location.get(location.id)
        if entry is None:
            continue
        current_company_id = location.company_id if location.company_id in trusted_company_ids else None
        entry["location"] = location
        entry["current_company_id"] = current_company_id
        if current_company_id is not None and current_company_id not in entry["company_counts"]:
            entry["company_counts"][current_company_id] = 0

    rows = _build_ambiguous_location_rows(
        by_location=by_location,
        trusted_company_name_by_id=trusted_company_name_by_id,
    )
    return {"rows": rows[:limit], "total_count": len(rows)}


def _make_engine():
    engine = create_engine("sqlite://")
    for model in _MODELS:
        table = model.__table__
        for column in table.c:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        table.create(bind=engine)
    return engine


def _seed_graph(session: Session) -> dict[str, uuid.UUID]:
    """The shared scenario graph. Returns the two source ids."""
    session.add_all(
        [
            Organization(id=ORG_ID, name="Org"),
            Organization(id=OTHER_ORG_ID, name="Other Org"),
            Company(id=GLG_ID, org_id=ORG_ID, name="Great Lakes Grain", canonical_key="great-lakes-grain"),
            Company(id=LAC_ID, org_id=ORG_ID, name="London Agricultural Commodities", canonical_key="london-agricultural-commodities"),
            Company(id=AGG_ID, org_id=ORG_ID, name="AgriCharts", canonical_key="agricharts"),
            Location(id=LOC_A, org_id=ORG_ID, company_id=None, name="Alpha", canonical_key="alpha", region="East"),
            Location(id=LOC_B, org_id=ORG_ID, company_id=GLG_ID, name="Beta", canonical_key="beta", region="East"),
            Location(id=LOC_C, org_id=ORG_ID, company_id=LAC_ID, name="Gamma", canonical_key="gamma", region="West"),
            Location(id=LOC_D, org_id=OTHER_ORG_ID, company_id=None, name="Delta", canonical_key="delta", region="West"),
        ]
    )
    source_one = Source(id=uuid.uuid4(), org_id=ORG_ID, name="feed-one", source_type="automated")
    source_two = Source(id=uuid.uuid4(), org_id=ORG_ID, name="feed-two", source_type="automated")
    other_source = Source(id=uuid.uuid4(), org_id=OTHER_ORG_ID, name="other-feed", source_type="automated")
    commodity = Commodity(id=uuid.uuid4(), name="Corn")
    session.add_all([source_one, source_two, other_source, commodity])
    session.flush()

    captured = datetime.combine(TODAY, time(12, 0), tzinfo=timezone.utc)

    def add_prices(source, specs) -> None:
        """specs: list of (location_id, company_id, source_name, count)."""
        for location_id, company_id, source_name, count in specs:
            for index in range(count):
                snapshot = PriceSnapshot(
                    id=uuid.uuid4(),
                    source_id=source.id,
                    commodity_id=commodity.id,
                    captured_at=captured,
                    raw_payload_json={},
                )
                session.add(snapshot)
                session.flush()
                session.add(
                    NormalizedPrice(
                        id=uuid.uuid4(),
                        snapshot_id=snapshot.id,
                        location_id=location_id,
                        company_id=company_id,
                        location="Wherever",
                        commodity_name="Corn",
                        source_name=source_name,
                        composite_key=f"eq-{uuid.uuid4()}",
                        cash_price_bu=Decimal("4.90"),
                        is_canonical=True,
                    )
                )
        session.flush()

    add_prices(
        source_one,
        [
            (LOC_A, GLG_ID, "GLG", 3),  # canonical-merges with the next line's label
            (LOC_A, GLG_ID, "Great Lakes Grain", 2),
            (LOC_A, LAC_ID, "LAC", 4),
            (LOC_A, GLG_ID, "AgriCharts", 5),  # non-identity source name: excluded
            (LOC_A, AGG_ID, "GLG", 6),  # untrusted company: excluded by the SQL filter
            (LOC_A, LAC_ID, None, 2),  # no source name: excluded
            (LOC_B, GLG_ID, "GLG", 3),  # single-company location: not ambiguous
            (LOC_C, GLG_ID, "GLG", 2),  # current company LAC joins with 0 rows
            (LOC_GHOST, GLG_ID, "GLG", 2),  # no Location row: dropped by the builder
            (LOC_GHOST, LAC_ID, "LAC", 1),
        ],
    )
    add_prices(
        source_two,
        [
            (LOC_A, LAC_ID, "London Agricultural Commodities", 1),
        ],
    )
    add_prices(
        other_source,
        [
            (LOC_D, GLG_ID, "GLG", 3),  # other org: invisible to ORG queries
            (LOC_D, LAC_ID, "LAC", 3),
            (LOC_A, LAC_ID, "LAC", 7),  # other org's source pointing at ORG's location: still excluded
        ],
    )
    session.commit()
    ids = {"source_one": source_one.id, "source_two": source_two.id}
    session.expunge_all()
    return ids


def _assert_equivalent(session: Session, **kwargs) -> dict:
    expected = _reference_candidates(session, org_id=ORG_ID, **kwargs)
    actual = list_ambiguous_location_company_candidates(session, org_id=ORG_ID, **kwargs)
    assert actual == expected
    return actual


def test_grouped_aggregation_matches_reference() -> None:
    engine = _make_engine()
    session = Session(bind=engine)
    try:
        _seed_graph(session)
        result = _assert_equivalent(session)
        # The scenario really is ambiguous in the expected ways.
        assert result["total_count"] == 2
        rows_by_name = {row["location_name"]: row for row in result["rows"]}
        assert set(rows_by_name) == {"Alpha", "Gamma"}
        alpha = rows_by_name["Alpha"]
        assert alpha["candidate_row_count"] == 3 + 2 + 4 + 1
        alpha_companies = {c["company_name"]: c["row_count"] for c in alpha["candidate_companies"]}
        assert alpha_companies == {"Great Lakes Grain": 5, "London Agricultural Commodities": 5}
        alpha_sources = {s["source_name"]: s["row_count"] for s in alpha["top_sources"]}
        assert alpha_sources == {"Great Lakes Grain": 5, "London Agricultural Commodities": 5}
        gamma = rows_by_name["Gamma"]
        assert gamma["current_company_name"] == "London Agricultural Commodities"
        gamma_companies = {c["company_name"]: c["row_count"] for c in gamma["candidate_companies"]}
        assert gamma_companies == {"Great Lakes Grain": 2, "London Agricultural Commodities": 0}
    finally:
        session.close()


def test_grouped_aggregation_matches_reference_with_source_filter() -> None:
    engine = _make_engine()
    session = Session(bind=engine)
    try:
        sources = _seed_graph(session)
        result = _assert_equivalent(session, source_id=sources["source_one"])
        assert result["total_count"] == 2
        _assert_equivalent(session, source_id=sources["source_two"])
    finally:
        session.close()


def test_grouped_aggregation_matches_reference_with_limit() -> None:
    engine = _make_engine()
    session = Session(bind=engine)
    try:
        _seed_graph(session)
        result = _assert_equivalent(session, limit=1)
        assert result["total_count"] == 2
        assert len(result["rows"]) == 1
    finally:
        session.close()


def test_grouped_aggregation_matches_reference_at_volume() -> None:
    """3,000 price rows over a few (location, company, source)
    combinations: outputs still identical, and the new counting is
    visibly a GROUP BY in the emitted SQL."""
    engine = _make_engine()
    session = Session(bind=engine)
    try:
        _seed_graph(session)
        # Bulk volume on top of the scenario graph.
        source_id = session.execute(select(Source.id).where(Source.org_id == ORG_ID).limit(1)).scalar_one()
        commodity_id = session.execute(select(Commodity.id).limit(1)).scalar_one()
        captured = datetime.combine(TODAY, time(12, 0), tzinfo=timezone.utc)
        snapshot_rows, price_rows = [], []
        combos = [
            (LOC_A, GLG_ID, "GLG"),
            (LOC_A, LAC_ID, "LAC"),
            (LOC_B, GLG_ID, "Great Lakes Grain"),
        ]
        for index in range(3_000):
            location_id, company_id, source_name = combos[index % len(combos)]
            snapshot_id = uuid.uuid4()
            snapshot_rows.append(
                {
                    "id": snapshot_id,
                    "source_id": source_id,
                    "commodity_id": commodity_id,
                    "captured_at": captured,
                    "raw_payload_json": {},
                }
            )
            price_rows.append(
                {
                    "id": uuid.uuid4(),
                    "snapshot_id": snapshot_id,
                    "location_id": location_id,
                    "company_id": company_id,
                    "location": "Wherever",
                    "commodity_name": "Corn",
                    "source_name": source_name,
                    "composite_key": f"vol-{index}",
                    "cash_price_bu": Decimal("4.90"),
                    "is_canonical": True,
                }
            )
            if len(snapshot_rows) >= 1000:
                session.execute(insert(PriceSnapshot), snapshot_rows)
                session.execute(insert(NormalizedPrice), price_rows)
                snapshot_rows, price_rows = [], []
        if snapshot_rows:
            session.execute(insert(PriceSnapshot), snapshot_rows)
            session.execute(insert(NormalizedPrice), price_rows)
        session.commit()
        session.expunge_all()

        statements: list[str] = []

        def capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", capture)
        try:
            result = list_ambiguous_location_company_candidates(session, org_id=ORG_ID)
        finally:
            event.remove(engine, "before_cursor_execute", capture)

        expected = _reference_candidates(session, org_id=ORG_ID)
        assert result == expected
        grouped = [s for s in statements if "GROUP BY" in s.upper() and "COUNT(" in s.upper()]
        assert grouped, "expected the counting to happen in a SQL GROUP BY query"
    finally:
        session.close()
