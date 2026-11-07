import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from test_unified_superpowers import setup
from server.groq_agents import CHAIN
from server.switch_groq_worker import SwitchGroqWorker
from server.notifications import Notifications
from server.unified_pipeline import UnifiedBoardroomCourtPipeline


def native_workers(w):
    queue=[];runtime=Mock();runtime.respond.side_effect=lambda role,*args:'Evidence-based advisory from '+role
    peers={r:{'sender_id':'sender:'+r,'mention':'@'+r} for r in CHAIN}
    class Client:
        room_id='contract-room';connected=True
        def __init__(self,r):self.agent_id=r
        def post_message(self,text):
            if '!shipcourt-agent ' in text:
                queue.append((text.split(' ')[0][1:],{'type':'message','room_id':self.room_id,'sequence':len(queue)+1,
                    'payload':{'addressed':True,'sender':'sender:'+self.agent_id,'body':text}}))
            return {'event_id':'contract-event-'+str(len(queue))}
    workers={r:SwitchGroqWorker(w,Client(r),r,{},peers,runtime) for r in CHAIN}
    w.switch_workers=[(v,SimpleNamespace(is_alive=lambda:True)) for v in workers.values()]
    def drain():
        while queue:
            role,event=queue.pop(0);workers[role].handle(event)
    return runtime,workers,drain


@pytest.mark.parametrize('kind',['engineering_review','idea_studio'])
def test_mission_native_decision_tasks_resume_and_persistence(setup,kind):
    w,p,fake,path=setup;runtime,workers,drain=native_workers(w)
    args={'mission_type':kind,'title':'Specific proposal','objective':'Bound checkout retries and validate the assumptions'}
    if kind=='engineering_review':args.update(pr_url='https://github.com/acme/shop/pull/18',services=['checkout-service'])
    m=w.workspace.create(args,p);mid=m['mission_id']
    w.workspace.action('start',{'mission_id':mid},p);delivery=Notifications(w);delivery.flush();drain()
    result=w.workspace.get(mid,p)
    assert result['status']=='AWAITING_HUMAN' and runtime.respond.call_count==4
    assert not fake.writes and len(result['native_job_ids'])==1
    assert all(x['status']=='DELIVERED' for x in w.store.list('switch_notification'))
    with pytest.raises(PermissionError):w.workspace.action('transition',{'mission_id':mid,'status':'COMPLETED'},p)
    w.workspace.action('decision',{'mission_id':mid,'text':'Pursue bounded retries; collect load evidence'},p)
    m=w.workspace.action('task',{'mission_id':mid,'description':'Run load test','owner_id':p.subject},p)
    with pytest.raises(ValueError):w.workspace.action('transition',{'mission_id':mid,'status':'COMPLETED'},p)
    w.workspace.action('task-update',{'mission_id':mid,'task_id':m['tasks'][0]['id'],'status':'DONE'},p)
    w.workspace.action('transition',{'mission_id':mid,'status':'COMPLETED'},p)
    job=w.store.list('native_job')[0];w.workspace.complete_native(job)
    assert w.workspace.get(mid,p)['status']=='COMPLETED' # A replay cannot undo a human decision.
    w.workspace.action('resume',{'mission_id':mid},p);delivery.flush();drain()
    assert len(w.workspace.get(mid,p)['native_job_ids'])==2 and runtime.respond.call_count==8
    with pytest.raises(PermissionError):w.workspace.action('transition',{'mission_id':mid,'status':'COMPLETED'},p)
    restarted=UnifiedBoardroomCourtPipeline(authorization=w.authorization,db_path=path)
    assert restarted.workspace.get(mid,p)['tasks'][0]['status']=='DONE'
    assert restarted.workspace.get(mid,p)['decisions'][0]['actor']==p.subject
    if kind=='engineering_review':
        assert w.cases[result['case_id']].state.value=='AWAITING_VERDICT'
        assert w.store.get('advisory',result['case_id'])['binding_authorization'] is False


def test_disconnected_notification_retries_and_real_receipts(setup):
    w,p,_,_=setup;_,workers,drain=native_workers(w)
    m=w.workspace.create({'mission_type':'idea_studio','title':'Idea','objective':'Compare two prototypes'},p)
    w.workspace.action('start',{'mission_id':m['mission_id']},p)
    clerk=workers['clerk'];clerk.client.connected=False;n=Notifications(w);n.flush()
    assert w.store.list('switch_notification')[0]['status']=='PENDING'
    clerk.client.connected=True;original=clerk.client.post_message
    clerk.client.post_message=lambda text:{};n.flush()
    item=w.store.list('switch_notification')[0];assert item['status']=='FAILED_OR_UNKNOWN' and 'receipt' not in item
    item['next_attempt']=0;w.store.put('switch_notification',item['notification_id'],item)
    clerk.client.post_message=original;n.flush();drain();n.flush()
    assert len(w.store.list('native_job'))==1
    assert w.workspace.get(m['mission_id'],p)['status']=='AWAITING_HUMAN'


def test_scope_notification_investigates_with_active_groq_workers(setup):
    w,p,_,_=setup;runtime,workers,drain=native_workers(w)
    result=w.ingest_violation({'agent_id':'frontend','event_id':'tool-1','decision_taken':'BLOCK','explanation':'Cross-scope pricing edit'},p)
    Notifications(w).flush();drain()
    assert runtime.respond.call_count==4 and w.cases[result['case_id']].state.value=='AWAITING_VERDICT'
    assert {'dev-watch','case-docket','agent-handoffs'} <= {x['channel'] for x in w.store.list('discord_outbox')}
    assert not w.store.get('advisory',result['case_id'])['binding_authorization']


def test_mission_permissions_and_guest_projection(setup):
    w,p,_,_=setup
    from server.authorization import Principal
    import time
    def register(subject,roles,scopes):
        principal=Principal(subject,frozenset(roles),frozenset(scopes),subject,time.time()+300)
        w.authorization._sessions[subject]=principal;return principal
    m=w.workspace.create({'mission_type':'idea_studio','title':'Private','objective':'A private proposal'},p)
    other=register('teammate',['operator'],[])
    with pytest.raises(PermissionError):w.workspace.get(m['mission_id'],other)
    assert not w.workspace.snapshot(other)['missions']
    guest=register('judge',['viewer'],[])
    assert w.workspace.snapshot(guest)['read_only'] and not w.workspace.snapshot(guest)['audit']
    with pytest.raises(PermissionError):w.workspace.action('create',{'mission_type':'idea_studio','title':'x','objective':'x'},guest)


def test_meeting_recap_is_persisted_and_queued_once(setup):
    w,p,_,path=setup
    m=w.workspace.create({'mission_type':'idea_studio','title':'Meeting','objective':'Plan a prototype'},p)
    linked=w.workspace.action('meeting',{'mission_id':m['mission_id']},p);mid=linked['meeting_id']
    w.meetings.consent(mid,p,True);w.meetings.transcript(mid,'Compare the prototypes',p,'spoken-1')
    w.meetings.decision(mid,'Build prototype A',p,['spoken-1'])
    first=w.meetings.end(mid,p);second=w.meetings.end(mid,p)
    assert first==second and first['mission_id']==m['mission_id']
    assert len([x for x in w.store.list('discord_outbox') if x['channel']=='meeting-recaps'])==1
    assert w.store.get('meeting',mid)['recap']['decisions'][0]['actor']==p.subject


def test_hook_uses_server_assignment_to_link_existing_pr_case(setup):
    w,p,_,_=setup
    m=w.workspace.create({'mission_type':'engineering_review','title':'Checkout','objective':'Investigate checkout boundaries',
        'pr_url':'https://github.com/acme/shop/pull/18','services':['checkout-service']},p)
    w.workspace.action('assignment',{'mission_id':m['mission_id'],'agent_id':'frontend','task_id':'front-1',
        'task_description':'UI','allowed_paths':['frontend/**'],'restricted_paths':['checkout/**']},p)
    event={'agent_id':'frontend','event_id':'real-contract-1','decision_taken':'BLOCK','explanation':'Attempted checkout edit','mission_id':'spoofed'}
    result=w.ingest_violation(event,p)
    assert result['case_id']==m['case_id']
    assert w.workspace.get(m['mission_id'],p)['evidence_refs'][0]['event_id']==event['event_id']
    assert w.store.list('scope_evidence')[0]['mission_id']==m['mission_id']


def test_technical_question_has_real_case_and_failed_agent_blocks_mission(setup):
    w,p,_,_=setup;runtime,workers,drain=native_workers(w)
    m=w.workspace.create({'mission_type':'engineering_review','title':'Question','objective':'Analyze bounded retries'},p)
    assert m['case_id'] in w.cases and not w.cases[m['case_id']].pr_url
    runtime.respond.side_effect=RuntimeError('Controlled provider unavailable')
    w.workspace.action('start',{'mission_id':m['mission_id']},p);Notifications(w).flush();drain()
    assert w.workspace.get(m['mission_id'],p)['status']=='BLOCKED'
    assert w.store.list('native_job')[0]['status']=='BLOCKED'


def test_linked_voice_controls_recheck_floor_and_persist_recap(setup):
    w,p,_,_=setup
    from server.voice_bridge import VoiceBridge
    bridge=VoiceBridge(w,'guild',{})
    m=w.workspace.create({'mission_type':'idea_studio','title':'Voice','objective':'Compare options'},p)
    linked=w.workspace.action('meeting',{'mission_id':m['mission_id']},p)
    meeting=bridge.dispatch('start',{'mission_id':m['mission_id']},p)
    mid=meeting['meeting_id'];assert mid==linked['meeting_id']
    first=w.floor_controller.raise_hand(mid,'third-voice','hand','Evidence','A proposal',80)
    assert bridge.dispatch('text',{'meeting_id':mid,'request_id':first.request_id},p)['contribution']=='A proposal'
    second=w.floor_controller.raise_hand(mid,'another-agent','hand','Other evidence','Another proposal',80)
    bridge.dispatch('grant',{'meeting_id':mid,'request_id':second.request_id},p)
    bridge.dispatch('speak',{'meeting_id':mid,'request_id':second.request_id},p)
    bridge.dispatch('mute',{'meeting_id':mid},p)
    assert bridge.dispatch('release',{'meeting_id':mid,'request_id':second.request_id},p)['state']=='interrupted'
    assert bridge.dispatch('state',{'meeting_id':mid},p)['muted']
    bridge.dispatch('end',{'meeting_id':mid},p)
    assert bridge.dispatch('state',{'meeting_id':mid},p)['status']=='ENDED'
    assert w.store.get('meeting',mid)['recap']['mission_id']==m['mission_id']


def test_workspace_github_plan_uses_real_service_and_shared_task_sources(setup):
    w,p,fake,_=setup
    m=w.workspace.create({'mission_type':'engineering_review','title':'PR','objective':'Review actual evidence',
        'pr_url':'https://github.com/acme/shop/pull/18','services':['checkout-service']},p)
    args={'mission_id':m['mission_id']}
    w.workspace.action('review',args,p)
    with pytest.raises(ValueError):w.workspace.action('github-plan',args,p)
    w.workspace.action('verdict',{**args,'command':'CONDITIONS collect load evidence'},p)
    plan=w.workspace.action('github-plan',args,p)
    assert not fake.writes
    with pytest.raises(ValueError):w.workspace.action('github-execute',{**args,'plan_hash':'wrong'},p)
    result=w.workspace.action('github-execute',{**args,'plan_hash':plan['plan_hash']},p)
    assert result['status']=='CONFIRMED' and len(fake.writes)==3
    assert any(o['channel']=='github-results' and 'https://github.com/' in o['content'] for o in w.store.list('discord_outbox'))
    linked=w.workspace.action('meeting',args,p);mid=linked['meeting_id']
    w.meetings.assign_task(mid,'Meeting follow-up',p.subject,p)
    tasks=w.workspace.snapshot(p)['tasks'];meeting_task=next(t for t in tasks if t['source']=='meeting')
    w.workspace.action('task-update',{**args,'task_id':meeting_task['id'],'status':'DONE'},p)
    assert w.meetings.get(mid)['tasks'][0]['status']=='DONE'
    assert any(t['source']=='case' for t in tasks)
