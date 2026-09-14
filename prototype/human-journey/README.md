# Watt 用户体验可点击原型

## 用途

这是 Watt 首发版用户旅程的高保真、可点击、确定性体验模拟。Prototype v2 用于评审 Work-centric 核心工作区、Current Interaction Layer 与双态 Composer，同时保留 v1 的完整场景覆盖。

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
- 顶层导航按本轮 Human Governor 覆盖调整为“首页 / Work / 交付”；Queue 通过首页、Work 和二级生产详情呈现。
- 当前使用临时视觉系统，不冻结最终品牌、色彩或字体。
- 窄屏布局用于体验方向评审，不代表最终移动端产品范围。
- Current Interaction 的 5.2 秒阅读宽限、流式节奏、Focus 比例与 Composer 展开方式都是可逆 dogfood 参数。
- Work 分组、置顶、历史与投影逻辑是本地模拟元数据，不改变生产优先级或 Work 领域事实。

## Prototype v2 的主要变化

- 左侧以当前 Work 为核心，支持搜索、置顶、语义/人工分组、折叠、拖放和历史工作项；
- 中央按场景事实自适应显示“当前情况 / 接下来 / 生产进展 / 需要你处理”，而非固定四宫格；
- 每个可见功能可进入 Focus Mode，其余功能收成可发现的摘要条；
- Conversation History 位于右侧，可收起，承担历史溯源而非当前真相；
- Composer 被动时位于右侧，获得焦点后在 Work 下方展开；
- 刚提交的 Human turn 与流式 Watt 回复保留在中央 Current Interaction Layer；
- 回复完成后经过阅读保护与安静 crossfade 进入对话历史，已形成的 Reality 继续保留；
- 交付按 Work → Delivery revision → Artifact/Runtime/Repository/Documentation 组织。
