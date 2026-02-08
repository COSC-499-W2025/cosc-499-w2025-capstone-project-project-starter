"""Unit tests for presentation_pipeline module"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.pipeline.presentation_pipeline import (
    PresentationPipeline,
    PresentationResult,
    BatchPresentationResult
)
from src.insights.storage import ProjectInsightsStore


@pytest.fixture
def encryption_key(monkeypatch):
    key = "test-pipeline-key"
    monkeypatch.setenv("INSIGHTS_ENCRYPTION_KEY", key)
    return key.encode("utf-8")


@pytest.fixture
def temp_store(tmp_path, encryption_key):
    db_path = tmp_path / "pipeline_test.db"
    return ProjectInsightsStore(db_path=str(db_path), encryption_key=encryption_key)


@pytest.fixture
def sample_project_payload():
    return {
        "project_name": "TestProject",
        "project_path": "/tmp/testproject",
        "is_git_repo": True,
        "git_analysis": {"total_commits": 100, "total_contributors": 3, "contributors": []},
        "categorized_contents": {
            "code": ["test.py", "main.py"],
            "code_by_language": {"python": ["test.py", "main.py"]},
            "documentation": ["README.md"],
            "images": ["logo.png"],
            "other": []
        },
        "analysis_results": {
            "code": {
                "metrics": {
                    "languages": ["Python", "JavaScript"],
                    "frameworks": ["Django", "React"],
                    "skills": ["REST API", "Database Design", "Unit Testing"],
                    "total_files": 25,
                    "total_lines": 5000,
                    "test_files": 5
                }
            },
            "documentation": {"totals": {"total_files": 1, "total_words": 500}},
            "images": None,
            "videos": None
        }
    }


@pytest.fixture
def sample_project_payload_2():
    return {
        "project_name": "SecondProject",
        "project_path": "/tmp/secondproject",
        "is_git_repo": False,
        "categorized_contents": {
            "code": ["app.js"],
            "code_by_language": {"javascript": ["app.js"]},
            "documentation": [],
            "images": [],
            "other": []
        },
        "analysis_results": {
            "code": {
                "metrics": {
                    "languages": ["JavaScript"],
                    "frameworks": ["Node.js"],
                    "skills": ["Backend Development"],
                    "total_files": 10,
                    "total_lines": 1000
                }
            }
        }
    }


@pytest.fixture
def populated_store(temp_store, sample_project_payload, sample_project_payload_2):
    pipeline_payload_1 = {
        "zip_metadata": {
            "root_name": "test-root-1",
            "file_count": 10,
            "total_uncompressed_bytes": 10000,
            "total_compressed_bytes": 5000
        },
        "projects": {"TestProject": sample_project_payload}
    }
    temp_store.record_pipeline_run("/tmp/test1.zip", pipeline_payload_1)
    
    pipeline_payload_2 = {
        "zip_metadata": {
            "root_name": "test-root-1",
            "file_count": 10,
            "total_uncompressed_bytes": 10000,
            "total_compressed_bytes": 5000
        },
        "projects": {
            "TestProject": sample_project_payload,
            "SecondProject": sample_project_payload_2
        }
    }
    temp_store.record_pipeline_run("/tmp/test1.zip", pipeline_payload_2)
    return temp_store


class TestPresentationPipeline:
    def test_pipeline_initialization_with_store(self, temp_store):
        pipeline = PresentationPipeline(insights_store=temp_store)
        assert pipeline.store is temp_store
    
    def test_pipeline_initialization_with_db_path(self, tmp_path, encryption_key):
        db_path = tmp_path / "new_pipeline.db"
        pipeline = PresentationPipeline(db_path=str(db_path), encryption_key=encryption_key)
        assert pipeline.store is not None
        assert pipeline.store.db_path == str(db_path)
    
    def test_pipeline_initialization_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/default.db")
        monkeypatch.setenv("INSIGHTS_ENCRYPTION_KEY", "default-key")
        pipeline = PresentationPipeline()
        assert pipeline.store is not None


class TestGenerateById:
    def test_generate_by_id_success(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute(
                """
                SELECT pi.id
                FROM project_info pi
                JOIN projects p ON p.id = pi.project_id
                WHERE p.project_name = ?;
                """,
                ("TestProject",),
            ).fetchone()
            project_id = row[0]
        
        result = pipeline.generate_by_id(project_id)
        
        assert isinstance(result, PresentationResult)
        assert result.success is True
        assert result.project_name == "TestProject"
        assert result.portfolio_item["project_name"] == "TestProject"
        assert len(result.resume_item["bullets"]) >= 2
    
    def test_generate_by_id_nonexistent(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        result = pipeline.generate_by_id(99999)
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_generate_by_id_to_dict(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT id FROM project_info LIMIT 1;").fetchone()
            project_id = row[0]
        result = pipeline.generate_by_id(project_id)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "project_id" in result_dict


class TestGenerateByName:
    def test_generate_by_name_success(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT source_hash FROM ingest LIMIT 1;").fetchone()
            zip_hash = row[0]
        result = pipeline.generate_by_name(zip_hash, "TestProject")
        assert result.success is True
        assert result.project_name == "TestProject"
    
    def test_generate_by_name_nonexistent_project(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT source_hash FROM ingest LIMIT 1;").fetchone()
            zip_hash = row[0]
        result = pipeline.generate_by_name(zip_hash, "NonExistentProject")
        assert result.success is False


class TestGenerateForZip:
    def test_generate_for_zip_success(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT source_hash FROM ingest LIMIT 1;").fetchone()
            zip_hash = row[0]
        result = pipeline.generate_for_zip(zip_hash)
        assert isinstance(result, BatchPresentationResult)
        assert result.total_processed == 2
        assert result.successful == 2
    
    def test_generate_for_zip_empty(self, temp_store):
        pipeline = PresentationPipeline(insights_store=temp_store)
        result = pipeline.generate_for_zip("nonexistent_hash")
        assert result.total_processed == 0
    
    def test_generate_for_zip_to_dict(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT source_hash FROM ingest LIMIT 1;").fetchone()
            zip_hash = row[0]
        result = pipeline.generate_for_zip(zip_hash)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "total_processed" in result_dict


class TestGenerateAll:
    def test_generate_all_success(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        result = pipeline.generate_all()
        assert result.total_processed == 2
        assert result.successful == 2
    
    def test_generate_all_with_limit(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        result = pipeline.generate_all(limit=1)
        assert result.total_processed == 1
    
    def test_generate_all_empty_database(self, temp_store):
        pipeline = PresentationPipeline(insights_store=temp_store)
        result = pipeline.generate_all()
        assert result.total_processed == 0


class TestListAvailableProjects:
    def test_list_available_projects_success(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        projects = pipeline.list_available_projects()
        assert isinstance(projects, list)
        assert len(projects) == 2
        assert "project_id" in projects[0]
    
    def test_list_available_projects_empty(self, temp_store):
        pipeline = PresentationPipeline(insights_store=temp_store)
        projects = pipeline.list_available_projects()
        assert len(projects) == 0


class TestInternalHelpers:
    def test_get_project_id(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT source_hash FROM ingest LIMIT 1;").fetchone()
            zip_hash = row[0]
        project_id = pipeline._get_project_id(zip_hash, "TestProject")
        assert project_id is not None
    
    def test_get_project_metadata(self, populated_store):
        pipeline = PresentationPipeline(insights_store=populated_store)
        with sqlite3.connect(populated_store.db_path) as conn:
            row = conn.execute("SELECT id FROM project_info LIMIT 1;").fetchone()
            project_id = row[0]
        metadata = pipeline._get_project_metadata(project_id)
        assert metadata is not None
        assert "project_name" in metadata


class TestDataclasses:
    def test_presentation_result_creation(self):
        result = PresentationResult(
            project_id=1,
            project_name="Test",
            zip_hash="abc123",
            portfolio_item={"project_name": "Test"},
            resume_item={"project_name": "Test"},
            success=True,
            error=None
        )
        assert result.project_id == 1
        assert result.success is True
    
    def test_batch_presentation_result_creation(self):
        result = BatchPresentationResult(
            total_processed=5,
            successful=4,
            failed=1,
            results=[]
        )
        assert result.total_processed == 5
        assert result.successful == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
