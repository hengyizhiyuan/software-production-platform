const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname,
  '../../src/spg/web/cloud_delivery.js'), 'utf8');

function surface() {
  const content = {children:[], append(node){this.children.push(node);}};
  const listeners = {};
  const document = {
    createElement(){return {className:'',innerHTML:''};},
    getElementById(id){return id==='content'?content:null;},
    addEventListener(name,callback){listeners[name]=callback;},
  };
  const window = {};
  vm.runInNewContext(source,{document,window,fetch(){throw Error('unexpected network');}});
  return {content,window,listeners};
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
  assert.match(html,/部署到阿里云/);
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
