"""
file_categorizer.py
-------------------
Responsible for categorizing a given extracted folder that may contain nested subfolders and files,
and producing a structured JSON representation of the directory hierarchy.

Run from root directory with:
    docker compose run --rm backend python3 -m src.categorize.file_categorizer 
"""

from pathlib import Path
import os
import json

doc_exts = {".md", ".txt", ".pdf", ".docx", ".rtf"}
image_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp"}
sketch_exts = {".drawio", ".vsdx", ".sketch", ".fig", ".xd"}
ignore_dirs = {".git", "__pycache__", "node_modules"}

ext_to_language = {
    # Scripting / Interpreted
    ".py": "python",".r": "r",".rb": "ruby",".pl": "perl",".pm": "perl",".php": "php",".lua": "lua",".jl": "julia",
    # JS/TS
    ".js": "javascript",".mjs": "javascript",".cjs": "javascript",".ts": "typescript",".tsx": "typescript",
    # C-family
    ".c": "c",".h": "c",".cpp": "cpp",".cc": "cpp",".cxx": "cpp",".hpp": "cpp",".hh": "cpp",".hxx": "cpp",".cs": "csharp",".java": "java",".kt": "kotlin",".kts": "kotlin",".swift": "swift",".scala": "scala",".go": "go",".rs": "rust",".m": "objective-c",".mm": "objective-cpp",
    # Data / Query / Build 
    ".sql": "sql",".ps1": "powershell",".psm1": "powershell",".sh": "shell",".bash": "shell",".zsh": "shell",".bat": "batch",".cmd": "batch",".ipynb": "jupyter",".mat": "matlab-data",".mli": "ocaml",".ml": "ocaml",".hs": "haskell",".clj": "clojure",".cljs": "clojure",".groovy": "groovy",".dart": "dart",
    # Build / Config 
    ".gradle": "gradle",".cmake": "cmake",".make": "make",".mk": "make",".toml": "toml",".yaml": "yaml",".yml": "yaml",".json": "json",
}

# Special filenames treated as code (no extension)
special_code_filenames = {
    "makefile": "make","cmakelists.txt": "cmake","dockerfile": "dockerfile","justfile": "just",
}

def _get_language(filename: str) -> str | None:
    """
    Return a language label for recognized code files; None if not recognized as code.
    Handles special filenames and a basic disambiguation for '.m' files.
    """
    name = filename.lower()
    if name in special_code_filenames:
        return special_code_filenames[name]

    ext = Path(name).suffix.lower()

    if ext == ".m":
        return "objective-c"

    return ext_to_language.get(ext)

def categorize_file(filename: str) -> str:
    """
    Return a top-level category label: one of
    'code', 'documentation', 'images', 'sketches', 'other'.
    """
    if _get_language(filename):
        return "code"

    ext = Path(filename).suffix.lower()
    if ext in doc_exts:
        return "documentation"
    elif ext in image_exts:
        return "images"
    elif ext in sketch_exts:
        return "sketches"
    else:
        return "other"

def categorize_folder_structure(folder_path: str) -> dict:
    """
    Walk through a folder hierarchy and produce a flattened, categorized representation.
    Filters out macOS metadata folders and files (like __MACOSX, ._*, .DS_Store).
    """
    root_folder = Path(folder_path)
    if not root_folder.exists() or not root_folder.is_dir():
        raise ValueError(f"ERROR: Invalid path: {root_folder}")

    categorized = {
        "code": [],
        "code_by_language": {},
        "documentation": [],
        "images": [],
        "sketches": [],
        "other": [],
    }

    for current_path, subdirs, files in os.walk(root_folder, topdown=True):
        # Skip unwanted folders entirely
        subdirs[:] = [d for d in subdirs if d not in ignore_dirs and not d.startswith("__MACOSX")]

        for filename in files:
            # Skip macOS metadata and hidden junk files
            if filename.startswith("._") or filename == ".DS_Store":
                continue

            file_path = Path(current_path) / filename
            category = categorize_file(filename)

            if category == "code":
                lang = _get_language(filename) or "unknown"
                categorized["code"].append(str(file_path))
                categorized["code_by_language"].setdefault(lang, []).append(str(file_path))
            else:
                categorized[category].append(str(file_path))

    # Deduplicate results
    for key in categorized:
        if isinstance(categorized[key], list):
            categorized[key] = list(dict.fromkeys(categorized[key]))
        elif isinstance(categorized[key], dict):
            for lang in categorized[key]:
                categorized[key][lang] = list(dict.fromkeys(categorized[key][lang]))

    return categorized