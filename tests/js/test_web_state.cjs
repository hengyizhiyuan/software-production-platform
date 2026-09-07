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
    /restoreComposerExpanded\(\);\s*reloadWorkspace\(\)/,
  );
  assert.ok((appSource.match(/catch \(_error\)/g) || []).length >= 2);
});

test("pre-Work composer keeps messaging separate from explicit governed admission", () => {
  assert.match(appSource, /apiRequest\("\/api\/interactions"/);
  assert.match(appSource, /\/api\/interactions\/\$\{state\.selectedInteractionId\}\/records/);
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

test("active Work interaction keeps revision admission explicit and Human governed", () => {
  assert.match(appSource, /work-revision-decisions/);
  assert.match(appSource, /work_revision_admission_status === "PENDING_HUMAN"/);
  assert.match(appSource, /approve-work-revision/);
  assert.match(appSource, /reject-work-revision/);
  assert.match(appSource, /refine-work-revision/);
});
