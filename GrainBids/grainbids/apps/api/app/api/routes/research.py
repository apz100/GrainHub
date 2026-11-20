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
    fetch_fas_psd,
    fetch_fas_psd_attribute_names,
    fetch_fas_psd_unit_names,
    fetch_fas_psd_world,
    fetch_nass_quick_stats,
    fetch_public_file_text,
    parse_commitments_of_traders_text,
    parse_crop_production_text,
    parse_crop_progress_text,
    parse_export_sales_text,
    parse_fas_psd_rows,
    parse_grain_stocks_text,
    parse_nass_records,
    parse_wasde_text,
    research_status,
)
from app.services.research_cache import get_or_fetch

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


def _cache_envelope(cached) -> dict[str, object]:
    return {
        "state": cached.cache_state,
        "fetched_at": cached.fetched_at.isoformat() if cached.fetched_at else None,
    }


def _psd_names(db: Session, kind: str) -> dict[int, str]:
    """PSD attribute/unit name tables, cached for a week.

    Payloads store {str(id): name} (JSON keys are strings); the
    decoder wants {int(id): name}, so keys are converted back here.
    """
    if kind == "attributes":
        dataset, fetcher = "fas_psd_attributes", fetch_fas_psd_attribute_names
    else:
        dataset, fetcher = "fas_psd_units", fetch_fas_psd_unit_names
    cached = get_or_fetch(
        db,
        dataset=dataset,
        cache_key="all",
        source="USDA FAS PSD",
        fetcher=lambda: {"names": {str(k): v for k, v in fetcher().items()}},
    )
    return {int(k): str(v) for k, v in cached.payload.get("names", {}).items()}


@router.get("/fas-psd/commodities")
def fas_psd_commodities(
    commodity_code: str = Query(...),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """PSD commodity catalogue rows for one commodity code (cached 24 h)."""
    try:
        cached = get_or_fetch(
            db,
            dataset="fas_psd_commodities",
            cache_key=commodity_code,
            source="USDA FAS PSD",
            fetcher=lambda: {"rows": fetch_fas_psd(commodity_code=commodity_code)},
        )
    except ResearchKeyRequired as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "commodity_code": commodity_code,
        "source": "USDA FAS PSD",
        "rows": cached.payload.get("rows", []),
        "cache": _cache_envelope(cached),
    }


@router.get("/fas-psd/world")
def fas_psd_world(
    commodity_code: str = Query("0440000"),
    year: int = Query(2026),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Decoded world PSD table for one commodity + marketing year.

    Live shape verified 2026-11-20: /api/psd/commodity/{code}/world/
    year/{year}; rows are decoded with the runtime attribute/unit
    lookups (never hardcoded ids). Cached 24 h; the response carries
    the cache state and fetch time so staleness is never hidden.
    """

    def _fetch_world() -> dict[str, object]:
        raw_rows = fetch_fas_psd_world(commodity_code=commodity_code, market_year=year)
        attributes = _psd_names(db, "attributes")
        units = _psd_names(db, "units")
        return {
            "rows": parse_fas_psd_rows(
                raw_rows, attribute_names=attributes, unit_names=units
            )
        }

    try:
        cached = get_or_fetch(
            db,
            dataset="fas_psd_world",
            cache_key=f"{commodity_code}/{year}",
            source="USDA FAS PSD",
            fetcher=_fetch_world,
        )
    except ResearchKeyRequired as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "commodity_code": commodity_code,
        "market_year": year,
        "source": "USDA FAS PSD",
        "rows": cached.payload.get("rows", []),
        "cache": _cache_envelope(cached),
    }


@router.get("/nass/series")
def nass_series(
    commodity: str = Query(...),
    year: int = Query(...),
    limit: int = Query(500, ge=1, le=5000),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Cached variant of /nass (24 h) with a bounded record count.

    /nass stays the always-live passthrough; this route exists for
    pages that reload often. ``truncated`` says plainly when the
    parsed series was cut to ``limit``.
    """

    def _fetch_series() -> dict[str, object]:
        records = parse_nass_records(fetch_nass_quick_stats(commodity=commodity, year=year))
        return {"records": records, "total_records": len(records)}

    try:
        cached = get_or_fetch(
            db,
            dataset="nass_series",
            cache_key=f"{commodity.upper()}/{year}",
            source="USDA NASS Quick Stats",
            fetcher=_fetch_series,
        )
    except ResearchKeyRequired as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    records = cached.payload.get("records", [])
    total = cached.payload.get("total_records", len(records))
    return {
        "commodity": commodity,
        "year": year,
        "source": "USDA NASS Quick Stats",
        "records": records[:limit],
        "total_records": total,
        "truncated": total > limit,
        "cache": _cache_envelope(cached),
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
    elif report_type == "grain_stocks":
        values = parse_grain_stocks_text(str(text))
        source = "USDA NASS Grain Stocks"
    elif report_type == "export_sales":
        values = parse_export_sales_text(str(text))
        source = "USDA FAS Export Sales"
    elif report_type == "commitments_of_traders":
        values = parse_commitments_of_traders_text(str(text))
        source = "CFTC Commitments of Traders"
    elif report_type == "crop_production":
        values = parse_crop_production_text(str(text))
        source = "USDA NASS Crop Production"
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
