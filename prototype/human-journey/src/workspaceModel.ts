import type { Scene } from "./types";

export type WorkspaceFunction = "reality" | "agenda" | "production" | "actions";
export type GroupSource = "ai" | "human" | "fallback";

export interface WorkNavItem {
  id: string;
  name: string;
  outcome: string;
  status: string;
  groupLabel: string;
  groupSource?: GroupSource;
  pinned: boolean;
  historical: boolean;
  productionPriority: number;
}

export interface WorkspaceProjection {
  visible: WorkspaceFunction[];
  emphasized: WorkspaceFunction;
  focused: WorkspaceFunction | null;
  compact: WorkspaceFunction[];
}

export const WORKSPACE_LABELS: Record<WorkspaceFunction, string> = {
  reality: "当前情况",
  agenda: "接下来",
  production: "生产进展",
  actions: "需要你处理",
};

export const DEFAULT_WORKS: WorkNavItem[] = [
  { id: "watt-ops", name: "Watt 运营后台", outcome: "让内容、渠道和用户反馈形成运营闭环", status: "正在推进", groupLabel: "", pinned: true, historical: false, productionPriority: 30 },
  { id: "feedback", name: "客户反馈门户", outcome: "让早期用户反馈形成可跟踪闭环", status: "等待验证", groupLabel: "产品体验", groupSource: "human", pinned: false, historical: false, productionPriority: 20 },
  { id: "invite", name: "团队邀请流程", outcome: "安全邀请并管理团队成员", status: "需要决定", groupLabel: "", pinned: false, historical: false, productionPriority: 10 },
  { id: "launch", name: "首轮推广素材", outcome: "形成第一轮可复用推广内容", status: "已归档", groupLabel: "推广与增长", groupSource: "human", pinned: false, historical: true, productionPriority: 0 },
  { id: "research", name: "早期用户访谈整理", outcome: "沉淀首批用户问题与语言", status: "已归档", groupLabel: "", pinned: false, historical: true, productionPriority: 0 },
];

export function semanticGroupFor(work: WorkNavItem): string {
  const text = `${work.name} ${work.outcome}`;
  if (/运营|推广|内容|渠道/.test(text)) return "推广与增长";
  if (/反馈|体验|用户/.test(text)) return "产品体验";
  if (/团队|邀请|成员/.test(text)) return "团队能力";
  return "其他";
}

export function assignSemanticGroup(work: WorkNavItem): WorkNavItem {
  if (work.groupLabel.trim()) return work;
  const groupLabel = semanticGroupFor(work);
  return { ...work, groupLabel, groupSource: groupLabel === "其他" ? "fallback" : "ai" };
}

export function assignHumanGroup(work: WorkNavItem, groupLabel: string): WorkNavItem {
  return { ...work, groupLabel: groupLabel.trim() || "其他", groupSource: "human" };
}

export function togglePinned(work: WorkNavItem): WorkNavItem {
  return { ...work, pinned: !work.pinned };
}

export function splitWorkHistory(works: WorkNavItem[]): { active: WorkNavItem[]; historical: WorkNavItem[] } {
  return {
    active: works.filter((work) => !work.historical),
    historical: works.filter((work) => work.historical),
  };
}

export function visibleWorkspaceFunctions(scene: Scene): WorkspaceFunction[] {
  const visible: WorkspaceFunction[] = ["reality"];
  if (scene.understanding || scene.recommendation || scene.milestones?.length || scene.transitions.length) visible.push("agenda");
  if (scene.production) visible.push("production");
  if (scene.attention || scene.result) visible.push("actions");
  return visible;
}

export function emphasizedWorkspaceFunction(scene: Scene, visible = visibleWorkspaceFunctions(scene)): WorkspaceFunction {
  if (scene.attention?.contract === "decision") return "actions";
  if (scene.result || scene.deliveries?.length) return "reality";
  if (scene.production) return "production";
  if (visible.includes("agenda")) return "agenda";
  return "reality";
}

export function projectWorkspace(scene: Scene, requestedFocus: WorkspaceFunction | null): WorkspaceProjection {
  const visible = visibleWorkspaceFunctions(scene);
  const focused = requestedFocus && visible.includes(requestedFocus) ? requestedFocus : null;
  return {
    visible,
    emphasized: emphasizedWorkspaceFunction(scene, visible),
    focused,
    compact: focused ? visible.filter((item) => item !== focused) : [],
  };
}
