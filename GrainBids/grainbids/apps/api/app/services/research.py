"""USDA / official-report research collectors (Research silo v1).

Design, from the super plan:
- NASS Quick Stats and FAS PSD are key-gated free APIs. With no key
  configured they raise ``ResearchKeyRequired`` and never call the API.
- WASDE / Crop Progress / Grain Stocks are public downloads, not an
  API. ``ingest_public_file`` downloads a caller-supplied official
  URL (or accepts supplied text) and parses only what it can find,
  recording source + vintage on every row. It never invents a number:
  a value that is not in the file is simply absent.
- All network calls use a contact User-Agent, a timeout, and honour
  HTTP 429 by raising ``ResearchUpstreamError`` (the caller backs off).
"""

from __future__ import annotations

from dataclasses import dataclass
import re

import requests

from app.core.config import settings

NASS_BASE_URL = "https://quickstats.nass.usda.gov/api"
FAS_PSD_BASE_URL = "https://api.fas.usda.gov/api/psd"

# Official USDA download locations, configurable per call. These are
# the public ESMIS / usda.gov release files; if USDA moves a file the
# ingest records the failure honestly instead of guessing.
WASDE_TXT_URL = "https://www.usda.gov/sites/default/files/documents/wasde.txt"
CROP_PROGRESS_URL = "https://downloads.usda.gov/esmis/nass-crop-progress/crop-progress.txt"

REPORT_TYPES = ("wasde", "crop_progress", "grain_stocks", "export_sales", "crop_production", "commitments_of_traders")


class ResearchKeyRequired(RuntimeError):
    """A key-gated collector was called without its API key configured."""


class ResearchUpstreamError(RuntimeError):
    """The upstream source failed, rate-limited, or returned bad data."""


@dataclass(frozen=True)
class ResearchStatus:
    nass_configured: bool
    fas_configured: bool
    wasde_file_url: str
    crop_progress_file_url: str


def research_status() -> ResearchStatus:
    return ResearchStatus(
        nass_configured=bool(settings.nass_api_key.strip()),
        fas_configured=bool(settings.fas_data_gov_api_key.strip()),
        wasde_file_url=WASDE_TXT_URL,
        crop_progress_file_url=CROP_PROGRESS_URL,
    )


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.research_user_agent, "Accept": "application/json, text/plain"}


def _get_json(url: str, *, params: dict[str, str]) -> dict:
    try:
        response = requests.get(
            url,
            params=params,
            headers=_headers(),
            timeout=settings.research_http_timeout_seconds,
        )
    except requests.RequestException as exc:
        raise ResearchUpstreamError(f"Request to {url} failed: {exc}") from exc
    if response.status_code == 429:
        raise ResearchUpstreamError(f"Rate limited (429) by {url}; back off and retry later.")
    if response.status_code >= 400:
        raise ResearchUpstreamError(f"Upstream {url} returned HTTP {response.status_code}.")
    try:
        return response.json()
    except ValueError as exc:
        raise ResearchUpstreamError(f"Upstream {url} did not return JSON.") from exc


def fetch_nass_quick_stats(
    *,
    commodity: str,
    year: int,
    api_key: str | None = None,
) -> list[dict[str, object]]:
    """Fetch NASS Quick Stats records for one commodity/year.

    Raises ResearchKeyRequired when no key is configured. Returns the
    raw ``data`` records from Quick Stats (up to 50,000 per request).
    """
    key = (api_key if api_key is not None else settings.nass_api_key).strip()
    if not key:
        raise ResearchKeyRequired(
            "NASS Quick Stats needs a free API key (NASS_API_KEY). "
            "Get one at https://quickstats.nass.usda.gov/api — no key is stored in git."
        )
    payload = _get_json(
        f"{NASS_BASE_URL}/api_GET/",
        params={
            "key": key,
            "format": "JSON",
            "commodity_desc": commodity,
            "year": str(year),
        },
    )
    records = payload.get("data")
    if not isinstance(records, list):
        raise ResearchUpstreamError("NASS Quick Stats returned an unexpected payload.")
    return records


def parse_nass_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Normalise Quick Stats records to the fields the dashboard needs."""
    output: list[dict[str, object]] = []
    for record in records:
        output.append(
            {
                "commodity": record.get("commodity_desc"),
                "statistic": record.get("statisticcat_desc"),
                "year": record.get("year"),
                "state": record.get("state_name"),
                "county": record.get("county_name"),
                "value": record.get("Value"),
                "unit": record.get("unit_desc"),
                "source": "USDA NASS Quick Stats",
            }
        )
    return output


def fetch_fas_psd(
    *,
    commodity_code: str,
    api_key: str | None = None,
) -> list[dict[str, object]]:
    """Fetch FAS PSD (Production, Supply & Distribution) rows.

    Key-gated via a free data.gov key (FAS_DATA_GOV_API_KEY, header
    ``X-Api-Key``). Raises ResearchKeyRequired when unconfigured.
    """
    key = (api_key if api_key is not None else settings.fas_data_gov_api_key).strip()
    if not key:
        raise ResearchKeyRequired(
            "FAS PSD needs a free data.gov API key (FAS_DATA_GOV_API_KEY). "
            "Get one at https://api.data.gov/signup/ — no key is stored in git."
        )
    try:
        response = requests.get(
            f"{FAS_PSD_BASE_URL}/commodities",
            params={"commodityCode": commodity_code},
            headers={**_headers(), "X-Api-Key": key},
            timeout=settings.research_http_timeout_seconds,
        )
    except requests.RequestException as exc:
        raise ResearchUpstreamError(f"Request to FAS PSD failed: {exc}") from exc
    if response.status_code == 429:
        raise ResearchUpstreamError("Rate limited (429) by FAS PSD; back off and retry later.")
    if response.status_code >= 400:
        raise ResearchUpstreamError(f"FAS PSD returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ResearchUpstreamError("FAS PSD did not return JSON.") from exc
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ResearchUpstreamError("FAS PSD returned an unexpected payload.")


def fetch_public_file_text(url: str) -> str:
    """Download a public official report file (WASDE / Crop Progress / Grain Stocks)."""
    try:
        response = requests.get(
            url, headers=_headers(), timeout=settings.research_http_timeout_seconds
        )
    except requests.RequestException as exc:
        raise ResearchUpstreamError(f"Download of {url} failed: {exc}") from exc
    if response.status_code == 429:
        raise ResearchUpstreamError(f"Rate limited (429) by {url}; back off and retry later.")
    if response.status_code >= 400:
        raise ResearchUpstreamError(f"Download of {url} returned HTTP {response.status_code}.")
    return response.text


def parse_wasde_text(text: str) -> list[dict[str, object]]:
    """Extract US ending-stocks lines from a WASDE text file.

    Only values actually present in the text are returned. The WASDE
    tables label ending stocks per commodity; this parser looks for
    lines of the form ``Ending stocks <value>`` inside a commodity
    section headed by e.g. ``U.S. Corn Supply and Use``. If the file
    format changes, the parser returns what it found (possibly
    nothing) rather than guessing.
    """
    output: list[dict[str, object]] = []
    current_commodity: str | None = None
    for line in text.splitlines():
        heading = re.match(r"U\.S\.\s+(Corn|Soybeans|Wheat|Rice|Cotton)\s+Supply and Use", line, re.IGNORECASE)
        if heading:
            current_commodity = heading.group(1).title()
            continue
        if current_commodity is None:
            continue
        match = re.match(r"\s*Ending stocks\s+([\d,]+\.?\d*)\s*$", line)
        if match:
            output.append(
                {
                    "commodity": current_commodity,
                    "metric": "ending_stocks",
                    "value": match.group(1).replace(",", ""),
                    "unit": "million bushels",
                    "source": "USDA WASDE",
                }
            )
    return output


def parse_crop_progress_text(text: str) -> list[dict[str, object]]:
    """Extract national harvest/planting percentages from a Crop Progress text file.

    Looks for lines like ``Corn harvested 88`` (percent complete).
    Only values present in the text are returned.
    """
    output: list[dict[str, object]] = []
    for line in text.splitlines():
        match = re.match(
            r"\s*(Corn|Soybeans|Winter wheat|Spring wheat|Oats|Barley|Sorghum)\s+"
            r"(planted|emerged|harvested|silking|dough|dented|mature|condition)\s+(\d+(?:\.\d+)?)\s*$",
            line,
            re.IGNORECASE,
        )
        if match:
            output.append(
                {
                    "commodity": match.group(1).title(),
                    "metric": match.group(2).lower(),
                    "value": match.group(3),
                    "unit": "percent",
                    "source": "USDA NASS Crop Progress",
                }
            )
    return output
