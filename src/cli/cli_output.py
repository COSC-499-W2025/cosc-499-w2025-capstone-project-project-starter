# src/cli/cli_output.py
"""
Small CLI output utilities.

Goal:
- Standardize formatting (headers/sections/status lines).
- Keep printing concerns in one place.
- Make it easy to test output without touching business logic.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Optional


PrintFn = Callable[[str], None]


def _line(width: int = 70, ch: str = "=") -> str:
    if not ch:
        ch = "="
    return ch[0] * width


def print_header(title: str, *, subtitle: Optional[str] = None, width: int = 70, print_fn: PrintFn = print) -> None:
    print_fn("\n" + _line(width))
    print_fn(title)
    print_fn(_line(width))
    if subtitle:
        print_fn(subtitle)
        print_fn(_line(width))


def print_section(title: str, *, width: int = 50, print_fn: PrintFn = print) -> None:
    print_fn("\n" + _line(width, "-"))
    print_fn(title)
    print_fn(_line(width, "-"))


def print_kv(items: Mapping[str, Any], *, indent: str = "  ", bullet: str = "•", print_fn: PrintFn = print) -> None:
    for k, v in items.items():
        print_fn(f"{indent}{bullet} {k}: {v}")


def print_status(label: str, message: str, *, print_fn: PrintFn = print) -> None:
    print_fn(f"\n[{label}] {message}")


def print_success(message: str, *, print_fn: PrintFn = print) -> None:
    print_status("SUCCESS", message, print_fn=print_fn)


def print_error(message: str, *, print_fn: PrintFn = print) -> None:
    print_status("ERROR", message, print_fn=print_fn)


def print_warning(message: str, *, print_fn: PrintFn = print) -> None:
    print_status("WARN", message, print_fn=print_fn)


def print_info(message: str, *, print_fn: PrintFn = print) -> None:
    print_status("INFO", message, print_fn=print_fn)


def pause(prompt: str = "\nPress Enter to continue...", *, input_fn=input, print_fn: PrintFn = print) -> None:
    # In tests/CI stdin may be closed.
    try:
        input_fn(prompt)
    except EOFError:
        print_fn("")  # keep output stable but don't crash


def safe_input(prompt: str, *, default: Optional[str] = None, input_fn=input, print_fn: PrintFn = print) -> str:
    try:
        s = input_fn(prompt)
    except EOFError:
        if default is None:
            return ""
        print_fn(f"\n[INFO] EOF detected. Using default: {default}")
        return default
    return s
