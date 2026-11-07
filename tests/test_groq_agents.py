from unittest.mock import Mock
import json
import pytest
from server.groq_agents import GroqBudget, GroqCustomRuntime, CHAIN
from server.switch_groq_worker import SwitchGroqWorker
from server.store import Store


def test_budget_serializes_and_waits_for_rolling_tokens():
    clock=[0]
    budget=GroqBudget(tokens_per_minute=100,calls_per_minute=3,clock=lambda:clock[0],sleep=lambda n:clock.__setitem__(0,clock[0]+n))
    assert budget.run(60,lambda:'one')=='one'
    assert budget.run(60,lambda:'two')=='two'
    assert clock[0]>=60
    with pytest.raises(ValueError):budget.run(101,lambda:None)


def test_role_context_is_bounded_and_transient_failures_back_off():
    engine=Mock(k_prosecutor='test-key')
    engine._call_llm.side_effect=[RuntimeError('HTTP Error 429'), 'Real model output']
    sleep=Mock();runtime=GroqCustomRuntime(engine,budget=Mock(),sleep=sleep)
    runtime.budget.run.side_effect=lambda estimate,call:call()
    assert runtime.respond('prosecutor',{'patch':'x'*20000},[])=='Real model output'
    assert len(engine._call_llm.call_args.args[2])<=6000
    sleep.assert_called_once_with(5)


def test_five_roles_handoff_only_to_trusted_peers_and_never_authorize():
    store=Store();workflow=Mock(store=store);runtime=Mock()
    runtime.respond.side_effect=lambda role,*args:'Advisory from '+role
    peers={role:{'agent_id':role,'sender_id':'sender:'+role,'mention':'@'+role} for role in CHAIN}
    queue=[]
    class Client:
        room_id='real-contract-room'
        def __init__(self,role):self.agent_id=role
        def post_message(self,text):
            if '!shipcourt-agent ' in text:
                target=text.split(' ',1)[0][1:]
                queue.append((target,{'type':'message','room_id':self.room_id,'sequence':len(queue)+1,
                    'payload':{'addressed':True,'sender':'sender:'+self.agent_id,'body':text}}))
            return {'event_id':'fixture-receipt'}
    workers={r:SwitchGroqWorker(workflow,Client(r),r,{'human':{'actor_type':'human','roles':['operator']}},peers,runtime) for r in CHAIN}
    workers['clerk'].handle({'type':'message','room_id':'real-contract-room','sequence':1,
        'payload':{'addressed':True,'sender':'admin','body':'!shipcourt discuss fake'}})
    assert not store.list('native_job')
    workers['clerk'].handle({'type':'message','room_id':'real-contract-room','sequence':2,
        'payload':{'addressed':True,'sender':'human','body':'!shipcourt discuss Checkout retry risk'}})
    job=store.list('native_job')[0]
    workers['historian'].step(job['job_id'],'spoofed-agent')
    runtime.respond.assert_not_called()
    while queue:
        role,event=queue.pop(0);workers[role].handle(event)
    result=store.get('native_job',job['job_id'])
    assert list(result['results'])==list(CHAIN)
    assert result['status']=='AWAITING_HUMAN'
    assert runtime.respond.call_count==5
    workers['clerk'].step(job['job_id'],'sender:third_voice')
    assert runtime.respond.call_count==5
    assert len(store.list('groq_context'))==5
    assert store.events()[-1]['payload']['binding_authorization'] is False
