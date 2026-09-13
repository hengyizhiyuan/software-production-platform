# Watt 首发版场景清单

## 1. 清单用途

本清单是后续原型构建和 Human 审阅的覆盖契约。优先级含义：

- **P0：** 首发版不可缺少的旅程和原型场景。
- **P1：** 必需的支撑、分支、异常或恢复旅程。
- **P2：** 有价值但可用轻量原型表达的首发方向。
- **DEFERRED：** 明确不进入首发版原型。

“类别”表示主要测试形态，同一场景仍可参与包含其他形态的长旅程。“预期结果”描述用户应看到的结果，不定义新的领域状态转换。

本次规划清单共冻结 **92 个场景**：

| 优先级 | 数量 |
|---|---:|
| P0 | 50 |
| P1 | 35 |
| P2 | 3 |
| DEFERRED | 4 |

按主要形态统计，包括 27 条正常路径、26 条分支、10 条异常、12 条恢复和 17 条管理场景。

## 2. Work 之前与 Motive

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J01 | 模糊的初始想法 | P0 | 正常路径 | 不填表也能探索尚未成形的想法 | 新首页，没有 Work | Watt 给出有用的暂定理解和一个有价值的下一步；不创建 Work | WIC、Conversation |
| J02 | Work 前直接提问 | P0 | 分支 | 获得答案而不启动生产 | 新对话或已有 Work 前对话 | 直接回答；除非用户后来表达 Motive，否则仍是普通对话 | WIC |
| J03 | 探索性头脑风暴 | P1 | 正常路径 | 在不承诺执行的情况下拓展可能性 | Work 前对话 | 选项和判断积累为解释上下文；不催促准入 | WIC、design intent |
| J04 | 补充业务背景 | P0 | 正常路径 | 通过多轮交流改善 Watt 的理解 | 活跃的 Work 前对话 | 共同理解吸收相关信息，不重复询问已知事实 | WIC |
| J05 | 纠正 Watt | P0 | 分支 | 快速替换错误理解 | Watt 已表达一个解释 | Watt 接受纠正，后续推理采用新理解，不为旧判断辩解 | WIC、interpretation revision |
| J06 | 不同意 Watt 的建议 | P1 | 分支 | 保留意图，同时否定 Watt 的判断 | Watt 推荐了一个方向 | Watt 简要说明取舍，接受用户选择并保留该决定 | WIC、Human Authority |
| J07 | 请求 Watt 给建议 | P0 | 正常路径 | 基于已知上下文获得明确专业判断 | 对话上下文足够 | Watt 给出一个建议、依据和取舍，只追问真正重要的问题 | WIC |
| J08 | 请求更多细节 | P1 | 分支 | 深入某一部分而不重新开始探索 | Watt 已回答或提议 | 在当前上下文中展开细节，并保留已有约束 | WIC |
| J09 | 信息不足 | P1 | 异常 | 知道缺少什么以及为什么重要 | 无法作出重大决定 | Watt 说明暂定假设或只问一个高价值问题，不启动问卷 | WIC |
| J10 | 存在多种合理解释 | P0 | 分支 | 不必理解术语也能选中真实意图 | 输入实质上支持两种结果 | Watt 对比关键后果，让用户选择或澄清 | WIC、design intent |
| J11 | 用户尚未准备创建 Work | P0 | 分支 | 安全地继续思考或离开 | Watt 认为想法已可行动 | Motive 可继续保留；不创建 Work、资产绑定或生产权限 | WIC、Interaction |
| J12 | 用户明确准备创建 Work | P0 | 正常路径 | 从讨论转向持续协作 | 共同理解已可行动 | Watt 展示 Work Formation Review，不静默创建 Work | WIC、Work formation |
| J13 | 意外切换话题 | P1 | 分支 | 问一个无关问题而不带偏原 Motive | Work 前对话活跃 | Watt 回答或澄清关系，同时保留原 Motive | WIC、focus classification |
| J14 | 真正的新 Motive | P0 | 分支 | 开始不同结果而不污染当前上下文 | 输入与当前内容实质无关 | Watt 建议新对话/Work 上下文，已有 Reality 不变 | WIC、Interaction relationship |
| J15 | 回到之前尚未准入的 Motive | P1 | 管理 | 延续之前的探索 | 存在休眠的 Work 前对话 | 恢复并概括此前理解，无需创建 Work 即可继续 | WIC、Interaction history |

## 3. Work 形成、准入与资产

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J16 | 形成审阅已就绪 | P0 | 正常路径 | 准确看到 Watt 打算完成什么 | WIC 达到 readiness | 准入前可读地展示目标、结果、范围、约束、预期制品和生产边界 | WIC、Work projection |
| J17 | 用户准入拟议 Work | P0 | 正常路径 | 从已审阅方案授权持续 Work | 精确形成方案可见 | 创建一个带溯源的 Work；生产权限仍独立 | Work、Human Authority |
| J18 | 形成理解有误 | P0 | 分支 | 不创建 Work，先纠正方案 | Formation Review 可见 | 方案回到细化，不创建 Work | WIC、Work formation |
| J19 | 补充最后一项约束 | P0 | 分支 | 准入前修订精确方案 | Formation Review 可见 | 约束进入新版审阅；旧 readiness 不授权新版本 | WIC、Work formation |
| J20 | 推迟准入 | P1 | 分支 | 保存进展，稍后决定 | Formation Review 可见 | 审阅可恢复，权限不转移 | Interaction、Work formation |
| J21 | 拒绝形成方案 | P1 | 分支 | 干净地拒绝拟议 Work | Formation Review 可见 | 关闭方案或返回对话，不创建 Work | WIC、Human Authority |
| J22 | 没有现成代码库 | P0 | 正常路径 | 无需准备基础设施也能开发软件 | Work 已准入，资产范围为空 | 设计继续；Watt 说明可在生产就绪时创建托管工作区 | Work、Assets |
| J23 | 添加已有代码库 | P0 | 正常路径 | 使用用户现有代码 | Work 存在，已提供代码库引用 | Watt 观察能力并展示明确的 Work 范围绑定决策 | Assets、Human Authority |
| J24 | 多个相关资产 | P1 | 分支 | 同时使用代码库、文档、设计或目标 | Work 需要多个输入/目标 | 按角色和能力展示资产，Work 身份不变 | Assets、Work |
| J25 | 外部资产需要授权 | P0 | 异常 | 只授予必要访问权限 | 可发现资产，但尚无能力授权 | 展示精确用途和后果；Work 可等待或采用替代方案 | Assets、Human Authority、Attention |
| J26 | 不支持的资产或能力 | P1 | 异常 | 理解 Watt 不能使用什么及如何继续 | 能力检查失败 | 明确说明不支持状态和安全替代方案；不伪造绑定或隐藏阻塞 | Assets、Attention |
| J27 | 资产在 Watt 外部发生变化 | P1 | 恢复 | 避免基于过期材料行动 | 已绑定资产指纹不匹配 | Watt 重新观察、解释影响并重新验证，或请求受治理决策 | Assets、Steering、recovery |

## 4. Guided Design 与规划

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J28 | Watt 提出设计结构 | P0 | 正常路径 | 把意图转成连贯的产品/设计形态 | Work 已准入 | Watt 聚焦最关键领域并说明原因 | Guided Design、WIC |
| J29 | 接受推荐 | P0 | 正常路径 | 不经过多余仪式直接推进 | 推荐可见 | 决策进入设计 Reality，随后切换到下一个重点 | Guided Design、Human Authority |
| J30 | 修改业务需求 | P0 | 分支 | 更新预期行为并理解影响 | Guided Design 活跃 | Watt 区分普通细化与重大范围变化，并更新正确所有者 | WIC、Work、Guided Design、Steering |
| J31 | 修改技术约束 | P1 | 分支 | 增加必要平台或集成约束 | Guided Design 活跃 | 展示约束影响、冲突和修改后的设计方向 | Guided Design、Work |
| J32 | 未解决的设计决策 | P0 | 异常 | 在上下文充分时作出重大选择 | 两种可行方案会影响结果 | Watt 推荐其一、解释取舍并记录用户选择 | Guided Design、Attention、Human Authority |
| J33 | 请求备选方案 | P1 | 分支 | 比较可信选项 | Watt 已推荐一种做法 | 精简对比保留 Watt 的判断，并允许用户选择 | Guided Design、WIC |
| J34 | 设计已可进入生产 | P0 | 正常路径 | 知道设计已足够，以及将要构建什么 | 必需设计领域均已满足 | 解释 readiness 和剩余假设，生产方案进入可审阅状态 | Guided Design、Steering |
| J35 | 多个有意义阶段 | P0 | 正常路径 | 不阅读 Executor 任务也能理解路径 | 生产需要多个成果 | 计划按顺序命名结果阶段、验证和依赖 | Steering、PWU planning |
| J36 | 新输入后修改计划 | P1 | 分支 | 看懂新信息如何改变下一步 | 生产前收到相关新输入 | Steering 从当前 Reality 修订方向并解释变化 | WIC、Work、Steering |
| J37 | 生产中出现重大变化 | P0 | 异常 | 改变范围而不污染进行中工作 | 生产活跃，输入改变目标/权限 | 安全限制或暂停当前生产，并展示受治理变更决策 | WIC、Steering、Queue、Human Authority |
| J38 | 审阅生产方案 | P0 | 正常路径 | 执行前确认输出、目标和检查 | 设计与计划已就绪 | 用通俗方案接受、细化或拒绝，无需理解 contract 内部细节 | Steering、PWU、Assets、Human Authority |
| J39 | 将未来方向与当前工作分开 | P1 | 分支 | 保留未来想法而不改变当前 Work | 出现相关但非当前的想法 | 作为 emerging direction 保留，不修改已准入范围 | WIC、Steering |

## 5. 队列、生产、进度与控制

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J40 | 已就绪但仍在排队 | P0 | 正常路径 | 知道 Work 已准入，只是在正常等待 | 可运行阶段已进入队列 | 展示排队原因、当前顺序上下文与下一次转换 | Queue、Work |
| J41 | 等待容量 | P0 | 分支 | 区分容量等待和失败 | 没有兼容容量 | 诚实说明等待，不伪造 ETA，也不虚构用户行动 | Queue、Capacity |
| J42 | 已分配 | P1 | 正常路径 | 知道 Watt 即将开始 | Scheduler 已授予容量 | 同一阶段从等待转为准备/启动 | Queue、Executor |
| J43 | 正在运行 | P0 | 正常路径 | 知道 Watt 当前正在做什么 | Native Attempt 活跃 | 展示有意义的当前活动、耗时、已完成阶段和可能的下一步 | Executor、Work projection |
| J44 | 检查点已保存 | P1 | 恢复 | 相信有用进展能抵御中断 | Executor 达到持久前沿 | 历史中显示平静的检查点标记，不把它当作产品完成 | Executor、checkpoint |
| J45 | 暂时让出资源 | P1 | 分支 | 理解计划内资源交接 | 活跃执行让出 | 同一阶段显示“已保存，等待继续”，不暗示新 Work/PWU | Executor、Queue |
| J46 | 重新入队 | P1 | 恢复 | 知道已保存工作将继续 | 让出或可恢复中断已处理 | 队列条目保留连续性和原因，不显示重复生产 | Queue、recovery |
| J47 | 从检查点恢复 | P0 | 恢复 | 不丢失有价值工作地继续 | 存在兼容分配和检查点 | 从保留前沿继续，恢复开销在详情中透明可查 | Queue、Executor、checkpoint |
| J48 | 等待 Provider 容量 | P1 | 分支 | 知道外部服务等待正被处理 | Provider 不可用或处于策略内限流 | 用户只看到“等待生产容量”、影响与责任方，隐藏原始 Provider 请求 | Executor、Queue |
| J49 | 等待用户 | P0 | 异常 | 明确看到阻塞进度的决策 | 需要受治理决定或凭据 | 队列和 Work 链接到同一个“需要我”事项，说明后果与选择 | Queue、Attention、Human Authority |
| J50 | 等待外部资源 | P1 | 异常 | 无需调试即可处理不可用能力 | 缺少工具、资产、Runtime 或账户前置条件 | Watt 解释所需资源，并提供替代或稍后继续选项 | Queue、Assets、Attention |
| J51 | 失败后自动恢复 | P0 | 恢复 | 让 Watt 处理普通故障 | 可恢复执行/工具失败 | Watt 保留事实，只在语义允许时重试，不要求用户参与调试 | Executor、recovery |
| J52 | `UNKNOWN` 与对账 | P0 | 恢复 | 确认 Watt 正谨慎处理未知影响 | 进程/Provider 结果无法证明外部 Reality | 阻断不安全继续；Watt 先重新观察，再做残余工作或请求行动 | Recovery、Executor、Attention |
| J53 | 用户暂停 | P1 | 管理 | 安全地暂时停止新工作 | 活跃或排队阶段支持受治理暂停 | 区分暂停请求与最终安全状态，保留进展 | Human Authority、Queue、Executor |
| J54 | 用户恢复 | P1 | 管理 | 继续已暂停 Work | 已暂停阶段仍兼容 | Watt 重新验证当前依据并恢复/重新入队，不改变阶段身份 | Human Authority、Queue、recovery |
| J55 | 停止当前生产 | P1 | 管理 | 安全终止当前生产路径 | 支持受治理停止 | 停止新影响，对账未知影响，保留输出与历史 | Human Authority、Executor、recovery |
| J56 | 取消排队阶段 | P1 | 管理 | 撤回尚未开始的工作 | 阶段在队列中且没有活跃影响 | 取消队列条目并说明影响；Work 仍可重新规划 | Queue、Human Authority |
| J57 | 一个 Work 包含多个阶段 | P0 | 正常路径 | 理解较长结果中的真实进度 | Plan 包含多个 PWU | 清楚展示已完成/当前/下一阶段，隐藏执行时间片 | Steering、PWU、Executor |
| J58 | 多个 Work 竞争容量 | P1 | 管理 | 理解为何一个等待、另一个运行 | 两个 Work 都可运行 | 全局队列解释容量分配，不让用户成为调度操作员 | Queue、Capacity |
| J59 | 一个阶段完成并转入下一阶段 | P0 | 正常路径 | 看懂结果阶段间的连续性 | 一个 PWU satisfied，Plan 仍有下一方向 | 更新里程碑历史，Steering 准入或准备下一阶段 | Verification、Steering、Queue |
| J60 | 回复/生产期间浏览器仍可使用 | P0 | 分支 | 继续输入和导航，不污染 Turn | Conversation 回复或生产流活跃 | Composer 接收有序 pending message；重连不重复提交或取消工作 | Conversation、event stream、Queue |

## 6. 验证、结果审阅、授权与交付

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J61 | 正在验证 | P0 | 正常路径 | 知道 Watt 正检查精确输出 | 存在 result-ready claim | 产品说明正在检查什么，并区分“已生成”与“已通过” | Verification、Executor claim |
| J62 | 验证通过 | P0 | 正常路径 | 理解为什么结果已可审阅 | 精确输出通过必需检查 | 精短信任摘要和可检查证据引导至结果预览 | Verification、Candidate |
| J63 | 验证失败，Watt 自行修正 | P0 | 恢复 | 让 Watt 自主修复普通缺陷 | 失败义务在已准入范围内且可恢复 | 保留失败历史；执行受治理修正并验证新的精确结果 | Verification、Steering、Executor |
| J64 | 验证失败，需要用户处理 | P1 | 异常 | 当修正改变目标、风险或访问权限时作决定 | 无法在当前权限内修正 | “需要我”说明违反的义务和决策选项 | Verification、Attention、Human Authority |
| J65 | 预览新应用 | P0 | 正常路径 | 授权前亲自体验软件 | 存在已验证且可预览的应用 Candidate | 在隔离运行预览中展示精确结果身份和已知限制 | Candidate preview、Verification |
| J66 | 预览代码/软件修改 | P0 | 正常路径 | 无需阅读每个文件也能理解改动 | 存在已验证的变更 Candidate | 展示摘要、关键行为、影响范围、检查及可选 diff/evidence | Candidate preview、Assets |
| J67 | 预览多代码库/多资产 | P1 | 分支 | 理解跨目标的一个连贯结果 | 聚合结果包含多个目标 | 以一次审阅展示逐目标影响和跨目标验证 | Candidate vector、Assets、Verification |
| J68 | 已知限制或重大风险 | P0 | 异常 | 存在残余风险时作知情决定 | 可审阅结果含已披露限制 | 突出限制、后果、缓解方式及其对授权的影响 | Verification、Candidate、Human Authority |
| J69 | 请求修正结果 | P0 | 分支 | 集成前要求 Watt 改进 | 预览已打开 | 当前结果保持不可变；修正成为受治理后续并生成新版本 | WIC、Steering、Candidate |
| J70 | 拒绝结果 | P1 | 分支 | 拒绝集成，同时保留证据 | 预览已打开 | 不进行集成；拒绝理由进入重新规划，历史仍保留 | Human Authority、Candidate |
| J71 | 授权精确结果 | P0 | 正常路径 | 批准亲自检查的内容及其应用位置 | 合格的精确结果和目标集合可见 | 授权只绑定该版本，并明确说明预期影响 | Human Authority、Candidate |
| J72 | 多目标部分收敛 | P1 | 恢复 | 理解并安全完成部分应用的授权 | 部分目标已推进，其他未推进 | 明确目标事实、安全向前完成状态和重新授权需求 | Integration、recovery、Assets |
| J73 | 交付可用 | P0 | 正常路径 | 打开或取得可用成果 | 必需 commit/trust 边界已完成 | 提供 Runtime、代码库更新或下载动作，以及清单和信任摘要 | Runtime Commit、Delivery |
| J74 | 审阅交付并确认满意 | P0 | 正常路径 | 判断实际结果是否可用 | 交付可用 | 用户可以接受或要求修改；只有用户验收能标记当前满意 | Delivery、Human acceptance、Work |

## 7. 已有 Work、交付历史与资源管理

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J75 | 查看并筛选 Work | P0 | 管理 | 找到活跃、暂停、已完成和需要处理的 Work | 回访首页或 Work 列表 | 无需 Goal 层级即可浏览状态与最近变化 | Work projections |
| J76 | 切换 Work 而不丢上下文 | P0 | 管理 | 在多个结果之间安全切换 | 存在多个 Work | 每个 Work 恢复自己的对话草稿、当前 Reality 与位置 | Work、Interaction |
| J77 | 重命名 Work | P2 | 管理 | 使用便于记忆的名称 | Work 存在 | 只改变显示名，不改变身份、权限或历史 | Work projection |
| J78 | 隐藏/归档 Work | P2 | 管理 | 减少杂乱且不删除历史 | 存在休眠/已完成 Work | 从默认视图移除，但仍可查找和恢复 | Work projection |
| J79 | 查看上次离开后的变化 | P0 | 管理 | 快速了解进展 | 用户离开期间发生持久事件 | 每项重大变化都链接到当前 Work 上下文 | Work events、Attention、Delivery |
| J80 | 查看交付历史 | P1 | 管理 | 重新打开旧成果及其依据 | Work 有一个或多个交付 | 可区分精确交付、信任依据、资产及后续版本 | Delivery、Work |
| J81 | 细化已完成 Work | P0 | 正常路径 | 延伸或改进同一个结果 | 存在满意 Work 和历史交付 | Conversation 重新打开；Watt 区分细化和新 Motive，进入受治理修订路径 | WIC、Work、Steering |
| J82 | 基础用量/容量可见性 | P2 | 管理 | 理解具有商业意义的限制 | 账户/容量限制影响进度 | 用通俗方式展示剩余额度或所需动作，不提供 Provider 请求控制 | Capacity、account projection |

## 8. 跨领域异常与恢复

| ID | 场景 | 优先级 | 类别 | 用户目标 | 进入条件 | 预期结果 | 涉及能力 |
|---|---|---|---|---|---|---|---|
| J83 | 浏览器断连/重连 | P0 | 恢复 | 返回时不取消或重复工作 | 标签页关闭或事件流中断 | 从 cursor/projection 恢复持久状态；pending message 与生产保持一致 | Event stream、Interaction、Executor |
| J84 | Runtime 或 worker 重启 | P1 | 恢复 | 相信服务重启不会抹掉有用进展 | Runtime 进程/worker 重启 | Lease/recovery 恢复一致前沿，UI 说明恢复或继续状态 | Executor、recovery、checkpoint |
| J85 | 工具失败 | P1 | 恢复 | 不成为工具调试信息的中转站 | 工具返回失败或影响不确定 | Watt 记录确定性，在授权内使用安全替代/恢复，或请求必要决策 | Executor、recovery |
| J86 | 资产不可用或权限丢失 | P1 | 异常 | 恢复访问或选择替代项 | 无法读取/写入已绑定资产 | 展示影响、所需能力以及重新授权/替换/稍后继续选项 | Assets、Attention、Human Authority |
| J87 | 决策界面已经过期 | P0 | 恢复 | 避免批准过期结果或计划 | 审阅期间 Reality 变化 | 安全拒绝动作、重新加载当前事实并突出依据变化 | Projections、Human Authority、recovery |
| J88 | 长时间离开后返回 | P1 | 管理 | 不阅读日志也能重建完整故事 | Work 跨多个阶段/交付发生变化 | 变化摘要、当前结果、现有需求和下一步形成连贯叙事 | Work events、Delivery、Attention |
| J89 | 企业角色与审批链 | DEFERRED | 管理 | 在组织内委派权限 | 请求多人企业治理 | 明确不在首发范围；原型假设一个负责操作者 | Future identity/governance |
| J90 | 高级 Provider 与 worker 控制台 | DEFERRED | 管理 | 调整模型、reasoning effort、重试和 worker | 请求专家级基础设施管理 | 明确不在首发范围；工程诊断保持独立 | Provider/Executor operations |
| J91 | 未来 Guardian 保障决策 | DEFERRED | 分支 | 使用 Guardian 判断 | Guardian 已存在 | 首发原型不声称具备 Guardian 行为 | Future Guardian |
| J92 | 未来 ECF 能力市场 | DEFERRED | 管理 | 选择具备资格的外部生产能力 | ECF 已存在 | 首发原型不声称具备 ECF 行为 | Future ECF |

## 9. 覆盖说明

清单覆盖从 Motive 到 Delivery 再到后续重新进入的连续价值旅程，也覆盖全局 Work 管理、Queue、Human Attention、资产、容量、授权、历史、异常和恢复。原型场景包会把这些条目组合成可重放叙事；场景包不是新场景，也不是新的事实来源。

清单中的任何条目都不构成生产实现授权。优先级只描述原型和首发版体验优先级，架构与 Runtime 所有者继续由其 SOT 文档定义。
