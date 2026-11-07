import json
import time
from nacl.signing import SigningKey
import pytest
from server.discord_interactions import DiscordInteractions
from server.unified_pipeline import UnifiedBoardroomCourtPipeline
from server.authorization import AuthorizationService


def test_discord_signature_identity_replay_and_floor(tmp_path):
    key = SigningKey.generate()
    workflow = UnifiedBoardroomCourtPipeline(authorization=AuthorizationService([]), db_path=tmp_path/'state.sqlite3')
    adapter = DiscordInteractions(workflow, key.verify_key.encode().hex(), 'app', 'guild',
                                  {'123': {'roles': ['operator', 'approver'], 'scopes': ['meeting:m1:floor']}})
    req = workflow.floor_controller.raise_hand('m1', 'ai', 'hand', 'risk', 'evidence')
    event = {'id': 'evt1', 'application_id': 'app', 'guild_id': 'guild', 'type': 3,
             'member': {'user': {'id': '123', 'username': 'any-display-name'}},
             'data': {'custom_id': 'grant:' + req.request_id}}
    def invoke(payload, timestamp=None, bad=False):
        raw = json.dumps(payload).encode()
        ts = timestamp or str(int(time.time()))
        signature = key.sign(ts.encode() + raw).signature.hex()
        return adapter.handle(raw, '00'*64 if bad else signature, ts)
    with pytest.raises(PermissionError): invoke(event, bad=True)
    with pytest.raises(PermissionError): invoke(event, timestamp='1')
    with pytest.raises(PermissionError): invoke({**event, 'member': {'user': {'id': '456', 'username': 'admin'}}})
    with pytest.raises(PermissionError): invoke({**event, 'member': {'user': {'id': '123', 'bot': True}}})
    first = invoke(event)
    assert json.loads(first['data']['content'])['granted'] is True
    assert invoke(event) == first
    assert len([e for e in workflow.floor_controller.events() if e['state']=='granted']) == 1
    assert workflow.floor_controller.requests[req.request_id].state.value == 'granted'


def test_webhook_failure_is_visible():
    from server.bridge_connector import ChatBridgeConnector
    from server.switch_room import SwitchRoom
    bridge = ChatBridgeConnector(SwitchRoom(), 'https://discord.com/api/webhooks/test', platform='discord', transport=lambda _: (400,b'bad'))
    assert 'text' not in bridge.build_outgoing_payload('hello')
    assert bridge.forward_to_chat('hello') is False
    assert bridge.delivery_results[-1] == {'status':'FAILED','http_status':400,'retryable':False,'attempts':1}
