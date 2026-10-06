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
  assert.match(helpers, /acceptance \? acceptanceCopy\(ws, acceptance\)/);
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

test('multi-unit Reality preserves waiting, dependency and reconciliation meaning', () => {
  const source = script.slice(script.indexOf('  function renderWorkspaceReality(ws,'),
    script.indexOf('  function renderWorkspaceActions(ws,'));
  const render = vm.runInNewContext(`${source}; renderWorkspaceReality`, {
    esc: value => String(value ?? '').replace(/</g, '&lt;'),
    humanStatus: value => value, executionCopy: () => '等待执行容量',
    verificationCopy: () => '尚无验证结果', guardianCopy: () => '尚未开始', link: () => '',
  });
  const html = render({product:{},work:{status:'RUNNING'},reality:{deliveries:[],production_plan:{
    revision_number:2,pwus:[
      {objective:'page <A>',human_visible:'page <A>：等待执行容量',state:'WAITING_CAPACITY',kind:'PWU'},
      {objective:'page B',human_visible:'page B：已通过验证',state:'VERIFIED',kind:'PWU'},
      {objective:'join',human_visible:'join：等待前置成果验证',state:'DEPENDENCIES_PENDING',kind:'JOIN'},
      {objective:'withdrawn',human_visible:'withdrawn：已取消，生产义务尚未完成',state:'CANCELLED',kind:'PWU'},
    ],
  }}},false,false,'work');
  assert.match(html, /生产计划 · 版本 2/);
  assert.match(html, /page &lt;A>.*等待执行容量/);
  assert.match(html, /page B.*已通过验证/);
  assert.match(html, /join.*等待前置成果验证.*成果整合与验证/);
  assert.match(html, /withdrawn.*已取消，生产义务尚未完成/);
  assert.doesNotMatch(html, /正在执行/);
  assert.equal((html.match(/data-workspace-quadrant=/g) || []).length,1);
});

for (const [status, gate] of [['NOT_STARTED', null], ['RUNNING', null],
  ['FINDINGS_PRESENT', 'FAIL_REPAIRABLE'], ['BLOCKED', 'BLOCKED'], ['PASS', 'PASS']]) {
  test(`required Guardian ${status} controls Human acceptance without changing quadrants`, () => {
    const source = script.slice(script.indexOf('  function renderWorkspaceActions(ws,'),
      script.indexOf('  async function renderWorkspace(id) {'));
    const {renderWorkspaceActions, renderWorkspaceProduction} = vm.runInNewContext(
      `${source}; ({renderWorkspaceActions, renderWorkspaceProduction})`, {
        esc: value => String(value ?? ''), link: () => '', renderAttention: () => '',
      });
    const ws = {actions:[], reality:{guardian:{required:true,status,gate}}};
    const candidate = {candidate_fingerprint:'exact-current-candidate'};
    const manifest = {id:'manifest',fingerprint:'exact-manifest'};
    const actions = renderWorkspaceActions(ws,candidate,manifest,null,'work',false);
    const production = renderWorkspaceProduction(ws,{now:'验证候选',reason:'独立证据',next:'质量检查'},true,null);
    assert.match(actions,/data-preview=/);
    assert.match(actions,/data-diff=/);
    if (gate === 'PASS') {
      assert.match(actions,/data-accept=/);
      assert.match(production,/等待你的明确决定/);
    } else {
      assert.doesNotMatch(actions,/data-accept=/);
      assert.match(actions,/还不能授权或验收/);
      assert.doesNotMatch(production,/新版本已经准备好/);
    }
    assert.equal((actions.match(/data-workspace-quadrant=/g)||[]).length,1);
    assert.equal((production.match(/data-workspace-quadrant=/g)||[]).length,1);
  });
}

for (const [promotionState, copy] of [['PENDING', '正在更新正式版本'], ['BLOCKED', '正式版本更新受阻'], ['COMPLETED', '已验收']]) {
  test(`immutable acceptance distinguishes Product promotion ${promotionState}`, () => {
    const source = script.slice(script.indexOf('  function acceptanceCopy(ws,'), script.indexOf('  async function renderWorkspace(id) {'));
    const {renderWorkspaceActions} = vm.runInNewContext(`${source}; ({renderWorkspaceActions})`, {
      esc: value => String(value ?? ''), link: () => '', renderAttention: () => '',
    });
    const ws = {actions:[], reality:{guardian:{required:true,gate:'PASS'}, deliveries:[{source_promotion:{state:promotionState}}]}};
    const html = renderWorkspaceActions(ws,{candidate_fingerprint:'exact'}, {id:'manifest',fingerprint:'exact'}, {decision:'ACCEPT'}, 'work', false);
    assert.match(html, new RegExp(copy));
    assert.doesNotMatch(html, /data-accept=/);
    assert.equal(html.includes('data-promotion-retry='), promotionState !== 'COMPLETED');
    assert.equal((html.match(/data-workspace-quadrant=/g)||[]).length,1);
  });
}

test('normal quadrants use one WIC realization and never fall through to owner prose', () => {
  const source = script.slice(script.indexOf('  function renderWorkspaceAgenda(ws)'),
    script.indexOf('  function acceptanceCopy(ws,'));
  const render = vm.runInNewContext(`${source}; renderWorkspaceAgenda`, {
    esc: value => String(value ?? ''),
  });
  const html = render({human_visible:{wording:{headline:'完成官网首版'}},agenda:[{
    id:'exact-step',type:'DESIGN',state:'current',
    title:'Establish the Motive, relevant actors, and problem boundary',
    human_visible:'准备官网首页的内容与页面结构',
  }]});
  assert.match(html,/准备官网首页的内容与页面结构/);
  assert.match(html,/完成官网首版/);
  assert.doesNotMatch(html,/Establish the Motive|DesignIssue|basis_fingerprint/);
  assert.doesNotMatch(render({agenda:[{id:'step',state:'current',title:'MATERIAL_RISK_OR_COST_DECISION'}]}),/MATERIAL_RISK/);
});

test('qualified Actions render WIC questions while preserving exact authority controls', () => {
  const source = script.slice(script.indexOf('  function renderAttention(a)'),
    script.indexOf('  const agendaLabels ='));
  const render = vm.runInNewContext(`${source}; renderAttention`, {
    esc: value => String(value ?? ''),actionText: () => '授权',
  });
  const html = render({id:'exact-owner-action',actions:['AUTHORIZE'],
    reason:'Choose how to handle a material risk or cost',
    conversation_prompt:'STEERING_DECISION_REQUIRED',
    human_visible:{question:'首版只展示品牌，还是加入登录和客户后台？',why_now:'这会改变产品范围与数据权限，需要由你决定。'}});
  assert.match(html,/首版只展示品牌/);
  assert.match(html,/exact-owner-action/);
  assert.match(html,/AUTHORIZE/);
  assert.doesNotMatch(html,/Choose how|STEERING_DECISION_REQUIRED/);
});
