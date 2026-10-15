"""Real HTTP clients against separate server processes sharing one SQLite database."""
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4
import httpx
from backend.engine import generate, verify, correct
from tests.test_engine import argument

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        return sock.getsockname()[1]

def test_two_backend_processes_share_atomic_winner(tmp_path):
    processes=[];clients=[]
    env={**os.environ,'CASE101_DB':str(tmp_path/'race.sqlite3')}
    try:
        for _ in range(2):
            port=free_port()
            processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],
                cwd=Path(__file__).resolve().parents[1],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
            client=httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=15)
            clients.append(client)
            deadline=time.monotonic()+15
            while True:
                try:
                    assert client.get('/api/session').status_code==200
                    break
                except httpx.ConnectError:
                    if time.monotonic()>deadline: raise
                    time.sleep(.1)
        a,b=clients
        m=a.post('/api/matches',json={'request_key':uuid4().hex}).json()
        assert b.post('/api/matches/join',json={'seed':m['seed'],'invite_key':m['invite_key']}).status_code==200
        raw=generate(m['seed'],'manor','murder','mixed')
        if not verify(raw)['playable']: raw,_=correct(raw)
        cid=m['case_id'];url='/api/cases/'+cid
        for player in clients:
            c=player.get(url).json()
            for _ in range(3):
                for clue in c['clues']: player.post(url+'/discover',json={'clue_id':clue['id']})
        barrier=Barrier(2)
        def submit(i):
            barrier.wait()
            return clients[i].post(url+'/accuse',json=argument(raw,alternate=bool(i)))
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(submit,[0,1]))
        assert sorted(r.status_code for r in results)==[200,409]
        final=[c.post('/api/matches/'+m['id']+'/heartbeat',json={}).json() for c in clients]
        assert final[0]['winner']==final[1]['winner']
        assert all(m['state']=='completed' for m in final)
        assert sum(m['you_won'] for m in final)==1
    finally:
        for client in clients: client.close()
        for process in processes:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill();process.wait()
