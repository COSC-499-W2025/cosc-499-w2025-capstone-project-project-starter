from pathlib import Path
import zipfile

import pytest

from src.tools import ollama_analyze_file as analyzer


def test_build_prompt_includes_filename_and_code(tmp_path):
    code_file = tmp_path / "sample.py"
    code_file.write_text("print('hello')\n", encoding="utf-8")

    prompt = analyzer.build_prompt(code_file, code_file.read_text(encoding="utf-8"))

    assert "sample.py" in prompt
    assert "print('hello')" in prompt


def test_analyze_file_uses_default_model_and_url(monkeypatch, tmp_path):
    code_file = tmp_path / "code.py"
    code_file.write_text("x = 1\n", encoding="utf-8")

    captured = {}

    def fake_call(prompt, model=None, url=None, timeout=None):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["url"] = url
        captured["timeout"] = timeout
        return "analysis-result"

    monkeypatch.setattr(analyzer, "call_ollama", fake_call)

    result = analyzer.analyze_file(code_file)

    assert result == "analysis-result"
    assert analyzer.DEFAULT_MODEL == captured["model"]
    assert analyzer.DEFAULT_URL == captured["url"]
    assert "code.py" in captured["prompt"]


def test_analyze_file_supports_custom_model_and_url(monkeypatch, tmp_path):
    code_file = tmp_path / "main.py"
    code_file.write_text("y = 2\n", encoding="utf-8")

    captured = {}

    def fake_call(prompt, model=None, url=None, timeout=None):
        captured["model"] = model
        captured["url"] = url
        return "custom-analysis"

    monkeypatch.setattr(analyzer, "call_ollama", fake_call)

    result = analyzer.analyze_file(code_file, model="custom-model", url="http://example/api")

    assert result == "custom-analysis"
    assert captured["model"] == "custom-model"
    assert captured["url"] == "http://example/api"


def test_analyze_file_raises_when_missing_file():
    missing = Path("does_not_exist.py")
    with pytest.raises(FileNotFoundError):
        analyzer.analyze_file(missing)


def test_build_zip_prompt_includes_file_list_and_snippets():
    prompt = analyzer.build_zip_prompt(
        Path("archive.zip"),
        [("a.py", "print('a')"), ("b.md", "# Title")],
    )
    assert "archive.zip" in prompt
    assert "a.py" in prompt and "b.md" in prompt
    assert "print('a')" in prompt
    assert "# Title" in prompt


def test_sample_zip_respects_limits(tmp_path):
    zip_path = tmp_path / "code.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a.py", "print('a')" * 1000)  # long content
        zf.writestr("b.py", "print('b')")
        zf.writestr("c.txt", "third")

    sampled = analyzer._sample_zip_contents(zip_path, max_files=2, max_bytes_per_file=20)

    assert len(sampled) == 2
    assert all(len(content) <= 20 for _, content in sampled)


def test_analyze_zip_calls_ollama_with_defaults(monkeypatch, tmp_path):
    zip_path = tmp_path / "proj.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("app.py", "print('hi')")

    captured = {}

    def fake_call(prompt, model=None, url=None, timeout=None):
        captured["prompt"] = prompt
        captured["model"] = model
        captured["url"] = url
        captured["timeout"] = timeout
        return "zip-analysis"

    monkeypatch.setattr(analyzer, "call_ollama", fake_call)

    result = analyzer.analyze_zip(zip_path)

    assert result == "zip-analysis"
    assert analyzer.DEFAULT_MODEL == captured["model"]
    assert analyzer.DEFAULT_URL == captured["url"]
    assert "app.py" in captured["prompt"]
