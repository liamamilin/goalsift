# M2 Report — Minimal Real Vertical Slice

**Milestone**: M2 — 最小真实纵向链路  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-10  
**Verdict**: ✅ **PASS**

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §5：浏览器提交具体目标→真实模型/搜索/资料读取→返回有来源的资源与初步方案→页面可查看；至少一条错误通道真实呈现；刷新/重启后已提交研究仍能读取。此阶段不以完整恢复和六操作深度为门槛。

---

## 1. Intended outcomes

- 最小 Home/Workspace、创建与查看 Job、启动、状态、结果视图。
- 简化 Controller：目标理解 → 初步条件 → 真实搜索与读取 → 初步 Assessment → Proposal；固定行动顺序（07 §5 允许）。
- 最小研究持久化（Job、成果与来源），重启后已完成成果可读取。
- API/错误处理真实存在，UI 显示真实资源、来源和限制。

## 2. Live E2E evidence (the gate)

**Case / Input**: 目标 = "我要一个像成熟商业产品一样好看的 Agent 管理网页，接入我现在运行的多个 Agent。"  
DeepSeek（deepseek-chat→flash）+ Exa（search+contents），凭据在 `.env`（gitignored）。

**Action**: `POST /api/jobs` → `POST /api/jobs/{id}/start` → 轮询 `GET /api/jobs/{id}` 至 COMPLETED。

**Observation**（真实运行，约 28s 完成）：

| 阶段 | 真实事件 | 结果 |
|---|---|---|
| Define | 保留用户原话 → Goal | original_user_text 完整保留 |
| Derive | live model | 5 条条件，区分 obligation×dimension（"good-looking"=REQUIRED+QUALITY） |
| Discover | live Exa search ($0.007) | 4 个真实资源（agentsroom.dev、anet.sh、@ian2018cs/agenthub、agentsroom features） |
| Inspect | live Exa contents ($0.001) | 1 条 Evidence（source_ref + locator + excerpt） |
| Match | live model | 21 条 Assessment：SUPPORTED（来源支持的能力）、UNKNOWN（许可证/视觉/安全未证实）、NOT_SATISFIED（AgentsRoom 闭源商业，无法自由选型） |
| Propose | live model | Proposal `READY_FOR_REVIEW`；risks 显式列出缺口；costs=`{"estimate":"UNKNOWN"}` |

关键不变量保持：
- 所有许可证 `UNKNOWN`（05 §6）——Exa 返回的 license 字段为 "Other"，不推定商用。
- 能力主张标 SUPPORTED 而非 VERIFIED（05 §9）——控制器强制：模型若输出 VERIFIED 自动降级为 SUPPORTED 并注明"无环境测试"。
- Proposal 标 `READY_FOR_REVIEW`——仅供人审查，不执行（01 §2）。
- 可追溯链完整：Proposal → Assessments(evidence_ids) → Conditions/Resources/Capability → Evidence（`has_evidence_links: true`）。

## 3. Error channel (real)

| 检查 | 真实调用 | 观察 |
|---|---|---|
| 非法状态转换 | `POST /api/jobs/{completed}/start` | `409 {"detail":"job already running or not startable"}`（COMPLETED 不可 start，须 Refine） |
| 源读取失败 | INSPECT 事件（早期 bug 修复前） | `ERROR` 事件记录 `OperationalError(...)`，研究继续而非崩溃 |
| SSE 错误事件 | 事件流 | 含 `error` 字段，前端 `error-inline` 显示 |

## 4. Persistence across restart (the gate)

**Action**: `pkill uvicorn` → 重启 `uvicorn`（无 --reload）→ `GET /api/jobs/{id}`。

**Observation**: 已 COMPLETED 的 Job 仍可读取，全部数据完整：

```
persisted_job_status: COMPLETED
conditions: 5  resources: 4  evidence: 1  proposal: true
original_user_text preserved
jobs_after_restart: 4 (全部存活)
```

数据存于隔离 SQLite（`.goalsift_data/goalsift.sqlite`，WAL 模式，路径守卫保护）。

## 5. Frontend

| 检查 | 结果 |
|---|---|
| TypeScript | `tsc --noEmit` 无错误 |
| 构建 | `npm run build` 成功（dist 227KB JS / 5KB CSS） |
| dev server | `vite` 端口 5173 返回 HTTP 200 |
| 页面 | Home（输入+任务列表）、Workspace（目标/进度/方案/条件/资源/证据/评估/SSE 事件/导出） |
| 真实交互 | 创建/启动/取消按钮真实行为；SSE 实时事件；导出链接真实 |

UI 按 03 §4 顺序：方案优先 → 条件 → 资源/证据 → 匹配。状态徽章覆盖全部 8 个 Job 状态。视觉细节审阅为 M5 门槛。

## 6. Changed files (M2)

| 文件 | 作用 |
|---|---|
| `goalsift/llm_adapter.py` | Pydantic AI/DeepSeek 包装：derive/assess/propose |
| `goalsift/search_adapter.py` | Exa 搜索+来源读取，SSRF 守卫 |
| `goalsift/repository.py` | SQLite 持久化（05 schema），事务/引用/事件 |
| `goalsift/controller.py` | 简化固定顺序 Controller（唯一可信写入口） |
| `goalsift/exporter.py` | Markdown + JSON 导出（同源当前 revision） |
| `goalsift/app.py` | FastAPI：06 §6 API + SSE + 状态转换强制 |
| `frontend/` | React+TS+Vite：Home/Workspace/api.ts |
| `README.md` | 运行说明 |

未修改 M0/M1 既有行为；M0 隔离测试 12 项仍 PASS。

## 7. Reused resources

- M1 锁定的 Pydantic AI/DeepSeek/Exa/FastAPI/SQLite/Pydantic v2 直接复用，无重写。
- `goalsift/paths.py`（M0）路径守卫保护 DB 位置。
- `goalsift/models.py`/`validators.py`（M1）领域模型与校验直接复用。

## 8. Mock/live distinction

- 全部 E2E 为 **live**：真实 DeepSeek 调用 + 真实 Exa 搜索/读取 + 真实 SQLite 持久化 + 真实 FastAPI HTTP。
- 唯一 mock 是 M1 `lookup_dimension` 工具（已属 M1，M2 不再使用）。
- 前端 dev server 为真实 Vite 服务（非 mock 端点）。

## 9. Gate verdict

| Gate 条件 (07 §5) | 满足 | 证据 |
|---|---|---|
| 浏览器提交目标→真实模型/搜索/资料读取 | ✅ | E2E live 运行 |
| 返回有来源的资源与初步方案→页面可查看 | ✅ | 4 资源带 canonical_source；Proposal READY_FOR_REVIEW；前端渲染 |
| 至少一条错误通道真实呈现 | ✅ | 非法 start→409；SSE ERROR 事件 |
| 刷新/重启后已提交研究仍能读取 | ✅ | 重启后 COMPLETED Job 全数据存活 |
| 可启动前后端 | ✅ | uvicorn + vite 均运行 |

**M2 Verdict: PASS**

## 10. Known limits & next safe action

- 一个 orphaned `RESEARCHING` Job（早期失败 start 留下 active_run_id）——正是 M4 崩溃恢复要解决的场景：重启时识别失联 run → PAUSED。
- Controller 为固定顺序（M2 允许）；M3 替换为完整六操作循环 + Challenge。
- 无 Refine/修订（M4）、无预算硬限 UI（M5）、无视觉审阅（M5）。
- `.goalsift_data` 在全局 Python 环境；M5/M6 用 `.venv` 隔离。
- 下一步：**M3 — 完整范式与证据校验**：真实六操作循环、Challenge（完整性/必要性/一致性反例）、Discover 高覆盖+局部、Match 全六状态、Validators 引用/证据/状态校验 + 负向用例（虚构 URL/未验证许可证/VERIFIED 提升/可追溯）。
