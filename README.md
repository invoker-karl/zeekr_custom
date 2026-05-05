# Zeekr Custom Integration

Home Assistant custom integration for Zeekr vehicles, with additional Zeekr 7X dashboard and visual assets.

## What Is Here

- Home Assistant integration platforms: `sensor.py`, `binary_sensor.py`, `cover.py`, and `device_tracker.py`.
- Config entry and coordinator wiring: `__init__.py`, `config_flow.py`, `coordinator.py`, and `base.py`.
- Zeekr API implementation: `zeekr_api/`.
- Chinese translations: `translations/zh-Hans.json`.
- Dashboard examples and usage notes: `docs/`.
- Zeekr 7X static assets and 3D page: `www/zeekr_7x/`.
- Development helpers for probing and asset generation: `tools/`.

## Important Runtime Files

The integration metadata is defined in `manifest.json`:

- Domain: `zeekr_custom`
- Config flow: enabled
- IoT class: `cloud_polling`
- Python requirement: `pycryptodome==3.23.0`

The main setup path is:

1. `async_setup_entry` in `__init__.py` creates an API `Controller`.
2. The controller authenticates and loads vehicles.
3. A `ZeekrDataUpdateCoordinator` is created for each VIN.
4. Home Assistant forwards setup to all platforms listed in `const.py`.

## Dashboard Assets

The `www/zeekr_7x/` folder contains generated PNG states, layered assets, app-style renders, and a local 3D model viewer.

Useful examples live in `docs/`:

- `docs/ha_usage.md`
- `docs/lovelace_zeekr_7x_example.yaml`
- `docs/lovelace_zeekr_7x_layered_example.yaml`
- `docs/lovelace_zeekr_7x_app_style_example.yaml`
- `docs/lovelace_zeekr_7x_app_model_example.yaml`
- `docs/lovelace_zeekr_7x_3d_iframe_example.yaml`

## Local Cleanup

The project has previously accumulated browser profile folders and verification screenshots. These are ignored by `.gitignore` because they are generated local artifacts and can make future automated scans slow or unresponsive.

Safe-to-remove generated paths include:

- `__pycache__/`
- `tools/__pycache__/`
- `zeekr_api/__pycache__/`
- `tmp_chrome_profile*/`
- `tmp_edge_profile*/`
- root-level `tmp_*` files

## Quick Verification

Run a syntax-only check from the project root:

```powershell
C:\Users\karl321\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q . -x "tmp_.*|__pycache__"
```

Full Home Assistant validation should be done after placing this directory under `custom_components/zeekr_custom` in a Home Assistant environment.

## Import Into Home Assistant

Use this directory as the integration folder:

```text
/config/custom_components/zeekr_custom/
```

Copy the integration runtime files and folders there:

```text
__init__.py
base.py
binary_sensor.py
config_flow.py
const.py
coordinator.py
cover.py
device_tracker.py
manifest.json
number.py
sensor.py
translations/
zeekr_api/
```

Copy dashboard assets separately to Home Assistant static files:

```text
/config/www/zeekr_7x/
```

The source folder for those assets is:

```text
www/zeekr_7x/
```

After copying, restart Home Assistant, add the integration from Settings -> Devices & services, and configure either SMS login or token login. For the 3D card, add this dashboard resource as a JavaScript module:

```text
/local/zeekr_7x/zeekr-3d-card.js
```

Then use `docs/lovelace_zeekr_7x_3d_iframe_example.yaml` or one of the other Lovelace examples as a starting point.
