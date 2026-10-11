# 定向补查与修订对比增量验收

日期：2026-10-11。恢复基线：`a57475b`。专项结论：**PASS**。

用户同意继续已提出的两项开发：针对未覆盖条件补查，以及比较修订变化。沿用此前真实服务授权，累计新增费用上限 $1；本轮服务端上限 $0.12，浏览器提交上限 $0.10。没有重新执行全部 M0–M6 或扩大 Phase A 至方案执行。

## 实现结果与复用

- 已完成的当前任务可从工作区、方案缺口或条件启动补查。表单选择 1–8 个条件，可限定最多两个已有候选、调查问题和本轮费用。未保存的条件复核草稿会禁用补查；历史只读。
- 补查原子保存旧快照、克隆条件及明确确认来源、创建新修订与范围检查点。目标不变，因此保留已完成的 Define/Derive/Challenge；重新执行来源收集、Match 和 Propose。未受影响评价显式复用；更新来源的候选全部条件重新核查。新来源已提交但模型未成功时，旧判断立即 NEEDS_REVIEW，不能保持虚假的当前确定性。
- 每轮只搜索一次、最多增加两个候选，目录累计上限 24；指定候选时过滤其他搜索结果。GitHub 别名按现有来源身份归一。暂停、恢复、取消沿用现有执行所有权和事务；恢复保持用户设定的上限、已读 URL 与匹配进度。
- 修订比较只读取 SQLite 投影，不调用收费服务。条件按谱系对齐，旧记录仅对齐唯一相同原文；不同标点、C++/C# 等不会被合并。展示条件及确认来源、候选、实际来源读取/版本、评价前后解释、覆盖与各轮费用。内容变化与相同内容重读分开；阶段结果明确标记。新增证据记录不冒充已满足条件，覆盖变化不宣称整体方案更优。
- 导出包含补查范围、基准修订、问题、预算与沿用评价数。旧快照不回填；新谱系字段可空，插入使用显式列名，兼容旧数据库列顺序。
- 复用 React、Radix Dialog/已有组件、FastAPI、Pydantic、现有 DeepSeek/Exa/GitHub 适配器、SQLite、预算和校验器。没有新增依赖，没有执行外部仓库代码。

主要文件：`goalsift/targeted_research.py`、`revision_diff.py`、`controller.py`、`repository.py`、`models.py`、`app.py`、`exporter.py`；`frontend/src/TargetedResearch.tsx`、`RevisionCompare.tsx`、`Workspace.tsx`、`GoalReview.tsx`、`api.ts`；`tests/test_targeted_diff.py`。03/04/05、README 和 M3/M4/M5/最终报告同步追加本次结果。

## 自动化验收：PASS，提供商使用隔离 fixture

命令：`.venv/bin/python -m pytest -q`，最终 **114 passed**，见 `pytest.txt`。`test-inventory.txt` 为实际收集清单；`npm --prefix frontend run lint` 与 `npm --prefix frontend run build` 成功，见 `lint.txt`、`build.txt`。

新增 12 项用例覆盖：限定/不限定范围及未受影响评价复用；候选更新影响全部条件；所属对象与陈旧修订拒绝；并发/执行者冲突；预算预检与恢复不扩大上限；暂停/重启/恢复/取消后的无迟到写入；已有八个候选后最多新增两个；明确改写的谱系与旧数据库迁移；旧记录 C++/C# 区分、条件移出不虚报覆盖改善；API schema/CSRF/状态/缺失快照；真实 Controller/API/SQLite 的提交、历史/当前对比与导出；资料提交后预算中断时旧评价及时失效；旧候选别名合并无悬空评价。

测试通过临时目录和 SQLite 实际数据库路径断言隔离，不使用用户数据库，不发模型/搜索收费请求。构建保留约 554 kB JS 分包提示，没有编译或 lint 错误；本轮未改构建阈值来隐藏提示。

## 实际浏览器验收：PASS

使用 Codex 浏览器实际操作，不将构建成功替代界面验收。独立 fixture 服务端口 61326，数据库 `/private/tmp/goalsift-targeted-qa-8ldufnlh/goalsift.sqlite`。`offline_server.py` 证明目录及 SQLite 路径隔离；提供商为明确模拟数据。

从缺口选择“启动暂停接口”、限定 Dash、费用 $0.05，提交到真实 API/Controller/SQLite。结果修订 2 COMPLETED，覆盖 2/3→3/3，沿用三项评价，README fixture 版本 sha-1→sha-2，一项 UNKNOWN→SUPPORTED。旧修订 1 保留。这只证明产品交互与状态链路，不计为 Live 模型验收。

桌面 1280×720 检查提交、阶段/完成对比、基准选择、历史只读。窄屏实际 DOM `innerWidth=390`、`innerHeight=844`、`scrollWidth=390`；补查表单正文可滚动，取消/提交固定可见，Escape 关闭。确认一项条件产生未保存草稿后，头部及条件补查均禁用；撤销恢复入口。主预览 8000 的原任务已加载两个新入口，免费比较可见。

截图：`offline-scope.png`、`offline-comparison-desktop.png`、`offline-comparison-mobile.png`、`offline-scope-mobile.png`。视觉验收是对实际布局、可读性、溢出和操作可达性的检查，不伪称自动证明美观。

## 独立真实服务验收：PASS

真实 DeepSeek + Exa + GitHub 公共只读 API；没有新增收费供应商。`live_server.py` 先以 SQLite backup 复制上轮隔离研究，创建 `/private/tmp/goalsift-targeted-live-ljzczi7q/goalsift.sqlite`，实际数据库路径断言；不使用或修改原应用数据。最终服务端口 61894。

浏览器实际从 `job_7f396bd6fd70462b` 修订 2 的未覆盖条件进入表单：仅选 Agent 状态展示、限定 builderz-labs/mission-control、问题要求无依据保留未知，预算 $0.10。一次提交，修订 3 **COMPLETED**，用时 34.02 秒。

| 检查 | 实际结果 |
|---|---|
| 目标及用户确认条件 | 原意不变，7 项均仍 USER_CONFIRMED |
| 候选与评价 | 8 候选、56 当前评价；49 项沿用，选中候选 7 项重新核查 |
| 真调用 | 4 次模型、2 次工具动作：仓库资料读取和一次 Exa 搜索；六个预算动作 |
| 实际来源 | 5 条同内容重读，1 条新增 `docs/agent-setup.md`；18 条新增证据记录含收据与主张 |
| 方案覆盖 | 5/7→5/7；状态展示仍 PARTIAL，响应式仍 UNKNOWN |
| 文档与实测 | 无 VERIFIED；没有运行或部署候选项目 |
| 历史 | 修订 2 数据与来源数据库快照逐字相同 |
| 引用与导出 | 对象归属/引用、方案可追溯链、状态证据校验通过；JSON/Markdown 一致 |
| 免费比较 | 重复比较前后预算用量完全不变 |

证据：`live-before.json`、`live-after.json`、`live-events.json`、`live-diff.json`、`live-history-r2.json`、`live-r3-export.json/.md`、`live-scope.png`、`live-comparison-desktop.png`。历史修订选择器实际显示只读，补查按钮不存在。模型解释会变化，即使状态相同也算评价内容变化；不是七项状态提升。

`PYTHONPATH=. .venv/bin/python acceptance/2026-10-11/targeted-diff/audit.py` 只读审计 PASS，见 `audit.json`。审计同时逐表比较原预览库与升级前 SQLite 备份，11 张表既有列值一致。API 新增兼容默认字段，所以 API 字段集合不完全相同；这不是用户结果被修改。早期审计脚本发现参数顺序和事件投影字段名不符，已修正后完整执行，未触发额外研究请求。

## 费用与交付

本轮应用记录费用 **$0.017689**，无未知费用或未结预留。此前保守累计 $0.5211726，本次后累计 **$0.5388616**，剩余 **$0.4611384**，见 `fee-ledger.json`。费用依据模型保守 token 单价与 Exa 返回成本，不是提供商最终账单。所有 UI fixture 和修订比较无收费调用。

当前配置值精确匹配扫描源文件与本次制品，结果见 `secret-scan.json`；不读取或输出凭据字面量。文件校验见 `manifest.sha256`。原 `.goalsift_data` 不写入；原预览保留，临时验收服务完成后停止。

已知范围：定向补查最多一轮搜索，不能保证发现全部替代方案；GitHub 补读仍限定公共默认分支的实际根目录文件，Exa 内容由提供商提供。谱系不对历史不同原文作相似推断。模型对原文含义可能误读，文档研究不代替目标环境验收。后续建议优先积累真实目标的失败/未知案例，再决定是否扩大检索和引入采用前人工验收记录；当前不启动生产方案执行。
