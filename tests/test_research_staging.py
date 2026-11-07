import io
import json
from unittest.mock import Mock
import pytest
from server.research import ResearchService
from server.staging import measure_staging
from server.authorization import AuthorizationService
import hashlib
from server.store import Store


def test_research_rejects_unretrieved_citations_and_unknown_hosts():
    token = 'research-test-token-at-least-32-characters'
    auth = AuthorizationService([{'id':'researcher','token_sha256':hashlib.sha256(token.encode()).hexdigest(),
                                  'roles':['operator'],'scopes':['*']}])
    principal = auth.authenticate('Bearer ' + token)
    engine=Mock();engine._call_llm.return_value=json.dumps({'status':'SUPPORTED','explanation':'Source says so','source_ids':['invented']})
    service=ResearchService(auth,Store(),engine,['docs.example.test'],lambda *a,**k:io.BytesIO(b'<p>Actual source content</p>'))
    with pytest.raises(ValueError,match='not retrieved'):
        service.verify('claim',['https://docs.example.test/source'],principal,'case')
    with pytest.raises(ValueError,match='allowlisted'):
        service.verify('claim',['http://127.0.0.1/admin'],principal,'case')
    engine._call_llm.return_value=json.dumps({'status':'INCONCLUSIVE','explanation':'Insufficient evidence','source_ids':['source-1']})
    result=service.verify('claim',['https://docs.example.test/source'],principal,'case')
    assert result['sources'][0]['retrieved'] is True
    assert result['status']=='INCONCLUSIVE'


def test_staging_metrics_are_observed_not_rollback_claims():
    class Response(io.BytesIO): status=200
    clock=iter([0,.1,1,1.2])
    result=measure_staging('https://staging.example.test/health',samples=2,opener=lambda *a,**k:Response(b'ok'),clock=lambda:next(clock))
    assert result['success_rate']==100
    assert result['p99_latency_ms']==pytest.approx(200)
    assert result['rollback_executed'] is False
    assert result['mode']=='OBSERVED_STAGING'
