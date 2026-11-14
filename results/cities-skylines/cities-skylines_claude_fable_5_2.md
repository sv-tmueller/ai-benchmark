# Meridian — a city builder in Three.js + Vite (single-pass blueprint)

**Read this first (honest status).** This document is a one-shot blueprint: every project file is below as a fenced block labelled with its path. The process the brief asks for (builder agents per module, critic gauntlet, blind A/B judging, `/loop`) needs a running dev server, headless Chrome and several agents; none of that was run in this pass. Therefore **no score is claimed anywhere**: `docs/STATUS.json` ships with every module at `score: null, verified: false`, and the loop in `ARCHITECTURE.md` §9 starts from there. Nothing here has been screenshotted, so by the brief's own rule nothing here may be called AAA yet.

Assumptions: original city builder in the genre (own name, own look, no third-party game assets); all materials are procedural (CC0 by construction), so the app runs offline; Poly Haven / ambientCG textures are an upgrade path listed in the open issues; `three` and `vite` resolve to the latest release at install time.

Run: `npm i`, `npm run dev`, open `http://localhost:5173/`. Verify: `npm run shot -- --cam=skyline --time=21`. Showcase: `/?showcase=roads`.

### `package.json`
```json
{
  "name": "meridian-city",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "shot": "node tools/screenshot.mjs"
  },
  "dependencies": { "three": "latest" },
  "devDependencies": { "vite": "latest", "puppeteer": "latest" }
}
```

### `vite.config.js`
```js
import { defineConfig } from 'vite';
export default defineConfig({ server: { port: 5173, strictPort: true }, build: { target: 'es2022' } });
```

### `index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meridian</title>
<style>html,body{margin:0;height:100%;overflow:hidden;background:#0b0e13}canvas{display:block}</style>
</head>
<body>
<script type="module" src="/src/main.js"></script>
</body>
</html>
```

### `ARCHITECTURE.md`
```markdown
# Architecture

## 1. Conventions
- Units: metres. +Y up. Right-handed. North = -Z, East = +X.
- World grid: N = 128 cells of CELL = 8 m (1024 m square) centred on the origin; city ground plane at y = 2 (GROUND); water at y = 0.6.
- Determinism: `Math.random` is banned. Every module takes `world.rng(tag)` (mulberry32) or `hash2/fbm` from `core/rng.js`. Simulation runs on a fixed 0.5 s tick.
- Performance budget: >= 50 fps at 1080p, <= 1500 draw calls, <= 3 M triangles, one 4096 shadow map. Everything repeated is an InstancedMesh; the whole city is roughly 60 draw calls.
- Asset policy: CC0 only (Poly Haven, ambientCG) or procedural. Current build: 100 % procedural canvas/data textures.

## 2. Folders (one owner each)
| Folder | Owns | Wave |
|---|---|---|
| `src/core` | world model, events, rng, registry, catalog, textures, staging (integrator only) | 0 |
| `src/terrain` | height field, terrain mesh, water | 1 |
| `src/environment` | sun/moon, sky, IBL, fog, stars, exposure | 1 |
| `src/roads` | road tiles, markings, bridges | 1 |
| `src/simulation` | clock, demand, growth, budget | 1 |
| `src/ui` | DOM HUD, toolbar, toasts | 1 |
| `src/audio` | procedural WebAudio ambience | 1 |
| `src/effects` | post-processing, bloom, clouds | 1 |
| `src/zoning` | zone overlay | 2 |
| `src/buildings` | instanced buildings, facades, night windows | 2 |
| `src/props` | trees, street lights, light pools | 2 |
| `src/traffic` | vehicles on the road graph | 2 |
| `src/tools` | road/zone/bulldoze input | 2 |
| `src/democity` | seeded demo city | 3 |

## 3. Shared world model (`core/world.js`)
`World { seed, road:Uint8Array, zone:Uint8Array, bldg:Int32Array, buildings:Map<id,{id,cx,cz,cls,tint}>, time (h), speed, timeLocked, stats{pop,jobs,money,demand{r,c,i,o}}, height(x,z) }`
Helpers: `rng(tag) inb idx wx cell isRoad roadMask buildable addBuilding removeBuilding night`.
Zones: 0 none, 1 residential, 2 commercial, 3 industrial, 4 office, 5 park. Building classes live in `core/catalog.js`.

## 4. Module contract
`export default function create(ctx) -> { name, init(), update(dt), api?, showcase? }`
`ctx = { THREE, scene, camera, renderer, controls, world, events, params, api, render }`.
- `init` may be async. `api` is published at `ctx.api[name]`. `showcase = { cam:{pos,target}, time }`.
- A module reads/writes only `world`, `events`, `ctx.api.*`; it never imports another module's folder.

## 5. Events
`roads:changed`, `zones:changed`, `buildings:changed`, `sim:tick(stats)`, `tool:changed(name)`, `tool:set(name)`, `ui:click`, `module:error({name,phase,message})`.

## 6. Failure isolation
`core/registry.js` loads each module by dynamic import inside try/catch (a syntax error in one module cannot break the graph), wraps `init`, and wraps every `update`; three consecutive update failures disable the module and raise `module:error`. Event handlers are individually guarded. If `effects` fails the loop falls back to `renderer.render`.

## 7. Verification loop
`tools/screenshot.mjs` drives headless Chrome: loads the URL, waits for `window.__game.ready`, calls `setTime` / `setCamera`, settles, writes `shots/<name>.png` + `.json` (console errors, fps, draw calls, triangles, module status). Exit code 1 on any console error.
`/?showcase=<module>` loads only that module and its dependencies on a staged 4x4-block scene.
Test hook: `window.__game = { ready, setTime(h), setCamera(preset), stats(), world }`. Presets: skyline, aerial, top, street, river, showcase.

## 8. Orchestration
Wave 1: terrain, environment, roads, simulation, ui, audio, effects. Wave 2: zoning, buildings, props, traffic, tools. Wave 3: democity. One builder per folder; core change requests go to the integrator between waves.
Critic (no code): shots at 07:00, 13:00, 18:30, 22:00 at street/aerial/skyline zoom; checks contract, console errors, fps, draw calls; scores 0-10 (10 indistinguishable from a shipped AAA city builder, 8.5 AAA with nits, 7 good indie, 5 programmer art). Pass = >= 8.5 and zero errors; up to 4 rounds.
Final gate: whole-game critic on the demo city, then blind A/B judges on shuffled screenshot pairs.

## 9. Loop state
`docs/STATUS.json` stores per-module score, round, verified flag and open issues. Each iteration resumes at the lowest-scoring unverified module. Scores are written only by a critic that produced screenshots; builders may not edit them.
```

### `docs/STATUS.json`
```json
{
  "note": "Initial state after the one-shot build. No critic has run, no screenshot has been taken; all scores are null on purpose.",
  "budget": { "fps_min": 50, "draw_calls_max": 1500, "measured": null },
  "modules": {
    "terrain": { "score": null, "round": 0, "verified": false, "issues": ["vertex-colour terrain, no splat-mapped PBR ground textures", "no shoreline foam or depth-based water colour"] },
    "environment": { "score": null, "round": 0, "verified": false, "issues": ["single shadow map, no cascades", "no weather states"] },
    "roads": { "score": null, "round": 0, "verified": false, "issues": ["grid-only roads, no curves or elevation", "no traffic signals or signs"] },
    "simulation": { "score": null, "round": 0, "verified": false, "issues": ["no services, utilities or land value"] },
    "ui": { "score": null, "round": 0, "verified": false, "issues": ["no info views or building inspector"] },
    "audio": { "score": null, "round": 0, "verified": false, "issues": ["synthesised ambience only"] },
    "effects": { "score": null, "round": 0, "verified": false, "issues": ["no SSAO, no volumetric clouds"] },
    "zoning": { "score": null, "round": 0, "verified": false, "issues": [] },
    "buildings": { "score": null, "round": 0, "verified": false, "issues": ["ten box-based classes, no modelled assets", "facade pattern shared per class"] },
    "props": { "score": null, "round": 0, "verified": false, "issues": ["two tree shapes", "street lights are emissive plus decals, not real lights"] },
    "traffic": { "score": null, "round": 0, "verified": false, "issues": ["no signals, no pedestrians, one vehicle body"] },
    "tools": { "score": null, "round": 0, "verified": false, "issues": ["no undo"] },
    "democity": { "score": null, "round": 0, "verified": false, "issues": [] }
  },
  "final_gate": { "whole_game_score": null, "blind_ab": null }
}
```

### `tools/screenshot.mjs`
```js
// Usage: node tools/screenshot.mjs --cam=skyline --time=21 [--showcase=roads] [--url=http://localhost:5173/] [--out=shots/x] [--settle=3000]
import puppeteer from 'puppeteer';
import fs from 'node:fs';
import path from 'node:path';

const a = Object.fromEntries(process.argv.slice(2).map((s) => s.replace(/^--/, '').split('=')));
const url = new URL(a.url || 'http://localhost:5173/');
for (const k of ['showcase', 'seed']) if (a[k]) url.searchParams.set(k, a[k]);
const cam = a.cam || (a.showcase ? 'showcase' : 'skyline');
const out = a.out || `shots/${a.showcase || 'game'}_${cam}_${a.time ?? 'default'}`;
fs.mkdirSync(path.dirname(out), { recursive: true });

const browser = await puppeteer.launch({
  headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--window-size=1920,1080'],
});
const errors = [];
let stats = null;
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url.href, { waitUntil: 'load' });
  await page.waitForFunction('window.__game && window.__game.ready', { timeout: 120000 });
  await page.evaluate((c, t) => { if (t !== null) window.__game.setTime(t); window.__game.setCamera(c); }, cam, a.time != null ? Number(a.time) : null);
  await new Promise((r) => setTimeout(r, Number(a.settle || 3000)));
  stats = await page.evaluate(() => window.__game.stats());
  await page.screenshot({ path: out + '.png' });
} catch (e) {
  errors.push('screenshot tool: ' + String(e));
} finally {
  await browser.close();
}
fs.writeFileSync(out + '.json', JSON.stringify({ url: url.href, cam, time: a.time ?? null, errors, stats }, null, 2));
console.log(out + '.png', JSON.stringify({ errors: errors.length, fps: stats?.fps, calls: stats?.calls }));
process.exit(errors.length ? 1 : 0);
```

### `src/core/rng.js`
```js
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function hash2(x, y, s = 0) {
  let h = (Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263) ^ Math.imul(s | 0, 1274126177)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
const sm = (t) => t * t * (3 - 2 * t);
export function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y), u = sm(x - xi), v = sm(y - yi);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
export function fbm(x, y, s, o = 5) {
  let f = 1, a = 0.5, r = 0;
  for (let i = 0; i < o; i++) { r += a * vnoise(x * f, y * f, s + i); f *= 2; a *= 0.5; }
  return r;
}
export const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (a, b, x) => sm(clamp((x - a) / (b - a), 0, 1));
```

### `src/core/events.js`
```js
export class Events {
  constructor() { this.m = new Map(); }
  on(n, f) { if (!this.m.has(n)) this.m.set(n, []); this.m.get(n).push(f); }
  emit(n, p) {
    for (const f of this.m.get(n) || []) {
      try { f(p); } catch (e) { console.error(`[events] handler for ${n} failed`, e); }
    }
  }
}
```

### `src/core/catalog.js`
```js
// Building classes. z = zone id, cells = lot edge in cells, w/d/h metres, fl floors, bays windows per side, f facade kind.
export const CATALOG = [
  { k: 'house', z: 1, cells: 1, w: 6, d: 6, h: 6.4, fl: 2, bays: 3, f: 'plaster', pop: 4, jobs: 0 },
  { k: 'apartments', z: 1, cells: 1, w: 7, d: 7, h: 19.2, fl: 6, bays: 4, f: 'brick', pop: 36, jobs: 0 },
  { k: 'res-tower', z: 1, cells: 2, w: 13.5, d: 13.5, h: 57.6, fl: 18, bays: 8, f: 'plaster', pop: 280, jobs: 0 },
  { k: 'shop', z: 2, cells: 1, w: 7.2, d: 7, h: 5, fl: 1, bays: 2, f: 'shop', pop: 0, jobs: 6 },
  { k: 'com-mid', z: 2, cells: 1, w: 7.2, d: 7.2, h: 25.6, fl: 8, bays: 4, f: 'glass', pop: 0, jobs: 60 },
  { k: 'com-tower', z: 2, cells: 2, w: 14, d: 14, h: 76.8, fl: 24, bays: 8, f: 'glass', pop: 0, jobs: 420 },
  { k: 'works', z: 3, cells: 1, w: 7, d: 7, h: 6, fl: 1, bays: 2, f: 'metal', pop: 0, jobs: 12 },
  { k: 'warehouse', z: 3, cells: 2, w: 14.5, d: 14, h: 9, fl: 1, bays: 4, f: 'metal', pop: 0, jobs: 40 },
  { k: 'office', z: 4, cells: 1, w: 7.2, d: 7.2, h: 32, fl: 10, bays: 4, f: 'glass2', pop: 0, jobs: 90 },
  { k: 'office-tower', z: 4, cells: 2, w: 14, d: 14, h: 128, fl: 40, bays: 8, f: 'glass2', pop: 0, jobs: 900 },
];
```

### `src/core/world.js`
```js
import { mulberry32 } from './rng.js';
import { CATALOG } from './catalog.js';

export const CELL = 8, N = 128, SIZE = N * CELL, HALF = SIZE / 2, GROUND = 2, WATER = 0.6;
export const ZONE = { NONE: 0, RES: 1, COM: 2, IND: 3, OFF: 4, PARK: 5 };

export class World {
  constructor(seed = 1337) {
    this.seed = seed;
    this.road = new Uint8Array(N * N);
    this.zone = new Uint8Array(N * N);
    this.bldg = new Int32Array(N * N);
    this.buildings = new Map();
    this.nextId = 1;
    this.time = 10;
    this.speed = 1;
    this.timeLocked = false;
    this.stats = { pop: 0, jobs: 0, money: 250000, demand: { r: 0.4, c: 0.2, i: 0.2, o: 0.1 } };
    this.height = () => GROUND;
  }
  rng(tag = 0) { return mulberry32(this.seed * 7919 + tag); }
  inb(x, z) { return x >= 0 && z >= 0 && x < N && z < N; }
  idx(x, z) { return z * N + x; }
  wx(c) { return c * CELL - HALF + CELL / 2; }
  cell(w) { return Math.floor((w + HALF) / CELL); }
  isRoad(x, z) { return this.inb(x, z) && this.road[z * N + x] > 0; }
  roadMask(x, z) {
    return (this.isRoad(x, z - 1) ? 1 : 0) | (this.isRoad(x + 1, z) ? 2 : 0) | (this.isRoad(x, z + 1) ? 4 : 0) | (this.isRoad(x - 1, z) ? 8 : 0);
  }
  cellHeight(x, z) { return this.height(this.wx(x), this.wx(z)); }
  buildable(x, z) { return this.inb(x, z) && Math.abs(this.cellHeight(x, z) - GROUND) < 0.6; }
  addBuilding(b) {
    b.id = this.nextId++;
    const n = CATALOG[b.cls].cells;
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) this.bldg[(b.cz + j) * N + b.cx + i] = b.id;
    this.buildings.set(b.id, b);
    return b;
  }
  removeBuilding(id) {
    const b = this.buildings.get(id);
    if (!b) return;
    const n = CATALOG[b.cls].cells;
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) this.bldg[(b.cz + j) * N + b.cx + i] = 0;
    this.buildings.delete(id);
  }
  // 0 = full day, 1 = full night
  get night() {
    const s = Math.sin(((this.time - 6) / 12) * Math.PI);
    return Math.min(1, Math.max(0, (0.08 - s) / 0.2));
  }
}
```

### `src/core/tex.js`
```js
import * as THREE from 'three';

export function canvasTex(size, draw, { repeat = 1, srgb = true } = {}) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  draw(c.getContext('2d'), size);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.anisotropy = 8;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
export function speckle(g, s, rng, n, a = 0.08) {
  for (let i = 0; i < n; i++) {
    const v = (rng() * 255) | 0;
    g.fillStyle = `rgba(${v},${v},${v},${a})`;
    g.fillRect(rng() * s, rng() * s, 1 + rng() * 2, 1 + rng() * 2);
  }
}
// Tileable normal map from a sum of integer-frequency waves.
export function waveNormalTex(size, rng, waves = 12, strength = 1) {
  const W = [];
  for (let i = 0; i < waves; i++) W.push([(1 + ((rng() * 7) | 0)) * (rng() < 0.5 ? -1 : 1), 1 + ((rng() * 7) | 0), rng() * 6.283, 1 / (1 + i * 0.35)]);
  const d = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const u = (x / size) * 6.2832, v = (y / size) * 6.2832;
    let dx = 0, dy = 0;
    for (const [kx, ky, p, a] of W) { const c = Math.cos(kx * u + ky * v + p) * a; dx += c * kx; dy += c * ky; }
    const nx = -dx * strength * 0.06, ny = -dy * strength * 0.06, l = Math.hypot(nx, ny, 1), i = (y * size + x) * 4;
    d[i] = ((nx / l) * 0.5 + 0.5) * 255; d[i + 1] = ((ny / l) * 0.5 + 0.5) * 255; d[i + 2] = ((1 / l) * 0.5 + 0.5) * 255; d[i + 3] = 255;
  }
  const t = new THREE.DataTexture(d, size, size);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.needsUpdate = true;
  return t;
}
export function glowTex(inner = 'rgba(255,255,255,1)') {
  return canvasTex(128, (g, s) => {
    const r = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    r.addColorStop(0, inner); r.addColorStop(0.35, 'rgba(255,255,255,0.35)'); r.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = '#000'; g.fillRect(0, 0, s, s); g.fillStyle = r; g.fillRect(0, 0, s, s);
  });
}
```

### `src/core/registry.js`
```js
export class Registry {
  constructor(ctx) { this.ctx = ctx; this.mods = []; this.status = {}; }
  fail(name, e, phase) {
    console.error(`[module:${name}] ${phase} failed`, e);
    this.status[name] = 'failed:' + phase;
    this.ctx.events.emit('module:error', { name, phase, message: String(e?.message || e) });
  }
  async load(name, loader) {
    try {
      if (!loader) throw new Error('module not found');
      const inst = (await loader()).default(this.ctx);
      await inst.init?.();
      this.ctx.api[name] = inst.api || {};
      this.mods.push({ name, inst, fails: 0 });
      this.status[name] = 'ok';
      return inst;
    } catch (e) { this.fail(name, e, 'init'); return null; }
  }
  update(dt) {
    for (const m of this.mods) {
      if (m.fails >= 3) continue;
      try { m.inst.update?.(dt); m.fails = 0; } catch (e) { if (++m.fails >= 3) this.fail(m.name, e, 'update'); }
    }
  }
}
```

### `src/core/stage.js`
```js
import { N } from './world.js';
// Shared showcase stage: a 4x4-block street grid with mixed zones around the origin.
export function stage(ctx) {
  const w = ctx.world, c = N / 2;
  for (let j = -10; j <= 10; j++) for (let i = -10; i <= 10; i++) {
    const k = (c + j) * N + c + i;
    if (i % 5 === 0 || j % 5 === 0) w.road[k] = 1;
    else w.zone[k] = 1 + ((Math.floor((i + 10) / 5) + Math.floor((j + 10) / 5)) % 4);
  }
  ctx.events.emit('roads:changed');
  ctx.events.emit('zones:changed');
}
```

### `src/main.js`
```js
import * as THREE from 'three';
import { MapControls } from 'three/addons/controls/MapControls.js';
import { World } from './core/world.js';
import { Events } from './core/events.js';
import { Registry } from './core/registry.js';
import { stage } from './core/stage.js';

const params = new URLSearchParams(location.search);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.info.autoReset = false;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(48, innerWidth / innerHeight, 2, 14000);
const controls = new MapControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.maxPolarAngle = 1.52;
controls.minDistance = 12;
controls.maxDistance = 2600;

const world = new World(Number(params.get('seed')) || 1337);
if (params.has('t')) { world.time = Number(params.get('t')); world.timeLocked = true; }
const events = new Events();
const ctx = { THREE, scene, camera, renderer, controls, world, events, params, api: {}, render: null };
const registry = new Registry(ctx);

const PRESETS = {
  skyline: { pos: [-430, 120, -400], target: [0, 45, 0] },
  aerial: { pos: [-260, 330, 330], target: [0, 0, 20] },
  top: { pos: [0, 760, 1], target: [0, 0, 0] },
  street: { pos: [3, 5, 96], target: [2, 14, -40] },
  river: { pos: [-330, 40, 330], target: [0, 30, 60] },
  showcase: { pos: [-95, 70, -120], target: [0, 8, 0] },
};
function setCamera(p) {
  const c = typeof p === 'string' ? PRESETS[p] || PRESETS.skyline : p;
  camera.position.set(...c.pos);
  controls.target.set(...c.target);
  controls.update();
}

const ALL = ['terrain', 'environment', 'effects', 'roads', 'simulation', 'zoning', 'buildings', 'props', 'traffic', 'tools', 'ui', 'audio', 'democity'];
const BASE = ['terrain', 'environment', 'effects'];
const SHOW = {
  terrain: [], environment: [], effects: [], roads: ['roads'], zoning: ['roads', 'zoning'],
  simulation: ['roads', 'simulation', 'zoning', 'buildings'], buildings: ['roads', 'simulation', 'buildings'],
  props: ['roads', 'props'], traffic: ['roads', 'traffic'], tools: ['roads', 'zoning', 'tools', 'ui'],
  ui: ['roads', 'ui'], audio: ['ui', 'audio'], democity: ALL.slice(3),
};
const loaders = import.meta.glob('./*/index.js');
const showcase = params.get('showcase');
let fps = 60, last = performance.now();
const keys = new Set();
addEventListener('keydown', (e) => keys.add(e.code));
addEventListener('keyup', (e) => keys.delete(e.code));
addEventListener('blur', () => keys.clear());
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  events.emit('resize');
});

function pan(dt) {
  const f = new THREE.Vector3(), r = new THREE.Vector3();
  camera.getWorldDirection(f); f.y = 0; f.normalize(); r.set(-f.z, 0, f.x);
  const s = camera.position.distanceTo(controls.target) * 0.9 * dt, m = new THREE.Vector3();
  if (keys.has('KeyW')) m.addScaledVector(f, s);
  if (keys.has('KeyS')) m.addScaledVector(f, -s);
  if (keys.has('KeyD')) m.addScaledVector(r, s);
  if (keys.has('KeyA')) m.addScaledVector(r, -s);
  camera.position.add(m); controls.target.add(m);
}
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  if (dt > 0) fps += (1 / dt - fps) * 0.05;
  pan(dt);
  controls.update();
  registry.update(dt);
  renderer.info.reset();
  try { if (ctx.render) ctx.render(); else renderer.render(scene, camera); }
  catch (e) { console.error('[render] post chain failed, falling back', e); ctx.render = null; }
}

async function boot() {
  const names = showcase ? [...new Set([...BASE, ...(SHOW[showcase] || [])])] : ALL;
  if (showcase && !SHOW[showcase]) console.error(`unknown showcase "${showcase}"`);
  let staged = false, sc = null;
  for (const name of names) {
    if (showcase && showcase !== 'democity' && !staged && !BASE.includes(name)) { /* stage after base */ }
    const inst = await registry.load(name, loaders[`./${name}/index.js`]);
    if (name === showcase) sc = inst?.showcase || null;
  }
  if (showcase && showcase !== 'democity' && names.includes('roads')) {
    stage(ctx);
    staged = true;
    ctx.api.simulation?.grow?.();
  }
  setCamera(showcase ? sc?.cam || PRESETS.showcase : params.get('cam') || 'skyline');
  if (showcase && sc?.time != null && !params.has('t')) { world.time = sc.time; world.timeLocked = true; }
  requestAnimationFrame(frame);
  window.__game = {
    ready: true, world,
    setTime(h) { world.time = ((h % 24) + 24) % 24; world.timeLocked = true; },
    setCamera,
    stats: () => ({ fps: Math.round(fps), calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, modules: { ...registry.status }, pop: world.stats.pop, staged }),
  };
}
boot();
```

### `src/terrain/index.js`
```js
import { GROUND, WATER } from '../core/world.js';
import { fbm, smooth, lerp, hash2 } from '../core/rng.js';
import { canvasTex, speckle, waveNormalTex } from '../core/tex.js';

export default function create(ctx) {
  const { THREE, scene, world } = ctx;
  let waterMat;
  return {
    name: 'terrain',
    showcase: { cam: { pos: [-520, 150, 520], target: [0, 10, 200] }, time: 17.5 },
    init() {
      const seed = world.seed;
      world.height = (x, z) => {
        const d = Math.hypot(x, z);
        let h = GROUND + fbm(x / 260 + 9, z / 260 + 9, seed, 5) * 95 * smooth(380, 640, d);
        const rv = 1 - smooth(22, 48, Math.abs(z - (250 + 40 * Math.sin(x / 140))));
        h = lerp(h, -5, rv);
        return lerp(h, -9, smooth(820, 1010, d));
      };
      const geo = new THREE.PlaneGeometry(2048, 2048, 256, 256).rotateX(-Math.PI / 2);
      const p = geo.attributes.position;
      for (let i = 0; i < p.count; i++) p.setY(i, world.height(p.getX(i), p.getZ(i)));
      geo.computeVertexNormals();
      const nrm = geo.attributes.normal, col = new Float32Array(p.count * 3);
      const grass = [0.105, 0.19, 0.055], dry = [0.21, 0.22, 0.08], rock = [0.27, 0.25, 0.23], sand = [0.5, 0.44, 0.31], bed = [0.09, 0.1, 0.08];
      for (let i = 0; i < p.count; i++) {
        const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
        const n = fbm(x / 70, z / 70, seed + 40, 4), steep = smooth(0.82, 0.62, nrm.getY(i));
        const shore = 1 - smooth(1.0, 1.9, y), deep = 1 - smooth(-1.5, 0.4, y);
        const v = 0.85 + hash2(x, z, 3) * 0.3;
        for (let k = 0; k < 3; k++) {
          let c = lerp(grass[k], dry[k], smooth(0.4, 0.7, n));
          c = lerp(c, rock[k], steep);
          c = lerp(c, sand[k], shore);
          c = lerp(c, bed[k], deep);
          col[i * 3 + k] = c * v;
        }
      }
      geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      const rng = world.rng(21);
      const detail = canvasTex(512, (g, s) => { g.fillStyle = '#d2d2d2'; g.fillRect(0, 0, s, s); speckle(g, s, rng, 26000, 0.1); }, { repeat: 240 });
      const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, map: detail, roughness: 0.96, metalness: 0 }));
      mesh.receiveShadow = true;
      scene.add(mesh);

      waterMat = new THREE.MeshStandardMaterial({
        color: 0x0a2733, roughness: 0.07, metalness: 0.1, normalMap: waveNormalTex(256, world.rng(22), 12, 1),
        normalScale: new THREE.Vector2(0.45, 0.45), transparent: true, opacity: 0.93, envMapIntensity: 1.5,
      });
      waterMat.normalMap.repeat.set(260, 260);
      const water = new THREE.Mesh(new THREE.PlaneGeometry(12000, 12000).rotateX(-Math.PI / 2), waterMat);
      water.position.y = WATER;
      water.receiveShadow = true;
      scene.add(water);
    },
    update(dt) {
      waterMat.normalMap.offset.x += dt * 0.012;
      waterMat.normalMap.offset.y += dt * 0.007;
    },
  };
}
```

### `src/environment/index.js`
```js
import { Sky } from 'three/addons/objects/Sky.js';
import { smooth, lerp } from '../core/rng.js';

export default function create(ctx) {
  const { THREE, scene, camera, renderer, controls, world } = ctx;
  const dir = new THREE.Vector3(), tmp = new THREE.Vector3();
  const cDay = new THREE.Color(0.6, 0.71, 0.86), cDusk = new THREE.Color(0.86, 0.5, 0.3), cNight = new THREE.Color(0.012, 0.018, 0.04);
  const sunLow = new THREE.Color(1, 0.62, 0.36), sunHigh = new THREE.Color(1, 0.96, 0.9), moon = new THREE.Color(0.55, 0.68, 1);
  let sky, envSky, envScene, pmrem, envRT = null, light, hemi, stars, lastEnv = -99;
  return {
    name: 'environment',
    showcase: { cam: { pos: [-520, 90, -300], target: [0, 60, 0] }, time: 18.6 },
    init() {
      sky = new Sky();
      sky.scale.setScalar(450000);
      scene.add(sky);
      envScene = new THREE.Scene();
      envSky = new Sky();
      envSky.material = sky.material;
      envSky.scale.setScalar(450000);
      envScene.add(envSky);
      pmrem = new THREE.PMREMGenerator(renderer);
      light = new THREE.DirectionalLight(0xffffff, 4);
      light.castShadow = true;
      light.shadow.mapSize.set(4096, 4096);
      const sc = light.shadow.camera;
      sc.left = sc.bottom = -420; sc.right = sc.top = 420; sc.near = 50; sc.far = 2200;
      light.shadow.bias = -0.0004;
      light.shadow.normalBias = 0.7;
      scene.add(light, light.target);
      hemi = new THREE.HemisphereLight(0xbfd4ff, 0x3a3428, 0.5);
      scene.add(hemi);
      scene.fog = new THREE.FogExp2(0x9fb8d8, 0.00042);
      const rng = world.rng(31), pos = new Float32Array(1800 * 3);
      for (let i = 0; i < 1800; i++) {
        const a = rng() * 6.283, y = rng() * 0.95 + 0.03, r = Math.sqrt(1 - y * y);
        pos.set([Math.cos(a) * r * 6000, y * 6000, Math.sin(a) * r * 6000], i * 3);
      }
      const sg = new THREE.BufferGeometry();
      sg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      stars = new THREE.Points(sg, new THREE.PointsMaterial({ color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0, fog: false, depthWrite: false }));
      stars.frustumCulled = false;
      scene.add(stars);
    },
    update() {
      const t = world.time, ang = ((t - 6) / 12) * Math.PI, night = world.night;
      dir.set(Math.cos(ang), Math.sin(ang) * 0.9, 0.42).normalize();
      const u = sky.material.uniforms;
      u.sunPosition.value.copy(dir);
      u.turbidity.value = lerp(2.2, 6, smooth(0.35, 0, Math.abs(dir.y)));
      u.rayleigh.value = lerp(1.1, 2.6, smooth(0.3, 0, dir.y));
      u.mieCoefficient.value = 0.004;
      u.mieDirectionalG.value = 0.82;
      const up = dir.y >= 0;
      const sunI = smooth(0, 0.16, dir.y) * 4.6, moonI = smooth(0.02, 0.25, -dir.y) * 0.28;
      light.intensity = up ? sunI : moonI;
      light.color.copy(up ? tmpColor(sunLow, sunHigh, smooth(0.05, 0.5, dir.y)) : moon);
      // snap the shadow frustum to the camera target to avoid shimmering
      const tx = Math.round(controls.target.x / 8) * 8, tz = Math.round(controls.target.z / 8) * 8;
      light.target.position.set(tx, 0, tz);
      tmp.copy(dir).multiplyScalar(up ? 1 : -1);
      if (tmp.y < 0.12) { tmp.y = 0.12; tmp.normalize(); }
      light.position.set(tx, 0, tz).addScaledVector(tmp, 1100);
      hemi.intensity = lerp(0.45, 0.07, night);
      const dusk = smooth(0.3, 0.02, Math.abs(dir.y)) * (1 - night);
      scene.fog.color.copy(cDay).lerp(cDusk, dusk).lerp(cNight, night);
      scene.fog.density = lerp(0.00042, 0.0003, night) + dusk * 0.00012;
      renderer.toneMappingExposure = lerp(0.42, 0.85, night);
      stars.material.opacity = night * 0.9;
      stars.position.copy(camera.position);
      if (Math.abs(t - lastEnv) > 0.15) {
        lastEnv = t;
        const rt = pmrem.fromScene(envScene);
        if (envRT) envRT.dispose();
        envRT = rt;
        scene.environment = rt.texture;
      }
    },
  };
}
const _c = { r: 0, g: 0, b: 0 };
function tmpColor(a, b, t) {
  _c.r = a.r + (b.r - a.r) * t; _c.g = a.g + (b.g - a.g) * t; _c.b = a.b + (b.b - a.b) * t;
  return _c;
}
```

### `src/effects/index.js`
```js
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { fbm, smooth, lerp } from '../core/rng.js';

export default function create(ctx) {
  const { THREE, scene, camera, renderer, world, events } = ctx;
  let composer, bloom, clouds;
  return {
    name: 'effects',
    showcase: { cam: { pos: [-430, 120, -400], target: [0, 60, 0] }, time: 21 },
    init() {
      const size = renderer.getDrawingBufferSize(new THREE.Vector2());
      const rt = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 4 });
      composer = new EffectComposer(renderer, rt);
      composer.addPass(new RenderPass(scene, camera));
      bloom = new UnrealBloomPass(new THREE.Vector2(size.x, size.y), 0.2, 0.55, 0.92);
      composer.addPass(bloom);
      composer.addPass(new OutputPass());
      events.on('resize', () => composer.setSize(innerWidth, innerHeight));
      ctx.render = () => composer.render();

      const S = 256, c = document.createElement('canvas');
      c.width = c.height = S;
      const g = c.getContext('2d'), img = g.createImageData(S, S);
      for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
        const n = fbm(x / 42, y / 42, world.seed + 77, 6), i = (y * S + x) * 4;
        img.data[i] = img.data[i + 1] = img.data[i + 2] = 255;
        img.data[i + 3] = smooth(0.5, 0.78, n) * 235;
      }
      g.putImageData(img, 0, 0);
      const tex = new THREE.CanvasTexture(c);
      tex.wrapS = tex.wrapT = THREE.MirroredRepeatWrapping;
      tex.repeat.set(3, 3);
      clouds = new THREE.Mesh(
        new THREE.PlaneGeometry(16000, 16000).rotateX(Math.PI / 2),
        new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, fog: false, side: THREE.DoubleSide }),
      );
      clouds.position.y = 1500;
      clouds.renderOrder = 1;
      scene.add(clouds);
    },
    update(dt) {
      const n = world.night;
      bloom.strength = lerp(0.12, 0.75, n);
      clouds.material.map.offset.x += dt * 0.0012;
      const dusk = smooth(0.35, 0, Math.abs(Math.sin(((world.time - 6) / 12) * Math.PI))) * (1 - n);
      clouds.material.color.setRGB(lerp(2.4, 0.03, n), lerp(2.4, 0.035, n) * (1 - dusk * 0.35), lerp(2.5, 0.05, n) * (1 - dusk * 0.6));
      clouds.material.opacity = lerp(0.85, 0.5, n);
    },
  };
}
```

### `src/roads/index.js`
```js
import { N, CELL, GROUND } from '../core/world.js';
import { mulberry32 } from '../core/rng.js';
import { canvasTex, speckle } from '../core/tex.js';

function tile(mask) {
  return canvasTex(256, (g, s) => {
    const rng = mulberry32(900 + mask), sw = 36, a = sw, b = s - sw, arms = [mask & 1, mask & 2, mask & 4, mask & 8];
    const n = arms.filter(Boolean).length;
    g.fillStyle = '#8c8a84'; g.fillRect(0, 0, s, s);
    g.strokeStyle = 'rgba(0,0,0,.13)'; g.lineWidth = 1;
    for (let i = 0; i <= s; i += 16) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, s); g.moveTo(0, i); g.lineTo(s, i); g.stroke(); }
    const shape = (o, col) => {
      g.fillStyle = col;
      g.fillRect(a - o, a - o, b - a + 2 * o, b - a + 2 * o);
      if (arms[0]) g.fillRect(a - o, 0, b - a + 2 * o, a);
      if (arms[2]) g.fillRect(a - o, b, b - a + 2 * o, a);
      if (arms[1]) g.fillRect(b, a - o, a, b - a + 2 * o);
      if (arms[3]) g.fillRect(0, a - o, a, b - a + 2 * o);
    };
    shape(4, '#b5b2a9');
    shape(0, '#28292c');
    speckle(g, s, rng, 5000, 0.07);
    for (let i = 0; i < 5; i++) { g.fillStyle = 'rgba(15,15,16,.18)'; g.fillRect(a + rng() * (b - a - 30), a + rng() * (b - a - 30), 10 + rng() * 40, 4 + rng() * 22); }
    g.fillStyle = 'rgba(232,230,220,.88)';
    const h = s / 2;
    if (n <= 2) {
      for (let y = 6; y < h; y += 36) { if (arms[0]) g.fillRect(h - 2, y, 4, 18); if (arms[2]) g.fillRect(h - 2, s - y - 18, 4, 18); }
      for (let x = 6; x < h; x += 36) { if (arms[1]) g.fillRect(s - x - 18, h - 2, 18, 4); if (arms[3]) g.fillRect(x, h - 2, 18, 4); }
    } else {
      for (let k = a + 8; k < b - 8; k += 14) {
        if (arms[0]) g.fillRect(k, 6, 7, 22);
        if (arms[2]) g.fillRect(k, s - 28, 7, 22);
        if (arms[1]) g.fillRect(s - 28, k, 22, 7);
        if (arms[3]) g.fillRect(6, k, 22, 7);
      }
    }
  });
}

export default function create(ctx) {
  const { THREE, scene, world, events } = ctx;
  const group = new THREE.Group(), mats = [], dummy = new THREE.Object3D();
  const plane = new THREE.PlaneGeometry(CELL, CELL).rotateX(-Math.PI / 2);
  const box = new THREE.BoxGeometry(1, 1, 1);
  let deckMat, dirty = true;
  function rebuild() {
    for (const m of group.children) m.dispose();
    group.clear();
    const buckets = Array.from({ length: 16 }, () => []), decks = [];
    for (let z = 0; z < N; z++) for (let x = 0; x < N; x++) {
      if (!world.road[z * N + x]) continue;
      buckets[world.roadMask(x, z)].push(x, z);
      if (world.cellHeight(x, z) < GROUND - 0.3) decks.push(x, z);
    }
    buckets.forEach((b, mask) => {
      if (!b.length) return;
      const m = new THREE.InstancedMesh(plane, mats[mask], b.length / 2);
      for (let i = 0; i < b.length; i += 2) {
        dummy.position.set(world.wx(b[i]), GROUND + 0.08, world.wx(b[i + 1]));
        dummy.scale.set(1, 1, 1); dummy.updateMatrix();
        m.setMatrixAt(i / 2, dummy.matrix);
      }
      m.receiveShadow = true; m.frustumCulled = false;
      group.add(m);
    });
    if (decks.length) {
      const m = new THREE.InstancedMesh(box, deckMat, decks.length);
      for (let i = 0; i < decks.length; i += 2) {
        const x = world.wx(decks[i]), z = world.wx(decks[i + 1]);
        dummy.position.set(x, GROUND - 0.55, z); dummy.scale.set(CELL + 0.6, 1.2, CELL + 0.02); dummy.updateMatrix();
        m.setMatrixAt(i, dummy.matrix);
        const pier = (decks[i + 1] % 3 === 0) ? 1.6 : 0.001;
        dummy.position.set(x, -3, z); dummy.scale.set(CELL - 2, 9, pier); dummy.updateMatrix();
        m.setMatrixAt(i + 1, dummy.matrix);
      }
      m.castShadow = m.receiveShadow = true; m.frustumCulled = false;
      group.add(m);
    }
  }
  return {
    name: 'roads',
    showcase: { cam: { pos: [-30, 26, 44], target: [0, 2, 0] }, time: 16.5 },
    init() {
      for (let m = 0; m < 16; m++) mats.push(new THREE.MeshStandardMaterial({ map: tile(m), roughness: 0.86, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }));
      const rng = world.rng(41);
      deckMat = new THREE.MeshStandardMaterial({ map: canvasTex(256, (g, s) => { g.fillStyle = '#9a9891'; g.fillRect(0, 0, s, s); speckle(g, s, rng, 5000, 0.08); }), roughness: 0.9 });
      scene.add(group);
      events.on('roads:changed', () => { dirty = true; });
    },
    update() { if (dirty) { dirty = false; rebuild(); } },
  };
}
```

### `src/zoning/index.js`
```js
import { N, CELL, GROUND } from '../core/world.js';

export default function create(ctx) {
  const { THREE, scene, world, events } = ctx;
  const COL = [0, 0x35c46a, 0x3d8bff, 0xf2b632, 0xb46cff, 0x1f8f4a].map((c) => new THREE.Color(c));
  const dummy = new THREE.Object3D();
  let mesh, dirty = true;
  function rebuild() {
    let n = 0;
    for (let z = 0; z < N; z++) for (let x = 0; x < N; x++) {
      const k = z * N + x, zn = world.zone[k];
      if (!zn || world.road[k] || world.bldg[k]) continue;
      dummy.position.set(world.wx(x), GROUND + 0.16, world.wx(z)); dummy.updateMatrix();
      mesh.setMatrixAt(n, dummy.matrix);
      mesh.setColorAt(n++, COL[zn]);
    }
    mesh.count = n;
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }
  return {
    name: 'zoning',
    showcase: { cam: { pos: [-70, 80, 90], target: [0, 2, 0] }, time: 12 },
    init() {
      mesh = new THREE.InstancedMesh(
        new THREE.PlaneGeometry(CELL * 0.92, CELL * 0.92).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.45, depthWrite: false, toneMapped: false }), N * N,
      );
      mesh.count = 0; mesh.frustumCulled = false;
      mesh.visible = ctx.params.get('showcase') === 'zoning';
      scene.add(mesh);
      for (const e of ['zones:changed', 'roads:changed', 'buildings:changed']) events.on(e, () => { dirty = true; });
      events.on('tool:changed', (t) => { mesh.visible = t.startsWith('zone') || t === 'bulldoze'; });
    },
    update() { if (dirty && mesh.visible) { dirty = false; rebuild(); } },
  };
}
```

### `src/buildings/index.js`
```js
import { CELL, GROUND } from '../core/world.js';
import { CATALOG } from '../core/catalog.js';
import { mulberry32 } from '../core/rng.js';
import { canvasTex, speckle } from '../core/tex.js';

const F = {
  plaster: { wall: '#cfc6b4', g0: '#1d2730', g1: '#3c4c5a', ww: 0.5, wh: 0.56, rough: 0.9, metal: 0, lit: 0.45 },
  brick: { wall: '#7d4a37', g0: '#1b232b', g1: '#36444f', ww: 0.46, wh: 0.58, rough: 0.92, metal: 0, lit: 0.5 },
  glass: { wall: '#33414d', g0: '#132230', g1: '#3f6078', ww: 0.9, wh: 0.84, rough: 0.16, metal: 0.75, lit: 0.4 },
  glass2: { wall: '#596168', g0: '#101c24', g1: '#35525f', ww: 0.84, wh: 0.7, rough: 0.2, metal: 0.7, lit: 0.55 },
  metal: { wall: '#7f878d', g0: '#20262c', g1: '#39424a', ww: 0.3, wh: 0.22, rough: 0.5, metal: 0.65, lit: 0.25 },
  shop: { wall: '#b3a590', g0: '#18222a', g1: '#405563', ww: 0.86, wh: 0.62, rough: 0.8, metal: 0, lit: 0.9 },
};

export default function create(ctx) {
  const { THREE, scene, world, events } = ctx;
  const meshes = [], mats = [], dummy = new THREE.Object3D(), col = new THREE.Color();
  let roofs, dirty = true;
  function facade(kind, seed) {
    const p = F[kind], rng = mulberry32(seed), G = 8, cs = 64, rects = [];
    const map = canvasTex(512, (g, s) => {
      g.fillStyle = p.wall; g.fillRect(0, 0, s, s);
      speckle(g, s, rng, 7000, 0.05);
      if (kind === 'brick') { g.strokeStyle = 'rgba(0,0,0,.2)'; for (let y = 0; y < s; y += 8) { g.beginPath(); g.moveTo(0, y); g.lineTo(s, y); g.stroke(); } }
      if (kind === 'metal') { g.strokeStyle = 'rgba(0,0,0,.16)'; for (let x = 0; x < s; x += 8) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, s); g.stroke(); } }
      for (let j = 0; j < G; j++) for (let i = 0; i < G; i++) {
        const w = cs * p.ww, h = cs * p.wh, x = i * cs + (cs - w) / 2, y = j * cs + (cs - h) * 0.4;
        const gr = g.createLinearGradient(x, y, x + w * 0.4, y + h);
        gr.addColorStop(0, p.g1); gr.addColorStop(1, p.g0);
        g.fillStyle = gr; g.fillRect(x, y, w, h);
        g.strokeStyle = 'rgba(255,255,255,.14)'; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
        g.fillStyle = 'rgba(0,0,0,.22)'; g.fillRect(x, y + h, w, 2);
        rects.push([x, y, w, h]);
      }
      g.fillStyle = 'rgba(0,0,0,.22)';
      for (let j = 1; j <= G; j++) g.fillRect(0, j * cs - 2, s, 2);
    });
    const em = canvasTex(512, (g, s) => {
      g.fillStyle = '#000'; g.fillRect(0, 0, s, s);
      for (const [x, y, w, h] of rects) {
        if (rng() > p.lit) continue;
        const b = 0.3 + rng() * 0.7;
        g.fillStyle = rng() < 0.72 ? `rgba(255,${(185 + rng() * 45) | 0},${(105 + rng() * 60) | 0},${b})` : `rgba(205,228,255,${b})`;
        g.fillRect(x, y, w, h);
      }
    });
    return new THREE.MeshStandardMaterial({ map, emissiveMap: em, emissive: 0xffffff, emissiveIntensity: 0, roughness: p.rough, metalness: p.metal });
  }
  function rebuild() {
    const counts = meshes.map(() => 0);
    let hr = 0;
    for (const b of world.buildings.values()) {
      const c = CATALOG[b.cls], m = meshes[b.cls], off = c.cells === 2 ? CELL / 2 : 0, i = counts[b.cls];
      if (i >= m.instanceMatrix.count) continue;
      counts[b.cls]++;
      dummy.position.set(world.wx(b.cx) + off, GROUND, world.wx(b.cz) + off); dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
      m.setColorAt(i, col.setHSL(0.06 + b.tint * 0.08, 0.1 + b.tint * 0.1, 0.72 + b.tint * 0.26));
      if (b.cls === 0 && hr < roofs.instanceMatrix.count) {
        dummy.position.y = GROUND + c.h; dummy.updateMatrix();
        roofs.setMatrixAt(hr, dummy.matrix);
        roofs.setColorAt(hr++, col.setHSL(0.03 + b.tint * 0.04, 0.45, 0.2 + b.tint * 0.12));
      }
    }
    meshes.forEach((m, i) => { m.count = counts[i]; m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; });
    roofs.count = hr; roofs.instanceMatrix.needsUpdate = true;
    if (roofs.instanceColor) roofs.instanceColor.needsUpdate = true;
  }
  return {
    name: 'buildings',
    showcase: { cam: { pos: [-110, 55, -120], target: [0, 22, 0] }, time: 19.4 },
    init() {
      const rng = world.rng(51);
      const roofMat = new THREE.MeshStandardMaterial({ map: canvasTex(256, (g, s) => { g.fillStyle = '#5b5d60'; g.fillRect(0, 0, s, s); speckle(g, s, rng, 7000, 0.12); g.strokeStyle = 'rgba(210,210,205,.5)'; g.lineWidth = 6; g.strokeRect(3, 3, s - 6, s - 6); }), roughness: 0.95 });
      const byKind = {};
      CATALOG.forEach((c, ci) => {
        const side = (byKind[c.f] ??= facade(c.f, world.seed + c.f.length * 31 + c.f.charCodeAt(0)));
        mats.push(side);
        const geo = new THREE.BoxGeometry(c.w, c.h, c.d).translate(0, c.h / 2, 0), uv = geo.attributes.uv;
        for (let i = 0; i < uv.count; i++) { if (i >= 8 && i < 16) continue; uv.setXY(i, (uv.getX(i) * c.bays) / 8 + ci * 0.125, (uv.getY(i) * c.fl) / 8); }
        const m = new THREE.InstancedMesh(geo, [side, side, roofMat, roofMat, side, side], c.cells === 2 ? 1500 : 6000);
        m.count = 0; m.castShadow = m.receiveShadow = true; m.frustumCulled = false;
        meshes.push(m); scene.add(m);
      });
      roofs = new THREE.InstancedMesh(new THREE.ConeGeometry(4.65, 2.7, 4).rotateY(Math.PI / 4).translate(0, 1.35, 0), new THREE.MeshStandardMaterial({ roughness: 0.85 }), 6000);
      roofs.count = 0; roofs.castShadow = true; roofs.frustumCulled = false;
      scene.add(roofs);
      events.on('buildings:changed', () => { dirty = true; });
    },
    update() {
      if (dirty) { dirty = false; rebuild(); }
      const e = world.night * 2.4;
      for (const k of new Set(mats)) k.emissiveIntensity = e;
    },
  };
}
```

### `src/props/index.js`
```js
import { N, GROUND, ZONE } from '../core/world.js';
import { fbm, hash2 } from '../core/rng.js';
import { glowTex } from '../core/tex.js';

export default function create(ctx) {
  const { THREE, scene, world, events } = ctx;
  const dummy = new THREE.Object3D(), wild = [], col = new THREE.Color();
  let trunks, crowns, conifers, poles, lamps, pools, lampMat, dirty = true;
  const inst = (geo, mat, n, shadow = true) => { const m = new THREE.InstancedMesh(geo, mat, n); m.count = 0; m.castShadow = shadow; m.receiveShadow = shadow; m.frustumCulled = false; scene.add(m); return m; };
  function put(m, i, x, y, z, s = 1, sy = s, r = 0) { dummy.position.set(x, y, z); dummy.rotation.set(0, r, 0); dummy.scale.set(s, sy, s); dummy.updateMatrix(); m.setMatrixAt(i, dummy.matrix); }
  function rebuild() {
    let nt = 0, nc = 0, nf = 0;
    const tree = (x, z, y, s, h) => {
      if (nt >= trunks.instanceMatrix.count) return;
      put(trunks, nt++, x, y, z, s, s, h * 6);
      if (y > 34 || h > 0.8) { put(conifers, nf, x, y + 1.2 * s, z, s, s * (0.9 + h * 0.4), h * 6); conifers.setColorAt(nf++, col.setHSL(0.33, 0.4, 0.1 + h * 0.06)); }
      else { put(crowns, nc, x, y + 4.2 * s, z, s, s * (0.95 + h * 0.4), h * 6); crowns.setColorAt(nc++, col.setHSL(0.24 + h * 0.08, 0.45, 0.13 + h * 0.08)); }
    };
    for (const t of wild) {
      const cx = world.cell(t.x), cz = world.cell(t.z);
      if (world.inb(cx, cz)) { const k = cz * N + cx; if (world.road[k] || world.bldg[k] || world.zone[k]) continue; }
      tree(t.x, t.z, t.y, t.s, t.h);
    }
    let np = 0;
    for (let z = 0; z < N; z++) for (let x = 0; x < N; x++) {
      const k = z * N + x;
      if (world.zone[k] === ZONE.PARK && !world.road[k]) for (let j = 0; j < 2; j++) {
        const h = hash2(x * 3 + j, z * 5, 7), h2 = hash2(x, z * 3 + j, 8);
        tree(world.wx(x) + (h - 0.5) * 6.5, world.wx(z) + (h2 - 0.5) * 6.5, GROUND, 0.8 + h * 0.5, h2 * 0.7);
      }
      if (world.road[k] && (x * 7 + z * 13) % 4 === 0 && np < poles.instanceMatrix.count && world.cellHeight(x, z) > GROUND - 0.3) {
        const px = world.wx(x) + 3.45, pz = world.wx(z) + 3.45;
        put(poles, np, px, GROUND, pz); put(lamps, np, px, GROUND + 7.1, pz); put(pools, np, px - 1.2, GROUND + 0.2, pz - 1.2);
        np++;
      }
    }
    for (const [m, n] of [[trunks, nt], [crowns, nc], [conifers, nf], [poles, np], [lamps, np], [pools, np]]) {
      m.count = n; m.instanceMatrix.needsUpdate = true;
      if (m.instanceColor) m.instanceColor.needsUpdate = true;
    }
  }
  return {
    name: 'props',
    showcase: { cam: { pos: [-40, 18, 52], target: [0, 5, 0] }, time: 20.5 },
    init() {
      const rng = world.rng(61);
      for (let i = 0; i < 26000 && wild.length < 9000; i++) {
        const x = (rng() - 0.5) * 1900, z = (rng() - 0.5) * 1900, y = world.height(x, z);
        if (y < 1.7) continue;
        const flat = Math.abs(y - GROUND) < 0.6, n = fbm(x / 90, z / 90, world.seed + 5, 3);
        if (n < (flat ? 0.56 : 0.4)) continue;
        if (Math.abs(world.height(x + 3, z) - y) + Math.abs(world.height(x, z + 3) - y) > 3.2) continue;
        wild.push({ x, z, y: y - 0.2, s: 0.75 + rng() * 0.8, h: rng() });
      }
      const crownGeo = new THREE.IcosahedronGeometry(2.6, 2), p = crownGeo.attributes.position;
      for (let i = 0; i < p.count; i++) { const k = 0.82 + fbm(p.getX(i) * 0.9 + 5, p.getY(i) * 0.9 + p.getZ(i) * 0.7, 3, 3) * 0.4; p.setXYZ(i, p.getX(i) * k, p.getY(i) * k * 1.15, p.getZ(i) * k); }
      crownGeo.computeVertexNormals();
      const leaf = new THREE.MeshStandardMaterial({ roughness: 0.92, metalness: 0 });
      trunks = inst(new THREE.CylinderGeometry(0.16, 0.3, 3.4, 6).translate(0, 1.7, 0), new THREE.MeshStandardMaterial({ color: 0x2e2218, roughness: 1 }), 12000);
      crowns = inst(crownGeo, leaf, 12000);
      conifers = inst(new THREE.ConeGeometry(2, 8.5, 8).translate(0, 4.25, 0), leaf, 12000);
      poles = inst(new THREE.CylinderGeometry(0.07, 0.1, 7, 6).translate(0, 3.5, 0), new THREE.MeshStandardMaterial({ color: 0x30343a, roughness: 0.5, metalness: 0.8 }), 4000);
      lampMat = new THREE.MeshStandardMaterial({ color: 0x222222, emissive: 0xffc98a, emissiveIntensity: 0 });
      lamps = inst(new THREE.SphereGeometry(0.22, 10, 8), lampMat, 4000, false);
      pools = inst(new THREE.PlaneGeometry(20, 20).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: glowTex('rgba(255,196,128,1)'), color: 0xffc080, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }), 4000, false);
      for (const e of ['roads:changed', 'zones:changed', 'buildings:changed']) events.on(e, () => { dirty = true; });
    },
    update() {
      if (dirty) { dirty = false; rebuild(); }
      const n = world.night;
      lampMat.emissiveIntensity = n * 9;
      pools.material.opacity = n * 0.5;
      pools.visible = n > 0.01;
    },
  };
}
```

### `src/traffic/index.js`
```js
import { N, CELL, GROUND } from '../core/world.js';
import { smooth, lerp } from '../core/rng.js';
import { glowTex } from '../core/tex.js';

const DX = [0, 1, 0, -1], DZ = [-1, 0, 1, 0], MAX = 600, GAP = 0.72;

export default function create(ctx) {
  const { THREE, scene, world, events } = ctx;
  const rng = world.rng(71), cars = [], tail = new Map(), dummy = new THREE.Object3D(), col = new THREE.Color();
  const PAINT = [0xd9dcdf, 0x16181b, 0x7a8087, 0x8c1a1a, 0x1c3d6e, 0xe7e2d2, 0x2f4f3a, 0xc9a227];
  let parts = [], headMat, tailMat, beamMat, roadCells = 0, recount = true;
  function place(c) {
    for (let k = 0; k < 30; k++) {
      const x = (rng() * N) | 0, z = (rng() * N) | 0;
      if (!world.isRoad(x, z)) continue;
      const m = world.roadMask(x, z), ds = [0, 1, 2, 3].filter((d) => m & (1 << d));
      if (!ds.length) continue;
      const d = ds[(rng() * ds.length) | 0];
      Object.assign(c, { x, z, d, pd: d, t: rng() * 0.9, wait: 0, ahead: null, seg: (z * N + x) * 4 + d });
      return true;
    }
    return false;
  }
  function step(c, dt) {
    const nx = c.x + DX[c.d], nz = c.z + DZ[c.d];
    if (!world.isRoad(c.x, c.z) || !world.isRoad(nx, nz)) { place(c); return; }
    const lead = c.ahead;
    if (lead && lead.seg === c.seg && lead.t >= c.t && lead.t - c.t < GAP) { c.wait += dt; return; }
    c.t += (c.v * dt) / CELL;
    if (c.t < 1) return;
    const m = world.roadMask(nx, nz), back = (c.d + 2) % 4;
    let ds = [0, 1, 2, 3].filter((d) => m & (1 << d) && d !== back);
    if (!ds.length) ds = [back];
    const nd = ds.includes(c.d) && rng() < 0.6 ? c.d : ds[(rng() * ds.length) | 0];
    const seg = (nz * N + nx) * 4 + nd, last = tail.get(seg);
    if (last && last !== c && last.seg === seg && last.t < GAP && c.wait < 6) { c.t = 1; c.wait += dt; return; }
    c.x = nx; c.z = nz; c.pd = c.d; c.d = nd; c.t = 0; c.seg = seg; c.wait = 0;
    c.ahead = last && last !== c && last.seg === seg ? last : null;
    tail.set(seg, c);
  }
  return {
    name: 'traffic',
    showcase: { cam: { pos: [-22, 14, 30], target: [0, 2, 0] }, time: 20.2 },
    init() {
      const mk = (geo, mat, shadow) => { const m = new THREE.InstancedMesh(geo, mat, MAX); m.count = 0; m.castShadow = shadow; m.frustumCulled = false; scene.add(m); return m; };
      headMat = new THREE.MeshStandardMaterial({ color: 0x555555, emissive: 0xfff2d8, emissiveIntensity: 0.4 });
      tailMat = new THREE.MeshStandardMaterial({ color: 0x330000, emissive: 0xff1a10, emissiveIntensity: 0.5 });
      beamMat = new THREE.MeshBasicMaterial({ map: glowTex('rgba(255,244,220,1)'), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -6, polygonOffsetUnits: -6 });
      parts = [
        mk(new THREE.BoxGeometry(1.8, 0.62, 4.3).translate(0, 0.58, 0), new THREE.MeshPhysicalMaterial({ roughness: 0.32, metalness: 0.55, clearcoat: 1, clearcoatRoughness: 0.08 }), true),
        mk(new THREE.BoxGeometry(1.6, 0.52, 2.2).translate(0, 1.14, -0.25), new THREE.MeshStandardMaterial({ color: 0x0c1014, roughness: 0.08, metalness: 0.9 }), true),
        mk(new THREE.BoxGeometry(1.5, 0.14, 0.06).translate(0, 0.66, 2.16), headMat, false),
        mk(new THREE.BoxGeometry(1.5, 0.12, 0.06).translate(0, 0.7, -2.16), tailMat, false),
        mk(new THREE.PlaneGeometry(4.5, 11).rotateX(-Math.PI / 2).translate(0, 0.06, 6.5), beamMat, false),
      ];
      events.on('roads:changed', () => { recount = true; });
    },
    update(dt) {
      if (recount) { recount = false; roadCells = 0; for (let i = 0; i < N * N; i++) if (world.road[i]) roadCells++; }
      const target = Math.min(MAX, Math.floor(roadCells / 3), 30 + Math.floor(world.stats.pop / 12));
      if (cars.length < target) { const c = { v: 8 + rng() * 5, paint: (rng() * PAINT.length) | 0 }; if (place(c)) cars.push(c); }
      else if (cars.length > target) cars.pop();
      const sdt = dt * Math.min(world.speed, 3), body = parts[0];
      for (let i = 0; i < cars.length; i++) {
        const c = cars[i];
        if (sdt > 0) step(c, sdt);
        const s = smooth(0, 0.42, c.t), a0 = Math.atan2(DX[c.pd], DZ[c.pd]), a1 = Math.atan2(DX[c.d], DZ[c.d]);
        const da = ((a1 - a0 + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
        const ox = lerp(-DZ[c.pd], -DZ[c.d], s) * 1.45, oz = lerp(DX[c.pd], DX[c.d], s) * 1.45;
        dummy.position.set(world.wx(c.x) + DX[c.d] * c.t * CELL + ox, GROUND + 0.1, world.wx(c.z) + DZ[c.d] * c.t * CELL + oz);
        dummy.rotation.set(0, a0 + da * s, 0); dummy.updateMatrix();
        for (const p of parts) p.setMatrixAt(i, dummy.matrix);
        body.setColorAt(i, col.setHex(PAINT[c.paint]));
      }
      for (const p of parts) { p.count = cars.length; p.instanceMatrix.needsUpdate = true; }
      if (body.instanceColor) body.instanceColor.needsUpdate = true;
      const n = world.night;
      headMat.emissiveIntensity = 0.4 + n * 9;
      tailMat.emissiveIntensity = 0.5 + n * 5;
      beamMat.opacity = n * 0.4;
      parts[4].visible = n > 0.01;
    },
  };
}
```

### `src/simulation/index.js`
```js
import { N, ZONE } from '../core/world.js';
import { CATALOG } from '../core/catalog.js';
import { clamp } from '../core/rng.js';

export default function create(ctx) {
  const { world, events } = ctx;
  const rng = world.rng(11), byZone = {};
  CATALOG.forEach((c, i) => (byZone[c.z] ??= []).push(i));
  let acc = 0;
  const free = (x, z, zn) => world.inb(x, z) && world.zone[z * N + x] === zn && !world.bldg[z * N + x] && !world.road[z * N + x] && world.buildable(x, z);
  const roadNear = (x, z) => { for (let j = -2; j <= 2; j++) for (let i = -2; i <= 2; i++) if (world.isRoad(x + i, z + j)) return true; return false; };
  function tryBuild(x, z) {
    const zn = world.zone[z * N + x];
    if (zn < 1 || zn > 4 || !free(x, z, zn) || !roadNear(x, z)) return false;
    const list = byZone[zn], big = free(x + 1, z, zn) && free(x, z + 1, zn) && free(x + 1, z + 1, zn);
    const dens = 1 - Math.hypot(x - N / 2, z - N / 2) / 34 + rng() * 0.3 - 0.15;
    let ci;
    if (zn === ZONE.IND) ci = big && rng() < 0.6 ? list[1] : list[0];
    else if (zn === ZONE.OFF) ci = big && dens > 0.55 ? list[1] : list[0];
    else ci = big && dens > 0.7 ? list[2] : dens > 0.42 ? list[1] : list[0];
    world.addBuilding({ cx: x, cz: z, cls: ci, tint: rng() });
    return true;
  }
  function census() {
    const s = world.stats;
    let pop = 0, jc = 0, ji = 0, jo = 0;
    for (const b of world.buildings.values()) { const c = CATALOG[b.cls]; pop += c.pop; if (c.z === 2) jc += c.jobs; else if (c.z === 3) ji += c.jobs; else if (c.z === 4) jo += c.jobs; }
    const jobs = jc + ji + jo, work = pop * 0.5, d = s.demand;
    s.pop = pop; s.jobs = jobs;
    d.r = clamp(0.35 + (jobs - work) / (work + 300), 0, 1);
    d.c = clamp(0.1 + (pop * 0.2 - jc) / (jc + 150), 0, 1);
    d.i = clamp(0.1 + (pop * 0.14 - ji) / (ji + 150), 0, 1);
    d.o = clamp(0.05 + (pop * 0.16 - jo) / (jo + 150), 0, 1);
    return s;
  }
  function tick() {
    const s = census(), d = s.demand, dz = [0, d.r, d.c, d.i, d.o];
    let roads = 0;
    for (let i = 0; i < N * N; i++) if (world.road[i]) roads++;
    s.money += Math.round(s.pop * 0.35 + s.jobs * 0.25 - roads * 0.15);
    let built = 0;
    for (let k = 0; k < 80 && built < 3; k++) {
      const x = (rng() * N) | 0, z = (rng() * N) | 0, zn = world.zone[z * N + x];
      if (zn >= 1 && zn <= 4 && rng() < dz[zn] + 0.05 && tryBuild(x, z)) built++;
    }
    if (built) events.emit('buildings:changed');
    events.emit('sim:tick', s);
  }
  return {
    name: 'simulation',
    showcase: { cam: { pos: [-110, 90, 120], target: [0, 10, 0] }, time: 15 },
    api: {
      // instantly develop every eligible zoned cell (used by the demo city and showcases)
      grow(fill = 0.94) {
        for (let z = 0; z < N; z++) for (let x = 0; x < N; x++) if (rng() < fill) tryBuild(x, z);
        census();
        events.emit('buildings:changed');
        events.emit('sim:tick', world.stats);
      },
    },
    init() { census(); },
    update(dt) {
      if (!world.timeLocked) world.time = (world.time + (dt * world.speed * 24) / 600) % 24;
      acc += dt * world.speed;
      for (let k = 0; acc >= 0.5 && k < 8; k++) { acc -= 0.5; tick(); }
      if (acc > 4) acc = 0;
    },
  };
}
```

### `src/tools/index.js`
```js
import { N, CELL, GROUND } from '../core/world.js';

export default function create(ctx) {
  const { THREE, scene, camera, renderer, controls, world, events } = ctx;
  const dom = renderer.domElement, ray = new THREE.Raycaster(), ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), -GROUND);
  const v = new THREE.Vector3(), m = new THREE.Vector2();
  const TINT = { road: 0xffffff, zone1: 0x35c46a, zone2: 0x3d8bff, zone3: 0xf2b632, zone4: 0xb46cff, zone5: 0x1f8f4a, bulldoze: 0xff4433 };
  let tool = 'none', start = null, preview;
  function pick(e) {
    const r = dom.getBoundingClientRect();
    m.set(((e.clientX - r.left) / r.width) * 2 - 1, (-(e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(m, camera);
    if (!ray.ray.intersectPlane(ground, v)) return null;
    const x = world.cell(v.x), z = world.cell(v.z);
    return world.inb(x, z) ? { x, z } : null;
  }
  function span(a, b) {
    let x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x), z0 = Math.min(a.z, b.z), z1 = Math.max(a.z, b.z);
    if (tool === 'road') { if (x1 - x0 >= z1 - z0) z0 = z1 = a.z; else x0 = x1 = a.x; }
    return { x0, x1, z0, z1 };
  }
  function show(a, b) {
    const s = span(a, b);
    preview.visible = true;
    preview.material.color.setHex(TINT[tool] || 0xffffff);
    preview.scale.set((s.x1 - s.x0 + 1) * CELL, 0.5, (s.z1 - s.z0 + 1) * CELL);
    preview.position.set((world.wx(s.x0) + world.wx(s.x1)) / 2, GROUND + 0.3, (world.wx(s.z0) + world.wx(s.z1)) / 2);
  }
  function apply(a, b) {
    const s = span(a, b), st = world.stats;
    let roads = false, zones = false, bld = false;
    for (let z = s.z0; z <= s.z1; z++) for (let x = s.x0; x <= s.x1; x++) {
      const k = z * N + x, h = world.cellHeight(x, z);
      if (tool === 'road') {
        if (world.road[k] || world.bldg[k] || h > GROUND + 0.6 || st.money < 40) continue;
        world.road[k] = 1; world.zone[k] = 0; st.money -= h < GROUND - 0.3 ? 400 : 40; roads = zones = true;
      } else if (tool.startsWith('zone')) {
        if (world.road[k] || world.bldg[k] || !world.buildable(x, z)) continue;
        world.zone[k] = Number(tool.slice(4)); zones = true;
      } else if (tool === 'bulldoze') {
        if (world.bldg[k]) { world.removeBuilding(world.bldg[k]); bld = true; }
        if (world.road[k]) { world.road[k] = 0; roads = true; }
        if (world.zone[k]) { world.zone[k] = 0; zones = true; }
      }
    }
    if (roads) events.emit('roads:changed');
    if (zones) events.emit('zones:changed');
    if (bld) events.emit('buildings:changed');
  }
  function set(t) {
    tool = t; start = null; preview.visible = false;
    controls.mouseButtons.LEFT = t === 'none' ? THREE.MOUSE.PAN : null;
    events.emit('tool:changed', t);
  }
  return {
    name: 'tools',
    showcase: { cam: { pos: [-60, 60, 80], target: [0, 2, 0] }, time: 11 },
    api: { set, get: () => tool },
    init() {
      preview = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.35, depthWrite: false, toneMapped: false }));
      preview.visible = false;
      scene.add(preview);
      events.on('tool:set', set);
      dom.addEventListener('pointerdown', (e) => { if (e.button === 0 && tool !== 'none') { start = pick(e); if (start) show(start, start); } });
      dom.addEventListener('pointermove', (e) => { if (tool === 'none') return; const c = pick(e); if (c) show(start || c, c); });
      addEventListener('pointerup', (e) => { if (e.button !== 0 || !start) return; const c = pick(e) || start; apply(start, c); start = null; });
      addEventListener('keydown', (e) => { if (e.code === 'Escape') set('none'); });
    },
  };
}
```

### `src/ui/index.js`
```js
const TOOLS = [['none', 'Inspect', '1'], ['road', 'Road', '2'], ['zone1', 'Residential', '3'], ['zone2', 'Commercial', '4'], ['zone3', 'Industrial', '5'], ['zone4', 'Office', '6'], ['zone5', 'Park', '7'], ['bulldoze', 'Bulldoze', '8']];
const CSS = `
#hud{position:fixed;inset:0;pointer-events:none;font:13px/1.3 "Inter","Segoe UI",system-ui,sans-serif;color:#eef2f6;user-select:none}
#hud .p{pointer-events:auto;background:rgba(16,21,28,.62);backdrop-filter:blur(14px) saturate(140%);border:1px solid rgba(255,255,255,.09);border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
#top{position:absolute;top:14px;left:50%;transform:translateX(-50%);display:flex;gap:22px;align-items:center;padding:9px 20px}
#top b{font-size:15px;font-weight:600;font-variant-numeric:tabular-nums}#top small{display:block;font-size:10px;letter-spacing:.09em;text-transform:uppercase;opacity:.55}
#dem{display:flex;gap:4px;align-items:flex-end;height:28px}#dem i{display:block;width:7px;border-radius:2px;min-height:2px}
#bar{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);display:flex;gap:6px;padding:8px}
#hud button{all:unset;cursor:pointer;padding:9px 13px;border-radius:9px;font-weight:500;transition:background .15s}
#hud button:hover{background:rgba(255,255,255,.1)}#hud button.on{background:#e9eef4;color:#10151c}
#hud kbd{font:10px ui-monospace,monospace;opacity:.5;margin-left:6px}
#clk{position:absolute;right:14px;top:14px;padding:10px 14px;display:flex;gap:10px;align-items:center}
#clk input[type=range]{width:150px;accent-color:#e9eef4}
#perf{position:absolute;left:14px;top:14px;padding:6px 10px;font:11px ui-monospace,monospace;opacity:.75}
#toast{position:absolute;left:14px;bottom:16px;display:flex;flex-direction:column;gap:6px}
#toast div{padding:8px 12px;border-left:3px solid #ff5a47}`;

export default function create(ctx) {
  const { world, events, renderer } = ctx;
  let root, t = 0, frames = 0, fps = 0;
  const $ = (s) => root.querySelector(s);
  const fmt = (n) => Math.round(n).toLocaleString('en-US');
  return {
    name: 'ui',
    showcase: { cam: { pos: [-95, 70, -120], target: [0, 8, 0] }, time: 17 },
    init() {
      const st = document.createElement('style');
      st.textContent = CSS;
      document.head.appendChild(st);
      root = document.createElement('div');
      root.id = 'hud';
      root.innerHTML = `
<div id="perf" class="p"></div>
<div id="top" class="p"><div><small>Population</small><b id="pop">0</b></div><div><small>Jobs</small><b id="jobs">0</b></div><div><small>Treasury</small><b id="money">0</b></div>
<div><small>Demand</small><div id="dem"><i style="background:#35c46a"></i><i style="background:#3d8bff"></i><i style="background:#f2b632"></i><i style="background:#b46cff"></i></div></div></div>
<div id="clk" class="p"><b id="time">10:00</b><input id="tod" type="range" min="0" max="24" step="0.05"><label><input id="lock" type="checkbox"> hold</label>
<span>${[0, 1, 3].map((s) => `<button data-speed="${s}">${s ? s + 'x' : 'II'}</button>`).join('')}</span></div>
<div id="bar" class="p">${TOOLS.map(([id, label, key]) => `<button data-tool="${id}">${label}<kbd>${key}</kbd></button>`).join('')}</div>
<div id="toast"></div>`;
      document.body.appendChild(root);
      const mark = () => {
        root.querySelectorAll('[data-speed]').forEach((b) => b.classList.toggle('on', Number(b.dataset.speed) === world.speed));
      };
      root.addEventListener('click', (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        events.emit('ui:click');
        if (b.dataset.tool) events.emit('tool:set', b.dataset.tool);
        if (b.dataset.speed) { world.speed = Number(b.dataset.speed); mark(); }
      });
      $('#tod').addEventListener('input', (e) => { world.time = Number(e.target.value) % 24; });
      $('#lock').addEventListener('change', (e) => { world.timeLocked = e.target.checked; });
      addEventListener('keydown', (e) => {
        const tool = TOOLS.find((x) => 'Digit' + x[2] === e.code);
        if (tool) events.emit('tool:set', tool[0]);
        if (e.code === 'Space') { world.speed = world.speed ? 0 : 1; mark(); e.preventDefault(); }
      });
      events.on('tool:changed', (name) => root.querySelectorAll('[data-tool]').forEach((b) => b.classList.toggle('on', b.dataset.tool === name)));
      events.on('module:error', (e) => {
        const d = document.createElement('div');
        d.className = 'p';
        d.textContent = `Module "${e.name}" disabled (${e.phase}): ${e.message}`;
        $('#toast').appendChild(d);
      });
      mark();
      root.querySelector('[data-tool="none"]').classList.add('on');
    },
    update(dt) {
      frames++; t += dt;
      if (t < 0.25) return;
      fps = frames / t; frames = 0; t = 0;
      const s = world.stats, d = s.demand, h = Math.floor(world.time), mi = Math.floor((world.time - h) * 60);
      $('#pop').textContent = fmt(s.pop);
      $('#jobs').textContent = fmt(s.jobs);
      $('#money').textContent = '₡ ' + fmt(s.money);
      $('#time').textContent = `${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`;
      $('#lock').checked = world.timeLocked;
      if (document.activeElement !== $('#tod')) $('#tod').value = world.time;
      [d.r, d.c, d.i, d.o].forEach((v, i) => { $('#dem').children[i].style.height = Math.round(2 + v * 26) + 'px'; });
      $('#perf').textContent = `${Math.round(fps)} fps  ${renderer.info.render.calls} calls  ${(renderer.info.render.triangles / 1e6).toFixed(2)} M tris`;
    },
  };
}
```

### `src/audio/index.js`
```js
import { clamp, smooth } from '../core/rng.js';

export default function create(ctx) {
  const { camera, world, events } = ctx;
  const rng = world.rng(81);
  let ac = null, city, wind, crick, next = 2;
  function start() {
    if (ac) return;
    ac = new (window.AudioContext || window.webkitAudioContext)();
    const len = ac.sampleRate * 3, buf = ac.createBuffer(1, len, ac.sampleRate), d = buf.getChannelData(0);
    let b = 0;
    for (let i = 0; i < len; i++) { b = (b + (rng() * 2 - 1) * 0.04) * 0.985; d[i] = b * 4; }
    const master = ac.createGain();
    master.gain.value = 0.6;
    master.connect(ac.destination);
    const layer = (type, freq) => {
      const s = ac.createBufferSource(), f = ac.createBiquadFilter(), g = ac.createGain();
      s.buffer = buf; s.loop = true; f.type = type; f.frequency.value = freq; g.gain.value = 0;
      s.connect(f).connect(g).connect(master); s.start();
      return g;
    };
    city = layer('lowpass', 220);
    wind = layer('bandpass', 700);
    const o = ac.createOscillator(), lfo = ac.createOscillator(), lg = ac.createGain();
    crick = ac.createGain();
    o.frequency.value = 4300; lfo.type = 'square'; lfo.frequency.value = 17; lg.gain.value = 0; crick.gain.value = 0;
    lfo.connect(lg.gain); o.connect(lg).connect(crick).connect(master); o.start(); lfo.start();
    ctx.audioMaster = master;
  }
  function blip(f0, f1, dur, vol) {
    if (!ac) return;
    const o = ac.createOscillator(), g = ac.createGain(), t = ac.currentTime;
    o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(ctx.audioMaster); o.start(t); o.stop(t + dur + 0.02);
  }
  return {
    name: 'audio',
    showcase: { cam: { pos: [-95, 70, -120], target: [0, 8, 0] }, time: 8 },
    init() {
      addEventListener('pointerdown', start, { once: true });
      events.on('ui:click', () => blip(880, 1320, 0.07, 0.05));
    },
    update(dt) {
      if (!ac) return;
      const t = ac.currentTime, y = camera.position.y, n = world.night, near = 1 - smooth(80, 1100, y);
      city.gain.setTargetAtTime(clamp(0.03 + world.stats.pop / 30000, 0.03, 0.5) * near * (1 - n * 0.4), t, 0.4);
      wind.gain.setTargetAtTime(smooth(150, 1400, y) * 0.22, t, 0.4);
      crick.gain.setTargetAtTime(n * near * 0.012, t, 0.6);
      next -= dt;
      if (next <= 0) {
        next = 1.5 + rng() * 5;
        if (n < 0.2 && near > 0.3) { const f = 2400 + rng() * 1800; blip(f, f * (1.1 + rng() * 0.4), 0.09 + rng() * 0.08, 0.02 * near); }
      }
    },
  };
}
```

### `src/democity/index.js`
```js
import { N, GROUND, ZONE } from '../core/world.js';
import { hash2 } from '../core/rng.js';

export default function create(ctx) {
  const { world, events } = ctx;
  return {
    name: 'democity',
    showcase: { cam: { pos: [-430, 120, -400], target: [0, 45, 0] }, time: 19.3 },
    init() {
      if (ctx.params.has('empty')) return;
      const c = N / 2, R = 30, s = world.seed;
      const set = (i, j, v) => { world.road[(c + j) * N + c + i] = v; };
      for (let j = -R; j <= R; j++) for (let i = -R; i <= R; i++) {
        const onV = i % 5 === 0, onH = j % 5 === 0;
        if ((onV || onH) && world.buildable(c + i, c + j)) set(i, j, (onV && i % 10 === 0) || (onH && j % 10 === 0) ? 2 : 1);
      }
      // three avenue bridges across the river and a small north-bank quarter
      for (const i of [-10, 0, 10]) for (let j = 15; j <= 44; j++) if (world.cellHeight(c + i, c + j) < GROUND + 0.6) set(i, j, 2);
      for (let i = -14; i <= 14; i++) for (const j of [40, 44]) if (world.buildable(c + i, c + j)) set(i, j, 1);
      for (let j = -R; j <= 46; j++) for (let i = -R; i <= R; i++) {
        const x = c + i, z = c + j, k = z * N + x;
        if (world.road[k] || !world.buildable(x, z)) continue;
        if (j > R) { if (j >= 39 && Math.abs(i) <= 15) world.zone[k] = ZONE.RES; continue; }
        const bi = Math.floor(i / 5), bj = Math.floor(j / 5), h = hash2(bi, bj, s), d = Math.hypot(bi * 5 + 2.5, bj * 5 + 2.5);
        let zn;
        if (hash2(bi, bj, s + 9) < 0.09) zn = ZONE.PARK;
        else if (d < 9) zn = h < 0.62 ? ZONE.OFF : ZONE.COM;
        else if (d < 17) zn = h < 0.3 ? ZONE.COM : h < 0.42 ? ZONE.OFF : ZONE.RES;
        else if (bi >= 3 && bj <= -1) zn = ZONE.IND;
        else zn = h < 0.14 ? ZONE.COM : ZONE.RES;
        world.zone[k] = zn;
      }
      events.emit('roads:changed');
      events.emit('zones:changed');
      if (ctx.api.simulation?.grow) ctx.api.simulation.grow(0.95);
      else console.warn('[democity] simulation module unavailable, city left undeveloped');
    },
  };
}
```

## What is real, what is missing

- Implemented in this pass: architecture and module contract, failure-isolating registry, seeded world, island terrain with river and water, physically based sun/sky with image-based lighting that follows the time of day, shadowed directional sun and moon, exponential fog, bloom, drifting clouds, tiled roads with markings, crossings and bridges, zoning, ten instanced building classes with lit windows at night, trees, street lights with light pools, lane-following traffic with head and tail lights, growth and budget simulation, build tools, HUD, synthesised ambience, a seeded demo city, the headless screenshot tool and per-module showcase URLs.
- Not done, stated plainly: no agent fan-out, no critic rounds, no blind A/B test, no measured fps or draw calls, no screenshot. Visual quality is unverified; the procedural materials are a starting point and will not match a shipped AAA title without photographic CC0 texture sets, modelled building assets, cascaded shadows, ambient occlusion and curved roads. Those items are the open issues in `docs/STATUS.json`, and the loop in `ARCHITECTURE.md` section 9 starts from them.
