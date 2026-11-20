"""Phase A (marathon 2026-11-20) — real-database regression tests for
GET list/report endpoints.

The 2026-11-19 production basis-tracker bug survived because the
route tests used fake sessions: the loader pulled every stored
(price, snapshot) pair including each snapshot's ``raw_payload_json``
(a whole day file per snapshot) and an ``isinstance(item, tuple)``
gate silently discarded real SQLAlchemy rows. These tests follow the
``test_basis_pair_loading.py`` pattern instead: real SQLite sessions,
real ORM rows, and assertions on what the query actually transferred
(a deferred column is absent from the instance ``__dict__`` but still
lazy-loads) and on the bounds in the emitted SQL.

Findings pinned here (see docs/marathon/phase-a-notes.md):

* ``normalized_prices`` list / preview / preview-grouped / top-movers,
  ``price_history`` history+seasonal, ``best_bids``, saved-search and
  watchlist previews, and the quotes export loader all selected full
  ``PriceSnapshot`` entities — ``raw_payload_json`` included — while
  only ever reading ``snapshot.captured_at`` in Python.
* ``report_calendar`` loaded EVERY ``ResearchReport`` row including
  the full ``payload`` JSON, unbounded, to compute a latest-per-type
  status that never reads ``payload``.
* ``advisor._latest_price`` loaded every matching ``NormalizedPrice``
  row for an org+commodity (no LIMIT) just to take the first.

The normalized-prices handlers also apply Postgres-only recency
filters (``~`` regex / ``to_date`` / ``initcap``) that SQLite cannot
execute; those are monkeypatched to a no-op in the two handler tests
below so the rest of the handler — including the shared
``_base_query`` loader — runs against the real database. The
freshness-filter SQL itself is unchanged and out of scope here.

SQLite in-memory; JSONB columns are swapped to plain JSON for DDL
only (same trick as the basis tests — production runs Postgres).
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import JSON, create_engine, event, select  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.api.routes.advisor as advisor_route  # noqa: E402
import app.api.routes.alerts as alerts_route  # noqa: E402
import app.api.routes.best_bids as best_bids_route  # noqa: E402
import app.api.routes.elevator_ops as elevator_ops_route  # noqa: E402
import app.api.routes.ingestion as ingestion_route  # noqa: E402
import app.api.routes.normalized_prices as np_route  # noqa: E402
import app.api.routes.price_history as price_history_route  # noqa: E402
import app.api.routes.quotes as quotes_route  # noqa: E402
import app.api.routes.reference as reference_route  # noqa: E402
import app.api.routes.report_calendar as calendar_route  # noqa: E402
import app.api.routes.saved_searches as saved_searches_route  # noqa: E402
import app.api.routes.signals as signals_route  # noqa: E402
import app.api.routes.source_health as source_health_route  # noqa: E402
import app.api.routes.sources as sources_route  # noqa: E402
import app.api.routes.uploads as uploads_route  # noqa: E402
import app.api.routes.watchlists as watchlists_route  # noqa: E402
from app.core.request_context import RequestContext  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.alert_rule import AlertRule  # noqa: E402
from app.models.commodity import Commodity  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.models.company_source_priority import CompanySourcePriority  # noqa: E402
from app.models.contract import GrowerContract  # noqa: E402
from app.models.crm_note import CrmNote  # noqa: E402
from app.models.farm_profile import FarmProfile  # noqa: E402
from app.models.ingestion_run import IngestionRun  # noqa: E402
from app.models.location import Location  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.quote_run import QuoteRun  # noqa: E402
from app.models.raw_upload import RawUpload  # noqa: E402
from app.models.research_report import ResearchReport  # noqa: E402
from app.models.saved_search import SavedSearch  # noqa: E402
from app.models.scale_ticket import ScaleTicket  # noqa: E402
from app.models.signal_forecast import SignalForecast  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.models.source_health_snapshot import SourceHealthSnapshot  # noqa: E402
from app.models.watchlist import Watchlist  # noqa: E402

ORG_ID = uuid.uuid4()
OTHER_ORG_ID = uuid.uuid4()
CTX = RequestContext(org_id=ORG_ID, user_email=None, user_role="admin")
PAYLOAD = {"rows": [{"note": "x" * 500} for _ in range(50)]}
REPORT_PAYLOAD = {"values": [{"note": "y" * 500} for _ in range(50)]}
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()

_PRICE_TABLES = [Organization, Source, Commodity, PriceSnapshot, NormalizedPrice]


def _make_session(models) -> tuple[object, Session]:
    """Real SQLite session with the given model tables created.

    JSONB columns are swapped to plain JSON for DDL only, mirroring
    tests/test_basis_pair_loading.py.
    """
    engine = create_engine("sqlite://")
    for model in models:
        table = model.__table__
        for column in table.c:
            if isinstance(column.type, JSONB):
                column.type = JSON()
        table.create(bind=engine)
    return engine, Session(bind=engine)


def _seed_price_graph(session: Session, pair_count: int = 1, **price_overrides):
    """Org + source + commodity + ``pair_count`` (snapshot, price) pairs.

    Snapshots carry a large ``raw_payload_json`` (a whole day file,
    like production file-ingestion snapshots). Returns the list of
    (snapshot, price) ORM objects; the session is expunged afterwards
    so handlers load fresh instances.
    """
    session.add(Organization(id=ORG_ID, name="Phase A Org"))
    session.add(Organization(id=OTHER_ORG_ID, name="Other Org"))
    source = Source(id=uuid.uuid4(), org_id=ORG_ID, name="test-source", source_type="automated")
    other_source = Source(id=uuid.uuid4(), org_id=OTHER_ORG_ID, name="other-source", source_type="automated")
    commodity = Commodity(id=uuid.uuid4(), name="Corn")
    session.add_all([source, other_source, commodity])
    session.flush()
    pairs = []
    for index in range(pair_count):
        snapshot = PriceSnapshot(
            id=uuid.uuid4(),
            source_id=source.id,
            commodity_id=commodity.id,
            captured_at=datetime.combine(TODAY, time(12, 0), tzinfo=timezone.utc) - timedelta(hours=index),
            raw_payload_json=PAYLOAD,
        )
        session.add(snapshot)
        session.flush()
        values = {
            "id": uuid.uuid4(),
            "snapshot_id": snapshot.id,
            "location": "Testville",
            "commodity_name": "Corn",
            "source_name": "test-source",
            "composite_key": f"pair-{index}",
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
        values.update(price_overrides)
        price = NormalizedPrice(**values)
        session.add(price)
        pairs.append((snapshot, price))
    session.commit()
    session.expunge_all()
    return pairs


def _loaded(session: Session, model) -> list:
    return [obj for obj in session.identity_map.values() if isinstance(obj, model)]


class _SqlCapture:
    """Collect every SQL statement executed on an engine.

    Handler-level tests use this (not the identity map): a handler's
    loaded ORM objects are only weakly referenced by the session, so
    after it returns they may be garbage-collected. The emitted SQL
    is the deterministic evidence of what the query transferred —
    a full-entity select names ``price_snapshots.raw_payload_json``
    in its column list; a deferred one does not.
    """

    def __init__(self, engine) -> None:
        self._engine = engine
        self.statements: list[str] = []

    def _capture(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def __enter__(self) -> "_SqlCapture":
        event.listen(self._engine, "before_cursor_execute", self._capture)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(self._engine, "before_cursor_execute", self._capture)

    def assert_column_not_transferred(self, qualified_column: str) -> None:
        selects = [s for s in self.statements if "SELECT" in s.upper()]
        assert selects, "expected the handler to run at least one SELECT"
        offenders = [s for s in selects if qualified_column in s]
        assert not offenders, (
            f"{qualified_column} was transferred by a query: {offenders[0][:200]}"
        )


def _assert_snapshots_deferred(session: Session) -> None:
    snapshots = _loaded(session, PriceSnapshot)
    assert snapshots, "expected the handler to load PriceSnapshot rows"
    for snapshot in snapshots:
        # Deferred: the payload was NOT transferred by the query…
        assert "raw_payload_json" not in snapshot.__dict__
        # …but it still lazy-loads on access (semantics preserved).
        assert snapshot.raw_payload_json == PAYLOAD


# ---------------------------------------------------------------------------
# Proven finding 1: full PriceSnapshot entities (payload included) loaded
# by price list/report endpoints that only read snapshot.captured_at.
# ---------------------------------------------------------------------------


def test_price_history_loader_defers_snapshot_payload() -> None:
    _engine, session = _make_session(_PRICE_TABLES)
    try:
        _seed_price_graph(session, pair_count=2)
        pairs = price_history_route._load_price_rows(session, commodity="Corn", location_id=None)
        assert len(pairs) == 2
        _assert_snapshots_deferred(session)
        # End to end: the history endpoint serializes real rows.
        result = price_history_route.price_history(
            commodity="Corn", location_id=None, days=90, db=session
        )
        assert result["point_count"] == 1  # same-day pair dedupes to one point
        assert result["points"][0]["cash_price_bu"] == 4.90
    finally:
        session.close()


def test_best_bids_defers_snapshot_payload() -> None:
    engine, session = _make_session(_PRICE_TABLES)
    try:
        _seed_price_graph(session, pair_count=1)
        with _SqlCapture(engine) as sql:
            result = best_bids_route.best_bids(commodity=None, limit=30, db=session)
        assert result["bid_count"] == 1
        assert result["groups"][0]["bids"][0]["cash_price_bu"] == 4.90
        sql.assert_column_not_transferred("price_snapshots.raw_payload_json")
    finally:
        session.close()


def test_saved_search_preview_defers_snapshot_payload() -> None:
    engine, session = _make_session([*_PRICE_TABLES, SavedSearch])
    try:
        _seed_price_graph(session, pair_count=1)
        saved_id = uuid.uuid4()
        session.add(SavedSearch(id=saved_id, org_id=ORG_ID, name="Corn watch", filters_json={}))
        session.commit()
        session.expunge_all()
        with _SqlCapture(engine) as sql:
            result = saved_searches_route.preview_saved_search(
                saved_search_id=saved_id, limit=60, context=CTX, db=session
            )
        assert len(result["rows"]) == 1
        assert result["rows"][0]["cash_price_bu"] == 4.90
        sql.assert_column_not_transferred("price_snapshots.raw_payload_json")
    finally:
        session.close()


def test_watchlist_preview_defers_snapshot_payload() -> None:
    engine, session = _make_session([*_PRICE_TABLES, Watchlist])
    try:
        _seed_price_graph(session, pair_count=1)
        watchlist_id = uuid.uuid4()
        session.add(Watchlist(id=watchlist_id, org_id=ORG_ID, name="My list", filters_json={}))
        session.commit()
        session.expunge_all()
        with _SqlCapture(engine) as sql:
            result = watchlists_route.preview_watchlist(
                watchlist_id=watchlist_id, limit=30, context=CTX, db=session
            )
        assert len(result["rows"]) == 1
        assert result["rows"][0]["cash_price_bu"] == 4.90
        sql.assert_column_not_transferred("price_snapshots.raw_payload_json")
    finally:
        session.close()


def test_quotes_export_loader_defers_snapshot_payload() -> None:
    _engine, session = _make_session(_PRICE_TABLES)
    try:
        _seed_price_graph(session, pair_count=2)
        rows = quotes_route._load_quote_rows(
            session,
            org_id=ORG_ID,
            commodity=None,
            location=None,
            source_name=None,
            captured_date=None,
            limit=10,
        )
        assert len(rows) == 2
        _assert_snapshots_deferred(session)
    finally:
        session.close()


def test_normalized_prices_base_query_defers_snapshot_payload() -> None:
    """The shared loader behind list / preview / preview-grouped /
    top-movers / market-search (and, via _load_preview_payload, the
    market-report and daily-newsletter services)."""
    _engine, session = _make_session(_PRICE_TABLES)
    try:
        _seed_price_graph(session, pair_count=2)
        query = np_route._base_query(CTX, enforce_latest=False)
        rows = session.execute(query.limit(10)).all()
        assert len(rows) == 2
        for price, snapshot in rows:
            assert price.commodity_name == "Corn"
            assert snapshot.captured_at is not None
        _assert_snapshots_deferred(session)
    finally:
        session.close()


def test_normalized_prices_list_handler_real_rows(monkeypatch) -> None:
    # The recency filters are Postgres-only SQL (~ / to_date /
    # initcap); stubbing them out lets the rest of the real handler
    # run on SQLite. The loader bound being pinned lives in
    # _base_query, which is untouched by the stub.
    monkeypatch.setattr(np_route, "_build_market_period_recency_filters", lambda: [])
    engine, session = _make_session([*_PRICE_TABLES, Company, Location])
    try:
        _seed_price_graph(session, pair_count=1)
        with _SqlCapture(engine) as sql:
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
        assert len(result["rows"]) == 1
        assert result["rows"][0]["cash_price_bu"] == 4.90
        assert result["rows"][0]["location"] == "Testville"
        sql.assert_column_not_transferred("price_snapshots.raw_payload_json")
    finally:
        session.close()


def test_normalized_prices_top_movers_handler_real_rows(monkeypatch) -> None:
    monkeypatch.setattr(np_route, "_build_market_period_recency_filters", lambda: [])
    engine, session = _make_session([*_PRICE_TABLES, Company, Location])
    try:
        _seed_price_graph(session, pair_count=1)
        with _SqlCapture(engine) as sql:
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
        assert len(result["rows"]) == 1
        assert result["rows"][0]["basis_change"] == 0.05
        sql.assert_column_not_transferred("price_snapshots.raw_payload_json")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Proven finding 2: report calendar loads every ResearchReport row,
# full payload included, unbounded.
# ---------------------------------------------------------------------------


def test_report_calendar_defers_report_payload() -> None:
    engine, session = _make_session([ResearchReport])
    try:
        older = ResearchReport(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            report_type="wasde",
            commodity="Corn",
            report_date="2026-10-09",
            vintage="2026-10-09",
            source="USDA WAOB",
            payload=REPORT_PAYLOAD,
            created_at=NOW - timedelta(days=30),
        )
        newer = ResearchReport(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            report_type="wasde",
            commodity="Corn",
            report_date="2026-11-10",
            vintage="2026-11-10",
            source="USDA WAOB",
            payload=REPORT_PAYLOAD,
            created_at=NOW - timedelta(days=1),
        )
        session.add_all([older, newer])
        session.commit()
        session.expunge_all()

        with _SqlCapture(engine) as sql:
            result = calendar_route.report_calendar(year=2026, db=session)
        wasde = result["ingestion_status"]["WASDE"]
        assert wasde["status"] == "ingested"
        assert wasde["latest_report_date"] == "2026-11-10"
        # The status computation never reads payload, so the query
        # behind the calendar must not transfer it for every row.
        sql.assert_column_not_transferred("research_reports.payload")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Proven finding 3: advisor _latest_price loads every matching price
# row (no LIMIT) to take the first.
# ---------------------------------------------------------------------------


def test_advisor_latest_price_is_bounded_and_correct() -> None:
    engine, session = _make_session(_PRICE_TABLES)
    try:
        _seed_price_graph(session, pair_count=0)
        source = session.execute(
            select(Source).where(Source.org_id == ORG_ID)
        ).scalar_one()
        commodity = session.execute(select(Commodity)).scalar_one()

        def _add_price(*, hours_ago: int, cash: str, canonical: bool) -> None:
            snapshot = PriceSnapshot(
                id=uuid.uuid4(),
                source_id=source.id,
                commodity_id=commodity.id,
                captured_at=NOW - timedelta(hours=hours_ago),
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
                    composite_key=f"adv-{hours_ago}-{canonical}",
                    cash_price_bu=Decimal(cash),
                    is_canonical=canonical,
                )
            )

        _add_price(hours_ago=48, cash="4.00", canonical=True)
        _add_price(hours_ago=24, cash="5.00", canonical=True)
        _add_price(hours_ago=1, cash="9.99", canonical=False)  # newest but not canonical
        session.commit()
        session.expunge_all()

        statements: list[str] = []

        def _capture(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", _capture)
        try:
            price = advisor_route._latest_price(
                session, org_id=ORG_ID, commodity_name="Corn", location=None
            )
        finally:
            event.remove(engine, "before_cursor_execute", _capture)

        # Canonical rows first, then newest capture: the 5.00 row wins
        # over both the older canonical row and the newer
        # non-canonical row.
        assert price is not None
        assert price.cash_price_bu == Decimal("5.00")
        price_selects = [s for s in statements if "normalized_prices" in s and "SELECT" in s.upper()]
        assert price_selects, "expected a normalized_prices SELECT to be captured"
        assert any("LIMIT" in s.upper() for s in price_selects), (
            "_latest_price must bound its query (LIMIT) instead of "
            "loading every matching price row to take the first"
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Clean endpoints: real-row tests pinning current (correct) behaviour.
# Each of these was read line by line for the Phase A audit; the test
# is the deliverable proving the endpoint works against real ORM rows
# (not fake sessions) within its documented bound.
# ---------------------------------------------------------------------------


def test_normalized_prices_facets_and_summary_real_rows(monkeypatch) -> None:
    monkeypatch.setattr(np_route, "_build_market_period_recency_filters", lambda: [])
    _engine, session = _make_session([*_PRICE_TABLES, Company, Location, AlertRule, Alert])
    try:
        # Facet rows are pruned below settings.user_visible_facet_min_market_count
        # (= 2) markets by design, so seed two markets for the location.
        pairs = _seed_price_graph(session, pair_count=2)
        company_id = uuid.uuid4()
        location_id = uuid.uuid4()
        session.add(Company(id=company_id, org_id=ORG_ID, name="Test Co", canonical_key="testco"))
        session.add(
            Location(id=location_id, org_id=ORG_ID, name="Testville", canonical_key="testville")
        )
        for _snapshot, price in pairs:
            session.add(price)
            price.company_id = company_id
            price.location_id = location_id
        session.commit()
        session.expunge_all()
        facets = np_route.facets(
            captured_date=TODAY, include_non_canonical=False, context=CTX, db=session
        )
        assert "Corn" in facets["commodities"]
        assert "Testville" in facets["locations"]

        summary = np_route.summary(
            commodity=None,
            location=None,
            source_name=None,
            region=None,
            company_id=None,
            location_id=None,
            captured_date=TODAY,
            include_non_canonical=False,
            context=CTX,
            db=session,
        )
        assert summary["row_count"] == 2
        assert summary["average_basis"] == 0.40
        assert summary["active_alert_rules"] == 0
        assert summary["open_alerts"] == 0
    finally:
        session.close()


def test_source_health_real_rows() -> None:
    # SQLite returns naive datetimes for DateTime(timezone=True)
    # columns (Postgres returns aware), so this test exercises the
    # classification paths that do not subtract datetimes in Python:
    # snapshot-only -> live, failed run -> broken. The staleness
    # arithmetic path is Postgres-only in practice and is covered by
    # the existing fake-row tests for classify_source_status.
    _engine, session = _make_session([Organization, Source, IngestionRun, SourceHealthSnapshot])
    try:
        session.add(Organization(id=ORG_ID, name="Phase A Org"))
        live_source = Source(id=uuid.uuid4(), org_id=ORG_ID, name="aaa-live", source_type="automated")
        broken_source = Source(id=uuid.uuid4(), org_id=ORG_ID, name="bbb-broken", source_type="automated")
        session.add_all([live_source, broken_source])
        session.flush()
        session.add(
            SourceHealthSnapshot(
                id=uuid.uuid4(), source_id=live_source.id, captured_at=NOW, status="completed"
            )
        )
        session.add(
            IngestionRun(
                id=uuid.uuid4(),
                source_name="bbb-broken",
                source_identifier="bbb-broken",
                started_at=NOW - timedelta(minutes=5),
                completed_at=NOW - timedelta(minutes=4),
                status="failed",
                error_message="boom",
            )
        )
        session.commit()
        session.expunge_all()

        result = source_health_route.list_source_health(context=CTX, db=session)
        assert result["count"] == 2
        by_name = {row["name"]: row for row in result["sources"]}
        assert by_name["aaa-live"]["status"] == "live"
        assert by_name["bbb-broken"]["status"] == "broken"
        assert by_name["bbb-broken"]["last_error"] == "boom"

        summary = source_health_route.source_health_summary(context=CTX, db=session)
        assert summary["counts"]["live"] == 1
        assert summary["counts"]["broken"] == 1
        assert summary["counts"]["total"] == 2
    finally:
        session.close()


def test_alerts_rules_and_recent_real_rows() -> None:
    _engine, session = _make_session([AlertRule, Alert])
    try:
        rule = AlertRule(
            id=uuid.uuid4(),
            org_id=ORG_ID,
            rule_type="basis",
            threshold_value=0.5,
            comparison_operator=">",
            created_at=NOW - timedelta(days=1),
        )
        session.add(rule)
        session.flush()
        session.add(
            Alert(
                id=uuid.uuid4(),
                alert_rule_id=rule.id,
                triggered_at=NOW - timedelta(hours=2),
                message="basis hit",
                status="new",
            )
        )
        session.commit()
        session.expunge_all()

        rules = alerts_route.list_alert_rules(context=CTX, db=session)
        assert len(rules["rows"]) == 1
        assert rules["rows"][0]["open_alert_count"] == 1
        assert rules["rows"][0]["last_triggered_at"] is not None

        recent = alerts_route.list_recent_alerts(limit=20, open_only=False, context=CTX, db=session)
        assert len(recent["rows"]) == 1
        assert recent["rows"][0]["message"] == "basis hit"
        assert recent["rows"][0]["rule_type"] == "basis"
    finally:
        session.close()


def test_elevator_ops_lists_real_rows_and_limits() -> None:
    _engine, session = _make_session([GrowerContract, ScaleTicket, CrmNote])
    try:
        for index in range(3):
            session.add(
                GrowerContract(
                    id=uuid.uuid4(),
                    org_id=ORG_ID,
                    grower_name=f"Grower {index}",
                    commodity="Corn",
                    quantity_bushels=Decimal("1000"),
                    status="draft",
                    created_at=NOW - timedelta(hours=index),
                )
            )
        session.add(
            ScaleTicket(
                id=uuid.uuid4(),
                org_id=ORG_ID,
                contract_id=None,
                ticket_number="T-1",
                ticket_date=TODAY,
                commodity="Corn",
                bushels=Decimal("800"),
            )
        )
        session.add(
            CrmNote(id=uuid.uuid4(), org_id=ORG_ID, grower_name="Grower 0", note="Called about basis.")
        )
        session.commit()
        session.expunge_all()

        contracts = elevator_ops_route.list_contracts(limit=2, context=CTX, db=session)
        assert len(contracts["rows"]) == 2  # limit honoured against real rows
        tickets = elevator_ops_route.list_scale_tickets(contract_id=None, limit=50, context=CTX, db=session)
        assert len(tickets["rows"]) == 1
        assert tickets["rows"][0]["ticket_number"] == "T-1"
        notes = elevator_ops_route.list_crm_notes(grower_name=None, limit=50, context=CTX, db=session)
        assert len(notes["rows"]) == 1
        assert notes["rows"][0]["note"] == "Called about basis."
    finally:
        session.close()


def test_saved_searches_and_watchlists_lists_real_rows() -> None:
    _engine, session = _make_session([SavedSearch, Watchlist])
    try:
        session.add(
            SavedSearch(
                id=uuid.uuid4(),
                org_id=ORG_ID,
                name="Corn watch",
                filters_json={"commodity_name": "Corn"},
                delivery_months_json=["December 2027"],
                updated_at=NOW,
            )
        )
        session.add(
            Watchlist(id=uuid.uuid4(), org_id=ORG_ID, name="My list", filters_json={}, updated_at=NOW)
        )
        session.commit()
        session.expunge_all()

        searches = saved_searches_route.list_saved_searches(context=CTX, db=session)
        assert [row["name"] for row in searches["rows"]] == ["Corn watch"]
        assert searches["rows"][0]["delivery_months"] == ["December 2027"]

        watchlists = watchlists_route.list_watchlists(context=CTX, db=session)
        assert [row["name"] for row in watchlists["rows"]] == ["My list"]
    finally:
        session.close()


def test_advisor_farm_profiles_real_rows() -> None:
    _engine, session = _make_session([FarmProfile])
    try:
        session.add(
            FarmProfile(
                id=uuid.uuid4(),
                org_id=ORG_ID,
                farm_name="Home Farm",
                crop_mix_json=[{"commodity": "Corn", "acres": 500.0}],
                created_at=NOW,
            )
        )
        session.commit()
        session.expunge_all()

        result = advisor_route.list_farm_profiles(context=CTX, db=session)
        assert len(result["rows"]) == 1
        assert result["rows"][0]["farm_name"] == "Home Farm"
        assert result["rows"][0]["crop_mix"][0]["commodity"] == "Corn"
    finally:
        session.close()


def test_ingestion_runs_endpoint_real_rows() -> None:
    _engine, session = _make_session([Organization, Source, IngestionRun])
    try:
        session.add(Organization(id=ORG_ID, name="Phase A Org"))
        session.add(Source(id=uuid.uuid4(), org_id=ORG_ID, name="test-source", source_type="file"))
        session.add(
            IngestionRun(
                id=uuid.uuid4(),
                source_name="test-source",
                source_identifier="test-source",
                started_at=NOW - timedelta(minutes=10),
                completed_at=NOW - timedelta(minutes=9),
                status="completed",
                raw_row_count=100,
                normalized_row_count=95,
            )
        )
        session.commit()
        session.expunge_all()

        result = ingestion_route.get_ingestion_runs(limit=25, _context=CTX, db=session)
        assert len(result["rows"]) == 1
        assert result["rows"][0]["source_name"] == "test-source"
        assert result["rows"][0]["normalized_row_count"] == 95
    finally:
        session.close()


def test_uploads_reference_signals_quotes_lists_real_rows() -> None:
    _engine, session = _make_session(
        [RawUpload, Commodity, Source, Organization, SignalForecast, QuoteRun]
    )
    try:
        session.add(Organization(id=ORG_ID, name="Phase A Org"))
        source_id = uuid.uuid4()
        session.add(Source(id=source_id, org_id=ORG_ID, name="test-source", source_type="file"))
        session.add(Commodity(id=uuid.uuid4(), name="Corn"))
        session.add(
            RawUpload(
                id=uuid.uuid4(),
                source_id=source_id,
                file_name="bids.csv",
                raw_headers=["location", "bid"],
                column_mapping={"location": "location"},
                uploaded_at=NOW,
            )
        )
        session.add(
            SignalForecast(
                id=uuid.uuid4(),
                composite_key="corn|testville",
                horizon_minutes=60,
                basis_forecast=0.42,
                generated_at=NOW,
            )
        )
        session.add(
            QuoteRun(
                id=uuid.uuid4(),
                org_id=ORG_ID,
                assumptions_json={"trucking_cost_bu": 0.1},
                output_file_url="/api/quotes/runs/quotes_x.csv",
                generated_at=NOW,
            )
        )
        session.commit()
        session.expunge_all()

        uploads = uploads_route.list_uploads(source_id=None, limit=25, db=session)
        assert [row["file_name"] for row in uploads["rows"]] == ["bids.csv"]

        commodities = reference_route.list_commodities(limit=200, db=session)
        assert [row["name"] for row in commodities["rows"]] == ["Corn"]

        forecasts = signals_route.list_forecasts(
            composite_key=None, horizon_minutes=None, limit=200, db=session
        )
        assert len(forecasts["rows"]) == 1
        assert forecasts["rows"][0]["basis_forecast"] == 0.42
        # signals_health subtracts a tz-aware now from the stored
        # generated_at in Python; SQLite returns naive datetimes
        # (Postgres returns aware), so that handler cannot execute
        # against SQLite — noted in the Phase A audit, not a prod bug.

        sources = reference_route.list_sources(org_id=None, active_only=True, limit=200, db=session)
        assert [row["name"] for row in sources["rows"]] == ["test-source"]

        runs = quotes_route.list_quote_runs(limit=50, context=CTX, db=session)
        assert len(runs["rows"]) == 1
        assert runs["rows"][0]["status"] == "completed"
    finally:
        session.close()


def test_sources_priority_candidates_and_coverage_real_rows() -> None:
    _engine, session = _make_session([*_PRICE_TABLES, Company, CompanySourcePriority])
    try:
        company_id = uuid.uuid4()
        pairs = _seed_price_graph(session, pair_count=2)
        session.add(Company(id=company_id, org_id=ORG_ID, name="Test Co", canonical_key="testco"))
        # Point the seeded prices at the company (real FK-style link).
        for _snapshot, price in pairs:
            session.add(price)
            price.company_id = company_id
        session.commit()
        session.expunge_all()

        candidates = sources_route.get_company_source_priority_candidates(
            company_id=company_id, context=CTX, db=session
        )
        assert len(candidates["rows"]) == 1
        assert candidates["rows"][0]["row_count"] == 2
        assert candidates["rows"][0]["canonical_count"] == 2

        coverage = sources_route.canonical_coverage(days=7, context=CTX, db=session)
        assert len(coverage["rows"]) == 1
        assert coverage["rows"][0]["row_count"] == 2
        assert coverage["rows"][0]["winner_rate"] == 1.0

        priority = sources_route.get_company_source_priority(
            company_id=company_id, context=CTX, db=session
        )
        assert priority["rows"] == []
    finally:
        session.close()
