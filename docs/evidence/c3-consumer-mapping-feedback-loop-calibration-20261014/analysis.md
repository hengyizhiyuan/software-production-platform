# C3 Consumer Mapping Feedback Loop Calibration — ordinary34

记录日期：2026-10-14。结论：**C3 仍 PARTIAL；本轮仅分析与最小设计，不改代码、预算、Validator、Review、历史 Candidate 或原收据。**

## 1. 精确事实与反馈路径

分析起点是 `codex/c3-open-semantic-obligation-convergence` 的 `a649075cdeaf9c50dc07a9c7ca9654483ca2722f`。ordinary34 的实际运行仍属于 `d27707cb49558a0bc0071d9e3c4250fe88234427` / 镜像 `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53`，库存 fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`。后来 Owner 校准提交 `f72707ab96ed67d167cd1dd26a8ddb55b716e323` 没有对该历史试次产生新模型结果。

E1：[公开调用链](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-15.json)及原私有收据 ECS `/data/watt/ai-native-evolution-20261013/nonholdout-15/private/ordinary34-owner-receipts.json`（SHA256 `8eea94156781896350044e1c8635f76d648d3212c9a0663b27909ec2d7930d4f`）。E2：[原始失败归责](../c3-semantic-review-failure-attribution-20261014/analysis.md)、[上轮 Consumer Mapping 分析](../c3-formation-consumer-mapping-convergence-analysis-20261014/analysis.md)、[Review15 归责](../ai-native-integrated-hardening-20261013/review15-attribution.md)。E3：[Work/Fact Owner 与反馈实现](../../../src/spg/application/governed_obligations.py)、[Formation/Review provider](../../../src/spg/providers/fulfillment_candidate.py)、[原消费者契约](../../../src/spg/domain/governed_obligation.py)。证据等级 E1=实际运行，E2=既有只读核对，E3=源码；本轮没有模型调用或反事实 PASS。

| 阶段 | ordinary34 实际发生 | 已进入反馈 / 未进入反馈 |
| --- | --- | --- |
| Candidate 1 | 32 条 route。source0/1 为字面标题、段落 EQUALITY Fact：route0/2 选内容消费者，同时 route1/3 **额外选 Git Diff**；source2 的 route4 才是独立文件范围 Fact 的正确 Diff。 | route1/3 的 rationale 把“该 Fact 与目标文件关联”当作该 Fact 自身的文件范围义务；此时只是未接纳提案。首响应 SHA `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`。 |
| Validator / Owner | `validate_projection_candidate(... allow_review_pending=True)` 先检查结构、身份、来源、方法资格和组件覆盖；原文覆盖 4 处缺字符，内层 Owner 另记录 7 条来源对应失败。 | 反馈收据 `9f11bb8c-618c-45fe-8f7b-fef91d07465d`；反馈 SHA `e3453b74164c512fcc110a9df22a35ca2d82e39b6d3ef6f88673ba816afcedd2`。source0/1 覆盖 COMPLETE；语义履约 UNKNOWN，实际证据 NEED_EVIDENCE，独立 Review NOT_EVALUABLE。**未反馈 route1/3 的语义不等价。** |
| Repair Request | `projection_validation_feedback` 收集可确定性评估的错误，`_bind_repair_feedback` 绑定原 Wire/库存/Attempt/收据；`_formation_repair_instructions` 要求检查这些错误并保留合法未变决定。 | 第二请求身份连续；这不是已完成的全计划语义审查。结构反馈没有声称 route1/3 正确，也没有声明其错误。 |
| Candidate 2 | 显式局部编辑 `replace17/remove0/append0`：10 条 quote 补为合法全文依据，7 条支持引用改成原 Clause；15 条原路线保留，包含 route1/3。原结构/来源错误消失。 | 第二响应 SHA `a406d457ffefa61b5c2122dadc40994005addbd653707b979a279ca44239c7fd`；正式 Wire SHA `2dec2a802c84c08930108553559641b2891811f86479d527a7e3c21f387a4718`。不能说模型“无视”未出现的 Consumer 负反馈。 |
| Independent Review / stop | 第二候选通过结构资格后才进入独立 Review。route1/3 的 `complete_and_equivalent=false`；文件 changed-path 集合不能证明 h1 或段落的字面值；整体终态 `OBLIGATION_SEMANTIC_COMPONENT_MISMATCH`。 | Candidate fingerprint `c6095b896416238aae5e85def5e073230e423634ca5f7cb7a8bbffbb2e4b9a62`；终止收据 `184f4cc7-cb42-436e-9019-5f96a5fd854f`。这时第二 Formation 候选已用完，Review 错误没有再进入一次 Formation 修复。 |

### Failure / Missing Feedback / Current Owner

- **Failure：** 模型提出原 EQUALITY 内容 Fact 之外的额外 Diff 消费者。确切 changed-path 证据不能区分同一文件内标题/段落正确与错误，独立 Review 对 route1/3 的拒绝有充分依据。
- **Missing Feedback：** 第一候选的可定位 route1/3 未获得“原 Fact 所要求的观察值与该消费者实际证明的观察值不等价”的来源/组件级诊断。首反馈只有覆盖、来源前提等已评估错误；它如实把独立语义审查列为 `NOT_EVALUABLE`。
- **Current Owner：** 模型提出 Consumer Mapping；Work/Fact Owner 做身份、来源和必要方法资格绑定；Validator 做可确定检查；独立 Semantic Review 判语义等价。`projection_validation_feedback` **已能在 Review 实际发生后**携带 source/component 负结果及原 route 对照，`_semantic_repair_observation` 还核对 Candidate/组件/库存/Review 收据身份。缺口主要在**何时取得可消费的语义观察**，并非反馈 JSON 没有负结果字段。

## 2. 哪类语义错误适合在 Formation 反馈

Consumer Mapping 是**候选自身可修复的错误（A）**：模型能够删除 route1/3，保留合法内容 route0/2 和 source2 范围 route4；现有局部编辑表示支持 remove，Owner 不需重写 Fact。它的**语义判决不能由纯结构 Validator 冒充（B）**：`_fact_evidence_method_failure` 只决定非 SCOPE Fact 的 reviewed-method 是否可提议，`literal_file_scope_value_paths(... proposed_method=True)` 只读出可能的路径形态，不证明完整原值/qualifiers 已由 Diff 覆盖。把所有 EQUALITY→Diff 静态拒绝会误伤值本身表达路径边界的合法 Fact。

因此本次需要的是**C：在既有 Formation 循环中，对已具备精确身份、原文组件、方法定义的有限组件取得早期、非授予式语义观察**。普通34 首候选的 source0/1 和 route1/3 已有可定位身份，虽同一候选其他来源缺字符，仍可问“该方法将来提供的证据能否区分本组件满足与违反”。若某组件的原文、来源、目标或资格本身不完整，则返回 `NOT_EVALUABLE`，不能猜测。早期观察只能提出修复反馈；第二候选仍须完成全部确定性校验与**完整独立 Review**，且不得以局部正观察授予 PASS。

还须隔离 Review15 已观察的其他问题：source3 对未来 Seal 的阶段误判、source4/11 对“新增页面”解释不一致；它们不能被普通34 route1/3 的确证错误吞并。早期诊断若给出这类存在争议的判断，也只是带原文和身份的**候选负观察**，不自动删改路线或降低最终 Review。局部反馈对错误 Consumer 的实际修复能力仍需新资格证明。

## 3. 方案选择与最小契约

### Option A — 单独增强 Validator Feedback：不选作语义判决来源

现有反馈生成器可以列 route、component ID、原来源及方法前提，但在没有 Review 时不能合法写“Diff 消费者违反 EQUALITY 原义”及期望的替代 Consumer。静态 Fact relation、文件名、rationale 或 `candidate_capabilities` 均不是语义证明。若仅增一条一般性“请重新想一遍方法”的文本，原 Formation 请求已经给过 Diff 不证明内容的消费者契约，不能据此称闭环已修。可复用现有反馈**承载**新观察，不能让它自行制造观察。

### Option B — 推荐的有限早期检查

复用现有 Formation/独立 Reviewer 的 Owner 和反馈收据，不新建语义层。仅当第一候选因其他结构错误无法进入完整 Review 时，对**精确可定位且自身结构可评估**的 Consumer Mapping 做一次范围受限的证据区分检查：原组件的目标/值/qualifier 与消费者实际可观察的证据之间，是否存在“证据相同而原要求一真一假”的反例。普通34 的 route1/3 属于此类；真正路径范围 Fact 的 Diff 不得因共用文件名而被误报。Reviewer 的输出应逐组件注明负观察及原来源/route/方法，不足者 `UNKNOWN/NOT_EVALUABLE`；不生成全计划 PASS、权限或已执行证据。

该检查需要**现有 Reviewer 的一个窄范围诊断输入/结果契约**，而不是把当前要求全来源、全组件结果的完整 Review 直接套在结构失败候选上。将可验证的负观察并入原 `projection_validation_feedback` 的一次反馈，绑定原 Wire fingerprint、库存 fingerprint、Attempt、候选/组件 fingerprint 和 Reviewer 诊断收据；第二 Formation 仍由模型选择显式局部编辑，Owner 不自动删除路线。第二候选须原样通过完整 Validator 和独立 Review。请求前必须核对当前调用限制：源码记录为 **2 Formation 候选、每候选最多 1 Review、总计最多 4 次模型调用**；早期诊断+最终 Review 在次数上有上界，但其实际 Token、超时和契约可行性**本轮未验证**。若现有资源/Reviewer 独立职责无法承载，不能暗增预算或以确定性特例顶替。

建议的失败反馈语义是“此候选的已指认 Consumer **尚不能证明**原组件；请保留已正确贡献并自行修正方法或保持未决”，同时给出原事实、方法可观察量与反例关系；**不是** Owner 指定唯一消费者、自动删除 route、代替 Human 补事实或宣称实际内容已通过 Verification。正观察同样不构成当前或最终 PASS。

### Option C — 保持现状：门禁正确，但不是收敛改进

若 Option B 的局部输入不能被合法独立核验，则维持现有结构反馈→完整 Review→有界 stop。ordinary34 的拒绝是真实且应保留；可以在下一次独立资格中重新观察，但不能不变条件盲试并称为反馈能力。C 只是真实终止策略，不能回答本任务所要求的同次候选闭环缺口。

## 4. Self-Refine 与验证边界

当前实际轨迹是 `结构/来源失败 → 精确反馈 → 17 条局部编辑 → 保留包括 route1/3 在内的 15 条 → 完整 Review 拒绝`。Option B 若成立，目标轨迹变成 `结构/来源失败 + 已核验的 route1/3 语义负观察 → 同一次绑定反馈 → 模型在唯一一次局部编辑中处理这些错误 → 完整 Validator/Review 判决`。这是**预期行为，不是已取得结果**；模型也可能不修正或引入新错误，届时仍按两候选限制停止。

推荐的后续实现仅触及既有 Formation/Review 调用阶段、诊断反馈生成和身份绑定；不改原 Wire 意义、Fact、Owner Authority、Consumer 方法、最终 Review 判定或 Guardian Gate。代码需修改，**本轮没有修改**。先用原普通34的只读候选及独立非 Holdout 变体验证“哪些组件可评估”，再以新受控试次证明反馈确实点名错误方法、第二编辑保留正确路线并修正错误路线；负例须覆盖路径值 Fact、来源/版本漂移、缺证据、错误目标及 Reviewer 输出不完整。旧 Review 不能被回填成首轮反馈，也不能把反事实修补候选冒充真实模型收敛。

## 5. 必须回答的四点

1. **为什么没修复？** 首轮结构失败阻断 Review；修复反馈没有 route1/3 的语义负信息，局部编辑把它们当未被点名的路线保留。真正拒绝出现于第二候选后的独立 Review，已无 Formation 修复额度。
2. **缺什么？** 缺少对首候选中可评估 Consumer Mapping 的**早期、身份绑定、非授予式语义负观察**，而非新的静态 Alias、已完成 Evidence 或反馈字段泛滥。
3. **最小有效改进？** 选择 **Option B**：在现有四次逻辑调用和两候选范围内研究一次窄范围独立诊断，负结果进入现有一次反馈，第二候选继续完整校验与独立 Review。先验证 Reviewer 契约/资源可行性；不成立则如实保持 Option C 的拒绝/终止。
4. **是否仍支持 Formation AI Native 方向？** 支持。现有模型提案、局部编辑、UNKNOWN、事实与权限边界及独立门禁均有真实证据；待补的是语义错误能否在有界循环**及时反馈并被修复**。此次没有证明泛化收敛或 C3 Closure。
