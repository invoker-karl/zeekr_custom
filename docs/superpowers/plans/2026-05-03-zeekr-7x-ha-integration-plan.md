# Zeekr 7X HA Integration 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 zeekr_custom 集成在用户的 HA OS 上跑通,接入 Zeekr 7X 账号显示续航/SOC/门窗等,3D 卡片随车机状态联动开关门/充电,把模型轮毂调成跟实车一致(银+黑双色 10 辐 + 橙铜卡钳 + ZEEKR 中心 logo),修复 4 critical + 6 high 阻塞 BUG。

**Architecture:** 6 阶段顺序执行——Phase 1 在本机 `D:\github\zeekr_custom\` 修代码;Phase 2 用户装 Samba addon 把 HA 的 `/config/` 挂成 `Z:\`,Claude 把代码 + 资产同步到 HA;Phase 3 跑阶段 A 验收(集成可用);Phase 4 部署 2D + 3D 卡片;Phase 5 迭代轮毂(参数化建模 + ZEEKR logo);Phase 6 走 D1-D5 兜底验证。

**Tech Stack:** Python 3.11+ (HA core)、aiohttp、voluptuous、Three.js r166、Canvas 2D、Samba SMB

**Spec 引用:** `D:\github\zeekr_custom\docs\superpowers\specs\2026-05-03-zeekr-7x-ha-integration-design.md`

---

## File Structure

### 修改的文件(D:\github\zeekr_custom\ → 同步到 Z:\custom_components\zeekr_custom\)

| 文件 | 改什么 | 责任 |
|------|--------|------|
| `__init__.py` | 删 60-114(async_setup);改 140-148(try/except 分流);改 173-194(async_unload_entry) | Config entry 生命周期 |
| `config_flow.py` | 改 210-214(async_step_reauth + 加 reauth_confirm) | UI 配置流 |
| `sensor.py` | 改 87-109(ZeekrCarTemp 修 type 碰撞) | sensor 平台实体 |
| `base.py` | 改 13-28(加 type 防御断言) | 实体基类 |
| `client_main.py` | _fetch 加 401 → ZeekrAuthError 分支 | 主项目 API client |
| `client_old.py` | 删 162-172 中的 token= kwarg | 老车型 API client |
| `controller.py` | 加 `_auth_lock: asyncio.Lock` 串行化 auth + update | 多 client 协调 |
| `manifest.json` | 加 issue_tracker、loggers 字段 | HA 集成元数据 |
| `const.py` | PLATFORMS 删 device_tracker | 平台清单 |

### 删除的文件

- `device_tracker.py`(从 PLATFORMS 移除后变孤儿)
- `number.py`(0 字节空文件)

### 修改的资产文件(D:\github\zeekr_custom\www\zeekr_7x\ → 同步到 Z:\www\zeekr_7x\)

| 文件 | 改什么 |
|------|--------|
| `model/index.html` | 改 331(USE_REFERENCE_WHEEL→true,如走路径 Y);改 964-968(ZEEKR logo 字体) |
| `model/fonts/Inter-Black.woff2` | **新增**(50KB,字体内嵌) |

---

## Phase 1: Python 代码修复(本机操作)

> 所有 task 在 `D:\github\zeekr_custom\` 下做,完成后 Phase 2 一次性同步到 Z:\。本项目非 git 仓库,用"文件保存即 checkpoint"。

---

### Task 1.1: 修 C1 — ZeekrCarTemp 类属性碰撞

**Files:**
- Modify: `D:\github\zeekr_custom\sensor.py:87-109`

- [ ] **Step 1: 打开文件并定位 ZeekrCarTemp 类**

文件 `sensor.py:87-109` 现状:

```python
class ZeekrCarTemp(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car interior temperature sensor."""

    type = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        *,
        inside=False,
    ) -> None:
        """Initialize temp entity."""
        self.inside = inside
        if inside is True:
            self.type += " (inside)"
        else:
            self.type += " (outside)"
        super().__init__(car, coordinator)
```

**问题:** `self.type += "..."` 在没有 instance attr 时改写 class attr。第一个 outside 实例把 `ZeekrCarTemp.type` 改成 `"temperature (outside)"`,第二个 inside 实例继承被改的类属性再追加,变成 `"temperature (outside) (inside)"`。两个 unique_id 都不对,HA 注册一个、丢一个。

- [ ] **Step 2: 替换整个类(去掉 type 类属性,改用 instance attr 直接赋值)**

```python
class ZeekrCarTemp(ZeekrCarEntity, SensorEntity):
    """Representation of the Zeekr car interior/exterior temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        car: ZeekrCar,
        coordinator: ZeekrDataUpdateCoordinator,
        *,
        inside=False,
    ) -> None:
        """Initialize temp entity."""
        self.inside = inside
        self.type = "temperature_inside" if inside else "temperature_outside"
        super().__init__(car, coordinator)
```

要点:
- 删掉 class-level `type = "temperature"`(line 90)
- 在 super().__init__ 调用**之前**直接赋值 `self.type`(必须在 super 之前,因为 base 类的 `__init__` 会用 self.type 算 unique_id)
- 改用下划线分隔(`temperature_inside` / `temperature_outside`),避免空格在 unique_id 里被 slugify 不一致

- [ ] **Step 3: 验证文件保存**

读取 `D:\github\zeekr_custom\sensor.py:87-109`,确认上面替换内容已写入,且 `type = "temperature"` 不再出现在该类块内(`grep -c "type = \"temperature\"" sensor.py` 应该返回 0,如果整个文件其他地方没有同名)。

---

### Task 1.2: 修 H2 — base.py 加 type 防御断言

**Files:**
- Modify: `D:\github\zeekr_custom\base.py:13-28`

- [ ] **Step 1: 打开文件,定位 ZeekrBaseEntity 类**

`base.py:13-28` 现状:

```python
class ZeekrBaseEntity(CoordinatorEntity[ZeekrDataUpdateCoordinator]):
    """Representation of a Zeekr device."""

    type: str
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _enabled_by_default: bool = True
    _memorized_unique_id: str | None = None

    def __init__(
        self, base_unique_id: str, coordinator: ZeekrDataUpdateCoordinator
    ) -> None:
        """Initialise the Zeekr device."""
        super().__init__(coordinator)
        self._attr_unique_id = slugify(f"{base_unique_id} {self.type}")
        self._attr_entity_registry_enabled_default = self._enabled_by_default
```

**问题:** `type: str` 只是类型注解,没默认值。如果某个子类忘了设 `type` 类属性 OR `self.type` instance attr,实例化时 `self.type` 会抛 `AttributeError`,但堆栈不直观,debug 慢。

- [ ] **Step 2: 在 super().__init__ 之前加防御断言**

替换 `__init__` 方法:

```python
    def __init__(
        self, base_unique_id: str, coordinator: ZeekrDataUpdateCoordinator
    ) -> None:
        """Initialise the Zeekr device."""
        if not getattr(self, "type", None):
            raise RuntimeError(
                f"{type(self).__name__} must define class attribute 'type' "
                f"or set self.type before calling super().__init__"
            )
        super().__init__(coordinator)
        self._attr_unique_id = slugify(f"{base_unique_id} {self.type}")
        self._attr_entity_registry_enabled_default = self._enabled_by_default
```

- [ ] **Step 3: 验证**

Read `D:\github\zeekr_custom\base.py:13-32`,确认新 `__init__` 包含 `RuntimeError` 行。

---

### Task 1.3: 修 C2 — async_setup_entry 异常分流

**Files:**
- Modify: `D:\github\zeekr_custom\__init__.py:140-148`

- [ ] **Step 1: 在文件头部 imports 区加 ConfigEntryNotReady**

`__init__.py:10` 当前 import:

```python
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
```

改成:

```python
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
```

- [ ] **Step 2: 替换 line 140-148 的双 try 块**

`__init__.py:140-148` 现状:

```python
    try:
        await controller.auth_all_api()
    except ZeekrAPIError as e:
        raise ConfigEntryAuthFailed from e

    try:
        await controller.get_vehicles()
    except ZeekrAuthError as e:
        raise ConfigEntryAuthFailed from e
```

替换成单一 try 块,正确分流(子类 `ZeekrAuthError` 放前优先匹配):

```python
    try:
        await controller.auth_all_api()
        await controller.get_vehicles()
    except ZeekrAuthError as e:
        raise ConfigEntryAuthFailed from e
    except ZeekrAPIError as e:
        raise ConfigEntryNotReady from e
```

- [ ] **Step 3: 验证**

Read `D:\github\zeekr_custom\__init__.py:140-150`,确认新代码块。`grep -c "ConfigEntryNotReady" __init__.py` 至少 2 次(import + raise)。

---

### Task 1.4: 修 C4 — 删除 async_setup(YAML 路径)

**Files:**
- Modify: `D:\github\zeekr_custom\__init__.py:60-114`

- [ ] **Step 1: 定位要删的整段**

`__init__.py:60-114` 是 `async_setup(hass, base_config)` 函数,55 行。从 `async def async_setup` 那行删到该函数的最后一行(返回 `True` 之后)。

- [ ] **Step 2: 删除整段**

删除 `__init__.py:60-115`(包括尾部空行)。删除前最后一行是 `return True`(line 114),删除后下一行直接是 `async def async_setup_entry`(原 line 117,删后变成 line 60 附近)。

也要删除 `__init__.py:7` 上 `SOURCE_IMPORT` 的 import,因为 `async_setup` 是它唯一的使用者。

`__init__.py:7` 现状:

```python
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
```

改成:

```python
from homeassistant.config_entries import ConfigEntry
```

同样,`_async_configured_mobiles`(`__init__.py:50-57`)也只被 `async_setup` 用,一并删除——它从 line 50 (`@callback`) 到 line 57 末尾(`}`)。

- [ ] **Step 3: 验证**

Read `D:\github\zeekr_custom\__init__.py`,行数应从原 248 缩减到 ~190 左右。`grep -c "async def async_setup\b" __init__.py` 应该返回 0(只剩 `async_setup_entry`)。`grep "SOURCE_IMPORT" __init__.py` 应无结果。

---

### Task 1.5: 修 H3 — async_unload_entry 顺序

**Files:**
- Modify: `D:\github\zeekr_custom\__init__.py`(原 line 173-194,Task 1.4 删除后行号会前移)

- [ ] **Step 1: 找到 async_unload_entry 函数**

Task 1.4 删除 async_setup 后,async_unload_entry 现在大约在 line 115-135。Read 找到具体位置。

现状(逻辑等价):

```python
async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    entry_data = hass.data[DOMAIN][config_entry.entry_id]

    for listener in entry_data[DATA_LISTENER]:
        listener()
    username = config_entry.title

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        _LOGGER.debug("Unloaded entry for %s", username)

        # TODO: 卸载service
        # if not hass.data[DOMAIN]:
        #     async_unload_services(hass)

        return True

    return False
```

- [ ] **Step 2: 替换整个函数为 unload-safe 版**

```python
async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if entry_data:
            for listener in entry_data.get(DATA_LISTENER, []):
                listener()
        _LOGGER.debug("Unloaded entry for %s", config_entry.title)
    return unload_ok
```

要点:
- listener 摘除 + `hass.data` 清理只在 `unload_ok` 时做
- 用 `dict.pop(key, None)` 容错,避免被外部代码竞争 pop 时 KeyError
- 用 `dict.get(DATA_LISTENER, [])` 容错
- 删掉 `username = config_entry.title` 临时变量(只在 _LOGGER.debug 用一次,直接写 `config_entry.title`)

- [ ] **Step 3: 验证**

Read 该函数,确认整个 `for listener in ...` 块在 `if unload_ok:` 内。

---

### Task 1.6: 修 C3 — config_flow async_step_reauth

**Files:**
- Modify: `D:\github\zeekr_custom\config_flow.py:210-214`

- [ ] **Step 1: 在文件 imports 加 Mapping**

`config_flow.py:6-9` 现状:

```python
from typing import Any
```

改成:

```python
from collections.abc import Mapping
from typing import Any
```

- [ ] **Step 2: 替换 async_step_reauth 函数(line 210-214)**

现状:

```python
    async def async_step_reauth(self, data):
        """Handle configuration by re-auth."""
        self.mobile = data[CONF_MOBILE]
        self.reauth = True
        return await self.async_step_user()
```

替换成:

```python
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> Any:
        """Handle initiation of re-authentication.

        Modern HA (2024+) signature. Reuses the original device_id from
        entry.data so the trusted-device binding on Zeekr's side stays valid.
        """
        self.mobile = entry_data.get(CONF_MOBILE)
        self.reauth = True
        # Reuse the controller created in async_step_user but inject the
        # original device_id so signing stays consistent across reauth.
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Confirm re-authentication with the user before re-running auth flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={"mobile": self.mobile or "—"},
            )
        # User confirmed. Route to original auth_type they used (mobile
        # or token); default to mobile (most common).
        return await self.async_step_user()
```

要点:
- 新签名 `async_step_reauth(self, entry_data: Mapping)` 是 HA 2024+ 现代规范
- 拆出 `async_step_reauth_confirm` — 显示一个确认表单(空 schema)告诉用户"需要重新认证",用户点 Submit 后才走原有 user step
- `device_id` 复用在 `async_step_user → async_step_mobile/token` 中通过现有的 `_async_update_auth_entry` 流程实现(已存在,line 226-239),不需要这里改

- [ ] **Step 3: 加 reauth_confirm 翻译条目**

打开 `D:\github\zeekr_custom\translations\zh-Hans.json`,找到 `"config"` → `"step"` 节点。在已有的 step 列表(`user`、`mobile`、`code`、`token`、`choose_vehicle`)旁加 `reauth_confirm`:

```json
"reauth_confirm": {
  "title": "重新认证 Zeekr",
  "description": "{mobile} 的 token 已失效或服务端拒绝。点击提交后将重新走登录流程。"
}
```

具体加在 `"choose_vehicle"` 项之后即可。

- [ ] **Step 4: 验证**

Read `config_flow.py:210-235`,确认有两个 reauth 函数。Read `translations/zh-Hans.json` grep `reauth_confirm`,应有 1 个匹配。

---

### Task 1.7: 修 H1 — client_main.py 401 → ZeekrAuthError

**Files:**
- Modify: `D:\github\zeekr_custom\zeekr_api\client_main.py:85-93`

- [ ] **Step 1: 打开 _fetch 看 401 处理**

`client_main.py:85-93` 现状:

```python
            if status != 200:
                _LOGGER.error(
                    "请求出错 %s result status: %s, reason: %s",
                    full_url,
                    status,
                    r.reason,
                )
                error_msg = f"response status {status}"
                raise ZeekrAPIError(error_msg)
```

- [ ] **Step 2: 加 401 → ZeekrAuthError 分支**

替换为:

```python
            if status != 200:
                _LOGGER.error(
                    "请求出错 %s result status: %s, reason: %s",
                    full_url,
                    status,
                    r.reason,
                )
                error_msg = f"response status {status}"
                if status == 401:
                    raise ZeekrAuthError(error_msg)
                raise ZeekrAPIError(error_msg)
```

- [ ] **Step 3: 在文件顶部 import 加 ZeekrAuthError**

`client_main.py:13` 当前:

```python
from .exceptions import ZeekrAPIError
```

改成:

```python
from .exceptions import ZeekrAPIError, ZeekrAuthError
```

- [ ] **Step 4: 验证**

`grep -c "ZeekrAuthError" client_main.py` 应 ≥ 2(import + raise)。

---

### Task 1.8: 修 H4 — client_old.py 删 token kwarg

**Files:**
- Modify: `D:\github\zeekr_custom\zeekr_api\client_old.py:162-172`

- [ ] **Step 1: 定位 auth_by_refresh_token 函数**

`client_old.py:162-172` 现状:

```python
    async def auth_by_refresh_token(self):
        """Authorize vehicle security by refresh token."""
        data, code, msg = await self._fetch(
            method="put",
            url="/auth/account/session/secure",
            data={"refreshToken": self.refresh_token},
            token=self.access_token,
        )
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return data, code, msg
```

**问题:** `token=self.access_token` 是个根本不存在的 kwarg,会被 `_fetch(**kwargs)` 透传给 `aiohttp.ClientSession.request(**kwargs)`,触发 `TypeError: unexpected keyword argument 'token'`。`Authorization` 头已经在 `_make_header` 通过 `self.access_token` 自动加,无需重传。

- [ ] **Step 2: 删除 token kwarg**

替换为:

```python
    async def auth_by_refresh_token(self):
        """Authorize vehicle security by refresh token."""
        data, code, msg = await self._fetch(
            method="put",
            url="/auth/account/session/secure",
            data={"refreshToken": self.refresh_token},
        )
        self.access_token = data["accessToken"]
        self.refresh_token = data["refreshToken"]
        return data, code, msg
```

- [ ] **Step 3: 验证**

Read 修改后的函数,确认 `token=` 行已删除,函数体由 6 行减为 5 行。

---

### Task 1.9: 修 H6 — controller.py asyncio.Lock

**Files:**
- Modify: `D:\github\zeekr_custom\zeekr_api\controller.py`

- [ ] **Step 1: 在 imports 区加 asyncio**

`controller.py:3-6` 现状(已经有):

```python
import asyncio
import logging
```

确认 `asyncio` 已导入。如已有,跳过此步。

- [ ] **Step 2: 在 Controller.__init__ 加 lock**

`controller.py:19-39` 当前 `__init__` 末尾(line 39 `self.cars: dict[str, ZeekrCar] = {}`)之后,加一行:

```python
        self.cars: dict[str, ZeekrCar] = {}
        self._auth_lock = asyncio.Lock()
```

- [ ] **Step 3: 在 auth_all_api 加锁**

`controller.py:61-66` 现状:

```python
    async def auth_all_api(self):
        """Auth all API."""
        data, _, _ = await self.__client_main.get_auth_code()
        auth_code = data["YIKAT_NEW"]
        await self.__client_old.auth_by_auth_code(auth_code)
        await self.__client_new.auth_by_main_token(self.main_token)
```

替换为:

```python
    async def auth_all_api(self):
        """Auth all API (serialized to avoid token rotation race)."""
        async with self._auth_lock:
            data, _, _ = await self.__client_main.get_auth_code()
            auth_code = data["YIKAT_NEW"]
            await self.__client_old.auth_by_auth_code(auth_code)
            await self.__client_new.auth_by_main_token(self.main_token)
```

- [ ] **Step 4: 在 update 加锁(读侧)**

`controller.py:94-98` 现状:

```python
    async def update(self, vin: str):
        """Update vehicle data."""
        vehicle_data = await self.get_vehicle_data(vin)
        self._vehicle_data.setdefault(vin, {}).update(vehicle_data)
        return self._vehicle_data[vin]
```

替换为:

```python
    async def update(self, vin: str):
        """Update vehicle data (serialized against auth refresh)."""
        async with self._auth_lock:
            vehicle_data = await self.get_vehicle_data(vin)
            self._vehicle_data.setdefault(vin, {}).update(vehicle_data)
            return self._vehicle_data[vin]
```

要点:用同一把 `_auth_lock` 串行 auth 和 update,确保 token 轮换期间没有 update 在用旧 token。

- [ ] **Step 5: 验证**

`grep -c "self._auth_lock" controller.py` 应该 ≥ 3 次(__init__ + auth_all_api + update)。

---

### Task 1.10: 修 H5 — manifest.json 元数据

**Files:**
- Modify: `D:\github\zeekr_custom\manifest.json`

- [ ] **Step 1: 替换整个文件**

现状:

```json
{
  "domain": "zeekr_custom",
  "name": "Zeekr Custom Integration",
  "codeowners": ["@aourwz"],
  "config_flow": true,
  "documentation": "https://www.home-assistant.io/integrations/zeekr_vehicle",
  "iot_class": "cloud_polling",
  "requirements": ["pycryptodome==3.23.0"],
  "version": "0.0.1"
}
```

替换为:

```json
{
  "domain": "zeekr_custom",
  "name": "Zeekr Custom Integration",
  "codeowners": ["@aourwz"],
  "config_flow": true,
  "documentation": "https://github.com/aourwz/zeekr_custom",
  "issue_tracker": "https://github.com/aourwz/zeekr_custom/issues",
  "iot_class": "cloud_polling",
  "loggers": ["custom_components.zeekr_custom"],
  "requirements": ["pycryptodome==3.23.0"],
  "version": "0.0.1"
}
```

- [ ] **Step 2: 验证 JSON 合法**

`python -c "import json; json.load(open(r'D:\github\zeekr_custom\manifest.json'))"` 无报错。

---

### Task 1.11: 改 const.py — 删 device_tracker

**Files:**
- Modify: `D:\github\zeekr_custom\const.py:15-28`

- [ ] **Step 1: 替换 PLATFORMS**

现状:

```python
PLATFORMS = [
    "sensor",
    # "lock",
    # "climate",
    # "cover",
    "binary_sensor",
    "device_tracker",
    # "switch",
    # "button",
    # "select",
    # "update",
    # "number",
    # "text",
]
```

替换为:

```python
PLATFORMS = [
    "sensor",
    "binary_sensor",
    # 以下平台暂不启用(本期 read-only,用户不需要 GPS):
    # "device_tracker", "lock", "climate", "cover", "switch",
    # "button", "select", "update", "number", "text",
]
```

- [ ] **Step 2: 验证**

Read const.py,确认 PLATFORMS 列表只有 2 项激活(sensor、binary_sensor)。

---

### Task 1.12: 删除 device_tracker.py + number.py

**Files:**
- Delete: `D:\github\zeekr_custom\device_tracker.py`
- Delete: `D:\github\zeekr_custom\number.py`

- [ ] **Step 1: 删除文件**

```powershell
Remove-Item D:\github\zeekr_custom\device_tracker.py -Force
Remove-Item D:\github\zeekr_custom\number.py -Force
```

- [ ] **Step 2: 验证**

```powershell
Test-Path D:\github\zeekr_custom\device_tracker.py
Test-Path D:\github\zeekr_custom\number.py
```

两个都应输出 `False`。

---

### Task 1.13: 加密码学/签名烟测(本机 import 检查)

**Files:**
- 不修改任何文件,只验证 imports 不破

- [ ] **Step 1: 用 Python 跑 syntax + import 烟测**

```powershell
cd D:\github\zeekr_custom
C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall -q . -x "tmp_.*|__pycache__|docs|tools"
```

Expected: 无输出(`compileall` 成功时静默)。如果有 SyntaxError,会打印对应文件行号——回到出错的 Task 修。

- [ ] **Step 2: 检查 zeekr_api 模块独立可 import**

```powershell
cd D:\github\zeekr_custom
python -c "import sys; sys.path.insert(0, '.'); from zeekr_api import controller, client_main, client_old, client_new; print('OK')"
```

Expected: `OK`。如果有 ImportError 或 NameError,定位修。

> **注意**:HA 集成本身的 imports(如 `from homeassistant.config_entries import ...`)需要在真 HA 环境才能解析,本地 import 这些模块会 fail——所以**不要**对 `__init__.py`、`config_flow.py`、`sensor.py`、`base.py` 跑独立 import 测试。`compileall`(Step 1)能验证语法,这就够了。

---

## Phase 2: 部署到 HA

> 用户操作 + Claude 验证。Phase 2 的所有 task 都需要用户在浏览器内操作,Claude 等待回报。

---

### Task 2.1: 用户装 Samba addon

- [ ] **Step 1: 用户在 HA 浏览器**

操作路径:
1. Settings → Add-ons → Add-on Store
2. 搜索 "Samba share"(官方,蓝色图标)
3. 点 Install,等待 ~2 分钟
4. 装完后点 Configuration tab,设置 username 和 password(记好,Windows 端用)
5. 切回 Info tab,Start 按钮,等 status 变 "Started"

- [ ] **Step 2: 用户回报**

用户告诉 Claude:Samba 已 Started,用户名/密码是 `<U>` / `<P>`(实际不要把密码贴对话里,可以发"装好了,凭据已记下")。

---

### Task 2.2: 用户挂 Z:\

- [ ] **Step 1: Windows 文件资源管理器**

1. 按 Win+E 打开资源管理器
2. 左侧 "此电脑" → 顶部菜单"映射网络驱动器"
3. 驱动器选 **Z:**
4. 文件夹输 `\\homeassistant.local\config`(若解析不了,用 IP,比如 `\\192.168.x.x\config`)
5. 勾选 "登录时重新连接"、"使用其他凭据"
6. 点完成,弹凭据框,输 Task 2.1 的 username/password
7. 看到 Z: 盘出现,里面有 `home-assistant.log`、`configuration.yaml`、`automations.yaml` 等

- [ ] **Step 2: 用户回报**

用户回:"Z 已挂,能看到 home-assistant.log"。

---

### Task 2.3: Claude 验证 Z:\ 可访问 + 红线生效

- [ ] **Step 1: Claude 验证读权限(只在允许列表)**

```
Read Z:\home-assistant.log (只读前 50 行,确认 Samba 通)
Glob Z:\custom_components\zeekr_custom\*  (应该是空,因为还没拖代码;若已存在,提示用户先删旧版本)
```

- [ ] **Step 2: Claude 自检红线**

确认下面这些路径不主动 Read/Edit:
- `Z:\secrets.yaml`
- `Z:\configuration.yaml`
- `Z:\automations.yaml`
- `Z:\.storage\`
- 其他 `Z:\custom_components\<other>\`

memory `zeekr_ha_redline.md` 已固化,但每次 Read 前看一眼路径前缀。

---

### Task 2.4: 同步 Python 代码到 Z:\custom_components\zeekr_custom\

- [ ] **Step 1: Claude 用 PowerShell 复制(过滤 docs/、tools/)**

```powershell
$source = "D:\github\zeekr_custom"
$dest = "Z:\custom_components\zeekr_custom"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy $source $dest /MIR /XD docs tools __pycache__ tmp_chrome_profile* tmp_edge_profile* /XF tmp_*.* *.pyc 2>&1 | Tail-Object -Last 10
```

`robocopy` 参数:
- `/MIR` 镜像复制(目标 = 源)
- `/XD docs tools` 排除目录(spec 已说明只同步运行时代码 + 资产)
- `/XF tmp_*.*` 排除临时文件

- [ ] **Step 2: 验证**

```powershell
Get-ChildItem Z:\custom_components\zeekr_custom\ | Select-Object Name
```

Expected 输出:`__init__.py`、`base.py`、`binary_sensor.py`、`config_flow.py`、`const.py`、`coordinator.py`、`cover.py`、`manifest.json`、`sensor.py`、`translations\`、`zeekr_api\`、`www\`。

`device_tracker.py` 和 `number.py` 应**不存在**(Task 1.12 删除了)。

---

### Task 2.5: 同步 www 资产到 Z:\www\zeekr_7x\

- [ ] **Step 1: Claude 复制**

```powershell
$source = "D:\github\zeekr_custom\www\zeekr_7x"
$dest = "Z:\www\zeekr_7x"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy $source $dest /MIR 2>&1 | Tail-Object -Last 10
```

- [ ] **Step 2: 验证**

```powershell
Get-ChildItem Z:\www\zeekr_7x\ | Select-Object Name
Test-Path Z:\www\zeekr_7x\model\zeekr_7x.glb
```

第二个应该是 `True`。GLB 31MB,Samba 上传需要 30-60 秒,等完成。

---

### Task 2.6: 用户 Restart HA

- [ ] **Step 1: 用户在 HA 浏览器**

Settings → Developer Tools → 右上角 ⟲ → Restart Home Assistant → 弹窗 Confirm。等 1-2 分钟,UI 会断开重连。

- [ ] **Step 2: 用户回报**

回:"已重启,UI 回来了"。

---

### Task 2.7: Claude 检查启动日志

- [ ] **Step 1: 读 home-assistant.log 过滤 zeekr**

```
Grep "zeekr_custom|zeekr_api" Z:\home-assistant.log -A 2 (head 100 行)
```

预期看到:
- `Setup of domain zeekr_custom took N.N seconds`
- 没有 `Error` / `Traceback` 行(这时还没添加集成,只是模块加载)

- [ ] **Step 2: 如有 ImportError**

回 Phase 1 修对应 task。

---

### Task 2.8: 用户添加集成 + SMS 登录

- [ ] **Step 1: 用户操作**

1. Settings → Devices & Services → 右下角 + Add Integration → 搜 "Zeekr"
2. 选 "Zeekr Custom Integration"
3. 选 "使用手机号验证码验证"
4. 输手机号,点 Submit
5. 收到 SMS,输 6 位验证码
6. 选车辆(应该看到 7X 在列表里)
7. 提交完成

- [ ] **Step 2: 用户回报结果**

- 成功 → 进 Task 2.9
- A2 失败(SMS 没收到 / 验证码错误 / 接口拒) → 走附录 C(token 兜底,见 spec §C.1-C.3)。Claude 先帮用户测 `account.zeekrlife.com` 之类的 web 入口是否开放;若都不通,本期阻塞,通知用户

---

### Task 2.9: Claude 验证集成实体出现

- [ ] **Step 1: 读日志**

Grep `zeekr_custom` 找 "Created entity" / "Set up sensor" / "Added device" 行。

预期看到 ~30 行 entity 添加。

- [ ] **Step 2: 用户在 HA 浏览器确认**

Settings → Devices & Services → Zeekr Custom Integration → 1 device → 点进去看实体清单。
预期 ~30 个 sensor + binary_sensor。

---

## Phase 3: 阶段 A 验收(走 spec §5.1)

### Task 3.1: A1-A3 集成可用 + 实体出现

(Phase 2 已经完成 A1-A3,这里只是 checklist 确认)

- [ ] A1: 找到 "Zeekr Custom Integration" ✓
- [ ] A2: SMS 登录成功,看到 7X 在车辆列表 ✓
- [ ] A3: 1 device + ~30 entity ✓

### Task 3.2: A4 SOC + 续航有合理值

- [ ] **Step 1: 用户在 HA 浏览器**

Settings → Devices & Services → Zeekr → 点 device → 找 `battery_level`(SOC)和 `distance_to_empty_battery`(续航 km)。

- [ ] **Step 2: 验证数字合理**

- battery_level: 0-100 整数
- distance_to_empty_battery: 50-700 km 之间(7X 标称续航)

如果显示 `unknown`,可能是字段名不匹配(新车 API 返回的 JSON 跟代码假设不一致)。Claude 读日志找 `_vehicle_data` 完整结构,跟 `car.py` 的 property 对照修。

### Task 3.3: A5 30s 自动刷新

- [ ] **Step 1: 用户去 Developer Tools → States**

输入 `sensor.<id>_speed`,看 last_updated 字段。

- [ ] **Step 2: 等 30 秒,刷页面**

last_updated 时间戳应该往后推进 30s 左右。

### Task 3.4: A6 + A7 无 ERROR + 温度传感器各一个

- [ ] **Step 1: A6: 看日志**

Settings → System → Logs → 过滤框输 `zeekr_custom`。预期没有 ERROR 行(WARNING / INFO 可接受)。

- [ ] **Step 2: A7: 温度传感器**

Settings → Devices & Services → Zeekr → 实体清单搜 "temperature":
- 应该有 2 个:`temperature_inside` + `temperature_outside`
- 不应该有 1 个 / 名字怪(C1 修复验证)

如果只有 1 个,Task 1.1 没生效,回去重做。

---

## Phase 4: 2D + 3D 卡片部署

### Task 4.1: 加 2D 卡片(layered_example)

- [ ] **Step 1: 用户**

打开 HA Lovelace dashboard → 右上 ⋮ → "Edit dashboard" → "+ ADD CARD" → 滚到底 "Manual" → 复制 `D:\github\zeekr_custom\docs\lovelace_zeekr_7x_layered_example.yaml` 整段内容粘贴。

把 yaml 里所有占位符 `sensor.YOUR_ZEEKR_DISPLAY_STATE` 替换成实际 entity_id(用户在 Task 3.2 已经看到自己的实体名了,通常是 `sensor.<plate>_<vin>_display_state`)。

- [ ] **Step 2: 验证**

卡片显示 7X 主图(`base.png`),状态文字"已驻车"等。

### Task 4.2: B2/B3 状态切换验证

- [ ] **Step 1: 用户实操**

实车解锁、开门、上车,卡片图随状态切换:
- `parked` → `parked.png`
- `unlocked` → `unlocked.png`
- `door_open` → `door_open.png`
- `driving` → `driving.png`
- 等等

如果 8 状态切换不全,可能是 `display_state` 在 `car.py` 里的判断逻辑边缘 case——回 Phase 1 修。

### Task 4.3: 注册 3D 卡片 JS resource

- [ ] **Step 1: 用户**

Settings → Dashboards → 右上 ⋮ → "Resources" → "+ ADD RESOURCE":
- URL: `/local/zeekr_7x/zeekr-3d-card.js`
- Resource type: JavaScript Module

保存。

### Task 4.4: 加 3D 卡片(iframe_example)

- [ ] **Step 1: 用户**

回到 Lovelace,Edit → "+ ADD CARD" → "Manual" → 复制 `D:\github\zeekr_custom\docs\lovelace_zeekr_7x_3d_iframe_example.yaml`。改 entity_id。

- [ ] **Step 2: 强刷页面**

Ctrl+F5,等 GLB 加载(31MB,首次 5-15 秒)。看到 3D 7X 模型自动慢转。

### Task 4.5: C2/C3 状态联动验证

- [ ] **Step 1: 实车操作**

打开驾驶员车门,等 30s coordinator 刷新。

- [ ] **Step 2: HA 浏览器看 3D 模型**

模型对应那扇门转开,角度跟随车机上报的 doorPositions 数值。

- [ ] **Step 3: 充电场景**

如果不方便实操,Developer Tools → States → 找 `sensor.<id>_display_state` → 在右侧"Set state"输入 `charging` → Apply。3D 模型的充电口盖打开,左下 chip 显示充电中。

### Task 4.6: C4 看轮毂截图

- [ ] **Step 1: 用户**

把 3D 模型转到能看清侧面轮毂的角度,截图发给 Claude(粘贴到对话里)。

- [ ] **Step 2: Claude 比对**

跟 spec 附录 A 的参考图(银+黑双色 10 辐 + 橙铜卡钳 + ZEEKR logo)对比,决定:
- **路径 X**:GLB 自带 `20inch_duofuheiyao` 已经接近,只调材质(进 Task 5.1-5.3 简化版)
- **路径 Y-保守**:启用 `USE_REFERENCE_WHEEL = true`,微调材质 + 颜色 + ZEEKR logo(进 Task 5.1-5.5)
- **路径 Y-激进**:Y-保守效果不够,辐条形状改 ExtrudeGeometry(进 Task 5.6+)

---

## Phase 5: 轮毂迭代 + ZEEKR logo

### Task 5.1: 下载 Inter-Black 字体

- [ ] **Step 1: 创建 fonts 目录**

```powershell
New-Item -ItemType Directory -Force -Path "Z:\www\zeekr_7x\model\fonts" | Out-Null
```

- [ ] **Step 2: 下载字体(Claude WebSearch 找最稳的 mirror)**

Claude 用 `WebSearch` 搜 "Inter-Black.woff2 download font-display swap" 找一个可用 URL。常见来源:
- GitHub `rsms/inter` 仓库 release(主源)
- jsDelivr CDN 镜像 GitHub:`https://cdn.jsdelivr.net/gh/rsms/inter@master/docs/font-files/Inter-Black.woff2`
- unpkg / npm `@fontsource/inter` 子包

Claude 找到一个 working URL 后,用 PowerShell:

```powershell
$url = "<找到的 URL>"
Invoke-WebRequest -Uri $url -OutFile "Z:\www\zeekr_7x\model\fonts\Inter-Black.woff2" -UseBasicParsing
```

- [ ] **Step 3: 验证文件**

```powershell
Test-Path Z:\www\zeekr_7x\model\fonts\Inter-Black.woff2
(Get-Item Z:\www\zeekr_7x\model\fonts\Inter-Black.woff2).Length
```

预期:`True`、文件大小 30-80KB(.woff2 压缩后)。

- [ ] **Step 4: 兜底——若所有 mirror 都不可达**

跳过 .woff2 下载,改用 spec §4.4 方案 A(Web-safe 字体栈):Task 5.3 直接用 `'Arial Black', 'Helvetica', 'Liberation Sans', sans-serif`,跳过 Task 5.2 的 @font-face。后续效果若用户不满意,再补字体。

### Task 5.2: index.html `<head>` 加 @font-face

- [ ] **Step 1: 编辑 model/index.html**

打开 `Z:\www\zeekr_7x\model\index.html`,定位 `<head>` 下的 `<style>` 块开头(大约 line 10-20)。在 `<style>` 第一行后插入:

```css
@font-face {
  font-family: 'Inter';
  src: url('./fonts/Inter-Black.woff2') format('woff2');
  font-weight: 900;
  font-display: swap;
}
```

- [ ] **Step 2: 验证**

Read `Z:\www\zeekr_7x\model\index.html` 前 80 行,确认 `@font-face` 存在。

### Task 5.3: 改 ZEEKR logo 字体 + 字号

- [ ] **Step 1: 替换 line 964-968**

`Z:\www\zeekr_7x\model\index.html:964-968` 现状:

```js
        ctx.fillStyle = "rgba(225, 230, 235, 0.96)";
        ctx.font = "700 52px 'Segoe UI', 'Microsoft YaHei', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("ZEEKR", center, center + 2);
```

替换为:

```js
        ctx.fillStyle = "rgba(225, 230, 235, 0.96)";
        ctx.font = "900 56px 'Inter', 'Helvetica', 'Liberation Sans', sans-serif";
        ctx.letterSpacing = "2px";  // 注:Canvas 2D 不支持 letterSpacing 直接,Step 2 加备用
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("ZEEKR", center, center + 2);
```

- [ ] **Step 2: Canvas letterSpacing 兼容性 fallback**

Canvas 2D 在新版 Chrome/Edge(~2023+)支持 `ctx.letterSpacing`,旧浏览器忽略。如果用户用旧浏览器看不到字距,改用手动绘字:

```js
        ctx.fillStyle = "rgba(225, 230, 235, 0.96)";
        ctx.font = "900 56px 'Inter', 'Helvetica', 'Liberation Sans', sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        // 手动加字距:每个字符独立 fillText,间隔 2px
        const letters = "ZEEKR";
        const charWidth = ctx.measureText("M").width;
        const spacing = 2;
        const totalWidth = charWidth * letters.length + spacing * (letters.length - 1);
        let x = center - totalWidth / 2 + charWidth / 2;
        for (const ch of letters) {
          ctx.fillText(ch, x, center + 2);
          x += charWidth + spacing;
        }
```

如果第一种就够好,跳过这步。

### Task 5.4: 用户刷页面看 logo

- [ ] **Step 1: 用户**

HA Lovelace 强刷(Ctrl+F5),看 3D 模型轮毂中心的 ZEEKR 字样。

- [ ] **Step 2: 用户截图**

中心盘特写截给 Claude。

### Task 5.5: Claude 评估 + 微调字号

基于截图调:
- 字太小 → `56px` 改 `64px`
- 字太大 → 改 `48px`
- 字虚 → 增加 `ctx.shadowColor` + `ctx.shadowBlur`
- 颜色不对 → 调 `fillStyle` rgba

每次微调一行,用户刷页面,~3 轮收敛。

### Task 5.6: 启用 USE_REFERENCE_WHEEL(Y-保守路径)

(若 Task 4.6 决定走路径 Y。如果 X,跳到 Task 5.10)

- [ ] **Step 1: Edit `Z:\www\zeekr_7x\model\index.html:331`**

现状:

```js
const USE_REFERENCE_WHEEL = false;
```

改为:

```js
const USE_REFERENCE_WHEEL = true;
```

- [ ] **Step 2: 用户强刷,截图**

整个轮毂特写截给 Claude。

### Task 5.7: 调辐条颜色

基于截图反馈调:
- 银面太亮 → `silverFace` 的 color 从 `0xf0f3f6` 调暗到 `0xd6dbe0`
- 黑底太黑 → `darkBody` 的 color 从 `0x24292f` 调亮到 `0x3a4148`
- 卡钳橙调 → `CALIPER_COLOR = 0xc67a24` 改 `0xb8651f`(更深)或 `0xd4853a`(更亮)

每次改 1-2 个值,用户刷,迭代。

### Task 5.8: 调辐条 tip facet 形状(Y-保守 → Y-激进决策点)

如果 Task 5.7 完成后用户觉得辐条还是不像菱形:

- [ ] **Step 1: Y-激进:重写 buildReferenceSpoke**

打开 `Z:\www\zeekr_7x\model\index.html:739-790`,把 `BoxGeometry` 改成 `ExtrudeGeometry` + `Shape`:

```js
function buildReferenceSpoke(angle, outerRadius, isRightSide = false) {
  const spoke = new THREE.Group();
  const radialDistance = outerRadius * 0.57;
  const darkZ = isRightSide ? -0.014 : 0.014;
  const silverZ = isRightSide ? -0.032 : 0.032;

  // 菱形辐条横截面 Shape
  const shape = new THREE.Shape();
  const length = outerRadius * 0.76;
  const halfL = length / 2;
  const wide = 0.045;  // 中间宽
  const narrow = 0.018;  // 两端尖
  shape.moveTo(-halfL, 0);
  shape.lineTo(-halfL * 0.7, narrow);
  shape.lineTo(halfL * 0.7, narrow);
  shape.lineTo(halfL, 0);
  shape.lineTo(halfL * 0.7, -narrow);
  shape.lineTo(-halfL * 0.7, -narrow);
  shape.lineTo(-halfL, 0);

  const extrudeSettings = {
    depth: 0.045,
    bevelEnabled: true,
    bevelThickness: 0.005,
    bevelSize: 0.003,
    bevelSegments: 2,
  };

  const darkBody = new THREE.Mesh(
    new THREE.ExtrudeGeometry(shape, extrudeSettings),
    new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(0x24292f),
      metalness: 0.72,
      roughness: 0.28,
    }),
  );
  darkBody.position.set(Math.cos(angle) * radialDistance, Math.sin(angle) * radialDistance, darkZ);
  darkBody.rotation.z = angle;
  darkBody.castShadow = true;
  darkBody.receiveShadow = true;
  spoke.add(darkBody);

  // silver overlay 用同 shape 但更扁
  const silverShape = new THREE.Shape();
  silverShape.moveTo(-halfL * 0.95, 0);
  silverShape.lineTo(-halfL * 0.65, narrow * 0.6);
  silverShape.lineTo(halfL * 0.65, narrow * 0.6);
  silverShape.lineTo(halfL * 0.95, 0);
  silverShape.lineTo(halfL * 0.65, -narrow * 0.6);
  silverShape.lineTo(-halfL * 0.65, -narrow * 0.6);
  silverShape.lineTo(-halfL * 0.95, 0);

  const silverFace = new THREE.Mesh(
    new THREE.ExtrudeGeometry(silverShape, { ...extrudeSettings, depth: 0.018 }),
    new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(0xf0f3f6),
      metalness: 1,
      roughness: 0.18,
      clearcoat: 0.34,
      clearcoatRoughness: 0.12,
    }),
  );
  silverFace.position.set(Math.cos(angle) * radialDistance, Math.sin(angle) * radialDistance, silverZ);
  silverFace.rotation.z = angle;
  silverFace.castShadow = true;
  silverFace.receiveShadow = true;
  spoke.add(silverFace);

  return spoke;
}
```

- [ ] **Step 2: 用户刷,截图**

Y-激进效果出来,继续微调菱形宽度 / 长度比(`narrow`、`halfL * 0.7` 等魔数)。

### Task 5.9-5.X: 收敛迭代

每轮:
- Claude 看截图
- 调 1-2 个参数(辐条比例、颜色 hex、卡钳位置 / 旋转角度、center cap 大小)
- 用户刷
- ~3-5 轮收敛(Y-保守)/ 5-7 轮(Y-激进)

收敛标准:用户说 "OK,够像了"。

### Task 5.10: C5 视角验证

- [ ] **Step 1: 用户**

在 3D 卡片上点击拖动,视角能旋转;放手后自动慢转。

通过 → C5 ✓

---

## Phase 6: 阶段 D 兜底验证

### Task 6.1: D1 重启后实体不丢

- [ ] **Step 1: 用户 Restart HA**

Settings → Developer Tools → ⟲ Restart。等 1-2 分钟。

- [ ] **Step 2: 验证**

回 Devices & Services → Zeekr,1 device + ~30 entity 全在,值还在。

### Task 6.2: D2 拔线 30s

- [ ] **Step 1: 用户**

物理拔 HA 主机网线,等 30s,插回。

- [ ] **Step 2: 用户观察**

实体短暂变 unavailable(灰色),~30-60s 后恢复。**不应该弹 reauth 通知**(C2 修复验证)。

- [ ] **Step 3: Claude 看日志**

Grep `zeekr_custom` 看 30s 内的日志:
- 应有 `ConfigEntryNotReady` 风格的日志(C2 修对了)
- 不应有 `ConfigEntryAuthFailed` 或 reauth 触发

### Task 6.3: D3 删除集成 + 重新添加

- [ ] **Step 1: 用户**

Settings → Devices & Services → Zeekr → ⋮ → Delete。等几秒。

- [ ] **Step 2: 重新添加**

+ Add Integration → 重走 SMS 登录。

- [ ] **Step 3: 验证**

实体名跟之前一样(无 `_2` 后缀),无残留实体。

### Task 6.4: D4 1 小时观察

- [ ] **Step 1: 让 HA 自然跑 1 小时**

不操作。

- [ ] **Step 2: Claude 看日志**

Grep zeekr_custom 找 ERROR 行。预期为 0。

### Task 6.5: D5 reauth 链路 E2E(可选)

> **注意**:这步触碰 spec §2.4 红线列出的 `Z:\.storage\`。Claude **不直接动**,需要用户操作。
>
> **可选性**:如果用户不想为这一次测试再装新 addon,可以**跳过 D5**。reauth 链路会在真实 token 过期(通常几周到几月)时自然触发,届时观察是否符合预期即可。跳过 D5 的影响:本期不能 100% 证明 C3(reauth 流签名)修对了,但 C2(异常分流)修对的话,wrong-state 也只是"网络抖动不弹 reauth",不会反向坏事。

**两条路径,二选一:**

#### 路径 A:用户已有 Samba 访问 `.storage/`(测试一下能不能)

- [ ] **Step 1: Claude 探测**

```
Glob Z:\.storage\* → 看是否能列出 `core.config_entries`
```

如果能,Samba addon 没限制 `.storage`,用户可以用 Windows 文件资源管理器打开:

`Z:\.storage\core.config_entries` (这是个 JSON 文件,记事本能开)

但 **Claude 不读 / 不写这个文件**(红线)。仅指导用户操作。

- [ ] **Step 2: 用户用 Notepad++(或 VS Code)打开**

搜索 `"domain": "zeekr_custom"`,定位到 `data` 节点,把 `access_token` 字段值前面加一段乱字符(比如 `eyXXXXXXXX...` 改成 `INVALIDeyXXXXXXXX...`),保存。

> ⚠️ **保存前先备份这个文件**(复制到桌面),万一改坏了好回滚。

#### 路径 B:Samba 不能访问 `.storage/`,用户装 File editor addon

- [ ] **Step 1: 用户装 File editor**

Add-on Store → File editor → Install + Start(2 分钟)。

- [ ] **Step 2: 用 File editor 在 HA UI 内打开**

侧边栏点 File editor → 文件树 → `.storage` → `core.config_entries` → 编辑同 Step 2 路径 A。

#### 共同的验证步骤(无论 A 或 B)

- [ ] **Step 3: 用户 Restart HA**

Settings → Developer Tools → ⟲ Restart。

- [ ] **Step 4: 验证 reauth 流触发**

- HA 通知中心(铃铛图标)应弹通知:"Zeekr 集成需要重新认证"
- 点通知 → 弹 reauth_confirm 表单(显示"{mobile} 的 token 已失效..."的中文文案,Task 1.6 加的翻译)
- 用户点 Submit → 走 SMS 验证码流程 → 重新认证
- 完成后 entry 恢复,实体不丢、值正常

通过 → D5 ✓ → 全部验收完成。

---

## 收尾

### Task 7.1: 用户清理 yaml 残留(C4 后续)

- [ ] **Step 1: 用户**

如果 `configuration.yaml` 里还有 `zeekr_custom:` 块(YAML 入口已删除),提示用户删除该块。Claude 不读 configuration.yaml(红线),只让用户自检。

### Task 7.2: 决策日志补充

- [ ] **Step 1: Claude 在 spec 附录 B 加一行**

记录本次实施过程中的关键决策(如:轮毂走了 Y-保守 / Y-激进 / X、字体 Inter / Liberation Sans、SMS 一次成功 / 走 token 兜底)。

---

## 自检清单(实施完成时检查)

- [ ] 4 个 critical 全过(C1 温度双实体存在 / C2 拔线不弹 reauth / C3 D5 reauth E2E 通过 / C4 async_setup 不存在)
- [ ] 6 个 high 全过(H1 401 触发 reauth / H2 base.py assert 在 / H3 unload 容错 / H4 refresh 不抛 TypeError / H5 manifest 完整 / H6 controller 有 _auth_lock)
- [ ] 验收阶段 A1-A7 全 pass
- [ ] 验收阶段 B1-B3 全 pass
- [ ] 验收阶段 C1-C5 全 pass
- [ ] 验收阶段 D1-D5 全 pass
- [ ] 用户对轮毂效果满意
- [ ] 日志连续 1 小时 zero ERROR

---

## 自检(plan 内部一致性,实施前看)

**Spec coverage** — 每个 spec §3.1/§3.2 修复条目都有 task 实现:
- C1 → Task 1.1 ✓
- C2 → Task 1.3 ✓
- C3 → Task 1.6 ✓
- C4 → Task 1.4 ✓
- H1 → Task 1.7 ✓
- H2 → Task 1.2 ✓
- H3 → Task 1.5 ✓
- H4 → Task 1.8 ✓
- H5 → Task 1.10 ✓
- H6 → Task 1.9 ✓
- 文件清理 → Task 1.11 + 1.12 ✓
- 部署 → Phase 2 ✓
- 阶段 A 验收 → Phase 3 ✓
- 阶段 B 验收 → Task 4.1-4.2 ✓
- 阶段 C 验收 → Task 4.3-4.6 + 5.10 ✓
- 阶段 D 验收 → Phase 6 ✓
- 轮毂(路径 Y-保守 / Y-激进)→ Task 5.6-5.9 ✓
- ZEEKR logo + 字体 → Task 5.1-5.5 ✓
- token 兜底(附录 C)→ Task 2.8 Step 2 引用 ✓

**类型一致性** — `_auth_lock`、`async_step_reauth_confirm`、`USE_REFERENCE_WHEEL`、`buildReferenceSpoke`、`type` 等命名在 plan 内多处出现,逐一核对一致。

**Placeholder scan** — 全文无 TBD / TODO 占位(注释 `# TODO` 是源代码已有不算)。

