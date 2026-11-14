### package.json
```json
{
  "name": "last-flight",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "postprocessing": "6.39.4",
    "three": "0.185.1"
  },
  "devDependencies": {
    "@types/three": "0.185.4",
    "typescript": "^5.9",
    "vite": "^8",
    "vitest": "^5"
  }
}
```

### vite.config.ts
```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  build: { target: 'es2022', chunkSizeWarningLimit: 2000 },
  test: { environment: 'node', include: ['tests/**/*.test.ts'] },
});
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM"],
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "types": ["vite/client"]
  },
  "include": ["src", "tests", "vite.config.ts"]
}
```

### index.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>LAST FLIGHT</title>
<style>
  html, body { margin: 0; height: 100%; overflow: hidden; background: #000; }
  canvas { display: block; }
  #hud { position: fixed; inset: 0; pointer-events: none; color: #dff6ff; font: 1.6vmin system-ui, sans-serif; letter-spacing: 0.25em; text-transform: uppercase; text-shadow: 0 0 0.6vmin #0af8; }
  #hud .p { position: absolute; background: #0208; border: 1px solid #8df4; padding: 1vmin 1.4vmin; }
  #hud .big { font-size: 4vmin; letter-spacing: 0.1em; }
  #hud .bar { width: 22vmin; height: 0.8vmin; background: #0006; border: 1px solid #8df6; margin-top: 0.5vmin; }
  #hud .bar i { display: block; height: 100%; background: #9ef; }
  #hud .red { color: #ff5a4a; } #hud .green { color: #7f8; }
  #cross { position: absolute; left: 50%; top: 50%; border: 1px solid #dffc; border-radius: 50%; transform: translate(-50%, -50%); }
  #lock { position: absolute; border: 1px solid #f54; width: 7vmin; height: 7vmin; transform: translate(-50%, -50%); font-size: 1.2vmin; color: #f76; white-space: nowrap; }
  #arrow { position: absolute; transform: translate(-50%, -50%); font-size: 1.4vmin; white-space: nowrap; }
  #popup { position: absolute; left: 50%; top: 32%; transform: translateX(-50%); font-size: 3vmin; transition: opacity 0.4s; }
  #title { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; background: #0005; line-height: 2.2; }
  #title h1 { font-size: 11vmin; font-weight: 200; letter-spacing: 0.5em; margin: 0; }
  .lb { position: absolute; left: 0; right: 0; height: 0; background: #000; transition: height 0.5s; }
  #flash { position: absolute; inset: 0; box-shadow: inset 0 0 18vmin 4vmin #f00; opacity: 0; }
  #radio { left: 2vmin; bottom: 2vmin; max-width: 50vmin; border: none !important; background: none !important; }
</style>
</head>
<body>
<div id="hud"></div>
<script type="module" src="/src/main.ts"></script>
</body>
</html>
```

### README.md
```md
# LAST FLIGHT

Cinematic 3D superhero flight and rescue game. Three.js + TypeScript + Vite, fully procedural (no assets, no network).

    npm install
    npm run dev
    npm run build

Other scripts: `npm run typecheck`, `npm test`, `npm run preview`.

Controls: mouse aim, LMB laser, RMB lock, W thrust, S brake, Shift boost, Space up, Ctrl down, A/D strafe,
E grab/release, R retry phase, Shift+R restart, F free-fly, ` debug panel, [ ] sensitivity.
```

### src/config.ts
```ts
/** Every tunable. Mutated only by the debug panel. Units in comments. */
export const CONFIG = {
  flight: {
    thrust: 60, // m/s^2 along aim
    boostMul: 2.2, // thrust multiplier on boost
    vCruise: 65, // m/s terminal cruise speed
    vBoost: 190, // m/s terminal boost speed
    turnSlow: 2.5, // rad/s turn rate at 0 m/s
    turnFast: 0.7, // rad/s turn rate at vBoost
    brakeMul: 6, // drag multiplier on air brake
    vert: 25, // m/s^2 Space / Ctrl
    strafe: 20, // m/s^2 A/D in hover
    yawAssist: 0.6, // rad/s A/D at speed
    gravCoast: 2.5, // m/s^2 when coasting
    gravStun: 9.8, // m/s^2 when stunned
    boostDrain: 4, // s to empty
    boostRefill: 3, // s to full
    boostLock: 1, // s lockout at empty
    blend: 0.4, // s drag / pose blend
    boomOn: 140, // m/s supersonic threshold
    boomOff: 120, // m/s re-arm threshold
    radius: 0.9, // m collision sphere
    standH: 1.8, // m centre height above surface
    landAlt: 2.2, // m landing altitude
    landSpeed: 8, // m/s landing speed
    hardLanding: 30, // m/s hard landing threshold
    restitution: 0.25, // bounce factor
    hitSpeedMul: 0.4, // speed kept after a wall hit
    bounds: 4500, // m soft boundary radius
  },
  laser: {
    range: 1500, // m
    jetDps: 35, // HP/s
    missileDps: 60, // HP/s
    heatTime: 4, // s 0 -> 100
    coolTime: 3, // s 100 -> 0
    overheat: 2, // s lockout
    assistDeg: 3, // deg magnetism cone
    lockDeg: 15, // deg lock acquire cone
    breakDeg: 30, // deg lock break cone
  },
  plane: {
    spawnX: 9000, // m east of downtown
    spawnY: 2400, // m altitude
    speed: 110, // m/s
    sink0: 18, // m/s initial sink
    sink1: 30, // m/s sink after sinkRamp
    sinkRamp: 60, // s
    pitchEnd: -12, // deg nose pitch after pitchRamp
    pitchRamp: 90, // s
    grabRange: 6, // m
    grabSpeed: 25, // m/s max relative speed
    tailTear: 1.5, // s until the tail tears
    tailDamage: 30, // hull
  },
  hold: {
    gravity: 8, // m/s^2 down
    lift: 25, // m/s^2 Space
    down: 10, // m/s^2 Ctrl
    brakeMax: 12, // m/s^2 S at full ramp
    brakeRamp: 1, // s to full brake
    push: 6, // m/s^2 W
    pitchMax: 35, // deg
    rollMax: 20, // deg
    yawRate: 0.4, // rad/s max
    aeroBrake: 4, // m/s^2 nose-up beyond aeroDeg
    aeroDive: 3, // m/s^2 nose-down beyond aeroDeg
    aeroDeg: 15, // deg
    stressBrake: 12, // stress/s per m/s^2 over stressFree
    stressFree: 7, // m/s^2 brake without stress
    stressRate: 15, // stress/s for yaw / speed / sink
    stressDecay: 20, // stress/s when gentle
    hullBurn: 8, // hull/s at stress 100
    perfectSink: 4, // m/s
    hardSink: 10, // m/s
    setdownSpeed: 8, // m/s over the zone
  },
  jet: {
    speed: 180, // m/s
    turn: 1.6, // rad/s
    floor: 250, // m altitude floor over the city
    hp: 100,
    burst: 0.6, // s cannon burst
    fireRate: 8, // tracers/s
    tracerSpeed: 600, // m/s
    missileEvery: 12, // s
    tracerHero: 8, // hero damage
    tracerHull: 4, // hull damage
  },
  missile: { speed: 250, turn: 1.2, hp: 20, heroDamage: 35, hullDamage: 25, life: 14 }, // m/s, rad/s, hp, hp, hull, s
  camera: {
    fov: 72, // deg base
    fovBoost: 30, // deg added at vBoost
    distHover: 5, // m
    distFast: 13, // m
    lagCruise: 0.12, // s
    lagBoost: 0.2, // s
    holdDist: 22, // m
    shakeMax: 0.12, // m at supersonic
    rollShare: 0.35, // share of body bank
  },
  city: { n: 64, cell: 48, street: 14, seed: 227 }, // cells, m, m
  stadium: { x: -1392, z: 0, zoneX: 120, zoneZ: 80 }, // m
  post: { bloom: 0.9, bloomThreshold: 0.8, noise: 0.03, vignette: 0.45, blurMax: 0.35 },
  input: { sensitivity: 0.0022, keyTurn: 1.8 }, // rad/px, rad/s
  audio: { master: 0.6 },
};
export type Config = typeof CONFIG;
```

### src/core/math.ts
```ts
import { Vector3, Quaternion, MathUtils } from 'three';

/** Shared temporaries: never hold one across a function call that also uses them. */
export const T0 = new Vector3(), T1 = new Vector3(), T2 = new Vector3(), T3 = new Vector3();
export const TQ0 = new Quaternion(), TQ1 = new Quaternion();
export const UP = new Vector3(0, 1, 0), AX = new Vector3(1, 0, 0), AZ = new Vector3(0, 0, 1);
export const clamp = MathUtils.clamp;
export const lerp = MathUtils.lerp;
export const DEG = Math.PI / 180;

export function smooth01(x: number): number { const t = clamp(x, 0, 1); return t * t * (3 - 2 * t); }
export function damp(a: number, b: number, rate: number, dt: number): number { return a + (b - a) * (1 - Math.exp(-rate * dt)); }
export function wrapPi(a: number): number { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
export function safeNorm(v: Vector3, fx = 0, fy = 0, fz = -1): Vector3 {
  const l = v.length();
  return l > 1e-6 && Number.isFinite(l) ? v.multiplyScalar(1 / l) : v.set(fx, fy, fz);
}
/** Forward is -Z at yaw 0; positive yaw turns left, positive pitch looks up. */
export function dirFromYP(yaw: number, pitch: number, out: Vector3): Vector3 {
  const c = Math.cos(pitch);
  return out.set(-Math.sin(yaw) * c, Math.sin(pitch), -Math.cos(yaw) * c);
}
export function quatFromYPR(q: Quaternion, yaw: number, pitch: number, roll: number): Quaternion {
  q.setFromAxisAngle(UP, yaw);
  q.multiply(TQ1.setFromAxisAngle(AX, pitch));
  return q.multiply(TQ1.setFromAxisAngle(AZ, roll));
}
/** Rotate v toward unit dir d by at most maxAngle, keeping length. */
export function rotateToward(v: Vector3, d: Vector3, maxAngle: number): void {
  const l = v.length();
  if (l < 1e-4) return;
  T3.copy(v).multiplyScalar(1 / l);
  const ang = Math.acos(clamp(T3.dot(d), -1, 1));
  if (ang < 1e-5) return;
  TQ0.setFromUnitVectors(T3, d);
  TQ1.identity().slerp(TQ0, Math.min(1, maxAngle / ang));
  v.applyQuaternion(TQ1);
}
export function finite(v: Vector3): boolean { return Number.isFinite(v.x) && Number.isFinite(v.y) && Number.isFinite(v.z); }
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => { a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
```

### src/core/events.ts
```ts
export interface GameEvents {
  jetKilled: { index: number; last: boolean };
  caught: { tail: boolean };
  tailTorn: undefined;
  touchdown: { sink: number };
  phaseChanged: { phase: string };
  heroHit: { damage: number; dx: number; dz: number };
  hullHit: { damage: number };
  boom: undefined;
}
type Handler<K extends keyof GameEvents> = (e: GameEvents[K]) => void;
export interface Bus {
  on<K extends keyof GameEvents>(k: K, h: Handler<K>): void;
  emit<K extends keyof GameEvents>(k: K, e: GameEvents[K]): void;
  clear(): void;
}
export function createBus(): Bus {
  const map = new Map<string, Array<(e: never) => void>>();
  return {
    on(k, h) { const l = map.get(k) ?? []; l.push(h as (e: never) => void); map.set(k, l); },
    emit(k, e) { const l = map.get(k); if (l) for (let i = 0; i < l.length; i++) (l[i] as (x: unknown) => void)(e); },
    clear() { map.clear(); },
  };
}
```

### src/core/pool.ts
```ts
/** Fixed-size object pool: no allocation after construction. */
export class Pool<T extends { alive: boolean }> {
  readonly items: T[] = [];
  constructor(size: number, make: (i: number) => T) { for (let i = 0; i < size; i++) this.items.push(make(i)); }
  get(): T | null {
    for (let i = 0; i < this.items.length; i++) if (!this.items[i].alive) { this.items[i].alive = true; return this.items[i]; }
    return null;
  }
  killAll(): void { for (const it of this.items) it.alive = false; }
  count(): number { let n = 0; for (const it of this.items) if (it.alive) n++; return n; }
}
```

### src/core/input.ts
```ts
import { CONFIG } from '../config';

export interface Input {
  down(code: string): boolean;
  pressed(code: string): boolean;
  dx: number; dy: number; lmb: boolean; rmbPressed: boolean; anyPressed: boolean; locked: boolean;
  endFrame(): void; update(dt: number): void; dispose(): void;
}
export function createInput(el: HTMLElement): Input {
  const keys = new Set<string>(), hit = new Set<string>();
  const inp: Input = {
    dx: 0, dy: 0, lmb: false, rmbPressed: false, anyPressed: false, locked: false,
    down: (c) => keys.has(c), pressed: (c) => hit.has(c),
    endFrame() { hit.clear(); inp.dx = 0; inp.dy = 0; inp.rmbPressed = false; inp.anyPressed = false; },
    update(dt) {
      if (inp.locked) return;
      const k = CONFIG.input.keyTurn * dt / CONFIG.input.sensitivity;
      if (keys.has('ArrowLeft')) inp.dx -= k; if (keys.has('ArrowRight')) inp.dx += k;
      if (keys.has('ArrowUp')) inp.dy -= k; if (keys.has('ArrowDown')) inp.dy += k;
    },
    dispose() { ac.abort(); },
  };
  const ac = new AbortController(), o = { signal: ac.signal };
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Tab' || e.code === 'Space') e.preventDefault();
    if (!e.repeat) { hit.add(e.code); inp.anyPressed = true; }
    keys.add(e.code);
    if (e.code === 'BracketLeft') CONFIG.input.sensitivity *= 0.9;
    if (e.code === 'BracketRight') CONFIG.input.sensitivity *= 1.1;
  }, o);
  window.addEventListener('keyup', (e) => keys.delete(e.code), o);
  window.addEventListener('blur', () => { keys.clear(); inp.lmb = false; }, o);
  el.addEventListener('mousedown', (e) => {
    if (!inp.locked) { try { const p = el.requestPointerLock() as unknown; if (p instanceof Promise) p.catch(() => undefined); } catch { /* denied: arrow keys steer */ } }
    if (e.button === 0) { inp.lmb = true; hit.add('Mouse0'); } else if (e.button === 2) inp.rmbPressed = true;
    inp.anyPressed = true;
  }, o);
  window.addEventListener('mouseup', (e) => { if (e.button === 0) inp.lmb = false; }, o);
  window.addEventListener('contextmenu', (e) => e.preventDefault(), o);
  window.addEventListener('mousemove', (e) => { if (inp.locked) { inp.dx += e.movementX; inp.dy += e.movementY; } }, o);
  document.addEventListener('pointerlockchange', () => { inp.locked = document.pointerLockElement === el; }, o);
  return inp;
}
```

### src/core/loop.ts
```ts
export interface Loop { timeScale: number; slow(scale: number, seconds: number): void; start(): void; stop(): void; }
const STEP = 1 / 120;
/** Fixed 120 Hz simulation with accumulator; frame dt clamped to 0.05 s. */
export function createLoop(fixed: (dt: number) => void, frame: (dt: number, timeScale: number, realDt: number) => void): Loop {
  let acc = 0, last = 0, raf = 0, slowT = 0, slowScale = 1;
  const loop: Loop = {
    timeScale: 1,
    slow(scale, seconds) { slowScale = scale; slowT = seconds; },
    start() { last = performance.now(); raf = requestAnimationFrame(tick); },
    stop() { cancelAnimationFrame(raf); },
  };
  function tick(now: number): void {
    raf = requestAnimationFrame(tick);
    const real = Math.min(0.05, Math.max(0, (now - last) / 1000));
    last = now;
    slowT -= real;
    const target = slowT > 0 ? slowScale : 1;
    loop.timeScale += (target - loop.timeScale) * Math.min(1, real * 10);
    const dt = real * loop.timeScale;
    acc += dt;
    let n = 0;
    while (acc >= STEP && n < 8) { fixed(STEP); acc -= STEP; n++; }
    if (n === 8) acc = 0;
    frame(dt, loop.timeScale, real);
  }
  return loop;
}
```

### src/core/audio.ts
```ts
import { CONFIG } from '../config';

export interface AudioParams { speed: number; boost: boolean; firing: boolean; heat: number; crowd: number; combat: boolean; fire: number; missile: number; timeScale: number; }
export interface GameAudio {
  init(): void; update(dt: number, p: AudioParams): void;
  boom(): void; explode(dist: number): void; cannon(): void; groan(): void; crunch(): void; scream(): void;
  thud(): void; beep(): void; whoosh(): void; chord(): void; dispose(): void;
}
/** All sound is Web Audio synthesis; created on first click. */
export function createAudio(): GameAudio {
  let ac: AudioContext | null = null, master: GainNode, noiseBuf: AudioBuffer;
  let windF: BiquadFilterNode, windG: GainNode, roarG: GainNode, laserO: OscillatorNode, laserG: GainNode, crowdG: GainNode, fireG: GainNode, droneF: BiquadFilterNode;
  let kickT = 0, missT = 0, rate = 1, t = 0;
  const noise = (loop: boolean): AudioBufferSourceNode => { const s = ac!.createBufferSource(); s.buffer = noiseBuf; s.loop = loop; return s; };
  function bed(type: BiquadFilterType, freq: number): { f: BiquadFilterNode; g: GainNode } {
    const s = noise(true), f = ac!.createBiquadFilter(), g = ac!.createGain();
    f.type = type; f.frequency.value = freq; g.gain.value = 0; s.connect(f).connect(g).connect(master); s.start();
    return { f, g };
  }
  function osc(type: OscillatorType, freq: number, gain: number, dest: AudioNode): OscillatorNode {
    const o = ac!.createOscillator(), g = ac!.createGain(); o.type = type; o.frequency.value = freq; g.gain.value = gain; o.connect(g).connect(dest); o.start(); return o;
  }
  function burst(dur: number, gain: number, f0: number, f1: number, type: BiquadFilterType = 'lowpass'): void {
    if (!ac) return;
    const s = noise(false), f = ac.createBiquadFilter(), g = ac.createGain(), n = ac.currentTime;
    f.type = type; f.frequency.setValueAtTime(f0, n); f.frequency.exponentialRampToValueAtTime(Math.max(20, f1), n + dur);
    g.gain.setValueAtTime(gain, n); g.gain.exponentialRampToValueAtTime(0.001, n + dur);
    s.playbackRate.value = rate; s.connect(f).connect(g).connect(master); s.start(n, Math.random()); s.stop(n + dur);
  }
  function tone(type: OscillatorType, f0: number, f1: number, dur: number, gain: number): void {
    if (!ac) return;
    const o = ac.createOscillator(), g = ac.createGain(), n = ac.currentTime;
    o.type = type; o.frequency.setValueAtTime(f0 * rate, n); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1 * rate), n + dur);
    g.gain.setValueAtTime(gain, n); g.gain.exponentialRampToValueAtTime(0.001, n + dur);
    o.connect(g).connect(master); o.start(n); o.stop(n + dur);
  }
  return {
    init() {
      if (ac) { void ac.resume(); return; }
      const Ctor = window.AudioContext; if (!Ctor) return;
      ac = new Ctor(); master = ac.createGain(); master.gain.value = CONFIG.audio.master; master.connect(ac.destination);
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 2, ac.sampleRate);
      const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      const w = bed('bandpass', 300); windF = w.f; windG = w.g;
      const c = bed('bandpass', 900); crowdG = c.g; c.f.Q.value = 0.4;
      const fr = bed('lowpass', 260); fireG = fr.g;
      const rf = ac.createBiquadFilter(); rf.type = 'lowpass'; rf.frequency.value = 220; roarG = ac.createGain(); roarG.gain.value = 0; rf.connect(roarG).connect(master); osc('sawtooth', 55, 1, rf);
      laserG = ac.createGain(); laserG.gain.value = 0; laserG.connect(master); laserO = osc('sawtooth', 180, 0.5, laserG);
      droneF = ac.createBiquadFilter(); droneF.type = 'lowpass'; droneF.frequency.value = 300; droneF.connect(master); osc('sawtooth', 55, 0.05, droneF); osc('sawtooth', 55.6, 0.05, droneF);
    },
    update(dt, p) {
      if (!ac) return;
      t += dt; rate = Math.max(0.4, p.timeScale);
      const n = ac.currentTime, s = Math.min(1, p.speed / 190);
      windF.frequency.setTargetAtTime(300 + 900 * s, n, 0.1); windG.gain.setTargetAtTime(0.5 * s, n, 0.1);
      roarG.gain.setTargetAtTime(p.boost ? 0.35 : 0, n, 0.15);
      laserG.gain.setTargetAtTime(p.firing ? 0.12 : 0, n, 0.03); laserO.frequency.setTargetAtTime((160 + p.heat * 2.2) * rate, n, 0.05);
      crowdG.gain.setTargetAtTime(0.5 * p.crowd, n, 0.4); fireG.gain.setTargetAtTime(0.5 * p.fire, n, 0.2);
      droneF.frequency.setTargetAtTime(300 + 200 * Math.sin(t * 0.3), n, 0.2);
      if (p.combat) { kickT -= dt; if (kickT <= 0) { kickT = 0.6; tone('sine', 110, 40, 0.18, 0.5); } }
      if (p.missile > 0) { missT -= dt; if (missT <= 0) { missT = 0.08 + 0.4 * (1 - p.missile); tone('square', 1400, 1400, 0.05, 0.12); } }
    },
    boom() { tone('sine', 120, 30, 0.4, 0.9); burst(0.5, 0.7, 4000, 200); },
    explode(dist) { const g = Math.min(1, 150 / Math.max(30, dist)); burst(1.2, 0.9 * g, 3000, 80); tone('sine', 70, 28, 0.6, 0.9 * g); },
    cannon() { burst(0.06, 0.18, 2500, 900, 'bandpass'); },
    groan() { tone('sawtooth', 90, 45, 1.2, 0.35); tone('sawtooth', 67, 38, 1.4, 0.3); },
    crunch() { burst(0.2, 0.4, 1800, 300, 'bandpass'); },
    scream() { tone('sawtooth', 500, 1800, 0.9, 0.3); burst(1, 0.5, 6000, 500, 'highpass'); },
    thud() { tone('sine', 60, 25, 0.5, 1); burst(0.4, 0.5, 600, 80); },
    beep() { tone('square', 1200, 1200, 0.06, 0.1); },
    whoosh() { burst(0.35, 0.4, 500, 3000, 'bandpass'); },
    chord() { for (const f of [110, 138.6, 164.8, 220]) tone('sawtooth', f, f, 6, 0.08); },
    dispose() { if (ac) void ac.close(); ac = null; },
  };
}
```

### src/vfx/shaders/radialBlur.ts
```ts
import { Uniform } from 'three';
import { Effect, EffectAttribute } from 'postprocessing';

const frag = /* glsl */ `
uniform float strength;
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec2 d = (vec2(0.5) - uv) * strength / 12.0;
  vec4 c = inputColor; vec2 p = uv;
  for (int i = 0; i < 11; i++) { p += d; c += texture2D(inputBuffer, p); }
  outputColor = c / 12.0;
}`;
/** 12 samples toward screen centre. */
export class RadialBlurEffect extends Effect {
  constructor() { super('RadialBlurEffect', frag, { attributes: EffectAttribute.CONVOLUTION, uniforms: new Map([['strength', new Uniform(0)]]) }); }
  set strength(v: number) { this.uniforms.get('strength')!.value = v; }
}
```

### src/vfx/shaders/grade.ts
```ts
import { Effect } from 'postprocessing';

const frag = /* glsl */ `
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec3 c = inputColor.rgb;
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  c = mix(c, c * c * (3.0 - 2.0 * c), 0.25 * step(l, 1.0));
  c += vec3(0.02, 0.008, -0.004) * (1.0 - smoothstep(0.0, 0.4, l));
  c *= vec3(1.03, 1.0, 0.96);
  outputColor = vec4(max(c, 0.0), inputColor.a);
}`;
/** Gentle S-curve with warm shadows. */
export class GradeEffect extends Effect { constructor() { super('GradeEffect', frag); } }
```

### src/vfx/shaders/fire.ts
```ts
export const fireVert = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
export const fireFrag = /* glsl */ `
varying vec2 vUv; uniform float uLife; uniform float uSeed;
float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
void main() {
  vec2 p = vUv * 2.0 - 1.0; float r = length(p);
  float f = n(p * 3.0 + uSeed + uLife * 2.0) * 0.6 + n(p * 7.0 - uSeed) * 0.4;
  float a = smoothstep(1.0, 0.2, r + f * 0.5) * (1.0 - uLife);
  vec3 hot = mix(vec3(1.0, 0.25, 0.02), vec3(1.0, 0.9, 0.6), smoothstep(0.3, 1.0, a + f * 0.3));
  vec3 col = mix(hot * 5.0, vec3(0.05, 0.03, 0.02), smoothstep(0.2, 1.0, uLife));
  gl_FragColor = vec4(col * a, a * smoothstep(0.3, 1.0, uLife));
}`;
```

### src/vfx/shaders/water.ts
```ts
export const waterVert = /* glsl */ `
varying vec3 vW;
void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`;
export const waterFrag = /* glsl */ `
varying vec3 vW; uniform float uTime; uniform vec3 uSun; uniform vec3 uSky; uniform vec3 uFog;
vec2 wave(vec2 p, float t) { return vec2(cos(p.x * 0.21 + t) + cos(p.x * 0.47 + p.y * 0.3 - t * 1.3), cos(p.y * 0.33 + t * 0.8) + cos(p.y * 0.61 - p.x * 0.2 + t * 1.7)); }
void main() {
  vec2 g = wave(vW.xz, uTime) * 0.06 + wave(vW.zx * 2.3, uTime * 1.6) * 0.04;
  vec3 nrm = normalize(vec3(g.x, 1.0, g.y));
  vec3 v = normalize(cameraPosition - vW);
  float fr = pow(1.0 - max(dot(nrm, v), 0.0), 4.0);
  float spec = pow(max(dot(reflect(-normalize(uSun), nrm), v), 0.0), 180.0);
  vec3 col = mix(vec3(0.02, 0.05, 0.07), uSky, fr) + vec3(1.0, 0.6, 0.3) * spec * 6.0;
  float fog = 1.0 - exp(-length(cameraPosition - vW) * 0.00028);
  gl_FragColor = vec4(mix(col, uFog, fog), 1.0);
}`;
```

### src/vfx/shaders/windows.ts
```ts
import { CanvasTexture, MeshStandardMaterial, NearestFilter, RepeatWrapping, SRGBColorSpace } from 'three';

/** 8x8 window tile: R = glass mask, G = per-window random used for the lit test. */
export function makeWindowTexture(): CanvasTexture {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d')!; g.fillStyle = '#000'; g.fillRect(0, 0, 128, 128);
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) { g.fillStyle = `rgb(255,${Math.floor(Math.random() * 255)},0)`; g.fillRect(x * 16 + 3, y * 16 + 3, 10, 11); }
  const t = new CanvasTexture(c); t.wrapS = t.wrapT = RepeatWrapping; t.magFilter = NearestFilter; t.colorSpace = SRGBColorSpace;
  return t;
}
/** World-space window UVs on vertical faces so every building gets 3 m windows. */
export function applyWindows(mat: MeshStandardMaterial, tex: CanvasTexture): void {
  mat.onBeforeCompile = (s) => {
    s.uniforms.uWin = { value: tex };
    s.vertexShader = s.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWp; varying vec3 vWn; varying float vSeed;')
      .replace('#include <project_vertex>', '#include <project_vertex>\n#ifdef USE_INSTANCING\nvWp = (modelMatrix * instanceMatrix * vec4(transformed, 1.0)).xyz; vSeed = fract(instanceMatrix[3].x * 0.137 + instanceMatrix[3].z * 0.291);\n#else\nvWp = (modelMatrix * vec4(transformed, 1.0)).xyz; vSeed = 0.0;\n#endif\nvWn = normal;');
    s.fragmentShader = s.fragmentShader.replace('#include <common>', '#include <common>\nuniform sampler2D uWin; varying vec3 vWp; varying vec3 vWn; varying float vSeed;')
      .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
      if (abs(vWn.y) < 0.5) {
        vec2 wuv = vec2(abs(vWn.x) > 0.5 ? vWp.z : vWp.x, vWp.y) / 24.0;
        vec4 w = texture2D(uWin, wuv);
        diffuseColor.rgb *= mix(1.0, 0.3, w.r);
        float lit = step(0.7, fract(w.g + vSeed + floor(wuv.y * 8.0) * 0.37)) * w.r;
        totalEmissiveRadiance += vec3(1.0, 0.72, 0.38) * lit * 1.6;
      }`);
  };
}
```

### src/vfx/shaders/cloud.ts
```ts
export const cloudVert = /* glsl */ `
attribute vec4 iData; // xyz centre, w size
attribute float iRot;
varying vec2 vUv; varying float vRot; varying float vFog;
void main() {
  vUv = uv; vRot = iRot;
  vec4 mv = viewMatrix * vec4(iData.xyz, 1.0);
  float c = cos(iRot), s = sin(iRot);
  vec2 p = mat2(c, -s, s, c) * position.xy * iData.w;
  mv.xy += p * vec2(1.0, 0.45);
  vFog = 1.0 - exp(-length(mv.xyz) * 0.00022);
  gl_Position = projectionMatrix * mv;
}`;
export const cloudFrag = /* glsl */ `
varying vec2 vUv; varying float vRot; varying float vFog; uniform vec2 uSunScreen; uniform vec3 uFog;
float h(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float n(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h(i), h(i + vec2(1, 0)), f.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), f.x), f.y); }
void main() {
  vec2 p = vUv * 2.0 - 1.0;
  float d = length(p) + (n(p * 3.0 + vRot * 9.0) - 0.5) * 0.6;
  float a = smoothstep(1.0, 0.25, d) * 0.75;
  if (a < 0.01) discard;
  float sun = clamp(dot(normalize(p + 1e-4), normalize(uSunScreen)) * 0.5 + 0.5, 0.0, 1.0);
  vec3 col = mix(vec3(0.42, 0.34, 0.42), vec3(1.9, 1.2, 0.75), sun * sun);
  gl_FragColor = vec4(mix(col, uFog, vFog), a * (1.0 - vFog * 0.7));
}`;
```

### src/core/renderer.ts
```ts
import { BufferAttribute, BufferGeometry, Color, HalfFloatType, Matrix4, Mesh, NoToneMapping, PCFSoftShadowMap, PerspectiveCamera, Scene, SRGBColorSpace, Vector2, WebGLRenderer } from 'three';
import { BlendFunction, BloomEffect, ChromaticAberrationEffect, EffectComposer, EffectPass, GodRaysEffect, NoiseEffect, RenderPass, SMAAEffect, SMAAPreset, ToneMappingEffect, ToneMappingMode, VignetteEffect } from 'postprocessing';
import { CONFIG } from '../config';
import { RadialBlurEffect } from '../vfx/shaders/radialBlur';
import { GradeEffect } from '../vfx/shaders/grade';

export interface Gfx { renderer: WebGLRenderer; render(dt: number): void; setFx(blur: number, ca: number): void; resize(): void; dispose(): void; }

/** Bake a transform and a vertex colour into a geometry part (for merged procedural models). */
export function part(g: BufferGeometry, color: number, m?: Matrix4): BufferGeometry {
  if (m) g.applyMatrix4(m);
  const c = new Color(color), n = g.getAttribute('position').count, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { a[i * 3] = c.r; a[i * 3 + 1] = c.g; a[i * 3 + 2] = c.b; }
  g.setAttribute('color', new BufferAttribute(a, 3));
  return g;
}

export function createGfx(scene: Scene, camera: PerspectiveCamera, sunMesh: Mesh): Gfx {
  const renderer = new WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);
  let composer: EffectComposer | null = null, blur: RadialBlurEffect | null = null, ca: ChromaticAberrationEffect | null = null;
  try {
    composer = new EffectComposer(renderer, { frameBufferType: HalfFloatType, multisampling: 4 });
    composer.addPass(new RenderPass(scene, camera));
    const god = new GodRaysEffect(camera, sunMesh, { density: 0.96, decay: 0.92, weight: 0.3, samples: 60, blur: true });
    const bloom = new BloomEffect({ mipmapBlur: true, luminanceThreshold: CONFIG.post.bloomThreshold, intensity: CONFIG.post.bloom, radius: 0.6 });
    blur = new RadialBlurEffect();
    ca = new ChromaticAberrationEffect({ offset: new Vector2(0, 0), radialModulation: false, modulationOffset: 0 });
    const noise = new NoiseEffect({ blendFunction: BlendFunction.OVERLAY }); noise.blendMode.opacity.value = CONFIG.post.noise;
    composer.addPass(new EffectPass(camera, god, bloom));
    composer.addPass(new EffectPass(camera, blur));
    composer.addPass(new EffectPass(camera, ca));
    composer.addPass(new EffectPass(camera, new GradeEffect(), new VignetteEffect({ darkness: CONFIG.post.vignette, offset: 0.35 }), noise, new ToneMappingEffect({ mode: ToneMappingMode.ACES_FILMIC })));
    composer.addPass(new EffectPass(camera, new SMAAEffect({ preset: SMAAPreset.HIGH })));
  } catch {
    composer = null; blur = null; ca = null;
  }
  const gfx: Gfx = {
    renderer,
    render(dt) { if (composer) composer.render(dt); else renderer.render(scene, camera); },
    setFx(b, c) { if (blur) blur.strength = b; if (ca) ca.offset.set(c, c * 0.5); },
    resize() { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); composer?.setSize(innerWidth, innerHeight); },
    dispose() { composer?.dispose(); renderer.dispose(); renderer.domElement.remove(); },
  };
  return gfx;
}
```

### src/world/collision.ts
```ts
import { Vector3 } from 'three';
import { rng } from '../core/math';

/** Buildings on a grid: h[j * n + i] is the roof height in metres (0 = empty cell). */
export interface Grid { n: number; cell: number; street: number; h: Float32Array; glass: Uint8Array; }
export interface Box { minX: number; maxX: number; minZ: number; maxZ: number; maxY: number; }
const box: Box = { minX: 0, maxX: 0, minZ: 0, maxZ: 0, maxY: 0 };

export function riverX(z: number): number { return 520 + 180 * Math.sin(z / 380); }
export function makeGrid(n: number, cell: number, street: number, seed: number, stadiumX: number, stadiumZ: number): Grid {
  const g: Grid = { n, cell, street, h: new Float32Array(n * n), glass: new Uint8Array(n * n) }, r = rng(seed);
  const plazas = [[-200, 300], [250, -350], [-500, -150]];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    const x = (i - n / 2 + 0.5) * cell, z = (j - n / 2 + 0.5) * cell, a = r(), b = r(), c = r();
    if (Math.abs(x - riverX(z)) < cell * 2.5) continue;
    if (Math.abs(x - stadiumX) < cell * 3 && Math.abs(z - stadiumZ) < cell * 3) continue;
    if (plazas.some((p) => Math.abs(x - p[0]) < cell && Math.abs(z - p[1]) < cell)) continue;
    const downtown = Math.exp(-(x * x + z * z) / (2 * 380 * 380));
    const tall = a < 0.08 + downtown * 0.5, mid = a < 0.3 + downtown * 0.5;
    g.h[j * n + i] = tall ? 160 + b * 260 * (0.3 + downtown) : mid ? 70 + b * 90 : 18 + b * 52;
    g.glass[j * n + i] = c < 0.25 + downtown * 0.4 ? 1 : 0;
  }
  return g;
}
export function cellBox(g: Grid, i: number, j: number, out: Box): boolean {
  if (i < 0 || j < 0 || i >= g.n || j >= g.n) return false;
  const h = g.h[j * g.n + i];
  if (h <= 0) return false;
  const half = g.n / 2, s = g.street / 2;
  out.minX = (i - half) * g.cell + s; out.maxX = (i - half + 1) * g.cell - s;
  out.minZ = (j - half) * g.cell + s; out.maxZ = (j - half + 1) * g.cell - s; out.maxY = h;
  return true;
}
/** Roof height directly below (x, z), or 0 for ground. O(1). */
export function surfaceY(g: Grid, x: number, z: number): number {
  const i = Math.floor(x / g.cell + g.n / 2), j = Math.floor(z / g.cell + g.n / 2);
  if (!cellBox(g, i, j, box)) return 0;
  return x >= box.minX && x <= box.maxX && z >= box.minZ && z <= box.maxZ ? box.maxY : 0;
}
/** Push sphere (p, r) out of a box standing on the ground. Writes the hit normal. */
export function pushOutBox(p: Vector3, r: number, b: Box, n: Vector3): boolean {
  const cx = Math.max(b.minX, Math.min(b.maxX, p.x)), cy = Math.min(b.maxY, p.y), cz = Math.max(b.minZ, Math.min(b.maxZ, p.z));
  const dx = p.x - cx, dy = p.y - cy, dz = p.z - cz, d2 = dx * dx + dy * dy + dz * dz;
  if (d2 >= r * r) return false;
  const e = r + 1e-3;
  if (d2 > 1e-10) { const d = Math.sqrt(d2); n.set(dx / d, dy / d, dz / d); p.set(cx + n.x * e, cy + n.y * e, cz + n.z * e); return true; }
  const a = p.x - b.minX, c = b.maxX - p.x, f = p.z - b.minZ, k = b.maxZ - p.z, t = b.maxY - p.y, m = Math.min(a, c, f, k, t);
  if (m === t) { n.set(0, 1, 0); p.y = b.maxY + e; }
  else if (m === a) { n.set(-1, 0, 0); p.x = b.minX - e; }
  else if (m === c) { n.set(1, 0, 0); p.x = b.maxX + e; }
  else if (m === f) { n.set(0, 0, -1); p.z = b.minZ - e; }
  else { n.set(0, 0, 1); p.z = b.maxZ + e; }
  return true;
}
/** Cell lookup plus the 8 neighbours. */
export function resolveSphere(g: Grid, p: Vector3, r: number, n: Vector3): boolean {
  const ci = Math.floor(p.x / g.cell + g.n / 2), cj = Math.floor(p.z / g.cell + g.n / 2);
  let hit = false;
  for (let j = cj - 1; j <= cj + 1; j++) for (let i = ci - 1; i <= ci + 1; i++) if (cellBox(g, i, j, box) && pushOutBox(p, r, box, n)) hit = true;
  return hit;
}
export function resolveSphereBrute(g: Grid, p: Vector3, r: number, n: Vector3): boolean {
  let hit = false;
  for (let j = 0; j < g.n; j++) for (let i = 0; i < g.n; i++) if (cellBox(g, i, j, box) && pushOutBox(p, r, box, n)) hit = true;
  return hit;
}
```

### src/entities/flight.ts
```ts
import { Quaternion, Vector3 } from 'three';
import { CONFIG } from '../config';
import { clamp, damp, DEG, dirFromYP, finite, lerp, quatFromYPR, rotateToward, smooth01, wrapPi } from '../core/math';
import { Grid, resolveSphere, surfaceY } from '../world/collision';

export type Mode = 'hover' | 'flight' | 'holding' | 'landed' | 'stunned';
export interface FlightInput { thrust: boolean; brake: boolean; boost: boolean; up: boolean; down: boolean; strafe: number; }
export interface FlightState {
  position: Vector3; velocity: Vector3; bodyQuat: Quaternion; aimYaw: number; aimPitch: number;
  boostCharge: number; boostLock: number; boosting: boolean; heat: number; hp: number; mode: Mode;
  stun: number; dragK: number; bank: number; yawRate: number; boomArmed: boolean; sinceDamage: number; charge: number; impact: number; modeT: number;
}
export const EV_BOOM = 1, EV_HIT = 2, EV_LAND = 4, EV_TAKEOFF = 8, EV_HARD = 16;
const a = new Vector3(), n = new Vector3(), q = new Quaternion();

export function createFlightState(): FlightState {
  const F = CONFIG.flight;
  return { position: new Vector3(0, 320, 0), velocity: new Vector3(), bodyQuat: new Quaternion(), aimYaw: -Math.PI / 2, aimPitch: 0, boostCharge: 1, boostLock: 0, boosting: false, heat: 0, hp: 100, mode: 'hover', stun: 0, dragK: F.thrust / (F.vCruise * F.vCruise), bank: 0, yawRate: 0, boomArmed: true, sinceDamage: 99, charge: 0, impact: 0, modeT: 0 };
}
export function turnRate(speed: number): number { return lerp(CONFIG.flight.turnSlow, CONFIG.flight.turnFast, smooth01(speed / CONFIG.flight.vBoost)); }
export function speedTier(speed: number): string { return speed < 6 ? 'HOVER' : speed < 65 ? 'CRUISE' : speed < 140 ? 'FAST' : 'SUPERSONIC'; }

export function stepFlight(s: FlightState, inp: FlightInput, dt: number, grid: Grid | null): number {
  const F = CONFIG.flight;
  let ev = 0;
  s.sinceDamage += dt; s.modeT += dt;
  s.aimPitch = clamp(s.aimPitch, -85 * DEG, 85 * DEG);
  if (s.sinceDamage > 4 && s.hp > 0) s.hp = Math.min(100, s.hp + 10 * dt);
  if (s.mode === 'holding') return 0;
  const v = s.velocity, p = s.position;
  if (s.mode === 'landed') {
    v.set(0, 0, 0);
    if (inp.up) s.charge = Math.min(0.6, s.charge + dt);
    else if (s.charge > 0) { v.y = lerp(15, 45, s.charge / 0.6); p.y += 0.6; s.charge = 0; s.mode = 'flight'; s.modeT = 0; ev |= EV_TAKEOFF; }
    quatFromYPR(q, s.aimYaw, 0, 0); s.bodyQuat.slerp(q, Math.min(1, 8 * dt));
    return ev;
  }
  const speed0 = v.length(), head0 = Math.atan2(-v.x, -v.z);
  dirFromYP(s.aimYaw, s.aimPitch, a);
  if (s.mode === 'stunned') {
    s.stun -= dt; v.y -= F.gravStun * dt; s.boosting = false;
    if (s.stun <= 0) { s.mode = 'flight'; s.modeT = 0; }
  } else {
    s.boosting = inp.boost && inp.thrust && s.boostLock <= 0 && s.boostCharge > 0;
    if (s.boosting) { s.boostCharge -= dt / F.boostDrain; if (s.boostCharge <= 0) { s.boostCharge = 0; s.boostLock = F.boostLock; s.boosting = false; } }
    else { s.boostLock = Math.max(0, s.boostLock - dt); if (s.boostLock <= 0) s.boostCharge = Math.min(1, s.boostCharge + dt / F.boostRefill); }
    if (speed0 > 6) s.aimYaw -= inp.strafe * F.yawAssist * dt;
    if (speed0 > 1) rotateToward(v, a, turnRate(speed0) * dt);
    if (inp.thrust) v.addScaledVector(a, F.thrust * (s.boosting ? F.boostMul : 1) * dt);
    const kT = s.boosting ? (F.thrust * F.boostMul) / (F.vBoost * F.vBoost) : F.thrust / (F.vCruise * F.vCruise);
    s.dragK += (kT - s.dragK) * Math.min(1, dt / F.blend);
    v.multiplyScalar(Math.max(0, 1 - s.dragK * v.length() * (inp.brake ? F.brakeMul : 1) * dt));
    if (inp.up) v.y += F.vert * dt;
    if (inp.down) v.y -= F.vert * dt;
    if (s.mode === 'hover') {
      v.x += Math.cos(s.aimYaw) * inp.strafe * F.strafe * dt; v.z -= Math.sin(s.aimYaw) * inp.strafe * F.strafe * dt;
      if (!inp.thrust && !inp.up && !inp.down && inp.strafe === 0) v.multiplyScalar(Math.max(0, 1 - 2 * dt));
    } else if (!inp.thrust && !inp.up) v.y -= F.gravCoast * dt;
    const sp = v.length();
    if (s.mode === 'hover' && sp > 8) { s.mode = 'flight'; s.modeT = 0; } else if (s.mode === 'flight' && sp < 6) { s.mode = 'hover'; s.modeT = 0; }
  }
  p.addScaledVector(v, dt);
  // soft boundary
  const rr = Math.hypot(p.x, p.z);
  if (rr > F.bounds && s.mode !== 'stunned') { const k = Math.min(60, (rr - F.bounds) * 0.2) * dt / rr; v.x -= p.x * k; v.z -= p.z * k; }
  // buildings
  if (grid && resolveSphere(grid, p, F.radius, n)) {
    const vn = v.dot(n);
    if (vn < 0) {
      s.impact = -vn; v.addScaledVector(n, -(1 + F.restitution) * vn);
      if (s.impact > 6) { v.multiplyScalar(F.hitSpeedMul); s.mode = 'stunned'; s.stun = 0.5; s.modeT = 0; ev |= EV_HIT; }
    }
  }
  // ground / rooftop
  const surf = grid ? surfaceY(grid, p.x, p.z) : 0;
  if (p.y < surf + F.standH) {
    p.y = surf + F.standH;
    if (v.length() > F.hardLanding) { s.impact = v.length(); v.y = Math.abs(v.y) * F.restitution; v.multiplyScalar(F.hitSpeedMul); s.mode = 'stunned'; s.stun = 0.4; s.modeT = 0; ev |= EV_HARD; }
    else if (v.y < 0) v.y = 0;
  }
  const speed = v.length();
  if (s.mode !== 'stunned' && p.y - surf < F.landAlt && speed < F.landSpeed && v.y <= 0.01 && !inp.up && !inp.thrust) { s.mode = 'landed'; s.modeT = 0; v.set(0, 0, 0); p.y = surf + F.standH; ev |= EV_LAND; }
  if (speed >= F.boomOn && s.boomArmed) { s.boomArmed = false; ev |= EV_BOOM; } else if (speed < F.boomOff) s.boomArmed = true;
  // body attitude
  const head1 = speed > 1 ? Math.atan2(-v.x, -v.z) : head0;
  const yr = speed0 > 1 && speed > 1 ? wrapPi(head1 - head0) / dt : 0;
  s.yawRate = damp(s.yawRate, yr, 12, dt);
  s.bank = damp(s.bank, clamp(-s.yawRate * smooth01(speed / 60) * 1.4, -70 * DEG, 70 * DEG), 1 / 0.15, dt);
  if (s.mode === 'stunned') { q.setFromAxisAngle(n.set(0.6, 0.3, 0.74), 9 * dt); s.bodyQuat.multiply(q).normalize(); }
  else if (s.mode === 'flight') {
    const pitch = Math.asin(clamp(v.y / Math.max(speed, 1e-3), -1, 1)) + (inp.brake ? 30 * DEG : 0);
    quatFromYPR(q, head1, pitch, -s.bank); s.bodyQuat.slerp(q, Math.min(1, (s.boosting ? 10 : 6) * dt));
  } else { quatFromYPR(q, s.aimYaw, 0, 0); s.bodyQuat.slerp(q, Math.min(1, 6 * dt)); }
  if (!finite(p) || !finite(v)) { p.set(0, 320, 0); v.set(0, 0, 0); s.bodyQuat.identity(); s.mode = 'hover'; s.dragK = F.thrust / (F.vCruise * F.vCruise); s.yawRate = 0; s.bank = 0; }
  return ev;
}
export function damageHero(s: FlightState, d: number): void { s.hp = Math.max(0, s.hp - d); s.sinceDamage = 0; }
```

### src/entities/holding.ts
```ts
import { Vector3 } from 'three';
import { CONFIG } from '../config';
import { clamp, damp, DEG, dirFromYP, lerp, wrapPi } from '../core/math';

/** Airliner simulation state. Heading uses the same yaw convention as the hero aim (west = +90 deg). */
export interface PlaneState {
  position: Vector3; velocity: Vector3; yaw: number; pitch: number; roll: number; yawRate: number;
  hull: number; stress: number; brake: number; t: number; held: boolean; tailT: number; tailTorn: boolean;
  sinkExtra: number; pitchExtra: number; landed: boolean; released: boolean; dead: boolean; spin: number;
}
export interface HoldInput { pushBack: number; pushFwd: boolean; lift: boolean; down: boolean; aimYaw: number; aimPitch: number; }
const f = new Vector3();

export function createPlane(): PlaneState {
  const P = CONFIG.plane;
  return { position: new Vector3(P.spawnX, P.spawnY, 0), velocity: new Vector3(-P.speed, -P.sink0, 0), yaw: Math.PI / 2, pitch: 0, roll: 0, yawRate: 0, hull: 100, stress: 0, brake: 0, t: 0, held: false, tailT: -1, tailTorn: false, sinkExtra: 0, pitchExtra: 0, landed: false, released: false, dead: false, spin: 0 };
}
export function copyPlane(dst: PlaneState, src: PlaneState): void {
  const p = dst.position, v = dst.velocity;
  Object.assign(dst, src); dst.position = p.copy(src.position); dst.velocity = v.copy(src.velocity);
}
/** Uncaught trajectory: constant ground speed, growing sink, nose slowly dropping. */
export function stepFreePlane(p: PlaneState, dt: number): void {
  const P = CONFIG.plane;
  if (p.landed) return;
  p.t += dt;
  if (p.dead) { p.spin += dt; p.roll += 1.2 * dt; p.pitch = Math.max(-1.2, p.pitch - 0.25 * dt); p.velocity.y -= 9.8 * dt; p.yaw += 0.3 * dt; }
  else {
    const sink = lerp(P.sink0, P.sink1, clamp(p.t / P.sinkRamp, 0, 1)) + p.sinkExtra;
    p.velocity.y = damp(p.velocity.y, -sink, 1.5, dt);
    p.pitch = damp(p.pitch, lerp(0, P.pitchEnd, clamp(p.t / P.pitchRamp, 0, 1)) * DEG + p.pitchExtra, 1, dt);
    p.roll = damp(p.roll, 0, 1, dt);
    const hs = Math.hypot(p.velocity.x, p.velocity.z);
    dirFromYP(p.yaw, 0, f); p.velocity.x = f.x * hs; p.velocity.z = f.z * hs;
  }
  p.position.addScaledVector(p.velocity, dt);
}
/** Tail grab timer: returns true on the step the tail tears off. */
export function stepTailGrab(p: PlaneState, dt: number): boolean {
  if (p.tailT < 0 || p.tailTorn) return false;
  p.tailT += dt;
  if (p.tailT < CONFIG.plane.tailTear) return false;
  p.tailTorn = true; p.tailT = -1; p.hull = Math.max(0, p.hull - CONFIG.plane.tailDamage); p.pitchExtra -= 8 * DEG; p.sinkExtra += 6;
  return true;
}
/** Hero and plane as one body; the plane's velocity is the state. */
export function stepHolding(p: PlaneState, inp: HoldInput, dt: number): void {
  const H = CONFIG.hold;
  if (p.landed) { p.velocity.set(0, 0, 0); p.pitch = damp(p.pitch, 0, 1.2, dt); p.roll = damp(p.roll, 0, 2, dt); p.stress = Math.max(0, p.stress - H.stressDecay * dt); return; }
  p.t += dt;
  let hs = Math.hypot(p.velocity.x, p.velocity.z), vy = p.velocity.y;
  const target = clamp(inp.pushBack, 0, 1) * H.brakeMax, rate = (H.brakeMax / H.brakeRamp) * dt;
  p.brake += clamp(target - p.brake, -rate, rate);
  hs -= p.brake * dt;
  if (inp.pushFwd) hs += H.push * dt;
  vy += (inp.lift ? H.lift : -H.gravity) * dt;
  if (inp.down) vy -= H.down * dt;
  p.yawRate = clamp(wrapPi(inp.aimYaw - p.yaw) * 0.6, -H.yawRate, H.yawRate);
  p.yaw = wrapPi(p.yaw + p.yawRate * dt);
  p.pitch = damp(p.pitch, clamp(inp.aimPitch, -H.pitchMax * DEG, H.pitchMax * DEG), 1.2, dt);
  p.roll = damp(p.roll, clamp(-p.yawRate * 1.2, -H.rollMax * DEG, H.rollMax * DEG), 2, dt);
  if (p.pitch > H.aeroDeg * DEG) { hs -= H.aeroBrake * dt; vy += 2 * dt; }
  else if (p.pitch < -H.aeroDeg * DEG) { hs += H.aeroDive * dt; vy -= 3 * dt; }
  hs = Math.max(0, hs); vy = clamp(vy, -70, 18);
  let rise = H.stressBrake * Math.max(0, p.brake - H.stressFree);
  if (Math.abs(p.yawRate) > 0.3 || hs > 130 || vy < -20) rise += H.stressRate;
  p.stress = clamp(p.stress + (rise > 0 ? rise : -H.stressDecay) * dt, 0, 100);
  if (p.stress >= 100) p.hull = Math.max(0, p.hull - H.hullBurn * dt);
  dirFromYP(p.yaw, 0, f);
  p.velocity.set(f.x * hs, vy, f.z * hs);
  p.position.addScaledVector(p.velocity, dt);
  if (!Number.isFinite(p.position.x + p.position.y + p.position.z)) { p.position.set(0, 600, 0); p.velocity.set(0, 0, 0); }
}
/** World position of a grab point: nose (under the nose cone) or tail. */
export function grabPoint(p: PlaneState, tail: boolean, out: Vector3): Vector3 {
  dirFromYP(p.yaw, p.pitch, out);
  return out.multiplyScalar(tail ? -28 : 28).add(p.position).setY(out.y - 3.4);
}
```

### src/entities/jet.ts
```ts
import { Vector3 } from 'three';
import { CONFIG } from '../config';
import { damp, finite, rotateToward, safeNorm } from '../core/math';

export type JetAI = 'approach' | 'attack' | 'break' | 'reposition' | 'evade' | 'dead';
export interface JetState {
  alive: boolean; position: Vector3; velocity: Vector3; hp: number; ai: JetAI; timer: number; burstT: number; fireT: number;
  missileT: number; laserT: number; evadeCd: number; bank: number; roll: number; nearT: number; onHero: boolean; goal: Vector3; id: number; turning: number;
}
export interface JetOut { fire: boolean; missile: boolean; }
const d = new Vector3(), want = new Vector3();

export function createJet(id: number): JetState {
  return { alive: false, position: new Vector3(), velocity: new Vector3(), hp: 100, ai: 'approach', timer: 0, burstT: 0, fireT: 0, missileT: 6, laserT: 0, evadeCd: 0, bank: 0, roll: 0, nearT: 0, onHero: true, goal: new Vector3(), id, turning: 0 };
}
export function spawnJet(j: JetState, x: number, y: number, z: number, onHero: boolean): void {
  j.alive = true; j.position.set(x, y, z); j.velocity.set(-CONFIG.jet.speed, 0, 0); j.hp = CONFIG.jet.hp; j.ai = 'approach'; j.timer = 0; j.missileT = 4 + (j.id % 4) * 2; j.laserT = 0; j.evadeCd = 0; j.nearT = 0; j.onHero = onHero; j.roll = 0;
}
/** Pure AI step. lasered = the beam is on this jet this step. */
export function stepJet(j: JetState, hero: Vector3, plane: Vector3, planeTarget: boolean, lasered: boolean, dt: number, out: JetOut): void {
  const J = CONFIG.jet;
  out.fire = false; out.missile = false;
  if (!j.alive) return;
  const heroDist = j.position.distanceTo(hero);
  j.nearT = heroDist < 200 ? j.nearT + dt : 0;
  if (!planeTarget || j.nearT > 3) j.onHero = true; else if (heroDist > 600) j.onHero = false;
  const tgt = j.onHero ? hero : plane;
  d.subVectors(tgt, j.position);
  const dist = d.length();
  safeNorm(d);
  j.timer += dt; j.missileT += dt; j.evadeCd -= dt;
  j.laserT = lasered ? j.laserT + dt : Math.max(0, j.laserT - dt * 2);
  if (j.laserT > 0.5 && j.evadeCd <= 0 && j.ai !== 'evade') { j.ai = 'evade'; j.timer = 0; j.evadeCd = 4; }
  want.copy(d);
  switch (j.ai) {
    case 'approach': if (dist < 1500) { j.ai = 'attack'; j.timer = 0; } break;
    case 'attack':
      j.burstT += dt; if (j.burstT > J.burst + 0.9) j.burstT = 0;
      if (j.burstT < J.burst && dist < 1100 && d.dot(want.copy(j.velocity).normalize()) > 0.985) { j.fireT += dt; if (j.fireT >= 1 / J.fireRate) { j.fireT = 0; out.fire = true; } }
      want.copy(d);
      if (dist < 150) { j.ai = 'break'; j.timer = 0; }
      break;
    case 'break': want.set(-d.z, 0.5, d.x); if (j.timer > 1.6) { j.ai = 'reposition'; j.timer = 0; j.goal.set(tgt.x - d.x * 800 + d.z * 400, tgt.y + (j.id % 2 ? 180 : -120), tgt.z - d.z * 800 - d.x * 400); } break;
    case 'reposition': want.subVectors(j.goal, j.position); if (want.length() < 200 || j.timer > 7) { j.ai = 'approach'; j.timer = 0; } break;
    case 'evade': j.roll += 7 * dt; want.set(d.z, 0.7, -d.x); if (j.timer > 1.2) { j.ai = 'reposition'; j.timer = 0; j.roll = 0; j.goal.set(j.position.x + d.z * 700, j.position.y + 150, j.position.z - d.x * 700); } break;
    default: break;
  }
  if (j.missileT >= J.missileEvery && dist > 600 && dist < 2500 && (j.ai === 'attack' || j.ai === 'approach')) { j.missileT = 0; out.missile = true; }
  if (j.position.y < J.floor + 40 && Math.hypot(j.position.x, j.position.z) < 1800) want.y = Math.max(want.y, 0.4 + (J.floor - j.position.y) * 0.01);
  safeNorm(want);
  const hx = j.velocity.x, hz = j.velocity.z;
  rotateToward(j.velocity, want, J.turn * dt);
  j.velocity.setLength(J.speed);
  j.turning = (hx * j.velocity.z - hz * j.velocity.x) / (J.speed * J.speed * dt);
  j.bank = damp(j.bank, Math.max(-1.3, Math.min(1.3, j.turning * 1.1)), 4, dt);
  j.position.addScaledVector(j.velocity, dt);
  if (!finite(j.position)) { j.alive = false; }
}
```

### src/entities/missile.ts
```ts
import { Vector3 } from 'three';
import { CONFIG } from '../config';
import { finite, rotateToward, safeNorm } from '../core/math';

export interface MissileState { alive: boolean; position: Vector3; velocity: Vector3; hp: number; life: number; onHero: boolean; closest: number; }
export const M_FLY = 0, M_HIT = 1, M_MISS = 2;
const d = new Vector3();

export function createMissile(): MissileState { return { alive: false, position: new Vector3(), velocity: new Vector3(), hp: 20, life: 0, onHero: true, closest: 1e9 }; }
export function launchMissile(m: MissileState, from: Vector3, vel: Vector3, onHero: boolean): void {
  m.alive = true; m.position.copy(from); m.velocity.copy(vel).setLength(CONFIG.missile.speed); m.hp = CONFIG.missile.hp; m.life = 0; m.onHero = onHero; m.closest = 1e9;
}
/** Homing with a turn limit: a hard turn inside 200 m makes it overshoot; a miss beyond 8 m detonates harmlessly. */
export function stepMissile(m: MissileState, target: Vector3, hitRadius: number, dt: number): number {
  const M = CONFIG.missile;
  m.life += dt;
  d.subVectors(target, m.position);
  const dist = d.length();
  if (dist < hitRadius) return M_HIT;
  if (dist > m.closest + 4 && m.closest < 200) return M_MISS;
  m.closest = Math.min(m.closest, dist);
  safeNorm(d);
  rotateToward(m.velocity, d, M.turn * dt);
  m.velocity.setLength(M.speed);
  m.position.addScaledVector(m.velocity, dt);
  if (m.life > M.life || m.position.y < 1 || !finite(m.position)) return M_MISS;
  return M_FLY;
}
```

### src/game/scoring.ts
```ts
export interface Stats { time: number; jets: number; hull: number; heroHp: number; sink: number; fireTime: number; onTarget: number; bonus: number; }
export interface Result { score: number; grade: 'S' | 'A' | 'B' | 'C'; accuracy: number; }
export interface Store { getItem(k: string): string | null; setItem(k: string, v: string): void; }
const KEY = 'last-flight-best';

export function createStats(): Stats { return { time: 0, jets: 0, hull: 100, heroHp: 100, sink: 0, fireTime: 0, onTarget: 0, bonus: 0 }; }
export function computeScore(s: Stats): Result {
  const accuracy = s.fireTime > 0.01 ? s.onTarget / s.fireTime : 0;
  const score = Math.round(Math.max(0, 6000 - s.time * 12) + s.jets * 500 + s.hull * 60 + s.heroHp * 10 + Math.max(0, 10 - s.sink) * 300 + accuracy * 1500 + s.bonus);
  return { score, accuracy, grade: score >= 17000 ? 'S' : score >= 13500 ? 'A' : score >= 10000 ? 'B' : 'C' };
}
export function loadBest(store: Store | null): number { try { return Number(store?.getItem(KEY) ?? 0) || 0; } catch { return 0; } }
export function saveBest(store: Store | null, score: number): number {
  const best = Math.max(loadBest(store), score);
  try { store?.setItem(KEY, String(best)); } catch { /* storage unavailable */ }
  return best;
}
```

### src/game/mission.ts
```ts
export type Phase = 'TITLE' | 'CINEMATIC' | 'INTERCEPT' | 'CATCH' | 'ARREST' | 'SETDOWN' | 'RESULTS' | 'FAILED';
export type FailReason = 'AIRLINER IMPACT' | 'HULL DESTROYED' | 'YOU FELL' | 'CRASH LANDING';
export interface MissionState { phase: Phase; phaseTime: number; time: number; fail: FailReason | null; failedIn: Phase; checkpointPhase: Phase; checkpoint: unknown; freeFly: boolean; touched: boolean; }
export interface MissionInput {
  start: boolean; skip: boolean; distToPlane: number; holding: boolean; planeSpeed: number; overZone: boolean;
  touchdownSink: number | null; released: boolean; hull: number; heroDead: boolean; planeImpact: boolean;
}
export const PHASES: Phase[] = ['TITLE', 'CINEMATIC', 'INTERCEPT', 'CATCH', 'ARREST', 'SETDOWN', 'RESULTS'];

export function createMission(): MissionState { return { phase: 'TITLE', phaseTime: 0, time: 0, fail: null, failedIn: 'TITLE', checkpointPhase: 'INTERCEPT', checkpoint: null, freeFly: false, touched: false }; }
export function blankInput(): MissionInput { return { start: false, skip: false, distToPlane: 1e9, holding: false, planeSpeed: 110, overZone: false, touchdownSink: null, released: false, hull: 100, heroDead: false, planeImpact: false }; }
function go(m: MissionState, p: Phase): Phase { m.phase = p; m.phaseTime = 0; return p; }
function fail(m: MissionState, r: FailReason): Phase { m.fail = r; m.failedIn = m.phase; return go(m, 'FAILED'); }
export const isPlaying = (p: Phase): boolean => p === 'INTERCEPT' || p === 'CATCH' || p === 'ARREST' || p === 'SETDOWN';

/** Returns the new phase when a transition happens this step, else null. */
export function stepMission(m: MissionState, i: MissionInput, dt: number, cfg = { cinematic: 4, catchDist: 1500, hardSink: 10 }): Phase | null {
  m.phaseTime += dt;
  if (m.freeFly) return null;
  if (isPlaying(m.phase)) {
    m.time += dt;
    if (i.heroDead) return fail(m, 'YOU FELL');
    if (i.touchdownSink !== null && !m.touched) { if (i.touchdownSink > cfg.hardSink || m.phase !== 'SETDOWN') return fail(m, 'CRASH LANDING'); m.touched = true; }
    if (i.hull <= 0) return fail(m, 'HULL DESTROYED');
    if (i.planeImpact) return fail(m, 'AIRLINER IMPACT');
  }
  switch (m.phase) {
    case 'TITLE': return i.start ? go(m, 'CINEMATIC') : null;
    case 'CINEMATIC': return m.phaseTime >= cfg.cinematic || i.skip ? go(m, 'INTERCEPT') : null;
    case 'INTERCEPT': return i.distToPlane < cfg.catchDist ? go(m, 'CATCH') : null;
    case 'CATCH': return i.holding ? go(m, 'ARREST') : null;
    case 'ARREST': return i.holding && i.overZone && i.planeSpeed < 8 ? go(m, 'SETDOWN') : null;
    case 'SETDOWN': return m.touched && i.released ? go(m, 'RESULTS') : null;
    default: return null;
  }
}
export function saveCheckpoint(m: MissionState, data: unknown): void { m.checkpointPhase = m.phase; m.checkpoint = data; }
/** Retry from the phase checkpoint: returns the stored snapshot for the caller to restore. */
export function retry(m: MissionState): unknown { m.fail = null; m.touched = false; go(m, m.checkpointPhase); return m.checkpoint; }
export function restart(m: MissionState): void { const f = m.freeFly; Object.assign(m, createMission()); m.freeFly = f; }
```

### src/context.ts
```ts
import type { PerspectiveCamera, Scene, Vector3 } from 'three';
import type { Bus } from './core/events';
import type { Input } from './core/input';
import type { GameAudio } from './core/audio';
import type { Loop } from './core/loop';
import type { Grid } from './world/collision';
import type { FlightState } from './entities/flight';
import type { PlaneState } from './entities/holding';
import type { JetState } from './entities/jet';
import type { MissileState } from './entities/missile';
import type { MissionState } from './game/mission';
import type { Stats } from './game/scoring';
import type { Particles } from './vfx/particles';

export interface System { update(dt: number, timeScale: number): void; dispose(): void; }
/** Shared frame-level state written by systems and read by views. */
export interface Shared {
  aimPoint: Vector3; firing: boolean; hitKind: number; hitJet: number; hitMissile: number; lock: number; shake: number; blur: number; flash: number;
  fogWhite: number; kick: number; cine: number; wave: number; jetsLeft: number; missileNear: number; popup: string; popupT: number; radio: string[]; overheat: number;
  grab: number; holdTail: boolean; catchT: number; touchSink: number; turnBack: boolean; best: number; resultText: string;
}
export interface Ctx {
  scene: Scene; camera: PerspectiveCamera; bus: Bus; input: Input; audio: GameAudio; loop: Loop; grid: Grid; sun: Vector3;
  hero: FlightState; plane: PlaneState; jets: JetState[]; missiles: MissileState[]; mission: MissionState; stats: Stats; particles: Particles; s: Shared;
}
```

### src/vfx/particles.ts
```ts
import { CustomBlending, InstancedBufferAttribute, InstancedBufferGeometry, Mesh, OneFactor, OneMinusSrcAlphaFactor, PlaneGeometry, Scene, ShaderMaterial, Vector3 } from 'three';
import type { System } from '../context';

const MAX = 20000;
export interface Particles extends System {
  /** add: 1 = additive (sparks, fire), 0 = alpha blended (smoke, dust). grow: size change per second (fraction). */
  spawn(p: Vector3, vx: number, vy: number, vz: number, life: number, size: number, r: number, g: number, b: number, add: number, gravity: number, grow: number): void;
  clear(): void;
}
/** One instanced system for everything: sparks, fire, smoke, debris glow, tracers, dust, crowd flashes. */
export function createParticles(scene: Scene, sun: Vector3): Particles {
  const pos = new Float32Array(MAX * 3), vel = new Float32Array(MAX * 3), col = new Float32Array(MAX * 4), dat = new Float32Array(MAX * 2);
  const life = new Float32Array(MAX), maxLife = new Float32Array(MAX), size = new Float32Array(MAX), grav = new Float32Array(MAX), grow = new Float32Array(MAX);
  const geo = new InstancedBufferGeometry(), base = new PlaneGeometry(1, 1);
  geo.index = base.index; geo.setAttribute('position', base.getAttribute('position')); geo.setAttribute('uv', base.getAttribute('uv'));
  const aPos = new InstancedBufferAttribute(pos, 3), aCol = new InstancedBufferAttribute(col, 4), aDat = new InstancedBufferAttribute(dat, 2);
  geo.setAttribute('iPos', aPos); geo.setAttribute('iCol', aCol); geo.setAttribute('iDat', aDat);
  geo.instanceCount = MAX;
  const mat = new ShaderMaterial({
    uniforms: { uSun: { value: sun } }, depthWrite: false, transparent: true, blending: CustomBlending, blendSrc: OneFactor, blendDst: OneMinusSrcAlphaFactor,
    vertexShader: `attribute vec3 iPos; attribute vec4 iCol; attribute vec2 iDat; varying vec2 vUv; varying vec4 vCol; varying float vA; uniform vec3 uSun;
      void main() { vUv = uv; vA = iDat.y; vec4 mv = viewMatrix * vec4(iPos, 1.0); mv.xy += position.xy * iDat.x;
        vec3 sv = (viewMatrix * vec4(uSun, 0.0)).xyz; float lit = 0.6 + 0.6 * clamp(dot(normalize(vec3(position.xy, 0.4)), sv), 0.0, 1.0);
        vCol = vec4(iCol.rgb * mix(lit, 1.0, iCol.a), iCol.a); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec2 vUv; varying vec4 vCol; varying float vA;
      void main() { float d = length(vUv - 0.5) * 2.0; float a = smoothstep(1.0, 0.0, d) * vA; if (a < 0.003) discard; gl_FragColor = vec4(vCol.rgb * a, a * (1.0 - vCol.a)); }`,
  });
  const mesh = new Mesh(geo, mat); mesh.frustumCulled = false; mesh.renderOrder = 10; scene.add(mesh);
  let next = 0;
  return {
    spawn(p, vx, vy, vz, l, s, r, g, b, add, gravity, gr) {
      const i = next; next = (next + 1) % MAX;
      pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z; vel[i * 3] = vx; vel[i * 3 + 1] = vy; vel[i * 3 + 2] = vz;
      col[i * 4] = r; col[i * 4 + 1] = g; col[i * 4 + 2] = b; col[i * 4 + 3] = add;
      life[i] = maxLife[i] = l; size[i] = s; grav[i] = gravity; grow[i] = gr;
    },
    clear() { life.fill(0); dat.fill(0); aDat.needsUpdate = true; },
    update(dt) {
      for (let i = 0; i < MAX; i++) {
        if (life[i] <= 0) continue;
        life[i] -= dt;
        if (life[i] <= 0) { dat[i * 2] = 0; dat[i * 2 + 1] = 0; continue; }
        vel[i * 3 + 1] -= grav[i] * dt;
        pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
        size[i] *= 1 + grow[i] * dt;
        const k = life[i] / maxLife[i];
        dat[i * 2] = size[i]; dat[i * 2 + 1] = Math.min(1, k * 2) * Math.min(1, (1 - k) * 12 + 0.2);
      }
      aPos.needsUpdate = true; aDat.needsUpdate = true; aCol.needsUpdate = true;
    },
    dispose() { scene.remove(mesh); geo.dispose(); base.dispose(); mat.dispose(); },
  };
}
```

### src/vfx/explosions.ts
```ts
import { AdditiveBlending, BoxGeometry, DoubleSide, InstancedMesh, Mesh, MeshBasicMaterial, Object3D, PlaneGeometry, PointLight, RingGeometry, ShaderMaterial, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { Pool } from '../core/pool';
import { fireFrag, fireVert } from './shaders/fire';

interface Ball { alive: boolean; mesh: Mesh; ring: Mesh; mat: ShaderMaterial; t: number; size: number; }
export interface Explosions extends System { explode(p: Vector3, size: number): void; }
const DEB = 160;

/** Layered: light flash, noise fireball, shockwave ring, spinning debris with flaming trails, lingering lit smoke, shake. */
export function createExplosions(ctx: Ctx): Explosions {
  const plane = new PlaneGeometry(1, 1), ringGeo = new RingGeometry(0.85, 1, 48);
  const balls = new Pool<Ball>(8, () => {
    const mat = new ShaderMaterial({ vertexShader: fireVert, fragmentShader: fireFrag, uniforms: { uLife: { value: 0 }, uSeed: { value: Math.random() * 50 } }, transparent: true, depthWrite: false, blending: AdditiveBlending });
    const mesh = new Mesh(plane, mat), ring = new Mesh(ringGeo, new MeshBasicMaterial({ color: 0xffc080, transparent: true, blending: AdditiveBlending, depthWrite: false, side: DoubleSide }));
    mesh.visible = ring.visible = false; mesh.renderOrder = ring.renderOrder = 11; ctx.scene.add(mesh, ring);
    return { alive: false, mesh, ring, mat, t: 0, size: 1 };
  });
  const light = new PointLight(0xffa050, 0, 600, 1.5); ctx.scene.add(light);
  let lightT = 0;
  const debris = new InstancedMesh(new BoxGeometry(1, 0.3, 0.7), new MeshBasicMaterial({ color: 0x221a14 }), DEB);
  debris.frustumCulled = false; ctx.scene.add(debris);
  const dp = new Float32Array(DEB * 3), dv = new Float32Array(DEB * 3), dl = new Float32Array(DEB), o = new Object3D(), tp = new Vector3();
  let dn = 0, trailT = 0;
  o.scale.setScalar(0); o.updateMatrix(); for (let i = 0; i < DEB; i++) debris.setMatrixAt(i, o.matrix);
  return {
    explode(p, size) {
      const b = balls.get();
      if (b) { b.t = 0; b.size = size; b.mesh.position.copy(p); b.ring.position.copy(p); b.mesh.visible = b.ring.visible = true; b.mat.uniforms.uSeed.value = Math.random() * 50; }
      light.position.copy(p); light.intensity = 200 * size * 40; lightT = 0.1;
      for (let i = 0; i < 40; i++) { const k = dn; dn = (dn + 1) % DEB; dp[k * 3] = p.x; dp[k * 3 + 1] = p.y; dp[k * 3 + 2] = p.z; dv[k * 3] = (Math.random() - 0.5) * 90; dv[k * 3 + 1] = Math.random() * 60 - 10; dv[k * 3 + 2] = (Math.random() - 0.5) * 90; dl[k] = 2 + Math.random() * 2; }
      for (let i = 0; i < 30; i++) ctx.particles.spawn(p, (Math.random() - 0.5) * 14 * size, Math.random() * 8, (Math.random() - 0.5) * 14 * size, 4 + Math.random() * 2, 8 * size, 0.2, 0.17, 0.16, 0, -0.6, 0.25);
      for (let i = 0; i < 50; i++) ctx.particles.spawn(p, (Math.random() - 0.5) * 120, (Math.random() - 0.5) * 120, (Math.random() - 0.5) * 120, 0.5 + Math.random() * 0.6, 1.5, 6, 2.4, 0.5, 1, 20, 0);
      const d = ctx.camera.position.distanceTo(p);
      ctx.s.shake = Math.max(ctx.s.shake, Math.min(1.2, (60 * size) / Math.max(20, d)));
      if (d < 150) ctx.s.blur = Math.max(ctx.s.blur, 0.5);
      ctx.audio.explode(d);
    },
    update(dt) {
      lightT -= dt; if (lightT <= 0) light.intensity = 0;
      for (const b of balls.items) {
        if (!b.alive) continue;
        b.t += dt; const k = b.t / 0.8;
        if (k >= 1) { b.alive = false; b.mesh.visible = b.ring.visible = false; continue; }
        b.mat.uniforms.uLife.value = k; b.mesh.scale.setScalar(b.size * (22 + 30 * k)); b.mesh.quaternion.copy(ctx.camera.quaternion);
        const rk = Math.min(1, b.t / 0.4); b.ring.scale.setScalar(b.size * (5 + 70 * rk)); b.ring.quaternion.copy(ctx.camera.quaternion);
        (b.ring.material as MeshBasicMaterial).opacity = 1 - rk; b.ring.visible = rk < 1;
      }
      trailT += dt; const trail = trailT > 0.04; if (trail) trailT = 0;
      for (let i = 0; i < DEB; i++) {
        if (dl[i] <= 0) continue;
        dl[i] -= dt; dv[i * 3 + 1] -= 9.8 * dt;
        dp[i * 3] += dv[i * 3] * dt; dp[i * 3 + 1] += dv[i * 3 + 1] * dt; dp[i * 3 + 2] += dv[i * 3 + 2] * dt;
        o.position.set(dp[i * 3], dp[i * 3 + 1], dp[i * 3 + 2]); o.rotation.set(dl[i] * 7, dl[i] * 5, i); o.scale.setScalar(dl[i] > 0 && dp[i * 3 + 1] > 0 ? 1.2 : 0); o.updateMatrix(); debris.setMatrixAt(i, o.matrix);
        if (trail && dl[i] > 0) ctx.particles.spawn(tp.copy(o.position), 0, 1, 0, 0.5, 1.6, 4, 1.4, 0.2, 1, 0, 0.5);
      }
      debris.instanceMatrix.needsUpdate = true;
    },
    dispose() { for (const b of balls.items) { ctx.scene.remove(b.mesh, b.ring); b.mat.dispose(); } ctx.scene.remove(light, debris); plane.dispose(); ringGeo.dispose(); debris.geometry.dispose(); },
  };
}
```

### src/vfx/trails.ts
```ts
import { AdditiveBlending, BufferAttribute, BufferGeometry, DoubleSide, DynamicDrawUsage, Mesh, MeshBasicMaterial, NormalBlending, Scene, Vector3 } from 'three';

export interface Ribbon { push(p: Vector3, active: boolean): void; reset(): void; dispose(): void; mesh: Mesh; }
/** Camera-agnostic ribbon: a strip of N segments, width tapering and alpha fading along its length. */
export function createRibbon(scene: Scene, segments: number, width: number, color: number, additive: boolean, opacity: number): Ribbon {
  const pos = new Float32Array(segments * 6), colr = new Float32Array(segments * 8), idx: number[] = [];
  for (let i = 0; i < segments - 1; i++) idx.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
  const geo = new BufferGeometry(), aPos = new BufferAttribute(pos, 3), aCol = new BufferAttribute(colr, 4);
  aPos.setUsage(DynamicDrawUsage); geo.setAttribute('position', aPos); geo.setAttribute('color', aCol); geo.setIndex(idx);
  const mat = new MeshBasicMaterial({ color, vertexColors: true, transparent: true, opacity, depthWrite: false, side: DoubleSide, blending: additive ? AdditiveBlending : NormalBlending, fog: !additive });
  const mesh = new Mesh(geo, mat); mesh.frustumCulled = false; scene.add(mesh);
  const pts = new Float32Array(segments * 3), on = new Float32Array(segments);
  let init = false;
  const r: Ribbon = {
    mesh,
    reset() { init = false; on.fill(0); },
    push(p, active) {
      if (!init) { for (let i = 0; i < segments; i++) { pts[i * 3] = p.x; pts[i * 3 + 1] = p.y; pts[i * 3 + 2] = p.z; } init = true; }
      pts.copyWithin(3, 0, (segments - 1) * 3); on.copyWithin(1, 0, segments - 1);
      pts[0] = p.x; pts[1] = p.y; pts[2] = p.z; on[0] = active ? 1 : 0;
      for (let i = 0; i < segments; i++) {
        const k = 1 - i / segments, w = width * (0.4 + (additive ? k : 2 - k));
        pos[i * 6] = pts[i * 3]; pos[i * 6 + 1] = pts[i * 3 + 1] + w; pos[i * 6 + 2] = pts[i * 3 + 2];
        pos[i * 6 + 3] = pts[i * 3]; pos[i * 6 + 4] = pts[i * 3 + 1] - w; pos[i * 6 + 5] = pts[i * 3 + 2];
        for (let c = 0; c < 8; c++) colr[i * 8 + c] = c % 4 === 3 ? k * on[i] : 1;
      }
      aPos.needsUpdate = true; aCol.needsUpdate = true;
    },
    dispose() { scene.remove(mesh); geo.dispose(); mat.dispose(); },
  };
  return r;
}
```

### src/vfx/speedlines.ts
```ts
import { AdditiveBlending, Mesh, MeshBasicMaterial, RingGeometry, DoubleSide, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { createRibbon } from './trails';
import { T0, T1 } from '../core/math';

/** Speed streaks above 40 m/s, the boost ribbon and the sonic boom ring. */
export function createSpeedFx(ctx: Ctx): System {
  const ribbon = createRibbon(ctx.scene, 40, 0.25, 0xffb060, true, 0.7);
  const ring = new Mesh(new RingGeometry(0.8, 1, 48), new MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, blending: AdditiveBlending, depthWrite: false, side: DoubleSide }));
  ctx.scene.add(ring);
  let ringT = 9, acc = 0;
  const fwd = new Vector3();
  ctx.bus.on('boom', () => { ringT = 0; ring.position.copy(ctx.hero.position); ring.lookAt(T0.copy(ctx.hero.position).add(ctx.hero.velocity)); });
  return {
    update(dt) {
      const h = ctx.hero, sp = h.velocity.length();
      ribbon.push(h.position, h.boosting);
      ringT += dt; const k = Math.min(1, ringT / 0.6); ring.scale.setScalar(4 + 90 * k); (ring.material as MeshBasicMaterial).opacity = (1 - k) * 0.9;
      if (sp > 40 && h.mode !== 'holding') {
        acc += Math.min(400, (sp - 40) * 3) * dt;
        fwd.copy(h.velocity).multiplyScalar(1 / sp);
        while (acc >= 1) {
          acc -= 1;
          T1.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).multiplyScalar(36).addScaledVector(fwd, 60 + Math.random() * 40).add(h.position);
          ctx.particles.spawn(T1, -fwd.x * sp * 0.4, -fwd.y * sp * 0.4, -fwd.z * sp * 0.4, 0.35, 0.22, 1.2, 1.2, 1.4, 1, 0, 0);
        }
      }
    },
    dispose() { ribbon.dispose(); ctx.scene.remove(ring); ring.geometry.dispose(); },
  };
}
```

### src/world/sky.ts
```ts
import { AmbientLight, CanvasTexture, Color, DirectionalLight, Fog, HemisphereLight, Mesh, MeshBasicMaterial, PMREMGenerator, Scene, SphereGeometry, Vector3, WebGLRenderer } from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { Lensflare, LensflareElement } from 'three/addons/objects/Lensflare.js';
import { DEG } from '../core/math';

export interface SkyRig { sun: Vector3; sunMesh: Mesh; light: DirectionalLight; fog: Fog; fogColor: Color; bakeEnv(r: WebGLRenderer): void; follow(p: Vector3): void; dispose(): void; }
function glow(ring: boolean): CanvasTexture {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d')!;
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  if (ring) { gr.addColorStop(0, 'rgba(255,200,150,0)'); gr.addColorStop(0.8, 'rgba(255,180,120,0.05)'); gr.addColorStop(0.92, 'rgba(255,200,160,0.5)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); }
  else { gr.addColorStop(0, 'rgba(255,240,210,1)'); gr.addColorStop(0.25, 'rgba(255,170,90,0.5)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); }
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return new CanvasTexture(c);
}
export function createSky(scene: Scene): SkyRig {
  const sky = new Sky(); sky.scale.setScalar(40000);
  const el = 4 * DEG, az = 250 * DEG; // sun low in the west-south-west
  const sun = new Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)).normalize();
  const u = sky.material.uniforms;
  u['turbidity'].value = 8; u['rayleigh'].value = 2.5; u['mieCoefficient'].value = 0.02; u['mieDirectionalG'].value = 0.85; u['sunPosition'].value.copy(sun);
  scene.add(sky);
  const fogColor = new Color(0.95, 0.52, 0.3); // horizon colour of this sky configuration
  const fog = new Fog(fogColor.clone(), 300, 9000); scene.fog = fog;
  const sunMesh = new Mesh(new SphereGeometry(260, 24, 16), new MeshBasicMaterial({ color: new Color(8, 5, 2.4), transparent: true, depthWrite: false, fog: false }));
  scene.add(sunMesh);
  const light = new DirectionalLight(0xffb070, 3.2);
  light.castShadow = true; light.shadow.mapSize.set(2048, 2048);
  const sc = light.shadow.camera; sc.left = sc.bottom = -200; sc.right = sc.top = 200; sc.near = 10; sc.far = 3000; sc.updateProjectionMatrix();
  light.shadow.bias = -0.0005; light.shadow.normalBias = 0.6;
  scene.add(light, light.target, new HemisphereLight(0x8fa4d8, 0x3a2a22, 0.9), new AmbientLight(0x554466, 0.35));
  const flare = new Lensflare(), tg = glow(false), tr = glow(true);
  flare.addElement(new LensflareElement(tg, 520, 0));
  [[90, 0.35], [140, 0.55], [220, 0.8], [110, 1.05]].forEach(([s, d]) => flare.addElement(new LensflareElement(tr, s, d)));
  sunMesh.add(flare);
  const texel = 400 / 2048, right = new Vector3().crossVectors(sun, new Vector3(0, 1, 0)).normalize(), upv = new Vector3().crossVectors(right, sun).normalize(), c = new Vector3();
  return {
    sun, sunMesh, light, fog, fogColor,
    bakeEnv(r) {
      const pm = new PMREMGenerator(r), env = new Scene(), s2 = new Sky(); s2.scale.setScalar(1000);
      Object.keys(u).forEach((k) => { const v = u[k].value; if (typeof v === 'number') s2.material.uniforms[k].value = v; });
      s2.material.uniforms['sunPosition'].value.copy(sun); env.add(s2);
      scene.environment = pm.fromScene(env, 0, 1, 5000).texture; scene.environmentIntensity = 0.7; pm.dispose();
    },
    follow(p) {
      // snap the shadow box to shadow texels so the map does not shimmer
      const x = Math.round(p.dot(right) / texel) * texel, y = Math.round(p.dot(upv) / texel) * texel, z = p.dot(sun);
      c.set(0, 0, 0).addScaledVector(right, x).addScaledVector(upv, y).addScaledVector(sun, z);
      light.target.position.copy(c); light.position.copy(c).addScaledVector(sun, 1500);
      sunMesh.position.copy(p).addScaledVector(sun, 14000); sky.position.copy(p);
    },
    dispose() { scene.remove(sky, sunMesh, light); tg.dispose(); tr.dispose(); },
  };
}
```

### src/world/ground.ts
```ts
import { AdditiveBlending, Color, Mesh, MeshBasicMaterial, MeshStandardMaterial, PlaneGeometry, Scene } from 'three';

/** Asphalt ground plane plus a warm haze sheet at 30 m across the city bowl. */
export function createGround(scene: Scene): { dispose(): void } {
  const ground = new Mesh(new PlaneGeometry(40000, 40000), new MeshStandardMaterial({ color: 0x1b1c20, roughness: 0.95, metalness: 0 }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true;
  const haze = new Mesh(new PlaneGeometry(5200, 5200), new MeshBasicMaterial({ color: new Color(0.5, 0.22, 0.1), transparent: true, opacity: 0.13, blending: AdditiveBlending, depthWrite: false }));
  haze.rotation.x = -Math.PI / 2; haze.position.y = 30;
  scene.add(ground, haze);
  return { dispose() { scene.remove(ground, haze); ground.geometry.dispose(); haze.geometry.dispose(); } };
}
```

### src/world/city.ts
```ts
import { BoxGeometry, Color, CylinderGeometry, InstancedMesh, MeshBasicMaterial, MeshStandardMaterial, Object3D, Scene } from 'three';
import type { System } from '../context';
import { CONFIG } from '../config';
import { rng } from '../core/math';
import { cellBox, Grid, riverX } from './collision';
import { applyWindows, makeWindowTexture } from '../vfx/shaders/windows';

/** Two instanced tower meshes (concrete, glass), rooftop boxes, blinking antennas, streetlights. */
export function createCity(scene: Scene, g: Grid): System {
  const tex = makeWindowTexture(), box = new BoxGeometry(1, 1, 1), o = new Object3D(), r = rng(CONFIG.city.seed + 1), col = new Color();
  let nGlass = 0; for (let i = 0; i < g.h.length; i++) if (g.h[i] > 0 && g.glass[i]) nGlass++;
  let nAll = 0; for (let i = 0; i < g.h.length; i++) if (g.h[i] > 0) nAll++;
  const mc = new MeshStandardMaterial({ color: 0xffffff, metalness: 0.15, roughness: 0.6 }), mg = new MeshStandardMaterial({ color: 0xffffff, metalness: 0.9, roughness: 0.15 });
  applyWindows(mc, tex); applyWindows(mg, tex);
  const conc = new InstancedMesh(box, mc, Math.max(1, nAll - nGlass)), glass = new InstancedMesh(box, mg, Math.max(1, nGlass));
  const roofs = new InstancedMesh(box, new MeshStandardMaterial({ color: 0x3a3a40, roughness: 0.8 }), nAll);
  const tall: number[] = [];
  const b = { minX: 0, maxX: 0, minZ: 0, maxZ: 0, maxY: 0 };
  let ic = 0, ig = 0, ir = 0;
  for (let j = 0; j < g.n; j++) for (let i = 0; i < g.n; i++) {
    if (!cellBox(g, i, j, b)) continue;
    const cx = (b.minX + b.maxX) / 2, cz = (b.minZ + b.maxZ) / 2, w = b.maxX - b.minX;
    o.position.set(cx, b.maxY / 2, cz); o.scale.set(w, b.maxY, w); o.updateMatrix();
    if (g.glass[j * g.n + i]) { glass.setMatrixAt(ig, o.matrix); glass.setColorAt(ig++, col.setRGB(0.3 + r() * 0.1, 0.38 + r() * 0.1, 0.5 + r() * 0.1)); }
    else { conc.setMatrixAt(ic, o.matrix); const k = 0.45 + r() * 0.3; conc.setColorAt(ic++, col.setRGB(k, k * 0.95, k * 0.88)); }
    o.position.set(cx + (r() - 0.5) * 10, b.maxY + 1.5, cz + (r() - 0.5) * 10); o.scale.set(6 + r() * 8, 3, 5 + r() * 6); o.updateMatrix(); roofs.setMatrixAt(ir++, o.matrix);
    if (b.maxY > 150) tall.push(cx, b.maxY, cz);
  }
  const nA = tall.length / 3;
  const ant = new InstancedMesh(new CylinderGeometry(0.3, 0.5, 1, 5), new MeshStandardMaterial({ color: 0x555560, metalness: 0.6, roughness: 0.4 }), Math.max(1, nA));
  const blinkMat = new MeshBasicMaterial({ color: new Color(6, 0.3, 0.2) }), blink = new InstancedMesh(box, blinkMat, Math.max(1, nA));
  for (let k = 0; k < nA; k++) {
    o.position.set(tall[k * 3], tall[k * 3 + 1] + 14, tall[k * 3 + 2]); o.scale.set(1, 28, 1); o.updateMatrix(); ant.setMatrixAt(k, o.matrix);
    o.position.y += 14.5; o.scale.setScalar(1.3); o.updateMatrix(); blink.setMatrixAt(k, o.matrix);
  }
  // streetlights every 24 m along every 4th street
  const half = (g.n * g.cell) / 2, lamps: number[] = [];
  for (let s = 0; s <= g.n; s += 4) for (let d = -half; d < half; d += 24) {
    const line = (s - g.n / 2) * g.cell;
    if (Math.abs(line - riverX(d)) > g.cell * 2.5 && Math.abs(line - CONFIG.stadium.x) > 150) lamps.push(line + 5, d);
    if (Math.abs(d - riverX(line)) > g.cell * 2.5 && !(Math.abs(d - CONFIG.stadium.x) < 150 && Math.abs(line) < 150)) lamps.push(d, line + 5);
  }
  const lampMesh = new InstancedMesh(box, new MeshBasicMaterial({ color: new Color(5, 3.2, 1.4) }), lamps.length / 2);
  for (let k = 0; k < lamps.length / 2; k++) { o.position.set(lamps[k * 2], 8, lamps[k * 2 + 1]); o.scale.set(0.7, 0.3, 0.7); o.updateMatrix(); lampMesh.setMatrixAt(k, o.matrix); }
  conc.castShadow = glass.castShadow = true; conc.receiveShadow = glass.receiveShadow = true;
  const all = [conc, glass, roofs, ant, blink, lampMesh];
  for (const m of all) { m.instanceMatrix.needsUpdate = true; m.frustumCulled = false; scene.add(m); }
  let t = 0;
  return {
    update(dt) { t += dt; blinkMat.color.setRGB(Math.sin(t * 4) > 0.3 ? 6 : 0.4, 0.2, 0.15); },
    dispose() { for (const m of all) { scene.remove(m); m.dispose(); } box.dispose(); tex.dispose(); },
  };
}
```

### src/world/river.ts
```ts
import { BufferAttribute, BufferGeometry, Color, Mesh, Scene, ShaderMaterial, Vector3 } from 'three';
import type { System } from '../context';
import { CONFIG } from '../config';
import { riverX } from './collision';
import { waterFrag, waterVert } from '../vfx/shaders/water';

/** A sinuous strip five cells wide following riverX(z), shaded by the water shader. */
export function createRiver(scene: Scene, sun: Vector3, fog: Color): System {
  const N = 160, len = 9000, w = CONFIG.city.cell * 2.3, pos = new Float32Array((N + 1) * 6), idx: number[] = [];
  for (let i = 0; i <= N; i++) { const z = -len / 2 + (len * i) / N, x = riverX(z); pos.set([x - w, 0.4, z, x + w, 0.4, z], i * 6); if (i < N) idx.push(i * 2, i * 2 + 2, i * 2 + 1, i * 2 + 1, i * 2 + 2, i * 2 + 3); }
  const geo = new BufferGeometry(); geo.setAttribute('position', new BufferAttribute(pos, 3)); geo.setIndex(idx);
  const mat = new ShaderMaterial({ vertexShader: waterVert, fragmentShader: waterFrag, uniforms: { uTime: { value: 0 }, uSun: { value: sun }, uSky: { value: new Color(0.9, 0.5, 0.32) }, uFog: { value: fog } } });
  const mesh = new Mesh(geo, mat); mesh.frustumCulled = false; scene.add(mesh);
  return { update(dt) { mat.uniforms.uTime.value += dt; }, dispose() { scene.remove(mesh); geo.dispose(); mat.dispose(); } };
}
```

### src/world/clouds.ts
```ts
import { BackSide, CanvasTexture, Color, InstancedBufferAttribute, InstancedBufferGeometry, Mesh, MeshBasicMaterial, PlaneGeometry, RepeatWrapping, ShaderMaterial, SphereGeometry, Vector2, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { rng, T0 } from '../core/math';
import { cloudFrag, cloudVert } from '../vfx/shaders/cloud';

/** Two instanced billboard layers (150 + 150) at 500-900 m plus a cirrus dome. */
export function createClouds(ctx: Ctx, fog: Color): System {
  const r = rng(77), base = new PlaneGeometry(2, 2), sunScreen = new Vector2(1, 0.2), meshes: Mesh[] = [], centres: number[] = [];
  const mat = new ShaderMaterial({ vertexShader: cloudVert, fragmentShader: cloudFrag, uniforms: { uSunScreen: { value: sunScreen }, uFog: { value: fog } }, transparent: true, depthWrite: false });
  for (let layer = 0; layer < 2; layer++) {
    const geo = new InstancedBufferGeometry(); geo.index = base.index; geo.setAttribute('position', base.getAttribute('position')); geo.setAttribute('uv', base.getAttribute('uv'));
    const d = new Float32Array(150 * 4), rot = new Float32Array(150);
    for (let i = 0; i < 150; i++) {
      const cx = (r() - 0.3) * 12000, cz = (r() - 0.5) * 9000, y = 500 + layer * 200 + r() * 200;
      d.set([cx, y, cz, 140 + r() * 220], i * 4); rot[i] = (r() - 0.5) * 0.8; centres.push(cx, y, cz);
    }
    geo.setAttribute('iData', new InstancedBufferAttribute(d, 4)); geo.setAttribute('iRot', new InstancedBufferAttribute(rot, 1)); geo.instanceCount = 150;
    const m = new Mesh(geo, mat); m.frustumCulled = false; m.renderOrder = 5; ctx.scene.add(m); meshes.push(m);
  }
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d')!;
  for (let i = 0; i < 260; i++) { g.strokeStyle = `rgba(255,${180 + r() * 60},${150 + r() * 60},${0.03 + r() * 0.07})`; g.lineWidth = 1 + r() * 5; const x = r() * 512, y = r() * 256; g.beginPath(); g.moveTo(x, y); g.bezierCurveTo(x + 60, y - 8 + r() * 16, x + 120, y - 8 + r() * 16, x + 160 + r() * 80, y + r() * 10); g.stroke(); }
  const ct = new CanvasTexture(c); ct.wrapS = RepeatWrapping; ct.repeat.set(3, 1);
  const dome = new Mesh(new SphereGeometry(18000, 32, 8, 0, Math.PI * 2, 0, Math.PI * 0.42), new MeshBasicMaterial({ map: ct, transparent: true, side: BackSide, depthWrite: false, fog: false }));
  dome.scale.y = 0.18; ctx.scene.add(dome);
  const sv = new Vector3();
  return {
    update(dt) {
      sv.copy(ctx.sun).transformDirection(ctx.camera.matrixWorldInverse); sunScreen.set(sv.x, sv.y + 1e-3);
      dome.position.set(ctx.camera.position.x, 0, ctx.camera.position.z);
      const p = ctx.hero.position; let inside = false;
      if (p.y > 450 && p.y < 950) for (let i = 0; i < centres.length; i += 3) if (T0.set(centres[i], centres[i + 1], centres[i + 2]).distanceToSquared(p) < 90 * 90) { inside = true; break; }
      ctx.s.fogWhite += ((inside ? 1 : 0) - ctx.s.fogWhite) * Math.min(1, dt * 3);
    },
    dispose() { for (const m of meshes) { ctx.scene.remove(m); m.geometry.dispose(); } ctx.scene.remove(dome); dome.geometry.dispose(); mat.dispose(); base.dispose(); ct.dispose(); },
  };
}
```

### src/world/stadium.ts
```ts
import { AdditiveBlending, BoxGeometry, CanvasTexture, Color, ConeGeometry, CylinderGeometry, DoubleSide, InstancedMesh, Mesh, MeshBasicMaterial, MeshStandardMaterial, Object3D, PlaneGeometry, SRGBColorSpace, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { CONFIG } from '../config';

/** Metro Stadium: bowl tiers, 8,000 crowd quads, diamond field with the set-down zone, floodlights, scoreboard, flashes. */
export function createStadium(ctx: Ctx): System {
  const S = CONFIG.stadium, o = new Object3D(), objs: Object3D[] = [], A = 140, B = 110;
  const fc = document.createElement('canvas'); fc.width = 1024; fc.height = 800; const g = fc.getContext('2d')!;
  for (let i = 0; i < 16; i++) { g.fillStyle = i % 2 ? '#2f7d32' : '#2a6f2d'; g.fillRect(i * 64, 0, 64, 800); }
  g.fillStyle = '#b58a55'; g.beginPath(); g.moveTo(170, 400); g.lineTo(330, 240); g.lineTo(490, 400); g.lineTo(330, 560); g.closePath(); g.fill();
  g.fillStyle = '#2f7d32'; g.beginPath(); g.moveTo(215, 400); g.lineTo(330, 285); g.lineTo(445, 400); g.lineTo(330, 515); g.closePath(); g.fill();
  g.strokeStyle = '#fff'; g.lineWidth = 4; g.beginPath(); g.moveTo(170, 400); g.lineTo(520, 50); g.moveTo(170, 400); g.lineTo(520, 750); g.stroke();
  g.strokeStyle = '#ffe14a'; g.lineWidth = 8; g.setLineDash([28, 16]); g.strokeRect(512 - 60 * 3.65, 400 - 40 * 3.65, 120 * 3.65, 80 * 3.65); g.setLineDash([]);
  g.fillStyle = '#ffe14a'; g.font = 'bold 30px system-ui'; g.textAlign = 'center'; g.fillText('SET-DOWN ZONE', 512, 400 - 40 * 3.65 - 14);
  const ft = new CanvasTexture(fc); ft.colorSpace = SRGBColorSpace;
  const field = new Mesh(new PlaneGeometry(280, 220), new MeshStandardMaterial({ map: ft, roughness: 0.9 }));
  field.rotation.x = -Math.PI / 2; field.position.set(S.x, 0.3, S.z); field.receiveShadow = true; objs.push(field);
  const steps = new InstancedMesh(new BoxGeometry(1, 1, 1), new MeshStandardMaterial({ color: 0x8a8d94, roughness: 0.8 }), 3 * 56);
  const crowd = new InstancedMesh(new PlaneGeometry(0.8, 1.1), new MeshBasicMaterial({ side: DoubleSide }), 8000), col = new Color(), seats: number[] = [];
  let n = 0;
  for (let tier = 0; tier < 3; tier++) for (let k = 0; k < 56; k++) {
    const a = (k / 56) * Math.PI * 2, ra = A + 8 + tier * 16, rb = B + 8 + tier * 16;
    o.position.set(S.x + Math.cos(a) * ra, 6 + tier * 9, S.z + Math.sin(a) * rb); o.rotation.set(0, -a, 0); o.scale.set(16, 12 + tier * 18, ((ra + rb) * Math.PI) / 56 + 2); o.updateMatrix(); steps.setMatrixAt(n++, o.matrix);
  }
  for (let i = 0; i < 8000; i++) {
    const tier = i % 3, a = Math.random() * Math.PI * 2, t = Math.random(), ra = A + 2 + tier * 16 + t * 12, rb = B + 2 + tier * 16 + t * 12;
    o.position.set(S.x + Math.cos(a) * ra, 13 + tier * 18 + t * 2 + (tier === 0 ? 0 : 1), S.z + Math.sin(a) * rb); o.rotation.set(0, -a + Math.PI / 2, 0); o.scale.setScalar(1); o.updateMatrix();
    crowd.setMatrixAt(i, o.matrix); crowd.setColorAt(i, col.setHSL(Math.random(), 0.6, 0.35 + Math.random() * 0.3)); if (i % 4 === 0) seats.push(o.position.x, o.position.y, o.position.z);
  }
  steps.receiveShadow = true; steps.frustumCulled = crowd.frustumCulled = false; objs.push(steps, crowd);
  const mastGeo = new CylinderGeometry(1.2, 1.8, 90, 6), headGeo = new BoxGeometry(16, 8, 2), coneGeo = new ConeGeometry(55, 130, 20, 1, true);
  const headMat = new MeshBasicMaterial({ color: new Color(9, 8.5, 7.5) }), coneMat = new MeshBasicMaterial({ color: 0xfff2d0, transparent: true, opacity: 0.045, blending: AdditiveBlending, depthWrite: false, side: DoubleSide });
  for (let k = 0; k < 4; k++) {
    const sx = k % 2 ? 1 : -1, sz = k < 2 ? 1 : -1, x = S.x + sx * 175, z = S.z + sz * 145;
    const mast = new Mesh(mastGeo, new MeshStandardMaterial({ color: 0x55585e, metalness: 0.6, roughness: 0.5 })); mast.position.set(x, 45, z);
    const head = new Mesh(headGeo, headMat); head.position.set(x, 92, z); head.lookAt(S.x, 0, S.z);
    const cone = new Mesh(coneGeo, coneMat); cone.position.set((x + S.x) / 2 + sx * 30, 46, (z + S.z) / 2 + sz * 26); cone.lookAt(x, 150, z); cone.rotateX(Math.PI / 2);
    objs.push(mast, head, cone);
  }
  const sc = document.createElement('canvas'); sc.width = 512; sc.height = 256; const sg = sc.getContext('2d')!, st = new CanvasTexture(sc); st.colorSpace = SRGBColorSpace;
  function board(a: string, b: string, c: string): void { sg.fillStyle = '#05080c'; sg.fillRect(0, 0, 512, 256); sg.fillStyle = c; sg.textAlign = 'center'; sg.font = 'bold 84px system-ui'; sg.fillText(a, 256, 120); sg.font = '40px system-ui'; sg.fillText(b, 256, 200); st.needsUpdate = true; }
  board('METRO 3 : 2', 'BOTTOM OF THE 9TH', '#ffcf60');
  const sb = new Mesh(new PlaneGeometry(70, 35), new MeshBasicMaterial({ map: st, color: new Color(2.2, 2.2, 2.2) })); sb.position.set(S.x - 185, 80, S.z); sb.rotation.y = Math.PI / 2; objs.push(sb);
  for (const m of objs) ctx.scene.add(m);
  let storm = 0; const p = new Vector3();
  ctx.bus.on('touchdown', () => { storm = 12; board('218 SAVED', 'FLIGHT 227', '#7dffa0'); });
  ctx.bus.on('phaseChanged', (e) => { if (e.phase === 'INTERCEPT') { storm = 0; board('METRO 3 : 2', 'BOTTOM OF THE 9TH', '#ffcf60'); } });
  return {
    update(dt) {
      storm = Math.max(0, storm - dt);
      const near = ctx.plane.position.distanceTo(field.position) < 1500 ? 1 : 0, rate = storm > 0 ? 900 : near * 25;
      let k = rate * dt; if (Math.random() < k % 1) k += 1;
      for (let i = 0; i < Math.floor(k); i++) { const s = Math.floor(Math.random() * (seats.length / 3)) * 3; ctx.particles.spawn(p.set(seats[s], seats[s + 1] + 1, seats[s + 2]), 0, 0, 0, 0.12, 4, 8, 8, 9, 1, 0, 0); }
    },
    dispose() { for (const m of objs) ctx.scene.remove(m); ft.dispose(); st.dispose(); mastGeo.dispose(); headGeo.dispose(); coneGeo.dispose(); },
  };
}
```

### src/entities/hero.ts
```ts
import { BoxGeometry, BufferAttribute, BufferGeometry, CapsuleGeometry, Color, DoubleSide, Group, Mesh, MeshBasicMaterial, MeshStandardMaterial, SphereGeometry, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { damp, T0, T1 } from '../core/math';

/** Procedural hero: capsule torso, sphere head, box limbs, glowing eyes, 7-segment Verlet cape. Poses blend by mode. */
export function createHero(ctx: Ctx): System & { head: Mesh } {
  const root = new Group(), body = new Group(); root.add(body);
  const red = new MeshStandardMaterial({ color: 0x8c0f14, roughness: 0.5, metalness: 0.2 }), gold = new MeshStandardMaterial({ color: 0xd9a13a, roughness: 0.3, metalness: 0.8 }), dark = new MeshStandardMaterial({ color: 0x15151a, roughness: 0.6 }), skin = new MeshStandardMaterial({ color: 0xd8a787, roughness: 0.7 });
  const eyeMat = new MeshBasicMaterial({ color: new Color(1, 0.2, 0.1) });
  const mk = (g: BufferGeometry, m: MeshStandardMaterial | MeshBasicMaterial, x: number, y: number, z: number, parent: Group = body): Mesh => { const me = new Mesh(g, m); me.position.set(x, y, z); me.castShadow = true; parent.add(me); return me; };
  mk(new CapsuleGeometry(0.26, 0.5, 4, 10), red, 0, 0.25, 0); mk(new BoxGeometry(0.5, 0.1, 0.3), gold, 0, -0.1, 0);
  const head = mk(new SphereGeometry(0.16, 14, 10), skin, 0, 0.82, 0);
  mk(new SphereGeometry(0.03, 6, 6), eyeMat, -0.08, 0.84, -0.14); mk(new SphereGeometry(0.03, 6, 6), eyeMat, 0.08, 0.84, -0.14);
  const limb = (x: number, y: number, len: number, m: MeshStandardMaterial, boot: boolean): Group => { const g = new Group(); g.position.set(x, y, 0); body.add(g); mk(new BoxGeometry(0.14, len, 0.14), m, 0, -len / 2, 0, g); if (boot) mk(new BoxGeometry(0.16, 0.22, 0.2), dark, 0, -len, -0.02, g); else mk(new BoxGeometry(0.15, 0.14, 0.15), gold, 0, -len, 0, g); return g; };
  const armL = limb(-0.36, 0.6, 0.62, red, false), armR = limb(0.36, 0.6, 0.62, red, false), legL = limb(-0.13, -0.15, 0.8, red, true), legR = limb(0.13, -0.15, 0.8, red, true);
  // cape
  const N = 8, cp = new Float32Array(N * 3), cq = new Float32Array(N * 3), pos = new Float32Array(N * 6), idx: number[] = [];
  for (let i = 0; i < N - 1; i++) idx.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
  const cgeo = new BufferGeometry(), cattr = new BufferAttribute(pos, 3); cgeo.setAttribute('position', cattr); cgeo.setIndex(idx);
  const cape = new Mesh(cgeo, new MeshStandardMaterial({ color: 0xa3141a, roughness: 0.7, side: DoubleSide })); cape.frustumCulled = false; cape.castShadow = true;
  ctx.scene.add(root, cape);
  let prone = 0, sweep = 0, brace = 0, t = 0, capeInit = false;
  const anchor = new Vector3(), right = new Vector3();
  return {
    head,
    update(dt) {
      const h = ctx.hero, sp = h.velocity.length(); t += dt;
      root.position.copy(h.position); root.quaternion.copy(h.bodyQuat);
      if (h.mode === 'hover') root.position.y += Math.sin(t * Math.PI * 1.6) * 0.15;
      prone = damp(prone, h.mode === 'flight' ? 1 : 0, 1 / 0.16, dt); sweep = damp(sweep, h.boosting ? 1 : 0, 6, dt); brace = damp(brace, h.mode === 'holding' ? 1 : 0, 6, dt);
      body.rotation.x = -Math.PI / 2 * prone + 0.52 * brace;
      const armA = Math.PI * prone * (1 - sweep) + 0.25 * sweep * prone + Math.PI * 0.92 * brace;
      armL.rotation.x = armR.rotation.x = -armA; armL.rotation.z = -0.12 - 0.2 * sweep; armR.rotation.z = 0.12 + 0.2 * sweep;
      legL.rotation.x = 0.05 + 0.25 * brace; legR.rotation.x = -0.05 * prone - 0.1 * brace;
      const e = 0.6 + h.heat * 0.03 + (ctx.s.firing ? 6 : 0); eyeMat.color.setRGB(ctx.s.overheat > 0 ? 0.05 : e, ctx.s.overheat > 0 ? 0.02 : e * 0.15, 0.02);
      // Verlet cape: gravity, relative-wind drag, flutter
      root.updateMatrixWorld(true);
      anchor.set(0, 0.62, 0.2).applyMatrix4(body.matrixWorld); right.set(1, 0, 0).transformDirection(body.matrixWorld);
      if (!capeInit || anchor.distanceToSquared(T0.set(cp[0], cp[1], cp[2])) > 400) { for (let i = 0; i < N; i++) { cp[i * 3] = cq[i * 3] = anchor.x; cp[i * 3 + 1] = cq[i * 3 + 1] = anchor.y - i * 0.2; cp[i * 3 + 2] = cq[i * 3 + 2] = anchor.z; } capeInit = true; }
      const sdt = Math.min(dt, 0.033), wind = Math.min(1, sp / 30);
      cp[0] = anchor.x; cp[1] = anchor.y; cp[2] = anchor.z;
      for (let i = 1; i < N; i++) {
        const a = i * 3, vx = (cp[a] - cq[a]) * 0.9, vy = (cp[a + 1] - cq[a + 1]) * 0.9, vz = (cp[a + 2] - cq[a + 2]) * 0.9;
        cq[a] = cp[a]; cq[a + 1] = cp[a + 1]; cq[a + 2] = cp[a + 2];
        const fl = Math.sin(t * 22 + i * 1.3) * wind * 6;
        cp[a] += vx + (-h.velocity.x * 0.9 * wind + right.x * fl) * sdt * sdt * 30 + h.velocity.x * sdt * (1 - 0.5 * wind);
        cp[a + 1] += vy + (-9.8 * (1 - wind * 0.8) - h.velocity.y * 0.9 * wind + fl * 0.5) * sdt * sdt * 30 + h.velocity.y * sdt * (1 - 0.5 * wind);
        cp[a + 2] += vz + (-h.velocity.z * 0.9 * wind + right.z * fl) * sdt * sdt * 30 + h.velocity.z * sdt * (1 - 0.5 * wind);
      }
      for (let it = 0; it < 3; it++) for (let i = 1; i < N; i++) {
        const a = i * 3, b = a - 3; T0.set(cp[a] - cp[b], cp[a + 1] - cp[b + 1], cp[a + 2] - cp[b + 2]); const l = T0.length();
        if (l > 1e-5) { T0.multiplyScalar(0.2 / l); cp[a] = cp[b] + T0.x; cp[a + 1] = cp[b + 1] + T0.y; cp[a + 2] = cp[b + 2] + T0.z; }
      }
      for (let i = 0; i < N; i++) { const w = 0.3 * (0.75 + 0.25 * i / N); T1.set(cp[i * 3], cp[i * 3 + 1], cp[i * 3 + 2]); pos.set([T1.x - right.x * w, T1.y - right.y * w, T1.z - right.z * w, T1.x + right.x * w, T1.y + right.y * w, T1.z + right.z * w], i * 6); }
      cattr.needsUpdate = true; cgeo.computeVertexNormals();
    },
    dispose() { ctx.scene.remove(root, cape); cgeo.dispose(); },
  };
}
```

### src/entities/airliner.ts
```ts
import { BoxGeometry, BufferAttribute, BufferGeometry, CapsuleGeometry, Color, ConeGeometry, CylinderGeometry, Matrix4, Mesh, MeshBasicMaterial, MeshStandardMaterial, Quaternion, SphereGeometry, Vector3 } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { Ctx, System } from '../context';
import { part } from '../core/renderer';
import { DEG, quatFromYPR, T0, T1 } from '../core/math';
import { grabPoint } from './holding';
import { createRibbon } from '../vfx/trails';

const M = (x: number, y: number, z: number, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1): Matrix4 => new Matrix4().compose(new Vector3(x, y, z), quatFromYPR(new Quaternion(), ry, rx, rz), new Vector3(sx, sy, sz));

/** Procedural airliner (nose toward -Z), engine fire, smoke ribbon, nav lights, gear, grab markers, nose crumple. */
export function createAirliner(ctx: Ctx): System {
  const parts: BufferGeometry[] = [];
  const fus = part(new CapsuleGeometry(3, 56, 8, 20), 0xf2f2f2, M(0, 0, 0, Math.PI / 2));
  const fc = fus.getAttribute('color') as BufferAttribute, fp = fus.getAttribute('position');
  for (let i = 0; i < fp.count; i++) { // blue belly, red cheatline, window strip, cockpit band
    const y = fp.getY(i), z = fp.getZ(i);
    if (y < -1.2) fc.setXYZ(i, 0.08, 0.16, 0.45); else if (y < -0.5) fc.setXYZ(i, 0.75, 0.06, 0.06);
    else if (y > 0.5 && y < 1.4 && Math.abs(z) < 24) fc.setXYZ(i, 0.05, 0.05, 0.06);
    if (z < -28 && y > 0.6 && y < 2.2) fc.setXYZ(i, 0.03, 0.03, 0.05);
  }
  parts.push(fus);
  for (const s of [-1, 1]) {
    parts.push(part(new BoxGeometry(30, 0.5, 7), 0xe6e6e8, M(s * 16, -1 + 1.5, 2, 0, -s * 0.45, s * 0.1)));
    parts.push(part(new CylinderGeometry(1.5, 1.3, 6, 12), 0xcfd2d8, M(s * 10, -2.6, -1, Math.PI / 2)));
    parts.push(part(new BoxGeometry(10, 0.35, 4), 0xe6e6e8, M(s * 5.5, 1.5, 28, 0, -s * 0.4, s * 0.08)));
  }
  parts.push(part(new BoxGeometry(0.4, 10, 6), 0xc41c1c, M(0, 6.5, 28, -0.45)));
  const geo = mergeGeometries(parts)!;
  const base = (geo.getAttribute('position').array as Float32Array).slice();
  const mat = new MeshStandardMaterial({ vertexColors: true, metalness: 0.7, roughness: 0.3 });
  const mesh = new Mesh(geo, mat); mesh.castShadow = true; mesh.frustumCulled = false; ctx.scene.add(mesh);
  const tail = new Mesh(part(new ConeGeometry(2.9, 9, 16), 0xf2f2f2, M(0, 0.6, 33, Math.PI / 2)), mat); mesh.add(tail);
  const winMat = new MeshBasicMaterial({ color: new Color(3, 2.2, 1.2) }), wins: BufferGeometry[] = [];
  for (let i = 0; i < 40; i++) for (const s of [-1, 1]) wins.push(new BoxGeometry(0.1, 0.45, 0.35).applyMatrix4(M(s * 2.98, 0.9, -23 + i * 1.2)));
  mesh.add(new Mesh(mergeGeometries(wins)!, winMat));
  const lightGeo = new SphereGeometry(0.5, 8, 6), navR = new Mesh(lightGeo, new MeshBasicMaterial({ color: new Color(8, 0.3, 0.2) })), navG = new Mesh(lightGeo, new MeshBasicMaterial({ color: new Color(0.2, 8, 0.4) })), strobe = new Mesh(lightGeo, new MeshBasicMaterial({ color: new Color(9, 9, 9) }));
  navR.position.set(-30, 3.2, 9); navG.position.set(30, 3.2, 9); strobe.position.set(0, 11.5, 31); mesh.add(navR, navG, strobe);
  const gear = new Mesh(mergeGeometries([new CylinderGeometry(0.35, 0.35, 4, 6).applyMatrix4(M(0, -4.5, -22)), new CylinderGeometry(0.4, 0.4, 4, 6).applyMatrix4(M(-4, -4.5, 3)), new CylinderGeometry(0.4, 0.4, 4, 6).applyMatrix4(M(4, -4.5, 3))])!, new MeshStandardMaterial({ color: 0x222226 })); mesh.add(gear);
  const markGeo = new SphereGeometry(1.2, 12, 8), markN = new Mesh(markGeo, new MeshBasicMaterial({ color: new Color(0.4, 4, 5), transparent: true, opacity: 0.8 })), markT = new Mesh(markGeo, new MeshBasicMaterial({ color: new Color(5, 2, 0.3), transparent: true, opacity: 0.8 }));
  ctx.scene.add(markN, markT);
  const smoke = createRibbon(ctx.scene, 200, 5, 0x555558, false, 0.55);
  let t = 0, fireAcc = 0, smokeAcc = 0, gearK = 0, crumple = 0;
  const eng = new Vector3();
  return {
    update(dt) {
      const p = ctx.plane; t += dt;
      mesh.position.copy(p.position); quatFromYPR(mesh.quaternion, p.yaw, p.pitch, p.roll); mesh.updateMatrixWorld();
      tail.visible = !p.tailTorn; strobe.visible = t % 1 < 0.08;
      const sp = p.velocity.length(), wantGear = p.position.y < 200 && sp < 20 ? 1 : 0; gearK += (wantGear - gearK) * Math.min(1, dt * 1.5); gear.scale.y = Math.max(0.01, gearK); gear.visible = gearK > 0.02;
      eng.set(-10, -2.6, 2).applyMatrix4(mesh.matrixWorld);
      fireAcc += dt * 70; while (fireAcc >= 1) { fireAcc -= 1; ctx.particles.spawn(eng, p.velocity.x * 0.7 + (Math.random() - 0.5) * 6, p.velocity.y * 0.7 + Math.random() * 5, p.velocity.z * 0.7 + (Math.random() - 0.5) * 6, 0.5 + Math.random() * 0.4, 3.2, 5, 1.6 + Math.random(), 0.2, 1, 0, 1.2); }
      smokeAcc += dt; if (smokeAcc > 0.12) { smokeAcc = 0; smoke.push(eng, !p.landed || p.t < 5); }
      const dist = ctx.hero.position.distanceTo(p.position), show = dist < 60 + 30 && !p.held && !p.landed && !p.dead, pulse = 0.8 + 0.3 * Math.sin(t * 8);
      markN.visible = show; markT.visible = show && !p.tailTorn; grabPoint(p, false, markN.position); grabPoint(p, true, markT.position); markN.scale.setScalar(pulse); markT.scale.setScalar(pulse);
      // nose skin crumples above stress 70
      const target = Math.max(0, (p.stress - 70) / 30); if (Math.abs(target - crumple) > 0.02) {
        crumple = target; const a = geo.getAttribute('position'), arr = a.array as Float32Array;
        for (let i = 0; i < a.count; i++) { const z = base[i * 3 + 2]; if (z > -24) continue; const k = crumple * Math.min(1, (-24 - z) / 6) * 0.5; arr[i * 3] = base[i * 3] * (1 - k * (0.5 + 0.5 * Math.sin(i * 12.9))); arr[i * 3 + 1] = base[i * 3 + 1] * (1 - k * (0.5 + 0.5 * Math.sin(i * 7.3))); arr[i * 3 + 2] = z + k * 3 * Math.sin(i * 3.1); }
        a.needsUpdate = true;
      }
      if (p.dead) { T0.copy(p.position); ctx.particles.spawn(T0, 0, 4, 0, 1.2, 9, 4, 1.4, 0.2, 1, 0, 0.8); }
      T1.set(0, 0, 0);
    },
    dispose() { ctx.scene.remove(mesh, markN, markT); geo.dispose(); mat.dispose(); smoke.dispose(); lightGeo.dispose(); markGeo.dispose(); },
  };
}
export const NOSE_PITCH_OFFSET = 30 * DEG;
```

### src/entities/laser.ts
```ts
import { AdditiveBlending, Color, CylinderGeometry, Mesh, MeshBasicMaterial, PointLight, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { CONFIG } from '../config';
import { DEG, safeNorm, T0 } from '../core/math';
import { surfaceY } from '../world/collision';
import { isPlaying } from '../game/mission';

export const HIT_NONE = 0, HIT_JET = 1, HIT_MISSILE = 2, HIT_WORLD = 3;
/** Two eye beams converging on the crosshair aim point; heat, overheat, aim assist, lock-on, scoring line on buildings. */
export function createLaser(ctx: Ctx, head: Mesh): System {
  const L = CONFIG.laser, geo = new CylinderGeometry(1, 1, 1, 8, 1, true).rotateX(Math.PI / 2).translate(0, 0, 0.5);
  const coreMat = new MeshBasicMaterial({ color: new Color(4, 4, 4), fog: false }), glowMat = new MeshBasicMaterial({ color: new Color(4, 0.25, 0.1), transparent: true, opacity: 0.45, blending: AdditiveBlending, depthWrite: false, fog: false });
  const beams = [0, 1].map(() => { const c = new Mesh(geo, coreMat), g = new Mesh(geo, glowMat); c.frustumCulled = g.frustumCulled = false; ctx.scene.add(c, g); return { c, g }; });
  const light = new PointLight(0xff3020, 0, 20, 1.2); ctx.scene.add(light);
  const o = new Vector3(), d = new Vector3(), eye = new Vector3(), tmp = new Vector3();
  let sparkAcc = 0, t = 0, pulse = 0;
  function raySphere(c: Vector3, r: number): number { tmp.subVectors(c, o); const b = tmp.dot(d); if (b < 0) return -1; const q = tmp.lengthSq() - b * b; return q > r * r ? -1 : b - Math.sqrt(r * r - q); }
  return {
    update(dt) {
      const s = ctx.s, h = ctx.hero; t += dt;
      ctx.camera.getWorldPosition(o); ctx.camera.getWorldDirection(d);
      // lock-on
      if (ctx.input.rmbPressed) {
        if (s.lock >= 0) s.lock = -1; else { let best = Math.cos(L.lockDeg * DEG); ctx.jets.forEach((j, i) => { if (!j.alive) return; const c = safeNorm(tmp.subVectors(j.position, o)).dot(d); if (c > best) { best = c; s.lock = i; } }); }
      }
      if (s.lock >= 0) { const j = ctx.jets[s.lock]; if (!j.alive || safeNorm(tmp.subVectors(j.position, o)).dot(d) < Math.cos(L.breakDeg * DEG)) s.lock = -1; }
      // aim assist: magnetise within 3 degrees of a jet
      let assist = -1, bestC = Math.cos(L.assistDeg * DEG);
      ctx.jets.forEach((j, i) => { if (!j.alive) return; const c = safeNorm(tmp.subVectors(j.position, o)).dot(d); if (c > bestC) { bestC = c; assist = i; } });
      if (assist >= 0) safeNorm(d.lerp(safeNorm(tmp.subVectors(ctx.jets[assist].position, o)), 0.7));
      // raycast
      let best = L.range; s.hitKind = HIT_NONE; s.hitJet = -1; s.hitMissile = -1;
      ctx.jets.forEach((j, i) => { if (!j.alive) return; const k = raySphere(j.position, 11); if (k > 0 && k < best) { best = k; s.hitKind = HIT_JET; s.hitJet = i; } });
      ctx.missiles.forEach((m, i) => { if (!m.alive) return; const k = raySphere(m.position, 4); if (k > 0 && k < best) { best = k; s.hitKind = HIT_MISSILE; s.hitMissile = i; } });
      for (let k = 6; k < best; k += 6) { const y = o.y + d.y * k; if (y < 0 || (y < 430 && surfaceY(ctx.grid, o.x + d.x * k, o.z + d.z * k) > y)) { best = k; s.hitKind = HIT_WORLD; s.hitJet = -1; s.hitMissile = -1; break; } }
      s.aimPoint.copy(o).addScaledVector(d, best);
      // heat
      const can = (isPlaying(ctx.mission.phase) || ctx.mission.freeFly) && h.mode !== 'stunned' && h.hp > 0;
      if (s.overheat > 0) { s.overheat -= dt; if (s.overheat <= 0) { pulse = 1; h.heat = 60; } }
      s.firing = ctx.input.lmb && can && s.overheat <= 0;
      if (s.firing) { h.heat += (100 / L.heatTime) * dt; ctx.stats.fireTime += dt; if (s.hitKind === HIT_JET || s.hitKind === HIT_MISSILE) ctx.stats.onTarget += dt; if (h.heat >= 100) { h.heat = 100; s.overheat = L.overheat; s.firing = false; s.popup = 'OVERHEAT'; s.popupT = 1.5; } }
      else if (s.overheat <= 0) h.heat = Math.max(0, h.heat - (100 / L.coolTime) * dt);
      if (!s.firing) { s.hitKind = s.hitKind === HIT_WORLD ? HIT_WORLD : HIT_NONE; if (!ctx.input.lmb) { s.hitJet = -1; s.hitMissile = -1; } }
      pulse = Math.max(0, pulse - dt * 3);
      // beams
      const flick = 1 - 0.05 * (Math.floor(t * 30) % 2), thin = h.heat > 75 ? 0.75 : 1;
      head.updateWorldMatrix(true, false);
      beams.forEach((b, i) => {
        b.c.visible = b.g.visible = s.firing; if (!s.firing) return;
        eye.set(i ? 0.08 : -0.08, 0.02, -0.15).applyMatrix4(head.matrixWorld);
        const len = eye.distanceTo(s.aimPoint);
        b.c.position.copy(eye); b.g.position.copy(eye); b.c.lookAt(s.aimPoint); b.g.lookAt(s.aimPoint);
        b.c.scale.set(0.06 * thin * flick, 0.06 * thin * flick, len); b.g.scale.set(0.25 * thin * flick, 0.25 * thin * flick, len);
      });
      light.intensity = s.firing && best < L.range ? 30 * 40 : pulse * 400; light.position.copy(s.firing ? s.aimPoint : h.position).addScaledVector(d, -1);
      if (s.firing && best < L.range) {
        sparkAcc += 40 * dt; T0.copy(s.aimPoint).addScaledVector(d, -0.5);
        while (sparkAcc >= 1) { sparkAcc -= 1; ctx.particles.spawn(T0, (Math.random() - 0.5) * 24, Math.random() * 16, (Math.random() - 0.5) * 24, 0.4, 0.5, 6, 2.5, 0.6, 1, 25, 0); }
        if (s.hitKind === HIT_WORLD) ctx.particles.spawn(T0, 0, 0, 0, 1.5, 1.6, 5, 1.2, 0.15, 1, 0, -0.3); // molten scoring line
      }
    },
    dispose() { for (const b of beams) ctx.scene.remove(b.c, b.g); ctx.scene.remove(light); geo.dispose(); coreMat.dispose(); glowMat.dispose(); },
  };
}
```

### src/entities/wreck.ts
```ts
import { BoxGeometry, CapsuleGeometry, Color, ConeGeometry, CylinderGeometry, InstancedMesh, Matrix4, MeshBasicMaterial, MeshStandardMaterial, Object3D, Quaternion, SphereGeometry, Vector3 } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import type { Ctx, System } from '../context';
import { CONFIG } from '../config';
import { Pool } from '../core/pool';
import { part } from '../core/renderer';
import { quatFromYPR, safeNorm, T0, T1, T2 } from '../core/math';
import { JetOut, JetState, spawnJet, stepJet } from './jet';
import { launchMissile, M_FLY, M_HIT, stepMissile } from './missile';
import { damageHero } from './flight';
import { surfaceY } from '../world/collision';
import type { Explosions } from '../vfx/explosions';
import { HIT_JET, HIT_MISSILE } from './laser';

interface Tracer { alive: boolean; p: Vector3; v: Vector3; life: number; onHero: boolean; }
interface Wreck { alive: boolean; p: Vector3; v: Vector3; q: Quaternion; }
export interface Combat extends System { fixed(dt: number): void; spawnWave(count: number, onHero: boolean): void; reset(): void; }
const M = (x: number, y: number, z: number, rx = 0, ry = 0, rz = 0): Matrix4 => new Matrix4().compose(new Vector3(x, y, z), quatFromYPR(new Quaternion(), ry, rx, rz), new Vector3(1, 1, 1));

/** Jet, missile, tracer and wreck simulation glue plus their instanced views. */
export function createCombat(ctx: Ctx, boom: Explosions): Combat {
  const jetGeo = mergeGeometries([
    part(new CapsuleGeometry(1, 13, 6, 10), 0x3a3d44, M(0, 0, 0, Math.PI / 2)), part(new BoxGeometry(11, 0.2, 6), 0x34373d, M(0, -0.1, 2.5)), part(new BoxGeometry(11, 0.22, 1), 0x9c1616, M(0, -0.1, 5)),
    part(new BoxGeometry(0.2, 3, 2.6), 0x34373d, M(-1.2, 1.5, 5.5, -0.3, 0, 0.35)), part(new BoxGeometry(0.2, 3, 2.6), 0x34373d, M(1.2, 1.5, 5.5, -0.3, 0, -0.35)), part(new SphereGeometry(0.8, 10, 8), 0x07090c, M(0, 0.7, -3.5)),
  ])!;
  const jetMesh = new InstancedMesh(jetGeo, new MeshStandardMaterial({ vertexColors: true, metalness: 0.8, roughness: 0.35 }), 12);
  const burnMat = new MeshBasicMaterial({ color: new Color(6, 2.2, 0.4) }), burn = new InstancedMesh(new ConeGeometry(0.8, 5, 8).applyMatrix4(M(0, 0, 9.5, -Math.PI / 2)), burnMat, 12);
  const misMesh = new InstancedMesh(mergeGeometries([new CylinderGeometry(0.2, 0.2, 3, 6).applyMatrix4(M(0, 0, 0, Math.PI / 2)), new BoxGeometry(1, 0.05, 0.5).applyMatrix4(M(0, 0, 1.3)), new BoxGeometry(0.05, 1, 0.5).applyMatrix4(M(0, 0, 1.3))])!, new MeshStandardMaterial({ color: 0xd8d8d8, metalness: 0.5, roughness: 0.4 }), 8);
  const wreckMesh = new InstancedMesh(jetGeo, new MeshStandardMaterial({ color: 0x111111, roughness: 1 }), 6);
  const meshes = [jetMesh, burn, misMesh, wreckMesh];
  for (const m of meshes) { m.frustumCulled = false; ctx.scene.add(m); } jetMesh.castShadow = true;
  const tracers = new Pool<Tracer>(96, () => ({ alive: false, p: new Vector3(), v: new Vector3(), life: 0, onHero: true }));
  const wrecks = new Pool<Wreck>(6, () => ({ alive: false, p: new Vector3(), v: new Vector3(), q: new Quaternion() }));
  const out: JetOut = { fire: false, missile: false }, o = new Object3D(), hide = new Matrix4().makeScale(0, 0, 0), look = new Vector3(), nose = new Vector3();
  let fxT = 0;
  function kill(j: JetState, i: number): void {
    j.alive = false; j.ai = 'dead'; boom.explode(j.position, 1);
    const w = wrecks.get(); if (w) { w.p.copy(j.position); w.v.copy(j.velocity).multiplyScalar(0.6); w.q.identity(); }
    ctx.stats.jets++; ctx.s.jetsLeft = ctx.jets.filter((x) => x.alive).length;
    ctx.bus.emit('jetKilled', { index: i, last: ctx.s.jetsLeft === 0 });
  }
  function hitHull(dmg: number): void { if (ctx.plane.landed && ctx.mission.touched) return; ctx.plane.hull = Math.max(0, ctx.plane.hull - dmg); ctx.bus.emit('hullHit', { damage: dmg }); }
  function hitHero(dmg: number, from: Vector3): void { damageHero(ctx.hero, dmg); ctx.bus.emit('heroHit', { damage: dmg, dx: from.x - ctx.hero.position.x, dz: from.z - ctx.hero.position.z }); }
  return {
    reset() { for (const j of ctx.jets) j.alive = false; for (const m of ctx.missiles) m.alive = false; tracers.killAll(); wrecks.killAll(); ctx.s.jetsLeft = 0; ctx.s.lock = -1; },
    spawnWave(count, onHero) {
      const tgt = onHero ? ctx.hero.position : ctx.plane.position; let n = 0;
      for (const j of ctx.jets) { if (j.alive || n >= count) continue; const a = n * 1.3 + ctx.s.wave; spawnJet(j, tgt.x + Math.cos(a) * 1700 - 300, Math.max(450, tgt.y + 150 + n * 60), tgt.z + Math.sin(a) * 1700, onHero); j.velocity.subVectors(tgt, j.position).setLength(CONFIG.jet.speed); n++; }
      ctx.s.wave++; ctx.s.jetsLeft = ctx.jets.filter((x) => x.alive).length;
    },
    fixed(dt) {
      const s = ctx.s, planeTarget = ctx.mission.phase !== 'INTERCEPT' && !ctx.mission.freeFly && !ctx.plane.dead;
      let near = 0;
      ctx.jets.forEach((j, i) => {
        if (!j.alive) return;
        const lasered = s.firing && s.hitKind === HIT_JET && s.hitJet === i;
        if (lasered) { j.hp -= CONFIG.laser.jetDps * dt; if (j.hp <= 0) { kill(j, i); return; } }
        stepJet(j, ctx.hero.position, ctx.plane.position, planeTarget, lasered, dt, out);
        if (j.position.y < surfaceY(ctx.grid, j.position.x, j.position.z) + 30) j.position.y += 60 * dt;
        const tgt = j.onHero ? ctx.hero.position : ctx.plane.position;
        if (out.fire) { const t = tracers.get(); if (t) { safeNorm(T0.subVectors(tgt, j.position)); T0.x += (Math.random() - 0.5) * 0.026; T0.y += (Math.random() - 0.5) * 0.026; T0.z += (Math.random() - 0.5) * 0.026; t.p.copy(j.position); t.v.copy(T0).setLength(CONFIG.jet.tracerSpeed); t.life = 2.5; t.onHero = j.onHero; ctx.audio.cannon(); ctx.particles.spawn(j.position, j.velocity.x, j.velocity.y, j.velocity.z, 0.05, 5, 8, 6, 2, 1, 0, 0); } }
        if (out.missile) { const m = ctx.missiles.find((x) => !x.alive); if (m) launchMissile(m, j.position, j.velocity, j.onHero); }
      });
      ctx.missiles.forEach((m, i) => {
        if (!m.alive) return;
        if (s.firing && s.hitKind === HIT_MISSILE && s.hitMissile === i) { m.hp -= CONFIG.laser.missileDps * dt; if (m.hp <= 0) { m.alive = false; boom.explode(m.position, 0.7); return; } }
        const tgt = m.onHero ? ctx.hero.position : ctx.plane.position, r = stepMissile(m, tgt, m.onHero ? 4 : 9, dt);
        if (m.onHero) near = Math.max(near, 1 - Math.min(1, m.position.distanceTo(tgt) / 1200));
        if (r === M_FLY) return;
        m.alive = false; boom.explode(m.position, r === M_HIT ? 0.8 : 0.4);
        if (r === M_HIT) { if (m.onHero) hitHero(CONFIG.missile.heroDamage, m.position); else hitHull(CONFIG.missile.hullDamage); }
      });
      s.missileNear = near;
      for (const t of tracers.items) {
        if (!t.alive) continue;
        t.p.addScaledVector(t.v, dt); t.life -= dt;
        if (t.life <= 0 || t.p.y < 0) { t.alive = false; continue; }
        if (t.onHero) { if (t.p.distanceToSquared(ctx.hero.position) < 4) { t.alive = false; hitHero(CONFIG.jet.tracerHero, t.p); } }
        else if (t.p.distanceToSquared(ctx.plane.position) < 900 && Math.abs(t.p.y - ctx.plane.position.y) < 5) { t.alive = false; hitHull(CONFIG.jet.tracerHull); ctx.particles.spawn(t.p, 0, 5, 0, 0.3, 2, 6, 3, 1, 1, 0, 0); }
      }
      for (const w of wrecks.items) {
        if (!w.alive) continue;
        w.v.y -= 9.8 * dt; w.p.addScaledVector(w.v, dt); w.q.multiply(T1 && quatFromYPR(new_q, 2 * dt, 3 * dt, 1.5 * dt));
        if (w.p.y < surfaceY(ctx.grid, w.p.x, w.p.z) + 2) { w.alive = false; w.p.y += 3; boom.explode(w.p, 1.2); for (let k = 0; k < 6; k++) ctx.particles.spawn(w.p, 0, 0.5, 0, 6, 10, 3, 0.9, 0.15, 1, 0, 0.05); }
      }
    },
    update(dt) {
      fxT += dt; const fx = fxT > 0.03; if (fx) fxT = 0;
      ctx.jets.forEach((j, i) => {
        if (!j.alive) { jetMesh.setMatrixAt(i, hide); burn.setMatrixAt(i, hide); return; }
        o.position.copy(j.position); o.up.set(0, 1, 0); o.lookAt(look.copy(j.position).sub(j.velocity)); o.rotateY(Math.PI); o.rotateZ(j.bank + j.roll); o.scale.setScalar(1); o.updateMatrix();
        jetMesh.setMatrixAt(i, o.matrix); burn.setMatrixAt(i, o.matrix);
        if (fx && Math.abs(j.turning) > 0.8) { nose.set(5.5, 0, 3).applyMatrix4(o.matrix); ctx.particles.spawn(nose, 0, 0, 0, 1.2, 1.2, 0.9, 0.9, 0.95, 0, 0, 0.6); nose.set(-5.5, 0, 3).applyMatrix4(o.matrix); ctx.particles.spawn(nose, 0, 0, 0, 1.2, 1.2, 0.9, 0.9, 0.95, 0, 0, 0.6); }
      });
      ctx.missiles.forEach((m, i) => {
        if (!m.alive) { misMesh.setMatrixAt(i, hide); return; }
        o.position.copy(m.position); o.up.set(0, 1, 0); o.lookAt(look.copy(m.position).sub(m.velocity)); o.rotateY(Math.PI); o.scale.setScalar(1); o.updateMatrix(); misMesh.setMatrixAt(i, o.matrix);
        if (fx) { ctx.particles.spawn(m.position, 0, 0, 0, 1.6, 2.2, 0.75, 0.72, 0.7, 0, -0.5, 0.8); ctx.particles.spawn(m.position, 0, 0, 0, 0.1, 2.5, 8, 4, 1, 1, 0, 0); }
      });
      for (const t of tracers.items) if (t.alive) for (let k = 0; k < 3; k++) ctx.particles.spawn(T2.copy(t.p).addScaledVector(t.v, -k * 0.006), 0, 0, 0, 0.03, 0.9, 8, 5, 1.2, 1, 0, 0);
      wrecks.items.forEach((w, i) => {
        if (!w.alive) { wreckMesh.setMatrixAt(i, hide); return; }
        o.position.copy(w.p); o.quaternion.copy(w.q); o.scale.setScalar(1); o.updateMatrix(); wreckMesh.setMatrixAt(i, o.matrix);
        if (fx) { ctx.particles.spawn(w.p, 0, 2, 0, 0.6, 5, 5, 1.8, 0.3, 1, 0, 0.5); ctx.particles.spawn(w.p, 0, 1, 0, 3.5, 5, 0.16, 0.15, 0.15, 0, -1, 0.5); }
      });
      burnMat.color.setRGB(5 + Math.random() * 2, 2.2, 0.4);
      for (const m of meshes) m.instanceMatrix.needsUpdate = true;
    },
    dispose() { for (const m of meshes) { ctx.scene.remove(m); m.dispose(); } jetGeo.dispose(); },
  };
}
const new_q = new Quaternion();
```

### src/game/camera.ts
```ts
import { MathUtils, Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { CONFIG } from '../config';
import { dirFromYP, lerp, smooth01 } from '../core/math';
import { surfaceY } from '../world/collision';

/** Aim-driven chase camera with a critically damped spring, FOV surge, shake, roll, building pull-in and cinematic modes. */
export function createCamera(ctx: Ctx): System {
  const C = CONFIG.camera, cam = ctx.camera, a = new Vector3(), right = new Vector3(), want = new Vector3(), vel = new Vector3(), look = new Vector3(), lookS = new Vector3(), tmp = new Vector3();
  let t = 0, init = false, wasBoost = false, kickF = 0, roll = 0;
  return {
    update(_dt, timeScale) {
      const dt = Math.min(0.05, _dt / Math.max(0.2, timeScale)), h = ctx.hero, s = ctx.s, sp = h.velocity.length(), k = smooth01(sp / CONFIG.flight.vBoost), ph = ctx.mission.phase;
      t += dt;
      dirFromYP(h.aimYaw, h.aimPitch, a); right.set(Math.cos(h.aimYaw), 0, -Math.sin(h.aimYaw));
      let lag = h.boosting ? C.lagBoost : C.lagCruise;
      if (ph === 'TITLE' || ph === 'CINEMATIC' || ph === 'RESULTS' || s.cine > 0) {
        const ang = t * (ph === 'TITLE' ? 0.05 : 0.35), focus = ph === 'RESULTS' || s.cine > 0 && h.mode === 'holding' ? ctx.plane.position : h.position, r = ph === 'TITLE' ? 60 : focus === h.position ? 9 : 85;
        want.set(focus.x + Math.cos(ang) * r, focus.y + r * 0.25 + 2, focus.z + Math.sin(ang) * r); look.copy(focus); lag = 0.5;
      } else if (h.mode === 'holding') {
        want.copy(h.position).addScaledVector(a, C.holdDist).addScaledVector(right, 10).setY(h.position.y - 4 + a.y * 8); look.copy(h.position).addScaledVector(a, -6).setY(h.position.y + 2); lag = 0.3;
      } else {
        want.copy(h.position).addScaledVector(a, -lerp(C.distHover, C.distFast, k)); want.y += lerp(2, 3.5, k);
        look.copy(h.position).addScaledVector(a, lerp(3, 25, k));
        if (s.lock >= 0 && ctx.jets[s.lock].alive) look.lerp(ctx.jets[s.lock].position, 0.2);
      }
      if (!init) { cam.position.copy(want); lookS.copy(look); init = true; }
      // critically damped spring
      const w = 2 / lag, e = Math.exp(-w * dt);
      tmp.subVectors(cam.position, want); const vx = (vel.x + w * tmp.x) * dt, vy = (vel.y + w * tmp.y) * dt, vz = (vel.z + w * tmp.z) * dt;
      vel.set((vel.x - w * vx) * e, (vel.y - w * vy) * e, (vel.z - w * vz) * e);
      cam.position.set(want.x + (tmp.x + vx) * e, want.y + (tmp.y + vy) * e, want.z + (tmp.z + vz) * e);
      lookS.lerp(look, Math.min(1, dt * 14));
      // pull in when a building blocks the view
      for (let i = 1; i <= 6; i++) { tmp.lerpVectors(lookS, cam.position, i / 6); if (surfaceY(ctx.grid, tmp.x, tmp.z) > tmp.y) { cam.position.lerpVectors(lookS, cam.position, Math.max(0.15, (i - 1) / 6)); vel.set(0, 0, 0); break; } }
      const floor = surfaceY(ctx.grid, cam.position.x, cam.position.z) + 1; if (cam.position.y < floor) cam.position.y = floor;
      // shake: sum of sines
      const sh = Math.max(0, (sp - 100) / 40) * C.shakeMax * (sp >= 140 ? 1 : 0.5) + s.shake;
      cam.position.x += (Math.sin(t * 47) + Math.sin(t * 83.1)) * sh * 0.5; cam.position.y += (Math.sin(t * 61.3) + Math.sin(t * 97.7)) * sh * 0.5;
      s.shake = Math.max(0, s.shake - dt * 2.5 * Math.max(0.3, s.shake));
      cam.up.set(0, 1, 0); cam.lookAt(lookS);
      roll += (-h.bank * C.rollShare - roll) * Math.min(1, dt * 6); cam.rotateZ(roll);
      if (h.boosting && !wasBoost) kickF = 4; wasBoost = h.boosting;
      const fov = C.fov + C.fovBoost * k + (kickF-- > 0 ? 6 : 0) + s.kick * 8; s.kick = Math.max(0, s.kick - dt * 3);
      cam.fov = MathUtils.lerp(cam.fov, fov, Math.min(1, 8 * dt)); cam.updateProjectionMatrix(); cam.updateMatrixWorld();
      s.cine = Math.max(0, s.cine - dt);
    },
    dispose() { /* nothing owned */ },
  };
}
```

### src/game/cinematics.ts
```ts
import type { Ctx, System } from '../context';

/** Radio lines typed during the cinematic and at phase changes, slow-motion beats and cinematic camera windows. */
export function createCinematics(ctx: Ctx): System {
  const s = ctx.s;
  const say = (line: string): void => { s.radio.push(line); if (s.radio.length > 4) s.radio.shift(); ctx.audio.beep(); };
  ctx.bus.on('phaseChanged', (e) => {
    if (e.phase === 'CINEMATIC') say("MAYDAY MAYDAY, Flight 227, engine fire, we're going down.");
    if (e.phase === 'INTERCEPT') { say('TOWER: Flight 227 is 9 km east. Bandits inbound on you.'); s.kick = 1; s.shake = 0.3; }
    if (e.phase === 'CATCH') say('227: Somebody is out there! Get under the nose!');
    if (e.phase === 'ARREST') say('TOWER: Metro Stadium is clear. Bring her west. Easy on that nose.');
    if (e.phase === 'SETDOWN') say('TOWER: You are over the field. Set her down gently.');
    if (e.phase === 'RESULTS') { say('227: All 218 souls accounted for. Thank you.'); ctx.loop.slow(0.3, 3); ctx.audio.chord(); }
  });
  ctx.bus.on('caught', () => { ctx.loop.slow(0.3, 1); s.cine = 1.4; ctx.audio.groan(); });
  ctx.bus.on('tailTorn', () => { ctx.loop.slow(0.3, 1.2); s.cine = 1.2; ctx.audio.scream(); say('227: We lost the tail! Catch the NOSE!'); });
  ctx.bus.on('jetKilled', (e) => { s.popup = e.last ? 'SPLASH — WAVE CLEAR' : 'SPLASH ONE'; s.popupT = 1.5; if (e.last) ctx.loop.slow(0.3, 0.5); });
  ctx.bus.on('touchdown', (e) => { ctx.loop.slow(0.3, 2); ctx.audio.thud(); s.popup = e.sink < 4 ? 'PERFECT TOUCHDOWN — PRESS E TO RELEASE' : 'HARD TOUCHDOWN — PRESS E TO RELEASE'; s.popupT = 5; });
  ctx.bus.on('boom', () => { s.popup = 'SUPERSONIC'; s.popupT = 1.2; ctx.audio.boom(); s.shake = Math.max(s.shake, 0.5); s.blur = 0.6; });
  ctx.bus.on('heroHit', (e) => { s.flash = 1; s.shake = Math.max(s.shake, e.damage / 50); });
  return { update() { /* event driven */ }, dispose() { /* bus cleared by main */ } };
}
```

### src/game/hud.ts
```ts
import { Vector3 } from 'three';
import type { Ctx, System } from '../context';
import { CONFIG } from '../config';
import { speedTier } from '../entities/flight';
import { isPlaying } from './mission';
import { surfaceY } from '../world/collision';

/** DOM HUD: thin cyan panels sized in vmin. */
export function createHud(ctx: Ctx): System {
  const root = document.getElementById('hud')!;
  root.innerHTML = `<div class="lb" id="lbt" style="top:0"></div><div class="lb" id="lbb" style="bottom:0"></div><div id="flash"></div>
  <div class="p" style="left:2vmin;top:2vmin"><div class="big" id="spd"></div><div id="tier"></div><div id="alt"></div>HP<div class="bar"><i id="hp"></i></div></div>
  <div class="p" style="left:50%;top:2vmin;transform:translateX(-50%);text-align:center"><div id="obj"></div><div id="imp"></div><div id="wave"></div></div>
  <div class="p" style="right:2vmin;top:2vmin;text-align:right"><div id="time"></div><div id="score"></div><div id="kills"></div></div>
  <div class="p" style="left:50%;bottom:2vmin;transform:translateX(-50%)">BOOST<div class="bar"><i id="boost"></i></div>HEAT<div class="bar"><i id="heat"></i></div></div>
  <div class="p" id="hold" style="right:2vmin;bottom:2vmin">HULL<div class="bar"><i id="hull"></i></div>STRESS <span id="buck" class="red"></span><div class="bar"><i id="stress"></i></div><div id="pspd"></div><div id="sink"></div></div>
  <div class="p" id="radio"></div><div id="cross"></div><div id="lock"></div><div id="arrow"></div><div id="popup"></div>
  <div id="title"><h1>LAST FLIGHT</h1><div>Flight 227 is going down over the city. 218 souls. Catch it.</div>
  <div>MOUSE aim · LMB laser · RMB lock · W thrust · S brake · SHIFT boost · SPACE up · CTRL down · A/D strafe · E grab/release · R retry · F free-fly</div><div class="big">CLICK TO FLY</div></div>`;
  const $ = (id: string): HTMLElement => document.getElementById(id)!;
  const el = { spd: $('spd'), tier: $('tier'), alt: $('alt'), hp: $('hp'), obj: $('obj'), imp: $('imp'), wave: $('wave'), time: $('time'), score: $('score'), kills: $('kills'), boost: $('boost'), heat: $('heat'), hold: $('hold'), hull: $('hull'), stress: $('stress'), buck: $('buck'), pspd: $('pspd'), sink: $('sink'), radio: $('radio'), cross: $('cross'), lock: $('lock'), arrow: $('arrow'), popup: $('popup'), title: $('title'), lbt: $('lbt'), lbb: $('lbb'), flash: $('flash') };
  const v = new Vector3(), fmt = (t: number): string => `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
  let acc = 0, typed = 0, lastRadio = '';
  function project(p: Vector3): boolean { v.copy(p).project(ctx.camera); return v.z < 1 && Math.abs(v.x) < 0.95 && Math.abs(v.y) < 0.95; }
  return {
    update(dt, timeScale) {
      const real = dt / Math.max(0.2, timeScale), h = ctx.hero, p = ctx.plane, m = ctx.mission, s = ctx.s, ph = m.phase, sp = h.mode === 'holding' ? p.velocity.length() : h.velocity.length();
      // per-frame elements
      const cs = 2.2 + Math.min(4, sp / 45); el.cross.style.width = el.cross.style.height = `${cs}vmin`; el.cross.style.borderColor = s.hitJet >= 0 ? '#f54' : '#dffc';
      el.flash.style.opacity = String(s.flash); s.flash = Math.max(0, s.flash - real * 2.5);
      const lockOn = s.lock >= 0 && ctx.jets[s.lock].alive && project(ctx.jets[s.lock].position);
      el.lock.style.display = lockOn ? 'block' : 'none';
      if (lockOn) { const j = ctx.jets[s.lock]; el.lock.style.left = `${(v.x * 0.5 + 0.5) * 100}%`; el.lock.style.top = `${(-v.y * 0.5 + 0.5) * 100}%`; el.lock.textContent = `BANDIT ${s.lock + 1} · ${Math.round(j.position.distanceTo(h.position))} M · HP ${Math.max(0, Math.round(j.hp))}`; }
      const showArrow = (ph === 'INTERCEPT' || ph === 'CATCH') && !p.held;
      el.arrow.style.display = showArrow ? 'block' : 'none';
      if (showArrow) { const on = project(p.position); let x = v.x, y = v.y; if (!on) { if (v.z > 1) { x = -x; y = -y; } const k = 0.85 / Math.max(Math.abs(x), Math.abs(y), 1e-3); x *= k; y *= k; } el.arrow.style.left = `${(x * 0.5 + 0.5) * 100}%`; el.arrow.style.top = `${(-y * 0.5 + 0.5) * 100}%`; el.arrow.textContent = `${on ? '◇' : '➤'} FLIGHT 227 ${(p.position.distanceTo(h.position) / 1000).toFixed(1)} KM`; }
      s.popupT -= real; el.popup.style.opacity = s.popupT > 0 ? '1' : '0'; if (s.popupT > 0) el.popup.textContent = s.popup;
      acc += real; if (acc < 0.08) return; acc = 0;
      // 12 Hz text
      const playing = isPlaying(ph) || m.freeFly, cine = ph === 'CINEMATIC' || s.cine > 0 || ph === 'RESULTS';
      el.title.style.display = ph === 'TITLE' && !m.freeFly ? 'flex' : 'none'; el.lbt.style.height = el.lbb.style.height = cine ? '11vh' : '0';
      el.spd.textContent = `${Math.round(sp * 3.6)} KM/H`; el.tier.textContent = h.mode === 'holding' ? 'HOLDING' : h.mode === 'landed' ? 'LANDED' : speedTier(sp);
      el.alt.textContent = `ALT ${Math.round(h.position.y)} M`; el.hp.style.width = `${h.hp}%`; el.hp.style.background = h.hp < 35 ? '#f54' : '#9ef';
      el.boost.style.width = `${h.boostCharge * 100}%`; el.heat.style.width = `${h.heat}%`; el.heat.style.background = h.heat > 75 || s.overheat > 0 ? '#f54' : '#9ef';
      const dStad = Math.hypot(p.position.x - CONFIG.stadium.x, p.position.z - CONFIG.stadium.z);
      let obj = '';
      if (m.freeFly) obj = 'FREE FLIGHT — F TO EXIT';
      else if (ph === 'INTERCEPT') obj = `INTERCEPT FLIGHT 227 — ${(p.position.distanceTo(h.position) / 1000).toFixed(1)} KM`;
      else if (ph === 'CATCH') obj = s.grab === 1 ? 'PRESS E — CATCH THE NOSE' : s.grab === 2 ? 'PRESS E — TAIL — UNSTABLE' : s.holdTail ? 'TAIL — UNSTABLE' : 'GET UNDER THE NOSE AND MATCH SPEED';
      else if (ph === 'ARREST') obj = `KILL ITS SPEED — ${Math.round(Math.hypot(p.velocity.x, p.velocity.z))} M/S — STADIUM ${(dStad / 1000).toFixed(1)} KM`;
      else if (ph === 'SETDOWN') obj = m.touched ? 'PRESS E TO RELEASE' : 'LOWER IT ONTO THE FIELD';
      else if (ph === 'RESULTS') obj = s.resultText;
      else if (ph === 'FAILED') obj = `MISSION FAILED — ${m.fail ?? ''} — R RETRY · SHIFT+R RESTART`;
      if (s.turnBack) obj = 'TURN BACK';
      if (!ctx.input.locked && playing) obj += ' · CLICK TO CAPTURE MOUSE';
      el.obj.textContent = obj; el.obj.className = ph === 'FAILED' || s.turnBack ? 'red' : '';
      const showImp = (ph === 'INTERCEPT' || ph === 'CATCH' || ph === 'ARREST') && !p.landed;
      if (showImp) { const altP = p.position.y - 4 - surfaceY(ctx.grid, p.position.x + p.velocity.x * 3, p.position.z + p.velocity.z * 3); if (p.velocity.y >= -0.5) { el.imp.textContent = 'PATH CLEAR'; el.imp.className = 'green'; } else { const tt = altP / -p.velocity.y; el.imp.textContent = `IMPACT IN ${fmt(Math.max(0, tt))}`; el.imp.className = tt < 30 ? 'red' : ''; } } else el.imp.textContent = '';
      el.wave.textContent = playing && s.wave > 0 ? `WAVE ${s.wave} · BANDITS ${s.jetsLeft}${s.missileNear > 0 ? ' · MISSILE' : ''}` : ''; el.wave.className = s.missileNear > 0 ? 'red' : '';
      el.time.textContent = fmt(m.time); el.score.textContent = `SCORE ${ctx.stats.jets * 500 + Math.round(ctx.stats.bonus)}`; el.kills.textContent = `JETS ${ctx.stats.jets} / 12`;
      const hold = p.held || ph === 'CATCH' || ph === 'ARREST' || ph === 'SETDOWN'; el.hold.style.display = hold ? 'block' : 'none';
      el.hull.style.width = `${p.hull}%`; el.hull.style.background = p.hull < 40 ? '#f54' : '#9ef'; el.stress.style.width = `${p.stress}%`; el.stress.style.background = p.stress > 70 ? '#f54' : '#9ef';
      el.buck.textContent = p.stress > 70 ? 'NOSE BUCKLING' : ''; el.pspd.textContent = `PLANE ${Math.round(Math.hypot(p.velocity.x, p.velocity.z))} M/S`;
      const sink = Math.max(0, -p.velocity.y); el.sink.textContent = dStad < 500 ? `SET-DOWN SINK ${sink.toFixed(1)} M/S${dStad < 60 ? ' · OVER ZONE' : ''}` : `SINK ${sink.toFixed(1)} M/S`; el.sink.className = sink < 4 ? 'green' : sink < 10 ? '' : 'red';
      const line = s.radio.length ? s.radio[s.radio.length - 1] : ''; if (line !== lastRadio) { lastRadio = line; typed = 0; }
      typed = Math.min(line.length, typed + 4); el.radio.textContent = (s.radio.length > 1 ? s.radio.slice(0, -1).join('\n') + '\n' : '') + line.slice(0, typed); el.radio.style.whiteSpace = 'pre-line';
    },
    dispose() { root.innerHTML = ''; },
  };
}
```

### src/game/debug.ts
```ts
import { GUI } from 'three/addons/libs/lil-gui.module.min.js';
import type { System } from '../context';
import { CONFIG } from '../config';

/** lil-gui bound to CONFIG; backquote toggles it. */
export function createDebug(): System {
  const gui = new GUI({ title: 'CONFIG' }); gui.hide(); let shown = false;
  for (const [name, group] of Object.entries(CONFIG)) {
    const f = gui.addFolder(name); f.close();
    for (const key of Object.keys(group)) { const rec = group as Record<string, number>; if (typeof rec[key] === 'number') f.add(rec, key); }
  }
  const onKey = (e: KeyboardEvent): void => { if (e.code === 'Backquote') { shown = !shown; if (shown) gui.show(); else gui.hide(); } };
  window.addEventListener('keydown', onKey);
  return { update() { /* gui is event driven */ }, dispose() { window.removeEventListener('keydown', onKey); gui.destroy(); } };
}
```

### src/main.ts
```ts
import { PerspectiveCamera, Scene, Vector3 } from 'three';
import { CONFIG } from './config';
import type { Ctx, Shared, System } from './context';
import { createBus } from './core/events';
import { createInput } from './core/input';
import { createAudio } from './core/audio';
import { createLoop } from './core/loop';
import { createGfx } from './core/renderer';
import { clamp, DEG, dirFromYP, quatFromYPR, T0 } from './core/math';
import { makeGrid, surfaceY } from './world/collision';
import { createSky } from './world/sky';
import { createGround } from './world/ground';
import { createCity } from './world/city';
import { createRiver } from './world/river';
import { createClouds } from './world/clouds';
import { createStadium } from './world/stadium';
import { createFlightState, damageHero, EV_BOOM, EV_HARD, EV_HIT, EV_TAKEOFF, FlightInput, FlightState, stepFlight } from './entities/flight';
import { copyPlane, createPlane, grabPoint, HoldInput, PlaneState, stepFreePlane, stepHolding, stepTailGrab } from './entities/holding';
import { createJet } from './entities/jet';
import { createMissile } from './entities/missile';
import { createHero } from './entities/hero';
import { createAirliner } from './entities/airliner';
import { createLaser } from './entities/laser';
import { createCombat } from './entities/wreck';
import { createParticles } from './vfx/particles';
import { createExplosions } from './vfx/explosions';
import { createSpeedFx } from './vfx/speedlines';
import { blankInput, createMission, isPlaying, restart, retry, saveCheckpoint, stepMission } from './game/mission';
import { computeScore, createStats, loadBest, saveBest, Stats } from './game/scoring';
import { createCamera } from './game/camera';
import { createHud } from './game/hud';
import { createCinematics } from './game/cinematics';
import { createDebug } from './game/debug';

interface Snap { hero: { p: Vector3; v: Vector3; yaw: number; pitch: number; mode: FlightState['mode'] }; plane: PlaneState; stats: Stats; time: number; wave: number; }

const scene = new Scene(), camera = new PerspectiveCamera(CONFIG.camera.fov, innerWidth / innerHeight, 0.3, 40000);
const sky = createSky(scene), gfx = createGfx(scene, camera, sky.sunMesh);
sky.bakeEnv(gfx.renderer);
const store = (() => { try { return window.localStorage; } catch { return null; } })();
const shared: Shared = { aimPoint: new Vector3(), firing: false, hitKind: 0, hitJet: -1, hitMissile: -1, lock: -1, shake: 0, blur: 0, flash: 0, fogWhite: 0, kick: 0, cine: 0, wave: 0, jetsLeft: 0, missileNear: 0, popup: '', popupT: 0, radio: [], overheat: 0, grab: 0, holdTail: false, catchT: 0, touchSink: -1, turnBack: false, best: loadBest(store), resultText: '' };
const bus = createBus(), input = createInput(gfx.renderer.domElement), audio = createAudio();
const grid = makeGrid(CONFIG.city.n, CONFIG.city.cell, CONFIG.city.street, CONFIG.city.seed, CONFIG.stadium.x, CONFIG.stadium.z);
const particles = createParticles(scene, sky.sun);
const fixedStep = (dt: number): void => simulate(dt);
const loop = createLoop(fixedStep, frame);
const ctx: Ctx = { scene, camera, bus, input, audio, loop, grid, sun: sky.sun, hero: createFlightState(), plane: createPlane(), jets: Array.from({ length: 12 }, (_, i) => createJet(i)), missiles: Array.from({ length: 8 }, createMissile), mission: createMission(), stats: createStats(), particles, s: shared };
const { hero, plane, mission, s } = ctx;
const ground = createGround(scene), explosions = createExplosions(ctx), heroView = createHero(ctx), combat = createCombat(ctx, explosions);
const systems: System[] = [createCity(scene, grid), createRiver(scene, sky.sun, sky.fogColor), createClouds(ctx, sky.fogColor), createStadium(ctx), heroView, createAirliner(ctx), createLaser(ctx, heroView.head), combat, explosions, createSpeedFx(ctx), particles, createCinematics(ctx), createDebug()];
const cameraSys = createCamera(ctx), hud = createHud(ctx);
const fin: FlightInput = { thrust: false, brake: false, boost: false, up: false, down: false, strafe: 0 };
const hin: HoldInput = { pushBack: 0, pushFwd: false, lift: false, down: false, aimYaw: 0, aimPitch: 0 };
const min = blankInput(), gp = new Vector3(), fwd = new Vector3();
let wave4 = false, arrestT = 0, nearCd = 0, crunchT = 0, failBoom = false, ePressed = false;

function resetWorld(): void {
  Object.assign(hero, createFlightState()); copyPlane(plane, createPlane()); Object.assign(ctx.stats, createStats());
  combat.reset(); particles.clear(); s.wave = 0; s.radio.length = 0; wave4 = false; arrestT = 0; failBoom = false; s.holdTail = false; s.touchSink = -1;
}
function snapshot(): Snap { const pl = createPlane(); copyPlane(pl, plane); return { hero: { p: hero.position.clone(), v: hero.velocity.clone(), yaw: hero.aimYaw, pitch: hero.aimPitch, mode: hero.mode }, plane: pl, stats: { ...ctx.stats }, time: mission.time, wave: s.wave }; }
function restore(sn: Snap): void {
  hero.position.copy(sn.hero.p); hero.velocity.copy(sn.hero.v); hero.aimYaw = sn.hero.yaw; hero.aimPitch = sn.hero.pitch; hero.mode = sn.hero.mode; hero.hp = 100; hero.heat = 0; hero.stun = 0; hero.boostCharge = 1;
  copyPlane(plane, sn.plane); Object.assign(ctx.stats, sn.stats); mission.time = sn.time; combat.reset(); s.wave = sn.wave; failBoom = false; s.touchSink = -1; s.holdTail = false; wave4 = false; arrestT = 0;
  onPhase(mission.phase, false);
}
function onPhase(ph: string, save: boolean): void {
  if (ph === 'INTERCEPT') { if (save) { resetWorld(); } combat.spawnWave(2, true); }
  if (ph === 'CATCH') combat.spawnWave(3, false);
  if (ph === 'ARREST') { combat.spawnWave(4, false); arrestT = 0; wave4 = false; }
  if (ph === 'RESULTS') { ctx.stats.time = mission.time; ctx.stats.hull = plane.hull; ctx.stats.heroHp = hero.hp; const r = computeScore(ctx.stats); s.best = saveBest(store, r.score); s.resultText = `218 SOULS SAVED — GRADE ${r.grade} — SCORE ${r.score} — BEST ${s.best} — TIME ${Math.round(mission.time)} S — JETS ${ctx.stats.jets} — HULL ${Math.round(plane.hull)} — HP ${Math.round(hero.hp)} — SINK ${ctx.stats.sink.toFixed(1)} M/S — ACC ${Math.round(r.accuracy * 100)}% — R TO PLAY AGAIN`; }
  if (save && isPlaying(mission.phase)) saveCheckpoint(mission, snapshot());
  bus.emit('phaseChanged', { phase: ph });
}

function simulate(dt: number): void {
  const ph = mission.phase, active = isPlaying(ph) || mission.freeFly;
  fin.thrust = active && input.down('KeyW'); fin.brake = active && input.down('KeyS'); fin.boost = active && (input.down('ShiftLeft') || input.down('ShiftRight'));
  fin.up = active && input.down('Space'); fin.down = active && (input.down('ControlLeft') || input.down('ControlRight')); fin.strafe = active ? (input.down('KeyD') ? 1 : 0) - (input.down('KeyA') ? 1 : 0) : 0;
  min.touchdownSink = null; min.planeImpact = false; min.released = false;
  // airliner
  if (!mission.freeFly && ph !== 'TITLE' && ph !== 'CINEMATIC' && !(ph === 'FAILED' && failBoom)) {
    if (plane.held && hero.mode === 'holding') {
      hin.pushBack = fin.brake ? 1 : 0; hin.pushFwd = fin.thrust; hin.lift = fin.up; hin.down = fin.down; hin.aimYaw = hero.aimYaw; hin.aimPitch = hero.aimPitch;
      stepHolding(plane, hin, dt);
      grabPoint(plane, false, gp); hero.position.copy(gp).setY(gp.y - 1.6); hero.velocity.copy(plane.velocity); quatFromYPR(hero.bodyQuat, plane.yaw + Math.PI, 0, 0);
    } else {
      stepFreePlane(plane, dt);
      if (s.holdTail) { grabPoint(plane, true, gp); hero.position.copy(gp).setY(gp.y - 1.6); hero.velocity.copy(plane.velocity); if (stepTailGrab(plane, dt)) { s.holdTail = false; hero.mode = 'stunned'; hero.stun = 0.5; hero.velocity.y -= 20; bus.emit('tailTorn', undefined); explosions.explode(gp, 0.5); } }
    }
    // touchdown / impact
    const S = CONFIG.stadium, overZone = Math.abs(plane.position.x - S.x) < S.zoneX / 2 && Math.abs(plane.position.z - S.z) < S.zoneZ / 2, floor = surfaceY(grid, plane.position.x, plane.position.z);
    min.overZone = overZone;
    if (!plane.landed && plane.position.y - 6.5 <= floor) {
      const sink = Math.max(0, -plane.velocity.y);
      if (plane.held && overZone && floor === 0 && sink <= CONFIG.hold.hardSink && Math.hypot(plane.velocity.x, plane.velocity.z) < 15) {
        plane.landed = true; plane.position.y = 6.5; plane.velocity.set(0, 0, 0); s.touchSink = sink; ctx.stats.sink = sink; min.touchdownSink = sink;
        if (sink > CONFIG.hold.perfectSink) { plane.hull = Math.max(1, plane.hull - 20); s.shake = 0.8; }
        for (let i = 0; i < 60; i++) particles.spawn(T0.set(plane.position.x + (Math.random() - 0.5) * 50, 1, plane.position.z + (Math.random() - 0.5) * 12), (Math.random() - 0.5) * 8, 2, (Math.random() - 0.5) * 8, 3, 6, 0.5, 0.45, 0.35, 0, -0.3, 0.5);
        bus.emit('touchdown', { sink });
      } else if (plane.held) { min.touchdownSink = 99; boomPlane(); } else { min.planeImpact = true; boomPlane(); }
    }
    if (plane.hull <= 0 && !plane.dead) { plane.dead = true; if (plane.held) release(true); explosions.explode(plane.position, 1.5); }
  }
  // hero
  const ev = stepFlight(hero, fin, dt, grid);
  if (ev & EV_BOOM) bus.emit('boom', undefined);
  if (ev & (EV_HIT | EV_HARD)) { s.flash = 0.8; s.shake = Math.max(s.shake, Math.min(1.5, hero.impact / 60)); audio.thud(); damageHero(hero, Math.min(30, hero.impact * 0.15)); }
  if (ev & EV_TAKEOFF) { s.kick = 1; audio.whoosh(); for (let i = 0; i < 40; i++) { const a = (i / 40) * Math.PI * 2; particles.spawn(hero.position, Math.cos(a) * 14, 0.5, Math.sin(a) * 14, 1.2, 2.5, 0.55, 0.5, 0.42, 0, 0, 0.8); } }
  s.turnBack = Math.hypot(hero.position.x, hero.position.z) > CONFIG.flight.bounds && !plane.held && hero.position.x < 4000;
  // grab logic
  s.grab = 0;
  if (ph === 'CATCH' && !plane.held && !s.holdTail && hero.mode !== 'stunned' && !plane.dead) {
    const rel = T0.subVectors(hero.velocity, plane.velocity).length();
    if (rel < CONFIG.plane.grabSpeed + 10) { if (grabPoint(plane, false, gp).distanceTo(hero.position) < CONFIG.plane.grabRange + 4) s.grab = 1; else if (!plane.tailTorn && grabPoint(plane, true, gp).distanceTo(hero.position) < CONFIG.plane.grabRange + 4) s.grab = 2; }
    if (ePressed && s.grab === 1) { plane.held = true; hero.mode = 'holding'; hero.aimYaw = plane.yaw; hero.aimPitch = plane.pitch; plane.brake = 0; s.lock = -1; bus.emit('caught', { tail: false }); }
    else if (ePressed && s.grab === 2) { s.holdTail = true; plane.tailT = 0; bus.emit('caught', { tail: true }); }
  } else if (ePressed && plane.held && plane.landed) { release(false); min.released = true; }
  ePressed = false;
  combat.fixed(dt);
  // mission
  min.distToPlane = hero.position.distanceTo(plane.position); min.holding = plane.held; min.planeSpeed = Math.hypot(plane.velocity.x, plane.velocity.z); min.hull = plane.hull; min.heroDead = hero.hp <= 0;
  const changed = stepMission(mission, min, dt);
  if (changed) { if (changed === 'FAILED') { loop.slow(0.3, 2); if (plane.held) release(true); if (hero.hp <= 0) { hero.mode = 'stunned'; hero.stun = 99; s.popup = 'YOU FELL'; s.popupT = 3; } } onPhase(changed, true); }
  if (mission.phase === 'ARREST') { arrestT += dt; if (!wave4 && (arrestT > 40 || plane.hull < 50)) { wave4 = true; combat.spawnWave(3, false); } }
  // near miss
  nearCd -= dt;
  if (nearCd <= 0 && active && hero.mode === 'flight' && hero.velocity.length() > 50) {
    fwd.set(-hero.velocity.z, 0, hero.velocity.x).setLength(9);
    if (surfaceY(grid, hero.position.x + fwd.x, hero.position.z + fwd.z) > hero.position.y || surfaceY(grid, hero.position.x - fwd.x, hero.position.z - fwd.z) > hero.position.y) { nearCd = 0.6; ctx.stats.bonus += 150; s.popup = 'NEAR MISS +150'; s.popupT = 0.9; hero.velocity.multiplyScalar(1 + 4 / hero.velocity.length()); audio.whoosh(); }
  }
  if (plane.stress > 70) { crunchT -= dt; if (crunchT <= 0) { crunchT = 0.5; audio.crunch(); s.shake = Math.max(s.shake, 0.15); } }
}
function release(thrown: boolean): void { plane.held = false; plane.released = !thrown; hero.mode = thrown ? 'stunned' : 'landed'; hero.stun = 0.5; if (!thrown) { dirFromYP(plane.yaw, 0, fwd); hero.position.addScaledVector(fwd, 6).setY(CONFIG.flight.standH); hero.velocity.set(0, 0, 0); } }
function boomPlane(): void { if (failBoom) return; failBoom = true; explosions.explode(plane.position, 3); dirFromYP(plane.yaw, 0, fwd); explosions.explode(T0.copy(plane.position).addScaledVector(fwd, 20), 2); explosions.explode(T0.copy(plane.position).addScaledVector(fwd, -20), 2); plane.position.y = -500; plane.velocity.set(0, 0, 0); plane.landed = true; }

function frame(dt: number, timeScale: number, real: number): void {
  input.update(real);
  const ph = mission.phase;
  if (ph !== 'TITLE' && hero.hp > 0) { hero.aimYaw -= input.dx * CONFIG.input.sensitivity; hero.aimPitch = clamp(hero.aimPitch - input.dy * CONFIG.input.sensitivity, -85 * DEG, 85 * DEG); }
  if (input.pressed('KeyE')) ePressed = true;
  if (ph === 'TITLE' && input.pressed('Mouse0')) { audio.init(); min.start = true; } else min.start = false;
  min.skip = ph === 'CINEMATIC' && mission.phaseTime > 0.3 && input.anyPressed;
  if (input.pressed('KeyF') && (ph === 'TITLE' || mission.freeFly)) { audio.init(); mission.freeFly = !mission.freeFly; resetWorld(); plane.position.set(0, -500, 9000); }
  if (input.pressed('KeyR') && !mission.freeFly) {
    if (input.down('ShiftLeft') || input.down('ShiftRight') || ph === 'RESULTS') { restart(mission); resetWorld(); mission.phase = 'INTERCEPT'; onPhase('INTERCEPT', true); }
    else if (ph === 'FAILED') { const sn = retry(mission) as Snap | null; if (sn) restore(sn); else { restart(mission); resetWorld(); } }
  }
  for (const sys of systems) sys.update(dt, timeScale);
  sky.follow(hero.position);
  cameraSys.update(dt, timeScale);
  hud.update(dt, timeScale);
  const sp = hero.velocity.length(), k = Math.max(0, (sp - 65) / 125);
  s.blur = Math.max(0, s.blur - real * 1.2);
  gfx.setFx(Math.min(0.8, k * k * CONFIG.post.blurMax + s.blur), k * 0.0035);
  sky.fog.color.copy(sky.fogColor).lerp(T_WHITE, s.fogWhite * 0.6); sky.fog.near = 300 - 250 * s.fogWhite; sky.fog.far = 9000 - 8200 * s.fogWhite;
  const dStad = Math.hypot(plane.position.x - CONFIG.stadium.x, plane.position.z - CONFIG.stadium.z);
  audio.update(real, { speed: sp, boost: hero.boosting, firing: s.firing, heat: hero.heat, crowd: ph === 'RESULTS' || mission.touched ? 1 : plane.held ? clamp(1 - dStad / 2500, 0, 0.6) : 0, combat: s.jetsLeft > 0 && isPlaying(ph), fire: clamp(1 - hero.position.distanceTo(plane.position) / 600, 0, 1), missile: s.missileNear, timeScale });
  gfx.render(real);
  input.endFrame();
}
const T_WHITE = new (sky.fogColor.constructor as new (r: number, g: number, b: number) => typeof sky.fogColor)(1, 0.92, 0.85);
window.addEventListener('resize', () => gfx.resize());
window.addEventListener('beforeunload', () => { loop.stop(); for (const sys of systems) sys.dispose(); ground.dispose(); cameraSys.dispose(); hud.dispose(); sky.dispose(); input.dispose(); audio.dispose(); gfx.dispose(); bus.clear(); });
loop.start();
```

### tests/flight.test.ts
```ts
import { describe, expect, it } from 'vitest';
import { CONFIG } from '../src/config';
import { createFlightState, FlightInput, stepFlight, turnRate } from '../src/entities/flight';

const DT = 1 / 120;
const input = (o: Partial<FlightInput> = {}): FlightInput => ({ thrust: false, brake: false, boost: false, up: false, down: false, strafe: 0, ...o });

describe('flight model', () => {
  it('turns slower at speed', () => { expect(turnRate(190)).toBeLessThan(turnRate(0)); });
  it('reaches cruise terminal speed within 5%', () => {
    const s = createFlightState(); s.position.set(0, 3000, 0); const i = input({ thrust: true });
    for (let n = 0; n < 120 * 12; n++) { s.position.set(0, 3000, 0); stepFlight(s, i, DT, null); }
    expect(Math.abs(s.velocity.length() - CONFIG.flight.vCruise) / CONFIG.flight.vCruise).toBeLessThan(0.05);
  });
  it('reaches boost terminal speed within 5%', () => {
    const s = createFlightState(); const i = input({ thrust: true, boost: true }); let max = 0;
    for (let n = 0; n < 120 * 4; n++) { s.position.set(0, 3000, 0); stepFlight(s, i, DT, null); max = Math.max(max, s.velocity.length()); }
    expect(Math.abs(max - CONFIG.flight.vBoost) / CONFIG.flight.vBoost).toBeLessThan(0.05);
  });
  it('never produces NaN under random input', () => {
    const s = createFlightState(); let seed = 1; const r = (): number => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (let n = 0; n < 10000; n++) {
      s.aimYaw += (r() - 0.5) * 0.5; s.aimPitch += (r() - 0.5) * 0.5;
      stepFlight(s, input({ thrust: r() > 0.4, brake: r() > 0.8, boost: r() > 0.5, up: r() > 0.7, down: r() > 0.7, strafe: Math.round(r() * 2 - 1) }), DT, null);
      expect(Number.isFinite(s.position.x + s.position.y + s.position.z + s.velocity.length())).toBe(true);
    }
  });
});
```

### tests/collision.test.ts
```ts
import { describe, expect, it } from 'vitest';
import { Vector3 } from 'three';
import { Box, cellBox, makeGrid, pushOutBox, resolveSphere, resolveSphereBrute } from '../src/world/collision';

const grid = makeGrid(64, 48, 14, 227, -1392, 0);
let seed = 7; const r = (): number => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };

describe('collision', () => {
  it('pushes an overlapping sphere fully outside the box', () => {
    const b: Box = { minX: -10, maxX: 10, minZ: -10, maxZ: 10, maxY: 50 }, n = new Vector3();
    for (let k = 0; k < 500; k++) {
      const p = new Vector3((r() - 0.5) * 24, r() * 54, (r() - 0.5) * 24);
      if (!pushOutBox(p, 0.9, b, n)) continue;
      const cx = Math.max(b.minX, Math.min(b.maxX, p.x)), cy = Math.min(b.maxY, p.y), cz = Math.max(b.minZ, Math.min(b.maxZ, p.z));
      expect(Math.hypot(p.x - cx, p.y - cy, p.z - cz)).toBeGreaterThanOrEqual(0.9);
    }
  });
  it('grid lookup agrees with brute force on 1,000 random points', () => {
    const n = new Vector3(), box: Box = { minX: 0, maxX: 0, minZ: 0, maxZ: 0, maxY: 0 };
    expect(cellBox(grid, -1, 0, box)).toBe(false);
    for (let k = 0; k < 1000; k++) {
      const a = new Vector3((r() - 0.5) * 3000, r() * 120, (r() - 0.5) * 3000), b = a.clone();
      const h1 = resolveSphere(grid, a, 0.9, n), h2 = resolveSphereBrute(grid, b, 0.9, n);
      expect(h1).toBe(h2);
      expect(a.distanceTo(b)).toBeLessThan(1e-6);
    }
  });
});
```

### tests/holding.test.ts
```ts
import { describe, expect, it } from 'vitest';
import { CONFIG } from '../src/config';
import { createPlane, HoldInput, stepHolding, stepTailGrab } from '../src/entities/holding';

const DT = 1 / 120;
const hold = (pushBack: number): HoldInput => ({ pushBack, pushFwd: false, lift: true, down: false, aimYaw: Math.PI / 2, aimPitch: 0 });

describe('holding physics', () => {
  it('8 m/s^2 of brake from 110 m/s reaches under 30 m/s within 12 s', () => {
    const p = createPlane(); p.velocity.set(-110, 0, 0); p.held = true;
    for (let n = 0; n < 120 * 12; n++) stepHolding(p, hold(8 / CONFIG.hold.brakeMax), DT);
    expect(Math.hypot(p.velocity.x, p.velocity.z)).toBeLessThan(30);
  });
  it('10 m/s^2 sustained crosses stress 70', () => {
    const p = createPlane(); p.velocity.set(-110, 0, 0); let max = 0;
    for (let n = 0; n < 120 * 6; n++) { stepHolding(p, hold(10 / CONFIG.hold.brakeMax), DT); max = Math.max(max, p.stress); }
    expect(max).toBeGreaterThan(70);
  });
  it('a tail grab tears at 1.5 s and drops hull by 30', () => {
    const p = createPlane(); p.tailT = 0; let t = 0, tornAt = -1;
    for (let n = 0; n < 120 * 3; n++) { t += DT; if (stepTailGrab(p, DT) && tornAt < 0) tornAt = t; }
    expect(tornAt).toBeGreaterThan(1.45); expect(tornAt).toBeLessThan(1.55);
    expect(p.hull).toBe(70); expect(p.tailTorn).toBe(true);
  });
});
```

### tests/mission.test.ts
```ts
import { describe, expect, it } from 'vitest';
import { blankInput, createMission, FailReason, MissionInput, retry, saveCheckpoint, stepMission } from '../src/game/mission';

const DT = 1 / 120;
function toArrest(): ReturnType<typeof createMission> {
  const m = createMission();
  stepMission(m, { ...blankInput(), start: true }, DT); stepMission(m, { ...blankInput(), skip: true }, DT);
  stepMission(m, { ...blankInput(), distToPlane: 1000 }, DT); stepMission(m, { ...blankInput(), distToPlane: 5, holding: true }, DT);
  return m;
}
describe('mission', () => {
  it('walks every phase in order', () => {
    const m = createMission(), i = blankInput();
    expect(m.phase).toBe('TITLE');
    expect(stepMission(m, { ...i, start: true }, DT)).toBe('CINEMATIC');
    let p = null; for (let n = 0; n < 120 * 5 && !p; n++) p = stepMission(m, i, DT);
    expect(p).toBe('INTERCEPT');
    expect(stepMission(m, { ...i, distToPlane: 1400 }, DT)).toBe('CATCH');
    expect(stepMission(m, { ...i, distToPlane: 5, holding: true }, DT)).toBe('ARREST');
    expect(stepMission(m, { ...i, holding: true, overZone: true, planeSpeed: 5 }, DT)).toBe('SETDOWN');
    expect(stepMission(m, { ...i, holding: true, touchdownSink: 3 }, DT)).toBe(null);
    expect(stepMission(m, { ...i, released: true }, DT)).toBe('RESULTS');
  });
  it('produces a reason for every fail state', () => {
    const cases: Array<[Partial<MissionInput>, FailReason]> = [[{ planeImpact: true }, 'AIRLINER IMPACT'], [{ hull: 0 }, 'HULL DESTROYED'], [{ heroDead: true }, 'YOU FELL'], [{ touchdownSink: 14 }, 'CRASH LANDING']];
    for (const [inp, reason] of cases) {
      const m = toArrest();
      expect(stepMission(m, { ...blankInput(), holding: true, ...inp }, DT)).toBe('FAILED');
      expect(m.fail).toBe(reason);
    }
  });
  it('retry restores the phase checkpoint', () => {
    const m = toArrest(); saveCheckpoint(m, { tag: 42 });
    stepMission(m, { ...blankInput(), holding: true, hull: 0 }, DT);
    expect(m.phase).toBe('FAILED');
    expect(retry(m)).toEqual({ tag: 42 });
    expect(m.phase).toBe('ARREST'); expect(m.fail).toBe(null);
  });
});
```

## File tree (approximate line counts; long lines, compact style)

```
last-flight/
  package.json 22   vite.config.ts 6   tsconfig.json 15   index.html 33   README.md 12
  src/
    main.ts 150   config.ts 100   context.ts 28
    core/      renderer.ts 55  loop.ts 30  input.ts 45  audio.ts 85  pool.ts 12  math.ts 45  events.ts 25
    world/     sky.ts 55  city.ts 60  river.ts 18  clouds.ts 40  stadium.ts 65  ground.ts 12  collision.ts 70
    entities/  hero.ts 65  flight.ts 105  laser.ts 70  airliner.ts 70  holding.ts 80  jet.ts 60  missile.ts 30  wreck.ts 110
    vfx/       particles.ts 55  explosions.ts 60  trails.ts 35  speedlines.ts 35
    vfx/shaders/  radialBlur.ts 17  grade.ts 14  fire.ts 18  water.ts 16  windows.ts 30  cloud.ts 28
    game/      mission.ts 45  camera.ts 50  hud.ts 75  cinematics.ts 25  scoring.ts 20  debug.ts 17
  tests/   flight.test.ts 32  collision.test.ts 30  holding.test.ts 27  mission.test.ts 40
```

## Run

```
npm install
npm run dev
npm run build
```

## Tuning tips

1. `CONFIG.flight.turnFast` and `CONFIG.flight.turnSlow` set how much momentum matters: lower `turnFast` for wider boost turns.
2. `CONFIG.camera.lagBoost` and `CONFIG.camera.fovBoost` set how violent the boost surge reads on screen.
3. `CONFIG.hold.stressFree` and `CONFIG.hold.brakeMax` set how hard you can push back on the airliner before the nose buckles.
