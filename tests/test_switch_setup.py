import json
from pathlib import Path
import pytest
from server import setup_switch as s
from server.groq_agents import ROLES


def fixture_config(tmp_path,monkeypatch):
    monkeypatch.setattr(s,'ROOT',tmp_path);monkeypatch.setenv('SWITCH_URL','http://127.0.0.1:12345')
    (tmp_path/'.runtime').mkdir()
    registry={r:{'agent_id':'id-'+r,'api_key':'private-test-key-'+r,'name':'shipcourt-'+r.replace('_','-')} for r in ROLES}
    (tmp_path/'.runtime'/'switch-agents.json').write_text(json.dumps(registry))
    (tmp_path/'.env').write_text('GROQ_API_KEY=preserve-this-value\nSWITCH_CLIENTS=[]\n')
    mapping={'agents':{r:'observed:'+r for r in ROLES},'humans':['observed:human']}
    path=tmp_path/'senders.json';path.write_text(json.dumps(mapping));return path,mapping


def test_configure_restores_existing_keys_without_printing(tmp_path,monkeypatch,capsys):
    path,mapping=fixture_config(tmp_path,monkeypatch);s.configure('real-room',path)
    values=dict(line.split('=',1) for line in (tmp_path/'.env').read_text().splitlines())
    clients=json.loads(values['SWITCH_CLIENTS'])
    assert len(clients)==5 and all(c['runtime']=='groq_custom' and c['room_id']=='real-room' for c in clients)
    assert values['GROQ_API_KEY']=='preserve-this-value'
    assert values['SWITCH_CLERK_KEY']=='private-test-key-clerk'
    assert json.loads(values['SWITCH_PARTICIPANTS'])['observed:human']['roles']==['operator']
    assert 'private-test-key' not in capsys.readouterr().out
    first=(tmp_path/'.env').read_text();s.configure('real-room',path)
    assert (tmp_path/'.env').read_text()==first


@pytest.mark.parametrize('bad',['missing','duplicate','human-agent-collision'])
def test_invalid_sender_maps_never_change_credentials(tmp_path,monkeypatch,bad):
    path,mapping=fixture_config(tmp_path,monkeypatch)
    if bad=='missing':mapping['agents'].pop('clerk')
    elif bad=='duplicate':mapping['agents']['clerk']=mapping['agents']['historian']
    else:mapping['humans']=[mapping['agents']['clerk']]
    path.write_text(json.dumps(mapping));before=(tmp_path/'.env').read_text()
    with pytest.raises(ValueError):s.configure('real-room',path)
    assert (tmp_path/'.env').read_text()==before
