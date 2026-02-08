"""
test_config_manager.py
------------------------
Unit tests for the normalized SQLite-backed config_manager module.

Coverage highlights:
    - table schema creation
    - create/update/load flows for the new consent fields
    - wrapper helpers for legacy callers
    - CLI prompts enforcing LLM consent and alternative analysis text

Run from repo root:
    docker compose run --rm backend python3 -m pytest tests/config/test_config_manager.py -v
    docker compose run --rm backend pytest tests/config/test_config_manager.py --cov=src/config --cov-report=term-missing -v
"""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from src.config import config_manager


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------
@pytest.fixture
def temp_db(monkeypatch):
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    monkeypatch.setattr(config_manager, "DB_PATH", tmp_db.name)
    yield tmp_db.name
    tmp_db.close()
    if os.path.exists(tmp_db.name):
        os.remove(tmp_db.name)


@pytest.fixture
def manager(temp_db):
    return config_manager.UserConfigManager(db_path=temp_db)


# --------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------

def test_init_db_creates_table(manager, temp_db):
    manager.init_db()
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_configurations';"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_create_and_load_config_roundtrip(manager):
    created = manager.create_config(
        "test_user",
        "/tmp/data.zip",
        llm_consent=False,
        llm_consent_asked=True,
        data_access_consent=False,
    )
    assert created is True

    cfg = manager.load_config("test_user")
    assert cfg is not None
    assert cfg.zip_file == "/tmp/data.zip"
    assert cfg.llm_consent is False
    assert cfg.llm_consent_asked is True
    assert cfg.data_access_consent is False
    assert cfg.updated_at is None


def test_update_config_sets_updated_timestamp(manager):
    manager.create_config("user", "/tmp/a.zip", False, llm_consent_asked=True, data_access_consent=False)
    assert manager.update_config("user", llm_consent=True, llm_consent_asked=True, data_access_consent=True) is True

    cfg = manager.load_config("user")
    assert cfg.llm_consent is True
    assert cfg.llm_consent_asked is True
    assert cfg.data_access_consent is True
    assert cfg.updated_at is not None


def test_save_config_helper_upserts(manager):
    payload = {
        "zip_file": "/tmp/original.zip",
        "llm_consent": False,
        "llm_consent_asked": True,
        "data_access_consent": False,
    }
    assert config_manager.save_config_to_db(payload, "helper_user") is True

    second = {
        "zip_file": "/tmp/new.zip",
        "llm_consent": True,
        "llm_consent_asked": True,
        "data_access_consent": True,
    }
    assert config_manager.save_config_to_db(second, "helper_user") is True

    cfg = manager.load_config("helper_user")
    assert cfg.zip_file == "/tmp/new.zip"
    assert cfg.llm_consent is True
    assert cfg.llm_consent_asked is True
    assert cfg.data_access_consent is True
    assert cfg.updated_at is not None


def test_load_config_from_db_missing_returns_empty(manager, capsys):
    result = config_manager.load_config_from_db("missing")
    assert result == {}
    out = capsys.readouterr().out
    assert "No configuration" in out


def test_cli_save_prompts_and_stores(temp_db, monkeypatch, capsys):
    monkeypatch.setattr(config_manager, "DB_PATH", temp_db)

    responses = iter(["n", "y"])  # llm consent, opt-out confirm
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    args = [
        "prog",
        "--user-id",
        "cli_user",
        "--save",
        "--zip-file",
        "/tmp/cli.zip",
    ]
    with patch("sys.argv", args):
        config_manager.run_cli()
    out = capsys.readouterr().out

    assert "Privacy notice" in out
    assert "User is opting out of external LLM services" in out

    cfg = config_manager.UserConfigManager(db_path=temp_db).load_config("cli_user")
    assert cfg is not None
    assert cfg.zip_file == "/tmp/cli.zip"
    assert cfg.llm_consent is False


def test_cli_update_respects_defaults(temp_db, monkeypatch, capsys):
    monkeypatch.setattr(config_manager, "DB_PATH", temp_db)
    manager = config_manager.UserConfigManager(db_path=temp_db)
    manager.create_config("update_user", "/tmp/current.zip", True)

    responses = iter([""])  # keep existing llm consent
    monkeypatch.setattr("builtins.input", lambda _: next(responses))

    args = [
        "prog",
        "--user-id",
        "update_user",
        "--update",
        "--zip-file",
        "/tmp/updated.zip",
    ]
    with patch("sys.argv", args):
        config_manager.run_cli()
    out = capsys.readouterr().out
    assert "Config updated" in out

    cfg = manager.load_config("update_user")
    assert cfg.zip_file == "/tmp/updated.zip"
    assert cfg.llm_consent is True
    assert cfg.updated_at is not None


def test_cli_update_accepts_llm_consent_flag(temp_db, monkeypatch, capsys):
    monkeypatch.setattr(config_manager, "DB_PATH", temp_db)
    manager = config_manager.UserConfigManager(db_path=temp_db)
    manager.create_config("toggle_user", "/tmp/current.zip", True)

    args = [
        "prog",
        "--user-id",
        "toggle_user",
        "--update",
        "--zip-file",
        "/tmp/current.zip",
        "--llm-consent",
        "no",
    ]
    with patch("sys.argv", args):
        config_manager.run_cli()
    out = capsys.readouterr().out
    assert "Config updated" in out

    cfg = manager.load_config("toggle_user")
    assert cfg.llm_consent is False
