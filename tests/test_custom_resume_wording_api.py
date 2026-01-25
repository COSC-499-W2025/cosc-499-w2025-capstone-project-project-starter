import sys
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from api.main import app

client = TestClient(app)


class TestCustomResumeWordingAPI:

    @patch('api.routes.resume_portfolio.ResumeManager.list_custom_worded_projects')
    def test_list_custom_wording(self, mock_list):
        mock_list.return_value = [1, 2, 10]

        r = client.get("/api/resume/test_user/custom-wording")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_ids"] == [1, 2, 10]

    @patch('api.routes.resume_portfolio.ResumeManager.save_custom_project_wording')
    def test_save_custom_wording(self, mock_save):
        mock_save.return_value = True

        r = client.post(
            "/api/resume/test_user/custom-wording",
            json={"project_id": 5, "wording": "My custom résumé line"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    @patch('api.routes.resume_portfolio.ResumeManager.clear_custom_project_wording')
    def test_clear_custom_wording(self, mock_clear):
        mock_clear.return_value = True

        r = client.delete("/api/resume/test_user/custom-wording/5")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_save_custom_wording_invalid_project_id(self):
        r = client.post(
            "/api/resume/test_user/custom-wording",
            json={"project_id": 0, "wording": "x"}
        )
        assert r.status_code == 422

    def test_clear_custom_wording_invalid_project_id(self):
        r = client.delete("/api/resume/test_user/custom-wording/0")
        assert r.status_code == 400
