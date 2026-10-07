# ARCHITECTURE.md  

**Project:** *Skylines‑II‑Clone* – a AAA‑level city‑builder built with **Three.js (r158‑latest)** + **Vite** using plain **ES‑modules**.  
**Root:** empty folder (git‑init, `package.json`, `vite.config.ts` already present).  

---  

## 1. High‑level Goals  

| Goal | Target |
|------|--------|
| Visual fidelity | Photographic PBR, physically‑based sky, sun, atmospheric scattering, night‑time illumination, realistic road & traffic shaders. |
| Performance | ≥ 50 fps @ 1080p (1920×1080) on a mid‑range GPU (RTX 3060 / Radeon 6700 XT). ≤ 1500 draw‑calls per frame (including UI). |
| Determinism | All gameplay‑logic (zoning, traffic, simulation) must be reproducible from a single **seeded RNG**. |
| Asset policy | **CC0 only** – Poly Haven, ambientCG, or procedurally generated (noise, shaders). No proprietary or “programmer art”. |
| Modularity | Each subsystem lives in its own folder, exports a **public API**, emits **typed events**, and is sandboxed so a crash in one cannot bring down the whole app. |
| Verification | Headless‑Chrome screenshot harness + per‑module “showcase” scenes. No code is merged without passing the **Gauntlet** (≥ 8.5/10, zero errors). |
| Continuous integration | `docs/STATUS.json` tracks scores, open issues, and the current iteration for each module. |

---  

## 2. Folder Layout (one folder = one subsystem)

```
src/
│
├─ core/                # tiny glue layer, event bus, RNG, logger, asset loader
│   ├─ World.js         # shared world data model (singleton)
│   ├─ EventBus.js
│   ├─ RNG.js
│   └─ AssetManager.js
│
├─ terrain/             # height‑map, ground textures, water, terrain LOD
│   ├─ index.js
│   └─ showcase.js
│
├─ environment/         # sky, sun, atmospheric scattering, weather, time‑of‑day
│   ├─ index.js
│   └─ showcase.js
│
├─ roads/               # road network graph, mesh generation, lane markings
│   ├─ index.js
│   └─ showcase.js
│
├─ zoning/              # residential/commercial/industrial zones, parceling
│   ├─ index.js
│   └─ showcase.js
│
├─ buildings/           # building generators, LOD, interior lights, night façade
│   ├─ index.js
│   └─ showcase.js
│
├─ props/               # street furniture, trees, lights, billboards
│   ├─ index.js
│   └─ showcase.js
│
├─ traffic/             # vehicle agents, path‑finding, traffic lights, AI
│   ├─ index.js
│   └─ showcase.js
│
├─ simulation/          # economy, population, utilities, demand curves
│   ├─ index.js
│   └─ showcase.js
│
├─ effects/             # particle systems (smoke, fire, dust), post‑process
│   ├─ index.js
│   └─ showcase.js
│
├─ audio/               # ambient city sounds, day/night mixes, UI SFX
│   ├─ index.js
│   └─ showcase.js
│
├─ ui/                  # HUD, menus, toolbars, inspector panels
│   ├─ index.js
│   └─ showcase.js
│
├─ tools/               # in‑editor utilities (road builder, zone painter, gizmos)
│   ├─ index.js
│   └─ showcase.js
│
├─ demo-city/           # scripted “demo” city that stitches all subsystems together
│   ├─ index.js
│   └─ showcase.js
│
└─ index.html            # entry point (loads core → demo‑city)
```

*All folders are **ES‑module** packages that export a **default class** (or factory) and a **static `API` descriptor** describing the public surface.*

---  

## 3. Shared World Data Model (`core/World.js`)

| Entity | Description | Key Fields |
|--------|-------------|------------|
| **Terrain** | Height‑field grid, material indices, water level | `heightMap: Float32Array`, `size: number (m)`, `resolution: number` |
| **Sky** | Sun position, atmospheric parameters, time of day | `time: number (0‑24h)`, `sunAzimuth`, `sunAltitude`, `weather: enum` |
| **RoadNetwork** | Graph of `Node`s and `Edge`s, lane data | `nodes: Map<id, Node>`, `edges: Map<id, Edge>` |
| **Zones** | Parcel polygons with type & density | `zones: Map<id, Zone>` |
| **Buildings** | Instances with transform, LOD state, occupancy | `instances: Map<id, BuildingInstance>` |
| **Props** | Static meshes (trees, lights, billboards) | `instances: Map<id, PropInstance>` |
| **Traffic** | Active vehicle agents, routes, speed | `vehicles: Map<id, Vehicle>` |
| **Simulation** | Global economy, population, utilities | `economy: EconomyState`, `population: PopulationState` |

*All coordinates are **metres**, **+Y up** (Three.js default).*  

The `World` object is a **singleton** imported by every subsystem. It holds **only data** – no rendering logic. All mutation must go through the **public API** of the owning subsystem (e.g., adding a road calls `Roads.addRoad(...)`).  

---  

## 4. Determinism & Randomness  

* **RNG** – `core/RNG.js` wraps `seedrandom` (or a tiny Xorshift128+ implementation).  
* The seed is supplied at app start (`window.__SKYLINE_SEED__` or URL param `?seed=…`).  
* Every subsystem that needs randomness receives a **local RNG instance** (`RNG.fork('roads')`, `RNG.fork('buildings')`, …) so that order of module initialization does not affect outcomes.  
* All simulation steps are **frame‑rate independent** (`deltaTime` passed to `update(dt)`), but the **order of updates** is fixed: `simulation → traffic → zoning → UI`.  

---  

## 5. Public API Contract (per module)

Each module exports:

```js
// src/<module>/index.js
export default class <ModuleName> {
  /** @type {World} */
  constructor(world, rng, eventBus) { … }

  /** Public API descriptor – consumed by integrator & other modules */
  static API = {
    // method name : { args: [...], returns: …, description: … }
    addRoad: { args: ['start:Vector3', 'end:Vector3', 'type:string'], returns: 'roadId:string' },
    // …
  };

  /** Event signatures emitted by this module */
  static EVENTS = {
    roadCreated: { roadId: 'string' },
    trafficJam: { roadId: 'string', severity: 'number' },
    // …
  };

  // lifecycle
  init()      // called once during app start
  update(dt)  // called each frame (if needed)
  dispose()   // clean up three.js objects, listeners
}
```

*The **integrator** reads `API` and `EVENTS` to wire modules together; no module may import another module’s internal classes directly.*  

### Example: `roads` API (excerpt)

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `addRoad(start, end, type)` | `Vector3`, `Vector3`, `'highway'|'street'|'alley'` | `roadId:string` | Creates a new road segment, updates the road graph, emits `roadCreated`. |
| `removeRoad(roadId)` | `string` | `boolean` | Deletes road and all attached lanes, emits `roadRemoved`. |
| `getRoad(roadId)` | `string` | `RoadData` | Read‑only snapshot of the road (for UI). |
| `setTrafficLight(roadId, state)` | `string`, `'red'|'yellow'|'green'` | `void` | Controls traffic‑light state, emits `trafficLightChanged`. |

All other modules follow the same pattern.

---  

## 6. Event Bus (`core/EventBus.js`)

* Simple **publish/subscribe** system based on `EventTarget`.  
* Events are **typed** (TS definitions in `src/types/events.d.ts`).  
* Each module registers listeners in its `init()` and removes them in `dispose()`.  
* The bus guarantees **asynchronous delivery** (`setTimeout(...,0)`) so a misbehaving listener cannot block the main loop.  

---  

## 7. Asset Policy  

| Category | Allowed Sources | Format | Notes |
|----------|----------------|--------|-------|
| Textures (albedo, normal, roughness, metal) | **Poly Haven**, **ambientCG** | `.exr`, `.hdr`, `.png`, `.jpg` | All textures must be **linear** (sRGB flagged). |
| 3D Models | Poly Haven (GLTF/GLB), procedural (e.g., `three-meshline`, `three-instanced-mesh`) | `.glb` (PBR‑ready) | No low‑poly “programmer art”. |
| HDRI / Sky | Poly Haven HDRIs (e.g., “Evening Sky”) | `.hdr` | Used for environment lighting only. |
| Audio | freesound.org (CC0) or generated via **Tone.js** | `.wav`, `.ogg` | Must be mono or stereo, 48 kHz. |
| Shaders | Custom GLSL, or **three‑examples** shaders (modified). | `.glsl` | Must respect PBR workflow (Metal‑Roughness). |

All assets are stored under `public/assets/` with a **manifest** (`assets/manifest.json`) that includes source URL, license hash, and a SHA‑256 checksum for integrity verification during CI.

---  

## 8. Performance Budget  

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Frame time** | ≤ 16 ms (≥ 60 fps) on reference hardware; ≥ 50 fps guaranteed on mid‑range GPU. |
| **Draw calls** | ≤ 1500 per frame (including UI). |
| **GPU memory** | ≤ 2 GB (textures ≤ 4 K, meshes instanced). |
| **CPU time (update)** | ≤ 4 ms per frame (simulation + traffic). |
| **Memory leaks** | No growth > 5 % after 5 min of idle simulation. |

The **integrator** runs a **performance monitor** (`core/PerfTracker.js`) that logs FPS, draw calls, and memory usage each frame to `dev/perf.log`. The headless‑Chrome harness asserts the budget before a module is accepted.

---  

## 9. Isolation & Failure Containment  

1. **Module sandbox** – each folder builds its own Three.js scene graph (`THREE.Group`) that is attached to a **root container** (`core/World.sceneRoot`). If a module throws during `update()`, the integrator catches the error, logs it, and **disables** that module for the remainder of the session (UI shows a warning).  
2. **Resource ownership** – every mesh, texture, or audio buffer is created via `AssetManager` which tracks a **reference count**. On `dispose()` the manager frees the GPU resources.  
3. **Error boundaries** – the main render loop wraps each subsystem’s `update()` in a `try/catch`. Errors are emitted as `systemError` events with module name and stack trace.  
4. **Hot‑reload safety** – Vite’s HMR only reloads the changed module; the integrator re‑instantiates the class while preserving the global `World` state (except for data owned by the reloaded module, which is cleared and rebuilt).  

---  

## 10. Verification Loop (pre‑game)

1. **Headless‑Chrome harness** (`tools/verify.js`)  
   * Launches Chrome via `puppeteer`.  
   * Loads `http://localhost:5173/` (Vite dev server).  
   * Waits for `window.__SKYLINE_READY__ === true`.  
   * Sets camera preset (top‑down, isometric, street‑level) and time of day (`World.time = …`).  
   * Takes a PNG screenshot (`screenshots/<module>/<preset>.png`).  
   * Extracts console logs, FPS, draw‑call count via `window.__SKYLINE_STATS__`.  
   * Writes `screenshots/<module>/log.json`.  

2. **Showcase mode** – each module exports `showcase(container: HTMLElement, options?)` that builds a minimal scene demonstrating its core features (e.g., `roads/showcase.js` creates a 2‑km grid with a few intersections). The harness loads `?showcase=roads` to trigger it.  

3. **No‑claim rule** – a module may only be advertised as “implemented” after its own showcase passes the screenshot check **and** the integrator has merged its API contract.  

---  

## 11. Integration Process (Integrator Role)

*Only the **integrator** may edit files in `src/core/` or any `index.js` that re‑exports a subsystem.*  

Steps after each builder wave:

1. Run `npm run lint && npm run typecheck`.  
2. Run the **verification harness** for every changed module.  
3. Merge the module’s `API` descriptor into `core/WorldAPI.ts` (central registry).  
4. Wire events: e.g., `Roads` emits `roadCreated`; `Traffic` subscribes to it to add lanes to its path‑finder.  
5. Resolve any **seam conflicts** (e.g., duplicate IDs, mismatched units).  
6. Commit a single atomic PR titled `integrate: <module‑list>`.  

All other agents (builders, critics) are **read‑only** to other folders.  

---  

## 12. Gauntlet (Critic) Process  

For each module after a builder round:

| Step | Action |
|------|--------|
| **Screenshots** | Critic runs the harness at 4 times of day (dawn, noon, dusk, night) and 3 zoom levels (city‑scale, street‑scale, vehicle‑scale). |
| **API contract check** | Runs a TypeScript validation script that imports the module’s `API` and ensures all required methods exist and signatures match. |
| **Console & perf audit** | Fails on any `console.error`/`console.warn` and on FPS < 50 fps or draw calls > 1500. |
| **Scoring** | Uses a simple image‑diff (SSIM) against a reference screenshot from Cities: Skylines II (provided by the project lead). Scores 0‑10. |
| **Pass threshold** | ≥ 8.5 **and** zero errors. |
| **Feedback** | Generates `docs/STATUS.json` entry: `{module: "roads", round: 2, score: 7.3, errors: [...], notes: "road mesh too low‑poly, shadows missing"}.` |
| **Iteration** | Builder receives the JSON, fixes issues, and repeats (max 4 rounds). |

---  

## 13. Final Gate  

1. Run the **demo‑city** showcase (full city generated from a deterministic seed).  
2. Critic scores the whole‑game screenshots (same 4 TOD + 3 zooms).  
3. Blind‑pair test: external judges view A/B pairs (our screenshot vs. official CS2) without labels, answer “which looks better” and why.  
4. If the average preference is **≥ 55 % for us** and the overall score ≥ 8.5, the build is considered **AAA‑ready**.  

---  

## 14. Documentation & Status Tracking  

* `docs/ARCHITECTURE.md` – this file.  
* `docs/STATUS.json` – array of module status objects (module, round, score, lastPass, openIssues). Updated automatically by the critic script (`tools/critic.js`).  
* `docs/ISSUES.md` – human‑readable list of all open tickets, grouped by module, with priority.  

---  

## 15. Assumptions & Routine Decisions (made now)

| Assumption | Rationale |
|------------|-----------|
| **Three.js r158** is the “latest release” at the time of scaffolding. | Guarantees support for WebGPU‑style features if needed later. |
| **Vite** will serve ES‑modules directly; no bundling for dev. | Keeps the dev server always loadable for screenshot agents. |
| **All coordinates in metres** – matches real‑world city planning tools. | Simplifies scaling of assets (e.g., road width 3 m). |
| **Seeded RNG** is the only source of randomness; no `Math.random` usage. | Ensures deterministic replay for debugging and testing. |
| **CC0 assets only** – we will download a starter pack from Poly Haven (textures, HDRI, some low‑poly props) and generate procedural meshes for roads/buildings. | Satisfies the “never programmer art” rule while staying legal. |
| **Performance budget** is generous enough for AAA‑level visuals but strict enough to force LOD/instancing. | Guides design decisions early (e.g., use `InstancedMesh` for trees). |
| **Module isolation** via separate scene groups and try/catch wrappers. | Prevents a single crash from taking down the whole app, meeting the “isolated failure” rule. |

---  

## 16. Next Immediate Action  

1. **Create folder skeleton** as described above (empty `index.js` + `showcase.js` placeholders).  
2. **Add core utilities** (`World.js`, `EventBus.js`, `RNG.js`, `AssetManager.js`).  
3. **Commit** the initial scaffold and `ARCHITECTURE.md`.  

The integrator will then run the first verification pass (which will pass trivially) and open the door for the first builder wave (Terrain).  

---  

*End of ARCHITECTURE.md*  

---  

**Ready for the integrator to scaffold the repo.**  