# AI Benchmark — Prompt Corpus & Artifacts

A small corpus of one-shot benchmark prompts and the model outputs they
produce. Every prompt delivers **exactly one file** that can be reviewed
directly: an `.html` page that opens in a browser, or, for the ServiceNow
prompt, an `.xml` update set that imports into an instance.

Two things live here:

- **`prompts/`** — 15 TOML prompt definitions: eleven games and 3D scenes,
  one app, one creative-writing task, one reasoning task and one ServiceNow
  build task.
- **`results/`** — the collected outputs, one folder per prompt, each
  deliverable next to a `.meta.json` sidecar.

The corpus was reworked in #285. Earlier prompt versions (markdown
blueprints for multi-file projects, plus text, math, SQL, vision and probe
prompts) and every result generated from them were removed; they remain in
the git history.

---

## Prompts

One TOML file per prompt. Core fields: `id` (equal to the file stem),
`title`, `category`, `difficulty`, `temperature`, `max_tokens`, `save_as`
(the deliverable's extension), `file_prefix` (the result file and folder
name) and a `[system]`/`[user]` text pair.

### Games and scenes

| Prompt | Deliverable | Runtime needs |
|---|---|---|
| `game-melon-jelly.toml` | HTML: soft-body watermelon slice to squish and cut | None — fully offline |
| `game-lava-lamp.toml` | HTML: ray-marched lava lamp studio shot | None — fully offline |
| `game-minecraft.toml` | HTML: voxel world with mining, crafting and mobs | Internet — Three.js + JSZip from a CDN; optional resource pack |
| `game-meridian-launch.toml` | HTML: scripted rocket launch scene | Internet — Three.js from a CDN |
| `game-sunset-ocean.toml` | HTML: open ocean at sunset | Internet — Three.js from a CDN |
| `game-horror-house.toml` | HTML: first-person haunted-house escape | Internet — Three.js from a CDN |
| `game-last-flight.toml` | HTML: superhero flight and airliner rescue, with a `?selftest` mode | Internet — Three.js + postprocessing from a CDN |
| `game-cities-skylines.toml` | HTML: city builder with a living demo city | Internet — Three.js from a CDN |
| `game-mario-kart.toml` | HTML: kart racer | Internet — Three.js from a CDN |
| `game-weichensteller.toml` | HTML: model-railway junction game | Internet — Three.js from a CDN |
| `game-rubiks-cube.toml` | HTML: 3D Rubik's cube to scramble and solve by hand | Internet — Three.js from a CDN |

### App

| Prompt | Deliverable | Runtime needs |
|---|---|---|
| `app-stillwater.toml` | HTML: voice-first AI companion that remembers sessions, browser-only | A Chromium-based browser and a microphone (text fallback otherwise); the page loads nothing itself, but Chrome's speech recognition and network voices need to be online |

### Text tasks

| Prompt | Deliverable | Runtime needs |
|---|---|---|
| `creative-water-bottle.toml` | HTML page with a 120–150 word product description in `#description` | None |
| `reasoning-seating-puzzle.toml` | HTML page with the step-by-step reasoning and the seating in `#answer` | None |

### ServiceNow

| Prompt | Deliverable | Runtime needs |
|---|---|---|
| `servicenow-loaner-request.toml` | XML: one update set that builds the Equipment Loan Desk (table, business rule, client scripts, scheduled job and notification, roles and ACLs, form and list) | A ServiceNow Personal Developer Instance: Retrieved Update Sets → Import Update Set from XML → preview → commit |

### Using a prompt with `@prompts/<file>.toml`

Reference any prompt file directly, e.g. `@prompts/game-melon-jelly.toml`;
the `[system]`/`[user]` texts are plain prose and need no preprocessing.

## Results

Outputs are grouped under `results/<file_prefix>/`, one folder per prompt:

```
results/<file_prefix>/<file_prefix>_<model_tag>.<save_as>      the deliverable
results/<file_prefix>/<file_prefix>_<model_tag>.meta.json      the sidecar
```

The model tag is the model id in lower case with every run of
non-alphanumerics replaced by `_` (`claude-fable-5-2` → `claude_fable_5_2`).
The sidecar records the prompt, the model, how the result was generated and
which sampling settings applied.

## One-shot arm

Every prompt is run as a plain one-shot: one fresh session per prompt, one
pass, one file, no orchestrator, no agents and no repair round. The table
below is the ledger for Claude Fable 5.2.

**How to run.** Start the whole arm with `/bench-run` and no arguments from a
clean checkout of `main`. The skill calls
[`harness/bench_run_all.py`](harness/bench_run_all.py), which starts one fresh
headless Claude Code session per prompt (`claude -p "/bench-run <prompt-id>"`)
with the calling session's exact model id and effort level, a narrow tool
allowlist and no merge rights, so each prompt is still one isolated one-shot.
`/bench-run --dry-run` prints the checks, which prompts would run or be
skipped, and the exact child command, and starts nothing. A prompt that
already has a result on `origin/main` or in an open PR is skipped, so
re-typing `/bench-run` after an interruption resumes the arm, and after CI
turns green it skips all 15 and reaches the final merge step again (the
helper runs `harness/merge_results.py` when that file exists, otherwise it
lists the open PRs). A single prompt still runs with `/bench-run <prompt-id>`,
for example `/bench-run game-melon-jelly`. The prompt TOML under `prompts/` is
used unmodified. Each sidecar's `reasoning_effort` records the session's
`CLAUDE_EFFORT` level.

**In-session generation caveats.** The generation happens inside a Claude
Code session, so:

- `temperature` and `max_tokens` from the TOML cannot be set; the session
  defaults apply.
- `finish_reason` and token `usage` are not observable. The sidecar records
  them as `null` with a note.
- There is no length-retry ladder: the first complete output is the result.

**Verification split.** Generation runs on the small dev box. Reviewing the
results is a separate step: HTML results are opened in a browser on a
stronger machine, and the ServiceNow update set is imported into a Personal
Developer Instance.

**Verification bar.** Per HTML game or app: a click-through transition,
sustained animation (pixel motion sampled over at least 3 s), per-script
brace/paren balance, and console capture across 10 s. The result is labelled
`PLAYABLE_VERIFIED`, `BOOTS_ONLY` or `BROKEN_AT_BOOT` (see
[Playability labels](#playability-labels)) in its sidecar, in a commit of its
own. A result has no playability verdict until this check has run; generation
alone does not earn one.

**Status.** A row moves from `not run` to `generated, review pending`
when its result and sidecar are on `main`.

| Prompt | Deliverable | Target path | Status |
|---|---|---|---|
| `game-melon-jelly` | HTML | `results/melon-jelly/melon-jelly_claude_fable_5_2.html` | not run |
| `game-lava-lamp` | HTML | `results/lava-lamp/lava-lamp_claude_fable_5_2.html` | not run |
| `game-minecraft` | HTML | `results/minecraft/minecraft_claude_fable_5_2.html` | not run |
| `game-meridian-launch` | HTML | `results/meridian-launch/meridian-launch_claude_fable_5_2.html` | not run |
| `game-sunset-ocean` | HTML | `results/sunset-ocean/sunset-ocean_claude_fable_5_2.html` | not run |
| `game-horror-house` | HTML | `results/horror-house/horror-house_claude_fable_5_2.html` | not run |
| `game-last-flight` | HTML | `results/last-flight/last-flight_claude_fable_5_2.html` | not run |
| `game-cities-skylines` | HTML | `results/cities-skylines/cities-skylines_claude_fable_5_2.html` | not run |
| `game-mario-kart` | HTML | `results/mario-kart/mario-kart_claude_fable_5_2.html` | not run |
| `app-stillwater` | HTML | `results/stillwater/stillwater_claude_fable_5_2.html` | not run |
| `game-weichensteller` | HTML | `results/weichensteller/weichensteller_claude_fable_5_2.html` | not run |
| `game-rubiks-cube` | HTML | `results/rubiks-cube/rubiks-cube_claude_fable_5_2.html` | not run |
| `creative-water-bottle` | HTML | `results/creative-water-bottle/creative-water-bottle_claude_fable_5_2.html` | not run |
| `reasoning-seating-puzzle` | HTML | `results/reasoning-seating-puzzle/reasoning-seating-puzzle_claude_fable_5_2.html` | not run |
| `servicenow-loaner-request` | XML | `results/servicenow-loaner-request/servicenow-loaner-request_claude_fable_5_2.xml` | not run |

**Merging results.** `python3 harness/merge_results.py --model <model-id>`
(add `--dry-run` to only read and report) squash-merges the open
`<prefix> (<model-id>, one-shot): result` PRs that pass a gate: the prompt
exists, the branch and folder match, the PR adds exactly the deliverable and
its `.meta.json` (plus `_grading.json` only for graded prompts) as new files,
and the checks are green. A PR that fails the gate, or that GitHub refuses to
merge, stays open with the reason printed; the command never uses `--admin`
or `--auto`. Afterwards it opens one docs PR that moves the model's `not run`
rows whose files are now on `main` to `generated, review pending`;
that PR is left for you to merge unless the opt-in below is used. Exit codes:
0 done, 1 something stayed open, 2 bad model id or failed preflight.

*Status exception (opt-in).* `main` requires the status contexts
`orchestrai/test` and `orchestrai/review`, and one-shot result PRs have no
orchestrator to post them, so GitHub refuses their merge. With
`--post-statuses` the command posts both as `success` on a result PR that has
passed the full gate, then merges it. Each status has the description prefix
`one-shot result exception:` and vouches for exactly one thing: that
`merge_results.py` gated that commit (file set, new files only, checks green).
Statuses go only on the gated head commit, read once more right before posting;
a PR that has to be brought up to date first is gated again and only its new
head gets them. The ledger docs PR gets the same two statuses and is merged
too, but only after its diff is proven to be exactly the README status cells the
command rewrote (one commit on top of `origin/main`, only `README.md`, checks
green); otherwise it stays open and is reported. A failed post leaves the PR
open with the reason printed, and nothing is retried; `--admin` and `--auto` are
never used. Without the flag the command posts no status, never merges the docs
PR and behaves as before. Branch protection is unchanged.
`/bench-run` batch mode passes the flag in its final merge step, and `--dry-run`
shows what it would post.

## Harness: grading results with `grade.py`

`harness/grade.py` grades results retroactively — it never generates new
model output. For every result file that has a grading rule it writes a
verdict sidecar `<result>_grading.json` next to the result:

```sh
python3 harness/grade.py --all                        # grade the whole corpus
python3 harness/grade.py --prompt game-melon-jelly    # one prompt only
```

A result is gradable when its paired `.meta.json` carries a playability
verdict or its prompt TOML carries a `[grading]` block. Results with neither
are **skipped, never failed**, as are the harness's own artifacts
(`*.meta.json`, `*_grading.json`, images). Prompt association goes through
the meta sidecar's `prompt_id` field.

### Playability labels

The `playability` mode reads the browser-verification verdict from
`<stem>.meta.json` (`playability_verification.playability_verdict`), without
re-verifying anything.

| Label | Verdict |
|---|---|
| `PLAYABLE_VERIFIED` | pass — the only passing label |
| `BOOTS_ONLY` | fail |
| `BROKEN_AT_BOOT` | fail |
| `SCRIPT_TRUNCATED` | fail |

### `[grading]` spec

No prompt currently carries a `[grading]` block; the mechanism stays for
future prompts. It is an opt-in table in a prompt TOML whose `mode` names the
module under `harness/modes/` that grades the result:

```toml
[grading]
mode     = "contains"
expected = "42"
```

- **`contains`** — passes when `expected` appears verbatim in the result
  text.

### Verdict sidecar schema

`<result>_grading.json`, exactly five keys:

```json
{
  "prompt_id": "game-melon-jelly",
  "model": "claude_fable_5_2",
  "mode": "playability",
  "pass": true,
  "detail": "PLAYABLE_VERIFIED"
}
```

`model` is the filename remainder after `<file_prefix>_`; `detail` is free
text explaining the outcome.

## CI

Lightweight validation only: every TOML must parse and every prompt TOML
must declare `id` and a non-empty `user` payload
([workflow](.github/workflows/ci.yml)).

## License

© 2026 Thomas Mueller. All rights reserved. Source shown for reference only.
