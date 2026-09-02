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
    READY: "Ready",
    RUNNING: "Running",
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
  assert.deepEqual(Array.from(viewModel.workActions("READY")), ["ADVANCE"]);
  assert.deepEqual(Array.from(viewModel.workActions("RUNNING")), ["ADVANCE"]);
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

test("UI-08 through UI-13 use safe DOM rendering and one explicit advance call", () => {
  assert.doesNotMatch(appSource, /innerHTML|insertAdjacentHTML|document\.write/);
  assert.doesNotMatch(appSource, /setInterval|setTimeout|runUntilDone/);
  assert.match(appSource, /node\.textContent = String\(text\)/);
  assert.match(appSource, /attention\.available_actions\.forEach/);
  assert.equal((appSource.match(/\$\{workPath\}\/advance/g) || []).length, 1);
  assert.doesNotMatch(appSource, /SPG_DATABASE_URL|OPENAI_API_KEY|api[_-]?key/i);
});
