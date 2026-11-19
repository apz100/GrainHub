#!/usr/bin/env python3
"""Sync ``config.toml`` ``[[us.elevators]]`` from ``us_elevators_urls.toml``.

``us_elevators_urls.toml`` is the canonical list of US elevator cash-bid
sources (name / url / type / enabled, in discovery order, with the audit
notes attached as comments). ``config.toml`` carries a copy of that list
under ``[us]`` for the legacy GrainBidder runner, and the two drifted apart
(Cycle 17 audit: config.toml had only 30 of the 121 entries, and 4 type
mismatches). This script regenerates the config.toml copy from the
canonical file so the two can never drift again without the guard test
(``tests/test_source_config_sync.py``) failing.

How it works
------------
* The ``[[us.elevators]]`` section of ``config.toml`` — from the first
  ``[[us.elevators]]`` line up to (but not including) the next top-level
  ``[section]`` header — is replaced wholesale.
* The replacement is the ``[[us.elevators]]`` span of
  ``us_elevators_urls.toml`` (first ``[[us.elevators]]`` line to end of
  file), transplanted verbatim, so entry order, comments and audit notes
  are a faithful copy of the canonical file.
* Everything else in ``config.toml`` is preserved byte-for-byte: the
  ``[paths]``, ``[sources]`` toggles, ``[posted_bid]`` and
  ``[notifications]`` sections, and every comment outside the replaced
  region. In particular the ``[sources]`` toggles are never touched.
* A header comment is prepended to the generated section stating it is
  generated from ``us_elevators_urls.toml`` by this script, with the date.

The script validates its own output before writing: both files must parse
as TOML, and the generated ``config.toml`` must parse with a
``[[us.elevators]]`` list identical (name / url / type / enabled, in
order) to the canonical file's. It refuses to write anything that fails
validation.

Usage
-----
    python scripts/sync_us_elevators_config.py           # rewrite config.toml
    python scripts/sync_us_elevators_config.py --check   # exit 1 if out of sync
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import tomllib
from pathlib import Path

SOURCES_DIR = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "platform"
    / "market_data"
    / "sources"
)
CONFIG_PATH = SOURCES_DIR / "config.toml"
URLS_PATH = SOURCES_DIR / "us_elevators_urls.toml"

ELEVATORS_MARKER = "[[us.elevators]]"

# First line of the generated header block (see generate_section).
GENERATED_HEADER_START = "# ── GENERATED — DO NOT EDIT BY HAND"

# Fields compared between the two files (the whole entry, in order).
ENTRY_FIELDS = ("name", "url", "type", "enabled")


def _elevator_span(text: str) -> str:
    """Text from the first ``[[us.elevators]]`` line to end of file.

    Line-anchored: the marker text also appears inside a comment in the
    urls file header ("Copy confirmed entries ... [[us.elevators]]"),
    so a plain substring search would start the span in the wrong place.
    """
    match = re.search(r"(?m)^\[\[us\.elevators\]\]", text)
    if match is None:
        raise ValueError(f"{ELEVATORS_MARKER} not found")
    return text[match.start():]


def _split_config(text: str) -> tuple[str, str, str]:
    """Split config.toml into (prefix, elevators section, suffix).

    Prefix is everything before the first ``[[us.elevators]]`` line
    (``[us]`` header included). Suffix starts at the next top-level
    ``[section]`` header after the elevators section. A generated header
    comment sitting directly above the first entry counts as part of the
    section, so it is replaced rather than duplicated on re-runs.
    """
    match = re.search(r"(?m)^\[\[us\.elevators\]\]", text)
    if match is None:
        raise ValueError(f"{ELEVATORS_MARKER} not found in config.toml")
    start = match.start()
    # The generated header comment belongs to the replaced section, not
    # the prefix: if one sits directly above the first entry (only comment
    # / blank lines between), start the section there so re-running the
    # script replaces it instead of duplicating it. Take the earliest such
    # header so a previously duplicated header is fully consumed.
    pos = 0
    while True:
        hdr = text.find(GENERATED_HEADER_START, pos, start)
        if hdr < 0:
            break
        if hdr > 0 and text[hdr - 1] != "\n":
            pos = hdr + 1
            continue
        between = text[hdr:start]
        if all(
            line.startswith("#") or line.strip() == ""
            for line in between.splitlines()
        ):
            start = hdr
            break
        pos = hdr + 1
    prefix = text[:start]
    rest = text[start:]
    suffix = ""
    offset = 0
    for line in rest.splitlines(keepends=True):
        if line.startswith("[") and not line.startswith("[["):
            suffix = rest[offset:]
            break
        offset += len(line)
    section = rest[: len(rest) - len(suffix)] if suffix else rest
    return prefix, section, suffix


def _elevators(data: dict) -> list[dict]:
    return data["us"]["elevators"]


def _check_match(config_elevators: list[dict], urls_elevators: list[dict]) -> list[str]:
    """Return a list of mismatch descriptions (empty when in sync)."""
    problems: list[str] = []
    if len(config_elevators) != len(urls_elevators):
        problems.append(
            f"entry count differs: config.toml has {len(config_elevators)}, "
            f"us_elevators_urls.toml has {len(urls_elevators)}"
        )
    for i, (cfg, src) in enumerate(zip(config_elevators, urls_elevators)):
        for field in ENTRY_FIELDS:
            if cfg.get(field) != src.get(field):
                problems.append(
                    f"entry {i} ({src.get('name')!r}): {field} differs: "
                    f"config.toml={cfg.get(field)!r} vs "
                    f"us_elevators_urls.toml={src.get(field)!r}"
                )
        extra = sorted(set(cfg) - set(ENTRY_FIELDS))
        if extra:
            problems.append(f"entry {i} ({src.get('name')!r}): extra fields in config.toml: {extra}")
    return problems


def generate_section(urls_text: str, when: datetime.date) -> str:
    """Build the generated ``[[us.elevators]]`` section for config.toml."""
    span = _elevator_span(urls_text).rstrip("\n") + "\n"
    header = (
        "# ── GENERATED — DO NOT EDIT BY HAND ──────────────────────────────────────\n"
        f"# Synced from us_elevators_urls.toml by scripts/sync_us_elevators_config.py\n"
        f"# on {when.isoformat()}. us_elevators_urls.toml is canonical: edit entries\n"
        "# there (name / url / type / enabled), then re-run this script.\n"
        "# The legacy GrainBidder runner reads this copy; entries whose type it\n"
        "# does not know (anything other than \"agricharts\" / \"dtn\") are skipped\n"
        "# with a [SKIP] line, so new types are safe to copy verbatim.\n"
        "# ─────────────────────────────────────────────────────────────────────────────\n"
        "\n"
    )
    # Trailing blank line: the section is followed directly by the next
    # top-level [section] header, so the section itself ends blank.
    return header + span + "\n"


def sync(*, check: bool = False) -> int:
    config_text = CONFIG_PATH.read_text(encoding="utf-8")
    urls_text = URLS_PATH.read_text(encoding="utf-8")

    try:
        urls_data = tomllib.loads(urls_text)
        config_data = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as exc:
        print(f"ERROR: TOML parse failed: {exc}", file=sys.stderr)
        return 2

    prefix, current_section, suffix = _split_config(config_text)

    if check:
        problems = _check_match(
            _elevators(config_data), _elevators(urls_data)
        )
        # The generated header carries today's date, so a section written
        # on an earlier date is still in sync: compare against a section
        # regenerated with the date stamped in the current header.
        stamped = re.search(r"on (\d{4}-\d{2}-\d{2})\.", current_section)
        when = (
            datetime.date.fromisoformat(stamped.group(1))
            if stamped
            else datetime.date.today()
        )
        if current_section != generate_section(urls_text, when):
            problems.append("generated [[us.elevators]] section text differs from config.toml")
        if problems:
            print("OUT OF SYNC:")
            for problem in problems:
                print(f"  - {problem}")
            print("Run: python scripts/sync_us_elevators_config.py")
            return 1
        print(
            f"IN SYNC: {len(_elevators(urls_data))} [[us.elevators]] entries "
            "match us_elevators_urls.toml"
        )
        return 0

    new_section = generate_section(urls_text, datetime.date.today())
    new_text = prefix + new_section + suffix

    # Validate the composed file before writing anything.
    try:
        new_data = tomllib.loads(new_text)
    except tomllib.TOMLDecodeError as exc:
        print(f"ERROR: generated config.toml would not parse: {exc}", file=sys.stderr)
        return 2
    problems = _check_match(_elevators(new_data), _elevators(urls_data))
    if problems:
        print("ERROR: generated config.toml does not match canonical list:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    if new_text[: len(prefix)] != prefix or not new_text.endswith(suffix):
        print("ERROR: content outside the [[us.elevators]] section changed", file=sys.stderr)
        return 2

    CONFIG_PATH.write_text(new_text, encoding="utf-8")
    print(
        f"Synced {len(_elevators(urls_data))} [[us.elevators]] entries from "
        f"{URLS_PATH.name} into {CONFIG_PATH.name}; "
        "everything outside the section is unchanged."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether config.toml is in sync; do not write",
    )
    args = parser.parse_args(argv)
    return sync(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
