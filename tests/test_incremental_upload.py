import os
import uuid
import tempfile

from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

TEST_DATA_DIR = "tests/data"


def test_req21_incremental_project_upload():
    """
    Req #21:
    The system must allow incremental information by adding another
    zipped folder of files for the same project at a later point in time.
    """

    zip_v1 = os.path.join(TEST_DATA_DIR, "code_collab_proj_v1.zip")
    zip_v2 = os.path.join(TEST_DATA_DIR, "code_collab_proj_v2.zip")

    project_name = f"req21-test-{uuid.uuid4()}"

    with tempfile.TemporaryDirectory() as tmp_blobstore:
        # Point the blobstore to a temporary folder so it's writable in tests
        os.environ["ARTIFACT_MINER_BLOBSTORE"] = tmp_blobstore

        # ---- Grant privacy consent ----
        consent_response = client.post(
            "/privacy-consent",
            json={
                "user_id": None,              # Let the server create a new user
                "consent_type": "data_access",
                "granted": True,
                "version": 1
            }
        )
        assert consent_response.status_code == 200
        user_id = consent_response.json()["user_id"]

        # ---- Upload first snapshot ----
        with open(zip_v1, "rb") as f:
            response_v1 = client.post(
                "/projects/upload",
                data={
                    "project_name": project_name,
                    "user_id": user_id
                },
                files={
                    "file": ("code_collab_proj_v1.zip", f, "application/zip")
                },
            )

        assert response_v1.status_code == 200
        data_v1 = response_v1.json()
        assert "created" in data_v1
        assert len(data_v1["created"]) >= 1
        project_id = data_v1["created"][0]["project_id"]

        # ---- Upload second snapshot (incremental update) ----
        with open(zip_v2, "rb") as f:
            response_v2 = client.post(
                "/projects/upload",
                data={
                    "project_name": project_name,
                    "user_id": user_id
                },
                files={
                    "file": ("code_collab_proj_v2.zip", f, "application/zip")
                },
            )

        assert response_v2.status_code == 200
        data_v2 = response_v2.json()

        # The same project should appear in "created" or "skipped"
        created_projects = data_v2.get("created", [])
        skipped_projects = data_v2.get("skipped", [])

        all_project_ids = [p["project_id"] for p in created_projects + skipped_projects]

        # Ensure the same project ID is present (incremental)
        assert project_id in all_project_ids

        # Optional: ensure only one project was created, others are skipped
        assert len([p for p in created_projects if p["project_id"] == project_id]) <= 1
