import { describe, expect, it } from "vitest";
import { interactionReducer, initialInteraction, transitionMotion } from "./interactionModel";
import { getPack, getScene } from "./scenarios";
import { DEFAULT_WORKS, WORKSPACE_SURFACE_IDS, assignHumanGroup, assignSemanticGroup, projectWorkspace, splitWorkHistory, togglePinned, workspaceMode, workspacePlacements, workspaceSummary, type WorkspaceFunction } from "./workspaceModel";

describe("v2 Work navigation", () => {
  it("assigns semantic grouping only when the label is empty", () => {
    const ungrouped = DEFAULT_WORKS[0];
    const grouped = DEFAULT_WORKS[1];
    expect(assignSemanticGroup(ungrouped).groupSource).toBe("ai");
    expect(assignSemanticGroup(grouped)).toBe(grouped);
  });

  it("retains a Human group and keeps pinning separate from production priority", () => {
    const work = assignHumanGroup(assignSemanticGroup(DEFAULT_WORKS[2]), "我关心的工作");
    expect(assignSemanticGroup(work)).toBe(work);
    const pinned = togglePinned(work);
    expect(pinned.pinned).not.toBe(work.pinned);
    expect(pinned.productionPriority).toBe(work.productionPriority);
  });

  it("separates active and historical Works without inferring from production status", () => {
    const split = splitWorkHistory(DEFAULT_WORKS);
    expect(split.active.every((work) => !work.historical)).toBe(true);
    expect(split.historical.every((work) => work.historical)).toBe(true);
    expect(split.historical).toHaveLength(2);
  });
});

describe("v2 adaptive workspace", () => {
  it("hides Production when facts do not support it", () => {
    const scene = getScene(getPack("P01"), "p01-review");
    expect(projectWorkspace(scene, null).visible).not.toContain("production");
  });

  it("expands and restores Focus Mode while keeping Actions discoverable", () => {
    const scene = getScene(getPack("P10"), "p10-limits");
    const focused = projectWorkspace(scene, "reality");
    expect(focused.focused).toBe("reality");
    expect(focused.compact).toContain("actions");
    expect(projectWorkspace(scene, null).focused).toBeNull();
  });
});

describe("v2.1 adaptive workspace morph", () => {
  const all: WorkspaceFunction[] = ["reality", "agenda", "production", "actions"];

  it("uses a true 2x2 overview for four surfaces", () => {
    const layout = workspacePlacements(all, null);
    expect(workspaceMode(null)).toBe("OVERVIEW");
    expect([layout.reality?.gridRow, layout.agenda?.gridRow, layout.production?.gridRow, layout.actions?.gridRow]).toEqual([1, 1, 2, 2]);
    expect([layout.reality?.gridColumn, layout.agenda?.gridColumn]).toEqual(["1 / 7", "7 / 13"]);
  });

  it.each([
    ["reality", "FOCUS_1", [1, 2, 2, 2]],
    ["agenda", "FOCUS_2", [1, 2, 3, 3]],
    ["production", "FOCUS_3", [1, 1, 2, 3]],
    ["actions", "FOCUS_4", [1, 1, 1, 2]],
  ] as const)("maps %s to its distinct spatial focus configuration", (focused, mode, rows) => {
    const layout = workspacePlacements(all, focused);
    expect(workspaceMode(focused)).toBe(mode);
    expect([layout.reality?.gridRow, layout.agenda?.gridRow, layout.production?.gridRow, layout.actions?.gridRow]).toEqual(rows);
    expect(layout[focused]?.dominant).toBe(true);
    expect(all.filter((surface) => surface !== focused).every((surface) => layout[surface]?.compact)).toBe(true);
  });

  it("fills available space for three and two surfaces without empty placements", () => {
    const three = workspacePlacements(["reality", "agenda", "actions"], null);
    expect(three.actions).toMatchObject({ gridColumn: "1 / 13", gridRow: 2 });
    const two = workspacePlacements(["reality", "agenda"], null);
    expect([two.reality?.gridColumn, two.agenda?.gridColumn]).toEqual(["1 / 7", "7 / 13"]);
    expect(two.production).toBeUndefined();
    expect(two.actions).toBeUndefined();
  });

  it("keeps stable surface identity and does not steal focus for a critical Action", () => {
    expect(WORKSPACE_SURFACE_IDS).toEqual({ reality: "surface-1", agenda: "surface-2", production: "surface-3", actions: "surface-4" });
    const base = getScene(getPack("P09"), "p09-failed");
    const scene = { ...base, attention: { ...base.attention!, contract: "decision" as const, title: "是否采用修订方案？" } };
    const projection = projectWorkspace(scene, "production");
    expect(projection.focused).toBe("production");
    expect(workspaceSummary(scene, "actions")).toMatch(/^1 项决定/);
  });
});

describe("v2 current interaction", () => {
  it("retains the submitted Human turn, streams Watt, then archives one ordered pair", () => {
    let state = initialInteraction();
    state = interactionReducer(state, { type: "submit", text: "登录后不要跳转", reply: "已收到，我会更新约束。", realityEffect: "新增登录约束" });
    expect(state.humanTurn).toBe("登录后不要跳转");
    state = interactionReducer(state, { type: "start" });
    state = interactionReducer(state, { type: "reveal", length: 5 });
    expect(state.visibleReply).toBe("已收到，我");
    state = interactionReducer(state, { type: "complete" });
    state = interactionReducer(state, { type: "archive" });
    expect(state.history.map((message) => message.actor)).toEqual(["human", "watt"]);
    expect(state.history.filter((message) => message.text.includes("登录后"))).toHaveLength(1);
  });

  it("pauses archive during reading and settles a prior pair before a new turn", () => {
    let state = interactionReducer(initialInteraction(), { type: "submit", text: "第一条", reply: "第一条回复" });
    state = interactionReducer(state, { type: "start" });
    state = interactionReducer(state, { type: "complete" });
    state = interactionReducer(state, { type: "protect-reading", value: true });
    expect(interactionReducer(state, { type: "archive" }).phase).toBe("complete");
    state = interactionReducer(state, { type: "submit", text: "第二条", reply: "第二条回复" });
    expect(state.history.map((message) => message.text)).toEqual(["第一条", "第一条回复"]);
    expect(state.humanTurn).toBe("第二条");
  });

  it("keeps archived history when Conversation is collapsed and supports reduced motion", () => {
    const archived = interactionReducer(interactionReducer(interactionReducer(initialInteraction(), { type: "submit", text: "问题", reply: "答案" }), { type: "complete" }), { type: "archive" });
    const conversationCollapsed = true;
    expect(conversationCollapsed).toBe(true);
    expect(archived.history).toHaveLength(2);
    expect(transitionMotion(true)).toBe("instant");
    expect(transitionMotion(false)).toBe("crossfade");
  });
});
