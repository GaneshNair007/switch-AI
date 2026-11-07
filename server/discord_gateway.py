"""Optional discord.py gateway for bidirectional text and deferred commands.

Gateway events are authenticated by Discord. Exact guild/user IDs are mapped
server-side; bot authors cannot issue commands. Run in the HTTP service process.
"""
import asyncio
import json
import secrets
import threading
import time
from .authorization import Principal


def start_discord_gateway(workflow, token, guild_id, members):
    import discord
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    async def execute(user, guild, action, args):
        if guild is None or str(guild.id) != str(guild_id) or user.bot:
            raise PermissionError('Human member of configured server required')
        identity = members.get(str(user.id))
        if not identity:
            raise PermissionError('User ID is not provisioned')
        principal = Principal('discord:' + str(user.id), frozenset(identity.get('roles', [])),
                              frozenset(identity.get('scopes', [])), secrets.token_urlsafe(32), time.time() + 300)
        auth = workflow.authorization
        with auth._lock:
            auth._sessions[principal.session_id] = principal
        def operation():
            if action == 'open': return workflow.open_case(args['pr_url'], args['services'], principal)
            if action == 'review': return workflow.review(args['case_id'], principal)
            if action == 'attach': return workflow.attach_pull_request(args['case_id'], args['pr_url'], args['services'], principal)
            if action == 'verdict': return {'release_brief': workflow.decide(args['case_id'], args['command'], principal)}
            if action == 'github-plan':
                import hashlib
                plan = workflow.github_plan(args['case_id'], principal)
                return {'plan': plan, 'plan_hash': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()}
            if action == 'github-execute': return workflow.execute_github(args['case_id'], principal, args['plan_hash'])
            if action == 'grant': return workflow.floor_controller.grant_floor(args['request_id'], principal)
            if action == 'text':
                result = workflow.floor_controller.grant_floor(args['request_id'], principal)
                if not result['granted']:
                    raise ValueError(result['reason'])
                script = workflow.floor_controller.start_speaking(args['request_id'])
                workflow.floor_controller.release(args['request_id'])
                return {'contribution': script}
            if action in ('dismiss', 'interrupt'):
                workflow.floor_controller.dismiss(args['request_id'], principal, interrupt=action=='interrupt')
                return {'status': action}
            if action == 'meeting-start': return workflow.meetings.start(args['title'], principal)
            if action == 'meeting-end': return workflow.meetings.end(args['meeting_id'], principal)
            if action == 'consent': return workflow.meetings.consent(args['meeting_id'], principal, args['enabled'] is True)
            if action == 'transcript': return workflow.meetings.transcript(args['meeting_id'], args['text'], principal, args['event_id'])
            if action == 'decision': return workflow.meetings.decision(args['meeting_id'], args['text'], principal, args.get('evidence_refs'))
            auth.require(principal, role='operator')
            if action == 'raise':
                if 'now' in args: raise ValueError('Client timestamps are not accepted')
                return workflow.floor_controller.raise_hand(**args)
            if action == 'status': return [{'case_id': c.case_id, 'state': c.state.value} for c in workflow.cases.values()]
            if action == 'tasks': return [t for c in workflow.cases.values() for t in c.tasks]
            raise ValueError('Unknown command')
        try:
            return await asyncio.to_thread(operation)
        finally:
            auth.revoke(principal)

    class FloorControls(discord.ui.View):
        def __init__(self, request_id):
            super().__init__(timeout=90)
            self.request_id = request_id

        async def act(self, interaction, action):
            await interaction.response.defer(ephemeral=action != 'text')
            try:
                result = await execute(interaction.user, interaction.guild, action, {'request_id': self.request_id})
                await interaction.followup.send(json.dumps(result), ephemeral=action != 'text', allowed_mentions=discord.AllowedMentions.none())
            except Exception as exc:
                await interaction.followup.send('Floor action failed: ' + type(exc).__name__, ephemeral=True)

        @discord.ui.button(label='Grant Floor', style=discord.ButtonStyle.primary)
        async def grant(self, interaction, button):
            await self.act(interaction, 'grant')

        @discord.ui.button(label='Text Instead', style=discord.ButtonStyle.secondary)
        async def text(self, interaction, button):
            await self.act(interaction, 'text')

        @discord.ui.button(label='Dismiss', style=discord.ButtonStyle.danger)
        async def dismiss(self, interaction, button):
            await self.act(interaction, 'dismiss')

    @client.event
    async def on_message(message):
        if message.author.bot or not message.content.startswith('!court '):
            return
        key = str(message.id)
        if workflow.store.get('discord_message', key):
            return
        from .store import encode
        raw = message.content[len('!court '):]
        action, _, argument = raw.partition(' ')
        try:
            result = await execute(message.author, message.guild, action, json.loads(argument or '{}'))
            text = json.dumps(result, default=encode, indent=2)
            # Attach long evidence as a file; never truncate the only artifact.
            if len(text) > 1800:
                import io
                await message.reply('Courtroom result attached.', file=discord.File(io.BytesIO(text.encode()), filename='courtroom-result.json'), allowed_mentions=discord.AllowedMentions.none())
            else:
                await message.reply(text, view=FloorControls(result.request_id) if action == 'raise' else None, allowed_mentions=discord.AllowedMentions.none())
            workflow.store.put('discord_message', key, {'status': 'COMPLETED'})
        except Exception as exc:
            await message.reply('Command failed: ' + type(exc).__name__, allowed_mentions=discord.AllowedMentions.none())
            workflow.store.event('discord.command_failed', key, str(message.author.id), {'error_type': type(exc).__name__})

    thread = threading.Thread(target=lambda: client.run(token, log_handler=None), daemon=True)
    thread.start()
    return client, thread
