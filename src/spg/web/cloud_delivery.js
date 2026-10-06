/* Guided Alibaba Cloud Delivery on a qualified Deliverable detail page. */
(() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {work:null, manifest:null, fingerprint:null, deployments:[],
    targetDeployments:[], connections:[], connection:null, open:false,
    deployIntent:false};
  async function request(path, method='GET', body) {
    const response = await fetch(path,{method,credentials:'same-origin',
      headers:body===undefined?{}:{'Content-Type':'application/json'},
      ...(body===undefined?{}:{body:JSON.stringify(body)})});
    const value = await response.json();
    if(!response.ok) throw new Error(value.message||'请求失败');
    return value;
  }
  function box() { return document.getElementById('cloud-delivery-flow'); }
  function message(value, failure=false) {
    const node=document.getElementById('cloud-delivery-message');
    if(node) {node.textContent=value;node.className=failure?'notice-error':'muted';}
  }
  function errorCopy(message) {
    return /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/.test(message)?
      '本次云操作未能完成，请查看保留的证据。':message;
  }
  function blockerCopy(deployment) {
    if(!deployment?.blocker)return '';
    return deployment.human_visible?.blocker||'部署条件未满足，尚未通过验证。';
  }
  async function renderFlow() {
    const node=box();if(!node||!state.open)return;
    const c=state.connection;
    const choices=state.connections.map(item=>`<option value="${escape(item.id)}" ${c?.id===item.id?'selected':''}>${escape(item.target?.name||item.role_arn||'待授权的云连接')} · ${escape(item.human_visible?.status||'云连接状态待确认')}</option>`).join('');
    const choose=state.connections.length?`<div class="field"><label for="cloud-connection-choice">已有云连接</label><select id="cloud-connection-choice">${choices}</select></div>`:'';
    const reselect=c?.target&&c.state!=='REVOKED'?`<div class="workspace-review"><p>当前目标：${escape(c.target.name)} · ${escape(c.target.region_id)} · ${escape(c.target.instance_id)}。更换目标会重新发现 ECS 并验证现有云连接；历史部署记录会保留。</p><button class="button secondary" type="button" data-cloud-reselect>重新选择 ECS</button></div>`:'';
    let step='';
    if(!c) step='<p>连接阿里云后，Watt 才能列出你授权的 ECS。</p><button class="button" type="button" data-cloud-create>连接阿里云</button>';
    else if(c.state==='REVOKED') step='<p>这个云连接已撤销。请选择其他连接或创建新连接。</p>';
    else if(!c.role_arn) step=`<h3>在阿里云完成一次连接授权</h3><p>Watt 将在你选择目标并授权部署后，只对该 ECS 执行固定类型的部署操作。</p><a href="https://ram.console.aliyun.com/roles" target="_blank" rel="noopener" class="button secondary">前往阿里云完成授权</a><details class="advanced-disclosure"><summary>查看角色信任配置</summary><p>建议角色名：${escape(c.recommended_role_name)}</p><pre class="code-view">${escape(JSON.stringify(c.trust_policy,null,2))}</pre></details><form id="cloud-role-form"><div class="field"><label for="cloud-role-arn">完成后填写角色 ARN</label><input id="cloud-role-arn" name="role_arn" required placeholder="acs:ram::…:role/WattECSDelivery"></div><button class="button" type="submit">继续</button></form>`;
    else if(c.state==='AWAITING_CLOUD_AUTHORIZATION'||c.state==='EXPIRED'||c.state==='INVALID') step=`<h3>验证云连接</h3><p>请在阿里云为这个角色配置一次受限连接策略，再返回 Watt。之后更换 ECS 无需再次编辑 RAM。</p><a href="https://ram.console.aliyun.com/roles" target="_blank" rel="noopener" class="button secondary">前往阿里云完成授权</a><details class="advanced-disclosure"><summary>查看连接策略和信任配置</summary><pre class="code-view">${escape(JSON.stringify(c.connection_policy,null,2))}</pre><pre class="code-view">${escape(JSON.stringify(c.trust_policy,null,2))}</pre></details><button class="button" type="button" data-cloud-verify>验证并查找 ECS</button>`;
    else if(!c.target) step=`<h3>选择一台 ECS</h3><p>请选择 Watt 从授权账号发现的资源。</p>${c.discovered_targets.length?c.discovered_targets.map(item=>`<div class="result-row"><div><strong>${escape(item.name)}</strong><p>${escape(item.region_id)} · ${escape(item.status)} · ${escape(item.os_name)} · 云助手 ${item.cloud_assistant_ready?'可用':'不可用'}</p></div><button class="button secondary" type="button" data-cloud-select="${escape(item.selection_token)}">选择</button></div>`).join(''):'<p>没有发现可选的 ECS。请检查授权范围。</p>'}`;
    else if(c.state!=='READY') step=/^Alibaba Cloud Linux\s+3(?:\.|\b)/.test(c.target.os_name)?`<h3>验证当前云连接能力</h3><p>目标：${escape(c.target.name)} · ${escape(c.target.region_id)}。Watt 将用当前连接验证能力，不需要为这台 ECS 新建策略。</p><button class="button" type="button" data-cloud-verify-target>重试连接验证</button>`:`<h3>不支持这台 ECS</h3><p>${escape(c.target.os_name)} 不属于当前可自动准备的 Alibaba Cloud Linux 3 主机。请选择另一台 ECS。</p>`;
    else {
      const prior=state.targetDeployments.find(d=>d.state==='SUCCEEDED'&&d.target.account_id===c.target.account_id&&d.target.region_id===c.target.region_id&&d.target.instance_id===c.target.instance_id);
      const latest=state.targetDeployments.find(d=>d.target.account_id===c.target.account_id&&d.target.region_id===c.target.region_id&&d.target.instance_id===c.target.instance_id);
      const targetLabel=`${escape(c.target.name)} · ${escape(c.target.region_id)} · ${escape(c.target.instance_id)}`;
      step=`<h3>确认本次部署</h3><div class="facts"><div class="fact"><span class="fact-label">成果版本</span><span>${escape(state.fingerprint?.slice(0,16))}</span></div><div class="fact"><span class="fact-label">目标 ECS</span><span>${targetLabel}</span></div><div class="fact"><span class="fact-label">环境状态</span><span>Watt 将自动检查并在受支持时准备</span></div>${prior?`<div class="fact"><span class="fact-label">当前 Watt 部署</span><span>${escape(prior.manifest_id.slice(0,12))} · 端口 ${escape(prior.port)}。</span></div>`:''}</div>${latest?.blocker?`<p class="muted">${escape(blockerCopy(latest))}</p>`:''}<form id="cloud-deploy-form"><div class="field"><label for="cloud-port">部署端口</label><input id="cloud-port" name="port" type="number" min="1024" max="65535" value="${prior?.port||8080}" required></div><div class="field"><label for="cloud-exposure-mode">网络暴露方式</label><select id="cloud-exposure-mode" name="exposure_mode" required><option value="PRIVATE" selected>内部部署：不修改安全组</option><option value="PUBLIC">公网部署：允许所有 IPv4 地址访问所选 TCP 端口</option></select></div><div class="field"><label for="cloud-rationale">本次授权依据</label><input id="cloud-rationale" name="rationale" required placeholder="确认把这个已验收版本部署到所选 ECS"></div><p class="muted">Watt 会自动准备主机并部署。选择公网部署时，Watt 仅检查或创建当前 ECS 关联安全组中该 TCP 端口的入站规则，并在创建后重新读取规则、验证真实公网 HTTP。不会修改 Nginx 或主机防火墙。</p><details class="advanced-disclosure"><summary>查看一次连接所需的完整受限云策略</summary><pre class="code-view">${escape(JSON.stringify(c.connection_policy,null,2))}</pre></details><button class="button" type="submit">授权并部署</button></form>`;
    }
    node.innerHTML=`${choose}${reselect}<div class="link-row"><button class="button quiet" type="button" data-cloud-create>添加云连接</button></div>${step}<p id="cloud-delivery-message" class="muted" role="status"></p>`;
  }
  async function loadConnection(id) {
    state.deployIntent=false;
    state.connection=await request(`/api/cloud-connections/aliyun/${encodeURIComponent(id)}`);
    state.targetDeployments=await request(`/api/cloud-connections/aliyun/${encodeURIComponent(id)}/deployments`);
    state.connections=await request('/api/cloud-connections/aliyun');
    await renderFlow();
  }
  async function open(preferredConnectionId=null) {
    state.open=true;
    state.connections=await request('/api/cloud-connections/aliyun');
    const selected=preferredConnectionId?
      state.connections.find(item=>item.id===preferredConnectionId):state.connections[0];
    if(preferredConnectionId&&!selected)throw new Error('原云连接已不在当前可用列表中');
    if(selected)await loadConnection(selected.id);
    else await renderFlow();
    box()?.scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  window.WattCloudDelivery={blockerCopy,render(detail){
    const m=detail.manifest,a=detail.acceptance,s=detail.summary;
    if(!m.software||!a||a.decision!=='ACCEPT'||!detail.current)return;
    state.work=s.work_id;state.manifest=m.id;state.fingerprint=m.fingerprint;
    state.deployments=detail.cloud_deployments||[];state.targetDeployments=[];
    state.open=false;state.connection=null;state.deployIntent=false;
    const current=state.deployments[0];
    const panel=document.createElement('section');panel.className='detail-panel';
    panel.innerHTML=`<h2>阿里云部署</h2><p>${current?`${escape(current.human_visible?.status||'部署状态待确认')} · ${escape(current.target.name)} · ${escape(current.target.region_id)} · ${escape(current.target.instance_id)}`:'这个已验收成果尚未部署到阿里云。'}</p>${current?.blocker?`<p class="muted">${escape(blockerCopy(current))}</p>`:''}${current?.connection_id?'<button class="button secondary" type="button" data-cloud-reselect>重新选择 ECS（不部署）</button>':''}<button class="button" type="button" data-cloud-open>查看云连接与目标</button><div id="cloud-delivery-flow"></div>`;
    document.getElementById('content')?.append(panel);
  }};
  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-cloud-open],[data-cloud-create],[data-cloud-verify],[data-cloud-reselect],[data-cloud-select],[data-cloud-verify-target],[data-cloud-show-deploy]');
    if(!button)return;
    button.disabled=true;
    try{
      if(button.hasAttribute('data-cloud-open'))await open(state.deployments[0]?.connection_id);
      else if(button.hasAttribute('data-cloud-create')){
        const result=await request('/api/cloud-connections/aliyun','POST');
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-verify')){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/verify`,'POST');
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-reselect')){
        if(!state.connection)await open(state.deployments[0]?.connection_id);
        if(!state.connection?.target)throw new Error('当前云连接没有可更换的目标 ECS');
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/verify`,'POST');
        await loadConnection(result.id);
      }else if(button.dataset.cloudSelect){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/select`,'POST',
          {selection_token:button.dataset.cloudSelect});
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-verify-target')){
        const result=await request(`/api/cloud-connections/aliyun/${state.connection.id}/verify-target`,'POST');
        await loadConnection(result.id);
      }else if(button.hasAttribute('data-cloud-show-deploy')){
        state.deployIntent=true;
        await renderFlow();
      }
    }catch(error){
      if(state.connection?.id){try{await loadConnection(state.connection.id);}catch(_){}}
      message(errorCopy(error.message),true);
    }finally{button.disabled=false;}
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
        const exposureMode=form.elements.namedItem('exposure_mode').value;
        const prior=state.targetDeployments.find(d=>(d.state==='SUCCEEDED'||
          (exposureMode==='PUBLIC'&&d.state==='NEEDS_HUMAN_ATTENTION'&&d.health_verified&&
            !d.business_verified&&d.manifest_id===state.manifest))&&d.port===p&&
          d.target.account_id===c.target.account_id&&d.target.region_id===c.target.region_id&&
          d.target.instance_id===c.target.instance_id);
        message('正在检查交付成果并部署，请勿重复提交。');
        const auth=await request(`/api/works/${state.work}/cloud-deliveries/authorize`,'POST',{
          connection_id:c.id,manifest_id:state.manifest,manifest_fingerprint:state.fingerprint,
          target_account_id:c.target.account_id,target_region_id:c.target.region_id,
          target_instance_id:c.target.instance_id,expected_current_deployment_id:prior?.id||null,
          port:p,exposure_mode:exposureMode,
          rationale:form.elements.namedItem('rationale').value.trim()});
        const result=await request(`/api/cloud-deliveries/${auth.id}/execute`,'POST');
        message(result.state==='SUCCEEDED'?(exposureMode==='PUBLIC'?
          '公网部署成功，运行及真实公网 HTTP 验证均已通过。':'内部部署成功，目标机运行验证已通过。'):
          `部署状态：${result.human_visible?.status||'待确认'}。${blockerCopy(result)||'请查看证据。'}`,result.state!=='SUCCEEDED');
      }
    }catch(error){message(errorCopy(error.message),true);}finally{button.disabled=false;}
  });
})();
