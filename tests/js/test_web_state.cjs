"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const repositoryRoot = path.resolve(__dirname, "..", "..");
const stateSource = fs.readFileSync(
  path.join(repositoryRoot, "src", "spg", "web", "state.js"),
  "utf8",
);
const appSource = fs.readFileSync(
  path.join(repositoryRoot, "src", "spg", "web", "app.js"),
  "utf8",
);
const context = {};
context.globalThis = context;
vm.runInNewContext(stateSource, context, { filename: "state.js" });
const viewModel = context.SPGViewModel;

test("UI-07 maps every admitted Work status to clear product language", () => {
  const expected = {
    DRAFT: "Draft",
    NEEDS_REFINEMENT: "Needs refinement",
    AWAITING_APPROVAL: "Awaiting approval",
    READY: "Watt is preparing",
    RUNNING: "Watt is working",
    NEEDS_ATTENTION: "Needs your attention",
    BLOCKED: "Blocked",
    COMPLETED: "Completed",
  };
  assert.deepEqual({ ...viewModel.STATUS_LABELS }, expected);
});

test("UI-09 through UI-11 expose only bounded status actions", () => {
  assert.deepEqual(Array.from(viewModel.workActions("DRAFT")), ["REFINE"]);
  assert.deepEqual(Array.from(viewModel.workActions("AWAITING_APPROVAL")), [
    "APPROVE",
    "REQUEST_REFINEMENT",
    "REJECT",
  ]);
  assert.deepEqual(Array.from(viewModel.workActions("READY")), []);
  assert.deepEqual(Array.from(viewModel.workActions("RUNNING")), []);
  assert.deepEqual(Array.from(viewModel.workActions("NEEDS_ATTENTION")), []);
  assert.deepEqual(Array.from(viewModel.workActions("BLOCKED")), []);
  assert.deepEqual(Array.from(viewModel.workActions("COMPLETED")), []);
});

test("UI-04 and UI-05 preserve useful intake summaries", () => {
  assert.deepEqual(Array.from(viewModel.splitTags(" mvp, docs, mvp, ")), [
    "docs",
    "mvp",
  ]);
  assert.equal(
    viewModel.workTitle({ raw_user_requirement: "  Keep the exact user request  " }),
    "Keep the exact user request",
  );
});

test("UI-14 through UI-16 do not invent result evidence", () => {
  assert.equal(viewModel.artifactSummary(null), "No artifacts observed.");
  assert.equal(
    viewModel.verificationSummary({ verification_summary: [] }),
    "No verification evidence available.",
  );
  assert.equal(
    viewModel.artifactSummary({ produced_artifacts: ["docs/result.md"] }),
    "docs/result.md",
  );
});

test("UI-08 through UI-13 use safe DOM rendering and observational polling", () => {
  assert.doesNotMatch(appSource, /innerHTML|insertAdjacentHTML|document\.write/);
  assert.doesNotMatch(appSource, /setInterval|runUntilDone/);
  assert.match(appSource, /node\.textContent = String\(text\)/);
  assert.match(appSource, /attention\.available_actions\.forEach/);
  assert.equal((appSource.match(/\$\{workPath\}\/advance/g) || []).length, 1);
  assert.match(appSource, /POLL_INTERVAL_MS = 2000/);
  assert.match(appSource, /scheduleObservationPolling/);
  assert.doesNotMatch(appSource, /SPG_DATABASE_URL|OPENAI_API_KEY|api[_-]?key/i);
});

test("ORCH-20 polling observes only and stops at Human or terminal states", () => {
  assert.equal(viewModel.shouldPoll("READY"), true);
  assert.equal(viewModel.shouldPoll("RUNNING"), true);
  for (const status of [
    "DRAFT",
    "NEEDS_REFINEMENT",
    "AWAITING_APPROVAL",
    "NEEDS_ATTENTION",
    "BLOCKED",
    "COMPLETED",
  ]) {
    assert.equal(viewModel.shouldPoll(status), false);
  }
  const polling = appSource.slice(
    appSource.indexOf("function scheduleObservationPolling"),
    appSource.indexOf("async function refreshAfterMutation"),
  );
  assert.doesNotMatch(polling, /method:\s*"POST"|\/advance/);
});

test("execution progress shows activity without inventing a percentage", () => {
  const unknown = viewModel.executionProgress({ execution_progress: {
    phase: "EXECUTION", activity: "Waiting for Provider evidence",
    transitions_completed: 2, transitions_total: null,
    percent_complete: null, elapsed_seconds: 9.8, still_working: true,
  }});
  assert.equal(unknown.progressText, "2 transitions completed · total unknown");
  assert.equal(unknown.percentComplete, null);
  assert.equal(unknown.elapsedText, "9s elapsed");
  assert.equal(unknown.stillWorking, true);
  assert.equal(unknown.activitySignal, "Still working");

  const stopped = viewModel.executionProgress({ execution_progress: {
    phase: "BLOCKED", activity: "Stopped", transitions_completed: 1,
    transitions_total: null, elapsed_seconds: 3, still_working: false,
    blocked_reason: "Verification failed",
  }});
  assert.equal(stopped.blockedReason, "Verification failed");
  assert.equal(stopped.stillWorking, false);
  assert.equal(stopped.activitySignal, "Not running");

  const known = viewModel.executionProgress({ execution_progress: {
    phase: "VERIFY", activity: "Running checks", transitions_completed: 1,
    transitions_total: 4, percent_complete: 25, elapsed_seconds: 12,
    still_working: true, updated_at: "2026-09-06T00:00:00Z",
  }});
  assert.equal(known.progressText, "1 of 4 transitions · 25%");
  assert.equal(known.percentComplete, 25);
  assert.equal(known.updatedAt, "2026-09-06T00:00:00Z");
});

test("Control Room Slice 1 projects only existing Work, WIC, Runtime, and Attention Reality", () => {
  const work = {
    work_id: "work-1",
    title: "Ship the Control Room foundation",
    desired_outcome: "Human can see objective, status, and attention.",
    status: "RUNNING",
    current_production_step: "EXECUTE",
    human_attention_required: true,
    execution_progress: {
      phase: "EXECUTION",
      activity: "Applying the admitted production step",
      transitions_completed: 2,
      transitions_total: null,
      elapsed_seconds: 4,
      still_working: false,
      blocked_reason: "Human review is required",
    },
  };
  const understandings = [{
    current_work_id: "work-1",
    governed_revision: {
      work_id: "work-1",
      motive: "Make production Reality understandable",
    },
    work_satisfaction_state: "IN_PROGRESS",
  }];
  const attention = [{
    work_id: "work-1",
    decision: "Review candidate",
    reason: "Human review is required",
    recommendation: "Authorize the admitted candidate",
  }];

  const projection = viewModel.controlRoomProjection(work, understandings, attention);

  assert.equal(projection.objective.motive, "Make production Reality understandable");
  assert.equal(projection.objective.currentWork, "Ship the Control Room foundation");
  assert.equal(
    projection.objective.desiredOutcome,
    "Human can see objective, status, and attention.",
  );
  assert.equal(projection.objective.satisfaction, "IN_PROGRESS");
  assert.equal(projection.status.workStatus, "Watt is working");
  assert.equal(projection.status.lifecyclePhase, "EXECUTE");
  assert.equal(projection.status.activity, "Applying the admitted production step");
  assert.equal(projection.status.condition, "Human review is required");
  assert.equal(projection.attention.required, true);
  assert.equal(projection.attention.state, "1 Human attention requirement");
  assert.equal(
    projection.attention.summary,
    "Review candidate: Human review is required",
  );
  assert.equal(
    projection.attention.emergingDirection,
    "Authorize the admitted candidate",
  );
});

test("Control Room Slice 1 does not infer missing or cross-Work Reality", () => {
  const projection = viewModel.controlRoomProjection(
    {
      work_id: "work-2",
      raw_user_requirement: "A conversational statement is not governed Motive truth",
      status: "DRAFT",
      human_attention_required: false,
    },
    [{
      current_work_id: "work-1",
      governed_revision: { work_id: "work-1", motive: "Different Work" },
      work_satisfaction_state: "CURRENTLY_SATISFIED",
    }],
    [{
      work_id: "work-1",
      decision: "Unrelated decision",
      reason: "Different Work",
    }],
  );

  assert.equal(projection.objective.motive, "Not available from governed Work Reality.");
  assert.equal(projection.objective.satisfaction, "Not available for this Work.");
  assert.equal(projection.status.lifecyclePhase, "Not reported by Work Reality.");
  assert.equal(projection.status.activity, "No active production activity reported.");
  assert.equal(projection.status.condition, "No blocking or waiting condition reported.");
  assert.equal(projection.attention.required, false);
  assert.equal(projection.attention.state, "No Human attention required");
  assert.equal(
    projection.attention.summary,
    "No blockers, reviews, or transitions require Human action.",
  );
  assert.equal(projection.attention.emergingDirection, "No emerging direction reported.");
});

test("Control Room Slice 1 preserves completed satisfaction without creating attention", () => {
  const projection = viewModel.controlRoomProjection(
    {
      work_id: "work-complete",
      title: "Completed governed Work",
      desired_outcome: "The admitted outcome is trusted.",
      status: "COMPLETED",
      current_production_step: "WORK_COMPLETED",
      human_attention_required: false,
    },
    [{
      current_work_id: "work-complete",
      governed_work_id: "work-complete",
      governed_revision: {
        work_id: "work-complete",
        motive: "Reach a trusted outcome",
      },
      work_satisfaction_state: "CURRENTLY_SATISFIED",
    }],
    [],
  );

  assert.equal(projection.status.workStatus, "Completed");
  assert.equal(projection.objective.satisfaction, "CURRENTLY_SATISFIED");
  assert.equal(projection.attention.required, false);
  assert.equal(projection.status.activity, "No active production activity reported.");
});

test("Control Room Slice 2 keeps Human, interpreted, and governed WIC Reality distinct", () => {
  const projection = viewModel.understandingAlignmentProjection(
    { work_id: "work-aligned" },
    [{
      interaction_id: "interaction-1",
      current_work_id: "work-aligned",
      human_said: ["Make the current production direction visible."],
      latest_assessment: { assessment_id: "assessment-1" },
      latest_assessment_current: true,
      interpreted_motive: "Improve production visibility",
      desired_outcome: "Human can inspect understanding alignment.",
      candidate_context: ["Candidate context"],
      candidate_constraints: ["Candidate constraint"],
      unresolved_material_questions: [],
      readiness: { status: "READY" },
      work_revision_admission_status: "NOT_APPLICABLE",
      governed_revision: {
        work_id: "work-aligned",
        revision_number: 2,
        motive: "Governed visibility motive",
        desired_outcome: "Governed alignment outcome",
        constraints: ["Confirmed constraint"],
        context_facts: ["Confirmed repository fact"],
      },
    }],
  );

  assert.equal(projection.status.label, "Understood");
  assert.equal(projection.status.tone, "status-completed");
  assert.deepEqual(Array.from(projection.human.statements), [
    "Make the current production direction visible.",
  ]);
  assert.equal(projection.interpreted.currency, "Current advisory interpretation");
  assert.equal(projection.interpreted.motive, "Improve production visibility");
  assert.equal(projection.governed.revision, "Work Reality revision 2");
  assert.equal(projection.governed.motive, "Governed visibility motive");
  assert.deepEqual(Array.from(projection.shared.confirmedConstraints), [
    "Confirmed constraint",
  ]);
  assert.deepEqual(Array.from(projection.shared.relevantFacts), [
    "Confirmed repository fact",
  ]);
  assert.deepEqual(Array.from(projection.shared.unresolvedQuestions), []);
});

test("Control Room Slice 2 projects pending Human authority without admitting Reality", () => {
  const projection = viewModel.understandingAlignmentProjection(
    { work_id: "work-pending" },
    [{
      current_work_id: "work-pending",
      human_said: ["Please change the admitted Work direction."],
      latest_assessment: { assessment_id: "assessment-pending" },
      latest_assessment_current: true,
      interpreted_motive: "Candidate changed direction",
      desired_outcome: "Candidate changed outcome",
      unresolved_material_questions: [],
      readiness: { status: "READY" },
      work_revision_admission_status: "PENDING_HUMAN",
      governed_revision: null,
    }],
  );

  assert.equal(projection.status.label, "Waiting for Human decision");
  assert.equal(
    projection.status.basis,
    "Existing WIC Reality reports a pending Human decision.",
  );
  assert.equal(projection.interpreted.motive, "Candidate changed direction");
  assert.equal(projection.governed.available, false);
  assert.equal(projection.governed.motive, "Not governed.");
  assert.deepEqual(Array.from(projection.shared.confirmedConstraints), []);
});

test("Control Room Slice 2 exposes stale and unresolved assessment conditions", () => {
  const stale = viewModel.understandingAlignmentProjection(
    { work_id: "work-stale" },
    [{
      current_work_id: "work-stale",
      latest_assessment: { assessment_id: "assessment-stale" },
      latest_assessment_current: false,
      interpreted_motive: "Earlier interpretation",
      unresolved_material_questions: [],
      readiness: { status: "READY" },
      work_revision_admission_status: "NOT_APPLICABLE",
    }],
  );
  assert.equal(stale.status.label, "Needs clarification");
  assert.equal(stale.interpreted.currency, "Stale advisory interpretation");
  assert.equal(stale.status.basis, "The latest WIC assessment is no longer current.");

  const unresolved = viewModel.understandingAlignmentProjection(
    { work_id: "work-unresolved" },
    [{
      current_work_id: "work-unresolved",
      latest_assessment: { assessment_id: "assessment-current" },
      latest_assessment_current: true,
      unresolved_material_questions: ["Which repository is authoritative?"],
      readiness: { status: "NOT_READY" },
      work_revision_admission_status: "NOT_APPLICABLE",
    }],
  );
  assert.equal(unresolved.status.label, "Needs clarification");
  assert.equal(unresolved.status.basis, "1 unresolved material question remains.");
  assert.deepEqual(Array.from(unresolved.shared.unresolvedQuestions), [
    "Which repository is authoritative?",
  ]);
});

test("Control Room Slice 2 remains explicit when no WIC Reality matches the Work", () => {
  const projection = viewModel.understandingAlignmentProjection(
    { work_id: "work-without-interaction" },
    [],
  );

  assert.equal(projection.available, false);
  assert.equal(projection.status.label, "Needs clarification");
  assert.deepEqual(Array.from(projection.human.statements), []);
  assert.equal(projection.interpreted.currency, "No advisory interpretation");
  assert.equal(projection.governed.revision, "No governed Work Reality revision");
  assert.equal(projection.shared.understoodObjective, "No understood objective is available.");
});

test("Control Room Slice 3 projects current direction from exact Steering Reality", () => {
  const projection = viewModel.currentDirectionProjection(
    { work_id: "work-direction" },
    {
      work_id: "work-direction",
      active_revision_number: 3,
      current_step: {
        type: "PRODUCE",
        objective: "Implement the admitted projection",
        state: "CURRENT",
      },
      known_next_steps: [{
        type: "VERIFY_ACCEPT",
        objective: "Verify the produced projection",
        state: "KNOWN",
      }],
      latest_decision: {
        reason: "The design step completed with governed evidence.",
        reality_refs: [
          { kind: "WORK", identity: "work-direction" },
          { kind: "SEMANTIC_RESULT", identity: "result-1" },
        ],
      },
      selection_rationale: "Current Reality admits the bounded production step.",
      steering_outcome: "AUTO_CONTINUE",
      automatic_progression_state: "RUNNING",
      human_attention_required: false,
      last_stop_reason: null,
    },
    [],
  );

  assert.equal(projection.available, true);
  assert.equal(projection.revision, "Plan revision 3");
  assert.equal(projection.direction, "Implement the admitted projection");
  assert.equal(projection.currentStep, "PRODUCE - CURRENT");
  assert.equal(projection.nextStep, "VERIFY_ACCEPT: Verify the produced projection");
  assert.equal(projection.rationale, "Current Reality admits the bounded production step.");
  assert.deepEqual(Array.from(projection.realityBasis), [
    "WORK: work-direction",
    "SEMANTIC_RESULT: result-1",
  ]);
  assert.equal(projection.condition, "Steering outcome: AUTO_CONTINUE");
});

test("Control Room Slice 3 preserves blockers and missing Plan Reality", () => {
  const blocked = viewModel.currentDirectionProjection(
    { work_id: "work-blocked" },
    {
      work_id: "work-blocked",
      active_revision_number: 2,
      current_step: { type: "HUMAN_DECISION", objective: "Choose direction", state: "CURRENT" },
      known_next_steps: [],
      latest_decision: null,
      selection_rationale: null,
      automatic_progression_state: "STOPPED",
      steering_outcome: "HUMAN_ATTENTION",
      human_attention_required: true,
      last_stop_reason: "HUMAN_ATTENTION",
    },
    [{ work_id: "work-blocked", reason: "Architecture authority is required." }],
  );
  assert.equal(blocked.nextStep, "No known next step available.");
  assert.equal(blocked.rationale, "No admitted Plan rationale available.");
  assert.equal(
    blocked.condition,
    "Human decision required: Architecture authority is required.",
  );

  const missing = viewModel.currentDirectionProjection(
    { work_id: "work-current" },
    { work_id: "different-work" },
    [],
  );
  assert.equal(missing.available, false);
  assert.equal(missing.direction, "No admitted production direction available.");
  assert.deepEqual(Array.from(missing.realityBasis), []);
});

test("Control Room Slice 3 explains a trusted result active at its baseline", () => {
  const projection = viewModel.trustSummaryProjection(
    {
      status: "RUNNING",
      work_complete: false,
      current_production_cycle_trusted: true,
      latest_trusted_runtime_commit_id: "runtime-commit-1",
    },
    {
      status: "COMPLETED",
      trusted_result: true,
      verification_summary: ["PATH_SCOPE: PASS", "NODE_TEST_TARGET: PASS"],
      runtime_activation: {
        state: "ACTIVE_AT_TRUSTED_BASELINE",
        active_application_revision: "revision-2",
        current_trusted_baseline_revision: "revision-2",
        current_trusted_baseline_tree_identity: "tree-2",
        reason: "Active Runtime matches the Current Trusted Baseline.",
      },
    },
  );

  assert.equal(projection.state, "Trusted and active");
  assert.equal(
    projection.completion,
    "Current production cycle completion and trust recorded by existing Work Reality.",
  );
  assert.equal(projection.verification, "PATH_SCOPE: PASS | NODE_TEST_TARGET: PASS");
  assert.equal(projection.runtimeCommit, "Runtime Commit runtime-commit-1");
  assert.equal(projection.trustedBaseline, "Revision revision-2 - tree tree-2");
  assert.equal(projection.activeRuntime, "ACTIVE_AT_TRUSTED_BASELINE - revision revision-2");
  assert.equal(projection.trustedRepository, true);
  assert.equal(projection.activeAtTrusted, true);
});

test("Control Room Slice 3 does not hide trusted baseline and Active Runtime divergence", () => {
  const projection = viewModel.trustSummaryProjection(
    { status: "COMPLETED", work_complete: true },
    {
      status: "COMPLETED",
      trusted_result: true,
      verification_summary: ["NODE_TEST_TARGET: PASS"],
      runtime_activation: {
        state: "ACTIVATION_REQUIRED",
        active_application_revision: "revision-1",
        current_trusted_baseline_revision: "revision-2",
        current_trusted_baseline_tree_identity: "tree-2",
        reason: "Active Runtime is behind the Current Trusted Baseline.",
      },
    },
  );

  assert.equal(projection.state, "Trusted repository result; activation pending");
  assert.equal(projection.activeAtTrusted, false);
  assert.equal(projection.activeRuntime, "ACTIVATION_REQUIRED - revision revision-1");
  assert.equal(
    projection.basis,
    "Active Runtime is behind the Current Trusted Baseline.",
  );
});

test("Control Room Slice 3 keeps incomplete and unverified Reality explicit", () => {
  const projection = viewModel.trustSummaryProjection(
    { status: "RUNNING", work_complete: false },
    {
      status: "RUNNING",
      trusted_result: false,
      verification_summary: [],
      remaining_blocker_or_risk: "Verification has not completed.",
      runtime_activation: null,
    },
  );

  assert.equal(projection.state, "Not trusted yet");
  assert.equal(projection.completion, "Not complete - Work status: RUNNING");
  assert.equal(projection.verification, "No Verification evidence is available.");
  assert.equal(projection.runtimeCommit, "No trusted Runtime Commit recorded.");
  assert.equal(projection.trustedBaseline, "Current Trusted Baseline is not available.");
  assert.equal(projection.activeRuntime, "Active Runtime Reality is not available.");
  assert.equal(projection.basis, "Verification has not completed.");
});

test("Work Composer preserves the user's expanded state across reloads", () => {
  assert.match(
    appSource,
    /const COMPOSER_EXPANDED_STORAGE_KEY = "spg\.workComposer\.expanded"/,
  );
  assert.match(
    appSource,
    /localStorage\.getItem\(COMPOSER_EXPANDED_STORAGE_KEY\)/,
  );
  assert.match(
    appSource,
    /if \(stored === "true" \|\| stored === "false"\) \{\s*setComposerExpanded\(stored === "true"\)/,
  );
  assert.match(
    appSource,
    /setComposerExpanded\(nextExpanded\);\s*try \{\s*localStorage\.setItem\(COMPOSER_EXPANDED_STORAGE_KEY, String\(nextExpanded\)\)/,
  );
  assert.match(
    appSource,
    /restoreComposerExpanded\(\);\s*consumeNewWorkEntry\(\);\s*reloadWorkspace\(\)/,
  );
  assert.ok((appSource.match(/catch \(_error\)/g) || []).length >= 2);
});

test("pre-Work composer keeps messaging separate from explicit governed admission", () => {
  assert.match(appSource, /apiRequest\("\/api\/interactions"/);
  assert.match(appSource, /\/api\/interactions\/\$\{state\.selectedInteractionId\}\/turns/);
  assert.match(appSource, /new globalThis\.EventSource\(/);
  assert.match(appSource, /message\.delta/);
  assert.match(appSource, /message\.reset/);
  assert.match(appSource, /message\.completed/);
  assert.match(appSource, /latestWattMessage/);
  assert.doesNotMatch(appSource, /apiRequest\("\/api\/works", \{ method: "POST"/);
  assert.match(appSource, /No Work was created/);
  assert.match(appSource, /\/api\/interactions\/\$\{projection\.interaction_id\}\/admit-work/);
  assert.match(appSource, /assessment_id: assessment\.assessment_id/);
  assert.match(appSource, /basis_fingerprint: assessment\.basis_fingerprint/);
  assert.match(appSource, /admitWorkControl\.addEventListener\("click", admitInteractionWork\)/);
  assert.doesNotMatch(appSource, /countdown/i);
});

test("WIC Slice 4 exposes Human-governed Work transition controls only", () => {
  assert.match(appSource, /work-transition-decisions/);
  assert.match(appSource, /CONTINUE_CURRENT_WORK/);
  assert.match(appSource, /START_NEW_WORK/);
  assert.match(appSource, /DISMISSED/);
  assert.match(appSource, /No Work or production authority was created/);
  assert.doesNotMatch(
    appSource,
    /apiRequest\("\/api\/works",\s*\{\s*method:\s*"POST"/,
  );
});

test("explicit New Work entry clears restored context without creating Work authority", () => {
  const htmlSource = fs.readFileSync(
    path.join(repositoryRoot, "src", "spg", "web", "index.html"),
    "utf8",
  );
  const deliverySource = fs.readFileSync(
    path.join(repositoryRoot, "src", "spg", "web", "delivery.html"),
    "utf8",
  );
  assert.match(htmlSource, /id="new-interaction-control"[^>]*>New Work</);
  assert.match(deliverySource, /id="new-work-entry"[^>]*href="\/app\?new=1"/);
  assert.match(deliverySource, /不会继承当前 Work 上下文或生产权限/);
  assert.match(appSource, /function consumeNewWorkEntry\(\)/);
  assert.match(appSource, /url\.searchParams\.get\("new"\) !== "1"/);
  assert.match(appSource, /state\.freshInteraction = true/);
  assert.match(appSource, /localStorage\.removeItem\(INTERACTION_STORAGE_KEY\)/);
  assert.match(appSource, /history\.replaceState/);
  assert.doesNotMatch(appSource, /apiRequest\("\/api\/works",\s*\{\s*method:\s*"POST"/);
});

test("active Work interaction keeps revision admission explicit and Human governed", () => {
  assert.match(appSource, /work-revision-decisions/);
  assert.match(appSource, /work_revision_admission_status === "PENDING_HUMAN"/);
  assert.match(appSource, /approve-work-revision/);
  assert.match(appSource, /reject-work-revision/);
  assert.match(appSource, /refine-work-revision/);
});

test("streaming assistant output occupies one message lifecycle until persisted truth arrives", () => {
  const projection = {
    conversation_messages: [{
      actor: "HUMAN",
      turn_id: "turn-1",
      content: "Design an operations platform.",
      processing_status: "PROCESSING",
    }],
    records: [],
  };
  const streaming = {
    turnId: "turn-1",
    content: "Let us start with the operator and problem.",
    status: "PROCESSING",
  };
  const during = viewModel.interactionConversationMessages(projection, streaming);
  assert.equal(during.length, 2);
  assert.equal(during[1].actor, "WATT");
  assert.equal(during[1].turn_id, "turn-1");
  assert.equal(during[1].content, streaming.content);
  assert.equal(during[1].streaming, true);

  const persisted = {
    ...projection,
    conversation_messages: [
      ...projection.conversation_messages,
      { actor: "WATT", turn_id: "turn-1", content: streaming.content, processing_status: "COMPLETED" },
    ],
  };
  const after = viewModel.interactionConversationMessages(persisted, streaming);
  assert.equal(after.length, 2);
  assert.equal(after[1].processing_status, "COMPLETED");
  assert.equal(after[1].streaming, undefined);
  assert.match(appSource, /streamingAssistantMessage\.content = streamed/);
  assert.doesNotMatch(appSource, /elements\.wattResponse\.textContent = streamed/);
});


function conversationHarness(request) {
  const state = {
    busy: false, selectedInteractionId: "interaction-1", sharedUnderstanding: { turns: [], conversation_messages: [] },
    sendInFlight: false, finishingTurn: false, activeInteractionTurnId: "", streamingAssistantMessage: null,
    interactionEventSource: null, streamFrame: null, outbox: [], drafts: {}, interactions: [],
  };
  const sources = [];
  const frames = [];
  const notices = [];
  let saved;
  let nextId = 0;
  class EventSource {
    constructor() { this.handlers = {}; sources.push(this); }
    addEventListener(name, handler) { this.handlers[name] = handler; }
    close() { this.closed = true; }
    emit(name, payload = {}) { return this.handlers[name]({ data: JSON.stringify(payload) }); }
  }
  class ApiError extends Error {
    constructor(status, code, message) { super(message); this.status = status; this.code = code; }
  }
  const harness = {
    state, viewModel, ApiError, EventSource, sources, frames, notices,
    crypto: { randomUUID: () => `pending-${++nextId}` },
    elements: { workRequirement: { value: "" } },
    localStorage: { setItem() {} }, INTERACTION_STORAGE_KEY: "selection",
    setTimeout: (callback) => setTimeout(callback, 0),
    cancelAnimationFrame() {},
    renderInteraction() {}, renderComposer() {}, setSurface() {}, announce() {}, hideNotice() {},
    setBusy(value) { state.busy = value; },
    showNotice(error) { notices.push(error); },
    scheduleStreamRender() {
      if (state.streamFrame !== null) return;
      state.streamFrame = frames.length + 1;
      frames.push(() => {
        state.streamFrame = null;
        const streamed = state.streamingAssistantMessage;
        if (!streamed) return;
        if (streamed.pendingResponseDeltas && streamed.pendingResponseDeltas.length) {
          streamed.content += streamed.pendingResponseDeltas.shift();
        } else if (streamed.deferredFinalContent !== null && streamed.deferredFinalContent !== undefined) {
          streamed.content = streamed.deferredFinalContent;
          streamed.deferredFinalContent = null;
          streamed.phase = "FINAL";
        }
        if ((streamed.pendingResponseDeltas && streamed.pendingResponseDeltas.length)
          || (streamed.deferredFinalContent !== null && streamed.deferredFinalContent !== undefined)) {
          harness.scheduleStreamRender();
          return;
        }
        if (streamed.pendingSettlement) {
          const settlement = streamed.pendingSettlement;
          streamed.pendingSettlement = null;
          void harness.finishInteractionTurn(settlement.interactionId, settlement.turnId, settlement.failure);
        }
      });
    },
    persistComposer() { saved = JSON.parse(JSON.stringify(state.outbox)); },
    saveDraft() { state.drafts[state.selectedInteractionId || "new"] = harness.elements.workRequirement.value; harness.persistComposer(); },
    apiRequest: request,
  };
  harness.globalThis = harness;
  vm.runInNewContext(appSource.slice(appSource.indexOf("  function observationIsCurrent("), appSource.indexOf("  async function admitInteractionWork()")), harness);
  harness.submit = async (content) => {
    harness.elements.workRequirement.value = content;
    await harness.continueInteraction({ preventDefault() {} });
  };
  harness.flushFrames = () => { while (frames.length) frames.shift()(); };
  harness.saved = () => saved;
  return harness;
}

async function settle() {
  for (let index = 0; index < 12; index += 1) await Promise.resolve();
}

test("Turn subscription precedes projection refresh; fast completion cannot overwrite saved truth", async () => {
  let resolveProjection;
  let harness;
  const stale = new Promise((resolve) => { resolveProjection = resolve; });
  harness = conversationHarness(async (url) => {
    if (url.endsWith("/turns")) return { turn_id: "turn-1", status: "RECEIVED" };
    assert.equal(harness.sources.length, 1, "subscribe before waiting for projection");
    return stale;
  });
  await harness.submit("Build a Web application.");
  await settle();
  assert.equal(harness.state.sharedUnderstanding.conversation_messages.at(-1).content, "Build a Web application.");
  const completed = { turns: [{ turn_id: "turn-1", status: "COMPLETED" }] };
  harness.state.activeInteractionTurnId = "";
  harness.state.sharedUnderstanding = completed;
  resolveProjection({ turns: [{ turn_id: "turn-1", status: "PROCESSING" }] });
  await settle();
  assert.equal(harness.state.sharedUnderstanding, completed);
  assert.equal(harness.state.sendInFlight, false);
});

test("messages queued while POST is in flight wait for persisted COMPLETED, exactly once", async () => {
  let acknowledge;
  let posts = 0;
  let projection = { turns: [], conversation_messages: [] };
  const harness = conversationHarness(async (url) => {
    if (url.endsWith("/turns")) {
      posts += 1;
      if (posts === 1) return new Promise((resolve) => { acknowledge = resolve; });
      return { turn_id: "turn-2", status: "RECEIVED" };
    }
    return projection;
  });
  await harness.submit("First");
  await harness.submit("Second");
  await harness.submit(""); // repeated submit after the composer was cleared
  assert.equal(posts, 1);
  assert.equal(harness.state.outbox[1].status, "queued");
  projection = { turns: [{ turn_id: "turn-1", status: "PROCESSING" }], conversation_messages: [] };
  acknowledge({ turn_id: "turn-1", status: "RECEIVED" });
  await settle();
  assert.equal(posts, 1);
  assert.equal(harness.state.outbox[0].waitForTurnId, "turn-1");
  harness.sources[0].emit("turn.status", { status: "COMPLETED" });
  await settle();
  assert.equal(posts, 1, "status or end of displayed text is insufficient to drain");
  projection = { turns: [{ turn_id: "turn-1", status: "COMPLETED" }], conversation_messages: [] };
  harness.sources[0].emit("message.completed");
  harness.flushFrames();
  await settle();
  assert.equal(posts, 2);
  harness.sources[0].emit("message.completed");
  await settle();
  assert.equal(posts, 2, "duplicate terminal event cannot resend");
});

test("uncertain delivery remains visible and survives refresh without an automatic retry", async () => {
  let posts = 0;
  const harness = conversationHarness(async () => { posts += 1; throw new Error("response lost"); });
  await harness.submit("Keep this exact input");
  await settle();
  assert.equal(harness.state.outbox[0].status, "uncertain");
  assert.equal(harness.saved()[0].content, "Keep this exact input");
  await harness.drainOutbox();
  assert.equal(posts, 1);
  const recovered = viewModel.restoreInteractionOutbox(harness.saved());
  assert.equal(recovered[0].status, "uncertain");
  assert.equal(viewModel.nextInteractionOutboxItem(recovered, "interaction-1", { turns: [] }), null);
});

test("failed replies pause later messages, keeping exact content for explicit resume", async () => {
  let posts = 0;
  let projection = { turns: [{ turn_id: "turn-1", status: "PROCESSING" }] };
  const harness = conversationHarness(async (url) => {
    if (url.endsWith("/turns")) { posts += 1; return { turn_id: "turn-1", status: "RECEIVED" }; }
    return projection;
  });
  await harness.submit("First"); await settle();
  await harness.submit("Continue after the first reply");
  projection = { turns: [{ turn_id: "turn-1", status: "FAILED" }] };
  harness.sources[0].emit("turn.failed", { code: "TEST_FAILURE", message: "Fixture failure" });
  harness.flushFrames();
  await settle();
  assert.equal(posts, 1);
  assert.equal(harness.state.outbox[0].status, "paused");
  assert.equal(harness.state.outbox[0].content, "Continue after the first reply");
  assert.equal(harness.notices[0].code, "TEST_FAILURE");
});

test("switching conversations ignores stale deltas and leaves the prior queue isolated", async () => {
  const harness = conversationHarness(async () => ({ turns: [] }));
  harness.state.outbox = [{ id: "pending", interactionId: "interaction-1", content: "Only for one", status: "queued", waitForTurnId: "turn-1" }];
  harness.observeInteractionTurn("interaction-1", "turn-1");
  harness.pauseOutbox("interaction-1");
  harness.stopTurnObservation();
  harness.state.selectedInteractionId = "interaction-2";
  harness.observeInteractionTurn("interaction-2", "turn-2");
  harness.sources[0].emit("message.delta", { delta: "wrong conversation" });
  harness.sources[0].emit("message.completed");
  await settle();
  assert.equal(harness.state.streamingAssistantMessage.content, "");
  assert.equal(harness.state.activeInteractionTurnId, "turn-2");
  assert.equal(harness.state.outbox[0].status, "paused");
  assert.equal(viewModel.nextInteractionOutboxItem(harness.state.outbox, "interaction-2", { turns: [] }), null);
});

test("controlled WIC response events evolve one bubble and suppress duplicate replay", () => {
  const harness = conversationHarness(async () => ({ turns: [] }));
  harness.observeInteractionTurn("interaction-1", "turn-1");
  const source = harness.sources[0];
  const provisional = {
    sequence: 3, response_id: "turn-1",
    content: "我已捕捉到新增约束：登录后不要跳首页。",
  };
  source.emit("response.provisional", provisional);
  source.emit("response.provisional", provisional);
  assert.equal(harness.state.streamingAssistantMessage.content, provisional.content);
  source.emit("response.refinement", {
    sequence: 4, response_id: "turn-1", reconciliation: "REFINE",
    content: null,
  });
  source.emit("response.stream.started", {
    sequence: 5, response_id: "turn-1", reconciliation: "REFINE",
  });
  const firstDelta = {
    sequence: 6, response_id: "turn-1", reconciliation: "REFINE",
    content: "\n\n这不会改变",
  };
  source.emit("response.delta", firstDelta);
  source.emit("response.delta", firstDelta);
  source.emit("response.delta", {
    sequence: 7, response_id: "turn-1", reconciliation: "REFINE",
    content: "现有鉴权协议。",
  });
  harness.flushFrames();
  assert.equal(
    harness.state.streamingAssistantMessage.content,
    provisional.content + "\n\n这不会改变现有鉴权协议。",
  );
  source.emit("response.final", {
    sequence: 8, response_id: "turn-1",
    content: provisional.content + "\n\n这不会改变现有鉴权协议。",
  });
  harness.flushFrames();
  assert.equal(harness.state.streamingAssistantMessage.phase, "FINAL");
  assert.equal(harness.state.streamingAssistantMessage.responseSequence, 8);
  assert.equal(harness.state.streamingAssistantMessage.turnId, "turn-1");
});

test("refresh during Deep WIC rebuilds provisional text without duplication", () => {
  const harness = conversationHarness(async () => ({ turns: [] }));
  harness.observeInteractionTurn("interaction-1", "turn-1");
  harness.sources[0].emit("response.provisional", {
    sequence: 3, response_id: "turn-1", content: "已记录这个明确约束。",
  });
  harness.stopTurnObservation();
  harness.observeInteractionTurn("interaction-1", "turn-1");
  harness.sources[1].emit("response.provisional", {
    sequence: 3, response_id: "turn-1", content: "已记录这个明确约束。",
  });
  harness.sources[1].emit("response.refinement", {
    sequence: 4, response_id: "turn-1", reconciliation: "REFINE",
    content: null,
  });
  harness.sources[1].emit("response.stream.started", {
    sequence: 5, response_id: "turn-1", reconciliation: "REFINE",
  });
  harness.sources[1].emit("response.delta", {
    sequence: 6, response_id: "turn-1", reconciliation: "REFINE",
    content: "\n\n原有范围",
  });
  harness.sources[1].emit("response.delta", {
    sequence: 7, response_id: "turn-1", reconciliation: "REFINE",
    content: "保持不变。",
  });
  harness.flushFrames();
  assert.equal(
    harness.state.streamingAssistantMessage.content,
    "已记录这个明确约束。\n\n原有范围保持不变。",
  );
});

test("SSE disconnect falls back to observation and drains once after saved completion", async () => {
  let posts = 0;
  let polls = 0;
  const harness = conversationHarness(async (url) => {
    if (url.endsWith("/turns")) { posts += 1; return { turn_id: "turn-2", status: "RECEIVED" }; }
    if (url.endsWith("/turn-1")) { polls += 1; return { status: "COMPLETED" }; }
    return { turns: [{ turn_id: "turn-1", status: "COMPLETED" }] };
  });
  harness.state.outbox = [{ id: "pending", interactionId: "interaction-1", content: "Next", status: "queued", waitForTurnId: "turn-1" }];
  harness.observeInteractionTurn("interaction-1", "turn-1");
  harness.sources[0].onerror();
  harness.sources[0].onerror();
  await settle();
  assert.equal(polls, 1);
  assert.equal(posts, 1);
});

test("restored queues pause, interrupted sends remain uncertain, and failed bases never auto-drain", () => {
  const restored = viewModel.restoreInteractionOutbox([
    { id: "one", interactionId: "a", content: "First", status: "queued", waitForTurnId: "turn-a" },
    { id: "two", interactionId: "b", content: "Second", status: "sending" },
  ]);
  assert.equal(restored[0].status, "paused");
  assert.equal(restored[1].status, "uncertain");
  restored[0].status = "queued";
  assert.equal(viewModel.nextInteractionOutboxItem(restored, "a", { turns: [{ turn_id: "turn-a", status: "FAILED" }] }), null);
  assert.equal(viewModel.nextInteractionOutboxItem(restored, "a", { turns: [{ turn_id: "turn-a", status: "COMPLETED" }] }).id, "one");
});

test("stream bursts repaint one message per frame and preserve historical DOM nodes", () => {
  class Node {
    constructor(className = "", text = "") {
      this.className = className; this.dataset = {}; this.children = []; this._text = text; this.writes = 0;
      this.classList = { toggle() {} };
    }
    get textContent() { return this._text; }
    set textContent(value) { this._text = value; this.writes += 1; }
    append(child) { child.parent = this; this.children.push(child); }
    insertBefore(child, next) {
      if (child.parent) child.remove();
      child.parent = this;
      const position = next ? this.children.indexOf(next) : this.children.length;
      this.children.splice(position, 0, child);
    }
    remove() { this.parent.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; }
    setAttribute() {}
    querySelector(selector) { return this.children.find((child) => child.className === selector.slice(1)); }
  }
  const frames = [];
  const state = {
    selectedInteractionId: "a", streamFrame: null,
    sharedUnderstanding: { conversation_messages: [{ actor: "HUMAN", turn_id: "t", content: "Question" }] },
    streamingAssistantMessage: { turnId: "t", content: "Answer", status: "PROCESSING" },
  };
  const harness = {
    state, viewModel, elements: { interactionHistory: new Node(), interactionProcessingStatus: new Node() },
    createElement: (_tag, className, text) => new Node(className, text),
    requestAnimationFrame: (callback) => { frames.push(callback); return frames.length; },
  };
  harness.globalThis = harness;
  vm.runInNewContext(appSource.slice(appSource.indexOf("  function messageKey("), appSource.indexOf("  function persistComposer(")), harness);
  harness.renderConversation();
  const [human, assistant] = harness.elements.interactionHistory.children;
  const humanContent = human.children[1];
  const assistantContent = assistant.children[1];
  const priorWrites = assistantContent.writes;
  for (let index = 0; index < 100; index += 1) {
    state.streamingAssistantMessage.content += ".";
    harness.scheduleStreamRender();
  }
  assert.equal(frames.length, 1);
  frames.shift()();
  assert.equal(assistantContent.writes, priorWrites + 1);
  assert.equal(humanContent.writes, 1);
  assert.equal(assistantContent.textContent, `Answer${".".repeat(100)}`);
  state.sharedUnderstanding.conversation_messages.push({ actor: "WATT", turn_id: "t", content: assistantContent.textContent, processing_status: "COMPLETED" });
  state.streamingAssistantMessage = null;
  harness.renderConversation();
  assert.equal(harness.elements.interactionHistory.children[0], human);
  assert.equal(harness.elements.interactionHistory.children[1], assistant);
});

test("governed response deltas paint one received chunk per frame", () => {
  class Node {
    constructor(className = "", text = "") {
      this.className = className; this.dataset = {}; this.children = []; this._text = text;
      this.classList = { toggle() {} };
    }
    get textContent() { return this._text; }
    set textContent(value) { this._text = value; }
    append(child) { child.parent = this; this.children.push(child); }
    insertBefore(child, next) {
      if (child.parent) child.remove();
      child.parent = this;
      const position = next ? this.children.indexOf(next) : this.children.length;
      this.children.splice(position, 0, child);
    }
    remove() { this.parent.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; }
    setAttribute() {}
    querySelector(selector) { return this.children.find((child) => child.className === selector.slice(1)); }
  }
  const frames = [];
  const state = {
    selectedInteractionId: "a", streamFrame: null,
    sharedUnderstanding: { conversation_messages: [{ actor: "HUMAN", turn_id: "t", content: "Question" }] },
    streamingAssistantMessage: {
      turnId: "t", content: "Receipt", status: "PROCESSING",
      pendingResponseDeltas: [" first", " second"], deferredFinalContent: null,
      pendingSettlement: null,
    },
  };
  const harness = {
    state, viewModel, elements: { interactionHistory: new Node(), interactionProcessingStatus: new Node() },
    createElement: (_tag, className, text) => new Node(className, text),
    requestAnimationFrame: (callback) => { frames.push(callback); return frames.length; },
  };
  harness.globalThis = harness;
  vm.runInNewContext(appSource.slice(appSource.indexOf("  function messageKey("), appSource.indexOf("  function persistComposer(")), harness);
  harness.renderConversation();
  harness.scheduleStreamRender();
  assert.equal(frames.length, 1);
  frames.shift()();
  assert.equal(harness.elements.interactionHistory.children[1].children[1].textContent, "Receipt first");
  assert.equal(frames.length, 1);
  frames.shift()();
  assert.equal(harness.elements.interactionHistory.children[1].children[1].textContent, "Receipt first second");
});

test("queue capacity leaves the unsent draft intact", async () => {
  const harness = conversationHarness(async () => { throw new Error("must not submit"); });
  harness.state.activeInteractionTurnId = "active";
  await harness.submit("One"); await harness.submit("Two"); await harness.submit("Three");
  await harness.submit("Fourth draft");
  assert.equal(harness.state.outbox.length, 3);
  assert.equal(harness.elements.workRequirement.value, "Fourth draft");
  assert.equal(harness.notices[0].code, "OUTBOX_FULL");
});

test("a rejected POST pauses for explicit retry and never loses the message", async () => {
  let harness;
  harness = conversationHarness(async () => { throw new harness.ApiError(409, "TURN_ACTIVE", "Busy"); });
  await harness.submit("Do not lose this"); await settle();
  assert.equal(harness.state.outbox[0].status, "paused");
  assert.equal(harness.saved()[0].content, "Do not lose this");
});

test("a reply completing during Refresh drains its queued message when busy clears", async () => {
  let releaseHealth;
  let posts = 0;
  const projection = { turns: [{ turn_id: "turn-1", status: "COMPLETED" }], conversation_messages: [] };
  const harness = conversationHarness(async (url) => {
    if (url.endsWith("/turns")) {
      posts += 1;
      return { turn_id: "turn-2", status: "RECEIVED" };
    }
    return projection;
  });
  harness.document = { querySelectorAll: () => [] };
  harness.loadHealth = () => new Promise((resolve) => { releaseHealth = resolve; });
  harness.loadCollections = async () => {};
  vm.runInNewContext(appSource.slice(appSource.indexOf("  function setBusy("), appSource.indexOf("  function setSurface(")), harness);
  vm.runInNewContext(appSource.slice(appSource.indexOf("  async function reloadWorkspace("), appSource.indexOf("  async function createGoal(")), harness);
  harness.state.outbox = [{ id: "pending", interactionId: "interaction-1", content: "Next after refresh", status: "queued", waitForTurnId: "turn-1" }];
  harness.observeInteractionTurn("interaction-1", "turn-1");
  const refreshing = harness.reloadWorkspace();
  assert.equal(harness.state.busy, true);
  harness.sources[0].emit("message.completed");
  harness.flushFrames();
  await settle();
  assert.equal(harness.state.activeInteractionTurnId, "");
  assert.equal(harness.state.outbox[0].status, "queued");
  assert.equal(posts, 0, "UI mutation must finish before submitting the next Turn");
  releaseHealth();
  await refreshing;
  await settle();
  assert.equal(harness.state.busy, false);
  assert.equal(posts, 1, "releasing busy must retry an eligible queued message");
  assert.equal(harness.state.activeInteractionTurnId, "turn-2");
  harness.setBusy(false);
  await settle();
  assert.equal(posts, 1, "repeated releases remain protected by the active Turn guard");
});
