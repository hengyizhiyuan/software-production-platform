# C3 Formation Decision Revision Contract Calibration

2026-10-14。基线：`codex/c3-open-semantic-obligation-convergence`，`a5d7712e8978d9a26faa4ef8bb1379c22540d156`。

**结论：现有表示能够修改 Consumer，但早期风险尚未成为明确的决策重评目标。一次请求契约探针使模型显式重写了 ordinary34 的 route 1、3，却仍保留原 Consumer，并遗漏其他修复。本轮没有取得合法第二候选或完整收敛资格。**

本轮仅增加本目录的分析、隔离工具及证据；没有修改运行时代码、Validator、Review、静态路由规则、输出 Schema 或候选额度。未创建 Work、触碰 Holdout、修改生产或历史记录。C3 保持 PARTIAL。

## 1. Diagnostic 与 Repair 的具体差别

原 [Early Diagnostic 报告](../c3-formation-early-semantic-diagnostic-feedback-20261014/report.md) 已证明：原首响应 SHA256 `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e` 中 route 1、3 的方法风险进入了第二请求；上一探针返回的编辑却未涉及它们。

| 维度 | 当前输入 / 实现事实 | 决策修复所需的最小表达 |
| --- | --- | --- |
| 风险对象 | `consumer_mapping_diagnostics.observations` 有 route/source/component 身份 | 复用这些身份，明确它们对应哪些待重评决策 |
| 风险理由 | 原 Fact 的完整含义与 Diff 的实际可观察量可能不等价 | 该问题要求重新判断方法，不能只改来源支持、quote 或解释文字来假定消除 |
| 有效性 | `UNREVIEWED_RISK_ONLY`，没有权威否定结论 | 保持语义有效性 UNKNOWN；不得直接写 `CONSUMER_INVALIDATED` |
| 修复操作 | 全局指令已要求 `Recompare`，输出已有 replace/remove | 逐决策标记 `REOPEN_REQUIRED`，撤回“可以不重评就沿用”的保留假设 |
| 可改范围 | 结构错误有 rejected operands；风险没有单独的字段重评范围 | Consumer 及相关依赖、目标、来源支持、方法解释可重评，由模型选择 |
| 必须保持 | 原指令已有一般事实/权限保护 | 对本次修复明确保留原来源版本、Fact 原义、完整覆盖、权限和其他合法贡献 |

**并非完全没有要求模型重新思考。** 现有 `_formation_repair_instructions` 已明确要求重新比较 Fact 和方法、通过显式局部编辑修正；不能把旧失败归因于“模型根本没收到重评指令”。缺少的是风险与决策目标、可变字段、保留边界之间的结构化关系。模型为何在上次具体生成中没有利用这些信息，内部过程仍 UNKNOWN。

## 2. 现有契约是否具备决策撤销能力

相关源码均属于上述基线：

- [Formation Owner](../../../src/spg/application/governed_obligations.py)：`_owner_repair_context` 保存未接纳观察、Owner 前提和 Consumer 风险；`_bind_repair_feedback` 绑定原 Wire、库存、Attempt 和持久收据。
- [Formation Provider](../../../src/spg/providers/fulfillment_candidate.py)：`candidate_construction_preconditions` 的理解状态风险主要来自 `violations`；`_coverage_repair_targets` 仅从原文覆盖错误生成定位目标。普通34已有 4 组修复目标，覆盖 route `[5,6]`、`[7,8,9]`、`[16,17]`、`[18,19,20]`，没有 route 1、3。
- 对**已经被独立 Review 否定的决策**，`projection_validation_feedback` 已能提供 `OBLIGATION_SEMANTIC_COMPONENT_MISMATCH`、`submitted_consumer_comparison` 及 Review 血缘。因此不能认定整个系统完全没有“已证实决策错误”的反馈表达。

真正缺口是：**尚未被 Review 判错的高风险选择，如何成为有边界的重新评估任务，同时不被提升为确定性否定事实。** 整体 Candidate 未接纳，并不表示每条未编辑路线都错误；局部编辑保留其他原路线的机制本身有必要维持。

## 3. 最小契约提案

在现有 `owner_repair_context` 内增加 `decision_revision_requests`，复用原诊断对象和身份，不引入新的事实或决策 Owner。此次冻结提案见 [完整字段](receipts/proposed-decision-revision-contract.json)。核心语义：

```text
decision_status: REOPEN_REQUIRED; SEMANTIC_VALIDITY_UNKNOWN
invalidated_assumption:
  THIS_OLD_CONSUMER_CHOICE_CAN_BE_PRESERVED_WITHOUT_REASSESSMENT
not_invalidated:
  NO_CONSUMER_HAS_BEEN_DECLARED_WRONG_BY_THIS_RISK_DIAGNOSTIC
```

每项引用原 route、原 route fingerprint、source_ref、component ID；整体绑定父反馈 SHA、原绑定 fingerprint 和诊断 fingerprint。字段重评范围为 `capability`、`current_fact_dependencies`、`target_paths`、`provenance_support_refs`、`rationale`。身份、原 Fact 的 relation/value/order/Scope/qualifiers/authority、所有原始必需含义、权限与门禁保持不变。修复 quote 时仍必须遵守原文与覆盖契约。

允许模型提出替换、在保全原义前提下删除多余贡献、经过重新评估后保留原 Consumer，或依法保留未决。为观察“保留是经过重评还是未处理”，可以通过已有 same-choice replace 的 `rationale` 表达新的公开方法解释。**解释变化只是重评行为的观察，不能成为修复正确或目标满足的证明。**

提案没有推荐替代 Consumer，没有自动修改路线，也没有从 Risk 生成确定性 invalid verdict。只有真实 Validator / Review 拒绝才能形成相应的已证实失败信息。

## 4. 一次最小探针及原始结果

探针维持相同原库存 19 项、原首候选、原模型和局部编辑基础。使用既有原型的同一镜像与只读源码挂载；没有构建新应用镜像。实际身份见 [运行收据](receipts/live-runtime.json)，源码文件 SHA 见 [预检](receipts/preflight.json)。

请求副本增加上述字段，并在 `candidate_construction_state.repair_targets` 中增加两项指向它的重评目标。预检确认：原错误集合与 Owner 条件保留，指令 SHA `63dd1838008364346588b0e83a4365bb0c7f09ce80a28a17aa2d53c423bee708` 与上一探针相同，输出 Schema 完全相同。新增的是请求数据语义，没有修改 Prompt 正文或路由判定规则。

离线负向检查拒绝原 Wire、库存、诊断 route 和父收据身份漂移。反馈从 66,390 增至 68,596 bytes；新反馈 SHA `9a364b36536f8ca65bd12b407ab80efcd62e19d6f858c99ff651d769d6c1f88a`。这些检查没有代替完整 Owner 派生状态重建检查，后者暴露了下述探针接线错误。

只执行 **1 次 Formation，0 次 Review，0 次重试**。实际收据见 [result.json](receipts/result.json)：

| 观察 | 上次早期风险探针 | 本次决策重评探针 |
| --- | --- | --- |
| 对 route 1、3 的编辑 | 均未编辑 | 两条都显式 replace |
| Consumer | 原额外 Git Diff 保留 | 仍保留 Git Diff |
| 改动字段 | 无 | `component_quote`、`rationale` |
| 方法解释 | 无新的对应解释 | 新解释仍把 Fact Subject 中的文件身份当作路径边界依据，而非证明完整 EQUALITY 值 |
| 对其他修复的处理 | 改动另外 10 条，仍有覆盖缺口 | 未编辑原其他覆盖/来源修复路线 |
| 实际停止 | 原文覆盖错误 | Owner 派生状态重建不一致，详见下一节 |

因此可观察到**决策被重新打开并形成了新解释**，不能宣称 Consumer 已正确修正。新理由重复了历史独立 Review 已指出的“内容 Fact 与目标文件关系被当作额外 Diff 义务”的模式；本次没有进行独立 Review，不能把分析意见冒充本次 Review verdict。

单个前后样本还受到模型随机性的影响，不能据此证明字段变化是行为变化的唯一原因，更不能证明长期收敛能力。

## 5. 探针身份拒绝的确切归责

本次真实终态为 `OBLIGATION_FORMATION_LOCAL_EDIT_BASIS_DRIFT`。**这是我在请求副本中直接追加派生 `repair_targets` 的接线错误，不能归责为模型返回错误 basis。**

只读 [边界归责](receipts/boundary-attribution.json) 确认：

1. 模型返回的 `basis` 与原始 Wire SHA 完全相同。
2. `_decode_fulfillment_candidate_wire` 按现有 `candidate_construction_preconditions` 从反馈重建 Owner 状态；现有构造器不消费新增重评任务，因此重建为原 4 项目标，而请求副本含 6 项。
3. 差异仅在 `repair_targets`。原身份门禁正确拒绝了这份状态；不应删除该比对或接受外部手填派生状态。
4. 若只在反馈中添加新字段、不手填派生目标，现有 Owner 重建结果与历史原状态一致。此为离线兼容性证明，不是另一次真实模型试验。

还对**同一份保存的响应字节**做了反事实解码：仅使用 Owner 原样重建的状态，仍出现 source 3、4、10、11 的覆盖缺口。该解码使用不同请求状态，**不是原试次资格结果、不是合法恢复，也不是接纳后的 Candidate**；仅用于证明身份接线错误没有掩盖一个已经完全修好的响应。没有修补模型输出或新增调用。

## 6. 推荐的最小有效动作

**建议校准当前契约，无需新增架构。** 分两个责任保持：

- `_owner_repair_context` 提供原诊断的身份绑定重评请求，区分 `REOPEN_REQUIRED/UNKNOWN` 与已有权威失败，不直接撤销 Consumer 或给出答案。
- 若要把请求投影为现有 `repair_targets`，必须由 **`candidate_construction_preconditions` 这个既有构造 Owner** 读取同一冻结反馈并确定性派生；生成、恢复、解码都复用同一构造路径。不能由探针或其他调用方手填状态，也不能修改解码器放行不一致。

需要保持原覆盖和来源修复目标，与 Consumer 重评任务共同存在；本次只处理新目标而忽略旧错误的响应不能算进展完成。后续最小验证应先离线证明**完整请求能通过 Owner 重建比对**、四类身份漂移仍拒绝、原错误/约束不丢失，再评价唯一一次第二候选是否产生有证据的方法修正。保留新 Consumer 或改理由都不自动 PASS，最终仍由原 Validator 和独立 Review 判断。

本轮没有把这一提案安装到 Runtime；没有增加候选次数或修改门禁来挽救探针。实际结果回答了本任务的窄问题：**旧上下文缺少明确的“待重新评估决策”投影；补充后出现了针对性重评行为，但不足以解决错误的方法理解，也没有取得完整修复资格。** “缺少字段”不是当前剩余语义错误的充分解释。

如果下一步需要表达真正的 `decision invalidated`，还必须取得或合法复用现有独立语义审查对该确切来源/组件/版本/方法的有效负观察，并验证其适用范围。本轮原始 Risk 不具备这项权限。模型的新解释表明它仍把“目标文件身份”当作新增路径义务的依据；仅将 Risk 字段改名为 Invalidated，会掩盖这一尚未得到有效纠正的语义前提，而不会证明错误已解决。

## 7. 消耗、恢复与状态

实际 request ID `095fd0ac-7701-49c2-8c75-8de5bceb83a5`，Provider `completed`；`deepseek-flash`、reasoning `none`、上限 16,384、timeout 120s，传输重发 0。input 88,853 / output 424 / reasoning 0 / total **89,277 tokens**；cached input 54,528 为输入子集。请求完成耗时 **3.249s**；货币成本 UNKNOWN。仅此一次调用，没有因探针接线错误补调用。

[前后完整性核对](receipts/postflight-integrity.json) 显示原收据 SHA `8eea94156781896350044e1c8635f76d648d3212c9a0663b27909ec2d7930d4f`、库存文件 SHA `f890af6ea4a85e481b03ea0e638651a61c9513042ad88761f6049f41ea895e85` 均不变。

跨电脑恢复：本目录随原 C3 分支保存脱敏收据、冻结提案与工具；ECS `/data/watt/ai-native-evolution-20261013/decision-revision-contract-20261014/` 保留完整私有请求和响应。`probe.py` 冻结的是此次含派生状态接线缺陷的实验，不是可直接部署的实现；`call-started` 防止原试次重复调用。原始响应不进入 Git。本阶段没有运行生产回归、G0、Guardian 或 Holdout，C3 状态没有变化。
