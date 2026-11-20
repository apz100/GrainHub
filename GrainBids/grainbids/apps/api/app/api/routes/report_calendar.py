"""USDA report calendar (read-only).

GET /api/research/calendar?year=2026

Returns the verified 2026 USDA/CFTC report schedule with a countdown
(``days_until``) to each release, computed from the current date in
US Eastern time. Only 2026 is supported: the dates below were verified
against the CME Group / NASS / AGSIST 2026 calendars in the research
notes (``~/workspace/research_notes/grain-price-sources-north-america-20261119-0305/report.md``
§5). No dates are invented for any other year — requesting another
year returns 400.

Release times (all ET unless noted):
* WASDE / Grain Stocks / Prospective Plantings / Acreage /
  Small Grains Summary — 12:00 ET, dates listed explicitly.
* Crop Progress — Mondays 4:00 pm ET, first Monday in April through
  the Monday after Thanksgiving (Apr 6 – Nov 30, 2026).
* Export Sales — Thursdays 8:30 am ET.
* Commitments of Traders (CFTC, not USDA) — Fridays 3:30 pm ET.

Ingestion status (Cycle 3 polish): every event carries
``ingestion_status`` — whether that report's latest file has been
ingested, from real ``ResearchReport`` rows — and the response carries
a top-level ``ingestion_status`` summary per report. A report type
with no ingested row is ``not_ingested_yet``, never assumed ingested.
Prospective Plantings / Acreage / Small Grains Summary have no
ingestion collector yet (see ``REPORT_NAME_TO_TYPE``), so they are
always ``not_ingested_yet`` until one is added. The calendar is a
public schedule, so ingestion status is deployment-wide (latest
ingested file in this deployment), not scoped to one org. When no
database is available the status is ``unknown``, not ``not_ingested_yet``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from app.db.session import get_sessionmaker
from app.models.research_report import ResearchReport
from app.services.research import REPORT_TYPES

router = APIRouter(prefix="/api/research", tags=["research"])

ET = ZoneInfo("America/New_York")
SUPPORTED_YEAR = 2026
SOURCE_LABEL = "USDA (NASS / WASDE / FAS) and CFTC — 2026 release schedule"

# Explicit 2026 dates (month, day) for reports released on fixed dates.
WASDE_2026: tuple[tuple[int, int], ...] = (
    (1, 12),
    (2, 10),
    (3, 10),
    (4, 9),
    (5, 12),
    (6, 11),
    (7, 10),
    (8, 12),
    (9, 11),
    (10, 9),
    (11, 10),
    (12, 10),
)
GRAIN_STOCKS_2026: tuple[tuple[int, int], ...] = (
    (1, 12),
    (3, 31),
    (6, 30),
    (9, 30),
)
PROSPECTIVE_PLANTINGS_2026: tuple[tuple[int, int], ...] = ((3, 31),)
ACREAGE_2026: tuple[tuple[int, int], ...] = ((6, 30),)
SMALL_GRAINS_2026: tuple[tuple[int, int], ...] = ((9, 30),)

# Weekly series: (first date, last date, weekday) — weekday is
# Monday=0 .. Sunday=6. Crop Progress runs Apr 6 – Nov 30, 2026.
CROP_PROGRESS_2026 = (date(2026, 4, 6), date(2026, 11, 30), 0)
EXPORT_SALES_2026 = (date(2026, 1, 1), date(2026, 12, 31), 3)
COT_2026 = (date(2026, 1, 2), date(2026, 12, 31), 4)


def _weekly_dates(start: date, end: date, weekday: int) -> list[date]:
    days_ahead = (weekday - start.weekday()) % 7
    current = start + timedelta(days=days_ahead)
    out: list[date] = []
    while current <= end:
        out.append(current)
        current += timedelta(days=7)
    return out


def _event(
    *,
    report: str,
    publisher: str,
    release: datetime,
    frequency: str,
    description: str,
    today: date,
) -> dict[str, Any]:
    days_until = (release.date() - today).days
    return {
        "report": report,
        "publisher": publisher,
        "release_at": release.isoformat(),
        "release_time_et": release.strftime("%I:%M %p ET").lstrip("0"),
        "frequency": frequency,
        "description": description,
        "days_until": days_until,
        "is_past": days_until < 0,
        "is_today": days_until == 0,
    }


def build_calendar(year: int, today: date) -> list[dict[str, Any]]:
    """All 2026 report events, sorted by release time.

    Raises ValueError for any year other than 2026 — no schedule is
    invented for unverified years.
    """
    if year != SUPPORTED_YEAR:
        raise ValueError(
            f"Only the verified {SUPPORTED_YEAR} schedule is available; "
            f"no dates are published for {year}."
        )
    events: list[dict[str, Any]] = []
    for month, day in WASDE_2026:
        events.append(
            _event(
                report="WASDE",
                publisher="USDA World Agricultural Outlook Board",
                release=datetime(year, month, day, 12, 0, tzinfo=ET),
                frequency="Monthly, ~10th",
                description=(
                    "Monthly US + world supply/demand balances: production, "
                    "imports, use, exports and ending stocks."
                ),
                today=today,
            )
        )
    for month, day in GRAIN_STOCKS_2026:
        events.append(
            _event(
                report="Grain Stocks",
                publisher="USDA NASS",
                release=datetime(year, month, day, 12, 0, tzinfo=ET),
                frequency="Quarterly",
                description=(
                    "Physical stocks by state, on-farm vs off-farm. The "
                    "Sep 30 report pins old-crop carryout."
                ),
                today=today,
            )
        )
    for month, day in PROSPECTIVE_PLANTINGS_2026:
        events.append(
            _event(
                report="Prospective Plantings",
                publisher="USDA NASS",
                release=datetime(year, month, day, 12, 0, tzinfo=ET),
                frequency="Annual, late March",
                description="Intended spring acres from the farmer survey.",
                today=today,
            )
        )
    for month, day in ACREAGE_2026:
        events.append(
            _event(
                report="Acreage",
                publisher="USDA NASS",
                release=datetime(year, month, day, 12, 0, tzinfo=ET),
                frequency="Annual, late June",
                description="Actual planted + harvested acres from the June survey.",
                today=today,
            )
        )
    for month, day in SMALL_GRAINS_2026:
        events.append(
            _event(
                report="Small Grains Summary",
                publisher="USDA NASS",
                release=datetime(year, month, day, 12, 0, tzinfo=ET),
                frequency="Annual, late September",
                description="Final wheat/oats/barley/rye production.",
                today=today,
            )
        )
    first, last, weekday = CROP_PROGRESS_2026
    for day in _weekly_dates(first, last, weekday):
        events.append(
            _event(
                report="Crop Progress",
                publisher="USDA NASS",
                release=datetime.combine(day, time(16, 0), tzinfo=ET),
                frequency="Weekly, Mondays 4:00 pm ET (Apr–Nov)",
                description=(
                    "Weekly planting/harvest progress and condition ratings "
                    "by state."
                ),
                today=today,
            )
        )
    first, last, weekday = EXPORT_SALES_2026
    for day in _weekly_dates(first, last, weekday):
        events.append(
            _event(
                report="Export Sales",
                publisher="USDA FAS",
                release=datetime.combine(day, time(8, 30), tzinfo=ET),
                frequency="Weekly, Thursdays 8:30 am ET",
                description=(
                    "Net sales, shipments and outstanding sales by "
                    "commodity and destination."
                ),
                today=today,
            )
        )
    first, last, weekday = COT_2026
    for day in _weekly_dates(first, last, weekday):
        events.append(
            _event(
                report="Commitments of Traders",
                publisher="CFTC",
                release=datetime.combine(day, time(15, 30), tzinfo=ET),
                frequency="Weekly, Fridays 3:30 pm ET",
                description="Fund / managed-money positioning by futures market.",
                today=today,
            )
        )
    events.sort(key=lambda event: event["release_at"])
    return events


def _optional_session():
    """Best-effort DB session for the ingestion-status lookup.

    Yields ``None`` when no database is configured, so the public
    calendar stays available and reports ingestion as ``unknown``
    instead of failing the whole request.
    """
    try:
        session = get_sessionmaker()()
    except Exception:
        yield None
        return
    try:
        yield session
    finally:
        session.close()


# Calendar report name -> ResearchReport.report_type. ``None`` means no
# ingestion collector exists for that report yet (ingest-file accepts
# only REPORT_TYPES), so its status is always "not ingested yet".
REPORT_NAME_TO_TYPE: dict[str, str | None] = {
    "WASDE": "wasde",
    "Grain Stocks": "grain_stocks",
    "Prospective Plantings": None,
    "Acreage": None,
    "Small Grains Summary": None,
    "Crop Progress": "crop_progress",
    "Export Sales": "export_sales",
    "Commitments of Traders": "commitments_of_traders",
}

_NO_COLLECTOR_NOTE = (
    "No ingestion collector exists for this report type yet, so no "
    "file can have been ingested."
)
_NO_DATABASE_NOTE = (
    "Research ingestion data could not be read for this request (no "
    "database available); ingestion status is unknown, not "
    "'not ingested yet'."
)
_MIN_CREATED_AT = datetime.min.replace(tzinfo=timezone.utc)


def _report_sort_key(report: ResearchReport) -> tuple[datetime, str]:
    created = report.created_at
    if created is not None and created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (created or _MIN_CREATED_AT, str(report.report_date or ""))


def build_ingestion_status(
    reports: list[ResearchReport],
) -> dict[str, dict[str, Any]]:
    """Latest ingested row per report type, from real ResearchReport rows.

    A type with no row is ``not_ingested_yet``. The latest row is the
    one with the greatest ``created_at`` (ties broken by
    ``report_date``); nothing is inferred from the schedule itself.
    """
    latest: dict[str, ResearchReport] = {}
    for report in reports:
        current = latest.get(report.report_type)
        if current is None or _report_sort_key(report) > _report_sort_key(current):
            latest[report.report_type] = report
    statuses: dict[str, dict[str, Any]] = {}
    for report_type in REPORT_TYPES:
        row = latest.get(report_type)
        if row is None:
            statuses[report_type] = {
                "status": "not_ingested_yet",
                "latest_report_date": None,
                "vintage": None,
                "source": None,
                "ingested_at": None,
                "note": "No file of this type has been ingested yet.",
            }
        else:
            statuses[report_type] = {
                "status": "ingested",
                "latest_report_date": row.report_date,
                "vintage": row.vintage,
                "source": row.source,
                "ingested_at": row.created_at.isoformat() if row.created_at else None,
                "note": (
                    f"Latest {report_type} file ingested "
                    f"(report date {row.report_date})."
                ),
            }
    return statuses


def ingestion_status_for_report(
    report_name: str,
    statuses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Ingestion status for one calendar report name."""
    report_type = REPORT_NAME_TO_TYPE.get(report_name)
    if report_type is None:
        return {
            "status": "not_ingested_yet",
            "latest_report_date": None,
            "vintage": None,
            "source": None,
            "ingested_at": None,
            "note": _NO_COLLECTOR_NOTE,
        }
    return dict(statuses.get(report_type) or {
        "status": "not_ingested_yet",
        "latest_report_date": None,
        "vintage": None,
        "source": None,
        "ingested_at": None,
        "note": "No file of this type has been ingested yet.",
    })


def _unknown_ingestion_statuses() -> dict[str, dict[str, Any]]:
    return {
        report_type: {
            "status": "unknown",
            "latest_report_date": None,
            "vintage": None,
            "source": None,
            "ingested_at": None,
            "note": _NO_DATABASE_NOTE,
        }
        for report_type in REPORT_TYPES
    }


@router.get("/calendar")
def report_calendar(year: int = Query(SUPPORTED_YEAR), db: Session | None = Depends(_optional_session)):
    try:
        events = build_calendar(year, datetime.now(ET).date())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if db is None:
        statuses = _unknown_ingestion_statuses()
        ingestion_note = _NO_DATABASE_NOTE
    else:
        # Phase A audit (2026-11-20): build_ingestion_status reads
        # only report_type / report_date / vintage / source /
        # created_at — defer the full ``payload`` JSON instead of
        # transferring it for every stored report row, unbounded.
        rows = (
            db.execute(select(ResearchReport).options(defer(ResearchReport.payload)))
            .scalars()
            .all()
        )
        reports = [row for row in rows if isinstance(row, ResearchReport)]
        statuses = build_ingestion_status(reports)
        ingestion_note = (
            "Ingestion status is the latest ingested ResearchReport row "
            "per report type in this deployment; 'not ingested yet' "
            "means no row of that type exists. Prospective Plantings, "
            "Acreage and Small Grains Summary have no ingestion "
            "collector yet, so they are 'not ingested yet' until one "
            "is added."
        )
    for event in events:
        event["ingestion_status"] = ingestion_status_for_report(event["report"], statuses)
    today = datetime.now(ET).date()
    upcoming = [event for event in events if not event["is_past"]]
    return {
        "year": year,
        "schedule": f"{year} USDA report schedule",
        "source": SOURCE_LABEL,
        "timezone": "America/New_York",
        "as_of": today.isoformat(),
        "next_event": upcoming[0] if upcoming else None,
        "upcoming": upcoming[:10],
        "events": events,
        "count": len(events),
        "ingestion_status": {
            report_name: ingestion_status_for_report(report_name, statuses)
            for report_name in REPORT_NAME_TO_TYPE
        },
        "ingestion_status_note": ingestion_note,
    }
