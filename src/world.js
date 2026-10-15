import * as THREE from 'three';
export function mountWorld(){
const $=s=>document.querySelector(s);let view='archive',place=0,clues=[];function render(){} function drawLinks(){}
const scene=new THREE.Scene();scene.background=new THREE.Color('#2b211b');scene.fog=new THREE.Fog('#2b211b',20,48);
const renderer=new THREE.WebGLRenderer({canvas:$('#world'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.95;
const camera=new THREE.PerspectiveCamera(38,innerWidth/innerHeight,.1,100);camera.position.set(13,11,17);
const target=new THREE.Vector3(0,1.5,0),camGoal=new THREE.Vector3(13,11,17),lookGoal=new THREE.Vector3(0,1.5,0);
scene.add(new THREE.HemisphereLight('#eadfc1','#223d31',2.3));const sun=new THREE.DirectionalLight('#ffe0a0',3.5);sun.position.set(-4,12,5);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-15,right:15,top:15,bottom:-15});scene.add(sun);
const material=(color)=>new THREE.MeshStandardMaterial({color,roughness:.88,flatShading:true});const mats={wood:material('#513e2b'),edge:material('#302b23'),floor:material('#655f43'),wall:material('#566251'),paper:material('#c7b88b'),metal:material('#b0a176'),red:material('#8f4839'),green:material('#607357'),black:material('#26352e'),blue:material('#536c6b')};
function box(w,h,d,mat,x=0,y=0,z=0,parent=scene){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),typeof mat==='string'?material(mat):mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
function cyl(r1,r2,h,mat,x,y,z,parent=scene,n=8){const m=new THREE.Mesh(new THREE.CylinderGeometry(r1,r2,h,n),mat);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
function label(text,w,h,x,y,z,parent,fg='#c8c6a7',bg='#293b2e',size=44){const canvas=document.createElement('canvas');canvas.width=512;canvas.height=256;const c=canvas.getContext('2d');c.fillStyle=bg;c.fillRect(0,0,512,256);c.strokeStyle=fg;c.lineWidth=3;c.strokeRect(12,12,488,232);c.fillStyle=fg;c.textAlign='center';c.textBaseline='middle';c.font=`${size}px Georgia`;text.split('\n').forEach((t,i,a)=>c.fillText(t,256,128+(i-(a.length-1)/2)*60));const t=new THREE.CanvasTexture(canvas);t.colorSpace=THREE.SRGBColorSpace;const m=new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshStandardMaterial({map:t,roughness:1}));m.position.set(x,y,z);parent.add(m);return m}
const office=new THREE.Group();scene.add(office);
box(18,.3,15,mats.floor,0,-.2,0,office);for(let x=-8.5;x<9;x+=.85)box(.025,.012,15,'#373d2e',x,-.04,0,office);
box(18,8,.3,mats.wall,0,4,-6,office);box(.3,8,15,mats.wall,-9,4,1.3,office);
for(let x=-8;x<=8;x+=1.2)box(.06,2.3,.15,mats.edge,x,1.15,-5.78,office);box(18,.15,.25,mats.wood,0,2.3,-5.7,office);
// A luminous rain-dark window, framed in heavy timber.
box(4.6,4.5,.18,mats.edge,3.8,4.6,-5.7,office);box(4.2,4.1,.2,'#a5b3a0',3.8,4.6,-5.55,office);box(.13,4.3,.25,mats.edge,3.8,4.6,-5.35,office);box(4.3,.13,.25,mats.edge,3.8,4.6,-5.35,office);
for(let i=0;i<6;i++)box(.65,.07,3.8,'#acb798',1.9+i*.65,.012,-2.5,office).rotation.y=-.35;
// Bookcase with individual low-poly volumes.
box(3.5,5.7,.85,mats.edge,-5.9,2.85,-5.2,office);for(let y=.5;y<5.8;y+=1.3){box(3.5,.12,1,mats.wood,-5.9,y,-5,office);for(let i=0;i<10;i++){const b=box(.19,.6+(i%3)*.14,.5,[mats.green,mats.red,mats.paper,mats.blue][i%4],-7.3+i*.3,y+.5,-4.95,office);b.rotation.z=(i%4===0?.12:0);}}
// Framed evidence board on the back wall.
box(4,2.65,.2,mats.edge,-1.1,4.45,-5.7,office);box(3.75,2.4,.23,'#897655',-1.1,4.45,-5.5,office);
for(let i=0;i<7;i++){const p=box(.65,.8,.035,mats.paper,-2.3+(i%4)*.8,4+(i%2)*.9,-5.35,office);p.rotation.z=(i%3-1)*.1;cyl(.04,.04,.05,mats.red,p.position.x,p.position.y+.3,-5.28,office).rotation.x=Math.PI/2;}
const points=[[-2.3,4.3],[-1.5,5.2],[-.7,4.3],[.1,5.2],[-2.3,4.3],[-.7,4.3]];const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(p[0],p[1],-5.25))),new THREE.LineBasicMaterial({color:'#b9533d'}));office.add(line);
// Desk, drawer, case folders and desk accessories.
const desk=new THREE.Group();office.add(desk);box(7,.3,3.5,mats.wood,0,2.5,0,desk);box(7.2,.12,3.65,'#6b5135',0,2.7,0,desk);
for(const x of [-2.7,2.7]){box(1.4,2.4,2.8,mats.edge,x,1.2,0,desk);for(let i=0;i<3;i++){box(1.28,.64,.12,mats.wood,x,.5+i*.72,1.43,desk);box(.4,.06,.12,mats.metal,x,.5+i*.72,1.54,desk)}}
box(3.8,.03,2.3,'#3f5141',0,2.78,.1,desk);
for(let i=0;i<5;i++){const f=box(1.45,.06,1,mats.paper,-.9+i*.12,2.84+i*.065,.3-i*.13,desk);f.rotation.y=-.15;box(.4,.05,.2,mats.paper,-1.3+i*.12,2.87+i*.065,-.28-i*.13,desk)}
const folderLabel=label('CASE 101\nINVESTIGATION FILE',1.1,.55,-.4,3.19,-.15,desk,'#354337','#cab88a',37);folderLabel.rotation.x=-Math.PI/2;
cyl(.45,.55,.12,mats.black,-2.5,2.84,-.8,desk);cyl(.045,.045,1.6,mats.metal,-2.5,3.65,-.8,desk);const shade=cyl(.35,.7,.4,mats.green,-2.5,4.45,-.8,desk);const lamp=new THREE.PointLight('#ffcf7d',18,7,2);lamp.position.set(-2.5,4.1,-.8);desk.add(lamp);
box(1.15,.2,.8,mats.black,1.8,2.9,-.6,desk);box(1,.45,.2,mats.black,1.8,3.15,-.9,desk);box(.8,.5,.02,mats.paper,1.8,3.4,-.93,desk);for(let a=0;a<3;a++)for(let b=0;b<8;b++)cyl(.032,.032,.03,mats.metal,1.43+b*.1,3.03,-.43+a*.12,desk);
cyl(.18,.15,.35,mats.paper,2.8,3,.8,desk);cyl(.15,.15,.015,mats.edge,2.8,3.18,.8,desk);
box(1.6,.2,1.5,mats.green,0,1.3,-2.5,office);box(1.6,1.6,.25,mats.green,0,2.1,-3.15,office);for(const x of [-.6,.6])for(const z of [-3,-2])box(.12,1.3,.12,mats.edge,x,.65,z,office);
// A coat stand and faceted hanging overcoat.
cyl(.06,.08,5,mats.wood,6.6,2.5,-3.9,office);cyl(.6,.7,.15,mats.edge,6.6,.1,-3.9,office);box(1.3,.08,.12,mats.wood,6.6,4.4,-3.9,office);cyl(.35,.6,2.1,mats.blue,6.6,3.2,-3.8,office,5);cyl(.55,.55,.07,mats.edge,6.6,4.8,-3.8,office);cyl(.3,.35,.35,mats.edge,6.6,5,-3.8,office);
// Searchable room props. Locations share the mansion's architecture and change their set dressing.
const investigation=new THREE.Group();scene.add(investigation);investigation.visible=false;const markers=[];
function setPlace(p){place=p;while(investigation.children.length)investigation.remove(investigation.children[0]);markers.length=0;desk.visible=false;
 box(6.5,.25,3.4,mats.wood,0,2.5,.1,investigation);for(const x of [-2.8,2.8])for(const z of [-1.2,1.4])box(.18,2.5,.18,mats.edge,x,1.25,z,investigation);
 clues.filter(c=>c.place===p&&!('interview'in c)).forEach((c,i)=>{const x=c.x,y=2.7,z=c.z;if(['glass','bottle'].includes(c.id)){cyl(.14,.19,.6,c.id==='glass'?mats.metal:mats.green,x,y+.3,z,investigation);cyl(.08,.08,.15,mats.edge,x,y+.67,z,investigation)}else if(c.id==='clock'){cyl(.24,.24,.08,mats.metal,x,y+.06,z,investigation)}else if(c.id==='key'){box(.48,.04,.09,mats.metal,x,y+.04,z,investigation);cyl(.11,.11,.04,mats.metal,x-.25,y+.04,z,investigation)}else{const b=box(.7,.04,.55,mats.paper,x,y+.04,z,investigation);b.rotation.y=(i-1)*.15;for(let j=0;j<4;j++)box(.45,.006,.014,mats.edge,x,y+.065,z-.15+j*.08,investigation)}markers.push({clue:c,pos:new THREE.Vector3(x,y+.5,z)});});
 if(p===1){box(1,.8,.7,mats.blue,2.6,3.1,-1,investigation);box(.5,.12,.12,mats.metal,2.6,3.55,-1,investigation)}
 if(p===2){cyl(.35,.45,1,mats.black,-2.6,3.3,-.9,investigation);const l=new THREE.PointLight('#ffd68d',9,5);l.position.set(-2.6,4,-.9);investigation.add(l)}
 render();}
function resize(){renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();drawLinks()}addEventListener('resize',resize);resize();
let frame;let disposed=false;function animate(){if(disposed)return;frame=requestAnimationFrame(animate);camera.position.lerp(camGoal,.035);target.lerp(lookGoal,.035);camera.lookAt(target);renderer.render(scene,camera);if(view==='scene'){markers.forEach(({clue,pos})=>{const el=document.getElementById('hot-'+clue.id);if(!el)return;const v=pos.clone().project(camera);el.style.left=(v.x*.5+.5)*innerWidth+'px';el.style.top=(-v.y*.5+.5)*innerHeight+'px';});const placed=[];markers.forEach(({clue})=>{const el=document.getElementById('hot-'+clue.id);if(!el)return;let x=parseFloat(el.style.left),y=parseFloat(el.style.top);const w=el.offsetWidth,h=el.offsetHeight;x=Math.max(w/2+12,Math.min(innerWidth-w/2-12,x));for(let k=0;k<8;k++){if(!placed.some(r=>Math.abs(x-r.x)<(w+r.w)/2+8&&Math.abs(y-r.y)<(h+r.h)/2+8))break;y+=h+8}el.style.left=x+'px';el.style.top=y+'px';placed.push({x,y,w,h})})}}animate();

const setDressing=new THREE.Group();scene.add(setDressing);
function configureWorld(c){clues=c.clues;while(setDressing.children.length)setDressing.remove(setDressing.children[0]);
 if(c.setting==='train'){for(let i=0;i<4;i++){box(1.5,1.8,.2,mats.edge,-5+i*3.1,4.5,-4.3,setDressing);box(1.25,1.55,.22,'#64777a',-5+i*3.1,4.5,-4.15,setDressing);box(1.8,.5,1.2,mats.red,-5+i*3.1,.8,-3.8,setDressing);box(1.8,1.2,.2,mats.red,-5+i*3.1,1.6,-4.2,setDressing)}box(15,.13,.3,mats.metal,0,6,-4.3,setDressing)}
 if(c.setting==='museum'){for(const x of [-5,4.8]){box(1.3,2.3,1.3,'#aaa28a',x,1.15,-3,setDressing);const head=new THREE.Mesh(new THREE.IcosahedronGeometry(.7,0),mats.paper);head.position.set(x,3.1,-3);setDressing.add(head);cyl(.35,.55,.8,mats.paper,x,2.6,-3,setDressing)}box(5.5,2.6,.2,mats.metal,0,4.6,-4.6,setDressing);label('THE WEST GALLERY',5,2.1,0,4.6,-4.45,setDressing)}
}
function worldMode(mode,p=0){view=mode;desk.visible=mode!=='scene';investigation.visible=mode==='scene';setDressing.visible=mode==='scene';if(mode==='scene'){camGoal.set(7,9,11);lookGoal.set(0,2.1,0);setPlace(p)}else{camGoal.set(0,8.7,8.7);lookGoal.set(0,2.7,0)}}
function introCamera(){camera.position.set(0,6.5,5.5);target.set(0,2.7,0);worldMode('archive')}
worldMode('archive');

return {configureWorld,worldMode,introCamera,dispose(){disposed=true;cancelAnimationFrame(frame);removeEventListener('resize',resize);renderer.dispose()}};
}
