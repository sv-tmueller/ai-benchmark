# Bridge Horror House

```json path=bridge-horror-house/package.json
{
  "name": "bridge-horror-house",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "three": "^0.160.0"
  },
  "devDependencies": {
    "vite": "^5.4.0"
  }
}
```

```markdown path=bridge-horror-house/SYSTEM_PROMPT.md
# BRIDGE HORROR HOUSE — DESIGN CONSTITUTION

First-person haunted-house escape. Three brass keys, one front door, one entity.

Priority order: 1. graphics / atmosphere, 2. functionality, 3. everything else.

- Darkness is a mechanic: the flashlight is the only real light and the only shadow caster.
- ACES tone mapping, exponential black fog, subtle bloom, vignette, film grain, dust motes.
- All textures are procedural canvas textures; all audio is synthesized Web Audio. Zero asset files.
- Scripted scares are one-shot. Anticipation beats the scare. Never two big scares back-to-back.
- Escalation: act 1 noises, act 2 (2nd key) stalking, act 3 (final key) blackout and chase.
- The beam burns the entity. Banish buys about 8 seconds in the finale. Battery is the resource.
- Death is fast: jumpscare, scream, restart. The chase is always winnable.
- Fixed floor plan: study / bedroom / kitchen (north), hallway, living / foyer / dining (south).
- Do not build: multiplayer, saves, inventories, extra floors, extra entities, external assets, touch controls.
```

```html path=bridge-horror-house/index.html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Bridge Horror House</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; color: #cfc8b8;
    font-family: Georgia, 'Times New Roman', serif; user-select: none; }
  #app { position: fixed; inset: 0; }
  #app canvas { display: block; width: 100%; height: 100%; }
  .layer { position: fixed; inset: 0; pointer-events: none; }
  #vignette { background: radial-gradient(ellipse at center, rgba(0,0,0,0) 38%, rgba(0,0,0,0.55) 72%, rgba(0,0,0,0.96) 100%); }
  #grain { width: 100%; height: 100%; opacity: 0.09; image-rendering: pixelated; mix-blend-mode: screen; }
  #flash { background: #fff; opacity: 0; }
  #hud { display: none; }
  #objective { position: absolute; top: 22px; left: 26px; font-size: 15px; letter-spacing: 1px; opacity: 0.75; text-shadow: 0 0 6px #000; }
  #keys { position: absolute; top: 22px; right: 26px; font-size: 16px; letter-spacing: 2px; color: #c9a14a; text-shadow: 0 0 8px #000; }
  #battery { position: absolute; left: 26px; bottom: 26px; width: 170px; }
  #battery .label { font-size: 11px; letter-spacing: 3px; opacity: 0.6; margin-bottom: 5px; }
  #battery .bar { height: 7px; border: 1px solid rgba(207,200,184,0.4); background: rgba(0,0,0,0.5); }
  #batteryFill { height: 100%; width: 100%; background: #d8c98a; transition: width 0.2s; }
  #crosshair { position: absolute; left: 50%; top: 50%; width: 4px; height: 4px; margin: -2px 0 0 -2px; border-radius: 50%; background: rgba(255,255,255,0.45); }
  #burn { position: absolute; left: 50%; top: calc(50% - 46px); width: 150px; margin-left: -75px; height: 6px;
    border: 1px solid rgba(255,220,190,0.6); background: rgba(0,0,0,0.5); opacity: 0; transition: opacity 0.2s; }
  #burnFill { height: 100%; width: 0%; background: linear-gradient(90deg, #ffb060, #fff); box-shadow: 0 0 10px #ffa040; }
  #prompt { position: absolute; left: 50%; top: calc(50% + 34px); transform: translateX(-50%); font-size: 14px; letter-spacing: 1px; text-shadow: 0 0 6px #000; opacity: 0.85; }
  #message { position: absolute; left: 50%; bottom: 17%; transform: translateX(-50%); font-size: 18px; font-style: italic;
    letter-spacing: 1px; text-shadow: 0 0 10px #000; opacity: 0; transition: opacity 0.5s; text-align: center; max-width: 70%; }
  .screen { position: fixed; inset: 0; display: none; align-items: center; justify-content: center; flex-direction: column;
    text-align: center; background: rgba(0,0,0,0.93); pointer-events: auto; }
  .screen h1 { font-weight: normal; letter-spacing: 12px; font-size: 46px; margin: 0 0 12px; color: #b9ab94; text-shadow: 0 0 24px rgba(160,20,10,0.6); }
  .screen p { max-width: 520px; line-height: 1.7; opacity: 0.75; margin: 6px 20px; }
  .screen .small { font-size: 13px; letter-spacing: 1px; opacity: 0.5; }
  .btn { margin-top: 26px; padding: 12px 34px; border: 1px solid #7a6c58; background: transparent; color: #cfc8b8;
    font-family: inherit; font-size: 15px; letter-spacing: 4px; cursor: pointer; }
  .btn:hover { background: #2a0806; border-color: #b33; }
  #title { display: flex; background: radial-gradient(ellipse at center, #0c0606 0%, #000 70%); }
  #death h1 { color: #a01010; }
  #note { background: rgba(0,0,0,0.78); }
  #notePaper { max-width: 440px; padding: 34px 38px; background: #cbbf9f; color: #2a2118; font-size: 17px; line-height: 1.7;
    font-style: italic; box-shadow: 0 0 60px #000; transform: rotate(-1.2deg); white-space: pre-line; text-align: left; }
  #jump { position: fixed; inset: 0; display: none; background: #000 center / cover no-repeat; }
  @keyframes jitter { 0% { transform: scale(1.3) translate(0,0); } 25% { transform: scale(1.5) translate(-3%,2%); }
    50% { transform: scale(1.4) translate(3%,-2%); } 75% { transform: scale(1.65) translate(-2%,-3%); } 100% { transform: scale(1.5) translate(2%,3%); } }
  #jump.on { display: block; animation: jitter 0.09s infinite; }
</style>
</head>
<body>
<div id="app"></div>
<div id="vignette" class="layer"></div>
<canvas id="grain" class="layer" width="160" height="90"></canvas>
<div id="flash" class="layer"></div>

<div id="hud" class="layer">
  <div id="objective"></div>
  <div id="keys">KEYS 0/3</div>
  <div id="battery"><div class="label">TORCH</div><div class="bar"><div id="batteryFill"></div></div></div>
  <div id="crosshair"></div>
  <div id="burn"><div id="burnFill"></div></div>
  <div id="prompt"></div>
  <div id="message"></div>
</div>

<div id="note" class="screen"><div id="notePaper"></div><p class="small">[E] put it down</p></div>
<div id="pause" class="screen"><h1>PAUSED</h1><p class="small">Click to return to the house</p></div>
<div id="jump"></div>

<div id="title" class="screen">
  <h1>BRIDGE HORROR HOUSE</h1>
  <p>You wake up locked inside an abandoned house at night. Every exit is sealed. Three brass keys are hidden in the dark. Find them. Unlock the front door. You are not alone in here.</p>
  <p class="small">WASD move &nbsp;·&nbsp; SHIFT sprint &nbsp;·&nbsp; MOUSE look &nbsp;·&nbsp; E interact &nbsp;·&nbsp; F torch<br/>Hold the beam on him. Wear headphones.</p>
  <button id="startBtn" class="btn">ENTER</button>
</div>

<div id="death" class="screen">
  <h1>HE FOUND YOU</h1>
  <p>The house keeps what it catches.</p>
  <button id="retryBtn" class="btn">TRY AGAIN</button>
</div>

<div id="win" class="screen">
  <h1>YOU ESCAPED</h1>
  <p id="winStats"></p>
  <p class="small">The door slams behind you. Something scratches at the other side.</p>
  <button id="againBtn" class="btn">GO BACK IN</button>
</div>

<script type="module" src="/src/main.js"></script>
</body>
</html>
```

```js path=bridge-horror-house/src/main.js
import { Game } from './Game.js';

const game = new Game(document.getElementById('app'));

for (const id of ['startBtn', 'retryBtn', 'againBtn']) {
  document.getElementById(id).addEventListener('click', () => game.start());
}
document.getElementById('pause').addEventListener('click', () => game.resume());
```

```js path=bridge-horror-house/src/Game.js
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Textures } from './world/Textures.js';
import { House } from './world/House.js';
import { Player } from './player/Player.js';
import { AudioEngine } from './systems/AudioEngine.js';
import { Ghost } from './systems/Ghost.js';
import { ScareDirector } from './systems/ScareDirector.js';
import { HUD } from './ui/HUD.js';

const NOTES = {
  foyer: 'To whoever wakes here —\n\nHe sealed every door. The front door takes three brass keys. I hid them where he made me sleep, where he made me cook, and where he made me write.\n\nDo not trust the quiet.',
  study: 'He hates the light.\n\nI held the torch on him and he burned like paper — he screamed and was gone. But only for a while. He always comes back together.\n\nKeep batteries. Keep the beam on his face.',
};

export class Game {
  constructor(container) {
    this.container = container;
    this.state = 'TITLE';
    this.paused = false;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.0;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);

    this.camera = new THREE.PerspectiveCamera(72, window.innerWidth / window.innerHeight, 0.05, 60);
    this.camera.rotation.order = 'YXZ';
    this.tex = new Textures();
    this.audio = new AudioEngine();
    this.hud = new HUD(this.tex);
    this.raycaster = new THREE.Raycaster();
    this.raycaster.far = 2.4;
    this.clock = new THREE.Clock();
    this.fwd = new THREE.Vector3();
    this.tmp = new THREE.Vector3();
    this.center = new THREE.Vector2(0, 0);

    this.build();

    window.addEventListener('resize', () => this.resize());
    window.addEventListener('keydown', (e) => this.onKey(e));
    document.addEventListener('pointerlockchange', () => this.onLockChange());
    this.renderer.setAnimationLoop(() => this.frame());
  }

  build() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);
    this.scene.fog = new THREE.FogExp2(0x000000, 0.105);
    this.house = new House(this.scene, this.tex);
    this.player = new Player(this.camera, this.scene, this.renderer.domElement, this.tex, this.audio);
    this.ghost = new Ghost(this.scene, this.tex);
    this.director = new ScareDirector(this);
    this.buildDust();

    const size = new THREE.Vector2(window.innerWidth, window.innerHeight);
    this.composer = new EffectComposer(this.renderer);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.composer.addPass(new UnrealBloomPass(size, 0.55, 0.6, 0.82));
    this.composer.addPass(new OutputPass());

    this.keys = 0;
    this.banishes = 0;
    this.time = 0;
    this.noteOpen = false;
    this.target = null;
    this.hud.reset();
    this.hud.setObjective('Find a way out');
  }

  buildDust() {
    const n = 380;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    this.dustVel = new Float32Array(n * 3);
    for (let i = 0; i < n * 3; i++) {
      pos[i] = (Math.random() - 0.5) * 8;
      this.dustVel[i] = (Math.random() - 0.5) * 0.06;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const mat = new THREE.PointsMaterial({ size: 0.022, vertexColors: true, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
    this.dust = new THREE.Points(geo, mat);
    this.dust.frustumCulled = false;
    this.scene.add(this.dust);
  }

  updateDust(dt) {
    const p = this.dust.geometry.attributes.position;
    const c = this.dust.geometry.attributes.color;
    const cam = this.camera.position;
    const f = this.fwd;
    const lit = this.player.lightOn ? this.player.flicker : 0;
    for (let i = 0; i < p.count; i++) {
      let x = p.getX(i) + this.dustVel[i * 3] * dt;
      let y = p.getY(i) + this.dustVel[i * 3 + 1] * dt * 0.5;
      let z = p.getZ(i) + this.dustVel[i * 3 + 2] * dt;
      if (x - cam.x > 4) x -= 8; else if (x - cam.x < -4) x += 8;
      if (z - cam.z > 4) z -= 8; else if (z - cam.z < -4) z += 8;
      if (y > 2.9) y = 0.1; else if (y < 0.05) y = 2.9;
      p.setXYZ(i, x, y, z);
      const dx = x - cam.x, dy = y - cam.y, dz = z - cam.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.0001;
      const cos = (dx * f.x + dy * f.y + dz * f.z) / d;
      let b = THREE.MathUtils.smoothstep(cos, 0.88, 0.975) * Math.max(0, 1 - d / 6) * 0.55 * lit;
      if (d < 0.4) b = 0;
      c.setXYZ(i, b, b * 0.92, b * 0.78);
    }
    p.needsUpdate = true;
    c.needsUpdate = true;
  }

  start() {
    this.audio.start();
    if (this.state !== 'TITLE') {
      this.audio.reset();
      this.scene.remove(this.player.spot, this.player.spot.target);
      this.player.dispose();
      this.build();
    }
    this.state = 'PLAYING';
    this.paused = false;
    this.hud.showPlaying();
    this.renderer.domElement.requestPointerLock();
    this.hud.message('The front door is sealed. Three keyholes.', 5);
  }

  resume() {
    this.renderer.domElement.requestPointerLock();
  }

  onLockChange() {
    const locked = document.pointerLockElement === this.renderer.domElement;
    if (this.state === 'PLAYING') {
      this.paused = !locked;
      this.hud.pause(this.paused && !this.noteOpen);
    }
  }

  onKey(e) {
    if (this.state !== 'PLAYING' || this.paused) return;
    if (e.code === 'KeyE') {
      if (this.noteOpen) { this.noteOpen = false; this.hud.hideNote(); return; }
      this.interact();
    }
  }

  findTarget() {
    this.raycaster.setFromCamera(this.center, this.camera);
    const hits = this.raycaster.intersectObjects(this.house.interactables, true);
    for (const h of hits) {
      let o = h.object;
      while (o && !o.userData.interact) o = o.parent;
      if (o && o.visible) return o;
    }
    return null;
  }

  promptFor(o) {
    const it = o.userData.interact;
    if (it.type === 'key') return '[E] Take brass key';
    if (it.type === 'battery') return '[E] Take battery';
    if (it.type === 'note') return '[E] Read note';
    if (it.type === 'door') {
      if (it.door.front) return this.keys >= 3 ? '[E] Unlock the front door' : '[E] Front door (locked)';
      return it.door.open ? '[E] Close door' : '[E] Open door';
    }
    return '';
  }

  interact() {
    const o = this.target;
    if (!o) return;
    const it = o.userData.interact;
    if (it.type === 'key') {
      this.house.removeItem(o);
      this.keys++;
      this.audio.pickup();
      this.hud.setKeys(this.keys);
      if (this.keys < 3) this.hud.setObjective('Find the brass keys');
      this.director.onKey(it.room, this.keys);
    } else if (it.type === 'battery') {
      this.house.removeItem(o);
      this.player.battery = Math.min(1, this.player.battery + 0.5);
      this.audio.pickup();
      this.hud.message('Battery replaced.', 2);
    } else if (it.type === 'note') {
      this.noteOpen = true;
      this.audio.paper();
      this.hud.showNote(NOTES[it.id]);
      if (this.keys < 3) this.hud.setObjective('Find the brass keys');
    } else if (it.type === 'door') {
      const d = it.door;
      if (d.front) {
        if (this.keys >= 3) this.escape();
        else {
          this.audio.rattle();
          this.hud.message('Locked. Three brass keyholes. ' + this.keys + ' of 3 keys.', 3);
          this.hud.setObjective('Find the brass keys');
        }
      } else {
        this.house.toggleDoor(d);
        this.audio.creak(0, 0.5);
      }
    }
  }

  caught() {
    if (this.state !== 'PLAYING') return;
    this.state = 'CAUGHT';
    this.audio.scream();
    this.audio.stopChase();
    this.audio.setBreath(0);
    this.audio.heartRate = 0;
    this.hud.flash('#a00', 1);
    document.exitPointerLock();
    this.hud.showDeath();
  }

  escape() {
    if (this.state !== 'PLAYING') return;
    this.state = 'ESCAPED';
    const d = this.house.doors.front;
    d.open = true;
    this.audio.creak(0, 0.9);
    this.audio.slam(0, 0.5, 0.9);
    this.audio.stopChase();
    this.audio.setBreath(0);
    this.audio.heartRate = 0;
    this.ghost.hide();
    document.exitPointerLock();
    this.hud.flash('#fff', 0.9);
    this.hud.showWin(this.time, this.banishes);
  }

  updateBurn(dt) {
    const g = this.ghost, p = this.player;
    let burning = false;
    if (g.present && p.lightOn) {
      this.tmp.set(g.pos.x - this.camera.position.x, 1.7 - this.camera.position.y, g.pos.z - this.camera.position.z);
      const d = this.tmp.length();
      const cos = this.tmp.dot(this.fwd) / (d + 0.0001);
      if (d < 10 && cos > 0.95) burning = true;
    }
    if (burning) {
      p.battery = Math.max(0, p.battery - dt * 0.014);
      this.audio.sizzle();
      if (g.applyBurn(dt)) {
        this.banishes++;
        this.audio.shriek();
        this.hud.flash('#fff', 0.7);
        this.hud.shake(0.12);
        this.hud.message(g.mode === 'chase' ? 'He scatters — he will reform. RUN.' : 'He burns away.', 2.5);
        this.director.quiet = Math.max(this.director.quiet, 8);
      }
    } else {
      g.coolBurn(dt);
    }
    this.hud.setBurn(g.burn, g.present && (burning || g.burn > 0.02));
  }

  frame() {
    const dt = Math.min(this.clock.getDelta(), 0.05);
    this.hud.update(dt);
    if (this.state === 'PLAYING' && !this.paused) {
      this.time += dt;
      if (!this.noteOpen) this.player.update(dt, this.house.colliders);
      this.camera.getWorldDirection(this.fwd);
      this.house.update(dt, this.time);
      this.director.update(dt);
      this.ghost.update(dt, this.player.pos, this.director.quiet);
      this.updateBurn(dt);
      this.updateDust(dt);

      const g = this.ghost;
      const dist = g.present ? Math.hypot(g.pos.x - this.player.pos.x, g.pos.z - this.player.pos.z) : 99;
      const prox = Math.max(0, 1 - dist / 12);
      this.audio.setBreath(g.present ? 0.15 + prox * 0.85 : 0);
      this.audio.heartRate = g.mode === 'chase' ? Math.max(0.45, prox) : (g.present ? prox * 0.8 : 0);
      this.audio.update(dt);
      if (g.dangerous && dist < 0.95) this.caught();

      this.target = this.noteOpen ? null : this.findTarget();
      this.hud.prompt(this.target ? this.promptFor(this.target) : '');
      this.hud.setBattery(this.player.battery);

      if (this.hud.shakeAmt > 0.001) {
        this.camera.position.x += (Math.random() - 0.5) * this.hud.shakeAmt;
        this.camera.position.y += (Math.random() - 0.5) * this.hud.shakeAmt;
        this.camera.rotation.z = (Math.random() - 0.5) * this.hud.shakeAmt * 0.4;
      } else this.camera.rotation.z = 0;
    } else if (this.state === 'TITLE') {
      const t = performance.now() * 0.0001;
      this.camera.position.set(0, 1.6, 6.5);
      this.camera.rotation.set(0, Math.sin(t) * 0.3, 0);
    }
    this.composer.render();
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
  }
}
```

```js path=bridge-horror-house/src/world/Textures.js
import * as THREE from 'three';

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}
const R = (a, b) => a + Math.random() * (b - a);

function speckle(g, w, h, n, lo, hi, a, size = 2) {
  for (let i = 0; i < n; i++) {
    const v = Math.floor(R(lo, hi));
    g.fillStyle = `rgba(${v},${v},${v},${a})`;
    g.fillRect(Math.random() * w, Math.random() * h, R(1, size), R(1, size));
  }
}
function stains(g, w, h, n, color, maxR) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * w, y = Math.random() * h, r = R(maxR * 0.3, maxR);
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, color);
    gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = gr;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
}
function toTex(c, repeat = true) {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 4;
  return t;
}

export class Textures {
  constructor() {
    this.floor = this.makeFloor();
    this.wallpaper = this.makeWallpaper();
    this.plaster = this.makePlaster();
    this.wood = this.makeWood();
    this.door = this.makeDoor();
    this.cookie = this.makeCookie();
    this.cobweb = this.makeCobweb();
    this.rug = this.makeRug();
    this.paper = this.makePaper();
    this.fabric = this.makeFabric();
    this.window = this.makeWindow();
    this.ghostFaces = [0, 1, 2].map((i) => toTex(this.faceCanvas(i, true), false));
    this.portraits = [0, 1, 2, 3, 4, 5].map((i) => toTex(this.portraitCanvas(i), false));
  }

  makeFloor() {
    const [c, g] = canvas(512, 512);
    g.fillStyle = '#2a1a10'; g.fillRect(0, 0, 512, 512);
    const pw = 64;
    for (let i = 0; i < 8; i++) {
      const off = (i % 2) * 130 + R(0, 40);
      for (let y = -off; y < 512; y += 260) {
        const v = R(-10, 10);
        g.fillStyle = `rgb(${58 + v},${37 + v * 0.7},${22 + v * 0.5})`;
        g.fillRect(i * pw + 1, y + 1, pw - 2, 258);
        for (let k = 0; k < 14; k++) {
          g.strokeStyle = `rgba(15,8,4,${R(0.08, 0.3)})`;
          g.beginPath();
          const x = i * pw + R(3, pw - 3);
          g.moveTo(x, y); g.bezierCurveTo(x + R(-4, 4), y + 80, x + R(-4, 4), y + 170, x + R(-3, 3), y + 260);
          g.stroke();
        }
        if (Math.random() < 0.5) {
          g.fillStyle = 'rgba(12,6,3,0.6)';
          g.beginPath(); g.ellipse(i * pw + R(15, 50), y + R(30, 220), R(3, 6), R(5, 10), 0, 0, 7); g.fill();
        }
      }
      g.fillStyle = 'rgba(0,0,0,0.7)'; g.fillRect(i * pw, 0, 1.5, 512);
    }
    stains(g, 512, 512, 14, 'rgba(0,0,0,0.35)', 90);
    stains(g, 512, 512, 3, 'rgba(60,5,0,0.3)', 60);
    speckle(g, 512, 512, 2500, 0, 60, 0.15);
    return toTex(c);
  }

  makeWallpaper() {
    const [c, g] = canvas(512, 512);
    g.fillStyle = '#4a3f33'; g.fillRect(0, 0, 512, 512);
    for (let x = 0; x < 512; x += 64) {
      g.fillStyle = '#3a2c25'; g.fillRect(x, 0, 30, 512);
      g.fillStyle = '#5b4b39'; g.fillRect(x + 30, 0, 2, 512);
      g.fillStyle = '#2c201c'; g.fillRect(x - 2, 0, 2, 512);
      for (let y = 20; y < 512; y += 64) {
        g.fillStyle = 'rgba(110,85,55,0.35)';
        g.beginPath(); g.moveTo(x + 47, y - 12); g.lineTo(x + 55, y); g.lineTo(x + 47, y + 12); g.lineTo(x + 39, y); g.fill();
      }
    }
    // water stains running from the top, grime at the bottom
    for (let i = 0; i < 16; i++) {
      const x = Math.random() * 512, w = R(8, 40), h = R(80, 400);
      const gr = g.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, 'rgba(20,14,8,0.6)'); gr.addColorStop(1, 'rgba(20,14,8,0)');
      g.fillStyle = gr; g.fillRect(x, 0, w, h);
    }
    const bot = g.createLinearGradient(0, 330, 0, 512);
    bot.addColorStop(0, 'rgba(0,0,0,0)'); bot.addColorStop(1, 'rgba(0,0,0,0.6)');
    g.fillStyle = bot; g.fillRect(0, 330, 512, 182);
    stains(g, 512, 512, 12, 'rgba(15,20,8,0.35)', 70);
    for (let i = 0; i < 6; i++) { // peeling tears
      g.fillStyle = 'rgba(95,88,74,0.5)';
      const x = R(0, 480), y = R(0, 480);
      g.beginPath(); g.moveTo(x, y); g.lineTo(x + R(10, 30), y + R(5, 20)); g.lineTo(x + R(0, 14), y + R(30, 70)); g.fill();
    }
    speckle(g, 512, 512, 3000, 0, 90, 0.12);
    return toTex(c);
  }

  makePlaster() {
    const [c, g] = canvas(512, 512);
    g.fillStyle = '#4c4840'; g.fillRect(0, 0, 512, 512);
    stains(g, 512, 512, 30, 'rgba(25,20,12,0.4)', 110);
    speckle(g, 512, 512, 5000, 20, 120, 0.1, 3);
    for (let i = 0; i < 9; i++) {
      let x = Math.random() * 512, y = Math.random() * 512, a = Math.random() * 7;
      g.strokeStyle = 'rgba(5,4,3,0.85)'; g.lineWidth = R(0.6, 1.8);
      g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 22; k++) {
        a += R(-0.7, 0.7); x += Math.cos(a) * R(5, 18); y += Math.sin(a) * R(5, 18);
        g.lineTo(x, y);
        if (Math.random() < 0.15) { g.lineTo(x + R(-22, 22), y + R(-22, 22)); g.moveTo(x, y); }
      }
      g.stroke();
    }
    return toTex(c);
  }

  makeWood() {
    const [c, g] = canvas(256, 256);
    g.fillStyle = '#24140c'; g.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 90; i++) {
      g.strokeStyle = `rgba(${R(5, 70)},${R(3, 35)},${R(0, 15)},${R(0.15, 0.5)})`;
      g.lineWidth = R(0.5, 2.5);
      const y = Math.random() * 256;
      g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(80, y + R(-9, 9), 170, y + R(-9, 9), 256, y + R(-5, 5)); g.stroke();
    }
    stains(g, 256, 256, 6, 'rgba(0,0,0,0.4)', 60);
    speckle(g, 256, 256, 900, 0, 50, 0.2);
    return toTex(c);
  }

  makeDoor() {
    const [c, g] = canvas(256, 512);
    g.drawImage(this.wood.image, 0, 0, 256, 512);
    g.fillStyle = 'rgba(40,22,12,0.35)'; g.fillRect(0, 0, 256, 512);
    for (const [x, y, w, h] of [[28, 30, 88, 200], [140, 30, 88, 200], [28, 262, 88, 220], [140, 262, 88, 220]]) {
      g.strokeStyle = 'rgba(0,0,0,0.8)'; g.lineWidth = 5; g.strokeRect(x, y, w, h);
      g.strokeStyle = 'rgba(110,75,45,0.35)'; g.lineWidth = 2; g.strokeRect(x + 5, y + 5, w - 10, h - 10);
    }
    for (let i = 0; i < 5; i++) { // claw scratches
      const x = R(60, 190), y = R(250, 420);
      g.strokeStyle = 'rgba(150,120,90,0.5)'; g.lineWidth = 1.5;
      for (let k = 0; k < 4; k++) { g.beginPath(); g.moveTo(x + k * 7, y); g.lineTo(x + k * 7 + R(-6, 6), y + R(40, 80)); g.stroke(); }
    }
    stains(g, 256, 512, 5, 'rgba(0,0,0,0.45)', 90);
    return toTex(c, false);
  }

  makeCookie() {
    const [c, g] = canvas(256, 256);
    g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256);
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 126);
    gr.addColorStop(0, '#fff'); gr.addColorStop(0.28, '#d8d8d8'); gr.addColorStop(0.34, '#f4f4f4');
    gr.addColorStop(0.6, '#9a9a9a'); gr.addColorStop(0.75, '#b5b5b5'); gr.addColorStop(0.9, '#3a3a3a'); gr.addColorStop(1, '#000');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    g.globalCompositeOperation = 'multiply';
    for (let i = 0; i < 9; i++) {
      g.fillStyle = `rgba(90,90,90,${R(0.2, 0.5)})`;
      g.beginPath(); g.arc(R(40, 216), R(40, 216), R(2, 8), 0, 7); g.fill();
    }
    g.strokeStyle = 'rgba(120,120,120,0.5)'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(60, 150); g.quadraticCurveTo(120, 130, 200, 170); g.stroke();
    g.globalCompositeOperation = 'source-over';
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }

  makeCobweb() {
    const [c, g] = canvas(256, 256);
    g.strokeStyle = 'rgba(200,200,200,0.5)'; g.lineWidth = 1;
    const spokes = 9;
    for (let i = 0; i <= spokes; i++) {
      const a = (i / spokes) * Math.PI / 2;
      g.beginPath(); g.moveTo(0, 0); g.lineTo(Math.cos(a) * 250, Math.sin(a) * 250); g.stroke();
    }
    for (let r = 30; r < 250; r += R(18, 30)) {
      g.beginPath();
      for (let i = 0; i <= spokes; i++) {
        const a = (i / spokes) * Math.PI / 2, rr = r * (i % 2 ? 0.93 : 1);
        if (i === 0) g.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); else g.lineTo(Math.cos(a) * rr, Math.sin(a) * rr);
      }
      g.stroke();
    }
    return toTex(c, false);
  }

  makeRug() {
    const [c, g] = canvas(256, 256);
    g.fillStyle = '#3a0d0d'; g.fillRect(0, 0, 256, 256);
    g.strokeStyle = '#6b5a2a'; g.lineWidth = 6; g.strokeRect(14, 14, 228, 228);
    g.strokeStyle = '#1c0606'; g.lineWidth = 3; g.strokeRect(30, 30, 196, 196);
    for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) {
      g.fillStyle = (i + j) % 2 ? 'rgba(107,90,42,0.5)' : 'rgba(20,6,6,0.6)';
      g.beginPath(); g.arc(52 + i * 30, 52 + j * 30, 7, 0, 7); g.fill();
    }
    stains(g, 256, 256, 8, 'rgba(0,0,0,0.5)', 70);
    speckle(g, 256, 256, 2500, 0, 80, 0.2);
    return toTex(c, false);
  }

  makePaper() {
    const [c, g] = canvas(128, 128);
    g.fillStyle = '#c9bd9a'; g.fillRect(0, 0, 128, 128);
    g.strokeStyle = 'rgba(40,25,15,0.8)'; g.lineWidth = 1.2;
    for (let y = 18; y < 116; y += 11) {
      g.beginPath(); g.moveTo(12, y);
      for (let x = 12; x < R(70, 116); x += 4) g.lineTo(x, y + R(-2, 2));
      g.stroke();
    }
    stains(g, 128, 128, 3, 'rgba(90,50,10,0.35)', 40);
    return toTex(c, false);
  }

  makeFabric() {
    const [c, g] = canvas(128, 128);
    g.fillStyle = '#2d2420'; g.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 128; i += 3) {
      g.fillStyle = `rgba(0,0,0,${R(0.1, 0.3)})`; g.fillRect(i, 0, 1, 128);
      g.fillStyle = `rgba(90,70,60,${R(0.03, 0.12)})`; g.fillRect(0, i, 128, 1);
    }
    stains(g, 128, 128, 6, 'rgba(0,0,0,0.5)', 50);
    return toTex(c);
  }

  makeWindow() {
    const [c, g] = canvas(128, 192);
    const gr = g.createLinearGradient(0, 0, 0, 192);
    gr.addColorStop(0, '#31466e'); gr.addColorStop(1, '#0c1322');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 192);
    g.strokeStyle = 'rgba(160,190,255,0.25)'; g.lineWidth = 1;
    for (let i = 0; i < 60; i++) { const x = R(0, 128), y = R(0, 192); g.beginPath(); g.moveTo(x, y); g.lineTo(x - 3, y + R(8, 22)); g.stroke(); }
    g.strokeStyle = '#000'; g.lineWidth = 3; // dead branches
    g.beginPath(); g.moveTo(128, 150); g.lineTo(80, 90); g.lineTo(60, 40); g.moveTo(80, 90); g.lineTo(40, 100); g.moveTo(95, 110); g.lineTo(110, 60); g.stroke();
    g.fillStyle = '#050505'; g.fillRect(60, 0, 8, 192); g.fillRect(0, 92, 128, 8);
    g.strokeStyle = '#050505'; g.lineWidth = 12; g.strokeRect(0, 0, 128, 192);
    return toTex(c, false);
  }

  // expr: 0 = blank stare, 1 = grin, 2 = scream
  faceCanvas(expr, transparent = false) {
    const [c, g] = canvas(256, 256);
    if (!transparent) { g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256); }
    g.fillStyle = '#a8a294';
    g.beginPath(); g.ellipse(128, 128, 84, 118, 0, 0, 7); g.fill();
    const sh = g.createRadialGradient(128, 110, 20, 128, 128, 125);
    sh.addColorStop(0, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.75)');
    g.fillStyle = sh; g.beginPath(); g.ellipse(128, 128, 84, 118, 0, 0, 7); g.fill();
    const eyeY = 100, eh = expr === 2 ? 30 : expr === 1 ? 14 : 20;
    for (const x of [92, 164]) {
      g.fillStyle = '#000';
      g.beginPath(); g.ellipse(x, eyeY, 21, eh, 0, 0, 7); g.fill();
      g.fillStyle = 'rgba(0,0,0,0.5)';
      g.beginPath(); g.ellipse(x, eyeY + 8, 27, eh + 12, 0, 0, 7); g.fill();
      g.strokeStyle = 'rgba(0,0,0,0.8)'; g.lineWidth = 2; // black tears
      g.beginPath(); g.moveTo(x - 4, eyeY + eh); g.lineTo(x - 7, eyeY + eh + R(30, 70)); g.stroke();
      g.beginPath(); g.moveTo(x + 6, eyeY + eh); g.lineTo(x + 8, eyeY + eh + R(20, 50)); g.stroke();
    }
    g.fillStyle = 'rgba(0,0,0,0.7)';
    g.beginPath(); g.moveTo(128, 128); g.lineTo(120, 150); g.lineTo(136, 150); g.fill();
    g.fillStyle = '#000';
    if (expr === 0) {
      g.fillRect(100, 182, 56, 4);
      for (let x = 104; x < 156; x += 9) g.fillRect(x, 174, 2, 20); // stitched shut
    } else if (expr === 1) {
      g.beginPath(); g.moveTo(62, 160); g.quadraticCurveTo(128, 232, 194, 160); g.quadraticCurveTo(128, 200, 62, 160); g.fill();
      g.fillStyle = '#c8c0a8';
      for (let i = 0; i < 11; i++) { const x = 78 + i * 10; g.beginPath(); g.moveTo(x, 172 + Math.abs(i - 5) * -2 + 8); g.lineTo(x + 4, 190); g.lineTo(x + 8, 172 + Math.abs(i - 5) * -2 + 8); g.fill(); }
    } else {
      g.beginPath(); g.ellipse(128, 196, 34, 50, 0, 0, 7); g.fill();
      g.fillStyle = '#c8c0a8';
      for (let i = 0; i < 6; i++) { const x = 104 + i * 8; g.beginPath(); g.moveTo(x, 152); g.lineTo(x + 4, 168); g.lineTo(x + 8, 152); g.fill(); }
      g.fillStyle = 'rgba(90,0,0,0.6)'; g.beginPath(); g.ellipse(128, 215, 18, 22, 0, 0, 7); g.fill();
    }
    g.strokeStyle = 'rgba(0,0,0,0.6)'; g.lineWidth = 1;
    for (let i = 0; i < 12; i++) { // cracks / veins
      let x = R(70, 186), y = R(30, 220);
      g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 5; k++) { x += R(-12, 12); y += R(-12, 12); g.lineTo(x, y); }
      g.stroke();
    }
    return c;
  }

  portraitCanvas(seed) {
    const [c, g] = canvas(192, 256);
    g.fillStyle = '#17110c'; g.fillRect(0, 0, 192, 256);
    const bg = g.createRadialGradient(96, 100, 10, 96, 120, 150);
    bg.addColorStop(0, '#3b2f22'); bg.addColorStop(1, '#0c0806');
    g.fillStyle = bg; g.fillRect(0, 0, 192, 256);
    g.fillStyle = '#0a0808'; // shoulders
    g.beginPath(); g.moveTo(20, 256); g.quadraticCurveTo(96, 140 + seed * 4, 172, 256); g.fill();
    g.fillStyle = seed % 2 ? '#8d8474' : '#9a8f7b';
    g.beginPath(); g.ellipse(96, 105, 38 + (seed % 3) * 3, 52, 0, 0, 7); g.fill();
    g.fillStyle = '#0d0907'; // hair
    g.beginPath(); g.ellipse(96, 68, 42 + (seed % 3) * 3, 26, 0, Math.PI, 0); g.fill();
    if (seed % 2) { g.fillRect(52, 66, 12, 90); g.fillRect(128, 66, 12, 90); }
    for (const x of [80, 112]) { // hollow or scratched-out eyes
      g.fillStyle = '#000';
      g.beginPath(); g.ellipse(x, 100, 9, seed % 3 === 0 ? 11 : 6, 0, 0, 7); g.fill();
      if (seed % 3 === 1) {
        g.strokeStyle = 'rgba(190,180,160,0.7)'; g.lineWidth = 1;
        for (let k = 0; k < 7; k++) { g.beginPath(); g.moveTo(x + R(-13, 13), 100 + R(-10, 10)); g.lineTo(x + R(-13, 13), 100 + R(-10, 10)); g.stroke(); }
      } else if (seed % 3 === 2) {
        g.fillStyle = '#b00'; g.fillRect(x - 1, 99, 2, 2);
      }
    }
    g.fillStyle = '#1a0a08';
    if (seed === 3 || seed === 0) { g.beginPath(); g.moveTo(70, 128); g.quadraticCurveTo(96, 158, 122, 128); g.quadraticCurveTo(96, 140, 70, 128); g.fill(); }
    else g.fillRect(82, 132, 28, 3);
    const sh = g.createLinearGradient(0, 0, 192, 0);
    sh.addColorStop(0, 'rgba(0,0,0,0.6)'); sh.addColorStop(0.5, 'rgba(0,0,0,0)'); sh.addColorStop(1, 'rgba(0,0,0,0.7)');
    g.fillStyle = sh; g.fillRect(0, 0, 192, 256);
    stains(g, 192, 256, 5, 'rgba(0,0,0,0.5)', 60);
    speckle(g, 192, 256, 1500, 0, 100, 0.12);
    return c;
  }
}
```

```js path=bridge-horror-house/src/world/House.js
import * as THREE from 'three';

const T = 0.2; // wall thickness
const H = 3;   // wall height
const DOOR_H = 2.2;

export function roomAt(x, z) {
  if (z < -2.1) return x < -4.1 ? 'study' : x < 3.9 ? 'bedroom' : 'kitchen';
  if (z < 0.9) return 'hallway';
  if (z > 1.1) return x < -4.1 ? 'living' : x < 3.9 ? 'foyer' : 'dining';
  return 'threshold';
}

function scaleUV(geo, su, sv) {
  const uv = geo.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
  return geo;
}

const KEY_SPOTS = {
  kitchen: [[6, 0.9, -7.5], [8.6, 0.9, -7.5], [7.4, 0.8, -5]],
  study: [[-7.7, 0.8, -6.5], [-4.6, 0.6, -7.3], [-9.3, 0.5, -2.8]],
  bedroom: [[0.5, 0.64, -7.3], [-1.6, 0.6, -7.4], [3.6, 0.9, -5.4]],
};

export class House {
  constructor(scene, tex) {
    this.scene = scene;
    this.tex = tex;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.colliders = [];
    this.interactables = [];
    this.doors = {};
    this.bulbs = [];
    this.moons = [];
    this.candles = [];
    this.keyMeshes = [];
    this.lightning = 0;
    this.flickerT = 0;
    this.blackout = false;
    this.chairSlide = -1;

    this.mat = {
      wall: new THREE.MeshStandardMaterial({ map: tex.wallpaper, roughness: 0.92 }),
      floor: new THREE.MeshStandardMaterial({ map: tex.floor, roughness: 0.8 }),
      ceil: new THREE.MeshStandardMaterial({ map: tex.plaster, roughness: 1 }),
      wood: new THREE.MeshStandardMaterial({ map: tex.wood, roughness: 0.7 }),
      trim: new THREE.MeshStandardMaterial({ map: tex.wood, roughness: 0.8, color: 0x555555 }),
      fabric: new THREE.MeshStandardMaterial({ map: tex.fabric, roughness: 1 }),
      sheet: new THREE.MeshStandardMaterial({ map: tex.fabric, roughness: 1, color: 0xb9b0a0 }),
      metal: new THREE.MeshStandardMaterial({ color: 0x555a5c, roughness: 0.45, metalness: 0.7 }),
      brass: new THREE.MeshStandardMaterial({ color: 0xd9a441, roughness: 0.25, metalness: 1, emissive: 0xa8701a, emissiveIntensity: 1.6 }),
      wax: new THREE.MeshStandardMaterial({ color: 0xb8b09a, roughness: 0.6 }),
      flame: new THREE.MeshBasicMaterial({ color: 0xffc070 }),
    };

    this.ambient = new THREE.AmbientLight(0x223044, 0.07);
    scene.add(this.ambient);

    this.buildShell();
    this.buildDoors();
    this.buildLights();
    this.buildFurniture();
    this.buildDressing();
    this.buildItems();
  }

  // ---------- helpers ----------
  box(w, h, d, x, y, z, mat, collide = false, shadow = true) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.position.set(x, y, z);
    m.castShadow = shadow; m.receiveShadow = true;
    this.group.add(m);
    if (collide) this.colliders.push({ minX: x - w / 2, maxX: x + w / 2, minZ: z - d / 2, maxZ: z + d / 2 });
    return m;
  }

  furn(x, z, w, h, d, mat = this.mat.wood) {
    return this.box(w, h, d, x, h / 2, z, mat, true);
  }

  table(x, z, w, d, h) {
    this.box(w, 0.06, d, x, h - 0.03, z, this.mat.wood);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      this.box(0.07, h - 0.06, 0.07, x + sx * (w / 2 - 0.08), (h - 0.06) / 2, z + sz * (d / 2 - 0.08), this.mat.wood);
    }
    this.colliders.push({ minX: x - w / 2, maxX: x + w / 2, minZ: z - d / 2, maxZ: z + d / 2 });
  }

  chair(x, z, rot = 0, collide = true) {
    const g = new THREE.Group();
    const add = (w, h, d, px, py, pz) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), this.mat.wood);
      m.position.set(px, py, pz); m.castShadow = true; m.receiveShadow = true; g.add(m);
    };
    add(0.42, 0.05, 0.42, 0, 0.45, 0);
    add(0.42, 0.55, 0.05, 0, 0.75, -0.19);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) add(0.05, 0.45, 0.05, sx * 0.17, 0.225, sz * 0.17);
    g.position.set(x, 0, z); g.rotation.y = rot;
    this.group.add(g);
    if (collide) this.colliders.push({ minX: x - 0.22, maxX: x + 0.22, minZ: z - 0.22, maxZ: z + 0.22 });
    return g;
  }

  wall(axis, c, a0, a1, gaps = []) {
    const piece = (p0, p1, y0, y1, collide) => {
      const L = p1 - p0;
      if (L <= 0.001) return;
      const mid = (p0 + p1) / 2, hh = y1 - y0;
      const geo = scaleUV(new THREE.BoxGeometry(axis === 'x' ? L : T, hh, axis === 'x' ? T : L), L / 2.2, hh / H);
      const m = new THREE.Mesh(geo, this.mat.wall);
      m.position.set(axis === 'x' ? mid : c, y0 + hh / 2, axis === 'x' ? c : mid);
      m.castShadow = true; m.receiveShadow = true;
      this.group.add(m);
      if (collide) {
        if (axis === 'x') this.colliders.push({ minX: p0, maxX: p1, minZ: c - T / 2, maxZ: c + T / 2 });
        else this.colliders.push({ minX: c - T / 2, maxX: c + T / 2, minZ: p0, maxZ: p1 });
        // baseboard
        const bb = new THREE.Mesh(new THREE.BoxGeometry(axis === 'x' ? L : T + 0.05, 0.13, axis === 'x' ? T + 0.05 : L), this.mat.trim);
        bb.position.set(m.position.x, 0.065, m.position.z);
        bb.receiveShadow = true;
        this.group.add(bb);
      }
    };
    let s = a0;
    for (const [gc, gw] of gaps.slice().sort((a, b) => a[0] - b[0])) {
      piece(s, gc - gw / 2, 0, H, true);
      piece(gc - gw / 2, gc + gw / 2, DOOR_H, H, false);
      // door frame trim
      for (const e of [gc - gw / 2, gc + gw / 2]) {
        const fr = new THREE.Mesh(new THREE.BoxGeometry(axis === 'x' ? 0.07 : T + 0.06, DOOR_H, axis === 'x' ? T + 0.06 : 0.07), this.mat.trim);
        fr.position.set(axis === 'x' ? e : c, DOOR_H / 2, axis === 'x' ? c : e);
        this.group.add(fr);
      }
      s = gc + gw / 2;
    }
    piece(s, a1, 0, H, true);
  }

  // ---------- structure ----------
  buildShell() {
    const floor = new THREE.Mesh(scaleUV(new THREE.PlaneGeometry(20, 16), 10, 8), this.mat.floor);
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
    this.group.add(floor);
    const ceil = new THREE.Mesh(scaleUV(new THREE.PlaneGeometry(20, 16), 5, 4), this.mat.ceil);
    ceil.rotation.x = Math.PI / 2; ceil.position.y = H; ceil.receiveShadow = true;
    this.group.add(ceil);

    this.wall('x', -8, -10, 10);
    this.wall('x', 8, -10, 10, [[0, 1.2]]);
    this.wall('z', -10, -8, 8);
    this.wall('z', 10, -8, 8);
    this.wall('x', -2, -10, 10, [[-7, 1.2], [0, 1.2], [7, 1.4]]);
    this.wall('x', 1, -10, 10, [[-7, 1.4], [0, 2.2], [7, 1.4]]);
    this.wall('z', -4, -8, -2);
    this.wall('z', 4, -8, -2);
    this.wall('z', -4, 1, 8);
    this.wall('z', 4, 1, 8);
  }

  makeDoor(name, hx, hz, front = false) {
    const pivot = new THREE.Group();
    pivot.position.set(hx, 0, hz);
    const mat = new THREE.MeshStandardMaterial({ map: this.tex.door, roughness: 0.7, color: front ? 0x8a6a5a : 0xffffff });
    const leaf = new THREE.Mesh(new THREE.BoxGeometry(1.2, DOOR_H, 0.07), mat);
    leaf.position.set(0.6, DOOR_H / 2, 0);
    leaf.castShadow = true; leaf.receiveShadow = true;
    pivot.add(leaf);
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), this.mat.metal);
    knob.position.set(1.08, 1.0, 0.07); pivot.add(knob);
    const knob2 = knob.clone(); knob2.position.z = -0.07; pivot.add(knob2);
    this.group.add(pivot);
    const collider = { minX: hx, maxX: hx + 1.2, minZ: hz - 0.1, maxZ: hz + 0.1, off: false };
    this.colliders.push(collider);
    const door = { name, pivot, open: false, angle: 0, collider, front };
    pivot.userData.interact = { type: 'door', door };
    this.interactables.push(pivot);
    this.doors[name] = door;
  }

  buildDoors() {
    this.makeDoor('study', -7.6, -2);
    this.makeDoor('bedroom', -0.6, -2);
    this.makeDoor('front', -0.6, 8, true);
  }

  toggleDoor(d, force) {
    d.open = force === undefined ? !d.open : force;
  }

  buildLights() {
    // faint warm bulbs: foyer + hallway
    for (const [x, z] of [[0, 4.5], [0, -0.5]]) {
      const l = new THREE.PointLight(0xffa24a, 1.1, 7, 2);
      l.position.set(x, 2.6, z);
      this.group.add(l);
      const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffb060 }));
      bulb.position.copy(l.position);
      this.group.add(bulb);
      this.box(0.015, 0.4, 0.015, x, 2.82, z, this.mat.trim, false, false);
      this.bulbs.push({ light: l, mesh: bulb, base: 1.1, v: 1 });
    }
    // windows with cold moonlight
    const win = (x, z, ry, lit) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.6), new THREE.MeshBasicMaterial({ map: this.tex.window, color: 0x8899bb, fog: false }));
      m.position.set(x, 1.7, z); m.rotation.y = ry;
      this.group.add(m);
      const entry = { mesh: m, light: null };
      if (lit) {
        const l = new THREE.PointLight(0x4a6aa8, 1.4, 7, 2);
        l.position.set(x + Math.sin(ry) * 0.6, 1.8, z + Math.cos(ry) * 0.6);
        this.group.add(l);
        entry.light = l;
      }
      this.moons.push(entry);
    };
    win(-9.89, -5.6, Math.PI / 2, true);
    win(9.89, -5, -Math.PI / 2, true);
    win(-9.89, 4.5, Math.PI / 2, true);
    win(9.89, 4.5, -Math.PI / 2, true);
    win(0, -7.89, 0, false);
    win(-2.6, 7.89, Math.PI, false);
    win(2.6, 7.89, Math.PI, false);
  }

  candle(x, y, z, lit) {
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.16, 8), this.mat.wax);
    body.position.set(x, y + 0.08, z); body.castShadow = true;
    this.group.add(body);
    const flame = new THREE.Mesh(new THREE.ConeGeometry(0.014, 0.05, 6), this.mat.flame);
    flame.position.set(x, y + 0.19, z);
    this.group.add(flame);
    let light = null;
    if (lit) {
      light = new THREE.PointLight(0xff8a3a, 0.5, 3.2, 2);
      light.position.set(x, y + 0.25, z);
      this.group.add(light);
    }
    this.candles.push({ flame, light, phase: Math.random() * 10 });
  }

  buildFurniture() {
    const M = this.mat;
    // FOYER
    this.table(-3.3, 5, 0.6, 1.4, 0.8);
    this.furn(3.6, 3, 0.5, 2.1, 0.5); // grandfather clock
    const face = new THREE.Mesh(new THREE.CircleGeometry(0.16, 20), new THREE.MeshStandardMaterial({ color: 0x9a927c, roughness: 0.6 }));
    face.position.set(3.34, 1.75, 3); face.rotation.y = -Math.PI / 2; this.group.add(face);
    this.box(0.06, 1.9, 0.06, 3.5, 0.95, 7.4, M.wood, false); // coat rack
    this.box(0.5, 0.04, 0.5, 3.5, 1.85, 7.4, M.wood, false);
    this.colliders.push({ minX: 3.35, maxX: 3.65, minZ: 7.25, maxZ: 7.55 });
    const coat = this.box(0.35, 0.9, 0.12, 3.5, 1.35, 7.25, M.fabric, false);
    coat.rotation.z = 0.06;
    const rug = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 3.4), new THREE.MeshStandardMaterial({ map: this.tex.rug, roughness: 1 }));
    rug.rotation.x = -Math.PI / 2; rug.position.set(0, 0.012, 4.8); rug.receiveShadow = true; this.group.add(rug);

    // LIVING ROOM
    this.furn(-7, 6.9, 2.4, 0.45, 0.9, M.fabric);       // sofa seat
    this.box(2.4, 0.55, 0.22, -7, 0.72, 7.25, M.fabric); // sofa back
    this.box(0.22, 0.3, 0.9, -8.1, 0.6, 6.9, M.fabric);
    this.box(0.22, 0.3, 0.9, -5.9, 0.6, 6.9, M.fabric);
    this.table(-7, 5.2, 1.2, 0.6, 0.45);
    this.furn(-9.2, 3.2, 0.9, 0.45, 0.9, M.fabric);      // armchair
    this.box(0.2, 0.6, 0.9, -9.55, 0.75, 3.2, M.fabric);
    this.furn(-4.45, 4.2, 0.5, 1.8, 1.4);                // cabinet
    this.furn(-9.7, 6, 0.4, 1.2, 1.6, M.trim);           // dead fireplace
    this.box(0.5, 0.08, 1.9, -9.65, 1.24, 6, M.wood);
    const hearth = this.box(0.05, 0.7, 0.9, -9.49, 0.4, 6, new THREE.MeshStandardMaterial({ color: 0x020202, roughness: 1 }), false, false);
    hearth.receiveShadow = false;
    this.candle(-7.3, 0.45, 5.15, true);
    this.candle(-9.65, 1.28, 5.4, false);

    // DINING ROOM
    this.table(7, 4.8, 1.4, 2.6, 0.8);
    this.chair(5.95, 4.2, Math.PI / 2); this.chair(5.95, 5.4, Math.PI / 2);
    this.chair(8.05, 4.2, -Math.PI / 2);
    const fallen = this.chair(8.5, 6.2, 0.6, false); fallen.rotation.x = Math.PI / 2; fallen.position.y = 0.2;
    this.furn(7, 7.6, 2, 0.9, 0.5);
    this.candle(7, 0.8, 4.4, true);
    this.candle(7.1, 0.8, 5.3, false);
    for (const [px, pz] of [[6.6, 4], [7.4, 4.9], [6.6, 5.7]]) { // plates
      const pl = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.1, 0.02, 14), new THREE.MeshStandardMaterial({ color: 0x8c877a, roughness: 0.4 }));
      pl.position.set(px, 0.81, pz); pl.receiveShadow = true; this.group.add(pl);
    }

    // HALLWAY
    this.furn(3, -1.68, 1, 0.8, 0.4);

    // STUDY
    this.table(-7, -6.5, 1.8, 0.8, 0.8);
    this.chair(-7, -5.7, Math.PI);
    this.furn(-9.65, -5, 0.5, 2.4, 2.4);
    for (let s = 0; s < 4; s++) { // books
      for (let b = 0; b < 12; b++) {
        if (Math.random() < 0.25) continue;
        const hh = 0.25 + Math.random() * 0.15;
        const bk = new THREE.Mesh(new THREE.BoxGeometry(0.2, hh, 0.07 + Math.random() * 0.06),
          new THREE.MeshStandardMaterial({ color: new THREE.Color().setHSL(Math.random() * 0.1, 0.4, 0.06 + Math.random() * 0.08), roughness: 0.9 }));
        bk.position.set(-9.36, 0.35 + s * 0.55 + hh / 2, -6.05 + b * 0.19);
        bk.rotation.x = (Math.random() - 0.5) * 0.15;
        this.group.add(bk);
      }
      this.box(0.08, 0.03, 2.4, -9.38, 0.33 + s * 0.55, -5, M.trim, false, false);
    }
    this.table(-4.6, -7.3, 0.6, 0.6, 0.6);
    this.furn(-9.3, -2.8, 0.9, 0.5, 0.6);

    // BEDROOM
    this.furn(0, -6.4, 2, 0.35, 2.8, M.wood);
    this.box(1.9, 0.2, 2.7, 0, 0.45, -6.4, M.sheet);
    this.box(2, 1.1, 0.12, 0, 0.55, -7.8, M.wood);
    this.box(0.7, 0.1, 0.4, 0.5, 0.58, -7.3, M.sheet);
    this.box(0.7, 0.1, 0.4, -0.5, 0.58, -7.3, M.sheet);
    const lump = new THREE.Mesh(new THREE.SphereGeometry(0.5, 12, 8), M.sheet); // something under the sheet
    lump.scale.set(0.7, 0.3, 1.7); lump.position.set(-0.4, 0.55, -6.1); lump.castShadow = true; this.group.add(lump);
    this.furn(-1.6, -7.4, 0.6, 0.6, 0.6);
    this.furn(3.6, -5, 0.5, 0.9, 1.6);
    this.furn(-3.55, -4.5, 0.6, 2.2, 1.4);
    this.candle(3.6, 0.9, -4.5, false);
    const mirror = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 1.0), new THREE.MeshStandardMaterial({ color: 0x1a2024, roughness: 0.08, metalness: 1 }));
    mirror.position.set(3.89, 1.7, -5); mirror.rotation.y = -Math.PI / 2; this.group.add(mirror);

    // KITCHEN
    this.furn(7, -7.5, 5, 0.9, 0.7, M.wood);
    this.box(5.04, 0.05, 0.74, 7, 0.9, -7.5, M.metal, false);
    this.box(5, 0.7, 0.35, 7, 2.2, -7.7, M.wood); // upper cabinets
    this.table(7, -5, 1.6, 1, 0.8);
    this.furn(9.5, -3.2, 0.7, 1.9, 0.8, new THREE.MeshStandardMaterial({ color: 0x8c8f88, roughness: 0.5, metalness: 0.3 }));
    this.chair(7.6, -4.2, 0);
    this.slidingChair = this.chair(6, -3.6, 0.4, false);
    const knife = this.box(0.03, 0.01, 0.25, 6.6, 0.81, -5.1, M.metal, false);
    knife.rotation.y = 0.5;
  }

  buildDressing() {
    // portraits
    const portrait = (i, x, z, ry) => {
      const g = new THREE.Group();
      const frame = new THREE.Mesh(new THREE.BoxGeometry(0.78, 1.02, 0.05), this.mat.wood);
      frame.castShadow = true;
      const pic = new THREE.Mesh(new THREE.PlaneGeometry(0.64, 0.88), new THREE.MeshStandardMaterial({ map: this.tex.portraits[i], roughness: 0.6 }));
      pic.position.z = 0.03;
      g.add(frame, pic);
      g.position.set(x, 1.75, z); g.rotation.set(0, ry, (Math.random() - 0.5) * 0.1);
      this.group.add(g);
    };
    portrait(0, -3.5, -1.86, 0);
    portrait(1, 3.6, 0.86, Math.PI);
    portrait(2, -3.5, 0.86, Math.PI);
    portrait(3, -3.86, 3, Math.PI / 2);
    portrait(4, -7, 7.86, Math.PI);
    portrait(5, 9.86, 1.9, -Math.PI / 2);
    portrait(1, -7, -7.86, 0);
    portrait(3, -3.86, -6.5, Math.PI / 2);
    portrait(0, 5.5, 7.86, Math.PI);

    // cobwebs in ceiling corners
    const webMat = new THREE.MeshBasicMaterial({ map: this.tex.cobweb, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false });
    const web = (x, z, ry, s = 1.2) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s), webMat);
      m.position.set(x, H - s / 2 - 0.02, z); m.rotation.y = ry; m.rotation.z = Math.PI; m.scale.x = -1;
      this.group.add(m);
    };
    web(-9.5, -7.5, Math.PI / 4); web(9.5, -7.5, -Math.PI / 4); web(-9.5, 7.5, Math.PI * 0.75); web(9.5, 7.5, -Math.PI * 0.75);
    web(-3.6, -2.4, -Math.PI / 4, 1); web(3.6, 1.4, Math.PI / 4, 1); web(-9.5, -1.6, Math.PI / 4, 1.4); web(9.5, 0.6, -Math.PI * 0.75, 1.4);
    web(-4.4, -7.5, -Math.PI / 4, 0.9); web(4.4, 7.5, Math.PI * 0.75, 0.9); web(3.6, -7.5, -Math.PI / 4, 1);
  }

  buildItems() {
    // keys — one per room, random spot
    for (const room of ['kitchen', 'study', 'bedroom']) {
      const spots = KEY_SPOTS[room];
      const [x, y, z] = spots[Math.floor(Math.random() * spots.length)];
      const k = new THREE.Group();
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.035, 0.01, 6, 14), this.mat.brass);
      const shaft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.014, 0.014), this.mat.brass);
      shaft.position.x = 0.085;
      const bit = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.035, 0.012), this.mat.brass);
      bit.position.set(0.12, -0.02, 0);
      const hit = new THREE.Mesh(new THREE.SphereGeometry(0.16, 6, 5), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
      k.add(ring, shaft, bit, hit);
      k.rotation.x = -Math.PI / 2;
      k.rotation.z = Math.random() * 6;
      k.position.set(x, y + 0.02, z);
      k.userData.interact = { type: 'key', room };
      this.group.add(k);
      this.interactables.push(k);
      this.keyMeshes.push(k);
    }
    // batteries (fixed)
    const batMat = new THREE.MeshStandardMaterial({ color: 0x2a6a3a, roughness: 0.4, metalness: 0.5, emissive: 0x0a2a10, emissiveIntensity: 0.6 });
    for (const [x, y, z] of [[-6.7, 0.45, 5.25], [7.3, 0.8, 5.6], [3.1, 0.8, -1.68], [5, 0.93, -7.5]]) {
      const b = new THREE.Group();
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.028, 0.11, 10), batMat);
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.02, 8), this.mat.metal);
      cap.position.y = 0.063;
      const hit = new THREE.Mesh(new THREE.SphereGeometry(0.15, 6, 5), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }));
      b.add(body, cap, hit);
      b.rotation.z = Math.PI / 2; b.rotation.y = Math.random() * 3;
      b.position.set(x, y + 0.03, z);
      b.userData.interact = { type: 'battery' };
      this.group.add(b);
      this.interactables.push(b);
    }
    // notes
    for (const [id, x, y, z] of [['foyer', -3.3, 0.8, 5], ['study', -6.5, 0.8, -6.4]]) {
      const n = new THREE.Mesh(new THREE.PlaneGeometry(0.24, 0.32), new THREE.MeshStandardMaterial({ map: this.tex.paper, roughness: 0.9, emissive: 0x2a2418, emissiveIntensity: 0.5 }));
      n.rotation.x = -Math.PI / 2; n.rotation.z = Math.random() - 0.5;
      n.position.set(x, y + 0.012, z);
      n.userData.interact = { type: 'note', id };
      this.group.add(n);
      this.interactables.push(n);
    }
  }

  removeItem(o) {
    o.visible = false;
    this.group.remove(o);
    const i = this.interactables.indexOf(o);
    if (i >= 0) this.interactables.splice(i, 1);
  }

  slideChair() { this.chairSlide = 0; }

  update(dt, t) {
    // doors
    for (const k in this.doors) {
      const d = this.doors[k];
      const target = d.open ? 1.75 : 0;
      d.angle += (target - d.angle) * Math.min(1, dt * (d.slam ? 16 : 3.2));
      if (Math.abs(target - d.angle) < 0.01) d.slam = false;
      d.pivot.rotation.y = d.angle;
      d.collider.off = d.angle > 0.9;
    }
    // bulbs
    for (const b of this.bulbs) {
      let v = 0.85 + Math.sin(t * 13 + b.base) * 0.05 + (Math.random() < 0.03 ? -0.5 : 0);
      if (this.flickerT > 0) v = Math.random() < 0.55 ? 0 : 1.3;
      if (this.blackout) v = 0;
      b.v += (v - b.v) * 0.5;
      b.light.intensity = b.base * Math.max(0, b.v);
      b.mesh.material.color.setScalar(1).multiplyScalar(0.15 + Math.max(0, b.v) * 0.85).multiply(new THREE.Color(1, 0.69, 0.38));
    }
    if (this.flickerT > 0) this.flickerT -= dt;
    // candles gutter
    for (const c of this.candles) {
      const f = 0.75 + Math.sin(t * 11 + c.phase) * 0.12 + Math.sin(t * 23.7 + c.phase * 2) * 0.1 + (Math.random() < 0.04 ? -0.3 : 0);
      c.flame.scale.set(1, 0.7 + f * 0.6, 1);
      c.flame.rotation.z = Math.sin(t * 7 + c.phase) * 0.2;
      if (c.light) c.light.intensity = (this.blackout ? 0.25 : 0.5) * f;
    }
    // lightning
    if (this.lightning > 0) this.lightning = Math.max(0, this.lightning - dt * 2.6);
    const L = this.lightning > 0 ? this.lightning * (Math.random() < 0.3 ? 0.3 : 1) : 0;
    for (const m of this.moons) {
      if (m.light) m.light.intensity = 1.4 + L * 45;
      m.mesh.material.color.setRGB(0.53 + L * 4, 0.6 + L * 4, 0.73 + L * 4);
    }
    this.ambient.intensity = 0.07 + L * 0.5;
    // keys glint
    for (const k of this.keyMeshes) if (k.visible) k.rotation.z += dt * 0.6;
    this.mat.brass.emissiveIntensity = 1.4 + Math.sin(t * 3) * 0.6;
    // kitchen chair slide
    if (this.chairSlide >= 0 && this.chairSlide < 1) {
      this.chairSlide = Math.min(1, this.chairSlide + dt * 1.1);
      const e = 1 - Math.pow(1 - this.chairSlide, 3);
      this.slidingChair.position.set(6 + e * 2.3, 0, -3.6 + e * 0.5);
      this.slidingChair.rotation.y = 0.4 + e * 1.1;
    }
  }
}
```

```js path=bridge-horror-house/src/player/Player.js
import * as THREE from 'three';

const RADIUS = 0.3;
const EYE = 1.62;

export class Player {
  constructor(camera, scene, dom, tex, audio) {
    this.camera = camera;
    this.dom = dom;
    this.audio = audio;
    this.pos = new THREE.Vector3(0, EYE, 6.4);
    this.yaw = 0;
    this.pitch = 0;
    this.keys = {};
    this.bob = 0;
    this.stepAcc = 0;
    this.battery = 1;
    this.on = true;
    this.blackout = 0;
    this.flicker = 1;
    this.lightOn = true;
    this.moving = false;

    this.spot = new THREE.SpotLight(0xfff0d2, 95, 22, 0.5, 0.65, 2);
    this.spot.castShadow = true;
    this.spot.shadow.mapSize.set(1024, 1024);
    this.spot.shadow.camera.near = 0.2;
    this.spot.shadow.camera.far = 22;
    this.spot.shadow.bias = -0.0006;
    this.spot.shadow.radius = 4;
    this.spot.map = tex.cookie;
    scene.add(this.spot, this.spot.target);
    this.aim = new THREE.Vector3(0, EYE, 0);
    this.fwd = new THREE.Vector3();
    this.right = new THREE.Vector3();

    this.onMouse = (e) => {
      if (document.pointerLockElement !== this.dom) return;
      this.yaw -= e.movementX * 0.0022;
      this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch - e.movementY * 0.0022));
    };
    this.onDown = (e) => {
      this.keys[e.code] = true;
      if (e.code === 'KeyF' && document.pointerLockElement === this.dom) {
        this.on = !this.on;
        this.audio.click();
      }
    };
    this.onUp = (e) => { this.keys[e.code] = false; };
    this.onBlur = () => { this.keys = {}; };
    document.addEventListener('mousemove', this.onMouse);
    window.addEventListener('keydown', this.onDown);
    window.addEventListener('keyup', this.onUp);
    window.addEventListener('blur', this.onBlur);
    this.syncCamera(0);
    this.aim.set(0, EYE, 0);
  }

  dispose() {
    document.removeEventListener('mousemove', this.onMouse);
    window.removeEventListener('keydown', this.onDown);
    window.removeEventListener('keyup', this.onUp);
    window.removeEventListener('blur', this.onBlur);
    this.spot.dispose();
  }

  collide(colliders) {
    const p = this.pos;
    for (let iter = 0; iter < 2; iter++) {
      for (const c of colliders) {
        if (c.off) continue;
        const cx = Math.max(c.minX, Math.min(p.x, c.maxX));
        const cz = Math.max(c.minZ, Math.min(p.z, c.maxZ));
        let dx = p.x - cx, dz = p.z - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 >= RADIUS * RADIUS) continue;
        if (d2 > 1e-8) {
          const d = Math.sqrt(d2);
          p.x = cx + (dx / d) * RADIUS;
          p.z = cz + (dz / d) * RADIUS;
        } else {
          // centre inside the box: push out along the shallowest axis
          const l = p.x - c.minX, r = c.maxX - p.x, n = p.z - c.minZ, s = c.maxZ - p.z;
          const m = Math.min(l, r, n, s);
          if (m === l) p.x = c.minX - RADIUS; else if (m === r) p.x = c.maxX + RADIUS;
          else if (m === n) p.z = c.minZ - RADIUS; else p.z = c.maxZ + RADIUS;
        }
      }
    }
    p.x = Math.max(-9.6, Math.min(9.6, p.x));
    p.z = Math.max(-7.6, Math.min(7.6, p.z));
  }

  syncCamera(dt) {
    const bobY = Math.sin(this.bob * 2) * 0.035;
    const bobX = Math.cos(this.bob) * 0.02;
    this.camera.position.set(this.pos.x + Math.cos(this.yaw) * bobX, EYE + bobY, this.pos.z - Math.sin(this.yaw) * bobX);
    this.camera.rotation.set(this.pitch, this.yaw, 0);
    this.camera.getWorldDirection(this.fwd);
    this.right.set(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
  }

  update(dt, colliders) {
    const k = this.keys;
    let f = 0, s = 0;
    if (k.KeyW || k.ArrowUp) f += 1;
    if (k.KeyS || k.ArrowDown) f -= 1;
    if (k.KeyD || k.ArrowRight) s += 1;
    if (k.KeyA || k.ArrowLeft) s -= 1;
    const sprint = k.ShiftLeft || k.ShiftRight;
    const len = Math.hypot(f, s);
    this.moving = len > 0;
    if (len > 0) {
      f /= len; s /= len;
      const speed = sprint ? 4.3 : 2.3;
      const fx = -Math.sin(this.yaw), fz = -Math.cos(this.yaw);
      const rx = Math.cos(this.yaw), rz = -Math.sin(this.yaw);
      const step = speed * dt;
      this.pos.x += (fx * f + rx * s) * step;
      this.pos.z += (fz * f + rz * s) * step;
      this.collide(colliders);
      this.bob += dt * (sprint ? 11 : 7);
      this.stepAcc += step;
      if (this.stepAcc > (sprint ? 1.5 : 1.05)) { this.stepAcc = 0; this.audio.step(sprint); }
    } else {
      this.bob += dt * 1.2; // idle breathing sway
    }
    this.syncCamera(dt);

    // battery + flashlight state
    if (this.blackout > 0) this.blackout -= dt;
    if (this.on && this.battery > 0) this.battery = Math.max(0, this.battery - dt / 260);
    this.lightOn = this.on && this.battery > 0 && this.blackout <= 0;
    let fl = 1;
    if (this.battery < 0.2) {
      const sput = Math.sin(performance.now() * 0.02) * Math.sin(performance.now() * 0.0073);
      fl = sput > 0.35 ? 0.15 : 0.55 + this.battery * 2;
      if (Math.random() < 0.04) fl = 0.05;
    } else if (Math.random() < 0.004) fl = 0.6;
    this.flicker += (fl - this.flicker) * 0.5;
    this.spot.intensity = this.lightOn ? 95 * this.flicker : 0;

    // beam lags behind the view and sways with the hand
    const t = performance.now() * 0.001;
    const sway = this.moving ? 0.12 : 0.04;
    const tx = this.camera.position.x + this.fwd.x * 6 + this.right.x * Math.sin(t * 1.7) * sway;
    const ty = this.camera.position.y + this.fwd.y * 6 + Math.sin(t * 2.3) * sway * 0.7 + Math.sin(this.bob * 2) * 0.05;
    const tz = this.camera.position.z + this.fwd.z * 6 + this.right.z * Math.sin(t * 1.7) * sway;
    const a = 1 - Math.exp(-dt * 9);
    this.aim.x += (tx - this.aim.x) * a;
    this.aim.y += (ty - this.aim.y) * a;
    this.aim.z += (tz - this.aim.z) * a;
    this.spot.position.set(
      this.camera.position.x + this.right.x * 0.22 + this.fwd.x * 0.05,
      this.camera.position.y - 0.2,
      this.camera.position.z + this.right.z * 0.22 + this.fwd.z * 0.05,
    );
    this.spot.target.position.copy(this.aim);
    this.spot.target.updateMatrixWorld();
  }
}
```

```js path=bridge-horror-house/src/systems/AudioEngine.js
// Everything here is synthesized. No audio files.
export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.heartRate = 0;
    this.nextBeat = 0;
    this.chaseOn = false;
    this.nextChase = 0;
    this.chaseStep = 0;
    this.lastSizzle = 0;
  }

  start() {
    if (this.ctx) { this.ctx.resume(); return; }
    const c = this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.comp = c.createDynamicsCompressor();
    this.master = c.createGain(); this.master.gain.value = 0.85;
    this.master.connect(this.comp); this.comp.connect(c.destination);

    // convolution reverb with a generated impulse response
    const len = c.sampleRate * 3.2;
    const ir = c.createBuffer(2, len, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
    }
    this.reverb = c.createConvolver(); this.reverb.buffer = ir;
    const wet = c.createGain(); wet.gain.value = 0.42;
    this.reverb.connect(wet); wet.connect(this.master);
    this.bus = c.createGain();
    this.bus.connect(this.master); this.bus.connect(this.reverb);

    // shared noise buffer
    this.noiseBuf = c.createBuffer(1, c.sampleRate * 2, c.sampleRate);
    const nd = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;

    // continuous low drone
    const dg = c.createGain(); dg.gain.value = 0.11;
    const df = c.createBiquadFilter(); df.type = 'lowpass'; df.frequency.value = 150;
    for (const [f, type] of [[41, 'sawtooth'], [43.4, 'sawtooth'], [61.7, 'sine'], [27.5, 'sine']]) {
      const o = c.createOscillator(); o.type = type; o.frequency.value = f; o.connect(df); o.start();
    }
    const lfo = c.createOscillator(); lfo.frequency.value = 0.07;
    const lg = c.createGain(); lg.gain.value = 60; lfo.connect(lg); lg.connect(df.frequency); lfo.start();
    df.connect(dg); dg.connect(this.bus);

    // rain bed
    const rain = this.loopNoise();
    const rf = c.createBiquadFilter(); rf.type = 'bandpass'; rf.frequency.value = 2600; rf.Q.value = 0.4;
    const rg = c.createGain(); rg.gain.value = 0.045;
    rain.connect(rf); rf.connect(rg); rg.connect(this.master);
    const roof = c.createBiquadFilter(); roof.type = 'lowpass'; roof.frequency.value = 400;
    const rg2 = c.createGain(); rg2.gain.value = 0.06;
    rain.connect(roof); roof.connect(rg2); rg2.connect(this.master);

    // entity breathing: band-passed noise with a slow LFO, level driven by proximity
    const br = this.loopNoise();
    const bf = c.createBiquadFilter(); bf.type = 'bandpass'; bf.frequency.value = 520; bf.Q.value = 1.6;
    const amp = c.createGain(); amp.gain.value = 0.5;
    const bl = c.createOscillator(); bl.frequency.value = 0.42;
    const blg = c.createGain(); blg.gain.value = 0.5; bl.connect(blg); blg.connect(amp.gain); bl.start();
    this.breathLevel = c.createGain(); this.breathLevel.gain.value = 0;
    br.connect(bf); bf.connect(amp); amp.connect(this.breathLevel); this.breathLevel.connect(this.bus);
    const bf2 = c.createBiquadFilter(); bf2.type = 'lowpass'; bf2.frequency.value = 110;
    const growlO = c.createOscillator(); growlO.type = 'sawtooth'; growlO.frequency.value = 36;
    const gg = c.createGain(); gg.gain.value = 0.5;
    growlO.connect(bf2); bf2.connect(gg); gg.connect(amp); growlO.start();
  }

  reset() {
    this.stopChase();
    this.heartRate = 0;
    this.setBreath(0);
  }

  loopNoise() {
    const s = this.ctx.createBufferSource();
    s.buffer = this.noiseBuf; s.loop = true; s.start(0, Math.random());
    return s;
  }

  out(pan = 0, dry = false) {
    const p = this.ctx.createStereoPanner();
    p.pan.value = Math.max(-1, Math.min(1, pan));
    p.connect(dry ? this.master : this.bus);
    return p;
  }

  tone(freq, type, dur, vol, o = {}) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime + (o.delay || 0);
    const osc = c.createOscillator(); osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    if (o.slide) osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.slide), t + dur);
    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + (o.attack || 0.01));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    let node = osc;
    if (o.lp) { const f = c.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = o.lp; node.connect(f); node = f; }
    node.connect(g); g.connect(this.out(o.pan, o.dry));
    osc.start(t); osc.stop(t + dur + 0.05);
  }

  burst(dur, vol, o = {}) {
    if (!this.ctx) return;
    const c = this.ctx, t = c.currentTime + (o.delay || 0);
    const s = c.createBufferSource(); s.buffer = this.noiseBuf; s.loop = true;
    const f = c.createBiquadFilter(); f.type = o.type || 'lowpass';
    f.frequency.setValueAtTime(o.freq || 800, t);
    if (o.slide) f.frequency.exponentialRampToValueAtTime(o.slide, t + dur);
    f.Q.value = o.q || 0.7;
    const g = c.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + (o.attack || 0.005));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(this.out(o.pan, o.dry));
    s.start(t, Math.random()); s.stop(t + dur + 0.05);
  }

  // ---------- one-shots ----------
  step(sprint) {
    this.burst(0.09, sprint ? 0.16 : 0.09, { freq: 300 + Math.random() * 200, dry: true });
    this.tone(70 + Math.random() * 20, 'sine', 0.08, sprint ? 0.14 : 0.08, { slide: 40, dry: true });
    if (Math.random() < 0.12) this.creak((Math.random() - 0.5) * 0.4, 0.12);
  }
  click() { this.tone(1800, 'square', 0.03, 0.08, { dry: true }); this.burst(0.02, 0.1, { type: 'highpass', freq: 3000, dry: true }); }
  pickup() { this.tone(880, 'triangle', 0.25, 0.12); this.tone(1320, 'triangle', 0.4, 0.1, { delay: 0.08 }); this.burst(0.05, 0.08, { type: 'highpass', freq: 5000 }); }
  paper() { this.burst(0.25, 0.1, { type: 'highpass', freq: 3500, slide: 1500 }); }
  rattle() { for (let i = 0; i < 4; i++) this.burst(0.05, 0.25, { type: 'bandpass', freq: 1400, q: 3, delay: i * 0.08 }); this.tone(90, 'square', 0.1, 0.15, { lp: 300 }); }
  creak(pan = 0, vol = 0.3) {
    const f = 240 + Math.random() * 200;
    this.tone(f, 'sawtooth', 0.7 + Math.random() * 0.5, vol * 0.25, { slide: f * (0.6 + Math.random() * 0.9), pan, lp: 1400, attack: 0.15 });
    this.tone(f * 1.52, 'square', 0.6, vol * 0.08, { slide: f * 1.1, pan, lp: 2000, attack: 0.2 });
  }
  knock(pan = 0, vol = 0.5) {
    for (let i = 0; i < 3; i++) { this.tone(110, 'sine', 0.14, vol, { slide: 55, pan, delay: i * 0.3 }); this.burst(0.05, vol * 0.5, { freq: 500, pan, delay: i * 0.3 }); }
  }
  thump(pan = 0, vol = 0.7) { this.tone(70, 'sine', 0.5, vol, { slide: 28, pan }); this.burst(0.2, vol * 0.5, { freq: 200, pan }); }
  whisper(pan = 0, vol = 0.22) {
    for (let i = 0; i < 6; i++) {
      this.burst(0.12 + Math.random() * 0.2, vol, { type: 'bandpass', freq: 1500 + Math.random() * 2500, q: 5, pan: pan + (Math.random() - 0.5) * 0.3, delay: i * 0.17 + Math.random() * 0.06, attack: 0.04 });
    }
  }
  slam(pan = 0, delay = 0, vol = 1) {
    this.tone(90, 'sine', 0.6, vol, { slide: 30, pan, delay });
    this.burst(0.35, vol, { freq: 900, slide: 120, pan, delay });
    this.burst(0.05, vol * 0.8, { type: 'highpass', freq: 2000, pan, delay });
  }
  thunder(vol = 0.8) {
    const pan = (Math.random() - 0.5) * 1.2;
    this.burst(0.3, vol * 0.7, { freq: 2500, slide: 300, pan });
    this.burst(3.5 + Math.random() * 2, vol, { freq: 220, slide: 50, pan, attack: 0.08 });
    this.burst(2.5, vol * 0.6, { freq: 90, pan: -pan, delay: 0.5, attack: 0.3 });
    this.tone(38, 'sine', 3, vol * 0.5, { slide: 24, delay: 0.1, attack: 0.2 });
  }
  stinger(vol = 0.9) {
    for (const f of [220, 233, 311, 466, 622, 932]) this.tone(f, 'sawtooth', 1.6, vol * 0.16, { slide: f * 1.06, pan: (Math.random() - 0.5) * 1.4 });
    this.burst(0.5, vol * 0.7, { type: 'highpass', freq: 1500 });
    this.tone(50, 'sine', 1.2, vol, { slide: 25 });
  }
  growl() {
    this.tone(48, 'sawtooth', 2.6, 0.6, { slide: 30, lp: 260, attack: 0.5 });
    this.tone(51, 'sawtooth', 2.6, 0.5, { slide: 33, lp: 220, attack: 0.5 });
    this.burst(2.4, 0.3, { type: 'bandpass', freq: 240, q: 2, attack: 0.5 });
  }
  shriek() {
    this.tone(1400, 'sawtooth', 1.3, 0.3, { slide: 320, lp: 5000 });
    this.tone(1570, 'square', 1.1, 0.18, { slide: 250, lp: 4000 });
    this.burst(1.2, 0.5, { type: 'bandpass', freq: 3200, slide: 600, q: 2 });
  }
  scream() {
    for (const f of [520, 780, 1040, 1310, 1750]) this.tone(f, 'sawtooth', 2.0, 0.28, { slide: f * 0.45, pan: (Math.random() - 0.5) });
    this.burst(1.8, 1.0, { type: 'bandpass', freq: 2000, slide: 500, q: 1 });
    this.tone(45, 'sine', 2, 1.0, { slide: 22 });
  }
  sizzle() {
    if (!this.ctx || this.ctx.currentTime - this.lastSizzle < 0.09) return;
    this.lastSizzle = this.ctx.currentTime;
    this.burst(0.14, 0.12, { type: 'highpass', freq: 4000 + Math.random() * 3000 });
  }

  setBreath(v) {
    if (!this.ctx) return;
    this.breathLevel.gain.setTargetAtTime(v * 0.5, this.ctx.currentTime, 0.4);
  }
  startChase() { this.chaseOn = true; this.chaseStep = 0; this.nextChase = this.ctx ? this.ctx.currentTime + 0.1 : 0; }
  stopChase() { this.chaseOn = false; }

  update() {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    if (this.heartRate > 0.02 && t >= this.nextBeat) {
      const v = 0.25 + this.heartRate * 0.6;
      this.tone(58, 'sine', 0.16, v, { slide: 34, dry: true });
      this.tone(52, 'sine', 0.14, v * 0.7, { slide: 30, delay: 0.17, dry: true });
      this.nextBeat = t + 60 / (55 + this.heartRate * 100);
    }
    if (this.chaseOn && t >= this.nextChase) {
      const seq = [55, 55, 58.27, 55, 51.91, 55, 65.41, 61.74];
      const f = seq[this.chaseStep % 8];
      this.tone(f, 'sawtooth', 0.2, 0.3, { lp: 500 });
      this.tone(f * 2.01, 'square', 0.12, 0.1, { lp: 900 });
      if (this.chaseStep % 2 === 0) this.burst(0.06, 0.22, { freq: 180 });
      if (this.chaseStep % 16 === 12) this.tone(1244, 'sawtooth', 1.4, 0.07, { slide: 1320, lp: 3000, attack: 0.5, pan: Math.random() - 0.5 });
      if (this.chaseStep % 16 === 4) this.tone(1175, 'sawtooth', 1.4, 0.06, { slide: 1108, lp: 3000, attack: 0.5, pan: Math.random() - 0.5 });
      this.chaseStep++;
      this.nextChase = t + 0.2;
    }
  }
}
```

```js path=bridge-horror-house/src/systems/Ghost.js
import * as THREE from 'three';

const R = (a, b) => a + Math.random() * (b - a);

export class Ghost {
  constructor(scene, tex) {
    this.tex = tex;
    this.group = new THREE.Group();
    this.group.visible = false;
    scene.add(this.group);
    this.pos = this.group.position;
    this.mode = 'none';      // none | stalk | chase
    this.phase = 'hidden';   // hidden | apparition | active | banished
    this.timer = 0;
    this.stalkWait = 0;
    this.alpha = 0;
    this.burn = 0;
    this.burning = false;
    this.t = 0;
    this.mats = [];

    const mk = (m, base = 1) => { m.transparent = true; m.userData.base = base; this.mats.push(m); return m; };
    const black = mk(new THREE.MeshStandardMaterial({ color: 0x060606, roughness: 1 }));
    const skin = mk(new THREE.MeshStandardMaterial({ color: 0x8f897c, roughness: 0.8 }));
    const cloth = mk(new THREE.MeshStandardMaterial({ color: 0x0a0909, roughness: 1, side: THREE.DoubleSide }), 0.92);
    this.eyeMat = mk(new THREE.MeshBasicMaterial({ color: 0xff3a1a, fog: false }));

    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.36, 1.75, 9, 1, true), cloth);
    body.position.y = 0.98; body.castShadow = true;
    const chest = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.34, 0.2), black);
    chest.position.y = 1.86; chest.castShadow = true;
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.2, 6), skin);
    neck.position.y = 2.1;
    this.head = new THREE.Group();
    this.head.position.y = 2.3;
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), skin);
    skull.scale.set(0.9, 1.35, 0.95); skull.castShadow = true;
    this.head.add(skull);
    this.faces = this.tex.ghostFaces.map((map) => {
      const m = mk(new THREE.MeshStandardMaterial({ map, emissive: 0x444444, emissiveMap: map, roughness: 0.9, depthWrite: false }));
      const f = new THREE.Mesh(new THREE.PlaneGeometry(0.34, 0.46), m);
      f.position.z = 0.15; f.visible = false;
      this.head.add(f);
      return f;
    });
    this.eyes = [];
    for (const x of [-0.052, 0.052]) {
      const e = new THREE.Mesh(new THREE.SphereGeometry(0.016, 8, 6), this.eyeMat);
      e.position.set(x, 0.052, 0.165);
      this.head.add(e); this.eyes.push(e);
    }
    this.group.add(body, chest, neck, this.head);

    // long arms with claw fingers
    this.arms = [];
    for (const side of [-1, 1]) {
      const arm = new THREE.Group();
      arm.position.set(side * 0.3, 1.95, 0);
      const upper = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.025, 1.25, 6), skin);
      upper.position.y = -0.62; upper.castShadow = true;
      arm.add(upper);
      for (let i = 0; i < 4; i++) {
        const claw = new THREE.Mesh(new THREE.ConeGeometry(0.012, 0.3, 5), black);
        claw.position.set((i - 1.5) * 0.028, -1.38, 0.02);
        claw.rotation.x = Math.PI + 0.25; claw.rotation.z = (i - 1.5) * 0.14;
        arm.add(claw);
      }
      arm.rotation.z = side * 0.1;
      this.group.add(arm); this.arms.push(arm);
    }

    // tattered strips
    this.strips = [];
    for (let i = 0; i < 14; i++) {
      const a = (i / 14) * Math.PI * 2;
      const len = R(0.5, 1.2);
      const geo = new THREE.PlaneGeometry(R(0.05, 0.12), len);
      geo.translate(0, -len / 2, 0);
      const s = new THREE.Mesh(geo, cloth);
      const top = R(0.9, 1.9);
      const rad = 0.14 + (1.9 - top) * 0.13;
      s.position.set(Math.cos(a) * rad, top, Math.sin(a) * rad);
      s.rotation.y = -a + Math.PI / 2;
      s.userData.phase = Math.random() * 6;
      this.group.add(s); this.strips.push(s);
    }

    // black vapor
    const n = 70;
    const vp = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { vp[i * 3] = R(-0.5, 0.5); vp[i * 3 + 1] = R(0, 2.5); vp[i * 3 + 2] = R(-0.5, 0.5); }
    const vg = new THREE.BufferGeometry();
    vg.setAttribute('position', new THREE.BufferAttribute(vp, 3));
    this.vaporMat = mk(new THREE.PointsMaterial({ color: 0x020202, size: 0.3, depthWrite: false }), 0.55);
    this.vapor = new THREE.Points(vg, this.vaporMat);
    this.vapor.frustumCulled = false;
    this.group.add(this.vapor);

    this.setFace(0);
    this.setAlpha(0);
  }

  get present() { return this.phase === 'apparition' || this.phase === 'active'; }
  get dangerous() { return this.phase === 'active' && this.alpha > 0.6; }

  setFace(i) {
    this.faceIdx = i;
    this.faces.forEach((f, k) => { f.visible = k === i; });
  }

  setAlpha(a) {
    this.alpha = a;
    for (const m of this.mats) m.opacity = m.userData.base * a;
  }

  hide() {
    this.phase = 'hidden';
    this.group.visible = false;
    this.burn = 0;
  }

  // brief, harmless manifestation
  appear(x, z, dur, face = 0) {
    this.pos.set(x, 0, z);
    this.phase = 'apparition';
    this.timer = dur;
    this.burn = 0;
    this.setFace(face);
    this.setAlpha(1);
    this.group.visible = true;
  }

  startStalk() {
    if (this.mode === 'chase') return;
    this.mode = 'stalk';
    this.stalkWait = 14;
  }

  startChase(px, pz) {
    this.mode = 'chase';
    this.spawnNear(px, pz, 9);
    this.phase = 'active';
    this.timer = 0;
    this.burn = 0;
    this.setFace(2);
    this.group.visible = true;
    this.setAlpha(0);
  }

  spawnNear(px, pz, dist) {
    let best = null, bestD = -1;
    for (let i = 0; i < 10; i++) {
      const a = Math.random() * Math.PI * 2;
      const x = Math.max(-9.3, Math.min(9.3, px + Math.cos(a) * dist));
      const z = Math.max(-7.3, Math.min(6, pz + Math.sin(a) * dist)); // never spawn on the front door
      const d = Math.hypot(x - px, z - pz);
      if (d > bestD) { bestD = d; best = [x, z]; }
      if (d > dist * 0.85) break;
    }
    this.pos.set(best[0], 0, best[1]);
  }

  applyBurn(dt) {
    if (!this.present) return false;
    this.burning = true;
    this.burn += dt / (this.mode === 'chase' ? 1.9 : 1.5);
    if (this.burn >= 1) {
      this.burn = 0;
      if (this.mode === 'chase') { this.phase = 'banished'; this.timer = 8; }
      else { this.phase = 'hidden'; this.stalkWait = R(22, 34); }
      this.group.visible = false;
      return true;
    }
    return false;
  }

  coolBurn(dt) {
    this.burning = false;
    this.burn = Math.max(0, this.burn - dt * 0.35);
  }

  update(dt, ppos, quiet) {
    this.t += dt;
    const t = this.t;

    if (this.phase === 'hidden') {
      if (this.mode === 'stalk') {
        this.stalkWait -= dt;
        if (this.stalkWait <= 0 && quiet <= 0) {
          this.spawnNear(ppos.x, ppos.z, 7.5);
          this.phase = 'active';
          this.timer = 13;
          this.setFace(Math.random() < 0.5 ? 0 : 1);
          this.setAlpha(0);
          this.group.visible = true;
        }
      }
      return;
    }
    if (this.phase === 'banished') {
      this.timer -= dt;
      if (this.timer <= 0) { // he reforms
        this.spawnNear(ppos.x, ppos.z, 8.5);
        this.phase = 'active';
        this.setFace(2);
        this.setAlpha(0);
        this.group.visible = true;
      }
      return;
    }

    const dx = ppos.x - this.pos.x, dz = ppos.z - this.pos.z;
    const d = Math.hypot(dx, dz) + 0.0001;
    this.group.rotation.y = Math.atan2(dx, dz);

    if (this.phase === 'apparition') {
      this.timer -= dt;
      // corrupted-frame flicker
      this.group.visible = Math.random() > 0.22;
      this.group.scale.set(1 + (Math.random() < 0.15 ? R(-0.25, 0.4) : 0), 1 + (Math.random() < 0.1 ? R(-0.1, 0.15) : 0), 1);
      this.head.rotation.z = Math.random() < 0.2 ? R(-0.7, 0.7) : 0.25;
      if (this.timer <= 0) { this.group.scale.set(1, 1, 1); this.hide(); }
    } else {
      // active: stalking drift or chase lurch
      this.setAlpha(Math.min(1, this.alpha + dt * (this.mode === 'chase' ? 1.4 : 0.6)));
      let speed;
      if (this.mode === 'chase') {
        speed = 2.55 * (0.55 + 0.75 * Math.max(0, Math.sin(t * 3.1)) + 0.25); // lurching
        if (d > 11) speed = 5;
      } else {
        speed = 0.85;
        this.timer -= dt;
        if (this.timer <= 0) { this.phase = 'hidden'; this.group.visible = false; this.stalkWait = R(18, 32); return; }
      }
      if (this.burning) speed *= 0.4;
      const weave = this.mode === 'chase' ? Math.sin(t * 2.3) * 0.9 : Math.sin(t * 0.9) * 0.3;
      const nx = dx / d, nz = dz / d;
      const k = Math.min(1, d / 3); // weave fades when close so contact is fair
      this.pos.x += (nx + -nz * weave * k) * speed * dt;
      this.pos.z += (nz + nx * weave * k) * speed * dt;
      this.group.visible = this.mode === 'chase' ? Math.random() > 0.04 : Math.random() > 0.08;
      const j = this.burning ? 0.12 : 0;
      this.group.scale.set(1 + R(-j, j), 1 + R(-j, j) + Math.sin(t * 3.1) * 0.03, 1);
      this.head.rotation.z = Math.sin(t * 1.3) * 0.35 + (Math.random() < 0.03 ? R(-0.8, 0.8) : 0);
      this.head.rotation.x = this.mode === 'chase' ? -0.15 : 0.1;
    }

    // limbs, strips, vapor, eyes
    const reach = this.mode === 'chase' && this.phase === 'active' ? -1.25 : -0.15;
    this.arms.forEach((a, i) => {
      a.rotation.x += (reach + Math.sin(t * 2.2 + i * 2) * 0.18 - a.rotation.x) * Math.min(1, dt * 4);
    });
    for (const s of this.strips) {
      s.rotation.x = Math.sin(t * 2.4 + s.userData.phase) * 0.35;
      s.rotation.z = Math.sin(t * 1.7 + s.userData.phase * 2) * 0.2;
    }
    const vp = this.vapor.geometry.attributes.position;
    for (let i = 0; i < vp.count; i++) {
      let y = vp.getY(i) + dt * (0.25 + (i % 5) * 0.08);
      if (y > 2.7) { y = 0; vp.setX(i, R(-0.45, 0.45)); vp.setZ(i, R(-0.45, 0.45)); }
      vp.setY(i, y);
      vp.setX(i, vp.getX(i) + Math.sin(t * 2 + i) * dt * 0.1);
    }
    vp.needsUpdate = true;
    const pulse = 0.7 + Math.sin(t * 9) * 0.3;
    if (this.burning) this.eyeMat.color.setRGB(3, 3, 2.6);
    else this.eyeMat.color.setRGB(2.4 * pulse, 0.35 * pulse, 0.12 * pulse);
    if (this.burning && this.faceIdx !== 2) this.setFace(2);
  }
}
```

```js path=bridge-horror-house/src/systems/ScareDirector.js
import { roomAt } from '../world/House.js';

const R = (a, b) => a + Math.random() * (b - a);

export class ScareDirector {
  constructor(game) {
    this.g = game;
    this.fired = new Set();
    this.queue = [];
    this.quiet = 6;           // seconds during which nothing ambient may happen
    this.ambientT = R(10, 16);
    this.lightningT = R(8, 14);
    this.act = 1;
  }

  after(sec, fn) { this.queue.push({ t: sec, fn }); }

  once(id, fn) {
    if (this.fired.has(id)) return false;
    this.fired.add(id);
    fn();
    return true;
  }

  pan(x) { // stereo position of a world x relative to the player's facing
    const p = this.g.player;
    const dx = x - p.pos.x;
    return Math.max(-1, Math.min(1, (dx * Math.cos(p.yaw)) / 6));
  }

  enterRoom(room) {
    const { audio, hud, house, player } = this.g;
    if (this.act === 3) return; // nothing scripted interrupts the finale
    if (room === 'living') this.once('living', () => {
      this.quiet = 9;
      this.after(1.2, () => audio.thump(-0.7, 0.6));
      this.after(2.6, () => audio.whisper(0.6, 0.2));
    });
    if (room === 'hallway') this.once('hallway', () => {
      this.quiet = 12;
      this.after(0.9, () => {
        house.flickerT = 2.2;
        audio.slam(player.yaw > -1.57 && player.yaw < 1.57 ? 0 : 0.3, 0.5, 0.9);
        this.after(0.5, () => hud.shake(0.07));
      });
    });
    if (room === 'kitchen') this.once('kitchen', () => {
      this.quiet = 14;
      this.after(0.7, () => {
        audio.slam(0.5, 0, 0.9);
        audio.stinger(0.5);
        hud.shake(0.06);
        this.after(0.5, () => { house.slideChair(); audio.creak(-0.3, 0.9); });
      });
    });
    if (room === 'bedroom') this.once('bedroom', () => {
      this.quiet = 14;
      this.after(0.8, () => {
        const d = house.doors.bedroom;
        if (d.open) { d.open = false; d.slam = true; }
        audio.slam(0, 0, 1);
        hud.shake(0.1);
        this.after(1.5, () => audio.whisper(0, 0.18));
      });
    });
  }

  onKey(room, count) {
    const { audio, hud, ghost, house, player } = this.g;
    if (count >= 3) { this.startFinale(); return; }
    let delay = 0;
    if (room === 'study') {
      this.once('studyKey', () => {
        this.quiet = 14;
        delay = 7;
        this.after(0.5, () => {
          house.doors.study.open = true;
          ghost.appear(-7, -2.25, 1.2, 0);
          audio.stinger(0.85);
          hud.flash('#fff', 0.25);
          hud.shake(0.05);
        });
      });
    }
    if (count === 2) {
      this.once('secondKey', () => {
        this.after(delay + 1.2, () => {
          this.act = 2;
          this.quiet = Math.max(this.quiet, 10);
          audio.growl();
          hud.shake(0.05);
          hud.message('Something in the house is awake.', 4);
          hud.setObjective('Find the last key — burn him with the light');
          ghost.startStalk();
        });
      });
    } else {
      hud.message('A brass key. Two more.', 3);
    }
  }

  startFinale() {
    const { audio, hud, ghost, house, player } = this.g;
    this.act = 3;
    this.quiet = 9999;
    this.queue.length = 0;
    ghost.hide();
    ghost.mode = 'chase';
    ghost.phase = 'hidden';
    // blackout beat
    house.blackout = true;
    player.blackout = 2.6;
    audio.click();
    audio.thump(0, 0.9);
    hud.setObjective('');
    this.after(2.6, () => {
      audio.scream();
      audio.startChase();
      hud.flash('#a00', 0.6);
      hud.shake(0.14);
      hud.setObjective('RUN — UNLOCK THE FRONT DOOR');
      hud.message('RUN.', 3);
      ghost.startChase(player.pos.x, player.pos.z);
    });
  }

  ambientEvent() {
    const a = this.g.audio;
    const pan = R(-1, 1);
    const r = Math.random();
    if (r < 0.3) a.creak(pan, 0.5);
    else if (r < 0.5) a.knock(pan, 0.35);
    else if (r < 0.7) a.whisper(pan, 0.15);
    else if (r < 0.88) a.thump(pan, 0.4);
    else { a.creak(pan, 0.4); this.after(0.8, () => a.creak(-pan, 0.4)); }
  }

  update(dt) {
    const { player, house, audio, hud } = this.g;
    if (this.quiet > 0) this.quiet -= dt;

    for (let i = this.queue.length - 1; i >= 0; i--) {
      const q = this.queue[i];
      q.t -= dt;
      if (q.t <= 0) { this.queue.splice(i, 1); q.fn(); }
    }

    const room = roomAt(player.pos.x, player.pos.z);
    if (room !== this.room) {
      this.room = room;
      this.enterRoom(room);
    }

    // randomized ambient dread between the scripted beats
    this.ambientT -= dt;
    if (this.ambientT <= 0) {
      if (this.quiet <= 0) this.ambientEvent();
      this.ambientT = this.act === 1 ? R(11, 24) : R(8, 17);
    }

    // rolling storm
    this.lightningT -= dt;
    if (this.lightningT <= 0) {
      this.lightningT = R(14, 38);
      house.lightning = 1;
      hud.flash('#cde', 0.07);
      const delay = R(0.25, 1.6);
      this.after(delay, () => audio.thunder(0.55 + (1.6 - delay) * 0.25));
      if (Math.random() < 0.4) this.after(0.22, () => { house.lightning = 0.8; });
    }
  }
}
```

```js path=bridge-horror-house/src/ui/HUD.js
const $ = (id) => document.getElementById(id);

export class HUD {
  constructor(tex) {
    this.el = {
      hud: $('hud'), objective: $('objective'), keys: $('keys'), batteryFill: $('batteryFill'),
      burn: $('burn'), burnFill: $('burnFill'), prompt: $('prompt'), message: $('message'),
      flash: $('flash'), note: $('note'), notePaper: $('notePaper'), pause: $('pause'),
      title: $('title'), death: $('death'), win: $('win'), winStats: $('winStats'), jump: $('jump'), grain: $('grain'),
    };
    this.el.jump.style.backgroundImage = `url(${tex.faceCanvas(2).toDataURL()})`;
    this.grainCtx = this.el.grain.getContext('2d');
    this.grainImg = this.grainCtx.createImageData(160, 90);
    this.grainT = 0;
    this.flashA = 0;
    this.shakeAmt = 0;
    this.msgT = 0;
    this.deathT = -1;
    this.lastPrompt = '';
  }

  reset() {
    this.setKeys(0);
    this.setBattery(1);
    this.setBurn(0, false);
    this.prompt('');
    this.el.message.style.opacity = 0;
    this.msgT = 0;
    this.shakeAmt = 0;
    this.deathT = -1;
    this.el.jump.classList.remove('on');
    this.hideNote();
  }

  showPlaying() {
    for (const k of ['title', 'death', 'win', 'pause', 'note']) this.el[k].style.display = 'none';
    this.el.jump.classList.remove('on');
    this.el.hud.style.display = 'block';
  }

  pause(on) { this.el.pause.style.display = on ? 'flex' : 'none'; }
  setObjective(t) { this.el.objective.textContent = t; }
  setKeys(n) { this.el.keys.textContent = `KEYS ${n}/3`; }

  setBattery(v) {
    this.el.batteryFill.style.width = `${Math.round(v * 100)}%`;
    this.el.batteryFill.style.background = v < 0.2 ? '#c0392b' : '#d8c98a';
  }

  setBurn(v, show) {
    this.el.burn.style.opacity = show ? 1 : 0;
    this.el.burnFill.style.width = `${Math.round(Math.min(1, v) * 100)}%`;
  }

  prompt(t) {
    if (t === this.lastPrompt) return;
    this.lastPrompt = t;
    this.el.prompt.textContent = t;
  }

  message(t, dur = 3) {
    this.el.message.textContent = t;
    this.el.message.style.opacity = 1;
    this.msgT = dur;
  }

  flash(color, alpha) {
    this.el.flash.style.background = color;
    this.flashA = Math.max(this.flashA, alpha);
  }

  shake(a) { this.shakeAmt = Math.max(this.shakeAmt, a); }

  showNote(text) {
    this.el.notePaper.textContent = text;
    this.el.note.style.display = 'flex';
  }
  hideNote() { this.el.note.style.display = 'none'; }

  showDeath() {
    this.el.hud.style.display = 'none';
    this.el.note.style.display = 'none';
    this.el.pause.style.display = 'none';
    this.el.jump.classList.add('on');
    this.deathT = 1.3;
  }

  showWin(time, banishes) {
    this.el.hud.style.display = 'none';
    this.el.pause.style.display = 'none';
    const m = Math.floor(time / 60), s = Math.floor(time % 60);
    this.el.winStats.textContent = `You survived ${m}:${String(s).padStart(2, '0')} in the house and banished him ${banishes} time${banishes === 1 ? '' : 's'}.`;
    this.el.win.style.display = 'flex';
  }

  update(dt) {
    // animated film grain
    this.grainT -= dt;
    if (this.grainT <= 0) {
      this.grainT = 0.05;
      const d = this.grainImg.data;
      for (let i = 0; i < d.length; i += 4) {
        const v = Math.random() * 255;
        d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255;
      }
      this.grainCtx.putImageData(this.grainImg, 0, 0);
    }
    if (this.flashA > 0) {
      this.flashA = Math.max(0, this.flashA - dt * 1.8);
      this.el.flash.style.opacity = this.flashA;
    }
    if (this.shakeAmt > 0) this.shakeAmt = Math.max(0, this.shakeAmt - dt * 0.25);
    if (this.msgT > 0) {
      this.msgT -= dt;
      if (this.msgT <= 0) this.el.message.style.opacity = 0;
    }
    if (this.deathT > 0) {
      this.deathT -= dt;
      if (this.deathT <= 0) {
        this.el.jump.classList.remove('on');
        this.el.death.style.display = 'flex';
      }
    }
  }
}
```
