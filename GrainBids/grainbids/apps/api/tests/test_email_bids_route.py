"""Route tests for the parse-only email-bid ingest endpoint.

The email_bids router runs standalone with the DB dependency overridden
by a strict fake session: any ``add`` / ``commit`` / ``execute`` /
``flush`` call raises, so these tests prove the endpoint never writes to
the database.  No mailbox access, no real emails, no sends.  All fixtures
are synthetic and use a neutral test location ("Testville"); no real
sender's bid data is used.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.email_bids import router as email_bids_router  # noqa: E402
from app.db.session import get_db  # noqa: E402

ANDERSONS_BODY = """Andersons Producer Commodity Bid Sheet
Corn
Testville
Nov 26 CH27 4.5025 -0.25 6.45 253.90
Dec 26 CH27 4.5500 -0.20 6.50 255.90
Soybeans
Testville
Nov 26 SX26 10.2500 -0.60 14.20 521.80
"""

GENERIC_BODY = """Test Elevator Co. Daily Bids
Corn Nov 2026 $6.45/bu
Soybeans Harvest 2026 $14.20/bu
Wheat Dec 2026 $7.10/bu
"""

INCOMPLETE_BODY = """Test Elevator Co. Daily Bids
Corn Nov 2026 $6.45/bu
Soybeans Dec 2026
Wheat Jan 2027 $7.10/bu
"""

OCR_BODY = """BroadGrain Bid Sheet   Del Testville
Corn
Nov-26   -0.25   4.5025   CH27   $6.45   $253.90
Dec-26   -0.20   4.5500   CH27   $6.50   $255.90
Soybeans
Nov-26   -0.60   10.2500   SX26   $14.20   $521.80
"""

EML_BODY = (
    "From: bids@andersons.com\r\n"
    "Subject: Producer Commodity Bid Sheet\r\n"
    'Content-Type: text/plain; charset="utf-8"\r\n'
    "\r\n" + ANDERSONS_BODY
)


class _StrictFakeSession:
    """Fails loudly on any database interaction.

    The endpoint is parse-only: it must never touch the session at all.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def add(self, *args, **kwargs):  # noqa: D102
        self.calls.append("add")
        raise AssertionError("email-bids endpoint must not write to the DB (add)")

    def commit(self, *args, **kwargs):  # noqa: D102
        self.calls.append("commit")
        raise AssertionError("email-bids endpoint must not write to the DB (commit)")

    def flush(self, *args, **kwargs):  # noqa: D102
        self.calls.append("flush")
        raise AssertionError("email-bids endpoint must not write to the DB (flush)")

    def execute(self, *args, **kwargs):  # noqa: D102
        self.calls.append("execute")
        raise AssertionError("email-bids endpoint must not read the DB (execute)")


def _make_client(session: _StrictFakeSession) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(email_bids_router)

    def override_db():
        yield session

    test_app.dependency_overrides[get_db] = override_db
    return TestClient(test_app)


def test_json_text_parse_andersons() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        json={
            "sender": "bids@andersons.com",
            "subject": "Producer Commodity Bid Sheet",
            "body_text": ANDERSONS_BODY,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Andersons"
    assert body["source"] == "text"
    assert body["total_rows"] == 3
    assert len(body["valid_rows"]) == 3
    assert body["rejected_rows"] == []
    assert body["parse_success_rate"] == 1.0
    corn = body["valid_rows"][0]
    assert corn["commodity"] == "Corn"
    assert corn["delivery_month"] == "Nov 2026"
    assert corn["cash_price"] == 6.45
    assert corn["location"] == "Testville"


def test_file_upload_txt_parse() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        files={"file": ("daily-bids.txt", GENERIC_BODY.encode(), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 3
    assert len(body["valid_rows"]) == 3
    assert body["valid_rows"][1]["commodity"] == "Soybeans"
    assert body["valid_rows"][1]["delivery_month"] == "Harvest 2026"
    assert body["parse_success_rate"] == 1.0


def test_file_upload_eml_extracts_sender_subject_and_body() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        files={"file": ("bids.eml", EML_BODY.encode(), "message/rfc822")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Andersons"
    assert body["sender"] == "bids@andersons.com"
    assert body["subject"] == "Producer Commodity Bid Sheet"
    assert len(body["valid_rows"]) == 3


def test_incomplete_rows_rejected_with_success_rate() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        json={"sender": "", "subject": "Daily bids", "body_text": INCOMPLETE_BODY},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["valid_rows"]) == 2
    assert len(body["rejected_rows"]) == 1
    assert body["total_rows"] == 3
    assert body["parse_success_rate"] == 2 / 3
    rejected = body["rejected_rows"][0]
    assert rejected["status"] == "incomplete"
    assert "price" in rejected["reason"]
    assert "Soybeans" in rejected["raw_text"]


def test_unknown_sender_still_parses_generic_rows() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        json={
            "sender": "someone@example.com",
            "subject": "Random newsletter",
            "body_text": GENERIC_BODY,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Unknown"
    assert len(body["valid_rows"]) == 3


def test_empty_body_json_returns_400() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    for payload in (
        {"sender": "", "subject": "Daily bids", "body_text": ""},
        {"sender": "", "subject": "Daily bids", "body_text": "   \n  "},
        {"sender": "", "subject": "Daily bids"},
    ):
        response = client.post("/api/email-bids/parse", json=payload)
        assert response.status_code == 400
        assert "body_text" in response.json()["detail"]


def test_empty_file_upload_returns_400() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        files={"file": ("empty.txt", b"   \n", "text/plain")},
    )
    assert response.status_code == 400


def test_unsupported_file_extension_returns_400() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        files={"file": ("bids.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert response.status_code == 400
    assert ".eml" in response.json()["detail"]


def test_ocr_text_parse() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.post(
        "/api/email-bids/parse",
        json={
            "sender": "Dylan Stewart",
            "subject": "BroadGrain bid sheet",
            "body_text": OCR_BODY,
            "source": "ocr",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "BroadGrain"
    assert body["source"] == "ocr"
    assert len(body["valid_rows"]) == 3
    assert body["rejected_rows"] == []
    assert body["valid_rows"][0]["source"] == "ocr"
    assert body["valid_rows"][0]["delivery_month"] == "Nov 2026"
    assert body["valid_rows"][0]["cash_price_cad_per_mt"] == 253.90


def test_senders_list_comes_from_parser_module() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    response = client.get("/api/email-bids/senders")
    assert response.status_code == 200
    senders = response.json()["senders"]
    companies = {entry["company"] for entry in senders}
    assert companies == {"MacEwen", "Andersons", "BroadGrain", "Richardson", "P&H", "Bunge"}
    by_company = {entry["company"]: entry for entry in senders}
    # Quirks are the parser module's own documented quirks, not invented.
    assert "MT-only" in by_company["MacEwen"]["quirks"]
    assert "six-column" in by_company["Andersons"]["quirks"]
    assert "basis-only" in by_company["Bunge"]["quirks"]
    assert "inline images" in by_company["BroadGrain"]["quirks"]
    assert "inline images" in by_company["Richardson"]["quirks"]
    assert "inline images" in by_company["P&H"]["quirks"]
    # Image-table senders arrive as OCR; the rest as plain text.
    assert by_company["BroadGrain"]["input"] == "ocr"
    assert by_company["Richardson"]["input"] == "ocr"
    assert by_company["P&H"]["input"] == "ocr"
    assert by_company["MacEwen"]["input"] == "text"
    assert by_company["Bunge"]["input"] == "text"
    # Detection markers come from the parser module too.
    assert "macewen" in by_company["MacEwen"]["markers"]
    assert "jose.borunda@bunge.com" in by_company["Bunge"]["markers"]


def test_no_db_writes_on_parse_or_senders() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    parse = client.post(
        "/api/email-bids/parse",
        json={"sender": "", "subject": "Daily bids", "body_text": GENERIC_BODY},
    )
    assert parse.status_code == 200
    senders = client.get("/api/email-bids/senders")
    assert senders.status_code == 200
    assert session.calls == []


def test_bunge_basis_only_rows_are_valid_via_json() -> None:
    session = _StrictFakeSession()
    client = _make_client(session)
    body = """Soybeans BCC
Nov-26: +0.45 CH27
Dec-26: -0.12 CZ26
"""
    response = client.post(
        "/api/email-bids/parse",
        json={
            "sender": "jose.borunda@bunge.com",
            "subject": "Bunge BIDS MTL/BCC",
            "body_text": body,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Bunge"
    assert len(data["valid_rows"]) == 2
    assert data["valid_rows"][0]["cash_price"] is None  # basis-only quote
    assert data["valid_rows"][0]["basis"] == 0.45
    assert data["valid_rows"][0]["basis_currency"] == "USD"
