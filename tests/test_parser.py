import pytest

from codeparser import parse_core


def test_parse_directory_basic(monkeypatch, tmp_path):
    f1 = tmp_path / "file1.txt"
    f1.write_text("content one", encoding="utf-8")
    f2 = tmp_path / "file2.txt"
    f2.write_text("content two", encoding="utf-8")
    def fake_list_text_files(root_dir):
        assert root_dir == tmp_path
        return [str(f1), str(f2)]
    def fake_classify_text(text, threshold=0.5):
        if "one" in text:
            return [("skill_a", 0.9)]
        return [("skill_a", 0.8)]

    monkeypatch.setattr(
        parse_core.file_classification, "list_text_files", fake_list_text_files
    )
    monkeypatch.setattr(parse_core.predict, "classify_text", fake_classify_text)

    results = parse_core.parse_directory(tmp_path, threshold=0.5)
    assert len(results) == 2

    r1, r2 = results
    assert r1["file"] == str(f1)
    assert r2["file"] == str(f2)
    assert r1["predictions"] == [("skill_a", 0.9)]
    assert r2["predictions"] == [("skill_a", 0.8)]
    assert r1["project"] == "__root__"
    assert r2["project"] == "__root__"
    assert "last_modified" in r1
    assert "last_modified" in r2


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

    assert len(summary) == 2

    by_skill = {entry["skill"]: entry for entry in summary}

    assert set(by_skill.keys()) == {"python", "ml"}

    python_entry = by_skill["python"]
    ml_entry = by_skill["ml"]

    assert python_entry["count"] == 2
    assert python_entry["avg_prob"] == pytest.approx(0.8)
    assert python_entry["max_prob"] == pytest.approx(0.9)

    assert ml_entry["count"] == 1
    assert ml_entry["avg_prob"] == pytest.approx(0.6)
    assert ml_entry["max_prob"] == pytest.approx(0.6)

    captured = capsys.readouterr()
    assert captured.out.strip() != ""
