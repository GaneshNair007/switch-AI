"""Five independent Groq roles whose handoffs travel through real Switch SSE."""
import json
import threading
import uuid
from .groq_agents import CHAIN, ROLES


class SwitchGroqWorker:
    def __init__(self, workflow, client, role, participants, peers, runtime):
        self.workflow, self.client, self.role = workflow, client, role
        self.participants, self.peers, self.runtime = participants, peers, runtime
        self.lock = threading.RLock()

    def handle(self, event):
        try:
            return self._handle(event)
        except (ValueError, KeyError, PermissionError, RuntimeError) as exc:
            self.workflow.store.event('switch.agent_failed', str(event.get('sequence')), self.client.agent_id,
                {'role':self.role,'error_type':type(exc).__name__}, source_platform='switch', room_id=self.client.room_id)
            self.client.post_message(f'{ROLES[self.role][0]} could not complete this request ({type(exc).__name__}). No approval or external operation was performed.')

    def _handle(self, event):
        if event.get('type') != 'message' or event.get('room_id') != self.client.room_id:
            return
        payload = event.get('payload', {})
        if not payload.get('addressed'):
            return
        body, sender = payload.get('body', ''), payload.get('sender')
        if not isinstance(body, str):
            return
        with self.lock:
            if '!shipcourt-agent ' in body:
                command = json.loads(body.split('!shipcourt-agent ', 1)[1])
                return self.step(command['job_id'], sender)
            if self.role != 'clerk':
                return
            identity = self.participants.get(sender, {})
            if identity.get('actor_type') != 'human' or 'operator' not in identity.get('roles', []):
                return
            if '!shipcourt discuss ' not in body:
                return
            task = body.split('!shipcourt discuss ', 1)[1].strip()
            if not task or len(task) > 4000:
                raise ValueError('Discuss needs a task of 1–4000 characters')
            key = self.client.agent_id + ':' + str(event['sequence'])
            job = self.workflow.store.get('native_intake', key)
            if not job:
                job = {'job_id':'NATIVE-' + uuid.uuid4().hex, 'room_id':self.client.room_id,
                       'task':task, 'human_sender':sender, 'results':{}, 'status':'IN_PROGRESS'}
                self.workflow.store.put('native_job', job['job_id'], job)
                self.workflow.store.put('native_intake', key, job)
                self.workflow.store.event('switch.human_task', job['job_id'], sender, {'task':task},
                    source_platform='switch', actor_type='human', room_id=self.client.room_id)
            self.send_step(job, 'historian')

    def send_step(self, job, role):
        marker = f"{job['job_id']}:{role}"
        if self.workflow.store.get('native_sent', marker):
            return
        text = self.peers[role]['mention'] + ' !shipcourt-agent ' + json.dumps({'job_id':job['job_id']})
        receipt = self.client.post_message(text)
        self.workflow.store.put('native_sent', marker, {'receipt':receipt})
        self.workflow.store.event('switch.agent_handoff', job['job_id'], self.client.agent_id,
            {'to_role':role,'receipt':receipt}, source_platform='switch', actor_type='agent', room_id=self.client.room_id)

    def step(self, job_id, sender):
        job = self.workflow.store.get('native_job', job_id)
        if not job or job['room_id'] != self.client.room_id:
            return
        index = CHAIN.index(self.role)
        expected = 'clerk' if index == 0 else CHAIN[index-1]
        if sender != self.peers[expected]['sender_id']:
            return
        if any(role not in job['results'] for role in CHAIN[:index]):
            return
        if self.role not in job['results']:
            evidence = self.evidence(job)
            context_key = self.client.agent_id + ':' + self.client.room_id
            history = self.workflow.store.get('groq_context', context_key) or []
            result = self.runtime.respond(self.role, evidence, history)
            job['results'][self.role] = result
            self.workflow.store.put('groq_context', context_key, (history + [{'job_id':job_id,'answer':result}])[-8:])
            self.workflow.store.put('native_job', job_id, job)
            self.workflow.store.event('switch.agent_reasoned', job_id, self.client.agent_id,
                {'role':self.role,'runtime':'groq_custom','advisory':result},
                source_platform='switch', actor_type='agent', room_id=self.client.room_id)
        # Publish saved output before delegating; reconnect retries never invoke the model twice.
        output_key = job_id + ':' + self.role
        if not self.workflow.store.get('native_output', output_key):
            receipt = self.client.post_message(f"[{job_id}] {ROLES[self.role][0]}\n" + job['results'][self.role])
            self.workflow.store.put('native_output', output_key, {'receipt':receipt})
        if index + 1 < len(CHAIN):
            self.send_step(job, CHAIN[index+1])
        elif job['status'] != 'AWAITING_HUMAN':
            job['status'] = 'AWAITING_HUMAN'
            self.workflow.store.put('native_job', job_id, job)
            self.workflow.store.event('switch.human_decision_requested', job_id, self.client.agent_id,
                {'binding_authorization':False,'roles_completed':list(CHAIN)},
                source_platform='switch', actor_type='agent', room_id=self.client.room_id)

    def evidence(self, job):
        store = self.workflow.store
        evidence = {'human_proposal_unverified':job['task'],
                    'previous_specialists':{k:v[:900] for k,v in job['results'].items()}}
        if self.role == 'historian':
            evidence['prior_human_decisions'] = [e for e in store.events() if e['event_type'] in
                ('court.human_verdict','meeting.decision')][-3:]
        if self.role == 'prosecutor':
            evidence['risk_model_provenance'] = 'No measured test or deployment logs supplied; request evidence before release.'
        if self.role == 'defender':
            evidence['test_evidence'] = 'No test logs supplied for this proposal; suggestions are not completed checks.'
        if self.role == 'third_voice':
            evidence['meeting_decisions'] = [m.get('decisions', [])[-2:] for m in store.list('meeting')[-2:]]
            evidence['floor_policy'] = 'Textual advisory only; voice requires a separate scoped human grant.'
        return evidence
