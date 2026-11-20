from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.daily_newsletter import router as daily_newsletter_router  # noqa: E402
from app.core.request_context import RequestContext, get_request_context  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.services import daily_newsletter as daily_module  # noqa: E402
from app.services.daily_newsletter import (  # noqa: E402
    daily_issue_key,
    delivery_dedup_key,
    generate_daily_draft,
    parse_draft_date,
)

DRAFT_DATE = date(2026, 11, 18)


def _bid(*, cash: float, basis: float | None, location: str, company: str = "Test Elevator Co.") -> dict[str, object]:
    return {
        "cash_price_bu": cash,
        "basis": basis,
        "location": location,
        "company_name": company,
        "delivery_label": "November 2026",
        "futures_month": "Dec 2026",
        "captured_at": "2026-11-18T13:00:00+00:00",
    }


def _price_rows() -> dict[str, list[dict[str, object]]]:
    return {
        "Corn": [
            _bid(cash=5.45, basis=1.30, location="Testville"),
            _bid(cash=5.15, basis=1.10, location="Sampletown"),
        ],
        "Soybeans": [_bid(cash=12.10, basis=0.85, location="Demoville")],
        "Wheat": [],
    }


def _wasde_row(*, report_date: str = "2026-11-18") -> dict[str, object]:
    return {
        "report_type": "wasde",
        "commodity": "Corn",
        "report_date": report_date,
        "vintage": report_date,
        "source": "USDA WASDE",
        "payload": {"values": [{"commodity": "Corn", "metric": "ending_stocks", "value": "1758", "unit": "million bushels"}]},
    }


class _EmptyResult:
    def all(self):
        return []

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return None


class _EmptySession:
    """Fake DB with no rows at all: every query comes back empty."""

    def execute(self, _query):
        return _EmptyResult()


class _StrictSession:
    """Fake DB that must never be touched (all data is injected)."""

    def execute(self, _query):
        raise AssertionError("database should not be touched when all data is injected")


def _test_app(db) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(daily_newsletter_router)
    org_id = uuid.uuid4()

    def override_db():
        yield db

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_request_context] = lambda: RequestContext(
        org_id=org_id, user_email=None, user_role="member"
    )
    return TestClient(test_app)


class DailyNewsletterDraftTests(unittest.TestCase):
    def test_draft_with_prices_has_top_bids_and_subject(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            price_rows=_price_rows(),
            research_rows=[],
            upcoming_events=[],
            generated_at=datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(draft.issue_key, "daily-2026-11-18")
        self.assertIn("GrainHub Daily Newsletter", draft.subject)
        self.assertIn("November 18, 2026", draft.subject)
        top_bids = draft.sections[0]
        self.assertFalse(top_bids["empty"])
        corn = top_bids["commodities"][0]
        self.assertEqual(corn["commodity"], "Corn")
        self.assertEqual(corn["top_bids"][0]["location"], "Testville")
        self.assertIn("$5.45/bu", draft.text)
        self.assertIn("Preview only", draft.text)

    def test_draft_with_no_data_renders_explicit_empty_states(self) -> None:
        draft = generate_daily_draft(
            _EmptySession(),
            DRAFT_DATE,
            upcoming_events=[],
            generated_at=datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(all(section["empty"] for section in draft.sections))
        self.assertIn("No current bids were available for 2026-11-18", draft.text)
        self.assertIn("No basis data was available for 2026-11-18", draft.text)
        self.assertIn("No USDA report dated 2026-11-18 is on file", draft.text)
        self.assertIn("No upcoming report dates are on file", draft.text)
        # No invented numbers: the empty draft contains no prices at all.
        self.assertNotIn("/bu", draft.text)

    def test_draft_with_research_rows_shows_usda_today_only(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            price_rows={"Corn": [], "Soybeans": [], "Wheat": []},
            research_rows=[_wasde_row(), _wasde_row(report_date="2026-11-10")],
            upcoming_events=[],
        )

        usda = draft.sections[2]
        self.assertFalse(usda["empty"])
        self.assertEqual(len(usda["reports"]), 1)
        self.assertEqual(usda["reports"][0]["report_date"], "2026-11-18")
        self.assertIn("wasde", draft.text)
        self.assertIn("USDA WASDE", draft.text)
        self.assertNotIn("2026-11-10", draft.text)

    def test_dedup_key_format(self) -> None:
        self.assertEqual(daily_issue_key(date(2026, 11, 18)), "daily-2026-11-18")
        subscriber_id = uuid.uuid4()
        self.assertEqual(
            delivery_dedup_key(subscriber_id, "daily-2026-11-18"),
            f"{subscriber_id}:daily-2026-11-18",
        )

    def test_preview_does_not_send_and_needs_no_database(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            price_rows=_price_rows(),
            research_rows=[_wasde_row()],
            upcoming_events=[],
        )

        payload = draft.as_dict()
        self.assertFalse(payload["delivery"]["enabled"])
        self.assertFalse(payload["delivery"]["sent"])
        self.assertFalse(daily_module.DELIVERY_ENABLED)
        # No sending code in this module: no SMTP import, no send call,
        # no message construction. (The docstring may *mention* SMTP
        # in prose saying there is none — check code, not prose.)
        source = Path(daily_module.__file__).read_text()
        self.assertNotIn("smtp_sender", source)
        self.assertNotIn("send_smtp", source)
        self.assertNotIn("EmailMessage", source)

    def test_date_parsing(self) -> None:
        self.assertEqual(parse_draft_date("2026-11-18"), date(2026, 11, 18))
        self.assertEqual(parse_draft_date(None), datetime.now(timezone.utc).date())
        for bad in ("18/11/2026", "2026-13-01", "yesterday", "2026-11-18T00:00:00"):
            with self.assertRaises(ValueError, msg=bad):
                parse_draft_date(bad)

    def test_filter_by_commodity(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            commodity="corn",
            price_rows=_price_rows(),
            research_rows=[],
            upcoming_events=[],
        )

        top_bids = draft.sections[0]
        self.assertEqual([c["commodity"] for c in top_bids["commodities"]], ["Corn"])
        self.assertNotIn("Soybeans", draft.text)

    def test_subject_line_present(self) -> None:
        draft = generate_daily_draft(_EmptySession(), DRAFT_DATE)
        self.assertTrue(draft.subject)
        self.assertIn("2026", draft.subject)
        self.assertEqual(draft.as_dict()["subject"], draft.subject)
        self.assertEqual(draft.as_dict()["issue_key"], "daily-2026-11-18")

    def test_basis_movers_rank_snapshot_and_empty_without_basis(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(), DRAFT_DATE, price_rows=_price_rows(), research_rows=[], upcoming_events=[]
        )
        basis = draft.sections[1]
        self.assertFalse(basis["empty"])
        labels = [item["label"] for item in basis["items"]]
        self.assertEqual(labels, ["Strongest basis", "Weakest basis"])
        self.assertIn("not a day-over-day move", draft.text)

        no_basis = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            price_rows={"Corn": [_bid(cash=5.00, basis=None, location="Sampletown")], "Soybeans": [], "Wheat": []},
            research_rows=[],
            upcoming_events=[],
        )
        self.assertTrue(no_basis.sections[1]["empty"])
        self.assertIn("No basis data was available", no_basis.text)

    def test_upcoming_events_show_only_future_dates(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            price_rows={"Corn": [], "Soybeans": [], "Wheat": []},
            research_rows=[],
            upcoming_events=[
                {"name": "WASDE", "report_date": "2026-12-09", "source": "USDA"},
                {"name": "Old report", "report_date": "2026-11-01", "source": "USDA"},
            ],
        )
        upcoming = draft.sections[3]
        self.assertFalse(upcoming["empty"])
        self.assertEqual(len(upcoming["events"]), 1)
        self.assertIn("2026-12-09", draft.text)
        self.assertNotIn("Old report", draft.text)

    def test_upcoming_uses_verified_report_calendar_by_default(self) -> None:
        # No injected events: the draft loads the verified 2026 USDA
        # calendar. 2026-11-18 is a Wednesday, so Export Sales on
        # Thursday 2026-11-19 is the next event inside the 14-day window.
        draft = generate_daily_draft(_EmptySession(), DRAFT_DATE)
        upcoming = draft.sections[3]
        self.assertFalse(upcoming["empty"])
        names = [event["name"] for event in upcoming["events"]]
        self.assertIn("Export Sales", names)
        self.assertIn("2026-11-19", draft.text)
        self.assertNotIn("2026-11-12", draft.text)  # past WASDE stays out

    def test_upcoming_empty_state_for_year_without_verified_calendar(self) -> None:
        draft = generate_daily_draft(_EmptySession(), date(2027, 1, 5))
        upcoming = draft.sections[3]
        self.assertTrue(upcoming["empty"])
        self.assertIn("No upcoming report dates are on file for the next 14 days", draft.text)

    def test_location_filter_applies_to_injected_rows(self) -> None:
        draft = generate_daily_draft(
            _StrictSession(),
            DRAFT_DATE,
            location="testville",
            price_rows=_price_rows(),
            research_rows=[],
            upcoming_events=[],
        )
        corn = draft.sections[0]["commodities"][0]
        self.assertEqual([row["location"] for row in corn["top_bids"]], ["Testville"])
        self.assertNotIn("Sampletown", draft.text)


class DailyNewsletterRouteTests(unittest.TestCase):
    def test_get_daily_draft_preview_needs_no_subscriber(self) -> None:
        client = _test_app(_EmptySession())
        response = client.get("/api/newsletter/daily-draft?date=2026-11-18")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["issue_key"], "daily-2026-11-18")
        self.assertIn("GrainHub Daily Newsletter", payload["subject"])
        self.assertFalse(payload["delivery"]["enabled"])
        self.assertFalse(payload["delivery"]["sent"])
        # No prices / research on the fake DB, but the verified 2026
        # calendar still supplies upcoming events.
        self.assertTrue(payload["sections"][0]["empty"])
        self.assertTrue(payload["sections"][1]["empty"])
        self.assertTrue(payload["sections"][2]["empty"])
        self.assertFalse(payload["sections"][3]["empty"])

    def test_get_daily_draft_rejects_bad_date(self) -> None:
        client = _test_app(_EmptySession())
        response = client.get("/api/newsletter/daily-draft?date=not-a-date")
        self.assertEqual(response.status_code, 400)

    def test_post_preview_with_commodity_filter_and_prices(self) -> None:
        client = _test_app(_EmptySession())
        with (
            patch.object(daily_module, "_load_price_rows", return_value=_price_rows()),
            patch.object(daily_module, "_load_research_rows", return_value=[_wasde_row()]),
        ):
            response = client.post(
                "/api/newsletter/daily-draft/preview",
                json={"date": "2026-11-18", "commodity": "Corn"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        top_bids = payload["sections"][0]
        self.assertEqual([c["commodity"] for c in top_bids["commodities"]], ["Corn"])
        self.assertIn("$5.45/bu", payload["text"])
        self.assertFalse(payload["sections"][2]["empty"])

    def test_router_has_no_send_endpoint(self) -> None:
        paths = {route.path for route in daily_newsletter_router.routes}
        self.assertEqual(paths, {"/api/newsletter/daily-draft", "/api/newsletter/daily-draft/preview"})
        methods = {route.path: set(route.methods) for route in daily_newsletter_router.routes}
        self.assertEqual(methods["/api/newsletter/daily-draft"], {"GET"})
        self.assertEqual(methods["/api/newsletter/daily-draft/preview"], {"POST"})


if __name__ == "__main__":
    unittest.main()
