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
const context = {};
context.globalThis = context;
vm.runInNewContext(source, context, { filename: "control-room.js" });
const controlRoom = context.WattControlRoom;

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

test("Production state maps observed queue and attempt facts without invented progress", () => {
  assert.equal(controlRoom.productionState({}, [{ condition: "WAITING_RESOURCE", wait_reason: "GPU unavailable" }], null).detail, "GPU unavailable");
  assert.equal(controlRoom.productionState({}, [{ condition: "EXECUTING" }], null).state, "RUNNING");
  assert.equal(controlRoom.productionState({}, [], { state: { runtime_mode: "RECOVERING" } }).state, "RECOVERING");
  assert.equal(controlRoom.productionState({ status: "COMPLETED" }, [], null).state, "FINISHED");
  assert.equal(controlRoom.productionState({ status: "NEEDS_ATTENTION", what_happens_next: "Choose a recovery path" }, [], null).detail, "Choose a recovery path");
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
  assert.match(app, /production\.insertBefore\(manual, result\)/);
  assert.match(app, /production\.insertBefore\(machineControls, result\)/);
  assert.match(app, /evidence\.append\(result\)/);
  assert.doesNotMatch(app, /reality\.append\(result\)/);
  assert.match(html, /<section id="actions-surface"/);
  assert.match(html, /id="agreement-action-panel"/);
  assert.match(app, /candidate-preview-panel/);
  assert.match(app, /agreementSelectionActions\.hidden = !selected/);
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

test("Production details are disclosed, while Actions contain only contextual controls", () => {
  assert.match(app, /evidence\.append\(result\)/);
  assert.match(html, /<section id="agreement-action-panel"[^>]+hidden>/);
  assert.match(html, /<details class="agreement-entry">/);
  assert.match(app, /agreementActionPanel\.hidden = !selected/);
  assert.match(app, /No action required\./);
  assert.doesNotMatch(app, /Exact Candidate \$\{preview\.repository_revision/);
});
