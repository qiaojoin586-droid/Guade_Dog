# 导盲AI智能体 - 设计方案与技术文档

> **版本**: v1.6  
> **日期**: 2026-08-09
> **变更**: v1.5 存储层改用 MySQL 8、移除 Redis；v1.6 RAG 知识库检索暂缓，第一阶段不引入向量库，留待升级阶段评估  
> **架构**: MVP 单体后端 + 后期 AI Agent 编排/微服务演进  
> **开发策略**: 先跑通“语音输入 → 意图判断 → 单一功能执行 → 语音反馈”的最小闭环，再逐步扩展视觉、导航、安全、生活服务与政策能力

---

## 目录
1. [项目概述](#1-项目概述)
2. [设计思路与演进策略](#2-设计思路与演进策略)
3. [系统架构设计](#3-系统架构设计)
4. [技术栈选型](#4-技术栈选型)
5. [API 与工具清单](#5-api-与工具清单)
6. [五大功能模块详细设计](#6-五大功能模块详细设计)
7. [数据库设计](#7-数据库设计)
8. [接口设计](#8-接口设计)
9. [分阶段实施路线图](#9-分阶段实施路线图)
10. [项目目录结构](#10-项目目录结构)
11. [附录](#11-附录)
   1. [A. 环境变量清单](#a-环境变量清单-envexample)
   2. [B. 本地开发与启动](#b-本地开发与启动)
   3. [C. 关键技术参考链接](#c-关键技术参考链接)
---

## 1. 项目概述

### 1.1 项目定位

导盲AI智能体是一款面向视障人士的全方位AI辅助应用。以**语音交互**为核心入口，集成**视觉感知**、**导航避障**、**安全求救**、**生活服务**、**政策咨询**五大能力，通过AI Agent协作分工，为盲人用户提供"听得到、走得稳、用得安全"的智能出行与生活体验。

### 1.2 目标用户

| 用户角色 | 描述 |
|---------|------|
| 视障用户（主用户） | 通过纯语音交互使用所有功能 |
| 家属用户（监护端） | 通过手机App实时查看用户位置与状态 |
| 系统管理员 | 后台管理与数据维护 |

### 1.3 核心设计原则

1. **语音优先 (Voice-First)**: 所有交互 100% 支持语音，零手动操作
2. **安全至上 (Safety-Critical)**: 避障判断、SOS求救等安全功能具备最高优先级和容错机制
3. **渐进增强 (Progressive Enhancement)**: MVP先实现核心基础功能，后续迭代添加复杂AI能力
4. **模块解耦 (Modular)**: 五大模块独立开发部署，通过统一API网关通信
5. **离线降级 (Offline-Fallback)**: 关键功能（语音唤醒、SOS）支持离线运行

### 1.4 与设计流程图的对应关系

`设计流程图.txt` 将系统拆成五大功能模块：语音、导航与避让、求救与安全、生活服务与感知、政策与智能追问。本文档的功能范围与流程图保持一致，但实现顺序采用“先核心闭环、再功能增强、最后智能化”的方式，避免第一阶段同时引入过多模型、服务和端侧能力。

| 流程图模块 | 文档对应章节 | 复杂度定位 | 第一阶段是否必须 |
|-----------|-------------|-----------|----------------|
| 语音模块 | 6.1 | 系统入口，必须先做 | 是 |
| 导航与避让模块 | 6.2 | 先路线导航，后视觉避障 | 部分是 |
| 求救与安全模块 | 6.3 | 先手动/语音SOS，后自动检测 | 部分是 |
| 生活服务与感知模块 | 6.4 | 先天气/提醒，后OCR/场景识别 | 否 |
| 政策与智能追问模块 | 6.5 | 先追问澄清，政策问答（RAG 知识库留升级阶段） | 否 |

### 1.5 功能复杂度分层

| 层级 | 目标 | 功能范围 | 设计要求 |
|------|------|---------|---------|
| L0 最小闭环 | 证明系统可用 | 语音输入、简单意图识别、语音播报、基础SOS | 规则优先，少依赖外部服务 |
| L1 出行基础 | 满足核心出行 | 地图导航、当前位置、天气提醒、SOS基础 | 明确错误提示和人工兜底 |
| L2 感知增强 | 让系统“看得见” | OCR、障碍物识别、物体/场景识别、药品文字朗读 | 高风险结果必须保守播报 |
| L3 智能扩展 | 提升体验 | 多轮追问、政策问答、个性化提醒、本地模型 | 在已有闭环稳定后再加入 |

---

## 2. 设计思路与演进策略

### 2.1 整体设计思路

本系统不在第一阶段直接采用完整的多 Agent + 微服务架构，而是采用演进式设计：

1. MVP 阶段先实现一个可运行的主控服务，完成最小语音交互闭环。
2. 功能稳定后，再把导航、安全、感知、政策等能力拆成独立服务或 Agent。
3. 当多模块之间出现复杂协作需求时，再引入 Agent 编排、任务队列（RAG 知识库检索留待升级阶段评估）。

MVP 的核心闭环如下：

```
用户语音输入
    → 语音识别/浏览器转写
    → 简单意图判断（规则 + 少量LLM辅助）
    → 调用一个明确功能（导航 / 天气 / SOS / 提醒）
    → 生成简短安全提示
    → TTS语音播报
```

后期演进为多 Agent 编排：

```
用户语音输入 → 语音识别(ASR) → 意图分类(Agent Router) → 分发到专业Agent
                                                              ├── Conversation Agent
                                                              ├── Navigation Agent
                                                              ├── Safety Agent
                                                              └── Perception Agent
                                           ↓
                                    结果聚合 + TTS播报 → 语音反馈给用户
```

**核心设计决策**:

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 交互方式 | 纯语音 + 极简触控 | 视障用户无法依赖视觉UI |
| 架构模式 | MVP 单体后端 + React；后期再拆服务 | 初期降低集成成本，避免一开始过度设计 |
| AI能力 | 规则优先 + 单一大模型辅助；后期多模型/多Agent | 先保证可控性，再追求智能化 |
| 语音方案 | Web Speech API 快速原型 + 云端TTS/ASR备选 | 先跑通交互，生产环境再提升准确率 |
| 视觉方案 | Phase 2 后接入摄像头 + 视觉模型 | 避障属于高风险能力，不放在第一步强依赖 |
| 导航方案 | 高德/百度地图API | 国内成熟地图服务，覆盖POI与实时路况 |

### 2.2 "四人分工" Agent 编排设计

系统拆分为 **4 个核心 Agent** + **1 个 LLM 路由核心（Orchestrator）**，每人负责一个 Agent 模块，对应流程图中的 5 大模块（其中 Perception Agent 负责“生活服务与感知”和“政策与智能追问”两个关联模块）。

**四个已确定的关键决定**：

1. **Orchestrator（LLM 路由核心）归 Conversation 负责人兼任**：意图判断与路由本质同源（都是 LLM 分析用户语音、决定调用谁），归一人管理，避免两份路由逻辑并存。
2. **语音模块是公共依赖**：ASR/TTS 不只是被路由的一个模块——所有 Agent 的回复文本都要经 Conversation 的 TTS 播报。因此 Conversation 的接口最先冻结，其余 3 人开发时用 mock 桩。
3. **纵向切片结构（方案B）**：每人一个自包含目录（api / agent / service / models / schemas / tests 全部在自己模块内），模块间只通过 `core/agent_protocol.py` 契约通信（见 §2.3），互不干涉。
4. **API key 统一放 `.env`**（见附录 A），`config.py` 统一读取，禁止硬编码。

| 成员 | 模块 | 目录 | 职责 |
|------|------|------|------|
| 人A | **Conversation Agent** + **Orchestrator** | `agents/conversation/` + `agents/orchestrator.py` | LLM 路由核心、ASR/TTS、唤醒词、对话管理；壳（main.py 装配、认证、家属绑定） |
| 人B | **Navigation Agent** | `agents/navigation/` | 路径规划、实时导航、障碍物检测（调 `core/vision.py`）、安全通行判断 |
| 人C | **Safety Agent** | `agents/safety/` | 位置追踪、SOS 触发、健康问答、家属通知、药品识别（调 `core/ocr.py`） |
| 人D | **Perception Agent** | `agents/perception/` | 物体识别、天气、政策问答、提醒、OCR、智能追问 |

| 阶段 | Agent实现方式 |
|------|--------------|
| MVP | 一个 FastAPI 进程内：Orchestrator（LLM 路由）+ 4 个纵向切片模块，模块间走 `agent_protocol` 契约 |
| 增强版 | 目录边界不变，增强各模块内部能力（视觉、政策问答等） |
| 完整版 | 引入 LangGraph/LangChain 编排框架；必要时把模块拆为独立服务 |

```
                    ┌──────────────┐
                    │  Orchestrator │  ← LLM 路由核心（归属: Conversation 负责人）
                    │  (意图路由)    │
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────────────┐
    │ Conversation│ │ Navigation  │ │   Safety    │ │  Perception  │
    │    Agent    │ │    Agent    │ │    Agent    │ │    Agent     │
    │             │ │             │ │             │ │              │
    │ · ASR/TTS   │ │ · GPS导航   │ │ · SOS检测   │ │ · 物体识别   │
    │ · 意图分类  │ │ · 避障分析  │ │ · 位置共享   │ │ · OCR文字    │
    │ · 对话管理  │ │ · 通行判断  │ │ · 药品识别   │ │ · 天气查询   │
    │ · 唤醒词    │ │ · POI查询   │ │ · 健康知识   │ │ · 政策解读   │
    └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘
```

### 2.3 Agent 调用协议（契约先行）

4 人并行互不干涉的前提：**先冻结跨模块契约，再各自开发**；对方模块未完成时用 mock 桩联调。

```python
# core/agent_protocol.py —— 唯一共享契约（由 Conversation 负责人维护冻结，改动需集成评审）
from pydantic import BaseModel

class AgentRequest(BaseModel):
    session_id: str          # 会话ID
    user_id: str
    intent: str              # Orchestrator(LLM) 解析出的意图
    params: dict             # 抽取的参数（目的地、时间、图片URL等）
    context: dict            # 位置、对话历史、语音原文等上下文

class AgentResponse(BaseModel):
    text: str                # 要播报的文本（统一由 Conversation 的 TTS 播出）
    action: str | None       # 可选动作: "navigate" | "trigger_sos" | ...
    data: dict | None        # 结构化结果（导航指令、药品信息等）
    needs_followup: bool     # 是否需要 Orchestrator 追问澄清

class AgentError(BaseModel):
    code: str                # "timeout" | "low_confidence" | "service_unavailable"
    fallback_text: str       # 兜底播报文本（宁可说“不确定”，不要说错）
```

调用链：

```
用户语音 → Conversation(ASR) → Orchestrator(LLM 判断意图 → 选择 Agent)
    → Agent.handle(req) → AgentResponse → Conversation(TTS) → 语音反馈
```

每个 Agent 只需实现 `handle(req: AgentRequest) -> AgentResponse`；Orchestrator 只依赖该接口，不感知各模块内部实现。

### 2.4 四人开发协作约定

| 事项 | 约定 |
|------|------|
| 模块边界 | 每人只改自己的 `agents/<模块>/` 目录；`core/` 为共享文件，改动需集成评审 |
| 跨模块调用 | 一律走 `core/agent_protocol.py`；对方未完成时用 mock 桩（`tests/mocks/`） |
| 认证 / 家属绑定 | 归 Conversation 负责人（壳的一部分） |
| 共享视觉推理 | YOLO 加载与推理统一放 `core/vision.py`（Navigation 负责人维护） |
| 共享 OCR 推理 | PaddleOCR 加载与推理统一放 `core/ocr.py`（Perception 负责人维护） |
| API key | 只放 `.env`（附录 A），`config.py` 统一读取，禁止硬编码 |
| 路由注册 | 每模块 `api.py` 自带 APIRouter，`main.py` 统一挂载（每模块一行） |
| 数据库迁移 | `alembic/versions/` 迁移链在集成时由 Conversation 负责人统一合并（避免多人 autogenerate 冲突） |

### 2.5 容错与安全设计

导盲场景里，最重要的不是“永远给答案”，而是“在不确定时不要说错”。

| 场景 | 失败模式 | 降级/兜底策略 |
|------|---------|--------------|
| GPS信号弱 | 定位漂移、无法获取当前位置 | 播报“定位信号弱，请稍候”，并使用最后已知位置 |
| 障碍物检测低置信度 | 模型不确定、误报风险高 | 只播报“前方可能有障碍物，请减速慢行” |
| LLM超时/不可用 | 意图分类或问答失败 | 切换规则引擎和固定命令词兜底 |
| 网络断开 | 外部 API 不可达 | 启用本地缓存、离线TTS、仅保留 SOS / 基础提醒 |
| 摄像头被遮挡 | 视觉输入不可用 | 明确提示摄像头异常，不输出确定性识别结论 |

安全原则：宁可说“不确定”，也不要自信地说错。

---

## 3. 系统架构设计

### 3.1 从MVP到目标架构

MVP 阶段建议先采用最小架构：

```
视障用户
  ↓ 语音/按钮
React/PWA 前端
  ↓ REST API
FastAPI 主控后端
  ├── speech_service      # 语音转写/播报
  ├── intent_router       # 简单意图判断
  ├── navigation_service  # 地图路线/POI
  ├── safety_service      # SOS/联系人通知
  └── reminder_service    # 基础提醒
  ↓
MySQL 8
```

目标架构在 MVP 稳定后再演进为：

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端层 (Frontend)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │   Web App (React)│  │ 家属端 (Mobile) │  │ 管理后台 (Admin)    │  │
│  │   视障用户主界面  │  │  位置监控/报警  │  │  数据管理/配置      │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘  │
│           └────────────────────┼──────────────────────┘             │
│                                │ WebSocket / RESTful API             │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────┐
│                          网关层 (Gateway)                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Nginx + API Gateway (鉴权/限流/路由)              │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────┐
│                       后端服务层 (Backend Services)                   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  主控服务     │  │  Agent编排   │  │  任务队列     │              │
│  │  (FastAPI)   │  │  (LangChain) │  │  (Celery)    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐              │
│  │ 语音服务      │  │ 导航服务      │  │ 安全服务      │              │
│  │ · ASR (识别)  │  │ · 路径规划    │  │ · SOS管理     │              │
│  │ · TTS (合成)  │  │ · 实时导航    │  │ · 位置追踪    │              │
│  │ · 唤醒检测    │  │ · POI查询     │  │ · 药品识别    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ 视觉服务      │  │ 生活服务      │  │ 政策服务      │              │
│  │ · 避障分析    │  │ · OCR识别     │  │ · 政策查询    │              │
│  │ · 物体检测    │  │ · 天气查询    │  │ · 智能追问    │              │
│  │ · 场景理解    │  │ · 翻译服务    │  │ · LLM 直答   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────┐
│                    数据层 (Data & Storage)                           │
│  ┌──────────┐ ┌──────────┐                                          │
│  │ MySQL 8   │ │ MinIO    │                                          │
│  │ (主数据库)│ │ (文件存储)│                                          │
│  └──────────┘ └──────────┘                                          │
└─────────────────────────────────────────────────────────────────────┘
```

> **4 Agent ↔ 6 服务映射**：目标架构图中的 6 个服务对应 4 个 Agent：语音服务 → Conversation；导航服务 + 视觉避障 → Navigation；安全服务 → Safety；视觉（物体/场景）+ 生活服务 + 政策服务 → Perception。共享视觉推理（YOLO）与共享 OCR 推理分别抽到 `core/vision.py`、`core/ocr.py`（归属见 §2.4）。RAG 知识库检索与向量库（Milvus/Chroma）留待升级阶段评估，本期不引入。

### 3.2 前端架构 (React SPA + PWA)

| 层级 | 技术 | 用途 |
|------|------|------|
| 框架 | React 18 + TypeScript | 组件化UI开发 |
| 样式 | Tailwind CSS + Headless UI | 无障碍友好的大字体/高对比度样式 |
| 路由 | React Router v6 | SPA路由管理 |
| 状态管理 | Zustand (轻量) | 全局状态（用户信息、导航状态） |
| 语音交互 | Web Speech API (SpeechRecognition + SpeechSynthesis) | 浏览器端语音输入输出 |
| 实时通信 | 原生 WebSocket API | 与后端实时通信（导航位置、SOS推送） |
| 地图 | Leaflet + 高德瓦片 | 家属端地图展示 |
| PWA | Workbox + Service Worker | 离线缓存、桌面安装 |
| 打包 | Vite | 快速开发构建 |


MVP 阶段默认面向桌面端 Chrome / Edge 浏览器。移动端浏览器的语音能力和后台监听不稳定，Phase 3 再切到 React Native + 原生语音模块。

### 3.3 后端架构 (Python FastAPI + 微服务)

| 层级 | 技术 | 用途 |
|------|------|------|
| Web框架 | FastAPI + Uvicorn | 高性能异步API，自动生成OpenAPI文档 |
| AI编排 | LangChain + LangGraph | Agent定义、工具调用链、多Agent协作 |
| LLM网关 | LiteLLM | 统一对接多个LLM API (GPT-4o / Claude / Qwen) |
| 任务队列 | MVP 用 asyncio 后台任务；Phase 2+ 引入 Celery（broker 用 MySQL） | 异步处理耗时任务（OCR、文件处理）；无 Redis 环境下不引入额外队列组件 |
| 实时通信 | 原生 WebSocket (FastAPI) | 双向实时推送 |
| 认证 | JWT + OAuth2 | 用户认证与家属授权 |
| ORM | SQLAlchemy 2.0 + Alembic | 数据库迁移管理 |
| 文件处理 | Pillow + OpenCV + PyMuPDF | 图片/视频预处理 |
| 测试 | Pytest + pytest-asyncio | 异步测试覆盖 |

---

## 4. 技术栈选型

> 这里列的是目标技术栈，不代表 MVP 阶段一次性全部启用。第一阶段只保留语音、导航、基础数据库、认证和通知所需组件，视觉、编排框架放到后续阶段；RAG 知识库检索与向量库留待升级阶段评估。
### 4.1 技术栈总览

```
前端：React 18 | TypeScript | Tailwind CSS | Vite | PWA
后端：Python 3.11+ | FastAPI | LangChain | Celery
数据库：MySQL 8 | MinIO
AI/ML：GPT-4o | GPT-4.1 | Anthropic Claude | Qwen-VL | Whisper | YOLOv8
地图：高德地图 API (AMap) | 百度地图 API
部署：Docker | Docker Compose | Nginx | GitHub Actions
```


| 需求 | 候选方案 | 最终选择 | 适用阶段 | 选择理由 |
|------|---------|---------|---------|---------|
| ASR语音识别 | Whisper / Azure Speech / 讯飞 | Whisper API (云端) | Phase 1+ | MVP 用云端 Whisper API 零配置启动；Phase 4 再考虑本地化部署 |
| TTS语音合成 | Edge-TTS / Azure / 讯飞 | Edge-TTS (仅开发调试) + 讯飞 (生产) | Phase 1 调试 / Phase 2+ 生产 | 开发阶段用免费Edge-TTS，生产切讯飞自然音色 |
| LLM大语言模型 | GPT-4o / GPT-4.1 / Qwen / DeepSeek | GPT-4o (主) + GPT-4.1 (文本推理备选) | Phase 1+ | GPT-4o 负责多模态，GPT-4.1 负责文本推理备选 |
| 物体检测 | YOLOv8 / MobileNet / DETR | YOLOv8n (轻量) + GPT-4o (场景描述) | Phase 2+ | YOLO做实时检测，GPT-4o做复杂场景描述 |
| OCR文字识别 | PaddleOCR / Tesseract / Azure OCR | PaddleOCR (中文优化) | Phase 2+ | 中文识别准确率高，支持中英混合 |
| 地图服务 | 高德 / 百度 / Google | 高德地图 | Phase 1+ | 国内POI数据最全，无障碍API支持好 |

---

### 4.2 关键 Library 选型说明

这一节只说明库的使用边界，不代表所有依赖都会在 MVP 里启用。

- `Web Speech API` 仅用于桌面端快速原型，移动端语音在 Phase 3 改为原生方案。
- `Edge-TTS` 仅用于开发调试，生产环境切换为稳定 TTS 服务。
- `Chroma` / Milvus 等向量库：RAG 知识库检索在升级阶段评估，本期不引入。
- `LangChain / LangGraph` 只在多 Agent 编排稳定后启用。

---

## 5. API 与工具清单

> 下列 API 与工具同样按阶段启用。MVP 只接入最小闭环需要的服务，后续再逐步叠加多模态和更复杂的推理能力（RAG 知识库检索留待升级阶段）。

### 5.1 外部 API 服务

| 服务商 | API名称 | 用途 | 对应模块 | 调用方式 | 适用阶段 |
|--------|---------|------|---------|---------|---------|
| OpenAI | GPT-4o | 多模态理解、场景描述、智能追问 | 视觉/政策/对话 | REST API | Phase 1+ |
| OpenAI | GPT-4.1 | 文本推理、政策解读、结构化问答 | 政策/安全 | REST API | Phase 1+ |
| OpenAI | Whisper API | 高精度云端语音识别 | 语音模块 | REST API | Phase 1+ |
| OpenAI | TTS API | 高质量语音合成 | 语音模块 | REST API | Phase 2+ |
| Anthropic | Claude Sonnet | 复杂推理、政策解读、安全判断 | 政策/安全 | REST API | Phase 2+ |
| 阿里云 | Qwen-VL-Max | 中文场景视觉理解 | 视觉/生活 | REST API | Phase 2+ |
| 讯飞 | 语音听写/语音合成 | 中文语音识别与合成（生产环境切讯飞高精度） | 语音模块 | WebSocket API | Phase 2+ |
| 极光推送 | App 推送 / SOS通知 | 家属端告警、提醒推送 | 家属端/App | SDK | Phase 2+ |
| Web Push API | 浏览器推送 | Web 端提醒与告警 | 家属端/Web | Service Worker | Phase 1+ |
| 高德地图 | 路径规划/POI搜索/地理编码 | 导航、周边查询 | 导航模块 | REST API | Phase 1+ |
| 和风天气 | 天气预报/预警 | 天气详情 | 生活模块 | REST API | Phase 2+ |
| PaddleOCR | 文字识别服务 | OCR提取 | 生活/政策 | 本地部署 | Phase 2+ |

### 5.2 本地模型与工具

| 工具 | 用途 | 部署方式 | 适用阶段 |
|------|------|---------|---------|
| Whisper (small/base) | 离线语音识别 | 本地ONNX推理 | Phase 4 |
| YOLOv8n | 实时障碍物检测 | 本地ONNX/TensorRT推理 | Phase 2+ |
| PaddleOCR | 文字检测与识别 | 本地ONNX推理 | Phase 2+ |
| Porcupine | 语音唤醒词检测 | 本地SDK | Phase 3+ |
| Edge-TTS | 免费语音合成（开发调试） | 调用Microsoft Edge服务 | Phase 1 调试 |

### 5.3 自建 Agent 工具集 (Function Calling)

```python
# Agent 可调用的工具函数清单（按归属模块分组，见 §2.2）
TOOLS = {
    # ── Conversation Agent（人A，含 Orchestrator）──
    "speech_to_text": "音频转文字 (ASR)",
    "text_to_speech": "文字转语音播报 (TTS)",
    "wake_word_detect": "唤醒词检测",
    "intent_classify": "用户意图分类（Orchestrator LLM 路由）",
    "chat_reply": "闲聊与兜底回复",

    # ── Navigation Agent（人B）──
    "get_current_location": "获取当前GPS位置",
    "plan_route": "规划导航路线",
    "search_nearby_poi": "搜索周边设施",
    "analyze_obstacle": "分析前方障碍物",

    # ── Safety Agent（人C）──
    "trigger_sos": "触发紧急求救",
    "share_location": "分享位置给家属",
    "recognize_medicine": "识别药品信息",
    "health_qa": "健康知识问答",

    # ── Perception Agent（人D）──
    "get_weather": "查询天气",
    "create_reminder": "创建语音备忘录",
    "list_reminders": "查询待提醒事项",
    "extract_text_ocr": "OCR文字提取",
    "translate_text": "文本翻译",
    "recognize_object": "物体与场景识别",
    "recognize_currency": "钞票面额识别",
    "search_policy": "搜索相关政策",
    "smart_followup": "智能追问引导",
}
```

---

## 6. 五大功能模块详细设计

### 6.1 语音模块 (Conversation Agent)

**核心目标**: 作为用户与系统的唯一交互入口，100%的输入输出都通过语音完成。

> **模块定位**：Conversation Agent 是**公共依赖**——所有 Agent 的回复文本都经本模块的 TTS 播报，接口最先冻结；Orchestrator（LLM 路由核心，代码位于 `agents/orchestrator.py`）由本模块负责人兼任，负责“意图判断 → 选择并调用 Agent”（调用契约见 §2.3）。

#### 技术架构

```
┌──────────┐   ┌──────────┐   ┌──────────┐
│ 麦克风输入 │ → │ VAD检测   │ → │ ASR识别   │
│ (前端采集) │   │ (静音过滤) │   │ (Whisper) │
└──────────┘   └──────────┘   └─────┬────┘
                                     │
                              ┌──────▼──────┐
                              │ 意图分类     │
                              │ (LLM Router)│
                              └──────┬──────┘
                                     │
        ┌────────┬────────┬─────────┼────────┬────────┐
        ▼        ▼        ▼         ▼        ▼        ▼
    导航意图  求救意图  查询意图  识别意图  提醒意图  政策意图
        │        │        │         │        │        │
        └────────┴────────┴─────────┼────────┴────────┘
                                     │
                              ┌──────▼──────┐
                              │ 结果聚合     │
                              │ (格式化文本) │
                              └──────┬──────┘
                                     │
                              ┌──────▼──────┐
                              │ TTS合成     │ → 扬声器输出
                              │ (Edge-TTS)  │
                              └─────────────┘
```

#### MVP 实现要点

```python
# 意图分类核心逻辑 (简化版)
from enum import Enum
from pydantic import BaseModel

class Intent(str, Enum):
    CHAT = "chat"                # 兜底/闲聊（L0）
    SOS = "sos"                  # 紧急求救（L0）
    NAVIGATION = "navigation"    # 导航（L1）
    WEATHER = "weather"          # 天气（L1）
    REMINDER = "reminder"        # 提醒（L1）
    VISION = "vision"            # 场景/避障识别（L2）
    OCR = "ocr"                  # 文字提取（L2）
    HEALTH = "health"            # 健康/药品问答（L2）
    POLICY = "policy"            # 政策咨询（L3）

class IntentResult(BaseModel):
    intent: Intent
    confidence: float
    params: dict  # 抽取的参数，如目的地、时间等
    needs_followup: bool  # 是否需要追问澄清
```

#### 关键代码结构

```
agents/conversation/                # 归属: 人A（兼任 Orchestrator）
├── api.py                          # 路由: /speech/*, /ws/chat, /auth/*, /family/*
├── agent.py                        # Conversation Agent 实现（契约见 §2.3）
├── service/
│   ├── vad.py                      # 语音端点检测 (WebRTC VAD)
│   ├── asr.py                      # 语音识别服务 (Whisper/讯飞)
│   ├── tts.py                      # 语音合成服务 (Edge-TTS/讯飞)
│   ├── wake_word.py                # 唤醒词检测 (Porcupine)
│   └── conversation.py             # 对话状态管理
├── models.py                       # conversation_logs / users / family_bindings
├── schemas.py
└── tests/

（意图分类/路由由 `agents/orchestrator.py` 承担，不再放在本模块的 intent.py）
```

---

### 6.2 导航与避让模块 (Navigation Agent)

**核心目标**: 帮助盲人安全地从A点到B点，实时检测障碍物并语音引导。

#### 技术架构

```
┌──────────┐   ┌───────────┐   ┌───────────┐
│ GPS定位   │   │ 摄像头帧   │   │ 地图服务   │
│ (手机GPS) │   │ (实时采集) │   │ (高德API)  │
└────┬─────┘   └─────┬─────┘   └─────┬─────┘
     │               │               │
     ▼               ▼               ▼
┌──────────┐   ┌───────────┐   ┌───────────┐
│ 位置解析  │   │ YOLOv8    │   │ 路线规划   │
│ (坐标转换)│   │ 障碍物检测 │   │ (路径API)  │
└────┬─────┘   └─────┬─────┘   └─────┬─────┘
     │               │               │
     └───────────────┼───────────────┘
                     ▼
           ┌─────────────────┐
           │ 安全融合判断引擎  │
           │ (规则 + LLM)     │
           └────────┬────────┘
                    ▼
          ┌──────────────────┐
          │ 语音引导输出      │
          │ "前方3米有台阶"   │
          │ "路口请等待绿灯"  │
          └──────────────────┘
```

#### MVP 实现要点

```python
# 危险等级枚举
class DangerLevel(str, Enum):
    SAFE = "safe"           # 可通行
    CAUTION = "caution"     # 注意慢行
    WARNING = "warning"     # 需要等待/绕行
    DANGER = "danger"       # 立即停止

class Obstacle(BaseModel):
    label: str              # "step", "pole", "car", "person"
    confidence: float       # 检测置信度
    bbox: tuple             # 边界框 (x, y, w, h)
    distance_estimate: float  # 估算距离 (米)
    danger_level: DangerLevel

class NavigationGuidance(BaseModel):
    instruction: str        # "前方3米有台阶，请小心抬脚"
    danger_level: DangerLevel
    alternative_route: Optional[str]  # 备选路线建议
```

#### 关键代码结构

```
agents/navigation/                  # 归属: 人B
├── api.py                          # 路由: /navigation/*, /ws/navigation
├── agent.py                        # Navigation Agent 实现
├── service/
│   ├── location.py                 # GPS定位与坐标转换
│   ├── route_planner.py            # 路径规划 (高德API封装)
│   ├── poi_search.py               # 周边POI查询
│   ├── obstacle_detector.py        # 障碍物检测（调用 core/vision.py 共享YOLO推理）
│   ├── traffic_light.py            # 红绿灯状态识别
│   ├── safety_judge.py             # 安全通行判断 (规则+LLM)
│   └── guidance_generator.py       # 导航语音生成
├── models.py                       # navigation_history
├── schemas.py
└── tests/
```

---

### 6.3 求救与安全模块 (Safety Agent)

**核心目标**: 紧急情况自动求救 + 日常药品识别与健康咨询，构成安全防护网。

#### 技术架构

```
┌──────────────────────────────────────────────┐
│                Safety Agent                  │
│                                              │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │ SOS子模块  │  │ 监控子模块 │  │ 健康子模块││
│  │           │  │           │  │          ││
│  │· 加速度计 │  │· GPS位置  │  │· OCR识别 ││
│  │· 撞击检测 │  │· 实时推送 │  │· 知识检索││
│  │· 自动拨打 │  │· 电子围栏 │  │· AI问答  ││
│  └─────┬─────┘  └─────┬─────┘  └────┬─────┘│
│        └──────────────┼──────────────┘      │
└───────────────────────┼─────────────────────┘
                        ▼
              ┌─────────────────┐
              │ 家属端推送通知    │
              │ (Push/短信/电话) │
              └─────────────────┘
```


#### 家属闭环流程

```
视障用户 → 后端 SOS 服务 → 家属端推送/短信/电话
家属确认 → 后端更新状态 → 视障用户收到语音反馈
家属取消/误报 → 后端标记 false_alarm → 记录审计日志
```

说明：SOS 不只是“发出告警”，还要有“家属确认、误报取消、状态回传”的闭环。

#### MVP 实现要点

```python
# SOS触发逻辑
class SOSEvent(BaseModel):
    id: str
    user_id: str
    trigger_type: str       # "impact" | "voice" | "manual"
    location: tuple[float, float]  # (lat, lng)
    timestamp: datetime
    accelerometer_data: Optional[dict]  # 撞击时的加速度数据
    status: str             # "pending" | "dispatched" | "acknowledged" | "resolved" | "false_alarm"

# 药品识别结果
class MedicineInfo(BaseModel):
    name: str               # 药品名称
    usage: str              # 用法用量
    contraindications: str  # 禁忌
    expiry_date: str        # 保质期
    raw_text: str           # OCR原始文本
```

#### 关键代码结构

```
agents/safety/                      # 归属: 人C
├── api.py                          # 路由: /safety/*
├── agent.py                        # Safety Agent 实现
├── service/
│   ├── sos_detector.py             # 撞击检测与SOS触发
│   ├── location_tracker.py         # 实时位置追踪
│   ├── family_notifier.py          # 家属端通知推送
│   ├── medicine_ocr.py             # 药品包装OCR识别（调用 core/ocr.py 共享OCR推理）
│   ├── medicine_parser.py          # 药品信息结构化提取
│   ├── health_knowledge.py         # 健康知识库检索
│   └── health_qa_agent.py          # 健康问答AI
├── models.py                       # sos_events / medicines / emergency_contacts
├── schemas.py
└── tests/
```

---

### 6.4 生活服务与感知模块 (Perception Agent - Part A)

**核心目标**: 帮助盲人"看见"周围世界，处理日常生活中的信息获取需求。

#### 技术架构

```
┌───────────────────────────────────────────────────┐
│              Perception Agent (生活服务)            │
│                                                   │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐│
│  │OCR服务  │ │视觉服务  │ │天气服务   │ │提醒服务  ││
│  │         │ │         │ │          │ │         ││
│  │· 文档OCR│ │· 物体识别│ │· 天气查询│ │· 备忘录  ││
│  │· 路牌OCR│ │· 场景描述│ │· 预警信息│ │· 定时提醒││
│  │· 翻译   │ │· 钞票识别│ │· 出行建议│ │· 循环提醒││
│  │· 图片OCR│ │· 方位距离│ │· 紫外线  │ │· 语音录入││
│  └─────────┘ └─────────┘ └──────────┘ └─────────┘│
└───────────────────────────────────────────────────┘
```

#### MVP 实现要点

```python
class ObjectRecognition(BaseModel):
    """物体识别结果"""
    objects: list[dict]     # [{"label": "水杯", "position": "前方偏右约1米"}]
    scene_description: str  # "这是一个室内办公桌，上面有水杯、电脑和电话"

class OCRResult(BaseModel):
    """OCR结果"""
    text: str               # 提取的文字
    language: str           # "zh" | "en" | "mixed"
    translated: Optional[str]  # 翻译结果

class WeatherInfo(BaseModel):
    """天气信息"""
    temperature: float
    condition: str          # "晴" / "多云" / "雨"
    humidity: int
    precipitation_warning: bool
    uv_index: int
    dressing_advice: str    # "今天有雨，建议带伞"

class Reminder(BaseModel):
    """提醒事项"""
    id: str
    user_id: str
    content: str            # "中午12点吃降压药"
    remind_at: datetime
    repeat: Optional[str]   # "daily" | "weekly" | None
    status: str             # "active" | "completed"
```

#### 关键代码结构

```
agents/perception/                  # 归属: 人D（生活服务 + 政策）
├── api.py                          # 路由: /perception/*, /reminder/*, /policy/*
├── agent.py                        # Perception Agent 实现
├── service/                        # 子模块分发（全仓库统一 service/ 目录约定）
├── models.py                       # ocr_records / reminders / policy_docs / weather_cache
├── schemas.py
├── vision/
│   ├── object_detector.py          # 物体检测（调用 core/vision.py 共享YOLO推理）
│   ├── scene_understander.py       # 场景理解（GPT-4o）
│   ├── currency_recognizer.py      # 钞票面额识别
│   └── depth_estimator.py          # 距离估算
├── ocr/
│   ├── paddle_ocr.py               # OCR业务（底层调用 core/ocr.py 共享推理）
│   ├── image_preprocess.py         # 图片预处理（去模糊、增强）
│   └── translator.py               # 翻译服务（中英互译）
├── weather/
│   └── weather_service.py          # 天气查询（和风+高德）
└── reminder/
    ├── reminder_manager.py         # 提醒CRUD管理
    └── reminder_scheduler.py       # 定时提醒调度
```

---

### 6.5 政策与智能追问模块 (Perception Agent - Part B)

**核心目标**: 帮助视障人士了解权益政策，并通过智能追问确保理解用户意图。

注：6.4 负责通用 OCR；6.5 负责政策文件、证件和政策材料等需要引用来源的场景。

> **实现阶段说明（v1.6）**：政策问答在第一阶段暂不做 RAG 知识库检索——采用 **LLM 直答 + 规则兜底 + 人工审核 FAQ**；RAG 检索、政策文档入库与向量库在升级阶段（Phase 4 及以后）评估引入。下方 `PolicyQA.retrieved_docs`、`policy_retriever.py`、`document_loader.py` 均为升级阶段预留。

#### 技术架构

```
┌───────────────────────────────────────────────────┐
│              Perception Agent (政策与追问)          │
│                                                   │
│  ┌───────────────┐  ┌───────────────┐             │
│  │  政策查询服务   │  │  智能追问引擎   │             │
│  │               │  │               │             │
│  │· LLM 直答    │  │· 问题不明确检测│             │
│  │· 政策文档库   │  │· 缺失信息补问  │             │
│  │· LLM解读生成  │  │· 上下文理解   │             │
│  │· 适用性分析   │  │· 多轮对话管理  │             │
│  └───────────────┘  └───────────────┘             │
│                                                   │
│  ┌───────────────┐                                │
│  │  政策文件OCR   │                                │
│  │               │                                │
│  │· 拍照上传     │                                │
│  │· 预处理增强   │                                │
│  │· OCR识别      │                                │
│  │· 来源引用     │                                │
│  └───────────────┘                                │
└───────────────────────────────────────────────────┘
```

#### MVP 实现要点

```python
class PolicyQA(BaseModel):
    """政策问答"""
    query: str                      # 用户原始问题
    retrieved_docs: list[str]       # 检索到的政策文档（升级阶段启用 RAG 后使用）
    answer: str                     # 生成的政策解答
    references: list[str]           # 引用来源
    applicability: str              # 适用性判断

class FollowUp(BaseModel):
    """智能追问"""
    original_query: str             # 原始查询
    missing_info: list[str]         # ["目的地不明确", "出行时间未指定"]
    clarification_question: str     # "请问您想去哪里？大概什么时候出发？"
    clarified_params: Optional[dict] # 追问后补全的参数
```

#### 关键代码结构

```
agents/perception/                  # 归属: 人D（Perception 子模块）
├── policy/
│   ├── policy_retriever.py   # 政策检索（升级阶段: RAG）
│   ├── document_loader.py    # 政策文档加载与切分（升级阶段: RAG 用）
│   └── policy_interpreter.py # LLM政策解读
├── followup/
│   ├── ambiguity_detector.py # 问题歧义检测
│   ├── slot_filler.py        # 参数槽填充
│   └── dialogue_manager.py   # 多轮对话管理
└── document_ocr/
    ├── document_preprocess.py # 政策文件预处理
    ├── policy_ocr.py          # 政策文件OCR（调用 core/ocr.py）
    └── source_linker.py       # 来源引用与定位
```
---

## 7. 数据库设计

> **存储约定（v1.5 决定）**：数据库统一使用 **MySQL 8**（InnoDB / utf8mb4），**不使用 Redis**。会话、实时位置、在线状态、缓存等原本依赖 Redis 的数据全部落 MySQL（见 §7.2）。文件/音频等对象存储使用 MinIO（单机 MVP 可用本地磁盘替代）。

### 7.1 核心表结构 (ER概要)

```
users                   -- 用户主表
├── id (PK)
├── phone                -- 手机号（登录/绑定）
├── password_hash        -- 密码哈希
├── name                 -- 姓名
├── role                 -- 'blind' | 'family' | 'admin'
├── status               -- 'active' | 'disabled'
├── medical_notes        -- 健康备注
├── created_at
├── updated_at

emergency_contacts      -- 紧急联系人
├── id (PK)
├── user_id (FK → users)
├── name
├── relationship         -- 'parent' | 'spouse' | 'friend' | 'other'
├── phone
├── priority             -- 1/2/3...
├── is_primary
├── created_at

family_bindings          -- 家属绑定关系
├── id (PK)
├── blind_user_id (FK → users)
├── family_user_id (FK → users)
├── permission_scope     -- 'location' | 'sos' | 'all'
├── status               -- 'pending' | 'approved' | 'rejected'
├── created_at
├── updated_at

user_devices            -- 设备与推送绑定
├── id (PK)
├── user_id (FK → users)
├── device_type          -- 'web' | 'android' | 'ios'
├── platform             -- 浏览器/APP平台
├── device_name
├── push_token           -- 推送Token
├── last_seen_at
├── is_active
├── created_at

sos_events               -- SOS事件记录
├── id (PK)
├── user_id (FK → users)
├── trigger_type         -- 'impact' | 'voice' | 'manual'
├── trigger_reason
├── location_lat
├── location_lng
├── status               -- 'pending' | 'dispatched' | 'acknowledged' | 'resolved' | 'false_alarm'
├── acknowledged_by_family_user_id (FK → users)
├── false_alarm_reason
├── created_at

medicines                -- 药品识别记录
├── id (PK)
├── user_id (FK → users)
├── name
├── usage
├── contraindications
├── expiry_date
├── image_url            -- 药品图片URL
├── created_at

reminders                -- 提醒事项
├── id (PK)
├── user_id (FK → users)
├── content
├── remind_at
├── repeat_type          -- 'none' | 'daily' | 'weekly' | 'monthly'
├── status               -- 'active' | 'completed' | 'cancelled'
├── created_at

navigation_history       -- 导航历史
├── id (PK)
├── user_id (FK → users)
├── origin
├── destination
├── route_geojson        -- 路线GeoJSON
├── distance
├── duration
├── status               -- 'completed' | 'cancelled'
├── created_at

ocr_records              -- OCR识别记录
├── id (PK)
├── user_id (FK → users)
├── image_url
├── extracted_text
├── language
├── translated_text
├── created_at

policy_docs              -- 政策文档库
├── id (PK)
├── title
├── category             -- 'transport' | 'welfare' | 'medical' | 'education' | 'other'
├── source
├── source_url
├── version
├── content_hash
├── published_at
├── created_at

conversation_logs        -- 对话日志
├── id (PK)
├── user_id (FK → users)
├── session_id
├── user_input           -- 用户语音转文字
├── intent
├── agent_response       -- 系统回复文本
├── audio_url            -- TTS音频URL
├── created_at

weather_cache            -- 天气缓存
├── id (PK)
├── city_code
├── weather_data (JSON)     -- MySQL JSON 类型
├── cached_at
```
### 7.2 缓存与会话设计（MySQL 版，无 Redis）

无 Redis 环境下，临时数据统一落 MySQL 或应用内内存（单实例 MVP 可行）：

| 数据 | 原 Redis 方案 | MySQL 方案 | 说明 |
|------|-------------|-----------|------|
| 对话会话状态 | `session:{id}` Hash 30min | `conversation_logs` 表 + `session_expire_at` 字段 | 会话表加过期字段，定时清理 |
| 用户实时位置 | `user:{id}:location` Geo 5min | `user_locations` 表（user_id, lat, lng, updated_at 索引） | WebSocket 推送 + 家属端查询均走该表 |
| 在线状态 | `user:{id}:online` 1min | `user_devices.last_seen_at` | 心跳更新 last_seen_at |
| 天气缓存 | `weather:{city}` 30min | 现有 `weather_cache` 表（JSON 字段） | 命中后 30min 内直接返回 |
| SOS 防重复触发 | `sos:lock:{id}` 60s | `sos_events` 表加 `dedup_key` 唯一约束 + 60s 时间窗口判断 | 或应用内进程锁（单实例） |
| API 限流计数 | `rate:{id}:{api}` 1min | 应用内内存计数（单实例 MVP）；多实例阶段再评估 | 见 §2.5 降级策略 |

> 说明：以上均为 MVP 单实例假设下的方案。多实例部署时如需共享会话/限流，再引入外部缓存或队列组件（另行评估，不在本期范围）。

---

## 8. 接口设计 (RESTful API)

> **权威契约**: 前后端接口以 `docs/api/openapi.yaml` 为准。以下路由总览为快速参考，详细请求/响应格式、错误码、认证流程等以 OpenAPI 文件为准。

### 8.1 API 路由总览

```
Base URL: /api/v1

> 路由注册约定：每个模块的 `api.py` 自带 APIRouter，`main.py` 统一挂载（每模块一行）。URL 路径与模块对应：`/speech`、`/auth`、`/family` → conversation；`/navigation` → navigation；`/safety` → safety；`/perception`、`/reminder`、`/policy` → perception。

# --- L0 最小闭环 ---
[L0] POST   /speech/asr              # 语音识别 (上传音频 → 文字 + 意图分类结果)
[L0] POST   /speech/tts              # 语音合成 (文字 → 音频)
[L0] POST   /safety/sos              # 触发SOS
[L0] POST   /auth/login              # 登录
[L0] POST   /auth/register           # 注册
[L0] POST   /family/bind             # 绑定家属
[L0] GET    /family/list             # 家属列表
[L0] GET    /task/{task_id}          # 异步任务结果轮询
[L0] WS     /ws/chat                 # 实时语音对话流

# --- L1 出行与通知 ---
[L1] POST   /navigation/route        # 路线规划
[L1] GET    /navigation/location     # 获取当前位置
[L1] GET    /navigation/poi          # 周边设施查询
[L1] GET    /perception/weather      # 天气查询
[L1] POST   /reminder                # 创建提醒
[L1] GET    /reminder                # 查询提醒列表
[L1] DELETE /reminder/{id}           # 删除提醒
[L1] GET    /safety/location/{user_id}  # 查询用户位置(家属端)
[L1] WS     /ws/navigation           # 导航实时数据流
[L1] WS     /ws/location             # 位置实时共享

# --- L2 感知增强 ---
[L2] POST   /navigation/obstacle     # 上传图片分析障碍物
[L2] POST   /perception/ocr          # OCR文字提取
[L2] POST   /perception/translate    # 翻译
[L2] POST   /perception/object       # 物体识别
[L2] POST   /perception/scene        # 场景描述
[L2] POST   /perception/currency     # 钞票识别
[L2] POST   /safety/medicine/recognize  # 药品识别
[L2] POST   /safety/health/ask       # 健康问答

# --- L3 政策智能 ---
[L3] POST   /policy/search           # 政策搜索
[L3] POST   /policy/ask              # 政策问答
[L3] POST   /policy/followup         # 智能追问
```
### 8.2 接口示例

#### 语音识别

```json
// POST /api/v1/speech/asr
// Content-Type: multipart/form-data
// Body: audio_file (wav/mp3)

// Response:
{
  "code": 200,
  "data": {
    "text": "帮我导航到最近的地铁站",
    "language": "zh",
    "confidence": 0.95,
    "duration_ms": 3200,
    "intent": {
      "intent": "navigation",
      "confidence": 0.92,
      "params": {"destination": "最近的地铁站"},
      "needs_followup": false
    }
  }
}
```

#### 障碍物检测

```json
// POST /api/v1/navigation/obstacle
// Content-Type: multipart/form-data
// Body: image (jpg/png)

// Response:
{
  "code": 200,
  "data": {
    "obstacles": [
      {
        "label": "台阶",
        "confidence": 0.92,
        "distance_estimate": 2.5,
        "position": "正前方",
        "danger_level": "warning"
      },
      {
        "label": "行人",
        "confidence": 0.88,
        "distance_estimate": 4.0,
        "position": "偏右",
        "danger_level": "safe"
      }
    ],
    "safe_to_walk": false,
    "guidance": "前方2.5米有台阶，请注意抬脚绕行。右侧4米有行人，请保持距离。"
  }
}
```

#### 药品识别

```json
// POST /api/v1/safety/medicine/recognize
// Content-Type: multipart/form-data
// Body: image (jpg/png)

// Response:
{
  "code": 200,
  "data": {
    "name": "阿莫西林胶囊",
    "usage": "口服，一次0.5g，一日3次",
    "contraindications": "对青霉素过敏者禁用",
    "expiry_date": "2027-06",
    "raw_text": "阿莫西林胶囊 0.5g×24粒...",
    "audio_url": "https://cdn.example.com/tts/med_xxx.mp3"
  }
}
```

---

## 9. 分阶段实施路线图

### 阶段总览

```
Phase 1 (L0)          Phase 2 (L1/L2)      Phase 3 (L2/L3)      Phase 4 (L3)
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│ 最小闭环  │  ──→   │ 导航增强  │  ──→   │ 感知扩展  │  ──→   │ 智能深化  │
│ 语音交互  │         │ 避障/OCR  │         │ 政策/追问 │         │ 本地推理  │
│ 认证/SOS  │         │ 天气/提醒 │         │ 移动端/App│         │ 个性化    │
│ 基础导航  │         │ 家属通知  │         │ 离线语音  │         │ 主动预测  │
└──────────┘         └──────────┘         └──────────┘         └──────────┘
   ~8周                  ~8周                 ~8周                  ~8周
```

### 层级与阶段对应关系

| 层级 | 对应阶段 | 周次 | 说明 |
|------|---------|------|------|
| L0 | Phase 1 | W1-W8 | 先跑通语音输入、意图判断、TTS反馈和基础SOS闭环 |
| L1 | Phase 1 末 + Phase 2 | W5-W16 | 加入导航、天气、提醒；家属通知推迟到 Phase 2 实现 |
| L2 | Phase 2 + Phase 3 | W9-W24 | 加入视觉感知、OCR、药品识别和移动端能力 |
| L3 | Phase 3 末 + Phase 4 | W21-W32 | 加入政策问答、智能追问、个性化和本地模型 |

### Phase 1: MVP 基础功能 (第1-8周)

**目标**: 可运行的前后端分离原型，覆盖核心语音交互与基础求救闭环。

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W1 | 项目初始化、Docker环境、本地开发环境、数据库搭建 | 可运行的基础项目骨架 |
| W2 | 用户系统 (注册/登录/JWT) + 家属绑定基础 | 用户认证模块 |
| W3 | 语音模块: ASR接入(Whisper API) + TTS(Edge-TTS + 浏览器SpeechSynthesis) | 语音输入输出能力 |
| W4 | 语音模块: 意图分类(规则优先，合并在 ASR 响应) + 对话管理 + chat兜底 | 核心语音闭环 |
| W5 | 导航模块: GPS定位 + 高德POI查询 | 基础位置能力 |
| W6 | SOS基础: 手动触发 + 位置数据存储 | 紧急求救功能 |
| W7 | 集成测试 + 降级策略验证 + 错误处理完善 | 稳定可测试版本 |
| W8 | 前后端联调 + 日志 + 部署文档 | MVP 可演示版本 |

**Phase 1 技术栈**: React + FastAPI + MySQL 8 + Whisper API + 高德API

### Phase 2: 导航与感知增强 (第9-16周)

**目标**: 加入视觉能力，实现核心避障、OCR与药品识别。

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W9 | 路线规划与实时导航回传 | 导航主流程 |
| W10 | YOLOv8 障碍物检测 | 实时避障识别 |
| W11 | OCR模块: PaddleOCR集成 | 文字提取与朗读 |
| W12 | 药品识别: OCR + LLM结构化提取 | 药品安全识别 |
| W13 | 健康问答: 知识检索 + 规则兜底 | 健康咨询能力 |
| W14 | 天气服务: 和风天气API接入 | 天气播报 |
| W15 | 物体/场景识别: GPT-4o 多模态理解 | 场景理解 |
| W16 | 联调、回归测试、降级策略验证 | 可用增强版 |

**Phase 2 新增技术栈**: YOLOv8 + PaddleOCR + GPT-4o + 和风天气API

### Phase 3: 移动端与完整功能 (第17-24周)

**目标**: 发布移动App，完善政策、提醒和家属协同能力。

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W17 | 翻译服务: 中英互译 | 多语言支持 |
| W18 | 钞票识别 + 提醒系统增强 | 生活辅助功能 |
| W19 | 政策问答基础版（LLM 直答 + 规则兜底，暂不建知识库） | 政策问答能力 |
| W20 | 智能追问: 歧义检测与参数补全 | 多轮问答能力 |
| W21 | 家属端App开发 (React Native) | 位置监控端 |
| W22 | 推送、位置共享、通知确认流程 | 家属协同闭环 |
| W23 | 离线语音 + 唤醒词 + 权限适配 | 免触控体验 |
| W24 | 无障碍UI优化 + 全面测试 | 生产可用版本 |

**Phase 3 新增技术栈**: React Native + Porcupine + 极光推送

### Phase 4: 端智能与深度个性化 (第25-32周)

**目标**: 本地推理、离线能力、主动式AI预测。

| 周次 | 任务 | 交付物 |
|------|------|--------|
| W25 | 本地模型部署 (Whisper+TinyLLM+YOLO-nano) | 离线核心功能 |
| W26 | 端侧推理优化与缓存加速 | 降低延迟 |
| W27 | 个性化学习: 用户行为模式分析 | 用户画像 |
| W28 | 主动提醒与习惯建议 | 智能提醒 |
| W29 | 预测式导航: 学习用户常去地点 | 智能路线推荐 |
| W30 | 风险审计与安全复核 | 安全审计 |
| W31 | 性能优化与成本控制 | 交付稳定性 |
| W32 | 正式发布与版本收尾 | v2.0 正式版 |

> **升级阶段（v2.0 之后）**：政策 RAG 知识库检索 + 向量库选型（Milvus / Chroma）另行评估，第一阶段（v1.6 起）不引入。

---

## 10. 项目目录结构

```
guide-dog-ai-agent/
├── docker-compose.yml              # 本地开发环境编排
├── .env.example                    # 环境变量模板
├── README.md                       # 项目说明
├── docs/                           # 文档
│   └── api/openapi.yaml           # OpenAPI 3.0 接口契约（前后端权威契约）
│
├── frontend/                       # 前端项目 (React)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── public/
│   │   ├── manifest.json          # PWA清单
│   │   ├── sw.js                  # Service Worker
│   │   └── icons/                 # 应用图标
│   └── src/
│       ├── main.tsx               # 入口
│       ├── App.tsx                # 根组件
│       ├── routes/                # 路由配置
│       ├── hooks/                 # 自定义Hooks
│       │   ├── useSpeech.ts       # 语音交互Hook
│       │   ├── useLocation.ts     # 定位Hook
│       │   ├── useCamera.ts       # 摄像头Hook
│       │   └── useWebSocket.ts    # WebSocket Hook
│       ├── services/              # 前端API调用
│       │   ├── api.ts             # Axios封装
│       │   ├── speechService.ts
│       │   ├── navigationService.ts
│       │   ├── safetyService.ts
│       │   └── perceptionService.ts
│       ├── components/            # UI组件
│       │   ├── VoiceButton.tsx    # 语音按钮（核心交互）
│       │   ├── AudioWave.tsx      # 语音波形动画
│       │   ├── StatusBar.tsx      # 状态栏
│       │   ├── AlertModal.tsx     # 紧急弹窗
│       │   └── AccessibilityProvider.tsx  # 无障碍上下文
│       ├── pages/                 # 页面
│       │   ├── MainPage.tsx       # 主界面（语音对话）
│       │   ├── NavigationPage.tsx # 导航页面
│       │   ├── SafetyPage.tsx     # 安全页面
│       │   └── SettingsPage.tsx   # 设置页面
│       ├── stores/                # 状态管理 (Zustand)
│       │   ├── useAppStore.ts     # 全局状态
│       │   ├── useNavigationStore.ts
│       │   └── useSafetyStore.ts
│       ├── styles/                # 样式
│       │   ├── globals.css        # 全局样式
│       │   └── accessibility.css  # 无障碍专用样式
│       └── types/                 # TypeScript类型
│           └── index.ts
│
├── backend/                        # 后端项目 (Python FastAPI) —— 纵向切片结构
│   ├── pyproject.toml             # 项目配置（pytest / ruff 工具配置）
│   ├── requirements.txt           # Python 依赖清单（pip）
│   ├── requirements-dev.txt       # 开发/测试依赖
│   ├── alembic.ini                # 数据库迁移配置
│   ├── Dockerfile
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI入口: 装配 core + 注册 4 个模块 router（每模块一行）
│   │   ├── config.py              # 配置管理 (Pydantic Settings, 统一读取 .env)
│   │   ├── dependencies.py        # 共享依赖注入
│   │   │
│   │   ├── core/                  # ★ 共享基础设施（写一次后基本不动，改动需集成评审）
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # JWT认证
│   │   │   ├── database.py        # 数据库连接 (SQLAlchemy, MySQL 8)
│   │   │   ├── websocket.py       # WebSocket管理
│   │   │   ├── celery_app.py      # Celery配置 (Phase 2+，broker 用 MySQL)
│   │   │   ├── llm.py             # LLM客户端封装 (LiteLLM)
│   │   │   ├── vision.py          # 共享视觉推理 (YOLOv8) —— Navigation 负责人维护
│   │   │   ├── ocr.py             # 共享OCR推理 (PaddleOCR) —— Perception 负责人维护
│   │   │   └── agent_protocol.py  # ★ Agent契约: AgentRequest/AgentResponse (见 §2.3)
│   │   │
│   │   ├── agents/                # ★ 4 个纵向切片模块（每人一个目录，互不干涉）
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # LLM 路由核心（归属: Conversation 负责人，契约见 §2.3）
│   │   │   │
│   │   │   ├── conversation/      # ── 人A: Conversation Agent（语音 + 壳 + 认证/家属）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py         # 路由: /speech/*, /ws/chat, /auth/*, /family/*
│   │   │   │   ├── agent.py       # Conversation Agent 实现（含 handle 契约）
│   │   │   │   ├── service/       # vad.py / asr.py / tts.py / wake_word.py / conversation.py
│   │   │   │   ├── models.py      # conversation_logs / users / family_bindings
│   │   │   │   ├── schemas.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── navigation/        # ── 人B: Navigation Agent
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py         # 路由: /navigation/*, /ws/navigation
│   │   │   │   ├── agent.py       # Navigation Agent 实现
│   │   │   │   ├── service/       # location.py / route.py / poi.py / obstacle.py / safety_judge.py / guidance.py
│   │   │   │   ├── models.py      # navigation_history
│   │   │   │   ├── schemas.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── safety/            # ── 人C: Safety Agent
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py         # 路由: /safety/*
│   │   │   │   ├── agent.py       # Safety Agent 实现
│   │   │   │   ├── service/       # sos.py / tracker.py / family_notifier.py / medicine.py / health.py
│   │   │   │   ├── models.py      # sos_events / medicines / emergency_contacts
│   │   │   │   ├── schemas.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   └── perception/        # ── 人D: Perception Agent（生活服务 + 政策）
│   │   │       ├── __init__.py
│   │   │       ├── api.py         # 路由: /perception/*, /reminder/*, /policy/*
│   │   │       ├── agent.py       # Perception Agent 实现
│   │   │       ├── service/       # 子模块分发（全仓库统一 service/ 目录约定）
│   │   │       ├── models.py      # ocr_records / reminders / policy_docs / weather_cache
│   │   │       ├── schemas.py
│   │   │       ├── vision/        # object_detector.py / scene_understander.py / currency.py / depth.py
│   │   │       ├── ocr/           # paddle_ocr.py / image_preprocess.py / translator.py
│   │   │       ├── weather/       # weather_service.py
│   │   │       ├── reminder/      # reminder_manager.py / reminder_scheduler.py
│   │   │       ├── policy/        # retriever.py / interpreter.py / document_loader.py
│   │   │       ├── followup/      # ambiguity_detector.py / slot_filler.py / dialogue_manager.py
│   │   │       └── tests/
│   │   │
│   │   └── utils/                 # 跨模块工具（尽量少，能下沉到各模块就下沉）
│   │       ├── image.py           # 图片预处理
│   │       ├── audio.py           # 音频处理
│   │       └── geo.py             # 地理计算
│   │
│   ├── alembic/                   # 数据库迁移（集成时由 Conversation 负责人统一合并）
│   │   └── versions/
│   │
│   ├── tests/                     # 跨模块集成测试
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   └── test_orchestrator/     # LLM 路由联调
│   │
│   └── scripts/                   # 脚本
│       └── seed_data.py           # 初始化数据
│
└── deployment/                    # 部署配置
    ├── nginx/
    │   └── nginx.conf
    ├── docker/
    │   ├── Dockerfile.backend
    │   ├── Dockerfile.frontend
    │   └── Dockerfile.celery   # (Phase 2+，启用任务队列时)
    └── k8s/                       # (后期Kubernetes配置)
        ├── backend-deployment.yaml
        └── frontend-deployment.yaml
```

---

## 11. 附录

### A. 环境变量清单 (.env.example)

```bash
# ===== 应用基础 =====
APP_NAME=guide-dog-ai
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
API_V1_PREFIX=/api/v1

# ===== 数据库 (MySQL 8) =====
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=guide_dog
MYSQL_USER=guide_dog_user
MYSQL_PASSWORD=change-me
MYSQL_CHARSET=utf8mb4

# ===== 任务队列 (Phase 2+ 启用，broker 用 MySQL) =====
# CELERY_BROKER_URL=mysql+aiomysql://guide_dog_user:change-me@localhost:3306/guide_dog

# ===== 对象存储 (MinIO) =====
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=guide-dog-assets

# ===== 阿里云 Qwen (DashScope) =====
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_MODEL=qwen-max
DASHSCOPE_VISION_MODEL=qwen-vl-max

# ===== DeepSeek =====
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_VISION_MODEL=deepseek-chat

# ===== 讯飞语音 =====
XFYUN_APP_ID=xxx
XFYUN_API_KEY=xxx
XFYUN_API_SECRET=xxx

# ===== 高德地图 =====
AMAP_API_KEY=xxx

# ===== 和风天气 =====
QWEATHER_API_KEY=xxx

# ===== 语音唤醒 =====
PORCUPINE_ACCESS_KEY=xxx
WAKE_WORD=你好导盲

# ===== JWT =====
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# ===== WebSocket =====
WS_HEARTBEAT_INTERVAL=30
WS_RECONNECT_DELAY=3
```

### B. 本地开发与启动

#### 本地开发前置

- Node.js 20 LTS
- Python 3.11+
- Docker Desktop 24+
- npm 10+（Node.js 20 LTS 自带）
- pip + venv（Python 3.11+ 自带，无需额外安装）

#### 启动方式

```bash
# 1. 克隆项目
git clone <repo-url> guide-dog-ai-agent
cd guide-dog-ai-agent

# 2. 复制环境变量
cp .env.example .env
# 编辑 .env 填入 API 密钥

# 3. 仅启动基础设施
docker-compose up -d mysql minio

# 4. 前端独立启动
cd frontend
npm install
npm run dev

# 5. 后端独立启动
cd ..\backend
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements-dev.txt
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

# 6. 下载本地模型
python scripts/download_models.py

# 7. 一键启动全部服务（开发/联调）
cd ..
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

#### 访问地址

- 前端: http://localhost:5173
- API文档: http://localhost:8000/docs
- 管理后台: http://localhost:8000/admin

### C. 关键技术参考链接

| 技术 | 文档/仓库 |
|------|----------|
| FastAPI | https://fastapi.tiangolo.com/ |
| LangChain | https://python.langchain.com/ |
| Whisper | https://github.com/openai/whisper |
| YOLOv8 | https://github.com/ultralytics/ultralytics |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR |
| Porcupine Wake Word | https://github.com/Picovoice/porcupine |
| 高德地图API | https://lbs.amap.com/ |
| 和风天气API | https://dev.qweather.com/ |

---

> **下一步行动**: 按照 Phase 1 (W1-W8) 计划，从 `docker-compose.yml` 和项目骨架搭建开始，逐步实现MVP核心功能。






