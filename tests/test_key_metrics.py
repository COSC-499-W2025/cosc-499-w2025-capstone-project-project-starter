from typing import List, Tuple
from src.analysis import key_metrics

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows
    # context manager support
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    # DB API stubs
    def execute(self, *_args, **_kwargs):
        pass
    def fetchall(self):
        return self._rows
    def close(self):
        pass

class _FakeConn:
    def __init__(self, rows):
        self._rows = rows
    # context manager support
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    # DB API stubs
    def cursor(self):
        return _FakeCursor(self._rows)

def _mock_db(monkeypatch, rows: List[Tuple[str, int, str, int]]):
    monkeypatch.setattr(key_metrics, "get_connection", lambda: _FakeConn(rows))

def test_analyze_project_from_db(monkeypatch):
    rows = [
        ("src/a.py", 120, "Python", False, b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10"),
        ("docs/readme.md", 50, "Markdown", False, b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\nline11\nline12\nline13\nline14\nline15"),
        ("data/users.csv", 90, "CSV", False, b"line1\nline2\nline3\nline4\nline5"),
    ]
    _mock_db(monkeypatch, rows)
    monkeypatch.setattr("builtins.input", lambda _: "3")

    result = key_metrics.analyze_project_from_db(project_id=1)
    assert result["totals"]["files"] == 3
    assert result["totals"]["lines"] == 30
    assert "by_language" in result and "by_activity" in result

def test_empty_project(monkeypatch):
    _mock_db(monkeypatch, [])
    result = key_metrics.analyze_project_from_db(project_id=999)
    assert result["totals"]["files"] == 0
    assert result["totals"]["lines"] == 0

def test_print_summary(capsys, monkeypatch):
    rows = [("src/x.py", 100, "Python", False, b"line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8")]
    _mock_db(monkeypatch, rows)
    key_metrics.analyze_project_from_db(project_id=42)
    out = capsys.readouterr().out
    assert "Key Metrics" in out and "Python" in out
