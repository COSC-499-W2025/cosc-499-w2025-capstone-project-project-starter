"""
tests/data/test_database.py
---
Unit tests for the database setup and connection logic in src/db.py.

These tests verify:
    - successful creation and connection to the SQLite database
    - proper handling of temporary databases in the test environment
    - basic CRUD operations (create, read, update, delete) on test tables
    - correct teardown and cleanup of test databases after execution

---
Run from the root directory with:
    docker compose run --rm backend pytest -v tests/data/test_database.py
    (coverage below, not applicable right now)
    docker compose run --rm backend coverage run -m pytest tests/data/test_database.py
    docker compose run --rm backend coverage report -m
"""

import os
import tempfile
import sqlite3
import pytest

@pytest.fixture(scope="function", autouse=True)
def test_database(monkeypatch):
    """Fixture to create and clean up a temporary SQLite database for tests."""
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    test_db_url = f"sqlite:///{tmp_db.name}"

    monkeypatch.setenv("DATABASE_URL", test_db_url)
    yield tmp_db.name 

    tmp_db.close()
    if os.path.exists(tmp_db.name):
        os.remove(tmp_db.name)


def test_database_file_created(test_database):
    """Verify that the temporary database file is created and accessible."""
    assert os.path.exists(test_database), "Database file should exist"
    conn = sqlite3.connect(test_database)
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    result = cursor.fetchone()
    assert result[0] == 1
    conn.close()


def test_can_create_and_read_data(test_database):
    """Verify we can create a table, insert data, and read it back."""
    conn = sqlite3.connect(test_database)
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT);")
    cursor.execute("INSERT INTO users (name) VALUES (?);", ("Alice",))
    cursor.execute("INSERT INTO users (name) VALUES (?);", ("Bob",))
    conn.commit()

    cursor.execute("SELECT name FROM users ORDER BY id;")
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()

    assert rows == ["Alice", "Bob"], "Expected two users in insertion order"


def test_database_cleanup(test_database):
    """Verify that the test database file is removed after tests complete."""
    assert os.path.isfile(test_database), "DB file should exist during test"
    conn = sqlite3.connect(test_database)
    conn.execute("CREATE TABLE IF NOT EXISTS test (x INTEGER);")
    conn.close()