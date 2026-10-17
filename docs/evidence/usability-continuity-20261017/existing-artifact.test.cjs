const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element {
 constructor(){this.children=[];this.events={};this.attributes={};this.value='';this.classList={toggle(){}};}
 set textContent(v){this.text=v;this.children=[];} get textContent(){return this.text||'';}
 appendChild(v){this.children.push(v);return v;} setAttribute(k,v){this.attributes[k]=v;}
 getAttribute(k){return this.attributes[k]??null;} addEventListener(k,f){this.events[k]=f;}
 focus(){} reset(){}
}
const nodes={};const filters=['all','unread','read'].map(v=>{let e=new Element();e.setAttribute('data-filter',v);return e;});
const document={getElementById(id){return nodes[id]??=new Element();},querySelectorAll(){return filters;},createElement(){return new Element();}};
const storage={};let confirmResult=false,confirmCalls=0;
const window={localStorage:{getItem:k=>storage[k]??null,setItem:(k,v)=>{storage[k]=v;}},confirm:()=>{confirmCalls++;return confirmResult;}};
vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],{document,window,Date,Math,JSON,Array});
nodes['book-title'].value='Cancel must preserve this book';nodes['book-author'].value='Qualification';
nodes['add-form'].events.submit({preventDefault(){}});
const key=Object.keys(storage)[0],original=storage[key];let book=JSON.parse(original)[0];
const row={getAttribute:()=>book.id};const button={closest:()=>row,getAttribute:()=> 'remove'};
nodes['book-list'].events.click({target:{closest:()=>button}});
assert.equal(confirmCalls,1);assert.equal(storage[key],original);assert.match(nodes['stats'].textContent,/共 1 本/);
confirmResult=true;nodes['book-list'].events.click({target:{closest:()=>button}});
assert.equal(confirmCalls,2);assert.equal(JSON.parse(storage[key]).length,0);assert.match(nodes['stats'].textContent,/共 0 本/);
console.log(JSON.stringify({status:'PASS',artifact_sha256:crypto.createHash('sha256').update(html).digest('hex'),checks:['actual-script-add-handler','cancel-keeps-exact-local-storage-and-count','confirm-deletes-and-updates-count'],scope:'Node VM execution of exact candidate script with DOM/storage/confirm test doubles; real browser prompt separately observed'}));
