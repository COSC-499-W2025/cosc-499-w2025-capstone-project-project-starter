import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.insights.storage import ProjectInsightsStore
from src.insights.user_role_store import ProjectRoleStore, ROLE_TABLE, load_project_insight_with_role
from tests.insights.utils import build_pipeline_payload


def _seed_store(tmp_path):
    db_path = tmp_path / "insights.db"
    store = ProjectInsightsStore(db_path=str(db_path), encryption_key=b"test-key")
    payload = build_pipeline_payload()
    store.record_pipeline_run("/tmp/demo.zip", payload)
    zip_hash = store.list_recent_zipfiles(limit=1)[0]["zip_hash"]
    return store, ProjectRoleStore(db_path=str(db_path)), zip_hash


def test_set_user_role_persists_and_merges(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_ENCRYPTION_KEY", "test-key")
    store, role_store, zip_hash = _seed_store(tmp_path)

    ok = role_store.set_user_role(zip_hash, "ProjectAlpha", "Lead Developer")
    assert ok is True

    role = role_store.get_user_role(zip_hash, "ProjectAlpha")
    assert role == "Lead Developer"

    payload = load_project_insight_with_role(
        zip_hash,
        "ProjectAlpha",
        store=store,
        role_store=role_store,
    )
    assert payload["user_role"] == "Lead Developer"


def test_update_user_role_overwrites_value(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_ENCRYPTION_KEY", "test-key")
    _, role_store, zip_hash = _seed_store(tmp_path)

    role_store.set_user_role(zip_hash, "ProjectAlpha", "Backend Engineer")
    role_store.set_user_role(zip_hash, "ProjectAlpha", "Technical Lead")

    role = role_store.get_user_role(zip_hash, "ProjectAlpha")
    assert role == "Technical Lead"


def test_delete_project_removes_role(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_ENCRYPTION_KEY", "test-key")
    store, role_store, zip_hash = _seed_store(tmp_path)

    role_store.set_user_role(zip_hash, "ProjectAlpha", "QA Lead")
    store.delete_project(zip_hash, "ProjectAlpha")

    with sqlite3.connect(store.db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        remaining = conn.execute(
            f"SELECT COUNT(*) FROM {ROLE_TABLE};"
        ).fetchone()[0]
    assert remaining == 0
