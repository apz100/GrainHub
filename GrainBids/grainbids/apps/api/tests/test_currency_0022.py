"""Tests for currency support (migration 0022, approved 2026-11-20).

Covers the four approved decisions from docs/plans/currency-design.md:

1. The source currency is stored per price row (never converted at
   ingest) — migration column, insert-path propagation from collector
   rows through the CSV round trip the orchestrator uses.
2. Display FX is the Bank of Canada daily noon rate with its as-of
   date — the fx_rates service and the best-bids ``convert_to`` toggle.
3. Mixed-currency lists group by currency by default — best-bids
   groups + per-currency limit, basis ranking grouped by currency.
4. The migration backfills only unambiguous source -> currency
   mappings (recorded in the migration docstring); every other
   source's rows stay NULL.

Plus Adam's country-rule amendment (2026-11-20, later the same day):
rows still NULL after the stated-currency backfill take the currency
of their delivery location's country (Canada -> CAD, US -> USD),
resolved per adapter — each adapter's delivery points are in one
country. A stated currency is never overridden, at migration time or
at ingest.
"""

from __future__ import annotations

import importlib.util
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import sqlalchemy as sa  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.operations import Operations  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import JSON, create_engine, select  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.routes.best_bids import router as best_bids_router  # noqa: E402
from app.api.routes.price_history import router as price_history_router  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.commodity import Commodity  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.price_snapshot import PriceSnapshot  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services import fx_rates  # noqa: E402
from app.services.basis_tracker import build_basis_history, rank_basis  # noqa: E402
from app.services.currency_rules import (  # noqa: E402
    ADAPTER_COUNTRIES,
    currency_for_adapter,
    currency_for_country,
)
from app.services.source_orchestration import _to_csv_bytes  # noqa: E402
from app.services.upload_csv import persist_normalized_rows, process_csv_upload  # noqa: E402

API_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = API_ROOT / "alembic" / "versions" / "0022_add_normalized_price_currency.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0022", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Migration 0022: chain, upgrade + backfill, downgrade (real SQLite DB)
# ---------------------------------------------------------------------------


def _pre_0022_schema():
    """The three tables migration 0022 touches, in their pre-0022 shape."""
    engine = create_engine("sqlite://")
    meta = sa.MetaData()
    sources = sa.Table(
        "sources",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("adapter_key", sa.String(100), nullable=True),
    )
    snapshots = sa.Table(
        "price_snapshots",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), nullable=False),
    )
    prices = sa.Table(
        "normalized_prices",
        meta,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("commodity_name", sa.String(120), nullable=False),
        sa.Column("composite_key", sa.String(400), nullable=False),
    )
    meta.create_all(engine)
    return engine, sources, snapshots, prices


def _seed_price(engine, sources, snapshots, prices, *, name, adapter_key) -> str:
    source_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    price_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            sources.insert().values(id=source_id, name=name, adapter_key=adapter_key)
        )
        conn.execute(snapshots.insert().values(id=snapshot_id, source_id=source_id))
        conn.execute(
            prices.insert().values(
                id=price_id,
                snapshot_id=snapshot_id,
                location="Testville",
                commodity_name="Corn",
                composite_key=f"{price_id}|corn",
            )
        )
    return price_id


def _run_migration(module, engine, direction: str) -> None:
    with engine.begin() as conn:
        context = MigrationContext.configure(conn)
        with Operations.context(context):
            getattr(module, direction)()


def test_migration_0022_chain_and_recorded_rule() -> None:
    module = _load_migration()
    assert module.revision == "0022"
    assert module.down_revision == "0021"
    # Anchor examples of the recorded stated-currency backfill rule.
    assert "fac" in module._USD_ADAPTER_KEYS  # Bushel US site
    assert "usda_mirror_jvg" in module._USD_ADAPTER_KEYS
    assert "five_star_coop" in module._USD_ADAPTER_KEYS
    assert "collwest" in module._CAD_ADAPTER_KEYS
    assert "fmn" in module._CAD_ADAPTER_KEYS
    # Families whose collectors record no currency are NOT in the
    # stated lists — they are covered by the country rule instead.
    for country_key in ("hensall", "agricharts", "snobelen", "mapleview", "ag_partners"):
        assert country_key not in module._USD_ADAPTER_KEYS
        assert country_key not in module._CAD_ADAPTER_KEYS
    # Country-rule anchors, each verified in the collector code:
    # Andersons is Andersons CANADA (all-Ontario locations) and
    # Bunge's scraped locations are all in MB / ON.
    for ca_key in ("snobelen", "hensall", "lac", "glg", "wanstead", "ganaraska",
                   "dg_global", "agricharts", "mapleview", "andersons", "bunge"):
        assert ca_key in module._CA_COUNTRY_ADAPTER_KEYS
    for us_key in ("green_plains", "kokomo_grain", "ag_partners", "mulvane_coop"):
        assert us_key in module._US_COUNTRY_ADAPTER_KEYS
    # The migration's inline country lists and the runtime table in
    # app/services/currency_rules.py are two copies of one rule and
    # must never drift apart.
    assert set(module._CA_COUNTRY_ADAPTER_KEYS) == {
        key for key, country in ADAPTER_COUNTRIES.items() if country == "CA"
    }
    assert set(module._US_COUNTRY_ADAPTER_KEYS) == {
        key for key, country in ADAPTER_COUNTRIES.items() if country == "US"
    }
    # Stated and country lists are disjoint: the country step can
    # only ever fill rows the stated step left NULL.
    stated = set(module._USD_ADAPTER_KEYS) | set(module._CAD_ADAPTER_KEYS)
    country = set(module._CA_COUNTRY_ADAPTER_KEYS) | set(module._US_COUNTRY_ADAPTER_KEYS)
    assert stated.isdisjoint(country)


def test_migration_upgrade_backfills_stated_then_country_rule() -> None:
    module = _load_migration()
    engine, sources, snapshots, prices = _pre_0022_schema()
    expected = {
        # adapter_key (name == key, as seeded): Bushel US site -> USD
        _seed_price(engine, sources, snapshots, prices, name="fac", adapter_key="fac"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="skyland_2730", adapter_key="skyland_2730"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="agtegra", adapter_key="agtegra"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="five_star_coop", adapter_key="five_star_coop"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="usda_mirror_fsg", adapter_key="usda_mirror_fsg"): "USD",
        # Collectors hard-coding CAD -> CAD
        _seed_price(engine, sources, snapshots, prices, name="collwest", adapter_key="collwest"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="fmn", adapter_key="fmn"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="mae_mart", adapter_key="mae_mart"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="north_gower", adapter_key="north_gower"): "CAD",
        # Country rule: Ontario Playwright sources state no currency,
        # but their delivery locations are in Canada -> CAD
        _seed_price(engine, sources, snapshots, prices, name="snobelen", adapter_key="snobelen"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="hensall", adapter_key="hensall"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="lac", adapter_key="lac"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="mapleview", adapter_key="mapleview"): "CAD",
        # Andersons Canada + Bunge's MB/ON locations -> CAD
        _seed_price(engine, sources, snapshots, prices, name="andersons", adapter_key="andersons"): "CAD",
        _seed_price(engine, sources, snapshots, prices, name="bunge", adapter_key="bunge"): "CAD",
        # Country rule: the us_dtn / us_agricharts families -> USD
        _seed_price(engine, sources, snapshots, prices, name="green_plains", adapter_key="green_plains"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="kokomo_grain", adapter_key="kokomo_grain"): "USD",
        _seed_price(engine, sources, snapshots, prices, name="ag_partners", adapter_key="ag_partners"): "USD",
        # No recorded country -> stays NULL
        _seed_price(engine, sources, snapshots, prices, name="some_eu_coop", adapter_key="some_eu_coop"): None,
        _seed_price(engine, sources, snapshots, prices, name="Ontario Daily File", adapter_key=None): None,
        # Seeded before adapter_key existed: name fallback still matches
        _seed_price(engine, sources, snapshots, prices, name="fac", adapter_key=None): "USD",
        _seed_price(engine, sources, snapshots, prices, name="snobelen", adapter_key=None): "CAD",
    }

    _run_migration(module, engine, "upgrade")

    columns = {col["name"] for col in sa.inspect(engine).get_columns("normalized_prices")}
    assert "currency" in columns
    reflected = sa.Table("normalized_prices", sa.MetaData(), autoload_with=engine)
    with engine.connect() as conn:
        stored = {
            row.id: row.currency
            for row in conn.execute(sa.select(reflected.c.id, reflected.c.currency)).all()
        }
    assert stored == expected


def test_migration_country_step_never_overrides_a_stated_currency() -> None:
    """A row whose currency is already set (e.g. stated USD by a
    Canadian-location collector) is untouched when the country step
    runs; only NULL rows are filled."""
    module = _load_migration()
    engine, sources, snapshots, prices = _pre_0022_schema()
    stated_id = _seed_price(engine, sources, snapshots, prices, name="snobelen", adapter_key="snobelen")
    _run_migration(module, engine, "upgrade")

    reflected = sa.Table("normalized_prices", sa.MetaData(), autoload_with=engine)
    with engine.begin() as conn:
        # Simulate a stated currency on the row, plus a fresh NULL row
        # from the same source (inserted after the upgrade).
        conn.execute(
            reflected.update().where(reflected.c.id == stated_id).values(currency="USD")
        )
    fresh_id = _seed_price(engine, sources, snapshots, prices, name="snobelen", adapter_key="snobelen")

    with engine.begin() as conn:
        module._backfill(conn, "CAD", module._CA_COUNTRY_ADAPTER_KEYS)

    with engine.connect() as conn:
        stored = {
            row.id: row.currency
            for row in conn.execute(sa.select(reflected.c.id, reflected.c.currency)).all()
        }
    assert stored[stated_id] == "USD"  # stated wins over the country rule
    assert stored[fresh_id] == "CAD"  # NULL row filled by the country rule


def test_migration_downgrade_drops_currency_column() -> None:
    module = _load_migration()
    engine, sources, snapshots, prices = _pre_0022_schema()
    _seed_price(engine, sources, snapshots, prices, name="fac", adapter_key="fac")

    _run_migration(module, engine, "upgrade")
    assert "currency" in {
        col["name"] for col in sa.inspect(engine).get_columns("normalized_prices")
    }

    _run_migration(module, engine, "downgrade")
    assert "currency" not in {
        col["name"] for col in sa.inspect(engine).get_columns("normalized_prices")
    }
    # The price rows themselves survive the downgrade.
    with engine.connect() as conn:
        assert conn.execute(sa.select(sa.func.count()).select_from(prices)).scalar() == 1


# ---------------------------------------------------------------------------
# Ingestion: collector currency is copied into normalized_prices at insert
# ---------------------------------------------------------------------------

_ORG_ID = uuid.uuid4()
_TABLES = (
    "organizations",
    "sources",
    "commodities",
    "companies",
    "locations",
    "price_snapshots",
    "normalized_prices",
    "raw_uploads",
)


def _make_session() -> Session:
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
    session.add(Organization(id=_ORG_ID, name="Currency Test Org"))
    session.flush()
    return session


def _seed_source(
    session: Session, *, name: str = "fac", adapter_key: str | None = ...
) -> tuple[Source, Commodity]:
    source = Source(
        id=uuid.uuid4(),
        org_id=_ORG_ID,
        name=name,
        adapter_key=name if adapter_key is ... else adapter_key,
        source_type="automated",
    )
    commodity = Commodity(id=uuid.uuid4(), name="Corn")
    session.add_all([source, commodity])
    session.flush()
    return source, commodity


def _csv_row(location: str, **overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "location": location,
        "commodity": "Corn",
        "source_name": "FAC",
        "delivery_label": "December 2026",
        "delivery_end": "December 2026",
        "futures_month": "December 2026",
        "futures_price": "5.00",
        "basis": "-0.15",
        "cash_price_bu": "4.85",
        "cash_price_mt": "190.90",
        "currency": "USD",
    }
    row.update(overrides)
    return row


def _stub_historical_changes(monkeypatch) -> None:
    """Skip the day-over-day change computation in persist tests.

    ``apply_historical_changes`` filters prior snapshots with the
    Postgres-only ``extract('isodow', ...)`` (production runs
    Postgres), which SQLite cannot compile — a pre-existing quirk
    unrelated to currency. The currency copy happens in the persist
    row loop itself, before that step, so stubbing it leaves the
    insert path under test intact.
    """
    monkeypatch.setattr(
        "app.services.upload_csv.apply_historical_changes",
        lambda *args, **kwargs: None,
    )


def test_persist_copies_collector_currency_verbatim(monkeypatch) -> None:
    _stub_historical_changes(monkeypatch)
    session = _make_session()
    source, commodity = _seed_source(session)
    headers = list(_csv_row("Arcadia").keys())
    result = persist_normalized_rows(
        session,
        source=source,
        commodity=commodity,
        rows=[
            _csv_row("Arcadia", currency="USD"),
            _csv_row("Schleswig", currency="cad"),  # case normalized
            _csv_row("Manning", currency="US dollars"),  # not a code -> unknown
            _csv_row("Nowhere", currency=""),  # blank -> unknown
        ],
        headers=headers,
    )
    assert result.inserted_rows == 4
    stored = {
        price.location: price.currency
        for price in session.execute(select(NormalizedPrice)).scalars().all()
    }
    assert stored == {
        "Arcadia": "USD",
        "Schleswig": "CAD",
        "Manning": None,
        "Nowhere": None,
    }


def test_persist_without_currency_column_stores_unknown(monkeypatch) -> None:
    _stub_historical_changes(monkeypatch)
    session = _make_session()
    source, commodity = _seed_source(session)
    row = _csv_row("Arcadia")
    del row["currency"]
    result = persist_normalized_rows(
        session,
        source=source,
        commodity=commodity,
        rows=[row],
        headers=list(row.keys()),
    )
    assert result.inserted_rows == 1
    price = session.execute(select(NormalizedPrice)).scalar_one()
    assert price.currency is None


# ---------------------------------------------------------------------------
# Ingestion: Adam's country rule fills rows whose collector states none
# ---------------------------------------------------------------------------


def test_country_currency_mapping() -> None:
    assert currency_for_country("CA") == "CAD"
    assert currency_for_country("Canada") == "CAD"
    assert currency_for_country("us") == "USD"
    assert currency_for_country("United States") == "USD"
    # Only CA / US map — anything else stays unknown.
    assert currency_for_country("MX") is None
    assert currency_for_country("") is None
    assert currency_for_country(None) is None
    assert currency_for_adapter("snobelen") == "CAD"
    assert currency_for_adapter("green_plains") == "USD"
    # Stated-currency families are not in the country table (their
    # stated value is used instead), and neither are file sources.
    assert currency_for_adapter("fac") is None
    assert currency_for_adapter("Ontario Daily File") is None
    assert currency_for_adapter(None) is None


def test_persist_derives_currency_from_location_country(monkeypatch) -> None:
    """Ontario Playwright sources (snobelen-shaped) record no currency
    on their rows; the country rule stores CAD because their delivery
    locations are in Canada. US adapters likewise store USD."""
    _stub_historical_changes(monkeypatch)

    session = _make_session()
    source, commodity = _seed_source(session, name="snobelen")
    row = _csv_row("Brussels")
    del row["currency"]
    result = persist_normalized_rows(
        session, source=source, commodity=commodity, rows=[row], headers=list(row.keys())
    )
    assert result.inserted_rows == 1
    assert session.execute(select(NormalizedPrice)).scalar_one().currency == "CAD"

    session = _make_session()
    source, commodity = _seed_source(session, name="green_plains")
    row = _csv_row("Ord")
    del row["currency"]
    result = persist_normalized_rows(
        session, source=source, commodity=commodity, rows=[row], headers=list(row.keys())
    )
    assert result.inserted_rows == 1
    assert session.execute(select(NormalizedPrice)).scalar_one().currency == "USD"


def test_persist_country_rule_never_overrides_stated_currency(monkeypatch) -> None:
    """A Canadian-location collector that states USD for a specific
    bid keeps USD — the country rule only fills silence."""
    _stub_historical_changes(monkeypatch)
    session = _make_session()
    source, commodity = _seed_source(session, name="snobelen")
    result = persist_normalized_rows(
        session,
        source=source,
        commodity=commodity,
        rows=[_csv_row("Brussels", currency="USD")],
        headers=list(_csv_row("Brussels").keys()),
    )
    assert result.inserted_rows == 1
    assert session.execute(select(NormalizedPrice)).scalar_one().currency == "USD"


def test_persist_file_source_without_currency_stays_unknown(monkeypatch) -> None:
    """File / manual sources have no adapter, hence no recorded
    location country — their rows stay NULL even under the rule."""
    _stub_historical_changes(monkeypatch)
    session = _make_session()
    source, commodity = _seed_source(session, name="Ontario Daily File", adapter_key=None)
    row = _csv_row("Winchester")
    del row["currency"]
    result = persist_normalized_rows(
        session, source=source, commodity=commodity, rows=[row], headers=list(row.keys())
    )
    assert result.inserted_rows == 1
    assert session.execute(select(NormalizedPrice)).scalar_one().currency is None


def test_collector_row_csv_round_trip_stores_currency(monkeypatch) -> None:
    """The orchestrator path: collector dict -> DataFrame-shaped CSV
    bytes -> process_csv_upload -> stored row keeps the currency."""
    _stub_historical_changes(monkeypatch)
    session = _make_session()
    source, commodity = _seed_source(session)
    bushel_row = {
        "company": "FAC",
        "location": "Arcadia",
        "commodity": "Corn",
        "delivery_month": "December 2026",
        "cash_price": 4.85,
        "cash_price_mt": None,
        "basis": -0.15,
        "futures_price": 5.00,
        "futures_month": "December 2026",
        "last_trade": None,
        "change": 0.01,
        "currency": "USD",
        "unit": "$/bu",
        "note": "",
    }
    headers = list(bushel_row.keys())
    payload = _to_csv_bytes([bushel_row], headers)
    upload = process_csv_upload(
        session,
        source_id=source.id,
        commodity_id=commodity.id,
        file_name="fac_2026-11-20.csv",
        content_type="text/csv",
        payload=payload,
    )
    assert upload.inserted_rows == 1
    assert upload.mapping.get("currency") == "currency"
    price = session.execute(select(NormalizedPrice)).scalar_one()
    assert price.currency == "USD"
    # Stored as published — no conversion at ingest.
    assert price.cash_price_bu == Decimal("4.85")


# ---------------------------------------------------------------------------
# FX service: Bank of Canada daily noon rate
# ---------------------------------------------------------------------------


def test_fx_parse_picks_latest_observation() -> None:
    payload = {
        "observations": [
            {"d": "2026-11-18", "FX_USDCAD": {"v": "1.3500"}},
            {"d": "2026-11-19", "FX_USDCAD": {"v": "1.3642"}},
            {"d": "2026-11-17", "FX_USDCAD": {"v": "1.3400"}},
        ]
    }
    rate = fx_rates._parse_boc_payload(payload)
    assert rate is not None
    assert rate.rate == Decimal("1.3642")
    assert rate.as_of == date(2026, 11, 19)
    assert "Bank of Canada" in rate.source


def test_fx_parse_rejects_garbage() -> None:
    assert fx_rates._parse_boc_payload(None) is None
    assert fx_rates._parse_boc_payload({}) is None
    assert fx_rates._parse_boc_payload({"observations": [{"d": "x", "FX_USDCAD": {"v": "y"}}]}) is None


def test_fx_convert_between_cad_and_usd() -> None:
    rate = fx_rates.FxRate(rate=Decimal("1.3642"), as_of=date(2026, 11, 19))
    assert fx_rates.convert_amount(
        Decimal("5.00"), from_currency="USD", to_currency="CAD", fx_rate=rate
    ) == Decimal("6.8210")
    assert fx_rates.convert_amount(
        Decimal("6.8210"), from_currency="CAD", to_currency="USD", fx_rate=rate
    ) == Decimal("5.0000")
    # Same currency: unchanged, no rate needed.
    assert fx_rates.convert_amount(
        Decimal("5.00"), from_currency="CAD", to_currency="CAD", fx_rate=None
    ) == Decimal("5.00")


def test_fx_convert_refuses_without_rate_currency_or_pair() -> None:
    rate = fx_rates.FxRate(rate=Decimal("1.3642"), as_of=date(2026, 11, 19))
    assert fx_rates.convert_amount(Decimal("5"), from_currency="USD", to_currency="CAD", fx_rate=None) is None
    assert fx_rates.convert_amount(Decimal("5"), from_currency=None, to_currency="CAD", fx_rate=rate) is None
    assert fx_rates.convert_amount(Decimal("5"), from_currency="EUR", to_currency="CAD", fx_rate=rate) is None
    assert fx_rates.convert_amount(None, from_currency="USD", to_currency="CAD", fx_rate=rate) is None


# ---------------------------------------------------------------------------
# API fakes (same pattern as test_best_bids.py / test_price_history.py)
# ---------------------------------------------------------------------------


class _FakeResult:
    def __init__(self, *, rows=None) -> None:
        self._rows = list(rows or [])

    def all(self):
        return list(self._rows)

    def scalars(self):
        raise AssertionError("scalars() should not be called by these routes")


class _FakeSession:
    def __init__(self, *, price_rows=None, companies=None, locations=None) -> None:
        self._price_rows = list(price_rows or [])
        self._companies = list(companies or [])
        self._locations = list(locations or [])

    def execute(self, query):
        text = str(query)
        if "FROM companies" in text:
            return _FakeResult(rows=self._companies)
        if "FROM locations" in text:
            return _FakeResult(rows=self._locations)
        return _FakeResult(rows=self._price_rows)


def _make_snapshot(captured_at):
    return PriceSnapshot(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        commodity_id=uuid.uuid4(),
        captured_at=captured_at,
    )


def _make_price(captured_at, **overrides):
    values = {
        "snapshot_id": uuid.uuid4(),
        "location": "Testville",
        "commodity_name": "Corn",
        "cash_price_bu": Decimal("5.00"),
        "cash_price_mt": Decimal("196.85"),
        "basis": Decimal("0.50"),
        "futures_price": Decimal("4.50"),
        "futures_month": "July 2026",
        "delivery_label": "July 2026",
        "source_name": "Great Lakes Grain",
        "composite_key": "testville|corn|july 2026|",
        "company_id": uuid.uuid4(),
        "location_id": uuid.uuid4(),
    }
    values.update(overrides)
    return NormalizedPrice(**values)


def _pair(captured_at, **overrides):
    return (_make_price(captured_at, **overrides), _make_snapshot(captured_at))


def _make_client(router, db):
    test_app = FastAPI()
    test_app.include_router(router)

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app)


_CAPTURED = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
_COMPANY_CAD = uuid.uuid4()
_COMPANY_USD = uuid.uuid4()
_COMPANY_UNKNOWN = uuid.uuid4()


def _mixed_currency_rows():
    return [
        _pair(
            _CAPTURED,
            cash_price_bu=Decimal("6.00"),
            currency="CAD",
            company_id=_COMPANY_CAD,
            source_name="Ontario Co",
            location="Collingwood",
        ),
        _pair(
            _CAPTURED,
            cash_price_bu=Decimal("5.00"),
            currency="USD",
            company_id=_COMPANY_USD,
            source_name="Iowa Co",
            location="Ames",
        ),
        _pair(
            _CAPTURED,
            cash_price_bu=Decimal("7.00"),
            currency=None,
            company_id=_COMPANY_UNKNOWN,
            source_name="Mystery Co",
            location="Nowhere",
        ),
    ]


# ---------------------------------------------------------------------------
# Best bids: grouping by currency, per-currency limit, explicit conversion
# ---------------------------------------------------------------------------


def test_best_bids_groups_mixed_currencies_and_labels_unknown() -> None:
    client = _make_client(best_bids_router, _FakeSession(price_rows=_mixed_currency_rows()))
    response = client.get("/api/best-bids")
    assert response.status_code == 200
    body = response.json()
    assert body["bid_count"] == 3
    assert body["convert_to"] is None
    assert body["fx"] is None
    by_currency = {group["currency"]: group for group in body["groups"]}
    assert set(by_currency) == {"CAD", "USD", None}
    cad_bid = by_currency["CAD"]["bids"][0]
    assert cad_bid["currency"] == "CAD"
    assert cad_bid["currency_unknown"] is False
    assert cad_bid["converted"] is False
    unknown_bid = by_currency[None]["bids"][0]
    assert unknown_bid["currency"] is None
    assert unknown_bid["currency_unknown"] is True
    assert by_currency[None]["currency_unknown"] is True


def test_best_bids_limit_applies_per_currency() -> None:
    client = _make_client(best_bids_router, _FakeSession(price_rows=_mixed_currency_rows()))
    body = client.get("/api/best-bids", params={"limit": 1}).json()
    # One best bid per currency block — a global cap would silently
    # drop whole currencies by comparing bare numbers across them.
    assert body["bid_count"] == 3
    assert {group["currency"] for group in body["groups"]} == {"CAD", "USD", None}


def test_best_bids_convert_to_labels_rate_and_converts(monkeypatch) -> None:
    rate = fx_rates.FxRate(rate=Decimal("1.3642"), as_of=date(2026, 11, 19))
    monkeypatch.setattr(fx_rates, "get_usd_cad_rate", lambda: rate)
    client = _make_client(best_bids_router, _FakeSession(price_rows=_mixed_currency_rows()))
    response = client.get("/api/best-bids", params={"convert_to": "USD"})
    assert response.status_code == 200
    body = response.json()
    assert body["convert_to"] == "USD"
    assert body["fx"]["rate"] == pytest.approx(1.3642)
    assert body["fx"]["as_of"] == "2026-11-19"
    assert "Bank of Canada" in body["fx"]["source"]

    bids = {bid["company_name"]: bid for group in body["groups"] for bid in group["bids"]}
    converted = bids["Ontario Co"]
    assert converted["converted"] is True
    assert converted["currency"] == "USD"
    assert converted["original_currency"] == "CAD"
    assert converted["original_cash_price_bu"] == 6.00
    assert converted["cash_price_bu"] == pytest.approx(6.00 / 1.3642, abs=1e-3)
    # Already-USD and unknown-currency bids are never touched.
    assert bids["Iowa Co"]["converted"] is False
    assert bids["Iowa Co"]["cash_price_bu"] == 5.00
    assert bids["Mystery Co"]["converted"] is False
    assert bids["Mystery Co"]["currency"] is None
    assert bids["Mystery Co"]["cash_price_bu"] == 7.00


def test_best_bids_convert_to_rejects_unsupported_currency() -> None:
    client = _make_client(best_bids_router, _FakeSession(price_rows=_mixed_currency_rows()))
    response = client.get("/api/best-bids", params={"convert_to": "EUR"})
    assert response.status_code == 400


def test_best_bids_convert_to_fails_loudly_without_rate(monkeypatch) -> None:
    monkeypatch.setattr(fx_rates, "get_usd_cad_rate", lambda: None)
    client = _make_client(best_bids_router, _FakeSession(price_rows=_mixed_currency_rows()))
    response = client.get("/api/best-bids", params={"convert_to": "USD"})
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# Price history: points carry their stored currency
# ---------------------------------------------------------------------------


def test_history_points_carry_stored_currency() -> None:
    rows = [
        _pair(_CAPTURED, currency="CAD"),
        _pair(_CAPTURED, currency=None, location="Other Town"),
    ]
    client = _make_client(price_history_router, _FakeSession(price_rows=rows))
    response = client.get("/api/prices/history", params={"commodity": "corn"})
    assert response.status_code == 200
    body = response.json()
    assert body["currencies"] == ["CAD"]
    by_location = {point["location"]: point for point in body["points"]}
    assert by_location["Testville"]["currency"] == "CAD"
    assert by_location["Testville"]["currency_unknown"] is False
    assert by_location["Other Town"]["currency"] is None
    assert by_location["Other Town"]["currency_unknown"] is True


# ---------------------------------------------------------------------------
# Basis service: stored currency flows through; ranking groups by currency
# ---------------------------------------------------------------------------


def test_rank_basis_groups_by_currency_before_comparing() -> None:
    pairs = [
        _pair(_CAPTURED, currency="USD", cash_price_bu=Decimal("7.00"), location="Ames"),
        _pair(_CAPTURED, currency="CAD", cash_price_bu=Decimal("5.10"), location="Collingwood"),
    ]
    ranked = rank_basis(pairs)
    # The USD basis (2.50) is numerically larger than the CAD basis
    # (0.60), but rows are grouped by currency first — never compared
    # across currencies.
    assert [row["location"] for row in ranked["ranked"]] == ["Collingwood", "Ames"]
    assert ranked["ranked"][0]["currency"] == "CAD"
    assert ranked["ranked"][0]["currency_unknown"] is False
    assert ranked["currency"] is None  # mixed: no single currency
    assert ranked["currencies"] == ["CAD", "USD"]
    assert ranked["currency_unknown_count"] == 0


def test_rank_basis_reports_single_currency_when_uniform() -> None:
    pairs = [
        _pair(_CAPTURED, currency="CAD", cash_price_bu=Decimal("5.10"), location="Collingwood"),
        _pair(_CAPTURED, currency="CAD", cash_price_bu=Decimal("5.30"), location="Brussels"),
    ]
    ranked = rank_basis(pairs)
    assert ranked["currency"] == "CAD"
    assert ranked["currencies"] == ["CAD"]
    # Within one currency the order is the plain basis ranking.
    assert [row["location"] for row in ranked["ranked"]] == ["Brussels", "Collingwood"]


def test_basis_history_reports_stored_currency() -> None:
    pairs = [_pair(_CAPTURED, currency="CAD")]
    history = build_basis_history(pairs, commodity="corn")
    assert history["currency"] == "CAD"
    assert history["currencies"] == ["CAD"]
    assert history["currency_unknown_count"] == 0
    assert history["rows"][0]["currency"] == "CAD"
    assert history["rows"][0]["currency_unknown"] is False
