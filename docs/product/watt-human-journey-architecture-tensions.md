# Watt 用户旅程架构张力登记表

## 1. 状态与用途

```text
登记表
    HUMAN_JOURNEY_ARCHITECTURE_TENSIONS

状态
    已发现 / 本任务不解决

实现授权
    无
```

本登记表对比首发版目标用户体验与当前代码库 Reality。“原型可模拟”表示后续隔离原型可以表达该目标，用于验证它是否易于理解；并不表示该能力已经存在，也不表示原型可以成为事实来源。

变更类型是供后续规划使用的初步判断：

- **API：** 命令/查询契约变化或新的聚合端点。
- **投影：** 新的读模型，或对已有事实进行组合。
- **领域：** 需要审查所有者语义或生命周期行为。
- **数据：** 持久化结构或持久事实变化。
- **ADR：** 实现前需要架构决策。

## 2. 登记表

| ID | 目标用户体验 | 当前代码库 Reality | 不匹配之处 | 原型可安全模拟？ | 后续可能需要的工作 |
|---|---|---|---|---|---|
| T01 | 首页从 Motive 和有价值的对话开始 | `/app` 打开以 Work/Goal 为中心的外壳和已选 Work 界面 | 用户尚无 Work 时，产品已先按既有实体组织体验 | 可以，需标记为目标体验 | 投影、UI，可能需要聚合 API |
| T02 | 回访首页说明发生了什么、哪些 Work 活跃、什么需要处理 | Work 列表、Attention、Queue、事件和 Delivery 分散在不同投影/路由 | 缺少按后果排序的统一回访摘要和访问 cursor | 可以 | API、投影，可能需要保存 last-seen 依据 |
| T03 | Work Formation Review 在准入前展示目标、范围、约束、结果、制品和生产边界 | WIC 已有 interpretation/readiness；更广义的 `PRE_AUTHORIZATION_WORK_PREVIEW_REQUIRED` 仍未解决 | 用户会在没有完整可见治理方案时授权一个解释 | 可以，但必须显著标记为规划能力 | 投影、API，可能需要数据；对精确方案身份/过期规则作 ADR |
| T04 | 一个平静的 Work 上下文随形成、设计、生产、审阅和完成自适应变化 | 当前 UI 同时呈现大量 Control Room 和工程面板 | 事实正确，但实时界面的信息优先级和渐进披露不够随状态变化 | 可以 | UI、投影 |
| T05 | 使用用户语言命名有意义的阶段 | Runtime 保存 PWU、Attempt、Queue、Step 和执行状态；UI 暴露部分原始状态 | 缺少贯穿 Plan 与执行的稳定用户阶段命名/进度投影 | 可以 | 投影，可能增加 API 展示元数据 |
| T06 | Queue 是跨 Work 的一等产品视图 | 已有持久 Queue API 和选中 Work 的队列控制 | Queue 嵌在 Work 详情；对全局竞争和等待原因的通俗说明有限 | 可以 | API/投影、UI |
| T07 | “需要我”是一个能深链到准确上下文的投影 | 已有 `/api/attention`，当前 UI 也有 Attention 面板 | 形成、资产、队列、结果审阅和恢复中的 Attention 尚未形成统一导航契约 | 可以 | 投影、API；仅在扩展语义时需要 ADR |
| T08 | 用户在精确授权前预览结果，看到行为、变化、检查、限制和风险 | Candidate/Vector 与 Verification 基础已存在；当前 Delivery UI 主要展示交付后制品/Runtime；blueprint 定义了 preview 方向 | 通用、适配不同交付形态的授权前 preview adapter 和统一审阅投影尚不完整 | 可以，使用确定性 mock preview | API、投影、Preview Record 数据、Adapter 实现；对不支持形态作 ADR |
| T09 | 一个用户动作授权易于理解的精确结果和目标集合 | 已有精确身份的标量 Candidate 和 native CandidateVector 授权路径 | 需要把内部 Candidate/Vector 术语翻译给用户，同时不削弱精确性 | 可以 | 投影/UI、API DTO 适配 |
| T10 | 多代码库结果以一个连贯成果呈现，并显示逐目标收敛情况 | 已有 native vector 和多目标收敛模型，部分路由受能力开关限制 | 产品级聚合 preview、authorization 与部分收敛呈现尚不完整 | 可以 | API、投影、UI、针对性能力补齐 |
| T11 | Work 下的 Asset 包括代码库、文档、设计、运行目标、外部系统和生成制品 | 当前已实现的资产接入以代码库为中心；已支持托管工作区 | 用户层面的通用 Asset 模型比当前持久资产类型和能力观察更宽 | 可以，但不支持类型必须标为模拟 | 领域、数据、API、投影；资产分类需要 ADR |
| T12 | 没有代码库的 Work 也能自然推进，仅在需要时获得托管工作区 | 架构和当前实现支持无代码库准入及托管工作区分配 | 当前 UI 仍高度突出代码库/Engineering Resource 概念 | 可以 | UI、投影 |
| T13 | Delivery 历史统一运行环境、代码库、下载、信任和后续细化 | `/delivery` 是独立页面，包含 manifest、Runtime 状态、下载和 Work 选择器 | Delivery 与主 Work 叙事及回访首页割裂 | 可以 | 投影/UI，可能需要聚合 API |
| T14 | 无需术语也能区分“已生成、已验证、已授权、已集成、已交付、用户满意” | 这些事实分别由 SPG、Verification、Governance、Runtime Commit、Delivery 和 Acceptance 建模 | 缺少跨所有者的精短信任叙事；原始状态可能泄漏 | 可以 | 投影/API 组合，不能合并领域事实 |
| T15 | 可从 Delivery 重新进入已完成 Work，并保留历史 | Work Interaction 支持 `CURRENTLY_SATISFIED + OPEN` 和 re-entry；应用逻辑会记录 satisfaction reopened | 导航和“从交付继续细化”的动作尚未形成连贯主旅程 | 可以 | UI/投影，可能增加 API 链接元数据 |
| T16 | 话题变化保留当前 Work，并提供清晰的新 Motive 路径 | WIC 已有 focus/relationship classification 和 transition decision | 当前技术分类及 candidate-change 字段会暴露实现语言 | 可以 | UI/投影、对话文案 |
| T17 | 浏览器断连和慢客户端绝不会看起来像取消或重复工作 | 已有事件流、cursor、有界 buffer、draft/outbox 与持久 Runtime 语义 | reconnect、offline、pending message 和“仍在其他位置运行”的状态需要统一体验契约 | 可以 | UI、投影/API 错误语义、聚焦测试 |
| T18 | 恢复状态明确告诉用户：Watt 正在恢复、只需知悉，还是必须行动 | 已有 Recovery classification/barrier、checkpoint、Queue mode 与 Attention 事实 | 技术条件尚未一致转译成三种用户契约 | 可以 | 投影/API 组合、UI 术语 |
| T19 | 过期 Plan/Result 决策会安全刷新并解释变化 | 精确 revision 与 optimistic/concurrency check 会保护命令 | UI 多数只显示错误/刷新，而不是对比依据发生了什么变化 | 可以 | API conflict payload、投影、UI |
| T20 | 部分集成会展示安全向前完成和精确重新授权需求 | 多目标 Integration Effect 和 Recovery 语义已定义/部分实现 | 缺少通俗投影解释 old/new ref、已推进目标和剩余授权 | 可以 | 投影/API、能力补齐；策略未决时做 ADR |
| T21 | 用户无需操作 Provider，也能理解容量和商业限制 | Runtime 保存 Resource Reservation/Usage 和 Queue Capacity；WIC/Executor profile 可配置 | 尚无确定的首发版商业用量投影，Provider 详情又过于底层 | 只模拟通用限制，不模拟计费事实 | 产品决策、API/投影，可能需要数据 |
| T22 | 普通故障不会把用户变成调试中转站 | Recovery 语义稳固，并在安全范围内自主处理 | 部分错误和状态仍是工程代码，升级文案与选项不一致 | 可以 | 投影/UI、错误分类映射 |
| T23 | Work 列表是主要组织方式，Goal 只是可选元数据 | 当前侧栏以 Goal 和状态筛选开头 | Goal-first 层级可能暗示必须存在类似 Project 的容器 | 可以 | IA/UI，不增加领域实体 |
| T24 | 产品身份和语言统一使用 Watt | Runtime UI 标题仍有 `TNGA Software Production`，中英文与内部标签混用 | 当前外壳尚未形成统一产品声音和术语体系 | 可以；最终视觉品牌仍不在范围内 | 内容设计/UI，后续品牌决策 |
| T25 | 按场景记录原型审阅状态，但不改变产品数据 | 不存在场景验收产品模型，也没有必要创建 | 评审连续性需要生产事实之外的轻量 ledger | 可以，只使用文档 ledger | 文档/流程，不增加产品 Schema |
| T26 | 原型模拟状态覆盖全旅程，但不与领域状态机竞争 | Reality 分散在 WIC、Work、Guided Design、Steering、Queue、Executor、Verification、Candidate、Commit、Delivery 和 Satisfaction | 单一 mock enum 可能让人误以为存在一个权威生命周期 | 仅当它作为映射到事实的场景 cursor 时可以 | 原型架构规则，不改领域/数据 |
| T27 | 未来 Guardian/ECF 可以增加保障/能力，但不阻塞首发版 | 两者均明确属于未来且保持独立 | 原型可能误导用户认为其判断或市场已经存在 | 只排除相关声称，并标为未来延后项 | 首发版无需工作，未来另做 ADR |
| T28 | 当前架构文档准确表达已实现状态 | 部分早期产品/架构文档保留“已设计/未实现”等时间点标签，或保留过期 WIC 状态，而后续证据和代码已推进 | 读者可能把历史范围标题误认为当前总体 Reality | 原型可引用当前证据；不能静默改写历史 | 文档 SOT 索引/时效策略，可能需要状态汇总 ADR |

## 3. 正式实现前必须解决的张力

下列张力直接影响体验，必须成为原型验收与生产实现之间的明确 Gate：

1. T03：Work Formation Review 的精确身份与权限语义；
2. T07：不创建第二套交互系统的统一 Attention 投影；
3. T08–T10：适配不同形态的结果预览与精确授权，包括多目标；
4. T11：当前代码库资产与通用 Asset 模型之间的边界；
5. T14：保持各类事实独立的跨所有者信任投影；
6. T19–T20：过期决策和部分收敛的用户契约；
7. T26：不能被误认为领域生命周期的原型状态映射。

原型应主动暴露这些张力。如果 Human 审阅不接受目标心智模型，就校准原型；如果 Human 接受体验，但代码库 Reality 无法在不改变所有权的情况下支持它，则先做架构审查再实现。生产实现不能机械复制被 Reality 证伪的原型假设。
