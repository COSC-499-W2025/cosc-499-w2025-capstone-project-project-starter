"""
tests/analyze/test_chronological_skills.py
---
Unit tests for the ChronologicalSkillList class in src/analyze/chronological_skills.py.

These tests verify:
    - correct detection of skills from all analyzers (code, text, video, image)
    - chronological ordering based on file modification times
    - correct export to JSON, CSV, and TXT formats
---
Run from root directory with:
    docker compose run --rm backend coverage run -m pytest tests/analyze/test_chronological_skills.py
    docker compose run --rm backend coverage report -m
"""

import pytest
import json
from pathlib import Path
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.analyze.chronological_skills import ChronologicalSkillList, make_json_serializable

@pytest.fixture
def temp_files(tmp_path):
    """
    Create dummy files for code, text, video, image so analyzers can reference real paths.
    """
    files = {}
    files['code'] = tmp_path / "file1.py"
    files['code'].write_text("print('hello')")
    files['text'] = tmp_path / "file1.txt"
    files['text'].write_text("AI ML data science")
    files['video'] = tmp_path / "video1.mp4"
    files['video'].write_text("fake video content")  
    files['image'] = tmp_path / "image1.png"
    files['image'].write_text("fake image content") 
    return files

@pytest.fixture
def mock_analyzers(temp_files):
    """
    Patch analyzers to return dummy results pointing to real temp files.
    """
    with patch("src.analyze.chronological_skills.CodeAnalyzer") as MockCode, \
         patch("src.analyze.chronological_skills.TextAnalyzer") as MockText, \
         patch("src.analyze.chronological_skills.VideoAnalyzer") as MockVideo, \
         patch("src.analyze.chronological_skills.ImageProcessor") as MockImage:

        code_instance = MockCode.return_value
        text_instance = MockText.return_value
        video_instance = MockVideo.return_value
        image_instance = MockImage.return_value

        code_instance.analyze_directory.return_value = [
            MagicMock(file_path=str(temp_files['code']), skills=["Python"], language="Python", frameworks=["pytest"])
        ]

        text_metrics = MagicMock()
        text_metrics.top_keywords = [("AI", 10), ("ML", 8)]
        text_metrics.word_count = 100
        text_metrics.lexical_diversity = 0.8
        text_metrics.avg_word_length = 4.5
        text_instance.analyze_file.return_value = text_metrics

        video_result = MagicMock()
        video_result.format = "mp4"
        video_result.resolution = "1080p"
        video_result.to_dict.return_value = {"format": "mp4", "resolution": "1080p"}
        video_instance.analyze_file.return_value = video_result

        image_instance.analyze_image.return_value = {"resolution": {"width": 1920, "height": 1080}}

        yield code_instance, text_instance, video_instance, image_instance

def test_build_skill_timeline_creates_events(tmp_path, mock_analyzers):
    """
    Ensure skill timeline events are correctly built from all analyzers and sorted chronologically.
    """
    analyzer = ChronologicalSkillList()
    events = analyzer.build_skill_timeline(tmp_path)

    # There should be 4 events: code, text, video, image
    assert len(events) == 4

    # Confirm categories present
    categories = {e["category"] for e in events}
    assert categories == {"code", "text", "video", "image"}

    # Confirm chronological order
    timestamps = [e["timestamp"] for e in events]
    assert timestamps == sorted(timestamps), "Events should be sorted by timestamp"

    # Check fields
    code_event = next(e for e in events if e["category"] == "code")
    assert code_event["skills"] == ["Python"]
    assert code_event["metadata"]["language"] == "Python"

    text_event = next(e for e in events if e["category"] == "text")
    assert "writing" in text_event["skills"]

    video_event = next(e for e in events if e["category"] == "video")
    assert video_event["metadata"]["format"] == "mp4"

    image_event = next(e for e in events if e["category"] == "image")
    assert image_event["metadata"]["resolution"]["width"] == 1920


def test_export_results_creates_files(tmp_path, mock_analyzers):
    """
    Ensure that export_results writes JSON, CSV, and TXT to the specified directory.
    """
    analyzer = ChronologicalSkillList()
    events = [
        {
            "file": "file1.py",
            "timestamp": datetime(2025, 11, 1, 12, 0),
            "category": "code",
            "skills": ["Python"],
            "metadata": {"language": "Python"}
        }
    ]

    output_dir = tmp_path / "output"
    paths = analyzer.export_results(events, str(output_dir))

    # Verify all file types exist
    for key in ["json", "csv", "txt"]:
        assert Path(paths[key]).exists(), f"{key} file was not created"

    # Verify JSON content
    with open(paths["json"]) as f:
        data = json.load(f)
        assert data[0]["file"] == "file1.py"

    # Verify CSV content
    with open(paths["csv"]) as f:
        lines = f.readlines()
        assert "file1.py" in lines[1]

    # Verify TXT content
    with open(paths["txt"]) as f:
        text = f.read()
        assert "file1.py" in text

def test_make_json_serializable():
    # np.integer
    assert make_json_serializable(np.int32(42)) == 42
    assert make_json_serializable(np.int64(99)) == 99

    # np.floating
    assert make_json_serializable(np.float32(3.14)) == pytest.approx(3.14)
    assert make_json_serializable(np.float64(2.718)) == pytest.approx(2.718)

    # np.ndarray
    arr = np.array([1, 2, 3], dtype=np.int32)
    assert make_json_serializable(arr) == [1, 2, 3]

    arr2 = np.array([[1.1, 2.2], [3.3, 4.4]], dtype=np.float64)
    assert make_json_serializable(arr2) == [[1.1, 2.2], [3.3, 4.4]]

    # nested dict/list
    nested = {
        "ints": np.array([1, 2, 3], dtype=np.int64),
        "float": np.float32(9.81),
        "nested_list": [np.int16(5), {"val": np.float64(0.123)}]
    }
    expected = {
        "ints": [1, 2, 3],
        "float": pytest.approx(9.81),
        "nested_list": [5, {"val": pytest.approx(0.123)}]
    }
    result = make_json_serializable(nested)
    assert result["ints"] == expected["ints"]
    assert result["float"] == expected["float"]
    assert result["nested_list"][0] == expected["nested_list"][0]
    assert result["nested_list"][1]["val"] == expected["nested_list"][1]["val"]

    # normal Python types remain unchanged
    normal = {
        "a": 1,
        "b": 2.5,
        "c": "text",
        "d": [1, 2, 3],
        "e": {"x": 9}
    }
    assert make_json_serializable(normal) == normal

    # empty structures
    assert make_json_serializable([]) == []
    assert make_json_serializable({}) == {}
