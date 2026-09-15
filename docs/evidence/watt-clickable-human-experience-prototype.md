# Watt 可点击用户体验原型实现 Reality

## 状态

```text
原型候选
    PROTOTYPE V2.3 IMPLEMENTED

Human Experience Acceptance
    PENDING

生产实现
    NOT STARTED
```

该原型位于 `prototype/human-journey/`，使用隔离的 Vite、React、TypeScript 与确定性本地 fixture。它不连接生产 API、数据库、Provider、Executor 或真实资产。

## 已实现范围

- 同一个响应式产品外壳承载首页、Work 与交付三个顶层区域；
- Queue/生产状态通过首页摘要、Work 上下文与二级生产详情呈现，不作为顶层导航；
- P01–P16 全部 16 个可重置场景包，共 53 个可直接深链的场景；
- Work 前对话、Formation Review、Guided Design/方向、资产、里程碑、等待、检查点、恢复、Attention、Verification、结果 Preview、精确 Authorization、Delivery 与 Re-entry；
- Reviewer Mode 支持选包、选场景、重置、推进、查看 J/T ID 与验收重点，并保存浏览器本地笔记；
- `#pack=<id>&scene=<id>` 直接场景链接；
- Network Guard 阻止应用代码进行 fetch、WebSocket、EventSource 与外部表单提交；
- 53 个场景的 DRAFT 验收记录。

## v1 → v2

v1 验证了完整 Journey 和 16 个场景包，但 Work 页面在多张内容卡与右侧对话之间显得分散。v2 保留全部 53 个场景，把核心体验重组为：

- 左侧 Work 导航：搜索、当前/历史、语义与 Human 分组、置顶和拖放；
- 中央自适应 Work workspace：当前情况、接下来、生产进展、需要你处理；
- Human-controlled Focus Mode；
- 右侧次要但持续可用的 Conversation History；
- Work 下方的 Current Interaction Layer 与展开 Composer；
- Human turn 保留、Watt reply 流式显示、阅读保护和安静归档；
- Human input → Watt interpretation → Reality highlight 的可见因果链；
- Work → Delivery revision → usable outcomes 的交付结构。

v1 的提交与记录仍保留在 Git 历史；本次没有把 v1 改写成从未存在。

## v2 → v2.1：Human Governor 草图空间校正

v2 已具备四项功能和 Human-controlled Focus Mode，但实际表现仍接近“卡片最大化”：聚焦表面置顶，其余表面统一纵向压缩，无法直观看出表面来自 2×2 空间中的哪个位置。

v2.1 按 Human Governor 草图把中央区域改为一个持续存在的 adaptive workspace：

- 四表面场景默认是完整 2×2 概览，而非互不相关的 dashboard cards；
- Surface 1 聚焦时位于主区上方，2/3/4 在底部并列；
- Surface 2 聚焦时保留 Surface 1 顶部摘要，3/4 位于底部；
- Surface 3 聚焦时保留 1/2 顶部摘要和 4 底部摘要；
- Surface 4 聚焦时保留 1/2/3 顶部摘要；
- 每个表面的 `surface-1`—`surface-4` identity 和正文实例持续保留；
- 360ms FLIP 动画从实际旧位置过渡到新位置，焦点间可直接切换并中断旧动画；
- 压缩表面展示真实状态摘要；关键 Actions 会增强提示，但不夺取 Human 当前焦点；
- 1–3 个表面时重新分配现有空间，不产生空象限；窄屏改为保持 identity 的纵向布局；
- reduced-motion 环境不执行空间动画，所有原生按钮继续支持键盘访问。

本次刻意不改 Reality、Agenda、Production、Actions 内部内容，也不改 Work 导航、Delivery、Human Turn Mediation、Current Interaction、场景 taxonomy 或生产实现。

## v2.1 → v2.2：Active Work 与当前交互归属校准

Human Governor 的原型体验确认了两个边界：

- 左侧是当前车间，只显示 Active Work；已完成/归档 Work 进入独立顶层“历史”；
- 当前交互属于中央 Work Reality，不属于右侧 Conversation History。

实现变化：

- 顶层导航从“首页 / Work / 交付”调整为“首页 / 历史 / 交付”；
- 左侧移除“当前 / 历史工作项”切换，仅保留三个 Active Work fixture；
- 顶层 History 展示两个归档 Work 的目标、状态与历史语义，不提供重新打开；
- Composer 从右栏完全移除，空闲时作为中央一行停靠栏，聚焦时在同一底部锚点向上展开；
- 发送后 Composer 收回，Human turn 与 Watt reply 在中央 Current Interaction 中共同显示；
- 完成且无人阅读交互后，当前 pair 通过安静 crossfade 恰好一次归入右侧 Conversation History；
- 右栏增加 provenance 说明并降低视觉权重，不承担当前动作；
- 四个 Work surface 的 identity、2×2 Overview、FOCUS_1–FOCUS_4 和响应式布局未改变。

这次变化只校准原型 shell 和交互几何。它没有实现 Archive 生命周期、新 Work Formation、生产 API 或最终视觉系统。

## v2.2 → v2.3：稳定四工作面

最终空间校准让 Reality、Agenda、Production、Actions 在每个 Active Work
场景中持续存在。Overview 始终采用相同 2×2 几何。场景、Work 阶段、生产活动
和 Attention 只改变表面内容与提示，不再自动移除、重排、聚焦或缩放工作面。

Human-controlled Focus 保留：可以聚焦任一工作面、直接切换焦点并返回
Overview。其余三个工作面继续以真实摘要存在。Attention 可以增强信号，但
不能抢夺焦点。没有生产或 Human 动作时，Production 与 Actions 显式呈现安静
空状态。

该规则是来自 Human 原型 dogfood 的候选生产 UX 方向，不是对所有未来自适应
界面的全局禁令，也不构成 Human Experience Acceptance。

## Mock 目标假设

Formation Review、统一 Attention 投影、通用 Asset、授权前 Preview、多目标结果、跨所有者 Trust 摘要、过期决策对比、部分目标收敛、回访 Home 与 reconnect continuity 均按目标体验模拟。Reviewer Mode 会显示相应 Tension ID；这些界面不表示生产 Runtime 已具备能力。

## 刻意延后的 v2 细节

- 真实或随机 AI 对话；
- 最终品牌、字体、色彩与像素级视觉规范；
- 真实移动端产品，只提供窄屏体验方向；
- 真实 Preview、代码 Diff、Queue 调度、Recovery、Verification、Authorization 或 Delivery；
- 企业 IAM、Guardian、ECF、Provider/worker 控制台；
- Agenda 内部结构、PWU/阶段投影与生产控制语义；
- 最终 Reality 命名、Focus 比例、Composer 阈值与归档时序；
- 生产级 mediation owner、持久化、确认规则和 archive lifecycle。

本记录不改写四篇规划文档，也不构成生产能力或 Human Experience Acceptance 证据。

本次 dogfood 中发现的 Experience-before-Production 模式已单独记录为
[候选治理模式](../product/experience-before-production-candidate.md)。其状态仍为
`CANDIDATE / DOGFOOD_PENDING`，不构成冻结的产品要求或正式生产门禁。

## 实现验证

- `npm run check`：fixture、Work 导航、稳定四工作面投影与四种 morph 构型、Current Interaction、隔离与验收记录测试通过，TypeScript 与 Vite production build 通过；
- v2.3 真实 Edge 烟测：从首页进入 Active Work、P01 Formation Review 与 P09 Verification Failure 均保持相同 `surface-1`—`surface-4` 和固定 2×2 Overview；Reality → Production → Actions 可直接切换并返回 Overview；Current Interaction 在阅读宽限后消失且恰好两条消息归入 Conversation History，History 往返不改变默认几何；Attention 不抢夺焦点；
- v2.3 reduced-motion 烟测：浏览器实际启用 `prefers-reduced-motion: reduce` 后，Focus 状态仍可达且四工作面的运行中动画数为 0；控制台无应用 warning/error；
- v2.2 静态边界：顶层只有首页/历史/交付；Active rail 不渲染 historical fixtures；右栏源码不含 Composer；中央 Work 始终渲染 idle/expanded Composer；
- v2.2 真实 Edge 烟测：从首页选择 Active Work 后，中央 Composer 由 idle 聚焦展开并在发送后收回；Human turn/Watt reply 只在中央显示，阅读聚焦超过归档宽限仍保留，结束阅读后恰好一次归入右侧 History；顶层 History 显示两个归档 Work 且左栏仍只有三个 Active Work；
- v2.2 共存路径：P09 四表面保持 `OVERVIEW` 与相同 `surface-1`—`surface-4`，Production 聚焦为 `FOCUS_3` 后 Current Interaction 出现但不改变焦点或表面数量；Reviewer Mode v2.2 与 Network Guard 均通过；
- v2.1 浏览器检查：P09 四表面 2×2 概览、FOCUS_1–FOCUS_4 四种独立构型、焦点间直接切换及概览恢复均通过；每个构型保留 4 个相同 `data-surface-id`；
- 稳定表面：P01 Formation Review 与 P09 Verification Failure 都保留相同四个 identity 和默认 2×2 几何；
- 共存与控制：FOCUS_3 中提交“请暂停当前生产”后，四表面、Current Interaction 与展开 Composer 同时可用；Enter 键可进入聚焦并恢复概览；Reviewer 深链显示正确 mode、visible surfaces 与 focused surface；
- 响应式：390×844 下四表面保持同一实例并纵向可读，顶部导航和 v2.1 模拟标识保持可见；临时 viewport override 已在验证后恢复；
- reduced-motion：布局动画由运行期 media preference 直接关闭，现有 reduced-motion 单元路径与 CSS media override 均通过构建；当前浏览器工具不提供 media emulation，因此未伪造手工 reduced-motion 结果；
- v2 浏览器路径：P01、P05、P07、P10、P11、P12、P14 已完成代表性点击验证；v1 已完成 P01、P05、P06、P10、P11、P12、P14、P16 全路径；
- 关键交互：Work Formation、Production/Actions 安静空状态、Focus expand/restore、Actions 提示保留、人工分组 reload 后保留、历史/当前搜索分离、授权前 Preview 与 Work-centric Delivery 已实际操作；
- Current Interaction：Human turn 保留、Watt 逐步回应、Reality effect、诚实 pause mediation、阅读聚焦暂停归档、归档后历史恰好一次、Conversation collapse 不丢当前交流均已验证；
- Reviewer Mode：Pack/Scene、可见功能、Focus、Current Interaction、分组来源、J/T ID、设计记录和本地笔记已验证；
- 窄屏：在 390×844 viewport 手动验证，document scroll width 保持 390px，三项顶层导航和永久模拟标识可见且互不遮挡；
- 浏览器控制台：代表路径无 warning/error；
- 网络边界：源代码扫描无远程 URL 或生产 API，运行期 Network Guard 拒绝 `fetch`、WebSocket、EventSource 与外部表单提交。
