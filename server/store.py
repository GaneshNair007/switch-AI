"""SQLite state and correlated audit events for the single-process service."""
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, is_dataclass


def encode(value):
    return asdict(value) if is_dataclass(value) else value


class Store:
    def __init__(self, path=':memory:'):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, data TEXT)')

    def put(self, kind, identifier, value):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO state VALUES (?,?,?)', (kind, identifier, json.dumps(value, default=encode)))

    def get(self, kind, identifier):
        with self.lock:
            row = self.db.execute('SELECT data FROM state WHERE kind=? AND id=?', (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def list(self, kind):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT data FROM state WHERE kind=? ORDER BY rowid', (kind,))]

    def event(self, event_type, correlation_id, actor_id, payload, source_platform='local', actor_type='service', room_id='ship-court'):
        event = dict(event_id=uuid.uuid4().hex, correlation_id=correlation_id, event_type=event_type,
                     timestamp=time.time(), actor_id=actor_id, actor_type=actor_type, source_platform=source_platform,
                     room_id=room_id, payload=payload, evidence_refs=[])
        with self.lock, self.db:
            self.db.execute('INSERT INTO audit VALUES (?,?)', (event['event_id'], json.dumps(event, default=encode)))
        return event

    def events(self):
        with self.lock:
            return [json.loads(row[0]) for row in self.db.execute('SELECT data FROM audit ORDER BY rowid')]
