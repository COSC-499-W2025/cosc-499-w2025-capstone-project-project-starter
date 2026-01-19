"""
Tests for FastAPI endpoints and connectivity.
"""
import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Adjust the path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api.main import app


class TestAPIRoot:
    """Test root endpoint."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns correct message."""
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Artifact API is running"
        assert data["version"] == "1.0.0"


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self):
        """Test basic health check endpoint."""
        client = TestClient(app)
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "artifact-api"
    
    @patch('api.dependencies.get_connection')
    def test_db_health_check_success(self, mock_get_connection):
        """Test database health check when DB is connected."""
        # Mock successful connection
        mock_conn = MagicMock()
        mock_get_connection.return_value = mock_conn
        
        client = TestClient(app)
        response = client.get("/api/health/db")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        mock_conn.close.assert_called_once()
    
    @patch('api.dependencies.get_connection')
    def test_db_health_check_failure(self, mock_get_connection):
        """Test database health check when DB connection fails."""
        # Mock failed connection
        mock_get_connection.return_value = None
        
        client = TestClient(app)
        response = client.get("/api/health/db")
        
        assert response.status_code == 503
        data = response.json()
        assert "Database connection failed" in data["detail"]
    
    @patch('api.dependencies.get_connection')
    def test_db_health_check_exception(self, mock_get_connection):
        """Test database health check when exception occurs."""
        # Mock connection raising exception
        mock_get_connection.side_effect = Exception("Connection timeout")
        
        client = TestClient(app)
        response = client.get("/api/health/db")
        
        assert response.status_code == 503
        data = response.json()
        assert "Database health check failed" in data["detail"]


class TestProjectsEndpoint:
    """Test projects endpoint."""
    
    def test_get_projects(self):
        """Test projects endpoint returns correct structure."""
        client = TestClient(app)
        response = client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "projects" in data
        assert data["message"] == "Projects endpoint is working"
        assert isinstance(data["projects"], list)


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema(self):
        """Test that OpenAPI schema is accessible."""
        client = TestClient(app)
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Artifact API"
    
class TestAPIErrorHandling:
    """Test API error handling."""
    
    def test_nonexistent_endpoint(self):
        """Test that nonexistent endpoints return 404."""
        client = TestClient(app)
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_invalid_method(self):
        """Test that invalid HTTP methods return 405."""
        client = TestClient(app)
        response = client.post("/api/health")
        
        # POST to GET-only endpoint should return 405
        assert response.status_code == 405


class TestDependencies:
    """Test API dependencies."""
    
    @patch('api.dependencies.get_connection')
    def test_get_db_cursor_dependency(self, mock_get_connection):
        """Test that database cursor dependency works correctly."""
        from api.dependencies import get_db_cursor
        
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Use dependency as generator
        gen = get_db_cursor()
        cursor = next(gen)
        
        assert cursor == mock_cursor
        
        # Cleanup should close cursor and connection
        try:
            next(gen)
        except StopIteration:
            pass
        
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
        mock_conn.commit.assert_called_once()
    
    @patch('api.dependencies.get_connection')
    def test_get_db_cursor_connection_failure(self, mock_get_connection):
        """Test that dependency raises error when connection fails."""
        from api.dependencies import get_db_cursor
        
        mock_get_connection.return_value = None
        
        with pytest.raises(ConnectionError, match="Could not connect to database"):
            gen = get_db_cursor()
            next(gen)
