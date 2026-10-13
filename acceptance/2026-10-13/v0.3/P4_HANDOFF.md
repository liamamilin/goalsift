# GoalSift 研究交接包

- 任务：job_99d6ae93275f4571
- 研究修订：2
- 状态：COMPLETED
- 导出时间：2026-10-13T06:54:07.277204+00:00
- 注记截止：事件游标 119；2026-10-13T06:49:29.325961+00:00
- 范围：公开来源的方案研究；方案尚未执行，来源支持不等于目标环境验收。
- 研究费用：已记录 $0.0639041；这不等同于服务商账单

## 目标

研究如何构建一个本地优先的 Agent 管理仪表盘，用于展示多个 Agent 的在线状态与最近活动。要求响应式网页、可导出 JSON；开源组件的商用许可需要核实，未经目标环境测试的接口应标为未知。
用户补充：新增约束：优先考虑允许商业使用且许可证条款可核验的开源组件。请针对核心候选逐项搜索许可证原文、版本与依赖清单；如果来源无法证实，保持 UNKNOWN。对 Agent 状态与活动数据接口，补充官方接口文档和验证方法；在目标环境没有实测前始终标为未知/未验证，不得宣称可用。仅研究并提出核验路径，不执行任何组件或接口。然后基于这些约束重新评估原候选方案及仍未解决的缺口。
[clarification] 目前不接受或否决任何具体组件，也不指定技术栈，不放宽原目标条件（本地优先、响应式界面、JSON 导出、许可证逐项核验、未实测接口标未知）。请继续做证据对照评估：报告哪些候选有许可证原文、版本和依赖证据，哪些接口有官方文档与可执行的验证方法；没有充分来源证据的仍保持 UNKNOWN。仅更新研究建议与缺口，不执行实施。

**用户原话：** 研究如何构建一个本地优先的 Agent 管理仪表盘，用于展示多个 Agent 的在线状态与最近活动。要求响应式网页、可导出 JSON；开源组件的商用许可需要核实，未经目标环境测试的接口应标为未知。

**用户要求与已确认前提**
- [USER_STATED] 研究如何构建一个本地优先的 Agent 管理仪表盘，用于展示多个 Agent 的在线状态与最近活动。要求响应式网页、可导出 JSON；开源组件的商用许可需要核实，未经目标环境测试的接口应标为未知。
- [USER_STATED] 新增约束：优先考虑允许商业使用且许可证条款可核验的开源组件。请针对核心候选逐项搜索许可证原文、版本与依赖清单；如果来源无法证实，保持 UNKNOWN。对 Agent 状态与活动数据接口，补充官方接口文档和验证方法；在目标环境没有实测前始终标为未知/未验证，不得宣称可用。仅研究并提出核验路径，不执行任何组件或接口。然后基于这些约束重新评估原候选方案及仍未解决的缺口。
- [USER_STATED] [clarification] 目前不接受或否决任何具体组件，也不指定技术栈，不放宽原目标条件（本地优先、响应式界面、JSON 导出、许可证逐项核验、未实测接口标未知）。请继续做证据对照评估：报告哪些候选有许可证原文、版本和依赖证据，哪些接口有官方文档与可执行的验证方法；没有充分来源证据的仍保持 UNKNOWN。仅更新研究建议与缺口，不执行实施。

**未确认假设**
- [SYSTEM_ASSUMED] （推断）Agent 的在线状态与最近活动数据可由本地可访问的数据源或接口提供，具体来源待核验
- [SYSTEM_ASSUMED] （推断）目标环境为可自行部署的本地/内网环境，具备运行响应式网页前端与本地数据存储的条件
- [SYSTEM_ASSUMED] （推断）用户可提供或指定待评估的核心候选组件清单，用于逐项许可证核验

**待确认问题**
- Agent 在线状态与最近活动的数据来源与接口具体是什么（官方文档位置、鉴权方式、可执行的验证方法）？
- 待逐项核验许可证原文、版本与依赖清单的核心候选组件清单由谁提供、以何为准？

## 候选路径

### 本地优先 Agent 管理仪表盘：证据对照评估与核验路径（不执行实施）

按用户复核决定，本轮只做证据对照，不选定或否决任何组件、不指定技术栈、不执行安装/调用/部署。八个候选中，仅 OpenAgenticOS 与 wildware-uk/agent-dashboard 具备可定位的许可证原文、版本号与部分依赖证据；Claude Code Agent Monitor、brunokktro/agent-dashboard、vibe-dash、agentmon、claude-agent-dashboard、agent-comm 的许可证原文/版本/依赖清单均缺来源，保持 UNKNOWN。响应式与 JSON 导出在全部候选中均无充分原文证据（agent-comm 仅 PARTIAL）。Agent 状态/活动接口方面，仅 agent-dashboard 设计文档给出 SSE 端点与事件类型、OpenAgenticOS 给出状态 API 字段与本地端口，均未在目标环境实测，一律标为未验证。缺口：依赖级许可证逐项核验、导出功能证据、响应式视口证据、接口可执行验证步骤。

**研究建议理由：** 建议以"证据最完整的两个候选"作为核验起点而非选型结论：OpenAgenticOS 与 agent-dashboard 有许可证原文、版本号与部分依赖来源，其余候选许可证与依赖证据缺失，无法支撑商用判断。两者均未实测，响应式与 JSON 导出无原文证据，接口可用性未知。下一步只做逐项核验（LICENSE 全文、lockfile/SBOM、导出与断点证据、接口验证脚本设计），不执行任何组件或接口。

**集成工作**
- 若采用 OpenAgenticOS：需自行实现 JSON 导出与响应式布局，其状态 API 字段与本地端口仅为文档描述，未实测
- 若采用 agent-dashboard：需按设计文档接入 SSE 事件流与 MCP 上报工具，端点契约需先取得完整官方文档
- 两者均需自建 Agent 状态/活动采集适配层，把各 Agent 探针输出映射为统一状态与最近活动模型
- 需建立依赖级许可证清单（lockfile/SBOM）与 NOTICE/版权声明保留流程，覆盖传递依赖
- 需设计目标环境验证脚本（本地端点探测、事件完整性断言、桌面/移动视口检查），本轮不执行

**补充工作**
- JSON 导出功能：全部候选均无原文证据，可能需新开发导出端点与字段定义
- 响应式界面：全部候选均无断点/视口证据，可能需新开发或改造前端布局
- 许可证逐项核验：需获取各候选 LICENSE 全文、SPDX 标识、版本标签与完整依赖清单
- 接口官方文档与验证方法：需补齐端点路径、方法、响应 schema 与可执行验证步骤
- 离线/无托管依赖证明：需确认是否存在必须联网的推送或托管服务依赖

**风险**
- 许可证证据缺口：多数候选仅有标识声明，无条款原文，商用许可无法判定，保持 UNKNOWN
- 依赖级许可风险：即使仓库自身为 MIT/Apache-2.0，传递依赖（如原生模块、媒体库）许可未核验
- 接口未实测：状态与活动数据来源在目标环境的可用性、事件完整性均未验证
- 响应式与导出能力可能不存在，需新开发，工作量与可行性未评估
- 本地优先主张多为自述，缺少离线运行与存储架构的可核验证据
- 候选仓库星标极少、创建时间新，维护与长期可用性存在不确定性
- 部分所选资源没有补充文档读取；许可、接口、部署和依赖缺口需人工核查。

**假设**
- （推断）Agent 的在线状态与最近活动数据可由本地可访问的数据源或接口提供，具体来源待核验
- （推断）目标环境为可自行部署的本地/内网环境，具备运行响应式网页前端与本地数据存储的条件
- （推断）用户可提供或指定待评估的核心候选组件清单，用于逐项许可证核验

实施费用：{"estimate": "UNKNOWN", "basis": "没有经核实的方案实施价格"}

## 方案决定与采用前检查

- 决定状态：本修订已记录倾向方案
- 所选方案：本地优先 Agent 管理仪表盘：证据对照评估与核验路径（不执行实施）（研究修订 r2）
- 用户理由：仅把此方案作为核验路径的阶段性倾向；尚未接受任何组件或技术栈。先核对许可证原文、依赖清单与接口测试方法，响应式和 JSON 导出仍需实测；本记录不代表实施批准。
- 决定注记版本：2

### 检查清单

- **FOLLOW_UP**：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。（依据状态：UNKNOWN；注记版本 1）
  - 下一步：按验收方式收集实际结果：在断网（或屏蔽外网）的本地环境中启动并操作仪表盘，确认 Agent 列表、在线状态与最近活动仍可读取与展示；记录断网场景下的功能清单与失败项。。
  - 缺口：未提供离线运行/无托管依赖的架构或部署证据
  - 缺口：未在目标环境实测
  - 缺口：无架构/存储/离线运行文档证据
  - 缺口：无依赖清单以判断是否需联网托管服务
  - 缺口：片段被省略，无法确认是否存在必须联网的托管服务依赖
  - 缺口：未提供部署/运行前置条件清单
  - 缺口：缺少架构/存储/离线运行说明
  - 缺口：缺少依赖清单以判断是否强制联网托管服务
  - 缺口：片段未说明状态与活动数据的本地存储机制（数据库/文件）
  - 缺口：未证实无任何联网托管依赖（如推送通知服务）
  - 缺口：缺少架构说明、README 运行前提、数据存储位置等证据
  - 缺口：未提供是否依赖托管服务的说明
  - 缺口：未在目标环境实测本地运行与离线行为
  - 缺口：README 为部分摘录，未覆盖全部运行路径
  - 缺口：未在目标环境实测启动与离线运行
  - 缺口：MCP 远程 Streamable HTTP 接入方式是否需联网未证实
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948）
  - 依据来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
  - 依据来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d）
  - 用户记录：测试环境未建立，本轮未执行 Agent 接口调用；许可证与传递依赖还需逐项核验。保留为待跟进，不作为通过证据。
- **PENDING**：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：在至少一个桌面视口与一个移动视口（如 375px 宽）下加载页面，检查布局无横向溢出、关键信息（状态、最近活动）可见可读；记录截图与视口尺寸。。
  - 缺口：缺少响应式布局或移动端适配的原文证据
  - 缺口：缺少桌面/移动视口实测记录
  - 缺口：无前端框架/样式或响应式设计证据
  - 缺口：无桌面与移动端渲染验证记录
  - 缺口：无移动端视口实测或断点说明
  - 缺口：未证实状态与活动在移动端可正常查看
  - 缺口：缺少前端框架与响应式设计证据
  - 缺口：缺少桌面/移动视口验证方法
  - 缺口：无 CSS/断点或响应式实现证据
  - 缺口：无桌面与移动视口实测记录
  - 缺口：缺少 UI 技术栈与响应式设计证据
  - 缺口：缺少桌面/移动端视口验证方法
  - 缺口：缺少响应式/移动端视口的文档或代码证据
  - 缺口：需查 UI 源码与 CSS 断点后再判定
  - 缺口：缺少响应式布局、断点或移动端视口的官方说明
  - 依据来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
- **PENDING**：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：在界面触发导出操作，获取生成的 JSON 文件，用 JSON 解析器校验其可解析，并核对其中包含 Agent 标识、状态与活动记录字段。。
  - 缺口：缺少 JSON 导出功能的原文证据
  - 缺口：stream-json 为输出格式，不等同于导出 JSON 文件
  - 缺口：无导出功能代码或文档证据
  - 缺口：未证实导出格式为 JSON
  - 缺口：未证实导出覆盖状态与最近活动字段
  - 缺口：缺少导出功能文档或代码证据
  - 缺口：需检索 README 全文与源码中 export/JSON 相关实现
  - 缺口：缺少导出功能证据
  - 缺口：缺少 JSON 导出验证方法
  - 缺口：无导出功能文档证据
  - 缺口：需查 API/CLI 是否提供导出端点
  - 缺口：缺少 JSON 导出功能/端点文档
  - 缺口：缺少导出文件格式与字段定义
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
- **PENDING**：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：为每个候选建立证据表：许可证原文链接/文件路径、版本号、依赖清单来源；逐条标注 CONFIRMED 或 UNKNOWN，并复核 UNKNOWN 条目确实缺少可追溯来源。。
  - 缺口：无许可证原文
  - 缺口：无版本号
  - 缺口：无依赖清单
  - 缺口：需查仓库 LICENSE 文件与 package.json/lockfile
  - 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
  - 缺口：缺少 MIT 许可证原文全文（仅标识）
  - 缺口：缺少版本号/发布标签证据
  - 缺口：缺少依赖清单（如 package.json/lockfile）证据
  - 缺口：无依赖清单（仅称 3 runtime deps，未列名）
  - 缺口：缺少 LICENSE 文件原文条款
  - 缺口：缺少版本号/发布标签
  - 缺口：缺少依赖清单（如 lockfile/SBOM）
  - 缺口：需 LICENSE 文件原文与 SPDX 标识
  - 缺口：需 release/tag 或 package 版本号
  - 缺口：需依赖清单（如 package.json / lockfile）
  - 缺口：缺少 MIT 许可证原文（LICENSE 文件全文）
  - 缺口：缺少依赖清单（如 package.json / lockfile）证据
  - 缺口：无 package-lock.json / 依赖树证据
  - 缺口：依赖清单条目保持 UNKNOWN
  - 缺口：package.json 依赖清单为截断片段，未含全部依赖
  - 缺口：各传递依赖的许可证原文与版本未核验
  - 缺口：package-lock.json 未提供
  - 依据来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6）
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE（exact source quote: evidence_5956966f61424259）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json（exact source quote: evidence_32ca15e079504732）
  - 依据来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e）
  - 依据来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12）
  - 依据来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf）
- **PENDING**：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：对照许可证原文中关于商业使用/再分发/修改的条款逐条引用，形成“允许商用：是/否/UNKNOWN”的判定表，并附条款出处。。
  - 缺口：缺少许可证标识与条款原文
  - 缺口：需核验 LICENSE 全文及商用授权范围
  - 缺口：需获取 LICENSE 文件原文以引用授权条款
  - 缺口：需确认许可证适用范围（代码/文档/资产）
  - 缺口：缺少许可证原文与 SPDX 标识
  - 缺口：缺少商用条款依据
  - 缺口：需引用 Apache-2.0 第2条授权与第4条条件原文
  - 缺口：需确认适用版本与 NOTICE 要求
  - 缺口：需引用 LICENSE 中授权/限制条款原文后再判定
  - 缺口：缺少 MIT 许可证正文条款引用（如授予权利、再分发条件）
  - 缺口：缺少许可证适用范围说明（仓库整体 vs 部分文件）
  - 缺口：需确认仓库内是否含第三方代码或子目录其他许可
  - 缺口：需保留版权与许可声明以满足 MIT 条件
  - 缺口：依赖组件（如 sharp、better-sqlite3、ffmpeg 等）的商用许可未核验
  - 缺口：未核验 MIT 声明是否覆盖全部仓库内容
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/LICENSE（exact source quote: evidence_3945ea3558d149a9）
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE（exact source quote: evidence_5956966f61424259）
- **PENDING**：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：为每个接口记录官方文档链接、版本/端点信息与验证步骤（如请求样例、预期响应字段、鉴权方式）；在目标环境执行前，状态字段保持 UNKNOWN/UNVERIFIED，并记录尚未执行的验证项。。
  - 缺口：未给出可执行验证步骤（如 curl 示例、期望响应）
  - 缺口：未在目标环境实测，接口可用性保持未知/未验证
  - 缺口：无接口文档链接
  - 缺口：无验证方法（如请求样例、schema、健康检查）
  - 缺口：目标环境未实测，保持未验证
  - 缺口：无端点/字段级接口文档
  - 缺口：无官方验证方法或示例请求
  - 缺口：目标环境未实测，可用性保持未知
  - 缺口：缺少接口官方文档链接
  - 缺口：缺少可执行验证步骤（如请求样例、断言）
  - 缺口：需 Claude Code / Codex hooks 官方文档链接
  - 缺口：需可执行验证步骤（如本地 hook 触发与状态断言）
  - 缺口：目标环境未实测，状态一律未验证
  - 缺口：缺少官方接口文档链接
  - 缺口：缺少可执行验证步骤（如本地探针、契约测试）
  - 缺口：接口可用性未实测，保持未知/未验证
  - 缺口：无端点路径、方法、响应 schema 的官方文档
  - 缺口：验证方法（如 curl 127.0.0.1:4180 状态端点）未在目标环境执行
  - 缺口：接口可用性保持 UNKNOWN/未验证
  - 缺口：未提供可执行验证步骤（如 curl 示例、预期响应）
  - 缺口：MCP 工具（post_update 等）的官方接口文档未提供
  - 缺口：目标环境未实测，可用性 UNKNOWN
  - 依据来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
  - 依据来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d）
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948）
- **PENDING**：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。（依据状态：PARTIAL；注记版本 0）
  - 下一步：补齐已知缺口后按验收方式复核：检查交付物中是否包含：候选证据表、接口文档与验证方法、UNKNOWN 缺口清单；确认无安装日志、无接口调用记录、无部署产物。。
  - 缺口：缺口清单需随新增来源持续更新
  - 缺口：未执行任何安装/调用/部署（符合要求）
  - 缺口：多数条件缺乏来源证据，需补充检索
  - 缺口：来源为部分摘录，无法据此确认完整证据链
  - 缺口：候选覆盖面不足，仅一个资源且仅含许可证声明
  - 缺口：需补充 LICENSE、版本、依赖与接口文档来源后重评
  - 缺口：多数条件仍缺来源证据，缺口清单需后续补充
  - 缺口：后续复核需在目标环境实测，本轮不执行
  - 缺口：后续需补充依赖级许可证核验与接口实测计划
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d）
  - 依据来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12）
  - 依据来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6）
  - 依据来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf）
  - 依据来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6）
  - 依据来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
- **PENDING**：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：抽查若干候选，确认其许可证、版本、依赖三项各自有独立状态标注，且存在部分 CONFIRMED、部分 UNKNOWN 的候选被如实呈现。。
  - 缺口：许可证证据状态：UNKNOWN
  - 缺口：版本证据状态：UNKNOWN
  - 缺口：依赖清单证据状态：UNKNOWN
  - 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
  - 缺口：版本证据缺失
  - 缺口：依赖清单证据缺失
  - 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
  - 缺口：版本与依赖清单均无来源证据
  - 缺口：版本证据状态：UNKNOWN（仅见 'v1' 状态描述，非版本号证据）
  - 缺口：依赖清单证据状态为 UNKNOWN（无 lockfile/依赖树）
  - 缺口：依赖清单证据不完整，无法逐项标注各依赖状态
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/package.json（exact source quote: evidence_c0544dfab30c444b）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json（exact source quote: evidence_32ca15e079504732）
  - 依据来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e）
  - 依据来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
  - 依据来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf）
- **PENDING**：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：检查证据表中每个候选是否附有许可证版本标识与依赖清单来源链接；缺失项标注为 UNKNOWN 而非留空。。
  - 缺口：需从仓库 LICENSE 获取 SPDX 标识
  - 缺口：需从 package.json 与 lockfile 获取依赖清单来源
  - 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
  - 缺口：未记录许可证版本号
  - 缺口：未记录依赖清单来源
  - 缺口：缺少 SPDX 标识
  - 缺口：缺少依赖清单来源（如 package.json / lockfile）
  - 缺口：需确认 SPDX 标识 Apache-2.0 及对应 LICENSE 文件
  - 缺口：需依赖清单来源（lockfile/SBOM 路径）
  - 缺口：待补：LICENSE 文件 URL 与 SPDX 标识
  - 缺口：待补：依赖清单文件 URL（如 package.json）
  - 缺口：未确认 SPDX 标识（MIT）是否来自 LICENSE 文件或仓库元数据
  - 缺口：缺少依赖清单来源（如 package.json 路径）
  - 缺口：依赖清单来源（lockfile/SBOM）缺失，保持 UNKNOWN
  - 缺口：依赖清单来源不完整，需 package-lock.json 或 SBOM
  - 依据来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6）
  - 依据来源：https://api.github.com/repos/destrynewiger/openagenticos（exact source quote: evidence_f64f221bbddc4287）
  - 依据来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e）
  - 依据来源：https://api.github.com/repos/wildware-uk/agent-dashboard（exact source quote: evidence_a31fe6f0c3e94210）
  - 依据来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf）
- **PENDING**：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。（依据状态：UNKNOWN；注记版本 0）
  - 下一步：按验收方式收集实际结果：检查文档中关于数据来源的表述是否带有 UNVERIFIED 标注，且无“已可用/已支持”等未经实测的断言。。
  - 缺口：未在目标环境实测数据来源可用性
  - 缺口：需验证 hooks/stream-json 摄取在目标环境的实际行为
  - 缺口：数据来源未记录
  - 缺口：目标环境未实测
  - 缺口：agents 表字段被截断，状态与活动字段定义不完整
  - 缺口：无实测验证记录
  - 缺口：缺少数据来源与采集方式说明
  - 缺口：缺少目标环境实测记录
  - 缺口：需官方 hooks 文档与本地验证脚本设计
  - 缺口：目标环境实测前保持未验证
  - 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
  - 缺口：缺少数据来源说明
  - 缺口：缺少目标环境实测计划
  - 缺口：各探针在目标环境的实际可用性未验证
  - 缺口：最近活动数据来源未在摘录中说明
  - 缺口：在线状态判定逻辑（last_seen_at/heartbeat）未实测
  - 缺口：未验证 SSE 在目标环境的连通性与事件完整性
  - 依据来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12）
  - 依据来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948）
  - 依据来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d）
  - 依据来源：https://github.com/darthnorse/agentmon/blob/main/README.md（Exa /contents full source text）
  - 依据来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8）
- **PENDING**：若采用 OpenAgenticOS：需自行实现 JSON 导出与响应式布局，其状态 API 字段与本地端口仅为文档描述，未实测（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：若采用 agent-dashboard：需按设计文档接入 SSE 事件流与 MCP 上报工具，端点契约需先取得完整官方文档（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：两者均需自建 Agent 状态/活动采集适配层，把各 Agent 探针输出映射为统一状态与最近活动模型（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：需建立依赖级许可证清单（lockfile/SBOM）与 NOTICE/版权声明保留流程，覆盖传递依赖（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：需设计目标环境验证脚本（本地端点探测、事件完整性断言、桌面/移动视口检查），本轮不执行（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：JSON 导出功能：全部候选均无原文证据，可能需新开发导出端点与字段定义（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：响应式界面：全部候选均无断点/视口证据，可能需新开发或改造前端布局（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：许可证逐项核验：需获取各候选 LICENSE 全文、SPDX 标识、版本标签与完整依赖清单（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：接口官方文档与验证方法：需补齐端点路径、方法、响应 schema 与可执行验证步骤（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：离线/无托管依赖证明：需确认是否存在必须联网的推送或托管服务依赖（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：许可证证据缺口：多数候选仅有标识声明，无条款原文，商用许可无法判定，保持 UNKNOWN（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：依赖级许可风险：即使仓库自身为 MIT/Apache-2.0，传递依赖（如原生模块、媒体库）许可未核验（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：接口未实测：状态与活动数据来源在目标环境的可用性、事件完整性均未验证（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：响应式与导出能力可能不存在，需新开发，工作量与可行性未评估（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：本地优先主张多为自述，缺少离线运行与存储架构的可核验证据（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：候选仓库星标极少、创建时间新，维护与长期可用性存在不确定性（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。
- **PENDING**：部分所选资源没有补充文档读取；许可、接口、部署和依赖缺口需人工核查。（依据状态：未评估；注记版本 0）
  - 下一步：由使用者明确负责人、完成条件和检查结果；此记录不会执行该工作。

清单状态和用户记录只表示准备进度，不证明条件已通过或任务已执行。

## 成立条件

- **[REQUIRED / FUNCTIONAL]** 仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。 (`cond_f4c55f6c443649e6`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户原始目标明确要求“本地优先”，且复核决定声明不放宽原目标条件，因此该条为必需。注意：这不等于禁止任何网络能力，而是要求离线/本地可用性不被打断。
  - 验收方式：在断网（或屏蔽外网）的本地环境中启动并操作仪表盘，确认 Agent 列表、在线状态与最近活动仍可读取与展示；记录断网场景下的功能清单与失败项。
- **[REQUIRED / QUALITY]** 仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。 (`cond_5295da7b02404be5`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户原始目标明确要求响应式网页，复核决定未放宽。具体断点数值与目标设备清单属未确认细节，不作为条件本身。
  - 验收方式：在至少一个桌面视口与一个移动视口（如 375px 宽）下加载页面，检查布局无横向溢出、关键信息（状态、最近活动）可见可读；记录截图与视口尺寸。
- **[REQUIRED / FUNCTIONAL]** 仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。 (`cond_80ecebf9f3b9477b`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户原始目标明确要求可导出 JSON，复核决定未放宽。导出字段集合、schema 版本与是否含历史区间属未确认细节，不并入本条。
  - 验收方式：在界面触发导出操作，获取生成的 JSON 文件，用 JSON 解析器校验其可解析，并核对其中包含 Agent 标识、状态与活动记录字段。
- **[REQUIRED / COMPLIANCE]** 对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。 (`cond_060b988e22c94ae2`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户补充约束明确要求逐项搜索许可证原文、版本与依赖清单，且来源无法证实则保持 UNKNOWN；复核决定重申许可证逐项核验不放宽。本条只要求证据与标注，不指定任何具体组件。
  - 验收方式：为每个候选建立证据表：许可证原文链接/文件路径、版本号、依赖清单来源；逐条标注 CONFIRMED 或 UNKNOWN，并复核 UNKNOWN 条目确实缺少可追溯来源。
- **[REQUIRED / COMPLIANCE]** 对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。 (`cond_efc01f5941044adb`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户补充约束要求优先考虑允许商业使用且条款可核验的组件；复核决定要求证据对照评估。注意：不额外引入用户未提出的许可证排除清单（如禁止某类许可证），仅做“是否允许商用 + 是否可核验”的判定。
  - 验收方式：对照许可证原文中关于商业使用/再分发/修改的条款逐条引用，形成“允许商用：是/否/UNKNOWN”的判定表，并附条款出处。
- **[REQUIRED / FUNCTIONAL]** 对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。 (`cond_1f60c0a1c05d4ce3`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户补充约束明确要求补充官方接口文档与验证方法，且未实测前始终标为未知/未验证；复核决定重申未实测接口标未知。本条不指定任何具体接口或技术栈。
  - 验收方式：为每个接口记录官方文档链接、版本/端点信息与验证步骤（如请求样例、预期响应字段、鉴权方式）；在目标环境执行前，状态字段保持 UNKNOWN/UNVERIFIED，并记录尚未执行的验证项。
- **[REQUIRED / OTHER]** 研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。 (`cond_dfa859532beb422b`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户明确要求仅研究并提出核验路径、不执行实施，且复核决定要求仅更新研究建议与缺口。本条约束研究交付物的形态与边界。
  - 验收方式：检查交付物中是否包含：候选证据表、接口文档与验证方法、UNKNOWN 缺口清单；确认无安装日志、无接口调用记录、无部署产物。
- **[OPTIONAL / COMPLIANCE]** 在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。 (`cond_fb6311c393e24947`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户要求“逐项搜索许可证原文、版本与依赖清单”，逐项报告是核验路径的合理细化；但用户未要求三者必须分列呈现，故列为可选增强，便于暴露部分证据缺失的情况。
  - 验收方式：抽查若干候选，确认其许可证、版本、依赖三项各自有独立状态标注，且存在部分 CONFIRMED、部分 UNKNOWN 的候选被如实呈现。
- **[OPTIONAL / COMPLIANCE]** 对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。 (`cond_e65405b0058442bd`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户补充约束提到“版本与依赖清单”，但未规定记录格式或必须使用 SPDX 标识；作为可选记录规范，避免把未确认的格式要求上升为必需条件。
  - 验收方式：检查证据表中每个候选是否附有许可证版本标识与依赖清单来源链接；缺失项标注为 UNKNOWN 而非留空。
- **[OPTIONAL / QUALITY]** 仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。 (`cond_f84c5df655c7446c`)
  - 确认来源：SYSTEM_ASSUMED
  - 依据：model-derived: 用户要求未实测接口标为未知，本条将其延伸到展示层的数据来源声明，属一致性增强；但用户未要求对展示层单独设条件，故为可选。
  - 验收方式：检查文档中关于数据来源的表述是否带有 UNVERIFIED 标注，且无“已可用/已支持”等未经实测的断言。

## 资源、许可与实际摘录

- **destrynewiger/OpenAgenticOS** — 许可：MIT
  - 来源：https://github.com/destrynewiger/OpenAgenticOS
  - # destrynewiger/OpenAgenticOS

Local-first agent operating dashboard with memory, agent tiles, council deliberation, and optional workflow examples.

- Stars: 4
- Forks: 0
- Watchers: 4
- Open issues: 0
- License: MIT License
- Default branch: main
- Created: 2026-06-15T23:23:05Z

## Languages

- CSS
- HTML
- JavaScript
- Shell

---

## README

# OpenAgenticOS

A local-first agent operating dashboard for memory, tool status, council deliberation, and optional GTM workflow examples.

It is built as a zero-dependency Node/SQLite app with a vanilla JavaScript dashboard. The app is designed to run on your machine, keep data local by default, and expose honest setup states for optional agent tools.

OpenAgenticOS dashboard preview

## What It Includes

- **Agent OS dashboard** with separate til
  - 补充文档（仓库与许可声明）：https://api.github.com/repos/destrynewiger/openagenticos；版本 main
  - 补充文档（许可原文）：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE；版本 e157333e051d1cfaeba6ec2746f62a72c0544421
  - 补充文档（接口与使用说明）：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md；版本 0cee2a224ab797d107aef0083864b6cd18183efa
  - 补充文档（运行依赖）：https://github.com/destrynewiger/OpenAgenticOS/blob/main/package.json；版本 9f9c6a64b9a9c090d1216e22cf4668128c1146e2
  - 匹配资料：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md；保存 2616 码点，实际提供 1888 码点；范围 [0, 550), [550, 1100), [1734, 2284), [2378, 2616)；读取于 2026-10-13T06:46:20.056493Z；版本 0cee2a224ab797d107aef0083864b6cd18183efa
    实际提供给模型的原文摘录：
    > # OpenAgenticOS
    >
    > OpenAgenticOS is a local dashboard for the agent tools on your computer. It checks which surfaces respond, stores private notes on disk, and gives you a four-angle review of an idea without calling a hosted model.
    >
    > The app ships with generic probes for Claude Code, Codex, Hermes, OpenClaw, and Ollama. Add or replace tools through a private config file. The browser cannot create probes or run commands.
    >
    > ## What you get
    >
    > - A status board for local agent commands and loopback HTTP services
    > - Owner-only local memory with add and de
    > [省略；以下为原文片段]
    > lete controls
    > - An offline council with Builder, Operator, Critic, and Memory lenses
    > - A loopback-only server with host and origin checks
    > - Zero runtime dependencies
    >
    > OpenAgenticOS does not discover your network, control remote machines, send messages, or sync data. Those capabilities belong in separate adapters with explicit security boundaries.
    >
    > ## Run it
    >
    > You need Node.js 22 or newer.
    >
    > ```bash
    > git clone https://github.com/destrynewiger/OpenAgenticOS.git
    > cd OpenAgenticOS
    > npm test
    > npm start
    > ```
    >
    > Open [http://127.0.0.1:4180](http://127.0.0.1:41
    > [省略；以下为原文片段]
    > ther users.
    >
    > ## Local data
    >
    > Notes live at `~/.local/share/openagenticos/state.json`. The directory uses mode `0700`; the file uses `0600`. Set `OPEN_AGENTIC_OS_STATE` to choose a different path.
    >
    > The status API returns labels, descriptions, states, and short results. It does not return configured commands, URLs, or command output.
    >
    > ## Develop
    >
    > ```bash
    > npm test
    > npm run dev
    > ```
    >
    > The project uses Node's built-in test runner and standard library. Start with a failing test for behavior changes.
    >
    > ## Project boundary
    >
    > This repository contains generic
    > [省略；以下为原文片段]
    > ata, and personal workflows in your private config or a private adapter repository.
    >
    > Read [SECURITY.md](SECURITY.md) before exposing the process through a proxy or changing the loopback boundary.
    >
    > ## License
    >
    > MIT. See [LICENSE](LICENSE).
    >
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
  - 匹配资料：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE；保存 1083 码点，实际提供 1083 码点；范围 [0, 1083)；读取于 2026-10-13T06:46:20.054250Z；版本 e157333e051d1cfaeba6ec2746f62a72c0544421
    实际提供给模型的原文摘录：
    > MIT License
    >
    > Copyright (c) 2026 OpenAgenticOS contributors
    >
    > Permission is hereby granted, free of charge, to any person obtaining a copy
    > of this software and associated documentation files (the "Software"), to deal
    > in the Software without restriction, including without limitation the rights
    > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    > copies of the Software, and to permit persons to whom the Software is
    > furnished to do so, subject to the following conditions:
    >
    > The above copyright notice and this permission notice shall be included in all
    > copies or substantial portions of the Software.
    >
    > THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    > IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    > FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    > AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    > LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    > OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    > SOFTWARE.
    >
  - 匹配资料：https://github.com/destrynewiger/OpenAgenticOS/blob/main/package.json；保存 347 码点，实际提供 347 码点；范围 [0, 347)；读取于 2026-10-13T06:46:20.058642Z；版本 9f9c6a64b9a9c090d1216e22cf4668128c1146e2
    实际提供给模型的原文摘录：
    > {
    >   "name": "openagenticos",
    >   "version": "0.2.0",
    >   "description": "Local-first dashboard for agent status, memory, and council deliberation.",
    >   "type": "module",
    >   "engines": {
    >     "node": ">=22"
    >   },
    >   "scripts": {
    >     "start": "node src/server.js",
    >     "dev": "node --watch src/server.js",
    >     "test": "node --test"
    >   },
    >   "license": "MIT"
    > }
    >
  - 匹配资料：https://api.github.com/repos/destrynewiger/openagenticos；保存 234 码点，实际提供 234 码点；范围 [0, 234)；读取于 2026-10-13T06:46:20.048099Z；版本 main
    实际提供给模型的原文摘录：
    > {"full_name": "destrynewiger/OpenAgenticOS", "default_branch": "main", "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT", "url": "https://api.github.com/licenses/mit", "node_id": "MDc6TGljZW5zZTEz"}, "archived": false}
  - 匹配资料：https://github.com/destrynewiger/OpenAgenticOS；保存 12 码点，实际提供 12 码点；范围 [0, 12)；读取于 2026-10-13T06:37:05.700212Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > License: MIT
  - 读取限制：未取得以下类别的可读根目录文件（缺失或超出读取限制），保持未核查：部署配置
- **Claude Code Agent Monitor - Real-Time Dashboard for Claude Code** — 许可：UNKNOWN
  - 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/
  - Claude Code Agent Monitor — Dashboard for Cursor & Codex

100% local · zero telemetry · real-time everything

# Real-time control plane for Claude Code, Cursor & Codex.

 A local-first dashboard that tracks Claude Code, Cursor, and Codex sessions, agents, conversations, tool calls, and model cost as they happen. Cursor monitoring is included with the Claude option and its history is snapshotted before the editor cleans it up.

 Real-time hooks ingestion Stream-json output Conversation mode One-shot headless Resume sessions MCP server (103 tools) Plugin marketplace VS Code extension WebSocket push SQLite (WAL) OpenAPI 3.0 ReDoc API reference Mermaid diagrams macOS & Windows desktop app Native OS toasts Hooks fan-out Tray live snapshot ⌘Q confirmation Auto-port discovery Discovery file CI
  - 匹配资料：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/；保存 11998 码点，实际提供 2200 码点；范围 [0, 550), [6554, 7104), [8833, 9383), [9513, 10063)；读取于 2026-10-13T06:37:09.618990Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > Claude Code Agent Monitor — Dashboard for Cursor & Codex
    >
    > 100% local · zero telemetry · real-time everything
    >
    > # Real-time control plane for Claude Code, Cursor & Codex.
    >
    >  A local-first dashboard that tracks Claude Code, Cursor, and Codex sessions, agents, conversations, tool calls, and model cost as they happen. Cursor monitoring is included with the Claude option and its history is snapshotted before the editor cleans it up.
    >
    >  Real-time hooks ingestion Stream-json output Conversation mode One-shot headless Resume sessions MCP server (103 too
    > [省略；以下为原文片段]
    > s
    >
    >  Explore orchestration DAGs, tool-flow Sankeys, collaboration networks, timelines, and scatter plots with hoverable, localized detail.
    >
    > ### Rules-based alerts
    >
    >  Detect error bursts, stuck agents, idle sessions, and token thresholds directly from the live event stream as it arrives.
    >
    > ### Alert triage
    >
    >  Per-rule, session, and agent cooldowns avoid duplicate noise. Acknowledge from the feed and jump to the session that triggered it.
    >
    > ### Universal webhooks
    >
    >  Route fired alerts to 14 first-class providers or any generic endpoint, each with it
    > [省略；以下为原文片段]
    >  Vietnamese, Korean, and Spanish cover charts, Settings, workflows, Agent Config, and Run Agent end to end.
    >
    > ### Kanban board
    >
    >  Switch between agents and sessions across Working, Waiting, Completed, Error, and Abandoned lanes with key metadata in view.
    >
    > ### Accurate idle state
    >
    >  A watchdog reconciles cancelled turns that emit no hook, so cards never stay falsely busy. Waiting badges explain the reason.
    >
    > ### API documentation
    >
    >  Browse the OpenAPI reference in interactive Swagger at `/api/docs` or readable ReDoc at `/api/redoc` — fully offline
    > [省略；以下为原文片段]
    > IX you install locally.
    >
    > ### Native desktop apps
    >
    >  Run the full dashboard as a macOS `.app` or a Windows `.exe`, with the Express server embedded in-process.
    >
    > ### Tray-first monitoring
    >
    >  Get a live status snapshot from the tray, start at login, and install hooks on first boot without changing your CLI workflow.
    >
    > ### Live activity feed
    >
    >  Pause and resume the streaming log, filter by event dimensions, expand raw payloads, and open the session behind any row.
    >
    > ### History import
    >
    >  Rescan Claude Code, Cursor, or Codex history. Manual provider i
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
- **docs/superpowers/specs/2026-08-25-agent-dashboard-design.md** — 许可：MIT
  - 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
  - # docs/superpowers/specs/2026-08-25-agent-dashboard-design.md

- Branch: main
- Repository: wildware-uk/agent-dashboard

---

# Agent Dashboard — Design

**Date:** 2026-08-25
**Status:** Approved
**Repo:** `wildware-uk/agent-dashboard` (public, MIT)

## 1. Overview

A self-hosted dashboard where AI coding agents report what they are doing, and their
owner watches and steers in real time.

Agents connect over MCP (remote Streamable HTTP) to create projects, post status
updates with images and video, claim tasks, read messages, and block on human
approval. The owner watches a live feed in a browser, manages projects, assigns
tasks, replies to agents, and answers approval requests.

The product is a single Node process plus SQLite plus a data directory. It is
released publicly for others to s
  - 补充文档（仓库与许可声明）：https://api.github.com/repos/wildware-uk/agent-dashboard；版本 main
  - 补充文档（许可原文）：https://github.com/wildware-uk/agent-dashboard/blob/main/LICENSE；版本 cd4571b5099be49adca8353ff11330b8f59add4a
  - 补充文档（接口与使用说明）：https://github.com/wildware-uk/agent-dashboard/blob/main/README.md；版本 2f169b30d446bf7cd0fc97fc158d688ce8aecc80
  - 补充文档（运行依赖）：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json；版本 d80ea9fddbc39cfd8a9ac2abc205a0fe300a44d6
  - 补充文档（部署配置）：https://github.com/wildware-uk/agent-dashboard/blob/main/Dockerfile；版本 c28957c4e31712a554efe8d27ccd8e50987a2120
  - 匹配资料：https://github.com/wildware-uk/agent-dashboard/blob/main/README.md；保存 12000 码点，实际提供 2086 码点；范围 [0, 550), [550, 1100), [2246, 2796), [11564, 12000)；读取于 2026-10-13T06:46:26.106115Z；版本 2f169b30d446bf7cd0fc97fc158d688ce8aecc80
    实际提供给模型的原文摘录：
    > # Agent Dashboard
    >
    > A self-hosted dashboard where AI coding agents report what they are doing, and
    > you watch and steer in real time.
    >
    > Agents connect over **MCP** (remote Streamable HTTP — no local install) to create
    > projects, post status updates with images and video, claim tasks, read your
    > replies, and stop to ask you a question. You watch a live feed in the browser
    > that updates without a refresh.
    >
    > ## What it does
    >
    > - **Rich status updates** — markdown, images, and video, posted by agents as they work.
    > - **Projects** — agents create them; you re
    > [省略；以下为原文片段]
    > name, pin, and archive them.
    > - **Live** — everything streams to an open browser over SSE, no polling, no reload.
    > - **Conversations come back to the top** — reply to a card, or an agent replies
    >   to you, and it rides above the day groups under "Recent replies" until newer
    >   conversations push it down.
    > - **Presence** — see which agents are alive right now.
    > - **Control plane** — assign tasks to agents, reply to them, and answer the
    >   questions they stop on: free text, a yes/no, one action out of several, one
    >   option from a list, several, or a **f
    > [省略；以下为原文片段]
    > beside the feed, because the feed is what
    >   happened and the board is what is being worked on. Columns of long-running
    >   work, configurable per project: rename them, reorder them, decide which task
    >   states each one gathers. Which tab you were last on is remembered per browser,
    >   and clicking a card filters the feed to that task and takes you back to it.
    >   Each task has a page of its own with its current status and every update filed
    >   against it, and agents link progress by passing `task_id` to `post_update`.
    > - **Pictures both ways** — drop, p
    > [省略；以下为原文片段]
    >   |
    > | `vapid-keys`                           | Generates a Web Push keypair. Paste both lines into `.env`.   |
    > | `backup <destination.db>`              | Online backup of the database, safe against a running server. |
    >
    > Outside Docker the same commands are `node build/cli.js <command>` after
    > `npm run build`, which produces the server, the CLI and the channel bridge
    > together. `npm run build:app` is the server alone, and it _empties_ `
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
  - 匹配资料：https://github.com/wildware-uk/agent-dashboard/blob/main/Dockerfile；保存 4116 码点，实际提供 2200 码点；范围 [0, 550), [596, 1146), [2434, 2984), [3309, 3859)；读取于 2026-10-13T06:46:26.113039Z；版本 c28957c4e31712a554efe8d27ccd8e50987a2120
    实际提供给模型的原文摘录：
    > # Agent Dashboard (design §10).
    > #
    > # One process, one SQLite file, one data directory. Nothing external, so the
    > # image is the whole product and the only state is the volume mounted at /data.
    > #
    > # Build stage compiles what needs compiling; the runtime stage keeps only
    > # production dependencies, the built server, the built CLI, and ffmpeg.
    >
    > # ── build ─────────────────────────────────────────────────────────────────────
    > FROM node:22-slim AS build
    >
    > # better-sqlite3, argon2 and sharp all ship prebuilt binaries for glibc x64/arm64
    > # and fall back to
    > [省略；以下为原文片段]
    > d for the
    > # platform. The toolchain is here so that fallback works instead of failing the
    > # build on a machine we did not anticipate; it is left behind in this stage.
    > RUN apt-get update \
    > 	&& apt-get install -y --no-install-recommends ca-certificates python3 make g++ \
    > 	&& rm -rf /var/lib/apt/lists/*
    >
    > WORKDIR /app
    >
    > # devDependencies include Playwright, whose install script would otherwise pull a
    > # browser bundle into a layer that only ever runs `vite build`.
    > ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
    >
    > COPY package.json package-lock.json ./
    > RUN npm
    > [省略；以下为原文片段]
    > ith the
    > # variable named rather than booting insecure.
    > ENV DATA_DIR=/data
    > # adapter-node rejects bodies over this *before* any route runs, and its own
    > # default of 512K would 413 every upload with an error the app never sees. Must
    > # stay >= MAX_VIDEO_BYTES; startup refuses if it is smaller.
    > ENV BODY_SIZE_LIMIT=209715200
    >
    > COPY --from=build /app/node_modules ./node_modules
    > COPY --from=build /app/build ./build
    > COPY --from=build /app/package.json ./package.json
    >
    > # `mint-token <name>` as an actual command, because that is what the README tells
    > # a s
    > [省略；以下为原文片段]
    > /app/build/cli.js hash-password "$@"\n' > /usr/local/bin/hash-password \
    > 	&& chmod +x /usr/local/bin/agent-dashboard /usr/local/bin/mint-token /usr/local/bin/hash-password
    >
    > # The volume is created by Docker on first run and must be writable by the
    > # process, which is not root.
    > RUN mkdir -p /data && chown node:node /data
    > USER node
    >
    > EXPOSE 8010
    > VOLUME ["/data"]
    >
    > # The login page renders without a session and without a database, so it answers
    > # even on a deployment that is not configured yet — which is what a health check
    > # should report on: the p
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
  - 匹配资料：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json；保存 2699 码点，实际提供 1353 码点；范围 [0, 550), [550, 1100), [2446, 2699)；读取于 2026-10-13T06:46:26.109831Z；版本 d80ea9fddbc39cfd8a9ac2abc205a0fe300a44d6
    实际提供给模型的原文摘录：
    > {
    > 	"name": "agent-dashboard",
    > 	"private": true,
    > 	"version": "0.0.1",
    > 	"type": "module",
    > 	"scripts": {
    > 		"dev": "vite dev",
    > 		"build:app": "vite build",
    > 		"build": "npm run build:app && npm run build:cli && npm run build:channel",
    > 		"build:cli": "vite build --config vite.cli.config.ts",
    > 		"build:channel": "vite build --config vite.channel.config.ts && vite build --config vite.monitor.config.ts",
    > 		"build:all": "npm run build",
    > 		"build:plugin": "vite build --config vite.plugin.config.ts && vite build --config vite.plugin-monitor.config.ts",
    > 		"p
    > [省略；以下为原文片段]
    > review": "vite preview",
    > 		"start": "node build",
    > 		"prepare": "svelte-kit sync || echo \"\"",
    > 		"typecheck": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json",
    > 		"typecheck:watch": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --watch",
    > 		"check": "npm run typecheck",
    > 		"lint": "prettier --check . && eslint .",
    > 		"format": "prettier --write .",
    > 		"test": "vitest run --project=unit",
    > 		"test:watch": "vitest --project=unit",
    > 		"test:component": "vitest run --project=component",
    > 		"test:e2e": "playwright test --pass-with-
    > [省略；以下为原文片段]
    > 4.19.2",
    > 		"sharp": "^0.35.3",
    > 		"ulid": "^3.0.2",
    > 		"web-push": "^3.6.7",
    > 		"zod": "^4.4.3"
    > 	},
    > 	"description": "Self-hosted dashboard where AI coding agents report what they are doing over MCP.",
    > 	"license": "MIT",
    > 	"engines": {
    > 		"node": ">=22"
    > 	}
    > }
    >
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
  - 匹配资料：https://github.com/wildware-uk/agent-dashboard/blob/main/LICENSE；保存 1065 码点，实际提供 1065 码点；范围 [0, 1065)；读取于 2026-10-13T06:46:26.102281Z；版本 cd4571b5099be49adca8353ff11330b8f59add4a
    实际提供给模型的原文摘录：
    > MIT License
    >
    > Copyright (c) 2026 Wildware
    >
    > Permission is hereby granted, free of charge, to any person obtaining a copy
    > of this software and associated documentation files (the "Software"), to deal
    > in the Software without restriction, including without limitation the rights
    > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    > copies of the Software, and to permit persons to whom the Software is
    > furnished to do so, subject to the following conditions:
    >
    > The above copyright notice and this permission notice shall be included in all
    > copies or substantial portions of the Software.
    >
    > THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    > IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    > FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    > AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    > LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    > OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    > SOFTWARE.
    >
  - 匹配资料：https://api.github.com/repos/wildware-uk/agent-dashboard；保存 234 码点，实际提供 234 码点；范围 [0, 234)；读取于 2026-10-13T06:46:26.097377Z；版本 main
    实际提供给模型的原文摘录：
    > {"full_name": "wildware-uk/agent-dashboard", "default_branch": "main", "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT", "url": "https://api.github.com/licenses/mit", "node_id": "MDc6TGljZW5zZTEz"}, "archived": false}
  - 匹配资料：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md；保存 12000 码点，实际提供 2200 码点；范围 [0, 550), [550, 1100), [5117, 5667), [6695, 7245)；读取于 2026-10-13T06:37:14.889993Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > # docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
    >
    > - Branch: main
    > - Repository: wildware-uk/agent-dashboard
    >
    > ---
    >
    > # Agent Dashboard — Design
    >
    > **Date:** 2026-08-25
    > **Status:** Approved
    > **Repo:** `wildware-uk/agent-dashboard` (public, MIT)
    >
    > ## 1. Overview
    >
    > A self-hosted dashboard where AI coding agents report what they are doing, and their
    > owner watches and steers in real time.
    >
    > Agents connect over MCP (remote Streamable HTTP) to create projects, post status
    > updates with images and video, claim tasks, read messages, and block on human
    > [省略；以下为原文片段]
    >
    > approval. The owner watches a live feed in a browser, manages projects, assigns
    > tasks, replies to agents, and answers approval requests.
    >
    > The product is a single Node process plus SQLite plus a data directory. It is
    > released publicly for others to self-host.
    >
    > ### Goals
    >
    > - Agents post rich status updates (markdown + images + video) with no local install.
    > - Owner sees everything live, with no page refresh.
    > - Owner can steer: assign tasks, reply to agents, gate agent work behind approval.
    > - One-command self-host: Docker image, env-var config, no
    > [省略；以下为原文片段]
    >           created_at, updated_at
    > agents          id, name, token_hash, created_at, revoked_at, last_seen_at
    > sessions        id, agent_id, started_at, last_heartbeat_at, ended_at,
    >                 meta(json: host, cwd, model)
    > updates         id, project_id, agent_id, session_id?, title?, body(md),
    >                 level(info|success|warn|error), pinned, created_at, deleted_at?
    > media           id, agent_id, update_id?, kind(image|video), mime, bytes, sha256,
    >                 width?, height?, duration_ms?, status(pending|ready|failed),
    >
    > [省略；以下为原文片段]
    > man` or `agent:<agent_id>`.
    > - Unread state per agent lives in `read_cursors`, not as a flag on `messages`,
    >  so adding a second reader never requires a schema change.
    >
    > ## 4. Real-time transport
    >
    > `GET /api/stream` is a single SSE endpoint carrying every event type as JSON, each
    > with an `id:` set to the global event sequence number.
    >
    > Event types: `project.created`, `project.updated`, `update.created`,
    > `update.deleted`, `media.ready`, `task.created`, `task.updated`,
    > `message.created`, `approval.created`, `approval.decided`, `agent.presence`.
    >
    > **Rec
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
  - 读取限制：README.md 仅保存前 12000 字符，后文未用于匹配判断。
- **brunokktro/agent-dashboard** — 许可：MIT
  - 来源：https://github.com/brunokktro/agent-dashboard
  - # brunokktro/agent-dashboard

Local-first observability dashboard for AI agent ecosystems (Kiro CLI, Claude Code) - real-time runs, queue kanban, health heatmaps, multi-terminal console with agent piping

- Stars: 2
- Forks: 0
- Watchers: 2
- Open issues: 0
- License: MIT License
- Default branch: main
- Created: 2026-08-07T20:53:58Z

## Languages

- CSS
- HTML
- Python
- Shell
- TypeScript

## Top Contributors

- brunokktro (40 contributions)

---

## README

# Agent Dashboard

**Local-first observability for AI agent ecosystems.** Built for Kiro CLI agents, adaptable to anything that can record a run - cron jobs, launchd services, Claude Code hooks.

Watch your agents live: what ran, what failed and *why*, what's queued, when everything happens - plus a multi-terminal console to chat wit
  - 匹配资料：https://github.com/brunokktro/agent-dashboard；保存 12 码点，实际提供 12 码点；范围 [0, 12)；读取于 2026-10-13T06:37:18.745330Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > License: MIT
- **docs/ARCHITECTURE.md** — 许可：UNKNOWN
  - 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md
  - # docs/ARCHITECTURE.md

- Branch: main
- Repository: keshrath/agent-comm

---

# Architecture

## Source structure

```
src/
├── types.ts              # Shared types, error hierarchy (CommError → NotFound/Conflict/Validation)
├── context.ts            # DI root — creates and wires all services, no global state
├── package-meta.ts       # Reads name/version from package.json (MCP initialize, WebSocket state)
├── index.ts              # MCP entry point (stdio JSON-RPC) + dashboard auto-start
├── server.ts             # HTTP + WebSocket server (standalone or embedded)
├── storage/
│   └── database.ts       # SQLite wrapper: WAL mode, versioned migrations, parameterized queries
├── domain/
│   ├── agents.ts         # Registration, presence, skill discovery, heartbeat reaper, stuck detection
│
  - 匹配资料：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md；保存 6887 码点，实际提供 1907 码点；范围 [0, 550), [1653, 2203), [3180, 3730), [6630, 6887)；读取于 2026-10-13T06:38:36.837423Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > # docs/ARCHITECTURE.md
    >
    > - Branch: main
    > - Repository: keshrath/agent-comm
    >
    > ---
    >
    > # Architecture
    >
    > ## Source structure
    >
    > ```
    > src/
    > ├── types.ts              # Shared types, error hierarchy (CommError → NotFound/Conflict/Validation)
    > ├── context.ts            # DI root — creates and wires all services, no global state
    > ├── package-meta.ts       # Reads name/version from package.json (MCP initialize, WebSocket state)
    > ├── index.ts              # MCP entry point (stdio JSON-RPC) + dashboard auto-start
    > ├── server.ts             # HTTP + WebSocket server (st
    > [省略；以下为原文片段]
    >          # WebSocket: real-time push, ping/pong, event filtering
    > └── ui/
    >     ├── index.html        # Dashboard SPA (ARIA, keyboard nav, Material Symbols)
    >     ├── styles.css        # Light/dark theme, responsive layout, prose markdown styles
    >     └── app.js            # Client: WebSocket, diff-aware rendering, markdown (marked + DOMPurify)
    > ```
    >
    > ## Design principles
    >
    > - **No global state** — everything flows through `AppContext` (dependency injection)
    > - **Domain-driven** — business logic in `domain/`, transports are thin adapters
    > - **3 runtime deps
    > [省略；以下为原文片段]
    > es `comm_inbox` as step 5 of the mandatory startup sequence
    > - Agents can call `comm_inbox` at the start of each task
    > - For time-critical coordination, use `comm_state({ action: "cas", ... })` (shared state with CAS) which agents can check synchronously
    >
    > ## Database
    >
    > SQLite with WAL mode at `~/.agent-comm/agent-comm.db`. Schema is versioned with automatic migrations.
    >
    > ```mermaid
    > erDiagram
    >     agents {
    >         text id PK
    >         text name UK
    >         text capabilities
    >         text skills
    >         text metadata
    >         text status
    >         text statu
    > [省略；以下为原文片段]
    > MCP | 34 | All 7 tools, auth gates, rate limiting, input validation |
    > | Integration: Workflows | 10 | Multi-agent scenarios (coordination, CAS locking, forwarding, search) |
    > | E2E: Server | 21 | REST endpoints, WebSocket state/events, export, error codes |
    >
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
- **sgentzen/vibe-dash** — 许可：Apache License 2.0
  - 来源：https://github.com/sgentzen/vibe-dash
  - # Repository: sgentzen/vibe-dash

Local-first real-time dashboard for monitoring AI-driven development projects via MCP

- Stars: 0
- Forks: 0
- Watchers: 0
- Open issues: 0
- Primary language: TypeScript
- Languages: TypeScript (97.1%), JavaScript (1.5%), CSS (0.7%), Shell (0.4%), Dockerfile (0.2%), HTML
- License: Apache License 2.0 (Apache-2.0)
- Topics: ai-agents, dashboard, developer-tools, mcp, model-context-protocol, react, ta[REDACTED], typescript
- Default branch: main
- Homepage: https://github.com/sgentzen/vibe-dash
- Created: 2026-03-31T05:51:42Z
- Last push: 2026-06-25T03:19:52Z
- Contributors: 2 (top: sgentzen, dependabot[bot])

---

# Vibe Dash

**The open-source project layer for AI-driven development.**

Connect your AI coding agents — Claude Code, Cursor, Codex, Copilot,
  - 匹配资料：https://github.com/sgentzen/vibe-dash；保存 27 码点，实际提供 27 码点；范围 [0, 27)；读取于 2026-10-13T06:38:42.135541Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > License: Apache License 2.0
- **README.md** — 许可：UNKNOWN
  - 来源：https://github.com/darthnorse/agentmon/blob/main/README.md
  - # README.md

- Branch: main
- Repository: darthnorse/agentmon

---

# AgentMon

**A multi-server, mobile-first dashboard for supervising AI coding agents.**

AgentMon shows the live terminal sessions from every one of your development servers in one place, surfaces
the ones that need you (an agent waiting for input or approval) first, and lets you jump into any of them —
from your desktop or your phone — to answer, approve, or course-correct. When a session you're *not* looking
at gets blocked, AgentMon tells you: an in-app toast and sound, or a push notification when your phone is
asleep.

It's built for the common reality of running several Claude Code or Codex sessions across several boxes:
status *is* navigation, and the thing you most need is "which agent needs me, and let me get to i
  - 匹配资料：https://github.com/darthnorse/agentmon/blob/main/README.md；保存 12000 码点，实际提供 2200 码点；范围 [0, 550), [550, 1100), [1121, 1671), [1691, 2241)；读取于 2026-10-13T06:38:46.515481Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > # README.md
    >
    > - Branch: main
    > - Repository: darthnorse/agentmon
    >
    > ---
    >
    > # AgentMon
    >
    > **A multi-server, mobile-first dashboard for supervising AI coding agents.**
    >
    > AgentMon shows the live terminal sessions from every one of your development servers in one place, surfaces
    > the ones that need you (an agent waiting for input or approval) first, and lets you jump into any of them —
    > from your desktop or your phone — to answer, approve, or course-correct. When a session you're *not* looking
    > at gets blocked, AgentMon tells you: an in-app toast and sound, or
    > [省略；以下为原文片段]
    > a push notification when your phone is
    > asleep.
    >
    > It's built for the common reality of running several Claude Code or Codex sessions across several boxes:
    > status *is* navigation, and the thing you most need is "which agent needs me, and let me get to it now."
    >
    > > **Status:** v1. Single-operator by design (each operator runs their own hub). LAN / private-network use —
    > > not built for public internet exposure. See Security & network posture.
    >
    > ---
    >
    > ## Contents
    >
    > - Features
    > - How it works
    > - Requirements
    > - Quick start — stand up the hub and enrol agents
    > [省略；以下为原文片段]
    > rence
    > - Using AgentMon — watch and drive live sessions
    > - Orchestration — running epics end to end — let it plan / implement / PR issues for you
    > - Updating
    > - Security & network posture
    > - Development
    > - License
    >
    > ---
    >
    > ## Features
    >
    > - **One hub, many servers.** A single browser/PWA UI aggregates `tmux` sessions from any number of servers,
    >  each running a lightweight agent. Agents are never browser-reachable — the hub is the only user-facing
    >  surface and the single authorization point.
    > - **Real terminals, real persistence.** Sessions are `tmux` sessio
    > [省略；以下为原文片段]
    > eep running when you
    >  close the tab, your phone sleeps, the hub restarts, or you SSH in directly. Full scrollback, touch
    >  scrolling, and a mobile key bar (Esc / Ctrl / Tab / arrows / paste).
    > - **Live state, blocked-first.** Claude Code and Codex hooks drive per-session state — `blocked` / `done` / `working`
    >  / `idle` — shown as colored dots per session, with blocked sessions (and the hosts holding them) always
    >  floated to the top. "Next blocked" jumps you to the next one. Each session is tagged `claude` / `codex`
    >  so you can tell at a glance wh
    说明：这是所选片段，不能据此判断整份资料不存在某项能力。
- **chuckplayer/claude-agent-dashboard** — 许可：MIT
  - 来源：https://github.com/chuckplayer/claude-agent-dashboard
  - # chuckplayer/claude-agent-dashboard

Localhost dashboard for Claude Code sessions with real-time agent activity monitoring and a persistent memory browser across projects.

- Stars: 2
- Forks: 0
- Watchers: 2
- Open issues: 0
- License: MIT License
- Default branch: main
- Created: 2026-03-05T20:48:17Z

## Languages

- CSS
- HTML
- JavaScript
- PowerShell
- Shell
- TypeScript
- Vue

## Topics

- ai-agents
- anthropic
- claude-code
- dashboard
- developer-tools
- nodejs
- session-monitoring
- sqllite
- typescipt
- websocket

## Top Contributors

- chuckplayer (64 contributions)

---

## README

# Claude Agent Dashboard

A real-time monitoring dashboard for Claude Code sessions. Watch agent activity as it happens, browse persistent memory files across projects, and review session history —
  - 匹配资料：https://github.com/chuckplayer/claude-agent-dashboard；保存 12 码点，实际提供 12 码点；范围 [0, 12)；读取于 2026-10-13T06:38:50.480780Z；版本 UNKNOWN
    实际提供给模型的原文摘录：
    > License: MIT

## 条件匹配与证据

### SUPPORTED：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
来源自述本地优先、零遥测；但仅为其自述，未在目标环境实测。
- 缺口：未提供离线运行/无托管依赖的架构或部署证据
- 缺口：未在目标环境实测
- 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12；读取于 2026-10-13T06:37:09.618990Z）
  > 100% local · zero telemetry · real-time everything

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
所给片段未出现响应式/移动端视口相关表述，无法判定。
- 缺口：缺少响应式布局或移动端适配的原文证据
- 缺口：缺少桌面/移动视口实测记录

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
片段提到 stream-json 输出与 OpenAPI 文档，但无 JSON 文件导出功能证据。
- 缺口：缺少 JSON 导出功能的原文证据
- 缺口：stream-json 为输出格式，不等同于导出 JSON 文件

### UNKNOWN：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
来源 license 字段为 UNKNOWN，片段无许可证原文、版本号或依赖清单。
- 缺口：无许可证原文
- 缺口：无版本号
- 缺口：无依赖清单
- 缺口：需查仓库 LICENSE 文件与 package.json/lockfile
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12；读取于 2026-10-13T06:37:09.618990Z）
  > 100% local · zero telemetry · real-time everything

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
无许可证标识或条款原文，无法判定商用许可，按规则保持 UNKNOWN。
- 缺口：缺少许可证标识与条款原文
- 缺口：需核验 LICENSE 全文及商用授权范围

### PARTIAL：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
有官方 OpenAPI/Swagger/ReDoc 文档线索，但无验证方法且未实测，可用性仍未知。
- 缺口：未给出可执行验证步骤（如 curl 示例、期望响应）
- 缺口：未在目标环境实测，接口可用性保持未知/未验证
- 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12；读取于 2026-10-13T06:37:09.618990Z）
  > Browse the OpenAPI reference in interactive Swagger at `/api/docs` or readable ReDoc at `/api/redoc` — fully offline

### SUPPORTED：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
本次仅做证据对照与缺口清单，未执行安装、调用或部署。
- 缺口：缺口清单需随新增来源持续更新
- 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12；读取于 2026-10-13T06:37:09.618990Z）
  > 100% local · zero telemetry · real-time everything

### UNKNOWN：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
三项证据均缺失：许可证 UNKNOWN、版本 UNKNOWN、依赖清单 UNKNOWN，无法分别举证。
- 缺口：许可证证据状态：UNKNOWN
- 缺口：版本证据状态：UNKNOWN
- 缺口：依赖清单证据状态：UNKNOWN
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN

### UNKNOWN：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
无 SPDX 标识、无许可证版本、无依赖清单来源可记录。
- 缺口：需从仓库 LICENSE 获取 SPDX 标识
- 缺口：需从 package.json 与 lockfile 获取依赖清单来源
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN

### PARTIAL：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：Claude Code Agent Monitor - Real-Time Dashboard for Claude Code
来源宣称实时追踪会话与活动，但未实测，仅记为待验证假设。
- 缺口：未在目标环境实测数据来源可用性
- 缺口：需验证 hooks/stream-json 摄取在目标环境的实际行为
- 来源：https://hoangsonww.github.io/Claude-Code-Agent-Monitor/（exact source quote: evidence_0f7ec8b76b9c4e12；读取于 2026-10-13T06:37:09.618990Z）
  > A local-first dashboard that tracks Claude Code, Cursor, and Codex sessions, agents, conversations, tool calls, and model cost as they happen.

### UNKNOWN：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：brunokktro/agent-dashboard
唯一来源仅含许可证声明，未提供任何本地优先运行或存储架构证据。
- 缺口：无架构/存储/离线运行文档证据
- 缺口：无依赖清单以判断是否需联网托管服务

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：brunokktro/agent-dashboard
来源未包含任何响应式布局或视口适配证据。
- 缺口：无前端框架/样式或响应式设计证据
- 缺口：无桌面与移动端渲染验证记录

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：brunokktro/agent-dashboard
来源未提及任何 JSON 导出功能。
- 缺口：无导出功能代码或文档证据

### PARTIAL：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：brunokktro/agent-dashboard
仅有许可证标识声明；无许可证原文全文、无版本号、无依赖清单。
- 缺口：缺少 MIT 许可证原文全文（仅标识）
- 缺口：缺少版本号/发布标签证据
- 缺口：缺少依赖清单（如 package.json/lockfile）证据
- 来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf；读取于 2026-10-13T06:37:18.745330Z）
  > License: MIT

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：brunokktro/agent-dashboard
仅有“License: MIT”标识，未提供可引用的许可条款原文，无法核验商用授权。
- 缺口：需获取 LICENSE 文件原文以引用授权条款
- 缺口：需确认许可证适用范围（代码/文档/资产）

### UNKNOWN：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：brunokktro/agent-dashboard
来源未包含任何 Agent 状态/活动接口的官方文档或验证方法。
- 缺口：无接口文档链接
- 缺口：无验证方法（如请求样例、schema、健康检查）
- 缺口：目标环境未实测，保持未验证

### PARTIAL：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：brunokktro/agent-dashboard
已产出证据对照与缺口清单；仅许可证标识一项有来源证据，其余均为 UNKNOWN。
- 缺口：未执行任何安装/调用/部署（符合要求）
- 缺口：多数条件缺乏来源证据，需补充检索
- 来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf；读取于 2026-10-13T06:37:18.745330Z）
  > License: MIT

### PARTIAL：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：brunokktro/agent-dashboard
许可证证据=仅标识（PARTIAL）；版本证据=UNKNOWN；依赖清单证据=UNKNOWN，三者已分列。
- 缺口：版本证据缺失
- 缺口：依赖清单证据缺失
- 来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf；读取于 2026-10-13T06:37:18.745330Z）
  > License: MIT

### PARTIAL：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：brunokktro/agent-dashboard
记录了 SPDX 标识 MIT，但未记录许可证版本号，也无依赖清单来源。
- 缺口：未记录许可证版本号
- 缺口：未记录依赖清单来源
- 来源：https://github.com/brunokktro/agent-dashboard（exact source quote: evidence_10f40dd3060148bf；读取于 2026-10-13T06:37:18.745330Z）
  > License: MIT

### UNKNOWN：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：brunokktro/agent-dashboard
来源未描述数据来源；按约束记为待验证假设，不宣称可用。
- 缺口：数据来源未记录
- 缺口：目标环境未实测

### PARTIAL：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：docs/ARCHITECTURE.md
证据显示本地 SQLite 存储与本地 HTTP/WS 服务，但片段不完整，未证实无联网托管依赖。
- 缺口：片段被省略，无法确认是否存在必须联网的托管服务依赖
- 缺口：未提供部署/运行前置条件清单
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > SQLite with WAL mode at `~/.agent-comm/agent-comm.db`. Schema is versioned with automatic migrations.

### PARTIAL：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：docs/ARCHITECTURE.md
有响应式布局与 SPA 描述，但无桌面/移动视口实测证据，未验证。
- 缺口：无移动端视口实测或断点说明
- 缺口：未证实状态与活动在移动端可正常查看
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > styles.css        # Light/dark theme, responsive layout, prose markdown styles

### PARTIAL：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：docs/ARCHITECTURE.md
测试清单提及 export，但未说明 JSON 格式与导出内容范围，未实测。
- 缺口：未证实导出格式为 JSON
- 缺口：未证实导出覆盖状态与最近活动字段
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > E2E: Server | 21 | REST endpoints, WebSocket state/events, export, error codes |

### UNKNOWN：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：docs/ARCHITECTURE.md
该来源 license 字段为 UNKNOWN，无许可证原文、无版本号、无依赖清单。
- 缺口：无许可证原文
- 缺口：无版本号
- 缺口：无依赖清单（仅称 3 runtime deps，未列名）
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > 3 runtime deps

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：docs/ARCHITECTURE.md
来源无任何许可证条款文本，无法判定商业使用许可，保持 UNKNOWN。
- 缺口：缺少许可证原文与 SPDX 标识
- 缺口：缺少商用条款依据

### PARTIAL：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：docs/ARCHITECTURE.md
提及 REST/WebSocket 状态与事件接口及 MCP 工具，但无接口契约细节，可用性未验证。
- 缺口：无端点/字段级接口文档
- 缺口：无官方验证方法或示例请求
- 缺口：目标环境未实测，可用性保持未知
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > WebSocket: real-time push, ping/pong, event filtering

### PARTIAL：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：docs/ARCHITECTURE.md
本评估仅做证据对照并列出缺口，未执行安装/调用/部署；但来源为部分片段，证据充分性有限。
- 缺口：来源为部分摘录，无法据此确认完整证据链
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > Branch: main

### UNKNOWN：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：docs/ARCHITECTURE.md
三项证据均缺失：许可证 UNKNOWN、版本未给出、依赖清单未列出。
- 缺口：许可证证据状态：UNKNOWN
- 缺口：版本证据状态：UNKNOWN
- 缺口：依赖清单证据状态：UNKNOWN
- 缺口：未确认资源许可；不能据此认定可商用或符合开源约束
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > 3 runtime deps

### UNKNOWN：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：docs/ARCHITECTURE.md
无 SPDX 标识、无许可证版本、无依赖清单来源。
- 缺口：缺少 SPDX 标识
- 缺口：缺少依赖清单来源（如 package.json / lockfile）
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN

### PARTIAL：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：docs/ARCHITECTURE.md
已按待验证假设记录状态/活动数据来源，未宣称可用；但来源片段不完整。
- 缺口：agents 表字段被截断，状态与活动字段定义不完整
- 缺口：无实测验证记录
- 来源：https://github.com/keshrath/agent-comm/blob/main/docs/ARCHITECTURE.md（exact source quote: evidence_1986ad441d6546a8；读取于 2026-10-13T06:38:36.837423Z）
  > text status

### UNKNOWN：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：sgentzen/vibe-dash
唯一证据仅为许可证声明，未涉及本地存储/离线运行能力，无法判定。
- 缺口：缺少架构/存储/离线运行说明
- 缺口：缺少依赖清单以判断是否强制联网托管服务

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：sgentzen/vibe-dash
证据未包含任何响应式布局或视口适配说明，无法判定。
- 缺口：缺少前端框架与响应式设计证据
- 缺口：缺少桌面/移动视口验证方法

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：sgentzen/vibe-dash
证据未提及任何 JSON 导出功能，无法判定。
- 缺口：缺少导出功能文档或代码证据

### PARTIAL：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：sgentzen/vibe-dash
仅有许可证标识声明；无许可证原文、无版本号、无依赖清单，三项均未证实。
- 缺口：缺少 LICENSE 文件原文条款
- 缺口：缺少版本号/发布标签
- 缺口：缺少依赖清单（如 lockfile/SBOM）
- 来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e；读取于 2026-10-13T06:38:42.135541Z）
  > License: Apache License 2.0

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：sgentzen/vibe-dash
仅有“Apache License 2.0”标识，无实际条款原文，不能据此推断商业许可。
- 缺口：需引用 Apache-2.0 第2条授权与第4条条件原文
- 缺口：需确认适用版本与 NOTICE 要求

### UNKNOWN：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：sgentzen/vibe-dash
来源未提供任何 Agent 状态/活动接口的官方文档或验证方法。
- 缺口：缺少接口官方文档链接
- 缺口：缺少可执行验证步骤（如请求样例、断言）

### PARTIAL：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：sgentzen/vibe-dash
本评估已区分证据条目与 UNKNOWN 条目；未执行任何安装、调用或部署。
- 缺口：候选覆盖面不足，仅一个资源且仅含许可证声明
- 来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e；读取于 2026-10-13T06:38:42.135541Z）
  > License: Apache License 2.0

### PARTIAL：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：sgentzen/vibe-dash
已分列三项：许可证=仅标识声明；版本=UNKNOWN；依赖清单=UNKNOWN。
- 缺口：版本与依赖清单均无来源证据
- 来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e；读取于 2026-10-13T06:38:42.135541Z）
  > License: Apache License 2.0

### PARTIAL：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：sgentzen/vibe-dash
记录了许可证名称但非 SPDX 标识或版本号；依赖清单来源缺失。
- 缺口：需确认 SPDX 标识 Apache-2.0 及对应 LICENSE 文件
- 缺口：需依赖清单来源（lockfile/SBOM 路径）
- 来源：https://github.com/sgentzen/vibe-dash（exact source quote: evidence_ffb65330dfc3465e；读取于 2026-10-13T06:38:42.135541Z）
  > License: Apache License 2.0

### UNKNOWN：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：sgentzen/vibe-dash
未提供数据来源说明；按约束记为待验证假设，不宣称可用。
- 缺口：缺少数据来源与采集方式说明
- 缺口：缺少目标环境实测记录

### PARTIAL：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：README.md
README 描述自托管 hub 与 LAN/私有网络定位，但存储/读取是否完全本地未在片段中证实。
- 缺口：片段未说明状态与活动数据的本地存储机制（数据库/文件）
- 缺口：未证实无任何联网托管依赖（如推送通知服务）
- 来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6；读取于 2026-10-13T06:38:46.515481Z）
  > Single-operator by design (each operator runs their own hub). LAN / private-network use —
  > > not built for public internet exposure.

### PARTIAL：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：README.md
README 自称 mobile-first 且支持桌面/手机，但无响应式实现或视口测试证据。
- 缺口：无 CSS/断点或响应式实现证据
- 缺口：无桌面与移动视口实测记录
- 来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6；读取于 2026-10-13T06:38:46.515481Z）
  > **A multi-server, mobile-first dashboard for supervising AI coding agents.**

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：README.md
所提供片段中未见任何 JSON 导出功能描述，缺失不等于不存在。
- 缺口：需检索 README 全文与源码中 export/JSON 相关实现

### UNKNOWN：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：README.md
来源元数据 license 为 UNKNOWN，片段含 License 章节标题但无条款原文、版本号或依赖清单。
- 缺口：需 LICENSE 文件原文与 SPDX 标识
- 缺口：需 release/tag 或 package 版本号
- 缺口：需依赖清单（如 package.json / lockfile）

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：README.md
无许可证条款原文可引用，无法判定商业使用许可，按规则保持 UNKNOWN。
- 缺口：需引用 LICENSE 中授权/限制条款原文后再判定

### PARTIAL：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：README.md
README 说明状态由 Claude Code/Codex hooks 驱动，但无官方接口文档或验证方法，可用性未验证。
- 缺口：需 Claude Code / Codex hooks 官方文档链接
- 缺口：需可执行验证步骤（如本地 hook 触发与状态断言）
- 缺口：目标环境未实测，状态一律未验证
- 来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6；读取于 2026-10-13T06:38:46.515481Z）
  > Claude Code and Codex hooks drive per-session state — `blocked` / `done` / `working`
  >  / `idle`

### SUPPORTED：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：README.md
本次仅基于所给片段做证据对照并列出缺口，未执行安装、调用或部署。
- 缺口：需补充 LICENSE、版本、依赖与接口文档来源后重评
- 来源：https://github.com/darthnorse/agentmon/blob/main/README.md（exact source quote: evidence_9678b5138f6945e6；读取于 2026-10-13T06:38:46.515481Z）
  > **Status:** v1. Single-operator by design (each operator runs their own hub).

### UNKNOWN：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：README.md
三项证据均缺失：许可证原文、版本号、依赖清单在片段中均无来源可引。
- 缺口：许可证证据状态：UNKNOWN
- 缺口：版本证据状态：UNKNOWN（仅见 'v1' 状态描述，非版本号证据）
- 缺口：依赖清单证据状态：UNKNOWN

### UNKNOWN：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：README.md
无 SPDX 标识、无许可证版本、无依赖清单来源可记录。
- 缺口：待补：LICENSE 文件 URL 与 SPDX 标识
- 缺口：待补：依赖清单文件 URL（如 package.json）

### UNKNOWN：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：README.md
已按待验证假设记录状态来源（hooks 驱动），未宣称可用；但缺官方文档与实测。
- 缺口：需官方 hooks 文档与本地验证脚本设计
- 缺口：目标环境实测前保持未验证
- 缺口：判断缺少可定位的原文依据，已降为 UNKNOWN
- 来源：https://github.com/darthnorse/agentmon/blob/main/README.md（Exa /contents full source text；读取于 2026-10-13T06:38:46.515481Z）
  > # README.md
  >
  > - Branch: main
  > - Repository: darthnorse/agentmon
  >
  > ---
  >
  > # AgentMon
  >
  > **A multi-server, mobile-first dashboard for supervising AI coding agents.**
  >
  > AgentMon shows the live terminal sessions from every one of your development servers in one place, surfaces
  > the ones that need you (an agent waiting for input or approval) first, and lets you jump into any of them —
  > from your desktop or your phone — to answer, approve, or course-correct. When a session you're *not* looking
  > at gets blocked, AgentMon tells you: an in-app toast and sound, or a push notification when your phone is
  > asleep.
  >
  > It's built for the common reality of running several Claude Code or Codex sessions across several boxe

### UNKNOWN：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：chuckplayer/claude-agent-dashboard
唯一证据仅为许可证声明，未涉及本地存储/离线运行架构，无法判定。
- 缺口：缺少架构说明、README 运行前提、数据存储位置等证据
- 缺口：未提供是否依赖托管服务的说明

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：chuckplayer/claude-agent-dashboard
证据未包含任何前端框架、视口适配或响应式布局信息。
- 缺口：缺少 UI 技术栈与响应式设计证据
- 缺口：缺少桌面/移动端视口验证方法

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：chuckplayer/claude-agent-dashboard
证据未提及任何导出功能或 JSON 序列化能力。
- 缺口：缺少导出功能证据
- 缺口：缺少 JSON 导出验证方法

### PARTIAL：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：chuckplayer/claude-agent-dashboard
仅有许可证标识声明，无许可证原文、无版本号、无依赖清单。
- 缺口：缺少 MIT 许可证原文（LICENSE 文件全文）
- 缺口：缺少版本号/发布标签证据
- 缺口：缺少依赖清单（如 package.json / lockfile）证据
- 来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6；读取于 2026-10-13T06:38:50.480780Z）
  > License: MIT

### UNKNOWN：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：chuckplayer/claude-agent-dashboard
仅有“License: MIT”标识，无许可证条款原文，不能据此判定商用许可。
- 缺口：缺少 MIT 许可证正文条款引用（如授予权利、再分发条件）
- 缺口：缺少许可证适用范围说明（仓库整体 vs 部分文件）

### UNKNOWN：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：chuckplayer/claude-agent-dashboard
证据中无任何接口文档、数据来源说明或验证方法。
- 缺口：缺少官方接口文档链接
- 缺口：缺少可执行验证步骤（如本地探针、契约测试）
- 缺口：接口可用性未实测，保持未知/未验证

### PARTIAL：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：chuckplayer/claude-agent-dashboard
已产出证据对照与缺口清单；仅许可证标识有证据，其余条目保持 UNKNOWN，未执行任何操作。
- 缺口：多数条件仍缺来源证据，缺口清单需后续补充
- 来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6；读取于 2026-10-13T06:38:50.480780Z）
  > License: MIT

### PARTIAL：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：chuckplayer/claude-agent-dashboard
三项已分别标注：许可证=仅有标识声明，版本=UNKNOWN，依赖清单=UNKNOWN。
- 缺口：版本证据缺失
- 缺口：依赖清单证据缺失
- 来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6；读取于 2026-10-13T06:38:50.480780Z）
  > License: MIT

### PARTIAL：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：chuckplayer/claude-agent-dashboard
仅记录到“MIT”标识，未确认 SPDX 标识来源；依赖清单来源缺失。
- 缺口：未确认 SPDX 标识（MIT）是否来自 LICENSE 文件或仓库元数据
- 缺口：缺少依赖清单来源（如 package.json 路径）
- 来源：https://github.com/chuckplayer/claude-agent-dashboard（exact source quote: evidence_62e8d0b1da804fe6；读取于 2026-10-13T06:38:50.480780Z）
  > License: MIT

### UNKNOWN：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：chuckplayer/claude-agent-dashboard
证据未描述数据来源，无法记录为待验证假设，保持 UNKNOWN。
- 缺口：缺少数据来源说明
- 缺口：缺少目标环境实测计划

### SUPPORTED：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：destrynewiger/OpenAgenticOS
README 声明本地仪表盘、磁盘存储、loopback 服务、零运行时依赖；未实测，仅文档证据。
- 缺口：未在目标环境实测本地运行与离线行为
- 缺口：README 为部分摘录，未覆盖全部运行路径
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948；读取于 2026-10-13T06:46:20.056493Z）
  > OpenAgenticOS is a local dashboard for the agent tools on your computer. It checks which surfaces respond, stores private notes on disk, and gives you a four-angle review of an idea without calling a hosted model.

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：destrynewiger/OpenAgenticOS
所提供摘录未提及响应式布局或移动端视口支持，无法判定。
- 缺口：缺少响应式/移动端视口的文档或代码证据
- 缺口：需查 UI 源码与 CSS 断点后再判定

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：destrynewiger/OpenAgenticOS
摘录仅提到状态 API 返回字段与本地 state.json 存储，未提及 JSON 导出功能。
- 缺口：无导出功能文档证据
- 缺口：需查 API/CLI 是否提供导出端点

### PARTIAL：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：destrynewiger/OpenAgenticOS
许可证原文与版本号有来源；依赖清单仅有“零运行时依赖”声明，无 lockfile 证据。
- 缺口：无 package-lock.json / 依赖树证据
- 缺口：依赖清单条目保持 UNKNOWN
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE（exact source quote: evidence_5956966f61424259；读取于 2026-10-13T06:46:20.054250Z）
  > MIT License
  >
  > Copyright (c) 2026 OpenAgenticOS contributors
  >
  > Permission is hereby granted, free of charge, to any person obtaining a copy
  > of this software and associated documentation files (the "Software"), to deal
  > in the Software without restriction

### SUPPORTED：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：destrynewiger/OpenAgenticOS
MIT 原文含“without restriction”及 use/sell 授权，覆盖商用；须保留版权与许可声明。
- 缺口：需确认仓库内是否含第三方代码或子目录其他许可
- 缺口：需保留版权与许可声明以满足 MIT 条件
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/LICENSE（exact source quote: evidence_5956966f61424259；读取于 2026-10-13T06:46:20.054250Z）
  > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  > copies of the Software, and to permit persons to whom the Software is
  > furnished to do so, subject to the following conditions:

### PARTIAL：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：destrynewiger/OpenAgenticOS
有状态 API 字段说明与本地端口，但无完整接口规范；可用性未实测，标为未验证。
- 缺口：无端点路径、方法、响应 schema 的官方文档
- 缺口：验证方法（如 curl 127.0.0.1:4180 状态端点）未在目标环境执行
- 缺口：接口可用性保持 UNKNOWN/未验证
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948；读取于 2026-10-13T06:46:20.056493Z）
  > The status API returns labels, descriptions, states, and short results. It does not return configured commands, URLs, or command output.

### SUPPORTED：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：destrynewiger/OpenAgenticOS
本评估仅基于给定来源做证据对照，未执行安装、调用或部署，并逐条标注 UNKNOWN。
- 缺口：后续复核需在目标环境实测，本轮不执行
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948；读取于 2026-10-13T06:46:20.056493Z）
  > Read [SECURITY.md](SECURITY.md) before exposing the process through a proxy or changing the loopback boundary.

### PARTIAL：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：destrynewiger/OpenAgenticOS
许可证：有原文；版本：package.json 0.2.0；依赖清单：仅“零运行时依赖”声明，无 lockfile。
- 缺口：依赖清单证据状态为 UNKNOWN（无 lockfile/依赖树）
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/package.json（exact source quote: evidence_c0544dfab30c444b；读取于 2026-10-13T06:46:20.058642Z）
  > "name": "openagenticos",
  >   "version": "0.2.0",

### PARTIAL：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：destrynewiger/OpenAgenticOS
SPDX 标识 MIT 与组件版本 0.2.0 有来源；依赖清单来源缺失，仅 README 声明。
- 缺口：依赖清单来源（lockfile/SBOM）缺失，保持 UNKNOWN
- 来源：https://api.github.com/repos/destrynewiger/openagenticos（exact source quote: evidence_f64f221bbddc4287；读取于 2026-10-13T06:46:20.048099Z）
  > "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT", "url": "https://api.github.com/licenses/mit", "node_id": "MDc6TGljZW5zZTEz"}

### PARTIAL：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：destrynewiger/OpenAgenticOS
文档称内置 Claude Code、Codex、Hermes、OpenClaw、Ollama 探针，但未实测，仅记为待验证假设。
- 缺口：各探针在目标环境的实际可用性未验证
- 缺口：最近活动数据来源未在摘录中说明
- 来源：https://github.com/destrynewiger/OpenAgenticOS/blob/main/README.md（exact source quote: evidence_f0ab50d146504948；读取于 2026-10-13T06:46:20.056493Z）
  > The app ships with generic probes for Claude Code, Codex, Hermes, OpenClaw, and Ollama. Add or replace tools through a private config file.

### SUPPORTED：仪表盘以本地优先方式运行：核心状态与活动数据的存储、读取与展示在本地环境即可完成，不依赖任何必须联网的托管服务作为运行前提。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
设计文档与 Dockerfile 显示单进程+SQLite+本地数据卷，无外部托管依赖；但未实测。
- 缺口：未在目标环境实测启动与离线运行
- 缺口：MCP 远程 Streamable HTTP 接入方式是否需联网未证实
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d；读取于 2026-10-13T06:37:14.889993Z）
  > The product is a single Node process plus SQLite plus a data directory. It is
  > released publicly for others to self-host.

### UNKNOWN：仪表盘以响应式网页形式呈现，在桌面与移动端视口下均可正常查看 Agent 在线状态与最近活动。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
所给片段仅提及浏览器实时 feed 与 SSE，未见响应式/移动端视口相关声明或证据。
- 缺口：缺少响应式布局、断点或移动端视口的官方说明
- 缺口：缺少桌面/移动视口实测记录

### UNKNOWN：仪表盘支持将 Agent 状态与最近活动数据导出为 JSON 格式文件。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
片段显示事件以 JSON 经 SSE 传输，但未见“导出为 JSON 文件”的功能或接口证据。
- 缺口：缺少 JSON 导出功能/端点文档
- 缺口：缺少导出文件格式与字段定义

### PARTIAL：对每个核心候选开源组件，逐项核验并记录其许可证原文、版本号与依赖清单；来源无法证实的条目保持 UNKNOWN，不得推断或补全。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
许可证原文与版本有来源；依赖清单仅片段，未逐项核验各依赖许可证。
- 缺口：package.json 依赖清单为截断片段，未含全部依赖
- 缺口：各传递依赖的许可证原文与版本未核验
- 缺口：package-lock.json 未提供
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json（exact source quote: evidence_32ca15e079504732；读取于 2026-10-13T06:46:26.109831Z）
  > "version": "0.0.1",

### SUPPORTED：对每个核心候选组件，判定其许可证是否允许商业使用，并给出可核验的条款依据；无法核验的标注为 UNKNOWN，不得默认允许或默认禁止。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
MIT 原文含 use/sell 授权条款，允许商业使用；仅覆盖本仓库自身，不含依赖。
- 缺口：依赖组件（如 sharp、better-sqlite3、ffmpeg 等）的商用许可未核验
- 缺口：未核验 MIT 声明是否覆盖全部仓库内容
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/LICENSE（exact source quote: evidence_3945ea3558d149a9；读取于 2026-10-13T06:46:26.102281Z）
  > Permission is hereby granted, free of charge, to any person obtaining a copy
  > of this software and associated documentation files (the "Software"), to deal
  > in the Software without restriction, including without limitation the rights
  > to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  > copies of the Software

### PARTIAL：对 Agent 状态与活动数据接口，收集官方接口文档并给出可执行的验证方法；在目标环境实测前，接口可用性一律标注为未知/未验证。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
有官方设计文档给出 SSE 端点与事件类型；但无实测，可用性仍为未验证。
- 缺口：未提供可执行验证步骤（如 curl 示例、预期响应）
- 缺口：MCP 工具（post_update 等）的官方接口文档未提供
- 缺口：目标环境未实测，可用性 UNKNOWN
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d；读取于 2026-10-13T06:37:14.889993Z）
  > `GET /api/stream` is a single SSE endpoint carrying every event type as JSON, each
  > with an `id:` set to the global event sequence number.

### SUPPORTED：研究产出为证据对照评估与缺口清单，明确区分“有充分来源证据”的条目与“仍为 UNKNOWN”的条目，且不执行任何组件安装、接口调用或部署。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
本次仅做证据对照与缺口清单，未执行安装、调用或部署。
- 缺口：后续需补充依赖级许可证核验与接口实测计划
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d；读取于 2026-10-13T06:37:14.889993Z）
  > **Repo:** `wildware-uk/agent-dashboard` (public, MIT)

### PARTIAL：在证据对照评估中，对每个核心候选同时报告许可证证据状态、版本证据状态与依赖清单证据状态，三者分别标注而非合并为单一结论。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
许可证=有原文；版本=有 package.json 版本号；依赖清单=仅截断片段，未逐项。
- 缺口：依赖清单证据不完整，无法逐项标注各依赖状态
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/package.json（exact source quote: evidence_32ca15e079504732；读取于 2026-10-13T06:46:26.109831Z）
  > "license": "MIT",

### SUPPORTED：对每个候选组件记录其许可证版本（如具体版本号或 SPDX 标识）与依赖清单来源，以便后续复核。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
SPDX 标识 MIT 与仓库版本 0.0.1 有来源；依赖清单来源为 package.json（片段）。
- 缺口：依赖清单来源不完整，需 package-lock.json 或 SBOM
- 来源：https://api.github.com/repos/wildware-uk/agent-dashboard（exact source quote: evidence_a31fe6f0c3e94210；读取于 2026-10-13T06:46:26.097377Z）
  > "license": {"key": "mit", "name": "MIT License", "spdx_id": "MIT", "url": "https://api.github.com/licenses/mit", "node_id": "MDc6TGljZW5zZTEz"}

### PARTIAL：仪表盘展示的 Agent 在线状态与最近活动数据来源，在目标环境实测前不宣称可用，仅记录为待验证假设。

资源：docs/superpowers/specs/2026-08-25-agent-dashboard-design.md
presence 与 agent.presence 事件有文档描述，但未实测，仅作待验证假设。
- 缺口：在线状态判定逻辑（last_seen_at/heartbeat）未实测
- 缺口：未验证 SSE 在目标环境的连通性与事件完整性
- 来源：https://github.com/wildware-uk/agent-dashboard/blob/main/docs/superpowers/specs/2026-08-25-agent-dashboard-design.md（exact source quote: evidence_2bf63c421a3d487d；读取于 2026-10-13T06:37:14.889993Z）
  > Event types: `project.created`, `project.updated`, `update.created`,
  > `update.deleted`, `media.ready`, `task.created`, `task.updated`,
  > `message.created`, `approval.created`, `approval.decided`, `agent.presence`.

## 研究范围与限制

- destrynewiger/OpenAgenticOS：未取得以下类别的可读根目录文件（缺失或超出读取限制），保持未核查：部署配置
- docs/superpowers/specs/2026-08-25-agent-dashboard-design.md：README.md 仅保存前 12000 字符，后文未用于匹配判断。
- 本修订候选目录上限为 8 个；未调查的候选不作结论。
- 检索范围内仍有未覆盖条件；这些缺口已保留，不代表目标已实现。

研究用量：{"actions": 21, "tool_calls": 4, "cost_usd": 0.0639041, "known_cost_usd": 0.0639041, "reserved_usd": 0.0, "input_tokens": 62707, "output_tokens": 25910, "model_requests": 17, "cost_unknown": false, "elapsed_seconds": 177.56, "stopped_reason": null}
