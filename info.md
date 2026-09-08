## Version 1.2.9

**Current release** for the legacy **1.x line** (domain `homey`, folder `custom_components/homey/`). Install from **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** in HACS — this repository publishes **only 1.2.x updates** (no 2.x notifications).

### Who should use this repository

- You have a **working 1.x setup** (domain `homey`) and want bug fixes without migrating to 2.x.
- You previously used `ifMike/homeyHASS` in HACS and want to **stop 2.x update notifications**.

### Who should not use this repository

- **New users** — install from [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) (**2.1.1+**, domain `homey_hass`) instead.
- Users already on **2.0.x / 2.1.x** — stay on the main repository.

---

## What's New in 1.2.9

### Fixed
- **Vacuum platform on Home Assistant 2026.9**: `VacuumEntityFeature.BATTERY` was removed in Core 2026.9 and caused the entire vacuum platform to fail setup (all vacuum entities disappeared). Battery remains available via the existing `measure_battery` sensor. (Same fix as main [#33](https://github.com/ifMike/homeyHASS/issues/33) / v2.1.1)

### Upgrading

1. Update via HACS (**homeyHASS-legacy**) or download **v1.2.9**
2. Restart Home Assistant

No config migration required for 1.2.8 → 1.2.9.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS-legacy/blob/main/CHANGELOG.md).

---

## HACS installation

1. **HACS** → **Integrations** → three dots → **Custom repositories**
2. Remove `https://github.com/ifMike/homeyHASS` if present
3. Add `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. Search **Homey** → **Download** (or **Redownload** → **v1.2.9** when switching)
5. Restart Home Assistant

**Permissions** (unchanged): Homey API key with Local API access — `homey.device.readonly`, `homey.device.control`, and `homey.system.readonly` (recommended for real-time updates).

Issues: [ifMike/homeyHASS/issues](https://github.com/ifMike/homeyHASS/issues) (shared with the main project).

Ready to migrate to 2.x? See the [migration guide](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x) on the main repository.
