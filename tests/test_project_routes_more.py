import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from api.main import app

"""
Additional tests for project API routes.

These tests extend coverage for:
- upload endpoint
- merge endpoint
- project listing
- ranking endpoints
- delete project data

Preference-related tests were intentionally excluded because
the git username logic is currently being fixed in another PR.
"""

client = TestClient(app)


class TestUploadProjectRoutes:
    def test_upload_project_invalid_file_type(self):
        response = client.post(
            "/api/projects/upload",
            files={"file": ("not_zip.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "ZIP" in data["message"]

    @patch("api.routes.project.add_file_to_db")
    def test_upload_project_add_file_failure(self, mock_add_file):
        mock_add_file.return_value = MagicMock(
            success=False,
            message="Upload failed"
        )

        response = client.post(
            "/api/projects/upload",
            files={"file": ("proj.zip", b"fakezipdata", "application/zip")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Upload failed" in data["message"]

    @patch("api.routes.project.add_file_to_db")
    def test_upload_project_success(self, mock_add_file):
        mock_add_file.return_value = MagicMock(
            success=True,
            to_dict=lambda: {
                "success": True,
                "project_id": 123,
                "message": "Uploaded successfully"
            }
        )

        response = client.post(
            "/api/projects/upload?user_name=test_user",
            files={"file": ("proj.zip", b"fakezipdata", "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == 123
        mock_add_file.assert_called_once()

    @patch("api.routes.project.add_file_to_db")
    def test_upload_project_unexpected_exception(self, mock_add_file):
        mock_add_file.side_effect = Exception("boom")

        response = client.post(
            "/api/projects/upload",
            files={"file": ("proj.zip", b"fakezipdata", "application/zip")},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error uploading file" in data["message"]


class TestMergeProjectRoutes:
    def test_merge_project_invalid_file_type(self):
        response = client.post(
            "/api/projects/1/merge",
            files={"file": ("bad.txt", b"abc", "text/plain")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "ZIP" in data["message"]

    @patch("api.routes.project.merge_zip_to_project")
    def test_merge_project_not_found(self, mock_merge):
        mock_merge.return_value = MagicMock(
            success=False,
            error_type="PROJECT_NOT_FOUND",
            message="Project not found"
        )

        response = client.post(
            "/api/projects/999/merge",
            files={"file": ("proj.zip", b"zipcontent", "application/zip")},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Project not found" in data["message"]

    @patch("api.routes.project.merge_zip_to_project")
    def test_merge_project_general_failure(self, mock_merge):
        mock_merge.return_value = MagicMock(
            success=False,
            error_type="MERGE_FAILED",
            message="Merge failed"
        )

        response = client.post(
            "/api/projects/1/merge",
            files={"file": ("proj.zip", b"zipcontent", "application/zip")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Merge failed" in data["message"]

    @patch("api.routes.project.merge_zip_to_project")
    def test_merge_project_success(self, mock_merge):
        mock_merge.return_value = MagicMock(
            success=True,
            to_dict=lambda: {
                "success": True,
                "new_files": 2,
                "skipped_files": 1
            }
        )

        response = client.post(
            "/api/projects/1/merge?user_name=test_user",
            files={"file": ("proj.zip", b"zipcontent", "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_files"] == 2
        assert data["skipped_files"] == 1

    @patch("api.routes.project.merge_zip_to_project")
    def test_merge_project_unexpected_exception(self, mock_merge):
        mock_merge.side_effect = Exception("merge boom")

        response = client.post(
            "/api/projects/1/merge",
            files={"file": ("proj.zip", b"zipcontent", "application/zip")},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error merging files" in data["message"]


class TestThumbnailUploadMore:
    def test_upload_thumbnail_empty_file(self):
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.png", b"", "image/png")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "empty" in data["message"].lower()

    def test_upload_thumbnail_invalid_image_bytes(self):
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.png", b"not-an-image", "image/png")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "valid image" in data["message"].lower()

    @patch("api.routes.project.get_project_by_id")
    def test_upload_thumbnail_project_not_found(self, mock_get_project):
        mock_get_project.return_value = None

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.png", png_bytes, "image/png")},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "not found" in data["message"].lower()

    @patch("api.routes.project.get_project_by_id")
    @patch("api.routes.project.add_thumbnail_bytes_to_project")
    def test_upload_thumbnail_storage_failure(self, mock_add_thumbnail, mock_get_project):
        mock_get_project.return_value = {"id": 123}
        mock_add_thumbnail.return_value = MagicMock(
            success=False,
            message="thumbnail save failed"
        )

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.png", png_bytes, "image/png")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "thumbnail save failed" in data["message"]


class TestProjectsListRoutes:
    @patch("api.routes.project.list_projects")
    def test_get_projects_by_user_success_with_string_datetime(self, mock_list_projects):
        mock_list_projects.return_value = [
            {
                "id": 1,
                "filename": "user_proj.zip",
                "created_at": "2024-01-01T10:00:00",
                "file_count": 3,
                "status": "uploaded",
            }
        ]

        response = client.get("/api/projects?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["projects"][0]["filename"] == "user_proj.zip"
        assert data["projects"][0]["created_at"] == "2024-01-01T10:00:00"

    @patch("api.routes.project.list_projects")
    def test_get_projects_by_user_success_with_datetime_object(self, mock_list_projects):
        mock_list_projects.return_value = [
            {
                "id": 2,
                "filename": "dt_proj.zip",
                "created_at": datetime(2024, 1, 1, 10, 0, 0),
                "file_count": 4,
                "status": "uploaded",
            }
        ]

        response = client.get("/api/projects?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["projects"][0]["created_at"] == "2024-01-01T10:00:00"

    @patch("api.routes.project.list_uploaded_files")
    def test_get_all_projects_success_with_metadata_string(self, mock_list_uploaded):
        mock_list_uploaded.return_value = [
            {
                "id": 1,
                "filename": "proj1.zip",
                "created_at": datetime(2024, 1, 2, 12, 0, 0),
                "metadata": '{"files": ["a.py", "folder/", "b.js"]}',
                "status": "uploaded",
            }
        ]

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["projects"][0]["file_count"] == 2
        assert data["projects"][0]["status"] == "uploaded"
        assert data["projects"][0]["created_at"] == "2024-01-02T12:00:00"

    @patch("api.routes.project.list_uploaded_files")
    def test_get_all_projects_success_with_bad_metadata(self, mock_list_uploaded):
        mock_list_uploaded.return_value = [
            {
                "id": 2,
                "filename": "proj2.zip",
                "created_at": None,
                "metadata": "not-json",
                "status": "uploaded",
            }
        ]

        response = client.get("/api/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["projects"][0]["file_count"] == 0
        assert data["projects"][0]["created_at"] is None

    @patch("api.routes.project.list_uploaded_files")
    def test_get_projects_unexpected_exception(self, mock_list_uploaded):
        mock_list_uploaded.side_effect = Exception("db blew up")

        response = client.get("/api/projects")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error retrieving projects" in data["message"]


class TestSingleProjectRoutes:
    @patch("api.routes.project.get_project_by_id")
    def test_get_project_by_id_not_found(self, mock_get_project):
        mock_get_project.return_value = None

        response = client.get("/api/projects/999")

        assert response.status_code == 404
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "not found" in data["message"].lower()

    @patch("api.routes.project.get_project_by_id")
    def test_get_project_by_id_success_with_datetime(self, mock_get_project):
        mock_get_project.return_value = {
            "project_info": {
                "id": 1,
                "filename": "proj.zip",
                "filepath": "/tmp/proj.zip",
                "status": "uploaded",
                "created_at": "2024-01-01T09:30:00"
            },
            "files": ["a.py"]
        }

        response = client.get("/api/projects/1?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project"]["id"] == 1
        assert data["project"]["filename"] == "proj.zip"
        assert data["project"]["created_at"] == "2024-01-01T09:30:00"

    @patch("api.routes.project.get_project_by_id")
    def test_get_project_by_id_success_with_string_datetime(self, mock_get_project):
        mock_get_project.return_value = {
            "project_info": {
                "id": 2,
                "filename": "proj2.zip",
                "filepath": "/tmp/proj2.zip",
                "status": "uploaded",
                "created_at": "2024-01-01T10:00:00"
            }
        }

        response = client.get("/api/projects/2")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project"]["created_at"] == "2024-01-01T10:00:00"

    @patch("api.routes.project.get_project_by_id")
    def test_get_project_by_id_unexpected_exception(self, mock_get_project):
        mock_get_project.side_effect = Exception("lookup fail")

        response = client.get("/api/projects/1")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error retrieving project" in data["message"]


class TestGeminiAndQuickSummaryMore:
    @patch("project_manager.get_project_by_id")
    @patch("config.db_config.with_db_cursor")
    def test_analyze_gemini_no_file_contents(self, mock_with_cursor, mock_get_project):
        mock_get_project.return_value = {"project_info": {"filename": "proj.zip"}}

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        response = client.post("/api/projects/123/analyze-gemini")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "No file contents found" in data["message"]

    @patch("analysis.gemini_analyzer.GeminiAnalyzer")
    @patch("project_analyzer.ProjectAnalyzer")
    @patch("config.db_config.with_db_cursor")
    @patch("project_manager.get_project_by_id")
    def test_analyze_gemini_analysis_failed(
        self, mock_get_project, mock_with_cursor, mock_pa_cls, mock_ga_cls
    ):
        mock_get_project.return_value = {"project_info": {"filename": "proj.zip"}}

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("main.py", "main.py", ".py", 10, "print('x')", "text/plain", False)
        ]
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        pa_instance = mock_pa_cls.return_value
        pa_instance._analyze_languages_from_files.return_value = {
            "primary_language": "Python",
            "detected_languages": ["Python"],
        }
        pa_instance._detect_frameworks_from_files.return_value = []

        ga_instance = mock_ga_cls.return_value
        ga_instance.analyze_project.return_value = {
            "success": False,
            "error": "Gemini failed"
        }

        response = client.post("/api/projects/123/analyze-gemini")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Gemini failed" in data["message"]

    @patch("project_manager.get_project_by_id")
    @patch("config.db_config.with_db_cursor")
    def test_quick_summary_no_file_contents(self, mock_with_cursor, mock_get_project):
        mock_get_project.return_value = {"project_info": {"filename": "proj.zip"}}

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        response = client.post("/api/projects/123/quick-summary")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "No file contents found" in data["message"]


class TestRankingRoutesMore:
    @patch("api.routes.project.rank_all_projects")
    def test_rank_projects_failure(self, mock_rank_all):
        mock_rank_all.side_effect = Exception("ranking boom")

        response = client.post("/api/projects/rank")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error ranking projects" in data["message"]

    @patch("api.routes.project.rank_all_projects")
    def test_rank_top3_failure(self, mock_rank_all):
        mock_rank_all.side_effect = Exception("top3 boom")

        response = client.post("/api/projects/rank-top3")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error ranking top 3" in data["message"]

    @patch("api.routes.project.rank_projects_with_gemini")
    def test_rank_projects_gemini_failure(self, mock_rank_gemini):
        mock_rank_gemini.return_value = {
            "success": False,
            "error": "Gemini ranking failed"
        }

        response = client.post("/api/projects/rank-gemini")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Gemini ranking failed" in data["message"]

    @patch("api.routes.project.get_stored_rankings")
    def test_get_rankings_failure(self, mock_get_rankings):
        mock_get_rankings.side_effect = Exception("read rankings failed")

        response = client.get("/api/projects/rankings")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error retrieving rankings" in data["message"]


class TestDeleteProjectDataRoutes:
    def test_delete_project_data_missing_user_name(self):
        response = client.delete("/api/projects/1/data")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "user_name parameter is required" in data["message"]

    @patch("api.routes.project.delete_insights")
    def test_delete_project_data_success(self, mock_delete):
        mock_delete.return_value = (5, 10, 1)

        response = client.delete("/api/projects/1/data?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted"]["metrics"] == 5
        assert data["deleted"]["files"] == 10
        assert data["deleted"]["projects"] == 1

    @patch("api.routes.project.delete_insights")
    def test_delete_project_data_permission_error(self, mock_delete):
        mock_delete.side_effect = PermissionError("forbidden")

        response = client.delete("/api/projects/1/data?user_name=test_user")

        assert response.status_code == 403
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "forbidden" in data["message"]

    @patch("api.routes.project.delete_insights")
    def test_delete_project_data_unexpected_exception(self, mock_delete):
        mock_delete.side_effect = Exception("delete boom")

        response = client.delete("/api/projects/1/data?user_name=test_user")

        assert response.status_code == 500
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"
        assert "Error deleting project data" in data["message"]