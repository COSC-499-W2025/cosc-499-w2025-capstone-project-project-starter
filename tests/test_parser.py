import pytest

from codeparser import parse_core


def test_parse_directory_basic(monkeypatch, tmp_path):
    # Create two simple text files
    f1 = tmp_path / "file1.txt"
    f1.write_text("content one", encoding="utf-8")
    f2 = tmp_path / "file2.txt"
    f2.write_text("content two", encoding="utf-8")

    # Mock list_text_files to return these files
    def fake_list_text_files(root_dir):
        assert root_dir == tmp_path
        return [str(f1), str(f2)]

    # Mock classify_text to return deterministic predictions
    def fake_classify_text(text, threshold=0.5):
        if "one" in text:
            return [("skill_a", 0.9)]
        return [("skill_a", 0.8)]

    monkeypatch.setattr(
        parse_core.file_classification, "list_text_files", fake_list_text_files
    )
    monkeypatch.setattr(parse_core.predict, "classify_text", fake_classify_text)

    results = parse_core.parse_directory(tmp_path, threshold=0.5)

    assert results == [
        {"file": str(f1), "predictions": [("skill_a", 0.9)]},
        {"file": str(f2), "predictions": [("skill_a", 0.8)]},
    ]


def test_summarize_results_and_output(capsys):
    results = [
        {
            "file": "a.py",
            "predictions": [("python", 0.9), ("ml", 0.6)],
        },
        {
            "file": "b.py",
            "predictions": [("python", 0.7)],
        },
        {
            "file": "c.py",
            "predictions": [],
        },
    ]

    summary = parse_core.summarize_results(results)

    # Summary structure and aggregation
    assert len(summary) == 2

    # Sorted by max_prob descending: "python" first
    python_entry = summary[0]
    ml_entry = summary[1]

    assert python_entry["skill"] == "python"
    assert python_entry["count"] == 2
    assert python_entry["avg_prob"] == pytest.approx(0.8)
    assert python_entry["max_prob"] == pytest.approx(0.9)

    assert ml_entry["skill"] == "ml"
    assert ml_entry["count"] == 1
    assert ml_entry["avg_prob"] == pytest.approx(0.6)
    assert ml_entry["max_prob"] == pytest.approx(0.6)

    # Check printed output contains key sections and values
    captured = capsys.readouterr()
    out = captured.out

    assert "=== Skill summary across all non-binary files ===" in out
    assert "python: files=2, avg_prob=0.800, max_prob=0.900" in out
    assert "ml: files=1, avg_prob=0.600, max_prob=0.600" in out
    assert "\n=== Per-file predictions (non-empty) ===" in out
    assert "File: a.py" in out
    assert "File: b.py" in out
    assert "python: 0.900" in out
    assert "python: 0.700" in out
    assert "ml: 0.600" in out
