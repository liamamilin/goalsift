# Final Acceptance Report — Phase A

**Project**: GoalSift — From Goals to Viable Paths  
**Phase**: A · V0.2 · Specification Baseline  
**Date**: 2026-10-10  
**Verdict**: ✅ **PASS** — Phase A complete

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §9：全部必需主功能和安全门槛已通过；真实模型与搜索在已授权预算内执行；状态恢复及修订功能可用；案例结果可追溯并真实；界面审阅完成；文档可复现；无阻断性未修缺陷。

---

## 1. What was built

一个**目标驱动的 AI 方案研究应用**（本地优先）。用户输入期望结果；应用推导并挑战成立条件、发现真实已有资源、评估证据支撑的适用性、提出可供人选择的路径。Phase A **不执行**选定方案。

范式：**Define → Derive → Challenge → Discover → Match → Propose**（研究操作，非六个 Agent）。

技术栈（M1 实测锁定）：Pydantic AI 2.54.0 + DeepSeek + Exa + FastAPI 0.143.0 + SQLite 3.51.0 + Pydantic 2.14.0 + React/TS/Vite 8.3.4。

## 2. Milestone trail (all PASS)

| M | 里程碑 | Commit | 关键证据 |
|---|---|---|---|
| M0 | 安全基线 | `2640561` | git 基线；12 隔离断言；密钥 gitignored |
| M1 | 技术 Spike | `42421cb` | live 模型/搜索/来源读取；SUPPORTED≠VERIFIED；锁定栈 |
| M2 | 最小纵向链路 | `ab01f31` | 浏览器→真实模型/搜索→有来源方案；重启持久化 |
| M3 | 完整范式+证据 | `a25fc12` | Challenge 修改条件；14 负向用例；可追溯 |
| M4 | 持久化+恢复+修订 | `f63b685` | 崩溃→PAUSED；Refine 新 revision+失效传播；原子回滚 |
| M5 | 体验+成本+安全 | `e7fd54d` | 预算→PARTIAL；SSRF/注入/脱敏；Settings 无泄漏 |
| M6 | 最终验收 | (本提交) | 3 跨域案例；范式对比；重新部署演练 |

## 3. Cross-nature live cases (07 §9)

| 案例 | 输入 | 真实结果 | 规范行为 |
|---|---|---|---|
| Web | 像 Agent 管理网页 | 4 真实资源(Exa)；5 evidence；SUPPORTED/UNKNOWN/NOT_SATISFIED；proposal READY_FOR_REVIEW | 不默认自造 UI；报告许可/集成缺口 |
| Game | 3D Boss 战系统 | 5 条件(战斗循环/伤害判定)；4 真实游戏资源；honest UNKNOWN | 体验/组合不可仅靠局部能力保证(01§7) |
| Ambiguous | "做一个很好的产品" | **NEEDS_INPUT** + 聚焦澄清问题 → 用户答复 → COMPLETED(7 条件/4 资源/方案) | 指出决定性歧义并询问，不编造产品定义(01§9) |

三案例均 `all_live`：真实 DeepSeek + 真实 Exa；无 mock 冒充。

## 4. Paradigm vs one-shot LLM comparison (07 §9)

同输入（Web 目标），不预设范式必胜：

| 维度 | 一次性 LLM | 范式研究 |
|---|---|---|
| 真实来源 URL | 0 | 4（Exa 实查） |
| 证据/locator | 无 | 5 条 Evidence（含 locator） |
| 许可证 | 未提及 | UNKNOWN（不推定商用） |
| 条件 vs 实现手段 | 立即规定 React/Next.js 为必要 | 区分目标必要性与方案依赖；Challenge 降级偷渡技术 |
| 可追溯性 | 无 | Proposal→Assessment→Condition/Resource/Capability→Evidence |
| 缺口/风险 | 未暴露 | 显式 UNKNOWN/NOT_SATISFIED + risks |

可观察、非编造的差异：一次性报告凭记忆造架构；范式查真实资源、保留证据、暴露缺口。结论基于证据而非预设。

## 5. Reproducibility / redeploy drill (07 §9)

干净环境演练：
1. `python3 -m venv .venv` → `pip install -r requirements.txt` → 成功。
2. `.venv/bin/python -c "import goalsift.app"` → OK。
3. `.venv/bin/python -m pytest` → **61/61 PASS**（隔离 venv）。
4. `.venv/bin/python -m uvicorn goalsift.app:app` → health 200；create job；export MD；settings(loopback, keys 配置)。

## 6. Test summary

| 套件 | 项 | 结果 |
|---|---|---|
| M0 isolation | 12 | PASS |
| M3 validators (negative) | 14 | PASS |
| M4 state/recovery/revision | 16 | PASS |
| M5 security/budget | 19 | PASS |
| **合计** | **61** | **全 PASS** |

Live 证据（非 mock）：M1 四 Spike、M2 E2E、M3 六操作、M4 崩溃+Refine、M5 预算→PARTIAL+Settings 无泄漏、M6 三案例+对比+重新部署。

## 7. Security thresholds (07 §8)

| 门槛 | 状态 |
|---|---|
| SSRF：loopback/private/metadata 拒绝 | ✅ test_ssrf (10) |
| 提示注入：外部文本作 UNTRUSTED DATA | ✅ test + adapter |
| 密钥防泄漏：`.env` 服务端；`/api/settings` 仅 `***` | ✅ grep 0 命中 |
| 日志脱敏：sk/UUID/Bearer → `[REDACTED]` | ✅ test |
| 隔离：路径守卫；测试不触及用户数据 | ✅ test |
| 预算硬限：超限→PARTIAL，停止新外部动作 | ✅ live + test |
| 绑定 loopback | ✅ settings.binding |

## 8. Invariants preserved (AGENTS.md §6)

- 用户原话保留；确认/假设分开 ✅
- 条件双维度独立（REQUIRED+QUALITY 合法）✅
- 目标条件 vs 方案依赖区分 ✅
- 真实来源，不虚构 URL/许可/版本 ✅
- SUPPORTED≠VERIFIED；UNKNOWN/CONFLICTED/PARTIAL/NOT_SATISFIED 各自独立 ✅
- 整系统组合检查 ✅
- Condition→Assessment→Resource→Evidence 可追溯 ✅
- Phase A 不执行方案 ✅

## 9. Known limits

- 美观/信息层级的最终判断为**人工审阅**（spec：人工评估不伪称自动证明美观）。前端构建通过、全状态覆盖，但视觉质量需人确认。
- DeepSeek `deepseek-chat` 映射到 `deepseek-flash`；如需更强推理用 `deepseek-v4-pro`。
- 预算 USD 未知时仅记 token 用量；价格需手动核验。
- 不承诺精确续接在途模型/搜索调用（04 §9）；保证已提交数据持久。
- 失效传播为 revision 粒度（标记 NEEDS_REVIEW），未做细粒度自动依赖推理（05 §12 允许）。
- V0.2 主要覆盖软件/数字生产资源；专业现场条件领域暴露边界（01 §7）。
- Phase B（选定方案后的受控生产执行）保留为未来独立阶段。

## 10. Deliverables

- 可运行源代码：`goalsift/`（后端）+ `frontend/`（前端）。
- 配置模板：`.env.example`。
- 启动说明：`README.md`。
- 测试：`tests/`（61 项）+ `spikes/`（live 证据）。
- 三实际案例：见本报告 §3 + 各 M 报告。
- 导出样例：`/api/jobs/{id}/export`（MD + JSON）。
- 已知限制：本报告 §9。
- 可恢复 Git tag：`phase-a-v0.2`。

## 11. Verdict

**Phase A: PASS.** 全部里程碑 M0–M6 通过；真实模型与搜索在授权预算内执行；状态恢复与修订可用；案例可追溯并真实；安全门槛满足；无阻断性未修缺陷。

> 服务不可用应记 BLOCKED；本报告所有 Live 证据均为真实执行，无伪造。
