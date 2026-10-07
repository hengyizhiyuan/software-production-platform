const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../../src/spg/web');
const script=fs.readFileSync(root+'/delivery_action.js','utf8');
let listener;const window={};vm.runInNewContext(script,{window,URL,document:{addEventListener:(type,fn)=>listener=fn},location:{origin:'http://watt.test'},crypto:{randomUUID:()=> 'client-click-uuid'}});
const correlate=window.WattDeliveryAction.correlateDeliveryAction;
test('native download correlates each actual click and preserves exact revision',()=>{
 const anchor={href:'http://watt.test/api/products/p/code-assets/export?revision=abc',dataset:{deliverySemantic:'DOWNLOAD_OFFICIAL_PRODUCT_SOURCE',deliveryWork:'work'}};
 assert.equal(correlate(anchor,'http://watt.test','first'),true);let u=new URL(anchor.href);
 assert.equal(u.searchParams.get('revision'),'abc');assert.equal(u.searchParams.get('action_semantic'),'DOWNLOAD_OFFICIAL_PRODUCT_SOURCE');assert.equal(u.searchParams.get('context_work_id'),'work');
 assert.equal(u.searchParams.get('initiating_action_id'),'first');correlate(anchor,'http://watt.test','second');assert.equal(new URL(anchor.href).searchParams.get('initiating_action_id'),'second');
 assert.ok(!anchor.href.includes('received'));
});
test('only canonical delivery boundaries receive hints; unrelated/external URLs untouched',()=>{
 for(const [url,semantic] of [['/api/works/w/deliveries/m/download','DOWNLOAD_CURRENT_AUTHORIZED_DELIVERY'],['/api/works/w/deliveries/m/artifact?path=index.html','DOWNLOAD_DELIVERY_ARTIFACT'],['/api/works/w/candidate-download/f/index.html','DOWNLOAD_CANDIDATE_ARTIFACT']]){
  const a={href:'http://watt.test'+url,dataset:{}};assert.equal(correlate(a,'http://watt.test','click'),true);assert.equal(new URL(a.href).searchParams.get('action_semantic'),semantic);
 }
 for(const url of ['http://other.test/api/works/w/deliveries/m/download','http://watt.test/api/works/w','http://watt.test/api/works/w/candidate-preview/f/index.html']){
  const a={href:url,dataset:{}};assert.equal(correlate(a,'http://watt.test','click'),false);assert.equal(a.href,url);
 }
});
test('Product formal/candidate exports carry explicit semantics without changing acceptance',()=>{
 const source=fs.readFileSync(root+'/experience.js','utf8');assert.match(source,/data-delivery-semantic=.*DOWNLOAD_OFFICIAL_PRODUCT_SOURCE.*DOWNLOAD_CANDIDATE_SOURCE/);assert.match(source,/data-delivery-work=/);assert.match(source,/data-delivery-surface="DELIVERABLE"/);
});
test('observed Trace stays compact, exposes divergence and unknown client truth',()=>{
 const admin=fs.readFileSync(root+'/admin.js','utf8');const code=admin.slice(admin.indexOf('  function servedDelivery('),admin.indexOf('  function traceSection('));
 const fn=vm.runInNewContext(code+';servedDelivery',{esc:x=>String(x??''),date:x=>x,table:(h,r)=>JSON.stringify({h,r}),evidence:x=>JSON.stringify(x)});
 const out=fn({served_delivery:{historical_action_identity:'NOT_RECORDED',historical_note:'历史点击未记录',actions:[{action_semantic:'DOWNLOAD_CURRENT_AUTHORIZED_DELIVERY',classification:'OBSERVED_DELIVERY_DIVERGENCE',request_id:'request',resolver_policy:'policy',expected:{revision:'new'},selected:{revision:'old'},response:{complete:true,http_status:200,byte_size:42,sha256:'payload-sha'},inventory:{file_count:2}}]}});
 for(const text of ['交付偏离','new','old','request','payload-sha','历史点击未记录','NOT_RECORDED','不能证明客户端接收或保存'])assert.ok(out.includes(text));
 const none=fn({});assert.match(none,/不能据 Manifest 推断用户已下载/);assert.doesNotMatch(none,/用户已成功保存/);
});
