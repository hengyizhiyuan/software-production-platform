# Watt 用户体验可点击原型

## 用途

这是 Watt 首发版用户旅程的高保真、可点击、确定性体验模拟。它供 Human Governor 在任何正式 UI 或后端实现开始前，评审产品心智模型、导航、对话、Work 形成、生产感知、Attention、结果授权、交付与重新进入。

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
