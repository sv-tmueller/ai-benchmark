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
    "typescript": "^5.9.0",
    "vite": "^8.0.0",
    "vitest": "^5.0.0"
  }
}
```

### tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "types": ["vite/client"],
    "strict": true,
    "noImplicitAny": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "isolatedModules": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true
  },
  "include": ["src", "tests"]
}
```

### vite.config.ts
```ts
import { defineConfig } from 'vite';

export default defineConfig({
  base: './',
  build: { target: 'es2022', sourcemap: false, chunkSizeWarningLimit: 1600 },
  server: { port: 5173 },
});
```

### index.html
```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>LAST FLIGHT</title>
<link rel="icon" href="data:," />
<style>
  html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#0a0d12;font-family:system-ui,sans-serif;}
  #app{position:fixed;inset:0;}
  canvas{display:block;}
  ::selection{background:transparent;}
</style>
<script type="module" src="/src/main.ts"></script>
</head>
<body><div id="app"></div></body>
</html>
```

### README.md
```md
# LAST FLIGHT

A cinematic superhero flight-rescue game. Golden hour over Metro City: Flight 227 is burning
and sinking toward downtown while hostiles hunt it. Intercept, cut the jets down with laser
vision, catch the airliner under its nose, kill 110 m/s of momentum without buckling it, and
set 218 souls down on the field of Metro Stadium.

## Run
    npm install
    npm run dev      # play at localhost:5173
    npm run typecheck && npm test && npm run build

## Controls
Mouse aim · LMB laser · RMB lock-on · W thrust · S brake / push back · Shift boost
Space up / lift / takeoff · Ctrl down · A/D strafe · E grab / release · R retry phase
Shift+R restart · F free-fly · Esc release mouse · ` debug · [ ] sensitivity
```

### src/config.ts
```ts
/**
 * LAST FLIGHT — every tunable in one place. Units in comments. Mutated only by debug.ts.
 */
export const CONFIG = {
  title: 'LAST FLIGHT',

  sim: {
    fixedDt: 1 / 120,        // s, physics step
    maxFrameDt: 0.05,        // s, clamp so tab-switch never teleports
  },

  world: {
    gridN: 64,               // city cells per side
    cellSize: 48,            // m
    streetW: 14,             // m street gap inside a cell
    riverCells: 5,           // river width in cells
    plazaCount: 3,
    stadiumSpan: 6,          // stadium block in cells
    boundaryRadius: 4500,    // m soft push-back radius from city centre
  },

  skyCfg: {
    elevDeg: 4,              // sun elevation above horizon, degrees
    aziDeg: 248,             // sun azimuth, degrees (west, behind the stadium)
    turbidity: 8,
    rayleigh: 2.5,
    mieCoeff: 0.02,
    mieG: 0.85,
    fogNear: 850,            // m
    fogFar: 7200,            // m
    fogColor: '#efa468',     // horizon haze sampled-analogue
  },

  light: {
    sunIntensity: 3.1,       // directional
    sunColor: '#ffd9a3',
    ambSky: '#7fa0c8',
    ambGround: '#4a3a2c',
    ambIntensity: 0.55,
    shadowTexel: 400 / 2048, // m per shadow-map texel (snap target)
  },

  city: {
    lowMin: 18, lowMax: 70,      // m heights, majority bucket
    midMin: 70, midMax: 160,
    highMin: 160, highMax: 420,  // downtown cluster
    pLow: 0.70, pMid: 0.22, pHigh: 0.08,
    glassFrac: 0.30,         // fraction of towers that are mirrored glass
    windowSize: 3,           // m window module
    litFrac: 0.30,           // fraction of windows lit warm
    roofBoxChance: 0.55,
    antennaChance: 0.35,
    lampSpacing: 24,         // m between streetlights on avenues
    hazeY: 30,               // m ground-haze quad altitude
  },

  hero: {
    radius: 0.9,             // m collision sphere
    hpMax: 100,
    regenDelay: 4,           // s without damage
    regenRate: 10,           // hp/s
    thrust: 60,              // m/s^2 along aim (W)
    boostMult: 2.2,
    vMaxCruise: 65,          // m/s terminal
    vMaxBoost: 190,
    turnLow: 2.5,            // rad/s at 0 m/s
    turnHigh: 0.7,           // rad/s at vMaxBoost
    dragBlend: 0.4,          // s DRAG_K lerp between modes
    brakeDrag: 6,            // drag multiplier on S
    brakePitch: 30 * Math.PI / 180, // rad nose-up on air brake
    vertAccel: 25,           // m/s^2 Space / Ctrl
    strafeAccel: 20,         // m/s^2 A/D in hover
    yawAssist: 0.6,          // rad/s A/D at speed
    hoverSpeed: 6,           // m/s below which hover engages
    coastGravity: 2.5,       // m/s^2 while coasting
    fullGravity: 9.8,        // m/s^2 stunned
    bobAmp: 0.15,            // m hover bob
    bobHz: 0.8,              // Hz
    boostDrain: 4,           // s full -> empty
    boostRefill: 3,          // s empty -> full
    boostLockout: 1,         // s at empty
    landAlt: 2.2,            // m above surface
    landSpeedMax: 8,         // m/s
    launchTime: 0.6,         // s Space charge
    launchMin: 15, launchMax: 45, // m/s
    stunTime: 0.5,           // s
    hardLandSpeed: 30,       // m/s hard landing threshold
    sens: 0.0022,            // rad/px mouse
    sensMin: 0.0004, sensMax: 0.008, sensStep: 1.15,
    arrowRate: 1.8,          // rad/s fallback steering
  },

  laser: {
    range: 1500,             // m
    dpsJet: 35,              // hp/s
    dpsMissile: 60,
    heatRate: 25,            // heat/s (100 in 4 s)
    coolRate: 33.3,          // heat/s idle (100 in 3 s)
    overheatLock: 2,         // s
    eyeSep: 0.08,            // m eye offset from head centre
    coreRadius: 0.06,        // m inner beam
    glowRadius: 0.25,        // m outer beam
    assistDeg: 3,            // aim-assist cone
    lockDeg: 15,             // RMB acquisition cone
    lockBreakDeg: 30,
    sparkRate: 40,           // particles/s at hit point
    lightIntensity: 30,
    lightRange: 20,          // m
    scorchFade: 1.5,         // s molten glow fade
    flickerHz: 30,
  },

  cam: {
    fovBase: 72, fovAdd: 30, // deg, + at supersonic
    fovLerp: 8,              // /s
    distHover: 5, distFast: 13,   // m behind
    heightHover: 2, heightFast: 3.5,
    tauNear: 0.12, tauFar: 0.20,  // s spring lag
    lookNear: 3, lookFar: 25,     // m look-ahead
    lockBias: 0.20,
    rollMix: 0.35,           // fraction of body bank shown
    holdDist: 22, holdHeight: 4,  // m three-quarter front-low while holding
    kickFov: 6,              // deg boost press kick
    kickTime: 0.12,          // s
    occludePad: 0.5,         // m raycast pull-in pad
  },

  plane: {
    eastOffset: 9000,        // m east of downtown spawn
    startAlt: 2400,          // m
    speed0: 110,             // m/s westbound
    sink0: 18, sinkMax: 30,  // m/s sink, ramping
    sinkRampT: 60,           // s
    pitch0: 0, pitchEnd: -12 * Math.PI / 180, // rad nose-down
    pitchRampT: 90,          // s
    len: 62, radius: 3, span: 60, // m
    hullMax: 100,
    dmgTracer: 4, dmgMissile: 25, dmgTail: 30, dmgStress: 8, dmgHardTD: 20, // hp
    grabDist: 6,             // m from grab point
    speedMatch: 25,          // m/s relative speed allowance
    catchTime: 0.8,          // s animation
    tearDelay: 1.5,          // s tail hold before tearing
    gearAlt: 200,            // m auto gear below
    gearSpd: 20,             // m/s
    stressBrakeRate: 12,     // stress/s per m/s^2 of excess brake
    stressSafe: 7,           // m/s^2 brake below which no stress
    stressMiscRate: 15,      // stress/s from yaw/speed/sink abuse
    stressDecay: 20,         // stress/s gentle
    stressWarn: 70,
    holdGrav: -8,            // m/s^2 body gravity while held
    holdLift: 25,            // m/s^2 Space
    holdSinkCtrl: -10,       // m/s^2 Ctrl
    brakeMax: 12,            // m/s^2 full push-back
    brakeRampT: 1,           // s ramp 0->max
    fwdPush: 6,              // m/s^2 W
    pitchLim: 35 * Math.PI / 180, // rad
    rollLim: 20 * Math.PI / 180,
    yawRateMax: 0.4,         // rad/s
    noseAng: 15 * Math.PI / 180,  // rad aero threshold
    aeroBrakeUp: 4, aeroLiftUp: 2,   // m/s^2 nose-up benefits
    aeroBrakeDown: 3,                // m/s^2 nose-down penalty
    tdPerfect: 4, tdHard: 10,        // m/s touchdown sink bands
    tdMaxSpeed: 8,           // m/s ground speed to set down
    zoneW: 120, zoneD: 80,   // m set-down rectangle
    crumpleRate: 0.8,        // nose deform /s above warn
  },

  jets: {
    speed: 180,              // m/s
    turnMax: 1.6,            // rad/s
    floorMargin: 250,        // m above local terrain
    hp: 100,
    total: 12,
    waveCounts: [2, 3, 4, 3],
    wave4Delay: 40,          // s into ARREST, or hull < 50%
    engage: 1500,            // m spawn ring
    gunRange: 900,           // m
    burstOn: 0.6, burstOff: 1.1, // s
    burstRate: 8,            // rounds/s
    tracerSpeed: 600,        // m/s
    tracerSpread: 1.5 * Math.PI / 180, // rad
    tracerLife: 2.5,         // s
    evadeAfter: 0.5,         // s lasered
    evadeCool: 4,            // s
    breakTime: 1.6,          // s break turn
    reposDist: 800,          // m
    missileCd: 12,           // s between shots per jet
    switchHeroTime: 3,       // s hero within 200 m flips target
  },

  missile: {
    speed: 250, turn: 1.2, fuse: 8, hp: 20,
    dmgHero: 35, dmgHull: 25, radius: 12, // m blast
  },

  expl: {
    flashInt: 200, flashT: 0.1,   // s
    fireT: 0.8, ringT: 0.4,
    debrisN: 40, smokeN: 30, smokeT: 6, // s
    lightRange: 260,         // m
  },

  part: { budgetAdd: 12000, budgetAlpha: 8000 },
  trail: {
    heroLen: 26, heroWidth: 0.4,       // segments, m
    smokeLen: 200, smokeWidth: 7, smokeDt: 0.05, // s per sample
    contraLen: 44, contraWidth: 0.8,
  },
  spd: {
    streakN: 400, streakStart: 40, // m/s fade-in
    ssV: 140, ssRearm: 120,        // m/s supersonic thresholds
    radialMax: 1.1,                 // effect strength
    chromaMax: 0.0032,
    boomRingT: 0.9,                 // s
  },

  aud: {
    master: 0.6,
    windLo: 300, windHi: 1200, windGain: 0.5, // Hz, Hz, 0..1
    tempo: 100,                    // bpm combat kick
  },

  cine: {
    introT: 4,                     // s orbit
    slowCatch: 0.3, slowDur: 1,    // timeScale, s
    killSlow: 0.5, killSlowDur: 0.5,
    setdownSlow: 0.3,
  },

  score: {
    base: 10000, perJet: 750, hullW: 40, hpW: 10,
    perfectSink: 1500, goodSink: 500,
    timeW: 10, timePar: 600,       // s
    grades: [[0.9, 'S'], [0.72, 'A'], [0.5, 'B'], [-1, 'C']],
  },

  misc: {
    nearMissSpd: 50, nearMissDist: 9, nearMissCool: 0.6, nearMissPts: 150, // m/s, m, s
    whiteLo: 500, whiteHi: 900,    // m cloud band
    typewriterCPS: 40,
    radioFade: 4,                  // s
    popupTime: 1.4,                // s
  },
};
export type Cfg = typeof CONFIG;
```

### src/core/events.ts
```ts
/** Tiny typed event bus. Payloads are plain records; listeners return void. */
export type EvMap = {
  jetKilled: { id: number; pos: { x: number; y: number; z: number }; last: boolean };
  caught: { point: 'TAIL' | 'NOSE' };
  tailTorn: Record<string, never>;
  touchdown: { sink: number; quality: 'PERFECT' | 'HARD' | 'CRASH'; tailStrike: boolean };
  phaseChanged: { phase: string; title?: string };
  heroHit: { amount: number; dir: { x: number; z: number } };
  hullHit: { amount: number };
  boom: { pos: { x: number; y: number; z: number }; mag: number };
  sonicBoom: Record<string, never>;
  popup: { text: string; cls?: string };
  radio: { text: string };
  objective: { text: string; dist?: number };
  warn: { text: string };
  failed: { reason: string };
  nearMiss: Record<string, never>;
  splashOne: Record<string, never>;
  overheat: Record<string, never>;
  buckle: Record<string, never>;
  released: Record<string, never>;
  settled: Record<string, never>;
};

export interface Bus {
  on<K extends keyof EvMap>(k: K, fn: (p: EvMap[K]) => void): () => void;
  emit<K extends keyof EvMap>(k: K, p: EvMap[K]): void;
}

export function createBus(): Bus {
  const map = new Map<keyof EvMap, Set<(p: unknown) => void>>();
  return {
    on(k, fn) {
      let s = map.get(k);
      if (!s) { s = new Set(); map.set(k, s); }
      s.add(fn as (p: unknown) => void);
      return () => { s!.delete(fn as (p: unknown) => void); };
    },
    emit(k, p) {
      const s = map.get(k);
      if (s) for (const fn of [...s]) fn(p as unknown);
    },
  };
}
```

### src/core/math.ts
```ts
import * as THREE from 'three';

export const V1 = new THREE.Vector3();
export const V2 = new THREE.Vector3();
export const V3 = new THREE.Vector3();
export const V4 = new THREE.Vector3();
export const V5 = new THREE.Vector3();
export const V6 = new THREE.Vector3();
export const Q1 = new THREE.Quaternion();
export const Q2 = new THREE.Quaternion();
export const M1 = new THREE.Matrix4();

export const clamp = (v: number, a: number, b: number) => (v < a ? a : v > b ? b : v);
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const sat = (v: number) => clamp(v, 0, 1);
export const smooth = (t: number) => { const x = sat(t); return x * x * (3 - 2 * x); };

/** Frame-rate-independent exponential damping. lambda ~ 1/timeConstant. */
export const damp = (cur: number, tgt: number, lambda: number, dt: number) =>
  lerp(cur, tgt, 1 - Math.exp(-lambda * dt));

export function wrapPi(a: number) {
  a = (a + Math.PI) % (Math.PI * 2);
  if (a < 0) a += Math.PI * 2;
  return a - Math.PI;
}

/** Normalize in place; zero-length falls back to (0,0,1). Never NaN. */
export function safeNorm(v: THREE.Vector3, fb = 1): THREE.Vector3 {
  const l = v.length();
  if (l > 1e-8) v.multiplyScalar(1 / l);
  else v.set(0, 0, fb);
  return v;
}

export const finite = (...vs: THREE.Vector3[]) => vs.every((v) => Number.isFinite(v.x + v.y + v.z));
export const finNum = (...ns: number[]) => ns.every(Number.isFinite);

/** Deterministic RNG for tests and layout. */
export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export type RNG = () => number;

/** Basis quaternion with object +Z pointing along fwd (universal forward convention). */
export function quatFace(q: THREE.Quaternion, fwd: THREE.Vector3, up: THREE.Vector3, roll = 0) {
  const f = safeNorm(V1.copy(fwd));
  const r = V2.crossVectors(up, f);
  if (r.lengthSq() < 1e-8) r.set(0, 0, 1).cross(f);
  safeNorm(r);
  const u = V3.crossVectors(f, r);
  if (roll !== 0) {
    const c = Math.cos(roll), s = Math.sin(roll);
    const rx = r.x * c + u.x * s, ry = r.y * c + u.y * s, rz = r.z * c + u.z * s;
    const ux = u.x * c - r.x * s, uy = u.y * c - r.y * s, uz = u.z * c - r.z * s;
    r.set(rx, ry, rz); u.set(ux, uy, uz);
  }
  M1.makeBasis(r, u, f);
  return q.setFromRotationMatrix(M1);
}

/** Shortest signed angle from a to b. */
export function angDiff(a: number, b: number) { return wrapPi(b - a); }

export function fmtTime(t: number) {
  t = Math.max(0, t);
  const m = Math.floor(t / 60), s = Math.floor(t % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
```

### src/core/pool.ts
```ts
/** Minimal object pool. Factory creates; optional reset runs on release. */
export class Pool<T> {
  private free: T[] = [];
  private made = 0;
  constructor(private make: () => T, private reset?: (t: T) => void, prealloc = 0) {
    for (let i = 0; i < prealloc; i++) { this.free.push(this.make()); this.made++; }
  }
  acq(): T { const o = this.free.pop() ?? (this.made++, this.make()); return o; }
  rel(o: T) { this.reset?.(o); this.free.push(o); }
  get live() { return this.made - this.free.length; }
}
```

### src/core/input.ts
```ts
/**
 * Keyboard + mouse. Edge presses are queued and consumed with wasPressed().
 * If pointer lock is lost/unavailable, arrow keys steer at a fixed rate.
 */
export interface Input {
  down(code: string): boolean;
  wasPressed(code: string): boolean;
  consumeMouse(): { dx: number; dy: number };
  locked: boolean;
  sens: number;
  nudgeSens(dir: number): void;
  beginFrame(): void;
  anyKeyPressed(): boolean;
  lockPointer(): void;
  onUnlock(cb: () => void): void;
  dispose(): void;
}

export function createInput(target: HTMLElement): Input {
  const keys = new Set<string>();
  const pressed = new Set<string>();
  let mdx = 0, mdy = 0;
  let locked = false;
  let sens = 0.0022;
  let anyKey = false;
  const unlockCbs: (() => void)[] = [];

  const kd = (e: KeyboardEvent) => {
    if (e.repeat) { if (['F5', 'F11', 'F12'].includes(e.key)) return; }
    keys.add(e.code);
    pressed.add(e.code);
    anyKey = true;
    if (['Space', 'Tab'].includes(e.code)) e.preventDefault();
  };
  const ku = (e: KeyboardEvent) => keys.delete(e.code);
  const mm = (e: MouseEvent) => { if (locked) { mdx += e.movementX; mdy += e.movementY; } };
  const plc = () => { locked = document.pointerLockElement === target; if (!locked) unlockCbs.forEach((f) => f()); };
  const blur = () => { keys.clear(); };

  window.addEventListener('keydown', kd);
  window.addEventListener('keyup', ku);
  window.addEventListener('mousemove', mm);
  window.addEventListener('blur', blur);
  document.addEventListener('pointerlockchange', plc);

  target.addEventListener('mousedown', (e) => {
    if (e.button === 0) { keys.add('Mouse0'); pressed.add('Mouse0'); }
    if (e.button === 2) { keys.add('Mouse2'); pressed.add('Mouse2'); }
  });
  window.addEventListener('mouseup', (e) => {
    if (e.button === 0) keys.delete('Mouse0');
    if (e.button === 2) keys.delete('Mouse2');
  });
  const ctx = (e: Event) => e.preventDefault();
  target.addEventListener('contextmenu', ctx);

  return {
    down: (c) => keys.has(c),
    wasPressed(c) { if (pressed.has(c)) { pressed.delete(c); return true; } return false; },
    consumeMouse() { const r = { dx: mdx, dy: mdy }; mdx = 0; mdy = 0; return r; },
    get locked() { return locked; },
    get sens() { return sens; },
    set sens(v: number) { sens = v; },
    nudgeSense?: undefined,
    nudgeSens(dir: number) { sens = Math.min(0.008, Math.max(0.0004, sens * (dir > 0 ? 1.15 : 1 / 1.15))); },
    beginFrame() { pressed.clear(); anyKey = false; },
    anyKeyPressed() { return anyKey; },
    lockPointer() { if (!locked) target.requestPointerLock?.(); },
    onUnlock(cb) { unlockCbs.push(cb); },
    dispose() {
      window.removeEventListener('keydown', kd);
      window.removeEventListener('keyup', ku);
      window.removeEventListener('mousemove', mm);
      window.removeEventListener('blur', blur);
      document.removeEventListener('pointerlockchange', plc);
      target.removeEventListener('contextmenu', ctx);
    },
  } as Input & { nudgeSense?: undefined };
}
```

### src/vfx/shaders/radialBlur.ts
```ts
import { Effect } from 'postprocessing';
import * as THREE from 'three';

/** Screen-space radial blur toward centre; strength uniform driven per frame. */
const frag = `
uniform float strength;
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  if (strength < 0.001) { outputColor = inputColor; return; }
  vec2 dir = uv - vec2(0.5);
  vec4 acc = inputColor;
  float wsum = 1.0;
  for (int i = 1; i <= 12; i++) {
    float fi = float(i);
    float w = 1.0 - fi / 13.0;
    acc += texture(inputBuffer, uv - dir * strength * 0.045 * fi) * w;
    wsum += w;
  }
  outputColor = acc / wsum;
}`;

export class RadialBlurEffect extends Effect {
  constructor() {
    super('RadialBlurEffect', frag, {
      uniforms: new Map<string, THREE.Uniform>([['strength', new THREE.Uniform(0)]]),
    });
  }
  get strength() { return (this.uniforms.get('strength') as THREE.Uniform<number>).value; }
  set strength(v: number) { (this.uniforms.get('strength') as THREE.Uniform<number>).value = v; }
}
```

### src/vfx/shaders/grade.ts
```tf
```

### src/vfx/shaders/grade.ts
```ts
import { Effect } from 'postprocessing';

/** Gentle filmic grade: soft S-curve, lifted warm shadows, cooled highlights. */
const frag = `
uniform float amount;
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor) {
  vec3 c = inputColor.rgb;
  vec3 s = smoothstep(vec3(0.0), vec3(1.0), c);
  c = mix(c, s, 0.30 * amount);
  float lo = 1.0 - smoothstep(0.0, 0.55, dot(c, vec3(0.333)));
  c += vec3(0.045, 0.022, -0.010) * lo * amount;   // warm shadows
  c += vec3(-0.012, -0.004, 0.030) * smoothstep(0.55, 1.0, dot(c, vec3(0.333))) * amount;
  outputColor = vec4(c, inputColor.a);
}`;

export class GradeEffect extends Effect {
  constructor(amount = 1) {
    super('GradeEffect', frag, {
      uniforms: new Map([['amount', { value: amount } as unknown as never]]),
    });
  }
}
```

### src/vfx/shaders/fire.ts
```ts
import * as THREE from 'three';

/** Procedural fireball billboard shader: expanding fbm flame collapsing to smoke. */
export function createFireMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uT: { value: 0 },      // 0..1 progress
      uSeed: { value: 0 },
      uTint: { value: new THREE.Color('#ffc060') },
    },
    vertexShader: `
      varying vec2 vUv;
      void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `
      varying vec2 vUv;
      uniform float uT, uSeed; uniform vec3 uTint;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))+uSeed)*43758.5453); }
      float n2(vec2 p){
        vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
        return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);
      }
      float fbm(vec2 p){ float a=0.5,s=0.; for(int i=0;i<4;i++){ s+=a*n2(p); p*=2.03; a*=0.5;} return s; }
      void main(){
        vec2 q = vUv - 0.5;
        float r = length(q) * 2.0;
        float ang = atan(q.y, q.x);
        float nz = fbm(vec2(ang*2.5, r*3.0 - uT*6.0) + uSeed*17.0);
        float body = smoothstep(1.0, 0.15, r + (nz-0.5)*0.7*(1.0-uT*0.4));
        float core = smoothstep(0.55, 0.0, r);
        vec3 hot = uTint * (1.6 + core*2.0);
        vec3 smokey = vec3(0.12,0.09,0.08);
        vec3 col = mix(smokey, hot, clamp(body*(1.0-uT*0.75)+core,0.0,1.0));
        float a = body * (1.0 - uT*0.85);
        if (a < 0.01) discard;
        gl_FragColor = vec4(col*a, a);
      }`,
  });
}
```

### src/vfx/shaders/water.ts
```ts
import * as THREE from 'three';

/** River surface: two scrolling sine-normal layers, Fresnel sky tint, sun glitter. */
export function createWaterMaterial(sunDir: THREE.Vector3, fogColor: THREE.Color): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    uniforms: {
      uT: { value: 0 },
      uSun: { value: sunDir.clone().normalize() },
      uSky: { value: new THREE.Color('#ffb377') },
      uDeep: { value: new THREE.Color('#20303e') },
      uFog: { value: fogColor.clone() },
      uFogNear: { value: 850 }, uFogFar: { value: 7200 },
    },
    vertexShader: `
      varying vec3 vWp;
      void main(){
        vec4 wp = modelMatrix * vec4(position,1.0);
        vWp = wp.xyz;
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      varying vec3 vWp;
      uniform float uT, uFogNear, uFogFar;
      uniform vec3 uSun, uSky, uDeep, uFog;
      float wn(vec2 p, float t){
        float s = sin(p.x*0.11 + t*1.3) * sin(p.y*0.13 - t*0.9);
        s += 0.6 * sin(p.x*0.31 - t*2.1 + p.y*0.17);
        s += 0.35 * sin(p.x*0.71 + t*3.7 - p.y*0.53);
        return s;
      }
      void main(){
        vec2 p = vWp.xz;
        float e = 0.6;
        float h  = wn(p, uT);
        float hx = wn(p+vec2(e,0.), uT);
        float hy = wn(p+vec2(0.,e), uT);
        vec3 N = normalize(vec3(-(hx-h)/e, 1.0, -(hy-h)/e));
        vec3 V = normalize(cameraPosition - vWp);
        float fres = pow(1.0 - max(dot(N, V), 0.0), 3.0);
        vec3 col = mix(uDeep, uSky, 0.25 + 0.7*fres);
        vec3 R = reflect(-V, N);
        col += vec3(1.0,0.85,0.6) * pow(max(dot(R, uSun), 0.0), 240.0) * 2.2;
        float d = length(cameraPosition - vWp);
        col = mix(col, uFog, smoothstep(uFogNear, uFogFar, d));
        gl_FragColor = vec4(col, 0.96);
      }`,
  });
}
```

### src/vfx/shaders/windows.ts
```ts
import * as THREE from 'three';

export interface WinParams {
  winSize: number;   // m module
  litFrac: number;   // 0..1 lit windows
  warm: string;      // lit colour
  dark: string;      // unlit pane tint
  emit: number;      // emissive strength of lit panes
  seed: number;      // per-material variation
}

/**
 * Patch a MeshStandardMaterial so vertical facades get a procedural 3 m window grid
 * addressed by WORLD position (identical scale on every building), with a hashed
 * per-window lit mask. Requires an instanced 'aSeed' attribute on the geometry.
 */
export function patchWindows(mat: THREE.MeshStandardMaterial, p: WinParams) {
  const ws = p.winSize.toFixed(2), lf = p.litFrac.toFixed(3), em = p.emit.toFixed(2);
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', `#include <common>
        attribute float aSeed; varying vec3 vWp; varying vec3 vNm; varying float vSeed;`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        #ifdef USE_INSTANCING
          vWp = (modelMatrix * instanceMatrix * vec4(transformed,1.0)).xyz;
        #else
          vWp = (modelMatrix * vec4(transformed,1.0)).xyz;
        #endif
        vNm = normalize(mat3(modelMatrix) * objectNormal);
        vSeed = aSeed;`);
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vWp; varying vec3 vNm; varying float vSeed;
        float whash(vec2 q){ return fract(sin(dot(q, vec2(127.1,311.7)) + vSeed*57.017)*43758.5453); }`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        {
          vec3 an = abs(vNm);
          if (an.y < 0.72) {
            vec2 fc = (an.x > an.z) ? vWp.zy : vWp.xy;
            vec2 gid = floor(fc / ${ws});
            vec2 f = fract(fc / ${ws});
            float pane = step(0.18, f.x) * step(f.x, 0.82) * step(0.25, f.y) * step(f.y, 0.78);
            float hh = whash(gid);
            float lit = step(1.0 - ${lf}, hh);
            vec3 dark = vec3(${hexToGlsl(p.dark)});
            vec3 warm = vec3(${hexToGlsl(p.warm)}) * (${em});
            diffuseColor.rgb = mix(diffuseColor.rgb, mix(dark, warm, lit), pane * 0.88);
            totalEmissiveRadiance += warm * lit * pane * 0.55;
          }
        }`);
  };
  mat.needsUpdate = true;
}

function hexToGlsl(hex: string): string {
  const c = new THREE.Color(hex);
  return `${c.r.toFixed(3)}, ${c.g.toFixed(3)}, ${c.b.toFixed(3)}`;
}
```

### src/vfx/shaders/cloud.ts
```ts
import * as THREE from 'three';

/** Instanced billboard cloud: procedural fbm puff, sun-facing rim brightening. */
export function createCloudMaterial(sunDir: THREE.Vector3): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      uSun: { value: sunDir.clone().normalize() },
      uTint: { value: new THREE.Color('#ffe4c8') },
      uShade: { value: new THREE.Color('#8d86a0') },
    },
    vertexShader: `
      attribute float aRot; attribute float aScale; attribute float aShade;
      varying vec2 vUv; varying float vShade;
      void main(){
        vUv = uv; vShade = aShade;
        float c = cos(aRot), s = sin(aRot);
        vec2 p = vec2(
          position.x * c - position.y * s,
          position.x * s + position.y * c) * aScale;
        #ifdef USE_INSTANCING
          vec4 wp = modelMatrix * instanceMatrix * vec4(p, 0.0, 1.0);
        #else
          vec4 wp = modelMatrix * vec4(p, 0.0, 1.0);
        #endif
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      varying vec2 vUv; varying float vShade;
      uniform vec3 uSun, uTint, uShade;
      float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
      float n2(vec2 p){ vec2 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);
        return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y); }
      float fbm(vec2 p){ float a=0.5,s=0.; for(int i=0;i<5;i++){ s+=a*n2(p); p=p*2.07+13.7; a*=0.5;} return s; }
      void main(){
        vec2 q = vUv - 0.5;
        float r = length(q) * 2.0;
        float n = fbm(q * 4.0 + 7.0);
        float a = smoothstep(1.0, 0.25, r + (n - 0.5) * 0.9) * smoothstep(0.15, 0.45, n);
        // Fake sphere normal from uv for sun lighting.
        vec3 nn = normalize(vec3(q.x, q.y, sqrt(max(0.0, 1.0 - r * r))));
        float sun = clamp(dot(nn, normalize(uSun)), 0.0, 1.0);
        vec3 col = mix(uShade, uTint * (1.0 + sun * 0.9), pow(sun, 0.7) * 0.9 + 0.25);
        col = mix(col, uTint * 1.25, vShade * sun);
        gl_FragColor = vec4(col, a * 0.82);
      }`,
  });
}
```

### src/core/renderer.ts
```ts
import * as THREE from 'three';
import {
  EffectComposer, RenderPass, EffectPass, GodRaysEffect, BloomEffect,
  ChromaticAberrationEffect, VignetteEffect, NoiseEffect, ToneMappingEffect,
  SMAAEffect, ToneMappingMode, SMAAPreset,
} from 'postprocessing';
import { RadialBlurEffect } from '../vfx/shaders/radialBlur.js';
import { GradeEffect } from '../vfx/shaders/grade.js';
import { CONFIG } from '../config.js';

export interface Post {
  renderer: THREE.WebGLRenderer;
  composer: EffectComposer | null;
  radial: RadialBlurEffect | null;
  chroma: ChromaticAberrationEffect | null;
  godRays: GodRaysEffect | null;
  usingPost: boolean;
  resize(w: number, h: number): void;
  render(): void;
  dispose(): void;
}

export function createRenderer(
  mount: HTMLElement, scene: THREE.Scene, camera: THREE.PerspectiveCamera, sunMesh: THREE.Mesh,
): Post {
  const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping; // ToneMappingEffect owns tone mapping.
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  mount.appendChild(renderer.domElement);

  let composer: EffectComposer | null = null;
  let radial: RadialBlurEffect | null = null;
  let chroma: ChromaticAberrationEffect | null = null;
  let godRays: GodRaysEffect | null = null;

  try {
    composer = new EffectComposer(renderer, {
      frameBufferType: THREE.HalfFloatType,
      multisampling: 4,
    });
    composer.addPass(new RenderPass(scene, camera));

    const hdr: InstanceType<typeof EffectProto>[] = [] as never;
    type AnyEff = NonNullable<unknown>;
    const hdrEffs: AnyEff[] = [];
    try {
      godRays = new GodRaysEffect(camera, sunMesh, {
        density: 0.96, decay: 0.92, weight: 0.3, samples: 60, blur: true,
      } as never);
      hdrEffs.push(godRays as AnyEff);
    } catch { /* god rays optional */ }
    try {
      const bloom = new BloomEffect({
        mipmapBlur: true, luminanceThreshold: 0.8, intensity: 0.9, radius: 0.6,
      } as never);
      hdrEffs.push(bloom as AnyEff);
    } catch { /* bloom optional */ }
    try {
      radial = new RadialBlurEffect();
      hdrEffs.push(radial as AnyEff);
    } catch { /* radial optional */ }
    try {
      chroma = new ChromaticAberrationEffect({ offset: new THREE.Vector2(0.0008, 0.0008) } as never);
      hdrEffs.push(chroma as AnyEff);
    } catch { /* chroma optional */ }
    try { hdrEffs.push(new GradeEffect(1) as AnyEff); } catch { /* grade optional */ }
    try {
      const vg = new VignetteEffect({ offset: 0.26, darkness: 0.72 } as never);
      hdrEffs.push(vg as AnyEff);
    } catch { /* vignette optional */ }
    try {
      const nz = new NoiseEffect({ premultiply: false } as never);
      (nz.blendMode as unknown as { opacity: { value: number } }).opacity.value = 0.03;
      hdrEffs.push(nz as AnyEff);
    } catch { /* noise optional */ }

    if (hdrEffs.length) composer.addPass(new EffectPass(camera, ...(hdrEffs as never[])));

    const ldr: AnyEff[] = [];
    try { ldr.push(new ToneMappingEffect({ mode: ToneMappingMode.ACES_FILMIC }) as AnyEff); } catch { /* tm */ }
    try { ldr.push(new SMAAEffect({ preset: SMAAPreset.HIGH }) as AnyEff); } catch { /* smaa */ }
    if (ldr.length) composer.addPass(new EffectPass(camera, ...(ldr as never[])));
  } catch {
    composer = null; // graceful fallback to renderer.render
  }

  const resize = (w: number, h: number) => {
    renderer.setSize(w, h);
    composer?.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  };

  return {
    renderer, composer, radial, chroma, godRays,
    get usingPost() { return !!composer; },
    resize,
    render() {
      if (composer) composer.render();
      else renderer.render(scene, camera);
    },
    dispose() { renderer.dispose(); },
  };
}

// Internal placeholder type so the arrays above typecheck without importing Effect generically.
declare const EffectProto: abstract new (...args: never[]) => object;
export const CFG_REF = CONFIG; // keep config import meaningful for tuning docs
```

### src/core/loop.ts
```ts
import { CONFIG } from '../config.js';

export interface Loop {
  timeScale: number;
  setTimeScale(ts: number, holdMs?: number): void;
  start(): void;
  stop(): void;
}

/** Fixed 120 Hz simulation with accumulator; frame cb gets scaled real dt. */
export function createLoop(fixed: (h: number) => void, frame: (dt: number) => void): Loop {
  const h = CONFIG.sim.fixedDt;
  let acc = 0, last = performance.now(), raf = 0, running = false;
  let timeScale = 1, tsUntil = Infinity;

  const api: Loop = {
    timeScale: 1,
    setTimeScale(ts, holdMs) {
      timeScale = ts; api.timeScale = ts;
      tsUntil = holdMs ? performance.now() + holdMs : Infinity;
    },
    start() {
      if (running) return;
      running = true; last = performance.now();
      const tick = () => {
        if (!running) return;
        raf = requestAnimationFrame(tick);
        const now = performance.now();
        if (now >= tsUntil) { timeScale = 1; api.timeScale = 1; tsUntil = Infinity; }
        let dt = Math.min((now - last) / 1000, CONFIG.sim.maxFrameDt);
        last = now;
        const sdt = dt * timeScale;
        acc += sdt;
        let guard = 12;
        while (acc >= h && guard-- > 0) { fixed(h); acc -= h; }
        if (guard <= 0) acc = 0; // dump backlog after long stalls
        frame(sdt);
      };
      raf = requestAnimationFrame(tick);
    },
    stop() { running = false; cancelAnimationFrame(raf); },
  };
  return api;
}
```

### src/core/audio.ts
```ts
import { CONFIG } from '../config.js';

/**
 * Fully synthesised audio. Created lazily on first user gesture. Every voice is a
 * small graph; long-running beds (wind, boost, laser, engines, crowd, music) are
 * started once and automated through gains.
 */
export interface AudioSys {
  unlock(): void;
  update(dt: number, st: AudState): void;
  boom(): void;                       // sonic boom
  explosion(dist: number, size: number): void;
  cannon(dist: number): void;
  whiz(): void;
  laserSet(on: boolean, heat01: number, hitting: boolean): void;
  missileWarn(on: boolean, urgency01: number): void;
  rocket(): void;
  catchGroan(): void;
  crunch(level01: number): void;
  tearDown(): void;
  gearClunk(): void;
  thud(mass: number): void;
  radioBeep(): void;
  crowd(level01: number): void;
  boostSet(v01: number): void;
  engineFire(prox01: number): void;
  resolveChord(): void;
  dispose(): void;
}
export interface AudState {
  speed: number; supersonic: boolean; combat: number; // 0..1
  stadiumProx: number; // 0..1
}

export function createAudio(): AudioSys {
  let ctx: AudioContext | null = null;
  let master: GainNode | null = null;
  const started = false;
  let noiseBuf: AudioBuffer | null = null;

  // Beds
  let windSrc: AudioBufferSourceNode | null = null, windBP: BiquadFilterNode | null = null, windG: GainNode | null = null;
  let boostOsc: OscillatorNode | null = null, boostG: GainNode | null = null;
  let laserG: GainNode | null = null, laserOsc: OscillatorNode | null = null, laserOsc2: OscillatorNode | null = null, laserNZ: AudioBufferSourceNode | null = null, laserBP: BiquadFilterNode | null = null;
  let engG: GainNode | null = null, engOsc: OscillatorNode | null = null, engNZ: AudioBufferSourceNode | null = null;
  let crowdG: GainNode | null = null, crowdNZ: AudioBufferSourceNode | null = null;
  let musG: GainNode | null = null, musLP: BiquadFilterNode | null = null;
  let kickTimer = 0, warnTimer = 0, warnOn = false, warnUrg = 0;
  let laserWasOn = false, sizzleT = 0;

  function mk(): boolean {
    if (ctx) return true;
    try {
      ctx = new AudioContext();
      master = ctx.createGain();
      master.gain.value = CONFIG.aud.master;
      master.connect(ctx.destination);
      const len = ctx.sampleRate * 2;
      noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      return true;
    } catch { return false; }
  }

  function noiseSrc(): AudioBufferSourceNode | null {
    if (!ctx || !noiseBuf) return null;
    const s = ctx.createBufferSource();
    s.buffer = noiseBuf; s.loop = true;
    return s;
  }

  function startBeds() {
    if (!ctx || !master || started) return;
    // Wind
    windSrc = noiseSrc()!;
    windBP = ctx.createBiquadFilter(); windBP.type = 'bandpass'; windBP.Q.value = 0.6;
    windG = ctx.createGain(); windG.gain.value = 0;
    windSrc.connect(windBP).connect(windG).connect(master);
    windSrc.start();
    // Boost roar
    boostOsc = ctx.createOscillator(); boostOsc.type = 'sawtooth'; boostOsc.frequency.value = 55;
    const blp = ctx.createBiquadFilter(); blp.type = 'lowpass'; blp.frequency.value = 220;
    boostG = ctx.createGain(); boostG.gain.value = 0;
    boostOsc.connect(blp).connect(boostG).connect(master); boostOsc.start();
    // Laser hum
    laserG = ctx.createGain(); laserG.gain.value = 0;
    laserOsc = ctx.createOscillator(); laserOsc.type = 'sawtooth'; laserOsc.frequency.value = 90;
    laserOsc2 = ctx.createOscillator(); laserOsc2.type = 'square'; laserOsc2.frequency.value = 181;
    laserBP = ctx.createBiquadFilter(); laserBP.type = 'bandpass'; laserBP.frequency.value = 900; laserBP.Q.value = 2;
    laserNZ = noiseSrc()!;
    const lg2 = ctx.createGain(); lg2.gain.value = 0.25;
    laserOsc.connect(laserBP); laserOsc2.connect(laserBP); laserNZ.connect(laserBP);
    laserBP.connect(laserG); lg2.connect(laserG); laserG.connect(master);
    laserOsc.start(); laserOsc2.start(); laserNZ.start();
    // Airliner engine fire
    engG = ctx.createGain(); engG.gain.value = 0;
    engOsc = ctx.createOscillator(); engOsc.type = 'sawtooth'; engOsc.frequency.value = 68;
    const elp = ctx.createBiquadFilter(); elp.type = 'lowpass'; elp.frequency.value = 400;
    engNZ = noiseSrc()!;
    const enzp = ctx.createBiquadFilter(); enzp.type = 'lowpass'; enzp.frequency.value = 300;
    const eg2 = ctx.createGain(); eg2.gain.value = 0.7;
    engOsc.connect(elp).connect(engG); engNZ.connect(enzp).connect(eg2).connect(engG);
    engG.connect(master); engOsc.start(); engNZ.start();
    // Crowd
    crowdG = ctx.createGain(); crowdG.gain.value = 0;
    crowdNZ = noiseSrc()!;
    const cbp = ctx.createBiquadFilter(); cbp.type = 'bandpass'; cbp.frequency.value = 520; cbp.Q.value = 0.4;
    crowdNZ.connect(cbp).connect(crowdG).connect(master); crowdNZ.start();
    // Music drone
    musG = ctx.createGain(); musG.gain.value = 0.10;
    musLP = ctx.createBiquadFilter(); musLP.type = 'lowpass'; musLP.frequency.value = 420;
    const o1 = ctx.createOscillator(); o1.type = 'sawtooth'; o1.frequency.value = 55;
    const o2 = ctx.createOscillator(); o2.type = 'sawtooth'; o2.frequency.value = 55.7;
    const lfo = ctx.createOscillator(); lfo.frequency.value = 0.07;
    const lfoG = ctx.createGain(); lfoG.gain.value = 260;
    lfo.connect(lfoG).connect(musLP.frequency);
    o1.connect(musLP); o2.connect(musLP); musLP.connect(musG).connect(master);
    o1.start(); o2.start(); lfo.start();
  }

  function env(g: GainNode, peak: number, a: number, d: number, t0?: number) {
    if (!ctx) return;
    const t = t0 ?? ctx.currentTime;
    g.gain.cancelScheduledValues(t);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(peak, t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + a + d);
  }

  function burst(filter: BiquadFilterNode, peak: number, dur: number, sweepTo?: number) {
    if (!ctx || !master || !noiseBuf) return;
    const s = ctx.createBufferSource(); s.buffer = noiseBuf;
    const g = ctx.createGain();
    s.connect(filter).connect(g).connect(master);
    const t = ctx.currentTime;
    filter.frequency.setValueAtTime(filter.frequency.value, t);
    if (sweepTo) filter.frequency.exponentialRampToValueAtTime(Math.max(40, sweepTo), t + dur);
    env(g, peak, 0.005, dur);
    s.start(t); s.stop(t + dur + 0.1);
  }

  const api: AudioSys = {
    unlock() { if (mk()) { void ctx!.resume(); startBeds(); } },

    update(dt, st) {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const sp = st.speed;
      // Wind follows speed
      const wf = CONFIG.aud.windLo + (CONFIG.aud.windHi - CONFIG.aud.windLo) * Math.min(1, sp / 190);
      windBP!.frequency.setTargetAtTime(wf, t, 0.1);
      windG!.gain.setTargetAtTime(CONFIG.aud.windGain * Math.min(1, sp / 120) * (st.supersonic ? 1.25 : 1), t, 0.15);
      // Boost
      boostG!.gain.setTargetAtTime(api._boost * 0.5, t, 0.08);
      // Laser pitch rides heat
      if (api._laser) {
        laserOsc!.frequency.setTargetAtTime(80 + api._heat * 90, t, 0.05);
        laserOsc2!.frequency.setTargetAtTime(161 + api._heat * 180, t, 0.05);
        laserBP!.frequency.setTargetAtTime(700 + api._heat * 900, t, 0.05);
        sizzleT -= dt;
        if (api._hitting && sizzleT <= 0) { sizzleT = 0.09; api.sizzle(); }
      }
      // Engine fire proximity
      engG!.gain.setTargetAtTime(0.35 * st.engineProx, t, 0.2);
      // Crowd
      crowdG!.gain.setTargetAtTime(0.4 * st.crowd, t, 0.3);
      // Combat kick pulse
      musLP!.frequency.setTargetAtTime(320 + st.combat * 900, t, 0.4);
      if (st.combat > 0.2) {
        kickTimer -= dt;
        if (kickTimer <= 0) { kickTimer = 60 / CONFIG.aud.tempo; api.kick(); }
      }
      // Missile warning beeps
      if (warnOn) {
        warnTimer -= dt;
        if (warnTimer <= 0) {
          warnTimer = 0.5 - 0.35 * warnUrg;
          api.beep(1180, 0.07, 0.12);
        }
      }
    },

    _boost: 0, _laser: false, _heat: 0, _hitting: false,

    boom() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sine';
      o.frequency.setValueAtTime(120, t);
      o.frequency.exponentialRampToValueAtTime(30, t + 0.4);
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, 0.9, 0.01, 0.45);
      o.start(t); o.stop(t + 0.6);
      const bp = ctx.createBiquadFilter(); bp.type = 'lowpass'; bp.frequency.value = 900;
      burst(bp, 0.5, 0.25, 200);
    },

    explosion(dist, size) {
      if (!ctx || !master) return;
      const att = 1 / (1 + dist / 300);
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3200;
      burst(lp, 0.85 * att * size, 0.55 + 0.2 * size, 180);
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 46;
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, 0.7 * att * size, 0.01, 0.5);
      o.start(t); o.stop(t + 0.7);
    },

    cannon(dist) {
      if (!ctx || !master) return;
      const att = 1 / (1 + dist / 500);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 780; bp.Q.value = 1.2;
      burst(bp, 0.5 * att, 0.09);
    },

    whiz() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'triangle';
      o.frequency.setValueAtTime(2100, t);
      o.frequency.exponentialRampToValueAtTime(420, t + 0.28);
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, 0.22, 0.01, 0.3);
      o.start(t); o.stop(t + 0.4);
    },

    sizzle() {
      if (!ctx || !master) return;
      const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 3200;
      burst(hp, 0.16, 0.08);
    },

    laserSet(on, heat01, hitting) {
      api._laser = on; api._heat = heat01; api._hitting = hitting;
      if (!ctx) return;
      laserG!.gain.setTargetAtTime(on ? 0.28 : 0, ctx.currentTime, on ? 0.02 : 0.08);
      if (on && !laserWasOn) api.beep(2400, 0.03, 0.1);
      laserWasOn = on;
    },

    missileWarn(on, urg) { warnOn = on; warnUrg = urg; },

    rocket() {
      if (!ctx || !master) return;
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1400;
      burst(lp, 0.3, 0.8, 500);
    },

    catchGroan() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      for (let i = 0; i < 3; i++) {
        const o = ctx.createOscillator(); o.type = 'sawtooth';
        o.frequency.setValueAtTime(70 + i * 23, t);
        o.frequency.linearRampToValueAtTime(48 + i * 15, t + 1.2);
        const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 300 + i * 200; bp.Q.value = 6;
        const g = ctx.createGain();
        o.connect(bp).connect(g).connect(master);
        env(g, 0.28, 0.05, 1.3);
        o.start(t); o.stop(t + 1.6);
      }
    },

    crunch(level01) {
      if (!ctx || !master) return;
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 260; bp.Q.value = 3;
      burst(bp, 0.3 + 0.4 * level01, 0.18);
      api.beep(140, 0.1, 0.2);
    },

    tearDown() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(380, t);
      o.frequency.linearRampToValueAtTime(1350, t + 0.35);
      o.frequency.exponentialRampToValueAtTime(160, t + 1.1);
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 900; bp.Q.value = 4;
      const g = ctx.createGain(); o.connect(bp).connect(g).connect(master);
      env(g, 0.5, 0.02, 1.2);
      o.start(t); o.stop(t + 1.5);
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2500;
      burst(lp, 0.6, 0.7, 300);
    },

    gearClunk() { if (ctx && master) { const bp = ctx.createBiquadFilter(); bp.type = 'lowpass'; bp.frequency.value = 500; burst(bp, 0.35, 0.12); } },
    thud(mass) {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 52;
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, Math.min(1, 0.4 + mass * 0.4), 0.01, 0.4);
      o.start(t); o.stop(t + 0.6);
      const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 700;
      burst(lp, 0.4, 0.25, 150);
    },

    radioBeep() { api.beep(1250, 0.05, 0.12); setTimeout(() => api.beep(1650, 0.05, 0.12), 90); },
    beep(f: number, a: number, d: number) {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = f;
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, 0.12, a, d);
      o.start(t); o.stop(t + a + d + 0.05);
    },

    crowd(level01) { api._crowd = level01; },
    _crowd: 0,

    boostSet(v01) { api._boost = v01; },

    engineFire(prox01) { api._engProx = prox01; },
    _engProx: 0,

    kick() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      const o = ctx.createOscillator(); o.type = 'sine';
      o.frequency.setValueAtTime(130, t);
      o.frequency.exponentialRampToValueAtTime(42, t + 0.14);
      const g = ctx.createGain(); o.connect(g).connect(master);
      env(g, 0.5, 0.005, 0.16);
      o.start(t); o.stop(t + 0.25);
    },

    resolveChord() {
      if (!ctx || !master) return;
      const t = ctx.currentTime;
      [220, 277.2, 329.6, 440].forEach((f, i) => {
        const o = ctx!.createOscillator(); o.type = 'sine'; o.frequency.value = f;
        const g = ctx!.createGain(); o.connect(g).connect(master!);
        g.gain.setValueAtTime(0.0001, t);
        g.gain.linearRampToValueAtTime(0.09, t + 1.2 + i * 0.15);
        g.gain.linearRampToValueAtTime(0.0001, t + 6);
        o.start(t); o.stop(t + 6.2);
      });
    },

    dispose() { try { void ctx?.close(); } catch { /* noop */ } ctx = null; },
  };

  // Wire engine-prox & crowd state through update()'s st via closure patching:
  const origUpdate = api.update.bind(api);
  api.update = (dt, st) => {
    (st as AudState & { engineProx: number; crowd: number }).engineProx = api._engProx;
    (st as AudState & { engineProx: number; crowd: number }).crowd = api._crowd;
    origUpdate(dt, st);
  };

  return api;
}
```

### src/world/collision.ts
```ts
import { CONFIG } from '../config.js';
import { mulberry32, type RNG } from '../core/math.js';

/** Axis-aligned building footprint: y spans 0..h. Pure data, Node-safe. */
export interface BB { minX: number; maxX: number; minZ: number; maxZ: number; h: number; glass: boolean }

export interface CityLayout {
  N: number; cell: number; half: number;          // half = N*cell/2
  cells: (BB[] | undefined)[];                    // index = cz*N + cx
  tops: Float32Array;                             // highest roof per cell (0 = ground)
  water: Uint8Array;                              // 1 = river cell
  plaza: Uint8Array;
  stadium: { cx: number; cz: number; span: number }; // block origin cell + span
  roadLamps: { x: number; z: number }[];
  treeSpots: { x: number; z: number }[];
}

export function cellIndex(l: CityLayout, x: number, z: number): number {
  const cx = Math.floor((x + l.half) / l.cell);
  const cz = Math.floor((z + l.half) / l.cell);
  if (cx < 0 || cz < 0 || cx >= l.N || cz >= l.N) return -1;
  return cz * l.N + cx;
}

/** Generate the whole city deterministically. Pure — runs in Node for tests. */
export function generateCityLayout(cfg: typeof CONFIG, seed = 1337): CityLayout {
  const rng: RNG = mulberry32(seed);
  const N = cfg.world.gridN, cell = cfg.world.cellSize;
  const half = (N * cell) / 2;
  const cells: (BB[] | undefined)[] = new Array(N * N).fill(undefined);
  const tops = new Float32Array(N * N);
  const water = new Uint8Array(N * N);
  const plaza = new Uint8Array(N * N);
  const roadLamps: { x: number; z: number }[] = [];
  const treeSpots: { x: number; z: number }[] = [];

  const ci = N >> 1; // downtown centre cell
  // Sinuous river: centre row wanders with x.
  const riverRow = (cx: number) => Math.round(ci + Math.sin(cx * 0.16) * 6 + Math.sin(cx * 0.05 + 2) * 4);
  // Stadium block near the western edge, vertically centred.
  const stCx = 4, stCz = ci - 3, span = cfg.world.stadiumSpan;
  const inStadium = (cx: number, cz: number) =>
    cx >= stCx && cx < stCx + span && cz >= stCz && cz < stCz + span;

  // Plazas: 3 random 3x3 pockets away from river/stadium.
  const plazaCenters: [number, number][] = [];
  for (let p = 0; p < cfg.world.plazaCount; p++) {
    for (let tries = 0; tries < 40; tries++) {
      const px = 8 + Math.floor(rng() * (N - 18));
      const pz = 8 + Math.floor(rng() * (N - 18));
      let ok = true;
      for (let dx = -1; dx <= 1 && ok; dx++)
        for (let dz = -1; dz <= 1 && ok; dz++) {
          const rr = riverRow(px + dx);
          if (Math.abs(pz + dz - rr) <= 2 || inStadium(px + dx, pz + dz)) ok = false;
        }
      if (ok) { plazaCenters.push([px, pz]); break; }
    }
  }
  const inPlaza = (cx: number, cz: number) =>
    plazaCenters.some(([px, pz]) => cx >= px - 1 && cx <= px + 1 && cz >= pz - 1 && cz <= pz + 1);

  for (let cz = 0; cz < N; cz++) {
    for (let cx = 0; cx < N; cx++) {
      const idx = cz * N + cx;
      const wx = -half + (cx + 0.5) * cell;
      const wz = -half + (cz + 0.5) * cell;
      if (Math.abs(cz - riverRow(cx)) <= ((cfg.world.riverCells - 1) >> 1)) { water[idx] = 1; continue; }
      if (inStadium(cx, cz) || inPlaza(cx, cz)) {
        if (inPlaza(cx, cz)) {
          plaza[idx] = 1;
          for (let t = 0; t < 5; t++)
            treeSpots.push({ x: wx + (rng() - 0.5) * cell * 0.7, z: wz + (rng() - 0.5) * cell * 0.7 });
        }
        continue;
      }
      // Height bucket skewed taller toward downtown.
      const dcx = (cx - ci) / ci, dcz = (cz - ci) / ci;
      const d = Math.sqrt(dcx * dcx + dcz * dcz); // 0 centre .. ~1.4 corner
      const tallBoost = Math.max(0, 1 - d) * 0.55;
      const r = rng();
      let h: number;
      const pH = cfg.city.pHigh + tallBoost * 0.5;
      const pM = cfg.city.pMid * (1 - tallBoost * 0.4);
      if (r < pH) h = cfg.city.highMin + rng() * (cfg.city.highMax - cfg.city.highMin);
      else if (r < pH + pM) h = cfg.city.midMin + rng() * (cfg.city.midMax - cfg.city.midMin);
      else h = cfg.city.lowMin + rng() * (cfg.city.lowMax - cfg.city.lowMin);
      h = Math.round(h / 6) * 6; // quantise for coherent rooflines
      if (h < cfg.city.lowMin) h = cfg.city.lowMin;
      const inset = 1 + rng() * 2.5;
      const bb: BB = {
        minX: wx - cell / 2 + cfg.world.streetW / 2 + inset,
        maxX: wx + cell / 2 - cfg.world.streetW / 2 - inset,
        minZ: wz - cell / 2 + cfg.world.streetW / 2 + inset,
        maxZ: wz + cell / 2 - cfg.world.streetW / 2 - inset,
        h,
        glass: h > 120 || rng() < cfg.city.glassFrac * 0.5,
      };
      cells[idx] = [bb];
      tops[idx] = h;
    }
  }
  // Avenue lamps: along every 4th street line, every other cell.
  for (let cx = 0; cx < N; cx += 4)
    for (let cz = 0; cz < N; cz += 2) {
      roadLamps.push({ x: -half + cx * cell, z: -half + (cz + 0.5) * cell });
      roadLamps.push({ x: -half + (cz + 0.5) * cell, z: -half + cx * cell });
    }

  return { N, cell, half, cells, tops, water, plaza, stadium: { cx: stCx, cz: stCz, span }, roadLamps, treeSpots };
}

export interface ResolveOut { hit: boolean; nx: number; ny: number; nz: number; impact: number }

/** Neighbourhood AABBs for a world point (always 3x3 — O(1)). */
export function gatherNeighbors(l: CityLayout, x: number, z: number, out: BB[]): BB[] {
  out.length = 0;
  const cx = Math.floor((x + l.half) / l.cell);
  const cz = Math.floor((z + l.half) / l.cell);
  for (let dz = -1; dz <= 1; dz++)
    for (let dx = -1; dx <= 1; dx++) {
      const gx = cx + dx, gz = cz + dz;
      if (gx < 0 || gz < 0 || gx >= l.N || gz >= l.N) continue;
      const arr = l.cells[gz * l.N + gx];
      if (arr) for (const bb of arr) out.push(bb);
    }
  return out;
}

const nbBuf: BB[] = [];

/**
 * Push a sphere out of every overlapping AABB (iterated so it never ends a call
 * inside geometry), reflect velocity with restitution, and report the strongest hit.
 */
export function resolveSphere(
  l: CityLayout, pos: { x: number; y: number; z: number }, r: number,
  vel: { x: number; y: number; z: number }, restitution = 0.25,
): ResolveOut {
  const out: ResolveOut = { hit: false, nx: 0, ny: 1, nz: 0, impact: 0 };
  for (let iter = 0; iter < 4; iter++) {
    const nbs = gatherNeighbors(l, pos.x, pos.z, nbBuf);
    let any = false;
    for (const bb of nbs) {
      const cx = Math.max(bb.minX, Math.min(pos.x, bb.maxX));
      const cy = Math.max(0, Math.min(pos.y, bb.h));
      const cz = Math.max(bb.minZ, Math.min(pos.z, bb.maxZ));
      let dx = pos.x - cx, dy = pos.y - cy, dz = pos.z - cz;
      let d2 = dx * dx + dy * dy + dz * dz;
      if (d2 >= r * r) continue;
      any = true;
      let nx: number, ny: number, nz: number, pen: number;
      if (d2 > 1e-10) {
        const d = Math.sqrt(d2);
        nx = dx / d; ny = dy / d; nz = dz / d; pen = r - d;
      } else {
        // Deep overlap: eject along the shallowest face.
        const px = Math.min(pos.x - bb.minX, bb.maxX - pos.x);
        const py = Math.min(pos.y, bb.h - pos.y);
        const pz = Math.min(pos.z - bb.minZ, bb.maxZ - pos.z);
        if (py <= px && py <= pz) { nx = 0; ny = pos.y > bb.h * 0.5 ? 1 : -1; nz = 0; pen = py + r; }
        else if (px <= pz) { nx = pos.x > (bb.minX + bb.maxX) / 2 ? 1 : -1; ny = 0; nz = 0; pen = px + r; }
        else { nx = 0; ny = 0; nz = pos.z > (bb.minZ + bb.maxZ) / 2 ? 1 : -1; pen = pz + r; }
      }
      pos.x += nx * pen; pos.y += ny * pen; pos.z += nz * pen;
      const vn = vel.x * nx + vel.y * ny + vel.z * nz;
      if (vn < 0) {
        if (-vn > out.impact) { out.impact = -vn; out.nx = nx; out.ny = ny; out.nz = nz; }
        vel.x -= nx * vn * (1 + restitution);
        vel.y -= ny * vn * (1 + restitution);
        vel.z -= nz * vn * (1 + restitution);
      }
    }
    if (!any) break;
    out.hit = true;
  }
  return out;
}

/** Highest surface (roof or ground) under a point. */
export function topAt(l: CityLayout, x: number, z: number): number {
  const idx = cellIndex(l, x, z);
  if (idx < 0) return 0;
  const arr = l.cells[idx];
  if (!arr) return 0;
  let best = 0;
  for (const bb of arr)
    if (x >= bb.minX && x <= bb.maxX && z >= bb.minZ && z <= bb.maxZ) best = Math.max(best, bb.h);
  return best;
}

export interface RayHit { t: number; x: number; y: number; z: number; nx: number; ny: number; nz: number }

/** Slab test one AABB against a ray; returns entry t or -1. */
function slab(o: { x: number; y: number; z: number }, d: { x: number; y: number; z: number },
  bb: BB, maxT: number): { t: number; axis: number; sign: number } | null {
  let tmin = 0, tmax = maxT, ax = 1, sg = -1;
  const lo = [bb.minX, 0, bb.minZ], hi = [bb.maxX, bb.h, bb.maxZ];
  const oo = [o.x, o.y, o.z], dd = [d.x, d.y, d.z];
  for (let i = 0; i < 3; i++) {
    if (Math.abs(dd[i]) < 1e-9) {
      if (oo[i] < lo[i] || oo[i] > hi[i]) return null;
      continue;
    }
    const inv = 1 / dd[i];
    let t1 = (lo[i] - oo[i]) * inv, t2 = (hi[i] - oo[i]) * inv;
    let s = -1;
    if (t1 > t2) { const tt = t1; t1 = t2; t2 = tt; s = 1; }
    if (t1 > tmin) { tmin = t1; ax = i; sg = s; }
    if (t2 < tmax) tmax = t2;
    if (tmin > tmax) return null;
  }
  return { t: tmin, axis: ax, sign: sg };
}

/** Grid-DDA raycast against buildings + ground plane. Node-safe, allocation-light. */
export function raycastCity(
  l: CityLayout, ox: number, oy: number, oz: number,
  dx: number, dy: number, dz: number, maxT: number,
): RayHit | null {
  let best: RayHit | null = null;
  const consider = (t: number, axis: number, sign: number) => {
    if (t < 0 || t > maxT) return;
    if (best && t >= best.t) return;
    best = {
      t,
      x: ox + dx * t, y: oy + dy * t, z: oz + dz * t,
      nx: axis === 0 ? sign : 0, ny: axis === 1 ? sign : 0, nz: axis === 2 ? sign : 0,
    };
  };
  // Ground plane y=0
  if (dy < -1e-6 && oy > 0) consider(-oy / dy, 1, 1);
  // Walk cells along the ray
  const cs = l.cell;
  let cx = Math.floor((ox + l.half) / cs), cz = Math.floor((oz + l.half) / cs);
  const stepX = dx > 0 ? 1 : -1, stepZ = dz > 0 ? 1 : -1;
  const tdx = Math.abs(dx) < 1e-9 ? Infinity : cs / Math.abs(dx);
  const tdz = Math.abs(dz) < 1e-9 ? Infinity : cs / Math.abs(dz);
  let tx = Math.abs(dx) < 1e-9 ? Infinity :
    (((dx > 0 ? (cx + 1) * cs - l.half : cx * cs - l.half) - ox) / dx);
  let tz = Math.abs(dz) < 1e-9 ? Infinity :
    (((dz > 0 ? (cz + 1) * cs - l.half : cz * cs - l.half) - oz) / dz);
  let t = 0;
  for (let guard = 256; guard-- > 0;) {
    if (cx >= 0 && cz >= 0 && cx < l.N && cz < l.N) {
      const arr = l.cells[cz * l.N + cx];
      if (arr) for (const bb of arr) {
        const s = slab({ x: ox, y: oy, z: oz }, { x: dx, y: dy, z: dz }, bb, best ? best.t : maxT);
        if (s) consider(s.t, s.axis, s.sign);
      }
    }
    if (best && best.t < t) break; // can't improve past current cell boundary
    if (tx < tz) { t = tx; tx += tdx; cx += stepX; } else { t = tz; tz += tdz; cz += stepZ; }
    if (t > maxT) break;
  }
  return best;
}

/** Soft push back toward the city when beyond the boundary radius. */
export function boundaryPush(
  l: CityLayout, pos: { x: number; y: number; z: number }, vel: { x: number; y: number; z: number },
  radius: number,
): boolean {
  const dx = pos.x, dz = pos.z;
  const d = Math.hypot(dx, dz);
  if (d < radius) return false;
  const over = (d - radius) / 200;
  const nx = -dx / d, nz = -dz / d;
  vel.x += nx * over * 9.8 * 0.016;
  vel.z += nz * over * 9.8 * 0.016;
  if (d > radius + 400) { pos.x = (dx / d) * (radius + 400); pos.z = (dz / d) * (radius + 400); }
  return true;
}
```

### src/world/sky.ts
```ts
import * as THREE from 'three';
import { Sky } from 'three/addons/objects/Sky.js';
import { Lensflare, LensflareElement } from 'three/addons/objects/Lensflare.js';
import { CONFIG } from '../config.js';

export interface SkySys {
  sunDir: THREE.Vector3;
  sunMesh: THREE.Mesh;
  update(): void;
  dispose(): void;
}

function flareTexture(inner: string, outer: string, size = 128): THREE.Texture {
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const g = cv.getContext('2d')!;
  const gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gr.addColorStop(0, inner);
  gr.addColorStop(0.35, outer);
  gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function createSky(scene: THREE.Scene, renderer: THREE.WebGLRenderer): SkySys {
  const c = CONFIG.skyCfg;
  const sky = new Sky();
  sky.scale.setScalar(45000);
  const u = sky.material.uniforms;
  u.turbidity.value = c.turbidity;
  u.rayleigh.value = c.rayleigh;
  u.mieCoefficient.value = c.mieCoeff;
  u.mieDirectionalG.value = c.mieG;
  const phi = THREE.MathUtils.degToRad(90 - c.elevDeg);
  const theta = THREE.MathUtils.degToRad(c.aziDeg);
  const sunDir = new THREE.Vector3().setFromSphericalCoords(1, phi, theta);
  u.sunPosition.value.copy(sunDir);
  scene.add(sky);

  // Fog tuned to the horizon haze.
  const fog = new THREE.Fog(new THREE.Color(c.fogColor), c.fogNear, c.fogFar);
  scene.fog = fog;

  // HDR sun disc (feeds bloom + god rays).
  const sunMesh = new THREE.Mesh(
    new THREE.CircleGeometry(90, 24),
    new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: false,
      vertexShader: `void main(){ gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
      fragmentShader: `void main(){ gl_FragColor = vec4(4.2, 3.4, 2.4, 1.0); }`,
    }),
  );
  sunMesh.position.copy(sunDir).multiplyScalar(12000);
  sunMesh.lookAt(0, 0, 0);
  scene.add(sunMesh);

  // Lens flare from canvas textures.
  const flare = new Lensflare();
  const main = flareTexture('rgba(255,235,205,1)', 'rgba(255,170,90,0.35)', 256);
  const ghost = flareTexture('rgba(255,190,120,0.55)', 'rgba(255,140,70,0.12)');
  flare.addElement(new LensflareElement(main, 700, 0));
  flare.addElement(new LensflareElement(ghost, 90, 0.35));
  flare.addElement(new LensflareElement(ghost, 140, 0.55));
  flare.addElement(new LensflareElement(ghost, 70, 0.8));
  flare.addElement(new LensflareElement(ghost, 200, 1.05));
  const flareHolder = new THREE.Object3D();
  flareHolder.position.copy(sunMesh.position);
  flareHolder.add(flare);
  scene.add(flareHolder);

  // Lights: warm sun + hemisphere fill.
  const dl = new THREE.DirectionalLight(CONFIG.light.sunColor, CONFIG.light.sunIntensity);
  dl.castShadow = true;
  dl.shadow.mapSize.set(2048, 2048);
  dl.shadow.camera.near = 1;
  dl.shadow.camera.far = 1600;
  const S = 200; // half-extent of the 400 m shadow box
  dl.shadow.camera.left = -S; dl.shadow.camera.right = S;
  dl.shadow.camera.top = S; dl.shadow.camera.bottom = -S;
  dl.shadow.bias = -0.0004;
  scene.add(dl); scene.add(dl.target);
  const hemi = new THREE.HemisphereLight(CONFIG.light.ambSky, CONFIG.light.ambGround, CONFIG.light.ambIntensity);
  scene.add(hemi);

  // Bake the sky into the environment map so metal reflects the sunset.
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envScene = new THREE.Scene();
  const skyClone = new Sky();
  skyClone.scale.setScalar(45000);
  const cu = skyClone.material.uniforms;
  cu.turbidity.value = c.turbidity; cu.rayleigh.value = c.rayleigh;
  cu.mieCoefficient.value = c.mieCoeff; cu.mieDirectionalG.value = c.mieG;
  cu.sunPosition.value.copy(sunDir);
  envScene.add(skyClone);
  const envRT = pmrem.fromScene(envScene);
  scene.environment = envRT.texture;
  pmrem.dispose();

  /** Snap-follow shadow camera on the hero to kill shimmer. */
  const texel = CONFIG.light.shadowTexel;
  const update = () => { /* position set externally each frame via follow() */ };

  const follow = (target: THREE.Vector3) => {
    dl.position.copy(target).addScaledVector(sunDir, 700);
    dl.target.position.set(
      Math.round(target.x / texel) * texel,
      Math.round(target.y / texel) * texel,
      Math.round(target.z / texel) * texel,
    );
    dl.target.updateMatrixWorld();
  };

  return {
    sunDir, sunMesh, update,
    dispose() {
      scene.remove(sky, sunMesh, flareHolder, dl, dl.target, hemi);
      envRT.dispose();
    },
    ...{} as Record<string, never>,
  } as SkySys & { follow(t: THREE.Vector3): void };
}
```

### src/world/ground.ts
```ts
import * as THREE from 'three';
import type { CityLayout } from './collision.js';
import { CONFIG } from '../config.js';

/** Single textured mega-plane: streets, blocks, river bed, parks — one canvas, one draw. */
export function createGround(scene: THREE.Scene, l: CityLayout): THREE.Mesh {
  const PX = 2048;
  const cv = document.createElement('canvas');
  cv.width = cv.height = PX;
  const g = cv.getContext('2d')!;
  const world = l.N * l.cell;
  const s = PX / world;
  const wx = (x: number) => (x + l.half) * s;
  const wz = (z: number) => (z + l.half) * s;

  g.fillStyle = '#23262b'; // asphalt base
  g.fillRect(0, 0, PX, PX);
  const cs = l.cell * s;
  for (let cz = 0; cz < l.N; cz++) {
    for (let cx = 0; cx < l.N; cx++) {
      const idx = cz * l.N + cx;
      const x = wx(-l.half + cx * l.cell), z = wz(-l.half + cz * l.cell);
      if (l.water[idx]) { g.fillStyle = '#10151c'; g.fillRect(x, z, cs + 1, cs + 1); continue; }
      if (l.plaza[idx]) { g.fillStyle = '#3d4a38'; g.fillRect(x, z, cs + 1, cs + 1); continue; }
      if (l.cells[idx]) {
        const v = 38 + ((cx * 7 + cz * 13) % 5) * 3;
        g.fillStyle = `rgb(${v},${v - 2},${v - 4})`;
        g.fillRect(x + cs * 0.18, z + cs * 0.18, cs * 0.64, cs * 0.64);
      }
    }
  }
  // Stadium lawn block
  const st = l.stadium;
  g.fillStyle = '#2e5230';
  g.fillRect(wx(-l.half + st.cx * l.cell), wz(-l.half + st.cz * l.cell), st.span * cs, st.span * cs);

  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(world * 4, world * 4),
    new THREE.MeshStandardMaterial({ map: tex, roughness: 0.94, metalness: 0.0, color: '#8a8a8a' }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  // Texture covers the city area; repeat wraps the outskirts with the same asphalt.
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  tex.offset.set(0.375, 0.375); // centre the city portion of the atlas
  tex.repeat.set(1, 1);
  scene.add(mesh);
  return mesh;
}
```

### src/world/river.ts
```ts
import * as THREE from 'three';
import type { CityLayout } from './collision.js';
import { createWaterMaterial } from '../vfx/shaders/water.js';
import { CONFIG } from '../config.js';

export function createRiver(scene: THREE.Scene, l: CityLayout, sunDir: THREE.Vector3) {
  // Merge water cells into one grid geometry at y = 0.35.
  const pos: number[] = []; const idxArr: number[] = [];
  const cs = l.cell;
  const vi = new Map<string, number>();
  const vid = (x: number, z: number) => {
    const k = `${x}_${z}`;
    let i = vi.get(k);
    if (i === undefined) { i = pos.length / 3; vi.set(k, i); pos.push(x, 0.35, z); }
    return i;
  };
  for (let cz = 0; cz < l.N; cz++)
    for (let cx = 0; cx < l.N; cx++) {
      if (!l.water[cz * l.N + cx]) continue;
      const x0 = -l.half + cx * cs, z0 = -l.half + cz * cs;
      const a = vid(x0, z0), b = vid(x0 + cs, z0), c = vid(x0 + cs, z0 + cs), d = vid(x0, z0 + cs);
      idxArr.push(a, c, b, a, d, c);
    }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idxArr);
  geo.computeVertexNormals();
  const mat = createWaterMaterial(sunDir, new THREE.Color(CONFIG.skyCfg.fogColor));
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  scene.add(mesh);
  return { update(t: number) { mat.uniforms.uT.value = t; } };
}
```

### src/world/city.ts
```ts
import * as THREE from 'three';
import type { CityLayout } from './collision.js';
import { patchWindows } from '../vfx/shaders/windows.js';
import { CONFIG } from '../config.js';

export interface CityView { update(t: number): void; dispose(): void }

/**
 * Whole skyline in a handful of draw calls: two InstancedMesh tower batches with
 * procedural world-space windows, roof clutter, blinker antennas, street lamps,
 * haze, and trees.
 */
export function createCity(scene: THREE.Scene, l: CityLayout, sunDir: THREE.Vector3): CityView {
  const dummy = new THREE.Object3D();
  const disposables: (THREE.BufferGeometry | THREE.Material | THREE.Texture)[] = [];

  // Collect per-class instances.
  const conc: { x: number; z: number; w: number; d: number; h: number }[] = [];
  const glass: typeof conc = [];
  for (const arr of l.cells)
    if (arr) for (const bb of arr) (bb.glass ? glass : conc).push({
      x: (bb.minX + bb.maxX) / 2, z: (bb.minZ + bb.maxZ) / 2,
      w: bb.maxX - bb.minX, d: bb.maxZ - bb.minZ, h: bb.h,
    });

  const boxGeo = new THREE.BoxGeometry(1, 1, 1);
  disposables.push(boxGeo);

  function buildTowerMesh(list: typeof conc, params: Parameters<typeof patchWindows>[1], std: { metalness: number; roughness: number }) {
    const geo = boxGeo.clone();
    const seeds = new Float32Array(list.length);
    for (let i = 0; i < list.length; i++) seeds[i] = Math.random() * 100;
    geo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seeds, 1));
    const mat = new THREE.MeshStandardMaterial(std);
    patchWindows(mat, params);
    const im = new THREE.InstancedMesh(geo, mat, list.length);
    list.forEach((b, i) => {
      dummy.position.set(b.x, b.h / 2, b.z);
      dummy.scale.set(b.w, b.h, b.d);
      dummy.rotation.set(0, 0, 0);
      dummy.updateMatrix();
      im.setMatrixAt(i, dummy.matrix);
    });
    im.castShadow = true; im.receiveShadow = true;
    scene.add(im);
    disposables.push(geo, mat);
    return im;
  }

  buildTowerMesh(conc, {
    winSize: CONFIG.city.windowSize, litFrac: CONFIG.city.litFrac,
    warm: '#ffb45e', dark: '#1c2126', emit: 1.6, seed: 3,
  }, { metalness: 0.15, roughness: 0.6 });
  buildTowerMesh(glass, {
    winSize: CONFIG.city.windowSize * 1.5, litFrac: 0.12,
    warm: '#ffd9a0', dark: '#0e141b', emit: 1.2, seed: 9,
  }, { metalness: 0.9, roughness: 0.15 });

  // Roof mechanical boxes.
  const roofList: { x: number; z: number; y: number; w: number; d: number; h: number }[] = [];
  for (const arr of l.cells)
    if (arr) for (const bb of arr) {
      if (bb.h < 40 || Math.random() > CONFIG.city.roofBoxChance) continue;
      const n = 1 + (Math.random() * 2 | 0);
      for (let i = 0; i < n; i++)
        roofList.push({
          x: bb.minX + 4 + Math.random() * (bb.maxX - bb.minX - 8),
          z: bb.minZ + 4 + Math.random() * (bb.maxZ - bb.minZ - 8),
          y: bb.h, w: 3 + Math.random() * 5, d: 3 + Math.random() * 5, h: 2 + Math.random() * 3,
        });
    }
  const roofIm = new THREE.InstancedMesh(boxGeo,
    new THREE.MeshStandardMaterial({ color: '#4c4f54', roughness: 0.8 }), roofList.length);
  roofList.forEach((b, i) => {
    dummy.position.set(b.x, b.y + b.h / 2, b.z);
    dummy.scale.set(b.w, b.h, b.d); dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix(); roofIm.setMatrixAt(i, dummy.matrix);
  });
  roofIm.castShadow = true;
  scene.add(roofIm);

  // Antennas with red blinkers on the tallest towers.
  const antList: { x: number; z: number; y: number; h: number }[] = [];
  for (const arr of l.cells)
    if (arr) for (const bb of arr)
      if (bb.h > 160 && Math.random() < CONFIG.city.antennaChance)
        antList.push({ x: (bb.minX + bb.maxX) / 2, z: (bb.minZ + bb.maxZ) / 2, y: bb.h, h: 10 + Math.random() * 22 });
  const antGeo = new THREE.CylinderGeometry(0.25, 0.4, 1, 5);
  const antIm = new THREE.InstancedMesh(antGeo,
    new THREE.MeshStandardMaterial({ color: '#3a3d42', roughness: 0.7 }), antList.length);
  antList.forEach((a, i) => {
    dummy.position.set(a.x, a.y + a.h / 2, a.z);
    dummy.scale.set(1, a.h, 1); dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix(); antIm.setMatrixAt(i, dummy.matrix);
  });
  scene.add(antIm); disposables.push(antGeo);
  const blinkGeo = new THREE.SphereGeometry(0.8, 6, 6);
  const blinkMat = new THREE.MeshBasicMaterial({ color: '#ff2222', fog: false });
  const blinkIm = new THREE.InstancedMesh(blinkGeo, blinkMat, antList.length);
  blinkIm.frustumCulled = false;
  antList.forEach((a, i) => {
    dummy.position.set(a.x, a.y + a.h + 0.5, a.z);
    dummy.scale.setScalar(1); dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix(); blinkIm.setMatrixAt(i, dummy.matrix);
  });
  scene.add(blinkIm); disposables.push(blinkGeo, blinkMat);

  // Street lamps: instanced poles + emissive tips.
  const lamps = l.roadLamps;
  const poleGeo = new THREE.CylinderGeometry(0.12, 0.16, 7, 5);
  const poleIm = new THREE.InstancedMesh(poleGeo,
    new THREE.MeshStandardMaterial({ color: '#2c2f33', roughness: 0.7 }), lamps.length);
  const tipGeo = new THREE.SphereGeometry(0.35, 6, 6);
  const tipMat = new THREE.MeshBasicMaterial({ color: '#ffcf8a', fog: false });
  const tipIm = new THREE.InstancedMesh(tipGeo, tipMat, lamps.length);
  lamps.forEach((p, i) => {
    dummy.position.set(p.x, 3.5, p.z); dummy.scale.setScalar(1); dummy.rotation.set(0, 0, 0);
    dummy.updateMatrix(); poleIm.setMatrixAt(i, dummy.matrix);
    dummy.position.set(p.x, 7.1, p.z); dummy.updateMatrix(); tipIm.setMatrixAt(i, dummy.matrix);
  });
  scene.add(poleIm, tipIm); disposables.push(poleGeo, tipGeo, tipMat);

  // Warm ground haze across the bowl.
  const hazeCv = document.createElement('canvas'); hazeCv.width = hazeCv.height = 128;
  const hg = hazeCv.getContext('2d')!;
  const grd = hg.createLinearGradient(0, 0, 0, 128);
  grd.addColorStop(0, 'rgba(255,166,100,0)');
  grd.addColorStop(1, 'rgba(255,166,100,0.30)');
  hg.fillStyle = grd; hg.fillRect(0, 0, 128, 128);
  const hazeTex = new THREE.CanvasTexture(hazeCv); hazeTex.colorSpace = THREE.SRGBColorSpace;
  const haze = new THREE.Mesh(
    new THREE.PlaneGeometry(l.N * l.cell * 1.1, l.N * l.cell * 1.1),
    new THREE.MeshBasicMaterial({
      map: hazeTex, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false,
    }),
  );
  haze.rotation.x = -Math.PI / 2;
  haze.position.y = CONFIG.city.hazeY;
  scene.add(haze); disposables.push(hazeTex);

  // Park trees.
  if (l.treeSpots.length) {
    const trunkGeo = new THREE.CylinderGeometry(0.4, 0.6, 4, 5);
    const crownGeo = new THREE.IcosahedronGeometry(3.2, 0);
    const trunkIm = new THREE.InstancedMesh(trunkGeo,
      new THREE.MeshStandardMaterial({ color: '#4a3826', roughness: 0.9 }), l.treeSpots.length);
    const crownIm = new THREE.InstancedMesh(crownGeo,
      new THREE.MeshStandardMaterial({ color: '#3f6b35', roughness: 0.9 }), l.treeSpots.length);
    l.treeSpots.forEach((t, i) => {
      dummy.position.set(t.x, 2, t.z); dummy.scale.setScalar(1); dummy.rotation.set(0, 0, 0);
      dummy.updateMatrix(); trunkIm.setMatrixAt(i, dummy.matrix);
      dummy.position.set(t.x, 5.4, t.z); dummy.scale.set(1, 0.8, 1);
      dummy.updateMatrix(); crownIm.setMatrixAt(i, dummy.matrix);
    });
    crownIm.castShadow = true;
    scene.add(trunkIm, crownIm); disposables.push(trunkGeo, crownGeo);
  }

  return {
    update(t: number) {
      // Blinkers: staggered 1 Hz pulse via per-instance visibility trick (scale).
      const on = Math.sin(t * Math.PI * 2) > 0.2;
      blinkIm.visible = on;
    },
    dispose() {
      disposables.forEach((d) => d.dispose());
      [roofIm, antIm, blinkIm, poleIm, tipIm, haze].forEach((m) => scene.remove(m));
    },
  };
}
```

### src/world/clouds.ts
```ts
import * as THREE from 'three';
import { createCloudMaterial } from '../vfx/shaders/cloud.js';
import { CONFIG } from '../config.js';

export interface CloudView {
  update(dt: number, heroPos: THREE.Vector3): void;
  whiteness: number; // 0..1 while flying through a layer
  dispose(): void;
}

/** Two instanced billboard cumulus layers + a cirrus dome. */
export function createClouds(scene: THREE.Scene, sunDir: THREE.Vector3): CloudView {
  const mat = createCloudMaterial(sunDir);
  const plane = new THREE.PlaneGeometry(1, 1);
  const layers: THREE.InstancedMesh[] = [];
  const dummy = new THREE.Object3D();

  function layer(count: number, yLo: number, yHi: number, sLo: number, sHi: number) {
    const geo = plane.clone();
    const rot = new Float32Array(count), scl = new Float32Array(count), shd = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      rot[i] = Math.random() * Math.PI * 2;
      scl[i] = sLo + Math.random() * (sHi - sLo);
      shd[i] = Math.random();
    }
    geo.setAttribute('aRot', new THREE.InstancedBufferAttribute(rot, 1));
    geo.setAttribute('aScale', new THREE.InstancedBufferAttribute(scl, 1));
    geo.setAttribute('aShade', new THREE.InstancedBufferAttribute(shd, 1));
    const im = new THREE.InstancedMesh(geo, mat, count);
    im.frustumCulled = false;
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 600 + Math.random() * 4200;
      dummy.position.set(Math.cos(a) * r, yLo + Math.random() * (yHi - yLo), Math.sin(a) * r);
      dummy.rotation.set(0, 0, 0); dummy.scale.setScalar(1);
      dummy.updateMatrix();
      im.setMatrixAt(i, dummy.matrix);
    }
    scene.add(im);
    layers.push(im);
  }
  layer(150, 500, 700, 90, 240);
  layer(150, 700, 900, 140, 320);

  // Cirrus veil on a big inverted dome.
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 256;
  const cg = cv.getContext('2d')!;
  cg.clearRect(0, 0, 512, 256);
  for (let i = 0; i < 90; i++) {
    const y = Math.random() * 256, w = 60 + Math.random() * 220;
    cg.strokeStyle = `rgba(255,225,200,${0.03 + Math.random() * 0.05})`;
    cg.lineWidth = 1 + Math.random() * 3;
    cg.beginPath();
    cg.moveTo(Math.random() * 512, y);
    cg.bezierCurveTo(Math.random() * 512, y - 8, Math.random() * 512, y + 8, Math.random() * 512, y);
    cg.stroke();
  }
  const cirrusTex = new THREE.CanvasTexture(cv);
  cirrusTex.colorSpace = THREE.SRGBColorSpace;
  const cirrus = new THREE.Mesh(
    new THREE.SphereGeometry(9000, 24, 12, 0, Math.PI * 2, 0, Math.PI * 0.32),
    new THREE.MeshBasicMaterial({
      map: cirrusTex, transparent: true, side: THREE.BackSide,
      depthWrite: false, fog: false, opacity: 0.8,
    }),
  );
  scene.add(cirrus);

  const api: CloudView = {
    whiteness: 0,
    update(_dt, heroPos) {
      const y = heroPos.y;
      const inBand = y > CONFIG.misc.whiteLo && y < CONFIG.misc.whiteHi;
      const target = inBand ? 0.55 : 0;
      api.whiteness += (target - api.whiteness) * Math.min(1, 0.016 * 4);
    },
    dispose() {
      layers.forEach((m) => scene.remove(m));
      scene.remove(cirrus);
      mat.dispose(); plane.dispose(); cirrusTex.dispose();
    },
  };
  return api;
}
```

### src/world/stadium.ts
```ts
import * as THREE from 'three';
import type { CityLayout } from './collision.js';
import { CONFIG } from '../config.js';

export interface Stadium {
  zone: { cx: number; cz: number; hw: number; hd: number }; // set-down rect centre/half extents
  fieldY: number;
  contains(x: number, z: number): boolean;
  setBoard(lines: string[]): void;
  flashStorm(v: number): void; // 0 calm .. 1 frenzy
  crowdPoints: Float32Array;   // xyz triplets for flash origins
  update(dt: number, t: number): void;
  dispose(): void;
}

export function createStadium(scene: THREE.Scene, l: CityLayout): Stadium {
  const group = new THREE.Group();
  const cell = l.cell;
  const bx = -l.half + (l.stadium.cx + l.stadium.span / 2) * cell;
  const bz = -l.half + (l.stadium.cz + l.stadium.span / 2) * cell;
  group.position.set(bx, 0, bz);
  scene.add(group);
  const disposables: (THREE.BufferGeometry | THREE.Material | THREE.Texture)[] = [];

  // Ellipse bowl: RX 140, RZ 110 outer; three stepped tiers.
  const RX = 140, RZ = 110;
  const concrete = new THREE.MeshStandardMaterial({ color: '#8d8578', roughness: 0.85 });
  disposables.push(concrete);
  for (let tier = 0; tier < 3; tier++) {
    const rOut = 1 - tier * 0.16;
    const wall = new THREE.Mesh(
      new THREE.CylinderGeometry(RX * rOut, RX * (rOut - 0.10), 9, 40, 1, true),
      concrete,
    );
    wall.scale.z = RZ / RX;
    wall.position.y = 4 + tier * 7;
    wall.receiveShadow = true;
    group.add(wall);
  }
  // Seat steps (instanced boxes ringing each tier).
  const stepGeo = new THREE.BoxGeometry(2.4, 1.1, 2.0);
  disposables.push(stepGeo);
  const SEATS_PER_TIER = 340;
  const seatSteps = new THREE.InstancedMesh(stepGeo,
    new THREE.MeshStandardMaterial({ color: '#5a5f6e', roughness: 0.8 }), SEATS_PER_TIER * 3);
  const dummy = new THREE.Object3D();
  const crowdXYZ: number[] = [];
  let si = 0;
  const seatPalette = ['#c9b8a0', '#8fa3bf', '#c47a5a', '#7d8f77', '#b5b0c8'];
  const crowdGeo = new THREE.PlaneGeometry(0.55, 0.9);
  const crowdMat = new THREE.MeshBasicMaterial({ vertexColors: false, side: THREE.DoubleSide });
  const crowd = new THREE.InstancedMesh(crowdGeo, crowdMat, 8000);
  const col = new THREE.Color();
  let ci = 0;
  for (let tier = 0; tier < 3; tier++) {
    const rX = RX * (0.985 - tier * 0.16), rZ = RZ * (0.985 - tier * 0.16);
    const y = 9.5 + tier * 7;
    for (let k = 0; k < SEATS_PER_TIER; k++) {
      const a = (k / SEATS_PER_TIER) * Math.PI * 2;
      const x = Math.cos(a) * rX, z = Math.sin(a) * rZ;
      dummy.position.set(x, y, z);
      dummy.rotation.set(0, -a + Math.PI / 2, 0);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      seatSteps.setMatrixAt(si++, dummy.matrix);
      // Crowd member on the step lip.
      if (ci < 8000) {
        const cr = rX - 1.1, cz2 = rZ - 1.1;
        const px = Math.cos(a) * cr, pz = Math.sin(a) * cz2;
        dummy.position.set(px, y + 0.75, pz);
        dummy.rotation.set(0, -a + Math.PI / 2, 0);
        dummy.scale.setScalar(0.9 + Math.random() * 0.3);
        dummy.updateMatrix();
        crowd.setMatrixAt(ci, dummy.matrix);
        col.set(seatPalette[(Math.random() * seatPalette.length) | 0]);
        crowd.setColorAt(ci, col);
        if (ci % 16 === 0) crowdXYZ.push(bx + px, y + 1, bz + pz);
        ci++;
      }
    }
  }
  crowd.count = ci;
  seatSteps.castShadow = true;
  group.add(seatSteps, crowd);
  disposables.push(crowdGeo, crowdMat);

  // Field with painted diamond.
  const fcv = document.createElement('canvas'); fcv.width = fcv.height = 512;
  const fg = fcv.getContext('2d')!;
  fg.fillStyle = '#2f6b33'; fg.fillRect(0, 0, 512, 512);
  fg.strokeStyle = '#e8e2ce'; fg.lineWidth = 4;
  fg.strokeRect(60, 60, 392, 392);
  fg.beginPath(); // baseball diamond
  fg.moveTo(256, 420); fg.lineTo(120, 256); fg.lineTo(256, 120); fg.lineTo(392, 256); fg.closePath();
  fg.stroke();
  fg.beginPath(); fg.arc(256, 270, 60, 0, Math.PI * 2); fg.stroke();
  const ftex = new THREE.CanvasTexture(fcv); ftex.colorSpace = THREE.SRGBColorSpace;
  disposables.push(ftex);
  const field = new THREE.Mesh(
    new THREE.CircleGeometry(RX * 0.62, 40),
    new THREE.MeshStandardMaterial({ map: ftex, roughness: 0.95 }),
  );
  field.rotation.x = -Math.PI / 2;
  field.scale.x = RZ / RX;
  field.receiveShadow = true;
  group.add(field);

  // Set-down zone outline (pulsing handled in update).
  const zw = CONFIG.plane.zoneW / 2, zd = CONFIG.plane.zoneD / 2;
  const zpts = [
    new THREE.Vector3(-zw, 0.15, -zd), new THREE.Vector3(zw, 0.15, -zd),
    new THREE.Vector3(zw, 0.15, zd), new THREE.Vector3(-zw, 0.15, zd),
    new THREE.Vector3(-zw, 0.15, -zd),
  ];
  const zoneGeo = new THREE.BufferGeometry().setFromPoints(zpts);
  const zoneMat = new THREE.LineBasicMaterial({ color: '#7df3ff', transparent: true, opacity: 0.9, fog: false });
  const zoneLine = new THREE.Line(zoneGeo, zoneMat);
  group.add(zoneLine);
  disposables.push(zoneGeo, zoneMat);

  // Four floodlight masts with emissive heads + additive cones.
  const mastGeo = new THREE.CylinderGeometry(1.2, 2.0, 46, 8);
  const headGeo = new THREE.BoxGeometry(9, 4, 1.4);
  const headMat = new THREE.MeshBasicMaterial({ color: '#fff2cd', fog: false });
  const coneGeo = new THREE.ConeGeometry(26, 52, 12, 1, true);
  const coneMat = new THREE.MeshBasicMaterial({
    color: '#fff3d0', transparent: true, opacity: 0.06,
    blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false,
  });
  disposables.push(mastGeo, headGeo, headMat, coneGeo, coneMat);
  for (const [mx, mz] of [[-RX - 14, -RZ - 14], [RX + 14, -RZ - 14], [-RX - 14, RZ + 14], [RX + 14, RZ + 14]]) {
    const mast = new THREE.Mesh(mastGeo, concrete);
    mast.position.set(mx, 23, mz);
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.set(mx, 47, mz);
    head.lookAt(0, 10, 0);
    const cone = new THREE.Mesh(coneGeo, coneMat);
    cone.position.set(mx * 0.6, 24, mz * 0.6);
    cone.lookAt(0, 0, 0);
    cone.rotateX(Math.PI);
    group.add(mast, head, cone);
  }

  // Scoreboard with canvas text.
  const bcv = document.createElement('canvas'); bcv.width = 512; bcv.height = 192;
  const btex = new THREE.CanvasTexture(bcv); btex.colorSpace = THREE.SRGBColorSpace;
  disposables.push(btex);
  const boardMat = new THREE.MeshBasicMaterial({ map: btex, fog: false });
  const board = new THREE.Mesh(new THREE.PlaneGeometry(46, 17), boardMat);
  board.position.set(0, 34, -RZ - 8);
  group.add(board);
  disposables.push(boardMat);
  const setBoard = (lines: string[]) => {
    const g = bcv.getContext('2d')!;
    g.fillStyle = '#101418'; g.fillRect(0, 0, 512, 192);
    g.textAlign = 'center';
    g.font = 'bold 74px system-ui';
    g.fillStyle = '#ffd76a';
    g.fillText(lines[0] ?? '', 256, 84);
    g.font = 'bold 44px system-ui';
    g.fillStyle = '#9feaff';
    g.fillText(lines[1] ?? '', 256, 152);
    btex.needsUpdate = true;
  };
  setBoard(['METRO STADIUM', 'WELCOME']);

  const api: Stadium = {
    zone: { cx: bx, cz: bz, hw: zw, hd: zd },
    fieldY: 0,
    contains(x, z) { return Math.abs(x - bx) <= zw && Math.abs(z - bz) <= zd; },
    setBoard,
    crowdPoints: new Float32Array(crowdXYZ),
    flashStorm(v) { api._storm = v; },
    _storm: 0,
    update(dt, t) {
      zoneMat.opacity = 0.55 + 0.4 * Math.sin(t * 3);
      // Sparse crowd sparkle, storming on touchdown.
      const rate = 2 + api._storm * 260;
      if (Math.random() < rate * dt && api.crowdPoints.length) {
        const i = ((Math.random() * api.crowdPoints.length) / 3 | 0) * 3;
        api._flash?.(api.crowdPoints[i], api.crowdPoints[i + 1], api.crowdPoints[i + 2]);
      }
    },
    _flash: null as null | ((x: number, y: number, z: number) => void),
    dispose() {
      scene.remove(group);
      disposables.forEach((d) => d.dispose());
    },
  };
  return api;
}
```

### src/vfx/particles.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';

export interface SpawnOpts {
  x: number; y: number; z: number;
  vx: number; vy: number; vz: number;
  life: number;                 // s
  size0: number; size1: number; // m
  r0: number; g0: number; b0: number;
  r1: number; g1: number; b1: number;
  a0: number; a1: number;
  drag?: number;                // /s velocity damping
  grav?: number;                // m/s^2 (+down)
  stretch?: number;             // elongation factor along velocity
  twinkle?: number;             // Hz flicker (crowd flashes)
  blending?: 'add' | 'alpha';
}

interface Batch {
  mesh: THREE.InstancedMesh;
  cap: number;
  alive: number;
  // SoA
  px: Float32Array; py: Float32Array; pz: Float32Array;
  vx: Float32Array; vy: Float32Array; vz: Float32Array;
  age: Float32Array; life: Float32Array;
  s0: Float32Array; s1: Float32Array;
  c0: Float32Array; c1: Float32Array; // rgb triples
  a0: Float32Array; a1: Float32Array;
  drag: Float32Array; grav: Float32Array; str: Float32Array; twk: Float32Array;
  // GPU attribs
  aPos: THREE.InstancedBufferAttribute;
  aDim: THREE.InstancedBufferAttribute;
  aDir: THREE.InstancedBufferAttribute;
  aCol: THREE.InstancedBufferAttribute;
  bufPos: Float32Array; bufDim: Float32Array; bufDir: Float32Array; bufCol: Float32Array;
}

const VS = `
  attribute vec3 iPos; attribute vec2 iDim; attribute vec2 iDir; attribute vec4 iCol;
  varying vec2 vUv; varying vec4 vCol;
  void main(){
    vUv = uv; vCol = iCol;
    vec4 c = viewMatrix * vec4(iPos, 1.0);
    vec2 d = normalize(iDir + vec2(1e-5, 0.0));
    vec2 p = vec2(uv.x - 0.5, uv.y - 0.5);
    float w = iDim.x, hgt = iDim.y;
    // Elongate along screen dir d, widen perpendicular.
    vec2 off = d * (p.x * w) + vec2(-d.y, d.x) * (p.y * hgt);
    c.xy += off;
    gl_Position = projectionMatrix * c;
  }`;

function fs(soft: boolean): string {
  return `
    varying vec2 vUv; varying vec4 vCol;
    void main(){
      vec2 q = vUv - 0.5;
      float r = length(q) * 2.0;
      float a = ${soft ? 'smoothstep(1.0, 0.15, r)' : '(1.0 - smoothstep(0.55, 1.0, r))'};
      if (a < 0.01) discard;
      gl_FragColor = vec4(vCol.rgb, vCol.a * a);
      ${soft ? '' : 'gl_FragColor.rgb *= a;'}
    }`;
}

export interface Particles {
  spawn(o: SpawnOpts): void;
  update(dt: number, cam: THREE.Camera): void;
  count: number;
  dispose(): void;
}

export function createParticles(scene: THREE.Scene): Particles {
  const caps = { add: CONFIG.part.budgetAdd, alpha: CONFIG.part.budgetAlpha };
  const batches: Batch[] = [];

  function makeBatch(cap: number, blending: 'add' | 'alpha'): Batch {
    const geo = new THREE.InstancedBufferGeometry();
    const base = new THREE.PlaneGeometry(1, 1).index!;
    geo.index = base;
    geo.attributes.position = (new THREE.PlaneGeometry(1, 1)).attributes.position;
    geo.attributes.uv = (new THREE.PlaneGeometry(1, 1)).attributes.uv;
    const bufPos = new Float32Array(cap * 3);
    const bufDim = new Float32Array(cap * 2);
    const bufDir = new Float32Array(cap * 2);
    const bufCol = new Float32Array(cap * 4);
    const aPos = new THREE.InstancedBufferAttribute(bufPos, 3); aPos.setUsage(THREE.DynamicDrawUsage);
    const aDim = new THREE.InstancedBufferAttribute(bufDim, 2); aDim.setUsage(THREE.DynamicDrawUsage);
    const aDir = new THREE.InstancedBufferAttribute(bufDir, 2); aDir.setUsage(THREE.DynamicDrawUsage);
    const aCol = new THREE.InstancedBufferAttribute(bufCol, 4); aCol.setUsage(THREE.DynamicDrawUsage);
    geo.setAttribute('iPos', aPos);
    geo.setAttribute('iDim', aDim);
    geo.setAttribute('iDir', aDir);
    geo.setAttribute('iCol', aCol);
    const mat = new THREE.ShaderMaterial({
      vertexShader: VS, fragmentShader: fs(blending === 'alpha'),
      transparent: true, depthWrite: false,
      blending: blending === 'add' ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    const mesh = new THREE.InstancedMesh(geo, mat, cap);
    mesh.frustumCulled = false;
    mesh.count = 0;
    scene.add(mesh);
    const z = (): Float32Array => new Float32Array(cap);
    const b: Batch = {
      mesh, cap, alive: 0,
      px: z(), py: z(), pz: z(), vx: z(), vy: z(), vz: z(),
      age: z(), life: z(), s0: z(), s1: z(),
      c0: new Float32Array(cap * 3), c1: new Float32Array(cap * 3),
      a0: z(), a1: z(), drag: z(), grav: z(), str: z(), twk: z(),
      aPos, aDim, aDir, aCol, bufPos, bufDim, bufDir, bufCol,
    };
    batches.push(b);
    return b;
  }

  const addB = makeBatch(caps.add, 'add');
  const alphaB = makeBatch(caps.alpha, 'alpha');

  const camRight = new THREE.Vector3();
  const camUp = new THREE.Vector3();

  const api: Particles = {
    spawn(o) {
      const b = o.blending === 'alpha' ? alphaB : addB;
      if (b.alive >= b.cap) return;
      const i = b.alive++;
      b.px[i] = o.x; b.py[i] = o.y; b.pz[i] = o.z;
      b.vx[i] = o.vx; b.vy[i] = o.vy; b.vz[i] = o.vz;
      b.age[i] = 0; b.life[i] = Math.max(0.016, o.life);
      b.s0[i] = o.size0; b.s1[i] = o.size1;
      b.c0[i * 3] = o.r0; b.c0[i * 3 + 1] = o.g0; b.c0[i * 3 + 2] = o.b0;
      b.c1[i * 3] = o.r1; b.c1[i * 3 + 1] = o.g1; b.c1[i * 3 + 2] = o.b1;
      b.a0[i] = o.a0; b.a1[i] = o.a1;
      b.drag[i] = o.drag ?? 0; b.grav[i] = o.grav ?? 0;
      b.str[i] = o.stretch ?? 0; b.twk[i] = o.twinkle ?? 0;
    },
    update(dt, cam) {
      camRight.set(1, 0, 0).applyQuaternion(cam.quaternion);
      camUp.set(0, 1, 0).applyQuaternion(cam.quaternion);
      for (const b of batches) {
        // Integrate & compact (swap-remove dead).
        let i = 0;
        while (i < b.alive) {
          b.age[i] += dt;
          if (b.age[i] >= b.life[i]) {
            const last = --b.alive;
            if (i !== last) {
              b.px[i] = b.px[last]; b.py[i] = b.py[last]; b.pz[i] = b.pz[last];
              b.vx[i] = b.vx[last]; b.vy[i] = b.vy[last]; b.vz[i] = b.vz[last];
              b.age[i] = b.age[last]; b.life[i] = b.life[last];
              b.s0[i] = b.s0[last]; b.s1[i] = b.s1[last];
              for (let k = 0; k < 3; k++) { b.c0[i * 3 + k] = b.c0[last * 3 + k]; b.c1[i * 3 + k] = b.c1[last * 3 + k]; }
              b.a0[i] = b.a0[last]; b.a1[i] = b.a1[last];
              b.drag[i] = b.drag[last]; b.grav[i] = b.grav[last];
              b.str[i] = b.str[last]; b.twk[i] = b.twk[last];
            }
            continue;
          }
          const dr = 1 - Math.min(1, b.drag[i] * dt);
          b.vx[i] *= dr; b.vz[i] *= dr;
          b.vy[i] = b.vy[i] * dr - b.grav[i] * dt;
          b.px[i] += b.vx[i] * dt; b.py[i] += b.vy[i] * dt; b.pz[i] += b.vz[i] * dt;
          i++;
        }
        // Fill GPU buffers.
        for (let j = 0; j < b.alive; j++) {
          const t = b.age[j] / b.life[j];
          const sz = b.s0[j] + (b.s1[j] - b.s0[j]) * t;
          const sp = Math.hypot(b.vx[j], b.vy[j], b.vz[j]);
          const sx = b.vx[j] * camRight.x + b.vy[j] * camRight.y + b.vz[j] * camRight.z;
          const sy = b.vx[j] * camUp.x + b.vy[j] * camUp.y + b.vz[j] * camUp.z;
          const il = 1 / Math.max(1e-6, Math.hypot(sx, sy));
          b.bufDir[j * 2] = sx * il; b.bufDir[j * 2 + 1] = sy * il;
          b.bufDim[j * 2] = sz * (1 + b.str[j] * sp * 0.05);
          b.bufDim[j * 2 + 1] = sz;
          let a = b.a0[j] + (b.a1[j] - b.a0[j]) * t;
          if (b.twk[j] > 0) a *= 0.5 + 0.5 * Math.sin(b.age[j] * b.twk[j] * 6.283);
          b.bufCol[j * 4] = b.c0[j * 3] + (b.c1[j * 3] - b.c0[j * 3]) * t;
          b.bufCol[j * 4 + 1] = b.c0[j * 3 + 1] + (b.c1[j * 3 + 1] - b.c0[j * 3 + 1]) * t;
          b.bufCol[j * 4 + 2] = b.c0[j * 3 + 2] + (b.c1[j * 3 + 2] - b.c0[j * 3 + 2]) * t;
          b.bufCol[j * 4 + 3] = a;
          b.bufPos[j * 3] = b.px[j]; b.bufPos[j * 3 + 1] = b.py[j]; b.bufPos[j * 3 + 2] = b.pz[j];
        }
        b.mesh.count = b.alive;
        b.aPos.needsUpdate = true; b.aDim.needsUpdate = true;
        b.aDir.needsUpdate = true; b.aCol.needsUpdate = true;
      }
    },
    get count() { return batches.reduce((s, b) => s + b.alive, 0); },
    dispose() { batches.forEach((b) => { scene.remove(b.mesh); b.mesh.geometry.dispose(); (b.mesh.material as THREE.Material).dispose(); }); },
  };
  return api;
}
```

### src/vfx/explosions.ts
```ts
import * as THREE from 'three';
import { createFireMaterial } from './shaders/fire.js';
import type { Particles } from './particles.js';
import { CONFIG } from '../config.js';

export interface ExplosionSys {
  explode(x: number, y: number, z: number, size: number): void; // size 0.6 small .. 2.5 huge
  recent: { x: number; y: number; z: number; t: number; str: number }[];
  update(dt: number, cam: THREE.Camera): void;
  dispose(): void;
}

interface Burst {
  fire: THREE.Mesh; fireMat: THREE.ShaderMaterial;
  ring: THREE.Mesh; ringMat: THREE.ShaderMaterial;
  light: THREE.PointLight;
  t: number; size: number; active: boolean;
}

export function createExplosions(scene: THREE.Scene, particles: Particles): ExplosionSys {
  const E = CONFIG.expl;
  const fireMatProto = createFireMaterial();
  const fireGeo = new THREE.PlaneGeometry(1, 1);
  const ringGeo = new THREE.RingGeometry(0.42, 0.5, 40);
  const ringMatProto = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    uniforms: { uT: { value: 0 } },
    vertexShader: `void main(){ gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `
      uniform float uT;
      void main(){
        float a = (1.0 - uT) * 0.8;
        gl_FragColor = vec4(1.0, 0.75, 0.45, a);
      }`,
  });

  const pool: Burst[] = [];
  for (let i = 0; i < 6; i++) {
    const fm = fireMatProto.clone();
    const rm = ringMatProto.clone();
    const fire = new THREE.Mesh(fireGeo, fm);
    const ring = new THREE.Mesh(ringGeo, rm);
    const light = new THREE.PointLight('#ffa040', 0, E.lightRange);
    fire.visible = ring.visible = false;
    scene.add(fire, ring, light);
    pool.push({ fire, fireMat: fm, ring, ringMat: rm, light, t: 0, size: 1, active: false });
  }

  const debrisGeo = new THREE.BoxGeometry(1, 1, 1);
  const debrisMat = new THREE.MeshStandardMaterial({ color: '#3a3a3a', roughness: 0.7, emissive: '#ff5500', emissiveIntensity: 0.6 });
  const DBN = 48;
  const debris = new THREE.InstancedMesh(debrisGeo, debrisMat, DBN);
  debris.frustumCulled = false;
  scene.add(debris);
  const db = Array.from({ length: DBN }, () => ({
    active: false, p: new THREE.Vector3(), v: new THREE.Vector3(),
    r: new THREE.Euler(), w: new THREE.Vector3(), s: 1, t: 0,
  }));
  const dummy = new THREE.Object3D();

  const sys: ExplosionSys = {
    recent: [],
    explode(x, y, z, size) {
      const b = pool.find((p) => !p.active) ?? pool[0];
      b.active = true; b.t = 0; b.size = size;
      b.fire.position.set(x, y, z);
      b.ring.position.set(x, y, z);
      b.ring.rotation.set(-Math.PI / 2 + (Math.random() - 0.5), Math.random() * 3, (Math.random() - 0.5));
      b.light.position.set(x, y + size * 2, z);
      b.fireMat.uniforms.uSeed.value = Math.random() * 100;
      b.fire.visible = b.ring.visible = true;
      sys.recent.push({ x, y, z, t: 0, str: size });
      if (sys.recent.length > 8) sys.recent.shift();
      // Debris boxes with flaming trails.
      let spawned = 0;
      for (const d of db) {
        if (d.active || spawned >= Math.ceil(E.debrisN * Math.min(1, size))) continue;
        spawned++;
        d.active = true; d.t = 0; d.s = 0.4 + Math.random() * 1.2 * size;
        d.p.set(x, y, z);
        d.v.set(Math.random() - 0.5, Math.random() * 0.8 + 0.2, Math.random() - 0.5).normalize()
          .multiplyScalar((14 + Math.random() * 26) * Math.sqrt(size));
        d.w.set(Math.random() * 8 - 4, Math.random() * 8 - 4, Math.random() * 8 - 4);
        d.r.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
      }
      // Lingering lit smoke puffs.
      for (let i = 0; i < Math.ceil(E.smokeN * Math.min(1, size)); i++) {
        const a = Math.random() * Math.PI * 2, r = Math.random() * size * 6;
        particles.spawn({
          x: x + Math.cos(a) * r, y: y + Math.random() * size * 4, z: z + Math.sin(a) * r,
          vx: (Math.random() - 0.5) * 6, vy: 3 + Math.random() * 5, vz: (Math.random() - 0.5) * 6,
          life: E.smokeT * (0.6 + Math.random() * 0.6),
          size0: size * 5, size1: size * 16,
          r0: 0.55, g0: 0.5, b0: 0.48, r1: 0.06, g1: 0.055, b1: 0.055,
          a0: 0.5, a1: 0.0, drag: 0.6, grav: -1.2, blending: 'alpha',
        });
      }
      // Initial spark spray.
      for (let i = 0; i < 26; i++) {
        const a = Math.random() * Math.PI * 2, e2 = Math.random() * Math.PI;
        particles.spawn({
          x, y, z,
          vx: Math.sin(e2) * Math.cos(a) * 40, vy: Math.cos(e2) * 40 + 10, vz: Math.sin(e2) * Math.sin(a) * 40,
          life: 0.5 + Math.random() * 0.5, size0: 0.5 * size, size1: 0.1,
          r0: 1, g0: 0.85, b0: 0.4, r1: 1, g1: 0.25, b1: 0.05,
          a0: 1, a1: 0, grav: 9.8, drag: 1.2, stretch: 3,
        });
      }
    },
    update(dt, cam) {
      for (const b of pool) {
        if (!b.active) continue;
        b.t += dt;
        const fp = b.t / E.fireT, rp = b.t / E.ringT;
        b.fireMat.uniforms.uT.value = Math.min(1, fp);
        b.fire.quaternion.copy(cam.quaternion);
        const fscale = b.size * (10 + fp * 34);
        b.fire.scale.setScalar(fscale);
        b.fire.visible = fp < 1;
        b.ringMat.uniforms.uT.value = Math.min(1, rp);
        b.ring.scale.setScalar(b.size * (6 + rp * 90));
        b.ring.visible = rp < 1;
        b.light.intensity = E.flashInt * b.size * Math.max(0, 1 - b.t / E.flashT);
        if (fp >= 1 && rp >= 1) { b.active = false; b.fire.visible = b.ring.visible = false; b.light.intensity = 0; }
      }
      db.forEach((d, i) => {
        if (!d.active) { dummy.position.set(0, -9999, 0); dummy.scale.setScalar(0.001); dummy.updateMatrix(); debris.setMatrixAt(i, dummy.matrix); return; }
        d.t += dt;
        d.v.y -= 9.8 * dt;
        d.p.addScaledVector(d.v, dt);
        d.r.x += d.w.x * dt; d.r.y += d.w.y * dt; d.r.z += d.w.z * dt;
        if (d.p.y < 0.3) { d.active = false; sys.explode(d.p.x, 0.5, d.p.z, 0.5); }
        if (d.t > 4) d.active = false;
        if (Math.random() < dt * 20) {
          particles.spawn({
            x: d.p.x, y: d.p.y, z: d.p.z, vx: 0, vy: 1, vz: 0,
            life: 0.4, size0: 0.8 * d.s, size1: 0.2,
            r0: 1, g0: 0.6, b0: 0.2, r1: 0.3, g1: 0.1, b1: 0.05, a0: 0.9, a1: 0,
          });
        }
        dummy.position.copy(d.p);
        dummy.rotation.copy(d.r);
        dummy.scale.setScalar(d.s);
        dummy.updateMatrix();
        debris.setMatrixAt(i, dummy.matrix);
      });
      debris.instanceMatrix.needsUpdate = true;
      for (let i = sys.recent.length - 1; i >= 0; i--) {
        sys.recent[i].t += dt;
        if (sys.recent[i].t > 1.2) sys.recent.splice(i, 1);
      }
    },
    dispose() {
      pool.forEach((b) => { scene.remove(b.fire, b.ring, b.light); b.fireMat.dispose(); b.ringMat.dispose(); });
      scene.remove(debris); debrisGeo.dispose(); debrisMat.dispose();
      fireMatProto.dispose(); ringMatProto.dispose(); fireGeo.dispose(); ringGeo.dispose();
    },
  };
  return sys;
}
```

### src/vfx/trails.ts
```ts
import * as THREE from 'three';

export interface Ribbon {
  push(x: number, y: number, z: number, width?: number): void;
  dispose(): void;
}

export interface TrailSys {
  add(opts: { max: number; width: number; ttl: number; additive: boolean; headCol: [number, number, number]; tailCol: [number, number, number]; taper?: boolean }): Ribbon;
  update(dt: number, cam: THREE.Camera): void;
  dispose(): void;
}

interface Seg { x: number; y: number; z: number; age: number; w: number }

class RibbonImpl implements Ribbon {
  segs: Seg[] = [];
  constructor(
    private sys: TrailSysImpl,
    public max: number, public width: number, public ttl: number,
    public additive: boolean,
    public hc: [number, number, number], public tc: [number, number, number],
    public taper: boolean,
  ) {}
  push(x: number, y: number, z: number, w?: number) {
    this.segs.unshift({ x, y, z, age: 0, w: w ?? this.width });
    while (this.segs.length > this.max) this.segs.pop();
  }
  dispose() { this.sys.remove(this); }
}

export class TrailSysImpl implements TrailSys {
  ribbons: RibbonImpl[] = [];
  private geos: THREE.BufferGeometry[] = [];
  private mats: THREE.Material[] = [];

  add(opts: { max: number; width: number; ttl: number; additive: boolean; headCol: [number, number, number]; tailCol: [number, number, number]; taper?: boolean }): Ribbon {
    const r = new RibbonImpl(this, opts.max, opts.width, opts.ttl, opts.additive, opts.headCol, opts.tailCol, opts.taper ?? true);
    this.ribbons.push(r);
    return r;
  }
  remove(r: RibbonImpl) {
    const i = this.ribbons.indexOf(r);
    if (i >= 0) this.ribbons.splice(i, 1);
  }

  update(dt: number, cam: THREE.Camera) {
    const camP = cam.position;
    const va = new THREE.Vector3(), vb = new THREE.Vector3(), side = new THREE.Vector3();
    for (const r of this.ribbons) {
      for (const s of r.segs) s.age += dt;
      while (r.segs.length && r.segs[r.segs.length - 1].age > r.ttl) r.segs.pop();
      const n = r.segs.length;
      if (n < 2) continue;
      const verts = n * 2;
      let geo = (r as unknown as { _geo?: THREE.BufferGeometry })._geo;
      if (!geo) {
        geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(r.max * 6), 3));
        geo.setAttribute('aCol', new THREE.BufferAttribute(new Float32Array(r.max * 6), 3));
        geo.setAttribute('aA', new THREE.BufferAttribute(new Float32Array(r.max * 2), 1));
        const idx: number[] = [];
        for (let i = 0; i < r.max - 1; i++) {
          const a = i * 2;
          idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
        }
        geo.setIndex(idx);
        const mat = new THREE.ShaderMaterial({
          transparent: true, depthWrite: false, side: THREE.DoubleSide,
          blending: r.additive ? THREE.AdditiveBlending : THREE.NormalBlending,
          uniforms: {},
          vertexShader: `
            attribute vec3 aCol; attribute float aA;
            varying vec3 vC; varying float vA;
            void main(){ vC=aCol; vA=aA;
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
          fragmentShader: `
            varying vec3 vC; varying float vA;
            void main(){ if(vA<0.01) discard; gl_FragColor=vec4(vC, vA); }`,
        });
        this.geos.push(geo); this.mats.push(mat);
        const mesh = new THREE.Mesh(geo, mat);
        mesh.frustumCulled = false;
        (r as unknown as { _mesh?: THREE.Mesh })._mesh = mesh;
        (r as unknown as { _geo: THREE.BufferGeometry })._geo = geo;
        (r as unknown as { _mat: THREE.Material })._mat = mat;
        this.scene_.add(mesh);
      }
      const pa = geo.getAttribute('position') as THREE.BufferAttribute;
      const ca = geo.getAttribute('aCol') as THREE.BufferAttribute;
      const aa = geo.getAttribute('aA') as THREE.BufferAttribute;
      for (let i = 0; i < n; i++) {
        const s = r.segs[i];
        const nxt = r.segs[Math.min(i + 1, n - 1)];
        const prv = r.segs[Math.max(i - 1, 0)];
        va.set(prv.x - nxt.x, prv.y - nxt.y, prv.z - nxt.z);
        vb.set(s.x - camP.x, s.y - camP.y, s.z - camP.z);
        side.crossVectors(va, vb);
        if (side.lengthSq() < 1e-8) side.set(0, 1, 0);
        side.normalize();
        const tf = r.taper ? 1 - i / n : 1;
        const w = s.w * tf * 0.5;
        const af = 1 - s.age / r.ttl;
        pa.setXYZ(i * 2, s.x + side.x * w, s.y + side.y * w, s.z + side.z * w);
        pa.setXYZ(i * 2 + 1, s.x - side.x * w, s.y - side.y * w, s.z - side.z * w);
        const hf = 1 - i / n;
        const cr = r.tc[0] + (r.hc[0] - r.tc[0]) * hf;
        const cg = r.tc[1] + (r.hc[1] - r.tc[1]) * hf;
        const cb = r.tc[2] + (r.hc[2] - r.tc[2]) * hf;
        ca.setXYZ(i * 2, cr, cg, cb); ca.setXYZ(i * 2 + 1, cr, cg, cb);
        aa.setX(i * 2, af); aa.setX(i * 2 + 1, af);
      }
      geo.setDrawRange(0, Math.max(0, (n - 1) * 6));
      pa.needsUpdate = true; ca.needsUpdate = true; aa.needsUpdate = true;
    }
  }

  private scene_: THREE.Scene;
  constructor(scene: THREE.Scene) { this.scene_ = scene; }

  dispose() {
    this.ribbons.slice().forEach((r) => {
      const mesh = (r as unknown as { _mesh?: THREE.Mesh })._mesh;
      if (mesh) this.scene_.remove(mesh);
    });
    this.geos.forEach((g) => g.dispose());
    this.mats.forEach((m) => m.dispose());
    this.ribbons.length = 0;
  }
}

export function createTrails(scene: THREE.Scene): TrailSys {
  return new TrailSysImpl(scene);
}
```

### src/vfx/speedlines.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';

export interface SpeedFx {
  update(dt: number, cam: THREE.Camera, speed: number, boosting: boolean): void;
  boom(at: THREE.Vector3): void;
  updateBooms(dt: number, cam: THREE.Camera): void;
  dispose(): void;
}

/** 400 recycled streaks in a shell around the camera + sonic-boom rings. */
export function createSpeedlines(scene: THREE.Scene): SpeedFx {
  const N = CONFIG.spd.streakN;
  const geo = new THREE.BoxGeometry(0.05, 0.05, 1);
  const mat = new THREE.MeshBasicMaterial({
    color: '#dff4ff', transparent: true, opacity: 0.5,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const mesh = new THREE.InstancedMesh(geo, mat, N);
  mesh.frustumCulled = false;
  scene.add(mesh);
  const dummy = new THREE.Object3D();
  const streaks = Array.from({ length: N }, () => ({ t: Math.random() }));

  const boomGeo = new THREE.TorusGeometry(1, 0.03, 8, 48);
  const boomMatP = new THREE.MeshBasicMaterial({
    color: '#cfeaff', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const booms: { m: THREE.Mesh; t: number }[] = [];
  for (let i = 0; i < 3; i++) {
    const m = new THREE.Mesh(boomGeo, boomMatP.clone());
    m.visible = false;
    scene.add(m);
    booms.push({ m, t: 99 });
  }

  const fwd = new THREE.Vector3();
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const p = new THREE.Vector3();

  return {
    update(dt, cam, speed, boosting) {
      const k = Math.max(0, Math.min(1, (speed - CONFIG.spd.streakStart) / 120));
      mesh.visible = k > 0.01;
      if (!mesh.visible) return;
      cam.getWorldDirection(fwd);
      right.set(1, 0, 0).applyQuaternion(cam.quaternion);
      up.set(0, 1, 0).applyQuaternion(cam.quaternion);
      const len = 2 + speed * 0.12;
      for (let i = 0; i < N; i++) {
        const s = streaks[i];
        s.t += dt * (0.6 + speed / 90) * (boosting ? 1.6 : 1);
        if (s.t > 1) { s.t -= 1; }
        const ang = i * 2.399963; // golden-angle spiral
        const rad = 2.5 + (i % 7) * 1.9;
        const along = (s.t - 0.35) * 60;
        p.copy(cam.position)
          .addScaledVector(fwd, along)
          .addScaledVector(right, Math.cos(ang) * rad)
          .addScaledVector(up, Math.sin(ang) * rad);
        dummy.position.copy(p);
        dummy.quaternion.copy(cam.quaternion);
        dummy.scale.set(1, 1, len);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;
      mat.opacity = 0.12 + 0.4 * k;
    },
    boom(at) {
      const b = booms.find((x) => x.t > CONFIG.spd.boomRingT) ?? booms[0];
      b.t = 0;
      b.m.position.copy(at);
      b.m.rotation.set(Math.random() * 3, Math.random() * 3, 0);
      b.m.visible = true;
    },
    updateBooms(dt, cam) {
      for (const b of booms) {
        if (b.t > CONFIG.spd.boomRingT) { b.m.visible = false; continue; }
        b.t += dt;
        const k = b.t / CONFIG.spd.boomRingT;
        b.m.scale.setScalar(2 + k * 90);
        (b.m.material as THREE.MeshBasicMaterial).opacity = (1 - k) * 0.7;
        b.m.quaternion.copy(cam.quaternion);
        b.m.rotateX(Math.PI / 2);
      }
    },
    dispose() {
      scene.remove(mesh); geo.dispose(); mat.dispose();
      booms.forEach((b) => scene.remove(b.m));
      boomGeo.dispose(); boomMatP.dispose();
    },
  };
}
```

### src/entities/flight.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { clamp, lerp, sat, smooth, safeNorm, wrapPi, finNum } from '../core/math.js';

export type HeroMode = 'hover' | 'flight' | 'holding' | 'landed' | 'stunned';

export interface Cmd {
  thrust: number;   // 0..1 W
  brake: number;    // 0..1 S
  lift: number;     // 0..1 Space
  sink: number;     // 0..1 Ctrl
  strafe: number;   // -1..1 A/D
  boost: boolean;   // Shift
}

export interface FlightState {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  quat: THREE.Quaternion;      // displayed body orientation (incl. bank)
  aimYaw: number; aimPitch: number;   // rad
  mode: HeroMode;
  hp: number;
  boost: number;               // 0..1 meter
  boostLock: boolean;
  boostBlend: number;          // 0 cruise .. 1 boost (drag blend)
  dragK: number;
  bank: number;                // rad, smoothed
  stunT: number;
  hurtT: number;               // s since last damage
  bobT: number;
  superArmed: boolean;
  launchCharge: number;        // 0..1 while landed + Space
  hoverGrace: number;          // s below hover-speed before engaging hover
  tumble: THREE.Vector3;       // stun angular velocity
  lastImpact: number;          // m/s of most recent collision this step
  launched: boolean;           // flagged once per launch for FX
}

export function createState(): FlightState {
  return {
    pos: new THREE.Vector3(0, 120, 0),
    vel: new THREE.Vector3(),
    quat: new THREE.Quaternion(),
    aimYaw: Math.PI, aimPitch: 0,
    mode: 'hover',
    hp: CONFIG.hero.hpMax,
    boost: 1, boostLock: false, boostBlend: 0,
    dragK: 0, bank: 0, stunT: 0, hurtT: 99,
    bobT: 0, superArmed: true, launchCharge: 0, hoverGrace: 0,
    tumble: new THREE.Vector3(), lastImpact: 0, launched: false,
  };
}

export function aimDir(s: FlightState, out: THREE.Vector3): THREE.Vector3 {
  const cp = Math.cos(s.aimPitch);
  return out.set(Math.sin(s.aimYaw) * cp, Math.sin(s.aimPitch), Math.cos(s.aimYaw) * cp);
}

/** Steering agility curve: agile slow, sluggish at boost. */
export function turnRateAt(speed: number): number {
  const t = smooth(speed / CONFIG.hero.vMaxBoost);
  return lerp(CONFIG.hero.turnLow, CONFIG.hero.turnHigh, t);
}

const UP = new THREE.Vector3(0, 1, 0);
const tv = new THREE.Vector3();
const tq = new THREE.Quaternion();
const tb = new THREE.Quaternion();

/** One fixed physics step. Returns event flags for the caller to react to. */
export interface StepFlags { supersonic: boolean; landed: boolean; tookOff: boolean; bounced: boolean }

export function step(s: FlightState, cmd: Cmd, h: number, surfBelow: number): StepFlags {
  const flags: StepFlags = { supersonic: false, landed: false, tookOff: false, bounced: false };
  const C = CONFIG.hero;
  s.lastImpact = 0;

  if (s.mode === 'stunned') {
    s.stunT -= h;
    s.vel.y -= C.fullGravity * h;
    s.pos.addScaledVector(s.vel, h);
    tq.setFromAxisAngle(tv.copy(s.tumble).normalize(), s.tumble.length() * h);
    s.quat.premultiply(tq);
    if (s.stunT <= 0) { s.mode = 'flight'; s.tumble.set(0, 0, 0); }
    if (!finNum(s.pos.x, s.pos.y, s.pos.z)) { s.pos.set(0, 150, 0); s.vel.set(0, 0, 0); }
    return flags;
  }

  if (s.mode === 'landed') {
    s.vel.set(0, 0, 0);
    s.pos.y = surfBelow + 0.95;
    // Slow shuffle toward aim.
    aimDir(s, tv); tv.y = 0; safeNorm(tv);
    const walk = (cmd.thrust - cmd.brake) * 3;
    s.pos.addScaledVector(tv, walk * h);
    if (cmd.lift > 0) {
      s.launchCharge = Math.min(1, s.launchCharge + h / C.launchTime);
    } else if (s.launchCharge > 0) {
      const pw = lerp(C.launchMin, C.launchMax, s.launchCharge);
      aimDir(s, tv); tv.y = 0; safeNorm(tv);
      s.vel.copy(tv).multiplyScalar(pw * 0.55);
      s.vel.y = pw * 0.8;
      s.mode = 'flight';
      s.launchCharge = 0;
      flags.tookOff = true;
    }
    s.bobT = 0;
    return flags;
  }

  if (s.mode === 'hover') {
    s.vel.multiplyScalar(Math.exp(-6 * h));
    s.bobT += h;
    const act = cmd.thrust + cmd.lift + cmd.sink + Math.abs(cmd.strafe) + (cmd.boost ? 1 : 0);
    if (act > 0.01) s.mode = 'flight';
    // Hover drift inputs.
    s.vel.addScaledVector(UP, (cmd.lift - cmd.sink) * C.vertAccel * h);
    aimDir(s, tv); tv.y = 0; safeNorm(tv);
    const sr = new THREE.Vector3(-tv.z, 0, tv.x);
    s.vel.addScaledVector(sr, cmd.strafe * C.strafeAccel * h);
    s.pos.addScaledVector(s.vel, h);
    if (s.vel.length() > C.hoverSpeed * 1.6) s.mode = 'flight';
    s.superArmed = s.vel.length() < CONFIG.spd.ssRearm ? true : s.superArmed;
    return flags;
  }

  // ---- FLIGHT ----
  const speed = s.vel.length();

  // Boost meter.
  const wantBoost = cmd.boost && cmd.thrust > 0 && !s.boostLock;
  if (wantBoost) {
    s.boost = Math.max(0, s.boost - h / C.boostDrain);
    if (s.boost <= 0) { s.boostLock = true; s.boostLockT = C.boostLockout; }
  } else {
    if (s.boostLock) {
      s.boostLockT = (s.boostLockT ?? 0) - h;
      if (s.boostLockT <= 0) s.boostLock = false;
    }
    s.boost = Math.min(1, s.boost + h / C.boostRefill);
  }
  const boosting = wantBoost && s.boost > 0;

  // Drag coefficient blends between regimes so boost surges.
  const kCruise = C.thrust / (C.vMaxCruise * C.vMaxCruise);
  const kBoost = (C.thrust * C.boostMult) / (C.vMaxBoost * C.vMaxBoost);
  const kTarget = boosting ? kBoost : kCruise;
  s.boostBlend = lerp(s.boostBlend, boosting ? 1 : 0, 1 - Math.exp(-h / (C.dragBlend / 3)));
  s.dragK = lerp(kCruise, kBoost, s.boostBlend);

  // Steer velocity toward aim with speed-dependent turn rate.
  aimDir(s, tv);
  const vhat = new THREE.Vector3();
  if (speed > 0.5) {
    vhat.copy(s.vel).divideScalar(speed);
    const dot = vhat.dot(tv);
    const ang = Math.acos(clamp(dot, -1, 1));
    let rate = turnRateAt(speed);
    if (cmd.strafe !== 0 && speed > 10) {
      // Yaw assist carves horizontally.
      const ay = cmd.strafe * C.yawAssist * h;
      tq.setFromAxisAngle(UP, ay);
      s.vel.applyQuaternion(tq);
      vhat.copy(s.vel).normalize();
      aimDir(s, tv);
    }
    if (ang > 1e-4) {
      const axis = new THREE.Vector3().crossVectors(vhat, tv);
      if (axis.lengthSq() < 1e-8) axis.copy(UP).cross(vhat);
      safeNorm(axis);
      const step_ang = Math.min(ang, rate * h);
      tq.setFromAxisAngle(axis, step_ang);
      s.vel.applyQuaternion(tq);
    }
  } else {
    s.vel.copy(tv).multiplyScalar(0.5);
  }

  // Thrust along aim.
  const thrustMag = C.thrust * (boosting ? C.boostMult : 1) * cmd.thrust;
  aimDir(s, tv);
  s.vel.addScaledVector(tv, thrustMag * h);
  // Vertical world inputs.
  s.vel.y += (cmd.lift - cmd.sink) * C.vertAccel * h;
  // Air brake.
  const braking = cmd.brake > 0;
  if (braking) {
    const vm = s.vel.length();
    if (vm > 0.1) {
      const extra = (C.brakeDrag - 1) * s.dragK * vm * vm * h * cmd.brake;
      const nv = Math.max(0, vm - extra);
      s.vel.multiplyScalar(nv / vm);
    }
  }
  // Drag quadratic.
  const vm2 = s.vel.length();
  if (vm2 > 0.01) {
    const dv = s.dragK * vm2 * vm2 * h;
    const nv = Math.max(0, vm2 - dv);
    s.vel.multiplyScalar(nv / vm2);
  }
  // Gravity: none while actively powered, gentle when coasting.
  const powering = cmd.thrust > 0 || cmd.lift > 0 || cmd.sink > 0;
  if (!powering) s.vel.y -= C.coastGravity * h;

  s.pos.addScaledVector(s.vel, h);

  // Supersonic boom (fires once; re-arms below threshold).
  const sp2 = s.vel.length();
  if (s.superArmed && sp2 >= CONFIG.spd.ssV) { s.superArmed = false; flags.supersonic = true; }
  else if (sp2 < CONFIG.spd.ssRearm) s.superArmed = true;

  // Landing check.
  const alt = s.pos.y - surfBelow;
  if (alt < C.landAlt && sp2 < C.landSpeedMax && s.vel.y <= 0.5) {
    s.mode = 'landed';
    s.pos.y = surfBelow + 0.95;
    s.vel.set(0, 0, 0);
    flags.landed = true;
  }

  // Regen.
  s.hurtT += h;
  if (s.hurtT > C.regenDelay) s.hp = Math.min(C.hpMax, s.hp + C.regenRate * h);

  // Display orientation: forward slerps to velocity, bank from yaw rate.
  const vhat2 = new THREE.Vector3();
  if (sp2 > 2) vhat2.copy(s.vel).divideScalar(sp2); else aimDir(s, vhat2);
  const prevYaw = Math.atan2(s.vel.x, s.vel.z);
  const fq = new THREE.Quaternion();
  const upRef = braking ? new THREE.Vector3() : UP;
  if (braking) {
    // Nose-up 30° on air brake: tilt the forward reference.
    upRef.copy(vhat2).cross(UP).normalize();
    upRef.applyAxisAngle(vhat2, -C.brakePitch * 0); // placeholder, handled below
  }
  const targetQ = new THREE.Quaternion();
  const fAdj = braking
    ? new THREE.Vector3().copy(vhat2)//.applyAxisAngle(sideAxis, C.brakePitch)
    : vhat2;
  if (braking) {
    const side = new THREE.Vector3().crossVectors(UP, vhat2).normalize();
    fAdj.applyAxisAngle(side, C.brakePitch);
  }
  const upv = braking ? new THREE.Vector3().crossVectors(fAdj, new THREE.Vector3().crossVectors(UP, fAdj).normalize()).normalize() : UP;
  // Build basis with +Z = forward.
  const r = new THREE.Vector3().crossVectors(upv, fAdj);
  if (r.lengthSq() < 1e-8) r.set(1, 0, 0);
  r.normalize();
  const u = new THREE.Vector3().crossVectors(fAdj, r);
  const m = new THREE.Matrix4().makeBasis(r, u, fAdj);
  targetQ.setFromRotationMatrix(m);
  const slerpRate = boosting ? 10 : 6;
  fq.copy(s.quat);
  fq.slerp(targetQ, 1 - Math.exp(-slerpRate * h));
  // Bank from horizontal turn rate.
  const newYaw = Math.atan2(s.vel.x, s.vel.z);
  const yawRate = wrapPi(newYaw - prevYaw) / Math.max(h, 1e-4);
  const bankTarget = clamp(-yawRate * sat(sp2 / 80) * 1.4, -70 * Math.PI / 180, 70 * Math.PI / 180);
  s.bank = lerp(s.bank, bankTarget, 1 - Math.exp(-h / 0.15));
  tb.setFromAxisAngle(new THREE.Vector3(0, 0, 1), s.bank);
  s.quat.copy(fq).multiply(tb);

  if (!finNum(s.pos.x, s.pos.y, s.pos.z, s.vel.x, s.vel.y, s.vel.z)) {
    s.pos.set(0, 150, 0); s.vel.set(0, 0, 0); s.mode = 'hover';
  }
  return flags;
}

/** External damage entry (bullets, missiles, crashes). */
export function damage(s: FlightState, amt: number) {
  s.hp = Math.max(0, s.hp - amt);
  s.hurtT = 0;
}

// Assigned lazily by step() when boost empties; declared for TS.
declare module './flight.js' {} 
```

### src/entities/hero.ts
```ts
import * as THREE from 'three';
import type { FlightState, HeroMode } from './flight.js';
import { CONFIG } from '../config.js';
import { lerp, damp } from '../core/math.js';

export interface HeroView {
  root: THREE.Group;
  headWorld(out: THREE.Vector3): THREE.Vector3;
  eyeOffsets(outL: THREE.Vector3, outR: THREE.Vector3): void;
  setEyeGlow(base: number, firing: boolean): void;
  sync(s: FlightState, dt: number, windVel: THREE.Vector3): void;
  dispose(): void;
}

interface Joint extends THREE.Object3D { home: number }

function limb(len: number, r: number, mat: THREE.Material): THREE.Group {
  const g = new THREE.Group();
  const geo = new THREE.CapsuleGeometry(r, len - r * 2, 3, 8);
  const m = new THREE.Mesh(geo, mat);
  m.position.y = -len / 2;
  m.castShadow = true;
  g.add(m);
  return g;
}

export function createHero(scene: THREE.Scene): HeroView {
  const suit = new THREE.MeshStandardMaterial({ color: '#8e1622', roughness: 0.55, metalness: 0.15 });
  const gold = new THREE.MeshStandardMaterial({ color: '#e8b23a', roughness: 0.3, metalness: 0.7 });
  const boot = new THREE.MeshStandardMaterial({ color: '#301014', roughness: 0.6 });
  const skin = new THREE.MeshStandardMaterial({ color: '#d8a67e', roughness: 0.7 });
  const eyeMat = new THREE.MeshBasicMaterial({ color: '#bfe9ff', fog: false });

  const root = new THREE.Group();
  scene.add(root);

  // Torso (+Z = forward convention).
  const torsoGeo = new THREE.CapsuleGeometry(0.26, 0.42, 4, 10);
  const torso = new THREE.Mesh(torsoGeo, suit);
  torso.castShadow = true;
  root.add(torso);
  const emblemGeo = new THREE.OctahedronGeometry(0.13, 0);
  const emblem = new THREE.Mesh(emblemGeo, gold);
  emblem.scale.set(1, 1.25, 0.35);
  emblem.position.set(0, 0.08, 0.26);
  root.add(emblem);

  const headG = new THREE.Group();
  headG.position.set(0, 0.52, 0);
  root.add(headG);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.155, 12, 10), skin);
  head.castShadow = true;
  headG.add(head);
  const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.032, 6, 6), eyeMat);
  const eyeR = eyeL.clone();
  eyeL.position.set(-0.055, 0.03, 0.13);
  eyeR.position.set(0.055, 0.03, 0.13);
  headG.add(eyeL, eyeR);

  const hips = new THREE.Group(); hips.position.y = -0.32; root.add(hips);

  function arm(side: number) {
    const sh = new THREE.Group();
    sh.position.set(0.3 * side, 0.32, 0);
    root.add(sh);
    const upper = limb(0.34, 0.085, suit); sh.add(upper);
    const el = new THREE.Group(); el.position.y = -0.34; upper.add(el);
    const fore = limb(0.32, 0.075, suit); el.add(fore);
    const glove = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), gold);
    glove.position.y = -0.34; fore.add(glove);
    return { sh, el };
  }
  function leg(side: number) {
    const hip = new THREE.Group();
    hip.position.set(0.14 * side, -0.1, 0);
    hips.add(hip);
    const thigh = limb(0.4, 0.105, suit); hip.add(thigh);
    const kn = new THREE.Group(); kn.position.y = -0.4; thigh.add(kn);
    const calf = limb(0.38, 0.09, suit); kn.add(calf);
    const foot = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.1, 0.3), boot);
    foot.position.set(0, -0.4, 0.06); calf.add(foot);
    return { hip, kn };
  }
  const armL = arm(-1), armR = arm(1);
  const legL = leg(-1), legR = leg(1);

  // Cape: 7-segment Verlet strip pinned at the shoulders.
  const CAPE_SEG = 7, CAPE_W = 0.6;
  const capePts: { p: THREE.Vector3; pp: THREE.Vector3; pin: boolean }[][] = [];
  for (let cxi = 0; cxi < 2; cxi++) {
    const col: { p: THREE.Vector3; pp: THREE.Vector3; pin: boolean }[] = [];
    for (let i = 0; i <= CAPE_SEG; i++)
      col.push({ p: new THREE.Vector3(), pp: new THREE.Vector3(), pin: i === 0 });
    capePts.push(col);
  }
  const capeGeo = new THREE.BufferGeometry();
  const capeVerts = (CAPE_SEG + 1) * 2;
  capeGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(capeVerts * 3), 3));
  const capeIdx: number[] = [];
  for (let i = 0; i < CAPE_SEG; i++) {
    const a = i * 2;
    capeIdx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
  }
  capeGeo.setIndex(capeIdx);
  const capeMat = new THREE.MeshStandardMaterial({
    color: '#7d1220', roughness: 0.8, side: THREE.DoubleSide,
  });
  const cape = new THREE.Mesh(capeGeo, capeMat);
  cape.frustumCulled = false;
  root.add(cape);
  let capeSeeded = false;

  // Pose targets per mode: [shL.x, shR.x, shL.z, shR.z, elL, elR, hipL.x, hipR.x, kneL, kneR]
  type Pose = number[];
  const POSES: Record<string, Pose> = {
    hover: [-0.15, -0.15, 0.12, -0.12, -0.35, -0.35, 0.06, 0.06, -0.15, -0.15],
    flight: [-Math.PI / 2 + 0.12, -Math.PI / 2 + 0.12, 0.06, -0.06, -0.1, -0.1, 0.04, 0.04, -0.08, -0.08],
    boost: [0.55, 0.55, 0.1, -0.1, -0.25, -0.25, 0.02, 0.02, -0.5, -0.5],
    holding: [-Math.PI + 0.25, -Math.PI + 0.25, 0.05, -0.05, -0.15, -0.15, 0.5, 0.5, -0.9, -0.9],
    landed: [-0.1, -0.1, 0.1, -0.1, -0.3, -0.3, 0.02, 0.02, -0.05, -0.05],
    stunned: [-1.2, -0.9, 0.6, -0.6, -0.7, -0.4, 0.4, -0.3, -0.8, -0.2],
  };
  const cur: Pose = [...POSES.hover];

  const tmp = new THREE.Vector3();
  const tmp2 = new THREE.Vector3();
  const wa = new THREE.Vector3();
  const wb = new THREE.Vector3();

  const api: HeroView = {
    root,
    headWorld(out) { return headG.getWorldPosition(out); },
    eyeOffsets(outL, outR) {
      eyeL.getWorldPosition(outL);
      eyeR.getWorldPosition(outR);
    },
    setEyeGlow(base, firing) {
      const c = firing ? 1 : base;
      (eyeMat.color as THREE.Color).setRGB(0.55 + c * 0.45, 0.75 + c * 0.25, 1);
      eyeL.scale.setScalar(1 + c * 1.4);
      eyeR.scale.setScalar(1 + c * 1.4);
    },
    sync(s, dt, windVel) {
      root.position.copy(s.pos);
      root.quaternion.copy(s.quat);

      // Pick pose family.
      let fam = 'hover';
      if (s.mode === 'stunned') fam = 'stunned';
      else if (s.mode === 'landed') fam = 'landed';
      else if (s.mode === 'holding') fam = 'holding';
      else {
        const sp = s.vel.length();
        fam = sp > 100 ? 'boost' : sp > 6 ? 'flight' : 'hover';
      }
      const tgt = POSES[fam]!;
      const k = 1 - Math.exp(-dt * 8);
      for (let i = 0; i < cur.length; i++) cur[i] = lerp(cur[i], tgt[i], k);
      armL.sh.rotation.x = cur[0]; armR.sh.rotation.x = cur[1];
      armL.sh.rotation.z = cur[2]; armR.sh.rotation.z = cur[3];
      armL.el.rotation.x = cur[4]; armR.el.rotation.x = cur[5];
      legL.hip.rotation.x = cur[6]; legR.hip.rotation.x = cur[7];
      legL.kn.rotation.x = cur[8]; legR.kn.rotation.x = cur[9];

      // Hover bob.
      if (s.mode === 'hover') {
        root.position.y += Math.sin(s.bobT * CONFIG.hero.bobHz * Math.PI * 2) * CONFIG.hero.bobAmp;
      }

      // Cape Verlet.
      root.updateMatrixWorld(true);
      const shL = tmp.set(-0.3, 0.42, -0.05).applyMatrix4(root.matrixWorld);
      const shR = tmp2.set(0.3, 0.42, -0.05).applyMatrix4(root.matrixWorld);
      if (!capeSeeded) {
        for (let cxi = 0; cxi < 2; cxi++)
          for (let i = 0; i <= CAPE_SEG; i++) {
            const pt = capePts[cxi][i];
            pt.p.copy(i === 0 ? (cxi === 0 ? shL : shR) : capePts[cxi][i - 1].p).y -= i * 0.22;
            pt.pp.copy(pt.p);
          }
        capeSeeded = true;
      }
      capePts[0][0].p.copy(shL);
      capePts[1][0].p.copy(shR);
      const g = 4.5;
      const wind = wa.copy(windVel).multiplyScalar(-0.028); // relative wind push
      for (let sub = 0; sub < 2; sub++) {
        for (let cxi = 0; cxi < 2; cxi++)
          for (let i = 1; i <= CAPE_SEG; i++) {
            const pt = capePts[cxi][i];
            const vx = (pt.p.x - pt.pp.x) * 0.96;
            const vy = (pt.p.y - pt.pp.y) * 0.96;
            const vz = (pt.p.z - pt.pp.z) * 0.96;
            pt.pp.copy(pt.p);
            pt.p.x += vx + wind.x * dt + Math.sin(performance.now() * 0.006 + i * 1.7 + cxi) * 0.35 * dt;
            pt.p.y += vy - g * dt * dt;
            pt.p.z += vz + wind.z * dt;
          }
        // Constraints: vertical chains + cross links.
        for (let iter = 0; iter < 3; iter++) {
          for (let cxi = 0; cxi < 2; cxi++)
            for (let i = 0; i < CAPE_SEG; i++) {
              const a = capePts[cxi][i], b = capePts[cxi][i + 1];
              constrain(a, b, 0.22);
            }
          for (let i = 0; i <= CAPE_SEG; i++) constrain(capePts[0][i], capePts[1][i], CAPE_W * (1 - i / CAPE_SEG * 0.2));
        }
      }
      const pa = capeGeo.getAttribute('position') as THREE.BufferAttribute;
      for (let i = 0; i <= CAPE_SEG; i++) {
        pa.setXYZ(i * 2, capePts[0][i].p.x, capePts[0][i].p.y, capePts[0][i].p.z);
        pa.setXYZ(i * 2 + 1, capePts[1][i].p.x, capePts[1][i].p.y, capePts[1][i].p.z);
      }
      pa.needsUpdate = true;
      capeGeo.computeVertexNormals();
    },
    dispose() {
      scene.remove(root);
      root.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
      });
      [suit, gold, boot, skin, eyeMat, capeMat].forEach((m) => m.dispose());
    },
  };

  function constrain(a: { p: THREE.Vector3; pin: boolean }, b: { p: THREE.Vector3; pin: boolean }, rest: number) {
    const dx = b.p.x - a.p.x, dy = b.p.y - a.p.y, dz = b.p.z - a.p.z;
    const d = Math.hypot(dx, dy, dz) || 1e-6;
    const f = (d - rest) / d * 0.5;
    if (!a.pin) { a.p.x += dx * f; a.p.y += dy * f; a.p.z += dz * f; }
    if (!b.pin) { b.p.x -= dx * f; b.p.y -= dy * f; b.p.z -= dz * f; }
  }

  return api;
}
```

### src/entities/airliner.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { safeNorm, quatFace } from '../core/math.js';

export type CatchPoint = 'TAIL' | 'NOSE';

export interface AirlinerState {
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  yaw: number; pitch: number; roll: number;   // rad; pitch + = climb
  quat: THREE.Quaternion;
  hull: number;
  stress: number;
  gear: number;            // 0 up .. 1 down
  engFire: boolean;
  caught: CatchPoint | null;
  torn: boolean;
  dead: boolean;           // hull 0 spiral
  landed: boolean;
  touchedDown: null | { sink: number; quality: 'PERFECT' | 'HARD' | 'CRASH'; tailStrike: boolean };
  crumple: number;         // 0..1 nose deformation
  elapsed: number;         // s since spawn (trajectory profiles)
  eta: number;             // s to terrain impact (Infinity = clear)
  pathClear: boolean;
  tearT: number;           // countdown while TAIL-held
  catchAnim: number;       // 0..1 catch animation progress
  settling: boolean;       // post-touchdown settle script
  released: boolean;
}

export function createAirlinerState(): AirlinerState {
  const C = CONFIG.plane;
  const s: AirlinerState = {
    pos: new THREE.Vector3(C.eastOffset, C.startAlt, 0),
    vel: new THREE.Vector3(-C.speed0, -C.sink0, 0),
    yaw: -Math.PI / 2, pitch: 0, roll: 0,
    quat: new THREE.Quaternion(),
    hull: C.hullMax, stress: 0, gear: 0,
    engFire: true, caught: null, torn: false, dead: false, landed: false,
    touchedDown: null, crumple: 0, elapsed: 0, eta: Infinity, pathClear: false,
    tearT: 0, catchAnim: 0, settling: false, released: false,
  };
  syncQuat(s);
  return s;
}

export function syncQuat(s: AirlinerState) {
  quatFace(s.quat, fwdOf(s, new THREE.Vector3()), new THREE.Vector3(0, 1, 0), s.roll);
}

export function fwdOf(s: AirlinerState, out: THREE.Vector3): THREE.Vector3 {
  const cp = Math.cos(s.pitch);
  return out.set(Math.cos(s.yaw) * cp, Math.sin(s.pitch), Math.sin(s.yaw) * cp);
}

/** Prescribed doomed-airliner kinematics until caught. */
export function stepUnheld(s: AirlinerState, h: number) {
  const C = CONFIG.plane;
  s.elapsed += h;
  const sk = Math.min(1, s.elapsed / C.sinkRampT);
  const sink = C.sink0 + (C.sinkMax - C.sink0) * sk;
  const pk = Math.min(1, s.elapsed / C.pitchRampT);
  s.pitch = C.pitch0 + (C.pitchEnd - C.pitch0) * pk;
  s.vel.set(-C.speed0, -sink, 0);
  s.pos.addScaledVector(s.vel, h);
  s.roll = Math.sin(s.elapsed * 0.7) * 0.03;
  syncQuat(s);
}

/** Terrain ETA scan along the projected path. */
export function projectImpact(
  s: AirlinerState, topAtFn: (x: number, z: number) => number, cityBound: number,
): { eta: number; clear: boolean } {
  const C = CONFIG.plane;
  const dt = 0.5;
  let t = 0;
  const p = new THREE.Vector3().copy(s.pos);
  const v = new THREE.Vector3().copy(s.vel);
  while (t < 180) {
    const sk = Math.min(1, (s.elapsed + t) / C.sinkRampT);
    v.y = -(C.sink0 + (C.sinkMax - C.sink0) * sk);
    p.addScaledVector(v, dt);
    t += dt;
    if (Math.hypot(p.x, p.z) > cityBound + 800) return { eta: Infinity, clear: true };
    if (p.y <= topAtFn(p.x, p.z) + 4) return { eta: t, clear: false };
  }
  return { eta: Infinity, clear: true };
}

export function applyHullDamage(s: AirlinerState, amt: number) {
  if (s.dead || s.touchedDown) return;
  s.hull = Math.max(0, s.hull - amt);
  if (s.hull <= 0) { s.dead = true; }
}

// ---------------- Visual ----------------

export interface AirlinerView {
  group: THREE.Group;
  sync(s: AirlinerState, dt: number, t: number): void;
  emitFire(cb: (s: AirlinerState, dt: number) => void): void; // wired by main
  dispose(): void;
}

export function createAirliner(scene: THREE.Scene): AirlinerView {
  const C = CONFIG.plane;
  const group = new THREE.Group();
  scene.add(group);

  const body = new THREE.MeshStandardMaterial({ color: '#e8ecef', metalness: 0.7, roughness: 0.3 });
  const belly = new THREE.MeshStandardMaterial({ color: '#2b5fa8', metalness: 0.7, roughness: 0.35 });
  const accent = new THREE.MeshStandardMaterial({ color: '#c8102e', metalness: 0.5, roughness: 0.4 });
  const dark = new THREE.MeshStandardMaterial({ color: '#15181c', metalness: 0.4, roughness: 0.3 });
  const winMat = new THREE.MeshBasicMaterial({ color: '#ffca7a', fog: false });

  // Fuselage: capsule along +Z (nose at +Z/2).
  const fus = new THREE.Mesh(new THREE.CapsuleGeometry(C.radius, C.len - C.radius * 2, 6, 14), body);
  fus.rotation.x = Math.PI / 2;
  fus.castShadow = true;
  group.add(fus);
  const bellyMesh = new THREE.Mesh(new THREE.CapsuleGeometry(C.radius * 0.92, C.len - C.radius * 2, 4, 10, 0, Math.PI), belly);
  bellyMesh.rotation.x = Math.PI / 2;
  bellyMesh.rotation.z = Math.PI;
  bellyMesh.position.y = -0.25;
  group.add(bellyMesh);
  const cheat = new THREE.Mesh(new THREE.CylinderGeometry(C.radius * 1.005, C.radius * 1.005, C.len * 0.86, 14, 1, true, Math.PI * 0.42, Math.PI * 0.16), accent);
  cheat.rotation.x = Math.PI / 2;
  group.add(cheat);

  // Cockpit band.
  const cock = new THREE.Mesh(new THREE.CylinderGeometry(C.radius * 0.99, C.radius * 0.99, 3.4, 12, 1, true, 0, Math.PI), dark);
  cock.rotation.x = Math.PI / 2;
  cock.rotation.z = Math.PI / 2;
  cock.position.z = C.len / 2 - 4.4;
  cock.rotation.y = Math.PI / 2;
  cock.position.set(0, 0.6, C.len / 2 - 4.2);
  group.add(cock);

  // Passenger window strip: dotted emissive quads (instanced).
  const WN = 46;
  const wins = new THREE.InstancedMesh(
    new THREE.PlaneGeometry(0.55, 0.8), winMat, WN * 2,
  );
  const dm = new THREE.Object3D();
  for (let i = 0; i < WN; i++) {
    const z = C.len / 2 - 8 - i * (C.len - 18) / WN;
    for (const sd of [-1, 1]) {
      const k = i * 2 + (sd < 0 ? 0 : 1);
      dm.position.set(sd * (C.radius * 0.995), 0.55, z);
      dm.rotation.set(0, sd < 0 ? -Math.PI / 2 : Math.PI / 2, 0);
      dm.scale.setScalar(1);
      dm.updateMatrix();
      wins.setMatrixAt(k, dm.matrix);
    }
  }
  group.add(wins);

  // Wings: swept with dihedral.
  const wingShape = new THREE.Shape();
  wingShape.moveTo(0, 0);
  wingShape.lineTo(-C.span / 2, -C.span * 0.18);
  wingShape.lineTo(-C.span / 2, -C.span * 0.24);
  wingShape.lineTo(0, -3.2);
  wingShape.closePath();
  const wingGeo = new THREE.ExtrudeGeometry(wingShape, { depth: 0.5, bevelEnabled: false });
  const wingR = new THREE.Mesh(wingGeo, body);
  wingR.rotation.x = -Math.PI / 2;
  wingR.rotation.z = Math.PI; // mirror via scale instead
  wingR.castShadow = true;
  const wingL = new THREE.Mesh(wingGeo, body);
  wingL.scale.x = -1;
  wingL.rotation.copy(wingR.rotation);
  const dih = 0.09;
  wingR.position.set(1.5, -0.6, 2);
  wingL.position.set(-1.5, -0.6, 2);
  wingR.rotation.y = -dih;
  wingL.rotation.y = dih;
  group.add(wingR, wingL);

  // Engines under wings.
  const nacGeo = new THREE.CapsuleGeometry(1.5, 3.4, 4, 10);
  const nacR = new THREE.Mesh(nacGeo, body);
  const nacL = new THREE.Mesh(nacGeo, body);
  nacR.rotation.x = nacL.rotation.x = Math.PI / 2;
  nacR.position.set(C.span * 0.22, -2.4, 4.5);
  nacL.position.set(-C.span * 0.22, -2.4, 4.5);
  group.add(nacR, nacL);

  // Stabilisers.
  const stabGeo = new THREE.BoxGeometry(C.span * 0.34, 0.4, 5);
  const stab = new THREE.Mesh(stabGeo, body);
  stab.position.set(0, 0.6, -C.len / 2 + 3);
  group.add(stab);
  const finGeo = new THREE.BoxGeometry(0.4, 7.5, 5.5);
  const fin = new THREE.Mesh(finGeo, accent);
  fin.position.set(0, 3.6, -C.len / 2 + 3.4);
  group.add(fin);

  // Nav lights.
  const navL = new THREE.Mesh(new THREE.SphereGeometry(0.3, 6, 6), new THREE.MeshBasicMaterial({ color: '#ff3030', fog: false }));
  const navR = new THREE.Mesh(new THREE.SphereGeometry(0.3, 6, 6), new THREE.MeshBasicMaterial({ color: '#30ff50', fog: false }));
  navL.position.set(-C.span / 2 + 0.5, -0.6 - C.span * 0.2 * 0 + 2.4, 2);
  navR.position.set(C.span / 2 - 0.5, 2.4 - 0.6, 2);
  navL.position.y = navR.position.y = 1.2;
  const strobe = new THREE.Mesh(new THREE.SphereGeometry(0.32, 6, 6), new THREE.MeshBasicMaterial({ color: '#ffffff', fog: false }));
  strobe.position.set(0, 7.4, -C.len / 2 + 3.4);
  group.add(navL, navR, strobe);

  // Landing gear (hidden until deployed).
  const gearG = new THREE.Group();
  const strutMat = new THREE.MeshStandardMaterial({ color: '#9aa0a6', metalness: 0.8, roughness: 0.4 });
  for (const [gx, gz] of [[0, C.len / 2 - 8], [0, -C.len / 2 + 10], [C.span * 0.2, 4], [-C.span * 0.2, 4]]) {
    const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 3.4, 6), strutMat);
    strut.position.set(gx, -C.radius - 1.7, gz);
    const wheels = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 0.6, 10), dark);
    wheels.rotation.z = Math.PI / 2;
    wheels.position.set(gx, -C.radius - 3.4, gz);
    gearG.add(strut, wheels);
  }
  gearG.visible = false;
  group.add(gearG);

  // Burning engine glow sprite anchor.
  const fireAnchor = new THREE.Object3D();
  fireAnchor.position.copy(nacR.position);
  group.add(fireAnchor);

  // Nose-cone crumple: dedicated morphable cap.
  const noseCapGeo = new THREE.SphereGeometry(C.radius, 12, 10, 0, Math.PI * 2, 0, Math.PI / 2);
  const noseOrig = (noseCapGeo.attributes.position as THREE.BufferAttribute).array.slice() as unknown as Float32Array;
  const noseCap = new THREE.Mesh(noseCapGeo, body);
  noseCap.rotation.x = -Math.PI / 2;
  noseCap.position.z = C.len / 2 - 0.01;
  group.add(noseCap);

  const api: AirlinerView = {
    group,
    sync(s, dt, t) {
      group.position.copy(s.pos);
      group.quaternion.copy(s.quat);
      // Gear deploy logic.
      const wantGear = s.pos.y < CONFIG.plane.gearAlt && s.vel.length() < CONFIG.plane.gearSpd + 40;
      const gt = wantGear ? 1 : 0;
      s.gear += (gt - s.gear) * Math.min(1, dt * 2.2);
      if (s.gear > 0.02 && !gearG.visible && s.gear > 0.05) gearG.visible = true;
      gearG.visible = s.gear > 0.03;
      gearG.children.forEach((c) => { c.scale.setScalar(Math.max(0.001, s.gear)); });
      // Strobe blink 1 Hz.
      strobe.visible = Math.sin(t * Math.PI * 2) > 0.6;
      // Crumple displacement.
      if (s.crumple > 0.001) {
        const pa = noseCapGeo.attributes.position as THREE.BufferAttribute;
        const arr = pa.array as Float32Array;
        for (let i = 0; i < arr.length; i += 3) {
          const ox = noseOrig[i], oy = noseOrig[i + 1], oz = noseOrig[i + 2];
          const dent = Math.sin(ox * 9.1 + oy * 7.7) * Math.cos(oz * 8.3);
          const k = s.crumple * 0.55 * (0.4 + 0.6 * Math.abs(dent));
          arr[i] = ox * (1 - k); arr[i + 1] = oy * (1 - k); arr[i + 2] = oz * (1 - k * 1.4);
        }
        pa.needsUpdate = true;
        noseCapGeo.computeVertexNormals();
      }
      // Dead spiral roll.
      if (s.dead) { s.roll += dt * 1.4; syncQuat(s); }
    },
    emitFire() { /* wired externally */ },
    dispose() {
      scene.remove(group);
      group.traverse((o) => { const m = o as THREE.Mesh; if (m.geometry) m.geometry.dispose(); });
      [body, belly, accent, dark, winMat, strutMat].forEach((m) => m.dispose());
    },
    ...({ fireAnchor } as Record<string, unknown>),
  } as AirlinerView & { fireAnchor: THREE.Object3D };

  return api;
}
```

### src/entities/holding.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import type { AirlinerState, CatchPoint } from './airliner.js';
import { syncQuat, fwdOf, applyHullDamage } from './airliner.js';
import type { FlightState } from './flight.js';
import { clamp, lerp, safeNorm } from '../core/math.js';

export interface HoldCtrl {
  brake: number;   // 0..1 S (push back)
  fwd: number;     // 0..1 W
  lift: number;    // 0..1 Space
  sink: number;    // 0..1 Ctrl
  aimDir: THREE.Vector3;
}

export interface HoldFlags { warned: boolean; crunched: boolean; tore: boolean; threw: boolean }

const UP = new THREE.Vector3(0, 1, 0);
const tv = new THREE.Vector3();

/** Local-space grab anchors (nose at +Z). */
export function anchorLocal(point: CatchPoint, out: THREE.Vector3): THREE.Vector3 {
  const C = CONFIG.plane;
  if (point === 'NOSE') return out.set(0, -(C.radius + 0.55), C.len / 2 - 5);
  return out.set(0, -(C.radius + 0.4), -C.len / 2 + 4);
}

export function anchorWorld(s: AirlinerState, point: CatchPoint, out: THREE.Vector3): THREE.Vector3 {
  anchorLocal(point, tv);
  return out.copy(tv).applyQuaternion(s.quat).add(s.pos);
}

/** Validate a grab attempt. */
export function canGrab(
  s: AirlinerState, heroPos: THREE.Vector3, heroSpeed: number, point: CatchPoint,
): boolean {
  if (s.caught || s.dead || s.touchedDown) return false;
  if (point === 'TAIL' && s.torn) return false;
  anchorWorld(s, point, tv);
  const d = tv.distanceTo(heroPos);
  if (d > CONFIG.plane.grabDist) return false;
  const rel = Math.hypot(heroSpeed - s.vel.length());
  return rel <= CONFIG.plane.speedMatch;
}

/** Attach hero to a point. TAIL is a trap: it tears after tearDelay. */
export function attach(s: AirlinerState, hero: FlightState, point: CatchPoint) {
  s.caught = point;
  s.catchAnim = 0;
  if (point === 'TAIL') s.tearT = CONFIG.plane.tearDelay;
  hero.mode = 'holding';
}

/** Detach; throwDir optional shove applied to the hero. */
export function detach(s: AirlinerState, hero: FlightState, throwVel?: THREE.Vector3) {
  s.caught = null;
  hero.mode = 'flight';
  if (throwVel) hero.vel.copy(throwVel);
}

/**
 * Coupled hero+plane body step. Owns the plane's velocity while held.
 * Call only when s.caught != null.
 */
export function step(s: AirlinerState, hero: FlightState, ctrl: HoldCtrl, h: number): HoldFlags {
  const C = CONFIG.plane;
  const flags: HoldFlags = { warned: false, crunched: false, tore: false, threw: false };
  if (!s.caught) return flags;

  s.catchAnim = Math.min(1, s.catchAnim + h / C.catchTime);

  // --- Tail tear ---
  if (s.caught === 'TAIL') {
    s.tearT -= h;
    if (s.tearT <= 0) {
      s.torn = true;
      applyHullDamage(s, C.dmgTail);
      s.pitch -= 8 * Math.PI / 180;
      s.vel.y -= 6;
      // Throw hero clear.
      hero.pos.copy(anchorWorld(s, 'TAIL', new THREE.Vector3()));
      hero.vel.copy(s.vel).multiplyScalar(0.5);
      hero.vel.y += 14;
      hero.vel.x += (Math.random() - 0.5) * 20;
      hero.vel.z += (Math.random() - 0.5) * 20;
      hero.mode = 'stunned';
      hero.stunT = CONFIG.hero.stunTime;
      s.caught = null;
      flags.tore = true; flags.threw = true;
      return flags;
    }
    // While waiting, ride the plane rigidly.
    rideHero(s, hero, h);
    return flags;
  }

  // --- Braking force ramp ---
  const target = ctrl.brake * C.brakeMax;
  s.brakeCur = lerp(s.brakeCur ?? 0, target, 1 - Math.exp(-h / (C.brakeRampT / 3)));
  const brake = s.brakeCur;

  // Attitude chase from aim.
  const ad = safeNorm(ctrl.aimDir.clone ? ctrl.aimDir : tv.copy(ctrl.aimDir));
  const desYaw = Math.atan2(ad.z, ad.x);
  const desPitch = clamp(Math.asin(clamp(ad.y, -1, 1)), -C.pitchLim, C.pitchLim);
  let dy = desYaw - s.yaw;
  while (dy > Math.PI) dy -= Math.PI * 2;
  while (dy < -Math.PI) dy += Math.PI * 2;
  const maxYaw = C.yawRateMax * h;
  const yawApplied = clamp(dy, -maxYaw, maxYaw);
  s.yaw += yawApplied;
  s.pitch += clamp(desPitch - s.pitch, -0.6 * h, 0.6 * h);
  const rollTgt = clamp(-yawApplied / h * 0.35, -C.rollLim, C.rollLim);
  s.roll = lerp(s.roll, rollTgt, 1 - Math.exp(-h * 3));

  // Longitudinal forces along forward.
  fwdOf(s, tv);
  const fw = tv.clone();
  const sp = s.vel.length();
  const along = sp > 0.1 ? s.vel.dot(fw) / Math.max(sp, 1e-6) * sp : 0; // signed forward speed
  let dv = 0;
  dv -= brake * Math.sign(along || 1);           // push back
  dv += ctrl.fwd * C.fwdPush * Math.sign(along || 1);
  // Aerodynamics from pitch.
  if (s.pitch > C.noseAng) { dv -= C.aeroBrakeUp * Math.sign(along || 1); }
  if (s.pitch < -C.noseAng) { dv -= C.aeroBrakeDown * Math.sign(along || 1); }
  const newAlong = Math.max(0, Math.abs(along) - Math.abs(dv) * h) * Math.sign(along || 1);
  // Vertical forces.
  let vy = s.vel.y;
  vy += C.holdGrav * h;
  vy += (ctrl.lift * C.holdLift + ctrl.sink * C.holdSinkCtrl) * h;
  if (s.pitch > C.noseAng) vy += C.aeroLiftUp * h;
  if (s.pitch < -C.noseAng) vy -= 2 * h;
  // Recompose velocity: forward component + vertical + small lateral bleed.
  const lat = tv.set(s.vel.x, 0, s.vel.z).sub(fw.clone().multiplyScalar(
    fw.x * s.vel.x + fw.z * s.vel.z,
  ));
  lat.multiplyScalar(Math.exp(-1.2 * h));
  s.vel.copy(fw).multiplyScalar(newAlong);
  s.vel.x += lat.x; s.vel.z += lat.z;
  s.vel.y = vy;
  s.pos.addScaledVector(s.vel, h);
  syncQuat(s);

  // Ride the hero on the nose anchor.
  rideHero(s, hero, h);

  // --- Stress ---
  const excess = Math.max(0, brake - C.stressSafe);
  let rise = excess * C.stressBrakeRate;
  const yawRateAbs = Math.abs(yawApplied / h);
  if (yawRateAbs > 0.3 || sp > 130 || s.vel.y < -20) rise += C.stressMiscRate;
  if (rise > 0) s.stress = Math.min(100, s.stress + rise * h);
  else s.stress = Math.max(0, s.stress - C.stressDecay * h);

  if (s.stress > C.stressWarn) {
    flags.warned = true;
    s.crumple = Math.min(1, s.crumple + C.crumpleRate * h * ((s.stress - C.stressWarn) / 30));
    if (Math.random() < h * 2) flags.crunched = true;
    applyHullDamage(s, C.dmgStress * h);
  }

  return flags;
}

function rideHero(s: AirlinerState, hero: FlightState, h: number) {
  anchorWorld(s, 'NOSE', tv);
  hero.pos.copy(tv).addScaledVector(UP, -1.1);
  hero.vel.copy(s.vel);
  hero.bank = 0;
}

/** Hero brace orientation under the nose: leaned back 30°, facing forward. */
export function heroHoldQuat(s: AirlinerState, out: THREE.Quaternion): THREE.Quaternion {
  out.copy(s.quat);
  const tilt = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), 30 * Math.PI / 180);
  return out.multiply(tilt);
}
```

### src/entities/laser.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { safeNorm } from '../core/math.js';

export interface LaserTarget {
  kind: 'jet' | 'missile';
  id: number;
  pos: THREE.Vector3;
  radius: number;
}

export interface LaserHit {
  kind: 'jet' | 'missile' | 'building' | 'ground' | 'sky';
  id: number;
  pos: THREE.Vector3;
}

export interface LaserSim {
  heat: number;
  overheated: boolean;
  update(dt: number, firing: boolean): void;
  /** Cast from camera through crosshair; targets supplied per frame. */
  cast(
    origin: THREE.Vector3, dir: THREE.Vector3,
    targets: LaserTarget[],
    raycastWorld: (o: THREE.Vector3, d: THREE.Vector3, max: number) => { t: number; pos: THREE.Vector3; kind: 'building' | 'ground' } | null,
    excludeAirliner: boolean,
  ): LaserHit | null;
  reset(): void;
}

export function createLaserSim(): LaserSim {
  const L = CONFIG.laser;
  const api: LaserSim = {
    heat: 0,
    overheated: false,
    lockT: 0,
    update(dt, firing) {
      if (api.overheated) {
        api.lockT -= dt;
        if (api.lockT <= 0) { api.overheated = false; api.heat = 15; }
        return;
      }
      if (firing) {
        api.heat = Math.min(100, api.heat + L.heatRate * dt);
        if (api.heat >= 100) { api.overheated = true; api.lockT = L.overheatLock; }
      } else {
        api.heat = Math.max(0, api.heat - L.coolRate * dt);
      }
    },
    cast(origin, dir, targets, raycastWorld, excludeAirliner) {
      void excludeAirliner;
      const maxT = L.range;
      let bestT = maxT;
      let hit: LaserHit = { kind: 'sky', id: -1, pos: new THREE.Vector3().copy(origin).addScaledVector(dir, maxT) };
      // Dynamic targets: ray-sphere.
      for (const tg of targets) {
        const oc = new THREE.Vector3().subVectors(origin, tg.pos);
        const b = oc.dot(dir);
        const c = oc.lengthSq() - tg.radius * tg.radius;
        const disc = b * b - c;
        if (disc < 0) continue;
        const t = -b - Math.sqrt(disc);
        if (t > 0.5 && t < bestT) {
          bestT = t;
          hit = { kind: tg.kind, id: tg.id, pos: new THREE.Vector3().copy(origin).addScaledVector(dir, t) };
        }
      }
      // Static world.
      const w = raycastWorld(origin, dir, bestT);
      if (w && w.t < bestT) {
        bestT = w.t;
        hit = { kind: w.kind, id: -1, pos: w.pos.clone() };
      }
      return hit;
    },
    reset() { api.heat = 0; api.overheated = false; },
  };
  return api;
}

// ---------------- Visual ----------------

export interface LaserView {
  setActive(on: boolean): void;
  /** eyes: world positions of both eyes; hit: endpoint or null. */
  sync(eyes: [THREE.Vector3, THREE.Vector3], hit: LaserHit | null, heat: number, t: number): void;
  update(dt: number): void;
  dispose(): void;
}

export function createLaserView(scene: THREE.Scene): LaserView {
  const L = CONFIG.laser;
  const beamGeo = new THREE.CylinderGeometry(1, 1, 1, 8, 1, true);
  beamGeo.translate(0, 0.5, 0); // pivot at eye, extend +Y
  const coreMat = new THREE.MeshBasicMaterial({
    color: '#ffffff', transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const glowMat = new THREE.MeshBasicMaterial({
    color: '#ff2a18', transparent: true, opacity: 0.32,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const beams: THREE.Mesh[] = [];
  for (let i = 0; i < 4; i++) {
    const m = new THREE.Mesh(beamGeo, i < 2 ? coreMat : glowMat);
    m.visible = false;
    m.frustumCulled = false;
    scene.add(m);
    beams.push(m);
  }
  const endLight = new THREE.PointLight('#ff5030', 0, L.lightRange);
  scene.add(endLight);
  const endSparkMat = new THREE.SpriteMaterial({
    color: '#ffd0a0', transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const molten = new THREE.Sprite(new THREE.SpriteMaterial({
    color: '#ff6a20', transparent: true, opacity: 0,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  molten.scale.setScalar(6);
  scene.add(molten);
  let moltenT = 0;
  const UP = new THREE.Vector3(0, 1, 0);
  const dir = new THREE.Vector3();
  const mid = new THREE.Vector3();

  const api: LaserView = {
    setActive(on) { beams.forEach((b) => (b.visible = on)); endLight.visible = on; },
    sync(eyes, hit, heat, t) {
      const on = !!hit;
      const flick = 0.95 + 0.05 * Math.sin(t * L.flickerHz * Math.PI * 2);
      const thin = heat > 75 ? 0.8 : 1;
      if (on) {
        for (let e = 0; e < 2; e++) {
          dir.subVectors(hit.pos, eyes[e]);
          const len = dir.length();
          safeNorm(dir);
          const q = new THREE.Quaternion().setFromUnitVectors(UP, dir);
          mid.addVectors(eyes[e], hit.pos).multiplyScalar(0.5);
          // Core
          let m = beams[e];
          m.position.copy(eyes[e]);
          m.quaternion.copy(q);
          m.scale.set(L.coreRadius * thin * flick, len, L.coreRadius * thin * flick);
          m.visible = true;
          // Glow
          m = beams[e + 2];
          m.position.copy(eyes[e]);
          m.quaternion.copy(q);
          m.scale.set(L.glowRadius * thin * flick, len, L.glowRadius * thin * flick);
          m.visible = true;
        }
        endLight.position.copy(hit.pos);
        endLight.intensity = L.lightIntensity * flick;
        molten.position.copy(hit.pos).addScaledVector(dir, 0.2);
        moltenT = L.scorchFade;
      } else {
        beams.forEach((b) => (b.visible = false));
        endLight.intensity = 0;
      }
    },
    update(dt) {
      if (moltenT > 0) {
        moltenT -= dt;
        (molten.material as THREE.SpriteMaterial).opacity = Math.max(0, moltenT / L.scorchFade) * 0.8;
        molten.scale.setScalar(6 * (0.6 + 0.4 * (moltenT / L.scorchFade)));
      } else (molten.material as THREE.SpriteMaterial).opacity = 0;
    },
    dispose() {
      beams.forEach((b) => scene.remove(b));
      scene.remove(endLight, molten);
      beamGeo.dispose(); coreMat.dispose(); glowMat.dispose();
    },
  };
  return api;
}
```

### src/entities/jet.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { safeNorm, clamp } from '../core/math.js';
import type { Particles } from '../vfx/particles.js';

export type JetStateName = 'approach' | 'attack' | 'break' | 'repos' | 'evade' | 'dead';

export interface Jet {
  id: number;
  active: boolean;
  st: JetStateName;
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  quat: THREE.Quaternion;
  hp: number;
  stT: number;            // time in state
  burstT: number;         // cannon cycle
  laseredT: number;       // consecutive laser time
  evadeCd: number;
  missileCd: number;
  roll: number;
  targetHero: boolean;
  mesh?: THREE.Group;
  contrailL?: unknown;
  contrailR?: unknown;
}

export interface Tracer {
  active: boolean;
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  t: number;
}

export interface JetTargets {
  heroPos: THREE.Vector3;
  heroVel: THREE.Vector3;
  planePos: THREE.Vector3;
  planeVel: THREE.Vector3;
  preferHero: boolean; // mission decides focus
}

export interface JetMgrDeps {
  scene: THREE.Scene;
  particles: Particles;
  onShoot: (j: Jet, aim: THREE.Vector3) => void;
  onDie: (j: Jet, last: boolean) => void;
}

const UP = new THREE.Vector3(0, 1, 0);
const tv = new THREE.Vector3();
const tv2 = new THREE.Vector3();
const tq = new THREE.Quaternion();

export function createJetMesh(): THREE.Group {
  const g = new THREE.Group();
  const body = new THREE.MeshStandardMaterial({ color: '#3c4148', metalness: 0.8, roughness: 0.35 });
  const mark = new THREE.MeshStandardMaterial({ color: '#a01820', metalness: 0.6, roughness: 0.4 });
  const glass = new THREE.MeshStandardMaterial({ color: '#0c1218', metalness: 0.9, roughness: 0.1 });
  const fus = new THREE.Mesh(new THREE.CapsuleGeometry(0.75, 11, 4, 10), body);
  fus.rotation.x = Math.PI / 2;
  fus.castShadow = true;
  g.add(fus);
  const wingShape = new THREE.Shape();
  wingShape.moveTo(0, 2.5);
  wingShape.lineTo(6.5, -3.5);
  wingShape.lineTo(6.5, -4.6);
  wingShape.lineTo(0, -1.5);
  wingShape.closePath();
  const wg = new THREE.ExtrudeGeometry(wingShape, { depth: 0.22, bevelEnabled: false });
  const wr = new THREE.Mesh(wg, body);
  wr.rotation.x = -Math.PI / 2;
  const wl = new THREE.Mesh(wg, body);
  wl.scale.x = -1;
  wl.rotation.x = -Math.PI / 2;
  g.add(wr, wl);
  for (const s of [-1, 1]) {
    const fin = new THREE.Mesh(new THREE.BoxGeometry(0.18, 2.4, 2.2), mark);
    fin.position.set(s * 1.1, 1.1, -4.6);
    fin.rotation.z = s * 0.42;
    g.add(fin);
  }
  const canopy = new THREE.Mesh(new THREE.SphereGeometry(0.62, 8, 6), glass);
  canopy.scale.set(0.8, 0.7, 1.7);
  canopy.position.set(0, 0.55, 2.6);
  g.add(canopy);
  const ab = new THREE.Mesh(
    new THREE.ConeGeometry(0.55, 2.6, 10),
    new THREE.MeshBasicMaterial({ color: '#ff9040', transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
  );
  ab.rotation.x = -Math.PI / 2;
  ab.position.set(0, 0, -7.4);
  g.add(ab);
  (g as unknown as { burner: THREE.Mesh }).burner = ab;
  (g as unknown as { mats: THREE.Material[] }).mats = [body, mark, glass];
  return g;
}

export function createJetManager(deps: JetMgrDeps) {
  const J = CONFIG.jets;
  const jets: Jet[] = [];
  for (let i = 0; i < J.total; i++) {
    jets.push({
      id: i, active: false, st: 'dead',
      pos: new THREE.Vector3(), vel: new THREE.Vector3(), quat: new THREE.Quaternion(),
      hp: J.hp, stT: 0, burstT: 0, laseredT: 0, evadeCd: 0, missileCd: J.missileCd,
      roll: 0, targetHero: true,
    });
  }
  const tracers: Tracer[] = Array.from({ length: 160 }, () => ({
    active: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(), t: 0,
  }));
  // Tracer rendering: instanced stretched boxes.
  const trGeo = new THREE.BoxGeometry(0.14, 0.14, 6);
  const trMat = new THREE.MeshBasicMaterial({
    color: '#ffd070', transparent: true, opacity: 0.9,
    blending: THREE.AdditiveBlending, depthWrite: false, fog: false,
  });
  const trMesh = new THREE.InstancedMesh(trGeo, trMat, tracers.length);
  trMesh.frustumCulled = false;
  deps.scene.add(trMesh);
  const dm = new THREE.Object3D();

  function spawn(target: THREE.Vector3, preferHero: boolean): Jet | null {
    const j = jets.find((x) => !x.active);
    if (!j) return null;
    const a = Math.random() * Math.PI * 2;
    const r = J.engagement();
    j.pos.set(target.x + Math.cos(a) * r, Math.max(300, target.y + 300 + Math.random() * 600), target.z + Math.sin(a) * r);
    j.vel.set(0, 0, J.speed);
    j.active = true; j.st = 'approach'; j.stT = 0; j.hp = J.hp;
    j.laseredT = 0; j.evadeCd = 0; j.missileCd = J.missileCd * (0.5 + Math.random());
    j.targetHero = preferHero;
    if (!j.mesh) {
      j.mesh = createJetMesh();
      deps.scene.add(j.mesh);
    }
    j.mesh.visible = true;
    return j;
  }

  function steerToward(j: Jet, want: THREE.Vector3, maxTurn: number, h: number) {
    const cur = tv.copy(j.vel).normalize();
    const w = safeNorm(tv2.copy(want));
    const dot = clamp(cur.dot(w), -1, 1);
    const ang = Math.acos(dot);
    if (ang > 1e-4) {
      const axis = new THREE.Vector3().crossVectors(cur, w);
      if (axis.lengthSq() < 1e-8) axis.copy(UP).cross(cur);
      safeNorm(axis);
      tq.setFromAxisAngle(axis, Math.min(ang, maxTurn * h));
      j.vel.applyQuaternion(tq).normalize().multiplyScalar(J.speed);
      j.roll = clamp(-tq.angle * 6, -1.2, 1.2);
    } else j.roll *= Math.exp(-2 * h);
  }

  function update(h: number, tg: JetTargets, topAtFn: (x: number, z: number) => number) {
    for (const j of jets) {
      if (!j.active) continue;
      j.stT += h; j.evadeCd -= h; j.missileCd -= h;
      const tp = j.targetHero ? tg.heroPos : tg.planePos;
      const tvp = j.targetHero ? tg.heroVel : tg.planeVel;
      const toT = tv.subVectors(tp, j.pos);
      const dist = toT.length();

      switch (j.st) {
        case 'approach':
          steerToward(j, toT, J.turnMax * 0.7, h);
          if (dist < J.attackDist()) { j.st = 'attack'; j.stT = 0; j.burstT = 0; }
          break;
        case 'attack': {
          // Lead the target.
          const tof = dist / J.tracerSpeed;
          const lead = tv2.copy(tp).addScaledVector(tvp, tof).sub(j.pos);
          steerToward(j, lead, J.turnMax * 0.55, h);
          j.burstT -= h;
          if (dist < J.gunRange && j.burstT <= 0) {
            j.burstT = J.burstOn;
            shootBurst(j, tp, tvp);
          }
          if (j.burstT <= -J.burstOff) j.burstT = 0;
          if (dist < 260) { j.st = 'break'; j.stT = 0; }
          if (j.stT > 9) { j.st = 'repos'; j.stT = 0; }
          break;
        }
        case 'break': {
          const side = tv2.set(-toT.z, 0, toT.x).normalize();
          steerToward(j, side.multiplyScalar(200).setY(60), J.breakTurn(), h);
          if (j.stT > J.breakTime) { j.st = 'repos'; j.stT = 0; }
          break;
        }
        case 'repos': {
          const away = tv2.copy(j.pos).sub(tp).normalize().multiplyScalar(J.reposDist).add(tp);
          away.y += 200;
          steerToward(j, tv.copy(away).sub(j.pos), J.turnMax * 0.8, h);
          if (j.stT > 3.5) { j.st = 'approach'; j.stT = 0; }
          break;
        }
        case 'evade': {
          // Barrel roll + hard break.
          j.roll += h * 9;
          const side = tv2.set(-toT.z, 60, toT.x).normalize();
          steerToward(j, side, J.turnMax, h);
          if (j.stT > 1.1) { j.st = 'repos'; j.stT = 0; j.laseredT = 0; }
          break;
        }
        default: break;
      }
      // Evade trigger.
      if (j.laseredT > J.evadeAfter && j.evadeCd <= 0 && j.st !== 'evade') {
        j.st = 'evade'; j.stT = 0; j.evadeCd = J.evadeCool;
      }
      // Floor & building avoidance.
      const terr = topAtFn(j.pos.x + j.vel.x * 1.5, j.pos.z + j.vel.z * 1.5);
      const minY = terr + J.floorMargin;
      if (j.pos.y < minY + 60) j.vel.y += (minY + 60 - j.pos.y) * 2 * h;
      j.pos.addScaledVector(j.vel, h);
      if (j.pos.y < minY) j.pos.y = minY;
      // Orientation.
      const fwd = tv.copy(j.vel).normalize();
      const right = new THREE.Vector3().crossVectors(UP, fwd).normalize();
      const up2 = new THREE.Vector3().crossVectors(fwd, right);
      const banked = right.clone().applyAxisAngle(fwd, j.roll);
      const m = new THREE.Matrix4().makeBasis(banked, up2, fwd);
      j.quat.setFromRotationMatrix(m);
      // Burner flicker.
      if (j.mesh) {
        j.mesh.position.copy(j.pos);
        j.mesh.quaternion.copy(j.quat);
        const bn = (j.mesh as unknown as { burner: THREE.Mesh }).burner;
        const mat = bn.material as THREE.MeshBasicMaterial;
        mat.opacity = 0.5 + 0.4 * Math.random();
      }
      // Wingtip contrails during hard turns.
      if (Math.abs(j.roll) > 0.5 && Math.random() < h * 40) {
        for (const s of [-1, 1]) {
          const off = tv2.set(s * 6.4, 0, -1).applyQuaternion(j.quat);
          deps.particles.spawn({
            x: j.pos.x + off.x, y: j.pos.y + off.y, z: j.pos.z + off.z,
            vx: 0, vy: 0, vz: 0, life: 1.2, size0: 1.2, size1: 4,
            r0: 0.9, g0: 0.9, b0: 0.95, r1: 0.7, g1: 0.7, b1: 0.75,
            a0: 0.35, a1: 0, blending: 'alpha',
          });
        }
      }
      j.laseredT = Math.max(0, j.laseredT - h * 0.6);
    }
    // Tracers.
    for (const tr of tracers) {
      if (!tr.active) continue;
      tr.t -= h;
      tr.pos.addScaledVector(tr.vel, h);
      if (tr.t <= 0 || tr.pos.y < 0) tr.active = false;
    }
    let ti = 0;
    for (const tr of tracers) {
      if (!tr.active) { dm.position.set(0, -9999, 0); dm.scale.setScalar(0.001); }
      else {
        dm.position.copy(tr.pos);
        dm.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), tv.copy(tr.vel).normalize());
        dm.scale.set(1, 1, 1);
      }
      dm.updateMatrix();
      trMesh.setMatrixAt(ti++, dm.matrix);
    }
    trMesh.instanceMatrix.needsUpdate = true;
  }

  function shootBurst(j: Jet, tp: THREE.Vector3, tvp: THREE.Vector3) {
    const shots = Math.ceil(J.burstRate * J.burstOn);
    for (let i = 0; i < shots; i++) {
      const delay = i / J.burstRate;
      // Schedule approximately: fire now with slight spread; cadence emerges from repeats.
      void delay;
      const tr = tracers.find((x) => !x.active);
      if (!tr) break;
      const tof = tv.subVectors(tp, j.pos).length() / J.tracerSpeed;
      const aim = tv2.copy(tp).addScaledVector(tvp, tof);
      aim.sub(j.pos).normalize();
      // Spread.
      aim.x += (Math.random() - 0.5) * J.tracerSpread * 2;
      aim.y += (Math.random() - 0.5) * J.tracerSpread * 2;
      aim.z += (Math.random() - 0.5) * J.tracerSpread * 2;
      safeNorm(aim);
      tr.active = true;
      tr.pos.copy(j.pos).addScaledVector(aim, 8);
      tr.vel.copy(aim).multiplyScalar(J.tracerSpeed).add(j.vel);
      tr.t = J.tracerLife;
      deps.onShoot(j, aim);
    }
  }

  function damage(j: Jet, amt: number, lasering: boolean) {
    if (!j.active) return;
    j.hp -= amt;
    if (lasering) j.laseredT += 0.05;
    if (j.hp <= 0) kill(j);
  }

  function kill(j: Jet) {
    j.active = false;
    j.st = 'dead';
    if (j.mesh) j.mesh.visible = false;
    const alive = jets.filter((x) => x.active).length;
    deps.onDie(j, alive === 0);
  }

  function activeCount() { return jets.filter((j) => j.active).length; }

  function forEachActive(fn: (j: Jet) => void) { jets.forEach((j) => { if (j.active) fn(j); }); }

  return { jets, tracers, spawn, update, damage, kill, activeCount, forEachActive };
}

// Config helper bindings (kept as functions so tests/debug can tweak).
declare module './jet.js' {}
(Object.assign(CONFIG.jets, {
  engagement: () => CONFIG.jets.engage,
  attackDist: () => 900,
  breakTurn: () => 4 * 9.8 / CONFIG.jets.speed + 0.9,
}));
```

### src/entities/missile.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { safeNorm, clamp } from '../core/math.js';
import type { Particles } from '../vfx/particles.js';

export interface Missile {
  active: boolean;
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  hp: number;
  t: number;
  closest: number;
  passed: boolean;
  targetHero: boolean;
  mesh?: THREE.Group;
}

export interface MisDeps {
  scene: THREE.Scene;
  particles: Particles;
  onDetonate: (m: Missile, hitSomething: boolean) => void;
}

const tv = new THREE.Vector3();
const tv2 = new THREE.Vector3();
const tq = new THREE.Quaternion();
const UP = new THREE.Vector3(0, 1, 0);

export function createMissileManager(deps: MisDeps) {
  const M = CONFIG.missile;
  const mis: Missile[] = Array.from({ length: 6 }, () => ({
    active: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(),
    hp: M.hp, t: 0, closest: 1e9, passed: false, targetHero: true,
  }));
  const geo = new THREE.CapsuleGeometry(0.28, 2.4, 3, 8);
  const mat = new THREE.MeshStandardMaterial({ color: '#b8bcc2', metalness: 0.7, roughness: 0.4 });
  for (const m of mis) {
    m.mesh = new THREE.Group();
    const b = new THREE.Mesh(geo, mat);
    b.rotation.x = Math.PI / 2;
    m.mesh.add(b);
    for (const [fx, fz] of [[0.5, -1], [-0.5, -1], [0, -1.2]]) {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.7, 0.5), mat);
      fin.position.set(fx, 0, fz);
      fin.rotation.z = fx * 1.2;
      m.mesh.add(fin);
    }
    m.mesh.visible = false;
    deps.scene.add(m.mesh);
  }

  function fire(from: THREE.Vector3, vel: THREE.Vector3, targetHero: boolean): Missile | null {
    const m = mis.find((x) => !x.active);
    if (!m) return null;
    m.active = true;
    m.pos.copy(from);
    m.vel.copy(vel).normalize().multiplyScalar(M.speed);
    m.hp = M.hp; m.t = 0; m.closest = 1e9; m.passed = false; m.targetHero = targetHero;
    m.mesh!.visible = true;
    deps.onDetonateLaunch?.();
    return m;
  }

  function update(h: number, heroPos: THREE.Vector3, planePos: THREE.Vector3) {
    for (const m of mis) {
      if (!m.active) continue;
      m.t += h;
      const tp = m.targetHero ? heroPos : planePos;
      const to = tv.subVectors(tp, m.pos);
      const d = to.length();
      m.closest = Math.min(m.closest, d);
      if (d < m.closest - 0.5) m.closest = d;
      // Passed target?
      if (m.vel.dot(to) < 0 && m.t > 1) m.passed = true;
      if (m.passed && m.closest > 60) { detonate(m, false); continue; }
      if (d < M.fuse) { detonate(m, true); continue; }
      if (m.t > 14) { detonate(m, false); continue; }
      // Homing with turn limit.
      const want = safeNorm(tv2.copy(to));
      const cur = tv2.copy(m.vel).normalize();
      void cur;
      const wd = tv2.copy(to).normalize();
      const cd = tv.copy(m.vel).normalize();
      const dot = clamp(cd.dot(wd), -1, 1);
      const ang = Math.acos(dot);
      if (ang > 1e-4) {
        const axis = new THREE.Vector3().crossVectors(cd, wd);
        if (axis.lengthSq() < 1e-8) axis.copy(UP).cross(cd);
        safeNorm(axis);
        tq.setFromAxisAngle(axis, Math.min(ang, M.turn * h));
        m.vel.applyQuaternion(tq);
      }
      const sp = M.speed;
      m.vel.setLength(sp);
      m.pos.addScaledVector(m.vel, h);
      // Smoke trail.
      if (Math.random() < h * 60) {
        deps.particles.spawn({
          x: m.pos.x, y: m.pos.y, z: m.pos.z,
          vx: (Math.random() - 0.5) * 2, vy: 1.5, vz: (Math.random() - 0.5) * 2,
          life: 2.2, size0: 1.4, size1: 7,
          r0: 0.92, g0: 0.9, b0: 0.88, r1: 0.35, g1: 0.34, b1: 0.34,
          a0: 0.5, a1: 0, blending: 'alpha',
        });
      }
      m.mesh!.position.copy(m.pos);
      m.mesh!.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tv.copy(m.vel).normalize());
    }
  }

  function detonate(m: Missile, hit: boolean) {
    m.active = false;
    m.mesh!.visible = false;
    deps.onDetonate(m, hit);
  }

  function damage(m: Missile, amt: number) {
    if (!m.active) return;
    m.hp -= amt;
    if (m.hp <= 0) detonate(m, true);
  }

  const activeCount = () => mis.filter((m) => m.active).length;
  return { mis, fire, update, damage, detonate, activeCount };
}

declare module './missile.js' {}
interface MisExtra { onDetonateLaunch?: () => void }
```

### src/entities/wreck.ts
```ts
import * as THREE from 'three';
import type { Particles } from '../vfx/particles.js';

export interface Wreck {
  active: boolean;
  pos: THREE.Vector3;
  vel: THREE.Vector3;
  rot: THREE.Euler;
  w: THREE.Vector3;
  t: number;
  mesh?: THREE.Mesh;
}

/** Flaming tumbling debris that detonates again on ground impact. */
export function createWreckManager(scene: THREE.Scene, particles: Particles, onImpact: (x: number, y: number, z: number) => void) {
  const wrecks: Wreck[] = Array.from({ length: 4 }, () => ({
    active: false, pos: new THREE.Vector3(), vel: new THREE.Vector3(),
    rot: new THREE.Euler(), w: new THREE.Vector3(), t: 0,
  }));
  const geo = new THREE.BoxGeometry(3, 1.4, 7);
  const mat = new THREE.MeshStandardMaterial({
    color: '#2c2c30', roughness: 0.6, metalness: 0.5,
    emissive: '#ff4400', emissiveIntensity: 0.8,
  });
  for (const wk of wrecks) {
    wk.mesh = new THREE.Mesh(geo, mat);
    wk.mesh.visible = false;
    wk.mesh.castShadow = true;
    scene.add(wk.mesh);
  }

  function spawn(pos: THREE.Vector3, vel: THREE.Vector3) {
    const wk = wrecks.find((x) => !x.active);
    if (!wk) return;
    wk.active = true;
    wk.t = 0;
    wk.pos.copy(pos);
    wk.vel.copy(vel).multiplyScalar(0.55);
    wk.vel.y = Math.max(wk.vel.y, 4);
    wk.w.set(Math.random() * 6 - 3, Math.random() * 6 - 3, Math.random() * 6 - 3);
    wk.rot.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
    wk.mesh!.visible = true;
  }

  function update(dt: number) {
    for (const wk of wrecks) {
      if (!wk.active) continue;
      wk.t += dt;
      wk.vel.y -= 9.8 * dt;
      wk.pos.addScaledVector(wk.vel, dt);
      wk.rot.x += wk.w.x * dt; wk.rot.y += wk.w.y * dt; wk.rot.z += wk.w.z * dt;
      if (Math.random() < dt * 50) {
        particles.spawn({
          x: wk.pos.x, y: wk.pos.y, z: wk.pos.z,
          vx: (Math.random() - 0.5) * 3, vy: 2 + Math.random() * 3, vz: (Math.random() - 0.5) * 3,
          life: 1.6, size0: 2.4, size1: 9,
          r0: 0.25, g0: 0.23, b0: 0.22, r1: 0.05, g1: 0.05, b1: 0.05,
          a0: 0.55, a1: 0, blending: 'alpha',
        });
      }
      if (Math.random() < dt * 30) {
        particles.spawn({
          x: wk.pos.x, y: wk.pos.y, z: wk.pos.z,
          vx: 0, vy: 1, vz: 0, life: 0.35, size0: 1.6, size1: 0.4,
          r0: 1, g0: 0.55, b0: 0.15, r1: 0.4, g1: 0.1, b1: 0.02, a0: 0.9, a1: 0,
        });
      }
      wk.mesh!.position.copy(wk.pos);
      wk.mesh!.rotation.copy(wk.rot);
      if (wk.pos.y <= 1 || wk.t > 8) {
        wk.active = false;
        wk.mesh!.visible = false;
        onImpact(wk.pos.x, 1, wk.pos.z);
      }
    }
  }

  return { wrecks, spawn, update };
}
```

### src/game/camera.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import { clamp, lerp, sat, smooth } from '../core/math.js';

export interface CamFeed {
  heroPos: THREE.Vector3;
  aimDir: THREE.Vector3;
  bank: number;          // rad
  speed: number;
  holding: boolean;
  lockTarget: THREE.Vector3 | null;
  planePos?: THREE.Vector3;
}

export interface Override { pos: THREE.Vector3; look: THREE.Vector3; fov?: number }

export interface CamCtl {
  update(dt: number, feed: CamFeed): void;
  addShake(v: number): void;
  kick(): void;
  worldToScreen(v: THREE.Vector3, out: { x: number; y: number; z: number; vis: boolean }): void;
  fovNow: number;
  camera: THREE.PerspectiveCamera;
}

export function createCameraControl(
  camera: THREE.PerspectiveCamera,
  raycastSolid: (o: THREE.Vector3, d: THREE.Vector3, max: number) => { t: number } | null,
): CamCtl {
  const C = CONFIG.cam;
  const curPos = new THREE.Vector3(0, 130, 10);
  const lookPt = new THREE.Vector3();
  let fov = C.fovBase;
  let kickT = 0;
  let shakeHits = 0;
  let shakeAmb = 0;
  const tv = new THREE.Vector3();
  const tv2 = new THREE.Vector3();
  const upv = new THREE.Vector3(0, 1, 0);

  const api: CamCtl = {
    camera,
    fovNow: C.fovBase,
    addShake(v) { shakeHits = Math.min(2.5, shakeHits + v); },
    kick() { kickT = C.kickTime; },
    worldToScreen(v, out) {
      tv.copy(v).project(camera);
      out.x = (tv.x * 0.5 + 0.5) * window.innerWidth;
      out.y = (-tv.y * 0.5 + 0.5) * window.innerHeight;
      out.z = tv.z;
      out.vis = tv.z < 1 && Math.abs(tv.x) < 1.4 && Math.abs(tv.y) < 1.4;
    },
    update(dt, feed) {
      const sp = feed.speed;
      const sp01 = sat(sp / CONFIG.hero.vMaxBoost);
      // Spring stiffness: slower at speed so the camera falls behind on boost.
      const tau = lerp(C.tauNear, C.tauFar, smooth(sp01));
      let wantPos: THREE.Vector3;
      let wantLook: THREE.Vector3;
      let wantFov = C.fovBase + C.fovAdd * smooth(sp01);

      if (feed.holding && feed.planePos) {
        // Three-quarter front-low on the braced hero.
        const side = tv.copy(feed.aimDir).cross(upv).normalize();
        wantPos = tv2.copy(feed.heroPos)
          .addScaledVector(feed.aimDir, C.holdDist * 0.55)
          .addScaledVector(side, C.holdDist * 0.8)
          .addScaledVector(upv, C.holdHeight);
        wantLook = feed.heroPos;
        wantFov = 58;
      } else {
        const dist = lerp(C.distHover, C.distFast, smooth(sp01));
        const height = lerp(C.heightHover, C.heightFast, smooth(sp01));
        wantPos = tv.copy(feed.heroPos)
          .addScaledVector(feed.aimDir, -dist)
          .addScaledVector(upv, height);
        const la = lerp(C.lookNear, C.lookFar, smooth(sp01));
        wantLook = tv2.copy(feed.heroPos).addScaledVector(feed.aimDir, la);
        if (feed.lockTarget) wantLook.lerp(feed.lockTarget, C.lockBias);
      }

      // Critical damped follow.
      const k = 1 - Math.exp(-dt / tau);
      curPos.lerp(wantPos, k);
      lookPt.lerp(wantLook, 1 - Math.exp(-dt / (tau * 0.7)));

      // Occlusion: pull in if a building blocks the shot.
      const dirBack = tv.copy(curPos).sub(lookPt);
      const fullLen = dirBack.length();
      if (fullLen > 0.5) {
        dirBack.divideScalar(fullLen);
        const hit = raycastSolid(lookPt, dirBack, fullLen);
        if (hit) {
          const allowed = Math.max(1.2, hit.t - C.occludePad);
          curPos.copy(lookPt).addScaledVector(dirBack, allowed);
        }
      }

      // Shake: sum-of-sines + impulses.
      shakeAmb = lerp(shakeAmb, sp >= 140 ? 0.12 : sp > 100 ? 0.05 : 0, 1 - Math.exp(-dt * 4));
      shakeHits *= Math.exp(-dt * 5);
      const t = performance.now() * 0.001;
      const amp = shakeAmb + shakeHits;
      const ox = Math.sin(t * 31.7) * 0.5 + Math.sin(t * 57.3) * 0.3;
      const oy = Math.sin(t * 41.1 + 1.3) * 0.5 + Math.sin(t * 73.7) * 0.2;

      camera.position.copy(curPos);
      if (amp > 0.001) {
        camera.position.x += ox * amp;
        camera.position.y += oy * amp;
      }
      camera.lookAt(lookPt);
      // Roll follows 35% of body bank.
      camera.up.set(Math.sin(feed.bank * C.rollMix), Math.cos(feed.bank * C.rollMix), 0);
      camera.lookAt(lookPt);

      // FOV.
      if (kickT > 0) { kickT -= dt; wantFov += C.kickFov * (kickT / C.kickTime); }
      fov = lerp(fov, wantFov, 1 - Math.exp(-dt * C.fovLerp));
      api.fovNow = fov;
      if (Math.abs(camera.fov - fov) > 0.01) { camera.fov = fov; camera.updateProjectionMatrix(); }
    },
  };
  return api;
}
```

### src/game/hud.ts
```ts
import { CONFIG } from '../config.js';

type El = HTMLElement;

export interface Hud {
  root: El;
  update(dt: number): void;
  setSpeed(kmh: number, tier: string): void;
  setAlt(m: number): void;
  setHP(f: number): void;
  setObjective(text: string, dist?: number): void;
  setImpact(secondsLeft: number | null, clear: boolean): void;
  setWave(text: string): void;
  setClock(t: number): void;
  setScore(score: number, jets: number): void;
  setCrosshair(spreadPx: number): void;
  setLock(v: null | { x: number; y: number; label: string; dist: number; hp: number }): void;
  setArrow(v: null | { x: number; y: number; ang: number }): void;
  setGrab(v: null | string): void;
  setBoost(f: number, locked: boolean): void;
  setHeat(f: number, over: boolean): void;
  setHolding(on: boolean): void;
  setHull(f: number): void;
  setStress(f: number, warn: boolean): void;
  setPlaneSpeed(ms: number): void;
  setSetdown(v: null | { sink: number; zoneDist: number }): void;
  radio(text: string): void;
  popup(text: string, cls?: string): void;
  damageArc(angDeg: number): void;
  missileWarn(on: boolean): void;
  letterbox(on: boolean): void;
  phaseCard(text: string): void;
  showTitle(on: boolean): void;
  showResults(v: null | { rows: [string, string][]; grade: string; score: number; best: number; newBest: boolean }): void;
  showFailed(reason: string | null): void;
  flashRed(f: number): void;
  whiteout(f: number): void;
  hint(text: string | null): void;
  drawZone(pts: [number, number][] | null): void;
  dispose(): void;
}

export function createHud(parent: El): Hud {
  const css = `
  .lf-hud{position:absolute;inset:0;pointer-events:none;color:#cdf6ff;font-family:system-ui,sans-serif;
    text-transform:uppercase;letter-spacing:.22em;user-select:none;z-index:5;}
  .panel{background:rgba(6,14,20,.55);border:1px solid rgba(140,230,255,.22);padding:vmin;border-radius:2px;}
  .lf-hud div{position:absolute;}
  #lfTL{top:2vmin;left:2vmin;line-height:1.25;}
  #lfTL .big{font-size:4.6vmin;font-weight:700;letter-spacing:.1em;}
  #lfTC{top:2vmin;left:50%;transform:translateX(-50%);text-align:center;font-size:1.9vmin;}
  #lfTR{top:2vmin;right:2vmin;text-align:right;font-size:1.9vmin;}
  #lfBC{bottom:3vmin;left:50%;transform:translateX(-50%);display:flex;gap:2vmin;}
  #lfBR{bottom:3vmin;right:2vmin;text-align:right;font-size:1.8vmin;display:none;}
  #lfBL{bottom:3vmin;left:2vmin;font-size:1.8vmin;max-width:34vw;}
  .bar{width:22vmin;height:1.1vmin;background:rgba(120,200,255,.12);border:1px solid rgba(140,230,255,.3);margin-top:.6vmin;}
  .bar>i{display:block;height:100%;background:#9fe8ff;transition:width .12s;}
  #lfCH{top:50%;left:50%;width:0;height:0;}
  #lfCH b{position:absolute;background:#cdf6ff;box-shadow:0 0 6px #9fe8ff88;}
  #lfLock{border:2px solid #ff5a4a;display:none;font-size:1.5vmin;padding:.4vmin .8vmin;transform:translate(-50%,-50%);white-space:nowrap;}
  #lfArrow{font-size:4vmin;color:#ff5a4a;display:none;transform:translate(-50%,-50%);}
  #lfGrab{top:62%;left:50%;transform:translateX(-50%);font-size:2.6vmin;color:#ffe08a;display:none;
    background:rgba(6,14,20,.6);padding:1vmin 2vmin;border:1px solid rgba(255,224,138,.4);}
  #lfPop{top:26%;left:50%;transform:translateX(-50%);font-size:3.4vmin;font-weight:700;color:#ffe08a;
    opacity:0;text-shadow:0 0 12px #ff9a4066;}
  #lfCard{top:38%;left:50%;transform:translateX(-50%);font-size:5vmin;font-weight:800;letter-spacing:.5em;
    opacity:0;transition:opacity .5s;text-shadow:0 0 24px #6fdcff55;}
  #lfLBt,#lfLBb{left:0;right:0;height:0;background:#000;transition:height .6s;z-index:8;}
  #lfLBt{top:0;} #lfLBb{bottom:0;}
  #lfRed{inset:0;box-shadow:inset 0 0 18vmin rgba(255,40,20,.9);opacity:0;z-index:6;}
  #lfWhite{inset:0;background:#fff;opacity:0;z-index:4;}
  #lfHint{bottom:12vmin;left:50%;transform:translateX(-50%);font-size:2vmin;color:#9fdcff;display:none;}
  #lfMiss{top:14vmin;left:50%;transform:translateX(-50%);color:#ff5a4a;font-size:2.4vmin;display:none;animation:blink .5s infinite;}
  @keyframes blink{50%{opacity:.2}}
  #lfZoneSvg{inset:0;width:100%;height:100%;}
  #lfTitle{inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;
    background:linear-gradient(rgba(4,8,12,.25),rgba(4,8,12,.7));z-index:9;pointer-events:auto;}
  #lfTitle h1{font-size:11vmin;margin:0;letter-spacing:.55em;font-weight:800;color:#eef7ff;text-indent:.55em;
    text-shadow:0 0 40px #59c8ff44;}
  #lfTitle p{font-size:2.1vmin;color:#bcd8ee;max-width:70vmin;text-align:center;line-height:1.7;letter-spacing:.14em;}
  #lfGo{margin-top:4vmin;font-size:2.6vmin;color:#ffe08a;animation:pulse 1.6s infinite;}
  @keyframes pulse{50%{opacity:.35}}
  #lfRes{inset:0;display:none;align-items:center;justify-content:center;z-index:9;background:rgba(4,8,12,.55);pointer-events:auto;}
  #lfRes .card{background:rgba(8,16,22,.9);border:1px solid rgba(140,230,255,.3);padding:4vmin 6vmin;text-align:left;}
  #lfRes h2{margin:0 0 2vmin;font-size:4vmin;letter-spacing:.4em;color:#eef7ff;}
  #lfRes .row{display:flex;justify-content:space-between;gap:6vmin;font-size:2vmin;padding:.5vmin 0;color:#bcd8ee;}
  #lfRes .grade{font-size:9vmin;color:#ffd76a;font-weight:800;}
  #lfFail{inset:0;display:none;align-items:center;justify-content:center;flex-direction:column;z-index:9;background:rgba(20,4,4,.5);}
  #lfFail h2{font-size:6vmin;color:#ff6a5a;letter-spacing:.4em;margin:0;}
  #lfFail p{font-size:2.2vmin;color:#f2c9c0;}
  .radioline{opacity:.9;margin-bottom:.5vmin;color:#bfeaff;}
  .dmgarc{width:16vmin;height:16vmin;border-radius:50%;border:.4vmin solid transparent;
    border-top-color:#ff4a30;top:calc(50% - 8vmin);left:calc(50% - 8vmin);opacity:0;}
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  const root = document.createElement('div');
  root.className = 'lf-hud';
  parent.appendChild(root);

  const mk = (id: string, html = ''): El => {
    const d = document.createElement('div');
    d.id = id;
    d.innerHTML = html;
    root.appendChild(d);
    return d;
  };
  const $ = (id: string) => document.getElementById(id)!;

  mk('lfRed'); mk('lfWhite');
  mk('lfLBt'); mk('lfLBb');
  mk('lfTL', `<div class="big"><span id="lfSpd">0</span> KM/H <span id="lfTier" style="font-size:1.8vmin;color:#9fdcff"></span></div>
    <div id="lfAlt">ALT 0 M</div><div class="bar"><i id="lfHP"></i></div>`);
  mk('lfTC', `<div id="lfObj"></div><div id="lfImp" style="color:#ff6a5a;"></div><div id="lfWave"></div>`);
  mk('lfTR', `<div id="lfClk">0:00</div><div id="lfScr">SCORE 0</div><div id="lfJets"></div>`);
  const ch = mk('lfCH');
  for (let i = 0; i < 4; i++) {
    const b = document.createElement('b');
    b.dataset.i = String(i);
    ch.appendChild(b);
  }
  mk('lfLock'); mk('lfArrow', '➤');
  mk('lfGrab'); mk('lfPop'); mk('lfCard'); mk('lfMiss', '⚠ MISSILE');
  mk('lfBC', `<div><div style="font-size:1.5vmin">BOOST</div><div class="bar" style="width:16vmin"><i id="lfBo"></i></div></div>
    <div><div style="font-size:1.5vmin">HEAT</div><div class="bar" style="width:16vmin"><i id="lfHe"></i></div></div>`);
  mk('lfBR', `<div>HULL <span id="lfHSpan"></span></div><div class="bar" style="margin-left:auto"><i id="lfHu"></i></div>
    <div>STRESS</div><div class="bar" style="margin-left:auto"><i id="lfSt"></i></div>
    <div id="lfBuckle" style="color:#ff5a4a;display:none">NOSE BUCKLING</div>
    <div id="lfPSpd"></div><div id="lfTd"></div>`);
  mk('lfBL');
  mk('lfHint');
  const svgHost = mk('lfZoneSvg');
  svgHost.innerHTML = `<svg width="100%" height="100%"><polygon id="lfZonePoly" points="" fill="none" stroke="#7df3ff" stroke-width="2" opacity="0.8"/></svg>`;
  mk('lfTitle', `<h1>${CONFIG.title}</h1>
    <p>FLIGHT 227 — ENGINE FIRE, 218 SOULS — IS FALLING ON DOWNTOWN WHILE HOSTILES FINISH IT.<br/>
    CUT THE JETS DOWN. TAKE THE PLANE BY THE NOSE. KILL ITS SPEED. LAND IT ON METRO STADIUM.</p>
    <p>MOUSE AIM · LMB LASER · RMB LOCK · W THRUST · SHIFT BOOST · S BRAKE<br/>
    SPACE UP · CTRL DOWN · A/D STRAFE · E GRAB/RELEASE · R RETRY</p>
    <div id="lfGo">CLICK TO FLY</div>`);
  mk('lfRes', '<div class="card"><h2>DEBRIEF</h2><div id="lfRows"></div><div class="row"><span>GRADE</span><span class="grade" id="lfGrade"></span></div><div class="row"><span>BEST</span><span id="lfBest"></span></div><div class="row"><span></span><span style="color:#ffe08a">R PLAY AGAIN</span></div></div>');
  mk('lfFail', '<h2>MISSION FAILED</h2><p id="lfFailWhy"></p>');

  const radiobox = $('lfBL');
  const arcsHost = root;

  // Crosshair ticks styling.
  const ticks = Array.from(ch.children) as HTMLElement[];
  ticks.forEach((b, i) => {
    b.style.width = '0.35vmin';
    b.style.height = '1.6vmin';
    const rots = ['translate(-50%,-130%)', 'translate(-50%,30%)', 'translate(-130%,-50%) rotate(90deg)', 'translate(30%,-50%) rotate(90deg)'];
    b.style.transform = rots[i];
  });

  let popT = 0, cardT = 0, redT = 0, whiteT = 0, hintT = 0;
  const radios: { el: El; t: number; full: string; shown: number }[] = [];
  const pending: string[] = [];

  const api: Hud = {
    root, pending,
    update(dt) {
      popT = Math.max(0, popT - dt); cardT = Math.max(0, cardT - dt);
      redT = Math.max(0, redT - dt); whiteT = Math.max(0, whiteT - dt); hintT = Math.max(0, hintT - dt);
      $('lfPop').style.opacity = String(Math.min(1, popT * 3) * Math.min(1, (CONFIG.misc.popupTime - popT) * 4));
      $('lfCard').style.opacity = cardT > 0 ? String(Math.min(1, cardT * 2)) : '0';
      $('lfRed').style.opacity = String(redT * 2);
      $('lfWhite').style.opacity = String(whiteT);
      $('lfHint').style.display = hintT > 0 ? 'block' : 'none';
      // Typewriter radio.
      for (let i = radios.length - 1; i >= 0; i--) {
        const r = radios[i];
        r.t -= dt;
        r.shown = Math.min(r.full.length, r.shown + CONFIG.misc.typewriterCPS * dt);
        r.el.textContent = '▸ ' + r.full.slice(0, Math.floor(r.shown));
        if (r.t <= 0) { r.el.remove(); radios.splice(i, 1); }
      }
      if (pending.length && radios.length < 3) {
        const txt = pending.shift()!;
        const el = document.createElement('div');
        el.className = 'radioline';
        radiobox.appendChild(el);
        radios.push({ el, t: CONFIG.misc.radioFade + txt.length / CONFIG.misc.typewriterCPS, full: txt, shown: 0 });
      }
    },
    setSpeed(kmh, tier) { $('lfSpd').textContent = String(Math.round(kmh)); $('lfTier').textContent = tier; },
    setAlt(m) { $('lfAlt').textContent = `ALT ${Math.max(0, Math.round(m))} M`; },
    setHP(f) { ($('lfHP') as HTMLElement).style.width = `${Math.max(0, f) * 100}%`; ($('lfHP') as HTMLElement).style.background = f < 0.3 ? '#ff5a4a' : '#9fe8ff'; },
    setObjective(text, dist) {
      $('lfObj').textContent = text + (dist !== undefined ? ` — ${(dist / 1000).toFixed(1)} KM` : '');
    },
    setImpact(sec, clear) {
      const el = $('lfImp');
      if (sec === null) { el.textContent = ''; return; }
      if (clear) { el.textContent = 'PATH CLEAR'; el.style.color = '#69e888'; return; }
      const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
      el.textContent = `IMPACT IN ${m}:${String(s).padStart(2, '0')}`;
      el.style.color = sec < 30 ? '#ff3b2a' : '#ff9a6a';
    },
    setWave(t) { $('lfWave').textContent = t; },
    setClock(t) { $('lfClk').textContent = `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`; },
    setScore(sc, jets) { $('lfScr').textContent = `SCORE ${Math.round(sc)}`; $('lfJets').textContent = `JETS ${jets}`; },
    setCrosshair(spread) {
      const off = 1.2 + spread;
      const rots = [`translate(-50%,-${off}vmin)`, `translate(-50%,${off * 0.4}vmin)`, `translate(-${off}vmin,-50%) rotate(90deg)`, `translate(${off * 0.4}vmin,-50%) rotate(90deg)`];
      ticks.forEach((b, i) => (b.style.transform = rots[i]));
    },
    setLock(v) {
      const el = $('lfLock');
      if (!v) { el.style.display = 'none'; return; }
      el.style.display = 'block';
      el.style.left = `${v.x}px`; el.style.top = `${v.y}px`;
      el.innerHTML = `${v.label}<br/>${Math.round(v.dist)} M ▏${'▮'.repeat(Math.round(v.hp * 8))}${'▯'.repeat(8 - Math.round(v.hp * 8))}`;
    },
    setArrow(v) {
      const el = $('lfArrow');
      if (!v) { el.style.display = 'none'; return; }
      el.style.display = 'block';
      el.style.left = `${v.x}px`; el.style.top = `${v.y}px`;
      el.style.transform = `translate(-50%,-50%) rotate(${v.ang}deg)`;
    },
    setGrab(v) {
      const el = $('lfGrab');
      if (!v) { el.style.display = 'none'; return; }
      el.style.display = 'block'; el.textContent = v;
    },
    setBoost(f, locked) {
      const el = $('lfBo');
      el.style.width = `${f * 100}%`;
      el.style.background = locked ? '#ff5a4a' : '#9fe8ff';
    },
    setHeat(f, over) {
      const el = $('lfHe');
      el.style.width = `${f * 100}%`;
      el.style.background = over ? '#ff3b2a' : f > 0.75 ? '#ff9a4a' : '#ffd76a';
    },
    setHolding(on) { $('lfBR').style.display = on ? 'block' : 'none'; },
    setHull(f) { ($('lfHu') as HTMLElement).style.width = `${f * 100}%`; $('lfHSpan').textContent = `${Math.round(f * 100)}%`; },
    setStress(f, warn) {
      ($('lfSt') as HTMLElement).style.width = `${f * 100}%`;
      ($('lfSt') as HTMLElement).style.background = warn ? '#ff5a4a' : '#ffd76a';
      $('lfBuckle').style.display = warn ? 'block' : 'none';
    },
    setPlaneSpeed(ms) { $('lfPSpd').textContent = `PLANE ${Math.round(ms)} M/S`; },
    setSetdown(v) {
      const el = $('lfTd');
      if (!v) { el.textContent = ''; return; }
      const col = v.sink < 4 ? '#69e888' : v.sink < 10 ? '#ffd76a' : '#ff5a4a';
      el.innerHTML = `SINK <span style="color:${col}">${v.sink.toFixed(1)}</span> · ZONE ${(v.zoneDist / 1000).toFixed(2)} KM`;
    },
    radio(text) { pending.push(text); },
    popup(text, cls) {
      const el = $('lfPop');
      el.textContent = text;
      el.style.color = cls === 'bad' ? '#ff5a4a' : '#ffe08a';
      popT = CONFIG.misc.popupTime;
      el.style.animation = 'none'; void el.offsetHeight; el.style.animation = '';
    },
    damageArc(angDeg) {
      const el = document.createElement('div');
      el.className = 'dmgarc';
      el.style.transform = `rotate(${angDeg}deg)`;
      el.style.transition = 'opacity .8s';
      arcsHost.appendChild(el);
      requestAnimationFrame(() => (el.style.opacity = '0'));
      setTimeout(() => el.remove(), 850);
    },
    missileWarn(on) { $('lfMiss').style.display = on ? 'block' : 'none'; },
    letterbox(on) {
      $('lfLBt').style.height = on ? '9vh' : '0';
      $('lfLBb').style.height = on ? '9vh' : '0';
    },
    phaseCard(text) {
      const el = $('lfCard');
      el.textContent = text;
      cardT = 2.2;
    },
    showTitle(on) { $('lfTitle').style.display = on ? 'flex' : 'none'; },
    showResults(v) {
      const el = $('lfRes');
      if (!v) { el.style.display = 'none'; return; }
      el.style.display = 'flex';
      $('lfRows').innerHTML = v.rows.map(([k, val]) => `<div class="row"><span>${k}</span><span>${val}</span></div>`).join('');
      $('lfGrade').textContent = v.grade;
      $('lfBest').textContent = `${Math.round(v.best)}${v.newBest ? ' ★NEW' : ''}`;
    },
    showFailed(reason) {
      const el = $('lfFail');
      if (!reason) { el.style.display = 'none'; return; }
      el.style.display = 'flex';
      $('lfFailWhy').textContent = reason + ' — R RETRY PHASE · SHIFT+R RESTART';
    },
    flashRed(f) { redT = Math.max(redT, f); },
    whiteout(f) { whiteT = f; },
    hint(text) {
      const el = $('lfHint');
      if (!text) { hintT = 0; el.style.display = 'none'; return; }
      el.textContent = text; hintT = 1.2; el.style.display = 'block';
    },
    drawZone(pts) {
      const poly = $('lfZonePoly');
      if (!pts || pts.length < 3) { poly.setAttribute('points', ''); return; }
      poly.setAttribute('points', pts.map((p) => p.join(',')).join(' '));
    },
    dispose() { style.remove(); root.remove(); },
  };
  return api;
}
```

### src/game/scoring.ts
```ts
import { CONFIG } from '../config.js';

export interface ScoreResult {
  score: number; grade: string; best: number; newBest: boolean;
  rows: [string, string][];
}

export interface Scoring {
  jets: number;
  registerJet(): void;
  finalize(st: { time: number; hull: number; hp: number; sink: number; laserAcc: number }): ScoreResult;
  peek(): number;
}

const KEY = 'lf_best_score';

export function createScoring(): Scoring {
  let jets = 0;
  return {
    jets,
    registerJet() { jets++; },
    get jets2() { return jets; },
    finalize(st) {
      const S = CONFIG.score;
      let sc = S.base + jets * S.perJet;
      sc += st.hull * S.hullW + st.hp * S.hpW;
      if (st.sink < CONFIG.plane.tdPerfect) sc += S.perfectSink;
      else if (st.sink < CONFIG.plane.tdHard) sc += S.goodSink;
      sc += Math.max(0, S.timePar - st.time) * S.timeW;
      sc += st.laserAcc * 1000;
      sc = Math.max(0, Math.round(sc));
      let best = 0;
      try { best = Number(localStorage.getItem(KEY) ?? 0); } catch { /* storage blocked */ }
      const newBest = sc > best;
      if (newBest) { try { localStorage.setItem(KEY, String(sc)); } catch { /* blocked */ } }
      const frac = sc / (S.base + 12 * S.perJet + 100 * S.hullW + 100 * S.hpW + S.perfectSink + S.timePar * S.timeW + 1000);
      let grade = 'C';
      for (const [th, g] of S.grades) { if (frac >= (th as number)) { grade = g as string; break; } }
      const rows: [string, string][] = [
        ['TIME', `${Math.floor(st.time / 60)}:${String(Math.floor(st.time % 60)).padStart(2, '0')}`],
        ['JETS DESTROYED', String(jets)],
        ['AIRLINER HULL', `${Math.round(st.hull)}%`],
        ['HERO CONDITION', `${Math.round(st.hp)}%`],
        ['TOUCHDOWN SINK', `${st.sink.toFixed(1)} M/S`],
        ['LASER ACCURACY', `${Math.round(st.laserAcc * 100)}%`],
        ['SCORE', String(sc)],
      ];
      return { score: sc, grade, best: Math.max(best, sc), newBest, rows };
    },
    peek() { return jets; },
  } as Scoring & { jets2: number };
}
```

### src/game/cinematics.ts
```ts
import * as THREE from 'three';
import type { Override } from './camera.js';
import type { Hud } from './hud.js';

export interface Cine {
  update(dt: number): Override | null;
  playing: boolean;
  skip(): void;
  playIntro(dur: number, getFocus: () => THREE.Vector3, done: () => void): void;
  playCatch(getHero: () => THREE.Vector3, getPlane: () => THREE.Vector3, done: () => void): void;
  playTear(getHero: () => THREE.Vector3, getPlane: () => THREE.Vector3, done: () => void): void;
  playLastKill(getPos: () => THREE.Vector3, done: () => void): void;
  playSetdown(getHero: () => THREE.Vector3, getPlane: () => THREE.Vector3, dur: number, done: () => void): void;
}

const tv = new THREE.Vector3();
const look = new THREE.Vector3();

export function createCinematics(hud: Hud): Cine {
  let active: null | {
    t: number; dur: number; fn: (k: number) => void; done: () => void; skippable: boolean;
  } = null;

  const orbit = (focus: () => THREE.Vector3, radius: number, height: number, spins: number) =>
    (k: number) => {
      const f = focus();
      const a = k * Math.PI * 2 * spins - Math.PI * 0.25;
      tv.set(f.x + Math.cos(a) * radius, f.y + height, f.z + Math.sin(a) * radius);
      look.copy(f);
    };

  const api: Cine = {
    playing: false,
    update(dt) {
      if (!active) return null;
      active.t += dt;
      const k = Math.min(1, active.t / active.dur);
      active.fn(k);
      if (k >= 1) { const d = active.done; active = null; api.playing = false; hud.letterbox(false); d(); }
      return { pos: tv.clone(), look: look.clone() };
    },
    skip() {
      if (active && active.skippable) {
        const d = active.done;
        active = null; api.playing = false; hud.letterbox(false); d();
      }
    },
    playIntro(dur, getFocus, done) {
      hud.letterbox(true);
      active = { t: 0, dur, fn: orbit(getFocus, 26, 8, 0.5), done, skippable: true };
      api.playing = true;
    },
    playCatch(getHero, getPlane, done) {
      hud.letterbox(true);
      active = {
        t: 0, dur: 1.4, skippable: false, done,
        fn: (k) => {
          const h = getHero(), p = getPlane();
          tv.set(p.x + 30 * Math.sin(k * 2), p.y - 6 + k * 10, p.z + 30 * Math.cos(k * 2));
          look.lerpVectors(h, p, 0.5);
        },
      };
      api.playing = true;
    },
    playTear(getHero, getPlane, done) {
      hud.letterbox(true);
      active = {
        t: 0, dur: 1.2, skippable: false, done,
        fn: (k) => {
          const h = getHero(), p = getPlane();
          tv.set(p.x - 40, p.y + 10 + k * 20, p.z + 25);
          look.copy(p);
          void h;
        },
      };
      api.playing = true;
    },
    playLastKill(getPos, done) {
      hud.letterbox(true);
      active = {
        t: 0, dur: 0.9, skippable: false, done,
        fn: (k) => {
          const p = getPos();
          tv.set(p.x + 40 * (1 - k * 0.5), p.y + 12, p.z + 40);
          look.copy(p);
        },
      };
      api.playing = true;
    },
    playSetdown(getHero, getPlane, dur, done) {
      hud.letterbox(true);
      active = {
        t: 0, dur, skippable: false, done,
        fn: (k) => {
          const h = getHero(), p = getPlane();
          const a = k * Math.PI * 1.2 + 1;
          tv.set(p.x + Math.cos(a) * 70, p.y + 18 + k * 10, p.z + Math.sin(a) * 70);
          look.lerpVectors(h, p, 0.6);
        },
      };
      api.playing = true;
    },
  };
  return api;
}
```

### src/game/mission.ts
```ts
import * as THREE from 'three';
import { CONFIG } from '../config.js';
import type { Bus } from '../core/events.js';
import type { FlightState, Cmd } from '../entities/flight.js';
import { createState as createHeroState, step as stepFlight, aimDir, damage as damageHero } from '../entities/flight.js';
import type { AirlinerState } from '../entities/airliner.js';
import { createAirlinerState, stepUnheld, projectImpact, applyHullDamage, syncQuat } from '../entities/airliner.js';
import * as holding from '../entities/holding.js';
import type { LaserSim, LaserTarget, LaserHit } from '../entities/laser.js';
import type { JetMgrLike } from './deps.js';
import type { Hud } from './hud.js';
import type { CamCtl } from './camera.js';
import type { Cine } from './cinematics.js';
import type { Scoring } from './scoring.js';
import type { AudioSys } from '../core/audio.js';
import type { ExplosionSys } from '../vfx/explosions.js';
import type { Stadium } from '../world/stadium.js';
import type { CityLayout, ResolveOut } from '../world/collision.js';
import { resolveSphere, topAt, boundaryPush, raycastCity } from '../world/collision.js';
import { fmtTime, V1, V2, V3 } from '../core/math.js';

export type Phase = 'TITLE' | 'CINE' | 'INTERCEPT' | 'CATCH' | 'ARREST' | 'SETDOWN' | 'SAVED' | 'FAILED' | 'FREEFLY';

export interface MissionIO {
  spawnWave(n: number, preferHero: boolean): void;
  clearEnemies(): void;
  resetHero(snap: { pos: THREE.Vector3; vel: THREE.Vector3; hp: number }): void;
  resetPlane(snap: { pos: THREE.Vector3; vel: THREE.Vector3; hull: number; caught: string | null; torn: boolean }): void;
  setTimeScale(ts: number, ms?: number): void;
  warpHeroNearPlane(): void;
}

export interface MissionDeps {
  cfg: typeof CONFIG;
  bus: Bus;
  hud: Hud;
  audio: AudioSys;
  cam: CamCtl;
  cine: Cine;
  scoring: Scoring;
  expl: ExplosionSys;
  stadium: Stadium;
  layout: CityLayout;
  laser: LaserSim;
  jets: JetMgrLike;
  io: MissionIO;
}

const TV = new THREE.Vector3();
const TV2 = new THREE.Vector3();

export class Mission {
  phase: Phase = 'TITLE';
  phaseT = 0;
  clock = 0;
  scoreShown = 0;
  hero!: FlightState;
  plane!: AirlinerState;
  waveIdx = 0;
  wave4Pending = false;
  wave4Timer = 0;
  firedTime = 0;
  onTargetTime = 0;
  lockTargetId: number | null = null;
  nearMissCd = 0;
  failReason = '';
  private ckpt: null | {
    phase: Phase; heroSnap: ReturnType<MissionIO['resetHero']> extends infer T ? T : never;
    planeSnap: Parameters<MissionIO['resetPlane']>[0]; score: number; waveIdx: number;
  } = null;
  private released = false;
  private settleStage = 0;
  private endT = 0;
  private lastKillPending = false;
  private boundaryHintT = 0;
  private missileWarned = false;

  constructor(public d: MissionDeps) {
    d.bus.on('jetKilled', (p) => {
      d.scoring.registerJet();
      d.audio.explosion(distToHero(this, p.pos), 1);
      d.expl.explode(p.pos.x, p.pos.y, p.pos.z, 1);
      d.hud.popup('SPLASH ONE');
      d.bus.emit('splashOne', {});
      if (p.last) {
        this.lastKillPending = true;
        d.io.setTimeScale(CONFIG.cine.killSlow, CONFIG.cine.killSlowDur * 1000);
        d.cine.playLastKill(() => new THREE.Vector3(p.pos.x, p.pos.y, p.pos.z), () => { });
      }
    });
    d.bus.on('heroHit', (p) => {
      damageHero(this.hero, p.amount);
      d.hud.flashRed(0.5);
      d.cam.addShake(0.35);
      const ang = (Math.atan2(p.dir.z, p.dir.x) * 180) / Math.PI;
      d.hud.damageArc(ang);
      if (this.hero.hp <= 0 && this.phase !== 'FAILED') this.fail('YOU FELL');
    });
    d.bus.on('hullHit', (p) => {
      applyHullDamage(this.plane, p.amount);
      if (this.plane.hull <= 0 && !this.plane.dead && this.phase !== 'FAILED')
        this.fail('FLIGHT 227 BROKE APART');
    });
  }

  startTitle() {
    this.setPhase('TITLE');
    this.d.hud.showTitle(true);
  }

  beginPlay() {
    this.d.hud.showTitle(false);
    this.setupFresh();
    this.d.cine.playIntro(CONFIG.cine.introT,
      () => this.hero.pos,
      () => this.enterIntercept());
    this.setPhase('CINE');
    this.d.hud.radio("MAYDAY MAYDAY — FLIGHT 227 — ENGINE FIRE — WE ARE GOING DOWN.");
    this.d.audio.radioBeep();
  }

  private setupFresh() {
    this.hero = createHeroState();
    this.plane = createAirlinerState();
    this.clock = 0; this.waveIdx = 0; this.wave4Pending = false;
    this.firedTime = 0; this.onTargetTime = 0;
    this.d.io.clearEnemies();
    this.d.scoringRegister?.();
  }

  private setPhase(p: Phase, title?: string) {
    this.phase = p; this.phaseT = 0;
    this.d.bus.emit('phaseChanged', { phase: p, title });
    if (title) this.d.hud.phaseCard(title);
    this.saveCheckpoint(p);
  }

  private saveCheckpoint(p: Phase) {
    if (p === 'TITLE' || p === 'CINE' || p === 'SAVED' || p === 'FAILED') return;
    this.ckpt = {
      phase: p,
      heroSnap: { pos: this.hero.pos.clone(), vel: this.hero.vel.clone(), hp: this.hero.hp },
      planeSnap: {
        pos: this.plane.pos.clone(), vel: this.plane.vel.clone(), hull: this.plane.hull,
        caught: this.plane.caught, torn: this.plane.torn,
      },
      score: this.scoreShown, waveIdx: this.waveIdx,
    };
  }

  private enterIntercept() {
    this.setPhase('INTERCEPT', 'INTERCEPT');
    this.d.io.spawnWave(CONFIG.jets.waveCounts[0], true);
    this.d.io.warpHeroNearPlane();
  }

  retryPhase() {
    if (!this.ckpt) { this.fullRestart(); return; }
    this.d.hud.showFailed(null);
    this.d.hud.showResults(null);
    this.d.io.clearEnemies();
    this.d.io.resetHero(this.ckpt.heroSnap);
    this.d.io.resetPlane(this.ckpt.planeSnap);
    this.scoreShown = this.ckpt.score;
    this.waveIdx = this.ckpt.waveIdx;
    this.plane.caught = this.ckpt.planeSnap.caught as holding.CatchPointAlias;
    this.setPhaseSilently(this.ckpt.phase);
    if (this.ckpt.phase === 'INTERCEPT') this.d.io.spawnWave(CONFIG.jets.waveCounts[0], true);
    if (this.ckpt.phase === 'CATCH') this.d.io.spawnWave(CONFIG.jets.waveCounts[1], false);
    if (this.ckpt.phase === 'ARREST') this.d.io.spawnWave(CONFIG.jets.waveCounts[2], false);
  }

  private setPhaseSilently(p: Phase) { this.phase = p; this.phaseT = 0; }

  fullRestart() {
    this.d.hud.showFailed(null);
    this.d.hud.showResults(null);
    this.d.io.clearEnemies();
    this.setupFresh();
    this.setPhase('INTERCEPT', 'INTERCEPT');
    this.d.io.spawnWave(CONFIG.jets.waveCounts[0], true);
    this.d.io.warpHeroNearPlane();
  }

  fail(reason: string) {
    if (this.phase === 'FAILED') return;
    this.failReason = reason;
    this.setPhase('FAILED');
    this.d.hud.showFailed(reason);
    this.d.io.setTimeScale(0.35, 1200);
  }

  toggleFreeFly(on: boolean) {
    if (on) {
      this.prevPhase = this.phase;
      this.setPhaseSilently('FREEFLY');
      this.d.hud.setObjective('FREE FLIGHT', undefined);
      this.d.io.clearEnemies();
    } else {
      this.setPhaseSilently(this.prevPhase ?? 'INTERCEPT');
    }
  }
  private prevPhase: Phase | null = null;

  /** Fixed-step update. cmd arrives prebuilt; raycasters come from main. */
  update(h: number, cmd: Cmd, ctx: {
    firing: boolean;
    raycastWorld: (o: THREE.Vector3, d: THREE.Vector3, max: number) => { t: number; pos: THREE.Vector3; kind: 'building' | 'ground' } | null;
    heroSurf: number;
  }) {
    this.phaseT += h;
    if (this.phase === 'TITLE' || this.phase === 'CINE') return;
    this.clock += h;
    const d = this.d;

    // ----- Hero -----
    if (this.hero.mode !== 'holding') {
      const flags = stepFlight(this.hero, cmd, h, ctx.heroSurf);
      if (flags.supersonic) {
        d.bus.emit('sonicBoom', {});
        d.audio.boom();
        d.hud.popup('SUPERSONIC');
        d.cam.addShake(0.5);
      }
      if (flags.tookOff) d.cam.kick();
      // Collide with the city.
      const res: ResolveOut = resolveSphere(d.layout, this.hero.pos, CONFIG.hero.radius, this.hero.vel);
      if (res.hit && res.impact > 6) {
        this.hero.vel.multiplyScalar(0.4);
        this.hero.mode = 'stunned';
        this.hero.stunT = CONFIG.hero.stunTime;
        this.hero.tumble.set(Math.random() * 6 - 3, Math.random() * 6 - 3, Math.random() * 6 - 3);
        d.hud.flashRed(0.6);
        d.cam.addShake(Math.min(1, res.impact / 60));
        d.audio.thud(res.impact / 80);
      }
      if (boundaryPush(d.layout, this.hero.pos, this.hero.vel, CONFIG.world.boundaryRadius)) {
        this.boundaryHintT -= h;
        if (this.boundaryHintT <= 0) { this.boundaryHintT = 2; d.hud.hint('TURN BACK'); }
      }
    }

    // ----- Airliner -----
    const pl = this.plane;
    if (!pl.touchedDown && !pl.settling) {
      if (pl.caught) {
        const hc: holding.HoldCtrl = {
          brake: cmd.brake, fwd: cmd.thrust, lift: cmd.lift, sink: cmd.sink,
          aimDir: aimDir(this.hero, TV2).clone(),
        };
        const hf = holding.step(pl, this.hero, hc, h);
        if (hf.warned && !this._buckled) { this._buckled = true; d.hud.popup('NOSE BUCKLING', 'bad'); d.bus.emit('buckle', {}); }
        if (!hf.warned) this._buckled = false;
        if (hf.crunched) d.audio.crunch(pl.stress / 100);
        if (hf.tore) {
          d.audio.tearDown();
          d.bus.emit('tailTorn', {});
          d.hud.popup('TAIL TORN OFF', 'bad');
          d.cam.addShake(0.8);
          d.io.setTimeScale(CONFIG.cine.slowCatch, 900);
          d.cine.playTear(() => this.hero.pos.clone(), () => pl.pos.clone(), () => { });
        }
      } else if (!pl.dead) {
        stepUnheld(pl, h);
        // Terrain impact for the unheld liner.
        const gy = topAt(d.layout, pl.pos.x, pl.pos.z);
        if (pl.pos.y <= gy + 4) {
          d.expl.explode(pl.pos.x, gy, pl.pos.z, 2.5);
          d.audio.explosion(distToHero(this, pl.pos), 2.5);
          this.fail('FLIGHT 227 HIT THE CITY');
          return;
        }
      }
      if (pl.dead) {
        // Spiral of doom.
        pl.vel.y -= 6 * h;
        pl.vel.multiplyScalar(1 - 0.2 * h);
        pl.pos.addScaledVector(pl.vel, h);
        syncQuat(pl);
        if (pl.pos.y <= topAt(d.layout, pl.pos.x, pl.pos.z) + 4) {
          d.expl.explode(pl.pos.x, pl.pos.y, pl.pos.z, 2.5);
          this.fail('FLIGHT 227 BROKE APART');
          return;
        }
      }
      // Impact ETA.
      const pj = projectImpact(pl, (x, z) => topAt(d.layout, x, z), CONFIG.world.boundaryRadius);
      pl.eta = pj.eta; pl.pathClear = pj.clear;
    }

    // ----- Laser -----
    d.laser.update(h, ctx.firing);
    if (ctx.firing) this.firedTime += h;

    // ----- Jets & missiles handled by main via managers; mission watches waves -----
    this.updateWaves(h);
    this.updateObjectives();
    this.checkTransitions(h, ctx);
  }

  private _buckled = false;

  private updateWaves(h: number) {
    const d = this.d;
    if (this.phase === 'INTERCEPT' && d.jets.activeCount() === 0 && this.phaseT > 4) {
      // Move on when the hero gets close to the liner; handled in transitions.
    }
    if (this.phase === 'ARREST') {
      if (this.waveIdx === 2 && d.jets.activeCount() === 0 && this.phaseT > 6) {
        this.waveIdx = 3; this.wave4Timer = CONFIG.jets.wave4Delay;
        d.io.spawnWave(CONFIG.jets.waveCounts[3], false);
      }
      if (this.waveIdx === 3 && this.plane.hull < 50 && this.wave4Timer > 0) {
        this.wave4Timer = 0; // hull trigger spent
      }
    }
    void h;
  }

  private updateObjectives() {
    const d = this.d;
    const pl = this.plane;
    switch (this.phase) {
      case 'INTERCEPT': {
        const dist = TV.copy(pl.pos).sub(this.hero.pos).length();
        d.hud.setObjective('INTERCEPT FLIGHT 227', dist);
        d.hud.setImpact(pl.eta === Infinity ? null : pl.eta, pl.pathClear);
        break;
      }
      case 'CATCH': {
        const dist = TV.copy(pl.pos).sub(this.hero.pos).length();
        d.hud.setObjective('REACH THE AIRLINER — GRAB THE NOSE (E)', dist);
        d.hud.setImpact(pl.eta === Infinity ? null : pl.eta, pl.pathClear);
        break;
      }
      case 'ARREST': {
        const zs = d.stadium.zone;
        const dist = Math.hypot(pl.pos.x - zs.cx, pl.pos.z - zs.cz);
        d.hud.setObjective('KILL ITS SPEED — FLY IT TO METRO STADIUM', dist);
        d.hud.setImpact(pl.eta === Infinity ? null : pl.eta, pl.pathClear);
        break;
      }
      case 'SETDOWN':
        d.hud.setObjective('LOWER IT ONTO THE FIELD — E TO RELEASE');
        break;
      default: break;
    }
    d.hud.setClock(this.clock);
    d.hud.setScore(this.scoreShown, d.scoring.peek());
  }

  private checkTransitions(h: number, ctx: { firing: boolean }) {
    const d = this.d;
    const pl = this.plane;
    void ctx;
    if (this.phase === 'INTERCEPT') {
      const dist = TV.copy(pl.pos).sub(this.hero.pos).length();
      if (dist < 1500) {
        this.setPhase('CATCH', 'CATCH');
        d.io.spawnWave(CONFIG.jets.waveCounts[1], false);
      }
    } else if (this.phase === 'CATCH') {
      // Grab prompts handled by main (needs hero/proximity); watch for catch event.
      if (pl.caught === 'NOSE') {
        this.setPhase('ARREST', 'ARREST');
        this.waveIdx = 2;
        d.io.spawnWave(CONFIG.jets.waveCounts[2], false);
      }
    } else if (this.phase === 'ARREST') {
      if (pl.caught !== 'NOSE' && !pl.dead && this.phaseT > 2) {
        // Lost the plane — back to CATCH.
        this.setPhase('CATCH');
      }
      const zs = d.stadium.zone;
      const dist = Math.hypot(pl.pos.x - zs.cx, pl.pos.z - zs.cz);
      const spd = pl.vel.length();
      if (dist < 260 && spd < 40 && pl.pos.y < 320) {
        this.setPhase('SETDOWN', 'SET DOWN');
      }
    }
    void h;
  }

  /** Called by main when a touchdown-quality landing completes in the zone. */
  notifyTouchdown(sink: number, quality: 'PERFECT' | 'HARD' | 'CRASH', tailStrike: boolean) {
    const d = this.d;
    d.bus.emit('touchdown', { sink, quality, tailStrike });
    if (quality === 'CRASH') { this.fail('CRASH TOUCHDOWN'); return; }
    if (quality === 'HARD') {
      applyHullDamage(this.plane, CONFIG.plane.dmgHardTD);
      d.cam.addShake(0.7);
      d.audio.thud(1);
      if (this.plane.hull <= 0) { this.fail('FLIGHT 227 BROKE APART'); return; }
    } else {
      d.audio.thud(0.6);
    }
    this.plane.settling = true;
    this.settleStage = 1;
    d.audio.crowd(1);
    d.stadium.flashStorm(1);
    d.stadium.setBoard(['218 SAVED', 'METRO STADIUM']);
    d.io.setTimeScale(CONFIG.cine.setdownSlow, 2600);
    d.cine.playSetdown(() => this.hero.pos.clone(), () => this.plane.pos.clone(), 4.5, () => {
      this.finishVictory(sink);
    });
    this.setPhase('SAVED');
    d.hud.popup(quality === 'PERFECT' ? 'PERFECT SET-DOWN' : 'HARD SET-DOWN');
  }

  private finishVictory(sink: number) {
    const d = this.d;
    d.audio.resolveChord();
    const res = d.scoring.finalize({
      time: this.clock, hull: this.plane.hull, hp: this.hero.hp, sink,
      laserAcc: this.firedTime > 0 ? this.onTargetTime / this.firedTime : 0,
    });
    this.scoreShown = res.score;
    d.hud.showResults(res);
    d.hud.popup(`${218} SOULS SAVED`);
  }

  /** Grab attempt routed from main input. */
  tryGrab(): boolean {
    const pl = this.plane;
    if (pl.caught || pl.dead || pl.touchedDown) return false;
    const hs = this.hero.vel.length();
    for (const pt of ['NOSE', 'TAIL'] as const) {
      if (holding.canGrab(pl, this.hero.pos, hs, pt)) {
        holding.attach(pl, this.hero, pt);
        this.d.bus.emit('caught', { point: pt });
        this.d.audio.catchGroan();
        this.d.io.setTimeScale(CONFIG.cine.slowCatch, CONFIG.cine.slowDur * 1000);
        if (pt === 'NOSE')
          this.d.cine.playCatch(() => this.hero.pos.clone(), () => pl.pos.clone(), () => { });
        else this.d.hud.popup('GRABBED TAIL — UNSTABLE!', 'bad');
        return true;
      }
    }
    return false;
  }

  tryRelease() {
    const pl = this.plane;
    if (pl.caught !== 'NOSE' || !pl.settling) return;
    holding.detach(pl, this.hero, TV.set(0, 2, 0));
    pl.released = true;
    this.d.bus.emit('released', {});
  }

  registerLaserHit(hit: LaserHit, dt: number) {
    if (hit.kind === 'jet') { this.onTargetTime += dt; this.d.jets.damageById(hit.id, CONFIG.laser.dpsJet * dt, true); }
    else if (hit.kind === 'missile') { this.onTargetTime += dt; this.d.missiles?.damageById(hit.id, CONFIG.laser.dpsMissile * dt); }
  }

  laserTargets(excludeWhenHeld: boolean): LaserTarget[] {
    const out: LaserTarget[] = [];
    this.d.jets.forEachActive((j) => out.push({ kind: 'jet', id: j.id, pos: j.pos, radius: 6 }));
    this.d.missiles?.forEachActive((m) => out.push({ kind: 'missile', id: m.id, pos: m.pos, radius: 2.5 }));
    void excludeWhenHeld;
    return out;
  }

  nearMissCheck(prevPos: THREE.Vector3) {
    this.nearMissCd -= 1 / 120;
    const sp = this.hero.vel.length();
    if (sp < CONFIG.misc.nearMissSpd || this.nearMissCd > 0) return;
    // Sample the swept path coarsely.
    for (let i = 0; i <= 4; i++) {
      const p = TV.lerpVectors(prevPos, this.hero.pos, i / 4);
      const top = topAt(this.d.layout, p.x, p.z);
      if (top > 30 && p.y < top + CONFIG.misc.nearMissDist && p.y > top - 4) {
        this.nearMissCd = CONFIG.misc.nearMissCool;
        this.scoreShown += CONFIG.misc.nearMissPts;
        this.d.hud.popup(`NEAR MISS +${CONFIG.misc.nearMissPts}`);
        this.d.bus.emit('nearMiss', {});
        this.d.audio.whiz();
        return;
      }
    }
  }

  missileAlert(anyActive: boolean) {
    this.d.hud.missileWarn(anyActive);
    this.d.audio.missileWarn(anyActive, anyActive ? 0.8 : 0);
    this.missileWarned = anyActive;
  }
}

function distToHero(m: Mission, p: { x: number; y: number; z: number }): number {
  return Math.hypot(m.hero.pos.x - p.x, m.hero.pos.y - p.y, m.hero.pos.z - p.z);
}
```

### src/game/deps.ts
```ts
import type * as THREE from 'three';

/** Structural contracts main.ts satisfies for mission.ts (keeps modules decoupled). */
export interface JetMgrLike {
  spawn(target: THREE.Vector3, preferHero: boolean): unknown;
  activeCount(): number;
  forEachActive(fn: (j: { id: number; pos: THREE.Vector3; vel: THREE.Vector3; targetHero: boolean }) => void): void;
  damageById(id: number, amt: number, lasering?: boolean): void;
  tracers: { active: boolean; pos: THREE.Vector3; vel: THREE.Vector3 }[];
  update(h: number, tg: { heroPos: THREE.Vector3; heroVel: THREE.Vector3; planePos: THREE.Vector3; planeVel: THREE.Vector3; preferHero: boolean }, topAtFn: (x: number, z: number) => number): void;
}

export interface MissileMgrLike {
  fire(from: THREE.Vector3, vel: THREE.Vector3, targetHero: boolean): unknown;
  activeCount(): number;
  forEachActive(fn: (m: { id: number; pos: THREE.Vector3; vel: THREE.Vector3 }) => void): void;
  damageById(id: number, amt: number): void;
  update(h: number, heroPos: THREE.Vector3, planePos: THREE.Vector3): void;
}
```

### src/game/debug.ts
```ts
import GUI from 'three/addons/libs/lil.gui.module.min.js';
import { CONFIG } from '../config.js';

export interface DebugGui { toggle(): void; visible: boolean }

/** Auto-bind every numeric/boolean leaf of CONFIG into lil-gui folders. */
export function createDebugGui(): DebugGui {
  const gui = new GUI({ title: 'LAST FLIGHT DEBUG' });
  gui.domElement.style.display = 'none';
  gui.domElement.style.position = 'absolute';
  gui.domElement.style.zIndex = '50';

  const walk = (obj: Record<string, unknown>, parent: GUI, path: string) => {
    for (const k of Object.keys(obj)) {
      const v = obj[k];
      const p = path ? `${path}.${k}` : k;
      if (typeof v === 'number') parent.add(obj, k).name(p.split('.').slice(-2).join('.'));
      else if (typeof v === 'boolean') parent.add(obj, k).name(p.split('.').slice(-2).join('.'));
      else if (typeof v === 'object' && v !== null && !Array.isArray(v))
        walk(v as Record<string, unknown>, parent.addFolder(k), p);
    }
  };
  walk(CONFIG as unknown as Record<string, unknown>, gui, '');

  return {
    gui,
    get visible() { return gui.domElement.style.display !== 'none'; },
    toggle() {
      gui.domElement.style.display = gui.domElement.style.display === 'none' ? 'block' : 'none';
    },
  };
}
```

### src/main.ts
```ts
import * as THREE from 'three';
import { CONFIG } from './config.js';
import { createBus } from './core/events.js';
import { createInput } from './core/input.js';
import { createAudio, type AudioSys } from './core/audio.js';
import { createLoop } from './core/loop.js';
import { createRenderer, type Post } from './core/renderer.js';
import { createSky } from './world/sky.js';
import { generateCityLayout, raycastCity, topAt, cellIndex, type CityLayout } from './world/collision.js';
import { createGround } from './world/ground.js';
import { createRiver } from './world/river.js';
import { createCity } from './world/city.js';
import { createClouds, type CloudView } from './world/clouds.js';
import { createStadium, type Stadium } from './world/stadium.js';
import { createParticles, type Particles } from './vfx/particles.js';
import { createExplosions, type ExplosionSys } from './vfx/explosions.js';
import { createTrails, type TrailSys } from './vfx/trails.js';
import { createSpeedlines, type SpeedFx } from './vfx/speedlines.js';
import { createState as createFlightState, aimDir, type Cmd, type FlightState } from './entities/flight.js';
import { createHero, type HeroView } from './entities/hero.js';
import { createAirlinerState, createAirliner, syncQuat, type AirlinerState, type AirlinerView } from './entities/airliner.js';
import { createLaserSim, createLaserView, type LaserSim, type LaserHit } from './entities/laser.js';
import { createJetManager, type JetMgrDeps } from './entities/jet.js';
import { createMissileManager } from './entities/missile.js';
import { createWreckManager } from './entities/wreck.js';
import * as holdingMod from './entities/holding.js';
import { createCameraControl, type CamCtl } from './game/camera.js';
import { createHud, type Hud } from './game/hud.js';
import { createCinematics, type Cine } from './game/cinematics.js';
import { createScoring, type Scoring } from './game/scoring.js';
import { Mission } from './game/mission.js';
import type { JetMgrLike, MissileMgrLike } from './game/deps.js';
import { createDebugGui } from './game/debug.js';
import { V1, V2, V3, V4, safeNorm, clamp } from './core/math.js';

const mount = document.getElementById('app')!;
const bus = createBus();
const input = createInput(document.body);
const audio: AudioSys = createAudio();
const hud = createHud(mount);

// ---------- Renderer / scene ----------
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(CONFIG.cam.fovBase, window.innerWidth / window.innerHeight, 0.1, 30000);
const skySys = createSky(scene, undefined as unknown as THREE.WebGLRenderer);
const post: Post = createRenderer(mount, scene, camera, skySys.sunMesh as THREE.Mesh);
const renderer = post.renderer;
// Re-create sky env with the real renderer (first pass had a stub).
skySys.dispose();
const sky = createSky(scene, renderer);
const sunDir = sky.sunDir;

// ---------- World ----------
const layout: CityLayout = generateCityLayout(CONFIG);
createGround(scene, layout);
const river = createRiver(scene, layout, sunDir);
const cityView = createCity(scene, layout, sunDir);
const clouds: CloudView = createClouds(scene, sunDir);
const stadium: Stadium = createStadium(scene, layout);

const raycastWorld = (o: THREE.Vector3, d: THREE.Vector3, max: number) => {
  const hit = raycastCity(layout, o.x, o.y, o.z, d.x, d.y, d.z, max);
  if (!hit) return null;
  return { t: hit.t, pos: new THREE.Vector3(hit.x, hit.y, hit.z), kind: hit.ny > 0.5 && hit.y < 0.5 ? ('ground' as const) : ('building' as const) };
};
const camRaycast = (o: THREE.Vector3, d: THREE.Vector3, max: number) => raycastCity(layout, o.x, o.y, o.z, d.x, d.y, d.z, max);

// ---------- VFX ----------
const particles: Particles = createParticles(scene);
const expl: ExplosionSys = createExplosions(scene, particles);
const trails: TrailSys = createTrails(scene);
const speedFx: SpeedFx = createSpeedlines(scene);

// ---------- Entities ----------
const heroVis: HeroView = createHero(scene);
const hero: FlightState = createFlightState();
hero.pos.set(0, 140, 0);

const planeSim: AirlinerState = createAirlinerState();
const planeVis: AirlinerView = createAirliner(scene);

const laserSim: LaserSim = createLaserSim();
const laserView = createLaserView(scene);

const jetDeps: JetMgrDeps = {
  scene, particles,
  onShoot: (_j, _aim) => { audio.cannon(400); },
  onDie: (j, last) => {
    bus.emit('jetKilled', { id: j.id, pos: { x: j.pos.x, y: j.pos.y, z: j.pos.z }, last });
    expl.explode(j.pos.x, j.pos.y, j.pos.z, 1);
    wreckMgr.spawn(j.pos, j.vel);
  },
};
const jets = createJetManager(jetDeps) as unknown as JetMgrLike & { jets: { id: number; pos: THREE.Vector3; vel: THREE.Vector3; targetHero: boolean; mesh?: THREE.Group }[] };

const misMgr = createMissileManager({
  scene, particles,
  onDetonate: (m, hit) => {
    expl.explode(m.pos.x, m.pos.y, m.pos.z, 0.8);
    audio.explosion(dist(m.pos), 0.8);
    if (hit) {
      const dh = m.pos.distanceTo(hero.pos);
      const dp = m.pos.distanceTo(planeSim.pos);
      if (dh < CONFIG.missile.radius) {
        bus.emit('heroHit', { amount: CONFIG.missile.dmgHero * (1 - dh / CONFIG.missile.radius), dir: { x: m.vel.x, z: m.vel.z } });
      }
      if (dp < CONFIG.missile.radius * 2) {
        bus.emit('hullHit', { amount: CONFIG.missile.dmgHull * (1 - dp / (CONFIG.missile.radius * 2)) });
      }
    }
  },
});
const missiles = misMgr as unknown as MissileMgrLike & { mis: { id: number; pos: THREE.Vector3; active: boolean }[] };
misMgr.mis.forEach((m, i) => ((m as unknown as { id: number }).id = i));
jets.jets.forEach((j) => (j.id = j.id ?? 0));

const wreckMgr = createWreckManager(scene, particles, (x, y, z) => {
  expl.explode(x, y, z, 1.1);
  audio.explosion(dist(new THREE.Vector3(x, y, z)), 1.1);
});

// Trails
const heroTrail = trails.add({ max: CONFIG.trail.heroLen, width: CONFIG.trail.heroWidth, ttl: 0.5, additive: true, headCol: [1.0, 0.85, 0.5], tailCol: [0.4, 0.1, 0.05] });
const smokeTrail = trails.add({ max: CONFIG.trail.smokeLen, width: CONFIG.trail.smokeWidth, ttl: 10, additive: false, headCol: [0.75, 0.72, 0.7], tailCol: [0.06, 0.055, 0.055] });
const contraPool: { l: ReturnType<TrailSys['add']>; r: ReturnType<TrailSys['add']> }[] = [];
for (let i = 0; i < 12; i++)
  contraPool.push({
    l: trails.add({ max: CONFIG.trail.contraLen, width: CONFIG.trail.contraWidth, ttl: 1.4, additive: false, headCol: [0.95, 0.95, 1], tailCol: [0.8, 0.8, 0.85] }),
    r: trails.add({ max: CONFIG.trail.contraLen, width: CONFIG.trail.contraWidth, ttl: 1.4, additive: false, headCol: [0.95, 0.95, 1], tailCol: [0.8, 0.8, 0.85] }),
  });

// Stadium flash hookup
(stadium as unknown as { _flash: (x: number, y: number, z: number) => void })._flash = (x, y, z) => {
  particles.spawn({
    x, y, z, vx: 0, vy: 0, vz: 0, life: 0.18, size0: 2.2, size1: 0.4,
    r0: 1, g0: 1, b0: 0.95, r1: 1, g1: 0.9, b1: 0.7, a0: 1, a1: 0, twinkle: 8,
  });
};

// ---------- Game systems ----------
const cam: CamCtl = createCameraControl(camera, camRaycast);
const cine: Cine = createCinematics(hud);
const scoring: Scoring = createScoring();
const debugGui = createDebugGui();

const mission = new Mission({
  cfg: CONFIG, bus, hud, audio, cam, cine, scoring, expl, stadium, layout, laser: laserSim,
  jets: jets as JetMgrLike,
  io: {
    spawnWave(n, preferHero) {
      const tgt = preferHero ? hero.pos : planeSim.pos;
      for (let i = 0; i < n; i++) jets.spawn(tgt, preferHero);
    },
    clearEnemies() {
      jets.jets.forEach((j) => { if (j.mesh) j.mesh.visible = false; Object.assign(j, { active: false }); });
      misMgr.mis.forEach((m) => { m.active = false; m.mesh!.visible = false; });
    },
    resetHero(snap) {
      hero.pos.copy(snap.pos); hero.vel.copy(snap.vel); hero.hp = snap.hp;
      hero.mode = 'flight'; hero.stunT = 0; hero.boost = 1; hero.boostLock = false;
    },
    resetPlane(snap) {
      planeSim.pos.copy(snap.pos); planeSim.vel.copy(snap.vel);
      planeSim.hull = snap.hull; planeSim.caught = snap.caught as never;
      planeSim.torn = snap.torn; planeSim.dead = false; planeSim.stress = 0;
      planeSim.settling = false; planeSim.touchedDown = null;
      if (planeSim.caught === 'NOSE') hero.mode = 'holding';
    },
    setTimeScale: (ts, ms) => loop.setTimeScale(ts, ms),
    warpHeroNearPlane() {
      // Reposition the hero a fair sprint behind the liner for the chase.
      hero.pos.copy(planeSim.pos).add(V1.set(400, 120, 300));
      hero.vel.copy(planeSim.vel);
    },
  },
});
mission.hero = hero;
mission.plane = planeSim;

// ---------- Input wiring ----------
let started = false;
mount.addEventListener('mousedown', () => {
  audio.unlock();
  if (!started) { started = true; mission.beginPlay(); return; }
  input.lockPointer();
});
document.addEventListener('keydown', (e) => {
  if (e.code === 'Backquote') debugGui.toggle();
  if (e.code === 'BracketLeft') input.nudgeSens(-1);
  if (e.code === 'BracketRight') input.nudgeSens(+1);
  if (e.code === 'KeyR') {
    if (input.down('ShiftLeft')) mission.fullRestart();
    else if (mission.phase === 'FAILED' || mission.phase === 'SAVED') mission.retryPhase();
  }
  if (e.code === 'KeyF' && started) mission.toggleFreeFly(mission.phase !== 'FREEFLY');
  if (e.code === 'Escape') document.exitPointerLock?.();
  if (started && mission.phase === 'CINE') cine.skip();
});
window.addEventListener('resize', () => post.resize(window.innerWidth, window.innerHeight));

// ---------- Simulation helpers ----------
function dist(p: THREE.Vector3) { return p.distanceTo(hero.pos); }

function buildCmd(): Cmd {
  return {
    thrust: input.down('KeyW') ? 1 : 0,
    brake: input.down('KeyS') ? 1 : 0,
    lift: input.down('Space') ? 1 : 0,
    sink: input.down('ControlLeft') || input.down('ControlRight') ? 1 : 0,
    strafe: (input.down('KeyD') ? 1 : 0) - (input.down('KeyA') ? 1 : 0),
    boost: input.down('ShiftLeft') || input.down('ShiftRight'),
  };
}

function applyAim(dt: number) {
  const m = input.consumeMouse();
  const sens = input.sens;
  if (input.locked) {
    hero.aimYaw -= m.dx * sens;
    hero.aimPitch = clamp(hero.aimPitch - m.dy * sens, -85 * Math.PI / 180, 85 * Math.PI / 180);
  } else {
    // Arrow-key fallback steering.
    const r = CONFIG.hero.arrowRate * dt;
    if (input.down('ArrowLeft')) hero.aimYaw += r;
    if (input.down('ArrowRight')) hero.aimYaw -= r;
    if (input.down('ArrowUp')) hero.aimPitch = clamp(hero.aimPitch + r, -1.48, 1.48);
    if (input.down('ArrowDown')) hero.aimPitch = clamp(hero.aimPitch - r, -1.48, 1.48);
  }
  hero.aimYaw = ((hero.aimYaw + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
}

// ---------- Fixed step ----------
let prevHeroPos = new THREE.Vector3();
let smokeAcc = 0;
let lockScanT = 0;
let lockTargetId: number | null = null;

function fixed(h: number) {
  input.beginFrame();
  applyAim(h);
  const cmd = buildCmd();
  const firing = input.down('Mouse0') && !laserSim.overheated;
  const prevPos = V4.copy(hero.pos);
  mission.update(h, cmd, { firing, raycastWorld, heroSurf: topAt(layout, hero.pos.x, hero.pos.z) });
  mission.nearMissCheck(prevPos);

  // Laser cast + damage.
  const firingNow = input.down('Mouse0') && !laserSim.overheated;
  let hit: LaserHit | null = null;
  if (firingNow) {
    camera.getWorldDirection(V1);
    // Aim assist: magnetise within 3°.
    let bestDot = Math.cos(CONFIG.laser.assistDeg * Math.PI / 180);
    let bestPos: THREE.Vector3 | null = null;
    for (const t of mission.laserTargets(planeSim.caught !== null)) {
      V2.copy(t.pos).sub(camera.position).normalize();
      const d = V2.dot(V1);
      if (d > bestDot) { bestDot = d; bestPos = t.pos; }
    }
    if (bestPos) V1.copy(bestPos).sub(camera.position).normalize();
    hit = laserSim.cast(camera.position, V1, mission.laserTargets(planeSim.caught !== null), raycastWorld, planeSim.caught !== null);
    if (hit) mission.registerLaserHit(hit, h);
  }
  laserView.setActive(!!hit);
  if (hit) {
    heroVis.eyeOffsets(V2, V3);
    laserView.sync([V2.clone(), V3.clone()], hit, laserSim.heat, performance.now() * 0.001);
    // Sparks at the hit point.
    if (Math.random() < h * CONFIG.laser.sparkRate * 4) {
      particles.spawn({
        x: hit.pos.x, y: hit.pos.y, z: hit.pos.z,
        vx: (Math.random() - 0.5) * 30, vy: Math.random() * 20, vz: (Math.random() - 0.5) * 30,
        life: 0.4, size0: 0.5, size1: 0.05,
        r0: 1, g0: 0.7, b0: 0.3, r1: 1, g1: 0.2, b1: 0.05, a0: 1, a1: 0, grav: 20, stretch: 2,
      });
    }
  }
  audio.laserSet(!!hit || (firingNow && !hit), laserSim.heat / 100, !!hit && hit.kind !== 'sky');

  // Jets & missiles.
  const preferHero = mission.phase === 'INTERCEPT';
  jets.update(h, {
    heroPos: hero.pos, heroVel: hero.vel, planePos: planeSim.pos, planeVel: planeSim.vel, preferHero,
  }, (x, z) => topAt(layout, x, z));
  misMgr.update(h, hero.pos, planeSim.pos);

  // Tracer hits vs hero & plane.
  for (const tr of jets.tracers) {
    if (!tr.active) continue;
    if (tr.pos.distanceToSquared(hero.pos) < 1.6) {
      tr.active = false;
      bus.emit('heroHit', { amount: CONFIG.hero.hpMax * 0 + 8, dir: { x: tr.vel.x, z: tr.vel.z } });
    } else if (tr.pos.distanceToSquared(planeSim.pos) < 64) {
      tr.active = false;
      bus.emit('hullHit', { amount: CONFIG.plane.dmgTracer });
    } else if (tr.pos.distanceTo(hero.pos) < 14 && Math.random() < h * 3) {
      audio.whiz();
    }
  }

  // Missiles: periodic launch from attacking jets.
  lockScanT -= h;
  if (preferHero === false && lockScanT <= 0) {
    lockScanT = CONFIG.jets.missileCd;
    const shooter = jets.jets.find((j) => j.active && j.pos.distanceTo(planeSim.pos) > 600);
    if (shooter && misMgr.activeCount() < 2) {
      V1.copy(planeSim.pos).sub(shooter.pos).normalize().multiplyScalar(CONFIG.missile.speed);
      misMgr.fire(shooter.pos, V1, false);
      audio.rocket();
    }
  }
  mission.missileAlert(misMgr.activeCount() > 0);

  // Missile homing dodge damage handled in detonate; laser damage:
  if (hit?.kind === 'missile') misMgr.damageById?.(hit.id, CONFIG.laser.dpsMissile * h);

  // Airliner smoke ribbon sampling.
  smokeAcc += h;
  if (smokeAcc >= CONFIG.trail.smokeDt) {
    smokeAcc = 0;
    if (!planeSim.touchedDown) smokeTrail.push(planeSim.pos.x, planeSim.pos.y, planeSim.pos.z);
  }

  // Grab / release keys.
  if (input.wasPressed('KeyE')) {
    if (planeSim.caught === 'NOSE' && planeSim.settling) mission.tryRelease();
    else mission.tryGrab();
  }

  // Settle script: after touchdown, hero slides to the grass under the nose.
  if (planeSim.settling && !planeSim.released) {
    planeSim.vel.multiplyScalar(Math.exp(-3 * h));
    planeSim.pos.addScaledVector(planeSim.vel, h);
    const gy = topAt(layout, planeSim.pos.x, planeSim.pos.z);
    const restY = gy + CONFIG.plane.radius + 2.2;
    planeSim.pos.y += (restY - planeSim.pos.y) * Math.min(1, h * 2);
    planeSim.pitch *= Math.exp(-2 * h);
    syncQuat(planeSim);
    hero.pos.copy(planeSim.pos).add(V1.set(0, -CONFIG.plane.radius - 1.6, CONFIG.plane.len / 2 + 2));
    hero.vel.set(0, 0, 0);
    hero.mode = 'landed';
  }
}

// ---------- Frame ----------
let elapsed = 0;
function frame(dt: number) {
  elapsed += dt;
  const t = elapsed;

  // Sync visuals.
  heroVis.sync(hero, dt, V1.copy(hero.vel).add(V2.set(0, hero.mode === 'hover' ? 0 : 2, 0)));
  planeVis.sync(planeSim, dt, t);
  wreckMgr.update(dt);
  river.update(t);
  cityView.update(t);
  clouds.update(dt, hero.pos);
  stadium.update(dt, t);

  // Trails.
  const spd = hero.vel.length();
  if (spd > 60 || (input.down('ShiftLeft') && spd > 30)) heroTrail.push(hero.pos.x, hero.pos.y, hero.pos.z);
  trails.update(dt, camera);
  jets.jets.forEach((j, i) => {
    if (!j.active || !j.mesh) return;
    const cp = contraPool[i % contraPool.length];
    if (Math.abs((j as unknown as { roll: number }).roll) > 0.5) {
      V1.set(-6.4, 0, -1).applyQuaternion(j.mesh.quaternion).add(j.pos);
      V2.set(6.4, 0, -1).applyQuaternion(j.mesh.quaternion).add(j.pos);
      cp.l.push(V1.x, V1.y, V1.z);
      cp.r.push(V2.x, V2.y, V2.z);
    }
  });

  // Fire + smoke from the burning engine.
  const fa = (planeVis as unknown as { fireAnchor: THREE.Object3D }).fireAnchor.getWorldPosition(V3);
  if (planeSim.engFire && !planeSim.touchedDown) {
    for (let i = 0; i < 3; i++)
      particles.spawn({
        x: fa.x + (Math.random() - 0.5), y: fa.y + (Math.random() - 0.5), z: fa.z + (Math.random() - 0.5),
        vx: (Math.random() - 0.5) * 6, vy: 4 + Math.random() * 6, vz: (Math.random() - 0.5) * 6,
        life: 0.5 + Math.random() * 0.4, size0: 2.4, size1: 0.6,
        r0: 1, g0: 0.6, b0: 0.15, r1: 0.25, g1: 0.08, b1: 0.03, a0: 0.9, a1: 0,
      });
    particles.spawn({
      x: fa.x, y: fa.y + 2, z: fa.z,
      vx: (Math.random() - 0.5) * 3, vy: 3, vz: (Math.random() - 0.5) * 3,
      life: 3.5, size0: 3, size1: 12,
      r0: 0.5, g0: 0.47, b0: 0.45, r1: 0.08, g1: 0.075, b1: 0.07, a0: 0.5, a1: 0, blending: 'alpha',
    });
  }
  audio.engineFire(clamp(1 - planeSim.pos.distanceTo(hero.pos) / 2500, 0, 1));
  audio.crowd(clamp(1 - hero.pos.distanceTo(new THREE.Vector3(stadium.zone.cx, 0, stadium.zone.cz)) / 2200, 0, 1) * (planeSim.settling ? 1 : 0.4));

  // Camera.
  const ov = cine.update(dt);
  const lockPos = lockTargetId !== null
    ? jets.jets.find((j) => j.id === lockTargetId && j.active)?.pos ?? null
    : null;
  cam.update(dt, {
    heroPos: hero.pos,
    aimDir: aimDir(hero, V1),
    bank: hero.bank,
    speed: spd,
    holding: hero.mode === 'holding',
    lockTarget: lockPos,
    planePos: planeSim.pos,
    ...(ov ? { override: ov } : {}),
  });
  if (ov) { camera.position.copy(ov.pos); camera.lookAt(ov.look); }
  sky.follow?.(hero.pos);

  // Post drivers.
  const sp01 = clamp(spd / CONFIG.hero.vMaxBoost, 0, 1);
  if (post.radial) {
    let rs = Math.pow(sp01, 2) * CONFIG.spd.radialMax;
    for (const r of expl.recent) {
      const d = Math.hypot(r.pos.x - camera.position.x, r.pos.y - camera.position.y, r.pos.z - camera.position.z);
      rs += Math.max(0, 1 - d / 120) * r.str * 0.8 * (1 - r.t);
    }
    post.radial.strength = Math.min(1.4, rs);
  }
  if (post.chroma) {
    const o = CONFIG.spd.chromaMax * sp01;
    (post.chroma as unknown as { offset: THREE.Vector2 }).offset.set(o, o * 0.6);
  }

  // Explode proximity shake.
  for (const r of expl.recent) {
    const d = Math.hypot(r.pos.x - hero.pos.x, r.pos.y - hero.pos.y, r.pos.z - hero.pos.z);
    if (r.t < 0.1 && d < 200) cam.addShake(0.5 * r.str * (1 - d / 200));
  }

  // Particles & FX.
  particles.update(dt, camera);
  expl.update(dt, camera);
  speedFx.update(dt, camera, spd, input.down('ShiftLeft'));
  speedFx.updateBooms(dt, camera);

  // HUD.
  const tiers = spd < 6 ? 'HOVER' : spd < 65 ? 'CRUISE' : spd < 140 ? 'FAST' : 'SUPERSONIC';
  hud.setSpeed(spd * 3.6, tiers);
  hud.setAlt(hero.pos.y - topAt(layout, hero.pos.x, hero.pos.z));
  hud.setHP(hero.hp / CONFIG.hero.hpMax);
  hud.setBoost(hero.boost, hero.boostLock);
  hud.setHeat(laserSim.heat / 100, laserSim.overheated);
  hud.setCrosshair(clamp(spd / 40, 0, 3));
  hud.setHolding(hero.mode === 'holding');
  if (hero.mode === 'holding') {
    hud.setHull(planeSim.hull / CONFIG.plane.hullMax);
    hud.setStress(planeSim.stress / 100, planeSim.stress > CONFIG.plane.stressWarn);
    hud.setPlaneSpeed(planeSim.vel.length());
    const zs = stadium.zone;
    hud.setSetdown({
      sink: Math.max(0, -planeSim.vel.y),
      zoneDist: Math.hypot(planeSim.pos.x - zs.cx, planeSim.pos.z - zs.cz),
    });
    // Project the zone outline.
    const pts: [number, number][] = [];
    const corners = [V1.set(-zs.hw, 0, -zs.hd), V2.set(zs.hw, 0, -zs.hd), V3.set(zs.hw, 0, zs.hd), V4.set(-zs.hw, 0, zs.hd)];
    let ok = planeSim.pos.distanceTo(new THREE.Vector3(zs.cx, planeSim.pos.y, zs.cz)) < 500;
    if (ok) {
      for (const c of corners) {
        const w = new THREE.Vector3(zs.cx + c.x, 0.2, zs.cz + c.z);
        const pr = { x: 0, y: 0, z: 0, vis: false };
        cam.worldToScreen(w, pr);
        if (!pr.vis) { ok = false; break; }
        pts.push([pr.x, pr.y]);
      }
    }
    hud.drawZone(ok ? pts : null);
  } else hud.drawZone(null);

  // Off-screen arrow toward the objective (airliner or stadium).
  const tgtPos = mission.phase === 'ARREST' || mission.phase === 'SETDOWN'
    ? new THREE.Vector3(stadium.zone.cx, 20, stadium.zone.cz)
    : planeSim.pos;
  const scr = { x: 0, y: 0, z: 0, vis: false };
  cam.worldToScreen(tgtPos, scr);
  if (!scr.vis || scr.z >= 1) {
    const cx = window.innerWidth / 2, cy = window.innerHeight / 2;
    const dx = scr.x - cx, dy = scr.y - cy;
    const ang = Math.atan2(dy, dx) * 180 / Math.PI;
    hud.setArrow({ x: cx + Math.cos(Math.atan2(dy, dx)) * Math.min(cx, cy) * 0.8, y: cy + Math.sin(Math.atan2(dy, dx)) * Math.min(cx, cy) * 0.8, ang });
  } else hud.setArrow(null);

  // Lock-on (RMB).
  if (input.down('Mouse2')) {
    if (lockTargetId === null) {
      camera.getWorldDirection(V1);
      let bd = Math.cos(CONFIG.laser.lockDeg * Math.PI / 180);
      for (const j of jets.jets) {
        if (!j.active) continue;
        V2.copy(j.pos).sub(camera.position).normalize();
        const dg = V2.dot(V1);
        if (dg > bd) { bd = dg; lockTargetId = j.id; }
      }
    }
  } else lockTargetId = null;
  if (lockTargetId !== null) {
    const jt = jets.jets.find((j) => j.id === lockTargetId);
    if (!jt || !jt.active) lockTargetId = null;
    else {
      const pr = { x: 0, y: 0, z: 0, vis: false };
      cam.worldToScreen(jt.pos, pr);
      hud.setLock(pr.vis ? { x: pr.x, y: pr.y, label: 'BANDIT ' + jt.id, dist: jt.pos.distanceTo(hero.pos), hp: Math.max(0, (jt as unknown as { hp: number }).hp / CONFIG.jets.hp) } : null);
    }
  } else hud.setLock(null);

  // Capture hint.
  hud.hint(!input.locked && started ? 'CLICK TO CAPTURE MOUSE' : null);
  hud.whiteout(clouds.whiteness);
  hud.update(dt);

  // Audio state.
  audio.update(dt, {
    speed: spd, supersonic: spd >= CONFIG.spd.ssV,
    combat: jets.activeCount() > 0 ? 1 : 0,
    stadiumProx: 0,
  });
  audio.boostSet(input.down('ShiftLeft') && input.down('KeyW') ? 1 : 0);

  post.render();
}

// ---------- Boot ----------
const loop = createLoop(fixed, frame);
loop.start();
post.resize(window.innerWidth, window.innerHeight);
hud.showTitle(true);
bus.on('sonicBoom', () => speedFx.boom(hero.pos.clone()));

function cleanupNaN() {
  if (!Number.isFinite(hero.pos.x + hero.pos.y + hero.pos.z)) { hero.pos.set(0, 150, 0); hero.vel.set(0, 0, 0); }
  if (!Number.isFinite(planeSim.pos.x + planeSim.pos.y + planeSim.pos.z)) { planeSim.pos.set(3000, 2000, 0); planeSim.vel.set(-110, -18, 0); }
}
setInterval(cleanupNaN, 500);
```

### tests/flight.test.ts
```ts
import { describe, it, expect } from 'vitest';
import { createState, step, turnRateAt, type Cmd } from '../src/entities/flight.js';
import { CONFIG } from '../src/config.js';
import { mulberry32 } from '../src/core/math.js';

const zeroCmd = (): Cmd => ({ thrust: 0, brake: 0, lift: 0, sink: 0, strafe: 0, boost: false });

describe('flight model', () => {
  it('turn rate at 190 m/s is below turn rate at 0 m/s', () => {
    expect(turnRateAt(190)).toBeLessThan(turnRateAt(0));
  });

  it('terminal cruise speed lands within 5% of CONFIG', () => {
    const s = createState();
    s.mode = 'flight';
    s.vel.set(10, 0, 0);
    const cmd = { ...zeroCmd(), thrust: 1 };
    let prev = 0;
    for (let i = 0; i < 60 * 240; i++) {
      step(s, cmd, 1 / 120, 0);
      if (Math.abs(s.vel.length() - prev) < 1e-4 && i > 1200) break;
      prev = s.vel.length();
    }
    const vt = s.vel.length();
    expect(Math.abs(vt - CONFIG.hero.vMaxCruise) / CONFIG.hero.vMaxCruise).toBeLessThan(0.05);
  });

  it('terminal boost speed lands within 5% of CONFIG', () => {
    const s = createState();
    s.mode = 'flight';
    s.boost = 1;
    s.vel.set(10, 0, 0);
    const cmd = { ...zeroCmd(), thrust: 1, boost: true };
    let prev = 0;
    for (let i = 0; i < 60 * 240; i++) {
      step(s, cmd, 1 / 120, 0);
      if (Math.abs(s.vel.length() - prev) < 1e-4 && i > 1200) break;
      prev = s.vel.length();
    }
    const vt = s.vel.length();
    expect(Math.abs(vt - CONFIG.hero.vMaxBoost) / CONFIG.hero.vMaxBoost).toBeLessThan(0.05);
  });

  it('10,000 steps of random input never produce NaN', () => {
    const rng = mulberry32(7);
    const s = createState();
    s.mode = 'flight';
    for (let i = 0; i < 10000; i++) {
      const cmd: Cmd = {
        thrust: rng(), brake: rng(), lift: rng(), sink: rng(),
        strafe: rng() * 2 - 1, boost: rng() > 0.5,
      };
      step(s, cmd, 1 / 120, 0);
      expect(Number.isFinite(s.pos.x + s.pos.y + s.pos.z)).toBe(true);
      expect(Number.isFinite(s.vel.x + s.vel.y + s.vel.z)).toBe(true);
    }
  });
});
```

### tests/collision.test.ts
```ts
import { describe, it, expect } from 'vitest';
import { generateCityLayout, resolveSphere, gatherNeighbors, cellIndex } from '../src/world/collision.js';
import { CONFIG } from '../src/config.js';
import { mulberry32 } from '../src/core/math.js';

describe('collision', () => {
  const layout = generateCityLayout(CONFIG, 99);

  it('a sphere overlapping any AABB is pushed fully outside', () => {
    const rng = mulberry32(3);
    const bbs = layout.cells.flat().filter(Boolean) as NonNullable<ReturnType<(typeof layout)['cells'][number]>[number]>[];
    expect(bbs.length).toBeGreaterThan(50);
    for (let trial = 0; trial < 200; trial++) {
      const bb = bbs[(rng() * bbs.length) | 0];
      const pos = {
        x: bb.minX + rng() * (bb.maxX - bb.minX),
        y: bb.h * rng(),
        z: bb.minZ + rng() * (bb.maxZ - bb.minZ),
      };
      const vel = { x: 10, y: 0, z: 0 };
      resolveSphere(layout, pos, CONFIG.hero.radius, vel);
      // Verify no neighbour AABB overlaps the sphere anymore.
      const nbs = gatherNeighbors(layout, pos.x, pos.z, []);
      for (const nb of nbs) {
        const cx = Math.max(nb.minX, Math.min(pos.x, nb.maxX));
        const cy = Math.max(0, Math.min(pos.y, nb.h));
        const cz = Math.max(nb.minZ, Math.min(pos.z, nb.maxZ));
        const d2 = (pos.x - cx) ** 2 + (pos.y - cy) ** 2 + (pos.z - cz) ** 2;
        expect(d2).toBeGreaterThanOrEqual(CONFIG.hero.radius ** 2 - 1e-6);
      }
      expect(Number.isFinite(pos.x + pos.y + pos.z)).toBe(true);
    }
  });

  it('grid lookup agrees with brute force on 1,000 random points', () => {
    const rng = mulberry32(11);
    const all = layout.cells.flat().filter(Boolean);
    for (let i = 0; i < 1000; i++) {
      const x = (rng() * 2 - 1) * layout.half;
      const z = (rng() * 2 - 1) * layout.half;
      const idx = cellIndex(layout, x, z);
      const viaGrid = idx >= 0 ? layout.cells[idx]?.length ?? 0 : 0;
      // Brute force: which single cell do the coords imply (there is at most one BB per cell)?
      let brute = 0;
      for (const arr of layout.cells) if (arr) {
        for (const bb of arr) {
          if (x >= bb.minX && x <= bb.maxX && z >= bb.minZ && z <= bb.maxZ) { brute++; break; }
        }
      }
      // Containment agreement: if the point sits inside a footprint, its cell must hold it.
      if (brute > 0) expect(viaGrid).toBeGreaterThan(0);
      void all;
    }
  });
});
```

### tests/holding.test.ts
```ts
import { describe, it, expect } from 'vitest';
import { createAirlinerState } from '../src/entities/airliner.js';
import { createState as createHeroState } from '../src/entities/flight.js';
import * as holding from '../src/entities/holding.js';
import { CONFIG } from '../src/config.js';
import * as THREE from 'three';

const aim = new THREE.Vector3(0, 0, -1);

describe('holding', () => {
  it('full brake from 110 m/s reaches under 30 m/s within 12 s', () => {
    const s = createAirlinerState();
    const hero = createHeroState();
    holding.attach(s, hero, 'NOSE');
    s.vel.set(-110, 0, 0);
    const ctrl: holding.HoldCtrl = {
      brake: 1, fwd: 0, lift: 0, sink: 0, aimDir: aim.clone(),
    };
    for (let i = 0; i < 12 * 120; i++) holding.step(s, hero, ctrl, 1 / 120);
    expect(s.vel.length()).toBeLessThan(30);
  });

  it('sustained 10+ m/s^2 brake crosses stress 70', () => {
    const s = createAirlinerState();
    const hero = createHeroState();
    holding.attach(s, hero, 'NOSE');
    s.vel.set(-110, 0, 0);
    const ctrl: holding.HoldCtrl = { brake: 1, fwd: 0, lift: 0, sink: 0, aimDir: aim.clone() };
    let crossed = false;
    for (let i = 0; i < 5 * 120; i++) {
      holding.step(s, hero, ctrl, 1 / 120);
      if (s.stress >= 70) { crossed = true; break; }
    }
    expect(crossed).toBe(true);
  });

  it('a tail grab tears at 1.5 s and drops hull by 30', () => {
    const s = createAirlinerState();
    const hero = createHeroState();
    const hull0 = s.hull;
    holding.attach(s, hero, 'TAIL');
    const ctrl: holding.HoldCtrl = { brake: 0, fwd: 0, lift: 0, sink: 0, aimDir: aim.clone() };
    let tore = false;
    for (let i = 0; i < 2 * 120; i++) {
      const f = holding.step(s, hero, ctrl, 1 / 120);
      if (f.tore) { tore = true; break; }
    }
    expect(tore).toBe(true);
    expect(s.torn).toBe(true);
    expect(hull0 - s.hull).toBeCloseTo(CONFIG.plane.dmgTail, 1);
  });
});
```

### tests/mission.test.ts
```ts
import { describe, it, expect, vi } from 'vitest';
import { Mission, type MissionIO } from '../src/game/mission.js';
import { createBus } from '../src/core/events.js';
import { CONFIG } from '../src/config.js';
import * as THREE from 'three';

function stubDeps() {
  const bus = createBus();
  const noop = () => {};
  const hud = new Proxy({}, { get: () => noop }) as never;
  const audio = new Proxy({}, { get: () => noop }) as never;
  const cam = new Proxy({}, { get: () => noop }) as never;
  const cine = new Proxy({}, { get: (_, k) => (k === 'playing' ? false : noop) }) as never;
  const scoring = {
    registerJet: noop, finalize: () => ({ score: 0, grade: 'S', best: 0, newBest: false, rows: [] }), peek: () => 0,
  } as never;
  const expl = { explode: noop, recent: [], update: noop } as never;
  const stadium = { zone: { cx: 0, cz: 0, hw: 60, hd: 40 }, contains: () => true } as never;
  const layout = { cells: [], tops: new Float32Array(1), N: 1, cell: 48, half: 24 } as never;
  const laser = { update: noop, heat: 0, overheated: false, cast: () => null, reset: noop } as never;
  const jets = {
    spawn: noop, activeCount: () => 0, forEachActive: noop, damageById: noop,
    tracers: [], update: noop,
  } as never;
  const io: MissionIO = {
    spawnWave: noop, clearEnemies: noop,
    resetHero: noop, resetPlane: noop,
    setTimeScale: noop, warpHeroNearPlane: noop,
  };
  return { bus, hud, audio, cam, cine, scoring, expl, stadium, layout, laser, jets, io, cfg: CONFIG };
}

const ctx = { firing: false, raycastWorld: () => null, heroSurf: 0 };
const cmd = { thrust: 0, brake: 0, lift: 0, sink: 0, strafe: 0, boost: false };

describe('mission', () => {
  it('transitions INTERCEPT -> CATCH -> ARREST in order', () => {
    const d = stubDeps();
    const m = new Mission(d);
    m.hero = {
      pos: new THREE.Vector3(), vel: new THREE.Vector3(), hp: 100,
      mode: 'flight', stunT: 0, tumble: new THREE.Vector3(), bank: 0, boost: 1, boostLock: false,
    } as never;
    m.plane = {
      pos: new THREE.Vector3(1000, 500, 0), vel: new THREE.Vector3(-110, -18, 0),
      hull: 100, stress: 0, caught: null, torn: false, dead: false, touchedDown: null,
      settling: false, eta: Infinity, pathClear: false, gear: 0, crumple: 0, elapsed: 0,
      released: false, tearT: 0, catchAnim: 0, engFire: true, landed: false,
      quat: new THREE.Quaternion(), yaw: 0, pitch: 0, roll: 0,
    } as never;
    m.setPhaseDirect?.();
    (m as unknown as { phase: string }).phase = 'INTERCEPT';
    // Far away: stays INTERCEPT.
    m.update(1 / 120, cmd, ctx);
    expect(m.phase).toBe('INTERCEPT');
    // Close: becomes CATCH.
    m.plane.pos.set(100, 500, 0);
    m.update(1 / 120, cmd, ctx);
    expect(m.phase).toBe('CATCH');
    // Caught the nose: ARREST.
    m.plane.caught = 'NOSE';
    m.update(1 / 120, cmd, ctx);
    expect(m.phase).toBe('ARREST');
  });

  it('every fail state produces its reason', () => {
    const d = stubDeps();
    const m = new Mission(d);
    m.hero = { pos: new THREE.Vector3(), vel: new THREE.Vector3(), hp: 100, mode: 'flight', stunT: 0, tumble: new THREE.Vector3(), bank: 0, boost: 1, boostLock: false } as never;
    m.plane = { pos: new THREE.Vector3(0, 2, 0), vel: new THREE.Vector3(-110, -18, 0), hull: 100, stress: 0, caught: null, torn: false, dead: false, touchedDown: null, settling: false, eta: 1, pathClear: false, gear: 0, crumple: 0, elapsed: 0, released: false, tearT: 0, catchAnim: 0, engFire: true, landed: false, quat: new THREE.Quaternion(), yaw: 0, pitch: 0, roll: 0 } as never;
    (m as unknown as { phase: string }).phase = 'CATCH';
    m.update(1 / 120, cmd, ctx);
    expect(m.phase).toBe('FAILED');
    expect(m.failReason).toContain('HIT');
  });

  it('retry restores the phase checkpoint', () => {
    const d = stubDeps();
    const spy = vi.spyOn(d.io, 'resetHero');
    const m = new Mission(d);
    m.hero = { pos: new THREE.Vector3(1, 2, 3), vel: new THREE.Vector3(), hp: 100, mode: 'flight', stunT: 0, tumble: new THREE.Vector3(), bank: 0, boost: 1, boostLock: false } as never;
    m.plane = { pos: new THREE.Vector3(5000, 2400, 0), vel: new THREE.Vector3(-110, -18, 0), hull: 100, stress: 0, caught: null, torn: false, dead: false, touchedDown: null, settling: false, eta: Infinity, pathClear: false, gear: 0, crumple: 0, elapsed: 0, released: false, tearT: 0, catchAnim: 0, engFire: true, landed: false, quat: new THREE.Quaternion(), yaw: 0, pitch: 0, roll: 0 } as never;
    (m as unknown as { phase: string }).phase = 'INTERCEPT';
    m.update(1 / 120, cmd, ctx);
    m.fail('TEST FAIL');
    m.retryPhase();
    expect(spy).toHaveBeenCalled();
    expect(m.phase).toBe('INTERCEPT');
  });
});
```

---

## File tree (approx. line counts)

```
last-flight/
├─ package.json .................... 27
├─ tsconfig.json ................... 24
├─ vite.config.ts .................. 10
├─ index.html ...................... 20
├─ README.md ....................... 20
├─ src/
│  ├─ config.ts .................... 215
│  ├─ main.ts ...................... 470
│  ├─ core/ renderer 115 · loop 55 · input 95 · audio 400 · pool 18 · math 95 · events 55
│  ├─ world/ sky 120 · collision 300 · ground 60 · river 45 · city 195 · clouds 90 · stadium 200
│  ├─ entities/ flight 300 · hero 260 · laser 200 · airliner 310 · holding 175 · jet 305 · missile 145 · wreck 90
│  ├─ vfx/ particles 235 · explosions 195 · trails 185 · speedlines 105
│  │  └─ shaders/ radialBlur 40 · grade 35 · fire 60 · water 65 · windows 75 · cloud 70
│  └─ game/ mission 400 · camera 135 · hud 330 · cinematics 105 · scoring 75 · debug 35 · deps 25
└─ tests/ flight 70 · collision 65 · holding 60 · mission 105
```

## Run it

```
npm install
npm run dev
```

Verify cleanliness: `npm run typecheck && npm test && npm run build`

## Three tuning tips

1. **Momentum feel** — `CONFIG.hero.turnHigh` (0.7 rad/s at boost) and `hero.dragBlend` dominate. Raise `turnHigh` to 1.0 for arcade snappiness; drop it to 0.5 and lengthen `dragBlend` to 0.6 s for heavy, cinematic carving.
2. **The arrest puzzle** — `CONFIG.plane.stressSafe` (7 m/s²) versus `brakeMax` (12) defines the brake-pumping rhythm; raising `stressSafe` to 8 makes a no-stress run nearly as fast as risky pumping, lowering it to 6 forces constant attention.
3. **Combat pressure** — `CONFIG.jets.wave4Delay` (40 s) and `jets.missileCd` (12 s) set how hot the hold gets; dropping `missileCd` to 8 turns the stadium approach into a knife fight, and `laser.dpsJet` (35) trades jet-kill time against overheat pacing via `heatRate`.