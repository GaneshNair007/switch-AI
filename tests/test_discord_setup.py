import copy
import json
import pytest
from server import discord_setup as d


class API:
    def __init__(self):
        self.channels=[{'id':'old-text','name':'ship-court','type':0,'parent_id':None},
            {'id':'old-voice','name':'boardroom','type':2,'parent_id':None}];self.writes=[]
    def call(self,method,path,body=None):
        if method=='GET':
            if path=='/users/@me':return {'id':'bot'}
            if '/members/' in path:return {'roles':['bot-role']}
            if path.endswith('/roles'):return [{'id':'guild','permissions':'0'},{'id':'bot-role','permissions':str(16|(1<<28))}]
            return copy.deepcopy(self.channels)
        self.writes.append((method,path,body))
        if method=='POST':
            channel={'id':str(len(self.channels)+1),**body};self.channels.append(channel);return channel
        channel=next(c for c in self.channels if c['id']==path.rsplit('/',1)[-1]);channel.update(body);return channel


def test_reconcile_is_idempotent_preserves_channels_and_permissions(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'MAP_PATH',tmp_path/'ids.json');api=API();members={'human':{'roles':['operator','approver']}}
    report=d.plan(api,'guild',members)
    assert not api.writes and not report['conflicts']
    with pytest.raises(PermissionError):d.apply(api,report,'other-server')
    ids=d.apply(api,report,'guild');count=len(api.channels)
    assert count==24 and ids['ship-court']=='old-text' and ids['Boardroom Live']=='old-voice'
    second=d.plan(api,'guild',members,ids);assert all(c['action']=='reuse' for c in second['changes'])
    d.apply(api,second,'guild');assert len(api.channels)==count
    private=next(c for c in api.channels if c['name']=='approvals')
    assert int(next(o for o in private['permission_overwrites'] if o['id']=='guild')['deny'])&1024
    unrelated={'id':'human-role','type':0,'allow':'2048','deny':'8192'}
    merged=d.overwrites('guild','bot',members,[unrelated]);assert unrelated in merged
    assert json.loads(d.MAP_PATH.read_text())['guild_id']=='guild'


def test_duplicate_and_privacy_conflicts_fail_closed(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'MAP_PATH',tmp_path/'ids.json')
    api=API();api.channels.append({'id':'duplicate','name':'ship-court','type':0})
    report=d.plan(api,'guild',{})
    with pytest.raises(ValueError):d.apply(api,report,'guild')
    api=API();api.channels.append({'id':'private','name':'approvals','type':0,'permission_overwrites':[{'id':'public-role','type':0,'allow':'1024','deny':'0'}]})
    assert d.plan(api,'guild',{})['conflicts']
    report=d.plan(API(),'guild',{});report['provisioning_allowed']=False
    with pytest.raises(PermissionError):d.apply(api,report,'guild')
