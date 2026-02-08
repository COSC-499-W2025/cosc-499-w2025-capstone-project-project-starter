"""Tests for project listing with filtering functionality."""

import pytest
import tempfile
import os
from unittest.mock import patch
from src.pipeline import cli
from src.pipeline.presentation_pipeline import PresentationPipeline
from src.insights.storage import ProjectInsightsStore


@pytest.fixture
def temp_store_with_projects():
    """Create a temporary store with multiple projects having different tech stacks."""
    td = tempfile.mkdtemp()
    db_path = os.path.join(td, "test.db")
    store = ProjectInsightsStore(db_path=db_path)
    
    # Project 1: Python + Django (web app)
    payload1 = {
        "zip_metadata": {
            "root_name": "demo1",
            "file_count": 10,
            "total_uncompressed_bytes": 50000,
            "total_compressed_bytes": 10000
        },
        "projects": {
            "WebApp": {
                "project_name": "WebApp",
                "project_path": "/tmp/webapp",
                "is_git_repo": True,
                "git_analysis": {"total_commits": 50},
                "categorized_contents": {
                    "code": ["webapp/app.py"],
                    "code_by_language": {"python": ["webapp/app.py"]},
                    "documentation": ["webapp/README.md"],
                    "images": [],
                    "other": []
                },
                "analysis_results": {
                    "code": {
                        "metrics": {
                            "total_files": 5,
                            "total_lines": 500,
                            "languages": ["Python"],
                            "frameworks": ["Django", "REST Framework"]
                        }
                    },
                    "documentation": {"totals": {"total_words": 200, "total_files": 1}}
                },
                "project_metrics": {
                    "languages": ["Python"],
                    "frameworks": ["Django", "REST Framework"],
                    "skills": [],
                    "total_files": 5,
                    "total_lines": 500
                }
            }
        }
    }
    
    # Project 2: JavaScript + React (frontend)
    payload2 = {
        "zip_metadata": {
            "root_name": "demo2",
            "file_count": 15,
            "total_uncompressed_bytes": 75000,
            "total_compressed_bytes": 15000
        },
        "projects": {
            "ReactApp": {
                "project_name": "ReactApp",
                "project_path": "/tmp/reactapp",
                "is_git_repo": True,
                "git_analysis": {"total_commits": 30},
                "categorized_contents": {
                    "code": ["reactapp/App.jsx"],
                    "code_by_language": {"javascript": ["reactapp/App.jsx"]},
                    "documentation": ["reactapp/README.md"],
                    "images": [],
                    "other": []
                },
                "analysis_results": {
                    "code": {
                        "metrics": {
                            "total_files": 8,
                            "total_lines": 600,
                            "languages": ["JavaScript", "TypeScript"],
                            "frameworks": ["React", "Redux"]
                        }
                    },
                    "documentation": {"totals": {"total_words": 150, "total_files": 1}}
                },
                "project_metrics": {
                    "languages": ["JavaScript", "TypeScript"],
                    "frameworks": ["React", "Redux"],
                    "skills": [],
                    "total_files": 8,
                    "total_lines": 600
                }
            }
        }
    }
    
    # Project 3: Python + Flask (different framework)
    payload3 = {
        "zip_metadata": {
            "root_name": "demo3",
            "file_count": 8,
            "total_uncompressed_bytes": 25000,
            "total_compressed_bytes": 5000
        },
        "projects": {
            "FlaskAPI": {
                "project_name": "FlaskAPI",
                "project_path": "/tmp/flaskapi",
                "is_git_repo": False,
                "categorized_contents": {
                    "code": ["flaskapi/api.py"],
                    "code_by_language": {"python": ["flaskapi/api.py"]},
                    "documentation": [],
                    "images": [],
                    "other": []
                },
                "analysis_results": {
                    "code": {
                        "metrics": {
                            "total_files": 3,
                            "total_lines": 250,
                            "languages": ["Python"],
                            "frameworks": ["Flask"]
                        }
                    },
                    "documentation": {"totals": {"total_words": 0, "total_files": 0}}
                },
                "project_metrics": {
                    "languages": ["Python"],
                    "frameworks": ["Flask"],
                    "skills": [],
                    "total_files": 3,
                    "total_lines": 250
                }
            }
        }
    }
    
    # Store all projects
    store.record_pipeline_run("/tmp/demo1.zip", payload1)
    store.record_pipeline_run("/tmp/demo2.zip", payload2)
    store.record_pipeline_run("/tmp/demo3.zip", payload3)
    
    yield store
    
    # Cleanup: Close all connections and delete temp directory
    import shutil
    import gc
    del store
    gc.collect()  # Force garbage collection to close connections
    try:
        shutil.rmtree(td, ignore_errors=True)
    except:
        pass


class TestListFilterBySingleLanguage:
    def test_filter_by_python(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["Python"]})
        assert len(projects) == 2
        project_names = [p["project_name"] for p in projects]
        assert "WebApp" in project_names and "FlaskAPI" in project_names
    
    def test_filter_by_javascript(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["JavaScript"]})
        assert len(projects) == 1
        assert projects[0]["project_name"] == "ReactApp"
    
    def test_filter_case_insensitive(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["python"]})
        assert len(projects) == 2


class TestListFilterByMultipleLanguages:
    def test_filter_by_python_or_javascript(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["Python", "JavaScript"]})
        assert len(projects) == 3
    
    def test_filter_by_typescript(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["TypeScript"]})
        assert len(projects) == 1
        assert projects[0]["project_name"] == "ReactApp"


class TestListFilterByFramework:
    def test_filter_by_django(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"frameworks": ["Django"]})
        assert len(projects) == 1
        assert projects[0]["project_name"] == "WebApp"
    
    def test_filter_by_react(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"frameworks": ["React"]})
        assert len(projects) == 1
        assert projects[0]["project_name"] == "ReactApp"
    
    def test_filter_framework_case_insensitive(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"frameworks": ["django"]})
        assert len(projects) == 1
        assert projects[0]["project_name"] == "WebApp"


class TestListFilterCombined:
    def test_filter_python_and_django(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={
            "languages": ["Python"], "frameworks": ["Django"]
        })
        assert len(projects) == 1
        assert projects[0]["project_name"] == "WebApp"
    
    def test_filter_python_and_react_returns_empty(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={
            "languages": ["Python"], "frameworks": ["React"]
        })
        assert len(projects) == 0


class TestListFilterEmptyResults:
    def test_filter_nonexistent_language(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={"languages": ["Rust"]})
        assert len(projects) == 0
    
    def test_empty_filter_dict_returns_all(self, temp_store_with_projects):
        pipeline = PresentationPipeline(insights_store=temp_store_with_projects)
        projects = pipeline.list_available_projects(filters={})
        assert len(projects) == 3


class TestListCLIIntegration:
    @patch("src.pipeline.presentation_pipeline.PresentationPipeline")
    def test_cli_list_with_language_filter(self, mock_pipeline_cls, capsys):
        mock_pipeline_cls.return_value.list_available_projects.return_value = [{
            "project_id": 1, "project_name": "WebApp", "zip_hash": "abc123",
            "code_files": 5, "doc_files": 1, "is_git_repo": True,
            "updated_at": "2024-01-15 10:30:00"
        }]
        exit_code = cli.main(["list", "--language", "Python"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "WebApp" in captured.out and "Language: Python" in captured.out
        call_args = mock_pipeline_cls.return_value.list_available_projects.call_args
        assert call_args[1]["filters"]["languages"] == ["Python"]
    
    @patch("src.pipeline.presentation_pipeline.PresentationPipeline")
    def test_cli_list_with_multiple_filters(self, mock_pipeline_cls, capsys):
        mock_pipeline_cls.return_value.list_available_projects.return_value = []
        exit_code = cli.main(["list", "--language", "Python", "--language", "JavaScript", "--framework", "React"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "No projects found" in captured.out
        assert "languages: Python, JavaScript" in captured.out
        call_args = mock_pipeline_cls.return_value.list_available_projects.call_args
        assert call_args[1]["filters"]["languages"] == ["Python", "JavaScript"]
        assert call_args[1]["filters"]["frameworks"] == ["React"]
    
    @patch("src.pipeline.presentation_pipeline.PresentationPipeline")
    def test_cli_list_without_filters(self, mock_pipeline_cls, capsys):
        mock_pipeline_cls.return_value.list_available_projects.return_value = [
            {"project_id": 1, "project_name": "P1", "zip_hash": "abc",
             "code_files": 5, "doc_files": 1, "is_git_repo": True, "updated_at": "2024-01-15 10:30:00"},
            {"project_id": 2, "project_name": "P2", "zip_hash": "def",
             "code_files": 3, "doc_files": 0, "is_git_repo": False, "updated_at": "2024-01-14 10:30:00"}
        ]
        exit_code = cli.main(["list"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "P1" in captured.out and "P2" in captured.out
        call_args = mock_pipeline_cls.return_value.list_available_projects.call_args
        assert call_args[1]["filters"] is None
