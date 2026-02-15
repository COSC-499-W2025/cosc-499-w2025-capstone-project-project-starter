"""API tests for Portfolio customization endpoints."""
import sys
import os
from unittest.mock import patch
from datetime import datetime
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from api.main import app

client = TestClient(app)


class TestPortfolioCustomizationAPI:

    @patch('api.routes.resume_portfolio.ResumeManager.list_customized_portfolio_projects')
    def test_list_portfolio_customizations(self, mock_list):
        """Test GET /portfolio/{user_id}/custom-data endpoint."""
        mock_list.return_value = [1, 5, 10]

        r = client.get("/api/portfolio/test_user/custom-data")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_ids"] == [1, 5, 10]

    @patch('api.routes.resume_portfolio.ResumeManager.get_portfolio_customization')
    @patch('api.routes.resume_portfolio.ResumeManager.save_portfolio_customization')
    def test_save_portfolio_customization(self, mock_save, mock_get):
        """Test POST /portfolio/{user_id}/custom-data endpoint."""
        mock_save.return_value = True
        mock_get.return_value = {
            'project_id': 5,
            'custom_title': 'My Project',
            'custom_description': 'A great project',
            'custom_role': 'Lead Developer',
            'created_at': datetime(2026, 2, 14, 10, 0, 0),
            'updated_at': datetime(2026, 2, 14, 11, 0, 0)
        }

        r = client.post(
            "/api/portfolio/test_user/custom-data",
            json={
                "project_id": 5,
                "custom_title": "My Project",
                "custom_description": "A great project",
                "custom_role": "Lead Developer"
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_id"] == 5
        assert data["custom_title"] == "My Project"

    @patch('api.routes.resume_portfolio.ResumeManager.get_portfolio_customization')
    def test_get_portfolio_customization(self, mock_get):
        """Test GET /portfolio/{user_id}/custom-data/{project_id} endpoint."""
        mock_get.return_value = {
            'project_id': 5,
            'custom_title': 'My Project',
            'custom_description': 'A great project',
            'custom_role': 'Lead Developer',
            'created_at': datetime(2026, 2, 14, 10, 0, 0),
            'updated_at': datetime(2026, 2, 14, 11, 0, 0)
        }

        r = client.get("/api/portfolio/test_user/custom-data/5")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_id"] == 5
        assert data["custom_title"] == "My Project"

    @patch('api.routes.resume_portfolio.ResumeManager.get_portfolio_customization')
    def test_get_portfolio_customization_not_found(self, mock_get):
        """Test GET endpoint when customization doesn't exist."""
        mock_get.return_value = None

        r = client.get("/api/portfolio/test_user/custom-data/999")
        assert r.status_code == 404

    @patch('api.routes.resume_portfolio.ResumeManager.clear_portfolio_customization')
    def test_clear_portfolio_customization(self, mock_clear):
        """Test DELETE /portfolio/{user_id}/custom-data/{project_id} endpoint."""
        mock_clear.return_value = True

        r = client.delete("/api/portfolio/test_user/custom-data/5")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "cleared" in data["message"].lower()

    def test_save_portfolio_customization_invalid_project_id(self):
        """Test POST endpoint with invalid project_id."""
        r = client.post(
            "/api/portfolio/test_user/custom-data",
            json={
                "project_id": 0,
                "custom_title": "Test"
            }
        )
        assert r.status_code == 422  # Pydantic validation error for ge=1 constraint

    def test_save_portfolio_customization_negative_project_id(self):
        """Test POST endpoint with negative project_id."""
        r = client.post(
            "/api/portfolio/test_user/custom-data",
            json={
                "project_id": -5,
                "custom_title": "Test"
            }
        )
        assert r.status_code == 422  # Pydantic validation error

    def test_clear_portfolio_customization_invalid_project_id(self):
        """Test DELETE endpoint with invalid project_id."""
        r = client.delete("/api/portfolio/test_user/custom-data/0")
        assert r.status_code == 400

    @patch('api.routes.resume_portfolio.ResumeManager.save_portfolio_customization')
    def test_save_portfolio_customization_with_partial_data(self, mock_save):
        """Test saving with only some fields set."""
        mock_save.return_value = False  # Simulate save failure

        r = client.post(
            "/api/portfolio/test_user/custom-data",
            json={
                "project_id": 5,
                "custom_title": "Only Title"
            }
        )
        assert r.status_code == 500  # Should return error when save fails

    @patch('api.routes.resume_portfolio.ResumeManager.get_portfolio_customization')
    @patch('api.routes.resume_portfolio.ResumeManager.save_portfolio_customization')
    def test_save_portfolio_customization_all_fields(self, mock_save, mock_get):
        """Test saving with all fields populated."""
        mock_save.return_value = True
        mock_get.return_value = {
            'project_id': 42,
            'custom_title': 'Complete Project',
            'custom_description': 'Full description here',
            'custom_role': 'Senior Developer',
            'created_at': datetime(2026, 2, 14, 10, 0, 0),
            'updated_at': datetime(2026, 2, 14, 11, 0, 0)
        }

        r = client.post(
            "/api/portfolio/test_user/custom-data",
            json={
                "project_id": 42,
                "custom_title": "Complete Project",
                "custom_description": "Full description here",
                "custom_role": "Senior Developer"
            }
        )
        assert r.status_code == 200
        data = r.json()
        assert data["custom_title"] == "Complete Project"
        assert data["custom_description"] == "Full description here"
        assert data["custom_role"] == "Senior Developer"

    @patch('api.routes.resume_portfolio.ResumeManager.get_portfolio_customization')
    def test_get_portfolio_customization_with_timestamps(self, mock_get):
        """Test that timestamps are properly serialized."""
        mock_get.return_value = {
            'project_id': 5,
            'custom_title': 'Test',
            'custom_description': 'Desc',
            'custom_role': 'Role',
            'created_at': datetime(2026, 2, 14, 10, 0, 0),
            'updated_at': datetime(2026, 2, 14, 11, 30, 0)
        }

        r = client.get("/api/portfolio/test_user/custom-data/5")
        assert r.status_code == 200
        data = r.json()
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        assert "2026-02-14" in data["created_at"]

    @patch('api.routes.resume_portfolio.ResumeManager.clear_portfolio_customization')
    def test_clear_portfolio_customization_failure(self, mock_clear):
        """Test DELETE endpoint when clear operation fails."""
        mock_clear.return_value = False

        r = client.delete("/api/portfolio/test_user/custom-data/5")
        assert r.status_code == 500

    @patch('api.routes.resume_portfolio.ResumeManager.list_customized_portfolio_projects')
    def test_list_portfolio_customizations_empty(self, mock_list):
        """Test listing when user has no customizations."""
        mock_list.return_value = []

        r = client.get("/api/portfolio/test_user/custom-data")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["project_ids"] == []
