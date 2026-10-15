from copy import deepcopy
import pytest
import networkx as nx
from backend.engine import generate, verify, correct, graph, infer, discoverable, validate_accusation

def argument(c, alternate=False):
    means = 'possession' if c['genre'] == 'theft' else 'means'
    alt = next(p for p in c['people'] if p['id'] != c['culprit'])
    evidence = {'motive': ['letter' if alternate else 'will'], means: ['bottle' if alternate else 'glass'], 'opportunity': ['footprint' if alternate else 'key'], 'timeline': ['clock']}
    return {'suspect': c['culprit'], 'claims': [{'category': k, 'evidence': v, 'relation': {'timeline': 'establishes timeline', 'opportunity': 'establishes opportunity'}.get(k, 'supports'), 'explanation': ''} for k, v in evidence.items()], 'challenge': {'strongest': evidence[means][0], 'conflict': {'claim': 'statement', 'evidence': 'log', 'resolution': 'independent_record'}, 'alternative': {'suspect': alt['id'], 'evidence': 'alibi-' + alt['id'][-1]}, 'assumption': {'kind': 'access_is_not_action', 'evidence': evidence[means][0]}}}

def progress(c): return {'found': [x['id'] for x in c['clues']]}

@pytest.mark.parametrize('setting', ['manor','train','museum'])
@pytest.mark.parametrize('genre', ['murder','theft','sabotage'])
def test_generated_seeds_are_reproducible_playable_and_have_multiple_paths(setting, genre):
    for seed in range(12):
        c = generate(seed, setting, genre)
        assert generate(seed, setting, genre) == c
        r = verify(c)
        assert r['playable'], r
        assert r['route_count'] > 1
        assert isinstance(graph(c), nx.DiGraph)
        assert validate_accusation(c, progress(c), argument(c))['accepted']
        assert validate_accusation(c, progress(c), argument(c, True))['accepted']

@pytest.mark.parametrize('fault,check', [('missing','missing_prerequisites'),('cycle','missing_prerequisites'),('contradiction','contradictions'),('timeline','contradictions'),('unreachable','unreachable_conclusions')])
def test_rejections_and_targeted_corrections(fault, check):
    c = generate(10, fault=fault); original = deepcopy(c); r = verify(c)
    assert not r['playable']
    assert any(x['check'] == check and x['suggestion'] for x in r['issues'])
    assert not validate_accusation(c, progress(c), argument(c))['accepted']
    fixed, changes = correct(c)
    assert changes and fixed['id'] != c['id'] and c == original
    assert fixed['people'] == c['people'] and fixed['culprit'] == c['culprit']
    assert verify(fixed)['playable']

def test_graph_edge_alone_does_not_prove_an_and_rule():
    c = generate()
    c['rules'] = [r for r in c['rules'] if not (r['head'].startswith('means:'))]
    assert nx.has_path(graph(c), 'location-0', c['required_conclusion'])
    assert not verify(c)['playable']

def test_guessed_suspect_and_irrelevant_evidence_rejected():
    c = generate(); p = progress(c)
    assert validate_accusation(c,p,{'suspect':c['culprit']})['status']=='unsupported_guess'
    a = argument(c); a['claims'][0]['evidence']=['telegram']
    assert validate_accusation(c,p,a)['status']=='irrelevant_evidence'

def test_undiscovered_evidence_and_incomplete_theory_rejected():
    c = generate(); a = argument(c); p = progress(c)
    p['found'].remove('glass')
    assert validate_accusation(c,p,a)['status']=='undiscovered_evidence'
    a['challenge']['conflict']['resolution']='ignore'
    assert validate_accusation(c,progress(c),a)['status']=='unaddressed_contradiction'

def test_wrong_suspect_and_invalid_relationship_rejected():
    c=generate(); a=argument(c); a['suspect']=next(p['id'] for p in c['people'] if p['id']!=c['culprit'])
    assert not validate_accusation(c,progress(c),a)['accepted']
    a=argument(c);a['claims'][0]['relation']='contradicts'
    assert validate_accusation(c,progress(c),a)['status']=='invalid_relationship'

def test_missing_prerequisite_in_player_argument():
    c=generate();a=argument(c)
    a['claims'][0]['evidence']=['ledger'];a['claims'][2]['evidence']=['footprint']
    assert validate_accusation(c,progress(c),a)['status']=='incomplete_chain'
    a['claims'][2]['evidence']=['footprint','key']
    assert validate_accusation(c,progress(c),a)['accepted']

def test_intentional_lie_needs_discoverable_resolution():
    c=generate(); assert verify(c)['playable']
    c['rules']=[r for r in c['rules'] if r['head']!='lie-resolved']
    assert any(x['check']=='contradictions' for x in verify(c)['issues'])

def test_unsupported_and_ambiguous_conclusions_rejected():
    c=generate();c['rules'].append({'id':'bad','body':['clock'],'head':c['required_conclusion'],'relation':'derives'})
    assert not verify(c)['playable']
    c=generate();other=next(p['id'] for p in c['people'] if p['id']!=c['culprit'])
    r=deepcopy(next(r for r in c['rules'] if r['head']==c['required_conclusion']));r['head']='guilty:'+other;c['rules'].append(r)
    assert not verify(c)['playable']

def test_discovery_locks_and_exploratory_generation():
    c=generate();assert not discoverable(c,'glass',[]);assert discoverable(c,'glass',['clock'])
    results=[verify(generate(i,fault='mixed'))['playable'] for i in range(30)]
    assert any(results) and not all(results)
