"""USDA / official-report research collectors (Research silo v1).

Design, from the super plan:
- NASS Quick Stats and FAS PSD are key-gated free APIs. With no key
  configured they raise ``ResearchKeyRequired`` and never call the API.
- WASDE / Crop Progress / Grain Stocks are public downloads, not an
  API. ``ingest_public_file`` downloads a caller-supplied official
  URL (or accepts supplied text) and parses only what it can find,
  recording source + vintage on every row. It never invents a number:
  a value that is not in the file is simply absent.
- Grain Stocks is a quarterly NASS txt release on ESMIS. Each release
  has its own txt URL (see ``GRAIN_STOCKS_TXT_URL`` — the Sep 30 2026
  release, verified 2026-11-19); pass the current release's txt URL
  from the ESMIS Grain Stocks page. Only the "Domestic Units" summary
  table is parsed (on-farm / off-farm / total, latest year in the file).
- Crop Production is a monthly NASS txt release on ESMIS. Each release
  has its own txt URL (see ``CROP_PRODUCTION_TXT_URL`` — the Nov 10
  2026 release, verified 2026-11-19); pass the current release's txt
  URL from the ESMIS Crop Production page. Only the per-crop "Area
  Harvested, Yield, and Production - States and United States" tables
  are parsed (Corn for Grain, Sorghum for Grain, Soybeans for Beans,
  Rice — the four whose units were verified in the Nov 10 2026 file),
  and only their "United States" rows. A row with fewer than the
  expected 7 numbers (blank cells) is skipped, never positionally
  guessed.
  Environment (Socrata JSON, no key): the Legacy futures-only dataset
  ``6dca-aqww``. The historical zip (``deacotYYYY.zip``) returned HTTP
  403 to a plain GET on 2026-11-19, so the API is the supported route.
  The parser keeps only the latest report date present in the payload
  and only grain markets.
- Export Sales is read from the USDA AgTransport open-data mirror of
  FAS Export Sales Reporting (Socrata JSON, no key). The dataset is
  per-country rows with no TOTAL row (verified 2026-11-19), so the
  parser sums the country rows for the latest week-ending date in the
  payload. The canonical weekly report itself is a PDF, and the FAS
  ESR API is key-gated (data.gov key, same as FAS PSD) — neither is
  parsed here.
- All network calls use a contact User-Agent, a timeout, and honour
  HTTP 429 by raising ``ResearchUpstreamError`` (the caller backs off).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
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
# Grain Stocks txt URL is release-specific: this is the Sep 30 2026
# release, verified live 2026-11-19 (HTTP 200, 104,567 bytes).
# For a new quarter, take the current release's "- txt" link from
# https://esmis.nal.usda.gov/publication/grain-stocks
GRAIN_STOCKS_TXT_URL = "https://esmis.nal.usda.gov/sites/default/release-files/796087/grst0926_0.txt"
# Crop Production txt URL is release-specific: this is the Nov 10 2026
# release, verified live 2026-11-19 (HTTP 200, 161,866 bytes).
# For a new month, take the current release's "- txt" link from
# https://esmis.nal.usda.gov/publication/crop-production
CROP_PRODUCTION_TXT_URL = "https://esmis.nal.usda.gov/sites/default/release-files/796144/crop1126.txt"
# CFTC Public Reporting Environment (Socrata, no key): Legacy COT,
# futures only. Callers should request the latest week(s), e.g.
# ?$order=report_date_as_yyyy_mm_dd DESC&$limit=200
COT_LEGACY_API_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
# USDA AgTransport open-data mirror of FAS Export Sales Reporting
# (Socrata, no key). Per-country rows; callers should request the
# latest week, e.g. ?$order=date DESC&$limit=5000
EXPORT_SALES_API_URL = "https://agtransport.usda.gov/resource/wnn7-29tu.json"

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
    """Fetch the FAS PSD commodity catalogue (metadata, not PSD data).

    Key-gated via a free data.gov key (FAS_DATA_GOV_API_KEY, header
    ``X-Api-Key``). Raises ResearchKeyRequired when unconfigured.

    Despite the historical name, this returns the 63-row commodity
    list from ``/api/psd/commodities/`` — the server ignores the
    ``commodityCode`` query param and returns every commodity
    (verified live 2026-11-19/20), so the requested code is filtered
    client-side below. For actual Production, Supply & Distribution
    numbers use :func:`fetch_fas_psd_world`.
    """
    key = (api_key if api_key is not None else settings.fas_data_gov_api_key).strip()
    if not key:
        raise ResearchKeyRequired(
            "FAS PSD needs a free data.gov API key (FAS_DATA_GOV_API_KEY). "
            "Get one at https://api.data.gov/signup/ — no key is stored in git."
        )
    try:
        # Trailing slash is required: without it the FAS server returns
        # HTTP 500 (verified live 2026-11-19 with a real key, while the
        # slashed URL returns 200). Do not "clean up" the slash.
        response = requests.get(
            f"{FAS_PSD_BASE_URL}/commodities/",
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
        rows = payload
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ResearchUpstreamError("FAS PSD returned an unexpected payload.")
    # The server ignores the commodityCode param (see docstring), so
    # honour the caller's filter here. Rows without a commodityCode
    # are kept — dropping them would hide an upstream shape change.
    return [
        row
        for row in rows
        if not isinstance(row, dict)
        or row.get("commodityCode") in (None, commodity_code)
    ]


def _fas_psd_get_json(path: str, *, api_key: str | None) -> object:
    """GET one FAS PSD path and return the decoded JSON payload.

    Shared by the world-data and metadata fetchers below. Same key
    handling and error behaviour as :func:`fetch_fas_psd`.
    """
    key = (api_key if api_key is not None else settings.fas_data_gov_api_key).strip()
    if not key:
        raise ResearchKeyRequired(
            "FAS PSD needs a free data.gov API key (FAS_DATA_GOV_API_KEY). "
            "Get one at https://api.data.gov/signup/ — no key is stored in git."
        )
    try:
        response = requests.get(
            f"{FAS_PSD_BASE_URL}{path}",
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
        return response.json()
    except ValueError as exc:
        raise ResearchUpstreamError("FAS PSD did not return JSON.") from exc


def _fas_psd_rows(payload: object, *, what: str) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]
    raise ResearchUpstreamError(f"FAS PSD {what} returned an unexpected payload.")


def fetch_fas_psd_world(
    *,
    commodity_code: str,
    market_year: int,
    api_key: str | None = None,
) -> list[dict[str, object]]:
    """Fetch world PSD rows for one commodity + marketing year.

    Verified live 2026-11-20: the live shape is path segments —
    ``GET /api/psd/commodity/{code}/world/year/{marketYear}`` (corn
    0440000, year 2026 → 200, 15 rows). The legacy
    ``/api/psd/worldData`` route is dead (404 in every form tried).
    Rows are coded: ``attributeId`` / ``unitId`` need the lookups from
    :func:`fetch_fas_psd_attribute_names` / :func:`fetch_fas_psd_unit_names`;
    decode with :func:`parse_fas_psd_rows`. World rows carry
    ``countryCode == "00"``.
    """
    payload = _fas_psd_get_json(
        f"/commodity/{commodity_code}/world/year/{market_year}", api_key=api_key
    )
    return _fas_psd_rows(payload, what="world data")


def fetch_fas_psd_attribute_names(*, api_key: str | None = None) -> dict[int, str]:
    """Map PSD ``attributeId`` → attribute name (85 rows, live-verified).

    Never hardcode attribute ids from third-party docs — they do not
    match the live API (live: 20 = Beginning Stocks, 28 = Production,
    176 = Ending Stocks). Fetch this table and join at runtime.
    """
    rows = _fas_psd_rows(
        _fas_psd_get_json("/commodityAttributes/", api_key=api_key),
        what="commodity attributes",
    )
    return {
        int(row["attributeId"]): str(row["attributeName"])
        for row in rows
        if isinstance(row, dict) and row.get("attributeId") is not None
    }


def fetch_fas_psd_unit_names(*, api_key: str | None = None) -> dict[int, str]:
    """Map PSD ``unitId`` → unit description (42 rows, live-verified)."""
    rows = _fas_psd_rows(
        _fas_psd_get_json("/unitsOfMeasure/", api_key=api_key),
        what="units of measure",
    )
    return {
        int(row["unitId"]): str(row["unitDescription"])
        for row in rows
        if isinstance(row, dict) and row.get("unitId") is not None
    }


def parse_fas_psd_rows(
    rows: list[dict[str, object]],
    *,
    attribute_names: dict[int, str],
    unit_names: dict[int, str],
) -> list[dict[str, object]]:
    """Decode coded PSD rows into labelled rows (cf. parse_nass_records).

    Unknown ids fall back to ``attribute <id>`` / ``unit <id>`` rather
    than dropping the row, so an upstream table change stays visible.
    """
    output: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        attribute_id = row.get("attributeId")
        unit_id = row.get("unitId")
        output.append(
            {
                "commodity": row.get("commodityCode"),
                "metric": attribute_names.get(attribute_id, f"attribute {attribute_id}"),
                "value": row.get("value"),
                "unit": unit_names.get(unit_id, f"unit {unit_id}"),
                "market_year": row.get("marketYear"),
                "month": row.get("month"),
                "country_code": row.get("countryCode"),
                "source": "USDA FAS PSD",
            }
        )
    return output


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


_GRAIN_STOCKS_COMMODITIES = ("Corn", "Sorghum", "Oats", "Barley", "All wheat", "Durum wheat", "Soybeans")
_GRAIN_STOCKS_DATES = ("March 1", "June 1", "September 1", "December 1")


def parse_grain_stocks_text(text: str) -> list[dict[str, object]]:
    """Extract US total stocks from a Grain Stocks txt release.

    Parses only the "Grain Stocks by Position and Month in Domestic
    Units" summary table (1,000 bushels), for the latest year shown in
    that table's header, one row per commodity / position date / metric
    (total / on-farm / off-farm). A position date with no value for the
    latest year (blank cell — the estimation period has not begun) is
    simply absent. State tables and the metric-units table in the same
    file are ignored. Only values actually in the file are returned.
    """
    lines = text.splitlines()
    start: int | None = None
    end: int | None = None
    # Anchor on the table heading itself, not the table-of-contents entry
    # for the same table (which carries trailing dots + a page number).
    heading_pattern = re.compile(
        r"^Grain Stocks by Position and Month in Domestic Units - United States: \d{4} and \d{4}\s*$"
    )
    metric_pattern = re.compile(
        r"^Grain Stocks by Position and Month in Metric Units - United States: \d{4} and \d{4}\s*$"
    )
    for index, line in enumerate(lines):
        if start is None and heading_pattern.match(line.strip()):
            start = index
        elif start is not None and metric_pattern.match(line.strip()):
            end = index
            break
    if start is None:
        return []
    section = lines[start:end]

    years: list[int] = []
    for line in section:
        found = re.findall(r"\b(?:19|20)\d{2}\b", line)
        if len(found) >= 2:
            years = [int(year) for year in found]
            break
    if len(years) < 2:
        return []
    latest_year = max(years)
    latest_index = years.index(latest_year)

    commodity_pattern = re.compile(
        r"^(Corn|Sorghum|Oats|Barley|All wheat|Durum wheat|Soybeans)(?:\s+\d/)?\s*:\s*$"
    )
    row_pattern = re.compile(
        r"^(March 1|June 1|September 1|December 1)\s*\.+:\s*(.*?)\s*$"
    )
    number_pattern = re.compile(r"^[\d,]+$")

    output: list[dict[str, object]] = []
    current_commodity: str | None = None
    for line in section:
        heading = commodity_pattern.match(line.strip())
        if heading:
            current_commodity = heading.group(1).title()
            continue
        if current_commodity is None:
            continue
        row = row_pattern.match(line.strip())
        if not row:
            continue
        tokens = [token for token in row.group(2).split() if number_pattern.match(token)]
        # 6 numbers = both years (on, off, total per year); 3 = first year only.
        if len(tokens) == 6:
            triple = tokens[latest_index * 3 : latest_index * 3 + 3]
        elif len(tokens) == 3 and latest_index == 0:
            triple = tokens
        else:
            continue
        on_farm, off_farm, total = (value.replace(",", "") for value in triple)
        position_date = f"{row.group(1)}, {latest_year}"
        for metric, value in (
            ("total_stocks", total),
            ("on_farm_stocks", on_farm),
            ("off_farm_stocks", off_farm),
        ):
            output.append(
                {
                    "commodity": current_commodity,
                    "metric": metric,
                    "value": value,
                    "unit": "thousand bushels",
                    "position_date": position_date,
                    "source": "USDA NASS Grain Stocks",
                }
            )
    return output


# Crop Production per-crop tables with the 7-column United States row
# (area harvested prior/forecast year, yield prior/Oct 1/Nov 1,
# production prior/forecast year). Only these four tables were verified
# against the Nov 10 2026 release; other tables in the file (Peanut,
# Cotton by type, Sugarbeet, Potato, ...) have different column shapes
# and are deliberately not parsed.
_CROP_PRODUCTION_TABLES = {
    "Corn for Grain": "Corn",
    "Sorghum for Grain": "Sorghum",
    "Soybeans for Beans": "Soybeans",
    "Rice": "Rice",
}
_CROP_PRODUCTION_HEADING = re.compile(
    r"^(Corn for Grain|Sorghum for Grain|Soybeans for Beans|Rice)"
    r" Area Harvested, Yield, and Production - States and United States: (\d{4})"
)
_CROP_PRODUCTION_FORECAST = re.compile(
    r"Forecasted (\w+ 1, \d{4})"
)
_CROP_PRODUCTION_UNITS = re.compile(
    r"1,000 acres\s+-+\s*(\w+)\s+-+\s+.*?(1,000 [a-z]+)"
)
_CROP_PRODUCTION_US_ROW = re.compile(r"^United States\s*(?:\.+\s*)?:\s*(.*?)\s*$")
_CROP_PRODUCTION_NUMBER = re.compile(r"^[\d,]+(?:\.\d+)?$")


def parse_crop_production_text(text: str) -> list[dict[str, object]]:
    """Extract US area / yield / production from a Crop Production txt release.

    Parses only the per-crop "Area Harvested, Yield, and Production -
    States and United States" tables, and only their "United States"
    rows (7 numbers: area harvested prior year / forecast year, yield
    prior year / October 1 / November 1, production prior year /
    forecast year). The yield and production units are read from the
    table's own units line (bushels for corn/sorghum/soybeans, pounds
    and 1,000 cwt for rice). A United States row with fewer than 7
    numbers (blank cells — the estimation period has not begun) is
    skipped, never positionally guessed. State rows and the summary
    tables in the same file are ignored. Only values actually in the
    file are returned.
    """
    lines = text.splitlines()
    output: list[dict[str, object]] = []
    index = 0
    while index < len(lines):
        heading = _CROP_PRODUCTION_HEADING.match(lines[index].strip())
        if heading is None:
            index += 1
            continue
        crop_label, prior_year_text = heading.group(1), heading.group(2)
        commodity = _CROP_PRODUCTION_TABLES[crop_label]
        prior_year = int(prior_year_text)
        # The heading wraps across lines ("2025 and\nForecasted
        # November 1, 2026", or "2025 and Forecasted\nNovember 1,
        # 2026"), so search the heading plus the next two lines joined.
        forecast_date: str | None = None
        heading_window = " ".join(
            line.strip() for line in lines[index : index + 3]
        )
        match = _CROP_PRODUCTION_FORECAST.search(heading_window)
        if match:
            forecast_date = match.group(1)
        if forecast_date is None:
            index += 1
            continue
        forecast_year = int(forecast_date.rsplit(", ", 1)[1])
        # Scan the table body (bounded; stop at the next table heading).
        yield_unit: str | None = None
        production_unit: str | None = None
        us_numbers: list[str] | None = None
        scan = index + 1
        while scan < len(lines) and scan < index + 120:
            stripped = lines[scan].strip()
            if (
                scan > index + 1
                and " Area Harvested, Yield, and Production - States and United States:" in stripped
            ):
                break  # next table — never attribute its rows to this crop
            if yield_unit is None:
                units = _CROP_PRODUCTION_UNITS.search(stripped)
                if units:
                    yield_unit = f"{units.group(1)} per acre"
                    production_unit = units.group(2).replace("1,000", "thousand")
            us_row = _CROP_PRODUCTION_US_ROW.match(stripped)
            if us_row is not None:
                tokens = [
                    token
                    for token in us_row.group(1).split()
                    if _CROP_PRODUCTION_NUMBER.match(token)
                ]
                if len(tokens) == 7:
                    us_numbers = tokens
                break
            scan += 1
        index = scan + 1 if us_numbers is not None else scan
        if us_numbers is None or yield_unit is None or production_unit is None:
            continue
        area_prior, area_forecast, yield_prior, yield_oct1, yield_nov1, prod_prior, prod_forecast = (
            value.replace(",", "") for value in us_numbers
        )
        for metric, value, unit, year, forecast in (
            ("area_harvested", area_prior, "thousand acres", prior_year, None),
            ("area_harvested", area_forecast, "thousand acres", forecast_year, None),
            ("yield", yield_prior, yield_unit, prior_year, None),
            ("yield", yield_oct1, yield_unit, forecast_year, "October 1, " + str(forecast_year)),
            ("yield", yield_nov1, yield_unit, forecast_year, forecast_date),
            ("production", prod_prior, production_unit, prior_year, None),
            ("production", prod_forecast, production_unit, forecast_year, None),
        ):
            row: dict[str, object] = {
                "commodity": commodity,
                "metric": metric,
                "value": value,
                "unit": unit,
                "year": year,
                "forecast_date": forecast_date,
                "source": "USDA NASS Crop Production",
            }
            if forecast is not None:
                row["forecast"] = forecast
            output.append(row)
    return output


# Legacy COT futures-only markets that are grains. Keys are the# ``contract_market_name`` values in the CFTC Public Reporting
# Environment dataset; values are the display names used downstream.
_COT_GRAIN_MARKETS = {
    "CORN": "Corn",
    "SOYBEANS": "Soybeans",
    "SOYBEAN OIL": "Soybean Oil",
    "SOYBEAN MEAL": "Soybean Meal",
    "WHEAT-SRW": "Wheat (SRW)",
    "WHEAT-HRW": "Wheat (HRW)",
    "WHEAT-HRS": "Wheat (HRS)",
    "OATS": "Oats",
    "ROUGH RICE": "Rice",
}

_COT_METRICS = (
    ("open_interest", "open_interest_all"),
    ("noncommercial_long", "noncomm_positions_long_all"),
    ("noncommercial_short", "noncomm_positions_short_all"),
    ("noncommercial_spread", "noncomm_postions_spread_all"),
    ("commercial_long", "comm_positions_long_all"),
    ("commercial_short", "comm_positions_short_all"),
)


def parse_commitments_of_traders_text(text: str) -> list[dict[str, object]]:
    """Extract grain positioning from CFTC Legacy COT futures-only JSON.

    Input is the JSON text of the CFTC Public Reporting Environment
    Legacy futures-only dataset (``6dca-aqww``) — a list of records.
    Only grain markets are kept, and only rows from the latest report
    date present in the payload. Only fields actually present in a
    record are emitted (a missing field is skipped, never filled in).
    Note the upstream field name ``noncomm_postions_spread_all`` is
    misspelled in the source data; it is read as-is.
    """
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, list):
        return []

    rows: list[dict[str, object]] = []
    latest_date: str | None = None
    for record in payload:
        if not isinstance(record, dict):
            continue
        market = str(record.get("contract_market_name") or "").strip().upper()
        if market not in _COT_GRAIN_MARKETS:
            continue
        report_date = str(record.get("report_date_as_yyyy_mm_dd") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", report_date):
            continue
        if latest_date is None or report_date > latest_date:
            latest_date = report_date
        rows.append(record)
    if latest_date is None:
        return []

    output: list[dict[str, object]] = []
    for record in rows:
        if str(record.get("report_date_as_yyyy_mm_dd") or "")[:10] != latest_date:
            continue
        market = str(record.get("contract_market_name") or "").strip().upper()
        commodity = _COT_GRAIN_MARKETS[market]
        for metric, field in _COT_METRICS:
            raw = record.get(field)
            if raw is None or str(raw).strip() == "":
                continue
            output.append(
                {
                    "commodity": commodity,
                    "metric": metric,
                    "value": str(raw).strip().replace(",", ""),
                    "unit": "contracts",
                    "report_date": latest_date,
                    "market": str(record.get("market_and_exchange_names") or "").strip(),
                    "source": "CFTC Commitments of Traders",
                }
            )
    return output


# FAS Export Sales fields, current marketing year, summed across the
# per-country rows of the latest week in the payload. The dataset has
# no TOTAL row (verified 2026-11-19), so the sums are the national
# totals only when the caller supplies the full week's rows.
_EXPORT_SALES_METRICS = (
    ("net_sales", "netsalescmy"),
    ("weekly_exports", "wkexportscmy"),
    ("outstanding_sales", "outsalescmy"),
    ("total_commitments", "totcommcmy"),
)


def _parse_export_sales_number(raw: object) -> int | None:
    if raw is None:
        return None
    cleaned = str(raw).strip().replace(",", "")
    if not re.match(r"^-?\d+(\.\d+)?$", cleaned):
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def parse_export_sales_text(text: str) -> list[dict[str, object]]:
    """Extract weekly export-sales totals from FAS Export Sales JSON.

    Input is the JSON text of the USDA AgTransport open-data mirror of
    FAS Export Sales Reporting — a list of per-country rows. Only rows
    from the latest week-ending date present in the payload are used,
    and each metric is the sum of that field across the country rows
    for the commodity. A metric with no numeric value in any row is
    absent. Only values present in the payload are returned.
    """
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, list):
        return []

    dated_rows: list[tuple[str, dict[str, object]]] = []
    latest_date: str | None = None
    for record in payload:
        if not isinstance(record, dict):
            continue
        week_ending = str(record.get("date") or "")[:10]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", week_ending):
            continue
        if not str(record.get("commodity") or "").strip():
            continue
        if latest_date is None or week_ending > latest_date:
            latest_date = week_ending
        dated_rows.append((week_ending, record))
    if latest_date is None:
        return []

    totals: dict[str, dict[str, int]] = {}
    meta: dict[str, dict[str, str]] = {}
    for week_ending, record in dated_rows:
        if week_ending != latest_date:
            continue
        commodity = str(record.get("commodity") or "").strip().title()
        totals.setdefault(commodity, {})
        meta.setdefault(
            commodity,
            {
                "unit": str(record.get("unit") or "Metric Tons"),
                "marketing_year": str(record.get("myear") or ""),
            },
        )
        for metric, field in _EXPORT_SALES_METRICS:
            value = _parse_export_sales_number(record.get(field))
            if value is None:
                continue
            totals[commodity][metric] = totals[commodity].get(metric, 0) + value

    output: list[dict[str, object]] = []
    for commodity in sorted(totals):
        for metric, _field in _EXPORT_SALES_METRICS:
            if metric not in totals[commodity]:
                continue
            output.append(
                {
                    "commodity": commodity,
                    "metric": metric,
                    "value": str(totals[commodity][metric]),
                    "unit": meta[commodity]["unit"],
                    "week_ending": latest_date,
                    "marketing_year": meta[commodity]["marketing_year"],
                    "source": "USDA FAS Export Sales",
                }
            )
    return output
