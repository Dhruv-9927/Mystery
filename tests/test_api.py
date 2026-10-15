import os
import tempfile
from pathlib import Path
os.environ['CASE101_DB'] = str(Path(tempfile.mkdtemp()) / 'test.sqlite3')
from fastapi.testclient import TestClient
from backend.app import app, get
from tests.test_engine import argument
import pytest

@pytest.fixture
def client():
    with TestClient(app) as c:
        assert c.get('/api/session').status_code==200
        yield c

def create(client, **kwargs):
    r=client.post('/api/cases',json={'seed':512, 'setting':'manor','genre':'murder','fault':'none',**kwargs})
    assert r.status_code==200,r.text
    draft=r.json(); assert draft['state']=='draft'
    assert client.post('/api/cases/'+draft['id']+'/select',json={}).status_code==409
    return client.post('/api/cases/'+draft['id']+'/verify',json={}).json()

def discover_all(client,c):
    for _ in range(4):
        for clue in c['clues']:
            client.post('/api/cases/'+c['id']+'/discover',json={'clue_id':clue['id']})
    return client.get('/api/cases/'+c['id']).json()

def test_draft_verification_and_correction_are_gates(client):
    c=create(client,fault='missing')
    assert c['state']=='rejected'
    assert client.post('/api/cases/'+c['id']+'/select',json={}).status_code==409
    proposal=client.post('/api/cases/'+c['id']+'/correction-preview',json={}).json()
    assert proposal['changes'] and proposal['result']['playable']
    corrected=client.post('/api/cases/'+c['id']+'/correct',json={}).json()
    assert corrected['id']!=c['id'] and corrected['state']=='verified'
    assert client.get('/api/cases/'+c['id']).json()['state']=='rejected'
    assert client.post('/api/cases/'+corrected['id']+'/select',json={}).status_code==200
    assert client.get('/api/session').json()['selected']==corrected['id']

def test_board_notes_connections_and_case_isolation(client):
    c=create(client);other=create(client,seed=513);url='/api/cases/'+c['id']
    assert client.post(url+'/board',json={'action':'pin','clue_id':'clock'}).status_code==422
    for id in ['clock','will']: assert client.post(url+'/discover',json={'clue_id':id}).status_code==200
    p=client.post(url+'/board',json={'action':'connect','source':'will','target':'clock','relation':'supports','explanation':'Compare these records.'}).json()['progress']
    link=p['links'][0]['id']
    assert client.post(url+'/board',json={'action':'edit-link','id':link,'source':'clock','target':'will','relation':'establishes timeline','explanation':'Revised comparison.'}).status_code==200
    p=client.post(url+'/board',json={'action':'note','text':'Check the time window.'}).json()['progress']
    note=p['notes'][0]['id']
    assert client.post(url+'/board',json={'action':'note','id':note,'text':'Updated theory.'}).json()['progress']['notes'][0]['text']=='Updated theory.'
    assert client.get('/api/cases/'+other['id']).json()['progress']['found']==[]
    assert client.get('/api/cases/'+other['id']).json()['progress']['notes']==[]
    p=client.post(url+'/board',json={'action':'unpin','clue_id':'will'}).json()['progress']
    assert 'will' in p['found'] and 'will' not in p['pinned'] and not p['links']
    assert client.post(url+'/board',json={'action':'pin','clue_id':'will'}).status_code==200
    p=client.post(url+'/board',json={'action':'delete-note','id':note}).json()['progress']
    assert not p['notes']
    assert client.post(url+'/board',json={'action':'disconnect','id':link}).status_code==200

def test_full_authoritative_player_journey(client):
    c=create(client,genre='theft')
    assert client.post('/api/cases/'+c['id']+'/select',json={}).status_code==200
    assert 'solution' not in client.get('/api/cases/'+c['id']).json()
    assert all('text' not in clue for clue in client.get('/api/cases/'+c['id']).json()['clues'])
    sid=client.cookies.get('case101_session');raw,_=get(sid,c['id']);a=argument(raw)
    assert not client.post('/api/cases/'+c['id']+'/accuse',json=a).json()['accepted']
    c=discover_all(client,c)
    assert client.post('/api/cases/'+c['id']+'/argument',json=a).json()['saved']
    player_graph=client.get('/api/cases/'+c['id']+'/graph').json()
    assert not any(n['type']=='conclusion' for n in player_graph['nodes'])
    author_graph=client.get('/api/cases/'+c['id']+'/graph?author=true').json()
    assert author_graph['paths'] and any(n['type']=='conclusion' for n in author_graph['nodes'])
    result=client.post('/api/cases/'+c['id']+'/accuse',json=a).json()
    assert result['accepted'],result
    final=client.get('/api/cases/'+c['id']).json()
    assert final['progress']['solved'] and final['solution']

def test_session_boundary_and_edit_gate(client):
    c=create(client)
    with TestClient(app) as stranger:
        stranger.get('/api/session')
        assert stranger.get('/api/cases/'+c['id']).status_code==404
    edited=client.post('/api/cases/'+c['id']+'/edit',json={'clue_id':'glass','requires':['absent']}).json()
    assert edited['id']!=c['id'] and edited['state']=='rejected'
    assert client.post('/api/cases/'+edited['id']+'/select',json={}).status_code==409
    assert client.post('/api/cases',headers={'Origin':'https://evil.example'},json={'seed':1}).status_code==403

def test_explicit_reveal_is_not_a_win(client):
    c=create(client)
    assert client.post('/api/cases/'+c['id']+'/reveal',json={}).json()['abandoned']
    p=client.get('/api/cases/'+c['id']).json()
    assert p['solution'] and not p['progress']['solved']

def test_malformed_argument_rejected_without_server_error(client):
    c=create(client)
    response=client.post('/api/cases/'+c['id']+'/accuse',json={'suspect':{},'claims':'invalid','challenge':None})
    assert response.status_code==422

def test_supplied_intro_asset_identity():
    import hashlib
    asset=Path(__file__).resolve().parents[1]/'public/assets/intro.mp4'
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == '9088ee21e66865bf6b648ec633f5cc620ed9e623a6c73e99ad8d613f8d3b9294'
