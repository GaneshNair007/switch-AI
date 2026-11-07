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
            if action.startswith('hq:'):
                return workflow.workspace.action(action[3:],args,principal)
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

    class MissionModal(discord.ui.Modal, title='New mission'):
        kind=discord.ui.TextInput(label='Type: engineering_review or idea_studio',default='engineering_review',max_length=30)
        name=discord.ui.TextInput(label='Mission title',max_length=120)
        objective=discord.ui.TextInput(label='Objective / technical question',style=discord.TextStyle.paragraph,max_length=2000)
        pr=discord.ui.TextInput(label='Optional GitHub PR URL',required=False,max_length=250)
        services=discord.ui.TextInput(label='Affected services, comma separated (for PR)',required=False,max_length=250)
        async def on_submit(self,interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                args={'mission_type':str(self.kind),'title':str(self.name),'objective':str(self.objective),
                      'discord_channel_id':str(interaction.channel_id)}
                if str(self.pr):args.update(pr_url=str(self.pr),services=[s.strip() for s in str(self.services).split(',') if s.strip()])
                result=await execute(interaction.user,interaction.guild,'hq:create',args)
                await interaction.followup.send('Created '+result['mission_id']+'\nStart with `!court hq:start {"mission_id":"'+result['mission_id']+'"}`',ephemeral=True)
            except Exception as exc:await interaction.followup.send('Mission failed: '+type(exc).__name__,ephemeral=True)

    class MeetingModal(discord.ui.Modal, title='Start meeting'):
        mission=discord.ui.TextInput(label='Mission ID')
        async def on_submit(self,interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                result=await execute(interaction.user,interaction.guild,'hq:meeting',{'mission_id':str(self.mission)})
                await interaction.followup.send('Meeting linked: '+result['meeting_id']+'\nJoin Boardroom Live and use `!voice start '+result['mission_id']+'`.',ephemeral=True)
            except Exception as exc:await interaction.followup.send('Meeting failed: '+type(exc).__name__,ephemeral=True)

    class MissionControls(discord.ui.View):
        def __init__(self):super().__init__(timeout=None)
        @discord.ui.button(label='New Mission',style=discord.ButtonStyle.primary,custom_id='hq:new')
        async def create(self,interaction,button):await interaction.response.send_modal(MissionModal())
        @discord.ui.button(label='Start Meeting',style=discord.ButtonStyle.primary,custom_id='hq:meeting')
        async def meeting(self,interaction,button):await interaction.response.send_modal(MeetingModal())
        @discord.ui.button(label='Open Court',style=discord.ButtonStyle.secondary,custom_id='hq:court')
        async def court(self,interaction,button):await interaction.response.send_modal(MissionModal())
        async def inspect(self,interaction,key):
            await interaction.response.defer(ephemeral=True)
            try:
                state=await execute(interaction.user,interaction.guild,'hq:snapshot',{})
                content=json.dumps(state.get(key,[]),default=str,indent=2)
                if len(content)>1800:
                    import io
                    await interaction.followup.send(file=discord.File(io.BytesIO(content.encode()),filename=key+'.json'),ephemeral=True)
                else:await interaction.followup.send(content,ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
            except Exception as exc:await interaction.followup.send('Access failed: '+type(exc).__name__,ephemeral=True)
        @discord.ui.button(label='View Agents',style=discord.ButtonStyle.secondary,custom_id='hq:agents')
        async def agents(self,interaction,button):await self.inspect(interaction,'agents')
        @discord.ui.button(label='View Tasks',style=discord.ButtonStyle.secondary,custom_id='hq:tasks')
        async def tasks(self,interaction,button):await self.inspect(interaction,'tasks')
        @discord.ui.button(label='View Results',style=discord.ButtonStyle.secondary,custom_id='hq:results',row=1)
        async def results(self,interaction,button):await self.inspect(interaction,'results')

    async def panel_loop():
        await client.wait_until_ready()
        from .discord_setup import MAP_PATH
        while not client.is_closed():
            try:
                if MAP_PATH.exists():
                    mapping=json.loads(MAP_PATH.read_text());channel=client.get_channel(int(mapping['channels']['mission-control']))
                    if channel:
                        missions=workflow.store.list('mission');connected=sum(w.client.connected and t.is_alive() for w,t in getattr(workflow,'switch_workers',[]))
                        embed=discord.Embed(title='SHIP COURT · MISSION CONTROL',description='Engineering headquarters · Personal AI studio',color=0x6366F1)
                        for name,value in [('Missions',len(missions)),('Active cases',sum(c.state.value not in ('APPROVED','BLOCKED','CONDITIONAL','CASE_CLOSED') for c in workflow.cases.values())),('Connected Switch agents',connected),
                            ('Open tasks',sum(t['status']!='DONE' for m in missions for t in workflow.workspace.tasks(m))),
                            ('Awaiting human',sum(m['status']=='AWAITING_HUMAN' for m in missions)),
                            ('Confirmed GitHub results',sum(r['status']=='CONFIRMED' for r in workflow.store.list('github'))),
                            ('Pending floor requests',sum(r.state.value=='waiting' for r in workflow.floor_controller.requests.values())),
                            ('Scope reports',len(workflow.store.list('violation')))]:
                            embed.add_field(name=name,value=str(value))
                        embed.set_footer(text='Live backend state · Human authorization required for decisions')
                        saved=workflow.store.get('discord_panel','mission-control')
                        if saved and saved.get('channel_id')==str(channel.id):
                            try:message=await channel.fetch_message(int(saved['message_id']))
                            except discord.NotFound:message=await channel.send(embed=embed,view=MissionControls())
                            await message.edit(embed=embed,view=MissionControls())
                            workflow.store.put('discord_panel','mission-control',{'channel_id':str(channel.id),'message_id':str(message.id)})
                        else:
                            message=await channel.send(embed=embed,view=MissionControls())
                            workflow.store.put('discord_panel','mission-control',{'channel_id':str(channel.id),'message_id':str(message.id)})
            except Exception as exc:workflow.store.event('discord.panel_failed','workspace','gateway',{'error_type':type(exc).__name__})
            await asyncio.sleep(30)

    @client.event
    async def on_ready():
        if not getattr(client,'hq_panel_task',None):
            client.add_view(MissionControls());client.hq_panel_task=asyncio.create_task(panel_loop())

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
        if message.author.bot:
            return
        from .discord_setup import MAP_PATH
        mapping=json.loads(MAP_PATH.read_text())['channels'] if MAP_PATH.exists() else {}
        idea=str(getattr(getattr(message,'channel',None),'id',''))==mapping.get('idea-lab') and not message.content.startswith('!')
        if not idea and not message.content.startswith('!court '):return
        key = str(message.id)
        if workflow.store.get('discord_message', key):
            return
        from .store import encode
        raw = message.content[len('!court '):]
        action, _, argument = raw.partition(' ')
        try:
            if idea:
                result=await execute(message.author,message.guild,'hq:create',{'mission_type':'idea_studio',
                    'title':message.content[:120],'objective':message.content,'discord_channel_id':str(message.channel.id)})
                workflow.store.put('discord_message',key,{'status':'CREATED','mission_id':result['mission_id']})
                try:result=await execute(message.author,message.guild,'hq:start',{'mission_id':result['mission_id']})
                except ValueError:result['next_action']='Switch unavailable. Start this saved project when the clerk reconnects.'
            else:result = await execute(message.author, message.guild, action, json.loads(argument or '{}'))
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
