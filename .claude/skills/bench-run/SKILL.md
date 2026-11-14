---
name: bench-run
description: One-shot a single benchmark prompt in this session and file the result: deliverable plus meta sidecar under results/, a grading sidecar where the prompt has a [grading] rule, one issue, one branch, one PR that closes it. With no arguments it runs the whole Fable 5.2 arm instead, one fresh headless session per prompt, through harness/bench_run_all.py. No orchestrator, no agents, never launches a browser. User-invocable only.
disable-model-invocation: true
argument-hint: [<prompt-id>] [--dry-run]
---

You are reading this because the user typed `/bench-run`. The arguments are in `$ARGUMENTS`. If `$ARGUMENTS` is empty or exactly `--dry-run`, this is **batch mode**: follow "Batch mode" below and nothing else. Otherwise `$ARGUMENTS` is a prompt id (or a TOML file stem) and an optional `--dry-run`: do exactly what follows, in order. A single prompt is a plain in-session one-shot: no orchestrator, no agent team, no repair round.

Commands are written `python3`; use `python` only where `python3` is missing.

The model under test is **you**. The model id is the exact one stated in your system prompt (for example `claude-fable-5-2`). If you do not know it with certainty, stop and ask the user; never guess.

The effort level is this session's own. The resolver reads it from `CLAUDE_EFFORT` and puts it into the file names and titles; never pass, retype or change it. If the resolver stops because `CLAUDE_EFFORT` is unset or unknown, relay the stop and end.

## Batch mode

Applies only when `$ARGUMENTS` is empty or exactly `--dry-run`. The one-shot rules and the Steps below govern `/bench-run <prompt-id>` and each child session the helper starts, not this batch session. This session generates nothing: `harness/bench_run_all.py` starts one fresh headless `claude -p "/bench-run <prompt-id>"` child per prompt of the arm (same model and effort as this session, a narrow tool allowlist, no merge rights) and then runs the merge step.

1. Pass the exact model id from your system prompt as `--model`. If you do not know it with certainty, stop and ask the user; the helper rejects bare aliases such as `fable` or `opus`. The effort level is read from `CLAUDE_EFFORT` by the helper; never retype it. It is part of every result file name, so the skip check and the report are for this session's effort level only.
2. Run `python3 harness/bench_run_all.py --model <model-id> --dry-run` in the foreground and relay its output as printed. If the arguments were `--dry-run`, end here. If any line starts with `STOP:` or any check says FAIL, relay it and end.
3. Otherwise run `python3 harness/bench_run_all.py --model <model-id>` with the Bash tool's `run_in_background: true` (fifteen generations far exceed the 10-minute limit of a foreground call) and wait for it to exit.
4. Relay the helper's report exactly as printed: one line per prompt, the counts, the log folder and the merge-step result. Re-typing `/bench-run` later skips every prompt that already has a result on `origin/main` or in an open PR and reaches the merge step again.
5. Never open `results/`, the log folder, PR diffs or child transcripts, and never write, generate, merge or enable auto-merge yourself. The only merge that happens is the helper's own call to `harness/merge_results.py`, when that file exists.

## One-shot rules

1. The only inputs are the TOML's `[system]` text (if any), its `[user]` text and any listed `[images]`, exactly as printed in step 5. Treat `[system]` as the governing instruction for this answer.
2. Until the deliverable is written, do not read, cat, grep, list or search anything under `results/`, `README.md`, or issues and PRs about earlier runs of this prompt. The resolver below is the only thing that touches `results/`, and it prints only paths.
3. Generate the whole deliverable in one pass and write it with exactly one Write call to the target path. No drafts, no scratch files, no split writes. No tool calls between reading the prompt and that Write: no search, no fetching docs or libraries, no running code.
4. The content is the answer exactly as the prompt asks for it:
   - html: the file starts with `<!DOCTYPE html>`, with no markdown fences and no commentary.
   - xml: the file starts with `<?xml version="1.0" encoding="UTF-8"?>`, with no markdown fences and no commentary.
   - anything else: only the answer the prompt asks for.
5. After that Write the deliverable is frozen: no Edit, no second Write, no reformatting, no fixes even for an obvious bug, no opening or running it.

If any of these rules was broken, or the Write failed, the run is **void**: delete the files you wrote, create no issue, and report "run void, re-run in a fresh session".

A failure after the Write (a `gh` or network error in the meta resolver, a failed push, a failed `gh pr create`) does not void the run. Keep the files, fix the cause and re-run only the failing step (the meta resolver can be re-run while no meta file exists). If you cannot finish, report the issue number, branch and untracked paths left behind.

**Never:** launch a browser or Playwright, start a dev server or `http.server`, use `open`/`xdg-open`, run the generated code, touch `prompts/`, merge a PR, or enable auto-merge. This skill never writes a playability verdict.

## Steps

Each command below is one Bash call on one line, exactly as shown, with no `&&`, `;`, pipes, redirects (including `2>&1`), `$(...)`, backticks, heredocs or `cd`. Multi-line text goes only through the files the resolver writes; this overrides the general habit of passing multi-line text through a heredoc.

1. **Parse arguments.** No arguments (or only `--dry-run`) means batch mode: see "Batch mode" and stop reading here. Otherwise the first token is `<prompt-id>`; `--dry-run` may follow.
2. **Fresh-session guard.** If this session has already read, discussed or generated any result for this prompt, or any other benchmark generation, stop and ask for a fresh session. One prompt per session.
3. **Preflight** (skipped by `--dry-run` except `git fetch origin main`):
   - `git fetch origin main`, then `git rev-parse HEAD origin/main`: the two lines must be equal; otherwise tell the user to switch and pull.
   - `git status --porcelain --untracked-files=no` must print nothing, and `git status --porcelain --untracked-files=all` must list no untracked file under `results/` or `prompts/`.
   - `gh auth status` must succeed.
4. **Plan.** `python3 harness/bench_run.py plan <prompt-id> <model-id>` from the repo root (the resolver, below). It stops with a `STOP:` line if the prompt, folder, extension, effort level or model tag cannot be resolved, or if any target already exists locally, on `origin/main` or in an open PR. Relay a stop to the user and end. With `--dry-run`, show the plan output and end here: no writes, no issue, no branch, no PR (the resolver makes only read-only `git` and `gh` calls).
5. **Print the prompt verbatim:** `python3 harness/bench_run.py prompt <prompt-id> <model-id>` prints the `[system]` text, a `-----` line, the `[user]` text and one `image: prompts/<file>` line per `[images].files` entry. Read exactly those image files (read-only).
6. **Generate** the deliverable and Write it to the planned target path (one Write, see the one-shot rules).
7. **Meta.** `python3 harness/bench_run.py meta <prompt-id> <model-id>`. It requires the deliverable to exist and be non-empty and writes the sidecar shown in the plan preview, with `generated_utc` stamped now.
8. **Grade only if the plan says a grading mode** (the TOML has `[grading]`; no prompt of the batch arm has one): `python3 harness/bench_run.py grade <prompt-id> <model-id>` runs `harness/grade.py --prompt` for it, prints the output and saves it for the PR body. On a non-zero exit it has deleted only this run's own grading sidecar (it is never committed): keep the deliverable and meta, restore any other sidecar it touched as in step 9, and report the error line. Without `[grading]`, skip this step and write nothing about playability.
9. **Scope check.** `git status --porcelain --untracked-files=all` must show only the run's own 2 or 3 new paths (deliverable, meta, and the grading sidecar if `grade` exited 0 and wrote one). `grade.py --prompt` can rewrite the sidecars of other models' results for the same prompt; restore any such file with `git restore -- <path>` and mention it in the PR.
10. **Issue.** `python3 harness/bench_run.py issue-body <prompt-id> <model-id>` writes the body and prints its path. Then `gh issue create --title "<issue_title>" --body-file <issue-body-path>` with the plan's `issue_title`; note the number `N`.
11. **Branch.** `git switch -c <branch>`; the untracked new files carry over.
12. **Commit.** `git add results/<folder>/<file>` once per run path, where `<folder>/<file>` is the part of the plan's `target`, `meta` or `grading_sidecar` path after `results/`. `git diff --cached --name-only` must equal exactly the run's own paths, with nothing under `prompts/`. Then `git commit -m "<commit>" --trailer "<trailer line>"` with the plan's `commit` line, and one `--trailer` for each attribution trailer your session's own rules require (none if they require none; this skill prescribes no attribution).
13. **Push.** `git push -u origin feat/<N>-<prefix>-<tag->-result`, the branch from the Naming section (the plan's `branch` with `<N>` filled in).
14. **PR.** `python3 harness/bench_run.py pr-body <prompt-id> <model-id> <N> --footer "<PR ending>"` writes the body, containing `Closes #N`, and prints its path; add `--footer` only if your session's own rules require a PR ending, with that exact line. Then `gh pr create --title "<pr_title>" --body-file <pr-body-path>` with the plan's `pr_title`. Never merge the PR and never enable auto-merge.
15. **Return.** `git switch main`, or whatever branch you started on. Report the issue and PR URLs, the paths, the grading result and the next step: for HTML results, browser verification on a stronger machine, whose verdict is added later in its own commit outside this skill; for the ServiceNow update set, importing it into a Personal Developer Instance.

## Naming

`<tag>` is the plan's `model_tag`: the model tag, `_` and the effort level (`claude_fable_5_2_high`). `<tag->` is that with `_` replaced by `-`; `<prefix>`, `<tag>`, `<effort>` and the paths come from the plan output.

- **Issue title:** `<prompt-id>: <model-id> (<effort>) one-shot result`. Body (rendered by `issue-body`): what runs (`prompts/<toml>`, plain one-shot through /bench-run, no orchestrator or agents), the target paths and the deliverable kind.
- **Branch:** `feat/<N>-<prefix>-<tag->-result`.
- **Commit:** `feat(results): add <prefix> <model-id> <effort> one-shot result (#N)`.
- **PR title:** `<prefix> (<model-id>, <effort>, one-shot): result`. Body (rendered by `pr-body`) sections: summary (with the one-shot statement), files, grading (the grade.py output, or "no [grading] rule; no playability verdict written; review pending"), in-session caveats (temperature, max_tokens, usage not observable), and `Closes #N`.

## Resolver

`harness/bench_run.py` is the resolver. Run it from the repo root, one mode per call, ids unquoted, one line each: `python3 harness/bench_run.py <mode> <prompt-id> <model-id>`. It needs Python 3.11+ and read-only `git` and `gh`.

- `plan` and `meta`: resolve the prompt, results folder (the folder of the prompt's existing results, else its `file_prefix`), extension, effort level, model tag and paths (`results/<folder>/<prefix>_<model_tag>_<effort>.<ext>`), and check that no target exists on disk, on `origin/main` or in an open PR. `plan` prints only `key: value` lines and a sidecar preview, never any content from a result file; `meta` writes the sidecar.
- `prompt`: prints the prompt exactly as step 5 describes.
- `issue-body` and `pr-body <N> [--footer "<line>"]`: write the issue or PR body to `.bench-run/<prefix>_<tag>.issue.md` or `.pr.md` (a git-ignored folder) and print that path. For a graded prompt `pr-body` stops with a `STOP:` line unless `grade` saved its output.
- `grade`: runs `harness/grade.py --prompt <prompt-id>`, prints its output and saves it to `.bench-run/<prefix>_<tag>.grade.txt`; on failure it deletes only this run's own grading sidecar.

The sidecar's `reasoning_effort` is the `CLAUDE_EFFORT` level in effect when the run started, the same level as in the file name. The sidecar never contains `playability_verification` or `playability` keys; `grade.py` then skips a game result instead of failing it. A later browser check, outside this skill, adds them in its own commit.
