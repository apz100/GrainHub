"""Daily newsletter generator (Cycle 2).

Preview-only: builds a daily newsletter *draft* from real data that
already exists in the database — today's top normalized prices, USDA
research rows that have actually been ingested, and upcoming report
dates that are actually on file.

Delivery stays OFF: this module never sends email. There is no SMTP
call and no send endpoint anywhere in this file. The draft carries
``delivery_enabled: False`` / ``sent: False`` so a caller can never
mistake a preview for a send.

Honesty rules (same as the weekly market report):
- Every section with no data renders an explicit empty state.
- No number is ever invented. Basis "movers" are ranked from today's
  snapshot only — no prior-day basis is stored, so no day-over-day
  move is claimed.
- There is no report-calendar table in the codebase yet (that is a
  separate Cycle 2 workstream). The upcoming-reports section is fed
  by the verified 2026 USDA/CFTC release schedule in
  :mod:`app.api.routes.report_calendar` (``build_calendar``, 2026
  only, sourced from CME / NASS / AGSIST 2026 calendars). For any
  year without a verified schedule it renders an explicit empty
  state instead of guessed release dates. Callers may also pass
  ``upcoming_events`` explicitly.

Reuse: the top-bids section is built with ``compile_market_report``
and the USDA section is attached with ``append_research_section``
from :mod:`app.services.market_report`. Neither signature is changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import escape
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext
from app.models.research_report import ResearchReport
from app.services.market_report import (
    REPORT_COMMODITIES,
    append_research_section,
    compile_market_report,
)
from app.api.routes.normalized_prices import _load_preview_payload


# Delivery is OFF for the daily newsletter: drafts only, never sent.
DELIVERY_ENABLED = False

EMPTY_TOP_BIDS = "No current bids were available for {date}."
EMPTY_BASIS = "No basis data was available for {date} — no basis movers to show."
EMPTY_USDA = "No USDA report dated {date} is on file."
EMPTY_UPCOMING = (
    "No upcoming report dates are on file for the next 14 days — the "
    "verified calendar covers 2026 only, so no dates are shown rather "
    "than guessed."
)

# Upcoming-report window: only the next 14 days, so the weekly
# Crop Progress / Export Sales series does not flood the digest.
UPCOMING_WINDOW_DAYS = 14


@dataclass(frozen=True)
class DailyNewsletterDraft:
    issue_key: str
    subject: str
    draft_date: date
    generated_at: datetime
    region: str
    sections: tuple[dict[str, object], ...]
    text: str
    html: str

    def as_dict(self) -> dict[str, object]:
        return {
            "issue_key": self.issue_key,
            "subject": self.subject,
            "date": self.draft_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "region": self.region,
            "delivery": {
                "enabled": False,
                "sent": False,
                "note": (
                    "Preview only — delivery is OFF for the daily newsletter. "
                    "This draft was not sent to any subscriber and no delivery "
                    "row was created. Dedup, when delivery is ever enabled, is "
                    "subscriber_id + issue_key (see MarketReportDelivery)."
                ),
            },
            "dedup_key_format": "daily-YYYY-MM-DD (subscriber_id + issue_key)",
            "sections": list(self.sections),
            "text": self.text,
            "html": self.html,
        }


def parse_draft_date(value: str | None) -> date:
    """Parse a ``YYYY-MM-DD`` draft date; ``None`` means today (UTC).

    Raises ``ValueError`` for anything else — the route turns that
    into a 400 rather than silently drafting for the wrong day.
    """
    if value is None or not str(value).strip():
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"date must be YYYY-MM-DD, got {value!r}") from exc


def daily_issue_key(draft_date: date) -> str:
    """Dedup issue key for a daily draft: ``daily-YYYY-MM-DD``."""
    return f"daily-{draft_date.isoformat()}"


def delivery_dedup_key(subscriber_id: uuid.UUID, issue_key: str) -> str:
    """Dedup key for a (future) delivery: ``subscriber_id:issue_key``.

    Mirrors the ``uq_market_report_delivery_subscriber_issue`` unique
    constraint on ``MarketReportDelivery`` (subscriber + issue_key):
    one delivery row per subscriber per issue, so a re-run skips
    instead of re-sending. No delivery row is created by a preview.
    """
    return f"{subscriber_id}:{issue_key}"


def generate_daily_draft(
    db: Session | None,
    draft_date: date | str | None,
    *,
    org_id: uuid.UUID | None = None,
    commodity: str | None = None,
    location: str | None = None,
    region: str = "Eastern Ontario",
    price_rows: dict[str, list[dict[str, object]]] | None = None,
    research_rows: list[dict[str, object]] | None = None,
    upcoming_events: list[dict[str, object]] | None = None,
    generated_at: datetime | None = None,
) -> DailyNewsletterDraft:
    """Build a daily newsletter draft from real data only.

    ``price_rows`` / ``research_rows`` / ``upcoming_events`` are
    injection points for tests; when omitted they are loaded from
    ``db`` (prices need ``org_id`` — without one the price section
    honestly reports no data rather than guessing an org).
    """
    resolved_date = draft_date if isinstance(draft_date, date) else parse_draft_date(draft_date)
    generated_at = generated_at or datetime.now(timezone.utc)
    commodities = _resolve_commodities(commodity)

    if price_rows is None:
        rows_by_commodity = _load_price_rows(
            db, org_id=org_id, commodities=commodities, location=location, region=region
        )
    else:
        rows_by_commodity = {
            name: _filter_rows(price_rows.get(name, []), location=location)
            for name in commodities
        }

    report = compile_market_report(
        rows_by_commodity, generated_at=generated_at, region=region
    )

    if research_rows is None:
        research_all = _load_research_rows(db, org_id=org_id)
    else:
        research_all = list(research_rows)
    if commodity:
        wanted = commodity.strip().casefold()
        research_all = [
            row for row in research_all
            if str(row.get("commodity") or "").strip().casefold() == wanted
        ]
    todays_research = [row for row in research_all if _is_dated(row, resolved_date)]
    # Reuse: no-op when there is nothing for today, appends a USDA
    # research section (source + vintage labelled) when there is.
    report = append_research_section(report, todays_research)

    if upcoming_events is None:
        upcoming = _load_upcoming_events(db, after=resolved_date)
    else:
        upcoming = _normalise_upcoming_events(upcoming_events, after=resolved_date)

    sections = (
        _top_bids_section(report, commodities, resolved_date),
        _basis_movers_section(rows_by_commodity, resolved_date),
        _usda_today_section(todays_research, len(research_all), resolved_date),
        _upcoming_section(upcoming, resolved_date),
    )
    subject = f"GrainHub Daily Newsletter — {resolved_date:%B} {resolved_date.day}, {resolved_date:%Y}"
    text = _render_text(subject, resolved_date, region, sections)
    html = _render_html(subject, resolved_date, region, sections)
    return DailyNewsletterDraft(
        issue_key=daily_issue_key(resolved_date),
        subject=subject,
        draft_date=resolved_date,
        generated_at=generated_at,
        region=region,
        sections=sections,
        text=text,
        html=html,
    )


# ---------------------------------------------------------------------------
# Loaders (real DB; each fails soft to "no data" for a preview draft)
# ---------------------------------------------------------------------------

def _load_price_rows(
    db: Session | None,
    *,
    org_id: uuid.UUID | None,
    commodities: list[str],
    location: str | None,
    region: str,
) -> dict[str, list[dict[str, object]]]:
    empty = {name: [] for name in commodities}
    if db is None or org_id is None:
        return empty
    try:
        context = RequestContext(org_id=org_id, user_email=None, user_role="admin")
        return {
            name: _load_preview_payload(
                context=context,
                db=db,
                commodity=name,
                location=location,
                source_name=None,
                region=region,
                company_id=None,
                location_id=None,
                captured_date=None,
                include_non_canonical=False,
                sort="cash_bu_desc",
                limit=500,
            )
            for name in commodities
        }
    except Exception:
        # A preview draft must never crash on a partial source: the
        # section honestly reports no data instead.
        return empty


def _load_research_rows(
    db: Session | None, *, org_id: uuid.UUID | None
) -> list[dict[str, object]]:
    if db is None:
        return []
    try:
        query = select(ResearchReport).order_by(ResearchReport.report_date.desc()).limit(10)
        if org_id is not None:
            query = query.where(ResearchReport.org_id == org_id)
        rows = db.execute(query).scalars().all()
        return [
            {
                "report_type": row.report_type,
                "commodity": row.commodity,
                "report_date": row.report_date,
                "vintage": row.vintage,
                "source": row.source,
                "payload": row.payload,
            }
            for row in rows
        ]
    except Exception:
        return []


def _load_upcoming_events(db: Session | None, *, after: date) -> list[dict[str, object]]:
    """Upcoming report dates from the verified report calendar.

    Uses ``build_calendar`` from :mod:`app.api.routes.report_calendar`
    — the verified 2026 USDA/CFTC release schedule (WASDE, Grain
    Stocks, Crop Progress, Export Sales, Commitments of Traders).
    Only events in the next 14 days are shown. For any year without
    a verified schedule (``build_calendar`` raises ``ValueError``)
    this returns [] and the section renders its explicit empty
    state rather than guessed dates. ``db`` is unused — the calendar
    is a sourced static schedule, not a table — and is kept in the
    signature so the loader matches the other loaders.
    """
    try:
        from app.api.routes.report_calendar import build_calendar

        events = build_calendar(after.year, after)
    except (ImportError, ValueError):
        return []
    upcoming = [
        {
            "name": event["report"],
            "report_date": str(event["release_at"])[:10],
            "source": event["publisher"],
            "release_time_et": event["release_time_et"],
            "days_until": event["days_until"],
        }
        for event in events
        if 0 <= int(event["days_until"]) <= UPCOMING_WINDOW_DAYS
    ]
    return _normalise_upcoming_events(upcoming, after=after)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _top_bids_section(report, commodities: list[str], draft_date: date) -> dict[str, object]:
    by_name = {str(section.get("commodity") or ""): section for section in report.sections}
    by_commodity = []
    any_bids = False
    for name in commodities:
        section = by_name.get(name)
        top_bids = list(section.get("top_bids") or []) if section else []
        if top_bids:
            any_bids = True
        by_commodity.append(
            {
                "commodity": name,
                "market_count": section.get("market_count", 0) if section else 0,
                "top_bids": top_bids,
                "median_cash_price_bu": section.get("median_cash_price_bu") if section else None,
                "empty": not top_bids,
                "empty_reason": None
                if top_bids
                else EMPTY_TOP_BIDS.format(date=draft_date.isoformat()),
            }
        )
    return {
        "kind": "top_bids",
        "title": "Top bids",
        "commodities": by_commodity,
        "empty": not any_bids,
        "empty_reason": None
        if any_bids
        else EMPTY_TOP_BIDS.format(date=draft_date.isoformat()),
    }


def _basis_movers_section(
    rows_by_commodity: dict[str, list[dict[str, object]]], draft_date: date
) -> dict[str, object]:
    with_basis = []
    for name, rows in rows_by_commodity.items():
        for row in rows:
            value = _as_number(row.get("basis"))
            if value is not None:
                with_basis.append((value, name, dict(row)))
    if not with_basis:
        return {
            "kind": "basis_movers",
            "title": "Basis movers",
            "items": [],
            "empty": True,
            "empty_reason": EMPTY_BASIS.format(date=draft_date.isoformat()),
            "note": (
                "Ranked from today's snapshot only — no prior-day basis is "
                "stored, so this is not a day-over-day move."
            ),
        }
    with_basis.sort(key=lambda item: item[0])
    items: list[dict[str, object]] = []
    weakest_value, weakest_name, weakest_row = with_basis[0]
    strongest_value, strongest_name, strongest_row = with_basis[-1]
    if len(with_basis) == 1:
        items.append({"label": "Only basis on file", "commodity": weakest_name, **weakest_row})
    else:
        items.append({"label": "Strongest basis", "commodity": strongest_name, **strongest_row})
        items.append({"label": "Weakest basis", "commodity": weakest_name, **weakest_row})
    return {
        "kind": "basis_movers",
        "title": "Basis movers",
        "items": items,
        "empty": False,
        "empty_reason": None,
        "note": (
            "Ranked from today's snapshot only — no prior-day basis is "
            "stored, so this is not a day-over-day move."
        ),
    }


def _usda_today_section(
    todays_research: list[dict[str, object]], total_research: int, draft_date: date
) -> dict[str, object]:
    if not todays_research:
        reason = EMPTY_USDA.format(date=draft_date.isoformat())
        if total_research:
            reason += f" {total_research} research report(s) on file in total."
        return {
            "kind": "usda_today",
            "title": "USDA today",
            "reports": [],
            "empty": True,
            "empty_reason": reason,
        }
    return {
        "kind": "usda_today",
        "title": "USDA today",
        "reports": todays_research,
        "empty": False,
        "empty_reason": None,
    }


def _upcoming_section(
    upcoming: list[dict[str, object]], draft_date: date
) -> dict[str, object]:
    if not upcoming:
        return {
            "kind": "upcoming_reports",
            "title": "Upcoming reports",
            "events": [],
            "empty": True,
            "empty_reason": EMPTY_UPCOMING,
        }
    return {
        "kind": "upcoming_reports",
        "title": "Upcoming reports",
        "events": upcoming,
        "empty": False,
        "empty_reason": None,
    }


# ---------------------------------------------------------------------------
# Rendering (plain text + simple HTML; empty states inline, never invented)
# ---------------------------------------------------------------------------

def _render_text(
    subject: str, draft_date: date, region: str, sections: tuple[dict[str, object], ...]
) -> str:
    lines = [
        subject,
        "",
        f"Date: {draft_date:%B} {draft_date.day}, {draft_date:%Y} | Region: {region}",
        "Preview only — nothing was sent.",
        "",
    ]
    top_bids = sections[0]
    lines.extend(["Top bids", "-"])
    for entry in top_bids["commodities"]:
        lines.append(str(entry["commodity"]))
        if entry["empty"]:
            lines.append(str(entry["empty_reason"]))
        else:
            for row in entry["top_bids"]:
                lines.append(
                    f"• {_row_label(row)} — {_format_cash(row.get('cash_price_bu'))}; "
                    f"basis {_format_basis(row.get('basis'))}"
                )
    lines.append("")

    basis = sections[1]
    lines.extend(["Basis movers", "-"])
    if basis["empty"]:
        lines.append(str(basis["empty_reason"]))
    else:
        for item in basis["items"]:
            lines.append(
                f"• {item['label']} ({item['commodity']}): {_row_label(item)} — "
                f"basis {_format_basis(item.get('basis'))}"
            )
        lines.append(str(basis["note"]))
    lines.append("")

    usda = sections[2]
    lines.extend(["USDA today", "-"])
    if usda["empty"]:
        lines.append(str(usda["empty_reason"]))
    else:
        for item in usda["reports"]:
            lines.append(
                f"• {item.get('report_type')} — {item.get('commodity')} "
                f"({item.get('vintage') or item.get('report_date')}); "
                f"source: {item.get('source')}"
            )
    lines.append("")

    upcoming = sections[3]
    lines.extend(["Upcoming reports", "-"])
    if upcoming["empty"]:
        lines.append(str(upcoming["empty_reason"]))
    else:
        for event in upcoming["events"]:
            lines.append(
                f"• {event.get('name') or event.get('report_type')} — "
                f"{event.get('report_date') or event.get('date')}"
                + (f"; source: {event.get('source')}" if event.get("source") else "")
            )
    lines.append("")
    lines.append(
        "Posted-bid snapshot only, not a delivered-netback recommendation. "
        "Freight is not included. Verify prices, grades, delivery periods, "
        "futures contracts, and freight before making a sale."
    )
    return "\n".join(lines)


def _render_html(
    subject: str, draft_date: date, region: str, sections: tuple[dict[str, object], ...]
) -> str:
    parts = [
        "<!doctype html><html><body style='margin:0;background:#f3f4f6;font-family:Arial,sans-serif;color:#111827'>"
        "<div style='max-width:680px;margin:0 auto;background:white;padding:32px'>",
        f"<h1 style='margin-top:0'>{escape(subject)}</h1>",
        f"<p style='color:#4b5563'>{draft_date:%B} {draft_date.day}, {draft_date:%Y} | {escape(region)} | Preview only — nothing was sent.</p>",
    ]
    for section in sections:
        parts.append(f"<h2 style='margin-top:28px'>{escape(str(section['title']))}</h2>")
        if section["empty"]:
            parts.append(f"<p>{escape(str(section['empty_reason']))}</p>")
            continue
        if section["kind"] == "top_bids":
            for entry in section["commodities"]:
                parts.append(f"<h3>{escape(str(entry['commodity']))}</h3>")
                if entry["empty"]:
                    parts.append(f"<p>{escape(str(entry['empty_reason']))}</p>")
                else:
                    rows = "".join(
                        f"<li>{escape(_row_label(row))} — {escape(_format_cash(row.get('cash_price_bu')))}; "
                        f"basis {escape(_format_basis(row.get('basis')))}</li>"
                        for row in entry["top_bids"]
                    )
                    parts.append(f"<ul>{rows}</ul>")
        elif section["kind"] == "basis_movers":
            rows = "".join(
                f"<li>{escape(str(item['label']))} ({escape(str(item['commodity']))}): "
                f"{escape(_row_label(item))} — basis {escape(_format_basis(item.get('basis')))}</li>"
                for item in section["items"]
            )
            parts.append(f"<ul>{rows}</ul><p style='font-size:13px;color:#4b5563'>{escape(str(section['note']))}</p>")
        elif section["kind"] == "usda_today":
            rows = "".join(
                f"<li>{escape(str(item.get('report_type')))} — {escape(str(item.get('commodity')))} "
                f"({escape(str(item.get('vintage') or item.get('report_date')))}); "
                f"source: {escape(str(item.get('source')))}</li>"
                for item in section["reports"]
            )
            parts.append(f"<ul>{rows}</ul>")
        elif section["kind"] == "upcoming_reports":
            rows = "".join(
                f"<li>{escape(str(event.get('name') or event.get('report_type')))} — "
                f"{escape(str(event.get('report_date') or event.get('date')))}</li>"
                for event in section["events"]
            )
            parts.append(f"<ul>{rows}</ul>")
    parts.append(
        "<p style='font-size:12px;color:#6b7280'>Posted-bid snapshot only, not a delivered-netback "
        "recommendation. Freight is not included. Verify prices, grades, delivery periods, futures "
        "contracts, and freight before making a sale.</p></div></body></html>"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_commodities(commodity: str | None) -> list[str]:
    if commodity is None or not commodity.strip():
        return list(REPORT_COMMODITIES)
    wanted = commodity.strip().casefold()
    for name in REPORT_COMMODITIES:
        if name.casefold() == wanted:
            return [name]
    return [commodity.strip().title()]


def _filter_rows(
    rows: list[dict[str, object]], *, location: str | None
) -> list[dict[str, object]]:
    if location is None or not location.strip():
        return list(rows)
    wanted = location.strip().casefold()
    return [
        row for row in rows
        if wanted in str(row.get("location") or "").casefold()
        or wanted in str(row.get("company_name") or "").casefold()
    ]


def _is_dated(row: dict[str, object], draft_date: date) -> bool:
    iso = draft_date.isoformat()
    for field in ("report_date", "vintage"):
        value = row.get(field)
        if value is None:
            continue
        if str(value).strip() == iso:
            return True
        try:
            if date.fromisoformat(str(value).strip()[:10]) == draft_date:
                return True
        except ValueError:
            continue
    return False


def _normalise_upcoming_events(
    events: list[dict[str, object]], *, after: date
) -> list[dict[str, object]]:
    kept: list[tuple[date, dict[str, object]]] = []
    for event in events:
        raw = event.get("report_date") or event.get("date")
        if raw is None:
            continue
        try:
            parsed = date.fromisoformat(str(raw).strip()[:10])
        except ValueError:
            continue
        if parsed >= after:
            kept.append((parsed, dict(event)))
    kept.sort(key=lambda item: item[0])
    return [event for _, event in kept]


def _as_number(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_cash(value: object) -> str:
    number = _as_number(value)
    return "n/a" if number is None else f"${number:,.2f}/bu"


def _format_basis(value: object) -> str:
    number = _as_number(value)
    return "n/a" if number is None else f"{number:+.2f}/bu"


def _row_label(row: dict[str, object]) -> str:
    company = str(row.get("company_name") or "").strip()
    location = str(row.get("location") or "").strip()
    if company and location and company.casefold() != location.casefold():
        return f"{company} — {location}"
    return company or location or "Unlabelled market"
