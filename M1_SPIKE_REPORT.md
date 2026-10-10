# 2026-10-10 当前复验 — M1 当前适配器复验

**当前 Gate：PASS**。本节与 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 为本轮证据；下方旧报告保留为历史，历史数字/推测不能代替当前复验。

- 实际行为与复用：沿用 Pydantic AI、DeepSeek、Exa、FastAPI 与 SQLite。结构化响应、真实搜索与读取通过实际三案例复验；收到模型超限错误并记录 FAILED。关闭 SDK 隐式重试并修复回执跨子任务丢失。
- 变更与证据：goalsift/llm_adapter.py、search_adapter.py、budget.py；108 项完整 requirements.lock。
- 执行/观察：干净 venv 安装 108 个固定版本并通过兼容检查；source quote 原文/ID 审计 PASS。新增费用总上界核算 $0.3987574。
- Mock/Live：本轮三例 DeepSeek/Exa 及一次性基线为真实收费调用；自动负向和恢复测试只替换付费提供商，不计作 Live。
- 恢复点：修改前归档与 `2be917c`；最终 `phase-a-v0.2.1`。测试在临时数据根，无目标项目执行。
- 限制与下一步：本节 Gate PASS；旧 Spike 中各项调用未全部重跑，旧文字仅作历史记录，不能算新增 Live 证据。

<!-- historical-report -->
# M1 Spike Report — Technology Selection & Verification

**Milestone**: M1 — 技术 Spike 与选择  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-09  
**Verdict**: ✅ **PASS**

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §4：模型真调用、工具真调用、来源真读取、结构真校验、至少一个由真实来源支撑的能力主张、错误路径可观察、成本与权限有约束。**Live 无凭据则 BLOCKED**——本里程碑凭据已授权，全部为真实调用。

---

## 1. Intended outcomes

- 用最小程序判断现成 Agent SDK、真实搜索、模型与基础应用候选是否满足 Phase A。
- 对 Pydantic AI 进行真实文本/结构化输出/工具调用/多轮/错误处理测试。
- 实际 Web 搜索、读取一处来源、记录 tool result 和来源定位。
- 生成最小 Goal/Condition/Resource/Evidence/Assessment/Proposal，校验 ID 关联；至少一个来源支持的主张正确标记 SUPPORTED 而非 VERIFIED。
- 核对 SDK/工具的来源追踪、预算/超时控制与外部可控性。
- 验证前后端/存储必要依赖可安装与启动最小示例；不构建完整应用。
- 记录采用或放弃现有技术的明确依据，锁定经验证的包版本。

## 2. Credentials & budget

| Provider | 用途 | 凭据状态 | 成本观察 |
|---|---|---|---|
| DeepSeek | LLM（OpenAI 兼容接口） | 已授权（.env，gitignored） | 极低；prompt cache 命中（`prompt_cache_hit_tokens`）显著降低成本；deepseek-chat→deepseek-flash |
| Exa | Web 搜索 + 来源读取 | 已授权（.env） | search $0.007/次；contents 读取 $0.001/次 |

`.env` 含真实密钥，已被 `.gitignore` 拦截，未纳入版本控制（M0 已验证 `git check-ignore`）。报告中不出现密钥值。

## 3. Spike scripts & live evidence

四个 Spike 脚本，全部 `all_live: true`，Verdict = PASS：

### 3.1 `spikes/spike_model.py` — Pydantic AI + DeepSeek (PASS)

| 检查 | 真实调用 | 观察 | 结论 |
|---|---|---|---|
| 文本生成 | ✅ live | "clearly presents the most important information at a glance…"；input 29 / output 22 tokens | PASS |
| 结构化输出 | ✅ live | 6 条 ConditionSpec；正确区分 obligation(REQUIRED/OPTIONAL) × dimension(FUNCTIONAL/QUALITY/COMPLIANCE)；"good-looking"=REQUIRED+QUALITY；未把 React 强制为必要条件 | PASS |
| 工具调用 | ✅ live | 模型真实调用 `lookup_dimension` 工具，返回 QUALITY；`tool_calls=1` | PASS |
| 多轮 | ✅ live | turn1 推荐 CopilotKit（真实开源库）；turn2 经 `message_history` 续接 | PASS |
| 错误处理 | ✅ live | 坏模型名 → `ModelHTTPError 400`，并暴露支持的模型：`deepseek-flash, deepseek-v4-pro` | PASS |

关键证据：模型正确实现 02 §3 不变量——`obligation` 与 `dimension` 独立，`REQUIRED+QUALITY` 合法，不把实现手段当必要条件。

### 3.2 `spikes/spike_search.py` — Exa 搜索 + 来源读取 (PASS)

| 检查 | 真实调用 | 观察 | 结论 |
|---|---|---|---|
| 搜索 | ✅ live | 5 个真实 GitHub 仓库（saltbo/agent-kanban、christag/agency、karem505/openclaw-agent-dashboard、Ericonaldo/AgentMonitor、SapienXai/AgentOS）；cost $0.007 | PASS |
| 来源读取 | ✅ live | 读取 saltbo/agent-kanban 全文 9764 字符；license="Other"；locator 记录；cost $0.001 | PASS |
| 错误处理 | ✅ live | 坏 key → `status=401` | PASS |

关键证据：license 字段为 "Other"（非已知商用许可）→ 正是应标记 UNKNOWN 的情形，支撑 05 §6 许可证规则。

### 3.3 `spikes/spike_artifacts.py` — 端到端真实制品 + 校验 (PASS)

| 检查 | 真实调用 | 观察 | 结论 |
|---|---|---|---|
| 条件推导 | ✅ live model | 5 条 ConditionSpec | PASS |
| 资源发现 | ✅ live Exa | 真实 GitHub 仓库 | PASS |
| 来源读取 | ✅ live Exa | 真实 README 文本 → Evidence（locator 记录） | PASS |
| ID 引用完整性 | ✅ validators | `reference_problems: []` | PASS |
| 证据状态规则 | ✅ validators | 能力主张 = SUPPORTED（来源支持）；许可证 = UNKNOWN；`assessment_status_problems: []` | PASS |
| 可追溯性 | ✅ validators | `traceability_problems: []`；Proposal→Assessment→Condition/Resource/Capability→Evidence | PASS |
| 负向：VERIFIED 无测试记录 | ✅ validators | 被拒绝："VERIFIED requires a test/human-review record (test_context + observed_result); doc-only evidence is not enough" | PASS |
| 状态机 | ✅ validators | 合法 CREATED→RESEARCHING 通过；非法 CANCELLED→RESEARCHING 被拒 | PASS |

关键不变量证据：
- `supported_not_verified: true` —— 来源支持的能力主张标 SUPPORTED，绝不自动提升为 VERIFIED（05 §9, 02 §6）。
- `license_unknown: true` —— "Other" 许可证不推定商用（05 §6）。
- 成本字段 `{"estimate":"UNKNOWN","basis":"no pricing data; no fabrication"}` —— 不编造精确数字（05 §10）。

### 3.4 `spikes/spike_stack.py` — 后端 + 存储 (PASS)

| 检查 | 真实调用 | 观察 | 结论 |
|---|---|---|---|
| SQLite 写读 | ✅ live | 写入 RESEARCHING，读回一致；位于隔离数据根内 | PASS |
| 事务回滚 | ✅ live | ROLLBACK 后 0 行，干净 | PASS |
| FastAPI 端点 | ✅ live (TestClient) | `/api/health` 200 | PASS |
| 状态转换强制 | ✅ live | 合法转换 200；非法 CREATED→PAUSED 400 | PASS |

### 3.5 前端工具链 (installability verified)

| 检查 | 结果 |
|---|---|
| Node | v22.21.1 |
| npm / npx | 10.9.4 |
| Vite | 8.3.4（registry 可达；`engines: ^20.19.0 \|\| >=22.12.0`，与 Node 22 兼容） |
| React + TypeScript + Vite | 可安装；实际脚手架与构建为 M2 纵向链路；M1 不构建完整前端（07 §4） |

## 4. Changed files (M1)

| 文件 | 作用 |
|---|---|
| `goalsift/config.py` | .env 加载器（presence-only 返回，不泄漏值） |
| `goalsift/models.py` | 05 权威领域模型 + 枚举（JobStatus/AssessmentStatus/Obligation/Dimension 等）+ `ALLOWED_TRANSITIONS` |
| `goalsift/validators.py` | 引用完整性、证据状态规则、状态转换、可追溯性校验（唯一可信写入门） |
| `spikes/spike_model.py` | 模型 Spike |
| `spikes/spike_search.py` | 搜索 Spike |
| `spikes/spike_artifacts.py` | 端到端制品 Spike |
| `spikes/spike_stack.py` | 后端+存储 Spike |
| `requirements.txt` | 锁定经验证版本 |
| `.env` | 真实密钥（gitignored，未提交） |
| `M1_SPIKE_REPORT.md` | 本报告 |

未修改任何 M0 既有文件；`M0_REPORT.md`/spec 文档不变。M0 隔离测试 12 项仍全 PASS（无回归）。

## 5. Technology selection (locked, M1 evidence-based)

| 层 | 选定 | 版本 | 依据 | 状态 |
|---|---|---|---|---|
| Agent SDK | Pydantic AI | 2.54.0 | 真实文本/结构化/工具/多轮/错误全通过；Python 3.10 兼容 | ✅ SELECTED |
| 模型 | DeepSeek (OpenAI 兼容) | deepseek-chat(→flash) / deepseek-v4-pro | 真实调用通过；prompt cache 降本 | ✅ SELECTED |
| 搜索/读取 | Exa | /search + /contents | 真实搜索+全文读取+locator；可换适配器 | ✅ SELECTED |
| 后端 | FastAPI | 0.143.0 | TestClient 端点 + 状态强制通过 | ✅ SELECTED |
| ASGI | uvicorn | 0.54.0 | 配套 FastAPI | ✅ SELECTED |
| 存储 | SQLite (stdlib) | 3.51.0 | 事务/回滚/隔离根通过 | ✅ SELECTED |
| 数据校验 | Pydantic v2 | 2.14.0 | 结构化输出 + 领域模型 | ✅ SELECTED |
| 前端 | React + TypeScript + Vite | Vite 8.3.4 | 工具链可安装；M2 构建纵向链路 | ✅ SELECTED (待 M2 实物) |
| UI 组件库 | 待定 | — | M5 视觉审阅决定 | PROVISIONAL |

## 6. Tooling observability & controllability (06 §10.4)

- 来源追踪：Exa `/contents` 返回 `url`+`text`+`publishedDate`，Evidence 记录 `source_ref`/`locator`/`retrieved_at`/`collection_method`。✅
- 预算/超时：httpx `timeout=60`；预算字段在 `.env`；DeepSeek 返回 `usage` token 计数。✅
- 外部可控：Controller + Validators 独占可信写入；模型输出经校验才入库。✅
- 领域判断由本产品控制：Pydantic AI 仅提供模型/工具调用，状态变更由 `validators.py` + `models.py` 控制（04 §11）。✅

## 7. Commands executed & observed output (摘要)

```
$ python3 -m spikes.spike_model      → VERDICT PASS (5/5 live)
$ python3 -m spikes.spike_search    → VERDICT PASS (3/3 live)
$ python3 -m spikes.spike_artifacts → VERDICT PASS (ref/status/trace ok; VERIFIED-rejected; license UNKNOWN)
$ python3 -m spikes.spike_stack     → VERDICT PASS (sqlite+rollback+fastapi+transition)
$ python3 -m pytest                 → 12 passed (M0 regression)
```

完整 live 输出已在本里程碑对话中展示（模型返回的 6 条条件、5 个 GitHub 仓库 URL、9764 字符来源文本、校验拒绝信息等）。

## 8. Mock/live distinction

- 全部 Spike 调用为 **live**（真实 DeepSeek API、真实 Exa API、真实 GitHub 仓库文本）。
- `lookup_dimension` 工具为受控本地 mock（仅验证"模型能调用工具并使用返回值"这一 SDK 能力），非冒充外部 live 来源；外部来源由 Exa 真实读取。
- `spike_stack` 的 TestClient 为 FastAPI 内置真实 HTTP 客户端（非 mock 端点）。

## 9. Gate verdict

| Gate 条件 (07 §4) | 满足 | 证据 |
|---|---|---|
| 模型真调用 | ✅ | spike_model 5/5 live |
| 工具真调用 | ✅ | spike_model tool_calls=1；spike_search live |
| 来源真读取 | ✅ | spike_search 9764 字符 + locator |
| 结构真校验 | ✅ | spike_artifacts ref/trace 全空问题 |
| 至少一个来源支持的能力主张 | ✅ | assessment SUPPORTED（非 VERIFIED） |
| 错误路径可观察 | ✅ | 坏模型 400、坏 key 401、VERIFIED 被拒 |
| 成本与权限有约束 | ✅ | .env 预算；usage 计数；$0.007/0.001 计费；密钥 gitignored |
| 前后端/存储可启动最小示例 | ✅ | spike_stack PASS；Vite 可安装 |

**M1 Verdict: PASS** — 技术栈锁定，可进入 M2 真实纵向链路。

## 10. Known limits & next safe action

- 前端仅验证可安装性；React 实物 + 视觉审阅为 M2/M5。
- `.env` 密钥在用户全局 Python 环境（M2 起应使用 `.venv` 隔离）。
- DeepSeek `deepseek-chat` 映射到 `deepseek-flash`；如需更强推理可用 `deepseek-v4-pro`。
- 下一步：**M2 — 最小真实纵向链路**：最小 Home/Workspace、创建/启动/查看 Job、简化 Controller（目标理解→初步条件→真实搜索读取→初步 Assessment→Proposal）、最小持久化（重启后已提交成果可读）、真实错误通道、`M2_VERTICAL_SLICE_REPORT.md`。
