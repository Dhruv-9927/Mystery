"""Authoritative generation, Horn proof inference and NetworkX validation."""
from copy import deepcopy
from itertools import product
import hashlib
import json
import random
import networkx as nx

GENERATOR_VERSION = 3
SETTINGS = {
    'manor': {'name': 'Country estate', 'places': ['The private study', 'The east passage', 'The gatehouse'], 'title': 'The Lantern House'},
    'train': {'name': 'Sleeper train', 'places': ['The private compartment', 'The luggage carriage', 'The conductor’s office'], 'title': 'The Midnight Carriage'},
    'museum': {'name': 'Private museum', 'places': ['The curator’s office', 'The restoration room', 'The security lodge'], 'title': 'The Gilded Gallery'},
}
GENRES = {'murder': 'Murder mystery', 'theft': 'Stolen artefact', 'sabotage': 'Deliberate sabotage'}
RELATIONS = ['supports', 'contradicts', 'establishes timeline', 'establishes opportunity', 'weakens an alibi']

def generate(seed=1042, setting='manor', genre='murder', fault='none'):
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 4294967295:
        raise ValueError('Seed must be a whole number from 0 to 4294967295.')
    if setting not in SETTINGS or genre not in GENRES:
        raise ValueError('Unknown setting or mystery type.')
    rng = random.Random(f'{GENERATOR_VERSION}:{setting}:{genre}:{seed}')
    names = rng.choice([['Evelyn Marsh', 'Arthur Vale', 'Clara Finch', 'Thomas Reed'], ['Iris Shaw', 'Benedict Cross', 'Nora Wells', 'Samuel Hart'], ['Ada Sterling', 'Oscar Blake', 'Mabel Stone', 'Henry Fox']])
    culprit = rng.randrange(4)
    person = names[culprit]
    target = rng.choice(['Edmund Voss', 'Felix Ward', 'Cecil Briar'])
    motive = rng.choice(['conceal embezzlement', 'protect a forged inheritance', 'end a blackmail arrangement'])
    hour = rng.randrange(20, 23)
    time = lambda m: f'{hour}:{m:02d}'
    incident = {'murder': f'{target} was killed with a poisoned drink', 'theft': 'the sealed sapphire vanished from its case', 'sabotage': 'the private generator was deliberately disabled'}[genre]
    means = 'possession' if genre == 'theft' else 'means'
    mechanism = {'murder': ('The unfinished drink', 'The medicine vial', 'The laboratory report matches poison in the drink to the registered vial', 'The labelled vial contains the same compound as the fatal drink'), 'theft': ('The packing cloth', 'A hidden jewel box', 'The sapphire’s unique chipped mount left its impression inside the suspect’s packing cloth', 'The missing sapphire was recovered in the suspect’s locked, monogrammed box'), 'sabotage': ('The cut wire', 'The repaired pliers', 'Microscopic tool marks on the severed wire match the suspect’s uniquely damaged pliers', 'A copper fragment in the suspect’s pliers fits the cut cable exactly')}[genre]
    cid = f'v3-{setting}-{genre}-{seed}-r1'
    people = [{'id': f'suspect-{i}', 'name': n, 'role': ['The executor', 'The associate', 'The archivist', 'The caretaker'][i]} for i, n in enumerate(names)]
    rows = [
        ('will', 'The disputed accounts', 0, 'motive', f'{person} needed to {motive}. {target} had signed a report exposing the scheme.'),
        ('letter', 'An unsent letter', 0, 'motive', f'Addressed to {person}, from {target}: “I will expose your scheme tomorrow. The records are already with my solicitor.”'),
        ('ledger', 'A signed admission', 1, 'motive', f'The locked archive contains {person}’s signed admission of the scheme. {target} refused their request for silence.'),
        ('glass', mechanism[0], 0, means, f'{mechanism[2]}. The registered owner is {person}. The timestamp is within the incident window.'),
        ('bottle', mechanism[1], 1, means, f'{mechanism[3]}. The sealed ownership record identifies {person}.'),
        ('key', 'The key register', 1, 'opportunity', f'{person} signed out the only spare private-room key at {time(5)} and returned it at {time(30)}.'),
        ('footprint', 'A distinctive heel print', 1, 'opportunity', f'The private-room threshold carries the triangular heel repair on {person}’s boot. This floor was cleaned at {time(10)}.'),
        ('log', 'The passage record', 2, 'opportunity', f'Two independent timestamped records place {person} inside the private room at {time(12)}, before the incident at {time(20)}.'),
        ('clock', 'The incident-time report', 0, 'timeline', f'The independently authenticated incident record establishes that {incident} at {time(20)}. The access window was {time(5)}–{time(30)}.'),
        ('statement', f'{person.split()[0]}’s statement', 1, 'testimony', f'“I never entered the private room. I was outside from {time(5)} until {time(30)}.” — {person}'),
    ]
    innocent = [i for i in range(4) if i != culprit]
    for i in innocent:
        rows.append((f'alibi-{i}', f'{names[i].split()[0]}’s corroborated alibi', 2, 'alibi', f'{names[i]} was in the public dining area from {time(5)} to {time(30)}, with three independent witnesses and a timestamped receipt. They could not enter the private room during the incident.'))
    rows.append(('telegram', 'A threatening message', 2, 'red-herring', f'{names[innocent[0]]} threatened to confront {target} over a debt. Check their independent alibi before treating a threat as proof.'))
    clues = []
    slots = [0, 0, 0]
    positions = [(-1.9, -.5), (.1, -.45), (1.9, -.1), (-1.1, 1), (1.1, 1)]
    for id, name, place, kind, text in rows:
        x, z = positions[slots[place] % 5]; slots[place] += 1
        clue = {'id': id, 'name': name, 'place': place, 'kind': kind, 'text': text, 'x': x, 'z': z, 'requires': [], 'trusted': kind != 'testimony', 'type': 'clue', 'claims': []}
        if kind in ['motive', means, 'opportunity']:
            clue['claims'] = [f'{kind}:suspect-{culprit}']
        if id == 'clock': clue['claims'] = ['incident-time']
        if id == 'glass': clue['requires'] = ['clock']
        if id == 'ledger': clue['requires'] = ['key']
        if id == 'statement': clue['interview'] = culprit
        if id.startswith('alibi-'):
            clue['interview'] = int(id[-1]); clue['claims'] = [f'excluded:suspect-{id[-1]}']
        clues.append(clue)
    location_key = f'location:suspect-{culprit}:{time(12)}'
    byid = {c['id']: c for c in clues}
    byid['log']['assertion'] = {'key': location_key, 'value': 'private-room'}
    byid['statement']['assertion'] = {'key': location_key, 'value': 'outside'}
    facts = [{'id': f'location-{i}', 'name': name, 'type': 'location', 'source': True} for i, name in enumerate(SETTINGS[setting]['places'])]
    facts += [{**p, 'type': 'suspect', 'source': True} for p in people]
    facts += [{'id': 'incident-time', 'name': 'Incident time established', 'type': 'event'}]
    for p in people:
        facts += [{'id': f'{k}:{p["id"]}', 'name': f'{p["name"]}: {k}', 'type': 'claim', 'category': k, 'suspect': p['id']} for k in ['motive', means, 'opportunity']]
        facts += [{'id': f'excluded:{p["id"]}', 'name': f'{p["name"]}: alibi corroborated', 'type': 'claim', 'suspect': p['id']}, {'id': f'guilty:{p["id"]}', 'name': f'{p["name"]}: responsibility established', 'type': 'conclusion', 'suspect': p['id']}]
    facts += [{'id': 'lie-resolved', 'name': 'The witness account is disproved', 'type': 'claim'}]
    rules = []
    for clue in clues:
        for claim in clue['claims']: rules.append({'id': f'r-{clue["id"]}-{claim}', 'body': [clue['id']], 'head': claim, 'relation': 'supports'})
    for p in people:
        rules.append({'id': f'conclude-{p["id"]}', 'body': [f'{k}:{p["id"]}' for k in ['motive', means, 'opportunity']] + ['incident-time'], 'head': f'guilty:{p["id"]}', 'relation': 'derives'})
    rules.append({'id': 'resolve-account', 'body': ['statement', 'log'], 'head': 'lie-resolved', 'relation': 'contradicts'})
    case = {'id': cid, 'root_id': cid[:-2], 'version': 1, 'generator_version': GENERATOR_VERSION, 'seed': seed, 'setting': setting, 'genre': genre, 'title': f'{SETTINGS[setting]["title"]} — {GENRES[genre]}', 'victim': target, 'people': people, 'places': SETTINGS[setting]['places'], 'clues': clues, 'facts': facts, 'rules': rules, 'culprit': f'suspect-{culprit}', 'required_conclusion': f'guilty:suspect-{culprit}', 'truth': {location_key: 'private-room'}, 'constraints': [{'type': 'time_window', 'start': hour * 60 + 5, 'event': hour * 60 + 20, 'end': hour * 60 + 30}], 'contradictions': [{'a': 'statement', 'b': 'log', 'resolution': 'lie-resolved', 'intentional': True}], 'requirements': ['motive', means, 'opportunity', 'timeline'], 'brief': f'At {time(20)}, {incident}. Four people had access to the premises. Establish a justified conclusion using evidence, not a guess.', 'solution': f'{person} was responsible and acted to {motive}. Independent records establish motive, {means}, opportunity and the incident time.', 'timeline': [{'time': time(5), 'clue': 'key', 'text': 'The private-room key is collected.'}, {'time': time(12), 'clue': 'log', 'text': 'An entry into the private room is recorded.'}, {'time': time(20), 'clue': 'clock', 'text': 'The incident occurs.'}], 'state': 'draft', 'corrections': []}
    if fault == 'mixed': fault = rng.choice(['none', 'missing', 'contradiction', 'unreachable', 'timeline'])
    case['fault'] = fault
    if fault == 'missing': byid['glass']['requires'].append('missing-lab-report')
    elif fault == 'contradiction': byid['log']['assertion']['value'] = 'outside'
    elif fault == 'unreachable': case['rules'] = [r for r in rules if r['head'] != case['required_conclusion']]
    elif fault == 'timeline': case['constraints'][0]['event'] = hour * 60 + 40
    elif fault == 'cycle': byid['key']['requires'] = ['ledger']
    elif fault not in ['none']: raise ValueError('Unknown fault mode.')
    return case

def graph(case):
    g = nx.DiGraph()
    for n in case['facts'] + case['clues']: g.add_node(n['id'], **n)
    for c in case['clues']:
        source = f'suspect-{c["interview"]}' if 'interview' in c else f'location-{c["place"]}'
        for p in [source] + c['requires']: g.add_edge(p, c['id'], relation='depends on')
    for r in case['rules']:
        for p in r['body']: g.add_edge(p, r['head'], relation=r['relation'], rule=r['id'])
    return g

def minimal(paths):
    ordered = sorted(set(frozenset(p) for p in paths), key=lambda p: (len(p), sorted(p)))
    result = []
    for p in ordered:
        if not any(q <= p for q in result): result.append(p)
    return result

def combine(groups):
    if any(not group for group in groups): return []
    if not groups: return [frozenset()]
    return minimal(frozenset().union(*items) for items in product(*groups))

def infer(case, available=None):
    """Least-fixed-point Horn inference; each proof retains its clue provenance."""
    proof = {n['id']: [] for n in case['facts'] + case['clues']}
    for n in case['facts']:
        if n.get('source'): proof[n['id']] = [frozenset()]
    for _ in range(len(proof) + 1):
        before = deepcopy(proof)
        for c in case['clues']:
            if available is not None and c['id'] not in available: continue
            source = f'suspect-{c["interview"]}' if 'interview' in c else f'location-{c["place"]}'
            paths = combine([proof.get(p, []) for p in [source] + c['requires']])
            proof[c['id']] = minimal(proof[c['id']] + [p | {c['id']} for p in paths])
        for r in case['rules']:
            proof[r['head']] = minimal(proof.get(r['head'], []) + combine([proof.get(p, []) for p in r['body']]))
        if before == proof: break
    return proof

def verify(case):
    g = graph(case); proof = infer(case); issues = []
    defined = {n['id'] for n in case['facts'] + case['clues']}
    def fail(check, ids, explanation, suggestion, path=None):
        issues.append({'check': check, 'node_ids': ids, 'explanation': explanation, 'suggestion': suggestion, 'dependency_path': path or ids})
    for n in set(g) - defined:
        users = list(g.successors(n)); fail('missing_prerequisites', [n] + users, f'Undefined prerequisite {n} is required by {", ".join(users)}.', 'Restore a legitimate source record or repair the erroneous prerequisite.')
    for component in nx.strongly_connected_components(g):
        if len(component) > 1 or any(g.has_edge(n, n) for n in component):
            fail('missing_prerequisites', sorted(component), 'Circular dependencies prevent an independent starting point.', 'Replace the circular dependency with a discoverable source.')
    sources = [n['id'] for n in case['facts'] if n.get('source')]
    reachable = set(sources)
    for s in sources: reachable.update(nx.descendants(g, s))
    for c in case['clues']:
        if c['id'] not in reachable or not proof.get(c['id']):
            fail('missing_prerequisites', [c['id']], f'{c["name"]} has no satisfiable discovery path.', 'Repair all prerequisites, including AND conditions; a graph edge alone is not a proof.', c['requires'] + [c['id']])
    trusted = [c for c in case['clues'] if c.get('trusted') and c.get('assertion')]
    for c in trusted:
        a = c['assertion']; expected = case['truth'].get(a['key'])
        if expected is not None and a['value'] != expected:
            fail('contradictions', [c['id']], f'Trusted fact {a["key"]} says {a["value"]}, but the timeline establishes {expected}.', 'Reconcile the trusted assertion with the authoritative event record.')
        for other in trusted:
            if other['id'] < c['id'] and other['assertion']['key'] == a['key'] and other['assertion']['value'] != a['value']:
                fail('contradictions', [other['id'], c['id']], 'Two trusted observations establish incompatible values.', 'Correct the inconsistent observation, preserving the constraint.')
    for constraint in case['constraints']:
        if constraint['type'] == 'time_window' and not constraint['start'] <= constraint['event'] <= constraint['end']:
            fail('contradictions', ['incident-time'], f'Event time {constraint["event"]} is outside the permitted interval {constraint["start"]}–{constraint["end"]}.', 'Restore the event timestamp from the independent incident record.')
    for c in case['clues']:
        if not c['trusted'] and c.get('assertion') and c['assertion']['value'] != case['truth'].get(c['assertion']['key']):
            conflict = next((x for x in case['contradictions'] if c['id'] in [x['a'], x['b']] and x['intentional']), None)
            if not conflict or not proof.get(conflict['resolution']): fail('contradictions', [c['id']], 'An intentional lie has no discoverable disproof.', 'Provide the independent contradictory record and its resolution rule.')
    paths = proof.get(case['required_conclusion'], [])
    candidates = [n for n in case['facts'] if n['type'] == 'conclusion' and proof.get(n['id'])]
    if not paths:
        fail('unreachable_conclusions', [case['required_conclusion']], 'No Horn-rule proof establishes the intended conclusion.', 'Restore a rule requiring supported case-specific claims and incident time.')
    if len(candidates) != 1:
        fail('unreachable_conclusions', [n['id'] for n in candidates], f'{len(candidates)} suspects have provable conclusions; one justified solution is required.', 'Repair ambiguity or unsupported conclusions using evidence, not the intended answer.')
    for conclusion in candidates:
        who = conclusion['suspect']
        for path in proof[conclusion['id']]:
            cited = [c for c in case['clues'] if c['id'] in path]
            for category in case['requirements']:
                claim = 'incident-time' if category == 'timeline' else f'{category}:{who}'
                if not any(c['trusted'] and claim in c['claims'] for c in cited):
                    fail('unreachable_conclusions', [conclusion['id']], f'A proof omits supported {category}.', f'Require an evidence-backed {category} intermediate fact.')
    checks = [{'id': k, 'name': name, 'passed': not any(x['check'] == k for x in issues)} for k, name in [('missing_prerequisites', 'Missing prerequisites & discovery'), ('contradictions', 'Contradictions & timeline constraints'), ('unreachable_conclusions', 'Reachable, justified, unique conclusion')]]
    return {'status': 'verified' if not issues else 'rejected', 'playable': not issues, 'checks': checks, 'issues': issues, 'paths': [sorted(p) for p in paths], 'route_count': len(paths), 'shortest': min(map(len, paths), default=0), 'node_count': g.number_of_nodes(), 'edge_count': g.number_of_edges(), 'networkx_version': nx.__version__}

def correct(case):
    """Propose only changed records; keep rejected source and create a new revision."""
    baseline = generate(case['seed'], case['setting'], case['genre'])
    fixed = deepcopy(case); changes = []
    def change(target, old, new, explanation):
        changes.append({'target': target, 'before': old, 'after': new, 'explanation': explanation})
    for c in fixed['clues']:
        canonical = next(n for n in baseline['clues'] if n['id'] == c['id'])
        for field in ['requires', 'assertion']:
            if c.get(field) != canonical.get(field):
                change(c['id'] + '.' + field, c.get(field), canonical.get(field), 'Restore this record from the deterministic case source; retain all checks and the original premise.')
                if field in canonical: c[field] = deepcopy(canonical[field])
                else: c.pop(field, None)
    if fixed['constraints'] != baseline['constraints']:
        change('timeline constraints', fixed['constraints'], baseline['constraints'], 'Use the independently recorded incident time.'); fixed['constraints'] = deepcopy(baseline['constraints'])
    byid = {r['id']: r for r in fixed['rules']}
    for r in baseline['rules']:
        if byid.get(r['id']) != r:
            change(r['id'], byid.get(r['id']), r, 'Restore the evidence-backed Horn rule, including all required intermediate facts.')
            fixed['rules'] = [x for x in fixed['rules'] if x['id'] != r['id']] + [deepcopy(r)]
    fixed['version'] += 1; fixed['id'] = case['id'].rsplit('-r', 1)[0] + f'-r{fixed["version"]}'
    fixed['parent_id'] = case['id']; fixed['corrections'] = changes; fixed['fault'] = 'none'; fixed['state'] = 'draft'
    return fixed, changes

def discoverable(case, clue_id, found):
    c = next((c for c in case['clues'] if c['id'] == clue_id), None)
    return bool(c) and all(infer(case, found).get(p) for p in c['requires'])

def validate_accusation(case, progress, argument):
    def reject(status, message, fields=None): return {'accepted': False, 'status': status, 'message': message, 'fields': fields or []}
    report = verify(case)
    if not report['playable']:
        proven = infer(case)
        if sum(bool(proven.get(n['id'])) for n in case['facts'] if n['type'] == 'conclusion') > 1:
            return reject('ambiguous_theory', 'This draft supports more than one suspect. The author must resolve its ambiguity before play.')
        return reject('case_rejected', 'This draft must pass verification before an accusation can be considered.')
    suspect = argument.get('suspect'); claims = argument.get('claims', [])
    if suspect not in {p['id'] for p in case['people']}: return reject('invalid_suspect', 'Choose a suspect from this case.')
    if not claims: return reject('unsupported_guess', 'A selected suspect is not a proof. Build the required claims from discovered records.')
    lookup = {c['id']: c for c in case['clues']}
    cited = set()
    required = set(case['requirements'])
    for claim in claims:
        category = claim.get('category'); evidence = claim.get('evidence', [])
        if category not in required or not evidence: return reject('unsupported_claim', 'Each required claim needs supporting discovered evidence.', [str(category)])
        fact = 'incident-time' if category == 'timeline' else f'{category}:{suspect}'
        for id in evidence:
            if id not in progress['found']: return reject('undiscovered_evidence', 'An accusation cites evidence not yet discovered in this case.', [id])
            if id in lookup and not lookup[id]['trusted'] and lookup[id].get('assertion'):
                return reject('contradictory_theory', 'An uncorroborated witness account conflicts with the independent record. It cannot establish this positive claim.', [id])
            if id not in lookup or fact not in lookup[id]['claims'] or not lookup[id]['trusted']:
                if id in lookup and any(x.startswith(category + ':') for x in lookup[id]['claims']):
                    return reject('incorrect_accusation', 'This evidence supports the claim for a different person, not the accused. Reconsider the suspect or the argument.', [id, category])
                return reject('irrelevant_evidence', f'The selected record does not establish {category} for this suspect. Access alone does not establish responsibility.', [id, category])
        expected_relation = {'timeline': 'establishes timeline', 'opportunity': 'establishes opportunity'}.get(category, 'supports')
        if claim.get('relation') != expected_relation: return reject('invalid_relationship', f'This claim needs the relationship “{expected_relation}”.', [category])
        cited.update(evidence)
    missing = required - {x.get('category') for x in claims}
    if missing: return reject('incomplete_argument', 'Your argument still needs: ' + ', '.join(sorted(missing)), sorted(missing))
    supporting = infer(case, cited)
    if not supporting.get(f'guilty:{suspect}'): return reject('incomplete_chain', 'The conclusion does not follow. Include prerequisite records and the required intermediate facts.')
    challenge = argument.get('challenge', {})
    if challenge.get('strongest') not in cited: return reject('challenge_required', 'Identify your strongest supporting record from your argument.')
    conflict = challenge.get('conflict', {})
    if not {'statement', 'log'} <= set(progress['found']): return reject('unaddressed_contradiction', 'Recover and compare the relevant witness account with an independent record before resolving the contradiction.')
    if conflict.get('claim') != 'statement' or conflict.get('evidence') != 'log' or conflict.get('resolution') != 'independent_record':
        return reject('unaddressed_contradiction', 'Address the conflicting witness account using an independent record and a valid resolution.')
    alternative = challenge.get('alternative', {})
    alt = alternative.get('suspect'); evidence = alternative.get('evidence')
    if alt == suspect or alt not in {p['id'] for p in case['people']} or evidence not in progress['found'] or f'excluded:{alt}' not in lookup.get(evidence, {}).get('claims', []):
        return reject('alternative_unaddressed', 'Consider a different suspect and cite their independently corroborated alibi.')
    assumption = challenge.get('assumption', {})
    if assumption.get('kind') != 'access_is_not_action' or assumption.get('evidence') not in cited or not any(k.startswith(('means:', 'possession:')) for k in lookup.get(assumption.get('evidence'), {}).get('claims', [])):
        return reject('assumption_unaddressed', 'Address why access alone is insufficient; cite separate evidence of means or possession.')
    return {'accepted': True, 'status': 'justified_conclusion', 'message': case['solution'], 'proof': sorted(supporting[f'guilty:{suspect}'][0])}
