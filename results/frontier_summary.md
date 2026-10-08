# Frontier baseline sweep — capability summary

**Model:** `vllm/release/gpt-oss-120b` · **Tier:** game/app (10 prompts = 9 games + `app-stillwater`)
**Compared against:** `glm-5.3-flash` (see #37, #97)
**Batches:** #112 (this sweep) · collaborative model assessments: #178

## Method

- One prompt TOML per test; **only the model id changes**.
- **One shot per prompt — no execution feedback.** The model never sees its own
  output run. This is the single most important property of the setup.
- Verification: headless-Chrome CDP harness — 10s console capture, click-through
  transition, ≥3s pixel-motion sampling, per-script brace/paren balance. Labels:
  PLAYABLE_VERIFIED / BOOTS_ONLY / BROKEN_AT_BOOT / SCRIPT_TRUNCATED. The harness
  was calibrated against the #97 human audit (reproduces every known flash
  verdict) before use.

## Results

| prompt | deliverable | glm-5.3-flash | gpt-oss-120b | truncation |
|---|---|---|---|---|
| melon-jelly | html | PLAYABLE_VERIFIED | BROKEN_AT_BOOT | — |
| lava-lamp | html | BROKEN_AT_BOOT | BOOTS_ONLY | — |
| mario-kart | blueprint | BOOTS_ONLY | BLUEPRINT_INCOMPLETE | — |
| minecraft | html | BOOTS_ONLY | BOOTS_ONLY | — |
| sunset-ocean | html | BOOTS_ONLY | BOOTS_ONLY | — |
| cities-skylines | blueprint | BOOTS_ONLY | BLUEPRINT_ONLY | flash: cut |
| horror-house | blueprint | BUILD_OK + PASS | BUILD_OK, RUNTIME_DEAD | — |
| last-flight | blueprint | BUILD_OK + PASS | BUILD_OK, RUNTIME_DEAD | — |
| meridian-launch | html | BROKEN_AT_BOOT | BROKEN_AT_BOOT | flash: cut |
| app-stillwater | blueprint | BLUEPRINT_ONLY | BLUEPRINT_ONLY | — |

## Findings

1. **Completeness vs correctness.** gpt-oss-120b completed 10/10 prompts on the
   first attempt with **zero truncation**; glm-5.3-flash truncated 2/10. The
   frontier model is more reliable at *finishing*.
2. **Neither arm produced a broadly playable set.** flash 1/5 single-file
   playable; gpt-oss-120b 0/5. Both scored 0 on the blueprint tier that requires
   a runtime.
3. **The failures are last-mile, not logic.** Every dead artifact died on one
   integration slip that a compiler or a 5-second runtime check catches:
   a `const` reassignment, a missing `import * as THREE`, a shader that will not
   compile, a canvas never created, a module graph that never loads.
4. **Blueprints build green and die at runtime.** horror-house and last-flight
   both `vite build` cleanly then throw `THREE is not defined` — namespace use
   against named imports.

## Verdict

The result is **not** "this model cannot code", and **not** "these models are too
small". It is: *one-shot generation of large, run-unverifiable code exceeds what
any model tested can do reliably — including the frontier one.* A single wrong
character is fatal when the model can never run its own output.

Evidence the model **can** code: 10/10 clean finishes; its melon-jelly was ~99%
correct (one two-word bug); its blueprints were structurally valid 12- and
36-file projects. It cannot **self-verify** — which is a property of the
harness, not the weights.

## Owner's hypothesis — evaluated

> *Flash models trade technical depth for speed; all models lack parameters and
> reasoning depth versus Claude / ChatGPT frontier models.*

- **"Not enough parameters" — NOT SUPPORTED.** Parameter count was never varied.
  gpt-oss-120b *is* a large model, and it finished cleanly 10/10. The failures
  are architectural (a missing import, an undeclared variable), not capacity.
- **"Traded depth for speed" — DOMAIN-SPECIFIC, not uniform.** flash handled GLSL
  where the non-flash model did not, and vice-versa. It is not a single dial.
- **"Weaker reasoning than frontier" — PLAUSIBLE BUT UNPROVEN HERE.** This
  endpoint reported `reasoning_tokens: null`, so the model may have run in a
  non-thinking mode. Do not read a reasoning verdict out of this data.
- **The dominant variable is the loop, not the model.** The biggest confound in
  any cross-model comparison is whether one arm had a run-observe-fix loop and
  the other did not. Same prompt, same harness, same retry budget — otherwise you
  are measuring the scaffold.

## Implication for the ServiceNow story → update-set workflow

This is the opposite of the game tier on every axis that mattered: deterministic
and schema-checked records, a cheap authoritative oracle (deploy to a PDI and
read the error), and modular components (20–200 line rules/scripts) rather than
monolithic files. **Use these models for the volume, never one-shot into prod.**
The PDI feedback loop is what turns the model's "propose" into a working update
set; the human keeps scope, permissions and ACLs.

## Data & provenance

- `results/*/*_gpt_oss_120b.meta.json` — raw output + playability block.
- Comparison table + correction: #106.
- Cross-model assessments: **#178** (add yours there).
- `playable/*.html` — five **agent-authored** playable references (not model
  output; see `playable/README.md`).

