import io
import json
from server.store import Store
from server.switch_protocol import SwitchProtocolClient


def test_sse_delivery_cursor_dedup_and_real_http_contract():
    store = Store()
    calls = []
    frames = ('event: connection_state\ndata: {"cursor":0,"rooms":["room"]}\n\n'
              'id: 1\nevent: message\ndata: {"type":"message","room_id":"room","sequence":1,"payload":{"addressed":true,"sender":"opaque-user","body":"hello"}}\n\n')
    def opener(req, timeout):
        calls.append(req)
        if '/events?' in req.full_url:
            return io.BytesIO(frames.encode())
        return io.BytesIO(b'{"event_id":"sent-1"}')
    client = SwitchProtocolClient('https://switch.example.test', 'agent', 'secret', 'room', store, opener)
    handled = []
    client.listen_once(handled.append)
    assert len(handled) == 1
    assert client.cursor == 1
    client.listen_once(handled.append)
    assert len(handled) == 1
    result = client.post_message('handoff')
    assert result['event_id'] == 'sent-1'
    assert calls[-1].full_url.endswith('/agents/agent/message')
    assert json.loads(calls[-1].data) == {'room_id':'room','content':'handoff'}
    assert calls[-1].get_header('Authorization') == 'Bearer secret'
    assert 'start_from=1' in calls[-2].full_url
    assert client.connected is False
