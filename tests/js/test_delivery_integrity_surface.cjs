const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.resolve(__dirname,'../../src/spg/web/experience.js'),'utf8');
const summary=source.slice(source.indexOf('  function deliverySummary('),source.indexOf('  function renderWorkspaceActions('));
const {deliverySummary}=vm.runInNewContext(summary+';({deliverySummary})',{esc:value=>String(value??'')});
test('download summary distinguishes software and document without manufacturing acceptance',()=>{
 const manifest={repository_revision:'a'.repeat(40),artifacts:[{path:'index.html'},{path:'site.css'}],verification_record_ids:['v'],software:{runtime_recipe:{entrypoint:'index.html'}}};
 const output=deliverySummary(manifest,{gate:'PASS'});assert.match(output,/软件交付包/);assert.match(output,/入口：index.html/);assert.match(output,/文件：2/);assert.match(output,/Verification：PASS/);assert.match(output,/Guardian：PASS/);assert.ok(output.includes(manifest.repository_revision));
 const doc=deliverySummary({...manifest,software:null},{status:'NOT_STARTED'});assert.match(doc,/文档交付包.*仅含文档成果/);assert.doesNotMatch(doc,/Guardian：PASS/);
});
test('Product source export pins inspected revision and exposes candidate independently of accepted source',()=>{
 const code=source.slice(source.indexOf('  async function renderCode('),source.indexOf('  async function renderUser('));
 assert.match(code,/revision:files.revision/);assert.match(code,/导出正式源码/);assert.match(code,/导出候选源码/);assert.match(code,/查看新候选源码/);assert.match(code,/可能早于预览中的新成果/);assert.match(code,/查看新成果与交付包/);
});
test('trusted package creation is an exact Human click, separate from acceptance and ordinary page reads',()=>{
 const action=source.slice(source.indexOf('  async function publishDelivery('),source.indexOf('  async function openDiff('));
 assert.match(action,/candidate_fingerprint:button.dataset.fingerprint/);assert.match(action,/repository_revision:button.dataset.revision/);assert.doesNotMatch(action,/acceptance|decision|AUTHORIZE/);
 const render=source.slice(source.indexOf('  async function renderWorkspace('),source.indexOf('  async function renderWorkspaceConversation('));assert.doesNotMatch(render,/publishDelivery\(/);
 assert.match(source,/!candidate.authorization_pending && assuranceReady/);
});
