"""Private two-session races; SQLite serializes membership and winning verdicts."""
import secrets
import time
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from .app import db, atomic, owner, generate, certify, correct, put, get, fresh_progress, validate_accusation

with db() as conn:
    conn.executescript('''CREATE TABLE IF NOT EXISTS matches (
      id TEXT PRIMARY KEY, seed INTEGER UNIQUE NOT NULL, case_id TEXT NOT NULL,
      p1 TEXT NOT NULL, p2 TEXT, invitation TEXT NOT NULL,
      state TEXT NOT NULL, winner TEXT, seen1 REAL NOT NULL, seen2 REAL,
      request_key TEXT NOT NULL, UNIQUE(p1, request_key));''')

def member(conn, mid, sid):
    m = conn.execute('SELECT * FROM matches WHERE id=? AND (p1=? OR p2=?)', (mid, sid, sid)).fetchone()
    if not m: raise HTTPException(404, 'Match not found in your session.')
    return m

def public(m, sid):
    slot = 1 if sid == m['p1'] else 2
    opponent_seen = m['seen2'] if slot == 1 else m['seen1']
    return {'id': m['id'], 'seed': m['seed'], 'case_id': m['case_id'], 'state': m['state'],
            'player': slot, 'opponent_joined': m['p2'] is not None,
            'opponent_online': bool(opponent_seen and time.time() - opponent_seen < 15),
            'winner': (1 if m['winner'] == m['p1'] else 2) if m['winner'] else None,
            'you_won': m['winner'] == sid,
            'invite_key': m['invitation'] if slot == 1 and m['state'] == 'waiting' else None}

def guard(conn, cid, sid, req):
    m = conn.execute('SELECT * FROM matches WHERE case_id=? AND (p1=? OR p2=?)', (cid, sid, sid)).fetchone()
    if not m: raise HTTPException(404, 'Match not found in your session.')
    action = req.url.path.rsplit('/', 1)[-1]
    if req.query_params.get('author', '').lower() not in ['', 'false', '0', 'off', 'no'] or action in ['verify', 'edit', 'correct', 'correction-preview', 'reveal']:
        raise HTTPException(403, 'Authoring and solution reveals are disabled for race cases.')
    if m['state'] == 'waiting': raise HTTPException(409, 'Waiting for the second player to join.')
    if m['state'] != 'active' and req.method == 'POST' and action != 'select':
        raise HTTPException(409, 'This match has ended. View the final match result.')

def race_accuse(sid, c, p, argument):
    # Called within the same BEGIN IMMEDIATE transaction as the route guard.
    with db() as conn:
        m = member(conn, c['match_id'], sid)
        if m['state'] != 'active': raise HTTPException(409, 'This match is not accepting accusations.')
        result = validate_accusation(c, p, argument)
        p['argument'] = argument
        if result['accepted']:
            changed = conn.execute("UPDATE matches SET winner=?, state='completed' WHERE id=? AND winner IS NULL AND state='active'", (sid, m['id'])).rowcount
            if changed != 1: raise HTTPException(409, 'Another valid accusation already won.')
            p['solved'] = True
        put(sid, c, p)
        return result | {'match': public(member(conn, m['id'], sid), sid)}

class CreateMatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    setting: str = 'manor'
    genre: str = 'murder'
    request_key: str = Field(min_length=16, max_length=100)

class JoinMatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    seed: int = Field(ge=0, le=4294967295, strict=True)
    invite_key: str = Field(min_length=16, max_length=100)

def register(app):
    @app.get('/api/matches')
    @atomic
    def list_matches(req: Request):
        sid = owner(req)
        with db() as conn:
            rows = conn.execute('SELECT * FROM matches WHERE p1=? OR p2=? ORDER BY rowid DESC', (sid, sid)).fetchall()
            return {'matches': [public(m, sid) for m in rows]}

    @app.post('/api/matches')
    @atomic
    def create_match(body: CreateMatch, req: Request):
        sid = owner(req)
        with db() as conn:
            old = conn.execute('SELECT * FROM matches WHERE p1=? AND request_key=?', (sid, body.request_key)).fetchone()
            if old: return public(old, sid)
            # One ongoing race per session avoids accidental double-click/new-tab duplicates.
            old = conn.execute("SELECT * FROM matches WHERE (p1=? OR p2=?) AND state IN ('waiting','active')", (sid, sid)).fetchone()
            if old: return public(old, sid)
            while True:
                seed = secrets.randbelow(4294967296)
                reserved = conn.execute('SELECT 1 FROM matches WHERE seed=?', (seed,)).fetchone()
                previously_authored = conn.execute("SELECT 1 FROM cases WHERE json_extract(data, '$.seed')=? LIMIT 1", (seed,)).fetchone()
                if not reserved and not previously_authored: break
            try:
                c = certify(generate(seed, body.setting, body.genre, 'mixed'))
                if not c['report']['playable']:
                    c, _ = correct(c)
                    certify(c)
            except ValueError as e: raise HTTPException(422, str(e))
            if not c['report']['playable']: raise HTTPException(409, 'The race draft failed verification. Create another match.')
            mid = secrets.token_hex(16)
            c['id'] = 'race-' + mid
            c['match_id'] = mid
            put(sid, c, fresh_progress())
            conn.execute('INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                         (mid, seed, c['id'], sid, None, secrets.token_urlsafe(24), 'waiting', None, time.time(), None, body.request_key))
            return public(member(conn, mid, sid), sid)

    @app.post('/api/matches/join')
    @atomic
    def join_match(body: JoinMatch, req: Request):
        sid = owner(req)
        with db() as conn:
            m = conn.execute('SELECT * FROM matches WHERE seed=?', (body.seed,)).fetchone()
            if not m or not secrets.compare_digest(m['invitation'], body.invite_key):
                raise HTTPException(404, 'No match found for that seed and invitation key.')
            if sid in [m['p1'], m['p2']]: return public(m, sid)
            if m['state'] != 'waiting' or m['p2']:
                raise HTTPException(409, 'This match is full, completed, or cancelled.')
            other = conn.execute("SELECT 1 FROM matches WHERE (p1=? OR p2=?) AND state IN ('waiting','active')", (sid, sid)).fetchone()
            if other: raise HTTPException(409, 'Finish or leave your existing match before joining another.')
            c, _ = get(m['p1'], m['case_id'])
            put(sid, c, fresh_progress())
            conn.execute("UPDATE matches SET p2=?, seen2=?, state='active' WHERE id=?", (sid, time.time(), m['id']))
            return public(member(conn, m['id'], sid), sid)

    @app.post('/api/matches/{mid}/heartbeat')
    @atomic
    def heartbeat(mid: str, req: Request):
        sid = owner(req)
        with db() as conn:
            m = member(conn, mid, sid)
            field = 'seen1' if sid == m['p1'] else 'seen2'
            conn.execute(f'UPDATE matches SET {field}=? WHERE id=?', (time.time(), mid))
            return public(member(conn, mid, sid), sid)

    @app.post('/api/matches/{mid}/leave')
    @atomic
    def leave(mid: str, req: Request):
        sid = owner(req)
        with db() as conn:
            m = member(conn, mid, sid)
            # Only a proven accusation wins; leaving cancels instead of granting an unproven victory.
            if m['state'] in ['waiting', 'active']:
                conn.execute("UPDATE matches SET state='cancelled' WHERE id=?", (mid,))
            return public(member(conn, mid, sid), sid)
