import os
import shutil
import sys
import tempfile
from pathlib import Path
import inspect
import httpx

from fastapi.testclient import TestClient

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.api import deps
from src.api.app import app
from src.insights.storage import ProjectInsightsStore
from src.pipeline.presentation_pipeline import PresentationPipeline
from tests.insights.utils import build_pipeline_payload

# Compatibility shim: older httpx versions don't accept the 'app' kwarg used by Starlette's TestClient
if "app" not in inspect.signature(httpx.Client.__init__).parameters:
    _orig_httpx_init = httpx.Client.__init__

    def _patched_httpx_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return _orig_httpx_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_init


def _seed_store(db_path: str) -> tuple[ProjectInsightsStore, int]:
    store = ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")
    payload = build_pipeline_payload(project_names=("ProjectAlpha",), include_presentation=True)
    store.record_pipeline_run(os.path.join(os.path.dirname(db_path), "seed.zip"), payload)
    projects = PresentationPipeline(insights_store=store).list_available_projects()
    project_id = next(item["project_id"] for item in projects if item["project_name"] == "ProjectAlpha")
    return store, project_id


def test_skills_and_resume_endpoints():
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store, project_id = _seed_store(db_path)

        app.dependency_overrides[deps.get_store] = lambda: store
        client = TestClient(app)

        # GET /skills
        resp = client.get("/skills")
        assert resp.status_code == 200
        skills = resp.json()
        assert isinstance(skills, list)
        assert all(isinstance(s, str) for s in skills)

        # GET /resume/{id}
        resp = client.get(f"/resume/{project_id}")
        assert resp.status_code == 200
        resume = resp.json()["resume_item"]
        assert isinstance(resume, dict)
        assert "bullets" in resume

        # POST /resume/generate (regenerate, returns resume)
        resp = client.post("/resume/generate", params={"project_id": project_id})
        assert resp.status_code == 200
        gen_resume = resp.json()["resume_item"]
        assert isinstance(gen_resume, dict)
        assert "bullets" in gen_resume

        # POST /resume/{id}/edit (persist bullets)
        new_bullets = ["Defined API contracts", "Increased coverage"]
        resp = client.post(f"/resume/{project_id}/edit", json={"bullets": new_bullets})
        assert resp.status_code == 200
        edited = resp.json()["resume_item"]
        assert edited["bullets"] == new_bullets

        # POST /portfolio/generate (regenerate portfolio)
        resp = client.post("/portfolio/generate", params={"project_id": project_id})
        assert resp.status_code == 200
        portfolio = resp.json()["portfolio_item"]
        assert isinstance(portfolio, dict)
        assert "description" in portfolio

        # POST /portfolio/{id}/edit (persist fields)
        resp = client.post(
            f"/portfolio/{project_id}/edit",
            json={
                "tagline": "High-impact data project",
                "is_collaborative": True,
                "key_features": ["P1", "P2"],
            },
        )
        assert resp.status_code == 200
        updated_portfolio = resp.json()["portfolio_item"]
        assert updated_portfolio["tagline"] == "High-impact data project"
        assert updated_portfolio["is_collaborative"] is True
        assert updated_portfolio["key_features"] == ["P1", "P2"]
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(td, ignore_errors=True)
