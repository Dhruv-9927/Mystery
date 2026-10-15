import {makeCase,verify,breakCase} from './engine.js';
self.onmessage=({data})=>{const results=Array.from({length:100},(_,i)=>{let c=makeCase(data.seed+i,data.setting);if(data.naive&&i%4!==0)c=breakCase(c,['missing','contradiction','unreachable'][i%3]);return {seed:c.seed,setting:c.setting,result:verify(c)}});self.postMessage(results)};
