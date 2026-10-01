const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const script = fs.readFileSync(path.join(root, 'src/spg/web/experience.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'src/spg/web/experience.css'), 'utf8');
const principles = fs.readFileSync(path.join(root, 'docs/product/workspace-first-experience-principles.md'), 'utf8');

const helpers = script.slice(script.indexOf('  function renderWorkspaceAgenda(ws) {'),
  script.indexOf('  async function renderWorkspaceConversation(id) {'));
const workspace = script.slice(script.indexOf('  async function renderWorkspace(id) {'),
  script.indexOf('  async function renderWorkspaceConversation(id) {'));

test('primary Product Workspace has exactly four named quadrants in governed order', () => {
  assert.equal((workspace.match(/data-workspace-four-quadrant/g) || []).length, 1);
  assert.deepEqual([...helpers.matchAll(/data-workspace-quadrant="([^"]+)"/g)].map(match => match[1]),
    ['agenda', 'reality', 'actions', 'production']);
  assert.match(workspace, /data-workspace-four-quadrant[^`]*\$\{renderWorkspaceAgenda\(ws\)\}\$\{renderWorkspaceReality\([^}]+\)\}\$\{renderWorkspaceActions\([^}]+\)\}\$\{renderWorkspaceProduction\([^}]+\)\}<\/section><section class="workspace-conversation"/);
  assert.ok(workspace.indexOf('data-workspace-four-quadrant') < workspace.indexOf('workspace-conversation'));
  assert.match(css, /grid-template-areas:"agenda reality" "actions production"/);
  assert.match(css, /@media\(max-width:760px\)[^{]*\{[^}]*grid-template-areas:"agenda" "reality" "actions" "production"/);
});

test('Actions and Production retain the existing review and attention paths', () => {
  assert.match(helpers, /ws\.actions\.map\(renderAttention\)/);
  assert.match(helpers, /data-preview=/);
  assert.match(helpers, /data-diff=/);
  assert.match(helpers, /data-accept=/);
  assert.match(helpers, /const review = candidate\?\.candidate_fingerprint \?/);
  assert.match(helpers, /acceptance \? '当前成果已验收'/);
  assert.match(helpers, /当前无需你操作/);
  assert.match(helpers, /guardian[\s\S]*REPAIR_IN_PROGRESS/);
  assert.match(workspace, /id="workspace-turn-form"/);
  assert.match(script, /target\.hasAttribute\('data-focus-composer'\)/);
  assert.match(script, /data-conversation-attention="\$\{esc\(a\.id\)\}"/);
  assert.match(script, /attention_id:form\.dataset\.attentionId/);
});

test('canonical Product principle requires Human Governor approval for structural changes', () => {
  assert.match(principles, /## 11\. Workspace Four-Quadrant Invariant/);
  assert.match(principles, /WORKSPACE_FOUR_QUADRANT_LAYOUT_IMMUTABLE = TRUE/);
  assert.match(principles, /explicit\s+Human Governor approval/);
});
