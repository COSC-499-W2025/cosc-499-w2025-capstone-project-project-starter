# tests/test_main_menu_noninteractive.py
from __future__ import annotations

import sys
import types
import importlib


def test_run_main_menu_exits_immediately_in_github_actions(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    # Ensure a clean import of main_menu for this test only
    sys.modules.pop("src.cli.main_menu", None)

    # ---- Fake src.cli.menus (avoid importing real menus.py) ----
    fake_menus = types.ModuleType("src.cli.menus")
    fake_menus.project_menu = lambda: None
    fake_menus.analysis_menu = lambda: None
    fake_menus.handle_rank_projects = lambda: None
    fake_menus.handle_rank_and_summarize_projects = lambda: None
    fake_menus.handle_view_edit_rankings = lambda: None
    fake_menus.settings_menu = lambda *_args, **_kwargs: None
    fake_menus.resume_menu = lambda: None
    fake_menus.portfolio_menu = lambda: None
    fake_menus.handle_zip_success_report = lambda: None
    monkeypatch.setitem(sys.modules, "src.cli.menus", fake_menus)

    # ---- Fake account.user_manager (avoid ModuleNotFoundError: account) ----
    fake_account = types.ModuleType("account")
    fake_user_manager = types.ModuleType("account.user_manager")

    class FakeAuthManager:
        logged_in = True
        user = "test_user"
        logged_out = False

        @staticmethod
        def is_user_logged_in() -> bool:
            return FakeAuthManager.logged_in

        @staticmethod
        def get_current_username() -> str:
            return FakeAuthManager.user

        @staticmethod
        def logout() -> None:
            FakeAuthManager.logged_out = True
            FakeAuthManager.logged_in = False

    fake_user_manager.AuthManager = FakeAuthManager
    monkeypatch.setitem(sys.modules, "account", fake_account)
    monkeypatch.setitem(sys.modules, "account.user_manager", fake_user_manager)

    # ---- Map "cli.cli_output" absolute import to the real src.cli.cli_output ----
    real_cli_output = importlib.import_module("src.cli.cli_output")
    fake_cli_pkg = types.ModuleType("cli")
    monkeypatch.setitem(sys.modules, "cli", fake_cli_pkg)
    monkeypatch.setitem(sys.modules, "cli.cli_output", real_cli_output)

    # ---- Import main_menu safely now ----
    main_menu = importlib.import_module("src.cli.main_menu")

    main_menu.run_main_menu(consent_manager=None, collab_manager=None)

    assert FakeAuthManager.logged_out is True
