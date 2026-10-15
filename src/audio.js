const read=(k,f)=>{try{return JSON.parse(localStorage.getItem(k)??JSON.stringify(f))}catch{return f}};
export class GameAudio{
 constructor(){this.enabled=read('case101-sound',true);this.effects=read('case101-effects',true);this.audio=new Audio('/assets/ambience.mp3');this.audio.loop=true;this.audio.volume=.28;this.audio.preload='metadata';this.unlocked=false;this.last=0;}
 async unlock(){this.unlocked=true;if(this.enabled){try{await this.audio.play();return true}catch{return false}}return true}
 async toggle(){this.enabled=!this.enabled;try{localStorage.setItem('case101-sound',JSON.stringify(this.enabled))}catch{}if(this.enabled)return this.unlock();this.audio.pause();return true}
 toggleEffects(){this.effects=!this.effects;try{localStorage.setItem('case101-effects',JSON.stringify(this.effects))}catch{}}
 effect(kind='paper'){if(!this.enabled||!this.effects||!this.unlocked||performance.now()-this.last<100)return;this.last=performance.now();try{this.ctx??=new AudioContext();this.ctx.resume();const ctx=this.ctx,duration=kind==='pin'?.08:.17,b=ctx.createBuffer(1,Math.ceil(ctx.sampleRate*duration),ctx.sampleRate),d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/d.length,2);const src=ctx.createBufferSource(),filter=ctx.createBiquadFilter(),gain=ctx.createGain();filter.type='bandpass';filter.frequency.value=kind==='pin'?850:2400;gain.gain.value=.055;src.buffer=b;src.connect(filter);filter.connect(gain);gain.connect(ctx.destination);src.start()}catch{}}
}
