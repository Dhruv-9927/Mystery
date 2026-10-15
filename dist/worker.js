import {makeCase,verify} from './engine.js';
self.onmessage=({data})=>self.postMessage(Array.from({length:100},(_,i)=>{const c=makeCase(1000+i,data.naive);return {seed:c.seed,result:verify(c)}}));
