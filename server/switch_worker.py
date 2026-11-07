"""Two Switch-managed clients sharing the workflow service.

Run with server.main --serve and SWITCH_CLIENTS JSON. Each client gets its own
registered agent key. Human identity mappings use exact Switch participant IDs.
"""
import json
import secrets
import threading
import time
from .authorization import Principal
from .switch_protocol import SwitchProtocolClient


class SwitchWorkflowWorker:
    def __init__(self, workflow, client, role, participants, reviewer_mention=None):
        if role not in ('clerk', 'reviewer'):
            raise ValueError('Worker role must be clerk or reviewer')
        self.workflow, self.client, self.role = workflow, client, role
        self.participants, self.reviewer_mention = participants, reviewer_mention

    def handle(self, event):
        if event.get('type') != 'message' or event.get('room_id') != self.client.room_id:
            return
        payload = event.get('payload', {})
        if not payload.get('addressed'):
            return
        sender = payload.get('sender')
        identity = self.participants.get(sender)
        if not identity:
            return
        content = payload.get('body', '')
        if isinstance(content, dict):
            content = content.get('body', '')
        if '!shipcourt ' not in content:
            return
        raw = content.split('!shipcourt ', 1)[1]
        action, _, arguments = raw.partition(' ')
        args = json.loads(arguments or '{}')
        roles = set(identity.get('roles', []))
        if identity.get('actor_type') != 'human':
            roles.discard('approver')
        if self.role == 'reviewer' and action != 'review':
            return
        if self.role == 'clerk' and action == 'review':
            return
        event_key = self.client.agent_id + ':' + str(event.get('sequence'))
        cached = self.workflow.store.get('switch_result', event_key)
        if cached:
            self.deliver_result(event_key, cached)
            return
        auth = self.workflow.authorization
        principal = Principal('switch:' + sender, frozenset(roles), frozenset(identity.get('scopes', [])),
                              secrets.token_urlsafe(32), time.time() + 300)
        with auth._lock:
            auth._sessions[principal.session_id] = principal
        try:
            if action == 'open':
                case = self.workflow.open_case(args['pr_url'], args['services'], principal)
                result = {'case_id': case.case_id, 'state': case.state.value}
            elif action == 'review':
                result = self.workflow.review(args['case_id'], principal)
            elif action == 'verdict':
                result = {'release_brief': self.workflow.decide(args['case_id'], args['command'], principal)}
            elif action == 'github-plan':
                import hashlib
                plan = self.workflow.github_plan(args['case_id'], principal)
                result = {'plan': plan, 'plan_hash': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()}
            elif action == 'github-execute':
                result = self.workflow.execute_github(args['case_id'], principal, args['plan_hash'])
            else:
                raise ValueError('Unsupported Ship Court command')
            cached = {'result': result, 'action': action, 'handoff_sent': False}
            self.workflow.store.put('switch_result', event_key, cached)
            self.deliver_result(event_key, cached)
            self.workflow.store.event('switch.workflow_completed', args.get('case_id', result.get('case_id', 'intake')), principal.subject,
                                      {'action': action, 'sequence': event.get('sequence')}, source_platform='switch')
        finally:
            auth.revoke(principal)

    def deliver_result(self, event_key, cached):
        result = cached['result']
        if cached['action'] == 'open' and self.reviewer_mention and not cached['handoff_sent']:
            self.client.post_message(self.reviewer_mention + ' !shipcourt review ' + json.dumps({'case_id': result['case_id']}))
            cached['handoff_sent'] = True
            self.workflow.store.put('switch_result', event_key, cached)
        self.client.post_message(json.dumps(result, default=str))

    def flush_notifications(self):
        if self.role != 'clerk' or not self.client.connected:
            return
        for item in self.workflow.store.list('switch_notification'):
            if item['status'] == 'DELIVERED' or item.get('attempts', 0) >= 5:
                continue
            item['attempts'] = item.get('attempts', 0) + 1
            try:
                item['receipt'] = self.client.post_message(item['content'])
                item['status'] = 'DELIVERED'
            except Exception as exc:
                item['status'] = 'FAILED_OR_UNKNOWN'
                item['error_type'] = type(exc).__name__
            self.workflow.store.put('switch_notification', item['case_id'], item)
            self.workflow.store.event('switch.scope_notification', item['case_id'], self.client.agent_id,
                                      {'status': item['status'], 'attempt': item['attempts']}, source_platform='switch')

    def notification_loop(self, receiver_thread):
        while receiver_thread.is_alive():
            self.flush_notifications()
            time.sleep(2)


def start_workers(workflow, configurations, participants):
    from .groq_agents import GroqBudget, GroqCustomRuntime
    from .switch_groq_worker import SwitchGroqWorker
    runtime = GroqCustomRuntime(workflow.debate_engine, GroqBudget())
    peers = {c['role']:c for c in configurations if c.get('runtime') == 'groq_custom'}
    workers = []
    for config in configurations:
        import os
        client = SwitchProtocolClient(config['url'], config['agent_id'], os.environ[config['key_env']],
                                      config['room_id'], workflow.store)
        if config.get('runtime') == 'groq_custom':
            worker = SwitchGroqWorker(workflow, client, config['role'], participants, peers, runtime)
        else:
            worker = SwitchWorkflowWorker(workflow, client, config['role'], participants, config.get('reviewer_mention'))
        thread = threading.Thread(target=client.run, args=(worker.handle,), daemon=True)
        thread.start()
        workers.append((worker, thread))
    workflow.switch_workers = workers
    from .notifications import Notifications
    from .discord_setup import DiscordREST
    workflow.notifications = Notifications(workflow, DiscordREST() if __import__('os').getenv('DISCORD_BOT_TOKEN') else None)
    threading.Thread(target=workflow.notifications.run, daemon=True).start()
    return workers
