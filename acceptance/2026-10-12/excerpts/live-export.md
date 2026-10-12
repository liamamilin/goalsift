# GoalSift 研究报告

- 任务：job_7f396bd6fd70462b
- 修订：4
- 状态：COMPLETED
- 导出时间：2026-10-12T05:34:37.597241+00:00
- 范围：公开来源的方案研究；方案尚未执行，来源支持不等于目标环境验收。

## 目标

为单用户本地演示选择成熟的开源 Agent 状态控制台：显示运行状态和任务列表，提供清晰的响应式页面，可商用。优先调查 builderz-labs/mission-control；部署方法和接口对接应有来源说明。无需登录权限、多用户协作或高帧率动画，未明确的前提请作为待确认假设。
用户补充：目标理解：选定可商用、能展示 Agent 状态与任务列表的开源响应式控制台，有部署和接口说明，供单用户本地演示。
（推断）本地演示环境为单机运行，无需对外网络暴露

**用户原话：** 为单用户本地演示选择成熟的开源 Agent 状态控制台：显示运行状态和任务列表，提供清晰的响应式页面，可商用。优先调查 builderz-labs/mission-control；部署方法和接口对接应有来源说明。无需登录权限、多用户协作或高帧率动画，未明确的前提请作为待确认假设。

**用户要求与已确认前提**
- [USER_STATED] 为单用户本地演示选择成熟的开源 Agent 状态控制台：显示运行状态和任务列表，提供清晰的响应式页面，可商用。优先调查 builderz-labs/mission-control；部署方法和接口对接应有来源说明。无需登录权限、多用户协作或高帧率动画，未明确的前提请作为待确认假设。
- [USER_CONFIRMED] 目标理解：选定可商用、能展示 Agent 状态与任务列表的开源响应式控制台，有部署和接口说明，供单用户本地演示。
- [USER_CONFIRMED] （推断）本地演示环境为单机运行，无需对外网络暴露

**未确认假设**
- [SYSTEM_ASSUMED] （推断）'成熟'指项目有持续维护、可用文档与稳定发布版本
- 已移出目标（r2）：优先调查 builderz-labs/mission-control，并在结论中给出其是否满足上述要求的评估结果。
- 已移出目标（r2）：待确认假设：目标运行环境（操作系统、Node/Python 等运行时版本、是否需要 Docker）、浏览器版本下限、以及“成熟”的量化标准（如 star 数、最近提交时间、发布版本数）。

## 候选路径

### 单用户本地演示：Agent 状态控制台候选方案（首选 builderz-labs/mission-control）

首选 builderz-labs/mission-control：MIT 许可原文已核验，无禁止商用条款；README 显示 Agent 状态/心跳与任务流水线展示；有本地启动章节与 Dockerfile；官方 agent-setup.md 提供注册/查询接口示例，package.json 引用 openapi.json 与契约校验脚本。响应式布局在已读来源中无证据，属未知，需查前端源码或实测窄屏。接口示例使用 [REDACTED]，免登录演示是否可行未说明。备选 open-alpine-ai/mission-control：MIT 原文核验通过、README 有完整 clone/pnpm 步骤，但 setup 强制用户名密码，且为 Alpha 软件。其余候选证据仅到许可证标识层级。

**建议理由：** 在已读来源中，仅 builderz-labs/mission-control 与 open-alpine-ai/mission-control 同时具备可核验的 MIT 许可原文、官方部署步骤与接口说明；前者在状态展示与任务列表上有 README 级证据且无强制登录描述，故列为首选。响应式与免鉴权仍为未知，需人工复核，不代表条件已满足。

**集成工作**
- 按官方 README「Start locally」章节与 Dockerfile 在本机启动控制台（Node 22+/pnpm 前提来自 README）
- 依据官方 agent-setup.md 的注册/查询接口示例，将本地 Agent 数据源接入控制台
- 核对 openapi.json 与 API 契约校验脚本，确认任务（task）相关端点与字段
- 确认本地演示下 [REDACTED] 是否可省略或使用默认值

**补充工作**
- 若需窄屏可用，需先核实前端是否已有响应式断点；无证据不等于必须新开发
- 若任务列表字段/筛选不满足演示需求，可能需前端调整（待确认）
- 若本地 Agent 数据源接口与控制台契约不一致，需编写适配层（待确认）

**风险**
- 响应式布局在已读来源中无证据，桌面与窄屏可用性未经测试
- 接口示例要求 Bearer 鉴权，与免登录演示偏好可能冲突
- 第三方依赖（如 @scalar/api-reference-react、xterm）许可清单未核验，整体商用合规待查
- README 源码安装命令块在已读片段中被省略，完整步骤需再取原文
- 任务相关接口示例未出现在已读片段中，对接细节未知
- 部分所选资源没有补充文档读取；许可、接口、部署和依赖缺口需人工核查。

**假设**
- （推断）'成熟'指项目有持续维护、可用文档与稳定发布版本

实施费用：{"estimate": "UNKNOWN", "basis": "没有经核实的方案实施价格"}

## 成立条件

## 本轮定向补查

- 基于修订：3；本轮费用上限：$0.08
- 调查条件：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。
- 调查问题：核查界面运行状态指示的具体文档依据；只依据实际提供的片段，不推断整份文档没有某项能力。
- 沿用评价：49 项；新增资料可能影响同一候选的其他条件。

- **[REQUIRED / COMPLIANCE]** 所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。 (`cond_e8fd80e9ac514d77`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_582de5e064174911
  - 验收方式：在候选项目仓库根目录读取 LICENSE / COPYING 文件及 README 中的许可声明，确认许可证标识（如 MIT/Apache-2.0/BSD 等）并核对是否含非商业限制条款；记录许可证名称与文件链接作为来源说明。
- **[REQUIRED / FUNCTIONAL]** 控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。 (`cond_66f43a5a54b44e78`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_f5b32e17ac804ccf
  - 验收方式：在本地启动后打开控制台页面，确认存在状态展示区域并能随 Agent 状态变化更新；同时对照项目文档/源码中状态字段定义作为佐证。
- **[REQUIRED / FUNCTIONAL]** 控制台界面能够展示任务列表。 (`cond_b1b122672eaa46d1`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_7545e2653ed54c45
  - 验收方式：在本地启动后打开控制台页面，确认存在任务列表视图并渲染出任务条目；对照项目文档/源码中的任务数据模型作为佐证。
- **[REQUIRED / QUALITY]** 页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。 (`cond_8794f11100e74023`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_43ea0cd950fb4a46
  - 验收方式：在桌面 1280×720 和手机 390×844 视口人工检查：文字与任务信息可读，主要操作可见，无横向溢出。
- **[REQUIRED / FUNCTIONAL]** 提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。 (`cond_fb6e789c021a4a9d`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_a0e6c602aa67484f
  - 验收方式：引用官方仓库 README 或文档中的部署章节，逐条记录命令与前置依赖；在本地按该说明执行并确认服务可启动、页面可访问，记录实际执行的命令与结果。
- **[REQUIRED / FUNCTIONAL]** 提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。 (`cond_9c8730155a4641ec`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_5dd0c304855b4eae
  - 验收方式：在官方文档或源码中定位数据接口定义（如 API 路由、数据模型、WebSocket/轮询机制），记录接口路径与字段来源链接；通过实际调用或页面数据流验证接口可用。
- **[OPTIONAL / FUNCTIONAL]** 方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。 (`cond_be699b5b72f74d0e`)
  - 确认来源：USER_CONFIRMED
  - 依据：用户确认于修订 2；原条件 cond_bed9b35049f0448d
  - 验收方式：在评估结论中说明候选是否包含登录/多用户/动画特性，并确认这些特性不影响单用户本地演示的可用性（例如可跳过登录或使用默认本地配置）。

## 资源与许可

- **builderz-labs/mission-control** — 许可：MIT
  - 来源：https://github.com/builderz-labs/mission-control
  - # builderz-labs/mission-control

Self-hosted control plane for AI agents: dispatch tasks, review runs, track spend, and operate OpenClaw, Claude Code, Codex, and other runtimes.

- Stars: 6332
- Forks: 107
- Watchers: 6332
- Open issues: 50
- License: MIT License
- Homepage: https://mc.builderz.dev
- Default branch: main
- Created: 2026-02-13T04:06:19Z

## Languages

- CSS
- Dockerfile
- JavaScript
- PowerShell
- Python
- Shell
- TypeScript

## Topics

- agent-observability
- agent-operations
- agent-orchestration
- ai-agents
- claude-code
- codex
- developer-tools
- mcp
- nextjs
- open-source
- openclaw
- self-hosted
- sqlite
- ta[REDACTED]
- typescript

## Top Contributors

- 0xNyk (432 contributions)
- bhavikprit (14 contributions)
- HonzysClawdbot (11 contributions)
- dependabot[bot] (
  - 补充文档（仓库与许可声明）：https://api.github.com/repos/builderz-labs/mission-control；版本 main
  - 补充文档（许可原文）：https://github.com/builderz-labs/mission-control/blob/main/LICENSE；版本 8bd4a619e7e36584314ee875ed7830867848c6ab
  - 补充文档（接口与使用说明）：https://github.com/builderz-labs/mission-control/blob/main/README.md；版本 07a29e050ee02f1104d1c5793eac6ad54b37bcd3
  - 补充文档（运行依赖）：https://github.com/builderz-labs/mission-control/blob/main/package.json；版本 04d6c6075da4431bd74353d89c42520f40f046a9
  - 补充文档（部署配置）：https://github.com/builderz-labs/mission-control/blob/main/Dockerfile；版本 84550db5bc9ad76ae54f8b5154550c8ae0901dc3
  - 匹配资料：https://github.com/builderz-labs/mission-control/blob/main/README.md；已保存 12000 字符，实际提供 2200 字符（选取片段，不能据此判断整份资料不存在某项能力）
  - 匹配资料：https://github.com/builderz-labs/mission-control/blob/main/Dockerfile；已保存 4518 字符，实际提供 1650 字符（选取片段，不能据此判断整份资料不存在某项能力）
  - 匹配资料：https://github.com/builderz-labs/mission-control/blob/main/package.json；已保存 4252 字符，实际提供 1100 字符（选取片段，不能据此判断整份资料不存在某项能力）
  - 匹配资料：https://github.com/builderz-labs/mission-control/blob/main/LICENSE；已保存 1070 字符，实际提供 1070 字符
  - 匹配资料：https://api.github.com/repos/builderz-labs/mission-control；已保存 236 字符，实际提供 236 字符
  - 匹配资料：https://github.com/builderz-labs/mission-control/blob/main/docs/agent-setup.md；已保存 6000 字符，实际提供 2200 字符（选取片段，不能据此判断整份资料不存在某项能力）
  - 读取限制：仓库文档读取失败：HTTPStatusError
- **Mission Control | Open-Source Control Plane for AI Agents** — 许可：UNKNOWN
  - 来源：https://mc.builderz.dev/
  - Mission Control | Open-Source Control Plane for AI Agents

# Run every AI agent from one control plane

See what your agents are doing, dispatch work, catch failures, and track spend without stitching together another internal dashboard.

Run Mission Control locally Star on GitHub 6.3k

Self-host free. No account. No forced product telemetry.

Live agent activity Tasks and pipelines Costs and alerts Open API

Built in public for teams operating AI agents

6.3k GitHub Stars

108 Forks

MIT License

Self-hosted Deployment

SQLite Local data

Use it when

Multiple agents, people, or gateways create enough operational surface that tasks, spend, security, and handoffs are getting hard to follow.

Skip it when

You run one agent on one machine, need a managed SaaS, or require stable production A
- **open-alpine-ai/mission-control** — 许可：MIT
  - 来源：https://github.com/open-alpine-ai/mission-control
  - # Repository: open-alpine-ai/mission-control (fork of [smolboon/mission-control](https://github.com/smolboon/mission-control))

Open Alpine Mission Control: operations cockpit for AI agent teams with task governance, gateway diagnostics, quality gates, and production observability.

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- Primary language: TypeScript
- Languages: TypeScript (97.8%), Shell (0.9%), JavaScript (0.9%), CSS (0.3%), Dockerfile
- License: MIT License (MIT)
- Default branch: main
- Homepage: https://mc.builderz.dev
- Created: 2026-03-08T08:52:34Z
- Last push: 2026-03-10T04:46:26Z
- Contributors: 10 (top: 0xNyk, bhavikprit, rezero-household, mark-liu, othavi0, patricksimpson, perter, ResistanceDown, beeman, 0xfulgore)

---

 

# Mission Control

**Open Alpine Mission
  - 补充文档（仓库与许可声明）：https://api.github.com/repos/open-alpine-ai/mission-control；版本 main
  - 补充文档（许可原文）：https://github.com/open-alpine-ai/mission-control/blob/main/LICENSE；版本 8bd4a619e7e36584314ee875ed7830867848c6ab
  - 补充文档（接口与使用说明）：https://github.com/open-alpine-ai/mission-control/blob/main/README.md；版本 02db6a662229e76d552aa34d549f3e29d7d500e7
  - 补充文档（运行依赖）：https://github.com/open-alpine-ai/mission-control/blob/main/package.json；版本 3623da5a368256f6ee70d8ff445064a618a1c68c
  - 补充文档（部署配置）：https://github.com/open-alpine-ai/mission-control/blob/main/Dockerfile；版本 792ef4a77bb51c4c54a7aa7331d5c07735eb8516
- **What is Mission Control? — Learn** — 许可：UNKNOWN
  - 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/
  - What is Mission Control? — Learn

## Welcome to Mission Control

Mission Control is an open-source Next.js dashboard designed for orchestrating AI coding agents. It gives developers a single pane of glass to plan, dispatch, and monitor work across multiple AI agents simultaneously.

At its core, Mission Control treats software tasks as first-class objects. You create a task by describing what you want done, optionally supplying context like affected files, priority level, or tags. Mission Control then uses AI to break that work into actionable steps and dispatches it to the agent best suited for the job.

## What Problems Does It Solve?

Modern AI coding tools like Claude Code, Codex CLI, and Gemini CLI are powerful in isolation, but managing them manually across many tasks becomes unwield
- **la-rebelion/agents-mission-control-panel** — 许可：MIT
  - 来源：https://github.com/la-rebelion/agents-mission-control-panel
  - # la-rebelion/agents-mission-control-panel

Self-hosted AI agent orchestration platform: dispatch tasks, run multi-agent workflows, monitor spend, and govern operations from one mission control dashboard.

- Stars: 0
- Forks: 1
- Watchers: 0
- Open issues: 0
- License: MIT License
- Homepage: https://rebelion.la
- Default branch: main
- Created: 2026-04-14T15:57:38Z
- Fork: yes

## Languages

- CSS
- Dockerfile
- JavaScript
- PowerShell
- Shell
- TypeScript

## Topics

- agentic-ai
- clawster
- managed-agents
- openclaw

## Top Contributors

- 0xNyk (274 contributions)
- bhavikprit (14 contributions)
- HonzysClawdbot (11 contributions)
- AlessandroMartini (5 contributions)
- Brixyy (5 contributions)
- danielaustralia1 (4 contributions)
- hectorarriolai (3 contributions)
- Shipu (3 contribu
- **absorbo/mission-control** — 许可：MIT
  - 来源：https://github.com/absorbo/mission-control
  - # absorbo/mission-control

Self-hosted AI agent orchestration platform: dispatch tasks, run multi-agent workflows, monitor spend, and govern operations from one mission control dashboard.

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- License: MIT License
- Homepage: https://mc.builderz.dev
- Default branch: main
- Created: 2026-04-17T17:27:30Z
- Fork: yes

## Languages

- CSS
- Dockerfile
- JavaScript
- PowerShell
- Shell
- TypeScript

## Top Contributors

- 0xNyk (274 contributions)
- bhavikprit (14 contributions)
- HonzysClawdbot (11 contributions)
- AlessandroMartini (5 contributions)
- Brixyy (5 contributions)
- danielaustralia1 (4 contributions)
- Shipu (3 contributions)
- absorbo (3 contributions)
- hectorarriolai (3 contributions)
- jrrcdev (2 contributions)

---

## READM
- **jeturing/mission-control** — 许可：MIT
  - 来源：https://github.com/jeturing/mission-control
  - # Repository: jeturing/mission-control

AI Agent Orchestration Dashboard - Monitor Grid, Pixel Office, Real-time visualization

- Stars: 1
- Forks: 0
- Watchers: 0
- Open issues: 7
- Primary language: TypeScript
- Languages: TypeScript (91.1%), JavaScript (3.6%), Shell (2.4%), Python (2.3%), CSS (0.4%), Dockerfile (0.2%)
- License: MIT License (MIT)
- Default branch: main
- Created: 2026-03-06T02:14:40Z
- Last push: 2026-05-28T19:56:57Z
- Contributors: 10 (top: crshdn, niks918, niketas, davetha, muneale, misterdas, JamesTsetsekas, superlowburn, nice-and-precise, nicozefrench)

---

 Autensa 

 
 Formerly known as Mission Control 
 autensa.com 
 

 
 AI Agent Orchestration Dashboard 
 Create tasks. Plan with AI. Dispatch to agents. Watch them work.
 

 
 
 
 
 
 
 
 
 

 
 🎮 Live Demo •
 Qu
- **omarnagy91/cortex** — 许可：MIT
  - 来源：https://github.com/omarnagy91/cortex
  - # omarnagy91/cortex

Open-source dashboard for AI agent orchestration. Manage agent fleets, dispatch tasks, track costs, and coordinate multi-agent workflows. Self-hosted, zero dependencies, SQLite-powered.

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- License: MIT License
- Homepage: https://mc.builderz.dev
- Default branch: main
- Created: 2026-03-26T18:06:24Z
- Fork: yes

## Languages

- CSS
- Dockerfile
- JavaScript
- PowerShell
- Shell
- TypeScript

## Top Contributors

- 0xNyk (259 contributions)
- bhavikprit (14 contributions)
- HonzysClawdbot (11 contributions)
- omarnagy91 (6 contributions)
- Brixyy (5 contributions)
- danielaustralia1 (4 contributions)
- hectorarriolai (3 contributions)
- jrrcdev (2 contributions)
- rezero-household (2 contributions)
- ResistanceDown (1

## 条件匹配与证据

### UNKNOWN：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：Mission Control | Open-Source Control Plane for AI Agents
页面标注 MIT License 与开源，但未引用 MIT 条款原文，商用授权未直接证实。
- 缺口：缺少 MIT 许可证条款原文（如“Permission is hereby granted, free of charge...”）以确认无禁止商用条款
- 缺口：缺少仓库 LICENSE 文件或 package.json license 字段等可追溯元数据
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.842224Z）
  > 6.3k GitHub Stars
  > 
  > 108 Forks
  > 
  > MIT License
  > 
  > Self-hosted Deployment

### PARTIAL：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：Mission Control | Open-Source Control Plane for AI Agents
页面称可查看 Agent 活动与状态，但未给出具体状态指示（运行中/空闲/异常）的界面证据。
- 缺口：缺少界面截图或组件源码证明存在运行中/空闲/异常等状态指示
- 缺口：未说明状态字段与取值定义
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.842607Z）
  > See what your agents are doing, dispatch work, catch failures, and track spend without stitching together another internal dashboard.

### SUPPORTED：控制台界面能够展示任务列表。

资源：Mission Control | Open-Source Control Plane for AI Agents
页面明确列出任务看板功能，含优先级、评论、项目等，属任务列表展示。
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.842898Z）
  > #### Task board
  > 
  > Six-stage flow with priorities, comments, projects, and sub-agent spawning.

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：Mission Control | Open-Source Control Plane for AI Agents
现有来源未提及响应式布局、断点或移动端适配，无法判断。
- 缺口：缺少响应式设计说明或 CSS 断点/媒体查询证据
- 缺口：缺少移动端视口截图或文档

### PARTIAL：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：Mission Control | Open-Source Control Plane for AI Agents
官网给出本地安装与 Docker 指引，但引文被截断，命令与步骤不完整。
- 缺口：引文截断，缺少完整 clone/安装命令与 setup guide 链接
- 缺口：未提供官方 README 或发布说明的可追溯 URL
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.843332Z）
  > The installer handles Node.js, pnpm, dependencies, and secure credentials. Use local mode or swap in Docker from the setup guide.

### PARTIAL：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：Mission Control | Open-Source Control Plane for AI Agents
页面提及 Open API 与 OpenAPI routes，但无端点、Schema 或文档链接。
- 缺口：缺少 OpenAPI 规范文件或端点清单
- 缺口：缺少官方 API 文档链接或源码接口实现引用
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.843576Z）
  > Live agent activity Tasks and pipelines Costs and alerts Open API

### SUPPORTED：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：Mission Control | Open-Source Control Plane for AI Agents
页面称本地自托管、无需账号，符合单用户本地演示且不强制鉴权。
- 来源：https://mc.builderz.dev/（exact source quote: evidence_08494ae16a7749cd；读取于 2026-10-10T12:12:09.843788Z）
  > Self-host free. No account. No forced product telemetry.

### UNKNOWN：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：What is Mission Control? — Learn
来源称其为开源，但未给出许可证名称或条款，无法确认可商用。
- 缺口：未提供许可证标识（如 MIT/Apache-2.0）
- 缺口：无许可证条款原文，无法判断是否含禁止商用条款
- 缺口：来源为第三方介绍页，非项目仓库 LICENSE 文件
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.844395Z）
  > Mission Control is an open-source Next.js dashboard designed for orchestrating AI coding agents.

### PARTIAL：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：What is Mission Control? — Learn
有实时监控与状态更新的描述，但未明确列出运行中/空闲/异常等状态指示。
- 缺口：未说明具体状态枚举（运行中/空闲/异常）
- 缺口：未提供界面截图或组件源码佐证
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.844632Z）
  > Monitor — watch the activity dashboard for live status updates

### SUPPORTED：控制台界面能够展示任务列表。

资源：What is Mission Control? — Learn
来源明确称任务为一等对象，并可从同一仪表盘跟踪多个任务。
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.844974Z）
  > You can have dozens of tasks across multiple agents running in parallel, all tracked from the same dashboard.

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：What is Mission Control? — Learn
来源未提及响应式布局、断点或移动端适配。
- 缺口：无响应式/移动端适配的任何说明
- 缺口：无 CSS 框架或断点信息

### PARTIAL：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：What is Mission Control? — Learn
仅给出默认本地端口 4000，缺少安装/启动步骤，且来源非官方仓库 README。
- 缺口：无依赖安装、构建、启动命令
- 缺口：无运行时/Node 版本要求
- 缺口：来源为第三方介绍页而非官方 README/发布说明
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.845337Z）
  > It runs locally on port 4000 by default, keeping your code and task history on your own machine.

### PARTIAL：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：What is Mission Control? — Learn
提到用 SSE 推送实时状态，但无接口定义、端点或字段说明。
- 缺口：无 SSE 端点路径、事件类型或数据字段定义
- 缺口：无 API 文档或源码接口实现引用
- 缺口：SQLite 存储结构未说明
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.845619Z）
  > Real-time monitoring — watch agents work through Server-Sent Events (SSE) without polling

### PARTIAL：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：What is Mission Control? — Learn
本地单机运行、数据留在本机，符合单用户演示；但未说明是否需登录鉴权。
- 缺口：未说明是否存在登录/鉴权流程
- 缺口：未说明是否含多用户协作功能
- 来源：https://www.autensa.com/learn/getting-started/what-is-mission-control/（exact source quote: evidence_df6ab75d92544639；读取于 2026-10-10T12:12:09.845694Z）
  > It runs locally on port 4000 by default, keeping your code and task history on your own machine.

### SUPPORTED：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：open-alpine-ai/mission-control
MIT 许可原文授予无限制使用、复制、修改、分发、再许可与销售权，无禁止商用条款。
- 缺口：需保留版权与许可声明（MIT 条件）
- 缺口：仓库为 Alpha 软件，商用需自担风险
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/LICENSE（exact source quote: evidence_168bb912887b46f2；读取于 2026-10-10T12:12:34.580156Z）
  > Permission is hereby granted, free of charge, to any person obtaining a copy
  > of this software and associated documentation files (the "Software"), to deal
  > in the Software without restriction, including without limitation the rights
  > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  > copies of the Software

### PARTIAL：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：open-alpine-ai/mission-control
README 列出 Agent 生命周期管理与实时监控，但未给出运行中/空闲/异常等具体状态指示的界面证据。
- 缺口：缺少状态指示 UI 截图或组件源码证据
- 缺口：未说明状态枚举（运行中/空闲/异常）
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.580411Z）
  > Agent management with full lifecycle (register, heartbeat, wake, retire)

### SUPPORTED：控制台界面能够展示任务列表。

资源：open-alpine-ai/mission-control
README 明确列出看板任务板，含拖拽、优先级、指派与评论，属任务列表展示。
- 缺口：未提供任务列表页面的截图或路由证据
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.580673Z）
  > Kanban task board with drag-and-drop, priorities, assignments, and comments

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：open-alpine-ai/mission-control
证据仅显示使用 Tailwind CSS，未提供任何响应式布局或移动视口适配的说明。
- 缺口：无响应式/断点相关文档或截图
- 缺口：需实测窄屏视口

### SUPPORTED：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：open-alpine-ai/mission-control
官方 README 给出 git clone、pnpm install、pnpm setup、pnpm dev 的完整本地启动步骤，来源可追溯。
- 缺口：需 pnpm 与 Node >=20
- 缺口：setup 强制要求用户名/密码，与单用户免登录偏好冲突
- 缺口：Dockerfile 健康检查指向 /login
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.581339Z）
  > git clone https://github.com/open-alpine-ai/mission-control.git
  > cd mission-control
  > pnpm install
  > cp .env.example .env    # edit with your values
  > pnpm setup              # interactive setup (username/password/openclaw host/port)
  > pnpm dev                # http://localhost:3000

### PARTIAL：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：open-alpine-ai/mission-control
证据显示存在 WebSocket+SSE 实时监控与 API 参考依赖，但未提供具体接口定义或对接文档原文。
- 缺口：未提供 API 端点/字段定义原文
- 缺口：未说明如何接入本地 Agent 数据源
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.581584Z）
  > Real-time monitoring via WebSocket + SSE with smart polling

### CONFLICTED：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：open-alpine-ai/mission-control
本地单机运行可行，但项目内置登录与 RBAC 多角色权限，与免登录单用户偏好相冲突。
- 缺口：需确认能否禁用鉴权以适配单用户演示
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.581885Z）
  > pnpm dev                # http://localhost:3000
- 来源：https://github.com/open-alpine-ai/mission-control/blob/main/README.md（exact source quote: evidence_aaaa9905f6884290；读取于 2026-10-10T12:12:34.581896Z）
  > Role-based access control (viewer, operator, admin)

### PARTIAL：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：la-rebelion/agents-mission-control-panel
仓库标注 MIT，但仅有标识符，无实际许可条款文本可核验商用范围。
- 缺口：缺少 MIT 许可证正文（如授权、专利、免责条款）以确认无禁止商用条款
- 缺口：未确认许可证覆盖范围（代码/文档/资源）
- 来源：https://github.com/la-rebelion/agents-mission-control-panel（exact source quote: evidence_cf8d7c27b9be4574；读取于 2026-10-10T12:13:15.603965Z）
  > License: MIT

### UNKNOWN：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：la-rebelion/agents-mission-control-panel
现有证据仅含许可证声明，无任何界面或状态展示相关材料。
- 缺口：缺少 README/截图/源码中状态指示实现的证据

### UNKNOWN：控制台界面能够展示任务列表。

资源：la-rebelion/agents-mission-control-panel
现有证据仅含许可证声明，无任务列表相关界面或代码证据。
- 缺口：缺少 README/截图/源码中任务列表实现的证据

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：la-rebelion/agents-mission-control-panel
无响应式布局或样式相关证据可供判断。
- 缺口：缺少 CSS/框架（如 Tailwind、媒体查询）或界面截图证据

### UNKNOWN：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：la-rebelion/agents-mission-control-panel
未提供 README 或部署文档内容，无法评估部署可复现性。
- 缺口：缺少官方 README/文档中的安装与启动步骤

### UNKNOWN：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：la-rebelion/agents-mission-control-panel
无 API 定义、文档或源码接口实现证据。
- 缺口：缺少 API 端点/数据模型或源码接口实现证据

### UNKNOWN：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：la-rebelion/agents-mission-control-panel
无功能范围证据，无法判断是否引入鉴权或多用户协作。
- 缺口：缺少功能清单/README 说明以确认无鉴权与多用户依赖

### PARTIAL：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：absorbo/mission-control
仓库标注 MIT，但仅有标识符，未提供实际许可条款文本，无法核实商用范围。
- 缺口：缺少 LICENSE 全文条款引用，无法确认无禁止商用条款
- 缺口：未确认许可证覆盖范围（代码/文档/资源）
- 来源：https://github.com/absorbo/mission-control（exact source quote: evidence_84b25e59c8714e04；读取于 2026-10-10T12:13:15.604297Z）
  > License: MIT

### UNKNOWN：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：absorbo/mission-control
现有来源仅含许可证标识，无任何界面或状态展示相关证据。
- 缺口：缺少界面截图、组件或状态字段说明

### UNKNOWN：控制台界面能够展示任务列表。

资源：absorbo/mission-control
现有来源未提供任务列表相关界面或数据说明。
- 缺口：缺少任务列表 UI 或数据模型证据

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：absorbo/mission-control
无响应式布局或视口适配相关证据。
- 缺口：缺少 CSS 框架/断点或响应式说明

### UNKNOWN：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：absorbo/mission-control
来源中无 README 或部署步骤内容。
- 缺口：缺少安装/启动命令与依赖说明

### UNKNOWN：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：absorbo/mission-control
无 API 定义、文档或源码接口实现证据。
- 缺口：缺少接口端点/数据格式说明

### UNKNOWN：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：absorbo/mission-control
无鉴权、协作或动画相关证据，无法判断是否引入额外能力要求。
- 缺口：缺少功能范围说明

### UNKNOWN：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：jeturing/mission-control
仅有 MIT 标识，未提供许可证条款原文，无法核实商用范围与前提。
- 缺口：缺少 LICENSE 文件条款原文（如授权范围、专利、商标、再分发条件）
- 缺口：缺少仓库开源可见性/源码可获取性的直接证据
- 缺口：缺少依赖项许可证对整体商用兼容性的说明
- 来源：https://github.com/jeturing/mission-control（license statement；读取于 2026-10-10T12:13:35.277571Z）
  > License: MIT

### UNKNOWN：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：jeturing/mission-control
现有证据仅为许可证声明，无界面或状态指示相关材料。
- 缺口：缺少 README/截图/UI 源码中状态指示的证据
- 缺口：缺少状态字段与取值（运行中/空闲/异常）的定义

### UNKNOWN：控制台界面能够展示任务列表。

资源：jeturing/mission-control
无任何关于任务列表界面的证据。
- 缺口：缺少任务列表 UI 或数据模型的证据

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：jeturing/mission-control
无响应式布局相关证据（无 CSS 框架、断点或截图说明）。
- 缺口：缺少响应式实现证据（媒体查询/栅格/组件库）
- 缺口：缺少窄屏视口下的可用性说明

### UNKNOWN：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：jeturing/mission-control
未提供 README 或部署文档内容，无法评估可复现性。
- 缺口：缺少官方 README/文档中的安装与启动步骤
- 缺口：缺少运行时/依赖前提说明

### UNKNOWN：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：jeturing/mission-control
无 API 定义、接口文档或源码接口实现证据。
- 缺口：缺少 API 端点/数据格式说明
- 缺口：缺少源码中接口实现的可追溯引用

### UNKNOWN：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：jeturing/mission-control
无鉴权、协作或动画相关证据，无法判断是否引入额外能力要求。
- 缺口：缺少是否内置登录/多用户模块的证据
- 缺口：缺少本地单机运行假设的验证材料

### UNKNOWN：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：omarnagy91/cortex
仅有 MIT 标识，未提供许可证条款原文，无法核实商用范围与前提。
- 缺口：缺少 LICENSE 文件条款原文（如授权范围、专利、商标、再分发条件）
- 缺口：缺少仓库开源可见性/源码可获取性的直接证据
- 来源：https://github.com/omarnagy91/cortex（license statement；读取于 2026-10-10T12:13:39.379742Z）
  > License: MIT

### UNKNOWN：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：omarnagy91/cortex
现有证据仅含许可证标识，无任何界面或状态展示相关材料。
- 缺口：缺少界面截图/文档说明状态指示
- 缺口：缺少源码中状态字段与渲染逻辑证据

### UNKNOWN：控制台界面能够展示任务列表。

资源：omarnagy91/cortex
无任务列表相关证据。
- 缺口：缺少任务列表 UI 或数据模型证据

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：omarnagy91/cortex
无响应式布局相关证据。
- 缺口：缺少 CSS 断点/响应式框架证据
- 缺口：缺少窄屏视口验证材料

### UNKNOWN：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：omarnagy91/cortex
未提供 README 或部署文档内容。
- 缺口：缺少官方 README/文档中的安装与启动步骤

### UNKNOWN：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：omarnagy91/cortex
无 API 定义或接口实现证据。
- 缺口：缺少 API 文档/OpenAPI 定义
- 缺口：缺少源码中接口路由实现证据

### UNKNOWN：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：omarnagy91/cortex
无鉴权/协作/动画相关证据，无法判断是否引入额外能力要求。
- 缺口：缺少是否含登录鉴权或协作模块的证据

### SUPPORTED：所选控制台项目必须是开源项目，且其许可证允许商业使用（无禁止商用的条款）。

资源：builderz-labs/mission-control
MIT 许可原文授予无限制使用/复制/修改/分发/再许可/销售权利，无禁止商用条款；仓库元数据亦标注 MIT。
- 缺口：未提供第三方依赖（如 @scalar/api-reference-react、xterm 等）的许可清单，整体商用合规需另行核查依赖许可
- 来源：https://github.com/builderz-labs/mission-control/blob/main/LICENSE（exact source quote: evidence_7f17262016274ca9；读取于 2026-10-11T03:14:37.938727Z）
  > Permission is hereby granted, free of charge, to any person obtaining a copy
  > of this software and associated documentation files (the "Software"), to deal
  > in the Software without restriction, including without limitation the rights
  > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  > copies of the Software

### SUPPORTED：控制台界面能够展示 Agent 的运行状态（如运行中/空闲/异常等状态指示）。

资源：builderz-labs/mission-control
README 展示活动流含每 Agent 状态与心跳事件，概览页含 fleet 状态；注册接口将状态置为 idle。
- 缺口：未给出状态枚举的完整定义（如 running/error 等取值）
- 来源：https://github.com/builderz-labs/mission-control/blob/main/README.md（exact source quote: evidence_9cd6dd4ba3ab452a；读取于 2026-10-11T03:14:37.942177Z）
  > ![Mission Control activity stream with per-agent status and heartbeat events](docs/mission-control-activity.png)

### SUPPORTED：控制台界面能够展示任务列表。

资源：builderz-labs/mission-control
README 概览图说明含 task pipeline，正文亦提及 dispatch tasks、inspect runs、review failures。
- 缺口：未提供任务列表字段/排序/筛选等界面细节
- 来源：https://github.com/builderz-labs/mission-control/blob/main/README.md（exact source quote: evidence_9cd6dd4ba3ab452a；读取于 2026-10-11T03:14:37.942177Z）
  > alt="Mission Control overview dashboard with active sessions, live activity, fleet status per runtime, and the task pipeline"

### UNKNOWN：页面布局为响应式，在桌面与移动/窄屏视口下均可正常阅读与操作。

资源：builderz-labs/mission-control
所给片段未提及响应式布局、断点或移动端适配；缺失不等于不存在，需查前端源码或文档确认。
- 缺口：需查看 Tailwind 断点用法、移动端导航或官方截图/文档中的响应式说明

### SUPPORTED：提供可复现的本地部署方法说明，且该说明有可追溯来源（官方 README/文档/发布说明等）。

资源：builderz-labs/mission-control
README 有 Start locally 章节（Node 22+/pnpm），仓库含 Dockerfile 与 docker-entrypoint.sh，来源可追溯。
- 缺口：README 中源码安装命令块被省略，需查阅完整 README/quickstart.md 获取完整步骤
- 缺口：Docker 运行命令（docker run/compose）未在所给片段中出现
- 来源：https://github.com/builderz-labs/mission-control/blob/main/README.md（exact source quote: evidence_9cd6dd4ba3ab452a；读取于 2026-10-11T03:14:37.942177Z）
  > ## Start locally
  > 
  > Node.js 22 or newer and pnpm are required for a source install.

### SUPPORTED：提供 Agent 状态/任务数据的接口对接说明，且该说明有可追溯来源（官方文档、API 定义或源码中的接口实现）。

资源：builderz-labs/mission-control
官方 agent-setup.md 给出注册/查询接口示例，package.json 引用 openapi.json 与 API 契约校验脚本。
- 缺口：任务（task）相关接口示例未在所给片段中出现
- 缺口：接口需 [REDACTED]，与“无需登录鉴权”的演示预期存在张力，需确认是否可本地关闭
- 来源：https://github.com/builderz-labs/mission-control/blob/main/docs/agent-setup.md（exact source quote: evidence_32afe857f23f47f3；读取于 2026-10-11T03:14:54.362897Z）
  > curl -X POST http://localhost:3000/api/agents \
  >   -H "Authorization: Bearer $MC_API_KEY" \
  >   -H "Content-Type: application/json"

### PARTIAL：方案面向单用户本地演示场景，不引入登录鉴权、多用户协作或高帧率动画等能力要求。

资源：builderz-labs/mission-control
定位为 self-hosted 本地 SQLite 单机控制台，符合单用户本地演示；但接口示例使用 Bearer 鉴权，鉴权是否可省略未说明。
- 缺口：未说明本地演示是否可禁用鉴权/访问控制
- 缺口：未说明是否存在多用户协作功能（存在也不构成要求，仅需确认非必需）
- 来源：https://github.com/builderz-labs/mission-control/blob/main/README.md（exact source quote: evidence_9cd6dd4ba3ab452a；读取于 2026-10-11T03:14:37.942177Z）
  > Self-hosted control plane for operating AI agents.

## 研究范围与限制

- 定向补查保留原目标与条件；未受影响的评价沿用前修订。新增资料会重新核查对应候选的全部条件。
- builderz-labs/mission-control：仓库文档读取失败：HTTPStatusError
- builderz-labs/mission-control：未获得额外文档，相关问题仍待核查。

研究用量：{"actions": 5, "tool_calls": 2, "cost_usd": 0.0141889, "known_cost_usd": 0.0141889, "reserved_usd": 0.0, "input_tokens": 14575, "output_tokens": 2347, "model_requests": 3, "cost_unknown": false, "elapsed_seconds": 27.44, "stopped_reason": null}
