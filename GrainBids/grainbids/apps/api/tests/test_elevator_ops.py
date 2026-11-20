"""Elevator Ops silo v1 tests.

Covers Pydantic payload validation for contracts / scale tickets / CRM
notes, the CRUD-ish endpoints, and the stubbed eSign workflow.

The router is exercised on a standalone FastAPI app (not app.main) because
route wiring in app/main.py belongs to the Cycle 1 coordinator. A fake
session stands in for the database, following tests/test_newsletter.py.
No real eSign provider, ERP, or database is touched.
"""

from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path
import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.elevator_ops import (  # noqa: E402
    ContractCreate,
    CrmNoteCreate,
    ESIGN_NOT_CONFIGURED_NOTE,
    ScaleTicketCreate,
    router,
)
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.contract import GrowerContract  # noqa: E402
from app.models.crm_note import CrmNote  # noqa: E402
from app.models.scale_ticket import ScaleTicket  # noqa: E402


ORG_ID = uuid.uuid4()


def _test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


class _Result:
    def __init__(self, rows) -> None:
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeSession:
    """Minimal stand-in for a SQLAlchemy session."""

    def __init__(self, rows=None) -> None:
        self.rows = list(rows or [])
        self.added = []
        self.commit_count = 0

    def execute(self, _query):
        return _Result(self.rows)

    def add(self, row) -> None:
        self.added.append(row)

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, row) -> None:
        # Mimic DB-assigned defaults that only fire on flush.
        if getattr(row, "id", None) is None:
            row.id = uuid.uuid4()
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(timezone.utc)

    def rollback(self) -> None:
        pass


def _client_with(db: _FakeSession) -> TestClient:
    app = _test_app()

    def override_db():
        yield db

    def override_context():
        return RequestContext(org_id=ORG_ID, user_email="staff@example.com", user_role="admin")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_request_context] = override_context
    return TestClient(app)


class ContractValidationTests(unittest.TestCase):
    def _valid(self, **overrides):
        payload = {
            "grower_name": "Test Grower",
            "commodity": "Corn",
            "quantity_bushels": "5000",
        }
        payload.update(overrides)
        return payload

    def test_valid_contract(self) -> None:
        contract = ContractCreate(**self._valid())
        self.assertEqual(contract.status, "draft")
        self.assertEqual(contract.grower_name, "Test Grower")

    def test_quantity_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            ContractCreate(**self._valid(quantity_bushels="0"))
        with self.assertRaises(ValidationError):
            ContractCreate(**self._valid(quantity_bushels="-10"))

    def test_invalid_status_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ContractCreate(**self._valid(status="shipped"))

    def test_delivery_end_before_start_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ContractCreate(
                **self._valid(delivery_start="2026-12-01", delivery_end="2026-11-01")
            )

    def test_negative_price_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ContractCreate(**self._valid(price_per_bushel="-1.50"))


class ScaleTicketValidationTests(unittest.TestCase):
    def test_bushels_must_be_positive(self) -> None:
        with self.assertRaises(ValidationError):
            ScaleTicketCreate(
                ticket_number="T-1",
                ticket_date="2026-11-18",
                commodity="Soybeans",
                bushels="0",
            )

    def test_moisture_range_enforced(self) -> None:
        with self.assertRaises(ValidationError):
            ScaleTicketCreate(
                ticket_number="T-1",
                ticket_date="2026-11-18",
                commodity="Soybeans",
                bushels="100",
                moisture_percent="101",
            )
        ticket = ScaleTicketCreate(
            ticket_number="T-1",
            ticket_date="2026-11-18",
            commodity="Soybeans",
            bushels="100",
            moisture_percent="14.5",
        )
        self.assertEqual(str(ticket.moisture_percent), "14.5")


class CrmNoteValidationTests(unittest.TestCase):
    def test_empty_note_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CrmNoteCreate(grower_name="Test Grower", note="   ")

    def test_valid_note(self) -> None:
        note = CrmNoteCreate(grower_name="Test Grower", note="Called about fall delivery.")
        self.assertEqual(note.grower_name, "Test Grower")


class ModelTests(unittest.TestCase):
    def test_table_names(self) -> None:
        self.assertEqual(GrowerContract.__tablename__, "grower_contracts")
        self.assertEqual(ScaleTicket.__tablename__, "scale_tickets")
        self.assertEqual(CrmNote.__tablename__, "crm_notes")

    def test_contract_has_esign_stub_columns(self) -> None:
        columns = GrowerContract.__table__.columns
        self.assertIn("esign_status", columns)
        self.assertIn("esign_requested_at", columns)
        self.assertIn("status", columns)

    def test_scale_ticket_links_to_contract(self) -> None:
        columns = ScaleTicket.__table__.columns
        self.assertIn("contract_id", columns)
        self.assertIn("ticket_number", columns)


class EndpointTests(unittest.TestCase):
    def test_create_and_list_contracts(self) -> None:
        db = _FakeSession()
        client = _client_with(db)
        response = client.post(
            "/api/elevator-ops/contracts",
            json={
                "grower_name": "Test Grower",
                "commodity": "Corn",
                "quantity_bushels": "5000",
                "delivery_start": "2026-12-01",
                "delivery_end": "2027-02-28",
                "price_per_bushel": "4.50",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["grower_name"], "Test Grower")
        self.assertEqual(response.json()["status"], "draft")
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].org_id, ORG_ID)
        self.assertEqual(db.commit_count, 1)

    def test_list_contracts_empty(self) -> None:
        client = _client_with(_FakeSession())
        response = client.get("/api/elevator-ops/contracts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"rows": []})

    def test_create_scale_ticket(self) -> None:
        db = _FakeSession()
        client = _client_with(db)
        response = client.post(
            "/api/elevator-ops/scale-tickets",
            json={
                "ticket_number": "T-100",
                "ticket_date": "2026-11-18",
                "commodity": "Soybeans",
                "bushels": "850.5",
                "moisture_percent": "13.2",
                "grade": "#2",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["ticket_number"], "T-100")
        self.assertEqual(db.added[0].org_id, ORG_ID)

    def test_scale_ticket_with_unknown_contract_is_404(self) -> None:
        client = _client_with(_FakeSession(rows=[]))
        response = client.post(
            "/api/elevator-ops/scale-tickets",
            json={
                "contract_id": str(uuid.uuid4()),
                "ticket_number": "T-101",
                "ticket_date": "2026-11-18",
                "commodity": "Wheat",
                "bushels": "100",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_crm_note(self) -> None:
        db = _FakeSession()
        client = _client_with(db)
        response = client.post(
            "/api/elevator-ops/crm-notes",
            json={
                "grower_name": "Test Grower",
                "author": "staff@example.com",
                "note": "Prefers morning deliveries.",
                "follow_up_date": "2026-11-25",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["follow_up_date"], "2026-11-25")
        self.assertEqual(db.commit_count, 1)


class EsignStubTests(unittest.TestCase):
    def _contract_row(self, **overrides):
        row = GrowerContract(
            org_id=ORG_ID,
            grower_name="Test Grower",
            commodity="Corn",
            quantity_bushels=5000,
            status="offered",
        )
        row.id = uuid.uuid4()
        row.created_at = datetime.now(timezone.utc)
        for key, value in overrides.items():
            setattr(row, key, value)
        return row

    def test_esign_stub_marks_pending_signature_without_provider(self) -> None:
        contract = self._contract_row()
        db = _FakeSession(rows=[contract])
        client = _client_with(db)
        response = client.post(f"/api/elevator-ops/contracts/{contract.id}/esign")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "pending_signature")
        self.assertEqual(body["esign_status"], "pending_signature")
        self.assertIsNotNone(body["esign_requested_at"])
        self.assertFalse(body["esign_configured"])
        self.assertIsNone(body["esign_provider"])
        self.assertIn("not configured", body["note"])
        self.assertEqual(body["note"], ESIGN_NOT_CONFIGURED_NOTE)
        self.assertEqual(db.commit_count, 1)

    def test_esign_missing_contract_is_404(self) -> None:
        client = _client_with(_FakeSession(rows=[]))
        response = client.post(f"/api/elevator-ops/contracts/{uuid.uuid4()}/esign")
        self.assertEqual(response.status_code, 404)

    def test_esign_cancelled_contract_is_rejected(self) -> None:
        contract = self._contract_row(status="cancelled")
        db = _FakeSession(rows=[contract])
        client = _client_with(db)
        response = client.post(f"/api/elevator-ops/contracts/{contract.id}/esign")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(db.commit_count, 0)


class MigrationTests(unittest.TestCase):
    def test_migration_0017_chain(self) -> None:
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0017_add_elevator_ops.py"
        self.assertTrue(path.exists(), "0017_add_elevator_ops.py missing")
        source = path.read_text()
        self.assertIn('revision = "0017"', source)
        # Chains onto the advisor silo's 0016 migration.
        self.assertIn('down_revision = "0016"', source)
        for table in ("grower_contracts", "scale_tickets", "crm_notes"):
            self.assertIn(f'"{table}"', source)
        compile(source, str(path), "exec")


if __name__ == "__main__":
    unittest.main()
