# GoalSift — From Goals to Viable Paths

本地优先的 AI 方案研究应用。输入目标后，应用理解目标、推导并挑战条件、检索真实资源、读取来源、逐项匹配并给出可追溯的候选路径。Phase A 的交付是供人选择的研究方案。

支持研究暂停/恢复/取消、关键问题澄清、完成后的增量修订、历史快照、Markdown/JSON 导出，以及持续保存的事件、费用与用量。复用已有前端设计和 React/Radix/Driver.js、FastAPI、Pydantic AI、SQLite、DeepSeek、Exa。

本次验收见 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md)。旧提交的安全测试曾包含真实凭据，本轮已清理当前文件；建议更换 DeepSeek/Exa key，公开旧 Git 历史前先处理这一遗留。原 M0–M5 报告保留为历史记录，当前实现以本次报告和源代码为准。

## 安装与启动

需要 Python 3.10+、Node.js 22.12+、npm；macOS/Linux 单进程服务。Python 的完整依赖锁定在 `requirements.lock`，前端锁定在 `frontend/package-lock.json`。

```sh
make install
# 仅在尚无 .env 时复制；已有配置请保留
cp -n .env.example .env
# 在 .env 填入自己的 DeepSeek 和 Exa key，并设置费用上限
make check
make run
```

打开 http://127.0.0.1:8000。后端直接提供构建后的前端，只需要一个服务。API 健康检查为 `/api/health`。前端开发可另开终端运行 `make dev`，浏览 http://127.0.0.1:5173；Vite 将 `/api` 转发至 8000。

现有开发环境可直接 `make run`。`PYTHON=/path/to/python make run` 可指定解释器，`PORT=8001 make run` 可更换端口。服务只绑定本地地址；同一数据目录只允许一个服务和一个 worker。

## 使用

1. 输入希望达到的结果及必须满足的约束，点击 **Create & start research**。
2. 如出现关键澄清问题，回答后在同一修订继续。Events 展示实际研究动作。
3. **Pause** 等待当前在途请求提交后暂停；**Resume** 从检查点继续；**Cancel** 立即撤销执行所有权，在途请求可能已收费。
4. 查看 Proposal 的组合工作、新开发内容、风险和未覆盖条件。Conditions、Resources、Match 可逐层打开证据原文和来源。
5. 完成后通过 **Refine** 加入新约束；创建新修订，复用已读取的资料并重新判断适用性。修订选择器可查看只读历史结果。
6. Markdown/JSON 导出当前显示的修订。刷新或重新启动后，任务与成果仍保留；异常中断的研究恢复为 Paused。

## 费用与配置

实际支持的适配器为 DeepSeek + Exa。密钥只在服务端读取，Settings 仅显示是否配置及掩码。修改 `.env` 后重启生效；外部环境变量优先于 `.env`。

预算按**每个修订**累计，Resume 不清零，Refine 有新预算。动作数、工具数、研究运行时长、搜索轮数、单请求超时和 token 限额共同约束研究。费用达到上限时停止后续请求，保留 Partial 成果；调整服务端预算后可继续。

模型费用使用已核对的保守峰值 token 单价，Exa 使用响应中的 `costDollars`。这不是提供商账单。发请求前预留最坏情况费用；未知账单或进程中断的请求保留预留额，避免误报零费用或重试越过上限。未知模型单价且设有费用上限时拒绝收费请求。单次请求没有提供商端硬预算，因此应用预算依赖单价与请求上界；更换模型时请更新单价。

默认限制为 30 动作、20 工具、300 秒、3 次检索；复杂任务可能合理地停止为 Partial。验收使用明确记录的较长运行预算，并保留失败与恢复证据。

## 数据、边界与备份

默认数据库在 `.goalsift_data/goalsift.sqlite`，包含本地任务、原文摘录和历史结果；不提交 Git。`GOALSIFT_DATA_DIR` 可指定独立目录。已有数据库只进行新增表的兼容迁移，不删除研究。

```sh
make backup
# 自动测试与应用数据隔离，不使用真实收费接口
make test
```

备份会通过 SQLite backup API 包含已提交的 WAL 数据。恢复时先停止服务，再保留当前数据库副本，把备份复制到数据目录的 `goalsift.sqlite`。`make clean` 仅清理构建和测试缓存，保留应用数据。

外部模型会收到研究目标及来源内容；Exa 会收到搜索语句和公开来源 URL。没有目标项目写入、检索脚本执行或方案自动部署。URL 只允许 HTTP(S)、标准端口及公共地址；拒绝凭据 URL、私有地址、客户端重定向和超量响应。在 VPN Fake-IP 环境下，仅 Exa 的委托读取会通过固定 Google DoH 端点再次核验公共 DNS，仍拒绝非公共解析。网络不可用时拒绝来源并显示限制。

## 证据与限制

`SUPPORTED` 表示已读取来源支持；`VERIFIED` 必须有目标环境测试或人工验收记录。本应用不会把文档声明或主观视觉判断变成 VERIFIED。没有许可依据是 UNKNOWN；CONFLICTED 要求可定位的相反证据。方案可以有未覆盖条件，研究完成不表示目标已经实现。

检索范围最多 8 个候选和 3 轮；模型对原文含义的理解仍可能出错，来源也可能过时。视觉质量、完整依赖许可、真实接口兼容性、性能和 3D 资产整合仍需采用前验收。有限样本对比不构成方案优越性的统计证明。当前没有用户账号、跨设备同步或生产方案执行；单机单用户使用。

## 代码与规格

`goalsift/` 为后端、预算、工具适配器、SQLite 和导出；`frontend/` 为用户界面；`tests/` 为隔离测试；`acceptance/2026-10-10/` 保存本次脱敏证据。`AGENTS.md` 及 01–07 文档定义产品与验收合同。
