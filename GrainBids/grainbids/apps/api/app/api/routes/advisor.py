"""Advisor silo v1 routes (GrainFox-like).

Wiring note for the coordinator: this router is NOT yet included in
``app/main.py`` — add ``from app.api.routes.advisor import router as
advisor_router`` and ``app.include_router(advisor_router)`` there. The
routes below are complete and tested standalone (see tests/test_advisor.py).

Endpoints:
* POST /api/advisor/farm-profiles — create a farm profile for the org.
* GET  /api/advisor/farm-profiles — list the org's farm profiles.
* POST /api/advisor/breakeven — breakeven + profit math (pure, no DB).
* POST /api/advisor/scenarios — sell-now vs hold math (pure, no DB).
* GET  /api/advisor/signal — sell/hold signal from the latest real cash
  price for a commodity/location; ``insufficient_data`` when the price or
  the profile inputs are missing. Never invents a price.
* POST /api/advisor/ask — AI assistant scaffold. Always 501 in v1 and
  never calls a paid API (see app/services/advisor.py llm_config_status).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, get_request_context
from app.db.session import get_db
from app.models.farm_profile import RISK_TOLERANCES, FarmProfile
from app.models.normalized_price import NormalizedPrice
from app.models.price_snapshot import PriceSnapshot
from app.models.source import Source
from app.services.advisor import (
    calculate_breakeven,
    compare_sell_vs_hold,
    llm_config_status,
    signal_for_profile_and_price,
)


router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class CropMixEntry(BaseModel):
    commodity: str = Field(..., min_length=1, max_length=120)
    acres: float = Field(..., gt=0)
    expected_yield_bu_per_acre: float = Field(..., gt=0)
    cost_per_acre: float = Field(..., ge=0)


class FarmProfileCreate(BaseModel):
    farm_name: str = Field(..., min_length=1, max_length=200)
    crop_mix: list[CropMixEntry] = Field(default_factory=list)
    total_acres: float | None = Field(None, gt=0)
    storage_capacity_bu: float | None = Field(None, ge=0)
    cash_flow_target_usd: float | None = Field(None, ge=0)
    risk_tolerance: str = Field("moderate")
    home_location: str | None = Field(None, max_length=200)

    def validated_risk_tolerance(self) -> str:
        tolerance = (self.risk_tolerance or "moderate").strip().lower()
        if tolerance not in RISK_TOLERANCES:
            raise HTTPException(
                status_code=400,
                detail=f"risk_tolerance must be one of {', '.join(RISK_TOLERANCES)}",
            )
        return tolerance


class BreakevenRequest(BaseModel):
    yield_bu_per_acre: float = Field(..., gt=0)
    cost_per_acre: float = Field(..., ge=0)
    cash_price_bu: float | None = Field(None, ge=0)
    acres: float | None = Field(None, gt=0)


class ScenarioRequest(BaseModel):
    cash_price_now: float = Field(..., ge=0)
    deferred_price: float = Field(..., ge=0)
    storage_cost_per_bu_per_month: float = Field(..., ge=0)
    months_held: float = Field(..., ge=0)
    bushels: float = Field(..., gt=0)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    farm_profile_id: uuid.UUID | None = None


def _profile_to_dict(row: FarmProfile) -> dict:
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "farm_name": row.farm_name,
        "crop_mix": row.crop_mix_json or [],
        "total_acres": float(row.total_acres) if row.total_acres is not None else None,
        "storage_capacity_bu": float(row.storage_capacity_bu) if row.storage_capacity_bu is not None else None,
        "cash_flow_target_usd": float(row.cash_flow_target_usd) if row.cash_flow_target_usd is not None else None,
        "risk_tolerance": row.risk_tolerance,
        "home_location": row.home_location,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _latest_price(
    db: Session,
    *,
    org_id: uuid.UUID,
    commodity_name: str,
    location: str | None,
) -> NormalizedPrice | None:
    """Latest real cash-price row for the org/commodity (location optional).

    Scoped through the snapshot's source org, like watchlist previews.
    Canonical rows first, then most recently captured.
    """
    query = (
        select(NormalizedPrice)
        .join(PriceSnapshot, PriceSnapshot.id == NormalizedPrice.snapshot_id)
        .join(Source, Source.id == PriceSnapshot.source_id)
        .where(Source.org_id == org_id)
        .where(NormalizedPrice.commodity_name.ilike(f"%{commodity_name.strip()}%"))
        .order_by(desc(NormalizedPrice.is_canonical), desc(PriceSnapshot.captured_at))
    )
    if location:
        query = query.where(NormalizedPrice.location.ilike(f"%{location.strip()}%"))
    rows = db.execute(query).scalars().all()
    return rows[0] if rows else None


@router.post("/farm-profiles", status_code=201)
def create_farm_profile(
    payload: FarmProfileCreate,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    row = FarmProfile(
        org_id=context.org_id,
        farm_name=payload.farm_name.strip(),
        crop_mix_json=[entry.model_dump() for entry in payload.crop_mix],
        total_acres=Decimal(str(payload.total_acres)) if payload.total_acres is not None else None,
        storage_capacity_bu=Decimal(str(payload.storage_capacity_bu)) if payload.storage_capacity_bu is not None else None,
        cash_flow_target_usd=Decimal(str(payload.cash_flow_target_usd)) if payload.cash_flow_target_usd is not None else None,
        risk_tolerance=payload.validated_risk_tolerance(),
        home_location=(payload.home_location or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _profile_to_dict(row)


@router.get("/farm-profiles")
def list_farm_profiles(
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(FarmProfile)
        .where(FarmProfile.org_id == context.org_id)
        .order_by(desc(FarmProfile.created_at))
    ).scalars().all()
    return {"rows": [_profile_to_dict(row) for row in rows]}


@router.post("/breakeven")
def breakeven(payload: BreakevenRequest):
    try:
        result = calculate_breakeven(
            yield_bu_per_acre=payload.yield_bu_per_acre,
            cost_per_acre=payload.cost_per_acre,
            cash_price_bu=payload.cash_price_bu,
            acres=payload.acres,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "breakeven_per_bu": result.breakeven_per_bu,
        "margin_per_bu": result.margin_per_bu,
        "profit_per_acre": result.profit_per_acre,
        "profit_total": result.profit_total,
        "cash_price_bu": result.cash_price_bu,
    }


@router.post("/scenarios")
def scenarios(payload: ScenarioRequest):
    try:
        result = compare_sell_vs_hold(
            cash_price_now=payload.cash_price_now,
            deferred_price=payload.deferred_price,
            storage_cost_per_bu_per_month=payload.storage_cost_per_bu_per_month,
            months_held=payload.months_held,
            bushels=payload.bushels,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "sell_now_net": result.sell_now_net,
        "hold_net": result.hold_net,
        "storage_cost_total": result.storage_cost_total,
        "difference_hold_minus_sell_now": result.difference_hold_minus_sell_now,
        "recommendation": result.recommendation,
        "note": result.note,
    }


@router.get("/signal")
def advisor_signal(
    commodity_name: str = Query(..., min_length=1, max_length=120),
    location: str | None = Query(None, max_length=200),
    farm_profile_id: uuid.UUID | None = Query(None),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    if farm_profile_id is not None:
        profile = db.execute(
            select(FarmProfile).where(
                FarmProfile.id == farm_profile_id,
                FarmProfile.org_id == context.org_id,
            )
        ).scalar_one_or_none()
        if profile is None:
            raise HTTPException(status_code=404, detail="farm profile not found")
    else:
        profile = db.execute(
            select(FarmProfile)
            .where(FarmProfile.org_id == context.org_id)
            .order_by(desc(FarmProfile.created_at))
        ).scalar_one_or_none()

    price = _latest_price(db, org_id=context.org_id, commodity_name=commodity_name, location=location)
    signal = signal_for_profile_and_price(farm_profile=profile, price_row=price)
    return {
        "farm_profile_id": str(profile.id) if profile is not None else None,
        "commodity_name": commodity_name.strip(),
        "location": location.strip() if location else (price.location if price is not None else None),
        "cash_price_bu": float(price.cash_price_bu) if price is not None and price.cash_price_bu is not None else None,
        "futures_price": float(price.futures_price) if price is not None and price.futures_price is not None else None,
        "source_name": price.source_name if price is not None else None,
        "delivery_label": price.delivery_label if price is not None else None,
        "signal": signal.signal,
        "breakeven_per_bu": signal.breakeven_per_bu,
        "required_margin": signal.required_margin,
        "reasons": signal.reasons,
    }


@router.post("/ask")
def ask_advisor(
    payload: AskRequest,
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """AI assistant scaffold — always 501 in Cycle 1.

    Nothing here calls an LLM or any paid API. When no key is configured
    the 501 says so explicitly; when a key is configured the 501 says the
    provider integration is not wired up yet. Adam still needs to choose
    a provider + key before this can answer.
    """
    status = llm_config_status()
    raise HTTPException(status_code=501, detail=status["detail"])
