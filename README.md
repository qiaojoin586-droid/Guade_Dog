# 导盲AI智能体（Guide Dog AI）

面向视障人士的全方位 AI 辅助应用：语音对话 + 导航 + 安全助手 + 感知生活服务。

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vite 5 + React 18 + TypeScript(strict) + Tailwind CSS + zustand + axios + PWA |
| 后端 | FastAPI + SQLAlchemy 2.0(async) + Pydantic v2 + Alembic |
| 数据库 | MySQL 8（aiomysql） |
| 外部服务 | 阿里云百炼千问（LLM/视觉）、讯飞（ASR/TTS）、高德（导航）、和风天气（预留） |

## 目录结构

```text
guade_dog/
├── backend/          # FastAPI 后端
│   ├── app/          # main/config/core/auth/users/agents(4个Agent模块)/utils
│   ├── alembic/      # 数据库迁移（users）
│   ├── config/config.yaml   # 非敏感配置（模型名/端口/超时）
│   ├── scripts/init_db.sql  # 建库建表脚本（11张表）
│   └── tests/        # pytest（全 mock，不触网）
└── frontend/         # Vite + React 前端
    └── src/          # pages/components/hooks/services/stores/routes/types
```

## 快速开始

### 前置

- Python ≥ 3.11、Node ≥ 18、MySQL 8、ffmpeg（语音转码必需，加入 PATH）；
- 阿里云百炼 API Key（安全助手三功能与对话需要，见下文「API Key 与模型开通」）。

### 1. 初始化数据库

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p < backend/scripts/init_db.sql
```

> 脚本会创建 guide_dog 库、guide_dog_user 用户（默认密码 change-me）与 11 张表。如需修改用户密码，用 root 执行 ALTER USER 后同步到 backend/.env。

### 2. 配置后端

```powershell
Copy-Item .env.example backend/.env   # 按实际填写 MYSQL_* 与 DASHSCOPE_API_KEY
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe scripts\seed_data.py   # 插入测试账号（可选）
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

验证：GET http://127.0.0.1:8000/health 返回 {"status":"ok"}；/docs 为接口文档。

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev    # http://localhost:5173 ，/api 自动代理到 8000
```

### 测试账号（开发环境种子数据）

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin | admin |
| 13800138000 | test123456 | 视障用户 |

## API Key 与模型开通（不配置则安全助手/对话功能降级）

1. 登录阿里云百炼控制台（bailian.console.aliyun.com）→ API-KEY 管理 → 创建 API-KEY（建议模型范围放开为全部模型）；
2. 模型广场开通两个模型：**qwen3.7-flash**（文本 LLM）与 **qwen-vl-max**（视觉识别，备选 qwen3-vl-plus）；
3. 控制台「费用」中关闭「仅使用免费额度/免费额度用完即停」（否则视觉接口报 AllocationQuota.FreeTierOnly）；
4. 把 key 填入 backend/.env 的 DASHSCOPE_API_KEY（**.env 已被 gitignore，禁止提交**），重启后端生效。

> 未配置 key 时：紧急词健康问答仍可用；药品识别/钞票识别返回 50020，普通健康问答返回 50021，属预期降级。

## 功能模块与状态

| 模块 | 目录 | 状态 |
|------|------|------|
| 对话 Conversation | backend/app/agents/conversation/ | ASR/TTS/聊天已实现；语音工具链为日志占位（未接真实动作） |
| 导航 Navigation | backend/app/agents/navigation/ | 定位/步行路线已实现（需 AMAP_API_KEY；路线端点有已知 P1 缺陷，见「已知问题」） |
| 安全 Safety | backend/app/agents/safety/ | ✅ 药品识别/健康问答/钞票识别已实现（含免责声明、紧急词拦截、置信度阈值）；SOS 下期 |
| 感知 Perception | backend/app/agents/perception/ | 骨架占位（天气/OCR/提醒下期） |
| 家属端 | frontend/src/pages/family/ | 页面占位（下期） |

## 测试

```powershell
cd backend && .venv\Scripts\python.exe -m pytest -q      # 全 mock，不触网
cd frontend && npx tsc --noEmit --incremental false       # 严格类型检查
```

## 协作红线

1. **密钥只进 backend/.env**：SECRET_KEY、MYSQL_PASSWORD、DASHSCOPE_API_KEY、XFYUN_*、AMAP_API_KEY 等禁止写入 config.yaml 或代码；.env.example 只留占位符；
2. **共享/冻结区改动需评审**：app/core/*（errors/llm/agent_protocol/orchestrator 等）与跨模块工具链改动需 4 人集成评审后合入；
3. **安全模块三条红线**：医疗免责声明必播、识别图片不落盘/不落日志、钞票置信度宁严勿松（不播错金额）；
4. **提交信息约定**：feat(模块): 中文描述；分批提交（共享区与模块代码分开）；
5. **隐私**：ASR 文本与识别图片只记长度/不落原文，不进 conversation_logs。

## 已知问题（提交时随代码评审）

- 导航 POST /navigation/route 存在未导入 RouteSummaryOut/RouteStepOut 的 NameError（规划成功时 500），待修复；
- 语音工具链 handler 为占位，说话尚不能触发安全/导航等模块动作；
- 模块业务端点（/safety/*、/navigation/*、/speech/*）暂未挂登录鉴权，上线前需统一加 get_current_user 与限流。

## License

GPL v2（见 LICENSE）。