"""Homey API client."""
from __future__ import annotations

import asyncio
import logging
import ssl
import time
from collections.abc import Callable
from typing import Any

import aiohttp
import socketio
from urllib.parse import quote

from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    API_BASE_V1,
    API_BASE_MANAGER,
    API_DEVICES,
    API_DEVICES_NO_SLASH,
    API_DEVICES_V1,
    API_FLOWS,
    API_ADVANCED_FLOWS,
    API_SYSTEM,
    API_ZONES,
    API_SCENES,
    API_MOODS,
    API_LOGIC_VARIABLES,
)
from .permissions import PermissionChecker

_LOGGER = logging.getLogger(__name__)


class HomeyAPI:
    """Homey API client."""

    def __init__(self, host: str, token: str, preferred_endpoint: str | None = None) -> None:
        """Initialize the Homey API client."""
        host = (host or "").strip().rstrip("/")
        if host and not host.startswith(("http://", "https://")):
            host = f"http://{host}"
        self.host = host
        self.token = token
        self.preferred_endpoint = preferred_endpoint  # "manager" or "v1"
        self.session: aiohttp.ClientSession | None = None
        self.sio: socketio.AsyncClient | None = None  # Single client for both root and /api namespace
        self.homey_id: str | None = None  # Homey device ID for Socket.IO authentication
        self.sio_namespace: str | None = None  # Namespace received from handshakeClient
        self.sio_token: str | None = None  # Token received from handshakeClient (used for Socket.IO auth)
        self._api_connected_evt: asyncio.Event | None = None  # Event to track /api namespace connection
        self._api_connect_error: Any = None  # Store /api namespace connect error if any
        self._sio_connecting: bool = False  # Flag to prevent reconnect during connection setup
        self.devices: dict[str, dict[str, Any]] = {}
        self.flows: dict[str, dict[str, Any]] = {}
        self.zones: dict[str, dict[str, Any]] = {}  # Rooms/zones
        self.scenes: dict[str, dict[str, Any]] = {}  # Scenes
        self.moods: dict[str, dict[str, Any]] = {}  # Moods
        self.logic_variables: dict[str, dict[str, Any]] = {}  # Logic variables
        self._listeners: list[Callable[[str, dict[str, Any]], None]] = []
        self._sio_connected: bool = False
        self._sio_reconnect_task: asyncio.Task | None = None
        self._sio_reconnect_interval: int = 60  # Try to reconnect every 60 seconds
        self._sio_last_reconnect_attempt: float = 0
        self._sio_http_session: aiohttp.ClientSession | None = None  # Must be closed on disconnect
        self._polling_logged: bool = False  # Track if we've logged polling status
        self._auth_failure_count: int = 0
        self._last_auth_failure: float | None = None
        self._last_polling_error_log: float = 0  # Rate limit repeated polling errors
        self._last_sio_error_log: float = 0  # Rate limit repeated Socket.IO errors
        self._ERROR_LOG_INTERVAL: float = 300  # Log at ERROR/WARNING at most every 5 min

    async def connect(self) -> None:
        """Connect to Homey API."""
        _LOGGER.info("Connecting to Homey at %s", self.host)
        # Warn if using mDNS (.local) - can resolve to unstable interface (e.g. WiFi 192.168.3.x)
        if ".local" in self.host.lower():
            _LOGGER.warning(
                "Using mDNS hostname (%s) - if you have connection issues or toggles fail, "
                "use static IP in Options (e.g. http://192.168.1.32 for Ethernet)",
                self.host,
            )
        # Detect if using HTTPS for SSL handling
        # For HTTPS connections (self-hosted servers), we need SSL but disable verification for self-signed certs
        # For HTTP connections (local Homey), disable SSL entirely
        use_https = self.host.startswith("https://")
        if use_https:
            # For HTTPS: create SSL context that doesn't verify certificates (for self-signed certs)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        else:
            # For HTTP: disable SSL entirely
            connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=aiohttp.ClientTimeout(total=30),
        )

        # Socket.IO connection will be established after authentication
        # We need homeyId from system info first, so Socket.IO is initialized later
        self.sio = None
        self._sio_connected = False

    async def authenticate(self) -> bool:
        """Authenticate with Homey API."""
        if not self.session:
            return False

        # Try multiple possible system endpoints
        # Note: /api/manager/system works (returns cloudId), /api/manager/system/info returns 404
        endpoints_to_try = [
            f"{API_BASE_MANAGER}/system",  # /api/manager/system - this works and returns cloudId
            f"{API_BASE_MANAGER}/system/",  # /api/manager/system/ - with trailing slash
            API_SYSTEM,  # /api/manager/system/info - fallback
            f"{API_BASE_V1}/manager/system/info",
            f"{API_BASE_V1}/manager/system",
            f"{API_BASE_V1}/system/info",
            f"{API_BASE_V1}/system",
        ]

        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        system_info = await response.json()
                        # Store homeyId for Socket.IO authentication
                        # Try multiple possible fields: cloudId (from system.getInfo()), id, homeyId
                        self.homey_id = (
                            system_info.get("cloudId") or 
                            system_info.get("id") or 
                            system_info.get("homeyId")
                        )
                        _LOGGER.info("Connected to Homey: %s (ID: %s)", 
                                   system_info.get("name") or system_info.get("homeyName") or system_info.get("hostname", "").split(".")[0],
                                   self.homey_id or "unknown")
                        # Attempt Socket.IO connection after successful authentication
                        # This is non-blocking - if it fails, we'll use polling
                        _LOGGER.info("Attempting Socket.IO connection for real-time updates...")
                        try:
                            success = await self._connect_socketio()
                            if not success:
                                _LOGGER.info("Socket.IO connection failed - will use polling (1 second interval)")
                        except Exception as err:
                            _LOGGER.error("Socket.IO connection attempt failed with exception: %s - will use polling", err, exc_info=True)
                        return True
                    elif response.status == 404:
                        _LOGGER.debug("Endpoint %s not found, trying next...", endpoint)
                        continue
                    elif response.status == 401:
                        _LOGGER.error("Authentication failed: Invalid API token")
                        return False
                    else:
                        _LOGGER.debug("Authentication failed with %s: %s", endpoint, response.status)
                        continue
            except Exception as err:
                _LOGGER.debug("Error trying endpoint %s: %s", endpoint, err)
                continue
        
        # If system endpoints don't work, try devices endpoint as fallback
        # This verifies the API is accessible even if system info isn't available
        _LOGGER.debug("System endpoints not available, verifying connection with devices endpoint")
        try:
            devices = await self.get_devices()
            # If get_devices() returns (even empty dict), API is accessible
            _LOGGER.info("API connection verified via devices endpoint")
            return True
        except Exception as err:
            _LOGGER.warning("Could not verify connection to any Homey API endpoint: %s", err)
            return False

    async def get_devices(self) -> dict[str, dict[str, Any]]:
        """Get all devices from Homey."""
        if not self.session:
            return {}

        # Try preferred endpoint first, then fallback
        if self.preferred_endpoint == "manager":
            endpoints_to_try = [
                API_DEVICES,  # /api/manager/devices/device/
                API_DEVICES_NO_SLASH,  # /api/manager/devices/device
                API_DEVICES_V1,  # /api/v1/device
                f"{API_DEVICES_V1}/",  # /api/v1/device/
            ]
        elif self.preferred_endpoint == "v1":
            endpoints_to_try = [
                API_DEVICES_V1,  # /api/v1/device
                f"{API_DEVICES_V1}/",  # /api/v1/device/
                API_DEVICES,  # /api/manager/devices/device/
                API_DEVICES_NO_SLASH,  # /api/manager/devices/device
            ]
        else:
            # Try manager API first, then fallback to v1
            endpoints_to_try = [
                API_DEVICES,  # /api/manager/devices/device/
                API_DEVICES_NO_SLASH,  # /api/manager/devices/device
                API_DEVICES_V1,  # /api/v1/device
                f"{API_DEVICES_V1}/",  # /api/v1/device/
            ]
        
        auth_error_count = 0
        last_connection_error: Exception | None = None
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        devices_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(devices_data, dict):
                            # If it's an object, convert to dict of devices
                            self.devices = devices_data
                        else:
                            # If it's an array, convert to dict keyed by id
                            self.devices = {device["id"]: device for device in devices_data}
                        # Only log once at startup, then silently poll
                        if not self._polling_logged:
                            _LOGGER.info("Polling working - successfully retrieved %d devices using endpoint: %s", len(self.devices), endpoint)
                            self._polling_logged = True
                        # Reset auth failure tracking on success
                        self._auth_failure_count = 0
                        self._last_auth_failure = None
                        self._last_polling_error_log = 0  # Reset on success
                        return self.devices
                    elif response.status == 401:
                        auth_error_count += 1
                        _LOGGER.warning(
                            "Authentication failed (401) for devices endpoint %s. "
                            "This can trigger reauth if repeated. Possible causes: "
                            "token invalidated on Homey, hub temporarily unreachable, "
                            "or host resolves to a different Homey in multi-hub setups.",
                            endpoint,
                        )
                        continue
                    elif response.status == 404:
                        _LOGGER.debug("Endpoint %s not found, trying next...", endpoint)
                        continue
                    else:
                        _LOGGER.debug("Failed to get devices from %s: %s", endpoint, response.status)
                        continue
            except Exception as err:
                last_connection_error = err
                _LOGGER.debug("Error getting devices from %s: %s", endpoint, err)
                continue
        
        # If all endpoints returned 401, treat as auth failure only after repeated occurrences
        if auth_error_count == len(endpoints_to_try):
            now = time.time()
            if self._last_auth_failure and now - self._last_auth_failure > 300:
                # Reset counter if last failure was long ago
                self._auth_failure_count = 0
            self._auth_failure_count += 1
            self._last_auth_failure = now

            if self._auth_failure_count >= 3:
                raise ConfigEntryAuthFailed("Invalid API key (repeated 401)")

            _LOGGER.warning(
                "Received 401 from all device endpoints (%d/%d). "
                "Deferring reauth until repeated failures. "
                "If this happens nightly on a secondary hub, verify that each hub "
                "uses a unique host (avoid shared mDNS like homey.local), and that "
                "the API key remains valid for that hub.",
                self._auth_failure_count,
                len(endpoints_to_try),
            )
            return self.devices or {}

        # Rate limit: log at ERROR on first occurrence, then at most every 5 min
        now = time.time()
        if now - self._last_polling_error_log >= self._ERROR_LOG_INTERVAL:
            self._last_polling_error_log = now
            err_detail = f": {last_connection_error}" if last_connection_error else ""
            if self._polling_logged:
                _LOGGER.error(
                    "Polling failed - unable to retrieve devices from any endpoint (host=%s)%s",
                    self.host,
                    err_detail,
                )
            else:
                _LOGGER.error(
                    "Failed to retrieve devices from any endpoint (host=%s)%s",
                    self.host,
                    err_detail,
                )
        else:
            _LOGGER.debug("Polling failed (rate limited) - unable to retrieve devices")
        return {}

    async def get_device(self, device_id: str) -> dict[str, Any] | None:
        """Get a specific device."""
        if not self.session:
            return None

        # Try manager API first, then fallback to v1
        endpoints_to_try = [
            f"{API_DEVICES}{device_id}",  # /api/manager/devices/device/{id}
            f"{API_DEVICES_NO_SLASH}/{device_id}",  # /api/manager/devices/device/{id}
            f"{API_DEVICES_V1}/{device_id}",  # /api/v1/device/{id}
        ]

        last_connection_error: Exception | None = None
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        _LOGGER.debug("Device endpoint %s not found, trying next...", endpoint)
                        continue
                    else:
                        _LOGGER.debug("Failed to get device %s from %s: %s", device_id, endpoint, response.status)
                        continue
            except Exception as err:
                last_connection_error = err
                _LOGGER.debug("Error getting device %s from %s: %s", device_id, endpoint, err)
                continue

        err_detail = f": {last_connection_error}" if last_connection_error else ""
        _LOGGER.error(
            "Failed to get device %s from any endpoint (host=%s)%s",
            device_id,
            self.host,
            err_detail,
        )
        return None

    async def set_capability_value(
        self, device_id: str, capability_id: str, value: Any
    ) -> bool:
        """Set a capability value on a device."""
        if not self.session:
            return False

        # Validate and convert value to appropriate type
        # Handle cases where Home Assistant might pass strings instead of numbers
        converted_value = self._convert_capability_value(capability_id, value)
        
        if converted_value is None:
            _LOGGER.error(
                "Invalid value for capability %s on device %s: %s (type: %s)",
                capability_id,
                device_id,
                value,
                type(value).__name__,
            )
            return False

        # Try multiple endpoint patterns and HTTP methods
        # Use preferred_endpoint if available, otherwise try all
        if self.preferred_endpoint == "manager":
            base_endpoints = [
                (API_DEVICES, "manager"),
                (API_DEVICES_NO_SLASH, "manager"),
            ]
        elif self.preferred_endpoint == "v1":
            base_endpoints = [
                (API_DEVICES_V1, "v1"),
            ]
        else:
            base_endpoints = [
                (API_DEVICES, "manager"),
                (API_DEVICES_NO_SLASH, "manager"),
                (API_DEVICES_V1, "v1"),
            ]
        
        last_connection_error: Exception | None = None
        endpoints_to_try = []
        for base_endpoint, _ in base_endpoints:
            # Try different endpoint formats
            # Format 1: /api/manager/devices/device/{id}/capability/{cap}
            endpoints_to_try.append((f"{base_endpoint}{device_id}/capability/{capability_id}", "PUT"))
            # Format 2: /api/manager/devices/device/{id}/capability/{cap}/ (with trailing slash)
            endpoints_to_try.append((f"{base_endpoint}{device_id}/capability/{capability_id}/", "PUT"))
            # Format 3: /api/manager/devices/device/{id}/capability/{cap} (without trailing slash on base)
            if base_endpoint.endswith("/"):
                endpoints_to_try.append((f"{base_endpoint[:-1]}/{device_id}/capability/{capability_id}", "PUT"))
            # Try POST as well
            endpoints_to_try.append((f"{base_endpoint}{device_id}/capability/{capability_id}", "POST"))
            endpoints_to_try.append((f"{base_endpoint}{device_id}/capability/{capability_id}/", "POST"))
            if base_endpoint.endswith("/"):
                endpoints_to_try.append((f"{base_endpoint[:-1]}/{device_id}/capability/{capability_id}", "POST"))
        
        for endpoint, method in endpoints_to_try:
            try:
                if method == "PUT":
                    async with self.session.put(
                        f"{self.host}{endpoint}",
                        json={"value": converted_value},
                    ) as response:
                        if response.status == 200 or response.status == 204:
                            _LOGGER.debug("Successfully set capability %s=%s on device %s via %s", capability_id, converted_value, device_id, endpoint)
                            return True
                        elif response.status == 404:
                            _LOGGER.debug("Capability endpoint %s not found, trying next...", endpoint)
                            continue
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(
                                response.status, "devices", "write", f"set_capability({capability_id})"
                            )
                            continue
                        else:
                            error_text = await response.text()
                            _LOGGER.info(
                                "Failed to set capability %s=%s on device %s via %s (%s): %s - %s",
                                capability_id,
                                converted_value,
                                device_id,
                                endpoint,
                                method,
                                response.status,
                                error_text[:200] if error_text else "No error text",
                            )
                            continue
                else:  # POST
                    async with self.session.post(
                        f"{self.host}{endpoint}",
                        json={"value": converted_value},
                    ) as response:
                        if response.status == 200 or response.status == 204:
                            _LOGGER.debug("Successfully set capability %s=%s on device %s via %s", capability_id, converted_value, device_id, endpoint)
                            return True
                        elif response.status == 404:
                            _LOGGER.debug("Capability endpoint %s not found, trying next...", endpoint)
                            continue
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(
                                response.status, "devices", "write", f"set_capability({capability_id})"
                            )
                            continue
                        else:
                            error_text = await response.text()
                            _LOGGER.debug(
                                "Failed to set capability %s=%s on device %s via %s (%s): %s - %s",
                                capability_id,
                                converted_value,
                                device_id,
                                endpoint,
                                method,
                                response.status,
                                error_text[:200] if error_text else "No error text",
                            )
                            continue
            except Exception as err:
                last_connection_error = err
                _LOGGER.debug(
                    "Exception setting capability %s=%s on device %s via %s (%s): %s",
                    capability_id,
                    converted_value,
                    device_id,
                    endpoint,
                    method,
                    err,
                )
                continue

        err_detail = f": {last_connection_error}" if last_connection_error else ""
        _LOGGER.error(
            "Failed to set capability %s=%s on device %s from any endpoint (host=%s). Tried %d endpoints%s",
            capability_id,
            converted_value,
            device_id,
            self.host,
            len(endpoints_to_try),
            err_detail,
        )
        return False

    async def get_system_info(self) -> dict[str, Any] | None:
        """Fetch system info from Homey, if available."""
        if not self.session:
            return None

        endpoints_to_try = [
            f"{API_BASE_MANAGER}/system",
            f"{API_BASE_MANAGER}/system/",
            API_SYSTEM,
            f"{API_BASE_V1}/manager/system/info",
            f"{API_BASE_V1}/manager/system",
            f"{API_BASE_V1}/system/info",
            f"{API_BASE_V1}/system",
        ]

        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        return await response.json()
            except Exception:
                continue
        return None

    def _convert_capability_value(self, capability_id: str, value: Any) -> Any:
        """Convert value to appropriate type and format for the capability.
        
        Homey API uses normalized values (0-1) for many capabilities, while
        Home Assistant uses different ranges. This function handles the conversion.
        
        Format conversions:
        - light_hue: HA 0-360 → Homey 0-1 (handled in light.py before calling this)
        - light_saturation: HA 0-100 → Homey 0-1 (handled in light.py before calling this)
        - dim: HA 0-255 → Homey 0-1 (handled in light.py before calling this)
        - fan_speed: HA 0-100 → Homey 0-1 (handled in fan.py before calling this)
        - windowcoverings_state: HA 0-100 → Homey 0-1 (handled in cover.py before calling this)
        - volume_set: HA 0.0-1.0 → Homey 0-1 (no conversion needed, both normalized)
        - light_temperature: Both use Kelvin, no conversion needed
        - target_temperature: Both use Celsius, no conversion needed
        """
        # Handle None values
        if value is None:
            return None
        
        # Handle boolean capabilities
        if capability_id in ("onoff", "locked", "volume_mute", "button"):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                value_lower = value.lower().strip()
                if value_lower in ("true", "1", "on", "yes"):
                    return True
                if value_lower in ("false", "0", "off", "no"):
                    return False
            # Try to convert to bool
            try:
                return bool(int(value))
            except (ValueError, TypeError):
                _LOGGER.warning("Cannot convert %s to boolean for capability %s", value, capability_id)
                return None
        
        # Handle windowcoverings_state specially - can be enum ("up", "idle", "down") or numeric (0-1)
        if capability_id == "windowcoverings_state":
            # Check if it's an enum string value first
            if isinstance(value, str):
                value_stripped = value.strip().lower()
                # Valid enum values for windowcoverings_state
                if value_stripped in ("up", "idle", "down"):
                    return value_stripped  # Return the enum string as-is
            
            # If not an enum string, treat as numeric (for numeric windowcoverings_state devices)
            if isinstance(value, (int, float)):
                return float(value)
            
            if isinstance(value, str):
                value_stripped = value.strip()
                # Try to convert to float for numeric windowcoverings_state
                if value_stripped.replace(".", "").replace("-", "").isdigit():
                    try:
                        return float(value_stripped)
                    except (ValueError, TypeError):
                        pass
            
            # If we get here, it's neither a valid enum nor a valid number
            _LOGGER.warning(
                "Invalid value for capability %s: %s (must be 'up', 'idle', 'down', or a number)",
                capability_id,
                value[:50] if len(str(value)) > 50 else value,
            )
            return None
        
        # Handle numeric capabilities - reject non-numeric strings
        numeric_capabilities = [
            "dim", "light_hue", "light_saturation", "light_temperature",
            "target_temperature", "measure_temperature", "fan_speed",
            "volume_set",
        ]
        
        if capability_id in numeric_capabilities:
            # If it's already a number, return it
            # Note: Format conversions (e.g., 0-360 → 0-1) are handled in platform files
            # before calling this function, so we just need to ensure it's a float
            if isinstance(value, (int, float)):
                return float(value)
            
            # If it's a string, try to convert it
            if isinstance(value, str):
                value_stripped = value.strip()
                # Reject strings that look like errors (e.g., "idleidleidle...")
                if not value_stripped or not value_stripped.replace(".", "").replace("-", "").isdigit():
                    _LOGGER.warning(
                        "Invalid numeric value for capability %s: %s (appears to be a string, not a number)",
                        capability_id,
                        value[:50] if len(str(value)) > 50 else value,
                    )
                    return None
                try:
                    return float(value_stripped)
                except (ValueError, TypeError):
                    _LOGGER.warning("Cannot convert %s to float for capability %s", value, capability_id)
                    return None
            
            # For other types, try to convert
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning("Cannot convert %s to float for capability %s", value, capability_id)
                return None
        
        # For other capabilities, return as-is but log if it's an unexpected string
        if isinstance(value, str) and len(value) > 50:
            _LOGGER.debug("Long string value for capability %s: %s...", capability_id, value[:50])
        
        return value

    async def get_capability_value(
        self, device_id: str, capability_id: str
    ) -> Any | None:
        """Get a capability value from a device."""
        device = await self.get_device(device_id)
        if device:
            capabilities = device.get("capabilitiesObj", {})
            return capabilities.get(capability_id, {}).get("value")
        return None

    async def get_flows(self) -> dict[str, dict[str, Any]]:
        """Get all flows from Homey (both Standard and Advanced Flows)."""
        if not self.session:
            return {}

        self.flows = {}
        
        # First, get Standard Flows from /api/manager/flow/flow
        endpoints_to_try = [
            API_FLOWS,  # /api/manager/flow/flow (correct endpoint per API docs)
            f"{API_FLOWS}/",  # With trailing slash
            # Fallback variations (in case API structure varies)
            f"{API_BASE_MANAGER}/flows/flow",  # /api/manager/flows/flow (plural - old/incorrect)
            f"{API_BASE_MANAGER}/flows/flow/",  # With trailing slash
            f"{API_BASE_V1}/flow",  # /api/v1/flow
            f"{API_BASE_V1}/flow/",  # With trailing slash
        ]

        auth_error_count = 0
        standard_flows_found = False
        
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        flows_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(flows_data, dict):
                            standard_flows = flows_data
                        else:
                            # If it's an array, convert to dict keyed by id
                            standard_flows = {flow["id"]: flow for flow in flows_data}
                        
                        # Mark as standard flows and add to collection
                        for fid, flow in standard_flows.items():
                            flow["_flow_type"] = "standard"  # Mark as standard flow
                            self.flows[fid] = flow
                        
                        standard_flows_found = True
                        break
                    elif response.status == 401:
                        auth_error_count += 1
                        _LOGGER.warning("Authentication failed (401) for flows endpoint %s - check homey.flow.readonly permission", endpoint)
                        continue
                    elif response.status == 403:
                        auth_error_count += 1
                        _LOGGER.warning("Forbidden (403) for flows endpoint %s - check homey.flow.readonly permission", endpoint)
                        continue
                    elif response.status == 404:
                        continue
                    else:
                        continue
            except Exception as err:
                continue
        
        # Now get Advanced Flows from /api/manager/flow/advancedflow
        advanced_endpoints_to_try = [
            API_ADVANCED_FLOWS,  # /api/manager/flow/advancedflow
            f"{API_ADVANCED_FLOWS}/",  # With trailing slash
        ]
        
        advanced_flows_found = False
        for endpoint in advanced_endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        flows_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(flows_data, dict):
                            advanced_flows = flows_data
                        else:
                            # If it's an array, convert to dict keyed by id
                            advanced_flows = {flow["id"]: flow for flow in flows_data}
                        
                        # Mark as advanced flows and add to collection
                        for fid, flow in advanced_flows.items():
                            flow["_flow_type"] = "advanced"  # Mark as advanced flow
                            self.flows[fid] = flow
                        
                        advanced_flows_found = True
                        break
                    elif response.status == 401:
                        auth_error_count += 1
                        _LOGGER.warning("Authentication failed (401) for advanced flows endpoint %s - check flow:read permission", endpoint)
                        continue
                    elif response.status == 403:
                        auth_error_count += 1
                        _LOGGER.warning("Forbidden (403) for advanced flows endpoint %s - check flow:read permission", endpoint)
                        continue
                    elif response.status == 404:
                        continue
                    else:
                        continue
            except Exception as err:
                continue
        
        if self.flows:
            return self.flows
        
        # If all endpoints returned 401/403, it's a permission issue
        total_endpoints = len(endpoints_to_try) + len(advanced_endpoints_to_try)
        if auth_error_count > 0 and auth_error_count == total_endpoints:
            _LOGGER.error("All flows endpoints returned authentication errors (401/403). Please check that your API key has 'homey.flow.readonly' permission enabled in Homey Settings → API Keys.")
        elif auth_error_count > 0:
            _LOGGER.warning("Some flows endpoints returned authentication errors. Please check that your API key has 'homey.flow.readonly' permission enabled in Homey Settings → API Keys.")
        else:
            # No auth errors but no flows - user just doesn't have flows configured or feature not available
            _LOGGER.debug("No flows found - this is normal if you don't have any flows configured in Homey")
        return {}

    async def trigger_flow(self, flow_id: str) -> bool:
        """Trigger a flow by ID (supports both Standard and Advanced Flows)."""
        if not self.session:
            return False

        # Check if this is an Advanced Flow by looking it up in our flows cache
        flow_type = None
        if flow_id in self.flows:
            flow_type = self.flows[flow_id].get("_flow_type")
        
        # Build endpoints to try based on flow type
        endpoints_to_try = []
        
        if flow_type == "advanced":
            # Advanced Flows use: POST /api/manager/flow/advancedflow/:id/trigger
            endpoints_to_try = [
                (f"{API_ADVANCED_FLOWS}/{flow_id}/trigger", "POST"),  # /api/manager/flow/advancedflow/{id}/trigger
                (f"{API_ADVANCED_FLOWS}/{flow_id}/trigger/", "POST"),  # With trailing slash
            ]
        elif flow_type == "standard":
            # Standard Flows use: POST /api/manager/flow/flow/:id/trigger
            endpoints_to_try = [
                (f"{API_FLOWS}/{flow_id}/trigger", "POST"),  # /api/manager/flow/flow/{id}/trigger
                (f"{API_FLOWS}/{flow_id}/trigger/", "POST"),  # With trailing slash
            ]
        else:
            # Unknown type - try both endpoints
            endpoints_to_try = [
                (f"{API_FLOWS}/{flow_id}/trigger", "POST"),  # Standard flow endpoint
                (f"{API_FLOWS}/{flow_id}/trigger/", "POST"),  # With trailing slash
                (f"{API_ADVANCED_FLOWS}/{flow_id}/trigger", "POST"),  # Advanced flow endpoint
                (f"{API_ADVANCED_FLOWS}/{flow_id}/trigger/", "POST"),  # With trailing slash
                # Fallback variations
                (f"{API_BASE_MANAGER}/flows/flow/{flow_id}/trigger", "POST"),  # Old/incorrect
                (f"{API_FLOWS}/{flow_id}/run", "PUT"),  # Alternative trigger method
                (f"{API_FLOWS}/{flow_id}/run", "POST"),  # POST to /run
                (f"{API_BASE_V1}/flow/{flow_id}/trigger", "POST"),  # V1 endpoint
                (f"{API_BASE_V1}/flow/{flow_id}/run", "PUT"),  # V1 run endpoint
            ]

        last_connection_error: Exception | None = None
        for endpoint, method in endpoints_to_try:
            try:
                url = f"{self.host}{endpoint}"

                if method == "POST":
                    async with self.session.post(url) as response:
                        status = response.status
                        if status == 200 or status == 204:
                            return True
                        elif status == 404:
                            continue
                        else:
                            continue
                else:  # PUT
                    async with self.session.put(url) as response:
                        status = response.status
                        if status == 200 or status == 204:
                            return True
                        elif status == 404:
                            continue
                        else:
                            continue
            except Exception as err:
                last_connection_error = err
                continue

        err_detail = f": {last_connection_error}" if last_connection_error else ""
        _LOGGER.error(
            "Failed to trigger flow %s from any endpoint (host=%s)%s",
            flow_id,
            self.host,
            err_detail,
        )
        return False

    async def get_zones(self) -> dict[str, dict[str, Any]]:
        """Get all zones (rooms) from Homey."""
        if not self.session:
            return {}

        # Try manager API first, then fallback to v1
        endpoints_to_try = [
            API_ZONES,  # /api/manager/zones/zone
            f"{API_ZONES}/",  # With trailing slash
            f"{API_BASE_V1}/zone",  # /api/v1/zone
        ]

        auth_error_count = 0
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        zones_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(zones_data, dict):
                            self.zones = zones_data
                        elif isinstance(zones_data, list):
                            # If it's an array, convert to dict keyed by id
                            self.zones = {zone["id"]: zone for zone in zones_data}
                        else:
                            # Empty or unexpected response
                            self.zones = {}
                        
                        # If we got a successful response but no zones, that's OK - user just doesn't have zones
                        if not self.zones:
                            _LOGGER.debug("Zones endpoint returned empty result - no zones/rooms configured in Homey")
                        else:
                            _LOGGER.info("Successfully retrieved %d zones using endpoint: %s", len(self.zones), endpoint)
                        return self.zones
                    elif response.status == 404:
                        _LOGGER.debug("Zones endpoint %s not found, trying next...", endpoint)
                        continue
                    elif response.status in (401, 403):
                        auth_error_count += 1
                        PermissionChecker.check_permission(response.status, "zones", "read", "get_zones")
                        continue
                    else:
                        _LOGGER.debug("Failed to get zones from %s: %s", endpoint, response.status)
                        continue
            except Exception as err:
                _LOGGER.debug("Error getting zones from %s: %s", endpoint, err)
                continue

        # Only log permission warning if we got auth errors, not if endpoints just don't exist
        if auth_error_count > 0:
            _LOGGER.warning("Failed to get zones from any endpoint - permission issue")
            PermissionChecker.log_missing_permission(
                "zones",
                "read",
                "Devices will not be organized by Homey rooms/areas. They will appear without room grouping.",
            )
        else:
            _LOGGER.debug("Zones endpoint not available - zones may not be supported or configured on this Homey")
        return {}

    async def get_scenes(self) -> dict[str, dict[str, Any]]:
        """Get all scenes from Homey."""
        if not self.session:
            return {}

        endpoints_to_try = [
            API_SCENES,  # /api/manager/scene/scene
            f"{API_SCENES}/",  # With trailing slash
            f"{API_BASE_MANAGER}/scenes/scene",  # Plural variation
            f"{API_BASE_MANAGER}/scenes/scene/",  # With trailing slash
            f"{API_BASE_V1}/scene",  # V1 endpoint
            f"{API_BASE_V1}/scene/",  # With trailing slash
        ]

        auth_error_count = 0
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        scenes_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(scenes_data, dict):
                            self.scenes = scenes_data
                        elif isinstance(scenes_data, list):
                            # If it's an array, convert to dict keyed by id
                            self.scenes = {scene["id"]: scene for scene in scenes_data}
                        else:
                            # Empty or unexpected response - feature may not be available
                            self.scenes = {}
                        
                        # If we got a successful response but no scenes, that's OK - user just doesn't have scenes
                        if not self.scenes:
                            _LOGGER.debug("Scenes endpoint returned empty result - no scenes configured in Homey")
                        else:
                            _LOGGER.info("Successfully retrieved %d scenes using endpoint: %s", len(self.scenes), endpoint)
                        return self.scenes
                    elif response.status == 404:
                        _LOGGER.debug("Scenes endpoint %s not found, trying next...", endpoint)
                        continue
                    elif response.status in (401, 403):
                        auth_error_count += 1
                        PermissionChecker.check_permission(response.status, "scenes", "read", "get_scenes")
                        continue
                    else:
                        _LOGGER.debug("Failed to get scenes from %s: %s", endpoint, response.status)
                        continue
            except Exception as err:
                _LOGGER.debug("Error getting scenes from %s: %s", endpoint, err)
                continue

        # Only log permission warning if we got auth errors, not if endpoints just don't exist
        if auth_error_count > 0:
            _LOGGER.warning("Failed to get scenes from any endpoint - permission issue")
            PermissionChecker.log_missing_permission(
                "scenes",
                "read",
                "Scene entities will not be created. You won't be able to activate Homey scenes from Home Assistant.",
            )
        else:
            _LOGGER.debug("Scenes endpoint not available - scenes may not be supported or configured on this Homey")
        return {}

    async def trigger_scene(self, scene_id: str) -> bool:
        """Trigger a scene by ID."""
        if not self.session:
            return False

        endpoints_to_try = [
            f"{API_SCENES}/{scene_id}/trigger",  # /api/manager/scene/scene/{id}/trigger
            f"{API_SCENES}/{scene_id}/trigger/",  # With trailing slash
            f"{API_BASE_MANAGER}/scenes/scene/{scene_id}/trigger",  # Plural variation
            f"{API_BASE_V1}/scene/{scene_id}/trigger",  # V1 endpoint
            f"{API_SCENES}/{scene_id}/run",  # Alternative trigger method
            f"{API_SCENES}/{scene_id}/activate",  # Alternative activate method
        ]

        for endpoint in endpoints_to_try:
            try:
                async with self.session.post(f"{self.host}{endpoint}") as response:
                    if response.status == 200 or response.status == 204:
                        _LOGGER.debug("Successfully triggered scene %s via %s", scene_id, endpoint)
                        return True
                    elif response.status == 404:
                        continue
                    elif response.status in (401, 403):
                        PermissionChecker.check_permission(response.status, "scenes", "write", f"trigger_scene({scene_id})")
                        continue
                    else:
                        continue
            except Exception as err:
                _LOGGER.debug("Error triggering scene %s via %s: %s", scene_id, endpoint, err)
                continue

        _LOGGER.error("Failed to trigger scene %s from any endpoint", scene_id)
        return False

    async def get_moods(self) -> dict[str, dict[str, Any]]:
        """Get all moods from Homey."""
        if not self.session:
            return {}

        endpoints_to_try = [
            API_MOODS,  # /api/manager/moods/mood (correct per API v3)
            f"{API_MOODS}/",  # With trailing slash
            f"{API_BASE_MANAGER}/mood/mood",  # Singular variation (fallback)
            f"{API_BASE_MANAGER}/mood/mood/",  # With trailing slash
            f"{API_BASE_V1}/mood",  # V1 endpoint
            f"{API_BASE_V1}/mood/",  # With trailing slash
        ]

        auth_error_count = 0
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        moods_data = await response.json()
                        # Handle both array and object responses
                        if isinstance(moods_data, dict):
                            self.moods = moods_data
                        elif isinstance(moods_data, list):
                            # If it's an array, convert to dict keyed by id
                            self.moods = {mood["id"]: mood for mood in moods_data}
                        else:
                            # Empty or unexpected response - feature may not be available
                            self.moods = {}
                        
                        # If we got a successful response but no moods, that's OK - user just doesn't have moods
                        if not self.moods:
                            _LOGGER.debug("Moods endpoint returned empty result - no moods configured in Homey")
                        else:
                            _LOGGER.info("Successfully retrieved %d moods using endpoint: %s", len(self.moods), endpoint)
                        return self.moods
                    elif response.status == 404:
                        _LOGGER.debug("Moods endpoint %s not found, trying next...", endpoint)
                        continue
                    elif response.status in (401, 403):
                        auth_error_count += 1
                        PermissionChecker.check_permission(response.status, "moods", "read", "get_moods")
                        continue
                    else:
                        _LOGGER.debug("Failed to get moods from %s: %s", endpoint, response.status)
                        continue
            except Exception as err:
                _LOGGER.debug("Error getting moods from %s: %s", endpoint, err)
                continue

        # Only log permission warning if we got auth errors, not if endpoints just don't exist or feature isn't configured
        if auth_error_count > 0:
            _LOGGER.warning("Failed to get moods from any endpoint - permission issue")
            PermissionChecker.log_missing_permission(
                "moods",
                "read",
                "Mood entities will not be created. You won't be able to activate Homey moods from Home Assistant.",
            )
        else:
            _LOGGER.debug("Moods endpoint not available - moods may not be supported or configured on this Homey")
        return {}

    async def get_logic_variables(self) -> dict[str, dict[str, Any]]:
        """Get all logic variables from Homey."""
        if not self.session:
            return {}

        endpoints_to_try = [
            API_LOGIC_VARIABLES,  # /api/manager/logic/variable
            f"{API_LOGIC_VARIABLES}/",  # With trailing slash
        ]

        auth_error_count = 0
        for endpoint in endpoints_to_try:
            try:
                async with self.session.get(f"{self.host}{endpoint}") as response:
                    if response.status == 200:
                        variables_data = await response.json()
                        # Handle array, object, or nested responses
                        if isinstance(variables_data, list):
                            self.logic_variables = {
                                v["id"]: v for v in variables_data if v.get("id")
                            }
                        elif isinstance(variables_data, dict):
                            # Unwrap nested structures (e.g. {"result": {...}} or {"variables": [...]})
                            inner = variables_data.get("result") or variables_data.get("variables")
                            if inner is not None:
                                if isinstance(inner, list):
                                    self.logic_variables = {
                                        v.get("id", str(i)): v for i, v in enumerate(inner)
                                    }
                                elif isinstance(inner, dict):
                                    self.logic_variables = inner
                                else:
                                    self.logic_variables = {}
                            else:
                                self.logic_variables = variables_data
                        else:
                            self.logic_variables = {}

                        if not self.logic_variables:
                            _LOGGER.debug("Logic variables endpoint returned empty result")
                        else:
                            _LOGGER.debug(
                                "Successfully retrieved %d logic variables using endpoint: %s",
                                len(self.logic_variables),
                                endpoint,
                            )
                        return self.logic_variables
                    elif response.status == 404:
                        _LOGGER.debug(
                            "Logic variables endpoint %s not found, trying next...",
                            endpoint,
                        )
                        continue
                    elif response.status in (401, 403):
                        auth_error_count += 1
                        PermissionChecker.check_permission(
                            response.status, "logic", "read", "get_logic_variables"
                        )
                        continue
                    else:
                        _LOGGER.debug(
                            "Failed to get logic variables from %s: %s",
                            endpoint,
                            response.status,
                        )
                        continue
            except Exception as err:
                _LOGGER.debug("Error getting logic variables from %s: %s", endpoint, err)
                continue

        if auth_error_count > 0:
            _LOGGER.warning("Failed to get logic variables from any endpoint - permission issue")
            PermissionChecker.log_missing_permission(
                "logic",
                "read",
                "Logic variable entities will not be created. Enable homey.logic.readonly to import them.",
            )
        else:
            _LOGGER.debug("Logic variables endpoint not available on this Homey")
        return {}

    async def update_logic_variable(self, variable_id: str, value: Any) -> bool:
        """Update a Homey logic variable value."""
        if not self.session:
            return False

        endpoints_to_try = [
            f"{API_LOGIC_VARIABLES}/{variable_id}",
            f"{API_LOGIC_VARIABLES}/{variable_id}/",
        ]
        # Try both payload formats - Homey API structure may vary
        payloads_to_try: list[dict[str, Any]] = [
            {"value": value},
            {"variable": {"value": value}},
        ]

        last_error: str | None = None
        for payload in payloads_to_try:
            for endpoint in endpoints_to_try:
                try:
                    async with self.session.put(
                        f"{self.host}{endpoint}",
                        json=payload,
                    ) as response:
                        if response.status in (200, 204):
                            _LOGGER.debug(
                                "Successfully updated logic variable %s via %s",
                                variable_id,
                                endpoint,
                            )
                            return True
                        elif response.status == 404:
                            continue
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(
                                response.status, "logic", "write", f"update_logic_variable({variable_id})"
                            )
                            last_error = f"{response.status} {response.reason}"
                            continue
                        else:
                            error_text = await response.text()
                            last_error = f"{response.status}: {error_text[:150] if error_text else 'No body'}"
                            _LOGGER.debug(
                                "Failed to update logic variable %s via %s (%s)",
                                variable_id,
                                endpoint,
                                last_error,
                            )
                            continue
                except Exception as err:
                    last_error = str(err)
                    _LOGGER.debug(
                        "Error updating logic variable %s via %s: %s",
                        variable_id,
                        endpoint,
                        err,
                    )
                    continue

        _LOGGER.error(
            "Failed to update logic variable %s from any endpoint (host=%s)%s. "
            "Ensure API key has homey.logic (Variables) permission.",
            variable_id,
            self.host,
            f": {last_error}" if last_error else "",
        )
        return False

    async def trigger_mood(self, mood_id: str) -> bool:
        """Trigger a mood by ID."""
        if not self.session:
            return False

        endpoints_to_try = [
            f"{API_MOODS}/{mood_id}/set",  # /api/manager/moods/mood/{id}/set (correct per API v3)
            f"{API_MOODS}/{mood_id}/set/",  # With trailing slash
            f"{API_BASE_MANAGER}/mood/mood/{mood_id}/set",  # Singular variation (fallback)
            f"{API_BASE_MANAGER}/mood/mood/{mood_id}/set/",  # With trailing slash
            f"{API_MOODS}/{mood_id}/trigger",  # Alternative trigger method
            f"{API_MOODS}/{mood_id}/trigger/",  # With trailing slash
            f"{API_BASE_V1}/mood/{mood_id}/set",  # V1 endpoint with /set
            f"{API_BASE_V1}/mood/{mood_id}/trigger",  # V1 endpoint
            f"{API_MOODS}/{mood_id}/run",  # Alternative trigger method
            f"{API_MOODS}/{mood_id}/activate",  # Alternative activate method
        ]

        for endpoint in endpoints_to_try:
            try:
                async with self.session.post(f"{self.host}{endpoint}") as response:
                    if response.status == 200 or response.status == 204:
                        _LOGGER.debug("Successfully triggered mood %s via %s", mood_id, endpoint)
                        return True
                    elif response.status == 404:
                        _LOGGER.debug("Mood trigger endpoint %s not found (404), trying next...", endpoint)
                        continue
                    elif response.status in (401, 403):
                        _LOGGER.debug("Mood trigger endpoint %s returned %s (permission denied)", endpoint, response.status)
                        PermissionChecker.check_permission(response.status, "moods", "write", f"trigger_mood({mood_id})")
                        continue
                    else:
                        # Log other status codes to help debug
                        try:
                            error_text = await response.text()
                            _LOGGER.debug("Mood trigger endpoint %s returned status %s: %s", endpoint, response.status, error_text[:200])
                        except:
                            _LOGGER.debug("Mood trigger endpoint %s returned status %s", endpoint, response.status)
                        continue
            except Exception as err:
                _LOGGER.debug("Error triggering mood %s via %s: %s", mood_id, endpoint, err)
                continue

        _LOGGER.error("Failed to trigger mood %s from any endpoint", mood_id)
        return False

    async def enable_flow(self, flow_id: str) -> bool:
        """Enable a flow by ID."""
        if not self.session:
            return False

        # Try to enable flow via PUT/PATCH to flow endpoint
        endpoints_to_try = [
            (f"{API_FLOWS}/{flow_id}", "PATCH"),  # Standard flow
            (f"{API_FLOWS}/{flow_id}/", "PATCH"),  # With trailing slash
            (f"{API_ADVANCED_FLOWS}/{flow_id}", "PATCH"),  # Advanced flow
            (f"{API_ADVANCED_FLOWS}/{flow_id}/", "PATCH"),  # With trailing slash
            (f"{API_FLOWS}/{flow_id}", "PUT"),  # PUT method
            (f"{API_ADVANCED_FLOWS}/{flow_id}", "PUT"),  # PUT method
        ]

        for endpoint, method in endpoints_to_try:
            try:
                url = f"{self.host}{endpoint}"
                data = {"enabled": True}
                
                if method == "PATCH":
                    async with self.session.patch(url, json=data) as response:
                        if response.status in (200, 204):
                            _LOGGER.debug("Successfully enabled flow %s", flow_id)
                            return True
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(response.status, "flows", "write", f"enable_flow({flow_id})")
                            continue
                else:  # PUT
                    async with self.session.put(url, json=data) as response:
                        if response.status in (200, 204):
                            _LOGGER.debug("Successfully enabled flow %s", flow_id)
                            return True
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(response.status, "flows", "write", f"enable_flow({flow_id})")
                            continue
            except Exception as err:
                _LOGGER.debug("Error enabling flow %s via %s: %s", flow_id, endpoint, err)
                continue

        _LOGGER.error("Failed to enable flow %s", flow_id)
        return False

    async def disable_flow(self, flow_id: str) -> bool:
        """Disable a flow by ID."""
        if not self.session:
            return False

        # Try to disable flow via PUT/PATCH to flow endpoint
        endpoints_to_try = [
            (f"{API_FLOWS}/{flow_id}", "PATCH"),  # Standard flow
            (f"{API_FLOWS}/{flow_id}/", "PATCH"),  # With trailing slash
            (f"{API_ADVANCED_FLOWS}/{flow_id}", "PATCH"),  # Advanced flow
            (f"{API_ADVANCED_FLOWS}/{flow_id}/", "PATCH"),  # With trailing slash
            (f"{API_FLOWS}/{flow_id}", "PUT"),  # PUT method
            (f"{API_ADVANCED_FLOWS}/{flow_id}", "PUT"),  # PUT method
        ]

        for endpoint, method in endpoints_to_try:
            try:
                url = f"{self.host}{endpoint}"
                data = {"enabled": False}
                
                if method == "PATCH":
                    async with self.session.patch(url, json=data) as response:
                        if response.status in (200, 204):
                            _LOGGER.debug("Successfully disabled flow %s", flow_id)
                            return True
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(response.status, "flows", "write", f"disable_flow({flow_id})")
                            continue
                else:  # PUT
                    async with self.session.put(url, json=data) as response:
                        if response.status in (200, 204):
                            _LOGGER.debug("Successfully disabled flow %s", flow_id)
                            return True
                        elif response.status in (401, 403):
                            PermissionChecker.check_permission(response.status, "flows", "write", f"disable_flow({flow_id})")
                            continue
            except Exception as err:
                _LOGGER.debug("Error disabling flow %s via %s: %s", flow_id, endpoint, err)
                continue

        _LOGGER.error("Failed to disable flow %s", flow_id)
        return False

    def _handle_socketio_event(self, event_name: str, *args: Any) -> None:
        """Route Socket.IO events by event name.
        
        Args:
            event_name: Event name (e.g., "homey:manager:devices", "homey:device:<id>")
            *args: Event arguments - Homey sends (event_type, data) for manager events
        """
        _LOGGER.debug("📥 HOMEY EVENT uri=%s args_count=%d", event_name, len(args))
        
        # Route by event name
        if event_name == "homey:manager:devices":
            # Manager-level event - Homey sends (event_type, data) where event_type is like "device.update"
            if args and len(args) >= 2:
                event_type = args[0] if isinstance(args[0], str) else None
                data = args[1] if isinstance(args[1], dict) else (args[0] if isinstance(args[0], dict) else {})
                _LOGGER.debug("📥 HOMEY EVENT uri=homey:manager:devices event=%s data=%s", event_type, str(data)[:500])
                if event_type:
                    self._on_sio_manager_event(event_type, data)
                else:
                    # Fallback: treat as manager event
                    self._on_sio_manager_event("manager", data)
            elif args and len(args) == 1:
                # Single arg - might be data only
                data = args[0] if isinstance(args[0], dict) else {}
                _LOGGER.debug("📥 HOMEY EVENT uri=homey:manager:devices (single arg) data=%s", str(data)[:500])
                self._on_sio_manager_event("manager", data)
        elif event_name.startswith("homey:device:"):
            # Device-specific URI event - extract device ID from URI
            # Homey sends (event_type, data) for device events too
            device_id = event_name.replace("homey:device:", "")
            if args and len(args) >= 2:
                event_type = args[0] if isinstance(args[0], str) else None
                data = args[1] if isinstance(args[1], dict) else (args[0] if isinstance(args[0], dict) else {})
                _LOGGER.debug("📥 HOMEY EVENT uri=%s device_id=%s event=%s data=%s", event_name, device_id, event_type, str(data)[:500])
                self._on_device_update(device_id, data)
            elif args and len(args) == 1:
                data = args[0] if isinstance(args[0], dict) else {}
                _LOGGER.debug("📥 HOMEY EVENT uri=%s device_id=%s (single arg) data=%s", event_name, device_id, str(data)[:500])
                self._on_device_update(device_id, data)
        elif event_name == "homey:manager:capability":
            # Capability event - Homey sends (event_type, data)
            if args and len(args) >= 2:
                event_type = args[0] if isinstance(args[0], str) else None
                data = args[1] if isinstance(args[1], dict) else (args[0] if isinstance(args[0], dict) else {})
                _LOGGER.debug("📥 HOMEY EVENT uri=homey:manager:capability event=%s data=%s", event_type, str(data)[:500])
                device_id = data.get("deviceId") or data.get("device", {}).get("id")
                if device_id:
                    self._on_device_update(device_id, data)
            elif args and len(args) == 1:
                data = args[0] if isinstance(args[0], dict) else {}
                _LOGGER.debug("📥 HOMEY EVENT uri=homey:manager:capability (single arg) data=%s", str(data)[:500])
                device_id = data.get("deviceId") or data.get("device", {}).get("id")
                if device_id:
                    self._on_device_update(device_id, data)
        else:
            # Unknown event - log and try to process as device event
            _LOGGER.debug("📥 HOMEY EVENT (unknown) uri=%s payload=%s", event_name, str(args)[:500])
            if args:
                self._on_sio_device_event(*args)
    
    def _on_device_update(self, device_id: str, data: dict[str, Any]) -> None:
        """Handle device update from Socket.IO or polling.
        
        Args:
            device_id: Device ID
            data: Device data dictionary (may be partial update like capability change)
        """
        if device_id:
            # Update local device cache - merge with existing data
            if device_id in self.devices:
                # Merge capability updates into existing capabilitiesObj
                if "capabilitiesObj" in data:
                    existing_caps = self.devices[device_id].get("capabilitiesObj", {})
                    # Deep merge: update existing capability values
                    for cap_id, cap_data in data["capabilitiesObj"].items():
                        if cap_id in existing_caps:
                            existing_caps[cap_id].update(cap_data)
                        else:
                            existing_caps[cap_id] = cap_data
                    # Ensure the merged capabilitiesObj is in the update
                    data["capabilitiesObj"] = existing_caps
                # Merge the update into existing device data
                self.devices[device_id].update(data)
            else:
                self.devices[device_id] = data
            # Notify listeners (this triggers coordinator updates)
            for listener in self._listeners:
                try:
                    if callable(listener):
                        listener(device_id, data)
                except Exception as err:
                    _LOGGER.error("Error in device update listener: %s", err)

    async def _connect_socketio(self) -> bool:
        """Connect to Homey Socket.IO server for real-time updates.
        
        Uses ONE AsyncClient and reuses the same Engine.IO connection for both root and /api namespace.
        This matches the working HTML test pattern (JS reuses the same WebSocket connection).
        
        Flow:
        1. Connect to root namespace /
        2. Call handshakeClient to get namespace token
        3. Manually send Socket.IO namespace connect packet to /api on SAME connection
        4. Subscribe to events on /api namespace
        
        Returns True if Socket.IO connection is established, False otherwise.
        Falls back to polling if Socket.IO fails.
        """
        if self._sio_connected and self.sio:
            _LOGGER.debug("Socket.IO already connected - skipping connection attempt")
            return True

        is_reconnect = not self._sio_connected and self._sio_reconnect_task is not None
        log = _LOGGER.debug if is_reconnect else _LOGGER.info
        log("=" * 60)
        log("Socket.IO Connection Test - %s", "Reconnecting..." if is_reconnect else "Starting")
        log("=" * 60)
        
        try:
            # Determine Socket.IO base URL (strip any path like /api from host)
            # Host MUST have scheme (http/https) - yarl treats bare IP/hostname as path, giving empty host -> ws:///
            from yarl import URL
            
            host_str = self.host.rstrip("/")
            if not host_str or host_str == "unknown":
                _LOGGER.error("Socket.IO: Host is empty or invalid, skipping connection")
                return False
            if not host_str.startswith(("http://", "https://")):
                host_str = f"http://{host_str}"
            raw_url = URL(host_str)
            base_url = str(raw_url.with_path("").with_query(None))
            
            _LOGGER.debug("  → Original host: %s", self.host)
            _LOGGER.debug("  → Base URL (no path): %s", base_url)
            
            # Detect SSL for Socket.IO
            use_https = base_url.startswith("https://")
            
            # Create aiohttp connector with SSL configuration
            if use_https:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)
            else:
                connector = aiohttp.TCPConnector(ssl=False)
            
            # Create aiohttp session with the connector (must be closed in _disconnect_socketio)
            self._sio_http_session = aiohttp.ClientSession(connector=connector)
            
            # Disable verbose logging from socketio library
            import logging
            sio_logger = logging.getLogger("socketio")
            sio_logger.setLevel(logging.WARNING)
            engineio_logger = logging.getLogger("engineio")
            engineio_logger.setLevel(logging.WARNING)
            
            # Set flag to prevent reconnect during connection setup
            self._sio_connecting = True
            
            # Step 1: Create single client and connect ONLY to root namespace
            _LOGGER.debug("Step 1/5: Creating Socket.IO client and connecting to root namespace")
            self.sio = socketio.AsyncClient(
                http_session=self._sio_http_session,
                logger=False,
                engineio_logger=False,
            )
            
            # Set up namespace-specific event handlers for root namespace
            def on_root_connect():
                _LOGGER.debug("✅ Root namespace / connected")
            
            def on_root_disconnect():
                _LOGGER.debug("⚠️ Root namespace / disconnected")
            
            def on_root_connect_error(data):
                now = time.time()
                if now - self._last_sio_error_log >= self._ERROR_LOG_INTERVAL:
                    self._last_sio_error_log = now
                    _LOGGER.error("❌ Root namespace / connect_error: %s", data)
                else:
                    _LOGGER.debug("Root namespace connect_error (rate limited): %s", data)

            self.sio.on("connect", on_root_connect, namespace="/")
            self.sio.on("disconnect", on_root_disconnect, namespace="/")
            self.sio.on("connect_error", on_root_connect_error, namespace="/")
            
            _LOGGER.debug("  → Connecting to %s (root namespace ONLY)", base_url)
            await self.sio.connect(
                base_url,  # e.g. http://homey.local or http://192.168.1.100 (no path)
                transports=["websocket"],
                wait_timeout=10,
                namespaces=["/"],  # CRITICAL: Only root namespace
            )
            
            await asyncio.sleep(0.5)  # Brief pause for connection to establish
            
            if not self.sio.connected:
                _LOGGER.error("Step 1/5: FAILED - Root namespace connection failed")
                _LOGGER.info("=" * 60)
                _LOGGER.info("Socket.IO Connection Test - FAILED")
                _LOGGER.info("Will use polling (1 second interval) for updates")
                _LOGGER.info("=" * 60)
                self._sio_connecting = False  # Clear flag before disconnect
                await self._disconnect_socketio()
                return False
            
            _LOGGER.debug("Step 1/5: SUCCESS - Root namespace connected")
            
            # Step 2: Authenticate with handshakeClient on root namespace
            _LOGGER.debug("Step 2/5: Authenticating Socket.IO connection (handshakeClient)")
            auth_success = await self._authenticate_socketio()
            if not auth_success:
                _LOGGER.warning("Step 2/5: WARNING - Socket.IO authentication failed")
                _LOGGER.warning("Continuing anyway - some Homey versions might not require authentication")
                self.sio_namespace = None
                self.sio_token = None
                self._sio_connecting = False  # Clear flag before disconnect
                await self._disconnect_socketio()
                return False
            
            if not self.sio_namespace or not self.sio_token:
                _LOGGER.error("Step 2/5: FAILED - No namespace/token received from handshakeClient")
                self._sio_connecting = False  # Clear flag before disconnect
                await self._disconnect_socketio()
                return False
            
            _LOGGER.debug("Step 2/5: SUCCESS - Socket.IO authentication successful")
            _LOGGER.debug("  → Received namespace: %s", self.sio_namespace)
            _LOGGER.debug("  → Received namespace token: %s...", self.sio_token[:20])
            
            # Step 3: Manually connect to /api namespace on the SAME Engine.IO connection
            # The namespace token is session-bound, so we must use the same Engine.IO session
            _LOGGER.debug("Step 3/5: Connecting to %s namespace on SAME Engine.IO connection", self.sio_namespace)
            _LOGGER.debug("  → Namespace token is session-bound - must use same Engine.IO connection")
            _LOGGER.debug("  → Trying both payload formats: {'token': ...} and {'auth': {'token': ...}}")
            
            # Initialize event and error storage for /api namespace connection
            self._api_connected_evt = asyncio.Event()
            self._api_connect_error = None
            
            # Helper function to connect /api namespace using proper Packet class
            async def _connect_namespace_api(token: str) -> bool:
                """Connect to /api namespace using python-socketio's Packet class."""
                from socketio.packet import Packet
                
                self._api_connected_evt = asyncio.Event()
                self._api_connect_error = None

                if self.sio is None:
                    _LOGGER.error("Socket.IO client not initialized; cannot connect /api namespace")
                    return False
                sio = self.sio
                
                # Set up namespace-specific event handlers for /api namespace
                def on_api_connect():
                    _LOGGER.info("✅ Namespace %s connected", self.sio_namespace)
                    if self._api_connected_evt:
                        self._api_connected_evt.set()
                
                def on_api_connect_error(data):
                    _LOGGER.error("❌ Namespace %s connect_error: %s", self.sio_namespace, data)
                    self._api_connect_error = data
                    if self._api_connected_evt:
                        self._api_connected_evt.set()  # Unblock waiter even on error
                
                sio.on("connect", on_api_connect, namespace=self.sio_namespace)
                sio.on("connect_error", on_api_connect_error, namespace=self.sio_namespace)
                
                # Helper to send packet with fallback for different python-socketio versions
                async def _send_packet(pkt: Packet):
                    """Send packet using available internal API with fallback."""
                    if hasattr(sio, "_send_packet"):
                        await sio._send_packet(pkt)
                    elif hasattr(sio, "_send_packet_internal"):
                        await sio._send_packet_internal(pkt)
                    else:
                        # Last resort: encode then send via engineio
                        encoded = pkt.encode()
                        await sio.eio.send(encoded)
                
                # Try both payload shapes, but send them as proper Packets
                # Socket.IO packet types: 0=CONNECT, 1=DISCONNECT, 2=EVENT, 3=ACK, 4=CONNECT_ERROR
                payloads: list[dict[str, Any]] = [
                    {"token": token},
                    {"auth": {"token": token}},
                ]
                for idx, payload_data in enumerate(payloads, start=1):
                    _LOGGER.debug(
                        "  → Attempt %d: CONNECT /api with payload keys: %s",
                        idx,
                        list(payload_data.keys()),
                    )
                    
                    # Create proper Socket.IO CONNECT packet (type 0 = CONNECT)
                    pkt = Packet(packet_type=0, namespace=self.sio_namespace, data=payload_data)
                    
                    # Encode packet and log length for debugging
                    encoded = pkt.encode()
                    _LOGGER.debug("  → Encoded CONNECT packet length: %d bytes", len(encoded))
                    
                    # Send packet using proper encoding
                    await _send_packet(pkt)
                    
                    try:
                        await asyncio.wait_for(self._api_connected_evt.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        pass
                    
                    # Check if namespace is actually connected (connect_error may not fire if server ignores)
                    connected_namespaces = set(getattr(sio, "namespaces", {}).keys())
                    if self.sio_namespace in connected_namespaces:
                        _LOGGER.debug("  → Attempt %d SUCCESS - Namespace %s connected", idx, self.sio_namespace)
                        return True
                    
                    # Reset for next attempt
                    self._api_connected_evt.clear()
                    if idx < 2:  # Log failure only if we have more attempts
                        _LOGGER.debug("  → Attempt %d failed, trying next format...", idx)
                
                _LOGGER.error(
                    "FAILED to connect /api. connected namespaces=%s, last_error=%s",
                    set(getattr(sio, "namespaces", {}).keys()),
                    self._api_connect_error,
                )
                return False
            
            try:
                # Connect /api namespace using proper Packet class
                success = await _connect_namespace_api(self.sio_token)
                
                if not success:
                    _LOGGER.error("Step 3/5: FAILED - Could not connect /api namespace on same Engine.IO session")
                    connected_namespaces = set(getattr(self.sio, "namespaces", {}).keys())
                    _LOGGER.error("  → Connected namespaces: %s", connected_namespaces)
                    _LOGGER.error("  → Expected namespace: %s", self.sio_namespace)
                    _LOGGER.error("  → Last connect_error: %s", self._api_connect_error)
                    # Don't disconnect root - keep it alive for retry
                    self._sio_connecting = False  # Clear flag even on failure
                    return False
                
                _LOGGER.debug("Step 3/5: SUCCESS - Namespace %s connected", self.sio_namespace)
                connected_namespaces = set(getattr(self.sio, "namespaces", {}).keys())
                _LOGGER.debug("  → Connected namespaces: %s", connected_namespaces)
                
                # Register catch-all handler now that /api namespace is connected
                # IMPORTANT: Preserve event_name - don't drop it!
                def catch_all_event(event_name, *args):
                    """Catch-all handler to see all Socket.IO events."""
                    is_system_event = event_name in ("connect", "disconnect", "connect_error", "error")
                    
                    if not is_system_event:
                        _LOGGER.debug("Socket.IO catch-all event received on /api: %s", event_name)
                        # Route event by event_name - don't drop it!
                        self._handle_socketio_event(event_name, *args)
                
                self.sio.on("*", catch_all_event, namespace=self.sio_namespace)
                
            except Exception as namespace_err:
                _LOGGER.error("Step 3/5: FAILED - Error connecting to namespace %s: %s", self.sio_namespace, namespace_err, exc_info=True)
                # Don't disconnect root - keep it alive for retry
                self._sio_connecting = False  # Clear flag even on exception
                return False
            
            # Step 4: Subscribe to device events on /api namespace (using same client)
            _LOGGER.debug("Step 4/5: Subscribing to device events")
            subscribe_success = await self._subscribe_device_events()
            if not subscribe_success:
                _LOGGER.error("Step 4/5: FAILED - Socket.IO device subscription failed")
                _LOGGER.info("Socket.IO connection failed - will use polling for updates")
                # Don't disconnect root - keep it alive for retry
                return False
            
            _LOGGER.debug("Step 4/5: SUCCESS - Subscribed to device events")
            
            # Final status check
            _LOGGER.debug("Step 5/5: Verifying Socket.IO connection status")
            if self.sio and self.sio.connected:
                # Check if /api namespace is connected
                connected_namespaces = set(getattr(self.sio, "namespaces", {}).keys())
                if self.sio_namespace in connected_namespaces:
                    self._sio_connected = True
                    self._last_sio_error_log = 0  # Reset so next failure is logged
                    _LOGGER.info("Socket.IO real-time updates enabled")
                    _LOGGER.debug("  → Root namespace: /")
                    _LOGGER.debug("  → API namespace: %s", self.sio_namespace)
                    _LOGGER.debug("  → Connected namespaces: %s", connected_namespaces)
                    _LOGGER.info("Real-time events will be received via Socket.IO")
                    _LOGGER.info("=" * 60)
                    # Stop any reconnection task since we're connected
                    self._stop_sio_reconnect_task()
                    self._sio_connecting = False  # Clear flag now that we're fully connected
                    return True
                else:
                    _LOGGER.error("Step 5/5: FAILED - /api namespace not connected")
                    _LOGGER.error("  → Connected namespaces: %s", connected_namespaces)
                    _LOGGER.error("  → Expected namespace: %s", self.sio_namespace)
                    # Don't disconnect root - keep it alive for retry
                    self._sio_connecting = False  # Clear flag even on failure
                    return False
            else:
                _LOGGER.error("Step 5/5: FAILED - Socket.IO connection lost during setup")
                _LOGGER.info("=" * 60)
                _LOGGER.info("Socket.IO Connection Test - FAILED")
                _LOGGER.info("Will use polling (1 second interval) for updates")
                _LOGGER.info("=" * 60)
                self._sio_connecting = False  # Clear flag before disconnect
                await self._disconnect_socketio()
                return False
            
        except Exception as err:
            now = time.time()
            if now - self._last_sio_error_log >= self._ERROR_LOG_INTERVAL:
                self._last_sio_error_log = now
                _LOGGER.error("Socket.IO connection error: %s", err, exc_info=True)
                _LOGGER.info("=" * 60)
                _LOGGER.info("Socket.IO Connection Test - FAILED")
                _LOGGER.info("Will use polling (1 second interval) for updates")
                _LOGGER.info("=" * 60)
            else:
                _LOGGER.debug("Socket.IO connection error (rate limited): %s", err)
            self._sio_connecting = False  # Clear flag before disconnect
            await self._disconnect_socketio()
            return False
    
    async def _authenticate_socketio(self) -> bool:
        """Authenticate Socket.IO connection with handshakeClient event.
        
        Returns True if authentication successful, False otherwise.
        """
        if not self.sio or not self.sio.connected:
            return False
        
        if not self.token:
            _LOGGER.error("Cannot authenticate Socket.IO: missing token")
            return False
        
        try:
            # Emit handshakeClient event with token and homeyId
            # According to Homey API docs, BOTH token and homeyId are REQUIRED
            # Prepare handshake data
            if not self.homey_id:
                _LOGGER.warning("homeyId not available - attempting to retrieve from system info")
                # Try to get homeyId from system info if not available
                try:
                    system_info = await self.get_system_info()
                    if system_info:
                        self.homey_id = (
                            system_info.get("cloudId") or 
                            system_info.get("id") or 
                            system_info.get("homeyId")
                        )
                except Exception:
                    pass
            
            # Try authentication with homeyId if available, otherwise try without it
            # Some Homey versions/configurations might allow authentication without homeyId
            if self.homey_id:
                handshake_data = {"token": self.token, "homeyId": self.homey_id}
                _LOGGER.debug("Authenticating Socket.IO with token and homeyId")
            else:
                _LOGGER.warning("homeyId not available - attempting Socket.IO authentication without it")
                _LOGGER.warning("If this fails, add 'homey.system.readonly' permission to your API key")
                handshake_data = {"token": self.token}
            
            # Use call() for request-response pattern (most reliable)
            # CRITICAL: Call handshakeClient on the root namespace (/) explicitly
            # Homey uses error-first callback pattern: (error, result)
            # python-socketio's call() may return this as a tuple or just the result
            try:
                _LOGGER.debug("Sending handshakeClient with data: %s", {k: v if k != "token" else "***" for k, v in handshake_data.items()})
                # Authenticate on root namespace (/) - this is where handshakeClient MUST be called
                auth_response = await self.sio.call(
                    "handshakeClient",
                    handshake_data,
                    timeout=10,
                    namespace="/"  # Explicitly use root namespace "/" (not None)
                )
                # Log the EXACT response format for debugging (debug level only)
                _LOGGER.debug("handshakeClient response: type=%s", type(auth_response).__name__)
            except Exception as call_err:
                _LOGGER.error("Socket.IO authentication failed: %s", call_err, exc_info=True)
                if "homeyId" not in handshake_data:
                    _LOGGER.error("  → Missing homeyId - add 'homey.system.readonly' permission to your API key")
                return False
            
            # Parse handshake response
            # Homey returns: (null, {token: '...', namespace: '/api', success: true})
            # python-socketio's call() may return:
            #   - Just the result dict: {token: '...', namespace: '/api', success: true}
            #   - Or a tuple: (error, result) where error is None and result is the dict
            self.sio_namespace = None
            self.sio_token = None
            
            if auth_response:
                # Handle (error, result) tuple format from error-first callback
                if isinstance(auth_response, (list, tuple)) and len(auth_response) == 2:
                    err, res = auth_response
                    if err:
                        _LOGGER.error("handshakeClient error: %s", err)
                        return False
                    # Extract from result
                    auth_response = res  # Use result for further processing
                
                # Now process the actual result (could be string, dict, etc.)
                if isinstance(auth_response, dict):
                    # Most common format: {token: '...', namespace: '/api', success: true}
                    self.sio_namespace = auth_response.get("namespace")
                    self.sio_token = auth_response.get("token")
                    success = auth_response.get("success", False)
                    if not success:
                        _LOGGER.error("handshakeClient returned success: false")
                        return False
                elif isinstance(auth_response, str):
                    # Direct namespace string response
                    self.sio_namespace = auth_response
                else:
                    _LOGGER.error("Unexpected handshake response format: %s (type: %s)", auth_response, type(auth_response))
                    return False
                
                # Validate namespace was extracted
                if not self.sio_namespace:
                    _LOGGER.error("No namespace in handshake response: %s", auth_response)
                    return False
                
                _LOGGER.info("Authentication successful - received namespace: %s", self.sio_namespace)
                if self.sio_token:
                    _LOGGER.debug("Received Socket.IO token from handshake")
                return True
            else:
                # Empty response (null/None) - authentication failed
                _LOGGER.error("handshakeClient returned empty response")
                return False
                
        except Exception as err:
            _LOGGER.error("Socket.IO authentication error: %s", err, exc_info=True)
            return False
    
    async def _subscribe_device_events(self) -> bool:
        """Subscribe to device update events via Socket.IO.
        
        According to Homey API docs, we need to subscribe to individual device URIs:
        - For a specific device: homey:device:{deviceId}
        - For manager-level events: homey:manager:devices
        
        After subscribing, events will arrive with the event name matching the URI.
        
        Returns True if subscription successful, False otherwise.
        """
        # Use the same client with namespace="/api" for subscriptions
        if not self.sio or not self.sio.connected:
            return False
        
        try:
            # CRITICAL: Use the namespace from handshakeClient - subscriptions MUST be on that namespace
            # If no namespace was returned, we can't subscribe (Homey requires namespace for broadcasts)
            if not self.sio_namespace:
                _LOGGER.error("  → Cannot subscribe: no namespace from handshakeClient")
                _LOGGER.error("  → Homey requires namespace for broadcasts - subscriptions will fail")
                return False
            
            subscription_namespace = self.sio_namespace
            _LOGGER.debug("  → Using namespace for subscriptions: %s", subscription_namespace)

            # Check if /api namespace is connected on the same client
            # Use namespaces.keys() instead of connection_namespaces attribute
            connected_namespaces = set(getattr(self.sio, "namespaces", {}).keys())
            if subscription_namespace not in connected_namespaces:
                _LOGGER.error(
                    "  → Cannot subscribe: namespace %s is not connected (connected: %s)",
                    subscription_namespace,
                    connected_namespaces,
                )
                return False
            
            # According to Homey API docs:
            # 1. Subscribe to manager-level events: homey:manager:devices (PLURAL - not singular!)
            # 2. Subscribe to per-device events: homey:device:{deviceId}
            # 3. The subscribe signature is: emit("subscribe", uri, callback) - URI as second parameter, not in object
            # 4. Listen for events where the event name IS the URI: socket.on(uri, callback)
            
            # Subscribe to manager-level device events (PLURAL: "devices")
            manager_uri = "homey:manager:devices"  # PLURAL - this is correct
            _LOGGER.debug("  → Subscribing to manager-level device events: %s", manager_uri)
            
            # Set up per-URI handler for manager events (event name IS the URI)
            # Homey emits: socket.on(uri, (event, data) => ...) - event name and data as separate args
            def manager_handler(event_name, data):
                """Handler for manager-level events - URI is homey:manager:devices."""
                _LOGGER.debug("📥 HOMEY EVENT uri=%s event=%s data=%s", manager_uri, event_name, str(data)[:500])
                # Manager events come as (event_name, data) where event_name is like "device.update", "capability.update"
                if isinstance(data, dict):
                    # Handle device events
                    if event_name and event_name.startswith("device."):
                        device_id = data.get("id") or data.get("deviceId")
                        if device_id:
                            _LOGGER.debug("  → Manager event: %s for device: %s", event_name, device_id)
                            self._on_device_update(device_id, data)
                        else:
                            _LOGGER.debug("  → Manager event %s has no device ID", event_name)
                    # Handle capability events
                    elif event_name and event_name.startswith("capability."):
                        device_id = data.get("deviceId") or data.get("device", {}).get("id")
                        if device_id:
                            _LOGGER.debug("  → Capability event: %s for device: %s", event_name, device_id)
                            self._on_device_update(device_id, data)
                        else:
                            _LOGGER.debug("  → Capability event %s has no device ID", event_name)
                    else:
                        # Unknown event type - try to extract device ID anyway
                        device_id = data.get("id") or data.get("deviceId")
                        if device_id:
                            _LOGGER.debug("  → Manager event (unknown type %s) for device: %s", event_name, device_id)
                            self._on_device_update(device_id, data)
                        else:
                            _LOGGER.debug("  → Manager event (unknown type %s, no device ID)", event_name)
                else:
                    _LOGGER.debug("  → Manager event data is not a dict: %s", type(data))
            
            self.sio.on(manager_uri, manager_handler, namespace=subscription_namespace)
            _LOGGER.debug("  → Registered event listener for manager URI: %s (namespace: %s)", manager_uri, subscription_namespace)
            
            try:
                _LOGGER.debug("  → Emitting 'subscribe' with URI as plain string: %s", manager_uri)
                # Homey expects: emit("subscribe", uri, namespace="/api") - URI as plain string, not object!
                subscription_acknowledged = False
                
                def subscription_callback(*args):
                    nonlocal subscription_acknowledged
                    subscription_acknowledged = True
                    _LOGGER.debug("  → Subscription callback received for %s: %s", manager_uri, args)
                
                # Use same client with namespace="/api" for subscriptions
                # CRITICAL: URI must be plain string argument, not {uri: "..."}
                await self.sio.emit("subscribe", manager_uri, callback=subscription_callback, namespace=subscription_namespace)
                _LOGGER.debug("  → Subscribe emit sent for %s (namespace: %s)", manager_uri, subscription_namespace)
                
                # Wait a moment to see if callback fires
                await asyncio.sleep(0.5)
                if subscription_acknowledged:
                    _LOGGER.debug("  → Subscription acknowledged via callback for %s", manager_uri)
                else:
                    _LOGGER.debug("  → No callback received for %s (may be normal)", manager_uri)
            except Exception as err:
                _LOGGER.error("  → Failed to subscribe to %s: %s", manager_uri, err, exc_info=True)
            
            # Now subscribe to individual devices
            # According to Homey API docs:
            # 1. Subscribe to each device URI: "homey:device:{deviceId}"
            # 2. Listen to events where the event name IS the URI: socket.on(uri, callback)
            # 3. Subscribe signature: emit("subscribe", uri, callback) - URI as second parameter
            devices = await self.get_devices()
            if devices:
                _LOGGER.debug("  → Found %d devices - subscribing to each device URI", len(devices))
                subscribed_count = 0
                failed_count = 0
                sample_device_id = None
                for idx, device_id in enumerate(devices.keys()):
                    try:
                        device_uri = f"homey:device:{device_id}"
                        # Set up per-URI handler for this device (event name IS the URI)
                        # Homey emits: socket.on(uri, (event, data) => ...) - event name and data as separate args
                        # Use closure to capture device_id and device_uri
                        def make_device_handler(_device_id, _device_uri):
                            def device_handler(event_name, data):
                                """Handler for device-specific URI events."""
                                _LOGGER.debug("📥 HOMEY EVENT uri=%s device_id=%s event=%s data=%s", _device_uri, _device_id, event_name, str(data)[:500])
                                
                                # Handle capability events - convert to device data format
                                if event_name == "capability" and isinstance(data, dict):
                                    capability_id = data.get("capabilityId")
                                    value = data.get("value")
                                    if capability_id and value is not None:
                                        # Convert capability event to device data format
                                        # Format: {"capabilitiesObj": {"onoff": {"value": false}}}
                                        device_update = {
                                            "capabilitiesObj": {
                                                capability_id: {
                                                    "value": value
                                                }
                                            }
                                        }
                                        _LOGGER.debug("  → Capability update: %s = %s", capability_id, value)
                                        self._on_device_update(_device_id, device_update)
                                    else:
                                        # Fallback: pass data as-is
                                        self._on_device_update(_device_id, data if isinstance(data, dict) else {})
                                else:
                                    # Other event types - process as device update
                                    self._on_device_update(_device_id, data if isinstance(data, dict) else {})
                            return device_handler
                        
                        self.sio.on(device_uri, make_device_handler(device_id, device_uri), namespace=subscription_namespace)
                        if idx < 3:  # Log first 3 listener registrations for debugging
                            _LOGGER.debug("  → Registered event listener for device URI: %s (namespace: %s)", device_uri, subscription_namespace)
                        # Subscribe with correct signature: emit("subscribe", uri, namespace="/api")
                        # CRITICAL: URI must be plain string argument, not {uri: "..."}
                        if idx < 3:  # Log first 3 subscriptions for debugging
                            _LOGGER.debug("  → Emitting 'subscribe' with URI as plain string: %s", device_uri)
                        # Use same client with namespace="/api" for subscriptions
                        await self.sio.emit("subscribe", device_uri, namespace=subscription_namespace)
                        subscribed_count += 1
                        if not sample_device_id:
                            sample_device_id = device_id
                    except Exception as err:
                        failed_count += 1
                        if failed_count <= 3:  # Log first 3 failures
                            _LOGGER.error("  → Failed to subscribe to device %s: %s", device_id, err)
                
                if subscribed_count > 0:
                    _LOGGER.debug("  → Subscribed to %d/%d devices successfully", subscribed_count, len(devices))
                    if sample_device_id:
                        _LOGGER.debug("  → Sample device URI subscribed: homey:device:%s", sample_device_id)
                    if failed_count > 0:
                        _LOGGER.warning("  → Failed to subscribe to %d devices", failed_count)
                else:
                    _LOGGER.error("  → Failed to subscribe to any individual devices")
                    return False
            else:
                _LOGGER.debug("  → No devices available to subscribe to")
                return False
            
            _LOGGER.debug("  → All subscriptions sent - Socket.IO ready to receive events")
            _LOGGER.info("Socket.IO Subscription Summary:")
            _LOGGER.info("  → Connected to: %s", self.host)
            _LOGGER.info("  → Namespace: %s", subscription_namespace)
            _LOGGER.info("  → Authenticated: Yes")
            _LOGGER.info("  → Listening for events:")
            _LOGGER.info("    - Manager URI: %s (receives device.create, device.update, device.delete, capability.*)", manager_uri)
            _LOGGER.info("    - Individual device URIs: homey:device:{deviceId} (%d devices)", len(devices) if devices else 0)
            _LOGGER.info("    - Catch-all handler: * (ALL events)")
            _LOGGER.info("  → Test: Change a device in Homey app and watch logs for events")
            _LOGGER.info("=" * 60)
            
            # If we got here, subscription was sent (even if no response)
            # Events will come through the handlers we set up above
            # The catch-all handler will also log any events we're not explicitly listening for
            return True
                
        except Exception as err:
            _LOGGER.warning("Socket.IO device subscription error: %s", err, exc_info=True)
            return False
    
    def _on_sio_connect(self) -> None:
        """Handle Socket.IO connection event."""
        _LOGGER.info("Socket.IO connect event received - connection established")
        # Don't set _sio_connected here - wait until authentication and subscription complete
        # This is set in _connect_socketio after successful auth/subscription
    
    def _on_sio_disconnect(self) -> None:
        """Handle Socket.IO disconnection event."""
        # Don't start reconnect if we're in the middle of connection setup (Step 3)
        if self._sio_connecting:
            _LOGGER.debug("Socket.IO disconnected during connection setup - skipping reconnect")
            return
        
        if self._sio_connected:  # Only log if we were previously connected
            _LOGGER.warning("=" * 60)
            _LOGGER.warning("Socket.IO DISCONNECTED - falling back to polling (5-10 second interval)")
            _LOGGER.warning("Reconnection will be attempted automatically")
            _LOGGER.warning("=" * 60)
        self._sio_connected = False
        # Start reconnection task if not already running
        self._start_sio_reconnect_task()
    
    def _on_sio_connect_error(self, data: Any) -> None:
        """Handle Socket.IO connection error."""
        now = time.time()
        if now - self._last_sio_error_log >= self._ERROR_LOG_INTERVAL:
            self._last_sio_error_log = now
            if self._sio_connected:
                _LOGGER.error("=" * 60)
                _LOGGER.error("Socket.IO CONNECTION ERROR: %s", data)
                _LOGGER.error("Falling back to polling (5-10 second interval)")
                _LOGGER.error("Reconnection will be attempted automatically")
                _LOGGER.error("=" * 60)
            else:
                _LOGGER.error("Socket.IO connection error during initial setup: %s", data)
        else:
            _LOGGER.debug("Socket.IO connect_error (rate limited): %s", data)
        self._sio_connected = False
        # Start reconnection task if not already running
        self._start_sio_reconnect_task()
    
    def _on_sio_manager_event(self, event_name: str, data: dict[str, Any]) -> None:
        """Handle manager-level events from Socket.IO.
        
        Manager events come as (event_name, data) where event_name is like:
        - "device.create", "device.update", "device.delete"
        - "capability.create", "capability.update", "capability.delete"
        
        Args:
            event_name: Event type (e.g., "device.update", "capability.update")
            data: Event data containing device/capability information
        """
        # Log first event to confirm Socket.IO is working
        if not hasattr(self, "_sio_first_event_logged"):
            _LOGGER.info("=" * 60)
            _LOGGER.info("✓ Socket.IO WORKING - Received first manager event")
            _LOGGER.info("Real-time updates confirmed - events arriving instantly")
            _LOGGER.info("  → Event name: %s", event_name)
            _LOGGER.info("  → Data keys: %s", list(data.keys())[:20] if isinstance(data, dict) else "N/A")
            _LOGGER.info("=" * 60)
            self._sio_first_event_logged = True
        
        _LOGGER.info("Socket.IO manager event received: %s", event_name)
        
        # Handle device events
        if event_name.startswith("device."):
            device_id = data.get("id") or data.get("deviceId")
            if device_id:
                _LOGGER.info("  → Device ID: %s", device_id)
                # Process as device update
                self._on_device_update(device_id, data)
        # Handle capability events
        elif event_name.startswith("capability."):
            device_id = data.get("deviceId") or data.get("device", {}).get("id")
            if device_id:
                _LOGGER.info("  → Capability update for device: %s", device_id)
                # Process as device update (capability changes affect device state)
                self._on_device_update(device_id, data)
    
    def _on_sio_device_event(self, *args: Any) -> None:
        """Handle device update event from Socket.IO.
        
        Args:
            *args: Variable arguments - could be (data,) or (event_name, data)
        """
        # Log first event to confirm Socket.IO is working
        if not hasattr(self, "_sio_first_event_logged"):
            _LOGGER.info("=" * 60)
            _LOGGER.info("✓ Socket.IO WORKING - Received first device event")
            _LOGGER.info("Real-time updates confirmed - events arriving instantly")
            _LOGGER.info("  → Args count: %d", len(args))
            for idx, arg in enumerate(args):
                _LOGGER.info("  → Arg[%d] type: %s", idx, type(arg).__name__)
                if isinstance(arg, dict):
                    _LOGGER.info("  → Arg[%d] keys: %s", idx, list(arg.keys())[:20])
                _LOGGER.info("  → Arg[%d] value: %s", idx, str(arg)[:500])
            _LOGGER.info("=" * 60)
            _LOGGER.info("=" * 60)
            self._sio_first_event_logged = True
        
        # Always log device events at INFO level so we can see them
        _LOGGER.info("Socket.IO device event received: %d args, first arg type: %s", 
                    len(args), type(args[0]).__name__ if args else "None")
        if args and isinstance(args[0], dict):
            device_id = args[0].get("id") or args[0].get("deviceId")
            if device_id:
                _LOGGER.info("  → Device ID: %s", device_id)
        
        # Handle different call signatures
        data = None
        if not args:
            return
            # If first arg is a string, it might be the event name
            if len(args) == 1:
                data = args[0]
            elif len(args) >= 2:
                # Event name, then data
                data = args[1] if isinstance(args[1], dict) else args[0]
            else:
                data = args[0]
        
        if not data:
            return
        
        # Data structure may vary - handle different formats
        # Expected formats:
        # 1. {"id": "device_id", ...device_data...} - direct device data
        # 2. {"device": {"id": "device_id", ...}} - nested device format
        # 3. {"deviceId": "device_id", ...} - alternative format
        # 4. Array of devices: [{"id": "device_id", ...}, ...]
        # 5. Event with URI and data: {"uri": "homey:manager:device:device_id", "data": {...}}
        device_id = None
        device_data = None
        
        if isinstance(data, dict):
            # Check for URI-based format first
            if "uri" in data and "data" in data:
                uri = data.get("uri", "")
                if "homey:manager:device" in uri:
                    # Extract device ID from URI if present
                    parts = uri.split(":")
                    if len(parts) > 3:
                        device_id = parts[-1]  # Last part is device ID
                    device_data = data.get("data", {})
                    if not device_id and "id" in device_data:
                        device_id = device_data.get("id")
            elif "id" in data:
                # Direct device data format
                device_id = data.get("id")
                device_data = data
            elif "device" in data:
                # Nested device format
                device = data.get("device", {})
                device_id = device.get("id")
                device_data = device
            elif "deviceId" in data:
                # Alternative format
                device_id = data.get("deviceId")
                device_data = data
        elif isinstance(data, list) and len(data) > 0:
            # Array of devices - process each one
            for item in data:
                if isinstance(item, dict) and "id" in item:
                    self._on_device_update(item.get("id"), item)
            return
        
        if device_id and device_data:
            # Log Socket.IO event arrival for debugging
            _LOGGER.debug("Socket.IO event received for device %s", device_id)
            # Call existing handler
            self._on_device_update(device_id, device_data)
        else:
            # Only log unexpected formats at debug level (not info)
            _LOGGER.debug("Socket.IO device event unexpected format: %s", data)
    
    def _start_sio_reconnect_task(self) -> None:
        """Start background task to periodically attempt Socket.IO reconnection."""
        # Only start if not already running and we have a session
        if (self._sio_reconnect_task is None or self._sio_reconnect_task.done()) and self.session:
            # Get the event loop - if we're in Home Assistant, use hass.loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._sio_reconnect_task = asyncio.create_task(self._sio_reconnect_loop())
            except Exception as err:
                _LOGGER.warning("Could not start Socket.IO reconnection task: %s", err)
    
    def _stop_sio_reconnect_task(self) -> None:
        """Stop the Socket.IO reconnection task."""
        if self._sio_reconnect_task and not self._sio_reconnect_task.done():
            self._sio_reconnect_task.cancel()
        self._sio_reconnect_task = None
    
    async def _sio_reconnect_loop(self) -> None:
        """Background loop to periodically attempt Socket.IO reconnection."""
        import time
        attempt_count = 0
        while True:
            try:
                # Wait before attempting reconnection
                await asyncio.sleep(self._sio_reconnect_interval)
                
                # Only attempt if we're not already connected
                if not self._sio_connected and self.session:
                    attempt_count += 1
                    _LOGGER.debug("Socket.IO reconnection attempt #%d...", attempt_count)
                    try:
                        success = await self._connect_socketio()
                        if success:
                            _LOGGER.info("=" * 60)
                            _LOGGER.info("Socket.IO RECONNECTED - real-time updates restored")
                            _LOGGER.info("Polling continues as backup (1 second interval)")
                            _LOGGER.info("=" * 60)
                            # Reset first event flag so we log when events resume
                            if hasattr(self, "_sio_first_event_logged"):
                                delattr(self, "_sio_first_event_logged")
                            return  # Exit loop since we're connected
                        else:
                            _LOGGER.debug("Socket.IO reconnection attempt #%d failed - will retry in %d seconds", attempt_count, self._sio_reconnect_interval)
                    except Exception as err:
                        _LOGGER.debug("Socket.IO reconnection attempt #%d error: %s", attempt_count, err)
                        # Continue loop to try again later
                elif self._sio_connected:
                    # Already connected - exit loop
                    _LOGGER.debug("Socket.IO already connected - stopping reconnection loop")
                    return
                else:
                    # Session not available - exit loop
                    return
            except asyncio.CancelledError:
                # Task was cancelled - exit cleanly
                return
            except Exception as err:
                _LOGGER.error("Error in Socket.IO reconnection loop: %s", err, exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(10)
    
    async def _disconnect_socketio(self) -> None:
        """Disconnect Socket.IO client."""
        # Stop reconnection task
        self._stop_sio_reconnect_task()
        
        # Disconnect the single client (handles both root and /api namespaces)
        if self.sio:
            try:
                if self.sio.connected:
                    await self.sio.disconnect()
            except Exception as err:
                _LOGGER.debug("Error disconnecting Socket.IO: %s", err)
            finally:
                self.sio = None
        
        # Close the aiohttp session we created for Socket.IO (prevents "Unclosed client session")
        if self._sio_http_session:
            try:
                await self._sio_http_session.close()
            except Exception as err:
                _LOGGER.debug("Error closing Socket.IO http session: %s", err)
            finally:
                self._sio_http_session = None
        
        self._sio_connected = False
        self.sio_namespace = None
        self.sio_token = None

    def add_device_listener(self, listener: Callable[[str, dict[str, Any]], None]) -> None:
        """Add a listener for device updates."""
        self._listeners.append(listener)

    def remove_device_listener(self, listener: Callable[[str, dict[str, Any]], None]) -> None:
        """Remove a device update listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    async def disconnect(self) -> None:
        """Disconnect from Homey API."""
        # Stop reconnection task
        self._stop_sio_reconnect_task()
        
        await self._disconnect_socketio()

        if self.session:
            await self.session.close()
            self.session = None

