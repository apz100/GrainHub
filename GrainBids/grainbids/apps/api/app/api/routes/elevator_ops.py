"""Elevator Ops silo v1 (Bushel / Grain Discovery-like).

Grower contracts, scale tickets, and CRM notes for elevator staff, plus a
white-label grower portal feed. All rows are scoped to the requesting org
via ``X-Org-Id`` (see ``app.core.request_context``), following the quotes
and normalized-prices routes.

Out of scope for v1 (scaffold only, no external calls):
- eSign: POST /contracts/{id}/esign only records a signing request with
  status ``pending_signature``. No eSign provider is configured or called.
- Payments / settlements: no money movement, no invoicing.
- ERP sync (Agris / Agvance / AgTrax): no ERP is referenced anywhere in
  the repo, so no sync target is wired in. Adam to decide.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.request_context import RequestContext, get_request_context, require_admin
from app.db.session import get_db
from app.models.contract import CONTRACT_STATUSES, GrowerContract
from app.models.crm_note import CrmNote
from app.models.scale_ticket import ScaleTicket


router = APIRouter(prefix="/api/elevator-ops", tags=["elevator-ops"])

ESIGN_NOT_CONFIGURED_NOTE = (
    "eSign provider not configured — signing request recorded as "
    "pending_signature; no document was sent to any eSign service."
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ContractCreate(BaseModel):
    company_id: uuid.UUID | None = None
    grower_name: str = Field(min_length=1, max_length=200)
    commodity: str = Field(min_length=1, max_length=100)
    quantity_bushels: Decimal = Field(gt=0)
    delivery_start: date | None = None
    delivery_end: date | None = None
    price_per_bushel: Decimal | None = Field(default=None, ge=0)
    basis: Decimal | None = None
    status: str = "draft"

    @field_validator("grower_name", "commodity", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value):
        if value not in CONTRACT_STATUSES:
            raise ValueError(f"status must be one of {sorted(CONTRACT_STATUSES)}")
        return value

    @model_validator(mode="after")
    def _delivery_window(self):
        if self.delivery_start and self.delivery_end and self.delivery_end < self.delivery_start:
            raise ValueError("delivery_end must be on or after delivery_start")
        return self


class ScaleTicketCreate(BaseModel):
    contract_id: uuid.UUID | None = None
    ticket_number: str = Field(min_length=1, max_length=100)
    ticket_date: date
    commodity: str = Field(min_length=1, max_length=100)
    bushels: Decimal = Field(gt=0)
    moisture_percent: Decimal | None = Field(default=None, ge=0, le=100)
    grade: str | None = Field(default=None, max_length=100)

    @field_validator("ticket_number", "commodity", "grade", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


class CrmNoteCreate(BaseModel):
    company_id: uuid.UUID | None = None
    grower_name: str = Field(min_length=1, max_length=200)
    author: str | None = Field(default=None, max_length=200)
    note: str = Field(min_length=1)
    follow_up_date: date | None = None

    @field_validator("grower_name", "author", "note", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def _serialize_contract(row: GrowerContract) -> dict:
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "company_id": str(row.company_id) if row.company_id else None,
        "grower_name": row.grower_name,
        "commodity": row.commodity,
        "quantity_bushels": float(row.quantity_bushels),
        "delivery_start": row.delivery_start.isoformat() if row.delivery_start else None,
        "delivery_end": row.delivery_end.isoformat() if row.delivery_end else None,
        "price_per_bushel": float(row.price_per_bushel) if row.price_per_bushel is not None else None,
        "basis": float(row.basis) if row.basis is not None else None,
        "status": row.status,
        "esign_status": row.esign_status,
        "esign_requested_at": row.esign_requested_at.isoformat() if row.esign_requested_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serialize_scale_ticket(row: ScaleTicket) -> dict:
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "contract_id": str(row.contract_id) if row.contract_id else None,
        "ticket_number": row.ticket_number,
        "ticket_date": row.ticket_date.isoformat() if row.ticket_date else None,
        "commodity": row.commodity,
        "bushels": float(row.bushels),
        "moisture_percent": float(row.moisture_percent) if row.moisture_percent is not None else None,
        "grade": row.grade,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serialize_crm_note(row: CrmNote) -> dict:
    return {
        "id": str(row.id),
        "org_id": str(row.org_id),
        "company_id": str(row.company_id) if row.company_id else None,
        "grower_name": row.grower_name,
        "author": row.author,
        "note": row.note,
        "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


@router.get("/module")
def module_info():
    return {
        "module": "elevator-ops",
        "primary_routes": [
            "/api/elevator-ops/contracts",
            "/api/elevator-ops/scale-tickets",
            "/api/elevator-ops/crm-notes",
        ],
        "esign": "stubbed — no provider configured",
        "erp_sync": "not configured — no ERP referenced in repo",
    }


@router.get("/contracts")
def list_contracts(
    limit: int = Query(50, ge=1, le=200),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(GrowerContract)
        .where(GrowerContract.org_id == context.org_id)
        .order_by(desc(GrowerContract.created_at))
        .limit(limit)
    ).scalars().all()
    return {"rows": [_serialize_contract(row) for row in rows]}


@router.post("/contracts", status_code=201)
def create_contract(
    payload: ContractCreate,
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = GrowerContract(
        org_id=context.org_id,
        company_id=payload.company_id,
        grower_name=payload.grower_name,
        commodity=payload.commodity,
        quantity_bushels=payload.quantity_bushels,
        delivery_start=payload.delivery_start,
        delivery_end=payload.delivery_end,
        price_per_bushel=payload.price_per_bushel,
        basis=payload.basis,
        status=payload.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_contract(row)


@router.post("/contracts/{contract_id}/esign")
def request_contract_esign(
    contract_id: uuid.UUID,
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Record an eSign request for a contract.

    STUB: no eSign provider is configured and no external service is
    called. The contract is marked ``pending_signature`` and the response
    says so plainly. A real provider (DocuSign, Adobe Sign, etc. — Adam
    to choose) must be wired in before any document is sent for signing.
    """
    row = db.execute(
        select(GrowerContract).where(
            GrowerContract.id == contract_id,
            GrowerContract.org_id == context.org_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="contract not found")
    if row.status == "cancelled":
        raise HTTPException(status_code=400, detail="cancelled contracts cannot be sent for signature")

    row.status = "pending_signature"
    row.esign_status = "pending_signature"
    row.esign_requested_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        **_serialize_contract(row),
        "esign_provider": None,
        "esign_configured": False,
        "note": ESIGN_NOT_CONFIGURED_NOTE,
    }


# ---------------------------------------------------------------------------
# Scale tickets
# ---------------------------------------------------------------------------


@router.get("/scale-tickets")
def list_scale_tickets(
    contract_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    query = (
        select(ScaleTicket)
        .where(ScaleTicket.org_id == context.org_id)
        .order_by(desc(ScaleTicket.created_at))
        .limit(limit)
    )
    if contract_id:
        query = query.where(ScaleTicket.contract_id == contract_id)
    rows = db.execute(query).scalars().all()
    return {"rows": [_serialize_scale_ticket(row) for row in rows]}


@router.post("/scale-tickets", status_code=201)
def create_scale_ticket(
    payload: ScaleTicketCreate,
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.contract_id is not None:
        contract = db.execute(
            select(GrowerContract).where(
                GrowerContract.id == payload.contract_id,
                GrowerContract.org_id == context.org_id,
            )
        ).scalar_one_or_none()
        if contract is None:
            raise HTTPException(status_code=404, detail="contract not found")
    row = ScaleTicket(
        org_id=context.org_id,
        contract_id=payload.contract_id,
        ticket_number=payload.ticket_number,
        ticket_date=payload.ticket_date,
        commodity=payload.commodity,
        bushels=payload.bushels,
        moisture_percent=payload.moisture_percent,
        grade=payload.grade,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_scale_ticket(row)


# ---------------------------------------------------------------------------
# CRM notes
# ---------------------------------------------------------------------------


@router.get("/crm-notes")
def list_crm_notes(
    grower_name: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    context: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    query = (
        select(CrmNote)
        .where(CrmNote.org_id == context.org_id)
        .order_by(desc(CrmNote.created_at))
        .limit(limit)
    )
    if grower_name:
        query = query.where(CrmNote.grower_name.ilike(f"%{grower_name.strip()}%"))
    rows = db.execute(query).scalars().all()
    return {"rows": [_serialize_crm_note(row) for row in rows]}


@router.post("/crm-notes", status_code=201)
def create_crm_note(
    payload: CrmNoteCreate,
    context: RequestContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = CrmNote(
        org_id=context.org_id,
        company_id=payload.company_id,
        grower_name=payload.grower_name,
        author=payload.author,
        note=payload.note,
        follow_up_date=payload.follow_up_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_crm_note(row)
