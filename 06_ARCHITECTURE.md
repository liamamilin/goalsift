# 06 — Architecture Specification

**版本：V0.2 · Phase A · 文档基线**  
**权威范围：技术候选、边界、模块、接口与技术选择验证**

## 1. 架构目标

以最小足够复杂度支撑六操作研究、真实搜索与资料读取、证据校验、增量持久化和可使用的 Web 工作区。尽可能复用成熟软件能力，只开发范式特有的 Goal/Condition/Assessment/Proposal 逻辑。

**本文件中的具体框架为候选建议，不是已完成实测的事实或已冻结的依赖。M1 Spike 才能正式确认。**

## 2. 方案发现与候选技术

应先验证现成组件能满足哪些条件，再决定自行开发缺口。当前待验证候选：

| 层次 | 优先候选 | 备选/取舍 | 决策状态 |
|---|---|---|---|
| Agent SDK | Pydantic AI 基础 Agent / 可用的 Researcher 组件 | OpenAI Agents SDK；如确有复杂工作流需要再评估 LangGraph | PROVISIONAL |
| 模型 | 具备工具调用及可校验输出的已授权模型 | 可配置不同提供商，须逐一验证兼容性 | PROVISIONAL |
| 搜索/读取 | Agent SDK 可用的 Web 搜索与网页读取工具 | Tavily/Exa/Firecrawl 等按效果与成本单独评估 | PROVISIONAL |
| 后端 | Python + FastAPI | 若 Spike 证据充分可提出替换 | PROVISIONAL |
| 前端 | React + TypeScript + Vite | 可采用更成熟且满足要求的整体模板 | PROVISIONAL |
| UI | Mantine 或成熟 Dashboard 模板 | shadcn/ui 等；需实际审查视觉与集成成本 | PROVISIONAL |
| 存储 | SQLite + 迁移机制 | 明确瓶颈出现再升级 | PROVISIONAL |
| 进度推送 | HTTP API + SSE | 仅确有双向流需求时 WebSocket | PROVISIONAL |
| 导出 | Markdown + JSON | 无需首版 PDF/Word | SELECTED（产品要求） |

**重要限制**：候选组件的名称与文档介绍不能证明它在选定版本、模型和环境中能够使用。特别是 Researcher 的搜索与来源记录功能，必须在 M1 用真实工具调用检查 API、数据结构、版本和成本。若不可用，退回基础 Agent + 独立 Search/Fetch Adapter，**不要为了迁就框架修改核心范式**。

不因为曾讨论过 DeepSeek Harness / Cordis 就必须使用它；其插件运行时价值与本产品首版研究能力不是同一要求。

## 3. 逻辑组件边界

```text
Browser UI
  │  HTTP + SSE (authenticated/local-origin constraints)
  ▼
Application API
  │
  ├── Research Controller (job state, actions, budget, gates)
  │     ├── LLM Adapter / Agent SDK
  │     ├── Read-only Research Tool Adapters
  │     └── Deterministic Validators
  │
  └── Research Repository (transactions, references, revisions)
             └── SQLite candidate
```

- Browser 不直接持有服务器模型/搜索密钥。
- Controller 独占可信研究提交入口。
- 模型可提议对象和状态解释，但不能直接覆写校验器、预算、权限或 Job 生命周期。
- 工具结果带来源引用、状态和错误，原始外部文本不可被提升为执行指令。

## 4. 最小前端

页面：**Home、Research Workspace、Settings**，定义见 03。

工作区默认按用户理解顺序组织：方案 → 条件 → 资源/证据，另有目标概要、研究进展、继续研究输入区。优先复用完整设计模板，再考虑 UI 组件库；若视觉结果不达标，允许更换模板而不改变领域逻辑。

技术要求：类型化 API 客户端、加载/部分完成/失败状态、长文本可读、窄屏可用、SSE 断线后状态重同步。所有按钮具真实行为。

## 5. 最小后端

职责：

1. Job CRUD、启动/暂停/取消/恢复/Refine。
2. Research Controller 与模型调用。
3. 搜索、网页读取及来源记录。
4. 结构校验、证据状态检查、失效传播。
5. Job/修订/对象/事件持久化。
6. 研究预算、配置与导出。

以单体应用开始，不默认拆分微服务。目录结构按职责清晰即可，**不得为匹配架构图创建一堆空文件**。

## 6. API 草案（M2 固定具体契约）

```text
POST /api/jobs                 create
GET  /api/jobs                 list
GET  /api/jobs/{id}            inspect state
POST /api/jobs/{id}/start      start
POST /api/jobs/{id}/pause      pause
POST /api/jobs/{id}/resume     resume
POST /api/jobs/{id}/cancel     cancel
POST /api/jobs/{id}/input      clarify/refine
GET  /api/jobs/{id}/results    current revision results
GET  /api/jobs/{id}/export     Markdown or JSON
GET  /api/jobs/{id}/events     SSE real events
```

根据状态约束检查每次命令的前提（唯一定义：04）。命令应避免重复启动相同 run，返回可理解的冲突信息；`start` 对已 COMPLETED 不会偷偷覆盖旧版本，继续研究使用 Refine 语义。

### 6.1 实时事件

SSE 从持久化 Research Event 流提供真实进度；事件至少 `job_id`, `event_id`, `revision`, `event_type`, `timestamp`, `payload`。客户端断线使用 last event ID 或重新 GET 状态，不依赖内存中的临时事件。若 SSE 失败，用户仍能轮询 Job 状态。

## 7. 后台执行与恢复

首版单机单工作进程/单有效 Job executor 即可，能够运行长研究任务而不依赖单个 HTTP 请求的存活。必须实现持久 run 所有权、恢复点及启动时的孤儿 Job 识别。

**不要误把 FastAPI 内存 BackgroundTasks 当作可跨崩溃恢复的持久队列。** 可使用简化 worker + 数据库存储/控制逻辑；重启将失联 RESEARCHING 恢复为可继续的 PAUSED 或明确 FAILED，并由用户显式恢复。规模和并发需求得到验证后再评估外部队列。

## 8. 内部持久化方案

首选 SQLite（单用户单机），结构与枚举完全遵守 05。须验证：事务、引用完整性、修订、并发锁、迁移、崩溃后恢复；适当设置合理的写入序列化。模型与工具的外部请求不在数据库事务内长时间持锁，返回后才校验和提交。

目标不是完整事件溯源；保留重要事件与当前有效状态即可。用户修改 Goal 与新版 Assessment/Proposal 可追溯。

## 9. 模型与工具契约

### 9.1 Model Adapter

必须通过选定模型验证：文本、结构化输出、单次/多轮工具调用、错误与超时、实际 token/费用信息。若原生结构化输出不支持，容许在严格校验下使用替代生成形式，不得假定行为等价。

### 9.2 Search / Fetch

只读公共资源；每次检索保存查询与结果标识，读取保存来源地址、重定向最终地址、检索时间、适用版本、内容定位及错误。GitHub 类型资源需要真实仓库证据、关键 README/文档、许可证、接口/源码资料；Star 数不能直接当成熟度证据。

**候选搜索提供商必须在 M1 检验可获得性、价格和输出字段，不默认免费或无限使用。**

### 9.3 安全边界

- 外部文本（网页/仓库）不得决定系统提示、工具权限、预算和用户目标。
- 外部 URL/重定向/DNS/IP 需防止 SSRF，阻断不被授权的 loopback、私有网段和云元数据地址；限制协议、体积、超时和重试。
- 抓取不执行第三方脚本、安装步骤或下载的二进制。
- 研究内部数据库、隔离缓存和临时文件允许写入；用户目标项目/外部生产环境不允许未经授权修改。
- 本地默认仅绑定 loopback；对敏感配置修改和跨站请求采取合理防护；配置与日志不得暴露密钥。
- 第三方遥测可能外传研究内容，需有关闭/脱敏能力，不应不经检查默认打开。

## 10. 资源复用技术 Spike（M1）

在正式建系统之前运行短小的可复现程序，判断现成资源的适用性：

1. 选定模型可用且支持真实工具调用；记录版本、配置信息（脱敏）和错误。
2. 搜索真实资源，读取至少一处原始资料并得到定位明确的证据。
3. 得到满足 05 的 Goal、Condition、Resource、Evidence、Assessment 和 Proposal，所有 ID 引用有效。
4. 查验 SDK 默认工具是否允许追踪来源、预算/超时控制，是否可从外部控制研究过程。
5. 验证选用前后端和存储可支持 API、写入/读取及最小页面。
6. 记录收费情况、工具限制、框架不兼容点与可替代方案。

失败时必须具体说明哪个关键条件不满足，再换用其他候选技术。此阶段的结果决定后续实现栈，不是通过修改产品目标来让某框架 PASS。

## 11. 明确暂缓

默认不使用 Kubernetes、微服务、图/向量数据库、复杂消息队列、六 Agent 分工、复杂动态 Planner、通用插件内核、自动执行 Sandbox 或动态自修改系统。只有有实测证据证明它们能解决产品当前瓶颈，才提变更建议。

## 12. 交付条件

架构可运行真实六操作研究、通过证据/状态/修订校验、正确处理停止和故障、支持本地 UI 与导出，且可以更换模型/搜索适配器而不破坏 02/05 的领域契约。框架、版本和许可证在 M1 报告里完成验证记录后才能标记 SELECTED。
