const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/spg/web/experience.js','utf8');
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const actionsSource = source.slice(source.indexOf('  function deliverySummary('), source.indexOf('  async function renderWorkspace(id) {'));
const {renderWorkspaceActions, candidateArtifactUrl} = vm.runInNewContext(`${actionsSource}; ({renderWorkspaceActions,candidateArtifactUrl})`, {esc,link:()=>'',renderAttention:()=>''});
const workspace = {actions:[],reality:{guardian:{required:false},deliveries:[]}};
const document = {candidate_fingerprint:'a'.repeat(64),preview_kind:null,authorization_pending:true,artifacts:['方案/需求 #1?.md']};

test('sealed document is readable and downloadable before authorization without advertising Preview', () => {
  const html = renderWorkspaceActions(workspace,document,null,null,'work-1',false);
  assert.match(html,/查看文档/);
  assert.match(html,/下载文档/);
  assert.match(html,/data-artifact-path="方案\/需求 #1\?\.md"/);
  assert.ok(html.includes(candidateArtifactUrl('work-1',document.candidate_fingerprint,document.artifacts[0])));
  assert.doesNotMatch(html,/data-preview=|查看预览与改动|data-publish-delivery=|data-accept=/);
  assert.match(html,/成果文件与改动/);
});

test('mixed artifact Candidate preserves its actual software Preview and offers every file', () => {
  const html = renderWorkspaceActions(workspace,{...document,preview_kind:'STATIC_WEB',artifacts:['index.html','docs/manual.md','usage.TXT']},null,null,'work',false);
  assert.match(html,/data-preview="work"/);
  assert.equal((html.match(/data-document=/g)||[]).length,2);
  assert.equal((html.match(/ download>/g)||[]).length,3);
  assert.match(html,/下载文件/);
});

test('file labels cannot inject attributes and non-text artifacts retain download only', () => {
  const html = renderWorkspaceActions(workspace,{...document,artifacts:['notes/"<img onerror=alert(1)>.md','report.pdf']},null,null,'work',false);
  assert.doesNotMatch(html,/<img|onerror="/);
  assert.match(html,/&lt;img/);
  assert.equal((html.match(/data-document=/g)||[]).length,1);
  assert.equal((html.match(/ download>/g)||[]).length,2);
});

const urlSource = source.slice(source.indexOf('  function candidateArtifactUrl('),source.indexOf('  function renderCandidateArtifacts('));
const readerSource = source.slice(source.indexOf('  async function openDocument('),source.indexOf('  async function publishDelivery('));
function readerHarness(api) {
  const reader={isConnected:true,textContent:'正在读取文档…',attributes:{},setAttribute(k,v){this.attributes[k]=v;}};
  const dialogs=[];
  const openDocument=vm.runInNewContext(`${urlSource}\n${readerSource}; openDocument`, {esc,dialogContent:{},$:()=>reader,openDialog:markup=>dialogs.push(markup),api});
  return {reader,dialogs,open:()=>openDocument({dataset:{document:'work',fingerprint:document.candidate_fingerprint,artifactPath:document.artifacts[0]}})};
}

test('reader GET consumes exact bound artifact as inert full text without authorizing or opening Preview', async () => {
  const calls=[];const text='# 方案\n<script>danger()</script>\n'+('长文'.repeat(6000));
  const h=readerHarness(async(...args)=>{calls.push(args);return text;});
  await h.open();
  assert.equal(calls.length,1);
  assert.equal(calls[0].length,1); // Existing API defaults to authenticated GET.
  assert.equal(calls[0][0],candidateArtifactUrl('work',document.candidate_fingerprint,document.artifacts[0]));
  assert.equal(h.reader.textContent,text);
  assert.equal(h.reader.attributes['aria-busy'],'false');
  assert.doesNotMatch(h.dialogs[0],/<script>/);
  assert.match(h.dialogs[0],/下载文档/);
});

test('stale or failed artifact reads surface the actual error and grant no new authority', async () => {
  const h=readerHarness(async()=>{throw new Error('Candidate 已变更');});await h.open();
  assert.equal(h.reader.textContent,'无法读取文档：Candidate 已变更');
  assert.equal(h.reader.attributes['aria-busy'],'false');
});

test('late response does not replace a closed or superseded reader', async () => {
  let resolve;const h=readerHarness(()=>new Promise(done=>{resolve=done;}));const pending=h.open();
  h.reader.isConnected=false;resolve('old content');await pending;
  assert.equal(h.reader.textContent,'正在读取文档…');
});
