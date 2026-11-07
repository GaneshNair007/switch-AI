import hashlib
import json
import threading
import urllib.request
import urllib.error
import http.cookiejar
from unittest.mock import Mock
import pytest
from server.authorization import AuthorizationService
from server.main import ShipCourtHTTPHandler, ShipCourtServer
from server.unified_pipeline import UnifiedBoardroomCourtPipeline


def test_dashboard_cookie_security_and_shared_records(tmp_path,monkeypatch):
    secret='hq-security-test-credential-unique'
    monkeypatch.setenv('SHIPCOURT_TOKEN',secret)
    auth=AuthorizationService([{'id':'human','token_sha256':hashlib.sha256(secret.encode()).hexdigest(),
        'roles':['operator','approver'],'scopes':['*']}])
    w=UnifiedBoardroomCourtPipeline(authorization=auth,db_path=tmp_path/'state.db',debate_engine=Mock())
    class Handler(ShipCourtHTTPHandler):pass
    Handler.workflow=w;Handler.mgr=w.manager;Handler.room=w.room
    server=ShipCourtServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    jar=http.cookiejar.CookieJar();browser=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def call(path,body=None,headers=None,client=browser):
        return client.open(urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json',**(headers or {})}),timeout=10)
    try:
        html=call('/').read().decode()
        assert secret not in html and '__TOKEN_PLACEHOLDER__' not in html
        assert secret not in call('/assets/hq.js').read().decode()
        for path,body in [('/api/hq',None),('/api/audit/events',None),('/api/hq/action',{'action':'create','args':{}})]:
            with pytest.raises(urllib.error.HTTPError):call(path,body)
        with pytest.raises(urllib.error.HTTPError):call('/api/auth/login',{'credential':secret},{'Origin':'https://attacker.invalid'})
        response=call('/api/auth/login',{'credential':secret})
        assert 'HttpOnly' in response.headers['Set-Cookie'] and 'SameSite=Strict' in response.headers['Set-Cookie']
        identity=json.load(call('/api/auth/me'));assert identity['identity']=='human' and secret not in json.dumps(identity)
        args={'mission_type':'idea_studio','title':'Student tools','objective':'Validate collaborative learning'}
        with pytest.raises(urllib.error.HTTPError):call('/api/hq/action',{'action':'create','args':args})
        with pytest.raises(urllib.error.HTTPError):call('/api/hq/action',{'action':'create','args':args},{'X-CSRF-Token':identity['csrf'],'Origin':'https://attacker.invalid'})
        mission=json.load(call('/api/hq/action',{'action':'create','args':args},{'X-CSRF-Token':identity['csrf']}))
        assert json.load(call('/api/hq'))['missions'][0]['mission_id']==mission['mission_id']
        call('/api/auth/logout',{}, {'X-CSRF-Token':identity['csrf']})
        with pytest.raises(urllib.error.HTTPError):call('/api/hq')
    finally:
        server.shutdown();server.server_close();thread.join(3)


def test_expired_and_revoked_dashboard_sessions_fail_closed():
    from dataclasses import replace
    import time
    from server.dashboard_auth import DashboardSessions
    secret='another-local-security-test-credential'
    auth=AuthorizationService([{'id':'viewer','token_sha256':hashlib.sha256(secret.encode()).hexdigest(),'roles':['viewer'],'scopes':[]}])
    sessions=DashboardSessions(auth);token=sessions.login(secret);cookie='shipcourt_session='+token
    p=sessions.resolve(cookie)['principal'];assert time.time()<p.expires_at<=time.time()+300
    auth.revoke(p)
    with pytest.raises(PermissionError):sessions.resolve(cookie)
    token=sessions.login(secret);record=sessions.sessions[token]
    record['principal']=replace(record['principal'],expires_at=time.time()-1)
    with pytest.raises(PermissionError):sessions.resolve('shipcourt_session='+token)
