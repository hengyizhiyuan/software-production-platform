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

export type WorkspaceMode = "OVERVIEW" | "FOCUS_1" | "FOCUS_2" | "FOCUS_3" | "FOCUS_4";

export interface SurfacePlacement {
  gridColumn: string;
  gridRow: number;
  compact: boolean;
  dominant: boolean;
}

export const WORKSPACE_LABELS: Record<WorkspaceFunction, string> = {
  reality: "当前情况",
  agenda: "接下来",
  production: "生产进展",
  actions: "需要你处理",
};

export const WORKSPACE_SURFACE_IDS: Record<WorkspaceFunction, string> = {
  reality: "surface-1",
  agenda: "surface-2",
  production: "surface-3",
  actions: "surface-4",
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

export function workspaceMode(focused: WorkspaceFunction | null): WorkspaceMode {
  if (!focused) return "OVERVIEW";
  return `FOCUS_${(["reality", "agenda", "production", "actions"] as WorkspaceFunction[]).indexOf(focused) + 1}` as WorkspaceMode;
}

function equalColumns(count: number, index: number): string {
  const width = 12 / count;
  return `${1 + index * width} / ${1 + (index + 1) * width}`;
}

/**
 * Places the same surface instances in overview and focus configurations.
 * The returned coordinates are deliberately independent from React rendering so
 * the spatial contract can be checked without relying on animation timing.
 */
export function workspacePlacements(visible: WorkspaceFunction[], focused: WorkspaceFunction | null): Record<WorkspaceFunction, SurfacePlacement | undefined> {
  const placements: Record<WorkspaceFunction, SurfacePlacement | undefined> = {
    reality: undefined,
    agenda: undefined,
    production: undefined,
    actions: undefined,
  };
  const activeFocus = focused && visible.includes(focused) ? focused : null;

  if (!activeFocus) {
    if (visible.length === 1) {
      placements[visible[0]] = { gridColumn: "1 / 13", gridRow: 1, compact: false, dominant: false };
    } else if (visible.length === 2) {
      visible.forEach((surface, index) => placements[surface] = { gridColumn: equalColumns(2, index), gridRow: 1, compact: false, dominant: false });
    } else {
      visible.forEach((surface, index) => {
        const lastFullWidth = visible.length === 3 && index === 2;
        placements[surface] = {
          gridColumn: lastFullWidth ? "1 / 13" : equalColumns(2, index % 2),
          gridRow: index < 2 ? 1 : 2,
          compact: false,
          dominant: false,
        };
      });
    }
    return placements;
  }

  const focusIndex = visible.indexOf(activeFocus);
  const before = visible.slice(0, focusIndex);
  const after = visible.slice(focusIndex + 1);
  let row = 1;
  if (before.length) {
    before.forEach((surface, index) => placements[surface] = { gridColumn: equalColumns(before.length, index), gridRow: row, compact: true, dominant: false });
    row += 1;
  }
  placements[activeFocus] = { gridColumn: "1 / 13", gridRow: row, compact: false, dominant: true };
  row += 1;
  if (after.length) {
    after.forEach((surface, index) => placements[surface] = { gridColumn: equalColumns(after.length, index), gridRow: row, compact: true, dominant: false });
  }
  return placements;
}

export function workspaceSummary(scene: Scene, surface: WorkspaceFunction): string {
  if (surface === "reality") return scene.workOutcome ?? scene.summary;
  if (surface === "agenda") {
    const current = scene.milestones?.find((item) => item.state === "current" || item.state === "blocked");
    return scene.recommendation?.title ?? current?.label ?? scene.transitions[0]?.label ?? "当前方向已经明确";
  }
  if (surface === "production") return scene.production ? `${scene.production.label} · ${scene.production.activity}` : "当前没有生产活动";
  if (scene.attention?.contract === "decision") return `1 项决定 · ${scene.attention.title}`;
  if (scene.result) return `结果待审阅 · ${scene.result.title}`;
  return scene.attention?.title ?? "当前无需你处理";
}
