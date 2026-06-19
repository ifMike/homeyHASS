from __future__ import annotations

import ast
import json
import re
from pathlib import Path

def _load_services_yaml_keys(path: Path) -> set[str]:
    """Parse top-level service keys from services.yaml without PyYAML."""
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(" ") and not line.startswith("\t") and line.endswith(":"):
            keys.add(line[:-1].strip())
    return keys


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "homey_hass"
MANIFEST_PATH = INTEGRATION_DIR / "manifest.json"
SERVICES_PATH = INTEGRATION_DIR / "services.yaml"
INIT_PATH = INTEGRATION_DIR / "__init__.py"
CONST_PATH = INTEGRATION_DIR / "const.py"

# Homey API permissions, Socket.IO URIs, hostnames, driver IDs — not HA integration domain.
ALLOWED_HOMEY_SUBSTRINGS = (
    "homey.device.",
    "homey.flow.",
    "homey.zone.",
    "homey.mood.",
    "homey.logic",
    "homey.system.",
    "homey.local",
    "homey:app:",
    "homey:manager:",
    "homey:device:",
    "homeyId",
    "homey_id",
    "homeyName",
    "homeyName",
    "multi_homey",
    "homey_api",
    "HomeyAPI",
    "homey5q",
    "homey6q",
    "homey7q",
    "homey1",
    "homey2",
    "homey3",
    "homey4",
    "homey7",
    "_homey._tcp",
    "apps.developer.homey.app",
    "developer.homey.app",
    "from Homey",
    "to Homey",
    "Homey ",
    "Homey.",
    "Homey,",
    "Homey\n",
    "Homey Pro",
    "Homey app",
    "Homey hub",
    "Homey ID",
    "Homey device",
    "Homey flow",
    "Homey integration",
    "Homey metadata",
    "Homey capability",
    "Homey Settings",
    "Homey broadcasts",
    "Homey IPv4",
    "Homey IP",
    "Homey connection",
    "Homey-scoped",
    "Homey config",
    "Homey entities",
    "Homey event",
    "Homey EVENT",
    "Homey models",
    "Homey name",
    "Homey permissions",
    "Homey variable",
    "Homey mood",
    "Homey scene",
    "Homey flows",
    "Homey host",
    "Homey firmware",
    "Homey update",
    "Homey installation",
    "Homey Data",
    "Homey Logic",
    "Homey Energy",
    "Homey API",
    "Homey Socket",
    "Homey real-time",
    "Homey real time",
    '"automatic", "homey"',
    "automatic', 'homey'",
    "multi-homey",
    "The Homey",
    "a Homey",
    "your Homey",
    "the Homey",
    "on Homey",
    "in Homey",
    "via Homey",
    "with Homey",
    "for Homey",
    "and Homey",
    "or Homey",
    "all Homey",
    "each Homey",
    "other Homey",
    "old Homey",
    "new Homey",
    "single Homey",
    "duplicate Homey",
    "Migrating Homey",
    "Rescoping Homey",
    "Disabled Homey",
    "Failed Homey",
    "Trigger Homey",
    "Activate Homey",
    "Subscribe Homey",
    "Connect Homey",
    "Configure Homey",
    "Reload Homey",
    "Remove Homey",
    "Update Homey",
    "Enable Homey",
    "Disable Homey",
    "Import Homey",
    "Fetch Homey",
    "Check Homey",
    "Verify Homey",
    "Target Homey",
    "Sample Homey",
    "Unknown Homey",
    "Pending Homey",
    "Resolved Homey",
    "Detected Homey",
    "Discovered Homey",
    "Supported Homey",
    "Unsupported Homey",
    "Invalid Homey",
    "Missing Homey",
    "Extract Homey",
    "Handle Homey",
    "Setup Homey",
    "Load Homey",
    "Parse Homey",
    "Build Homey",
    "Get Homey",
    "Set Homey",
    "Use Homey",
    "Read Homey",
    "Write Homey",
    "Call Homey",
    "Run Homey",
    "Start Homey",
    "Stop Homey",
    "Turn Homey",
    "Show Homey",
    "List Homey",
    "Find Homey",
    "Create Homey",
    "Delete Homey",
    "Clean Homey",
    "Skip Homey",
    "Warn Homey",
    "Log Homey",
    "Debug Homey",
    "Info Homey",
    "Error Homey",
    "Warning Homey",
    "homey_hass",
    "HomeyConfigFlow",
    "HomeyDataUpdateCoordinator",
    "HomeyLogicUpdateCoordinator",
    "HomeyLock",
    "HomeyFan",
    "HomeyLight",
    "HomeyCover",
    "HomeyClimate",
    "HomeySwitch",
    "HomeySensor",
    "HomeyBinarySensor",
    "HomeyButton",
    "HomeyFlowButton",
    "HomeyDeviceButton",
    "HomeyScene",
    "HomeyVacuum",
    "HomeyMediaPlayer",
    "HomeyNumber",
    "HomeySelect",
    "HomeyText",
    "Homey (",
    "Homey)",
    "Homey:",
    "Homey→",
    "Homey—",
    "Homey–",
    "Homey'",
    'Homey"',
    "Homey*",
    "Homey/",
    "Homey\\",
    "Homey+",
    "Homey-",
    "Homey_",
    "Homey\n\n",
    "Homey\n",
    "Homey**",
    "Homey`",
    "Homey (IP",
    "Homey (domain",
    "domain). Now",
    "homey_{flow_id}",
    "homey_{device_id}",
    "RonnyWinkler/homeassistant.homey",
    "ifMike/homeyHASS",
    "github.com/ifMike/homeyHASS",
)

STALE_DOMAIN_PATTERNS = (
    re.compile(r'["\']homey["\']'),  # quoted integration domain
    re.compile(r"custom_components/homey(?!_hass)"),
    re.compile(r"custom_components\.homey(?!_hass)"),
    re.compile(r"\bhomey\.(trigger_flow|enable_flow|disable_flow|set_device_temperature_unit|test_capability_report|rename_entities_to_titles)\b"),
    re.compile(r'UNIQUE_ID_PREFIX\s*=\s*["\']homey_'),
    re.compile(r'DOMAIN\s*=\s*["\']homey["\']'),
)


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_const_domain() -> tuple[str, str]:
    tree = ast.parse(CONST_PATH.read_text(encoding="utf-8"))
    domain = None
    prefix = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    if target.id == "DOMAIN":
                        domain = node.value.value
                    if target.id == "UNIQUE_ID_PREFIX":
                        prefix = node.value.value
    assert domain is not None
    assert prefix is not None
    return domain, prefix


def test_integration_folder_matches_manifest_domain() -> None:
    manifest = _load_manifest()
    assert manifest["domain"] == INTEGRATION_DIR.name == "homey_hass"


def test_display_name_unchanged() -> None:
    manifest = _load_manifest()
    assert manifest["name"] == "Homey"


def test_const_domain_and_unique_id_prefix() -> None:
    domain, prefix = _load_const_domain()
    manifest = _load_manifest()
    assert domain == manifest["domain"] == "homey_hass"
    assert prefix == f"{domain}_"


def test_old_integration_folder_is_gone() -> None:
    old_dir = ROOT / "custom_components" / "homey"
    assert not old_dir.exists(), "Old custom_components/homey folder must be removed"


def test_services_yaml_matches_registered_services() -> None:
    yaml_services = _load_services_yaml_keys(SERVICES_PATH)
    init_source = INIT_PATH.read_text(encoding="utf-8")
    # Services declared in services.yaml must be registered under DOMAIN in __init__.py
    for service in yaml_services:
        assert (
            f'"{service}"' in init_source
            or f"'{service}'" in init_source
            or f"SERVICE_{service.upper()}" in init_source
            or f"async_register(\n            DOMAIN,\n            \"{service}\"" in init_source
            or f'async_register(DOMAIN, "{service}"' in init_source
        ), f"Service {service!r} in services.yaml is not registered in __init__.py"

    # Flow services are registered inline (not in services.yaml)
    for flow_service in ("trigger_flow", "enable_flow", "disable_flow"):
        assert f'"{flow_service}"' in init_source


def test_config_flow_uses_domain() -> None:
    source = (INTEGRATION_DIR / "config_flow.py").read_text(encoding="utf-8")
    assert "domain=DOMAIN" in source
    assert 'class HomeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN)' in source


def test_no_stale_integration_domain_references_in_python() -> None:
    violations: list[str] = []
    for path in sorted(INTEGRATION_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        for pattern in STALE_DOMAIN_PATTERNS:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 40)
                end = min(len(text), match.end() + 40)
                snippet = text[start:end].replace("\n", " ")
                if any(allowed in snippet for allowed in ALLOWED_HOMEY_SUBSTRINGS):
                    continue
                violations.append(f"{rel}: {match.group()!r} in ...{snippet}...")
    assert not violations, "Stale homey domain references:\n" + "\n".join(violations)


def test_const_module_loads() -> None:
    """Smoke-test const.py loads and exposes expected domain constants."""
    import importlib.util

    path = CONST_PATH
    spec = importlib.util.spec_from_file_location("homey_hass_const_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DOMAIN == "homey_hass"
    assert module.UNIQUE_ID_PREFIX == "homey_hass_"
