# Project Notes for Coding Agents

This workspace is a Home Assistant custom integration named `zeekr_custom`, with optional dashboard assets for Zeekr 7X visual cards.

## High-signal paths

- `manifest.json`: Home Assistant integration metadata.
- `__init__.py`: config entry setup, controller creation, coordinator wiring, unload handling.
- `config_flow.py`: login/config/options flow.
- `coordinator.py`: periodic vehicle refresh orchestration.
- `base.py`: shared Home Assistant entity base class.
- `sensor.py`, `binary_sensor.py`, `cover.py`, `device_tracker.py`: platform entities.
- `zeekr_api/`: Zeekr API client, controller, vehicle model, and protocol helpers.
- `translations/zh-Hans.json`: Home Assistant UI translations.
- `www/zeekr_7x/`: Lovelace/web assets intended to be copied or served from Home Assistant `www`.
- `docs/`: usage notes, Lovelace examples, and asset previews.
- `tools/`: local generation/probing helpers. Treat these as development utilities, not runtime integration code.

## Avoid scanning these by default

- `tmp_chrome_profile*/` and `tmp_edge_profile*/`: browser cache/profile folders from visual checks. They are large and noisy.
- `__pycache__/` and `tools/__pycache__/`: generated Python bytecode.
- `tmp_*`: screenshots, temporary servers, and probe outputs unless the current task explicitly needs them.

## Current organization intent

- Runtime integration code lives at the repository root plus `zeekr_api/` and `translations/`.
- Dashboard examples and generated assets live in `docs/` and `www/zeekr_7x/`.
- The 3D model page is `www/zeekr_7x/model/index.html`; it depends on local vendored Three.js files under `www/zeekr_7x/model/vendor/` and `utils/`.

## Verification

- Syntax check Python without touching browser profiles:
  `python -m compileall -q . -x "tmp_.*|__pycache__"`
- For Home Assistant behavior, test inside a real Home Assistant custom_components deployment because HA packages are not vendored in this workspace.
- For 3D/Lovelace visual work, serve the workspace locally and open `www/zeekr_7x/model/index.html` rather than using a browser profile directory committed into the project.

