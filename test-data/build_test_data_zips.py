"""
Build zipped test data files for Milestone #2.

Creates:
1. code_collab_proj_early.zip - Same project, earlier snapshot (app/, test/, doc/)
2. code_collab_proj_late.zip  - Same project, later snapshot with additional/modified files
3. multi_project.zip          - Multiple projects: code_indiv, code_collab, text_indiv, image_indiv

Run from project root: python test-data/build_test_data_zips.py
"""
import zipfile
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR  # write zips next to script


def _add_dir(zf: zipfile.ZipFile, zip_dir: str, local_path: Path):
    for f in local_path.rglob("*"):
        if f.is_file():
            arcname = f"{zip_dir}/{f.relative_to(local_path.parent)}".replace("\\", "/")
            zf.write(f, arcname)


def build_code_collab_early():
    """Early snapshot: code_collab_proj with app/, test/, doc/."""
    zpath = OUT_DIR / "code_collab_proj_early.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        base = "code_collab_proj"
        zf.writestr(f"{base}/app/main.py", "# Early version\nprint('hello')\n")
        zf.writestr(f"{base}/app/__init__.py", "")
        zf.writestr(f"{base}/test/test_main.py", "# Early tests\nimport unittest\n")
        zf.writestr(f"{base}/doc/README.md", "# Code Collab Project (early)\n")
    print(f"Created {zpath}")


def build_code_collab_late():
    """Later snapshot: same project with more files and one modified (app/main.py)."""
    zpath = OUT_DIR / "code_collab_proj_late.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        base = "code_collab_proj"
        zf.writestr(f"{base}/app/main.py", "# Later version with new feature\nprint('hello world')\n")
        zf.writestr(f"{base}/app/__init__.py", "")
        zf.writestr(f"{base}/app/config.py", "# New file in late snapshot\nDEBUG = True\n")
        zf.writestr(f"{base}/test/test_main.py", "# Early tests\nimport unittest\n")
        zf.writestr(f"{base}/test/test_config.py", "# New test file\n")
        zf.writestr(f"{base}/doc/README.md", "# Code Collab Project (late)\n")
        zf.writestr(f"{base}/doc/CHANGELOG.md", "# Changelog\n## v2\n- Added config\n")
    print(f"Created {zpath}")


def build_multi_project():
    """One zip with multiple project types: code indiv, code collab, text, image."""
    zpath = OUT_DIR / "multi_project.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("code_indiv_proj/README.md", "# Individual code project\n")
        zf.writestr("code_indiv_proj/src/main.py", "def main(): pass\n")
        zf.writestr("code_collab_proj/app/main.py", "# Collaborative project\n")
        zf.writestr("code_collab_proj/app/__init__.py", "")
        zf.writestr("code_collab_proj/test/test_app.py", "import unittest\n")
        zf.writestr("text_indiv_proj/essay.txt", "A non-code project: written essay or report.\n")
        zf.writestr("text_indiv_proj/notes.md", "# Notes\n")
        # Minimal "image" project: placeholder plus a tiny 1x1 PNG (base64)
        tiny_png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x1d"
            b"\n\xb4\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        zf.writestr("image_indiv_proj/thumbnail.png", tiny_png)
        zf.writestr("image_indiv_proj/README.md", "# Image / design project\n")
    print(f"Created {zpath}")


def main():
    os.chdir(SCRIPT_DIR)
    build_code_collab_early()
    build_code_collab_late()
    build_multi_project()
    print("Done. Zips are in", OUT_DIR)


if __name__ == "__main__":
    main()
