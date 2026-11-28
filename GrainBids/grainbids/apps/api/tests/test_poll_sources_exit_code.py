"""Exit-code contract for app.jobs.poll_sources.run_once.

Changed 2026-11-28 (first scheduled run, 46099501182): the old rule
returned 1 unless EVERY source passed, so a run with 71/101 sources
live still reported FAILURE — and would stay red forever while any
single elevator site is down or changes its page. Per-source outcomes
are already recorded in /api/source-health; the run's exit code now
means "the poll itself ran", and is 1 only when the poll crashes.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.jobs import poll_sources  # noqa: E402


class _DummySession:
    def close(self) -> None:
        pass


@pytest.fixture
def _patched_run(monkeypatch):
    monkeypatch.setattr(poll_sources, "get_sessionmaker", lambda: lambda: _DummySession())
    monkeypatch.setattr(poll_sources, "_default_commodity_id", lambda db: uuid.uuid4())
    return monkeypatch


def _results(*statuses: str):
    return [SimpleNamespace(status=status) for status in statuses]


def test_run_once_succeeds_when_all_sources_complete(_patched_run) -> None:
    _patched_run.setattr(poll_sources, "poll_due_sources", lambda *a, **k: _results("completed", "completed"))
    assert poll_sources.run_once() == 0


def test_run_once_succeeds_when_some_sources_fail(_patched_run) -> None:
    # The behavior change: per-source failures must not fail the run.
    _patched_run.setattr(
        poll_sources,
        "poll_due_sources",
        lambda *a, **k: _results("completed", "failed", "completed", "failed"),
    )
    assert poll_sources.run_once() == 0


def test_run_once_succeeds_when_nothing_is_due(_patched_run) -> None:
    _patched_run.setattr(poll_sources, "poll_due_sources", lambda *a, **k: [])
    assert poll_sources.run_once() == 0


def test_run_once_fails_when_the_poll_itself_crashes(_patched_run) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("database is down")

    _patched_run.setattr(poll_sources, "poll_due_sources", _boom)
    assert poll_sources.run_once() == 1
