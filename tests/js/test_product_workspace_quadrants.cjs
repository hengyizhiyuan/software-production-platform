const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

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

test('Workspace reports persisted Execution and verification without claiming early success', () => {
  const source = script.slice(script.indexOf('  function executionCopy(execution) {'),
    script.indexOf('  function actionText(raw) {'));
  const {executionCopy, verificationCopy, focusCopy} = vm.runInNewContext(
    `${source}; ({executionCopy, verificationCopy, focusCopy})`,
    {humanStatus: status => status, guardianCopy: () => '质量检查尚未开始'},
  );
  const workspace = status => ({work:{status:'RUNNING'}, actions:[], reality:{
    guardian:{status:'NOT_STARTED'}, deliveries:[], execution:{status},
  }});
  assert.equal(executionCopy({status:'QUEUED'}), '排队中');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'CAPACITY_WAIT'}}), '等待执行容量');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'CAPACITY_WAIT',draining_worker_count:1,compatible_slots:0}}), '执行资源正在维护，任务在等待');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'CAPACITY_WAIT',draining_worker_count:1,compatible_slots:2}}), '等待执行容量');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'INFRASTRUCTURE_UNAVAILABLE'}}), '执行资源暂不可用，恢复后自动继续');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'SCHEDULING',available_slots:1}}), '已可执行，等待分配');
  assert.equal(executionCopy({status:'QUEUED',scheduling:{progression_state:'NOT_APPLICABLE'}}), '执行暂缓，等待所需条件');
  assert.equal(executionCopy({status:'ASSIGNED',scheduling:{progression_state:'NOT_APPLICABLE'}}), 'Worker 已领取');
  assert.equal(focusCopy(workspace('RUNNING')).now, 'Worker 正在执行');
  assert.equal(focusCopy(workspace('VERIFYING')).now, '正在独立验证');
  assert.equal(focusCopy(workspace('FAILED')).now, '执行或验证失败');
  assert.equal(verificationCopy(null, {status:'RUNNING'}), '尚无验证结果');
  assert.equal(verificationCopy({verification:['PATH_SCOPE: PASS','GIT_DIFF_CHECK: PASS']},
    {status:'COMPLETED'}), '独立验证已通过（2 项）');
  assert.equal(verificationCopy(null, {status:'FAILED',
    recovery_reason:'VERIFICATION_FAILED'}), '独立验证未通过');
  const waitingForHuman = workspace('COMPLETED');
  waitingForHuman.actions = [{id:'current-authority'}];
  assert.equal(focusCopy(waitingForHuman).now, '等待你的决定');
});
