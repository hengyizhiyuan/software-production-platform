# Watt Work Trace 自分析修复交接 — 2026-10-12

## 1. 结论与接手边界

**功能尚未完成本轮语义资格验证，禁止以本次推送作为部署依据。**

用户最新要求是先保存现场、提交并推送交接，本轮在交接后停止推进修复与部署。
本次推送包含独立分支已有修复、最新未验证 WIP 和交接证据。
真实模型返回 COMPLETED / RESULT_READY 仅代表分析流程与结构引用校验完成，不能代替语义核验 PASS。

- 分支：`codex/watt-trace-self-analysis`。
- 独立工作区：`C:/Users/yuchunbo/.codex/worktrees/watt-trace-self-analysis/software-production-platform`。
- 远端：`https://github.com/hengyizhiyuan/software-production-platform.git`。
- 稳定架构基线：`5de657f3cb65780adf50f6557b54171a6c3cfae5`。
- 最新完成回归的代码：`27cfcfd871f6a96fe21d2cc9ff0add8e96ae8b8d`。
- 最新待验证代码：`ac3c8083a08ab91189fd48f9aa3ba7b218b6711f`（WIP）。
- canonical main 工作区：`D:/hy/software-production-platform`；本任务未修改 main 或 C3 工作区、未向 C3 任务发消息。

继续保持原范围：复用 Watt 现有 Work/Trace、Context Assembly、Native Executor、Evidence、Verification、Self-Refine 与仓库读取，Human 触发、只生成咨询报告。
不添加针对某个 Work 的运行时规则，不自动改代码/创建 Work/部署/自升级，不扩大为 C3/C4 重构。

## 2. 正式环境现状与部署经过

当前正式 API 已回滚，交接时再次通过 `docker inspect` 确认：

| 项目 | 当前记录 |
|---|---|
| SSH 别名 | `watt-ecs`，ECS `8.130.172.58` |
| 正式 API | `watt-cloud-worker-api-1` |
| 当前镜像 | `sha256:75980116516128bffc00d322b7c6721aa6bfd1a9cae86a47d5044450ca69cf2f` |
| 当前镜像标签/源码 | `watt-cloud-worker:trace-self-analysis-8505c7bd` / `8505c7bd75ca0e53be4cfd189b34eac653f8764d` |
| 容器状态 | `running` |
| 容器启动时间 | `2026-10-11T13:02:27.834026702Z` |
| 访问入口 | `http://8.130.172.58:8080/admin/works` |
| Compose | `/data/watt/runtime/docker-compose.yml`，项目 `watt-cloud-worker` |

回滚时曾验证 health、数据库与初始化恢复；本次交接只复核容器镜像/状态，不能将其说成新的完整业务健康资格。

此前 `0ad7bf83cb096021adbc398116b32d429599ef9f` 经离线报告审查后进行了 API 替换，但真实 API 分析请求 `a5014c92-b033-4423-bf4b-0cbf5f7ad0ca` 超时失败，无有效 RESULT_READY，已回滚。
之后同镜像直接服务资格请求 `ea782066-57ca-4a5e-9e05-7fee10457722` 虽生成报告，语义复核仍失败。不得抹去这段部署失败，或声称整轮从未部署。

`ecc5c747` 与 `27cfcfd8` 只构建了候选镜像并进行独立容器资格分析，**均未替换正式 API**。
最新候选镜像：`sha256:8d9dd0b4f82effd0a7a02e1cbcb6774c6052a9e6627023b88873de7e34a631a4`。
276 个 `/app/src/spg` 与实际 Python 安装目录源码哈希、导入位置、Git 源码 HEAD 已核验匹配 `27cfcfd8`。
**WIP `ac3c8083` 尚无镜像、真实报告或部署资格。**

正式 Worker、N1 Worker、协调器、数据库及 Schema 未被本任务重建或修改；部署命令只针对正式 API。
较早全容器对比曾发现其他 C3 容器生命周期变化，来源 UNKNOWN，不能声称所有其他容器全程不变。

启动时出现过 `Required governed context does not fit selected Context Budget`：新候选和旧回滚镜像均观察到同样异常，属于已保存的既有启动行为；这不等于所有恢复路径均已健康，也不在本任务扩大修复范围。
后续部署须再次确认无活动队列/分配/分析锁，备份原 API 与 Compose，API 单服务替换，异常回滚。

## 3. 已实现的通用修复

源码位置：

| 文件 | 作用 |
|---|---|
| `src/spg/application/trace_analysis.py` | 调查契约、Context/Native 流程、咨询输出边界 |
| `src/spg/domain/trace_analysis.py` | 报告 v6 结构、事实/假设/UNKNOWN 与治理约束 |
| `src/spg/infrastructure/trace_analysis_evidence.py` | 原始 Owner 读取、关联、范围检查、源码证据、报告校验 |
| `src/spg/executor/context.py` | 去除重复检查点后重新计算既有可读上下文边界；原预算不变 |
| `src/spg/web/admin.js` | 中文入口、报告呈现、旧版本兼容 |
| `tests/test_trace_analysis.py` 等 | 单元、Native、导出、数据库与 UI 回归 |

关键能力：

1. 每条 finding 必须 inspect 原始主体，并按显式 Owner 引用读取关联字段。Work/attempt/时间相同、错误文本相同不能代替直接事件关联。
2. 区分下载审计、HTTP Preview、客户端接收/保存；`completion_basis` 是规则，不是发送成功事件。
3. 已有 PWU/会话/attempt 映射保持 PRESENT；先检查具体字段，不从漏读推断平台能力缺失。
4. 读取失败效果的关联 `semantic_input`，恢复实际命令、参数、工作目录；不能仅根据错误消息猜测。
5. 大 JSON 字段可用 `evidence.read(field=JSON Pointer, offset, limit)` 返回原始连续片段；按原始 body 范围记账，读取子字段不会把父字段及其他尾部标成 READ。
6. inspect 在预算内返回原始 `request_payload.available_tools[*].identity`，区分历史生产工具与当前调查工具；工具定义并不自动证明实际执行或当前权限。
7. 同一 Owner 的字节一致投影可去重，冲突投影保留；引用被移除时不能继续保留其事实断言。
8. 根因假设要求 `repository.read` 的实际实现与周围控制流；search 只定位，最终 diff 只证明净变更，当前代码不证明历史 Worker 版本。
9. UNKNOWN 不能绕过源码门禁写条件机制。诊断标签/预算/拒绝行为清单不证明实际执行、中断、重试次数或缺陷。
10. 失败时间、创建时间、恢复状态、运行时提交时间分开；有执行/规划记录须重建对应时间线阶段。
11. 原始 `validation_issues` 类型/位置保留在事实中，不能泛化为不同异常分支统一输出。
12. 原预算仍为 12 次推理、48 次工具、600 秒；引用/结构校验不声称全语义蕴含成立，仍需独立报告复核。

## 4. 最新真实 Work 验证及尚未通过项

历史 Work：`3ee622b5-b816-5679-afdc-e5de51cd2702`。
这是已完成的真实模型 dogfood/资格 Work，不是未知客户 holdout。
目标为既有演示官网新增 `services.html`、`news.html`，只新增两文件，两 PWU 加 JOIN，独立验证与真实 HTTP Preview 后由 Human 明确 ACCEPT。

### `ecc5c747`：语义 FAIL

- 请求：`2d67ac2c-c9e3-4d2f-b6a9-986e6ac96327`。
- 流程完成、结构引用 PASS；独立语义复核 FAIL。
- 错误：调查 `repository.read/search` 被当成历史已准入恢复工具；一次诊断类型/位置被推广到不同异常；UNKNOWN 下写未读源码的条件产生机制。
- 后续 `27cfcfd8` 针对通用读取与边界作了修复，未对这个 Work 硬编码。

### `27cfcfd8`：回归 PASS，真实报告语义仍 FAIL

- 请求：`0bf80dc8-f233-4013-a847-c6986de29963`。
- 分析开始/结束：`2026-10-11T14:27:10.165723Z` / `2026-10-11T14:35:20.389180Z`。
- COMPLETED、RESULT_READY；10 次推理、28 次工具，结构引用 PASS。
- 报告摘要：`5b28a8237e7b2b0120cdf063f5ecc4991a9ac3faf6f60a7e9319c36676723fe6`。
- 冻结 snapshot：`3f3b536e79d874a7905e4719bef7ff9eab985866e566715128eb1645bf07b72d`。
- 原始 Work/PWU/Self-Refine/Human 验收四组记录前后哈希一致：`2e3b1d60025c720a12c4e24ccac3bb30fc27f0b5020328ee1cba04efed3ae9ca`。这只覆盖所检查四组，不能声称整库完全不变。

已修正：原始 `argv=['ls','-la']`、`cwd='.'`；历史 available_tools 的九个身份；两种失败及其 Self-Refine 的分别关联；诊断不计入实际中断；原始校验 subtype 不再混入通用机制；预览/下载/验收表面分开；现有映射不被称作缺失。

**仍失败的具体表述**：

- `findings/3/recommendation`：“不得用未来日志回填历史丢弃的响应”。
- `platform_improvements/0/statement`：“使未来诊断不依赖对已丢弃响应的重建”。

`/result_payload/raw_response` 未导出只证明指定快照字段取证边界，不能证明历史响应已丢弃、删除或丢失。以上句子带有未经证明的前提，不能作为通过报告部署。
还应继续复核所有建议的适用权限、诊断与执行的差别、引用主体和源码条件，不能只检查这两句。

**审阅者笔记更正**：较早现场摘要误把 services.html 的一次读取记为 preview.inspect。
重新核对冻结原始回执 `1f8f5cb0-b877-4311-babb-4f95fbe7f61d` 的 effect_id `0faefc4c-21ab-4111-8157-0d448e7fe740`，关联原始效果实际是 `file.read`。
最新报告这项为正确引用，不应为了迎合旧笔记改为 preview.inspect。

## 5. 最新 WIP 与测试状态

WIP 提交：`ac3c8083a08ab91189fd48f9aa3ba7b218b6711f`。

- 改写通用调查说明，明确未导出/未读不证明丢弃，历史保留状态须保持 UNKNOWN。
- 增加 `HISTORICAL_DATA_LOSS` 与 `CAPTURE_GAP_CANNOT_ESTABLISH_HISTORICAL_DATA_LOSS` 校验，覆盖事实、分析、恢复/平台建议、回归场景。要断言数据损失须有相应原始 Owner 引文；派生范围检查、调查草稿或仓库比较不能充当历史删除收据。
- 新增 11 个参数化回归案例，包括中文/英文建议隐含数据损失及有原始处置记录的区分。
- **实现与新增测试尚未通过回归，属于 WIP，不是已验证修复。**这些语言检查是保守门禁，不证明完整语义蕴含；后续需要审查误拒与漏拒边界。

| 范围 | 结果 |
|---|---|
| `27cfcfd8` Python/数据库/Native/导出测试 | 210 PASS，0 error/failure/skip，约 50.31 秒 |
| `27cfcfd8` Admin JS | 33 PASS |
| `ac3c8083` 新增 11 例及全量相关回归 | NOT EXECUTED / PENDING；预期总数 221，未实际观察 |
| `ac3c8083` 真实模型 Work 复验 | PENDING |
| `ac3c8083` 镜像与部署 | NOT BUILT / NOT DEPLOYED |

尝试 WIP 回归时，本机 Docker Linux daemon 不可用（`dockerDesktopLinuxEngine` 命名管道不存在），pytest 未启动，因此不存在新 JUnit PASS。
曾隐藏启动用户本机 Docker Desktop；交接时 `docker info` 仍失败。不要自动重启/删除 Docker 数据或清理其他项目容器来解决它。
可以在确认测试环境职责后恢复本任务隔离测试服务，或准备独立 Linux/PostgreSQL 测试环境；不能使用或停掉 N1/C3 环境来代替。

## 6. 接续事项与完成门禁

按依赖顺序：

1. 审查 WIP 对数据丢失断言的覆盖/误拒边界，必要时修正通用实现；恢复独立测试依赖，执行新增与相关全套回归，保存真实 JUnit。不可沿用 `27cfcfd8` 的 210 PASS 作为 WIP PASS。
2. 提交验证代码，在原正式镜像基础上构建可追溯镜像，核验原始 Git blob 哈希、实际导入位置、Git HEAD、276 个源码文件一致。Windows `git archive` 可能应用 CRLF 过滤，应使用原始 `git cat-file` 字节。
3. 正式 API 保持原版本，通过同一 `TraceAnalysisService` / Native 流程读取真实 ECS Work 原始 Owner，保存完整新报告与审计，核对四组 Owner 前后哈希。不手改生成报告、替换审计、删掉失败历史或回填 UNKNOWN。
4. 对完整报告独立语义审查，至少覆盖命令参数、历史工具权限、PWU/session/attempt 映射、引用身份、异常条件分支、诊断标签、历史数据保留状态、预览/下载/Human 验收、时间线与最终 Git 净变化。任一错配或过度推断则语义 FAIL，继续原范围修复，不部署。
5. 用户先前仅在“确认完成”前提下授权部署；最新指令是先交接。恢复部署工作时须遵守该先决条件并重新查运行状态。合格后保存回滚依据，仅替换正式 API；Worker/N1/协调器/数据库/C3 不变。健康或集成失败立即回滚并保存证据。
6. 部署后检查实际源码/导入、health、登录与 Origin 门禁、中文 JS 哈希、历史报告列表与 GET，以及同一已核验 request_id/rationale 的幂等 POST 重放。重放须不新增模型调用/事件，**不能说成新的真实模型生成验证**。若进行新模型分析，需重新审查新报告。
7. 保存完整发布证据、最终语义审查与剩余 UNKNOWN，再提交并推送独立分支；不合并 main、不声称 C3 通过。

当前没有可交付的本轮最终语义 PASS。仍保留：历史 Worker 加载版本 UNKNOWN；未捕获原始无效响应的内容/详细原因 UNKNOWN；具体执行过的替代配方/重试次数不能从诊断和预算推出；客户端收到/保存不能从服务器规则或 HTTP Preview 推出。

## 7. 证据与脚本位置

可随远端分支取得的精选证据位于 [evidence/work-trace-self-analysis-handoff-20261012](evidence/work-trace-self-analysis-handoff-20261012)：

- `handoff-checkpoint.json`：代码身份、状态、请求、哈希和证据文件 SHA256。
- `latest-model-report-NOT-QUALIFIED.json`：最新原始报告，未经手工改写，明确未通过语义资格。
- `latest-model-summary.json`：模型执行完成记录。
- 两份 `independent-review-*-FAIL.json`：失败复核及笔记更正。
- `regression-27cfcfd8-PASS.json`：已通过版本的回归摘要。
- `image-build/preflight/source-manifest-27cfcfd8*.json`：候选镜像身份与源文件哈希。

本机完整证据（不是远端仓库依赖）：

- `D:/hy/watt-trace-owner-repair-artifacts-20261011/historical-attempts`：旧失败报告、离线/部署/回滚记录、脚本与上下文。
- `D:/hy/watt-trace-owner-repair-artifacts-20261011/release-ecc5c747`。
- `D:/hy/watt-trace-owner-repair-artifacts-20261011/release-27cfcfd8`：`analysis.json`、`report.json`、`summary.json`、JUnit、镜像构建与资格脚本。
- `D:/hy/watt-trace-owner-repair-artifacts-20261011/loss-regression`：当前为空，不能据此宣称回归完成。
- 原始冻结导出仍在 `C:/Users/yuchunbo/Downloads/Watt-Trace-Review-20261011`；原 ZIP 未改写。

由于 C 盘空间紧张，本任务旧输出已保留并搬到以上 D 盘目录，不清理其他用户文件、受管理工作区或 Docker 全局资源。

ECS 私有证据与脚本：`/data/watt/trace-analysis-releases/{0ad7bf83,ecc5c747,27cfcfd8}`。
`*.private.*`、完整 Docker inspect/ENV、Compose 配置可能含凭证，留在原私有位置，不提交到 Git、不输出凭证。
分析 CAS：`/data/watt/native-executor/trace-analysis`；不要篡改原始记录或擅自删除 `.active-investigation`。恢复前先确认是否存在、所属进程和职责。

两次最新资格容器交接时均 `exited 0`：`watt-trace-owner-qual-ecc5c747`、`watt-trace-owner-qual-27cfcfd8`。这表示进程退出，不表示报告语义 PASS；可在证据确认完整后仅清理本任务资源。

本任务的本机隔离测试容器/网络：`watt-trace-owner-pg-20261011` / `watt-trace-owner-regression-20261011`，DB `watt_trace_owner_test`，独立测试角色 `watt_trace_owner_test_runner`。
完整回归使用 `--import-mode=importlib`、`PYTHONPATH=/repo/src:/repo/tests/integration`、独立可写 native-executor 目录；避免再次把同名 integration 模块、只读 fixture 路径或错误 DB 用户造成的环境错误写成产品回归结果。
不要全局 prune 或停用 N1；只核对实际相关的 Watt 契约。
