"""
Tests for the main API endpoints: upload, consent, and project retrieval.
"""
import sys
import os
import pytest
import zipfile
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.main import app


class TestProjectUploadEndpoint:
    """Test POST /api/projects/upload endpoint."""
    
    def test_upload_invalid_file_type(self):
        """Test that non-ZIP files are rejected."""
        client = TestClient(app)
        
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("not a zip file")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as file:
                response = client.post(
                    "/api/projects/upload",
                    files={"file": ("test.txt", file, "text/plain")}
                )
            
            assert response.status_code == 400
            assert "Only ZIP files are supported" in response.json()["detail"]
        finally:
            os.unlink(temp_path)
    
    @patch('api.routes.project.add_file_to_db')
    def test_upload_valid_zip(self, mock_add_file):
        """Test uploading a valid ZIP file."""
        # Mock successful upload
        from upload_file import UploadResult
        mock_add_file.return_value = UploadResult(
            success=True,
            message="File 'test.zip' uploaded successfully!",
            error_type=None,
            data={
                "file_id": 123,
                "filename": "test.zip",
                "filepath": "/tmp/test.zip",
                "file_count": 5,
                "files": ["file1.txt", "file2.py"]
            }
        )
        
        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            with zipfile.ZipFile(f.name, 'w') as zf:
                zf.writestr("test.txt", "test content")
            temp_path = f.name
        
        try:
            client = TestClient(app)
            with open(temp_path, 'rb') as file:
                response = client.post(
                    "/api/projects/upload",
                    files={"file": ("test.zip", file, "application/zip")},
                    params={"user_name": "test_user"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "test.zip" in data["message"]
            assert data["data"]["file_id"] == 123
            mock_add_file.assert_called_once()
        finally:
            os.unlink(temp_path)
    
    @patch('api.routes.project.add_file_to_db')
    def test_upload_duplicate_file(self, mock_add_file):
        """Test that duplicate uploads are rejected."""
        from upload_file import UploadResult
        mock_add_file.return_value = UploadResult(
            success=False,
            message="This ZIP file appears to have already been uploaded",
            error_type="DUPLICATE_UPLOAD",
            data={"existing_file_id": 100, "existing_filename": "test.zip"}
        )
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            with zipfile.ZipFile(f.name, 'w') as zf:
                zf.writestr("test.txt", "content")
            temp_path = f.name
        
        try:
            client = TestClient(app)
            with open(temp_path, 'rb') as file:
                response = client.post(
                    "/api/projects/upload",
                    files={"file": ("test.zip", file, "application/zip")}
                )
            
            assert response.status_code == 400
            data = response.json()
            assert "already been uploaded" in data["detail"]
        finally:
            os.unlink(temp_path)


class TestPrivacyConsentEndpoint:
    """Test POST /api/privacy-consent endpoint."""
    
    @patch('api.routes.consent.ConsentStorage.store_consent')
    @patch('api.routes.consent.ConsentStorage.get_consent_status')
    def test_post_consent_granted(self, mock_get_status, mock_store):
        """Test storing consent when granted."""
        mock_store.return_value = True
        mock_get_status.return_value = {
            'consent_given': True,
            'consent_date': '2024-01-01T00:00:00',
            'withdrawn_date': None,
            'consent_version': '1.0'
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/privacy-consent",
            json={"consent_given": True, "user_id": "test_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["consent_given"] is True
        assert data["user_id"] == "test_user"
        mock_store.assert_called_once_with(consent_given=True, user_id="test_user")
    
    @patch('api.routes.consent.ConsentStorage.store_consent')
    @patch('api.routes.consent.ConsentStorage.get_consent_status')
    def test_post_consent_denied(self, mock_get_status, mock_store):
        """Test storing consent when denied."""
        mock_store.return_value = True
        mock_get_status.return_value = {
            'consent_given': False,
            'consent_date': '2024-01-01T00:00:00',
            'withdrawn_date': None,
            'consent_version': '1.0'
        }
        
        client = TestClient(app)
        response = client.post(
            "/api/privacy-consent",
            json={"consent_given": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["consent_given"] is False
        assert data["user_id"] == "default_user"  # Default value
    
    @patch('api.routes.consent.ConsentStorage.store_consent')
    def test_post_consent_storage_failure(self, mock_store):
        """Test handling when consent storage fails."""
        mock_store.return_value = False
        
        client = TestClient(app)
        response = client.post(
            "/api/privacy-consent",
            json={"consent_given": True}
        )
        
        assert response.status_code == 500
        assert "Failed to store consent" in response.json()["detail"]


class TestGetProjectsEndpoint:
    """Test GET /api/projects endpoint."""
    
    @patch('api.routes.project.list_projects')
    def test_get_projects_with_user(self, mock_list):
        """Test getting projects for a specific user."""
        mock_list.return_value = [
            {
                'id': 1,
                'filename': 'project1.zip',
                'created_at': '2024-01-01',
                'file_count': 10,
                'has_thumbnail': True
            },
            {
                'id': 2,
                'filename': 'project2.zip',
                'created_at': '2024-01-02',
                'file_count': 5,
                'has_thumbnail': False
            }
        ]
        
        client = TestClient(app)
        response = client.get("/api/projects?user_name=test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["projects"]) == 2
        assert data["projects"][0]["filename"] == "project1.zip"
        mock_list.assert_called_once_with(user_name="test_user")
    
    @patch('api.routes.project.list_uploaded_files')
    def test_get_all_projects(self, mock_list):
        """Test getting all projects when no user specified."""
        from datetime import datetime
        mock_list.return_value = [
            {
                'id': 1,
                'filename': 'project1.zip',
                'status': 'uploaded',
                'metadata': '{"files": ["file1.txt"]}',
                'created_at': datetime(2024, 1, 1, 10, 0, 0),
                'user_name': 'user1'
            }
        ]
        
        client = TestClient(app)
        response = client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1
        assert data["projects"][0]["id"] == 1


class TestGetProjectByIdEndpoint:
    """Test GET /api/projects/{id} endpoint."""
    
    @patch('api.routes.project.get_project_by_id')
    def test_get_project_by_id_success(self, mock_get):
        """Test successfully retrieving a project by ID."""
        from datetime import datetime
        mock_get.return_value = {
            'id': 123,
            'filename': 'test_project.zip',
            'filepath': '/uploads/test_project.zip',
            'status': 'uploaded',
            'metadata': '{"files": ["file1.txt", "file2.py"]}',
            'created_at': datetime(2024, 1, 1, 0, 0, 0)
        }
        
        client = TestClient(app)
        response = client.get("/api/projects/123?user_name=test_user")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project"]["id"] == 123
        assert data["project"]["filename"] == "test_project.zip"
        mock_get.assert_called_once_with(123, user_name="test_user")
    
    @patch('api.routes.project.get_project_by_id')
    def test_get_project_by_id_not_found(self, mock_get):
        """Test retrieving a non-existent project."""
        mock_get.return_value = None
        
        client = TestClient(app)
        response = client.get("/api/projects/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch('api.routes.project.get_project_by_id')
    def test_get_project_by_id_without_user(self, mock_get):
        """Test retrieving a project without user verification."""
        from datetime import datetime
        mock_get.return_value = {
            'id': 456,
            'filename': 'another_project.zip',
            'filepath': '/uploads/another_project.zip',
            'status': 'uploaded',
            'metadata': None,
            'created_at': datetime(2024, 1, 2, 0, 0, 0)
        }
        
        client = TestClient(app)
        response = client.get("/api/projects/456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["id"] == 456
        mock_get.assert_called_once_with(456, user_name=None)
