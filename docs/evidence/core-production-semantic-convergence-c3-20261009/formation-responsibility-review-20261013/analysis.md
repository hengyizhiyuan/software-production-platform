# WORK_FULFILLMENT_PROJECTION：职责与最小架构缺口分析

2026-10-13（Asia/Shanghai）。本轮为架构分析与后续建议：只读源码、既有非 Holdout 开发证据及独立 Reviewer 允许公开的资格收据。没有修改 Runtime/测试、模型调用、Holdout 调优、历史事实修改或新增资格。

Repository Reality：证据 HEAD `9b1c8ec67b81ae722aff0bd68240f5da1ee07e31`；冻结应用 `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`；镜像 `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`；Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。

## 1. 结论与证据强度

**已证明的是 Formation 的候选构造与有界消费未取得真实泛化资格；尚未证明缺少一个外部、前置的 Reality/Evidence normalization Owner。** 实际 Evidence 消费及 Guardian 在四个真实场景中根本没有被调用，不能将其失败归因于下游 Evidence normalization。

现有模块已经具有库存身份、来源类型、可逆输入视图、原始语义/出处引用、Owner 必要前提、精确引用还原、安全收据、结构与独立语义门禁。不能再用“完全没有 normalization”描述它。

**最小设计问题：语义履行提案、来源/证据角色解析、精确候选编码仍被压在同一次完整模型输出里；现有准备和反馈多为表格/必要条件/错误观察，尚未形成足够可靠的模块内构造与恢复能力。** 这是代码可见的职责耦合与真实收敛不足之间的最小工作假设，**不是已经证明四类失败只有一个原因，也不是已证明必须新增架构层**。

建议复用现有输入准备、构造、解码和反馈，明确一个当前模块内的必要子能力：**来源与证据角色准备、候选构造及有界修复**。其输入是原权威记录及既有 Owner 契约，输出是派生、可复核的候选表示；不拥有新的事实、权限或 Assurance。

## 2. 当前真实职责链

| 步骤 | 实际模块 | 合法职责 / 不是其职责 |
| --- | --- | --- |
| 读取接纳 Reality | `fulfillment_inventory`，application/governed_obligations.py:666 | 保存 Fact/Clause/Item/Work Constraint/Context、源码/路径/原文及身份；不重解释 Human 输入、改接纳事实 |
| 准备必要前提 | `_owner_source_preconditions`:2132 | 从实际消费者谓词提供类型、来源支撑、Owner/Phase/方法资格；资格不代表该方法已履行或语义充分 |
| 可逆请求准备 | `_formation_inventory_view`、`_formation_source_table`、`_source_consumer_input`、`_fulfillment_wire_context` | 原 IR Item 共享、原来源表、精确类型/出处引用、库存及 Wire 指纹；不是新的语义中枢 |
| 提出派生方案 | `ModelFulfillmentCandidateProvider.form`:1941 | 模型选择组件、能力、f/u 支撑和目标，输出整个 Wire Candidate；r 是可审查说明，不是证明 |
| 安全/结构/接纳前检查 | `_safe_fulfillment_response_output`:1883、decoder、locator、`validate_projection_candidate` | 只收取可安全保留的响应，核对精确身份/原文/类型/权限/来源/处置；不从合法 Schema 推导语义 PASS |
| 独立语义判断 | 现有 Semantic Review | 判断派生计划对原要求的完整性、方法/阶段/来源语义一致性；不是履行 Evidence 或 Guardian Assurance |
| 接纳履行计划 | `FulfillmentBinding` | `BOUND_PENDING_EVIDENCE` / `UNRESOLVED` / `RETAINED_CONTEXT`；不是 SATISFIED，更不产生 Human 授权 |
| 取得真实履行证据 | 原 Verification、Native、Product Source、Candidate、Human Gate | 各自用实际 Artifact/Diff/记录/决定证明适用义务；保持独立 Guardian 最终消费边界 |

Formation 的目的，是从接纳 Reality 构造**怎样履行与怎样证明的合法计划**。通常生产文件、Diff 或未来授权尚未存在。因此不能要求先取得完整 Fulfillment Evidence 才允许 Formation，也不能用预生成 Evidence 解决候选失败。

## 3. 五类信息是否混淆

| 类型 | 此处的准确含义 | 不允许的晋升 |
| --- | --- | --- |
| Fact | 已接纳 EngineeringSemanticFact，带原关系/值/Scope/Qualifiers/authority/epistemic status；需求事实可以表达“标题必须是 X”，不是“产物已经实现 X” | 不因已接纳需求或状态名就视为履行完成；不把 working assumption 变 Human-confirmed truth |
| Observation | 特定 Owner 在特定时点观察到的 Wire、文件、请求状态、记录及错误；限定 identity/版本/范围 | “Provider completed”“原文存在”“Gate 记录存在”不能自行变语义正确或 Evidence PASS |
| Inference | 候选语义分解、方法选择、来源对应及等价性解释 | 推断不能产生 Human 决定、真实效果、原 Fact 或缺失证据 |
| Claim | 模型提出的“该组件可由此 Owner/方法在此阶段证明”的主张；包括 r、提案 Route 和 Review 的候选判断 | Claim 或 Review 判断不能代替实际验证；必要条件满足不能变成充分证明 |
| Fulfillment Evidence | 对应权威 Owner 已实际取得并核验、绑定具体源码/Work/Attempt/Candidate/阶段的证据 | 不能由 Formation、输入 normalization 或普通日志缺失自行创造 |

**正式类型和晋升门禁没有显示把五类信息统统混为 Engineering Truth。** `EngineeringSemanticFactCandidate` 禁止系统推断直接宣称 Human-confirmed；`FulfillmentProjectionCandidate` 和 Review consumption witness 明确是候选；持久收据 authority 为 `work-governance:derived-candidate-observation`；实际履行另由 `verify_fulfillment_fact_routes` 等消费者读取。

这不表示已有五个统一的一等类型。部分区别依靠现有类型，部分依靠 authority/epistemic status、阶段、收据与消费契约；Inference/Claim 在 Formation 中主要体现为候选 Route 与说明。建议先明确这些现有边界的使用，不因概念表新增五套数据库对象。

但**生成输入与构造任务有角色混装风险**：Fact、Clause、派生 Constraint、Context 使用同一源序号空间；f 是当前 Fact 依赖，u 是原始 provenance 支撑，来源文本同时用作语义依据/几何依据；必要 proof alternatives、未来待履行 Evidence 和实际 Observation 同时出现在大输入中。协议在代码中能分辨这些角色，模型仍需自己正确选取并编码全部操作数。

本轮 `WIRE_FACT_KIND_INVALID` 和来源对应失败与这种角色误用相容，但仅凭错误码不能证明模型内部怎样理解。没有独立语义 Review 或 hidden reasoning 证据，不能将这个风险改写成已证明的认知原因。

## 4. 四类失败能解释到哪一层

| 失败类 | 现有证据支持 | normalization 能做什么 / 不能做什么 |
| --- | --- | --- |
| Schema / Fact 类型 / 历史字符覆盖 | 候选格式、源序号角色或原文覆盖没有满足协议；当前已有 typed domains 与 exact locator | 准备精确有类型引用、从明确选择确定性编译字段、分类反馈；不能将非 Fact 转 Fact、猜测指代、扩展原文跨度或放宽 decoder |
| 同组件矛盾处置 | 同一原文跨度的提案被赋予不一致处置；不等于已经证明合法多组件不可表达 | 观察候选集合和互斥处置，支持模型在原预算内作明确语义选择；不能替模型删掉其中一个 Route 或自行将要求转背景 |
| 支撑来源对应未证明 | 所选 u 等原来源不足以通过现有消费者对应谓词；实际履行 Evidence 尚未进入消费 | 展示每个角色的真实可用前提和支持关系；唯一、明确且由原 Owner 可确定的编码可复用。多种语义可能或实际来源缺失仍须 UNRESOLVED；不能“规范化”出新的来源 |
| UNSAFE_JSON_RECEIPT | 原响应有 EXTRA_DATA/转义，安全性不能建立，因此未作为 Candidate 保留；未证明凭据泄露 | Provider 收取边界需要安全、身份绑定的错误观察与合法反馈恢复；上游 Reality 规范化不能修复任意非法 JSON，不能截取前缀/删除转义后冒充原候选 |

最后一类明确发生在 Provider 响应收取边界，前置 Reality 准备不足不能作为它的已证实原因。三类候选/对应失败加一类收取失败属于同一个 Owner 链的不同责任点；它们支持“模块内构造/恢复能力不足”，不支持“所有错误都应增加一种输入 normalization”。

四个新 WIC 库存的语义来源摘要均不同于旧 trial，输入→WIC 的语义忠实度比较仍 UNKNOWN；WIC→库存字段保存已证明。下游必须消费各自接纳 Reality，不能通过将其“规范化”成旧库存来消除合法随机变化。如果以后证明 WIC 错接纳，应回到原 IRK/WIC Owner，不能由 Formation 偷改。

## 5. 能力应放在哪里

**内置于 WORK_FULFILLMENT_PROJECTION，以其内部必要子能力落实。** 这是责任归属和内部结构两个层次，不是二选一。

- Work Owner 继续拥有库存/当前阶段/来源及履行绑定；Provider 继续拥有其输出收取、表示构造与反馈消费。沿用现有 ports、收据和预算。
- 不新增外部 Reality Normalizer、Evidence Broker、Adapter、全局 graph/ontology、Coordinator、状态机或新的事实 Owner。
- 现有上游拥有 Fact 接纳与原始 Observation；实际 Verification 等 Owner 拥有履行 Evidence；Formation 内部只准备引用、语义角色和证据**前提**，不接管两端权威。
- 不新增独立多阶段模型调用预算；“内部子能力”先指现有调用内的清晰输入/构造/校验/反馈职责。分阶段推理、更改跨 Owner 类型或 Wire Schema 若确实必要，需另行提出具体设计决策，不能以本分析自动授权。

## 6. 下一步最小修复建议

### 第一步：在非 Holdout 中先证明边界

沿用已知开发库存，固定一份接纳 Reality，人工审查建立至少两种合法完整履行计划作开发 Oracle，严格区分它们是测试计划而非 Human 授权或真实 Evidence。证明原 Validator/Review 契约是否能表达同一目标的不同分解、同一来源的多种角色及多来源协作。

同时固定错误对照：类型错配、支撑来源缺失/歧义、同组件冲突、真实义务遗漏、Future/Continuous 混淆、无安全可读 Candidate。每项预先明确是输入前提缺失、候选表达错，还是语义未确定；不从 Holdout 抄取字面输入/答案。

### 第二步：复用现有准备函数形成可复核的消费基线

将当前散落的来源/类型/authority/版本/原文/角色与 Owner 必要前提汇成同一库存上的明确视图。每个引用都能回到原记录，输入能精确重建。保留各来源各自义务；不能因同引文或相同含义合并其身份/覆盖要求。

区分：已知原文事实、已观察记录、尚未审查的语义判断、候选证据方法、实际证据存在状态。尤其 f 当前 Fact 依赖与 u provenance 原支撑必须在消费基线中分开呈现，**不必新增 FACT-only 索引空间**。先用现有 source kind 与字段合同落实。

### 第三步：减少模型承担的可确定编码，保留开放语义

模型继续负责“何种贡献、哪种合法消费者/阶段、如何组合、何处未决”。原 Owner 能从其**明确提交的选择**确定性恢复的 identity/header、来源引用、版本、精确目标和原文位置，应复用现有 reversible representation / compiler / locator。

不能用 compiler 填补语义选择、缺少的证明成员、缺失的原来源或新的 Fact；不能将非法原 Wire 静默改成合法候选。先形成一个仍属 Candidate 的临时表示，所有构造操作留痕，再由原完整 Validator 与独立 Review 检查最终对象。如果现有 Wire 无法承载这种职责拆分，应提交精确契约变更决策，停止该部分施工；不偷换“未改变最终门禁”来绕过协议。

### 第四步：按职责处理一次有界修复

在原一次反馈内分别标明：可确定的格式/引用错误；必须重新作语义选择的组件冲突；来源证明前提缺失；隐私不可评估；真实目标不合格。UNKNOWN 是不知道，NEED_EVIDENCE 是尚需合法 Owner 证据，不能变成模型补全任务。

修复保持原库存/源码/Attempt/原始 Wire 指纹与收据血缘。无合法 basis、未知请求结果、实际权限缺失或预算耗尽时停止；不给模型新的 authority，不追加每类错误专用模型请求。语义选择、最终计划仍未通过时不晋升。

### 第五步：资格门

先验证：合法路径/组合均可表达；确定性构造不产生新事实；观测/推断/Claim 不混入 Evidence；缺证据与真正缺义务持续不合格；非法 JSON 不被猜测修复；历史/replay/反馈身份及预算不变。必要时再执行固定非 Holdout 基线上的限定真实模型资格，取得正确语义与实际证据消费；受控 PASS 不等于真实模型成功。

只有上述开发资格成立并冻结 exact source/image 后，才进入另行授权的独立泛化复验。Holdout 不用于设计答案；C3 Closure Contract 不变。

## 7. 建议与暂不建议

建议：优先验证和修正**现有 Owner 内“语义提案—类型化角色/前提—可接纳候选构造—有界恢复”接线**。这是待实施方案，不声称上述每一项都缺失；先复用已有效的可逆输入、typed prerequisites、locator、观察与收据，避免重复实现。

不建议：增加一个前置平台级 normalization 系统，先“补齐”Reality/Evidence 再喂模型；继续增加 Prompt 禁令、schema 枚举或 Holdout case 特例；放宽支持来源/字符覆盖/安全收据/Guardian；改变预算让模型多试；以未来 Evidence 不存在为由强制阻断合法当前计划。

本轮最重要的修正，是停止把所有失败归因于模型没听话，也停止把所有拒绝归因于 Validator 太严格。现有事实支持的是内部构造和恢复责任仍未获得真实资格；具体设计必须在非 Holdout 的固定 Reality 上证明有效。

## 可核对依据

- [独立复验结果与证据边界](../holdout-requalification-20261013/report.md)、[逐次实际判断](../holdout-requalification-20261013/independent-review/qualification-final.json)、[安全分类](../holdout-requalification-20261013/independent-review/unsafe-json-classification.json)。仅使用公开允许资料，没有读取原封存输入/Oracle。
- [既有非 Holdout 对照](../non-holdout-root-cause-20261012/report.md)、[上轮 Owner 内部修复边界](../formation-module-adaptation-20261012/analysis-and-design.md)。不把夹具的合法计划当成历史模型结果。
- [应用 Owner 确切源码](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/application/governed_obligations.py)、[Provider 确切源码](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/providers/fulfillment_candidate.py)。
- [Fact 正式类型](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/domain/engineering_semantics.py)、[候选/绑定正式类型](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/domain/governed_obligation.py)、[真实履行 Evidence 消费](https://github.com/hengyizhiyuan/software-production-platform/blob/f52d39965826ba2e9ddcdba44c85e79bf5c43fc0/src/spg/providers/managed_context_fulfillment.py)。
- Watt 开发原则 §13/§14、原 C3 Mission。本文只记录架构分析与下一步建议，不改变任何权威契约，不授权实施或调用，也不宣布 C3 CLOSED。
