"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(path.resolve(__dirname, "../../src/spg/web/p1-readiness.js"), "utf8");

class Element {
  constructor() { this.children = []; this.handlers = {}; this.dataset = {}; this.value = ""; this.textContent = ""; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  setAttribute(name, value) { this[name] = value; }
  click() { return this.handlers.click?.({ preventDefault() {} }); }
}

test("P1 Product/Work history and operator health render from persisted API facts", async () => {
  const ids = ["selected-work", "refresh-control", "p1-product-list", "p1-product-detail", "p1-product-summary", "p1-product-assets",
    "p1-work-product", "p1-bind-work", "p1-work-product-summary", "p1-diagnosis", "p1-economics",
    "p1-history", "p1-product-form", "p1-product-name", "p1-repository-form", "p1-repository-url",
    "p1-platform-status", "p1-connector-list", "p1-credential-list", "p1-evaluation-list",
    "p1-operator-panel", "p1-github-grant-form", "p1-github-repository", "p1-github-permission"];
  const elements = Object.fromEntries(ids.map((id) => [id, new Element()]));
  elements["selected-work"].dataset = { workId: "w1", productId: "p1" };
  const requests = [];
  const routes = {
    "/api/products": [{ id: "p1", name: "Finance Product", lifecycle: "ACTIVE",
      assets: [{ asset_kind: "REPOSITORY", reference: "https://github.com/example/finance.git" }],
      works: [{ id: "w1" }], current_sources: [{ reference: "https://github.com/example/finance.git",
        metadata: { repository_ref: "refs/heads/main", revision: "abc123" } }] }],
    "/api/works/w1/operations": { state: "WAITING_FOR_CAPACITY", root_cause: "Worker capacity unavailable",
      pwu: [{ id: "u1" }], queue: [{ id: "q1" }], verification: { count: 0 },
      candidate_ids: [], evidence_refs: ["executor-queue:q1"],
      economics: { wall_elapsed_seconds: 10, execution_seconds: 15, queue_wait_seconds: 4,
        critical_path_seconds: 9, token_usage: { status: "UNREPORTED", total_tokens: 0 },
        observed_provider_spend: { status: "UNREPORTED", amount: null },
        pwu_count: 1, join_count: 0, self_refine_event_count: 0 } },
    "/api/products/p1/history": { name: "Finance Product", timeline: [
      { at: "2026-09-26T09:00:00Z", kind: "WORK_REQUESTED", requirement: "Add reimbursement" }] },
    "/api/operations/connectors": { connectors: [], credentials: [] },
    "/api/operations/evaluations?limit=8": [],
    "/api/operations/summary": { workers: { healthy: 0, registered: 1 },
      queue: { active_count: 1, by_condition: { WAITING_RESOURCE: 1 } },
      leases: { unhealthy_count: 1 }, recent_self_refine_failures: 0,
      recent_work_provider_spend: { status: "UNREPORTED", sample_size: 1 } },
  };
  const context = {
    document: { getElementById: (id) => elements[id] || null, createElement: () => new Element() },
    MutationObserver: class { observe() {} },
    Option: class extends Element { constructor(label, value) { super(); this.textContent = label; this.value = value; } },
    fetch: async (url) => { requests.push(url); return { ok: true, json: async () => routes[url] }; },
  };
  vm.runInNewContext(script, context, { filename: "p1-readiness.js" });
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setImmediate(resolve));
  assert.match(elements["p1-product-summary"].textContent, /1 assets · 1 Works/);
  assert.match(elements["p1-product-assets"].children[0].textContent, /refs\/heads\/main · abc123/);
  assert.equal(elements["p1-bind-work"].disabled, true);
  assert.equal(elements["p1-diagnosis"].children[0].textContent, "Production: WAITING_FOR_CAPACITY");
  assert.match(elements["p1-economics"].children[2].textContent, /provider spend UNREPORTED \(unknown\)/);
  routes["/api/works/w1/operations"].economics.observed_provider_spend = {
    status: "PARTIAL", by_currency: { USD: 0.5 }, unreported_attempt_count: 2,
  };
  elements["refresh-control"].click();
  for (let i = 0; i < 3; i++) await new Promise((resolve) => setImmediate(resolve));
  assert.match(elements["p1-economics"].children[2].textContent,
    /provider spend PARTIAL: USD 0.5; 2 attempts unreported/);
  assert.match(elements["p1-history"].children[1].textContent, /Add reimbursement/);
  routes["/api/works/w1/operations"].state = "COMPLETED";
  routes["/api/works/w1/operations"].root_cause = "Work completed";
  elements["refresh-control"].click();
  for (let i = 0; i < 3; i++) await new Promise((resolve) => setImmediate(resolve));
  assert.equal(elements["p1-diagnosis"].children[0].textContent, "Production: COMPLETED");
  routes["/api/operations/connectors"] = {
    connectors: [{ id: "c1", capability_id: "git.branch.current", scope: "PLATFORM",
      health: "HEALTHY", enabled: true, provider: "git", capability_family: "SOURCE_CONTROL",
      owner_id: "platform", version: "1", maturity: "BUILT_IN", qualification: "BUILT_IN",
      credential_requirements: [], permissions_required: ["READ"], usage_count_status: "NOT_INSTRUMENTED",
      last_success_status: "NOT_INSTRUMENTED", failure_count: 1 }],
    credentials: [{ grant_id: "g1", repository_url: "https://github.com/example/finance.git",
      permission: "READ", credential_status: "ACTIVE", condition: "ACTIVE",
      provider: "GitHub", owner_id: "human:owner", scope: "REPOSITORY",
      credential_ref: "settings:SPG_GITHUB_READ_TOKEN", usage_count: 0, failure_count: 0 }],
  };
  routes["/api/operations/connectors/c1/history"] = [
    { created_at: "2026-09-26", action: "CONTROL_CHANGED", actor_id: "human:owner",
      detail: { evidence_ref: "probe:p1-q3" } },
  ];
  routes["/api/github/grants/g1/history"] = [
    { created_at: "2026-09-26", action: "CREATED", actor_id: "human:owner", detail: {} },
  ];
  elements["p1-operator-panel"].open = true;
  elements["p1-operator-panel"].handlers.toggle();
  for (let i = 0; i < 3; i++) await new Promise((resolve) => setImmediate(resolve));
  assert.match(elements["p1-platform-status"].textContent, /0\/1 workers healthy/);
  assert.match(elements["p1-platform-status"].textContent, /1 unhealthy leases/);
  assert.match(elements["p1-connector-list"].children[1].children[3].textContent, /NOT_INSTRUMENTED/);
  await elements["p1-connector-list"].children[1].children[5].click();
  assert.match(elements["p1-connector-list"].children[1].children[6].textContent, /probe:p1-q3/);
  assert.match(elements["p1-credential-list"].children[1].children[1].textContent, /settings:SPG_GITHUB_READ_TOKEN/);
  await elements["p1-credential-list"].children[1].children[3].click();
  assert.match(elements["p1-credential-list"].children[1].children[4].textContent, /CREATED/);
  assert.ok(requests.includes("/api/operations/summary"));
});
