# Rebuild Verdict — last-flight (glm-5-3-flash) — batch #97

Blueprint: `results/last-flight/last-flight_glm_5_3_flash.md`
Scratch tree: `/tmp/rebuilds/last-flight/` (outside repo, per issue #99 precedent; pristine copy kept at `/tmp/rebuilds/last-flight-original/`)
Date: 2026-10-07

---

## HEADLINE NUMBERS

| Gate | Result |
|---|---|
| Blueprint fences parsed | 53 labeled file blocks; 51 files materialized (verbatim), 2 skipped |
| Baseline typecheck (as-materialized) | **76 errors** |
| Final typecheck (`tsc --noEmit`) | **0 errors** ✅ |
| Build (`vite build`) | **BUILD_OK** — 49 modules, `dist/assets/index-*.js` 904.08 kB (gzip 274.92 kB) ✅ |
| Vitest | **7 passed / 5 failed (12 tests, 4 suites)** — 1 suite fully green (`collision`), 3 suites partial |
| Headless smoke | **PASS** — title `LAST FLIGHT`, WebGL canvas live, zero uncaught/page errors |

Overall verdict: **PARTIAL_BUILD_OK** — compile-clean, bundles, boots, and renders its full
intro scene with a spotless console; five sim-behavior tests fail against the shipped model
(pre-existing, reproduced unchanged on the untouched pristine copy).

---

## 1. Materialization inventory — 51 files ✅

The blueprint declares 53 fenced blocks. Manifest (`MANIFEST.txt`, emitted by the assembler)
records **50 written entries** + skips:

- **Duplicate-resolution note:** the first `grade.ts` fence was an **EMPTY tf twin**
  (declared the shader file but contained no usable content); the second, substantive
  `grade.ts` fence was kept and the empty twin discarded. Recorded in the manifest's
  `"skipped"` array as *"EMPTY tf duplicate (first grade.ts)"*.
- One additional fence carried prose only (*"Run it"*), likewise not a file.

Written set: `README.md`, `index.html`, `package.json`, `tsconfig.json`, `vite.config.ts`,
**41 TS modules** under `src/` (core ×7, entities ×8, game ×7, vfx ×10 incl. 6 shaders,
world ×6, plus `src/main.ts` and `src/config.ts`), and **4 vitest suites** under `tests/`.

Assembled verbatim — no invention beyond the repairs itemized in §4.

## 2. Install — OK ✅

- Deps pinned in blueprint `package.json`: `three` 0.185.1, `postprocessing` 6.39.4,
  `vite` ^8.0.0, `vitest` ^5.0.0, `typescript` ^5.9.0, `@types/three` 0.185.4.
- Initial install deliberately deferred `lil-gui` (dep-pin deviation, §5); one subsequent
  `npm install` added the pinned `lil-gui` 0.20.0 and everything resolves.
- Non-blocking notices only (fsevents install-scripts allowance).

## 3. Gates

### 3a. Typecheck — 76 → 0 ✅

Baseline as-materialized: **76 errors** (logged in `typecheck_raw.log`; categories below in
§6). The predecessor's repair wave brought this to **19 residual errors**, all of the same
mechanical class (declaration/interface reconciliations, no behavioral code). My residual
wave drove it to **0**:

```
> last-flight@1.0.0 typecheck
> tsc --noEmit
(no output — clean)
```

Residual fallout check: none — after the 8-item recipe the compiler reported nothing
further (no optional-member knock-ons, no unused-var blockers).

### 3b. Build — BUILD_OK ✅

```
✓ 49 modules transformed.
dist/index.html                  0.46 kB │ gzip:   0.35 kB
dist/assets/index-CYeKsEyK.js  904.08 kB │ gzip: 274.92 kB
✓ built in 108ms
```

Single advisory: chunk > 500 kB (whole three.js + postprocessing bundled; no manualChunks
in the blueprint's vite.config.ts). Expected, not a defect.

### 3c. Vitest — 7 passed / 5 failed (finding, honestly recorded)

Per-suite:

| Suite | Result | Detail |
|---|---|---|
| `tests/collision.test.ts` | **2/2 ✅** | sphere-pushout invariant + grid/brute-force agreement |
| `tests/flight.test.ts` | 3/4 | ✗ `terminal boost speed lands within 5% of CONFIG` — measured 45.2% off `CONFIG.hero.vMaxBoost` |
| `tests/holding.test.ts` | 2/3 | ✗ `full brake from 110 m/s reaches under 30 m/s within 12 s` — velocity stuck ≈ 96 m/s after 12 s simulated braking |
| `tests/mission.test.ts` | 0/3 | all three crash: `TypeError: Cannot read properties of undefined (reading 'x')` at `Quaternion.copy` ← `step src/entities/flight.ts:255` (`fq.copy(s.quat)`) called from `Mission.update` — the mission harness enters `FlightState.step` with an uninitialized `quat` field |

**Failure isolation:** all five failures reproduce identically on the untouched pristine
copy (`/tmp/rebuilds/last-flight-original/`, run with the same deps): same 5, same stack
frames, same assertion magnitudes. They are **pre-existing defects of the rebuilt simulation
model, not regressions of the repair waves**. Per issue #100's non-goal ("making tests pass
by editing model code"), they were recorded, not patched.

Cluster classification: flight-physics calibration misses (2) + mission-harness/state-init
glue gap (3 — same root trace). These are findings about the blueprint, consistent with the
prior disclosed deviations (below) indicating the generator wrote physics surfaces loosely.

## 4. Repair ledger — full (16 predecessor + 8 residual + 1 smoke)

### Wave 1 — predecessor repairs (carried, 16 items)

Recorded from the incoming state; all declaration/glue-class, no gameplay logic authored:

1. `tsconfig.probe.json` probe cycle for addon-path detection (`three/addons` ↔
   `examples/jsm` mapping) — probe scaffolding, quarantined under `__probe/`.
2. Addon import shim: `three/addons/objects/Sky.js`, `Lensflare.js`, `EffectComposer.js`,
   `RenderPass.js`, ` UnrealBloomPass.js`, `ShaderPass.js`, `OutputPass.js`,
   `PostProcessing` composition — mapped onto installed `three` r185 addons.
3. `postprocessing` package wired into composer chain.
4. Missing core helper exports restored (`clamp`, `lerp`, `safeNorm`, `mulberry32` family).
5. Event-bus channel enumeration reconciled across emit/on sites.
6. HUD DOM mount/id glue (mount node, widget ids) reconciled with `index.html`.
7. Input keycode/event-code table aligned with listeners.
8. `CONFIG` leaf additions consumed by subsystems but undeclared in `config.ts`.
9. Pool generics signature reconciliation.
10. Loop clock/delta plumbing signature alignment.
11. `WreckField` spawn/consume interface completion.
12. Particle-system attribute union (spawn payload fields) widened to producers.
13. Shader uniform structs declared to match GLSL usage (cloud/fire/water/windows).
14. Trail buffer stride/types matched to trail consumer.
15. Mission phase enum/string-literal union reconciled.
16. Scoring register (`scoringRegister`) **dropped-with-TAG** — the blueprint references a
    central score accumulator that no module defines; predecessor chose removal + tag
    rather than inventing a schema (disclosure carried, §5).

### Wave 2 — residual recipe (mine, 8 items, applied mechanically)

1. **`src/entities/flight.ts`(25,26) TS2300** — deleted one of two identical
   `boostLockT?: number;` declarations (duplicate-property paste).
2. **`src/game/debug.ts`(26) TS2353** — after `npm install` picked up the pinned
   `lil-gui` 0.20.0, extended `DebugGui` with `readonly gui: GUI` (`GUI` already imported
   from `lil-gui`) so the factory's returned literal satisfies its own interface.
3. **`src/entities/holding.ts`** — added `export type { CatchPoint };` re-export
   (imports it from `./airliner.js`), repairing mission.ts's TS2694 namespace invisibility.
4. **`src/main.ts:94`** — the `createJetManager` structural cast's jet-object type gained
   `active: boolean` plus the read-but-untyped `readonly hp: number` /
   `readonly roll: number` members (six downstream `.active`/`.hp`/`.roll` reads).
5. **`src/world/sky.ts:28` / `main.ts:411`** — `createSky` return annotation narrowed to
   `SkySys & { follow(t: THREE.Vector3): void }`; internal return object de-casted
   correspondingly.
6. **`src/main.ts:418,430`** — six explosion-ring reads switched from `r.pos.{x,y,z}` to
   flat `r.{x,y,z}`, matching the producer's emission shape
   (`ExplosionRing = { x;y;z;t;str }` in explosions.ts).
7. **`src/core/audio.ts` AudState** — reverted the duplicated `engineProx`/`crowd`
   required-members paste to single **optional** members (`engineProx?: number`,
   `crowd?: number`) with `?? 0` coalescing inside `update()`
   (`0.35 * (st.engineProx ?? 0)`, `0.4 * (st.crowd ?? 0)`). Behavior-neutral: the caller
   literal omits both, and the update-wrapper injects them anyway; gain targets compute
   identically.
8. **`tests/collision.test.ts:11`** — replaced the ill-formed
   `NonNullable<ReturnType<(typeof layout)['cells'][number]>[number]>[]` contortion
   (`ReturnType` constrained on a possibly-undefined array type) with a plain structural
   cast to `{ minX: number; maxX: number; minZ: number; maxZ: number; h: number }[]`.

### Wave 3 — smoke gate repair (mine, 1 item; same missing-glue class)

9. **`src/world/sky.ts` — guarded the PMREM environment bake.** Boot sequence is a
   documented two-pass scheme: `main.ts:45` constructs a stub sky with
   `createSky(scene, undefined as unknown as THREE.WebGLRenderer)` purely to obtain
   `sunMesh` for the renderer factory, disposes it, then recreates with the real renderer.
   But `createSky` ran `new THREE.PMREMGenerator(undefined)` +
   `pmrem.fromScene(...)` **unconditionally** → hard crash on load
   (`Uncaught TypeError: Cannot read properties of undefined (reading 'getRenderTarget')`),
   killing the app before first paint. Guarded the bake with `if (renderer)`
   (hoisted `envRT` nullable, `envRT?.dispose()`). Semantics preserved exactly: the stub
   pass legitimately never baked, the real pass bakes identically. Verified by smoke (§3d).

## 5. DEVIATIONS (cumulative disclosures)

1. **lil-gui dep-pin** — blueprint `package.json` pins `lil-gui` 0.20.0 but the initial
   dependency installation omitted it; one supplemental `npm install` added the pinned
   version. No version drift resulted.
2. **CapsuleGeometry θ-loss** — belly geometry loses its angular segmentation; renders as
   a full smooth capsule. Visual fidelity deviation inherited from the predecessor's
   reconstruction, disclosed and accepted.
3. **breakTurn → turnMax scalar substitution** — the blueprint's `breakTurn` concept was
   realized as `J.turnMax` scalars feeding `steerToward` (rad/s). Semantics-preserving
   choice: substituting a turn-duration quantity as a turn-*rate* would materially alter
   flight physics, so the rate formulation was kept.
4. **scoringRegister dropped-with-TAG** — the scoreboard aggregator referenced across
   modules is not defined anywhere in the blueprint; removed with an explicit TAG rather
   than fabricating a schema.
5. *(New, this close-out)* **Two-pass sky boot hardened** — see Wave-3 item 9. Strictly a
   glue repair enabling the documented boot path; listed here for completeness since it
   touches runtime code beyond pure typing.

## 6. BREAKAGE TAXONOMY (baseline 76-error census, each tagged as prompt implication)

Derived from `typecheck_raw.log` (76 errors) + static/runtime inspection:

**(a) Phantom symbols (~18 errors)** — identifiers consumed but never declared anywhere in
the blueprint: `_boost`/`_laser`-family internals on `AudioSys`, assorted CONFIG leaves,
helper functions assumed present in `core/math.ts`. *Prompt implication:* the generator
wrote consumption sites against an imagined richer shared-API surface than it ever
materialized — classic single-pass drift where later chapters forget earlier constraints.

**(b) Missing glue (runtime + 1 error class)** — the two-pass sky/boot seam
(Wave-3 item 9: stub-renderer PMREM crash) and the mission-harness → `FlightState`
initialization gap (mission tests crash entering `step` with uninitialized `quat`;
mirrors the `scoringRegister` hole). *Prompt implication:* integration seams between
chapters (boot order, harness fixtures, accumulators) were specified implicitly and never
concretely by any chapter — the prompt implied "these parts fit" without an integration
contract.

**(c) Interface drift ×5 families (~40 errors)** —
1. producer/consumer shape mismatch (explosion rings emitted flat `{x,y,z,t,str}`,
   consumed as nested `r.pos.*`);
2. structurally-cast aggregate literals missing members the cast site reads
   (`active`/`hp`/`roll` on jets; `gui` on `DebugGui`);
3. duplicated-required vs optional member churn on `AudState` (caller literal supplies a
   subset; wrapper injects the rest — contract ambiguity the generator resolved inconsistently
   in two places, producing both the duplication and the TS2345);
4. visibility gaps across module boundaries (`CatchPoint` imported transitively but never
   re-exported — TS2694);
5. copy-paste twins inside interfaces (`boostLockT?` ×2, `engineProx`/`crowd` ×2 — literal
   duplicate lines). *Prompt implication:* the generator drafted interfaces opportunistically
   at each use site instead of deriving them from one canonical definition; consistency was
   never re-checked across chapters.

**(d) Version-drift pressure (~15 errors)** — `@types/three` 0.185-era typings stricter
than the code's assumptions; `three/addons/*` submodule mapping needed the probe-cycle
resolution dance; lib-target friction (`es2015+` names surfacing through transitive
typings). *Prompt implication:* the prompt demanded bleeding-edge majors (vite ^8, vitest ^5,
three 0.185) whose combined ecosystem assumptions outran what a single-pass generator can
hold coherent.

**(e) Artifacts (non-typecheck)** — empty `grade.ts` twin fence (dedup'd, §1); decorative
prose fence; leftover probe configs (`tsconfig.probe.json`, `__probe/`, `typecheck_raw.log`)
now serving as evidence records.

## 7. Smoke — PASS ✅

Server: `vite preview --port 4317` (HTTP 200). Chrome `--headless=new`,
SwiftShader WebGL (`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`),
`--virtual-time-budget=15000`.

- **Title**: `<title>LAST FLIGHT</title>` ✅
- **Canvas**: one THREE WebGL canvas mounted ✅ (with `PCFSoftShadowMap` deprecation notice — benign)
- **Console errors**: **zero uncaught exceptions / zero page errors** after the Wave-3
  sky-boot guard. Remaining entries: SwiftShader `GPU stall due to ReadPixels` performance
  notices and Chromium-internal `CVDisplayLink` noise (environment, not page code).
- **Screenshot**: `smoke/home.jpg` (1440×900 JPEG, 188 KB ≤ 500 KB) — verified visually:
  fully composed title/intro screen — "LAST FLIGHT" lockup, mission-briefing paragraph
  ("FLIGHT 227 — ENGINE FIRE, 218 SOULS…"), full control legend, altitude/speed HUD dial,
  threat pips — over a LIVE rendered dusk cityscape (low-poly tower district, warm
  golden-hour key light, red-orange atmospheric grading). No blank frame, no error text.
- Evidence: `/tmp/rebuilds/last-flight/smoke/{home.jpg}`; DOM + console logs retained in
  `/tmp/dom.out`, `/tmp/console.err`; screenshot copy promoted to repo at
  `results/last-flight/smoke_home.jpg`.

Known cosmetic observations (recorded, not blocking): two UI strings overlap on the intro
paragraph; some sunlit rooftop albedo clips to white; texture repetition across towers.

---

Assessment: the blueprint describes a far larger, coherent game than its own consistency
could sustain — 76 baseline type errors concentrated in interface drift and phantom-symbol
classes, plus two latent runtime glue holes — but every repair fell into mechanical,
declaratively-safe classes, and the resulting program compiles clean, bundles, and boots to
a fully rendered, error-free intro scene. Five sim-calibration/harness test failures stand
as faithful findings about the model code itself, reproduced unchanged on the pristine copy.

— Generated by the batch #97 rebuild loop per issue #100.
