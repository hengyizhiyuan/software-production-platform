# Watt 可点击用户体验原型实现 Reality

## 状态

```text
原型候选
    FIRST CANDIDATE IMPLEMENTED

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

## Mock 目标假设

Formation Review、统一 Attention 投影、通用 Asset、授权前 Preview、多目标结果、跨所有者 Trust 摘要、过期决策对比、部分目标收敛、回访 Home 与 reconnect continuity 均按目标体验模拟。Reviewer Mode 会显示相应 Tension ID；这些界面不表示生产 Runtime 已具备能力。

## 未实现的原型项目

- 真实或随机 AI 对话；
- 最终品牌、字体、色彩与像素级视觉规范；
- 真实移动端产品，只提供窄屏体验方向；
- 真实 Preview、代码 Diff、Queue 调度、Recovery、Verification、Authorization 或 Delivery；
- 企业 IAM、Guardian、ECF、Provider/worker 控制台。

本记录不改写四篇规划文档，也不构成生产能力或 Human Experience Acceptance 证据。

## 实现验证

- `npm run check`：6 项 fixture/隔离/验收记录测试通过，TypeScript 与 Vite production build 通过；
- 浏览器完整路径：P01、P05、P06、P10、P11、P12、P14、P16 均从 Seed 点击到终态；
- 关键交互：首次建议填入与发送、Work Formation、等待与恢复、授权前完整预览、Attention 深链、回复期间继续输入、Delivery/Re-entry、运行版本差异均已实际操作；
- Reviewer Mode：Pack/Scene 选择、URL fragment 深链、J/T 标识和浏览器本地笔记已验证；
- 窄屏：响应式收敛、结果卡重排、侧栏隐藏和永久模拟标识由断点样式覆盖；
- 网络边界：源代码扫描无远程 URL 或生产 API，运行期 Network Guard 拒绝 `fetch`、WebSocket、EventSource 与外部表单提交。
