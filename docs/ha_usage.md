# Zeekr 7X Home Assistant Usage

This integration exposes the Zeekr 7X as normal Home Assistant entities and adds a dashboard-oriented display state.

## Model Display

The `model` sensor maps the API model code `CX1E` to `Zeekr 7X`.

The `display_state` sensor is intended for Lovelace cards. It changes according to vehicle state in this priority order:

1. `charging`
2. `plugged_in`
3. `driving`
4. `trunk_open`
5. `engine_hood_open`
6. `sunroof_open`
7. `door_open`
8. `window_open`
9. `unlocked`
10. `parked`

The sensor also includes dashboard attributes for door/window/opening states, battery level, range, and model metadata.

## Image Assets

Place state images in Home Assistant under:

```text
/config/www/zeekr_7x/
```

They will be available to Lovelace as:

```text
/local/zeekr_7x/<file>.png
```

Recommended files:

```text
parked.png
charging.png
plugged_in.png
driving.png
door_open.png
window_open.png
trunk_open.png
engine_hood_open.png
sunroof_open.png
unlocked.png
```

See `docs/lovelace_zeekr_7x_example.yaml` for a `picture-elements` example.

## Zeekr-App-Style Dashboard

If you prefer the Zeekr app homepage look, use:

```text
docs/lovelace_zeekr_7x_app_style_example.yaml
```

It uses this mobile portrait background:

```text
/local/zeekr_7x/app_style/home_base.png
```

The image gives you the app-like ice-field scene, large 7X model, quick action row, and card backgrounds. Home Assistant overlays real entity values on top of it, such as range, battery, charging time, odometer, service counters, lock/window/trunk/plug states, and location.

The clean car scene without static cards is also available:

```text
/local/zeekr_7x/app_style/car_scene_clean.png
```

## App Model State Switching

If you want the car model itself to change, use:

```text
docs/lovelace_zeekr_7x_app_model_example.yaml
```

This switches the whole model image by `display_state`:

```text
/local/zeekr_7x/app_model/base.png
/local/zeekr_7x/app_model/window_open.png
/local/zeekr_7x/app_model/door_open.png
/local/zeekr_7x/app_model/trunk_open.png
/local/zeekr_7x/app_model/engine_hood_open.png
/local/zeekr_7x/app_model/sunroof_open.png
/local/zeekr_7x/app_model/charging.png
/local/zeekr_7x/app_model/plugged_in.png
/local/zeekr_7x/app_model/unlocked.png
```

This is the closest current implementation to the Zeekr app model behavior: when the API says a window, door, hatch, sunroof, charging, or lock state changed, the visible car model changes instead of showing a separate badge.

## Rotatable 3D Model

For a rotatable 3D model in Home Assistant, use:

```text
docs/lovelace_zeekr_7x_3d_iframe_example.yaml
```

The viewer page is:

```text
/local/zeekr_7x/model/index.html
```

The current viewer is strict about model authenticity. It does not draw a fake
or approximate car. It only renders a real local Zeekr 7X model file:

```text
/config/www/zeekr_7x/model/zeekr_7x.glb
/config/www/zeekr_7x/model/zeekr_7x.gltf
```

For the Sketchfab download used in this project, use the GLB file and rename it
to:

```text
zeekr_7x.glb
```

The optional ZIP download contains the source `source/cx1e.fbx` and textures,
but Home Assistant should use the GLB because it is browser-ready.

For live Home Assistant state updates, add this dashboard resource:

```text
/local/zeekr_7x/zeekr-3d-card.js
```

Resource type:

```text
JavaScript module
```

Then use:

```yaml
type: custom:zeekr-3d-card
entity: sensor.zeekr_7x_display_state
height: 560px
```

Replace `sensor.zeekr_7x_display_state` with your actual display state entity.
The card reads all model, door, window, charging, range, and battery attributes
from that entity. With a model that has the expected Zeekr 7X node names, the
viewer animates these parts from HA state:

```text
Door_LF / Door_RF / Door_LB / Door_RB
Glass_LF / Glass_RF / Glass_LB / Glass_RB
Trunk / Hood / Cover_RF
Fillet_srf_15299 / sunfat
Mirror_LF / Mirror_RF
```

That covers front/rear doors, side windows, tailgate, hood, charge lid,
sunroof panel, sunshade, and folded mirrors when lock status is known.

Recommended 3D model format:

```text
.glb or .gltf
```

I found a Zeekr 7X 2025 model on Sketchfab, but Sketchfab download requires authenticated access through their API, so it cannot be pulled anonymously by this project. If you download a legally usable model yourself, export or convert it to `zeekr_7x.glb` and place it in the path above.

Known model sources to check manually:

```text
Sketchfab: Zeekr 7X 2025
CGTrader / TurboSquid / 3DModels: paid automotive models
```

The current viewer supports mouse/touch rotation and zoom through Three.js. If
no original model is present, it shows a missing-model message and keeps HA
state labels active. It intentionally does not show an approximate replacement.

Quick local test URL:

```text
/local/zeekr_7x/model/index.html?door_df=1&window_df_pos=65&trunk=1&charge_lid=1&charging=1
```

## Zeekr App APK Model Findings

I inspected the provided Android APK. It does contain Zeekr 7X 3D resource
entries in:

```text
assets/hybrid/laya3DManifest.json
```

The relevant app bundle is:

```text
assets/hybrid/20250010077X3.zip
targetPath: resources/car/7X
```

However, the APK bundle is not a readable zip. Its raw MD5 matches the
manifest's `enMd5`, not `md5`, which indicates the APK stores the encrypted
resource form. The public manifest URL returns the same encrypted bytes as the
APK bundle, so it is not directly usable as a `.glb`, `.gltf`, or normal zip.
Static inspection located the resource but did not produce a redistributable
original model. See:

```text
docs/zeekr_app_apk_3d_model_notes.md
```

## Layered App-Style Display

For a display closer to the Zeekr app, use the layered example:

```text
docs/lovelace_zeekr_7x_layered_example.yaml
```

The recommended version uses the clearer schematic image pack:

```text
/local/zeekr_7x/schematic/base.png
/local/zeekr_7x/schematic/layers/
```

This is easier to read in Home Assistant than a photo because every door, window, hatch, and status marker has a fixed schematic position.

The photo-based version is also generated and available at:

```text
/local/zeekr_7x/layers/
```

Layer files include:

```text
charging.png
plugged_in.png
driving.png
unlocked.png
door_driver_front.png
door_driver_rear.png
door_passenger_front.png
door_passenger_rear.png
window_driver_front.png
window_driver_rear.png
window_passenger_front.png
window_passenger_rear.png
trunk_open.png
engine_hood_open.png
sunroof_open.png
rear_sunshade_open.png
```

This approach can show multiple states at the same time, such as charging plus unlocked plus sunroof open.

The schematic pack includes a preview image:

```text
www/zeekr_7x/schematic/layered_preview.jpg
```

The project includes a generated image pack under `www/zeekr_7x/`, with matching documentation previews under `docs/assets/zeekr_7x/`. The source photo is `source_zeekr_7x_005_cropped.jpg`, downloaded from Wikimedia Commons:

```text
https://commons.wikimedia.org/wiki/File:Zeekr_7X_005_(cropped).jpg
```

To regenerate the state images after changing the overlay style:

```text
python tools/generate_zeekr_7x_assets.py
python tools/generate_zeekr_7x_schematic_assets.py
python tools/generate_zeekr_7x_app_style_assets.py
python tools/generate_zeekr_7x_app_model_variants.py
```

## More Vehicle Data

The integration now exposes additional read-only values from the API, including range, charge time, charge voltage/current, average consumption, odometer, service counters, low-voltage battery voltage, trip distance, sunroof and rear sunshade positions, and front seat heating/ventilation levels.
