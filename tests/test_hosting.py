import hashlib
import json
import sqlite3
import threading
import urllib.request
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from server.hosting import prepare_bundle,public_origin,read_env,write_private
from server.authorization import AuthorizationService
from server.main import ShipCourtHTTPHandler,ShipCourtServer
from server.unified_pipeline import UnifiedBoardroomCourtPipeline
from server.groq_agents import ROLES


def test_public_proxy_uses_secure_sessions_and_rejects_wrong_origin_host(tmp_path,monkeypatch):
    monkeypatch.setenv('SHIPCOURT_PUBLIC_ORIGIN','https://shipcourt.example.test')
    secret='deployment-test-local-credential-with-32-characters'
    auth=AuthorizationService([{'id':'owner','token_sha256':hashlib.sha256(secret.encode()).hexdigest(),'roles':['operator','approver'],'scopes':['*']}])
    w=UnifiedBoardroomCourtPipeline(authorization=auth,db_path=tmp_path/'state.db',debate_engine=Mock())
    class Handler(ShipCourtHTTPHandler):pass
    Handler.workflow=w;Handler.mgr=w.manager;Handler.room=w.room
    http=ShipCourtServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{http.server_port}'
    def call(path,body=None,headers=None):
        request=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json','Host':'shipcourt.example.test','Origin':'https://shipcourt.example.test',**(headers or {})})
        return urllib.request.urlopen(request,timeout=10)
    try:
        response=call('/api/auth/login',{'credential':secret})
        cookie=response.headers['Set-Cookie'];assert 'Secure' in cookie and 'HttpOnly' in cookie
        token=cookie.split(';')[0];identity=json.load(call('/api/auth/me',headers={'Cookie':token}))
        assert identity['identity']=='owner'
        assert 'Ship Court' in call('/').read().decode()
        with pytest.raises(urllib.error.HTTPError):call('/api/auth/login',{'credential':secret},{'Origin':'http://shipcourt.example.test'})
        with pytest.raises(urllib.error.HTTPError):call('/api/hq',headers={'Cookie':token,'Host':'attacker.example.test'})
        with pytest.raises(urllib.error.HTTPError):call('/api/hq/action',{'action':'snapshot'},{'Cookie':token,'X-CSRF-Token':identity['csrf'],'Origin':'https://attacker.example.test'})
        assert call('/health',headers={'Host':f'127.0.0.1:{http.server_port}','Origin':''}).status==200
    finally:http.shutdown();http.server_close();thread.join(3)


@pytest.mark.parametrize('origin',['http://shipcourt.example.com','https://user:secret@example.com','https://example.com/path','https://example.com?q=1'])
def test_invalid_public_origin_fails_closed(origin,monkeypatch):
    monkeypatch.setenv('SHIPCOURT_PUBLIC_ORIGIN',origin)
    with pytest.raises(ValueError):public_origin()


def test_private_migration_bundle_preserves_data_and_separates_credentials(tmp_path):
    root=tmp_path/'repo';runtime=root/'.runtime';runtime.mkdir(parents=True)
    token='test-owner-credential-of-more-than-32-characters';groq='test-groq-credential-private'
    clients=[{'role':r,'url':'http://localhost:63239','key_env':'KEY_'+r,'agent_id':'id-'+r,'room_id':'actual-room'} for r in ROLES]
    env={'SHIPCOURT_TOKEN':token,'SHIPCOURT_IDENTITIES':json.dumps([{'id':'owner','roles':['operator'],'token_sha256':hashlib.sha256(token.encode()).hexdigest()}]),
        'GROQ_API_KEY':groq,'DEFAULT_GROQ_MODEL':'configured-model','GITHUB_TOKEN':'test-github-private','SWITCH_URL':'http://localhost:63239',
        'SWITCH_CLIENTS':json.dumps(clients),'UNRELATED_SECRET':'do-not-copy'}
    env.update({'KEY_'+r:'test-private-agent-'+r for r in ROLES})
    (root/'.env').write_text('\n'.join(k+'='+v for k,v in env.items()))
    (runtime/'discord_channels.json').write_text('{"guild_id":"guild","channels":{"meeting-floor":"floor"}}')
    with sqlite3.connect(runtime/'shipcourt.sqlite3') as db:db.execute('CREATE TABLE example(value TEXT)');db.execute("INSERT INTO example VALUES ('persistent mission')")
    output=runtime/'bundle';manifest=prepare_bundle(root,output,'shipcourt.example.com','owner@example.com')
    backend=(output/'config/backend.env').read_text();voice=(output/'config/voice.env').read_text()
    assert token in backend and token not in voice and 'test-github-private' not in voice
    assert 'do-not-copy' not in backend+voice and groq in voice
    exported=read_env(output/'config/backend.env')
    assert exported['GROQ_API_KEY']==groq and exported['SHIPCOURT_TOKEN']==token
    assert len(exported)>5 and exported['DEFAULT_GROQ_MODEL']=='configured-model'
    with pytest.raises(ValueError):write_private(runtime/'invalid.env',{'KEY':'first\nSECOND=oops'})
    for bad in ('example.com\n{','example.com}','#example.com','-invalid.example.com'):
        with pytest.raises(ValueError):prepare_bundle(root,runtime/'bad',bad,'owner@example.com')
    assert 'http://localhost:63239' not in backend and 'http://127.0.0.1:8000' in backend
    with sqlite3.connect(output/'state/shipcourt.sqlite3') as db:assert db.execute('SELECT value FROM example').fetchone()[0]=='persistent mission'
    assert manifest['switch_database_included'] is False and not manifest['switch_secrets_included']
    with pytest.raises(ValueError):prepare_bundle(root,root/'public','shipcourt.example.com','owner@example.com')
    with pytest.raises(ValueError):prepare_bundle(root,output,'shipcourt.example.com','owner@example.com')


def test_prolonged_switch_outage_keeps_retrying_with_capped_delay():
    from server.switch_protocol import SwitchProtocolClient
    from server.store import Store
    client=SwitchProtocolClient('http://localhost:8000','agent','secret','room',Store())
    client.listen_once=Mock(side_effect=[ConnectionError('outage')]*7+[KeyboardInterrupt()])
    client.stop=Mock();client.stop.wait.return_value=False
    with pytest.raises(KeyboardInterrupt):client.run(lambda event:None)
    assert client.listen_once.call_count==8
    assert [c.args[0] for c in client.stop.wait.call_args_list]==[1,2,4,8,16,30,30]


def test_occupied_port_does_not_start_duplicate_gateways(tmp_path,monkeypatch):
    from server import main,discord_gateway,switch_worker
    import server.unified_pipeline as pipeline
    monkeypatch.delenv('SHIPCOURT_PUBLIC_ORIGIN',raising=False)
    monkeypatch.setenv('SHIPCOURT_STATE_PATH',str(tmp_path/'state.db'))
    monkeypatch.setattr(main,'setup_live_courtroom',Mock())
    monkeypatch.setattr(pipeline,'UnifiedBoardroomCourtPipeline',lambda **kwargs:SimpleNamespace(manager=Mock(),room=Mock()))
    class Handler(ShipCourtHTTPHandler):pass
    monkeypatch.setattr(main,'ShipCourtHTTPHandler',Handler)
    monkeypatch.setattr(main,'ShipCourtServer',Mock(side_effect=OSError('port occupied')))
    discord=Mock();workers=Mock()
    monkeypatch.setattr(discord_gateway,'start_discord_gateway',discord);monkeypatch.setattr(switch_worker,'start_workers',workers)
    with pytest.raises(OSError):main.start_server()
    discord.assert_not_called();workers.assert_not_called()


def test_backup_is_consistent_and_refuses_overwrite(tmp_path):
    from deploy.backup import backup
    source=tmp_path/'live.sqlite3';target=tmp_path/'backups'/'copy.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE missions(id TEXT)');db.execute("INSERT INTO missions VALUES ('mission-1')")
    backup(source,target)
    with sqlite3.connect(target) as db:assert db.execute('SELECT id FROM missions').fetchone()[0]=='mission-1'
    with pytest.raises(ValueError):backup(source,target)
