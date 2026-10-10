# C3 — Source Coverage & Owner Evidence Preconditions Calibration

状态：**本轮有界契约修复及受控资格完成；C3 PARTIAL。**

取证时间：2026-10-10T05:20:24.504147+00:00。继续原 `codex/c3-open-semantic-obligation-convergence` 分支；由 Human 与 Codex 共同推进。历史架构审查材料保留为历史，不新增审批角色。

## 1. 原因与证据等级

| 已证实问题 | 原始证据与边界 |
| --- | --- |
| 支持引用不等于完整组件绑定 | 原两次 29 Route 候选中，来源 9、10、12 只有 `u` 支持引用，没有自身 `s` 路线、组件跨度及处置。`u` 是来源对应证明的引用列表，不包含被引用来源的独立组件计划。文本相同不能合并 Fact / Clause / Constraint 的身份或权限。当前业务意义是否完整等价仍 UNKNOWN，独立 Review 从未运行。 |
| 来源集合不符合 Work Owner 前提 | 原 Route 11、source 15 引用 `[9,10]`，逐项直接对应为 `[true,false]`；Route 12/13、source 17/18 的相同引用集合则是 `[false,true]`。已有 `work_constraint_sources_correspond` 要求全部选中支持合法对应，不能用一条正确引用许可另一条无关引用。生产排除要求还必须通过已有 exclusion + 原始 NEGATED Clause + 正确组件/阶段的组合证明。所有原 11 条 Work Constraints 具备进入已有证明分支的必要前提，不是已证明的通用能力缺失。 |
| Scope Evidence Owner 错配 | 原 Route 22 将来源 3 的精确文件 Scope Fact 送往 `ARTIFACT_CONTENT`。已有带限定条件的文件范围契约要求 `EXACT_GIT_DIFF_SCOPE`，HTML 内容不能证明 Git 修改范围。原 Owner 拒绝是正确的。 |
| 同一次反馈缺少可评估的后续 Owner 错误 | 严格 Wire 解码先因来源覆盖失败终止，原反馈将 `OWNER_PHASE_EVIDENCE` 整体标为不可评估；因此 Scope、引用对应、权限原始 Clause 和处置冲突未传入该次修复反馈。此实现缺口可以修复，但不能据此证明模型收到完整反馈后一定会收敛。 |

证据等级：原始输出/库存/持久收据为保留的观测事实；本轮 exact-image 只读重放为确定性契约证明；Fixture 为受控回归。模型内部推理原因、修复后的实际模型成功、旧工作业务语义完整性仍未得到资格。

两次原输出 fingerprint：

- `c284188fa79f1d59840abe30ada227600af39c0b010cad1a19e5b844fbf46297`
- `c9556f29b825ee22d997b026e5171df12ab0a377e8d46d60a8c05b7defda7eda`

库存 fingerprint：`7c67a051be3bfa873767a417ead82e9c8e43888d42ded7592de1d945f9e99dcf`。完整私有来源和输出未复制到 Git。

## 2. 最小修改与保留的门禁

- `fulfillment_candidate.py`：复用同一个单 Route 元数据展开器；严格完整解码仍检查全部来源覆盖。新增只读 Route 观测用于诊断，不能返回部分合格 Candidate。明确 `u` 不产生被引用来源的组件处置，不合并相同文本的来源身份。
- `governed_obligations.py`：复用原来源对应谓词和原 `_projection_binding`，向既有一次反馈附加 `owner_repair_context`。包含原 Route 的稳定错误、原始对应来源序号、文件 Scope 的必要证据方法及既有权限/阶段前提。不生成路线、不修补历史 Candidate、不提供权威证据或 PASS。
- 新反馈与原始 Wire fingerprint、库存、Attempt、请求/响应持久收据绑定，恢复时重算。已有 Owner 收据增加窄范围契约标记，拒绝移除整个新反馈上下文进行历史格式降级；旧无标记收据继续使用旧格式。
- 异常、版本漂移、非法索引、假引文或无法定位的 Route 不可作为证明；缺少完整兄弟 Route 时，背景资格标记 `NOT_EVALUABLE`。完整计划接纳、独立语义 Review、实际 Owner Evidence、Guardian Assurance 始终不能由只读诊断替代。
- 不改变 Wire v1 / Schema fingerprint / 索引空间 / 正式绑定结构。仍最多两次 Formation、一次反馈、每候选最多一次独立 Review、最多四次逻辑调用；Token、传输、超时及累计预算策略不变。
- Guardian / ECF 正式契约和源码未修改。新字段是 Work Owner 的失败观测与反馈；最终合格绑定继续通过原正式契约及独立 Guardian。

## 3. 精确身份与验证

| 对象 | 确切身份 / 结果 |
| --- | --- |
| Watt 应用源码 | `9846bddee5b63cfa427a3ec70828b5e5180480fc` |
| Watt Git Tree | `8266956ec3af7d4907c85654a58f63615398c253` |
| 新隔离镜像 | `sha256:7c9e3782d985ec93c72b3d71d7fa24b2b10fc1123305119cdbc6c64687faca82` |
| Guardian | `76c1e87a1b29d151f4ed949748e3298f2169c5b1` |
| ECF 实际导入版本 | `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| 镜像构建 / 实际导入身份 | PASS；新构建，未覆盖旧镜像中的文件 |
| exact-image 相关回归 | **325 PASS，0 FAIL / ERROR / SKIP** |
| 新隔离 PostgreSQL + Watt/Guardian 联合契约 | **37 PASS，0 FAIL / ERROR / SKIP**；其中 15 项 C3 持久化恢复检查、22 项 C1 Guardian/Gate 保护 |
| Migration | `20261007_72`，仅新建隔离 Fixture 数据库 |
| 原两次失败 exact-image 只读重放 | 仍 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`；原收据未修改，所有绑定仍 UNRESOLVED，0 模型调用 |

正向：小/中/复杂库存能在一次完整绑定反馈后，产生新的合法 Fixture Candidate 并经过独立 Fixture Review；合法来源支持保留自身完整组件。负向：支持引用替代覆盖、错误文件 Scope Owner、无关来源混入、非法/漂移版本及引用、伪造引文、缺失证据、非法压缩、处置冲突和反馈篡改持续被拒绝。实际 PostgreSQL 恢复不会重置预算或重复请求。

Guardian 联合检查使用其实际冻结源码，确认原独立 Owner 记录核验、未来 Human Authority 与禁止 Deploy/Publish Gate 保持有效；执行器和推断使用受控 Fixture，**不算真实 AI Work / G0 / 真实 Candidate 生产资格**。

开发收据完整保留：54 PASS → 233 PASS → 55 PASS / 1 FAIL → 56 PASS。开发第三次失败来自新增 legacy fixture 只删去部分绑定标记、未同步恢复旧诊断 fingerprint；仅修正该测试的旧格式构造，最终镜像全部通过。不得抹去该失败或把开发覆盖式测试算成 exact-image 资格。

## 4. 成本、历史与生产保护

本轮真实模型请求、真实 Review、Token 消耗、新真实 G0 均为 **0**；只运行受控模型替身。一次镜像构建 17.335 秒；exact-image 回归 12.775 秒；隔离 PostgreSQL 180.391 秒。CPU 实际累计用量、金额为 UNKNOWN。各进程存在并行，不能将进程 wall time 之和冒充任务总耗时。

没有提高预算、增添候选次数、Subject Alias 或业务特例，没有修改 R1/R2/R3、历史 Work/Candidate/Human Decisions/Quality Ledger。未解封 Holdout，未启动 C4/N1/N3。原生产源码 HEAD `5de657f3cb65780adf50f6557b54171a6c3cfae5` / canonical main ref `ee5bd86a53891f9391785c91d0ccef81ad2d56c3` 保持原样；Watt 远端 main 本轮起点为 `5b7bf217937d7e002c0264c3fe9fdd518dba152c`，本轮未向 main 推送。

## 5. Closure Delta 与下一项必要动作

已消除：覆盖失败遮蔽其他可评估 Owner 错误；反馈未说明支持引用与自身覆盖的差异；原始对应来源及 Scope 证据前提未形成可复核的结构化修复信息。已资格：绑定、防漂移、历史格式兼容、受控修复与独立 Owner/Gate 保护。

仍未消除为真实成功：旧两次 Candidate 的覆盖/来源/Scope/权限/处置错误。仍 UNKNOWN：模型能否利用本修复在既有预算内收敛，以及业务语义是否完整。**不修改这些失败结果，也不宣告 C3 CLOSED。**

下一项必要行动：在本确切源码/镜像与原 26 项完整库存上进行限定真实 Formation/独立 Review 验证，沿用原停止条件及累计预算，不重跑 G0 碰运气。只有形成与独立 Review 合格后，才有依据继续对应正常生产资格；Holdout 仍封存。本轮没有发起这项模型验证。

## 6. 跨电脑恢复

- Git：本目录及原 C3 分支保存公共证据、控制器、SHA256 清单；最终证据提交由远端核对收据记录。
- ECS：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-owner-calibration-20261010`，包括 final-inputs、exact-image 回归、独立 PG 收据、只读诊断、完整新镜像导出、public-delivery 和最终检查点。
- exact image 导出：`/data/watt/c3-semantic-convergence-20261009/semantic-contract-implementation-20261010/source-owner-calibration-20261010/image-recovery/exact-image.tar.gz`；SHA256 `58449363dc57166a2d392cd65e22beba194e62caa1d14cf24ab3e880b31a4e00`；336607538 bytes。未执行 restore-load，未做离站备份。
- 完整原私有库存/输出：相邻 `repair-context-live-1/private/model-observations/`，权限隔离，不进入公共 Git。

关键收据：[构建](receipts/final-image/evidence/build.json)、[325 项回归](receipts/final-image/evidence/watt-continuation-receipt.json)、[37 项 PostgreSQL / Guardian](receipts/owner-pg-final/evidence/receipt.json)、[确切镜像只读分析](receipts/readonly-analysis-exact/analysis.json)、[成本与尝试](cost-and-attempts.json)、[证据 SHA256 清单](receipts/manifest.json)。
