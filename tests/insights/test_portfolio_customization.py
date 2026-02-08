import os
import tempfile
import sqlite3
from typing import Dict, Any
import inspect
import httpx

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.insights.storage import ProjectInsightsStore
from src.insights.api import router

if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    _orig_httpx_init = httpx.Client.__init__

    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_init


def _mk_store(tmpdir: str) -> ProjectInsightsStore:
    db_path = os.path.join(tmpdir, "app.db")
    return ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")


def _insert_run_with_portfolio(store: ProjectInsightsStore, zip_path: str) -> None:
    payload: Dict[str, Any] = {
        "zip_metadata": {
            "root_name": os.path.basename(zip_path),
            "file_count": 1,
            "total_uncompressed_bytes": 10,
            "total_compressed_bytes": 5,
        },
        "projects": {
            "demo": {
                "categorized_contents": {"code": ["a.py"]},
                "portfolio_item": {
                    "tagline": "Initial Tagline",
                    "description": "Initial Description",
                    "project_type": "web",
                    "complexity": "medium",
                    "is_collaborative": False,
                    "summary": "Initial Summary",
                    "key_features": ["Feature A", "Feature B"],
                },
                "resume_item": {
                    "project_name": "demo",
                    "bullets": ["Did X", "Built Y"],
                },
            }
        },
    }
    stats = store.record_pipeline_run(zip_path, payload)
    assert stats.inserted == 1


def _get_any_project_info_id(db_path: str) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT id FROM project_info ORDER BY id DESC LIMIT 1;").fetchone()
        assert row is not None
        return int(row[0])


def test_patch_portfolio_customization_updates_fields_and_bullets():
    with tempfile.TemporaryDirectory() as td:
        store = _mk_store(td)
        _insert_run_with_portfolio(store, os.path.join(td, "z1.zip"))
        pid = _get_any_project_info_id(store.db_path)

        
        os.environ["DATABASE_URL"] = f"sqlite:///{store.db_path}"
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

       
        resp = client.patch(
            f"/insights/portfolio/{pid}",
            json={
                "portfolio_fields": {
                    "tagline": "New Tagline",
                    "description": "Refined Description",
                    "key_features": ["Improved A", "Added B"],
                    "is_collaborative": True,
                },
                "resume_bullets": ["Led migration", "Optimized pipeline"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "noop")

       
        updated = store.load_project_insight_by_id(pid)
        assert updated is not None
        p = updated["portfolio_item"]
        r = updated["resume_item"]
        assert p["tagline"] == "New Tagline"
        assert p["description"] == "Refined Description"
        assert p["is_collaborative"] is True
        assert p["key_features"] == ["Improved A", "Added B"]
        assert r["bullets"] == ["Led migration", "Optimized pipeline"]


def test_patch_portfolio_customization_404_for_unknown_id():
    with tempfile.TemporaryDirectory() as td:
        store = _mk_store(td)
        os.environ["DATABASE_URL"] = f"sqlite:///{store.db_path}"
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.patch(
            "/insights/portfolio/999999",
            json={"portfolio_fields": {"tagline": "T"}, "resume_bullets": ["A"]},
        )
        assert resp.status_code == 404
