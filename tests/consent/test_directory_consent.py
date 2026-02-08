"""
Tests for directory consent management functionality.

"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.consent.directory_consent_manager import DirectoryConsentManager


def read_config(path):
    """Helper to read JSON config file."""
    with open(path, 'r') as f:
        return json.load(f)


@pytest.fixture
def manager(tmp_path):
    """Create a fresh DirectoryConsentManager for each test."""
    config_path = tmp_path / "consent" / "directory.json"
    return DirectoryConsentManager(str(config_path))


class TestDirectoryConsent:
    """Test cases for DirectoryConsentManager class."""
    
    def test_default_state_no_consent(self, manager, tmp_path):
        """Ensure default consent is false and config file created."""
        assert not manager.has_consent()
        assert manager.get_consent_timestamp() is None
        assert manager.get_allowed_paths() == []
        
        config_path = tmp_path / "consent" / "directory.json"
        assert config_path.exists()
        
        config = read_config(config_path)
        assert config["consent_given"] is False
        assert config["consent_timestamp"] is None
        assert config["consent_type"] == "directory_access"
        assert config["allowed_paths"] == []
    
    def test_grant_consent_sets_true(self, manager, tmp_path):
        """Verify granting consent sets consent_given=True."""
        assert not manager.has_consent()
        
        manager.grant()
        assert manager.has_consent()
        
        config_path = tmp_path / "consent" / "directory.json"
        config = read_config(config_path)
        
        assert config["consent_given"] is True
        assert config["consent_timestamp"] is not None
        assert config["last_updated"] is not None
    
    def test_grant_consent_with_paths(self, manager, tmp_path):
        """Verify granting consent with specific paths."""
        test_paths = ["/path/to/dir1", "/another/path"]
        manager.grant(allowed_paths=test_paths)
        
        assert manager.has_consent()
        assert set(manager.get_allowed_paths()) == set(test_paths)
        
        config_path = tmp_path / "consent" / "directory.json"
        config = read_config(config_path)
        
        assert set(config["allowed_paths"]) == set(test_paths)
    
    def test_revoke_consent_sets_false_and_clears_paths(self, manager, tmp_path):
        """Verify revoking consent sets consent_given=False and clears paths."""
        manager.grant(allowed_paths=["/test/path"])
        assert manager.has_consent()
        assert manager.get_allowed_paths() == ["/test/path"]
        
        manager.revoke()
        assert not manager.has_consent()
        assert manager.get_allowed_paths() == []
        
        config_path = tmp_path / "consent" / "directory.json"
        config = read_config(config_path)
        
        assert config["consent_given"] is False
        assert config["consent_timestamp"] is not None
        assert config["allowed_paths"] == []
    
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
        test_paths = ["/test/path1", "/test/path2"]
        manager.grant(allowed_paths=test_paths)
        info = manager.get_consent_info()
        
        expected_fields = [
            "consent_given", "consent_timestamp", "consent_type",
            "last_updated", "version", "description", "config_path",
            "allowed_paths"
        ]
        
        for field in expected_fields:
            assert field in info
        
        assert info["consent_given"] is True
        assert info["consent_timestamp"] is not None
        assert info["consent_type"] == "directory_access"
        assert info["version"] == "1.0"
        assert set(info["allowed_paths"]) == set(["/test/path1", "/test/path2"])
    
    def test_reset_consent_functionality(self, manager):
        """Verify reset revokes consent and preserves timestamp."""
        manager.grant(allowed_paths=["/test/path"])
        assert manager.has_consent()
        assert manager.get_allowed_paths() == ["/test/path"]
        
        manager.reset()
        assert not manager.has_consent()
        assert manager.get_consent_timestamp() is not None
        assert manager.get_allowed_paths() == []
    
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
        assert manager.get_allowed_paths() == []
        
      
        manager.grant()
        assert manager.has_consent()
        assert manager.get_allowed_paths() == []
        
     
        manager.revoke()
        assert not manager.has_consent()
        assert manager.get_allowed_paths() == []
        
      
        test_paths = ["/path/one", "/path/two"]
        manager.grant(allowed_paths=test_paths)
        assert manager.has_consent()
        assert set(manager.get_allowed_paths()) == set(test_paths)
        
        
        manager.revoke()
        assert not manager.has_consent()
        assert manager.get_allowed_paths() == []
    
    def test_corrupted_config_file_self_healing(self, manager, tmp_path):
        """Verify self-healing behavior with corrupted JSON."""
        config_path = tmp_path / "consent" / "directory.json"
        
        
        with open(config_path, 'w') as f:
            f.write("{ invalid json content")
        
      
        assert not manager.has_consent()
        
        test_paths = ["/test/path"]
        manager.grant(allowed_paths=test_paths)
        assert manager.has_consent()
        assert manager.get_allowed_paths() == test_paths
        
       
        config = read_config(config_path)
        assert config["consent_given"] is True
        assert config["allowed_paths"] == test_paths
    
    def test_separation_from_llm_consent(self, manager, tmp_path):
        """Verify directory consent is separate from LLM consent."""
        dir_config_path = tmp_path / "consent" / "directory.json"
        llm_config_path = tmp_path / "consent" / "llm.json"
        
        
        manager.grant(allowed_paths=["/test/path"])
        assert manager.has_consent()
        
        
        assert dir_config_path.exists()
        dir_config = read_config(dir_config_path)
        assert dir_config["consent_type"] == "directory_access"
        

        assert not llm_config_path.exists()
    
    def test_backward_compatibility_methods(self, manager):
        """Verify deprecated methods still work."""
        assert not manager.has_directory_consent()
        
        manager.grant_directory_consent(["/test/path"])
        assert manager.has_directory_consent()
        assert manager.get_allowed_paths() == ["/test/path"]
        
        manager.revoke_directory_consent()
        assert not manager.has_directory_consent()
        
      
        manager.grant_directory_consent()
        assert manager.is_directory_consent_valid()
        assert manager.get_directory_consent_timestamp() is not None
        assert "consent_given" in manager.get_directory_consent_info()
        
        manager.reset_directory_consent()
        assert not manager.has_directory_consent()
