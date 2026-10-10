# 2026-10-10 当前复验 — M0 安全基线

**当前 Gate：PASS**。本节与 [FINAL_ACCEPTANCE_REPORT.md](FINAL_ACCEPTANCE_REPORT.md) 为本轮证据；下方旧报告保留为历史，历史数字/推测不能代替当前复验。

- 实际行为与复用：保存原 HEAD、未提交前端和源文件/diff 归档，测试数据库与收费研究全部隔离；原 .env 和 .goalsift_data 未改写。复用既有 Git/pytest/路径守卫。
- 变更与证据：tests/conftest.py、tests/test_isolation.py 与 tests/test_runtime_integration.py；恢复归档见最终报告 §1。
- 执行/观察：初始 .venv/bin/python -m pytest：61 passed；最终隔离回归 88 passed。
- Mock/Live：本轮三例 DeepSeek/Exa 及一次性基线为真实收费调用；自动负向和恢复测试只替换付费提供商，不计作 Live。
- 恢复点：修改前归档与 `2be917c`；最终 `phase-a-v0.2.1`。测试在临时数据根，无目标项目执行。
- 限制与下一步：本节 Gate PASS；后续沿现有架构完成 SDK 与真实来源复验。

- 凭据遗留：原 HEAD 安全测试含两个真实 key 字面量，本轮当前文件已替换为合成值并扫描通过；旧历史/0600 本机归档仍需按敏感材料处理，建议更换提供商凭据。

<!-- historical-report -->
# M0 Report — Requirements Review & Safe Baseline

**Milestone**: M0 — 需求审查与安全基线  
**Phase**: Phase A · V0.2  
**Date**: 2026-10-09  
**Verdict**: ✅ **PASS**

Gate 标准来自 `07_DEVELOPMENT_PLAN.md` §3：当前工作区状态已记录；可以恢复；任何测试不会写用户真实目录；测试入口能运行；凭据不会纳入版本控制；影响产品的文档冲突已处理/明确列为 BLOCKED。M0 不要求已选定 React/FastAPI/Pydantic AI，也不要求完整应用启动。

---

## 1. Intended outcomes

- 阅读全部八份文档并形成冲突/不确定项清单；严重产品歧义请求用户决定。
- 检查现有工作树、未提交修改、用户数据路径与当前 Git 状态。
- 建立代码仓库/基线检查点、`.gitignore`、凭据模板、依赖/测试执行入口。
- 配置隔离临时目录和测试数据存储；**运行实际断言**证明不会触及用户真实文件。
- 保留最简目录，不启动正式前后端应用。

## 2. Document cross-check & conflict list

按 AGENTS.md §2 顺序阅读 01–07 + AGENTS.md。八份文档交叉核对结论：

| # | 项目 | 结论 |
|---|---|---|
| 1 | Job 状态机唯一性（04 vs 03/05 引用） | 一致。03 表格注明"唯一来源：04"；05 §3 注明状态机引用 04，不自建。 |
| 2 | Assessment 状态枚举（05 vs 02/04 引用） | 一致。05 §9 是唯一六态定义；02 §6、04 §5 引用且语义一致（SUPPORTED≠VERIFIED）。 |
| 3 | 六操作 vs 六 Agent/页面（02 vs 03/04） | 一致。02 §1、03 §1、04 §1 均明确六操作是认知操作，不要求六个 Agent/页面/模型调用。 |
| 4 | 06 架构候选状态 | 06 全文标注 PROVISIONAL，待 M1 实测。无产品级冲突，属预期。 |
| 5 | 条件双维度（02 §3 vs 05 §5） | 一致。`obligation`×`dimension` 独立；`REQUIRED+QUALITY` 合法。 |
| 6 | 不执行方案（01/02 vs 04） | 一致。Phase A 不执行用户选定方案；Proposal=建议。 |
| 7 | 修订与失效传播（04 §3.1 vs 05 §12） | 一致。COMPLETED→Refine 创新 revision；下游受影响→NEEDS_REVIEW。 |

**无严重产品级冲突**，无需用户决策阻断 M0。

### 不确定项 / 已知 BLOCKED 前瞻（不阻断 M0）

| # | 不确定项 | 影响里程碑 | 处置 |
|---|---|---|---|
| U1 | M1 要求真实模型调用与真实搜索，但用户尚未授权任何 LLM/搜索 API 密钥与预算 | M1 Live 测试 | 若 M1 启动时仍无凭据/预算，M1 Live 部分将如实报告 **BLOCKED**，不伪造 PASS。M1 仅可完成不依赖凭据的独立任务。 |
| U2 | Python 3.10.13 为环境版本；Pydantic AI（候选）最低要求 ≥3.10 | M1 | 边界满足，M1 实测兼容性。 |
| U3 | Go 1.13.1 偏旧，但 Go 不在候选技术栈 | 无影响 | 忽略。 |

## 3. Environment inspection

| 检查项 | 结果 |
|---|---|
| 工作树原有内容 | 仅 8 份规范 `.md`（01–07 + AGENTS.md），无代码、无隐藏文件、无用户数据。 |
| Git 状态 | 原非 git 仓库（`fatal: not a git repository`）。本里程碑初始化。 |
| 未提交用户工作 | 无（工作树仅规范文档，无既有代码或草稿）。 |
| Python | 3.10.13（pyenv），pip 25.2，pytest 9.0.2。 |
| uv | 0.11.26。 |
| Node | v22.21.1。 |
| git | 2.50.1 (Apple Git)。 |
| 批准的临时目录 | `/private/var/folders/hr/tz7sdpwx2xv30x2xydhkg70w0000gn/T/opencode`（已存在、可写）。 |

## 4. Actual behavior & changed files

新建文件（M0 产出）：

| 文件 | 作用 |
|---|---|
| `.gitignore` | 拦截 `.env`/凭据/数据目录/缓存/构建产物。 |
| `.env.example` | 凭据模板（LLM/搜索密钥、数据根、预算）；`.env` 被 ignore，模板不被 ignore。 |
| `pyproject.toml` | 最小项目元数据 + pytest 配置。 |
| `Makefile` | `test`/`test-verbose`/`check-env`/`clean` 入口。 |
| `README.md` | 项目说明、规范索引、快速开始。 |
| `goalsift/__init__.py` | 应用包起点（版本 `0.2.0a0`）。 |
| `goalsift/paths.py` | **可复用**隔离基础设施：数据根解析 + 路径逃逸守卫（后续里程碑的 Repository/工具适配器复用）。 |
| `tests/__init__.py` | 测试包。 |
| `tests/conftest.py` | autouse fixture：每个测试强制唯一隔离数据根。 |
| `tests/test_isolation.py` | 12 条实际断言。 |

未修改任何既有文件；未删除任何规范文档。

## 5. Reused resources

- `pytest`（已安装 9.0.2）作为测试入口，无需引入额外测试框架。
- Python 标准库 `pathlib`/`os`/`threading` 实现 `paths.py`，无新依赖。
- 未引入未经验证的第三方包（M1 才决定 Agent SDK/搜索提供商）。

## 6. Commands executed & observed output

```
$ python3 -m pytest -v
collected 12 items
tests/test_isolation.py ............                                     [100%]
============================== 12 passed in 0.02s ==============================
```

```
$ git check-ignore -v .env .goalsift_data/probe.db secrets.json credentials.json ...
.gitignore:2:.env            .env
.gitignore:11:.goalsift_data/  .goalsift_data/probe.db
.gitignore:8:secrets.json   secrets.json
.gitignore:7:credentials.json credentials.json
.gitignore:37:node_modules/ node_modules/x
.gitignore:27:.venv/        .venv/bin/python
.gitignore:20:__pycache__/  __pycache__/x.pyc
.gitignore:51:*.log         app.log
exit=0

$ git check-ignore .env.example   # expect NOT ignored
exit=1   # confirmed: .env.example is tracked
```

## 7. Test cases & evidence (mock/live distinction)

全部为**确定性单元/隔离测试**，无 live 外部调用（M0 不要求 live，M1 才要求）。无 mock 冒充 live。

| # | 测试 | 断言内容 | 结果 |
|---|---|---|---|
| 1 | `test_sanctioned_root_is_not_user_home` | 数据根 ≠ 用户 HOME，HOME 不在写根内 | PASS |
| 2 | `test_sanctioned_root_is_not_project_real_data` | 数据根 ≠ 项目真实 `.goalsift_data` | PASS |
| 3 | `test_sanctioned_root_is_not_spec_dir` | 规范目录不在写根内 | PASS |
| 4 | `test_sanctioned_root_is_under_temp` | 数据根位于批准的临时区 | PASS |
| 5 | `test_real_write_stays_inside_root` | 真实写入经 API 落在根内、不在禁地 | PASS |
| 6 | `test_dotdot_traversal_refused` | `../../../../etc/passwd` 被拒 | PASS |
| 7 | `test_absolute_path_outside_refused` | `/etc/passwd` 被拒 | PASS |
| 8 | `test_absolute_path_inside_root_allowed` | 根内绝对路径放行 | PASS |
| 9 | `test_symlink_escape_refused` | 指向根外的 symlink 被拒 | PASS |
| 10 | `test_spec_docs_exist_and_outside_write_root` | 8 份规范均在写根外 | PASS |
| 11 | `test_spec_docs_not_modified_by_test_run` | 测试运行不改规范文档 mtime | PASS |
| 12 | `test_package_importable` | `goalsift` 可导入 | PASS |

## 8. Checkpoint reference

- Git 仓库于本里程碑初始化；基线提交见 `git log` 首个 commit（message: `M0: safe baseline, isolation, test entry`）。
- 恢复方式：`git checkout` 到该 commit 即可回到 M0 通过态。

## 9. Gate verdict

| Gate 条件 (07 §3) | 满足 | 证据 |
|---|---|---|
| 当前工作区状态已记录；可以恢复 | ✅ | git init + 基线 commit |
| 任何测试不会写用户真实目录 | ✅ | 测试 1–11 路径断言全 PASS |
| 测试入口能运行 | ✅ | `python3 -m pytest` 12 passed |
| 凭据不会纳入版本控制 | ✅ | `git check-ignore` 拦截 `.env`/`credentials.json`/`secrets.json`/`.goalsift_data/`；`.env.example` 被跟踪 |
| 影响产品的文档冲突已处理/列为 BLOCKED | ✅ | §2 交叉核对无冲突；U1(M1 凭据)前瞻性记录，不阻断 M0 |
| 未要求锁定 React/FastAPI/Pydantic AI | ✅ | 未引入前端/Agent SDK；`paths.py` 与选型无关 |
| 未要求完整应用启动 | ✅ | 仅最小测试入口与隔离基础设施 |

**M0 Verdict: PASS**

## 10. Known limits & next safe action

- U1：M1 live 模型/搜索测试在无授权凭据/预算时将 BLOCKED，不可伪造 PASS。
- `paths.py` 仅为隔离基础设施；领域对象（Goal/Condition/...）与 Controller 在后续里程碑构建。
- 下一步安全行动：进入 **M1 — 技术 Spike**，验证候选 Agent SDK（Pydantic AI 等）的真实文本/结构化输出/工具调用/错误处理、真实搜索与来源读取，产出 `M1_SPIKE_REPORT.md`。若 M1 启动时无凭据，如实在报告中标记 live 部分 BLOCKED 并继续可独立完成的任务。
