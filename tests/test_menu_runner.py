# tests/test_menu_runner.py
from __future__ import annotations

import io
from src.cli.menu_runner import MenuSpec, run_menu


def test_run_menu_handles_invalid_then_back() -> None:
    inputs = iter(["abc", "9", "2"])  # invalid, out-of-range, then BACK

    def fake_input(prompt: str) -> str:
        return next(inputs)

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    spec = MenuSpec(
        title="TEST MENU",
        options=["Do Thing", "Back"],
        prompt="Choose an option",
    )

    handlers = {
        "1": lambda: None,
        "2": "BACK",
    }

    result = run_menu(spec, handlers, input_fn=fake_input, print_fn=fake_print)
    text = out.getvalue()

    assert "Invalid choice" in text
    assert result == "BACK"

def test_run_menu_returns_eof_on_eoferror() -> None:
    def eof_input(prompt: str) -> str:
        raise EOFError()

    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    spec = MenuSpec(
        title="EOF MENU",
        options=["Back"],
        prompt="Choose an option",
    )

    handlers = {"1": "BACK"}

    result = run_menu(spec, handlers, input_fn=eof_input, print_fn=fake_print)
    text = out.getvalue()

    assert result == "EOF"
    assert "EOF received" in text
