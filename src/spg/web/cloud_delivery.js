/* Guided Alibaba Cloud Delivery on a qualified Deliverable detail page. */
(() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {work:null, manifest:null, fingerprint:null, deployments:[],
    targetDeployments:[], connections:[], connection:null, open:false};
  async function request(path, method='GET', body) {
    const response = await fetch(path,{method,credentials:'same-origin',
      headers:body===undefined?{}:{'Content-Type':'application/json'},
      ...(body===undefined?{}:{body:JSON.stringify(body)})});
    const value = await response.json();
    if(!response.ok) throw new Error(value.message||value.code||'请求失败');
    return value;
  }
  function box() { return document.getElementById('cloud-delivery-flow'); }
  function message(value, failure=false) {
    const node=document.getElementById('cloud-delivery-message');
    if(node) {node.textContent=value;node.className=failure?'notice-error':'muted';}
  }
  function blockerCopy(deployment) {
    if(!deployment?.blocker)return '';
    if(deployment.blocker==='DEPLOYMENT_USER_NOT_FOUND') {
      const receipt=(deployment.operations||[]).find(item=>item.output_summary==='DEPLOYMENT_USER_NOT_FOUND');
      const candidate=receipt?.deployment_user||deployment.deployment_user||'wattdeploy';
      const username=/^[a-z_][a-z0-9_-]{0,31}$/.test(candidate)?candidate:'wattdeploy';
      return `目标 ECS 缺少 Watt 部署用户 ${username}。部署尚未开始，未修改服务器运行状态；需要你完成服务器前置条件。`;
    }
    return deployment.blocker;
  }
  async function renderFlow() {
    const node=box();if(!node||!state.open)return;
    const c=state.connection;
    const choices=state.connections.map(item=>`<option value="${escape(item.id)}" ${c?.id===item.id?'selected':''}>${escape(item.target?.name||item.role_arn||'待授权的云连接')} · ${escape(item.state)}</option>`).join('');
    const choose=state.connections.length?`<div class="field"><label for="cloud-connection-choice">已有云连接</label><select id="cloud-connection-choice">${choices}</select></div>`:'';
    let step='';
    if(!c) step='<p>连接阿里云后，Watt 才能列出你授权的 ECS。</p><button class="button" type="button" data-cloud-create>连接阿里云</button>';
    else if(c.state==='REVOKED') step='<p>这个云连接已撤销。请选择其他连接或创建新连接。</p>';
    else if(!c.role_arn) step=`<h3>在阿里云完成授权</h3><p>Watt 将查看授权账号中的 ECS，并检查目标是否具备部署条件。此时不会获得部署执行权限。</p><a href="https://ram.console.aliyun.com/roles" target="_blank" rel="noopener" class="button secondary">前往阿里云完成授权</a><details class="advanced-disclosure"><summary>查看角色信任配置</summary><p>建议角色名：${escape(c.recommended_role_name)}</p><pre class="code-view">${escape(JSON.stringify(c.trust_policy,null,2))}</pre></details><form id="cloud-role-form"><div class="field"><label for="cloud-role-arn">完成后填写角色 ARN</label><input id="cloud-role-arn" name="role_arn" required placeholder="acs:ram::…:role/WattECSDelivery"></div><button class="button" type="submit">继续</button></form>`;
    else if(c.state==='AWAITING_CLOUD_AUTHORIZATION'||c.state==='EXPIRED'||c.state==='INVALID') step=`<h3>验证云连接</h3><p>请先在阿里云把只读发现策略授予这个角色，再返回验证。</p><a href="https://ram.console.aliyun.com/roles" target="_blank" rel="noopener" class="button secondary">前往阿里云完成授权</a><details class="advanced-disclosure"><summary>查看发现策略和信任配置</summary><pre class="code-view">${escape(JSON.stringify(c.discovery_policy,null,2))}</pre><pre class="code-view">${escape(JSON.stringify(c.trust_policy,null,2))}</pre></details><button class="button" type="button" data-cloud-verify>验证并查找 ECS</button>`;
    else if(!c.target) step=`<h3>选择一台 ECS</h3><p>请选择 Watt 从授权账号发现的资源。</p>${c.discovered_targets.length?c.discovered_targets.map(item=>`<div class="result-row"><div><strong>${escape(item.name)}</strong><p>${escape(item.region_id)} · ${escape(item.status)} · ${escape(item.os_name)} · 云助手 ${item.cloud_assistant_ready?'可用':'不可用'}</p></div><button class="button secondary" type="button" data-cloud-select="${escape(item.selection_token)}">选择</button></div>`).join(''):'<p>没有发现可选的 ECS。请检查授权范围。</p>'}`;
    else if(c.state!=='READY') step=`<h3>授权这台 ECS</h3><p>目标：${escape(c.target.name)} · ${escape(c.target.region_id)}。Watt 需要只对这台 ECS 执行受限部署；不会获得通用服务器管理权限。</p><a href="https://ram.console.aliyun.com/roles" target="_blank" rel="noopener" class="button secondary">前往阿里云授权此主机</a><details class="advanced-disclosure"><summary>查看精确目标策略</summary><pre class="code-view">${escape(JSON.stringify(c.target_policy,null,2))}</pre></details><button class="button" type="button" data-cloud-verify-target>验证目标授权</button>`;
    else {
      const prior=state.targetDeployments.find(d=>d.state==='SUCCEEDED'&&d.target.account_id===c.target.account_id&&d.target.region_id===c.target.region_id&&d.target.instance_id===c.target.instance_id);
      step=`<h3>确认本次部署</h3><div class="facts"><div class="fact"><span class="fact-label">成果版本</span><span>${escape(state.fingerprint?.slice(0,16))}</span></div><div class="fact"><span class="fact-label">目标 ECS</span><span>${escape(c.target.name)} · ${escape(c.target.region_id)}</span></div><div class="fact"><span class="fact-label">运行方式</span><span>Watt 管理的独立容器</span></div>${prior?`<div class="fact"><span class="fact-label">当前 Watt 部署</span><span>${escape(prior.manifest_id.slice(0,12))} · 端口 ${escape(prior.port)}。将先验证新版本，再替换此精确运行版本。</span></div>`:''}</div><form id="cloud-deploy-form"><div class="field"><label for="cloud-port">对外端口</label><input id="cloud-port" name="port" type="number" min="1024" max="65535" value="${prior?.port||8080}" required></div><div class="field"><label for="cloud-rationale">本次授权依据</label><input id="cloud-rationale" name="rationale" required placeholder="确认把这个已验收版本部署到所选 ECS"></div><p class="muted">Watt 会先检查服务器条件和端口归属。若需要安装软件或提升权限，部署会停止并说明原因。</p><button class="button" type="submit">授权并部署</button></form>`;
    }
    node.innerHTML=`${choose}<div class="link-row"><button class="button quiet" type="button" data-cloud-create>添加云连接</button></div>${step}<p id="cloud-delivery-message" class="muted" role="status"></p>`;
  }
  async function loadConnection(id) {
    state.connection=await request(`/api/cloud-connections/aliyun/${encodeURIComponent(id)}`);
    state.targetDeployments=await request(`/api/cloud-connections/aliyun/${encodeURIComponent(id)}/deployments`);
    state.connections=await request('/api/cloud-connections/aliyun');
    await renderFlow();
  }
  async function open() {
    state.open=true;
    state.connections=await request('/api/cloud-connections/aliyun');
    if(state.connections.length)await loadConnection(state.connections[0].id);
    else await renderFlow();
    box()?.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  window.WattCloudDelivery={blockerCopy,render(detail){
    const m=detail.manifest,a=detail.acceptance,s=detail.summary;
    if(!m.software||!a||a.decision!=='ACCEPT'||!detail.current)return;
    state.work=s.work_id;state.manifest=m.id;state.fingerprint=m.fingerprint;
    state.deployments=detail.cloud_deployments||[];state.targetDeployments=[];
    state.open=false;state.connection=null;
    const current=state.deployments[0];
    const panel=document.createElement('section');panel.className='detail-panel';
    panel.innerHTML=`<h2>阿里云部署</h2><p>${current?escape({SUCCEEDED:'部署成功',NEEDS_HUMAN_ATTENTION:'需要你处理',ROLLED_BACK:'已回滚',FAILED:'部署失败'}[current.state]||'正在部署'):'这个已验收成果尚未部署到阿里云。'}</p>${current?.blocker?`<p class="muted">${escape(blockerCopy(current))}</p>`:''}<button class="button" type="button" data-cloud-open>部署到阿里云</button><div id="cloud-delivery-flow"></div>`;
    document.getElementById('content')?.append(panel);
  }};
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-cloud-open],[data-cloud-create],[data-cloud-verify],[data-cloud-select],[data-cloud-verify-target]');
    if(!button)return;
    button.disabled=true;
    try{
      if(button.hasAttribute('data-cloud-open'))await open();
      else if(button.hasAttribute('data-cloud-create')){
        const result=await request('/api/cloud-connections/aliyun','POST');
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-verify')){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/verify`,'POST');
        await loadConnection(result.id);
      }else if(button.dataset.cloudSelect){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/select`,'POST',
          {selection_token:button.dataset.cloudSelect});
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-verify-target')){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/verify-target`,'POST');
        await loadConnection(result.id);
      }
    }catch(error){message(error.message,true);}finally{button.disabled=false;}
  });
  document.addEventListener('change',async event=>{
    if(event.target.id==='cloud-connection-choice'){
      try{await loadConnection(event.target.value);}catch(error){message(error.message,true);}
    }
  });
  document.addEventListener('submit',async event=>{
    const form=event.target;
    if(form.id!=='cloud-role-form'&&form.id!=='cloud-deploy-form')return;
    event.preventDefault();const button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    try{
      if(form.id==='cloud-role-form'){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/role`,'POST',
          {role_arn:form.elements.namedItem('role_arn').value.trim()});
        await loadConnection(result.id);
      }else{
        const c=state.connection,p=Number(form.elements.namedItem('port').value);
        const prior=state.targetDeployments.find(d=>d.state==='SUCCEEDED'&&d.port===p&&
          d.target.account_id===c.target.account_id&&d.target.region_id===c.target.region_id&&
          d.target.instance_id===c.target.instance_id);
        message('正在检查交付成果并部署，请勿重复提交。');
        const auth=await request(`/api/works/${state.work}/cloud-deliveries/authorize`,'POST',{
          connection_id:c.id,manifest_id:state.manifest,manifest_fingerprint:state.fingerprint,
          target_account_id:c.target.account_id,target_region_id:c.target.region_id,
          target_instance_id:c.target.instance_id,expected_current_deployment_id:prior?.id||null,
          port:p,rationale:form.elements.namedItem('rationale').value.trim()});
        const result=await request(`/api/cloud-deliveries/${auth.id}/execute`,'POST');
        message(result.state==='SUCCEEDED'?'部署成功，运行及公网验证均已通过。':
          `部署状态：${result.state}。${blockerCopy(result)||'请查看证据。'}`,result.state!=='SUCCEEDED');
      }
    }catch(error){message(error.message,true);}finally{button.disabled=false;}
  });
})();
