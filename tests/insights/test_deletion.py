import os
import tempfile
import json
import sqlite3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import inspect

from src.insights.storage import ProjectInsightsStore
from src.insights.api import router

# Compatibility shim: older httpx versions don't accept the 'app' kwarg used by Starlette's TestClient
if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    _orig_httpx_init = httpx.Client.__init__

    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_init


def _mk_store(tmpdir):
    db_path = os.path.join(tmpdir, "app.db")
    return ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")


def _insert_dummy_run(store: ProjectInsightsStore, zip_path: str, projects: int = 2):
    payload = {
        "zip_metadata": {
            "root_name": os.path.basename(zip_path),
            "file_count": 10,
            "total_uncompressed_bytes": 1000,
            "total_compressed_bytes": 500,
        },
        "projects": {f"proj{i}": {"categorized_contents": {"code": ["a.py"]}} for i in range(projects)},
    }
    stats = store.record_pipeline_run(zip_path, payload)
    assert stats.inserted == projects
    return store


def test_storage_delete_all_zip_and_projects_counts():
    with tempfile.TemporaryDirectory() as td:
        s = _mk_store(td)
        _insert_dummy_run(s, os.path.join(td, "z1.zip"), projects=3)
        _insert_dummy_run(s, os.path.join(td, "z2.zip"), projects=1)

       
        with sqlite3.connect(s.db_path) as conn:
            z_before = conn.execute("SELECT COUNT(1) FROM ingest").fetchone()[0]
            p_before = conn.execute("SELECT COUNT(1) FROM project_info").fetchone()[0]
        assert z_before == 2 and p_before == 4

        out = s.delete_all()
        assert out["deleted_zips"] == 2
        assert out["deleted_projects"] == 4

   
        with sqlite3.connect(s.db_path) as conn:
            z_after = conn.execute("SELECT COUNT(1) FROM ingest").fetchone()[0]
            p_after = conn.execute("SELECT COUNT(1) FROM project_info").fetchone()[0]
        assert z_after == 0 and p_after == 0


def test_storage_delete_zip_and_project():
    with tempfile.TemporaryDirectory() as td:
        s = _mk_store(td)
        _insert_dummy_run(s, os.path.join(td, "z1.zip"), projects=2)
        _insert_dummy_run(s, os.path.join(td, "z2.zip"), projects=1)

        # Get a zip_hash to delete
        zips = s.list_recent_zipfiles(limit=10)
        assert len(zips) == 2
        target = zips[0]["zip_hash"]

        res = s.delete_zip(target)
        assert res["deleted_zips"] == 1
        # Remaining zip should still be present
        zips_after = s.list_recent_zipfiles(limit=10)
        assert len(zips_after) == 1

        # Delete single project from remaining zip
        remaining_hash = zips_after[0]["zip_hash"]
        projects = s.list_projects_for_zip(remaining_hash)
        assert projects
        pname = projects[0]
        res2 = s.delete_project(remaining_hash, pname)
        assert res2["deleted_projects"] == 1

        # If we delete the last project, zip should also be removed
        projects_left = s.list_projects_for_zip(remaining_hash)
        for p in projects_left:
            s.delete_project(remaining_hash, p)
        assert not s.list_projects_for_zip(remaining_hash)
        # The zip row should also be gone now
        assert s.get_zip_metadata(remaining_hash) is None


def test_api_delete_endpoints():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with tempfile.TemporaryDirectory() as td:
        # Inject env for DB path
        os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(td, 'app.db')}"
        s = _mk_store(td)
        _insert_dummy_run(s, os.path.join(td, "z1.zip"), projects=1)

       
        resp = client.delete("/insights/projects/unknown/unknown")
        assert resp.status_code in (404, 200)

        # fetch zip
        zips = s.list_recent_zipfiles(limit=1)
        zh = zips[0]["zip_hash"]
        pname = s.list_projects_for_zip(zh)[0]

        # Delete project
        resp = client.delete(f"/insights/projects/{zh}/{pname}")
        assert resp.status_code == 200
        # Delete zip (may be already removed if last project)
        _insert_dummy_run(s, os.path.join(td, "z1.zip"), projects=1)
        zh2 = s.list_recent_zipfiles(limit=1)[0]["zip_hash"]
        resp2 = client.delete(f"/insights/zips/{zh2}")
        assert resp2.status_code == 200

        # Delete all
        _insert_dummy_run(s, os.path.join(td, "z2.zip"), projects=2)
        resp3 = client.delete("/insights/")
        assert resp3.status_code == 200
