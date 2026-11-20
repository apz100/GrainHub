"""Canonical commodity resolution (Marathon Phase B, 2026-11-20).

Cash-bid sources name the same commodity many ways. The live
production facets on 2026-11-20 carried 25 distinct commodity labels
(``#2 Yellow Corn``, ``HARD RED WINTER``, ``HRW New Crop Wheat``,
``WHEAT, SRW`` ...) that collapse to a handful of canonical
commodities. Before this module, ``canonical_commodity_name`` knew
five aliases and passed everything else through, so facets fragmented
and market search — a raw ILIKE substring match — could not find
``HRW New Crop Wheat`` rows for the query ``HRW Wheat`` at all.

Design:

- Rules first. ``resolve_commodity_name`` normalizes a raw label,
  extracts a crop tag (``new`` / ``old``) when the label carries one,
  and matches the remaining base against a conservative alias table.
  Only equivalences that are unambiguous in North American grain
  trade usage are mapped.
- Ambiguity is data, not a guess. Labels that cannot be resolved
  without inventing information (``Hard Red Wheat`` — spring or
  winter?; bare ``Wheat`` — which class?; ``GLG Cash`` — a program
  label, not a commodity) resolve to ``canonical=None`` and are
  listed in :data:`AMBIGUOUS_LABELS` with the reason. Callers fall
  back to the raw label for display, and the dry-run report job
  surfaces them for a human decision.
- Database overrides win. The ``commodity_aliases`` table (migration
  0020) lets an operator pin a raw label to a canonical name without
  a code change; ``resolve_commodity_name(..., db=session)`` checks
  it before the rules. Nothing writes to that table automatically.

The crop tag is preserved in the display name (``HRW Wheat
(New Crop)``) because new-crop and old-crop bids are commercially
different rows; grouping happens on the canonical base.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.services.market_canonicalization import normalize_text


@dataclass(frozen=True)
class CommodityResolution:
    raw: str
    canonical: str | None  # canonical base, e.g. "HRW Wheat"; None = unmapped
    crop_tag: str | None  # "new" | "old" | None
    ambiguous: bool
    reason: str | None  # why a label is ambiguous / unmapped

    @property
    def display_name(self) -> str:
        if self.canonical is None:
            return self.raw
        if self.crop_tag == "new":
            return f"{self.canonical} (New Crop)"
        if self.crop_tag == "old":
            return f"{self.canonical} (Old Crop)"
        return self.canonical


# Base-label aliases, keyed by the normalized (casefolded, tag-stripped,
# punctuation-light) form. Values are canonical base names.
_BASE_ALIASES: dict[str, str] = {
    # Corn
    "corn": "Corn",
    "yellow corn": "Corn",
    "#2 yellow corn": "Corn",
    "no 2 yellow corn": "Corn",
    "no. 2 yellow corn": "Corn",
    "white corn": "White Corn",
    # Soybeans
    "soybeans": "Soybeans",
    "soybean": "Soybeans",
    # Hard red winter wheat
    "hrw": "HRW Wheat",
    "hrw wheat": "HRW Wheat",
    "hard red winter": "HRW Wheat",
    "hard red winter wheat": "HRW Wheat",
    "wheat, hrw": "HRW Wheat",
    "wheat hrw": "HRW Wheat",
    # Hard red spring wheat
    "hrs": "HRS Wheat",
    "hrs wheat": "HRS Wheat",
    "hard red spring": "HRS Wheat",
    "hard red spring wheat": "HRS Wheat",
    "wheat, hrs": "HRS Wheat",
    "wheat hrs": "HRS Wheat",
    # Soft red winter wheat
    "srw": "SRW Wheat",
    "srw wheat": "SRW Wheat",
    "soft red": "SRW Wheat",
    "soft red wheat": "SRW Wheat",
    "soft red winter": "SRW Wheat",
    "soft red winter wheat": "SRW Wheat",
    "wheat, srw": "SRW Wheat",
    "wheat srw": "SRW Wheat",
    # Soft white wheat
    "sww": "White Wheat",
    "sww wheat": "White Wheat",
    "white wheat": "White Wheat",
    "soft white": "White Wheat",
    "soft white wheat": "White Wheat",
    "soft white winter": "White Wheat",
    "soft white winter wheat": "White Wheat",
    # Other grains that appear in the Ontario catalogue (barley/oats
    # are carried at Hensall HDC and Sunderland; canola is a standard
    # Ontario crop even though FMN carries no canola table).
    "barley": "Barley",
    "oats": "Oats",
    "oat": "Oats",
    "canola": "Canola",
    "rye": "Rye",
}

# Labels that must NOT be guessed. Keyed by normalized base form.
AMBIGUOUS_LABELS: dict[str, str] = {
    "wheat": "wheat class not stated (could be HRW, HRS, SRW or white)",
    "hard red wheat": "season not stated (hard red spring vs hard red winter)",
    "hard red": "season not stated (hard red spring vs hard red winter)",
    "red wheat": "class not stated (hard/soft, spring/winter unknown)",
    "glg cash": "program label, not a commodity name",
    "cash": "not a commodity name",
}

# Raw-substring patterns per canonical base, used to expand a
# canonical market-search query into the raw labels sources actually
# stored. Substrings are matched with ILIKE %pattern% against the raw
# commodity_name column, mirroring the existing source-name expansion
# in normalized_prices._canonical_source_filter_values.
SEARCH_PATTERNS: dict[str, tuple[str, ...]] = {
    "Corn": ("corn",),
    "White Corn": ("white corn",),
    "Soybeans": ("soybean",),
    "HRW Wheat": ("hrw", "hard red winter"),
    "HRS Wheat": ("hrs", "hard red spring"),
    "SRW Wheat": ("srw", "soft red"),
    "White Wheat": ("sww", "white wheat", "soft white"),
    "Barley": ("barley",),
    "Oats": ("oat",),
    "Canola": ("canola",),
    "Rye": ("rye",),
}

_CROP_TAG_RE = re.compile(r"\b(new|old)\s+crop\b", flags=re.IGNORECASE)


def _normalize_base(value: str) -> str:
    """Casefold, collapse whitespace, and normalize comma spacing."""
    base = re.sub(r"\s+", " ", value.strip().casefold())
    base = re.sub(r"\s*,\s*", ", ", base)
    return base


def split_crop_tag(normalized: str) -> tuple[str, str | None]:
    """Split a normalized label into (base, crop_tag)."""
    match = _CROP_TAG_RE.search(normalized)
    if match is None:
        return normalized, None
    tag = match.group(1).casefold()
    base = _normalize_base(_CROP_TAG_RE.sub(" ", normalized))
    return base, tag


def resolve_commodity_name(
    commodity_name: str | None,
    *,
    db: Session | None = None,
) -> CommodityResolution | None:
    """Resolve one raw commodity label to its canonical commodity.

    Returns None for empty/null-like input. A resolution with
    ``canonical=None`` means the label is known-ambiguous or simply
    unrecognized — callers should keep the raw label for display and
    never invent a mapping.
    """
    normalized = normalize_text(commodity_name)
    if normalized is None:
        return None

    if db is not None:
        override = _lookup_override(db, normalized)
        if override is not None:
            return override

    base, crop_tag = split_crop_tag(_normalize_base(normalized))
    if base in AMBIGUOUS_LABELS:
        return CommodityResolution(
            raw=normalized,
            canonical=None,
            crop_tag=crop_tag,
            ambiguous=True,
            reason=AMBIGUOUS_LABELS[base],
        )
    canonical = _BASE_ALIASES.get(base)
    if canonical is None:
        return CommodityResolution(
            raw=normalized,
            canonical=None,
            crop_tag=crop_tag,
            ambiguous=False,
            reason="no rule and no database override for this label",
        )
    return CommodityResolution(
        raw=normalized,
        canonical=canonical,
        crop_tag=crop_tag,
        ambiguous=False,
        reason=None,
    )


def _lookup_override(db: Session, raw: str) -> CommodityResolution | None:
    """Check the commodity_aliases override table for this raw label."""
    # Imported lazily: the model module must not be required for the
    # pure-rule path (scripts and tests use rules without a database).
    from app.models.commodity_alias import CommodityAlias

    row = db.get(CommodityAlias, raw)
    if row is None:
        # Overrides are keyed by the exact stored label; also try the
        # casefolded key so an operator entry survives case drift.
        from sqlalchemy import func, select

        row = db.execute(
            select(CommodityAlias).where(
                func.lower(CommodityAlias.raw_name) == raw.casefold()
            )
        ).scalars().first()
    if row is None:
        return None
    return CommodityResolution(
        raw=raw,
        canonical=row.canonical_name,
        crop_tag=row.crop_tag,
        ambiguous=False,
        reason=None,
    )


def canonical_display_name(commodity_name: str | None) -> str | None:
    """Display name for a raw label: canonical (+ crop tag) or raw."""
    resolution = resolve_commodity_name(commodity_name)
    if resolution is None:
        return None
    return resolution.display_name


def search_patterns_for_query(commodity_query: str | None) -> tuple[str, ...] | None:
    """Expand a user's commodity query to raw-label search patterns.

    Returns None when the query does not resolve to a canonical
    commodity — the caller then keeps its existing substring search,
    so free-text queries behave exactly as before.
    """
    resolution = resolve_commodity_name(commodity_query)
    if resolution is None or resolution.canonical is None:
        return None
    return SEARCH_PATTERNS.get(resolution.canonical)


def known_ambiguous_labels() -> dict[str, str]:
    """The labels this module refuses to guess, with reasons."""
    return dict(AMBIGUOUS_LABELS)
