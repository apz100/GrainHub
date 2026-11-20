"""Tests for the ``app.jobs.seed_sources`` one-command seed job.

The job wraps the existing ``seed_sources_from_registry`` service (the
same one behind ``POST /api/sources/seed``) so an operator can register
the registry adapters as ``Source`` rows against a target database
with a single command — no running server or admin headers needed.

Covered:
- org resolution: single-org default, --org-name, --org-id, ambiguous
  and missing orgs are errors that write nothing;
- a real run creates the enabled adapters and a second run is
  idempotent (created=0);
- --dry-run reports the would-be count and writes nothing;
- --scope pilot seeds only the pilot adapter set.

In-memory SQLite only; no network. Table creation is limited to the
two tables the job touches (organizations, sources).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.jobs.seed_sources import run  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.source_registry import ADAPTERS, list_pilot_adapter_keys  # noqa: E402
from app.services.source_toggles import disabled_adapter_keys  # noqa: E402

ENABLED_COUNT = len(ADAPTERS) - len(disabled_adapter_keys(sorted(ADAPTERS)))


def _session(*org_names: str) -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["organizations"].create(bind=engine)
    Base.metadata.tables["sources"].create(bind=engine)
    session = Session(bind=engine)
    for name in org_names:
        session.add(Organization(id=uuid.uuid4(), name=name))
    session.commit()
    return session


def _source_count(session: Session) -> int:
    return session.execute(select(func.count(Source.id))).scalar_one()


def test_single_org_is_the_default_target() -> None:
    session = _session("Only Org")
    try:
        assert run(session) == 0
        assert _source_count(session) == ENABLED_COUNT
    finally:
        session.close()


def test_second_run_is_idempotent() -> None:
    session = _session("Only Org")
    try:
        assert run(session) == 0
        assert run(session) == 0
        assert _source_count(session) == ENABLED_COUNT
    finally:
        session.close()


def test_dry_run_writes_nothing() -> None:
    session = _session("Only Org")
    try:
        assert run(session, dry_run=True) == 0
        assert _source_count(session) == 0
        # A real run afterwards still creates the full set.
        assert run(session) == 0
        assert _source_count(session) == ENABLED_COUNT
    finally:
        session.close()


def test_org_name_and_id_resolution() -> None:
    session = _session("Alpha Org", "Beta Org")
    try:
        beta = session.execute(
            select(Organization).where(Organization.name == "Beta Org")
        ).scalar_one()
        assert run(session, org_name="Beta Org") == 0
        rows = session.execute(select(Source)).scalars().all()
        assert rows and all(row.org_id == beta.id for row in rows)

        assert run(session, org_id=str(beta.id)) == 0  # idempotent re-run
        assert _source_count(session) == ENABLED_COUNT
    finally:
        session.close()


def test_ambiguous_org_is_an_error_and_writes_nothing() -> None:
    session = _session("Alpha Org", "Beta Org")
    try:
        assert run(session) == 2
        assert _source_count(session) == 0
        assert run(session, org_name="Missing Org") == 2
        assert run(session, org_id=str(uuid.uuid4())) == 2
        assert run(session, org_id="not-a-uuid") == 2
        assert _source_count(session) == 0
    finally:
        session.close()


def test_pilot_scope_seeds_only_pilot_adapters() -> None:
    session = _session("Only Org")
    try:
        assert run(session, scope="pilot") == 0
        keys = {
            row.adapter_key
            for row in session.execute(select(Source)).scalars().all()
        }
        expected = {
            key
            for key in list_pilot_adapter_keys()
            if key not in disabled_adapter_keys([key])
        }
        assert keys == expected
        assert 0 < len(keys) < ENABLED_COUNT
    finally:
        session.close()
