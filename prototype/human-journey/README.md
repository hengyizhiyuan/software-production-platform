# Watt 用户体验可点击原型

## 用途

这是 Watt 首发版用户旅程的高保真、可点击、确定性体验模拟。Prototype v2.3 用于评审 Work-centric 核心工作区、稳定四工作面、Human-controlled Focus、Active/History 边界、workspace-native Composer 与 Current Interaction Layer，同时保留此前版本的完整场景覆盖。

所有界面都是候选体验，当前状态均为 `DRAFT`，不代表 Human 已接受。

## 隔离边界

原型只使用 `src/scenarios.ts` 中打包的 mock facts：

- 不连接 Watt API 或 PostgreSQL；
- 不调用 DeepSeek 或任何 Provider；
- 不触发 Executor、Git 或真实 Preview；
- 不读取真实用户或代码库数据；
- 不依赖 Docker、凭据或现有 Watt Runtime；
- 不修改生产数据。

启动时安装的 Network Guard 会拒绝应用代码发起的 `fetch`、WebSocket、EventSource 和外部表单提交。Vite 开发服务器只负责从 `127.0.0.1` 提供本地静态模块。

## 启动

```bash
cd prototype/human-journey
npm install
npm run dev
```

默认地址：`http://127.0.0.1:4173`

构建与验证：

```bash
npm run check
```

## Reviewer Mode

点击右上角滑杆图标打开评审模式。它可以：

- 选择 P01–P16 场景包；
- 直接选择任一场景；
- 重置到场景包 Seed；
- 按默认路径推进模拟；
- 查看 J 场景 ID、T 张力 ID 和验收重点；
- 保存仅存在当前浏览器 `localStorage` 中的短评审笔记。
- 查看当前可见的 Reality/Agenda/Production/Actions、Focus 状态、Current Interaction 状态与 Work 分组来源。

当前场景会同步到 URL fragment：

```text
#pack=P10&scene=p10-result
```

复制该 fragment 即可直接回到同一个问题状态。Reviewer 工具与模拟的客户产品界面在视觉上明确分开。

## 与规划文档的关系

- [首发版用户旅程与信息架构](../../docs/product/watt-first-release-human-journey.md)
- [首发版场景清单](../../docs/product/watt-first-release-scenario-inventory.md)
- [可点击原型范围、验收与实施计划](../../docs/product/watt-clickable-prototype-plan.md)
- [用户旅程架构张力登记表](../../docs/product/watt-human-journey-architecture-tensions.md)

原型可以模拟规划中的目标体验，但不能成为领域 SOT。Owner-specific mock facts 只用于驱动界面；`PRE_WORK`、`RUNNING` 等便利状态只是 Reviewer Cursor，并非新的统一生命周期。

## 已知限制

- Conversation 回复是人工编写的确定性内容，不评价真实 WIC 智能或首字符延迟。
- 应用 Preview、代码 Diff、Queue、Recovery、Verification、Authorization 与 Delivery 均为体验模拟。
- 顶层导航按 Human Governor 校准为“首页 / 历史 / 交付”；左侧导航只保留 Active Work，Queue 通过首页、Work 和二级生产详情呈现。
- 当前使用临时视觉系统，不冻结最终品牌、色彩或字体。
- 窄屏布局用于体验方向评审，不代表最终移动端产品范围。
- Current Interaction 的 5.2 秒阅读宽限、流式节奏、Focus 比例与 Composer 展开方式都是可逆 dogfood 参数。
- Work 分组、置顶、历史与投影逻辑是本地模拟元数据，不改变生产优先级或 Work 领域事实。

## Prototype v2 的主要变化

- 左侧以当前 Work 为核心，支持搜索、置顶、语义/人工分组、折叠和拖放；
- 中央持续显示“当前情况 / 接下来 / 生产进展 / 需要你处理”四个工作面；
- 每个可见功能可进入 Focus Mode，其余功能收成可发现的摘要条；
- Conversation History 位于右侧，可收起，承担历史溯源而非当前真相；
- Composer 永久属于中央 Work Workspace：空闲时是一行安静的停靠栏，获得焦点后从底部向上展开；
- 刚提交的 Human turn 与流式 Watt 回复保留在中央 Current Interaction Layer；
- 回复完成后经过阅读保护与安静 crossfade 进入对话历史，已形成的 Reality 继续保留；
- 交付按 Work → Delivery revision → Artifact/Runtime/Repository/Documentation 组织。

## Prototype v2.1 的聚焦修订

v2 的四项功能在聚焦时更像卡片最大化与纵向替换，没有充分表达 Human Governor 草图中的空间连续性。v2.1 只修订中央工作空间：

- 四个可见表面默认形成一个连贯的 2×2 概览；不足四个表面时自然填满可用区域；
- `surface-1` 至 `surface-4` 在概览、聚焦和直接切换期间保持同一 React identity；
- Surface 1–4 各自使用与原始空间关系一致的主区和摘要区构型；
- 压缩表面仍显示标题、当前状态摘要与切换入口，重要 Actions 只提示，不自动夺取焦点；
- 使用 360ms、无弹跳的 FLIP 位移与缩放动画解释空间变化；连续点击会取消旧动画并转向最新布局；
- `prefers-reduced-motion` 下跳过空间动画，键盘仍可访问所有聚焦和恢复控件；
- 正文始终挂载，压缩只改变呈现，因此局部 disclosure、草稿和选择状态可继续保留。

这轮没有调整四个表面的内部内容、Work 导航、Delivery、Current Interaction、Composer、场景语义或生产架构。360ms 只是可逆原型参数。v2.3 保留这一 Human-controlled morph，但不再允许场景事实自动改变工作面的存在或默认几何。

## Prototype v2.2 的边界校准

- 左侧只显示仍需关注或生产的 Active Work，不再提供“当前 / 历史工作项”切换；
- 已完成或归档的 Work 位于顶层“历史”，可查看结果、状态和摘要，但不能在原型中重新打开；
- 顶层冗余 Work 入口被“历史”替代，选择左侧 Active Work 仍直接进入其中央 workspace；
- Composer 从右侧 Conversation rail 完全移除，始终停靠在中央 Work 下方；
- 空闲 Composer 约一行高度；聚焦后在同一底部锚点向上扩展，Escape 仅在空内容时安全收回；
- 发送后 Composer 收回，Human turn 与 Watt reply 在中央形成 bounded Current Interaction，完成后安静归入右侧历史；
- 右侧只承担较弱的 Conversation provenance，不提供输入或伪输入跳转；
- Reality / Agenda / Production / Actions 的 identity、内容和 Overview/Focus morph 规则保持不变。

## Prototype v2.3 的稳定四工作面校准

- Reality、Agenda、Production、Actions 在每个 Active Work 场景中持续存在；
- 默认 Overview 始终采用同一 2×2 空间：Reality 左上、Agenda 右上、Production 左下、Actions 右下；
- Work Stage、生产状态和 Attention 只能改变内容与提示，不得自动重排、隐藏、聚焦或最大化工作面；
- Human 可以聚焦任一工作面、在焦点之间直接切换，并随时返回 Overview；
- Focus 时其他三个工作面仍以真实摘要保留，重要 Actions 只增强信号，不抢夺 Human 当前焦点；
- reduced-motion 偏好继续关闭空间动画，不改变相同的可达状态与键盘路径；
- 四个工作面的深层信息结构留待真实生产 Dogfood，不在本轮扩展。
