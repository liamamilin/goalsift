# v0.3 P2 — 采用前检查清单

日期：2026-10-13<br>
基线：P1 Gate PASS 后的本地工作树<br>
Gate：**PASS**（确定性投影、注记隔离、桌面与窄屏操作通过）

## 结果

方案页新增采用前检查清单。用户记录当前修订的倾向方案后，清单才显示该方案的 REQUIRED 条件、未 VERIFIED 条件、Assessment 缺口、关联资源与 Evidence、现有验收方式、集成/补充工作和风险。可选且已 VERIFIED 的条件不重复列入；SUPPORTED 条件仍明确提示要在目标环境实测。无验收方式时显示“待明确标准”。

每个条目有稳定 ID 和依据指纹。状态只允许“待检查、已记录、需跟进”，注记和事件追加保存。它们不创建 Evidence，不更改 Assessment、Proposal 或已完成快照；新修订重新生成自己的条目，旧状态与备注留在历史修订并只读显示。

## 改动

- `goalsift/adoption.py`：确定性清单投影、依据哈希、版本冲突校验和检查注记事务。
- `goalsift/repository.py`：新增 `checklist_annotations` 追加式表和索引。
- `goalsift/app.py`：增加读取清单与更新条目 API。
- `frontend/src/api.ts`、`frontend/src/AdoptionChecklist.tsx`、`frontend/src/ProposalDecision.tsx`、`frontend/src/Workspace.tsx`：清单数据、方案选择后的刷新、工作进度与证据详情。
- `tests/test_adoption_checklist.py`：确定性投影、来源支持/未知/冲突、无选择、写入隔离、陈旧版本和跨修订注记用例。
- `07_DEVELOPMENT_PLAN.md`：记录 P2 Gate 状态。

## 验证证据

- `.venv/bin/python -m pytest -q tests/test_adoption_checklist.py tests/test_adoption_decisions.py`：10 项通过。
- `.venv/bin/python -m pytest -q`：全套退出码 0；原 125 项基线加 P1/P2 新增 10 项，共 135 项。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run build`：通过。Vite 保留大于 500 kB 的 bundle 提示；未阻断构建。
- `git diff --check`：通过。
- 真实本地浏览器操作使用 1280×720 桌面视口和 390×844 窄屏视口、独立 `/private/tmp` SQLite 固定夹具：先看到“请先在方案页记录倾向方案”，记录方案后立即出现 6 项清单；其中包含 SUPPORTED 实测提示、UNKNOWN 缺标准提示、CONFLICTED 冲突提示、来源链接、集成工作和风险；将一项记为“已记录”并保存备注，刷新后状态与备注仍在。
- 已重置临时视口，关闭测试页并删除隔离 UI 数据目录；未打开或写入原用户任务。没有执行真实模型/搜索调用，费用新增 `$0`。

## 下一步

进入 P3：将方案决定、检查清单与其版本/截止时间加入 Markdown/JSON 交接导出；展示实际保存的来源摘录范围及旧数据缺失范围的限制。P3 完成后再进行 P4 完整流程和发布验收。
