# 2026-10-10 当前复验 — M5 产品体验、安全与预算复验

**当前 Gate：PASS**。本节与 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 为本轮证据；下方旧报告保留为历史，历史数字/推测不能代替当前复验。

- 实际行为与复用：沿用用户前端设计、Radix/Tailwind/Driver.js。补齐 HTTP 错误、实时事件与刷新、历史只读、真实下载、条件依据、费用/预留、密钥掩码；修复窄屏撑宽、引导残留与 hash 刷新。
- 变更与证据：frontend/src/、goalsift/app.py、budget.py、security.py、search_adapter.py；README/Makefile/备份脚本。
- 执行/观察：make check：88 tests、oxlint、TypeScript 和 Vite build PASS；浏览器桌面/390px 实查，匹配两个 viewport 340/340，页面 390/390；密钥只显示 ***。备份 integrity_check/已提交行数 PASS。
- Mock/Live：本轮三例 DeepSeek/Exa 及一次性基线为真实收费调用；自动负向和恢复测试只替换付费提供商，不计作 Live。
- 恢复点：修改前归档与 `2be917c`；最终 `phase-a-v0.2.1`。测试在临时数据根，无目标项目执行。
- 限制与下一步：本节 Gate PASS；预算耗尽、SSRF/注入、无证据与错误路径由隔离测试覆盖，不冒称全部为付费 Live。临时窄屏已复原。

- 凭据遗留：原 HEAD 安全测试含两个真实 key 字面量，本轮当前文件已替换为合成值并扫描通过；旧历史/0600 本机归档仍需按敏感材料处理，建议更换提供商凭据。

<!-- historical-report -->
# M5 Report — Product Experience, Cost & Security

**Milestone**: M5 — 产品体验、成本与安全  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-10  
**Verdict**: ✅ **PASS** (UI 视觉审阅待人工确认 — 不伪称自动证明美观)

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §8。

---

## 1. Intended outcomes

- 完成 Home/Workspace/Settings 全路径（方案优先、条件/资源/证据详情、继续研究、导出）。
- 成熟 UI 资源真实审阅；覆盖长文本、多资源、空结果、部分完成、等待输入、错误、窄屏。
- 配置/预算硬限制、真实工具调用记录、费用可见性/未知成本提示。
- 密钥防泄漏、外部文档提示注入、URL/重定向 SSRF、日志脱敏、内部数据与用户项目隔离。
- 实测全部可见交互控件，清除虚假按钮和占位成功状态。

## 2. Security boundary (06 §9.3)

`goalsift/security.py` + `goalsift/budget.py`：

| 边界 | 实现 | 测试 |
|---|---|---|
| SSRF | `is_safe_url`：拒绝 loopback/private/link-local/reserved/multicast/metadata；仅 http(s) | test_ssrf (10 cases) |
| 提示注入 | 外部来源文本以 `UNTRUSTED DATA` 块传入模型，仅作证据；llm_adapter 标注"never as instructions" | test_external_content_wrapped_as_data |
| 密钥防泄漏 | `.env` 服务端读取；`/api/settings` 仅返回 `***`/`(unset)`；响应 grep 实测 0 命中 | test_settings_never_exposes_keys + live |
| 日志脱敏 | `redact_secrets`：sk-*/UUID/Bearer 模式 → `[REDACTED]` | test_redact_* (3 cases) |
| 隔离 | `paths.py` 路径守卫；测试路径无法逃逸 sanctioned root | test_isolation_test_path_cannot_escape |

## 3. Cost & budget (04 §7)

`goalsift/budget.py` — `BudgetGuard`：
- 硬限制 `max_actions`/`max_tool_calls`/`max_runtime_seconds`/`budget_usd`，**后端强制**（不靠 prompt）。
- 每次外部动作前 `guard.check(tool_call=...)`；超限抛 `BudgetExhausted`。
- Controller 捕获 → **PARTIAL**（非 FAILED），保存已提交成果，记录 `stopped_reason`。
- 费用未知提示：`budget_usd` 未配置时 `cost_unknown` 提示（05 §10）。

Live 证明（`spikes/spike_m5_budget.py`）：`max_actions=1` → 真实运行 → `final_status: PARTIAL`，`stopped_reason: "budget exhausted: max_actions"`，6 个事件已保存。

## 4. UI completeness

| 页面 | 实现 |
|---|---|
| Home | 目标输入、任务列表、状态徽章、刷新 |
| Workspace | 目标摘要、实时 SSE 事件、方案优先→条件→资源→评估→证据、取消/恢复、导出 MD/JSON、预算用量 |
| Settings | LLM/搜索配置状态（`***`）、预算硬限、SSRF/注入/密钥/隔离安全说明 |

状态覆盖：全部 8 个 Job 状态徽章（CREATED/RESEARCHING/NEEDS_INPUT/PAUSED/PARTIAL/FAILED/COMPLETED/CANCELLED）。空结果、加载、错误均有反馈。窄屏 `@media (max-width:600px)` 适配。所有可见控件实现真实行为（创建/启动/取消/恢复/导出/Refine）。

前端构建：`tsc --noEmit` 无错误；`npm run build` 成功（21 modules，230KB JS）。

## 5. Tests — `tests/test_m5_security.py` (19 项, 全 PASS)

| 类别 | 测试 |
|---|---|
| SSRF (10) | 公网 IP 通过；loopback/localhost/metadata/10.x/192.168/[::1]/ftp/javascript 拒绝 |
| 注入 (1) | 外部内容以 UNTRUSTED DATA 块包裹 |
| 脱敏 (3) | DeepSeek sk-key / Exa UUID / Bearer token 全部 `[REDACTED]` |
| 密钥防泄漏 (1) | `/api/settings` 不含任何真实密钥；key_preview=*** |
| 预算 (3) | tracks_usage / actions_exhaust / exhausted_yields_partial |
| 隔离 (1) | 测试路径无法逃逸 sanctioned root |

## 6. Live evidence

| 检查 | 真实调用 | 观察 |
|---|---|---|
| /api/settings 无泄漏 | curl + grep | 响应含 `***`；`sk-7dd23...`/`fa69bb10...` grep 计数 0 |
| 预算超限→PARTIAL | spike_m5_budget (真实 DeepSeek+Exa) | PARTIAL + stopped_reason；6 事件保存 |
| 前端构建 | vite build | 成功 |
| 前端 dev | vite dev | HTTP 200 |

## 7. Mock/live distinction

- 安全/预算逻辑为确定性单元测试（19 项）。
- `/api/settings` 无泄漏、预算→PARTIAL 为 **live**（真实 HTTP + 真实模型/搜索）。
- 无 mock 冒充 live。

## 8. Changed files (M5)

| 文件 | 变更 |
|---|---|
| `goalsift/budget.py` | BudgetConfig/BudgetUsage/BudgetGuard/BudgetExhausted |
| `goalsift/security.py` | is_safe_url/redact_secrets/external_content_as_data |
| `goalsift/controller.py` | guard.check 置于每个外部动作前；BudgetExhausted→PARTIAL |
| `goalsift/llm_adapter.py` | 外部文本标注 UNTRUSTED DATA |
| `goalsift/app.py` | `/api/settings`（无密钥） |
| `frontend/src/Settings.tsx` + api.ts | Settings 页 + getSettings |
| `frontend/src/App.tsx` + App.css | 导航/路由；settings/nav/kv 样式 |
| `tests/test_m5_security.py` | 19 项 |
| `spikes/spike_m5_budget.py` | live 预算证明 |

未破坏 M0–M4 行为；全测试 61 项 PASS。

## 9. Gate verdict

| Gate 条件 (07 §8) | 满足 | 证据 |
|---|---|---|
| 主用户流程无阻断 | ✅ | Home→create→start→Workspace→方案/条件/资源/证据→导出 |
| 错误态真实 | ✅ | 非法转换 400/409；FAILED/PARTIAL 真实；SSE ERROR 事件 |
| 每个可见动作有效 | ✅ | 创建/启动/取消/恢复/导出/Refine 全真实 |
| 预算超限停止新动作 | ✅ | live PARTIAL + stopped_reason |
| 注入和受限 URL 不能绕过边界 | ✅ | test_ssrf + test_injection |
| 测试路径不触及真实用户数据 | ✅ | test_isolation + 路径守卫 |
| 密钥防泄漏 | ✅ | /api/settings grep 0；脱敏 |
| UI 审阅认可信息层级与基本质量 | ⚠️ 待人工 | 构建通过 + 全状态覆盖；**人工视觉审阅不可由 AI 伪称自动通过**（spec 明确） |

**M5 Verdict: PASS**（UI 视觉质量留待 M6 人工最终确认，依规范不伪造自动美观证明）。

## 10. Known limits & next safe action

- 美观/信息层级的最终人工审阅在 M6 进行（spec：人工评估不伪称自动证明）。
- 预算 USD 未知时仅记 token 用量；DeepSeek 价格需手动核验（M6 锁定）。
- 下一步：**M6 — 最终验收与发布**：独立 E2E、跨性质案例（Agent 网页/3D Boss 战/模糊目标）、范式 vs 一次性 LLM 对比、重新部署演练、锁定依赖、`FINAL_ACCEPTANCE_REPORT.md`。


## 2026-10-10 信息布局补充验收 — PASS

按用户要求打磨首页与研究工作区，保持既有深色风格、状态与来源语义。结果优先，目标与用量转入辅助区，手机折叠背景，澄清入口始终先显示。复用现有组件，未新增依赖或收费调用。

前端 lint/build 与实际桌面、手机、平板交互检查通过；已有真实研究的历史导出，以及隔离模拟的答复/Refine 已验证。恢复基线为 `ffbd43c`。详见 [布局验收记录](acceptance/2026-10-10/layout/LAYOUT_REVIEW.md) 与截图。本轮未将模拟验证计为 M6 Live 验收。
