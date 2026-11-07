"""Exercise real discord.py controls with an authenticated-event fixture, no login."""
import asyncio
from types import SimpleNamespace
import discord
from server.authorization import AuthorizationService
from server.unified_pipeline import UnifiedBoardroomCourtPipeline
from server.discord_gateway import start_discord_gateway


def test_gateway_floor_buttons_enforce_identity(monkeypatch,tmp_path):
    monkeypatch.setattr(discord.Client,'run',lambda *args,**kwargs:None)
    workflow=UnifiedBoardroomCourtPipeline(authorization=AuthorizationService([]),db_path=tmp_path/'gateway.sqlite3')
    client,thread=start_discord_gateway(workflow,'unused-test-token','guild',{'human':{'roles':['operator','approver'],'scopes':['*']}})
    sent=[]
    async def reply(content,**kwargs):sent.append((content,kwargs))
    message=SimpleNamespace(id='message-1',author=SimpleNamespace(id='human',bot=False),guild=SimpleNamespace(id='guild'),
        content='!court raise {"meeting_id":"m1","agent_id":"reviewer","emoji":"hand","reason":"risk","spoken_script":"Check this evidence"}',reply=reply)
    async def exercise():
        await client.on_message(message)
        view=sent[-1][1]['view']
        assert [button.label for button in view.children]==['Grant Floor','Text Instead','Dismiss']
        async def defer(**kwargs):pass
        interaction=SimpleNamespace(user=message.author,guild=message.guild,response=SimpleNamespace(defer=defer),followup=SimpleNamespace(send=reply))
        await view.children[1].callback(interaction)
        assert 'Check this evidence' in sent[-1][0]
        assert not workflow.floor_controller.active_speakers
        await client.close()
    asyncio.run(exercise())
    thread.join(timeout=2)
