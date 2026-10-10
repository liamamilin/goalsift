# 目标复核与证据补查增量验收 — PASS

日期：2026-10-10。用户同意先完成开发计划的第 1、2 项。代码恢复点 `9c2f79c`；复用现有 React/shadcn、Pydantic AI、Exa、httpx、SQLite 与验证器，没有新增依赖。Phase A 研究边界保持一致。

## 实际交付

- 条件页区分用户原话、目标理解、前提/假设与系统推导。确认、修改、移出条件，确认/移除假设与调整目标理解先成为可撤销草稿。提交后原子创建新修订，拒绝陈旧页面、异任务条件、运行中修改与重复请求。旧条件/评价/方案待复核；旧完成快照保留。
- 新字段 `Condition.provenance`、Goal 的两类 review decisions 以增量数据库迁移加入。旧条件默认待确认；旧历史 JSON 不回填。确认不提升能力满足状态。明确条件在后续 Challenge/Refine 中保持，移出/替换原文过滤并作为用户决定交给模型。
- 主要候选最多补查两个不同来源。GitHub 首页、README、原始文件地址合并为同一仓库候选，同时保留各自已读取的来源。读取实际根目录文件及默认分支，许可、接口/使用 README、依赖与部署各最多一份，另有元数据收据；每次最多六个只读公共 API 请求，不使用 token，不克隆、安装或执行候选代码。
- 其他网站仅跟进已读内容中的同站文档链接，沿用 Exa URL/超时/费用控制。新增文档使对应资源重新匹配，旧当前评价失效。资源页展示已读取的文档链接和版本；文档收据与具体能力依据分开。
- 原文引用仅在本次传给模型、属于对应资源的来源中定位。编号错误仅允许唯一原文定位；空白差异校正后保存确切原句。不存在、歧义、跨资源或未提供的引用仍无法升级。许可元数据不能独自成为完整商用支持。方案输入包含实际已读文档目录，避免将“证据不足”写成“文件未读”。
- 手机资源列表的自动网格列曾被长地址撑宽，已用显式单列与任意位置换行修复。资源长说明可展开；目标假设默认按需展开，草稿操作随滚动保持可见。表单读屏标签使用条件文本。

主要改动：`goalsift/goal_review.py`、`source_research.py`、controller/app/models/repository/search_adapter/llm_adapter/exporter，以及 `frontend/src/GoalReview.tsx`、Workspace/api。03/04/05 与 README 同步契约。

## 验证与证据

| 验收 | 结果与证据 |
|---|---|
| 回归与新增隔离测试 | 102 项通过，其中新增 14 项。`pytest.txt`、`test-collection.txt`；每项强制独立数据根，新测试以 `PRAGMA database_list` 断言实际 DB 路径 |
| 迁移/历史/修订/并发 | 旧 schema 自动增量迁移、历史 JSON 字符串保留；确认/编辑/移出/假设复核及后续 Refine；非法输入、异任务引用、旧 revision、并发、关联条件重映射及依赖移除拒绝；C++/C# 与大小写不同的接口确认不误合并 |
| 来源/状态/控制 | 实际存在的有界文件选择、错误文件、URL 注入过滤；新增文档重新匹配；许可标识不成为完整商用支持；唯一引句/空白/歧义/未提供来源；深度读取暂停恢复与取消不提交晚到结果；既有预算、SSRF、冲突、错误及恢复测试仍通过 |
| 前端 | lint/build 通过，`lint.txt`、`build.txt`。JS 约 512 KB、gzip 157 KB，Vite 500 KB 提示仍为建议；没有构建错误 |
| 浏览器离线交互 | 明确假模型/假搜索，真实 API/Controller/SQLite/UI。提交目标理解、确认条件、编辑 QUALITY/REQUIRED/验收方式、移出条件、确认与移除假设，形成 r2；历史只读且旧内容仍在。`offline-r1/r2.json` 与 draft/history 截图。没有真实付费调用 |
| 原预览升级 | 8000 服务沿用 `/private/tmp/goalsift-completion-live`；SQLite backup 已保存。最终代码重启后健康检查通过，r3 历史逐项比较完全一致（preview-history-before/after.json）；在原预览编辑草稿再切换同 r3 历史，草稿与保存操作均不显示（preview-history-draft-isolation.png），返回当前后无遗留测试草稿。原 `.goalsift_data` 不参与验收 |
| 真实来源探针 | GitHub 公共 API 六次 GET，取得许可、README、manifest、Dockerfile 与元数据，保留 SHA；`github-live-probe.json` |
| 真实浏览器链路 | 浏览器创建目标→真实 DeepSeek/Exa→文档补查→r1；浏览器复核并提交→独立 DB 的 r2。`live-r1/r2.json`、事件、历史、JSON/Markdown 导出与 `audit.json` |
| 响应式 | 桌面 1280×720：main client/scroll 都为 1016；手机 390×844：main client/scroll 都为 382、scrollLeft=0，包含资源长说明展开后。文档与确认状态截图；内部滚动边界也检查，不能仅看 document.scrollWidth |

真实目录 `/private/tmp/goalsift-review-live-a2993wyu`，任务 `job_7f396bd6fd70462b`。r1/r2 均 COMPLETED。最终 7 项明确确认条件保留，8 个无仓库别名重复的资源，56 项评价（10 SUPPORTED、13 PARTIAL、32 UNKNOWN、1 CONFLICTED）。方案覆盖 5/7，2 项未覆盖；没有 VERIFIED。两个不同仓库各 5 份文档记录。旧 r1 快照与导出一致，所有对象引用、原句定位、冲突和方案追溯验证通过。此次是新增能力的独立专项 Live 验收，既有 M6 跨域结果在原报告中保留。

## 费用

r1 保守费用 $0.065635，r2 $0.0567802，本次合计 $0.1224152；此前授权费用 $0.3987574，累计 $0.5211726，原 $1 授权剩余 $0.4788274。两修订各 $0.15 上限，没有未知费用或未结预留。GitHub 无 token 的公共读取没有付费服务调用。模型采用峰值 token 单价估计，Exa 使用返回的 costDollars；详见 `cost-ledger.json`。

## 范围和后续

- 来源解释仍需人复核，文档支持不等于目标环境测试。实际状态呈现、响应式行为、部分集成和完整依赖许可仍有未知项。
- GitHub 补读限于默认分支与根目录，保留文件 SHA；嵌套文档、特定版本、全部接口和依赖传递许可尚未穷尽。检索上限 8 个候选、3 轮，补查最多两个候选。
- 用户移出决定按原文与明确上下文保持；语义不同的模型改写仍需复核。全修订失效保守，尚未按细粒度依赖只重跑受影响条件。
- 下一项可在这些记录基础上做针对未覆盖条件的增量补查、修订差异比较。候选方案执行保持 Phase A 的人工选择边界。

## 复现

在仓库根运行 `make check`。离线浏览器环境：`PYTHONPATH=. .venv/bin/python acceptance/2026-10-10/review-depth/offline_fixture.py`，进程打印随机本地端口并使用新的临时目录。`live_server.py` 保存的是本次两修订专项环境；重新真实运行会计费，应从最新账本和明确授权计算预算。

公共文件读取使用 GitHub 官方 [Get repository content](https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#get-repository-content) 的目录、默认分支和 Base64 内容字段；只读端点支持公共资源无鉴权。验收过程没有调用写入端点。
