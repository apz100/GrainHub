from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, get_request_context, require_admin
from app.db.session import get_db
from app.models.research_report import ResearchReport
from app.services.research import (
    REPORT_TYPES,
    ResearchKeyRequired,
    ResearchUpstreamError,
    fetch_nass_quick_stats,
    fetch_public_file_text,
    parse_crop_progress_text,
    parse_nass_records,
    parse_wasde_text,
    research_status,
)

router = APIRouter(prefix="/api/research", tags=["research"])


def _serialize(report: ResearchReport) -> dict[str, object]:
    return {
        "id": str(report.id),
        "report_type": report.report_type,
        "commodity": report.commodity,
        "report_date": report.report_date,
        "vintage": report.vintage,
        "source": report.source,
        "source_url": report.source_url,
        "delay_label": report.delay_label,
        "payload": report.payload,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


@router.get("/status")
def status(context: RequestContext = Depends(get_request_context)):
    current = research_status()
    return {
        "nass_configured": current.nass_configured,
        "fas_configured": current.fas_configured,
        "wasde_file_url": current.wasde_file_url,
        "crop_progress_file_url": current.crop_progress_file_url,
        "note": (
            "Keys are never returned. NASS / FAS collectors report "
            "'key required' until a free key is configured in env."
        ),
    }


@router.get("/reports")
def list_reports(
    report_type: str | None = Query(None),
    commodity: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    query = select(ResearchReport).where(ResearchReport.org_id == context.org_id)
    if report_type:
        query = query.where(ResearchReport.report_type == report_type)
    if commodity:
        query = query.where(ResearchReport.commodity.ilike(f"%{commodity.strip()}%"))
    rows = db.execute(query.order_by(ResearchReport.report_date.desc()).limit(limit)).scalars().all()
    return {"reports": [_serialize(row) for row in rows], "count": len(rows)}


@router.get("/wasde")
def wasde(
    commodity: str | None = Query(None),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    return list_reports(report_type="wasde", commodity=commodity, context=context, db=db)


@router.get("/crop-progress")
def crop_progress(
    commodity: str | None = Query(None),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    return list_reports(report_type="crop_progress", commodity=commodity, context=context, db=db)


@router.get("/nass")
def nass(
    commodity: str = Query(...),
    year: int = Query(...),
    context: RequestContext = Depends(get_request_context),
):
    try:
        records = fetch_nass_quick_stats(commodity=commodity, year=year)
    except ResearchKeyRequired as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "commodity": commodity,
        "year": year,
        "source": "USDA NASS Quick Stats",
        "records": parse_nass_records(records),
    }


@router.post("/ingest-file")
def ingest_file(
    payload: dict,
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report_type = str(payload.get("report_type") or "").strip()
    if report_type not in REPORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"report_type must be one of {', '.join(REPORT_TYPES)}.",
        )
    url = str(payload.get("url") or "").strip()
    text = payload.get("text")
    report_date = str(payload.get("report_date") or "").strip() or "unknown"
    if text is None:
        if not url:
            raise HTTPException(status_code=400, detail="Provide url or text for the report file.")
        try:
            text = fetch_public_file_text(url)
        except ResearchUpstreamError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    if report_type == "wasde":
        values = parse_wasde_text(str(text))
        source = "USDA WASDE"
    elif report_type == "crop_progress":
        values = parse_crop_progress_text(str(text))
        source = "USDA NASS Crop Progress"
    else:
        values = []
        source = f"USDA {report_type.replace('_', ' ').title()}"
    commodities = sorted({str(v.get("commodity")) for v in values if v.get("commodity")})
    stored = 0
    for commodity in commodities or ["All"]:
        rows = [v for v in values if str(v.get("commodity")) == commodity] or values
        report = ResearchReport(
            org_id=context.org_id,
            report_type=report_type,
            commodity=commodity,
            report_date=report_date,
            vintage=report_date,
            source=source,
            source_url=url or None,
            delay_label="Public release file; no delay beyond the release itself.",
            payload={"values": rows},
        )
        db.add(report)
        stored += 1
    db.commit()
    return {
        "report_type": report_type,
        "report_date": report_date,
        "source": source,
        "values_found": len(values),
        "reports_stored": stored,
        "note": "Only values present in the file were stored. Nothing was invented.",
    }
