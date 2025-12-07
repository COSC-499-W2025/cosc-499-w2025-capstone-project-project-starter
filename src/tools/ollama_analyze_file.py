from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional
from urllib import error, request


DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
DEFAULT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

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

def analyze_file(file_path: Path, model: Optional[str] = None, url: Optional[str] = None) -> str:
    file_path = file_path.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    code = file_path.read_text(encoding="utf-8")
    prompt = build_prompt(file_path, code)
    return call_ollama(prompt, model=model or DEFAULT_MODEL, url=url or DEFAULT_URL)

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a source file to a local Ollama model for quick analysis."
    )
    parser.add_argument("file", type=Path, help="Path to the code file to analyze.")
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
    return parser

def main():
    parser = _build_parser()
    args = parser.parse_args()

    result = analyze_file(args.file, model=args.model, url=args.url)
    print(result)

if __name__ == "__main__":
    main()
