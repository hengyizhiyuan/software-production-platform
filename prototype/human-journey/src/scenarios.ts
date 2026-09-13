import type { Milestone, ScenarioPack, Scene } from "./types";

export const VALID_SCENARIO_IDS = new Set(
  Array.from({ length: 92 }, (_, index) => `J${String(index + 1).padStart(2, "0")}`),
);

export const VALID_TENSION_IDS = new Set(
  Array.from({ length: 28 }, (_, index) => `T${String(index + 1).padStart(2, "0")}`),
);

const deliveryMilestones: Milestone[] = [
  { label: "理解目标", detail: "目标与边界已确认", state: "done" },
  { label: "形成方案", detail: "关键设计与取舍已明确", state: "done" },
  { label: "完成生产", detail: "结果已生成并保存", state: "done" },
  { label: "验证结果", detail: "关键检查已通过", state: "done" },
  { label: "交付使用", detail: "可用成果已经提供", state: "current" },
];

const productionMilestones: Milestone[] = [
  { label: "梳理信息结构", detail: "后台导航与权限边界", state: "done" },
  { label: "实现内容工作台", detail: "正在完成内容资产与渠道关联", state: "current" },
  { label: "连接渠道数据", detail: "等待当前阶段完成", state: "next" },
  { label: "验证并交付", detail: "按真实业务路径验收", state: "next" },
];

const defaultFacts = {
  wic: "对话仅提供表达、解释与溯源。",
  work: "当前界面由 Work 的受治理事实投影。",
};

type SceneDraft = Omit<Scene, "transitions" | "ownerFacts" | "scenarioIds" | "tensionIds" | "acceptanceFocus"> &
  Partial<Pick<Scene, "transitions" | "ownerFacts" | "scenarioIds" | "tensionIds" | "acceptanceFocus">>;

const buildPack = (
  meta: Omit<ScenarioPack, "seed" | "scenes">,
  drafts: SceneDraft[],
): ScenarioPack => {
  const scenes = drafts.map((draft, index) => ({
    ...draft,
    ownerFacts: { ...defaultFacts, ...draft.ownerFacts },
    scenarioIds: draft.scenarioIds ?? [],
    tensionIds: draft.tensionIds ?? [],
    acceptanceFocus: draft.acceptanceFocus ?? "确认此时的信息重点、下一步和用户控制感是否清晰。",
    transitions:
      draft.transitions ??
      (index < drafts.length - 1
        ? [{ label: "推进模拟", to: drafts[index + 1].id, kind: "primary" as const }]
        : []),
  }));
  return { ...meta, seed: scenes[0].id, scenes };
};

const opsUnderstanding = {
  objective: "为 Watt 建立一个能支撑早期推广工作的运营管理后台。",
  scope: ["管理内容资产", "跟踪公众号、小红书与直播渠道", "沉淀开发者和小团队线索"],
  constraints: ["第一期不做完整 CRM", "优先支持冷启动", "关键结果必须可追溯"],
  deliverable: "一个可运行的 Web 运营后台，以及使用说明和验证结果。",
  boundary: "Watt 可以设计和生产后台；对外发布、连接真实账号和写入外部平台需要你另行授权。",
};

const resultDashboard = {
  kind: "application" as const,
  title: "Watt 运营工作台",
  summary: "内容资产、渠道表现和用户线索已经形成一个连贯的日常工作流。",
  highlights: ["按渠道规划和复用内容", "从内容表现追踪到用户线索", "首页直接提示今天值得处理的事项"],
  checks: ["12 条核心业务路径通过", "窄屏布局通过", "空状态与异常状态通过"],
  limitations: ["当前数据为演示数据", "真实公众号和小红书账号尚未连接"],
  assets: ["watt-growth-console", "运营流程说明", "静态 Web 运行预览"],
  previewVariant: "dashboard" as const,
};

export const scenarioPacks: ScenarioPack[] = [
  buildPack(
    {
      id: "P01",
      title: "模糊想法如何自然变成 Work",
      shortTitle: "模糊 Motive",
      description: "从一句不完整的想法开始，体验 Watt 如何先理解和给判断，再邀请用户形成正式 Work。",
      reviewReason: "验证首页第一印象、对话质量和 Work 形成是否自然。",
    },
    [
      {
        id: "p01-home",
        label: "安静的新用户首页",
        phase: "PRE_WORK",
        surface: "home",
        tone: "neutral",
        eyebrow: "第一次来到 Watt",
        title: "你想让什么事情发生？",
        summary: "不必先创建项目或配置代码库。先告诉 Watt 你想解决的问题。",
        messages: [],
        scenarioIds: ["J01", "J11"],
        tensionIds: ["T01"],
      },
      {
        id: "p01-understanding",
        label: "暂定理解与建议",
        phase: "REFINING",
        surface: "home",
        tone: "active",
        eyebrow: "正在一起想清楚",
        title: "先把推广工作真正跑起来",
        summary: "Watt 没有把一句想法变成需求问卷，而是给出可修正的理解和明确建议。",
        messages: [
          { actor: "human", text: "我想做一个运营管理平台。" },
          { actor: "watt", text: "我先按一个可修正的理解推进：你要的是一个帮助团队持续开展运营工作的后台，而不是一次运营活动。第一期我建议先抓住内容资产、渠道归因和用户线索这三件事，它们最直接影响冷启动。你准备主要服务什么业务？" },
        ],
        recommendation: {
          title: "先做内容、渠道、线索闭环",
          body: "这三块能让日常运营真正运转，也能最快验证后台是否有价值。",
          rationale: "完整 CRM 和复杂自动化会拉长第一版周期，却不会优先解决冷启动问题。",
        },
        scenarioIds: ["J01", "J07", "J09"],
        tensionIds: ["T01", "T04"],
      },
      {
        id: "p01-context",
        label: "补充背景",
        phase: "REFINING",
        surface: "work",
        tone: "active",
        eyebrow: "共同理解正在形成",
        title: "目标已经更具体了",
        summary: "面向个人开发者和小团队，通过公众号、小红书和直播推广 Watt。",
        workName: "Watt 运营后台（形成中）",
        workOutcome: opsUnderstanding.objective,
        messages: [
          { actor: "human", text: "主要用于推广 Watt，用户是个人开发者和小团队，渠道包括公众号、小红书和直播。" },
          { actor: "watt", text: "明白了。这个后台的核心不是管理一场活动，而是让 Watt 的内容、渠道和用户反馈形成长期闭环。我建议第一版先让三类渠道共用内容资产，再用简单归因把反馈带回选题。" },
        ],
        scenarioIds: ["J04", "J10"],
        tensionIds: ["T04", "T16"],
      },
      {
        id: "p01-review",
        label: "Work 形成审阅",
        phase: "READY_FOR_WORK",
        surface: "work",
        tone: "attention",
        eyebrow: "准备正式继续",
        title: "我们已经理解到这个程度了",
        summary: "如果你认可，Watt 会按下面的目标建立持续 Work；此时仍不会连接真实账号或对外发布。",
        workName: "Watt 运营后台（待确认）",
        workOutcome: opsUnderstanding.objective,
        understanding: opsUnderstanding,
        ownerFacts: { wic: "形成方案已就绪，但尚未创建 Work。", authority: "只有用户选择继续后才发生 Work Admission。" },
        scenarioIds: ["J12", "J16", "J17", "J20"],
        tensionIds: ["T03"],
        transitions: [
          { label: "按这个目标继续", to: "p01-admitted", kind: "primary" },
          { label: "我还想补充", to: "p01-context", kind: "secondary" },
        ],
      },
      {
        id: "p01-admitted",
        label: "Work 已建立",
        phase: "DESIGNING",
        surface: "work",
        tone: "success",
        eyebrow: "Work 已建立",
        title: "开始把目标变成可用方案",
        summary: "Watt 正在从用户最常做的事入手整理后台结构。",
        workName: "Watt 运营后台",
        workOutcome: opsUnderstanding.objective,
        recommendation: {
          title: "先确定每天的核心工作流",
          body: "从“准备内容 → 发布渠道 → 收集反馈 → 调整选题”建立第一版信息结构。",
          rationale: "先围绕真实工作流设计，比先列功能模块更容易得到一个可用产品。",
        },
        ownerFacts: { work: "Work 已从精确形成方案准入。", guidedDesign: "Guided Design 正聚焦日常运营闭环。" },
        scenarioIds: ["J17", "J28"],
        tensionIds: ["T04", "T05"],
      },
    ],
  ),

  buildPack(
    {
      id: "P02",
      title: "清晰软件想法，没有现成代码库",
      shortTitle: "无代码库创建",
      description: "体验从清晰想法到 Work、设计、托管工作区和生产方案的连续过程。",
      reviewReason: "验证用户不准备基础设施也能自然开始。",
    },
    [
      {
        id: "p02-ready", label: "清晰想法", phase: "READY_FOR_WORK", surface: "work", tone: "attention", eyebrow: "目标已经清楚", title: "做一个轻量客户反馈门户", summary: "让内测用户提交问题、查看处理进度，并在更新后收到说明。", workName: "客户反馈门户（待确认）", workOutcome: "让早期用户反馈形成可跟踪的闭环。", understanding: { objective: "创建一个面向内测用户的反馈门户。", scope: ["反馈提交", "公开进度", "更新说明"], constraints: ["无需登录即可浏览", "管理入口保持简单"], deliverable: "可运行的 Web 应用", boundary: "先使用 Watt 托管工作区；对外部署另行确认。" }, scenarioIds: ["J12", "J16", "J22"], tensionIds: ["T03", "T12"]
      },
      {
        id: "p02-design", label: "设计方向", phase: "DESIGNING", surface: "work", tone: "active", eyebrow: "正在形成方案", title: "先让反馈状态对用户有意义", summary: "Watt 建议使用“已收到、正在处理、已有更新”三段表达，避免暴露内部工单流程。", workName: "客户反馈门户", workOutcome: "让早期用户反馈形成可跟踪的闭环。", recommendation: { title: "用用户能理解的状态", body: "状态围绕用户想知道的结果，而不是团队内部流程。", rationale: "这能减少追问，也让管理端保持轻量。", alternatives: ["完整工单状态", "只有留言列表"] }, assets: [{ name: "Watt 托管工作区", role: "生产目标", state: "将在生产就绪时创建" }], ownerFacts: { guidedDesign: "状态模型是当前设计重点。", assets: "Work 当前没有外部代码库。" }, scenarioIds: ["J22", "J28", "J29"], tensionIds: ["T05", "T12"]
      },
      {
        id: "p02-plan", label: "生产方案", phase: "PLANNING", surface: "work", tone: "success", eyebrow: "方案已可生产", title: "分三个有意义的阶段完成", summary: "先完成反馈浏览和提交，再做管理处理，最后验证真实使用路径。", workName: "客户反馈门户", workOutcome: "让早期用户反馈形成可跟踪的闭环。", milestones: [{ label: "反馈门户", detail: "列表、详情和提交", state: "current" }, { label: "管理处理", detail: "状态更新与回复", state: "next" }, { label: "验证与交付", detail: "核心路径和窄屏体验", state: "next" }], ownerFacts: { steering: "Steering 已提出三阶段生产方向。", assets: "生产时将分配 Watt 托管工作区。" }, scenarioIds: ["J34", "J35", "J38"], tensionIds: ["T05", "T12"]
      },
    ],
  ),

  buildPack(
    { id: "P03", title: "在已有代码库上继续", shortTitle: "已有代码库", description: "添加已有产品代码，检查能力并审阅一项真实软件修改。", reviewReason: "验证 Asset 从属于 Work，权限说明清楚且不过度工程化。" },
    [
      { id: "p03-asset", label: "发现代码库", phase: "DESIGNING", surface: "work", tone: "attention", eyebrow: "需要一项访问决定", title: "已找到现有客户门户", summary: "Watt 已完成只读观察。要在此代码库生产，需要把它明确绑定到当前 Work。", workName: "改善客户门户反馈体验", workOutcome: "让用户更容易发现反馈处理进展。", assets: [{ name: "acme/customer-portal", role: "现有产品代码", state: "只读可用 · 等待绑定" }], attention: { contract: "decision", title: "允许当前 Work 使用此代码库？", body: "Watt 只会在已确认范围内创建隔离工作区，不会自动推送远端。", action: "绑定到这个 Work", consequence: "绑定后可以分析和生产候选修改；远端写入仍需另行授权。" }, scenarioIds: ["J23", "J25"], tensionIds: ["T11", "T12"] },
      { id: "p03-bound", label: "资产已绑定", phase: "DESIGNING", surface: "work", tone: "success", eyebrow: "代码库已准备好", title: "先改善反馈详情的状态说明", summary: "Watt 发现用户最困惑的是状态变化没有解释，建议先修正详情页。", workName: "改善客户门户反馈体验", workOutcome: "让用户更容易发现反馈处理进展。", recommendation: { title: "先解决状态解释", body: "为每次状态变化增加面向用户的原因与下一步。", rationale: "这是当前反馈中出现最多、改动边界也最清晰的问题。" }, assets: [{ name: "acme/customer-portal", role: "生产输入与目标", state: "已绑定 · 当前 Work 可读写隔离副本" }], scenarioIds: ["J23", "J31"], tensionIds: ["T09", "T11"] },
      { id: "p03-result", label: "修改结果预览", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "attention", eyebrow: "结果待你审阅", title: "状态变化现在说得更清楚", summary: "修改已通过检查，尚未写入目标分支。", workName: "改善客户门户反馈体验", workOutcome: "让用户更容易发现反馈处理进展。", result: { kind: "change", title: "反馈状态说明优化", summary: "详情页会解释当前状态、最近变化和用户下一步。", highlights: ["增加状态原因", "突出最近一次团队回复", "为关闭状态提供继续反馈入口"], checks: ["组件测试 18/18", "键盘操作通过", "现有详情路径无回归"], assets: ["acme/customer-portal · 6 个文件"], previewVariant: "diff" }, scenarioIds: ["J66", "J71"], tensionIds: ["T08", "T09"] },
    ],
  ),

  buildPack(
    { id: "P04", title: "一个结果跨越多个代码库", shortTitle: "多代码库", description: "以一个连贯结果呈现前端、API 和说明文档，并处理部分目标延迟收敛。", reviewReason: "验证多目标结果仍保持单一 Work 心智模型。" },
    [
      { id: "p04-plan", label: "跨目标计划", phase: "PLANNING", surface: "work", tone: "active", eyebrow: "三个资产，一个结果", title: "一起交付新的邀请流程", summary: "前端、身份 API 和接入说明需要作为一个整体通过验证。", workName: "团队邀请流程", workOutcome: "让小团队可以安全邀请并管理成员。", assets: [{ name: "watt-web", role: "邀请界面", state: "已绑定" }, { name: "identity-api", role: "邀请与权限接口", state: "已绑定" }, { name: "onboarding-guide", role: "用户说明", state: "已绑定" }], milestones: [{ label: "统一邀请契约", detail: "跨资产行为约定", state: "done" }, { label: "实现三个目标", detail: "保持版本兼容", state: "current" }, { label: "跨目标验证", detail: "整体结果通过后再审阅", state: "next" }], scenarioIds: ["J24", "J35"], tensionIds: ["T10", "T11"] },
      { id: "p04-preview", label: "聚合结果", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "attention", eyebrow: "一个结果，三个目标", title: "邀请流程已可整体审阅", summary: "Watt 将跨目标变化组织成一个用户结果，同时保留每个资产的影响。", workName: "团队邀请流程", workOutcome: "让小团队可以安全邀请并管理成员。", result: { kind: "multi", title: "团队邀请与成员权限", summary: "从发送邀请到成员加入和撤销访问，三个资产已形成一致行为。", highlights: ["邀请链接 24 小时失效", "成员权限在界面和 API 中一致", "说明文档覆盖管理员操作"], checks: ["跨代码库契约测试通过", "权限边界检查通过", "文档示例与 API 一致"], limitations: ["企业单点登录不在本次范围"], assets: ["watt-web · 9 个文件", "identity-api · 7 个文件", "onboarding-guide · 2 个文件"], previewVariant: "dashboard" }, scenarioIds: ["J67", "J68", "J71"], tensionIds: ["T08", "T10"] },
      { id: "p04-partial", label: "部分收敛", phase: "RECOVERING", surface: "work", tone: "warning", eyebrow: "Watt 正在安全收敛", title: "两个目标已更新，一个仍在确认", summary: "前端和文档已应用授权结果；API 目标发生外部变化，Watt 没有盲目覆盖。", workName: "团队邀请流程", workOutcome: "让小团队可以安全邀请并管理成员。", attention: { contract: "awareness", title: "暂时不需要你操作", body: "Watt 正重新观察 identity-api，并判断原授权是否仍允许向前完成。", consequence: "如果目标变化影响权限语义，Watt 会带着差异和选项回来请你决定。" }, assets: [{ name: "watt-web", role: "邀请界面", state: "已更新" }, { name: "identity-api", role: "邀请与权限接口", state: "外部变化 · 正在对账" }, { name: "onboarding-guide", role: "用户说明", state: "已更新" }], ownerFacts: { authority: "原授权只覆盖精确目标版本。", delivery: "完整交付尚未形成。" }, scenarioIds: ["J72"], tensionIds: ["T20"] },
    ],
  ),

  buildPack(
    { id: "P05", title: "容量不足时的生产体验", shortTitle: "容量等待", description: "两个 Work 竞争容量，用户能理解等待、启动、运行和阶段完成。", reviewReason: "验证 Queue 可见但不会把 Watt 变成队列管理器。" },
    [
      { id: "p05-home", label: "首页生产概览", phase: "QUEUED", surface: "home", tone: "active", eyebrow: "Watt 正在安排生产", title: "一个 Work 正在运行，另一个已经就绪", summary: "你无需调整队列。Watt 会在兼容容量释放后继续第二项工作。", changedSince: ["客户反馈门户已完成设计", "运营后台已开始内容工作台", "团队邀请流程等待验证"], production: { label: "2 项生产中 · 1 项等待", activity: "Watt 运营后台正在实现内容工作台", queueDetail: ["Watt 运营后台 · 正在运行", "客户反馈门户 · 等待容量", "团队邀请流程 · 等待验证"] }, scenarioIds: ["J40", "J58"], tensionIds: ["T02", "T06"] },
      { id: "p05-wait", label: "等待容量", phase: "WAITING_FOR_CAPACITY", surface: "work", tone: "neutral", eyebrow: "已就绪，正在等待", title: "客户反馈门户会在当前生产完成后开始", summary: "没有兼容容量可用。这是正常等待，不是失败，也不需要你处理。", workName: "客户反馈门户", workOutcome: "让早期用户反馈形成可跟踪闭环。", production: { label: "等待生产容量", activity: "所有准备工作已完成", reason: "当前容量正用于更早进入生产的运营后台", queueDetail: ["同一 Work 不会重复创建生产", "Watt 会自动开始", "没有可靠 ETA，因此不显示虚假时间"] }, attention: { contract: "handling", title: "Watt 会继续处理", body: "容量释放后会自动开始，并保留当前 Work 的全部上下文。" }, scenarioIds: ["J40", "J41", "J48"], tensionIds: ["T06", "T21"] },
      { id: "p05-start", label: "获得分配", phase: "RUNNING", surface: "work", tone: "active", eyebrow: "生产已经开始", title: "正在建立反馈浏览与提交", summary: "同一个阶段从等待转入执行，没有产生重复 Work 或阶段。", workName: "客户反馈门户", workOutcome: "让早期用户反馈形成可跟踪闭环。", production: { label: "正在生产", activity: "实现反馈列表、详情与提交流程", elapsed: "已运行 2 分钟" }, milestones: [{ label: "反馈门户", detail: "正在实现列表、详情和提交", state: "current" }, { label: "管理处理", detail: "下一阶段", state: "next" }, { label: "验证与交付", detail: "之后进行", state: "next" }], scenarioIds: ["J42", "J43", "J57"], tensionIds: ["T05", "T06"] },
      { id: "p05-next", label: "阶段完成", phase: "VERIFYING", surface: "work", tone: "success", eyebrow: "第一个阶段已完成", title: "反馈门户正在接受独立检查", summary: "完成一个有意义结果后，Watt 会先验证，再决定下一阶段。", workName: "客户反馈门户", workOutcome: "让早期用户反馈形成可跟踪闭环。", milestones: [{ label: "反馈门户", detail: "生产完成 · 正在验证", state: "done" }, { label: "管理处理", detail: "验证通过后开始", state: "current" }, { label: "验证与交付", detail: "最后进行", state: "next" }], scenarioIds: ["J59", "J61"], tensionIds: ["T05", "T14"] },
    ],
  ),

  buildPack(
    { id: "P06", title: "生产中断后自动恢复", shortTitle: "中断恢复", description: "展示检查点、中断、对账、重新入队和从保留前沿继续。", reviewReason: "验证故障不会把用户变成调试中转站。" },
    [
      { id: "p06-running", label: "正常生产", phase: "RUNNING", surface: "work", tone: "active", eyebrow: "Watt 正在生产", title: "正在实现内容工作台", summary: "当前活动清晰可见，用户可以离开页面。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, production: { label: "正在生产", activity: "完成内容资产与渠道关联", elapsed: "已运行 18 分钟" }, milestones: productionMilestones, scenarioIds: ["J43"], tensionIds: ["T05"] },
      { id: "p06-checkpoint", label: "检查点已保存", phase: "CHECKPOINTED", surface: "work", tone: "neutral", eyebrow: "进展已保存", title: "Watt 保存了一个可继续的工作位置", summary: "这不是最终结果，但意味着中断后无需从头开始。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, production: { label: "检查点已保存", activity: "内容模型和主界面已经持久保存", elapsed: "18 分钟" }, milestones: productionMilestones, scenarioIds: ["J44"], tensionIds: ["T18"] },
      { id: "p06-recover", label: "自动对账", phase: "RECOVERING", surface: "work", tone: "warning", eyebrow: "Watt 正在恢复", title: "执行环境意外中断，已保留有用进展", summary: "Watt 正在确认最后一次操作的实际影响；在确认前不会盲目重复。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, attention: { contract: "handling", title: "暂时不需要你处理", body: "Watt 已隔离不确定范围，正在从检查点和实际文件状态恢复。", consequence: "确认一致后会自动重新入队并继续。" }, production: { label: "正在对账", activity: "确认最后一次文件修改是否已完整保存", reason: "生产 worker 意外重启" }, ownerFacts: { executor: "原 Attempt 已中断；未知影响被 fence。", queue: "恢复完成前不会产生新执行。" }, scenarioIds: ["J51", "J52", "J84"], tensionIds: ["T18", "T22"] },
      { id: "p06-resume", label: "从前沿继续", phase: "RUNNING", surface: "work", tone: "success", eyebrow: "已经恢复", title: "Watt 从保存的位置继续生产", summary: "已确认进展完整，没有重复工作。恢复历史仍可在详情中查看。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, production: { label: "已恢复 · 正在生产", activity: "继续完成渠道关联", elapsed: "累计 21 分钟" }, milestones: productionMilestones, ownerFacts: { queue: "同一 PWU 已重新入队并获得分配。", executor: "新执行从兼容 checkpoint frontier 恢复。" }, scenarioIds: ["J46", "J47"], tensionIds: ["T17", "T18"] },
    ],
  ),

  buildPack(
    { id: "P07", title: "生产中纠正 Watt 的理解", shortTitle: "活跃 Work 纠正", description: "用户指出真正目标，Watt 接受纠正并安全处理对进行中生产的影响。", reviewReason: "验证纠正不触发辩解，重大变化也不会静默污染生产。" },
    [
      { id: "p07-running", label: "输入纠正", phase: "RUNNING", surface: "work", tone: "active", eyebrow: "当前生产仍在进行", title: "正在准备运营活动模板", summary: "用户可以在 Watt 工作时继续表达。", workName: "Watt 推广运营", workOutcome: "帮助团队持续推广 Watt。", messages: [{ actor: "human", text: "不对，我不是想设计运营活动，我是想开发一个运营管理后台。" }, { actor: "watt", text: "明白，是后台产品本身。当前正在准备的活动模板不应该继续作为主要方向。我会先把进行中的工作停在安全位置，再按“运营后台”重新整理影响和下一步。" }], production: { label: "正在停在安全位置", activity: "保存当前有用分析，停止扩展活动模板" }, scenarioIds: ["J05", "J30", "J37"], tensionIds: ["T16", "T18"] },
      { id: "p07-decision", label: "范围变化决定", phase: "WAITING_FOR_HUMAN", surface: "work", tone: "attention", eyebrow: "需要你确认新的目标", title: "这次纠正会改变当前 Work 的交付结果", summary: "Watt 已经停止不合适的方向，并保留仍有价值的渠道分析。", workName: "Watt 推广运营", workOutcome: "当前目标仍是运营活动方案，等待修订。", attention: { contract: "decision", title: "将当前 Work 改为开发运营后台？", body: "可复用渠道和用户背景；活动模板生产将结束，后续改为产品设计与开发。", action: "修订当前 Work", consequence: "目标、范围与交付形态会产生新版本；旧生产历史完整保留。" }, scenarioIds: ["J37", "J49"], tensionIds: ["T07", "T16"] },
      { id: "p07-revised", label: "采用新理解", phase: "DESIGNING", surface: "work", tone: "success", eyebrow: "目标已修订", title: "现在设计的是运营管理后台", summary: "渠道和用户背景继续有效，Watt 已把当前重点改为后台的日常工作流。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, recommendation: { title: "先做内容资产与渠道归因", body: "它们最直接支撑公众号、小红书与直播的长期运营。", rationale: "活动模板可以以后作为后台中的一项能力，而不是产品本身。" }, scenarioIds: ["J05", "J30", "J36"], tensionIds: ["T04", "T16"] },
    ],
  ),

  buildPack(
    { id: "P08", title: "重大范围变化需要治理", shortTitle: "范围变化", description: "生产中加入新能力时，Watt 解释影响并让用户决定继续、修订或新建 Work。", reviewReason: "验证权限边界清晰，但体验不像审批系统。" },
    [
      { id: "p08-change", label: "新需求到达", phase: "RUNNING", surface: "work", tone: "warning", eyebrow: "发现一项重大变化", title: "连接真实渠道账号会扩大当前生产边界", summary: "当前 Work 只授权构建后台和演示数据，尚未授权访问公众号或小红书账号。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, messages: [{ actor: "human", text: "顺便把公众号和小红书账号直接接上，能自动发内容。" }, { actor: "watt", text: "可以把它作为下一步，但这会引入外部账号权限和真实发布影响。我会保持当前后台生产不变，先把新增范围、权限和风险说明清楚。" }], scenarioIds: ["J37", "J39"], tensionIds: ["T07", "T16"] },
      { id: "p08-options", label: "治理选项", phase: "WAITING_FOR_HUMAN", surface: "work", tone: "attention", eyebrow: "需要你的方向决定", title: "后台可以先完成，渠道连接有三种处理方式", summary: "Watt 已把新需求与当前生产隔离，不会静默取得或使用账号权限。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, attention: { contract: "decision", title: "你希望怎样继续？", body: "推荐先完成后台，再把渠道连接作为同一 Work 的下一阶段。也可以暂停当前生产立即修订，或建立独立 Work。", action: "先完成后台，随后继续", consequence: "当前结果边界不变；交付后会形成新的权限审阅。" }, scenarioIds: ["J14", "J37", "J53"], tensionIds: ["T07", "T19"] },
      { id: "p08-resolved", label: "方向已确定", phase: "RUNNING", surface: "work", tone: "success", eyebrow: "当前生产继续", title: "先交付后台，再处理真实渠道连接", summary: "新方向已经保留，但不会影响当前已授权结果。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, production: { label: "正在生产", activity: "继续完成内容工作台", queueDetail: ["当前阶段：后台核心能力", "未来方向：真实渠道连接", "权限：尚未请求外部账号访问"] }, scenarioIds: ["J39", "J54"], tensionIds: ["T16"] },
    ],
  ),

  buildPack(
    { id: "P09", title: "验证发现问题后自行修正", shortTitle: "验证修正", description: "结果检查失败，Watt 在既有范围内完成修正并保留完整历史。", reviewReason: "验证用户能信任过程，却不用充当测试失败中转站。" },
    [
      { id: "p09-verify", label: "正在检查", phase: "VERIFYING", surface: "work", tone: "active", eyebrow: "正在独立检查结果", title: "验证真实运营路径", summary: "Watt 正检查内容创建、渠道关联和线索回流，不会把“已生成”说成“已完成”。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, milestones: productionMilestones.map((m, i) => ({ ...m, state: i < 3 ? "done" : "current" })), scenarioIds: ["J61"], tensionIds: ["T14"] },
      { id: "p09-failed", label: "发现缺陷", phase: "RECOVERING", surface: "work", tone: "warning", eyebrow: "发现一个问题，Watt 正在修正", title: "窄屏下渠道筛选会遮挡内容", summary: "问题在当前已准入范围内，Watt 已开始修正；你无需处理。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, attention: { contract: "awareness", title: "值得知道，但没有阻塞你", body: "原结果没有通过窄屏使用检查。失败结果和证据会保留，新修订将重新接受完整检查。" }, production: { label: "正在修正", activity: "调整窄屏筛选布局并补充交互测试" }, scenarioIds: ["J63"], tensionIds: ["T14", "T22"] },
      { id: "p09-pass", label: "修订通过", phase: "RESULT_READY", surface: "work", tone: "success", eyebrow: "修订结果已通过检查", title: "运营工作台已可预览", summary: "新版本修复窄屏问题；第一次失败仍保留在验证历史中。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, result: resultDashboard, scenarioIds: ["J62", "J63"], tensionIds: ["T08", "T14"] },
    ],
  ),

  buildPack(
    { id: "P10", title: "结果预览与精确授权", shortTitle: "预览与授权", description: "用户在授权前体验应用、理解变化和限制，并可要求修改或批准精确结果。", reviewReason: "验证最关键的信任与权限体验。" },
    [
      { id: "p10-result", label: "结果已就绪", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "attention", eyebrow: "结果待你审阅", title: "Watt 运营工作台已经可以体验", summary: "这是已通过检查的精确结果。尚未应用到交付目标。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, result: resultDashboard, ownerFacts: { verification: "12 项业务与体验检查通过。", authority: "当前结果尚未获得集成授权。" }, scenarioIds: ["J62", "J65", "J66", "J68"], tensionIds: ["T08", "T09", "T14"], transitions: [{ label: "查看完整预览", to: "p10-preview", kind: "primary" }, { label: "直接查看限制", to: "p10-limits", kind: "secondary" }] },
      { id: "p10-preview", label: "应用预览", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "active", eyebrow: "隔离预览 · 不会影响真实环境", title: "像真实用户一样体验结果", summary: "预览中的数据和动作都是模拟的；当前结果身份保持不变。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, result: resultDashboard, scenarioIds: ["J65", "J66"], tensionIds: ["T08"], transitions: [{ label: "继续审阅授权", to: "p10-limits", kind: "primary" }] },
      { id: "p10-limits", label: "限制与影响", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "attention", eyebrow: "授权前确认", title: "你将批准这个结果进入交付", summary: "会更新 Watt 托管代码库并创建可访问的静态 Web Runtime；不会连接真实渠道账号。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, result: resultDashboard, attention: { contract: "decision", title: "授权结果 2026.09.13-01", body: "你正在批准刚刚预览并通过 12 项检查的运营工作台。", action: "授权并准备交付", consequence: "更新托管代码库并创建运行交付；任何修订都需要重新审阅。" }, scenarioIds: ["J68", "J69", "J70", "J71"], tensionIds: ["T09", "T14"], transitions: [{ label: "授权并准备交付", to: "p10-authorized", kind: "primary" }, { label: "要求修改", to: "p10-result", kind: "secondary", hint: "当前结果会保持不变" }] },
      { id: "p10-authorized", label: "已精确授权", phase: "AUTHORIZED", surface: "work", tone: "success", eyebrow: "授权已记录", title: "Watt 正在准备可用交付", summary: "授权只适用于你刚刚审阅的结果和目标；后续修订不会继承这次授权。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, milestones: deliveryMilestones.map((m, i) => ({ ...m, state: i < 4 ? "done" : "current" })), ownerFacts: { authority: "精确 Candidate 结果与目标集合已授权。", delivery: "正在形成 Delivery manifest。" }, scenarioIds: ["J71", "J73"], tensionIds: ["T09", "T14"] },
    ],
  ),

  buildPack(
    { id: "P11", title: "已完成 Work 的回访与细化", shortTitle: "完成后细化", description: "Watt 在用户离开时完成交付；用户回来后快速理解变化并继续同一个 Work。", reviewReason: "验证回访首页、交付历史和 Re-entry 是一个连贯故事。" },
    [
      { id: "p11-home", label: "回访首页", phase: "DELIVERED", surface: "home", tone: "success", eyebrow: "欢迎回来", title: "Watt 在你离开后完成了两件事", summary: "运营后台已经交付，客户反馈门户完成了第一阶段；有一项结果值得你审阅。", changedSince: ["Watt 运营后台已通过检查并完成交付", "客户反馈门户已完成反馈浏览与提交", "团队邀请流程等待你的目标确认"], deliveries: [{ title: "Watt 运营工作台", form: "Web 应用", detail: "今天 14:32 交付", action: "打开应用", trust: "检查通过 · 已授权 · 运行一致", runtimeState: "aligned" }], attention: { contract: "decision", title: "团队邀请流程需要你的决定", body: "身份 API 的外部变化影响了原授权目标。", action: "查看差异" }, scenarioIds: ["J73", "J79", "J88"], tensionIds: ["T02", "T13"] },
      { id: "p11-delivery", label: "查看交付", phase: "COMPLETED", surface: "deliveries", tone: "success", eyebrow: "已交付", title: "Watt 运营工作台", summary: "内容、渠道和线索已经形成一个可用的运营闭环。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, deliveries: [{ title: "Watt 运营工作台 · 第一版", form: "可运行 Web 应用", detail: "包含源码、使用说明与 12 项验证结果", action: "打开应用", trust: "可信结果 · 活跃运行一致", runtimeState: "aligned" }, { title: "设计方案", form: "文档包", detail: "信息架构、业务规则与范围决定", action: "查看文档", trust: "随第一版交付保留" }], milestones: deliveryMilestones.map((m) => ({ ...m, state: "done" })), scenarioIds: ["J74", "J80"], tensionIds: ["T13", "T15"] },
      { id: "p11-reopen", label: "继续细化", phase: "REOPENED", surface: "work", tone: "active", eyebrow: "新的细化周期", title: "在已有成果上增加真实渠道连接", summary: "Watt 已恢复原 Work 的目标、交付与历史，并把新需求识别为同一结果的下一阶段。", workName: "Watt 运营后台", workOutcome: "在现有运营后台中安全连接真实渠道账号。", messages: [{ actor: "human", text: "第一版挺好，我们继续把公众号账号接上吧。" }, { actor: "watt", text: "可以，这属于同一个运营后台的后续细化。我会沿用已经交付的内容和渠道模型，但真实账号访问和发布权限需要单独确认。先从只读同步内容表现开始，会比直接自动发布更稳妥。" }], recommendation: { title: "先做只读数据同步", body: "先验证账号连接、数据映射和反馈闭环，再考虑自动发布。", rationale: "这样能尽早发现平台差异，同时把真实发布风险留到明确授权之后。" }, scenarioIds: ["J81", "J88"], tensionIds: ["T15", "T16"] },
    ],
  ),

  buildPack(
    { id: "P12", title: "真正需要用户处理的事项", shortTitle: "需要我处理", description: "从首页提醒进入准确 Work 上下文，理解原因、选项和后果。", reviewReason: "验证 Attention 是导航投影，不是审批收件箱。" },
    [
      { id: "p12-home", label: "首页提醒", phase: "WAITING_FOR_HUMAN", surface: "home", tone: "attention", eyebrow: "有 1 件事需要你决定", title: "真实渠道连接正在等你的访问选择", summary: "其他 Work 会继续进行。只有“渠道数据同步”这个阶段被阻塞。", attention: { contract: "decision", title: "选择公众号访问范围", body: "Watt 可以先只读同步内容表现，或在以后申请发布权限。", action: "查看并决定", consequence: "不作决定也不会影响已交付的运营后台。" }, scenarioIds: ["J25", "J49"], tensionIds: ["T07"] },
      { id: "p12-context", label: "准确上下文", phase: "WAITING_FOR_HUMAN", surface: "work", tone: "attention", eyebrow: "需要你的决定", title: "Watt 建议先授予只读数据访问", summary: "Watt 已完成账号发现与能力检查，没有尝试读取或发布真实内容。", workName: "Watt 运营后台 · 渠道连接", workOutcome: "把真实渠道表现带回运营工作台。", attention: { contract: "decision", title: "允许读取公众号内容表现？", body: "只读取文章标题、发布时间和表现数据；不创建、修改或发布内容。", action: "授权只读访问", consequence: "Watt 将验证数据映射并生成下一步方案；发布权限仍保持未授权。" }, assets: [{ name: "Watt 公众号", role: "渠道数据源", state: "已发现 · 等待只读授权" }], ownerFacts: { assets: "外部账号 capability 为 READ pending。", authority: "发布与写入能力不在当前决定中。" }, scenarioIds: ["J25", "J32", "J86"], tensionIds: ["T07", "T11"] },
      { id: "p12-resolved", label: "决定已处理", phase: "PLANNING", surface: "work", tone: "success", eyebrow: "只读访问已授权", title: "Watt 会先验证数据同步", summary: "当前路径已经恢复；下一次需要你时，会带着真实映射结果和明确影响回来。", workName: "Watt 运营后台 · 渠道连接", workOutcome: "把真实渠道表现带回运营工作台。", milestones: [{ label: "验证账号连接", detail: "只读能力已确认", state: "done" }, { label: "同步演示数据", detail: "当前方向", state: "current" }, { label: "审阅数据映射", detail: "下一步", state: "next" }], scenarioIds: ["J25", "J49"], tensionIds: ["T07", "T18"] },
    ],
  ),

  buildPack(
    { id: "P13", title: "对话分支与新 Motive 安全", shortTitle: "对话分支", description: "直接问答、纠正、无关插曲和新 Motive 不会污染当前 Work。", reviewReason: "验证 Conversation 是统一入口，但不拥有受治理事实。" },
    [
      { id: "p13-question", label: "Work 前直接问答", phase: "PRE_WORK", surface: "home", tone: "neutral", eyebrow: "普通问题", title: "先得到答案，不必创建 Work", summary: "Watt 会判断用户是在提问、探索还是准备形成持续 Work。", messages: [{ actor: "human", text: "设计方案的文档以后会放在哪里？" }, { actor: "watt", text: "它会保存在对应 Work 的交付与资产中，你可以从 Work 或交付历史随时打开。现在还没有形成 Work，所以不会编造一个路径或提前创建文件。" }], scenarioIds: ["J02"], tensionIds: ["T01"] },
      { id: "p13-correct", label: "纠正与插曲", phase: "REFINING", surface: "work", tone: "active", eyebrow: "原方向保持不变", title: "Watt 接受纠正，也能处理临时问题", summary: "无关问题不会成为当前 Work 的新范围。", workName: "Watt 运营后台（形成中）", messages: [{ actor: "human", text: "这里说错了，目标用户还包括独立设计师。顺便问一下，现在几点？" }, { actor: "watt", text: "收到，目标用户应包括个人开发者、小团队和独立设计师。我会采用这个新范围。关于时间，我无法从这个原型读取真实时钟；这个问题不会改变当前 Work。" }], scenarioIds: ["J05", "J13"], tensionIds: ["T16"] },
      { id: "p13-new", label: "识别新 Motive", phase: "REFINING", surface: "work", tone: "attention", eyebrow: "这是另一个目标", title: "招聘页面不会静默进入运营后台", summary: "Watt 建议另开一个 Work，并保留当前对话与设计。", workName: "Watt 运营后台（形成中）", attention: { contract: "decision", title: "开始一个新的 Work？", body: "“做一个招聘页面”与当前运营后台没有直接结果关系。", action: "新建招聘页面 Work", consequence: "当前运营后台保持不变，你可以随时回来。" }, scenarioIds: ["J10", "J14", "J15"], tensionIds: ["T16"] },
    ],
  ),

  buildPack(
    { id: "P14", title: "浏览器与消息连续性", shortTitle: "浏览器连续性", description: "Watt 回复时继续输入、切换 Work、断连再返回，消息和生产都保持一致。", reviewReason: "验证 UI 连续性不会污染 Turn 或重复生产。" },
    [
      { id: "p14-stream", label: "回复仍在生成", phase: "REFINING", surface: "work", tone: "active", eyebrow: "Watt 正在组织建议", title: "你可以继续输入", summary: "当前回复不会锁住 Composer；新消息会清楚地进入等待状态。", workName: "Watt 运营后台", messages: [{ actor: "human", text: "你建议下一步先设计什么？" }, { actor: "watt", text: "我建议先确定内容资产如何在三个渠道之间复用，因为这会影响后台结构、归因方式和日常工作流……" }, { actor: "human", text: "还要考虑直播回放的二次剪辑。", pending: true }], scenarioIds: ["J60"], tensionIds: ["T17"] },
      { id: "p14-away", label: "离开与断连", phase: "RUNNING", surface: "home", tone: "neutral", eyebrow: "连接短暂中断", title: "Watt 仍在继续当前工作", summary: "页面断连不会取消对话或生产。等待消息仍按原顺序保留。", changedSince: ["上一条回复已经完成", "关于直播回放的补充仍在等待处理", "运营后台生产不受页面连接影响"], attention: { contract: "handling", title: "正在重新连接", body: "Watt 会从最后确认的位置恢复页面，不会重复发送消息。" }, scenarioIds: ["J76", "J83"], tensionIds: ["T17"] },
      { id: "p14-back", label: "重连并继续", phase: "DESIGNING", surface: "work", tone: "success", eyebrow: "已恢复到最新状态", title: "直播回放已经进入内容复用设计", summary: "消息顺序、当前 Work 和生产状态都与离开前一致。", workName: "Watt 运营后台", messages: [{ actor: "watt", text: "我建议先确定内容资产的复用模型。公众号长文、笔记素材和直播回放都可以从一份核心内容拆分，但需要保留来源和渠道表现。" }, { actor: "human", text: "还要考虑直播回放的二次剪辑。" }, { actor: "watt", text: "会纳入。直播回放应作为核心内容资产，短视频切片和图文摘要作为衍生版本，这样复用和归因都更清楚。" }], scenarioIds: ["J60", "J83", "J87"], tensionIds: ["T17", "T19"] },
    ],
  ),

  buildPack(
    { id: "P15", title: "资产丢失与过期 Reality", shortTitle: "资产与过期状态", description: "代码库外部变化、决策界面过期和权限丢失都会得到安全、可理解的处理。", reviewReason: "验证 Watt 先重新观察，不会盲目覆盖或把用户送去调试。" },
    [
      { id: "p15-stale", label: "外部变化", phase: "RECOVERING", surface: "work", tone: "warning", eyebrow: "目标代码刚刚发生变化", title: "这个授权界面已经过期", summary: "另一项修改已进入目标分支。Watt 已阻止使用旧依据继续。", workName: "改善客户门户反馈体验", attention: { contract: "handling", title: "Watt 正在重新比较", body: "不会覆盖外部变化，也不会重复应用已经存在的修改。" }, assets: [{ name: "acme/customer-portal", role: "生产目标", state: "外部变化 · 正在重新观察" }], scenarioIds: ["J27", "J87"], tensionIds: ["T18", "T19"] },
      { id: "p15-lost", label: "权限丢失", phase: "WAITING_FOR_HUMAN", surface: "work", tone: "attention", eyebrow: "需要恢复资产访问", title: "Watt 已完成比较，但当前无法写入目标", summary: "候选结果和验证证据都已保留。只有目标写入被阻塞。", workName: "改善客户门户反馈体验", attention: { contract: "decision", title: "重新授权或改用托管代码库", body: "读取仍可用，写入权限已经失效。", action: "重新授权写入", consequence: "Watt 会再次核对目标 revision 后呈现新的精确授权；也可以交付到 Watt 托管代码库。" }, assets: [{ name: "acme/customer-portal", role: "生产目标", state: "可读 · 写入权限失效" }], scenarioIds: ["J50", "J86"], tensionIds: ["T11", "T19"] },
      { id: "p15-safe", label: "安全替代路径", phase: "READY_FOR_AUTHORIZATION", surface: "work", tone: "success", eyebrow: "结果已转到托管交付", title: "无需等待外部权限也能继续审阅", summary: "Watt 在新的托管目标上重新验证了同等结果，原代码库保持不变。", workName: "改善客户门户反馈体验", result: { kind: "change", title: "反馈状态说明优化", summary: "完整结果已保存到 Watt 托管代码库，可下载或稍后再集成。", highlights: ["保留外部最新变化", "重新应用兼容修改", "生成独立交付"], checks: ["重放后行为一致", "未写入外部代码库"], assets: ["Watt 托管代码库"], previewVariant: "diff" }, scenarioIds: ["J26", "J86", "J87"], tensionIds: ["T11", "T12"] },
    ],
  ),

  buildPack(
    { id: "P16", title: "交付与运行状态不一致", shortTitle: "交付信任差异", description: "交付已经可信，但活跃 Runtime 仍是旧版本；用户能准确理解现状和下一步。", reviewReason: "验证信任叙事不会把不同事实压成一个绿色状态。" },
    [
      { id: "p16-delivery", label: "可信交付", phase: "DELIVERED", surface: "deliveries", tone: "success", eyebrow: "交付已经形成", title: "Watt 运营工作台 · 第一版", summary: "结果已通过检查、获得精确授权，并进入可信代码库基线。", workName: "Watt 运营后台", deliveries: [{ title: "Watt 运营工作台", form: "Web 应用与源码", detail: "版本 2026.09.13-01", action: "查看交付", trust: "检查通过 · 已授权 · 可信基线已更新", runtimeState: "different" }], scenarioIds: ["J62", "J71", "J73"], tensionIds: ["T13", "T14"] },
      { id: "p16-mismatch", label: "运行仍是旧版本", phase: "WAITING_FOR_HUMAN", surface: "deliveries", tone: "warning", eyebrow: "交付可用，线上尚未切换", title: "当前运行环境仍是上一版", summary: "可信交付没有问题；切换活跃 Runtime 是另一项有影响的动作。", workName: "Watt 运营后台", attention: { contract: "decision", title: "现在切换到新版本？", body: "新交付已通过检查。当前线上仍稳定运行旧版本。", action: "切换活跃版本", consequence: "运行入口将指向刚刚审阅的交付；如果启动检查失败，会保持旧版本并报告。" }, deliveries: [{ title: "新交付", form: "版本 2026.09.13-01", detail: "已可信，等待运行切换", action: "打开隔离预览", trust: "可信基线：新版本", runtimeState: "different" }, { title: "当前运行", form: "版本 2026.09.06-02", detail: "仍在为用户提供服务", action: "查看当前运行", trust: "活跃 Runtime：旧版本", runtimeState: "aligned" }], scenarioIds: ["J68", "J73", "J74"], tensionIds: ["T13", "T14"] },
      { id: "p16-aligned", label: "运行已一致", phase: "COMPLETED", surface: "deliveries", tone: "success", eyebrow: "交付与运行已经一致", title: "Watt 运营工作台现在可以正式使用", summary: "新版本启动检查通过；旧交付和切换历史仍然可查。", workName: "Watt 运营后台", workOutcome: opsUnderstanding.objective, deliveries: [{ title: "Watt 运营工作台", form: "Web 应用与源码", detail: "版本 2026.09.13-01 · 当前运行", action: "打开应用", trust: "检查通过 · 已授权 · 已交付 · 运行一致", runtimeState: "aligned" }], milestones: deliveryMilestones.map((m) => ({ ...m, state: "done" })), scenarioIds: ["J73", "J74", "J80"], tensionIds: ["T13", "T14", "T20"] },
    ],
  ),
];

export function getPack(packId: string): ScenarioPack {
  return scenarioPacks.find((pack) => pack.id === packId) ?? scenarioPacks[0];
}

export function getScene(pack: ScenarioPack, sceneId: string): Scene {
  return pack.scenes.find((scene) => scene.id === sceneId) ?? pack.scenes[0];
}

export function cloneSeed(pack: ScenarioPack): Scene {
  return structuredClone(getScene(pack, pack.seed));
}
