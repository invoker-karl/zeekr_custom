# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-05-06

Initial public release of `zeekr_custom` for Home Assistant.

### Added

- **Integration platforms**: `sensor`, `binary_sensor` (read-only)
- **Sensors**: state of charge, range, total odometer, average consumption,
  4-tire pressure & temperature, cabin & exterior temperature, driver/passenger
  seat heating level, 12V battery voltage, service-due remaining days/distance,
  charging voltage/current/state/time-to-full, sunshade position, trip distance
- **Binary sensors**: lock, 4 doors (individual + aggregate), 4 windows
  (individual + aggregate), sunroof, rear sunshade, trunk, hood, charging plug,
  defrost, steering wheel heating, engine running
- **3D Lovelace card** (`zeekr-3d-card.js`):
  - Three.js + GLB renderer with live state animation
    (door / hood / trunk opens, mirrors fold on lock, charge port flap)
  - Panoramic glass roof rendered as light bluish-grey reflective material
    matching the real Zeekr 7X (instead of the GLB's default deep transparent
    glass which read as "open sunroof")
  - Auto cache-busting: iframe URL gets a `&_t=Date.now()` suffix so updates
    to `model/index.html` are picked up on a normal page reload
- **Sample dashboard**: 3-column Lovelace template
  (`docs/lovelace_zeekr_7x_dashboard_template.yaml`) with KPI glance,
  status entities, 24h SOC trend, 3D banner, 4-tire health, cabin & maintenance,
  conditional charging info
- **Reverse-engineered Zeekr cloud API client** (`zeekr_api/`):
  - HMAC-SHA256 + AES-CBC X-VIN signing for new platform (Zeekr 7X)
  - HMAC-SHA1 signing for legacy platform
  - SMS-code login + main-token login flows
  - asyncio.Lock-based serialization to prevent token-refresh stampede
- **Config flow**: SMS login, options flow, reauth (bound to original
  `entry_id` so reauth cannot redirect to a different entry sharing the
  same mobile)
- **Coordinator**: 60s polling, raises `ConfigEntryAuthFailed` on auth error
  (triggers HA's "Reconfigure" prompt) and `UpdateFailed` on transient errors
- **Documentation**: README, `docs/ha_usage.md`, dashboard template, sample
  reverse-engineering notes
- **HACS metadata**: `hacs.json` with `content_in_root: true`
- **CI**: `.github/workflows/validate.yml` runs hassfest + HACS validation
  on push, PR, and nightly schedule

### Notes

- 7X panoramic glass roof has no openable sunroof; the rear sunshade entity
  is what users actually control. The integration's `display_state` reflects
  this priority order with `rear_sunshade_open` ahead of `sunroof_open`,
  and the latter is gated by `sunroof_position > 0` to filter stale boolean
  status from cars without a real sunroof.
- Entity IDs are derived from the vehicle's VIN slug; the dashboard template
  uses `<YOUR_VIN_SLUG>` placeholder which users replace after install.
- Read-only at this version. No remote commands (lock/unlock, climate,
  charge start/stop) are implemented yet.

[Unreleased]: https://github.com/invoker-karl/zeekr_custom/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/invoker-karl/zeekr_custom/releases/tag/v0.0.1
