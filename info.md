# Homey Integration for Home Assistant

---

## Version 2.1.0

**Current stable release** for the `homey_hass` integration (folder `custom_components/homey_hass/`, services `homey_hass.*`).

**Available in the official HACS default catalog** — search for **Homey** in HACS → Integrations (listed as **Homey 2.x** while legacy 1.x may still be installed on some systems).

---

## New installation?

Install normally: **Add integration → Homey 2.x** and enter your Homey host and API key. **No migration steps apply.** (The **2.x** name distinguishes this from legacy 1.x on systems where both folders exist.)

---

## Upgrading from 1.x?

Version 2.1.0 adds a **guided migration assistant**. Full step-by-step instructions: [Migrating from 1.x to 2.x](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x).

**Quick summary:**

1. Create a Home Assistant **backup**
2. Update to **2.1.0** — keep your existing **Homey 1.x** entry until migration finishes
3. Restart Home Assistant
4. **Settings → Devices & services → Add integration → Homey 2.x**
   - While both 1.x and 2.x are installed you may see two **Homey** entries — pick **Homey 2.x** (not plain **Homey**, which is 1.x)
5. Choose **Migrate from Homey 1.x** (recommended)
6. After migration: delete `custom_components/homey/`, restart. **If** any automations or scripts call `homey.*` services (e.g. `homey.trigger_flow`), update them to `homey_hass.*` — entity-based automations usually need no changes if entity IDs were preserved.

Migration screens appear **only** when Homey 1.x is still configured. After migration, setup is the same as a normal install.

---

## Staying on 1.x?

If you have a **working 1.x installation** and do **not** want to migrate yet:

- Use HACS repository **[`ifMike/homeyHASS-legacy`](https://github.com/ifMike/homeyHASS-legacy)** — it publishes **only 1.2.x updates**
- Do **not** install 2.x from this repository until you follow the [migration guide](https://github.com/ifMike/homeyHASS#migrating-from-1x-to-2x)

---

## What's New in 2.1.0

### Added
- **Guided 1.x → 2.x migration assistant** — preserves entity IDs, restores device areas, optionally removes the old integration
- **Options flow migration** — **Configure → Migrate from Homey 1.x** if you added 2.x before migrating
- **Startup reminder** — shown only when 1.x is configured, 2.x is installed, and you have not added a 2.x entry yet

### Fixed
- **Device registry compatibility** with newer Home Assistant versions (`config_entries` vs legacy `config_entry_id`)
- **Migration resilience** — migration errors no longer block the integration from loading
- **Discovery deduplication** — prevents multiple identical Homey discovery cards
- **Config flow UI** — reliable migration form labels in custom integrations

### Permissions

Unchanged from 2.0.x. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

## Upgrading from 2.0.x

1. Update via HACS or download **v2.1.0** from [Releases](https://github.com/ifMike/homeyHASS/releases)
2. Restart Home Assistant

No migration steps required between 2.0.x and 2.1.0 unless you are still on 1.x.

For the full changelog, see [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
