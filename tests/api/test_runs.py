import os
import shutil
import tempfile

import httpx
import pytest

from src.api import deps
from src.api.app import app
from src.insights.storage import ProjectInsightsStore


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _insert_dummy_run(store: ProjectInsightsStore, zip_path: str):
    payload = {
        "zip_metadata": {
            "root_name": os.path.basename(zip_path),
            "file_count": 1,
            "total_uncompressed_bytes": 10,
            "total_compressed_bytes": 5,
        },
        "projects": {"demo": {"categorized_contents": {"code": ["a.py"]}}},
    }
    store.record_pipeline_run(zip_path, payload)


@pytest.mark.anyio
async def test_list_runs():
    td = tempfile.mkdtemp()
    try:
        db_path = os.path.join(td, "app.db")
        store = ProjectInsightsStore(db_path=db_path, encryption_key=b"dev")
        _insert_dummy_run(store, os.path.join(td, "sample.zip"))

        app.dependency_overrides[deps.get_store] = lambda: store
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/runs")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        runs = response.json()
        assert isinstance(runs, list)
        assert runs
        assert "zip_hash" in runs[0]
    finally:
        shutil.rmtree(td, ignore_errors=True)
