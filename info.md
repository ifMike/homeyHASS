## What's New in 2.1.6

### Fixed
- **Repeated “New Homey capabilities detected” after every restart (#41)**: The set of already-seen capabilities was only kept in memory. After a Home Assistant restart or integration reload, the first poll rebuilt that baseline, so a capability that appeared a bit later in the same session was reported again — even if you had dismissed the notice before. The baseline is now stored per config entry and restored before the first check, so each capability is reported once.

### Thanks

Thanks to [@KevlarD-67](https://github.com/KevlarD-67) for the fix ([#41](https://github.com/ifMike/homeyHASS/pull/41)).

### Permissions

Unchanged. Homey API key with **Local API** access — typically:

- `homey.device.readonly` — discover and read device states
- `homey.device.control` — control devices
- `homey.system.readonly` — Socket.IO real-time updates (recommended)
- Optional: flows, moods, logic variables (see [README](https://github.com/ifMike/homeyHASS/blob/main/README.md))

---

Update via HACS (or [Releases](https://github.com/ifMike/homeyHASS/releases)), then restart Home Assistant.

Full history: [CHANGELOG](https://github.com/ifMike/homeyHASS/blob/main/CHANGELOG.md).
