# src/cli/menu_runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union, Any


Handler = Callable[[], Any]
HandlerOrSentinel = Union[Handler, str]  # "BACK" / "EXIT"


@dataclass(frozen=True)
class MenuSpec:
    title: str
    options: List[str]
    prompt: str = "Choose an option"
    min_choice: int = 1  # usually 1
    show_header: bool = True


def _print_menu(spec: MenuSpec, print_fn: Callable[[str], None]) -> None:
    if spec.show_header:
        print_fn("\n" + "=" * 70)
        print_fn(spec.title)
        print_fn("=" * 70)

    for idx, option in enumerate(spec.options, start=1):
        print_fn(f"{idx}. {option}")

    print_fn("=" * 70)


def run_menu(
    spec: MenuSpec,
    handlers: Dict[str, HandlerOrSentinel],
    *,
    input_fn: Optional[Callable[[str], str]] = None,
    print_fn: Callable[[str], None] = print,
    pause_after_action: bool = False,
) -> str:
    """
    Run a CLI menu loop.

    - handlers keys are string numbers: "1", "2", ...
    - handlers values are callables or sentinel strings: "BACK", "EXIT"

    Returns:
        "BACK" if user chose a BACK option or handler returns BACK
        "EXIT" if user chose EXIT
        "EOF"  if stdin closed
    """
    if input_fn is None:
        input_fn = input
    
    max_choice = len(spec.options)

    while True:
        _print_menu(spec, print_fn)

        try:
            raw = input_fn(f"{spec.prompt} ({spec.min_choice}-{max_choice}): ").strip()
        except (EOFError, OSError):
            print_fn("\n[INFO] Input unavailable (EOF/OSError). Exiting menu.")
            return "EOF"

        if not raw.isdigit():
            print_fn("Invalid choice. Please enter a number.")
            continue

        choice_int = int(raw)
        if choice_int < spec.min_choice or choice_int > max_choice:
            print_fn(f"Invalid choice. Please enter {spec.min_choice}-{max_choice}.")
            continue

        choice_key = str(choice_int)
        handler = handlers.get(choice_key)

        if handler is None:
            print_fn("Invalid choice. Please try again.")
            continue

        # Sentinel handling
        if isinstance(handler, str):
            sentinel = handler.upper()
            if sentinel in ("BACK", "EXIT"):
                return sentinel
            print_fn("Invalid menu configuration (unknown sentinel).")
            continue

        # Callable handler
        result = handler()
        if isinstance(result, str) and result.upper() in ("BACK", "EXIT"):
            return result.upper()

        if pause_after_action:
            try:
                input_fn("\nPress Enter to continue...")
            except (EOFError, OSError):
                return "EOF"
            continue
