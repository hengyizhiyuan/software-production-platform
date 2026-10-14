# C3 Formation Failure Boundary Analysis

分析日期：2026-10-14，Asia/Shanghai；目录沿用任务指定的 `20261013`。

**结论：继续现有 Owner 内的收敛路径；现有证据不支持新增架构层，也不支持把增加候选次数当成已证实的解决方案。C3 保持 PARTIAL。**

本轮仅核对源码、既有公开收据及 ECS 保留的私有 Owner 收据，生成本文档。没有修改代码/测试、执行测试/模型、创建 Work、读取 Holdout 或改变 Validator、Review、Guardian、预算与生产环境。

## 1. 三个直接答案

1. **为什么这轮跨过此前障碍？** 新 Hardening 路径修复了候选表示与原消费契约接线、可安全失败提案的修复入口、反馈重复存储、原始编辑目标定位，以及两次机会的使用顺序。ordinary34 本次实际形成完整初始计划，第一次覆盖失败后，第二次明确编辑消除了覆盖阻断，才进入真正的独立 Review。不是通过放宽门禁取得突破。
2. **剩余障碍是什么？** ordinary34 仍有错误的“来源 → 消费方法”提案，被独立 Review 正确拒绝；同时存在一条 Reviewer 混淆计划资格与未来履约证据的阶段判断。ordinary41 尚未到 Review，仍有两个 UNRESOLVED 和一个不满足原 Owner 证明前提的支撑集合。另有单次收敛预算已耗尽的边界。它们不能合并成一个错误标签。
3. **下一步最小有效动作是什么？** 先在既有非 Holdout 库存及原收据上完成剩余争议的来源/消费者逐项归责，确认完整 Review 反馈在现有修复分支中的处置责任；不先添加规则或模型调用。若之后需要验证“结构修复后再做语义修复”，只能在明确批准的单次累计预算内进行，不能复活已终止 Attempt。当前没有证据要求重构 Formation、转移 Review 职责或削弱独立判断。

**校正“首次”范围：这是 Integrated Hardening 的本组非 Holdout 诊断序列首次进入 Review，不是 C3 历史首次。** [G60 报告](../core-production-semantic-convergence-c3-20261009/formation-feedback-consumption-20261011/report.md) 已记录 Formation2 → 独立 Review；[G61 报告](../core-production-semantic-convergence-c3-20261009/identity-feedback-recovery-20261011/report.md) 更已记录两次 Formation/两次 Review 后接纳投影并进入 Worker。因此不能据本轮推断“此前十几轮从未具备 Review 能力”，也不能把重新到达 Review 当成超过全部历史生产进度。

## 2. 身份、证据等级与比较范围

| 对象 | 核对结果 |
| --- | --- |
| 工作分支 / 分析前证据 HEAD | `codex/c3-open-semantic-obligation-convergence` / `1600e7bdf5e9cef89d52e22d997d376e6afd203f` |
| 冻结应用源码 / Tree | `d27707cb49558a0bc0071d9e3c4250fe88234427` / `04f146f4937a7fc7b0bbda21cd70dcad40dd4053` |
| 实际镜像 | `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53` |
| Guardian / ECF | `0d7aca954588c8ad3883dbedb730e59dc1d7b867` / `5aa4f8833c359c15bd059eda5972aa3915bcc18c` |
| ordinary34 / trial15 | 19 sources；input basis `aad0fa15b3b24c12aa5b4b1099f8fe7ef0d6f7044bbc79ba8650a68ad4c81998`；inventory `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29` |
| ordinary41 / trial14 | 23 sources；input basis `8139c4b98c98069cd5b02ad2c9b731497253a851d1994fdbaa4a2704f0cc03e7`；inventory `24cb332f3225bda169e3a393eac4470a826be2c3c665f37be296737deec0eb42` |

证据分级：**E1** 为当次实际 Provider/Owner/容器保留观察；**E2** 为已保存的受控回归或只读反事实检查；**E3** 为确切源码路径。本文的归责是这些事实上的分析，不是新的 Owner Verdict 或 Assurance。

主要 E1：[trial15 模型及构造收据](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-15.json)、[trial15 实际运行身份](../ai-native-integrated-hardening-20261013/receipts/nonholdout-runtime-d27707cb-15.json)、[trial14 收据](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-14.json)。运行使用已安装包、无应用源码覆盖；没有数据库访问、新 Work、产物验证或 Guardian 调用。进程 exit 0 表示诊断正常结束，不表示 Formation 成功。

原始私有材料仍在 ECS `/data/watt/ai-native-evolution-20261013/nonholdout-15/private/ordinary34-owner-receipts.json` 与 `nonholdout-14/private/ordinary41-owner-receipts.json`。本文只列身份、统计与必要的语义归责，不复制原始 Human 对话、完整 Prompt、Provider 输出或凭据。

trial 编号是诊断批次，不是同一 Work 的无限重试计数；部分批次含两个库存。早期 26-source 库存、后来的普通 G0 以及本组 19/23-source 库存也不是同一个实验输入。不能以批次数推算失败率或收敛概率。

## 3. Failure Evolution Timeline

“已修复”指已证实的工程缺口，不表示模型不会再生成同类非法提案。“当前未出现”也不构成泛化资格。

| Failure Type | 首次/代表性出现 | 修复提交或处理 | 当前状态 / 是否重复 |
| --- | --- | --- | --- |
| Provider 容量失败 | 初期历史请求原因 UNKNOWN；后来获授权诊断证实 `max_output_tokens`。冻结 e0df 的 low 对照实际 output/reasoning 均 16384 | `e0df8196` 减少表示冗余；随后获授权 none 对照改变推理配置 | none 对照 completed，但 57 Route 不合格；不能把容量问题等同 JSON 太大，也不能追认旧事故原因。当前14/15均 completed，无容量/传输失败。[原对照](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/live-model-verification-1/architecture-lead-submission.md)、[none 对照](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/reasoning-none-control-1/architecture-lead-submission.md) |
| 组件表达/完整性契约 | 初期 57 Route：重复、UNRESOLVED、背景与当前义务混合；不能仅用 source/capability pair 表达合法多组件 | Option A `a91442c2`；[原限定结果](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/option-a-live-bounded-1/review.md) | 多组件表达能力保留；重复/矛盾/遗漏仍必须拒绝。没有消灭模型错误 |
| Predecode 反馈缺信息 | a914 的两候选均 `WIRE_FACT_KIND_INVALID`，canonical Candidate 前只有主错误，后续不可评估 | `e7afb5a1`，绑定 raw Wire/库存/Attempt/持久收据的结构化诊断 | 工程诊断缺口已修；非法 FACT 引用没有因而合法。[修复证据](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/predecode-feedback-recovery-1/review.md) |
| 支持引用、Scope Owner 和来源对应 | 原支持 `u` 被当成独立来源贡献；Scope 误用内容证明；Owner 前提没完整进入反馈 | `9846bdde`、`530ea434`、`8c2b3d22` 等原 Owner 校准 | 接线已修；当前14仍选不充分支撑，属于重复出现的候选问题，非旧缺口自动重现。[来源审查](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/source-owner-calibration-1/review.md)、[后续](../core-production-semantic-convergence-c3-20261009/capacity-representation-20261009/source-operands-calibration-1/Closure-delta.md) |
| BOUND/当前内容与未来 Seal 错拒 | 正常 G0 的文件边界 Fact 不只用 SCOPE；混合当前内容与未来 Seal 曾提前拒绝 | `ec4fc607`、`2189ea69` 等消费契约修复，汇总于 `881c2c30` | 表达与阶段入口已修；trial15 的对应组件能进入 Review。Review 的阶段误判是另一边界。[生产流恢复](../core-production-semantic-convergence-c3-20261009/production-flow-recovery-20261011/report.md) |
| 历史 feedback 消费失败 | G57 第二候选重复反馈中已明确的 Seal 支撑/背景错误 | `9f9c94d8` 保留原反馈并调整既有修复入口 | 未证明历史反馈传输丢失；G60 实际进入 Review，但输入库存不同，不能算控制实验。[G60](../core-production-semantic-convergence-c3-20261009/formation-feedback-consumption-20261011/report.md) |
| Review 精确身份生成失败 | G60 Review 抄错 component ID 一个 hex 字符 | `ca891e0c` / Guardian `5c88ffb9` 将身份复用绑定到持久请求 slots | G61 实际 Review 收敛；trial15 无身份漂移失败。语义判断仍由 Reviewer 独立给出。[G61](../core-production-semantic-convergence-c3-20261009/identity-feedback-recovery-20261011/report.md) |
| 新表示的 Fact 类型/生成域接线 | Hardening trial1 ordinary41 把非 FACT 放入 f；trial2 越过该门后来源证明失败 | `dd5fc214` / `31028c15` 复用原域与必要证明 Schema；`65b9fdca` 原始引用的命名角色表示 | 类型门保持；当前14/15没有该错误。trial5仍重现，故曾经修过 Schema 不等于模型已遵守。[批次1–6](../ai-native-integrated-hardening-20261013/progress.md) |
| Unlocated/不合形状提案无法局部修复 | trial3 quote 未观察后仅1次调用就失去 basis；trial6安全 role 原 JSON 含错误字段类型也提前停止 | `f423bd6a`、`aeb49d2a`，允许严格绑定的未接纳原提案成为修复 basis | 修复入口有资格，不把无效提案变有效；后续最终校验仍拒绝错误。当前14/15实际完成第二候选 |
| 局部编辑覆盖原反馈说明 | trial4后代码核对：临时局部输出路径覆盖原 `_formation_repair_instructions` | `42c26d28` 复用原修复方向 | 接线修复；trial5仍未收敛，说明反馈到达不保证行为正确 |
| 临时理解/角色构造丢消费语义 | c4检查发现 override 丢掉原 consumer/原意/证明集合说明 | `148a25ce` 复用原语义说明，分离 Wire 编码方向 | 工程接线修复；trial10先因格式停止，未验证到后续角色阶段，不能把那次算语义改善 |
| Owner 收据容量与停止异常 | trial8重复完整载荷达到131072-byte限制，随后 finish KeyError；该 case丢失内存用量。trial9反馈内再含原 Wire，记录133150 bytes | `1f74d76e` 请求/响应父引用；`c4dbbac5` 精确原 Wire/反馈引用与重建 | 信息未删除、界限未增加；当前14/15反馈和终态完整保存。trial8缺失细节仍 UNKNOWN，不追认历史成功 |
| 未解析 JSON 无合法修复入口 | trial10 completed但尾部JSON错误，1次后 `LOCAL_REPAIR_BASIS_UNAVAILABLE` | `67b9f492` 严格绑定安全原输出为 UNPARSED claim | 工程入口已修；14/15未触发该 malformed分支，不能声称它直接导致这次成功进 Review |
| 两步构造耗尽修复机会 / 覆盖反馈目标不明确 | trial11理解→完整计划后已用完两候选；trial12同源v3局部编辑将覆盖错误10来源减到2，但仍失败 | `3d5656ac` 优先完整初候选，保留理解fallback；原 source ordinal映射到原route目标 | 当前14/15确实使用完整初计划→局部编辑。覆盖目标身份有真实消费；不能分离量化其与模型变化各自贡献 |
| 编辑 remove 形状不一致 | trial13完整JSON fence、完整replace，但 `remove:[{index:27}]` 被仅整数的旧规则拒绝 | `d27707cb` 新协商v2支持同域显式index target，旧v1保持原拒绝 | trial14真正消费object removals；trial15没有remove，不能把它的Review突破单独归功于此修复。原13只读反事实仍因覆盖失败，无Review |
| 当前语义映射 / Review rejection | trial14来源证明与UNRESOLVED；trial15错误Git Diff组件及来源级负判断 | 本轮没有实施修复 | **仍开放。** 不属于 Schema/容量失败；一部分原本就存在，只是在前置障碍消除后终于被下一门看见 |

本组详细原始结果均在 [Hardening receipts](../ai-native-integrated-hardening-20261013/receipts/) 与 [逐轮进展](../ai-native-integrated-hardening-20261013/progress.md)。时间线是原始记录的阶段索引，不把旧提交的结果算作当前源码资格。

其中一部分反复来自**新临时表示没有完整继承原消费与恢复契约**：字段域遗漏、局部编辑覆盖反馈方向、角色构造覆盖消费语义，以及重复收据。这是已观察到的工程回归链，不能全部归咎于模型随机性，也不能把修回旧能力一律描述成新增智能能力。另一部分则是门禁正确拒绝了始终不合法的模型提案，两类原因必须分开。

## 4. 当前版本为什么能进入 Review

### 4.1 已证实的工程机制变化（A）

这里的 A/B/C/D 指题目中的“进展因素”，不是下面第5节的失败类别。

| 当前行为 | 源码与实际观察 | 证据允许的结论 |
| --- | --- | --- |
| 保存理解候选 | Provider `_interpretation_observations` / `candidate_construction_preconditions`，已有trial8/11保存19/23条理解 Claim；仍 UNREVIEWED/NOT_PROVIDED | 具备保存与继续绑定能力；**trial15使用完整角色方案，并未先跑理解-only。** 不能归因于“这次理解阶段终于成功” |
| 第二候选可处理 | `_construct_local_candidate` 接受安全绑定 basis、只应用显式编辑，再生成完整正式 Wire；原响应/父收据/Attempt严格校验 | 不是重置预算或人工修 Candidate；当前15的实际编辑链有完整身份 |
| 一次修复机会留给完整计划 | `_role_generation_schema` / `form` 消费 `role_convergence_contract`；3d改为优先完整初始方案 | 当前15第一次就有32条route；第二次修复的是完整方案，未把两次都用于“理解→第一次方法计划” |
| 覆盖反馈定位到原提案 | `_coverage_repair_targets` 给出source_ref、原route indices/fingerprints、缺口，不选择语义/不扩引文 | 当前15的第二请求实际包含source3/4/10/11与其原route映射，反馈SHA与失败收据一致 |
| 实际进入 Review | `form_fulfillment_projection` 先运行原确定性校验，再 `_review_fulfillment_candidate`，最后合并验证 | 当前15有真实 `SEMANTIC_REVIEW_OBSERVED`，不是测试替身或文本声明；没有完成接纳 |

E3 固定于 d277：[Provider](../../../src/spg/providers/fulfillment_candidate.py) 的 `_role_proposal_semantic_value`、`_construct_semantic_proposal`、`_coverage_repair_targets`、`_construct_local_candidate`、`_construction_consumer_instructions`；[Work Owner](../../../src/spg/application/governed_obligations.py) 的 `validate_projection_components`、`_review_fulfillment_candidate`、`form_fulfillment_projection`。分析前 HEAD 与 d277 在这两个文件无差异。

### 4.2 模型随机性（B）、条件变化（C）和归因限制（D）

- **模型实际行为确有变化**：同一ordinary34库存早期编辑曾删必要贡献/重复组件；trial15显式编辑后覆盖通过。但未做同一请求、受控随机条件的消融或重复抽样，不能断言某一提交单独使模型“理解正确”，也不能给出稳定成功率。
- **输入没有为本次简化**：公开批次记录的ordinary34 basis/inventory指纹从trial1到15相同；ordinary41同样保持自身指纹。二者互不相同（19 vs23来源），不能以ordinary34进入Review证明ordinary41已解决。
- **生成请求条件确有工程变化**：临时候选表示、Schema/消费接线、反馈与完整初计划优先策略逐步改变。trial12还是同源镜像的v3机制对照，不等于最终v4请求；早期low→none也属明确获准条件变化。不能把全部历史运行当同条件随机重跑。
- **当前并未放宽最终门**：14/15保持模型none/16384/120秒、2 Formation/1 feedback/最多4逻辑调用；Guardian根本未调用。第一次已跨过的门与剩余拒绝分开记录。
- **反事实提供了直接限制**：[trial13原输出在d277的既有只读检查](../ai-native-integrated-hardening-20261013/receipts/counterfactual-formation13-d27707cb.json) 消除了旧编辑Schema阻断，随后仍 `SOURCE_CONTRIBUTION_LOST`，不进入Review。因此修复编码消费确实有效，但不足以自动得到合法语义。

## 5. 当前剩余失败的责任边界

以下 Category A–D 为本任务分类，**不是**开发原则§13中 A模型波动/B系统缺陷/C治理阻断的字母含义。

### 5.1 ordinary34：已到 Review，但投影未接纳

实际Review请求 `3c22936a-e90f-49da-ba48-9e4c5863335c`；观察收据 `00d1a5f7-3809-4665-8e6e-1575d12cee8e`；最终拒绝收据 `184f4cc7-cb42-436e-9019-5f96a5fd854f`。

| 具体项 | 分类 / 证据 | 结论 |
| --- | --- | --- |
| 内容Fact source0/1，多提出GIT_DIFF_SCOPE route1/3；同源另有ARTIFACT_CONTENT route0/2 | **Category A：模型方法映射错误。** 两个组件的 `complete_and_equivalent=false`，`nonredundant=true`、`owner_phase_evidence_valid=true`；Review指出Diff不能证明字面内容 | 正确消费者存在，不使同源错误组件自动合法。需模型消除/修正无依据的方法提案；不新增文件名/Fact特例，不让Watt自动删route。这里不支持Validator错拒或Wire无法表达 |
| 混合当前内容与未来Seal的source3 | **Category C：Reviewer在本次判断中越过计划资格阶段。** source reason承认两种方法分别覆盖内容与Seal，却因“实际证据须在各自阶段可用”给负判断；其对应两个组件本身未被判错 | Formation/Review目前判断派生方法计划，不能提前要求未来Seal已发生。既有Review输入已明确这一点，故是Reviewer推理偏差，不是已证实的正式Owner职责设计缺陷。不能据此伪造Seal或自动反转总判定 |
| 禁止性Fact source4及Clause source11 | **Category D：剩余归责未完成。** source reason认为Git Diff不足以证明“新增页面”等完整含义；对应组件结果未给负判断 | source级与组件级结果需对照原始限定语义及真实消费者覆盖再归责。尚不能断言必为Review错拒，也不能断言必须新增执行权限。保持UNKNOWN，不用标签替代依据 |
| Projection/Wire表达不足 | **Category B：本次没有正面证据。** 当前内容、Diff、持续禁止及未来Seal都已有可提交的方法/阶段；两个错误Diff提案不证明合法方法不可表达 | 没有“合法结果无法编码却被拒绝”的已证实剩余反例，不启动新契约层或重构 |

本次最终反馈实际包含 **5条source mismatch（0/1/3/4/11）+2条component mismatch（route1/3）**。不能把7条诊断当成7个独立系统Bug，也不能仅摘取阶段偏差而忽略另外两条有依据的拒绝。[既有归责](../ai-native-integrated-hardening-20261013/review15-attribution.md) 与本次只读核对一致。

Review请求明确其为“derived-plan semantic validation”，不产生Assurance、Verification PASS、Fact或Human authority。`SEMANTIC_REVIEW_VALIDATED` 阶段保存了解码后的独立结果，其中仍可含false verdict；其名字不是“整体语义通过”。最终 `CANDIDATE_VALIDATED.validation_passed=false` 是实际终态。

### 5.2 ordinary41：仍在确定性Owner前提门，未进入Review

| 项 | 实际事实 | 分类与处理 |
| --- | --- | --- |
| source20 / route25、source21 / route26 | 两者是WORK_CONSTRAINT，模型选择UNRESOLVED | 保留显式未决是正确保护；未产生合法方法，不计履约完成。Category A的未完成提案；尚未证明Category B表达无能或现有权威事实真正缺失 |
| source22 / route27 | 选择GIT_DIFF_SCOPE，但support只有source6；原Owner允许的完整替代集合为[5,12]/[6,12]/[7,12]/[8,12]/[11,12] | Category A的支撑选择不满足既有必要条件；确定性拒绝正确。不能由Watt自动补12或宣告COVERED |
| 必要方法/支撑前提 | 原Owner给source20/21也暴露了多个必要证明分支 | 这些是进入语义审查的必要条件，**不是已完成证据或某一方法的语义批准**；不能反过来称模型必须任选一个就能PASS |

[原Owner只读核验](../ai-native-integrated-hardening-20261013/receipts/failure14-owner-audit.json) 不含模型调用。未发现错误来源被放行，也没有证明真实生产Evidence丢失。这里的“证明不足”首先是候选的来源对应前提不足，不是已经运行Worker后缺少产物证明。

### 5.3 已解决、迁移及继续开放的区别

- **已解决的工程问题**：可安全basis的恢复入口、反馈/消费语义被临时协议覆盖、重复收据容量、编辑形状接线、过早用完完整计划修复机会。旧失败记录仍失败；修复并不升级历史终态。
- **继续存在的模型/候选问题**：覆盖遗漏、无依据消费者、错误支撑、UNRESOLVED。类型问题在早期修复后也曾重现，说明生成契约修复不是智能正确性的保证。
- **向后暴露的新门**：trial15原覆盖错误消失，随后Review发现两条初始就存在、且本轮被原样保留的错误Diff组件。它们不是局部编辑新引入的证据，属于前门通过后才可被下一门识别的潜在错误。
- **不应算作完整恢复**：trial14消除了原覆盖错误，却仍没有合法完整映射；trial15进入Review，却没有接纳。两者都没有新软件Candidate、当前版真实Guardian或C3 Closure。

## 6. Self-Refine实际效果

### 6.1 ordinary34 / trial15

**Observed:** 第一次32条route，覆盖source3/4/10/11不完整。第二次显式replace17条，remove0、append0，保留15条；全部source_ref/capability选择不变。17条中10条修改component_quote/rationale，另外7条修改provenance_support_refs/rationale。第二候选仍32条route，越过确定性检查并实际进入Review。

**Evidence:** 第一次失败收据 `9f11bb8c-618c-45fe-8f7b-fef91d07465d`；反馈SHA `e3453b74164c512fcc110a9df22a35ca2d82e39b6d3ef6f88673ba816afcedd2`。第二请求 `0bc40261-7ba2-4543-babf-d11fe96cd8a0` 明确引用该失败收据和相同反馈SHA，其basis指向原响应 `66f53c9d-b2f7-4c9a-a4a7-ae3a3e001097`、原Wire SHA `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`、原库存及Attempt1。第二模型编辑SHA `a406d457ffefa61b5c2122dadc40994005addbd653707b979a279ca44239c7fd`；构造完整Wire SHA `2dec2a802c84c08930108553559641b2891811f86479d527a7e3c21f387a4718`。[公开链路](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-15.json)。

**Conclusion:** 反馈有实际身份绑定和行为变化；不是“反馈从未消费”。原覆盖错误没有重复，局部编辑机制保留未改部分，结构搜索范围收缩。但保留不等于“保留的全是正确部分”：错误Diff route1/3就在15条保留项中。第一次未执行Review，反馈尚无这两条语义拒绝；不能指责第二候选忽略尚未产生的Review反馈。

10条quote变更是模型明确选择 `component_quote=null`，使用既有协议的exact whole-source basis；不是Owner静默扩展截断引文。源码 `_construct_semantic_proposal` 对null使用原始[0,L)，其他quote要求唯一原文定位。**完整字符覆盖已证明；组件分工和方法适用性仍须Review**，不能因null覆盖全文就判语义完整。

### 6.2 ordinary41 / trial14

**Observed:** 初始30条route，source18/19覆盖失败；第二次replace7、remove2、append0，保留21条，最后28条。原覆盖错误消失，剩余两个UNRESOLVED与一个来源证明失败。

**Evidence:** 第一失败收据 `3c8c45c9-fe34-4c0c-b9f0-1b21229aefbe`；第二请求 `4d82f1cf-5be0-47a7-acb2-823e02241a34` 对应反馈SHA `307c1e7203f437b1b67b6fa48e119a850e1d6ae05d6b513fdd3a683814ac345c`。原索引16/20由模型以object target明确移除，新v2解码成功。[当次收据](../ai-native-integrated-hardening-20261013/receipts/nonholdout-model-d27707cb-14.json)。

**Conclusion:** 原反馈确实驱动了局部修复；没有证明全部必要意义收敛，也不能把首个predicate变化当成整体错误数量严格下降。后置前提此前可能尚不可评估，不能称为“新引入”而无逐字段依据。

### 6.3 效果边界

现有Self-Refine证明了**身份连续、显式编辑、原提案保留、覆盖修复以及可到达独立语义审查**。尚未证明本组库存的稳定语义收敛、错误Review的自动纠正或最终生产成功。trial12“10来源覆盖失败→2来源”也是收缩证据，终态仍失败；[原审计](../ai-native-integrated-hardening-20261013/receipts/coverage-audit-11-12.json) 明确保留剩余实际字符缺口。

## 7. 架构判断与下一步最小动作

### 7.1 选择：Continue Current Path，带明确验证边界

依据：已有Owner能表达这些方法/阶段；身份与局部修复实际执行；完整方法计划能进入独立Review；错误消费者被拒绝。尚无证据表明必须转移Formation/Review职责或创建独立normalization模块才能处理本次剩余项。原有推理/Claim与Fact/Evidence边界也没有因拒绝而被破坏。

这不是“当前机制已稳定成功”的结论。跨批次仍有明显语义波动，本组两个库存均未接纳；本次证据只足以支持继续验证和校准现有收敛职责，不能支持无限追加调用。

### 7.2 最小有效动作，按依赖顺序

1. **先完成只读归责，不先改Validator或Prompt。** 对ordinary34 source4/11原限定语义、现有Diff目标集合及否定操作的Owner覆盖逐项说明；核对source级负判断为何与组件级正判断并存。对source3保存“计划方法可提议/实际Seal未发生”的两层状态，保留其Reviewer偏差及整体拒绝。对ordinary41说明原支撑集合的推导关系与候选为何少必要成员，不自动补成合法结果。
2. **明确修复责任与反馈可达性。** 原Owner已有绑定的Review反馈，含独立结果、失败谓词及submitted-consumer comparison；可处理生产者语义偏差，也有保持候选而修复critic输出契约的分支。但source3这种自然语言阶段推理偏差，不等于已经被机械检测器识别的Review输出契约错误；不能直接借critic-repair分支反转它。若发现现有反馈把这种已证实错误派给错误责任方，再在原Owner内提交最小接线改动和正负依据；目前不声称该缺陷已经证明。
3. **将资源决策与能力结论分开。** 当前15实际为F1覆盖失败→F2修复→Review(F2)拒绝，已用2候选/1反馈/3逻辑调用。第4调用单独生成F3既违反候选数，也无法再独立Review；F3+Review(F3)需总5调用。已有[3候选/2反馈/2适用Review/5调用决策包](../ai-native-integrated-hardening-20261013/convergence-budget-decision-package.md)仍是待决建议，本任务未批准也未实施。它可验证“双层失败能否先结构后语义修复”，不是解决ordinary41的充分证据，也不是对现有失败的追认。
4. **批准后才做单次明确实验；不批准就不盲跑。** 若允许预算实验，沿原Owner持久策略绑定累计调用、失败类型、进展、身份和停止条件；模型/每次上限/来源/Review/Guardian不变，原终态不重开。衡量指标是必要语义是否被合法修复、独立Review是否可靠、UNKNOWN是否保留；不是多执行一次就算能力提升。出现无进展、身份不明、容量/传输未知或真正缺权威证据立即停止对应分支。

### 7.3 什么证据才要求Revisit Architecture

仅当进一步证明下列任一事实，才需要调整**具体职责边界**：合法方法无法在现有组件/来源/阶段契约中表达；Owner必要证明条件与权威原始语义冲突；已有真实证据无法合法到达消费者；或模块承诺的有界修复因身份/责任设计而无法成立。一次模型错误、一个Review误判、一次预算耗尽都不是上述证明。

当前首要改进对象仍是现有Formation/Review内的来源到消费者语义选择与按失败责任收敛；**没有已证实的下一项代码改动可据本轮直接下单**。先完成上面的剩余归责，再决定是既有运行时恢复实验还是有证据的窄范围工程修复。不以“大重构”或不断加规则替代这个判断。

## 8. 当前资格与成本结论

| 最终应用上的真实诊断 | 调用 | 实际Input / Output / Total | Reasoning / Cached | Owner观察耗时 |
| --- | --- | --- | --- | --- |
| ordinary41 trial14 | 2 Formation / 0 Review | 138322 / 5945 / 144267 | 0 / 43776 | 26.393秒 |
| ordinary34 trial15 | 2 Formation / 1 Review | 227206 / 15300 / 242506 | 0 / 5248 | 59.904秒 |

Token均来自原Provider Usage；cached是input子集，reasoning是output子集，不重复相加。两次均无传输重发，金额与完整Program累计成本UNKNOWN。本轮分析新增模型用量为0，未进行新回归或构建。

**C3仍PARTIAL。** 本轮突破是“新构造/反馈路径确实能让一个原库存完成局部修复并接受独立语义审查”；剩余是“生成语义不合格、部分Review阶段判断及来源级争议未归责、现有单次恢复额度已尽”。当前应用尚无新正常入口G0→Worker→Git→Verification→密封Candidate→适用Guardian资格，也未执行新的独立Holdout。历史G61及其后续Candidate/Guardian成果仍是历史版本资格，既不删除，也不移作d277的成功证明。

最终答案：**这轮突破来自已执行的工程修复与本次模型成功完成覆盖修复的共同事实；不能归因于一次万能补丁。剩余障碍主要已进入真实语义选择和独立审查边界，另有待归责事项与预算约束。下一步是原Owner内精确归责与受治理的收敛验证，不是新增架构层，也不是降低PASS定义。**
