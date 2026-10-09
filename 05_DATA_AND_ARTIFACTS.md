# 05 — Data and Artifacts Specification

**版本：V0.2 · Phase A · 文档基线**  
**权威范围：数据语义、字段与引用、证据/Assessment 状态、修订和导出契约**

## 1. 目标与边界

将研究保存在可检查、可引用、可恢复的状态中，而非只靠聊天记录。**六种核心研究对象**：Goal、Condition、Resource、Capability、Evidence、Proposal；运行容器 Research Job，以及关系性 Assessment 和 Research Event 为实现所需的支撑结构。

这是逻辑契约，不强制每一概念成为单独数据库表或服务；不采用图数据库、向量数据库、全量事件溯源作为默认前提。Job 状态转移**唯一规则见 04**，此处不另写状态机。

## 2. 公共字段和不变量

每个对象包含 `id`, `job_id`, `created_at`, `updated_at`；需要随目标演变的对象还应有 `revision_created` 和有效性/修订信息。ID 使用稳定标识，引用明确通过 ID 而非名称解析。

- 用户原始输入不可覆盖。
- 用户确认、用户原话、系统假设严格区分。
- 结构化对象写入前检查必填字段、枚举和引用。
- 一次操作产生相关对象与关系时保证数据库提交一致性。
- 无效数据或不可信模型输出不能直接变成正式可信记录。
- 历史证据、报告修订应当可追溯；不因新资料否定旧结论就物理抹掉来源。

## 3. Research Job（运行容器）

最低字段：`id`, `original_request`, `current_goal_id`, `current_revision`, `status`, `created_at`, `updated_at`, `budget_config`, `budget_usage`, `active_run_id`, `checkpoint_ref`, `open_questions`。

`status` 使用 04 唯一定义的八个枚举；修改规则完全引用 04。每个已完成 revision 可以重新生成其当时报告，新 revision 不覆盖旧报告。研究事件可作为审计与恢复线索，但不要求重放每一个事件恢复全部状态。

## 4. Goal

字段：

| 字段 | 含义 |
|---|---|
| `statement` | 当前用户期望的结果 |
| `purpose` | 预期用途 |
| `requirements[]` | 用户要求及其来源 |
| `constraints[]` | 已确认的环境、许可、预算等约束 |
| `assumptions[]` | 未确认但分析中暂用的假设 |
| `open_questions[]` | 可能影响方案空间的问题 |
| `revision` | 当前目标修订号 |

每条 requirement/constraint 有 `provenance`：`USER_STATED`、`USER_CONFIRMED` 或 `SYSTEM_ASSUMED`。系统假设不能静默成为已确认事实。用户修改目标时增加 revision。

## 5. Condition

字段：`id`, `statement`, `obligation`, `dimension`, `origin`, `source_refs[]`, `scope`, `verification_method`, `relations[]`, `validity_status`, `revision_created`。

**两个独立维度：**

- `obligation`: `REQUIRED` / `OPTIONAL`。
- `dimension`: `FUNCTIONAL` / `QUALITY` / `COMPLIANCE` / `OTHER`。

例：`“页面具有成熟视觉效果” = REQUIRED + QUALITY`。将视觉质量写成 QUALITY 不意味着自动成为可选项。

`origin`：用户要求、定义、用途、环境、领域来源、从其他条件推导、反例审查等，应包含依据或引用。关系：`ALL_OF`, `ANY_OF`, `REQUIRES`；必须表达清楚父子/引用方向及 AND/OR 作用范围。禁止自引用和无法解释的依赖循环。

`validity_status`：`ACTIVE`, `NEEDS_REVIEW`, `SUPERSEDED`。这仅指记录对当前 revision 是否有效，**不是条件在现实中是否已经实现**。

**方案依赖**（如特定框架需要 Node 版本）默认记录于 Resource 前提、Assessment 或 Proposal，不能未经确认塞入 Goal 的 REQUIRED 条件。

## 6. Resource

字段：`id`, `name`, `kind`, `description`, `canonical_source`, `source_references[]`, `version_or_revision`, `availability`, `license_claim`, `environment`, `discovery_status`, `discovered_at`。

`discovery_status` 建议：`CONFIRMED_EXISTENCE`, `UNVERIFIED_LEAD`。只有通过实际获取或用户可核对来源确认存在才用前者；模型回忆出的名称应为待调查线索。

许可证若未查到为 `UNKNOWN`；GitHub 公开可访问不等于具有商业许可。特定版本的能力和许可证结论尽可能注明适用版本与调查时间。

## 7. Capability

字段：`id`, `resource_id`, `statement`, `preconditions[]`, `interface_or_use`, `effects[]`, `limitations[]`, `evidence_ids[]`。

能力可以是接口、视觉素材、模板结构或其他资源效果，不能要求全部能描述成 API 函数。能力存在不自动构成 Condition 满足。

## 8. Evidence（证据）

字段：`id`, `claim`, `source_type`, `source_ref`, `locator`, `excerpt_or_summary`, `retrieved_at`, `source_version`, `collection_method`, `stance`, `verification_method`, `test_context`, `observed_result`, `source_integrity_ref`（可选）。

- `stance`: `SUPPORTS`, `REFUTES`, `CONTEXT`。
- `source_type` 可以是官方文档、源码、第三方资料、用户材料、实际测试/人工审查等。
- `source_ref` 可以是 URL 或内部可解析引用；代码来源尽可能标注 commit/文件位置，页面资料尽可能保留章节、快照或引用定位。
- **证据是具体主张的依据**，不是对所有能力的通用背书。
- 保留矛盾证据和来源时效性；新来源新增 Evidence 或标记旧证据需复核，而不直接覆盖历史。

### 8.1 三种不可混淆的事实

1. **来源已获取**：可证明工具读取发生过，以及当时来源包含什么。
2. **主张受来源支持**：可证明文档/源码/测试记录支持一个限定的主张。
3. **目标条件已验证**：可证明在明确环境和验收标准下，实际观察到条件成立。

文档“声称有 API”不等于“该 API 已在目标环境运行通过”。人工视觉审查可构成限定范围的验证证据，但须记录审查人/标准/结果，不得自动当作普适审美真理。

## 9. Assessment（满足关系：最重要的关联）

字段：`id`, `condition_id`, `resource_ids[]`, `capability_ids[]`, `context`, `status`, `evidence_ids[]`, `explanation`, `gaps[]`, `assumptions[]`, `review_status`, `revision_evaluated`。

| `status` | 精确定义 |
|---|---|
| `VERIFIED` | 存在符合该 Condition 预先限定的环境/验收准则的**实际测试或人工审查记录**，且观察结果支持满足；不代表别的环境也适用 |
| `SUPPORTED` | 已有定位清晰、已读取的来源支持可行性主张，但**尚未**完成充分的实际验收验证 |
| `PARTIAL` | 只覆盖了条件的某些方面，缺口明确 |
| `NOT_SATISFIED` | 已有证据在指定上下文中表明不满足 |
| `UNKNOWN` | 尚无足够依据判断；不得猜测 |
| `CONFLICTED` | 证据对关键主张存在待解决冲突 |

`review_status`：`CURRENT` / `NEEDS_REVIEW` / `SUPERSEDED`，独立于满足状态。一个旧版本的 `VERIFIED` 若依赖已变化的条件，依旧保留历史验证记录，但在当前版本标记 `NEEDS_REVIEW`，不可作为当前的确定性覆盖。

组合 Assessment 可以引用多个资源，但必须说明资源之间的接口/语义/使用条件，以及组合后新增的缺口。`VERIFIED` **不得**由 LLM 单方面宣称或从“有官方文档”自动提升。

## 10. Proposal

字段：`id`, `title`, `summary`, `resource_ids[]`, `assessment_ids[]`, `condition_coverage`, `integration_work[]`, `new_work[]`, `uncovered_conditions[]`, `risks[]`, `assumptions[]`, `costs`, `recommendation_reason`, `validity_status`, `revision_created`。

`validity_status`：`CANDIDATE` / `READY_FOR_REVIEW` / `NEEDS_REVIEW` / `SUPERSEDED`；READY_FOR_REVIEW 是可供人审查，**不代表用户已选择，更不授权执行**。

`costs` 支持事实价格、带依据的估计区间、定性判断或 UNKNOWN，不允许无依据的精确数字。没有可信可行路径时可以输出经过说明的空 Proposal Set，而不是造一个假方案。

## 11. Research Event（运行记录）

字段：`event_id`, `job_id`, `revision`, `run_id`, `action_type`, `status`, `started_at`, `ended_at`, `related_object_ids[]`, `tool_result_ref`, `usage`, `error`。

保存真实工具调用、目标更改、重要审查、来源获取、证据冲突、评价变更和状态转换等，可供 SSE 恢复与审计。不要求记录隐私敏感的全部模型原始推理文本；密钥、token、敏感文件内容不得泄漏到导出或日志。

## 12. 修订与失效传播

最小有向影响路径：

```text
Goal/constraint changed
  └─> affected Condition NEEDS_REVIEW
         └─> dependent Assessment NEEDS_REVIEW
                └─> dependent Proposal NEEDS_REVIEW

Resource/Capability/Evidence changed
  └─> dependent Assessment NEEDS_REVIEW
         └─> dependent Proposal NEEDS_REVIEW
```

用户修改条件时必须产生新的 Goal revision 或清晰的研究变更记录。无关条件、资源及有效来源尽量复用；旧证据仍保留但可能因版本/时效失去适用性。

不要求实现通用自动推理图数据库；使用显式 ID 引用、数据库事务与受影响对象查询即可。不得将引用不存在的对象提交为正式状态。

## 13. Artifacts / 导出

用户侧提供六个**逻辑视图**，不是六份数据库或独立文件：

1. Goal Brief：目标、约束、假设与待确认问题。
2. Condition Model：重要条件及依赖。
3. Resource Catalog：真实资源、能力、版本/许可与来源。
4. Satisfaction Analysis：Assessment 和明确缺口。
5. Proposal Set：候选路径与建议依据。
6. Open Questions：未知、冲突、下一步需核查事项。

交付默认提供可读 **Markdown**，另提供机器可读 **JSON**。两者应从同一个已校验的**当前有效 revision**生成；LLM 可润色说明，不能导出新的未经调查的资源事实。导出包含研究日期/范围/限制和关键来源。

## 14. 机器不变量与测试

- 核心对象 ID 唯一，关联对象存在，Capability 归属 Resource。
- Condition 分类使用双维度，来源与适用范围不可缺失。
- 阻止非法条件依赖、无效枚举、悬空 Assessment/Proposal。
- `SUPPORTED` 有可定位来源；`VERIFIED` 有匹配条件范围的实际观察记录。
- 保留冲突证据，不让来源不符的判断过关。
- 修改目标/资源重要依据后，下游判断必须进入待复核状态。
- 事务中途失败不留下半提交的对象关系。
- 导出不出现过期的确定性结论，不暴露敏感凭据。
- 能从用户可见 Proposal 追溯到 Condition、Resource/Capability、Assessment 和 Evidence。

## 15. 数据层完成标准

在真实研究任务中，系统能够保存全部必要对象与引用、恢复、增量修订、查看证据和从当前数据生成一致的 Markdown/JSON；受控负向测试能拦截虚假 `VERIFIED`、非法状态与过期评价。存储引擎选择由 06 与 M1 验证决定。
