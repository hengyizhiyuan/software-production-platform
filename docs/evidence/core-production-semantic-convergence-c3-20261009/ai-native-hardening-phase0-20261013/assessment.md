# Watt AI Native Hardening Phase 0 — Core Production Chain Assessment

2026-10-13，Asia/Shanghai。**架构评估，未实施修复；C3 保持 PARTIAL。**

## 1. 范围、版本与判断依据

本阶段只读取既有代码、权威契约与允许公开的资格收据。不调用模型、不运行资格、不读取封存输入或 Oracle、不修改实现、测试、历史事实、生产环境或 Closure Contract。本文是评估记录，不是新的架构决策或实施授权。

| 对象 | 评估基线 |
| --- | --- |
| 分支 / 证据 HEAD | `codex/c3-open-semantic-obligation-convergence` / `1cc5dddfdff2597ac563cad369ff9c0b9f9de217` |
| 冻结应用 / Git Tree | `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0` / `c8ad5b06283905e218786ef785e940a82edd1dbf` |
| 最近独立复验镜像 | `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1` |
| Guardian | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` |
| ECF | `5aa4f8833c359c15bd059eda5972aa3915bcc18c`；按此提交读取，未以本机 ECF 新 HEAD 替代 |

检查时 C3 checkout 存在先前未提交的旧取证文件及一份旧审计文档修改，予以保留。应用源码与上述冻结提交之间没有差异。其他任务 checkout 不作为本次施工或事实来源。

判断遵循 Program ADR-0002、Watt 开发原则 §13/§14。严格身份、Schema、来源、权限、Effect Permit、证据完整性和独立 Assurance 是应复用的确定性。它们的存在本身不是 AI Native 缺陷。需要审查的是：模块是否能在这些边界内消费合法变化，以及拒绝后的恢复是否真的有效。

证据分级：**实测**＝既有实际运行收据；**代码确认**＝可见实现/契约；**待证假设**＝尚未用独立事实证明的解释。风险定义：P0 影响当前 C3 Closure；P1 影响后续生产可靠性；P2 长期演进。未发现当前缺陷的模块，不因处在核心链路就推定必须重构。

## 2. 当前生产状态

- 原真实 G0 已到 SEALED Candidate、READY Preview、Independent Guardian PASS / 0 Findings，见[覆盖恢复报告](../guardian-coverage-recovery-20261012/report.md)。这说明链路已有实际生产能力；该历史资格绑定其当时版本，不替代新修订资格。
- 最近冻结版本的独立泛化复验为 **真实模型 0/4 PASS，受控 Owner 负向 4/4 PASS**。四个真实场景均未接纳 Projection，独立 Semantic Review / 下游 Verification / Guardian 调用均为 0。见[复验报告](../holdout-requalification-20261013/report.md)。
- 本次直接阻断在 WIC 后、生产执行前的 Formation 接纳边界。不能把未被调用的 Executor、Verification 或 Guardian 判为这四条运行的失败 Owner。
- 原输入 hash 与 IR 字段/出处连续性已有收据；新旧来源数量及语义描述有变化。**WIC 的语义等价/完整性尚未独立证实**，不根据数量变化宣布失真，也不宣布其必然无责。
- 目前未证明 Validator 错拒合法结果。正确的结构、安全、来源和权限拒绝必须保留。真实生成不收敛也不能全部归咎于模型“没听话”。

## 3. AI Native Gap Map

| 模块 | 已有适应与事实边界 | 当前主要差距 | 风险 / 证据 |
| --- | --- | --- | --- |
| WIC | 语义候选、IRK/Fact 接纳校验、原输入出处、有限结构/动作修复 | 结构合法不证明原意完整；变化后来源语义等价尚待证；部分反馈分派依赖错误文本 | **P0 待证项**：C3 来源基线可信度；非已确认 WIC Bug。其余 P1 |
| Planning / Steering | 在接纳 Work/Source/权限内提出计划；Reality 驱动推进；未决停止 | 非法计划回退规则 Planner；保护目标文字不等于理解多种实现；有限图/能力规则有适用边界 | **P1**，代码可见；未证明当前 C3 被其错误阻断 |
| Formation / WORK_FULFILLMENT_PROJECTION | 多来源/多组件、可逆输入、Owner 前提、精确 Validator、独立 Review、UNRESOLVED | 语义选择、来源角色、证明操作数、Wire 编码耦合；一次反馈后仍不能构造合法候选 | **P0 已证实资格缺口**；共同机制解释仍需非 Holdout 证明 |
| Verification | 精确 Git/内容/来源/执行 Gate；计划与事实分离；UNVERIFIABLE；有限计划修复 | 支持的方法范围有限，源码见证不总能证明行为；语义充分性不能由匹配引文单独保证 | **P1**；当前 C3 必须保留回归门，但没有本次直接故障证据 |
| Self-Refine | Owner 内修复、共享信号、收据/预算/重复签名、未知与停止分类 | Formation 当前修复有执行记录但不收敛；结构反馈不等于修复策略有效；跨 Owner 信号仍须保持各自含义 | **P0：Formation 内恢复**；其他 Owner 接线/经济性 P1 |
| Executor | Native 循环、真实工具观察、Claim/产物分离、权限门、Checkpoint/Effect UNKNOWN | 工具结果到下一步语义修复的有效性只能按实际场景证明；单次执行完成不证明 Work 闭环 | **P1**；原链路有实测，新泛化试次未调用 |
| Guardian | 独立读取 Owner Evidence；检查版本、来源、阶段；PASS/FAIL_REPAIRABLE/BLOCKED | 既有方法覆盖有边界；未知/不可观测转 BLOCKED 的原因必须完整投影；通用语义 Assurance 未获无限范围资格 | **P1**，未证实当前新阻断；长期通用 Assurance P2 |
| ECF | 来源/权限/时效/冲突/缺类、决策投影、指纹与 lineage | 有限类型与 surface 策略可能限制新语义；上下文 READY 不证明履约或生成会收敛 | **P1**；未证实当前 C3 有 ECF 错拒或 Protected Context 丢失 |

### 3.1 WIC

**职责。** 解释当前 Human 输入与权威上下文，提出语义/动作/Fact 候选，通过 IRK 与现有接纳边界形成 Work Reality；响应表达不拥有额外权限。

**确定性假设。** 结构化字段及 Fact 权限检查合理；风险是将“字段及引用合法”当成“所有原始目标已被理解”。`deepseek_interaction.py` 具有初次候选加最多三次结构/动作修复；部分修复指导按验证错误文本选择。后者是现有诊断消费方式，不能不加区分地称为业务关键词替代智能，但对新错误形态的适应有待证。

**四项差距。** 输入适应：已有开放模型解释，合法拆分变化仍需语义等价证明。事实边界：已有 Fact candidate 接纳及 SYSTEM_INFERRED 权限限制，不是模型直接授予 Human Authority。不确定性：已有低置信、未决、阻断机制；没有证明每条合法变化都有精确不确定性说明。收敛：已有有限修复，但 Schema 修好不代表遗漏语义已恢复。

**C3 范围。** 在非 Holdout 固定 Human 输入上核对目标、Scope、限定、禁止事项和阶段要求，不要求相同 Fact 数量或同一拆分。若无遗漏证据，不改 WIC。P0 是基线证明责任，不是预先定罪。

依据：[WIC Provider](../../../../src/spg/providers/deepseek_interaction.py)、[WIC 接纳政策](../../../../src/spg/application/wic_intelligence.py)、[Fact 类型](../../../../src/spg/domain/engineering_semantics.py)、[接纳绑定](../../../../src/spg/application/engineering_semantics.py)。

### 3.2 Planning / Steering

**职责。** 在接纳目标、Source、Change Contract、能力与权限内提出生产计划，依据实际完成/阻断 Reality 形成下一步候选，再由治理边界接纳。

**确定性假设。** `ProductionPlanningService` 对 ValueError 或权限扩张回退到现有 RuleBasedProductionPlanner。此回退能保护 authority，但不证明它理解任意开放实现。保持 objective/desired_outcome 的原值合理，不应扩展为实现步骤必须唯一。图约束如 PWU 数量与已证明路径数量的关系体现当前有限模型，尚未证明造成 C3 的非法拒绝。Deterministic Steering 仅处理结构明显的推进/等待，本身不应被宣传为开放规划能力。

**四项差距。** 输入适应：可以接受计划候选，复杂替代路径的覆盖有限。事实边界：proposal 不等于接纳计划，exact Source/权限受保护。不确定性：NEEDS_REFINEMENT、Authority uncertain、Human Attention 与 Completion evidence 均有区分。收敛：存在候选再生/持久修复记录；没有证据保证规则回退后的计划在语义上足够，而不能因回退未越权就认定生产必然成功。

**C3 范围。** 保留 Formation UNRESOLVED 到 Runtime 前 BLOCKED 的接线，以及合法计划到 Task/PWU 的连续性。当前不重做 Planner，也不在本轮实现 C4 的高级 Human Attention/恢复路由。

依据：[Planning](../../../../src/spg/application/planning.py)、[Steering 决策](../../../../src/spg/application/steering_decision.py)、[生产接线与未决停止](../../../../src/spg/application/steering_production.py)。

### 3.3 Formation / WORK_FULFILLMENT_PROJECTION

**职责。** 从接纳 Fact/Clause/IR Item/Work Constraint/Context 和既有 Capability Contract 提出派生组件及履行绑定；核对精确引用/范围/Owner/Phase/方法资格，随后独立语义 Review。它生成的是待履行计划，不生成已完成 Evidence，也不拥有更改原意或权限的 authority。

**确定性假设。** 当前已经支持多来源、多组件、不同合法处置，不能说实现要求唯一路线。更具体的问题是：一次完整模型输出同时承担开放语义选择、Fact dependency 与 provenance 区分、来源证明操作数选择及严格 Wire 编码；恢复再生成完整候选。准确索引、原文和身份要求应保留，但能由 Owner 从明确选择恢复的信息不应不必要地依赖概率编码。

**四项差距。** 输入适应：现有 source table/consumer input/typed preconditions 有准备能力，实际泛化仍不合格。事实边界：结构候选、接纳绑定、Review、实际 Evidence 已区分；在模型输入中这些角色是否足够清晰仍是工作假设。不确定性：UNRESOLVED、BOUND_PENDING_EVIDENCE、RETAINED_CONTEXT 已存在，缺证据不自动 PASS。收敛：两次候选/一次身份绑定反馈真实执行，但本轮四条试次均未收敛，不能以“存在 retry”宣称内生适应合格。

**C3 必需加固。** 在本模块内完善来源/证据角色准备、候选构造及有界修复，优先复用可逆表示、locator、typed prerequisites 和 feedback。分别对格式/引用、组件语义冲突、证明前提缺失及安全不可评估给出合法处理；不补造 Fact/Evidence，不静默修正非法历史 Wire，不新增全局 normalization Owner，不增加预算。

依据：[既有职责分析](../formation-responsibility-review-20261013/analysis.md)、[非 Holdout 对照](../non-holdout-root-cause-20261012/report.md)、[Application](../../../../src/spg/application/governed_obligations.py)（inventory:666、validator:1349、feedback:1576、前提:2132、执行:3563）、[Provider](../../../../src/spg/providers/fulfillment_candidate.py)（输入视图:441、source table:491、consumer input:713、安全收据:1883）、[候选/绑定类型](../../../../src/spg/domain/governed_obligation.py)。

### 3.4 Verification

**职责。** 针对实际、确切 Candidate/Proposed Snapshot 及当前适用义务产生验证证据，区分内容、Diff、Source、执行权限和后续 Gate；只有完整、适用且版本一致的 PASS 才晋升。

**确定性假设。** Protected content SATISFIED 需要真实 implementation witness；这是内容证据门，不是所有治理要求都必须出现源码字符串。现有 managed fulfillment 已按 Owner/阶段分别消费。静态方法集和源码引文只能证明其适用范围；若任意行为因“有引文”被认为实现，就会混淆方法证据与实际效果，但此次未获得这样的错误放行证据。

**四项差距。** 输入适应：已有 Post-admission Materialization 和有限检查计划修复，不要求 WIC 预先采用固定 Subject。不确定性：CONTRADICTED/UNVERIFIABLE 与 SATISFIED 区分。事实边界：原 Fact 不随检查计划改写；实际引文、精确 Git、Owner records 分开。收敛：表达/计划问题可修复，真实产物错误保持不合格。剩余适用方法和真实行为覆盖应按要求报告，不引入理论上覆盖所有行为的 C3 新门。

**C3 范围。** Formation 改动后仅验证受影响的多组件/联合贡献与对应证据消费，保留错误内容、错版本、缺证据拒绝。当前没有依据重新设计 Verification。

依据：[Verification 接纳](../../../../src/spg/application/verification.py)、[内容证据](../../../../src/spg/providers/protected_context_verifier.py)、[静态计划及有界修复](../../../../src/spg/providers/static_html_semantic_verifier.py)、[分 Owner 证据消费](../../../../src/spg/providers/managed_context_fulfillment.py)。

### 3.5 Self-Refine

**职责。** 这是各现有 Owner 内的候选修复及停止机制，不是一个拥有全链路 authority 的独立协调器。共享 refinement contract 提供信号、分类和收敛观察；具体候选、反馈、预算和晋升仍由所属 Owner 管理。

**确定性假设。** 固定次数/资源上限是正确治理。问题是不能把“发过反馈”“局部修复 PASS”视为全 Work 收敛，也不能将不同 Owner 的 SCHEMA_INVALID、EVIDENCE_INSUFFICIENT 与真实目标错误混成同一种再生请求。

**四项差距。** 输入适应：WIC、Formation、检查计划、Executor 各有实际局部机制，强度不相同。事实边界：修复候选不改事实/权限，收据和 lineage 约束已实现。不确定性：AMBIGUITY、LOW_CONFIDENCE、REALITY_MISMATCH、EVIDENCE_INSUFFICIENT、NON_CONVERGING 等已存在，不是二元状态系统。收敛：Formation 反馈虽然身份绑定且预算受控，当前实际恢复收益不合格；这属于需要在该 Owner 内证明/修复的 P0。

**C3 范围。** 修复 Formation 一次反馈的可消费性和合法修复策略，保持次数、累计预算、原 Wire/库存/Attempt/收据身份；无合法依据及预算耗尽如实停止。其他模块的统一经济度量或 Work 级高级恢复归 P1/P2，不启动 C4。

依据：[共享 refinement 语义](../../../../src/spg/domain/refinement_contract.py)、WIC/Formation/Verification/Executor 各上述实现。`application/refinement.py` 是 Repository Change Proposal 边界，不能因名称将其当成全局 Self-Refine Owner。

### 3.6 Executor

**职责。** 在 Native Binding、Task Contract、SourceVector、Workspace 和 Effect Permit 内进行实际推理/工具循环，记录观察、效果、产物、Checkpoint 和 terminal outcome；其 result_claim 不是 Verification PASS。

**确定性假设。** 进程路径、版本、权限、工具 Schema 严格是必要边界。实际 kernel 可在拒绝决策/工具结果后继续有限推理，保留残余义务及修复历史，不要求唯一执行步骤。三轮无新证据和资源 envelope 形成停止边界；计数不应被误读为“智能推理已充分”，其恢复能力需真实运行证明。

**四项差距。** 输入适应：合法工具/计划变化可进入原循环，推理拒绝也有反馈观察。事实边界：Claim、ToolExecutionResult、ExecutionEffect、Git 和后续 Verification 分开。不确定性：Effect UNKNOWN、EFFECT_UNRESOLVED、PARTIAL、STALE、LOST、NO_EFFECT 等已区分，避免未知效果重复执行。收敛：有推理/工具预算、ineffective rounds、checkpoint frontier；未证明任意任务可以恢复，不能借既有 G0 成功作泛化承诺。

**C3 范围。** 保留已工作的真实 Workspace、Native Context 引用、权限和证据链。Formation 未接纳时不能通过 Executor 补事实，亦无依据重写 Executor。后续受影响真实链路按原资格要求证明。

依据：[Native kernel](../../../../src/spg/executor/kernel.py)、[未知效果恢复分类](../../../../src/spg/executor/recovery.py)、[Context evidence](../../../../src/spg/executor/context_evidence.py)、[Worker](../../../../src/spg/infrastructure/executor_runtime/worker.py)。

### 3.7 Guardian

**职责。** 独立核验实际 Owner Evidence、Candidate/Source/Work/执行版本、义务/阶段及适用的软件行为；Watt 的 COVERED、模型 Review 或缺少日志都不能单独构成 Assurance PASS。

**确定性假设。** 证据方法和检查契约有限，属于有明确范围的独立 Assurance，不需要让 Guardian 对任意开放文本作无证据推理。当前软件 Assurance 提供 PASS、FAIL_REPAIRABLE、BLOCKED；缺权限或不可观察应阻断，而不是制造 UNKNOWN 后仍放行。

**四项差距。** 输入适应：能读取投影组件、联合依赖和对应真实 Owner 记录，但通用覆盖范围不能由接口存在推断。事实边界：独立 resolver 对来源、版本及 Review receipt 再核验；模型 verdict 不等于证据。不确定性：不可修复/缺证据以 BLOCKED/Finding 保留；若需要用户理解具体缺口，应消费其原因而非另造结论。收敛：repairable Findings 可由原生产 Owner 修复，Guardian 保持独立复核，不授予生产修复权限。

**C3 范围。** 保持已有 coverage 修复与独立门禁，按原条件在实际新证据出现后调用。最近四条试次未调用 Guardian，不能归责 Guardian normalization，也不能用 controlled scope 检查称为真实 Guardian PASS。没有新契约缺口证据时不改 Guardian。

依据：[Guardian 固定源码](https://github.com/hengyizhiyuan/guardian/blob/0d7aca954588c8ad3883dbedb730e59dc1d7b867/src/guardian/runtime.py)（独立证据:183、组件计划:481、内容:875、库存:922）、本机精确 checkout `D:/hy/c3-open-obligation-convergence/guardian` 的 `docs/04_integration/watt-software-assurance-v1.md`、[实际覆盖恢复](../guardian-coverage-recovery-20261012/report.md)。仓库远端地址以该 checkout 配置为准，不以文档中的名称推定部署。

### 3.8 ECF

**职责。** 按请求的决策类型/Scope/Authority，从真实来源选择与投影上下文，提供来源追踪、版本/新鲜度、冲突和必要类别判断。原来源事实仍由 Git/Product/Work 等 Owner 拥有；ECF READY 不是 Work、Evidence 或 Closure PASS。

**确定性假设。** 固定 Context Class/Decision Type 及 surface 注册是当前有限契约。若所有 Greenfield 强制存在无关 Approved Decision，会错误拒绝合法工作；但不能根据有限类型的存在宣称此旧问题仍未修复。Watt Gateway 的注册路径/surface 规则是否覆盖未来开放项目，是 P1 适用范围风险，不是本次已证明失败。

**四项差距。** 输入适应：可按 Owner/Scope 投影，开放事实到类别的适用性仍须有来源依据。事实边界：GOVERNED/PROJECTION、Authority、SourceIdentity 和 historical/current 分开。不确定性：READY、INCOMPLETE、CONFLICTED、STALE_OR_UNCERTAIN 已有；不需要模型编造缺类记录。收敛：通过真实来源刷新/纠正请求责任恢复，不能用 Self-Refine 创造 Approved Facts。

**C3 范围。** 复用已资格版本和受保护上下文完整性。若 Formation 的角色准备需要 Context 引用，只引用既有事实与 provenance；不重做 ECF taxonomy，不扩展审计到其他项目。

依据：ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c:src/ecf/decision_context.py`（从本机 Git 对象读取）、[Watt bounded consumer](../../../../src/spg/application/decision_context.py)。本机 ECF 新 HEAD 未作为资格基线。

## 4. Fact / Observation / Inference / Claim / Fulfillment Evidence

这些是角色边界，不要求新增五套实体、状态机或数据库。

| 角色 | 当前来源 / 合法用法 | 禁止晋升 |
| --- | --- | --- |
| Fact | 已接纳 Semantic Fact、Human/Source/Work Reality，带 authority/出处/版本 | “有要求”不能证明产物已实现 |
| Observation | 实际 Source/工具/Provider/验证/环境观察与对应收据 | 未覆盖的日志或旧版本观察不能证明不存在非法效果 |
| Inference | WIC 解释、计划、履行方法候选、检查方案及语义判断 | 推断不能生成不存在的 Owner 记录或 Human 决定 |
| Claim | Route/rationale、Executor result_claim、Watt coverage 描述 | 格式正确、模型自述或 Semantic Review 不等于 Assurance |
| Fulfillment Evidence | 正确 Owner 在适用阶段提供的确切 Git/内容/执行门/Seal/授权证明 | 未来 Gate 的 PENDING 不能作为已授权/已完成证据 |

代码中这些界限已部分明确存在。当前主要风险不是“没有任何区分”，而是在构造候选和消费反馈时，来源角色、方法资格、Review 判断与实际证据状态仍需更清晰、可合法构造的内部处理。UNKNOWN 必须附着在不知道的具体事项上；前提未知、方法不明、目标未满足、已知权限拒绝不能统一称为 UNKNOWN。

## 5. C3 必需 Hardening 范围与后续顺序

### 必需范围

1. **确认输入基线，而非重做 WIC。** 非 Holdout 已知 Human 输入 → 接纳 Reality 的目标/限定/禁止/阶段语义连续性。允许不同合法拆分；如果发现真实遗漏，再在原 Owner 修复。
2. **Formation 内候选构造与恢复。** 将开放语义选择与已有 Owner 可确定恢复的身份/角色/引用编码职责理清；保留多来源联合、多组件和合法方法变化。先证明现有契约可表达，不预设必须改 Schema。格式、语义、来源前提、安全不可评估分别消费，仍使用原次数和预算。
3. **受影响链路证明。** 当前/未来/持续禁止/保留上下文的门禁不丢失；来源/版本/权限/内容/证据负例仍拒绝。新的方案必须沿既有独立 Review、真实 Evidence、Guardian 与封存泛化资格验证，不能以本报告或受控测试关闭 C3。

### 建议顺序

| 顺序 | 工作 | 前进依据 |
| --- | --- | --- |
| 1 | 在非 Holdout 固定 Reality 上证明至少两种合法联合/多组件方案，梳理 source/evidence 角色与失败边界 | 区分不可表达的契约缺陷、模型错误及正确拒绝；不根据 Holdout 构造答案 |
| 2 | 仅在证明缺口的 Owner 内实现最小构造/反馈恢复改动 | 优先现有 wire/view/locator/receipt；不新增请求、authority 或 Evidence |
| 3 | 局部正负回归及受影响 PostgreSQL/Owner 联合验证 | 保持 identity、完整性、权限与独立门禁；不每次微调运行全库 |
| 4 | 冻结 exact source/image，按原 Mission 取得必要实际模型与生产链路证据 | 成功位置、未决、反馈收益、实际 Token 和停止原因可关联；旧历史结果不冒充新版本 |
| 5 | 独立泛化资格与原 Closure 对账 | 仅作验收，不向执行者回流输入/Oracle 调优；真实未满足仍 PARTIAL |

这是下一阶段建议，不在本次执行。若现有契约已能满足正确性，应修内部消费而非增加接口；只有明确证明缺口才考虑窄契约变更，并与 Human 核对架构/权限边界。

### 明确不纳入 C3 必需施工

全局 Reality/Evidence Normalizer、万能 AI Adapter、第二个 Coordinator、统一五类事实数据库；全 Planner 自适应重构、任意行为的理论完备验证、Guardian 全范围语义推理、ECF 通用本体；跨阶段高级恢复/Human 路由、C4/N1/N3、模型路由或预算策略变化。

## 6. 结论与评估限制

**优先修 Formation 内构造和恢复；先证明 WIC 语义基线；其他模块保留现有责任与门禁，按受影响接口做资格保护。** 当前证据不支持八个模块一起重构，也不支持“全部问题只是模型随机性”。

本评估未新增实测结果。代码存在机制不等于已资格；历史成功不等于新修订泛化；未调用的下游也不是已被证明有缺陷。最近四类失败是否共用一个具体根因仍需非 Holdout 证明，不能用设计假设替代证据。

本阶段模型调用 0、镜像构建 0、测试/资格运行 0、生产变更 0；计算及人工时间成本未计量。没有新增 Runtime、Schema 或测试修改。C3 保持 PARTIAL，Closure Contract 不变。
