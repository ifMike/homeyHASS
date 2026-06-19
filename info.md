# Homey Integration for Home Assistant

---

## ⚠️ BREAKING CHANGE — Version 2.0.0 — Read before updating

**This release is a major breaking change. It is required for inclusion in the official HACS default repository, but it does not upgrade automatically from previous versions.**

### Do NOT update to 2.0.0 if your current installation is working

If you are on **version 1.x** (domain `homey`, folder `custom_components/homey/`) and everything works today:

- **Stay on 1.2.6** (or your current 1.x version) until you are ready to migrate manually.
- **Do not click Update** in HACS unless you have read this entire notice and planned time for migration.
- There is **no in-place upgrade**. Updating without following the steps below will **break** your integration.

### Why this change is happening

The integration domain was renamed from `homey` to `homey_hass` because the domain `homey` conflicts with another integration already in the HACS default catalog: [RonnyWinkler/homeassistant.homey](https://github.com/RonnyWinkler/homeassistant.homey). HACS requires a unique domain before this integration can be listed in the official default repository.

The **display name in Home Assistant remains "Homey"**. Only the technical domain, install folder, and service names change.

### What breaks when you update without migrating

| Item | Result |
|------|--------|
| Existing config entry (domain `homey`) | Stops loading — integration shows as failed/orphaned |
| All entities | Become **unavailable** |
| Automations using `homey.*` services | **Stop working** (services are now `homey_hass.*`) |
| Dashboards | May show unavailable entities |
| Entity history | May not carry over if entity IDs change after re-setup |
| Old install folder `custom_components/homey/` | Must be removed manually |

### Who should update to 2.0.0

- **New users** installing for the first time — use 2.0.0.
- **Existing users** who want official HACS default listing support and are ready to migrate manually.
- **Existing users with a working 1.x install** — only update when you have time to migrate; otherwise **stay on 1.x**.

### Migration steps (existing 1.x users — follow in order)

**Before you start:** Create a **Home Assistant backup**. Have your Homey **IP/hostname** and **API key** ready.

1. **Do not update yet** — read all steps first.
2. In Home Assistant: **Settings → Devices & services → Homey** → delete the **old** config entry (domain `homey`). This removes entities tied to the old integration.
3. Update via HACS to **2.0.0** (or download the release manually).
4. Remove the old folder: delete `custom_components/homey/` from your config directory if it still exists.
5. Confirm the new folder exists: `custom_components/homey_hass/`
6. **Restart Home Assistant**
7. **Settings → Devices & services → Add Integration** → search **Homey** → set up again with your API key and host.
8. Re-select devices to import if prompted.
9. Update **automations, scripts, and dashboards**:
   - Replace service calls: `homey.trigger_flow` → `homey_hass.trigger_flow`, `homey.enable_flow` → `homey_hass.enable_flow`, `homey.disable_flow` → `homey_hass.disable_flow`, `homey.set_device_temperature_unit` → `homey_hass.set_device_temperature_unit`, etc.
   - Fix any entity IDs that changed (check **Settings → Devices & services → Entities**).
10. Remove orphaned unavailable entities if any remain after migration.

### New installs (2.0.0)

1. Install via HACS (or copy `custom_components/homey_hass/` manually).
2. Restart Home Assistant.
3. **Settings → Devices & services → Add Integration** → search **Homey**.

---

## What's New in 2.0.0

### Breaking changes
- **Integration domain** renamed from `homey` to `homey_hass` (display name remains **Homey**). Required for official HACS default repository approval. See migration steps above.

### Included from 1.2.x
- Device temperature unit override (Configure → Device temperature units, or `homey_hass.set_device_temperature_unit`).
- Temperature unit handling from Homey metadata; display follows your HA region (**Settings → System → Home information**).
- Capability alert fixes and thermostat temperature display fixes.

For the full list of changes, see the [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
