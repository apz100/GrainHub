"""One-command registration of registry adapters as ``Source`` rows.

The admin endpoint ``POST /api/sources/seed`` already wraps
``seed_sources_from_registry``, but using it against production needs a
running server plus admin headers. This job is the operator equivalent
for the morning rollout step: point ``DATABASE_URL`` at the target
database and run one command.

    python -m app.jobs.seed_sources                 # the only org, scope=all
    python -m app.jobs.seed_sources --scope pilot   # just the pilot adapters
    python -m app.jobs.seed_sources --org-name "GrainBids Demo Org"
    python -m app.jobs.seed_sources --org-id <uuid> --dry-run

Behaviour:
- Idempotent: adapters that already have a ``Source`` row for the org
  are skipped (the service compares adapter keys), so re-running is
  safe and reports ``created=0``.
- Toggle-aware: adapters whose ``[sources]`` toggle is off in
  ``config.toml`` are not seeded and are listed as skipped_disabled.
- Org resolution: ``--org-id`` wins, then ``--org-name`` (exact match),
  then — only when the database holds exactly one organization — that
  organization. Anything ambiguous is an error (exit 2) that lists the
  organizations found; nothing is written on an error path.
- ``--dry-run`` reports what would be created and writes nothing.

Exit codes: 0 = seeded (or dry-run) successfully, 2 = org could not be
resolved unambiguously.
"""

from __future__ import annotations

import argparse
import sys
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_sessionmaker
from app.models.organization import Organization
from app.models.source import Source
from app.services.source_orchestration import seed_sources_from_registry
from app.services.source_registry import list_pilot_adapter_keys


def resolve_org(db: Session, *, org_id: str = "", org_name: str = "") -> Organization:
    """Resolve the target organization or raise ``LookupError``."""
    if org_id:
        try:
            parsed = uuid.UUID(org_id)
        except ValueError:
            raise LookupError(f"--org-id is not a valid UUID: {org_id!r}") from None
        org = db.get(Organization, parsed)
        if org is None:
            raise LookupError(f"no organization with id {parsed}")
        return org
    if org_name:
        matches = db.execute(
            select(Organization).where(Organization.name == org_name)
        ).scalars().all()
        if len(matches) != 1:
            raise LookupError(
                f"expected exactly one organization named {org_name!r}, found {len(matches)}"
            )
        return matches[0]
    orgs = db.execute(select(Organization).order_by(Organization.created_at.asc())).scalars().all()
    if len(orgs) == 1:
        return orgs[0]
    listing = ", ".join(f"{org.name} ({org.id})" for org in orgs) or "none"
    raise LookupError(
        f"cannot pick an organization automatically: found {len(orgs)} ({listing}); "
        "pass --org-id or --org-name"
    )


def run(
    db: Session,
    *,
    org_id: str = "",
    org_name: str = "",
    scope: str = "all",
    dry_run: bool = False,
) -> int:
    try:
        org = resolve_org(db, org_id=org_id, org_name=org_name)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    adapter_keys = list_pilot_adapter_keys() if scope == "pilot" else None
    result = seed_sources_from_registry(
        db, org_id=org.id, adapter_keys=adapter_keys, dry_run=dry_run
    )
    total = db.execute(
        select(func.count(Source.id)).where(Source.org_id == org.id)
    ).scalar_one()
    verb = "would create" if dry_run else "created"
    print(
        f"org={org.name} ({org.id}) scope={scope} {verb}={result.created} "
        f"skipped_disabled={len(result.skipped_disabled)} total_sources_for_org={total}"
    )
    if result.skipped_disabled:
        print(f"skipped_disabled_keys={','.join(result.skipped_disabled)}")
    if dry_run:
        print("dry_run=true — nothing was written")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed registry adapters as Source rows for one organization."
    )
    parser.add_argument("--org-id", type=str, default="", help="Organization UUID.")
    parser.add_argument("--org-name", type=str, default="", help="Organization name (exact match).")
    parser.add_argument(
        "--scope",
        choices=("all", "pilot"),
        default="all",
        help="Seed every enabled registry adapter (all) or only the pilot set (pilot).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be created without writing anything.",
    )
    args = parser.parse_args()

    db = get_sessionmaker()()
    try:
        return run(
            db,
            org_id=args.org_id,
            org_name=args.org_name,
            scope=args.scope,
            dry_run=args.dry_run,
        )
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
