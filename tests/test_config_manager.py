import json
import os
import tempfile
import pytest

from src.validator.config_manager import (
    load_config,
    save_config,
    get_config_value,
    set_config_value
)


@pytest.fixture
def temp_config_env():
    """
    Creates a temporary directory acting as .vscode/
    Ensures tests never touch real user config.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        yield temp_dir, config_path


# ---------------------- TESTS ---------------------- #


def test_load_config_creates_file_if_missing(temp_config_env):
    temp_dir, config_path = temp_config_env

    cfg = load_config(config_path)

    assert isinstance(cfg, dict)
    assert os.path.exists(config_path)


def test_save_config_creates_and_writes_file(temp_config_env):
    temp_dir, config_path = temp_config_env

    sample_cfg = {"consent": True, "lastZip": "/path/to/project.zip"}
    save_config(sample_cfg, config_path)

    assert os.path.exists(config_path)

    with open(config_path, "r") as f:
        loaded = json.load(f)

    assert loaded == sample_cfg


def test_get_config_value_existing_key(temp_config_env):
    temp_dir, config_path = temp_config_env

    save_config({"consent": False}, config_path)

    cfg = load_config(config_path)
    assert get_config_value(cfg, "consent") is False


def test_get_config_value_missing_key_returns_none(temp_config_env):
    temp_dir, config_path = temp_config_env

    save_config({}, config_path)
    cfg = load_config(config_path)

    assert get_config_value(cfg, "missing_key") is None


def test_set_config_value_updates_dict(temp_config_env):
    temp_dir, config_path = temp_config_env

    cfg = load_config(config_path)

    set_config_value(cfg, "consent", True)
    assert cfg["consent"] is True


def test_set_config_value_persists_to_disk(temp_config_env):
    temp_dir, config_path = temp_config_env

    cfg = load_config(config_path)
    set_config_value(cfg, "consent", True)

    save_config(cfg, config_path)

    with open(config_path, "r") as f:
        reloaded = json.load(f)

    assert reloaded["consent"] is True


def test_config_persists_across_multiple_loads(temp_config_env):
    temp_dir, config_path = temp_config_env

    cfg1 = load_config(config_path)
    set_config_value(cfg1, "language", "python")
    save_config(cfg1, config_path)

    # Load again
    cfg2 = load_config(config_path)

    assert cfg2["language"] == "python"
