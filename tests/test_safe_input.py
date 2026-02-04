# tests/test_safe_input.py
from __future__ import annotations

import io

from src.cli.cli_output import safe_input


def test_safe_input_strips_whitespace() -> None:
    inputs = iter(["   3   "])

    def fake_input(prompt: str) -> str:
        return next(inputs)

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    result = safe_input("Choose: ", input_fn=fake_input, default="X", print_fn=fake_print)
    assert result == "3"


def test_safe_input_returns_default_on_empty_string() -> None:
    inputs = iter([""])

    def fake_input(prompt: str) -> str:
        return next(inputs)

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    result = safe_input("Choose: ", input_fn=fake_input, default="10", print_fn=fake_print)
    assert result == "10"


def test_safe_input_returns_default_on_eoferror() -> None:
    def eof_input(prompt: str) -> str:
        raise EOFError()

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    result = safe_input("Choose: ", input_fn=eof_input, default="10", print_fn=fake_print)
    assert result == "10"

    # safe_input prints an empty line to keep output stable (no crash)
    text = out.getvalue()
    assert "\n" in text


def test_safe_input_returns_default_on_oserror() -> None:
    def os_error_input(prompt: str) -> str:
        raise OSError("pytest capture simulated")

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    result = safe_input("Choose: ", input_fn=os_error_input, default="10", print_fn=fake_print)
    assert result == "10"

    text = out.getvalue()
    assert "\n" in text
