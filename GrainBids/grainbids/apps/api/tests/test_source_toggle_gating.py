"""``[sources]`` toggle gating tests (Cycle 20).

Seeding and scheduled polling must honour the ``config.toml``
``[sources]`` toggles, which the FastAPI side previously never read:

- ``seed_sources_from_registry`` skips toggled-off adapters (today
  ``bunge`` and ``mapleview`` plus the 13 DTN adapters, whose
  toggles are off until a Playwright render check verifies them)
  and records them in ``SeedSourcesResult.skipped_disabled``.
- ``list_due_sources`` excludes a toggled-off adapter's ``Source`` row
  even if the row already exists (defence in depth — a row seeded
  before the toggle was turned off must not keep polling).
- A missing toggle entry defaults to enabled, so adapters without a
  config entry keep working.

No network is involved: the tests run against an in-memory SQLite
database and read the real repo ``config.toml`` (``bunge`` /
``mapleview`` off, everything else on). Fixture rows use neutral
synthetic names only.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.services.source_orchestration import list_due_sources, seed_sources_from_registry  # noqa: E402
from app.services.source_registry import ADAPTERS, list_adapters  # noqa: E402
from app.services.source_toggles import disabled_adapter_keys, is_adapter_enabled  # noqa: E402

ORG_ID = uuid.uuid4()
# Derived from the real config.toml toggles (not hardcoded): today
# bunge + mapleview + the 13 DTN adapters (toggles off until a
# Playwright render check verifies them). disabled_adapter_keys
# returns them sorted, matching seed_sources_from_registry.
DISABLED_TODAY = disabled_adapter_keys(sorted(ADAPTERS))


def _session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["sources"].create(bind=engine)
    return Session(bind=engine)


def _seeded_session() -> Session:
    session = _session()
    result = seed_sources_from_registry(session, org_id=ORG_ID)
    assert result.created == len(ADAPTERS) - len(DISABLED_TODAY)
    assert result.skipped_disabled == DISABLED_TODAY
    return session


def _insert_source_row(session: Session, *, adapter_key: str) -> Source:
    row = Source(
        org_id=ORG_ID,
        name=adapter_key,
        adapter_key=adapter_key,
        source_type="automated",
        polling_interval_minutes=15,
        timeout_seconds=90,
        max_retries=2,
        is_active=True,
    )
    session.add(row)
    session.commit()
    return row


def test_seed_skips_toggled_off_adapters_and_records_them() -> None:
    session = _session()
    try:
        result = seed_sources_from_registry(session, org_id=ORG_ID)
        assert result.created == len(ADAPTERS) - len(DISABLED_TODAY)
        assert result.skipped_disabled == DISABLED_TODAY
        keys = {row.adapter_key for row in session.query(Source).all()}
        assert "bunge" not in keys
        assert "mapleview" not in keys
    finally:
        session.close()


def test_seed_includes_toggled_on_adapter() -> None:
    session = _seeded_session()
    try:
        keys = {row.adapter_key for row in session.query(Source).all()}
        assert "agricharts" in keys
        assert keys == {adapter.key for adapter in list_adapters()} - set(DISABLED_TODAY)
    finally:
        session.close()


def test_seed_with_explicit_keys_still_skips_disabled() -> None:
    session = _session()
    try:
        result = seed_sources_from_registry(
            session, org_id=ORG_ID, adapter_keys=["bunge", "agricharts"]
        )
        assert result.created == 1
        assert result.skipped_disabled == ["bunge"]
        keys = {row.adapter_key for row in session.query(Source).all()}
        assert keys == {"agricharts"}
    finally:
        session.close()


def test_due_sources_exclude_preexisting_toggled_off_row() -> None:
    # A bunge row seeded before the toggle was turned off must not
    # keep polling: list_due_sources gates on the toggle, not just on
    # the row existing.
    session = _seeded_session()
    try:
        _insert_source_row(session, adapter_key="bunge")
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {row.adapter_key for row in due}
        assert "bunge" not in due_keys
        assert "mapleview" not in due_keys
        assert "agricharts" in due_keys
    finally:
        session.close()


def test_missing_toggle_defaults_to_enabled() -> None:
    # "testville" has no [sources] entry in config.toml: the helper
    # and the due list must both treat it as enabled.
    assert is_adapter_enabled("testville") is True
    assert disabled_adapter_keys(["testville", "bunge"]) == ["bunge"]
    session = _seeded_session()
    try:
        _insert_source_row(session, adapter_key="testville")
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {row.adapter_key for row in due}
        assert "testville" in due_keys
    finally:
        session.close()


def test_due_sources_exclude_adapter_disabled_after_seeding(monkeypatch: pytest.MonkeyPatch) -> None:
    # Defence in depth: if a toggle flips off after seeding, the row
    # must drop out of the due list without any DB change.
    session = _seeded_session()
    try:
        import app.services.source_orchestration as orchestration

        real_is_enabled = orchestration.is_adapter_enabled

        def _patched(key: str) -> bool:
            if key == "agricharts":
                return False
            return real_is_enabled(key)

        monkeypatch.setattr(orchestration, "is_adapter_enabled", _patched)
        due = list_due_sources(session, now=datetime.now(timezone.utc))
        due_keys = {row.adapter_key for row in due}
        assert "agricharts" not in due_keys
        assert "glg" in due_keys
    finally:
        session.close()
