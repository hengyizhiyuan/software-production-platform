const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname,
  '../../src/spg/web/cloud_delivery.js'), 'utf8');

function surface(respond) {
  const content = {children:[], append(node){this.children.push(node);}};
  const flow = {innerHTML:'',scrollIntoView(){}};
  const listeners = {};
  const calls = [];
  const document = {
    createElement(){return {className:'',innerHTML:''};},
    getElementById(id){return id==='content'?content:id==='cloud-delivery-flow'?flow:null;},
    addEventListener(name,callback){listeners[name]=callback;},
  };
  const window = {};
  vm.runInNewContext(source,{document,window,async fetch(url,options){
    if(!respond)throw Error('unexpected network');
    calls.push([url,options?.method||'GET']);
    return {ok:true,async json(){return respond(url,options?.method||'GET');}};
  }});
  return {content,flow,window,listeners,calls};
}

test('qualified Deliverable gets a cloud deployment action without a remote terminal',()=>{
  const {content,window}=surface();
  window.WattCloudDelivery.render({
    manifest:{id:'manifest',software:{runtime_recipe:{adapter:'STATIC_WEB'}},
      fingerprint:'a'.repeat(64)},
    acceptance:{decision:'ACCEPT'},current:true,
    summary:{work_id:'work'},cloud_deployments:[],
  });
  assert.equal(content.children.length,1);
  const html=content.children[0].innerHTML;
  assert.match(html,/查看云连接与目标/);
  assert.doesNotMatch(html,/SSH|Terminal|命令输入|shell/i);
});

test('stale or unaccepted Deliverable cannot show deployment authority',()=>{
  const detail={manifest:{id:'manifest',software:{},fingerprint:'a'.repeat(64)},
    acceptance:{decision:'ACCEPT'},current:false,
    summary:{work_id:'work'},cloud_deployments:[]};
  const first=surface();first.window.WattCloudDelivery.render(detail);
  assert.equal(first.content.children.length,0);
  const second=surface();second.window.WattCloudDelivery.render({...detail,
    current:true,acceptance:{decision:'REQUEST_CHANGES'}});
  assert.equal(second.content.children.length,0);
});

test('historical missing deployment user leads to automatic host preparation',()=>{
  const {content,window}=surface();
  window.WattCloudDelivery.render({
    manifest:{id:'manifest',software:{runtime_recipe:{adapter:'STATIC_WEB'}},
      fingerprint:'a'.repeat(64)},
    acceptance:{decision:'ACCEPT'},current:true,summary:{work_id:'work'},
    cloud_deployments:[{state:'FAILED',blocker:'DEPLOYMENT_USER_NOT_FOUND',
      target:{name:'新 ECS',region_id:'cn-hongkong',instance_id:'i-newtarget'},
      operations:[{output_summary:'DEPLOYMENT_USER_NOT_FOUND',
        deployment_user:'wattdeploy',provider_error_code:'AccountNotExists'}]}],
  });
  const html=content.children[0].innerHTML;
  assert.match(html,/历史尝试：目标 ECS 当时缺少部署用户 wattdeploy/);
  assert.match(html,/部署尚未开始/);
  assert.match(html,/Watt 现在会在新授权的部署尝试中自动评估并准备受支持的主机/);
  assert.doesNotMatch(html,/SSH|手[动工](?:创建用户|安装 Docker|准备服务器)|需要你完成服务器前置条件/i);
  assert.doesNotMatch(html,/AccountNotExists|CLOUD_OPERATION_UNVERIFIED/);
  assert.match(window.WattCloudDelivery.blockerCopy({blocker:'UNSUPPORTED_HOST_PROFILE'}),
    /不在当前自动部署支持范围内/);
  assert.match(window.WattCloudDelivery.blockerCopy({blocker:'HOST_PROFILE_CONFLICT'}),
    /Watt 已安全停止/);
});

test('existing connection can rediscover targets without creating a connection or deployment',async()=>{
  const id='existing-connection';
  let rediscovered=false;
  const target={name:'旧 CentOS ECS',region_id:'cn-beijing',instance_id:'i-oldtarget'};
  const base={id,state:'READY',role_arn:'acs:ram::1234567890123456:role/wattecsdelivery',
    target,discovered_targets:[]};
  const {content,flow,window,listeners,calls}=surface((url,method)=>{
    if(url==='/api/cloud-connections/aliyun'&&method==='GET')return [
      {id:'other-connection',state:'READY',target:{name:'别的 ECS'}},base];
    if(url===`/api/cloud-connections/aliyun/${id}/deployments`)return [];
    if(url===`/api/cloud-connections/aliyun/${id}/verify`&&method==='POST'){
      rediscovered=true;return {id};
    }
    if(url===`/api/cloud-connections/aliyun/${id}`)return rediscovered?{
      ...base,state:'DISCOVERY_READY',target:null,
      discovered_targets:[{selection_token:'new-selection',name:'新 Alibaba Cloud Linux ECS',
        region_id:'cn-beijing',status:'Running',os_name:'Alibaba Cloud Linux 3',
        cloud_assistant_ready:true}],
    }:base;
    throw Error(`unexpected request ${method} ${url}`);
  });
  window.WattCloudDelivery.render({
    manifest:{id:'manifest',software:{runtime_recipe:{adapter:'STATIC_WEB'}},
      fingerprint:'a'.repeat(64)},
    acceptance:{decision:'ACCEPT'},current:true,summary:{work_id:'work'},
    cloud_deployments:[{id:'old-failure',connection_id:id,state:'FAILED',target,
      blocker:'DEPLOYMENT_USER_NOT_FOUND',operations:[]}],
  });
  assert.match(content.children[0].innerHTML,/重新选择 ECS（不部署）/);
  const button=attribute=>({disabled:false,dataset:{},hasAttribute(name){return name===attribute;}});
  await listeners.click({target:{closest(){return button('data-cloud-reselect');}}});
  assert.match(flow.innerHTML,/新 Alibaba Cloud Linux ECS/);
  assert.ok(!calls.some(([url])=>url.includes('other-connection')));
  assert.ok(calls.some(([url,method])=>url===`/api/cloud-connections/aliyun/${id}/verify`&&method==='POST'));
  assert.ok(!calls.some(([url,method])=>url==='/api/cloud-connections/aliyun'&&method==='POST'));
  assert.ok(!calls.some(([url,method])=>url.endsWith('/select')&&method==='POST'));
});

test('READY target presents exact governed Delivery authorization directly',async()=>{
  const id='existing-connection';
  const target={account_id:'1234567890123456',name:'新 Alibaba Cloud Linux ECS',
    region_id:'cn-hongkong',instance_id:'i-newtarget'};
  const deployment={id:'failed-new-target',connection_id:id,state:'FAILED',
    target,blocker:'DEPLOYMENT_USER_NOT_FOUND',operations:[{
      output_summary:'DEPLOYMENT_USER_NOT_FOUND',deployment_user:'wattdeploy'}]};
  const connection={id,state:'READY',target,
    role_arn:'acs:ram::1234567890123456:role/wattecsdelivery'};
  const {content,flow,window,listeners,calls}=surface((url,method)=>{
    if(url==='/api/cloud-connections/aliyun')return [connection];
    if(url===`/api/cloud-connections/aliyun/${id}`)return connection;
    if(url===`/api/cloud-connections/aliyun/${id}/deployments`)return [deployment];
    throw Error(`unexpected request ${method} ${url}`);
  });
  window.WattCloudDelivery.render({
    manifest:{id:'manifest',software:{runtime_recipe:{adapter:'STATIC_WEB'}},
      fingerprint:'a'.repeat(64)},
    acceptance:{decision:'ACCEPT'},current:true,summary:{work_id:'work'},
    cloud_deployments:[deployment],
  });
  assert.match(content.children[0].innerHTML,/新 Alibaba Cloud Linux ECS/);
  const button=attribute=>({disabled:false,dataset:{},hasAttribute(name){return name===attribute;}});
  await listeners.click({target:{closest(){return button('data-cloud-open');}}});
  assert.match(flow.innerHTML,/新 Alibaba Cloud Linux ECS · cn-hongkong · i-newtarget/);
  assert.match(flow.innerHTML,/Watt 将自动检查并在受支持时准备/);
  assert.match(flow.innerHTML,/id="cloud-deploy-form"/);
  assert.match(flow.innerHTML,/name="exposure_mode"/);
  assert.match(flow.innerHTML,/value="PRIVATE" selected/);
  assert.match(flow.innerHTML,/value="PUBLIC"/);
  assert.match(flow.innerHTML,/name="rationale" required/);
  assert.match(flow.innerHTML,/授权并部署/);
  assert.doesNotMatch(flow.innerHTML,/我决定准备部署|前往阿里云授权此主机|目标授权已验证|data-cloud-show-deploy/);
  assert.doesNotMatch(flow.innerHTML,/SSH|手[动工](?:创建用户|安装 Docker|准备服务器)|需要你完成服务器前置条件/i);
  assert.ok(!calls.some(([,method])=>method==='POST'));
});
