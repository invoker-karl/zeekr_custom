# Zeekr 7X Home Assistant Usage

This integration exposes the Zeekr 7X as normal Home Assistant entities and adds a dashboard-oriented `display_state`.

## Display state

The `display_state` sensor is intended for Lovelace cards. It picks the most relevant single label from this priority order:

1. `charging`
2. `plugged_in`
3. `driving`
4. `trunk_open`
5. `engine_hood_open`
6. `rear_sunshade_open` (the 7X has no openable sunroof; this is the panoramic-roof sunshade)
7. `door_open`
8. `window_open`
9. `unlocked`
10. `parked`

It also exposes attributes for door/window/opening states, battery level, range, and model metadata so a single `picture-entity` or `custom:zeekr-3d-card` can read everything from one entity.

The model code `CX1E` is mapped to `Zeekr 7X` in the `model` sensor.

## 3D Lovelace card

The integration ships an iframe-based 3D viewer that animates door / hood / trunk / mirror / charging-port state in real time, plus a panoramic-roof reflective material that matches the real car.

### 1. Add the JavaScript module as a dashboard resource

**Settings → Dashboards → Resources → Add**:

- URL: `/local/zeekr_7x/zeekr-3d-card.js`
- Type: JavaScript module

### 2. Use the card in YAML

```yaml
type: custom:zeekr-3d-card
entity: sensor.<your_vin_slug>
height: 380px
```

The card reads `model`, `door_*`, `window_*`, `is_charging`, `battery_level`, `range`, `rear_sunshade_open`, etc. directly from the entity attributes — you only need to point it at the main vehicle sensor.

### 3. Auto cache-busting

`zeekr-3d-card.js` appends `&_t=Date.now()` to the iframe URL on every render, so changes to `model/index.html` and the GLB are picked up on a normal page reload — no need to manually bump query-string versions.

## Sample dashboard

`docs/lovelace_zeekr_7x_dashboard_template.yaml` is a complete 3-column Lovelace dashboard:

- Col 1: KPI glance (battery / range / odometer / energy) + status entities + 24h SOC trend
- Col 2: 3D banner + 4-tire pressure & temperature
- Col 3: cabin & maintenance + conditional charging info

To use it, find your VIN slug in **Developer Tools → States** (look for `binary_sensor.<vin_slug>_lock`), then find-and-replace all 33 occurrences of `<YOUR_VIN_SLUG>` in the template. See the main `README.md` for a one-line PowerShell command.

### Required HACS frontend cards

The template uses these cards (popular, all on HACS):

- [`button-card`](https://github.com/custom-cards/button-card)
- [`mini-graph-card`](https://github.com/kalkih/mini-graph-card)
- [`card-mod`](https://github.com/thomasloven/lovelace-card-mod)

## Animated 3D parts

If your `zeekr_7x.glb` has the standard 7X node names, the viewer animates these parts from HA state:

```text
Door_LF / Door_RF / Door_LB / Door_RB        (driver/passenger × front/rear)
Glass_LF / Glass_RF / Glass_LB / Glass_RB    (side windows)
Trunk / Hood / Cover_RF                      (tailgate / hood / charging port flap)
Mirror_LF / Mirror_RF                        (folded when locked)
```

The panoramic glass roof mesh (`Fillet_srf_15299_glass_top_0`) is statically remapped to a light bluish-grey reflective material to match the real car. There is no "sunroof open" animation because the 7X glass roof is fixed; the rear sunshade state is shown via the `rear_sunshade_open` chip.

## Quick local test URL

You can preview the model with synthetic state via query string (no HA required):

```text
/local/zeekr_7x/model/index.html?door_df=1&window_df_pos=65&trunk=1&charge_lid=1&charging=1
```

## All sensor attributes

The integration exposes (per vehicle) battery SOC, range, total odometer, average consumption, 4-tire pressure & temperature, cabin temperature, exterior temperature, seat heating levels, 12V battery voltage, service-due remaining days/distance, charging V/A/state/ETA, sunshade position, etc.

Use **Developer Tools → States** to discover every entity for your VIN.
