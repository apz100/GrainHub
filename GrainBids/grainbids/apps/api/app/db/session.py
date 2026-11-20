from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def normalize_database_url(url: str) -> str:
    """Pin the psycopg v3 driver for bare Postgres URLs.

    requirements.txt ships psycopg v3 (``psycopg[binary]``), but a bare
    ``postgresql://`` URL makes SQLAlchemy select the psycopg2 dialect,
    which is not installed — the app crashed on boot on Render with
    ``ModuleNotFoundError: No module named 'psycopg2'`` (first deploy,
    2026-11-19). Providers hand out bare URLs, so normalize here.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy apps/api/.env.example to apps/api/.env and set DATABASE_URL."
            )
        # Supabase transaction pooler (PgBouncer) is incompatible with psycopg prepared statements.
        _engine = create_engine(
            normalize_database_url(settings.database_url),
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
        )
    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
