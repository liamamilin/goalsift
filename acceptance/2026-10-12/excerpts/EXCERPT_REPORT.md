# 来源摘录与引用边界专项验收

日期：2026-10-12。恢复基线：`b77ec1038613fad972bc77b916b20fe88b1c2846`。专项结论：**PASS**。

下一步按上轮建议检查真实失败/未知语料，不扩展 Phase A 至方案执行。修改前工作区干净、与 GitHub main 一致。沿用累计 $1 的真实服务授权；此前累计 $0.5388616，本次单次研究上限 $0.08。

## 问题与实际修复

旧规则对长来源只保留开头及首个安装/API 段落。上轮实际保存的 builderz-labs/mission-control README 中，活动/状态界面的截图说明存在于原文，却不在旧摘录中。`corpus-audit.json` 记录真实来源、SHA、读取时间与前后范围。另一个问题是引文验证搜索全部已保存正文，即使模型没有收到相关文字，也可能接受其引文；受控负向测试复现这条边界。

现在按当前条件或定向补查问题进行确定性的关键词选择，保留开头及不同位置的相关原文片段。仍限制每来源 2400 字符、每候选六个来源，GitHub 最多六次读取，不增加检索轮次或执行候选代码。选择只帮助提供相关上下文，不推断能力存在。没有相关词时保留旧摘录规则，短文本保持完整。

支持、部分满足、不满足和冲突引文必须完整位于同一实际提供的原文区间；未提供的正文、跨省略边界的文字和合成标记不能成为该次主张依据。仅在实际提供的资源来源中唯一定位才允许纠正引文 ID。主张证据继承对应来源的读取时间与版本，避免把重用旧资料显示为刚读取。

匹配返回与原输入一起保存至检查点。恢复使用已保存上下文；旧检查点没有输入记录时，以原摘录规则保守校验。资料更新会清理旧匹配上下文并使旧判断待复核。匹配记录不被误算为补充文档已经读取。

成功匹配的 `source_reviews[resource_id].match_context` 保存 Evidence ID、URL、保存/提供字符数、部分摘录标记与原文范围。范围以 Python 字符串的 Unicode 码点计数，是半开区间。JSON 保留范围，Markdown 展示提供量。GitHub 超出 12000 字符保存上限时，已有资源页读取说明与导出明确提示后文未用于匹配。旧快照不补写新字段。

复用现有 Python 正则、Controller、SQLite、Pydantic、来源适配器、校验器和导出，不增加依赖。改动为 `goalsift/source_research.py`、`controller.py`、`search_adapter.py`、`llm_adapter.py`、`exporter.py`，以及前端 API 类型、04/05 和 README。

## 自动化与真实语料：PASS

`.venv/bin/python -m pytest`：**125 passed in 2.04s**，见 `pytest.txt`。新增 11 项覆盖真实 README 摘录盲区、短/无关文本兼容、中英条件词匹配、同一片段边界/重复引句/多来源歧义、未提供引句不得支持/反驳/构成冲突、相关后文进入匹配且留痕导出、新旧检查点恢复及读取上限说明。SQLite 实际路径通过临时目录断言，提供商为 fixture，不发收费请求。

最终清理失效来源的匹配元数据后，`.venv/bin/python -m pytest tests/test_excerpt_context.py tests/test_targeted_diff.py` 再检查相关 22 项，见 `scoped-regression.txt`。前端 lint 和构建通过，见 `lint.txt`、`build.txt`；约 554 kB 的既有分包提示仍记录。本轮 API 类型同步，不新增页面布局或交互；没有新的浏览器验收，不将 Controller 成功冒称浏览器通过。

## 独立真实服务：PASS

`PYTHONPATH=. .venv/bin/python acceptance/2026-10-12/excerpts/live_check.py` 使用 SQLite backup 复制上轮隔离数据库，实际写入 `/private/tmp/goalsift-excerpts-live-tm01q70a/goalsift.sqlite`。启动及 SQLite 实际路径有断言，来源数据库只读。

对修订 3 的 Agent 状态展示条件做一次限定候选补查。真实 DeepSeek/Exa/GitHub，修订 4 **COMPLETED**，27.44 秒、3 次模型和 2 次工具动作。7 个已确认条件保持，8 个候选，49 项评价沿用。实际模型上下文为六个来源，其中四个是部分摘录；新增六条主张逐条审计，全部位于实际提供的范围，读取时间/版本与来源一致。旧修订 3 与原数据库快照逐字相同。

本案例覆盖从 5/7→6/7。Agent 状态展示变为 SUPPORTED，引用 README 中“每 Agent 状态与心跳事件”的活动流截图说明；完整 running/error 状态枚举仍有缺口。响应式布局仍 UNKNOWN，未部署、运行或人工验收候选；没有 VERIFIED。有限案例与合法引文不能证明全部语义理解正确，也不证明总体研究质量的统计提升。

首次验收脚本在保存 JSON 时把 `to_json` 的字典误当字符串，研究本身已 COMPLETED。修正脚本后使用 `GOALSIFT_AUDIT_EXISTING_DATA=/private/tmp/goalsift-excerpts-live-tm01q70a` 做只读复审；没有第二次收费研究。初次错误见 `live-run.txt`，成功复审见 `live-audit-run.txt`、`live-audit.json`。结果、事件、对比和导出分别保存于 `live-result.json`、`live-events.json`、`live-diff.json`、`live-export.json/.md`。

## 费用、预览与交付

新增记录 **$0.0141889**，无未知费用或未结预留，累计 **$0.5530505**，低于 $1，见 `fee-ledger.json`。依据模型保守 token 单价和 Exa 记录，不是提供商账单。

发现 8000 预览服务已停止，保留旧数据并使用最终代码重启。原任务仍 COMPLETED、修订 3；原库 11 张表逐项与重启前备份一致，见 `preview-audit.json`。未对原任务发起新研究。

当前文件及本轮制品按真实配置值精确匹配检查凭据，见 `secret-scan.json`；文件校验见 `manifest.sha256`。最终代码重现六份实际 Live 输入区间，见 `final-selector-audit.json`。Git 源码差异空白检查通过，原始日志与导出保留实际空格。原恢复归档留在本地 Git 元数据，不提交或上传。

后续建议继续增加不同领域和长资料的固定回归语料，评估片段选择的遗漏；需要完整接口/视觉/性能结论时，仍须采用前的限定环境验收。当前选择是关键词启发式，保存上限之后的正文仍不可见，不能宣称已阅读全文。
