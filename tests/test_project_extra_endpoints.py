import base64
import os
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from api.main import app


client = TestClient(app)


class TestProjectThumbnailEndpoints:
    @patch('api.routes.project.get_project_by_id')
    @patch('api.routes.project.add_thumbnail_bytes_to_project')
    def test_upload_thumbnail_success(self, mock_add_thumbnail, mock_get_project):
        mock_get_project.return_value = {"id": 123}
        mock_add_thumbnail.return_value = MagicMock(success=True, to_dict=lambda: {"success": True})

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.png", png_bytes, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_upload_thumbnail_invalid_type(self):
        response = client.post(
            "/api/projects/123/thumbnail",
            files={"file": ("thumb.txt", b"hello", "text/plain")},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"

    @patch('api.routes.project.get_project_by_id')
    def test_get_thumbnail_not_found(self, mock_get_project):
        mock_get_project.return_value = None

        response = client.get("/api/projects/123/thumbnail")

        assert response.status_code == 404

    @patch('api.routes.project.get_project_by_id')
    @patch('api.routes.project.with_db_cursor')
    def test_get_thumbnail_none(self, mock_with_cursor, mock_get_project):
        mock_get_project.return_value = {"id": 123}

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (None,)
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        response = client.get("/api/projects/123/thumbnail")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["has_thumbnail"] is False

    @patch('api.routes.project.get_project_by_id')
    @patch('api.routes.project.with_db_cursor')
    def test_get_thumbnail_success(self, mock_with_cursor, mock_get_project):
        mock_get_project.return_value = {"id": 123}

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (png_bytes,)
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        response = client.get("/api/projects/123/thumbnail")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["has_thumbnail"] is True
        assert data["thumbnail_data"].startswith("data:image/png;base64,")


class TestProjectAnalysisEndpoints:
    @patch('project_analyzer.ProjectAnalyzer')
    def test_analyze_project_success(self, mock_analyzer_cls):
        mock_instance = mock_analyzer_cls.return_value
        mock_instance.analyze_uploaded_project.return_value = {"success": True, "metrics": {"loc": 10}}

        response = client.post("/api/projects/123/analyze?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["analysis"]["success"] is True

    @patch('project_analyzer.ProjectAnalyzer')
    def test_analyze_project_failure(self, mock_analyzer_cls):
        mock_instance = mock_analyzer_cls.return_value
        mock_instance.analyze_uploaded_project.return_value = {"success": False, "error": "boom"}

        response = client.post("/api/projects/123/analyze")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "HTTP_ERROR"

    @patch('project_manager.get_project_by_id')
    def test_analyze_gemini_project_not_found(self, mock_get_project):
        mock_get_project.return_value = None

        response = client.post("/api/projects/123/analyze-gemini")

        assert response.status_code == 404

    @patch('analysis.gemini_analyzer.GeminiAnalyzer')
    @patch('project_analyzer.ProjectAnalyzer')
    @patch('config.db_config.with_db_cursor')
    @patch('project_manager.get_project_by_id')
    def test_analyze_gemini_success(self, mock_get_project, mock_with_cursor, mock_pa_cls, mock_ga_cls):
        mock_get_project.return_value = {"project_info": {"filename": "proj.zip"}}

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("file.py", "file.py", ".py", 10, "print('x')", "text/plain", False)
        ]
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        pa_instance = mock_pa_cls.return_value
        pa_instance._analyze_languages_from_files.return_value = {"primary_language": "Python", "detected_languages": ["Python"]}
        pa_instance._detect_frameworks_from_files.return_value = ["FastAPI"]

        ga_instance = mock_ga_cls.return_value
        ga_instance.analyze_project.return_value = {"success": True, "summary": "ok"}

        response = client.post("/api/projects/123/analyze-gemini?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["analysis"]["success"] is True


class TestProjectQuickSummaryEndpoint:
    @patch('analysis.gemini_analyzer.GeminiAnalyzer')
    @patch('config.db_config.with_db_cursor')
    @patch('project_manager.get_project_by_id')
    def test_quick_summary_success(self, mock_get_project, mock_with_cursor, mock_ga_cls):
        mock_get_project.return_value = {"project_info": {"filename": "proj.zip"}}
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("file.py", "file.py", ".py", 10, "print('x')", "text/plain", False)
        ]
        mock_with_cursor.return_value.__enter__.return_value = mock_cursor

        ga_instance = mock_ga_cls.return_value
        ga_instance.get_quick_summary.return_value = "summary"

        response = client.post("/api/projects/123/quick-summary")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["summary"] == "summary"

    @patch('project_manager.get_project_by_id')
    def test_quick_summary_project_not_found(self, mock_get_project):
        mock_get_project.return_value = None

        response = client.post("/api/projects/123/quick-summary")

        assert response.status_code == 404


class TestProjectRankingEndpoints:
    @patch('api.routes.project.save_rankings_with_summaries')
    @patch('api.routes.project.rank_all_projects')
    def test_rank_projects(self, mock_rank_all, mock_save):
        mock_rank_all.return_value = [
            {"project_id": 1, "score": 0.9},
            {"project_id": 2, "score": 0.8},
        ]

        response = client.post("/api/projects/rank?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2
        mock_save.assert_called_once()

    @patch('api.routes.project.rank_all_projects')
    @patch('api.routes.project.rank_and_summarize_top_projects')
    def test_rank_top3(self, mock_rank_top3, mock_rank_all):
        mock_rank_all.return_value = [
            {"project_id": 1, "score": 0.9},
            {"project_id": 2, "score": 0.8},
            {"project_id": 3, "score": 0.7},
        ]

        response = client.post("/api/projects/rank-top3?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["top3"]) == 3
        mock_rank_top3.assert_called_once()

    @patch('api.routes.project.get_stored_rankings')
    def test_get_rankings(self, mock_get_rankings):
        mock_get_rankings.return_value = [{"project_id": 1, "rank": 1}]

        response = client.get("/api/projects/rankings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rankings"] == [{"project_id": 1, "rank": 1}]

    @patch('api.routes.project.rank_projects_with_gemini')
    def test_rank_projects_gemini(self, mock_rank_gemini):
        mock_rank_gemini.return_value = {"success": True, "ranked": [1, 2, 3]}

        response = client.post("/api/projects/rank-gemini?user_name=test_user")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
