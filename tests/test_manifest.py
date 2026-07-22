from __future__ import annotations

import json
from pathlib import Path


def test_manifest_has_required_fields() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = ["domain", "name", "version", "documentation", "issue_tracker"]
    missing = [key for key in required if not manifest.get(key)]
    assert not missing, f"Missing required manifest fields: {missing}"


def test_manifest_domain_is_homey() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("domain") == "homey"


def test_manifest_version_is_current() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "homey"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("version") == "1.2.8"
