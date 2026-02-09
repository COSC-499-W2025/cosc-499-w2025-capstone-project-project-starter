# tests/test_print_formatting.py
from __future__ import annotations

import io

from src.cli.cli_output import (
    print_header,
    print_section,
    print_kv,
    print_status,
    print_success,
    print_error,
    print_warning,
    print_info,
)


def test_print_header_basic_title_only() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_header("HELLO", print_fn=fake_print)

    text = out.getvalue()
    lines = [ln for ln in text.splitlines() if ln != ""]

    # Expect: line, title, line
    assert len(lines) >= 3
    assert lines[0] == "=" * 70
    assert lines[1] == "HELLO"
    assert lines[2] == "=" * 70


def test_print_header_with_subtitle_adds_extra_line_block() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_header("TITLE", subtitle="sub", print_fn=fake_print)

    text = out.getvalue()
    lines = [ln for ln in text.splitlines() if ln != ""]

    # Expect: line, title, line, subtitle, line
    assert lines[0] == "=" * 70
    assert lines[1] == "TITLE"
    assert lines[2] == "=" * 70
    assert lines[3] == "sub"
    assert lines[4] == "=" * 70


def test_print_header_respects_width() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_header("X", width=10, print_fn=fake_print)

    lines = [ln for ln in out.getvalue().splitlines() if ln != ""]
    assert lines[0] == "=" * 10
    assert lines[2] == "=" * 10


def test_print_section_uses_dashes_and_default_width() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_section("SEC", print_fn=fake_print)

    lines = [ln for ln in out.getvalue().splitlines() if ln != ""]
    assert lines[0] == "-" * 50
    assert lines[1] == "SEC"
    assert lines[2] == "-" * 50


def test_print_kv_formats_items_with_indent_and_bullet() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_kv({"a": 1, "b": "two"}, indent="  ", bullet="•", print_fn=fake_print)

    text = out.getvalue()
    assert "• a: 1" in text
    assert "• b: two" in text
    assert text.splitlines()[0].startswith("  • ")


def test_print_status_and_shortcuts_use_labels() -> None:
    out = io.StringIO()

    def fake_print(msg: str) -> None:
        out.write(msg + "\n")

    print_status("TAG", "hello", print_fn=fake_print)
    print_success("ok", print_fn=fake_print)
    print_error("bad", print_fn=fake_print)
    print_warning("warn", print_fn=fake_print)
    print_info("info", print_fn=fake_print)

    text = out.getvalue()
    assert "[TAG] hello" in text
    assert "[SUCCESS] ok" in text
    assert "[ERROR] bad" in text
    assert "[WARN] warn" in text
    assert "[INFO] info" in text
