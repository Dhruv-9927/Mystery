import assert from 'node:assert/strict';import {makeCase,verify,accuse,clues,suspects} from './dist/engine.js';
for(let seed=0;seed<1000;seed++){const c=makeCase(seed);assert.deepEqual(c,makeCase(seed));assert.equal(verify(c).ok,true)}
const broken=makeCase();broken.nodes=broken.nodes.filter(n=>n.id!=='glass');assert.equal(verify(broken).ok,false);assert.match(verify(broken).errors.join(' '),/glass/);
const cyclic=makeCase();cyclic.nodes[0].requires=['will'];assert.equal(verify(cyclic).ok,false);
const ambiguous=makeCase();ambiguous.candidates[1].routes=[['will','glass','key']];assert.equal(verify(ambiguous).ok,false);
assert.equal(accuse(suspects[0],['will','glass','key']).ok,true);assert.equal(accuse(suspects[0],['will']).ok,false);assert.equal(accuse(suspects[1],clues.map(c=>c.id)).ok,false);
const naive=Array.from({length:100},(_,i)=>verify(makeCase(1000+i,true)));assert(naive.some(r=>!r.ok));assert(naive.some(r=>r.ok));console.log('Passed: 1,000 seeded cases, determinism, missing evidence, cycles, ambiguity, accusation rules and naive-generator failures.');
