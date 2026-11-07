"""One mission ledger linking existing cases, native jobs and meetings."""
from dataclasses import asdict
import hashlib
import json
import threading
import time
import uuid

TRANSITIONS={'CREATED':{'PLANNING','IN_PROGRESS','CANCELLED'},'PLANNING':{'IN_PROGRESS','BLOCKED','CANCELLED'},
 'IN_PROGRESS':{'AWAITING_HUMAN','BLOCKED','CANCELLED'},'AWAITING_HUMAN':{'COMPLETED','IN_PROGRESS','BLOCKED','CANCELLED'},
 'BLOCKED':{'IN_PROGRESS','CANCELLED'},'COMPLETED':{'IN_PROGRESS'},'CANCELLED':set()}


class Workspace:
    def __init__(self,workflow):
        self.w=workflow;self.store=workflow.store;self.auth=workflow.authorization;self.lock=threading.RLock()

    def get(self,mid,p):
        self.auth.require(p,role='operator')
        m=self.store.get('mission',mid)
        if not m:raise KeyError('Mission not found')
        if m['created_by']!=p.subject and '*' not in p.scopes and f'mission:{mid}:manage' not in p.scopes:
            raise PermissionError('Mission access required')
        return m

    def save(self,m,event,actor):
        self.store.put('mission',m['mission_id'],m)
        self.store.event('mission.'+event,m['mission_id'],actor,{'status':m['status'],'case_id':m.get('case_id')},actor_type='human')
        return m

    def tasks(self,m):
        tasks=[{**t,'source':'mission','mission_id':m['mission_id']} for t in m['tasks']]
        if m.get('meeting_id'):
            tasks.extend({**t,'source':'meeting','mission_id':m['mission_id']} for t in (self.store.get('meeting',m['meeting_id']) or {}).get('tasks',[]))
        if m.get('case_id') in self.w.cases:
            tasks.extend({**asdict(t),'owner_id':t.owner,'source':'case','mission_id':m['mission_id']} for t in self.w.cases[m['case_id']].tasks)
        return tasks

    def create(self,args,p):
        self.auth.require(p,role='operator')
        kind=args['mission_type']
        if kind not in ('engineering_review','idea_studio') or not args.get('title','').strip() or not args.get('objective','').strip():
            raise ValueError('Valid mission type, title and objective required')
        mid='MISSION-'+uuid.uuid4().hex
        m={'mission_id':mid,'mission_type':kind,'title':args['title'][:200],'objective':args['objective'][:4000],
           'created_by':p.subject,'created_at':time.time(),'status':'CREATED','switch_room_id':args.get('switch_room_id'),
           'discord_channel_id':args.get('discord_channel_id'),'discord_thread_id':None,'case_id':None,'meeting_id':None,
           'assigned_agents':['clerk','historian','prosecutor','defender'],'tasks':[],'decisions':[],'evidence_refs':[],
           'native_job_ids':[],'next_action':'Start native collaboration'}
        if kind=='engineering_review' and args.get('pr_url'):
            m['case_id']=self.w.open_case(args['pr_url'],args['services'],p).case_id
        elif kind=='engineering_review':
            from .models import Case
            case=Case('SC-'+uuid.uuid4().hex,'','',[],'Not verified',deployment_target='Not specified',change_summary=m['objective'])
            with self.w.lock:
                self.w.cases[case.case_id]=case;self.store.put('case',case.case_id,case)
                self.store.event('case.question_opened',case.case_id,p.subject,{'mission_id':mid,'no_repository_evidence':True},actor_type='human')
            m['case_id']=case.case_id
        self.save(m,'created',p.subject)
        self.notify(m,'mission-control','Mission created: '+m['title'])
        if kind=='idea_studio':self.notify(m,'my-projects','Project captured: '+m['objective'])
        else:self.notify(m,'case-docket','Case opened: '+m['case_id']+' · '+(args.get('pr_url') or 'Technical question; repository evidence not supplied'))
        return m

    def notify(self,m,channel,text):
        key=hashlib.sha256((m['mission_id']+channel+text).encode()).hexdigest()
        self.store.put('discord_outbox',key,{'id':key,'channel':channel,'correlation_id':m['mission_id'],
            'content':f"[{m['mission_id']}] {text}",'status':'PENDING','attempts':0})
        stored=self.store.get('mission',m['mission_id']) or m
        if stored.get('discord_thread_id') and channel not in ('approvals','agent-traces','system-alerts','mission-control'):
            thread_key=key+':thread'
            self.store.put('discord_outbox',thread_key,{'id':thread_key,'channel':channel,'destination_id':stored['discord_thread_id'],
                'correlation_id':m['mission_id'],'content':f"[{m['mission_id']}] {text}",'status':'PENDING','attempts':0})

    def start(self,m,p):
        if m['status'] not in ('CREATED','PLANNING','BLOCKED','COMPLETED','AWAITING_HUMAN'):
            raise ValueError('Mission is already running')
        if not m['switch_room_id']:
            workers=getattr(self.w,'switch_workers',[])
            clerk=next((w for w,t in workers if w.role=='clerk' and t.is_alive() and w.client.connected),None)
            if not clerk:raise ValueError('A live Switch clerk is required; no local fallback')
            m['switch_room_id']=clerk.client.room_id
        m['status']='IN_PROGRESS';m['next_action']='Waiting for native Switch agents';m['last_started_at']=time.time()
        self.save(m,'started',p.subject)
        notification_id='notification-'+uuid.uuid4().hex
        self.store.put('switch_notification',notification_id,{'notification_id':notification_id,'case_id':m['mission_id'],'mission_id':m['mission_id'],
            'switch_room_id':m['switch_room_id'],'status':'PENDING','content':f"[{m['mission_id']}] {m['title']}: {m['objective']}",'investigate':True})
        return m

    def action(self,action,args,p):
        if action=='create':return self.create(args,p)
        if action=='snapshot':return self.snapshot(p)
        with self.lock:
            m=self.get(args['mission_id'],p);mid=m['mission_id']
            if action=='start' or action=='resume':return self.start(m,p)
            if action=='decision':
                self.auth.require(p,role='approver',scope=f'mission:{mid}:decision')
                if m['status']!='AWAITING_HUMAN':raise ValueError('Mission must await a human decision')
                text=args['text'].strip()
                if not text:raise ValueError('Decision text required')
                d={'id':'DEC-'+uuid.uuid4().hex,'text':text,'actor':p.subject,'timestamp':time.time()}
                m['decisions'].append(d);m['next_action']='Create tasks or complete the mission'
                self.notify(m,'approvals','Human decision recorded: '+text)
                return self.save(m,'decision',p.subject)
            if action=='task':
                if not args.get('description') or not args.get('owner_id'):raise ValueError('Task description and owner required')
                m['tasks'].append({'id':'TASK-'+uuid.uuid4().hex,'description':args['description'],'owner_id':args['owner_id'],'status':'OPEN'})
            elif action=='task-update':
                if args['status'] not in ('OPEN','IN_PROGRESS','BLOCKED','DONE'):raise ValueError('Invalid task status')
                task=next((t for t in self.tasks(m) if t['id']==args['task_id']),None)
                if not task:raise KeyError('Task not found')
                if task['owner_id']!=p.subject:self.auth.require(p,scope=f'mission:{mid}:decision')
                if task['source']=='meeting':self.w.meetings.update_task(m['meeting_id'],task['id'],args['status'],p)
                elif task['source']=='case':
                    with self.w.lock:
                        case=self.w.cases[m['case_id']]
                        next(t for t in case.tasks if t.id==task['id']).status=args['status']
                        self.store.put('case',case.case_id,case)
                else:next(t for t in m['tasks'] if t['id']==task['id'])['status']=args['status']
            elif action=='transition':
                state=args['status']
                if state not in TRANSITIONS[m['status']]:raise ValueError('Invalid mission transition')
                if state=='COMPLETED':
                    self.auth.require(p,role='approver',scope=f'mission:{mid}:decision')
                    if not any(d['timestamp']>=m.get('last_started_at',0) for d in m['decisions']):raise PermissionError('Explicit human decision for this work cycle required')
                    if any(t['status']!='DONE' for t in self.tasks(m)):raise ValueError('Resolve open tasks first')
                m['status']=state
            elif action=='meeting':
                meeting=self.w.meetings.start(m['title'],p,args.get('mode','Professional Colleague'))
                m['meeting_id']=meeting['meeting_id'];meeting['mission_id']=mid;self.store.put('meeting',meeting['meeting_id'],meeting)
            elif action=='research':
                result=self.w.research.verify(args['claim'],args['urls'],p,mid)
                m['evidence_refs'].append(result);self.save(m,'research',p.subject);return result
            elif action=='assignment':
                result=self.w.scope.set_assignment({**args,'mission_id':mid,'case_id':m.get('case_id')},p)
                self.save(m,'scope_assigned',p.subject);return result
            elif action=='court':
                if not m['case_id']:m['case_id']=self.w.open_case(args['pr_url'],args['services'],p).case_id
                elif not self.w.cases[m['case_id']].pr_url:self.w.attach_pull_request(m['case_id'],args['pr_url'],args['services'],p)
                return self.save(m,'case_linked',p.subject)
            elif action=='review':
                case=self.w.cases[m['case_id']]
                if not case.pr_url:raise ValueError('Attach real PR evidence before the standalone courtroom review; native agents can review technical questions')
                result=self.w.review(m['case_id'],p)
                m['status']='AWAITING_HUMAN';m['next_action']='Review advisory and record a human verdict'
                self.save(m,'reviewed',p.subject);return result
            elif action=='verdict':
                result=self.w.decide(m['case_id'],args['command'],p)
                m['decisions'].append({'id':'DEC-'+uuid.uuid4().hex,'text':args['command'],'actor':p.subject,'timestamp':time.time()})
                m['status']='AWAITING_HUMAN';m['next_action']='Review GitHub plan or follow-up tasks'
                self.save(m,'verdict',p.subject);self.notify(m,'approvals','Human verdict: '+args['command'])
                return {'release_brief':result}
            elif action=='github-plan':
                plan=self.w.github_plan(m['case_id'],p)
                return {'plan':plan,'plan_hash':hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()}
            elif action=='github-execute':
                result=self.w.execute_github(m['case_id'],p,args['plan_hash'])
                if result['status']=='CONFIRMED':self.notify(m,'github-results','Confirmed GitHub artifacts: '+', '.join(result['urls']))
                return result
            elif action=='simulate':
                result=self.w.parallel_earth.run_simulation(self.w.cases[m['case_id']],estimated_downtime_minutes=args.get('downtime_minutes',15),
                    synthetic_requests=args.get('requests',1000),failure_probability=args.get('failure_probability',.01),seed=args.get('seed',0))
                self.store.put('simulation',m['case_id'],result);self.notify(m,'parallel-earth','Modeled risk updated; not production telemetry');return asdict(result)
            else:raise ValueError('Unknown workspace action')
            return self.save(m,action,p.subject)

    def complete_native(self,job):
        mid=job.get('mission_id')
        with self.lock:
            if self.store.get('native_projection',job['job_id']):return
            m=self.store.get('mission',mid) if mid else None
            case_id=m.get('case_id') if m else job.get('case_id')
            if case_id and case_id in self.w.cases:
                from .models import CaseState
                case=self.w.cases[case_id]
                if case.state==CaseState.CASE_OPENED:
                    case.state=CaseState.AWAITING_VERDICT
                    self.store.put('advisory',case.case_id,{'prosecutor_indictment':job['results']['prosecutor'],
                        'defender_rebuttal':job['results']['defender'],'judge_verdict':job['results']['clerk'],
                        'binding_authorization':False,'native_job_id':job['job_id']})
                    self.store.put('case',case.case_id,case)
            if not m:
                self.store.put('native_projection',job['job_id'],{'case_id':case_id})
                return
            if job['job_id'] not in m['native_job_ids']:m['native_job_ids'].append(job['job_id'])
            m['status']='AWAITING_HUMAN';m['next_action']='Review agent findings and record a human decision'
            self.store.put('mission',mid,m)
            self.notify(m,'my-projects' if m['mission_type']=='idea_studio' else 'case-docket',job['results']['clerk'])
            self.store.event('mission.advisory_ready',mid,'switch-clerk',{'native_job_id':job['job_id'],'binding_authorization':False},actor_type='agent',source_platform='switch')
            self.store.put('native_projection',job['job_id'],{'mission_id':mid})

    def snapshot(self,p):
        if 'viewer' in getattr(p,'roles',[]):
            self.auth.require(p,role='viewer');return {'identity':p.subject,'read_only':True,'missions':[],'agents':[],'cases':[],'meetings':[],'audit':[],'tasks':[],'floor':[],'results':[]}
        self.auth.require(p,role='operator')
        missions=[]
        for m in self.store.list('mission'):
            try:missions.append(self.get(m['mission_id'],p))
            except PermissionError:pass
        admin='*' in p.scopes
        case_ids={m['case_id'] for m in missions};meeting_ids={m['meeting_id'] for m in missions}
        agents=[{'role':w.role,'status':'DISCONNECTED' if not (t.is_alive() and w.client.connected) else
                 'WORKING' if getattr(w,'working',False) else 'IDLE','connected':bool(w.client.connected and t.is_alive()),'receiver_running':t.is_alive(),'room_id':w.client.room_id}
                for w,t in getattr(self.w,'switch_workers',[])]
        audit=[e for e in self.store.events() if admin or e['correlation_id'] in {m['mission_id'] for m in missions}|case_ids|meeting_ids]
        return {'identity':p.subject,'read_only':False,'missions':missions,'agents':agents,
          'cases':[asdict(c) for c in self.w.cases.values() if admin or c.case_id in case_ids],
          'meetings':[m for m in self.store.list('meeting') if admin or m['meeting_id'] in meeting_ids],
          'tasks':[t for m in missions for t in self.tasks(m)], 'floor':[asdict(r) for r in self.w.floor_controller.requests.values() if admin or r.meeting_id in meeting_ids],
          'results':self.store.list('github') if admin else [],'audit':audit[-120:],
          'simulations':[{'case_id':cid,**(self.store.get('simulation',cid) or {})} for cid in (set(self.w.cases) if admin else case_ids) if cid and self.store.get('simulation',cid)],
          'advisories':[{'case_id':cid,**(self.store.get('advisory',cid) or {})} for cid in (set(self.w.cases) if admin else case_ids) if cid and self.store.get('advisory',cid)],
          'scope_events':[e for e in self.store.list('scope_evidence') if admin or e['case_id'] in case_ids],
          'native_jobs':[j for j in self.store.list('native_job') if admin or j.get('mission_id') in {m['mission_id'] for m in missions}]}
