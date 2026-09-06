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

test("pre-Work composer uses Interaction truth and never creates Work", () => {
  assert.match(appSource, /apiRequest\("\/api\/interactions"/);
  assert.match(appSource, /\/api\/interactions\/\$\{state\.selectedInteractionId\}\/records/);
  assert.doesNotMatch(appSource, /apiRequest\("\/api\/works", \{ method: "POST"/);
  assert.match(appSource, /No Work was created/);
});
