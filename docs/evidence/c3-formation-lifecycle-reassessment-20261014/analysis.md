# C3 Formation Lifecycle Reassessment

2026-10-14（Asia/Shanghai）。仅分析；C3 保持 **PARTIAL**。本次没有代码或测试修改，没有测试、模型调用、镜像构建或真实资格运行，不修改历史事实、生产环境及 Holdout。

## 1. 结论

**现有 Formation 不是裸的“生成 → 失败后再生成”。它已经是有身份连续性、评估、局部演进、重新验证和如实停止的有界候选生命周期。当前不足是：局部决策修订与完整候选的一致性尚未形成被真实资格证明的联合收敛能力。**

因此应当细化现有 Owner 内的演进责任：一次修复必须考虑完整候选、变更影响及全部残余要求。现有证据不要求新增独立生命周期阶段、Agent、Owner 或模型调用，也不证明增加候选次数可以解决问题。

两个判断必须分开：

- **安全及接纳边界：** 当前受查路径能保留来源/权限边界，拒绝不合格提案，并在既定预算内停止；这不是任意输入下安全性的普遍证明。
- **生产收敛资格：** 尚未证明能可靠地把局部语义修正组合为整体有效计划；最新探针没有进入独立 Review。不能将正确拒绝等同于生产能力已充分。

“Generation → Evaluation → Evolution → Convergence”可作为描述同一 Owner 责任的分析视角，但名称本身不提供缺失能力。尤其不能把 Convergence 当成一个会自动产出成功的新增阶段。

## 2. Repository Reality 与证据范围

| 项目 | 本次核对身份 |
| --- | --- |
| 分析起点 HEAD | `2e4895a9a693cb87f76899ef3678f4ba27eeac32` |
| 实际工作分支 | `codex/c3-formation-ai-native-convergence`；分析前与本地及远端旧 C3 分支指向同一 HEAD；未切换、合并或重置分支 |
| 最后相关应用源码 | `a1d99fd8e60967e7601fe1e265fa9ef6c66ecc0e` |
| 应用 Git Tree | `5aeaf6236c67e8f7ac7a510a720b1f82301c2c81` |
| 最新探针实际镜像 | `sha256:58c07b462a438aa936ba59857624559e77230258d24bd960512706a90d121803` |
| 对应 Guardian / ECF | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` / `5aa4f8833c359c15bd059eda5972aa3915bcc18c`；本次未运行或修改独立 Owner |

核对现有源码、公开原始收据、历史阶段报告和此前逐字段取证。没有重新执行 Validator、重放模型或构造反事实 Candidate。私有原请求的结论沿用已标明身份的既有取证，不冒称本轮再次读取全部私有原件。已有未提交的 g50/g51 材料和开发库存保持原样。

提交现场补记：分析期间该工作分支被外部从 `codex/c3-formation-ai-native-convergence` 重命名为 `claude/c3-formation-ai-native-convergence`，Git reflog 确认重命名仍位于上述分析起点。本轮没有执行该重命名；文档提交沿用现场实际分支，不改动旧 C3 分支指针。

主要证据：

1. [最新调用及终态原收据](../c3-formation-decision-action-consistency-20261014/receipts/ordinary34/retained-first-result.json)、[动作及失败集合](../c3-formation-decision-action-consistency-20261014/receipts/ordinary34/action-observations.json)。
2. [完整候选协调与原请求核对](../c3-formation-candidate-convergence-analysis-20261014/analysis.md)、[Action Consistency 实现及资格范围](../c3-formation-decision-action-consistency-20261014/report.md)。
3. [历史失败演进与 ordinary34/41 真实 Review 边界](../c3-formation-failure-boundary-analysis-20261013/analysis.md)、[Hardening 原始进展记录](../ai-native-integrated-hardening-20261013/progress.md)。
4. [语义责任及来源资格入口校准](../c3-formation-semantic-boundary-calibration-20261014/report.md)、[原型与稳定契约归责](../c3-semantic-revision-behavior-attribution-20261014/analysis.md)。
5. [独立 Holdout 公开复验报告](../core-production-semantic-convergence-c3-20261009/holdout-requalification-20261013/report.md)。仅参考公开资格边界，不读取封存输入、Oracle 或据其设计修复。

此处 Candidate 指 **Fulfillment Projection 方法计划候选**，不是已密封的软件产物 Candidate。方法资格、实际履约 Evidence、Guardian Assurance、Human 授权与 Acceptance 均为不同事实。

## 3. 当前 Formation 的真实心智模型

### 3.1 实际执行链

依据 [`_form_fulfillment_projection`](../../../src/spg/application/governed_obligations.py:3841)、[`candidate_construction_preconditions`](../../../src/spg/providers/fulfillment_candidate.py:566)及 Provider 的现有协商分支，主路径可概括为：

```text
固定 Work Reality / Inventory / Source / Capability / 已协商契约
    ↓
恢复原收据与累计预算；身份不明或已终态则按原事实停止/返回
    ↓
形成未接纳提案（当前主路径优先完整角色计划）
    ↓
Owner 精确绑定 / 构造 / 定位 + 当前可评估的确定性校验
    ├─ 失败且可合法修复、有剩余额度
    │    → 绑定原输出的失败/关系观察
    │    → 重开决策、显式局部编辑
    │    → Owner 重建整个候选，再走原校验
    └─ 当前确定性资格通过
         → 独立 Semantic Review
         → 合并复核
         → 接纳派生计划，或在原剩余额度内反馈，或未决停止
```

不是每个失败都可重试。未知传输结果、身份漂移、无安全 basis 等有直接停止路径；既定两候选、一次反馈、最多四逻辑调用不会因恢复重置。未使用的 Review 槽位不自动变成 Formation 额度。

### 3.2 已有演进能力及限制

| 当前机制 | 已有责任 | 不能推导的能力 |
| --- | --- | --- |
| Understanding / Evidence / Convergence state | 区分原 Fact、提案 Claim、观察与缺失 Evidence，表达 unknowns/alternatives、CONTINUE/REPAIR/STOP 等 | 字段存在不证明模型已完成全局理解或能自主选择有效策略 |
| 原 Wire 与 feedback lineage | 原输出、库存、Attempt、父收据绑定；恢复不生成新的权威事实 | 身份正确不证明内容正确 |
| replace/remove/append + Decision Revision | 重评局部语义选择；Owner 只应用模型明确选择的操作 | “局部编辑”不强制只改一条，也不保证所有保留项都正确 |
| Decision → Action consistency | 结构化 retain/revise/remove/unresolved 与实际动作相符 | revise 一个字段不等于整体方案取得进展 |
| 完整候选重建及原 Validator | 对构造后的整体重新检查，拒绝重复、缺失、错误引用等 | 拒绝不等于生成端已经知道如何协调下一提案 |
| Independent Review | 独立判断候选方法是否忠实、阶段及证明归属是否成立 | 不是最终履约或 Guardian，也不能在确定性失败后算作已调用 |

源码 [`OwnerConvergenceDecision`](../../../src/spg/domain/refinement_contract.py:36)已有 progress/stop/strategy 表达；当前生成侧进展主要以“完整提案须通过原 Validator 和独立 Review”描述，终态以有无合法接纳判断。不能说系统没有进展信号；但它没有在本次真实修复中证明**跨贡献影响与残余目标的联合兑现**。

当前协商还保留“理解 Claim → 完整角色绑定”的路径。历史 trial11 曾在首次完整方法计划形成时耗尽两候选额度，随后主路径改为优先完整初候选、将剩余额度用于修复。这个真实教训反对仅为流程图新增一次模型阶段：内部职责分解不应被机械解释为逐阶段增加调用。

## 4. 跨 C3 资格的演进证据

| 阶段 | 已有事实 | 对生命周期的含义 |
| --- | --- | --- |
| 历史独立 Holdout | 公开复验真实模型 0/4，均未接纳、未进入 Review；当时源码 `f52d3996` | 证明旧版真实泛化不足；不是当前源码的复验结果，也不能从错误标签推出必须新增 normalization 阶段 |
| Hardening 早期 | 字段域、格式修复 basis、消费指令投影、重复收据容量、显式编辑形状等存在真实工程缺口并被修正 | 恢复入口及反馈连续性本身必须正确；不能把这些故障全部称模型波动 |
| ordinary41 / d277 trial14 | 覆盖修复后仍有未决及来源对应不足，0 Review | 前置修复让后续问题可见，不等于全部是新问题；之后 Owner 校准建立合法资格入口，但未追认旧候选成功 |
| ordinary34 / d277 trial15 | 覆盖及部分来源修复后实际进入 Review；错误 Consumer 保留并被拒，另有计划/履约阶段判断偏差 | 评估和局部演进真实发生；“一次结构修复后还可能有语义失败”是事实，不证明多调用必能成功 |
| Assumption Review 原型 | 模型实际 remove 额外 Consumer，保留其他贡献；整体仍未接纳 | 现有表示可以表达该局部合法解；单次成功不构成稳定因果或完整收敛证明 |
| 稳定 Decision Revision | 决策确被重开，但部分输出只改解释、保留原 Consumer | 解释变化与动作变化必须区分；不能仅凭 rationale 认定语义修正 |
| 最新 Action Consistency 探针 | 模型自主改变 Consumer，声明与动作一致；整体仍因覆盖及一致性问题失败 | 当前瓶颈已不只是“能否重开/修改一个决策”，而是局部变化与整个候选共同成立 |

这些试次不是同一输入请求条件下的重复抽样：源码、请求表示和反馈契约曾变化。不能据此推导成功率、模型固有能力上限或某项提示的独立因果。

## 5. 最新证据：收敛在哪一处断开

最新探针绑定19项来源，库存 fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`。第一响应为明确标注的保留控制，不是本次新模型调用；其后仅一次真实 Formation，request `bf74aa3e-13f7-4889-89dd-39c64441ee1f`，response SHA `48d9d575159a5db2a99f92e97c73d79916d7e709a5c7ef16ed2b272a43127428`。

1. 原32条路线已包含内容贡献0/2、额外 Diff 贡献1/3、真正范围贡献4，以及依赖前两个 Fact 当前内容证明的路线5。
2. 模型对1/3声明 revise capability，实际 Diff → 内容；Owner 观察 `STRUCTURALLY_CONSISTENT; SEMANTIC_VALIDITY_UNKNOWN`。
3. 20项 replace、无 remove/append；0/2保持，因此1/3与原内容贡献形成两组同组件/同能力重复。
4. route5 的显式依赖及目标不变；每个依赖的当前内容证明候选由1条变为2条。现有唯一证明条件不再成立。这里是**计划内引用/证明路线资格**，不能声称缺少新的运行时外部 Evidence 或 Human 批准。
5. source3/4/10/11的原引用覆盖缺口仍在，相关路线改理由没有修正跨度。实际停止谓词是 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`。

重复与依赖问题来自可独立评估的 Owner 前提观察；不能声称完整最终 Validator 和 Review 已逐门运行。本次 Review 调用数为0，Provider completed，实际输出4,303 tokens、reasoning0，未耗尽16,384上限，无传输重发。

[`_construct_local_candidate`](../../../src/spg/providers/fulfillment_candidate.py:743)确实应用编辑并重建整个候选。因此断点**不是“缺少整体重建/校验阶段”**，而是模型提交的编辑集合没有联合解决变更后的贡献关系与原来尚未满足的要求。先改一个错误、再产生关联错误，说明局部正确不具备自动组合性；也不能用“错误数减少”单独证明进展。

## 6. 四种主要解释的证据权重

| 解释 | 支持证据 | 限制/反证 | 判断 |
| --- | --- | --- | --- |
| 缺少信息 | 角色局部构造路径没有投影 `_primary_meaning_instructions` 中额外去重段落；没有本次拟议编辑的联合影响表达 | 完整库存、全部原路线、组件分组、四项覆盖反馈、linked proof 唯一性规则实际已给出 | **不是原始必要事实整体缺失。** 有明确消费投影差异；是否为失败主因尚未证明 |
| 模型能力不足 | 最新输出只完成局部目标，未协调已知关系；覆盖反馈未落实 | 此前同模型能删除额外贡献、修复覆盖并进入 Review；未做同条件对照 | **本次全局协调失败已观察；模型固有上限 UNKNOWN。** 不宜以“不够聪明”终结归责 |
| 缺失生命周期阶段 | 没有被证明有效的、面向本次编辑集合的全局协调责任兑现 | 生成、评估、演进、整体重建、Review、停止已存在；新的阶段名字不会产生协调能力 | **缺的是现有演进环节的联合协调能力，不是已证明缺少一个独立运行阶段。** |
| Candidate 表示不足 | 路线级操作要求模型自行协调多个选择，表达成本存在 | 组件身份、linked refs、显式多路线编辑均已有；实际历史 remove 能表达取消冗余贡献，未触达编辑上限 | **没有证明合法解不可表达。** 暂无依据引入新图、IR 或替代 Wire |

两候选预算确实是停止边界，但尚未证明是根因：原覆盖信息已给出而未修复；多一次可能修复，也可能继续局部打补丁。未用的 Review 槽位不能借给 Formation。本评估不提出提高预算。

**最有证据支持的解释：生成端的联合决策/影响协调尚未兑现，既有反馈的表达和消费路径存在可核对差异；尚无因果证据把它归结为单一缺字段、模型极限、新阶段缺失或表示无能。**

## 7. 是否需要不同生命周期抽象

需要的是更准确的**职责抽象**：Formation 演进一个有关系和未决要求的整体提案，局部编辑只是实现手段。不能将“每个被重开的决策动作正确”当作候选演进成功。

| 分析中的生命周期责任 | 当前对应 | 需要补强的最小责任 |
| --- | --- | --- |
| Generation | 未接纳的理解/方法提案 | 继续允许多种合法选择，不要求首次完美 |
| Evaluation | 当前可评估 Owner 观察、Validator、适用 Review | 区分局部动作一致、整体资格、不可评估项；已有拒绝条件不变 |
| Evolution | 原身份绑定的反馈、决策重开、多路线编辑 | 在同一剩余候选中联合处理局部变化、已有贡献、依赖与全部残余目标 |
| Convergence disposition | 派生计划接纳或 UNRESOLVED/STOP；终态持久恢复 | 必须以实际完整资格判断，保留未决；不把修订动作或文字改进当成已收敛 |

这个视角不要求四次调用，也不要求新增四种数据库状态。Convergence 是现有 Owner 在边界内对结果及停止的判断；安全停止是合法终态，但不能替代本 Mission 所需生产资格。

## 8. 最小架构校准建议：完整候选是演进责任单位

**在现有 WORK_FULFILLMENT_PROJECTION 的 Repair 契约中，明确“完整候选及其未决要求”是演进责任单位；一个决策的修订应与受影响的既有贡献和证明关系联合协调。** 不新增外部层或独立运行阶段。

最小能力边界应涵盖：

1. **改动影响可见。** 利用已有 source/component 分组与显式 linked refs，模型能将拟改贡献同保留贡献、依赖它的路线一起考虑；Owner 提供可证实关系，不给出删除或改选 Consumer 的标准答案。
2. **整体编辑决策。** 模型可在原 replace/remove/append 内提出联合选择，既不机械保留全部旧路线，也不整份盲目重生。保留内容、来源、阶段、权限和覆盖约束。
3. **残余要求连续。** 原失败目标不能因局部语义修正被遗忘；未解决的覆盖、支撑、版本或权限条件保持显式失败/未决，不以解释改写声称完成。
4. **进展必须关联结果。** 用实际编辑后的贡献、依赖和原 Gate 结果解释变化；允许某局部改善但整体失败。暂时错误增加不自动证明修复毫无价值，也不允许据局部改善给予接纳。

这不是增加一个检测器：现有检测已经发现这些问题。它也不是依靠复制去重段落或增加 Prompt 禁令；要补的是**现有关系在生成和修复决策中的联合消费责任**。当前关系、编辑表示及 Owner 重建足以作为最小起点，尚无证据需要新语义图或全局 reconciliation 服务。

本报告只提出能力及责任范围，不决定新增字段、算法或额外模型步骤。**已经证明的是本次候选没有完成整体协调；尚未证明任何具体新契约一定优于现有契约，也未证明必须新增运行阶段。** 后续若决定实施，应先界定现有输入如何支持联合决策，避免仅增加字段包装就声称实现智能收敛。

## 9. 后续资格应证明什么（本轮未执行）

沿非 Holdout 库存验证通用责任，不能只问 ordinary34 是否 PASS：

- 局部消费者改变后，能协调保留/替代/移除等不同合法组合；无关正确贡献保留。
- 被影响的显式依赖仍具有正确身份、版本、目标与必要证明关系；不能只修显眼路线。
- 原残余目标有实际修复或明确未决，错误来源、权限、重复与缺失仍拒绝。
- 最终完整候选继续经过原 Validator 和适用独立 Review；保留原两候选、一次反馈及累计调用约束。
- 提案、反馈、编辑与观测严格绑定实际 fingerprint、Attempt 和持久收据；恢复不重新开预算或复活历史终态。

不要求每个合法输入在一次试次都成功；需要的是可解释、有界且有真实证据的适应与收敛。未能收敛时允许如实停止。后续生产及独立泛化资格仍按原 C3 Contract，不新增本轮关闭条件，也不把文档或受控实验替代它。

## 10. 最终回答

1. **当前心智模型是什么？** 是“固定权威基础上的有界提案 → 当前可评估校验 → 身份绑定的修订/完整重建 → 原校验与独立 Review → 派生计划接纳或停止”，已有演进机制；概括为 Generate/Repair 会漏掉其保护与评估能力。
2. **是否需要新生命周期？** 需要把完整候选的联合协调明确为现有 Evolution 责任；尚无证据要求独立新阶段或新编排系统。“Generation/Evaluation/Evolution/Convergence”适合澄清职责，不能被当作实现已经充分。
3. **主要剩余差距是什么？** 局部修订与整体贡献/依赖/残余目标没有在本次输出中联合成立。模型协调偏差已观察、输入消费差异已核对；模型能力上限、增加阶段的收益以及更多候选效果均 UNKNOWN。
4. **最小改变是什么？** 继续在原 Formation Owner 和原一次 Repair 内，使其对变更影响与完整候选负责；复用关系、表示、门禁、预算及收据。不是再加 Validator、静态规则或普通34特例。

**生命周期框架在治理与停止边界上已有基础，在可靠整体收敛上尚未取得充分资格。下一步要补的是同一有界演进中的联合协调能力，而不是用更多轮次或更多阶段名称替代它。**

本轮新增模型/测试/构建消耗为0；分析与文档的计算及货币成本 UNKNOWN。C3 状态、历史结果、Guardian 门禁和正式环境均不变。
