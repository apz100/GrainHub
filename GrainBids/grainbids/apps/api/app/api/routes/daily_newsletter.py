"""Daily newsletter draft routes (preview only).

GET  /api/newsletter/daily-draft?date=YYYY-MM-DD[&commodity=..&location=..]
POST /api/newsletter/daily-draft/preview  {"date": ..., "commodity": ..., "location": ...}

Both return the draft for the requested day and send nothing:
no subscriber is required, no SMTP call is made, and no delivery
row is created. Delivery stays OFF — there is intentionally no
send endpoint in this module.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.services.daily_newsletter import generate_daily_draft, parse_draft_date


router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


class DailyDraftPreviewRequest(BaseModel):
    date: str | None = None
    commodity: str | None = None
    location: str | None = None


def _draft(
    db: Session,
    context: RequestContext,
    *,
    date_value: str | None,
    commodity: str | None,
    location: str | None,
) -> dict[str, object]:
    try:
        draft_date = parse_draft_date(date_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    draft = generate_daily_draft(
        db,
        draft_date,
        org_id=context.org_id,
        commodity=commodity,
        location=location,
    )
    return draft.as_dict()


@router.get("/daily-draft")
def get_daily_draft(
    date: str | None = Query(default=None, description="Draft date as YYYY-MM-DD; defaults to today (UTC)."),
    commodity: str | None = Query(default=None),
    location: str | None = Query(default=None),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _draft(db, context, date_value=date, commodity=commodity, location=location)


@router.post("/daily-draft/preview")
def preview_daily_draft(
    payload: DailyDraftPreviewRequest,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _draft(
        db,
        context,
        date_value=payload.date,
        commodity=payload.commodity,
        location=payload.location,
    )
