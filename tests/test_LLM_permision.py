import json
from pathlib import Path
import pytest
from src.validator import LLM_permission as esc

@pytest.fixture(autouse=True)
def temp_config(monkeypatch, tmp_path):
    """Redirect config path to a temporary file for each test."""
    fake_config = tmp_path / "config.json"
    monkeypatch.setattr(esc, "CONFIG_PATH", fake_config)
    yield fake_config

def test_user_declines(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "no")
    result = esc.request_external_service_permission("FakeService", "some data")
    assert result is False

def test_user_accepts(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    result = esc.request_external_service_permission("FakeService", "some data")
    assert result is True

def test_stored_preference(monkeypatch, temp_config):
    # Save previous consent
    with open(temp_config, "w") as f:
        json.dump({"external_services": {"FakeService": True}}, f)
    # Should not ask again
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(Exception("Should not prompt")))
    result = esc.request_external_service_permission("FakeService", "some data")
    assert result is True

def test_invalid_config_json(monkeypatch, temp_config):
    # Write invalid JSON
    temp_config.write_text("{bad json")
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    result = esc.request_external_service_permission("FakeService", "some data")
    assert result is True

def test_case_insensitive_input(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "Y")
    result = esc.request_external_service_permission("FakeService", "some data")
    assert result is True
