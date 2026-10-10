# GoalSift 研究报告

- 任务：job_8a48c356fcd049ab
- 修订：3
- 状态：COMPLETED
- 导出时间：2026-10-10T08:40:42.436885+00:00
- 范围：公开来源的方案研究；方案尚未执行，来源支持不等于目标环境验收。

## 目标

我要一个像成熟商业产品一样好看的 Agent 管理网页，管理多个已运行的 Agent。Agent 已有 HTTP API，可查询状态、启动、暂停并接收运行事件；希望复用成熟开源资源，本地部署，先完成可用演示。视觉质量是必须条件。
用户补充：新增约束：所有复用组件必须有明确允许商业使用的开源许可。范围为单用户本地网页演示，Agent HTTP API 已可查询状态、启动、暂停，事件使用 SSE；视觉质量必须达标。优先研究成熟完整控制台或仪表盘模板，逐项说明证据和待验收项。
[clarification] 选择 B：轻量本地后端转发现有 HTTP API 和 SSE，前端复用成熟模板。后端 Node 或 Python 都可，技术栈由研究结果推荐，单用户即可。商业开源许可和成熟视觉仍是必须条件。
只保留有明确商用许可来源的候选，复用前版已读取的资料并重新匹配。允许追加轻量适配层，模板无需原生控制我的 HTTP API。不要增加我未提出的许可证类别禁令；未核实的许可条款应保留未知，需要采用前逐项确认。视觉质量仍是必须条件。

**用户原话：** 我要一个像成熟商业产品一样好看的 Agent 管理网页，管理多个已运行的 Agent。Agent 已有 HTTP API，可查询状态、启动、暂停并接收运行事件；希望复用成熟开源资源，本地部署，先完成可用演示。视觉质量是必须条件。

**约束**
- 我要一个像成熟商业产品一样好看的 Agent 管理网页，管理多个已运行的 Agent。Agent 已有 HTTP API，可查询状态、启动、暂停并接收运行事件；希望复用成熟开源资源，本地部署，先完成可用演示。视觉质量是必须条件。
- 新增约束：所有复用组件必须有明确允许商业使用的开源许可。范围为单用户本地网页演示，Agent HTTP API 已可查询状态、启动、暂停，事件使用 SSE；视觉质量必须达标。优先研究成熟完整控制台或仪表盘模板，逐项说明证据和待验收项。
- [clarification] 选择 B：轻量本地后端转发现有 HTTP API 和 SSE，前端复用成熟模板。后端 Node 或 Python 都可，技术栈由研究结果推荐，单用户即可。商业开源许可和成熟视觉仍是必须条件。
- 只保留有明确商用许可来源的候选，复用前版已读取的资料并重新匹配。允许追加轻量适配层，模板无需原生控制我的 HTTP API。不要增加我未提出的许可证类别禁令；未核实的许可条款应保留未知，需要采用前逐项确认。视觉质量仍是必须条件。

**未确认假设**
- [推断] 已有 Agent HTTP API 的接口契约（端点、鉴权、SSE 事件格式）可由用户提供或可读取
- [推断] 演示环境为本地单机，无需多用户、鉴权与权限体系
- [推断] 前端模板与后端适配层可分离部署，通过本地网络通信

**待确认问题**
- 已有 Agent HTTP API 的具体端点、鉴权方式与 SSE 事件负载格式是什么？
- 演示的验收标准中，视觉质量与功能覆盖各自的判定依据是什么？

## 候选路径

### 单用户本地 Agent 管理控制台：复用成熟模板 + 轻量适配层（候选路径）

推荐以 builderz-labs/mission-control 作为主候选控制台（MIT、自托管、6.3k stars、可本地源码/Docker 启动），配一个轻量 Node 适配层把已有 Agent HTTP API 的状态/启动/暂停与 SSE 事件转发给前端；备选为 shadcndashboard（MIT 前端模板，需自建适配层）与 gastown-dashboard（MIT，自带 Node 后端与 SSE Feed，但依赖 Gas Town 编排器）。AetharaAI/MCPFabric 有 SSE 证据但默认指向外部托管后端，本地化存在冲突。AI Agent Ops 模板与 ClauBoard 许可未确认，Faagent 许可未知，均不进入候选。所有候选的许可、SSE 对接、多 Agent 启停、视觉质量均需逐项验收，尚无任何一项经过实际运行验证。

**建议理由：** mission-control 是唯一同时具备 MIT 许可、明确自托管启动方式、多运行时编排定位与较高成熟度的候选，最贴近"成熟商业产品观感 + 本地部署"的目标；其 SSE 与逐 Agent 启停能力在现有证据中仍为未知，因此以轻量适配层补齐，而非假定模板原生支持。其余候选或缺少许可证据，或依赖外部托管后端与额外编排器。

**集成工作**
- 轻量 Node 适配层：把 Agent HTTP API 的状态查询映射为控制台列表/详情数据源
- 适配层暴露启动/暂停端点，转发到各 Agent 的 HTTP API，并回传结果与错误
- 适配层订阅 Agent SSE 事件流并转发给前端，统一事件字段与心跳/断线重连
- 前端接入适配层：替换模板默认数据源，保留其布局、组件与主题体系
- 补齐空/加载/错误/断线状态展示，保证演示时的视觉一致性
- 本地启动编排：模板前端 + 适配层 + 已有 Agent 的启动顺序与端口约定

**补充工作**
- 逐项许可清单：模板自身 LICENSE 原文、版本号，以及 React/Tailwind/shadcn 等依赖的许可与版本
- 多 Agent 列表与逐 Agent 启停交互（若模板未原生提供，需在模板内新增页面/操作）
- SSE 事件面板与筛选（若模板无事件流视图，需基于其组件库新建）
- 适配层配置化：Agent 端点、鉴权、超时与重试策略
- 演示脚本与验收清单：视觉走查、状态流转、事件到达、异常态

**风险**
- 许可证据不足：多数候选仅有仓库级 MIT 标注，缺 LICENSE 原文、版本与依赖许可明细，商用前须逐项确认
- SSE 对接未验证：mission-control 与 shadcndashboard 均无 SSE 证据，事件链路可能需自建
- 逐 Agent 启停未验证：现有证据多为监控/编排，未必提供单 Agent 启动/暂停操作
- 视觉质量仅为自述：无截图或在线演示可核验，需实际渲染验收
- 本地化冲突：MCPFabric 默认指向外部托管后端，离线运行需改造
- 外部依赖：gastown-dashboard 需 Gas Town 编排器在 PATH 中，可能引入额外组件

**假设**
- [推断] 已有 Agent HTTP API 的接口契约（端点、鉴权、SSE 事件格式）可由用户提供或可读取
- [推断] 演示环境为本地单机，无需多用户、鉴权与权限体系
- [推断] 前端模板与后端适配层可分离部署，通过本地网络通信

实施费用：{"estimate": "UNKNOWN", "basis": "没有经核实的方案实施价格"}

## 成立条件

- **[REQUIRED / FUNCTIONAL]** 交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。 (`cond_7110cb5f84a04176`)
  - 依据：model-derived: 用户明确选择方案 B：轻量本地后端转发现有 HTTP API 与 SSE，前端复用成熟模板；模板无需原生控制其 HTTP API。
  - 验收方式：在本地启动适配层与前端，对至少一个已运行的 Agent 依次执行状态查询、启动、暂停，确认请求经适配层转发到 Agent HTTP API 并返回预期结果；记录请求/响应日志作为证据。
- **[REQUIRED / FUNCTIONAL]** 控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。 (`cond_72bd59fa104f4a43`)
  - 依据：model-derived: 用户补充说明事件使用 SSE，且要求管理多个已运行的 Agent，事件可见性是演示可用性的核心。
  - 验收方式：触发 Agent 产生运行事件，观察浏览器界面在无手动刷新的情况下出现对应事件条目或状态变化；用浏览器开发者工具确认 EventSource/SSE 连接建立并收到消息。
- **[REQUIRED / FUNCTIONAL]** 控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。 (`cond_dfbe660eef0843ae`)
  - 依据：model-derived: 用户目标是管理多个已运行的 Agent。
  - 验收方式：配置至少两个 Agent 端点，确认界面同时列出两者，并能对其中一个执行启动/暂停而不影响另一个；记录操作前后各 Agent 状态。
- **[REQUIRED / COMPLIANCE]** 所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。 (`cond_5945600c48e745c0`)
  - 依据：model-derived: 用户明确要求所有复用组件必须有明确允许商业使用的开源许可，且要求逐项说明证据。
  - 验收方式：对每个复用组件，检查其仓库 LICENSE 文件与包元数据（如 package.json license 字段、PyPI 元数据），在交付清单中记录许可证名称与来源 URL；对无法确认的组件标注为未知并排除或待确认。
- **[REQUIRED / COMPLIANCE]** 交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。 (`cond_f4bd3099279b4e2f`)
  - 依据：model-derived: 用户要求逐项说明证据和待验收项，并明确未核实的许可条款应保留未知、采用前逐项确认。
  - 验收方式：审阅交付清单，确认每个组件均有证据条目与待验收项；确认不存在把未核实条款表述为已确认许可的表述。
- **[REQUIRED / QUALITY]** 控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。 (`cond_926f05a1b8ae4369`)
  - 依据：model-derived: 用户两次强调视觉质量是必须条件。
  - 验收方式：由用户或评审者按预设的视觉检查清单（布局对齐、字体层级、配色一致性、组件状态完整性、响应式表现）对运行中的界面逐项打分验收；记录截图与评分结果。
- **[REQUIRED / OTHER]** 交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。 (`cond_b2cf14b8edba4625`)
  - 依据：model-derived: 用户要求本地部署、先完成可用演示。
  - 验收方式：在无外网或仅本地网络的机器上按交付说明启动，确认前端与适配层正常运行并完成一次完整演示流程。
- **[OPTIONAL / OTHER]** 技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。 (`cond_20a7641546644f53`)
  - 依据：model-derived: 用户表示后端 Node 或 Python 都可，技术栈由研究结果推荐。
  - 验收方式：审阅交付说明中的选型章节，确认给出了候选对比与推荐理由。

## 资源与许可

- **shadcndashboard/shadcndashboard** — 许可：MIT
  - 来源：https://github.com/shadcndashboard/shadcndashboard
  - # shadcndashboard/shadcndashboard

Free, open source admin dashboard built with React + vite, shadcn/ui, Tailwind CSS, and TypeScript.

- Stars: 406
- Forks: 54
- Watchers: 406
- Open issues: 1
- License: MIT License
- Homepage: https://shadcndashboard.dev
- Default branch: main
- Created: 2026-05-20T06:04:39Z

## Languages

- CSS
- Dockerfile
- HTML
- JavaScript
- TypeScript

## Topics

- admin
- admin-dashboard
- admin-panel
- admin-template
- dashboard
- free-dashboard
- free-react-dashboard
- free-shadcn-dashboard
- open-source
- react-dashboard
- shadcn
- shadcn-dashboard
- shadcn-react
- shadcn-ui
- tanstack-table
- typescript
- vite

## Top Contributors

- wrappixelTeam (9 contributions)
- DashboardJungle (4 contributions)

---

## README

 
 
 
 
 

 
 
 Shadcn Dashboard - Free Sha
- **AetharaAI/MCPFabric** — 许可：MIT
  - 来源：https://github.com/AetharaAI/MCPFabric
  - # AetharaAI/MCPFabric

A production-ready Next.js 14 application for managing MCP (Model Context Protocol) servers. Deploy, observe, and orchestrate agent systems at scale.

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- Default branch: main
- Created: 2026-02-03T10:47:05Z

## Languages

- CSS
- Dockerfile
- HTML
- JavaScript
- TypeScript

## Top Contributors

- AetharaAI (10 contributions)

---

## README

# MCP Fabric

A production-ready Next.js 14 application for managing MCP (Model Context Protocol) servers. Deploy, observe, and orchestrate agent systems at scale.

MCP Fabric
Next.js
TypeScript
Tailwind CSS

## Features

- **Registry Explorer** - Browse and discover MCP tools, resources, and prompts
- **Observatory** - Real-time D3.js visualization of agent message passing
- **
- **AI Agent Ops - Monitoring Dashboard Template** — 许可：UNKNOWN
  - 来源：https://shadcnspace.com/templates/ai-agent-ops
  - AI Agent Ops - Monitoring Dashboard Template

New (update: 6th Oct) Launched Animated Blocks + 56+ New Blocks & Components - production-grade & copy-paste ready

# AI Agent Ops - Monitoring Dashboard Template

An AI agent operations dashboard for monitoring requests, token usage, cost, latency, and error rates across models, with API key management built in.

## AI Agent Ops Dashboard Template Built with shadcn/ui

AI Agent Ops is a monitoring dashboard designed for teams running AI agents and LLM-powered products in production. Built using Next.js, React, Tailwind CSS, TypeScript, and shadcn/ui + Base UI, it provides request, token, and cost metrics, usage and latency analytics, and API key management out of the box, so you can track model performance without building the dashboard from s
- **abhiksark/gastown-dashboard** — 许可：MIT
  - 来源：https://github.com/abhiksark/gastown-dashboard
  - # abhiksark/gastown-dashboard

- Stars: 8
- Forks: 0
- Watchers: 8
- Open issues: 0
- Default branch: main
- Created: 2026-04-03T14:41:50Z

## Languages

- CSS
- HTML
- JavaScript
- TypeScript

## Topics

- agent-observability
- gas-town
- multi-agent
- multi-agent-ai
- react
- tailwind
- vite

## Top Contributors

- abhiksark (170 contributions)

---

## README

 
 Gas Town Dashboard 
 
 Real-time monitoring and control panel for Gas Town multi-agent orchestration
 
 

 
 
 
 
 
 

 
 
 
 
 
 
 
 
 

 

 
 
 

---

## What is Gas Town Dashboard?

Gas Town orchestrates fleets of AI agents --- polecats, witnesses, refineries, deacons --- across multiple rigs, each working on beads (issues) through molecules (workflows). **This dashboard gives you full visibility and control from a single br
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
- **Sipoke123/ClauBoard** — 许可：UNKNOWN
  - 来源：https://github.com/Sipoke123/ClauBoard
  - # Sipoke123/ClauBoard

Visual control plane for AI coding agents. Launch, monitor, and coordinate multiple agents from one dashboard.

- Stars: 5
- Forks: 0
- Watchers: 5
- Open issues: 0
- License: Other
- Default branch: main
- Created: 2026-03-19T22:18:03Z

## Languages

- CSS
- Dockerfile
- JavaScript
- Shell
- TypeScript

## Top Contributors

- Sipoke123 (91 contributions)

---

## README

# ClauBoard

License: AGPL v3

**Visual control plane for Claude Code agents.** Launch, monitor, and coordinate multiple AI agents from one screen. Free, open-source, self-hosted.

ClauBoard Dashboard

---

Stop switching between terminals. ClauBoard gives you a real-time dashboard where every agent is a draggable node on a canvas, so you can see what it's doing, what tools it's calling, what files 
- **SyntaxilitY/Faagent-AI-agentic-System-Typescript** — 许可：UNKNOWN
  - 来源：https://github.com/SyntaxilitY/Faagent-AI-agentic-System-Typescript
  - # SyntaxilitY/Faagent-AI-agentic-System-Typescript

“Micro-agentic systems” are an emerging design pattern for building AI systems from many small, narrowly scoped agents rather than one large, general-purpose agent. The idea combines principles from multi-agent systems, microservices, and modern LLM-based agent frameworks. 

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- Homepage: https://migentic.vercel.app
- Default branch: main
- Created: 2026-07-08T08:27:08Z

## Languages

- CSS
- JavaScript
- TypeScript

## Topics

- micro-agent
- multi-agents
- syntaxility
- tariq-mehmood

---

## README

# AgentFabric | Enterprise Multi-Agent Framework in TypeScript

A production-grade, multi-agent orchestration system built with **Next.js**, **Drizzle ORM**, and **PostgreSQL**. This system
- **iriseye931-ai/mission-control-dashboard** — 许可：MIT
  - 来源：https://github.com/iriseye931-ai/mission-control-dashboard
  - # iriseye931-ai/blockhouse

A launch-control room for your local AI agents — block minifig crew, NASA-style GO/NO-GO board, real-time events from Claude Code hooks and agent logs. No cloud, no simulation.

- Stars: 17
- Forks: 5
- Watchers: 17
- Open issues: 0
- License: MIT License
- Default branch: main
- Created: 2026-03-25T11:45:11Z

## Languages

- CSS
- Dockerfile
- HTML
- JavaScript
- Python
- Shell
- TypeScript

## Topics

- ai-agents
- claude-code
- dashboard
- fastapi
- local-llm
- mission-control
- mlx
- multi-agent
- pixel-art
- react

## Top Contributors

- iriseye931-ai (5 contributions)

---

## README

# Blockhouse

**A launch-control room for your local AI agents — with a tiny crew that actually does the work.**

Your agents render as animated block minifigs at their conso

## 条件匹配与证据

### UNKNOWN：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：shadcndashboard/shadcndashboard
证据仅描述模板功能，未提及适配层或转发状态/启动/暂停接口的能力。
- 缺口：无证据说明该模板或配套后端可转发 Agent HTTP API 的状态查询/启动/暂停接口
- 缺口：无证据说明适配层实现方式（Node/Python）

### UNKNOWN：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：shadcndashboard/shadcndashboard
证据未提及 SSE 或实时事件流能力。
- 缺口：无 SSE/实时事件展示相关证据

### UNKNOWN：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：shadcndashboard/shadcndashboard
证据提到数据表格与列表类应用，但未涉及多 Agent 管理。
- 缺口：无多 Agent 列表/分别控制相关证据

### PARTIAL：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：shadcndashboard/shadcndashboard
仓库元数据标注 MIT 许可，但未给出具体版本号，且未覆盖其依赖组件（shadcn/ui、Tailwind 等）。
- 缺口：未提供具体版本号
- 缺口：未逐项列出依赖组件（shadcn/ui、Base UI、Tailwind CSS v4、React 19）的许可证与来源链接
- 缺口：MIT 声明来自仓库元数据，未核对 LICENSE 文件原文
- 来源：https://github.com/shadcndashboard/shadcndashboard（exact source quote: evidence_bbf5dc0c7cf4447c；读取于 2026-10-10T08:33:56.559231Z）
  > License: MIT License

### PARTIAL：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：shadcndashboard/shadcndashboard
证据提供仓库级许可与功能描述，可作为逐项证据基础，但缺少版本与依赖许可明细。
- 缺口：缺少依赖组件逐项许可证据
- 缺口：缺少版本锁定信息
- 缺口：未提供 LICENSE 文件原文链接
- 来源：https://github.com/shadcndashboard/shadcndashboard（exact source quote: evidence_bbf5dc0c7cf4447c；读取于 2026-10-10T08:33:56.559305Z）
  > License: MIT License

### PARTIAL：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：shadcndashboard/shadcndashboard
证据称其为 production-ready 现代响应式仪表盘模板，含图表、数据表与丰富组件，但未提及空/加载/错误状态。
- 缺口：未说明空/加载/错误状态处理
- 缺口：视觉质量需实际渲染验收，证据仅为自述
- 来源：https://github.com/shadcndashboard/shadcndashboard（exact source quote: evidence_bbf5dc0c7cf4447c；读取于 2026-10-10T08:33:56.559371Z）
  > Shadcn Dashboard is a production-ready admin dashboard starter to kickstart your next project.

### PARTIAL：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：shadcndashboard/shadcndashboard
基于 React+Vite 的本地可构建前端，含 Dockerfile，但证据未明确说明完全离线本地运行。
- 缺口：未说明是否需要外部托管服务或 CDN
- 缺口：未说明本地启动步骤
- 来源：https://github.com/shadcndashboard/shadcndashboard（exact source quote: evidence_bbf5dc0c7cf4447c；读取于 2026-10-10T08:33:56.559433Z）
  > Free, open source admin dashboard built with React + vite, shadcn/ui, Tailwind CSS, and TypeScript.

### UNKNOWN：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：shadcndashboard/shadcndashboard
证据支持 React+Vite 前端选型理由（现代、响应式、组件丰富），但未涉及后端 Node/Python 推荐。
- 缺口：未给出后端技术栈推荐
- 缺口：未比较其他候选模板
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/shadcndashboard/shadcndashboard（Exa /contents full source text；读取于 2026-10-10T08:14:33.950439Z）
  > # shadcndashboard/shadcndashboard
  > 
  > Free, open source admin dashboard built with React + vite, shadcn/ui, Tailwind CSS, and TypeScript.
  > 
  > - Stars: 406
  > - Forks: 54
  > - Watchers: 406
  > - Open issues: 1
  > - License: MIT License
  > - Homepage: https://shadcndashboard.dev
  > - Default branch: main
  > - Created: 2026-05-20T06:04:39Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - HTML
  > - JavaScript
  > - TypeScript
  > 
  > ## Topics
  > 
  > - admin
  > - admin-dashboard
  > - admin-panel
  > - admin-template
  > - dashboard
  > - free-dashboard
  > - free-react-dashboard
  > - free-shadcn-dashboard
  > - open-source
  > - react-dashboard
  > - shadcn
  > - shadcn-dashboard
  > - shadcn-react
  > - shadcn-ui
  > - tanstack-table
  > - typescript
  > - vite
  > 
  > ## Top Contributors
  > 
  > - wrappixelTeam (9 contributio

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：AetharaAI/MCPFabric
模板为前端控制台，可加适配层转发；但证据未提及状态查询/启动/暂停三类接口。
- 缺口：证据未说明对 Agent 状态查询/启动/暂停接口的支持
- 缺口：未说明适配层（Node/Python 转发）方案
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.559622Z）
  > **Console** - Split-pane dashboard with event stream and operation details

### SUPPORTED：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：AetharaAI/MCPFabric
证据明确列出 SSE 实时集成与事件流面板，满足事件可见更新要求。
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.559749Z）
  > - **Real-time** - SSE integration for live telemetry updates

### PARTIAL：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：AetharaAI/MCPFabric
有多租户切换与注册表浏览，暗示多实体管理，但未明确多 Agent 状态/启停。
- 缺口：未明确支持列出多个 Agent 并分别启动/暂停
- 缺口：多租户面向 MCP server 而非 Agent 生命周期
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.559809Z）
  > - **Multi-tenant** - Tenant switching with isolated data contexts

### PARTIAL：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：AetharaAI/MCPFabric
仓库标注 MIT，但证据未给出许可证文件链接或各依赖组件许可清单。
- 缺口：证据未提供 LICENSE 文件或来源链接
- 缺口：未逐项列出 Tailwind/shadcn/D3/Monaco 等依赖的许可证与版本
- 缺口：仓库 Stars/Forks 为 0，成熟度与维护性未核实
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.559862Z）
  > A production-ready Next.js 14 application for managing MCP (Model Context Protocol) servers.

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：AetharaAI/MCPFabric
证据未包含逐项许可证据与待验收项清单，无法据此判断。
- 缺口：缺少逐组件证据与待验收项
- 缺口：未核实的许可条款未标注为未知

### PARTIAL：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：AetharaAI/MCPFabric
采用 Tailwind+shadcn/ui 等成熟视觉栈，但证据未展示实际界面或空/加载/错误状态。
- 缺口：无截图或在线演示可核验视觉质量
- 缺口：未说明空/加载/错误状态处理
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.559951Z）
  > - **Styling**: Tailwind CSS + shadcn/ui

### CONFLICTED：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：AetharaAI/MCPFabric
本地 Docker/开发服务器支持本地运行，但默认配置指向外部托管后端，存在冲突。
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.560010Z）
  > The application will be available at `http://localhost:5173`.
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.560020Z）
  > | `VITE_FABRIC_API_BASE` | Fabric backend base URL for admin/docs pages | `https://fabric.perceptor.us` |

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：AetharaAI/MCPFabric
证据给出 React+Vite+TS 前端栈，但未给出后端选型理由或对比。
- 缺口：未给出 Node/Python 后端推荐及理由
- 缺口：未说明选型对比依据
- 来源：https://github.com/AetharaAI/MCPFabric（exact source quote: evidence_0a47b04953634e14；读取于 2026-10-10T08:33:56.560086Z）
  > - **Framework**: React + Vite + TypeScript

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：AI Agent Ops - Monitoring Dashboard Template
模板为 Next.js/React 前端，可经适配层对接 HTTP API，但证据未提及启动/暂停接口调用。
- 缺口：未提供状态查询/启动/暂停三类接口的对接证据
- 缺口：未说明适配层（Node/Python）方案
- 来源：https://shadcnspace.com/templates/ai-agent-ops（exact source quote: evidence_1a3750cb32274fa9；读取于 2026-10-10T08:33:56.560140Z）
  > Built using Next.js, React, Tailwind CSS, TypeScript, and shadcn/ui + Base UI

### UNKNOWN：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：AI Agent Ops - Monitoring Dashboard Template
证据仅称实时指标卡，未提及 SSE 或事件流更新机制。
- 缺口：无 SSE/事件流相关证据
- 缺口：实时更新是否自动刷新未核实

### PARTIAL：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：AI Agent Ops - Monitoring Dashboard Template
有模型/运行列表与状态标记，可承载多 Agent 列表，但无启动/暂停操作证据。
- 缺口：未提供多 Agent 启动/暂停操作证据
- 缺口：列表对象为模型而非 Agent
- 来源：https://shadcnspace.com/templates/ai-agent-ops（exact source quote: evidence_1a3750cb32274fa9；读取于 2026-10-10T08:33:56.560229Z）
  > A breakdown of deployed models with request counts and status indicators.

### UNKNOWN：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：AI Agent Ops - Monitoring Dashboard Template
来源标注 license 为 UNKNOWN，证据文本未给出任何许可证名称或来源链接。
- 缺口：模板自身许可证未知
- 缺口：shadcn/ui、Base UI、Next.js、Tailwind 等依赖许可证未逐项核实
- 缺口：无版本号与来源链接

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：AI Agent Ops - Monitoring Dashboard Template
本评估已逐项标注未知与待验收项，但来源本身未提供可核实的许可证据。
- 缺口：来源未提供许可证证据，无法完成逐项许可验收
- 缺口：需补充各依赖版本与许可证链接
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://shadcnspace.com/templates/ai-agent-ops（exact source quote: evidence_1a3750cb32274fa9；读取于 2026-10-10T08:33:56.560318Z）
  > Built using Next.js, React, Tailwind CSS, TypeScript, and shadcn/ui + Base UI

### PARTIAL：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：AI Agent Ops - Monitoring Dashboard Template
自称 production-grade、copy-paste ready 并含侧边栏与命令面板，但空/加载/错误态未提及。
- 缺口：空/加载/错误状态处理无证据
- 缺口：视觉质量需实际渲染验收
- 来源：https://shadcnspace.com/templates/ai-agent-ops（exact source quote: evidence_1a3750cb32274fa9；读取于 2026-10-10T08:33:56.560370Z）
  > production-grade & copy-paste ready

### UNKNOWN：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：AI Agent Ops - Monitoring Dashboard Template
证据未说明本地部署方式或是否依赖外部托管服务。
- 缺口：未提供本地部署说明
- 缺口：是否依赖外部服务未核实

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：AI Agent Ops - Monitoring Dashboard Template
证据显示前端为 Next.js/React 栈，可作推荐依据，但未给出后端选型理由。
- 缺口：未给出 Node/Python 后端推荐及理由
- 来源：https://shadcnspace.com/templates/ai-agent-ops（exact source quote: evidence_1a3750cb32274fa9；读取于 2026-10-10T08:33:56.560458Z）
  > Built using Next.js, React, Tailwind CSS, TypeScript, and shadcn/ui + Base UI

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：abhiksark/gastown-dashboard
有本地 Node 后端与 Vite 代理 /api/*，可作适配层基础；但证据未显示启动/暂停接口。
- 缺口：未证实存在启动/暂停（start/pause）控制接口
- 缺口：未证实可对接任意已有 Agent HTTP API（README 绑定 Gas Town 的 gt/bd）
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560513Z）
  > Server on 4800, frontend on 5173, Vite proxies `/api/*` automatically.

### SUPPORTED：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：abhiksark/gastown-dashboard
README 明确 live feed 通过 SSE 流式推送事件，并有 Feed 页可搜索过滤。
- 缺口：未证实 SSE 端点可重定向到用户自有 Agent 的事件源
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560568Z）
  > The live feed streams every event via SSE.

### PARTIAL：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：abhiksark/gastown-dashboard
Agents 页列出多 rig 全部 worker 与状态，但证据仅显示 nudge，未显示启动/暂停。
- 缺口：未证实对每个 Agent 可执行启动/暂停操作
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560624Z）
  > The **Agents** page shows all workers across all rigs with role badges, session status, and one-click nudge.

### PARTIAL：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：abhiksark/gastown-dashboard
仓库元数据标注 MIT，但证据未含 LICENSE 文件文本、版本号或依赖组件许可清单。
- 缺口：无 LICENSE 原文或来源链接证据
- 缺口：未列出 React/Tailwind/Vite 等依赖的许可证与版本
- 缺口：未确认仓库内是否含第三方受限代码
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560677Z）
  > abhiksark/gastown-dashboard

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：abhiksark/gastown-dashboard
证据仅为仓库 README 摘要，未包含任何逐项证据/待验收项或未知标注的交付说明。
- 缺口：无交付说明文档证据
- 缺口：许可条款未核实部分未标注为未知

### PARTIAL：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：abhiksark/gastown-dashboard
自述对标 Vercel/Linear 并有健康条、热力图等，但无截图或空/加载/错误态证据。
- 缺口：无实际界面截图或设计系统证据
- 缺口：未证实空/加载/错误状态处理
- 缺口：仅 8 stars、单人贡献，成熟度存疑
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560786Z）
  > Think **Vercel's deployment dashboard** meets **Linear's issue tracker**, purpose-built for multi-agent AI systems.

### PARTIAL：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：abhiksark/gastown-dashboard
本地 pnpm dev 起 4800/5173 服务，但前置依赖 Gas Town（gt/bd）本地运行。
- 缺口：依赖 Gas Town 编排器在 PATH 中可用
- 缺口：未证实无外部托管服务依赖（如字体/CDN）
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560842Z）
  > Prerequisites: Node.js 22+, pnpm, Gas Town running (gt/bd on PATH)

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：abhiksark/gastown-dashboard
证据显示 Node 后端 + React/Tailwind/Vite 前端，可作推荐依据，但无对比理由。
- 缺口：无与其他候选栈的对比或选型理由
- 来源：https://github.com/abhiksark/gastown-dashboard（exact source quote: evidence_9cc805047e534827；读取于 2026-10-10T08:33:56.560897Z）
  > Server on 4800, frontend on 5173, Vite proxies `/api/*` automatically.

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：builderz-labs/mission-control
本地自托管控制台存在，但证据未显示状态/启动/暂停三类接口或适配层。
- 缺口：未提供状态查询/启动/暂停接口文档
- 缺口：未说明可对接任意已有 HTTP API 的适配层
- 缺口：未说明单用户模式
- 来源：https://github.com/builderz-labs/mission-control（exact source quote: evidence_d1e7e6c16d0247c5；读取于 2026-10-10T08:33:56.560954Z）
  > Self-hosted control plane for AI agents: dispatch tasks, review runs, track spend, and operate OpenClaw, Claude Code, Codex, and other runtimes.

### UNKNOWN：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：builderz-labs/mission-control
证据未提及 SSE 或实时事件流展示能力。
- 缺口：无 SSE/实时事件证据

### PARTIAL：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：builderz-labs/mission-control
证据显示可协调多种运行时，但未证实多 Agent 列表与逐项启停。
- 缺口：未证实多 Agent 列表视图
- 缺口：未证实逐 Agent 启动/暂停
- 来源：https://github.com/builderz-labs/mission-control（exact source quote: evidence_d1e7e6c16d0247c5；读取于 2026-10-10T08:33:56.561070Z）
  > It works with OpenClaw, Claude Code, Codex, and other runtimes - it is not part of any one of them.

### PARTIAL：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：builderz-labs/mission-control
仓库标注 MIT，但未逐项列出子组件/依赖的许可证与版本。
- 缺口：未列出各子组件名称/版本/许可证/来源链接
- 缺口：依赖树许可证未核实
- 来源：https://github.com/builderz-labs/mission-control（exact source quote: evidence_d1e7e6c16d0247c5；读取于 2026-10-10T08:33:56.561127Z）
  > License: MIT License

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：builderz-labs/mission-control
现有证据仅为仓库元数据，无逐项证据与待验收项清单。
- 缺口：无逐组件证据/待验收项
- 缺口：无未知项标注
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/builderz-labs/mission-control（Exa /contents full source text；读取于 2026-10-10T08:15:27.080634Z）
  > # builderz-labs/mission-control
  > 
  > Self-hosted control plane for AI agents: dispatch tasks, review runs, track spend, and operate OpenClaw, Claude Code, Codex, and other runtimes.
  > 
  > - Stars: 6332
  > - Forks: 107
  > - Watchers: 6332
  > - Open issues: 50
  > - License: MIT License
  > - Homepage: https://mc.builderz.dev
  > - Default branch: main
  > - Created: 2026-02-13T04:06:19Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - JavaScript
  > - PowerShell
  > - Python
  > - Shell
  > - TypeScript
  > 
  > ## Topics
  > 
  > - agent-observability
  > - agent-operations
  > - agent-orchestration
  > - ai-agents
  > - claude-code
  > - codex
  > - developer-tools
  > - mcp
  > - nextjs
  > - open-source
  > - openclaw
  > - self-hosted
  > - sqlite
  > - ta[REDACTED]
  > - typescript
  > 
  > ## Top Contributors
  > 
  > - 0xNyk (432 co

### UNKNOWN：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：builderz-labs/mission-control
证据未包含界面截图或视觉质量说明，无法评估。
- 缺口：无 UI 截图/设计说明
- 缺口：无空/加载/错误状态证据

### SUPPORTED：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：builderz-labs/mission-control
证据明确给出本地源码与 Docker 自托管启动方式。
- 缺口：未确认运行时是否需外部托管服务
- 来源：https://github.com/builderz-labs/mission-control（exact source quote: evidence_d1e7e6c16d0247c5；读取于 2026-10-10T08:33:56.561275Z）
  > Self-hosted control plane for operating AI agents.

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：builderz-labs/mission-control
证据显示 Node.js 22 + pnpm + Next.js 技术栈，但无推荐理由。
- 缺口：无选型理由说明
- 来源：https://github.com/builderz-labs/mission-control（exact source quote: evidence_d1e7e6c16d0247c5；读取于 2026-10-10T08:33:56.561346Z）
  > Node.js 22 or newer and pnpm are required for a source install.

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：Sipoke123/ClauBoard
ClauBoard 是自托管控制台，但证据未显示可经适配层调用外部 HTTP 状态/启动/暂停接口。
- 缺口：未证实存在可对接外部 Agent HTTP API 的适配层或状态查询/启动/暂停接口映射
- 缺口：未证实单用户本地运行模式
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561408Z）
  > Free, open-source, self-hosted.

### NOT_SATISFIED：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：Sipoke123/ClauBoard
证据显示事件通过 WebSocket 推送，而非要求的 SSE。
- 缺口：未提供 SSE 支持证据；需适配层转换 WebSocket/SSE
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561465Z）
  > Every tool call, file edit, and terminal output streams via WebSocket

### SUPPORTED：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：Sipoke123/ClauBoard
证据明确支持从单一仪表盘启动、监控并协调多个 Agent。
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561522Z）
  > Launch, monitor, and coordinate multiple agents from one dashboard.

### UNKNOWN：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：Sipoke123/ClauBoard
README 声明 AGPL v3，属强 copyleft，非明确允许商业使用的宽松许可。
- 缺口：AGPL v3 不满足“明确允许商业使用”的宽松许可要求
- 缺口：元数据 License 字段为 Other，与 README 声明不一致，需核实
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561577Z）
  > License: AGPL v3

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：Sipoke123/ClauBoard
许可信息存在冲突（元数据 Other vs README AGPL v3），需标注为待确认。
- 缺口：许可证字段与 README 声明不一致，须列为未知/待确认
- 缺口：缺少版本号与来源链接的逐项清单
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561637Z）
  > License: Other

### UNKNOWN：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：Sipoke123/ClauBoard
证据仅描述功能与主题切换，无视觉质量或状态处理的直接证据。
- 缺口：无截图或设计系统证据
- 缺口：未提及空/加载/错误状态处理

### UNKNOWN：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：Sipoke123/ClauBoard
证据显示自托管并提供 Docker 一键部署，可本地运行。
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/Sipoke123/ClauBoard（Exa /contents full source text；读取于 2026-10-10T08:15:32.135948Z）
  > # Sipoke123/ClauBoard
  > 
  > Visual control plane for AI coding agents. Launch, monitor, and coordinate multiple agents from one dashboard.
  > 
  > - Stars: 5
  > - Forks: 0
  > - Watchers: 5
  > - Open issues: 0
  > - License: Other
  > - Default branch: main
  > - Created: 2026-03-19T22:18:03Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - JavaScript
  > - Shell
  > - TypeScript
  > 
  > ## Top Contributors
  > 
  > - Sipoke123 (91 contributions)
  > 
  > ---
  > 
  > ## README
  > 
  > # ClauBoard
  > 
  > License: AGPL v3
  > 
  > **Visual control plane for Claude Code agents.** Launch, monitor, and coordinate multiple AI agents from one screen. Free, open-source, self-hosted.
  > 
  > ClauBoard Dashboard
  > 
  > ---
  > 
  > Stop switching between terminals. ClauBoard gives you a real-time dashboard where every agent i

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：Sipoke123/ClauBoard
证据显示 TypeScript/JavaScript 技术栈，但未给出选型理由或对比。
- 缺口：未提供技术栈推荐理由
- 缺口：后端框架未明确
- 来源：https://github.com/Sipoke123/ClauBoard（exact source quote: evidence_cbbe039941e84b44；读取于 2026-10-10T08:33:56.561786Z）
  > CSS
  > - Dockerfile
  > - JavaScript
  > - Shell
  > - TypeScript

### UNKNOWN：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据仅描述该框架自身的编排/SSE 架构，未提及状态查询、启动、暂停三类接口或适配层。
- 缺口：无证据表明该资源提供或可适配状态查询/启动/暂停接口
- 缺口：无证据表明存在轻量适配层设计

### PARTIAL：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据显示该框架使用 SSE 流式推送运行事件，但未说明前端界面是否展示这些事件。
- 缺口：未说明前端是否有事件流列表或自动刷新 UI
- 缺口：未说明是否可对接外部 Agent 的 SSE 端点
- 来源：https://github.com/SyntaxilitY/Faagent-AI-agentic-System-Typescript（exact source quote: evidence_9a300812d7da4f92；读取于 2026-10-10T08:33:56.561885Z）
  > API -->|Stream Connection| SSE[SSE Route: /api/runs/:id/stream]

### UNKNOWN：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据提到多智能体编排，但未提供列出多个已运行 Agent 并分别启停的管理界面证据。
- 缺口：无证据表明可列出并分别管理多个已运行 Agent
- 缺口：无证据表明支持对单个 Agent 执行启动/暂停

### UNKNOWN：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
该资源许可证标注为 UNKNOWN，证据中无任何许可证名称或来源链接，无法核实商用许可。
- 缺口：许可证为 UNKNOWN，缺少许可证名称与来源链接
- 缺口：未列出所依赖组件（Next.js、Drizzle ORM 等）的版本与许可证

### UNKNOWN：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据未包含逐项证据与待验收项清单，也未对许可条款作未知/待确认标注。
- 缺口：缺少逐项证据与待验收项
- 缺口：缺少对未核实许可条款的未知/待确认标注

### UNKNOWN：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据仅含架构图与文字描述，无界面截图或视觉质量说明，无法评估视觉质量。
- 缺口：无界面截图或设计说明
- 缺口：无法评估布局、排版、配色、组件一致性及空/加载/错误状态

### UNKNOWN：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据未说明本地部署方式；其依赖 PostgreSQL 与外部托管主页，本地可运行性未证实。
- 缺口：未提供本地部署说明
- 缺口：依赖 PostgreSQL 等外部组件，是否满足纯本地演示未知

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：SyntaxilitY/Faagent-AI-agentic-System-Typescript
证据表明该资源为 TypeScript/Next.js 技术栈，可作为 Node 方向候选，但未给出选型理由对比。
- 缺口：未提供与其他候选栈的对比与推荐理由
- 缺口：未说明前端模板选型依据
- 来源：https://github.com/SyntaxilitY/Faagent-AI-agentic-System-Typescript（exact source quote: evidence_fcc6b6e3bcb6446b；读取于 2026-10-10T08:33:56.562139Z）
  > A production-grade, multi-agent orchestration system built with **Next.js**, **Drizzle ORM**, and **PostgreSQL**.

### PARTIAL：交付物是一个可在单用户本地环境运行的网页控制台，能够通过一个轻量适配层（Node 或 Python 均可）转发并调用已有 Agent HTTP API 的状态查询、启动、暂停三类接口，前端不要求原生支持这些接口。

资源：iriseye931-ai/mission-control-dashboard
有 FastAPI 后端与前端，可加适配层；但证据未提及状态查询/启动/暂停三类接口。
- 缺口：未证实存在状态查询/启动/暂停接口或可对接的适配层
- 缺口：未说明单用户本地运行方式
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（exact source quote: evidence_eecdf075e0a242c2；读取于 2026-10-10T08:33:56.562197Z）
  > React 19 FastAPI MLX License

### UNKNOWN：控制台能够接收并展示 Agent 通过 SSE 推送的运行事件，且事件在界面上可见地更新（如事件流列表或状态刷新），无需用户手动刷新页面。

资源：iriseye931-ai/mission-control-dashboard
有实时事件流与滚动日志，但证据未说明使用 SSE 协议。
- 缺口：未证实事件传输为 SSE（可能为 WebSocket 或轮询）
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（Exa /contents full source text；读取于 2026-10-10T08:15:41.901496Z）
  > # iriseye931-ai/blockhouse
  > 
  > A launch-control room for your local AI agents — block minifig crew, NASA-style GO/NO-GO board, real-time events from Claude Code hooks and agent logs. No cloud, no simulation.
  > 
  > - Stars: 17
  > - Forks: 5
  > - Watchers: 17
  > - Open issues: 0
  > - License: MIT License
  > - Default branch: main
  > - Created: 2026-03-25T11:45:11Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - HTML
  > - JavaScript
  > - Python
  > - Shell
  > - TypeScript
  > 
  > ## Topics
  > 
  > - ai-agents
  > - claude-code
  > - dashboard
  > - fastapi
  > - local-llm
  > - mission-control
  > - mlx
  > - multi-agent
  > - pixel-art
  > - react
  > 
  > ## Top Contributors
  > 
  > - iriseye931-ai (5 contributions)
  > 
  > ---
  > 
  > ## README
  > 
  > # Blockhouse
  > 
  > **A launch-control room for your local AI agents — with a ti

### PARTIAL：控制台支持同时管理多个已运行的 Agent（可列出多个 Agent 并分别查看状态、执行启动/暂停），而非仅支持单个 Agent。

资源：iriseye931-ai/mission-control-dashboard
多 Agent 展示与筛选有证据，但启动/暂停操作未证实。
- 缺口：未证实可对单个 Agent 执行启动/暂停操作
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（exact source quote: evidence_eecdf075e0a242c2；读取于 2026-10-10T08:33:56.562310Z）
  > each agent is a block minifig at a console with a live status LED

### PARTIAL：所选用的每一个复用组件（前端模板/仪表盘、UI 组件库、后端框架等）都具备可核实的、明确允许商业使用的开源许可证来源（如 MIT、Apache-2.0、BSD 等），并在交付说明中逐项列出组件名称、版本、许可证名称与来源链接。

资源：iriseye931-ai/mission-control-dashboard
仓库标注 MIT，但未逐项列出子组件（React、FastAPI 等）版本与许可来源。
- 缺口：未提供各子组件（React 19、FastAPI 等）的版本与许可证来源链接
- 缺口：未提供许可证文件原文链接
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（exact source quote: evidence_eecdf075e0a242c2；读取于 2026-10-10T08:33:56.562368Z）
  > License: MIT License

### NOT_SATISFIED：交付说明中对每个复用组件逐项给出证据与待验收项，且对任何未核实的许可条款或未确认事项明确标注为未知/待确认，不作出未经核实的许可结论。

资源：iriseye931-ai/mission-control-dashboard
现有资料仅为仓库元数据，无逐项证据与待验收项清单。
- 缺口：缺少逐组件证据与待验收项
- 缺口：缺少未知/待确认事项标注
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（exact source quote: evidence_eecdf075e0a242c2；读取于 2026-10-10T08:33:56.562427Z）
  > License: MIT License

### UNKNOWN：控制台界面达到成熟商业产品级别的视觉质量（布局、排版、配色、组件一致性、空/加载/错误状态处理），作为必须满足的验收条件。

资源：iriseye931-ai/mission-control-dashboard
有 NASA 风格面板与像素动画等视觉设计，但空/加载/错误状态未证实。
- 缺口：未证实空/加载/错误状态处理
- 缺口：无截图或设计规范可核验商业级视觉一致性
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（Exa /contents full source text；读取于 2026-10-10T08:15:41.901496Z）
  > # iriseye931-ai/blockhouse
  > 
  > A launch-control room for your local AI agents — block minifig crew, NASA-style GO/NO-GO board, real-time events from Claude Code hooks and agent logs. No cloud, no simulation.
  > 
  > - Stars: 17
  > - Forks: 5
  > - Watchers: 17
  > - Open issues: 0
  > - License: MIT License
  > - Default branch: main
  > - Created: 2026-03-25T11:45:11Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - HTML
  > - JavaScript
  > - Python
  > - Shell
  > - TypeScript
  > 
  > ## Topics
  > 
  > - ai-agents
  > - claude-code
  > - dashboard
  > - fastapi
  > - local-llm
  > - mission-control
  > - mlx
  > - multi-agent
  > - pixel-art
  > - react
  > 
  > ## Top Contributors
  > 
  > - iriseye931-ai (5 contributions)
  > 
  > ---
  > 
  > ## README
  > 
  > # Blockhouse
  > 
  > **A launch-control room for your local AI agents — with a ti

### UNKNOWN：交付物可在本地部署运行，不依赖外部托管服务即可完成演示（除被管理的 Agent 自身端点外）。

资源：iriseye931-ai/mission-control-dashboard
明确声明无云、无 API key，本地运行。
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（Exa /contents full source text；读取于 2026-10-10T08:15:41.901496Z）
  > # iriseye931-ai/blockhouse
  > 
  > A launch-control room for your local AI agents — block minifig crew, NASA-style GO/NO-GO board, real-time events from Claude Code hooks and agent logs. No cloud, no simulation.
  > 
  > - Stars: 17
  > - Forks: 5
  > - Watchers: 17
  > - Open issues: 0
  > - License: MIT License
  > - Default branch: main
  > - Created: 2026-03-25T11:45:11Z
  > 
  > ## Languages
  > 
  > - CSS
  > - Dockerfile
  > - HTML
  > - JavaScript
  > - Python
  > - Shell
  > - TypeScript
  > 
  > ## Topics
  > 
  > - ai-agents
  > - claude-code
  > - dashboard
  > - fastapi
  > - local-llm
  > - mission-control
  > - mlx
  > - multi-agent
  > - pixel-art
  > - react
  > 
  > ## Top Contributors
  > 
  > - iriseye931-ai (5 contributions)
  > 
  > ---
  > 
  > ## README
  > 
  > # Blockhouse
  > 
  > **A launch-control room for your local AI agents — with a ti

### PARTIAL：技术栈（Node 或 Python 后端、前端模板选型）由研究结果推荐并给出理由，而非预先锁定某一框架。

资源：iriseye931-ai/mission-control-dashboard
证据显示为 React 19 + FastAPI 组合，可作为推荐依据，但无选型理由。
- 缺口：未给出相对 Node 方案的选型理由
- 来源：https://github.com/iriseye931-ai/mission-control-dashboard（exact source quote: evidence_eecdf075e0a242c2；读取于 2026-10-10T08:33:56.562588Z）
  > React 19 FastAPI MLX License

## 研究范围与限制

- 候选目录限制为 8 个资源；未调查的候选不作结论。
- 检索范围内仍有未覆盖条件；这些缺口已保留，不代表目标已实现。

研究用量：{"actions": 17, "tool_calls": 2, "cost_usd": 0.0500969, "known_cost_usd": 0.0500969, "reserved_usd": 0.0, "input_tokens": 49155, "output_tokens": 17792, "model_requests": 15, "cost_unknown": false, "elapsed_seconds": 113.53, "stopped_reason": null}
