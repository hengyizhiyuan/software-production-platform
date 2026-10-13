# C3 独立 Holdout 新修订复验

2026-10-13（Asia/Shanghai）。**C3 PARTIAL — Independent Holdout NOT_QUALIFIED。** 本轮经 Human 明确批准，仅验证固定新修订；未修改实现、输入、Oracle、Validator、Guardian、历史 Evidence 或封存 Candidate。

## 结果

| 原封存场景（匿名序号） | 上轮终态 | 本轮终态 | Fulfillment Projection / Evidence 变化 |
| --- | --- | --- | --- |
| 0 | 来源字符覆盖缺口，FAIL | 第一候选 `OBLIGATION_FORMATION_WIRE_SCHEMA_INVALID`；第二候选 `OBLIGATION_PROJECTION_CONFLICTING_DISPOSITION`，FAIL | 两次候选、一次既有反馈；没有接纳 Projection，没有进入独立 Review。不能把失败类别变化记作自然恢复 |
| 1 | 同组件矛盾处置，FAIL | 首候选同组件冲突；第二候选 `OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN`，FAIL | 推进到来源证明检查，但支撑来源尚未证明对应；没有合法绑定或新的 Owner Evidence |
| 2 | 同组件矛盾处置，FAIL | 第一候选 `OBLIGATION_FORMATION_WIRE_SCHEMA_INVALID`；第二候选 `OBLIGATION_FORMATION_WIRE_FACT_KIND_INVALID`，FAIL | 候选 Wire/Fact 来源类型未合法收敛，没有接纳或独立 Review，不能称新的证据映射通过 |
| 3 | scoped WIC/IRK/Formation/Review PASS | 两次 `OBLIGATION_FORMATION_UNSAFE_JSON_RECEIPT`，FAIL | 本轮停止在安全 JSON 收据边界，未接纳；旧 scoped PASS 未在此试次维持。不发布被拒的 Provider 原文 |
| 4–7 | 4/4 scoped controlled Owner PASS | 4/4 scoped controlled Owner PASS | 原封存负向配方仍拒绝不合格来源/证据/权限；受控结果不替代四条真实模型资格 |

**真实模型 0/4 PASS；受控 Owner 负向 4/4 PASS。** 四个真实场景各用完最多两次 Formation、一次既有反馈；实际独立 Semantic Review 调用 0，未把未决映射或安全拒绝改为 PASS。逐次 Wire/库存/版本/反馈收据关联见 [独立最终判断](independent-review/qualification-final.json)，不是依错误标签编造结论。

### 逐场景 Projection 与证据映射的具体变化

| 序号 | 来源库存数量（旧→新） | 本轮原始提案 Route（第一次→第二次） | 最终履行映射 |
| --- | --- | --- | --- |
| 0 | 18→21 | 35→31 | 21 条原来源均保持 UNRESOLVED；0 个接纳组件，0 条实际 Verification/Guardian Evidence |
| 1 | 19→24 | 49→43 | 24 条原来源均保持 UNRESOLVED；0 个接纳组件，0 条实际 Verification/Guardian Evidence |
| 2 | 25→20 | 50→50 | 20 条原来源均保持 UNRESOLVED；0 个接纳组件，0 条实际 Verification/Guardian Evidence |
| 3 | 16→25 | NOT_EVALUABLE→NOT_EVALUABLE | 25 条原来源均保持 UNRESOLVED；原响应未作为可安全持久 Candidate 收取，0 个接纳组件，0 条实际 Verification/Guardian Evidence |

Route 数是**未接纳提案的观察**，不能当作已证明的语义组件数。四个场景都没有合格 Owner/Phase/Evidence 映射。来源与关联并未删除：终态 fallback 保留全部本试次来源，以 UNRESOLVED Owner/Phase/Method 明确停止；该 fallback 不是通过的 Projection。

第四场景的 [独立安全分类](independent-review/unsafe-json-classification.json)确认：两次原始响应均为含转义符的非法 JSON（EXTRA_DATA），无法证明安全可收取；Provider 均 completed。**未证明命中密钥/凭据，不能称为凭据泄露。** 不截取 JSON 前缀、删除转义符或生成修补后的 Candidate 来追认通过。

## 当前能力是否自然恢复

本轮**没有证明原失败在新能力下自然恢复**。集合约束和来源联合反馈已进入固定模块，但没有形成合格、被接纳的实际 Projection。因此多来源联合覆盖、多组件协同、合法实现变化的真实泛化资格仍未取得；此前开发控制正例不能替代本轮结果。

这是原封存库存在新修订上的独立复验，不是首次未见 Holdout。本轮真实入口重新经过 WIC；原输入/Oracle 不变，不意味着每次生成的 IR/Fact/库存也完全相同。四个新库存的语义来源摘要在排除 volatile identity 后仍均不同于旧库存。新旧库存/候选只按各自真实身份关联，不能断言终态差异完全由 Formation 修复引起；新旧 WIC 语义忠实度比较仍 UNKNOWN。

本试次 WIC→库存的 28/28 Clause、28/28 Item、22/22 Fact 语义及 provenance 字段保持；四条原用户输入 hash 均符合封存身份，ProductionIntent/约束/Context 原值保持。该保留证明不替代开放语义等价判断。独立 Reviewer 保留 WIC 与 Formation 的分层对照；实现者不读取封存私有内容或用失败样例调优。

## Evidence 与 Guardian 边界

- 所有真实场景均未接纳履行计划。被拒 Route 是候选观察，不是已成立的工程事实、Evidence 或权限。
- 没有实际语义审查结果可作为本轮合格映射；也没有新 Artifact Verification、Candidate Seal、Native Effect 或 Human 决策。
- 原四个 Owner 负向检查保持其 scoped 控制范围。没有将证据不足、语义猜测或不存在的事实提升为本轮 PASS；这不构成任意输入永无错误的普遍证明。
- [实际受控谓词补充](independent-review/controlled-evidence-addendum.json)：序号 4 拒绝错误 Source Revision 和 Work Reality；序号 5 的 scope/seal eligibility 在缺独立 Review、缺 Review 观察收据、错误 capability fingerprint 时均为 false。它验证资格前提，不是实际产物内容 Verification 或 Candidate sealing。
- 原持续权限场景通过真实 Owner 读取拒绝 Deploy/Publish（`OBLIGATION_DELIVERY_PROHIBITED`），未发起外部效果。未来 Human Gate 场景中缺 Native、缺来源引用、虚构授权的结果均为 false；合法未来门禁保持 PENDING，不生成 Human 授权。受控正例仍是既有 Owner 配方，不称为真实软件生产。
- 本 suite **未执行**产物内容变造、虚构不存在 Fact 内容、缺失/错误独立 Guardian Evidence 的额外负例；不以“没有任何真实候选通过”推导这些未知场景也已经资格通过。没有增加新 Oracle 或试验来扩张本轮范围。
- **本 Holdout suite 未调用独立 Guardian：NOT_CALLED_THIS_SUITE。** 不为填报告添加新 Assurance 请求或把 Watt 控制通过称为 Guardian PASS。
- 已有真实 G0 Candidate `4a4096c3-2846-5678-ab8c-37aed60a0c9c` 的独立 Guardian 请求 `6b28aa08-4484-5860-9648-8aa2e8b3737d` PASS / 0 Findings 保留为独立历史证据；它不是本轮四个失败场景的 Assurance。

## Exact 身份与执行范围

- 应用源码 `f52d39965826ba2e9ddcdba44c85e79bf5c43fc0`；Tree `c8ad5b06283905e218786ef785e940a82edd1dbf`。
- 实际 Image ID `sha256:24d9f809ad3cd6b98d68948020fccd3997c09ee947f9cb5acd57e48abb44e5b1`。
- Guardian `0d7aca954588c8ad3883dbedb730e59dc1d7b867`；ECF `5aa4f8833c359c15bd059eda5972aa3915bcc18c`。
- 原封存八项库存 `3f093e0d09bec5d2f213ba4e823adbb6dcf42678acc4f76847bf4bb46b1eedb0`。
- 实际 image/labels/env/installed import 由独立 Reviewer 核对；原 91 个 trial 文件前后 hash 固定。新增试次使用专用隔离 PostgreSQL/卷，不改历史 Work 或正式 Production Reality。
- 资格恢复根目录：`/data/watt/c3-semantic-convergence-20261009/independent-holdout-requalification-20261013-020000Z`；私有 Provider 内容/Oracle 只在独立受限目录保存，公开证据由 Reviewer allowlist 发布。

## 资源与 Closure 判断

实际逻辑模型调用 **14 = 8 Formation + 6 WIC**，独立 Review 0；pending 14 / observed 14，未知终态 0。Formation/Review 使用 8 次，未超过原 suite 的 16 次上限；额外算术空间不授权再次打开已终态场景。

[实际 Provider Usage](independent-review/usage-final.json)：input **579,996** / output **85,136** / total **665,132 tokens**；cached 40,704、reasoning 18,309 是已包含的子计数，不重复相加。Formation 总计 513,188 tokens，WIC 151,944。原同库存试次与本次累积 28 次 / 1,279,752 tokens；原更早 24 项试次 33 次 / 789,271 tokens 单独保存，不算本次资格。

实际 live wall time **366.652 秒**，controlled **8.201 秒**；Formation 调用耗时合计 138.704 秒，WIC 217.376 秒。所有 Formation output 低于 16384，传输重发 0，Provider completed 与终态文本对应；明确 finish_reason 未捕获，不猜测。HTTP 传输次数、货币成本、CPU/峰值内存仍 UNKNOWN；不从逻辑调用次数猜测。

原 C3 Mission 的独立泛化资格未满足，**不能 C3 CLOSED**。原 G0 生产结果、Verification、Preview 与实际 Guardian 历史资格保持；Human Integration/Acceptance/Delivery 仍未授权或待决。没有启动 C4/N1/N3、重新生产 G0、实现调优或额外模型诊断。

本轮按授权执行至终态后停止。若继续工程改进，应仅以非 Holdout 开发库存建立共同原因和合法表达证明；本报告本身不授权通过重跑本库存、改 Oracle、加特例、预算扩张或门禁放宽取得成功。

## 收据与持久恢复

独立公开包 v2 的 [交付收据](independent-review/public-delivery-receipt-v2.json)及 [允许清单](independent-review/public-manifest.json)标识 13 个公开 JSON；完整原始 Provider/候选/Oracle 排除在公开包外。Archive SHA256 `4a01f9e8539ff2ea5451b75003abaf360512e688ea861908898fce7a967653af`；最终资格收据 SHA256 `b376174621f69da093a3c9870bf14f379086af9f67ff80abab135e3cb5dbdedd`。

[收据连续性](independent-review/receipt-continuity.json)证明原 91 个文件 hash 一致、八项新 trial 均单一终态、请求/观察对账完整。新 PostgreSQL 已停止，独立卷、网络、容器和私有恢复资料按 [保留收据](independent-review/resource-retention.json)保存；未进行恢复演练，不宣称恢复资格。

执行副本沿用此前已证明的 retention 方法 selector 机械接线（原文本/Oracle 不改），其原件及窄 diff 血缘保留；本轮 Docker IPAM 空配置处理发生在设施创建前，没有模型调用或预算重置。[机械接线](independent-review/mechanical-selector-lineage.json)、[准备恢复](independent-review/preparation-recovery.json)如实分类。没有覆盖历史失败或运行时源码。
