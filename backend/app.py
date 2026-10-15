from copy import deepcopy
from pathlib import Path
import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from .engine import generate, verify, correct, discoverable, infer, graph, validate_accusation, SETTINGS, GENRES, RELATIONS

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('CASE101_DB', str(ROOT / 'data' / 'case101.sqlite3')))
DB.parent.mkdir(parents=True, exist_ok=True)
LOCK = threading.RLock()

@contextmanager
def db():
    with LOCK:
        conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
        try: yield conn; conn.commit()
        finally: conn.close()

with db() as conn:
    conn.executescript('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, selected TEXT); CREATE TABLE IF NOT EXISTS cases (owner TEXT, id TEXT, data TEXT, progress TEXT, PRIMARY KEY(owner,id));')

app = FastAPI(title='Case 101', docs_url=None, redoc_url=None)

@app.middleware('http')
async def boundary(request: Request, call_next):
    if request.url.path.startswith('/api') and request.method not in ['GET', 'HEAD']:
        origin = request.headers.get('origin')
        allowed = {str(request.base_url).rstrip('/'), 'http://127.0.0.1:5173', 'http://localhost:5173'}
        allowed.update(x for x in os.environ.get('CASE101_ORIGINS', '').split(',') if x)
        if origin and origin not in allowed: return Response('Origin not allowed', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if request.url.path.startswith('/api'): response.headers['Cache-Control'] = 'no-store'
    return response

def owner(req):
    sid = req.cookies.get('case101_session')
    with db() as conn: valid = conn.execute('SELECT id FROM sessions WHERE id=?', (sid,)).fetchone()
    if not valid: raise HTTPException(401, 'Open the archive to establish a local player session.')
    return sid

def fresh_progress():
    return {'found': [], 'pinned': [], 'links': [], 'notes': [], 'positions': {}, 'solved': False, 'revealed': False, 'argument': {}}

def put(sid, c, p=None):
    with db() as conn:
        existing = conn.execute('SELECT progress FROM cases WHERE owner=? AND id=?', (sid, c['id'])).fetchone()
        progress = p if p is not None else json.loads(existing['progress']) if existing else fresh_progress()
        conn.execute('INSERT OR REPLACE INTO cases VALUES (?,?,?,?)', (sid, c['id'], json.dumps(c), json.dumps(progress)))

def get(sid, cid):
    with db() as conn: row = conn.execute('SELECT data,progress FROM cases WHERE owner=? AND id=?', (sid, cid)).fetchone()
    if not row: raise HTTPException(404, 'Case not found in this player’s archive.')
    return json.loads(row['data']), json.loads(row['progress'])

def certify(c):
    c['state'] = 'verifying'; c['report'] = verify(c); c['state'] = c['report']['status']; return c

def summary(c, p):
    return {k: c[k] for k in ['id', 'version', 'seed', 'setting', 'genre', 'title', 'victim', 'state', 'brief']} | {'found': len(p['found']), 'total': len(c['clues']), 'solved': p['solved'], 'parent_id': c.get('parent_id')}

def view(c, p, author=False):
    report = c.get('report') or {'status': c['state'], 'playable': False, 'checks': [], 'issues': []}
    if not author: report = {k: v for k, v in report.items() if k not in ['paths', 'issues']} | {'issues': []}
    clues = []
    for clue in c['clues']:
        public = {k: clue[k] for k in ['id', 'name', 'place', 'x', 'z', 'requires', 'interview'] if k in clue}
        public.update(found=clue['id'] in p['found'], available=discoverable(c, clue['id'], p['found']))
        if author or public['found']: public.update({k: clue[k] for k in ['kind', 'text', 'trusted', 'claims']})
        clues.append(public)
    result = summary(c, p) | {'places': c['places'], 'people': c['people'], 'clues': clues, 'requirements': c['requirements'], 'report': report, 'progress': p, 'timeline': [e for e in c['timeline'] if author or e['clue'] in p['found']], 'corrections': c.get('corrections', []) if author else []}
    if author or p['solved'] or p['revealed']: result['solution'] = c['solution']
    return result

@app.get('/api/session')
def session(req: Request, response: Response):
    sid = req.cookies.get('case101_session')
    with db() as conn: row = conn.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
    if not row:
        sid = secrets.token_urlsafe(32)
        with db() as conn: conn.execute('INSERT INTO sessions VALUES (?,NULL)', (sid,))
        for seed, setting, genre in [(1042, 'manor', 'murder'), (2087, 'train', 'theft'), (3916, 'museum', 'sabotage')]: put(sid, certify(generate(seed, setting, genre)))
        response.set_cookie('case101_session', sid, httponly=True, samesite='strict', secure=req.url.scheme == 'https', max_age=31536000)
    with db() as conn:
        selected = conn.execute('SELECT selected FROM sessions WHERE id=?', (sid,)).fetchone()['selected']
        rows = conn.execute('SELECT data,progress FROM cases WHERE owner=?', (sid,)).fetchall()
    return {'cases': [summary(json.loads(r['data']), json.loads(r['progress'])) for r in rows], 'selected': selected, 'settings': SETTINGS, 'genres': GENRES, 'relations': RELATIONS}

class Generation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seed: int = Field(ge=0, le=4294967295)
    setting: str = 'manor'
    genre: str = 'murder'

@app.post('/api/cases')
def create(body: Generation, req: Request):
    sid = owner(req)
    try: c = generate(body.seed, body.setting, body.genre, 'mixed')
    except ValueError as e: raise HTTPException(422, str(e))
    # Distinct draft identity for a different fault variant, without changing reproducibility.
    c['id'] = c['id'].replace('-r1', f'-{c["fault"]}-r1')
    try: existing, p = get(sid, c['id']); return view(existing, p, True)
    except HTTPException as e:
        if e.status_code != 404: raise
    put(sid, c)
    return view(c, fresh_progress(), True)

@app.post('/api/cases/{cid}/verify')
def verify_case(cid: str, req: Request):
    sid = owner(req); c, p = get(sid, cid); certify(c); put(sid, c, p); return view(c, p, True)

@app.get('/api/cases/{cid}')
def case_detail(cid: str, req: Request, author: bool = False):
    c, p = get(owner(req), cid); return view(c, p, author)

@app.post('/api/cases/{cid}/select')
def select(cid: str, req: Request):
    sid = owner(req); c, p = get(sid, cid)
    if c['state'] != 'verified' or not verify(c)['playable']: raise HTTPException(409, 'Choose a verified case. This draft is not playable.')
    with db() as conn: conn.execute('UPDATE sessions SET selected=? WHERE id=?', (cid, sid))
    return view(c, p)

@app.post('/api/cases/{cid}/correction-preview')
def preview_correction(cid: str, req: Request):
    sid = owner(req); c, p = get(sid, cid)
    if c['state'] != 'rejected': raise HTTPException(409, 'Only rejected drafts need correction.')
    fixed, changes = correct(c)
    return {'original_id': cid, 'proposed_id': fixed['id'], 'changes': changes, 'original_report': c['report'], 'result': verify(fixed)}

@app.post('/api/cases/{cid}/correct')
def apply_correction(cid: str, req: Request):
    sid = owner(req); c, p = get(sid, cid)
    if c['state'] != 'rejected': raise HTTPException(409, 'Only rejected drafts need correction.')
    fixed, changes = correct(c); certify(fixed); put(sid, fixed)
    return view(fixed, fresh_progress(), True)

class Edit(BaseModel):
    clue_id: str
    requires: list[str] = Field(max_length=20)

@app.post('/api/cases/{cid}/edit')
def edit_case(cid: str, body: Edit, req: Request):
    sid = owner(req); c, _ = get(sid, cid); c = deepcopy(c)
    clue = next((x for x in c['clues'] if x['id'] == body.clue_id), None)
    if not clue: raise HTTPException(422, 'Unknown clue.')
    c['parent_id'] = cid; c['version'] += 1
    c['id'] = cid.rsplit('-r', 1)[0] + '-edit' + secrets.token_hex(3) + f'-r{c["version"]}'
    c['corrections'] = [{'target': body.clue_id, 'before': clue['requires'], 'after': body.requires, 'explanation': 'Manual dependency edit.'}]
    clue['requires'] = body.requires; certify(c); put(sid, c); return view(c, fresh_progress(), True)

class Discovery(BaseModel):
    clue_id: str

class Claim(BaseModel):
    category: str
    evidence: list[str] = Field(default_factory=list, max_length=30)
    relation: str = ''
    explanation: str = Field(default='', max_length=1000)

class ConflictArgument(BaseModel):
    claim: str = ''
    evidence: str = ''
    resolution: str = ''

class AlternativeArgument(BaseModel):
    suspect: str = ''
    evidence: str = ''

class AssumptionArgument(BaseModel):
    kind: str = ''
    evidence: str = ''

class Challenge(BaseModel):
    strongest: str = ''
    conflict: ConflictArgument = Field(default_factory=ConflictArgument)
    alternative: AlternativeArgument = Field(default_factory=AlternativeArgument)
    assumption: AssumptionArgument = Field(default_factory=AssumptionArgument)

class Argument(BaseModel):
    suspect: str = ''
    claims: list[Claim] = Field(default_factory=list, max_length=12)
    challenge: Challenge = Field(default_factory=Challenge)

def require_playable(c):
    if c['state'] != 'verified' or not c.get('report', {}).get('playable'): raise HTTPException(409, 'This case is not verified/playable.')

@app.post('/api/cases/{cid}/discover')
def discover(cid: str, body: Discovery, req: Request):
    sid = owner(req); c, p = get(sid, cid); require_playable(c)
    if not discoverable(c, body.clue_id, p['found']): raise HTTPException(409, 'Recover the prerequisite evidence before opening this clue.')
    if body.clue_id not in p['found']: p['found'].append(body.clue_id)
    if body.clue_id not in p['pinned']: p['pinned'].append(body.clue_id)
    put(sid, c, p); return view(c, p)

class BoardAction(BaseModel):
    action: str
    clue_id: str | None = None
    id: str | None = None
    source: str | None = None
    target: str | None = None
    relation: str | None = None
    explanation: str = Field(default='', max_length=1000)
    text: str = Field(default='', max_length=3000)
    x: float = Field(default=0, ge=-200, le=300)
    y: float = Field(default=0, ge=-100, le=300)

@app.post('/api/cases/{cid}/board')
def board(cid: str, body: BoardAction, req: Request):
    sid = owner(req); c, p = get(sid, cid); require_playable(c)
    if body.action in ['pin', 'unpin', 'position']:
        if body.clue_id not in p['found']: raise HTTPException(422, 'Only discovered evidence may be used on this board.')
        if body.action == 'pin' and body.clue_id not in p['pinned']: p['pinned'].append(body.clue_id)
        if body.action == 'unpin':
            p['pinned'] = [x for x in p['pinned'] if x != body.clue_id]
            p['links'] = [x for x in p['links'] if body.clue_id not in [x['source'], x['target']]]
        if body.action == 'position': p['positions'][body.clue_id] = {'x': body.x, 'y': body.y}
    elif body.action in ['connect', 'edit-link']:
        if body.source == body.target or body.source not in p['pinned'] or body.target not in p['pinned'] or body.relation not in RELATIONS: raise HTTPException(422, 'Connect two different pinned clues with a supported relationship type.')
        link = {'id': body.id or secrets.token_hex(6), 'source': body.source, 'target': body.target, 'relation': body.relation, 'explanation': body.explanation}
        if body.action == 'edit-link' and not any(x['id'] == body.id for x in p['links']): raise HTTPException(404, 'Connection not found.')
        p['links'] = [x for x in p['links'] if x['id'] != link['id']] + [link]
    elif body.action == 'disconnect': p['links'] = [x for x in p['links'] if x['id'] != body.id]
    elif body.action == 'note':
        if not body.text.strip(): raise HTTPException(422, 'Enter a note before saving.')
        if body.id and not any(x['id'] == body.id for x in p['notes']): raise HTTPException(404, 'Note not found.')
        note = {'id': body.id or secrets.token_hex(6), 'text': body.text}
        p['notes'] = [x for x in p['notes'] if x['id'] != note['id']] + [note]
    elif body.action == 'delete-note': p['notes'] = [x for x in p['notes'] if x['id'] != body.id]
    else: raise HTTPException(422, 'Unknown board action.')
    put(sid, c, p); return view(c, p)

@app.post('/api/cases/{cid}/argument')
def save_argument(cid: str, body: Argument, req: Request):
    sid = owner(req); c, p = get(sid, cid); require_playable(c); p['argument'] = body.model_dump(); put(sid, c, p)
    return {'saved': True}

@app.post('/api/cases/{cid}/accuse')
def accuse(cid: str, body: Argument, req: Request):
    sid = owner(req); c, p = get(sid, cid); result = validate_accusation(c, p, body.model_dump())
    p['argument'] = body.model_dump()
    if result['accepted']: p['solved'] = True
    put(sid, c, p); return result

@app.post('/api/cases/{cid}/reveal')
def reveal(cid: str, req: Request):
    sid = owner(req); c, p = get(sid, cid); p['revealed'] = True; put(sid, c, p)
    return {'solution': c['solution'], 'abandoned': not p['solved']}

@app.get('/api/cases/{cid}/graph')
def graph_view(cid: str, req: Request, author: bool = False):
    c, p = get(owner(req), cid); g = graph(c); proofs = infer(c, None if author else p['found'])
    allnodes = {n['id']: n for n in c['facts'] + c['clues']}
    allowed = set(g) if author else {id for id in g if allnodes.get(id, {}).get('source') or (proofs.get(id) and allnodes.get(id, {}).get('type') != 'conclusion')}
    nodes = []
    for id in g:
        if id not in allowed: continue
        n = allnodes.get(id, {'id': id, 'name': id, 'type': 'missing'})
        nodes.append({'id': id, 'name': n.get('name', id), 'type': n['type'], 'proven': bool(proofs.get(id)), 'rules': [r for r in c['rules'] if r['head'] == id and (author or set(r['body']) <= allowed)], 'requires': n.get('requires', [])})
    edges = [{'id': f'{a}>{b}', 'source': a, 'target': b, 'label': data['relation']} for a, b, data in g.edges(data=True) if a in allowed and b in allowed]
    report = c.get('report', {})
    return {'case_id': cid, 'nodes': nodes, 'edges': edges, 'paths': report.get('paths', []) if author else [], 'issues': report.get('issues', []) if author else []}

@app.post('/api/import-v2')
def import_v2(body: dict, req: Request):
    sid = owner(req); imported = 0
    for spec in body.get('library', [])[:200]:
        try: c = certify(generate(int(spec['seed']), spec['setting'], 'murder'))
        except (ValueError, KeyError, TypeError): continue
        try: _, p = get(sid, c['id'])
        except HTTPException: p = fresh_progress()
        old = body.get('saves', {}).get(f'{spec["setting"]}-{spec["seed"]}', {})
        p['legacy_snapshot'] = deepcopy(old)
        # Transfer historical discoveries only; never authorize a win from client state.
        pending = set(old.get('found', []))
        for _ in range(len(c['clues'])):
            for id in list(pending):
                if discoverable(c, id, p['found']):
                    if id not in p['found']: p['found'].append(id)
                    if id not in p['pinned']: p['pinned'].append(id)
                    pending.remove(id)
        p['legacy_case_completed'] = bool(old.get('solved'))
        put(sid, c, p); imported += 1
    return {'imported': imported, 'message': 'Recovered clues were migrated. Earlier completion flags are retained as history; Case 101 requires a newly validated argument.'}

if (ROOT / 'dist' / 'assets').exists(): app.mount('/assets', StaticFiles(directory=ROOT / 'dist' / 'assets'), name='assets')

@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith('api/'): raise HTTPException(404, 'Unknown API endpoint.')
    index = ROOT / 'dist' / 'index.html'
    if not index.exists(): return {'message': 'Run npm run build first, or use npm run dev.'}
    return FileResponse(index)
