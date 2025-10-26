from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Iterator, Dict, Tuple, Callable, Set, Optional

# Easy default directories to skip
DEFAULT_EXCLUDES: Set[str] = {".git", ".hg", ".svn", ".idea", ".vscode", "node_modules", "dist", "build", "target", "__pycache__", "venv", ".venv"}
# Charlimit for ml model
DEFAULT_MAX_CHARS = 2000
# How many characters each chunk can overlap into the next oen
DEFAULT_OVERLAP = 200
# Maximum number of characters to avoid slowdowns on huge files
DEFAULT_MAX_FILE_CHARS = 1_000_000


# two internal functiosn for normalizing text and getting some rough metadata to start with

def _normalize_text(s: str) -> str:
	return s.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")

def _language_from_path(p: Path) -> str:
    return EXT_TO_LANG.get(p.suffix.lower(), "unknown")


def chunk(text: str, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> Iterator[Tuple[int, int, str]]:
	n = len(text)
	if n == 0:
		return
	start = 0
	while start < n:
		end = min(n, start + max_chars)
		yield (start, end, text[start:end])
		if end >= n:
			break
		start = max(0, end - overlap)

def iter_text(root: Path, is_binary_file: Callable[[str], bool], excludes: Optional[Set[str]] = None) -> Iterator[Path]:
	excludes = excludes or DEFAULT_EXCLUDES
	root = root.resolve()
	for dirpath, dirnames, filenames in os.walk(root):
		dirnames[:] = [d for d in dirnames if d not in excludes]
		for fn in filenames:
			p = Path(dirpath) / fn
			try:
				if not is_binary_file(str(p)):
					yield p
			except Exception:
				#just skip
				continue

def file_to_chunk(path: Path, *, repo_root: Path, max_file_chars: int = DEFAULT_MAX_FILE_CHARS, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> Iterator[Dict]:
	try:
		with open(path, "r", encoding="utf-8", errors="replace") as f:
			raw = f.read(max_file_chars)
	except Exception:
		return

	text = _normalize_text(raw)
	lang = _language_from_path(path)
	rel = str(path.resolve().relative_to(repo_root))


	for idx, (start, end, slice_) in enumerate(chunk(text, max_chars, overlap)):
		yield {
			"repo_relpath": rel,
			"language": lang,
			"chunk_index": idx,
			"start": start,
			"end": end,
			"text": slice_,
		}



def write_chunks_json(repo_root: str, out_json: str, is_binary_file: Callable[[str], bool], *, excludes: Optional[Set[str]] = None, max_file_chars: int = DEFAULT_MAX_FILE_CHARS, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> int:
	root = Path(repo_root).resolve()
	out = Path(out_json).resolve()
	out.parent.mkdir(parents=True, exist_ok=True)

	count = 0
	with open(out, "w", encoding="utf-8") as sink:
		for p in iter_text(root, is_binary_file=is_binary_file, excludes=excludes):
			for chunk in file_to_chunk(p, repo_root=root, max_file_chars=max_file_chars, max_chars=max_chars,overlap=overlap):
				sink.write(json.dumps(chunk, ensure_ascii=False) + "\n")
				count += 1
	return count




#mapping of file extensions to their respective languages
EXT_TO_LANG: Dict[str, str] = {
    ".py": "python",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".m": "objc",
    ".mm": "objc++",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".r": "r",
    ".jl": "julia",
    ".sql": "sql",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
}
