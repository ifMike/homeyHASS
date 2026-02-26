"""Config flow for Homey integration."""
from __future__ import annotations

import logging
import ssl
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv, device_registry as dr, selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import (
    CONF_DEVICE_FILTER,
    CONF_POLL_INTERVAL,
    CONF_RECOVERY_COOLDOWN,
    CONF_INVERT_LIGHT_TEMPERATURE,
    CONF_EXPOSE_SETTABLE_TEXT,
    CONF_EXPOSE_READONLY_STRINGS,
    CONF_USE_CAPABILITY_TITLES,
    CONF_TOKEN,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RECOVERY_COOLDOWN,
    DEFAULT_INVERT_LIGHT_TEMPERATURE,
    DEFAULT_EXPOSE_SETTABLE_TEXT,
    DEFAULT_EXPOSE_READONLY_STRINGS,
    DEFAULT_USE_CAPABILITY_TITLES,
    DOMAIN,
)
from .device_info import get_device_type

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="homey.local"): str,
        vol.Required(CONF_TOKEN): str,
    }
)

def _dhcp_confirm_schema(discovered_host: str) -> vol.Schema:
    """Schema for discovery confirmation with editable host."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=discovered_host): str,
            vol.Required(CONF_TOKEN): str,
        }
    )


async def _async_find_reachable_host(addresses: list[str]) -> str | None:
    """Try addresses (IPv4 first) and return the first reachable one."""
    ipv4 = [a for a in addresses if ":" not in a]
    ipv6 = [a for a in addresses if ":" in a]
    for addr in ipv4 + ipv6:
        if await _async_check_homey_reachable(addr):
            return addr
    return None


async def _async_check_homey_reachable(host: str) -> bool:
    """Check if a device at host responds as Homey (reachable, returns 200 or 401)."""
    if not host or host == "unknown":
        return False
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    use_https = host.startswith("https://")
    timeout = aiohttp.ClientTimeout(total=5)
    if use_https:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
    else:
        connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(f"{host}/api/manager/system/info") as response:
                return response.status in (200, 401)
    except Exception:
        return False


class HomeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Homey."""

    VERSION = 1

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> FlowResult:
        """Handle DHCP discovery."""
        macaddress = dr.format_mac(discovery_info.macaddress)

        _LOGGER.info(
            "DHCP discovery: Homey detected at %s (MAC %s)",
            discovery_info.ip,
            macaddress,
        )

        # Check if the device responds as Homey (reachable, returns 200 or 401).
        # If unreachable (e.g. HA in Docker, firewall), still show form - user can try.
        if not await _async_check_homey_reachable(discovery_info.ip):
            _LOGGER.warning(
                "DHCP discovery: Could not reach Homey at %s - showing form anyway "
                "(check network/firewall if setup fails)",
                discovery_info.ip,
            )

        await self.async_set_unique_id(macaddress)
        # Do NOT pass updates= - would overwrite user's configured host (e.g. Ethernet 192.168.1.x)
        # with discovery address (e.g. WiFi 192.168.3.x). User chooses host in Options.
        self._abort_if_unique_id_configured()

        self._discovered_ip = discovery_info.ip

        return await self.async_step_dhcp_confirm()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle Zeroconf (mDNS) discovery.

        Homey broadcasts _homey._tcp via mDNS. This discovery path does not
        depend on MAC address, so it works even when DHCP discovery fails
        (e.g. different MAC prefix, Docker networking, or router not reporting).

        When Homey has multiple interfaces (e.g. Ethernet + WiFi), we try each
        address and prefer the first reachable one (IPv4 before IPv6).
        """
        hostname = (discovery_info.hostname or discovery_info.host or "").rstrip(".")
        addresses = discovery_info.addresses or ([discovery_info.host] if discovery_info.host else [])

        _LOGGER.debug(
            "Zeroconf discovery: Homey detected at %s (hostname: %s)",
            ", ".join(addresses),
            hostname,
        )

        # Try all addresses (IPv4 first) and use first reachable
        reachable = await _async_find_reachable_host(addresses)
        if reachable:
            host = reachable
            _LOGGER.info("Zeroconf discovery: Homey found at %s", host)
        else:
            # Prefer IPv4 when none reachable; avoid IPv6 (often fails on local networks)
            ipv4 = [a for a in addresses if ":" not in a]
            if ipv4:
                host = ipv4[0]
                _LOGGER.debug(
                    "Zeroconf discovery: Could not reach Homey - defaulting to IPv4 %s",
                    host,
                )
            elif hostname:
                host = hostname
                _LOGGER.debug(
                    "Zeroconf discovery: Could not reach Homey - using hostname %s (user can enter IP if needed)",
                    host,
                )
            else:
                host = addresses[0] if addresses else "homey.local"
                _LOGGER.debug("Zeroconf discovery: Defaulting to %s", host)

        await self.async_set_unique_id(hostname or host or "homey")
        # Do NOT pass updates= - would overwrite user's configured host (e.g. Ethernet 192.168.1.x)
        # with discovery address (e.g. WiFi 192.168.3.x). User chooses host in Options.
        self._abort_if_unique_id_configured()

        self._discovered_ip = host

        return await self.async_step_dhcp_confirm()

    async def async_step_dhcp_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle DHCP/Zeroconf discovery confirmation.

        Form includes host so user can correct it when auto-detection picks the
        wrong address (e.g. IPv6 or different subnet).
        """
        errors: dict[str, str] = {}
        discovered_host = getattr(self, "_discovered_ip", "homey.local")

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            host = user_input.get(CONF_HOST, discovered_host).strip()
            if not host.startswith(("http://", "https://")):
                host = f"http://{host}"

            valid, working_endpoint, error_key = await self._async_validate_host_token(
                host, token
            )
            if valid:
                return self.async_create_entry(
                    title=f"Homey ({user_input.get(CONF_HOST, discovered_host)})",
                    data={
                        CONF_HOST: host,
                        CONF_TOKEN: token,
                        "working_endpoint": working_endpoint or "manager",
                        CONF_DEVICE_FILTER: None,
                        CONF_USE_CAPABILITY_TITLES: DEFAULT_USE_CAPABILITY_TITLES,
                    },
                )
            if error_key:
                errors["base"] = error_key
                # Preserve user's host when re-showing form after error
                discovered_host = user_input.get(CONF_HOST, discovered_host).strip()

        return self.async_show_form(
            step_id="dhcp_confirm",
            data_schema=_dhcp_confirm_schema(discovered_host),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthentication flow."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication and update credentials."""
        errors: dict[str, str] = {}
        entry = getattr(self, "_reauth_entry", None)
        current_host = entry.data.get(CONF_HOST, "") if entry else ""

        if user_input is not None:
            host = user_input[CONF_HOST].strip().rstrip("/")
            token = user_input[CONF_TOKEN].strip()

            if not host.startswith(("http://", "https://")):
                host = f"http://{host}"

            valid, working_endpoint, error_key = await self._async_validate_host_token(
                host, token
            )
            if valid and entry:
                new_data = {
                    **entry.data,
                    CONF_HOST: host,
                    CONF_TOKEN: token,
                    "working_endpoint": working_endpoint or entry.data.get("working_endpoint"),
                }
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            if error_key:
                errors["base"] = error_key

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        _LOGGER.info("Homey options flow registered for entry: %s", config_entry.entry_id)
        return HomeyOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the connection
            try:
                host = user_input[CONF_HOST].strip().rstrip("/")
                token = user_input[CONF_TOKEN].strip()

                # Ensure host has protocol
                if not host.startswith(("http://", "https://")):
                    host = f"http://{host}"

                # Detect if using HTTPS for SSL handling
                use_https = host.startswith("https://")

                # Test connection - try multiple possible endpoints
                # For HTTPS connections (self-hosted servers), we need SSL but disable verification for self-signed certs
                # For HTTP connections (local Homey), disable SSL entirely
                timeout = aiohttp.ClientTimeout(total=10)
                if use_https:
                    # For HTTPS: create SSL context that doesn't verify certificates (for self-signed certs)
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                else:
                    # For HTTP: disable SSL entirely
                    connector = aiohttp.TCPConnector(ssl=False)
                
                # Try different possible endpoints based on Homey API documentation
                endpoints_to_try = [
                    "/api/manager/system/info",  # Manager API structure
                    "/api/manager/system/info/",  # With trailing slash
                    "/api/manager/system",
                    "/api/manager/system/",
                    "/api/v1/manager/system/info",
                    "/api/v1/manager/system/info/",
                    "/api/v1/manager/system",
                    "/api/v1/manager/system/",
                    "/api/v1/system/info",
                    "/api/v1/system/info/",
                    "/api/v1/system",
                    "/api/v1/system/",
                ]
                
                data = None
                last_error = None
                last_error_details = None
                auth_errors = []  # Track 401 errors from different endpoints
                error_details = []  # Collect detailed error information
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"Authorization": f"Bearer {token}"},
                ) as session:
                    for endpoint in endpoints_to_try:
                        url = f"{host}{endpoint}"
                        _LOGGER.debug("Trying endpoint: %s", url)
                        
                        try:
                            async with session.get(url) as response:
                                _LOGGER.debug("Response status: %s for %s", response.status, url)
                                
                                if response.status == 200:
                                    try:
                                        data = await response.json()
                                        _LOGGER.info("Successfully connected to Homey using endpoint: %s", endpoint)
                                        break
                                    except Exception as json_err:
                                        # If JSON parsing fails, read text for debugging
                                        try:
                                            response_text = await response.read()
                                            error_msg = f"HTTP 200 but JSON parse failed: {str(json_err)}"
                                            error_details.append(f"{url}: {error_msg}")
                                            _LOGGER.warning("Failed to parse JSON from %s: %s, body: %s", url, json_err, response_text[:200].decode('utf-8', errors='ignore'))
                                        except:
                                            error_msg = f"HTTP 200 but JSON parse failed: {str(json_err)}"
                                            error_details.append(f"{url}: {error_msg}")
                                            _LOGGER.warning("Failed to parse JSON from %s: %s", url, json_err)
                                        # Continue to next endpoint
                                elif response.status == 401:
                                    # Some endpoints may return 401 even with valid credentials
                                    # Track it but continue trying other endpoints
                                    auth_errors.append(endpoint)
                                    try:
                                        response_text = await response.text()
                                        error_details.append(f"{url}: HTTP 401 Unauthorized - {response_text[:200]}")
                                    except:
                                        error_details.append(f"{url}: HTTP 401 Unauthorized")
                                    _LOGGER.debug("Authentication failed with endpoint %s (will try other endpoints)", endpoint)
                                    continue
                                elif response.status == 404:
                                    _LOGGER.debug("Endpoint %s not found, trying next...", endpoint)
                                    last_error = f"Endpoint {endpoint} not found"
                                    last_error_details = f"HTTP 404 Not Found for {url}"
                                    error_details.append(last_error_details)
                                    continue
                                else:
                                    try:
                                        response_text = await response.text()
                                        error_msg = f"HTTP {response.status} - {response_text[:200]}"
                                        error_details.append(f"{url}: {error_msg}")
                                        _LOGGER.debug("Unexpected status %s for %s: %s", response.status, url, response_text[:200])
                                    except:
                                        error_msg = f"HTTP {response.status}"
                                        error_details.append(f"{url}: {error_msg}")
                                        _LOGGER.debug("Unexpected status %s for %s", response.status, url)
                                    last_error = f"Status {response.status} for {endpoint}"
                                    last_error_details = error_msg
                                    continue
                        except Exception as err:
                            error_msg = f"Connection error: {str(err)}"
                            error_details.append(f"{url}: {error_msg}")
                            _LOGGER.debug("Error trying endpoint %s: %s", endpoint, err)
                            last_error = str(err)
                            last_error_details = error_msg
                            continue
                    
                    # If we got data from any endpoint, proceed
                    if data:
                        # Success - ignore any 401 errors from other endpoints
                        pass
                    elif auth_errors and len(auth_errors) == len(endpoints_to_try):
                        # ALL endpoints returned 401 - this means invalid credentials
                        # Show a summary of errors
                        probable_cause = "Probable cause: Invalid API key or API key missing required permissions. Check Homey Settings → API Keys."
                        if error_details:
                            error_summary = "\n".join(error_details[:3])  # Show first 3 errors
                            if len(error_details) > 3:
                                error_summary += f"\n... ({len(error_details) - 3} more similar errors)"
                            errors["base"] = f"invalid_auth\n\n{probable_cause}\n\nError details:\n{error_summary}"
                        else:
                            errors["base"] = f"invalid_auth\n\n{probable_cause}"
                        _LOGGER.error("Authentication failed with all system endpoints. Check your API key.")
                        return self.async_show_form(
                            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
                        )
                    # Otherwise, continue to fallback (devices endpoint)
                    
                    # If we got data from any endpoint, proceed
                    if data:
                        # Use Homey name as unique ID
                        unique_id = data.get("id") or data.get("homeyId") or host
                        name = data.get("name") or data.get("homeyName") or "Homey"
                        
                        # Determine which endpoint structure worked
                        working_endpoint = "manager" if "/api/manager" in endpoint else "v1"

                        await self.async_set_unique_id(unique_id)
                        self._abort_if_unique_id_configured()

                        # Store connection info for device selection step
                        self.host = host
                        self.token = token
                        self.working_endpoint = working_endpoint
                        
                        # Move to device selection step
                        return await self.async_step_device_selection()
                    else:
                        # Try devices endpoint as final fallback - if this works, API is accessible
                        _LOGGER.debug("System endpoints failed, trying devices endpoint as fallback...")
                        device_endpoints = [
                            "/api/manager/devices/device/",  # Manager API structure with trailing slash
                            "/api/manager/devices/device",
                            "/api/v1/device/",
                            "/api/v1/device",
                        ]
                        device_auth_errors = []
                        
                        for device_endpoint in device_endpoints:
                            try:
                                url = f"{host}{device_endpoint}"
                                _LOGGER.debug("Trying devices endpoint: %s", url)
                                async with session.get(url) as response:
                                    response_text = await response.text()
                                    _LOGGER.debug("Devices endpoint %s returned status %s, body: %s", device_endpoint, response.status, response_text[:500])
                                    
                                    if response.status == 200:
                                        # Devices endpoint works, so API is accessible
                                        _LOGGER.info("Devices endpoint accessible at %s, proceeding with setup", device_endpoint)
                                        await self.async_set_unique_id(host)
                                        self._abort_if_unique_id_configured()
                                        
                                        # Determine which endpoint structure worked
                                        working_endpoint = "manager" if "/api/manager" in device_endpoint else "v1"
                                        
                                        # Store connection info for device selection step
                                        self.host = host
                                        self.token = token
                                        self.working_endpoint = working_endpoint
                                        
                                        # Move to device selection step
                                        return await self.async_step_device_selection()
                                    elif response.status == 401:
                                        # Track 401 but continue trying other device endpoints
                                        device_auth_errors.append(device_endpoint)
                                        try:
                                            error_details.append(f"{url}: HTTP 401 Unauthorized - {response_text[:200]}")
                                        except:
                                            error_details.append(f"{url}: HTTP 401 Unauthorized")
                                        _LOGGER.debug("Authentication failed with devices endpoint %s (will try other endpoints)", device_endpoint)
                                        continue
                                    elif response.status == 404:
                                        error_details.append(f"{url}: HTTP 404 Not Found")
                                        _LOGGER.debug("Devices endpoint %s not found, trying next...", device_endpoint)
                                        continue
                                    else:
                                        error_msg = f"HTTP {response.status} - {response_text[:200]}"
                                        error_details.append(f"{url}: {error_msg}")
                                        _LOGGER.debug("Unexpected status %s for %s: %s", response.status, device_endpoint, response_text[:200])
                                        continue
                            except Exception as dev_err:
                                url = f"{host}{device_endpoint}"
                                error_msg = f"Connection error: {str(dev_err)}"
                                error_details.append(f"{url}: {error_msg}")
                                _LOGGER.debug("Error trying devices endpoint %s: %s", device_endpoint, dev_err)
                                continue
                        
                        # If we get here, all endpoints failed
                        # Check if we got 401 from any API endpoints (especially the devices endpoint)
                        # If we got 401 from actual API endpoints, it's an auth issue, not a connection issue
                        all_auth_errors = auth_errors + device_auth_errors
                        total_endpoints_tried = len(endpoints_to_try) + len(device_endpoints)
                        
                        # Prioritize 401 errors: if we got 401 from any actual API endpoint, it's invalid_auth
                        # (404s are normal - not all endpoints exist, but 401s mean auth failed)
                        has_auth_error_from_key_endpoint = (
                            device_auth_errors or  # Got 401 from devices endpoint (main API endpoint)
                            len(auth_errors) > 0   # Got 401 from system endpoints
                        )
                        
                        if len(all_auth_errors) == total_endpoints_tried or has_auth_error_from_key_endpoint:
                            # Got 401 from API endpoints - invalid credentials
                            probable_cause = "Probable cause: Invalid API key or API key missing required permissions. Check Homey Settings → API Keys."
                            if error_details:
                                # Show 401 errors first (they're most relevant)
                                auth_error_details = [e for e in error_details if "401" in e]
                                if auth_error_details:
                                    error_summary = "\n".join(auth_error_details[:3])
                                    if len(auth_error_details) > 3:
                                        error_summary += f"\n... ({len(auth_error_details) - 3} more similar errors)"
                                else:
                                    error_summary = "\n".join(error_details[:3])
                                    if len(error_details) > 3:
                                        error_summary += f"\n... ({len(error_details) - 3} more similar errors)"
                                errors["base"] = f"invalid_auth\n\n{probable_cause}\n\nError details:\n{error_summary}"
                            else:
                                errors["base"] = f"invalid_auth\n\n{probable_cause}"
                            _LOGGER.error("Authentication failed with API endpoints. Please verify your API key is correct and has the required permissions.")
                        else:
                            # Some endpoints returned 404 or other errors - connection issue
                            # Determine probable cause based on error types
                            has_connection_errors = any("Connection error" in e or "Connection refused" in e or "Name resolution" in e for e in error_details)
                            has_timeout = any("timeout" in e.lower() for e in error_details)
                            
                            if has_connection_errors:
                                probable_cause = f"Probable cause: Cannot reach Homey at {host}. Check that:\n- The IP address/hostname is correct\n- Homey is powered on and on the same network\n- Firewall is not blocking connections"
                            elif has_timeout:
                                probable_cause = f"Probable cause: Connection timeout. Homey at {host} is not responding. Check that:\n- Homey is powered on\n- Network connectivity is working\n- Firewall is not blocking connections"
                            else:
                                probable_cause = f"Probable cause: Cannot connect to Homey API at {host}. Check that:\n- The IP address/hostname is correct\n- Homey API is enabled in settings\n- Network connectivity is working"
                            
                            if error_details:
                                # Show most relevant errors (prioritize non-404 errors)
                                non_404_errors = [e for e in error_details if "404" not in e]
                                if non_404_errors:
                                    error_summary = "\n".join(non_404_errors[:3])
                                    if len(non_404_errors) > 3:
                                        error_summary += f"\n... ({len(non_404_errors) - 3} more errors)"
                                else:
                                    error_summary = "\n".join(error_details[:3])
                                    if len(error_details) > 3:
                                        error_summary += f"\n... ({len(error_details) - 3} more errors)"
                                
                                if last_error_details:
                                    errors["base"] = f"cannot_connect\n\n{probable_cause}\n\nLast error: {last_error_details}\n\nAll errors:\n{error_summary}"
                                else:
                                    errors["base"] = f"cannot_connect\n\n{probable_cause}\n\nError details:\n{error_summary}"
                            else:
                                errors["base"] = f"cannot_connect\n\n{probable_cause}"
                            _LOGGER.error("Could not connect to Homey API. Tried system endpoints: %s and device endpoints: %s. Last error: %s", endpoints_to_try, device_endpoints, last_error)
            except aiohttp.ClientConnectorError as err:
                error_msg = str(err)
                probable_cause = f"Probable cause: Cannot reach Homey at {host}. Check that:\n- The IP address/hostname is correct\n- Homey is powered on and on the same network\n- Firewall is not blocking connections"
                errors["base"] = f"cannot_connect\n\n{probable_cause}\n\nError details:\nConnection error: {error_msg}"
                _LOGGER.error("Connection error: %s", err)
            except aiohttp.ServerTimeoutError as err:
                error_msg = f"Connection timeout after 10 seconds"
                probable_cause = f"Probable cause: Homey at {host} is not responding. Check that:\n- Homey is powered on\n- Network connectivity is working\n- Firewall is not blocking connections\n- Try using the IP address instead of hostname"
                errors["base"] = f"cannot_connect\n\n{probable_cause}\n\nError details:\n{error_msg}"
                _LOGGER.error("Connection timeout")
            except aiohttp.ClientError as err:
                error_msg = str(err)
                probable_cause = f"Probable cause: Network or HTTP error connecting to {host}. Check that:\n- The IP address/hostname is correct\n- Homey API is enabled\n- Network connectivity is working"
                errors["base"] = f"cannot_connect\n\n{probable_cause}\n\nError details:\nClient error: {error_msg}"
                _LOGGER.error("Client error: %s", err)
            except Exception as err:
                error_msg = str(err)
                probable_cause = "Probable cause: Unexpected error occurred. Check the logs for more details."
                errors["base"] = f"unknown\n\n{probable_cause}\n\nError details:\nUnexpected error: {error_msg}"
                _LOGGER.exception("Unexpected exception: %s", err)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_device_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step."""
        errors: dict[str, str] = {}
        
        # Store device_id to display_name mapping for parsing user input
        if not hasattr(self, "_device_id_to_display_name"):
            self._device_id_to_display_name: dict[str, str] = {}
        
        # Fetch devices and zones from Homey
        devices = {}
        zones = {}
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self.token}"},
            ) as session:
                # Try to get devices
                device_endpoints = [
                    f"{self.host}/api/manager/devices/device/",
                    f"{self.host}/api/manager/devices/device",
                    f"{self.host}/api/v1/device/",
                    f"{self.host}/api/v1/device",
                ]
                
                for device_endpoint in device_endpoints:
                    try:
                        async with session.get(device_endpoint) as response:
                            if response.status == 200:
                                devices_data = await response.json()
                                # Handle both dict and list responses
                                if isinstance(devices_data, dict):
                                    devices = devices_data
                                elif isinstance(devices_data, list):
                                    devices = {
                                        device.get("id", str(i)): device
                                        for i, device in enumerate(devices_data)
                                    }
                                break
                    except Exception as err:
                        _LOGGER.debug("Error fetching devices from %s: %s", device_endpoint, err)
                        continue
                
                # Try to get zones (rooms)
                # Note: Zones may require additional API permissions (homey.zone.readonly)
                # If zones can't be fetched, we'll proceed without room grouping
                zone_endpoints = [
                    f"{self.host}/api/manager/zones/zone/",
                    f"{self.host}/api/manager/zones/zone",
                    f"{self.host}/api/v1/zone/",
                    f"{self.host}/api/v1/zone",
                ]
                
                zones_fetched = False
                for zone_endpoint in zone_endpoints:
                    try:
                        async with session.get(zone_endpoint) as response:
                            if response.status == 200:
                                zones_data = await response.json()
                                if isinstance(zones_data, dict):
                                    zones = zones_data
                                elif isinstance(zones_data, list):
                                    zones = {
                                        zone.get("id", str(i)): zone
                                        for i, zone in enumerate(zones_data)
                                    }
                                zones_fetched = True
                                _LOGGER.debug("Successfully fetched zones from %s", zone_endpoint)
                                break
                            elif response.status == 401:
                                _LOGGER.debug(
                                    "Zones endpoint requires authentication - may need homey.zone.readonly permission"
                                )
                                continue
                            elif response.status == 403:
                                _LOGGER.debug(
                                    "Zones endpoint forbidden - API key may not have homey.zone.readonly permission"
                                )
                                continue
                    except Exception as err:
                        _LOGGER.debug("Error fetching zones from %s: %s", zone_endpoint, err)
                        continue
                
                if not zones_fetched:
                    _LOGGER.info(
                        "Could not fetch zones/rooms from Homey. Devices will be shown without room grouping. "
                        "This may require homey.zone.readonly permission in your API key."
                    )
                    zones = {}
        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            errors["base"] = "cannot_fetch_devices"
        
        if user_input is not None:
            # User has selected devices from multi-select
            selected_device_ids = user_input.get(CONF_DEVICE_FILTER, [])
            
            # If no devices selected, import all (None means import all)
            if not selected_device_ids:
                selected_device_ids = None
            
            # Get Homey name for entry title
            name = "Homey"
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"Authorization": f"Bearer {self.token}"},
                ) as session:
                    for endpoint in ["/api/manager/system/info", "/api/v1/system"]:
                        try:
                            async with session.get(f"{self.host}{endpoint}") as response:
                                if response.status == 200:
                                    data = await response.json()
                                    name = data.get("name") or data.get("homeyName") or "Homey"
                                    break
                        except Exception:
                            continue
            except Exception:
                pass
            
            return self.async_create_entry(
                title=name,
                data={
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    "working_endpoint": self.working_endpoint,
                    CONF_DEVICE_FILTER: selected_device_ids,  # None means import all
                    CONF_USE_CAPABILITY_TITLES: True,
                },
            )
        
        if not devices:
            # No devices found or error - proceed without selection
            _LOGGER.warning("No devices found or error fetching devices, proceeding with all devices")
            return self.async_create_entry(
                title="Homey",
                data={
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    "working_endpoint": self.working_endpoint,
                    CONF_DEVICE_FILTER: None,  # Import all
                    CONF_USE_CAPABILITY_TITLES: True,
                },
            )
        
        # Group devices by room/zone and type for better organization
        devices_by_room_and_type: dict[str, dict[str, list[tuple[str, dict[str, Any], str]]]] = {}
        devices_no_room_by_type: dict[str, list[tuple[str, dict[str, Any], str]]] = {}
        
        # Device type labels for display
        type_labels = {
            "light": "Light",
            "switch": "Switch",
            "sensor": "Sensor",
            "binary_sensor": "Binary Sensor",
            "cover": "Cover",
            "climate": "Climate",
            "fan": "Fan",
            "lock": "Lock",
            "media_player": "Media Player",
            "device": "Device",
        }
        
        # Check if we have zones - if not, don't group by room
        has_zones = bool(zones)
        
        for device_id, device in devices.items():
            capabilities = device.get("capabilitiesObj", {})
            driver_uri = device.get("driverUri")
            device_class = device.get("class")
            device_type = get_device_type(capabilities, driver_uri, device_class)
            type_label = type_labels.get(device_type, "Device")
            zone_id = device.get("zone")
            
            # Only group by room if we have zones AND device has a zone
            if has_zones and zone_id and zone_id in zones:
                zone_name = zones[zone_id].get("name", "Unknown Room")
                if zone_name not in devices_by_room_and_type:
                    devices_by_room_and_type[zone_name] = {}
                if device_type not in devices_by_room_and_type[zone_name]:
                    devices_by_room_and_type[zone_name][device_type] = []
                devices_by_room_and_type[zone_name][device_type].append(
                    (device_id, device, type_label)
                )
            else:
                # Device has no room or zones couldn't be fetched
                if device_type not in devices_no_room_by_type:
                    devices_no_room_by_type[device_type] = []
                devices_no_room_by_type[device_type].append((device_id, device, type_label))
        
        # Build device options dict for multi-select (cv.multi_select works with voluptuous_serialize)
        # Format: {device_id: "Room • Type • Device Name"}
        device_options: dict[str, str] = {}
        
        # Device type order for consistent sorting (most common first)
        type_order = [
            "light",
            "switch",
            "cover",
            "climate",
            "fan",
            "lock",
            "media_player",
            "sensor",
            "binary_sensor",
            "device",
        ]
        
        # Build options dict grouped by room, then by type (sorted alphabetically)
        for room_name in sorted(devices_by_room_and_type.keys()):
            room_types = devices_by_room_and_type[room_name]
            # Sort types by our preferred order, then alphabetically
            sorted_types = sorted(
                room_types.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t),
            )
            
            for device_type in sorted_types:
                room_devices = sorted(
                    room_types[device_type],
                    key=lambda x: x[1].get("name", "").lower(),
                )
                
                for device_id, device, type_label in room_devices:
                    device_name = device.get("name", f"Device {device_id}")
                    # Create display name with room (if available), type, and device name
                    if room_name and room_name != "Unknown Room":
                        display_name = f"{room_name} • {type_label} • {device_name}"
                    else:
                        display_name = f"{type_label} • {device_name}"
                    device_options[device_id] = display_name
        
        # Add devices without room, grouped by type
        if devices_no_room_by_type:
            sorted_no_room_types = sorted(
                devices_no_room_by_type.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t),
            )
            
            for device_type in sorted_no_room_types:
                type_label = type_labels.get(device_type, "Device")
                devices_no_room_sorted = sorted(
                    devices_no_room_by_type[device_type],
                    key=lambda x: x[1].get("name", "").lower(),
                )
                
                for device_id, device, type_label_actual in devices_no_room_sorted:
                    device_name = device.get("name", f"Device {device_id}")
                    # Only show "No Room" if we successfully fetched zones but device has no room
                    if zones:
                        display_name = f"No Room • {type_label_actual} • {device_name}"
                    else:
                        display_name = f"{type_label_actual} • {device_name}"
                    device_options[device_id] = display_name
        
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEVICE_FILTER, default=list(device_options.keys())
                ): cv.multi_select(device_options)
            }
        )
        return self.async_show_form(
            step_id="device_selection", data_schema=schema, errors=errors
        )

    async def _async_validate_host_token(
        self, host: str, token: str
    ) -> tuple[bool, str | None, str | None]:
        """Validate Homey host and token. Returns (valid, working_endpoint, error_key)."""
        use_https = host.startswith("https://")
        timeout = aiohttp.ClientTimeout(total=10)
        if use_https:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
        else:
            connector = aiohttp.TCPConnector(ssl=False)

        endpoints_to_try = [
            "/api/manager/system/info",
            "/api/manager/system/info/",
            "/api/manager/system",
            "/api/manager/system/",
            "/api/v1/manager/system/info",
            "/api/v1/manager/system/info/",
            "/api/v1/manager/system",
            "/api/v1/manager/system/",
            "/api/v1/system/info",
            "/api/v1/system/info/",
            "/api/v1/system",
            "/api/v1/system/",
        ]

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"},
        ) as session:
            for endpoint in endpoints_to_try:
                try:
                    async with session.get(f"{host}{endpoint}") as response:
                        if response.status == 200:
                            working_endpoint = (
                                "manager" if "/api/manager" in endpoint else "v1"
                            )
                            return True, working_endpoint, None
                        if response.status == 401:
                            return False, None, "invalid_auth"
                except Exception:
                    continue
        return False, None, "cannot_connect"


class HomeyOptionsFlowHandlerLegacy(config_entries.OptionsFlow):
    """Handle options for the Homey integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize Homey options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the Homey options."""
        if user_input is not None:
            host = user_input[CONF_HOST].strip().rstrip("/")
            token = user_input.get(CONF_TOKEN, "").strip()
            poll_interval = user_input.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            recovery_cooldown = user_input.get(
                CONF_RECOVERY_COOLDOWN, DEFAULT_RECOVERY_COOLDOWN
            )
            invert_temp = user_input.get(CONF_INVERT_LIGHT_TEMPERATURE, False)
            expose_text = user_input.get(CONF_EXPOSE_SETTABLE_TEXT, DEFAULT_EXPOSE_SETTABLE_TEXT)
            expose_readonly_strings = user_input.get(
                CONF_EXPOSE_READONLY_STRINGS, DEFAULT_EXPOSE_READONLY_STRINGS
            )
            existing_use_titles = self.config_entry.options.get(
                CONF_USE_CAPABILITY_TITLES,
                self.config_entry.data.get(CONF_USE_CAPABILITY_TITLES),
            )
            use_titles = user_input.get(
                CONF_USE_CAPABILITY_TITLES,
                existing_use_titles
                if existing_use_titles is not None
                else DEFAULT_USE_CAPABILITY_TITLES,
            )

            if not host.startswith(("http://", "https://")):
                host = f"http://{host}"

            new_data = {
                **self.config_entry.data,
                CONF_HOST: host,
                CONF_INVERT_LIGHT_TEMPERATURE: invert_temp,
                CONF_EXPOSE_SETTABLE_TEXT: expose_text,
                CONF_EXPOSE_READONLY_STRINGS: expose_readonly_strings,
            }
            if existing_use_titles is not None or use_titles:
                new_data[CONF_USE_CAPABILITY_TITLES] = use_titles
            if token:
                new_data[CONF_TOKEN] = token

            new_options = {
                **self.config_entry.options,
                CONF_POLL_INTERVAL: poll_interval,
                CONF_RECOVERY_COOLDOWN: recovery_cooldown,
                CONF_INVERT_LIGHT_TEMPERATURE: invert_temp,
                CONF_EXPOSE_SETTABLE_TEXT: expose_text,
                CONF_EXPOSE_READONLY_STRINGS: expose_readonly_strings,
            }
            if existing_use_titles is not None or use_titles:
                new_options[CONF_USE_CAPABILITY_TITLES] = use_titles

            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, options=new_options
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        defaults = {
            CONF_HOST: self.config_entry.data.get(CONF_HOST, ""),
            CONF_TOKEN: "",
            CONF_POLL_INTERVAL: self.config_entry.options.get(
                CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
            ),
            CONF_RECOVERY_COOLDOWN: self.config_entry.options.get(
                CONF_RECOVERY_COOLDOWN, DEFAULT_RECOVERY_COOLDOWN
            ),
            CONF_INVERT_LIGHT_TEMPERATURE: self.config_entry.options.get(
                CONF_INVERT_LIGHT_TEMPERATURE,
                self.config_entry.data.get(CONF_INVERT_LIGHT_TEMPERATURE, DEFAULT_INVERT_LIGHT_TEMPERATURE),
            ),
            CONF_EXPOSE_SETTABLE_TEXT: self.config_entry.options.get(
                CONF_EXPOSE_SETTABLE_TEXT,
                self.config_entry.data.get(CONF_EXPOSE_SETTABLE_TEXT, DEFAULT_EXPOSE_SETTABLE_TEXT),
            ),
            CONF_EXPOSE_READONLY_STRINGS: self.config_entry.options.get(
                CONF_EXPOSE_READONLY_STRINGS,
                self.config_entry.data.get(CONF_EXPOSE_READONLY_STRINGS, DEFAULT_EXPOSE_READONLY_STRINGS),
            ),
            CONF_USE_CAPABILITY_TITLES: self.config_entry.options.get(
                CONF_USE_CAPABILITY_TITLES,
                self.config_entry.data.get(CONF_USE_CAPABILITY_TITLES, DEFAULT_USE_CAPABILITY_TITLES),
            ),
        }
        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults[CONF_HOST]): str,
                vol.Optional(CONF_TOKEN, default=defaults[CONF_TOKEN]): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=defaults[CONF_POLL_INTERVAL]
                ): vol.All(vol.Coerce(int), vol.Clamp(min=5, max=60)),
                vol.Optional(
                    CONF_RECOVERY_COOLDOWN, default=defaults[CONF_RECOVERY_COOLDOWN]
                ): vol.All(vol.Coerce(int), vol.Clamp(min=60, max=3600)),
                vol.Optional(
                    CONF_INVERT_LIGHT_TEMPERATURE,
                    default=defaults[CONF_INVERT_LIGHT_TEMPERATURE],
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_EXPOSE_SETTABLE_TEXT,
                    default=defaults[CONF_EXPOSE_SETTABLE_TEXT],
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_EXPOSE_READONLY_STRINGS,
                    default=defaults[CONF_EXPOSE_READONLY_STRINGS],
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_USE_CAPABILITY_TITLES,
                    default=defaults[CONF_USE_CAPABILITY_TITLES],
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors={}
        )

    async def async_step_device_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection step."""
        errors: dict[str, str] = {}
        
        # Store device_id to display_name mapping for parsing user input
        if not hasattr(self, "_device_id_to_display_name"):
            self._device_id_to_display_name: dict[str, str] = {}
        
        # Fetch devices and zones from Homey
        devices = {}
        zones = {}
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self.token}"},
            ) as session:
                # Try to get devices
                device_endpoints = [
                    f"{self.host}/api/manager/devices/device/",
                    f"{self.host}/api/manager/devices/device",
                    f"{self.host}/api/v1/device/",
                    f"{self.host}/api/v1/device",
                ]
                
                for device_endpoint in device_endpoints:
                    try:
                        async with session.get(device_endpoint) as response:
                            if response.status == 200:
                                devices_data = await response.json()
                                # Handle both dict and list responses
                                if isinstance(devices_data, dict):
                                    devices = devices_data
                                elif isinstance(devices_data, list):
                                    devices = {device.get("id", str(i)): device for i, device in enumerate(devices_data)}
                                break
                    except Exception as err:
                        _LOGGER.debug("Error fetching devices from %s: %s", device_endpoint, err)
                        continue
                
                # Try to get zones (rooms)
                # Note: Zones may require additional API permissions (homey.zone.readonly)
                # If zones can't be fetched, we'll proceed without room grouping
                zone_endpoints = [
                    f"{self.host}/api/manager/zones/zone/",
                    f"{self.host}/api/manager/zones/zone",
                    f"{self.host}/api/v1/zone/",
                    f"{self.host}/api/v1/zone",
                ]
                
                zones_fetched = False
                for zone_endpoint in zone_endpoints:
                    try:
                        async with session.get(zone_endpoint) as response:
                            if response.status == 200:
                                zones_data = await response.json()
                                if isinstance(zones_data, dict):
                                    zones = zones_data
                                elif isinstance(zones_data, list):
                                    zones = {zone.get("id", str(i)): zone for i, zone in enumerate(zones_data)}
                                zones_fetched = True
                                _LOGGER.debug("Successfully fetched zones from %s", zone_endpoint)
                                break
                            elif response.status == 401:
                                _LOGGER.debug("Zones endpoint requires authentication - may need homey.zone.readonly permission")
                                continue
                            elif response.status == 403:
                                _LOGGER.debug("Zones endpoint forbidden - API key may not have homey.zone.readonly permission")
                                continue
                    except Exception as err:
                        _LOGGER.debug("Error fetching zones from %s: %s", zone_endpoint, err)
                        continue
                
                if not zones_fetched:
                    _LOGGER.info("Could not fetch zones/rooms from Homey. Devices will be shown without room grouping. This may require homey.zone.readonly permission in your API key.")
                    zones = {}
        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            errors["base"] = "cannot_fetch_devices"
        
        if user_input is not None:
            # User has selected devices from multi-select
            selected_device_ids = user_input.get(CONF_DEVICE_FILTER, [])
            
            # If no devices selected, import all (None means import all)
            if not selected_device_ids:
                selected_device_ids = None
            
            # Get Homey name for entry title
            name = "Homey"
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={"Authorization": f"Bearer {self.token}"},
                ) as session:
                    for endpoint in ["/api/manager/system/info", "/api/v1/system"]:
                        try:
                            async with session.get(f"{self.host}{endpoint}") as response:
                                if response.status == 200:
                                    data = await response.json()
                                    name = data.get("name") or data.get("homeyName") or "Homey"
                                    break
                        except:
                            continue
            except:
                pass
            
            return self.async_create_entry(
                title=name,
                data={
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    "working_endpoint": self.working_endpoint,
                    CONF_DEVICE_FILTER: selected_device_ids,  # None means import all
                },
            )
        
        if not devices:
            # No devices found or error - proceed without selection
            _LOGGER.warning("No devices found or error fetching devices, proceeding with all devices")
            return self.async_create_entry(
                title="Homey",
                data={
                    CONF_HOST: self.host,
                    CONF_TOKEN: self.token,
                    "working_endpoint": self.working_endpoint,
                    CONF_DEVICE_FILTER: None,  # Import all
                },
            )
        
        # Group devices by room/zone and type for better organization
        devices_by_room_and_type: dict[str, dict[str, list[tuple[str, dict[str, Any], str]]]] = {}
        devices_no_room_by_type: dict[str, list[tuple[str, dict[str, Any], str]]] = {}
        
        # Device type labels for display
        type_labels = {
            "light": "Light",
            "switch": "Switch",
            "sensor": "Sensor",
            "binary_sensor": "Binary Sensor",
            "cover": "Cover",
            "climate": "Climate",
            "fan": "Fan",
            "lock": "Lock",
            "media_player": "Media Player",
            "device": "Device",
        }
        
        # Check if we have zones - if not, don't group by room
        has_zones = bool(zones)
        
        for device_id, device in devices.items():
            capabilities = device.get("capabilitiesObj", {})
            driver_uri = device.get("driverUri")
            device_class = device.get("class")
            device_type = get_device_type(capabilities, driver_uri, device_class)
            type_label = type_labels.get(device_type, "Device")
            zone_id = device.get("zone")
            
            # Only group by room if we have zones AND device has a zone
            if has_zones and zone_id and zone_id in zones:
                zone_name = zones[zone_id].get("name", "Unknown Room")
                if zone_name not in devices_by_room_and_type:
                    devices_by_room_and_type[zone_name] = {}
                if device_type not in devices_by_room_and_type[zone_name]:
                    devices_by_room_and_type[zone_name][device_type] = []
                devices_by_room_and_type[zone_name][device_type].append((device_id, device, type_label))
            else:
                # Device has no room or zones couldn't be fetched
                if device_type not in devices_no_room_by_type:
                    devices_no_room_by_type[device_type] = []
                devices_no_room_by_type[device_type].append((device_id, device, type_label))
        
        # Build device options dict for multi-select (cv.multi_select works with voluptuous_serialize)
        # Format: {device_id: "Room • Type • Device Name"}
        device_options: dict[str, str] = {}
        
        # Device type order for consistent sorting (most common first)
        type_order = ["light", "switch", "cover", "climate", "fan", "lock", "media_player", "sensor", "binary_sensor", "device"]
        
        # Build options dict grouped by room, then by type (sorted alphabetically)
        for room_name in sorted(devices_by_room_and_type.keys()):
            room_types = devices_by_room_and_type[room_name]
            # Sort types by our preferred order, then alphabetically
            sorted_types = sorted(
                room_types.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t)
            )
            
            for device_type in sorted_types:
                room_devices = sorted(
                    room_types[device_type],
                    key=lambda x: x[1].get("name", "").lower()
                )
                
                for device_id, device, type_label in room_devices:
                    device_name = device.get("name", f"Device {device_id}")
                    # Create display name with room (if available), type, and device name
                    if room_name and room_name != "Unknown Room":
                        display_name = f"{room_name} • {type_label} • {device_name}"
                    else:
                        display_name = f"{type_label} • {device_name}"
                    device_options[device_id] = display_name
        
        # Add devices without room, grouped by type
        if devices_no_room_by_type:
            sorted_no_room_types = sorted(
                devices_no_room_by_type.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t)
            )
            
            for device_type in sorted_no_room_types:
                type_label = type_labels.get(device_type, "Device")
                devices_no_room_sorted = sorted(
                    devices_no_room_by_type[device_type],
                    key=lambda x: x[1].get("name", "").lower()
                )
                
                for device_id, device, type_label_actual in devices_no_room_sorted:
                    device_name = device.get("name", f"Device {device_id}")
                    # Only show "No Room" if we successfully fetched zones but device has no room
                    if zones:
                        display_name = f"No Room • {type_label_actual} • {device_name}"
                    else:
                        display_name = f"{type_label_actual} • {device_name}"
                    device_options[device_id] = display_name
        
        # Use cv.multi_select for device selection - this works with voluptuous_serialize
        # Default to all devices selected
        default_selected = list(device_options.keys())
        
        device_schema = vol.Schema({
            vol.Optional(
                CONF_DEVICE_FILTER,
                default=default_selected
            ): cv.multi_select(device_options),
        })
        
        return self.async_show_form(
            step_id="device_selection",
            data_schema=device_schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(devices)),
                "room_count": str(len(devices_by_room_and_type)),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return HomeyOptionsFlowHandler(config_entry)


class HomeyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Homey integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        # OptionsFlow's config_entry property is set by the framework
        # We need to call super().__init__() first, but OptionsFlow doesn't take config_entry
        # Store it in a private variable and use self.config_entry property after init
        super().__init__()
        # Store config entry data in instance variables for easy access
        # Note: self.config_entry is a property set by the framework, but we need
        # to store the passed config_entry for use in our methods
        self._entry = config_entry
        self.host = config_entry.data[CONF_HOST]
        self.token = config_entry.data[CONF_TOKEN]
        self.working_endpoint = config_entry.data.get("working_endpoint")
        self._device_id_to_display_name: dict[str, str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "settings": "Connection & Polling",
                "device_management": "Manage Devices",
            },
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle connection and polling settings."""
        host_label = "Homey IP Address or Hostname"
        token_label = "API Key (leave blank to keep current)"
        poll_label = "Fallback polling interval (seconds)"
        recovery_label = "Recovery cooldown (seconds, between auto-recovery attempts)"
        invert_temp_label = "Invert normalized light temperature (fixes warm/cold reversal)"
        expose_text_label = "Expose string capabilities as editable text inputs (exclusive)"
        expose_readonly_strings_label = "Expose string capabilities as read-only sensors (default)"
        use_titles_label = "Use Homey capability titles for entity names"
        if user_input is not None:
            def _get(label_key: str, config_key: str, default: Any) -> Any:
                if label_key in user_input:
                    return user_input.get(label_key, default)
                return user_input.get(config_key, default)

            host = _get(host_label, CONF_HOST, "").strip().rstrip("/")
            token = str(_get(token_label, CONF_TOKEN, "")).strip()
            poll_interval = _get(poll_label, CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
            recovery_cooldown = _get(
                recovery_label, CONF_RECOVERY_COOLDOWN, DEFAULT_RECOVERY_COOLDOWN
            )
            invert_temp = _get(invert_temp_label, CONF_INVERT_LIGHT_TEMPERATURE, False)
            expose_text = _get(
                expose_text_label, CONF_EXPOSE_SETTABLE_TEXT, DEFAULT_EXPOSE_SETTABLE_TEXT
            )
            expose_readonly_strings = user_input.get(
                expose_readonly_strings_label, DEFAULT_EXPOSE_READONLY_STRINGS
            )
            expose_readonly_strings = _get(
                expose_readonly_strings_label,
                CONF_EXPOSE_READONLY_STRINGS,
                expose_readonly_strings,
            )
            existing_use_titles = self._entry.options.get(
                CONF_USE_CAPABILITY_TITLES,
                self._entry.data.get(CONF_USE_CAPABILITY_TITLES),
            )
            use_titles = _get(
                use_titles_label,
                CONF_USE_CAPABILITY_TITLES,
                existing_use_titles
                if existing_use_titles is not None
                else DEFAULT_USE_CAPABILITY_TITLES,
            )
            if expose_text:
                # Prevent duplicates: editable text inputs take priority.
                expose_readonly_strings = False

            if not host.startswith(("http://", "https://")):
                host = f"http://{host}"

            new_data = {
                **self._entry.data,
                CONF_HOST: host,
                CONF_INVERT_LIGHT_TEMPERATURE: invert_temp,
                CONF_EXPOSE_SETTABLE_TEXT: expose_text,
                CONF_EXPOSE_READONLY_STRINGS: expose_readonly_strings,
            }
            if existing_use_titles is not None or use_titles:
                new_data[CONF_USE_CAPABILITY_TITLES] = use_titles
            if token:
                new_data[CONF_TOKEN] = token

            new_options = {
                **self._entry.options,
                CONF_POLL_INTERVAL: poll_interval,
                CONF_RECOVERY_COOLDOWN: recovery_cooldown,
                CONF_INVERT_LIGHT_TEMPERATURE: invert_temp,
                CONF_EXPOSE_SETTABLE_TEXT: expose_text,
                CONF_EXPOSE_READONLY_STRINGS: expose_readonly_strings,
            }
            if existing_use_titles is not None or use_titles:
                new_options[CONF_USE_CAPABILITY_TITLES] = use_titles

            self.hass.config_entries.async_update_entry(
                self._entry, data=new_data, options=new_options
            )
            await self.hass.config_entries.async_reload(self._entry.entry_id)
            return self.async_create_entry(title="", data={})

        defaults = {
            host_label: self._entry.data.get(CONF_HOST, ""),
            token_label: "",
            poll_label: self._entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
            recovery_label: self._entry.options.get(
                CONF_RECOVERY_COOLDOWN, DEFAULT_RECOVERY_COOLDOWN
            ),
            invert_temp_label: self._entry.options.get(
                CONF_INVERT_LIGHT_TEMPERATURE,
                self._entry.data.get(CONF_INVERT_LIGHT_TEMPERATURE, DEFAULT_INVERT_LIGHT_TEMPERATURE),
            ),
            expose_text_label: self._entry.options.get(
                CONF_EXPOSE_SETTABLE_TEXT,
                self._entry.data.get(CONF_EXPOSE_SETTABLE_TEXT, DEFAULT_EXPOSE_SETTABLE_TEXT),
            ),
            expose_readonly_strings_label: self._entry.options.get(
                CONF_EXPOSE_READONLY_STRINGS,
                self._entry.data.get(CONF_EXPOSE_READONLY_STRINGS, DEFAULT_EXPOSE_READONLY_STRINGS),
            ),
            use_titles_label: self._entry.options.get(
                CONF_USE_CAPABILITY_TITLES,
                self._entry.data.get(CONF_USE_CAPABILITY_TITLES, DEFAULT_USE_CAPABILITY_TITLES),
            ),
        }
        if defaults[expose_text_label]:
            defaults[expose_readonly_strings_label] = False
        options_schema = vol.Schema(
            {
                vol.Required(host_label, default=defaults[host_label]): str,
                vol.Optional(token_label, default=defaults[token_label]): str,
                vol.Required(poll_label, default=defaults[poll_label]): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=60, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    recovery_label, default=defaults[recovery_label]
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60, max=3600, step=30, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    invert_temp_label, default=defaults[invert_temp_label]
                ): selector.BooleanSelector(),
                vol.Optional(
                    expose_text_label, default=defaults[expose_text_label]
                ): selector.BooleanSelector(),
                vol.Optional(
                    expose_readonly_strings_label,
                    default=defaults[expose_readonly_strings_label],
                ): selector.BooleanSelector(),
                vol.Optional(
                    use_titles_label,
                    default=defaults[use_titles_label],
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="settings", data_schema=options_schema, errors={}
        )

    async def async_step_device_management(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device management step."""
        errors: dict[str, str] = {}
        device_filter_label = "Devices"
        
        # Get currently selected devices from config entry
        current_selected = self._entry.data.get(CONF_DEVICE_FILTER)
        if current_selected is None:
            # None means all devices are selected
            current_selected_set: set[str] = set()
        else:
            current_selected_set = set(current_selected)
        
        # Fetch devices and zones from Homey
        devices = {}
        zones = {}
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self.token}"},
            ) as session:
                # Try to get devices
                device_endpoints = [
                    f"{self.host}/api/manager/devices/device/",
                    f"{self.host}/api/manager/devices/device",
                    f"{self.host}/api/v1/device/",
                    f"{self.host}/api/v1/device",
                ]
                
                for device_endpoint in device_endpoints:
                    try:
                        async with session.get(device_endpoint) as response:
                            if response.status == 200:
                                devices_data = await response.json()
                                # Handle both dict and list responses
                                if isinstance(devices_data, dict):
                                    devices = devices_data
                                elif isinstance(devices_data, list):
                                    devices = {device.get("id", str(i)): device for i, device in enumerate(devices_data)}
                                break
                    except Exception as err:
                        _LOGGER.debug("Error fetching devices from %s: %s", device_endpoint, err)
                        continue
                
                # Try to get zones (rooms)
                # Note: Zones may require additional API permissions (homey.zone.readonly)
                # If zones can't be fetched, we'll proceed without room grouping
                zone_endpoints = [
                    f"{self.host}/api/manager/zones/zone/",
                    f"{self.host}/api/manager/zones/zone",
                    f"{self.host}/api/v1/zone/",
                    f"{self.host}/api/v1/zone",
                ]
                
                zones_fetched = False
                for zone_endpoint in zone_endpoints:
                    try:
                        async with session.get(zone_endpoint) as response:
                            if response.status == 200:
                                zones_data = await response.json()
                                if isinstance(zones_data, dict):
                                    zones = zones_data
                                elif isinstance(zones_data, list):
                                    zones = {zone.get("id", str(i)): zone for i, zone in enumerate(zones_data)}
                                zones_fetched = True
                                _LOGGER.debug("Successfully fetched zones from %s", zone_endpoint)
                                break
                            elif response.status == 401:
                                _LOGGER.debug("Zones endpoint requires authentication - may need homey.zone.readonly permission")
                                continue
                            elif response.status == 403:
                                _LOGGER.debug("Zones endpoint forbidden - API key may not have homey.zone.readonly permission")
                                continue
                    except Exception as err:
                        _LOGGER.debug("Error fetching zones from %s: %s", zone_endpoint, err)
                        continue
                
                if not zones_fetched:
                    _LOGGER.info("Could not fetch zones/rooms from Homey. Devices will be shown without room grouping. This may require homey.zone.readonly permission in your API key.")
                    zones = {}
        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            errors["base"] = "cannot_fetch_devices"
        
        if user_input is not None:
            # User has selected devices from multi-select
            selected_device_ids = user_input.get(device_filter_label, [])
            
            # If no devices selected, import all (None means import all)
            if not selected_device_ids:
                selected_device_ids = None
            
            # Update config entry with new device selection
            new_data = {**self._entry.data}
            new_data[CONF_DEVICE_FILTER] = selected_device_ids
            
            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self._entry,
                data=new_data,
            )
            
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self._entry.entry_id)
            
            return self.async_create_entry(title="", data={})
        
        if not devices:
            # No devices found or error - show error
            errors["base"] = "cannot_fetch_devices"
            return self.async_show_form(
                step_id="device_management",
                errors=errors,
            )
        
        # Group devices by room/zone and type for better organization
        devices_by_room_and_type: dict[str, dict[str, list[tuple[str, dict[str, Any], str]]]] = {}
        devices_no_room_by_type: dict[str, list[tuple[str, dict[str, Any], str]]] = {}
        
        # Device type labels for display
        type_labels = {
            "light": "Light",
            "switch": "Switch",
            "sensor": "Sensor",
            "binary_sensor": "Binary Sensor",
            "cover": "Cover",
            "climate": "Climate",
            "fan": "Fan",
            "lock": "Lock",
            "media_player": "Media Player",
            "device": "Device",
        }
        
        # Check if we have zones - if not, don't group by room
        has_zones = bool(zones)
        
        for device_id, device in devices.items():
            capabilities = device.get("capabilitiesObj", {})
            driver_uri = device.get("driverUri")
            device_class = device.get("class")
            device_type = get_device_type(capabilities, driver_uri, device_class)
            type_label = type_labels.get(device_type, "Device")
            zone_id = device.get("zone")
            
            # Only group by room if we have zones AND device has a zone
            if has_zones and zone_id and zone_id in zones:
                zone_name = zones[zone_id].get("name", "Unknown Room")
                if zone_name not in devices_by_room_and_type:
                    devices_by_room_and_type[zone_name] = {}
                if device_type not in devices_by_room_and_type[zone_name]:
                    devices_by_room_and_type[zone_name][device_type] = []
                devices_by_room_and_type[zone_name][device_type].append((device_id, device, type_label))
            else:
                # Device has no room or zones couldn't be fetched
                if device_type not in devices_no_room_by_type:
                    devices_no_room_by_type[device_type] = []
                devices_no_room_by_type[device_type].append((device_id, device, type_label))
        
        # Build device options dict for multi-select (cv.multi_select works with voluptuous_serialize)
        # Format: {device_id: "Room • Type • Device Name"}
        device_options: dict[str, str] = {}
        
        # Device type order for consistent sorting (most common first)
        type_order = ["light", "switch", "cover", "climate", "fan", "lock", "media_player", "sensor", "binary_sensor", "device"]
        
        # Build options dict grouped by room, then by type (sorted alphabetically)
        for room_name in sorted(devices_by_room_and_type.keys()):
            room_types = devices_by_room_and_type[room_name]
            # Sort types by our preferred order, then alphabetically
            sorted_types = sorted(
                room_types.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t)
            )
            
            for device_type in sorted_types:
                room_devices = sorted(
                    room_types[device_type],
                    key=lambda x: x[1].get("name", "").lower()
                )
                
                for device_id, device, type_label in room_devices:
                    device_name = device.get("name", f"Device {device_id}")
                    # Create display name with room (if available), type, and device name
                    if room_name and room_name != "Unknown Room":
                        display_name = f"{room_name} • {type_label} • {device_name}"
                    else:
                        display_name = f"{type_label} • {device_name}"
                    device_options[device_id] = display_name
        
        # Add devices without room, grouped by type
        if devices_no_room_by_type:
            sorted_no_room_types = sorted(
                devices_no_room_by_type.keys(),
                key=lambda t: (type_order.index(t) if t in type_order else 999, t)
            )
            
            for device_type in sorted_no_room_types:
                type_label = type_labels.get(device_type, "Device")
                devices_no_room_sorted = sorted(
                    devices_no_room_by_type[device_type],
                    key=lambda x: x[1].get("name", "").lower()
                )
                
                for device_id, device, type_label_actual in devices_no_room_sorted:
                    device_name = device.get("name", f"Device {device_id}")
                    # Only show "No Room" if we successfully fetched zones but device has no room
                    if zones:
                        display_name = f"No Room • {type_label_actual} • {device_name}"
                    else:
                        display_name = f"{type_label_actual} • {device_name}"
                    device_options[device_id] = display_name
        
        # Determine default selection based on current config
        if current_selected is None:
            # All devices selected by default
            default_selected = list(device_options.keys())
        else:
            # Only currently selected devices
            default_selected = [did for did in current_selected if did in device_options]
        
        # Use cv.multi_select for device selection - this works with voluptuous_serialize
        device_schema = vol.Schema(
            {
                vol.Optional(
                    device_filter_label,
                    default=default_selected,
                ): cv.multi_select(device_options),
            }
        )
        
        return self.async_show_form(
            step_id="device_management",
            data_schema=device_schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(devices)),
                "room_count": str(len(devices_by_room_and_type)),
            },
        )

