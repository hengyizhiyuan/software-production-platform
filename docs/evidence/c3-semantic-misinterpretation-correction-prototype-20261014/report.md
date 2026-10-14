# C3 Semantic Misinterpretation Correction Prototype

2026-10-14。基线分支 `codex/c3-open-semantic-obligation-convergence`，HEAD `86619c7ce28febcd916a767a98e3ffeefed25171`。

**本轮观察到真实的候选映射修正：模型删除了 ordinary34 原 route 1、3 的额外 Git Diff 消费者，同时保留对应内容路线与真正文件范围路线。完整候选仍被原门禁拒绝；本结果只满足本原型的窄成功条件，不关闭 C3。**

## 1. 冻结输入与边界

继承 [Decision Revision Calibration](../c3-formation-decision-revision-contract-calibration-20261014/report.md)。在调用前保存 [实验协议](protocol.md)、[完整预检](receipts/preflight.json) 和实际容器身份，冻结成功/失败的观察口径。只做请求副本原型，没有修改运行时代码、Validator、Review、输出 Schema、静态路由规则或候选额度；没有创建 Work、运行 G0、触碰 Holdout、生产或历史 Owner。

原库存保持 19 项，fingerprint `b023bae819f456da05abe983f48da4f2157da60df412de909f9f834991bcef29`。原编辑基础仍是第一次 Wire，SHA256 `893f167cab558759ab2eb2a2a3664e2d57650e71a0077b2fcf6e5553928ebc4e`。上次未接纳解释来自 request `095fd0ac-7701-49c2-8c75-8de5bceb83a5`，响应 SHA256 `b5ff1b986992a1423eaf4b5ae65b6d21d88f2af77f6acf9e1743680ea35fbc90`；它作为 **Claim observation** 输入，没有变成 Fact 或独立 Review 结论。

使用原隔离镜像 `sha256:73da30f5567f5766b9767855c1e772fc5421d93a9da54f99a971db9d2f48ce53`，只读挂载此前两个未变源码文件，实际文件 SHA 见预检。该运行方式是原型资格，不是新完整应用镜像资格。准备阶段禁网；实际调用容器的只读输入、用户与镜像事实见 [live-runtime.json](receipts/live-runtime.json)。

## 2. 新上下文的六个部分

在原有反馈的 `owner_repair_context` 中增加 `semantic_assumption_review`。公开的 [脱敏结构](receipts/assumption-context-redacted.json) 保留身份与语义边界，完整旧解释只保存在 ECS 私有证据中。

| 要求 | 本原型如何表达 |
| --- | --- |
| Decision to reopen | 引用原 route/source/component ID、原 route fingerprint；沿用此前重评对象，不另造语义身份 |
| Current interpretation | 引用上次模型的实际方法解释原文及其 SHA、响应 SHA、request ID；明确标记未接纳 Claim |
| Assumption under review | 指出待复核前提：Fact Subject 中的文件身份本身，是否足以产生原 Fact predicate 之外的独立 changed-path 义务 |
| Why it may be invalid | 要求指出原始 relation/value/Scope/qualifier 中哪一部分真正蕴含新增 predicate，区分对象身份、来源支持与需履行要求；这是假设挑战，不是门禁判决 |
| Facts unchanged | 保留原来源版本、Fact 原值/顺序/Scope/限定条件/权限、完整原义、已有门禁和其他合法贡献 |
| Reconsiderable fields | 允许模型重新选择 capability、依赖、目标、来源支持与方法解释；仍通过已有显式 replace/remove 表达 |

**没有提供替代 Consumer、建议删除的答案、预制映射或确定性路由。** 模型可以根据完整原事实反驳这个挑战；新解释仍必须经过原校验和独立 Review。请求仅要求已有公开 rationale 在适用时说明选择的语义与被拒绝/未决解释，不索取隐藏推理，也不增加响应字段或要求枚举多余路线。

## 3. 预检消除了上轮探针接线错误

本轮没有手填 `candidate_construction_state.repair_targets`。完整状态由未修改的 `candidate_construction_preconditions` 从确切反馈生成，再验证完全一致的重建结果；原覆盖/来源错误集合没有删减。

预检通过：

- Owner 前提重建完全相同，未插入派生状态；指令 SHA 与此前相同，输出 Schema 完全相同。
- 原 Wire、库存、决策身份、旧解释响应漂移均在网络调用前被拒绝。
- 在新请求上下文中，原样解码上次响应仍返回覆盖失败，没有发生身份绕过或误放行。

新反馈 74,067 bytes，SHA256 `9dc192e61dfd83c8c4a0748400df4c04833e699c08cac64a99d83bc4f759e8e1`；实际 Provider 记录的反馈 SHA 与冻结值一致。完整预检见 [preflight.json](receipts/preflight.json)。

与历史样本相比，本轮同时修正了其非法派生状态接线。因此这是**历史描述性对比**；没有额外调用一个新控制组，不能把行为差异全部归因于假设字段，也不能排除模型随机性。

## 4. 唯一一次真实探针结果

[实际响应收据](receipts/result.json)：request `c8cdb73b-0228-45b4-bf75-242782296ad8`；响应 SHA256 `3f1ad40064b1816a7de63881738dff91563ca982b37401aabb7d65d2a79586df`。Provider `completed`，1 次 Formation、0 次 Review、0 次传输重发，没有追加候选。

| 检查 | 上次：决策重开、没有具体假设复核 | 本次：加入具体假设复核 |
| --- | --- | --- |
| route 1、3 | replace，但仍为 Git Diff；只改 quote/rationale | 模型显式 remove，两条额外消费者均删除 |
| 同一 Fact 的合法内容贡献 | 原保留 | 原 route 0、2 保留；source 0、1 仅剩 ARTIFACT_CONTENT，覆盖完整 |
| 真正文件范围贡献 | 原保留 | 原 route 4 保留；source 2 的 GIT_DIFF_SCOPE 和覆盖完整 |
| 其他修复 | 没有处理原覆盖/来源修复路线 | 显式替换另外 17 条原路线，没有 append；仍有未关闭失败 |
| 实际停止 | Owner 派生状态不一致 | `OBLIGATION_COMPONENT_SOURCE_CONTRIBUTION_LOST`，source 3、10 |

模型的删除操作直接改变了原始提案的 Consumer 集合，Owner 没有自动选解或删除路线。只读观察恢复了全部 30 条新提案路线，确认 source 0、1 没有在其他位置重新出现额外 Diff。**这是映射层的语义修正行为，而非仅把原解释换一种措辞。** 它不证明模型的隐藏理解过程，也不证明剩余方案整体正确。

### 三个问题的直接回答

1. **是否放弃旧 Consumer 假设？** 在可观察候选处置上是：依该假设提出的两个额外消费者被删除，原内容与独立范围贡献保留。内部信念如何变化 UNKNOWN。
2. **是否提出替代语义解释？** 形成了一个与旧提案不同的路由组合；但 remove 本身没有 rationale 字段，模型没有对这两个被删决策返回新的文字解释或显式多方案比较。不能宣称已观察到多种备选解释或完整假设推理过程。
3. **来源与覆盖是否保留？** 目标 source 0、1、2 的身份、消费者与覆盖保持；替换路线的 primary source 未漂移，目标路径均在原 allowlist。全计划没有全部满足来源/覆盖契约，见下节。

## 5. 未通过的原门禁

[来源与覆盖只读观察](receipts/source-coverage-observations.json) 复用既有 Wire locator 和 Owner 前提诊断，没有制造部分接纳结果：

- source 3、10 各有 3 个非空白字符未被组件跨度覆盖，仍被完整解码器拒绝。
- 原 Owner 前提诊断还识别 source 14 的 `OBLIGATION_SUPPORTING_SOURCE_CORRESPONDENCE_UNPROVEN`，新提案 route 23；该来源对应关系没有得到证明。
- 当前连续禁止约束等路线仍保留，但保留路线不等于实际 Effect Evidence、Assurance 或未来 Human 授权已经成立。

没有返回一个合格的 canonical Candidate，因此完整后续 Candidate Validator / 独立 Semantic Review / Guardian 均未执行或通过。没有扩展这次原型去修补覆盖、来源证明或其他语义问题；原停止证据完整保留。

## 6. 范围结论、消耗与恢复

**本次原型的窄成功条件达到：观察到真实 Consumer 集合修正，且对应原始内容/范围贡献仍在。** 这支持继续评估“把具体错误假设作为有来源的待复核 Claim 暴露给修复者”的价值；不支持自动把所有风险判错、自动消费假设分析为 Fact，或将该提示直接固化成生产静态规则。

尚未证明：假设字段的独立因果效果、完整语义正确性、覆盖与来源修复的稳定协同、跨场景泛化或 C3 Closure。本轮只验证原型；不安装新运行时契约、不启动其他修复或资格。

实际用量：input **90,345** / output **2,811** / reasoning **0** / total **93,156 tokens**；cached input 82,176 为输入子集。`deepseek-flash`、reasoning `none`、上限 16,384、timeout 120s 均未变；请求完成耗时 **10.356s**；货币成本 UNKNOWN。没有因失败再调用模型，也没有运行无关的大回归。

[完整性收据](receipts/postflight-integrity.json) 确认原 Owner 收据、原库存、上轮解释响应文件的 SHA 均未变化。完整私有反馈及响应留存于 ECS `/data/watt/ai-native-evolution-20261013/semantic-assumption-review-20261014/private/`；协议、工具和脱敏收据随本目录提交，跨电脑可从原分支恢复。原始输入只读挂载，未传递业务数据库或 Docker Socket。**C3 保持 PARTIAL。**
