"""Commodity normalization tests (Marathon Phase B, 2026-11-20).

Covers the rule set in app.services.commodity_normalization against
the 25 commodity labels actually present in the live production
facets on 2026-11-20, the ambiguous labels the resolver refuses to
guess, the commodity_aliases DB override, and — against a real
SQLite database — the market-search filter expansion that lets the
query "HRW Wheat" find rows stored as "HRW New Crop Wheat" and
"HARD RED WINTER" (a plain substring search found none of them).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.routes.normalized_prices import _build_filters  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models.commodity_alias import CommodityAlias  # noqa: E402
from app.models.normalized_price import NormalizedPrice  # noqa: E402
from app.services.commodity_normalization import (  # noqa: E402
    canonical_display_name,
    known_ambiguous_labels,
    resolve_commodity_name,
    search_patterns_for_query,
)
from app.services.market_canonicalization import canonical_commodity_name  # noqa: E402


# The exact labels in the live facets snapshot
# (docs/marathon/snapshots/facets.json, 2026-11-20) and the display
# name each must resolve to.
LIVE_LABELS = {
    "#2 Yellow Corn": "Corn",
    "Corn": "Corn",
    "GLG Cash": "GLG Cash",  # ambiguous: program label, not a commodity
    "HARD RED WINTER": "HRW Wheat",
    "HRS New Crop Wheat": "HRS Wheat (New Crop)",
    "HRS Old Crop Wheat": "HRS Wheat (Old Crop)",
    "HRW New Crop Wheat": "HRW Wheat (New Crop)",
    "HRW Old Crop Wheat": "HRW Wheat (Old Crop)",
    "Hard Red Spring Wheat": "HRS Wheat",
    "Hard Red Wheat": "Hard Red Wheat",  # ambiguous: season unstated
    "Hard Red Winter Wheat": "HRW Wheat",
    "SRW New Crop Wheat": "SRW Wheat (New Crop)",
    "SRW Old Crop Wheat": "SRW Wheat (Old Crop)",
    "SWW New Crop Wheat": "White Wheat (New Crop)",
    "SWW Old Crop Wheat": "White Wheat (Old Crop)",
    "Soft Red Wheat": "SRW Wheat",
    "Soft Red Winter Wheat": "SRW Wheat",
    "Soft White Wheat": "White Wheat",
    "Soft White Winter Wheat": "White Wheat",
    "Soybeans": "Soybeans",
    "WHEAT, HRS": "HRS Wheat",
    "WHEAT, HRW": "HRW Wheat",
    "WHEAT, SRW": "SRW Wheat",
    "Wheat": "Wheat",  # ambiguous: class unstated, label kept as-is
    "White Wheat": "White Wheat",
}


def test_every_live_label_resolves_as_expected() -> None:
    for raw, expected_display in LIVE_LABELS.items():
        assert canonical_display_name(raw) == expected_display, raw


def test_live_labels_collapse_to_canonical_groups() -> None:
    groups = {}
    for raw in LIVE_LABELS:
        resolution = resolve_commodity_name(raw)
        assert resolution is not None
        if resolution.canonical is not None:
            groups.setdefault(resolution.canonical, []).append(raw)
    assert set(groups) == {
        "Corn",
        "Soybeans",
        "HRW Wheat",
        "HRS Wheat",
        "SRW Wheat",
        "White Wheat",
    }
    assert len(groups["Corn"]) == 2
    assert len(groups["HRW Wheat"]) == 5


def test_ambiguous_labels_are_flagged_not_guessed() -> None:
    for raw in ("Wheat", "Hard Red Wheat", "GLG Cash"):
        resolution = resolve_commodity_name(raw)
        assert resolution is not None
        assert resolution.canonical is None, raw
        assert resolution.ambiguous is True, raw
        assert resolution.reason, raw
    assert set(known_ambiguous_labels()) >= {"wheat", "hard red wheat", "glg cash"}


def test_crop_tag_is_extracted_and_preserved() -> None:
    resolution = resolve_commodity_name("srw old crop wheat")
    assert resolution is not None
    assert resolution.canonical == "SRW Wheat"
    assert resolution.crop_tag == "old"
    assert resolution.display_name == "SRW Wheat (Old Crop)"


def test_unrecognized_label_passes_through_unmapped() -> None:
    resolution = resolve_commodity_name("Purple Hulled Peas")
    assert resolution is not None
    assert resolution.canonical is None
    assert resolution.ambiguous is False
    assert canonical_display_name("Purple Hulled Peas") == "Purple Hulled Peas"


def test_empty_and_null_like_inputs() -> None:
    assert resolve_commodity_name(None) is None
    assert resolve_commodity_name("") is None
    assert resolve_commodity_name("nan") is None
    assert canonical_display_name(None) is None


def test_legacy_canonical_commodity_name_behaviour_kept() -> None:
    # The pre-Phase-B aliases must not regress: facets and preview
    # display have routed through this function since Cycle 1.
    assert canonical_commodity_name("corn") == "Corn"
    assert canonical_commodity_name("soybean") == "Soybeans"
    assert canonical_commodity_name("white corn") == "White Corn"
    assert canonical_commodity_name("Wheat") == "Wheat"
    assert canonical_commodity_name("HRW New Crop Wheat") == "HRW Wheat (New Crop)"


def test_search_patterns_expand_canonical_queries() -> None:
    assert search_patterns_for_query("HRW Wheat") == ("hrw", "hard red winter")
    assert search_patterns_for_query("Hard Red Winter Wheat") == ("hrw", "hard red winter")
    assert search_patterns_for_query("Corn") == ("corn",)
    assert search_patterns_for_query("Soybeans") == ("soybean",)
    # Ambiguous / unknown / free-text queries do not expand.
    assert search_patterns_for_query("Wheat") is None
    assert search_patterns_for_query("Hard Red Wheat") is None
    assert search_patterns_for_query("some free text") is None
    assert search_patterns_for_query(None) is None


def _alias_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["commodity_aliases"].create(bind=engine)
    return Session(bind=engine)


def test_database_override_wins_over_rules_and_ambiguity() -> None:
    session = _alias_session()
    try:
        session.add(
            CommodityAlias(
                raw_name="Hard Red Wheat",
                canonical_name="HRS Wheat",
                crop_tag=None,
                note="Pinned by operator for the test source.",
            )
        )
        session.commit()
        resolution = resolve_commodity_name("Hard Red Wheat", db=session)
        assert resolution is not None
        assert resolution.canonical == "HRS Wheat"
        # Without the session, the same label stays unmapped.
        without_db = resolve_commodity_name("Hard Red Wheat")
        assert without_db is not None and without_db.canonical is None
    finally:
        session.close()


def _price_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.tables["normalized_prices"].create(bind=engine)
    session = Session(bind=engine)
    snapshot_id = uuid.uuid4()
    for index, name in enumerate(
        ["HRW New Crop Wheat", "HARD RED WINTER", "HRS Old Crop Wheat", "Corn", "#2 Yellow Corn"]
    ):
        session.add(
            NormalizedPrice(
                id=uuid.uuid4(),
                snapshot_id=snapshot_id,
                location="Testville",
                commodity_name=name,
                composite_key=f"key-{index}",
            )
        )
    session.commit()
    return session


def _names_matching(session: Session, commodity_query: str) -> list[str]:
    filters = _build_filters(
        commodity=commodity_query,
        location=None,
        source_name=None,
        region=None,
        captured_date=None,
    )
    rows = session.execute(
        select(NormalizedPrice.commodity_name).where(*filters)
    ).scalars().all()
    return sorted(rows)


def test_search_filter_finds_hrw_rows_by_canonical_name() -> None:
    session = _price_session()
    try:
        # The headline Phase B bug: before the expansion, both of
        # these queries returned zero rows against this data.
        assert _names_matching(session, "HRW Wheat") == [
            "HARD RED WINTER",
            "HRW New Crop Wheat",
        ]
        assert _names_matching(session, "Hard Red Winter Wheat") == [
            "HARD RED WINTER",
            "HRW New Crop Wheat",
        ]
        assert _names_matching(session, "HRS Wheat") == ["HRS Old Crop Wheat"]
    finally:
        session.close()


def test_search_filter_corn_and_free_text_behave_as_before() -> None:
    session = _price_session()
    try:
        assert _names_matching(session, "Corn") == ["#2 Yellow Corn", "Corn"]
        # Unresolvable queries keep the legacy substring behaviour.
        assert _names_matching(session, "Crop Wheat") == [
            "HRS Old Crop Wheat",
            "HRW New Crop Wheat",
        ]
    finally:
        session.close()
