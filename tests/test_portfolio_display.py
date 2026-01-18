import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import portfolio.portfolio_display as pd  # noqa: E402


@patch("portfolio.portfolio_display.PortfolioFormatter")
@patch("portfolio.portfolio_display.PortfolioManager")
@patch("sys.stdout", new_callable=StringIO)
def test_display_portfolio_success(mock_stdout, mock_manager_cls, mock_formatter_cls):
    """display_portfolio should generate data and print formatted output."""
    mock_manager = mock_manager_cls.return_value
    mock_manager.generate_portfolio_report.return_value = {"projects": []}

    mock_formatter = mock_formatter_cls.return_value
    mock_formatter.get_formatted_portfolio.return_value = "FORMATTED"

    pd.display_portfolio(user_name="u1", format_type="text", top_n=3)

    mock_manager_cls.assert_called_once_with("u1")
    mock_manager.generate_portfolio_report.assert_called_once_with(top_n=3)
    mock_formatter.get_formatted_portfolio.assert_called_once_with({"projects": []}, "text")
    assert "FORMATTED" in mock_stdout.getvalue()


@patch("portfolio.portfolio_display.PortfolioFormatter")
@patch("portfolio.portfolio_display.PortfolioManager")
@patch("sys.stdout", new_callable=StringIO)
def test_display_portfolio_error(mock_stdout, mock_manager_cls, mock_formatter_cls):
    """Errors from portfolio generation should be shown and stop formatting."""
    mock_manager = mock_manager_cls.return_value
    mock_manager.generate_portfolio_report.return_value = {"error": "boom"}

    pd.display_portfolio()

    assert "Error generating portfolio: boom" in mock_stdout.getvalue()
    mock_formatter_cls.assert_not_called()


@patch("portfolio.portfolio_display.display_portfolio")
@patch("builtins.input", side_effect=["1", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_portfolio_menu_option_1(mock_stdout, mock_input, mock_display):
    """Menu option 1 should call display_portfolio with defaults."""
    pd.portfolio_menu()
    mock_display.assert_called_once_with()


@patch("portfolio.portfolio_display.display_portfolio")
@patch("builtins.input", side_effect=["2", ""])
def test_portfolio_menu_option_2(mock_input, mock_display):
    """Menu option 2 should call display_portfolio with top_n=5."""
    pd.portfolio_menu()
    mock_display.assert_called_once_with(top_n=5)


@patch("portfolio.portfolio_display.display_portfolio")
@patch("builtins.input", side_effect=["3", ""])
def test_portfolio_menu_option_3(mock_input, mock_display):
    """Menu option 3 should call display_portfolio with top_n=10."""
    pd.portfolio_menu()
    mock_display.assert_called_once_with(top_n=10)


@patch("portfolio.portfolio_display.PortfolioFormatter")
@patch("portfolio.portfolio_display.PortfolioManager")
@patch("builtins.input", side_effect=["4", "y", "out", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_portfolio_menu_option_4_save_markdown(mock_stdout, mock_input, mock_manager_cls, mock_formatter_cls):
    """Option 4 should format markdown and save to a file when user opts in."""
    mock_manager = mock_manager_cls.return_value
    mock_manager.generate_portfolio_report.return_value = {"projects": []}

    mock_formatter = mock_formatter_cls.return_value
    mock_formatter.format_markdown.return_value = "MD CONTENT"

    pd.portfolio_menu()

    # File should be written; verify via formatter call and file exists
    mock_formatter.format_markdown.assert_called_once_with({"projects": []})
    assert os.path.exists("out.md")
    with open("out.md", "r", encoding="utf-8") as f:
        assert "MD CONTENT" in f.read()
    os.remove("out.md")


@patch("portfolio.portfolio_display.PortfolioManager")
@patch("builtins.input", side_effect=["4", "n", ""])
@patch("sys.stdout", new_callable=StringIO)
def test_portfolio_menu_option_4_print_markdown(mock_stdout, mock_input, mock_manager_cls):
    """Option 4 should print markdown when not saving."""
    mock_manager = mock_manager_cls.return_value
    mock_manager.generate_portfolio_report.return_value = {"projects": []}

    with patch.object(pd.PortfolioFormatter, "format_markdown", return_value="MD CONTENT"):
        pd.portfolio_menu()
    assert "MD CONTENT" in mock_stdout.getvalue()


@patch("builtins.input", return_value="5")
def test_portfolio_menu_option_5(mock_input):
    """Option 5 exits the menu."""
    pd.portfolio_menu()


@patch("builtins.input", return_value="bad")
@patch("sys.stdout", new_callable=StringIO)
def test_portfolio_menu_invalid_choice(mock_stdout, mock_input):
    """Invalid choice should prompt an error message."""
    pd.portfolio_menu()
    assert "Invalid choice" in mock_stdout.getvalue()

