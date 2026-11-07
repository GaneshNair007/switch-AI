"""Permission-controlled, per-meeting floor ownership with durable transitions."""
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import math
import sqlite3
import threading
import time
import uuid


class FloorState(str, Enum):
    LISTENING = 'listening'
    EVALUATING = 'evaluating'
    HAND_RAISED = 'hand_raised'
    WAITING = 'waiting'
    GRANTED = 'granted'
    SPEAKING = 'speaking'
    YIELDING = 'yielding'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    DISMISSED = 'dismissed'
    INTERRUPTED = 'interrupted'


@dataclass
class FloorRequest:
    request_id: str
    meeting_id: str
    agent_id: str
    intent: str
    emoji: str
    reason: str
    spoken_script: str
    priority: int
    evidence_refs: list = field(default_factory=list)
    created_at: float = 0
    expires_at: float = 0
    state: FloorState = FloorState.LISTENING


class FloorRequestController:
    def __init__(self, room, bridge=None, default_ttl_seconds=90, db_path=':memory:', cooldown_seconds=5, clock=time.time):
        if not math.isfinite(default_ttl_seconds) or default_ttl_seconds <= 0:
            raise ValueError('TTL must be positive and finite')
        self.room, self.bridge = room, bridge
        self.default_ttl_seconds = default_ttl_seconds
        self.cooldown_seconds, self.clock = cooldown_seconds, clock
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.execute('CREATE TABLE IF NOT EXISTS floor_requests (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self._db.execute('CREATE TABLE IF NOT EXISTS floor_events (id INTEGER PRIMARY KEY, request_id TEXT, state TEXT, actor TEXT, timestamp REAL)')
        self.requests = {}
        self.active_speakers = {}
        self._cooldowns = {}
        for _, data in self._db.execute('SELECT id,data FROM floor_requests'):
            record = json.loads(data)
            record['state'] = FloorState(record['state'])
            req = FloorRequest(**record)
            self.requests[req.request_id] = req
        for request_id, timestamp in self._db.execute("SELECT request_id, MAX(timestamp) FROM floor_events WHERE state IN ('yielding','interrupted','dismissed') GROUP BY request_id"):
            req = self.requests[request_id]
            self._cooldowns[(req.meeting_id, req.agent_id)] = timestamp + self.cooldown_seconds
        # Playback cannot survive process restart; require a new human grant.
        for req in self.requests.values():
            if req.state in (FloorState.GRANTED, FloorState.SPEAKING, FloorState.YIELDING):
                self._transition(req, FloorState.INTERRUPTED, 'restart', self.clock())
        self.room.register_session('shipcourt-third-voice', 'third-voice', 'local-floor-controller', 'configured')

    @property
    def active_speaker_request_id(self):
        return next(iter(self.active_speakers.values()), None)

    def _transition(self, req, state, actor, now):
        req.state = state
        with self._db:
            self._db.execute('INSERT OR REPLACE INTO floor_requests VALUES (?,?)', (req.request_id, json.dumps(asdict(req))))
            self._db.execute('INSERT INTO floor_events(request_id,state,actor,timestamp) VALUES (?,?,?,?)',
                             (req.request_id, state.value, actor, now))

    def events(self):
        with self._lock:
            return [dict(zip(('request_id', 'state', 'actor', 'timestamp'), row)) for row in
                    self._db.execute('SELECT request_id,state,actor,timestamp FROM floor_events ORDER BY id')]

    def _expire(self, now):
        for req in self.requests.values():
            if req.state in (FloorState.WAITING, FloorState.GRANTED) and now >= req.expires_at:
                self._transition(req, FloorState.EXPIRED, 'clock', now)
                if self.active_speakers.get(req.meeting_id) == req.request_id:
                    self.active_speakers.pop(req.meeting_id)

    def raise_hand(self, meeting_id, agent_id, emoji, reason, spoken_script, priority=80, evidence_refs=None, now=None):
        ts = self.clock() if now is None else now
        if not meeting_id or not agent_id or not reason or not spoken_script:
            raise ValueError('Meeting, agent, reason and script are required')
        if not isinstance(priority, int) or not 0 <= priority <= 100:
            raise ValueError('Priority must be an integer from 0 to 100')
        with self._lock:
            self._expire(ts)
            for req in self.requests.values():
                if (req.meeting_id == meeting_id and req.agent_id == agent_id and req.reason == reason
                        and req.state in (FloorState.WAITING, FloorState.GRANTED, FloorState.SPEAKING)):
                    return req
            if ts < self._cooldowns.get((meeting_id, agent_id), 0):
                raise ValueError('Agent cooldown active')
            req = FloorRequest('floor-' + uuid.uuid4().hex, meeting_id, agent_id, 'contribution', emoji,
                               reason, spoken_script, priority, list(evidence_refs or []), ts, ts + self.default_ttl_seconds)
            self.requests[req.request_id] = req
            for state in (FloorState.LISTENING, FloorState.EVALUATING, FloorState.HAND_RAISED, FloorState.WAITING):
                self._transition(req, state, agent_id, ts)
        message = f'{emoji} [{agent_id} requests floor] {reason} ({req.request_id})'
        self.room.post_message('third-voice', message, sender_role='third-voice')
        if self.bridge:
            self.bridge.forward_to_chat(message)
        return req

    def grant_floor(self, request_id, human_actor, now=None):
        ts = self.clock() if now is None else now
        with self._lock:
            req = self.requests[request_id]
            principal = self.room.authorization.require(human_actor, scope=f'meeting:{req.meeting_id}:floor')
            self._expire(ts)
            if req.state in (FloorState.GRANTED, FloorState.SPEAKING):
                return {'granted': False, 'reason': 'already_processed_idempotent', 'state': req.state.value}
            if req.state != FloorState.WAITING:
                return {'granted': False, 'reason': 'request_' + req.state.value, 'state': req.state.value}
            if req.meeting_id in self.active_speakers:
                return {'granted': False, 'reason': 'floor_busy', 'state': req.state.value}
            waiting = sorted((r for r in self.requests.values() if r.meeting_id == req.meeting_id and r.state == FloorState.WAITING),
                             key=lambda r: (-r.priority, r.created_at, r.request_id))
            if waiting[0].request_id != request_id:
                return {'granted': False, 'reason': 'higher_priority_pending', 'state': req.state.value}
            self.active_speakers[req.meeting_id] = request_id
            self._transition(req, FloorState.GRANTED, principal.subject, ts)
            return {'granted': True, 'request_id': request_id, 'state': req.state.value}

    def start_speaking(self, request_id):
        with self._lock:
            self._expire(self.clock())
            req = self.requests[request_id]
            if self.active_speakers.get(req.meeting_id) != request_id or req.state != FloorState.GRANTED:
                raise ValueError('A current human floor grant is required')
            self._transition(req, FloorState.SPEAKING, req.agent_id, self.clock())
            return req.spoken_script

    def release(self, request_id):
        with self._lock:
            req = self.requests[request_id]
            if req.state == FloorState.LISTENING:
                return
            if self.active_speakers.get(req.meeting_id) != request_id:
                raise ValueError('Request does not own the floor')
            ts = self.clock()
            self._transition(req, FloorState.YIELDING, req.agent_id, ts)
            self.active_speakers.pop(req.meeting_id)
            self._cooldowns[(req.meeting_id, req.agent_id)] = ts + self.cooldown_seconds
            self._transition(req, FloorState.LISTENING, req.agent_id, ts)

    def dismiss(self, request_id, principal, interrupt=False):
        with self._lock:
            req = self.requests[request_id]
            actor = self.room.authorization.require(principal, scope=f'meeting:{req.meeting_id}:floor')
            if req.state not in (FloorState.WAITING, FloorState.GRANTED, FloorState.SPEAKING):
                return
            state = FloorState.INTERRUPTED if interrupt else FloorState.DISMISSED
            self._transition(req, state, actor.subject, self.clock())
            if self.active_speakers.get(req.meeting_id) == request_id:
                self.active_speakers.pop(req.meeting_id)
            self._cooldowns[(req.meeting_id, req.agent_id)] = self.clock() + self.cooldown_seconds

    def cancel(self, request_id, principal):
        with self._lock:
            req = self.requests[request_id]
            actor = self.room.authorization.require(principal, scope=f'meeting:{req.meeting_id}:floor')
            if req.state in (FloorState.WAITING, FloorState.GRANTED, FloorState.SPEAKING):
                self._transition(req, FloorState.CANCELLED, actor.subject, self.clock())
                if self.active_speakers.get(req.meeting_id) == request_id:
                    self.active_speakers.pop(req.meeting_id)

    def close(self):
        self._db.close()
