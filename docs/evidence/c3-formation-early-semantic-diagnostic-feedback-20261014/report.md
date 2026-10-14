# C3 Formation Early Semantic Diagnostic Feedback Prototype

记录日期：2026-10-14。**原型已证明 Consumer Mapping 风险能进入现有 Repair Context；本次真实第二候选没有修正被点名的 Consumer。C3 仍为 PARTIAL。**

## 1. 范围、来源与精确版本

继承 [Feedback Loop Calibration](../c3-consumer-mapping-feedback-loop-calibration-20261014/analysis.md)。在原 `codex/c3-open-semantic-obligation-convergence` 分支实施，起点 `8061626b323cc4aefbf6066299f57ae562718406`。

本轮源码提交：**`ec74603b22199777a4439b6bc34f1234b8496eda`**，Git tree `e35d544b4a13ee37d3fae831582479edc211c1ce`。修改仅涉及现有 Formation Owner、Provider 的反馈接线及定向测试。Validator、独立 Review、Guardian 的判定逻辑、Wire Schema 和调用预算没有修改。

ordinary34 原始运行属于 `d27707cb49558a0bc0071d9e3c4250fe88234427`；原 Owner 收据 SHA256 `8eea94156781896350044e1c8635f76d648d3212c9a0663b27909ec2d7930d4f`，本轮核对仍相同。库存为原 19 项，fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`。没有创建 Work、修改历史 Candidate 或向历史 Owner 追加反馈。

本轮在既有隔离 ECS 上，以镜像 `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53` 加两个源码文件只读挂载进行原型验证；文件 SHA256 见 [qualification.json](receipts/qualification.json)。**没有构建或宣称新的完整应用镜像资格，也没有运行 G0 / Holdout / Guardian。**

证据等级：源码与定向测试证明接线和边界；只读原收据回放证明普通34的定位；单次实际 Provider 调用证明新的修复输入与响应。它们均不等于完整生产资格。

## 2. 放置位置与反馈契约

诊断位于**首候选确定性校验失败后的反馈组装、第二 Formation 请求之前**。首候选若存在覆盖错误但原始完整 Wire 的身份、Schema 与组件位置可确定，复用 `_owner_repair_context` 已有的未接纳观察视图；不接纳局部 Candidate，也不提前运行完整 Review。

在 [Formation Owner](../../../src/spg/application/governed_obligations.py) 内增加 `_consumer_mapping_diagnostics`，结果进入现有反馈的 `owner_repair_context.consumer_mapping_diagnostics`。本原型只观察原类型为 `EQUALITY` / `CARDINALITY` 的 Fact 提议 `EXACT_GIT_DIFF_SCOPE` 时的高风险方法组合，要求修复者比较**完整 Fact 的值、限定条件与 changed-path 集合实际能证明的内容**。不读取 Subject、文件名或场景 ID 决定消费者。

这是保守的风险选择条件，**没有执行开放语义判决**。值本身表示合法路径边界的 EQUALITY 也可能被提示，仍可保持原方法并交给完整 Review。因而输出明确标记：

```text
UNREVIEWED_RISK_ONLY; NOT_A_VIOLATION_OR_REVIEW_VERDICT; NO_EDIT_OR_PASS
```

输出包含原 route/source 序号、component ID、候选 fingerprint、方法的实际可观察量，以及回到不可变库存原 Fact 的引用。最多列 16 条风险并保留额外数量，不声称穷尽诊断。原始约束、完整库存和既有错误集合均保留。

新请求收据记录 `consumer_mapping_diagnostic_contract=existing-consumer-mapping-risk-v1`。诊断随原有反馈绑定原 Wire fingerprint、库存、Attempt、请求/响应收据；恢复时按同一原始输入重建并比较反馈。历史请求无此标记时不补入新反馈。篡改诊断 route，即使重算反馈自身 SHA/字节数，仍被反馈血缘校验拒绝。

[Provider](../../../src/spg/providers/fulfillment_candidate.py) 只在原有修复指令中说明该字段的非裁决性质。局部编辑仍由模型显式提出；Owner 不自动删除或更换路线。Formation 候选数、Review 次数、传输恢复和总调用上界不变；诊断本身不调用模型。

## 3. ordinary34 原始候选 → 诊断

[只读回放收据](receipts/ordinary34-readonly-replay.json) 与 [回放工具](replay_ordinary34.py) 使用原始首响应，SHA256 `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`。

| 观察 | 结果 |
| --- | --- |
| 原首候选 | 32 条 route；原停止原因 `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST` |
| 诊断点名 | route 1、3，对应 source 0、1；两条内容 Fact 的额外 Git Diff 路线 |
| 原正确范围消费者 | source 2 / route 4 不在此风险列表 |
| 原反馈大小 | 65,497 bytes |
| 增加诊断后的大小 | 66,390 bytes；增加 893 bytes |
| 新反馈 SHA256 | `6503e481b0ebfe6f5a4cc6a5817a7f065dcbcf99981bcd1973ef731296b67ffb` |

上述是隔离副本的诊断与体积实测，没有改写原反馈收据；没有以此证明所有持久化记录或其他规模库存均满足容量上限。

## 4. 一次真实第二候选探针

使用原首响应及原绑定修复上下文，在独立探针中加入上述诊断，保留普通34第二请求的原 Owner 前提及原局部编辑基础。仅调用一次 Formation，无新 Work、数据库访问、第二次重试或 Review。该探针不是向原 Work 恢复一次新 Attempt。

[实际 Provider 收据](receipts/live-probe.json) 记录：`deepseek-flash`、`reasoning=none`、上限 16,384、timeout 120s；request ID `4f536808-993b-40c1-80f6-226c4d231d64`。模型观察到的反馈 SHA 与上表一致；Provider 状态 `completed`，0 次传输重发，输出 6,786 bytes。完整私有响应保留在 ECS，未复制到公开报告。

| 检查 | 实际结果 |
| --- | --- |
| 诊断进入请求 | 已确认：实际请求反馈 SHA 与包含诊断的反馈一致 |
| 修正错误 Consumer | 未发生：没有替换或删除 route 1、3 |
| 局部编辑 | 替换 route 5、6、7、8、9、16、17、18、19、20；删除 0；新增 2 条 Git Diff 路线 |
| 保留正确部分 | 原未编辑路线中包括正确内容 route 0、2 和正确范围 route 4；不能据此认定全部正确决策均保留 |
| 完整校验 | `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`，source 4、11 仍有覆盖缺口 |
| 独立 Review / Admission | 未进入；未授予 PASS |

具体编辑序号和失败谓词见 [私有响应的脱敏只读检查](receipts/probe-edit-inspection.json)。

实际用量：input **87,782**、output **2,169**、reasoning **0**、total **89,951** tokens；cached input 1,152（包含于 Provider 输入统计，不额外相加）；模型请求完成耗时 **10.251s**。货币成本 UNKNOWN。

**失败归属：** 反馈传输接线已成立；本次响应没有把点名风险转化为对应局部修复，并再次违反既有覆盖契约。诊断只提出未审查的方法风险，没有提供已核验的语义负观察。单次探针不能进一步区分“风险诊断不够明确”与“模型本次未利用这类反馈”，更不能证明模型普遍没有该能力。现有 remove/replace 能表示修复，所以本轮没有发现 Consumer 表示不足的证据。不得把本结果算作 Consumer Mapping 已收敛。

## 5. 定向正负验证与实际限制

[新增测试](../../../tests/test_c3_early_consumer_mapping_diagnostics.py) 的 3 项均通过：诊断不编辑候选或给裁决；首候选结构失败时诊断进入第二请求且绑定血缘；合法路径值 EQUALITY 仍有资格进入原 Review。血缘测试同时覆盖诊断篡改、未知诊断契约及历史无标记请求保持旧反馈。

联合执行原 Wire feedback、Reviewer feedback、Fact method applicability 定向回归：**107 项执行，105 PASS，2 FAIL**。完整 [日志](receipts/prototype-focused.log)、[JUnit](receipts/prototype-focused.xml) 和 [资格汇总](receipts/qualification.json) 已保存。两项失败为重复响应/重复验证收据的终止错误码断言：实际均在新模型请求前停止于 `OBLIGATION_FORMATION_RECEIPT_REFERENCE_DRIFT`，旧断言期待 `OBLIGATION_FORMATION_WIRE_FEEDBACK_IDENTITY_DRIFT`。

这两项在**不挂载本轮源码的原镜像**中同样复现，见 [基线对照](receipts/unchanged-image-duplicate-controls.log)；没有改断言使其转绿。此次联合回归不能记为全 PASS，也没有执行 PostgreSQL 或完整应用集成资格。

首次持久化 JUnit 时，资格输出目录对容器用户不可写；保留 [原失败日志](receipts/harness-junit-permission-failure.log)，修正该隔离输出目录归属后保存最终收据。此为验证工具的输出问题，未修改应用权限。没有因此重发真实模型请求。

## 6. 结论与最小下一步

原型的最小成功条件已达到：**错误 Consumer 对应的风险信息可在首候选反馈中被定位，并送入既有 Repair Context。** 更强的行为效果没有达到：本次第二候选未纠正该映射，完整候选仍被原门禁拒绝。

下一步应先评估现有修复决策如何消费这类“未核验风险”，以及现有独立 Reviewer 的窄诊断契约能否在原总预算内提供可归属的语义负观察。当前结果不足以支持增加静态拒绝规则、扩大候选次数、重复同条件模型调用或调整最终 Review。不得把提示送达等同于有界语义收敛，也不能据此关闭 C3。

跨电脑恢复位置：本目录的源码工具、脱敏 JSON、日志和 JUnit 随原分支提交；ECS `/data/watt/ai-native-evolution-20261013/early-consumer-diagnostic-20261014/` 保存原型源文件、测试副本和运行证据，`private/` 保存完整私有反馈及响应。原 ordinary34 收据仍位于 `/data/watt/ai-native-evolution-20261013/nonholdout-15/private/ordinary34-owner-receipts.json`；原库存位于 `/data/watt/c3-semantic-convergence-20261009/non-holdout-cause-control-20261012/private/ordinary34/immutable-inventory.json`。公开证据不包含凭据或完整 Human 原文。
