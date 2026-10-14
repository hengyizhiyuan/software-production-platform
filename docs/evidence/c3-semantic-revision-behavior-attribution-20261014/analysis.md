# C3 Semantic Revision Behavior Attribution

2026-10-14。分析基线：分支 `codex/c3-open-semantic-obligation-convergence`，HEAD `d814bc4d3a1e2232cae199f1b76bc63a662a954d`；稳定化应用源码 `6afd558eabe5437b597611c3be39c99d8966941d`。

**结论：两次输入并不相同，不能认定某一句提示导致了成功。更直接的新证据是：稳定版模型在理由中已经否定额外 Consumer，并声称已移除，但实际返回的仍是保留该 Consumer 的 replace。剩余可观察失败位于语义处置声明与局部编辑动作的一致性，不能仅归为“没有重新理解假设”。**

本轮只读分析既有请求、响应、代码和契约。没有修改 Runtime、测试、Validator、Review、预算、历史收据或 C3 状态；没有调用模型、重新运行资格或使用 Holdout。只进行禁网请求重建及数据比较。

## 1. 比较对象及证据可信度

比较成功原型的一次真实修复与稳定契约的 `retained-first` 修复控制。两者均以同一原首 Wire 为编辑基础。**不使用稳定版新鲜完整运行作为 Consumer 修正对照**：该运行首候选本来就没有额外 Diff Consumer。

| 身份 | 成功原型 P | 稳定契约 S |
| --- | --- | --- |
| 实际模型请求 | `c8cdb73b-0228-45b4-bf75-242782296ad8` | `ce7a3ca9-3d61-4448-bdee-c3ca8c713e6c` |
| 输入文本 SHA256 | `8012a4ecf7d61206c49bd881419426f949cbd05ee7b79248513363b7338b6ea1` | `9b3477563f8dfcce2b54c07201aa1a717041acb06595374051417e09e3cf1955` |
| 响应 SHA256 | `3f1ad40064b1816a7de63881738dff91563ca982b37401aabb7d65d2a79586df` | `e9f99dce74bb979a17936a64707568f2f035cab5eddc588d22e0d5e827d3f578` |
| 输入文本 / 内嵌反馈 bytes | 192,789 / 74,067 | 188,408 / 69,123 |
| 路由1、3实际操作 | remove | replace，Consumer 未变 |
| 完整候选 | 覆盖等要求仍失败，未 Review | 覆盖等要求仍失败，未 Review |

原库存 fingerprint：`b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`，19个来源；共同原 Wire SHA：`893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`。

证据入口：[P 预检](../c3-semantic-misinterpretation-correction-prototype-20261014/receipts/preflight.json)、[P 实际响应](../c3-semantic-misinterpretation-correction-prototype-20261014/receipts/result.json)、[S 实际响应](../c3-formation-decision-revision-stabilization-20261014/receipts/ordinary34/retained-first-result.json)、[S 编辑观察](../c3-formation-decision-revision-stabilization-20261014/receipts/ordinary34/candidate-observations.json)。

### 实际请求核对方法

P 没有单独保存完整 `generate` 请求文件。本轮使用其原只读源码覆盖文件、已保存的 `prepared-feedback.json`、`prepared-preconditions.json`、原库存和此前的 `capture_request`，在原镜像中禁网重建请求；捕获器不连接 Provider。重建的 input SHA、instructions SHA、Schema fingerprint **全部匹配 P 预检及实际 Provider 观测**，因此比较的是经实际发送身份校验的输入，而非推测 Prompt。

S 直接读取已保存的 `request-2.json`，其 input SHA 与对应 `MODEL_RESPONSE_OBSERVED.model.generation_input_sha256` 相同。该私有请求文件 SHA 为 `955bf69ce73512fea1d94c07b895e96da5d4278b65a8946aec2d3722f1bbdcc2`。

两者 `immutable_inventory`、IR item table、Capability Contracts、实际 Consumer Contracts、来源索引表及目标路径表均逐值相同。输出 Schema 完全相同，fingerprint 为 `fc6afc4af5634c388ca17655e5c8d7830dce3bddee63817888cb9c4cb528890f`。不同请求/响应收据、反馈和派生状态产生各自的新请求 fingerprint，属于正常身份绑定，不是原来源漂移。

## 2. 模型实际看到了什么差异

| 维度 | P 实际上下文 | S 实际上下文 | 判断 |
| --- | --- | --- | --- |
| 决策对象 | 原 `decision_revision_requests`，另附逐决策 `semantic_assumption_review` | 单一正式 `decision_revision_requests` | S 并非没有重开决策 |
| 当前解释 | 额外内联**更晚一次历史失败响应**的实际公开方法理由，绑定其 request/response/claim SHA | 引用**原首候选**的 rationale，附 ref/SHA；原文位于同一反馈的原 Wire 中 | 解释来源及直接显著性均改变；没有“引用指向不存在文本”证据 |
| 被挑战前提 | 每个决策明确指出：从 Fact Subject 中的文件身份额外推出 changed-path 限制 | 共享挑战：是否从对象身份或 supporting provenance 推出原 relation/value/Scope/qualifier 未蕴含的额外义务 | S 仍含对象身份问题，但从具体 Subject→path 论证变成较宽的共享问题 |
| 挑战权限 | 标记为分析者从旧 Claim 提出的假设，可被原 Fact 反驳 | 未接纳解释；未知语义有效性；可重评或有理由保留 | 均没有把诊断提升为必须删除的权威结论 |
| 可观察处置 | 原 `observable_outcomes` 明列 replace / remove / retain / unresolved；remove 以原义仍完整覆盖为条件 | `response` 汇总要求显式局部编辑，有理由保留不能只是改措辞；未保留单独 `observable_outcomes` 表 | 丢失了逐类处置到操作的显式解释；**没有丢失 remove 能力** |
| 修复范围 | capability、依赖、目标、来源支持、rationale | 同上，并显式包含 component_quote | S 没有将范围缩为 rationale |
| Owner 派生 repair_targets | 4个原覆盖修复目标；P 的假设复核位于反馈中 | 保留相同4目标，另由 Owner 合法构造 route1、3 的2个重评目标 | S 对决策聚焦更明确，未将模型限制为 replace |
| 解释输出要求 | 既有 rationale 可说明所选解释及被拒绝/未决替代解释 | 明确重开解释、检查假设，有理由保留或合法修订 | 都不要求输出隐藏推理；S 不是“只要解释更好即可” |

字段来源：[P 假设复核构造](../c3-semantic-misinterpretation-correction-prototype-20261014/probe.py)、[P 原 Decision Revision 处置](../c3-formation-decision-revision-contract-calibration-20261014/probe.py)、[S 稳定契约](../../../src/spg/providers/fulfillment_candidate.py:376)。

### 措辞及指令核对

P instructions 为8,682 bytes，SHA `63dd1838008364346588b0e83a4365bb0c7f09ce80a28a17aa2d53c423bee708`；S 为9,028 bytes，SHA `a59aaf21ed8a56c1c6dd6a86977e455d5acc2389322bef9db3c1f42ef1071131`。S **完整保留 P 指令，并增加346 bytes**，明确要求消费 `decision_revision_requests`、重开解释、检查假设、由模型选择修订或有理由保留。

共同修复指令已经说明：rationale 或无关跨度变化不能修复无效 Consumer；风险诊断不等于判决，不应仅因出现在诊断中而删除。由此可以排除“稳定版指令撤销了 Consumer 修改责任”这一解释。相关路径：[`_formation_repair_instructions`](../../../src/spg/providers/fulfillment_candidate.py:1437)。

## 3. 新发现：不是简单地继续为旧假设辩护

只看 `changed_fields=[rationale]` 会遗漏重要信息。本轮直接检查 S 两条实际 replacement 的公开方法理由：两者都指出原 EQUALITY 内容要求不能单独推出 changed-path 限制，并都以短句 **“Removed as unsupported.”** 结束；但对应的实际记录却是：

| 原 route | 返回操作 | 返回 capability | 相比原 route 改变字段 | 是否出现在 remove 中 |
| --- | --- | --- | --- | --- |
| 1 | replace | GIT_DIFF_SCOPE | 仅 rationale | 否 |
| 3 | replace | GIT_DIFF_SCOPE | 仅 rationale | 否 |

两条 replacement rationale 的 SHA 分别为 `b504299cfc6c0c9fd400b231a6fa16023c33bce5205fce33df09b6c407238f5a`、`7b26c4bbf11a917b5ff8a8c6389122e56965457ccd09310b662aee7138021bb7`。完整原文仅留私有证据，本报告不复制整个响应或 Human 内容。

这支持以下有限结论：

- **可观察 Claim 已否定旧映射**；不能继续声称“模型完全未收到或未表达对错误假设的反思”。这不证明模型内部理解过程正确。
- **可执行编辑仍保留旧映射**；不应把文字中的“移除”当作真实处置。
- Owner 没有把模型的 remove 改回 replace。原响应本身就是 replace；[`_construct_local_candidate`](../../../src/spg/providers/fulfillment_candidate.py:624)依据显式 replace/remove/append 构造完整候选，不从理由文字推断命令。这一确定性职责是正确的。
- S 的第二候选实际删除了其他 route5、6、16、17，进一步证明 remove 路径可见且可用；问题不是该操作无法表达。

因此对上一份稳定化报告应补充解释：**“没有真正修改 Consumer”成立；“只改理由所以没有发生任何语义重新考虑”无法由证据推出。** 历史报告及收据保留原样，本分析提供更细归责。

两次都因其他必要条件失败而没有进入 Independent Review。S 最终覆盖失败及重复路线，与 route1、3 的编辑矛盾是不同观察。未发生“Validator 接纳错误映射”或“Review 放行”的事实。

## 4. 失败分类

| 类别 | 证据判断 | 归责边界 |
| --- | --- | --- |
| A Context missing | **输入差异确认；信息不足未证实。** S 少了更晚历史理由和逐项具体假设，但库存、Consumer 可观察能力、首候选理由及共享挑战都在；输出还明确否定原假设 | 不能把缺少历史 Claim 本身当必要能力缺失；不能要求生产必须先额外失败一轮才能修复 |
| B Decision scope insufficient | **本次证据不支持。** capability 在重评字段内，两个 Owner 重评目标存在，Schema 支持 remove，实际也使用了 remove | 未证明决策权限或表示范围阻止 Consumer 改动 |
| C Repair objective ambiguity | **限定支持，因果未证明。** S 缺少 P 独立列出的处置/操作解释，但共同指令仍要求实际修订；本次 Claim 与动作矛盾符合“形成了文字处置却未落实编辑”的失败形态 | 不能断言模型只被要求优化文字，也不能断言补回一段文字必然修复 |
| D Model stochastic variation | **仍未排除。** 每种上下文只有一次可比真实修复，且多个输入维度同时变化 | 不可把一次 P 成功确认为稳定因果，也不可断言纯随机是唯一原因 |
| E Other | **直接证实：候选内部的语义处置 Claim 与编辑操作不一致** | 当前最窄失败边界在 Formation 修复候选构造；未证明 Owner 绑定错误、Schema 表示不足或门禁错拒 |

**主要可观察归责为 E；C 是最小契约改进的依据，A 是已知混杂因素，D 仍 UNKNOWN。** 没有证据支持新模块、架构调整或更宽 Validator 接受范围。

## 5. 原型成功是否依赖偶然因素

1. **历史文本额外输入存在。** P 显式注入 request `095fd0ac-7701-49c2-8c75-8de5bceb83a5`、响应 SHA `b5ff1b986992a1423eaf4b5ae65b6d21d88f2af77f6acf9e1743680ea35fbc90` 中的两条方法理由。它们更明确地用 Subject 的文件身份为额外 Diff 辩护，随后被逐项挑战。这是有来源的额外历史 Claim，不是盲测或同输入对照。
2. **未发现正确答案泄露。** 那份历史文本仍为旧映射辩护，并未提供“删除1、3”的正确编辑答案；P 也明确将其标为未接纳 Claim。不能混淆额外上下文、跨记录信息暴露与伪造权威证据。
3. **删除方向的语义提示更具体。** P 的具体 Subject→path 假设及 `observable_outcomes.remove` 使“若不成立且原义已覆盖，可移除额外贡献”的路径更显著。但没有写死必须删除这两个 route；允许反驳或保留，不是更强的接纳门禁。
4. **P 不仅加了一个字段名。** 它保留旧 Decision Revision 处置表，再附加逐项假设复核；S 将其收敛为共享契约并更换了解释来源。不能把二者描述为同一内容换名。
5. **不能确认纯随机或单句因果。** 两者模型标签均为 deepseek-flash、reasoning none、上限16,384、timeout120s，均 completed，0传输重发。没有容量失败解释本差异。模型内部过程、Provider 后端不可变版本及每个上下文因素的独立因果效果均 UNKNOWN；cache 用量差异不是语义原因的证据。

P 此前报告提到“派生状态接线同时修正”，是它与更早探针的比较。本次 P/S 的 Owner 前提均可合法重建，不能再用该旧问题解释这里的输出差异。P 删除 Consumer 后仍未形成整体合格候选，因此其“成功”只限原型窄观察。

## 6. 唯一推荐：adjust Decision Revision Contract

**最小下一步：在现有 `decision_revision_requests` 内恢复并明确“语义处置如何落实为现有显式编辑”的契约说明。** 优先解决本轮直接观察到的 Claim/action 矛盾，而不是继续增加关于文件身份的特殊提示。

建议范围仅为：

- 保留当前源、Wire、attempt、receipt、route/component 绑定以及 Owner 唯一构造派生状态。
- 将现有允许结果明确为：有理由保留、修订、移除、保持未决；分别关联原决策身份与已有 replace/remove/append/UNRESOLVED 表达，不新增输出字段或 Wire 版本。
- 对所有被重开的决策，要求其**所声明的处置与返回操作相符**：可保持有依据的同 Consumer replace；若声明已移除，不能仍以同 Consumer replace 来编码该声明。何种语义处置成立仍由模型提出，Owner 不解析理由中的关键词自动删路线。
- 移除或修订不能损失原内容、来源、限定条件、范围及权限；原覆盖/证据失败仍全部需要修复。不可合法选择时保留既有未决状态。
- 保留现有 Validator / Independent Review 的最终判断。不新增确定性语义路由或把诊断变为必须删除的判决；也不新增针对文字措辞的硬编码规则。

这是**下一步设计建议，本轮未实施**。不建议此时复制 P 的更晚历史理由到常规生产路径，也不建议仅把共享挑战改得更像普通34：S 已在 Claim 层面表达了同一否定，先补假设措辞不足以解释或解决动作矛盾。

这也不等于“把 `observable_outcomes` 字段搬回来就能修复”。更早的 Decision Revision 原型本来就包含该表，仍保留错误 Consumer，P 又在它之上增加了假设复核。该历史事实排除了“字段名/菜单本身足够”的结论。建议的重点是把**当前处置选择与现有编辑动作一致性**写清，而非重复已失败的字段包装；效果仍未获资格。

后续资格应在原预算内分别观察：模型选择了何种处置、输出何种编辑、原义是否仍覆盖、原门禁是否接受；对“有依据保留”“合法改映射”“证据不足保持未决”均保留适用路径。只出现更好理由或一项 Schema PASS 不能作为成功。无需现在再调用模型取得这一归责；改动能否改善真实行为仍须后续独立资格，不能预先保证。

## 7. 对最终问题的回答

**为什么一个 Prompt 让模型改变 Consumer，而稳定契约只让它重写解释？**

已证实的是：P 提供了更具体的历史解释、逐决策假设挑战和显式处置菜单，并收到真正 remove；S 改为原首候选解释引用和共享挑战，收到的文字已经声称放弃旧映射，实际却仍编码为同 Consumer replace。**本轮最明确的差别是“语义修订声明没有落实为一致的编辑动作”，不是“Consumer 无权修改”或“缺少正确 Consumer 答案”。** 两个不同输入下各一次输出，无法证明哪一项措辞造成结果，更无法排除随机性；原型的行为成功不能当作因果证明。

完整私有输入/响应仍位于 ECS：`/data/watt/ai-native-evolution-20261013/semantic-assumption-review-20261014/private/` 及 `/data/watt/ai-native-evolution-20261013/decision-revision-stabilization-20261014/private/qualification/retained-first/`。本报告只保存可复核身份及必要摘要；生产、历史事实和 C3 PARTIAL 不变。
