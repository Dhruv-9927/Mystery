from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import json
import time
import pytest
from fastapi.testclient import TestClient
from tests.test_api import app, discover_all
from backend.app import get, db
from tests.test_engine import argument

@pytest.fixture
def players():
    clients = [TestClient(app) for _ in range(3)]
    for c in clients: assert c.get('/api/session').status_code == 200
    yield clients
    for c in clients: c.close()

def make(p1, p2=None, **options):
    r = p1.post('/api/matches', json={'request_key': uuid4().hex, **options})
    assert r.status_code == 200, r.text
    m = r.json()
    if p2:
        r = p2.post('/api/matches/join', json={'seed': m['seed'], 'invite_key': m['invite_key']})
        assert r.status_code == 200, r.text
    return m

def status(p, m):
    return p.post('/api/matches/'+m['id']+'/heartbeat', json={}).json()

def ready(p, m, alternate=False):
    cid=m['case_id']
    c=p.get('/api/cases/'+cid).json()
    discover_all(p, c)
    raw,_=get(p.cookies.get('case101_session'),cid)
    return argument(raw, alternate=alternate)

def test_same_case_independent_state_and_no_spoiler_escape(players):
    a,b,outsider=players
    m=make(a,b)
    cid=m['case_id']; url='/api/cases/'+cid
    raw_a,_=get(a.cookies.get('case101_session'),cid)
    raw_b,_=get(b.cookies.get('case101_session'),cid)
    assert raw_a == raw_b and raw_a['seed'] == m['seed']
    assert a.post(url+'/discover',json={'clue_id':'clock'}).status_code==200
    assert a.post(url+'/board',json={'action':'note','text':'PRIVATE A THEORY'}).status_code==200
    assert a.post(url+'/argument',json={'suspect':'private-a'}).status_code==200
    assert b.post(url+'/board',json={'action':'note','text':'PRIVATE B THEORY'}).status_code==200
    pa=a.get(url).json()['progress']; pb=b.get(url).json()['progress']
    assert pa['found']==['clock'] and pb['found']==[]
    assert pa['notes'][0]['text']=='PRIVATE A THEORY' and pb['notes'][0]['text']=='PRIVATE B THEORY'
    assert pb['argument']=={} and pb['pinned']==[]
    assert outsider.get(url).status_code==404
    assert outsider.post('/api/matches/'+m['id']+'/heartbeat',json={}).status_code==404
    assert outsider.get('/api/matches').json()=={'matches':[]}
    assert 'solution' not in a.get(url).json()
    for player in [a,b]:
        for suffix in ['?author=true','/graph?author=true','?author=yes','/graph?author=on','?author=1']:
            assert player.get(url+suffix).status_code==403
        for action in ['verify','correct','correction-preview','reveal']:
            assert player.post(url+'/'+action,json={}).status_code==403
        assert player.post(url+'/edit',json={'clue_id':'glass','requires':[]}).status_code==403
        assert player.post('/api/cases',json={'seed':m['seed']}).status_code==409
        graph=player.get(url+'/graph').json()
        assert not graph['paths'] and not any(n['type']=='conclusion' for n in graph['nodes'])
        payload=status(player,m)
        assert set(payload)=={'id','seed','case_id','state','player','opponent_joined','opponent_online','winner','you_won','invite_key'}
        assert 'PRIVATE' not in json.dumps(payload)
    assert b.get('/api/session').json()['cases']  # Single player files remain intact.
    assert all(not c['match_id'] for c in b.get('/api/session').json()['cases'])

def test_waiting_membership_duplicates_and_late_joins(players):
    a,b,c=players
    request={'request_key':uuid4().hex}
    m=a.post('/api/matches',json=request).json()
    assert a.post('/api/matches',json=request).json()['id']==m['id']
    assert make(a)['id']==m['id']
    url='/api/cases/'+m['case_id']
    assert a.post(url+'/discover',json={'clue_id':'clock'}).status_code==409
    assert b.post('/api/matches/join',json={'seed':m['seed']}).status_code==422
    assert b.post('/api/matches/join',json={'seed':m['seed'],'invite_key':'wrong-key-123456789'}).status_code==404
    invitation={'seed':m['seed'],'invite_key':m['invite_key']}
    assert b.post('/api/matches/join',json=invitation).json()['state']=='active'
    b.post(url+'/discover',json={'clue_id':'clock'})
    assert b.post('/api/matches/join',json=invitation).json()['player']==2
    assert b.get(url).json()['progress']['found']==['clock']
    assert c.post('/api/matches/join',json=invitation).status_code==409
    assert a.post('/api/matches/'+m['id']+'/leave',json={}).json()['state']=='cancelled'
    assert status(b,m)['state']=='cancelled'
    assert b.post(url+'/accuse',json={}).status_code==409
    assert c.post('/api/matches/join',json=invitation).status_code==409
    for seed in [-1,4294967296,'bad',True]:
        assert c.post('/api/matches/join',json={**invitation,'seed':seed}).status_code==422

@pytest.mark.parametrize('alternate',[False,True])
def test_valid_proof_wins_invalid_does_not_and_result_is_private(players,alternate):
    a,b,c=players
    m=make(a,b);url='/api/cases/'+m['case_id']
    proof=ready(b,m,alternate)
    assert not a.post(url+'/accuse',json=proof).json()['accepted'] # Undiscovered.
    assert not b.post(url+'/accuse',json={'suspect':proof['suspect']}).json()['accepted']
    assert status(a,m)['state']=='active'
    result=b.post(url+'/accuse',json=proof).json()
    assert result['accepted'] and result['match']['you_won']
    assert status(a,m)['winner']==2 and not status(a,m)['you_won']
    assert status(b,m)['winner']==2
    assert b.post(url+'/accuse',json=proof).status_code==409 # No duplicate win.
    assert a.post(url+'/accuse',json=proof).status_code==409
    assert 'solution' not in a.get(url).json()
    assert not a.get(url).json()['progress']['solved']
    assert c.post('/api/matches/join',json={'seed':m['seed'],'invite_key':m['invite_key']}).status_code==409

def test_simultaneous_valid_accusations_have_exactly_one_winner(players):
    a,b,_=players
    m=make(a,b);proofs=[ready(a,m),ready(b,m,True)];barrier=Barrier(2)
    def submit(i):
        barrier.wait()
        return players[i].post('/api/cases/'+m['case_id']+'/accuse',json=proofs[i])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(submit,[0,1]))
    assert sorted(r.status_code for r in results)==[200,409]
    assert sum(r.json().get('accepted',False) for r in results)==1
    winner=status(a,m)['winner']
    assert winner==status(b,m)['winner']
    assert results[winner-1].status_code==200

def test_presence_and_cookie_reconnection(players):
    a,b,c=players
    m=make(a,b)
    b.post('/api/cases/'+m['case_id']+'/discover',json={'clue_id':'clock'})
    with db() as conn: conn.execute('UPDATE matches SET seen2=? WHERE id=?',(time.time()-30,m['id']))
    assert not status(a,m)['opponent_online']
    with TestClient(app) as reconnect:
        reconnect.cookies.update(b.cookies)
        assert status(reconnect,m)['player']==2
        assert reconnect.get('/api/cases/'+m['case_id']).json()['progress']['found']==['clock']
    assert status(a,m)['opponent_online']
    assert c.get('/api/matches').json()['matches']==[]

def test_concurrent_join_reserves_only_one_second_slot(players):
    a,b,c=players;m=make(a);barrier=Barrier(2)
    def join(player):
        barrier.wait()
        return player.post('/api/matches/join',json={'seed':m['seed'],'invite_key':m['invite_key']})
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(join,[b,c]))
    assert sorted(r.status_code for r in results)==[200,409]
