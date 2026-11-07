"""Meeting context, consent, decisions and task summaries backed by SQLite."""
import threading
import time
import uuid


class Meetings:
    MODES = ('Quiet Assistant', 'Professional Colleague', 'Debate Mode', 'Autonomous Facilitator')

    def __init__(self, authorization, store, floor):
        self.auth, self.store, self.floor = authorization, store, floor
        self.lock = threading.RLock()

    def start(self, title, principal, mode='Professional Colleague'):
        self.auth.require(principal, role='operator')
        if mode not in self.MODES or not title.strip():
            raise ValueError('Valid title and participation mode required')
        meeting = {'meeting_id': 'meeting-' + uuid.uuid4().hex, 'title': title, 'mode': mode, 'status': 'ACTIVE',
                   'created_at': time.time(), 'consenting_participants': [], 'transcripts': [], 'decisions': [], 'tasks': []}
        self.store.put('meeting', meeting['meeting_id'], meeting)
        return meeting

    def consent(self, meeting_id, principal, enabled):
        self.auth.require(principal, role='operator')
        with self.lock:
            meeting = self.get(meeting_id)
            members = set(meeting['consenting_participants'])
            if enabled: members.add(principal.subject)
            else: members.discard(principal.subject)
            meeting['consenting_participants'] = sorted(members)
            self.store.put('meeting', meeting_id, meeting)
            return meeting

    def get(self, meeting_id):
        meeting = self.store.get('meeting', meeting_id)
        if not meeting:
            raise KeyError('Meeting not found')
        return meeting

    def transcript(self, meeting_id, text, principal, event_id):
        self.auth.require(principal, role='operator')
        with self.lock:
            meeting = self.get(meeting_id)
            if meeting['status'] != 'ACTIVE' or principal.subject not in meeting['consenting_participants']:
                raise PermissionError('Active meeting and participant consent required')
            if not any(item['event_id'] == event_id for item in meeting['transcripts']):
                meeting['transcripts'].append({'event_id': event_id, 'speaker': principal.subject,
                                               'timestamp': time.time(), 'text': text, 'source': 'authenticated_text'})
                self.store.put('meeting', meeting_id, meeting)
            return meeting

    def decision(self, meeting_id, text, principal, evidence_refs=None):
        self.auth.require(principal, scope=f'meeting:{meeting_id}:decision')
        with self.lock:
            meeting = self.get(meeting_id)
            if meeting['status'] != 'ACTIVE':
                raise ValueError('Meeting has ended')
            known = {item['event_id'] for item in meeting['transcripts']}
            if not set(evidence_refs or []).issubset(known):
                raise ValueError('Evidence references must identify existing meeting entries')
            decision = {'id': 'DEC-' + uuid.uuid4().hex, 'text': text, 'actor': principal.subject,
                        'evidence_refs': evidence_refs or [], 'timestamp': time.time()}
            meeting['decisions'].append(decision)
            self.store.put('meeting', meeting_id, meeting)
            self.store.event('meeting.decision', meeting_id, principal.subject, decision, actor_type='human')
            return decision

    def assign_task(self, meeting_id, description, owner_id, principal, evidence_refs=None):
        self.auth.require(principal, scope=f'meeting:{meeting_id}:decision')
        if not description.strip() or not owner_id:
            raise ValueError('Task description and owner identity required')
        with self.lock:
            meeting = self.get(meeting_id)
            known = {d['id'] for d in meeting['decisions']}
            if not set(evidence_refs or []).issubset(known):
                raise ValueError('Task references must identify approved decisions')
            task = {'id':'TASK-' + uuid.uuid4().hex, 'description':description, 'owner_id':owner_id,
                    'status':'OPEN', 'approved_by':principal.subject, 'evidence_refs':evidence_refs or []}
            meeting['tasks'].append(task)
            self.store.put('meeting', meeting_id, meeting)
            self.store.event('meeting.task_assigned', meeting_id, principal.subject, task, actor_type='human')
            return task

    def update_task(self, meeting_id, task_id, status, principal):
        self.auth.require(principal, role='operator')
        if status not in ('OPEN', 'IN_PROGRESS', 'BLOCKED', 'DONE'):
            raise ValueError('Invalid task status')
        with self.lock:
            meeting = self.get(meeting_id)
            task = next(t for t in meeting['tasks'] if t['id'] == task_id)
            if task['owner_id'] != principal.subject:
                self.auth.require(principal, scope=f'meeting:{meeting_id}:decision')
            task['status'] = status
            self.store.put('meeting', meeting_id, meeting)
            self.store.event('meeting.task_updated', meeting_id, principal.subject, task)
            return task

    def end(self, meeting_id, principal):
        self.auth.require(principal, scope=f'meeting:{meeting_id}:floor')
        with self.lock:
            meeting = self.get(meeting_id)
            if meeting.get('recap'):return meeting['recap']
            meeting['status'] = 'ENDED'
            for req in list(self.floor.requests.values()):
                if req.meeting_id == meeting_id:
                    self.floor.dismiss(req.request_id, principal, interrupt=True)
            recap={'meeting_id': meeting_id, 'mission_id':meeting.get('mission_id'), 'title': meeting['title'], 'decisions': meeting['decisions'],
                    'tasks': meeting['tasks'], 'transcript_entries': len(meeting['transcripts']),
                    'discussion_points':[{'text':t['text'],'source':t['event_id']} for t in meeting['transcripts'][-12:]],
                    'verified_findings':[], 'proposed_ideas':[], 'open_questions':[],
                    'summary_provenance': 'structured records; no unverified generated claims'}
            meeting['recap']=recap;self.store.put('meeting', meeting_id, meeting)
            import json
            key=meeting_id+':recap'
            self.store.put('discord_outbox',key,{'id':key,'channel':'meeting-recaps','correlation_id':meeting.get('mission_id') or meeting_id,
                'content':json.dumps(recap,ensure_ascii=False),'status':'PENDING','attempts':0,'attachment_name':meeting_id+'-recap.json'})
            self.store.event('meeting.ended',meeting_id,principal.subject,{'recap_id':key},actor_type='human')
            return recap
