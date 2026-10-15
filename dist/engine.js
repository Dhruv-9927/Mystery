export const suspects=['Evelyn Marsh','Arthur Vale','Clara Finch','Thomas Reed'];
export const clues=[
 {id:'will',name:'An amended will',place:0,kind:'motive',text:'Edmund removed Evelyn from his will this morning. Her inheritance would pass to the town trust.',x:-1.9,z:0.2},
 {id:'glass',name:'The last drink',place:0,kind:'means',text:'The glass smells sharply of bitter almonds. The residue matches the poison in Evelyn’s medicine case.',x:0.2,z:-.1},
 {id:'clock',name:'A stopped pocket watch',place:0,kind:'time',text:'Edmund’s watch broke in his fall. It stopped at 9:20 p.m.',x:1.6,z:.45},
 {id:'letter',name:'A letter never sent',place:0,kind:'motive',text:'“Evelyn, I know about the missing trust money. Tomorrow the accounts go to the police.”',x:-.7,z:.7},
 {id:'key',name:'The brass key',place:1,kind:'opportunity',text:'The study’s only spare key was signed out to Evelyn at 8:55 p.m. It was returned at 9:30.',x:-1.8,z:0},
 {id:'bottle',name:'An empty medicine vial',place:1,kind:'means',text:'A poison vial inside Evelyn’s monogrammed medical bag. Its stopper has the same residue as Edmund’s glass.',x:.2,z:.2},
 {id:'ledger',name:'The trust ledger',place:1,kind:'motive',text:'Three withdrawals carry Evelyn’s signature. Edmund circled them in red ink.',x:1.8,z:.4},
 {id:'footprint',name:'Mud on the threshold',place:1,kind:'opportunity',text:'A narrow boot with a triangular heel repair left a print outside the study. Evelyn’s boots have that repair.',x:-.5,z:1.1},
 {id:'receipt',name:'A railway receipt',place:2,kind:'alibi',text:'The station clerk stamped Arthur’s ticket at 9:18 p.m. The station is twenty minutes from the house.',x:-1.8,z:.3},
 {id:'log',name:'The gatekeeper’s log',place:2,kind:'opportunity',text:'Evelyn entered the east study passage at 9:12 p.m. No one else entered before the alarm.',x:.1,z:.2},
 {id:'telegram',name:'An angry telegram',place:2,kind:'red-herring',text:'Arthur threatened to confront Edmund over a debt. A motive, but his station receipt excludes him from the murder.',x:1.8,z:.3},
 {id:'schedule',name:'The kitchen rota',place:2,kind:'alibi',text:'Clara and Thomas served supper together from 9:00 to 9:30. Six guests corroborate their account.',x:-.4,z:1.2},
 {id:'statement',name:'Evelyn’s statement',place:1,kind:'contradiction',text:'“I never went near the study that evening. I stayed in the garden until half past nine.”',interview:0},
 {id:'witness',name:'Clara’s recollection',place:2,kind:'opportunity',text:'“Evelyn carried the nightcap into the study just after nine. I recognised her blue medical bag.”',interview:2}
];
export const routes=[['will','glass','key'],['letter','bottle','footprint'],['ledger','glass','log']];
export function makeCase(seed=1042,naive=false){
 let n=seed>>>0;const rand=()=>{n=(1664525*n+1013904223)>>>0;return n/4294967296};
 const names=['The Lantern House','The Ashwood Estate','The Midnight Carriage','The Briarwood Will'];
 const title=names[Math.floor(rand()*names.length)];
 const nodes=clues.map(c=>({id:c.id,requires:[],kind:c.kind}));
 const solutionRoutes=routes.map(r=>[...r]);
 if(naive){for(const node of nodes){if(rand()<.16)node.requires=['missing-record'];}if(rand()<.22)nodes[0].requires=['will'];}
 return {seed,title,nodes,routes:solutionRoutes,culprit:suspects[Math.floor(rand()*4)],redHerrings:['telegram'],contradictions:[['statement','log']],candidates:[{id:'culprit',routes:solutionRoutes},{id:'other',routes:[]}]};
}
export function verify(c){
 const ids=new Set(c.nodes.map(n=>n.id)),errors=[],reachable=new Set();
 for(const n of c.nodes)for(const p of n.requires)if(!ids.has(p))errors.push(`${n.id} requires missing ${p}. Restore the record or remove the prerequisite.`);
 let changed=true;while(changed){changed=false;for(const n of c.nodes)if(!reachable.has(n.id)&&n.requires.every(p=>reachable.has(p))){reachable.add(n.id);changed=true;}}
 const blocked=c.nodes.filter(n=>!reachable.has(n.id)&&n.requires.every(p=>ids.has(p)));
 if(blocked.length)errors.push(`Circular or blocked dependencies: ${blocked.map(n=>n.id).join(', ')}.`);
 const validRoutes=c.routes.filter(r=>r.every(id=>reachable.has(id)));
 const justified=validRoutes.filter(r=>['motive','means','opportunity'].every(k=>r.some(id=>c.nodes.find(n=>n.id===id)?.kind===k)));
 if(!justified.length)errors.push('No complete evidence route establishes motive, means and opportunity.');
 const winners=c.candidates.filter(x=>x.routes.some(r=>r.every(id=>reachable.has(id))));
 if(winners.length!==1)errors.push('The solution is not unique.');
 for(const r of c.routes)for(const id of r)if(!ids.has(id))errors.push(`Broken solution route: ${id} is missing. Restore this clue.`);
 for(const [a,b] of c.contradictions)if(!ids.has(a)||!ids.has(b))errors.push(`Unresolved contradiction: ${a} / ${b}.`);
 return {ok:!errors.length,errors,validRoutes:justified,shortest:justified.length?Math.min(...justified.map(r=>r.length)):0,reachable:reachable.size,total:c.nodes.length};
}
export function accuse(person,evidence){
 if(person!==suspects[0])return {ok:false,text:'The evidence does not establish this suspect as the culprit. Revisit the alibis and the study passage.'};
 const missing=['motive','means','opportunity'].filter(k=>!clues.some(c=>evidence.includes(c.id)&&c.kind===k));
 return missing.length?{ok:false,text:`Your case still needs evidence for ${missing.join(' and ')}.`}:{ok:true,text:'Evelyn poisoned Edmund’s nightcap to hide the stolen trust funds. Your evidence establishes motive, means and opportunity.'};
}
