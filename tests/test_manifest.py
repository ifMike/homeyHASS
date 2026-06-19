from __future__ import annotations

import json
from pathlib import Path


def test_manifest_has_required_fields() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey_hass"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = ["domain", "name", "version", "documentation", "issue_tracker"]
    missing = [key for key in required if not manifest.get(key)]
    assert not missing, f"Missing required manifest fields: {missing}"


def test_manifest_domain_is_homey_hass() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey_hass"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("domain") == "homey_hass"
    assert manifest.get("name") == "Homey"


def test_manifest_version_is_2_0_0() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey_hass"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("version") == "2.0.0"

