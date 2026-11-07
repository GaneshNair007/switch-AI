"""Actual loopback HTTP integration; external GitHub/LLM transports are fixtures."""
import hashlib
import json
import threading
import urllib.request
import urllib.error
from unittest.mock import Mock
import pytest
from server.main import ShipCourtHTTPHandler, ShipCourtServer
from server.authorization import AuthorizationService
from server.unified_pipeline import UnifiedBoardroomCourtPipeline
from server.github_client import GitHubClient
from test_unified_superpowers import FakeGitHub, TOKEN


def test_authenticated_http_lifecycle(tmp_path, monkeypatch):
    auth = AuthorizationService([{'id':'human-http', 'token_sha256':hashlib.sha256(TOKEN.encode()).hexdigest(),
                                  'roles':['operator','approver','hook'], 'scopes':['*']}])
    engine = Mock()
    engine.run_live_trial.return_value = {'prosecutor_indictment':'Patch risk', 'defender_rebuttal':'Testing required', 'verdict':'CONDITIONS'}
    workflow = UnifiedBoardroomCourtPipeline(authorization=auth, db_path=tmp_path/'state.sqlite3',
                                             github_client=GitHubClient(transport=FakeGitHub()), debate_engine=engine)
    class Handler(ShipCourtHTTPHandler):
        pass
    Handler.workflow, Handler.mgr, Handler.room = workflow, workflow.manager, workflow.room
    server = ShipCourtServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(route, body=None, authorized=True):
        headers = {'Content-Type':'application/json'}
        if authorized: headers['Authorization']='Bearer ' + TOKEN
        req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}' + route,
            data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)
    try:
        with pytest.raises(urllib.error.HTTPError) as denied:
            call('/api/verdicts', {'case_id':'fake','judge':'admin','is_human':True,'command':'APPROVE'}, authorized=False)
        assert denied.value.code == 403
        case = call('/api/cases', {'pr_url':'https://github.com/acme/shop/pull/18','services':['checkout-service']})
        case_id = case['case_id']
        assert call('/api/cases/review', {'case_id':case_id})['binding_authorization'] is False
        brief = call('/api/verdicts', {'case_id':case_id,'command':'CONDITIONS load test'})
        assert 'Release Brief' in brief['release_brief']
        plan = call('/api/github/plan', {'case_id':case_id})
        assert call('/api/github/execute', {'case_id':case_id,'plan_hash':plan['plan_hash']})['status']=='CONFIRMED'
        meeting = call('/api/meetings/start', {'title':'Checkout review'})
        mid = meeting['meeting_id']
        call('/api/meetings/consent', {'meeting_id':mid,'enabled':True})
        call('/api/meetings/transcript', {'meeting_id':mid,'event_id':'text-1','text':'Use a bounded timeout'})
        call('/api/meetings/decision', {'meeting_id':mid,'text':'Adopt timeout','evidence_refs':['text-1']})
        request = call('/api/floor/requests', {'meeting_id':mid,'agent_id':'reviewer','emoji':'hand','reason':'risk','spoken_script':'Review timeout'})
        assert call('/api/floor/grants', {'request_id':request['request_id']})['granted'] is True
        summary = call('/api/meetings/end', {'meeting_id':mid})
        assert len(summary['decisions']) == 1
        assert not workflow.floor_controller.active_speakers
        # A real hook invocation retrieves assignment and reports its violation over HTTP.
        from scope_guard.antigravity.hook_handler import process_hook_input
        monkeypatch.setenv('SHIPCOURT_HOOK_TOKEN', TOKEN)
        monkeypatch.setenv('SHIPCOURT_AGENT_ID', 'frontend-agent')
        assignment = call('/api/scope/assignments', {'agent_id':'frontend-agent','task_id':'task-1',
                          'task_description':'Frontend only','allowed_paths':['frontend/**'],'restricted_paths':['backend/**']})
        payload = {'toolCall':{'name':'edit_file','args':{'Path':'backend/server.py'}},'workspacePaths':['untrusted-path']}
        hook = process_hook_input(payload, workspace_root=str(tmp_path), coordinator_url=f'http://127.0.0.1:{server.server_port}')
        assert hook['decision'] == 'deny'
        scope_request = {'request_id':'scope-1','agent_id':'frontend-agent','task_id':'task-1','attempted_action':'edit_file',
                         'target_path':'backend/server.py','reason':'Coordinated fix','current_version':assignment['assignment_version'],
                         'requested_paths':['backend/server.py']}
        assert call('/api/v1/approvals', scope_request)['status']=='PENDING'
        response = call('/api/scope/decide', {'request_id':'scope-1','approve':True})
        assert response['approved_by']=='human-http'
        assert process_hook_input(payload, workspace_root=str(tmp_path), coordinator_url=f'http://127.0.0.1:{server.server_port}')['decision']=='allow'
        events = call('/api/audit/events')
        assert any(e['correlation_id']==case_id and e['event_type']=='github.operation' for e in events)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
