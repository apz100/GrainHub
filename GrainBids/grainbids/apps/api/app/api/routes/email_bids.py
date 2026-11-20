"""Parse-only preview endpoint for emailed cash-bid tables.

POST /api/email-bids/parse accepts either pasted email text (JSON) or an
uploaded ``.eml`` / ``.txt`` / ``.csv`` file (multipart) and runs it through
the pure parser in ``app.services.email_bid_parser``.  Nothing is stored
to the database and nothing is sent anywhere: the response is a preview of
the valid and rejected rows plus the parse success rate.

No mailbox access happens here -- the caller supplies the text or file.
All fixtures in tests are synthetic; no real sender's bid data is used.
"""

from __future__ import annotations

import email
import email.policy
import re
from email.message import Message

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import email_bid_parser
from app.services.email_bid_parser import (
    EmailBidParseResult,
    detect_sender_company,
    parse_email_bid_text,
    parse_ocr_bid_rows,
)

router = APIRouter(prefix="/api/email-bids", tags=["email-bids"])

#: File extensions accepted for multipart uploads.
_SUPPORTED_EXTENSIONS = (".eml", ".txt", ".csv")

#: Maximum upload size (2 MiB -- bid-table emails are small text files).
_MAX_UPLOAD_BYTES = 2 * 1024 * 1024


# ---------------------------------------------------------------------------
# Response shaping
# ---------------------------------------------------------------------------

def _result_to_dict(result: EmailBidParseResult, *, source: str) -> dict:
    return {
        "company": result.company,
        "sender": result.sender,
        "subject": result.subject,
        "source": source,
        "total_rows": result.total_rows,
        "valid_rows": [row.to_dict() for row in result.valid_rows],
        "rejected_rows": [
            {
                "raw_text": row.raw_text,
                "reason": row.reason,
                "status": row.status,
                "company": row.company,
                "commodity": row.commodity,
                "fields_present": list(row.fields_present),
            }
            for row in result.rejected_rows
        ],
        "parse_success_rate": result.parse_success_rate,
    }


# ---------------------------------------------------------------------------
# Input handling (JSON text or multipart file)
# ---------------------------------------------------------------------------

def _parse_fx_rate(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="fx_rate must be a number") from None
    if value <= 0:
        raise HTTPException(status_code=400, detail="fx_rate must be positive")
    return value


def _extract_eml_text(payload: bytes) -> tuple[str, str, str]:
    """Pull sender, subject and plain-text body out of a raw .eml file.

    Falls back to the raw decoded bytes when the message does not parse
    as an email (the caller still gets a parse attempt, not an error).
    """
    try:
        message: Message = email.parser.BytesParser(policy=email.policy.default).parsebytes(payload)
    except Exception:
        return "", "", payload.decode("utf-8", errors="replace")
    sender = str(message.get("From") or "")
    subject = str(message.get("Subject") or "")
    body = ""
    try:
        plain = message.get_body(preferencelist=("plain",))
        if plain is not None:
            body = plain.get_content()
        elif message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            content = message.get_content()
            if isinstance(content, str):
                body = content
    except Exception:
        body = ""
    if not body.strip():
        body = payload.decode("utf-8", errors="replace")
    return sender, subject, body


def _decode_upload(filename: str, payload: bytes) -> tuple[str, str, str]:
    """Return (sender, subject, body_text) for an uploaded file."""
    name = filename.lower()
    if name.endswith(".eml"):
        return _extract_eml_text(payload)
    if name.endswith((".txt", ".csv")):
        return "", "", payload.decode("utf-8", errors="replace")
    raise HTTPException(
        status_code=400,
        detail="only .eml, .txt and .csv files are supported",
    )


async def _read_inputs(request: Request) -> dict:
    """Read sender/subject/body_text/source/fx_rate from JSON or multipart.

    JSON: ``{"sender": ..., "subject": ..., "body_text": ..., "source":
    "text"|"ocr", "fx_rate": ...}``.
    Multipart: file field ``file`` plus optional form fields ``sender``,
    ``subject``, ``source`` and ``fx_rate``.
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="request body is not valid JSON") from None
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON body must be an object") from None
        return {
            "sender": str(payload.get("sender") or ""),
            "subject": str(payload.get("subject") or ""),
            "body_text": payload.get("body_text"),
            "source": str(payload.get("source") or "text").lower(),
            "fx_rate": _parse_fx_rate(payload.get("fx_rate")),
        }
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not getattr(upload, "filename", ""):
            raise HTTPException(status_code=400, detail="file is required")
        filename = str(upload.filename)
        if not filename.lower().endswith(_SUPPORTED_EXTENSIONS):
            raise HTTPException(
                status_code=400,
                detail="only .eml, .txt and .csv files are supported",
            )
        payload = await upload.read()
        if len(payload) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=400, detail="uploaded file is too large")
        if not payload.strip():
            raise HTTPException(status_code=400, detail="uploaded file is empty")
        sender, subject, body_text = _decode_upload(filename, payload)
        # Form fields override anything extracted from the .eml headers.
        if form.get("sender"):
            sender = str(form.get("sender"))
        if form.get("subject"):
            subject = str(form.get("subject"))
        return {
            "sender": sender,
            "subject": subject,
            "body_text": body_text,
            "source": str(form.get("source") or "text").lower(),
            "fx_rate": _parse_fx_rate(form.get("fx_rate")),
        }
    raise HTTPException(
        status_code=400,
        detail="send JSON (application/json) or a file upload (multipart/form-data)",
    )


# ---------------------------------------------------------------------------
# Sender catalogue (derived from the parser module -- no new data)
# ---------------------------------------------------------------------------

def _quirks_from_docstring() -> dict[str, str]:
    """Per-company quirks, read from the parser module's own docstring.

    The module documents one bullet per sender quirk; a bullet that names
    several companies (BroadGrain / Richardson / P&H share one) is
    attributed to each company it names.  Nothing is invented here.
    """
    doc = email_bid_parser.__doc__ or ""
    bullets: list[str] = []
    current: list[str] = []
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped.startswith("* "):
            if current:
                bullets.append(" ".join(current))
            current = [stripped[2:].strip()]
        elif current and stripped and not stripped.startswith("Sender quirks"):
            current.append(stripped)
    if current:
        bullets.append(" ".join(current))
    quirks: dict[str, str] = {}
    for company, _markers in email_bid_parser._SENDER_COMPANIES:
        matched = [b for b in bullets if company.lower() in b.lower()]
        if matched:
            quirks[company] = " ".join(matched)
    return quirks


@router.get("/senders")
def list_senders() -> dict:
    """Supported email-bid sender companies and their parsing quirks.

    Company names, detection markers and quirks all come from
    ``app.services.email_bid_parser``; this endpoint adds no new data.
    """
    quirks = _quirks_from_docstring()
    senders = []
    for company, markers in email_bid_parser._SENDER_COMPANIES:
        quirk = quirks.get(company, "")
        senders.append(
            {
                "company": company,
                "markers": list(markers),
                "quirks": quirk,
                # Rows from this sender normally arrive as OCR text from an
                # inline bid-table image, rather than as plain email text.
                "input": "ocr" if "ocr" in quirk.lower() else "text",
            }
        )
    return {"senders": senders}


# ---------------------------------------------------------------------------
# Parse endpoint (parse-only: no DB writes, no sends)
# ---------------------------------------------------------------------------

@router.post("/parse")
async def parse_email_bids(
    request: Request,
    db: Session = Depends(get_db),  # accepted for parity with uploads; unused
) -> dict:
    """Parse pasted email text or an uploaded bid file. Preview only."""
    _ = db  # Deliberately unused: this endpoint never writes to the database.
    inputs = await _read_inputs(request)
    body_text = inputs["body_text"]
    if body_text is None or not str(body_text).strip():
        raise HTTPException(status_code=400, detail="body_text is required")
    body_text = str(body_text)
    source = inputs["source"]
    if source not in {"text", "ocr"}:
        raise HTTPException(status_code=400, detail="source must be 'text' or 'ocr'")
    sender = inputs["sender"]
    subject = inputs["subject"]
    fx_rate = inputs["fx_rate"]
    if source == "ocr":
        company = detect_sender_company(sender, subject, body_text)
        result = parse_ocr_bid_rows(
            body_text,
            company=None if company == "Unknown" else company,
            fx_rate=fx_rate,
        )
        result.sender = sender
        result.subject = subject
    else:
        result = parse_email_bid_text(
            sender, subject, body_text, fx_rate=fx_rate
        )
    return _result_to_dict(result, source=source)
