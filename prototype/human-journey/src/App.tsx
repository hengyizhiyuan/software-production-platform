import { FormEvent, ReactNode, useEffect, useMemo, useReducer, useState } from "react";
import { getPack, getScene, scenarioPacks } from "./scenarios";
import type {
  AttentionFact,
  DeliveryFact,
  Message,
  Milestone,
  ResultFact,
  ScenarioPack,
  Scene,
  Surface,
  Tone,
  Transition,
} from "./types";

type IconName =
  | "home"
  | "work"
  | "delivery"
  | "spark"
  | "check"
  | "clock"
  | "arrow"
  | "chevron"
  | "close"
  | "sliders"
  | "layers"
  | "shield"
  | "asset"
  | "message"
  | "play"
  | "refresh"
  | "info"
  | "pause";

const icons: Record<IconName, ReactNode> = {
  home: <><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v10h13V10"/><path d="M9.5 20v-6h5v6"/></>,
  work: <><rect x="3" y="5" width="18" height="15" rx="3"/><path d="M8 5V3h8v2M3 11h18"/></>,
  delivery: <><path d="M5 8h14l1 12H4L5 8Z"/><path d="M9 8V5a3 3 0 0 1 6 0v3"/></>,
  spark: <><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z"/><path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  arrow: <><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  sliders: <><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></>,
  layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
  shield: <><path d="M12 3 5 6v5c0 4.6 2.8 8.2 7 10 4.2-1.8 7-5.4 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/></>,
  asset: <><path d="M4 4h6l2 3h8v13H4V4Z"/><path d="M4 9h16"/></>,
  message: <path d="M4 5h16v11H9l-5 4V5Z"/>,
  play: <path d="m9 6 9 6-9 6V6Z"/>,
  refresh: <><path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M18 12a6 6 0 0 0-10.3-4.2L4 12M6 12a6 6 0 0 0 10.3 4.2L20 12"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>,
  pause: <><path d="M9 7v10M15 7v10"/></>,
};

function Icon({ name, size = 19 }: { name: IconName; size?: number }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[name]}</svg>;
}

const surfaceMeta: Record<Surface, { label: string; icon: IconName }> = {
  home: { label: "首页", icon: "home" },
  work: { label: "Work", icon: "work" },
  deliveries: { label: "交付", icon: "delivery" },
};

interface AppState {
  packId: string;
  sceneId: string;
  surface: Surface;
  reviewerOpen: boolean;
  productionOpen: boolean;
  evidenceOpen: boolean;
  previewOpen: boolean;
}

type AppAction =
  | { type: "select-pack"; pack: ScenarioPack }
  | { type: "select-scene"; pack: ScenarioPack; scene: Scene }
  | { type: "navigate"; surface: Surface }
  | { type: "transition"; pack: ScenarioPack; target: string }
  | { type: "reset"; pack: ScenarioPack }
  | { type: "toggle-reviewer" }
  | { type: "toggle-production" }
  | { type: "toggle-evidence" }
  | { type: "toggle-preview" };

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "select-pack": {
      const scene = getScene(action.pack, action.pack.seed);
      return { ...state, packId: action.pack.id, sceneId: scene.id, surface: scene.surface, productionOpen: false, evidenceOpen: false, previewOpen: false };
    }
    case "select-scene":
      return { ...state, packId: action.pack.id, sceneId: action.scene.id, surface: action.scene.surface, productionOpen: false, evidenceOpen: false, previewOpen: false };
    case "navigate": return { ...state, surface: action.surface };
    case "transition": {
      const scene = getScene(action.pack, action.target);
      return { ...state, sceneId: scene.id, surface: scene.surface, productionOpen: false, evidenceOpen: false, previewOpen: scene.id.endsWith("preview") };
    }
    case "reset": {
      const scene = getScene(action.pack, action.pack.seed);
      return { ...state, sceneId: scene.id, surface: scene.surface, productionOpen: false, evidenceOpen: false, previewOpen: false };
    }
    case "toggle-reviewer": return { ...state, reviewerOpen: !state.reviewerOpen };
    case "toggle-production": return { ...state, productionOpen: !state.productionOpen };
    case "toggle-evidence": return { ...state, evidenceOpen: !state.evidenceOpen };
    case "toggle-preview": return { ...state, previewOpen: !state.previewOpen };
  }
}

function readHash(): { packId: string; sceneId?: string } {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  return { packId: params.get("pack") ?? "P01", sceneId: params.get("scene") ?? undefined };
}

function initialState(): AppState {
  const hash = readHash();
  const pack = getPack(hash.packId);
  const scene = getScene(pack, hash.sceneId ?? pack.seed);
  return { packId: pack.id, sceneId: scene.id, surface: scene.surface, reviewerOpen: false, productionOpen: false, evidenceOpen: false, previewOpen: scene.id.endsWith("preview") };
}

const phaseLabels: Record<Scene["phase"], string> = {
  PRE_WORK: "尚未形成 Work", REFINING: "正在理解", READY_FOR_WORK: "目标待确认", DESIGNING: "正在形成方案", PLANNING: "准备生产", QUEUED: "已就绪", WAITING_FOR_CAPACITY: "等待生产容量", RUNNING: "正在生产", CHECKPOINTED: "进展已保存", PAUSED: "已暂停", RECOVERING: "正在恢复", WAITING_FOR_HUMAN: "需要你的决定", VERIFYING: "正在验证", RESULT_READY: "结果已就绪", READY_FOR_AUTHORIZATION: "结果待审阅", AUTHORIZED: "已授权", DELIVERED: "已交付", COMPLETED: "当前目标已完成", REOPENED: "继续细化",
};

export function App() {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const pack = useMemo(() => getPack(state.packId), [state.packId]);
  const scene = useMemo(() => getScene(pack, state.sceneId), [pack, state.sceneId]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    const next = `pack=${pack.id}&scene=${scene.id}`;
    if (window.location.hash.slice(1) !== next) window.history.replaceState(null, "", `#${next}`);
  }, [pack.id, scene.id]);

  useEffect(() => {
    const onHash = () => {
      const hash = readHash();
      const nextPack = getPack(hash.packId);
      const nextScene = getScene(nextPack, hash.sceneId ?? nextPack.seed);
      dispatch({ type: "select-scene", pack: nextPack, scene: nextScene });
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const move = (transition: Transition) => {
    dispatch({ type: "transition", pack, target: transition.to });
    setToast(transition.hint ?? "模拟状态已推进");
    window.setTimeout(() => setToast(""), 1800);
  };

  return (
    <div className={`app tone-${scene.tone}`}>
      <header className="topbar">
        <button className="brand" onClick={() => dispatch({ type: "navigate", surface: "home" })} aria-label="返回 Watt 首页">
          <span className="brand-mark"><Icon name="spark" size={18} /></span>
          <span>Watt</span>
        </button>
        <nav className="primary-nav" aria-label="主导航">
          {(Object.keys(surfaceMeta) as Surface[]).map((surface) => (
            <button key={surface} className={state.surface === surface ? "active" : ""} onClick={() => dispatch({ type: "navigate", surface })}>
              <Icon name={surfaceMeta[surface].icon} size={17} />
              {surfaceMeta[surface].label}
            </button>
          ))}
        </nav>
        <div className="top-actions">
          <span className="simulation-badge"><span />Watt Experience Prototype — simulated data</span>
          <button className="icon-button reviewer-trigger" onClick={() => dispatch({ type: "toggle-reviewer" })} aria-label="打开评审模式"><Icon name="sliders" /></button>
        </div>
      </header>

      <main className="main-shell">
        <ContextRail pack={pack} scene={scene} surface={state.surface} onNavigate={(surface) => dispatch({ type: "navigate", surface })} />
        <section className="content-area">
          {state.surface === "home" && <HomeSurface scene={scene} pack={pack} onOpenWork={() => dispatch({ type: "navigate", surface: "work" })} onMove={move} onProduction={() => dispatch({ type: "toggle-production" })} />}
          {state.surface === "work" && <WorkSurface scene={scene} pack={pack} onMove={move} onProduction={() => dispatch({ type: "toggle-production" })} onEvidence={() => dispatch({ type: "toggle-evidence" })} onPreview={() => dispatch({ type: "toggle-preview" })} />}
          {state.surface === "deliveries" && <DeliveriesSurface scene={scene} onMove={move} onWork={() => dispatch({ type: "navigate", surface: "work" })} />}
        </section>
      </main>

      {state.productionOpen && <ProductionDrawer scene={scene} onClose={() => dispatch({ type: "toggle-production" })} />}
      {state.evidenceOpen && <EvidenceDrawer scene={scene} onClose={() => dispatch({ type: "toggle-evidence" })} />}
      {state.previewOpen && scene.result && <PreviewOverlay result={scene.result} onClose={() => dispatch({ type: "toggle-preview" })} />}
      {state.reviewerOpen && <ReviewerPanel pack={pack} scene={scene} onClose={() => dispatch({ type: "toggle-reviewer" })} onPack={(next) => dispatch({ type: "select-pack", pack: next })} onScene={(next) => dispatch({ type: "select-scene", pack, scene: next })} onReset={() => dispatch({ type: "reset", pack })} onAdvance={() => scene.transitions[0] && move(scene.transitions[0])} />}
      {toast && <div className="toast"><Icon name="check" size={16} />{toast}</div>}
    </div>
  );
}

function ContextRail({ pack, scene, surface, onNavigate }: { pack: ScenarioPack; scene: Scene; surface: Surface; onNavigate: (surface: Surface) => void }) {
  return (
    <aside className="context-rail">
      <div className="rail-heading"><span className="rail-kicker">当前体验</span><strong>{pack.shortTitle}</strong></div>
      <div className="rail-phase"><span className={`status-orb ${scene.tone}`} /><div><small>当前状态</small><span>{phaseLabels[scene.phase]}</span></div></div>
      {scene.workName ? (
        <button className={`rail-work ${surface === "work" ? "selected" : ""}`} onClick={() => onNavigate("work")}>
          <span className="mini-icon"><Icon name="work" size={16} /></span><span><small>当前 Work</small><strong>{scene.workName}</strong></span><Icon name="chevron" size={15} />
        </button>
      ) : <div className="rail-empty"><Icon name="message" size={18} /><span>先从一次自然对话开始，不会自动创建 Work。</span></div>}
      <div className="rail-divider" />
      <button className="rail-secondary" onClick={() => onNavigate("home")}><Icon name="clock" size={16} />最近变化</button>
      <button className="rail-secondary" onClick={() => onNavigate("deliveries")}><Icon name="delivery" size={16} />交付历史</button>
      <div className="rail-foot">场景 {pack.id} · {pack.scenes.findIndex((item) => item.id === scene.id) + 1}/{pack.scenes.length}</div>
    </aside>
  );
}

function SurfaceHeader({ scene, trailing }: { scene: Scene; trailing?: ReactNode }) {
  return <div className="surface-header"><div><span className="eyebrow">{scene.eyebrow}</span><h1>{scene.title}</h1><p>{scene.summary}</p></div>{trailing}</div>;
}

function HomeSurface({ scene, pack, onOpenWork, onMove, onProduction }: { scene: Scene; pack: ScenarioPack; onOpenWork: () => void; onMove: (t: Transition) => void; onProduction: () => void }) {
  const isNew = scene.phase === "PRE_WORK" && !scene.messages?.length;
  const [starterPrompt, setStarterPrompt] = useState("");
  const primaryTransition = scene.transitions[0];
  return (
    <div className={`surface home-surface ${isNew ? "new-user" : ""}`}>
      <SurfaceHeader scene={scene} trailing={!isNew && <button className="soft-button" onClick={onProduction}><Icon name="layers" size={16} />生产动态</button>} />
      {isNew ? (
        <div className="motive-hero">
          <div className="motive-glow" />
          <Composer placeholder="比如：我想做一个能帮助 Watt 推广的运营后台……" featured suggestion={starterPrompt} onSend={() => primaryTransition && onMove(primaryTransition)} />
          <div className="starter-row"><span>也可以从这里开始</span><button onClick={() => setStarterPrompt("我有个还比较模糊的想法，想请你先帮我理清楚。")}>梳理一个模糊想法</button><button onClick={() => setStarterPrompt("我想改进一个已有产品，先帮我判断最值得解决的问题。")}>改进已有产品</button><button onClick={() => setStarterPrompt("我想先问你一个问题，再决定是否形成正式的 Work。")}>直接问 Watt</button></div>
          <SceneActions transitions={scene.transitions} onMove={onMove} />
        </div>
      ) : (
        <div className="home-grid">
          <div className="home-main">
            {scene.attention && <AttentionCard attention={scene.attention} onAction={() => primaryTransition && onMove(primaryTransition)} />}
            {scene.changedSince && <ChangedCard items={scene.changedSince} />}
            {scene.messages && <Conversation messages={scene.messages} compact />}
            <div className="active-work-card" onClick={onOpenWork} role="button" tabIndex={0}>
              <div className="card-top"><span className="mini-icon violet"><Icon name="work" size={17} /></span><span className="card-kicker">可以继续</span><Icon name="chevron" size={18} /></div>
              <h3>{scene.workName ?? "Watt 运营后台"}</h3>
              <p>{scene.workOutcome ?? "把内容、渠道和用户反馈形成持续运营闭环。"}</p>
              <span className="inline-status"><span className={`status-orb ${scene.tone}`} />{phaseLabels[scene.phase]}</span>
            </div>
          </div>
          <div className="home-side">
            {scene.production && <ProductionCard production={scene.production} onOpen={onProduction} />}
            {scene.deliveries && <DeliveryList deliveries={scene.deliveries} compact onAction={() => primaryTransition && onMove(primaryTransition)} />}
            <div className="quiet-card"><Icon name="spark" /><div><strong>Watt 会继续照看这些工作</strong><p>只有真正需要你的判断时，才会明确提出。</p></div></div>
          </div>
          <SceneActions transitions={scene.transitions} onMove={onMove} />
        </div>
      )}
      <div className="scenario-caption">{pack.reviewReason}</div>
    </div>
  );
}

function WorkSurface({ scene, pack, onMove, onProduction, onEvidence, onPreview }: { scene: Scene; pack: ScenarioPack; onMove: (t: Transition) => void; onProduction: () => void; onEvidence: () => void; onPreview: () => void }) {
  const primaryTransition = scene.transitions[0];
  return (
    <div className="surface work-surface">
      <SurfaceHeader scene={scene} trailing={<div className="header-actions"><span className={`phase-pill ${scene.tone}`}><span className={`status-orb ${scene.tone}`} />{phaseLabels[scene.phase]}</span>{scene.production && <button className="icon-button" onClick={onProduction} aria-label="查看生产详情"><Icon name="layers" /></button>}</div>} />
      {scene.workOutcome && <div className="outcome-strip"><span>当前结果目标</span><strong>{scene.workOutcome}</strong></div>}
      <div className="work-grid">
        <div className="work-primary">
          {scene.attention && <AttentionCard attention={scene.attention} onAction={() => primaryTransition && onMove(primaryTransition)} />}
          {scene.understanding && <FormationReview value={scene.understanding} />}
          {scene.recommendation && <RecommendationCard value={scene.recommendation} />}
          {scene.result && <ResultCard result={scene.result} onPreview={onPreview} onEvidence={onEvidence} />}
          {scene.production && <ProductionCard production={scene.production} onOpen={onProduction} />}
          {scene.milestones && <MilestoneCard milestones={scene.milestones} />}
          {scene.deliveries && <DeliveryList deliveries={scene.deliveries} onAction={() => primaryTransition && onMove(primaryTransition)} />}
          {scene.assets && <AssetsCard assets={scene.assets} />}
          <SceneActions transitions={scene.transitions} onMove={onMove} />
        </div>
        <aside className="conversation-column">
          <div className="column-title"><div><Icon name="message" size={17} /><strong>与 Watt 对话</strong></div><span>上下文会持续保留</span></div>
          <Conversation messages={scene.messages ?? defaultConversation(scene)} />
          <Composer placeholder="继续补充、纠正，或直接问 Watt……" />
        </aside>
      </div>
      <div className="work-meta"><span>{pack.id} · {scene.label}</span><button onClick={onEvidence}>查看事实来源与工程详情 <Icon name="chevron" size={14} /></button></div>
    </div>
  );
}

function DeliveriesSurface({ scene, onMove, onWork }: { scene: Scene; onMove: (t: Transition) => void; onWork: () => void }) {
  const deliveries = scene.deliveries ?? [{ title: "Watt 运营工作台", form: "Web 应用", detail: "最近交付 · 演示数据", action: "打开交付", trust: "检查通过 · 已授权", runtimeState: "aligned" as const }];
  const primaryTransition = scene.transitions[0];
  return <div className="surface deliveries-surface"><SurfaceHeader scene={{ ...scene, eyebrow: scene.surface === "deliveries" ? scene.eyebrow : "你的可用成果", title: scene.surface === "deliveries" ? scene.title : "交付", summary: scene.surface === "deliveries" ? scene.summary : "查看已经真正形成的结果，以及它们与 Work 的关系。" }} trailing={<button className="soft-button" onClick={onWork}><Icon name="work" size={16} />返回相关 Work</button>} />{scene.attention && <AttentionCard attention={scene.attention} onAction={() => primaryTransition && onMove(primaryTransition)} />}<DeliveryList deliveries={deliveries} onAction={() => primaryTransition ? onMove(primaryTransition) : onWork()} />{scene.milestones && <MilestoneCard milestones={scene.milestones} />}<SceneActions transitions={scene.transitions} onMove={onMove} /></div>;
}

function defaultConversation(scene: Scene): Message[] {
  if (scene.phase === "READY_FOR_WORK") return [{ actor: "watt", text: "我已经把我们讨论的目标整理成可审阅的 Work。你可以继续补充，也可以按这个理解正式继续。" }];
  if (scene.phase === "RUNNING") return [{ actor: "watt", text: "我正在按当前目标继续生产。你可以随时补充信息；如果它会改变范围，我会先说明影响。" }];
  if (scene.phase === "READY_FOR_AUTHORIZATION") return [{ actor: "watt", text: "结果已经通过必要检查。你可以先体验和查看限制，再决定是否授权。" }];
  return [{ actor: "watt", text: "我会保留当前 Work 的目标和约束。你可以直接说想补充或改变什么。" }];
}

function Composer({ placeholder, featured = false, suggestion = "", onSend }: { placeholder: string; featured?: boolean; suggestion?: string; onSend?: (value: string) => void }) {
  const [value, setValue] = useState("");
  const [sent, setSent] = useState(false);
  useEffect(() => {
    if (suggestion) setValue(suggestion);
  }, [suggestion]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim()) return;
    const submitted = value.trim();
    setSent(true); setValue("");
    window.setTimeout(() => setSent(false), 1800);
    onSend?.(submitted);
  };
  return <form className={`composer ${featured ? "featured" : ""}`} onSubmit={submit}><textarea value={value} onChange={(event) => setValue(event.target.value)} placeholder={placeholder} rows={featured ? 3 : 2} aria-label="给 Watt 发消息" /><div className="composer-footer"><span>{sent ? "已加入当前对话 · 模拟" : "Watt 会结合当前上下文回应"}</span><button type="submit" disabled={!value.trim()} aria-label="发送消息"><Icon name="arrow" size={18} /></button></div></form>;
}

function Conversation({ messages, compact = false }: { messages: Message[]; compact?: boolean }) {
  if (!messages.length) return null;
  return <div className={`conversation ${compact ? "compact" : ""}`}>{messages.map((message, index) => <div className={`message ${message.actor} ${message.pending ? "pending" : ""}`} key={`${message.actor}-${index}`}><div className="avatar">{message.actor === "watt" ? <Icon name="spark" size={14} /> : "你"}</div><div><span className="speaker">{message.actor === "watt" ? "Watt" : "你"}{message.pending && <em>等待发送</em>}</span><p>{message.text}</p></div></div>)}</div>;
}

function SceneActions({ transitions, onMove }: { transitions: Transition[]; onMove: (t: Transition) => void }) {
  if (!transitions.length) return <div className="end-state"><Icon name="check" size={17} /><span>此场景路径已走完。你可以打开评审模式切换场景或重置。</span></div>;
  return <div className="scene-actions">{transitions.map((transition) => <button key={`${transition.label}-${transition.to}`} className={`action-button ${transition.kind ?? "primary"}`} onClick={() => onMove(transition)}>{transition.label}<Icon name={transition.kind === "secondary" ? "chevron" : "arrow"} size={16} /></button>)}</div>;
}

function AttentionCard({ attention, onAction }: { attention: AttentionFact; onAction?: () => void }) {
  const labels = { handling: "Watt 正在处理", awareness: "值得知道", decision: "需要你的决定" };
  const icon: IconName = attention.contract === "decision" ? "spark" : attention.contract === "handling" ? "refresh" : "info";
  return <section className={`attention-card ${attention.contract}`}><div className="attention-icon"><Icon name={icon} /></div><div className="attention-copy"><span className="card-kicker">{labels[attention.contract]}</span><h2>{attention.title}</h2><p>{attention.body}</p>{attention.consequence && <div className="consequence"><strong>接下来</strong>{attention.consequence}</div>}{attention.action && <button className="inline-action" onClick={onAction}>{attention.action}<Icon name="chevron" size={15} /></button>}</div></section>;
}

function FormationReview({ value }: { value: NonNullable<Scene["understanding"]> }) {
  return <section className="formation-card"><div className="section-heading"><div><span className="card-kicker">Work 形成审阅</span><h2>Watt 对目标的当前理解</h2></div><span className="soft-tag">尚未创建 Work</span></div><div className="objective-block"><span>想实现的结果</span><strong>{value.objective}</strong></div><div className="formation-grid"><ListBlock title="主要范围" items={value.scope} /><ListBlock title="重要约束" items={value.constraints} /></div><div className="formation-foot"><div><span>预期交付</span><strong>{value.deliverable}</strong></div><div><span>当前边界</span><p>{value.boundary}</p></div></div></section>;
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return <div className="list-block"><span>{title}</span><ul>{items.map((item) => <li key={item}><Icon name="check" size={14} />{item}</li>)}</ul></div>;
}

function RecommendationCard({ value }: { value: NonNullable<Scene["recommendation"]> }) {
  return <section className="recommendation-card"><div className="recommendation-mark"><Icon name="spark" /></div><div><span className="card-kicker">Watt 的建议</span><h2>{value.title}</h2><p className="recommendation-body">{value.body}</p><div className="rationale"><strong>为什么这样建议</strong><p>{value.rationale}</p></div>{value.alternatives && <details><summary>查看其他可行方向</summary><ul>{value.alternatives.map((item) => <li key={item}>{item}</li>)}</ul></details>}</div></section>;
}

function MilestoneCard({ milestones }: { milestones: Milestone[] }) {
  return <section className="milestone-card"><div className="section-heading"><div><span className="card-kicker">有意义的进展</span><h2>从结果看进度</h2></div><span className="soft-tag">不使用虚假百分比</span></div><div className="milestone-list">{milestones.map((item, index) => <div className={`milestone ${item.state}`} key={`${item.label}-${index}`}><div className="milestone-line"><span>{item.state === "done" ? <Icon name="check" size={14} /> : index + 1}</span></div><div><strong>{item.label}</strong><p>{item.detail}</p></div><em>{item.state === "done" ? "已完成" : item.state === "current" ? "当前" : item.state === "blocked" ? "等待决定" : "下一步"}</em></div>)}</div></section>;
}

function ProductionCard({ production, onOpen }: { production: NonNullable<Scene["production"]>; onOpen: () => void }) {
  return <section className="production-card"><div className="production-pulse"><span /><span /><span /></div><div className="production-copy"><span className="card-kicker">生产状态</span><h2>{production.label}</h2><p>{production.activity}</p>{production.reason && <div className="reason"><Icon name="clock" size={16} /><span>{production.reason}</span></div>}</div><div className="production-side">{production.elapsed && <span>{production.elapsed}</span>}<button onClick={onOpen}>查看生产详情<Icon name="chevron" size={14} /></button></div></section>;
}

function AssetsCard({ assets }: { assets: NonNullable<Scene["assets"]> }) {
  return <section className="assets-card"><div className="section-heading"><div><span className="card-kicker">当前 Work 的资产</span><h2>相关材料与目标</h2></div><Icon name="asset" /></div><div className="asset-list">{assets.map((asset) => <div className="asset-row" key={asset.name}><span className="mini-icon"><Icon name="asset" size={16} /></span><div><strong>{asset.name}</strong><p>{asset.role}</p></div><em>{asset.state}</em></div>)}</div></section>;
}

function ResultCard({ result, onPreview, onEvidence }: { result: ResultFact; onPreview: () => void; onEvidence: () => void }) {
  return <section className="result-card"><div className="result-preview-mini"><MockPreview variant={result.previewVariant ?? "dashboard"} /></div><div className="result-copy"><span className="card-kicker">可以审阅的结果</span><h2>{result.title}</h2><p>{result.summary}</p><ul className="highlight-list">{result.highlights.map((item) => <li key={item}><Icon name="check" size={15} />{item}</li>)}</ul><div className="result-actions"><button className="action-button primary" onClick={onPreview}><Icon name="play" size={16} />打开完整预览</button><button className="action-button secondary" onClick={onEvidence}>查看检查与影响</button></div></div></section>;
}

function MockPreview({ variant }: { variant: NonNullable<ResultFact["previewVariant"]> }) {
  if (variant === "diff") return <div className="mock-diff"><div className="mock-window-bar"><i /><i /><i /></div><div><span className="minus">−</span><code>状态：处理中</code></div><div><span className="plus">+</span><code>正在处理 · 预计下一步由团队回复</code></div><div><span className="plus">+</span><code>最近更新：已确认问题影响范围</code></div></div>;
  return <div className={`mock-app ${variant}`}><div className="mock-window-bar"><i /><i /><i /><b>运营工作台</b></div><div className="mock-app-body"><aside><span className="mock-logo" /><i className="on"/><i/><i/><i/></aside><main><div className="mock-title"><b>今天值得关注</b><span /></div><div className="mock-stats"><i/><i/><i/></div><div className="mock-chart"><span/><span/><span/><span/><span/><span/></div><div className="mock-list"><i/><i/><i/></div></main></div></div>;
}

function DeliveryList({ deliveries, compact = false, onAction }: { deliveries: DeliveryFact[]; compact?: boolean; onAction?: () => void }) {
  return <section className={`delivery-list-card ${compact ? "compact" : ""}`}><div className="section-heading"><div><span className="card-kicker">{compact ? "最近交付" : "可用成果"}</span><h2>{compact ? "已经真正拿到的结果" : "交付与历史"}</h2></div><Icon name="delivery" /></div><div className="delivery-list">{deliveries.map((delivery, index) => <article className="delivery-row" key={`${delivery.title}-${index}`}><span className="delivery-icon"><Icon name="delivery" /></span><div className="delivery-main"><strong>{delivery.title}</strong><p>{delivery.form} · {delivery.detail}</p><span className={`trust-line ${delivery.runtimeState === "different" ? "different" : ""}`}><Icon name={delivery.runtimeState === "different" ? "info" : "shield"} size={14} />{delivery.trust}</span></div><button onClick={onAction}>{delivery.action}<Icon name="arrow" size={15} /></button></article>)}</div></section>;
}

function ChangedCard({ items }: { items: string[] }) {
  return <section className="changed-card"><div className="section-heading"><div><span className="card-kicker">上次离开后</span><h2>这些事情有了进展</h2></div><span className="soft-tag">{items.length} 项变化</span></div><ol>{items.map((item, index) => <li key={item}><span>{index + 1}</span><p>{item}</p><Icon name="chevron" size={15} /></li>)}</ol></section>;
}

function ProductionDrawer({ scene, onClose }: { scene: Scene; onClose: () => void }) {
  const detail = scene.production?.queueDetail ?? ["当前阶段与 Work 身份保持不变", "生产可以安全暂停、让出和恢复", "普通故障由 Watt 自行处理"];
  return <div className="overlay-shell" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside className="side-drawer"><DrawerHeader label="生产详情" title={scene.production?.label ?? phaseLabels[scene.phase]} onClose={onClose} /><div className="drawer-body"><div className="drawer-status"><span className={`status-orb ${scene.tone}`} /><div><strong>{scene.production?.activity ?? scene.summary}</strong><p>{scene.production?.reason ?? "这是当前 Work 的上下文生产状态，不是独立的队列管理任务。"}</p></div></div><div className="drawer-section"><span>当前状态说明</span>{detail.map((item) => <div className="detail-row" key={item}><Icon name="check" size={15} /><p>{item}</p></div>)}</div>{scene.milestones && <MilestoneCard milestones={scene.milestones} />}<div className="simulation-note"><Icon name="info" size={16} />此处仅模拟 Queue/Executor 的用户投影，不运行真实生产。</div></div></aside></div>;
}

function EvidenceDrawer({ scene, onClose }: { scene: Scene; onClose: () => void }) {
  return <div className="overlay-shell" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside className="side-drawer"><DrawerHeader label="渐进详情" title="事实来源与检查" onClose={onClose} /><div className="drawer-body"><div className="simulation-note"><Icon name="shield" size={16} />这些是用于体验验证的 owner-specific mock facts，不是生产事实。</div><div className="drawer-section"><span>架构所有者投影</span>{Object.entries(scene.ownerFacts).map(([owner, fact]) => <div className="owner-fact" key={owner}><strong>{owner}</strong><p>{fact}</p></div>)}</div>{scene.result && <><div className="drawer-section"><span>检查结果</span>{scene.result.checks.map((check) => <div className="detail-row" key={check}><Icon name="check" size={15} /><p>{check}</p></div>)}</div>{scene.result.limitations && <div className="drawer-section warning"><span>已知限制</span>{scene.result.limitations.map((item) => <div className="detail-row" key={item}><Icon name="info" size={15} /><p>{item}</p></div>)}</div>}</>}</div></aside></div>;
}

function PreviewOverlay({ result, onClose }: { result: ResultFact; onClose: () => void }) {
  return <div className="preview-overlay"><div className="preview-toolbar"><div><span className="preview-dot" /><strong>隔离结果预览</strong><em>模拟数据 · 不会影响真实环境</em></div><button onClick={onClose}><Icon name="close" /></button></div><div className="preview-stage"><div className="preview-frame"><MockPreview variant={result.previewVariant ?? "dashboard"} /></div><aside className="preview-inspector"><span className="card-kicker">正在预览</span><h2>{result.title}</h2><p>{result.summary}</p><ListBlock title="关键变化" items={result.highlights} /><ListBlock title="检查通过" items={result.checks} />{result.limitations && <ListBlock title="已知限制" items={result.limitations} />}<button className="action-button primary" onClick={onClose}>返回结果审阅<Icon name="arrow" size={16} /></button></aside></div></div>;
}

function DrawerHeader({ label, title, onClose }: { label: string; title: string; onClose: () => void }) {
  return <header className="drawer-header"><div><span>{label}</span><h2>{title}</h2></div><button onClick={onClose} aria-label={`关闭${title}`}><Icon name="close" /></button></header>;
}

function ReviewerPanel({ pack, scene, onClose, onPack, onScene, onReset, onAdvance }: { pack: ScenarioPack; scene: Scene; onClose: () => void; onPack: (pack: ScenarioPack) => void; onScene: (scene: Scene) => void; onReset: () => void; onAdvance: () => void }) {
  const key = `watt-prototype-note:${pack.id}:${scene.id}`;
  const [note, setNote] = useState(() => localStorage.getItem(key) ?? "");
  useEffect(() => setNote(localStorage.getItem(key) ?? ""), [key]);
  return <div className="reviewer-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside className="reviewer-panel"><DrawerHeader label="独立评审工具" title="体验评审模式" onClose={onClose} /><div className="reviewer-body"><label>场景包<select value={pack.id} onChange={(event) => onPack(getPack(event.target.value))}>{scenarioPacks.map((item) => <option value={item.id} key={item.id}>{item.id} · {item.shortTitle}</option>)}</select></label><div className="reviewer-description"><strong>{pack.title}</strong><p>{pack.description}</p><span>{pack.reviewReason}</span></div><label>当前场景<select value={scene.id} onChange={(event) => onScene(getScene(pack, event.target.value))}>{pack.scenes.map((item, index) => <option value={item.id} key={item.id}>{index + 1}. {item.label}</option>)}</select></label><div className="reviewer-buttons"><button onClick={onReset}><Icon name="refresh" size={16} />重置场景包</button><button className="primary" onClick={onAdvance} disabled={!scene.transitions.length}><Icon name="play" size={16} />推进模拟</button></div><div className="reviewer-meta"><div><span>模拟状态</span><code>{scene.phase}</code></div><div><span>场景清单</span><p>{scene.scenarioIds.join(" · ") || "—"}</p></div><div><span>架构张力</span><p>{scene.tensionIds.join(" · ") || "—"}</p></div><div><span>本场景验收重点</span><p>{scene.acceptanceFocus}</p></div></div><label>本地评审笔记<textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} placeholder="记录让你困惑、安心或想调整的地方……" /></label><button className="save-note" onClick={() => localStorage.setItem(key, note)}><Icon name="check" size={16} />保存在此浏览器</button><div className="simulation-note"><Icon name="info" size={16} />评审笔记只保存在当前浏览器，不写入产品数据或代码库。</div></div></aside></div>;
}
