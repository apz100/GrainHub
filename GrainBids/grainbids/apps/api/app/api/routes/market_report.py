from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, require_admin
from app.db.session import get_db
from app.models.research_report import ResearchReport
from app.services.market_report import append_research_section, build_market_report


router = APIRouter(prefix="/api/market-report", tags=["market-report"])


@router.get("/preview")
def preview_market_report(
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    report = build_market_report(db, org_id=context.org_id)
    research_rows = db.execute(
        select(ResearchReport)
        .where(ResearchReport.org_id == context.org_id)
        .order_by(ResearchReport.report_date.desc())
        .limit(10)
    ).scalars().all()
    research = [
        {
            "report_type": row.report_type,
            "commodity": row.commodity,
            "report_date": row.report_date,
            "vintage": row.vintage,
            "source": row.source,
            "payload": row.payload,
        }
        for row in research_rows
    ]
    return append_research_section(report, research).as_dict()
