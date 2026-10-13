# v0.3 P1 — 方案选择记录

日期：2026-10-13<br>
基线：`cef4c61588008ae44f2d40f5d598d8bf1d20c909`<br>
Gate：**PASS**（后端/API、持久性、历史语义和临时浏览器流程通过）

## 结果

完成后端追加式方案决定存储与 API，并将“你的方案决定”面板加入方案页。支持记录倾向、修改理由、撤回和再次选择；页面展示动作历史。新修订中旧决定显示为待重新确认，选择旧修订时从该修订快照读取方案并保持只读。保存与审计事件同事务提交。

研究快照只读不变。选择不会创建 Evidence、改 Assessment 或启动研究。选中的只是当前修订单一有效 Proposal，不允许从候选资源列表伪造备选路径。

## 改动

- `goalsift/adoption.py`：选择校验、历史投影、并发检查和事务写入。
- `goalsift/repository.py`：增加 `proposal_decisions` 表及读取/追加方法。
- `goalsift/app.py`：增加 GET/PUT `/api/jobs/{id}/decision`。
- `frontend/src/api.ts`、`frontend/src/ProposalDecision.tsx`、`frontend/src/Workspace.tsx`：类型、请求和方案页交互。
- `tests/test_adoption_decisions.py`：SQLite/API、迁移、负向及回滚用例。
- `03_USER_WORKFLOW.md`、`04_AGENT_RUNTIME.md`、`05_DATA_AND_ARTIFACTS.md`：P0 契约；`07_DEVELOPMENT_PLAN.md` 更新进度。

## 验证证据

- `.venv/bin/python -m pytest -q tests/test_adoption_decisions.py`：6 项通过。
- `.venv/bin/python -m pytest -q`：全套通过，退出码 0（原 125 项基线 + 6 项新用例，共 131 项）。无真实模型/搜索调用。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run build`：通过；Vite 提示打包 JS 大于 500 kB，这是已有构建警告，未阻断构建。
- `git diff --check`：通过。
- 在 1280×720 的隔离浏览器页（`127.0.0.1:8011`，测试数据位于 `/private/tmp/goalsift-p1-ui-20261013`）实际记录理由、修改理由、撤回、再次选择、刷新恢复、切换到修订 2 查看旧决定待重新确认，以及查看修订 1 的只读决定。页面提示选择不代表满足/执行；修订 1 与修订 2 的方案分别从自己的快照读取。
- 该浏览器夹具使用固定测试数据；未写入用户原有 `job_8a48c356fcd049ab` 或原始项目数据库。

## 限制与下一步

P1 没有进行收费 Live 调用，费用新增 `$0`。检查清单尚未实现；由 P2 接续。本报告不代表 P2–P4 或 v0.3.0 通过。
