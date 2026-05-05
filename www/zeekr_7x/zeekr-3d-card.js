class Zeekr3DCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("zeekr-3d-card requires an entity");
    }

    this._config = {
      url: "/local/zeekr_7x/model/index.html",
      height: "520px",
      ...config,
    };

    this.innerHTML = `
      <ha-card>
        <div class="zeekr-3d-frame">
          <iframe title="Zeekr 7X 3D" allow="fullscreen"></iframe>
        </div>
      </ha-card>
    `;

    const style = document.createElement("style");
    style.textContent = `
      .zeekr-3d-frame {
        width: 100%;
        height: var(--zeekr-3d-height, 520px);
        overflow: hidden;
        border-radius: 8px;
        background: #dce9ee;
      }

      iframe {
        display: block;
        width: 100%;
        height: 100%;
        border: 0;
      }
    `;
    this.appendChild(style);

    this._iframe = this.querySelector("iframe");
    // 给 iframe URL 自动追加时间戳防止 HA / 浏览器缓存旧 model.html。
    // yaml 里的 ?v=xxx 仍然有效,在它后面追加 &_t=timestamp。
    const baseUrl = this._config.url;
    const sep = baseUrl.includes("?") ? "&" : "?";
    this._iframe.src = `${baseUrl}${sep}_t=${Date.now()}`;
    this._iframe.addEventListener("load", () => this._postState());
    this.style.setProperty("--zeekr-3d-height", this._config.height);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config?.entity) {
      return;
    }
    // HA recreates the entity object on every state change, so reference
    // equality is a correct cheap way to skip unrelated entity updates.
    const entity = hass?.states?.[this._config.entity];
    if (entity === this._lastEntityRef) {
      return;
    }
    this._lastEntityRef = entity;
    this._postState();
  }

  getCardSize() {
    return 6;
  }

  _postState() {
    if (!this._hass || !this._iframe?.contentWindow || !this._config?.entity) {
      return;
    }

    const entity = this._hass.states[this._config.entity];
    if (!entity) {
      return;
    }

    const attrs = entity.attributes || {};
    const state = {
      model: attrs.model_name || attrs.model || "极氪 7X",
      display: entity.state || "parked",
      range: attrs.range_km ?? "--",
      soc: attrs.battery_level ?? "--",
      charging: this._bool(attrs.is_charging),
      plugged: this._bool(attrs.is_plugged_in),
      chargeLid: this._bool(attrs.charge_lid_open),
      unlocked: this._bool(attrs.is_unlocked),
      lockKnown: attrs.is_unlocked !== undefined && attrs.is_unlocked !== null,
      trunk: this._bool(attrs.trunk_open),
      hood: this._bool(attrs.engine_hood_open),
      sunroof: this._bool(attrs.sunroof_open),
      sunroofPosition: this._number(attrs.sunroof_position),
      rearSunshade: this._bool(attrs.rear_sunshade_open),
      rearSunshadePosition: this._number(attrs.rear_sunshade_position),
      doors: {
        df: this._bool(attrs.door_driver_front),
        dr: this._bool(attrs.door_driver_rear),
        pf: this._bool(attrs.door_passenger_front),
        pr: this._bool(attrs.door_passenger_rear),
      },
      doorPositions: {
        df: this._number(attrs.door_driver_front_position),
        dr: this._number(attrs.door_driver_rear_position),
        pf: this._number(attrs.door_passenger_front_position),
        pr: this._number(attrs.door_passenger_rear_position),
      },
      windows: {
        df: this._bool(attrs.window_driver_front),
        dr: this._bool(attrs.window_driver_rear),
        pf: this._bool(attrs.window_passenger_front),
        pr: this._bool(attrs.window_passenger_rear),
      },
      windowPositions: {
        df: this._number(attrs.window_driver_front_position),
        dr: this._number(attrs.window_driver_rear_position),
        pf: this._number(attrs.window_passenger_front_position),
        pr: this._number(attrs.window_passenger_rear_position),
      },
    };

    this._iframe.contentWindow.postMessage(
      {
        type: "zeekr-7x-state",
        state,
      },
      window.location.origin,
    );
  }

  _bool(value) {
    return value === true || value === "true" || value === "on" || value === "1";
  }

  _number(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }
}

customElements.define("zeekr-3d-card", Zeekr3DCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "zeekr-3d-card",
  name: "Zeekr 7X 3D Card",
  description: "Rotatable Zeekr 7X model driven by zeekr_custom display_state attributes.",
});
