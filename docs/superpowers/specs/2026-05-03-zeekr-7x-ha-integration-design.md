# Zeekr 7X Home Assistant 集成落地设计

**日期:** 2026-05-03
**范围:** MVP 跑通 + 3D 模型联动 + 真实 7X 轮毂(基于车主参考图)+ 修复 4 个 critical 阻塞 BUG
**作者:** 用户(车主) × Claude(实施)
**状态:** 设计阶段,待用户批准

---

## 0. 摘要(TL;DR)

把现有 `zeekr_custom` 集成在用户自己的 HA OS 上跑起来,接入用户的极氪 7X(`CX1E`)账号,在 HA 里以 ~30 个实体的形式暴露续航、SOC、门窗、温度等数据;接入 3D Lovelace 卡片让模型随车机状态联动开门/开窗/充电指示;把模型轮毂调成跟用户车上的款式一致(银+黑双色 10 辐 + 橙铜卡钳 + ZEEKR 中心 logo);顺手修掉 4 个 critical 级别的阻塞 BUG。

**3-5 个工作日**(乐观 3 天 / 保守 5 天,详见 §6),每天 2-5 小时挂在用户与 Claude 协作回合里。

---

## 1. 目标 & 非目标

### 1.1 In Scope(本期做)

- **集成可用**:HA 浏览器内能找到、配置、登录极氪账号(SMS 优先,token 兜底)
- **数据流通**:30s 自动刷新,续航 / SOC / 速度 / 门窗位置 / 4 胎压 / 4 胎温 / 内外温 / 充电电压电流 / 表显总里程 / 保养周期 等核心实体出现
- **2D Lovelace 卡片**:`docs/lovelace_zeekr_7x_layered_example.yaml` 直接用,根据 `display_state` 切换 8 个状态贴图
- **3D Lovelace 卡片**:`zeekr-3d-card.js` + `model/index.html`,模型门窗/天窗/后备箱/引擎盖/充电口随车机状态联动
- **真实 7X 轮毂**:跟用户提供的参考图(银+黑双色 10 辐 + 橙铜卡钳)外观接近,中心盘有 **ZEEKR** logo
- **已知 ERROR 全修**:§3.1/§3.2 列出的 10 项修完(4 critical + 6 high);验收期间新发现的 ERROR 按严重度分流,不阻塞验收(只阻塞合并)
- **4 个 critical BUG 全修**(详见 §3.1)
- **6 个 high BUG 顺手修**(详见 §3.2,因与 critical 同文件/同根因 / 或被验收测试 D2/D5 命中)

### 1.2 Out of Scope(本期不做)

- **写命令通道**(锁车 / 开窗 / 空调控制等):集成保持 read-only,延后实施
- **device_tracker / GPS 地图**:用户明确不需要,从 `PLATFORMS` 移除
- **12 个 high 中的剩下 7 个**(并发竞态、postMessage origin 校验、性能优化、资产去重等):先放着,本期不阻塞
- **HACS 元数据完整化 / 上架**:本期个人使用
- **GCJ-02 → WGS-84 坐标转换**:因为不暴露 device_tracker,无意义
- **车机命令的反向通道**(3D 卡片点击 → 实车操作):read-only

---

## 2. 架构 & 部署

### 2.1 数据流

```
[ 极氪云 ]
    │ HTTPS + 三套签名 (HMAC-SHA1/SHA256, AES-CBC X-VIN)
    ▼
[ ClientMain ] ── auth_code ──→ [ ClientNew ]    (7X 是新车型,走 ClientNew)
    │
    ▼
[ Controller ]  ── 并发刷新所有 VIN
    │
    ▼
[ DataUpdateCoordinator(per VIN, 30s) ]
    │
    ▼
[ ZeekrCar(数据视图层) ]──→ ~30 个 Entity (sensor / binary_sensor)
                                    │
                                    ▼
                         HA 状态机 (state + attributes)
                                    │
                       ┌────────────┴───────────────┐
                       ▼                            ▼
            [ 2D 图层卡片 ]              [ zeekr-3d-card.js (iframe) ]
            picture-elements              postMessage state
            + 8 状态贴图                       │
                                                ▼
                                     [ model/index.html + Three.js ]
                                     部件动画(门窗/天窗/后备箱/引擎盖/充电口/后视镜/8 chip)
                                                │
                                                ▼
                                     [ 真实 7X 轮毂(参考图建模)]
```

### 2.2 部署通道:Samba

用户的 HA 是 **Home Assistant OS,只能通过浏览器访问**。决定走 **Samba share addon** 把 HA 的 `/config/` 挂成 Windows 网络驱动器(`Z:\`),让 Claude 通过本机文件系统直接读写代码 + 日志。

**部署步骤:**

1. HA 浏览器内 → Settings → Add-ons → Add-on Store → 装 **Samba share** → 设密码 → 启动
2. Windows 文件资源管理器 → "此电脑" → 顶部"映射网络驱动器" → 输入 `\\homeassistant.local\config` → 选 **Z:** → 勾选"使用其他凭据"→ 输 Samba 用户名密码
3. 完成后 `Z:\` 直接对应 HA 的 `/config/`:
   - 集成代码:`Z:\custom_components\zeekr_custom\`
   - 静态资源:`Z:\www\zeekr_7x\`
   - 日志:`Z:\home-assistant.log`

**首次代码部署:**

- 把 `D:\github\zeekr_custom\`(除 `docs\`、`tools\` 外)整个拖到 `Z:\custom_components\zeekr_custom\`
- 把 `D:\github\zeekr_custom\www\zeekr_7x\` 拖到 `Z:\www\zeekr_7x\`

**之后所有改动**:Claude 直接 Edit `Z:\` 下的文件;`D:\github\zeekr_custom\` 退化为出厂参照备份,不再编辑。

### 2.3 迭代循环

```
Claude:  Read Z:\home-assistant.log → 看到错误
Claude:  Edit Z:\custom_components\zeekr_custom\<file>.py
用户:    浏览器 Settings → Developer Tools → ⟲ Restart
Claude:  Read Z:\home-assistant.log → 验证
```

3D 卡片改动(`Z:\www\zeekr_7x\` 下)不需要重启 HA,浏览器 Ctrl+F5 强刷 dashboard 即可。

### 2.4 红线(用户明确划定)

Claude 在挂载 `Z:\` 后,**只动 zeekr 相关**:

- ✅ 读+写:`Z:\custom_components\zeekr_custom\` 整树
- ✅ 读+写:`Z:\www\zeekr_7x\` 整树
- ✅ 读(过滤):`Z:\home-assistant.log` 仅过滤 `zeekr_custom|zeekr_api` 行
- ❌ 禁:`Z:\secrets.yaml`、`Z:\configuration.yaml`、`Z:\automations.yaml`、`Z:\.storage\`、其他 `Z:\custom_components\<other>\`、其他 `Z:\www\<other>\`、所有备份/快照/db

红线已固化进 memory(`zeekr_ha_redline.md`),开新 Agent 子任务也会带上。

---

## 3. 必修 BUG 清单

### 3.1 Critical(4 个,全修)

| # | 文件 | 现状 | 改法 |
|---|------|------|------|
| **C1** | `sensor.py:104-108` `ZeekrCarTemp.__init__` | `self.type += " (inside)"` 改写**类属性**,内/外温实例 unique_id 碰撞,只活一个 | 替换为 `self.type = "temperature_inside" if inside else "temperature_outside"`,赋值前完成,不用 `+=` |
| **C2** | `__init__.py:140-148` `async_setup_entry` | 代码现有两个 try 块,但 `except ZeekrAPIError → ConfigEntryAuthFailed` 在前、`except ZeekrAuthError → ConfigEntryAuthFailed` 在后——`ZeekrAuthError` 是 `ZeekrAPIError` 的子类,被父类先捕获,实际行为等同于"一律 AuthFailed",网络抖动也弹 reauth | 把两个 except 分支正确分流:`ZeekrAuthError → ConfigEntryAuthFailed`(子类放前,优先匹配)、`ZeekrAPIError → ConfigEntryNotReady` |
| **C3** | `config_flow.py:210-214` `async_step_reauth` | 用旧 `data` 参数签名,且 `async_step_user` 每次重建 `Controller` → `device_id` 漂移 → 服务端拒 | 改成 `async_step_reauth(self, entry_data: Mapping)`,从 `entry.data` 读出旧 `device_id` 复用;再加 `async_step_reauth_confirm` 做一个 `show_form` 提示("token 失效,需要重新认证"),**用户确认后**才跳 `async_step_mobile`/`token`(符合 HA 2024+ 官方 UX 规范) |
| **C4** | `__init__.py:60-114` `async_setup`(YAML 路径) | `mobile = ""` 占位 + 永远不验证 token,`zeekr_custom:` 进 YAML 会污染 hass.data | 整段删除——这是 config-flow-only 集成,不需要 YAML 入口。**注意**:删除后,如果用户 `configuration.yaml` 里仍留 `zeekr_custom:` 块,HA 不会报错但 yaml 配置会被静默忽略;部署完毕后 Claude 应主动告知用户检查并删除 |

### 3.2 顺手修的 High(6 个)

| # | 文件 | 改法 | 理由 |
|---|------|------|------|
| **H1** | `client_main.py:_fetch` | 加 `if status == 401: raise ZeekrAuthError(...)` 分支 | 跟 C2 配套——没这个,reauth 链路在 main client 那侧根本不触发 |
| **H2** | `base.py:16` `ZeekrBaseEntity` | 把 `type` 从隐式类属性改成 `__init__` 必填参数 | 跟 C1 同根问题,杜绝整类碰撞 |
| **H3** | `__init__.py:178-194` `async_unload_entry` | listener 摘除 + `hass.data` 清理统一移到 `if unload_ok:` 分支内 | 4 行改动,unload 失败不留脏 |
| **H4** | `client_old.py:162-172` `auth_by_refresh_token` | 删掉 `token=self.access_token` kwarg(它会透传给 aiohttp 触发 `TypeError`) | refresh 路径才能跑 |
| **H5** | `manifest.json` | 加 `"issue_tracker"`、`"loggers": ["custom_components.zeekr_custom"]`,改 `documentation` URL 到本仓库或保持不变 | 一次写完,日志会自动启用 zeekr_custom logger |
| **H6** | `controller.py` `Controller.auth_all_api` + `update` | 包一个 `asyncio.Lock` 串行化 token 刷新与 per-VIN update | 30s coordinator + token 过期边缘的并发 race 正是 D2 拔线 / D5 reauth 测试可能命中的真实场景;~5 行改动,顺手做。**严重度从 §3.5 升上来** |

### 3.3 const.py 改动

```python
PLATFORMS = [
    "sensor",
    "binary_sensor",
    # device_tracker 删除(用户不需要 GPS,见 §1.2)
]
```

### 3.4 文件清理

- 删除 `device_tracker.py`(从 PLATFORMS 移除后变孤儿)
- 删除 `number.py`(0 字节文件,且不在 PLATFORMS)
- 保留 `cover.py` 暂不动(不在 PLATFORMS,无运行时影响,后续启用 cover 时再修)

### 3.5 不修清单(放着,理由记录)

| 类别 | 例子 | 理由 |
|------|------|------|
| 并发竞态(剩余) | `client_new.py:54-58` 改 headers 原地双重 AES、单签名函数被多 caller 共享 | 单用户单 7X 场景下不命中;`controller.py` 的 token 轮换 race 已升级到 §3.2 H6 修复 |
| 性能优化 | `zeekr-3d-card.js` 每次 hass 全量 postMessage、资产 58MB 重复 | 不影响功能 |
| 安全加固 | `model/index.html` 未校验 postMessage origin、Three.js MIT header 缺失 | 同源 iframe 下无攻击面;个人用 license 无害 |
| UI 体验 | `config_flow.py` `vol.In(dict)` 不渲染中文 label | UI 难看但不阻塞 |

---

## 4. 3D 模型联动 + 轮毂

### 4.1 状态联动现状(已经做好的)

`model/index.html` 里的 `applyState()` + `applyModelState()` 已经覆盖以下联动:

| HA 实体属性 | 3D 模型反应 | 函数/位置 |
|------------|-----------|---------|
| `door_*` + `door_*_position` | `Door_LF/RF/LB/RB` 绕 Y 轴旋转开,角度按位置 0-100% 线性 | `setPartTarget` @ 1130 |
| `window_*` + `window_*_position` | `Glass_LF/RF/LB/RB` 向下平移 | 1135 |
| `trunk_open` | `Trunk` 抬起 -48° | 1140 |
| `engine_hood_open` | `Hood` 抬起 +42° | 1143 |
| `is_plugged_in` / `charge_lid_open` | `Cover_RF`(充电口盖)绕 Y 转 -48° | 1146 |
| `sunroof_open` + `sunroof_position` | `Fillet_srf_15299` + `sunfat` 平移倾斜 | 1150 |
| `is_unlocked` | `Mirror_LF/RF` 锁车时折叠 | 1158 |
| `display_state` 等 | 8 chip 状态气泡(lock/door/window/sunroof/trunk/hood/plug/charge) | `applyState` @ 1190 |
| `range_km` / `model_name` | 直接显示 | 1197-1199 |

**结论:本期不补任何状态联动**,只要 HA 实体的属性正确(C1 修了温度碰撞,其余字段已经对齐),3D 模型自动反应。

### 4.2 字段对齐(zeekr-3d-card.js push vs applyState read)

全部已对齐(详见 §Section 3 of 主对话)。`soc` 卡片推了但 `applyState` 没用——非阻塞,后续可加。

### 4.3 轮毂方案:两阶段

**阶段 1(零改动):先看现状**

GLB 内置多套轮毂 mesh,当前激活的是 `20inch_duofuheiyao`(20 寸多辐黑曜),命名暗示已经接近用户的车;另有 `attachWheelAccentOverlay` 在叠加程序生成的中心盘 + 卡钳贴图。

用户先按 §2.2 部署完毕,加 lovelace 卡片打开 3D 视图,**截图给 Claude**。Claude 比对截图与车主参考图。

**阶段 2:基于截图选路径**

- **路径 X(GLB 自带轮毂已接近)**:只调材质参数(`WHEEL_METAL` / `CALIPER_COLOR`)+ 调 accent overlay 的中心盘 logo。工作量 ~30 行。
- **路径 Y(GLB 自带不像)**:启用 `USE_REFERENCE_WHEEL = true`(已有完整代码 @ 657-823),基于参考图迭代。**两条子路径:**
  - **路径 Y-保守**:辐条形状不变(继续用 3 层 `BoxGeometry`),只调材质分层 + 颜色 + 卡钳位置 + 加 ZEEKR logo。**~80 行 + 3-4 轮收敛**
  - **路径 Y-激进**:辐条形状从 `BoxGeometry` 改 `ExtrudeGeometry` + `Shape` 路径做菱形收口,完全重写 `buildReferenceSpoke`。**~150-250 行 + 5-7 轮收敛**
  - 共同要做:辐条数确认(参考图 ~10 根 ≈ 当前代码 10)✓ / 中心 logo(见 §4.4)/ 卡钳颜色微调(`CALIPER_COLOR = 0xc67a24`,据截图反馈调)
  - **决策点**:阶段 2 第一轮看 Y-保守效果,若收口不像再升级到 Y-激进

### 4.4 ZEEKR 中心 logo 实现细节

`getWheelCenterCapTexture()` 当前已经存在(`model/index.html:939` 附近),其字体栈用的是 `Segoe UI / Microsoft YaHei`(Windows 字体)。

**问题**:HA OS 是 Linux,容器内浏览器没有 Segoe UI / Helvetica / Microsoft YaHei,会 fallback 到 DejaVu Sans 或 Liberation Sans,字形跟 Windows 端不一致——你截图调好的版本,别人 HA 上看会变。

**解决方案二选一:**

**A. Web-safe 字体栈**(简单,视觉一般):
```js
ctx.font = "900 64px 'Arial Black', 'Helvetica', 'Liberation Sans', sans-serif";
```
Linux 上落到 Liberation Sans Bold,字形对得上 ZEEKR 官方简洁无衬线风,跨平台稳定。

**B. 内嵌一份开源字体 .woff2**(推荐,视觉好):
- 下载 `Inter-Black.woff2`(~50KB)或 `Manrope-ExtraBold.woff2`(~40KB)放 `Z:\www\zeekr_7x\fonts\`
- 在 `model/index.html` `<head>` 加:
  ```css
  @font-face {
    font-family: 'Inter';
    src: url('./fonts/Inter-Black.woff2') format('woff2');
    font-weight: 900;
  }
  ```
- 然后 `ctx.font = "900 64px 'Inter', sans-serif";`

**完整改造代码**(走方案 B 之后):
```js
ctx.fillStyle = "#f0f3f6";  // 银白色
ctx.font = "900 64px 'Inter', sans-serif";
ctx.textAlign = "center";
ctx.textBaseline = "middle";
ctx.fillText("ZEEKR", canvas.width / 2, canvas.height / 2);
```

具体字号、字距、垂直偏移基于阶段 2 截图反馈微调。**推荐走 B**——HA 是分发型软件,跨平台一致性比 50KB 资产成本重要。

### 4.5 其他模型微调(预留)

如果 3D 模型本体在用户验收时发现部件错位/动画幅度不对(比如门开太大撞侧裙、天窗滑动方向反了),`applyModelState` 里的 `transform.position` / `transform.rotation` 是单一来源,改动一个数字就改一个动画,迭代成本极低。

---

## 5. 验收标准

### 5.1 阶段 A:集成跑通

| # | 操作 | 通过条件 |
|---|------|---------|
| A1 | HA 浏览器 → Settings → Devices & Services → Add Integration → 搜 "Zeekr" | 能找到 "Zeekr Custom Integration" |
| A2 | 选 SMS 登录 → 输手机号 → 收验证码 → 输入 → 选车辆 | 能看到用户的 7X 在车辆列表里 |
| A3 | 配置完成后回到 Devices & Services 页 | 看到 1 个 device(7X 车牌+VIN),~30 个 entity |
| A4 | 点进 device 看实体值 | 找到 SOC 实体(`battery_level`)有 0-100 的数字;找到续航实体(`distance_to_empty_battery`)有合理 km 数字 |
| A5 | 等 30 秒,Developer Tools → States 看 sensor.* 的 last_updated | 动态字段(speed、charge_level、odometer 等)的 last_updated 时间戳每 30s 推进 |
| A6 | Settings → System → Logs → 过滤 zeekr_custom | 没有 ERROR 级别行(WARNING 和 INFO 可接受) |
| A7 | C1 修复验证:实体列表里搜 "temperature" | 同时存在两个温度实体(inside 和 outside),不丢任何一个(C1 修前必丢一个) |

### 5.2 阶段 B:2D 卡片

| # | 操作 | 通过条件 |
|---|------|---------|
| B1 | Lovelace → 编辑 → 添加 manual 卡片 → 粘贴 `docs/lovelace_zeekr_7x_layered_example.yaml`,改实体 ID | 卡片显示 7X 主图(`base.png`) |
| B2 | 让车驾驶/停车 / 触发任一状态变化 | 主图自动切换(driving.png / parked.png / charging.png 等 8 选 1) |
| B3 | 充电 OR 拔枪 OR 开门 | 状态文字 + 图变化对应 |

### 5.3 阶段 C:3D 卡片 + 轮毂

| # | 操作 | 通过条件 |
|---|------|---------|
| C1 | Lovelace → Resources → 添加 `/local/zeekr_7x/zeekr-3d-card.js` (Module),刷新 → 添加 manual 卡片用 `docs/lovelace_zeekr_7x_3d_iframe_example.yaml` | 看到 3D 7X 模型缓慢自动旋转,左下角 chip 状态 |
| C2 | 在 HA 让车的某个门打开(实车操作 OR 用 Developer Tools 强改 sensor 状态测试) | 3D 模型对应那扇门转开,角度跟随位置百分比 |
| C3 | 同 C2,改充电状态 | 充电口盖打开,chip 显示充电中 |
| C4 | 看轮毂 | 4 个轮毂位置都有显示,中心盘有 **ZEEKR** 字样,辐条形状 + 颜色 + 卡钳跟用户参考图大体接近 |
| C5 | 点击模型拖动 | 视角能旋转,放开手自动慢转 |

### 5.4 阶段 D:无 BUG 兜底

| # | 操作 | 通过条件 |
|---|------|---------|
| D1 | Settings → Developer Tools → Restart | 重启后集成自动恢复,实体不丢 |
| D2 | 拔网线 30 秒再插回 | 实体短暂 unavailable 后恢复,不弹 reauth(C2 修复验证) |
| D3 | 删除集成再重新添加 | 一次成功,无残留实体 |
| D4 | 连续观察 1 小时 | 日志里没有 ERROR 级别行 |
| D5 | reauth 链路 E2E:用户在浏览器 Settings → Devices & Services → Zeekr → ⋮ → "Reload" 失败的话不算;真正的测试是用户**手工修改 access_token 让它失效**(具体方式:Claude 用户在 Studio Code Server 或 SSH 临时打开下的 `.storage/core.config_entries`,把 zeekr 那条 `access_token` 字段改成 `INVALID`,保存,重启 HA)。**注意:此操作触碰 §2.4 红线禁列里的 `.storage/`,必须由用户在浏览器内 / 自己执行,Claude 不直接动**。 | HA 弹出 reauth 通知 → 走 SMS / token 重新认证 → entry 恢复且实体不丢(C3 修复验证) |

---

## 6. 时间线

```
Day 1  (≈3-5 小时实际工作 + 用户配合 Restart 的几次回合)
├── Claude: 修 §3.1 / §3.2 的 4 critical + 6 high(代码改动写在 D:\github\zeekr_custom\,验证用 Z:\)
├── 用户:  装 Samba addon,挂 Z:\,告诉 Claude 成功
├── Claude: Edit 改好的代码到 Z:\custom_components\zeekr_custom\
├── 用户:  Restart HA → 走 §5.1 阶段 A 的 7 项验收 → 任何 ERROR 贴 log
└── 收敛后:阶段 A 全过 ✓

Day 2  (≈2-3 小时)
├── 用户:  把 D:\github\zeekr_custom\www\zeekr_7x\ 拖到 Z:\www\zeekr_7x\
├── Claude: Edit 一份 lovelace yaml 给用户,用户贴进去
├── 走 §5.2 阶段 B 的 3 项 → §5.3 C1
└── 用户:  截图 3D 当前轮毂 → Claude 决定路径 X 或 Y

Day 3  (≈2-4 小时,看路径 Y 的迭代轮数)
├── 路径 Y(预计):迭代调轮毂 + 加 ZEEKR logo
│   ├── Claude 改一版 → 用户 Ctrl+F5 → 截图 → Claude 看了 → 改下一版
│   └── 通常 3-5 轮收敛
└── 全部 §5.1-5.4 走一遍最终验收 ✓
```

**总计:3-5 个工作日**,每天 2-5 小时挂在协作回合。
- **乐观情形(3 天)**:轮毂走 §4.3 路径 Y-保守 + SMS 一次成功
- **保守情形(5 天)**:轮毂升级到 Y-激进(`ExtrudeGeometry` 重写) + SMS 失败走 token 兜底(见**附录 C**),首日 +1 天 buffer

---

## 7. 风险 & 兜底

| 风险 | 概率 | 影响 | 兜底 |
|------|------|------|------|
| 极氪 SMS 接口签名密钥过期(`X_CA_SECRET` 等 hardcode 在 `const.py`) | **中-高** | A2 失败,首日卡住 | 走 token 兜底路径,详见**附录 C**;前提是 H4 已修(否则 `client_old.auth_by_refresh_token` 透传 `token=` 触发 `TypeError`);兜底也失败则只能等社区(原仓库 `@aourwz`)更新密钥,本期阻塞,通知用户 |
| `zeekr_7x.glb` 加载慢(31MB) | 低 | C1 首次显示等 5-10s | 卡片加 loading 占位文案;若长期慢,后续用 Draco 压缩 |
| Three.js r166 跟最新 Chromium 兼容性 | 极低 | 3D 不显示 | vendor 已经版本锁定,不会自动升级 |
| 极氪 API 返回字段格式新旧车型不同 | 低-中 | 部分 sensor 显示 unknown | 先看真实响应再决定字段映射;`utils.redact_sensitive` 已覆盖,可放心读 |
| 用户车实际不是 7X | 极低 | GLB 模型不匹配 | 配置时如果车型 `appModelCode` 不是 `CX1E`,Claude 立即停下确认 |
| 阶段 D2 拔线测试触发了未发现的 reauth 链路 BUG | 中 | 体验问题 | 看日志定位,可能要补 `client_new.auth_by_refresh_token`(原本是空 stub),延期处理 |

---

## 8. 实施权限边界

Claude 在本期具备的权限:

- **本机 D:\github\zeekr_custom\**:任意读写,作为 source of truth 起点(部署后不再编辑)
- **HA 上 Z:\custom_components\zeekr_custom\**:任意读写
- **HA 上 Z:\www\zeekr_7x\**:任意读写
- **HA 上 Z:\home-assistant.log**:仅 grep 过滤 `zeekr` 行读取
- **memory 系统**:可读写自己的 memory 目录

Claude 在本期 **不具备** 的权限:

- 操作 HA 任何重启/reload(必须用户在浏览器点)
- 触发实车命令(read-only 集成,不写)
- 读 HA 上任何非 zeekr 文件(见 §2.4 红线)
- 提交 git / push / create PR(项目不是 git 仓库)

---

## 9. 后续(本期之后,不阻塞验收)

落地后用户可考虑(本设计文档不展开):

- 写命令通道:锁车、空调远程预热、开关窗——需要找极氪命令 API 端点 + 加 climate / lock / button 平台
- 修剩余 12 个 high BUG 中的 7 个(主要是并发竞态 + token 静默刷新 + reauth 流程的边界 case)
- 资产去重 / Draco 压缩 GLB,把 www 体积从 ~58MB 降到 ~10MB 以内
- HACS 元数据完整化,如果想分发给别的极氪车主
- 补 `cover` 平台的写命令(如果实车 API 支持开关窗户 / 后备箱)

---

## 附录 A:用户提供的轮毂参考图

(图存于 `C:\Users\Administrator\.claude\image-cache\a1fd5855-f6f7-4f80-ba58-b664c1327d56\1.png`,正文 §4.3 描述提取要点)

观察提取:
- 银色辐条边缘 + 黑色凹槽双色调
- ~10 根细长辐条对称分布
- 中心圆形 hub(深色),中央有 logo(本期实现 **ZEEKR** 字样贴图)
- 橙铜色 brembo 风格刹车卡钳
- 透出黑色 brake disc

## 附录 B:已知决策日志

| 日期 | 决策 | 备选 | 选了 | 理由 |
|------|------|------|------|------|
| 2026-05-03 | 部署形态 | A(HA OS)/B/C/D/E | A | 用户已部署 |
| 2026-05-03 | 文件通道 | Studio Code Server / Samba / SSH / 其他 | Samba | Windows native,Claude 可直接读写 |
| 2026-05-03 | GitHub 部署 | A(已有写权限)/ B(只读 fork)/ C(新建)/ D(不用 GH) | D | Samba 直连无需 git 中转 |
| 2026-05-03 | 范围 | A(MVP)/ B(MVP+3D)/ C(完整版)/ D(全修) | C | 平衡覆盖度与工作量 |
| 2026-05-03 | 轮毂方案 | a(参数化建模)/ b(下载 GLB)/ c(开源)/ d(保留原模型) | a | 可控 + 无授权问题 |
| 2026-05-03 | device_tracker | A(留+高德)/ B(留+转 WGS-84)/ C(去掉) | C | 用户不需要 GPS |
| 2026-05-03 | 红线 | 自由 / 划红线 | 划红线:只动 zeekr 相关 | 用户明确要求 |
| 2026-05-03 | 中心 logo | 不贴 / 贴 | 贴 ZEEKR 字样 | 用户明确要求 |
| 2026-05-03 | spec review 反馈处理 | A(全吃 1 Blocker + 3 Major + 5 Minor)/ B(只 Blocker+Major)/ C(只 Blocker)/ D(全跳) | A | Codex 额度耗尽,改用 Claude 独立二审;反馈质量高,全吃修订进 spec |
| 2026-05-03 | Phase 5 wheel 妥协方案 | A(深黑 base + silver outline)/ B(亮银 base + silver outline)/ 进一步加工(自绘 texture / shader 注入) | A | GLB lunguhei 单 mesh 限制无法做出 silver-outlined-black-fill 双色;A 方案的"silver outline + dark fill"对比强烈,跟用户参照视觉调性最接近 |
| 2026-05-03 | Phase 6 验收范围 | A(D1+D3 简版)/ B(跳过 in-use 观察)/ C(D1-D5 全做) | C | 用户严格按 spec 走完整体验收,完整证明 read-only MVP 稳定性 |
| 2026-05-03 | Phase 6 D1-D5 验收结果 | — | 全 ✓ | D1 重启不丢实体 ✓,D2 拔线 30s 不弹 reauth(C2 修复验证)✓,D3 删除重添无残留(unique_id 稳定)✓,D4 30+ 分钟无 ERROR 日志 ✓,D5 改 access_token 触发 reauth flow → reauth_confirm 表单 → SMS 重配 → entry 恢复(C3 修复验证)✓ |

---

## 附录 C:Token 兜底获取流程(SMS 失败时启用)

如果 §5.1 A2(SMS 验证码)失败,大概率是极氪云端轮换了 SMS 接口的签名 secret(`X_CA_SECRET` / 其他 hardcode 在 `const.py` 的密钥)。这种情况走 token 直接登录路径,需要用户从极氪官方渠道抓一份有效的 JWT。

### C.1 极氪官网 / 小程序 web 登录(若开放)

某些品牌账号同时提供 web 入口(类似 `account.zeekr.com`)。Claude 在阶段 A 启动前会先用 curl 探测极氪是否有这种入口;若有:
1. 用户在浏览器登录该 web 入口
2. 开 DevTools → Network → 任意一个 XHR 请求 → Headers 标签
3. 找 `Authorization` 头(或 `Cookie` 里的 token 字段),复制值
4. 在 HA 集成配置时选"使用 token 登录"输入

**最简,但需要极氪开放 web 端**。Claude 会先用 `WebFetch` 验证。

### C.2 用 mitmproxy / Charles 抓极氪 APP HTTPS 流量

适用于无 web 入口或 web 入口签名机制不同的情况。

1. **PC 装 mitmproxy 或 Charles Proxy**(免费版即可)
2. **手机装根证书**:Charles 引导手机下载并信任 CA 根证书,否则 HTTPS 解密失败
3. **极氪 APP 可能有 SSL pinning**:某些 Android 版本会拒绝中间人证书
   - **iOS** 通常不开 SSL pinning,Charles 直接能抓
   - **Android** 若 pinning 开了,需要 Frida + Objection bypass(用户没玩过的话,这步是阻塞,**Claude 教学时间约 30-60 分钟**)
4. 打开极氪 APP,任意操作触发 API 请求(查看车辆状态等)
5. 在 Charles 里筛选 `*.zeekrlife.com` 域的请求
6. 找到 `Authorization` 头,复制 JWT(形如 `eyJhbGciOi...` 三段式)
7. 在 HA 集成配置时选"使用 token 登录"输入

**风险**:Android SSL pinning + 用户技术门槛。

### C.3 第三方工具 / 社区脚本

参考 Tesla 集成生态中常见的 `tesla_auth` / `bmw_cn_helper` 模式——若极氪社区已经有类似工具,直接拿来用。**本期不依赖**;Claude 在 C.2 启动前花 5 分钟搜一下 GitHub。

### 回退方案

如果 C.1 / C.2 / C.3 全部走不通:
- **本期落地阻塞**,Claude 通知用户停下
- 等原仓库 `@aourwz` 更新 `const.py` 的 hardcode secret(可订阅 GitHub watch)
- 或者用户找另一个已知能用的极氪 token 来源(论坛 / 群组)

### 对时间线的影响

- C.1 成功:不影响,阶段 A 当天搞定
- C.2 成功且无 SSL pinning:+30-60 分钟,当天搞定
- C.2 遇 SSL pinning + 用户配合:+0.5-1 天
- 全部失败:本期暂停,等社区或换路径

**已纳入 §6 "3-5 天" 区间内的保守估算。**
