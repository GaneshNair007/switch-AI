"""Discord signed interactions adapter. No unsigned identity or display-name trust."""
import json
import time
import threading
from .authorization import Principal
import secrets


class DiscordInteractions:
    def __init__(self, workflow, public_key, application_id, guild_id, members, clock=time.time):
        from nacl.signing import VerifyKey
        self.verify_key = VerifyKey(bytes.fromhex(public_key))
        self.workflow = workflow
        self.application_id, self.guild_id = application_id, guild_id
        self.members, self.clock = members, clock
        self.lock = threading.RLock()

    def handle(self, raw, signature, timestamp):
        from nacl.exceptions import BadSignatureError
        try:
            if abs(self.clock() - int(timestamp)) > 300:
                raise PermissionError('Expired Discord request')
            self.verify_key.verify(timestamp.encode() + raw, bytes.fromhex(signature))
        except (ValueError, TypeError, BadSignatureError) as exc:
            raise PermissionError('Invalid Discord signature') from exc
        event = json.loads(raw)
        if event.get('application_id') != self.application_id:
            raise PermissionError('Wrong Discord application')
        if event['type'] == 1:
            return {'type': 1}
        if event.get('guild_id') != self.guild_id:
            raise PermissionError('Wrong Discord server')
        user = event.get('member', {}).get('user', {})
        identity = self.members.get(user.get('id'))
        if not identity or user.get('bot'):
            raise PermissionError('Discord user not authorized')
        with self.lock:
            key = str(event['id'])
            previous = self.workflow.store.get('discord_interaction', key)
            if previous:
                return previous
            # Only reached after Ed25519 verification, guild check and exact ID mapping.
            auth = self.workflow.authorization
            with auth._lock:
                principal = Principal('discord:' + user['id'], frozenset(identity.get('roles', [])),
                                      frozenset(identity.get('scopes', [])), secrets.token_urlsafe(32), self.clock() + 300)
                auth._sessions[principal.session_id] = principal
            try:
                data = event['data']
                if event['type'] == 3:
                    action, target = data['custom_id'].split(':', 1)
                    args = {'request_id': target}
                else:
                    options = {o['name']: o.get('value') for o in data.get('options', [])}
                    action = options.get('action', 'status')
                    args = json.loads(options.get('arguments', '{}'))
                result = self.dispatch(action, args, principal)
                response = {'type': 4, 'data': {'content': json.dumps(result, default=str)[:1900],
                                               'flags': 64, 'allowed_mentions': {'parse': []}}}
                self.workflow.store.put('discord_interaction', key, response)
                return response
            finally:
                auth.revoke(principal)

    def dispatch(self, action, args, principal):
        service = self.workflow
        if action == 'grant':
            return service.floor_controller.grant_floor(args['request_id'], principal)
        if action in ('dismiss', 'interrupt'):
            service.floor_controller.dismiss(args['request_id'], principal, interrupt=action == 'interrupt')
            return {'status': action}
        if action == 'verdict':
            return {'release_brief': service.decide(args['case_id'], args['command'], principal)}
        service.authorization.require(principal, role='operator')
        if action == 'raise':
            from dataclasses import asdict
            if 'now' in args:
                raise ValueError('Client timestamps are not accepted')
            return asdict(service.floor_controller.raise_hand(**args))
        if action == 'status':
            return [{'case_id': c.case_id, 'state': c.state.value} for c in service.cases.values()]
        if action == 'tasks':
            return [t.description for c in service.cases.values() for t in c.tasks]
        raise ValueError('Supported actions: status, tasks, raise, grant, dismiss, interrupt, verdict')

    @staticmethod
    def floor_buttons(request_id):
        return [{'type': 1, 'components': [
            {'type': 2, 'style': 1, 'label': 'Grant Floor', 'custom_id': 'grant:' + request_id},
            {'type': 2, 'style': 2, 'label': 'Dismiss', 'custom_id': 'dismiss:' + request_id},
            {'type': 2, 'style': 4, 'label': 'Interrupt', 'custom_id': 'interrupt:' + request_id}]}]
