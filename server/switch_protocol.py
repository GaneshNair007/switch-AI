"""Official Switch SSE/HTTP client, checked against source 7bf37f8f82b4.

No local fallback: disconnects stop delivery. Register agents and room membership
out of band. Use a separate connection ID per running client.
"""
import json
import threading
import urllib.parse
import urllib.request
import uuid


class SwitchProtocolClient:
    def __init__(self, base_url, agent_id, api_key, room_id, store, opener=None):
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
            raise ValueError('Switch requires HTTPS except on localhost')
        if not agent_id or not api_key or not room_id:
            raise ValueError('Switch URL, agent ID, key and room ID are required')
        self.base_url, self.agent_id, self.api_key, self.room_id = base_url.rstrip('/'), agent_id, api_key, room_id
        self.store, self.opener = store, opener or urllib.request.urlopen
        state = store.get('switch_cursor', agent_id) or {}
        self.connection_id = state.get('connection_id', str(uuid.uuid4()))
        self.cursor = state.get('cursor', 'head')
        self.stop = threading.Event()
        self.stream = None
        self.connected = False
        self.generation = None

    def request(self, path, payload=None, accept='application/json'):
        headers = {'Authorization': 'Bearer ' + self.api_key, 'Accept': accept, 'Content-Type': 'application/json',
                   'X-Switch-Connection-Id': self.connection_id}
        req = urllib.request.Request(self.base_url + '/agents/' + urllib.parse.quote(self.agent_id, safe='') + path,
                                     data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        return self.opener(req, timeout=30)

    def post_message(self, content):
        with self.request('/message', {'room_id': self.room_id, 'content': content}) as response:
            result = json.load(response)
        self.store.event('switch.message_sent', self.room_id, self.agent_id, {'response': result}, source_platform='switch', actor_type='agent')
        return result

    def operations(self):
        with self.request('/ops') as response:
            return json.load(response)['operations']

    def operation(self, name, arguments):
        if name not in self.operations():
            raise ValueError('Operation is not supported by the connected Switch runtime')
        with self.request('/ops/' + urllib.parse.quote(name, safe=''), arguments) as response:
            return json.load(response)

    def _heartbeat(self):
        while not self.stop.wait(2):
            try:
                with self.request('/connection/beat', {'connection_id': self.connection_id, 'cursor': self.cursor if self.cursor != 'head' else 0, 'generation': self.generation}) as response:
                    json.load(response)
            except Exception:
                self.connected = False
                if self.stream:
                    self.stream.close()
                return

    def listen_once(self, handler):
        query = urllib.parse.urlencode({'connection_id': self.connection_id, 'scope': 'single', 'filter': 'all',
                                       'rooms': self.room_id, 'start_from': self.cursor})
        self.stop.clear()
        with self.request('/events?' + query, accept='text/event-stream') as stream:
            self.stream = stream
            beat = None
            data, event_name, sequence = [], '', None
            try:
                for raw in stream:
                    line = raw.decode('utf-8').rstrip('\r\n')
                    if line.startswith(':'):
                        continue
                    if line:
                        field, _, value = line.partition(':')
                        if field == 'data': data.append(value.lstrip())
                        elif field == 'event': event_name = value.strip()
                        elif field == 'id': sequence = int(value.strip())
                        continue
                    if not data:
                        continue
                    event = json.loads('\n'.join(data))
                    if event_name == 'connection_state':
                        self.connected = True
                        self.cursor = event.get('cursor', self.cursor)
                        self.generation = event.get('generation')
                        if beat is None:
                            beat = threading.Thread(target=self._heartbeat, daemon=True)
                            beat.start()
                    elif event_name in ('evicted', 'gap'):
                        raise RuntimeError('Switch stream requires resynchronization: ' + event_name)
                    elif sequence is not None:
                        event_key = self.agent_id + ':' + str(sequence)
                        if not self.store.get('switch_event', event_key):
                            handler(event)
                            self.store.put('switch_event', event_key, {'processed': True})
                        self.cursor = sequence
                    self.store.put('switch_cursor', self.agent_id, {'connection_id': self.connection_id, 'cursor': self.cursor})
                    data, event_name, sequence = [], '', None
                    if self.stop.is_set():
                        break
            finally:
                self.connected = False
                self.stop.set()
                if beat:
                    beat.join(timeout=3)
                self.stream = None

    def run(self, handler, max_reconnects=5):
        for attempt in range(max_reconnects + 1):
            try:
                self.listen_once(handler)
                raise ConnectionError("Switch event stream closed")
            except Exception as exc:
                self.store.event('switch.disconnected', self.room_id, self.agent_id, {'error_type': type(exc).__name__})
                if attempt == max_reconnects:
                    raise
                self.stop.clear()
                if self.stop.wait(min(2 ** attempt, 10)):
                    return
