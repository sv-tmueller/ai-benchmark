# Rebuild Verdict — horror-house (glm-5-3-flash) — batch #97

Blueprint: `results/horror-house/horror-house_glm_5_3_flash.md`
Scratch tree: `/tmp/rebuilds/horror-house/` (outside repo, per issue #99)
Date: 2026-10-07

## 1. Materialization inventory — 13/13 ✅

Parsed the markdown: **14 fenced code blocks were found, 13 bold file labels declared**
(`**package.json**`, `**vite.config.js**`, `**SYSTEM_PROMPT.md**`, `**index.html**`,
`**src/main.js**`, `**src/ui/HUD.js**`, `**src/world/Textures.js**`, `**src/world/House.js**`,
`**src/player/Player.js**`, `**src/systems/AudioEngine.js**`, `**src/systems/Ghost.js**`,
`**src/systems/ScareDirector.js**`, `**src/Game.js**`).

Itemized parse mismatches:

- Fence 14 (markdown lines 4224–4244, unlabeled, no info-string) sits AFTER the
  `**src/Game.js**` section and is a decorative ASCII **project-tree diagram** ending in
  “Run with `npm install && npm run dev`.” — not a file. Correctly excluded; no content lost.
- Label `**src/Game.js**` therefore technically precedes TWO fences (its own file at line 3737
  and the tree diagram) — counted as one duplicate-label adjacency, resolved by inspection.
- No unlabeled FILE fences, no missing labels, no contradictory labels.

All 13 files written byte-for-byte from their fenced blocks (only assembly normalization:
trailing closing-fence markers removed from extracted slices):

| File | Bytes |
|---|---|
| package.json | 280 |
| vite.config.js | 187 |
| SYSTEM_PROMPT.md | 333 |
| index.html | 11,529 |
| src/main.js | 454 |
| src/ui/HUD.js | 4,936 |
| src/world/Textures.js | 27,708 |
| src/world/House.js | 48,291 |
| src/player/Player.js | 7,684 |
| src/systems/AudioEngine.js | 26,244 |
| src/systems/Ghost.js | 17,414 |
| src/systems/ScareDirector.js | 6,712 |
| src/Game.js | 18,246 |

## 2. Install + build — BUILD_OK ✅

- `npm install`: success. Resolved `three` (^0.161.0 → r161) and `vite` ^5.2.0 (→ 5.4.21).
  Non-blocking warnings only (audit advisories; esbuild post-install-script allowance notice).
- `npm run build` (vite build): **success** —

  ```
  ✓ 23 modules transformed.
  dist/index.html                 11.57 kB │ gzip:   3.87 kB
  dist/assets/index-BOLbdH8L.js  591.01 kB │ gzip: 153.39 kB
  ✓ built in 402ms
  ```

  Single advisory warning: chunk > 500 kB (expected — three.js bundled whole; blueprint’s
  vite.config.js sets no manualChunks). Not a defect.

## 3. Headless smoke — PASS ✅

Server: `vite preview --port 4173` (HTTP 200). Chrome `--headless=new`,
SwiftShader WebGL, `--virtual-time-budget=10000`.

- **DOM**: `<title>BRIDGE HORROR HOUSE</title>` present ✅; THREE.WebGL canvas mounted:
  `<canvas data-engine="three.js r161" width="756" height="469">` ✅; grain-canvas +
  full HUD skeleton intact.
- **Console**: zero page-JavaScript errors, zero uncaught exceptions, zero `[BHH]` handler
  firings. Only benign entries: SwiftShader `GPU stall due to ReadPixels` performance notices
  and Chromium-internal `CVDisplayLink` noise (environment, not page code).
- **Screenshot**: `home.png` (1280×800, 181 KB) — verified visually: fully styled title
  screen (“BRIDGE / horror house” lockup, controls grid, objective tracker, battery HUD),
  with a LIVE 3D interior rendering behind it (perspective floor/walls, lamp glow, dust
  motes). No blank frame, no error text, no unstyled HTML.
- Evidence copied to repo: `results/horror-house/smoke_home.png`; full-res originals remain
  in `/tmp/rebuilds/horror-house/smoke/` ({dom.html, console.log, home.png}).

## 4. Mechanical fixes made (assembly-only, itemized)

1. Removed the markdown parser’s trailing ``` residue appended to each extracted file slice
   (13 files) — artifact of MY slicing, not of the blueprint.
2. Nothing else. No code edited, no imports rewritten, no config patched.

Cross-checks performed (all clean, no fixes needed):
- Static import-graph walk: every intra-project specifier resolves to a materialized file;
  `three` + `three/addons/postprocessing/*` resolve into the installed package; `vite` import
  confined to vite.config.js.
- DOM-id coupling: every `getElementById('#…')` target used by src/**.js exists in
  index.html; every `classList.toggle(...)` hook has a matching CSS rule.

## 5. Breakage taxonomy

**Result: EMPTY.** No missing glue, no phantom imports, no contradictions between blueprint
files were found. Specifics checked:

- Glue wiring: index.html loads `/src/main.js` as module; main.js boots `Game`;
  Game composes Tex/House/Player/AudioEngine/Ghost/ScareDirector/HUD — chain complete.
- Phantom imports: none (every import resolved statically AND the production bundle built
  with Rollup full resolution — 23 modules, no unresolved-specifier errors).
- Cross-file contradictions: none detected — DOM ids, CSS classes, event codes, and the
  three-keys/win/burn contracts agree across Game/HUD/House/ScareDirector.
- Runtime: boot reached PLAYING-state render loop headlessly (r161 canvas alive, animated
  scene composited behind the title overlay) with a spotless console.

Assessment: this blueprint is unusually self-consistent for a single-pass generated project.
Nothing observed contradicts the hypothesis that the generation prompt supplied a complete
integration contract (shared constants/IDs enumerated up-front). No negative prompt
implications to feed back from this sample.

— Generated by the batch #97 rebuild loop per issue #99.
