from capstone_project_team_5 import main


def test_main() -> None:
    result = main()
    expected = "Hello from capstone-project-team-5!"
    assert result == expected


def test_main_return_type() -> None:
    result = main()
    assert isinstance(result, str)
