# 2026-10-10 当前复验 — M3 六操作与可信证据复验

**当前 Gate：PASS**。本节与 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 为本轮证据；下方旧报告保留为历史，历史数字/推测不能代替当前复验。

- 实际行为与复用：六操作均实际执行；Challenge 能新增/降级/替代条件。精确引用、引句必须来自对应真实读取来源；文档不得升 VERIFIED。CONFLICTED 必须有确切支持和反驳引句；条件关系校验引用与循环。
- 变更与证据：goalsift/controller.py、validators.py、llm_adapter.py；tests/test_runtime_integration.py。
- 执行/观察：三案例制品独立审计 PASS；网页 r3 包含 1 个真实 CONFLICTED，3 案例无 VERIFIED；假 ID/引句、双证据缺失、循环等负向测试通过。
- Mock/Live：本轮三例 DeepSeek/Exa 及一次性基线为真实收费调用；自动负向和恢复测试只替换付费提供商，不计作 Live。
- 恢复点：修改前归档与 `2be917c`；最终 `phase-a-v0.2.1`。测试在临时数据根，无目标项目执行。
- 限制与下一步：本节 Gate PASS；引句真实性不等于语义判断无误。跨域推导与建议不足如实见最终报告评分表；人工可检查依据并 Refine。

<!-- historical-report -->
# M3 Report — Full Paradigm & Evidence Validation

**Milestone**: M3 — 完整范式与证据校验  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-10  
**Verdict**: ✅ **PASS**

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §6：六操作实现、正式数据结构、证据校验测试、可检查研究 Trace；**PASS Gate 必须含负向用例**（8 项）。

---

## 1. Intended outcomes

- Define：保留用户原话、已确认要求和系统假设。
- Derive：区分 `obligation` 与 `dimension`、目标条件与方案依赖。
- Challenge：运行完整性/必要性/一致性检查，重要结果**修改条件**而非仅文本评论。
- Discover：发现整体候选与局部替代，记录真实搜索。
- Match：判断上下文、来源、缺口、组合新约束；支持全六 Assessment 状态。
- Propose：从有效 Condition/Assessment/Resource 产生方案。
- Validators：引用完整性、证据级别、状态、数据写入校验。

## 2. Six-operation implementation

| 操作 | 实现 | 证据 |
|---|---|---|
| Define | Goal.original_user_text 完整保留；requirements/constraints 带 provenance（USER_STATED/USER_CONFIRMED/SYSTEM_ASSUMED） | 模型 / spikes.spike_m3_live |
| Derive | 模型结构化输出 ConditionSpec，`obligation`×`dimension` 独立 | live run（REQUIRED+QUALITY 出现） |
| Challenge | 新 `challenge_conditions` LLM 角色；finding 可 `mark_optional`/`supersede`/`add_condition`；necessity 校验器降级偷渡的实现技术 | live: `revised=true`，1 条 REQUIRED→OPTIONAL |
| Discover | Exa 搜索 + 每 resource 来源读取 → Evidence（locator） | live: 4 resources, 5 evidence |
| Match | 模型评估全六状态；VERIFIED 自动降级 SUPPORTED；冲突→CONFLICTED | live: SUPPORTED/UNKNOWN/NOT_SATISFIED |
| Propose | 从有效 Condition/Assessment/Resource 生成；costs=UNKNOWN 不编造 | live: proposal READY_FOR_REVIEW |

## 3. Validators (deterministic trusted write gate)

`goalsift/validators.py` 新增：
- `validate_condition_necessity` — 偷渡的 React/REST 等 REQUIRED+FUNCTIONAL 标记（gate 4）
- `validate_evidence_sources(evidence, fetched_urls)` — 模型虚构 URL 必须出现在真实抓取集合中（gate 1）
- `detect_conflict` / `validate_conflict_handling` — SUPPORTS+REFUTES → 必须 CONFLICTED（gate 6）
- `validate_traceability` — Proposal→Assessment→Condition/Resource/Capability→Evidence（gate 7）
- `validate_assessment_status` — VERIFIED 需 test_context+observed_result（gate 2，M1 已有）
- `validate_references` / `validate_transition`（M1 已有）

Controller 在最终提交前运行全部校验；任一失败 → FAILED，不留下半提交对象（04 §5）。

## 4. Negative test cases (07 §6 PASS Gate 1–7)

`tests/test_validators_m3.py` — 14 项确定性测试，全 PASS：

| Gate | 测试 | 断言 | 结果 |
|---|---|---|---|
| 1 | `test_gate1_fabricated_url_rejected` | 不在真实抓取集合的 URL 被拒 | PASS |
| 1 | `test_gate1_real_url_accepted` | 真实 URL 通过 | PASS |
| 2 | `test_gate2_doc_only_cannot_be_verified` | 文档支持不可提升为 VERIFIED | PASS |
| 2 | `test_gate2_doc_only_can_be_supported` | 文档支持可为 SUPPORTED | PASS |
| 3 | `test_gate3_visual_quality_required_quality` | REQUIRED+QUALITY 合法且不被标记 | PASS |
| 4 | `test_gate4_react_as_required_functional_flagged` | "must use React" REQUIRED+FUNCTIONAL 被标记 | PASS |
| 4 | `test_gate4_rest_api_as_required_functional_flagged` | REST API 被标记 | PASS |
| 4 | `test_gate4_generic_functional_not_flagged` | 通用功能条件不被误标 | PASS |
| 6 | `test_gate6_missing_license_is_unknown` | license_claim="UNKNOWN" | PASS |
| 6 | `test_gate6_conflicting_evidence_must_be_conflicted` | 矛盾证据不可静默解决 | PASS |
| 6 | `test_gate6_conflicted_status_accepted` | CONFLICTED 状态被接受 | PASS |
| 7 | `test_gate7_traceable_chain_ok` | 完整可追溯链通过 | PASS |
| 7 | `test_gate7_untraceable_proposal_detected` | 悬空引用被检出 | PASS |
| — | `test_illegal_transition_blocked` | 非法状态转换被拒 | PASS |

## 5. Live proof (07 §6 PASS Gate 5, 7, 8)

`spikes/spike_m3_live.py` — 真实六操作运行（DeepSeek + Exa），`all_live: true`，Verdict=PASS：

| Gate | 检查 | 真实结果 |
|---|---|---|
| 5 | Challenge 修改条件 | `challenge_events=2`, `revised=true`；条件2 "Core agent-management operations" 由 challenge 的必要性反例从 REQUIRED 降为 OPTIONAL |
| 5 | 无偷渡实现技术 | `smuggled_impl_tech_remaining: []` |
| 7 | 可追溯 | `traceable: true`, problems=[] |
| 1 | 证据来源真实 | `all_fetched: true`, 5 evidence, problems=[] |
| 6 | 冲突处理 | problems=[] |
| 8 | 真实检索+匹配 | 5 conditions, 4 resources, 4 capabilities, 5 evidence, 21 assessments, proposal=true |

## 6. Mock/live distinction

- 14 项负向测试为**确定性单元测试**（仅证明内部约束，gate 明确要求）。
- `spike_m3_live` 为 **live**：真实 DeepSeek Challenge/Match + 真实 Exa 搜索/读取 + 真实 SQLite 持久化。
- 无 mock 冒充 live。

## 7. Changed files (M3)

| 文件 | 变更 |
|---|---|
| `goalsift/llm_adapter.py` | 新 `challenge_conditions` 角色 + ChallengeFinding/ChallengeReport 模型 |
| `goalsift/controller.py` | Challenge 操作（修改条件）；每资源来源读取→Evidence；necessity 降级；最终运行 evidence_sources/conflict/traceability 校验 |
| `goalsift/validators.py` | 4 个新校验器 + 导入 |
| `tests/test_validators_m3.py` | 14 项负向测试 |
| `spikes/spike_m3_live.py` | live 六操作证明 |

未破坏 M0/M1/M2 行为；全测试 26 项 PASS。

## 8. Gate verdict

| Gate 条件 (07 §6) | 满足 | 证据 |
|---|---|---|
| 1. 模型虚构 URL/证据不可成为确认来源 | ✅ | test_gate1 + live all_fetched |
| 2. 仅文档声明不可 VERIFIED | ✅ | test_gate2 |
| 3. 视觉质量可 REQUIRED+QUALITY | ✅ | test_gate3 + live |
| 4. 不默认 React/REST 为必要 | ✅ | test_gate4 + live smuggled=[] |
| 5. 有效反例促使条件修订 | ✅ | live revised=true, REQUIRED→OPTIONAL |
| 6. 缺证据许可证 UNKNOWN；冲突 CONFLICTED | ✅ | test_gate6 |
| 7. 方案可追溯 Condition→Assessment→Resource/Capability→Evidence | ✅ | test_gate7 + live traceable |
| 8. 至少一个 Live 案例证明真实检索与匹配 | ✅ | spike_m3_live PASS |

**M3 Verdict: PASS**

## 9. Known limits & next safe action

- Controller 仍以相对固定顺序运行（Challenge 在 Derive 后）；M4 不改范式，加持久化/恢复/修订。
- 匹配阶段评估依赖模型质量；当来源文本模糊时模型倾向 UNKNOWN（正确行为，非缺陷）。
- 下一步：**M4 — 持久化、任务恢复与增量研究**：05 正式持久化（已基本就绪）、04 唯一状态机（合法/非法转换、单 Job 单执行者、pause/cancel/resume、崩溃清理）、COMPLETED→Refine 新 revision、约束变更失效传播、原子提交失败不破坏数据。


## 2026-10-10 目标复核与证据补查专项增量验收 — PASS

从恢复点 `9c2f79c` 增加目标/条件/假设的明确复核，原子新修订、确认决定保持、历史兼容迁移、主要候选原文补读与重新匹配。102 项隔离测试、桌面/手机操作及独立目录中两轮真实浏览器研究通过；旧快照保留，未知/冲突/源支持与实测验证仍区分。

具体改动、失败路径、Mock/Live 证据、费用、范围与复现见 [专项验收报告](acceptance/2026-10-10/review-depth/REVIEW_DEPTH_REPORT.md)。本次费用 $0.1224152，原授权累计 $0.5211726，未达到 $1 上限。后续安全动作是未覆盖条件的定向补查与修订比较。
