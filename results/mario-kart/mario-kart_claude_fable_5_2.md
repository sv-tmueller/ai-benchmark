# Turbo Tumble Grand Prix — an original Three.js kart racer

## Report

The game is built and complete. One deliberate deviation from the request: I did not make a clone of Mario Kart. Its name, characters, tracks, items and look belong to Nintendo, so instead this is an **original arcade kart racer in the same genre** — its own name, its own cast, its own circuit and its own items — with the mechanics that make the genre fun:

- **8-kart races, 3 laps** on "Skyline Meadows", a flowing spline circuit with an S-bend, sweepers, curbs, grass run-off and barrier posts
- **Drift + mini-turbo**: hop into a drift, hold it to charge three spark levels (cyan → orange → magenta), release for a bigger boost
- **Items** from prism crates, weighted by race position: Comet Boost, Goo Puddle, Zap Bolt (track-following, homing), Bubble Shield
- **Boost pads**, off-road slowdown, wall deflection, kart-to-kart bumping, spin-outs
- **AI rivals** with pure-pursuit steering, lane wandering, item use, per-driver skill and light rubber-banding
- **Three speed classes** (Relaxed / Swift / Blazing) and **8 selectable original drivers**
- **Full HUD**: position, lap, timer, item slot with roulette, drift gauge, speedometer, live minimap, wrong-way warning, countdown, final-lap banner, results table with best lap
- **Presentation**: soft shadows, ACES tone mapping, fog, gradient sky, instanced forest, mountains, clouds, hot-air balloons, start arch, chase camera with boost FOV kick, additive particle sparks / flames / dust
- **Audio**, all synthesised with WebAudio (no asset files): engine note, sound effects and an original chiptune loop

No build step and no assets. Three.js is loaded from a CDN through an import map.

### Run it

ES modules need an HTTP origin, so serve the folder rather than opening the file directly:

```bash
npm start          # runs: npx --yes serve -l 5173 .
# or
python3 -m http.server 5173
```

Then open `http://localhost:5173`.

### Controls

| Action | Keys |
| --- | --- |
| Accelerate | `W` / `↑` |
| Brake / reverse | `S` / `↓` |
| Steer | `A` `D` / `←` `→` |
| Hop / drift (hold while steering) | `Space` or `Shift` |
| Use item | `E` or `X` |
| Pause | `Esc` or `P` |
| Mute | `M` |

### Project layout

```
turbo-tumble/
├── index.html
├── style.css
├── package.json
└── src/
    ├── config.js      tuning constants, drivers, items, speed classes
    ├── track.js       spline circuit, road meshes, scenery, track queries
    ├── kart.js        kart model + arcade driving physics
    ├── particles.js   pooled additive particle system
    ├── audio.js       WebAudio engine, sfx and music sequencer
    └── main.js        game loop, AI, items, camera, HUD, menus
```

---

## Files

### `package.json`

```json
{
  "name": "turbo-tumble-grand-prix",
  "version": "1.0.0",
  "private": true,
  "description": "An original arcade kart racer built with Three.js",
  "scripts": {
    "start": "npx --yes serve -l 5173 ."
  }
}
```

### `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Turbo Tumble Grand Prix</title>
  <link rel="stylesheet" href="./style.css">
  <script type="importmap">
    { "imports": { "three": "https://unpkg.com/three@0.160.0/build/three.module.js" } }
  </script>
</head>
<body>
  <div id="game"></div>
  <div id="boostFx"></div>

  <div id="hud" class="hidden">
    <div id="posBox"><span id="pos">1</span><span id="posSuffix">st</span></div>
    <div id="topRight">
      <div id="lap">Lap 1/3</div>
      <div id="time">0:00.000</div>
    </div>
    <div id="itemSlot"><span id="itemIcon"></span><small id="itemName"></small></div>
    <div id="speedBox">
      <div id="driftTrack"><div id="driftBar"></div></div>
      <span id="speed">0</span><small>km/h</small>
    </div>
    <canvas id="minimap" width="180" height="180"></canvas>
    <div id="wrongway" class="hidden">WRONG WAY</div>
  </div>

  <div id="center"></div>
  <div id="banner"></div>

  <div id="menu" class="overlay">
    <div class="panel">
      <h1>TURBO TUMBLE<span>GRAND PRIX</span></h1>
      <h2>Choose your driver</h2>
      <div id="racers"></div>
      <h2>Speed class</h2>
      <div id="classes"></div>
      <button id="startBtn" class="big">START RACE</button>
      <p class="help">
        <b>W/↑</b> accelerate · <b>S/↓</b> brake · <b>A D / ← →</b> steer ·
        <b>Space/Shift</b> hop &amp; drift · <b>E/X</b> use item · <b>Esc</b> pause · <b>M</b> mute
      </p>
      <p class="help">Hold a drift to charge sparks, then release for a mini-turbo.</p>
    </div>
  </div>

  <div id="pause" class="overlay hidden">
    <div class="panel small">
      <h1>PAUSED</h1>
      <button id="resumeBtn" class="big">RESUME</button>
      <button id="quitBtn">Quit to menu</button>
    </div>
  </div>

  <div id="results" class="overlay hidden">
    <div class="panel small">
      <h1 id="resultsTitle">FINISH!</h1>
      <ol id="resultsList"></ol>
      <p id="bestLap" class="help"></p>
      <button id="againBtn" class="big">RACE AGAIN</button>
      <button id="menuBtn">Back to menu</button>
    </div>
  </div>

  <div id="loadError" class="hidden">
    The game could not load. Serve this folder over HTTP
    (for example <code>npm start</code> or <code>python3 -m http.server</code>)
    and check your internet connection (Three.js is loaded from a CDN).
  </div>

  <script>
    setTimeout(function () {
      if (!window.__gameBooted) document.getElementById('loadError').classList.remove('hidden');
    }, 5000);
  </script>
  <script type="module" src="./src/main.js"></script>
</body>
</html>
```

### `style.css`

```css
* { box-sizing: border-box; }
html, body {
  margin: 0; height: 100%; overflow: hidden; background: #0b1020; color: #fff;
  font-family: "Trebuchet MS", "Segoe UI", system-ui, sans-serif;
  user-select: none; -webkit-user-select: none;
}
#game, #game canvas { position: fixed; inset: 0; width: 100%; height: 100%; display: block; }
.hidden { display: none !important; }

/* ---------- boost vignette ---------- */
#boostFx {
  position: fixed; inset: 0; pointer-events: none; opacity: 0; transition: opacity .18s;
  background:
    radial-gradient(ellipse at center, rgba(255,255,255,0) 45%, rgba(120,220,255,.28) 80%, rgba(255,255,255,.55) 100%),
    repeating-conic-gradient(from 0deg at 50% 50%, rgba(255,255,255,0) 0deg 5deg, rgba(255,255,255,.07) 5deg 6deg);
  -webkit-mask-image: radial-gradient(ellipse at center, transparent 35%, #000 85%);
          mask-image: radial-gradient(ellipse at center, transparent 35%, #000 85%);
}
#boostFx.on { opacity: 1; }

/* ---------- HUD ---------- */
#hud { position: fixed; inset: 0; pointer-events: none; font-style: italic; font-weight: 900; }
#hud > * { position: absolute; text-shadow: 0 3px 0 rgba(0,0,0,.45), 0 0 14px rgba(0,0,0,.35); }
#posBox { left: 28px; bottom: 20px; line-height: 1; }
#pos {
  font-size: 120px;
  background: linear-gradient(#fff36b, #ff8a1f); -webkit-background-clip: text; background-clip: text;
  color: transparent; -webkit-text-stroke: 3px #3a1b00; text-shadow: none;
  filter: drop-shadow(0 5px 0 rgba(0,0,0,.4));
}
#posSuffix { font-size: 44px; margin-left: 4px; color: #ffd45e; }
#topRight { right: 28px; top: 20px; text-align: right; }
#lap { font-size: 34px; }
#time { font-size: 24px; font-variant-numeric: tabular-nums; opacity: .92; }
#itemSlot {
  left: 50%; top: 18px; width: 96px; height: 96px; margin-left: -48px;
  border-radius: 22px; border: 4px solid rgba(255,255,255,.9);
  background: linear-gradient(160deg, rgba(40,60,130,.75), rgba(15,20,50,.75));
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(0,0,0,.4), inset 0 0 18px rgba(120,180,255,.35);
  font-style: normal;
}
#itemIcon { font-size: 44px; line-height: 1; text-shadow: none; }
#itemName { font-size: 10px; letter-spacing: .5px; margin-top: 4px; font-weight: 700; opacity: .9; }
#speedBox { right: 28px; bottom: 24px; text-align: right; }
#speed { font-size: 64px; font-variant-numeric: tabular-nums; }
#speedBox small { font-size: 18px; margin-left: 6px; opacity: .85; }
#driftTrack {
  width: 190px; height: 12px; border-radius: 8px; margin: 0 0 4px auto;
  background: rgba(0,0,0,.45); border: 2px solid rgba(255,255,255,.7); overflow: hidden;
}
#driftBar { width: 0; height: 100%; background: #9aa7b8; }
#minimap {
  right: 24px; top: 110px; width: 180px; height: 180px; border-radius: 18px;
  background: rgba(10,16,40,.45); border: 2px solid rgba(255,255,255,.35);
}
#wrongway {
  left: 50%; top: 34%; transform: translateX(-50%); font-size: 46px; color: #ff4d4d;
  animation: blink .5s steps(2) infinite;
}
@keyframes blink { 50% { opacity: .2; } }

#center {
  position: fixed; left: 0; right: 0; top: 30%; text-align: center; pointer-events: none;
  font-size: 150px; font-weight: 900; font-style: italic; color: #fff;
  -webkit-text-stroke: 4px #1b2a66; text-shadow: 0 8px 0 rgba(0,0,0,.35);
}
#center.pop { animation: pop .45s ease-out; }
@keyframes pop { from { transform: scale(1.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }

#banner {
  position: fixed; left: 0; right: 0; top: 20%; text-align: center; pointer-events: none;
  font-size: 58px; font-weight: 900; font-style: italic; color: #ffe45e;
  -webkit-text-stroke: 2px #5a2a00; text-shadow: 0 5px 0 rgba(0,0,0,.4);
  opacity: 0; transform: translateX(-60px); transition: opacity .25s, transform .25s;
}
#banner.show { opacity: 1; transform: none; }

/* ---------- overlays ---------- */
.overlay {
  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  background: radial-gradient(ellipse at center, rgba(8,14,40,.35), rgba(8,14,40,.8));
  backdrop-filter: blur(3px);
}
.panel {
  width: min(760px, 94vw); max-height: 96vh; overflow: auto; padding: 26px 34px 22px; text-align: center;
  border-radius: 28px; border: 2px solid rgba(255,255,255,.25);
  background: linear-gradient(170deg, rgba(36,52,128,.92), rgba(18,22,60,.94));
  box-shadow: 0 30px 80px rgba(0,0,0,.55), inset 0 0 60px rgba(90,150,255,.18);
}
.panel.small { width: min(460px, 94vw); }
h1 {
  margin: 0 0 8px; font-size: 54px; font-style: italic; font-weight: 900; letter-spacing: 1px; line-height: 1;
  background: linear-gradient(#fff, #ffe45e 55%, #ff8a1f); -webkit-background-clip: text; background-clip: text;
  color: transparent; filter: drop-shadow(0 4px 0 rgba(0,0,0,.35));
}
h1 span { display: block; font-size: 24px; letter-spacing: 9px; margin-top: 6px; }
h2 { margin: 18px 0 8px; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; opacity: .75; }
#racers { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.racer {
  padding: 10px 6px; border-radius: 16px; cursor: pointer; border: 3px solid transparent;
  background: rgba(255,255,255,.08); transition: transform .12s, background .12s;
}
.racer:hover { transform: translateY(-3px); background: rgba(255,255,255,.16); }
.racer.sel { border-color: #ffe45e; background: rgba(255,228,94,.18); }
.racer i {
  display: block; width: 46px; height: 46px; margin: 0 auto 6px; border-radius: 50%;
  border: 4px solid #fff; box-shadow: inset -6px -8px 0 rgba(0,0,0,.22);
}
.racer b { display: block; font-size: 16px; }
.racer small { font-size: 11px; opacity: .7; }
#classes { display: flex; gap: 10px; justify-content: center; }
button {
  font: inherit; font-weight: 800; color: #fff; cursor: pointer; padding: 9px 20px; border-radius: 14px;
  border: 2px solid rgba(255,255,255,.3); background: rgba(255,255,255,.1);
}
button:hover { background: rgba(255,255,255,.2); }
button.sel { border-color: #ffe45e; background: rgba(255,228,94,.2); }
button.big {
  display: block; margin: 20px auto 10px; padding: 14px 44px; font-size: 24px; font-style: italic;
  border: 0; border-radius: 18px; color: #3a1b00;
  background: linear-gradient(#fff36b, #ff9a2f); box-shadow: 0 7px 0 #b3560a, 0 14px 28px rgba(0,0,0,.4);
}
button.big:hover { filter: brightness(1.08); background: linear-gradient(#fff36b, #ff9a2f); }
button.big:active { transform: translateY(4px); box-shadow: 0 3px 0 #b3560a; }
.help { font-size: 13px; opacity: .8; margin: 8px 0 0; line-height: 1.5; }
#resultsList { list-style: none; padding: 0; margin: 12px 0; text-align: left; }
#resultsList li {
  display: flex; align-items: center; gap: 10px; padding: 7px 12px; margin: 4px 0;
  border-radius: 10px; background: rgba(255,255,255,.08); font-weight: 700;
}
#resultsList li.me { background: rgba(255,228,94,.25); outline: 2px solid #ffe45e; }
#resultsList li i { width: 16px; height: 16px; border-radius: 50%; border: 2px solid #fff; }
#resultsList li span:last-child { margin-left: auto; font-variant-numeric: tabular-nums; opacity: .9; }
#resultsList li em { width: 28px; font-style: italic; opacity: .8; }
#loadError {
  position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%); max-width: 90vw;
  padding: 12px 18px; border-radius: 12px; background: #b3261e; font-size: 14px; z-index: 10;
}
@media (max-width: 720px) {
  #pos { font-size: 80px; } #speed { font-size: 44px; } #minimap { display: none; }
  #racers { grid-template-columns: repeat(2, 1fr); } h1 { font-size: 38px; }
}
```

### `src/config.js`

```js
export const CFG = {
  laps: 3,
  samples: 600,      // spline samples around the circuit
  roadHalf: 11,      // half road width (world units)
  wallDist: 20,      // lateral distance of the barrier from the centre line
  kartRadius: 1.15,
};

export const CLASSES = {
  relaxed: { label: 'Relaxed', speed: 48, ai: 0.93 },
  swift:   { label: 'Swift',   speed: 58, ai: 0.96 },
  blazing: { label: 'Blazing', speed: 68, ai: 0.99 },
};

// Original cast: a crew of toy-like critters and bots.
export const RACERS = [
  { name: 'Pip',    tag: 'Fox kit',     color: 0xff5a3c, accent: 0xffe066, skin: 0xffc48a, trait: 'ears' },
  { name: 'Bolt',   tag: 'Scrap bot',   color: 0x2f7bff, accent: 0xd9e4f5, skin: 0xb8c4d6, trait: 'antenna' },
  { name: 'Juno',   tag: 'Moon moth',   color: 0x9b5cff, accent: 0xffd1f7, skin: 0xe9dcff, trait: 'feelers' },
  { name: 'Moss',   tag: 'Bog frog',    color: 0x2fbf62, accent: 0xf4ff8a, skin: 0x8fe08a, trait: 'eyes' },
  { name: 'Ember',  tag: 'Lava newt',   color: 0xff2e63, accent: 0xff9f1c, skin: 0xffa27a, trait: 'fin' },
  { name: 'Quill',  tag: 'Ink owl',     color: 0x1fc8c8, accent: 0x12355b, skin: 0xd8f3f0, trait: 'tufts' },
  { name: 'Dune',   tag: 'Sand ram',    color: 0xe0a030, accent: 0x6b3f12, skin: 0xf2d9a6, trait: 'horns' },
  { name: 'Nova',   tag: 'Star sprite', color: 0xf5f5ff, accent: 0xff4fd8, skin: 0xfff1b8, trait: 'star' },
];

export const ITEMS = {
  boost:  { label: 'COMET BOOST',   icon: '🚀' },
  slick:  { label: 'GOO PUDDLE',    icon: '🫧' },
  bolt:   { label: 'ZAP BOLT',      icon: '⚡' },
  shield: { label: 'BUBBLE SHIELD', icon: '🛡️' },
};
export const ITEM_KEYS = Object.keys(ITEMS);

export const ITEM_BOX_ROWS = [60, 200, 330, 470, 560];
export const ITEM_BOX_LANES = [-6, -2, 2, 6];
export const BOOST_PADS = [[95, 0], [255, -4], [405, 5], [520, 0]];
```

### `src/particles.js`

```js
import * as THREE from 'three';

export class Particles {
  constructor(scene, max = 900) {
    this.max = max;
    this.cursor = 0;
    this.pos = new Float32Array(max * 3);
    this.col = new Float32Array(max * 3);
    this.base = new Float32Array(max * 3);
    this.vel = new Float32Array(max * 3);
    this.life = new Float32Array(max);
    this.maxLife = new Float32Array(max);
    this.grav = new Float32Array(max);
    for (let i = 0; i < max; i++) this.pos[i * 3 + 1] = -999;

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(this.col, 3));
    this.geo = geo;

    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d');
    const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grd.addColorStop(0, 'rgba(255,255,255,1)');
    grd.addColorStop(0.35, 'rgba(255,255,255,.7)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, 64, 64);
    const tex = new THREE.CanvasTexture(c);

    const mat = new THREE.PointsMaterial({
      size: 1.1, map: tex, vertexColors: true, transparent: true,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
    });
    this.points = new THREE.Points(geo, mat);
    this.points.frustumCulled = false;
    scene.add(this.points);
  }

  emit(x, y, z, vx, vy, vz, life, r, g, b, grav = 0) {
    const i = this.cursor;
    this.cursor = (i + 1) % this.max;
    const j = i * 3;
    this.pos[j] = x; this.pos[j + 1] = y; this.pos[j + 2] = z;
    this.vel[j] = vx; this.vel[j + 1] = vy; this.vel[j + 2] = vz;
    this.base[j] = r; this.base[j + 1] = g; this.base[j + 2] = b;
    this.col[j] = r; this.col[j + 1] = g; this.col[j + 2] = b;
    this.life[i] = life; this.maxLife[i] = life; this.grav[i] = grav;
  }

  update(dt) {
    const { pos, vel, col, base, life, maxLife, grav } = this;
    for (let i = 0; i < this.max; i++) {
      if (life[i] <= 0) continue;
      const j = i * 3;
      life[i] -= dt;
      if (life[i] <= 0) { pos[j + 1] = -999; continue; }
      vel[j + 1] -= grav[i] * dt;
      pos[j] += vel[j] * dt;
      pos[j + 1] += vel[j + 1] * dt;
      pos[j + 2] += vel[j + 2] * dt;
      if (pos[j + 1] < 0.05) { pos[j + 1] = 0.05; vel[j + 1] *= -0.4; }
      const f = life[i] / maxLife[i];
      col[j] = base[j] * f; col[j + 1] = base[j + 1] * f; col[j + 2] = base[j + 2] * f;
    }
    this.geo.attributes.position.needsUpdate = true;
    this.geo.attributes.color.needsUpdate = true;
  }
}
```

### `src/audio.js`

```js
const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);

// Original four-bar loop: A minor, F, C, G.
const CHORDS = [
  { root: 45, third: 3 },
  { root: 41, third: 4 },
  { root: 48, third: 4 },
  { root: 43, third: 4 },
];
const ARP_ORDER = [0, 1, 2, 3, 2, 1, 2, 3];

export class GameAudio {
  constructor() {
    this.ctx = null;
    this.muted = false;
    this.musicOn = false;
    this.step = 0;
    this.nextTime = 0;
  }

  init() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC());
    this.master = ctx.createGain();
    this.master.gain.value = 0.6;
    this.master.connect(ctx.destination);
    this.musicGain = ctx.createGain();
    this.musicGain.gain.value = 0.55;
    this.musicGain.connect(this.master);

    this.engFilter = ctx.createBiquadFilter();
    this.engFilter.type = 'lowpass';
    this.engFilter.frequency.value = 500;
    this.engGain = ctx.createGain();
    this.engGain.gain.value = 0;
    this.engOsc = ctx.createOscillator();
    this.engOsc.type = 'sawtooth';
    this.engOsc.frequency.value = 60;
    this.engOsc2 = ctx.createOscillator();
    this.engOsc2.type = 'square';
    this.engOsc2.frequency.value = 30;
    this.engOsc.connect(this.engFilter);
    this.engOsc2.connect(this.engFilter);
    this.engFilter.connect(this.engGain);
    this.engGain.connect(this.master);
    this.engOsc.start();
    this.engOsc2.start();

    const len = ctx.sampleRate;
    this.noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  }

  toggleMute() {
    this.muted = !this.muted;
    if (this.ctx) this.master.gain.value = this.muted ? 0 : 0.6;
  }

  setEngine(ratio, on) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    const r = Math.max(0, Math.min(1.5, ratio));
    const f = 55 + r * 135;
    this.engOsc.frequency.setTargetAtTime(f, t, 0.05);
    this.engOsc2.frequency.setTargetAtTime(f * 0.5, t, 0.05);
    this.engFilter.frequency.setTargetAtTime(350 + r * 900, t, 0.05);
    this.engGain.gain.setTargetAtTime(on ? 0.05 + 0.035 * r : 0, t, 0.08);
  }

  toneAt(t, freq, dur, type = 'square', vol = 0.15, slide = 0, dest = null) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g);
    g.connect(dest || this.master);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  tone(freq, dur, type = 'square', vol = 0.15, slide = 0, delay = 0) {
    if (!this.ctx) return;
    this.toneAt(this.ctx.currentTime + delay, freq, dur, type, vol, slide);
  }

  noiseAt(t, dur, vol, cutoff, dest = null) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    const f = ctx.createBiquadFilter();
    f.type = 'highpass';
    f.frequency.value = cutoff;
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f);
    f.connect(g);
    g.connect(dest || this.master);
    src.start(t);
    src.stop(t + dur + 0.05);
  }

  sfx(name) {
    if (!this.ctx) return;
    const now = this.ctx.currentTime;
    switch (name) {
      case 'count': this.tone(440, 0.18, 'square', 0.16); break;
      case 'go': this.tone(880, 0.5, 'square', 0.18); break;
      case 'hop': this.tone(260, 0.1, 'triangle', 0.15, 520); break;
      case 'pickup':
        [660, 880, 1100, 1320].forEach((f, i) => this.tone(f, 0.09, 'square', 0.1, 0, i * 0.06));
        break;
      case 'itemReady': this.tone(1320, 0.2, 'triangle', 0.16); break;
      case 'boost':
        this.tone(180, 0.55, 'sawtooth', 0.14, 900);
        this.noiseAt(now, 0.4, 0.12, 1500);
        break;
      case 'mini': this.tone(500, 0.25, 'sawtooth', 0.11, 1300); break;
      case 'hit':
        this.tone(600, 0.5, 'sawtooth', 0.16, 70);
        this.noiseAt(now, 0.25, 0.15, 800);
        break;
      case 'block': this.tone(900, 0.2, 'sine', 0.2, 1500); break;
      case 'drop': this.tone(300, 0.18, 'sine', 0.18, 110); break;
      case 'zap': this.tone(1500, 0.3, 'square', 0.1, 300); break;
      case 'shield': this.tone(400, 0.4, 'sine', 0.18, 1000); break;
      case 'bump': this.noiseAt(now, 0.08, 0.14, 300); break;
      case 'lap':
        [523, 659, 784].forEach((f, i) => this.tone(f, 0.14, 'square', 0.13, 0, i * 0.1));
        break;
      case 'final':
        [784, 784, 1047].forEach((f, i) => this.tone(f, 0.16, 'square', 0.14, 0, i * 0.14));
        break;
      case 'finish':
        [523, 659, 784, 1047, 784, 1047].forEach((f, i) => this.tone(f, 0.22, 'square', 0.14, 0, i * 0.15));
        break;
      default: break;
    }
  }

  startMusic() { this.musicOn = true; this.step = 0; this.nextTime = 0; }
  stopMusic() { this.musicOn = false; }

  tickMusic() {
    if (!this.ctx || !this.musicOn) return;
    const ctx = this.ctx;
    const stepDur = 60 / 132 / 4;
    if (this.nextTime < ctx.currentTime) this.nextTime = ctx.currentTime + 0.05;
    while (this.nextTime < ctx.currentTime + 0.15) {
      this.scheduleStep(this.step, this.nextTime, stepDur);
      this.step = (this.step + 1) % 64;
      this.nextTime += stepDur;
    }
  }

  scheduleStep(step, t, sd) {
    const bar = Math.floor(step / 16);
    const s = step % 16;
    const ch = CHORDS[bar];
    const dest = this.musicGain;
    if (s % 4 === 0 || s === 6 || s === 14) {
      this.toneAt(t, midi(ch.root), sd * 1.8, 'triangle', 0.24, 0, dest);
    }
    if (s % 2 === 0) {
      const tones = [12, 12 + ch.third, 19, 24];
      const n = ch.root + 12 + tones[ARP_ORDER[s / 2]];
      this.toneAt(t, midi(n), sd * 1.4, 'square', 0.04, 0, dest);
    }
    if (s % 8 === 0) this.toneAt(t, 150, 0.13, 'sine', 0.3, 45, dest);
    if (s % 8 === 4) this.noiseAt(t, 0.09, 0.09, 1800, dest);
    if (s % 4 === 2) this.noiseAt(t, 0.03, 0.04, 7000, dest);
  }
}
```

### `src/track.js`

```js
import * as THREE from 'three';
import { CFG } from './config.js';

// Control points (x, z) of the "Skyline Meadows" circuit.
const CONTROL = [
  [0, 0], [120, 0], [220, -20], [290, -90], [280, -180], [200, -230], [110, -200],
  [60, -130], [-20, -120], [-80, -180], [-90, -270], [-180, -310], [-270, -260],
  [-290, -160], [-250, -80], [-290, 0], [-250, 70], [-170, 90], [-110, 50], [-60, 10],
];

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function canvasTexture(w, h, draw, repeat = true) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  if (repeat) { tex.wrapS = THREE.RepeatWrapping; tex.wrapT = THREE.RepeatWrapping; }
  tex.anisotropy = 8;
  return tex;
}

export class Track {
  constructor(scene) {
    this.scene = scene;
    const n = (this.n = CFG.samples);
    const curve = new THREE.CatmullRomCurve3(
      CONTROL.map(([x, z]) => new THREE.Vector3(x, 0, z)), true, 'centripetal'
    );
    const sp = curve.getSpacedPoints(n);
    this.length = curve.getLength();
    this.segLen = this.length / n;
    this.px = new Float32Array(n); this.pz = new Float32Array(n);
    this.tx = new Float32Array(n); this.tz = new Float32Array(n);
    this.sx = new Float32Array(n); this.sz = new Float32Array(n);
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    for (let i = 0; i < n; i++) {
      this.px[i] = sp[i].x; this.pz[i] = sp[i].z;
      minX = Math.min(minX, sp[i].x); maxX = Math.max(maxX, sp[i].x);
      minZ = Math.min(minZ, sp[i].z); maxZ = Math.max(maxZ, sp[i].z);
    }
    for (let i = 0; i < n; i++) {
      const a = sp[(i + 1) % n], b = sp[(i - 1 + n) % n];
      let dx = a.x - b.x, dz = a.z - b.z;
      const l = Math.hypot(dx, dz) || 1;
      dx /= l; dz /= l;
      this.tx[i] = dx; this.tz[i] = dz;
      // "side" points to the left of the direction of travel
      this.sx[i] = dz; this.sz[i] = -dx;
    }
    this.bounds = { minX, maxX, minZ, maxZ };
    this.center = { x: (minX + maxX) / 2, z: (minZ + maxZ) / 2 };
    this.balloons = [];
    this.padTex = null;

    this.buildGround();
    this.buildRoad();
    this.buildStart();
    this.buildBarriers();
    this.buildScenery();
  }

  // ---------- queries ----------
  wrap(i) { const n = this.n; return ((i % n) + n) % n; }

  nearest(x, z, hint = -1) {
    const n = this.n, px = this.px, pz = this.pz;
    let best = 0, bd = Infinity;
    if (hint < 0) {
      for (let i = 0; i < n; i++) {
        const dx = x - px[i], dz = z - pz[i], d = dx * dx + dz * dz;
        if (d < bd) { bd = d; best = i; }
      }
    } else {
      for (let k = -14; k <= 26; k++) {
        const i = this.wrap(hint + k);
        const dx = x - px[i], dz = z - pz[i], d = dx * dx + dz * dz;
        if (d < bd) { bd = d; best = i; }
      }
    }
    return best;
  }

  lateral(x, z, i) {
    return (x - this.px[i]) * this.sx[i] + (z - this.pz[i]) * this.sz[i];
  }

  headingAt(i) { return Math.atan2(this.tx[i], this.tz[i]); }

  // Point at fractional sample position s with a lateral offset; writes into out {x,z}.
  pointAt(s, lat, out) {
    const n = this.n;
    const f = ((s % n) + n) % n;
    const i = Math.floor(f) % n, j = (i + 1) % n, t = f - Math.floor(f);
    out.x = this.px[i] + (this.px[j] - this.px[i]) * t + (this.sx[i] + (this.sx[j] - this.sx[i]) * t) * lat;
    out.z = this.pz[i] + (this.pz[j] - this.pz[i]) * t + (this.sz[i] + (this.sz[j] - this.sz[i]) * t) * lat;
    return out;
  }

  distToTrack(x, z) {
    let bd = Infinity;
    for (let i = 0; i < this.n; i += 3) {
      const dx = x - this.px[i], dz = z - this.pz[i], d = dx * dx + dz * dz;
      if (d < bd) bd = d;
    }
    return Math.sqrt(bd);
  }

  // ---------- geometry helpers ----------
  ribbon(latA, latB, y, vScale) {
    const n = this.n;
    const pos = [], uv = [], nor = [], idx = [];
    for (let i = 0; i <= n; i++) {
      const j = i % n;
      pos.push(this.px[j] + this.sx[j] * latA, y, this.pz[j] + this.sz[j] * latA);
      pos.push(this.px[j] + this.sx[j] * latB, y, this.pz[j] + this.sz[j] * latB);
      const v = (i * this.segLen) / vScale;
      uv.push(0, v, 1, v);
      nor.push(0, 1, 0, 0, 1, 0);
    }
    const tri = (a, b, c) => {
      const ax = pos[a * 3], az = pos[a * 3 + 2];
      const ux = pos[b * 3] - ax, uz = pos[b * 3 + 2] - az;
      const vx = pos[c * 3] - ax, vz = pos[c * 3 + 2] - az;
      // y component of (u × v); make every triangle face upward
      if (uz * vx - ux * vz >= 0) idx.push(a, b, c); else idx.push(a, c, b);
    };
    for (let i = 0; i < n; i++) {
      const a = i * 2, b = a + 1, c = a + 2, d = a + 3;
      tri(a, b, c);
      tri(b, d, c);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    return g;
  }

  // Group positioned at sample i, local +z along the track, local +x to the left.
  frameAt(i, lat = 0) {
    const g = new THREE.Group();
    g.position.set(this.px[i] + this.sx[i] * lat, 0, this.pz[i] + this.sz[i] * lat);
    g.rotation.y = this.headingAt(i);
    return g;
  }

  // ---------- construction ----------
  buildGround() {
    const tex = canvasTexture(256, 256, (g, w, h) => {
      g.fillStyle = '#5fb04a'; g.fillRect(0, 0, w, h);
      const rnd = mulberry32(7);
      for (let i = 0; i < 2600; i++) {
        const v = rnd();
        g.fillStyle = v < 0.5 ? 'rgba(40,120,40,.35)' : 'rgba(150,220,90,.3)';
        g.fillRect(rnd() * w, rnd() * h, 2 + rnd() * 3, 2 + rnd() * 3);
      }
    });
    tex.repeat.set(260, 260);
    const geo = new THREE.PlaneGeometry(6000, 6000);
    geo.rotateX(-Math.PI / 2);
    const mesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ map: tex }));
    mesh.position.set(this.center.x, 0, this.center.z);
    mesh.receiveShadow = true;
    this.scene.add(mesh);
  }

  buildRoad() {
    const hw = CFG.roadHalf;
    const roadTex = canvasTexture(256, 256, (g, w, h) => {
      g.fillStyle = '#3b3f4a'; g.fillRect(0, 0, w, h);
      const rnd = mulberry32(11);
      for (let i = 0; i < 3500; i++) {
        g.fillStyle = rnd() < 0.5 ? 'rgba(255,255,255,.05)' : 'rgba(0,0,0,.09)';
        g.fillRect(rnd() * w, rnd() * h, 2, 2);
      }
      g.fillStyle = '#f2f2f2';
      g.fillRect(5, 0, 6, h); g.fillRect(w - 11, 0, 6, h);
      g.fillStyle = '#ffd84a';
      g.fillRect(w / 2 - 3, 0, 6, h / 2);
    });
    const mk = (geo, mat, off) => {
      mat.polygonOffset = true; mat.polygonOffsetFactor = off; mat.polygonOffsetUnits = off;
      const m = new THREE.Mesh(geo, mat);
      m.receiveShadow = true;
      this.scene.add(m);
      return m;
    };
    // dirt shoulder under everything
    mk(this.ribbon(hw + 5.5, -hw - 5.5, 0.03, 20), new THREE.MeshLambertMaterial({ color: 0x8a7a55 }), -1);
    mk(this.ribbon(hw, -hw, 0.06, 16),
      new THREE.MeshStandardMaterial({ map: roadTex, roughness: 0.85, metalness: 0 }), -2);

    const curbTex = canvasTexture(32, 64, (g, w, h) => {
      g.fillStyle = '#ffffff'; g.fillRect(0, 0, w, h);
      g.fillStyle = '#14b8a6'; g.fillRect(0, 0, w, h / 2);
    });
    const curbMat = () => new THREE.MeshLambertMaterial({ map: curbTex });
    mk(this.ribbon(hw + 1.6, hw, 0.09, 6), curbMat(), -3);
    mk(this.ribbon(-hw, -hw - 1.6, 0.09, 6), curbMat(), -3);
  }

  buildStart() {
    const hw = CFG.roadHalf;
    const g = this.frameAt(0);
    const checker = canvasTexture(128, 16, (c, w, h) => {
      const s = 8;
      for (let y = 0; y < h / s; y++) for (let x = 0; x < w / s; x++) {
        c.fillStyle = (x + y) % 2 ? '#111' : '#fff';
        c.fillRect(x * s, y * s, s, s);
      }
    }, false);
    checker.magFilter = THREE.NearestFilter;
    const lineGeo = new THREE.PlaneGeometry(hw * 2, 2.8);
    lineGeo.rotateX(-Math.PI / 2);
    const lineMat = new THREE.MeshLambertMaterial({ map: checker });
    lineMat.polygonOffset = true; lineMat.polygonOffsetFactor = -4; lineMat.polygonOffsetUnits = -4;
    const line = new THREE.Mesh(lineGeo, lineMat);
    line.position.y = 0.1;
    line.receiveShadow = true;
    g.add(line);

    const postMat = new THREE.MeshStandardMaterial({ color: 0xf4f6ff, roughness: 0.4, metalness: 0.3 });
    const postGeo = new THREE.CylinderGeometry(0.7, 0.9, 11, 12);
    for (const s of [-1, 1]) {
      const p = new THREE.Mesh(postGeo, postMat);
      p.position.set(s * (hw + 3.2), 5.5, 0);
      p.castShadow = true;
      g.add(p);
      const cap = new THREE.Mesh(new THREE.SphereGeometry(1.2, 16, 12),
        new THREE.MeshStandardMaterial({ color: 0xff8a1f, emissive: 0xff5a00, emissiveIntensity: 0.5 }));
      cap.position.set(s * (hw + 3.2), 11.4, 0);
      g.add(cap);
    }
    const bannerTex = canvasTexture(1024, 128, (c, w, h) => {
      const grd = c.createLinearGradient(0, 0, w, 0);
      grd.addColorStop(0, '#2f4bff'); grd.addColorStop(0.5, '#9b5cff'); grd.addColorStop(1, '#ff4fd8');
      c.fillStyle = grd; c.fillRect(0, 0, w, h);
      c.fillStyle = '#fff';
      c.font = 'italic 900 84px "Trebuchet MS", sans-serif';
      c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillText('TURBO TUMBLE GRAND PRIX', w / 2, h / 2 + 4);
    }, false);
    const banner = new THREE.Mesh(
      new THREE.BoxGeometry(hw * 2 + 7.5, 2.8, 0.6),
      new THREE.MeshLambertMaterial({ map: bannerTex })
    );
    banner.position.set(0, 9.3, 0);
    banner.castShadow = true;
    g.add(banner);
    this.scene.add(g);
  }

  buildBarriers() {
    const n = this.n, step = 3;
    const count = Math.floor(n / step) * 2;
    const geo = new THREE.CylinderGeometry(0.55, 0.65, 1.7, 8);
    geo.translate(0, 0.85, 0);
    const mesh = new THREE.InstancedMesh(geo, new THREE.MeshLambertMaterial({ color: 0xffffff }), count);
    const dummy = new THREE.Object3D();
    const ca = new THREE.Color(0xffffff), cb = new THREE.Color(0xff7a2f);
    let k = 0;
    for (let i = 0; i + step <= n; i += step) {
      for (const s of [-1, 1]) {
        const lat = s * (CFG.wallDist + 1.4);
        dummy.position.set(this.px[i] + this.sx[i] * lat, 0, this.pz[i] + this.sz[i] * lat);
        dummy.updateMatrix();
        mesh.setMatrixAt(k, dummy.matrix);
        mesh.setColorAt(k, (i / step) % 2 ? ca : cb);
        k++;
      }
    }
    mesh.count = k;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.castShadow = true;
    this.scene.add(mesh);
  }

  buildScenery() {
    const rnd = mulberry32(2024);
    const b = this.bounds;
    const dummy = new THREE.Object3D();

    // ---- forest ----
    const spots = [];
    for (let tries = 0; tries < 2600 && spots.length < 520; tries++) {
      const x = b.minX - 220 + rnd() * (b.maxX - b.minX + 440);
      const z = b.minZ - 220 + rnd() * (b.maxZ - b.minZ + 440);
      if (this.distToTrack(x, z) < CFG.wallDist + 9) continue;
      spots.push([x, z, 0.7 + rnd() * 0.9, rnd() * Math.PI * 2, rnd()]);
    }
    const trunkGeo = new THREE.CylinderGeometry(0.5, 0.75, 3.2, 6);
    trunkGeo.translate(0, 1.6, 0);
    const leafGeo = new THREE.ConeGeometry(3.1, 7.5, 7);
    leafGeo.translate(0, 6.6, 0);
    const leaf2Geo = new THREE.ConeGeometry(2.2, 5, 7);
    leaf2Geo.translate(0, 10, 0);
    const trunks = new THREE.InstancedMesh(trunkGeo, new THREE.MeshLambertMaterial({ color: 0x7a5230 }), spots.length);
    const leaves = new THREE.InstancedMesh(leafGeo, new THREE.MeshLambertMaterial({ color: 0xffffff }), spots.length);
    const leaves2 = new THREE.InstancedMesh(leaf2Geo, new THREE.MeshLambertMaterial({ color: 0xffffff }), spots.length);
    const col = new THREE.Color();
    spots.forEach(([x, z, s, r, h], i) => {
      dummy.position.set(x, 0, z);
      dummy.rotation.set(0, r, 0);
      dummy.scale.setScalar(s);
      dummy.updateMatrix();
      trunks.setMatrixAt(i, dummy.matrix);
      leaves.setMatrixAt(i, dummy.matrix);
      leaves2.setMatrixAt(i, dummy.matrix);
      col.setHSL(0.27 + h * 0.1, 0.55, 0.3 + h * 0.12);
      leaves.setColorAt(i, col);
      col.offsetHSL(0, 0, 0.06);
      leaves2.setColorAt(i, col);
    });
    for (const m of [trunks, leaves, leaves2]) {
      m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
      m.castShadow = true;
      this.scene.add(m);
    }

    // ---- mountains ----
    const mMat = new THREE.MeshLambertMaterial({ color: 0x7f8fd0, flatShading: true });
    const snowMat = new THREE.MeshLambertMaterial({ color: 0xf5f8ff, flatShading: true });
    for (let i = 0; i < 18; i++) {
      const a = (i / 18) * Math.PI * 2 + rnd() * 0.2;
      const r = 820 + rnd() * 240;
      const h = 190 + rnd() * 220, rad = 170 + rnd() * 130;
      const m = new THREE.Mesh(new THREE.ConeGeometry(rad, h, 7), mMat);
      m.position.set(this.center.x + Math.cos(a) * r, h / 2 - 4, this.center.z + Math.sin(a) * r);
      m.rotation.y = rnd() * 6;
      this.scene.add(m);
      const cap = new THREE.Mesh(new THREE.ConeGeometry(rad * 0.3, h * 0.3, 7), snowMat);
      cap.position.set(m.position.x, h * 0.85 - 3, m.position.z);
      cap.rotation.y = m.rotation.y;
      this.scene.add(cap);
    }

    // ---- clouds ----
    const cloudMat = new THREE.MeshLambertMaterial({ color: 0xffffff, emissive: 0x9fb4d8, emissiveIntensity: 0.35, fog: false });
    const cloudGeo = new THREE.SphereGeometry(1, 10, 8);
    for (let i = 0; i < 26; i++) {
      const grp = new THREE.Group();
      const puffs = 3 + Math.floor(rnd() * 3);
      for (let p = 0; p < puffs; p++) {
        const s = new THREE.Mesh(cloudGeo, cloudMat);
        const sc = 18 + rnd() * 20;
        s.scale.set(sc * 1.5, sc * 0.55, sc);
        s.position.set((p - puffs / 2) * 24 + rnd() * 8, rnd() * 6, rnd() * 14);
        grp.add(s);
      }
      const a = rnd() * Math.PI * 2, r = 150 + rnd() * 750;
      grp.position.set(this.center.x + Math.cos(a) * r, 190 + rnd() * 110, this.center.z + Math.sin(a) * r);
      grp.rotation.y = rnd() * 6;
      this.scene.add(grp);
    }

    // ---- hot-air balloons ----
    const colors = [0xff5a3c, 0xffd23f, 0x2f7bff, 0x9b5cff, 0x2fbf62, 0xff4fd8, 0x1fc8c8];
    for (let i = 0; i < 7; i++) {
      const grp = new THREE.Group();
      const env = new THREE.Mesh(new THREE.SphereGeometry(9, 16, 14),
        new THREE.MeshLambertMaterial({ color: colors[i % colors.length] }));
      env.scale.y = 1.2;
      const band = new THREE.Mesh(new THREE.TorusGeometry(8.6, 0.8, 8, 24),
        new THREE.MeshLambertMaterial({ color: 0xffffff }));
      band.rotation.x = Math.PI / 2;
      const basket = new THREE.Mesh(new THREE.BoxGeometry(3, 2.4, 3),
        new THREE.MeshLambertMaterial({ color: 0x7a5230 }));
      basket.position.y = -14;
      grp.add(env, band, basket);
      const a = (i / 7) * Math.PI * 2 + 0.4, r = 110 + rnd() * 240;
      const baseY = 55 + rnd() * 45;
      grp.position.set(this.center.x + Math.cos(a) * r, baseY, this.center.z + Math.sin(a) * r);
      this.scene.add(grp);
      this.balloons.push({ grp, baseY, phase: rnd() * 6 });
    }
  }

  update(t) {
    for (const b of this.balloons) {
      b.grp.position.y = b.baseY + Math.sin(t * 0.4 + b.phase) * 4;
      b.grp.rotation.y = t * 0.05 + b.phase;
    }
    if (this.padTex) this.padTex.offset.y = -(t * 1.6) % 1;
  }
}
```

### `src/kart.js`

```js
import * as THREE from 'three';
import { CFG } from './config.js';

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export function wrapAngle(a) {
  const t = Math.PI * 2;
  return ((((a + Math.PI) % t) + t) % t) - Math.PI;
}

const SPIN_DUR = 1.3;
const MINI_TURBO = [0, 0.6, 1.1, 1.8];

function buildKartMesh(racer) {
  const group = new THREE.Group();
  const inner = new THREE.Group();
  group.add(inner);

  const paint = new THREE.MeshStandardMaterial({ color: racer.color, roughness: 0.35, metalness: 0.25 });
  const accent = new THREE.MeshStandardMaterial({ color: racer.accent, roughness: 0.4, metalness: 0.2 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x22252e, roughness: 0.7, metalness: 0.3 });
  const tyre = new THREE.MeshStandardMaterial({ color: 0x15161a, roughness: 0.95 });
  const skin = new THREE.MeshStandardMaterial({ color: racer.skin, roughness: 0.7 });
  const black = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.3 });

  const add = (geo, mat, x, y, z, parent = inner) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    parent.add(m);
    return m;
  };

  // chassis
  add(new THREE.BoxGeometry(1.8, 0.45, 3.0), paint, 0, 0.55, 0);
  add(new THREE.BoxGeometry(1.25, 0.36, 0.9), paint, 0, 0.52, 1.75);
  const bumper = add(new THREE.CylinderGeometry(0.2, 0.2, 2.0, 10), accent, 0, 0.42, 2.2);
  bumper.rotation.z = Math.PI / 2;
  add(new THREE.BoxGeometry(0.36, 0.34, 1.7), accent, 1.0, 0.52, -0.05);
  add(new THREE.BoxGeometry(0.36, 0.34, 1.7), accent, -1.0, 0.52, -0.05);
  add(new THREE.BoxGeometry(1.4, 0.06, 0.9), accent, 0, 0.79, 0.9);
  // seat + engine
  add(new THREE.BoxGeometry(1.05, 0.95, 0.24), dark, 0, 1.1, -0.95);
  add(new THREE.BoxGeometry(1.15, 0.5, 0.7), dark, 0, 0.98, -1.4);
  for (const s of [-1, 1]) {
    const ex = add(new THREE.CylinderGeometry(0.13, 0.16, 0.7, 8), accent, s * 0.36, 0.98, -1.95);
    ex.rotation.x = Math.PI / 2;
    add(new THREE.BoxGeometry(0.1, 0.55, 0.1), dark, s * 0.75, 1.3, -1.65);
  }
  add(new THREE.BoxGeometry(2.1, 0.09, 0.55), accent, 0, 1.6, -1.7);
  // steering wheel
  const sw = add(new THREE.TorusGeometry(0.22, 0.05, 6, 14), dark, 0, 1.08, 0.4);
  sw.rotation.x = -0.5;
  add(new THREE.CylinderGeometry(0.04, 0.04, 0.5, 6), dark, 0, 0.88, 0.5).rotation.x = -0.5;

  // wheels
  const wheelGeo = new THREE.CylinderGeometry(0.46, 0.46, 0.42, 16);
  const hubGeo = new THREE.BoxGeometry(0.46, 0.14, 0.62);
  const wheels = [];
  const steerPivots = [];
  for (const [x, z, front] of [[1.08, 1.12, true], [-1.08, 1.12, true], [1.1, -1.12, false], [-1.1, -1.12, false]]) {
    const steer = new THREE.Group();
    steer.position.set(x, 0.46, z);
    const spin = new THREE.Group();
    steer.add(spin);
    const w = new THREE.Mesh(wheelGeo, tyre);
    w.rotation.z = Math.PI / 2;
    spin.add(w);
    spin.add(new THREE.Mesh(hubGeo, accent));
    inner.add(steer);
    wheels.push(spin);
    if (front) steerPivots.push(steer);
  }

  // driver
  const torso = add(new THREE.SphereGeometry(0.44, 14, 12), paint, 0, 1.2, -0.45);
  torso.scale.y = 1.25;
  add(new THREE.SphereGeometry(0.42, 16, 14), skin, 0, 1.95, -0.42);
  const helmet = add(new THREE.SphereGeometry(0.46, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2), accent, 0, 1.98, -0.44);
  helmet.rotation.x = -0.25;
  add(new THREE.SphereGeometry(0.07, 8, 8), black, 0.16, 1.95, -0.04);
  add(new THREE.SphereGeometry(0.07, 8, 8), black, -0.16, 1.95, -0.04);
  for (const s of [-1, 1]) {
    const arm = add(new THREE.CylinderGeometry(0.09, 0.09, 0.75, 6), paint, s * 0.34, 1.22, 0.0);
    arm.rotation.x = 1.15;
  }
  // trait: each driver gets a distinct silhouette
  const hy = 2.38, hz = -0.44;
  switch (racer.trait) {
    case 'ears':
      for (const s of [-1, 1]) add(new THREE.ConeGeometry(0.16, 0.42, 6), paint, s * 0.26, hy + 0.1, hz).rotation.z = -s * 0.3;
      break;
    case 'antenna':
      add(new THREE.CylinderGeometry(0.03, 0.03, 0.55, 6), dark, 0, hy + 0.2, hz);
      add(new THREE.SphereGeometry(0.1, 8, 8), new THREE.MeshStandardMaterial({ color: 0xff3b3b, emissive: 0xff0000, emissiveIntensity: 0.8 }), 0, hy + 0.5, hz);
      break;
    case 'feelers':
      for (const s of [-1, 1]) {
        add(new THREE.CylinderGeometry(0.025, 0.025, 0.6, 5), dark, s * 0.18, hy + 0.2, hz + 0.15).rotation.set(0.5, 0, -s * 0.4);
        add(new THREE.SphereGeometry(0.07, 8, 8), accent, s * 0.3, hy + 0.45, hz + 0.3);
      }
      break;
    case 'eyes':
      for (const s of [-1, 1]) {
        add(new THREE.SphereGeometry(0.17, 10, 10), skin, s * 0.24, hy + 0.02, hz + 0.1);
        add(new THREE.SphereGeometry(0.08, 8, 8), black, s * 0.24, hy + 0.05, hz + 0.24);
      }
      break;
    case 'fin':
      add(new THREE.BoxGeometry(0.07, 0.4, 0.75), paint, 0, hy + 0.12, hz - 0.05).rotation.x = -0.3;
      break;
    case 'tufts':
      for (const s of [-1, 1]) add(new THREE.ConeGeometry(0.1, 0.5, 5), dark, s * 0.32, hy + 0.08, hz - 0.05).rotation.z = -s * 0.7;
      break;
    case 'horns':
      for (const s of [-1, 1]) add(new THREE.TorusGeometry(0.2, 0.07, 6, 10, Math.PI * 1.2), accent, s * 0.42, hy - 0.2, hz).rotation.y = Math.PI / 2;
      break;
    default: {
      const star = add(new THREE.OctahedronGeometry(0.2), new THREE.MeshStandardMaterial({ color: 0xffe45e, emissive: 0xffc400, emissiveIntensity: 0.9 }), 0, hy + 0.3, hz);
      star.scale.y = 1.4;
    }
  }

  inner.traverse((o) => { if (o.isMesh) o.castShadow = true; });

  const shield = new THREE.Mesh(
    new THREE.SphereGeometry(2.5, 20, 16),
    new THREE.MeshStandardMaterial({
      color: 0x7fe8ff, emissive: 0x2aa8ff, emissiveIntensity: 0.6, transparent: true,
      opacity: 0.28, roughness: 0.1, depthWrite: false,
    })
  );
  shield.position.y = 1.1;
  shield.visible = false;
  group.add(shield);

  return { group, inner, wheels, steerPivots, shield };
}

export class Kart {
  constructor(racer, isPlayer, track, scene) {
    this.racer = racer;
    this.isPlayer = isPlayer;
    this.track = track;
    this.scene = scene;
    const m = buildKartMesh(racer);
    this.group = m.group; this.inner = m.inner; this.wheels = m.wheels;
    this.steerPivots = m.steerPivots; this.shield = m.shield;
    scene.add(this.group);

    this.x = 0; this.z = 0; this.heading = 0; this.speed = 0;
    this.idx = 0; this.progress = 0; this.lat = 0; this.offroad = false;
    this.boostTime = 0; this.spinTime = 0; this.shieldTime = 0;
    this.driftDir = 0; this.driftCharge = 0; this.driftHeld = false;
    this.hopY = 0; this.hopV = 0;
    this.steerVis = 0; this.yawVis = 0; this.wheelRot = 0;
    this.item = null; this.pendingItem = null; this.itemRoll = 0; this.itemTimer = 0;
    this.finished = false; this.finishTime = 0; this.rank = 1;
    this.maxLap = 0; this.lapStart = 0; this.bestLap = Infinity;
    this.skill = 1; this.lane = 0; this.phase = Math.random() * 6;
    this.evMini = 0; this.evHop = false; this.evWall = false;
    this.wallCooldown = 0;
  }

  place(i, lat) {
    const tr = this.track;
    const w = tr.wrap(i);
    this.idx = w;
    this.progress = i;
    this.x = tr.px[w] + tr.sx[w] * lat;
    this.z = tr.pz[w] + tr.sz[w] * lat;
    this.heading = tr.headingAt(w);
    this.lat = lat;
    this.speed = 0;
    this.sync(0);
  }

  driftLevel() {
    const c = this.driftCharge;
    return c >= 3.2 ? 3 : c >= 2.0 ? 2 : c >= 0.9 ? 1 : 0;
  }

  // Returns true if the kart was actually knocked into a spin.
  hit() {
    if (this.shieldTime > 0) { this.shieldTime = 0; return false; }
    if (this.spinTime > 0) return false;
    this.spinTime = SPIN_DUR;
    this.driftDir = 0; this.driftCharge = 0; this.boostTime = 0;
    return true;
  }

  update(dt, inp, topSpeed) {
    const tr = this.track, n = tr.n;
    this.boostTime = Math.max(0, this.boostTime - dt);
    this.shieldTime = Math.max(0, this.shieldTime - dt);
    this.wallCooldown = Math.max(0, this.wallCooldown - dt);

    let throttle = inp.throttle, steer = inp.steer, drift = inp.drift;
    if (this.spinTime > 0) {
      this.spinTime = Math.max(0, this.spinTime - dt);
      throttle = 0; steer = 0; drift = false;
      this.speed *= Math.exp(-2.4 * dt);
    }

    const boosting = this.boostTime > 0;
    let max = topSpeed;
    if (this.offroad && !boosting) max *= 0.5;
    if (boosting) max *= 1.3;

    // ---- longitudinal ----
    let v = this.speed;
    if (boosting && this.spinTime <= 0) throttle = 1;
    if (throttle > 0) {
      if (v < max) v = Math.min(max, v + (boosting ? 75 : 30) * throttle * dt * (1.2 - (0.8 * Math.max(0, v)) / max));
    } else if (throttle < 0) {
      if (v > 0.5) v = Math.max(0, v - 60 * dt);
      else v = Math.max(-topSpeed * 0.3, v - 22 * dt);
    } else {
      v -= Math.sign(v) * Math.min(Math.abs(v), 10 * dt);
    }
    if (v > max) v = Math.max(max, v - (this.offroad ? 70 : 22) * dt);
    this.speed = v;

    // ---- hop / drift ----
    const canDrift = v > topSpeed * 0.45 && this.spinTime <= 0;
    if (drift && !this.driftHeld && this.hopY <= 0.001 && this.spinTime <= 0) {
      this.hopV = 7;
      this.evHop = true;
      if (canDrift && Math.abs(steer) > 0.2) { this.driftDir = Math.sign(steer); this.driftCharge = 0; }
    }
    // steering into a held hop button after landing also starts a drift
    if (drift && this.driftDir === 0 && canDrift && Math.abs(steer) > 0.2 && this.hopY > 0.001) {
      this.driftDir = Math.sign(steer); this.driftCharge = 0;
    }
    if (this.driftDir !== 0 && (!drift || !canDrift)) {
      if (!drift && canDrift) {
        const lvl = this.driftLevel();
        if (lvl > 0) { this.boostTime = Math.max(this.boostTime, MINI_TURBO[lvl]); this.evMini = lvl; }
      }
      this.driftDir = 0; this.driftCharge = 0;
    }
    this.driftHeld = drift;

    // ---- steering ----
    let eff = steer, turn = 1.9;
    if (this.driftDir !== 0) {
      eff = this.driftDir * 0.6 + steer * 0.5;
      turn = 2.25;
      if (this.hopY <= 0.001) this.driftCharge += dt * (0.75 + 0.5 * Math.max(0, steer * this.driftDir));
    }
    const sf = clamp(Math.abs(v) / 14, 0, 1) * (v < 0 ? -1 : 1);
    const grip = 1 - 0.28 * clamp(v / (topSpeed * 1.3), 0, 1);
    this.heading += eff * turn * sf * grip * dt;

    // ---- integrate ----
    this.x += Math.sin(this.heading) * v * dt;
    this.z += Math.cos(this.heading) * v * dt;
    this.hopV -= 30 * dt;
    this.hopY += this.hopV * dt;
    if (this.hopY < 0) { this.hopY = 0; this.hopV = 0; }

    // ---- track relation ----
    const ni = tr.nearest(this.x, this.z, this.idx);
    let d = ni - this.idx;
    if (d > n / 2) d -= n;
    if (d < -n / 2) d += n;
    this.progress += d;
    this.idx = ni;
    let lat = tr.lateral(this.x, this.z, ni);
    if (Math.abs(lat) > CFG.wallDist) {
      const s = Math.sign(lat), over = Math.abs(lat) - CFG.wallDist;
      this.x -= tr.sx[ni] * over * s;
      this.z -= tr.sz[ni] * over * s;
      lat = s * CFG.wallDist;
      this.speed *= Math.exp(-2.5 * dt);
      const diff = wrapAngle(tr.headingAt(ni) - this.heading);
      if (Math.abs(diff) < Math.PI / 2) this.heading += diff * Math.min(1, 3 * dt);
      if (this.wallCooldown <= 0 && Math.abs(this.speed) > 12) { this.evWall = true; this.wallCooldown = 0.5; }
    }
    this.lat = lat;
    this.offroad = Math.abs(lat) > CFG.roadHalf + 1.4;

    this.steerVis += (steer - this.steerVis) * Math.min(1, 10 * dt);
    this.sync(dt);
  }

  sync(dt) {
    this.yawVis += (this.driftDir * 0.38 - this.yawVis) * Math.min(1, 8 * dt);
    const spin = this.spinTime > 0 ? (1 - this.spinTime / SPIN_DUR) * Math.PI * 4 : 0;
    this.group.position.set(this.x, this.hopY, this.z);
    this.group.rotation.y = this.heading + this.yawVis + spin;
    this.inner.rotation.z = -this.steerVis * 0.07 - this.driftDir * 0.06;
    this.inner.rotation.x = this.boostTime > 0 ? -0.05 : 0;
    this.wheelRot += (this.speed * dt) / 0.46;
    for (const w of this.wheels) w.rotation.x = this.wheelRot;
    for (const p of this.steerPivots) p.rotation.y = this.steerVis * 0.4;
    const sh = this.shieldTime > 0;
    this.shield.visible = sh;
    if (sh) {
      const blink = this.shieldTime < 2 ? 0.5 + 0.5 * Math.sin(this.shieldTime * 20) : 1;
      this.shield.material.opacity = 0.12 + 0.18 * blink;
      this.shield.rotation.y += dt * 2;
    }
  }

  dispose() {
    this.scene.remove(this.group);
    this.group.traverse((o) => {
      if (o.isMesh) { o.geometry.dispose(); if (o.material.dispose) o.material.dispose(); }
    });
  }
}
```

### `src/main.js`

```js
import * as THREE from 'three';
import { CFG, CLASSES, RACERS, ITEMS, ITEM_KEYS, ITEM_BOX_ROWS, ITEM_BOX_LANES, BOOST_PADS } from './config.js';
import { Track, canvasTexture } from './track.js';
import { Kart, clamp, wrapAngle } from './kart.js';
import { Particles } from './particles.js';
import { GameAudio } from './audio.js';

const $ = (id) => document.getElementById(id);
const SPARK = [[0.5, 0.5, 0.5], [0.3, 0.85, 1], [1, 0.6, 0.12], [1, 0.3, 0.95]];
const DRIFT_COLORS = ['#9aa7b8', '#4fd8ff', '#ff9a1f', '#ff4ff0'];
const hex = (n) => '#' + n.toString(16).padStart(6, '0');

function fmtTime(t) {
  const m = Math.floor(t / 60), s = t - m * 60;
  return m + ':' + (s < 10 ? '0' : '') + s.toFixed(3);
}
function ordinal(n) { return ['st', 'nd', 'rd'][n - 1] || 'th'; }

class Game {
  constructor() {
    // ---------- renderer / scene ----------
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    $('game').appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = canvasTexture(4, 512, (g, w, h) => {
      const grd = g.createLinearGradient(0, 0, 0, h);
      grd.addColorStop(0, '#2f6fe0'); grd.addColorStop(0.45, '#7fc0ff');
      grd.addColorStop(0.62, '#d9efff'); grd.addColorStop(1, '#ffe9c9');
      g.fillStyle = grd; g.fillRect(0, 0, w, h);
    }, false);
    this.scene.fog = new THREE.Fog(0xcfe6fa, 320, 1700);

    this.camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.4, 3500);
    this.camera.position.set(0, 120, 200);
    this.camYaw = 0;

    this.scene.add(new THREE.HemisphereLight(0xd8ecff, 0x55803f, 1.25));
    this.sun = new THREE.DirectionalLight(0xfff1d6, 2.6);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    const sc = this.sun.shadow.camera;
    sc.left = -75; sc.right = 75; sc.top = 75; sc.bottom = -75; sc.near = 1; sc.far = 320;
    this.sun.shadow.bias = -0.0006;
    this.sun.shadow.normalBias = 0.04;
    this.scene.add(this.sun);
    this.scene.add(this.sun.target);

    // ---------- world ----------
    this.track = new Track(this.scene);
    this.particles = new Particles(this.scene);
    this.audio = new GameAudio();
    this.karts = [];
    this.player = null;
    this.puddles = [];
    this.bolts = [];
    this.finishOrder = [];
    this.tmp = { x: 0, z: 0 };
    this.buildItemBoxes();
    this.buildPads();
    this.buildMinimap();

    // ---------- state ----------
    this.state = 'menu';
    this.paused = false;
    this.time = 0;       // wall clock for animation
    this.raceTime = 0;
    this.countdown = 0;
    this.lastCount = 0;
    this.centerTimer = 0;
    this.bannerTimer = 0;
    this.resultsDelay = -1;
    this.orbit = 0;
    this.selRacer = 0;
    this.selClass = 'swift';
    this.keys = {};
    this.itemPressed = false;

    this.buildMenu();
    this.bindInput();
    window.addEventListener('resize', () => this.onResize());

    this.clock = new THREE.Clock();
    this.loop = this.loop.bind(this);
    window.__gameBooted = true;
    requestAnimationFrame(this.loop);
  }

  // ====================================================================
  // World pieces owned by the game
  // ====================================================================
  buildItemBoxes() {
    const tr = this.track;
    this.boxMat = new THREE.MeshStandardMaterial({
      color: 0x66ccff, emissive: 0x2266ff, emissiveIntensity: 0.7, roughness: 0.15,
      metalness: 0.4, transparent: true, opacity: 0.88,
    });
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const geo = new THREE.OctahedronGeometry(1.15);
    const coreGeo = new THREE.OctahedronGeometry(0.42);
    this.boxes = [];
    for (const row of ITEM_BOX_ROWS) {
      for (const lane of ITEM_BOX_LANES) {
        const x = tr.px[row] + tr.sx[row] * lane, z = tr.pz[row] + tr.sz[row] * lane;
        const mesh = new THREE.Group();
        const shell = new THREE.Mesh(geo, this.boxMat);
        shell.castShadow = true;
        mesh.add(shell, new THREE.Mesh(coreGeo, coreMat));
        mesh.position.set(x, 1.7, z);
        this.scene.add(mesh);
        this.boxes.push({ mesh, x, z, timer: 0, phase: Math.random() * 6 });
      }
    }
  }

  buildPads() {
    const tr = this.track;
    const tex = canvasTexture(64, 64, (g, w, h) => {
      g.fillStyle = '#0b2a6b'; g.fillRect(0, 0, w, h);
      g.fillStyle = '#3df0ff';
      for (const cy of [16, 48]) {
        g.beginPath();
        g.moveTo(w / 2, cy - 12); g.lineTo(w - 8, cy); g.lineTo(w / 2, cy + 12); g.lineTo(8, cy);
        g.closePath(); g.fill();
      }
    });
    tex.repeat.set(1, 2);
    tr.padTex = tex;
    const mat = new THREE.MeshBasicMaterial({ map: tex });
    mat.polygonOffset = true; mat.polygonOffsetFactor = -5; mat.polygonOffsetUnits = -5;
    this.pads = [];
    for (const [i, lat] of BOOST_PADS) {
      const g = tr.frameAt(i, lat);
      const geo = new THREE.PlaneGeometry(6, 8);
      geo.rotateX(-Math.PI / 2);
      const m = new THREE.Mesh(geo, mat);
      m.position.y = 0.12;
      g.add(m);
      this.scene.add(g);
      this.pads.push({ x: g.position.x, z: g.position.z });
    }
  }

  buildMinimap() {
    const c = $('minimap'), size = 180, pad = 16;
    const b = this.track.bounds;
    const scale = (size - pad * 2) / Math.max(b.maxX - b.minX, b.maxZ - b.minZ);
    const ox = (size - (b.maxX - b.minX) * scale) / 2, oz = (size - (b.maxZ - b.minZ) * scale) / 2;
    const map = (x, z) => [(x - b.minX) * scale + ox, (z - b.minZ) * scale + oz];
    const bg = document.createElement('canvas');
    bg.width = bg.height = size;
    const g = bg.getContext('2d');
    const tr = this.track;
    const path = () => {
      g.beginPath();
      for (let i = 0; i < tr.n; i += 2) {
        const [mx, my] = map(tr.px[i], tr.pz[i]);
        if (i === 0) g.moveTo(mx, my); else g.lineTo(mx, my);
      }
      g.closePath();
    };
    g.lineJoin = 'round';
    g.strokeStyle = 'rgba(10,16,40,.9)'; g.lineWidth = 9; path(); g.stroke();
    g.strokeStyle = 'rgba(255,255,255,.92)'; g.lineWidth = 5; path(); g.stroke();
    const [sx, sy] = map(tr.px[0], tr.pz[0]);
    g.fillStyle = '#ffe45e'; g.fillRect(sx - 3, sy - 6, 6, 12);
    this.mm = { ctx: c.getContext('2d'), bg, map, size };
  }

  // ====================================================================
  // Menus + input
  // ====================================================================
  buildMenu() {
    const rc = $('racers');
    RACERS.forEach((r, i) => {
      const d = document.createElement('div');
      d.className = 'racer' + (i === this.selRacer ? ' sel' : '');
      d.innerHTML = `<i style="background:${hex(r.color)};border-color:${hex(r.accent)}"></i><b>${r.name}</b><small>${r.tag}</small>`;
      d.addEventListener('click', () => {
        this.selRacer = i;
        rc.querySelectorAll('.racer').forEach((e, j) => e.classList.toggle('sel', j === i));
      });
      rc.appendChild(d);
    });
    const cc = $('classes');
    Object.entries(CLASSES).forEach(([key, c]) => {
      const b = document.createElement('button');
      b.textContent = c.label;
      b.className = key === this.selClass ? 'sel' : '';
      b.addEventListener('click', () => {
        this.selClass = key;
        cc.querySelectorAll('button').forEach((e) => e.classList.toggle('sel', e === b));
      });
      cc.appendChild(b);
    });
    $('startBtn').addEventListener('click', () => this.startRace());
    $('againBtn').addEventListener('click', () => this.startRace());
    $('menuBtn').addEventListener('click', () => this.toMenu());
    $('quitBtn').addEventListener('click', () => this.toMenu());
    $('resumeBtn').addEventListener('click', () => this.togglePause());
  }

  bindInput() {
    const block = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'];
    window.addEventListener('keydown', (e) => {
      if (block.includes(e.code)) e.preventDefault();
      if (e.repeat) return;
      this.keys[e.code] = true;
      if (e.code === 'KeyE' || e.code === 'KeyX') this.itemPressed = true;
      if (e.code === 'Escape' || e.code === 'KeyP') this.togglePause();
      if (e.code === 'KeyM') this.audio.toggleMute();
    });
    window.addEventListener('keyup', (e) => {
      if (block.includes(e.code)) e.preventDefault();
      this.keys[e.code] = false;
    });
    window.addEventListener('blur', () => { this.keys = {}; });
  }

  onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  playerInput() {
    const k = this.keys;
    const up = k.KeyW || k.ArrowUp, down = k.KeyS || k.ArrowDown;
    return {
      throttle: up ? 1 : down ? -1 : 0,
      steer: (k.KeyA || k.ArrowLeft ? 1 : 0) - (k.KeyD || k.ArrowRight ? 1 : 0),
      drift: !!(k.Space || k.ShiftLeft || k.ShiftRight),
    };
  }

  aiInput(k) {
    const tr = this.track;
    const look = 4 + Math.floor(Math.max(0, k.speed) * 0.14);
    const ti = tr.wrap(k.idx + look);
    const lane = clamp(k.lane + Math.sin(this.time * 0.25 + k.phase) * 2.5, -6, 6);
    const tx = tr.px[ti] + tr.sx[ti] * lane, tz = tr.pz[ti] + tr.sz[ti] * lane;
    const diff = wrapAngle(Math.atan2(tx - k.x, tz - k.z) - k.heading);
    return { throttle: Math.abs(diff) > 1.0 ? 0 : 1, steer: clamp(diff * 3, -1, 1), drift: false };
  }

  // ====================================================================
  // Race flow
  // ====================================================================
  clearRace() {
    for (const k of this.karts) k.dispose();
    for (const p of this.puddles) this.scene.remove(p.mesh);
    for (const b of this.bolts) this.scene.remove(b.mesh);
    this.karts = []; this.puddles = []; this.bolts = []; this.finishOrder = [];
    this.player = null;
    for (const b of this.boxes) { b.timer = 0; b.mesh.visible = true; }
  }

  startRace() {
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
    this.audio.init();
    this.clearRace();
    const cls = CLASSES[this.selClass];
    this.topSpeed = cls.speed;

    const others = RACERS.map((r, i) => i).filter((i) => i !== this.selRacer);
    for (let i = others.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [others[i], others[j]] = [others[j], others[i]];
    }
    const skills = [1.0, 0.985, 0.97, 0.955, 0.94, 0.925, 0.91];
    others.forEach((ri, slot) => {
      const k = new Kart(RACERS[ri], false, this.track, this.scene);
      k.skill = skills[slot] * cls.ai;
      k.lane = slot % 2 ? -4 : 4;
      k.place(-(3 + slot * 2), slot % 2 ? -4 : 4);
      this.karts.push(k);
    });
    const p = new Kart(RACERS[this.selRacer], true, this.track, this.scene);
    p.place(-(3 + 7 * 2), -4);
    p.lane = -3;
    this.karts.push(p);
    this.player = p;
    this.camYaw = p.heading;
    this.camera.position.set(p.x - Math.sin(p.heading) * 14, 7, p.z - Math.cos(p.heading) * 14);

    this.state = 'countdown';
    this.paused = false;
    this.countdown = 3.4;
    this.lastCount = 4;
    this.raceTime = 0;
    this.resultsDelay = -1;
    this.itemPressed = false;
    $('menu').classList.add('hidden');
    $('results').classList.add('hidden');
    $('pause').classList.add('hidden');
    $('hud').classList.remove('hidden');
    $('wrongway').classList.add('hidden');
    this.setCenter('');
    this.audio.startMusic();
    this.updateRanks();
    this.updateHud();
  }

  toMenu() {
    this.clearRace();
    this.state = 'menu';
    this.paused = false;
    this.audio.stopMusic();
    this.audio.setEngine(0, false);
    $('menu').classList.remove('hidden');
    $('results').classList.add('hidden');
    $('pause').classList.add('hidden');
    $('hud').classList.add('hidden');
    $('boostFx').classList.remove('on');
    this.setCenter('');
    $('banner').classList.remove('show');
  }

  togglePause() {
    if (this.state !== 'race' && this.state !== 'countdown') return;
    this.paused = !this.paused;
    $('pause').classList.toggle('hidden', !this.paused);
    if (this.paused) this.audio.setEngine(0, false);
    this.keys = {};
  }

  setCenter(text, dur = 0) {
    const el = $('center');
    el.textContent = text;
    el.classList.remove('pop');
    if (text) { void el.offsetWidth; el.classList.add('pop'); }
    this.centerTimer = dur;
  }

  showBanner(text, dur = 2) {
    const el = $('banner');
    el.textContent = text;
    el.classList.add('show');
    this.bannerTimer = dur;
  }

  // ====================================================================
  // Items
  // ====================================================================
  chooseItem(k) {
    const back = (k.rank - 1) / Math.max(1, this.karts.length - 1);
    const w = {
      boost: 0.25 + 0.35 * back,
      bolt: 0.15 + 0.3 * back,
      slick: 0.35 - 0.25 * back,
      shield: 0.25 - 0.1 * back,
    };
    let total = 0;
    for (const key of ITEM_KEYS) total += w[key];
    let r = Math.random() * total;
    for (const key of ITEM_KEYS) { r -= w[key]; if (r <= 0) return key; }
    return 'boost';
  }

  giveItem(k) {
    if (k.item || k.itemRoll > 0) return;
    k.pendingItem = this.chooseItem(k);
    k.itemRoll = k.isPlayer ? 1.4 : 0.6;
    k.itemTimer = 1 + Math.random() * 4;
    if (k.isPlayer) this.audio.sfx('pickup');
  }

  useItem(k) {
    const item = k.item;
    if (!item) return;
    k.item = null;
    const me = k.isPlayer;
    const fx = Math.sin(k.heading), fz = Math.cos(k.heading);
    if (item === 'boost') {
      k.boostTime = Math.max(k.boostTime, 1.9);
      if (me) this.audio.sfx('boost');
    } else if (item === 'shield') {
      k.shieldTime = 8;
      if (me) this.audio.sfx('shield');
    } else if (item === 'slick') {
      const geo = new THREE.CircleGeometry(2.3, 20);
      geo.rotateX(-Math.PI / 2);
      const mat = new THREE.MeshBasicMaterial({ color: 0x9b3ffc, transparent: true, opacity: 0.85 });
      mat.polygonOffset = true; mat.polygonOffsetFactor = -6; mat.polygonOffsetUnits = -6;
      const mesh = new THREE.Mesh(geo, mat);
      const x = k.x - fx * 4, z = k.z - fz * 4;
      mesh.position.set(x, 0.14, z);
      this.scene.add(mesh);
      this.puddles.push({ mesh, x, z, owner: k, age: 0 });
      if (me) this.audio.sfx('drop');
    } else if (item === 'bolt') {
      const mesh = new THREE.Mesh(
        new THREE.OctahedronGeometry(0.9),
        new THREE.MeshBasicMaterial({ color: 0xfff27a })
      );
      mesh.scale.set(0.7, 0.7, 1.8);
      this.scene.add(mesh);
      this.bolts.push({ mesh, s: k.idx + 2, lat: k.lat, owner: k, life: 5 });
      if (me) this.audio.sfx('zap');
    }
  }

  hitKart(k, byOwner) {
    const had = k.shieldTime > 0;
    const spun = k.hit();
    const near = k.isPlayer || byOwner === this.player;
    if (spun) {
      for (let i = 0; i < 24; i++) {
        this.particles.emit(k.x, 1, k.z, (Math.random() - 0.5) * 16, 3 + Math.random() * 8,
          (Math.random() - 0.5) * 16, 0.6, 1, 0.9, 0.3, 18);
      }
      if (near) this.audio.sfx('hit');
    } else if (had && near) {
      this.audio.sfx('block');
    }
  }

  updateItems(dt) {
    const tr = this.track;
    // prism crates
    this.boxMat.color.setHSL((this.time * 0.15) % 1, 0.8, 0.62);
    this.boxMat.emissive.setHSL((this.time * 0.15 + 0.1) % 1, 0.9, 0.3);
    for (const b of this.boxes) {
      if (b.timer > 0) {
        b.timer -= dt;
        if (b.timer <= 0) b.mesh.visible = true;
        continue;
      }
      b.mesh.rotation.y = this.time * 1.6 + b.phase;
      b.mesh.rotation.x = this.time * 0.9 + b.phase;
      b.mesh.position.y = 1.7 + Math.sin(this.time * 2.5 + b.phase) * 0.25;
      if (this.state === 'menu') continue;
      for (const k of this.karts) {
        const dx = k.x - b.x, dz = k.z - b.z;
        if (dx * dx + dz * dz < 5.3) {
          b.timer = 3.5; b.mesh.visible = false;
          this.giveItem(k);
          for (let i = 0; i < 14; i++) {
            this.particles.emit(b.x, 1.7, b.z, (Math.random() - 0.5) * 12, Math.random() * 9,
              (Math.random() - 0.5) * 12, 0.5, 0.5, 0.8, 1, 14);
          }
          break;
        }
      }
    }
    if (this.state === 'menu') return;

    // boost pads
    for (const p of this.pads) {
      for (const k of this.karts) {
        const dx = k.x - p.x, dz = k.z - p.z;
        if (dx * dx + dz * dz < 14 && k.hopY < 0.5 && k.spinTime <= 0) {
          if (k.boostTime < 0.3 && k.isPlayer) this.audio.sfx('boost');
          k.boostTime = Math.max(k.boostTime, 1.2);
        }
      }
    }

    // goo puddles
    for (let i = this.puddles.length - 1; i >= 0; i--) {
      const p = this.puddles[i];
      p.age += dt;
      let gone = p.age > 40;
      if (!gone) {
        for (const k of this.karts) {
          if (k === p.owner && p.age < 1.2) continue;
          const dx = k.x - p.x, dz = k.z - p.z;
          if (dx * dx + dz * dz < 7.5 && k.hopY < 0.4) {
            this.hitKart(k, p.owner);
            gone = true;
            break;
          }
        }
      }
      if (gone) { this.scene.remove(p.mesh); p.mesh.geometry.dispose(); p.mesh.material.dispose(); this.puddles.splice(i, 1); }
    }

    // zap bolts follow the circuit and home in sideways on the next kart ahead
    for (let i = this.bolts.length - 1; i >= 0; i--) {
      const b = this.bolts[i];
      b.life -= dt;
      b.s += (115 / tr.segLen) * dt;
      let target = null, best = 45;
      const sm = ((b.s % tr.n) + tr.n) % tr.n;
      for (const k of this.karts) {
        if (k === b.owner) continue;
        const d = (((k.idx - sm) % tr.n) + tr.n) % tr.n;
        if (d < best) { best = d; target = k; }
      }
      if (target) {
        const dl = target.lat - b.lat;
        b.lat += Math.sign(dl) * Math.min(Math.abs(dl), 16 * dt);
      }
      tr.pointAt(b.s, b.lat, this.tmp);
      b.mesh.position.set(this.tmp.x, 1.2, this.tmp.z);
      b.mesh.rotation.y = tr.headingAt(Math.floor(sm) % tr.n);
      b.mesh.rotation.z = this.time * 14;
      this.particles.emit(this.tmp.x, 1.2, this.tmp.z, (Math.random() - 0.5) * 3, Math.random() * 2,
        (Math.random() - 0.5) * 3, 0.3, 1, 0.95, 0.4);
      let gone = b.life <= 0;
      if (!gone) {
        for (const k of this.karts) {
          if (k === b.owner) continue;
          const dx = k.x - this.tmp.x, dz = k.z - this.tmp.z;
          if (dx * dx + dz * dz < 7.5) { this.hitKart(k, b.owner); gone = true; break; }
        }
      }
      if (gone) { this.scene.remove(b.mesh); b.mesh.geometry.dispose(); b.mesh.material.dispose(); this.bolts.splice(i, 1); }
    }
  }

  // ====================================================================
  // Simulation
  // ====================================================================
  updateRanks() {
    const sorted = this.karts.slice().sort((a, b) => {
      const pa = a.finished ? 1e9 - a.finishTime : a.progress;
      const pb = b.finished ? 1e9 - b.finishTime : b.progress;
      return pb - pa;
    });
    sorted.forEach((k, i) => { k.rank = i + 1; });
    this.sorted = sorted;
  }

  updateRace(dt) {
    const tr = this.track, n = tr.n, player = this.player;
    this.raceTime += dt;

    for (const k of this.karts) {
      const human = k.isPlayer && !k.finished;
      const inp = human ? this.playerInput() : this.aiInput(k);
      let top = this.topSpeed;
      if (!human) {
        const gap = k.progress - player.progress;
        const rubber = k.isPlayer ? 0.85 : clamp(1 - gap * 0.0006, 0.9, 1.08);
        top *= (k.isPlayer ? 1 : k.skill) * rubber;
      }
      k.update(dt, inp, top);

      // item roulette + use
      if (k.itemRoll > 0) {
        k.itemRoll -= dt;
        if (k.itemRoll <= 0) {
          k.item = k.pendingItem; k.pendingItem = null;
          if (k.isPlayer) this.audio.sfx('itemReady');
        }
      } else if (k.item) {
        if (human) {
          if (this.itemPressed) this.useItem(k);
        } else if (!k.finished) {
          k.itemTimer -= dt;
          if (k.itemTimer <= 0 && k.spinTime <= 0) this.useItem(k);
        }
      }

      // events → sfx
      if (k.isPlayer) {
        if (k.evHop) this.audio.sfx('hop');
        if (k.evMini) this.audio.sfx('mini');
        if (k.evWall) this.audio.sfx('bump');
      }
      k.evHop = false; k.evMini = 0; k.evWall = false;

      // laps
      const lap = Math.floor(k.progress / n);
      if (lap > k.maxLap) {
        k.maxLap = lap;
        const lt = this.raceTime - k.lapStart;
        k.lapStart = this.raceTime;
        if (lt < k.bestLap) k.bestLap = lt;
        if (lap >= CFG.laps) {
          if (!k.finished) {
            k.finished = true;
            k.finishTime = this.raceTime;
            k.item = null; k.itemRoll = 0;
            this.finishOrder.push(k);
            if (k.isPlayer) this.onPlayerFinish();
            else if (this.state === 'finished' && this.resultsDelay < 0) this.showResults();
          }
        } else if (k.isPlayer) {
          if (lap === CFG.laps - 1) { this.showBanner('FINAL LAP!', 2.5); this.audio.sfx('final'); }
          else { this.showBanner('LAP ' + (lap + 1), 1.8); this.audio.sfx('lap'); }
        }
      }
    }
    this.itemPressed = false;

    // kart-to-kart bumping
    const ks = this.karts, R = CFG.kartRadius * 2;
    for (let i = 0; i < ks.length; i++) {
      for (let j = i + 1; j < ks.length; j++) {
        const a = ks[i], b = ks[j];
        const dx = b.x - a.x, dz = b.z - a.z, d2 = dx * dx + dz * dz;
        if (d2 < R * R && d2 > 1e-4) {
          const d = Math.sqrt(d2), push = (R - d) / 2, nx = dx / d, nz = dz / d;
          a.x -= nx * push; a.z -= nz * push;
          b.x += nx * push; b.z += nz * push;
          const dv = (a.speed - b.speed) * 0.12;
          a.speed -= dv; b.speed += dv;
        }
      }
    }

    this.updateItems(dt);
    this.updateRanks();
    for (const k of this.karts) this.emitKartFx(k, dt);
  }

  onPlayerFinish() {
    this.state = 'finished';
    this.resultsDelay = 2.2;
    this.setCenter('FINISH!', 2.2);
    this.audio.sfx('finish');
    $('wrongway').classList.add('hidden');
  }

  showResults() {
    const list = $('resultsList');
    list.innerHTML = '';
    const rows = this.finishOrder.concat(this.sorted.filter((k) => !k.finished));
    rows.forEach((k, i) => {
      const li = document.createElement('li');
      if (k.isPlayer) li.className = 'me';
      li.innerHTML = `<em>${i + 1}${ordinal(i + 1)}</em><i style="background:${hex(k.racer.color)}"></i>` +
        `<span>${k.racer.name}${k.isPlayer ? ' (you)' : ''}</span>` +
        `<span>${k.finished ? fmtTime(k.finishTime) : '…'}</span>`;
      list.appendChild(li);
    });
    const p = this.player;
    const place = this.finishOrder.indexOf(p) + 1;
    $('resultsTitle').textContent = place === 1 ? 'YOU WIN!' : place <= 3 ? 'PODIUM!' : 'FINISH!';
    $('bestLap').textContent = 'Best lap: ' + (isFinite(p.bestLap) ? fmtTime(p.bestLap) : '—');
    $('results').classList.remove('hidden');
  }

  emitKartFx(k, dt) {
    const P = this.particles;
    const yaw = k.group.rotation.y, c = Math.cos(yaw), s = Math.sin(yaw);
    const rnd = Math.random;
    const wx = (lx, lz) => k.x + lx * c + lz * s;
    const wz = (lx, lz) => k.z - lx * s + lz * c;
    if (k.driftDir !== 0 && k.hopY <= 0.01) {
      const col = SPARK[k.driftLevel()];
      for (const side of [-1, 1]) {
        if (rnd() < 0.7) {
          P.emit(wx(side * 1.1, -1.1), 0.25, wz(side * 1.1, -1.1), (rnd() - 0.5) * 7, 2 + rnd() * 5,
            (rnd() - 0.5) * 7, 0.35, col[0], col[1], col[2], 16);
        }
      }
    }
    if (k.boostTime > 0) {
      for (const side of [-1, 1]) {
        P.emit(wx(side * 0.36, -2.2), 0.98, wz(side * 0.36, -2.2), -s * 9 + (rnd() - 0.5) * 3, (rnd() - 0.3) * 3,
          -c * 9 + (rnd() - 0.5) * 3, 0.28, 1, 0.5 + rnd() * 0.3, 0.12);
      }
    }
    if (k.offroad && Math.abs(k.speed) > 8 && rnd() < 0.5) {
      P.emit(wx(0, -1.4), 0.3, wz(0, -1.4), (rnd() - 0.5) * 5, 1.5 + rnd() * 3, (rnd() - 0.5) * 5,
        0.5, 0.32, 0.26, 0.14, 6);
    }
  }

  // ====================================================================
  // Camera + HUD
  // ====================================================================
  updateCamera(dt) {
    const cam = this.camera;
    if (this.state === 'menu' || !this.player) {
      this.orbit += dt * 0.07;
      const c = this.track.center;
      cam.position.set(c.x + Math.cos(this.orbit) * 330, 150, c.z + Math.sin(this.orbit) * 330);
      cam.lookAt(c.x, 0, c.z);
      cam.fov += (60 - cam.fov) * Math.min(1, 3 * dt);
      cam.updateProjectionMatrix();
      this.sun.position.set(c.x + 120, 220, c.z + 80);
      this.sun.target.position.set(c.x, 0, c.z);
      this.sun.target.updateMatrixWorld();
      return;
    }
    const k = this.player;
    if (this.state === 'finished') {
      this.orbit += dt * 0.6;
      const tx = k.x + Math.sin(this.orbit) * 11, tz = k.z + Math.cos(this.orbit) * 11;
      const a = 1 - Math.exp(-3 * dt);
      cam.position.x += (tx - cam.position.x) * a;
      cam.position.y += (5 - cam.position.y) * a;
      cam.position.z += (tz - cam.position.z) * a;
      cam.lookAt(k.x, 1.4, k.z);
    } else {
      this.camYaw += wrapAngle(k.heading + k.driftDir * 0.2 - this.camYaw) * (1 - Math.exp(-5.5 * dt));
      const fx = Math.sin(this.camYaw), fz = Math.cos(this.camYaw);
      const boosting = k.boostTime > 0;
      const dist = 8.6 + (boosting ? 1.6 : 0);
      const a = 1 - Math.exp(-11 * dt);
      cam.position.x += (k.x - fx * dist - cam.position.x) * a;
      cam.position.y += (4.3 + k.hopY * 0.4 - cam.position.y) * a;
      cam.position.z += (k.z - fz * dist - cam.position.z) * a;
      cam.lookAt(k.x + fx * 5, 1.7, k.z + fz * 5);
      const fov = 70 + (boosting ? 13 : 0) + clamp(k.speed / this.topSpeed, 0, 1) * 5;
      cam.fov += (fov - cam.fov) * Math.min(1, 5 * dt);
      cam.updateProjectionMatrix();
    }
    this.sun.position.set(k.x + 70, 110, k.z + 45);
    this.sun.target.position.set(k.x, 0, k.z);
    this.sun.target.updateMatrixWorld();
  }

  updateHud() {
    const p = this.player;
    if (!p) return;
    $('pos').textContent = p.rank;
    $('posSuffix').textContent = ordinal(p.rank);
    const lap = clamp(Math.floor(p.progress / this.track.n) + 1, 1, CFG.laps);
    $('lap').textContent = `Lap ${lap}/${CFG.laps}`;
    $('time').textContent = fmtTime(p.finished ? p.finishTime : this.raceTime);
    $('speed').textContent = Math.round(Math.abs(p.speed) * 2.6);

    let icon = '', name = '';
    if (p.itemRoll > 0) icon = ITEMS[ITEM_KEYS[Math.floor(this.time * 14) % ITEM_KEYS.length]].icon;
    else if (p.item) { icon = ITEMS[p.item].icon; name = ITEMS[p.item].label; }
    $('itemIcon').textContent = icon;
    $('itemName').textContent = name;

    const bar = $('driftBar');
    bar.style.width = (p.driftDir !== 0 ? clamp(p.driftCharge / 3.2, 0, 1) * 100 : 0) + '%';
    bar.style.background = DRIFT_COLORS[p.driftLevel()];
    $('boostFx').classList.toggle('on', p.boostTime > 0 && this.state === 'race');

    const tr = this.track;
    const dot = Math.sin(p.heading) * tr.tx[p.idx] + Math.cos(p.heading) * tr.tz[p.idx];
    $('wrongway').classList.toggle('hidden', !(this.state === 'race' && dot < -0.4 && p.speed > 6));

    // minimap
    const { ctx, bg, map, size } = this.mm;
    ctx.clearRect(0, 0, size, size);
    ctx.drawImage(bg, 0, 0);
    for (const k of this.karts) {
      if (k === p) continue;
      const [mx, my] = map(k.x, k.z);
      ctx.fillStyle = hex(k.racer.color);
      ctx.strokeStyle = '#0a1028'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(mx, my, 4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    }
    const [mx, my] = map(p.x, p.z);
    ctx.fillStyle = '#ffffff'; ctx.strokeStyle = hex(p.racer.color); ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(mx, my, 5.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }

  // ====================================================================
  // Main loop
  // ====================================================================
  loop() {
    requestAnimationFrame(this.loop);
    const dt = Math.min(this.clock.getDelta(), 0.05);

    if (!this.paused) {
      this.time += dt;
      this.track.update(this.time);

      if (this.state === 'countdown') {
        this.countdown -= dt;
        const c = Math.ceil(this.countdown);
        if (c !== this.lastCount) {
          this.lastCount = c;
          if (c >= 1 && c <= 3) { this.setCenter(String(c), 1); this.audio.sfx('count'); }
        }
        if (this.countdown <= 0) {
          this.state = 'race';
          this.setCenter('GO!', 0.9);
          this.audio.sfx('go');
          for (const k of this.karts) k.lapStart = 0;
        }
        for (const k of this.karts) k.sync(dt);
        this.updateItems(dt);
      } else if (this.state === 'race' || this.state === 'finished') {
        this.updateRace(dt);
        if (this.resultsDelay >= 0) {
          this.resultsDelay -= dt;
          if (this.resultsDelay < 0) this.showResults();
        }
      } else {
        this.updateItems(dt);
      }

      if (this.centerTimer > 0) {
        this.centerTimer -= dt;
        if (this.centerTimer <= 0) $('center').textContent = '';
      }
      if (this.bannerTimer > 0) {
        this.bannerTimer -= dt;
        if (this.bannerTimer <= 0) $('banner').classList.remove('show');
      }

      this.particles.update(dt);
      this.updateCamera(dt);
      if (this.state !== 'menu') {
        this.updateHud();
        const p = this.player;
        const rev = this.state === 'countdown'
          ? ((this.keys.KeyW || this.keys.ArrowUp) ? 0.6 : 0.1)
          : Math.abs(p.speed) / this.topSpeed;
        this.audio.setEngine(rev, true);
      }
      this.audio.tickMusic();
    }

    this.renderer.render(this.scene, this.camera);
  }
}

new Game();
```

---

## Design notes

- **Track model.** The circuit is a closed centripetal Catmull-Rom spline sampled into 600 evenly spaced points. Every gameplay query (lap progress, off-road, walls, AI targets, bolt flight, minimap) works on those samples, so physics never needs mesh collision. Each kart keeps a rolling nearest-sample index and an unwrapped progress counter; laps are `floor(progress / samples)`, which also makes driving backwards over the line harmless.
- **Driving model.** Arcade, not simulation: speed and heading with a speed-dependent grip curve. Drifting commits to a direction, biases the steering range into the turn, slides the kart body visually and charges a three-stage mini-turbo.
- **Fair racing.** Rivals have fixed skill spreads per speed class plus mild rubber-banding (±8–10 %), and item odds shift toward offensive items and boosts the further back a racer is.
- **Performance.** Scenery uses instanced meshes, particles are a single pooled `Points` draw call, and one 2048² shadow map follows the player.

## Possible next steps

- More circuits (the track is data-driven: change `CONTROL` in `src/track.js`), elevation and jumps
- Touch and gamepad controls, split-screen multiplayer
- Time-trial ghosts and a multi-race cup mode
