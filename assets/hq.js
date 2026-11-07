/* Shared backend state. No credential is persisted in JS, storage or URLs. */
(() => {
  'use strict';
  let csrf='', state={}, identity=null, view='Command Center', plan=null;
  const $=id=>document.getElementById(id), rawFetch=window.fetch.bind(window);
  const tabs=['Command Center','Team Workspace','Boardroom OS','Ship Court','Parallel Earth','GitHub Control','Idea Studio','Audit Trail'];
  window.fetch=async (input,options={})=>{
    const url=new URL(typeof input==='string'?input:input.url,location.href);
    if(url.origin===location.origin && url.pathname.startsWith('/api/')){
      const headers=new Headers(options.headers||{});
      if(headers.get('Authorization')?.trim()==='Bearer')headers.delete('Authorization');
      if(!['GET','HEAD'].includes((options.method||'GET').toUpperCase()) && csrf)headers.set('X-CSRF-Token',csrf);
      options={...options,headers,credentials:'same-origin'};
    }
    return rawFetch(input,options);
  };
  async function api(path,body){
    const r=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await r.json();if(!r.ok){const e=new Error(data.error+(data.detail?' · '+data.detail:''));e.status=r.status;throw e;}return data;
  }
  function error(e){$('hq-error').textContent=e?.message||String(e||'');}
  function card(title,data,buttons=[]){
    const el=document.createElement('article');el.className='hq-panel';
    const heading=document.createElement('h3');heading.textContent=title;el.append(heading);
    const pre=document.createElement('pre');pre.textContent=JSON.stringify(data,null,2);el.append(pre);
    for(const [label,fn] of buttons){const b=document.createElement('button');b.textContent=label;b.onclick=()=>run(fn);el.append(b);}return el;
  }
  async function run(fn){try{error('');await fn();}catch(e){error(e);}}
  function selected(){const m=(state.missions||[]).find(m=>m.mission_id===$('hq-mission').value);if(!m)throw new Error('Select a real mission first');return m;}
  function output(data){$('hq-output').textContent=JSON.stringify(data,null,2);}
  async function action(name,args={}){const result=await api('/api/hq/action',{action:name,args:{mission_id:selected().mission_id,...args}});output(result);await refresh();return result;}
  function render(){
    const host=$('hq-records');host.replaceChildren();$('hq-heading').textContent=view;
    const add=(title,data,buttons)=>host.append(card(title,data,buttons));
    let m;try{m=selected();}catch{};
    if(view==='Command Center'||view==='Idea Studio')for(const mission of state.missions||[]){if(view==='Idea Studio'&&mission.mission_type!=='idea_studio')continue;add(mission.title,mission,[['Select mission',()=>{$('hq-mission').value=mission.mission_id;render();}]]);}
    if(view==='Command Center'||view==='Team Workspace')for(const a of state.agents||[])add(a.role,a);
    if(view==='Command Center'&&!state.agents?.length)add('Switch transport',{status:identity?'UNCONFIGURED / DISCONNECTED':'SIGN IN REQUIRED',detail:'Sign in to inspect actual connections.'});
    if(view==='Team Workspace')for(const j of state.native_jobs||[])add(j.job_id,j);
    if(view==='Team Workspace'||view==='Audit Trail')for(const e of state.audit||[])if(view==='Audit Trail'||e.event_type.startsWith('switch.')||e.event_type.startsWith('scope.'))add(e.event_type,e);
    if(view==='Ship Court'){for(const c of state.cases||[])add(c.case_id,c);for(const a of state.advisories||[])add('AI advisory · '+a.case_id,a);}
    if(view==='Team Workspace')for(const e of state.scope_events||[])add('Authenticated scope report',e);
    if(view==='Boardroom OS'){
      for(const mt of state.meetings||[])add(mt.title,mt,[['Consent for myself',()=>api('/api/meetings/consent',{meeting_id:mt.meeting_id,enabled:true}).then(refresh)],['Revoke consent',()=>api('/api/meetings/consent',{meeting_id:mt.meeting_id,enabled:false}).then(refresh)],['End meeting',()=>api('/api/meetings/end',{meeting_id:mt.meeting_id}).then(output).then(refresh)]]);
      for(const r of state.floor||[])add(r.agent_id+' · '+r.state,r,[['Grant floor',()=>api('/api/floor/grants',{request_id:r.request_id}).then(output).then(refresh)],['Dismiss',()=>api('/api/floor/dismiss',{request_id:r.request_id}).then(refresh)],['Interrupt',()=>api('/api/floor/dismiss',{request_id:r.request_id,interrupt:true}).then(refresh)]]);
    }
    if(view==='Parallel Earth')for(const s of state.simulations||[])add('Modeled risk · '+s.case_id,s);
    if(view==='GitHub Control')for(const r of state.results||[])add(r.status,r);
    if(view==='Command Center'||view==='Idea Studio')for(const t of (state.tasks||[]).filter(t=>t.mission_id===m?.mission_id))add(t.description,t,[['Mark in progress',()=>action('task-update',{task_id:t.id,status:'IN_PROGRESS'})],['Mark done',()=>action('task-update',{task_id:t.id,status:'DONE'})]]);
    if(!host.children.length)add('No records yet',{detail:'Create or select a mission. Records appear after the backend confirms them.'});
  }
  async function refresh(){
    try{identity=await api('/api/auth/me');}catch(e){
      if(e.status===401){identity=null;state={};csrf='';plan=null;$('hq-login').hidden=false;$('hq-controls').hidden=true;$('hq-counts').replaceChildren();$('hq-identity').textContent='Sign in to your workspace';$('hq-transport-status').textContent='Sign in for connection status';render();}
      throw e;
    }
    csrf=identity.csrf;state=await api('/api/hq');
    $('hq-identity').textContent=identity.identity+' · '+identity.roles.join(', ');$('hq-login').hidden=true;$('hq-controls').hidden=state.read_only;
    $('hq-transport-status').textContent=(state.agents?.filter(a=>a.connected).length||0)+' Switch transports connected';
    const prior=$('hq-mission').value;$('hq-mission').replaceChildren();
    for(const m of state.missions||[]){const o=document.createElement('option');o.value=m.mission_id;o.textContent=m.title+' · '+m.status;$('hq-mission').append(o);}
    if((state.missions||[]).some(m=>m.mission_id===prior))$('hq-mission').value=prior;
    $('hq-owner').placeholder='Owner identity (e.g. '+identity.identity+')';
    $('hq-counts').replaceChildren();for(const [label,count] of [['Missions',state.missions?.length||0],['Connected agents',state.agents?.filter(a=>a.connected).length||0],['Open tasks',state.tasks?.filter(t=>t.status!=='DONE').length||0],['Awaiting human',state.missions?.filter(m=>m.status==='AWAITING_HUMAN').length||0]]){const span=document.createElement('span');span.className='hq-badge';span.textContent=count+' '+label;$('hq-counts').append(span);}render();
  }
  function activate(name){view=name;$('section-hq').classList.add('active-section');document.querySelectorAll('.view-section').forEach(s=>{if(s.id!=='section-hq')s.classList.remove('active-section');});$('crumb-active').textContent=name;render();}
  for(const name of tabs){const b=document.createElement('button');b.textContent=name;b.onclick=()=>activate(name);$('hq-tabs').append(b);}
  const mapping={overview:'Command Center',switchroom:'Team Workspace',scopeguard:'Team Workspace',courtroom:'Ship Court',graph:'Parallel Earth',brief:'Boardroom OS',ledger:'Audit Trail',github:'GitHub Control',earth:'Parallel Earth',settings:'Idea Studio'};
  window.showView=id=>activate(mapping[id]||'Command Center');
  for(const [key,label] of Object.entries(mapping))for(const id of ['tab-'+key,'mpill-'+key]){const b=$(id);if(b){b.textContent=label;b.onclick=()=>activate(label);}}
  document.querySelector('.switch-env-strip').textContent='Shared SQLite ledger · Official Switch transport · Human approval required · No production telemetry assumed';
  document.querySelector('.switch-top-actions .sw-tag').textContent='SECURE WORKSPACE';
  document.querySelector('.switch-breadcrumb').childNodes.forEach(n=>{if(n.nodeType===1&&n.textContent==='acme/shop')n.textContent='Your workspace';});
  $('hq-login').onsubmit=e=>{e.preventDefault();run(async()=>{const credential=$('hq-credential').value;$('hq-credential').value='';await api('/api/auth/login',{credential});await refresh();});};
  $('hq-logout').onclick=()=>run(async()=>{await api('/api/auth/logout',{});csrf='';state={};identity=null;plan=null;$('hq-login').hidden=false;$('hq-controls').hidden=true;$('hq-identity').textContent='Signed out';$('hq-transport-status').textContent='Sign in for connection status';$('hq-counts').replaceChildren();render();});
  $('hq-refresh').onclick=()=>run(refresh);$('hq-mission').onchange=()=>{plan=null;$('hq-execute').disabled=true;render();};
  $('hq-create').onsubmit=e=>{e.preventDefault();run(async()=>{const args={mission_type:$('hq-kind').value,title:$('hq-title').value,objective:$('hq-objective').value};if($('hq-pr').value)Object.assign(args,{pr_url:$('hq-pr').value,services:$('hq-services').value.split(',').map(s=>s.trim()).filter(Boolean)});const m=await api('/api/hq/action',{action:'create',args});await refresh();$('hq-mission').value=m.mission_id;output(m);render();});};
  document.querySelectorAll('[data-hq]').forEach(b=>b.onclick=()=>run(async()=>{
    const name=b.dataset.hq,args={};
    if(name==='decision')args.text=$('hq-decision').value;
    if(name==='transition')args.status=$('hq-state').value;
    if(name==='task')Object.assign(args,{description:$('hq-task').value,owner_id:$('hq-owner').value||identity.identity});
    if(name==='court')Object.assign(args,{pr_url:$('hq-pr').value,services:$('hq-services').value.split(',').map(s=>s.trim()).filter(Boolean)});
    if(name==='verdict')args.command=$('hq-verdict').value;
    if(name==='research')Object.assign(args,{claim:$('hq-claim').value,urls:$('hq-urls').value.split(',').map(s=>s.trim()).filter(Boolean)});
    if(name==='simulate')Object.assign(args,{downtime_minutes:Number($('hq-downtime').value),requests:Number($('hq-requests').value),failure_probability:Number($('hq-probability').value)});
    b.disabled=true;try{const data=await action(name,args);if(name==='github-plan'){plan={...data,mission_id:selected().mission_id};$('hq-execute').disabled=false;}}finally{b.disabled=false;}
  }));
  $('hq-execute').onclick=()=>run(async()=>{if(!plan||plan.mission_id!==selected().mission_id)throw new Error('Review a plan for this mission first');if(!confirm('Execute the exact GitHub operations shown in the reviewed plan?'))return;await action('github-execute',{plan_hash:plan.plan_hash});plan=null;$('hq-execute').disabled=true;});
  $('hq-export').onclick=()=>run(()=>{const blob=new Blob([JSON.stringify(selected(),null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=selected().mission_id+'.json';a.click();URL.revokeObjectURL(url);});
  window.handleWriteBackAction=()=>activate('GitHub Control');window.adoptTargetUniverse=()=>error(new Error('Record a real human verdict on a selected case. Preview values cannot authorize a change.'));window.exportMultiverseReport=()=>activate('Parallel Earth');
  activate('Command Center');run(refresh);
  setInterval(()=>{if(identity)run(refresh);},15000);
})();
