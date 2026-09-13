# Watt 可点击原型范围、验收与实施计划

## 1. 状态与目标

```text
原型定义
    高保真体验模拟

规划状态
    已就绪 / 待 Human 审阅

原型实现
    未开始 / 本文档不授权

生产实现
    未开始 / 本文档不授权
```

后续原型用于回答：贯穿整个首发版旅程时，真实用户使用 Watt 应该是什么感受。它是体验校准工具，不是生产客户端、后端模拟器、领域模型、技术资格环境或第二个事实来源。

原型实现 [Watt 首发版用户旅程与信息架构](watt-first-release-human-journey.md)描述的目标旅程，使用[场景清单](watt-first-release-scenario-inventory.md)作为覆盖依据，并通过[架构张力登记表](watt-human-journey-architecture-tensions.md)持续暴露所有已知不匹配。

## 2. 原型边界

### 2.1 技术方案

原型放置在：

```text
prototype/human-journey/
```

采用一个小型 Vite + React + TypeScript 应用，拥有隔离的 package 和 lock 文件。选择 React 是因为评审需要一个持续存在的产品外壳、多条有状态路径、可重置 fixture、随条件变化的上下文面板，以及快速的场景级迭代。当前生产前端使用原生静态 HTML/JavaScript，导入与 Runtime 耦合的模块并不能节省多少工作，反而会模糊隔离边界。必要时可以有意识地复制视觉 token，但不能导入生产模块、API Client 或 Store。

原型包含：

- 适配桌面和窄屏的首页、Work、队列、交付应用外壳；
- 保存在类型化本地文件中的确定性场景 fixture；
- 纯内存场景 reducer；
- 只能前往预先声明 fixture 状态的可点击动作；
- 用于选择场景包、切换场景、重置和记录意见的评审抽屉；
- 真实感较强的文本、预览、资产、证据摘要和时间线；
- 始终可见的“Watt 体验原型 — 模拟数据”标记；
- 可选的 pack/scene URL fragment，便于分享评审位置且无需持久化。

默认构建不提供生产 base URL，也不实现通用网络 Client。开发期 Guard 应在代码尝试 `fetch`、WebSocket、EventSource 或向同文档静态资源以外提交表单时立即报错。所有转换只操作打包的 mock 数据。启动、暂停、授权、交付或重置场景都绝不能调用生产 API、修改数据库、消耗 Provider 额度或触发 Executor 生产。

原型只需一个有文档说明的本地命令即可运行；正式实现完成后可直接删除整个目录。它不应依赖 Docker、PostgreSQL、凭据或 Watt Runtime。

### 2.2 范围内

原型模拟：

- 新用户首页与回访首页；
- 从模糊 Motive、纠正到 readiness 的对话；
- 完整的 Work Formation Review 与明确准入选择；
- Work 在设计、规划、排队、执行、恢复、验证、结果审阅、交付、完成与重新进入各阶段的上下文；
- 零资产、单资产和多资产 Work，包括代码库能力状态；
- 多个 Work 的全局 Queue；
- 能深链到 Work 上下文的“需要我”投影；
- 有意义的阶段，不使用虚假完成百分比；
- pending conversation message 和浏览器重连状态；
- 授权前软件/结果预览、变更、检查、限制与精确 Human authorization 文案；
- 交付历史和后续细化周期；
- 自动恢复、只需知悉、必须行动三种恢复体验；
- 桌面与窄屏交互布局；
- 不强迫用户阅读的工程详情渐进披露。

### 2.3 范围外

原型不模拟真实模型、动态自然语言质量、生产延迟、Token 流式性能、真实代码库、Git 操作、Provider 计费、真实队列调度、真实 Preview、Build/Test 执行、Runtime Commit 影响、交付打包、身份认证、多人协作、企业 IAM、Guardian、ECF、分布式调度、最终品牌或最终视觉 token。

Conversation 分支使用人工编写的确定性回复。评审者只判断内容结构、连续性、语气方向与动作位置，不能用原型评价真实 WIC 智能或 Provider 性能。

## 3. 模拟架构

### 3.1 场景包、场景与投影

每个场景包包含不可变起始 fixture 和有序场景图。每个场景声明：

```text
场景身份
用户可见状态
各真实所有者投射出的事实
界面重点
可用的用户动作
自动转换选项
预期后续场景
验收重点
关联场景 ID 与架构张力
```

Reducer 只保存当前场景包、当前场景、本地输入草稿、已展开详情和评审意见。发生转换时，当前 mock fact bundle 会被声明的下一个 bundle 替换。Reducer 不推导生产事实，也不实现恢复策略。

自动推进仍然是确定性的：评审者点击“推进模拟”，或启用可选的短时脚本 timer。Timer 只影响呈现并可暂停。Reset 会把场景包恢复到完全一致的 seed。

### 3.2 模拟状态映射

以下标签只用于方便评审，并非领域生命周期状态。每个界面都必须由第三列列出的 mock source facts 驱动，组件不能只根据便利标签进行分支。

| 原型概念 | 用户含义 | Fixture 所代表的现有 Reality | 绝不能暗示 |
|---|---|---|---|
| `PRE_WORK` | 存在 Motive 或问题，但尚无 Work | Interaction/WIC 记录；没有已准入 Work | 已有 Draft Work 或生产权限 |
| `REFINING` | 用户和 Watt 正在澄清含义 | Interpretation revision、Shared Understanding、未决问题 | 对话文本就是受治理事实 |
| `READY_FOR_WORK` | 可以审阅一个精确形成方案 | WIC readiness 与拟议形成投影 | Readiness 等同准入授权 |
| `DESIGNING` | 已准入 Work 正在解决产品/设计问题 | Work revision、Guided Design agenda/issue/readiness | 新的设计所有者或生命周期 |
| `PLANNING` | Watt 正决定有意义的后续结果 | Steering plan/revision/current step 与 Reality basis | Executor 决定 WHAT NEXT |
| `QUEUED` | 一个可运行阶段正在等待执行机会 | PWU contract 与 Queue `QUEUED` | 新的任务身份 |
| `WAITING_FOR_CAPACITY` | 当前没有兼容容量 | Queue/Execution mode `WAITING_RESOURCE`、资源/容量事实 | 执行失败或精确 ETA |
| `RUNNING` | Watt 正在进行生产 | Queue `ALLOCATED/EXECUTING`、Attempt/Step 事实 | 把原始 Execution Slice 当成产品对象 |
| `CHECKPOINTED` | 有用工作已持久保存 | 已提交 checkpoint、Queue `CHECKPOINTED` 或 returned-to-queue frontier | 结果已经完成或验证 |
| `PAUSED` | 受治理工作已安全暂停 | control request 与 Execution mode `PAUSE_REQUESTED/PAUSING/PAUSED` | 进程已瞬间终止，或观察前所有影响均已确定 |
| `RECOVERING` | Watt 正恢复一个一致、安全的前沿 | Execution mode `RECONCILING`、Recovery Case/Barrier、observation | 自动重放未知影响 |
| `WAITING_FOR_HUMAN` | 某个明确用户决策阻塞当前路径 | Queue `WAITING_HUMAN`、Attention、authority requirement | 与 Work 脱节的错误收件箱 |
| `VERIFYING` | 独立检查正在评估精确输出 | result-ready claim、进行中的 Completion/Verification | Executor 自我报告等于信任 |
| `RESULT_READY` | 结果已存在，正在准备审阅 | 不可变 output/result claim、已观察 artifact/evidence | 已可信、已授权、已交付或已验收 |
| `READY_FOR_AUTHORIZATION` | 精确预览和必要保障已可审阅 | Candidate/aggregate manifest、verification/admissibility、preview | 用户已经批准 |
| `AUTHORIZED` | 用户授权了一个精确结果与目标集合 | 精确 Candidate authorization | 授权覆盖修订结果或变化后的目标 |
| `DELIVERED` | 约定的可用形态已经提供 | integration effect、Runtime Commit、Trusted Baseline、Delivery manifest/runtime status | 活跃 Runtime 必然一致，或用户已经验收 |
| `COMPLETED` | 用户认为当前 Work 已令人满意 | Human acceptance 与 Work satisfaction projection | Conversation 或 Work 历史永久关闭 |
| `REOPENED` | 同一 Work 进入新的细化周期 | 新 Interaction/Work revision 与 reopened satisfaction/design/steering facts | 无关 Motive 静默改变旧 Work |

## 4. 原型场景包

每个场景包都提供重置动作和简短的“为什么要评审此场景”说明。场景包引用清单 ID，不重复定义其验收契约。

| 场景包 | 可重放故事与关键场景 | 清单覆盖 | 主要张力 |
|---|---|---|---|
| P01 — 模糊 Motive | 新首页 → 暂定理解 → 有价值建议 → 补充背景 → 推迟或进入 Formation Review | J01、J03、J04、J07、J09、J11、J12、J16 | T01、T03、T04 |
| P02 — 清晰想法，无代码库 | 清晰软件结果 → Formation Review → 准入 → 设计 → 解释托管工作区 → 规划 | J12、J16、J17、J22、J28、J34、J35、J38 | T03、T05、T12 |
| P03 — 已有代码库 | 添加引用 → 观察能力 → Work 范围授权 → 设计/变更计划 → 代码结果预览 | J23、J25、J27、J31、J38、J66 | T09、T11、T12 |
| P04 — 多代码库 Work | 绑定两个代码库和一份文档 → 跨目标计划 → 聚合预览 → 一个目标延迟收敛 | J24、J35、J67、J71、J72 | T08、T10、T20 |
| P05 — 容量队列 | 两个 Work 就绪 → 一个运行 → 第二个无虚假 ETA 地等待 → 获得分配 → 阶段转换 | J40–J43、J57–J59 | T05、T06、T21 |
| P06 — 中断后恢复 | 运行 → 检查点 → worker 中断 → 告知正在恢复 → 重新入队 → 从前沿继续 | J44–J47、J51、J84 | T17、T18 |
| P07 — 活跃 Work 中的用户纠正 | 用户纠正业务意图 → Watt 识别重大影响 → 限制当前活动 → 修订 Work 决策 | J05、J30、J37、J49 | T07、T16、T18 |
| P08 — 重大范围治理 | 新能力扩大目标 → 清晰影响 → 暂停/继续/新 Work 选项 → 精确决策 | J14、J30、J37、J39、J53–J55 | T07、T16、T19 |
| P09 — 验证后自动修正 | 结果就绪 → 独立检查失败 → Watt 说明无需用户行动 → 受治理修正 → 新结果通过 | J61–J64 | T14、T18、T22 |
| P10 — 预览与授权 | 已验证应用 → 交互 mock preview → 变化/检查/限制 → 请求修改或精确授权 | J62、J65、J66、J68–J71 | T08、T09、T14 |
| P11 — 完成后再次细化 Work | Delivery → Human acceptance → 离开 → 回访首页摘要 → 历史交付 → 细化同一 Work | J73、J74、J79–J81、J88 | T02、T13、T15 |
| P12 — 需要用户处理 | 首页“需要我” → 精确 Work 上下文 → 资产凭据或不安全歧义 → 解决/推迟 | J25、J32、J49、J64、J86 | T07、T18、T22 |
| P13 — 对话分支安全 | 直接提问 → 多种解释 → 纠正 → 无关插曲 → 新 Motive → 返回原对话 | J02、J05、J10、J13–J15 | T01、T16 |
| P14 — 浏览器连续性 | Assistant 回复中 → 第二条消息排队 → 离开/重连 → 消息保持顺序，生产不受影响 | J60、J76、J83、J87 | T17、T19 |
| P15 — 资产丢失与过期 Reality | 已绑定代码库被外部修改 → 拒绝过期审阅 → 权限丢失 → 重新授权或使用托管替代项 | J27、J50、J86、J87 | T11、T18、T19 |
| P16 — Delivery 与 Trust 不一致 | 检查通过 → 授权 → 交付存在 → 活跃 Runtime 不一致 → 解释状态 → 后续收敛 | J62、J68、J71、J73、J74、J80 | T13、T14、T20 |

任务要求的 12 条路径全部包含在 P01–P12 中。P13–P16 用于暴露只评审孤立正常路径时容易遗漏的全局矛盾。

## 5. 原型界面与组件范围

原型应实现体验系统，而不是页面目录：

1. **外壳与定位：** 顶层导航、全局新 Motive 入口、当前 Work 身份、原型标记、评审抽屉。
2. **首页：** 新用户对话起点；回访用户的“需要我”、变化、活跃 Work、Queue 摘要和近期 Delivery。
3. **Work 上下文：** 自适应页头、Conversation、Shared Understanding、Formation Review、设计决策、方向与有意义阶段、当前生产、信任/结果、交付与重新进入。
4. **队列：** 跨 Work 顺序、容量/等待原因、当前活动和受治理的上下文控制。
5. **结果审阅：** 适配结果形态的 mock preview、变更摘要、检查、证据、限制、目标、请求修改、拒绝与精确授权。
6. **交付：** 可用动作、信任与 Runtime 状态、历史，以及返回 Work/细化的链接。
7. **Attention 投影：** 首页摘要、本地 Work 卡片、深链、决策对比、过期依据处理和已解决历史。
8. **渐进详情：** 可按需打开的 Evidence 和工程 lineage，不污染普通用户语言。

## 6. 用户原型验收

### 6.1 评审方法

用户治理者（Human Governor）每次评审一个场景包。评审从 Reset 开始，遍历所有已声明分支，并针对具体场景记录观察。评审只关注体验：

- 心智模型清晰度与术语；
- 导航和方位感；
- 交互连续性与 Conversation 的位置；
- 信息层级和不必要点击；
- 控制感与精确授权；
- 信任感，以及结果/检查/授权/交付之间的区分；
- 不使用虚假精度的进度与等待体验；
- 异常与恢复体验；
- 能否判断发生了什么、接下来会怎样；
- 工程细节泄漏；
- 桌面和窄屏可用性。

原型验收不测试 Provider 速度、WIC 智能、API 正确性、数据库持久性、Executor 恢复、Verification 完整性、安全隔离或生产性能。

### 6.2 场景验收记录

在未来原型旁保存一个简单的版本化 Markdown ledger：

```text
prototype/human-journey/acceptance/scenes.md
```

每行包含场景包、场景 ID、原型 revision、状态、Human 观察、所需校准、决定日期，以及被替代场景/revision。只使用以下状态：

- `DRAFT`
- `UNDER_HUMAN_REVIEW`
- `CALIBRATION_REQUIRED`
- `HUMAN_EXPERIENCE_ACCEPTED`

批准只适用于一个精确原型 revision 中的一个场景。后续视觉变化只有在改变已接受的交互、信息、术语、权限或信任契约时才需要重新批准。发生实质变化的场景使用新 revision，并保留历史决定。

### 6.3 场景包退出标准

当 Human 无需阅读架构说明即可做到以下事项时，场景包可以进入验收：

1. 说出当前预期结果；
2. 区分 Conversation 与受治理 Work；
3. 判断 Watt 正在做什么或为什么等待；
4. 判断是否需要用户行动；
5. 解释拟议动作将授权什么；
6. 区分已生成、已检查、已授权、已交付和已验收；
7. 走过每个分支后重新找回方位；
8. 无需阅读工程详情即可找到合理下一步。

只有满足以下条件，整体原型才能标记为 `APPROVED_HUMAN_EXPERIENCE_BASELINE`：所有 P0 场景以及保证异常/恢复连续性所需的 P1 场景均为 `HUMAN_EXPERIENCE_ACCEPTED`；四个顶层区域形成统一心智模型；每项已接受的架构假设都有现有支持或明确张力解决计划。该标记只约束体验实现，不是架构事实，也不是对生产产品的 Human acceptance。

## 7. 原型构建顺序

后续原型任务分六个可评审增量构建：

1. **定位主干：** 外壳、新/回访首页、Work 上下文框架、确定性引擎、评审 Reset、P01/P13。
2. **形成与设计：** Shared Understanding、Work Formation Review、准入时资产、设计建议/决策、P02/P03。
3. **计划、队列与进度：** 有意义阶段、全局 Queue、等待/活动、pending conversation、P05/P14。
4. **Attention 与恢复：** 深链“需要我”、三种恢复契约、检查点、范围治理、过期依据、P06/P07/P08/P12/P15。
5. **结果、信任与授权：** Preview、Verification、限制、多目标结果、精确授权、P04/P09/P10。
6. **交付与重新进入：** Delivery 历史、Runtime/Trust 不一致、满意状态、回访摘要、细化、P11/P16、响应式打磨和完整场景 ledger。

每个增量结束后进行 Human 场景评审。视觉调整可以跨场景包进行，但已接受的信息与权限契约必须继续按场景追踪。

## 8. 原型验收后的正式实施

只有相关原型场景已接受，且该阶段的架构张力已解决，生产工作才能开始。正式实现以有意义旅程块推进，而非孤立组件。

| 实施块 | 用户场景 | 所需后端/投影能力 | 可能的架构/数据工作 | 测试与保真检查 | Runtime Human Acceptance |
|---|---|---|---|---|---|
| I1. 首页与定位 | 首次使用、回访摘要、查找/切换 Work、变化摘要 | 聚合当前 Work/Attention/Queue/Delivery 投影；访问/变化依据 | 解决 T01/T02/T23；可能保存 last-seen；不引入 Project 实体 | 投影事实测试、空白/回访状态、深链、与已接受场景对比 | 开始 Motive；离开后返回；找到两个 Work 和一项变化 |
| I2. 形成与上下文资产 | 澄清/纠正、Formation Review、零/单/多资产接入 | 精确方案查询/命令契约、现有 WIC/Work Admission、资产能力投影 | 解决 T03/T11；在改 Schema 前定义方案身份与通用资产边界 | 首轮不创建 Work、过期审阅、准入/细化/拒绝、无代码库和权限测试；原型保真 | 用户审阅并准入一个无代码库 Work 和一个代码库 Work |
| I3. Guided Design 与方向 | 建议、备选方案、重大决策、阶段计划 | Guided Design 与 Steering 组合、用户阶段投影 | 解决 T05/T16；保持 WHAT NEXT 所有权 | 设计决策/计划修订不变量、约束记忆、范围变化边界、场景对比 | 用户改变业务和技术约束，并理解修订方向 |
| I4. Queue、进度与对话连续性 | 排队/容量/运行/检查点/重新入队/暂停/恢复、pending message | 跨 Work Queue 投影、持久 event cursor、受治理控制、outbox/reconnect | 解决 T06/T17/T18/T21；不引入 Execution Slice 产品实体 | 队列顺序/容量、浏览器重连、慢客户端背压、无重复 Turn/Effect、控制竞争测试；视觉保真 | 用户观察真实队列、关闭/重开浏览器、安全暂停/恢复 |
| I5. Attention 与恢复 | 决策/访问/歧义/UNKNOWN/过期/自动恢复 | 类型化 Attention 组合和精确深链、恢复摘要、conflict delta payload | 解决 T07/T18/T19/T22，不增加事实所有者 | 每种 Attention、自动/知悉/行动分类、过期决策、UNKNOWN 禁止重放、资产丢失 | 用户处理一个决策、观察一次自动恢复、解决一个过期界面 |
| I6. 结果预览与授权 | Verification、自动修正、应用/代码/多目标预览、拒绝/细化/授权 | 适配结果形态的 preview adapter、聚合结果/信任投影、精确授权命令 | 解决 T08–T10/T14/T20；仅在 ADR 后增加 preview record/data | 不可变 revision、preview 隔离、验证失败、限制可见、过期授权、多目标收敛 | 用户预览真实结果、请求修正，再授权精确修订结果 |
| I7. Delivery、满意与重新进入 | Runtime/代码库/下载交付、历史、Acceptance、后续细化 | Delivery/Runtime/Trust 组合、Delivery-to-Work 深链、现有 Acceptance/Re-entry | 解决 T13/T15；保持技术信任与用户满意分离 | Delivery manifest/Runtime 不一致、历史、请求修改、re-entry 身份、原型保真 | 用户打开交付、记录满意，稍后返回并细化同一 Work |
| I8. 集成旅程验收 | 所有已接受 P0 和必需 P1 场景包 | 前述所有实施块在一个隔离的当前源码 Runtime 中协同工作 | 关闭剩余已接受张力；更新 SOT 状态且不改写历史 | 聚焦端到端契约和相关既有回归；性能另行测量 | Human 运行 Motive→Delivery→Re-entry 及管理/恢复旅程；只有 Human 能决定验收 |

每个实施块都必须把生产行为与精确的已接受场景 revision 对比，同时验证 Runtime 事实。如果 Reality 否定原型假设，就暂停该实施块进行架构审查，校准原型，重新获得场景批准后再继续。不能强迫生产实现复制无效 mock。

## 9. 提交前内部评审

| 评审问题 | 结论 | 修订或约束 |
|---|---|---|
| 1. 旅程是否覆盖 Motive → Delivery？ | 是。18 个阶段覆盖 Work 前表达、形成、设计、队列、生产、验证、预览、权限、提交、交付、满意与重新进入。 | P01/P02/P10/P11 合起来覆盖完整主链。 |
| 2. 是否覆盖回访用户管理？ | 是。包含首页变化摘要、Work 筛选/切换、Delivery 历史、长时间离开后返回、归档方向和完成后细化。 | P11/P14/P16 检验离开后的重新定位。 |
| 3. Queue/等待/恢复是否可见？ | 是。容量、Provider/资源/用户等待、检查点、让出、重新入队、恢复、自动恢复、UNKNOWN、重启和部分收敛都是独立场景。 | P05/P06/P12/P15 在全局和 Work 上下文中暴露这些状态。 |
| 4. Human Authority 节点是否明确？ | 是。Work Admission、资产访问/绑定、重大设计/范围决策、生产方案/控制、精确结果授权、外部集成和产品满意相互分离。 | 每个相关场景把动作放在受治理依据旁。 |
| 5. 是否强迫用户学习工程内部细节？ | 目标体验不会。默认心智模型只有九个用户概念，内部细节渐进披露。 | 明确使用阶段/结果/信任转译，禁止以工程标识作为主标签。 |
| 6. 是否存在重复交互渠道？ | 没有。Conversation 是唯一表达平面；Attention 负责导航；结构化动作治理精确上下文对象。 | 不建立独立审批收件箱或第二套 Chat。 |
| 7. 异常是否被当作产品体验，而非调试输出？ | 是。所有故障都归入 Watt 自行恢复、告知无需行动、需要用户行动，并说明后果和下一步。 | 原始错误/Provider/Lease 代码留在工程详情。 |
| 8. 原型是否足以暴露全局矛盾？ | 是。16 个场景包横跨首页、Work、Queue、Attention、Preview、Delivery、Asset、Recovery 和 Re-entry。 | 额外的 P13–P16 专门验证跨领域矛盾。 |
| 9. 原型是否足够小，可以低成本迭代？ | 是。一个隔离客户端、确定性 fixture、无后端、一个 reducer、四个顶层区域且不定义最终品牌。 | 分六个增量构建，排除与体验无关的 Runtime 模拟。 |
| 10. 架构张力是否被显式揭示？ | 是。28 项张力记录当前 Reality、不匹配、安全模拟边界和可能实现变更。 | 七个体验关键张力组是正式实现前 Gate。 |

评审发现一项范围风险：把 92 个场景做成 92 个独立界面会昂贵且重复。因此，方案通过 16 个场景包复用界面和分支，同时保留场景级覆盖标签。评审还发现一项架构风险：单一模拟 enum 可能被误解为领域生命周期。因此，方案要求使用各所有者的 mock facts 驱动界面，并只把模拟状态标签当作评审 cursor。
