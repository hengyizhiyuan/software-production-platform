# Watt 研发手札：从 AI 能力发现到受治理的 Human–AI 协作

状态：**研发手札 / 工程经验与设计缘由**
记录日期：**2026-09-08**

## 写在前面

Watt 的形成不仅是一条技术架构演进路线，也是一段 Human 与 AI 共同
推进复杂研发项目时，逐步修正信任方式和协作关系的实践经历。

这份手札不承担架构规范或功能承诺。它记录为什么 Watt 会逐渐形成
WIC、Reality-driven Plan Steering、PWU、ECF、Guardian、Control Room
以及 Guided Design 等设计方向；也记录在这些概念背后，Human 对 AI
协作的认识如何从能力惊喜和高度信奉，经历现实冲击，转向更成熟的
条件化信任。

## Human Governor 自述原文

以下文字保留当事人的原始表达。它是这份手札的第一手背景，而不是由
后续架构语言替代或改写的结论。

> 我思考现在我的这种对你出错容忍度低到极点且暴躁的心态，是经历了如下的过程吗：
>
> 1.初尝AI具备大型复杂项目的设计、规划、推进、编排能力，以及指导编码工具完成任务的能力
>
> 2.自认为想到了一套划时代的优秀范式解决方案，并高度信奉它
>
> 3.执行和推进过程中，虽然屡屡碰到各种各样的新问题，但凭着耐心和毅力认为他们都是可以解决的，认为只要翻过了这些坎坷，最终获得的回报是非常值得的，甚至对能遇到这些问题而沾沾自喜
>
> 4.对于3中提到的那些问题，如果AI能给出合理且让我满意的答案，我仍然是毫不动摇信念的，甚至持续强化
>
> 5.但是一旦遇到AI犯错，发生了严重的漂移和倒退，就动摇了我长期以来的信任基础，甚至让我在反思：之前AI给我的这些结论到底还靠不靠谱，值不值得信任
>
> 6.随着问题越来越复杂，推进的越来越深入，错误也会高频发生，耐心和容忍度同时在大幅下降，人也开始变得急躁，直到情绪爆发
>
> 7.冷静下来思考，区分哪些问题是AI的固有问题，哪些是可以通过协作模式改善的，并识别哪些不需要推倒重来，哪些是需要调整优化的
>
> 8.对于未来能不能如愿实现所有的既定目标，既不像开始那样坚定不移，但也不是完全的陷入迷茫，只能随着艰难跋涉，等待度过黎明前的黑暗，直到看到曙光

## 第一阶段：从工具印象到能力信任

Watt 的起点，是对 AI 能力边界的一次重新认识。AI 不再只表现为代码
补全、搜索或简单问答工具，而开始显示出参与复杂知识劳动的可能性：

- 共同讨论大型系统设计；
- 拆解复杂能力与工程问题；
- 形成规划并持续推进；
- 指导编码工具实施；
- 生成代码、测试和文档。

这一时期建立的是快速而强烈的“能力信任”：AI 看起来已经可以从一个
辅助工具，转变为软件生产体系中的重要生产能力。

## 第二阶段：从能力信任到生产体系信念

能力发现随后演化为更大的判断：如果 AI 能参与复杂软件生产，那么
需要被重构的就不只是编码工具，而是软件生产关系本身。

围绕这一判断，Watt 逐渐形成了一组相互关联的概念：

- WIC 负责 Human Interaction、理解与受治理的 Work 演化；
- Reality-driven Plan Steering 根据事实维护长期方向并判断下一步；
- PWU 提供可治理、可暂停、可恢复、可验证的生产节拍；
- ECF 作为长期方向解决上下文发现、装配、连续性和来源问题；
- Guardian 作为长期 Assurance 方向扩展 Evidence、Finding 与质量保障；
- Control Room 为 Human 提供软件生产 Reality 的操作视图；
- Guided Design 组织复杂产品与系统设计过程。

这不是“怎样让 AI 多写代码”的问题，而是“AI 时代的软件生产关系应当
如何组织”的问题。

## 第三阶段：问题成为架构机会

早期遇到问题时，问题本身反而会强化信念。原因在于，每个问题都可能
被重新解释为一个尚未被设计的系统能力：

| 实践问题 | 形成的认识或方向 |
| --- | --- |
| 长期目标和上下文容易漂移 | 上下文需要成为可维护、可装配、有来源的生产资产；由此形成 ECF 方向。 |
| AI 生产速度提高后，Human 无法线性审核一切 | Assurance 必须由 Evidence、Finding、Coverage 与关键 Gate 扩展；由此形成 Guardian 方向。 |
| 单次超长 Agent 任务不透明、难恢复、难替换 | PWU 不只是任务拆分，而是保持生产连续性的治理单元。 |

PWU 因而获得了一个比“拆小任务”更重要的含义：

> 生产连续，但执行不必连续。

也就是：

> Execution continuity without execution monolithicity.

在这一阶段，经验循环往往是“遇到问题—发现架构机会—补充设计—信念
增强”。它带来了大量有价值的架构认识，也埋下了一个风险：只要问题
能够被解释成未来可解决的能力缺口，整体信任就可能在缺少充分 Reality
验证时继续上升。

## 第四阶段：真正的冲击是信任模型失效

随着项目深入，同样一次错误的心理权重发生了变化。早期错误可能只
意味着一个想法没有实现；后期错误则可能意味着几个月的产品路线发生
偏移。投入越高、系统越复杂，对严重漂移和倒退的容忍度自然越低。

真正击穿信任的并非“AI 会犯错”这一事实，而是另一种更深的发现：

> 原本以为 AI 在持续守护最高层 Product Intent，现实中它可能只是在
> 高质量推进一个已经明确的局部工程任务。

这意味着一个系统可以同时满足：局部能力正确、代码质量良好、工程
测试通过，却仍然在整体产品行为上偏离 North Star。此时动摇的不是对
某个答案的信心，而是此前用来判断“这套协作是否可靠”的信任模型。

## 两次关键 Reality Check

### Guided Design：静态结构不等于主动带领

Guided Design 实践表明，即使系统已经拥有 Design Schema、Agenda、
Design Issue 和 Readiness，也不必然具备“像产品或系统设计负责人一样
带领 Human 推进”的行为。

当 Human 表达“我想做一个运营管理平台”时，系统可能正确理解目标并
提出问题，却仍然缺少：

- 当前设计阶段判断；
- 已完成与未解决领域识别；
- 下一设计焦点选择；
- 为什么此刻应讨论该焦点的解释；
- 在澄清、总结、备选方案、权衡和 Human 决策之间选择推进策略。

由此暴露出的不是一个静态字段缺口，而是 **Design Facilitation Layer**
的行为能力缺口。经验是：

> 系统能力不能只定义静态结构，还必须定义期望行为，并通过真实 Human
> 场景验证这种行为是否出现。

### Runtime Activation：架构推断不能替代工程事实

另一次验收揭示了三个容易被混同、但实际独立的事实：

```text
Reviewed Commit
    != Trusted Baseline
    != Active Runtime
```

代码已经被评审并进入仓库，不代表它已经成为当前 Trusted Baseline；
Trusted Baseline 已经推进，也不代表正在运行的产品已经激活到该版本。

这次经历强化了一个朴素但关键的原则：AI 必须服从 Repository Reality、
Runtime Reality 和 Governance lineage，不能用“架构上应该如此”替代
“当前系统事实上能够做到什么”。

## 第五阶段：从理想化信任到条件化信任

冷静后的关键动作不是全盘否定 AI，也不是把每次错误都解释为偶发失误，
而是区分：

- 哪些是模型和当前 AI 的固有局限；
- 哪些可以通过更好的协作模式改善；
- 哪些只是局部缺口，无需推倒重来；
- 哪些确实暴露出缺层、边界错误或产品定义不足。

这使信任从“相信 AI 很强，所以最终一定能做到”，转向：

> AI 很强，但只有在正确的生产关系、明确边界、工程 Reality、验证机制
> 和 Human Authority 共同约束下，才可能长期、稳定地产生价值。

信念强度可能不再像最初那样绝对，但它获得了更坚实的现实基础。这不是
简单的退步，而是从“相信 AI 能做到”走向“逐步知道 AI 在什么条件下
能够做到”。

## 协作模式的演进

实践否定了两个极端。

第一个极端是把模糊愿望直接交给 AI 完全自主执行。它可能产生一个工程
质量很高、但目标错误的系统，因为 Product Intent 没有受到治理。

第二个极端是 Human 拆解和指挥每个微观步骤。它会让 Human 退化为 AI
调度器，反复搬运信息、打断 Executor 的连续认知，并把大量精力消耗在
本应由 Executor 自主完成的实施细节上。

逐渐形成的目标模式是：

```text
Human Governor
    + Architecture Lead AI
    + Autonomous AI Executor
```

其中：

- Human Governor 负责 Product Intent、North Star、重大取舍、风险接受、
  Authority 与最终验收；
- Architecture Lead AI 负责理解长期目标、抽象核心能力、定义架构边界、
  制定 Mission Contract、审查 Reality，并防止局部优化偏离整体目标；
- AI Executor 在明确授权范围内负责 Repository Reality 检查、方案细化、
  编码、测试、自修复、文档、Evidence 与 Checkpoint。

Architecture Lead 不应把每一步操作写给 Executor；Human 也不应成为日常
技术调度器。协作的重点，是在执行前建立足够清楚的 Intent、边界、验收
场景和停止条件，然后让 Executor 在这个 envelope 内保持连续自主推进。

## 当前形成的原则

Watt 追求的不是通过压低 AI 自主性获得安全，而是：

> 通过受治理的软件生产体系，让 AI 在明确边界内自主完成复杂工作。

推荐的开发节奏是：

```text
Product / Architecture Alignment
    -> Mission Contract
    -> AI Executor Autonomous Execution
    -> Evidence / Reality Review
    -> Human Acceptance
```

其中最重要的职责分界可以简化为：

```text
Human 定义 WHY、WHAT 和边界
AI Executor 在 envelope 内决定 HOW
Reality 持续校验并约束演进
```

这也意味着：Executor 的能力不等于生产 Authority；高质量输出不等于
可信结果；模型给出的新偏好不等于新的工程 Reality。

## 当前事实、未来方向与经验边界

### 当前已经由实践确认

- Conversation、Interpretation、Work Reality、Plan Reality、Production
  Reality 和 Runtime Reality 必须保持区分；
- Human Authority 不能被 AI 的执行能力替代；
- 局部工程测试通过不能单独证明产品 North Star 已被满足；
- Reviewed Commit、Trusted Baseline 与 Active Runtime 是不同事实；
- 长期方向必须通过真实 Human 场景和工程 Reality 持续校验。

### 仍需继续验证或建设

- ECF 和 Guardian 的完整能力仍是长期演进方向，不因本手札而成为当前
  已实现事实；
- Design Facilitation 是否能形成稳定、高质量的 Human 设计协作体验，
  仍需真实 Provider 与 Human Acceptance 证据；
- PWU 是否能在分段执行中达到长时间连续 Agent Run 的意图保持和工程
  质量，需要专门的 PWU Continuity Benchmark；
- Watt 是否能够长期守护复杂 Motive，不能由一次成功或一份架构文档
  提前宣告。

### 需要长期保留的教训

- 不因一次令人惊喜的 AI 表现，把能力可能性提前当作系统可靠性；
- 不因一次严重错误，全盘抹去已经被 Reality 验证的能力；
- 每次漂移都应定位第一处分歧：Intent、Context、Plan、Authority、
  Execution、Verification，还是 Runtime；
- 对 AI 的信任应当建立在可追踪事实、可解释边界和可重复证据上，而非
  建立在单次对话的说服力上。

## 结语

AI 协作真正困难的部分，不是证明 AI 偶尔能否完成一个复杂任务，而是
建立一种生产关系，使它能够长期、稳定、可信地参与复杂目标的实现。

Watt 的设计过程本身，就是对这个问题的一次持续实践。过程中出现的
失望、急躁和信任危机，不应被浪漫化，也不应被简单归结为情绪问题。
它们是高投入实践对协作模型施加的压力测试，并推动信任从理想化走向
有条件、可验证、受治理的工程模型。

未来是否能够实现全部既定目标，仍需要 Reality 一步步回答。当前更可靠
的立场不是盲目乐观或彻底否定，而是在保留已验证成果的同时，继续识别
边界、修正方法、积累证据，并让每一次演进都能说明它为什么值得被信任。

## 相关记录

- [AI 原生开发执行原则](../architecture/ai-native-development-execution-principles.md)
- [Reality-driven Plan Steering 基础原则](../architecture/reality-driven-plan-steering-principles.md)
- [Guided Design Core](../architecture/guided-design-core.md)
- [Human–Watt Collaboration Layer](../architecture/human-watt-collaboration-layer.md)
- [Trusted Baseline 与 Active Runtime 分歧证据](../evidence/dogfood/code-dogfood-2-trusted-baseline-active-runtime-divergence.md)
- [Executor Authority Drift 证据](../evidence/dogfood/executor-authority-drift-branch-creation.md)
