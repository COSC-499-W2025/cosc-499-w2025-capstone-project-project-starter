"""
User consent management module for data access.

This module provides functionality to manage different types of user consents:
- LLM data access consent
- Directory access consent
"""

from .llm_consent_manager import LLMConsentManager
from .directory_consent_manager import DirectoryConsentManager

__all__ = ['LLMConsentManager', 'DirectoryConsentManager']