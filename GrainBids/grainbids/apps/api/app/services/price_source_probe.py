"""Polite single-probe smoke test for verified price sources.

One GET per source, contact User-Agent, 30 s timeout, 2 s pause
between probes. Never records prices — only reachability and
whether bid content is present in the page. Live probing is a
manual/CLI operation, not part of the pytest suite (network tests
would be flaky); the pytest suite covers ``classify_status`` only.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

from app.core.config import settings

# Sample of verified sources (see docs/plans/price-source-catalogue.md).
# The full catalogue is the source of truth; this list is the smoke
# sample only.
SAMPLE_SOURCES: tuple[tuple[str, str], ...] = (
    ("AgriCharts FMN", "https://fmn1.agricharts.com/markets/cash.php"),
    ("Great Lakes Grain", "https://cashbids.greatlakesgrain.com/index.cfm"),
    ("LAC (new domain)", "https://www.londonag-dtn.com/index.cfm?show=11"),
    ("Andersons Canada", "https://dtn-api.andersonscanada.com/cash-bids/blacks-lane"),
    ("DG Global", "https://dgglobal.ca/cash-bids"),
    ("North Gower Grains", "https://northgowergrains.com/"),
    ("Collwest Grain", "https://www.collwestgrain.com/"),
    ("Mae-Mart Farms", "http://www.mae-martfarms.com/"),
    ("Mapleview Grain", "https://www.mapleviewgrain.ca/"),
)

BID_MARKERS = ("cash bid", "cash price", "cash bids")


@dataclass(frozen=True)
class ProbeResult:
    company: str
    url: str
    status: str  # live | dead | blocked | error
    http_status: int | None
    has_bid_content: bool
    note: str


def classify_status(http_status: int | None, body: str = "") -> tuple[str, bool]:
    """Classify one probe. ``body`` is only scanned for bid markers."""
    has_bid_content = any(marker in body.lower() for marker in BID_MARKERS)
    if http_status is None:
        return "error", False
    if http_status == 200:
        return "live", has_bid_content
    if http_status in (401, 403, 429):
        return "blocked", has_bid_content
    return "dead", has_bid_content


def probe_sources(
    sources: tuple[tuple[str, str], ...] = SAMPLE_SOURCES,
    *,
    pause_seconds: float = 2.0,
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    headers = {"User-Agent": settings.research_user_agent}
    for index, (company, url) in enumerate(sources):
        if index:
            time.sleep(pause_seconds)
        try:
            response = requests.get(
                url, headers=headers, timeout=settings.research_http_timeout_seconds
            )
            status, has_bid = classify_status(response.status_code, response.text[:50_000])
            results.append(
                ProbeResult(company, url, status, response.status_code, has_bid, "")
            )
        except requests.RequestException as exc:
            results.append(ProbeResult(company, url, "error", None, False, str(exc)))
    return results


def main() -> None:
    results = probe_sources()
    print(
        json.dumps(
            [
                {
                    "company": r.company,
                    "url": r.url,
                    "status": r.status,
                    "http_status": r.http_status,
                    "has_bid_content": r.has_bid_content,
                    "note": r.note,
                }
                for r in results
            ],
            indent=2,
        )
    )
    live = sum(1 for r in results if r.status == "live")
    print(f"\n{live}/{len(results)} live", flush=True)


if __name__ == "__main__":
    main()
