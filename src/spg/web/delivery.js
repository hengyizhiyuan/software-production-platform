(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const node = (tag, text, cls) => { const el = document.createElement(tag); el.textContent = text || ""; if(cls) el.className=cls; return el; };
  let selected = new URLSearchParams(location.search).get("work") || "", work = null, busy = false, generation = 0;
  let intakeKey = null, intakeBody = null;
  async function api(url, data) {
    const response = await fetch(url, data === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
    const value = await response.json(); if(!response.ok) throw new Error(value.message || JSON.stringify(value)); return value;
  }
  async function action(fn) {
    if(busy) return; busy=true; $("notice").textContent="正在处理…";
    document.querySelectorAll("button, select").forEach(el=>{el.disabled=true;});
    try {await fn(); $("notice").textContent="已保存。"; await refresh();} catch(error) {$("notice").textContent=error.message;}
    finally {busy=false; document.querySelectorAll("button, select").forEach(el=>{el.disabled=false;});}
  }
  function requireWork() {if(!work) throw new Error("请先在对话中准入 Work，再选择它。"); return work.work_id;}
  function showAsset(asset) {
    const card=node("article","","card");
    const unresolved=!asset.resource_id;
    card.append(node("h3",asset.title+(unresolved?" · 访问能力未解析":asset.selected_for_production?" · 当前生产目标":asset.bound?" · 已关联":"")), node("p",asset.description),
      node("p",asset.repository_identity+(asset.repository_ref?" · "+asset.repository_ref:""),"meta"));
    if(unresolved) card.append(node("p",asset.message||"授权与集成确认前不会用于生产；当前 Work 可继续使用 Watt 管理的执行工作区。","meta"));
    else card.append(node("p","接入观察版本："+asset.revision,"meta"));
    const details=node("details"); details.append(node("summary","查看接入目录与观察依据"),node("pre",JSON.stringify({paths:asset.paths,observed_at:asset.observed_at,fingerprint:asset.fingerprint},null,2))); card.append(details);
    if(work&&!unresolved) {const button=node("button",asset.bound?"选择为后续生产目标":"绑定到当前 Work"); button.type="button";
      button.addEventListener("click",()=>action(()=>api(`/api/works/${requireWork()}/asset-scope-admissions`,{resource_id:asset.resource_id,
        expected_work_revision_id:work.current_work_reality_revision_id,observation_fingerprint:asset.fingerprint,authority_identity:"human:local-operator",rationale:"Human selected this observed repository as the Work production target"})));card.append(button);}
    $("assets").append(card);
  }
  function showDelivery(entry) {
    const manifest=entry.manifest, card=node("article","","card"), decision=entry.acceptance;
    card.append(node("h3",entry.current?"当前交付版本":"历史交付版本"),node("p",decision?(decision.decision==="ACCEPT"?"Human 已接受":"Human 请求修改"):"HUMAN PRODUCT ACCEPTANCE PENDING","badge"),node("p","仓库版本："+manifest.repository_revision,"meta"),node("p","清单指纹："+manifest.fingerprint,"meta"));
    for(const artifact of manifest.artifacts) {const link=node("a","预览 "+artifact.path);link.href=`/api/works/${work.work_id}/deliveries/${manifest.id}/artifact?path=${encodeURIComponent(artifact.path)}`;link.target="_blank";link.rel="noopener";
      const row=node("p");row.append(link,node("span",` · ${artifact.size_bytes} bytes · SHA-256 ${artifact.sha256}`,"meta"));card.append(row);}
    if(manifest.software){const details=node("details");details.append(node("summary","代码变更与独立验证证据"),node("pre",JSON.stringify(manifest.software,null,2)));card.append(details);
      const runtime=node("div","","runtime"),status=entry.runtime||{status:"NOT_READY"};
      if(status.status==="READY"){const link=node("a","打开软件进行验收","download");link.href=status.url;link.target="_blank";link.rel="noopener";runtime.append(link,node("p","已核对当前运行入口与此交付清单一致。"));}
      else runtime.append(node("p","软件运行入口尚未就绪。"));
      if(entry.current){const start=node("button","启动 / 检查此版本的软件");start.addEventListener("click",()=>action(()=>api(`/api/works/${requireWork()}/deliveries/${manifest.id}/runtime`,{})));runtime.append(start);}card.append(runtime);
    }
    const download=node("a",manifest.software?"下载源码、说明与验证证据":"下载文档包与验证清单","download");download.href=`/api/works/${work.work_id}/deliveries/${manifest.id}/download`;card.append(download);
    if(decision)card.append(node("p",decision.authority_identity+"："+decision.rationale));
    const acceptanceReady=!manifest.software||(entry.runtime&&entry.runtime.status==="READY");
    if(entry.current&&!decision&&!acceptanceReady)card.append(node("p","请先启动并打开这个精确版本的软件；运行入口核对成功后，才可记录接受或修改决定。","meta"));
    if(entry.current&&!decision&&acceptanceReady){const form=node("form"),label=node("label"),checked=document.createElement("input");checked.type="checkbox";checked.required=true;label.append(checked,document.createTextNode("我已检查这个版本的产物和验收标准（软件产物已实际操作）"));
      const rationale=document.createElement("textarea");rationale.required=true;rationale.maxLength=4000;rationale.placeholder="接受理由或需要修改的具体内容";rationale.setAttribute("aria-label","Human 验收意见");form.append(label,rationale);
      for(const [value,text] of [["ACCEPT","接受此交付"],["REQUEST_CHANGES","请求修改"]]){const button=node("button",text);button.type="submit";button.value=value;form.append(button);}
      form.addEventListener("submit",event=>{event.preventDefault();const value=event.submitter.value;action(()=>api(`/api/works/${requireWork()}/deliveries/${manifest.id}/acceptance`,{manifest_fingerprint:manifest.fingerprint,decision:value,authority_identity:"human:local-operator",rationale:rationale.value}));});card.append(form);}
    $("deliveries").append(card);
  }
  async function refresh(){const currentGeneration=++generation;if(!busy)$("notice").textContent="";const works=await api("/api/works");const list=Array.isArray(works)?works:works.works||[];if(currentGeneration!==generation)return;
    $("work").replaceChildren(node("option","选择 Work（或先返回对话进行准入）"));$("work").firstChild.value="";
    list.forEach(item=>{const option=node("option",item.title||item.desired_outcome||item.work_id);option.value=item.work_id;$("work").append(option);});$("work").value=selected;
    const [current,assets,delivery,context,attention]=await Promise.all([selected?api(`/api/works/${selected}`):null,api("/api/repository-assets"+(selected?`?work_id=${selected}`:"")),selected?api(`/api/works/${selected}/delivery`):null,selected?api(`/api/works/${selected}/delivery-context`):null,selected?api(`/api/attention?work_id=${selected}`):[]]);if(currentGeneration!==generation)return;
    work=current;$("assets").replaceChildren();assets.forEach(showAsset);$("work-summary").textContent=work?`${work.desired_outcome} · ${work.status==="COMPLETED"?"生产已完成；产品接受状态见下方交付版本":work.status+" · "+work.what_happens_next}`:"返回对话澄清并准入 Work；用户仓库可稍后按需接入。";
    $("plan").textContent=work&&work.production_plan?JSON.stringify(work.production_plan,null,2):"尚无生产计划。继续对话与 Guided Design，成熟后审阅具体生产建议。";
    $("attention").replaceChildren();for(const item of attention){const card=node("article","","card");card.append(node("h3",item.decision),node("p",item.reason));for(const available of item.available_actions){const labels={APPROVE:"批准此项",REJECT:"拒绝此项",AUTHORIZE:"授权精确仓库变更",REQUEST_REFINEMENT:"请求细化"};const button=node("button",labels[available]||available);
      button.addEventListener("click",()=>action(()=>api(`/api/attention/${item.attention_id||item.id}/resolve`,{action:available,authority_identity:"human:local-operator",rationale:"Human reviewed the displayed exact decision and production plan"})));card.append(button);}$("attention").append(card);}
    $("deliveries").replaceChildren();
    const target=context&&context.target;$("target-summary").textContent=target?`${target.title}：${target.acceptance_criteria.join("；")}`:"尚无唯一可推导的交付目标。";$("target").hidden=Boolean(target);$("target-blocker").textContent=context&&context.blocker||"";
    const contextCard=$("delivery-context");contextCard.replaceChildren();
    if(context){contextCard.append(node("h3","Prepared Delivery Candidate"),node("p",context.target_source==="GOVERNED_REALITY"?"目标与验收标准来自当前 Governed Reality，无需重新填写。":"显示当前已记录的交付信息。"),node("p",`期望结果：${context.desired_outcome}`),node("p",`产物：${context.artifacts.join("、")||"尚无"}`),node("p",`Verification：${context.verification.join("；")||"尚无"}`),node("p",`技术信任：${context.trusted?"TECHNICALLY VERIFIED / TRUSTED":"尚未形成 Trusted Runtime Commit"}`));}
    $("publish").hidden=!(context&&context.trusted&&target);
    if(delivery){await Promise.all(delivery.deliveries.filter(entry=>entry.manifest.software).map(async entry=>{entry.runtime=await api(`/api/works/${selected}/deliveries/${entry.manifest.id}/runtime`);}));if(currentGeneration!==generation)return;delivery.deliveries.forEach(showDelivery);}
  }
  $("work").addEventListener("change",()=>{selected=$("work").value;work=null;["assets","deliveries","attention"].forEach(id=>$(id).replaceChildren());history.replaceState(null,"","/delivery"+(selected?`?work=${selected}`:""));refresh().catch(error=>{$("notice").textContent=error.message;});});
  $("refresh").addEventListener("click",()=>refresh().catch(error=>{$("notice").textContent=error.message;}));
  $("intake").addEventListener("submit",event=>{event.preventDefault();action(async()=>{const body={source:$("repo-source").value.trim()||null,title:$("repo-title").value,description:$("repo-description").value,authority_identity:"human:local-operator"};const signature=JSON.stringify(body);if(signature!==intakeBody){intakeBody=signature;intakeKey=crypto.randomUUID();}await api("/api/repository-assets/intake",{...body,request_id:intakeKey});});});
  $("target").addEventListener("submit",event=>{event.preventDefault();action(()=>api(`/api/works/${requireWork()}/delivery-target`,{kind:$("target-kind").value,title:$("target-title").value,acceptance_criteria:$("criteria").value.split("\n").map(s=>s.trim()).filter(Boolean),authority_identity:"human:local-operator",...($("target-kind").value==="SOFTWARE_ARTIFACT"?{software_form:$("software-form").value,runtime_recipe:{adapter:$("runtime-adapter").value,entrypoint:$("runtime-adapter").value==="STATIC_WEB"?$("entrypoint").value.trim():null}}:{})}));});
  $("publish").addEventListener("click",()=>action(()=>api(`/api/works/${requireWork()}/deliveries`,{})));
  $("target-kind").addEventListener("change",()=>{$("software-config").hidden=$("target-kind").value!=="SOFTWARE_ARTIFACT";});
  $("runtime-adapter").addEventListener("change",()=>{$("entrypoint-config").hidden=$("runtime-adapter").value!=="STATIC_WEB";});
  refresh().catch(error=>{$("notice").textContent=error.message;});
})();
