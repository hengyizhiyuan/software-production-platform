# C3 Formation Candidate Convergence Root Cause Analysis

2026-10-14。分析 HEAD `237b11373d8d64b8b75df67c94bc993b6e905a81`；应用源码 `a1d99fd8e60967e7601fe1e265fa9ef6c66ecc0e`；实际镜像 `sha256:58c07b462a438aa936ba59857624559e77230258d24bd960512706a90d121803`。原 C3 分支，C3 PARTIAL 不变。

**最强证据指向：局部决策修正已经发生，但修复候选没有同时协调已有贡献、受影响的证明依赖及原来尚未修复的覆盖要求。两个重复路线与 linked Fact 证明不可用并非三个独立根因；后者可由前者造成的证明候选数量翻倍解释。**

本轮仅分析代码、原请求、原响应和持久收据。不修改代码/测试/门禁，不运行测试、模型或新资格；不修改历史数据、不使用 Holdout。没有执行“修补后候选”或反事实验证。

## 1. 取证基础与当前状态

原库存19来源，fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`。原首 Wire SHA `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`。

最新真实修复 request `bf74aa3e-13f7-4889-89dd-39c64441ee1f`；输入文本 SHA `543de3b9b9f789c16aee2926685b98af1f848a5f13df0e1b6cbd2b1f8463cddd`；响应 SHA `48d9d575159a5db2a99f92e97c73d79916d7e709a5c7ef16ed2b272a43127428`。本轮核对实际保存的 `request-2.json`，其输入 SHA 与响应 Owner 收据中的 Provider 观测一致。

主要证据：[实际调用及终态](../c3-formation-decision-action-consistency-20261014/receipts/ordinary34/retained-first-result.json)、[编辑与完整失败集合](../c3-formation-decision-action-consistency-20261014/receipts/ordinary34/action-observations.json)、[私有恢复清单](../c3-formation-decision-action-consistency-20261014/receipts/private-evidence-manifest.json)。完整私有材料在 ECS `/data/watt/ai-native-evolution-20261013/decision-action-consistency-20261014/private/qualification/retained-first/`。

| 能力/要求 | 当前事实 | 资格边界 |
| --- | --- | --- |
| 语义误解修正 | 原额外 Diff Consumer 实际改为内容 Consumer，系统没有代选 | 已观察到局部语义方向修正，不再归因于“模型不能修订”；未取得完整独立语义 Review |
| 决策重开 | route1、3 进入反馈、重评、显式编辑 | 已实现并被真实使用 |
| Decision → Action 一致性 | 声明 revise capability，实际也改变 capability | 已通过当前结构一致性检查，不等于方案正确 |
| Candidate 完整性 | source3、4、10、11 原字符覆盖缺口仍在 | FAIL；不能把字符覆盖缺口直接宣称为四项业务义务未理解 |
| 全局一致性 | 两组同组件/同 Consumer 重复；关联证明唯一性失效 | FAIL |
| Evidence 收敛 | 必要证明计划未闭合；没有执行实际内容 Verification | 当前是证明绑定/可用性问题；实际履约 Evidence、Review、Guardian 均不能推断 PASS |

这里的 Candidate 是未接纳的 Fulfillment Projection，不是修改历史密封软件 Candidate。当前没有进入新 Worker、实际产物 Verification 或新的 Guardian Assurance。

## 2. 失败链重建

### 2.1 原候选与反馈

原首响应是已冻结的受控历史输出，并非本轮新的 Provider 生成。32条路线中：

- source0：route0 已为 ARTIFACT_CONTENT，route1 是额外 GIT_DIFF_SCOPE；两者对应同一规范组件。
- source1：route2 已为 ARTIFACT_CONTENT，route3 是额外 GIT_DIFF_SCOPE；同样对应同一规范组件。
- source2/route4 是真正的 Git 文件范围贡献。
- 混合验收 source3：route5 为当前内容贡献，route6 为 Candidate Seal；route5 显式依赖 source0、1 的 Fact 当前内容证明。
- source3、4、10、11 已存在覆盖缺口；另有 supporting-source 前提失败。失败集合不只包含两个 Consumer 风险。

现有风险诊断不是自动语义判决。它指出方法/原义关系需要重评；模型随后选择改变 Consumer，Owner 检查其声明与动作相符。

### 2.2 最新修复实际做了什么

模型返回20项 replace、0 remove、0 append。Owner 将全部编辑应用于原32条路线，构造后的候选仍为32条；没有漏执行一个 remove，也没有悄悄恢复旧 Consumer。

| 原路线 | 实际变化 | 全局影响 |
| --- | --- | --- |
| 0、2 | 完全保持原路线 | 两条既有内容贡献仍存在 |
| 1、3 | 仅 capability 与 rationale 改变；Diff → 内容 | 与保留的0、2变成同组件/同 Consumer 重复 |
| 4 | 原样保留 | 真正文件范围贡献未丢失 |
| 5 | 只改 rationale；quote、目标、linked Fact refs 不变 | 原覆盖缺口仍在；现在其依赖各有两条当前内容证明候选 |
| 6、17、20 | 原样保留 | 原角色保留，但无法修复其他路线未覆盖部分 |
| 7、8、9、16、18、19 | 只改 rationale，原 quote 不变 | 字符跨度未变化，原覆盖失败没有实质修复 |

代码路径：[`_construct_local_candidate`](../../../src/spg/providers/fulfillment_candidate.py:743)重建完整候选；[`_decision_action_observation`](../../../src/spg/providers/fulfillment_candidate.py:468)只核对被请求决策的结构化处置，不负责全局语义协调。**不是“系统没有重算完整 Candidate”，而是重建出来的整体编辑方案本身不一致。**

### 2.3 重复贡献如何传播到证明可用性

原始和最终收据均显示：route0/1 具有同一个 component ID `7f9be2e6f3cfc7372c92f82cb78431afe7d1a81ba8433a87731438e335dbed62`；route2/3 具有同一个 component ID `17696c29e9cde1515646aae8d546eeca8c5d6f161182349e2431dfa9e13be18f`。模型可见上下文还给出相同 span/quote SHA 分组，不能把原引用形式差异当作不同贡献。

[`validate_projection_candidate`](../../../src/spg/application/governed_obligations.py:1380)要求 `(component_id, capability)` 不重复。改完 Consumer 后，两组都违反该原有条件。

同时，[`linked_component_dependency_failures`](../../../src/spg/providers/managed_context_fulfillment.py:431)对混合验收的 linked Fact 要求：每个依赖有且仅有一条匹配 Work Reality/source/target 的当前内容证明路线。

| route5 的显式依赖 | 修复前当前内容路线 | 修复后当前内容路线 | 变化 |
| --- | --- | --- | --- |
| source0 的 Fact | `[0]` | `[0,1]` | 1 → 2 |
| source1 的 Fact | `[2]` | `[2,3]` | 1 → 2 |

route5 自身 linked refs 与目标不变，这些证明路线也保留相同目标和共同版本。因此 `OBLIGATION_LINKED_FACT_CURRENT_PROOF_UNAVAILABLE` 在本样本中有直接的数量原因：`len(proofs) != 1`。**不是已经证明缺少新的权威事实、需要未来 Human 决策，或要求此刻拿出尚未生产的运行时履约证据。** 本结论来自代码谓词与原记录的匹配，未执行删改后候选验证。

### 2.4 另一条独立的未收敛链：原覆盖要求未修复

| 来源 | 原反馈缺口 `[start,end)` | 最终缺口 | 非空白位置数 |
| --- | --- | --- | --- |
| 3 | `[39,42)`, `[71,72)` | 相同 | 4 |
| 4 | `[13,14)`, `[22,23)`, `[54,55)` | 相同 | 3 |
| 10 | `[39,42)`, `[71,72)` | 相同 | 4 |
| 11 | `[13,14)`, `[22,23)`, `[54,55)` | 相同 | 3 |

这四个来源的原 quote/spans 没有因 rationale 变化而扩展，故原覆盖谓词仍然失败。source3与10、4与11虽然文本相同，却属于不同权威来源，不能互相替代覆盖或合并删除。上述14是按各来源身份统计的位置，不是14项新业务要求。

收敛断点可概括为：

`首候选 → 完整原反馈 + Consumer 风险 → 决策重开 → 正确执行局部 Consumer 改动 → 未协调保留路线/证明依赖，未落实原覆盖修复 → 完整候选仍拒绝。`

**实际终止谓词**是 Wire 解码的 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`。重复路线和 linked Fact 失败是现有 Owner 对完整可定位提案形成的独立前提观察；不能把它们描述成完整最终 Validator/Review 已逐阶段执行完毕。Independent Review 调用数为0。两候选边界正常停止，没有 Provider/传输/容量错误。

## 3. Repair Context 到底缺什么、已经有什么

本轮直接检查模型收到的请求，确认它已包含：

- 完整库存、32条原路线、Consumer Contracts、同来源组件分组及 located component ID。
- source0 的 `[0,1]`、source1 的 `[2,3]` 共同 span/quote 分组，及两个现有 Consumer。
- 全部四个来源的精确覆盖缺口；`repair_targets` 中4项覆盖目标和2项 Consumer 重评目标，没有删减原失败。
- 原 `current_fact_dependency_rule`：混合验收 linked Fact 必须有 **one exact current content route**，匹配 source/version/target；原路线中有显式 linked refs。
- 实际修复指令要求比较每个来源的 UNION coverage、重新检查全部失败。实际未读取上下文的模型内部过程 UNKNOWN。

因此，“只告诉哪个 Consumer 错，没有提供其他路线/覆盖/依赖”不符合事实。已存在关系和完整数据，不能再假设需要从零建立通用语义图。

同时有两个真实的消费局限：

1. 上下文是**原候选的关系及失败快照**；没有与本次拟议编辑联合的影响决策，明确处理改动后的同组件碰撞、反向依赖证明数量及全部残余修复要求。模型目前须自行跨多个现有视图完成这些协调。
2. 源码 [`_primary_meaning_instructions`](../../../src/spg/providers/fulfillment_candidate.py:1469)有一段按 component/Consumer 合并重复贡献的指导，但本次局部构造走 [`_construction_consumer_instructions`](../../../src/spg/providers/fulfillment_candidate.py:1546)，只投影基础 Consumer 文案；该具体去重段落**不在实际发送的 instructions 中**。不能用“代码里有文字”冒充已消费。其他完整覆盖/全体失败指导及组件数据仍在，故这不是全局信息完全缺失，也不足以证明复制这段话就能解决问题。

另一个可观察不对称是：新增 `decision_revisions` 对两个风险决策要求显式处置；四项原覆盖目标依然由原反馈和完整候选 Gate 约束，没有相同的逐目标动作兑现记录。它可能影响修复聚焦，但本轮不能从输出反推模型的注意力或认定唯一因果。

## 4. A/B/C/D 归责

| 类别 | 支持证据 | 相反/限制证据 | 结论与置信度 |
| --- | --- | --- | --- |
| **A Model planning limitation** | 同一实际输出修正1/3，却保留已有0/2造成重复；依赖证明数量随之失效；原覆盖目标只改理由未改 quote | 模型确实协调了20项编辑；此前原型能删除额外路线并保留内容/范围；只有本次有限样本，不能证明模型普遍不能全局规划 | **对本次全局协调失败：高。对模型固有能力上限：不足。** 最直接的行为归责 |
| **B Repair Context insufficiency** | 没有将拟议编辑与已有贡献/反向依赖/残余要求形成联合影响决策；具体去重指导在本路径未投影；目标兑现形式有不对称 | 原组件组、全部路线、覆盖缺口、linked 证明唯一性规则都实际提供。并非缺少判定必需的原始事实 | **对具体投影/消费差异：高；对它导致本次失败：中，尚非因果证明。** 是最窄的能力改进方向，不是“上下文全缺” |
| **C Candidate representation limitation** | 当前是路线级编辑，跨路线取舍须由模型协调，没有专门的联合替代操作 | component ID、linked refs、显式 replace/remove/append 和完整 Owner 重建均已有；32条候选、20项 replace 未触及64项操作上限；此前同一原 Wire 的实际 remove 已成功表达该局部解 | **不支持“合法解无法表达”，置信度高。** 表达成本可能影响行为，但没有证据要求新图、新 IR 或重做表示 |
| **D Candidate budget limitation** | 第二候选终止后没有继续消费新重复/依赖诊断的修复槽位 | 已知覆盖缺口在本次反馈中充分给出却未修复；第三候选可能改重复也可能继续局部修补。没有额外候选对照、成功率或成本收益证据；Provider completed、输出4,303未耗尽16,384 | **预算是停止边界，尚未证明是根因；更多候选能否解决 UNKNOWN。** 不支持提高候选次数 |

这次是冻结首响应加一次真实修复，不是两次新模型生成或候选数量实验。未消费的 Review 调用槽位也不能变成新的 Formation 额度。

## 5. 之前成功修正能证明什么

重新核对[原型原响应](../c3-semantic-misinterpretation-correction-prototype-20261014/receipts/result.json)及[完整只读观察](../c3-semantic-misinterpretation-correction-prototype-20261014/receipts/source-coverage-observations.json)：当时实际 remove 原1、3，replace17项、append0，形成30条未接纳路线；原内容0、2及真实范围4保留。覆盖仍失败于source3、10，另有来源对应未证实。

它证明“取消额外贡献、复用已有贡献”可以用现有表示完成；**不证明曾有一个完整普通34合格候选，也不证明本轮应复制那份编辑作为答案**。两次上下文/源码不同，不能用一次历史成功估计增加候选的收益。删除本轮重复也不能单独解决四项原覆盖缺口。

## 6. 最小下一项能力：在现有 Formation 内协调完整候选

**建议的最小能力是：在现有一次有界 Repair 中，将局部决策的改动影响与完整候选的残余要求联合协调，再提交一个相互一致的编辑集合。** 这是能力边界建议，不是实现设计或新增模型阶段授权。

它应复用已存在的来源/组件身份、覆盖观察和 linked Fact 依赖，至少能同时回答：

1. 改了一个贡献后，与哪些已有贡献重合？应该保留、替代、移除还是未决，由模型依原意提出联合选择，Owner 不自动选解。
2. 这些选择会使哪些现有依赖的必要证明数量或版本/目标关系变化？不能只看被编辑 route 本身。
3. 原反馈的每项必要修复，在最终提案中是否有实际贡献变化，还是只改变解释？未能解决的仍明确未决/失败。

核心是**生成端的整体协调**，不是再增一个全局检查器：现有 Owner 已经重建完整候选，已有 Validator 已能拒绝重复和缺口。也不是先建设新的 semantic contribution graph：本样本所需的组件组和依赖已能表达。应先让现有 Formation 正确消费、联合使用这些关系；不复制普通34答案，不把所有困难转成更多 Prompt/规则。

这里“欠缺”指本次真实输出未兑现的能力，不表示源码中完全不存在联合观察/依赖机制，也不证明必须改契约才能得到合法结果。已证实的生成偏差与可能需要工程改进的消费路径，应继续分开归责。

本报告不决定新字段、算法、额外调用或重构方案；不增加预算，不改变现有独立 Review 和事实/权限/证据门禁。是否存在必须修改系统契约的能力缺口，仍应区别于当前已证实的生成偏差，不能因一次拒绝自动扩张施工。

## 7. 明确回答

**After Decision Revision works, what is the next missing mechanism required for AI-native engineering convergence?**

下一项欠缺的是：**让修复候选对局部选择的整体影响负责，联合协调已有贡献、依赖证明与所有尚未修复要求的有界能力。** 当前已经能重开、修订并正确编码单个决策，也已能验证整个候选；缺的是在同一候选生成过程中把这些局部成功组合成一致的整体。

本次最直接表现为 A；B 的实际消费差异为最小改进方向提供依据，但还不足以证明唯一因果。没有证据要求新的表示架构、更多 Validator 或更高候选预算。原型和本轮都没有获得完整 Review，因此不能把局部修正升级成整体履约或 C3 Closure。
