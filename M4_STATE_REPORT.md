# 2026-10-10 当前复验 — M4 持久化、恢复和修订复验

**当前 Gate：PASS**。本节与 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 为本轮证据；下方旧报告保留为历史，历史数字/推测不能代替当前复验。

- 实际行为与复用：原子单所有权、嵌套事务、持久检查点和逐资源付费结果，恢复不重复已提交批次；异常进程恢复 PAUSED；新修订失效旧判断，快照保持只读。共享 SQLite 连接整个操作加锁，修复 Live 并发崩溃。
- 变更与证据：goalsift/repository.py、controller.py、app.py。
- 执行/观察：Live 网页崩溃后恢复并完成，r1/r2/r3 可追踪；Live Game PAUSED/Resume 完成；浏览器取消 Needs Input。并发读写、在途取消晚提交、快照/当前视图、rollback 和重启隔离测试均通过。
- Mock/Live：本轮三例 DeepSeek/Exa 及一次性基线为真实收费调用；自动负向和恢复测试只替换付费提供商，不计作 Live。
- 恢复点：修改前归档与 `2be917c`；最终 `phase-a-v0.2.1`。测试在临时数据根，无目标项目执行。
- 限制与下一步：本节 Gate PASS；在途请求不能精确回滚或保证账单可追回，未对账请求保留费用预留。

<!-- historical-report -->
# M4 Report — Persistence, Task Recovery & Incremental Research

**Milestone**: M4 — 持久化、任务恢复与增量研究  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-10  
**Verdict**: ✅ **PASS**

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §7。

---

## 1. Intended outcomes

- 05 规定的正式持久化、引用约束、修订和事件（M2 已基本就绪，本里程碑补全）。
- 04 唯一状态机：合法/非法转换、单 Job 单执行者、pause/cancel/resume 与崩溃清理。
- COMPLETED 后 Refine 创建新 revision，保留前版结果。
- 新约束触发 Condition/Assessment/Proposal 受影响失效传播。
- 原子提交，失败不破坏已有效数据；无关资料尽量复用。

## 2. Implementation

| 能力 | 实现 |
|---|---|
| 状态机 | `validate_transition`（04 唯一权威表）；app 端点每次命令检查前提 |
| 单执行者 | `active_run_id` + 数据库锁；`start`/`_schedule_run` 拒绝重复启动 |
| 暂停/取消 | `_stopped()` 检查点置于 Discover/Match/Propose 前；取消后不再发新外部动作 |
| 崩溃恢复 | `recover_orphans()`：启动时将所有 RESEARCHING Job 恢复为 PAUSED（04 §9） |
| Refine | `new_revision()`（COMPLETED→RESEARCHING + 旧版失效传播）+ `add_constraint()` + `_schedule_run()` |
| 失效传播 | `mark_revision_needs_review()`：旧 revision 的 Condition→NEEDS_REVIEW、Assessment→NEEDS_REVIEW、Proposal→NEEDS_REVIEW（05 §12） |
| 原子提交 | `transaction()` 上下文管理器，异常→ROLLBACK |

## 3. Deterministic tests — `tests/test_m4_state.py` (16 项, 全 PASS)

| Gate | 测试 | 断言 |
|---|---|---|
| 1 | `test_gate1_transitions` (9 cases) | 合法转换通过；非法（CANCELLED→RESEARCHING、CREATED→PAUSED、PAUSED→COMPLETED）明确失败 |
| 2 | `test_gate2_concurrent_start_one_executor` | 同一 Job 二次 start 返回 False；仅一个 active_run_id |
| 3 | `test_gate3_cancel_stops_external_actions` | 取消后 `_stopped` 检查点阻止外部搜索调用 |
| 4 | `test_gate4_orphan_recovery` | RESEARCHING+active_run_id → recover → PAUSED |
| 4 | `test_gate4_no_orphans_when_clean` | CREATED Job 不被误恢复 |
| 4 | `test_gate4_app_startup_recovery_isolated` | 隔离 repo 恢复验证（不触及 live DB） |
| 5 | `test_gate5_refine_new_revision_and_invalidation` | new_revision→rev2；旧 Condition/Assessment/Proposal 均 NEEDS_REVIEW |
| 6 | `test_gate6_atomic_failure_no_half_objects` | 事务中途 raise → ROLLBACK，无半提交 condition |

## 4. Live proof (gates 4 & 5)

| Gate | 真实操作 | 观察 |
|---|---|---|
| 4 | 创建 Job→start→RESEARCHING 中 `pkill uvicorn`→重启 | orphan RESEARCHING Job 启动时恢复为 **PAUSED**；已提交数据完整 |
| 5 | COMPLETED Job（rev1）→ `POST /input` constraint "只能使用允许商业使用的开源方案" | refine_ok: HTTP 200, revision=2, RESEARCHING→**COMPLETED**；11 条新条件；Proposal 生成；评估含 SUPPORTED/UNKNOWN/**NOT_SATISFIED**（闭源资源因商用约束失败） |
| 5 | 旧版失效 | rev1 的 Condition/Assessment/Proposal 标 NEEDS_REVIEW（新 revision 不覆盖） |

约束 "只能商用开源" 导致 NOT_SATISFIED 出现——正是 01 §9 Revision 案例与 05 §12 失效传播的预期行为。

## 5. Mock/live distinction

- 16 项为确定性单元测试（含 mock controller）。
- 崩溃恢复与 Refine 为 **live**：真实 uvicorn 进程 kill/重启 + 真实 SQLite 持久化 + 真实模型 revision 2 研究。
- 无 mock 冒充 live。

## 6. Changed files (M4)

| 文件 | 变更 |
|---|---|
| `goalsift/repository.py` | `recover_orphans`、`mark_revision_needs_review`、`new_revision`、`add_constraint` |
| `goalsift/controller.py` | `_stopped` 检查点；`_schedule_run`；`refine`；取消检查置于 Discover/Match/Propose 前 |
| `goalsift/app.py` | 启动 `recover_orphans()`；`/api/jobs/{id}/input` 实现 Refine |
| `pyproject.toml` | `asyncio_mode=auto` |
| `tests/test_m4_state.py` | 16 项测试 |
| `requirements.txt` | + pytest-asyncio |

未破坏 M0–M3 行为；全测试 42 项 PASS。

## 7. Gate verdict

| Gate 条件 (07 §7) | 满足 | 证据 |
|---|---|---|
| 1. 合法转换成功，非法明确失败 | ✅ | test_gate1 |
| 2. 同一 Job 并发启动不能生成两个执行者 | ✅ | test_gate2 |
| 3. PAUSE/CANCEL 后不得新发外部动作 | ✅ | test_gate3 + _stopped 检查点 |
| 4. 崩溃重启后已提交数据仍在且可安全 Resume | ✅ | live orphan→PAUSED |
| 5. COMPLETED 后新约束→新 revision，受影响对象待复核；无关事实仍可用 | ✅ | live refine rev2 + invalidation |
| 6. 结构/引用提交失败不留下半套对象 | ✅ | test_gate6 ROLLBACK |

**M4 Verdict: PASS**

## 8. Known limits & next safe action

- 不承诺精确续接在途模型/搜索调用（04 §9 明确）；保证已提交数据持久。
- 失效传播为 revision 粒度（标记 NEEDS_REVIEW），未做细粒度自动依赖推理（05 §12 允许显式 ID 引用 + 受影响查询）。
- 下一步：**M5 — 产品体验、成本与安全**：完整 Home/Workspace/Settings 全路径、真实 UI 审阅、预算硬限 UI、密钥防泄漏、SSRF/注入防护、日志脱敏、内部数据与用户项目隔离实测。


## 2026-10-10 目标复核与证据补查专项增量验收 — PASS

从恢复点 `9c2f79c` 增加目标/条件/假设的明确复核，原子新修订、确认决定保持、历史兼容迁移、主要候选原文补读与重新匹配。102 项隔离测试、桌面/手机操作及独立目录中两轮真实浏览器研究通过；旧快照保留，未知/冲突/源支持与实测验证仍区分。

具体改动、失败路径、Mock/Live 证据、费用、范围与复现见 [专项验收报告](acceptance/2026-10-10/review-depth/REVIEW_DEPTH_REPORT.md)。本次费用 $0.1224152，原授权累计 $0.5211726，未达到 $1 上限。后续安全动作是未覆盖条件的定向补查与修订比较。


## 2026-10-11 定向补查与修订对比专项增量验收 — PASS

从恢复点 `a57475b` 增加按已有条件、候选与本轮费用上限的定向新修订；复用未受影响评价，新增资料及时失效相关旧判断。修订对比读取实际快照/当前投影，展示条件谱系、来源版本、评价解释、覆盖与各轮费用，不触发收费服务。

114 项隔离自动化测试、前端 lint/build、桌面与 390×844 窄屏交互通过；独立 SQLite 副本中的一次真实浏览器补查 COMPLETED，7 项已确认条件保留、49 项评价沿用、选中候选的 7 项重核查，覆盖仍为 5/7。历史快照逐字不变，原预览 11 张表的既有数据与升级前备份一致。真调用记录费用 $0.017689，授权累计 $0.5388616，低于 $1；未知与来源支持不冒充实测。

改动、复用、命令、负向测试、Mock/Live 区分、费用及范围见 [专项验收报告](acceptance/2026-10-11/targeted-diff/TARGETED_DIFF_REPORT.md)。这是本轮增量验收，不重写既有 M0–M6 结果。下一步优先收集真实目标的失败与未知案例，继续改进研究质量。
