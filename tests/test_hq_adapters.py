import io
import json
import os
from unittest.mock import Mock
from test_unified_superpowers import setup


def test_antigravity_wrapper_uses_real_input_and_only_hook_credentials(tmp_path,monkeypatch):
    from server import antigravity_hook as entry
    from scope_guard.antigravity import hook_handler
    (tmp_path/'server').mkdir()
    (tmp_path/'.env').write_text('SHIPCOURT_HOOK_TOKEN=scoped-test-token\nSHIPCOURT_AGENT_ID=frontend-agent\nGROQ_API_KEY=do-not-export-this-key\n',encoding='utf-8')
    monkeypatch.setattr(entry,'__file__',str(tmp_path/'server'/'antigravity_hook.py'))
    for key in ('SHIPCOURT_HOOK_TOKEN','SHIPCOURT_AGENT_ID','GROQ_API_KEY','SHIPCOURT_COORDINATOR_URL','SHIPCOURT_WORKSPACE_ROOT'):monkeypatch.delenv(key,raising=False)
    incoming='{"toolCall":{"name":"edit_file","args":{"Path":"server/app.py"}}}'
    monkeypatch.setattr('sys.stdin',io.StringIO(incoming));received=[]
    monkeypatch.setattr(hook_handler,'main',lambda:received.append(__import__('sys').stdin.read()))
    entry.main()
    assert received==[incoming] and os.environ['SHIPCOURT_AGENT_ID']=='frontend-agent'
    assert 'GROQ_API_KEY' not in os.environ


def test_long_discord_records_keep_full_artifact_and_receipt(setup,tmp_path,monkeypatch):
    from server import notifications as n
    w,p,_,_=setup
    mapping=tmp_path/'channels.json';mapping.write_text(json.dumps({'guild_id':'guild','channels':{'meeting-recaps':'recaps'}}))
    monkeypatch.setattr(n,'MAP_PATH',mapping)
    api=Mock();api.call.return_value={'id':'real-contract-receipt'}
    content='source-linked discussion '*300
    w.store.put('discord_outbox','recap',{'id':'recap','channel':'meeting-recaps','correlation_id':'meeting-1','content':content,'status':'PENDING','attempts':0})
    delivery=n.Notifications(w,api);delivery.flush();delivery.flush()
    api.call.assert_called_once()
    assert api.call.call_args.kwargs['attachment'][1]==content
    assert api.call.call_args.args[2]['enforce_nonce'] is True
    assert w.store.get('discord_outbox','recap')['receipt']['message_id']=='real-contract-receipt'
