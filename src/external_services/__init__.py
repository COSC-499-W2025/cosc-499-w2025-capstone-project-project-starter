# src/external_services/__init__.py
"""
External services module for managing permissions and external API integrations.
Implements Issue #10 and its sub-issues.
"""

from .permission_manager import ExternalServicePermission
from .service_config import ServiceConfig
from .external_service_prompt import (
    ExternalServicePrompt,
    request_external_service_permission
)
__all__ = [
    'ExternalServicePermission',
    'ServiceConfig',
    'ExternalServicePrompt',
    'request_external_service_permission'
]
