# 2026-10-10 信息布局验收

结论：PASS。范围为现有 Phase A 前端的信息层级和响应式布局，保留既有深色风格与全部研究状态语义。

恢复基线：`ffbd43c` / `phase-a-v0.2.1`。开始时工作树干净，沿用当前开发。

## 实现

- 首页将目标输入与已有研究并列，缩短介绍和示例；任务卡展示状态、修订、两行目标和下一步。
- 工作区扩大可用宽度，桌面以结果为主栏，目标理解、原始需求、研究范围、用量与 Refine 为辅助栏。窄屏默认折叠背景，五个页签均保留文字。
- 方案先展示标题、候选状态、覆盖与缺口、概述和推荐理由；长文可展开。风险默认可读，未覆盖条件及集成/补充工作可按需展开。实施成本以字段说明展示，与本轮研究用量分开。
- 条件卡默认展示条件及属性，推导依据、验收方式和资源评估可展开；来源与证据跳转保留。
- 澄清问题与答复框位于辅助背景之前。导览结束恢复背景折叠状态；历史快照导览排除执行操作。提交答复或 Refine 后恢复结果阅读布局。

更改文件：`frontend/src/App.tsx`、`Home.tsx`、`Workspace.tsx`、`api.ts`、`tour.ts`。复用现有 React、Radix、Tailwind、Driver.js 与后端契约，未更换框架或引入依赖。

## 实际验证

- `npm run lint`：PASS，无 lint 警告。
- `npm run build`：PASS，TypeScript 与 Vite 构建成功。详细结果见 `build.txt`。
- `git diff --check`：PASS。
- Cua 真实浏览器检查：1280×720 桌面、390×844 手机、1024×768 平板。桌面 main 的 scrollWidth/clientWidth 均为 1016，手机均为 382，平板均为 760；未出现横向溢出。
- 首页示例填入实际文本，创建按钮从禁用转为可用；未在真实供应商服务上提交新任务。
- 真实已有研究 `job_8a48c356fcd049ab`：方案概述展开/收起、查看原始需求、条件的资源评估展开、评估跳转 Match 正常。2/8 方案覆盖、6 项缺口及来源支持不等于实测的提示保留。
- 真实历史修订 2：只读标记可见，Refine 不可用，JSON 链接包含 revision=2。浏览器实际下载文件 `web-r2-export.json` 已解析，revision=2、COMPLETED、9 个条件；除导出时间外，与先前验收导出内容完全一致。只读导览显示 4 步，不指向 Refine；恢复当前修订 3。
- 隔离模拟验证：Controller + SQLite + 本地 API，供应商使用已有 ModelFixture/SearchFixture。初次澄清导览关闭后背景为折叠；真实点击答复后进入 COMPLETED；真实点击 Refine 创建修订 2/3，补充答复后继续。澄清问题始终位于背景之前，背景展开也不遮挡问题。
- 模拟 PARTIAL：状态、Resume/Cancel 按钮及不完整结果提示可见，背景区明确显示费用未知；未将未知费用当作零。

## 隔离、费用与限度

本轮没有新增真实模型或搜索调用，新增收费为 **0 美元**。已有真实结果用于只读检查；所有提交答复与 Refine 操作使用 `/private/tmp/goalsift-layout-qa` 的模拟数据。模拟供应商的费用元数据不是实际账单。未触碰用户原 `.goalsift_data`。

`offline_fixture.py` 提供可复现的辅助服务（从仓库根目录、安装测试依赖后执行 `PYTHONPATH=. .venv/bin/python acceptance/2026-10-10/layout/offline_fixture.py`）；它每次创建独立临时目录，校验 SQLite 实际位置，绑定 127.0.0.1 的系统空闲端口，并显式注入模拟供应商。验收期间使用端口 49831；临时服务及浏览器标签已关闭，预览恢复当前研究，视口覆盖已重置。

本轮未重跑先前 88 项后端测试或 M6 收费验收，因为后端未变更；此报告不把模拟检查称为 Live 验收。Vite 的 500 kB 主包体积建议仍存在（当前 501.03 kB），不影响构建通过。

## 预览与证据

- `workspace-before.png` / `workspace-desktop.png`：同一研究调整前后首屏。
- `workspace-mobile.png`、`home-desktop.png`、`home-mobile.png`：响应式界面。
- `conditions-desktop.png`、`match-desktop.png`：条件与证据。
- `needs-input-mobile-fixture.png`、`partial-mobile-fixture.png`：明确标记的模拟数据。
- `web-r2-export.json`：真实历史修订的浏览器导出。

各文件 SHA-256 见同目录 `manifest.json`。下一安全动作：继续使用现有本地预览审阅布局；无需调用收费服务。
