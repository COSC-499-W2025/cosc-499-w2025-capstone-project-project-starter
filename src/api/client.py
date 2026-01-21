"""API client for making HTTP requests to the Artifact API."""
import os
import httpx
from typing import Optional, Dict, List, Any
from pathlib import Path


class APIClient:
    """Client for interacting with the Artifact API."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the API (defaults to http://localhost:8000)
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        self.api_prefix = "/api"
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to httpx
            
        Returns:
            dict: Response JSON data
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}{self.api_prefix}{endpoint}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            # Try to get error details from response
            try:
                error_data = e.response.json()
                raise Exception(f"API Error: {error_data.get('detail', str(e))}")
            except:
                raise Exception(f"API Error: {str(e)}")
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def upload_project(self, file_path: str, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a project file via POST /projects/upload.
        
        Args:
            file_path: Path to the ZIP file to upload
            user_name: Optional username for the upload
            
        Returns:
            dict: Upload result with file information
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        params = {}
        if user_name:
            params['user_name'] = user_name
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/zip')}
            return self._make_request('POST', '/projects/upload', files=files, params=params)
    
    def post_privacy_consent(self, consent_given: bool, user_id: str = "default_user") -> Dict[str, Any]:
        """
        Store privacy consent via POST /privacy-consent.
        
        Args:
            consent_given: Whether consent is granted
            user_id: User identifier (defaults to 'default_user')
            
        Returns:
            dict: Consent storage result
        """
        data = {
            "consent_given": consent_given,
            "user_id": user_id
        }
        return self._make_request('POST', '/privacy-consent', json=data)
    
    def get_projects(self, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get list of projects via GET /projects.
        
        Args:
            user_name: Optional username to filter projects
            
        Returns:
            dict: Response containing projects list
        """
        params = {}
        if user_name:
            params['user_name'] = user_name
        
        return self._make_request('GET', '/projects', params=params)
    
    def get_project_by_id(self, project_id: int, user_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific project by ID via GET /projects/{id}.
        
        Args:
            project_id: The ID of the project to retrieve
            user_name: Optional username to verify ownership
            
        Returns:
            dict: Response containing project information
        """
        params = {}
        if user_name:
            params['user_name'] = user_name
        
        return self._make_request('GET', f'/projects/{project_id}', params=params)


# Global client instance
_default_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """Get or create the default API client instance."""
    global _default_client
    if _default_client is None:
        _default_client = APIClient()
    return _default_client


def set_api_client(client: APIClient):
    """Set the default API client instance."""
    global _default_client
    _default_client = client
