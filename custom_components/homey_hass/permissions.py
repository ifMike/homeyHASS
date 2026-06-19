"""Permission checking and validation for Homey API."""
from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class PermissionChecker:
    """Helper class to check API permissions and log warnings."""
    
    # Permission requirements for each feature
    # Using actual Homey API permission names
    PERMISSIONS = {
        "devices": {
            "read": "homey.device.readonly",
            "write": "homey.device.control",
        },
        "flows": {
            "read": "homey.flow.readonly",
            "write": "homey.flow.start",
        },
        "zones": {
            "read": "homey.zone.readonly",
        },
        "scenes": {
            # Note: Scenes may not have separate permissions in Homey API v3
            # They might be controlled via device.control or flow.start
            "read": "homey.device.readonly",  # Scenes are likely accessible via device read
            "write": "homey.device.control",  # Scene activation likely uses device control
        },
        "moods": {
            "read": "homey.mood.readonly",
            "write": "homey.mood.set",
        },
        "logic": {
            "read": "homey.logic.readonly",
            "write": "homey.logic",
        },
    }
    
    @staticmethod
    def check_permission(
        response_status: int,
        feature: str,
        permission_type: str,
        operation: str = "",
    ) -> bool:
        """Check if a response status indicates missing permissions.
        
        Args:
            response_status: HTTP response status code
            feature: Feature name (devices, flows, zones, scenes, moods)
            permission_type: Permission type (read, write)
            operation: Optional operation description for logging
            
        Returns:
            True if permission appears to be missing, False otherwise
        """
        if response_status == 401:
            permission = PermissionChecker.PERMISSIONS.get(feature, {}).get(permission_type, f"{feature}:{permission_type}")
            _LOGGER.warning(
                "Authentication failed (401) for %s%s. Your API key may be missing the '%s' permission. "
                "Go to Homey Settings → API Keys to update permissions.",
                feature,
                f" ({operation})" if operation else "",
                permission,
            )
            return True
        elif response_status == 403:
            permission = PermissionChecker.PERMISSIONS.get(feature, {}).get(permission_type, f"{feature}:{permission_type}")
            _LOGGER.warning(
                "Access forbidden (403) for %s%s. Your API key is missing the '%s' permission. "
                "Go to Homey Settings → API Keys to enable '%s' permission.",
                feature,
                f" ({operation})" if operation else "",
                permission,
                permission,
            )
            return True
        return False
    
    @staticmethod
    def log_missing_permission(feature: str, permission_type: str, impact: str) -> None:
        """Log a warning about missing permissions.
        
        Args:
            feature: Feature name (devices, flows, zones, scenes, moods)
            permission_type: Permission type (read, write)
            impact: Description of what won't work without this permission
        """
        permission = PermissionChecker.PERMISSIONS.get(feature, {}).get(permission_type, f"{feature}:{permission_type}")
        _LOGGER.warning(
            "%s feature is disabled: Missing '%s' permission. %s "
            "To enable this feature, go to Homey Settings → API Keys and enable '%s' permission.",
            feature.title(),
            permission,
            impact,
            permission,
        )
