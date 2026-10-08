# Playable reference artifacts

Agent-authored, hand-verified **playable** HTML artifacts. They are **not**
model outputs and are **not** part of the benchmark corpus under `results/`.

## Why these exist

The sweeps under `results/` record RAW model output and are graded honestly
(see `results/*/rebuild_verdict_gpt_oss_120b.md` and the flash-vs-frontier
table on #106). Every gpt-oss-120b single-file game failed at the raised
playability bar — each on a single runtime-only bug (a `const` reassignment,
a non-compiling shader, a frozen/NaN render loop, a canvas that is never
created, a module graph that never loads). This directory holds clean,
self-contained implementations of the same ideas so that at least one
artifact per prompt is genuinely playable.

Open any file directly in a browser — no build, no CDN, no server.

| file | what it is | how to play |
|---|---|---|
| `melon-jelly.html` | soft-body verlet jelly | drag to grab/wobble · Cut mode slices · Reset rebuilds · colour swatch |
| `lava-lamp.html` | metaball lava lamp | drag a blob to stir · click empty space (or the button) to re-mix the palette · heat slider · tint |
| `sunset-ocean.html` | animated ocean at sunset | move the mouse to raise/lower wind · click the water for ripples · "next phase" jumps time of day |
| `minecraft.html` | isometric voxel world | click a tile to build · Mine mode removes · WASD or drag to pan · "new world" regenerates |
| `meridian-launch.html` | rocket launch mini-game | hold mouse/space to thrust · reach 100 km before fuel runs out · R resets |

## Verification

Each file was graded with the same frame-level harness used on the model
outputs (`verify_playable.mjs`): content actually painted, `requestAnimationFrame`
running, sustained pixel motion over a 3.5 s window, click-through changes the
canvas, and zero console errors. All five:

```
melon-jelly      label=PLAYABLE_VERIFIED  paint=PAINTED  trans=True  motion=True  errs=0
lava-lamp        label=PLAYABLE_VERIFIED  paint=PAINTED  trans=True  motion=True  errs=0
sunset-ocean     label=PLAYABLE_VERIFIED  paint=PAINTED  trans=True  motion=True  errs=0
minecraft        label=PLAYABLE_VERIFIED  paint=PAINTED  trans=True  motion=True  errs=0
meridian-launch  label=PLAYABLE_VERIFIED  paint=PAINTED  trans=True  motion=True  errs=0
```

Per-file evidence: `<name>.verify.json`.

## Provenance

- `results/` = raw model output, unmodified. Nothing there is edited or
  presented as playable.
- `playable/` = agent-authored reference (this directory). Not a model result.
