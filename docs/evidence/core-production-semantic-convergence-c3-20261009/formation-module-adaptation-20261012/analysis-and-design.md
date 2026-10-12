# WORK_FULFILLMENT_PROJECTION：职责分析与最小修复

2026-10-12；实施前分析。依据当前 Human 任务、C3 Mission、Program ADR-0002、Watt 开发原则 §13/§14。证据起点 `70ef6f7eef88e63a96efac5acae38f046508b1d1`，应用起点 `01446afc7cccb03f99e8e6febbe4cfe9ed8388e4`。本轮只用非 Holdout 开发材料；保留原资格结果和封存事实。

## 1. 实际职责边界

`fulfillment_inventory` 从已接纳 Work Reality、IR/Fact/provenance、源码版本和精确 Task 路径构造完整库存。`_owner_source_preconditions` 引用真实 Owner 契约，提供必要来源、类型、操作数及阶段资格。它不推荐业务实现，也不宣告证据已取得。

`ModelFulfillmentCandidateProvider.form` 在同一库存上提出来源组件、能力、目标和来源支撑的派生计划。Wire v1 的 ordinal/header 是可逆的请求表示，不是工程事实。Decoder、唯一原文 locator 和 `validate_projection_candidate` 先检查身份、跨度覆盖、权限、处置、方法及依赖资格；合格才进行独立 Semantic Review，再接纳为已有履行绑定。

证据主要是**履行前提与未来所需证据契约**，不是 Formation 内已经执行的内容验证。当前绑定为 `BOUND_PENDING_EVIDENCE`；后续现有 Verification、Native Gate、Candidate、Human Gate 与 Guardian 各自检查真正履行。不存在模型自行授予 PASS/权限的合法路径。

收据记录两个累积 Candidate、一个反馈、每 Candidate 一次 Review、最多四次逻辑调用。恢复使用同一库存/源码/Attempt/原始 Wire/持久收据；未观察到请求终态时停止 UNKNOWN，不重置预算。

## 2. 确定性假设与失败分类

没有找到要求唯一代码实现或唯一履行 Owner 的全局假设。现有契约允许同一来源多组件、多个互补消费者、不同原文跨度与合法混合阶段；独立 Review 比较意图/证据语义。精确身份、原文覆盖、权限及同物理组件处置一致性是治理约束，不能作为“非确定性适应”而放宽。

确认一个**生成接线缺口**：旧生成路径把既有完整组件处置不变量投影到输出 schema，而当前 qualified-operand 生成路径提前 return，只接上逐 Route 的几何、来源和能力前提，漏掉集合级的同完整组件矛盾处置约束。最终 Validator 正确拒绝，但模块让已知不可成立的候选进入一次有限修复窗口。它不是合法替代实现被 Validator 排斥的证据。

来源缺口的直接现象仍是 A：候选未遵守原文覆盖契约。当前反馈已有范围/Route 错误，但来源联合贡献与同组件处置散落在不同诊断结构；修复者必须自行重建集合关系。改进应是当前 Owner 提供可确定性复核的联合观察，而不是默认扩大引文或替模型决定哪个 Route 应删除。

| 用户分类 | 本轮判定 |
| --- | --- |
| A：模型未遵守契约 | 已证实：非 Holdout ordinary34 的缺口及 ordinary41 的同组件冲突 |
| B：Formation 不能识别合法替代路径 | 未证明普遍不支持；已有合法多组件对照通过。当前生成分支遗漏既有约束投影是具体系统接线缺陷 |
| C：Evidence 映射不足 | 本次失败尚未执行实际证据消费；没有证据证明 Owner 方法不存在。不能把未来证据尚未产生误作目标失败 |
| D：收敛无法处理不确定性 | 真实候选未在既有窗口收敛，能力资格不足；不等于应增加重试。补齐当前模块的集合级生成与反馈消费能力，再独立证明收益 |

## 3. 与 AI-Native Module 原则的距离

- 合法语义等价实现：已有模型候选 + 独立语义 Review；确定性层只验证合法边界，不能自动裁决任意语义等价。仍需真实模型资格。
- “表达不同但满足”与“目标未满足”：在方法合法且 Review 通过之后交真实 Owner 验证，不能仅凭字符串跨度宣布产品达标。
- “证据不足”：已有 `BOUND_PENDING_EVIDENCE`、`UNRESOLVED`、`UNVERIFIABLE_CURRENT` 和请求终态 UNKNOWN。`validation_passed=False` 是拒绝当前候选，不必等同于证明产品目标不能满足。无需新增平行 UNKNOWN 状态机。
- 差距：当前生成准备没有始终复用其自身集合不变量；反馈没有一个直接体现同来源联合覆盖和物理组件处置的可复核视图。补齐这两个当前模块能力，保留独立语义判断及证据未知。

## 4. 实施边界

1. 在现有 Provider 内复用旧完整组件冲突约束，接入当前 qualified-operand 请求。只约束已有非法组合；不选择能力、不限制多个互补执行消费者，也不改变 Wire v1 或 Validator。
2. 在现有 `_owner_repair_context` 内形成来源/组件联合观察：原文指纹、已定位 Route 身份、联合字符覆盖、缺口、同物理组件处置及独立语义/真实证据尚未知。该视图只指导现有一次修复，不补引文、不删 Route、不制造 Evidence。
3. 新请求用一个 Owner 内部适应契约标记绑定以上变化。旧请求/反馈/历史回放不升级；新视图参与既有 Wire/库存/Attempt/收据反馈身份复核。预算、模型路由、Review 和 Guardian 不变。
4. 开发验证包含不同合法分解、多组件协同、证据待取得、遗漏义务、冲突/版本/来源篡改、反馈恢复与终态不重复调用。使用已有开发库存及完整原始失败 Wire；不阅读 Holdout 私有材料。

本修复没有确定性替代开放语义选择；提供的是当前模块本来已经负责的不变量和反馈集合关系。受控验证通过只证明该改动的边界有效；真实模型收敛和最终泛化资格需另行取得。完成开发验证后提交 Human Holdout 复验决策包，未获本轮末决策前不运行 Holdout。
