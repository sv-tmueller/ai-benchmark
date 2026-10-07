**package.json**

```json
{
  "name": "bridge-horror-house",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "three": "^0.161.0"
  },
  "devDependencies": {
    "vite": "^5.2.0"
  }
}
```

**vite.config.js**

```js
import { defineConfig } from 'vite';

export default defineConfig({
  server: { port: 5173, open: false },
  build: { target: 'esnext', sourcemap: false },
  optimizeDeps: { include: ['three'] }
});
```

**SYSTEM_PROMPT.md**

```md
# Bridge Horror House — design constitution
The full design charter (graphics mandate, horror rules, floor plan, scare
sequence, tech stack, acceptance tests) is maintained by the Lead Horror Game
Agent and supplied alongside this repository. This file reserves its place in
the tree; consult the delivered charter for the authoritative contract.
```

**index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>BRIDGE HORROR HOUSE</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Special+Elite&display=swap');

:root{
  --bone:#cfc6b4; --bone-dim:rgba(207,198,180,.55); --blood:#8c1a17;
  --ink:#050507; --brass:#c79a45;
  --f-serif:"IM Fell English",Georgia,serif;
  --f-type:"Special Elite","Courier New",monospace;
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-user-select:none;user-select:none}
html,body{width:100%;height:100%;overflow:hidden;background:var(--ink);cursor:default}
body{font-family:var(--f-type);color:var(--bone)}
#app,#app canvas{position:absolute;inset:0;width:100%;height:100%;display:block}

/* ---------- permanent optical layers ---------- */
.layer{position:absolute;inset:0;pointer-events:none}
#fx-vignette{background:radial-gradient(ellipse at 50% 48%, transparent 46%, rgba(0,0,0,.55) 78%, rgba(0,0,0,.92) 100%);}
#fx-grain{width:100%;height:100%;opacity:.07;mix-blend-mode:overlay}
#fx-flash{background:#fff;opacity:0;transition:opacity .06s linear}
#danger-veil{opacity:0;box-shadow:inset 0 0 22vw 6vw rgba(112,10,8,.85);}

/* ---------- HUD ---------- */
#hud{position:absolute;inset:0;pointer-events:none;font-size:14px;letter-spacing:.06em}
#crosshair{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%)}
#crosshair .dot{display:block;width:3px;height:3px;border-radius:50%;background:var(--bone-dim)}
#crosshair .ring{position:absolute;left:50%;top:50%;width:26px;height:26px;margin:-13px 0 0 -13px;
  border:1px solid transparent;border-radius:50%;transition:all .12s ease}
#crosshair.hot .ring{border-color:var(--bone-dim);width:34px;height:34px;margin:-17px 0 0 -17px}
#prompt{position:absolute;left:50%;top:calc(50% + 34px);transform:translateX(-50%);
  padding:5px 14px;border:1px solid rgba(207,198,180,.28);background:rgba(4,4,6,.72);
  font-size:12px;color:var(--bone);opacity:0;transition:opacity .12s}
#prompt.show{opacity:1}
#prompt b{color:var(--brass)}

#objective{position:absolute;top:26px;left:50%;transform:translateX(-50%);text-align:center}
#objective .lbl{font-size:10px;letter-spacing:.4em;color:var(--bone-dim);opacity:.7}
#obj-text{font-family:var(--f-serif);font-size:19px;color:var(--bone);margin-top:2px;text-shadow:0 1px 0 #000}
#obj-sub{font-size:11px;color:var(--bone-dim);margin-top:2px}
#key-row{margin-top:8px;display:flex;gap:10px;justify-content:center}
#key-row svg{width:22px;height:22px;opacity:.16;filter:grayscale(1);transition:all .5s}
#key-row svg.found{opacity:1;filter:none;stroke:var(--brass);fill:none;
  filter:drop-shadow(0 0 4px rgba(199,154,69,.55))}
#warn-tag{font-family:var(--f-serif);font-style:italic;font-size:13px;color:#a4524c;
  margin-top:6px;opacity:0;transition:opacity 1.2s}
#warn-tag.show{opacity:.9}

#battery{position:absolute;left:28px;bottom:26px;display:flex;align-items:center;gap:10px}
#battery svg{width:20px;height:20px;stroke:var(--bone-dim);fill:none;stroke-width:1.6}
#batt-track{width:130px;height:8px;border:1px solid rgba(207,198,180,.3);padding:1px;background:rgba(0,0,0,.5)}
#batt-fill{height:100%;width:100%;background:var(--bone);transition:width .25s linear}
#battery.warn #batt-fill{background:#c9a23a}
#battery.crit #batt-fill{background:var(--blood);animation:battblink .5s steps(2) infinite}
@keyframes battblink{50%{opacity:.35}}
#batt-pct{font-size:11px;color:var(--bone-dim);min-width:34px}

#burn-wrap{position:absolute;left:50%;top:calc(50% - 58px);transform:translateX(-50%);
  text-align:center;opacity:0;transition:opacity .15s}
#burn-wrap.show{opacity:1}
#burn-label{font-size:10px;letter-spacing:.35em;color:#e0b184;text-shadow:0 0 6px rgba(255,120,30,.6)}
#burn-track{width:120px;height:5px;margin-top:4px;border:1px solid rgba(224,177,132,.5);padding:1px}
#burn-fill{height:100%;width:0%;background:#ff8a2a;box-shadow:0 0 8px rgba(255,138,42,.8)}

#toast{position:absolute;bottom:96px;left:50%;transform:translateX(-50%);
  font-family:var(--f-serif);font-style:italic;font-size:16px;color:var(--bone);
  opacity:0;transition:opacity .4s;text-shadow:0 1px 2px #000}
#toast.show{opacity:1}

/* ---------- note overlay ---------- */
#note-ov{position:absolute;inset:0;display:none;align-items:center;justify-content:center;
  background:rgba(2,2,3,.78);pointer-events:auto;z-index:30}
#note-paper{width:min(480px,84vw);max-height:76vh;overflow:auto;background:#cdb894;color:#241c10;
  padding:44px 40px 34px;transform:rotate(-1.4deg);
  box-shadow:0 24px 60px rgba(0,0,0,.9), inset 0 0 60px rgba(88,60,20,.35);
  font-family:var(--f-serif);font-size:18px;line-height:1.65}
#note-title{font-size:14px;letter-spacing:.18em;text-transform:uppercase;border-bottom:1px solid rgba(36,28,16,.4);
  padding-bottom:8px;margin-bottom:14px;font-family:var(--f-type)}
#note-close{margin-top:22px;font-family:var(--f-type);font-size:11px;letter-spacing:.25em;opacity:.65;text-align:right}

/* ---------- full screens ---------- */
.screen{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;z-index:40}
.screen.on{display:flex}
.btn{pointer-events:auto;cursor:pointer;background:none;border:1px solid rgba(207,198,180,.4);
  color:var(--bone);font-family:var(--f-type);font-size:13px;letter-spacing:.3em;
  padding:13px 34px 11px;text-transform:uppercase;transition:all .18s}
.btn:hover{background:var(--bone);color:#0a0a0c;border-color:var(--bone)}

#scr-title{background:rgba(3,3,5,.42)}
#scr-title h1{font-family:var(--f-serif);font-weight:400;color:#ddd3bf;
  font-size:clamp(44px,9vw,104px);line-height:.95;letter-spacing:.04em;
  text-shadow:0 2px 0 #000,0 0 26px rgba(0,0,0,.9);animation:titlebreathe 6s ease-in-out infinite}
#scr-title h1 em{display:block;font-style:italic;font-size:.62em;color:#b9ab90}
@keyframes titlebreathe{50%{opacity:.86;letter-spacing:.055em}}
.title-rule{width:220px;height:1px;background:rgba(207,198,180,.35);margin:26px 0 18px}
#scr-title .caption{font-size:12px;letter-spacing:.42em;color:var(--bone-dim)}
.controls-grid{display:grid;grid-template-columns:auto auto;gap:6px 22px;margin:30px 0 34px;
  font-size:12px;color:var(--bone-dim);text-align:left}
.controls-grid b{color:var(--bone);font-weight:400;letter-spacing:.15em}
.title-start{font-family:var(--f-serif);font-style:italic;font-size:20px;color:var(--brass);
  animation:pulse 2.4s ease-in-out infinite;cursor:pointer;pointer-events:auto}
@keyframes pulse{50%{opacity:.45}}
.headphones{margin-top:26px;font-size:10px;letter-spacing:.3em;color:rgba(207,198,180,.4)}

#scr-death{background:transparent}
#jumpface{position:absolute;inset:0;background-size:cover;background-position:center;
  display:none;animation:jolt .09s steps(2) infinite}
@keyframes jolt{50%{transform:translate(6px,-5px) scale(1.03)}}
#scr-death .panel{position:relative;background:rgba(4,4,6,.88);border:1px solid rgba(140,26,23,.5);
  padding:44px 60px;max-width:520px}
#scr-death h2{font-family:var(--f-serif);font-size:44px;color:var(--blood);font-weight:400;
  text-shadow:0 0 18px rgba(140,26,23,.5)}
.stat-line{margin-top:14px;font-size:13px;color:var(--bone-dim);letter-spacing:.12em}
.stat-line b{color:var(--bone);font-weight:400}
#scr-death .btn{margin-top:30px}

#scr-win{background:rgba(228,232,238,.06)}
#scr-win .panel{background:rgba(6,7,9,.92);border:1px solid rgba(188,210,255,.25);padding:48px 64px}
#scr-win h2{font-family:var(--f-serif);font-size:42px;color:#ccd8ec;font-weight:400}
#scr-win .stat-line b{color:#e6eefc}

#scr-pause{background:rgba(2,2,3,.7);cursor:pointer;pointer-events:auto}
#scr-pause p{font-family:var(--f-serif);font-style:italic;font-size:22px;color:var(--bone-dim)}

#unsupported{position:absolute;inset:0;z-index:99;display:none;align-items:center;justify-content:center;
  background:#050507;font-family:var(--f-serif);font-size:18px;color:var(--bone-dim);text-align:center;padding:30px}
.vtag{position:absolute;bottom:12px;right:16px;font-size:10px;letter-spacing:.25em;color:rgba(207,198,180,.28)}
</style>
</head>
<body>
<div id="app"></div>

<!-- optical layers -->
<canvas id="fx-grain" class="layer" width="200" height="112"></canvas>
<div id="fx-vignette" class="layer"></div>
<div id="danger-veil" class="layer"></div>
<div id="fx-flash" class="layer"></div>

<!-- HUD -->
<div id="hud">
  <div id="crosshair"><span class="dot"></span><span class="ring"></span></div>
  <div id="prompt"></div>
  <div id="objective">
    <div class="lbl">OBJECTIVE</div>
    <div id="obj-text">Find the three brass keys</div>
    <div id="obj-sub">kitchen &middot; study &middot; bedroom</div>
    <div id="warn-tag">something else is awake now</div>
    <div id="key-row">
      <svg viewBox="0 0 24 24" stroke="#c79a45" stroke-width="1.8" stroke-linecap="round"><circle cx="7" cy="12" r="3.1"/><path d="M10.1 12h10M15 12v3.4M18.4 12v2.6"/></svg>
      <svg viewBox="0 0 24 24" stroke="#c79a45" stroke-width="1.8" stroke-linecap="round"><circle cx="7" cy="12" r="3.1"/><path d="M10.1 12h10M15 12v3.4M18.4 12v2.6"/></svg>
      <svg viewBox="0 0 24 24" stroke="#c79a45" stroke-width="1.8" stroke-linecap="round"><circle cx="7" cy="12" r="3.1"/><path d="M10.1 12h10M15 12v3.4M18.4 12v2.6"/></svg>
    </div>
  </div>
  <div id="battery">
    <svg viewBox="0 0 24 24"><rect x="9" y="7" width="6" height="13" rx="1"/><path d="M10.5 7V5h3v2M12 2v2M7 4l1.6 1.6M17 4l-1.6 1.6"/></svg>
    <div id="batt-track"><div id="batt-fill"></div></div>
    <span id="batt-pct">100%</span>
  </div>
  <div id="burn-wrap">
    <div id="burn-label">HOLD THE BEAM</div>
    <div id="burn-track"><div id="burn-fill"></div></div>
  </div>
  <div id="toast"></div>
</div>

<!-- note -->
<div id="note-ov">
  <div id="note-paper">
    <div id="note-title"></div>
    <div id="note-body"></div>
    <div id="note-close">PRESS&nbsp;&nbsp;E&nbsp;&nbsp;/&nbsp;&nbsp;CLICK&nbsp;&nbsp;TO&nbsp;&nbsp;PUT&nbsp;&nbsp;DOWN</div>
  </div>
</div>

<!-- title -->
<div id="scr-title" class="screen on">
  <h1>BRIDGE<em>&nbsp;&nbsp;horror house</em></h1>
  <div class="title-rule"></div>
  <div class="caption">THE DOORS ARE SEALED &middot; THE KEYS ARE LOST &middot; YOU ARE NOT ALONE</div>
  <div class="controls-grid">
    <b>MOUSE</b><span>look</span>
    <b>W A S D</b><span>move</span>
    <b>SHIFT</b><span>sprint</span>
    <b>E</b><span>interact</span>
    <b>F</b><span>torch</span>
  </div>
  <div class="title-start" id="btn-begin">click to wake up</div>
  <div class="headphones">HEADPHONES &middot; LIGHTS OFF &middot; ALONE</div>
  <div class="vtag">v0.1 &mdash; A HAUNTED PROTOTYPE</div>
</div>

<!-- death -->
<div id="scr-death" class="screen">
  <div id="jumpface"></div>
  <div class="panel">
    <h2>IT HAS YOU</h2>
    <div class="stat-line" id="death-stats"></div>
    <button class="btn" id="btn-retry">Wake again</button>
  </div>
</div>

<!-- win -->
<div id="scr-win" class="screen">
  <div class="panel">
    <h2>YOU ESCAPED</h2>
    <div class="stat-line">Survived <b id="win-time">--:--</b> in the house</div>
    <div class="stat-line">Drove it back <b id="win-ban">0</b> times</div>
    <button class="btn" id="btn-again">Enter once more</button>
  </div>
</div>

<!-- pause -->
<div id="scr-pause" class="screen"><p>the house waits&hellip;</p></div>
<div id="unsupported">This haunting requires a keyboard, a mouse and a stubborn heart.<br/>Desktop browsers only.</div>

<script type="module" src="/src/main.js"></script>
</body>
</html>
```

**src/main.js**

```js
import { Game } from './Game.js';

if (!('onpointerlockchange' in document) || 'ontouchstart' in window && navigator.maxTouchPoints > 2) {
  // Soft refusal for devices that cannot pointer-lock; desktop proceeds untouched.
  if (!matchMedia('(pointer:fine)').matches) {
    document.getElementById('unsupported').style.display = 'flex';
  }
}

const game = new Game();
game.boot();

window.addEventListener('error', (e) => {
  console.error('[BHH]', e.message);
});
```

**src/ui/HUD.js**

```js
// Plain-DOM heads-up display: objectives, torch gauge, burn meter, prompts,
// screen flashes, film grain, note overlay and the full-screen states.
const $ = (id) => document.getElementById(id);

export class HUD {
  constructor() {
    this.el = {
      crosshair: $('crosshair'),
      prompt: $('prompt'),
      objText: $('obj-text'),
      objSub: $('obj-sub'),
      warn: $('warn-tag'),
      keys: [...$('key-row').children],
      battery: $('battery'),
      battFill: $('batt-fill'),
      battPct: $('batt-pct'),
      burnWrap: $('burn-wrap'),
      burnFill: $('burn-fill'),
      toast: $('toast'),
      flash: $('fx-flash'),
      veil: $('danger-veil'),
      grain: $('fx-grain'),
      noteOv: $('note-ov'),
      noteTitle: $('note-title'),
      noteBody: $('note-body'),
      title: $('scr-title'),
      death: $('scr-death'),
      jumpface: $('jumpface'),
      deathStats: $('death-stats'),
      win: $('scr-win'),
      winTime: $('win-time'),
      winBan: $('win-ban'),
      pause: $('scr-pause')
    };
    this.grainCtx = this.el.grain.getContext('2d');
    this.grainW = this.el.grain.width;
    this.grainH = this.el.grain.height;
    this.grainData = this.grainCtx.createImageData(this.grainW, this.grainH);
    this._toastT = 0;
    this._flashT = 0;
    this._veil = 0;
    this._veilTarget = 0;
  }

  /* ---- objectives ------------------------------------------------------ */
  setObjective(main, sub) {
    this.el.objText.textContent = main;
    if (sub !== undefined) this.el.objSub.innerHTML = sub;
  }
  setWarn(show) { this.el.warn.classList.toggle('show', !!show); }
  setKeys(n) {
    this.el.keys.forEach((k, i) => k.classList.toggle('found', i < n));
  }

  /* ---- gauges ---------------------------------------------------------- */
  battery(v) {
    const pct = Math.max(0, Math.round(v));
    this.el.battFill.style.width = pct + '%';
    this.el.battPct.textContent = pct + '%';
    this.el.battery.classList.toggle('warn', v <= 35 && v > 18);
    this.el.battery.classList.toggle('crit', v <= 18);
  }
  burn(show, frac) {
    this.el.burnWrap.classList.toggle('show', !!show);
    if (show) this.el.burnFill.style.width = Math.min(100, frac * 100) + '%';
  }
  prompt(html) {
    if (html) { this.el.prompt.innerHTML = html; this.el.prompt.classList.add('show'); this.el.crosshair.classList.add('hot'); }
    else { this.el.prompt.classList.remove('show'); this.el.crosshair.classList.remove('hot'); }
  }
  veil(v) { this._veilTarget = v; }

  /* ---- ephemeral feedback ---------------------------------------------- */
  toast(msg, dur = 2.6) {
    this.el.toast.textContent = msg;
    this.el.toast.classList.add('show');
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => this.el.toast.classList.remove('show'), dur * 1000);
  }
  flash(color, alpha, dur = 0.14) {
    const el = this.el.flash;
    el.style.background = color;
    el.style.transition = 'none';
    el.style.opacity = alpha;
    void el.offsetWidth;
    el.style.transition = `opacity ${dur}s ease-out`;
    el.style.opacity = '0';
  }
  lightning(pop = 1) { this.flash('#dfe6ff', 0.16 * pop, 0.22); }

  /* ---- note ------------------------------------------------------------ */
  openNote(def) {
    this.el.noteTitle.textContent = def.title;
    this.el.noteBody.innerText = def.body;
    this.el.noteOv.style.display = 'flex';
  }
  closeNote() { this.el.noteOv.style.display = 'none'; }
  get noteOpen() { return this.el.noteOv.style.display === 'flex'; }

  /* ---- screens ---------------------------------------------------------- */
  show(which) {
    for (const s of [this.el.title, this.el.death, this.el.win, this.el.pause]) s.classList.remove('on');
    if (which) which.classList.add('on');
  }
  jumpscare(dataUrl) {
    this.el.jumpface.style.backgroundImage = `url(${dataUrl})`;
    this.el.jumpface.style.display = 'block';
  }
  calmJumpscare() { this.el.jumpface.style.display = ''; }
  deathStats(timeTxt, keys) {
    this.el.deathStats.innerHTML =
      `You lasted <b>${timeTxt}</b> &middot; keys recovered <b>${keys}/3</b>`;
  }
  winStats(timeTxt, bans) {
    this.el.winTime.textContent = timeTxt;
    this.el.winBan.textContent = bans;
  }

  /* ---- per-frame -------------------------------------------------------- */
  frame(dt) {
    // animated film grain
    const d = this.grainData.data;
    for (let i = 0; i < d.length; i += 4) {
      const v = (Math.random() * 255) | 0;
      d[i] = d[i + 1] = d[i + 2] = v;
      d[i + 3] = 255;
    }
    this.grainCtx.putImageData(this.grainData, 0, 0);

    // danger veil easing
    this._veil += (this._veilTarget - this._veil) * Math.min(1, dt * 4);
    this.el.veil.style.opacity = this._veil.toFixed(3);
  }

  reset() {
    this.setKeys(0);
    this.setWarn(false);
    this.battery(100);
    this.burn(false, 0);
    this.prompt(null);
    this.veil(0);
    this.closeNote();
    this.calmJumpscare();
  }
}
```

**src/world/Textures.js**

```js
// Every surface in the house wears a procedurally painted canvas texture.
// Zero binaries, zero fetches, instant load. All canvases are power-of-two
// so mipmapping stays legal.
import * as THREE from 'three';

const CACHE = new Map();
let MAX_ANISO = 4;

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function cv(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

function finish(c, { srgb = true, repeat = false } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  t.anisotropy = MAX_ANISO;
  return t;
}

function cached(key, maker) {
  if (!CACHE.has(key)) CACHE.set(key, maker());
  return CACHE.get(key);
}

/* ------------------------------------------------------------------ wood */
function paintWood(base, dark) {
  return cached('wood_' + base, () => {
    const [c, x] = cv(512, 512);
    const R = rng(1188);
    x.fillStyle = base; x.fillRect(0, 0, 512, 512);
    const rows = 6, rh = 512 / rows;
    for (let r = 0; r < rows; r++) {
      const y0 = r * rh;
      const lum = (R() - 0.5) * 26;
      x.fillStyle = `rgba(${lum > 0 ? 255 : 0},${lum > 0 ? 240 : 10},${lum > 0 ? 210 : 5},${Math.abs(lum) / 340})`;
      x.fillRect(0, y0, 512, rh);
      // grain streaks
      for (let i = 0; i < 26; i++) {
        const gy = y0 + R() * rh;
        const amp = 2 + R() * 5, wl = 60 + R() * 160;
        x.strokeStyle = `rgba(${R() > .5 ? '10,6,3' : '120,92,60'},${0.04 + R() * 0.09})`;
        x.lineWidth = 0.5 + R() * 1.6;
        x.beginPath();
        for (let px = 0; px <= 512; px += 16) {
          const py = gy + Math.sin(px / wl * Math.PI * 2 + r) * amp;
          px === 0 ? x.moveTo(px, py) : x.lineTo(px, py);
        }
        x.stroke();
      }
      // knot
      if (R() < 0.5) {
        const kx = R() * 512, ky = y0 + rh * (0.25 + R() * 0.5);
        for (let q = 5; q > 0; q--) {
          x.strokeStyle = `rgba(12,7,4,${0.16 + q * 0.03})`;
          x.lineWidth = 1.1;
          x.beginPath();
          x.ellipse(kx, ky, q * 3.4, q * 2.1, R() * 3, 0, Math.PI * 2);
          x.stroke();
        }
      }
      // seam + bevel
      x.fillStyle = 'rgba(0,0,0,.55)'; x.fillRect(0, y0, 512, 2);
      x.fillStyle = 'rgba(190,160,120,.10)'; x.fillRect(0, y0 + 2, 512, 1);
      // nails
      for (const nx of [86, 256, 426]) {
        x.fillStyle = 'rgba(8,6,4,.8)';
        x.beginPath(); x.arc(nx + R() * 8 - 4, y0 + 4, 1.6, 0, 7); x.fill();
        x.fillStyle = 'rgba(96,58,30,.35)';
        x.beginPath(); x.arc(nx + R() * 8 - 4, y0 + 4, 3.4, 0, 7); x.fill();
      }
    }
    // scratches & wear
    for (let i = 0; i < 40; i++) {
      x.strokeStyle = `rgba(168,140,104,${0.05 + R() * 0.08})`;
      x.lineWidth = 0.7;
      const sx = R() * 512, sy = R() * 512;
      x.beginPath(); x.moveTo(sx, sy); x.lineTo(sx + (R() - .5) * 90, sy + (R() - .5) * 14); x.stroke();
    }
    if (dark) { x.fillStyle = 'rgba(0,0,0,.34)'; x.fillRect(0, 0, 512, 512); }
    // patina vignette
    const vg = x.createRadialGradient(256, 256, 120, 256, 256, 370);
    vg.addColorStop(0, 'rgba(0,0,0,0)');
    vg.addColorStop(1, 'rgba(0,0,0,.28)');
    x.fillStyle = vg; x.fillRect(0, 0, 512, 512);
    return finish(c, { repeat: true });
  });
}

/* ------------------------------------------------------------- wallpaper */
function paintWallpaper(variant) {
  return cached('wp' + variant, () => {
    const [c, x] = cv(512, 512);
    const R = rng(4000 + variant * 77);
    const pal = variant === 0 ? ['#4a4132', '#373126'] : ['#453f31', '#322e28'];
    // stripes (8 across => seamless horizontally)
    for (let s = 0; s < 8; s++) {
      x.fillStyle = pal[s % 2];
      x.fillRect(s * 64, 0, 64, 512);
      x.fillStyle = 'rgba(214,196,150,.07)';
      x.fillRect(s * 64 + 28, 0, 3, 512);
      if (s % 2 === 0) { // damask motifs
        for (let m = 0; m < 4; m++) {
          const mx = s * 64 + 32, my = 64 + m * 128;
          x.strokeStyle = 'rgba(206,188,146,.13)';
          x.lineWidth = 1.4;
          x.beginPath();
          x.moveTo(mx, my - 22); x.quadraticCurveTo(mx + 16, my, mx, my + 22);
          x.quadraticCurveTo(mx - 16, my, mx, my - 22);
          x.moveTo(mx - 12, my); x.lineTo(mx + 12, my);
          x.stroke();
          x.fillStyle = 'rgba(206,188,146,.10)';
          x.beginPath(); x.arc(mx, my, 2.4, 0, 7); x.fill();
        }
      }
    }
    // age blotches, heavier toward the bottom
    for (let i = 0; i < 46; i++) {
      const bx = R() * 512, by = 512 * Math.pow(R(), 0.6);
      const br = 14 + R() * 70;
      const g = x.createRadialGradient(bx, by, 2, bx, by, br);
      g.addColorStop(0, `rgba(58,38,18,${0.05 + R() * 0.13})`);
      g.addColorStop(1, 'rgba(58,38,18,0)');
      x.fillStyle = g;
      x.beginPath(); x.arc(bx, by, br, 0, 7); x.fill();
    }
    // drips
    for (let i = 0; i < 12; i++) {
      const dx = R() * 512, dy = R() * 200;
      x.fillStyle = `rgba(40,26,12,${0.08 + R() * 0.1})`;
      x.fillRect(dx, dy, 1.5 + R() * 2.5, 512 - dy);
    }
    // peeled tears
    for (let i = 0; i < 3; i++) {
      const tx = R() * 512, ty = R() * 400;
      x.fillStyle = 'rgba(14,10,7,.85)';
      x.beginPath();
      x.moveTo(tx, ty); x.lineTo(tx + 26 + R() * 20, ty + 8); x.lineTo(tx + 10, ty + 34 + R() * 20);
      x.closePath(); x.fill();
      x.strokeStyle = 'rgba(190,170,130,.25)'; x.lineWidth = 1;
      x.beginPath(); x.moveTo(tx, ty); x.lineTo(tx + 26 + R() * 20, ty + 8); x.stroke();
    }
    // speckle
    for (let i = 0; i < 700; i++) {
      x.fillStyle = `rgba(${R() > .5 ? '0,0,0' : '215,200,160'},${0.03 + R() * 0.05})`;
      x.fillRect(R() * 512, R() * 512, 1.4, 1.4);
    }
    /* --- wainscot: bottom 34% is painted panelling ----------------------- */
    const wy = 512 * 0.66;
    x.fillStyle = '#2c2015'; x.fillRect(0, wy, 512, 512 - wy);
    // chair rail
    x.fillStyle = 'rgba(196,164,116,.28)'; x.fillRect(0, wy, 512, 3);
    x.fillStyle = 'rgba(0,0,0,.6)'; x.fillRect(0, wy + 3, 512, 2);
    // stiles + recessed panels
    for (let sxx = 0; sxx < 512; sxx += 106) {
      x.fillStyle = 'rgba(0,0,0,.5)'; x.fillRect(sxx, wy, 3, 512 - wy);
      x.fillStyle = 'rgba(150,116,74,.10)';
      x.fillRect(sxx + 12, wy + 16, 82, 512 - wy - 44);
      x.strokeStyle = 'rgba(0,0,0,.55)'; x.lineWidth = 2;
      x.strokeRect(sxx + 12, wy + 16, 82, 512 - wy - 44);
    }
    x.fillStyle = 'rgba(0,0,0,.5)'; x.fillRect(0, 506, 512, 6);
    return finish(c, { repeat: true });
  });
}

/* ------------------------------------------------------- plaster/ceiling */
function paintPlaster(base, seed, rings) {
  return cached('pl' + base + seed, () => {
    const [c, x] = cv(512, 512);
    const R = rng(seed);
    x.fillStyle = base; x.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 520; i++) {
      const g = 0.5 + R() * 0.5;
      x.fillStyle = `rgba(${g > .6 ? '225,218,204' : '20,16,12'},${0.02 + R() * 0.05})`;
      x.beginPath(); x.arc(R() * 512, R() * 512, 3 + R() * 26, 0, 7); x.fill();
    }
    // cracks
    for (let i = 0; i < 6; i++) {
      let px = R() * 512, py = R() * 512;
      x.strokeStyle = 'rgba(28,22,16,.6)'; x.lineWidth = 0.9;
      x.beginPath(); x.moveTo(px, py);
      const segs = 6 + (R() * 8 | 0);
      for (let sgi = 0; sgi < segs; sgi++) {
        px += (R() - .5) * 70; py += (R() - .3) * 60;
        x.lineTo(px, py);
        if (R() < 0.3) { x.moveTo(px, py); x.lineTo(px + (R() - .5) * 40, py + (R() - .5) * 40); x.moveTo(px, py); }
      }
      x.stroke();
    }
    // water rings
    for (let i = 0; i < rings; i++) {
      const wx = R() * 512, wy2 = R() * 512, wr = 20 + R() * 60;
      for (let rr = wr; rr > 6; rr -= 7) {
        x.strokeStyle = `rgba(96,66,30,${0.05 + R() * 0.07})`;
        x.lineWidth = 2 + R() * 3;
        x.beginPath(); x.arc(wx, wy2, rr, 0, 7); x.stroke();
      }
    }
    return finish(c, { repeat: true });
  });
}

/* ------------------------------------------------------------------ tile */
function paintTile() {
  return cached('tile', () => {
    const [c, x] = cv(512, 512);
    const R = rng(909);
    x.fillStyle = '#181410'; x.fillRect(0, 0, 512, 512);
    const cs = 60, g = 4;
    for (let iy = 0; iy < 8; iy++)
      for (let ix = 0; ix < 8; ix++) {
        const dark = (ix + iy) % 2 === 0;
        const lx = (R() - .5) * 22;
        x.fillStyle = dark ? `rgb(${26 + lx},${23 + lx},${20 + lx})` : `rgb(${134 + lx},${125 + lx},${110 + lx})`;
        x.fillRect(ix * 64 + g, iy * 64 + g, cs, cs);
        if (!dark && R() < 0.4) { // glazed streak
          x.strokeStyle = 'rgba(255,255,245,.06)'; x.lineWidth = 5;
          x.beginPath(); x.moveTo(ix * 64 + 8, iy * 64 + 50); x.lineTo(ix * 64 + 50, iy * 64 + 10); x.stroke();
        }
        if (R() < 0.22) { // chipped corner
          x.fillStyle = 'rgba(10,8,6,.7)';
          x.beginPath();
          x.moveTo(ix * 64 + g, iy * 64 + g);
          x.lineTo(ix * 64 + g + 14, iy * 64 + g);
          x.lineTo(ix * 64 + g, iy * 64 + g + 14);
          x.closePath(); x.fill();
        }
      }
    for (let i = 0; i < 26; i++) {
      const g2 = x.createRadialGradient(R() * 512, R() * 512, 2, R() * 512, R() * 512, 40 + R() * 50);
      g2.addColorStop(0, 'rgba(30,22,12,.14)'); g2.addColorStop(1, 'rgba(30,22,12,0)');
      x.fillStyle = g2; x.fillRect(0, 0, 512, 512);
    }
    return finish(c, { repeat: true });
  });
}

/* ---------------------------------------------------------------- fabrics */
function paintFabric(hex, seed) {
  return cached('fb' + hex + seed, () => {
    const [c, x] = cv(256, 256);
    const R = rng(seed);
    x.fillStyle = hex; x.fillRect(0, 0, 256, 256);
    for (let yy = 0; yy < 256; yy += 2) {
      x.fillStyle = `rgba(${yy % 4 ? '0,0,0' : '255,250,235'},${0.05 + R() * 0.03})`;
      x.fillRect(0, yy, 256, 1);
    }
    for (let i = 0; i < 9; i++) { // crushed wrinkles
      x.strokeStyle = `rgba(0,0,0,${0.05 + R() * 0.06})`;
      x.lineWidth = 6 + R() * 14;
      x.beginPath();
      x.moveTo(-20, R() * 256);
      x.quadraticCurveTo(128, R() * 256, 276, R() * 256);
      x.stroke();
    }
    for (let i = 0; i < 5; i++) {
      const g = x.createRadialGradient(R() * 256, R() * 256, 2, R() * 256, R() * 256, 30 + R() * 40);
      g.addColorStop(0, 'rgba(12,8,4,.16)'); g.addColorStop(1, 'rgba(12,8,4,0)');
      x.fillStyle = g; x.fillRect(0, 0, 256, 256);
    }
    return finish(c, { repeat: true });
  });
}

function paintCurtain() {
  return cached('curtain', () => {
    const [c, x] = cv(256, 256);
    const R = rng(5150);
    x.fillStyle = '#2b2320'; x.fillRect(0, 0, 256, 256);
    for (let f = 0; f < 10; f++) {
      const fw = 25.6;
      x.fillStyle = `rgba(${f % 2 ? '8,5,4' : '120,100,86'},${0.10 + R() * 0.08})`;
      x.fillRect(f * fw, 0, fw, 256);
    }
    for (let i = 0; i < 7; i++) { // moth holes
      x.globalCompositeOperation = 'destination-out';
      x.beginPath(); x.arc(R() * 256, R() * 256, 1.5 + R() * 3, 0, 7); x.fill();
      x.globalCompositeOperation = 'source-over';
    }
    // frayed hem
    x.clearRect(0, 246, 256, 10);
    for (let i = 0; i < 40; i++) x.fillRect(R() * 256, 244 + R() * 8, 1.5, 4 + R() * 8);
    return finish(c, { repeat: false });
  });
}

function paintRunner() {
  return cached('runner', () => {
    const [c, x] = cv(256, 512);
    const R = rng(1717);
    x.fillStyle = '#431d1a'; x.fillRect(0, 0, 256, 512);
    x.strokeStyle = 'rgba(200,176,130,.5)'; x.lineWidth = 3;
    x.strokeRect(14, 14, 228, 484);
    x.strokeStyle = 'rgba(200,176,130,.25)'; x.lineWidth = 1.4;
    x.strokeRect(24, 24, 208, 464);
    for (let mz = 60; mz < 460; mz += 80) { // medallion chain
      x.save(); x.translate(128, mz);
      x.rotate(Math.PI / 4);
      x.strokeStyle = 'rgba(206,182,136,.4)'; x.lineWidth = 2;
      x.strokeRect(-22, -22, 44, 44);
      x.restore();
      x.fillStyle = 'rgba(206,182,136,.28)';
      x.beginPath(); x.arc(128, mz, 4, 0, 7); x.fill();
    }
    for (let i = 0; i < 900; i++) {
      x.fillStyle = `rgba(${R() > .5 ? '0,0,0' : '190,160,110'},${0.04 + R() * 0.06})`;
      x.fillRect(R() * 256, R() * 512, 1.6, 1.6);
    }
    // fringe
    for (let i = 0; i < 46; i++) {
      x.fillStyle = 'rgba(200,178,132,.5)';
      x.fillRect(i * 5.6 + 4, 0, 2, 10); x.fillRect(i * 5.6 + 4, 502, 2, 10);
    }
    return finish(c, { repeat: false });
  });
}

/* -------------------------------------------------------------- portraits */
function paintPortrait(seed, scratched) {
  return cached('pt' + seed + (scratched ? 's' : ''), () => {
    const [c, x] = cv(256, 256);
    const R = rng(seed);
    // murky backdrop
    const bg = x.createRadialGradient(128, 110, 20, 128, 128, 190);
    bg.addColorStop(0, '#2c2115'); bg.addColorStop(1, '#120c07');
    x.fillStyle = bg; x.fillRect(0, 0, 256, 256);
    // shoulders / garment
    x.fillStyle = '#1d1712';
    x.beginPath();
    x.moveTo(28, 256); x.quadraticCurveTo(60, 172, 128, 166);
    x.quadraticCurveTo(196, 172, 228, 256); x.closePath(); x.fill();
    if (R() < 0.5) { x.fillStyle = 'rgba(212,204,186,.14)'; x.beginPath(); x.moveTo(108, 176); x.lineTo(128, 208); x.lineTo(148, 176); x.closePath(); x.fill(); }
    // neck + head
    x.fillStyle = '#8f7c66'; x.fillRect(114, 138, 28, 34);
    x.save();
    x.translate(128, 96); x.rotate((R() - .5) * 0.12);
    x.fillStyle = '#9c8874';
    x.beginPath(); x.ellipse(0, 0, 34, 44, 0, 0, 7); x.fill();
    // shading crescents
    x.fillStyle = 'rgba(30,20,12,.4)';
    x.beginPath(); x.ellipse(-14, 4, 20, 38, 0.2, 0, 7); x.fill();
    x.fillStyle = '#9c8874';
    x.beginPath(); x.ellipse(6, 2, 24, 40, 0, 0, 7); x.fill();
    // hair
    x.fillStyle = '#150e08';
    x.beginPath(); x.ellipse(0, -26, 36, 24, 0, Math.PI, 0); x.fill();
    x.fillRect(-36, -30, 12, 40 + R() * 20); x.fillRect(24, -30, 12, 40 + R() * 20);
    // eyes — misaligned, milk-blind or hollow
    const ey = 2, exl = -14 + (R() - .5) * 4, exr = 14 + (R() - .5) * 4;
    x.fillStyle = 'rgba(20,12,8,.85)';
    x.beginPath(); x.ellipse(exl, ey, 6.5, 4.5, 0, 0, 7); x.fill();
    x.beginPath(); x.ellipse(exr, ey, 6.5, 4.5, 0, 0, 7); x.fill();
    if (R() < 0.55) {
      x.fillStyle = 'rgba(212,206,190,.8)';
      x.beginPath(); x.arc(exl + 1, ey, 2.6, 0, 7); x.arc(exr - 1, ey, 2.6, 0, 7); x.fill();
      x.fillStyle = '#0a0705';
      x.beginPath(); x.arc(exl + 2, ey + 1, 1, 0, 7); x.arc(exr - 2, ey, 1, 0, 7); x.fill();
    }
    // nose + mouth
    x.strokeStyle = 'rgba(40,26,16,.7)'; x.lineWidth = 1.6;
    x.beginPath(); x.moveTo(0, ey + 6); x.quadraticCurveTo(3, ey + 16, -2, ey + 18); x.stroke();
    x.fillStyle = 'rgba(24,14,8,.9)';
    x.beginPath(); x.arc(-4, ey + 20, 1.6, 0, 7); x.arc(4, ey + 20, 1.6, 0, 7); x.fill();
    x.strokeStyle = 'rgba(30,18,10,.9)'; x.lineWidth = 2;
    const mw = 10 + R() * 6;
    if (R() < 0.4) { // faint asymmetric smirk
      x.beginPath(); x.moveTo(-mw, ey + 30); x.quadraticCurveTo(2, ey + 33 + R() * 3, mw, ey + 28); x.stroke();
    } else {
      x.beginPath(); x.moveTo(-mw, ey + 31); x.quadraticCurveTo(0, ey + 29, mw, ey + 31); x.stroke();
    }
    // sunken cheeks
    x.fillStyle = 'rgba(28,18,10,.35)';
    x.beginPath(); x.ellipse(-20, 16, 7, 12, 0.3, 0, 7); x.fill();
    x.beginPath(); x.ellipse(20, 16, 7, 12, -0.3, 0, 7); x.fill();
    x.restore();
    // craquelure
    for (let i = 0; i < 70; i++) {
      x.strokeStyle = `rgba(${R() > .5 ? '230,220,200' : '10,6,3'},${0.08 + R() * 0.1})`;
      x.lineWidth = 0.6;
      let px = R() * 256, py = R() * 256;
      x.beginPath(); x.moveTo(px, py);
      for (let s = 0; s < 3; s++) { px += (R() - .5) * 26; py += (R() - .5) * 26; x.lineTo(px, py); }
      x.stroke();
    }
    if (scratched) { // the ruined face
      x.lineCap = 'round';
      for (let i = 0; i < 26; i++) {
        x.strokeStyle = `rgba(8,5,3,${0.6 + R() * 0.4})`;
        x.lineWidth = 3 + R() * 6;
        const ax = 128 + (R() - .5) * 70, ay = 96 + (R() - .5) * 80;
        x.beginPath(); x.moveTo(ax, ay);
        x.lineTo(ax + (R() - .5) * 60, ay + (R() - .5) * 60);
        x.stroke();
      }
    }
    // varnish gloom
    const vg = x.createRadialGradient(128, 128, 60, 128, 128, 185);
    vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.55)');
    x.fillStyle = vg; x.fillRect(0, 0, 256, 256);
    return finish(c);
  });
}

/* ------------------------------------------------------------ the entity */
function paintGhoul(mode) {
  return cached('gh' + mode, () => {
    const [c, x] = cv(512, 512);
    const R = rng(mode.length * 999 + 13);
    // hooded pallor bleeding to dark at edges (composites onto the skull)
    const base = x.createRadialGradient(256, 250, 60, 256, 256, 270);
    base.addColorStop(0, '#8d8578'); base.addColorStop(0.72, '#5d5a52'); base.addColorStop(1, '#17151a');
    x.fillStyle = base; x.fillRect(0, 0, 512, 512);
    // mottled corpse skin
    for (let i = 0; i < 240; i++) {
      x.fillStyle = `rgba(${R() > .5 ? '104,112,96' : '58,50,44'},${0.05 + R() * 0.1})`;
      x.beginPath(); x.arc(R() * 512, R() * 512, 4 + R() * 22, 0, 7); x.fill();
    }
    // temples / veins
    x.strokeStyle = 'rgba(88,60,84,.35)'; x.lineWidth = 1.4;
    for (let i = 0; i < 8; i++) {
      let vx = 256 + (R() - .5) * 300, vy = 120 + R() * 160;
      x.beginPath(); x.moveTo(vx, vy);
      for (let s = 0; s < 4; s++) { vx += (R() - .5) * 40; vy += (R() - .5) * 40; x.lineTo(vx, vy); }
      x.stroke();
    }
    // eye pits
    const ey = 218, eo = 74;
    for (const sgn of [-1, 1]) {
      const ex = 256 + sgn * eo;
      const pit = x.createRadialGradient(ex, ey, 4, ex, ey, 46);
      pit.addColorStop(0, '#000'); pit.addColorStop(0.75, '#0c0a0e'); pit.addColorStop(1, 'rgba(20,16,20,0)');
      x.fillStyle = pit;
      x.beginPath(); x.ellipse(ex, ey, 44, 36, 0, 0, 7); x.fill();
      // bruised rim
      x.strokeStyle = 'rgba(70,44,66,.5)'; x.lineWidth = 5;
      x.beginPath(); x.ellipse(ex, ey, 44, 36, 0, 0, 7); x.stroke();
      // pinprick gleam
      const ic = mode === 'chase' ? '#ff2418' : mode === 'burn' ? '#ffa53c' : '#cdd6da';
      const ig = x.createRadialGradient(ex, ey, 1, ex, ey, 10);
      ig.addColorStop(0, ic); ig.addColorStop(1, 'rgba(0,0,0,0)');
      x.fillStyle = ig;
      x.beginPath(); x.arc(ex, ey, 10, 0, 7); x.fill();
    }
    // nasal aperture
    x.fillStyle = 'rgba(4,3,4,.92)';
    x.beginPath();
    x.moveTo(256, 258); x.quadraticCurveTo(242, 292, 250, 306);
    x.quadraticCurveTo(256, 314, 262, 306); x.quadraticCurveTo(270, 292, 256, 258);
    x.fill();
    // cheek hollows
    x.fillStyle = 'rgba(10,8,10,.5)';
    x.beginPath(); x.ellipse(178, 300, 26, 44, 0.4, 0, 7); x.fill();
    x.beginPath(); x.ellipse(334, 300, 26, 44, -0.4, 0, 7); x.fill();
    // mouth
    const teeth = () => {
      x.fillStyle = '#cabf9d';
      for (let ti = 0; ti < 9; ti++) {
        const tw = 20, tx = 256 - 90 + ti * tw + (ti % 2) * 3;
        x.fillRect(tx, 352, tw - 5, 16 + (ti % 3) * 5);
      }
    };
    if (mode === 'scream') {
      x.fillStyle = '#050305';
      x.beginPath(); x.ellipse(256, 396, 74, 92, 0, 0, 7); x.fill();
      x.fillStyle = '#3d1210';
      x.beginPath(); x.ellipse(256, 448, 30, 26, 0, 0, 7); x.fill(); // throat
      teeth();
      x.save(); x.translate(256, 396); x.scale(1, -1); x.translate(-256, -396); teeth(); x.restore();
      // stress cracks around the jaw
      x.strokeStyle = 'rgba(20,14,12,.7)'; x.lineWidth = 2;
      for (let i = 0; i < 10; i++) {
        x.beginPath();
        const sx2 = 256 + (R() - .5) * 190, sy2 = 310 + R() * 30;
        x.moveTo(sx2, sy2); x.lineTo(sx2 + (R() - .5) * 30, sy2 + 26 + R() * 30); x.stroke();
      }
    } else if (mode === 'grin') {
      x.strokeStyle = '#1a1210'; x.lineWidth = 7;
      x.beginPath(); x.moveTo(150, 366); x.quadraticCurveTo(256, 428, 362, 360); x.stroke();
      x.fillStyle = '#060405';
      x.beginPath(); x.moveTo(156, 368); x.quadraticCurveTo(256, 424, 356, 362);
      x.quadraticCurveTo(256, 402, 156, 368); x.fill();
      teeth();
    } else { // idle: lipless too-wide line
      x.strokeStyle = '#120c0c'; x.lineWidth = 6;
      x.beginPath(); x.moveTo(140, 372); x.quadraticCurveTo(256, 386, 372, 368); x.stroke();
      x.fillStyle = 'rgba(202,191,157,.5)';
      for (let ti = 0; ti < 12; ti++) x.fillRect(150 + ti * 18, 372 + Math.sin(ti) * 3, 10, 7);
    }
    // encroaching dark at the borders
    const dk = x.createRadialGradient(256, 256, 150, 256, 256, 262);
    dk.addColorStop(0, 'rgba(10,8,12,0)'); dk.addColorStop(1, 'rgba(10,8,12,1)');
    x.fillStyle = dk; x.fillRect(0, 0, 512, 512);
    return finish(c);
  });
}

/* ------------------------------------------------- tatters / strips / web */
function paintTatter() {
  return cached('tatter', () => {
    const [c, x] = cv(128, 128);
    x.clearRect(0, 0, 128, 128);
    const R = rng(666);
    for (let s = 0; s < 7; s++) { // hanging shreds
      const sx = s * 18 + R() * 6;
      x.fillStyle = `rgba(${16 + R() * 10},${13 + R() * 8},${16 + R() * 8},1)`;
      x.fillRect(sx, 0, 14, 60 + R() * 60);
      // ragged hem
      x.clearRect(sx + R() * 10, 100 + R() * 26, 14, 30);
    }
    x.fillStyle = 'rgba(60,52,58,.25)';
    for (let i = 0; i < 40; i++) x.fillRect(R() * 128, R() * 128, 2, 2);
    return finish(c);
  });
}

function paintWeb() {
  return cached('web', () => {
    const [c, x] = cv(256, 256);
    x.clearRect(0, 0, 256, 256);
    const R = rng(2828);
    x.strokeStyle = 'rgba(214,208,196,.4)'; x.lineWidth = 1;
    const spokes = [];
    for (let i = 0; i <= 9; i++) {
      const a = (i / 9) * Math.PI / 2 + (R() - .5) * 0.08;
      const len = 200 + R() * 60;
      const ex = Math.cos(a) * len, ey2 = Math.sin(a) * len;
      x.beginPath(); x.moveTo(0, 0); x.lineTo(ex, ey2); x.stroke();
      spokes.push([ex, ey2]);
    }
    for (let ri = 1; ri <= 7; ri++) {
      const rr = ri * ri * 5.4;
      for (let si = 0; si < spokes.length - 1; si++) {
        if (R() < 0.2) continue; // broken strands
        const [ax, ay] = spokes[si], [bx, by] = spokes[si + 1];
        const al = Math.hypot(ax, ay), bl = Math.hypot(bx, by);
        const p1x = ax / al * rr, p1y = ay / al * rr;
        const p2x = bx / bl * rr, p2y = by / bl * rr;
        x.beginPath(); x.moveTo(p1x, p1y);
        x.quadraticCurveTo((p1x + p2x) / 2 + 4, (p1y + p2y) / 2 + 6, p2x, p2y);
        x.stroke();
        if (R() < 0.3) { x.fillStyle = 'rgba(230,226,214,.5)'; x.beginPath(); x.arc((p1x + p2x) / 2, (p1y + p2y) / 2 + 4, 1.2, 0, 7); x.fill(); }
      }
    }
    return finish(c);
  });
}

/* ------------------------------------------------- light cookies & sprites */
function paintCookie() {
  return cached('cookie', () => {
    const [c, x] = cv(256, 256);
    const R = rng(1234);
    const g = x.createRadialGradient(128, 128, 8, 128, 128, 128);
    g.addColorStop(0, '#ffffff'); g.addColorStop(0.55, '#bdbdbd'); g.addColorStop(1, '#2c2c2c');
    x.fillStyle = g; x.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 70; i++) { // dirt in the reflector
      x.fillStyle = `rgba(0,0,0,${0.06 + R() * 0.12})`;
      x.beginPath(); x.arc(R() * 256, R() * 256, 3 + R() * 16, 0, 7); x.fill();
    }
    for (let i = 0; i < 5; i++) {
      x.strokeStyle = 'rgba(0,0,0,.1)'; x.lineWidth = 2 + R() * 3;
      x.beginPath(); x.arc(128, 128, 30 + R() * 90, R() * 6, R() * 6 + 2); x.stroke();
    }
    return finish(c, { srgb: false });
  });
}

function paintFlame() {
  return cached('flame', () => {
    const [c, x] = cv(64, 64);
    const g = x.createRadialGradient(32, 40, 2, 32, 36, 30);
    g.addColorStop(0, 'rgba(255,252,238,1)');
    g.addColorStop(0.25, 'rgba(255,214,122,.95)');
    g.addColorStop(0.55, 'rgba(255,138,30,.55)');
    g.addColorStop(1, 'rgba(255,90,10,0)');
    x.fillStyle = g;
    x.beginPath(); x.ellipse(32, 36, 15, 24, 0, 0, 7); x.fill();
    return finish(c);
  });
}

function paintDust() {
  return cached('dust', () => {
    const [c, x] = cv(32, 32);
    const g = x.createRadialGradient(16, 16, 1, 16, 16, 15);
    g.addColorStop(0, 'rgba(255,250,235,1)'); g.addColorStop(1, 'rgba(255,250,235,0)');
    x.fillStyle = g; x.fillRect(0, 0, 32, 32);
    return finish(c, { srgb: false });
  });
}

/* -------------------------------------------------------------- paperwork */
function paintPaper() {
  return cached('paper', () => {
    const [c, x] = cv(256, 256);
    const R = rng(808);
    x.fillStyle = '#cdb894'; x.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 1400; i++) {
      x.strokeStyle = `rgba(${R() > .5 ? '120,92,50' : '240,228,196'},${0.05 + R() * 0.05})`;
      const lx = R() * 256, ly = R() * 256;
      x.beginPath(); x.moveTo(lx, ly); x.lineTo(lx + (R() - .5) * 8, ly + (R() - .5) * 8); x.stroke();
    }
    for (let i = 0; i < 8; i++) { // foxing
      x.fillStyle = `rgba(112,74,30,${0.08 + R() * 0.1})`;
      x.beginPath(); x.arc(R() * 256, R() * 256, 4 + R() * 14, 0, 7); x.fill();
    }
    x.fillStyle = 'rgba(60,40,16,.35)'; x.fillRect(0, 118, 256, 2); // fold
    x.fillStyle = 'rgba(255,244,214,.25)'; x.fillRect(0, 120, 256, 1);
    const eg = x.createRadialGradient(128, 128, 90, 128, 128, 190);
    eg.addColorStop(0, 'rgba(60,40,16,0)'); eg.addColorStop(1, 'rgba(60,40,16,.4)');
    x.fillStyle = eg; x.fillRect(0, 0, 256, 256);
    return finish(c);
  });
}

/* -------------------------------------------------------- clock dial etc. */
function paintClockFace() {
  return cached('clk', () => {
    const [c, x] = cv(256, 256);
    x.fillStyle = '#d8ccb2'; x.beginPath(); x.arc(128, 128, 124, 0, 7); x.fill();
    x.strokeStyle = '#3a2c18'; x.lineWidth = 6;
    x.beginPath(); x.arc(128, 128, 118, 0, 7); x.stroke();
    x.fillStyle = '#2c2014';
    x.font = '28px Georgia'; x.textAlign = 'center'; x.textBaseline = 'middle';
    const rom = ['XII', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'];
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
      x.fillText(rom[i], 128 + Math.cos(a) * 92, 128 + Math.sin(a) * 92 + 2);
    }
    // stopped at eleven minutes past three — the hour nobody came home
    x.strokeStyle = '#1a120a'; x.lineCap = 'round';
    x.lineWidth = 7; x.beginPath(); x.moveTo(128, 128); x.lineTo(128 + 52, 128 + 30); x.stroke();
    x.lineWidth = 5; x.beginPath(); x.moveTo(128, 128); x.lineTo(128 - 20, 128 - 78); x.stroke();
    x.fillStyle = '#1a120a'; x.beginPath(); x.arc(128, 128, 7, 0, 7); x.fill();
    // water stain across VII
    x.fillStyle = 'rgba(96,66,30,.25)';
    x.beginPath(); x.arc(70, 190, 34, 0, 7); x.fill();
    return finish(c);
  });
}

/* ============================================================ public API */
export const Tex = {
  setMaxAniso(n) { MAX_ANISO = n; },

  wood: () => paintWood('#33241a', false),
  woodDark: () => paintWood('#33241a', true),

  wallpaper: (variant = 0) => paintWallpaper(variant),
  plaster: () => paintPlaster('#5d5850', 311, 4),
  ceiling: () => paintPlaster('#6a655c', 717, 7),
  tile: () => paintTile(),

  fabric: (hex, seed = 1) => paintFabric(hex, seed),
  curtain: () => paintCurtain(),
  runner: () => paintRunner(),

  portrait: (seed, scratched = false) => paintPortrait(seed, scratched),
  ghoul: (mode) => paintGhoul(mode),

  tatter: () => paintTatter(),
  web: () => paintWeb(),
  cookie: () => paintCookie(),
  flame: () => paintFlame(),
  dust: () => paintDust(),
  paper: () => paintPaper(),
  clockFace: () => paintClockFace()
};
```

**src/world/House.js**

```js
// The house itself: floor plan, walls, doors, furniture, lights, items,
// cobwebs, dust. Builds a fresh instance into any parent group so a run can
// be discarded and rebuilt cleanly.
import * as THREE from 'three';
import { Tex } from './Textures.js';

export const WALL_H = 3;
export const HALF_T = 0.12;

export const ROOMS = {
  study:   { x0: -10, x1: -4, z0: -8, z1: -2 },
  bedroom: { x0: -4,  x1: 4,  z0: -8, z1: -2 },
  kitchen: { x0: 4,   x1: 10, z0: -8, z1: -2 },
  hall:    { x0: -10, x1: 10, z0: -2, z1: 2 },
  living:  { x0: -10, x1: -4, z0: 2,  z1: 8 },
  foyer:   { x0: -4,  x1: 4,  z0: 2,  z1: 8 },
  dining:  { x0: 4,   x1: 10, z0: 2,  z1: 8 }
};

export const GHOST_LURK = [
  [-9, 0], [9, 0], [0, -1], [-7, -5], [7, -5], [0, -5],
  [-7, 5], [7, 5], [0, 6.5], [-9, -6], [9, -6]
];

/* Randomized key anchors: one is drawn from each room's pool every run. */
export const KEY_SPOTS = {
  kitchen: [
    { pos: [8.7, 0.98, -6.9], hint: 'the kitchen counter' },
    { pos: [5.4, 0.86, -7.3], hint: 'the kitchen table' },
    { pos: [9.5, 1.62, -3.2], hint: 'the kitchen shelf' }
  ],
  study: [
    { pos: [-8.6, 0.84, -7.2], hint: 'the study desk' },
    { pos: [-9.5, 1.42, -4.0], hint: 'the study shelves' },
    { pos: [-5.2, 0.55, -6.4], hint: 'the study armchair' }
  ],
  bedroom: [
    { pos: [3.4, 1.06, -7.2], hint: 'the bedroom dresser' },
    { pos: [-2.9, 0.62, -6.6], hint: 'the nightstand' },
    { pos: [-1.4, 1.62, -7.7], hint: 'the bedroom windowsill' }
  ]
};

export const BATTERY_SPOTS = [
  { pos: [-8.8, 0.56, 6.6] },   // living room side table
  { pos: [9.4, 1.02, 5.2] },    // dining buffet
  { pos: [-3.0, 0.52, 1.55] },  // hallway bench
  { pos: [9.6, 0.98, -6.9] }    // kitchen counter end
];

export const NOTE_DEFS = [
  {
    id: 'foyer',
    pos: [0.9, 0.86, 6.9], rotY: 0.4,
    title: 'Scrawled page \u2014 foyer table',
    body: 'I woke on the doormat.\n\nThe door will not answer me. Neither will the windows. There were three keys in the dream I fell out of \u2014 brass, warm, humming like struck bells.\n\nKitchen. Study. Bedroom.\n\nFind them before it finishes counting my breaths.\n\n\u2014 R.'
  },
  {
    id: 'study',
    pos: [-8.2, 0.84, -6.6], rotY: -0.7,
    title: 'Journal \u2014 final entry',
    body: 'It hates the light. Not daylight \u2014 there is no day in this house \u2014 but a held beam. Pin it. Hold the torch steady on its heart until the burning takes hold and it comes apart like smoke in a fist.\n\nIt will tear itself back together. Eight breaths, perhaps ten. Spend those running.\n\nThe previous family hoarded torch cells wherever they hid things from themselves. Search the parlours.'
  }
];

/* ===================================================================== */
class Door {
  /**
   * axis: 'x' wall runs along X (door faces Z traffic); 'z' wall runs along Z.
   */
  constructor(spec) {
    Object.assign(this, spec); // x,z,axis,width,height,swing,kind,locked
    this.openT = 0; this.target = 0; this.speed = 2.0;
    this.wasMoving = false; this.wantThunk = false; this.jiggleT = -1;
    this.baseRot = 0;

    const g = new THREE.Group();
    g.position.set(this.x, 0, this.z);
    if (this.axis === 'z') g.rotation.y = Math.PI / 2;
    this.pivot = g;

    const mat = this.kind === 'front' ? MAT.frontDoor : MAT.door;
    const geo = new THREE.BoxGeometry(this.width, this.height, 0.07);
    geo.translate(this.width / 2, this.height / 2, 0);
    this.panel = new THREE.Mesh(geo, mat);
    this.panel.castShadow = true; this.panel.receiveShadow = true;
    g.add(this.panel);

    // moulding insets
    const insGeo = new THREE.BoxGeometry(this.width * 0.62, this.height * 0.34, 0.02);
    for (const fy of [0.28, 0.66]) {
      const ins = new THREE.Mesh(insGeo, MAT.trim);
      ins.position.set(this.width / 2, this.height * fy, 0.045);
      g.add(ins);
    }
    // knob both faces
    const kn = new THREE.Mesh(Door.knobGeo, MAT.brass);
    kn.position.set(this.width - 0.14, this.height * 0.46, 0.06);
    g.add(kn);
    const kn2 = kn.clone(); kn2.position.z = -0.06; g.add(kn2);
    if (this.kind === 'front') {
      const stud = new THREE.Mesh(Door.studGeo, MAT.iron);
      for (let i = 0; i < 6; i++) {
        const s = stud.clone();
        s.position.set(this.width / 2 + (i % 2 ? 0.28 : -0.28), 0.5 + Math.floor(i / 2) * 0.7, 0.045);
        g.add(s);
      }
      const slot = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.06, 0.02), MAT.iron);
      slot.position.set(this.width / 2, this.height * 0.78, 0.04);
      g.add(slot);
    }
    // collider covering the closed doorway
    const t = 0.16;
    if (this.axis === 'x') {
      this.collider = { x0: this.x, x1: this.x + this.width, z0: this.z - t, z1: this.z + t, active: true };
    } else {
      this.collider = { x0: this.x - t, x1: this.x + t, z0: this.z, z1: this.z + this.width, active: true };
    }
  }
  set openFraction(v) { this.openT = v; this.target = v; this.pivot.rotation.y = this.baseRot + v * 1.85 * this.swing; this.collider.active = v < 0.3; }
  toggle() {
    if (this.locked) return false;
    this.target = this.target > 0.5 ? 0 : 1;
    this.speed = 2.0;
    return true;
  }
  slam() {
    if (this.openT < 0.05) return false;
    this.target = 0; this.speed = 11; this.wantThunk = true;
    return true;
  }
  rattle() { this.jiggleT = 0; }
  update(dt, audio) {
    if (this.jiggleT >= 0) {
      this.jiggleT += dt;
      this.pivot.rotation.y = this.baseRot + Math.sin(this.jiggleT * 40) * 0.02 * Math.max(0, 1 - this.jiggleT * 2.5);
      if (this.jiggleT > 0.5) { this.jiggleT = -1; this.pivot.rotation.y = this.baseRot; }
    }
    const moving = Math.abs(this.target - this.openT) > 0.001;
    if (moving && !this.wasMoving) audio?.doorCreak(this.kind === 'front');
    if (moving) {
      const dir = Math.sign(this.target - this.openT);
      this.openT += dir * this.speed * dt;
      if ((dir > 0 && this.openT >= this.target) || (dir < 0 && this.openT <= this.target)) {
        this.openT = this.target;
        if (this.wantThunk) { audio?.slamBoom(); this.wantThunk = false; }
        else audio?.doorLatch();
      }
      this.pivot.rotation.y = this.baseRot + this.openT * 1.85 * this.swing;
      this.collider.active = this.openT < 0.3;
    }
    this.wasMoving = moving;
  }
}
Door.knobGeo = new THREE.SphereGeometry(0.045, 10, 8);
Door.studGeo = new THREE.SphereGeometry(0.035, 8, 6);

/* ===================================================================== */
let MAT = {};
let GEO = {};

export class House {
  constructor(parent) {
    this.group = new THREE.Group();
    parent.add(this.group);

    this.solids = [];       // circle-vs-AABB colliders
    this.doors = {};        // named Door instances
    this.pickTargets = [];  // raycastables (items + door panels)
    this.updatables = [];   // per-frame closures
    this.flames = [];
    this.flickerLights = [];

    this._materials();
    this._shell();
    this._doorsAndFrames();
    this._furnishings();
    this._lights();
    this._items();
    this._cobwebs();
    this._dust();

    this.time = 0;
    this.lastTickWhole = -1;
  }

  /* ---------------------------------------------------------- materials */
  _materials() {
    const S = (o) => new THREE.MeshStandardMaterial(o);
    const wp = Tex.wallpaper(0); wp.repeat.set(1.8, 1);
    const wp2 = Tex.wallpaper(1); wp2.repeat.set(1.4, 1);
    const wd = Tex.wood(); wd.repeat.set(7, 5);
    const tl = Tex.tile(); tl.repeat.set(4, 3);
    const ce = Tex.ceiling(); ce.repeat.set(5, 4);
    const rn = Tex.runner();
    const fb1 = Tex.fabric('#39424a', 11); fb1.repeat.set(2, 2);
    const fb2 = Tex.fabric('#4a3a35', 22); fb2.repeat.set(2, 2);
    const mt = Tex.plaster(); mt.repeat.set(2, 1.4);

    MAT = {
      floor: S({ map: wd, roughness: 0.82, metalness: 0 }),
      tile: S({ map: tl, roughness: 0.55, metalness: 0.05 }),
      runner: S({ map: rn, roughness: 0.95 }),
      ceil: S({ map: ce, roughness: 0.96 }),
      wallA: S({ map: wp, roughness: 0.92 }),
      wallB: S({ map: wp2, roughness: 0.92 }),
      mortar: S({ map: mt, roughness: 0.95 }),
      trim: S({ map: Tex.woodDark(), roughness: 0.7 }),
      door: S({ map: Tex.woodDark(), roughness: 0.62 }),
      frontDoor: S({ map: Tex.woodDark(), roughness: 0.55, color: 0x8a7a66 }),
      brass: S({ color: 0xb98a3e, metalness: 0.92, roughness: 0.32 }),
      iron: S({ color: 0x2a2c30, metalness: 0.8, roughness: 0.5 }),
      glassNight: S({ color: 0x0b1322, metalness: 0.9, roughness: 0.08, emissive: 0x0a1424, emissiveIntensity: 0.5 }),
      mirror: S({ color: 0x0e141a, metalness: 1, roughness: 0.06 }),
      sofa: S({ map: fb1, roughness: 0.95 }),
      cushion: S({ map: fb2, roughness: 0.95 }),
      sheet: S({ color: 0x8d8578, roughness: 0.95 }),
      blanket: S({ color: 0x41303f, roughness: 0.95 }),
      linen: S({ color: 0xa39a86, roughness: 0.9 }),
      porcelain: S({ color: 0xb9b2a6, roughness: 0.35 }),
      black: S({ color: 0x0c0b0d, roughness: 0.96 }),
      paper: S({ map: Tex.paper(), roughness: 0.9, side: THREE.DoubleSide }),
      curtain: S({ map: Tex.curtain(), roughness: 0.95, side: THREE.DoubleSide }),
      tatter: S({ map: Tex.web(), transparent: true, opacity: 0 }), // placeholder, replaced below
      bookCols: ['#5a3b2e', '#3e4a52', '#6b5636', '#493b4e', '#59493f', '#2f4436']
        .map(cc => S({ color: cc, roughness: 0.9 })),
      flame: new THREE.SpriteMaterial({
        map: Tex.flame(), blending: THREE.AdditiveBlending,
        depthWrite: false, transparent: true
      })
    };
    GEO = {
      box: new THREE.BoxGeometry(1, 1, 1),
      cyl: new THREE.CylinderGeometry(1, 1, 1, 12),
      sph: new THREE.SphereGeometry(1, 12, 10)
    };
  }

  /* ------------------------------------------------------------- helpers */
  _static(mesh, { cast = false, recv = true } = {}) {
    mesh.castShadow = cast; mesh.receiveShadow = recv;
    mesh.matrixAutoUpdate = false; mesh.updateMatrix();
    this.group.add(mesh);
    return mesh;
  }
  _box(w, h, d, mat, x, y, z, ry = 0, opts = {}) {
    const m = new THREE.Mesh(GEO.box, mat);
    m.scale.set(w, h, d); m.position.set(x, y, z); m.rotation.y = ry;
    return this._static(m, opts);
  }
  _solid(cx, cz, hw, hd, tag) {
    const s = { x0: cx - hw, x1: cx + hw, z0: cz - hd, z1: cz + hd, active: true, tag };
    this.solids.push(s); return s;
  }
  /** Axis-aligned wall segment with matched texture repeat. */
  _wall(x0, z0, x1, z1, mat, { h = WALL_H, y = 0, cast = true } = {}) {
    const horiz = Math.abs(x1 - x0) > Math.abs(z1 - z0);
    const len = horiz ? Math.abs(x1 - x0) : Math.abs(z1 - z0);
    const m = mat.clone();
    if (m.map) { m.map = m.map.clone(); m.map.needsUpdate = true; m.map.repeat.set(Math.max(1, len / 2.6), h / WALL_H); }
    const mesh = new THREE.Mesh(GEO.box, m);
    mesh.scale.set(horiz ? len : HALF_T * 2, h, horiz ? HALF_T * 2 : len);
    mesh.position.set((x0 + x1) / 2, y + h / 2, (z0 + z1) / 2);
    this._static(mesh, { cast });
    if (y < 0.1) {
      if (horiz) this._solid((x0 + x1) / 2, (z0 + z1) / 2, len / 2 + HALF_T, HALF_T, 'wall');
      else this._solid((x0 + x1) / 2, (z0 + z1) / 2, HALF_T, len / 2 + HALF_T, 'wall');
    }
    return mesh;
  }
  _lintel(x0, x1, z, mat) { // above a gap in a Z-constant wall
    const w = x1 - x0;
    this._box(w, WALL_H - 2.14, HALF_T * 2, mat, (x0 + x1) / 2, 2.14 + (WALL_H - 2.14) / 2, z);
  }
  _lintelZ(z0, z1, x, mat) {
    const w = z1 - z0;
    this._box(HALF_T * 2, WALL_H - 2.14, w, mat, x, 2.14 + (WALL_H - 2.14) / 2, (z0 + z1) / 2);
  }
  _archJambs(x0, x1, z) {
    this._box(0.14, 2.14, HALF_T * 2 + 0.08, MAT.trim, x0 + 0.07, 1.07, z);
    this._box(0.14, 2.14, HALF_T * 2 + 0.08, MAT.trim, x1 - 0.07, 1.07, z);
    this._box(x1 - x0 + 0.28, 0.16, HALF_T * 2 + 0.08, MAT.trim, (x0 + x1) / 2, 2.22, z);
  }

  /* --------------------------------------------------------------- shell */
  _shell() {
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 16), MAT.floor);
    floor.rotation.x = -Math.PI / 2; floor.position.y = 0;
    this._static(floor, { recv: true });

    // kitchen tile overlay
    const kt = new THREE.Mesh(new THREE.PlaneGeometry(6, 6), MAT.tile);
    kt.rotation.x = -Math.PI / 2; kt.position.set(7, 0.006, -5);
    this._static(kt);

    // rugs
    const run = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 12), MAT.runner);
    run.rotation.x = -Math.PI / 2; run.position.set(0, 0.008, 0);
    this._static(run);
    const lr = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 2.6), MAT.runner);
    lr.rotation.x = -Math.PI / 2; lr.rotation.z = 0.2; lr.position.set(-7, 0.008, 5);
    this._static(lr);
    const br = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 2), MAT.runner);
    br.rotation.x = -Math.PI / 2; br.position.set(-1.2, 0.008, -5.4);
    this._static(br);
    const dm = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.9), MAT.black);
    dm.rotation.x = -Math.PI / 2; dm.position.set(0, 0.007, 7.1);
    this._static(dm);

    // ceiling
    const ceil = new THREE.Mesh(new THREE.PlaneGeometry(20, 16), MAT.ceil);
    ceil.rotation.x = Math.PI / 2; ceil.position.y = WALL_H;
    this._static(ceil);

    // ceiling beams
    for (let bz = -7; bz <= 7; bz += 2.8)
      this._box(20, 0.22, 0.16, MAT.trim, 0, WALL_H - 0.11, bz, 0, { cast: false });

    // perimeter (front door gap at south centre)
    this._wall(-10, -8, 10, -8, MAT.wallA);
    this._wall(-10, -8, -10, 8, MAT.wallA);
    this._wall(10, -8, 10, 8, MAT.wallA);
    this._wall(-10, 8, -0.95, 8, MAT.wallA);
    this._wall(0.95, 8, 10, 8, MAT.wallA);
    this._lintel(-0.95, 0.95, 8, MAT.trim);
    // doorstep
    this._box(2.4, 0.09, 0.7, MAT.mortar, 0, 0.045, 8.35, 0, { cast: false });

    // row dividers
    this._wall(-4, -8, -4, -2, MAT.wallB);
    this._wall(4, -8, 4, -2, MAT.wallB);
    this._wall(-4, 2, -4, 8, MAT.wallB);
    this._wall(4, 2, 4, 8, MAT.wallB);

    // hallway north wall (z=-2): study door / bedroom door / kitchen arch
    this._wall(-10, -2, -7.55, -2, MAT.wallA);
    this._wall(-6.45, -2, -0.55, -2, MAT.wallA);
    this._wall(0.55, -2, 6.2, -2, MAT.wallA);
    this._wall(7.8, -2, 10, -2, MAT.wallA);
    this._lintel(-7.55, -6.45, -2, MAT.trim);
    this._lintel(-0.55, 0.55, -2, MAT.trim);
    this._lintel(6.2, 7.8, -2, MAT.mortar);
    this._archJambs(6.2, 7.8, -2);

    // hallway south wall (z=2): living arch / foyer arch / dining arch
    this._wall(-10, 2, -7.8, 2, MAT.wallA);
    this._wall(-6.2, 2, -2.2, 2, MAT.wallA);
    this._wall(2.2, 2, 6.2, 2, MAT.wallA);
    this._wall(7.8, 2, 10, 2, MAT.wallA);
    this._lintel(-7.8, -6.2, 2, MAT.mortar);
    this._lintel(-2.2, 2.2, 2, MAT.mortar);
    this._lintel(6.2, 7.8, 2, MAT.mortar);
    this._archJambs(-7.8, -6.2, 2);
    this._archJambs(-2.2, 2.2, 2);
    this._archJambs(6.2, 7.8, 2);
  }

  /* ------------------------------------------------------- doors & frames */
  _doorsAndFrames() {
    const mk = (spec) => {
      const d = new Door(spec);
      this.group.add(d.pivot);
      d.pivot.traverse(o => { o.matrixAutoUpdate = true; }); // animated subtree
      this.solids.push(d.collider);
      this.pickTargets.push(d.panel);
      d.panel.userData = { type: 'door', door: d };
      return d;
    };
    this.doors.study = mk({ x: -7.55, z: -2, axis: 'x', width: 1.1, height: 2.14, swing: 1, kind: 'inner', locked: false });
    this.doors.bedroom = mk({ x: -0.55, z: -2, axis: 'x', width: 1.1, height: 2.14, swing: 1, kind: 'inner', locked: false });
    this.doors.front = mk({ x: -0.95, z: 8, axis: 'x', width: 1.9, height: 2.3, swing: 1, kind: 'front', locked: true });
    this.doors.front.openFraction = 0;

    // dead sidelantern by the front door
    const lg = new THREE.Group(); lg.position.set(1.45, 1.9, 7.85);
    const cage = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 0.3, 6, 1, true), MAT.iron);
    const cap = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.12, 6), MAT.iron);
    cap.position.y = 0.2; lg.add(cage, cap);
    this.group.add(lg);
  }

  /* ---------------------------------------------------------- furnishings */
  _shelfFilled(x, y, z, w, ry = 0) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry;
    const R = Math.random;
    for (let row = 0; row < 4; row++) {
      let bx = -w / 2 + 0.05;
      while (bx < w / 2 - 0.08) {
        const bw = 0.03 + R() * 0.035, bh = 0.17 + R() * 0.1;
        const b = new THREE.Mesh(GEO.box, MAT.bookCols[(R() * 6) | 0]);
        b.scale.set(bw, bh, 0.15);
        b.position.set(bx + bw / 2, 0.1 + bh / 2 + row * 0.315, 0);
        if (R() < 0.08) b.rotation.z = 0.14;
        b.castShadow = false; b.receiveShadow = true;
        g.add(b);
        bx += bw + 0.004;
      }
    }
    this.group.add(g);
    return g;
  }
  _bookcase(x, z, ry, w = 1.6) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const body = new THREE.Mesh(GEO.box, MAT.trim);
    body.scale.set(w, 2.2, 0.34); body.position.y = 1.1;
    body.castShadow = true; body.receiveShadow = true; g.add(body);
    const hollow = new THREE.Mesh(GEO.box, MAT.black);
    hollow.scale.set(w - 0.16, 1.9, 0.05); hollow.position.set(0, 1.08, 0.16);
    g.add(hollow);
    this._shelfFilled(0, 0.16, 0.2, w - 0.2).position.add(g.position).applyMatrix4(g.matrix);
    // simpler: nest shelf inside group
    g.children.pop();
    const shelf = this._shelfFilledLocal(g, w - 0.2);
    this.group.add(g);
    const [hx, hz] = ry === 0 ? [x, z + 0.3] : ry === Math.PI / 2 ? [x + 0.3, z] : [x, z - 0.3];
    this._solid(x, z, ry === 0 || ry === Math.PI ? w / 2 : 0.25, ry === 0 || ry === Math.PI ? 0.25 : w / 2, 'furn');
    return { group: g, shelf };
  }
  _shelfFilledLocal(parent, w) {
    const g = new THREE.Group(); g.position.set(0, 0.16, 0.2);
    const R = Math.random;
    for (let row = 0; row < 4; row++) {
      let bx = -w / 2 + 0.05;
      while (bx < w / 2 - 0.08) {
        const bw = 0.03 + R() * 0.035, bh = 0.17 + R() * 0.1;
        const b = new THREE.Mesh(GEO.box, MAT.bookCols[(R() * 6) | 0]);
        b.scale.set(bw, bh, 0.15);
        b.position.set(bx + bw / 2, 0.1 + bh / 2 + row * 0.315, 0);
        if (R() < 0.08) b.rotation.z = 0.14;
        g.add(b);
        bx += bw + 0.004;
      }
    }
    parent.add(g); return g;
  }

  _tableRect(x, z, w, d, h, ry = 0) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const top = new THREE.Mesh(GEO.box, MAT.trim);
    top.scale.set(w, 0.06, d); top.position.y = h;
    top.castShadow = true; top.receiveShadow = true; g.add(top);
    for (const [lx, lz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      const leg = new THREE.Mesh(GEO.box, MAT.trim);
      leg.scale.set(0.07, h, 0.07);
      leg.position.set(lx * (w / 2 - 0.08), h / 2, lz * (d / 2 - 0.08));
      leg.castShadow = true; g.add(leg);
    }
    this.group.add(g);
    return g;
  }
  _chair(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const seat = new THREE.Mesh(GEO.box, MAT.trim);
    seat.scale.set(0.42, 0.05, 0.4); seat.position.y = 0.46;
    seat.castShadow = true; g.add(seat);
    const back = new THREE.Mesh(GEO.box, MAT.trim);
    back.scale.set(0.42, 0.5, 0.04); back.position.set(0, 0.73, -0.18);
    back.castShadow = true; g.add(back);
    for (const [lx, lz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      const leg = new THREE.Mesh(GEO.box, MAT.trim);
      leg.scale.set(0.04, 0.46, 0.04);
      leg.position.set(lx * 0.17, 0.23, lz * 0.16);
      g.add(leg);
    }
    this.group.add(g);
    return g;
  }
  _sofa(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const base = new THREE.Mesh(GEO.box, MAT.sofa);
    base.scale.set(1.9, 0.42, 0.85); base.position.y = 0.24;
    base.castShadow = true; base.receiveShadow = true; g.add(base);
    const back = new THREE.Mesh(GEO.box, MAT.sofa);
    back.scale.set(1.9, 0.62, 0.24); back.position.set(0, 0.72, -0.32);
    back.castShadow = true; g.add(back);
    for (const s of [-1, 1]) {
      const arm = new THREE.Mesh(GEO.box, MAT.sofa);
      arm.scale.set(0.24, 0.56, 0.85); arm.position.set(s * 0.85, 0.5, 0);
      arm.castShadow = true; g.add(arm);
    }
    for (const s of [-1, 1]) {
      const cu = new THREE.Mesh(GEO.box, MAT.cushion);
      cu.scale.set(0.7, 0.14, 0.6); cu.position.set(s * 0.42, 0.52, 0.04);
      cu.rotation.y = (R1() - .5) * 0.2; cu.castShadow = true; g.add(cu);
    }
    this.group.add(g);
    this._solid(x, z, 1.0, 0.5, 'furn');
    return g;
  }
  _bed(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const frame = new THREE.Mesh(GEO.box, MAT.trim);
    frame.scale.set(1.5, 0.32, 2.2); frame.position.y = 0.18;
    frame.castShadow = true; g.add(frame);
    const matt = new THREE.Mesh(GEO.box, MAT.sheet);
    matt.scale.set(1.42, 0.2, 2.1); matt.position.y = 0.42;
    matt.castShadow = true; matt.receiveShadow = true; g.add(matt);
    const blk = new THREE.Mesh(GEO.box, MAT.blanket);
    blk.scale.set(1.46, 0.08, 1.3); blk.position.set(0, 0.54, 0.35);
    blk.castShadow = true; g.add(blk);
    for (const s of [-1, 1]) {
      const pil = new THREE.Mesh(GEO.box, MAT.linen);
      pil.scale.set(0.55, 0.12, 0.34); pil.position.set(s * 0.36, 0.58, -0.8);
      pil.rotation.y = (R1() - .5) * 0.3; pil.castShadow = true; g.add(pil);
    }
    const head = new THREE.Mesh(GEO.box, MAT.trim);
    head.scale.set(1.5, 0.9, 0.08); head.position.set(0, 0.65, -1.14);
    head.castShadow = true; g.add(head);
    for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      const post = new THREE.Mesh(GEO.box, MAT.trim);
      post.scale.set(0.09, 1.1, 0.09);
      post.position.set(sx * 0.72, 0.55, sz * 1.08);
      post.castShadow = true; g.add(post);
    }
    this.group.add(g);
    this._solid(x, z, 0.85, 1.2, 'furn');
    return g;
  }
  _wardrobe(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const body = new THREE.Mesh(GEO.box, MAT.trim);
    body.scale.set(1.2, 2.15, 0.6); body.position.y = 1.075;
    body.castShadow = true; body.receiveShadow = true; g.add(body);
    // one door left eternally ajar
    const dg = new THREE.BoxGeometry(0.56, 2.0, 0.04); dg.translate(0.28, 0, 0);
    const dj = new THREE.Group(); dj.position.set(-0.58, 1.07, 0.31); dj.rotation.y = 0.5;
    const dm = new THREE.Mesh(dg, MAT.door); dm.castShadow = true; dj.add(dm);
    const kb = new THREE.Mesh(Door.knobGeo, MAT.brass); kb.position.set(0.52, 0, 0.05); dj.add(kb);
    g.add(dj);
    const d2 = new THREE.Mesh(new THREE.BoxGeometry(0.56, 2.0, 0.04), MAT.door);
    d2.position.set(0.3, 1.07, 0.31); d2.castShadow = true; g.add(d2);
    const kb2 = new THREE.Mesh(Door.knobGeo, MAT.brass); kb2.position.set(x + 0.02, 1.07, z + 0.36); g.add(kb2);
    const voidIn = new THREE.Mesh(GEO.box, MAT.black);
    voidIn.scale.set(0.5, 1.9, 0.02); voidIn.position.set(-0.28, 1.07, 0.28);
    g.add(voidIn);
    this.group.add(g);
    this._solid(x, z, 0.65, 0.4, 'furn');
    return g;
  }
  _dresserWithMirror(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const body = new THREE.Mesh(GEO.box, MAT.trim);
    body.scale.set(1.3, 0.9, 0.5); body.position.y = 0.45;
    body.castShadow = true; g.add(body);
    for (let i = 0; i < 3; i++) {
      const drawer = new THREE.Mesh(GEO.box, MAT.door);
      drawer.scale.set(1.14, 0.2, 0.02); drawer.position.set(0, 0.22 + i * 0.26, 0.26);
      g.add(drawer);
      const pull = new THREE.Mesh(Door.knobGeo, MAT.brass);
      pull.scale.setScalar(0.6); pull.position.set(0, 0.22 + i * 0.26, 0.28);
      g.add(pull);
    }
    const mir = new THREE.Mesh(new THREE.CircleGeometry(0.34, 20), MAT.mirror);
    mir.position.set(0, 1.55, 0.02); g.add(mir);
    const mf = new THREE.Mesh(new THREE.TorusGeometry(0.36, 0.035, 8, 20), MAT.trim);
    mf.position.copy(mir.position); g.add(mf);
    this.group.add(g);
    this._solid(x, z, 0.7, 0.35, 'furn');
    return g;
  }
  _grandfatherClock(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const body = new THREE.Mesh(GEO.box, MAT.trim);
    body.scale.set(0.6, 2.15, 0.36); body.position.y = 1.075;
    body.castShadow = true; body.receiveShadow = true; g.add(body);
    const crest = new THREE.Mesh(GEO.box, MAT.trim);
    crest.scale.set(0.7, 0.16, 0.4); crest.position.y = 2.2; g.add(crest);
    const face = new THREE.Mesh(new THREE.CircleGeometry(0.21, 24), new THREE.MeshStandardMaterial({ map: Tex.clockFace(), roughness: 0.6 }));
    face.position.set(0, 1.78, 0.19); g.add(face);
    const bezel = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.02, 8, 24), MAT.brass);
    bezel.position.copy(face.position); g.add(bezel);
    const win = new THREE.Mesh(GEO.box, MAT.glassNight);
    win.scale.set(0.3, 0.9, 0.02); win.position.set(0, 0.85, 0.185); g.add(win);
    // pendulum
    const pj = new THREE.Group(); pj.position.set(0, 1.28, 0.1);
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.8, 6), MAT.brass);
    rod.position.y = -0.4; pj.add(rod);
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.02, 16), MAT.brass);
    disc.rotation.x = Math.PI / 2; disc.position.y = -0.8; pj.add(disc);
    g.add(pj);
    this.pendulum = pj;
    this.group.add(g);
    this._solid(x, z, 0.36, 0.26, 'furn');
    this.clockPos = new THREE.Vector3(x, 1.2, z);
    return g;
  }
  _fireplace(x, z, ry) {
    const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry;
    const breast = new THREE.Mesh(GEO.box, MAT.mortar);
    breast.scale.set(2.0, WALL_H, 0.6); breast.position.y = WALL_H / 2;
    breast.castShadow = true; breast.receiveShadow = true; g.add(breast);
    const hole = new THREE.Mesh(GEO.box, MAT.black);
    hole.scale.set(1.2, 1.0, 0.1); hole.position.set(0, 0.62, 0.28); g.add(hole);
    const mantel = new THREE.Mesh(GEO.box, MAT.trim);
    mantel.scale.set(2.2, 0.1, 0.75); mantel.position.y = 1.35; mantel.castShadow = true; g.add(mantel);
    const hearth = new THREE.Mesh(GEO.box, MAT.mortar);
    hearth.scale.set(2.0, 0.05, 0.9); hearth.position.set(0, 0.025, 0.35); g.add(hearth);
    for (let i = 0; i < 2; i++) {
      const log = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.7, 8), MAT.trim);
      log.rotation.z = Math.PI / 2; log.rotation.y = i * 0.5;
      log.position.set(0, 0.12 + i * 0.13, 0.3); log.castShadow = true; g.add(log);
    }
    const ash = new THREE.Mesh(GEO.sph, new THREE.MeshStandardMaterial({ color: 0x4a4642, roughness: 1 }));
    ash.scale.set(0.5, 0.06, 0.3); ash.position.set(0, 0.05, 0.32); g.add(ash);
    this.group.add(g);
    this._solid(x, z, 1.05, 0.42, 'furn');
  }
  _portrait(x, y, z, ry, seed, scratched = false, w = 0.62, h = 0.78) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry;
    const pic = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshStandardMaterial({ map: Tex.portrait(seed, scratched), roughness: 0.85 }));
    g.add(pic);
    const fr = new THREE.Mesh(new THREE.BoxGeometry(w + 0.09, h + 0.09, 0.05), MAT.trim);
    fr.position.z = -0.026; g.add(fr);
    this.group.add(g);
    return g;
  }
  _window(x, y, z, ry, w = 1.1, h = 1.5) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry;
    const fr = new THREE.Mesh(GEO.box, MAT.trim);
    fr.scale.set(w + 0.2, h + 0.2, 0.08); g.add(fr);
    const glass = new THREE.Mesh(GEO.box, MAT.glassNight);
    glass.scale.set(w, h, 0.03); glass.position.z = 0.03; g.add(glass);
    for (const s of [-1, 1]) {
      const mu = new THREE.Mesh(GEO.box, MAT.trim);
      mu.scale.set(0.05, h, 0.02); mu.position.set(s * w / 4, 0, 0.05); g.add(mu);
      const mv = new THREE.Mesh(GEO.box, MAT.trim);
      mv.scale.set(w, 0.05, 0.02); mv.position.set(0, s * h / 4, 0.05); g.add(mv);
    }
    const sill = new THREE.Mesh(GEO.box, MAT.trim);
    sill.scale.set(w + 0.3, 0.06, 0.18); sill.position.set(0, -h / 2 - 0.05, 0.08); g.add(sill);
    for (const s of [-1, 1]) { // curtained
      const cur = new THREE.Mesh(new THREE.PlaneGeometry(0.4, h + 0.35), MAT.curtain);
      cur.position.set(s * (w / 2 + 0.16), 0.05, 0.1);
      cur.rotation.y = s * 0.25; g.add(cur);
    }
    this.group.add(g);
    // inward normal for the moonlight
    const n = new THREE.Vector3(0, 0, 1).applyAxisAngle(new THREE.Vector3(0, 1, 0), ry);
    return { lightPos: new THREE.Vector3(x, y, z).addScaledVector(n, 0.5) };
  }
  _candlestick(x, y, z, withCluster, clusterId) {
    const g = new THREE.Group(); g.position.set(x, y, z);
    const stick = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.045, 0.22, 8), MAT.brass);
    stick.position.y = 0.11; stick.castShadow = true; g.add(stick);
    const wax = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.02, 0.09, 8), MAT.porcelain);
    wax.position.y = 0.26; g.add(wax);
    const fl = new THREE.Sprite(MAT.flame);
    fl.scale.set(0.09, 0.16, 1); fl.position.y = 0.37;
    g.add(fl);
    this.flames.push(fl);
    this.group.add(g);
    if (withCluster) {
      const li = new THREE.PointLight(0xff9a3c, 2.2, 4.2, 2);
      li.position.set(x, y + 0.5, z);
      this.group.add(li);
      this.flickerLights.push({ light: li, base: 2.2, seed: clusterId * 31.7, kind: 'candle' });
    }
  }
  _coatStand(x, z) {
    const g = new THREE.Group(); g.position.set(x, 0, z);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.05, 1.8, 8), MAT.trim);
    pole.position.y = 0.9; pole.castShadow = true; g.add(pole);
    for (let i = 0; i < 3; i++) {
      const hk = new THREE.Mesh(GEO.box, MAT.trim);
      hk.scale.set(0.05, 0.05, 0.22);
      hk.position.y = 1.68; hk.rotation.y = i * 2.1;
      hk.translateZ(0.1); g.add(hk);
    }
    // a draped coat — a person-shaped absence
    const coat = new THREE.Mesh(new THREE.ConeGeometry(0.3, 1.15, 8, 1, true),
      new THREE.MeshStandardMaterial({ map: Tex.curtain(), roughness: 1, side: THREE.DoubleSide }));
    coat.position.set(0.12, 1.05, 0.05); coat.castShadow = true; g.add(coat);
    this.group.add(g);
    this._solid(x, z, 0.2, 0.2, 'furn');
  }
  _doll(x, y, z, ry) {
    const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry;
    const head = new THREE.Mesh(GEO.sph, MAT.porcelain);
    head.scale.setScalar(0.07); head.position.y = 0.16; g.add(head);
    const dress = new THREE.Mesh(new THREE.ConeGeometry(0.075, 0.16, 8), MAT.blanket);
    dress.position.y = 0.06; g.add(dress);
    // hollow stare: two drilled pupils
    for (const s of [-1, 1]) {
      const eye = new THREE.Mesh(GEO.sph, MAT.black);
      eye.scale.setScalar(0.014); eye.position.set(s * 0.025, 0.17, 0.06); g.add(eye);
    }
    this.group.add(g);
  }

  _furnishings() {
    /* ================= LIVING ROOM (west-south) ======================== */
    this._fireplace(-9.55, 5, Math.PI / 2);
    this._sofa(-6.6, 5.4, Math.PI / 2);
    this._chair(-6.8, 3.2, 2.4);
    this._tableRect(-7.6, 4.4, 0.9, 0.6, 0.5, 0.3);
    this._bookcase(-9.6, 2.9, Math.PI / 2, 1.7);
    this.sideTableLiv = this._tableRect(-8.9, 6.6, 0.6, 0.6, 0.52);
    this.portraitAskew = this._portrait(-6.9, 1.9, 2.14, 0, 101);
    this._portrait(-9.86, 1.9, 3.6, Math.PI / 2, 102);

    /* ================= FOYER =========================================== */
    this.consoleTbl = this._tableRect(0.9, 6.9, 1.3, 0.42, 0.82, 0);
    this._candlestick(0.55, 0.85, 6.9, true, 1);
    this._candlestick(1.25, 0.85, 6.9, false);
    this._coatStand(-3.4, 6.9);
    this._portrait(0, 2.0, 2.14, 0, 103, true); // the scratched-out face
    for (const s of [-1, 1]) {
      const mir = new THREE.Mesh(new THREE.CircleGeometry(0.26, 18), MAT.mirror);
      mir.position.set(s * 1.7, 1.8, 7.86); this._static(mir, {});
    }

    /* ================= DINING ROOM (east-south) ======================== */
    this._tableRect(7, 5, 2.6, 1.1, 0.78);
    for (const [cx, cz, ry] of [[6.2, 4.1, 0], [7.8, 4.1, 0], [6.2, 5.9, Math.PI], [7.8, 5.9, Math.PI]])
      this._chair(cx, cz, ry);
    this._candlestick(6.7, 0.81, 5, true, 2);
    this._candlestick(7.3, 0.81, 5, false);
    const vase = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 0.24, 10), MAT.porcelain);
    vase.position.set(7, 0.93, 5); vase.castShadow = true; this._static(vase, { cast: true });
    this._bookcase(9.6, 3.2, -Math.PI / 2, 1.5);
    this.buffet = this._tableRect(9.4, 5.2, 0.6, 1.6, 0.98, Math.PI / 2);
    // dead chandelier silhouette
    const ch = new THREE.Group(); ch.position.set(7, 2.45, 5);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.03, 8, 20), MAT.iron);
    ring.rotation.x = Math.PI / 2; ch.add(ring);
    const chain = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.55, 6), MAT.iron);
    chain.position.y = 0.28; ch.add(chain);
    for (let i = 0; i < 5; i++) {
      const a = i / 5 * Math.PI * 2;
      const cst = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.02, 0.14, 6), MAT.porcelain);
      cst.position.set(Math.cos(a) * 0.4, 0.08, Math.sin(a) * 0.4); ch.add(cst);
    }
    this._static(ch, {});

    /* ================= KITCHEN (east-north) ============================= */
    // counter run along the north wall
    this._box(4.6, 0.9, 0.62, MAT.trim, 7.2, 0.45, -7.65);
    this._box(4.7, 0.05, 0.66, MAT.mortar, 7.2, 0.925, -7.65);
    for (let i = 0; i < 4; i++) {
      const cdr = new THREE.Mesh(GEO.box, MAT.door);
      cdr.scale.set(1.0, 0.7, 0.02); cdr.position.set(5.4 + i * 1.2, 0.42, -7.33);
      this._static(cdr, { cast: true });
      const kp = new THREE.Mesh(Door.knobGeo, MAT.brass);
      kp.scale.setScalar(0.55); kp.position.set(5.4 + i * 1.2 + 0.4, 0.42, -7.31);
      this._static(kp, {});
    }
    this._solid(7.2, -7.65, 2.35, 0.36, 'furn');
    // sink + tap
    const sink = new THREE.Mesh(GEO.box, MAT.black);
    sink.scale.set(0.6, 0.06, 0.44); sink.position.set(6.4, 0.93, -7.6);
    this._static(sink, {});
    const tap = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.3, 8), MAT.iron);
    tap.position.set(6.4, 1.1, -7.8); this._static(tap, { cast: true });
    // stove
    this._box(0.75, 0.95, 0.65, MAT.iron, 9.5, 0.475, -7.6);
    for (const [bx, bz] of [[-0.18, -0.14], [0.18, -0.14], [-0.18, 0.14], [0.18, 0.14]]) {
      const bur = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.015, 12), MAT.black);
      bur.position.set(9.5 + bx, 0.96, -7.6 + bz); this._static(bur, {});
    }
    this._solid(9.5, -7.6, 0.42, 0.36, 'furn');
    // fridge
    this._box(0.8, 1.9, 0.7, new THREE.MeshStandardMaterial({ map: (() => { const t = Tex.plaster(); return t; })(), color: 0x6a6e72, metalness: 0.6, roughness: 0.4 }), 4.6, 0.95, -7.55);
    this._solid(4.6, -7.55, 0.45, 0.4, 'furn');
    // overhead cupboards
    this._box(3.4, 0.7, 0.4, MAT.trim, 7.6, 1.85, -7.75);
    // kitchen table + the chair that will move itself
    this._tableRect(5.6, -4.6, 1.5, 0.9, 0.8, 0.2);
    this.slidingChair = this._chair(5.2, -3.9, 2.8);
    this._chair(6.1, -5.3, 0.4);
    this._chair(4.9, -5.2, 1.4);
    // hanging pans that sway
    this.pans = [];
    const rail = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.6, 6), MAT.iron);
    rail.rotation.z = Math.PI / 2; rail.position.set(7.4, 2.1, -6.6);
    this._static(rail, {});
    for (const px of [6.9, 7.4, 7.9]) {
      const pg = new THREE.Group(); pg.position.set(px, 2.08, -6.6);
      const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.09, 0.14, 10), MAT.iron);
      pot.position.y = -0.24; pot.castShadow = true; pg.add(pot);
      this.group.add(pg);
      this.pans.push({ g: pg, phase: Math.random() * 6, amp: 0 });
    }

    /* ================= STUDY (west-north) =============================== */
    this.desk = this._tableRect(-8.6, -7.2, 1.7, 0.8, 0.78, 0);
    const drwr = new THREE.Mesh(GEO.box, MAT.door);
    drwr.scale.set(1.5, 0.5, 0.04); drwr.position.set(-8.6, 0.35, -6.82);
    this._static(drwr, { cast: true });
    this._chair(-8.6, -6.4, Math.PI);
    this._bookcase(-9.6, -4.0, Math.PI / 2, 1.7);
    this._bookcase(-5.6, -7.6, 0, 1.4);
    const glob = new THREE.Mesh(GEO.sph, new THREE.MeshStandardMaterial({ color: 0x3d4a3a, roughness: 0.7 }));
    glob.scale.setScalar(0.16); glob.position.set(-9.5, 1.0, -7.4);
    this._static(glob, { cast: true });
    this.studyChair = this._chair(-5.2, -6.4, 2.2);
    this._portrait(-4.14, 1.9, -5, -Math.PI / 2, 104);

    /* ================= BEDROOM (centre-north) =========================== */
    this._bed(-2.4, -5.6, Math.PI / 2);
    this.nightstand = this._tableRect(-2.9, -6.9, 0.55, 0.55, 0.58);
    this._candlestick(-2.9, 0.61, -6.9, true, 3);
    this._wardrobe(3.2, -7.4, 0);
    this.dresser = this._dresserWithMirror(3.4, -4.6, -Math.PI / 2);
    this._doll(3.35, 0.94, -4.3, -2.4); // slumped, staring at the wall
    const wk = this._window(-1.4, 1.62, -7.86, 0, 1.0, 1.3);
    this.bedWindowLight = wk.lightPos;

    /* ================= HALLWAY ========================================== */
    this._grandfatherClock(-9.3, 0, Math.PI / 2);
    this.bench = this._tableRect(-3.0, 1.55, 1.3, 0.45, 0.48, Math.PI);
    this._coatStand(9.2, 1.55);
    this._portrait(-2.9, 1.85, -2.14, 0, 105, false, 0.5, 0.64);
    this._portrait(3.4, 1.85, 2.14, Math.PI, 106, false, 0.5, 0.64);
    this._portrait(-9.86, 1.85, -1.2, Math.PI / 2, 107, false, 0.5, 0.64);
  }

  /* --------------------------------------------------------------- lights */
  _lights() {
    // foyer pendant
    const pg = new THREE.Group(); pg.position.set(0, 2.62, 5);
    const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.38, 6), MAT.iron);
    cord.position.y = 0.19; pg.add(cord);
    const shade = new THREE.Mesh(new THREE.ConeGeometry(0.24, 0.2, 12, 1, true),
      new THREE.MeshStandardMaterial({ color: 0x35302a, roughness: 0.6, side: THREE.DoubleSide }));
    shade.position.y = -0.06; pg.add(shade);
    const bulb = new THREE.Mesh(GEO.sph, new THREE.MeshStandardMaterial({ color: 0xffd9a0, emissive: 0xffc684, emissiveIntensity: 1.6 }));
    bulb.scale.setScalar(0.045); bulb.position.y = -0.12; pg.add(bulb);
    this.group.add(pg);
    const pl = new THREE.PointLight(0xffc78e, 11, 9, 2);
    pl.position.set(0, 2.45, 5);
    this.group.add(pl);
    this.flickerLights.push({ light: pl, base: 11, seed: 5.1, kind: 'bulb', bulbMesh: bulb });
    this.foyerBulb = { light: pl, bulb };

    // hallway sconce (dies permanently after scare #2)
    const sg = new THREE.Group(); sg.position.set(3.2, 2.25, -1.82);
    const brk = new THREE.Mesh(GEO.box, MAT.iron);
    brk.scale.set(0.06, 0.2, 0.14); sg.add(brk);
    const sbulb = new THREE.Mesh(GEO.sph, new THREE.MeshStandardMaterial({ color: 0xffd9a0, emissive: 0xffb97a, emissiveIntensity: 1.4 }));
    sbulb.scale.setScalar(0.04); sbulb.position.y = -0.12; sg.add(sbulb);
    this.group.add(sg);
    const sl = new THREE.PointLight(0xffb97a, 8, 7, 2);
    sl.position.set(3.2, 2.1, -1.5);
    this.group.add(sl);
    this.sconce = { light: sl, bulb: sbulb, alive: true };
    this.flickerLights.push({ light: sl, base: 8, seed: 17.3, kind: 'bulbFaulty', bulbMesh: sbulb });

    // moonlight through windows
    this.moonLights = [];
    const addMoon = (pos, inten = 5.5) => {
      const ml = new THREE.PointLight(0x91a7cf, inten, 9, 2);
      ml.position.copy(pos);
      this.group.add(ml);
      this.moonLights.push({ light: ml, base: inten });
    };
    const w1 = this._window(-9.86, 1.7, 5, Math.PI / 2); addMoon(w1.lightPos);
    const w2 = this._window(9.86, 1.7, 5, -Math.PI / 2); addMoon(w2.lightPos);
    addMoon(this.bedWindowLight ?? new THREE.Vector3(-1.4, 1.7, -7.4));
    const w4 = this._window(7, 1.7, -7.86, 0, 0.9, 1.2); addMoon(w4.lightPos, 4);
  }

  /* ----------------------------------------------------------------- items */
  _makeProxy(x, y, z, owner) {
    const p = new THREE.Mesh(GEO.box, MAT.black);
    p.scale.setScalar(0.34); p.position.set(x, y, z);
    p.visible = false;
    p.userData = { owner };
    this.group.add(p);
    this.pickTargets.push(p);
    return p;
  }

  _items() {
    this.keyMeshes = [];
    this.batteryMeshes = [];
    this.noteMeshes = [];

    // ----- keys: shuffled pick, one per room -----
    const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
    this.keyDefs = [
      { room: 'kitchen', ...pick(KEY_SPOTS.kitchen) },
      { room: 'study', ...pick(KEY_SPOTS.study) },
      { room: 'bedroom', ...pick(KEY_SPOTS.bedroom) }
    ];
    const keyGeoBits = () => {
      const g = new THREE.Group();
      const bow = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.014, 8, 16), MAT.brass);
      g.add(bow);
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.14, 6), MAT.brass);
      shaft.rotation.z = Math.PI / 2; shaft.position.x = 0.1; g.add(shaft);
      for (const [tx, th] of [[0.15, 0.035], [0.11, 0.028]]) {
        const tooth = new THREE.Mesh(GEO.box, MAT.brass);
        tooth.scale.set(0.014, th, 0.014); tooth.position.set(tx, -(th / 2 + 0.01), 0);
        g.add(tooth);
      }
      return g;
    };
    this.keyDefs.forEach((def, i) => {
      const km = keyGeoBits();
      km.position.set(...def.pos);
      km.rotation.z = 0.5; km.rotation.y = Math.random() * 6;
      km.traverse(o => { o.castShadow = true; });
      // faint self-glint so the eye can catch it in the dark
      km.traverse(o => { if (o.isMesh) { o.material = MAT.brass.clone(); o.material.emissive = new THREE.Color(0x6b4a12); o.material.emissiveIntensity = 0.5; } });
      this.group.add(km);
      this.keyMeshes.push(km);
      def.mesh = km;
      def.proxy = this._makeProxy(...def.pos, { type: 'key', def });
      def.collected = false;
    });

    // ----- batteries -----
    BATTERY_SPOTS.forEach((bp, i) => {
      const bm = new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.032, 0.11, 12), MAT.iron);
      bm.position.set(...bp.pos); bm.rotation.z = Math.PI / 2;
      const tip = new THREE.Mesh(GEO.sph, MAT.brass);
      tip.scale.setScalar(0.02); tip.position.x = 0.06; bm.add(tip);
      const led = new THREE.Mesh(GEO.sph, new THREE.MeshStandardMaterial({ color: 0x143a2a, emissive: 0x2affa0, emissiveIntensity: 0.9 }));
      led.scale.setScalar(0.012); led.position.x = -0.058; bm.add(led);
      this.group.add(bm);
      this.batteryMeshes.push(bm);
      bp.mesh = bm; bp.led = led; bp.taken = false;
      bp.proxy = this._makeProxy(...bp.pos, { type: 'battery', def: bp });
    });

    // ----- notes -----
    NOTE_DEFS.forEach((nd) => {
      const nm = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.3), MAT.paper);
      nm.position.set(...nd.pos);
      nm.rotation.x = -Math.PI / 2; nm.rotation.z = nd.rotY;
      nm.position.y += 0.005;
      this.group.add(nm);
      this.noteMeshes.push(nm);
      nd.mesh = nm;
      nd.proxy = this._makeProxy(nd.pos[0], nd.pos[1] + 0.05, nd.pos[2], { type: 'note', def: nd });
    });
  }

  /* -------------------------------------------------------------- cobwebs */
  _cobwebs() {
    const wt = Tex.web();
    const wm = new THREE.MeshBasicMaterial({ map: wt, transparent: true, opacity: 0.55, depthWrite: false, side: THREE.DoubleSide });
    const spots = [
      [-9.85, 2.7, -7.85, 0], [9.85, 2.7, -7.85, Math.PI], [-9.85, 2.7, 7.85, Math.PI / 2],
      [9.85, 2.7, 7.85, -Math.PI / 2], [-4.1, 2.7, -2.1, Math.PI / 4], [4.1, 2.7, 2.1, Math.PI + Math.PI / 4],
      [-9.85, 2.7, 1.85, Math.PI / 2], [9.85, 2.7, -1.85, -Math.PI / 2]
    ];
    for (const [wx, wy, wz, ry] of spots) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), wm);
      w.position.set(wx, wy, wz); w.rotation.y = ry;
      w.rotation.z = ry + Math.PI / 4;
      this._static(w, { cast: false, recv: false });
    }
  }

  /* ------------------------------------------------------------------ dust */
  _dust() {
    const N = 240;
    const pos = new Float32Array(N * 3);
    const vel = [];
    for (let i = 0; i < N; i++) {
      pos[i * 3] = -10 + Math.random() * 20;
      pos[i * 3 + 1] = 0.2 + Math.random() * 2.6;
      pos[i * 3 + 2] = -8 + Math.random() * 16;
      vel.push([(Math.random() - .5) * 0.05, -0.01 - Math.random() * 0.02, (Math.random() - .5) * 0.05]);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pm = new THREE.PointsMaterial({
      map: Tex.dust(), size: 0.035, transparent: true, opacity: 0.5,
      blending: THREE.AdditiveBlending, depthWrite: false, color: 0xd8d2c0
    });
    this.dust = new THREE.Points(g, pm);
    this.dust.frustumCulled = false;
    this.group.add(this.dust);
    this.dustVel = vel;
  }

  /* ============================================================== runtime */
  update(dt, t, playerPos) {
    this.time = t;
    for (const dn of ['study', 'bedroom', 'front']) this.doors[dn]?.update(dt, this.audioHook);

    // flickering lights
    for (const f of this.flickerLights) {
      if (f.dead) continue;
      let m = 0.78 + 0.22 * Math.sin(t * (f.kind === 'candle' ? 11 : 3.3) + f.seed) * Math.sin(t * 7.7 + f.seed * 2);
      if (f.kind !== 'candle' && Math.random() < 0.006) f.dropT = 0.08 + Math.random() * 0.1;
      if (f.dropT > 0) { f.dropT -= dt; m *= 0.12; }
      f.light.intensity = f.boost ? f.base * (1 + f.boost) * m : f.base * m;
      if (f.bulbMesh) f.bulbMesh.material.emissiveIntensity = 1.6 * m;
    }
    // candle flames flutter
    for (const fl of this.flames) {
      const s = 0.8 + Math.random() * 0.35;
      fl.scale.set(0.09 * s, 0.16 * (0.85 + Math.random() * 0.3), 1);
    }
    // pendulum + tick
    if (this.pendulum) {
      this.pendulum.rotation.z = Math.sin(t * Math.PI) * 0.28;
      const whole = Math.floor(t);
      if (whole !== this.lastTickWhole && playerPos) {
        this.lastTickWhole = whole;
        const d = playerPos.distanceTo(this.clockPos);
        this.onTick?.(Math.max(0, 1 - d / 14));
      }
    }
    // swaying pans
    for (const p of this.pans) {
      p.amp += (p.impulse ? 1 : 0) * dt * 4; p.impulse = false;
      p.amp = Math.max(0, p.amp - dt * 0.35);
      p.phase += dt * 3.1;
      p.g.rotation.x = Math.sin(p.phase) * (0.02 + p.amp * 0.3);
    }
    // dust drift
    const dp = this.dust.geometry.attributes.position;
    for (let i = 0; i < this.dustVel.length; i++) {
      let x = dp.getX(i) + this.dustVel[i][0] * dt;
      let y = dp.getY(i) + this.dustVel[i][1] * dt;
      let z = dp.getZ(i) + this.dustVel[i][2] * dt;
      if (y < 0.1) y = 2.8;
      if (x < -10) x = 10; if (x > 10) x = -10;
      if (z < -8) z = 8; if (z > 8) z = -8;
      dp.setXYZ(i, x, y, z);
    }
    dp.needsUpdate = true;
    // key glimmer pulse
    for (const kd of this.keyDefs) {
      if (kd.collected) continue;
      kd.mesh.traverse(o => { if (o.isMesh) o.material.emissiveIntensity = 0.4 + 0.5 * (0.5 + 0.5 * Math.sin(t * 2.4 + kd.pos[0])); });
    }
    // battery LEDs blink
    for (const bp of BATTERY_SPOTS) {
      if (bp.taken) continue;
      bp.led.material.emissiveIntensity = (Math.sin(t * 3 + bp.pos[0]) > 0.6) ? 1.2 : 0.15;
    }
  }

  killSconce() {
    if (!this.sconce.alive) return;
    this.sconce.alive = false;
    const f = this.flickerLights.find(f => f.kind === 'bulbFaulty');
    f.dead = true;
    this.sconce.light.intensity = 0;
    this.sconce.bulb.material.emissiveIntensity = 0;
  }
  setBlackout(on) {
    for (const m of this.moonLights) m.light.intensity = on ? 0 : m.base;
    for (const f of this.flickerLights) {
      if (f.kind === 'candle') f.light.intensity = on ? 0 : f.base;
      else if (!f.dead) f.light.intensity = on ? 0 : f.base;
    }
    this.blackout = on;
  }
  boostMoons(v) { for (const m of this.moonLights) m.boost = v; }

  snapshotProps() {
    this._snap = {
      chair: this.slidingChair.position.clone(),
      portrait: this.portraitAskew.rotation.z
    };
  }
  restoreProps() {
    if (!this._snap) return;
    this.slidingChair.position.copy(this._snap.chair);
    this.portraitAskew.rotation.z = this._snap.portrait;
    if (this.sconce.alive === false) { /* stays dead per run-reset below */ }
  }
}
function R1() { return Math.random(); }
```

**src/player/Player.js**

```js
// First-person rig: pointer-lock look, WASD + sprint, swept-circle collision,
// head bob, footsteps, and the flashlight — the game's one shadow-casting
// light, with aim lag, sway and a projector cookie.
import * as THREE from 'three';
import { Tex } from '../world/Textures.js';

const EYE = 1.62;
const RAD = 0.34;
const WALK = 2.2, SPRINT = 3.55;

export class Player {
  constructor(camera, scene) {
    this.camera = camera;
    this.root = new THREE.Object3D();         // yaw + position
    this.pitchObj = new THREE.Object3D();     // pitch
    this.pitchObj.position.y = EYE;
    this.root.add(this.pitchObj);
    this.pitchObj.add(camera);
    scene.add(this.root);

    this.yaw = 0; this.pitch = 0;
    this.vel = new THREE.Vector3();
    this.input = { f: 0, b: 0, l: 0, r: 0, sprint: false };
    this.enabled = true;

    this.bobPhase = 0; this.bobPrevUp = true;
    this.onStep = null;
    this.trauma = 0;

    // -------- flashlight --------
    this.torch = { on: true, battery: 100, warned20: false, dead: false };
    this.spot = new THREE.SpotLight(0xfff2dc, 150, 27, 0.46, 0.6, 1.8);
    this.spot.map = Tex.cookie();
    this.spot.castShadow = true;
    this.spot.shadow.mapSize.set(1024, 1024);
    this.spot.shadow.bias = -0.0006;
    this.spot.shadow.normalBias = 0.03;
    this.spot.shadow.camera.near = 0.2;
    this.spot.shadow.camera.far = 27;
    this.spotTarget = new THREE.Object3D();
    scene.add(this.spot, this.spotTarget);
    this.spot.target = this.spotTarget;

    this.smoothFwd = new THREE.Vector3(0, 0, -1);
    this.swayT = 0;
    this._tmp = new THREE.Vector3();
    this._q = new THREE.Quaternion();
    this.forcedDim = 0; // used by the blackout beat
  }

  onMouse(dx, dy) {
    if (!this.enabled) return;
    this.yaw -= dx * 0.0021;
    this.pitch -= dy * 0.0021;
    this.pitch = Math.max(-1.52, Math.min(1.52, this.pitch));
  }

  addTrauma(a) { this.trauma = Math.min(1, this.trauma + a); }

  eyePos(out = new THREE.Vector3()) {
    this.camera.getWorldPosition(out);
    return out;
  }
  lookDir(out = new THREE.Vector3()) {
    this.camera.getWorldDirection(out);
    return out;
  }

  toggleTorch(audio) {
    if (this.torch.battery <= 0) { audio?.switchDead(); return; }
    this.torch.on = !this.torch.on;
    audio?.switchClick();
  }

  addCharge(v) {
    this.torch.battery = Math.min(100, this.torch.battery + v);
    if (this.torch.battery > 0) this.torch.dead = false;
  }

  /** Is the beam meaningfully pointed at this world point right now? */
  beamOn(point) {
    if (!this.torch.on || this.torch.battery <= 0 || this.forcedDim > 0.5) return false;
    const ep = this.eyePos(this._tmp);
    const to = point.clone().sub(ep);
    const d = to.length();
    if (d > 10.5) return false;
    to.normalize();
    return to.dot(this.smoothFwd) > 0.972;
  }

  reset(px, pz, yaw) {
    this.root.position.set(px, 0, pz);
    this.yaw = yaw; this.pitch = 0;
    this.vel.set(0, 0, 0);
    this.torch.on = true; this.torch.battery = 100;
    this.torch.warned20 = false; this.torch.dead = false;
    this.trauma = 0; this.forcedDim = 0;
    this.smoothFwd.set(0, 0, -1);
  }

  update(dt, solids, audio) {
    /* ------ movement ------ */
    let ix = this.input.r - this.input.l;
    let iz = this.input.b - this.input.f;
    const mag = Math.hypot(ix, iz);
    if (mag > 1) { ix /= mag; iz /= mag; }
    const spd = (this.input.sprint ? SPRINT : WALK) * (this.enabled ? 1 : 0);
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    const wx = (ix * cos - iz * sin) * spd;
    const wz = (ix * -sin - iz * cos) * spd;
    const k = 1 - Math.exp(-10 * dt);
    this.vel.x += (wx - this.vel.x) * k;
    this.vel.z += (wz - this.vel.z) * k;

    let nx = this.root.position.x + this.vel.x * dt;
    let nz = this.root.position.z + this.vel.z * dt;
    for (let pass = 0; pass < 2; pass++) {
      for (const s of solids) {
        if (s.active === false) continue;
        const cx = Math.max(s.x0, Math.min(nx, s.x1));
        const cz = Math.max(s.z0, Math.min(nz, s.z1));
        let dx = nx - cx, dz = nz - cz;
        const d2 = dx * dx + dz * dz;
        if (d2 < RAD * RAD) {
          if (d2 < 1e-9) {
            const l = nx - s.x0, r = s.x1 - nx, tt = nz - s.z0, bb = s.z1 - nz;
            const mn = Math.min(l, r, tt, bb);
            if (mn === l) nx = s.x0 - RAD; else if (mn === r) nx = s.x1 + RAD;
            else if (mn === tt) nz = s.z0 - RAD; else nz = s.z1 + RAD;
          } else {
            const dd = Math.sqrt(d2);
            nx = cx + dx / dd * RAD; nz = cz + dz / dd * RAD;
          }
        }
      }
    }
    nx = Math.max(-9.6, Math.min(9.6, nx));
    nz = Math.max(-7.6, Math.min(7.6, nz));
    this.root.position.x = nx; this.root.position.z = nz;

    const speed2 = Math.hypot(this.vel.x, this.vel.z);
    const sprinting = this.input.sprint && speed2 > WALK * 1.05 && this.enabled;

    /* ------ head bob + footsteps ------ */
    const mn = Math.min(1, speed2 / WALK);
    this.bobPhase += speed2 * 4.4 * dt;
    const bobY = Math.sin(this.bobPhase * 2) * 0.034 * mn;
    const bobRoll = Math.cos(this.bobPhase) * 0.008 * mn;
    const crest = Math.sin(this.bobPhase * 2);
    if (this.bobPrevUp && crest < -0.86 && this.onStep) this.onStep(sprinting);
    this.bobPrevUp = crest < -0.86;

    /* ------ camera orientation + shake ------ */
    this.trauma = Math.max(0, this.trauma - 1.7 * dt);
    const sh = this.trauma * this.trauma;
    const ts = this.swayT = performance.now() / 1000;
    const shx = (Math.sin(ts * 57.3) * 0.6 + Math.sin(ts * 31.7) * 0.4) * 0.05 * sh;
    const shy = (Math.sin(ts * 47.9) * 0.6 + Math.sin(ts * 23.3) * 0.4) * 0.05 * sh;

    this.root.rotation.y = this.yaw;
    this.pitchObj.rotation.x = this.pitch;
    this.camera.rotation.z = bobRoll + shy * 0.4;
    this.camera.position.y = bobY;
    this.camera.rotation.x = shx * 0.5;

    /* ------ flashlight follow with lag + sway ------ */
    const desired = this.lookDir(this._tmp);
    this.smoothFwd.lerp(desired, 1 - Math.exp(-8.5 * dt)).normalize();
    const swayAmp = 0.010 + mn * 0.012;
    const swY = (Math.sin(ts * 1.3) * 0.5 + Math.sin(ts * 2.71 + 1) * 0.3 + Math.sin(ts * 4.3) * 0.2) * swayAmp;
    const swP = (Math.sin(ts * 1.7 + 2) * 0.5 + Math.sin(ts * 3.3) * 0.3) * swayAmp;
    const dir = this.smoothFwd.clone()
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), swY);
    const right = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0)).normalize();
    dir.applyAxisAngle(right, swP).normalize();

    const ep = this.eyePos();
    this.spot.position.copy(ep).addScaledVector(right, 0.16).add(new THREE.Vector3(0, -0.18, 0));
    this.spotTarget.position.copy(ep).addScaledVector(dir, 8);

    /* ------ battery ------ */
    const burning = this.externalBurnDrain ? 1 : 0;
    if (this.torch.on && this.torch.battery > 0) {
      this.torch.battery = Math.max(0, this.torch.battery - dt * (0.30 + burning * 1.0));
      if (this.torch.battery <= 0) { this.torch.dead = true; this.torch.on = false; audio?.torchDie(); }
      else if (this.torch.battery < 20 && !this.torch.warned20) { this.torch.warned20 = true; audio?.torchWeak(); }
      if (this.torch.battery > 25) this.torch.warned20 = false;
    }
    let inten = 1;
    if (!this.torch.on || this.torch.battery <= 0) inten = 0;
    else {
      if (this.torch.battery < 20 && Math.random() < 0.09) inten = 0.25;
      inten *= 0.96 + Math.random() * 0.07;
    }
    if (this.forcedDim > 0) { this.forcedDim = Math.max(0, this.forcedDim - dt); inten *= 0.03; }
    this.spot.intensity = 150 * inten;
    this.spot.castShadow = inten > 0.1;

    return { sprinting, speed: speed2 };
  }
}
```

**src/systems/AudioEngine.js**

```js
// Fully synthesized soundscape: rain bed, drones, thunder, footsteps, doors,
// stingers, whispers, heartbeat, the entity's breath, and the chase ostinato.
// Nothing loaded; everything grown from oscillators and shaped noise.
export class AudioEngine {
  constructor() { this.ok = false; }

  init() {
    if (this.ok) return;
    const C = this.C = new (window.AudioContext || window.webkitAudioContext)();
    this.master = C.createGain(); this.master.gain.value = 0.9;
    this.comp = C.createDynamicsCompressor();
    this.comp.threshold.value = -14; this.comp.ratio.value = 8; this.comp.attack.value = 0.004;
    this.master.connect(this.comp).connect(C.destination);

    // convolution reverb from a synthetic IR
    this.rev = C.createConvolver();
    this.rev.buffer = this._makeIR(2.1, 2.4);
    this.revGain = C.createGain(); this.revGain.gain.value = 0.9;
    this.rev.connect(this.revGain).connect(this.master);

    this.noise = this._makeNoise(2, false);
    this.brown = this._makeNoise(3, true);

    this._startBeds();
    this.ok = true;
  }
  resume() { this.C?.resume(); }

  _makeNoise(sec, brown) {
    const C = this.C, n = C.sampleRate * sec;
    const buf = C.createBuffer(1, n, C.sampleRate);
    const d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < n; i++) {
      const w = Math.random() * 2 - 1;
      if (brown) { last = (last + 0.02 * w) / 1.02; d[i] = last * 3.5; }
      else d[i] = w;
    }
    return buf;
  }
  _makeIR(sec, decay) {
    const C = this.C, n = C.sampleRate * sec;
    const buf = C.createBuffer(2, n, C.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let lp = 0;
      for (let i = 0; i < n; i++) {
        const t = i / n;
        let s = (Math.random() * 2 - 1) * Math.pow(1 - t, decay);
        // early reflections
        if (i < C.sampleRate * 0.06 && Math.random() < 0.02) s *= 4;
        lp += (s - lp) * (0.25 + t * 0.5); // progressive HF damping
        d[i] = lp;
      }
    }
    return buf;
  }
  _noiseSrc(buf) { const s = this.C.createBufferSource(); s.buffer = buf || this.noise; s.loop = true; return s; }
  _env(g, t0, a, peak, d, sus = 0, rel = 0) {
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.linearRampToValueAtTime(peak, t0 + a);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0001, sus), t0 + a + d);
    if (rel) g.gain.exponentialRampToValueAtTime(0.0001, t0 + a + d + rel);
  }
  _route(node, dry = 1, wet = 0) {
    const gd = this.C.createGain(); gd.gain.value = dry;
    node.connect(gd).connect(this.master);
    if (wet > 0) {
      const gw = this.C.createGain(); gw.gain.value = wet;
      node.connect(gw).connect(this.rev);
    }
  }
  _pan(v) { const p = this.C.createStereoPanner(); p.pan.value = v; return p; }

  /* ------------------------------------------------------------ beds */
  _startBeds() {
    const C = this.C;
    // rain
    const rs = this._noiseSrc(this.brown);
    this.rainLP = C.createBiquadFilter(); this.rainLP.type = 'lowpass'; this.rainLP.frequency.value = 420;
    const hp = C.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 90;
    this.rainGain = C.createGain(); this.rainGain.gain.value = 0.14;
    rs.connect(this.rainLP).connect(hp).connect(this.rainGain);
    this._route(this.rainGain, 1, 0.25);
    rs.start();
    const lfo = C.createOscillator(); lfo.frequency.value = 0.07;
    const lg = C.createGain(); lg.gain.value = 130;
    lfo.connect(lg).connect(this.rainLP.frequency); lfo.start();

    // dread drone
    this.droneGain = C.createGain(); this.droneGain.gain.value = 0.045;
    this.droneFil = C.createBiquadFilter(); this.droneFil.type = 'lowpass'; this.droneFil.frequency.value = 260;
    const o1 = C.createOscillator(); o1.type = 'triangle'; o1.frequency.value = 54.5;
    const o2 = C.createOscillator(); o2.type = 'sine'; o2.frequency.value = 108.8;
    const og = C.createGain(); og.gain.value = 0.5;
    o1.connect(og); o2.connect(og);
    og.connect(this.droneFil).connect(this.droneGain);
    this._route(this.droneGain, 1, 0.4);
    o1.start(); o2.start();
    const dl = C.createOscillator(); dl.frequency.value = 0.11;
    const dlg = C.createGain(); dlg.gain.value = 0.8;
    dl.connect(dlg).connect(o1.detune); dl.start();

    // entity breath (level driven by setBreath)
    const bs = this._noiseSrc(this.noise);
    const bf = C.createBiquadFilter(); bf.type = 'bandpass'; bf.frequency.value = 520; bf.Q.value = 0.8;
    this.breathGain = C.createGain(); this.breathGain.gain.value = 0;
    const lfoB = C.createOscillator(); lfoB.frequency.value = 0.36;
    const sh = C.createWaveShaper();
    const curve = new Float32Array(128);
    for (let i = 0; i < 128; i++) { const x = i / 127 * 2 - 1; curve[i] = Math.max(0, Math.sin(x * Math.PI)); }
    sh.curve = curve;
    const lbg = C.createGain(); lbg.gain.value = 0.5;
    lfoB.connect(sh).connect(lbg);
    this.breathDepth = C.createGain(); this.breathDepth.gain.value = 0;
    bs.connect(bf).connect(this.breathDepth);
    lbg.connect(this.breathDepth.gain);
    this.breathDepth.connect(this.breathGain);
    this._route(this.breathGain, 1, 0.5);
    bs.start(); lfoB.start();
    this.breathLFO = lfoB;

    // dragging rasp (chase locomotion)
    const ds = this._noiseSrc(this.brown);
    const df = C.createBiquadFilter(); df.type = 'lowpass'; df.frequency.value = 160;
    this.dragGain = C.createGain(); this.dragGain.gain.value = 0;
    const dlfo = C.createOscillator(); dlfo.frequency.value = 1.7;
    const dg2 = C.createGain(); dg2.gain.value = 0.5;
    dlfo.connect(dg2);
    this.dragDepth = C.createGain(); this.dragDepth.gain.value = 0;
    ds.connect(df).connect(this.dragDepth);
    dg2.connect(this.dragDepth.gain);
    this.dragDepth.connect(this.dragGain);
    this._route(this.dragGain, 1, 0.6);
    ds.start(); dlfo.start();

    // heartbeat scheduler
    this.hb = { bpm: 45, vol: 0, next: 0 };
    setInterval(() => this._hbTick(), 40);
  }

  _hbTick() {
    if (!this.ok) return;
    const C = this.C, hb = this.hb;
    if (hb.vol <= 0.01) { hb.next = C.currentTime + 0.1; return; }
    const period = 60 / hb.bpm;
    while (hb.next < C.currentTime + 0.15) {
      this._thump(hb.next, 58, 0.09, hb.vol);
      this._thump(hb.next + period * 0.32, 44, 0.07, hb.vol * 0.7);
      hb.next += period;
    }
  }
  _thump(t, f, dur, vol) {
    const C = this.C;
    const o = C.createOscillator(); o.frequency.setValueAtTime(f, t);
    o.frequency.exponentialRampToValueAtTime(f * 0.55, t + dur);
    const g = C.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); this._route(g, 1, 0.2);
    o.start(t); o.stop(t + dur + 0.05);
  }

  /* --------------------------------------------------------- parameters */
  setDanger(d) {
    if (!this.ok) return;
    const t = this.C.currentTime;
    this.droneFil.frequency.setTargetAtTime(220 + d * 900, t, 0.5);
    this.droneGain.gain.setTargetAtTime(0.04 + d * 0.05, t, 0.5);
    this.hb.bpm = 45 + d * 105;
    this.hb.vol = Math.min(1, d * 1.2);
  }
  setBreath(v) {
    if (!this.ok) return;
    const t = this.C.currentTime;
    this.breathDepth.gain.setTargetAtTime(v * 0.5, t, 0.2);
    this.breathLFO.frequency.setTargetAtTime(0.36 + v * 0.5, t, 0.4);
  }
  setDrag(v) {
    if (!this.ok) return;
    this.dragDepth.gain.setTargetAtTime(v * 0.55, this.C.currentTime, 0.15);
  }

  /* ------------------------------------------------------- one-shots UI */
  switchClick() { this._blip(1900, 0.02, 0.25, 'square'); }
  switchDead() { this._blip(300, 0.05, 0.2, 'square'); }
  _blip(f, dur, vol, type = 'sine') {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator(); o.type = type; o.frequency.value = f;
    const g = C.createGain(); this._env(g, t, 0.002, vol, dur);
    o.connect(g); this._route(g, 0.8, 0.1);
    o.start(t); o.stop(t + dur + 0.05);
  }
  step(sprint) {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const v = sprint ? 0.5 : 0.3;
    const s = C.createBufferSource(); s.buffer = this.noise;
    s.playbackRate.value = 0.6 + Math.random() * 0.3;
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 300;
    const g = C.createGain(); this._env(g, t, 0.004, v, 0.07);
    s.connect(f).connect(g); this._route(g, 1, 0.35);
    s.start(t); s.stop(t + 0.15);
    if (Math.random() < 0.13) this._creakBlip(t + 0.05);
  }
  _creakBlip(t) {
    const C = this.C;
    const o = C.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(150 + Math.random() * 60, t);
    o.frequency.exponentialRampToValueAtTime(70, t + 0.3);
    const vf = C.createOscillator(); vf.frequency.value = 9;
    const vg = C.createGain(); vg.gain.value = 22;
    vf.connect(vg).connect(o.frequency); vf.start(t); vf.stop(t + 0.35);
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 750;
    const g = C.createGain(); this._env(g, t, 0.03, 0.09, 0.3);
    o.connect(f).connect(g); this._route(g, 0.8, 0.5);
    o.start(t); o.stop(t + 0.4);
  }
  tick(vol) {
    if (!this.ok || vol <= 0.02) return;
    this._blip(1150, 0.025, 0.06 * vol, 'sine');
    const C = this.C, t = C.currentTime;
    const s = C.createBufferSource(); s.buffer = this.noise;
    const f = C.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1900; f.Q.value = 8;
    const g = C.createGain(); this._env(g, t, 0.001, 0.05 * vol, 0.03);
    s.connect(f).connect(g); this._route(g, 1, 0.3);
    s.start(t); s.stop(t + 0.06);
  }
  paper() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const s = C.createBufferSource(); s.buffer = this.noise;
    const f = C.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 2400;
    const g = C.createGain(); this._env(g, t, 0.02, 0.12, 0.16);
    s.connect(f).connect(g); this._route(g, 0.8, 0.2);
    s.start(t); s.stop(t + 0.25);
  }
  keyChime() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const car = C.createOscillator(); car.frequency.value = 1244;
    const mod = C.createOscillator(); mod.frequency.value = 622;
    const mg = C.createGain(); mg.gain.value = 900;
    mod.connect(mg).connect(car.frequency);
    const g = C.createGain(); this._env(g, t, 0.004, 0.22, 1.1);
    car.connect(g); this._route(g, 0.7, 0.6);
    car.start(t); mod.start(t); car.stop(t + 1.3); mod.stop(t + 1.3);
    this._blip(1867, 0.4, 0.06);
  }
  batteryGrab() { this.switchClick(); this._blip(720, 0.08, 0.12, 'triangle'); }

  /* ------------------------------------------------------------- doors */
  doorCreak(long) {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime, dur = long ? 1.6 : 1.0;
    const o = C.createOscillator(); o.type = 'sawtooth';
    o.frequency.setValueAtTime(170, t);
    o.frequency.linearRampToValueAtTime(95, t + dur);
    const vf = C.createOscillator(); vf.frequency.value = 7.5;
    const vg = C.createGain(); vg.gain.value = 26;
    vf.connect(vg).connect(o.frequency); vf.start(t); vf.stop(t + dur);
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 850;
    const g = C.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.11, t + 0.15);
    g.gain.linearRampToValueAtTime(0.07, t + dur * 0.7);
    g.gain.linearRampToValueAtTime(0.0001, t + dur);
    o.connect(f).connect(g); this._route(g, 0.9, 0.5);
    o.start(t); o.stop(t + dur + 0.05);
  }
  doorLatch() { this._blip(2600, 0.02, 0.1, 'square'); }
  doorThunk() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator();
    o.frequency.setValueAtTime(78, t);
    o.frequency.exponentialRampToValueAtTime(40, t + 0.16);
    const g = C.createGain(); this._env(g, t, 0.003, 0.5, 0.18);
    o.connect(g); this._route(g, 1, 0.4);
    o.start(t); o.stop(t + 0.25);
  }
  slamBoom() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator();
    o.frequency.setValueAtTime(56, t);
    o.frequency.exponentialRampToValueAtTime(30, t + 0.5);
    const g = C.createGain(); this._env(g, t, 0.004, 0.9, 0.5);
    o.connect(g); this._route(g, 1, 0.8);
    o.start(t); o.stop(t + 0.6);
    const s = C.createBufferSource(); s.buffer = this.noise;
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 900;
    const ng = C.createGain(); this._env(ng, t, 0.002, 0.4, 0.12);
    s.connect(f).connect(ng); this._route(ng, 1, 0.6);
    s.start(t); s.stop(t + 0.2);
  }
  rattle() {
    if (!this.ok) return;
    const C = this.C;
    for (let i = 0; i < 4; i++) {
      const t = C.currentTime + i * 0.07 + Math.random() * 0.02;
      this._blip(1400 + Math.random() * 900, 0.02, 0.14, 'square');
      void t;
    }
  }
  bolts() {
    if (!this.ok) return;
    const C = this.C;
    [0, 0.4, 0.85].forEach((dl, i) => {
      const t = C.currentTime + dl;
      const o = C.createOscillator(); o.type = 'square';
      o.frequency.setValueAtTime(220 - i * 40, t);
      o.frequency.exponentialRampToValueAtTime(90, t + 0.1);
      const g = C.createGain(); this._env(g, t, 0.004, 0.3, 0.12);
      o.connect(g); this._route(g, 1, 0.4);
      o.start(t); o.stop(t + 0.2);
      this._blip(90 + i * 30, 0.2, 0.3, 'sine');
    });
  }

  /* ------------------------------------------------------- ambient dread */
  thumpFar() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator();
    o.frequency.setValueAtTime(46, t);
    o.frequency.exponentialRampToValueAtTime(28, t + 0.7);
    const g = C.createGain(); this._env(g, t, 0.02, 0.5, 0.8);
    o.connect(g); this._route(g, 0.8, 1);
    o.start(t); o.stop(t + 0.9);
  }
  knock(pan = 0, far = true) {
    if (!this.ok) return;
    const C = this.C;
    const n = 2 + (Math.random() * 2 | 0);
    for (let i = 0; i < n; i++) {
      const t = C.currentTime + i * 0.3;
      const o = C.createOscillator();
      o.frequency.setValueAtTime(far ? 90 : 150, t);
      o.frequency.exponentialRampToValueAtTime(50, t + 0.1);
      const g = C.createGain(); this._env(g, t, 0.003, far ? 0.25 : 0.4, 0.12);
      const p = this._pan(pan);
      o.connect(g).connect(p); this._route(p, 1, 0.7);
      o.start(t); o.stop(t + 0.2);
    }
  }
  whisper(pan = 0, dur = 1.0) {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const s = C.createBufferSource(); s.buffer = this.noise; s.loop = true;
    const p = this._pan(pan);
    const g = C.createGain(); g.gain.value = 0;
    const f1 = C.createBiquadFilter(); f1.type = 'bandpass'; f1.Q.value = 6;
    const f2 = C.createBiquadFilter(); f2.type = 'bandpass'; f2.Q.value = 8;
    s.connect(f1).connect(f2).connect(g).connect(p);
    this._route(p, 0.9, 0.5);
    const syll = 4 + (Math.random() * 4 | 0);
    let ct = t;
    for (let i = 0; i < syll; i++) {
      const sd = 0.06 + Math.random() * 0.12;
      f1.frequency.setTargetAtTime(700 + Math.random() * 1700, ct, 0.02);
      f2.frequency.setTargetAtTime(1400 + Math.random() * 1600, ct, 0.02);
      g.gain.setTargetAtTime(0.07 + Math.random() * 0.05, ct, 0.015);
      g.gain.setTargetAtTime(0.004, ct + sd, 0.02);
      ct += sd + 0.03 + Math.random() * 0.06;
    }
    s.start(t); s.stop(ct + 0.1);
  }
  skitter() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const p = this._pan(Math.random() * 1.6 - 0.8);
    const g = C.createGain(); g.gain.value = 0.05;
    const f = C.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = 3000;
    const s = C.createBufferSource(); s.buffer = this.noise;
    s.connect(f).connect(g).connect(p); this._route(p, 1, 0.2);
    for (let i = 0; i < 14; i++) {
      const tt = t + i * 0.045 + Math.random() * 0.02;
      g.gain.setTargetAtTime(0.04 + Math.random() * 0.05, tt, 0.005);
      g.gain.setTargetAtTime(0.001, tt + 0.02, 0.005);
    }
    s.start(t); s.stop(t + 0.9);
  }
  moan() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(180 + Math.random() * 80, t);
    o.frequency.linearRampToValueAtTime(120, t + 2.4);
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 500;
    const g = C.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.06, t + 1.1);
    g.gain.linearRampToValueAtTime(0.0001, t + 2.6);
    o.connect(f).connect(g); this._route(g, 0.7, 0.9);
    o.start(t); o.stop(t + 2.7);
  }
  pipes() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    for (let i = 0; i < 3; i++) {
      const tt = t + i * 0.22;
      const o = C.createOscillator(); o.type = 'square'; o.frequency.value = 300 + Math.random() * 200;
      const g = C.createGain(); this._env(g, tt, 0.003, 0.08, 0.08);
      const p = this._pan(Math.random() - 0.5);
      o.connect(g).connect(p); this._route(p, 1, 0.8);
      o.start(tt); o.stop(tt + 0.15);
    }
  }
  thunder(delay, inten) {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime + delay;
    const s = C.createBufferSource(); s.buffer = this.brown; s.loop = true;
    const f = C.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.setValueAtTime(300, t);
    f.frequency.exponentialRampToValueAtTime(60, t + 2.6);
    const g = C.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.55 * inten, t + 0.06);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 2.4 + inten);
    s.connect(f).connect(g); this._route(g, 1, 0.9);
    s.start(t); s.stop(t + 3.4);
  }

  /* ------------------------------------------------------------- threats */
  clang() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    [213, 517, 1339, 2961].forEach((fr, i) => {
      const o = C.createOscillator(); o.frequency.value = fr * (0.98 + Math.random() * 0.04);
      const g = C.createGain(); this._env(g, t, 0.002, 0.22 / (i + 1), 1.2);
      o.connect(g); this._route(g, 0.9, 0.7);
      o.start(t); o.stop(t + 1.4);
    });
  }
  scrape(dur = 0.7) {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const s = C.createBufferSource(); s.buffer = this.noise; s.loop = true;
    const f = C.createBiquadFilter(); f.type = 'bandpass'; f.Q.value = 3;
    f.frequency.setValueAtTime(380, t);
    f.frequency.linearRampToValueAtTime(900, t + dur * 0.6);
    f.frequency.linearRampToValueAtTime(480, t + dur);
    const am = C.createOscillator(); am.frequency.value = 27;
    const ag = C.createGain(); ag.gain.value = 0.5;
    const g = C.createGain(); g.gain.value = 0.001;
    am.connect(ag).connect(g.gain);
    const gg = C.createGain(); this._env(gg, t, 0.03, 0.3, dur);
    s.connect(f).connect(g).connect(gg); this._route(gg, 1, 0.4);
    s.start(t); am.start(t); s.stop(t + dur + 0.1); am.stop(t + dur + 0.1);
  }
  growl() {
    if (!this.ok) return;
    const C = this.C, t = this.C.currentTime, dur = 1.7;
    const ws = C.createWaveShaper();
    const cur = new Float32Array(256);
    for (let i = 0; i < 256; i++) { const x = i / 128 - 1; cur[i] = Math.tanh(x * 5); }
    ws.curve = cur;
    const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 260;
    const g = C.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(0.4, t + 0.2);
    g.gain.setValueAtTime(0.4, t + dur - 0.3);
    g.gain.linearRampToValueAtTime(0.0001, t + dur);
    [55, 57.5, 52].forEach(fr => {
      const o = C.createOscillator(); o.type = 'sawtooth'; o.frequency.value = fr;
      const vl = C.createOscillator(); vl.frequency.value = 11;
      const vg = C.createGain(); vg.gain.value = 6;
      vl.connect(vg).connect(o.frequency);
      o.connect(ws); o.start(t); o.stop(t + dur); vl.start(t); vl.stop(t + dur);
    });
    ws.connect(f).connect(g); this._route(g, 1, 0.6);
  }
  stingerShort() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    for (let i = 0; i < 5; i++) {
      const o = C.createOscillator(); o.type = 'sawtooth';
      o.frequency.value = 1800 + Math.random() * 1700;
      const tr = C.createOscillator(); tr.frequency.value = 14;
      const tg = C.createGain(); tg.gain.value = 0.5;
      const g = C.createGain(); this._env(g, t, 0.005, 0.09, 0.4);
      tr.connect(tg).connect(g.gain);
      o.connect(g); this._route(g, 1, 0.7);
      o.start(t); o.stop(t + 0.5); tr.start(t); tr.stop(t + 0.5);
    }
  }
  shriek() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    for (let i = 0; i < 4; i++) {
      const o = C.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(850 + i * 90, t);
      o.frequency.exponentialRampToValueAtTime(1750 + i * 120, t + 0.35);
      o.frequency.exponentialRampToValueAtTime(500, t + 0.9);
      const g = C.createGain(); this._env(g, t, 0.01, 0.16, 0.9);
      o.connect(g); this._route(g, 1, 0.8);
      o.start(t); o.stop(t + 1);
    }
    const s = C.createBufferSource(); s.buffer = this.noise;
    const hf = C.createBiquadFilter(); hf.type = 'highpass'; hf.frequency.value = 2000;
    const hg = C.createGain(); this._env(hg, t, 0.01, 0.2, 0.5);
    s.connect(hf).connect(hg); this._route(hg, 1, 0.6);
    s.start(t); s.stop(t + 0.6);
  }
  scream() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    this.duck(0.25);
    for (let i = 0; i < 6; i++) {
      const o = C.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(380 + i * 130, t);
      o.frequency.exponentialRampToValueAtTime(1500 + i * 200, t + 0.25);
      o.frequency.exponentialRampToValueAtTime(220, t + 1.3);
      const rm = C.createOscillator(); rm.frequency.value = 90;
      const rg = C.createGain(); rg.gain.value = 0.5;
      const g = C.createGain(); this._env(g, t, 0.008, 0.2, 1.3);
      rm.connect(rg).connect(g.gain);
      o.connect(g); this._route(g, 0.8, 1);
      o.start(t); o.stop(t + 1.4); rm.start(t); rm.stop(t + 1.4);
    }
    setTimeout(() => this.duck(1), 1600);
  }
  powerDown() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    const o = C.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(210, t);
    o.frequency.exponentialRampToValueAtTime(26, t + 1.9);
    const g = C.createGain(); this._env(g, t, 0.02, 0.3, 2);
    o.connect(g); this._route(g, 1, 0.5);
    o.start(t); o.stop(t + 2.1);
  }
  duck(level) {
    if (!this.ok) return;
    const t = this.C.currentTime;
    this.rainGain.gain.setTargetAtTime(0.14 * level, t, 0.3);
    this.droneGain.gain.setTargetAtTime((0.04) * level, t, 0.3);
  }
  torchDie() { this._blip(140, 0.3, 0.2, 'sine'); }
  torchWeak() { this._blip(500, 0.1, 0.1, 'triangle'); }

  /* --------------------------------------------------------- chase music */
  startChase() {
    if (!this.ok || this.chaseOn) return;
    this.chaseOn = true;
    this.duck(0.35);
    const C = this.C;
    this.chaseGain = C.createGain(); this.chaseGain.gain.value = 0;
    this.chaseGain.gain.setTargetAtTime(0.5, C.currentTime, 0.4);
    this._route(this.chaseGain, 1, 0.35);
    const bpm = 138, sixteenth = 60 / bpm / 4;
    let step = 0, next = C.currentTime + 0.1;
    const bassSeq = [55, 55, 55, 65.4, 55, 55, 49, 41.2];
    this.chaseTimer = setInterval(() => {
      if (!this.chaseOn) return;
      while (next < C.currentTime + 0.18) {
        const s16 = step % 16;
        // pounding kick
        if (s16 % 4 === 0) {
          const o = C.createOscillator();
          o.frequency.setValueAtTime(120, next);
          o.frequency.exponentialRampToValueAtTime(38, next + 0.12);
          const g = C.createGain(); this._env(g, next, 0.002, 0.5, 0.14);
          o.connect(g).connect(this.chaseGain);
          o.start(next); o.stop(next + 0.2);
        }
        // snapping hats
        if (s16 % 2 === 1) {
          const hs = C.createBufferSource(); hs.buffer = this.noise;
          const hf = C.createBiquadFilter(); hf.type = 'highpass'; hf.frequency.value = 6000;
          const hg = C.createGain(); this._env(hg, next, 0.001, 0.06, 0.03);
          hs.connect(hf).connect(hg).connect(this.chaseGain);
          hs.start(next); hs.stop(next + 0.05);
        }
        // driving bass ostinato
        if (s16 % 2 === 0) {
          const o = C.createOscillator(); o.type = 'square';
          o.frequency.value = bassSeq[(step >> 1) % 8];
          const f = C.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 420;
          const g = C.createGain(); this._env(g, next, 0.004, 0.16, sixteenth * 1.7);
          o.connect(f).connect(g).connect(this.chaseGain);
          o.start(next); o.stop(next + sixteenth * 2);
        }
        // string stab at the bar
        if (s16 === 0 && (step >> 4) % 2 === 1) {
          [220, 261.6, 311.1].forEach(fr => {
            const o = C.createOscillator(); o.type = 'sawtooth'; o.frequency.value = fr;
            const g = C.createGain(); this._env(g, next, 0.01, 0.05, 0.5);
            o.connect(g).connect(this.chaseGain);
            o.start(next); o.stop(next + 0.6);
          });
        }
        next += sixteenth; step++;
      }
    }, 60);
  }
  stopChase() {
    if (!this.chaseOn) return;
    this.chaseOn = false;
    clearInterval(this.chaseTimer);
    if (this.chaseGain) {
      this.chaseGain.gain.setTargetAtTime(0.0001, this.C.currentTime, 0.3);
      const cg = this.chaseGain;
      setTimeout(() => { try { cg.disconnect(); } catch (_) {} }, 1500);
    }
    this.duck(1);
  }
  relief() {
    if (!this.ok) return;
    const C = this.C, t = C.currentTime;
    [220, 330, 415, 554, 660].forEach((fr, i) => {
      const o = C.createOscillator(); o.type = 'sine'; o.frequency.value = fr;
      const g = C.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(0.05, t + 1.6 + i * 0.2);
      g.gain.linearRampToValueAtTime(0.0001, t + 5);
      o.connect(g); this._route(g, 0.8, 0.9);
      o.start(t); o.stop(t + 5.2);
    });
  }

  softReset() {
    if (!this.ok) return;
    this.stopChase();
    this.setDanger(0); this.setBreath(0); this.setDrag(0);
    this.duck(1);
  }
}
```

**src/systems/Ghost.js**

```js
// The Entity. Tall, gaunt, tattered; three faces; black vapour; burning eyes.
// Modes: HIDDEN -> APPARITION (scripted cameo) -> STALK (after key 2) ->
// CHASE (finale). The held beam burns him; banishment buys respites.
import * as THREE from 'three';
import { Tex } from '../world/Textures.js';
import { GHOST_LURK } from '../world/House.js';

const MODE = { HIDDEN: 0, APPARITION: 1, STALK: 2, CHASE: 3, DYING: 4, REFORM: 5, LUNGE: 6 };

export class Ghost {
  constructor(scene) {
    this.scene = scene;
    this.mode = MODE.HIDDEN;
    this.timer = 0;
    this.burnMeter = 0;
    this.banishedTotal = 0;
    this.stalkCadence = [14, 24];
    this.nextStalkAt = Infinity;
    this.reformAt = 0;
    this.weaveT = Math.random() * 10;
    this.hooks = {}; // onCatch, onBanish, onLunge

    this._build();
    this.group.visible = false;
    scene.add(this.group);
  }

  _build() {
    const g = this.group = new THREE.Group();

    const skin = new THREE.MeshStandardMaterial({ color: 0x17141a, roughness: 0.92, metalness: 0.05 });
    const cloth = new THREE.MeshStandardMaterial({
      map: Tex.tatter(), color: 0xffffff, roughness: 0.95,
      alphaTest: 0.45, side: THREE.DoubleSide
    });

    const M = (geo, mat, x, y, z) => {
      const m = new THREE.Mesh(geo, mat);
      m.position.set(x, y, z); m.castShadow = true;
      g.add(m); return m;
    };

    // torso — broad wasted shoulders sinking to a hollow pelvis
    M(new THREE.CylinderGeometry(0.26, 0.17, 0.72, 10), skin, 0, 1.5, 0);
    M(new THREE.CylinderGeometry(0.17, 0.2, 0.34, 10), skin, 0, 1.02, 0);
    M(new THREE.CylinderGeometry(0.05, 0.05, 0.14, 8), skin, 0, 1.93, 0);

    // head + interchangeable face
    this.headGrp = new THREE.Group(); this.headGrp.position.set(0, 2.1, 0);
    const skull = new THREE.Mesh(new THREE.SphereGeometry(0.16, 14, 12), skin);
    skull.scale.set(1, 1.18, 0.9); skull.castShadow = true;
    this.headGrp.add(skull);
    this.faceMat = {
      idle: new THREE.MeshStandardMaterial({ map: Tex.ghoul('idle'), roughness: 0.85 }),
      scream: new THREE.MeshStandardMaterial({ map: Tex.ghoul('scream'), roughness: 0.85 }),
      grin: new THREE.MeshStandardMaterial({ map: Tex.ghoul('grin'), roughness: 0.85 })
    };
    this.face = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.3), this.faceMat.idle);
    this.face.position.set(0, -0.01, 0.149);
    this.headGrp.add(this.face);
    const hood = new THREE.Mesh(
      new THREE.ConeGeometry(0.21, 0.36, 10, 1, true), cloth);
    hood.position.y = 0.16; this.headGrp.add(hood);
    g.add(this.headGrp);

    // eyes — twin embers for the bloom pass
    this.eyeMat = new THREE.MeshStandardMaterial({
      color: 0x0a0a0a, emissive: 0xcdd6da, emissiveIntensity: 2.4
    });
    this.eyes = [];
    for (const s of [-1, 1]) {
      const e = new THREE.Mesh(new THREE.SphereGeometry(0.02, 8, 6), this.eyeMat);
      e.position.set(s * 0.055, 0.03, 0.16);
      this.headGrp.add(e); this.eyes.push(e);
    }

    // arms ending in claws
    this.armGroups = [];
    for (const s of [-1, 1]) {
      const aj = new THREE.Group(); aj.position.set(s * 0.27, 1.76, 0);
      const ua = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.038, 0.5, 8), skin);
      ua.position.y = -0.25; ua.castShadow = true; aj.add(ua);
      const fa = new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.03, 0.55, 8), skin);
      fa.position.y = -0.75; fa.castShadow = true; aj.add(fa);
      const hand = new THREE.Group(); hand.position.y = -1.04;
      for (let fi = 0; fi < 4; fi++) {
        const fg = new THREE.Mesh(new THREE.ConeGeometry(0.011, 0.17, 6), skin);
        fg.rotation.z = s * (0.25 + fi * 0.16);
        fg.position.set(s * (fi - 1.5) * 0.02, -0.08, 0);
        fg.castShadow = true; hand.add(fg);
      }
      aj.add(hand);
      aj.rotation.z = s * 0.16;
      g.add(aj); this.armGroups.push(aj);
    }

    // tattered shroud hiding where legs should be
    const skirt = new THREE.Mesh(
      new THREE.ConeGeometry(0.34, 1.05, 12, 1, true), cloth);
    skirt.position.y = 0.52; skirt.castShadow = true;
    g.add(skirt);
    const inner = new THREE.Mesh(
      new THREE.ConeGeometry(0.3, 1.0, 12, 1, true),
      new THREE.MeshStandardMaterial({ color: 0x050405, roughness: 1, side: THREE.BackSide }));
    inner.position.y = 0.52; g.add(inner);

    // trailing strips
    this.strips = [];
    for (let i = 0; i < 12; i++) {
      const w = 0.05 + Math.random() * 0.05, h = 0.5 + Math.random() * 0.45;
      const geo = new THREE.PlaneGeometry(w, h);
      geo.translate(0, -h / 2, 0);
      const sp = new THREE.Mesh(geo, cloth);
      const a = (i / 12) * Math.PI * 2;
      const r = 0.2 + Math.random() * 0.08;
      const yAnchor = Math.random() < 0.5 ? 1.72 : 1.1;
      sp.position.set(Math.cos(a) * r, yAnchor, Math.sin(a) * r);
      sp.rotation.y = -a;
      g.add(sp);
      this.strips.push({ m: sp, ph: Math.random() * 6, amp: 0.1 + Math.random() * 0.15 });
    }

    // black vapour wreathing him
    const N = 42;
    const vp = new Float32Array(N * 3);
    this.vaporSeeds = [];
    for (let i = 0; i < N; i++) {
      vp[i * 3] = (Math.random() - .5) * 0.9;
      vp[i * 3 + 1] = Math.random() * 1.7;
      vp[i * 3 + 2] = (Math.random() - .5) * 0.9;
      this.vaporSeeds.push(Math.random() * 6);
    }
    const vg = new THREE.BufferGeometry();
    vg.setAttribute('position', new THREE.BufferAttribute(vp, 3));
    this.vapor = new THREE.Points(vg, new THREE.PointsMaterial({
      color: 0x2a2a30, size: 0.16, transparent: true, opacity: 0.35,
      depthWrite: false, blending: THREE.NormalBlending
    }));
    this.vapor.frustumCulled = false;
    g.add(this.vapor);

    // phantom ground stain
    const stain = new THREE.Mesh(new THREE.CircleGeometry(0.5, 18),
      new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.4, depthWrite: false }));
    stain.rotation.x = -Math.PI / 2; stain.position.y = 0.02;
    g.add(stain);

    // ember burst pool while burning
    const EN = 50;
    this.emberPos = new Float32Array(EN * 3);
    this.emberLife = new Float32Array(EN);
    const eg = new THREE.BufferGeometry();
    eg.setAttribute('position', new THREE.BufferAttribute(this.emberPos, 3));
    this.embers = new THREE.Points(eg, new THREE.PointsMaterial({
      color: 0xff8a2a, size: 0.05, transparent: true, opacity: 0.9,
      blending: THREE.AdditiveBlending, depthWrite: false
    }));
    this.embers.frustumCulled = false;
    g.add(this.embers);

    this.chest = new THREE.Object3D(); this.chest.position.set(0, 1.5, 0.1);
    g.add(this.chest);
  }

  setExpression(name) { this.face.material = this.faceMat[name]; }
  setEyeColor(hex, inten = 2.4) {
    this.eyeMat.emissive.setHex(hex);
    this.eyeMat.emissiveIntensity = inten;
  }

  chestPos(out = new THREE.Vector3()) {
    this.chest.getWorldPosition(out);
    return out;
  }

  /* --------------------------------------------------------- transitions */
  _flickerIn(dur = 0.5) { this.flick = { t: 0, dur, dir: 1 }; this.group.visible = true; }
  _flickerOut(dur = 0.25, thenHide = true) { this.flick = { t: 0, dur, dir: -1, thenHide }; }

  apparition(pos, dur = 1.2) {
    this.group.position.set(pos[0], 0, pos[1]);
    this.mode = MODE.APPARITION;
    this.timer = dur;
    this.setExpression('idle');
    this.setEyeColor(0xcdd6da, 2.4);
    this._flickerIn(0.28);
  }

  lunge(camPos, camDir) {
    this.group.position.copy(camPos).addScaledVector(camDir, 0.55);
    this.group.position.y = 0;
    this.mode = MODE.LUNGE;
    this.timer = 0.7;
    this.setExpression('scream');
    this.setEyeColor(0xff2418, 3.2);
    this.group.visible = true;
    this.flick = null;
  }

  enableStalk(firstDelay = 4) {
    this.nextStalkAt = firstDelay;
  }
  disableStalk() { this.nextStalkAt = Infinity; }

  startChase() {
    this.mode = MODE.CHASE;
    this.setExpression('scream');
    this.setEyeColor(0xff2418, 3.4);
    this.group.visible = true;
    this.flick = null;
    this._placeForChase(true);
  }

  _candidates(pp) {
    return GHOST_LURK.filter(([x, z]) => {
      const d = Math.hypot(x - pp.x, z - pp.z);
      return d > 6 && d < 16;
    });
  }
  _placeForChase(intercept, pp, doorPos) {
    let best = null, bestScore = -Infinity;
    const pool = GHOST_LURK;
    for (const [x, z] of pool) {
      const d = Math.hypot(x - pp.x, z - pp.z);
      if (d < 8) continue;
      let score = -d;
      if (intercept && doorPos) {
        // favour points lying between the player and the front door
        const dx = doorPos.x - pp.x, dz = doorPos.z - pp.z;
        const L2 = dx * dx + dz * dz;
        const t = Math.max(0, Math.min(1, ((x - pp.x) * dx + (z - pp.z) * dz) / L2));
        const px = pp.x + dx * t, pz = pp.z + dz * t;
        score += 20 - Math.hypot(x - px, z - pz) * 2;
      }
      if (score > bestScore) { bestScore = score; best = [x, z]; }
    }
    this.group.position.set(best[0], 0, best[1]);
  }

  banish() {
    this.mode = MODE.DYING;
    this.timer = 0.55;
    this.burnMeter = 0;
    this.banishedTotal++;
    this.setExpression('scream');
    this.hooks.onBanish?.();
  }

  reset() {
    this.mode = MODE.HIDDEN;
    this.group.visible = false;
    this.burnMeter = 0;
    this.disableStalk();
    this.flick = null;
    this.setExpression('idle');
    this.setEyeColor(0xcdd6da, 2.4);
  }

  get isActive() { return this.mode !== MODE.HIDDEN && this.mode !== MODE.DYING && this.mode !== MODE.REFORM; }

  /* -------------------------------------------------------------- update */
  update(dt, ctx) {
    const { pp, beam, onCatch } = ctx;
    const gp = this.group.position;
    const dist = Math.hypot(gp.x - pp.x, gp.z - pp.z);

    // flicker visibility envelope
    if (this.flick) {
      this.flick.t += dt;
      const p = this.flick.t / this.flick.dur;
      if (p >= 1) {
        if (this.flick.dir === -1 && this.flick.thenHide) {
          this.group.visible = false;
          if (this.mode === MODE.APPARITION || this.mode === MODE.LUNGE) this.mode = MODE.HIDDEN;
        }
        this.flick = null;
        this.group.visible = this.mode !== MODE.HIDDEN;
      } else {
        const gate = this.flick.dir === 1 ? p : 1 - p;
        this.group.visible = Math.random() < (0.15 + gate * 0.85);
      }
    }

    switch (this.mode) {
      case MODE.HIDDEN: {
        if (this.nextStalkAt !== Infinity) {
          this.nextStalkAt -= dt;
          if (this.nextStalkAt <= 0) {
            const cands = this._candidates(pp);
            if (cands.length) {
              const [x, z] = cands[(Math.random() * cands.length) | 0];
              this.group.position.set(x, 0, z);
              this.mode = MODE.STALK;
              this.stalkAge = 0;
              this.setExpression('grin');
              this.setEyeColor(0xcdd6da, 2.2);
              this._flickerIn(0.6);
            }
            this.nextStalkAt = this.stalkCadence[0] + Math.random() *
              (this.stalkCadence[1] - this.stalkCadence[0]);
          }
        }
        if (this.mode === MODE.REFORM) break;
        break;
      }
      case MODE.REFORM: {
        this.timer -= dt;
        if (this.timer <= 0) {
          this.mode = MODE.CHASE;
          this._placeForChase(true, pp, ctx.doorPos);
          this._flickerIn(0.4);
          this.setExpression('scream');
          this.setEyeColor(0xff2418, 3.4);
        }
        break;
      }
      case MODE.APPARITION: {
        this.timer -= dt;
        this._faceTowards(pp, dt, 20);
        this.headGrp.rotation.z = Math.sin(this.timer * 30) * 0.03;
        if (this.timer <= 0 && !this.flick) this._flickerOut(0.22);
        break;
      }
      case MODE.LUNGE: {
        this.timer -= dt;
        this._faceTowards(pp, dt, 40);
        this.headGrp.scale.setScalar(1.35);
        if (this.timer <= 0 && !this.flick) {
          this.headGrp.scale.setScalar(1);
          this._flickerOut(0.15);
          this.hooks.onLungeEnd?.();
        }
        break;
      }
      case MODE.STALK: {
        this.stalkAge += dt;
        this._faceTowards(pp, dt, 3);
        const lit = beam && dist < 9;
        let sp = 0.38;
        if (lit) {
          sp *= 0.22; // recoils from the beam
          this.burnMeter += dt * 0.5;
          this.headGrp.rotation.z = Math.sin(performance.now() / 40) * 0.06;
          if (Math.random() < 0.3) this.setExpression('scream'); else if (Math.random() < 0.2) this.setExpression('grin');
        } else {
          this.burnMeter = Math.max(0, this.burnMeter - dt * 0.3);
          this.headGrp.rotation.z *= 0.9;
        }
        if (this.burnMeter >= 1) { this.banish(); break; }
        const dir = this._steer(pp, dt, sp, 0.15);
        gp.x += dir.x * sp * dt; gp.z += dir.z * sp * dt;
        // unnoticed approach ends in a lunge to the face
        if (dist < 1.5 && !lit) {
          this.lunge(ctx.camPos, ctx.camDir);
          this.hooks.onLunge?.();
        }
        if (this.stalkAge > 22 && !this.flick) { this._flickerOut(0.3); this.mode = MODE.HIDDEN; }
        break;
      }
      case MODE.CHASE: {
        this._faceTowards(pp, dt, 6);
        const lit = beam && dist < 10;
        if (lit) {
          this.burnMeter += dt * 0.8;
          this.setExpression('scream');
          this.headGrp.rotation.z = Math.sin(performance.now() / 28) * 0.08;
          if (this.burnMeter >= 1) {
            this.banish();
            this.mode = MODE.REFORM;
            this.timer = 8;
            this.group.visible = false;
            break;
          }
        } else {
          this.burnMeter = Math.max(0, this.burnMeter - dt * 0.35);
          if (Math.random() < 0.02) this.setExpression('grin');
        }
        // rubber-banded pursuit through walls
        let sp = dist > 13 ? 3.5 : dist < 5 ? 2.55 : 2.95;
        if (lit) sp *= 0.3;
        const dir = this._steer(pp, dt, sp, 0.55);
        gp.x += dir.x * sp * dt;
        gp.z += dir.z * sp * dt;
        if (dist < 0.85) onCatch?.();
        break;
      }
      case MODE.DYING: {
        this.timer -= dt;
        const p = Math.max(0, this.timer / 0.55);
        this.group.scale.set(1 + (1 - p) * 0.5, Math.max(0.05, p), 1 + (1 - p) * 0.5);
        this.group.visible = Math.random() < 0.7;
        if (this.timer <= 0) {
          this.group.scale.set(1, 1, 1);
          this.group.visible = false;
          this.mode = this.wasChaseBeforeBanish ? MODE.REFORM : MODE.HIDDEN;
          if (this.mode === MODE.REFORM) this.timer = 0; // set by caller
        }
        break;
      }
    }

    // remember chase-context for banish routing
    if (this.mode === MODE.CHASE) this.wasChaseBeforeBanish = true;
    else if (this.mode === MODE.STALK || this.mode === MODE.HIDDEN) this.wasChaseBeforeBanish = false;

    // shared idle animation
    if (this.group.visible) {
      const t = performance.now() / 1000;
      const moving = this.mode === MODE.CHASE || this.mode === MODE.STALK;
      this.group.position.y = Math.sin(t * 1.7) * 0.05 + (this.mode === MODE.CHASE ? 0.08 : 0);
      this.group.rotation.x = this.mode === MODE.CHASE ? 0.1 : 0;
      for (const s of this.strips) {
        s.m.rotation.x = Math.sin(t * (2 + s.ph) + s.ph) * (s.amp + (moving ? 0.25 : 0));
        s.m.rotation.z = Math.cos(t * (1.6 + s.ph) + s.ph) * s.amp;
      }
      for (let i = 0; i < this.armGroups.length; i++) {
        this.armGroups[i].rotation.x = Math.sin(t * 1.3 + i * 2) * (moving ? 0.2 : 0.06) - 0.1;
      }
      // vapour swirl
      const va = this.vapor.geometry.attributes.position;
      for (let i = 0; i < this.vaporSeeds.length; i++) {
        const a = t * 0.6 + this.vaporSeeds[i];
        va.setX(i, Math.cos(a) * (0.25 + 0.2 * Math.sin(this.vaporSeeds[i])));
        va.setY(i, ((va.getY(i) + dt * 0.25) % 1.7));
        va.setZ(i, Math.sin(a * 0.8) * (0.25 + 0.2 * Math.cos(this.vaporSeeds[i])));
      }
      va.needsUpdate = true;
      // embers while burning
      const ea = this.embers.geometry.attributes.position;
      const burning = this.burnMeter > 0.02 && (this.mode === MODE.STALK || this.mode === MODE.CHASE);
      this.embers.visible = burning;
      if (burning) {
        const cp = this.chestPos();
        for (let i = 0; i < this.emberLife.length; i++) {
          this.emberLife[i] -= dt;
          if (this.emberLife[i] <= 0) {
            this.emberLife[i] = 0.4 + Math.random() * 0.3;
            ea.setXYZ(i, cp.x - gp.x + (Math.random() - .5) * 0.2, 1.5, cp.z - gp.z + (Math.random() - .5) * 0.2);
          } else {
            ea.setY(i, ea.getY(i) + dt * 1.2);
          }
        }
        ea.needsUpdate = true;
        this.setEyeColor(0xffa53c, 3.6);
      } else if (this.mode !== MODE.CHASE) {
        this.setEyeColor(0xcdd6da, 2.2);
      }
    }
  }

  _faceTowards(pp, dt, rate) {
    const gp = this.group.position;
    const want = Math.atan2(pp.x - gp.x, pp.z - gp.z);
    let cur = this.group.rotation.y;
    let diff = want - cur;
    while (diff > Math.PI) diff -= Math.PI * 2;
    while (diff < -Math.PI) diff += Math.PI * 2;
    this.group.rotation.y = cur + diff * Math.min(1, rate * dt);
  }
  _steer(pp, dt, sp, weaveAmp) {
    this.weaveT += dt;
    const gp = this.group.position;
    const dx = pp.x - gp.x, dz = pp.z - gp.z;
    const L = Math.hypot(dx, dz) || 1;
    const nx = dx / L, nz = dz / L;
    const w = Math.sin(this.weaveT * 3.1) * weaveAmp;
    return { x: nx + (-nz) * w, z: nz + nx * w };
  }
}
```

**src/systems/ScareDirector.js**

```js
// One-shot trigger volumes, the escalating scare script, randomized ambient
// dread, and the rolling lightning storm. Every big scare fires exactly once.
import { ROOMS } from '../world/House.js';

const inRect = (p, r, pad = 0) =>
  p.x > r.x0 - pad && p.x < r.x1 + pad && p.z > r.z0 - pad && p.z < r.z1 + pad;

export class ScareDirector {
  constructor(refs) {
    // { house, audio, ghost, hud, player, game }
    Object.assign(this, refs);
    this.reset();
  }

  reset() {
    this.fired = {};
    this.timers = [];
    this.ambientAt = 8 + Math.random() * 8;
    this.lightningAt = 6 + Math.random() * 8;
    this.finaleDone = false;
    this.act = 1;
    this.house.snapshotProps();
    this.house.killSconceRestore?.();
    this.house.restoreProps();
    this.house.sconce.alive = true;
    const f = this.house.flickerLights.find(f => f.kind === 'bulbFaulty');
    if (f) { f.dead = false; f.light.intensity = f.base; this.house.sconce.bulb.material.emissiveIntensity = 1.4; }
    this.house.setBlackout(false);
  }

  after(sec, fn) { this.timers.push({ t: sec, fn }); }

  once(id, cond, fn) {
    if (this.fired[id] || !cond) return;
    this.fired[id] = true;
    fn();
  }

  onKey(room, count) {
    const { audio, ghost, hud, player, game } = this;

    if (room === 'study' && !this.fired.studyGhost) {
      this.fired.studyGhost = true;
      // it is standing in the doorway behind you
      this.after(0.6, () => {
        ghost.apparition([-7, -1.0], 1.2);
        audio.stingerShort();
        hud.flash('#7a1518', 0.22, 0.3);
        player.addTrauma(0.45);
      });
    }

    if (count === 2 && !this.fired.stalkBegin) {
      this.fired.stalkBegin = true;
      this.act = 2;
      this.after(1.2, () => {
        audio.growl();
        hud.setWarn(true);
        hud.toast('It knows you are here.');
        ghost.enableStalk(4);
      });
    }

    if (count === 3 && !this.finaleDone) {
      this.finaleDone = true;
      this.act = 3;
      this._finale();
    }
  }

  _finale() {
    const { audio, ghost, hud, player, house, game } = this;
    // BLACKOUT BEAT — even the torch fails
    house.setBlackout(true);
    player.forcedDim = 1.6;
    audio.powerDown();
    audio.setDanger(0.85);
    this.after(1.5, () => audio.whisper(-0.9, 1.1));
    this.after(1.9, () => audio.whisper(0.9, 1.0));
    this.after(2.2, () => audio.whisper(0, 0.9));

    this.after(2.5, () => {
      // glimpse it, inches away
      const ep = player.eyePos();
      const fd = player.lookDir();
      ghost.apparition([ep.x + fd.x * 2.2, ep.z + fd.z * 2.2], 0.35);
      audio.scream();
      hud.flash('#ffffff', 0.35, 0.25);
      player.addTrauma(0.9);
    });

    this.after(2.75, () => {
      house.setBlackout(false);
      audio.thunder(0.05, 1);
      house.boostMoons(3);
      this.after(0.5, () => house.boostMoons(0));
    });

    this.after(3.0, () => {
      ghost.startChase();
      audio.startChase();
      house.doors.front.locked = false;
      audio.bolts();
      game.beginFinale();
    });
  }

  update(dt) {
    const { player, house, audio, ghost, hud } = this;
    const p = player.root.position;

    // deferred timers
    for (let i = this.timers.length - 1; i >= 0; i--) {
      this.timers[i].t -= dt;
      if (this.timers[i].t <= 0) { const fn = this.timers[i].fn; this.timers.splice(i, 1); fn(); }
    }

    /* ------------- scripted one-shot zones -------------- */
    this.once('living', inRect(p, ROOMS.living), () => {
      audio.thumpFar();
      this.after(0.9, () => audio.whisper(Math.random() * 1.6 - 0.8, 1.2));
      player.addTrauma(0.2);
      // a portrait leans, very slightly, forever
      house.portraitAskew.rotation.z = 0.055;
    });

    this.once('hall', inRect(p, ROOMS.hall), () => {
      // lights seize, something slams behind you, the sconce dies
      const f = house.flickerLights.find(f => f.kind === 'bulbFaulty');
      let tAcc = 0;
      for (let i = 0; i < 7; i++) {
        tAcc += 0.1 + Math.random() * 0.12;
        this.after(tAcc, () => {
          if (house.sconce.alive) house.sconce.light.intensity = Math.random() < 0.5 ? 0 : 8;
          house.foyerBulb.light.intensity = Math.random() < 0.5 ? 0 : 11;
        });
      }
      this.after(tAcc + 0.25, () => {
        audio.slamBoom();
        player.addTrauma(0.55);
        hud.flash('#000000', 0.5, 0.2);
        house.killSconce();
      });
    });

    this.once('kitchen', inRect(p, ROOMS.kitchen), () => {
      audio.clang();
      player.addTrauma(0.4);
      // a chair drags itself across the tiles
      const ch = house.slidingChair;
      const from = ch.position.clone();
      const to = from.clone().add(new (from.constructor)(0.9, 0, 0.35));
      let t = 0;
      const anim = (dt2) => {
        t += dt2;
        const k = Math.min(1, t / 0.7);
        ch.position.lerpVectors(from, to, 1 - (1 - k) * (1 - k));
        if (k < 1) requestAnimationFrame(anim);
      };
      requestAnimationFrame(anim);
      audio.scrape(0.7);
      house.pans.forEach(pn => pn.impulse = true);
      this.after(1.1, () => audio.whisper(0.6, 0.8));
    });

    this.once('bedroom', inRect(p, ROOMS.bedroom), () => {
      const slammed = house.doors.bedroom.slam();
      if (!slammed) { audio.slamBoom(); audio.rattle(); }
      player.addTrauma(0.45);
      this.after(1.4, () => audio.whisper(-0.7, 1.0));
    });

    /* ------------- randomized ambient dread -------------- */
    this.ambientAt -= dt;
    if (this.ambientAt <= 0) {
      this.ambientAt = 9 + Math.random() * 10;
      if (!ghost.isActive && this.act >= 1) {
        const roll = Math.random();
        const pan = Math.random() * 1.7 - 0.85;
        if (roll < 0.28) audio.moan();
        else if (roll < 0.46) audio.whisper(pan, 0.8 + Math.random() * 0.6);
        else if (roll < 0.62) audio.knock(pan, true);
        else if (roll < 0.74) audio.skitter();
        else if (roll < 0.88) audio.pipes();
        else audio.thumpFar();
      }
    }

    /* ------------- the storm outside -------------- */
    this.lightningAt -= dt;
    if (this.lightningAt <= 0) {
      this.lightningAt = (this.act === 3 ? 7 : 12) + Math.random() * (this.act === 3 ? 7 : 12);
      this._strike();
    }
  }

  _strike() {
    const { house, hud, audio } = this;
    const pulses = 2 + (Math.random() * 2 | 0);
    for (let i = 0; i < pulses; i++) {
      this.after(i * (0.1 + Math.random() * 0.12), () => {
        house.boostMoons(5 + Math.random() * 4);
        hud.lightning(0.7 + Math.random() * 0.5);
      });
    }
    this.after(pulses * 0.14, () => house.boostMoons(0));
    const delay = 0.25 + Math.random() * 2.0;
    audio.thunder(delay, Math.max(0.3, 1.2 - delay * 0.4));
  }
}
```

**src/Game.js**

```js
// Orchestrator: renderer + post pipeline, state machine, interaction,
// the burn-the-entity mechanic, win/loss cinematics, restart.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

import { Tex } from './world/Textures.js';
import { House, NOTE_DEFS } from './world/House.js';
import { Player } from './player/Player.js';
import { AudioEngine } from './systems/AudioEngine.js';
import { Ghost } from './systems/Ghost.js';
import { ScareDirector } from './systems/ScareDirector.js';
import { HUD } from './ui/HUD.js';

const STATE = { TITLE: 0, PLAYING: 1, CAUGHT: 2, ESCAPED: 3, ESCAPING: 4 };

export class Game {
  constructor() {
    this.state = STATE.TITLE;
    this.keysFound = 0;
    this.banishes = 0;
    this.runStart = 0;
    this.eQueued = false;
    this.suppressPause = false;
    this.cine = null;
    this.perf = { acc: 0, n: 0, degraded: false };
  }

  /* ------------------------------------------------------------- boot */
  boot() {
    const renderer = this.renderer = new THREE.WebGLRenderer({
      antialias: false, powerPreference: 'high-performance'
    });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.setSize(innerWidth, innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    document.getElementById('app').appendChild(renderer.domElement);

    Tex.setMaxAniso(Math.min(8, renderer.capabilities.getMaxAnisotropy()));

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x000000, 0.075);

    this.camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.05, 60);

    // near-black base so the flashlight owns the world
    this.scene.add(new THREE.AmbientLight(0x30363f, 0.3));
    this.scene.add(new THREE.HemisphereLight(0x232a36, 0x0b0908, 0.22));

    // post: HDR target -> bloom -> output
    const rt = new THREE.WebGLRenderTarget(innerWidth, innerHeight, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(renderer, rt);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.55, 0.55, 0.82);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    this.hud = new HUD();
    this.audio = new AudioEngine();

    this._buildWorld();
    this.player = new Player(this.camera, this.scene);
    this.player.onStep = (sprint) => this.audio.step(sprint);

    this.ghost = new Ghost(this.scene);
    this.ghost.hooks = {
      onBanish: () => {
        this.banishes++;
        this.audio.shriek();
        this.hud.toast('It tore itself apart — go, NOW.', 2.2);
      },
      onCatch: () => { if (this.state === STATE.PLAYING) this._caught(); },
      onLunge: () => {
        this.audio.scream();
        this.hud.flash('#7a1518', 0.5, 0.4);
        this.player.addTrauma(1);
      },
      onLungeEnd: () => {}
    };

    this.director = new ScareDirector({
      house: this.house, audio: this.audio, ghost: this.ghost,
      hud: this.hud, player: this.player, game: this
    });
    this.house.audioHook = this.audio;
    this.house.onTick = (v) => this.audio.tick(v);

    this._bind();
    this.clock = new THREE.Clock();
    this.renderer.setAnimationLoop(() => this._frame());

    // title tableau: slow drift through the foyer while the storm plays
    this.titleT = 0;
  }

  _buildWorld() {
    this.world = new THREE.Group();
    this.scene.add(this.world);
    this.house = new House(this.world);
  }

  _disposeWorld() {
    this.world.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        const mats = Array.isArray(o.material) ? o.material : [o.material];
        for (const m of mats) m.dispose(); // shared textures survive in cache
      }
    });
    this.scene.remove(this.world);
  }

  /* ------------------------------------------------------------ input */
  _bind() {
    const dom = this.renderer.domElement;
    const $ = (id) => document.getElementById(id);

    addEventListener('resize', () => {
      this.camera.aspect = innerWidth / innerHeight;
      this.camera.updateProjectionMatrix();
      renderer.setSize(innerWidth, innerHeight);
      this.composer.setSize(innerWidth, innerHeight);
    });

    document.addEventListener('mousemove', (e) => {
      if (document.pointerLockElement === dom && this.state === STATE.PLAYING && !this.hud.noteOpen)
        this.player.onMouse(e.movementX, e.movementY);
    });

    document.addEventListener('keydown', (e) => {
      if (e.repeat) return;
      const k = e.code;
      if (k === 'KeyW') this.player.input.f = 1;
      if (k === 'KeyS') this.player.input.b = 1;
      if (k === 'KeyA') this.player.input.l = 1;
      if (k === 'KeyD') this.player.input.r = 1;
      if (k === 'ShiftLeft' || k === 'ShiftRight') this.player.input.sprint = true;
      if (k === 'KeyF' && this.state === STATE.PLAYING) this.player.toggleTorch(this.audio);
      if (k === 'KeyE') {
        if (this.hud.noteOpen) { this.hud.closeNote(); this.audio.paper(); }
        else this.eQueued = true;
      }
    });
    document.addEventListener('keyup', (e) => {
      const k = e.code;
      if (k === 'KeyW') this.player.input.f = 0;
      if (k === 'KeyS') this.player.input.b = 0;
      if (k === 'KeyA') this.player.input.l = 0;
      if (k === 'KeyD') this.player.input.r = 0;
      if (k === 'ShiftLeft' || k === 'ShiftRight') this.player.input.sprint = false;
    });

    document.addEventListener('pointerlockchange', () => {
      const locked = document.pointerLockElement === dom;
      if (!locked && this.state === STATE.PLAYING && !this.suppressPause) {
        this.paused = true;
        this.hud.show(this.hud.el.pause);
      }
      if (locked) { this.paused = false; if (this.state === STATE.PLAYING) this.hud.show(null); }
    });

    const requestLock = () => {
      dom.requestPointerLock()?.catch?.(() => {});
    };

    // title
    $('btn-begin').addEventListener('click', () => this._begin(requestLock));
    $('scr-title').addEventListener('click', () => this._begin(requestLock));

    // pause resume
    $('scr-pause').addEventListener('click', () => { this.hud.show(null); requestLock(); });

    // restarts
    $('btn-retry').addEventListener('click', () => { this._restart(); requestLock(); });
    $('btn-again').addEventListener('click', () => { this._restart(); requestLock(); });

    // note dismiss by click
    this.hud.el.noteOv.addEventListener('click', () => { this.hud.closeNote(); this.audio.paper(); });

    dom.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  _begin(requestLock) {
    if (this.state !== STATE.TITLE) return;
    this.audio.init();
    this.audio.resume();
    this.suppressPause = false;
    requestLock();

    // glide from the title tableau into the player's eyes
    const ep = this.player.eyePos().clone();
    const eq = this.camera.quaternion.clone();
    this.player.reset(0, 6.4, 0);
    this.player.root.updateMatrixWorld(true);
    const tp = this.player.eyePos().clone();
    this.player.root.rotation.y = 0;
    const tq = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, 0));
    this.cine = { t: 0, dur: 1.4, fp: ep, fq: eq, tp, tq };

    this.state = STATE.PLAYING;
    this.runStart = performance.now();
    this.hud.show(null);
    this.hud.setObjective('Find the three brass keys', 'kitchen &middot; study &middot; bedroom');
    this.hud.reset();
    this.audio.setDanger(0.05);
  }

  _restart() {
    this.suppressPause = true;
    this._disposeWorld();
    this._buildWorld();
    this.house.audioHook = this.audio;
    this.house.onTick = (v) => this.audio.tick(v);
    this.player.reset(0, 6.4, 0);
    this.ghost.reset();
    this.director.reset();
    this.audio.softReset();
    this.keysFound = 0;
    this.banishes = 0;
    this.hud.reset();
    this.hud.setObjective('Find the three brass keys', 'kitchen &middot; study &middot; bedroom');
    this.hud.show(null);
    this.state = STATE.PLAYING;
    this.runStart = performance.now();
    this.paused = false;
    setTimeout(() => { this.suppressPause = false; }, 400);
  }

  /* -------------------------------------------------------- interaction */
  _raycaster = new THREE.Raycaster();

  _interact() {
    this._raycaster.far = 2.35;
    this._raycaster.setFromCamera({ x: 0, y: 0 }, this.camera);
    const hits = this._raycaster.intersectObjects(this.house.pickTargets, false);
    let label = null, acted = false;

    if (hits.length) {
      const ud = hits[0].object.userData.owner || hits[0].object.userData;
      if (ud?.type) {
        const d = ud.def ?? ud.door ?? ud;
        switch (ud.type) {
          case 'key':
            label = 'Take the <b>brass key</b>';
            if (this.eQueued) {
              ud.def.collected = true;
              ud.def.mesh.visible = false;
              ud.def.proxy.visible = false;
              this.house.pickTargets = this.house.pickTargets.filter(p => p !== ud.def.proxy);
              this.keysFound++;
              this.audio.keyChime();
              this.hud.setKeys(this.keysFound);
              this.director.onKey(ud.def.room, this.keysFound);
              if (this.keysFound < 3)
                this.hud.setObjective(`Find the three brass keys — <b>${this.keysFound}/3</b>`,
                  'kitchen &middot; study &middot; bedroom');
            }
            break;
          case 'battery':
            label = 'Take the <b>torch cell</b>';
            if (this.eQueued) {
              ud.def.taken = true;
              ud.def.mesh.visible = false;
              ud.def.proxy.visible = false;
              this.house.pickTargets = this.house.pickTargets.filter(p => p !== ud.def.proxy);
              this.player.addCharge(55);
              this.audio.batteryGrab();
              this.hud.toast('+ torch cell');
            }
            break;
          case 'note':
            label = 'Read the <b>note</b>';
            if (this.eQueued) { this.hud.openNote(ud.def); this.audio.paper(); }
            break;
          case 'door': {
            const door = ud.door;
            if (door.kind === 'front' && door.locked) {
              if (this.keysFound >= 3) {
                label = 'Turn the <b>key</b> — escape';
                if (this.eQueued) { this._escape(); acted = true; }
              } else {
                label = `Locked tight — <b>${3 - this.keysFound}</b> key${3 - this.keysFound > 1 ? 's' : ''} missing`;
                if (this.eQueued) { door.rattle(); this.audio.rattle(); this.hud.toast('It will not give.'); }
              }
            } else {
              label = door.openT > 0.5 ? 'Close the door' : 'Open the door';
              if (this.eQueued) door.toggle();
            }
            break;
          }
        }
      }
    }
    this.hud.prompt(label);
    this.eQueued = false;
  }

  /* ------------------------------------------------------ state shifts */
  beginFinale() {
    this.hud.setObjective('<span style="color:#c94b3e">RUN — unlock the front door</span>', '');
    this.hud.setWarn(false);
  }

  _caught() {
    this.state = STATE.CAUGHT;
    this.suppressPause = true;
    this.audio.stopChase();
    this.audio.scream();
    this.player.addTrauma(1);
    // the face fills the world
    const c = document.createElement('canvas');
    c.width = 512; c.height = 512;
    c.getContext('2d').drawImage(Tex.ghoul('scream').image, 0, 0);
    this.hud.jumpscare(c.toDataURL());
    this.hud.flash('#7a1518', 0.6, 0.5);
    const secs = (performance.now() - this.runStart) / 1000;
    const txt = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(Math.floor(secs % 60)).padStart(2, '0')}`;
    setTimeout(() => {
      this.hud.deathStats(txt, this.keysFound);
      this.hud.show(this.hud.el.death);
      document.exitPointerLock?.();
      this.suppressPause = false;
    }, 1150);
  }

  _escape() {
    this.state = STATE.ESCAPING;
    this.suppressPause = true;
    const door = this.house.doors.front;
    this.audio.bolts();
    this.audio.relief();
    this.audio.stopChase();
    this.ghost.reset();

    // dawn-cold light pouring in
    const outLight = new THREE.PointLight(0xbcd2ff, 0, 14, 1.6);
    outLight.position.set(0, 1.7, 9.4);
    this.scene.add(outLight);
    const glow = new THREE.Mesh(
      new THREE.PlaneGeometry(2.4, 2.8),
      new THREE.MeshBasicMaterial({ color: 0xdfe9ff, transparent: true, opacity: 0, depthWrite: false }));
    glow.position.set(0, 1.4, 8.4);
    this.scene.add(glow);

    let t = 0;
    const step = (dt) => {
      t += dt;
      outLight.intensity = Math.min(90, t * 70);
      glow.material.opacity = Math.min(0.85, t * 0.6);
      this.scene.fog.density = Math.max(0.02, 0.075 - t * 0.03);
      // wrench the gaze to the opening door
      const ep = this.player.eyePos();
      const look = new THREE.Vector3(0, 1.4, 8.2).sub(ep).normalize();
      const want = Math.atan2(-look.x, -look.z);
      let diff = want - this.player.yaw;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      this.player.yaw += diff * Math.min(1, dt * 3);
      this.player.pitch *= (1 - Math.min(1, dt * 3));
      if (t > 0.7 && door.openT < 1) { door.target = 1; door.speed = 1.1; }
      if (t > 1.1) this.hud.flash('#eef3ff', Math.min(1, (t - 1.1) * 1.4), 99);
      if (t > 2.1) {
        const secs = (performance.now() - this.runStart) / 1000;
        const txt = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(Math.floor(secs % 60)).padStart(2, '0')}`;
        this.hud.winStats(txt, this.banishes);
        this.hud.show(this.hud.el.win);
        this.hud.flash('#eef3ff', 0, 0.01);
        this.scene.fog.density = 0.075;
        this.scene.remove(outLight, glow);
        document.exitPointerLock?.();
        this.suppressPause = false;
        this.state = STATE.ESCAPED;
        return;
      }
      requestAnimationFrame(() => step(this.clock.getDelta()));
    };
    requestAnimationFrame(() => step(this.clock.getDelta()));
  }

  /* -------------------------------------------------------------- frame */
  _frame() {
    const dt = Math.min(0.05, this.clock.getDelta());
    const t = this.clock.elapsedTime;

    // adaptive quality watchdog
    if (this.state === STATE.PLAYING && !this.perf.degraded) {
      this.perf.acc += dt; this.perf.n++;
      if (this.perf.n >= 180) {
        const avg = this.perf.acc / this.perf.n;
        if (avg > 1 / 45) {
          this.renderer.setPixelRatio(1);
          this.bloom.strength *= 0.8;
          this.perf.degraded = true;
        }
        this.perf.acc = 0; this.perf.n = 0;
      }
    }

    if (this.state === STATE.TITLE) {
      // living diorama behind the menu
      this.titleT += dt;
      const a = this.titleT * 0.05;
      this.camera.position.set(Math.sin(a) * 1.2, 1.55 + Math.sin(this.titleT * 0.3) * 0.05, 5.4 + Math.cos(a) * 0.4);
      this.camera.lookAt(0, 1.5, -2);
      this.house.update(dt, t, this.camera.position);
      this.director.update(dt * 0.4);
      this.hud.frame(dt);
      this.composer.render();
      return;
    }

    if (this.state === STATE.PLAYING && !this.paused) {
      // cinematic hand-off from the title glide
      if (this.cine) {
        this.cine.t += dt;
        const k = Math.min(1, this.cine.t / this.cine.dur);
        const e = 1 - Math.pow(1 - k, 3);
        this.camera.position.lerpVectors(this.cine.fp, this.cine.tp, e);
        this.camera.quaternion.slerpQuaternions(this.cine.fq, this.cine.tq, e);
        if (k >= 1) this.cine = null;
      }

      const { sprinting } = this.player.update(dt, this.house.solids, this.audio);
      this.house.update(dt, t, this.player.root.position);

      // sprint widens the view a breath
      const wantFov = sprinting ? 76 : 70;
      if (Math.abs(this.camera.fov - wantFov) > 0.05) {
        this.camera.fov += (wantFov - this.camera.fov) * Math.min(1, dt * 5);
        this.camera.updateProjectionMatrix();
      }

      // entity brain
      const gp = this.ghost.group.position;
      const dist = Math.hypot(gp.x - this.player.root.position.x, gp.z - this.player.root.position.z);
      const beam = this.ghost.isActive &&
        this.player.beamOn(this.ghost.chestPos());
      this.ghost.update(dt, {
        pp: this.player.root.position,
        beam,
        camPos: this.player.eyePos(),
        camDir: this.player.lookDir(),
        doorPos: { x: 0, z: 8.6 },
        onCatch: this.ghost.hooks.onCatch
      });

      // burn meter HUD
      const burning = beam && (this.ghost.mode === 2 || this.ghost.mode === 3);
      this.player.externalBurnDrain = burning;
      this.hud.burn(burning || (this.ghost.isActive && this.ghost.burnMeter > 0.02),
        this.ghost.burnMeter);

      // proximity dread
      let danger = 0;
      if (this.ghost.isActive) danger = Math.max(0, 1 - (dist - 1) / 10);
      if (this.ghost.mode === 3) danger = Math.max(danger, 0.75);
      this._dangerSm = (this._dangerSm ?? 0) + (danger - (this._dangerSm ?? 0)) * Math.min(1, dt * 2);
      this.audio.setDanger(this._dangerSm);
      this.audio.setBreath(this.ghost.isActive ? Math.pow(Math.max(0, 1 - (dist - 1.2) / 11), 1.4) : 0);
      this.audio.setDrag(this.ghost.mode === 3 ? Math.max(0, 1 - dist / 14) : 0);
      this.hud.veil(this.ghost.mode === 3 ? Math.max(0, 1 - (dist - 1) / 9) * 0.6 : 0);

      this._interact();
      this.director.update(dt);
      this.hud.battery(this.player.torch.battery);
    }

    if (this.state === STATE.PLAYING || this.state === STATE.CAUGHT || this.state === STATE.ESCAPED) {
      this.hud.frame(dt);
      this.composer.render();
    } else {
      this.hud.frame(dt);
      this.composer.render();
    }
  }
}
```

Project tree as delivered:

```
bridge-horror-house/
├── package.json
├── vite.config.js
├── SYSTEM_PROMPT.md
├── index.html
└── src/
    ├── main.js
    ├── Game.js
    ├── world/
    │   ├── Textures.js
    │   └── House.js
    ├── player/
    │   └── Player.js
    ├── systems/
    │   ├── AudioEngine.js
    │   ├── Ghost.js
    │   └── ScareDirector.js
    └── ui/
        └── HUD.js
```

Run with `npm install && npm run dev`.