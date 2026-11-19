"""Ingestion-orchestrator coverage tests (Cycle 19).

The scheduled poll path (``app.jobs.poll_sources`` ->
``poll_due_sources`` -> ``list_due_sources`` -> ``run_source_refresh``)
used to filter on the 5-key pilot allowlist, so 88 of the 93 registry
adapters could never be polled on schedule even after being seeded.
These tests assert the orchestrator's due-source set equals the
enabled registry set: every seeded, active, automated, due adapter
is returned, and inactive / file-type / not-yet-due rows are not.

No network is involved: the tests run ``list_due_sources`` (pure
query) against an in-memory SQLite database, and never call a
collector. Fixture source rows are seeded from the registry itself,
so the test stays in sync as adapters are added.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.source_orchestration import list_due_sources, seed_sources_from_registry  # noqa: E402
from app.services.source_registry import ADAPTERS, list_adapters, list_pilot_adapter_keys  # noqa: E402

ORG_ID = uuid.uuid4()


def _session_with_all_adapters_seeded() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["sources"].create(bind=engine)
    session = Session(bind=engine)
    created = seed_sources_from_registry(session, org_id=ORG_ID)
    assert created == len(ADAPTERS)
    return session


def test_due_sources_cover_every_enabled_registry_adapter() -> None:
    session = _session_with_all_adapters_seeded()
    try:
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {row.adapter_key for row in due}
        assert due_keys == {adapter.key for adapter in list_adapters()}
    finally:
        session.close()


def test_due_sources_include_non_pilot_adapters() -> None:
    # Regression test for the Cycle 19 gap: non-pilot adapters (the
    # 88 outside the 5-key pilot set) were previously unreachable
    # from the scheduled poll path.
    session = _session_with_all_adapters_seeded()
    try:
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {row.adapter_key for row in due}
        non_pilot = {key for key in ADAPTERS if key not in set(list_pilot_adapter_keys())}
        assert len(non_pilot) > 0
        assert non_pilot.issubset(due_keys)
    finally:
        session.close()


def test_due_sources_exclude_inactive_file_and_not_yet_due_rows() -> None:
    session = _session_with_all_adapters_seeded()
    try:
        now = datetime.now(timezone.utc)
        rows = session.query(Source).all()
        by_key = {row.adapter_key: row for row in rows}
        pilot_key = list_pilot_adapter_keys()[0]
        non_pilot_key = next(key for key in ADAPTERS if key not in set(list_pilot_adapter_keys()))

        by_key[pilot_key].is_active = False
        by_key[non_pilot_key].source_type = "file"
        another_key = next(
            key
            for key in ADAPTERS
            if key not in {pilot_key, non_pilot_key}
        )
        by_key[another_key].next_poll_at = now + timedelta(hours=1)
        session.commit()

        due = list_due_sources(session, now=now)
        due_keys = {row.adapter_key for row in due}
        assert pilot_key not in due_keys
        assert non_pilot_key not in due_keys
        assert another_key not in due_keys
        assert len(due_keys) == len(ADAPTERS) - 3
    finally:
        session.close()
