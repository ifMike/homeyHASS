## What's New in 2.1.5

### Fixed
- **Matter / Aqara lock modes reported as unknown (#38, #39)**: `lock_mode` (for example on Aqara Smart Lock U200 Lite via Matter) is mapped to a select entity. Enum capabilities that already become select entities are treated as supported, so the new-capability notifier no longer opens duplicate issues for working lock modes.
- **Matter AC fan/swing stealing climate HVAC control (#40)**: Climate Series / Matter air-conditioning accessories expose `fan_mode` and `swing_mode` next to `thermostat_mode`. Those enums are no longer used as custom HVAC modes, so heat/cool stays on `thermostat_mode`. Fan and swing remain available as select (or climate fan/swing) where mapped.

### Changed
- **Home Assistant 2026.11 readiness**: Climate uses `native_*` temperature properties when the running Core supports them (older HA keeps the previous API). Lights opt into in-place `entity_id` renames so `async_added_to_hass` does not force remove/re-add on newer Core.
- **Hassfest**: Removed `aiohttp` from `manifest.json` requirements — it is provided by Home Assistant Core and must not be listed for custom integrations.

### Thanks

Thanks to [@Fredrik1980](https://github.com/Fredrik1980) for reporting Matter/Aqara `lock_mode` ([#38](https://github.com/ifMike/homeyHASS/issues/38), [#39](https://github.com/ifMike/homeyHASS/issues/39)), and to [@ahversluis](https://github.com/ahversluis) for reporting Matter AC `fan_mode` / `swing_mode` / `thermostat_mode` ([#40](https://github.com/ifMike/homeyHASS/issues/40)).

### Permissions

Unchanged. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

Update via HACS (or [Releases](https://github.com/ifMike/homeyHASS/releases)), then restart Home Assistant.

Full history: [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
