## Version 1.2.8

**Current release** for the legacy **1.x line** (domain `homey`, folder `custom_components/homey/`). Install from **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** in HACS — this repository publishes **only 1.2.x updates** (no 2.x notifications).

### Who should use this repository

- You have a **working 1.x setup** (domain `homey`) and want bug fixes without migrating to 2.x.
- You previously used `ifMike/homeyHASS` in HACS and want to **stop 2.x update notifications**.

### Who should not use this repository

- **New users** — install from [`ifMike/homeyHASS`](https://github.com/ifMike/homeyHASS) (**2.0.1**, domain `homey_hass`) instead.
- Users already on **2.0.x** — stay on the main repository.

---

## What's New in 1.2.8

### Documentation
- Full HACS instructions for this dedicated legacy repository, including switching from the main `ifMike/homeyHASS` repo without losing your config entry.

### Included from 1.2.7

- **Fibaro dim-based roller shutters** → `cover.*` entities
- **Dyson fan** `oscillate`, `less_air`, `more_air`
- **Discovery hostname resolution** fix
- Integration brand icon

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS-legacy/blob/main/CHANGELOG.md).

---

## HACS installation

1. **HACS** → **Integrations** → three dots → **Custom repositories**
2. Remove `https://github.com/ifMike/homeyHASS` if present
3. Add `https://github.com/ifMike/homeyHASS-legacy` (Category: Integration)
4. Search **Homey** → **Download** (or **Redownload** → **v1.2.8** when switching)
5. Restart Home Assistant

**Permissions** (unchanged): Homey API key with Local API access — `homey.device.readonly`, `homey.device.control`, and `homey.system.readonly` (recommended for real-time updates).

Issues: [ifMike/homeyHASS/issues](https://github.com/ifMike/homeyHASS/issues) (shared with the main project).
