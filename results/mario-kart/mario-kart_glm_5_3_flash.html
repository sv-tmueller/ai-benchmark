<!DOCTYPE html>

<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"/>
<title>CANYON KART GP</title>
<link href="https://fonts.googleapis.com/css2?family=Titan+One&family=Baloo+2:wght@500;700;800&display=swap" rel="stylesheet">
<style>
  :root{
    --ink:#241420; --paper:#fff3df; --accent:#ff5c39; --teal:#19b892;
    --gold:#ffc93c; --shadow:rgba(36,20,32,.92);
  }
  *{margin:0;padding:0;box-sizing:border-box;-webkit-user-select:none;user-select:none}
  html,body{width:100%;height:100%;overflow:hidden;background:#1c1420;font-family:'Baloo 2',sans-serif;color:var(--paper)}
  canvas#gl{display:block;width:100vw;height:100vh}

  /* ---------- generic chunky panel language ---------- */
  .panel{background:var(--paper);color:var(--ink);border:3px solid var(--ink);border-radius:16px;
         box-shadow:0 7px 0 var(--shadow);}
  .btn{font-family:'Titan One';letter-spacing:.04em;display:inline-flex;align-items:center;justify-content:center;
       cursor:pointer;border:3px solid var(--ink);border-radius:14px;background:var(--accent);color:#fff;
       box-shadow:0 6px 0 var(--shadow);transition:transform .08s,box-shadow .08s;}
  .btn:hover{filter:brightness(1.06)}
  .btn:active{transform:translateY(4px);box-shadow:0 2px 0 var(--shadow)}

  /* ---------- Title / menu ---------- */
  #menu{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:30}
  #menu .poster{text-align:center;margin-bottom:26px;pointer-events:none}
  .big-title{font-family:'Titan One';line-height:.88;transform:rotate(-3deg)}
  .big-title span{display:block;font-size:clamp(44px,9vw,110px);color:var(--paper);
     text-shadow:-3px -3px 0 var(--ink),3px -3px 0 var(--ink),-3px 3px 0 var(--ink),3px 3px 0 var(--ink),
                 8px 10px 0 var(--accent),12px 16px 0 var(--shadow);}
  .big-title em{font-style:normal;color:var(--gold)}
  .sub-badge{display:inline-block;margin-top:18px;font-weight:800;font-size:clamp(13px,1.6vw,18px);
     background:var(--ink);color:var(--paper);padding:7px 18px;border-radius:999px;transform:rotate(2deg);
     box-shadow:0 4px 0 rgba(0,0,0,.35)}
  #controlsCard{padding:16px 22px;max-width:min(430px,88vw);text-align:left}
  #controlsCard h3{font-family:'Titan One';font-size:15px;letter-spacing:.06em;margin-bottom:8px;color:var(--accent)}
  .ctl-row{display:flex;align-items:center;gap:10px;margin:5px 0;font-weight:700;font-size:14px}
  kbd{font-family:'Baloo 2';font-weight:800;background:var(--ink);color:var(--paper);border-radius:7px;
      padding:2px 9px;font-size:12.5px;box-shadow:0 3px 0 rgba(0,0,0,.4);min-width:30px;text-align:center}
  #startBtn{margin-top:22px;font-size:clamp(20px,3vw,30px);padding:14px 54px}
  #muteHint{margin-top:14px;font-size:12px;font-weight:700;opacity:.75}

  /* ---------- HUD ---------- */
  #hud{position:fixed;inset:0;pointer-events:none;z-index:20;display:none}
  #posPlate{position:absolute;top:max(14px,env(safe-area-inset-top));left:18px;transform:rotate(-4deg)}
  #posNum{font-family:'Titan One';font-size:clamp(46px,7vw,84px);color:var(--gold);line-height:.9;
     text-shadow:-3px -3px 0 var(--ink),3px -3px 0 var(--ink),-3px 3px 0 var(--ink),3px 3px 0 var(--ink),6px 8px 0 var(--shadow)}
  #posOrd{font-family:'Titan One';font-size:clamp(16px,2.4vw,26px);color:var(--paper);
     text-shadow:-2px -2px 0 var(--ink),2px -2px 0 var(--ink),-2px 2px 0 var(--ink),2px 2px 0 var(--ink)}
  #posPlate.pop{animation:pop .3s} @keyframes pop{40%{transform:rotate(-4deg) scale(1.25)}}
  #lapPlate{position:absolute;top:max(14px,env(safe-area-inset-top));left:50%;transform:translateX(-50%) rotate(1.5deg);
     font-family:'Titan One';font-size:clamp(15px,2.2vw,22px);padding:6px 20px}
  #lapPlate.final{background:var(--accent);color:#fff;animation:pulse .5s infinite alternate}
  @keyframes pulse{to{transform:translateX(-50%) rotate(1.5deg) scale(1.07)}}
  #speedBox{position:absolute;bottom:max(18px,env(safe-area-inset-bottom));right:18px;text-align:right}
  #speedVal{font-family:'Titan One';font-size:clamp(34px,5vw,58px);color:var(--paper);
     text-shadow:-3px -3px 0 var(--ink),3px -3px 0 var(--ink),-3px 3px 0 var(--ink),3px 3px 0 var(--ink),5px 6px 0 var(--shadow)}
  #speedUnit{font-weight:800;font-size:13px;letter-spacing:.2em;opacity:.9;text-shadow:0 2px 0 var(--ink)}
  #timerBox{position:absolute;top:max(14px,env(safe-area-inset-top));right:18px;font-family:'Titan One';
     font-size:clamp(16px,2.4vw,24px);padding:6px 16px}
  #bestTag{display:block;font-family:'Baloo 2';font-weight:800;font-size:11px;color:var(--teal)}
  #itemSlot{position:absolute;left:18px;bottom:max(18px,env(safe-area-inset-bottom));width:clamp(66px,9vw,96px);
     aspect-ratio:1;display:flex;align-items:center;justify-content:center;background:var(--paper);
     border:3px solid var(--ink);border-radius:18px;box-shadow:0 6px 0 var(--shadow)}
  #itemSlot svg{width:68%;height:68%}
  #itemCharges{position:absolute;right:-7px;top:-7px;background:var(--accent);color:#fff;border:2.5px solid var(--ink);
     border-radius:999px;font-family:'Titan One';font-size:14px;width:26px;height:26px;display:none;
     align-items:center;justify-content:center}
  #itemSlot.spin svg{animation:roul .12s infinite}
  @keyframes roul{50%{transform:scale(.82) rotate(-8deg)}}
  #miniWrap{position:absolute;right:18px;top:calc(max(14px,env(safe-area-inset-top)) + clamp(40px,5.5vw,64px));
     width:clamp(110px,15vw,168px);aspect-ratio:1;background:rgba(36,20,32,.55);border:3px solid var(--ink);
     border-radius:16px;box-shadow:0 5px 0 var(--shadow);overflow:hidden}
  #minimap{width:100%;height:100%}
  #banner{position:absolute;top:32%;left:50%;transform:translate(-50%,-50%) rotate(-2deg);font-family:'Titan One';
     font-size:clamp(26px,5vw,54px);color:var(--gold);opacity:0;white-space:nowrap;
     text-shadow:-3px -3px 0 var(--ink),3px -3px 0 var(--ink),-3px 3px 0 var(--ink),3px 3px 0 var(--ink),7px 9px 0 var(--shadow)}
  #banner.show{animation:bnr 1.8s forwards}
  @keyframes bnr{0%{opacity:0;transform:translate(-50%,-50%) rotate(-2deg) scale(.4)}
     12%{opacity:1;transform:translate(-50%,-50%) rotate(-2deg) scale(1.15)}
     22%{transform:translate(-50%,-50%) rotate(-2deg) scale(1)}80%{opacity:1}100%{opacity:0}}
  #wrongWay{position:absolute;top:22%;left:50%;transform:translateX(-50%);font-family:'Titan One';
     font-size:clamp(20px,3.6vw,38px);color:#ff3b2f;display:none;animation:blink .4s infinite;
     text-shadow:-2px -2px 0 var(--ink),2px -2px 0 var(--ink),-2px 2px 0 var(--ink),2px 2px 0 var(--ink)}
  @keyframes blink{50%{opacity:.15}}

  /* countdown */
  #count{position:fixed;inset:0;display:none;align-items:center;justify-content:center;z-index:25;pointer-events:none}
  #cdLights{display:flex;gap:16px;margin-bottom:20px}
  .lamp{width:clamp(26px,4vw,40px);aspect-ratio:1;border-radius:50%;background:#3a2a34;border:3px solid var(--ink)}
  .lamp.on1{background:#ffb020}.lamp.on2{background:#ff5c39}.lamp.go{background:#3ee06d}
  #cdText{font-family:'Titan One';font-size:clamp(70px,14vw,160px);color:var(--paper);
     text-shadow:-4px -4px 0 var(--ink),4px -4px 0 var(--ink),-4px 4px 0 var(--ink),4px 4px 0 var(--ink),9px 12px 0 var(--shadow)}
  #cdText.zoom{animation:cz .9s} @keyframes cz{0%{transform:scale(2.2);opacity:0}30%{transform:scale(1);opacity:1}}

  /* results */
  #results{position:fixed;inset:0;display:none;align-items:center;justify-content:center;z-index:40;background:rgba(28,16,26,.45)}
  #resPanel{width:min(480px,92vw);padding:24px 26px;max-height:86vh;overflow:auto}
  #resTitle{font-family:'Titan One';font-size:clamp(26px,4.5vw,40px);text-align:center;color:var(--accent);
     margin-bottom:4px;transform:rotate(-1.5deg)}
  #resSub{text-align:center;font-weight:800;font-size:13px;margin-bottom:14px;opacity:.8}
  .resRow{display:flex;align-items:center;gap:10px;padding:7px 10px;border-radius:12px;font-weight:800;font-size:15px}
  .resRow.me{background:var(--ink);color:var(--paper)}
  .resRow .medal{font-family:'Titan One';width:34px;text-align:center;font-size:16px}
  .chip{width:16px;height:16px;border-radius:5px;border:2px solid var(--ink);flex:none}
  .resRow .nm{flex:1;letter-spacing:.02em}
  .resRow .tm{font-variant-numeric:tabular-nums;font-size:13.5px;opacity:.85}
  #restartBtn{margin:18px auto 0;display:flex;font-size:20px;padding:10px 40px}

  /* pause */
  #pause{position:fixed;inset:0;display:none;align-items:center;justify-content:center;z-index:45;background:rgba(28,16,26,.5)}
  #pausePanel{padding:26px 34px;text-align:center}
  #pausePanel h2{font-family:'Titan One';font-size:30px;color:var(--accent);margin-bottom:14px}
  #pausePanel .btn{display:flex;margin:8px auto;font-size:16px;padding:8px 30px;min-width:210px}

  /* mute btn */
  #muteBtn{position:fixed;top:max(12px,env(safe-area-inset-top));left:50%;transform:translateX(-50%);
   z-index:50;width:40px;height:40px;border-radius:12px;border:3px solid var(--ink);background:var(--paper);
   box-shadow:0 4px 0 var(--shadow);cursor:pointer;display:none;align-items:center;justify-content:center}
  #muteBtn svg{width:20px;height:20px;fill:var(--ink)}
  #muteBtn.muted svg{fill:#b04a35}

  /* touch controls */
  #touch{position:fixed;inset:0;z-index:22;display:none;pointer-events:none}
  .tcirc{position:absolute;pointer-events:auto;width:74px;height:74px;border-radius:50%;
     background:rgba(255,243,223,.16);border:3px solid rgba(255,243,223,.5);display:flex;align-items:center;
     justify-content:center;font-family:'Titan One';font-size:13px;color:rgba(255,243,223,.85)}
  .tcirc.press{background:rgba(255,92,57,.45)}
  #tL{left:16px;bottom:110px}#tR{left:106px;bottom:110px}
  #tGas{right:16px;bottom:186px}#tDrift{right:16px;bottom:96px}#tItem{right:106px;bottom:96px}
</style>
</head>
<body>

<canvas id="gl"></canvas>

<!-- ======================= MENU ======================= -->
<div id="menu">
  <div class="poster">
    <div class="big-title"><span>CANYON</span><span>KART <em>GP</em></span></div>
    <div class="sub-badge">SUNSET CIRCUIT &nbsp;•&nbsp; 3 LAPS &nbsp;•&nbsp; 8 RACERS</div>
  </div>
  <div id="controlsCard" class="panel">
    <h3>RACE CONTROLS</h3>
    <div class="ctl-row"><kbd>&uarr;</kbd><kbd>W</kbd> accelerate &nbsp;&nbsp;<kbd>&darr;</kbd><kbd>S</kbd> brake / reverse</div>
    <div class="ctl-row"><kbd>&larr;</kbd><kbd>&rarr;</kbd> or <kbd>A</kbd><kbd>D</kbd> steer</div>
    <div class="ctl-row"><kbd>SPACE</kbd> hop &amp; drift — hold to charge mini-turbo!</div>
    <div class="ctl-row"><kbd>E</kbd> / <kbd>SHIFT</kbd> use item</div>
    <div class="ctl-row"><kbd>P</kbd> pause &nbsp;•&nbsp; <kbd>M</kbd> mute</div>
  </div>
  <button id="startBtn" class="btn">START ENGINE</button>
  <div id="muteHint">Best experienced with sound on</div>
</div>

<button id="muteBtn" title="Toggle sound">
  <svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9H4zm12.5 3a3.5 3.5 0 0 0-2-3.15v6.3a3.5 3.5 0 0 0 2-3.15zM14.5 4.2v2.1a6 6 0 0 1 0 11.4v2.1a8 8 0 0 0 0-15.6z"/></svg>
</button>

<!-- ======================= HUD ======================= -->
<div id="hud">
  <div id="posPlate"><span id="posNum">8</span><span id="posOrd">TH</span></div>
  <div id="lapPlate" class="panel">LAP 1<span style="opacity:.55">/3</span></div>
  <div id="timerBox" class="panel"><span id="raceClock">0:00.00</span><span id="bestTag"></span></div>
  <div id="speedBox"><div id="speedVal">0</div><div id="speedUnit">KM/H</div></div>
  <div id="itemSlot"><div id="itemArt"></div><div id="itemCharges">3</div></div>
  <div id="miniWrap"><canvas id="minimap"></canvas></div>
  <div id="banner"></div>
  <div id="wrongWay">WRONG WAY!</div>
</div>

<div id="count"><div style="text-align:center"><div id="cdLights">
  <div class="lamp" id="lp1"></div><div class="lamp" id="lp2"></div><div class="lamp" id="lp3"></div>
</div><div id="cdText">READY</div></div></div>

<div id="results"><div id="resPanel" class="panel">
  <div id="resTitle">FINISH!</div><div id="resSub">SUNSET CIRCUIT — FINAL STANDINGS</div>
  <div id="resRows"></div><button id="restartBtn" class="btn">RACE AGAIN</button>
</div></div>

<div id="pause"><div id="pausePanel" class="panel">
  <h2>PAUSED</h2>
  <button id="resumeBtn" class="btn">RESUME</button>
  <button id="quitBtn" class="btn">BACK TO TITLE</button>
</div></div>

<div id="touch">
  <div class="tcirc" id="tL">&#9664;</div><div class="tcirc" id="tR">&#9654;</div>
  <div class="tcirc" id="tGas">GO</div><div class="tcirc" id="tDrift">DRIFT</div><div class="tcirc" id="tItem">ITEM</div>
</div>

<script type="module">
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

/* =====================================================================
   CONFIG & SMALL UTILS
===================================================================== */
const TOTAL_LAPS = 3, NS = 700, ROAD_W = 9, CURB_W = 1.5, WALL_LAT = ROAD_W + 13;
const clamp=(v,a,b)=>v<a?a:v>b?b:v, lerp=(a,b,t)=>a+(b-a)*t;
const wrapPI=a=>{while(a>Math.PI)a-=2*Math.PI;while(a<-Math.PI)a+=2*Math.PI;return a;};
const rnd=(a=1,b)=>b===undefined?Math.random()*a:a+Math.random()*(b-a);
const fmtT=s=>{if(s==null)return '--:--.--';const m=Math.floor(s/60),ss=s-m*60;return m+':'+String(Math.floor(ss)).padStart(2,'0')+'.'+String(Math.floor((ss%1)*100)).padStart(2,'0');};
const ORD=n=>n===1?'ST':n===2?'ND':n===3?'RD':'TH';
const $=id=>document.getElementById(id);

/* deterministic-ish hash noise for scenery placement / colors */
function hash2(x,z){let h=Math.sin(x*127.1+z*311.7)*43758.5453;return h-Math.floor(h);}

/* =====================================================================
   RENDERER / SCENE / LIGHTS / SKY
===================================================================== */
const renderer=new THREE.WebGLRenderer({canvas:$('gl'),antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth,innerHeight);
renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.06;

const scene=new THREE.Scene();
scene.fog=new THREE.Fog(0xffbe87,240,760);
const camera=new THREE.PerspectiveCamera(63,innerWidth/innerHeight,.1,2200);

const hemi=new THREE.HemisphereLight(0xbfd7ff,0x8a5a3c,.55); scene.add(hemi);
const sun=new THREE.DirectionalLight(0xffd7a3,1.75);
sun.castShadow=true; sun.shadow.mapSize.set(2048,2048);
Object.assign(sun.shadow.camera,{left:-70,right:70,top:70,bottom:-70,near:10,far:320});
sun.shadow.bias=-0.0004; sun.shadow.normalBias=.03;
scene.add(sun,sun.target);

/* --- gradient dusk sky dome with baked sun glow --- */
const skyMat=new THREE.ShaderMaterial({
  side:THREE.BackSide,depthWrite:false,fog:false,
  uniforms:{sunDir:{value:new THREE.Vector3(.55,.16,.35).normalize()}},
  vertexShader:`varying vec3 vP;void main(){vP=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`,
  fragmentShader:`uniform vec3 sunDir;varying vec3 vP;
  void main(){
    vec3 d=normalize(vP);float h=d.y;
    vec3 zen=vec3(.16,.22,.38), mid=vec3(.98,.53,.36), hor=vec3(1.,.87,.66);
    vec3 c=mix(hor,mid,smoothstep(.0,.18,h)); c=mix(c,zen,smoothstep(.14,.62,h));
    float s=max(dot(d,sunDir),0.);
    c+=vec3(1.,.72,.4)*pow(s,60.)*.9 + vec3(1.,.6,.35)*pow(s,6.)*.22;
    gl_FragColor=vec4(c,1.);}`
});
scene.add(new THREE.Mesh(new THREE.SphereGeometry(1000,32,20),skyMat));

/* faint stars up high */
{
  const g=new THREE.BufferGeometry(),p=[];
  for(let i=0;i<340;i++){const az=rnd(Math.PI*2),el=rnd(.35,1.35),r=940;
    p.push(r*Math.cos(el)*Math.cos(az),r*Math.sin(el),r*Math.cos(el)*Math.sin(az));}
  g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));
  const st=new THREE.Points(g,new THREE.PointsMaterial({color:0xfff4dd,size:2.1,sizeAttenuation:false,transparent:true,opacity:.55,fog:false}));
  scene.add(st);
}

/* =====================================================================
   TRACK SPLINE + DERIVED DATA
===================================================================== */
const CP=[ // hand-authored circuit: long start straight -> climb -> esses -> hairpin -> chicane -> carousel
  [-60,-90,0],[ 10,-94,0],[ 55,-92,0],[105,-72,2.5],[126,-30,6],[124, 8,6],
  [106, 22,4.5],[128, 58,3],[122, 96,2.5],[ 92,114,2],[ 58,104,1.4],[ 44, 78,1],
  [ 40, 56,0.6],[ 12, 78,1],[-28, 94,2],[-64,104,3],[-96, 84,3.4],[-96, 52,2.6],
  [-80, 30,1.6],[-104,  4,1],[-108,-34,0.4],[-88,-64,0]];
const ctrlPts=CP.map(p=>new THREE.Vector3(p[0],p[2],p[1]));
const curve=new THREE.CatmullRomCurve3(ctrlPts,true,'catmullrom',.55);

const S_P=[],S_T=[],S_SIDE=[],S_K=[];          // pos / tangent / side / curvature
{
  const raw=curve.getSpacedPoints(NS); raw.pop();               // drop duplicated endpoint
  for(const p of raw)S_P.push(p.clone());
  for(let i=0;i<NS;i++){
    const a=S_P[(i-1+NS)%NS],b=S_P[(i+1)%NS];
    const t=new THREE.Vector3(b.x-a.x,b.y-a.y,b.z-a.z).normalize();
    S_T.push(t); S_SIDE.push(new THREE.Vector3(t.z,0,-t.x).normalize()); // 90° horiz rotation
  }
  for(let i=0;i<NS;i++){                                        // signed horizontal curvature
    const t0=S_T[i],t1=S_T[(i+1)%NS];
    const cr=t0.x*t1.z-t0.z*t1.x, dp=clamp(t0.dot(t1),-1,1);
    S_K.push(Math.asin(clamp(cr,-1,1))/1.42);                   // ~segment length 1.42m
  }
}
const SMOD=i=>((i%NS)+NS)%NS;
function sampleAt(idx,out={}){                                  // interpolated sample helpers
  const i0=SMOD(Math.floor(idx)),i1=SMOD(i0+1),f=idx-Math.floor(idx);
  out.p=out.p||new THREE.Vector3(); out.t=out.t||new THREE.Vector3(); out.s=out.s||new THREE.Vector3();
  out.p.lerpVectors(S_P[i0],S_P[i1],f); out.t.lerpVectors(S_T[i0],S_T[i1],f).normalize();
  out.s.lerpVectors(S_SIDE[i0],S_SIDE[i1],f).normalize();
  return out;
}
function groundY(x,z){
  return .9*Math.sin(x*.043)*Math.cos(z*.037)+.6*Math.sin((x+z)*.021)-.4;
}

/* =====================================================================
   STATIC WORLD GEOMETRY
===================================================================== */
const world=new THREE.Group(); scene.add(world);

/* ---- terrain ---- */
{
  const g=new THREE.PlaneGeometry(900,900,130,130); g.rotateX(-Math.PI/2);
  const pos=g.attributes.position,col=[];
  const cA=new THREE.Color('#83a757'),cB=new THREE.Color('#6b8f47'),cC=new THREE.Color('#b59a67');
  for(let i=0;i<pos.count;i++){
    const x=pos.getX(i),z=pos.getZ(i);
    pos.setY(i,groundY(x,z));
    const n=hash2(Math.round(x*.35),Math.round(z*.35));
    const c=cA.clone().lerp(cB,n).lerp(cC,clamp((hash2(Math.round(x*.08),Math.round(z*.08))-.72)*4,0,1)*.8);
    col.push(c.r,c.g,c.b);
  }
  g.computeVertexNormals();
  g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  const m=new THREE.Mesh(g,new THREE.MeshLambertMaterial({vertexColors:true}));
  m.receiveShadow=true; world.add(m);
}

/* ---- road texture (speckle + lanes) ---- */
function roadTexture(){
  const cv=document.createElement('canvas');cv.width=cv.height=256;const c=cv.getContext('2d');
  c.fillStyle='#43454c';c.fillRect(0,0,256,256);
  for(let i=0;i<2600;i++){c.fillStyle=`rgba(${rnd(40,90)|0},${rnd(40,90)|0},${rnd(45,95)|0},.25)`;c.fillRect(rnd(256),rnd(256),2,2);}
  c.fillStyle='#efe6cf';c.fillRect(123,0,10,256);              // centre dash base
  c.clearRect(123,32,10,64);c.clearRect(123,160,10,64);        // -> dashes
  c.fillStyle='#e8dcc0';c.fillRect(6,0,5,256);c.fillRect(245,0,5,256);
  const tx=new THREE.CanvasTexture(cv);tx.wrapS=tx.wrapT=THREE.RepeatWrapping;tx.anisotropy=4;tx.colorSpace=THREE.SRGBColorSpace;
  return tx;
}
/* general ribbon builder along the spline */
function buildRibbon(inOff,outOff,yOff,colorFn,matOpts={}){
  const pos=[],uv=[],col=[],idx=[];
  for(let i=0;i<=NS;i++){
    const ii=i%NS,P=S_P[ii],T=S_T[ii],S=S_SIDE[ii];
    const li=inOff instanceof Function?inOff(ii):inOff, lo=outOff instanceof Function?outOff(ii):outOff;
    const yi=yOff instanceof Function?yOff(ii):yOff;
    pos.push(P.x+S.x*li,P.y+yOff==='__'?yi:P.y+yi,P.z+S.z*li,
             P.x+S.x*lo,P.y+yi,P.z+S.z*lo);
    uv.push(0,i*1.42/9,1,i*1.42/9);
    const ci=colorFn?colorFn(ii):[1,1,1];col.push(ci[0],ci[1],ci[2],ci[0],ci[1],ci[2]);
  }
  for(let i=0;i<NS;i++){const a=i*2;idx.push(a,a+1,a+2,a+1,a+3,a+2);}
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));
  g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  g.setIndex(idx);g.computeVertexNormals();
  const m=new THREE.Mesh(g,new THREE.MeshLambertMaterial(Object.assign({vertexColors:true,map:matOpts.map},matOpts.extra)));
  m.receiveShadow=true;world.add(m);return m;
}
/* road deck */
buildRibbon(-ROAD_W,ROAD_W,0,(ii)=>{
  const e=1-(Math.abs(S_K[ii])>.02?.12:0);                     // slight shade on kerbs entry
  return [e,e,e];
},{map:null});
$('');// noop guard (keeps bundlers honest, harmless here)
world.children.at(-1).material.map=roadTexture();

/* curbs — alternating red / bone */
buildRibbon(-(ROAD_W+CURB_W),-ROAD_W,.07,ii=>((Math.floor(ii/4)%2)?[.92,.2,.14]:[.98,.94,.86]));
buildRibbon(ROAD_W,ROAD_W+CURB_W,.07,ii=>(((Math.floor(ii/4)+1)%2)?[.92,.2,.14]:[.98,.94,.86]));

/* earthen skirts pinning road edges down to terrain */
function skirt(side){
  const pos=[],col=[],idx=[];
  for(let i=0;i<=NS;i++){
    const ii=i%NS,P=S_P[ii],S=S_SIDE[ii];
    const ex=P.x+S.x*side*(ROAD_W+CURB_W),ez=P.z+S.z*side*(ROAD_W+CURB_W);
    const by=Math.min(groundY(ex,ez),P.y-.25);
    pos.push(ex,P.y+.05,ez,ex,by,ez);
    const sh=.55+hash2(ii,side)*.2;col.push(sh,sh*.82,sh*.62,sh*.5,sh*.4,sh*.3);
  }
  for(let i=0;i<NS;i++){const a=i*2;if(side>0)idx.push(a,a+1,a+2,a+1,a+3,a+2);else idx.push(a,a+2,a+1,a+1,a+2,a+3);}
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  g.setIndex(idx);g.computeVertexNormals();
  const m=new THREE.Mesh(g,new THREE.MeshLambertMaterial({vertexColors:true,side:THREE.DoubleSide}));
  m.receiveShadow=true;world.add(m);
}
skirt(1);skirt(-1);

/* support pylons where the road flies */
{
  const mats=[];const dummy=new THREE.Object3D();
  for(let i=0;i<NS;i+=7){
    const P=S_P[i],cl=P.y-groundY(P.x,P.z);
    if(cl>1.7&&Math.abs(S_K[i])<.03)mats.push([P.x,P.z,cl]);
  }
  const im=new THREE.InstancedMesh(new THREE.BoxGeometry(1.4,1,1.4),
      new THREE.MeshLambertMaterial({color:0xcdb69b}),mats.length);
  mats.forEach(([x,z,h],k)=>{dummy.position.set(x,groundY(x,z)+h/2-.2,z);dummy.scale.set(1,h,1);dummy.updateMatrix();im.setMatrixAt(k,dummy.matrix);});
  im.castShadow=true;world.add(im);
}

/* ---- start line + gantry ---- */
function checkerTex(n=8){const cv=document.createElement('canvas');cv.width=cv.height=128;const c=cv.getContext('2d');
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){c.fillStyle=((x+y)%2)?'#111':'#fafafa';c.fillRect(x*128/n,y*128/n,128/n,128/n);}
  const t=new THREE.CanvasTexture(cv);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(6,1);return t;}
{
  const lm=new THREE.Mesh(new THREE.PlaneGeometry(ROAD_W*2,3),
    new THREE.MeshBasicMaterial({map:checkerTex()}));
  lm.rotation.x=-Math.PI/2;lm.rotation.z=-Math.atan2(S_T[0].x,S_T[0].z);
  lm.position.copy(S_P[0]).y+=.03;world.add(lm);
}
function banner(text,w){
  const cv=document.createElement('canvas');cv.width=1024;cv.height=192;const c=cv.getContext('2d');
  c.fillStyle='#ff5c39';c.fillRect(0,0,1024,192);
  for(let x=0;x<32;x++){c.fillStyle=x%2?'#241420':'#fff3df';c.fillRect(x*32,0,32,26);c.fillRect(x*32,166,32,26);}
  c.font='900 96px "Arial Black",sans-serif';c.textAlign='center';c.textBaseline='middle';
  c.lineWidth=14;c.strokeStyle='#241420';c.strokeText(text,512,100);c.fillStyle='#fff3df';c.fillText(text,512,100);
  const t=new THREE.CanvasTexture(cv);t.colorSpace=THREE.SRGBColorSpace;return t;
}
function makeGate(ti,text,scale=1){
  const P=S_P[ti],S=S_SIDE[ti],grp=new THREE.Group();
  const pg=new THREE.CylinderGeometry(.45*scale,.55*scale,9,10);
  const pm=new THREE.MeshLambertMaterial({color:0xe8dcc0});
  [[-1,0],[1,0]].forEach(([sd])=>{
    const p=new THREE.Mesh(pg,pm);
    p.position.set(P.x+S.x*sd*(ROAD_W+2),P.y+4.5,P.z+S.z*sd*(ROAD_W+2));
    p.castShadow=true;grp.add(p);
  });
  const bn=new THREE.Mesh(new THREE.BoxGeometry((ROAD_W+4)*scale,2.6*scale,.5),
    new THREE.MeshLambertMaterial({map:banner(text,1)}));
  bn.position.set(P.x,P.y+8*scale,P.z);bn.rotation.y=Math.atan2(S.x,S.z)+Math.PI/2;
  bn.castShadow=true;grp.add(bn);
  world.add(grp);
}
makeGate(0,'CANYON GP',1.15);
makeGate(230,'SECTOR 2');makeGate(520,'HAIRPIN!');

/* ---- desert flora & rocks (instanced) ---- */
{
  const sites=[];
  for(let tries=0;tries<900&&sites.length<330;tries++){
    const x=rnd(-380,380),z=rnd(-380,380);
    let md=1e9;for(let i=0;i<NS;i+=6){const dx=S_P[i].x-x,dz=S_P[i].z-z;md=Math.min(md,dx*dx+dz*dz);}
    if(md>(ROAD_W+9)**2)sites.push([x,z,hash2(x|0,z|0)]);
  }
  const dum=new THREE.Object3D();
  /* cacti: body + two arms share placement */
  const cacSites=sites.filter(s=>s[2]<.4).slice(0,80);
  const cg=new THREE.CapsuleGeometry(.55,3.2,4,10);
  const cm=new THREE.MeshLambertMaterial({color:0x4e8f5b});
  const body=new THREE.InstancedMesh(cg,cm,cacSites.length);
  const armL=new THREE.InstancedMesh(cg,cm,cacSites.length);
  const armR=new THREE.InstancedMesh(cg,cm,cacSites.length);
  cacSites.forEach(([x,z,h],k)=>{
    const gy=groundY(x,z),sc=.7+h*.9;
    dum.position.set(x,gy+2.1*sc,z);dum.scale.setScalar(sc);dum.rotation.y=h*6;dum.updateMatrix();body.setMatrixAt(k,dum.matrix);
    const mk=(sx,sz,ry)=>{const d2=new THREE.Object3D();
      d2.position.set(x+Math.sin(ry)*1.1*sx*sc,gy+2.4*sc,z+Math.cos(ry)*1.1*sx*sc);
      d2.scale.set(sz*sc,1.1*sc,sz*sc);d2.rotation.z=ry>0?-.7:.7;d2.updateMatrix();return d2.matrix;};
    if(h>.12)armL.setMatrixAt(k,mk(1,.8,1.2));else armL.setMatrixAt(k,new THREE.Matrix4().makeScale(0,0,0));
    if(h<.3)armR.setMatrixAt(k,mk(1,.8,-1.2));else armR.setMatrixAt(k,new THREE.Matrix4().makeScale(0,0,0));
  });
  [body,armL,armR].forEach(m=>{m.castShadow=true;m.instanceMatrix.needsUpdate=true;world.add(m);});

  /* dry bushes */
  const bushSites=sites.filter(s=>s[2]>=.4&&s[2]<.75);
  const bi=new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1,0),
    new THREE.MeshLambertMaterial({color:0xa9853f,flatShading:true}),bushSites.length);
  bushSites.forEach(([x,z,h],k)=>{dum.position.set(x,groundY(x,z)+.5,z);
    dum.scale.set(.8+h,.6+h*.7,.8+h);dum.rotation.set(h*3,h*7,0);dum.updateMatrix();bi.setMatrixAt(k,dum.matrix);});
  bi.castShadow=true;world.add(bi);

  /* red-rock spires (grouped stacks) */
  const rockCols=['#c1613f','#a94f36','#d1794e'];
  for(let k=0;k<16;k++){
    const [x,z]=sites[Math.floor(rnd(sites.length))]||[rnd(-300,300),rnd(-300,300)];
    if(Math.hypot(x,z)>360)continue;
    const grp=new THREE.Group(),segs=3+Math.floor(rnd(3));
    for(let s=0;s<segs;s++){
      const sc=(segs-s)/(segs+.4);
      const mm=new THREE.Mesh(new THREE.DodecahedronGeometry(3.4*sc,0),
        new THREE.MeshLambertMaterial({color:rockCols[s%3],flatShading:true}));
      mm.position.set(rnd(-.7,.7),s*3.1+1.6,rnd(-.7,.7));mm.rotation.set(rnd(3),rnd(3),rnd(3));
      mm.castShadow=true;grp.add(mm);
    }
    grp.position.set(x,groundY(x,z)-.6,z);world.add(grp);
  }

  /* distant mountain ring */
  for(let k=0;k<26;k++){
    const a=k/26*Math.PI*2+rnd(.15),r=rnd(430,560),hh=rnd(60,150);
    const mt=new THREE.Mesh(new THREE.ConeGeometry(rnd(60,120),hh,7),
      new THREE.MeshLambertMaterial({color:new THREE.Color().setHSL(.78,.22,rnd(.3,.42)),flatShading:true}));
    mt.position.set(Math.cos(a)*r,hh/2-8,Math.sin(a)*r);mt.rotation.y=rnd(3);world.add(mt);
    if(hh>95){const cap=new THREE.Mesh(new THREE.ConeGeometry(hh*.16,16,7),
      new THREE.MeshLambertMaterial({color:0xfdf3ea,flatShading:true}));
      cap.position.set(mt.position.x,hh-8,mt.position.z);world.add(cap);}
  }
}

/* drifting clouds + party balloons */
const clouds=[],balloons=[];
{
  const cm=new THREE.MeshLambertMaterial({color:0xfff6ec,transparent:true,opacity:.92});
  for(let i=0;i<9;i++){
    const g=new THREE.Group();
    for(let k=0;k<4;k++){const s=new THREE.Mesh(new THREE.SphereGeometry(rnd(7,13),10,8),cm);
      s.position.set(rnd(-14,14),rnd(-2,2),rnd(-6,6));s.scale.y=.45;g.add(s);}
    g.position.set(rnd(-450,450),rnd(70,120),rnd(-450,450));scene.add(g);clouds.push(g);
  }
  const pal=[0xff5c39,0x19b892,0xffc93c,0xef476f,0x4cc9f0];
  for(let i=0;i<6;i++){
    const g=new THREE.Group();
    const bv=new THREE.Mesh(new THREE.SphereGeometry(4,14,12),
      new THREE.MeshLambertMaterial({color:pal[i%pal.length]}));
    bv.scale.y=1.2;g.add(bv);
    const bk=new THREE.Mesh(new THREE.BoxGeometry(2,1.6,2),new THREE.MeshLambertMaterial({color:0x8a5a3c}));
    bk.position.y=-6.4;g.add(bk);
    const rope=new THREE.Mesh(new THREE.CylinderGeometry(.05,.05,4.4),new THREE.MeshBasicMaterial({color:0x5a4030}));
    rope.position.y=-4.2;g.add(rope);
    g.position.set(rnd(-200,200),rnd(26,44),rnd(-200,200));scene.add(g);balloons.push(g);
  }
}

/* =====================================================================
   AUDIO — fully synthesized (engine, sfx, chiptune loop)
===================================================================== */
const AU={ctx:null,on:true,musicOn:true,engNodes:null,master:null,musGain:null,nextBeat:0,beat:0,intensity:0};
function auInit(){
  if(AU.ctx)return;
  const C=AU.ctx=new (window.AudioContext||window.webkitAudioContext)();
  AU.master=C.createGain();AU.master.gain.value=.9;
  const comp=C.createDynamicsCompressor();AU.master.connect(comp);comp.connect(C.destination);
  AU.musGain=C.createGain();AU.musGain.gain.value=.17;AU.musGain.connect(AU.master);
  /* engine voice */
  const eg=AU.engNodes={},g=C.createGain();g.gain.value=0;
  const lp=C.createBiquadFilter();lp.type='lowpass';lp.frequency.value=650;
  const o1=C.createOscillator(),o2=C.createOscillator();
  o1.type='sawtooth';o2.type='square';o2.detune.value=9;
  o1.connect(lp);o2.connect(lp);lp.connect(g);g.connect(AU.master);o1.start();o2.start();
  Object.assign(eg,{o1,o2,g,lp});
  /* looping noise for wind */
  const nb=C.createBuffer(1,C.sampleRate,C.sampleRate),d=nb.getChannelData(0);
  for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;
  const ns=C.createBufferSource();ns.buffer=nb;ns.loop=true;
  const nf=C.createBiquadFilter();nf.type='bandpass';nf.frequency.value=900;nf.Q.value=.6;
  const ng=C.createGain();ng.gain.value=0;ns.connect(nf);nf.connect(ng);ng.connect(AU.master);ns.start();
  eg.wind=ng;
  AU.nextBeat=C.currentTime+.1;
  setInterval(scheduleMusic,25);
}
function beep(f,dur=.12,type='square',vol=.25,slide=0){
  if(!AU.ctx||!AU.on)return;const C=AU.ctx,t=C.currentTime;
  const o=C.createOscillator(),g=C.createGain();o.type=type;o.frequency.setValueAtTime(f,t);
  if(slide)o.frequency.exponentialRampToValueAtTime(Math.max(30,f+slide),t+dur);
  g.gain.setValueAtTime(vol,t);g.gain.exponentialRampToValueAtTime(.001,t+dur);
  o.connect(g);g.connect(AU.master);o.start(t);o.stop(t+dur+.02);
}
function noiseHit(fc=800,dur=.25,vol=.3){
  if(!AU.ctx||!AU.on)return;const C=AU.ctx,t=C.currentTime;
  const b=C.createBuffer(1,C.sampleRate*dur,C.sampleRate),d=b.getChannelData(0);
  for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*(1-i/d.length);
  const s=C.createBufferSource();s.buffer=b;
  const f=C.createBiquadFilter();f.type='lowpass';f.frequency.setValueAtTime(fc,t);f.frequency.exponentialRampToValueAtTime(120,t+dur);
  const g=C.createGain();g.gain.value=vol;s.connect(f);f.connect(g);g.connect(AU.master);s.start();
}
const hz=m=>440*Math.pow(2,(m-69)/12);
const LEAD=[76,null,79,null,81,null,79,76, 74,null,76,null,72,null,74,null,
            76,null,79,null,81,null,84,81, 79,76,74,null,72,null,74,null];
const BASS=[48,48,43,43,45,45,41,43];
function scheduleMusic(){
  if(!AU.ctx||!AU.musicOn||!AU.on)return;
  const C=AU.ctx,spb=60/138/4;                       // sixteenth @138bpm
  while(AU.nextBeat<C.currentTime+.15){
    const st=AU.beat%32,tr=AU.intensity?2:0,t=AU.nextBeat;
    const L=LEAD[st];
    if(L!==null&&(state==='run'||state==='count')){
      const o=C.createOscillator(),g=C.createGain();o.type='square';o.frequency.value=hz(L+tr);
      g.gain.setValueAtTime(.16,t);g.gain.exponentialRampToValueAtTime(.001,t+spb*1.7);
      o.connect(g);g.connect(AU.musGain);o.start(t);o.stop(t+spb*2);
    }
    if(st%16===0||(st%16===6)||(st%16===11)){
      const b=BASS[Math.floor(st/16)%8]+tr;
      const o=C.createOscillator(),g=C.createGain();o.type='triangle';o.frequency.value=hz(b);
      g.gain.setValueAtTime(.3,t);g.gain.exponentialRampToValueAtTime(.001,t+spb*2.6);
      o.connect(g);g.connect(AU.musGain);o.start(t);o.stop(t+spb*3);
    }
    if(st%2===0){                                   // hat
      const b=C.createBuffer(1,1200,C.sampleRate),d=b.getChannelData(0);
      for(let i=0;i<1200;i)d[i++]=Math.random()*2-1;
      const s=C.createBufferSource();s.buffer=b;
      const f=C.createBiquadFilter();f.type='highpass';f.frequency.value=7000;
      const g=C.createGain();g.gain.setValueAtTime(.06,t);g.gain.exponentialRampToValueAtTime(.001,t+.04);
      s.connect(f);f.connect(g);g.connect(AU.musGain);s.start(t);
    }
    AU.nextBeat+=spb;AU.beat++;
  }
}

/* =====================================================================
   PARTICLES (GPU-friendly pooled points) + CONFETTI INSTANCES
===================================================================== */
function softDot(){const cv=document.createElement('canvas');cv.width=cv.height=64;const c=cv.getContext('2d');
  const gr=c.createRadialGradient(32,32,2,32,32,30);gr.addColorStop(0,'rgba(255,255,255,1)');
  gr.addColorStop(.5,'rgba(255,255,255,.5)');gr.addColorStop(1,'rgba(255,255,255,0)');
  c.fillStyle=gr;c.fillRect(0,0,64,64);return new THREE.CanvasTexture(cv);}
class Pool{
  constructor(cap,blend,grav){
    this.cap=cap;this.grav=grav;this.i=0;
    this.pos=new Float32Array(cap*3);this.col=new Float32Array(cap*3);
    this.dat=new Float32Array(cap*2);           // size, life
    this.vel=new Float32Array(cap*3);this.life=new Float32Array(cap);this.max=new Float32Array(cap);
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.BufferAttribute(this.pos,3));
    g.setAttribute('color',new THREE.BufferAttribute(this.col,3));
    g.setAttribute('pdata',new THREE.BufferAttribute(this.dat,2));
    const m=new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:blend,
      uniforms:{tex:{value:softDot()}},
      vertexShader:`attribute vec2 pdata;attribute vec3 color;varying vec3 vC;varying float vA;
        uniform float pr;void main(){vC=color;vA=pdata.y;
        vec4 mv=modelViewMatrix*vec4(position,1.);gl_PointSize=pdata.x*pr/mv.w;
        gl_Position=projectionMatrix*mv;}`,
      fragmentShader:`uniform sampler2D tex;varying vec3 vC;varying float vA;
        void main(){vec4 t=texture2D(tex,gl_PointCoord);gl_FragColor=vec4(vC,t.a*vA);}`});
    this.mesh=new THREE.Points(g,m);this.mesh.frustumCulled=false;scene.add(this.mesh);
  }
  emit(p,v,color,size,life){
    const k=this.i;this.i=(this.i+1)%this.cap;
    this.pos[k*3]=p.x;this.pos[k*3+1]=p.y;this.pos[k*3+2]=p.z;
    this.vel[k*3]=v.x;this.vel[k*3+1]=v.y;this.vel[k*3+2]=v.z;
    const c=new THREE.Color(color);this.col[k*3]=c.r;this.col[k*3+1]=c.g;this.col[k*3+2]=c.b;
    this.dat[k*2]=size;this.dat[k*2+1]=1;this.life[k]=life;this.max[k]=life;
  }
  update(dt){
    for(let k=0;k<this.cap;k++){
      if(this.life[k]<=0){this.dat[k*2+1]=0;continue;}
      this.life[k]-=dt;const f=Math.max(this.life[k]/this.max[k],0);
      this.dat[k*2+1]=f;
      this.pos[k*3]+=this.vel[k*3]*dt;this.pos[k*3+1]+=this.vel[k*3+1]*dt;this.pos[k*3+2]+=this.vel[k*3+2]*dt;
      if(this.grav)this.vel[k*3+1]-=14*dt;
      this.dat[k*2]=Math.max(this.dat[k*2]*(1-dt*(this.grav?0:.9)),.2);
    }
    this.mesh.geometry.attributes.position.needsUpdate=true;
    this.mesh.geometry.attributes.pdata.needsUpdate=true;
    this.mesh.material.uniforms.pr.value=innerHeight*.9;
  }
}
const sparks=new Pool(500,THREE.AdditiveBlending,false);
const smokes=new Pool(400,THREE.NormalBlending,false);

/* confetti */
const CONF_N=140;
const confMesh=new THREE.InstancedMesh(new THREE.PlaneGeometry(.34,.5),
  new THREE.MeshBasicMaterial({side:THREE.DoubleSide}),CONF_N);
confMesh.visible=false;scene.add(confMesh);
const confP=[];const cdum=new THREE.Object3D();
for(let i=0;i<CONF_N;i++)confP.push({p:new THREE.Vector3(),v:new THREE.Vector3(),r:new THREE.Euler(),rv:new THREE.Vector3(),live:false});
function confetti(origin){
  confMesh.visible=true;
  const cols=[0xff5c39,0x19b892,0xffc93c,0xef476f,0x4cc9f0,0xffffff];
  confP.forEach((c,i)=>{c.live=true;c.p.copy(origin).add(new THREE.Vector3(rnd(-3,3),rnd(0,2),rnd(-3,3)));
    c.v.set(rnd(-4,4),rnd(6,13),rnd(-4,4));c.rv.set(rnd(-6,6),rnd(-6,6),rnd(-6,6));
    confMesh.setColorAt(i,new THREE.Color(cols[i%cols.length]));});
  confMesh.instanceColor.needsUpdate=true;
}
function updConf(dt){
  if(!confMesh.visible)return;let alive=false;
  confP.forEach((c,i)=>{if(!c.live){cdum.scale.setScalar(0);}else{alive=true;
    c.v.y-=9*dt;c.p.addScaledVector(c.v,dt);c.r.x+=c.rv.x*dt;c.r.y+=c.rv.y*dt;c.r.z+=c.rv.z*dt;
    if(c.p.y<groundY(c.p.x,c.p.z)){c.live=false;cdum.scale.setScalar(0);}
    else cdum.scale.setScalar(1);
    cdum.position.copy(c.p);cdum.rotation.copy(c.r);}
    cdum.updateMatrix();confMesh.setMatrixAt(i,cdum.matrix);});
  confMesh.instanceMatrix.needsUpdate=true;
  if(!alive)setTimeout(()=>confMesh.visible=false,50);
}

/* =====================================================================
   KART MODEL FACTORY
===================================================================== */
function buildKart(bodyCol,helmCol){
  const g=new THREE.Group(),core=new THREE.Group();g.add(core);
  const mat=c=>new THREE.MeshLambertMaterial({color:c});
  const body=new THREE.Mesh(new THREE.BoxGeometry(1.7,.55,2.6),mat(bodyCol));
  body.position.y=.55;body.castShadow=true;core.add(body);
  const nose=new THREE.Mesh(new THREE.BoxGeometry(1.1,.34,.9),mat(bodyCol));
  nose.position.set(0,.5,1.6);nose.castShadow=true;core.add(nose);
  const bumper=new THREE.Mesh(new THREE.BoxGeometry(1.9,.22,.25),mat(0x2b2b33));
  bumper.position.set(0,.42,2.05);core.add(bumper);
  const seat=new THREE.Mesh(new THREE.BoxGeometry(1,.7,.35),mat(0x33333d));
  seat.position.set(0,1.05,-.75);seat.rotation.x=-.15;core.add(seat);
  const torso=new THREE.Mesh(new THREE.CapsuleGeometry(.32,.4,4,10),mat(0xf2c9a0));
  torso.position.set(0,1.25,-.55);torso.castShadow=true;core.add(torso);
  const helm=new THREE.Mesh(new THREE.SphereGeometry(.42,14,12),mat(helmCol));
  helm.position.set(0,1.85,-.5);helm.castShadow=true;core.add(helm);
  const visor=new THREE.Mesh(new THREE.BoxGeometry(.5,.18,.3),mat(0x22242e));
  visor.position.set(0,1.86,-.14);core.add(visor);
  const spo=new THREE.Mesh(new THREE.BoxGeometry(1.9,.1,.5),mat(bodyCol));
  spo.position.set(0,1.15,-1.45);spo.castShadow=true;core.add(spo);
  [[-.95,.3],[ -.95,-.3]];// placeholder to keep lint calm
  const wg=new THREE.CylinderGeometry(.42,.42,.36,14);wg.rotateZ(Math.PI/2);
  const wm=new THREE.MeshLambertMaterial({color:0x23232a});
  const hub=new THREE.CylinderGeometry(.18,.18,.38,10);hub.rotateZ(Math.PI/2);
  const hm=new THREE.MeshLambertMaterial({color:0xd9d2c5});
  const wheels=[],fr=[];
  [[-.95,.95,1],[.95,.95,1],[-.95,-.95,0],[.95,-.95,0]].forEach(([x,z,front])=>{
    const pivot=new THREE.Group();pivot.position.set(x,.42,z);
    const w=new THREE.Mesh(wg,wm);w.castShadow=true;pivot.add(w);
    const hb=new THREE.Mesh(hub,hm);hb.position.x=(x>0?.02:-.02);pivot.add(hb);
    core.add(pivot);wheels.push(w);if(front)fr.push(pivot);
  });
  const exh=new THREE.Mesh(new THREE.CylinderGeometry(.13,.16,.6,8),mat(0x777d88));
  exh.rotation.x=Math.PI/2-.25;exh.position.set(-.45,.75,-1.5);core.add(exh);
  const exh2=exh.clone();exh2.position.x=.45;core.add(exh2);
  const flGeo=new THREE.ConeGeometry(.2,.9,8);flGeo.rotateX(-Math.PI/2);
  const flMat=new THREE.MeshBasicMaterial({color:0xffa53d,transparent:true,opacity:.9,blending:THREE.AdditiveBlending,depthWrite:false});
  const flames=[];
  [exh,exh2].forEach(e=>{const f=new THREE.Mesh(flGeo,flMat);f.position.copy(e.position);f.position.z-=.7;
    f.visible=false;core.add(f);flames.push(f);});
  return {group:g,core,wheels,front:fr,flames,bodyMat:body.material,helmMat:helm.material};
}

/* =====================================================================
   RACERS
===================================================================== */
const ROSTER=[
  ['YOU',      0xff5c39,0x241420,true ],
  ['MAJOR VOLT',0x2fa7de,0x143a4d],
  ['PEPPER',   0xef476f,0x5c1626],
  ['BRUNO',    0xf2b134,0x5c4310],
  ['MINT',     0x2ecc8f,0x14523a],
  ['NOVA',     0xe8e2ef,0x4a3f61],
  ['KILO',     0x8d67e0,0x2f2350],
  ['SHADOW',   0x3a3f4c,0x101218]];
const GRID_OFF=[[ -3.4,6],[3.4,10],[-3.4,14],[3.4,18],[-3.4,22],[3.4,26],[-3.4,30],[3.4,34]];

const karts=[];
function makeKarts(){
  karts.length=0;
  ROSTER.forEach(([name,col,helm,isP],rank)=>{
    const mdl=buildKart(col,helm);scene.add(mdl.group);
    const gi=ROSTER.length-1-rank;                    // leaders at front
    const [gx,gz]=GRID_OFF[gi];
    const t0=0.002+gz*S_T[0].length()/curve.getLength()*0; // grid measured along straight
    const idx=SMOD(Math.round(gz/1.42));
    const P=S_P[idx],S=S_SIDE[idx];
    const pos=new THREE.Vector3().copy(P).addScaledVector(S,gx);
    karts.push({
      name,col,isPlayer:!!isP,mdl,pos,yaw:Math.atan2(S_T[idx].x,S_T[idx].z),
      vel:new THREE.Vector3(),steer:0,idx,lat:0,prog:0,prevProg:0,lap:0,mid:false,
      speed:0,drift:false,driftDir:0,charge:0,hopY:0,hopV:0,air:false,
      boostT:0,spinT:0,immT:0,starT:0,item:null,chrg:0,finished:false,ft:0,
      pers:{top:.9+ (isP?0:rnd(0,.07)),lane:rnd(-3,3),seed:rnd(100)},
      laneCur:gx,aiThr:1,aiBrk:0,wrongT:0,lapTimes:[],lapStart:0,best:null,
    });
  });
}

/* =====================================================================
   ITEMS WORLD OBJECTS
===================================================================== */
const boxes=[],bananas=[],shells=[];
const qTex=(()=>{const cv=document.createElement('canvas');cv.width=cv.height=128;const c=cv.getContext('2d');
  c.font='900 92px Arial';c.textAlign='center';c.textBaseline='middle';
  c.lineWidth=12;c.strokeStyle='#241420';c.strokeText('?',64,70);c.fillStyle='#fff';c.fillText('?',64,70);
  return new THREE.CanvasTexture(cv);})();
function makeBoxes(){
  boxes.forEach(b=>world.remove(b.grp));boxes.length=0;
  [[110,[ -3,0,3]],[300,[-3,0,3]],[365,[-4,0,4]],[560,[-3,0,3]],[640,[-4,0,4]]].forEach(([ti,lanes])=>{
    lanes.forEach(lo=>{
      const grp=new THREE.Group();
      const cube=new THREE.Mesh(new THREE.BoxGeometry(1.7,1.7,1.7),
        new THREE.MeshPhongMaterial({color:0x8fe3ff,transparent:true,opacity:.55,shininess:90,specular:0xffffff}));
      const q=new THREE.Sprite(new THREE.SpriteMaterial({map:qTex,transparent:true}));
      q.scale.setScalar(1.15);
      grp.add(cube,q);world.add(grp);
      const tmp={};sampleAt(ti,tmp);
      const p=tmp.p.clone().addScaledVector(tmp.s,lo);p.y+=1.4;
      grp.position.copy(p);
      boxes.push({grp,cube,q,p,base:p.clone(),active:true,respT:0,ph:rnd(6)});
    });
  });
}
/* shell mesh template */
function shellMesh(red){
  const prof=[];for(let i=0;i<=8;i++){const a=i/8*Math.PI;prof.push(new THREE.Vector2(Math.sin(a)*.55,Math.cos(a)*.55*.9+.05));}
  prof.push(new THREE.Vector2(.62,.02),new THREE.Vector2(.62,0),new THREE.Vector2(-.62,0),new THREE.Vector2(-.62,.02));
  const m=new THREE.Mesh(new THREE.LatheGeometry(prof.reverse(),14),
    new THREE.MeshLambertMaterial({color:red?0xe8402a:0x35d052}));
  m.castShadow=true;return m;
}
function bananaMesh(){
  const g=new THREE.TorusGeometry(.5,.19,8,14,Math.PI*1.05);
  const m=new THREE.Mesh(g,new THREE.MeshLambertMaterial({color:0xffd23f}));
  m.rotation.x=Math.PI/2;m.rotation.z=Math.PI*.55;m.position.y=.28;m.castShadow=true;
  const tip=new THREE.Mesh(new THREE.SphereGeometry(.14,8,6),new THREE.MeshLambertMaterial({color:0x7a5220}));
  tip.position.set(.5,.28,.42);const grp=new THREE.Group();grp.add(m,tip);return grp;
}

/* =====================================================================
   INPUT
===================================================================== */
const keys={};
addEventListener('keydown',e=>{
  if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' ','Space'].includes(e.key)||e.code==='Space')e.preventDefault();
  keys[e.code]=true;
  if(e.code==='KeyP'&&state==='run')togglePause();
  if(e.code==='Escape'&&state==='run')togglePause(true);
  if(e.code==='KeyM')toggleMute();
});
addEventListener('keyup',e=>keys[e.code]=false);
const touch={l:0,r:0,gas:0,drift:0,item:0};
if(matchMedia('(pointer:coarse)').matches)$('touch').style.display='block';
[['tL','l'],['tR','r'],['tGas','gas'],['tDrift','drift']].forEach(([id,k])=>{
  const el=$(id);
  el.addEventListener('touchstart',e=>{e.preventDefault();touch[k]=1;el.classList.add('press');auResume();});
  el.addEventListener('touchend',e=>{e.preventDefault();touch[k]=0;el.classList.remove('press');});
});
$('tItem').addEventListener('touchstart',e=>{e.preventDefault();touch.item=1;$('tItem').classList.add('press');auResume();});
$('tItem').addEventListener('touchend',e=>{e.preventDefault();touch.item=0;$('tItem').classList.remove('press');});
function readInput(k){
  const up=keys.ArrowUp||keys.KeyW||touch.gas, dn=keys.ArrowDown||keys.KeyS;
  const lf=keys.ArrowLeft||keys.KeyA||touch.l, rt=keys.ArrowRight||keys.KeyD||touch.r;
  const dr=keys.Space||touch.drift, it=keys.KeyE||keys.ShiftLeft||keys.ShiftRight||keys.ControlLeft||touch.item;
  return {thr:up?1:0,brk:dn?1:0,steer:(rt?1:0)-(lf?1:0),drift:dr,item:it};
}

/* =====================================================================
   PHYSICS STEP FOR ONE KART
===================================================================== */
const _sv={},_tv=new THREE.Vector3(),_nv=new THREE.Vector3();
function locate(k){                                     // nearest sample + lateral offset
  let best=k.idx,bd=1e18;
  for(let o=-30;o<=30;o++){const i=SMOD(k.idx+o);
    const dx=S_P[i].x-k.pos.x,dz=S_P[i].z-k.pos.z,d=dx*dx+dz*dz;
    if(d<bd){bd=d;best=i;}}
  k.idx=best;
  const S=S_SIDE[best];
  k.lat=(k.pos.x-S_P[best].x)*S.x+(k.pos.z-S_P[best].z)*S.z;
  const prev=k.prog;
  k.prog=(best+k.speed*0)/NS;                            // refined below by projection
  const nx=S_P[SMOD(best+1)],pv=_tv.subVectors(nx,S_P[best]);pv.y=0;
  const pl=clamp(_nv.subVectors(k.pos,S_P[best]).setY(0).dot(pv.normalize())/1.42,0,1);
  k.prog=(best+pl)/NS;
  if(prev>.75&&k.prog<.25){                              // wrapped forward across line
    if(k.mid){k.lap++;k.mid=false;onLap(k);}
  } else if(prev<.25&&k.prog>.75){k.lap--;k.mid=true;}   // reversed across line
  if(k.prog>.45&&k.prog<.55)k.mid=true;
}
function physStep(k,input,dt){
  const P=k.pers;
  /* --- spin / stun overrides --- */
  if(k.spinT>0){k.spinT-=dt;k.steer=0;input.thr=0;}
  /* --- steering --- */
  const tgt=input.steer;
  k.steer+=(tgt-k.steer)*Math.min(1,dt*10);
  const spd=k.vel.length(),vr=clamp(spd/33,0,1);
  let turn=k.steer*lerp(2.15,1.28,vr);
  if(k.drift){
    const eff=clamp(k.driftDir*.62+k.steer*.55,-1,1);
    turn=eff*lerp(2.6,1.7,vr);
    k.charge+=dt;
  }
  if(spd>.6&&!k.air)k.yaw-=turn*dt*(spd>0?(k.vel.dot(_tv.set(Math.sin(k.yaw),0,Math.cos(k.yaw)))<0?-1:1):1);
  /* --- hop / drift lifecycle --- */
  if(input.drift&&!k.prevDrift&&k.spinT<=0&&!k.air&&spd>6){
    k.hopV=5.4;k.air=true;k.driftPending=true;beep(300,.08,'square',.15,120);
  }
  if(k.air){
    k.hopY+=k.hopV*dt;k.hopV-=20*dt;
    if(k.hopY<=0){k.hopY=0;k.air=false;
      if(k.driftPending&&input.drift&&Math.abs(input.steer)>.2&&spd>8){
        k.drift=true;k.driftDir=Math.sign(input.steer);k.charge=0;
      } else k.driftPending=false;
      smokes.emit(k.pos,_nv.set(rnd(-1,1),.5,rnd(-1,1)),0xcbbaa0,2.2,.5);
    }
  }
  if(k.drift&&(!input.drift||spd<5||k.spinT>0)){releaseDrift(k);}
  k.prevDrift=input.drift;
  /* --- forces --- */
  const fwd=_tv.set(Math.sin(k.yaw),0,Math.cos(k.yaw));
  const onRoad=Math.abs(k.lat)<=ROAD_W+CURB_W+.4;
  let top=33*P.top;
  if(k.boostT>0)top*=1.33;
  if(k.starT>0)top*=1.12;
  if(!onRoad&&k.starT<=0)top*=.45;
  if(k.isPlayer&&touch.gas&&!input.thr)input.thr=1;
  if(input.brk){k.vel.addScaledVector(fwd,-26*dt);if(spd<1&&input.brk)k.vel.addScaledVector(fwd,-8*dt);}
  if(input.thr&&k.spinT<=0){
    const acc=(top-spd)*1.35;
    k.vel.addScaledVector(fwd,acc*dt);
  } else {
    k.vel.multiplyScalar(Math.max(0,1-.7*dt));
  }
  if(k.boostT>0){                                        // boost enforces minimum pace
    const fs=fwd.clone().multiplyScalar(top*.85);
    if(k.vel.dot(fs)<fs.length())k.vel.addScaledVector(fwd,60*dt);
  }
  /* grip: rotate velocity toward facing */
  const ms=k.vel.length();
  if(ms>.4){
    const ma=Math.atan2(k.vel.x,k.vel.z);
    let da=wrapPI(k.yaw-ma);
    const rate=k.drift?3.1:(onRoad?8.5:5);
    const na=ma+clamp(da,-rate*dt,rate*dt);
    k.vel.set(Math.sin(na)*ms,0,Math.cos(na)*ms);
  }
  /* soft wall */
  if(Math.abs(k.lat)>WALL_LAT){
    const S=S_SIDE[k.idx],push=(Math.abs(k.lat)-WALL_LAT)*4;
    k.vel.addScaledVector(S,-Math.sign(k.lat)*push*dt*10);
    k.vel.multiplyScalar(1-1.5*dt);
  }
  k.pos.addScaledVector(k.vel,dt);
  locate(k);
  /* ground snap */
  const gy=roadOrGround(k);
  k.pos.y=gy+k.hopY;
  /* timers */
  k.boostT=Math.max(0,k.boostT-dt);k.immT=Math.max(0,k.immT-dt);k.starT=Math.max(0,k.starT-dt);
  /* drift charge fx */
  if(k.drift){
    const tier=k.charge>2?2:k.charge>.9?1:0;
    const wc=wWheelWorld(k,1);
    sparks.emit(wc,_nv.set(rnd(-2,2),rnd(1,3),rnd(-2,2)),
      tier===2?0xffa53d:tier===1?0x59d9ff:0x9adcff,1.6,.35);
  }
  if(!onRoad&&spd>7&&Math.random()<dt*22)
    smokes.emit(rearAxle(k),_nv.set(rnd(-1,1),rnd(1,2),rnd(-1,1)),0xb59a67,2.6,.6);
  if(k.boostT>0&&Math.random()<dt*40)
    sparks.emit(rearAxle(k),_nv.set(rnd(-1,1),rnd(.5,2),rnd(-1,1)),0xff8a3d,1.8,.3);
}
function releaseDrift(k){
  const tier=k.charge>2?2:k.charge>.9?1:0;
  if(tier>0){applyBoost(k,tier===2?1.35:.75);beep(tier===2?750:550,.25,'sawtooth',.2,300);}
  k.drift=false;k.driftPending=false;k.charge=0;
}
function applyBoost(k,d){k.boostT=Math.max(k.boostT,d);if(k.isPlayer)noiseHit(2400,.4,.22);}
function roadOrGround(k){
  const al=Math.abs(k.lat);
  const cy=S_P[k.idx].y;
  if(al<=ROAD_W+CURB_W)return cy;
  const f=clamp((al-ROAD_W-CURB_W)/6,0,1);
  return lerp(cy,groundY(k.pos.x,k.pos.z),f*f*(3-2*f));
}
function wWheelWorld(k,rear){
  return _nv.set(k.pos.x-Math.sin(k.yaw)*(rear?1.2:-1.2)+(rear?Math.cos(k.yaw)*.9:-Math.cos(k.yaw)*.9),
                 k.pos.y+.2,k.pos.z-Math.cos(k.yaw)*(rear?1.2:-1.2)-(rear?Math.sin(k.yaw)*.9:-Math.sin(k.yaw)*.9));
}
function rearAxle(k){return _tv.set(k.pos.x-Math.sin(k.yaw)*1.6,k.pos.y+.4,k.pos.z-Math.cos(k.yaw)*1.6);}

/* =====================================================================
   COLLISIONS & HAZARDS
===================================================================== */
function spinOut(k,strong){
  if(k.starT>0||k.immT>0||k.finished)return false;
  k.spinT=strong?1.25:1.05;k.immT=1.8;k.vel.multiplyScalar(.25);
  if(k.drift)releaseDrift(k);
  if(k.isPlayer){noiseHit(500,.5,.4);shake=.5;}
  return true;
}
function collideKarts(){
  for(let i=0;i<karts.length;i++)for(let j=i+1;j<karts.length;j++){
    const a=karts[i],b=karts[j];
    const dx=b.pos.x-a.pos.x,dz=b.pos.z-a.pos.z,d2=dx*dx+dz*dz;
    if(d2<4.6&&d2>1e-6){
      const d=Math.sqrt(d2),nx=dx/d,nz=dz/d,ov=(2.15-d)/2;
      a.pos.x-=nx*ov;a.pos.z-=nz*ov;b.pos.x+=nx*ov;b.pos.z+=nz*ov;
      const rv=(b.vel.x-a.vel.x)*nx+(b.vel.z-a.vel.z)*nz;
      if(rv<0){const imp=rv*.55;a.vel.x+=nx*imp;a.vel.z+=nz*imp;b.vel.x-=nx*imp;b.vel.z-=nz*imp;
        if((-rv)>7){noiseHit(300,.2,.25);
          if(a.starT>0)spinOut(b);else if(b.starT>0)spinOut(a);}}
    }
  }
}
function updHazards(dt){
  /* bananas */
  for(let i=bananas.length-1;i>=0;i--){
    const b=bananas[i];b.life-=dt;b.grp.rotation.y+=dt*1.5;
    if(b.life<=0){world.remove(b.grp);bananas.splice(i,1);continue;}
    for(const k of karts){
      if(k.ownerImmune>k.ageSkip)break;
      const dx=k.pos.x-b.p.x,dz=k.pos.z-b.p.z;
      if(dx*dx+dz*dz<2.1&&k.immT<=0){
        if(k.starT>0){sparks.emit(b.p,_nv.set(0,3,0),0xffd23f,3,.5);world.remove(b.grp);bananas.splice(i,1);break;}
        if(spinOut(k)){world.remove(b.grp);bananas.splice(i,1);}
        break;
      }
    }
  }
  /* shells */
  for(let i=shells.length-1;i>=0;i--){
    const s=shells[i];s.life-=dt;s.mesh.rotation.y+=dt*14;
    let kill=s.life<=0;
    if(s.kind==='green'){
      s.p.addScaledVector(s.dir,44*dt);
      const si=nearestIdx(s.p.x,s.p.z),SS=S_SIDE[si];
      const lt=(s.p.x-S_P[si].x)*SS.x+(s.p.z-S_P[si].z)*SS.z;
      if(Math.abs(lt)>WALL_LAT-1){                        // bounce
        s.dir.reflect(SS.clone().multiplyScalar(Math.sign(lt)));s.bounce--;
        noiseHit(900,.15,.2);if(s.bounce<=0)kill=true;
      }
      s.p.y=roadOrGroundLite(si,lt)+.6;
    } else {                                              // red homing
      const v=s.victim;
      if(!v||v.finished)v=null;
      const aim=v?v.pos:s.p.clone().addScaledVector(s.lastDir,10);
      _tv.subVectors(aim,s.p).setY(0).normalize();
      s.lastDir.lerp(_tv,Math.min(1,dt*4.5)).normalize();
      s.p.addScaledVector(s.lastDir,46*dt);
      s.p.y=roadOrGroundLite(nearestIdx(s.p.x,s.p.z),0)+.7;
      if(v){const dd=s.p.distanceTo(v.pos);if(dd<2){if(spinOut(v))explodeFx(v.pos);kill=true;}}
    }
    for(const k of karts){
      if(k===s.owner&&s.grace>0)continue;
      const dx=k.pos.x-s.p.x,dz=k.pos.z-s.p.z;
      if(dx*dx+dz*dz<2.4&&k.immT<=0){
        if(k.starT>0){explodeFx(s.p);kill=true;break;}
        if(spinOut(k)){explodeFx(s.p);kill=true;}break;
      }
    }
    s.grace-=dt;
    if(Math.random()<dt*30)smokes.emit(s.p,_nv.set(0,.5,0),s.kind==='red'?0xff8866:0x9adf9a,1.6,.3);
    s.mesh.position.copy(s.p);
    if(kill){world.remove(s.mesh);shells.splice(i,1);}
  }
}
function roadOrGroundLite(idx,lat){
  const al=Math.abs(lat),cy=S_P[idx].y;
  if(al<=ROAD_W+CURB_W)return cy;
  const f=clamp((al-ROAD_W-CURB_W)/6,0,1);
  return lerp(cy,groundY(S_P[idx].x+S_SIDE[idx].x*lat,S_P[idx].z+S_SIDE[idx].z*lat),f*f*(3-2*f));
}
function nearestIdx(x,z){
  let best=0,bd=1e18;
  for(let i=0;i<NS;i+=4){const dx=S_P[i].x-x,dz=S_P[i].z-z,d=dx*dx+dz*dz;if(d<bd){bd=d;best=i;}}
  return best;
}
function explodeFx(p){for(let i=0;i<14;i++)sparks.emit(p,_nv.set(rnd(-5,5),rnd(2,7),rnd(-5,5)),0xffa53d,2.4,.5);noiseHit(700,.35,.35);}

/* =====================================================================
   ITEM SYSTEM
===================================================================== */
const ICON={
  mush:`<svg viewBox="0 0 48 48"><path d="M24 4C12 4 4 13 4 21c0 4 3 6 8 6h24c5 0 8-2 8-6C44 13 36 4 24 4z" fill="#e8402a"/><circle cx="14" cy="14" r="4" fill="#fff3df"/><circle cx="30" cy="10" r="3.4" fill="#fff3df"/><rect x="17" y="27" width="14" height="14" rx="5" fill="#ffe9d2"/><circle cx="21" cy="34" r="1.6" fill="#241420"/><circle cx="28" cy="34" r="1.6" fill="#241420"/></svg>`,
  tmush:`<svg viewBox="0 0 48 48">${ICON_M()}</svg>`,
  banana:`<svg viewBox="0 0 48 48"><path d="M8 12c2 14 12 24 30 24 4 0 6-2 6-5-14 0-24-8-28-21-1-3-8-2-8 2z" fill="#ffd23f" stroke="#241420" stroke-width="2.5"/><path d="M40 33l4 4" stroke="#7a5220" stroke-width="4" stroke-linecap="round"/></svg>`,
  green:`<svg viewBox="0 0 48 48"><path d="M24 4a20 20 0 0 1 20 20H4A20 20 0 0 1 24 4z" fill="#35d052"/><ellipse cx="24" cy="30" rx="21" ry="7" fill="#fff3df"/><circle cx="15" cy="14" r="3" fill="#1d7a33"/><circle cx="29" cy="11" r="3" fill="#1d7a33"/></svg>`,
  red:`<svg viewBox="0 0 48 48"><path d="M24 4a20 20 0 0 1 20 20H4A20 20 0 0 1 24 4z" fill="#e8402a"/><ellipse cx="24" cy="30" rx="21" ry="7" fill="#fff3df"/><circle cx="15" cy="14" r="3" fill="#8f1d12"/><circle cx="29" cy="11" r="3" fill="#8f1d12"/></svg>`,
  star:`<svg viewBox="0 0 48 48"><path d="M24 3l5.8 13.2L44 18l-11 10 3 14.6L24 35l-12 7.6L15 28 4 18l14.2-1.8z" fill="#ffc93c" stroke="#241420" stroke-width="2.5"/></svg>`};
function ICON_M(){return `<g transform="translate(2,4) scale(.62)"><path d="M24 4C12 4 4 13 4 21c0 4 3 6 8 6h24c5 0 8-2 8-6C44 13 36 4 24 4z" fill="#e8402a"/><rect x="17" y="27" width="14" height="14" rx="5" fill="#ffe9d2"/></g><g transform="translate(20,-2) scale(.62)"><path d="M24 4C12 4 4 13 4 21c0 4 3 6 8 6h24c5 0 8-2 8-6C44 13 36 4 24 4z" fill="#e8402a"/><rect x="17" y="27" width="14" height="14" rx="5" fill="#ffe9d2"/></g><g transform="translate(10,14) scale(.62)"><path d="M24 4C12 4 4 13 4 21c0 4 3 6 8 6h24c5 0 8-2 8-6C44 13 36 4 24 4z" fill="#e8402a"/><rect x="17" y="27" width="14" height="14" rx="5" fill="#ffe9d2"/></g>`;}

function weightPick(rank){
  const tbl=
    rank<=2? [['banana',.42],['green',.3],['mush',.16],['red',.07],['star',.05]]:
    rank<=5? [['green',.26],['red',.24],['mush',.2],['banana',.16],['star',.14]]:
             [['tmush',.3],['red',.25],['star',.2],['mush',.15],['green',.1]];
  let r=Math.random(),acc=0;
  for(const [it,w] of tbl){acc+=w;if(r<=acc)return it;}
  return 'mush';
}
function giveItem(k,it){
  k.item=it;k.chrg=it==='tmush'?3:1;
  if(k.isPlayer){renderItem();beep(880,.09,'square',.2);setTimeout(()=>beep(1175,.12,'square',.2),90);}
}
function useItem(k){
  if(!k.item||k.spinT>0)return;
  const it=k.item;
  const consume=()=>{if(it!=='tmush'){k.item=null;}else{k.chrg--;if(k.chrg<=0)k.item=null;}if(k.isPlayer)renderItem();};
  if(it==='mush'||it==='tmush'){applyBoost(k,1.35);consume();}
  else if(it==='banana'){
    const bp=rearAxle(k).clone();bp.y=roadOrGroundLite(k.idx,k.lat)+0;
    const gm=bananaMesh();gm.position.copy(bp);world.add(gm);
    bananas.push({grp:gm,p:bp,life:25});consume();beep(220,.12,'triangle',.2);
  }
  else if(it==='green'||it==='red'){
    const m=shellMesh(it==='red');
    const dir=new THREE.Vector3(Math.sin(k.yaw),0,Math.cos(k.yaw));
    const p=k.pos.clone().addScaledVector(dir,2.4);p.y+=.6;
    m.position.copy(p);world.add(m);
    const sh={kind:it,mesh:m,p,owner:k,grace:.7,life:it==='red'?12:9,bounce:3,
      dir:dir.clone(),victim:null,lastDir:dir.clone()};
    if(it==='red'){
      const sorted=[...karts].sort((a,b)=>b.progTot()-a.progTot());
      const ri=sorted.indexOf(k);sh.victim=ri>0?sorted[ri-1]:sorted[1]||null;
    }
    shells.push(sh);consume();noiseHit(1500,.2,.25);
  }
  else if(it==='star'){k.starT=6.5;consume();
    [523,659,784,1046].forEach((f,i)=>setTimeout(()=>beep(f,.15,'square',.22),i*90));}
}
Object.defineProperty(Object.prototype,'progTot',{value:function(){return this.lap+this.prog;},enumerable:false});

/* roulette for player */
let rouT=0,rouActive=false;
function startRoulette(){rouActive=true;rouT=1.15;$('itemSlot').classList.add('spin');}
function updRoulette(dt){
  if(!rouActive)return;
  rouT-=dt;
  const seq=['mush','banana','green','red','star','tmush'];
  $('itemArt').innerHTML=ICON[seq[Math.floor(performance.now()/70)%seq.length]];
  if(rouT<=0){rouActive=false;$('itemSlot').classList.remove('spin');
    giveItem(player(),weightPick(currentRank(player())));}
}
function renderItem(){
  const k=player();
  $('itemArt').innerHTML=k.item?ICON[k.item]:'';
  $('itemCharges').style.display=(k.item==='tmush')?'flex':'none';
  if(k.item==='tmush')$('itemCharges').textContent=k.chrg;
}

/* =====================================================================
   AI DRIVER BRAINS
===================================================================== */
function aiThink(k,dt){
  const inp={thr:1,brk:0,steer:0,drift:false,item:false};
  if(k.finished){inp.thr=.4;}
  /* lane wandering + obstacle dodging */
  let laneT=k.pers.lane+Math.sin(clockT*.4+k.pers.seed)*2.4;
  for(const b of bananas){
    const rel=_tv.subVectors(b.p,k.pos);const fw=_nv.set(Math.sin(k.yaw),0,Math.cos(k.yaw));
    const ah=rel.dot(fw);
    if(ah>0&&ah<12){const ss=_tv.crossVectors([0,1,0].length?fwdTmp():fw,fw).x;/*fallback*/
      const side=rel.x*Math.cos(k.yaw)-rel.z*Math.sin(k.yaw);
      if(Math.abs(side)<3)laneT=k.lat+(side>=0?-4:4);}
  }
  k.laneCur+=(laneT-k.laneCur)*Math.min(1,dt*1.6);
  /* steer toward lookahead */
  const la=SMOD(k.idx+clamp(Math.round(k.vel.length()*.55),6,42));
  sampleAt(la,_sv);
  _tv.copy(_sv.p).addScaledVector(_sv.s,k.laneCur);
  const dy=wrapPI(Math.atan2(_tv.x-k.pos.x,_tv.z-k.pos.z)-k.yaw);
  inp.steer=clamp(-dy*2.4,-1,1);
  /* curvature-aware speed target */
  let vk=33;
  for(let o=4;o<34;o+=3){
    const kk=Math.abs(S_K[SMOD(k.idx+o)])*(1-o/40);
    if(kk>1e-4)vk=Math.min(vk,Math.sqrt(11/kk));
  }
  const top=33*k.pers.top*rubber(k);
  vk=Math.min(vk,top);
  const sp=k.vel.length();
  inp.thr=sp<vk-1?1:(sp>vk+2?0:.4);
  inp.brk=sp>vk+6?1:0;
  /* occasional cosmetic drift sparks on fast sweeps */
  if(Math.abs(dy)>.5&&sp>20&&Math.random()<dt*3)
    sparks.emit(wWheelWorld(k,1),_nv.set(rnd(-2,2),rnd(1,3),rnd(-2,2)),0x9adcff,1.4,.3);
  /* item behaviour */
  if(k.item&&!k.finished){
    k.aiDelay=(k.aiDelay||rnd(.5,1.6))-dt;
    if(k.aiDelay<=0){
      if(k.item==='mush'||k.item==='tmush'||k.item==='star')useItem(k);
      else if(k.item==='banana'&&Math.random()<.5)useItem(k);
      else if((k.item==='green'||k.item==='red')){
        const fw=_nv.set(Math.sin(k.yaw),0,Math.cos(k.yaw));
        let aimed=false;
        for(const o of karts){if(o===k)continue;
          const rel=_tv.subVectors(o.pos,k.pos);
          if(rel.dot(fw)>6&&rel.dot(fw)<70&&Math.abs(rel.normalizedCross(fw))<4){aimed=true;break;}}
        if(aimed||k.item==='red')useItem(k);
      }
      k.aiDelay=rnd(.6,1.5);
    }
  }
  return inp;
}
const _cx=new THREE.Vector3();
function fwdTmp(){return _cx;}
function rubber(k){
  const gap=currentRank(k)-currentRank(player());
  if(gap>0)return .93;                  // ahead of player: ease off
  if(gap<=-2)return 1.06;               // far behind: catch up
  return 1;
}
function currentRank(k){return ranks.indexOf(k)+1;}
let ranks=[];
function updateRanks(){
  ranks=[...karts].sort((a,b)=>(b.finished?1e6-b.ft:b.lap+b.prog)-(a.finished?1e6-a.ft:a.lap+a.prog));
}

/* =====================================================================
   VISUAL SYNC OF KART MODELS
===================================================================== */
function syncModel(k,dt){
  const m=k.mdl;
  m.group.position.copy(k.pos);
  /* pitch from slope ahead/behind along tangent */
  const ti=S_T[k.idx];
  const ay=S_P[SMOD(k.idx+2)].y,by=S_P[SMOD(k.idx-2)].y;
  const pit=-Math.atan2(ay-by,5.6);
  const lean=k.drift?-k.driftDir*.14:-k.steer*.07*clamp(k.vel.length()/20,0,1);
  m.group.rotation.set(pit,k.yaw,lean,'YXZ');
  if(k.spinT>0)m.core.rotation.y=(1-k.spinT/1.05)*Math.PI*4;
  else m.core.rotation.y*= (1-Math.min(1,dt*10));
  /* wheels */
  const ws=k.vel.length()*dt/.42;
  m.wheels.forEach(w=>w.rotation.x+=ws);
  m.front.forEach(f=>f.rotation.y=k.steer*-.42);
  /* flames */
  const fl=k.boostT>0||k.starT>0;
  m.flames.forEach(f=>{f.visible=fl;if(fl)f.scale.set(1,rnd(.7,1.5),1);});
  /* star shimmer */
  if(k.starT>0){
    const h=(clockT*2)%1;
    m.bodyMat.emissive.setHSL(h,.9,.45);m.helmMat.emissive.setHSL(1-h,.9,.4);
  } else {m.bodyMat.emissive.setHex(0);m.helmMat.emissive.setHex(0);}
}

/* =====================================================================
   CAMERA
===================================================================== */
const camPos=new THREE.Vector3(0,30,-120),camLook=new THREE.Vector3();
let shake=0,fovT=63;
function chaseCam(dt,instant){
  const k=player();
  const vd=k.vel.lengthSq()>1?_tv.copy(k.vel).normalize():_tv.set(Math.sin(k.yaw),0,Math.cos(k.yaw));
  const tgt=_nv.copy(k.pos).addScaledVector(vd,-6.6).add({x:0,y:3.4,z:0}?new THREE.Vector3(0,3.4,0):null);
  tgt.copy(k.pos).addScaledVector(vd,-6.6);tgt.y=k.pos.y+3.4;
  if(instant)camPos.copy(tgt);
  else camPos.lerp(tgt,1-Math.exp(-dt*5.5));
  camLook.lerp(_tv.copy(k.pos).addScaledVector(vd,3).setY(k.pos.y+1.4),1-Math.exp(-dt*8));
  camera.position.copy(camPos);
  if(shake>0){shake-=dt*1.6;
    camera.position.x+=rnd(-1,1)*shake*.4;camera.position.y+=rnd(-1,1)*shake*.3;}
  camera.lookAt(camLook);
  const wantFov=63+(k.boostT>0?12:0)+(k.starT>0?6:0)+clamp(k.vel.length()-24,0,10)*.4;
  fovT+=(wantFov-fovT)*Math.min(1,dt*5);
  camera.fov=fovT;camera.updateProjectionMatrix();
}

/* =====================================================================
   MINIMAP
===================================================================== */
const mmc=$('minimap'),mmc2=mmc.getContext('2d');
let mmFit=null;
function mmSetup(){
  let minX=1e9,maxX=-1e9,minZ=1e9,maxZ=-1e9;
  S_P.forEach(p=>{minX=Math.min(minX,p.x);maxX=Math.max(maxX,p.x);minZ=Math.min(minZ,p.z);maxZ=Math.max(maxZ,p.z);});
  const pad=14,W=mmc.clientWidth,H=mmc.clientHeight;
  const sx=(W-pad*2)/(maxX-minX),sz=(H-pad*2)/(maxZ-minZ),s=Math.min(sx,sz);
  mmFit={s,ox:pad+(W-pad*2-(maxX-minX)*s)/2-minX*s,oz:H-pad-(H-pad*2-(maxZ-minZ)*s)/2-maxZ*(-s)};
  mmc.width=W*devicePixelRatio;mmc.height=H*devicePixelRatio;mmc2.scale(devicePixelRatio,devicePixelRatio);
}
const mmXY=(x,z)=>[mmFit.ox+x*mmFit.s,mmFit.oz-z*(-mmFit.s)*-1];
function drawMini(){
  if(!mmFit)return;
  const W=mmc.clientWidth,H=mmc.clientHeight;
  mmc2.clearRect(0,0,W,H);
  mmc2.lineJoin='round';mmc2.beginPath();
  for(let i=0;i<=NS;i+=5){const p=S_P[i%NS];
    const[x,y]=[mmFit.ox+p.x*mmFit.s,mmFit.oz+p.z*-mmFit.s*-1];
    const yy=mmFit.oz-p.z*mmFit.s*-1; // canonical
    const py=mmFit.oz+p.z*mmFit.s*-1;
    i===0?mmc2.moveTo(x,py):mmc2.lineTo(x,py);}
  mmc2.closePath();
  mmc2.strokeStyle='rgba(255,243,223,.28)';mmc2.lineWidth=7;mmc2.stroke();
  mmc2.strokeStyle='#fff3df';mmc2.lineWidth=3;mmc2.stroke();
  for(const k of karts){
    const x=mmFit.ox+k.pos.x*mmFit.s,y=mmFit.oz-k.pos.z*mmFit.s;
    mmc2.beginPath();mmc2.arc(x,y,k.isPlayer?5:3.4,0,7);
    mmc2.fillStyle='#'+new THREE.Color(k.col).getHexString();mmc2.fill();
    if(k.isPlayer){mmc2.lineWidth=2;mmc2.strokeStyle='#fff';mmc2.stroke();}
  }
  for(const s of shells){
    const x=mmFit.ox+s.p.x*mmFit.s,y=mmFit.oz-s.p.z*mmFit.s;
    mmc2.beginPath();mmc2.arc(x,y,2.4,0,7);mmc2.fillStyle=s.kind==='red'?'#ff3b2f':'#35d052';mmc2.fill();
  }
}

/* =====================================================================
   HUD HELPERS
===================================================================== */
function bannerMsg(txt){const b=$('banner');b.textContent=txt;b.classList.remove('show');void b.offsetWidth;b.classList.add('show');}
function onLap(k){
  if(k.lap>TOTAL_LAPS||k.finished)return;
  const t=clockT-k.lapStart;k.lapStart=clockT;
  k.lapTimes.push(t);
  if(!k.best||t<k.best)k.best=t;
  if(k.isPlayer){
    if(k.lap<TOTAL_LAPS){
      bannerMsg(`LAP ${k.lap}/${TOTAL_LAPS} — ${fmtT(t)}`);
      beep(660,.12,'square',.25);setTimeout(()=>beep(880,.18,'square',.25),120);
      if(k.lap===TOTAL_LAPS){$('lapPlate').classList.add('final');$('lapPlate').innerHTML='FINAL LAP!';
        AU.intensity=1;bannerMsg('FINAL LAP!');}
      updateLapPlate();
    } else finishKart(k);
  } else if(k.lap>=TOTAL_LAPS)finishKart(k);
}
function updateLapPlate(){
  const k=player();
  if(!$('lapPlate').classList.contains('final'))
    $('lapPlate').innerHTML=`LAP ${Math.min(k.lap+1,TOTAL_LAPS)}<span style="opacity:.55">/${TOTAL_LAPS}</span>`;
}
function finishKart(k){
  k.finished=true;k.ft=clockT;
  if(k.isPlayer){
    state='over';AU.intensity=0;
    bannerMsg(k.rankAtFinish? '' :'');
    setTimeout(showResults,1400);
    confetti(k.pos);
    [784,988,1175,1568].forEach((f,i)=>setTimeout(()=>beep(f,.3,'square',.25),i*140));
  }
}
function showResults(){
  updateRanks();
  const rows=$('resRows');rows.innerHTML='';
  const medals=['&#129351;','&#129352;','&#129353;'];
  ranks.forEach((k,i)=>{
    const row=document.createElement('div');
    row.className='resRow'+(k.isPlayer?' me':'');
    row.innerHTML=`<div class="medal">${medals[i]||(i+1)}</div>
      <div class="chip" style="background:#${new THREE.Color(k.col).getHexString()}"></div>
      <div class="nm">${k.name}${k.finished?'':' <small style="opacity:.6">(racing)</small>'}</div>
      <div class="tm">${k.finished?fmtT(k.ft):''}${k.best?'&nbsp;<small>BEST '+fmtT(k.best)+'</small>':''}</div>`;
    rows.appendChild(row);
  });
  $('resTitle').textContent=ranks[0].isPlayer?'VICTORY!':'FINISH!';
  $('results').style.display='flex';
}

/* =====================================================================
   GAME STATE MACHINE
===================================================================== */
let state='menu',clockT=0,countT=0,resIntro=0;
const player=()=>karts.find(k=>k.isPlayer);
function setState(s){state=s;}

function beginRace(){
  makeKarts();makeBoxes();
  bananas.forEach(b=>world.remove(b.grp));bananas.length=0;
  shells.forEach(s=>world.remove(s.mesh));shells.length=0;
  ranks=[...karts].reverse();
  clockT=0;countT=3.6;setState('count');
  $('menu').style.display='none';$('results').style.display='none';
  $('hud').style.display='block';$('muteBtn').style.display='flex';
  $('count').style.display='flex';$('lapPlate').classList.remove('final');
  $('lapPlate').innerHTML=`LAP 1<span style="opacity:.55">/3</span>`;
  $('bestTag').textContent='';$('wrongWay').style.display='none';
  renderItem();mmSetup();
  karts.forEach(k=>{k.lapStart=0;});
  resIntro=0;
}
function togglePause(force){
  if(state==='run'||force===true&&state==='run'){paused=!paused;
    $('pause').style.display=paused?'flex':'none';}
}
let paused=false;
$('resumeBtn').onclick=()=>{paused=false;$('pause').style.display='none';};
$('quitBtn').onclick=()=>{paused=false;$('pause').style.display='none';
  $('hud').style.display='none';$('menu').style.display='flex';setState('menu');initIdleScene();};
$('restartBtn').onclick=()=>beginRace();
$('startBtn').onclick=()=>{auInit();auResume();beginRace();};
function auResume(){if(AU.ctx&&AU.ctx.state==='suspended')AU.ctx.resume();}
function toggleMute(){
  AU.on=!AU.on;$('muteBtn').classList.toggle('muted',!AU.on);
  if(AU.master)AU.master.gain.value=AU.on?.9:0;
}
$('muteBtn').onclick=toggleMute;

/* idle attract-mode camera for the menu */
let idleA=0;
function initIdleScene(){}
function idleCam(dt){
  idleA+=dt*.07;
  const r=150;
  camera.position.set(Math.cos(idleA)*r,34+Math.sin(idleA*.6)*10,Math.sin(idleA)*r);
  camera.lookAt(0,4,0);camera.fov=58;camera.updateProjectionMatrix();
}

/* =====================================================================
   MAIN UPDATE
===================================================================== */
let last=performance.now();
function frame(now){
  requestAnimationFrame(frame);
  let dt=Math.min((now-last)/1000,.05);last=now;
  if(paused){renderer.render(scene,camera);return;}
  clockT+=dt;

  /* ambience motion */
  clouds.forEach((c,i)=>{c.position.x+=dt*(1+i*.15);if(c.position.x>480)c.position.x=-480;});
  balloons.forEach((b,i)=>{b.position.y+=Math.sin(clockT*.5+i)*dt*.6;b.rotation.y+=dt*.1;});
  boxes.forEach(b=>{
    if(!b.active){b.respT-=dt;if(b.respT<=0){b.active=true;b.cube.scale.setScalar(.01);}
      else{b.grp.visible=false;return;}}
    b.grp.visible=true;
    b.cube.scale.lerp(new THREE.Vector3(1,1,1),Math.min(1,dt*5));
    b.q.material.rotation+=dt*2;
    b.grp.position.y=b.base.y+Math.sin(clockT*2+b.ph)*.25;
    b.cube.material.color.setHSL((clockT*.25+b.ph)%1,.75,.62);
  });

  if(state==='menu'){idleCam(dt);updPools(dt);renderer.render(scene,camera);return;}

  if(state==='count'){
    countT-=dt;
    const k=player();
    /* cinematic swing around the grid */
    const f=clamp(1-countT/3.6,0,1),e=f*f*(3-2*f);
    const az=lerp(-2.4,-.15,e),el=lerp(.9,.32,e),rr=lerp(13,7,e);
    camera.position.set(k.pos.x+Math.sin(az)*rr,k.pos.y+Math.sin(el)*rr+2,k.pos.z+Math.cos(az)*rr);
    camera.lookAt(k.pos.x,k.pos.y+1.2,k.pos.z);
    const sec=Math.ceil(countT);
    if(sec!==frame._ls&&sec<=3&&sec>0){
      frame._ls=sec;
      $('cdText').textContent=sec;$('cdText').classList.remove('zoom');void $('cdText').offsetWidth;$('cdText').classList.add('zoom');
      $( 'lp'+sec)?.classList.add('on'+sec);beep(440,.18,'square',.3);
    }
    if(countT<=0){
      setState('run');$('count').style.display='none';
      $('cdText').textContent='GO!';$('cdText').classList.add('zoom');
      setTimeout(()=>$('cdText').textContent='',700);
      document.querySelectorAll('.lamp').forEach(l=>l.className='lamp go');
      setTimeout(()=>document.querySelectorAll('.lamp').forEach(l=>l.className='lamp'),900);
      beep(880,.5,'square',.35);
      karts.forEach(kk=>kk.lapStart=0);
      frame._ls=0;
    }
    karts.forEach(syncDummyOnly);
    updPools(dt);renderer.render(scene,camera);drawMini();return;
  }

  /* ------- RUN / OVER ------- */
  const pk=player();
  let pInp=readInput(pk);
  if(pk.finished)pInp=aiThink(pk,dt);
  physStep(pk,pInp,dt);

  for(const k of karts){
    if(k.isPlayer)continue;
    const ainp=aiThink(k,dt);
    physStep(k,ainp,dt);
  }
  collideKarts();
  updHazards(dt);
  updRoulette(dt);
  updateRanks();

  /* item box pickups */
  for(const b of boxes){
    if(!b.active)continue;
    for(const k of karts){
      if(k.immT>0)continue;
      if(k.pos.distanceToSquared(b.p)<4.6){
        b.active=false;b.respT=3;b.cube.scale.setScalar(.01);
        sparks.emit(b.p,_nv.set(0,2,0),0x8fe3ff,3,.4);
        if(k.isPlayer)startRoulette();
        else setTimeout(()=>giveItem(k,weightPick(currentRank(k))),rnd(300,1100));
        break;
      }
    }
  }
  /* player item fire */
  if(pInp.item&&!pk.prevItem)useItem(pk);
  pk.prevItem=pInp.item;

  /* wrong way detector */
  const fdot=Math.sin(pk.yaw)*S_T[pk.idx].x+Math.cos(pk.yaw)*S_T[pk.idx].z;
  if(fdot<-.45&&pk.vel.length()>4)pk.wrongT+=dt;else pk.wrongT=0;
  $('wrongWay').style.display=pk.wrongT>.8?'block':'none';

  /* models + camera */
  karts.forEach(k=>syncModel(k,dt));
  chaseCam(dt,state==='over'&&resIntro++<1);

  /* engine audio */
  if(AU.ctx&&AU.on){
    const eg=AU.engNodes,sp=pk.vel.length()/33;
    eg.o1.frequency.value=55+sp*185+Math.sin(clockT*30)*3;
    eg.o2.frequency.value=(55+sp*185)*.5;
    eg.lp.frequency.value=500+sp*1800;
    eg.g.gain.value=state==='run'||state==='over'?.09+sp*.1:.05;
    eg.wind.gain.value=sp*sp*.12;
  }

  /* HUD */
  const rk=currentRank(pk);
  if(rk!==frame._rk){frame._rk=rk;
    $('posNum').textContent=rk;$('posOrd').textContent=ORD(rk);
    $('posPlate').classList.remove('pop');void $('posPlate').offsetWidth;$('posPlate').classList.add('pop');}
  $('speedVal').textContent=Math.round(pk.vel.length()*3.6);
  $('raceClock').textContent=fmtT(clockT);
  if(pk.best)$('bestTag').textContent='BEST LAP '+fmtT(pk.best);
  if(pk.item==='tmush')$('itemCharges').textContent=pk.chrg;

  /* sun follows action */
  sun.position.copy(pk.pos).add(new THREE.Vector3(60,90,35));
  sun.target.position.copy(pk.pos);

  updPools(dt);updConf(dt);
  renderer.render(scene,camera);
  drawMini();
}
function syncDummyOnly(k){k.mdl.group.position.copy(k.pos);k.mdl.group.rotation.set(0,k.yaw,0);}
function updPools(dt){sparks.update(dt);smokes.update(dt);}

/* boot */
makeKarts();          // pre-place grid so menu backdrop shows the field
mmSetup();
requestAnimationFrame(frame);

addEventListener('resize',()=>{
  camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);mmSetup();
});
</script>
</body>
</html>
