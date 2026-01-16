import os
import subprocess
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

from src.api.app import app


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        url = "postgresql+psycopg2://postgres:postgres@localhost:5432/artifactminer_test"
    return url


@pytest.fixture(scope="session")
def db_url() -> str:
    return _database_url()


@pytest.fixture(scope="session")
def migrated_db(db_url: str) -> None:
    """
    Ensures schema exists once per test session.
    We keep alembic_version; per-test cleanup truncates data only.
    """
    env = dict(os.environ)
    env["DATABASE_URL"] = db_url
    subprocess.check_call(["alembic", "upgrade", "head"], env=env)


@pytest.fixture()
def engine(migrated_db: None, db_url: str):
    eng = create_engine(db_url, future=True)
    return eng


def _truncate_all_tables(conn) -> None:
    conn.execute(
        text(
            """
            DO $$
            DECLARE r RECORD;
            BEGIN
              FOR r IN (
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> 'alembic_version'
              )
              LOOP
                EXECUTE format('TRUNCATE TABLE %I CASCADE', r.tablename);
              END LOOP;
            END $$;
            """
        )
    )


@pytest.fixture(autouse=True)
def clean_db(engine) -> Iterator[None]:
    # Clean slate before each test for determinism.
    with engine.begin() as conn:
        _truncate_all_tables(conn)
    yield
    # Clean after too (helps when a test fails mid-way).
    with engine.begin() as conn:
        _truncate_all_tables(conn)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
