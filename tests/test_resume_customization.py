"""
Unit tests for non-persistent resume item customization feature.

These tests verify the apply_resume_item_customization function without
requiring OpenAI API keys or any external dependencies.
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.insights.storage import ProjectInsightsStore
from src.project.presentation import apply_resume_item_customization
from tests.insights.utils import build_pipeline_payload


def test_apply_resume_item_customization_edits_does_not_mutate():
    """
    Test that applying edits creates a new dict and does not mutate the original.
    """
    # Arrange
    original = {
        "project_name": "Cool Project",
        "bullets": ["Built X", "Improved Y", "Deployed Z"]
    }
    customization = {
        "edits": [{"index": 1, "text": "Improved Y by 25%"}]
    }
    
    # Act
    customized = apply_resume_item_customization(original, customization)
    
    # Assert - customized has the edit
    assert customized["bullets"][1] == "Improved Y by 25%"
    assert customized["bullets"][0] == "Built X"
    assert customized["bullets"][2] == "Deployed Z"
    assert customized["project_name"] == "Cool Project"
    
    # Assert - original is unchanged (no mutation)
    assert original["bullets"][1] == "Improved Y"
    assert original["bullets"][0] == "Built X"
    assert original["bullets"][2] == "Deployed Z"
    assert original["project_name"] == "Cool Project"


def test_apply_resume_item_customization_full_bullets_override():
    """
    Test that bullets override replaces entire list and strips whitespace.
    Also test project_name override.
    """
    # Arrange
    original = {
        "project_name": "Old Project",
        "bullets": ["Old bullet 1", "Old bullet 2", "Old bullet 3"]
    }
    customization = {
        "project_name": "  New Name  ",
        "bullets": ["  Bullet 1  ", "Bullet 2"]
    }
    
    # Act
    customized = apply_resume_item_customization(original, customization)
    
    # Assert
    assert customized["project_name"] == "New Name"  # Stripped
    assert len(customized["bullets"]) == 2
    assert customized["bullets"][0] == "Bullet 1"  # Stripped
    assert customized["bullets"][1] == "Bullet 2"
    
    # Assert - original unchanged
    assert original["project_name"] == "Old Project"
    assert len(original["bullets"]) == 3


def test_apply_resume_item_customization_invalid_index_raises():
    """
    Test that an out-of-range edit index raises ValueError.
    """
    # Arrange
    resume_item = {
        "project_name": "Test Project",
        "bullets": ["Bullet 1", "Bullet 2"]
    }
    customization = {
        "edits": [{"index": 5, "text": "Invalid edit"}]
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match=r"Edit index 5 out of range"):
        apply_resume_item_customization(resume_item, customization)


def test_apply_resume_item_customization_empty_bullets_override_raises():
    """
    Test that bullets override with only empty/whitespace strings raises ValueError.
    """
    # Arrange
    resume_item = {
        "project_name": "Test Project",
        "bullets": ["Bullet 1", "Bullet 2"]
    }
    customization = {
        "bullets": ["   ", ""]
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match=r"must contain at least one non-empty bullet"):
        apply_resume_item_customization(resume_item, customization)


def test_apply_resume_item_customization_invalid_resume_item_raises():
    """
    Test that invalid resume_item structure raises appropriate errors.
    """
    # Missing bullets key
    with pytest.raises(ValueError, match=r"must contain 'bullets' key"):
        apply_resume_item_customization(
            {"project_name": "Test"},
            {}
        )
    
    # Empty bullets list
    with pytest.raises(ValueError, match=r"bullets.*cannot be empty"):
        apply_resume_item_customization(
            {"project_name": "Test", "bullets": []},
            {}
        )
    
    # Non-dict resume_item
    with pytest.raises(TypeError, match=r"resume_item must be a dict"):
        apply_resume_item_customization("not a dict", {})
    
    # Non-dict customization
    with pytest.raises(TypeError, match=r"customization must be a dict"):
        apply_resume_item_customization(
            {"project_name": "Test", "bullets": ["Bullet"]},
            "not a dict"
        )


def test_apply_resume_item_customization_multiple_edits():
    """
    Test that multiple edits can be applied in a single customization.
    """
    # Arrange
    resume_item = {
        "project_name": "Project",
        "bullets": ["First", "Second", "Third", "Fourth"]
    }
    customization = {
        "edits": [
            {"index": 0, "text": "Updated First"},
            {"index": 2, "text": "Updated Third"}
        ]
    }
    
    # Act
    customized = apply_resume_item_customization(resume_item, customization)
    
    # Assert
    assert customized["bullets"][0] == "Updated First"
    assert customized["bullets"][1] == "Second"  # Unchanged
    assert customized["bullets"][2] == "Updated Third"
    assert customized["bullets"][3] == "Fourth"  # Unchanged


def test_apply_resume_item_customization_bullets_override_ignores_edits():
    """
    Test that bullets override takes precedence over edits.
    """
    # Arrange
    resume_item = {
        "project_name": "Project",
        "bullets": ["Old 1", "Old 2"]
    }
    customization = {
        "bullets": ["New 1", "New 2", "New 3"],
        "edits": [{"index": 0, "text": "This should be ignored"}]
    }
    
    # Act
    customized = apply_resume_item_customization(resume_item, customization)
    
    # Assert - bullets override wins, edits ignored
    assert len(customized["bullets"]) == 3
    assert customized["bullets"][0] == "New 1"
    assert customized["bullets"][1] == "New 2"
    assert customized["bullets"][2] == "New 3"


def test_apply_resume_item_customization_max_bullets_enforced():
    """
    Test that max_bullets limit is enforced.
    """
    # Arrange
    resume_item = {
        "project_name": "Project",
        "bullets": ["Bullet 1"]
    }
    customization = {
        "bullets": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"]
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match=r"cannot exceed 6 bullets"):
        apply_resume_item_customization(resume_item, customization, max_bullets=6)


def test_apply_resume_item_customization_empty_edit_text_raises():
    """
    Test that empty edit text (after stripping) raises ValueError.
    """
    # Arrange
    resume_item = {
        "project_name": "Project",
        "bullets": ["Bullet 1", "Bullet 2"]
    }
    customization = {
        "edits": [{"index": 0, "text": "   "}]
    }
    
    # Act & Assert
    with pytest.raises(ValueError, match=r"Edit text at index 0 cannot be empty"):
        apply_resume_item_customization(resume_item, customization)


def test_apply_resume_item_customization_no_customization():
    """
    Test that passing empty customization dict returns a copy with no changes.
    """
    # Arrange
    original = {
        "project_name": "Project",
        "bullets": ["Bullet 1", "Bullet 2"]
    }
    customization = {}
    
    # Act
    customized = apply_resume_item_customization(original, customization)
    
    # Assert - same content
    assert customized["project_name"] == original["project_name"]
    assert customized["bullets"] == original["bullets"]
    
    # Assert - different object (no mutation)
    assert customized is not original
    assert customized["bullets"] is not original["bullets"]


def test_apply_resume_item_customization_project_name_only():
    """
    Test that project_name can be customized without touching bullets.
    """
    # Arrange
    original = {
        "project_name": "Old Name",
        "bullets": ["Bullet 1", "Bullet 2"]
    }
    customization = {
        "project_name": "New Name"
    }
    
    # Act
    customized = apply_resume_item_customization(original, customization)
    
    # Assert
    assert customized["project_name"] == "New Name"
    assert customized["bullets"] == original["bullets"]
    assert customized["bullets"] is not original["bullets"]  # Still a copy


def test_update_resume_item_persists_project_name(tmp_path):
    """
    Test that a saved resume item can update the stored project_name.
    """
    # Arrange
    db_path = tmp_path / "insights.db"
    store = ProjectInsightsStore(db_path=str(db_path), encryption_key=b"test-key")
    payload = build_pipeline_payload(project_names=("ProjectAlpha",))
    store.record_pipeline_run("/tmp/demo.zip", payload)

    with sqlite3.connect(store.db_path) as conn:
        project_info_id = conn.execute(
            """
            SELECT pi.id
            FROM project_info pi
            JOIN projects p ON p.id = pi.project_id
            WHERE p.project_name = ?;
            """,
            ("ProjectAlpha",),
        ).fetchone()[0]

    resume_item = {
        "project_name": "Custom Project Name",
        "bullets": ["Updated bullet"]
    }

    # Act
    updated = store.update_resume_item_by_id(project_info_id, resume_item)

    # Assert
    assert updated is True
    insight = store.load_project_insight_by_id(project_info_id)
    assert insight["project_name"] == "Custom Project Name"
    assert insight["resume_item"]["bullets"] == ["Updated bullet"]
