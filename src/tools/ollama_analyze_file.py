from __future__ import annotations

import argparse
import json
import os
import zipfile
from pathlib import Path
from typing import Optional
from urllib import error, request


DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MAX_FILES = 20
DEFAULT_MAX_BYTES_PER_FILE = 4000


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, url: str = DEFAULT_URL, timeout: int = 60) -> str:
    """
    Send a prompt to a local Ollama server and return the generated text.

    Uses the non-streaming API for simplicity.
    """
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except error.HTTPError as exc:  # pragma: no cover - network dependent
        raise RuntimeError(f"Ollama HTTP error {exc.code}: {exc.read().decode('utf-8', errors='ignore')}") from exc
    except error.URLError as exc:  # pragma: no cover - network dependent
        raise RuntimeError(f"Could not reach Ollama at {url}: {exc}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned non-JSON response: {body}") from exc

    if "response" not in data:
        raise RuntimeError(f"Ollama response missing 'response' field: {data}")
    return data["response"].strip()


def build_prompt(file_path: Path, code: str) -> str:
    return (
        "You are a code analysis assistant. Provide a concise summary and note any potential issues.\n"
        f"File: {file_path}\n"
        "Code:\n"
        f"{code}\n"
        "Respond with a short summary and a bullet list of skills shown and concepts demonstrated if any."
    )


def build_zip_prompt(zip_path: Path, files: list[tuple[str, str]]) -> str:
    file_list = "\n".join(f"- {name}" for name, _ in files) or "(no files sampled)"
    snippets = "\n\n".join(
        f"---- {name} ----\n{content}" for name, content in files if content.strip()
    )
    return (
        "You are a code analysis assistant. Summarize the project what languages are used and skills demonstrated.\n"
        "If contributor information appears in the files (authors based on .git logs history), include it.\n"
        f"Zip archive: {zip_path}\n"
        "Files sampled:\n"
        f"{file_list}\n\n"
        "Sample contents:\n"
        f"{snippets}\n"
        "Respond with a summary, languages used, skills used and any observed contributors."
    )


def analyze_file(file_path: Path, model: Optional[str] = None, url: Optional[str] = None) -> str:
    file_path = file_path.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    code = file_path.read_text(encoding="utf-8")
    prompt = build_prompt(file_path, code)
    return call_ollama(prompt, model=model or DEFAULT_MODEL, url=url or DEFAULT_URL)


def _sample_zip_contents(
    zip_path: Path,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes_per_file: int = DEFAULT_MAX_BYTES_PER_FILE,
) -> list[tuple[str, str]]:
    sampled: list[tuple[str, str]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = sorted(name for name in zf.namelist() if not name.endswith("/"))
        for name in names[:max_files]:
            with zf.open(name) as f:
                data = f.read(max_bytes_per_file + 1)
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = ""
            text = text[:max_bytes_per_file]
            sampled.append((name, text))
    return sampled


def analyze_zip(
    zip_path: Path,
    model: Optional[str] = None,
    url: Optional[str] = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes_per_file: int = DEFAULT_MAX_BYTES_PER_FILE,
) -> str:
    zip_path = zip_path.resolve()
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    sampled = _sample_zip_contents(zip_path, max_files=max_files, max_bytes_per_file=max_bytes_per_file)
    prompt = build_zip_prompt(zip_path, sampled)
    return call_ollama(prompt, model=model or DEFAULT_MODEL, url=url or DEFAULT_URL)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a source file (or zip archive) to a local Ollama model for quick analysis."
    )
    parser.add_argument("file", type=Path, help="Path to the code file or zip archive to analyze.")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Ollama model name (default: env OLLAMA_MODEL or {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help=f"Ollama generate endpoint (default: env OLLAMA_URL or {DEFAULT_URL}).",
    )
    parser.add_argument(
        "--zip",
        action="store_true",
        help="Treat the input path as a zip archive and analyze sampled files inside it.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help="Maximum number of files to sample from the zip (default: %(default)s).",
    )
    parser.add_argument(
        "--max-bytes-per-file",
        type=int,
        default=DEFAULT_MAX_BYTES_PER_FILE,
        help="Maximum bytes to read per file when sampling a zip (default: %(default)s).",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.zip or args.file.suffix.lower() == ".zip":
        result = analyze_zip(
            args.file,
            model=args.model,
            url=args.url,
            max_files=args.max_files,
            max_bytes_per_file=args.max_bytes_per_file,
        )
    else:
        result = analyze_file(args.file, model=args.model, url=args.url)
    print(result)


if __name__ == "__main__":
    main()
