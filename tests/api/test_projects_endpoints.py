import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.api import deps
from src.api.app import app
from src.config.config_manager import UserConfigManager
from src.insights.storage import ProjectInsightsStore
from src.insights.user_role_store import ProjectRoleStore
from src.pipeline.presentation_pipeline import PresentationPipeline
from tests.insights.utils import build_pipeline_payload


def _seed_store(db_path: str) -> tuple[ProjectInsightsStore, str, int]:
    store = ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")
    payload = build_pipeline_payload()
    store.record_pipeline_run(os.path.join(os.path.dirname(db_path), "seed.zip"), payload)
    zip_hash = store.list_recent_zipfiles(limit=1)[0]["zip_hash"]
    projects = PresentationPipeline(insights_store=store).list_available_projects()
    project_id = next(item["project_id"] for item in projects if item["project_name"] == "ProjectAlpha")
    return store, zip_hash, project_id


def test_projects_list_and_detail_and_portfolio():
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store, zip_hash, project_id = _seed_store(db_path)
        role_store = ProjectRoleStore(db_path=db_path)
        role_store.set_user_role(zip_hash, "ProjectAlpha", "Lead Developer")

        app.dependency_overrides[deps.get_store] = lambda: store
        app.dependency_overrides[deps.get_role_store] = lambda: role_store

        client = TestClient(app)

        response = client.get("/projects")
        assert response.status_code == 200
        items = response.json()
        assert any(item["project_id"] == project_id for item in items)

        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == project_id
        assert payload["user_role"] == "Lead Developer"

        response = client.get(f"/portfolio/{project_id}")
        assert response.status_code == 200
        portfolio = response.json()
        assert portfolio["project_id"] == project_id
        assert portfolio["project_title"] == payload["project_name"]
        assert portfolio["user_role"] == "Lead Developer"
        assert "key_skills" in portfolio
        assert "key_metrics" in portfolio
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(td, ignore_errors=True)


def test_projects_upload_triggers_pipeline(monkeypatch):
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store = ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")
        manager = UserConfigManager(db_path=db_path)

        zip_path = os.path.join(td, "demo.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "hello")

        manager.create_config(
            "uploader",
            zip_path,
            llm_consent=False,
            llm_consent_asked=True,
            data_access_consent=True,
        )

        app.dependency_overrides[deps.get_store] = lambda: store
        app.dependency_overrides[deps.get_config_manager] = lambda: manager

        # Inject a lightweight dummy ArtifactPipeline to avoid importing heavy deps (pyzbar/zbar)
        import types, sys as _sys

        dummy_module = types.ModuleType("src.pipeline.orchestrator")

        class _DummyPipeline:
            def __init__(self, insights_store=None):
                self.insights_store = insights_store

            def _save_json_report(self, zip_path, result):
                return Path(zip_path)

            def start(self, zip_path, use_llm=False, data_access_consent=True, prompt_project_names=False):
                # Minimal shape expected by the API handler
                return {"projects": {"ProjectAlpha": {}, "ProjectBeta": {}}}

        dummy_module.ArtifactPipeline = _DummyPipeline
        _sys.modules["src.pipeline.orchestrator"] = dummy_module

        client = TestClient(app)
        response = client.post(
            "/projects/upload",
            json={"user_id": "uploader", "zip_path": zip_path},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["zip_hash"]
        assert data["projects"]
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(td, ignore_errors=True)
