# Watt AI Native Architecture Standard v1.0

- **版本：** 1.0
- **批准：** Human Governor，2026-10-13（Asia/Shanghai）
- **性质：** 架构标准，不是功能设计、实现方案或运行资格报告。
- **范围：** 未来 Watt 模块的 AI Native Contract，以及核心模块的架构评估。

## 1. Purpose 与权威关系

基于 C3 Semantic Convergence、Trace Self Analysis 的实际工程验证，建立模块面对非确定智能输入时必须满足的架构契约，防止以 Prompt、规则和特例堆积模拟智能能力，却保留固定输入、唯一输出和失败即重试的假设。

最高 Program 准则仍由 [ADR-0002 固定版本](https://github.com/hengyizhiyuan/software-production-system/blob/1e2c1fdf37d9252c0a9bd480fc2ff15c88d0fee1/docs/04-decisions/ADR-0002-STOCHASTIC-NATIVE-ENGINEERING.md)拥有：**Reuse Determinism, Harness Stochasticity**。

本标准是 Human 本次批准的模块契约及成熟度标准，与 Watt [开发原则 §13/§14](ai-native-development-execution-principles.md#13-ai-non-determinism-principle-and-execution-discipline)共同使用。§13/§14 继续规定既有 Owner 内的执行、恢复及维护职责；本标准不转移这些职责，不创建新治理 Owner 或平行生命周期。

[Phase 0.5 Repository Reality 评估](watt-ai-native-evolution-assessment.md)记录当时实现与资格；本标准不将其中的评估、历史失败或待证项改写为新事实。文档批准、分支发布、进入权威默认分支与 Runtime 达标是不同事实。新增本标准不表示当前模块已经符合它。

## 2. Core Definition

**AI Native Module 不由内部是否调用大模型定义。**

判断标准是：模块在面对非确定性、语义变化、不完整信息和概率性推理结果时，能否在自己的责任边界内保持：

- 正确的现实边界；
- 可解释、可审查的决策过程；
- 有界探索；
- 可恢复收敛。

直接调用 LLM 不足以构成 AI Native。确定性消费者也必须处理其责任内的智能输入变化。Hash、事务、精确身份和权限检查可以保持严格确定性；它们保护工程不变量，不负责替代开放语义判断。

## 3. AI Native Module Contract

### 3.1 Semantic Adaptation

模块必须能够处理：

- 同一意图的不同表达；
- 合理但不同的候选方案；
- 不完整输入；
- 模型输出格式变化。

**禁止将单一表达形式等同于真实意图。** 合法方案可以有不同的实现、步骤或表达，必须保持原目标、约束、Scope、来源和权限的等价性。

格式变化应在现有 Owner 内被识别、合法解释、修复或如实拒绝；不能让尚未满足既有 Wire、身份或安全契约的对象直接晋升。适应能力不要求接受任意输入，也不能静默补齐缺失语义。

### 3.2 Reality Boundary

模块必须明确区分：

| 角色 | 定义 | 权威边界 |
| --- | --- | --- |
| Fact | 已经确认的工程事实 | 由适用 Owner 按合法 authority、来源、版本和接纳契约确认 |
| Observation | 实际观察到的信息 | 带观察对象、来源及适用范围；不自动证明声明成立 |
| Inference | 基于事实的推理 | 保留依据与不确定性，不能产生不存在的权威事实 |
| Claim | 候选声明 | 待验证；自述、候选方案和模型判断不能自行授予权威 |
| Evidence | 证明声明成立的依据 | 必须满足对应声明的来源、版本、Scope、阶段和证据契约 |

禁止：

- Claim 自动升级为 Fact；
- Observation 自动升级为 Evidence；
- Model output 自动成为 Reality；
- 将存在记录当作履约证明；
- 将候选方案当作完成结果。

Observation 可以在适用 Owner 校验其关联性、完整性和证明范围后成为对应 Evidence；不能仅凭“观察到了”就证明任意结论。结构合法、引用真实与语义成立也必须分开。

这些是语义与权威边界，不要求新增五套数据库实体或统一状态机。原 Owner、Fact、Work、Candidate、Verification、Guardian 和 Human Gate 保持各自职责。

### 3.3 Uncertainty Handling

模块必须支持以下含义：

| 含义 | 必须保留的信息与处理 |
| --- | --- |
| UNKNOWN | 当前不知道什么、已观察范围及证据限制；不猜测为确定事实 |
| CONFLICT | 哪些解释、来源或要求冲突；不能静默覆盖或选取 |
| ALTERNATIVE | 多种合理候选及各自依据；没有足够依据时不强制选定 |
| NEED_INFORMATION | 所需信息、合法来源/Owner，以及等待、获取或停止的边界 |

禁止为了得到确定输出而猜测缺失信息、强制选择没有依据的方案或隐藏不确定性。

这些含义可以由现有状态、结果、Finding、候选及收据表达，不机械要求新增同名字段。UNKNOWN 不自动 PASS，也不能用它隐藏已知真实错误。未来授权可以合法保持待决；持续性禁止约束必须从适用阶段受实际 Gate 保护。

### 3.4 Convergence Control

任何涉及 AI 推理、搜索、调查或修复的模块必须定义：

| 契约项 | 必须回答 |
| --- | --- |
| Exploration Boundary | 可探索哪些输入、来源、方案和动作？现有权限、Scope、时间及资源边界是什么？ |
| Progress Signal | 哪些实际观察证明必要信息、合法候选、剩余义务或证据状态有进展？ |
| Stop Condition | 何时满足当前责任，何时需要等待，何时不可修复、无进展或预算耗尽？ |
| Failure Classification | 是可恢复模型偏差、系统能力缺陷、治理阻断，还是原因仍 UNKNOWN？ |
| Recovery Strategy | 在同一合法 basis、身份与剩余预算内，由哪个 Owner 选择修复、再生、允许重试、取证、等待或终止？ |

禁止主要依靠无限 retry、增加 Token、增加 Prompt 或增加规则获得收敛。

复用现有 Owner-specific Self-Refine / Self-Converge、Feedback、Repair 和合法再生。失败候选、反馈和恢复必须保持原来源、版本、Attempt、收据与预算连续性。不能重置预算、重复未知效果、删除难以履行的要求或修改已接纳事实。

局部修复成功不等于 Work 完成；耗尽预算也不能自动证明 Human 必须修改产品目标。无合法修复依据时应保留不确定性并如实停止。

## 4. Maturity Level

| 等级 | 名称 | 特征与边界 |
| --- | --- | --- |
| Level 0 | Deterministic Wrapper | 传统模块加 LLM 调用，仍假设输入固定、输出确定，失败主要靠重试。调用模型本身不提升等级 |
| Level 1 | AI Assisted | 有部分 AI 输入适配、基础验证与错误处理，但缺少适用的不确定性状态建模及收敛机制 |
| Level 2 | AI Native Boundary Aware | 具备 Reality Boundary、Evidence 管理、UNKNOWN 和基础收敛能力；不表示全部合法变化都已获得可靠资格 |
| Level 3 | AI Native Autonomous Module | 在明确责任及适用范围内具备完整 Semantic Adaptation、Reality Boundary、Uncertainty Handling、Convergence Control；能自主判断信息充分性、继续或停止，在不确定条件下保持可靠 |

成熟度判断应引用实际契约、代码和资格证据。单次 Case、Schema、测试或模型生成成功不能证明整个模块达到 Level 3。自主决策始终受既有 authority、预算、证据与 Human Gate 约束，不代表自主获得 Integration、Acceptance 或 Delivery 权限。

## 5. AI Native Anti Patterns

| 反模式 | 问题 | 标准要求 |
| --- | --- | --- |
| Prompt Patch | 不断增加提示词掩盖系统性消费、表示或恢复缺口 | 禁止作为主要解决方案；应定位模块责任与真实缺口 |
| Rule Accumulation | 用不断增长的 if/else、关键词、Alias 或特例覆盖智能行为变化 | 禁止替代模块自身语义适应和收敛能力 |
| False Determinism | 把概率性输出包装为确定 Reality，例如模型猜测直接成为 Fact | 候选必须经过合法验证、接纳与证据边界 |
| Retry Intelligence | 认为多执行几次就获得智能能力 | Retry 只是有条件、有边界的机制，不是智能，也不制造权限或证据 |
| Validation Illusion | 将测试通过、格式正确或 Schema 合法等同于目标完成 | 必须区分结构、语义、履约、独立 Assurance 和真实 Human 决策 |

本节不禁止必要的协议、身份、权限及证据验证规则，也不禁止有依据的提示改进或既有预算内重试。禁止的是以这些机制替代模块能力或制造表面 PASS。

## 6. Module Evaluation Standard

未来所有 Watt 核心模块评估必须回答：

1. 当前模块接受什么形式的不确定输入？
2. 当前模块如何管理语义变化？
3. 当前模块如何保护 Reality Boundary？
4. 当前模块如何表达 UNKNOWN？
5. 当前模块如何决定继续探索或停止？
6. 当前模块失败后如何分类，而不是简单重试？

答案必须绑定实际 Owner、版本、适用范围与可核对证据，分别标识已实现、已资格、未验证及 UNKNOWN。不存在的能力不能用设计意图冒充，设计标准发布也不能自动使既有实现合格。

后续设计、维护和资格继续使用 §13/§14 及[既有 Golden Journey 治理](watt-regression-protection-and-golden-journey-governance.md)。允许合法不同表达和方案，保留真实端到端与必要负向证据；不新增运行时 Compliance Engine。

## 7. Initial Priority

以下为 Human 批准的 AI Native Evolution 初始优先级：

| 优先级 | 模块 |
| --- | --- |
| P0 | Formation；Self-Refine Convergence |
| P1 | Trace Analysis；Verification；WIC；Planning；ECF；Guardian |
| P2 | Executor；UI/Interaction Layer |

这是演进工作的排序，不表示每个列出的模块都已证明存在缺陷，也不豁免更低优先级模块的真实治理阻断。当前 C3 的原 Closure Contract、状态及历史资格保持不变；Trace 和长期演进事项不自动成为 C3 的新增前置条件。本标准不授权任何模块实现、模型调用、Holdout 执行或部署。

## 8. Constraints 与职责分工

AI Native Evolution 不意味着放弃工程约束、放宽 Guardian、减少验证或让 AI 自由修改现实。

| AI 提供 | 系统提供 |
| --- | --- |
| 推理 | 事实 |
| 候选 | 边界 |
| 创造 | 权限 |
| 合法表达与方案探索 | 证据 |
| 有依据的候选修复 | 收敛治理 |

系统提供事实是指从合法 Owner 接纳和保护真实事实，不是创造缺失的 Reality。模型可以提出方法、表达与候选；权限、事实接纳、Evidence Integrity、Verification、Guardian 和 Human Authority 继续由现有职责控制。

不建立万能 AI Adapter、全局 Refine Coordinator 或第二套治理系统；不以 Holdout 特例、放宽门禁或补造 Evidence 达标。

## 9. 本次落库边界

本阶段仅新增本标准文档。没有修改代码、测试、数据库、Runtime、预算或部署环境，没有新增资格结果，也没有改变 C3 状态。**C3 仍为 PARTIAL。**

后续模块是否符合 v1.0，必须通过其实际 Repository Reality 与适用资格判断；本标准不宣布当前 Watt 已整体达到 AI Native Level 3。
