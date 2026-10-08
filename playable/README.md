# Playable reference artifacts

These are **agent-authored, hand-verified playable** HTML artifacts. They are
**not** model outputs and are **not** part of the benchmark corpus under
`results/`.

## Why this directory exists

The sweeps under `results/` record **raw model output** and are verified
honestly (see `results/*/rebuild_verdict_gpt_oss_120b.md` and the model
comparison table on issue #106). Every gpt-oss-120b single-file game failed to
boot into something playable, each on a single integration bug:

| artifact | failure |
|---|---|
| melon-jelly | `TypeError: Assignment to constant variable` (const reassigned in the seed loop) — crashed before first frame |
| lava-lamp | render loop runs (~60fps) but the shader output is byte-identical forever — frozen |
| minecraft | no `<canvas>` is ever created; the engine never initialises |
| sunset-ocean | animates and responds, but its core ShaderMaterial fails to compile |
| meridian-launch | ES-module graph (three from a CDN via importmap) fails to load |

Rather than dress up a boot-paint as "working" (the failure mode issue #97
exists to prevent), this directory holds a **from-scratch playable
implementation of the same game idea**, so there is at least one artifact that
is genuinely playable.

## melon-jelly.html

- Self-contained — no CDN, no build step. Open it directly in a browser.
- A soft-body (verlet) jelly you can **grab and wobble**; **Cut** mode slices
  it; **Reset** rebuilds; the colour picker changes the flesh colour. It has an
  idle wobble, so it is always visibly animating.
- **Verified playable** with the same frame-level harness used to grade the
  model artifacts:
  - content painted: canvas contrast sd ≈ 94, 20 distinct colour buckets,
    360/2048 sampled pixels opaque;
  - render loop live: 119 requestAnimationFrame ticks / 2 s;
  - sustained motion: frames differ across a 3.5 s window (6/7 consecutive
    frame pairs changed);
  - interaction: a click/drag changes the canvas (mean-abs-diff ≈ 3.35);
  - 0 console errors;
  - **label: PLAYABLE_VERIFIED**.
- Raw evidence: `melon-jelly.verify.json`.

## Provenance labels

- `results/**` — **model output**, unmodified. The benchmark record.
- `playable/**` — **agent-authored reference** (this directory). Not a model
  result; do not compare it against the model column.
