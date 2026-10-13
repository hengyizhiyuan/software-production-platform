# Watt AI Native Evolution — Phase 0.5 Architecture Reality Assessment

评估日期：2026-10-13（Asia/Shanghai）。**评估记录，不是实现交付或 Runtime Conformance Qualification。C3 保持 PARTIAL。**

## 1. AI Native Architecture Principle

权威准则仍由 [Program ADR-0002 固定版本](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md)及 Watt [开发原则 §13/§14](ai-native-development-execution-principles.md#13-ai-non-determinism-principle-and-execution-discipline)拥有。本文用以下四个维度评估 Repository Reality，不建立另一份最高准则或改变 Owner 契约。

| 维度 | 本次检查的问题 | 必须保持的边界 |
| --- | --- | --- |
| Semantic Adaptation | 能否消费等价表达、不完整信息、多种合理解释及候选结构变化？ | 适应不等于允许错误版本、伪造引用、越权或协议不合法的对象直接晋升 |
| Reality Boundary | 是否区分 Fact、Observation、Inference、Claim、Evidence？ | 模型解释、存在记录、候选计划及自述均不单独证明履约 |
| Uncertainty Handling | 不知道、冲突、替代方案、需要更多信息是否可被准确表达？ | 未决不自动 PASS；等待未来合法 Gate 不等于未来动作已获授权 |
| Convergence Control | 是否有探索边界、进展判断、合法修复选择及停止条件？ | 保持 Owner、身份、累计预算、效果确定性和独立门禁；不能以无限再生取得成功 |

**复用确定性，驾驭随机性。** 严格 hash、Source Identity、权限、事务、Wire 协议和证据完整性是必要治理，不能因为其确定性就判为落后。智能模块应在这些边界内处理合法变化。并非每个模块都需要 LLM，也不要求每个 Owner 新增四个同名数据库状态。

### 1.1 成熟度解释

- **Level 0：** 仅消费固定输入，未见适用的智能变化处理。
- **Level 1：** 已有部分变化适配，但事实边界或不确定性处理尚不足。
- **Level 2：** 已有可识别的事实边界与不确定性处理；不能据此声称收敛完整、稳定或普遍合格。
- **Level 3：** 在明确责任和适用范围内，完整 AI Native Contract 的合法变化、事实边界、不确定性、恢复及停止已形成闭环，并有相应资格支持。

本次没有足够证据将任一**整个模块**判为 Level 3。大部分模块达到 Level 2，是因为已有的边界与状态确实存在；同一等级不表示同一可靠性。局部成功和严格权限子契约不能自动升级整个模块。

优先级采用本任务定义：**P0＝影响当前 C3 Closure；P1＝影响长期生产可靠性；P2＝长期优化。** 这是评估范围的排序，不重写 §13 的通用执行规则。

### 1.2 Exact Reality 与证据规则

| 对象 | 本次使用的真实版本 |
| --- | --- |
| 当前 C3 分支 / 评估起点 | `codex/c3-open-semantic-obligation-convergence` / `8891eeab6a1054166196606258bd2f2ebe45d118` |
| C3 应用源码 / Tree | `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0` / `c8ad5b06283905e218786ef785e940a82edd1dbf`；起点 HEAD 的 src/tests 无新差异 |
| C3 最近独立复验镜像 | `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1` |
| Guardian | `0d7aca954588c8ad3883dbedb730e59dc1d7b867`，实际独立 checkout 核对 |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c`，读取固定 Git 对象，不使用本机新 HEAD 替代 |
| Trace 独立分支 / HEAD | `codex/watt-trace-self-analysis` / `d378ddb6fd82ce687efa887f34c6664419a6df0c` |
| Trace 最近实测源码 | `bde096d210894f9d249e7b3e5545b9df16b0ebe5`；上述 HEAD 与该源码的 src/tests 无差异 |

Trace 已存在于独立分支，**并未因本文读取而集成到 C3 或部署**。不合并分支。旧未提交取证文件保持原状。

下文分别标识代码可见能力、已有实际失败和未取得的资格；不从错误标签推断根因。没有读取 Holdout 原输入/Oracle，也没有从 Holdout 制作实现规则。Phase 0 已读的八模块责任和源码依据沿用[既有评估](../evidence/core-production-semantic-convergence-c3-20261009/ai-native-hardening-phase0-20261013/assessment.md)，新增检查聚焦 Trace 实际分支与本次成熟度维度。

## 2. Module Gap Map

| 模块 | 当前职责 | 成熟度 | 已有边界/不确定性 | 已暴露事实 | 演进优先级 |
| --- | --- | --- | --- | --- | --- |
| WIC | Human 输入解释、候选语义/动作、IRK/Work 接纳前校验 | L2 | 候选与接纳 Fact、Authority、低置信/未决、有限修复 | 同一封存输入在复验中形成不同来源库存；语义等价未独立证实，不能据数量宣布丢失 | P0 基线待证；未确认 WIC 缺陷；一般适应 P1 |
| Planning / Steering | 受治理计划、下一步候选、Task/PWU 交接 | L2 | Source/目标/权限保持，NEEDS_REFINEMENT、Authority uncertain、Human Gate | 代码存在规则 Planner 回退；没有本次 C3 错拒合法计划的实测证据 | P1；当前仅保留受影响交接资格 |
| Formation | 从接纳 Reality 提出组件、Owner/Phase/证据方法并独立 Review | L2 | 精确来源、多组件、待证据绑定、UNRESOLVED、一次反馈/两次候选 | 最新真实泛化 0/4 接纳；全部未进入 Review；有界反馈执行但未收敛 | **P0** |
| Verification | 对确切产物和适用义务形成验证证据 | L2 | PASS/FAIL/UNKNOWN、UNVERIFIABLE，内容/Diff/治理分 Owner | 当前四条试次未调用；没有本次错误拒绝或错误放行证据 | P1；C3 受影响证据回归必须保留 |
| Self-Refine | 各 Owner 的候选修复、反馈、预算与停止 | L2，Owner 间不同 | 分类、血缘、有限次数、无进展/耗尽停止 | Formation 一次反馈真实发生但不收敛；不能以机制存在宣告恢复能力合格 | **P0：Formation 内部**；其余 P1 |
| Executor | Native 推理/工具循环、实际效果与产物、Checkpoint/恢复 | L2 | Claim/效果/验证分离，UNKNOWN effects、预算和控制动作 | 原 G0 有实际 Worker/Git 成功；最新泛化试次未进入 Executor | P1；不据未调用判缺陷 |
| Guardian | 独立核验软件与真实 Owner Evidence | L2，限现有契约 | PASS/FAIL_REPAIRABLE/BLOCKED，版本/来源/阶段独立核对 | 原 G0 独立 PASS/0 Findings；最新四条未调用，不能算新 Assurance PASS | P1；不重开已解决 Coverage 问题 |
| ECF | 权威上下文选择、投影、来源/新鲜度/冲突检查 | L2，限已注册契约 | READY/INCOMPLETE/CONFLICTED/STALE_OR_UNCERTAIN | 本次无 ECF 丢失 Protected Context 或错拒的已证实事实 | P1；扩展适用范围 P2 |
| Trace Analysis | 只读调查历史 Work，生成可追溯咨询报告 | L2，自动资格未通过 | Owner 引用、Observation/假设/UNKNOWN、有限调查及修订、自审 | 旧报告结构通过但语义 FAIL；最新 Native FAILED；辅助修订稿不替代自动成功 | **P1**，非当前 C3 新前置门 |

### 2.1 WIC

**A — 职责。** 在当前 Human 意图和权威上下文中提出语义及动作候选；经 IRK/Fact 绑定与 authority 校验接纳。回复表达不能创造产品决定或权限。

**B — L2。** 开放解释及有限结构/动作修复已存在。接纳前绑定、SYSTEM_INFERRED 权限限制和低置信处理证明其并非仅固定输入模块；尚无本次变化后的完整语义等价资格。

**C — 假设检查。** 输入：要求结构化协议，但语义来源允许模型解释。输出：未要求唯一拆分。偏移：已有校验和初次候选加最多三次修复，未假设模型永不出错。重试：有上限，部分指导依据错误文本选择，不能等同开放语义修复充分。完成：合法 IR 不等于目标已完成。

**D — 已暴露。** 复验新旧来源数量/描述不同；原输入 hash 和字段/出处连续性有收据。原目标、Scope、限定及禁止事项的语义等价目前 UNKNOWN。未证明 WIC 丢失事实。

**E — 建议。** P0：在非 Holdout 输入上证明语义连续性，允许合法拆分；有实际遗漏再改该 Owner。P1：评估现有澄清/低置信/冲突处理的真实有效性。P2：更广泛语言和表达覆盖，不成为新的 C3 完备性要求。

依据：[Provider](../../src/spg/providers/deepseek_interaction.py)、[接纳政策](../../src/spg/application/wic_intelligence.py)、[Fact 类型](../../src/spg/domain/engineering_semantics.py)。

### 2.2 Planning / Steering

**A — 职责。** 在已接纳 Work/Source/Capability/Authority 内提出计划和下一步候选，依据持久 Reality 推進，交接到 Task/PWU。

**B — L2。** proposal 与接纳计划分开；NEEDS_REFINEMENT、权限不确定、未证明完成与真实 Human Gate 已有表达。开放替代规划的完整资格未取得。

**C — 假设检查。** 输入：有明确 typed contract。输出：允许不同计划，但 governed objective、目标和范围保持原值。偏移：authority violation 会拒绝。重试：非法结构/权限扩张可回退规则 Planner，这能防扩权，不能证明开放任务的方案充分。完成：Steering 读取适用 Completion/Verification，不以存在计划判完成。

**D — 已暴露。** 规则回退和有限 graph/admission 约束是代码事实；尚无当前 C3 被其错误阻断的运行证据。Work READY、Runtime BLOCKED 与当前步骤投影不能不分字段含义地判为冲突 Bug。

**E — 建议。** P0：保持 Formation 未决停止与合法交接，不新增施工。P1：在有实际需求时验证替代路径、计划变化和回退的语义充分性。P2：更广开放规划；C4 高级恢复/Human 路由不在本轮。

依据：[Planning](../../src/spg/application/planning.py)、[Steering](../../src/spg/application/steering_decision.py)、[Runtime 前停止](../../src/spg/application/steering_production.py)。

### 2.3 Formation / WORK_FULFILLMENT_PROJECTION

**A — 职责。** 从接纳 Fact/Clause/IR Item/Work Constraint/Context 提出多来源、多组件履行计划；定位 Owner、阶段及证据方法，经过精确校验和独立 Semantic Review。方法有资格不等于证据已存在或义务已完成。

**B — L2。** 已有可逆库存、typed preconditions、组件身份、原文/版本/权限校验、BOUND_PENDING_EVIDENCE / UNRESOLVED / RETAINED_CONTEXT。真实构造和恢复仍未取得泛化资格。

**C — 假设检查。** 输入：已经支持不同来源与合法多组件，不应描述成固定单一语义。输出：最终 Wire 必须合法，但语义路线不要求唯一。偏移：Validator 和独立 Review 分离。重试：当前一次完整生成同时承担语义选择、引用/角色/证明操作数及编码，失败后有限再生成完整 Candidate。完成：接纳 Projection 不是当前履约 PASS。

**D — 已暴露。** 最近独立复验真实 0/4、受控负向 4/4；实际出现 Wire/Fact kind、安全 JSON 收据、组件矛盾和支撑来源对应证明拒绝，独立 Review 调用 0。未证明 Validator 错拒合法方案，也未证明四类失败仅有一个根因。

**E — 建议。** P0：在非 Holdout 固定 Reality 上证明合法方案可表达，再修本模块内角色准备、候选构造和有界反馈消费。语义选择与 Owner 可确定恢复的身份信息分工，是待验证方案而非已证实缺陷结论。P1：更多复杂联合义务可靠性；P2：在既有契约确实不足后才讨论更大形成策略，不预设分阶段新增调用。

依据：[Application](../../src/spg/application/governed_obligations.py)、[Provider](../../src/spg/providers/fulfillment_candidate.py)、[最近复验](../evidence/core-production-semantic-convergence-c3-20261009/holdout-requalification-20261013/report.md)、[已有职责分析](../evidence/core-production-semantic-convergence-c3-20261009/formation-responsibility-review-20261013/analysis.md)。

### 2.4 Verification

**A — 职责。** 针对确切源码/产物和当前适用义务产生内容、Diff、Source 或治理证据，由 SPG 判定证据是否可用于当前晋升。

**B — L2。** result 有 PASS/FAIL/UNKNOWN，内容检查有 CONTRADICTED/UNVERIFIABLE；检查计划可 Materialize/修复，原 Fact 不改。适用方法有限，不宣称任意行为验证。

**C — 假设检查。** 输入：确切 subject/basis 固定合理，表达可以变化。输出：同一要求可选择合法检查方法。偏移：引文/Scope/版本需机械核实。重试：修复的是检查计划/表达，不能把真实错误产物改成预期满足。完成：一个 Verification PASS 不等于整个 Work、Guardian、Human Acceptance 或 Delivery 完成。

**D — 已暴露。** 本次四条实际试次未进入 Verification。历史产物和权限证据已存在，但不能用于宣布新修订通过；没有新错误放行/错拒证据。

**E — 建议。** P0：保留受影响多组件/联合覆盖和当前/未来义务的证据消费资格。P1：按真实任务检验“引文确实支持断言”与行为方法的适用性。P2：扩大方法范围，但不把理论完备证明加入 C3。

依据：[证据接纳](../../src/spg/application/verification.py)、[内容检查](../../src/spg/providers/protected_context_verifier.py)、[Owner/阶段分流](../../src/spg/providers/managed_context_fulfillment.py)。

### 2.5 Self-Refine

**A — 职责。** 各 Owner 内的候选修复/再生/允许重试及真实停止；共享分类和观察不转移候选、authority 或 budget 所有权。

**B — L2。** 已有 AMBIGUITY、LOW_CONFIDENCE、CONTRACT/REALITY/EVIDENCE 信号、收据、重复签名及无进展/耗尽状态。局部机制成熟度不同，不是单一完整协调系统。

**C — 假设检查。** 输入/输出：可以修复合法临时候选，不能修权威事实。偏移：不要求零失败。重试：有次数/资源/效果边界，不能因多执行一次就认为有收益。完成：LOCAL_OBLIGATION_RECOVERED 与 Work 收敛明确不同；预算终止不能自动证明 Human 应改目标。

**D — 已暴露。** Formation 反馈实际执行但两次候选均不能接纳；这证明当前资格不收敛，不证明所有 Owner 的 Self-Refine 都失败，也不证明增加次数可以修好。

**E — 建议。** P0：修原 Formation 的反馈可消费性与合法修复选择。P1：按 Owner 核实重复签名、反馈身份和真实进展。P2：更完整经济度量/跨阶段策略留给原路线，不新增 Coordinator。

依据：[共享语义](../../src/spg/domain/refinement_contract.py)、各 Owner 的原有实现及 Formation 实际收据。

### 2.6 Executor

**A — 职责。** 在真实 Workspace、SourceVector、Task Contract、Native Binding、Effect Permit 内运行模型与工具，保留效果、产物、Checkpoint 和终态。

**B — L2。** Claim 与 Tool Observation/效果/后续 Verification 分开；未知效果被 fence，恢复有 EFFECT_UNRESOLVED、NO_EFFECT、PARTIAL、STALE、LOST 等分类。

**C — 假设检查。** 输入：身份/权限严格，工具和计划可在授权内变化。输出：实现步骤无需唯一。偏移：InferenceDecisionRejected 和工具失败可进入有界反馈。重试：效果不确定不能重复执行，未变化源码观察不能购买新收敛预算。完成：RESULT_READY/result_claim 不是 Verification、Guardian 或完整 Work PASS。

**D — 已暴露。** 原 G0 有真实 Worker/Git 资格；最新四条未调用。Trace Native 最新未完成且终态前报告工具为空，但完整触发机制未核查，不能直接宣布 Kernel 缺陷或预算耗尽。

**E — 建议。** P0：维持当前 C3 真实执行边界，只有实际新 Executor 缺陷证据才施工。P1：证明已知恢复路径对合法变化有效，保留效果/预算连续性。P2：更广任务执行能力。

依据：[Kernel](../../src/spg/executor/kernel.py)、[恢复分类](../../src/spg/executor/recovery.py)、[Worker](../../src/spg/infrastructure/executor_runtime/worker.py)。

### 2.7 Guardian

**A — 职责。** 独立核验真实 Owner Evidence 与软件行为，判断来源/版本/生命周期阶段及义务证明是否有效。

**B — L2（现有契约内）。** PASS / FAIL_REPAIRABLE / BLOCKED 和独立 resolver 已存在；缺证据不放行。整个模块的开放语义适应不能由局部 Assurance PASS 推断为完整 L3。

**C — 假设检查。** 输入：真实证据 contract 严格，Watt COVERED 不足以证明。输出：多种合法方法可在已有契约内消费，不要求实现唯一。偏移：模型 Review 也要核对实际 receipt/basis。重试：修复由生产 Owner 承接，Guardian 重新独立核验。完成：Guardian PASS 不授予 Human Integration、Acceptance 或 Delivery。

**D — 已暴露。** Coverage 历史阻断已修复；原 G0 实际独立 PASS/0 Findings。最近四条试次未调用；不能将未调用归因于 Guardian，也不能把受控负向夹具替代实际 Assurance。

**E — 建议。** P0：保留原 Gate，不重开已解决阻断。P1：按真实方法覆盖和 evidence origin 验证扩展需求。P2：更广独立 Assurance，未纳入 C3。

依据：[固定 Guardian runtime](https://github.com/hengyizhiyuan/guardian/blob/0d7aca954588c8ad3883dbedb730e59dc1d7b867/src/guardian/runtime.py)、[实际覆盖恢复](../evidence/core-production-semantic-convergence-c3-20261009/guardian-coverage-recovery-20261012/report.md)。

### 2.8 ECF

**A — 职责。** 消费既有权威来源，按 Decision Type/Scope/Authority 投影上下文，核对来源、新鲜度、缺类、冲突及 lineage。

**B — L2（注册契约内）。** GOVERNED/PROJECTION 和 current/historical 状态不同；READY、INCOMPLETE、CONFLICTED、STALE_OR_UNCERTAIN 明确存在。模型生成 Approved Fact 不是其恢复方式。

**C — 假设检查。** 输入：Context Class 与 surface 有有限注册契约，不证明任意语义覆盖。输出：选择受来源/权威限制，不产生独一实现要求。偏移：Watt 消费时检查指纹/版本变化。重试：缺类/冲突需要合法来源或请求责任修正，不能概率补齐 Authority。完成：Context READY 不等于 Work 或义务完成。

**D — 已暴露。** 本次未有新 ECF 错拒、受保护上下文漏保的实测证据；有限 taxonomy 是代码事实，不自动等于平台缺陷。

**E — 建议。** P0：保持已资格来源与保护，暂无新施工依据。P1：在真实新增决策场景评估请求类别和来源投影适用性。P2：扩展范围须基于现有 ECF Owner 契约，不构造第二套语义中枢。

依据：ECF 固定提交的 `src/ecf/decision_context.py`（本机 Git 对象读取），[Watt consumer](../../src/spg/application/decision_context.py)。

### 2.9 Trace Analysis（独立分支已存在）

**A — 职责。** Human 触发只读历史 Work 调查；冻结脱敏 snapshot、查询原始 Owner 关联与精确 Git，形成咨询性报告、修订和自审。不能重放生产、修改 Work、生成授权、部署或自升级。

**B — L2，自动资格未通过。** 观察、根因假设、UNKNOWN 和建议有 typed contract；只引用实际读取的片段，缺字段/未导出不证明历史删除；草稿和自审均不构成独立 Assurance。

**C — 假设检查。** 输入：冻结 evidence 存在纯文本、嵌套 JSON、部分读取和不同 Owner，已实现分页/inspect/field 引用。输出：原文引文与字段引用均可表达；叙述不必唯一。偏移：submit/revise/review 和稳定反馈存在。重试：不是仅完整再生成，支持草稿显式编辑；探索/提交/自审预算已有规划和工具选择。完成：CITATIONS_AND_STRUCTURE_PASS 明确不证明语义蕴含，Native 自审也不是独立 Assurance。

**D — 已暴露事实。**

1. 较早 `27cfcfd8` 的 Native 请求 COMPLETED/RESULT_READY，结构引用 PASS，但独立语义复核 FAIL：将某字段未导出扩大为历史响应已丢弃的前提。是实际“结构通过不能证明语义正确”，不是推测。
2. 本阶段已修正的纯文本导航缺陷：`field_navigation` 曾对纯文本再 `json.loads`，使真实字段拒绝被导航异常覆盖。后续改为消费已捕获类型值，不能再作为当前未修复项。
3. `53af5abc` 草稿结构引用通过，自审来源集合不匹配并最终超时；后续已由不可变草稿 Owner 绑定可确定引用集合，显式错误 ID 仍拒绝。不能继续要求模型重复抄写身份作为唯一方案。
4. 最新 `bde096d2` 请求 `1a9c6de8-8aea-4b80-aea9-e78331dcdd61` 为 **FAILED / UNABLE_TO_COMPLETE**，9 次推理、26 次工具；出现字段定位、占位草稿、缺 EXECUTION 时间线及乱序问题。原预算 12 次推理、48 次工具、600 秒。模型终态前报告可用工具为空，完整触发原因仍 UNKNOWN；不把它直接归因于预算太小或 Kernel 错误。
5. 最新交付是 **Watt 草稿经 Codex 辅助修订**的单事件报告；254 Python/35 JS 回归通过不替代 Native 自主资格。原失败未被覆盖，未部署。辅助修订者/自审者也不是独立 Human Governor。

**E — 建议。** P0：不把 Trace 完整自动分析升级为 C3 新关闭条件。P1：在独立 Trace 任务中核对探索→草稿→修订→自审→终止的实际剩余资源、合法工具和进展；准确表达 UNKNOWN，不将语义不足交给引用匹配掩盖。只在实际证据证明选择/接线缺口后修原模块，保持原预算。P2：多事件和更广调查，先于此不追求全历史完备。

固定来源：Trace 分支 `d378ddb6fd82ce687efa887f34c6664419a6df0c` 的 [最低交付与边界](https://github.com/hengyizhiyuan/software-production-platform/blob/d378ddb6fd82ce687efa887f34c6664419a6df0c/docs/architecture/work-trace-self-analysis-minimum-20261013.md)、[资格收据](https://github.com/hengyizhiyuan/software-production-platform/blob/d378ddb6fd82ce687efa887f34c6664419a6df0c/docs/evidence/work-trace-self-analysis-minimum-20261013/qualification.json)、[Application](https://github.com/hengyizhiyuan/software-production-platform/blob/bde096d210894f9d249e7b3e5545b9df16b0ebe5/src/spg/application/trace_analysis.py)、[证据/报告工具](https://github.com/hengyizhiyuan/software-production-platform/blob/bde096d210894f9d249e7b3e5545b9df16b0ebe5/src/spg/infrastructure/trace_analysis_evidence.py)。

### 2.10 四维能力与状态表达对照

| 模块 | Semantic Adaptation | Reality Boundary | Uncertainty Handling | Convergence Control |
| --- | --- | --- | --- | --- |
| WIC | 开放解释、澄清/修复；本次等价待证 | Fact candidate→接纳，原出处/Authority | 低置信/未决；澄清不等于所有替代解释已保存 | 初次加最多三次修复，受 Owner 校验 |
| Planning / Steering | 候选图/计划可变，规则回退范围有限 | proposal/接纳计划/Reality 分离 | NEEDS_REFINEMENT、权限不确定、Human Attention | 有限回退、当前 Reality 检查；非开放搜索资格 |
| Formation | 多来源/组件支持；真实构造不收敛 | 候选/Review/绑定/履约证据分离 | UNRESOLVED、待证据、Context retained；冲突拒绝 | 两次候选/一次反馈；实际有效性不合格 |
| Verification | 方法计划 Materialization 与修复 | 适用证据、确切 subject、原 Fact 不变 | UNKNOWN、UNVERIFIABLE、CONTRADICTED | 表达修复有界，真实产物错误不消除 |
| Self-Refine | 合法临时候选修复，各 Owner 不同 | 修复不授予新 truth/authority | ambiguity、low confidence、evidence insufficient、non-converging | 信号/血缘/预算/停止存在，不能以次数替代进展 |
| Executor | 授权内多工具/实现路径及原循环 | Claim、观察、效果、Git/验证分离 | UNKNOWN effects、残余义务、恢复分类 | 推理/工具 envelope、无进展、checkpoint fencing |
| Guardian | 既有方法/组件证据独立消费 | caller claim≠Owner proof≠Human authority | BLOCKED/repairable Findings 保留缺证据原因 | 原 Owner 修复后独立再核验，无自行放行 |
| ECF | 已注册 Scope/类别中的合法投影 | Source/Authority/GOVERNED/PROJECTION | INCOMPLETE、CONFLICTED、STALE_OR_UNCERTAIN | 合法源刷新/请求修正；不生成批准事实 |
| Trace | 多种证据结构、分页、引用/字段、显式修订 | Observation/假设/草稿/自审/咨询分离 | UNKNOWN、捕获不全、SUPPORTED/QUALIFIED/REVISE | 预算观察与提交/自审路径存在，自主成功未证明 |

ALTERNATIVE 与 NEED_MORE_INFORMATION 不一定是独立 enum。当前候选变化、未决或澄清只能证明相应能力，**不自动证明持久保存多个解释、比较替代方案或主动获取必要证据已完整闭环**。没有这项完整资格，不意味着应立即给九个模块增加统一状态机。

## 3. C3 必需 Hardening 范围

1. **输入连续性证明。** 非 Holdout 已知输入→接纳 Reality 的目标、Scope、值/顺序、限定、禁止事项与阶段语义不丢失；不要求同一来源数量或拆分。
2. **Formation 内构造与有界恢复。** 在原 Owner 内区分开放语义选择、来源/证据角色、可确定编码和合法修复。先证明合法方案可表达，再依据共同缺口修复；不把正确 Validator 拒绝改为系统 Bug，也不把错拒伪装为模型方差。
3. **必要证据与独立 Gate。** 针对受影响接口保留内容、Diff、Source、持续禁止、未来 Gate 和 Context retention 的正负验证；当前证据不足不 PASS。冻结 exact source/image 后取得原 Mission 要求的实际链路与独立泛化资格。

当前 P0 在 Formation 及其 Owner 内恢复；WIC 为必要基线待证。未调用的 Verification/Executor/Guardian/ECF 不自动新增施工义务。Trace 的完整自动收敛保持独立任务，不新增 C3 验收条件。Human Integration/Acceptance/Delivery 均依真实原 Gate 与原 Closure Contract，不把本评估当作授权。

## 4. 长期演进方向与实施顺序建议

### 4.1 建议顺序

| 顺序 | 范围 | 进入依据 |
| --- | --- | --- |
| 1 — P0 | 非 Holdout 固定 Reality 的合法多来源/多组件方案与失败对照 | 证明是契约缺口、模型偏差、反馈消费还是正确治理拒绝 |
| 2 — P0 | Formation 内最小构造/修复变更及受影响接线 | 已证实共同缺口，复用原 wire/view/locator/receipt，不增预算 |
| 3 — P0 | 定向回归、受影响 PostgreSQL/Owner 验证、确切版本真实资格 | 符合原 Mission；局部 PASS 不代替实际生产和独立泛化 |
| 4 — P1，独立范围 | Trace 的探索/提交/修订/自审合法路径和语义边界 | 已持久失败与预算观察；先查确切原因，辅助报告不是自动 PASS |
| 5 — P1 | Planning/Verification/Executor/Guardian/ECF 的适用范围 | 真实生产需求与 Owner 证据表明能力缺口时推进，不同时重构 |
| 6 — P2 | 更广替代方案、调查范围、成本与可靠性覆盖 | 已有 P0/P1 路径取得相应资格后安排 |

### 4.2 演进方法

- 在现有模块契约里描述合法变化、保留不变量、可修复偏差、证据需求、实际进展和终止，不默认新增类型/表/Owner。
- 同一目标的不同方案可被验证；原 Fact 和权限不变。由已有 Owner 确定恢复的引用身份不必强迫模型重复转写，但明确提交的语义选择不得被自动补造。
- 准确区分“目标不满足”“不同实现但满足”“当前证据不足”“多种解释待选择”。必须知道的权威事实缺失时等待/停止；不能把未知当默认值。
- 评估收敛要看合法接纳、必要证据和剩余义务的真实变化，不看提示长度、规则数量、重试次数或报告数量。
- 局部变更→局部验证；关联改动→聚焦回归；确有责任/接口变化→相应较广资格。稳定版本仍履行原强制门，避免每次微调跑全库。

这些是已有原则的适用建议，不为当前九个模块宣布新完成标准，不证明当前 Runtime 全面合规。

## 5. 不做事项与退出事实

- 不修改代码、测试、Schema、Runtime、模型配置、预算或部署。
- 不放宽 Validator/Guardian，制造 Evidence、Human Decision 或完整审计。
- 不增加 Subject Alias、业务特例、Holdout 规则或 Prompt 禁令追逐失败样例。
- 不增加万能 Adapter、Normalizer、全局 Refine Coordinator、第二个语义中枢或生产编排系统。
- 不修改 Holdout、原事故 Work、历史 Evidence、封存 Candidate 或 Production Reality，不重放生产结果。
- 不因本评估自动集成 Trace、不启动 C4/N1/N3，不将辅助调查报告算作 Watt 自动资格。

本次仅生成本架构评估文档；模型调用、测试运行、镜像构建、资格运行、生产变更均为 0。未新增任何 PASS。**C3 PARTIAL；Formation 泛化收敛仍未合格；Trace 自主稳定分析未建立。** 后续工程需要针对已证实的现有 Owner 缺口，不将设计建议改写为已实现事实。
