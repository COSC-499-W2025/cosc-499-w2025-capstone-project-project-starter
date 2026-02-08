"""
Handles user consent for directory access.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from ..utils.jsonio import to_json, from_json


class DirectoryConsentManager:
    """Manages user consent specifically for directory access."""

    def __init__(self, config_path: str = "data/consent/directory.json"):
        """
        Initialize the manager and ensure configuration file exists.

        Args:
            config_path: Path to the JSON file storing consent data.
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            self._initialize_default_config()

    def _initialize_default_config(self) -> None:
        """Create a default consent file if none exists."""
        default_config = {
            "consent_given": False,
            "consent_timestamp": None,
            "consent_type": "directory_access",
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "description": "Consent for accessing user directory.",
            "allowed_paths": []
        }
        to_json(default_config, self.config_path)
        self.logger.info(f"Initialized default directory consent config at {self.config_path}")

    def _read_config(self) -> Dict[str, Any]:
        """Load the consent configuration from disk, re-initializing if corrupted."""
        try:
            return from_json(self.config_path)
        except Exception as e:
            self.logger.error(f"Error reading {self.config_path}: {e}")
            self.logger.info("Re-initializing corrupted directory consent config file")
            self._initialize_default_config()
            return from_json(self.config_path)

    def _write_config(self, config: Dict[str, Any]) -> None:
        """Save the updated consent configuration to disk."""
        try:
            to_json(config, self.config_path)
        except Exception as e:
            self.logger.error(f"Error writing {self.config_path}: {e}")
            raise

    def grant(self, allowed_paths: Optional[list] = None) -> None:
        """
        Grant user consent for directory access.
        
        Args:
            allowed_paths: List of directory paths that are allowed to be accessed.
        """
        config = self._read_config()
        now = datetime.now(timezone.utc).isoformat()
        
        update_data = {
            "consent_given": True,
            "consent_timestamp": now,
            "last_updated": now
        }
        
        if allowed_paths is not None:
            update_data["allowed_paths"] = [str(Path(path).resolve()) for path in allowed_paths]
            
        config.update(update_data)
        self._write_config(config)
        self.logger.info(f"Granted directory access consent at {now}")

    def revoke(self) -> None:
        """Revoke previously granted consent for directory access."""
        config = self._read_config()
        now = datetime.now(timezone.utc).isoformat()
        config.update({
            "consent_given": False,
            "consent_timestamp": now,
            "last_updated": now,
            "allowed_paths": []
        })
        self._write_config(config)
        self.logger.info(f"Revoked directory access consent at {now}")

    def has_consent(self) -> bool:
        """Return True if user has granted directory access consent."""
        return self._read_config().get("consent_given", False)

    def get_allowed_paths(self) -> list:
        """Return the list of allowed directory paths."""
        return self._read_config().get("allowed_paths", [])

    def get_consent_timestamp(self) -> Optional[str]:
        """Return the timestamp of the last consent update, if available."""
        return self._read_config().get("consent_timestamp")

    def get_consent_info(self) -> Dict[str, Any]:
        """Return all stored consent details."""
        cfg = self._read_config()
        return {
            "consent_given": cfg.get("consent_given", False),
            "consent_timestamp": cfg.get("consent_timestamp"),
            "consent_type": cfg.get("consent_type", "directory_access"),
            "last_updated": cfg.get("last_updated"),
            "version": cfg.get("version", "1.0"),
            "description": cfg.get("description", "Consent for directory access"),
            "allowed_paths": cfg.get("allowed_paths", []),
            "config_path": str(self.config_path)
        }

    def reset(self) -> None:
        """Reset consent to its default (revoked) state."""
        self.revoke()
        self.logger.info("Reset directory access consent configuration to default")

    def is_valid(self) -> bool:
        """
        Check if current consent is valid.
        For now, consent is valid if granted; add expiration checks later.
        """
        return self.has_consent()

   
    def grant_directory_consent(self, allowed_paths: Optional[list] = None) -> None:
        """Deprecated: use grant()."""
        self.logger.warning("grant_directory_consent() is deprecated, use grant() instead")
        self.grant(allowed_paths)

    def revoke_directory_consent(self) -> None:
        """Deprecated: use revoke()."""
        self.logger.warning("revoke_directory_consent() is deprecated, use revoke() instead")
        self.revoke()

    def has_directory_consent(self) -> bool:
        """Deprecated: use has_consent()."""
        self.logger.warning("has_directory_consent() is deprecated, use has_consent() instead")
        return self.has_consent()

    def get_directory_consent_timestamp(self) -> Optional[str]:
        """Deprecated: use get_consent_timestamp()."""
        self.logger.warning("get_directory_consent_timestamp() is deprecated, use get_consent_timestamp() instead")
        return self.get_consent_timestamp()

    def get_directory_consent_info(self) -> Dict[str, Any]:
        """Deprecated: use get_consent_info()."""
        self.logger.warning("get_directory_consent_info() is deprecated, use get_consent_info() instead")
        return self.get_consent_info()

    def reset_directory_consent(self) -> None:
        """Deprecated: use reset()."""
        self.logger.warning("reset_directory_consent() is deprecated, use reset() instead")
        self.reset()

    def is_directory_consent_valid(self) -> bool:
        """Deprecated: use is_valid()."""
        self.logger.warning("is_directory_consent_valid() is deprecated, use is_valid() instead")
        return self.is_valid()
