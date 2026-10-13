# v0.3 P3 — 交接包与资料阅读

日期：2026-10-13<br>
基线：P0–P2 Gate PASS 后的本地工作树<br>
Gate：**PASS**（导出一致性、注记截止、资料摘录和桌面/窄屏浏览器检查通过）

## 结果

Markdown 与 JSON 现在将研究修订和追加式用户注记一起冻结。交接数据记录研究修订、事件游标、最近注记时间、方案选择/理由/历史、清单状态/备注/依据版本。导出 API 支持 `revision` 与 `annotation_cursor`；同一数据库读取事务内取得研究视图和注记，较晚的并发写入不会混入当前包。重复指定同一修订和游标可重现相同内容（导出时间字段除外）。

没有当前选择时显示“待决策”；新修订中的旧选择标为“需要重新确认”，旧注记不会显示成当前选择或当前检查项。费用字段未知时报告直接标明未知。资料详情会显示已保存文档的实际提供摘录、半开区间、读取时间、版本和省略提示；旧记录没有范围时明确说明无法还原。区间按 Unicode 码点读取。

## 改动

- `goalsift/repository.py`：按事件游标读取决定和检查注记，审计事件与注记 ID 精确关联。
- `goalsift/adoption.py`：按冻结修订/游标投影决定状态、历史、清单状态和依据版本。
- `goalsift/exporter.py`：统一构造 Markdown/JSON 交接包，加入选择、理由、检查项、版本、截止时间、费用提示和实际摘录。
- `goalsift/app.py`：导出 API 接受 `annotation_cursor`，在一致事务中生成两种格式。
- `frontend/src/Workspace.tsx`、`frontend/src/api.ts`：资料详情展示实际摘录、范围、读取时间和来源版本；可生成指定修订/注记游标的导出 URL。
- `03_USER_WORKFLOW.md`、`04_AGENT_RUNTIME.md`、`05_DATA_AND_ARTIFACTS.md`、`README.md`：记录用户可见导出行为、游标 API、数据语义和当前 Gate 状态。
- `tests/test_adoption_checklist.py`：新增游标前后对比、历史重现、无选择、Unicode 码点、多格式一致和并发编辑隔离用例。
- `P3_HANDOFF_EXAMPLE.md`、`P3_HANDOFF_EXAMPLE.json`：由固定隔离夹具生成的脱敏交接样例。

## 验证证据

- `.venv/bin/python -m pytest -q -o addopts=''`：**140 passed**。
- `npm --prefix frontend run lint`：通过。
- `npm --prefix frontend run build`：通过。保留 Vite 大于 500 kB 的 chunk 提示。
- `git diff --check`：通过。
- API 用例验证 Markdown 与 JSON 对应同一修订及事件游标；游标之前的导出不包含较晚注记，指定不存在的游标返回 400；历史修订/游标的业务内容可重复生成。
- 并发测试在导出已读取研究修订、尚未读取注记时尝试保存清单。写入等待读取事务结束；当次交接只含原游标内容，下一次导出才显示新记录。
- 在隔离 SQLite 固定夹具的真实浏览器页 `127.0.0.1:8011` 检查资料详情和交接页面：桌面 `1280×720`、窄屏 `390×844`。窄屏 `documentElement.scrollWidth` 为 `390`，没有横向溢出。页面显示 `🙂状态` 的真实保存摘录、`[2, 5)` 范围、读取时间、`commit-abc123` 版本、省略提示及检查记录。
- 浏览器夹具位于 `/private/tmp/goalsift-p3-ui-20261013`，所有内容均为固定测试数据；未访问用户原有任务或调用真实模型/搜索服务，新增费用 `$0`。

## 限制与下一步

样例仅证明导出与摘录展示行为，不代表外部来源质量或目标环境验收。进入 P4：隔离全流程回归、真实浏览器流程、受预算约束的 Live 检查、最终验收报告和 v0.3.0 发布准备。
