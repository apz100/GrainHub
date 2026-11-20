"""Regression tests for the Render first-deploy crash (2026-11-19).

requirements.txt installs psycopg v3, but a bare postgresql:// URL made
SQLAlchemy import the psycopg2 dialect, which is not installed, so both
alembic and the app died on boot with ModuleNotFoundError: psycopg2.
normalize_database_url pins the installed v3 driver.
"""

from app.db.session import normalize_database_url


def test_bare_postgresql_url_gets_psycopg_v3_driver():
    assert (
        normalize_database_url("postgresql://postgres:pw@db.example.co:5432/postgres")
        == "postgresql+psycopg://postgres:pw@db.example.co:5432/postgres"
    )


def test_heroku_style_postgres_url_gets_psycopg_v3_driver():
    assert (
        normalize_database_url("postgres://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )


def test_already_pinned_url_unchanged():
    url = "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url(url) == url


def test_sqlite_url_unchanged():
    url = "sqlite:///./test.db"
    assert normalize_database_url(url) == url
