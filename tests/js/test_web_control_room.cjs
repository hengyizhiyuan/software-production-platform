"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const webRoot = path.resolve(__dirname, "../../src/spg/web");
const source = fs.readFileSync(path.join(webRoot, "control-room.js"), "utf8");
const app = fs.readFileSync(path.join(webRoot, "app.js"), "utf8");
const html = fs.readFileSync(path.join(webRoot, "index.html"), "utf8");
const appearance = fs.readFileSync(path.join(webRoot, "appearance.css"), "utf8");
const context = {};
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "control-room.js" });
const controlRoom = context.WattControlRoom;

test("early Workspace projects a candidate without fabricating Work or production", () => {
  const projection = {
    interpreted_motive: "做一个五年级课程表网页",
    selected_design_schema_identity: "PRODUCT_SYSTEM",
    readiness: { status: "READY", unresolved_material_questions: [] },
    latest_assessment: { progressive_semantics: {
      turn_intent: "BUILD", governance_candidate: "WORK_FORMATION_PROPOSAL",
    } },
  };
  assert.deepEqual({ ...controlRoom.prospectiveWorkspaceProjection(projection) }, {
    visible: true, canStart: true, blocker: null,
  });
  assert.equal(controlRoom.prospectiveWorkspaceProjection(projection, "real-work").visible, false);
  assert.equal(controlRoom.prospectiveWorkspaceProjection({ ...projection,
    latest_assessment: { progressive_semantics: { turn_intent: "DIRECT_QUESTION", governance_candidate: "CONVERSATION_ONLY" } },
  }).visible, false);
  assert.equal(controlRoom.prospectiveWorkspaceProjection({ ...projection,
    latest_assessment: { progressive_semantics: { turn_intent: "DIRECT_QUESTION", governance_candidate: "WORK_FORMATION_PROPOSAL" } },
  }).visible, false, "a schema and conflicting proposal must not turn a direct question into Work");
  assert.deepEqual({ ...controlRoom.prospectiveWorkspaceProjection({
    ...projection,
    current_work_id: "pre-work-1",
    latest_assessment: { progressive_semantics: {
      turn_intent: "DIRECT_QUESTION", governance_candidate: "CONVERSATION_ONLY",
    } },
  }) }, {
    visible: true, canStart: true, blocker: null,
  }, "a durable PRE_WORK keeps its panel when the latest turn is a direct question");
  assert.deepEqual({ ...controlRoom.prospectiveWorkspaceProjection({ ...projection,
    readiness: { status: "NOT_READY", unresolved_material_questions: ["Which external repository may be mutated?"] },
  }) }, { visible: true, canStart: false, blocker: "Which external repository may be mutated?" });
  assert.match(app, /prospectiveStart\.addEventListener\("click", admitInteractionWork\)/);
  assert.match(app, /start_work_context: true/);
  assert.match(app, /assessment_id: assessment\.assessment_id/);
  assert.match(app, /basis_fingerprint: assessment\.basis_fingerprint/);
  assert.match(html, /id="formal-workspace-grid"/);
  assert.match(html, /id="prospective-start"[^>]*>按当前理解开始/);
  assert.match(app, /IDLE · Production has not started/);
});

test("first Send opens provisional Workspace and a confirmed Motive latches it", () => {
  assert.match(app, /provisionalWorkspace: false/);
  assert.match(app, /workspaceEngaged: false/);
  assert.match(app, /state\.provisionalWorkspace = true;[\s\S]*?renderProspectiveWorkspace\(\);[\s\S]*?void drainOutbox\(\)/);
  assert.match(app, /if \(candidate\.visible\) state\.workspaceEngaged = true/);
  assert.match(app, /candidate\.visible \|\| state\.workspaceEngaged \|\| provisional/);
  assert.match(app, /if \(projection\.latest_assessment_current\) state\.provisionalWorkspace = false/);
  assert.match(app, /state\.workspaceEngaged = false;[\s\S]*?setSurface\("empty"\)/);
  assert.match(app, /Waiting for interpretation; no Work or production has started/);
  assert.match(app, /sending\.status === "queued" \|\| !messages\.some/);
});

test("New Work clears every selected-Work projection and hides stale result actions", () => {
  assert.match(app, /function clearSelectedWorkState\(\)/);
  for (const assignment of [
    'state.selectedWork = null',
    'state.attention = []',
    'state.result = null',
    'state.nativeQueue = []',
    'state.nativeAttempt = null',
    'state.sources = null',
    'state.agreements = []',
  ]) {
    assert.match(app, new RegExp(assignment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
  assert.match(app, /setSurface\("prospective"\);\s*renderResult\(\);\s*renderAttention\(\);\s*elements\.workActions\.replaceChildren\(\)/);
  assert.match(app, /function beginNewInteraction\(\)[\s\S]*?clearSelectedWorkState\(\)/);
  assert.match(app, /function consumeNewWorkEntry\(\)[\s\S]*?clearSelectedWorkState\(\)/);
});

test("Agenda follows the governed Steering path, including its actual step labels", () => {
  const steps = controlRoom.agendaSteps({
    completed_steps: [{ step_id: "a", objective: "Inspect existing design" }],
    current_step: { step_id: "b", objective: "Build the feature" },
    known_next_steps: [{ step_id: "c", objective: "Verify behavior" }],
  });
  assert.deepEqual(Array.from(steps, ({ label, state }) => ({ label, state })), [
    { label: "Inspect existing design", state: "DONE" },
    { label: "Build the feature", state: "CURRENT" },
    { label: "Verify behavior", state: "NEXT" },
  ]);
  assert.equal(controlRoom.agendaSteps(null).length, 0);
});

test("Agenda groups consecutive governed steps without losing their detail or current state", () => {
  const milestones = controlRoom.agendaMilestones({
    completed_steps: [
      { step_id: "r", type: "REFINE", objective: "Clarify goal" },
      { step_id: "d1", type: "DESIGN", objective: "Choose approach" },
      { step_id: "d2", type: "DESIGN", objective: "Review design" },
    ],
    current_step: { step_id: "p", type: "PRODUCE", objective: "Implement approved plan" },
    known_next_steps: [{ step_id: "v", type: "VERIFY_ACCEPT", objective: "Check acceptance" }],
  });
  assert.deepEqual(Array.from(milestones, (item) => item.label), ["Understand", "Shape solution", "Produce", "Verify"]);
  assert.deepEqual(Array.from(milestones, (item) => item.state), ["DONE", "DONE", "CURRENT", "NEXT"]);
  assert.deepEqual(Array.from(milestones[1].steps, (step) => step.label), ["Choose approach", "Review design"]);
});

test("Agenda closes Deliver when the authoritative Work projection is complete", () => {
  const milestones = controlRoom.agendaMilestones({
    completed_steps: [
      { step_id: "p", type: "PRODUCE", objective: "Produce trusted result" },
      { step_id: "v", type: "VERIFY_ACCEPT", objective: "Verify trusted result" },
    ],
    current_step: { step_id: "c", type: "COMPLETE", objective: "Complete the admitted Work" },
    known_next_steps: [],
    automatic_progression_state: "STOPPED",
    last_stop_reason: "COMPLETE",
  });
  assert.deepEqual(Array.from(milestones, (item) => item.label), ["Produce", "Verify", "Deliver"]);
  assert.deepEqual(Array.from(milestones, (item) => item.state), ["DONE", "DONE", "DONE"]);
  assert.equal(milestones[2].steps[0].state, "DONE");
});

test("Work Plan Projection shows goal, current stage, remaining path, and latest governed change", () => {
  const projection = controlRoom.workPlanProjection({
    work_objective: "Build authentication capability",
    active_revision_number: 2,
    completed_steps: [
      { step_id: "d", type: "DESIGN", objective: "Decide architecture" },
    ],
    current_step: {
      step_id: "p", type: "PRODUCE", objective: "Implement backend",
    },
    known_next_steps: [
      { step_id: "v", type: "VERIFY_ACCEPT", objective: "Verify behavior" },
      { step_id: "c", type: "COMPLETE", objective: "Deliver result" },
    ],
    plan_changes: [{
      reason: "Runtime discovery requires frontend integration before verification.",
      affected_reality_refs: [{ kind: "WORK_REALITY_REVISION", identity: "revision-2" }],
      changed_at: "2026-09-21T10:00:00Z",
    }],
  });

  assert.equal(projection.goal, "Build authentication capability");
  assert.equal(projection.currentStage, "Produce");
  assert.deepEqual(Array.from(projection.remainingStages), ["Verify", "Deliver"]);
  assert.equal(projection.revision, 2);
  assert.equal(
    projection.latestChange.reason,
    "Runtime discovery requires frontend integration before verification.",
  );
  assert.deepEqual(Array.from(projection.latestChange.affectedWorkState), [
    "WORK_REALITY_REVISION",
  ]);
});

test("Work Plan Projection never invents stages without Steering Reality", () => {
  const projection = controlRoom.workPlanProjection(null);
  assert.equal(projection.available, false);
  assert.equal(projection.goal, null);
  assert.deepEqual(Array.from(projection.stages), []);
  assert.equal(projection.latestChange, null);
});

test("Production state maps observed queue and attempt facts without invented progress", () => {
  const unavailable = controlRoom.productionState({}, [{
    condition: "WAITING_RESOURCE",
    progression_state: "INFRASTRUCTURE_UNAVAILABLE",
    progression_reason: "No live compatible worker. Watt will recover automatically.",
  }], null);
  assert.equal(unavailable.state, "RECOVERING");
  assert.match(unavailable.detail, /recover automatically/);
  const scheduling = controlRoom.productionState({}, [{
    condition: "QUEUED",
    progression_state: "SCHEDULING",
    progression_reason: "Compatible execution capacity is available and Watt is assigning it.",
  }], null);
  assert.equal(scheduling.state, "PREPARING");
  const actualCapacityWait = controlRoom.productionState({}, [{
    condition: "QUEUED",
    progression_state: "CAPACITY_WAIT",
  }], null);
  assert.equal(actualCapacityWait.state, "QUEUED");
  assert.equal(actualCapacityWait.detail, "Waiting for execution capacity.");
  assert.equal(controlRoom.productionState({}, [{ condition: "WAITING_RESOURCE", wait_reason: "GPU unavailable" }], null).detail, "GPU unavailable");
  const transportRecovery = controlRoom.productionState({}, [{
    condition: "WAITING_RESOURCE",
    wait_reason: "PROVIDER_TRANSPORT INCOMPLETE_RESPONSE: stream ended before completion",
    resume_count: 1,
  }], null);
  assert.equal(transportRecovery.state, "RETRYING PROVIDER");
  assert.match(transportRecovery.detail, /Retrying automatically.*\(1\/3\)/);
  const exhaustedRecovery = controlRoom.productionState({}, [{ condition: "COMPLETED" }], {
    state: { runtime_mode: "FINISHED", terminal_outcome: "UNABLE_TO_COMPLETE" },
    steps: Array.from({ length: 4 }, () => ({
      result_payload: { error_type: "InferenceTransportUnknown" },
    })),
  });
  assert.equal(exhaustedRecovery.state, "FAILED");
  assert.equal(exhaustedRecovery.detail, "Provider response failed after 3 automatic retries.");
  const truthfulUnable = controlRoom.productionState({}, [{ condition: "COMPLETED" }], {
    state: { runtime_mode: "FINISHED", terminal_outcome: "UNABLE_TO_COMPLETE" },
    steps: [{ result_payload: { action: "UNABLE_TO_COMPLETE", summary: "Verification remains." } }],
  });
  assert.equal(truthfulUnable.state, "FAILED");
  assert.equal(truthfulUnable.detail, "Execution finished with unresolved obligations. Review the recorded evidence before retrying.");
  const reviewableCandidate = controlRoom.productionState({ work_id: "one" }, [{ condition: "COMPLETED" }], {
    state: { runtime_mode: "FINISHED", terminal_outcome: "UNABLE_TO_COMPLETE" },
    steps: [{ result_payload: { action: "UNABLE_TO_COMPLETE" } }],
  }, [{ work_id: "one", kind: "CANDIDATE_AUTHORIZATION", available_actions: ["AUTHORIZE"] }]);
  assert.equal(reviewableCandidate.state, "FINISHED");
  assert.equal(reviewableCandidate.detail, "Candidate ready for preview and authorization.");
  assert.equal(controlRoom.productionState({}, [{ condition: "EXECUTING" }], null).state, "RUNNING");
  assert.equal(controlRoom.productionState({}, [], { state: { runtime_mode: "RECOVERING" } }).state, "RECOVERING");
  assert.equal(controlRoom.productionState({ status: "COMPLETED" }, [], null).state, "FINISHED");
  assert.equal(controlRoom.productionState({ status: "NEEDS_ATTENTION", what_happens_next: "Choose a recovery path" }, [], null).detail, "Choose a recovery path");
  assert.equal(controlRoom.productionState({ status: "NEEDS_ATTENTION", what_happens_next: "Configure an Executor capability" }, [], null).state, "BLOCKED");
  assert.equal(controlRoom.productionState({ work_id: "one", status: "NEEDS_ATTENTION" }, [], null,
    [{ work_id: "one", kind: "PRODUCTION_PROPOSAL_REVIEW", available_actions: ["APPROVE"] }]).state, "WAITING FOR HUMAN");
  assert.doesNotMatch(source, /\d+%|percent_complete/);
});

test("inspection stays a single read-only floating workspace with multi-file controls", () => {
  for (const id of ["inspection-window", "inspection-tabs", "inspection-close", "inspection-expand", "inspection-opacity", "inspection-search", "inspection-view"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(source, /const files = new Map\(\)/);
  assert.match(source, /files\.delete\(key\)/);
  assert.match(source, /sourceMode = !sourceMode/);
  assert.match(source, /is-translucent/);
  assert.match(source, /inspection-line-number/);
  assert.doesNotMatch(source, /innerHTML|contentEditable|document\.write|method:\s*"POST"/);
});

test("machine controls belong to Production and Human authority actions belong to Actions", () => {
  assert.match(app, /function concentrateWorkMutations\(\)/);
  assert.match(app, /actions\.append\(preview\)/);
  assert.match(app, /actions\.append\(revisionAdmission\)/);
  assert.match(app, /RETRY_PRODUCTION: "Retry production"/);
  assert.match(app, /\/retry-production/);
  assert.match(app, /actions\.append\(transitionDecision\)/);
  assert.match(app, /evidence\.append\(manual\)/);
  assert.match(app, /production\.insertBefore\(machineControls, result\)/);
  assert.match(app, /evidence\.append\(agreementEntry\)/);
  assert.match(app, /evidence\.prepend\(sharedUnderstanding\)/);
  assert.match(app, /evidence\.append\(result\)/);
  assert.doesNotMatch(app, /reality\.append\(result\)/);
  assert.match(html, /<section id="actions-surface"/);
  assert.match(html, /id="agreement-action-panel"/);
  assert.match(app, /candidate-preview-panel/);
  assert.match(app, /agreementSelectionActions\.hidden = !selected/);
});

test("conversation sidebar does not retain governed revision controls", () => {
  assert.match(app, /actions\.append\(revisionAdmission\)/);
  assert.match(app, /actions\.append\(transitionDecision\)/);
  const currentPanel = html.match(/<section id="current-interaction-panel"[\s\S]*?<\/section>/)?.[0];
  assert.ok(currentPanel);
  assert.doesNotMatch(currentPanel, /work-revision-admission|work-transition-decision/);
});

test("latest turn has exactly one surface owner through stream, handoff, and next turn", () => {
  const records = [
    { actor: "HUMAN", turn_id: "old" }, { actor: "WATT", turn_id: "old" },
    { actor: "HUMAN", turn_id: "latest" }, { actor: "WATT", turn_id: "latest", streaming: true },
  ];
  const pending = controlRoom.conversationOwnership(records);
  assert.deepEqual(Array.from(pending.history, (item) => item.turn_id), ["old", "old"]);
  assert.deepEqual(Array.from(pending.current, (item) => item.turn_id), ["latest", "latest"]);
  const handed = controlRoom.conversationOwnership(records, "latest");
  assert.equal(handed.current.length, 0);
  assert.equal(handed.history.length, 4);
  const next = controlRoom.conversationOwnership([...records, { actor: "HUMAN", turn_id: "next" }], "latest");
  assert.equal(next.current[0].turn_id, "next");
  assert.equal(next.history.length, 4);
  assert.match(app, /handoffCurrentInteraction\(\)/);
  assert.match(app, /state\.activeInteractionTurnId \|\| state\.finishingTurn/);
});

test("V4 Current Interaction is on-demand, floating, and conversation-only", () => {
  assert.match(html, /id="current-interaction-panel"[^>]*hidden/);
  assert.match(app, /currentInteractionPanel\.hidden = active\.length === 0/);
  assert.doesNotMatch(app, /The current exchange will appear here/);
  assert.match(appearance, /body:has\(\.work-workspace\) \.current-interaction-panel \{\s*position: absolute;/);
  assert.match(appearance, /max-height: min\(35vh, 270px\)/);
  assert.match(app, /evidence\.prepend\(sharedUnderstanding\)/);
  assert.match(app, /if \(message\.children\.length < 3\) return/);
  assert.match(appearance, /prefers-reduced-motion: reduce/);
});

test("V4.1 anchors the message-only Current Interaction above the composer", () => {
  const panel = html.match(/<section id="current-interaction-panel"[\s\S]*?<\/section>/)?.[0];
  assert.ok(panel);
  assert.match(panel, /id="current-interaction-live"/);
  assert.doesNotMatch(panel, /interaction-admission|shared-understanding|DESIGN_SCHEMA|interaction-readiness/);
  assert.match(html, /<section class="composer"[^>]*>[\s\S]*?<section id="current-interaction-panel"/);
  assert.match(appearance, /\.current-interaction-panel \{\s*position: absolute;[\s\S]*?bottom: calc\(100% \+ 9px\)/);
  // The browser qualification also asserts actual getBoundingClientRect values.
  assert.match(app, /currentInteractionPanel\.hidden = active\.length === 0/);
});

test("V4.1 exposes one governed pre-Work admission action outside the message body", () => {
  const panel = html.match(/<section id="current-interaction-panel"[\s\S]*?<\/section>/)?.[0];
  assert.ok(panel);
  assert.doesNotMatch(panel, /admit-work-control|interaction-admission/);
  assert.equal((html.match(/id="admit-work-control"/g) || []).length, 1);
  assert.match(html, /id="interaction-admission"[^>]*hidden/);
  assert.match(html, /id="admit-work-control"[^>]*>Start Work<\/button>/);
  assert.match(app, /interactionAdmission\.hidden = status !== "READY" \|\| Boolean\(governed\)/);
  assert.match(app, /\/api\/interactions\/\$\{projection\.interaction_id\}\/admit-work/);
  assert.match(app, /assessment_id: assessment\.assessment_id/);
  assert.match(app, /basis_fingerprint: assessment\.basis_fingerprint/);
  assert.match(app, /state\.selectedWorkId = state\.sharedUnderstanding\.governed_work_id/);
  assert.doesNotMatch(panel, /manual-advance-control|DESIGN_SCHEMA/);
});

test("V4 composer state keeps a draft but collapses after either send", () => {
  const step = controlRoom.nextComposerMode;
  assert.equal(step("COMPACT_IDLE", "FOCUS"), "EXPANDED_COMPOSING");
  assert.equal(step("EXPANDED_COMPOSING", "OUTSIDE", false), "COMPACT_IDLE");
  assert.equal(step("EXPANDED_COMPOSING", "OUTSIDE", true), "EXPANDED_COMPOSING");
  let mode = step("EXPANDED_COMPOSING", "SEND", false);
  assert.equal(mode, "SUBMITTING");
  mode = step(mode, "ACCEPTED");
  assert.equal(mode, "WAITING_RESPONSE");
  mode = step(mode, "SETTLED");
  assert.equal(mode, "RESPONSE_SETTLED");
  mode = step(mode, "FOCUS");
  assert.equal(step(mode, "SEND", false), "SUBMITTING");
  assert.match(app, /renderConversation\(\);\s*renderProspectiveWorkspace\(\);\s*if \(state\.activeInteractionTurnId/);
});

test("V4 attention badge and Actions derive from the same executable Human operations", () => {
  const project = controlRoom.humanActionProjection;
  const quiet = project({ work_id: "one", status: "NEEDS_ATTENTION" }, [], null);
  assert.equal(quiet.required, false);
  assert.equal(quiet.summary, "No action required.");
  const approval = project({ work_id: "one", status: "AWAITING_APPROVAL" }, [], null);
  assert.equal(approval.required, true);
  assert.deepEqual(Array.from(approval.workActions), ["APPROVE", "REQUEST_REFINEMENT", "REJECT"]);
  const review = project({ work_id: "one", status: "NEEDS_ATTENTION" }, [
    { work_id: "one", kind: "PRODUCTION_PROPOSAL_REVIEW", available_actions: ["APPROVE"] },
  ]);
  assert.equal(review.required, true);
  assert.equal(review.actionableAttention.length, 1);
  const question = project({ work_id: "one", status: "NEEDS_ATTENTION" }, [
    {
      work_id: "one",
      kind: "STEERING_DECISION_REQUIRED",
      conversation_prompt: "Which feature should be added first?",
      available_actions: [],
    },
  ]);
  assert.equal(question.required, true);
  assert.equal(question.summary, "Answer the current Work question in conversation.");
  assert.equal(question.conversationalDecision.conversation_prompt, "Which feature should be added first?");
  assert.match(app, /attention\.conversation_prompt \? "Answer in conversation"/);
  const unrelated = project({ work_id: "one", status: "RUNNING" }, [
    { work_id: "two", kind: "CANDIDATE_AUTHORIZATION", available_actions: ["AUTHORIZE"] },
  ]);
  assert.equal(unrelated.required, false);
  const stopped = project({
    work_id: "one",
    status: "READY",
    steering_enabled: true,
    automatic_progression_state: "STOPPED",
    last_stop_reason: "BLOCKED",
  }, [], null);
  assert.equal(stopped.required, false);
  assert.deepEqual(Array.from(stopped.workActions), []);
  assert.equal(stopped.summary, "No action required.");
  assert.match(app, /attentionMarker\.hidden = !controlRoom\.humanActionProjection/);
  assert.match(app, /workspaceActionsSummary\.textContent = repositoryAuthorizationRequired/);
  assert.match(app, /: humanActions\.summary;/);
  assert.match(app, /humanActions\.required \|\| repositoryAuthorizationRequired/);
  assert.match(app, /\/retry-steering/);
});

test("Production follows the current Work revision instead of a completed prior cycle", () => {
  const work = {
    current_work_reality_revision_id: "revision-3",
    automatic_progression_state: "ACTIVE",
    what_happens_next: "Reassessing the admitted change",
  };
  const prior = [{
    condition: "COMPLETED",
    attempt_id: "old-attempt",
    work_reality_revision_id: "revision-2",
    production_cycle_number: 1,
  }];
  assert.equal(controlRoom.currentProductionQueue(work, prior).length, 0);
  const preparing = controlRoom.productionState(work, prior, {
    state: { runtime_mode: "FINISHED", terminal_outcome: "RESULT_READY" },
  });
  assert.equal(preparing.state, "PREPARING");
  assert.equal(preparing.detail, "Reassessing the admitted change");

  const current = [...prior, {
    condition: "EXECUTING",
    attempt_id: "current-attempt",
    work_reality_revision_id: "revision-3",
    production_cycle_number: 2,
  }];
  assert.deepEqual(
    Array.from(controlRoom.currentProductionQueue(work, current), (entry) => entry.attempt_id),
    ["current-attempt"],
  );
  assert.equal(controlRoom.productionState(work, current, {
    state: { runtime_mode: "RUNNING" },
  }).state, "RUNNING");
});

test("a completed branch-preparation attempt is not the new feature's production", () => {
  const work = {
    current_work_reality_revision_id: "feature-revision",
    current_production_cycle_number: null,
    automatic_progression_state: "ACTIVE",
    what_happens_next: "Shaping the admitted navigation-link change",
  };
  const branchPreparation = [{
    condition: "COMPLETED",
    attempt_id: "branch-attempt",
    work_reality_revision_id: null,
    production_cycle_number: null,
  }];
  assert.deepEqual(Array.from(controlRoom.currentProductionQueue(work, branchPreparation)), []);
  const state = controlRoom.productionState(work, branchPreparation, {
    state: { runtime_mode: "FINISHED", terminal_outcome: "RESULT_READY" },
  });
  assert.equal(state.state, "PREPARING");
  assert.equal(state.detail, "Shaping the admitted navigation-link change");
});

test("Production details are disclosed, while Actions contain only contextual controls", () => {
  assert.match(app, /evidence\.append\(result\)/);
  assert.match(html, /<section id="agreement-action-panel"[^>]+hidden>/);
  assert.match(html, /<details class="agreement-entry">/);
  assert.match(app, /agreementActionPanel\.hidden = !selected/);
  assert.match(source, /No action required\./);
  assert.doesNotMatch(app, /Exact Candidate \$\{preview\.repository_revision/);
});

test("repository acquisition UI exposes persisted intermediate states and governed retry", () => {
  assert.match(app, /Repository acquisition requested/);
  assert.match(app, /Acquiring repository/);
  assert.match(app, /Waiting for GitHub authorization/);
  assert.match(app, /Repository acquisition failed/);
  assert.match(app, /Repository ready/);
  assert.match(app, /Authorize repository access · unavailable/);
  assert.match(app, /Retry after external access changes/);
  assert.match(app, /integration_available/);
  assert.match(app, /repository-acquisition\/retry/);
  assert.match(app, /source\.revision/);
});

test("Work revision admission is rendered once through its authoritative panel", () => {
  assert.match(app, /item\.kind !== "WORK_REVISION_APPROVAL"/);
  assert.match(app, /workRevisionAdmission\.hidden/);
  assert.match(html, /id="approve-work-revision"/);
});
