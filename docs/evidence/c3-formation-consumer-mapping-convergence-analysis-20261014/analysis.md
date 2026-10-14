# C3 Formation Consumer Mapping Convergence Analysis — ordinary34

记录日期：2026-10-14。**结论：C3 仍为 PARTIAL；本轮只分析，没有修改代码、门禁、预算、历史收据或运行环境。** 本报告讨论的是候选检查方法的语义映射，不能把方法资格、Review 结果或实际履约证据混为一谈。

## 1. 基线与证据

| 身份 | 精确记录 |
| --- | --- |
| 分支及分析起点 | `codex/c3-open-semantic-obligation-convergence`，`80b6e3babd5f1bb1869474a7fae655da57e2d779` |
| ordinary34 实测源码 / 镜像 | `d27707cb49558a0bc0071d9e3c4250fe88234427` / `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53` |
| 当前边界校准代码 | `f72707ab96ed67d167cd1dd26a8ddb55b716e323`；只做过定向验证，不能追认 ordinary34 的历史实测 |
| 原库存 | 19 项，fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29` |
| Guardian / ECF | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` / `5aa4f8833c359c15bd059eda5972aa3915bcc18c`；本次未调用 |

E1（实际运行）：[ordinary34 公开调用链](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-15.json)及 ECS 原件 `/data/watt/ai-native-evolution-20261013/nonholdout-15/private/ordinary34-owner-receipts.json`（SHA256 `8eea94156781896350044e1c8635f76d648d3212c9a0663b27909ec2d7930d4f`）。E2（原收据的逐项核对）：[Semantic Review 归责](../c3-semantic-review-failure-attribution-20261014/analysis.md)与[边界校准收据](../c3-formation-semantic-boundary-calibration-20261014/qualification-receipt.json)。E3（实现与契约）：[Formation provider](../../../src/spg/providers/fulfillment_candidate.py)、[Work/Fact Owner](../../../src/spg/application/governed_obligations.py)。以下序号只指该次原始库存和原候选，不另造身份。原始 Human 全文、私有模型响应和请求正文不复制到本报告。

## 2. Consumer Mapping 决策链

| Stage | Decision | Evidence | Responsible component |
| --- | --- | --- | --- |
| Input Understanding | source0/1 为字面标题、段落 EQUALITY Fact，包含目标文件关联；source2 是独立的文件范围 SCOPE Fact。模型没有交付独立、已验证的 understanding-only 状态；理解只可从其 route、quote、依赖和 rationale 观察。 | 原库存；首轮 32 条命名 route；[原始逐项核对](../c3-semantic-review-failure-attribution-20261014/analysis.md#31-第一次候选已有什么理解错在哪里)。 | 原 Work/Fact Owner 提供权威语义；Formation 模型提出解释。 |
| Semantic Candidate / Consumer Selection | source0/1 各有正确的 `ARTIFACT_CONTENT`（route0/2），又各多选 `GIT_DIFF_SCOPE`（route1/3）。其理由把“与目标文件关联”推成该 Fact 自身的变更范围要求；真正的文件范围由 source2 的 route4 单独承担。**错误在模型的消费者语义选择处产生。** | 首候选 raw SHA `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`；原逐项核对 §3.1。 | Formation 模型。 |
| Owner Binding | Owner 把模型提出的来源、目标和支持引用扩展为精确身份，并检查版本、方法资格与来源对应；没有替模型增删 route。`candidate_capabilities` 是必要资格域，不表示方法能证明当前 Fact。 | `_formation_binding_choices`、`_decode_fulfillment_candidate_wire`；`_fact_evidence_method_failure` 对非 SCOPE Fact 的 reviewed-method 条件。 | Work/Fact Owner，确定性绑定。 |
| Validator / 首轮反馈 | 首候选在 4 处字符覆盖缺口先停止，内层还报告 7 条派生来源对应错误；source0/1 的几何覆盖为 COMPLETE，但语义履约仍 UNKNOWN、证据 NEED_EVIDENCE。未执行独立 Review，**route1/3 的语义错误没有进入这次反馈**。 | 首轮失败收据 `9f11bb8c-618c-45fe-8f7b-fef91d07465d`；反馈 SHA `e3453b74164c512fcc110a9df22a35ca2d82e39b6d3ef6f88673ba816afcedd2`；`OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`。 | Validator/Owner 反馈；语义等价性未作判决。 |
| Feedback-driven local repair / 第二候选 | 第二调用显式 `replace17/remove0/append0`：10 条 quote 改为合法全文依据，7 条支持引用改回原 Clause；原 route0–4 等 15 条保留，**包含错误 route1/3**。覆盖和来源错误消失，候选得以进入 Review。 | 第二响应 SHA `a406d457ffefa61b5c2122dadc40994005addbd653707b979a279ca44239c7fd`；正式 Wire SHA `2dec2a802c84c08930108553559641b2891811f86479d527a7e3c21f387a4718`；原逐项核对 §3.2–3.3。 | Formation 模型选择编辑；Owner 只按原身份执行显式编辑并重验。 |
| Independent Semantic Review | 对 source0/1 判 false；两个额外 Diff 组件 route1/3 的 `complete_and_equivalent=false`，内容组件 route0/2 为 true。Git Diff 的 changed-path 证据不会随字面标题或段落是否正确而改变，因此不能证明两个 EQUALITY 值。独立拒绝有依据，整份候选 FAIL。 | Review candidate fingerprint `c6095b896416238aae5e85def5e073230e423634ca5f7cb7a8bbffbb2e4b9a62`；components fingerprint `bfa5420855019b144a0ed20fe196a828776c5562ca9b6e40d7b1e6d887c4b0c0`；终止收据 `184f4cc7-cb42-436e-9019-5f96a5fd854f`，`OBLIGATION_SEMANTIC_COMPONENT_MISMATCH`。 | 独立 Semantic Review；终态由现有 Gate 执行。 |

Review 另对 source3 的未来 Seal 证据时机、source4/11 的“新增页面”解释给出有争议的负判断；它们是独立的 Review 边界问题。**不能因其存在就翻转 route1/3 的正确拒绝，也不能用 route1/3 解释全部五个 source false。** 当前边界校准已澄清 Reviewer 请求中的计划阶段语义，但尚无新的真实 Reviewer 收据证明效果。

## 3. 失败类别：已证实与未证实

| 类别 | ordinary34 判断与界限 |
| --- | --- |
| A — Context Insufficient | **未证实。** 现有生成代码将原 Fact 的 relation/value/scope/qualifiers、完整来源、Owner 前提和 `existing_consumer_contracts` 传入请求。后者明确说 Git Diff 只证明 changed-path 集合，不证明允许文件内的内容；指令也明确区分 `ARTIFACT_CONTENT` 与 `GIT_DIFF_SCOPE`。模型同时选出了正确的内容消费者和 source2 的正确范围消费者，说明不是只因缺少这些能力选项而错。保存的实际请求 fingerprint/输入 SHA 支持调用同一实现路径；本报告没有保存或重放完整私有请求正文，所以不能声称逐 token 观察了模型注意力。 |
| B — Representation Insufficient | **未证实。** 现有 route 能表示同来源多组件、原 span、消费者、目标、支持引用、阶段和 rationale；第二响应的显式局部编辑也允许删除错误 route。source0/1 的正确内容方法与 source2 的正确 Diff 方法已经在同一候选中表达。没有证据表明需要新 Wire 字段才能表达正确方案。`r` 是候选理由，不是被 Validator 认可的语义证明。 |
| C — Decision Process Insufficient | **在反馈时序上已证实。** 当前两次 Formation 候选只有一次反馈；首轮结构失败阻断 Review，第二候选修完可评估的结构/来源错误后才收到真正的消费者语义拒绝，此时既有第二候选额度已用尽。局部编辑保留的是“反馈未点名的路线”，不是“语义正确的路线”。证据**不**证明必须大规模生成多种完整替代计划，也不支持增加无限候选。 |
| D — Responsibility Boundary | **Owner 边界本身无错配证据。** 模型负责提出“原义→消费者”候选；Owner 绑定来源、身份和必要资格；Validator 阻止结构/权限/来源越界；独立 Review 裁决开放语义等价性。把 EQUALITY Fact 一概禁止 Diff 会误伤合法的、值本身表达文件边界的 Fact；把 rationale 当证据则会削弱门禁。本次缺口是语义判决进入可消费反馈的时机，不是应让 Owner 替模型选消费者。 |
| E — Model Capability Limitation | **不能据此定论。** 一次已绑定 trial 中模型提出了错误额外消费者，但也提出正确内容/范围消费者；它从未收到 route1/3 的语义负反馈并获得同一 trial 的修复机会。无法据此排除模型在有效语义反馈下能修正，也不能保证一定能修正。 |

## 4. Self-Refine 实际效果

**Observed：** 反馈绑定第一响应、库存 fingerprint、Attempt 与原失败收据；第二调用选择显式局部编辑，修复 4 处覆盖与 7 条来源对应，不是简单重新生成整份候选。15 条未编辑路线得以保留，其中有正确的 route0/2/4，也有错误的 route1/3。随后全量 Validator 合格、独立 Review 拒绝错误消费者。没有第三候选，也没有用 Review 负反馈修复 route1/3 的机会。

**Conclusion：** 对本次已经可判定的结构/来源错误，内生 Self-Refine 有效；对 Consumer 语义选择，本次**未被检验为有效或无效**，因为语义反馈到达于最后一次候选之后。当前机制不能把“未获反馈”当“已证明正确”，也不能把第二次保留错误路线描述成无视了首轮 Consumer 错误反馈。失败保持真实 FAIL。

## 5. 最小有效改进方向

**推荐 Option B：在现有 Formation/Independent Review 的有界流程内调整语义反馈时机；不增新 Owner、适配层或候选次数。** 具体工程设计须先核对当前 Review 的实际调用预算及其完整计划输入契约，再作最小变更：对首候选中身份、来源、原文 span 与消费者定义均可确定的组件，允许既有独立 Review 给出**局部语义观察**，同时把几何/来源失败继续标为 NOT_EVALUABLE；将两类结果按原 Wire、库存、Attempt、Review 收据身份绑定，作为第二候选的一次反馈。修复后仍对**完整第二候选**执行原 Validator 与独立 Review，所有来源/权限/证据 Gate 不变。首候选的局部正判断不得被升级为计划 PASS，也不得跳过最终 Review。

这属于**有限流程/Reviewer 输入契约调整，需代码修改才可实现**；不能把它描述成当前已具备的能力。首候选虽不完整，route1/3 的精确源、方法和原文在当时已经可定位，因此有理由研究其局部语义判决是否可评估。若现有 Reviewer 契约或原有总调用预算无法在不增加资源/改变独立职责的前提下支持局部观察，**停止该方向并保留精确阻塞**，不能用确定性关键词规则代替独立语义判断，也不能暗中增加调用。该可行性在本轮未验证。

Option A 的现有信息展示、rationale 和局部编辑已经能表达本次正确方案；再写一段“Diff 不证明标题”的 Prompt 或给 EQUALITY/文件名加特例，既没有新的判决证据，也无法解决结构失败先阻断语义反馈的时序问题。因此不推荐将普通34专属规则、静态能力禁令或 Prompt 加长作为下一步。可用非 Holdout 的不同 literal、不同文件范围及合法路径值 Fact 作正负对照：应能在原预算内把错误方法指出并移除，保留真正的文件范围路线；缺证据/错版本/越权仍拒绝。若旧调用预算只支持一次独立 Review，则最小可执行行动是保留当前正确失败，先通过收据验证预算和 Review 契约边界，不声称已有闭环。

## 6. 最终回答

ordinary34 的**直接错误是模型把文件关联误映射为额外的 Git Diff 消费者**；**可证实的系统收敛缺口是语义反馈晚于本次最后一个可修复候选**。现有上下文和表示并未证明不足；Owner、Validator 与独立 Review 的严格拒绝有必要保留。故不能简单归因于“AI 不够聪明”；更准确地说，**系统已能让 AI 提案、局部修复并由独立门禁发现错误，但尚未在同一有界循环中给它消费该类语义负反馈的结构**。下一步应先验证上述有限流程调整在现有独立 Review 契约和预算内是否可行；可行才实施并用非 Holdout 对照资格证明，不以本报告宣布 C3 CLOSED。
