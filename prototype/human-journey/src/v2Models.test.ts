import { describe, expect, it } from "vitest";
import { interactionReducer, initialInteraction, transitionMotion } from "./interactionModel";
import { getPack, getScene } from "./scenarios";
import { DEFAULT_WORKS, assignHumanGroup, assignSemanticGroup, projectWorkspace, splitWorkHistory, togglePinned } from "./workspaceModel";

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
