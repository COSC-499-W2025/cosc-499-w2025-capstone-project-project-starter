# tests/test_pause.py
from __future__ import annotations

import io

from src.cli.cli_output import pause


def test_pause_calls_input_and_does_not_crash() -> None:
    calls: list[str] = []

    def fake_input(prompt: str) -> str:
        calls.append(prompt)
        return ""  # user pressed Enter

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    pause(input_fn=fake_input, print_fn=fake_print)

    assert len(calls) == 1
    assert "Press Enter" in calls[0]


def test_pause_handles_eoferror() -> None:
    def eof_input(prompt: str) -> str:
        raise EOFError()

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    # Should not raise
    pause(input_fn=eof_input, print_fn=fake_print)

    # safe_input prints an empty line for stability; pause should trigger it
    assert "\n" in out.getvalue()


def test_pause_handles_oserror() -> None:
    def os_error_input(prompt: str) -> str:
        raise OSError("pytest capture simulated")

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    # Should not raise
    pause(input_fn=os_error_input, print_fn=fake_print)

    assert "\n" in out.getvalue()
