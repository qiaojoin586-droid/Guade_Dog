# 导盲AI智能体前端设计方案

> **版本**: v1.4  
> **依据**: `导盲AI智能体设计方案.md`(v1.6)、`设计流程图.txt`、`backend_design_plan.md`(v1.4)  
> **原则**: 先语音闭环，后多模态；先可用，后完善  
> **本次更新**: 对齐主文档 v1.6 与后端 v1.4 —— 明确前端薄壳定位与开发协作边界、接口契约对齐（存储层 MySQL/无 Redis、RAG 暂缓均不影响前端接口）

---

## 1. 设计目标

前端的第一任务不是“做得多”，而是“让视障用户能顺畅地用起来”。

### 1.1 核心目标

1. 以语音为主入口，尽量不依赖视觉操作。
2. 让用户在一个界面里完成最常见动作：说话、听结果、确认、重试。
3. 支持从 MVP 到完整版的平滑演进，不推翻重做。
4. 在弱网、失败、无权限场景下给出明确反馈。

### 1.2 设计分层

| 层级 | 目标 | 核心能力 |
|------|------|---------|
| L0 | 最小可用 | 语音录入、文本回显、TTS 播报、基础确认 |
| L1 | 出行基础 | 导航、当前位置、SOS |
| L2 | 感知增强 | OCR、障碍物结果、物体识别、天气/提醒 |
| L3 | 智能扩展 | 政策问答、追问澄清、个性化建议 |

### 1.3 开发协作定位（与主文档 §2.4 对齐）

- **前端是薄壳**：以语音交互为主，页面少而稳定，不承载业务逻辑。
- **不按后端 Agent 拆分前端**：4 个后端模块共用同一套页面/组件/Store，避免多人同时修改 `App.tsx`、路由和全局样式造成冲突。
- **前端单独归属**：建议由一人统一负责或轮值；后端 4 人通过接口契约（OpenAPI + `agent_protocol`）对接，不直接依赖前端进度。
- **联调方式**：前端先用 mock 数据跑通 UI 与状态机（组件三态规范见 §5.2），后端接口就绪后切换真实调用。

---

## 2. 信息架构

前端不从“很多页面”开始，而是从“一个主界面 + 少量辅助页”开始。

### 2.1 MVP 页面

- 登录/认证页
- 主界面
- 导航页
- SOS页
- 设置页
- 家属端基础页（仅家属绑定流程，位置查看推迟到 Phase 2）

### 2.2 后续页面

- OCR/感知页
- 政策问答页
- 提醒管理页
- 历史记录页

---

## 3. 页面设计

### 3.1 主界面

这是绝对核心页，用户进入后优先看到三件事：

1. 当前状态
2. 开始说话按钮
3. 最近一次系统回复

MVP 阶段主界面只做最小闭环，不堆功能。

**语音状态流转**（`useVoiceStore` 核心状态机）：

```
idle       → 等待用户触发，按钮显示"点击说话"
listening  → 正在录音，显示波形/倒计时，按钮显示"正在聆听..."
processing → 音频已发送，等待后端返回，按钮显示加载动画
speaking   → 正在 TTS 播报，显示播放动画，禁用录音按钮
error      → 出错，语音提示具体原因，按钮恢复可点击重试
```

只有 `idle` 和 `error` 状态下允许触发新一轮录音。

### 3.2 登录/认证页

视障用户场景下，登录方式设计为**手机号 + 短信验证码**：

1. 语音提示"请输入手机号" → 用户语音说出号码 → ASR 提取数字。
2. 语音确认号码 → 后端发送短信验证码。
3. 语音提示"请输入验证码" → 用户说出 6 位数字 → 自动提交。
4. 后端返回 JWT → access_token 存入内存（不持久化），refresh_token 存入 httpOnly + Secure + SameSite=Strict Cookie → 跳转主界面。

Token 管理（双层策略）：

| 令牌 | 存储位置 | 过期时间 | 说明 |
|------|---------|---------|------|
| `access_token` | 内存（React state） | 15 分钟 | 每次请求通过 `Authorization: Bearer` 携带；页面刷新后丢失 |
| `refresh_token` | httpOnly Cookie | 7 天 | JS 不可访问（防 XSS）；页面刷新后自动附加到 `/auth/refresh` 请求 |

- `Authorization: Bearer <access_token>` 通过 Axios 拦截器自动附带。
- 401 响应时自动调用 `POST /auth/refresh`（Cookie 自动附带 refresh_token），换取新 access_token 存入内存，原请求重放。
- 页面刷新：access_token 丢失 → 自动调 `/auth/refresh` → 无感恢复登录态。
- 刷新失败则跳转登录页并语音提示"登录已过期，请重新登录"。

### 3.3 导航页

提供：

- 起点/终点语音输入
- 当前定位
- 路线结果
- 简短语音引导

### 3.4 SOS页

提供：

- 手动 SOS 触发
- 联系人状态（通过 `GET /safety/sos/{id}/status` 轮询）
- 当前位置信息（通过 WebSocket 实时推送）
- 紧急播报

### 3.5 感知页

后续才加入：

- 摄像头预览
- OCR 结果
- 物体识别结果
- 天气和翻译

### 3.6 家属页

**家属端与视障端的关系**：MVP 阶段家属端与视障端共用一套前端代码和仓库，通过路由区分（`/family` 前缀）。家属端不需要无障碍的大字体/高对比度样式，但共用同一套 API 和认证体系。状态管理通过 `useFamilyStore` 隔离。

**MVP（Phase 1）**：

- 绑定/解绑视障用户（`POST /family/bind`、`GET /family/list`）

**Phase 2 接入**（后端 WebSocket 已在 Phase 1 就绪）：

- 用户实时位置（WebSocket `WS /ws/location`）
- SOS 状态与响应确认
- 历史轨迹回放

---

## 4. 交互原则

### 4.1 语音优先

所有核心操作都要支持语音完成，按钮只是辅助。

### 4.2 一次只做一件事

用户每次说话后，界面只反馈一个明确结果，不同时抛太多信息。

### 4.3 结果要短

语音回复优先使用短句，必要时分两段播报。

### 4.4 错误要可理解

不要只说“出错了”，要说：

- 没听清
- 网络不可用
- 定位失败
- 当前无法识别

---

## 5. 组件设计

### 5.1 核心组件

- `VoiceButton`
- `TranscriptPanel`
- `StatusBar`
- `ActionChip`
- `AlertBanner`
- `MapPreview`
- `FamilyStatusCard`
- `HistoryList`

### 5.2 组件三态规范

每个可交互组件必须具备三个状态的明确表现。对视障用户来说，**空状态/加载态/错误态**比成功态更需要设计：

| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| `VoiceButton` | 旋转动画 + "正在聆听" | — | 抖动 + "点击重试" + 错误原因播报 |
| `TranscriptPanel` | 骨架屏 + "识别中" | "请点击按钮开始说话" | "识别失败：{原因}" + 重试按钮 |
| `StatusBar` | 脉冲动画 | 显示"就绪" | 红色 + "网络已断开" |
| `AlertBanner` | 加载条 | — | 自动播报错误内容 |
| `MapPreview` | 骨架 + "加载地图中" | "暂无位置信息" | "地图加载失败" + 文字版位置描述 |
| `FamilyStatusCard` | "获取状态中" | "暂未绑定家属" | "获取失败，下拉刷新" |
| `HistoryList` | 列表骨架屏 | "暂无记录" | "加载失败，点击重试" |

所有 Error 态必须同时触发语音播报，且错误文案以"能听懂的原因"开头（如"网络不可用"而非 `ERR_CONNECTION_REFUSED`）。

### 5.3 组件使用原则

1. 优先使用按钮、图标和状态提示，不堆复杂卡片。
2. 组件尺寸固定，避免语音状态变化导致页面跳动。
3. 文案短、明确、可播报。

---

## 6. 状态管理与数据流

### 6.1 推荐划分

| Store | 职责 | 关键字段 |
|-------|------|---------|
| `useAppStore` | 全局状态 | 当前路由、网络状态、系统就绪 |
| `useAuthStore` | 认证状态 | JWT Token、用户信息、`isAuthenticated`、`refreshToken()` |
| `useVoiceStore` | 语音状态机 | `status: idle \| listening \| processing \| speaking \| error`、当前文本、错误信息 |
| `useNavigationStore` | 导航状态 | 起点、终点、路线、当前定位 |
| `useSafetyStore` | SOS 和告警 | SOS状态、联系人列表、位置共享开关 |
| `useFamilyStore` | 家属端专属 | 绑定视障用户列表、实时位置、SOS通知 |

### 6.2 数据流

**主语音流程**：

1. 用户点击/语音唤醒 → `useVoiceStore.status = listening`。
2. 前端采集音频（Web Speech API 或 MediaRecorder 降级）。
3. 上传到 `POST /speech/asr` → `status = processing`。
4. 后端返回 `{text, intent, confidence}`（intent 由后端 Orchestrator/LLM 解析）→ `status = speaking`。
5. TTS 播报：优先调用浏览器 `SpeechSynthesis`；不支持时降级为后端音频 `<audio>` 播放。
6. 如 `intent.needs_followup === true`，前端只展示追问内容，等待用户新一轮语音输入。

**文件上传流程**（OCR、障碍物检测等）：

1. 用户拍照/选择图片 → 前端压缩（max 1920px，JPEG quality 0.8）。
2. `POST` 上传 → 立即返回 `202 {task_id}`。
3. 前端显示"处理中"状态 → 每 2s 轮询 `GET /task/{task_id}` 或等待 WebSocket 推送。
4. 完成后展示结果 + TTS 播报。

---

## 7. 技术方案

### 7.1 MVP 选型

| 模块 | 技术 | 说明 |
|------|------|------|
| 框架 | React 18 + TypeScript | 组件化UI开发 |
| 构建 | Vite | 快速开发构建 |
| 状态 | Zustand | 轻量状态管理 |
| 路由 | React Router v6 | 视障端 `/app`，家属端 `/family`，认证 `/auth` |
| 样式 | Tailwind CSS + Headless UI | 高对比度、大字体样式 |
| 语音（默认） | Web Speech API | `SpeechRecognition` + `SpeechSynthesis` |
| 语音（降级） | MediaRecorder + 后端 ASR/TTS | 见 7.2 |
| 实时通信 | 原生 WebSocket | 位置共享、SOS推送（含自动重连） |
| HTTP | Axios + 拦截器 | JWT自动附带、401 自动刷新 |
| 地图 | 高德 JS API v2.0 | 家属端地图展示（官方 SDK，避免瓦片服务合规风险） |
| PWA | Workbox + Service Worker | 离线缓存、桌面安装 |

### 7.2 语音双轨降级策略

Web Speech API 在移动端浏览器（iOS Safari、微信内置浏览器、Android WebView）存在兼容性问题。前端采用**先探测、后降级**策略：

```
应用启动
  → 检测 SpeechRecognition 是否可用
  → 可用 → 使用浏览器原生语音识别，本地 TTS 合成
  → 不可用 → 降级为 MediaRecorder 录制音频
      → 上传 POST /speech/asr 获取文本
      → TTS 降级为 POST /speech/tts 获取 audio_url
      → <audio> 元素播放
```

降级模式下需告知用户："当前浏览器不支持语音输入，已切换为录音模式"。

降级 TTS 音频播放完成后触发 `onended` 事件，将 `useVoiceStore.status` 从 `speaking` 切回 `idle`。

### 7.3 麦克风权限处理

首次请求麦克风的流程：

1. 用户点击"开始说话" → 浏览器弹出权限弹窗。
2. **允许** → 开始录音，按钮显示"正在聆听"，语音提示"请说话"。
3. **拒绝** → `useVoiceStore.status = error`，语音播报："无法访问麦克风，请在浏览器设置中允许麦克风权限，或使用录音模式。"按钮文案变为"录音模式"，点击后触发降级方案。
4. 权限状态存入 `useVoiceStore.permission: 'prompt' | 'granted' | 'denied' | 'unsupported'`。

每次 `status` 切换到 `listening` 前检查权限状态，避免重复触发浏览器弹窗。

### 7.4 PWA 离线缓存策略

| 资源类型 | 策略 | 说明 |
|---------|------|------|
| JS/CSS/字体 | Precache（首次安装时全量缓存） | 核心框架和样式，版本号控制更新 |
| 页面 HTML | NetworkFirst（网络优先，失败读缓存） | 保证最新内容，离线时展示缓存 |
| 天气 API 响应 | StaleWhileRevalidate（返回缓存同时更新） | 缓存 30min，展示上次数据 |
| 导航/路线 API | NetworkOnly（仅网络） | 路线数据实时敏感，不缓存 |
| TTS 音频 | CacheFirst（缓存优先） | 同一段文字不重复生成音频 |
| 用户设置 | CacheFirst | 本地存储的偏好设置 |

**离线提示**：网络断开时，`StatusBar` 显示"当前无网络"并语音播报一次。SOS 按钮始终可见但离线时提示"需要网络连接才能发送求救信号"（后续 Phase 4 加入离线 SOS：本地缓存 + 网络恢复后自动发送）。

### 7.5 摄像头集成（Phase 3+）

感知页的摄像头能力在 Phase 3 接入，用到 `MediaDevices.getUserMedia()` API：

- 连续帧采集送后端做实时障碍物检测（WebSocket 推送结果）。
- 拍照后前端压缩（max 1920px），上传用于 OCR/物体识别。
- 前端不跑推理模型，只负责采集和展示结果。

### 7.6 后续增强

- React Native 或桌面壳
- 摄像头流处理
- 本地缓存和离线包
- 语音唤醒词

---

## 8. 无障碍设计

前端必须优先照顾视障使用场景。

### 8.1 规则

1. 所有可交互元素有 `aria-label` 和 `role` 语义标注。
2. 文字变化通过 `aria-live="polite"` 或 `aria-live="assertive"`（错误/紧急信息）通知读屏器。
3. 高对比度模式（WCAG AA 最低 4.5:1 对比度），默认大字号（≥ 18px）。
4. 不依赖颜色单独传达状态（如红色错误同时用文字说明）。
5. 关键反馈同时支持视觉文字展示和语音播报。
6. **焦点管理**：弹窗/错误出现时自动聚焦，播报完成后焦点回到主按钮。
7. **减少动效**：不使用自动轮播、闪烁动画，避免诱发光敏反应。

### 8.2 屏幕阅读器适配

- 默认大字号
- 低层级信息优先
- 重要状态固定位置显示
- 避免页面元素频繁重排

---

## 9. 分阶段实施

> 以下 Phase 划分与 `backend_design_plan.md` 第11节对齐，确保前后端可联调。

| 能力 | 后端 Phase | 前端 Phase | 联调时机 |
|------|-----------|-----------|---------|
| ASR / TTS / 意图分类 | Phase 1 | Phase 1 | W3-4 |
| 基础导航 / SOS | Phase 1 | Phase 1 | W5-6 |
| 家属位置查看 | Phase 1 (WS) | Phase 2 | W9-10 |
| 家属通知推送 | Phase 2 | Phase 2 | W9-10 |
| 提醒 CRUD / 天气 | Phase 2 | Phase 2 | W11 |
| OCR | Phase 2 | Phase 2 | W12 |
| 障碍物 / 物体识别 | Phase 2 | Phase 2 | W13-14 |
| 药品识别 | Phase 2 | Phase 2 | W15 |
| 摄像头预览 | — | Phase 3 | W18 |
| 政策问答 / 智能追问 | Phase 3 | Phase 3 | W19 |

### Phase 1: 主闭环 (W1-W8)

- W1-W2: 项目骨架 + 登录/认证（手机号+验证码 + JWT双层Token）
- W3: 语音输入（含降级方案）+ ASR接入
- W4: TTS 双轨策略（浏览器优先 + Edge-TTS 降级）+ 意图结果展示
- W5: 导航最小入口 + GPS 定位展示
- W6: SOS 页面 + 位置数据展示
- W7: 降级策略验证 + 组件三态完善 + 错误处理
- W8: 前后端联调 + PWA 缓存 + 无障碍测试

> 家属位置查看（WebSocket）推迟到 Phase 2 前端实现，后端 API 已在 Phase 1 就绪。

### Phase 2: 基础能力

- 地图导航页
- 家属位置查看（WebSocket 实时定位）
- 提醒功能（列表/创建/删除）
- 天气
- 简单 OCR（拍照上传 → 文字展示 → TTS朗读）
- 药品识别（拍照上传 → 结构化信息 → TTS朗读）
- 障碍物检测结果展示（后端 YOLO 结果 → 语音引导）

### Phase 3: 感知增强

- 摄像头实时预览与帧采集
- 物体识别与场景描述展示
- 政策问答
- 智能追问多轮对话

### Phase 4: 完整版

- 个性化设置
- 历史记录
- 多端同步
- 更细的权限控制

---

## 10. 前端目录建议

> 目录按前端能力组织，**不按后端 Agent 拆分**（见 §1.3）。

```text
frontend/
├── src/
│   ├── components/
│   │   ├── VoiceButton.tsx        # 语音按钮（含状态机）
│   │   ├── TranscriptPanel.tsx    # 对话面板
│   │   ├── StatusBar.tsx          # 状态栏（网络/权限/就绪）
│   │   ├── AlertBanner.tsx        # 错误/警告横幅
│   │   ├── MapPreview.tsx         # 地图预览
│   │   ├── FamilyStatusCard.tsx   # 家属状态卡片
│   │   └── HistoryList.tsx        # 历史记录列表
│   ├── pages/
│   │   ├── MainPage.tsx           # 主界面
│   │   ├── LoginPage.tsx          # 登录/认证
│   │   ├── NavigationPage.tsx     # 导航
│   │   ├── SOSPage.tsx            # SOS
│   │   ├── PerceptionPage.tsx     # 感知（Phase 2+）
│   │   ├── FamilyPage.tsx         # 家属端
│   │   └── SettingsPage.tsx       # 设置
│   ├── hooks/
│   │   ├── useSpeech.ts           # 语音交互（含降级）
│   │   ├── useMediaPermission.ts  # 麦克风/摄像头权限
│   │   ├── useLocation.ts         # GPS定位
│   │   ├── useCamera.ts           # 摄像头采集（Phase 3+）
│   │   └── useWebSocket.ts        # 原生 WebSocket 管理（含自动重连、心跳保活）
│   ├── stores/
│   │   ├── useAppStore.ts
│   │   ├── useAuthStore.ts        # JWT + 刷新
│   │   ├── useVoiceStore.ts       # 语音状态机
│   │   ├── useNavigationStore.ts
│   │   ├── useSafetyStore.ts
│   │   └── useFamilyStore.ts
│   ├── services/
│   │   ├── api.ts                 # Axios + 拦截器
│   │   ├── speechService.ts
│   │   ├── navigationService.ts
│   │   ├── safetyService.ts
│   │   ├── perceptionService.ts
│   │   └── authService.ts         # 登录/刷新
│   ├── routes/
│   │   └── index.tsx              # 含 AuthGuard 路由守卫
│   ├── styles/
│   │   ├── globals.css
│   │   └── accessibility.css
│   └── types/
│       └── index.ts
```

---

## 11. 验收标准

### 11.1 功能验收

| 验收项 | 标准 | 测试方式 |
|--------|------|---------|
| 语音主流程 | 用户可只靠语音完成"说话→听到回复"闭环 | 关闭屏幕盲测 |
| 语音降级 | Web Speech API 不可用时自动切换到 MediaRecorder 模式 | 模拟不支持的浏览器 |
| 认证流程 | 手机号+验证码登录可走通，Token 过期自动刷新 | 手动过期 Token |
| 组件三态 | 每个组件在 Loading / Empty / Error 状态下均有正确表现 | 逐个 Mock 状态 |
| 网络切换 | Wi-Fi → 断网 → 恢复网络全流程有反馈 | 浏览器 DevTools 模拟 |
| 屏幕阅读器 | 所有关键信息可被 NVDA/VoiceOver 读出 | 实际读屏器测试 |

### 11.2 性能指标

| 指标 | MVP 目标 |
|------|---------|
| 首屏加载（含 PWA 缓存） | < 2s |
| 语音按钮点击 → 开始录音 | < 200ms |
| 录音上传 → 文字回显 | P95 < 2.5s |
| TTS 播报延迟（文字 → 语音开始） | < 300ms（浏览器端）/ < 1s（降级音频） |
| WebSocket 重连 | < 3s |

### 11.3 无障碍清单

- [ ] 所有按钮有 `aria-label`
- [ ] 状态变化通过 `aria-live` 通知
- [ ] 最低对比度 4.5:1
- [ ] 不使用颜色作为唯一状态指示
- [ ] 键盘可完成所有操作（Tab/Enter/Esc）
- [ ] 无自动播放的音频（用户主动触发后才播放）
