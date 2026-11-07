import hashlib
from unittest.mock import Mock
import pytest
from server.authorization import AuthorizationService
from server.unified_pipeline import UnifiedBoardroomCourtPipeline
from server.voice_bridge import VoiceBridge


def test_voice_gateway_cannot_impersonate_an_unmapped_human(tmp_path):
    token='voice-service-test-credential-at-least-32'
    auth=AuthorizationService([{'id':'voice-service','token_sha256':hashlib.sha256(token.encode()).hexdigest(),
                                'roles':['voice_gateway'],'scopes':['gateway:voice']}])
    gateway=auth.authenticate('Bearer '+token)
    workflow=UnifiedBoardroomCourtPipeline(authorization=auth,db_path=tmp_path/'voice.sqlite3')
    workflow.debate_engine=Mock()
    workflow.debate_engine._call_llm.return_value='{"raise_hand":true,"reason":"Risk","script":"Check the timeout","priority":80,"evidence_refs":["spoken-1"]}'
    bridge=VoiceBridge(workflow,'guild',{'123':{'roles':['operator','approver'],'scopes':['*']},
                                      '456':{'roles':['operator'],'scopes':['*']}})
    def call(action,args=None,uid='123'):
        return bridge.handle(gateway,{'guild_id':'guild','user_id':uid,'action':action,'args':args or {}})
    with pytest.raises(PermissionError):
        call('start',{'title':'meeting'},uid='admin')
    with pytest.raises(PermissionError):
        auth.require(gateway,role='approver')
    meeting=call('start',{'title':'Review'})
    mid=meeting['meeting_id']
    with pytest.raises(PermissionError):
        call('test-request',{'meeting_id':mid},uid='456')
    check=call('test-request',{'meeting_id':mid})
    # An explicit test command still creates a waiting request, not auto speech.
    with pytest.raises(ValueError):
        call('speak',{'meeting_id':mid,'request_id':check['request_id']})
    # Remove the test request through the same human boundary before the main scenario.
    call('grant',{'meeting_id':mid,'request_id':check['request_id']})
    call('speak',{'meeting_id':mid,'request_id':check['request_id']})
    call('release',{'meeting_id':mid,'request_id':check['request_id']})
    with pytest.raises(PermissionError):
        call('transcript',{'meeting_id':mid,'text':'Timeout risk','event_id':'spoken-1'})
    call('consent',{'meeting_id':mid,'enabled':True})
    result=call('transcript',{'meeting_id':mid,'text':'Timeout risk','event_id':'spoken-1'})
    rid=result['request']['request_id']
    with pytest.raises(ValueError, match='full floor- ID'):
        call('grant', {'meeting_id':mid,'request_id':'unknown'})
    # A new utterance must not re-raise an old concern based only on old evidence.
    assert call('transcript',{'meeting_id':mid,'text':'Thank you','event_id':'spoken-2'})['request'] is None
    args={'meeting_id':mid,'request_id':rid}
    with pytest.raises(ValueError): call('speak',args)
    with pytest.raises(PermissionError): call('grant',args,uid='456')
    with pytest.raises(PermissionError): call('grant',{**args,'meeting_id':'other'})
    assert call('grant',args)['granted']
    assert call('speak',args)['script']=='Check the timeout'
    call('release',args)
    assert not workflow.floor_controller.active_speakers
    call('consent',{'meeting_id':mid,'enabled':False})
    with pytest.raises(PermissionError): call('transcript',{'meeting_id':mid,'text':'stop','event_id':'spoken-2'})
    assert workflow.meetings.get(mid)['transcripts'][0]['source']=='discord_voice_transcription'
