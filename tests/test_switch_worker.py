from unittest.mock import Mock
import pytest
from server.switch_worker import SwitchWorkflowWorker
from server.store import Store
from test_unified_superpowers import setup


def test_failed_switch_reply_reuses_completed_intake(setup):
    service, _, _, _ = setup
    client = Mock(agent_id='clerk', room_id='room', connected=True)
    client.post_message.side_effect = [ConnectionError('offline'), {'event_id':'reply'}]
    worker = SwitchWorkflowWorker(service, client, 'clerk',
        {'human': {'actor_type':'human', 'roles':['operator'], 'scopes':['*']}})
    event = {'type':'message','room_id':'room','sequence':42,
             'payload':{'addressed':True,'sender':'human',
                        'body':'!shipcourt open {"pr_url":"https://github.com/acme/shop/pull/18","services":["checkout-service"]}'}}
    with pytest.raises(ConnectionError):
        worker.handle(event)
    worker.handle(event)
    assert len(service.cases) == 1
    assert service.store.get('switch_result', 'clerk:42')['result']['case_id'] in service.cases


def test_scope_notification_waits_for_switch_and_retains_failure():
    service = Mock(store=Store())
    service.store.put('switch_notification','AG-1',{'case_id':'AG-1','status':'PENDING','content':'Case AG-1'})
    client = Mock(agent_id='clerk', connected=False)
    worker = SwitchWorkflowWorker(service,client,'clerk',{})
    worker.flush_notifications()
    client.post_message.assert_not_called()
    client.connected = True
    client.post_message.side_effect = ConnectionError('disconnected')
    worker.flush_notifications()
    assert service.store.get('switch_notification','AG-1')['status'] == 'FAILED_OR_UNKNOWN'
    client.post_message.side_effect = None
    client.post_message.return_value = {'event_id':'native-message'}
    worker.flush_notifications()
    assert service.store.get('switch_notification','AG-1')['status'] == 'DELIVERED'


def test_interrupted_review_can_resume_after_restart(setup):
    from server.models import CaseState
    from server.unified_pipeline import UnifiedBoardroomCourtPipeline
    service, p, _, path = setup
    case = service.open_case('https://github.com/acme/shop/pull/18',['checkout-service'],p)
    case.state = CaseState.EVIDENCE_COLLECTION
    service.store.put('case', case.case_id, case)
    restarted = UnifiedBoardroomCourtPipeline(authorization=service.authorization,db_path=path)
    assert restarted.cases[case.case_id].state == CaseState.CASE_OPENED
