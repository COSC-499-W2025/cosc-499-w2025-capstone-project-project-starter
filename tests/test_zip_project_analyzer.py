import os
import zipfile
import tempfile

from analysis.zip_project_analyzer import analyze_zip_project


def _build_zip(path, files):
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_analyze_zip_project_basic_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "demo.zip")
        files = {
            "README.md": "# Demo\n\nUsage: run locally\n",
            "index.html": "<!doctype html><html></html>",
            "index.js": "console.log('ok');",
        }
        _build_zip(zip_path, files)

        result = analyze_zip_project(zip_path)
        assert result["success"]["status"] in {"success", "partial"}
        assert result["signals"]["has_readme"] is True
        assert result["signals"]["has_entrypoint"] is True
        assert result["metrics"]["total_files"] == 3


def test_analyze_zip_project_incomplete_markers():
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "wip.zip")
        files = {
            "README.md": "# WIP Project\n\nTODO: finish setup\n",
            "app.py": "print('hello')\n",
        }
        _build_zip(zip_path, files)

        result = analyze_zip_project(zip_path)
        assert result["signals"]["has_incomplete_markers"] is True
        assert result["success"]["status"] in {"partial", "incomplete"}
