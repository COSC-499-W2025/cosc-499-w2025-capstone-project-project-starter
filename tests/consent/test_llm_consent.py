"""
Tests for LLM consent management functionality.

"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.consent.llm_consent_manager import LLMConsentManager


def read_config(path):
    """Helper to read JSON config file."""
    with open(path, 'r') as f:
        return json.load(f)


@pytest.fixture
def manager(tmp_path):
    """Create a fresh LLMConsentManager for each test."""
    config_path = tmp_path / "consent" / "llm.json"
    return LLMConsentManager(str(config_path))


class TestLLMConsent:
    """Test cases for LLMConsentManager class."""
    
    def test_default_state_no_consent(self, manager, tmp_path):
        """Ensure default consent is false and config file created."""
        assert not manager.has_consent()
        assert manager.get_consent_timestamp() is None
        
        config_path = tmp_path / "consent" / "llm.json"
        assert config_path.exists()
        
        config = read_config(config_path)
        assert config["consent_given"] is False
        assert config["consent_timestamp"] is None
        assert config["consent_type"] == "external_llm_data_access"
    
    def test_grant_consent_sets_true(self, manager, tmp_path):
        """Verify granting consent sets consent_given=True."""
        assert not manager.has_consent()
        
        manager.grant()
        assert manager.has_consent()
        
        config_path = tmp_path / "consent" / "llm.json"
        config = read_config(config_path)
        
        assert config["consent_given"] is True
        assert config["consent_timestamp"] is not None
        assert config["last_updated"] is not None
    
    def test_revoke_consent_sets_false(self, manager, tmp_path):
        """Verify revoking consent sets consent_given=False."""
        manager.grant()
        assert manager.has_consent()
        
        manager.revoke()
        assert not manager.has_consent()
        
        config_path = tmp_path / "consent" / "llm.json"
        config = read_config(config_path)
        
        assert config["consent_given"] is False
        assert config["consent_timestamp"] is not None
    
    def test_consent_timestamp_updates_after_grant(self, manager):
        """Verify timestamp is set after granting consent."""
        assert manager.get_consent_timestamp() is None
        
        manager.grant()
        timestamp = manager.get_consent_timestamp()
        
        assert timestamp is not None
        parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)
    
    def test_consent_timestamp_updates_after_revoke(self, manager):
        """Verify timestamp updates after revoking consent."""
        manager.grant()
        initial_timestamp = manager.get_consent_timestamp()
        
      
        import time
        time.sleep(0.1)
        
        manager.revoke()
        new_timestamp = manager.get_consent_timestamp()
        
        assert new_timestamp is not None
        assert new_timestamp != initial_timestamp
        
        parsed_timestamp = datetime.fromisoformat(new_timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_timestamp, datetime)
    
    def test_get_consent_info_complete_data(self, manager):
        """Verify get_consent_info returns all expected fields."""
        manager.grant()
        info = manager.get_consent_info()
        
        expected_fields = [
            "consent_given", "consent_timestamp", "consent_type",
            "last_updated", "version", "description", "config_path"
        ]
        
        for field in expected_fields:
            assert field in info
        
        assert info["consent_given"] is True
        assert info["consent_timestamp"] is not None
        assert info["consent_type"] == "external_llm_data_access"
        assert info["version"] == "1.0"
    
    def test_reset_consent_functionality(self, manager):
        """Verify reset revokes consent and preserves timestamp."""
        manager.grant()
        assert manager.has_consent()
        
        manager.reset()
        assert not manager.has_consent()
        assert manager.get_consent_timestamp() is not None
    
    def test_is_valid(self, manager):
        """Verify consent validation logic."""
        assert not manager.is_valid()
        
        manager.grant()
        assert manager.is_valid()
        
        manager.revoke()
        assert not manager.is_valid()
    
    def test_multiple_operations_preserve_state(self, manager):
        """Verify multiple operations maintain correct state."""
        assert not manager.has_consent()
        
        manager.grant()
        assert manager.has_consent()
        
        manager.revoke()
        assert not manager.has_consent()
        
        manager.grant()
        assert manager.has_consent()
        
        info = manager.get_consent_info()
        assert info["consent_given"] is True
        assert info["consent_timestamp"] is not None
    
    def test_corrupted_config_file_self_healing(self, manager, tmp_path):
        """Verify self-healing behavior with corrupted JSON."""
        config_path = tmp_path / "consent" / "llm.json"
  
        with open(config_path, 'w') as f:
            f.write("{ invalid json content")
        
       
        assert not manager.has_consent()
        
        manager.grant()
        assert manager.has_consent()
        
     
        config = read_config(config_path)
        assert config["consent_given"] is True
    
    def test_separation_from_directory_consent(self, manager, tmp_path):
        """Verify LLM consent is separate from directory access consent."""
        llm_config_path = tmp_path / "consent" / "llm.json"
        dir_config_path = tmp_path / "consent" / "directory.json"
        
        manager.grant()
        assert manager.has_consent()
        
        assert llm_config_path.exists()
        assert not dir_config_path.exists()
        
        config = read_config(llm_config_path)
        assert config["consent_type"] == "external_llm_data_access"
    
    def test_backward_compatibility_methods(self, manager):
        """Verify deprecated methods still work."""
        assert not manager.has_llm_consent()
        
        manager.grant_llm_consent()
        assert manager.has_llm_consent()
        
        manager.revoke_llm_consent()
        assert not manager.has_llm_consent()
        
        info = manager.get_llm_consent_info()
        assert "consent_given" in info
        
        manager.grant_llm_consent()
        manager.reset_llm_consent()
        assert not manager.has_llm_consent()
        
        assert not manager.is_llm_consent_valid()
    
    def test_config_file_structure(self, manager, tmp_path):
        """Verify config file has correct structure and metadata."""
        config_path = tmp_path / "consent" / "llm.json"
        config = read_config(config_path)
        
    
        assert "consent_given" in config
        assert "consent_timestamp" in config
        assert "consent_type" in config
        assert "version" in config
        assert "created_at" in config
        assert "description" in config
        
    
        assert config["consent_type"] == "external_llm_data_access"
        assert config["version"] == "1.0"
        assert "LLM data analysis" in config["description"]
        
      
        created_at = config["created_at"]
        parsed_created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        assert isinstance(parsed_created, datetime)
    
    def test_directory_creation(self, tmp_path):
        """Verify consent directory is created automatically."""
        config_path = tmp_path / "consent" / "llm.json"
        
     
        assert not config_path.parent.exists()
        
  
        manager = LLMConsentManager(str(config_path))
        assert config_path.parent.exists()
        assert config_path.exists()
    """ fixed the last test case """