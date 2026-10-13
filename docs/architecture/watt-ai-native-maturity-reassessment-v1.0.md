# Watt AI Native Maturity Reassessment v1.0

2026-10-13（Asia/Shanghai）。Phase 0.5，**仅架构重评；C3 状态仍为 PARTIAL**。

## 1. Executive Summary

评估依据为已批准的 [AI Native Architecture Standard v1.0](watt-ai-native-architecture-standard-v1.0.md)，不是以没有失败、已有 LLM 调用、Schema 或测试数量证明成熟度。

**Watt 已具备 AI Native System 雏形：候选接纳、权威来源、证据与权限门、未知效果保护、有限反馈/修复/停止均实际存在。尚不能认定整个系统或任一整个核心模块达到 Level 3。**

本次仍将九个模块判为 **Level 2，范围与资格不同**。依据是正面的代码/收据证明：存在 Reality Boundary、Evidence 管理、不确定性及基础有界机制，而不是未见失败。Level 2 不代表完整符合四项 Contract，也不保证生产泛化。各模块未证实部分在矩阵中保留 Unknown。

- **Formation / Self-Refine Convergence：** 有受控多组件表达与严格接纳，最近真实泛化仍未收敛；是当前 P0。
- **Trace：新增进展。** 本次核对到上一评估之后的独立分支新提交：一条 Native 调查在两次来源反馈后自行完成、没有人工改写报告，限定复核通过。不能继续将“只有辅助报告、Native 尚无成功”作为最新事实，也不能从单条成功推导自主稳定性或全语义正确。
- **WIC、Planning、Verification、Executor、Guardian、ECF：** 分别已有机制与局部资格；等价表达、多解释、信息不足和恢复有效性的组合资格不完整。缺少失败记录不构成成熟度证明。
- **Phase 1 应先演进：** 原 Formation Owner 内的合法候选构造、来源/证据角色消费及有界修复的真实进展判断。先用非 Holdout 证明共同缺口，不增加 Prompt、特例或接受范围；不同时重构九个模块。

### 1.1 Repository Reality

| 对象 | 本次实际读取身份 |
| --- | --- |
| C3 分支 / 起点 HEAD | `codex/c3-open-semantic-obligation-convergence` / `3fbbadfb46ede7ae6cd953224881a46ddc3a090c` |
| C3 应用 / Tree | `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0` / `c8ad5b06283905e218786ef785e940a82edd1dbf`；起点 src/tests 无新差异 |
| 最近 C3 复验镜像 | `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1` |
| Guardian | `0d7aca954588c8ad3883dbedb730e59dc1d7b867`，实际 checkout 核对 |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c`，按固定 Git 对象读取 |
| Trace 分支 / 起点 HEAD | `codex/watt-trace-self-analysis` / `6aada04010631b6833b9b9487addb11f9ec36f6b` |
| Trace 新实测源码 / 镜像 | `e207b92ce7b6a670bd48e4a58639593447262637` / `sha256:2968973bd2554b27c8c1d71996cac917e7146df700702a96445ad05729131d9e`，来自该分支持久收据 |

Trace 仍是独立分支；其新部署来自另一任务已保存的记录，**本次没有部署、合并或修改该分支**。旧评估按其时间保留。本次只新增指定文档，保留原未提交取证文件。

### 1.2 Status 与证据含义

- **Confirmed：** 所列明的具体能力有正面代码/既有行为收据支持；必须阅读 Evidence 中的版本和范围。并不表示整个维度在任意输入上完整合格。
- **Observed Risk：** 已观察到失败，或实现中可核对的限制/耦合；不将风险自动升级为已证实 Bug，也不把历史问题冒充当前未修复问题。
- **Unknown：** 对该能力的重要部分没有足够适用证明；不能用机制存在或没有失败替代。

代码、测试定义、受控执行、真实模型执行及独立复核分别标识。读取测试代码不是本次运行测试。较早版本资格不能冒称冻结新版本通过；矩阵不新增任何资格结果。严格身份、权限和协议不是应消除的传统假设，问题是智能模块能否在其内合法适应。

## 2. Overall Maturity Matrix

| 模块 | Level | Semantic Adaptation | Reality Boundary | Uncertainty Handling | Convergence Control | 优先级 |
| --- | --- | --- | --- | --- | --- | --- |
| WIC | 2，边界能力已有 | Unknown | Confirmed | Unknown | Unknown | P1；C3 输入语义基线需先证明 |
| Planning / Steering | 2，受治理候选已有 | Observed Risk | Confirmed | Unknown | Unknown | P1 |
| Formation / WORK_FULFILLMENT_PROJECTION | 2，构造泛化未合格 | Observed Risk | Confirmed | Confirmed，限未决/待证据处置 | Observed Risk | **P0** |
| Verification | 2，适用证据分流已有 | Unknown | Confirmed | Confirmed，限既有结果/方法 | Unknown | P1 |
| Self-Refine | 2，Owner 内基础机制 | Observed Risk | Confirmed | Confirmed，限已有信号/分类 | Observed Risk | **P0：收敛** |
| Executor | 2，Native 边界/恢复已有 | Unknown | Confirmed | Confirmed，限效果/恢复 | Unknown | P2；真实阻断出现仍必须处理 |
| Guardian | 2，独立 Assurance 已有 | Confirmed，限已资格 v3 消费 | Confirmed | Confirmed，限既有 Findings/Gate | Unknown | P1 |
| ECF | 2，来源/上下文边界已有 | Unknown | Confirmed | Confirmed，限注册上下文 | Unknown | P1 |
| Trace Analysis | 2，新 scoped 自主成功 | Confirmed，限单事件调查/反馈 | Observed Risk | Confirmed，限已审报告 | Confirmed，限一条 Native 链 | P1 |

这里的 Level 不取四列平均数。Level 2 的底座存在与 Level 3 的完整适应/自主可靠性是不同判断。特别是多种解释的保留与选择，以及 ALTERNATIVE / NEED_MORE_INFORMATION 的实际闭环，不能由 UNRESOLVED 枚举或多个生成尝试代替。

## 3. Module-by-Module Assessment

### 3.1 WIC

**A — Current Responsibility。** 输入为 Human Turn、已有 Product/Work Reality、来源/上下文 basis；输出语义、动作和 Fact 候选，以及经现有 IRK/Work Owner 接纳后的结果。WIC 不直接授予执行或 Human 权限；下游 Planning/Formation 消费接纳 Reality。

**B — Level 2 依据。** 代码存在候选→校验→接纳，限制 SYSTEM_INFERRED 的权限；非法模型结果不会创建治理事实。既有真实 WIC 失败记录证明 malformed 输出终止而未创建 Assessment/Work。结构/交叉引用修复有受控路径。未达 L3：本次不同来源拆分的语义连续性未独立证明，多解释/缺信息处理和真实修复策略的完整资格不足。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Unknown | 开放模型解释与澄清机制存在；最近相同封存输入生成不同来源库存，语义等价仍 UNKNOWN；不得以数量不同宣布丢失或正确 |
| Reality Boundary | Confirmed | Fact candidate 绑定与 Authority 校验；历史 invalid JSON 为 TURN_FAILED，未从被拒输出创建 Work。仅证实这些边界，不证明所有内容忠实 |
| Uncertainty Handling | Unknown | low-confidence、未决、Human 决策/澄清结构存在；保存/比较合理解释及不足信息闭环的适用证明不全 |
| Convergence Control | Unknown | 最多三次结构/动作修复的代码及受控案例可见；历史一次手工重新提交成功不算模块内恢复；开放语义进展与策略选择仍未完整证明 |

**D — Deterministic Assumption Inventory。** 严格结构化输出是协议要求；部分修复指导按错误文本分派，仍需验证新类型反馈的可消费性。字段/引用合法不能证明原意完整。没有证据表明 WIC 要求唯一语义拆分或允许模型直接改 Reality。

**E — P1。** 非 Holdout 的原意/Scope/限定/禁止/阶段连续性是 C3 必要基线检查；若发现遗漏才修原 Owner，不因 Unknown 自动重构 WIC。

来源：[WIC Provider](../../src/spg/providers/deepseek_interaction.py)、[Fact 类型](../../src/spg/domain/engineering_semantics.py)、[接纳绑定](../../src/spg/application/engineering_semantics.py)、[历史实际失败](../evidence/wic-interaction-intelligence-phase-closure.md)、[复验分层边界](../evidence/core-production-semantic-convergence-c3-20261009/holdout-requalification-20261013/report.md)。

### 3.2 Planning / Steering

**A。** 输入接纳 Work、Source Baseline、变更合同、Capability 与当前 PlanFrame/Reality；输出生产计划 proposal、图/步骤和下一步候选；治理接纳后交接 Task/PWU。完成和 Human Gate 由持久证据决定。

**B — Level 2。** Authority/Source 不可由 proposal 扩张，NEEDS_REFINEMENT、权限不确定及 Completion Evidence 均有表达；既有受控治理及较早生产收据支持局部基础。未达 L3：规则回退不证明理解合法替代方案，多解释、信息充分性及自主计划修复的资格未完整建立。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Observed Risk | `ProductionPlanningService` 对 ValueError/authority violation 回退 RuleBasedProductionPlanner；图/PWU admission 有有限范围。代码限制可见，但未证实当前 C3 错拒合法计划 |
| Reality Boundary | Confirmed | 原 objective、Source、targets、constraints、scope 不可被 proposal 更改，计划与接纳、实际完成分开；历史受控治理有对应记录 |
| Uncertainty Handling | Unknown | NEEDS_REFINEMENT、unresolved questions、Authority uncertain 存在；多方案比较/保留及缺信息的自主取得路径尚无完整资格 |
| Convergence Control | Unknown | bounded fallback/recorded refinement 已实现，较早受控路径可用；不能从回退未越权证明真实方案充分，也不能以旧资格覆盖新组合 |

**D。** 有限 graph/能力/路径规则；遇非法候选回退规则方案。严格保留目标文字是 authority 边界，不要求实现步骤相同。未证明存在“计划记录＝完成”的自动晋升。

**E — P1。** 先保护合法 Task/PWU 交接与未决停止；当实际需求暴露替代路径缺口，再改原计划 Owner。C4 高级恢复与决策路由不引入本轮。

来源：[Planning](../../src/spg/application/planning.py)、[Steering](../../src/spg/application/steering_decision.py)、[未决停止](../../src/spg/application/steering_production.py)、[既有分 Owner 收据综述](../evidence/stability/system-wide-stability-closure-20260927.md)。

### 3.3 Formation / WORK_FULFILLMENT_PROJECTION

**A。** 输入接纳 Fact/Clause/IR Item/Work Constraint/Context、精确库存/Source 和 Capability Contracts；输出候选组件/route，经精确 Validator 与独立 Review 形成待履行 Binding。下游 Verification/Native/Candidate/Human Owner 提供实际证据。

**B — Level 2。** 多来源/多组件、原文引用、Owner 前提、独立 Review、库存身份/反馈血缘和 UNRESOLVED 均实际存在；受控正负证明可表达并拒绝非法来源/证据。未达 L3：真实模型未构造出合格 Projection，恢复有执行但不收敛。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Observed Risk | f52d3996 安装态 15 项控制覆盖不同合法分解/联合贡献；实际独立复验 0/4。Fixture 可表达不能证明模型真实消费能力 |
| Reality Boundary | Confirmed | 未合格候选不接纳；四条真实试次没有 Review/新履约证据/Guardian；错 Source/Work Reality、缺 Review、虚构授权受控拒绝 |
| Uncertainty Handling | Confirmed | 当前试次失败来源保持 UNRESOLVED；合法计划 BOUND_PENDING_EVIDENCE、背景 RETAINED_CONTEXT；不能据此证明多解释选择的完整能力 |
| Convergence Control | Observed Risk | 两次候选/一次反馈实际执行，预算与收据保持；四条均未收敛。PostgreSQL 27 项验证恢复/篡改/终态连续性，不代替真实模型收敛 |

**D。** 同次模型输出耦合语义选择、来源/证据角色、证明操作数及 Wire 编码；失败再生成整个候选。代码已经允许合法多组件，不存在已证明的唯一路线要求。此耦合是可核对设计事实；是否为四类失败共同原因仍待非 Holdout 证明。

**E — P0。** 优先在原 Owner 内证明合法方案，再依据共同缺口改善构造及一次反馈修复；不扩接纳范围、预算或权限，不添加外部适配层。

来源：[Application](../../src/spg/application/governed_obligations.py)、[Provider](../../src/spg/providers/fulfillment_candidate.py)、[受控资格及范围](../evidence/core-production-semantic-convergence-c3-20261009/formation-module-adaptation-20261012/report.md)、[真实复验](../evidence/core-production-semantic-convergence-c3-20261009/holdout-requalification-20261013/report.md)。

### 3.4 Verification

**A。** 输入确切 Proposed Snapshot/Candidate、义务、原 Fact 和实际 Owner Records；输出适用 Verification Evidence/结果，由 SPG 决定可否晋升。Guardian 和 Human 决策保持独立。

**B — Level 2。** 精确 subject/basis、当前/未来阶段分流、UNKNOWN/UNVERIFIABLE、检查计划与原 Fact 分离已有实现和受控消费。未达 L3：不同合法实现的完整行为证明及计划恢复有效性未取得整体资格，不能以引文存在代表语义成立。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Unknown | Post-admission Materialization、有限静态方法及计划修复已有代码；不同实现的广泛语义/行为等价证明不足 |
| Reality Boundary | Confirmed | Candidate/Revision/Tree 对应、内容/Diff/Source/治理分 Owner；原 G0 有实际 PATH_SCOPE/GIT_DIFFCHECK，但绑定旧 Watt 修订，不能算 f52 新资格 |
| Uncertainty Handling | Confirmed | PASS/FAIL/UNKNOWN，CONTRADICTED/UNVERIFIABLE_CURRENT 与 pending gates 已有具体契约/控制；并非任意缺证据均 SATISFIED |
| Convergence Control | Unknown | 内容 verifier 提供有限反馈，保留矛盾/不可验证判断；尚无当前广泛真实执行证明可修复偏差与真实产物错误始终正确分流 |

**D。** 有限方法集、精确 witness 的消费规则；“引文在源码中”不能独自证明任意行为。模型 SATISFIED 不能自动 PASS。严格 evidence matching 合理，不应通过宽松匹配消除 UNKNOWN。

**E — P1。** 以受影响证据接口做定向资格；随后按真实任务补方法范围，不追求先证明所有软件行为。

来源：[Verification](../../src/spg/application/verification.py)、[内容 verifier](../../src/spg/providers/protected_context_verifier.py)、[Owner 分流](../../src/spg/providers/managed_context_fulfillment.py)、[原 G0 精确证据](../evidence/core-production-semantic-convergence-c3-20261009/guardian-coverage-recovery-20261012/report.md)。

### 3.5 Self-Refine

**A。** 输入所属 Owner 的失败候选、真实反馈/basis、历史收据和剩余预算；输出合法修复/再生/等待/停止及观察。它是各 Owner 的内生机制，不是独立全局 authority。

**B — Level 2。** 信号、分类、证据/身份/预算及无进展停止可见；Formation controlled replay 与 Trace 新实际反馈证明局部机制确实执行。未达 L3：不同 Owner 的信息充分性、进展和修复选择没有整体资格，Formation 当前失败。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Observed Risk | Owner 内修复并不统一有效：Formation 不收敛；Trace 新请求两次来源反馈后修复成功。不能从任何一条替代全模块能力 |
| Reality Boundary | Confirmed | 反馈绑定 Wire/库存/Attempt/收据，PostgreSQL 篡改拒绝；Trace 修订不回填历史 Owner 或授予生产权限 |
| Uncertainty Handling | Confirmed | AMBIGUITY、LOW_CONFIDENCE、EVIDENCE_INSUFFICIENT、REALITY_MISMATCH、NON_CONVERGING 等分类；已有停止不隐藏未履行义务 |
| Convergence Control | Observed Risk | 预算/停止及 replay 限额有效，不证明 repair strategy 有效；Formation 有界执行耗尽未成功，Trace scoped 正例显示可恢复但非普遍保证 |

**D。** 部分恢复依赖完整再生成，反馈存在不等于被正确消费；固定上限是治理约束，不是智能。局部 PASS 与 Work convergence 不可等同，人工重做不能算自动恢复。

**E — P0：Self-Refine Convergence。** 在 Formation 原循环优先改进可行动反馈与实际进展判断，保留原预算和身份。其他 Owner 依据各自事实演进，不新增 Coordinator。

来源：[共享分类](../../src/spg/domain/refinement_contract.py)、Formation 当前运行和 Trace 新运行（见 3.9）。

### 3.6 Executor

**A。** 输入 Task Contract、Native Binding、SourceVector、Workspace、capability grants、checkpoint/observations；输出工具效果、Git/产物、result_claim、checkpoint 和终态，再由完成/Verification/Candidate Owner 接管。

**B — Level 2。** Claim/效果/验证分离，UNKNOWN fencing、恢复分类、资源 envelope/无进展观察和原 G0 的真实执行支持基础。未达 L3：多种合理实现/不完整信息下的自主恢复范围尚未完整证明。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Unknown | 原 G0 证明一个实际 Native 实现路径；不能证明同目标多种实现、不同工具输出结构均可靠消费 |
| Reality Boundary | Confirmed | `result_claim` 单独记录、effects 有真实回执、后续 Git/Verification 独立；历史实际链路有资格，版本范围必须保留 |
| Uncertainty Handling | Confirmed | Effect UNKNOWN/EFFECT_UNRESOLVED、NO_EFFECT/PARTIAL/STALE/LOST；代码与既有恢复资格保留不确定效果，不盲目 replay |
| Convergence Control | Unknown | max inference/tools、无进展 frontier、控制/checkpoint 存在；当前 f52 泛化未进入 Executor，不能凭旧路径或 Trace 的不同源码为其证明完整自主恢复 |

**D。** 固定 tool schema 与 allowlist 保护真实效果；语义映射和 tool feedback 到下一步的有效性不能从这些检查推导。RESULT_READY 不等于 Work 完成。未证明要求固定实现或零模型偏差。

**E — P2（标准初始排序）。** 保留既有真实执行边界；真实 P0 阻断出现时仍需处理，不因排序豁免。广泛自主实现覆盖在当前核心构造链之后推进。

来源：[Kernel](../../src/spg/executor/kernel.py)、[Recovery](../../src/spg/executor/recovery.py)、[Worker](../../src/spg/infrastructure/executor_runtime/worker.py)、[历史 Native 资格](../evidence/watt-native-executor-qualification-closure-20260912.md)。

### 3.7 Guardian

**A。** 输入 exact Candidate/Source/Work/执行身份与真实 Owner Evidence，通过独立 resolver 和软件观察输出 Assurance Gate/Findings。Watt、模型和 Executor 不拥有其判定权。

**B — Level 2。** 独立证据校验、BLOCKED/FAIL_REPAIRABLE、当前/未来/背景贡献区分有实测。未达 L3：已资格 v3 消费不是任意语义、证据不足处理和自主复核策略的完整能力。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Confirmed | 0d7aca95 修复 v3 原 Fact qualifier 不含固定 negated 标记及合法背景贡献的错拒；实际同 Candidate PASS，限已证明的来源/方法契约 |
| Reality Boundary | Confirmed | 独立读取 Review/Native/Source records，Watt COVERED 不能单独通过；155 项镜像测试及 PostgreSQL 联合 2 项、实际 PASS 均有历史身份 |
| Uncertainty Handling | Confirmed | 缺权限/错版本/缺证明产生 BLOCKED 或 Findings，repairable defect 不等于授权；实际 scoped 契约支持，非任意不确定解释管理 |
| Convergence Control | Unknown | Findings 可交原生产 Owner 修复，重新独立核验；历史本轮通过由工程修复促成，不证明 Guardian 自主探索与恢复策略完整 |

**D。** 已修复旧固定 qualifier/背景规则的适用性缺口，不能继续列作当前阻断。现存有限 evidence methods 合理但不能保证全部合法新证据可表达；这一广泛能力未验证。缺日志不能证明没有非法效果。

**E — P1。** 保持独立 Gate，只在真实新契约缺口出现时做窄 Owner 校准，不重开已解决 Coverage 问题。

来源：[Guardian 固定源码](https://github.com/hengyizhiyuan/guardian/blob/0d7aca954588c8ad3883dbedb730e59dc1d7b867/src/guardian/runtime.py)、[实测恢复及确切版本](../evidence/core-production-semantic-convergence-c3-20261009/guardian-coverage-recovery-20261012/report.md)。

### 3.8 ECF

**A。** 输入 DecisionType、Scope、Authority 和真实 source snapshots；输出选定上下文、来源 trace、指纹、时效/缺类/冲突状态。Git/Product/Work 保有事实，Watt Consumer 负责接纳与 lineage。

**B — Level 2。** 来源/投影分开，Authority 与 current/historical、新鲜度/冲突有契约和既有 Owner 回归。未达 L3：注册类别外的合法语义、歧义解决和自主信息补足未完整资格。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Unknown | 固定注册 DecisionType/ContextClass/Scope 投影已实现；不等于开放表达和多解释到权威上下文的广泛适应证明 |
| Reality Boundary | Confirmed | GOVERNED/PROJECTION、SourceIdentity、Authority/current lineage 分开；Watt bounded consumer 不授予域 Closure |
| Uncertainty Handling | Confirmed | INCOMPLETE、CONFLICTED、STALE_OR_UNCERTAIN、缺类与具体来源风险可表达；证明的是注册契约范围，不是完整 ALTERNATIVE 自主选择 |
| Convergence Control | Unknown | 重新观察来源/更新请求由既有 Owner 负责；未见对所有缺类/冲突自主选择恢复策略的适用资格，不能靠生成 Approved Facts 填补 |

**D。** 有限 taxonomy、surface 注册、确定投影规则可见；它们不是 Bug 证据，但不能以注册上下文 READY 推导语义充分或目标完成。未证明当前 C3 漏保 Protected Context。

**E — P1。** 对真实新场景核对 source/authority/投影消费，不建全局 ontology 或另一层语义中心。

来源：ECF 固定提交的 `src/ecf/decision_context.py`、`tests/test_decision_context.py` / `tests/test_managed_greenfield_context.py`（本机 Git 对象读取，未运行）；[Watt consumer](../../src/spg/application/decision_context.py)、[已有 Owner Runtime 范围](../evidence/watt-p0-full-system-closure-20260926.md)。

### 3.9 Trace Analysis

**A。** Human 请求只读调查历史/静止等待 Work；输入冻结导出、明确 Owner 关联与 exact repository reads；输出草稿、引用/结构结果、咨询报告及同 Owner 自审。无生产 Work 重放、代码修改、自升级或审批权限。

**B — Level 2，新 scoped 自主正例。** 实际 Evidence inspect/read、来源反馈/显式修订、UNKNOWN、自审和精确 digest 终态均已存在，最新 Native 自动成功支持基础收敛。未达 L3：一条单事件成功不证明广泛或稳定自主调查；引用完整不等于全部因果断言可靠，独立 Human Assurance 仍不存在。

| Capability | Status | Evidence |
| --- | --- | --- |
| Semantic Adaptation | Confirmed | e207b92c 新调查在两次来源反馈后自动修复、提交/自审，报告未经人工改写。限最低充分单事件路径，不能据此证明所有证据结构和多解释适应 |
| Reality Boundary | Observed Risk | 边界门实际存在；较早 27cfcfd8 结构 PASS 的报告把未导出扩大为历史丢弃，语义 FAIL。最新 scoped 复核 PASS，旧缺口不能被称为当前同样错误，完整语义可靠性仍未验证 |
| Uncertainty Handling | Confirmed | 新报告保留 historical Worker revision、Provider/其他事件 UNKNOWN；根因分类 ROOT_CAUSE_HYPOTHESIS，不冒充排他证据。咨询完成不改变 WAITING_HUMAN |
| Convergence Control | Confirmed | 新请求 11 inference / 26 tools / 约 540.5 秒，在原 12 / 48 / 600 内完成来源修复、自审及 RESULT_READY；只证明一次有界链，不证明长期稳定 |

**D。** 报告 schema、引用集合、阶段路线/预算保留；之前纯文本被当 JSON 的导航 Bug、自审身份重复转写缺口和等待 Human 入口误拒已经修复。当前自审仍是模型 proposal，不是独立 Assurance；不能以结构结果或自审通过代替完整语义证明。探索转提交的有限策略存在，但对不同难度的可恢复性还没有全面资格。

**E — P1。** 在独立 Trace 任务中验证不同证据结构、冲突/缺证据/替代因果解释及恢复路线，既保留新正例也保留旧失败。不把 Trace 变为 C3 新前置门，不增加预算或扩大调查到全部历史。

新事实：[入口修复与链路](https://github.com/hengyizhiyuan/software-production-platform/blob/6aada04010631b6833b9b9487addb11f9ec36f6b/docs/architecture/work-trace-entry-fix-20261013.md)、[Native 结果](https://github.com/hengyizhiyuan/software-production-platform/blob/6aada04010631b6833b9b9487addb11f9ec36f6b/docs/evidence/work-trace-entry-fix-20261013/native-result.json)、[限定复核](https://github.com/hengyizhiyuan/software-production-platform/blob/6aada04010631b6833b9b9487addb11f9ec36f6b/docs/evidence/work-trace-entry-fix-20261013/independent-review.json)。复核者为 Codex，不声称 Human Assurance 或全 Work 根因认证。

历史事实：[旧辅助交付及失败](https://github.com/hengyizhiyuan/software-production-platform/blob/d378ddb6fd82ce687efa887f34c6664419a6df0c/docs/architecture/work-trace-self-analysis-minimum-20261013.md)、[较早语义 FAIL](https://github.com/hengyizhiyuan/software-production-platform/blob/d378ddb6fd82ce687efa887f34c6664419a6df0c/docs/architecture/work-trace-self-analysis-handoff-20261012.md)。当前实现：[Trace Service](https://github.com/hengyizhiyuan/software-production-platform/blob/e207b92ce7b6a670bd48e4a58639593447262637/src/spg/application/trace_analysis.py)、[证据工具](https://github.com/hengyizhiyuan/software-production-platform/blob/e207b92ce7b6a670bd48e4a58639593447262637/src/spg/infrastructure/trace_analysis_evidence.py)。

## 4. Confirmed AI Native Gaps

| 事实 | 当前结论 | 不允许的推导 |
| --- | --- | --- |
| Formation 当前真实泛化 0/4，全部没有接纳/Review；两次候选与一次反馈已发生 | 合法构造及有界收敛资格未达成，当前 P0 | 不能说 Validator 已错拒、四类错误只有一个根因或必须增加次数 |
| Formation 受控表达/版本/反馈/replay 通过，但不代表真实模型成功 | 受控工程能力与实际语义消费间存在已观察的资格差距 | 不将 Fixture PASS 宣布为 AI Native 泛化 |
| Trace 历史结构通过仍语义 FAIL，最新 scoped 自动成功 | 结构/引用/自审与语义成立是不同门；局部进展真实，广泛可靠性仍待资格 | 不保留过时的“Native 无成功”判断，也不以新一次成功消除历史或直接升级 L3 |

已修复的问题单独记录：Guardian v3 固定 negation/背景错拒；Trace 纯文本导航、草稿引用身份重复转写、静止 Human wait 入口拒绝。它们不再作为未解决缺口。当前有证据的缺口应在原 Owner 内处理，不凭本评估新增平台层。

## 5. Observed Risks 与尚未验证

### 5.1 已观察风险

1. **语义与精确编码耦合：** Formation 同次完整输出承接语义、角色与操作数/引用；真实反馈未成功。这是具体风险，不是新 Normalizer 的必要性证明。
2. **规则回退与语义充分性：** Planning 回退能保护范围，不独立证明方案理解与实际目标覆盖。
3. **验证幻觉：** Trace 有实际反例；其他模块应保留不同 gate 的职责，不能因未见错放而判整个语义能力合格。
4. **反馈与真实进展不同：** Formation 反馈执行无合法接纳；Trace 新正例有来源修复与 digest 终态。不能以调用次数统一描述两者。
5. **版本/资格漂移：** 较早 G0/Guardian 和新 f52 复验、Trace 独立版本不能相互替代。文档层新标准也不改变实测版本。

### 5.2 Unknown，不是已证实缺陷

- WIC 新旧来源分解的开放语义忠实度。
- Planning 的替代方案比较与信息不足时自主决定路径的广泛有效性。
- Verification 面向合法不同实现的行为充分性与恢复范围。
- Executor 在当前新版本泛化场景下的实际恢复能力；最近试次尚未调用。
- Guardian/ECF 已注册范围之外的新语义与独立取证/源刷新路径。
- Trace 多事件、复杂冲突和稳定自主报告的资格；新一次 scoped PASS 不足以证明。

以上 Unknown 不自动要求改代码。先用适用的非 Holdout 对照与真实证据判责任，仍可能是合法有限范围或正确停止。

## 6. Evolution Priority

沿用标准初始排序，以真实生产/核心能力缺口决定具体施工：

| 优先级 | 对象 | 本次建议边界 |
| --- | --- | --- |
| P0 | Formation；Self-Refine Convergence | 原 Owner 内合法候选构造、来源/证据角色与可行动修复、进展/停止；不扩权限或预算 |
| P1 | Trace；Verification；WIC；Planning；ECF；Guardian | 各自现有责任内证明变体、未知、证据不足、替代方案及恢复；依实际缺口排序 |
| P2 | Executor；UI/Interaction | 较广可靠性/表达与体验演进；不豁免任何真实安全或生产阻断 |

WIC 原意连续性是 P0 Formation 的输入基线证明，不表示已确认 WIC 平台缺陷或改动其长期排序。Human Gate 的真实等待不是工程缺陷，不为自主收敛伪造授权。

## 7. Recommended Next Phase

**推荐 Phase 1：在既有 Formation Owner 内完成“合法构造与有界修复”的基础能力资格。**

1. 固定非 Holdout Human/Work Reality、source/版本/权限与已有 capability。证明同目标的多个合法分解/联合贡献可表达，并区分真正缺义务、缺证据、矛盾、格式/引用错误。
2. 对已确认共同缺口，复用 source view、locator、typed prerequisites、receipt 和现有反馈；模型负责语义选择，Owner 负责从明确选择恢复可确定身份。不能自动补造组件/支撑成员/Fact。
3. 原预算内明确恢复策略和进展：合法组件/来源对应、必要证据或剩余未决确有变化；格式变好/调用更多不等于进展。不可评估、缺 authority、结果未知或耗尽时真实停止。
4. 局部/受影响回归后冻结 exact source/image，按原 C3 Mission 取得实际链路及独立泛化资格。保持 Holdout 独立，不用内容调优，不增加 C3 Closure 条件。
5. Trace 新 scoped 正例作为独立 P1 证据保留，随后验证其自己的难度变化与边界；不把它移植成全局修复框架或 C3 新要求。

本阶段只提出建议，不实施以上步骤。不修改代码/测试/Guardian Gate/C3 状态，不调用模型、重跑资格、加 Prompt Patch 或全面推倒重构。

### 7.1 最终四问

**1. Watt 当前是否已有 AI Native System 雏形？** 有。正面证据包括候选与权威接纳分离、准确来源/版本/权限、UNKNOWN 与待证据/后续 Gate、独立 Guardian、有限修复与真实停止，以及 Trace 新实际有界恢复。它尚不是整体 Level 3 或稳定泛化已证实的系统。

**2. 哪些能力已经存在？** IRK/Fact 接纳边界、派生履行组件、按 Owner/阶段的证据消费、精确 Verification、未知效果 fencing、Checkpoint/预算、反馈/恢复收据及独立 Assurance。新 Trace 已在一条实际调查内自主修复来源反馈并形成报告。这些都有明确适用范围，不能合并为无限范围能力声明。

**3. 哪些能力仍停留在传统确定性假设或未获证实？** Formation 将开放语义选择与精确协议构造绑定、恢复依赖整体再生；Planning 的规则回退只证明边界安全，未证明开放方案充分；格式/引用/Schema 合法不能保证语义成立，Trace 历史已出现反例。多解释/ALTERNATIVE、NEED_MORE_INFORMATION 的主动闭环，以及不同难度下恢复策略的可靠性仍未完整验证。严格 Source/Authority/协议是必要治理，不应被消除。

**4. Phase 1 首先演进哪些基础能力？** Formation 自身的来源/证据角色消费、合法候选构造与有界 Self-Refine；建立可核对的实际进展/停止和正负资格。其他模块按真实新缺口演进，不全面重构、不降低 Validator/Guardian、不让 Human 人工补齐本应由模块处理的 HOW。

本次模型/测试/镜像/资格/生产操作均为 0；仅文档重评。**C3 保持 PARTIAL。**
