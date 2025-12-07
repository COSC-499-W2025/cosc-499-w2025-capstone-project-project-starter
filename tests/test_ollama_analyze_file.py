from pathlib import Path

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
