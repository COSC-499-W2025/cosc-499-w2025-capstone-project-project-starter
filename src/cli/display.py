"""Display functions for CLI output."""

from __future__ import annotations
from typing import Any, Mapping, Callable
from .cli_output import print_header, print_kv

def _get(result: Any, key: str, default: Any = None) -> Any:
    """Get attribute/key from result whether it is an object or dict."""
    if isinstance(result, Mapping):
        return result.get(key, default)
    return getattr(result, key, default)

def display_success(result: Any, *, print_fn: Callable[[str], None] = print) -> None:
    """Display success information to user (supports dict or object)."""
    print_header("SUCCESS", print_fn=print_fn)

    message = _get(result, "message")
    if message:
        print_fn(f"Message: {message}")

    data = _get(result, "data")
    if isinstance(data, Mapping) and data:
        # Display file information
        filename = data.get("filename")
        if filename:
            print_fn(f"File: {filename}")

        file_id = data.get("file_id")
        if file_id:
            print_fn(f"File ID: {file_id}")

        files = data.get("files")
        if isinstance(files, list) and files:
            file_count = len(files)
            print_fn(f"\n{file_count} files:")
            for i, f in enumerate(files[:5], 1):
                print_fn(f"  {i}. {f}")
            if file_count > 5:
                print_fn(f"  ... and {file_count - 5} more files")

        if "file_count" in data and "files" not in data:
            print_fn(f"Total files: {data['file_count']}")

    print_fn("=" * 70 + "\n")

def display_error(result: Any, *, print_fn: Callable[[str], None] = print) -> None:
    """Format and display error information (supports dict or object)."""
    print_header("ERROR", width=60, print_fn=print_fn)
    error_type = _get(result, "error_type", "UNKNOWN_ERROR")
    message = _get(result, "message", "")

    print_fn(f"Error Type: {error_type}")
    print_fn(f"Message: {message}")

    data = _get(result, "data")
    if isinstance(data, Mapping) and data:
        print_fn("\nDetails:")
        print_kv(
            {str(k): v for k, v in data.items()},
            indent="  ",
            bullet="•",
            print_fn=print_fn
        )
    print_fn("=" * 60 + "\n")
