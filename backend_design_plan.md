# 导盲AI智能体后端设计方案

> **版本**: v1.4  
> **依据**: `导盲AI智能体设计方案.md`(v1.6)、`设计流程图.txt`、`frontend_design_plan.md`  
> **原则**: 先单体后拆分，先规则后智能，先闭环后扩展  
> **本次更新**: 对齐主文档 v1.6 —— 纵向切片结构（4 Agent + Orchestrator）、Agent 调用契约、模块归属分工、补齐认证/家属接口与数据表；存储层改用 MySQL 8、移除 Redis（v1.3）；RAG 知识库检索暂缓、留待升级阶段（v1.4）

---

## 1. 设计目标

后端的第一任务是稳定支撑最小可用产品，而不是一开始就堆满微服务。

### 1.1 核心目标

1. 跑通语音输入到语音回复的闭环。
2. 支撑导航、SOS、天气、提醒等基础能力。
3. 预留视觉、OCR、政策问答和多 Agent 编排能力。
4. 让后续拆分服务时不推翻现有接口。

### 1.2 分层策略

| 阶段 | 形态 | 说明 |
|------|------|------|
| MVP | 单体 FastAPI（纵向切片） | 4 个 Agent 模块 + Orchestrator，模块间走 `agent_protocol` 契约（见 §4.3） |
| 增强版 | 模块化单体 | 目录边界不变，增强各模块内部能力（视觉、政策问答等） |
| 完整版 | 微服务 + Agent 编排 | 复杂能力再独立部署，引入 LangGraph 等编排框架 |

---

## 2. 总体架构

### 2.1 MVP 架构

- FastAPI 作为主控入口
- MySQL 8 作为主数据库（无 Redis，缓存/会话/实时状态落 MySQL，见 §5.3）
- WebSocket 用于实时推送
- 外部 API 只接最关键的几项

### 2.2 目标架构

后续演进为（与主文档 §2.2 四人分工对应）：

| 目标服务 | 归属 Agent | 负责人 |
|---------|-----------|--------|
| 主控服务 + LLM 路由核心 | Orchestrator（`agents/orchestrator.py`） | 人A（Conversation 兼任） |
| 语音服务 | Conversation Agent（`agents/conversation/`） | 人A |
| 导航服务（含视觉避障） | Navigation Agent（`agents/navigation/`） | 人B |
| 安全服务 | Safety Agent（`agents/safety/`） | 人C |
| 感知服务 + 政策服务 | Perception Agent（`agents/perception/`） | 人D |
| 任务队列服务 | Phase 2+ Celery（broker 用 MySQL）；MVP 用 asyncio 后台任务 | — |

> 主文档目标架构中的 6 个服务即由此 4 个 Agent 覆盖：语音 → Conversation；导航 + 视觉避障 → Navigation；安全 → Safety；视觉（物体/场景）+ 生活 + 政策 → Perception。

---

## 3. 核心模块

> 与主文档 v1.5 对齐：以下 5 个职责域对应 **4 个 Agent 模块**（纵向切片，每个模块自包含 api/agent/service/models/schemas/tests，见 §9 目录）。模块间不直接调用，统一走 `core/agent_protocol.py` 契约（§4.3）。

### 3.1 语音模块（Conversation Agent · 人A）

职责：

- ASR（音频转文字）
- TTS（文字转语音）—— **公共依赖**：所有 Agent 的回复文本都经本模块 TTS 播报，接口最先冻结
- 唤醒词
- 意图分类与 Agent 路由（由本模块负责人兼任的 Orchestrator 承担，代码在 `agents/orchestrator.py`）

**TTS 双轨策略**（与前端协同）：

| 优先级 | 方案 | 说明 |
|--------|------|------|
| 默认 | 浏览器 Web Speech API `SpeechSynthesis` | 前端本地合成，零延迟零成本 |
| 降级 | 后端 `POST /speech/tts`（Edge-TTS / 讯飞） | 前端不支持时，后端返回 `audio_url` |

ASR 响应中直接携带意图分类结果（由 Orchestrator 判断），MVP 阶段不单独暴露 `/speech/intent` 端点。流程如下：

```
前端上传音频 → ASR 转文字 → Orchestrator(LLM 意图判断与路由) → 返回 {text, intent, confidence}
```

前端一次调用即可拿到文本和意图，避免两次网络往返。意图判断由 Orchestrator（LLM 路由）承担，MVP 与后续 Agent 编排阶段共用同一入口。

### 3.2 导航模块

职责：

- 当前定位
- 路线规划
- POI 查询
- 基础避障提示

先做地图和路线，再做视觉避障。

### 3.3 安全模块

职责：

- 手动 SOS
- 自动告警
- 家属通知
- 药品识别
- 健康问答

先做手动求救和位置共享，再做自动撞击检测。

### 3.4 感知模块

职责：

- OCR
- 物体识别
- 场景理解
- 天气查询
- 翻译
- 钞票识别

这些能力优先放在 Phase 2 以后。

### 3.5 政策模块（Perception Agent 子模块 · 人D）

职责：

- 政策问答（LLM 直答 + 规则兜底，暂不建知识库）
- 政策解读
- 智能追问
- RAG 知识库检索（升级阶段评估，v1.4 暂缓）

建议在主闭环稳定后再接入。

---

## 4. 请求流转

### 4.1 语音主流程

1. 前端上传音频。
2. Conversation 模块 ASR 转文字。
3. Orchestrator（LLM 路由核心）判断意图、选择目标 Agent。
4. 目标 Agent 执行（`handle(AgentRequest) → AgentResponse`）。
5. Conversation 模块 TTS 播报回复文本。
6. 前端接收文本和音频地址。

> 完整调用链与契约见主文档 §2.3。

### 4.2 异步流程

适合交给任务队列的任务（MVP 用 asyncio 后台任务，Phase 2+ 用 Celery + MySQL broker）：

- OCR
- 视频分析
- 文档处理
- 通知发送

### 4.3 Agent 调用契约

跨模块交互统一走 `core/agent_protocol.py`（契约先冻结，改动需集成评审）：

- `AgentRequest`: `{session_id, user_id, intent, params, context}`
- `AgentResponse`: `{text, action, data, needs_followup}`
- `AgentError`: `{code, fallback_text}` —— 兜底播报文本（宁可说"不确定"，不要说错）

每个 Agent 模块实现 `handle(req: AgentRequest) -> AgentResponse`；Orchestrator 只依赖该接口，不感知内部实现。对方模块未完成时用 mock 桩联调（`tests/mocks/`）。

---

## 5. 数据设计

### 5.1 核心表

- `users`（含 `password_hash`、`device_token` 字段）
- `family_bindings`
- `emergency_contacts`
- `user_devices`
- `sos_events`
- `navigation_history`
- `reminders`
- `medicines`
- `ocr_records`
- `conversation_logs`
- `weather_cache`

> `policy_docs` 表在 Phase 3 政策问答模块接入时再建，MVP 阶段不包含。
> 表归属：每张表由所属模块的 `models.py` 定义（如 `sos_events` → `agents/safety/models.py`、`reminders` → `agents/perception/models.py`），迁移在集成时统一合并（避免多人 autogenerate 冲突）。

### 5.2 `users` 表补充字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `password_hash` | VARCHAR | bcrypt 哈希 |
| `phone` | VARCHAR | 手机号（登录凭证） |
| `device_token` | VARCHAR | 推送通知设备标识 |

> 紧急联系人使用独立的 `emergency_contacts` 表存储（见主文档数据库设计），不在 `users` 表中以 JSONB 冗余。

### 5.3 缓存与会话设计（MySQL 版，无 Redis）

| 数据 | MySQL 方案 | 说明 |
|------|-----------|------|
| 会话状态 | `conversation_logs` + `session_expire_at` | 定时清理过期会话 |
| 实时位置 | `user_locations` 表 | WebSocket 推送 + 家属端查询 |
| 在线状态 | `user_devices.last_seen_at` | 心跳更新 |
| 天气缓存 | `weather_cache` 表（JSON） | 30min 内直接返回 |
| SOS 防重复 | `sos_events.dedup_key` 唯一约束 | 60s 时间窗口判断 |
| 限流计数 | 应用内内存计数（单实例 MVP） | 多实例阶段再评估 |

> 原 Redis 方案（session / Geo / 限流）在无 Redis 环境下全部落 MySQL 或应用内内存，详见主文档 §7.2。

---

## 6. API 设计

### 6.0 统一响应格式

**成功响应**：

```json
{
  "code": 200,
  "data": { ... },
  "request_id": "uuid"
}
```

**错误响应**：

```json
{
  "code": 40001,
  "message": "语音识别失败：音频过短",
  "detail": "audio_duration_ms < 500",
  "request_id": "uuid"
}
```

**错误码分段**（前端据此决定行为）：

| 错误码范围 | 含义 | 前端行为 |
|-----------|------|---------|
| 40001-40099 | 参数/输入错误 | 语音提示用户重试，告知原因 |
| 40100-40199 | 认证/授权失败 | 跳转登录或提示重新授权 |
| 40200-40299 | 资源不存在 | 提示"未找到"，建议换关键词 |
| 40300-40399 | 业务逻辑拒绝 | 提示具体原因（如"SOS 已触发，请等待响应"） |
| 50001-50099 | 服务内部错误 | "系统繁忙，请稍后重试"，可自动重试1次 |
| 50010-50019 | 外部服务超时 | "网络超时，正在切换离线模式" |
| 50020-50029 | 外部服务不可用 | 降级到备用方案 |

每个响应必须包含 `request_id`，用于前后端联调和问题追踪。

### 6.1 MVP 接口

> 路由按模块注册：每模块 `api.py` 自带 APIRouter，`main.py` 统一挂载（每模块一行）。URL 路径与模块对应：`/speech`、`/auth`、`/family` → conversation；`/navigation` → navigation；`/safety` → safety；`/perception`、`/reminder`、`/policy` → perception。

- `GET /health` — 存活检测
- `POST /auth/send-code` — 发送短信验证码
- `POST /auth/login` — 手机号+验证码登录（返回 JWT 双 Token）
- `POST /auth/refresh` — 刷新 Token
- `POST /family/bind` — 绑定家属
- `GET /family/list` — 家属列表
- `POST /speech/asr` — 语音识别（响应含 `{text, intent, confidence}`，意图由 Orchestrator 判断，合并在该响应中）
- `POST /speech/tts` — 语音合成降级端点
- `POST /navigation/route` — 路线规划
- `GET /navigation/location` — 当前位置
- `POST /safety/sos` — 触发求救
- `GET /safety/sos/{id}/status` — 查询SOS状态（供前端轮询/家属端查看）
- `POST /reminder` — 创建提醒
- `GET /reminder` — 查询提醒列表
- `DELETE /reminder/{id}` — 删除提醒
- `GET /task/{task_id}` — 异步任务结果轮询（用于 OCR、障碍物检测等耗时操作）
- `WS /ws/chat` — 实时语音对话流
- `WS /ws/navigation` — 导航实时数据流
- `WS /ws/location` — 位置实时共享（SOS场景下向家属端推送）

### 6.2 文件上传规范

所有文件上传使用 `multipart/form-data`：

| 字段 | 类型 | 限制 | 说明 |
|------|------|------|------|
| 音频 | `audio/webm` 或 `audio/wav` | ≤ 15 秒 / ≤ 2 MB | ASR 输入 |
| 图片 | `image/jpeg` 或 `image/png` | ≤ 10 MB | OCR / 障碍物 / 药品识别 |

后端在处理上传时：

1. 立即返回 `202 Accepted` + `task_id`。
2. 异步处理完成后通过 WebSocket 推送结果，或前端用 `task_id` 轮询 `GET /task/{task_id}`。
3. 临时文件处理完成后 1 小时内自动清理。

### 6.3 增强接口

- `POST /perception/ocr` — OCR 文字提取
- `POST /perception/translate` — 翻译
- `POST /perception/object` — 物体识别
- `POST /perception/scene` — 场景描述
- `POST /perception/currency` — 钞票识别
- `POST /navigation/obstacle` — 障碍物分析（上传图片）
- `POST /safety/medicine/recognize` — 药品识别
- `POST /safety/health/ask` — 健康问答
- `POST /policy/search` — 政策搜索
- `POST /policy/ask` — 政策问答
- `POST /policy/followup` — 智能追问
- `WS /ws/navigation` — 导航实时数据流
- `WS /ws/location` — 位置实时共享

---

## 7. 安全与权限

### 7.1 认证

- JWT（`Authorization: Bearer <token>`），服务端签发，前端在 Axios 拦截器中自动附带。
- **登录方式**：手机号 + 短信验证码（视障用户友好，无需手动输入密码），验证通过后返回 JWT。
- **Token 刷新**：`POST /auth/refresh`，使用 `refresh_token`（httpOnly cookie 或安全存储）换取新 JWT，前端在 401 响应时自动触发刷新。
- **角色区分**：视障用户（`blind`）、家属（`family`）、管理员（`admin`）。中间件根据角色限制接口访问。

### 7.2 安全策略

1. 家属授权后才能查看位置。
2. SOS 请求要可追踪。
3. 高风险操作写审计日志。
4. API 做频率限制。
5. 重要数据加密存储。

---

## 8. 外部依赖

### 8.1 MVP 阶段（具体服务商）

| 能力 | 服务商 | API | 备选 |
|------|--------|-----|------|
| 语音识别 (ASR) | OpenAI Whisper API | REST | 讯飞语音听写 |
| 语音合成 (TTS) | 浏览器端为主；降级用 Edge-TTS | 免费 | 讯飞语音合成 |
| 地图/导航 | 高德地图 | Web服务 API | 百度地图 |
| 天气 | 和风天气 API | REST | 高德天气 |
| 短信通知 | 腾讯云 SMS | REST | 阿里云短信 |
| LLM 意图分类 | OpenAI GPT-4o | REST | Qwen / DeepSeek |

> MVP 阶段不部署本地 Whisper 模型，直接使用云端 API。本地化部署推迟到 Phase 4。

### 8.2 后续阶段

- 视觉模型
- OCR
- 多 Agent 编排
- RAG 知识库检索（升级阶段评估）

---

## 9. 后端目录建议（纵向切片 · 与主文档 §10 一致）

```text
backend/
├── app/
│   ├── main.py                # 装配 core + 注册 4 个模块 router（每模块一行）
│   ├── config.py              # 统一读取 .env，API key 禁止硬编码
│   ├── core/                  # ★ 共享基础设施（写一次后基本不动，改动需集成评审）
│   │   ├── security.py  database.py  websocket.py  llm.py
│   │   ├── celery_app.py      # (Phase 2+ 启用，broker 用 MySQL)
│   │   ├── vision.py          # 共享 YOLO 推理（Navigation 负责人维护）
│   │   ├── ocr.py             # 共享 PaddleOCR 推理（Perception 负责人维护）
│   │   └── agent_protocol.py  # ★ AgentRequest/AgentResponse 契约（§4.3）
│   ├── agents/                # ★ 4 个纵向切片模块（每人一个目录，互不干涉）
│   │   ├── orchestrator.py    # LLM 路由核心（归属: Conversation 负责人）
│   │   ├── conversation/      # 人A: api/ agent/ service/ models/ schemas/ tests/
│   │   ├── navigation/        # 人B: 同上
│   │   ├── safety/            # 人C: 同上
│   │   └── perception/        # 人D: 同上（含 vision/ ocr/ weather/ reminder/ policy/ followup/）
│   └── utils/                 # 跨模块工具（尽量少，能下沉到各模块就下沉）
├── alembic/                   # 迁移（集成时统一合并）
├── tests/                     # 跨模块集成测试 + test_orchestrator/
└── scripts/                   # seed_data.py / download_models.py
```

---

## 10. 部署建议

### 10.1 MVP

- 1 个 FastAPI 服务（含 `/health` 端点供负载均衡器检测）
- 1 个 MySQL 8（无 Redis）
- 1 个 MinIO 对象存储（单机 MVP 可用本地磁盘替代）

### 10.2 完整版

- API 网关
- 多个业务服务
- 独立任务队列
- 独立模型服务

---

## 11. 实施节奏

### Phase 1: 基础闭环 (W1-W8)

- W1: 项目骨架（纵向切片目录）+ Docker + 数据库 + `core/agent_protocol.py` 契约冻结
- W2: 用户系统（注册/登录/JWT + 家属绑定）
- W3: ASR（Whisper API）+ TTS（Edge-TTS 降级端点）
- W4: Orchestrator 意图分类与路由（合并在 ASR 响应中）+ 对话管理 + chat 兜底
- W5: GPS 定位 + 高德 POI + 路线规划
- W6: 手动 SOS + 位置数据存储
- W7: 集成测试 + 降级策略验证 + 错误码全覆盖
- W8: 前后端联调 + 日志 + 部署文档
>
> 家属通知推送（极光/Web Push）推迟到 Phase 2 开头（W9-W10），Phase 1 不包含。

### Phase 2: 感知增强

- OCR
- 障碍物识别
- 天气
- 药品识别

### Phase 3: 智能增强

- 政策问答
- 智能追问
- 个性化提醒
- 历史分析

### Phase 4: 服务拆分

- Agent 编排
- 微服务拆分
- 监控和治理
- 性能优化

---

## 12. 验收标准

| 指标 | MVP 目标 | 测量方式 |
|------|---------|---------|
| ASR 端到端延迟（音频上传 → 文字返回） | P95 < 2s | 服务端计时 + Prometheus |
| 主闭环延迟（语音输入 → 语音播报开始） | P95 < 4s | 端到端打点 |
| 接口可用性 | > 99.5% | `/health` 探测 |
| 并发语音请求 | ≥ 10 QPS | 压测 |
| 错误率 | < 1% | 错误日志 / 监控 |
| 异步任务不阻塞 | 后台任务队列深度 < 100 | asyncio 任务队列监控（MVP 用 asyncio 后台任务；Phase 2+ Celery + MySQL broker） |

**功能验收**：

1. 语音输入 → ASR → 意图 → 业务执行 → TTS 播报全链路可走通。
2. 新模块接入时无需修改核心路由逻辑（通过注册机制扩展）。
3. 降级场景：ASR 服务不可用时，返回明确错误码和提示文案，前端展示"语音识别暂不可用，请稍后重试"。
4. WebSocket 连接断开后自动重连，重连后推送最后一次已知状态。
