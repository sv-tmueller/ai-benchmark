# AI Benchmark — Prompt Corpus & Artifacts

A small corpus of one-shot benchmark prompts and the model outputs they
produce. Every prompt delivers **exactly one file** that can be reviewed
directly: an `.html` page that opens in a browser, or, for the ServiceNow
prompt, an `.xml` update set that imports into an instance.

Two things live here:

- **`prompts/`** — 14 TOML prompt definitions: eleven games and 3D scenes,
  one creative-writing task, one reasoning task and one ServiceNow build task.
- **`results/`** — the collected outputs, one folder per prompt, each
  deliverable next to a `.meta.json` sidecar.

The corpus was reworked in #285. Earlier prompt versions (markdown
blueprints for multi-file projects, plus text, math, SQL, vision and probe
prompts) and every result generated from them were removed; they remain in
the git history.

**Dashboard.** [`dashboard.html`](dashboard.html) at the repo root has one row
per result under `results/`: prompt, model, effort, generation date, and the
duration, output tokens and cost from the result's `.run.json` where it has one
(a dash otherwise). Open it in a browser straight from a clone; it needs no
network. Click a column header to sort (click again to reverse), group by
prompt, model or effort, and click a file name to open that result in a new tab.
The file is committed and kept current by the merge step: the docs PR that
`harness/merge_results.py` opens after merging results also carries the
regenerated page, built from the results on `origin/main`. To regenerate it by
hand run `python3 harness/dashboard.py`. A hand run reflects the working tree,
not `origin/main`: untracked or git-ignored result files that are present there
(a stray folder, an editor's `.swp` next to a result) appear in the page it
writes. The "leaves `git status` clean" statement applies to a clean checkout
whose committed dashboard is current: there the run writes the same bytes (or
writes nothing), so it does not block a later batch run. A `.gitattributes`
entry pins `dashboard.html` to LF line endings in every checkout, whatever
`core.autocrlf` says. Between a result merge and the merge of its docs PR the
committed page is out of date by design: if you regenerated it by hand then,
run `git restore dashboard.html` before starting a batch (the batch needs no
tracked changes).

---

## Prompts

One TOML file per prompt. Core fields: `id` (equal to the file stem),
`title`, `category`, `difficulty`, `save_as`
(the deliverable's extension), `file_prefix` (the result file and folder
name) and a `[system]`/`[user]` text pair.

### Games and scenes

| Prompt | Deliverable | Runtime needs |
|---|---|---|
| `game-melon-jelly.toml` | HTML: soft-body watermelon slice to squish and cut | None — fully offline |
| `game-lava-lamp.toml` | HTML: ray-marched lava lamp studio shot | None — fully offline |
| `game-minecraft.toml` | HTML: voxel world with mining, crafting and mobs | Internet — Three.js + JSZip from a CDN; optional resource pack |
| `scene-meridian-launch.toml` | HTML: scripted rocket launch scene | Internet — Three.js from a CDN |
| `scene-sunset-ocean.toml` | HTML: open ocean at sunset | Internet — Three.js from a CDN |
| `game-horror-house.toml` | HTML: first-person haunted-house escape | Internet — Three.js from a CDN |
| `game-last-flight.toml` | HTML: superhero flight and airliner rescue, with a `?selftest` mode | Internet — Three.js + postprocessing from a CDN |
| `game-cities-skylines.toml` | HTML: city builder with a living demo city | Internet — Three.js from a CDN |
| `game-mario-kart.toml` | HTML: kart racer | Internet — Three.js from a CDN |
| `game-weichensteller.toml` | HTML: model-railway junction game | Internet — Three.js from a CDN |
| `game-rubiks-cube.toml` | HTML: 3D Rubik's cube to scramble and solve by hand | Internet — Three.js from a CDN |

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
results/<file_prefix>/<file_prefix>_<model_tag>_<effort>.<save_as>      the deliverable
results/<file_prefix>/<file_prefix>_<model_tag>_<effort>.meta.json      the sidecar
results/<file_prefix>/<file_prefix>_<model_tag>_<effort>.run.json       run metrics (batch runs only)
```

The model tag is the model id in lower case with every run of
non-alphanumerics replaced by `_` (`claude-fable-5-2` → `claude_fable_5_2`).
The effort is the effort level of the session that generated the result
(`low`, `medium`, `high`, `xhigh` or `max`), so
`melon-jelly_claude_fable_5_2_high.html` is Fable 5.2 at `high`, and results of
one model at different effort levels sit side by side.
The sidecar records the prompt, the model, how the result was generated and
that the session's defaults applied.

A result generated in a batch run also has a run file with the generating
session's duration and token usage: `duration_seconds`, `input_tokens`,
`output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `cost_usd`. Results
from `/bench-run <prompt-id>`, and older ones, have none.

## One-shot arm

Every prompt is run as a plain one-shot: one fresh session per prompt, one
pass, one file, no orchestrator, no agents and no repair round. The table
below is the ledger for Claude Fable 5.2.

**How to run.** Start a batch with `/bench-run` and no arguments from a
checkout of `main` that matches `origin/main` with no tracked changes
(untracked files don't matter). It lists the arm's 14 prompts numbered in
ledger order, marks each one that already has a result on `origin/main` or in
an open PR for your model and effort level, and asks which to run: `all`, or
numbers such as `2`, `1,4,7`, `3-6` or `1,3-5`; any other answer is asked
again. `/bench-run all` runs the whole arm without asking. The skill calls
[`harness/bench_run_all.py`](harness/bench_run_all.py), which starts one fresh
headless Claude Code session per selected prompt (`claude -p "/bench-run <prompt-id>"`)
with the calling session's exact model id and effort level, a narrow tool
allowlist and no merge rights, so each prompt is still one isolated one-shot.
The sessions run in a private git worktree for that model and effort level
(`.claude/worktrees/bench-run-<model-tag>_<effort>`, detached at `origin/main`),
never in your checkout, so batches for other models or effort levels can run
side by side from the same checkout; a second batch for the same model and
effort stops while the first is running. After a run that ended without a halt
the worktree is removed; after a halt it is kept, and the next run reuses it
only if it is clean and not detached at a commit that is not on `origin/main`.
After a session that opened a PR has exited, the helper reads that session's
duration, token usage and cost from its JSON output and adds them to the PR: as
the run file, in a commit of its own made through the GitHub API, and as a "Run
metrics" section in the PR description. If the output carries no usable usage
data, the description says so and no run file is written. If the commit or the
edit fails, the PR stays valid and the report line says so.
`/bench-run --dry-run` asks the same question, then prints the checks, which
selected prompts would run or be skipped, and the exact child command, and
starts nothing; `/bench-run all --dry-run` does this for the whole arm. A
prompt that already has a result on `origin/main` or in an open PR is skipped
even when selected, so re-typing `/bench-run all` after an interruption
resumes the arm, and after CI turns green it skips all 14 and reaches the
final merge step again (the
helper runs `harness/merge_results.py` when that file exists, otherwise it
lists the open PRs). A single prompt still runs with `/bench-run <prompt-id>`,
for example `/bench-run game-melon-jelly`. The prompt TOML under `prompts/` is
used unmodified. The effort level is always the session's own
(`CLAUDE_EFFORT`), never typed in: it goes into the file name, the issue, the
commit and the PR title (`<prefix> (<model-id>, <effort>, one-shot): result`),
and into the sidecar's `reasoning_effort`. A run stops if the level is unset
or unknown. The skip check is per effort level, so running the arm again at
another level generates a second set of results.

**In-session generation caveats.** The generation happens inside a Claude
Code session, so:

- No sampling settings can be set, so the prompt files carry none; the session
  defaults apply.
- `finish_reason` and token `usage` are not observable. The sidecar records
  them as `null` with a note. In a batch run the helper records the session's
  usage afterwards in the run file; the sidecar is unchanged.
- There is no length-retry ladder: the first complete output is the result.

**Verification split.** Generation runs on the small dev box. Reviewing the
results is a separate step: HTML results are opened in a browser on a
stronger machine, and the ServiceNow update set is imported into a Personal
Developer Instance.

**Verification bar.** Per HTML game or scene: a click-through transition,
sustained animation (pixel motion sampled over at least 3 s), per-script
brace/paren balance, and console capture across 10 s. The result is labelled
`PLAYABLE_VERIFIED`, `BOOTS_ONLY` or `BROKEN_AT_BOOT` (see
[Playability labels](#playability-labels)) in its sidecar, in a commit of its
own. A result has no playability verdict until this check has run; generation
alone does not earn one.

**Status.** `<effort>` in a target path stands for the effort level of a
run. A row moves from `not run` to `generated (<effort>), review pending` when
a result and its sidecar are on `main`, and lists every level that is there,
for example `generated (high, max), review pending`.

| Prompt | Deliverable | Target path | Status |
|---|---|---|---|
| `game-melon-jelly` | HTML | `results/melon-jelly/melon-jelly_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `game-lava-lamp` | HTML | `results/lava-lamp/lava-lamp_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `game-minecraft` | HTML | `results/minecraft/minecraft_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `scene-meridian-launch` | HTML | `results/meridian-launch/meridian-launch_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `scene-sunset-ocean` | HTML | `results/sunset-ocean/sunset-ocean_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `game-horror-house` | HTML | `results/horror-house/horror-house_claude_fable_5_2_<effort>.html` | generated (medium), review pending |
| `game-last-flight` | HTML | `results/last-flight/last-flight_claude_fable_5_2_<effort>.html` | not run |
| `game-cities-skylines` | HTML | `results/cities-skylines/cities-skylines_claude_fable_5_2_<effort>.html` | not run |
| `game-mario-kart` | HTML | `results/mario-kart/mario-kart_claude_fable_5_2_<effort>.html` | not run |
| `game-weichensteller` | HTML | `results/weichensteller/weichensteller_claude_fable_5_2_<effort>.html` | not run |
| `game-rubiks-cube` | HTML | `results/rubiks-cube/rubiks-cube_claude_fable_5_2_<effort>.html` | not run |
| `creative-water-bottle` | HTML | `results/creative-water-bottle/creative-water-bottle_claude_fable_5_2_<effort>.html` | not run |
| `reasoning-seating-puzzle` | HTML | `results/reasoning-seating-puzzle/reasoning-seating-puzzle_claude_fable_5_2_<effort>.html` | not run |
| `servicenow-loaner-request` | XML | `results/servicenow-loaner-request/servicenow-loaner-request_claude_fable_5_2_<effort>.xml` | not run |

**Merging results.** `python3 harness/merge_results.py --model <model-id>`
(add `--dry-run` to only read and report) squash-merges the open
`<prefix> (<model-id>, <effort>, one-shot): result` PRs of the model, at every
effort level, that pass a gate: the prompt exists, the branch and folder match
the model and the effort in the title, the PR adds exactly the deliverable and
its `.meta.json` (plus `_grading.json` only for graded prompts, and the
`.run.json` run file if the batch helper added one) as new files,
and the checks are green. A PR that fails the gate, or that GitHub refuses to
merge, stays open with the reason printed; the command never uses `--admin`
or `--auto`. Afterwards it opens one docs PR that brings the model's ledger rows up to
date with the effort levels whose files are now on `main` and regenerates
`dashboard.html` from the results on `origin/main` (read as git objects at one
pinned commit, never from your working tree). The PR is one commit that changes
`README.md`, `dashboard.html` or both, whichever is out of date: if only the
dashboard is stale it carries just the dashboard, and if both are current no PR
is opened. `dashboard.html` must already exist on `origin/main`; if it does not,
the command reports that, exits 1 and does not add it.
That PR is left for you to merge unless the opt-in below is used. Exit codes:
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
too, but only after its diff is proven to be exactly what the command computed:
one commit whose only parent is the pinned `origin/main`, changing exactly the
expected files (`README.md`, `dashboard.html` or both) and nothing else, each
`modified` to byte for byte this run's content, with main's README as its base
and green checks. A docs PR with an extra or a missing file, other content or an
older base stays open and is reported, and that includes one left by an earlier
run when the dashboard has since gone stale. A failed post leaves the PR
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
(`*.meta.json`, `*_grading.json`, `*.run.json`, images). Prompt association goes through
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

`model` is the filename remainder after `<file_prefix>_` (for a `/bench-run`
result that includes the effort, e.g. `claude_fable_5_2_high`); `detail` is free
text explaining the outcome.

## CI

Lightweight validation only: every TOML must parse and every prompt TOML
must declare `id` and a non-empty `user` payload
([workflow](.github/workflows/ci.yml)).

## License

© 2026 Thomas Mueller. All rights reserved. Source shown for reference only.
