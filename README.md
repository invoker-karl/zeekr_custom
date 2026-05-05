# Zeekr Custom Integration

Home Assistant custom integration for Zeekr vehicles, with extended support for the **Zeekr 7X** (panoramic glass roof + electric sunshade).

Cloud-polling, read-only — exposes vehicle telemetry (range, SOC, tire pressure/temperature, doors, charging state, …) and a 3D dashboard card with live state animation.

> ⚠️ Read-only at the moment. No remote commands (lock/unlock, start/stop charging, climate). The integration only reads from the Zeekr cloud.

---

## Features

**Sensors**
- State of charge (%), range (km), total odometer (km), average consumption (kWh/100km)
- Cabin & exterior temperature, driver/passenger seat heating level
- 4-tire pressure & temperature
- Charging voltage / current / state / time-to-full
- 12V battery voltage
- Service-due remaining days & distance
- Trip distance, sunroof/sunshade position

**Binary sensors**
- Lock state
- 4 doors (individual + aggregate)
- 4 windows (individual + aggregate)
- Sunroof, rear sunshade, trunk, hood, charging plug
- Defrost, steering wheel heating, engine running

**3D Lovelace card**
- Live state animation: doors / hood / trunk open, mirrors fold on lock, charge port flap
- Custom Three.js + GLB renderer, no external dependencies
- Auto cache-busting (no need to bump URL versions when updating)

**Sample dashboard**
- 3-column sections layout: KPI + status + SOC trend / 3D model + 4-tire health / cabin & maintenance + conditional charging info

---

## Installation

### Via HACS (recommended)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/invoker-karl/zeekr_custom` as type **Integration**
3. Install **Zeekr Custom Integration**
4. Restart Home Assistant

### Manual

Copy the integration files into `/config/custom_components/zeekr_custom/`:

```
__init__.py        base.py            binary_sensor.py
config_flow.py     const.py           coordinator.py
cover.py           manifest.json      sensor.py
translations/      zeekr_api/
```

Copy the dashboard assets into `/config/www/zeekr_7x/`:

```
model/             zeekr-3d-card.js
```

Restart Home Assistant.

---

## Configure the integration

1. **Settings → Devices & services → Add integration → "Zeekr"**
2. Enter your Zeekr account phone number, request SMS code, enter the code

The integration creates one device per vehicle. Entities are named after the vehicle's VIN slug, e.g. `binary_sensor.<vin_slug>_lock`.

---

## Configure the dashboard

### 1. Add the 3D card as a Lovelace resource

**Settings → Dashboards → Resources → Add**:

- URL: `/local/zeekr_7x/zeekr-3d-card.js`
- Type: JavaScript module

### 2. Find your VIN slug

**Developer Tools → States** → search for `binary_sensor.` and look for one of the integration's entities, e.g. `binary_sensor.xiang_xxxxxx_xxxxxxxxxxxxxxxxx_lock`. The middle part (`xiang_xxxxxx_xxxxxxxxxxxxxxxxx`) is your VIN slug.

### 3. Render the dashboard template with your VIN slug

Open `docs/lovelace_zeekr_7x_dashboard_template.yaml` in any text editor and **find-and-replace** all occurrences of `<YOUR_VIN_SLUG>` (33 places) with your VIN slug. Save as a new file (e.g. `my_dashboard.yaml`).

PowerShell one-liner:
```powershell
(Get-Content docs/lovelace_zeekr_7x_dashboard_template.yaml) `
  -replace '<YOUR_VIN_SLUG>', 'xiang_xxxxxx_xxxxxxxxxxxxxxxxx' `
  | Set-Content my_dashboard.yaml
```

### 4. Paste into Home Assistant

**Settings → Dashboards → New dashboard → ⋮ → Take control → ⋮ → Raw configuration editor** → paste the rendered yaml → Save → Ctrl+Shift+R.

---

## Required HACS frontend cards

The dashboard template uses these HACS frontend cards (all popular):

- [`button-card`](https://github.com/custom-cards/button-card)
- [`mini-graph-card`](https://github.com/kalkih/mini-graph-card)
- [`card-mod`](https://github.com/thomasloven/lovelace-card-mod)

---

## Project layout

```
zeekr_custom/
├── __init__.py            integration entry, device registry
├── config_flow.py         SMS login / token refresh
├── coordinator.py         data update coordinator (60s polling)
├── const.py               PLATFORMS = sensor + binary_sensor
├── manifest.json          integration metadata
├── sensor.py / binary_sensor.py / cover.py    entity platforms
├── base.py                ZeekrCarEntity base class
├── translations/zh-Hans.json   Chinese strings
├── zeekr_api/
│   ├── controller.py      auth scheduling
│   ├── client_old.py      legacy models  (HMAC-SHA1)
│   ├── client_new.py      new models     (HMAC-SHA256 + AES-CBC X-VIN)
│   ├── client_main.py     main account auth
│   └── car.py             Car data model
└── www/zeekr_7x/
    ├── model/             Three.js + GLB 3D viewer
    │   ├── index.html
    │   ├── zeekr_7x.glb
    │   └── vendor/        three.module.js + GLTFLoader + OrbitControls
    └── zeekr-3d-card.js   Lovelace iframe wrapper card
```

---

## Vehicle compatibility

The reverse-engineered API client supports both old and new Zeekr cloud platforms. Tested on:

- ✅ Zeekr 7X (new platform, panoramic glass roof variant)

Other models *should* work for read-only telemetry but may need entity/dashboard tweaks:

- 001, 009, 001 FR, X, 001 (FR), Mix, …

If you successfully use this integration with another model, please open an issue with details.

---

## Acknowledgments

- Reverse-engineered from the Zeekr Life iOS app
- Based on Three.js for 3D rendering, GLB model converted from app's local assets
- Inspired by similar HACS integrations: tesla_custom, kia_uvo

---

## License

MIT — see [LICENSE](LICENSE).
